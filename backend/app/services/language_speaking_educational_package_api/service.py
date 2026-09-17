"""Thin API service for Speaking Learning Package E1."""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.language_speaking_educational_package import (
    SpeakingLearningPackageOut,
    SpeakingLearningPackageStatusOut,
)
from app.services.language_speaking_educational_package.author_pipeline import (
    generate_speaking_learning_package,
)
from app.services.language_speaking_educational_package.persistence import (
    audit_from_item,
    get_package_item_by_id,
    package_from_item,
    status_from_item,
)
from app.services.language_speaking_educational_package.projection import (
    project_package_for_student,
)


class SpeakingLearningPackageApiError(Exception):
    def __init__(self, status_code: int, detail: Any) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail if isinstance(detail, str) else str(detail))


def _author_truncated_detail(audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "reason": "author_truncated",
        "stop_reason": audit.get("stop_reason"),
        "output_tokens": audit.get("output_tokens"),
        "model": audit.get("model"),
    }


async def create_speaking_learning_package_api(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    constraints: dict[str, Any],
    author_mode: Literal["claude", "template", "auto"] = "auto",
    use_cache: bool = True,
) -> SpeakingLearningPackageOut:
    result = await generate_speaking_learning_package(
        db,
        student_id=student_id,
        language_id=language_id,
        constraints_payload=constraints,
        author_mode=author_mode,  # type: ignore[arg-type]
        use_cache=use_cache,
    )
    if not result.success or result.package is None:
        if result.reason == "author_truncated":
            raise SpeakingLearningPackageApiError(
                422,
                _author_truncated_detail(result.audit or {}),
            )
        raise SpeakingLearningPackageApiError(
            422,
            result.reason or "Learning package generation failed.",
        )
    return SpeakingLearningPackageOut(
        success=True,
        cached=result.cached,
        content_item_id=result.content_item_id,
        package_id=result.package.package_id,
        status=result.package.status.value,
        constraints_fingerprint=result.package.constraints_fingerprint,
        content_fingerprint=result.package.content_fingerprint,
        outcome=result.outcome.value,
        package=project_package_for_student(result.package),
        audit=result.audit,
    )


async def get_speaking_learning_package_api(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    package_id: str,
) -> SpeakingLearningPackageOut:
    item = await get_package_item_by_id(
        db, student_id=student_id, language_id=language_id, package_id=package_id
    )
    if item is None:
        raise SpeakingLearningPackageApiError(404, "Learning package not found.")
    pkg = package_from_item(item)
    if pkg is None:
        raise SpeakingLearningPackageApiError(404, "Learning package payload missing.")
    return SpeakingLearningPackageOut(
        success=True,
        cached=True,
        content_item_id=item.id,
        package_id=pkg.package_id,
        status=pkg.status.value,
        constraints_fingerprint=pkg.constraints_fingerprint,
        content_fingerprint=pkg.content_fingerprint,
        outcome="success",
        package=project_package_for_student(pkg),
        audit=audit_from_item(item),
    )


async def get_speaking_learning_package_status_api(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    package_id: str,
) -> SpeakingLearningPackageStatusOut:
    item = await get_package_item_by_id(
        db, student_id=student_id, language_id=language_id, package_id=package_id
    )
    if item is None:
        raise SpeakingLearningPackageApiError(404, "Learning package not found.")
    status = status_from_item(item)
    return SpeakingLearningPackageStatusOut(**status)
