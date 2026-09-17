"""Progression mastery ledger — path state for Curriculum Graph (not promotion)."""

from __future__ import annotations

from typing import Any

from app.services.language_speaking_curriculum_engine.progression_types import (
    ProgressionDecision,
    ProgressionMasteryLedger,
)

SPEAKING_PROGRESSION_KEY = "speaking_progression_mastery"


def progression_ledger_from_payload(payload: dict[str, Any] | None) -> ProgressionMasteryLedger:
    if not isinstance(payload, dict):
        return ProgressionMasteryLedger()
    raw = payload.get(SPEAKING_PROGRESSION_KEY)
    return ProgressionMasteryLedger.from_dict(raw if isinstance(raw, dict) else None)


def merge_progression_ledger_into_payload(
    payload: dict[str, Any] | None,
    ledger: ProgressionMasteryLedger,
) -> dict[str, Any]:
    out = dict(payload) if isinstance(payload, dict) else {}
    out[SPEAKING_PROGRESSION_KEY] = ledger.to_dict()
    return out


def record_progression_exposure(
    ledger: ProgressionMasteryLedger,
    decision: ProgressionDecision,
    *,
    mastery_delta: float = 0.12,
) -> ProgressionMasteryLedger:
    """Update exposure / soft mastery after an Educational Case is generated."""
    node = decision.node
    case_id = decision.case_variant.case_id
    ledger.current_node_id = node.node_id
    ledger.node_exposure[node.node_id] = int(ledger.node_exposure.get(node.node_id) or 0) + 1
    prev = float(ledger.node_mastery.get(node.node_id) or 0.0)
    if decision.action == "advance":
        # Leaving node: ensure advance threshold reached on record
        ledger.node_mastery[node.node_id] = max(prev, node.estimated_mastery_advance)
        if node.node_id not in ledger.completed_path:
            ledger.completed_path.append(node.node_id)
    else:
        ledger.node_mastery[node.node_id] = min(1.0, prev + mastery_delta)
    if case_id not in ledger.used_case_ids:
        ledger.used_case_ids.append(case_id)
    # Aggregate soft mastery for cluster / domain
    ledger.cluster_mastery[node.cluster_id] = max(
        float(ledger.cluster_mastery.get(node.cluster_id) or 0.0),
        float(ledger.node_mastery.get(node.node_id) or 0.0),
    )
    ledger.domain_mastery[node.domain_id] = max(
        float(ledger.domain_mastery.get(node.domain_id) or 0.0),
        float(ledger.node_mastery.get(node.node_id) or 0.0),
    )
    return ledger
