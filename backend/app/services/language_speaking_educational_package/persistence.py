"""Persist frozen Learning Packages in LanguageContentItem (no new Alembic table)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.content import LanguageContentItem
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.services.language_educational_package.constraints import PackageConstraints
from app.services.language_educational_package.types import EducationalPackage

CONTENT_TYPE = "speaking_learning_package"
BODY_PACKAGE_KEY = "educational_package"
BODY_CONSTRAINTS_KEY = "package_constraints"
BODY_AUDIT_KEY = "generation_audit"
SOURCE_TAG = "speaking_elp_e1"


def _content_item_has_student_owner() -> bool:
    return hasattr(LanguageContentItem, "student_id")


def _student_owner_clause(student_id: int):
    json_owner = LanguageContentItem.body_json["owner_student_id"].astext == str(student_id)
    if not _content_item_has_student_owner():
        return json_owner
    return or_(
        LanguageContentItem.student_id == student_id,
        and_(LanguageContentItem.student_id.is_(None), json_owner),
    )


def _level_from_cefr(cefr: str) -> LanguageLevel:
    try:
        return LanguageLevel(cefr.upper())
    except ValueError:
        return LanguageLevel.A2


def build_body_json(
    *,
    student_id: int | None = None,
    package: EducationalPackage,
    constraints: PackageConstraints,
    audit: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "source": SOURCE_TAG,
        BODY_PACKAGE_KEY: package.to_dict(),
        BODY_CONSTRAINTS_KEY: constraints.to_dict(),
        BODY_AUDIT_KEY: dict(audit),
        "package_id": package.package_id,
        "constraints_fingerprint": package.constraints_fingerprint,
        "content_fingerprint": package.content_fingerprint,
        "status": package.status.value,
        "immutable": True,
    }
    if student_id is not None:
        payload["owner_student_id"] = student_id
    return payload


async def persist_frozen_package(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    package: EducationalPackage,
    constraints: PackageConstraints,
    audit: dict[str, Any],
) -> LanguageContentItem:
    item_kwargs = dict(
        language_id=language_id,
        skill=LanguageSkill.speaking,
        level=_level_from_cefr(constraints.official_cefr),
        content_type=CONTENT_TYPE,
        title=(package.input_material.title or "Learning Package")[:500],
        body_json=build_body_json(student_id=student_id, package=package, constraints=constraints, audit=audit),
        sort_order=0,
        is_published=True,
    )
    if _content_item_has_student_owner():
        item_kwargs["student_id"] = student_id
    item = LanguageContentItem(**item_kwargs)
    db.add(item)
    await db.flush()
    return item


async def get_package_item_by_id(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    package_id: str,
) -> LanguageContentItem | None:
    clauses = [
        LanguageContentItem.language_id == language_id,
        LanguageContentItem.skill == LanguageSkill.speaking,
        LanguageContentItem.content_type == CONTENT_TYPE,
        LanguageContentItem.body_json["package_id"].astext == package_id,
    ]
    clauses.append(_student_owner_clause(student_id))
    result = await db.execute(select(LanguageContentItem).where(*clauses))
    return result.scalar_one_or_none()


async def find_cached_package_item(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    constraints_fingerprint: str,
) -> LanguageContentItem | None:
    clauses = [
        LanguageContentItem.language_id == language_id,
        LanguageContentItem.skill == LanguageSkill.speaking,
        LanguageContentItem.content_type == CONTENT_TYPE,
        LanguageContentItem.body_json["constraints_fingerprint"].astext == constraints_fingerprint,
        LanguageContentItem.is_published.is_(True),
    ]
    clauses.append(_student_owner_clause(student_id))
    result = await db.execute(
        select(LanguageContentItem)
        .where(*clauses)
        .order_by(LanguageContentItem.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def package_from_item(item: LanguageContentItem) -> EducationalPackage | None:
    body = item.body_json if isinstance(item.body_json, dict) else {}
    raw = body.get(BODY_PACKAGE_KEY)
    if not isinstance(raw, dict):
        return None
    return EducationalPackage.from_dict(raw)


def constraints_from_item(item: LanguageContentItem) -> PackageConstraints | None:
    body = item.body_json if isinstance(item.body_json, dict) else {}
    raw = body.get(BODY_CONSTRAINTS_KEY)
    if not isinstance(raw, dict):
        return None
    return PackageConstraints.from_dict(raw)


def audit_from_item(item: LanguageContentItem) -> dict[str, Any]:
    body = item.body_json if isinstance(item.body_json, dict) else {}
    raw = body.get(BODY_AUDIT_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


def status_from_item(item: LanguageContentItem) -> dict[str, Any]:
    body = item.body_json if isinstance(item.body_json, dict) else {}
    pkg = package_from_item(item)
    return {
        "content_item_id": item.id,
        "package_id": body.get("package_id") or (pkg.package_id if pkg else None),
        "status": body.get("status") or (pkg.status.value if pkg else "unknown"),
        "constraints_fingerprint": body.get("constraints_fingerprint"),
        "content_fingerprint": body.get("content_fingerprint"),
        "immutable": bool(body.get("immutable")),
        "title": item.title,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "audit": audit_from_item(item),
    }
