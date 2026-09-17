from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai_job import AiJobOut
from app.services import ai_job_service

router = APIRouter(prefix="/ai", tags=["AI Jobs"])


@router.get("/jobs/{job_id}", response_model=AiJobOut)
async def get_ai_job(
    job_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await ai_job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المهمة غير موجودة")
    return AiJobOut.model_validate(job)
