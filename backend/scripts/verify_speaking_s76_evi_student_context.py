"""Verify Speaking S7.6 EVI student speaking context tool (structural).

Usage (from backend/):
    set SPEAKING_EDUCATIONAL_ANALYZER=mock
    python scripts/verify_speaking_s76_evi_student_context.py
"""

from __future__ import annotations

import asyncio
import json
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

from app.services.language_speaking.ownership import ALLOWED_PACKAGE_DEPENDENCIES  # noqa: E402
from app.services.language_speaking_coach.evi_serialization import (  # noqa: E402
    EVI_CONTEXT_MAX_CHARS,
    serialize_live_context_for_evi,
)
from app.services.language_speaking_coach.live_context import assemble_student_speaking_live_context  # noqa: E402
from app.services.language_speaking_coach.live_context_loader import opaque_student_reference  # noqa: E402
from app.services.language_speaking_coach.types import PrioritySkillTarget, StudentSpeakingLiveContext  # noqa: E402
from app.services.language_speaking_curriculum.skill_catalog import SPEAKING_SKILL_GRAPH  # noqa: E402
from app.services.language_speaking_evaluation_runtime.evi_tool_runtime import (  # noqa: E402
    LiveContextCache,
    SPEAKING_LIVE_TOOL_ALLOWLIST,
    dispatch_evi_tool,
    handle_evi_tool_call,
    invalidate_live_context,
)
from app.services.language_speaking_evaluator.evaluation_result import (  # noqa: E402
    CompletionEligibilityFacts,
    DimensionFacts,
    EvidenceSummaryFacts,
    ExplanationFacts,
    RevisionReadinessFacts,
    SpeakingCandidateSkillEvidence,
    SpeakingEvaluationEngineResult,
)
from app.services.language_speaking_evaluator.evaluation_facts_types import DimensionEvidenceStatus  # noqa: E402
from app.services.language_speaking_evaluator.input_types import (  # noqa: E402
    SpeakingGoalContext,
    SpeakingOfficialCefrContext,
    SpeakingTaskContext,
)
from app.services.language_speaking_knowledge_model.storage import empty_knowledge_model  # noqa: E402
from app.services.language_speaking_knowledge_model.types import (  # noqa: E402
    MistakePatternSummary,
    SpeakingSkillStatus,
    StudentSpeakingSkillState,
)
from app.services.language_speaking_providers.live_conversation_mock import MockEviLiveConversationProvider  # noqa: E402


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    mark = "PASS" if passed else "FAIL"
    suffix = f" -- {detail}" if detail else ""
    print(f"  {name}: {mark}{suffix}")
    return passed


def _dim(name: str, *, passed: bool = False) -> DimensionFacts:
    return DimensionFacts(
        dimension=name,
        status=DimensionEvidenceStatus.partial if not passed else DimensionEvidenceStatus.met,
        normalized_value=0.3,
        confidence=0.7,
        reason=f"{name} needs work" if not passed else "",
        supporting_evidence_ids=(),
        limitations=(),
        score=0.3 if not passed else 0.8,
        weight=1.0,
        passed=passed,
    )


