"""Student Learning Journey API (Phase G) — compose-only graph.

GET /api/student/languages/journey
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.language_learning_journey import (
    JourneyLevelOut,
    JourneyProgressOut,
    JourneyStageOut,
    LearningJourneyOut,
)
from app.services.language_access_service import require_language_learning_ready
from app.services.language_learning_journey import build_learning_journey_graph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/student/languages", tags=["Student Learning Journey"])


@router.get("/journey", response_model=LearningJourneyOut)
async def learning_journey(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    try:
        graph = await build_learning_journey_graph(db, student_id=student.id)
    except Exception:  # noqa: BLE001
        logger.exception("learning_journey_failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Learning journey is temporarily unavailable.",
        ) from None

    data = graph.to_dict()
    return LearningJourneyOut(
        enabled=data["enabled"],
        anchor_cefr=data["anchor_cefr"],
        current_grammar_id=data["current_grammar_id"],
        next_grammar_id=data["next_grammar_id"],
        curriculum_version=data["curriculum_version"],
        progress=JourneyProgressOut(**data["progress"]),
        levels=[
            JourneyLevelOut(
                cefr=lv["cefr"],
                status=lv["status"],
                expanded=lv["expanded"],
                completed_count=lv["completed_count"],
                total_count=lv["total_count"],
                stages=[JourneyStageOut(**s) for s in lv["stages"]],
            )
            for lv in data["levels"]
        ],
        schema_version=data["schema_version"],
    )
