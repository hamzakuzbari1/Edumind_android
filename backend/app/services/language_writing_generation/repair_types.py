"""Repair Layer types (W5) — structural repair only; no educational invention."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

REPAIR_LAYER_VERSION = "5.0.0"


class RepairActionCode(StrEnum):
    """Allowed structural repair actions."""

    restore_checklist_from_blueprint = "restore_checklist_from_blueprint"
    restore_tips_from_mission = "restore_tips_from_mission"
    restore_learning_outcomes_from_blueprint = "restore_learning_outcomes_from_blueprint"
    restore_success_criteria_from_blueprint = "restore_success_criteria_from_blueprint"
    restore_constraints_from_mission = "restore_constraints_from_mission"
    restore_expected_output_from_blueprint = "restore_expected_output_from_blueprint"
    restore_grammar_display_from_blueprint = "restore_grammar_display_from_blueprint"
    restore_vocabulary_display_from_blueprint = "restore_vocabulary_display_from_blueprint"
    normalize_enum_casing = "normalize_enum_casing"
    fill_empty_optional_array = "fill_empty_optional_array"


# Repairs that copy from blueprint/mission — never invent content.
BLUEPRINT_SOURCED_REPAIRS: frozenset[RepairActionCode] = frozenset(
    {
        RepairActionCode.restore_checklist_from_blueprint,
        RepairActionCode.restore_tips_from_mission,
        RepairActionCode.restore_learning_outcomes_from_blueprint,
        RepairActionCode.restore_success_criteria_from_blueprint,
        RepairActionCode.restore_constraints_from_mission,
        RepairActionCode.restore_expected_output_from_blueprint,
        RepairActionCode.restore_grammar_display_from_blueprint,
        RepairActionCode.restore_vocabulary_display_from_blueprint,
        RepairActionCode.fill_empty_optional_array,
    }
)

# Repairs forbidden — would invent educational content.
FORBIDDEN_REPAIR_ACTIONS: frozenset[str] = frozenset(
    {
        "invent_grammar_target",
        "invent_vocabulary_lemma",
        "invent_learning_outcome",
        "invent_success_criterion",
        "change_word_limits",
        "change_cefr_band",
        "change_evaluation_plan",
    }
)


@dataclass(frozen=True, slots=True)
class RepairAction:
    code: RepairActionCode
    field: str
    detail: str


@dataclass(frozen=True, slots=True)
class RepairResult:
    """Outcome of structural repair pass."""

    repaired: bool
    actions: tuple[RepairAction, ...]
    repair_layer_version: str = REPAIR_LAYER_VERSION

    def to_audit_dict(self) -> dict[str, object]:
        return {
            "repaired": self.repaired,
            "action_count": len(self.actions),
            "actions": [
                {"code": a.code.value, "field": a.field, "detail": a.detail}
                for a in self.actions
            ],
        }