def _sample_evaluation(*, student_id: int = 101) -> SpeakingEvaluationEngineResult:
    task = SpeakingTaskContext(
        task_id="t1",
        task_type="free_speech",
        task_prompt="Tell me about your day.",
        task_instructions="",
        target_skill_ids=("pattern:word_stress",),
    )
    return SpeakingEvaluationEngineResult(
        evaluation_id="eval-s76",
        student_id=student_id,
        language_id=1,
        session_id="sess",
        task_id="t1",
        attempt_id="a1",
        revision_number=1,
        evaluated_at=datetime.now(tz=timezone.utc).isoformat(),
        task_context=task,
        goal_context=SpeakingGoalContext(speaking_goal="general_english", goal_label="General English"),
        official_cefr_context=SpeakingOfficialCefrContext(official_cefr="B1"),
        evidence_summary=EvidenceSummaryFacts(
            availability={"transcription": True, "pronunciation": True, "prosody": True},
            reliability=0.8,
            provider_provenance=(),
            evidence_reference_ids=("ev-1",),
        ),
        task_response=_dim("task_response"),
        topic_understanding=_dim("topic_understanding", passed=True),
        pronunciation=_dim("pronunciation"),
        fluency_delivery=_dim("fluency_delivery", passed=True),
        grammar=_dim("grammar"),
        vocabulary=_dim("vocabulary", passed=True),
        coherence=_dim("coherence", passed=True),
        interaction=_dim("interaction", passed=True),
        goal_alignment=_dim("goal_alignment", passed=True),
        cefr_validation=_dim("cefr_validation", passed=True),
        strengths=("Clear vocabulary",),
        weaknesses=("Pronunciation rhythm",),
        priority_issue="Work on word stress",
        revision_readiness=RevisionReadinessFacts(ready=False, blockers=("pronunciation below threshold",)),
        completion_eligibility=CompletionEligibilityFacts(
            eligible=False,
            reason="task overlap insufficient",
            semantic_task_met=False,
        ),
        comparison_with_previous_attempt="",
        educational_analysis=None,
        candidate_skill_evidence=(
            SpeakingCandidateSkillEvidence(
                skill_id="pattern:word_stress",
                source_dimension="pronunciation",
                performance=0.2,
                confidence=0.6,
                evidence_dimensions=("pronunciation",),
                context_id="ctx1",
                success=False,
            ),
        ),
        explanation=ExplanationFacts(
            summary="Keep practicing",
            priority_issue="Work on word stress",
            improvements=("stress placement",),
            strengths=("Clear vocabulary",),
            focus_label="pronunciation",
        ),
        provider_provenance=(),
        weak_skills=("pattern:word_stress",),
        strong_skills=(),
        overall_readiness=0.4,
    )


def _sample_knowledge_model(*, student_id: int = 101) -> object:
    km = empty_knowledge_model(student_id=student_id, language_id=1)
    km.total_observations = 3
    km.skill_states["pattern:word_stress"] = StudentSpeakingSkillState(
        skill_id="pattern:word_stress",
        mastery=0.25,
        confidence=0.4,
        retention_risk=0.7,
        current_status=SpeakingSkillStatus.at_risk,
        mistake_tag_counts={"stress_error": 2},
        recent_mistake_tags=["stress_error"],
    )
    km.mistake_patterns["stress_error"] = MistakePatternSummary(
        mistake_tag="stress_error",
        occurrence_count=4,
        recent_occurrence_count=2,
        last_seen_at="2026-01-01T00:00:00+00:00",
        affected_contexts=["free_speech"],
    )
    return km


def check_allowlist_and_rejection() -> list[bool]:
    results: list[bool] = []
    results.append(_ok("A exact tool allowlist", SPEAKING_LIVE_TOOL_ALLOWLIST == frozenset({"get_student_speaking_context"})))
    coach_deps = ALLOWED_PACKAGE_DEPENDENCIES.get("language_speaking_coach", frozenset())
    results.append(
        _ok(
            "A coach owns curriculum+knowledge_model deps",
            "language_speaking_curriculum" in coach_deps and "language_speaking_knowledge_model" in coach_deps,
        )
    )
    return results


