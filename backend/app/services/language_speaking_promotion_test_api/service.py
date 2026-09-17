"""API orchestration for Speaking Promotion Assessment blueprint create (S18)."""

from __future__ import annotations

import hashlib
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.schemas.language_speaking_promotion_test import (
    SpeakingPromotionAssessmentCreateOut,
    SpeakingPromotionAssessmentGetOut,
    SpeakingPromotionAssessmentStatusOut,
    SpeakingPromotionAssessmentTaskOut,
)
from app.services.language_progression_service import ensure_progression_row
from app.services.language_speaking.enums import SpeakingLearningStage
from app.services.language_speaking_knowledge_model.locking import lock_speaking_progression_row
from app.services.language_speaking_progression.runtime import run_speaking_progression_engines
from app.services.language_speaking_promotion_readiness.storage import (
    speaking_promotion_bucket_from_payload,
)
from app.services.language_speaking_promotion_test import (
    SpaCreateFailureCode,
    SpaUnlockAuthority,
    create_speaking_promotion_assessment,
    get_active_blueprint,
    persist_active_blueprint,
)
from app.services.language_speaking_promotion_test.policy import estimated_duration_seconds
from app.services.language_speaking_promotion_test.storage import assessments_bucket_from_payload
from app.services.language_speaking_promotion_test.types import SpeakingPromotionAssessmentBlueprint


