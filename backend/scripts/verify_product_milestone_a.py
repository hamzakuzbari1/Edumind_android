"""Verify Product Milestone A — Student Grammar Module (generate-only).

Usage (from backend/):
    python scripts/verify_product_milestone_a.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
SERVICES = BACKEND / "app" / "services"
MODULE_PKG = SERVICES / "language_grammar_module"
PIPELINE_PKG = SERVICES / "language_grammar_pipeline"
API_FILE = BACKEND / "app" / "api" / "language_grammar_student.py"
FRONTEND_VIEW = ROOT / "src" / "views" / "student" / "grammar" / "StudentGrammarView.vue"
FRONTEND_API = ROOT / "src" / "api" / "grammar.js"

FORBIDDEN_CALLS = (
    "run_execution",
    "evaluate_grammar",
    "apply_evidence_and_persist",
    "compute_mastery_from_evidence",
    "evaluate_review_queue",
    "complete_review_and_persist",
    "run_grammar_learning_pipeline",
    "stage_execute",
    "stage_evaluate",
    "stage_mastery",
    "stage_review",
)

RESPONSE_FIELDS = (
    "lesson_id",
    "grammar_target",
    "lesson_title",
    "teacher_opening",
    "lesson_goal",
    "warmup",
    "main_activity",
    "follow_up_questions",
    "teacher_hints",
    "common_mistakes",
    "expected_patterns",
    "completion_message",
    "estimated_minutes",
    "difficulty",
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


def _module_source() -> str:
    parts = [p.read_text(encoding="utf-8") for p in MODULE_PKG.rglob("*.py")]
    parts.append(API_FILE.read_text(encoding="utf-8"))
    parts.append((PIPELINE_PKG / "generate.py").read_text(encoding="utf-8"))
    return "\n".join(parts)


def _make_snapshot():
    from app.services.language_grammar.enums import GrammarCEFRBand
    from app.services.language_grammar_catalog.catalog import get_default_catalog
    from app.services.language_grammar_evidence.types import GrammarEvidenceBatch, GrammarEvidenceObservation
    from app.services.language_grammar.enums import (
        GrammarEvidenceSourceSkill,
        GrammarObservationType,
    )
    from app.services.language_grammar_evidence.validation import validate_batch
    from app.services.language_grammar_integration.service import build_learning_snapshot
    from app.services.language_grammar_mastery.engine import apply_observations, empty_snapshot
    from app.services.language_grammar_progression.engine import compute_progression_snapshot
    from app.services.language_grammar_progression.types import GrammarProgressionStudentState
    from app.services.language_grammar_review.engine import empty_student_state
    from app.services.language_grammar_review.service import compute_from_mastery

    catalog = get_default_catalog()
    prog = compute_progression_snapshot(
        catalog=catalog,
        anchor_cefr=GrammarCEFRBand.A2,
        student=GrammarProgressionStudentState(student_id=11, language_id=1),
    )
    gid = prog.current_grammar_id or "gram_present_simple"
    obs = GrammarEvidenceObservation(
        observation_id="m1",
        student_id=11,
        language_id=1,
        grammar_id=gid,
        source_skill=GrammarEvidenceSourceSkill.speaking,
        observation_type=GrammarObservationType.formative,
        attempt_count=2,
        correct_count=1,
        confidence=0.7,
        context="seed",
        observed_at="2026-07-01T00:00:00Z",
    )
    validated = validate_batch(GrammarEvidenceBatch(observations=(obs,)))
    mastery = apply_observations(
        empty_snapshot(student_id=11, language_id=1),
        validated.observations,
        catalog=catalog,
    )
    review = compute_from_mastery(
        mastery=mastery,
        student=empty_student_state(student_id=11, language_id=1),
        as_of="2026-07-18T00:00:00Z",
    )
    return build_learning_snapshot(
        student_id=11,
        language_id=1,
        overall_cefr=GrammarCEFRBand.A2,
        progression=prog,
        mastery=mastery,
        review=review,
        catalog=catalog,
        as_of="2026-07-18T00:00:00Z",
    )


def audit_1_frontend() -> list[bool]:
    print("[Audit 1 - Frontend]")
    results: list[bool] = []
    results.append(_ok("grammar view exists", FRONTEND_VIEW.is_file()))
    results.append(_ok("grammar api client exists", FRONTEND_API.is_file()))
    view = FRONTEND_VIEW.read_text(encoding="utf-8") if FRONTEND_VIEW.is_file() else ""
    api = FRONTEND_API.read_text(encoding="utf-8") if FRONTEND_API.is_file() else ""
    nav = (ROOT / "src" / "config" / "navigation.js").read_text(encoding="utf-8")
    router = (ROOT / "src" / "router" / "index.js").read_text(encoding="utf-8")
    results.append(_ok("nav includes /student/grammar", "/student/grammar" in nav))
    results.append(_ok("router registers grammar", "student-grammar" in router or "path: 'grammar'" in router))
    results.append(_ok("calls lesson/start", "/student/grammar/lesson/start" in api))
    results.append(_ok("Start Lesson CTA", "Start Lesson" in view))
    results.append(_ok("loading state", "generating" in view and "LoadingState" in view))
    results.append(_ok("error retry UX", "Try again" in view))
    results.append(_ok("renders warmup/main activity", "warmup" in view and "main_activity" in view))
    results.append(_ok("Finish button", "Finish" in view))
    results.append(_ok("Audit 1 verdict", all(results)))
    print()
    return results


def audit_2_backend() -> list[bool]:
    print("[Audit 2 - Backend]")
    results: list[bool] = []
    results.append(_ok("API file exists", API_FILE.is_file()))
    api_text = API_FILE.read_text(encoding="utf-8")
    results.append(_ok("POST lesson/start route", '"/lesson/start"' in api_text or "/lesson/start" in api_text))
    results.append(_ok("dashboard route", "/dashboard" in api_text))
    results.append(_ok("status route", "/status" in api_text))
    router = (BACKEND / "app" / "api" / "router.py").read_text(encoding="utf-8")
    results.append(_ok("router includes grammar student", "language_grammar_student" in router))

    from app.core.config import get_settings
    from app.services.language_grammar_module import grammar_module_enabled
    from app.services.language_grammar_pipeline import generate_grammar_lesson, lesson_dict_from_generation
    from app.services.language_grammar_pipeline.types import PipelineRequest, PipelineStatus

    settings = get_settings()
    results.append(_ok("LANG_GRAMMAR_MODULE_ENABLED defined", hasattr(settings, "LANG_GRAMMAR_MODULE_ENABLED")))
    results.append(_ok("module flag helper", isinstance(grammar_module_enabled(), bool)))

    snap = _make_snapshot()
    with patch(
        "app.services.language_grammar_pipeline.generate.grammar_pipeline_enabled",
        return_value=True,
    ), patch(
        "app.services.language_grammar_lesson_planner.service.grammar_engine_enabled",
        return_value=True,
    ), patch(
        "app.services.language_grammar_activity_authoring.flags.activity_authoring_enabled",
        return_value=True,
    ), patch(
        "app.services.language_grammar_activity_authoring.author.activity_authoring_enabled",
        return_value=True,
    ):
        outcome = generate_grammar_lesson(
            PipelineRequest(
                student_id=11,
                language_id=1,
                student_response="",
                learning_snapshot=snap,
                use_llm_authoring=False,
                as_of="2026-07-18T00:00:00Z",
                apply_learner_writes=False,
            )
        )
        results.append(_ok("generate completed", outcome.status is PipelineStatus.completed))
        lesson = lesson_dict_from_generation(outcome)
        for field in RESPONSE_FIELDS:
            results.append(_ok(f"response field {field}", field in lesson and lesson[field] not in (None, "")))
        results.append(_ok("no execution invoked", outcome.execution_invoked is False))
        results.append(_ok("mastery not applied", outcome.write_gate.mastery_applied is False))
        results.append(_ok("review not applied", outcome.write_gate.review_applied is False))

    results.append(_ok("Audit 2 verdict", all(results)))
    print()
    return results


def audit_3_pipeline_integration() -> list[bool]:
    print("[Audit 3 - Integration]")
    results: list[bool] = []
    svc = (MODULE_PKG / "service.py").read_text(encoding="utf-8")
    results.append(_ok("module calls generate_grammar_lesson", "generate_grammar_lesson" in svc))
    results.append(_ok("module uses lesson_dict_from_generation", "lesson_dict_from_generation" in svc))
    results.append(_ok("module does not call full pipeline run", "run_grammar_learning_pipeline" not in svc))
    gen = (PIPELINE_PKG / "generate.py").read_text(encoding="utf-8")
    results.append(_ok("generate path notes generate_only", "generate_only" in gen))
    results.append(_ok("generate stops after author", "stage_author_activity" in gen and "stage_execute" not in gen))
    results.append(_ok("Audit 3 verdict", all(results)))
    print()
    return results


def audit_4_ux() -> list[bool]:
    print("[Audit 4 - UX]")
    results: list[bool] = []
    view = FRONTEND_VIEW.read_text(encoding="utf-8")
    results.append(_ok("loading skeleton present", "LoadingState" in view or "LearningLoader" in view))
    results.append(_ok("start button disabled while generating", ":disabled=" in view and "generating" in view))
    results.append(_ok("friendly error copy", "couldn't generate" in view.lower() or "try again" in view.lower()))
    results.append(_ok("no raw exception dump", "exc.message" not in view and "stack" not in view.lower()))
    results.append(_ok("empty state message", "Generate your first Grammar lesson" in view or "empty_state_message" in view))
    results.append(_ok("Audit 4 verdict", all(results)))
    print()
    return results


def audit_5_architecture() -> list[bool]:
    print("[Audit 5 - Architecture]")
    results: list[bool] = []
    src = _module_source()
    for needle in FORBIDDEN_CALLS:
        # evaluate_review_queue may appear only via integration import chain in comments — block direct calls
        if needle == "evaluate_review_queue":
            results.append(_ok(f"no direct {needle}", "evaluate_review_queue(" not in src))
        else:
            results.append(_ok(f"no {needle}", needle not in src))

    from app.services.language_grammar.ownership import (
        FORBIDDEN_MASTERY_WRITERS,
        PACKAGE_LAYER,
        PACKAGE_OWNERSHIP,
        ALLOWED_PACKAGE_DEPENDENCIES,
    )

    results.append(_ok("ownership entry module", "language_grammar_module" in PACKAGE_OWNERSHIP))
    results.append(_ok("layer product", PACKAGE_LAYER.get("language_grammar_module") == "product"))
    results.append(_ok("module forbidden mastery writer", "language_grammar_module" in FORBIDDEN_MASTERY_WRITERS))

    deps: set[str] = set()
    for py in MODULE_PKG.rglob("*.py"):
        deps |= _parse_imports(py)
    deps.discard("language_grammar_module")
    deps.discard("language_grammar")
    allowed = ALLOWED_PACKAGE_DEPENDENCIES.get("language_grammar_module", frozenset())
    unexpected = sorted(deps - set(allowed))
    results.append(_ok("module DAG respected", not unexpected, detail=str(unexpected)))

    env_root = (ROOT / ".env.example").read_text(encoding="utf-8")
    env_be = (BACKEND / ".env.example").read_text(encoding="utf-8")
    results.append(_ok("root env documents MODULE flag", "LANG_GRAMMAR_MODULE_ENABLED" in env_root))
    results.append(_ok("backend env documents MODULE flag", "LANG_GRAMMAR_MODULE_ENABLED" in env_be))
    results.append(_ok("Audit 5 verdict", all(results)))
    print()
    return results


def main() -> int:
    print("Product Milestone A — Grammar Module verification\n")
    all_results: list[bool] = []
    all_results.extend(audit_1_frontend())
    all_results.extend(audit_2_backend())
    all_results.extend(audit_3_pipeline_integration())
    all_results.extend(audit_4_ux())
    all_results.extend(audit_5_architecture())

    passed = sum(1 for r in all_results if r)
    failed = sum(1 for r in all_results if not r)
    print(f"Summary: {passed} passed, {failed} failed, {len(all_results)} total")
    if failed:
        print("Product Milestone A VERDICT: NOT READY")
        return 1
    print("Product Milestone A VERDICT: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
