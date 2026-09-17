"""Assemble WritingJourneyBundle — stage, readiness, blockers, WPA availability."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.language_writing_bundles import WritingJourneyBundleOut
from app.services.language_learner_memory_service import get_memory
from app.services.language_level_utils import CEFR_RANK, RANK_CEFR
from app.services.language_progression_service import ensure_progression_row
from app.services.language_promotion_readiness.types import ReadinessStatus
from app.services.language_writing.enums import OfficialWritingCEFR, WritingGoal
from app.services.language_writing_curriculum.goal_profiles import profile_for_goal as writing_profile_for_goal
from app.services.language_writing_curriculum.selector import select_writing_curriculum_node
from app.services.language_writing_journey import BUILDER_VERSION
from app.services.language_writing_journey.types import (
    WritingJourneyBundle,
    WritingJourneyGoal,
    WritingJourneyMission,
    WritingJourneyPromotion,
)
from app.services.language_writing_learning_stage import evaluate_writing_learning_stage
from app.services.language_writing_learning_stage.types import writing_stage_label
from app.services.language_writing_promotion_readiness import evaluate_writing_promotion_readiness
from app.services.language_writing_promotion_readiness.engine import estimated_lessons_from_readiness
from app.services.language_writing_promotion_stability import evaluate_writing_promotion_stability
from app.services.language_writing_promotion_test import check_writing_promotion_test_eligibility
from app.services.language_writing_promotion_test.storage import get_active_session, latest_attempt
from app.services.language_writing_progression.storage import (
    completed_node_ids_from_state,
    load_completed_nodes_from_lessons,
    merge_completed_nodes,
    writing_state_from_payload,
)
from app.services.language_writing_runtime.student_context import (
    official_writing_cefr_for_student,
    writing_goal_from_preferences,
)


def _target_cefr(official: str) -> str:
    try:
        from app.models.language.enums import LanguageLevel

        rank = CEFR_RANK.get(LanguageLevel(official.upper()), 1) + 1
        return RANK_CEFR[rank].value if rank in RANK_CEFR else official
    except ValueError:
        return official


async def build_writing_journey_bundle(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> WritingJourneyBundleOut:
    official = await official_writing_cefr_for_student(db, student_id=student_id, language_id=language_id)
    memory = await get_memory(db, student_id=student_id, language_id=language_id)
    writing_goal = writing_goal_from_preferences(memory)
    wprofile = writing_profile_for_goal(writing_goal)

    row = await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    payload = dict(row.promotion_readiness_json or {}) if row else {}
    state = writing_state_from_payload(payload)
    from_lessons = await load_completed_nodes_from_lessons(db, student_id=student_id, language_id=language_id)
    state = merge_completed_nodes(state, from_lessons)
    completed = completed_node_ids_from_state(state)
    recent = frozenset(str(n) for n in (state.get("recent_node_ids") or []) if n)
    weak = tuple(str(w) for w in (state.get("weak_skills") or []) if w)

    stage_result = await evaluate_writing_learning_stage(
        db, student_id=student_id, language_id=language_id, official_cefr=official.value
    )
    readiness = await evaluate_writing_promotion_readiness(
        db, student_id=student_id, language_id=language_id, official_cefr=official.value
    )
    stability = await evaluate_writing_promotion_stability(db, student_id=student_id, language_id=language_id)
    wpa_eligible, wpa_reason, _, target = await check_writing_promotion_test_eligibility(
        db, student_id=student_id, language_id=language_id
    )

    selection = select_writing_curriculum_node(
        goal=writing_goal,
        official_cefr=official,
        completed_node_ids=completed,
        recent_node_ids=recent,
        weak_skills=weak,
    )

    lessons_count = int(state.get("lessons_completed_count") or 0)
    stage = int(stage_result.current_stage)
    stage_label = writing_stage_label(official_cefr=official.value, stage=stage)
    estimated = estimated_lessons_from_readiness(readiness.estimated_remaining)

    weak_display = tuple(w.replace("_", " ").split(":")[-1] for w in weak[:4])
    strong_display = tuple(s.replace("_", " ").split(":")[-1] for s in (state.get("strong_skills") or [])[:3])

    blockers = list(readiness.primary_blockers) + list(readiness.secondary_blockers)[:2]
    promotion_checklist = tuple(
        list(readiness.next_actions[:3])
        or [f"Reach stage 3 with strong grammar and revision quality at {official.value}"]
    )

    active_wpa = get_active_session(payload)
    last_attempt = latest_attempt(payload)

    bundle = WritingJourneyBundle(
        official_writing_level=official.value,
        learning_stage_label=stage_label,
        personal_goal=WritingJourneyGoal(id=writing_goal.value, label=wprofile.label),
        todays_mission=WritingJourneyMission(
            lesson_id=None,
            title=selection.node.label,
            status="ready" if lessons_count == 0 else "continue",
            teaser=selection.node.narrative_why[:120],
        ),
        weak_skills=weak_display or ("task completion",),
        progress_summary=(
            f"{official.value} writing · Stage {stage}/3 · "
            f"{lessons_count} lesson{'s' if lessons_count != 1 else ''} · "
            f"Readiness {readiness.readiness_score}/100"
        ),
        next_milestone=(
            f"Next: {selection.node.label} — "
            f"~{estimated} lesson{'s' if estimated != 1 else ''} estimated to next milestone"
        ),
        promotion=WritingJourneyPromotion(
            headline=f"Working toward {target} writing promotion",
            checklist=promotion_checklist,
            eligible_for_level_test=wpa_eligible,
            level_test_label="Writing Promotion Assessment (WPA)",
        ),
        portfolio_teaser=f"Strengths emerging: {', '.join(strong_display)}" if strong_display else "",
        builder_version=BUILDER_VERSION,
    )
    out = bundle.to_student_dict()
    out["meta_builder_version"] = BUILDER_VERSION
    out["next_chain_id"] = selection.chain_id
    out["next_node_id"] = selection.node_id
    out["strong_skills"] = list(strong_display)
    out["lessons_completed_count"] = lessons_count
    out["estimated_lessons_remaining"] = estimated
    out["lessons_today"] = int(state.get("lessons_today") or 0)
    out["learning_stage"] = stage
    out["stage_score"] = stage_result.stage_score
    out["readiness_score"] = readiness.readiness_score
    out["readiness_band"] = readiness.status.value
    out["can_start_wpa"] = wpa_eligible
    out["wpa_reason"] = wpa_reason if not wpa_eligible else ""
    out["primary_blockers"] = list(readiness.primary_blockers)
    out["promotion_target"] = target
    out["stability_prediction"] = stability.prediction
    out["active_wpa_session_id"] = active_wpa.get("session_id") if active_wpa else None
    out["last_wpa_result"] = last_attempt.get("result") if last_attempt else None
    out["promotion"] = {
        **out.get("promotion", {}),
        "readiness_band": readiness.status.value,
        "can_start_test": wpa_eligible,
        "primary_blockers": list(readiness.primary_blockers),
    }
    out["trend"] = {
        "trend_headline": stability.prediction,
        "improvement_areas": list(readiness.primary_blockers[:2]),
        "sustained_skills": list(readiness.strengths[:2]),
    }
    return WritingJourneyBundleOut.model_validate(out)
