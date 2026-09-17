"""SPA unlock reconciliation — stale soft unlock must not authorize create (S18).

Receives a reconciled authority DTO from the API/progression layer.
Does not trust spa_unlocked alone; verifies dual-gate fields + CEFR alignment.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.language.enums import LanguageLevel
from app.services.language_level_utils import CEFR_RANK, RANK_CEFR
from app.services.language_speaking_promotion_test.policy import curriculum_skills_for_official_cefr
from app.services.language_speaking_promotion_test.types import (
    SpaCreateFailureCode,
    SpaUnlockAuthority,
)


@dataclass(frozen=True, slots=True)
class SpaUnlockDecision:
    allowed: bool
    failure_code: SpaCreateFailureCode | None = None
    student_safe_message: str = ""
    resolved_target_cefr: str | None = None


def resolve_next_speaking_cefr_local(official_cefr: str) -> str:
    """Mirror readiness target resolution without importing readiness (ownership-safe)."""
    cefr = (official_cefr or "").upper()
    try:
        level = LanguageLevel(cefr)
    except ValueError as exc:
        raise ValueError("invalid_official_cefr") from exc
    rank = CEFR_RANK[level]
    if level is LanguageLevel.C2 or rank >= max(CEFR_RANK.values()):
        raise ValueError("terminal_c2")
    target = RANK_CEFR[rank + 1].value
    if len(curriculum_skills_for_official_cefr(target)) <= 0:
        raise ValueError("target_curriculum_unavailable")
    return target


def reconcile_spa_unlock(
    authority: SpaUnlockAuthority,
    *,
    expected_official_cefr: str | None = None,
    fresh_readiness_snapshot_fingerprint: str | None = None,
    fresh_source_stage_signal_fingerprint: str | None = None,
) -> SpaUnlockDecision:
    """C+B stale policy: re-verify unlock fields before first blueprint creation."""

    if not authority.spa_unlocked:
        return SpaUnlockDecision(
            allowed=False,
            failure_code=SpaCreateFailureCode.unlock_not_granted,
            student_safe_message="The next-level speaking assessment is not unlocked yet.",
        )
    if not authority.current_stage_advanced:
        return SpaUnlockDecision(
            allowed=False,
            failure_code=SpaCreateFailureCode.unlock_not_granted,
            student_safe_message="Keep building Advanced speaking skills before the assessment.",
        )
    if not authority.hard_blockers_empty or not authority.stability_requirements_passed:
        return SpaUnlockDecision(
            allowed=False,
            failure_code=SpaCreateFailureCode.unlock_not_granted,
            student_safe_message="The next-level speaking assessment is not unlocked yet.",
        )

    official = (authority.official_cefr or "").upper()
    if expected_official_cefr and official != expected_official_cefr.upper():
        return SpaUnlockDecision(
            allowed=False,
            failure_code=SpaCreateFailureCode.cefr_mismatch,
            student_safe_message="Your speaking level changed. Refresh and try again later.",
        )

    try:
        resolved_target = resolve_next_speaking_cefr_local(official)
    except ValueError as exc:
        code = str(exc)
        if code == "terminal_c2":
            return SpaUnlockDecision(
                allowed=False,
                failure_code=SpaCreateFailureCode.unsupported_target,
                student_safe_message="You are already at the highest speaking level.",
            )
        return SpaUnlockDecision(
            allowed=False,
            failure_code=SpaCreateFailureCode.unsupported_target,
            student_safe_message="The next-level speaking assessment is temporarily unavailable.",
        )

    if authority.target_cefr and authority.target_cefr.upper() != resolved_target:
        return SpaUnlockDecision(
            allowed=False,
            failure_code=SpaCreateFailureCode.cefr_mismatch,
            student_safe_message="Your speaking assessment target changed. Refresh and try again later.",
        )

    # Stale fingerprint protection: when fresh fingerprints are supplied, they must match.
    if (
        fresh_readiness_snapshot_fingerprint
        and fresh_readiness_snapshot_fingerprint != authority.readiness_snapshot_fingerprint
    ):
        return SpaUnlockDecision(
            allowed=False,
            failure_code=SpaCreateFailureCode.stale_fingerprint,
            student_safe_message="Your speaking readiness changed. Refresh and try again later.",
        )
    if (
        fresh_source_stage_signal_fingerprint
        and fresh_source_stage_signal_fingerprint != authority.source_stage_signal_fingerprint
    ):
        return SpaUnlockDecision(
            allowed=False,
            failure_code=SpaCreateFailureCode.stale_fingerprint,
            student_safe_message="Your speaking readiness changed. Refresh and try again later.",
        )

    if not authority.readiness_snapshot_fingerprint or not authority.unlock_fingerprint:
        return SpaUnlockDecision(
            allowed=False,
            failure_code=SpaCreateFailureCode.stale_fingerprint,
            student_safe_message="The next-level speaking assessment is temporarily unavailable.",
        )

    return SpaUnlockDecision(
        allowed=True,
        resolved_target_cefr=resolved_target,
    )
