"""Verify Speaking S7 Hybrid Multimodal Evaluation Engine (structural + scenarios).

Usage (from backend/):
    set SPEAKING_EDUCATIONAL_ANALYZER=mock
    python scripts/verify_speaking_s7_evaluation.py
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("SPEAKING_EDUCATIONAL_ANALYZER", "mock")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"

from app.services.language_speaking_curriculum import ALL_EVIDENCE_CODES, SPEAKING_SKILL_GRAPH  # noqa: E402
from app.services.language_speaking_educational_analyzer.parser import parse_speaking_educational_json  # noqa: E402
from app.services.language_speaking_educational_analyzer.types import (  # noqa: E402
    DimensionInsight,
    SpeakingEducationalFacts,
    VocabularyInsight,
)
from app.services.language_speaking_evaluator.engine import evaluate_speaking_turn_sync  # noqa: E402
from app.services.language_speaking_evaluator.evaluation_result import SPEAKING_EVALUATION_RESULT_VERSION  # noqa: E402
from app.services.language_speaking_evaluator.facts_deserialize import evaluation_result_from_dict  # noqa: E402
from app.services.language_speaking_evaluator.hybrid_merge import merge_speaking_evaluation  # noqa: E402
from app.services.language_speaking_evaluator.input_types import (  # noqa: E402
    SpeakingEvaluationInput,
    SpeakingGoalContext,
    SpeakingOfficialCefrContext,
    SpeakingTaskContext,
)
from app.services.language_speaking_evaluator.rule_engine import evaluate_speaking_evidence  # noqa: E402
from app.services.language_speaking_pronunciation.issue_taxonomy import ISSUE_THETA_TO_S  # noqa: E402
from app.services.language_speaking_pronunciation.types import (  # noqa: E402
    PhonemeAlignmentOperation,
    PhonemeObservation,
    PronunciationIssueObservation,
    PronunciationProvenance,
    PronunciationReferenceSource,
    SpeakingPronunciationEvidenceResult,
)
from app.services.language_speaking_prosody.issue_taxonomy import ISSUE_HIGH_PAUSE_DENSITY  # noqa: E402
from app.services.language_speaking_prosody.types import (  # noqa: E402
    ProsodyEvidenceSource,
    ProsodyIssueObservation,
    ProsodyProvenance,
    ProsodySignalObservation,
    SpeakingProsodyEvidenceResult,
)
from app.services.language_speaking.ownership import ALLOWED_PACKAGE_DEPENDENCIES  # noqa: E402

NOW = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
VALID_SKILLS = SPEAKING_SKILL_GRAPH.node_ids()


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    suffix = f" -- {detail}" if detail else ""
    print(f"  {name}: {status}{suffix}")
    return passed


def _task(**kwargs) -> SpeakingTaskContext:
    defaults = dict(
        task_id="task_s7_qa",
        task_type="prompt_response",
        task_prompt="Describe your favorite holiday destination and why you like it.",
        task_instructions="Speak for 30-60 seconds about a holiday place.",
        success_criteria=("Mention the place", "Give reasons"),
        target_skill_ids=("pattern:word_stress", "phoneme:theta"),
    )
    defaults.update(kwargs)
    return SpeakingTaskContext(**defaults)


def _ctx(**kwargs):
    from app.services.language_speaking_evaluator.engine import new_evaluation_context

    task = kwargs.pop("task", _task())
    return new_evaluation_context(
        evaluation_id=kwargs.pop("evaluation_id", "eval-s7-qa"),
        student_id=kwargs.pop("student_id", 7),
        language_id=kwargs.pop("language_id", 1),
        session_id=kwargs.pop("session_id", "session_s7_qa"),
        task_id=task.task_id,
        attempt_id=kwargs.pop("attempt_id", "attempt-1"),
        revision_number=kwargs.pop("revision_number", 1),
        task=task,
        goal=SpeakingGoalContext(speaking_goal="travel", goal_label="Travel"),
        official_cefr=SpeakingOfficialCefrContext(official_cefr="B1"),
        evaluated_at=NOW.isoformat(),
        **kwargs,
    )


def _pron(skill_ids: tuple[str, ...] = ("phoneme:theta",)) -> SpeakingPronunciationEvidenceResult:
    return SpeakingPronunciationEvidenceResult(
        audio_id="a1",
        session_id="session_s7_qa",
        reference_source=PronunciationReferenceSource.transcript_hypothesis,
        reference_text="holiday destination",
        provenance=PronunciationProvenance(provider_name="mock", model_name="mock"),
        phoneme_observations=(
            PhonemeObservation("θ", "s", 0.1, 0.2, operation=PhonemeAlignmentOperation.substitution),
        ),
        issue_observations=(
            PronunciationIssueObservation(
                issue_tag=ISSUE_THETA_TO_S,
                candidate_skill_ids=skill_ids,
                evidence_reliability=0.72,
            ),
        ),
        evidence_coverage=0.8,
        evidence_reliability=0.72,
    )


def _pros(skill_ids: tuple[str, ...] = ("pattern:word_stress",)) -> SpeakingProsodyEvidenceResult:
    return SpeakingProsodyEvidenceResult(
        audio_id="a1",
        session_id="session_s7_qa",
        source_audio_id="a1",
        provenance=ProsodyProvenance(provider_name="acoustic", model_name="numpy-derived"),
        signal_observations=(
            ProsodySignalObservation("pause_density", 0.45, ProsodyEvidenceSource.derived_acoustic, 0.7),
            ProsodySignalObservation("long_pause_count", 2.0, ProsodyEvidenceSource.derived_acoustic, 0.7),
        ),
        issue_observations=(
            ProsodyIssueObservation(issue_tag=ISSUE_HIGH_PAUSE_DENSITY, candidate_skill_ids=skill_ids, evidence_reliability=0.65),
        ),
        candidate_skill_ids=skill_ids,
        evidence_coverage=0.75,
        evidence_reliability=0.65,
    )


def _input(**kwargs) -> SpeakingEvaluationInput:
    defaults = dict(
        transcript_text="My favorite holiday destination is the coast because the sea is beautiful and relaxing.",
        transcript_word_count=14,
        evidence_availability={"transcript": True, "pronunciation": True, "prosody": True},
        evidence_reliability=0.7,
        evidence_reference_ids=("bundle-s7",),
        pronunciation=_pron(),
        prosody=_pros(),
    )
    defaults.update(kwargs)
    return SpeakingEvaluationInput(**defaults)


def check_architecture() -> list[bool]:
    results: list[bool] = []
    results.append(_ok("engine version 7.0.0", SPEAKING_EVALUATION_RESULT_VERSION == "7.0.0"))
    engine = (SERVICES / "language_speaking_evaluator/engine.py").read_text(encoding="utf-8")
    results.append(_ok("engine calls rule engine", "evaluate_speaking_evidence" in engine))
    results.append(_ok("engine calls analyzer", "analyze_speaking_turn_educationally" in engine))
    results.append(_ok("engine calls merge", "merge_speaking_evaluation" in engine))
    deps = ALLOWED_PACKAGE_DEPENDENCIES.get("language_speaking_evaluator", frozenset())
    results.append(_ok("evaluator may import educational_analyzer", "language_speaking_educational_analyzer" in deps))
    results.append(_ok("evaluator has no curriculum dep", "language_speaking_curriculum" not in deps))
    eval_src = "\n".join(
        (SERVICES / "language_speaking_evaluator" / f).read_text(encoding="utf-8")
        for f in (
            "rule_engine.py",
            "hybrid_merge.py",
            "engine.py",
            "candidate_skill_evidence.py",
        )
        if (SERVICES / "language_speaking_evaluator" / f).exists()
    )
    results.append(_ok("no Writing imports in evaluator", "language_writing" not in eval_src))
    return results


def check_parser() -> list[bool]:
    results: list[bool] = []
    good = parse_speaking_educational_json(
        json.dumps({"task_response": {"score": 0.4, "reason": "Off-topic."}, "observed_cefr_estimate": "A2"})
    )
    results.append(_ok("parser accepts educational JSON", good.available))
    bad = parse_speaking_educational_json('{"passed": true, "task_response": {"score": 0.9}}')
    results.append(_ok("parser rejects decision fields", not bad.available))
    return results


def check_rule_engine() -> list[bool]:
    results: list[bool] = []
    rule = evaluate_speaking_evidence(_input(), _ctx())
    results.append(_ok("rule facts transcript present", rule.transcript.has_transcript))
    results.append(_ok("rule facts S5 issues counted", rule.pronunciation.substitution_count >= 1))
    results.append(_ok("rule facts S6 signals", rule.prosody.pause_density is not None))
    codes = set(rule.pronunciation_dimension.evidence_codes)
    results.append(_ok("rule pronunciation evidence codes", "phoneme_alignment" in codes))
    return results


def check_persistence_roundtrip() -> list[bool]:
    results: list[bool] = []
    result = evaluate_speaking_turn_sync(_input(), _ctx())
    raw = result.to_persistence_dict()
    results.append(_ok("persistence has engine_result fields", "evaluation_id" in raw and "dimensions" in raw))
    restored = evaluation_result_from_dict(raw)
    results.append(_ok("deserialize roundtrip", restored is not None))
    if restored:
        results.append(_ok("roundtrip readiness matches", restored.revision_readiness.ready == result.revision_readiness.ready))
        results.append(_ok("roundtrip educational_analysis", restored.educational_analysis is not None))
    else:
        results.extend([_ok("roundtrip readiness matches", False), _ok("roundtrip educational_analysis", False)])
    return results


def check_merge_guards() -> list[bool]:
    results: list[bool] = []
    inp = _input(transcript_text="I like cats and dogs.", transcript_word_count=5)
    ctx = _ctx(task=_task(task_prompt="Describe your favorite holiday destination and why you like it."))
    rule = evaluate_speaking_evidence(inp, ctx)
    optimistic = SpeakingEducationalFacts(
        task_response=DimensionInsight(0.99, "Perfect task fit."),
        topic_understanding=DimensionInsight(0.99, ""),
        idea_development=DimensionInsight(0.99, ""),
        coherence=DimensionInsight(0.99, ""),
        spoken_grammar=DimensionInsight(0.99, ""),
        spoken_vocabulary=VocabularyInsight(0.99, ""),
        communicative_effectiveness=DimensionInsight(0.99, ""),
        interaction_quality=DimensionInsight(0.99, ""),
        goal_alignment=DimensionInsight(0.99, ""),
        observed_cefr_estimate="C2",
        cefr_reason="",
        major_learning_issue="",
        pronunciation_interpretation="",
        delivery_interpretation="",
        previous_attempt_comparison="",
        learning_diagnosis="",
        single_revision_priority="",
        encouragement="",
        strengths=("Great",),
        available=True,
        source="test",
    )
    merged = merge_speaking_evaluation(rule, optimistic, input=inp, context=ctx)
    results.append(_ok("off-topic cannot complete", not merged.completion_eligibility.eligible))
    results.append(_ok("acoustic boost blocked flag", merged.completion_eligibility.acoustic_only_boost_blocked))
    results.append(_ok("pronunciation stays rule-owned", merged.pronunciation.score == rule.pronunciation_dimension.score))
    force_ctx = _ctx(force_complete=True)
    forced = merge_speaking_evaluation(rule, optimistic, input=inp, context=force_ctx)
    results.append(_ok("force_complete cannot bypass", not forced.completion_eligibility.eligible))
    return results


def check_skill_bridge() -> list[bool]:
    results: list[bool] = []
    result = evaluate_speaking_turn_sync(_input(), _ctx())
    ids = {c.skill_id for c in result.candidate_skill_evidence}
    results.append(_ok("candidate skills emitted", len(ids) >= 1))
    invalid = [sid for sid in ids if sid not in VALID_SKILLS]
    results.append(_ok("all candidate skill IDs graph-valid", not invalid, ", ".join(invalid[:4])))
    return results


def check_evidence_codes() -> list[bool]:
    results: list[bool] = []
    result = evaluate_speaking_turn_sync(_input(), _ctx())
    codes: set[str] = set()
    for dim in (
        result.task_response,
        result.pronunciation,
        result.fluency_delivery,
        result.grammar,
        result.vocabulary,
    ):
        codes.update(dim.evidence_codes)
    local_mirror = {"phoneme_alignment", "pauses", "semantic_task_response", "grammar_control"}
    results.append(_ok("local evidence codes used", bool(local_mirror & codes)))
    unknown = codes - ALL_EVIDENCE_CODES
    results.append(_ok("codes subset of ALL_EVIDENCE_CODES", not unknown, ", ".join(sorted(unknown)[:4])))
    return results


def _scenario(label: str, inp: SpeakingEvaluationInput, ctx_kwargs: dict | None = None) -> bool:
    ctx = _ctx(**(ctx_kwargs or {}))
    result = evaluate_speaking_turn_sync(inp, ctx)
    return result.engine_version == "7.0.0" and result.educational_analysis is not None


def check_scenario_matrix() -> list[bool]:
    """Cases A–T — synthetic bundles + mock analyzer."""
    cases: dict[str, tuple[SpeakingEvaluationInput, dict | None, callable]] = {
        "A_empty": (_input(transcript_text="", transcript_word_count=0, evidence_availability={"transcript": False}), None, lambda r: not r.revision_readiness.ready),
        "B_good_task": (_input(), None, lambda r: r.task_response.score > 0.4),
        "C_off_topic": (_input(transcript_text="The weather is cloudy today."), None, lambda r: not r.completion_eligibility.eligible),
        "D_grammar": (_input(transcript_text="I are happy about my holiday destination trip."), None, lambda r: bool(r.grammar.errors)),
        "E_pron_only": (_input(transcript_text="unrelated words only here"), {"task": _task()}, lambda r: r.pronunciation.score >= 0),
        "F_no_s5": (_input(pronunciation=None, evidence_availability={"transcript": True, "pronunciation": False, "prosody": True}), None, lambda r: r.pronunciation.status.value == "insufficient_evidence"),
        "G_no_s6": (_input(prosody=None, evidence_availability={"transcript": True, "pronunciation": True, "prosody": False}), None, lambda r: r.fluency_delivery.status.value == "insufficient_evidence"),
        "H_low_rel": (_input(evidence_reliability=0.1), None, lambda r: r.evidence_summary.reliability <= 0.2),
        "I_revision_2": (_input(), {"revision_number": 2, "previous_attempt_summary": "Previous try was shorter."}, lambda r: r.revision_number == 2),
        "J_cefr_sep": (_input(), None, lambda r: "official" not in (r.educational_analysis.observed_cefr_estimate if r.educational_analysis else "")),
        "K_explanation": (_input(), None, lambda r: bool(r.explanation.summary)),
        "L_weak_skills": (_input(transcript_text="hi"), None, lambda r: isinstance(r.weak_skills, tuple)),
        "M_provider_prov": (_input(provider_provenance=({"provider_name": "mock"},)), None, lambda r: len(r.provider_provenance) >= 1),
        "N_priority": (_input(), None, lambda r: bool(r.priority_issue)),
        "O_readiness_vs_completion": (_input(), None, lambda r: hasattr(r, "completion_eligibility") and hasattr(r, "revision_readiness")),
        "P_mock_analyzer": (_input(), None, lambda r: r.educational_analysis is not None and r.educational_analysis.source == "mock"),
        "Q_coach_no_recompute": (_input(), None, lambda r: "engine_version" in r.to_persistence_dict()),
        "R_no_s2_mutation": (_input(), None, lambda r: "mastery_update" not in json.dumps(r.to_persistence_dict())),
        "S_dimensions_10": (_input(), None, lambda r: all(hasattr(r, d) for d in ("task_response", "pronunciation", "fluency_delivery", "grammar", "vocabulary", "coherence", "interaction", "goal_alignment", "cefr_validation", "topic_understanding"))),
        "T_overall_readiness": (_input(), None, lambda r: 0.0 <= r.overall_readiness <= 1.0),
    }
    results: list[bool] = []
    for label, (inp, ctx_kw, pred) in cases.items():
        ctx = _ctx(**(ctx_kw or {}))
        result = evaluate_speaking_turn_sync(inp, ctx)
        results.append(_ok(f"scenario {label}", pred(result)))
    return results


def check_frozen_regressions() -> list[bool]:
    scripts = [
        "verify_speaking_s0_architecture.py",
        "verify_speaking_s3_audio_frontend.py",
        "verify_speaking_s4_audio_runtime.py",
        "verify_speaking_s5_pronunciation.py",
        "verify_speaking_s6_prosody.py",
    ]
    results: list[bool] = []
    for script in scripts:
        path = BACKEND / "scripts" / script
        if not path.exists():
            results.append(_ok(f"frozen rerun {script}", False, "missing"))
            continue
        proc = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(BACKEND),
            capture_output=True,
            text=True,
            timeout=600,
            env={**os.environ, "SPEAKING_EDUCATIONAL_ANALYZER": os.environ.get("SPEAKING_EDUCATIONAL_ANALYZER", "mock")},
        )
        ok = proc.returncode == 0
        detail = "" if ok else (proc.stdout + proc.stderr)[-200:]
        results.append(_ok(f"frozen rerun {script}", ok, detail))
    return results


def main() -> int:
    print("Speaking S7 Hybrid Evaluation Verification\n")
    sections = [
        ("Architecture", check_architecture),
        ("Parser safety", check_parser),
        ("Rule engine", check_rule_engine),
        ("Persistence roundtrip", check_persistence_roundtrip),
        ("Merge guards", check_merge_guards),
        ("Skill bridge", check_skill_bridge),
        ("Evidence codes", check_evidence_codes),
        ("Scenario matrix A–T", check_scenario_matrix),
        ("Frozen S0–S6 regressions", check_frozen_regressions),
    ]
    all_results: list[bool] = []
    for title, fn in sections:
        print(f"[{title}]")
        all_results.extend(fn())
        print()
    passed = sum(all_results)
    total = len(all_results)
    print(f"Summary: {passed}/{total} checks passed")
    if passed == total:
        print("SPEAKING S7 STRUCTURAL VERIFICATION PASSED.")
        return 0
    print("SPEAKING S7 STRUCTURAL VERIFICATION FAILED.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
