"""Evidence quarantine helpers for SPA (S19).

SPA evidence is labeled promotion_assessment and must not default-apply into S2.
"""

from __future__ import annotations

from app.services.language_speaking_promotion_test.policy import (
    EVIDENCE_SOURCE_PROMOTION_ASSESSMENT,
)


def is_promotion_assessment_evidence_source(source: str | None) -> bool:
    return str(source or "") == EVIDENCE_SOURCE_PROMOTION_ASSESSMENT


def spa_evidence_may_apply_to_mastery(*, evidence_source: str | None) -> bool:
    """S19 default: never apply promotion_assessment evidence into S2 mastery."""
    return not is_promotion_assessment_evidence_source(evidence_source)
