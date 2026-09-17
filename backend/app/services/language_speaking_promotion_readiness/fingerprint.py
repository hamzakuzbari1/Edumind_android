"""Deterministic fingerprint for speaking promotion readiness results."""

from __future__ import annotations

import hashlib
import json

from app.services.language_speaking_promotion_readiness.types import SpeakingPromotionReadinessResult


def readiness_fingerprint_payload(result: SpeakingPromotionReadinessResult) -> dict[str, object]:
    return {
        "schema_version": result.schema_version,
        "policy_version": result.policy_version,
        "official_cefr": result.official_cefr,
        "target_cefr": result.target_cefr,
        "current_stage": int(result.current_stage),
        "eligible_for_readiness": result.eligible_for_readiness,
        "readiness_score": result.readiness_score,
        "status": result.status.value,
        "hard_blockers": list(result.hard_blockers),
        "advisory_signals": list(result.advisory_signals),
        "unknown_signals": list(result.unknown_signals),
        "source_stage_signal_fingerprint": result.source_stage_signal_fingerprint,
        "hard_blockers_empty": result.hard_blockers_empty,
        "score_meets_promotion_floor": result.score_meets_promotion_floor,
        "stability_requirements_passed": result.stability_requirements_passed,
        "spa_unlocked": result.spa_unlocked,
        "unlock_state": result.unlock_state.value,
        "dimensions": [
            {
                "code": d.code,
                "current": round(d.current, 6),
                "required": round(d.required, 6),
                "progress": round(d.progress, 6),
                "contribution": round(d.contribution, 6),
                "passed": d.passed,
            }
            for d in result.dimensions
        ],
    }


def compute_readiness_fingerprint(result: SpeakingPromotionReadinessResult) -> str:
    payload = readiness_fingerprint_payload(result)
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]
