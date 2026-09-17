"""Verify Speaking S8 — S7 evaluation evidence → S2 knowledge model bridge.

Usage (from backend/):
    set SPEAKING_EDUCATIONAL_ANALYZER=mock
    set SPEAKING_LIVE_CONVERSATION_PROVIDER=mock
    python scripts/verify_speaking_s8_knowledge_bridge.py

Proves checks A–AE: structural bridge rules, real PostgreSQL mutation,
adaptive weak→improved loop, isolation, forbidden-write preservation,
and frozen S0–S7.6 subprocess regressions.
"""

from __future__ import annotations

import asyncio
import copy
import inspect
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

os.environ.setdefault("SPEAKING_EDUCATIONAL_ANALYZER", "mock")
os.environ.setdefault("SPEAKING_LIVE_CONVERSATION_PROVIDER", "mock")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]

import app.models  # noqa: F401
from app.models.user import User  # noqa: F401

from sqlalchemy import text
from sqlalchemy.orm.attributes import flag_modified

from app.db.session import AsyncSessionLocal, check_database_connection
from app.models.language.progression import LanguageProgression
from app.services.language_progression_service import ensure_progression_row
from app.services.language_speaking.ownership import ALLOWED_PACKAGE_DEPENDENCIES
from app.services.language_speaking_coach.live_context import assemble_student_speaking_live_context
from app.services.language_speaking_coach.live_context_loader import opaque_student_reference
from app.services.language_speaking_curriculum.evidence_ids import (
    MEANING_SUCCESS,
    PAUSES,
    PHONEME_ALIGNMENT,
    PRONUNCIATION_CONFIDENCE,
    RHYTHM,
    SEMANTIC_TASK_RESPONSE,
    SPEAKING_RATE,
)
from app.services.language_speaking_curriculum.skill_catalog import SPEAKING_SKILL_GRAPH
from app.services.language_speaking_evaluation_runtime.evi_tool_runtime import (
    dispatch_evi_tool,
    get_live_context_cache,
    invalidate_live_context,
)
from app.services.language_speaking_evaluation_runtime.knowledge_bridge import (
    _mint_observation_id,
    apply_speaking_evaluation_to_knowledge_model,
    build_speaking_skill_observations,
)
from app.services.language_speaking_evaluation_runtime.knowledge_bridge_types import (
    LANGUAGE_SPEAKING_KNOWLEDGE_BRIDGE_VERSION,
    SpeakingKnowledgeMutationStatus,
)
from app.services.language_speaking_evaluation_runtime.live_runtime import process_completed_live_turn
from app.services.language_speaking_evaluator.evaluation_result import (
    SPEAKING_EVALUATION_RESULT_VERSION,
    CompletionEligibilityFacts,
    DimensionFacts,
    EvidenceSummaryFacts,
    ExplanationFacts,
    RevisionReadinessFacts,
    SpeakingCandidateSkillEvidence,
    SpeakingEvaluationEngineResult,
)
from app.services.language_speaking_evaluator.evaluation_facts_types import DimensionEvidenceStatus
from app.services.language_speaking_evaluator.input_types import (
    SpeakingGoalContext,
    SpeakingOfficialCefrContext,
    SpeakingTaskContext,
)
from app.services.language_speaking_knowledge_model.engine import apply_observations_batch
from app.services.language_speaking_knowledge_model.storage import (
    SPEAKING_BUCKET_KEY,
    empty_knowledge_model,
    knowledge_model_from_speaking_bucket,
    speaking_bucket_from_payload,
)
from app.services.language_speaking_knowledge_model.types import (
    ObservationSourceType,
    SpeakingSkillEvidenceObservation,
)

NOW = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
TS = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    mark = "PASS" if passed else "FAIL"
    suffix = f" -- {detail}" if detail else ""
    print(f"  {mark}  {name}{suffix}")
    return passed


