"""Run writing progression after lesson completion — updates shared progression row."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.language.enums import LanguageLevel
from app.services.language_level_utils import CEFR_RANK
from app.services.language_progression_service import ensure_progression_row, record_progression_event
from app.services.language_writing.enums import OfficialWritingCEFR, WritingGoal
from app.services.language_writing_evaluator.evaluation_result import WritingEvaluationEngineResult
from app.services.language_writing_learning_stage.types import writing_stage_label, WritingLearningStage
from app.services.language_writing_progression.json_mutation import mutate_writing_progression_json
from app.services.language_writing_progression.storage import RECENT_NODE_WINDOW, writing_state_from_payload
from app.services.language_writing_progression.types import (
    WritingChallengeSnapshot,
    WritingConfidenceSnapshot,
    WritingEvidenceSnapshot,
    WritingProgressionResult,
)
from app.services.language_writing_revision.comparison import RevisionComparisonResult


def _blend_mastery(mastery: dict[str, float], key: str, *, score: float, passed: bool) -> None:
    """Move mastery toward the actual continuous dimension score (EMA).

    Uses the real evaluator score rather than a fixed pass/fail step, so mastery
    reflects performance quality. Falls back to a pass/fail nudge when no score.
    """
    if not key:
        return
    prev = float(mastery.get(key, 0.5))
    if score is not None and score > 0:
        target = max(0.0, min(1.0, float(score)))
        blended = prev + (target - prev) * 0.4
    else:
        blended = min(1.0, prev + 0.12) if passed else max(0.0, prev - 0.08)
    mastery[key] = round(max(0.0, min(1.0, blended)), 3)


def _dim_score(evaluation: WritingEvaluationEngineResult, name: str) -> float:
    """Blend the rule-engine dimension score with Claude's insight when available."""
    rule = {
        "task_response": evaluation.task_completion.score,
        "organization": evaluation.organization.score,
    }.get(name, 0.5)
    claude = evaluation.claude_analysis
    if claude is None or not getattr(claude, "available", False):
        return max(0.0, min(1.0, float(rule)))
    if name == "task_response":
        c = float(getattr(claude.task_response, "score", 0.0) or 0.0)
    elif name == "organization":
        org = float(getattr(claude.organization, "score", 0.0) or 0.0)
        coh = float(getattr(claude.coherence, "score", 0.0) or 0.0)
        c = (org + coh) / 2.0 if (org or coh) else 0.0
    else:
        c = 0.0
    if c <= 0:
        return max(0.0, min(1.0, float(rule)))
    return max(0.0, min(1.0, 0.5 * float(rule) + 0.5 * c))


def _cefr_alignment_value(evaluation: WritingEvaluationEngineResult, official_cefr: str) -> float:
    """0..1 measure of how close the draft's CEFR is to the official band.

    Prefers Claude's estimate (rank vs official); falls back to the rule engine's
    CEFR validation status. Repeated below-band drafts keep this low so readiness
    cannot falsely climb.
    """
    claude = evaluation.claude_analysis
    estimate = ""
    if claude is not None and getattr(claude, "available", False):
        estimate = (getattr(claude, "cefr_estimate", "") or "").strip().upper()
    estimate = estimate.replace("+", "")
    if estimate:
        try:
            est_rank = CEFR_RANK.get(LanguageLevel(estimate))
            off_rank = CEFR_RANK.get(LanguageLevel(official_cefr.upper()))
            if est_rank is not None and off_rank is not None:
                delta = est_rank - off_rank
                if delta >= 0:
                    return 1.0
                if delta == -1:
                    return 0.5
                return 0.2
        except ValueError:
            pass
    status = evaluation.cefr_validation.status.value
    return {"met": 0.9, "partial": 0.6, "not_met": 0.3}.get(status, 0.6)