class SpeakingPromotionAssessmentApiError(Exception):
    def __init__(self, status_code: int, detail: dict | str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(str(detail))


def _unlock_fingerprint(readiness_fp: str, stage_fp: str, official: str, target: str | None) -> str:
    raw = f"{readiness_fp}|{stage_fp}|{official}|{target or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _authority_from_engines(result) -> SpaUnlockAuthority:
    readiness = result.readiness
    stability = result.stability
    return SpaUnlockAuthority(
        spa_unlocked=bool(readiness.spa_unlocked),
        official_cefr=str(readiness.official_cefr),
        target_cefr=readiness.target_cefr,
        readiness_snapshot_fingerprint=str(readiness.snapshot_fingerprint),
        source_stage_signal_fingerprint=str(readiness.source_stage_signal_fingerprint),
        unlock_fingerprint=_unlock_fingerprint(
            str(readiness.snapshot_fingerprint),
            str(readiness.source_stage_signal_fingerprint),
            str(readiness.official_cefr),
            readiness.target_cefr,
        ),
        hard_blockers_empty=bool(readiness.hard_blockers_empty),
        stability_requirements_passed=bool(stability.requirements_passed),
        current_stage_advanced=readiness.current_stage == SpeakingLearningStage.advanced,
    )


def _task_out(raw: dict[str, Any]) -> SpeakingPromotionAssessmentTaskOut:
    return SpeakingPromotionAssessmentTaskOut(
        task_id=str(raw.get("task_id", "")),
        task_order=int(raw.get("task_order") or 0),
        task_family=str(raw.get("task_family", "")),
        execution_mode=str(raw.get("execution_mode", "")),
        scenario=str(raw.get("scenario", "")),
        student_prompt=str(raw.get("student_prompt", "")),
        follow_up_prompts=[str(x) for x in (raw.get("follow_up_prompts") or [])],
        context_descriptor=str(raw.get("context_descriptor", "")),
        max_duration_seconds=int(raw.get("max_duration_seconds") or 0),
        preparation_seconds=int(raw.get("preparation_seconds") or 0),
        spontaneous_production_required=bool(raw.get("spontaneous_production_required", False)),
        spontaneous_interaction_required=False,
    )


def _create_out(bp: SpeakingPromotionAssessmentBlueprint) -> SpeakingPromotionAssessmentCreateOut:
    safe = bp.to_student_safe_dict(include_tasks=True)
    return SpeakingPromotionAssessmentCreateOut(
        assessment_id=str(safe["assessment_id"]),
        blueprint_id=str(safe["blueprint_id"]),
        status=str(safe["status"]),
        source_cefr=str(safe["source_cefr"]),
        target_cefr=str(safe["target_cefr"]),
        task_count=int(safe["task_count"]),
        frozen=bool(safe["frozen"]),
        has_interaction_coverage_gaps=bool(safe.get("has_interaction_coverage_gaps")),
        tasks=[_task_out(t) for t in (safe.get("tasks") or [])],
    )


def _get_out(bp: SpeakingPromotionAssessmentBlueprint) -> SpeakingPromotionAssessmentGetOut:
    safe = bp.to_student_safe_dict(include_tasks=True)
    return SpeakingPromotionAssessmentGetOut(
        assessment_id=str(safe["assessment_id"]),
        blueprint_id=str(safe["blueprint_id"]),
        status=str(safe["status"]),
        source_cefr=str(safe["source_cefr"]),
        target_cefr=str(safe["target_cefr"]),
        task_count=int(safe["task_count"]),
        frozen=bool(safe["frozen"]),
        has_interaction_coverage_gaps=bool(safe.get("has_interaction_coverage_gaps")),
        tasks=[_task_out(t) for t in (safe.get("tasks") or [])],
        created_at=bp.created_at,
    )


def _failure_http(code: SpaCreateFailureCode | None) -> tuple[int, str]:
    if code in (
        SpaCreateFailureCode.unlock_not_granted,
        SpaCreateFailureCode.stale_fingerprint,
        SpaCreateFailureCode.cefr_mismatch,
    ):
        return 403, "Speaking promotion assessment is not available."
    if code == SpaCreateFailureCode.unsupported_target:
        return 409, "Speaking promotion assessment target is unsupported."
    return 503, "Speaking promotion assessment is temporarily unavailable."


async def get_speaking_promotion_assessment_status(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> SpeakingPromotionAssessmentStatusOut:
    await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    engines = await run_speaking_progression_engines(
        db, student_id=student_id, language_id=language_id
    )
    authority = _authority_from_engines(engines)
    row = await lock_speaking_progression_row(db, student_id=student_id, language_id=language_id)
    payload = dict(row.promotion_readiness_json or {}) if row is not None else {}
    active = get_active_blueprint(payload)

    if active is not None:
        safe = active.to_student_safe_dict(include_tasks=False)
        return SpeakingPromotionAssessmentStatusOut(
            available=True,
            spa_unlocked=authority.spa_unlocked,
            source_cefr=active.source_cefr,
            target_cefr=active.target_cefr,
            estimated_duration_seconds=estimated_duration_seconds(),
            status=str(safe["status"]),
            assessment_id=str(safe["assessment_id"]),
            task_count=int(safe["task_count"]),
            has_interaction_coverage_gaps=bool(safe.get("has_interaction_coverage_gaps")),
            message="Your next-level speaking assessment is ready.",
        )

    if not authority.spa_unlocked:
        proj = engines.readiness.to_student_safe_dict()
        return SpeakingPromotionAssessmentStatusOut(
            available=False,
            spa_unlocked=False,
            source_cefr=authority.official_cefr,
            target_cefr=authority.target_cefr,
            estimated_duration_seconds=estimated_duration_seconds(),
            status="locked",
            message=str(proj.get("message") or "Keep building speaking skills."),
        )

    return SpeakingPromotionAssessmentStatusOut(
        available=True,
        spa_unlocked=True,
        source_cefr=authority.official_cefr,
        target_cefr=authority.target_cefr,
        estimated_duration_seconds=estimated_duration_seconds(),
        status="available",
        message="You can start the next-level speaking assessment.",
    )


async def create_speaking_promotion_assessment_api(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> SpeakingPromotionAssessmentCreateOut:
    await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    engines = await run_speaking_progression_engines(
        db, student_id=student_id, language_id=language_id
    )
    authority = _authority_from_engines(engines)

    result = create_speaking_promotion_assessment(
        authority,
        expected_official_cefr=authority.official_cefr,
        fresh_readiness_snapshot_fingerprint=authority.readiness_snapshot_fingerprint,
        fresh_source_stage_signal_fingerprint=authority.source_stage_signal_fingerprint,
    )
    if not result.ok or result.blueprint is None:
        status, msg = _failure_http(result.failure_code)
        raise SpeakingPromotionAssessmentApiError(
            status,
            {
                "message": result.student_safe_message or msg,
                "code": (result.failure_code.value if result.failure_code else "unavailable"),
            },
        )

    row = await lock_speaking_progression_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        raise SpeakingPromotionAssessmentApiError(503, {"message": "Progression unavailable."})
    payload = dict(row.promotion_readiness_json or {})
    _ = speaking_promotion_bucket_from_payload(payload)
    payload = persist_active_blueprint(payload, result.blueprint, retire_previous_active_as_terminal=True)
    row.promotion_readiness_json = payload
    flag_modified(row, "promotion_readiness_json")
    await db.flush()
    return _create_out(result.blueprint)


async def get_speaking_promotion_assessment_api(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    assessment_id: str,
) -> SpeakingPromotionAssessmentGetOut:
    await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    row = await lock_speaking_progression_row(db, student_id=student_id, language_id=language_id)
    payload = dict(row.promotion_readiness_json or {}) if row is not None else {}
    active = get_active_blueprint(payload)
    if active is not None and (
        active.assessment_id == assessment_id or active.blueprint_id == assessment_id
    ):
        return _get_out(active)

    bucket = assessments_bucket_from_payload(payload)
    terminal = bucket.get("most_recent_terminal_blueprint")
    if isinstance(terminal, dict) and (
        terminal.get("assessment_id") == assessment_id or terminal.get("blueprint_id") == assessment_id
    ):
        return _get_out(SpeakingPromotionAssessmentBlueprint.from_dict(terminal))

    raise SpeakingPromotionAssessmentApiError(404, {"message": "Assessment not found."})
