import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.academic_grades import MIN_ACADEMIC_GRADE, MAX_ACADEMIC_GRADE
from app.core.deps import require_role
from app.db.session import get_db
from app.models.catalog import Subject
from app.models.user import User, UserRole
from app.schemas.teacher_setup import (
    TeacherCourseCreate,
    TeacherProfileUpdate,
    TeacherSetupCompleteOut,
    TeacherSetupStatusOut,
    TeacherTeachingUpdate,
)
from app.schemas.teacher_profile_cv import (
    TeacherAchievementCreate,
    TeacherAchievementOut,
    TeacherAchievementUpdate,
    TeacherProfileCvOut,
    TeacherQualificationCreate,
    TeacherQualificationOut,
    TeacherQualificationUpdate,
    TeacherTeachingExperienceCreate,
    TeacherTeachingExperienceOut,
    TeacherTeachingExperienceUpdate,
)
from app.core.reference_catalog import ensure_reference_subjects, is_subject_allowed_for_grade
from app.services import teacher_setup_service
from app.services import teacher_profile_cv_service
from app.services import teacher_portfolio_service
from app.schemas.teacher_portfolio import (
    TeacherPortfolioEditOut,
    TeacherProfessionalDocumentOut,
    TeacherProfessionalDocumentUpdate,
    TeacherWhyStudyPointCreate,
    TeacherWhyStudyPointOut,
    TeacherWhyStudyPointUpdate,
    TeachingImpactOut,
    TeachingImpactUpdate,
    TeachingPhilosophyOut,
    TeachingPhilosophyUpdate,
)
from app.schemas.teacher_ai_profile import TeacherAiProfileOut, TeacherAiProfileUpdate
from app.services import teacher_ai_profile_service

router = APIRouter(prefix="/teacher/setup", tags=["Teacher Setup"])