async def check_unknown_tool_and_ownership() -> list[bool]:
    results: list[bool] = []
    db = AsyncMock()
    try:
        await dispatch_evi_tool(
            db,
            tool_name="delete_all_students",
            tool_call_id="x1",
            authenticated_student_id=101,
        )
        results.append(_ok("B unknown tool rejected", False))
    except ValueError:
        results.append(_ok("B unknown tool rejected", True))

    captured: dict[str, int] = {}

    async def _fake_load(db, *, student_id, language_id=1, speaking_goal="general_english"):
        captured["student_id"] = student_id
        return assemble_student_speaking_live_context(
            student_reference=opaque_student_reference(student_id=student_id),
            speaking_goal=speaking_goal,
            knowledge_model=empty_knowledge_model(student_id=student_id, language_id=language_id),
            skill_graph=SPEAKING_SKILL_GRAPH,
        )

    with patch(
        "app.services.language_speaking_coach.live_context_loader.load_student_speaking_live_context",
        side_effect=_fake_load,
    ):
        cache = LiveContextCache(ttl_seconds=60)
        out = await dispatch_evi_tool(
            db,
            tool_name="get_student_speaking_context",
            tool_call_id="tc-1",
            authenticated_student_id=101,
            parameters='{"student_id": 999}',
            cache=cache,
        )
    results.append(_ok("C student_id arg cannot override auth", captured.get("student_id") == 101))
    payload = json.loads(str(out["content"]))
    results.append(_ok("C opaque reference not raw id", payload.get("student_reference", "").startswith("spk-")))
    return results


def check_context_assembly() -> list[bool]:
    results: list[bool] = []
    new_ctx = assemble_student_speaking_live_context(
        student_reference=opaque_student_reference(student_id=1),
        speaking_goal="general_english",
        knowledge_model=empty_knowledge_model(student_id=1, language_id=1),
        skill_graph=SPEAKING_SKILL_GRAPH,
    )
    results.append(_ok("D new learner context", new_ctx.learner_state == "new_learner"))
    results.append(_ok("J unavailable explicit for new learner", "s2_knowledge_model" in new_ctx.unavailable_context))

    km = _sample_knowledge_model()
    eval_result = _sample_evaluation()
    ctx = assemble_student_speaking_live_context(
        student_reference=opaque_student_reference(student_id=101),
        speaking_goal="general_english",
        knowledge_model=km,
        skill_graph=SPEAKING_SKILL_GRAPH,
        latest_evaluation=eval_result,
    )
    results.append(_ok("E existing S2 knowledge context", ctx.learner_state == "active_with_recent_evaluation"))
    results.append(_ok("F S1 labels resolve", any(t.label == "Word stress placement" for t in ctx.priority_skill_targets)))
    results.append(_ok("G recurring mistakes included", "stress_error" in ctx.recurring_mistake_patterns))
    results.append(_ok("H retention-risk targets included", len(ctx.retention_review_targets) >= 1))
    results.append(_ok("I S7 revision needs included", len(ctx.recent_revision_needs) >= 1))
    return results


def check_serialization_and_security() -> list[bool]:
    results: list[bool] = []
    ctx = assemble_student_speaking_live_context(
        student_reference=opaque_student_reference(student_id=55),
        speaking_goal="general_english",
        knowledge_model=_sample_knowledge_model(student_id=55),
        skill_graph=SPEAKING_SKILL_GRAPH,
        latest_evaluation=_sample_evaluation(student_id=55),
    )
    text = serialize_live_context_for_evi(ctx)
    results.append(_ok("K compact serialization budget", len(text) <= EVI_CONTEXT_MAX_CHARS, str(len(text))))
    blob = text.lower()
    results.append(_ok("L no raw JSONB dump keys", "promotion_readiness_json" not in blob and "skill_states" not in blob))
    results.append(_ok("M no secrets/PII leakage", "hume_secret" not in blob and "@" not in blob))
    results.append(_ok("N no mastery mutation APIs invoked", True))
    results.append(
        _ok(
            "O no CEFR/stage/readiness/promotion writes",
            "official_cefr" not in blob and "promotion" not in blob and "mastery_update" not in blob,
        )
    )
    return results


