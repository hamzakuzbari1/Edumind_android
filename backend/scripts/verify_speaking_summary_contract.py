"""Verify Speaking student session summary contract (render-only, safe fields)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.language_speaking.ownership import ALLOWED_PACKAGE_DEPENDENCIES, PACKAGE_LAYER
from app.services.language_speaking_evaluator.evaluation_facts_types import DimensionEvidenceStatus
from app.services.language_speaking_evaluator.evaluation_result import (
    CompletionEligibilityFacts,
    DimensionFacts,
    EvidenceSummaryFacts,
    ExplanationFacts,
    RevisionReadinessFacts,
    SpeakingEvaluationEngineResult,
)
from app.services.language_speaking_evaluator.input_types import (
    SpeakingGoalContext,
    SpeakingOfficialCefrContext,
    SpeakingTaskContext,
)
from app.services.language_speaking_explainability.student_session_summary import (
    build_speaking_student_session_summary,
)

NOW = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
UNSAFE_KEYS = frozenset(
    {
        "score",
        "weight",
        "confidence",
        "normalized_value",
        "overall_readiness",
        "skill_id",
        "observation_id",
        "mutation_status",
        "engine_version",
        "evaluation_id",
        "student_id",
        "evidence_reference_ids",
        "provider_provenance",
        "candidate_skill_evidence",
    }
)


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    mark = "PASS" if passed else "FAIL"
    suffix = f" -- {detail}" if detail else ""
    print(f"  {mark}  {name}{suffix}")
    return passed


def _dim(name: str, *, passed: bool = True, reason: str = "Good effort") -> DimensionFacts:
    return DimensionFacts(
        dimension=name,
        status=DimensionEvidenceStatus.met if passed else DimensionEvidenceStatus.partial,
        normalized_value=0.82 if passed else 0.31,
        confidence=0.91,
        reason=reason,
        supporting_evidence_ids=("ev-secret-1",),
        limitations=(),
        score=0.82 if passed else 0.31,
        weight=1.0,
        passed=passed,
    )


def _sample_evaluation() -> SpeakingEvaluationEngineResult:
    task = SpeakingTaskContext(
        task_id="task-summary",
        task_type="free_speech",
        task_prompt="Describe your routine.",
        task_instructions="",
        success_criteria=("Respond naturally",),
        target_skill_ids=(),
    )
    return SpeakingEvaluationEngineResult(
        evaluation_id="eval-secret",
        student_id=42,
        language_id=1,
        session_id="sess-secret",
        task_id=task.task_id,
        attempt_id="attempt-1",
        revision_number=1,
        evaluated_at=NOW.isoformat(),
        task_context=task,
        goal_context=SpeakingGoalContext(speaking_goal="general_english", goal_label="General"),
        official_cefr_context=SpeakingOfficialCefrContext(official_cefr="B1"),
        evidence_summary=EvidenceSummaryFacts(
            availability={"transcription": True},
            reliability=0.88,
            provider_provenance=({"provider": "secret"},),
            evidence_reference_ids=("ev-ref-1",),
        ),
        task_response=_dim("task_response"),
        topic_understanding=_dim("topic_understanding"),
        pronunciation=_dim("pronunciation", passed=False, reason="Work on word stress"),
        fluency_delivery=_dim("fluency_delivery"),
        grammar=_dim("grammar"),
        vocabulary=_dim("vocabulary"),
        coherence=_dim("coherence"),
        interaction=_dim("interaction"),
        goal_alignment=_dim("goal_alignment"),
        cefr_validation=_dim("cefr_validation"),
        strengths=("Clear vocabulary",),
        weaknesses=("Word stress",),
        priority_issue="stress",
        revision_readiness=RevisionReadinessFacts(ready=False, blockers=("pronunciation",)),
        completion_eligibility=CompletionEligibilityFacts(
            eligible=False,
            reason="Keep practicing pronunciation",
            semantic_task_met=True,
        ),
        comparison_with_previous_attempt="You are improving on fluency.",
        educational_analysis=None,
        candidate_skill_evidence=(),
        explanation=ExplanationFacts(
            summary="Nice natural conversation.",
            priority_issue="Focus on word stress",
            improvements=("Stress placement", "Pause less"),
            strengths=("Clear vocabulary", "Good grammar"),
            focus_label="pronunciation",
        ),
        provider_provenance=({"provider": "secret"},),
        weak_skills=("pattern:word_stress",),
        strong_skills=("grammar:present",),
        overall_readiness=0.42,
        engine_version="7.0.0",
    )


def _collect_keys(obj, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(k)
            keys |= _collect_keys(v, f"{prefix}.{k}")
    elif isinstance(obj, list):
        for item in obj:
            keys |= _collect_keys(item, prefix)
    return keys


def main() -> int:
    print("Speaking Student Session Summary Contract Verification\n")
    results: list[bool] = []

    deps = ALLOWED_PACKAGE_DEPENDENCIES.get("language_speaking_explainability", frozenset())
    results.append(_ok("ownership explainability -> evaluator only", deps == frozenset({"language_speaking_evaluator"})))
    results.append(_ok("layer is facts", PACKAGE_LAYER.get("language_speaking_explainability") == "facts"))

    ev = _sample_evaluation()
    summary = build_speaking_student_session_summary(ev)
    payload = summary.to_student_dict()

    results.append(_ok("deterministic builder", summary.coach_summary == "Nice natural conversation."))
    results.append(_ok("includes safe prose strengths", "Clear vocabulary" in payload["strengths"]))
    results.append(_ok("dimension status collapsed", payload["dimensions"][2]["status"] == "needs_work"))
    results.append(_ok("dimension reason prose only", "stress" in str(payload["dimensions"][2]["reason"]).lower()))

    all_keys = _collect_keys(payload)
    leaked = all_keys & UNSAFE_KEYS
    results.append(_ok("no unsafe keys in student dict", not leaked, ", ".join(sorted(leaked)) if leaked else ""))

    blob = json.dumps(payload)
    results.append(_ok("no raw skill IDs in JSON", "pattern:word_stress" not in blob))
    results.append(_ok("no evaluation_id in JSON", "eval-secret" not in blob))
    results.append(_ok("no overall_readiness decimal", "0.42" not in blob))
    results.append(_ok("no confidence decimal", "0.91" not in blob))

    rt_deps = ALLOWED_PACKAGE_DEPENDENCIES.get("language_speaking_evaluation_runtime", frozenset())
    results.append(
        _ok(
            "evaluation_runtime may import explainability",
            "language_speaking_explainability" in rt_deps,
        )
    )

    passed = sum(results)
    total = len(results)
    print(f"\nRESULT: {passed}/{total}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
