"""Teacher portfolio — impact, philosophy, why-study, documents."""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.catalog import TeacherProfile
from app.models.teacher_profile_cv import TeacherProfessionalDocument, TeacherWhyStudyPoint
from app.models.user import User
from app.schemas.teacher_portfolio import (
    TeacherAcademicStatisticsOut,
    TeacherPortfolioEditOut,
    TeacherProfessionalDocumentOut,
    TeacherWhyStudyPointCreate,
    TeacherWhyStudyPointOut,
    TeacherWhyStudyPointUpdate,
    TeachingImpactOut,
    TeachingImpactUpdate,
    TeachingPhilosophyOut,
    TeachingPhilosophyUpdate,
)
from app.services.teacher_portfolio_stats_service import build_teacher_academic_statistics
from app.services.teacher_setup_service import get_or_create_teacher_profile
from app.utils.media_urls import public_upload_url

settings = get_settings()

ALLOWED_DOC_MIME = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}


def build_impact_highlights(tp: TeacherProfile, subject_name: str | None = None) -> list[str]:
    subject = subject_name or "المادة"
    lines: list[str] = []
    if tp.impact_total_students:
        lines.append(f"درّس أكثر من {tp.impact_total_students} طالب")
    if tp.impact_grade12_students:
        lines.append(f"درّس {tp.impact_grade12_students} طالب في الصف الثاني عشر")
    if tp.impact_completed_subject:
        lines.append(f"أكمل {subject} بنجاح أكثر من {tp.impact_completed_subject} طالب")
    if tp.impact_excellent_grades:
        lines.append(f"حقّق {tp.impact_excellent_grades} طالباً درجات ممتازة")
    if tp.impact_years_teaching:
        lines.append(f"خبرة {tp.impact_years_teaching} سنة في تدريس {subject}")
    return lines


def teaching_impact_out(tp: TeacherProfile, subject_name: str | None = None) -> TeachingImpactOut:
    return TeachingImpactOut(
        total_students_taught=tp.impact_total_students,
        grade12_students_taught=tp.impact_grade12_students,
        students_completed_subject=tp.impact_completed_subject,
        students_excellent_grades=tp.impact_excellent_grades,
        years_teaching_subject=tp.impact_years_teaching,
        highlights=build_impact_highlights(tp, subject_name),
    )


def teaching_philosophy_out(tp: TeacherProfile) -> TeachingPhilosophyOut:
    return TeachingPhilosophyOut(
        teaching_style=tp.philosophy_teaching_style,
        lesson_approach=tp.philosophy_lesson_approach,
        exam_preparation_strategy=tp.philosophy_exam_preparation,
    )


def _why_point_out(row: TeacherWhyStudyPoint) -> TeacherWhyStudyPointOut:
    return TeacherWhyStudyPointOut(
        id=row.id, title=row.title, description=row.description, sort_order=row.sort_order
    )


def _document_out(row: TeacherProfessionalDocument) -> TeacherProfessionalDocumentOut:
    return TeacherProfessionalDocumentOut(
        id=row.id,
        title=row.title,
        document_type=row.document_type,
        file_url=public_upload_url(row.file_url) or row.file_url,
        original_filename=row.original_filename,
        mime_type=row.mime_type,
        sort_order=row.sort_order,
    )


async def load_portfolio_public(
    db: AsyncSession,
    teacher_profile_id: int,
    *,
    subject_name: str | None = None,
) -> dict:
    result = await db.execute(
        select(TeacherProfile)
        .where(TeacherProfile.id == teacher_profile_id)
        .options(
            selectinload(TeacherProfile.why_study_points),
            selectinload(TeacherProfile.professional_documents),
        )
    )
    tp = result.scalar_one_or_none()
    if not tp:
        return {
            "teaching_impact": TeachingImpactOut(),
            "teaching_philosophy": TeachingPhilosophyOut(),
            "why_study_points": [],
            "professional_documents": [],
            "academic_statistics": TeacherAcademicStatisticsOut(),
        }
    stats = await build_teacher_academic_statistics(db, teacher_profile_id)
    return {
        "teaching_impact": teaching_impact_out(tp, subject_name),
        "teaching_philosophy": teaching_philosophy_out(tp),
        "why_study_points": [_why_point_out(p) for p in tp.why_study_points],
        "professional_documents": [_document_out(d) for d in tp.professional_documents],
        "academic_statistics": stats,
    }


async def get_portfolio_for_edit(db: AsyncSession, user: User) -> TeacherPortfolioEditOut:
    tp = await get_or_create_teacher_profile(db, user)
    data = await load_portfolio_public(db, tp.id)
    return TeacherPortfolioEditOut(**data)


async def update_teaching_impact(
    db: AsyncSession, user: User, body: TeachingImpactUpdate
) -> TeachingImpactOut:
    tp = await get_or_create_teacher_profile(db, user)
    tp.impact_total_students = body.total_students_taught
    tp.impact_grade12_students = body.grade12_students_taught
    tp.impact_completed_subject = body.students_completed_subject
    tp.impact_excellent_grades = body.students_excellent_grades
    tp.impact_years_teaching = body.years_teaching_subject
    await db.flush()
    return teaching_impact_out(tp)


