"""Language certificate eligibility, issuance, PDF generation, and verification."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.language.analytics import LanguageAnalytics
from app.models.language.certificate import LanguageCertificate
from app.models.language.enums import LanguageLevel
from app.models.language.profile import LanguageStudentProfile
from app.models.user import User
from app.services.language_level_utils import CERTIFICATE_LEVELS, CEFR_RANK, meets_certificate_threshold
from app.services.language_subscription_service import get_default_language

settings = get_settings()

SKILL_KEYS = ("reading", "listening", "writing", "speaking")


def _frontend_base_url() -> str:
    origins = [o.strip() for o in (settings.CORS_ORIGINS or "").split(",") if o.strip()]
    return (origins[0] if origins else "http://localhost:5173").rstrip("/")


def _verification_path(certificate_number: str) -> str:
    return f"/verify-certificate/{certificate_number}"


def _verification_url(certificate_number: str) -> str:
    return f"{_frontend_base_url()}{_verification_path(certificate_number)}"


def _analytics_skill_levels(analytics: LanguageAnalytics | None) -> dict[str, LanguageLevel | None]:
    if not analytics:
        return {k: None for k in SKILL_KEYS}
    return {
        "reading": analytics.reading_level,
        "listening": analytics.listening_level,
        "writing": analytics.writing_level,
        "speaking": analytics.speaking_level,
    }


def _certificate_number(level: LanguageLevel) -> str:
    year = datetime.now(timezone.utc).year
    suffix = uuid.uuid4().hex[:8].upper()
    return f"ES-LANG-{year}-{level.value}-{suffix}"


def _verification_code() -> str:
    return secrets.token_hex(6).upper()


def _certificate_pdf_path(student_id: int, certificate_number: str) -> Path:
    upload_root = Path(settings.UPLOAD_DIR)
    dest_dir = upload_root / f"student_{student_id}" / "certificates"
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = certificate_number.replace("/", "-")
    return dest_dir / f"{safe_name}.pdf"


def _pdf_public_url(student_id: int, certificate_number: str) -> str:
    safe_name = certificate_number.replace("/", "-")
    return f"/uploads/student_{student_id}/certificates/{safe_name}.pdf"


def generate_certificate_pdf(
    dest: Path,
    *,
    student_name: str,
    certificate_level: str,
    certificate_number: str,
    issued_at: datetime,
    verification_code: str,
    verification_url: str,
) -> None:
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    page.insert_text((72, 72), "EduSpark", fontsize=14, color=(0.15, 0.35, 0.75))
    page.insert_text((72, 120), "Language Learning Certificate", fontsize=22)
    page.insert_text((72, 155), f"CEFR Level {certificate_level}", fontsize=16, color=(0.2, 0.2, 0.2))

    page.insert_text((72, 220), "This certifies that", fontsize=12, color=(0.35, 0.35, 0.35))
    page.insert_text((72, 252), student_name, fontsize=20)
    page.insert_text(
        (72, 295),
        f"has demonstrated proficiency at CEFR level {certificate_level}",
        fontsize=12,
    )
    page.insert_text(
        (72, 318),
        "in Reading, Listening, Writing, and Speaking.",
        fontsize=12,
    )

    issue_label = issued_at.astimezone(timezone.utc).strftime("%Y-%m-%d")
    page.insert_text((72, 390), f"Certificate Number: {certificate_number}", fontsize=11)
    page.insert_text((72, 415), f"Issue Date: {issue_label}", fontsize=11)
    page.insert_text((72, 440), f"Verification Code: {verification_code}", fontsize=11)
    page.insert_text((72, 475), f"Verify at: {verification_url}", fontsize=10, color=(0.4, 0.4, 0.4))

    doc.save(str(dest))
    doc.close()


def certificate_to_dict(cert: LanguageCertificate) -> dict:
    return {
        "id": cert.id,
        "certificate_level": cert.certificate_level.value,
        "certificate_number": cert.certificate_number,
        "verification_code": cert.verification_code,
        "certificate_status": cert.certificate_status,
        "verification_url": cert.verification_url,
        "issued_at": cert.issued_at,
        "pdf_url": cert.pdf_url,
    }


async def _load_existing_certificates(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> list[LanguageCertificate]:
    rows = await db.execute(
        select(LanguageCertificate)
        .where(
            LanguageCertificate.student_id == student_id,
            LanguageCertificate.language_id == language_id,
        )
        .order_by(LanguageCertificate.issued_at.desc())
    )
    return list(rows.scalars().all())


async def _update_profile_certificate(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    certificates: list[LanguageCertificate],
) -> None:
    if not certificates:
        return
    highest = max(certificates, key=lambda c: CEFR_RANK[c.certificate_level])
    profile_row = await db.execute(
        select(LanguageStudentProfile).where(
            LanguageStudentProfile.student_id == student_id,
            LanguageStudentProfile.language_id == language_id,
        )
    )
    profile = profile_row.scalar_one_or_none()
    if not profile:
        return
    profile.certificate_level = highest.certificate_level
    profile.certificate_awarded_at = highest.issued_at


async def _issue_certificate(
    db: AsyncSession,
    *,
    student: User,
    language_id: int,
    level: LanguageLevel,
) -> LanguageCertificate:
    cert_number = _certificate_number(level)
    verify_code = _verification_code()
    verify_url = _verification_url(cert_number)
    issued_at = datetime.now(timezone.utc)

    pdf_path = _certificate_pdf_path(student.id, cert_number)
    generate_certificate_pdf(
        pdf_path,
        student_name=student.name,
        certificate_level=level.value,
        certificate_number=cert_number,
        issued_at=issued_at,
        verification_code=verify_code,
        verification_url=verify_url,
    )

    cert = LanguageCertificate(
        student_id=student.id,
        language_id=language_id,
        certificate_level=level,
        certificate_number=cert_number,
        verification_code=verify_code,
        certificate_status="issued",
        verification_url=verify_url,
        issued_at=issued_at,
        pdf_url=_pdf_public_url(student.id, cert_number),
    )
    db.add(cert)
    await db.flush()
    return cert


async def sync_eligible_certificates(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int | None = None,
) -> list[LanguageCertificate]:
    """Issue certificates for all eligible levels not yet awarded."""
    language = await get_default_language(db) if language_id is None else None
    lang_id = language.id if language else language_id
    if lang_id is None:
        raise ValueError("language_id required")

    student_row = await db.execute(select(User).where(User.id == student_id))
    student = student_row.scalar_one_or_none()
    if not student:
        return []

    analytics_row = await db.execute(
        select(LanguageAnalytics).where(
            LanguageAnalytics.student_id == student_id,
            LanguageAnalytics.language_id == lang_id,
        )
    )
    analytics = analytics_row.scalar_one_or_none()
    levels = _analytics_skill_levels(analytics)

    existing = await _load_existing_certificates(db, student_id=student_id, language_id=lang_id)
    issued_levels = {c.certificate_level for c in existing}

    for level in CERTIFICATE_LEVELS:
        if level in issued_levels:
            continue
        if meets_certificate_threshold(levels, level):
            cert = await _issue_certificate(
                db,
                student=student,
                language_id=lang_id,
                level=level,
            )
            existing.append(cert)
            issued_levels.add(level)

    if existing:
        await _update_profile_certificate(
            db,
            student_id=student_id,
            language_id=lang_id,
            certificates=existing,
        )
    return existing


def build_eligibility(
    levels: dict[str, LanguageLevel | None],
    certificates: list[LanguageCertificate],
) -> list[dict]:
    issued_levels = {c.certificate_level for c in certificates}
    out: list[dict] = []
    for level in CERTIFICATE_LEVELS:
        out.append(
            {
                "level": level.value,
                "eligible": meets_certificate_threshold(levels, level),
                "issued": level in issued_levels,
            }
        )
    return out


async def list_student_certificates(db: AsyncSession, *, student_id: int) -> dict:
    language = await get_default_language(db)
    await sync_eligible_certificates(db, student_id=student_id, language_id=language.id)

    certificates = await _load_existing_certificates(
        db, student_id=student_id, language_id=language.id
    )
    analytics_row = await db.execute(
        select(LanguageAnalytics).where(
            LanguageAnalytics.student_id == student_id,
            LanguageAnalytics.language_id == language.id,
        )
    )
    analytics = analytics_row.scalar_one_or_none()
    levels = _analytics_skill_levels(analytics)

    return {
        "certificates": [certificate_to_dict(c) for c in certificates],
        "eligibility": build_eligibility(levels, certificates),
    }


async def get_latest_certificate_summary(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> dict | None:
    certificates = await _load_existing_certificates(
        db, student_id=student_id, language_id=language_id
    )
    if not certificates:
        return None
    latest = max(certificates, key=lambda c: (CEFR_RANK[c.certificate_level], c.issued_at))
    return {
        "certificate_level": latest.certificate_level.value,
        "certificate_number": latest.certificate_number,
        "issued_at": latest.issued_at,
        "verification_url": latest.verification_url,
        "pdf_url": latest.pdf_url,
    }


async def verify_certificate(db: AsyncSession, *, certificate_number: str) -> dict:
    row = await db.execute(
        select(LanguageCertificate, User)
        .join(User, User.id == LanguageCertificate.student_id)
        .where(LanguageCertificate.certificate_number == certificate_number)
    )
    result = row.one_or_none()
    if not result:
        return {
            "valid": False,
            "student_name": None,
            "certificate_level": None,
            "issued_at": None,
            "certificate_number": certificate_number,
        }

    cert, student = result
    if cert.certificate_status != "issued":
        return {
            "valid": False,
            "student_name": student.name,
            "certificate_level": cert.certificate_level.value,
            "issued_at": cert.issued_at,
            "certificate_number": cert.certificate_number,
        }

    return {
        "valid": True,
        "student_name": student.name,
        "certificate_level": cert.certificate_level.value,
        "issued_at": cert.issued_at,
        "certificate_number": cert.certificate_number,
    }
