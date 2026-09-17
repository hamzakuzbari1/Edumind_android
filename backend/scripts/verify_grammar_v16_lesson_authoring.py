"""Verify Grammar-Aware Lesson Authoring V1.6.

Usage (from backend/):
    python scripts/verify_grammar_v16_lesson_authoring.py
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"
PKG = SERVICES / "language_grammar_activity_authoring"
LLM_PKG = PKG / "llm"

UNCHANGED_PACKAGES = (
    "language_grammar_lesson_runtime",
    "language_grammar_skill_executor",
    "language_grammar_mastery",
    "language_grammar_progression",
    "language_grammar_review",
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


def _pkg_imports(path: Path) -> set[str]:
    deps: set[str] = set()
    for py in path.rglob("*.py"):
        deps |= _parse_imports(py)
    return deps


def _make_request(*, targets: tuple[str, ...] = ("gram_present_simple",)):
    from app.services.language_grammar_activity_authoring import (
        AuthoringContext,
        AuthoringRequest,
        AuthoringVersionBundle,
        LessonContext,
        StudentProfile,
        TeacherPersona,
    )
    from app.services.language_grammar_activity_spec import ActivityDifficulty

    return AuthoringRequest(
        request_id="req_v16",
        context=AuthoringContext(
            grammar_targets=targets,
            student_cefr="A2",
            learning_objective="Use present simple accurately with frequency adverbs when relevant",
            teacher_persona=TeacherPersona(),
            student_profile=StudentProfile(student_id=1, language_id=1, overall_cefr="A2"),
            lesson_context=LessonContext(lesson_id="gless_v16", step_id="practice"),
            activity_type="free_text",
            localization="en",
            difficulty=ActivityDifficulty.guided,
            versions=AuthoringVersionBundle(
                catalog_version="1.0.0",
                grammar_schema_version=1,
                blueprint_version="1.0.0",
                activity_schema_version=1,
                planner_version="1.0.0",
            ),
        ),
    )


def _valid_lesson_json(request, *, inject_bad_grammar: str = "") -> str:
    gid = request.context.grammar_targets[0]
    locale = request.context.localization
    main = f"Practice sentences using {gid} only."
    if inject_bad_grammar:
        main = f"{main} Also practice {inject_bad_grammar}."
    payload = {
        "activity_id": f"lesson:{gid}:v16",
        "activity_type": request.context.activity_type,
        "grammar_topic": gid,
        "lesson_id": request.context.lesson_context.lesson_id,
        "step_id": request.context.lesson_context.step_id,
        "title": {"values": {locale: "Grammar Lesson"}, "default_locale": locale},
        "goal": {
            "values": {locale: request.context.learning_objective},
            "default_locale": locale,
        },
        "instructions": {
            "values": {locale: "Complete the lesson activities."},
            "default_locale": locale,
        },
        "difficulty": "guided",
        "estimated_duration_seconds": 900,
        "grammar_targets": list(request.context.grammar_targets),
        "expected_outputs": [
            {
                "output_id": "out_1",
                "output_type": "free_text",
                "required": True,
                "options": [],
                "constraints": {},
            }
        ],
        "evaluation_mode": "rule_based",
        "completion_rules": [{"rule_id": "r1", "kind": "require_all_outputs", "params": {}}],
        "evidence": [
            {
                "evidence_id": "e1",
                "evidence_kind": "formative",
                "grammar_targets": list(request.context.grammar_targets),
                "observation_types_hint": ["formative"],
                "required": True,
                "notes": "",
            }
        ],
        "provider_metadata": {
            "provider_id": "claude",
            "provider_version": "1.6.0",
            "generation_mode": "llm_lesson_authoring",
            "extras": {},
        },
        "localization_default_locale": locale,
        "supported_locales": [locale],
        "versions": {
            "activity_schema_version": 1,
            "provider_version": "1.6.0",
            "planner_version": "1.0.0",
            "blueprint_version": "1.0.0",
            "catalog_version": "1.0.0",
            "grammar_schema_version": 1,
            "package_version": "1.0.0",
        },
        "lesson": {
            "teacher_opening": f"Welcome — today we focus on {gid}.",
            "lesson_goal": request.context.learning_objective,
            "warmup": f"Warm up with one easy {gid} sentence.",
            "main_activity": main,
            "follow_up_questions": [
                "What do you usually do on Mondays?",
                "How often do you practice English each week, and why?",
            ],
            "grammar_focus": f"Teach and practice {gid} forms only.",
            "expected_patterns": [
                "I usually ...",
                "I always ...",
                "Subject + Verb (Present Simple)",
            ],
            "common_mistakes": [
                {"incorrect": "I am play football.", "correct": "I play football."}
            ],
            "teacher_hints": ["Look at the time word — which verb form fits?"],
            "encouragement_messages": ["Nice try — keep going!"],
            "completion_message": f"Great work practicing {gid}.",
            "alternative_examples": [f"Try another {gid} sentence about daily routines."],
            "extra_scaffolding": ["First choose the subject, then the verb form."],
            "adaptive_followups": ["Can you make a harder sentence with a frequency word?"],
            "difficulty_adjustments": "Increase challenge after the warmup.",
            "review_focus": f"Review the missed pattern for {gid}.",
            "encouragement": "Nice progress — focus on the tricky pattern.",
            "lesson_schema_version": 2,
            "lesson_package_version": "1.7.0",
        },
    }
    return json.dumps(payload)


def audit_1_grammar_fidelity() -> list[bool]:
    print("[Audit 1 - Grammar Fidelity]")
    results: list[bool] = []
    from app.services.language_grammar_activity_authoring.llm import (
        ClaudeAuthoringProvider,
        REQUIRED_LESSON_SECTIONS,
        author_activity_with_llm_detailed,
        lesson_package_from_specification_payload,
    )

    req = _make_request()
    provider = ClaudeAuthoringProvider(json_generator=lambda u, s, t: _valid_lesson_json(req))
    outcome = author_activity_with_llm_detailed(req, provider=provider, allow_fallback=False)
    package = lesson_package_from_specification_payload(dict(outcome.specification.payload))
    blob = package.section_text_blob().lower()
    results.append(_ok("all sections present", all(s in outcome.specification.payload for s in REQUIRED_LESSON_SECTIONS)))
    results.append(_ok("targets preserved on spec", set(outcome.specification.grammar_targets) == set(req.context.grammar_targets)))
    results.append(_ok("lesson mentions target id", req.context.grammar_targets[0] in blob))
    results.append(_ok("no past perfect leakage", "past perfect" not in blob))
    results.append(_ok("no passive voice leakage", "passive voice" not in blob))
    results.append(
        _ok(
            "generation_mode adaptive lesson authoring",
            outcome.specification.provider_metadata.generation_mode
            == "llm_adaptive_lesson_authoring",
        )
    )
    results.append(_ok("Audit 1 verdict", all(results)))
    print()
    return results


def audit_2_lesson_completeness() -> list[bool]:
    print("[Audit 2 - Lesson Completeness]")
    results: list[bool] = []
    from app.services.language_grammar_activity_authoring.llm import (
        REQUIRED_LESSON_SECTIONS,
        parse_activity_specification_json,
        lesson_package_from_specification_payload,
    )

    req = _make_request()
    spec = parse_activity_specification_json(_valid_lesson_json(req), req, provider_id="claude")
    package = lesson_package_from_specification_payload(dict(spec.payload))
    for section in REQUIRED_LESSON_SECTIONS:
        results.append(_ok(f"section {section}", bool(getattr(package, section, None) or spec.payload.get(section))))
    results.append(_ok("follow_up progressive count", len(package.follow_up_questions) >= 2))
    results.append(_ok("expected_patterns non-empty", len(package.expected_patterns) >= 1))
    results.append(_ok("common_mistakes non-empty", len(package.common_mistakes) >= 1))
    results.append(_ok("teacher_hints non-empty", len(package.teacher_hints) >= 1))
    results.append(_ok("encouragement non-empty", len(package.encouragement_messages) >= 1))
    results.append(_ok("Audit 2 verdict", all(results)))
    print()
    return results


def audit_3_prompt_quality() -> list[bool]:
    print("[Audit 3 - Prompt Quality]")
    results: list[bool] = []
    from app.services.language_grammar_activity_authoring.llm import build_prompt_bundle

    req = _make_request()
    bundle = build_prompt_bundle(req, provider_id="claude")
    combined = "\n".join([bundle.system_prompt, bundle.developer_prompt, bundle.user_prompt]).lower()

    for needle in (
        "never invent curriculum",
        "grammar engine already selected",
        "must not introduce unrelated grammar",
        "only teach the grammar targets provided",
    ):
        results.append(_ok(f"prompt contains '{needle}'", needle in combined))

    # Must not ask the model to choose grammar / invent syllabus
    for banned in (
        "choose the best grammar topic",
        "invent a grammar syllabus",
        "decide the student's cefr",
        "select next grammar",
    ):
        results.append(_ok(f"prompt avoids '{banned}'", banned not in combined))

    results.append(_ok("prompt_version 1.x", bundle.prompt_version.startswith("1.")))
    # Prompts only in templates / builder
    providers_src = (LLM_PKG / "providers.py").read_text(encoding="utf-8")
    results.append(_ok("providers have no SYSTEM_PROMPT_TEMPLATE", "SYSTEM_PROMPT_TEMPLATE" not in providers_src))
    results.append(_ok("Audit 3 verdict", all(results)))
    print()
    return results


def audit_4_parser() -> list[bool]:
    print("[Audit 4 - Parser]")
    results: list[bool] = []
    from app.services.language_grammar_activity_authoring.llm import (
        LLMSchemaError,
        parse_activity_specification_json,
    )

    req = _make_request()

    # Missing lesson sections
    bare = json.loads(_valid_lesson_json(req))
    bare.pop("lesson", None)
    bare["payload"] = {"correct_option": "a"}
    try:
        parse_activity_specification_json(json.dumps(bare), req, provider_id="claude")
        results.append(_ok("rejects missing lesson sections", False))
    except LLMSchemaError as exc:
        results.append(_ok("rejects missing lesson sections", "missing_lesson" in exc.code or "lesson" in exc.message.lower()))

    # Unsupported grammar
    try:
        parse_activity_specification_json(
            _valid_lesson_json(req, inject_bad_grammar="past perfect and passive voice"),
            req,
            provider_id="claude",
        )
        results.append(_ok("rejects unsupported grammar", False))
    except LLMSchemaError as exc:
        results.append(_ok("rejects unsupported grammar", exc.code == "unsupported_grammar_detected"))

    # Malformed common_mistakes
    bad = json.loads(_valid_lesson_json(req))
    bad["lesson"]["common_mistakes"] = [{"incorrect": "same", "correct": "same"}]
    try:
        parse_activity_specification_json(json.dumps(bad), req, provider_id="claude")
        results.append(_ok("rejects invalid common_mistakes", False))
    except LLMSchemaError:
        results.append(_ok("rejects invalid common_mistakes", True))

    # Hint reveals answer
    reveal = json.loads(_valid_lesson_json(req))
    reveal["lesson"]["teacher_hints"] = ["The answer is: I play football every day."]
    try:
        parse_activity_specification_json(json.dumps(reveal), req, provider_id="claude")
        results.append(_ok("rejects answer-revealing hints", False))
    except LLMSchemaError as exc:
        results.append(_ok("rejects answer-revealing hints", exc.code == "hint_reveals_answer"))

    # Valid parses
    spec = parse_activity_specification_json(_valid_lesson_json(req), req, provider_id="claude")
    results.append(_ok("accepts valid lesson package", "teacher_opening" in spec.payload))
    results.append(_ok("Audit 4 verdict", all(results)))
    print()
    return results


def audit_5_architecture() -> list[bool]:
    print("[Audit 5 - Architecture]")
    results: list[bool] = []
    from app.services.language_grammar.ownership import ALLOWED_PACKAGE_DEPENDENCIES, PACKAGE_OWNERSHIP

    results.append(_ok("ownership entry", "language_grammar_activity_authoring" in PACKAGE_OWNERSHIP))

    allowed = ALLOWED_PACKAGE_DEPENDENCIES.get("language_grammar_activity_authoring", frozenset())
    deps = {d for d in _pkg_imports(PKG) if d.startswith("language_grammar")}
    deps.discard("language_grammar")
    deps.discard("language_grammar_activity_authoring")
    extra = deps - set(allowed)
    results.append(_ok("authoring DAG respected", not extra, str(sorted(extra))))

    for pkg_name in UNCHANGED_PACKAGES:
        pkg_path = SERVICES / pkg_name
        imported = _pkg_imports(pkg_path) if pkg_path.is_dir() else set()
        # Unchanged packages must not newly depend on lesson schema modules specifically;
        # they also must not import authoring at all for isolation of this phase.
        results.append(
            _ok(
                f"{pkg_name} unchanged (no authoring import)",
                "language_grammar_activity_authoring" not in imported,
            )
        )

    # Authoring must not import runtime / skill executor / mastery
    authoring_deps = _pkg_imports(PKG)
    for bad in (
        "language_grammar_lesson_runtime",
        "language_grammar_skill_executor",
        "language_grammar_mastery",
        "language_grammar_progression",
        "language_grammar_review",
    ):
        results.append(_ok(f"authoring no import {bad}", bad not in authoring_deps))

    results.append(_ok("lesson_schema.py present", (LLM_PKG / "lesson_schema.py").is_file()))
    results.append(_ok("lesson_validation.py present", (LLM_PKG / "lesson_validation.py").is_file()))
    results.append(_ok("Audit 5 verdict", all(results)))
    print()
    return results


def check_schema_versioning() -> list[bool]:
    print("[Schema / Versioning]")
    results: list[bool] = []
    from app.services.language_grammar_activity_authoring.llm import (
        LESSON_PACKAGE_VERSION,
        LESSON_SCHEMA_VERSION,
        LLM_AUTHORING_PROMPT_VERSION,
        parse_activity_specification_json,
    )

    results.append(_ok("lesson schema version >= 1", LESSON_SCHEMA_VERSION >= 1))
    results.append(_ok("lesson package 1.x", LESSON_PACKAGE_VERSION.startswith("1.")))
    results.append(_ok("prompt version 1.x", LLM_AUTHORING_PROMPT_VERSION.startswith("1.")))

    req = _make_request(targets=("gram_present_simple", "gram_connectors_and_but"))
    # Avoid false unsupported hits: keep content about present simple + connectors only
    data = json.loads(_valid_lesson_json(_make_request()))
    data["grammar_targets"] = list(req.context.grammar_targets)
    data["grammar_topic"] = "gram_present_simple"
    data["evidence"][0]["grammar_targets"] = list(req.context.grammar_targets)
    data["lesson"]["grammar_focus"] = "Focus on gram_present_simple and gram_connectors_and_but only."
    data["lesson"]["main_activity"] = "Practice gram_present_simple with and/but connectors."
    spec = parse_activity_specification_json(json.dumps(data), req, provider_id="claude")
    results.append(_ok("multi-target lesson accepted", set(spec.grammar_targets) == set(req.context.grammar_targets)))
    results.append(
        _ok(
            "payload lesson_schema_version",
            spec.payload.get("lesson_schema_version") in {"1", "2"},
        )
    )
    print()
    return results


def main() -> int:
    print("Grammar-Aware Lesson Authoring V1.6 verification\n")
    all_results: list[bool] = []
    all_results.extend(audit_1_grammar_fidelity())
    all_results.extend(audit_2_lesson_completeness())
    all_results.extend(audit_3_prompt_quality())
    all_results.extend(audit_4_parser())
    all_results.extend(audit_5_architecture())
    all_results.extend(check_schema_versioning())

    passed = sum(1 for r in all_results if r)
    failed = sum(1 for r in all_results if not r)
    print(f"Summary: {passed} passed, {failed} failed, {len(all_results)} total")
    if failed:
        print("V1.6 VERDICT: NOT READY")
        return 1
    print("V1.6 VERDICT: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
