"""Verify Adaptive Lesson Authoring V1.7.

Usage (from backend/):
    python scripts/verify_grammar_v17_adaptive_lesson_authoring.py
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

UNCHANGED = (
    "language_grammar_lesson_runtime",
    "language_grammar_skill_executor",
    "language_grammar_mastery",
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


def _snapshot(*, weak_pattern: str = "I am play"):
    from app.services.language_grammar_activity_authoring import (
        AdaptiveAuthoringContext,
        RecentErrorSummary,
        StudentLearningSnapshot,
    )

    return AdaptiveAuthoringContext(
        learning_snapshot=StudentLearningSnapshot(
            mastery_summary="Developing present simple accuracy",
            recent_errors=(
                RecentErrorSummary(
                    grammar_target="gram_present_simple",
                    pattern=weak_pattern,
                    frequency=3,
                    last_seen="2026-07-17",
                    confidence=0.7,
                ),
            ),
            recent_successes=("I like coffee.",),
            commonly_missed_patterns=(weak_pattern, "he go"),
            commonly_mastered_patterns=("I like ...",),
            last_lesson_summary="Practiced greetings and present simple basics",
            last_activity_type="free_text",
            lesson_history_summary="3 lessons on A2 present simple",
            confidence_summary="Medium confidence; slips on progressive form confusion",
        )
    )


def _make_request(*, adaptive=None):
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
        request_id="req_v17",
        context=AuthoringContext(
            grammar_targets=("gram_present_simple",),
            student_cefr="A2",
            learning_objective="Use present simple accurately in daily routines",
            teacher_persona=TeacherPersona(),
            student_profile=StudentProfile(student_id=1, language_id=1, overall_cefr="A2"),
            lesson_context=LessonContext(lesson_id="gless_v17", step_id="practice"),
            activity_type="free_text",
            localization="en",
            difficulty=ActivityDifficulty.guided,
            adaptive=adaptive or _snapshot(),
            versions=AuthoringVersionBundle(
                catalog_version="1.0.0",
                grammar_schema_version=1,
                blueprint_version="1.0.0",
                activity_schema_version=1,
                planner_version="1.0.0",
            ),
        ),
    )


def _valid_adaptive_json(request, *, ignore_snapshot: bool = False, mastered_only: bool = False) -> str:
    gid = request.context.grammar_targets[0]
    locale = request.context.localization
    weak = "I am play"
    if request.context.learning_snapshot.recent_errors:
        weak = request.context.learning_snapshot.recent_errors[0].pattern

    if ignore_snapshot:
        review = "Generic practice only. Do not use student history."
        scaffolding = [f"General scaffold for {gid} sentences."]
        followups = [f"Can you make any {gid} sentence?"]
        alternatives = [f"A generic {gid} example."]
    else:
        review = f"Review the missed pattern '{weak}' for {gid}."
        scaffolding = [f"Scaffold fixing the missed pattern '{weak}' within {gid}."]
        followups = [f"Can you correct a sentence like '{weak}' using {gid}?"]
        alternatives = [f"Personalized {gid} example about routines."]
    expected = ["I like ..."] if mastered_only else ["I usually ...", "Subject + Verb (Present Simple)"]
    payload = {
        "activity_id": f"adaptive:{gid}:v17",
        "activity_type": request.context.activity_type,
        "grammar_topic": gid,
        "lesson_id": request.context.lesson_context.lesson_id,
        "step_id": request.context.lesson_context.step_id,
        "title": {"values": {locale: "Adaptive Lesson"}, "default_locale": locale},
        "goal": {
            "values": {locale: request.context.learning_objective},
            "default_locale": locale,
        },
        "instructions": {"values": {locale: "Complete the adaptive lesson."}, "default_locale": locale},
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
            "provider_version": "1.7.0",
            "generation_mode": "llm_adaptive_lesson_authoring",
            "extras": {},
        },
        "localization_default_locale": locale,
        "supported_locales": [locale],
        "versions": {
            "activity_schema_version": 1,
            "provider_version": "1.7.0",
            "planner_version": "1.0.0",
            "blueprint_version": "1.0.0",
            "catalog_version": "1.0.0",
            "grammar_schema_version": 1,
            "package_version": "1.0.0",
        },
        "lesson": {
            "teacher_opening": f"Welcome — we will practice {gid}.",
            "lesson_goal": request.context.learning_objective,
            "warmup": f"Warm up with a simple {gid} sentence.",
            "main_activity": f"Practice {gid} using personalized examples.",
            "follow_up_questions": [
                "What do you usually do after school?",
                "How often do you practice English, and why?",
            ],
            "grammar_focus": f"Focus on {gid} only.",
            "expected_patterns": expected,
            "common_mistakes": [
                {"incorrect": "I am play football.", "correct": "I play football."}
            ],
            "teacher_hints": ["Check the verb form after the subject."],
            "encouragement_messages": ["Keep going!"],
            "completion_message": f"Great adaptive practice on {gid}.",
            "alternative_examples": alternatives,
            "extra_scaffolding": scaffolding,
            "adaptive_followups": followups,
            "difficulty_adjustments": "Start guided, then increase challenge gradually.",
            "review_focus": review,
            "encouragement": "You are improving on the tricky pattern — keep practicing.",
            "lesson_schema_version": 2,
            "lesson_package_version": "1.7.0",
        },
    }
    return json.dumps(payload)


def audit_1_grammar_ownership() -> list[bool]:
    print("[Audit 1 - Grammar Ownership]")
    results: list[bool] = []
    from app.services.language_grammar_activity_authoring import (
        AuthoringValidationError,
        ClaudeAuthoringProvider,
        RecentErrorSummary,
        StudentLearningSnapshot,
        AdaptiveAuthoringContext,
        author_activity_with_llm_detailed,
        validate_authoring_request,
    )

    req = _make_request()
    targets_before = tuple(req.context.grammar_targets)
    provider = ClaudeAuthoringProvider(json_generator=lambda u, s, t: _valid_adaptive_json(req))
    outcome = author_activity_with_llm_detailed(req, provider=provider, allow_fallback=False)
    results.append(
        _ok(
            "targets unchanged after adaptive authoring",
            tuple(outcome.specification.grammar_targets) == targets_before,
        )
    )
    results.append(_ok("snapshot did not add grammar topics", len(outcome.specification.grammar_targets) == 1))

    # Adaptive errors outside targets rejected at request validation
    bad = _make_request(
        adaptive=AdaptiveAuthoringContext(
            learning_snapshot=StudentLearningSnapshot(
                recent_errors=(
                    RecentErrorSummary(
                        grammar_target="gram_past_simple",
                        pattern="I goed",
                        frequency=2,
                    ),
                )
            )
        )
    )
    try:
        validate_authoring_request(bad)
        results.append(_ok("rejects snapshot errors outside targets", False))
    except AuthoringValidationError as exc:
        results.append(_ok("rejects snapshot errors outside targets", exc.code == "adaptive_error_outside_targets"))

    # Prompt must not ask to change targets
    from app.services.language_grammar_activity_authoring import build_prompt_bundle

    bundle = build_prompt_bundle(req)
    combined = (bundle.system_prompt + bundle.developer_prompt).lower()
    results.append(_ok("prompt forbids changing targets", "must not change" in combined and "grammar targets" in combined))
    results.append(_ok("Audit 1 verdict", all(results)))
    print()
    return results


def audit_2_personalization() -> list[bool]:
    print("[Audit 2 - Personalization]")
    results: list[bool] = []
    from app.services.language_grammar_activity_authoring import (
        ClaudeAuthoringProvider,
        author_activity_with_llm_detailed,
    )
    from app.services.language_grammar_activity_authoring.llm import (
        REQUIRED_PERSONALIZATION_SECTIONS,
        lesson_package_from_specification_payload,
    )

    req = _make_request()
    weak = req.context.learning_snapshot.recent_errors[0].pattern
    provider = ClaudeAuthoringProvider(json_generator=lambda u, s, t: _valid_adaptive_json(req))
    outcome = author_activity_with_llm_detailed(req, provider=provider, allow_fallback=False)
    package = lesson_package_from_specification_payload(dict(outcome.specification.payload))
    for section in REQUIRED_PERSONALIZATION_SECTIONS:
        results.append(_ok(f"personalization {section}", bool(getattr(package, section))))
    blob = package.personalization_text_blob().lower()
    results.append(_ok("reflects missed pattern", weak.lower() in blob or weak.lower() in package.review_focus.lower()))
    results.append(
        _ok(
            "generation_mode adaptive",
            outcome.specification.provider_metadata.generation_mode == "llm_adaptive_lesson_authoring",
        )
    )
    results.append(_ok("Audit 2 verdict", all(results)))
    print()
    return results


def audit_3_prompt_quality() -> list[bool]:
    print("[Audit 3 - Prompt Quality]")
    results: list[bool] = []
    from app.services.language_grammar_activity_authoring import build_prompt_bundle

    req = _make_request()
    bundle = build_prompt_bundle(req)
    combined = "\n".join([bundle.system_prompt, bundle.developer_prompt, bundle.user_prompt]).lower()
    for needle in (
        "learning snapshot",
        "influences how",
        "never what grammar",
        "avoid only repeating already-mastered",
        "gradually increase challenge",
        "must not change, add, or remove grammar targets",
    ):
        results.append(_ok(f"prompt has '{needle}'", needle in combined))
    results.append(_ok("adaptive json in user prompt", "recent_errors" in combined))
    results.append(_ok("prompt_version 1.7", bundle.prompt_version.startswith("1.7")))
    results.append(_ok("Audit 3 verdict", all(results)))
    print()
    return results


def audit_4_validation() -> list[bool]:
    print("[Audit 4 - Validation]")
    results: list[bool] = []
    from app.services.language_grammar_activity_authoring.llm import (
        LLMSchemaError,
        parse_activity_specification_json,
    )

    req = _make_request()

    try:
        parse_activity_specification_json(
            _valid_adaptive_json(req, ignore_snapshot=True),
            req,
            provider_id="claude",
        )
        results.append(_ok("rejects ignored adaptive context", False))
    except LLMSchemaError as exc:
        results.append(_ok("rejects ignored adaptive context", exc.code == "adaptive_context_ignored"))

    try:
        parse_activity_specification_json(
            _valid_adaptive_json(req, mastered_only=True),
            req,
            provider_id="claude",
        )
        results.append(_ok("rejects mastered-only expected_patterns", False))
    except LLMSchemaError as exc:
        results.append(_ok("rejects mastered-only expected_patterns", exc.code == "adaptive_context_ignored"))

    # Missing personalization
    bare = json.loads(_valid_adaptive_json(req))
    for key in (
        "alternative_examples",
        "extra_scaffolding",
        "adaptive_followups",
        "difficulty_adjustments",
        "review_focus",
        "encouragement",
    ):
        bare["lesson"].pop(key, None)
    try:
        parse_activity_specification_json(json.dumps(bare), req, provider_id="claude")
        results.append(_ok("rejects missing personalization", False))
    except LLMSchemaError:
        results.append(_ok("rejects missing personalization", True))

    spec = parse_activity_specification_json(_valid_adaptive_json(req), req, provider_id="claude")
    results.append(_ok("accepts consistent adaptive lesson", "review_focus" in spec.payload))
    results.append(_ok("Audit 4 verdict", all(results)))
    print()
    return results


def audit_5_architecture() -> list[bool]:
    print("[Audit 5 - Architecture]")
    results: list[bool] = []
    from app.services.language_grammar.ownership import ALLOWED_PACKAGE_DEPENDENCIES

    deps = {d for d in _pkg_imports(PKG) if d.startswith("language_grammar")}
    deps.discard("language_grammar")
    deps.discard("language_grammar_activity_authoring")
    allowed = ALLOWED_PACKAGE_DEPENDENCIES.get("language_grammar_activity_authoring", frozenset())
    extra = deps - set(allowed)
    results.append(_ok("authoring DAG respected", not extra, str(sorted(extra))))

    for pkg_name in UNCHANGED:
        imported = _pkg_imports(SERVICES / pkg_name)
        results.append(
            _ok(
                f"{pkg_name} unchanged (no authoring import)",
                "language_grammar_activity_authoring" not in imported,
            )
        )

    authoring_deps = _pkg_imports(PKG)
    for bad in (
        "language_grammar_lesson_runtime",
        "language_grammar_skill_executor",
        "language_grammar_mastery",
        "language_grammar_review",
        "language_grammar_progression",
    ):
        results.append(_ok(f"authoring no import {bad}", bad not in authoring_deps))

    # Snapshot immutability / no runtime objects in adaptive module
    adaptive_src = (PKG / "adaptive.py").read_text(encoding="utf-8").lower()
    for needle in ("runtime_session", "executionresult", "apply_evidence", "update_mastery"):
        results.append(_ok(f"adaptive.py no {needle}", needle not in adaptive_src))

    results.append(_ok("adaptive.py present", (PKG / "adaptive.py").is_file()))
    results.append(_ok("Audit 5 verdict", all(results)))
    print()
    return results


def check_snapshot_contracts() -> list[bool]:
    print("[Snapshot / Versioning]")
    results: list[bool] = []
    from app.services.language_grammar_activity_authoring import (
        ADAPTIVE_SNAPSHOT_SCHEMA_VERSION,
        StudentLearningSnapshot,
        empty_learning_snapshot,
        fingerprint_authoring_request,
    )
    from app.services.language_grammar_activity_authoring.llm import (
        LESSON_SCHEMA_VERSION,
        LLM_AUTHORING_PROMPT_VERSION,
    )

    snap = empty_learning_snapshot()
    results.append(_ok("empty snapshot immutable", snap.is_empty()))
    results.append(_ok("snapshot schema v1", ADAPTIVE_SNAPSHOT_SCHEMA_VERSION == 1))
    results.append(_ok("lesson schema v2", LESSON_SCHEMA_VERSION == 2))
    results.append(_ok("prompt 1.7", LLM_AUTHORING_PROMPT_VERSION.startswith("1.7")))

    req_a = _make_request()
    req_b = _make_request()
    results.append(
        _ok(
            "fingerprint includes adaptive context",
            fingerprint_authoring_request(req_a) == fingerprint_authoring_request(req_b),
        )
    )
    # Different snapshot => different fingerprint
    from app.services.language_grammar_activity_authoring import AdaptiveAuthoringContext

    req_c = _make_request(adaptive=AdaptiveAuthoringContext(learning_snapshot=StudentLearningSnapshot()))
    results.append(
        _ok(
            "fingerprint changes with snapshot",
            fingerprint_authoring_request(req_a) != fingerprint_authoring_request(req_c),
        )
    )
    print()
    return results


def main() -> int:
    print("Adaptive Lesson Authoring V1.7 verification\n")
    all_results: list[bool] = []
    all_results.extend(audit_1_grammar_ownership())
    all_results.extend(audit_2_personalization())
    all_results.extend(audit_3_prompt_quality())
    all_results.extend(audit_4_validation())
    all_results.extend(audit_5_architecture())
    all_results.extend(check_snapshot_contracts())

    passed = sum(1 for r in all_results if r)
    failed = sum(1 for r in all_results if not r)
    print(f"Summary: {passed} passed, {failed} failed, {len(all_results)} total")
    if failed:
        print("V1.7 VERDICT: NOT READY")
        return 1
    print("V1.7 VERDICT: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