@router.get("/status", response_model=TeacherSetupStatusOut)
async def setup_status(
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    status = await teacher_setup_service.get_setup_status(db, teacher)
    await db.commit()
    return status


@router.put("/profile", response_model=TeacherSetupStatusOut)
async def update_profile(
    body: TeacherProfileUpdate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    status = await teacher_setup_service.update_profile(db, teacher, body.full_name, body.bio)
    await db.commit()
    return status


@router.get("/ai-profile", response_model=TeacherAiProfileOut)
async def get_ai_profile(
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await teacher_ai_profile_service.get_ai_profile(db, teacher)


@router.put("/ai-profile", response_model=TeacherAiProfileOut)
async def update_ai_profile(
    body: TeacherAiProfileUpdate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    profile = await teacher_ai_profile_service.update_ai_profile(db, teacher, body)
    await db.commit()
    return profile


@router.post("/avatar", response_model=TeacherSetupStatusOut)
async def upload_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    content = await file.read()
    if not content or len(content) < 32:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ملف الصورة فارغ أو غير صالح — أعد اختيار الصورة",
        )
    ext = Path(file.filename or "avatar.jpg").suffix or ".jpg"
    filename = f"avatar_{uuid.uuid4().hex[:10]}{ext}"
    url = await teacher_setup_service.save_profile_image_async(
        db,
        teacher,
        filename=filename,
        content=content,
        mime_type=file.content_type,
    )
    status = await teacher_setup_service.set_profile_image(db, teacher, url)
    await db.commit()
    return status


@router.put("/teaching", response_model=TeacherSetupStatusOut)
async def update_teaching(
    body: TeacherTeachingUpdate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    status = await teacher_setup_service.update_teaching(db, teacher, body.subject_ids, body.grades)
    await db.commit()
    return status


@router.get("/subjects", response_model=list[dict])
async def subjects_for_teacher(
    grade: int = Query(..., ge=MIN_ACADEMIC_GRADE, le=MAX_ACADEMIC_GRADE),
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    await ensure_reference_subjects(db, grades=range(grade, grade + 1))
    result = await db.execute(
        select(Subject).where(Subject.grade == grade, Subject.is_active.is_(True)).order_by(Subject.name_ar)
    )
    rows = [
        {"id": s.id, "name_ar": s.name_ar, "grade": s.grade, "slug": s.slug}
        for s in result.scalars().all()
        if is_subject_allowed_for_grade(s.slug, s.grade)
    ]
    await db.commit()
    return rows


@router.post("/courses", response_model=TeacherSetupStatusOut)
async def create_course(
    body: TeacherCourseCreate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    status = await teacher_setup_service.create_course(
        db, teacher, title=body.title, subject_id=body.subject_id, grade=body.grade, price=body.price
    )
    await db.commit()
    return status


@router.post("/complete", response_model=TeacherSetupCompleteOut)
async def complete_setup(
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    status = await teacher_setup_service.complete_setup(db, teacher)
    await db.commit()
    return TeacherSetupCompleteOut()


@router.get("/cv", response_model=TeacherProfileCvOut)
async def get_profile_cv(
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await teacher_profile_cv_service.get_teacher_cv(db, teacher)


@router.post("/qualifications", response_model=TeacherQualificationOut)
async def create_qualification(
    body: TeacherQualificationCreate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    out = await teacher_profile_cv_service.create_qualification(db, teacher, body)
    await db.commit()
    return out


@router.put("/qualifications/{entry_id}", response_model=TeacherQualificationOut)
async def update_qualification(
    entry_id: int,
    body: TeacherQualificationUpdate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    out = await teacher_profile_cv_service.update_qualification(db, teacher, entry_id, body)
    await db.commit()
    return out


@router.delete("/qualifications/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_qualification(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    await teacher_profile_cv_service.delete_qualification(db, teacher, entry_id)
    await db.commit()


@router.post("/teaching-experiences", response_model=TeacherTeachingExperienceOut)
async def create_teaching_experience(
    body: TeacherTeachingExperienceCreate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    out = await teacher_profile_cv_service.create_teaching_experience(db, teacher, body)
    await db.commit()
    return out


@router.put("/teaching-experiences/{entry_id}", response_model=TeacherTeachingExperienceOut)
async def update_teaching_experience(
    entry_id: int,
    body: TeacherTeachingExperienceUpdate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    out = await teacher_profile_cv_service.update_teaching_experience(db, teacher, entry_id, body)
    await db.commit()
    return out


@router.delete("/teaching-experiences/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_teaching_experience(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    await teacher_profile_cv_service.delete_teaching_experience(db, teacher, entry_id)
    await db.commit()


@router.post("/achievements", response_model=TeacherAchievementOut)
async def create_achievement(
    body: TeacherAchievementCreate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    out = await teacher_profile_cv_service.create_achievement(db, teacher, body)
    await db.commit()
    return out


@router.put("/achievements/{entry_id}", response_model=TeacherAchievementOut)
async def update_achievement(
    entry_id: int,
    body: TeacherAchievementUpdate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    out = await teacher_profile_cv_service.update_achievement(db, teacher, entry_id, body)
    await db.commit()
    return out


@router.delete("/achievements/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_achievement(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    await teacher_profile_cv_service.delete_achievement(db, teacher, entry_id)
    await db.commit()


@router.get("/portfolio", response_model=TeacherPortfolioEditOut)
async def get_portfolio(
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await teacher_portfolio_service.get_portfolio_for_edit(db, teacher)


@router.put("/portfolio/impact", response_model=TeachingImpactOut)
async def update_portfolio_impact(
    body: TeachingImpactUpdate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    out = await teacher_portfolio_service.update_teaching_impact(db, teacher, body)
    await db.commit()
    return out


@router.put("/portfolio/philosophy", response_model=TeachingPhilosophyOut)
async def update_portfolio_philosophy(
    body: TeachingPhilosophyUpdate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    out = await teacher_portfolio_service.update_teaching_philosophy(db, teacher, body)
    await db.commit()
    return out


@router.post("/why-study-points", response_model=TeacherWhyStudyPointOut)
async def create_why_study_point(
    body: TeacherWhyStudyPointCreate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    out = await teacher_portfolio_service.create_why_study_point(db, teacher, body)
    await db.commit()
    return out


@router.put("/why-study-points/{entry_id}", response_model=TeacherWhyStudyPointOut)
async def update_why_study_point(
    entry_id: int,
    body: TeacherWhyStudyPointUpdate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    out = await teacher_portfolio_service.update_why_study_point(db, teacher, entry_id, body)
    await db.commit()
    return out


@router.delete("/why-study-points/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_why_study_point(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    await teacher_portfolio_service.delete_why_study_point(db, teacher, entry_id)
    await db.commit()


@router.post("/documents", response_model=TeacherProfessionalDocumentOut)
async def upload_document(
    title: str = Query(..., min_length=1, max_length=255),
    document_type: str = Query("certificate", pattern="^(certificate|degree|training)$"),
    sort_order: int = Query(0, ge=0),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    out = await teacher_portfolio_service.upload_professional_document(
        db, teacher, title=title, document_type=document_type, file=file, sort_order=sort_order
    )
    await db.commit()
    return out


@router.put("/documents/{doc_id}", response_model=TeacherProfessionalDocumentOut)
async def update_document(
    doc_id: int,
    body: TeacherProfessionalDocumentUpdate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    out = await teacher_portfolio_service.update_professional_document(
        db,
        teacher,
        doc_id,
        title=body.title,
        document_type=body.document_type,
        sort_order=body.sort_order,
    )
    await db.commit()
    return out


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    await teacher_portfolio_service.delete_professional_document(db, teacher, doc_id)
    await db.commit()
