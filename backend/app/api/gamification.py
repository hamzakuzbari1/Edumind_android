from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_student_actor
from app.db.session import get_db
from app.models.user import User
from app.schemas.gamification import GamificationProfileOut
from app.services.gamification.xp_service import get_gamification_profile

router = APIRouter(prefix="/student/gamification", tags=["Gamification"])


@router.get("", response_model=GamificationProfileOut)
async def student_gamification(
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    data = await get_gamification_profile(db, student.id)
    return GamificationProfileOut(**data)
