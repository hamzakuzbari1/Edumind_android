"""FastAPI dependency — block listening routes when migrations are missing."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.listening_deployment import assert_listening_deployment_ready
from app.db.session import get_db


async def require_listening_deployment_ready(
    db: AsyncSession = Depends(get_db),
) -> None:
    await assert_listening_deployment_ready(db)
