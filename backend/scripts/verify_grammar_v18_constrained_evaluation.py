"""Verify Grammar-Constrained Evaluation V1.8.

Usage (from backend/):
    python scripts/verify_grammar_v18_constrained_evaluation.py
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"
PKG = SERVICES / "language_grammar_evaluation"

FORBIDDEN_IMPORTS = frozenset(
    {
        "language_grammar_mastery",
        "language_grammar_progression",
        "language_grammar_review",
        "language_grammar_lesson_planner",
        "language_grammar_lesson_runtime",
        "language_grammar_skill_executor",
        "claude_service",
    }
)


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"  {name}: {status}{suffix}")
    return passed


def _parse_imports(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app.services."):
            parts = node.module.split(".")
            if len(parts) >= 3:
                imports.add(parts[2])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app.services."):
                    parts = alias.name.split(".")
                    if len(parts) >= 3:
                        imports.add(parts[2])
    return imports


def _pkg_imports() -> set[str]:
    deps: set[str] = set()
    for py in PKG.rglob("*.py"):
        deps |= _parse_imports(py)
    deps.discard("language_grammar_evaluation")
    return deps


def _lesson(*, patterns: tuple[str, ...] = ("I usually ...", "He plays ...", "Subject + Verb (Present Simple)")):
    from app.services.language_grammar_evaluation import LessonPackageView

    return LessonPackageView(
        expected_patterns=patterns,
        grammar_focus="gram_present_simple forms only",
        main_activity="Practice present simple",
    )


def _request(*, response: str, patterns: tuple[str, ...] | None = None, targets: tuple[str, ...] = ("gram_present_simple",)):
    from app.services.language_grammar_evaluation import build_evaluation_request

    lesson = _lesson(patterns=patterns) if patterns is not None else _lesson()
    return build_evaluation_request(
        grammar_targets=targets,
        student_response=response,
        expected_patterns=tuple(lesson.expected_patterns),
        lesson_package=lesson,
        student_id=7,
        language_id=1,
        as_of="2026-07-18T00:00:00Z",
        evaluation_id="geval_test_1",
    )


def audit_1_grammar_ownership() -> list[bool]:
    print("[Audit 1 - Grammar Ownership]")
    results: list[bool] = []
    from app.services.language_grammar_evaluation import (
        PatternStatus,
        TargetStatus,
        evaluate_grammar,
    )

    req = _request(response="He play football every day.")
    result = evaluate_grammar(req)
    results.append(_ok("only one target evaluated", len(result.target_results) == 1))
    results.append(_ok("target is grammar target", result.target_results[0].target_id == "gram_present_simple"))
    results.append(
        _ok(
            "all pattern results bound to targets",
            all(p.grammar_target == "gram_present_simple" for p in result.pattern_results),
        )
    )
    # Third-person incorrect detected
    he_plays = next(p for p in result.pattern_results if "He plays" in p.pattern)
    results.append(_ok("he plays pattern incorrect", he_plays.status is PatternStatus.incorrect))

    # Source has no fluency/vocab scoring APIs
    src = "\n".join(p.read_text(encoding="utf-8") for p in PKG.rglob("*.py")).lower()
    for needle in ("vocabulary richness", "pronunciation", "accent score", "fluency_score", "creativity"):
        results.append(_ok(f"no {needle}", needle not in src))
    results.append(_ok("Audit 1 verdict", all(results)))
    print()
    return results


def audit_2_evidence_quality() -> list[bool]:
    print("[Audit 2 - Evidence Quality]")
    results: list[bool] = []
    from app.services.language_grammar_evidence.types import GrammarEvidenceObservation
    from app.services.language_grammar_evaluation import evaluate_grammar

    req = _request(response="I usually wake up early.")
    result = evaluate_grammar(req)
    results.append(_ok("evidence items non-empty", len(result.evidence_items) >= 1))
    results.append(_ok("observations non-empty", len(result.observations) >= 1))
    results.append(_ok("observation type", isinstance(result.observations[0], GrammarEvidenceObservation)))
    for item in result.evidence_items:
        results.append(_ok(f"evidence target-specific {item.pattern[:20]}", item.grammar_target == "gram_present_simple"))
        results.append(_ok("evidence has pattern", bool(item.pattern)))
        results.append(_ok("evidence has reason", bool(item.reason)))
    results.append(
        _ok(
            "observation grammar_id matches target",
            all(o.grammar_id == "gram_present_simple" for o in result.observations),
        )
    )
    results.append(_ok("no mastery fields on observation", not hasattr(result.observations[0], "overall_mastery")))
    results.append(_ok("Audit 2 verdict", all(results)))
    print()
    return results


def audit_3_architecture() -> list[bool]:
    print("[Audit 3 - Architecture]")
    results: list[bool] = []
    from app.services.language_grammar.ownership import (
        ALLOWED_PACKAGE_DEPENDENCIES,
        FORBIDDEN_MASTERY_WRITERS,
        PACKAGE_LAYER,
        PACKAGE_OWNERSHIP,
    )

    results.append(_ok("ownership entry", "language_grammar_evaluation" in PACKAGE_OWNERSHIP))
    results.append(_ok("layer evaluation", PACKAGE_LAYER.get("language_grammar_evaluation") == "evaluation"))
    results.append(
        _ok(
            "forbidden mastery writer",
            "language_grammar_evaluation" in FORBIDDEN_MASTERY_WRITERS,
        )
    )

    deps = _pkg_imports()
    for bad in sorted(FORBIDDEN_IMPORTS):
        results.append(_ok(f"no import {bad}", bad not in deps))

    allowed = ALLOWED_PACKAGE_DEPENDENCIES.get("language_grammar_evaluation", frozenset())
    grammar_deps = {d for d in deps if d.startswith("language_grammar")}
    grammar_deps.discard("language_grammar")
    extra = grammar_deps - set(allowed)
    results.append(_ok("DAG respected", not extra, str(sorted(extra))))

    src = "\n".join(p.read_text(encoding="utf-8") for p in PKG.rglob("*.py"))
    for needle in (
        "apply_evidence_and_persist",
        "update_mastery",
        "resolve_targets",
        "review_queue",
        "GrammarLessonBlueprint",
    ):
        results.append(_ok(f"no {needle}", needle not in src))

    results.append(_ok("Audit 3 verdict", all(results)))
    print()
    return results


def audit_4_validation() -> list[bool]:
    print("[Audit 4 - Validation]")
    results: list[bool] = []
    from app.services.language_grammar_evaluation import (
        EvaluationValidationError,
        LessonPackageView,
        build_evaluation_request,
        evaluate_grammar,
        validate_evaluation_request,
    )

    try:
        evaluate_grammar(
            build_evaluation_request(
                grammar_targets=(),
                student_response="hello",
                lesson_package=LessonPackageView(expected_patterns=("I usually ...",)),
            )
        )
        results.append(_ok("rejects missing targets", False))
    except EvaluationValidationError as exc:
        results.append(_ok("rejects missing targets", exc.code == "missing_grammar_targets"))

    try:
        evaluate_grammar(
            build_evaluation_request(
                grammar_targets=("gram_present_simple",),
                student_response="hello",
                lesson_package=LessonPackageView(expected_patterns=()),
                expected_patterns=(),
            )
        )
        results.append(_ok("rejects missing lesson patterns", False))
    except EvaluationValidationError as exc:
        results.append(
            _ok(
                "rejects missing lesson patterns",
                exc.code in {"missing_lesson_package", "missing_expected_patterns"},
            )
        )

    # Pattern outside lesson
    try:
        req = build_evaluation_request(
            grammar_targets=("gram_present_simple",),
            student_response="I usually swim.",
            expected_patterns=("I usually ...", "Past Perfect had done ..."),
            lesson_package=LessonPackageView(expected_patterns=("I usually ...",)),
        )
        validate_evaluation_request(req)
        results.append(_ok("rejects pattern outside lesson", False))
    except EvaluationValidationError as exc:
        results.append(_ok("rejects pattern outside lesson", exc.code == "pattern_outside_lesson"))

    # Unexpected grammar named in patterns
    try:
        req = build_evaluation_request(
            grammar_targets=("gram_present_simple",),
            student_response="I usually swim.",
            expected_patterns=("I usually ...", "Use past perfect forms"),
            lesson_package=LessonPackageView(
                expected_patterns=("I usually ...", "Use past perfect forms")
            ),
        )
        validate_evaluation_request(req)
        results.append(_ok("rejects unexpected grammar in patterns", False))
    except EvaluationValidationError as exc:
        results.append(
            _ok(
                "rejects unexpected grammar in patterns",
                exc.code == "unexpected_grammar_evaluated",
            )
        )

    results.append(_ok("Audit 4 verdict", all(results)))
    print()
    return results


def audit_5_replayability() -> list[bool]:
    print("[Audit 5 - Replayability]")
    results: list[bool] = []
    from app.services.language_grammar_evaluation import (
        evaluate_grammar,
        fingerprint_evaluation_request,
    )

    req = _request(response="He plays football.")
    a = evaluate_grammar(req)
    b = evaluate_grammar(req)
    results.append(_ok("fingerprint stable", a.request_fingerprint == b.request_fingerprint))
    results.append(
        _ok(
            "fingerprint helper matches",
            a.request_fingerprint == fingerprint_evaluation_request(req),
        )
    )
    results.append(
        _ok(
            "pattern statuses reproducible",
            [p.status for p in a.pattern_results] == [p.status for p in b.pattern_results],
        )
    )
    results.append(
        _ok(
            "target statuses reproducible",
            [t.status for t in a.target_results] == [t.status for t in b.target_results],
        )
    )
    results.append(
        _ok(
            "observation ids reproducible",
            [o.observation_id for o in a.observations] == [o.observation_id for o in b.observations],
        )
    )
    # Different response => different fingerprint
    req2 = _request(response="I usually cook.")
    results.append(
        _ok(
            "fingerprint changes with response",
            fingerprint_evaluation_request(req) != fingerprint_evaluation_request(req2),
        )
    )
    results.append(_ok("Audit 5 verdict", all(results)))
    print()
    return results


def check_flags_and_happy_path() -> list[bool]:
    print("[Flags / Context / Happy path]")
    results: list[bool] = []
    from app.core.config import get_settings
    from app.services.language_grammar_activity_spec import build_minimal_specification
    from app.services.language_grammar_evaluation import (
        PatternStatus,
        TargetStatus,
        evaluate_grammar,
        grammar_evaluation_enabled,
        lesson_view_from_specification,
        build_evaluation_request,
    )

    settings = get_settings()
    results.append(_ok("LANG_GRAMMAR_EVALUATION_ENABLED defined", hasattr(settings, "LANG_GRAMMAR_EVALUATION_ENABLED")))
    results.append(_ok("flag helper callable", isinstance(grammar_evaluation_enabled(), bool)))

    # Spec payload path
    spec = build_minimal_specification()
    # inject lesson patterns into payload
    from dataclasses import replace

    payload = dict(spec.payload)
    payload["expected_patterns"] = json.dumps(["I usually ...", "Subject + Verb (Present Simple)"])
    payload["grammar_focus"] = "gram_present_simple"
    payload["teacher_opening"] = "Hello"
    payload["main_activity"] = "Practice"
    spec = replace(spec, payload=payload, grammar_targets=("gram_present_simple",), grammar_topic="gram_present_simple")
    view = lesson_view_from_specification(spec)
    results.append(_ok("lesson view from spec", len(view.expected_patterns) == 2))

    req = build_evaluation_request(
        grammar_targets=("gram_present_simple",),
        student_response="I usually walk to school.",
        specification=spec,
        student_id=1,
        language_id=1,
        evaluation_id="geval_spec_1",
    )
    result = evaluate_grammar(req)
    usually = next(p for p in result.pattern_results if "usually" in p.pattern.lower())
    results.append(_ok("usually pattern correct", usually.status is PatternStatus.correct))
    results.append(
        _ok(
            "target not incorrect when match present",
            result.target_results[0].status in {TargetStatus.correct, TargetStatus.partial},
        )
    )

    env_root = (BACKEND.parent / ".env.example").read_text(encoding="utf-8")
    env_be = (BACKEND / ".env.example").read_text(encoding="utf-8")
    results.append(_ok("root .env.example flag", "LANG_GRAMMAR_EVALUATION_ENABLED" in env_root))
    results.append(_ok("backend .env.example flag", "LANG_GRAMMAR_EVALUATION_ENABLED" in env_be))

    for name in (
        "types.py",
        "engine.py",
        "pattern_matching.py",
        "evidence_mapper.py",
        "validation.py",
        "fingerprint.py",
        "__init__.py",
    ):
        results.append(_ok(f"file {name}", (PKG / name).is_file()))
    print()
    return results


def main() -> int:
    print("Grammar-Constrained Evaluation V1.8 verification\n")
    all_results: list[bool] = []
    all_results.extend(audit_1_grammar_ownership())
    all_results.extend(audit_2_evidence_quality())
    all_results.extend(audit_3_architecture())
    all_results.extend(audit_4_validation())
    all_results.extend(audit_5_replayability())
    all_results.extend(check_flags_and_happy_path())

    passed = sum(1 for r in all_results if r)
    failed = sum(1 for r in all_results if not r)
    print(f"Summary: {passed} passed, {failed} failed, {len(all_results)} total")
    if failed:
        print("V1.8 VERDICT: NOT READY")
        return 1
    print("V1.8 VERDICT: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
