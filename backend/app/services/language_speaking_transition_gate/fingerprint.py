"""Deterministic decision fingerprint for S16 transition decisions.

Same input decision content → same fingerprint. No timestamps / random ids.
"""

from __future__ import annotations

import hashlib
import json

from app.services.language_speaking_transition_gate.types import SpeakingStageTransitionDecision


def decision_fingerprint_payload(decision: SpeakingStageTransitionDecision) -> dict[str, object]:
    return {
        "schema_version": decision.schema_version,
        "policy_version": decision.policy_version,
        "official_cefr": decision.official_cefr,
        "current_stage": int(decision.current_stage),
        "target_stage": None if decision.target_stage is None else int(decision.target_stage),
        "decision": decision.decision.value,
        "authorized": decision.authorized,
        "signal_fingerprint": decision.signal_fingerprint,
        "blocking_reasons": list(decision.blocking_reasons),
        "advisory_reasons": list(decision.advisory_reasons),
        "satisfied_requirements": list(decision.satisfied_requirements),
        "unknown_requirements": list(decision.unknown_requirements),
        "requirements": [
            {
                "code": r.code,
                "passed": r.passed,
                "current": r.current,
                "required": r.required,
                "operator": r.operator.value,
                "applicability": r.applicability,
            }
            for r in decision.requirements
        ],
    }


def compute_decision_fingerprint(decision: SpeakingStageTransitionDecision) -> str:
    payload = decision_fingerprint_payload(decision)
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]
