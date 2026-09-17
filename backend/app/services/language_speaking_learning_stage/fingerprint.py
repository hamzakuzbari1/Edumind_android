"""Deterministic fingerprint for SpeakingStageSignalSnapshot (S15).

Same authoritative educational state → same fingerprint.
Excludes projection timestamps, copy text, and random ids.
"""

from __future__ import annotations

import hashlib
import json

from app.services.language_speaking_learning_stage.types import SpeakingStageSignalSnapshot


def snapshot_fingerprint_payload(snapshot: SpeakingStageSignalSnapshot) -> dict[str, object]:
    """Canonical fingerprint payload — numbers rounded for float stability."""
    return {
        "v": snapshot.schema_version,
        "official_cefr": snapshot.official_cefr,
        "current_stage": int(snapshot.current_stage),
        "curriculum_skill_count": snapshot.curriculum_skill_count,
        "skills_with_evidence_count": snapshot.skills_with_evidence_count,
        "coverage_ratio": round(snapshot.coverage_ratio, 6),
        "core_skill_coverage_ratio": round(snapshot.core_skill_coverage_ratio, 6),
        "sufficient_evidence_ratio": round(snapshot.sufficient_evidence_ratio, 6),
        "stable_skill_ratio": round(snapshot.stable_skill_ratio, 6),
        "developing_skill_ratio": round(snapshot.developing_skill_ratio, 6),
        "at_risk_skill_ratio": round(snapshot.at_risk_skill_ratio, 6),
        "in_level_mastery_avg": round(snapshot.in_level_mastery_avg, 6),
        "in_level_stability_avg": round(snapshot.in_level_stability_avg, 6),
        "recent_success_signal": round(snapshot.recent_success_signal, 6),
        "recent_failure_signal": round(snapshot.recent_failure_signal, 6),
        "retry_dependence_signal": (
            None
            if snapshot.retry_dependence_signal is None
            else round(snapshot.retry_dependence_signal, 6)
        ),
        "support_dependence_signal": snapshot.support_dependence_signal,
        "retention_risk_signal": round(snapshot.retention_risk_signal, 6),
        "transfer_breadth_signal": round(snapshot.transfer_breadth_signal, 6),
        "context_diversity_signal": round(snapshot.context_diversity_signal, 6),
        "performance_stability_signal": round(snapshot.performance_stability_signal, 6),
        "data_sufficiency": snapshot.data_sufficiency.value,
        "blocker_kinds": [b.kind.value for b in snapshot.blockers],
        "total_observations": snapshot.total_observations,
        "distinct_tasks_attempted": snapshot.distinct_tasks_attempted,
        "core_skills_with_min_evidence": snapshot.core_skills_with_min_evidence,
        "core_skill_count": snapshot.core_skill_count,
    }


def compute_snapshot_fingerprint(snapshot: SpeakingStageSignalSnapshot) -> str:
    payload = snapshot_fingerprint_payload(snapshot)
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]
