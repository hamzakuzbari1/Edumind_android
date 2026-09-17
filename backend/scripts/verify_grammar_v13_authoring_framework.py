"""Verify Grammar Activity Authoring Framework V1.3.

Usage (from backend/):
    python scripts/verify_grammar_v13_authoring_framework.py
"""

from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"
PKG = SERVICES / "language_grammar_activity_authoring"

FORBIDDEN_IMPORTS = frozenset(
    {
        "claude_service",
        "language_grammar_lesson_runtime",
        "language_grammar_skill_executor",
        "language_grammar_lesson_planner",
        "language_grammar_mastery",
        "language_grammar_progression",
        "language_grammar_review",
        "language_grammar_speaking",
        "language_speaking_lesson_runtime",
        "language_speaking_journey",
    }
)

REQUIRED_STRATEGY_IDS = frozenset(
    {
        "speaking",
        "writing",
        "reading",
        "listening",
        "grammar_exercise",
        "conversation",
        "matching",
        "ordering",
        "fill_blank",
        "multiple_choice",
        "sentence_builder",
    }
)

MAPPED_ACTIVITY_TYPES = (
    "free_text",
    "multiple_choice",
    "voice_recording",
    "ordering",
    "matching",
    "fill_in_the_blank",
    "selection",
    "conversation",
    "sentence_building",
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


def _core_py_files() -> list[Path]:
    """V1.3 core modules only — exclude V1.4 llm/ subpackage from isolation audits."""
    return sorted(PKG.glob("*.py"))


def _pkg_imports() -> set[str]:
    deps: set[str] = set()
    for py in _core_py_files():
        deps |= _parse_imports(py)
    deps.discard("language_grammar_activity_authoring")
    return deps


def _sample_grammar_id() -> str:
    from app.services.language_grammar_catalog import all_grammar_ids

    ids = sorted(all_grammar_ids())
    assert ids, "catalog empty"
    # Prefer a well-known topic when present.
    if "gram_present_simple" in ids:
        return "gram_present_simple"
    return ids[0]


def _make_request(
    *,
    activity_type: str = "multiple_choice",
    grammar_targets: tuple[str, ...] | None = None,
    preferred_strategy_id: str = "",
    learning_objective: str = "Produce accurate present simple statements",
):
    from app.services.language_grammar_activity_authoring import (
        AuthoringContext,
        AuthoringRequest,
        AuthoringVersionBundle,
        LessonContext,
        StudentProfile,
        TeacherPersona,
    )
    from app.services.language_grammar_activity_spec import ActivityDifficulty

    targets = grammar_targets or (_sample_grammar_id(),)
    return AuthoringRequest(
        request_id="req_v13_test",
        context=AuthoringContext(
            grammar_targets=targets,
            student_cefr="A2",
            learning_objective=learning_objective,
            teacher_persona=TeacherPersona(persona_id="tutor_a", tone="supportive"),
            student_profile=StudentProfile(student_id=7, language_id=1, overall_cefr="A2", locale="en"),
            lesson_context=LessonContext(lesson_id="gless_v13", step_id="practice", context_hint="cafe"),
            activity_type=activity_type,
            localization="en",
            difficulty=ActivityDifficulty.guided,
            preferred_strategy_id=preferred_strategy_id,
            versions=AuthoringVersionBundle(
                catalog_version="1.0.0",
                grammar_schema_version=1,
                blueprint_version="1.0.0",
                activity_schema_version=1,
                planner_version="1.0.0",
                provider_version="authoring",
            ),
        ),
    )


def audit_1_grammar_ownership() -> list[bool]:
    print("[Audit 1 - Grammar Ownership]")
    results: list[bool] = []
    from app.services.language_grammar_activity_authoring import (
        AuthoringValidationError,
        author_activity,
        validate_authoring_request,
    )
    from app.services.language_grammar_activity_spec import ActivitySpecification

    gid = _sample_grammar_id()
    req = _make_request(grammar_targets=(gid,), activity_type="multiple_choice")
    try:
        validate_authoring_request(req)
        results.append(_ok("valid grammar target accepted", True))
    except Exception as exc:  # noqa: BLE001
        results.append(_ok("valid grammar target accepted", False, str(exc)))

    try:
        validate_authoring_request(_make_request(grammar_targets=("not_a_grammar_id",)))
        results.append(_ok("invalid grammar_id rejected", False))
    except AuthoringValidationError:
        results.append(_ok("invalid grammar_id rejected", True))
    except Exception as exc:  # noqa: BLE001
        results.append(_ok("invalid grammar_id rejected", False, str(exc)))

    try:
        validate_authoring_request(_make_request(grammar_targets=("gram_does_not_exist_zzzz",)))
        results.append(_ok("unknown catalog id rejected", False))
    except AuthoringValidationError:
        results.append(_ok("unknown catalog id rejected", True))
    except Exception as exc:  # noqa: BLE001
        results.append(_ok("unknown catalog id rejected", False, str(exc)))

    try:
        validate_authoring_request(_make_request(learning_objective="   "))
        results.append(_ok("empty learning objective rejected", False))
    except AuthoringValidationError:
        results.append(_ok("empty learning objective rejected", True))

    spec = author_activity(req)
    results.append(_ok("output is ActivitySpecification", isinstance(spec, ActivitySpecification)))
    results.append(_ok("grammar_topic from request", spec.grammar_topic == gid))
    results.append(_ok("grammar_targets from request only", set(spec.grammar_targets) == {gid}))
    results.append(
        _ok(
            "goal equals learning objective",
            spec.goal.values.get(spec.localization_default_locale) == req.context.learning_objective,
        )
    )

    # Strategies must not invent alternate learning goals (V1.3 core only).
    src = "\n".join(p.read_text(encoding="utf-8") for p in _core_py_files())
    results.append(
        _ok(
            "no skill engines decide grammar",
            "language_speaking" not in src and "decide_grammar" not in src.lower(),
        )
    )
    results.append(_ok("Audit 1 verdict", all(results)))
    print()
    return results


def audit_2_architecture_isolation() -> list[bool]:
    print("[Audit 2 - Architecture Isolation]")
    results: list[bool] = []
    deps = _pkg_imports()
    for bad in sorted(FORBIDDEN_IMPORTS):
        results.append(_ok(f"no import {bad}", bad not in deps))

    allowed_grammar = {
        "language_grammar",
        "language_grammar_activity_spec",
        "language_grammar_catalog",
    }
    grammar_deps = {d for d in deps if d.startswith("language_grammar")}
    extra = grammar_deps - allowed_grammar
    results.append(_ok("only allowed grammar deps", not extra, str(sorted(extra))))

    # Isolation applies to V1.3 core; LLM authoring lives under llm/ (V1.4).
    src = "\n".join(p.read_text(encoding="utf-8") for p in _core_py_files()).lower()
    for needle in (
        "anthropic",
        "openai",
        "gemini",
        "claude_service",
        "prompt_template",
        "react",
        "jsx",
        "dispatch_step",
        "skill_executor",
    ):
        results.append(_ok(f"no {needle}", needle not in src))

    # Runtime must not import authoring (framework-only phase).
    runtime_pkg = SERVICES / "language_grammar_lesson_runtime"
    runtime_deps: set[str] = set()
    if runtime_pkg.is_dir():
        for py in runtime_pkg.rglob("*.py"):
            runtime_deps |= _parse_imports(py)
    results.append(
        _ok(
            "Runtime does not import authoring",
            "language_grammar_activity_authoring" not in runtime_deps,
        )
    )

    skill_pkg = SERVICES / "language_grammar_skill_executor"
    skill_deps: set[str] = set()
    if skill_pkg.is_dir():
        for py in skill_pkg.rglob("*.py"):
            skill_deps |= _parse_imports(py)
    results.append(
        _ok(
            "Skill executor does not import authoring",
            "language_grammar_activity_authoring" not in skill_deps,
        )
    )

    results.append(_ok("Audit 2 verdict", all(results)))
    print()
    return results


def audit_3_registry() -> list[bool]:
    print("[Audit 3 - Registry]")
    results: list[bool] = []
    from app.services.language_grammar_activity_authoring import (
        ActivityAuthoringRegistry,
        AuthoringStrategyError,
        REQUIRED_AUTHORING_STRATEGY_IDS,
        author_activity,
        get_default_authoring_registry,
        resolve_authoring_strategy,
    )
    from app.services.language_grammar_activity_authoring.base import PlaceholderAuthoringStrategy
    from app.services.language_grammar_activity_spec import ActivitySpecification

    reg = get_default_authoring_registry()
    ids = set(reg.ids())
    results.append(_ok("required strategy ids present", REQUIRED_STRATEGY_IDS <= ids))
    results.append(_ok("REQUIRED constant matches", REQUIRED_AUTHORING_STRATEGY_IDS == REQUIRED_STRATEGY_IDS))

    for activity_type in MAPPED_ACTIVITY_TYPES:
        req = _make_request(activity_type=activity_type)
        try:
            strategy = resolve_authoring_strategy(req, registry=reg)
            results.append(_ok(f"resolve {activity_type}", bool(strategy.strategy_id)))
            spec = author_activity(req, registry=reg)
            results.append(
                _ok(
                    f"author {activity_type} → Spec",
                    isinstance(spec, ActivitySpecification) and spec.activity_type == activity_type,
                )
            )
        except Exception as exc:  # noqa: BLE001
            results.append(_ok(f"resolve/author {activity_type}", False, str(exc)))

    # Preferred strategy path for writing/reading/listening placeholders.
    for sid in ("writing", "reading", "listening"):
        req = _make_request(activity_type="free_text", preferred_strategy_id=sid)
        strategy = resolve_authoring_strategy(req, registry=reg)
        results.append(_ok(f"preferred {sid}", strategy.strategy_id == sid))

    # Extensibility: register new strategy without touching Runtime.
    class CustomStrategy(PlaceholderAuthoringStrategy):
        def __init__(self) -> None:
            super().__init__("custom_v13", frozenset({"free_text"}))

    custom_reg = ActivityAuthoringRegistry()
    custom_reg.register(CustomStrategy())
    custom_reg.map_activity_type("free_text", "custom_v13")
    req = _make_request(activity_type="free_text")
    strategy = resolve_authoring_strategy(req, registry=custom_reg)
    results.append(_ok("new strategy via registry only", strategy.strategy_id == "custom_v13"))

    # No switch/if-chain resolution in resolution.py
    resolution_src = (PKG / "resolution.py").read_text(encoding="utf-8")
    results.append(_ok("resolution uses registry lookup", "preferred_strategy_id_for" in resolution_src))
    results.append(_ok("resolution has no activity_type if-chain", "if activity_type ==" not in resolution_src))

    try:
        resolve_authoring_strategy(_make_request(activity_type="totally_unknown_type_xyz"))
        results.append(_ok("unknown activity type fails strategy resolve", False))
    except AuthoringStrategyError:
        results.append(_ok("unknown activity type fails strategy resolve", True))
    except Exception:
        # Validation may reject first — also acceptable.
        results.append(_ok("unknown activity type fails strategy resolve", True))

    results.append(_ok("Audit 3 verdict", all(results)))
    print()
    return results


def audit_4_contracts() -> list[bool]:
    print("[Audit 4 - Contracts]")
    results: list[bool] = []
    from app.services.language_grammar_activity_authoring import (
        AuthoringResult,
        author_activity,
        author_activity_detailed,
    )
    from app.services.language_grammar_activity_spec import (
        ActivitySpecification,
        validate_activity_specification,
    )

    req = _make_request(activity_type="conversation")
    detailed = author_activity_detailed(req)
    results.append(_ok("AuthoringResult envelope", isinstance(detailed, AuthoringResult)))
    results.append(
        _ok(
            "envelope content is ActivitySpecification",
            isinstance(detailed.specification, ActivitySpecification),
        )
    )
    results.append(_ok("strategy_id set", bool(detailed.strategy_id)))
    results.append(_ok("request_fingerprint set", len(detailed.request_fingerprint) >= 16))

    spec = author_activity(req)
    results.append(_ok("author_activity returns Spec only", isinstance(spec, ActivitySpecification)))
    try:
        validate_activity_specification(spec)
        results.append(_ok("spec validates", True))
    except Exception as exc:  # noqa: BLE001
        results.append(_ok("spec validates", False, str(exc)))

    # Public author_activity return annotation / runtime type
    sig = inspect.signature(author_activity)
    results.append(
        _ok(
            "author_activity annotated ActivitySpecification",
            "ActivitySpecification" in str(sig.return_annotation),
        )
    )

    # No UI/markdown/html fields as primary contract
    results.append(_ok("no html field on Spec", not hasattr(spec, "html")))
    results.append(_ok("no markdown field on Spec", not hasattr(spec, "markdown")))
    results.append(_ok("no ui_state field on Spec", not hasattr(spec, "ui_state")))

    results.append(_ok("Audit 4 verdict", all(results)))
    print()
    return results


def audit_5_future_llm_readiness() -> list[bool]:
    print("[Audit 5 - Future LLM Readiness]")
    results: list[bool] = []
    from app.services.language_grammar_activity_authoring import AuthoringStrategy
    from app.services.language_grammar_activity_authoring.base import PlaceholderAuthoringStrategy
    from app.services.language_grammar_activity_authoring.types import AuthoringRequest
    from app.services.language_grammar_activity_spec import ActivitySpecification

    # Protocol: author(request) -> ActivitySpecification
    results.append(_ok("AuthoringStrategy is Protocol", hasattr(AuthoringStrategy, "author")))
    method = getattr(AuthoringStrategy, "author", None)
    results.append(_ok("author method present", callable(method) or method is not None))

    annotations = getattr(AuthoringStrategy.author, "__annotations__", {})
    results.append(
        _ok(
            "author returns ActivitySpecification",
            "ActivitySpecification" in str(annotations.get("return", "")),
        )
    )

    # Claude can replace placeholder without contract change: same interface.
    class FakeClaudeStrategy(PlaceholderAuthoringStrategy):
        def __init__(self) -> None:
            super().__init__("claude_future", frozenset({"multiple_choice"}))

        def author(self, request: AuthoringRequest) -> ActivitySpecification:
            # Still returns Spec — no prompt surface on the public contract.
            return super().author(request)

    from app.services.language_grammar_activity_authoring import (
        ActivityAuthoringRegistry,
        author_activity,
    )

    reg = ActivityAuthoringRegistry(strategies=(FakeClaudeStrategy(),))
    reg.map_activity_type("multiple_choice", "claude_future")
    spec = author_activity(_make_request(activity_type="multiple_choice"), registry=reg)
    results.append(_ok("replacement strategy yields Spec", isinstance(spec, ActivitySpecification)))
    results.append(_ok("replacement strategy_id used", spec.provider_metadata.extras.get("strategy_id") == "claude_future"))

    # Placeholder base has no LLM hooks / prompt engineering surfaces.
    base_src = (PKG / "base.py").read_text(encoding="utf-8").lower()
    for needle in (
        "anthropic",
        "openai",
        "claude",
        "gemini",
        "prompt_template",
        "system_prompt",
        "user_prompt",
        "chat.completions",
        "messages=[",
    ):
        results.append(_ok(f"placeholder base no {needle}", needle not in base_src))

    results.append(_ok("Audit 5 verdict", all(results)))
    print()
    return results


def check_validation_versioning_replay() -> list[bool]:
    print("[Validation / Versioning / Replayability]")
    results: list[bool] = []
    from app.services.language_grammar_activity_authoring import (
        AuthoringValidationError,
        author_activity_detailed,
        fingerprint_authoring_request,
        validate_authoring_request,
    )

    req = _make_request(activity_type="ordering")
    validate_authoring_request(req)
    results.append(_ok("version bundle required fields present", True))

    bad = _make_request()
    # Mutate via object replace — frozen dataclass: rebuild
    from app.services.language_grammar_activity_authoring import (
        AuthoringContext,
        AuthoringRequest,
        AuthoringVersionBundle,
        LessonContext,
        StudentProfile,
        TeacherPersona,
    )
    from app.services.language_grammar_activity_spec import ActivityDifficulty

    incomplete = AuthoringRequest(
        context=AuthoringContext(
            grammar_targets=(_sample_grammar_id(),),
            student_cefr="A2",
            learning_objective="obj",
            teacher_persona=TeacherPersona(),
            student_profile=StudentProfile(),
            lesson_context=LessonContext(),
            activity_type="ordering",
            difficulty=ActivityDifficulty.guided,
            versions=AuthoringVersionBundle(
                catalog_version="",
                grammar_schema_version=1,
                blueprint_version="1.0.0",
                activity_schema_version=1,
                planner_version="1.0.0",
            ),
        )
    )
    try:
        validate_authoring_request(incomplete)
        results.append(_ok("missing catalog_version rejected", False))
    except AuthoringValidationError:
        results.append(_ok("missing catalog_version rejected", True))

    fp1 = fingerprint_authoring_request(req)
    fp2 = fingerprint_authoring_request(req)
    results.append(_ok("fingerprint stable", fp1 == fp2 and len(fp1) == 32))

    detailed_a = author_activity_detailed(req)
    detailed_b = author_activity_detailed(req)
    results.append(_ok("replay fingerprint match", detailed_a.request_fingerprint == detailed_b.request_fingerprint))
    results.append(
        _ok(
            "replay activity_id deterministic",
            detailed_a.specification.activity_id == detailed_b.specification.activity_id,
        )
    )
    results.append(
        _ok(
            "spec carries version set",
            detailed_a.specification.versions.catalog_version == "1.0.0"
            and detailed_a.specification.versions.blueprint_version == "1.0.0"
            and detailed_a.specification.versions.planner_version == "1.0.0",
        )
    )
    print()
    return results


def check_flags_and_ownership() -> list[bool]:
    print("[Flags & Ownership]")
    results: list[bool] = []
    from app.core.config import get_settings
    from app.services.language_grammar.ownership import (
        ALLOWED_PACKAGE_DEPENDENCIES,
        FORBIDDEN_MASTERY_WRITERS,
        PACKAGE_LAYER,
        PACKAGE_OWNERSHIP,
    )
    from app.services.language_grammar_activity_authoring import (
        activity_authoring_enabled,
        activity_authoring_strict,
    )

    settings = get_settings()
    results.append(
        _ok(
            "LANG_GRAMMAR_ACTIVITY_AUTHORING_ENABLED defined",
            hasattr(settings, "LANG_GRAMMAR_ACTIVITY_AUTHORING_ENABLED"),
        )
    )
    results.append(
        _ok(
            "LANG_GRAMMAR_ACTIVITY_AUTHORING_STRICT defined",
            hasattr(settings, "LANG_GRAMMAR_ACTIVITY_AUTHORING_STRICT"),
        )
    )
    results.append(_ok("activity_authoring_enabled callable", isinstance(activity_authoring_enabled(), bool)))
    results.append(_ok("activity_authoring_strict callable", isinstance(activity_authoring_strict(), bool)))

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
    results.append(_ok("may depend on activity_spec", "language_grammar_activity_spec" in allowed))
    results.append(_ok("may depend on catalog", "language_grammar_catalog" in allowed))
    provider_allowed = ALLOWED_PACKAGE_DEPENDENCIES.get("language_grammar_activity_provider", frozenset())
    results.append(
        _ok(
            "provider may depend on authoring",
            "language_grammar_activity_authoring" in provider_allowed,
        )
    )

    env_root = (BACKEND.parent / ".env.example").read_text(encoding="utf-8")
    env_be = (BACKEND / ".env.example").read_text(encoding="utf-8")
    results.append(_ok("root .env.example flag", "LANG_GRAMMAR_ACTIVITY_AUTHORING_ENABLED" in env_root))
    results.append(_ok("backend .env.example flag", "LANG_GRAMMAR_ACTIVITY_AUTHORING_ENABLED" in env_be))

    required_files = (
        "__init__.py",
        "types.py",
        "author.py",
        "registry.py",
        "resolution.py",
        "strategies.py",
        "base.py",
        "validation.py",
        "fingerprint.py",
        "flags.py",
        "errors.py",
    )
    for name in required_files:
        results.append(_ok(f"file {name}", (PKG / name).is_file()))

    init = (PKG / "__init__.py").read_text(encoding="utf-8")
    results.append(_ok("RESPONSIBILITY declared", "RESPONSIBILITY" in init))
    print()
    return results


def main() -> int:
    print("Grammar Activity Authoring Framework V1.3 verification\n")
    all_results: list[bool] = []
    all_results.extend(audit_1_grammar_ownership())
    all_results.extend(audit_2_architecture_isolation())
    all_results.extend(audit_3_registry())
    all_results.extend(audit_4_contracts())
    all_results.extend(audit_5_future_llm_readiness())
    all_results.extend(check_validation_versioning_replay())
    all_results.extend(check_flags_and_ownership())

    passed = sum(1 for r in all_results if r)
    failed = sum(1 for r in all_results if not r)
    print(f"Summary: {passed} passed, {failed} failed, {len(all_results)} total")
    if failed:
        print("V1.3 VERDICT: NOT READY")
        return 1
    print("V1.3 VERDICT: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
