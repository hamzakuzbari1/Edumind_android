"""Assemble frozen SPA blueprints from validated tasks (S18)."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

from app.services.language_speaking_promotion_test.policy import (
    SPA_POLICY_VERSION,
    SPA_SCHEMA_VERSION,
)
from app.services.language_speaking_promotion_test.types import (
    SpaBlueprintStatus,
    SpeakingPromotionAssessmentBlueprint,
    SpeakingPromotionAssessmentSpecification,
    SpeakingPromotionAssessmentTask,
)


def _fp(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def build_spa_blueprint(
    *,
    specification: SpeakingPromotionAssessmentSpecification,
    tasks: tuple[SpeakingPromotionAssessmentTask, ...] | list[SpeakingPromotionAssessmentTask],
    readiness_snapshot_fingerprint: str,
    unlock_fingerprint: str,
    generation_provenance: dict | None = None,
    blueprint_id: str | None = None,
    created_at: str | None = None,
) -> SpeakingPromotionAssessmentBlueprint:
    bid = blueprint_id or f"spa_{uuid.uuid4().hex[:16]}"
    ts = created_at or datetime.now(timezone.utc).isoformat()
    ordered = tuple(sorted(tasks, key=lambda t: t.task_order))
    prov = dict(generation_provenance or {})
    bp_fp = _fp(
        {
            "blueprint_id": bid,
            "specification_fingerprint": specification.specification_fingerprint,
            "tasks": [t.to_dict() for t in ordered],
            "coverage_gaps": [g.to_dict() for g in specification.coverage_gaps],
            "readiness_snapshot_fingerprint": readiness_snapshot_fingerprint,
            "unlock_fingerprint": unlock_fingerprint,
        }
    )
    return SpeakingPromotionAssessmentBlueprint(
        blueprint_id=bid,
        schema_version=SPA_SCHEMA_VERSION,
        policy_version=SPA_POLICY_VERSION,
        specification_fingerprint=specification.specification_fingerprint,
        blueprint_fingerprint=bp_fp,
        source_cefr=specification.source_cefr,
        target_cefr=specification.target_cefr,
        tasks=ordered,
        coverage_gaps=specification.coverage_gaps,
        generation_provenance=prov,
        readiness_snapshot_fingerprint=readiness_snapshot_fingerprint,
        unlock_fingerprint=unlock_fingerprint,
        frozen=True,
        status=SpaBlueprintStatus.not_started,
        created_at=ts,
        assessment_id=bid,
        attempt_id=None,
    )
