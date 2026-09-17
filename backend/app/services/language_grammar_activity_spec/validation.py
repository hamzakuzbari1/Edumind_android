"""Activity Specification validation (G3.35)."""

from __future__ import annotations

from app.services.language_grammar_activity_spec.registry import (
    ActivitySpecRegistry,
    get_default_spec_registry,
)
from app.services.language_grammar_activity_spec.types import (
    ActivitySpecification,
    LocalizedText,
)


class ActivitySpecError(ValueError):
    """Invalid or incompatible Activity Specification."""


def _require_localized(field: str, text: LocalizedText) -> None:
    if not text or not any(str(v).strip() for v in text.values.values()):
        raise ActivitySpecError(f"Missing localized text: {field}")


def validate_activity_specification(
    spec: ActivitySpecification,
    *,
    registry: ActivitySpecRegistry | None = None,
    known_activity_ids: set[str] | None = None,
) -> None:
    """Reject unknown types, missing contracts, broken versions, duplicate IDs."""
    reg = registry or get_default_spec_registry()

    if not spec.activity_id or not str(spec.activity_id).strip():
        raise ActivitySpecError("Missing activity_id")
    if known_activity_ids is not None and spec.activity_id in known_activity_ids:
        raise ActivitySpecError(f"Duplicate activity_id: {spec.activity_id}")

    if not reg.is_activity_type_known(spec.activity_type):
        raise ActivitySpecError(f"Unknown activity type: {spec.activity_type}")
    if not reg.is_evaluation_mode_known(spec.evaluation_mode):
        raise ActivitySpecError(f"Unknown evaluation mode: {spec.evaluation_mode}")
    if not reg.is_schema_compatible(spec.versions.activity_schema_version):
        raise ActivitySpecError(
            f"Broken / unsupported activity_schema_version: {spec.versions.activity_schema_version}"
        )

    if not spec.grammar_topic.strip():
        raise ActivitySpecError("Missing grammar_topic")
    if not spec.lesson_id.strip():
        raise ActivitySpecError("Missing lesson_id")
    if not spec.step_id.strip():
        raise ActivitySpecError("Missing step_id")

    _require_localized("title", spec.title)
    _require_localized("goal", spec.goal)
    _require_localized("instructions", spec.instructions)

    if not spec.grammar_targets:
        raise ActivitySpecError("Missing grammar_targets")
    if not spec.expected_outputs:
        raise ActivitySpecError("Missing expected_outputs")
    if not spec.completion_rules:
        raise ActivitySpecError("Missing completion_rules")
    if not spec.evidence:
        raise ActivitySpecError("Missing evidence declaration")

    output_ids: set[str] = set()
    for out in spec.expected_outputs:
        if not out.output_id.strip():
            raise ActivitySpecError("expected_output missing output_id")
        if out.output_id in output_ids:
            raise ActivitySpecError(f"Duplicate output_id: {out.output_id}")
        output_ids.add(out.output_id)
        if not reg.is_output_type_known(out.output_type):
            raise ActivitySpecError(f"Unknown output type: {out.output_type}")

    rule_ids: set[str] = set()
    for rule in spec.completion_rules:
        if not rule.rule_id.strip():
            raise ActivitySpecError("completion_rule missing rule_id")
        if rule.rule_id in rule_ids:
            raise ActivitySpecError(f"Duplicate completion rule_id: {rule.rule_id}")
        rule_ids.add(rule.rule_id)
        if not rule.kind.strip():
            raise ActivitySpecError(f"completion_rule {rule.rule_id} missing kind")

    evidence_ids: set[str] = set()
    for ev in spec.evidence:
        if not ev.evidence_id.strip():
            raise ActivitySpecError("evidence missing evidence_id")
        if ev.evidence_id in evidence_ids:
            raise ActivitySpecError(f"Duplicate evidence_id: {ev.evidence_id}")
        evidence_ids.add(ev.evidence_id)
        if not reg.is_evidence_kind_known(ev.evidence_kind):
            raise ActivitySpecError(f"Unknown evidence kind: {ev.evidence_kind}")
        if not ev.grammar_targets:
            raise ActivitySpecError(f"evidence {ev.evidence_id} missing grammar_targets")

    if spec.estimated_duration_seconds < 0:
        raise ActivitySpecError("estimated_duration_seconds cannot be negative")

    # Localization integrity
    if not spec.supported_locales:
        raise ActivitySpecError("supported_locales required")
    if spec.localization_default_locale not in spec.supported_locales:
        raise ActivitySpecError("default locale must be in supported_locales")

    # No UI / markdown document leakage in structured payload keys
    forbidden_payload_keys = {"html", "jsx", "react_tree", "markdown_document", "runtime_state"}
    bad = forbidden_payload_keys & set(spec.payload.keys())
    if bad:
        raise ActivitySpecError(f"UI/runtime leakage in payload keys: {sorted(bad)}")
