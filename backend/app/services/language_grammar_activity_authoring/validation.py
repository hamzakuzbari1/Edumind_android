"""Authoring request validation (V1.3 / V1.7 adaptive)."""

from __future__ import annotations

from app.services.language_grammar.id_canon import is_canonical_grammar_id, normalize_grammar_id
from app.services.language_grammar_activity_authoring.errors import AuthoringValidationError
from app.services.language_grammar_activity_authoring.types import AuthoringRequest
from app.services.language_grammar_activity_spec import ActivityDifficulty
from app.services.language_grammar_activity_spec.registry import get_default_spec_registry
from app.services.language_grammar_catalog.catalog import all_grammar_ids


def validate_authoring_request(
    request: AuthoringRequest,
    *,
    catalog_ids: frozenset[str] | None = None,
) -> None:
    """Validate grammar ownership inputs before strategy resolution."""
    ctx = request.context
    if not ctx.grammar_targets:
        raise AuthoringValidationError("missing_grammar_targets", "grammar_targets required")

    ids = catalog_ids if catalog_ids is not None else all_grammar_ids()
    targets = tuple(normalize_grammar_id(raw) for raw in ctx.grammar_targets)
    for raw, gid in zip(ctx.grammar_targets, targets):
        if not is_canonical_grammar_id(gid):
            raise AuthoringValidationError("invalid_grammar_target", f"Invalid grammar_id: {raw!r}")
        if gid not in ids:
            raise AuthoringValidationError("unknown_grammar_target", f"Unknown grammar_id: {gid}")

    # Adaptive snapshot may only reference Grammar Targets (HOW, not new WHAT).
    snapshot = ctx.learning_snapshot
    for err in snapshot.recent_errors:
        eg = normalize_grammar_id(err.grammar_target)
        if eg not in targets:
            raise AuthoringValidationError(
                "adaptive_error_outside_targets",
                f"recent_errors.grammar_target {err.grammar_target!r} not in Grammar Targets",
            )
        if not (err.pattern or "").strip():
            raise AuthoringValidationError("invalid_recent_error", "recent_errors.pattern required")
        if err.frequency < 1:
            raise AuthoringValidationError("invalid_recent_error", "recent_errors.frequency >= 1")

    if not (ctx.learning_objective or "").strip():
        raise AuthoringValidationError("missing_learning_objective", "learning_objective required")

    if not (ctx.activity_type or "").strip():
        raise AuthoringValidationError("missing_activity_type", "activity_type required")

    spec_reg = get_default_spec_registry()
    if not spec_reg.is_activity_type_known(ctx.activity_type):
        raise AuthoringValidationError(
            "unsupported_activity_type",
            f"Unknown activity type: {ctx.activity_type}",
        )

    locale = (ctx.localization or ctx.student_profile.locale or "").strip()
    if not locale:
        raise AuthoringValidationError("missing_localization", "localization required")

    if not isinstance(ctx.difficulty, ActivityDifficulty):
        raise AuthoringValidationError("invalid_difficulty", f"Invalid difficulty: {ctx.difficulty!r}")

    versions = ctx.versions
    if not (versions.catalog_version or "").strip():
        raise AuthoringValidationError("missing_catalog_version", "catalog_version required")
    if versions.grammar_schema_version < 1:
        raise AuthoringValidationError("invalid_grammar_schema_version", "grammar_schema_version >= 1")
    if not (versions.blueprint_version or "").strip():
        raise AuthoringValidationError("missing_blueprint_version", "blueprint_version required")
    if versions.activity_schema_version < 1:
        raise AuthoringValidationError("invalid_activity_schema_version", "activity_schema_version >= 1")
    if not (versions.planner_version or "").strip():
        raise AuthoringValidationError("missing_planner_version", "planner_version required")