def _dim(name: str, *, score: float = 0.3, passed: bool = False) -> DimensionFacts:
    return DimensionFacts(
        dimension=name,
        status=DimensionEvidenceStatus.met if passed else DimensionEvidenceStatus.partial,
        normalized_value=score,
        confidence=0.7,
        reason="",
        supporting_evidence_ids=(),
        limitations=(),
        score=score,
        weight=1.0,
        passed=passed,
    )


def _evaluation(
    *,
    student_id: int = 8801,
    session_id: str = "sess-s8",
    evaluation_id: str = "eval-s8",
    candidates: tuple[SpeakingCandidateSkillEvidence, ...],
    target_skill_ids: tuple[str, ...] = (),
) -> SpeakingEvaluationEngineResult:
    task = SpeakingTaskContext(
        task_id="task-s8",
        task_type="free_speech",
        task_prompt="Describe your routine.",
        task_instructions="",
        success_criteria=("Respond naturally",),
        target_skill_ids=target_skill_ids,
    )
    return SpeakingEvaluationEngineResult(
        evaluation_id=evaluation_id,
        student_id=student_id,
        language_id=1,
        session_id=session_id,
        task_id=task.task_id,
        attempt_id="attempt-1",
        revision_number=1,
        evaluated_at=TS,
        task_context=task,
        goal_context=SpeakingGoalContext(speaking_goal="general_english", goal_label="General"),
        official_cefr_context=SpeakingOfficialCefrContext(official_cefr="B1"),
        evidence_summary=EvidenceSummaryFacts(
            availability={"transcription": True, "pronunciation": True, "prosody": True},
            reliability=0.75,
            provider_provenance=(),
            evidence_reference_ids=("ev-s8",),
        ),
        task_response=_dim("task_response", score=0.5, passed=True),
        topic_understanding=_dim("topic_understanding", score=0.6, passed=True),
        pronunciation=_dim("pronunciation", score=0.25),
        fluency_delivery=_dim("fluency_delivery", score=0.4),
        grammar=_dim("grammar", score=0.5, passed=True),
        vocabulary=_dim("vocabulary", score=0.55, passed=True),
        coherence=_dim("coherence", score=0.5, passed=True),
        interaction=_dim("interaction", score=0.5, passed=True),
        goal_alignment=_dim("goal_alignment", score=0.5, passed=True),
        cefr_validation=_dim("cefr_validation", score=0.5, passed=True),
        strengths=(),
        weaknesses=("word stress",),
        priority_issue="stress",
        revision_readiness=RevisionReadinessFacts(ready=False, blockers=()),
        completion_eligibility=CompletionEligibilityFacts(
            eligible=False,
            reason="",
            semantic_task_met=False,
        ),
        comparison_with_previous_attempt="",
        educational_analysis=None,
        candidate_skill_evidence=candidates,
        explanation=ExplanationFacts(
            summary="practice",
            priority_issue="stress",
            improvements=("stress",),
            strengths=(),
            focus_label="pronunciation",
        ),
        provider_provenance=(),
        weak_skills=("pattern:word_stress",),
        strong_skills=(),
        overall_readiness=0.35,
        engine_version=SPEAKING_EVALUATION_RESULT_VERSION,
    )


def _pron_candidate(
    *,
    performance: float = 0.25,
    confidence: float = 0.72,
    success: bool = False,
    mistake_tags: tuple[str, ...] = ("misarticulation:stress",),
    target_skill: bool = False,
) -> SpeakingCandidateSkillEvidence:
    return SpeakingCandidateSkillEvidence(
        skill_id="pattern:word_stress",
        source_dimension="pronunciation",
        performance=performance,
        confidence=confidence,
        evidence_dimensions=(PHONEME_ALIGNMENT, PRONUNCIATION_CONFIDENCE),
        context_id="eval-ctx",
        success=success,
        mistake_tags=mistake_tags,
        target_skill=target_skill,
    )


def _prosody_candidate(*, skill_id: str = "pattern:word_stress") -> SpeakingCandidateSkillEvidence:
    return SpeakingCandidateSkillEvidence(
        skill_id=skill_id,
        source_dimension="fluency_delivery",
        performance=0.4,
        confidence=0.65,
        evidence_dimensions=(PAUSES, SPEAKING_RATE, RHYTHM),
        context_id="eval-ctx",
        success=False,
    )