def _coach_memory_update(
    memory: dict[str, Any],
    *,
    weaknesses: tuple[str, ...],
    strengths: tuple[str, ...],
    content_item_id: int,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    mistakes = list(memory.get("repeated_mistakes") or [])
    str_list = list(memory.get("repeated_strengths") or [])
    for w in weaknesses[:3]:
        code = w.split(":", 1)[-1]
        found = next((m for m in mistakes if m.get("code") == code), None)
        if found:
            found["occurrence_count"] = int(found.get("occurrence_count") or 0) + 1
            found["last_seen_at"] = now
        else:
            mistakes.append({"code": code, "label": w, "occurrence_count": 1, "last_seen_at": now, "lesson_ids": [content_item_id]})
    for s in strengths[:2]:
        code = s.split(":", 1)[-1]
        found = next((m for m in str_list if m.get("code") == code), None)
        if found:
            found["occurrence_count"] = int(found.get("occurrence_count") or 0) + 1
        else:
            str_list.append({"code": code, "label": s, "occurrence_count": 1, "last_seen_at": now})
    memory["repeated_mistakes"] = mistakes[-12:]
    memory["repeated_strengths"] = str_list[-12:]


def _history_comparison_phrases(
    state: dict[str, Any],
    *,
    evaluation: WritingEvaluationEngineResult,
    comparison: RevisionComparisonResult | None,
) -> tuple[str, ...]:
    phrases: list[str] = []
    history = state.get("lesson_history") or []
    if len(history) >= 1 and comparison and comparison.improved:
        phrases.append(f"You improved {', '.join(comparison.improved[:2])} compared to your previous draft.")
    prev_weak = set()
    if history:
        last = history[-1]
        if isinstance(last, dict):
            prev_weak = set(last.get("weaknesses") or [])
    current_weak = set(evaluation.weak_skills)
    fixed = prev_weak - current_weak
    if fixed:
        phrases.append(f"You are making fewer mistakes in {', '.join(list(fixed)[:2])} than last lesson.")
    if evaluation.strong_skills:
        phrases.append("You use more consistent vocabulary when you address the task clearly.")
    return tuple(phrases)


async def run_writing_progression_after_complete(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    content_item_id: int,
    goal: WritingGoal,
    official_cefr: OfficialWritingCEFR,
    chain_id: str,
    node_id: str,
    evaluation: WritingEvaluationEngineResult,
    revision_count: int = 1,
) -> WritingProgressionResult:
    """Persist learning progress after a completed writing lesson — render-only from evaluation."""
    comparison = evaluation.comparison
    completion = evaluation.completion
    history_phrases: tuple[str, ...] = ()

    def mutator(state: dict[str, Any]) -> dict[str, Any]:
        nonlocal history_phrases
        completed = list(state.get("completed_node_ids") or [])
        if node_id not in completed:
            completed.append(node_id)
        recent = [node_id] + [n for n in (state.get("recent_node_ids") or []) if n != node_id]
        recent = recent[:RECENT_NODE_WINDOW]

        weak = list(state.get("weak_skills") or [])
        for w in evaluation.weak_skills:
            if w not in weak:
                weak.append(w)
        weak = weak[-10:]
        strong = list(state.get("strong_skills") or [])
        for s in evaluation.strong_skills:
            if s not in strong:
                strong.append(s)
        strong = strong[-10:]

        grammar_m = dict(state.get("grammar_mastery") or {})
        vocab_m = dict(state.get("vocabulary_mastery") or {})
        _blend_mastery(
            grammar_m,
            evaluation.grammar.dimension,
            score=evaluation.grammar.score,
            passed=evaluation.grammar.passed,
        )
        _blend_mastery(
            vocab_m,
            "vocabulary",
            score=evaluation.vocabulary.score,
            passed=evaluation.vocabulary.passed,
        )

        coach_mem = dict(state.get("coach_memory") or {})
        _coach_memory_update(
            coach_mem,
            weaknesses=evaluation.weak_skills,
            strengths=evaluation.strong_skills,
            content_item_id=content_item_id,
        )

        lessons_count = int(state.get("lessons_completed_count") or 0) + 1
        current_stage = int(state.get("learning_stage") or 1)
        estimated = int(state.get("estimated_lessons_to_next_stage") or 5)

        history_phrases = _history_comparison_phrases(state, evaluation=evaluation, comparison=comparison)

        task_response_score = _dim_score(evaluation, "task_response")
        organization_score = _dim_score(evaluation, "organization")
        cefr_alignment = _cefr_alignment_value(evaluation, official_cefr.value)
        claude = evaluation.claude_analysis
        cefr_estimate = ""
        if claude is not None and getattr(claude, "available", False):
            cefr_estimate = (getattr(claude, "cefr_estimate", "") or "").strip().upper()

        lesson_entry = {
            "content_item_id": content_item_id,
            "chain_id": chain_id,
            "node_id": node_id,
            "goal": goal.value,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "revision_count": revision_count,
            "criteria_met": completion.criteria_met_count,
            "criteria_total": completion.criteria_total,
            "confidence": round(evaluation.confidence, 4),
            # Continuous educational facts from WritingEvaluationEngineResult
            "grammar_score": round(evaluation.grammar.score, 4),
            "vocabulary_score": round(evaluation.vocabulary.score, 4),
            "organization_score": round(organization_score, 4),
            "task_response_score": round(task_response_score, 4),
            "goal_alignment_score": round(evaluation.goal_alignment.score, 4),
            "overall_readiness": round(evaluation.overall_readiness, 4),
            "cefr_estimate": cefr_estimate,
            "cefr_validation_status": evaluation.cefr_validation.status.value,
            "cefr_alignment": round(cefr_alignment, 4),
            "weaknesses": list(evaluation.weak_skills),
            "strengths": list(evaluation.strong_skills),
        }
        hist = list(state.get("lesson_history") or [])
        hist.append(lesson_entry)
        hist = hist[-20:]

        today = datetime.now(timezone.utc).date().isoformat()
        last_day = str(state.get("progress_day") or "")
        lessons_today = int(state.get("lessons_today") or 0)
        if last_day != today:
            lessons_today = 1
        else:
            lessons_today += 1

        state.update(
            {
                "completed_node_ids": completed,
                "recent_node_ids": recent,
                "weak_skills": weak,
                "strong_skills": strong,
                "grammar_mastery": grammar_m,
                "vocabulary_mastery": vocab_m,
                "coach_memory": coach_mem,
                "lessons_completed_count": lessons_count,
                "current_chain_id": chain_id,
                "current_node_id": node_id,
                "learning_stage": current_stage,
                "learning_stage_label": writing_stage_label(
                    official_cefr=official_cefr.value,
                    stage=WritingLearningStage(max(1, min(3, current_stage))),
                ),
                "estimated_lessons_to_next_stage": estimated,
                "lesson_history": hist,
                "lessons_today": lessons_today,
                "progress_day": today,
                "last_completed_at": lesson_entry["completed_at"],
                "history_phrases": list(history_phrases),
            }
        )
        return state

    row, updated = await mutate_writing_progression_json(
        db,
        student_id=student_id,
        language_id=language_id,
        mutator=mutator,
    )
    stage_before = int((updated or {}).get("learning_stage") or 1)
    from app.services.language_writing_progression.runtime import run_writing_progression_engines

    await run_writing_progression_engines(db, student_id=student_id, language_id=language_id)
    readiness_score = 0.0
    if row is not None:
        await db.refresh(row)
        payload = dict(row.promotion_readiness_json or {})
        updated = writing_state_from_payload(payload)
        wr = payload.get("writing_readiness") or {}
        if isinstance(wr, dict):
            readiness_score = float(wr.get("readiness_score") or 0) / 100.0
        row.learning_stage_writing = int((updated or {}).get("learning_stage") or 1)
        flag_modified(row, "learning_stage_writing")
        await db.flush()

    await record_progression_event(
        db,
        student_id=student_id,
        language_id=language_id,
        event_type="writing_lesson_completed",
        payload_json={
            "content_item_id": content_item_id,
            "chain_id": chain_id,
            "node_id": node_id,
            "goal": goal.value,
            "criteria_met": completion.criteria_met_count,
            "criteria_total": completion.criteria_total,
        },
    )

    lessons_count = int((updated or {}).get("lessons_completed_count") or 1)
    stage = int((updated or {}).get("learning_stage") or 1)
    return WritingProgressionResult(
        student_id=student_id,
        language_id=language_id,
        content_item_id=content_item_id,
        official_cefr=official_cefr,
        confidence=WritingConfidenceSnapshot(
            overall=evaluation.confidence,
            grammar=evaluation.grammar.score,
            lexis=evaluation.vocabulary.score,
            organization=evaluation.organization.score,
            task_achievement=evaluation.task_completion.score,
        ),
        evidence=WritingEvidenceSnapshot(
            chain_nodes_completed=tuple((updated or {}).get("completed_node_ids") or []),
        ),
        challenge=WritingChallengeSnapshot(challenge_level="standard"),
        learning_stage=stage,
        stage_advanced=stage > stage_before,
        readiness_score=readiness_score,
    )