async def update_teaching_philosophy(
    db: AsyncSession, user: User, body: TeachingPhilosophyUpdate
) -> TeachingPhilosophyOut:
    tp = await get_or_create_teacher_profile(db, user)
    tp.philosophy_teaching_style = body.teaching_style.strip() if body.teaching_style else None
    tp.philosophy_lesson_approach = body.lesson_approach.strip() if body.lesson_approach else None
    tp.philosophy_exam_preparation = (
        body.exam_preparation_strategy.strip() if body.exam_preparation_strategy else None
    )
    await db.flush()
    return teaching_philosophy_out(tp)


async def _owned_why_point(db: AsyncSession, user: User, entry_id: int) -> TeacherWhyStudyPoint:
    tp = await get_or_create_teacher_profile(db, user)
    row = await db.get(TeacherWhyStudyPoint, entry_id)
    if not row or row.teacher_profile_id != tp.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="العنصر غير موجود")
    return row


async def create_why_study_point(
    db: AsyncSession, user: User, body: TeacherWhyStudyPointCreate
) -> TeacherWhyStudyPointOut:
    tp = await get_or_create_teacher_profile(db, user)
    row = TeacherWhyStudyPoint(
        teacher_profile_id=tp.id,
        title=body.title.strip(),
        description=body.description.strip() if body.description else None,
        sort_order=body.sort_order,
    )
    db.add(row)
    await db.flush()
    return _why_point_out(row)


async def update_why_study_point(
    db: AsyncSession, user: User, entry_id: int, body: TeacherWhyStudyPointUpdate
) -> TeacherWhyStudyPointOut:
    row = await _owned_why_point(db, user, entry_id)
    if body.title is not None:
        row.title = body.title.strip()
    if body.description is not None:
        row.description = body.description.strip() or None
    if body.sort_order is not None:
        row.sort_order = body.sort_order
    await db.flush()
    return _why_point_out(row)


async def delete_why_study_point(db: AsyncSession, user: User, entry_id: int) -> None:
    row = await _owned_why_point(db, user, entry_id)
    await db.delete(row)
    await db.flush()


def save_teacher_document(user_id: int, filename: str, content: bytes) -> str:
    """Legacy local-only helper; prefer store path in upload_professional_document."""
    upload_root = Path(settings.UPLOAD_DIR) / "teachers" / str(user_id) / "documents"
    upload_root.mkdir(parents=True, exist_ok=True)
    dest = upload_root / filename
    dest.write_bytes(content)
    rel = dest.resolve().relative_to(Path(settings.UPLOAD_DIR).resolve())
    return "/uploads/" + "/".join(rel.parts)


async def _owned_document(db: AsyncSession, user: User, doc_id: int) -> TeacherProfessionalDocument:
    tp = await get_or_create_teacher_profile(db, user)
    row = await db.get(TeacherProfessionalDocument, doc_id)
    if not row or row.teacher_profile_id != tp.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المستند غير موجود")
    return row


async def upload_professional_document(
    db: AsyncSession,
    user: User,
    *,
    title: str,
    document_type: str,
    file: UploadFile,
    sort_order: int = 0,
) -> TeacherProfessionalDocumentOut:
    from app.models.media import MediaAccessScope
    from app.services.media_storage.upload import build_object_key, store_and_register_media

    content = await file.read()
    if not content or len(content) < 32:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="الملف فارغ أو غير صالح")
    mime = file.content_type or "application/octet-stream"
    if mime not in ALLOWED_DOC_MIME:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="نوع الملف غير مدعوم — PDF أو صورة")

    if mime == "application/pdf" and len(content) > settings.MAX_PDF_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="حجم ملف PDF كبير جداً")

    filename = file.filename or "document.pdf"
    object_key = build_object_key(
        "teacher-documents",
        f"teacher_{user.id}",
        filename=filename,
    )
    stored = await store_and_register_media(
        db,
        content=content,
        filename=filename,
        mime_type=mime,
        uploaded_by_user_id=user.id,
        access_scope=MediaAccessScope.private.value,
        object_key=object_key,
        kind="teacher-document",
        metadata_json={"kind": "teacher_professional_document", "user_id": user.id},
        keep_local_working_copy=False,
    )

    tp = await get_or_create_teacher_profile(db, user)
    row = TeacherProfessionalDocument(
        teacher_profile_id=tp.id,
        title=title.strip(),
        document_type=document_type,
        file_url=stored.client_url,
        media_object_id=stored.media.id,
        original_filename=file.filename,
        mime_type=stored.mime_type,
        sort_order=sort_order,
    )
    db.add(row)
    await db.flush()
    return _document_out(row)


async def update_professional_document(
    db: AsyncSession, user: User, doc_id: int, *, title: str | None, document_type: str | None, sort_order: int | None
) -> TeacherProfessionalDocumentOut:
    row = await _owned_document(db, user, doc_id)
    if title is not None:
        row.title = title.strip()
    if document_type is not None:
        row.document_type = document_type
    if sort_order is not None:
        row.sort_order = sort_order
    await db.flush()
    return _document_out(row)


async def delete_professional_document(db: AsyncSession, user: User, doc_id: int) -> None:
    row = await _owned_document(db, user, doc_id)
    if row.file_url:
        try:
            rel = row.file_url.removeprefix("/uploads/")
            path = Path(settings.UPLOAD_DIR) / rel
            if path.is_file():
                path.unlink()
        except OSError:
            pass
    await db.delete(row)
    await db.flush()