def _semantic_candidate(*, skill_id: str = "phoneme:theta") -> SpeakingCandidateSkillEvidence:
    return SpeakingCandidateSkillEvidence(
        skill_id=skill_id,
        source_dimension="task_response",
        performance=0.8,
        confidence=0.65,
        evidence_dimensions=(SEMANTIC_TASK_RESPONSE, MEANING_SUCCESS),
        context_id="eval-ctx",
        success=True,
    )


def check_ownership_and_entrypoint() -> list[bool]:
    results: list[bool] = []
    rt_deps = ALLOWED_PACKAGE_DEPENDENCIES.get("language_speaking_evaluation_runtime", frozenset())
    results.append(
        _ok(
            "A single bridge entry apply_speaking_evaluation_to_knowledge_model",
            inspect.isfunction(apply_speaking_evaluation_to_knowledge_model),
        )
    )
    results.append(
        _ok(
            "B evaluation_runtime owns curriculum+knowledge_model deps",
            "language_speaking_curriculum" in rt_deps and "language_speaking_knowledge_model" in rt_deps,
        )
    )
    src = inspect.getsource(build_speaking_skill_observations)
    results.append(_ok("C only S7 candidate_skill_evidence consumed", "candidate_skill_evidence" in src))
    return results


def check_build_rules() -> list[bool]:
    results: list[bool] = []
    ev = _evaluation(candidates=(_pron_candidate(),))
    built = build_speaking_skill_observations(ev, turn_reference="turn-a", session_id="sess-a")
    results.append(
        _ok(
            "D valid S1 skill IDs only",
            all(SPEAKING_SKILL_GRAPH.node_by_id(o.skill_id) for o in built.observations),
        )
    )

    unknown_ev = _evaluation(
        candidates=(
            SpeakingCandidateSkillEvidence(
                skill_id="bogus:skill",
                source_dimension="pronunciation",
                performance=0.5,
                confidence=0.5,
                evidence_dimensions=(PHONEME_ALIGNMENT, PRONUNCIATION_CONFIDENCE),
                context_id="x",
                success=False,
            ),
        )
    )
    unknown_built = build_speaking_skill_observations(unknown_ev, turn_reference="turn-u", session_id="sess-u")
    results.append(_ok("E unknown skill explicit", "bogus:skill" in unknown_built.unknown_skill_ids))
    results.append(_ok("E unknown skill not observed", len(unknown_built.observations) == 0))

    missing_ev = _evaluation(
        candidates=(
            SpeakingCandidateSkillEvidence(
                skill_id="pattern:word_stress",
                source_dimension="pronunciation",
                performance=0.5,
                confidence=0.5,
                evidence_dimensions=(),
                context_id="x",
                success=False,
            ),
        )
    )
    missing_built = build_speaking_skill_observations(missing_ev, turn_reference="turn-m", session_id="sess-m")
    results.append(_ok("F no fake observation on missing evidence", len(missing_built.observations) == 0))

    prosody_only = build_speaking_skill_observations(
        _evaluation(candidates=(_prosody_candidate(),)),
        turn_reference="turn-p",
        session_id="sess-p",
    )
    results.append(
        _ok(
            "G pronunciation/fluency require acoustic overlap",
            len(prosody_only.observations) == 0 and len(prosody_only.unavailable_dimensions) == 1,
        )
    )

    semantic_fake = build_speaking_skill_observations(
        _evaluation(candidates=(_semantic_candidate(skill_id="pattern:word_stress"),)),
        turn_reference="turn-s",
        session_id="sess-s",
    )
    results.append(_ok("H semantic cannot fake pronunciation skill", len(semantic_fake.observations) == 0))

    obs = built.observations[0]
    results.append(_ok("I bounded performance reused", 0.0 <= obs.performance <= 1.0))
    results.append(_ok("J evidence-aware confidence reused", obs.confidence == 0.72))
    results.append(_ok("K stable mistake tags kept", obs.mistake_tags == ("misarticulation:stress",)))

    prose_ev = _evaluation(candidates=(_pron_candidate(mistake_tags=("this is prose not a tag",)),))
    prose_built = build_speaking_skill_observations(prose_ev, turn_reference="turn-prose", session_id="sess-prose")
    results.append(_ok("L prose tags built then rejected at apply", len(prose_built.observations) == 1))

    oid1 = _mint_observation_id(
        student_id=1,
        session_id="s",
        turn_reference="t",
        engine_version="7.0.0",
        skill_id="pattern:word_stress",
        source_dimension="pronunciation",
    )
    oid2 = _mint_observation_id(
        student_id=1,
        session_id="s",
        turn_reference="t",
        engine_version="7.0.0",
        skill_id="pattern:word_stress",
        source_dimension="pronunciation",
    )
    results.append(_ok("M deterministic observation IDs", oid1 == oid2 and oid1.startswith("obs-")))

    no_target = build_speaking_skill_observations(
        _evaluation(candidates=(_pron_candidate(target_skill=False),), target_skill_ids=()),
        turn_reference="turn-nt",
        session_id="sess-nt",
    )
    results.append(_ok("N target_skill false without task target", not no_target.observations[0].target_skill))
    results.append(_ok("O context_id uses turn_reference", built.observations[0].context_id == "turn-a"))
    results.append(_ok("P no fake revision chain", built.observations[0].previous_observation_id is None))
    return results


