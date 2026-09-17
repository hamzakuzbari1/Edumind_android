"""Mint SpeakingPromotionAssessment envelopes with distinct assessment_id (S19)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.services.language_speaking_promotion_test.execution_types import (
    LANGUAGE_SPEAKING_PROMOTION_EXECUTION_VERSION,
    SpeakingPromotionAssessment,
)
from app.services.language_speaking_promotion_test.mandatory import (
    declare_mandatory_competency_requirements,
)
from app.services.language_speaking_promotion_test.types import (
    SpaBlueprintStatus,
    SpeakingPromotionAssessmentBlueprint,
)


def mint_assessment_id() -> str:
    return f"spa_assess_{uuid.uuid4().hex[:16]}"


def mint_attempt_id() -> str:
    return f"spa_attempt_{uuid.uuid4().hex[:16]}"


def mint_session_id() -> str:
    return f"spa_session_{uuid.uuid4().hex[:16]}"


def mint_task_attempt_id(task_id: str) -> str:
    return f"spa_task_attempt_{task_id}_{uuid.uuid4().hex[:8]}"


def build_speaking_promotion_assessment(
    blueprint: SpeakingPromotionAssessmentBlueprint,
    *,
    assessment_id: str | None = None,
    created_at: str | None = None,
) -> SpeakingPromotionAssessment:
    """Wrap a frozen blueprint in a distinct assessment identity.

    Guarantees assessment_id != blueprint_id.
    """
    bid = blueprint.blueprint_id
    aid = assessment_id or mint_assessment_id()
    if aid == bid:
        aid = mint_assessment_id()
    ts = created_at or datetime.now(timezone.utc).isoformat()
    reqs = declare_mandatory_competency_requirements(blueprint)
    return SpeakingPromotionAssessment(
        assessment_id=aid,
        blueprint_id=bid,
        blueprint=blueprint,
        status=SpaBlueprintStatus.not_started,
        created_at=ts,
        updated_at=ts,
        mandatory_requirements=reqs,
        schema_version=LANGUAGE_SPEAKING_PROMOTION_EXECUTION_VERSION,
    )
