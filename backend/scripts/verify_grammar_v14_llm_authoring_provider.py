"""Verify Grammar LLM Activity Authoring Provider V1.4.

Usage (from backend/):
    python scripts/verify_grammar_v14_llm_authoring_provider.py
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

FORBIDDEN_OWNERS = frozenset(
    {
        "language_grammar_lesson_runtime",
        "language_grammar_lesson_planner",
        "language_grammar_mastery",
        "language_grammar_progression",
        "language_grammar_review",
        "language_grammar_skill_executor",
        "language_grammar_speaking",
    }
)

UNCHANGED_PACKAGES = (
    "language_grammar_lesson_runtime",
    "language_grammar_lesson_planner",
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


def _sample_grammar_id() -> str:
    from app.services.language_grammar_catalog import all_grammar_ids

    ids = sorted(all_grammar_ids())
    if "gram_present_simple" in ids:
        return "gram_present_simple"
    return ids[0]


def _make_request(*, activity_type: str = "multiple_choice"):
    from app.services.language_grammar_activity_authoring import (
        AuthoringContext,
        AuthoringRequest,
        AuthoringVersionBundle,
        LessonContext,
        StudentProfile,
        TeacherPersona,
    )
    from app.services.language_grammar_activity_spec import ActivityDifficulty

    gid = _sample_grammar_id()
    return AuthoringRequest(
        request_id="req_v14",
        context=AuthoringContext(
            grammar_targets=(gid,),
            student_cefr="A2",
            learning_objective="Use present simple accurately in short statements",
            teacher_persona=TeacherPersona(),
            student_profile=StudentProfile(student_id=1, language_id=1, overall_cefr="A2"),
            lesson_context=LessonContext(lesson_id="gless_v14", step_id="practice"),
            activity_type=activity_type,
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


def _valid_llm_json(request) -> str:
    gid = request.context.grammar_targets[0]
    locale = request.context.localization
    payload = {
        "activity_id": f"llm:{gid}:mc",
        "activity_type": request.context.activity_type,
        "grammar_topic": gid,
        "lesson_id": request.context.lesson_context.lesson_id,
        "step_id": request.context.lesson_context.step_id,
        "title": {"values": {locale: "LLM MC"}, "default_locale": locale},
        "goal": {
            "values": {locale: request.context.learning_objective},
            "default_locale": locale,
        },
        "instructions": {
            "values": {locale: "Choose the correct form."},
            "default_locale": locale,
        },
        "difficulty": "guided",
        "estimated_duration_seconds": 90,
        "grammar_targets": list(request.context.grammar_targets),
        "expected_outputs": [
            {
                "output_id": "out_1",
                "output_type": "multiple_choice",
                "required": True,
                "options": ["a", "b", "c"],
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
        "payload": {"correct_option": "a"},
        "lesson": {
            "teacher_opening": f"Today we practice {gid} only.",
            "lesson_goal": request.context.learning_objective,
            "warmup": f"Say one sentence using {gid}.",
            "main_activity": f"Complete the activity practicing {gid}.",
            "follow_up_questions": [
                f"Can you make a simple sentence with {gid}?",
                f"Can you make a longer sentence with {gid} and a time word?",
            ],
            "grammar_focus": f"Focus on {gid} forms only.",
            "expected_patterns": [f"Pattern for {gid}", "Subject + Verb"],
            "common_mistakes": [
                {"incorrect": "I am play football.", "correct": "I play football."}
            ],
            "teacher_hints": ["Look at the subject — which verb form fits?"],
            "encouragement_messages": ["Nice effort — keep going!"],
            "completion_message": f"Great work on {gid}.",
            "alternative_examples": [f"Another {gid} example for practice."],
            "extra_scaffolding": [f"Scaffold a {gid} sentence step by step."],
            "adaptive_followups": [f"Can you reuse {gid} with a new subject?"],
            "difficulty_adjustments": "Start easy, then add one time expression.",
            "review_focus": f"Review the core {gid} pattern briefly.",
            "encouragement": "You are making progress — keep practicing.",
            "lesson_schema_version": 2,
            "lesson_package_version": "1.7.0",
        },
    }
    return json.dumps(payload)


def audit_1_llm_isolation() -> list[bool]:
    print("[Audit 1 - LLM Isolation]")
    results: list[bool] = []
    from app.services.language_grammar_activity_authoring import (
        ClaudeAuthoringProvider,
        author_activity_with_llm_detailed,
    )
    from app.services.language_grammar_activity_spec import ActivitySpecification

    req = _make_request()
    provider = ClaudeAuthoringProvider(json_generator=lambda u, s, t: _valid_llm_json(req))
    outcome = author_activity_with_llm_detailed(req, provider=provider, allow_fallback=False)
    results.append(_ok("returns ActivitySpecification", isinstance(outcome.specification, ActivitySpecification)))
    results.append(_ok("provider_id claude", outcome.provider_id == "claude"))
    results.append(_ok("not fallback", outcome.used_fallback is False))
    results.append(
        _ok(
            "grammar_targets unchanged",
            set(outcome.specification.grammar_targets) == set(req.context.grammar_targets),
        )
    )

    # Claude provider module must not import mastery/progression/runtime/skills
    provider_deps = _parse_imports(LLM_PKG / "providers.py")
    for bad in sorted(FORBIDDEN_OWNERS):
        results.append(_ok(f"providers.py no {bad}", bad not in provider_deps))

    service_src = (LLM_PKG / "service.py").read_text(encoding="utf-8")
    for needle in ("apply_evidence", "update_mastery", "resolve_targets", "dispatch_step"):
        results.append(_ok(f"service no {needle}", needle not in service_src))

    results.append(_ok("Audit 1 verdict", all(results)))
    print()
    return results


def audit_2_prompt_isolation() -> list[bool]:
    print("[Audit 2 - Prompt Isolation]")
    results: list[bool] = []
    from app.services.language_grammar_activity_authoring import build_prompt_bundle

    req = _make_request()
    bundle = build_prompt_bundle(req, provider_id="claude")
    results.append(_ok("system prompt non-empty", bool(bundle.system_prompt.strip())))
    results.append(_ok("developer prompt non-empty", bool(bundle.developer_prompt.strip())))
    results.append(_ok("user prompt non-empty", bool(bundle.user_prompt.strip())))
    results.append(_ok("prompt_version set", bool(bundle.prompt_version)))

    # Prompt templates live only in templates.py / prompt_builder.py
    templates_src = (LLM_PKG / "templates.py").read_text(encoding="utf-8")
    results.append(_ok("templates define SYSTEM", "SYSTEM_PROMPT_TEMPLATE" in templates_src))
    results.append(_ok("templates define DEVELOPER", "DEVELOPER_PROMPT_TEMPLATE" in templates_src))
    results.append(_ok("templates define USER", "USER_PROMPT_TEMPLATE" in templates_src))

    providers_src = (LLM_PKG / "providers.py").read_text(encoding="utf-8")
    for needle in ("SYSTEM_PROMPT", "You are the EduMind", "Author an ActivitySpecification"):
        results.append(_ok(f"providers.py no inline '{needle[:24]}'", needle not in providers_src))

    # Builder is the only composer
    builder_src = (LLM_PKG / "prompt_builder.py").read_text(encoding="utf-8")
    results.append(_ok("builder imports templates", "SYSTEM_PROMPT_TEMPLATE" in builder_src))
    results.append(_ok("Audit 2 verdict", all(results)))
    print()
    return results


def audit_3_structured_output() -> list[bool]:
    print("[Audit 3 - Structured Output]")
    results: list[bool] = []
    from app.services.language_grammar_activity_authoring.llm.errors import (
        LLMInvalidJSONError,
        LLMSchemaError,
    )
    from app.services.language_grammar_activity_authoring.llm.parser import (
        extract_json_object,
        parse_activity_specification_json,
    )

    req = _make_request()

    try:
        extract_json_object("not json at all")
        results.append(_ok("rejects non-json", False))
    except LLMInvalidJSONError:
        results.append(_ok("rejects non-json", True))

    try:
        extract_json_object("# Markdown title\n\nHello")
        results.append(_ok("rejects markdown document", False))
    except LLMInvalidJSONError:
        results.append(_ok("rejects markdown document", True))

    try:
        parse_activity_specification_json('{"activity_id":"x"}', req, provider_id="claude")
        results.append(_ok("rejects missing fields", False))
    except LLMSchemaError:
        results.append(_ok("rejects missing fields", True))

    bad_type = json.loads(_valid_llm_json(req))
    bad_type["activity_type"] = "totally_unknown_type_zzz"
    try:
        parse_activity_specification_json(json.dumps(bad_type), req, provider_id="claude")
        results.append(_ok("rejects unknown activity type", False))
    except LLMSchemaError:
        results.append(_ok("rejects unknown activity type", True))

    bad_targets = json.loads(_valid_llm_json(req))
    bad_targets["grammar_targets"] = ["gram_not_in_request_zzz"]
    bad_targets["grammar_topic"] = "gram_not_in_request_zzz"
    try:
        parse_activity_specification_json(json.dumps(bad_targets), req, provider_id="claude")
        results.append(_ok("rejects invalid grammar targets", False))
    except LLMSchemaError:
        results.append(_ok("rejects invalid grammar targets", True))

    spec = parse_activity_specification_json(_valid_llm_json(req), req, provider_id="claude")
    results.append(_ok("accepts valid structured JSON", spec.activity_type == req.context.activity_type))
    results.append(_ok("Audit 3 verdict", all(results)))
    print()
    return results


def audit_4_fallback() -> list[bool]:
    print("[Audit 4 - Fallback]")
    results: list[bool] = []
    from app.services.language_grammar_activity_authoring import (
        ClaudeAuthoringProvider,
        author_activity_with_llm_detailed,
    )
    from app.services.language_grammar_activity_authoring.llm.errors import LLMTransientError

    req = _make_request()

    def _always_fail(user: str, system: str, timeout: float) -> str:
        raise LLMTransientError("transient_failure", "simulated provider outage")

    provider = ClaudeAuthoringProvider(json_generator=_always_fail)
    outcome = author_activity_with_llm_detailed(req, provider=provider, allow_fallback=True)
    results.append(_ok("fallback activated", outcome.used_fallback is True))
    results.append(
        _ok(
            "fallback returns Spec",
            outcome.specification is not None and bool(outcome.specification.activity_id),
        )
    )
    results.append(
        _ok(
            "fallback generation_mode",
            outcome.specification.provider_metadata.generation_mode == "authoring_placeholder_fallback",
        )
    )
    results.append(_ok("attempts recorded", len(outcome.attempts) >= 1))

    # Without fallback, failure must raise
    try:
        author_activity_with_llm_detailed(req, provider=provider, allow_fallback=False)
        results.append(_ok("no-fallback raises", False))
    except Exception:
        results.append(_ok("no-fallback raises", True))

    results.append(_ok("Audit 4 verdict", all(results)))
    print()
    return results


def audit_5_architecture() -> list[bool]:
    print("[Audit 5 - Architecture]")
    results: list[bool] = []
    from app.services.language_grammar.ownership import (
        ALLOWED_PACKAGE_DEPENDENCIES,
        FORBIDDEN_MASTERY_WRITERS,
        PACKAGE_LAYER,
        PACKAGE_OWNERSHIP,
    )

    results.append(_ok("ownership entry", "language_grammar_activity_authoring" in PACKAGE_OWNERSHIP))
    results.append(
        _ok(
            "layer activity_authoring",
            PACKAGE_LAYER.get("language_grammar_activity_authoring") == "activity_authoring",
        )
    )
    results.append(
        _ok(
            "forbidden mastery writer",
            "language_grammar_activity_authoring" in FORBIDDEN_MASTERY_WRITERS,
        )
    )

    allowed = ALLOWED_PACKAGE_DEPENDENCIES.get("language_grammar_activity_authoring", frozenset())
    deps = {d for d in _pkg_imports(PKG) if d.startswith("language_grammar")}
    deps.discard("language_grammar")
    deps.discard("language_grammar_activity_authoring")
    extra = deps - set(allowed)
    results.append(_ok("DAG respected", not extra, str(sorted(extra))))

    # Runtime / Planner / Mastery / Review must not import LLM authoring
    for pkg_name in UNCHANGED_PACKAGES:
        pkg_path = SERVICES / pkg_name
        if not pkg_path.is_dir():
            results.append(_ok(f"{pkg_name} exists", False))
            continue
        imported = _pkg_imports(pkg_path)
        results.append(
            _ok(
                f"{pkg_name} unchanged (no authoring/llm import)",
                "language_grammar_activity_authoring" not in imported,
            )
        )

    # Registry extensibility
    from app.services.language_grammar_activity_authoring.llm import (
        LLMAuthoringProviderRegistry,
        get_default_llm_authoring_registry,
    )

    reg = get_default_llm_authoring_registry()
    for pid in ("claude", "gemini", "gpt", "local"):
        results.append(_ok(f"registry has {pid}", pid in reg.ids()))

    class FakeProvider:
        provider_id = "fake_v14"

        def generate_json(self, prompts, *, timeout_seconds: float) -> str:
            return "{}"

    custom = LLMAuthoringProviderRegistry(providers=())
    custom.register(FakeProvider())
    results.append(_ok("register without architecture change", "fake_v14" in custom.ids()))

    # Prompt leakage: no SYSTEM_PROMPT in non-builder modules except templates
    for name in ("providers.py", "service.py", "parser.py", "registry.py", "fallback.py"):
        src = (LLM_PKG / name).read_text(encoding="utf-8")
        results.append(_ok(f"{name} no SYSTEM_PROMPT_TEMPLATE", "SYSTEM_PROMPT_TEMPLATE" not in src))

    results.append(_ok("Audit 5 verdict", all(results)))
    print()
    return results


def check_flags_registry_retry() -> list[bool]:
    print("[Flags / Registry / Retry / Validation]")
    results: list[bool] = []
    from app.core.config import get_settings
    from app.services.language_grammar_activity_authoring.llm import (
        ClaudeAuthoringProvider,
        RetryPolicy,
        author_activity_with_llm_detailed,
        llm_authoring_enabled,
        llm_authoring_retry_policy,
    )

    settings = get_settings()
    for attr in (
        "LANG_GRAMMAR_LLM_AUTHORING_ENABLED",
        "LANG_GRAMMAR_LLM_AUTHORING_PROVIDER",
        "LANG_GRAMMAR_LLM_AUTHORING_FALLBACK",
        "LANG_GRAMMAR_LLM_AUTHORING_MAX_RETRIES",
        "LANG_GRAMMAR_LLM_AUTHORING_TIMEOUT_SECONDS",
    ):
        results.append(_ok(f"{attr} defined", hasattr(settings, attr)))

    results.append(_ok("llm_authoring_enabled callable", isinstance(llm_authoring_enabled(), bool)))
    policy = llm_authoring_retry_policy()
    results.append(_ok("retry policy type", isinstance(policy, RetryPolicy)))
    results.append(_ok("retry max_attempts >= 1", policy.max_attempts >= 1))

    # Retry on invalid JSON then succeed
    req = _make_request()
    calls = {"n": 0}

    def flaky(user: str, system: str, timeout: float) -> str:
        calls["n"] += 1
        if calls["n"] < 2:
            return "NOT_JSON"
        return _valid_llm_json(req)

    outcome = author_activity_with_llm_detailed(
        req,
        provider=ClaudeAuthoringProvider(json_generator=flaky),
        allow_fallback=False,
    )
    results.append(_ok("retries invalid JSON then succeeds", outcome.used_fallback is False and calls["n"] >= 2))

    env_root = (BACKEND.parent / ".env.example").read_text(encoding="utf-8")
    env_be = (BACKEND / ".env.example").read_text(encoding="utf-8")
    results.append(_ok("root .env.example flag", "LANG_GRAMMAR_LLM_AUTHORING_ENABLED" in env_root))
    results.append(_ok("backend .env.example flag", "LANG_GRAMMAR_LLM_AUTHORING_ENABLED" in env_be))

    required = (
        "__init__.py",
        "types.py",
        "prompt_builder.py",
        "templates.py",
        "parser.py",
        "retry.py",
        "providers.py",
        "registry.py",
        "fallback.py",
        "service.py",
        "flags.py",
        "errors.py",
    )
    for name in required:
        results.append(_ok(f"llm/{name}", (LLM_PKG / name).is_file()))
    print()
    return results


def main() -> int:
    print("Grammar LLM Activity Authoring Provider V1.4 verification\n")
    all_results: list[bool] = []
    all_results.extend(audit_1_llm_isolation())
    all_results.extend(audit_2_prompt_isolation())
    all_results.extend(audit_3_structured_output())
    all_results.extend(audit_4_fallback())
    all_results.extend(audit_5_architecture())
    all_results.extend(check_flags_registry_retry())

    passed = sum(1 for r in all_results if r)
    failed = sum(1 for r in all_results if not r)
    print(f"Summary: {passed} passed, {failed} failed, {len(all_results)} total")
    if failed:
        print("V1.4 VERDICT: NOT READY")
        return 1
    print("V1.4 VERDICT: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