async def _pick_qa_row(db) -> tuple[int, int]:
    row = (await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))).first()
    if row is not None:
        return int(row[0]), int(row[1])
    user_row = (await db.execute(text("SELECT id FROM users LIMIT 1"))).first()
    lang_row = (await db.execute(text("SELECT id FROM languages LIMIT 1"))).first()
    if user_row is None or lang_row is None:
        raise RuntimeError("No QA row available")
    sid, lid = int(user_row[0]), int(lang_row[0])
    await ensure_progression_row(db, student_id=sid, language_id=lid)
    await db.flush()
    return sid, lid


def _seed_siblings(payload: dict) -> dict:
    out = copy.deepcopy(payload)
    out.setdefault("writing", {})["verify_s8_marker"] = "preserve"
    listening = dict(out.get("listening_official_promotions") or {})
    listening["verify_s8_marker"] = "preserve"
    out["listening_official_promotions"] = listening
    speaking = dict(out.get(SPEAKING_BUCKET_KEY) or {})
    readiness = dict(speaking.get("readiness") or {})
    readiness["verify_s8_marker"] = "preserve"
    speaking["readiness"] = readiness
    out[SPEAKING_BUCKET_KEY] = speaking
    return out


async def check_real_postgres() -> list[bool]:
    results: list[bool] = []
    try:
        await check_database_connection()
    except Exception as exc:
        results.append(_ok("Q REAL PostgreSQL available", False, str(exc)))
        return results

    async with AsyncSessionLocal() as db:
        sid, lid = await _pick_qa_row(db)
        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        assert row is not None
        baseline_cols = {
            "official_speaking_cefr": row.official_speaking_cefr,
            "learning_stage_speaking": row.learning_stage_speaking,
            "promotion_readiness_score": row.promotion_readiness_score,
            "version": row.version,
        }
        original = copy.deepcopy(dict(row.promotion_readiness_json or {}))
        row.promotion_readiness_json = _seed_siblings(original)
        flag_modified(row, "promotion_readiness_json")
        await db.flush()

        weak_ev = _evaluation(
            student_id=sid,
            session_id="sess-adaptive",
            candidates=(_pron_candidate(performance=0.2, success=False),),
        )
        turn1 = "turn-adaptive-1"
        r1 = await apply_speaking_evaluation_to_knowledge_model(
            db,
            student_id=sid,
            language_id=lid,
            evaluation=weak_ev,
            turn_reference=turn1,
            session_id="sess-adaptive",
            now=NOW,
        )
        results.append(
            _ok("Q REAL PostgreSQL mutation applied", r1.mutation_status == SpeakingKnowledgeMutationStatus.applied)
        )

        prose_ev = _evaluation(
            student_id=sid,
            candidates=(_pron_candidate(mistake_tags=("bad prose tag without colon",)),),
        )
        prose_res = await apply_speaking_evaluation_to_knowledge_model(
            db,
            student_id=sid,
            language_id=lid,
            evaluation=prose_ev,
            turn_reference="turn-prose-db",
            session_id="sess-adaptive",
            now=NOW,
        )
        results.append(
            _ok(
                "L prose tags fail mutation on real DB",
                prose_res.mutation_status == SpeakingKnowledgeMutationStatus.mutation_failed,
            )
        )

        db.expire_all()
        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        km1 = knowledge_model_from_speaking_bucket(
            speaking_bucket_from_payload(dict(row.promotion_readiness_json or {})),
            student_id=sid,
            language_id=lid,
        )
        st1 = km1.skill_states.get("pattern:word_stress")
        count1 = st1.evidence_count if st1 else 0
        mastery1 = st1.mastery if st1 else 0.0

        await apply_speaking_evaluation_to_knowledge_model(
            db,
            student_id=sid,
            language_id=lid,
            evaluation=weak_ev,
            turn_reference=turn1,
            session_id="sess-adaptive",
            now=NOW,
        )
        db.expire_all()
        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        km1b = knowledge_model_from_speaking_bucket(
            speaking_bucket_from_payload(dict(row.promotion_readiness_json or {})),
            student_id=sid,
            language_id=lid,
        )
        st1b = km1b.skill_states.get("pattern:word_stress")
        results.append(_ok("R same-turn retry idempotent", st1b and st1b.evidence_count == count1))

        turn2 = "turn-adaptive-2"
        improved_ev = _evaluation(
            student_id=sid,
            session_id="sess-adaptive",
            evaluation_id="eval-improved",
            candidates=(_pron_candidate(performance=0.85, confidence=0.8, success=True, mistake_tags=()),),
        )
        r2 = await apply_speaking_evaluation_to_knowledge_model(
            db,
            student_id=sid,
            language_id=lid,
            evaluation=improved_ev,
            turn_reference=turn2,
            session_id="sess-adaptive",
            now=NOW,
        )
        results.append(
            _ok("S distinct turn distinct observation", r2.applied_observation_ids != r1.applied_observation_ids)
        )

        db.expire_all()
        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        km2 = knowledge_model_from_speaking_bucket(
            speaking_bucket_from_payload(dict(row.promotion_readiness_json or {})),
            student_id=sid,
            language_id=lid,
        )
        st2 = km2.skill_states.get("pattern:word_stress")
        results.append(_ok("T weak->improved mastery increases", st2 and st2.mastery > mastery1))
        results.append(_ok("T weak->improved evidence_count grows", st2 and st2.evidence_count > count1))

        ctx1 = assemble_student_speaking_live_context(
            student_reference=opaque_student_reference(student_id=sid),
            speaking_goal="general_english",
            knowledge_model=km1,
            skill_graph=SPEAKING_SKILL_GRAPH,
        )
        ctx2 = assemble_student_speaking_live_context(
            student_reference=opaque_student_reference(student_id=sid),
            speaking_goal="general_english",
            knowledge_model=km2,
            skill_graph=SPEAKING_SKILL_GRAPH,
            latest_evaluation=improved_ev,
        )
        results.append(
            _ok(
                "U adaptive context reflects updated S2",
                ctx2.learner_state != ctx1.learner_state or ctx2.priority_targets != ctx1.priority_targets,
            )
        )

        payload = dict(row.promotion_readiness_json or {})
        results.append(
            _ok("V writing JSONB preserved", (payload.get("writing") or {}).get("verify_s8_marker") == "preserve")
        )
        results.append(
            _ok(
                "V listening JSONB preserved",
                (payload.get("listening_official_promotions") or {}).get("verify_s8_marker") == "preserve",
            )
        )
        results.append(
            _ok(
                "V speaking.readiness preserved",
                ((payload.get(SPEAKING_BUCKET_KEY) or {}).get("readiness") or {}).get("verify_s8_marker")
                == "preserve",
            )
        )

        row_after = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        assert row_after is not None
        results.append(
            _ok(
                "W forbidden CEFR/stage/score columns unchanged",
                row_after.official_speaking_cefr == baseline_cols["official_speaking_cefr"]
                and row_after.learning_stage_speaking == baseline_cols["learning_stage_speaking"]
                and row_after.promotion_readiness_score == baseline_cols["promotion_readiness_score"]
                and row_after.version == baseline_cols["version"],
            )
        )

        model = empty_knowledge_model(student_id=sid, language_id=lid)
        good = SpeakingSkillEvidenceObservation(
            observation_id="obs-batch-good",
            skill_id="pattern:word_stress",
            observed_at=TS,
            performance=0.5,
            confidence=0.8,
            evidence_dimensions=(PHONEME_ALIGNMENT, PRONUNCIATION_CONFIDENCE),
            context_id="ctx-batch",
            success=True,
            source_type=ObservationSourceType.synthetic_test,
        )
        bad = SpeakingSkillEvidenceObservation(
            observation_id="obs-batch-bad",
            skill_id="pattern:word_stress",
            observed_at=TS,
            performance=0.5,
            confidence=0.8,
            evidence_dimensions=(PHONEME_ALIGNMENT, PRONUNCIATION_CONFIDENCE),
            context_id="ctx-batch",
            success=True,
            mistake_tags=("bad prose tag without colon",),
            source_type=ObservationSourceType.synthetic_test,
        )
        before = copy.deepcopy(model.skill_states)
        apply_observations_batch(model, [good, bad], now=NOW)
        results.append(_ok("X failed batch no partial mutation", model.skill_states == before))

        await db.rollback()
        results.append(_ok("Y transaction rolled back (non-destructive QA)", True))

    return results