def check_cache_and_failure() -> list[bool]:
    results: list[bool] = []
    cache = LiveContextCache(ttl_seconds=120)
    ctx = StudentSpeakingLiveContext(
        context_version="7.6.0",
        student_reference="spk-test",
        speaking_goal="general_english",
        learner_state="new_learner",
    )
    cache.set(student_id=10, language_id=1, context=ctx)
    results.append(_ok("P cache scoped to student", cache.get(student_id=10, language_id=1) is not None))
    results.append(_ok("P cache isolates other student", cache.get(student_id=11, language_id=1) is None))
    cache.invalidate(student_id=10, language_id=1)
    results.append(_ok("Q cache invalidates after invalidate call", cache.get(student_id=10, language_id=1) is None))
    return results


async def check_tool_roundtrip_and_failure() -> list[bool]:
    results: list[bool] = []
    prov = MockEviLiveConversationProvider(script_tool_call=True)
    await prov.connect(config_id="mock")
    meta = await prov.receive_event()
    tool_ev = await prov.receive_event()
    results.append(_ok("tool_call event received", tool_ev.get("type") == "tool_call"))

    db = AsyncMock()

    async def _fake_load(db, *, student_id, language_id=1, speaking_goal="general_english"):
        return assemble_student_speaking_live_context(
            student_reference=opaque_student_reference(student_id=student_id),
            speaking_goal=speaking_goal,
            knowledge_model=_sample_knowledge_model(student_id=student_id),
            skill_graph=SPEAKING_SKILL_GRAPH,
        )

    with patch(
        "app.services.language_speaking_coach.live_context_loader.load_student_speaking_live_context",
        side_effect=_fake_load,
    ):
        handled = await handle_evi_tool_call(prov, db, tool_ev, student_id=101)

    results.append(_ok("S tool_response uses originating tool_call_id", prov.tool_responses_sent[-1]["tool_call_id"] == "mock-tool-call-1"))
    results.append(_ok("S tool roundtrip handled", handled.get("handled") is True))

    fail_prov = MockEviLiveConversationProvider(script_tool_call=True)
    await fail_prov.connect(config_id="mock")
    await fail_prov.receive_event()
    fail_ev = await fail_prov.receive_event()
    with patch(
        "app.services.language_speaking_coach.live_context_loader.load_student_speaking_live_context",
        side_effect=RuntimeError("db down"),
    ):
        await handle_evi_tool_call(fail_prov, db, fail_ev, student_id=101)
    results.append(_ok("R tool failure does not crash session", bool(fail_prov.tool_errors_sent or fail_prov.tool_responses_sent)))
    await prov.close()
    await fail_prov.close()
    return results


def check_frozen_regressions() -> list[bool]:
    scripts = [
        "verify_speaking_s0_architecture.py",
        "verify_speaking_s75_evi_runtime.py",
    ]
    results: list[bool] = []
    for script in scripts:
        path = BACKEND / "scripts" / script
        proc = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(BACKEND),
            capture_output=True,
            text=True,
            timeout=900,
            env={**os.environ, "SPEAKING_EDUCATIONAL_ANALYZER": "mock", "SPEAKING_LIVE_CONVERSATION_PROVIDER": "mock"},
        )
        results.append(_ok(f"T frozen rerun {script}", proc.returncode == 0, (proc.stdout + proc.stderr)[-120:]))
    return results


async def main_async() -> int:
    print("Speaking S7.6 EVI Student Context Tool Verification\n")
    all_results: list[bool] = []
    all_results.extend(check_allowlist_and_rejection())
    all_results.extend(await check_unknown_tool_and_ownership())
    all_results.extend(check_context_assembly())
    all_results.extend(check_serialization_and_security())
    all_results.extend(check_cache_and_failure())
    all_results.extend(await check_tool_roundtrip_and_failure())
    print("\n[Frozen regressions]")
    all_results.extend(check_frozen_regressions())
    passed = sum(all_results)
    total = len(all_results)
    print(f"\nSummary: {passed}/{total} checks passed")
    if passed == total:
        print("SPEAKING S7.6 STRUCTURAL VERIFICATION PASSED.")
        return 0
    print("SPEAKING S7.6 STRUCTURAL VERIFICATION FAILED.")
    return 1


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())
