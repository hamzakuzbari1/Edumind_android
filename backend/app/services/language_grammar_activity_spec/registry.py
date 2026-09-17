"""Activity Specification Registry (G3.35) — schema discovery & compatibility only."""

from __future__ import annotations

from app.services.language_grammar_activity_spec.enums import (
    ACTIVITY_SCHEMA_VERSION,
    BUILTIN_ACTIVITY_TYPES,
    BUILTIN_EVALUATION_MODES,
    BUILTIN_EVIDENCE_KINDS,
    BUILTIN_OUTPUT_TYPES,
)


class ActivitySpecRegistry:
    """Responsible only for schema discovery, validation catalogs, and version compatibility.

    Never executes activities. Never calls providers. Never renders UI.
    """

    def __init__(self) -> None:
        self._activity_types: set[str] = set(BUILTIN_ACTIVITY_TYPES)
        self._output_types: set[str] = set(BUILTIN_OUTPUT_TYPES)
        self._evaluation_modes: set[str] = set(BUILTIN_EVALUATION_MODES)
        self._evidence_kinds: set[str] = set(BUILTIN_EVIDENCE_KINDS)
        self._supported_schema_versions: set[int] = {ACTIVITY_SCHEMA_VERSION}

    # --- discovery ---
    def activity_types(self) -> frozenset[str]:
        return frozenset(self._activity_types)

    def output_types(self) -> frozenset[str]:
        return frozenset(self._output_types)

    def evaluation_modes(self) -> frozenset[str]:
        return frozenset(self._evaluation_modes)

    def evidence_kinds(self) -> frozenset[str]:
        return frozenset(self._evidence_kinds)

    def supported_schema_versions(self) -> frozenset[int]:
        return frozenset(self._supported_schema_versions)

    # --- extensibility (no breaking schema change) ---
    def register_activity_type(self, code: str) -> None:
        code = _norm(code)
        if not code:
            raise ValueError("activity type code required")
        self._activity_types.add(code)

    def register_output_type(self, code: str) -> None:
        code = _norm(code)
        if not code:
            raise ValueError("output type code required")
        self._output_types.add(code)

    def register_evaluation_mode(self, code: str) -> None:
        code = _norm(code)
        if not code:
            raise ValueError("evaluation mode code required")
        self._evaluation_modes.add(code)

    def register_evidence_kind(self, code: str) -> None:
        code = _norm(code)
        if not code:
            raise ValueError("evidence kind code required")
        self._evidence_kinds.add(code)

    def register_schema_version(self, version: int) -> None:
        if int(version) < 1:
            raise ValueError("schema version must be >= 1")
        self._supported_schema_versions.add(int(version))

    # --- compatibility ---
    def is_activity_type_known(self, code: str) -> bool:
        return _norm(code) in self._activity_types

    def is_output_type_known(self, code: str) -> bool:
        return _norm(code) in self._output_types

    def is_evaluation_mode_known(self, code: str) -> bool:
        return _norm(code) in self._evaluation_modes

    def is_evidence_kind_known(self, code: str) -> bool:
        return _norm(code) in self._evidence_kinds

    def is_schema_compatible(self, version: int) -> bool:
        return int(version) in self._supported_schema_versions


def _norm(code: str) -> str:
    return str(code or "").strip().lower()


_DEFAULT = ActivitySpecRegistry()


def get_default_spec_registry() -> ActivitySpecRegistry:
    return _DEFAULT


def reset_default_spec_registry_for_tests() -> ActivitySpecRegistry:
    """Reset singleton — test helper only."""
    global _DEFAULT
    _DEFAULT = ActivitySpecRegistry()
    return _DEFAULT