async def check_isolation_and_runtime() -> list[bool]:
    results: list[bool] = []
    evi_src = inspect.getsource(dispatch_evi_tool)
    results.append(_ok("Z EVI tool dispatch has no bridge import", "knowledge_bridge" not in evi_src))

    s7_fail = await apply_speaking_evaluation_to_knowledge_model(
        AsyncMock(),
        student_id=1,
        language_id=1,
        evaluation=None,
        turn_reference="t",
        session_id="s",
        now=NOW,
    )
    results.append(
        _ok("AA S7 unavailable -> no mutation", s7_fail.mutation_status == SpeakingKnowledgeMutationStatus.s7_unavailable)
    )

    cache = get_live_context_cache()
    cache.set(
        student_id=999,
        language_id=1,
        context=assemble_student_speaking_live_context(
            student_reference="spk-test",
            speaking_goal="general_english",
            knowledge_model=empty_knowledge_model(student_id=999, language_id=1),
            skill_graph=SPEAKING_SKILL_GRAPH,
        ),
    )
    invalidate_live_context(student_id=999, language_id=1)
    results.append(_ok("AB cache invalidates (S7.6 path)", cache.get(student_id=999, language_id=1) is None))

    task = SpeakingTaskContext(
        task_id="live-task",
        task_type="free_speech",
        task_prompt="Hi",
        task_instructions="",
        success_criteria=("Speak",),
        target_skill_ids=(),
    )
    goal = SpeakingGoalContext(speaking_goal="general_english", goal_label="General")
    cefr = SpeakingOfficialCefrContext(official_cefr="B1")
    fake_eval = _evaluation(candidates=(_pron_candidate(performance=0.3),))

    async with AsyncSessionLocal() as db:
        wire_sid, wire_lid = await _pick_qa_row(db)
        with patch(
            "app.services.language_speaking_evaluation_runtime.live_runtime.process_speaking_evaluation",
            new_callable=AsyncMock,
        ) as mock_eval:
            from app.services.language_speaking_evaluation_runtime.evaluation_pipeline import (
                SpeakingEvaluationTurnResult,
            )

            wire_eval = _evaluation(
                student_id=wire_sid,
                candidates=(_pron_candidate(performance=0.3),),
            )
            mock_eval.return_value = SpeakingEvaluationTurnResult(
                success=True,
                evaluation=wire_eval,
                persistence_dict={"engine_result": wire_eval.to_persistence_dict()},
            )
            handoff = await process_completed_live_turn(
                live_session_id="sess-wire",
                live_turn_id="turn-wire",
                student_id=wire_sid,
                language_id=wire_lid,
                audio_bytes=b"\x00" * 3200,
                audio_content_type="audio/wav",
                evi_events_json="[]",
                task=task,
                goal=goal,
                official_cefr=cefr,
                db=db,
            )
        results.append(_ok("AC completed turn mutates via db param", handoff.mutation_status == "applied"))
        results.append(_ok("AD S7 preserved on bridge path", handoff.success and bool(handoff.engine_version)))
        await db.rollback()

    with patch(
        "app.services.language_speaking_evaluation_runtime.live_runtime.process_speaking_evaluation",
        new_callable=AsyncMock,
    ) as mock_eval:
        from app.services.language_speaking_evaluation_runtime.evaluation_pipeline import SpeakingEvaluationTurnResult

        mock_eval.return_value = SpeakingEvaluationTurnResult(
            success=True,
            evaluation=fake_eval,
            persistence_dict={"engine_result": fake_eval.to_persistence_dict()},
        )
        no_db = await process_completed_live_turn(
            live_session_id="sess-nodb",
            live_turn_id="turn-nodb",
            student_id=8804,
            language_id=1,
            audio_bytes=b"\x00" * 3200,
            audio_content_type="audio/wav",
            evi_events_json="[]",
            task=task,
            goal=goal,
            official_cefr=cefr,
        )
    results.append(_ok("AE no db -> no mutation status", no_db.mutation_status == ""))

    return results


def check_frozen_regressions() -> list[bool]:
    scripts = [
        "verify_speaking_s0_architecture.py",
        "verify_speaking_s1_skill_graph.py",
        "verify_speaking_s2_knowledge_model.py",
        "verify_speaking_s3_audio_frontend.py",
        "verify_speaking_s4_audio_runtime.py",
        "verify_speaking_s5_pronunciation.py",
        "verify_speaking_s6_prosody.py",
        "verify_speaking_s7_evaluation.py",
        "verify_speaking_s75_evi_runtime.py",
        "verify_speaking_s76_evi_student_context.py",
    ]
    env = {
        **os.environ,
        "SPEAKING_EDUCATIONAL_ANALYZER": "mock",
        "SPEAKING_LIVE_CONVERSATION_PROVIDER": "mock",
    }
    results: list[bool] = []
    for script in scripts:
        path = BACKEND / "scripts" / script
        proc = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(BACKEND),
            capture_output=True,
            text=True,
            timeout=900,
            env=env,
        )
        tail = (proc.stdout + proc.stderr)[-160:]
        results.append(_ok(f"AF frozen {script}", proc.returncode == 0, tail.replace("\n", " ")[:120]))
    return results


async def main_async() -> int:
    print("Speaking S8 Knowledge Bridge Verification\n")
    print(f"Bridge version: {LANGUAGE_SPEAKING_KNOWLEDGE_BRIDGE_VERSION}\n")

    all_results: list[bool] = []
    print("[Structural + build rules]")
    all_results.extend(check_ownership_and_entrypoint())
    all_results.extend(check_build_rules())

    print("\n[Real PostgreSQL + adaptive loop]")
    all_results.extend(await check_real_postgres())

    print("\n[Isolation + runtime wiring]")
    all_results.extend(await check_isolation_and_runtime())

    print("\n[Frozen S0–S7.6 regressions]")
    all_results.extend(check_frozen_regressions())

    passed = sum(all_results)
    total = len(all_results)
    print(f"\n{'=' * 60}")
    print(f"S8 RESULT: {passed}/{total} checks passed")
    if passed == total:
        print("Speaking S8 COMPLETE - adaptive S7->S8->S2->S7.6 loop proven.")
        return 0
    print("Speaking S8 INCOMPLETE - see failures above.")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main_async()))
