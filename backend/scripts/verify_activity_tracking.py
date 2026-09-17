"""Verify student activity tracking foundation."""

from __future__ import annotations

import asyncio
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.student_activity_tracking import EngagementEventType, StudentActivitySession
from app.models.user import User, UserRole
from app.services import student_activity_tracking_service


async def main() -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.role == UserRole.student).limit(1)
        )
        student = result.scalar_one_or_none()
        if not student:
            print("No student found")
            return 1

        session = await student_activity_tracking_service.on_student_login(
            db, student.id, auth_session_id=None
        )
        await student_activity_tracking_service.record_engagement_event(
            db,
            student.id,
            EngagementEventType.page_navigation,
            path="/student/dashboard",
        )
        await student_activity_tracking_service.record_engagement_event(
            db,
            student.id,
            EngagementEventType.lesson_opened,
            resource_type="lesson",
            resource_id=1,
        )
        summary = await student_activity_tracking_service.get_student_activity_summary(db, student.id)
        await db.commit()

        print("student_id", student.id)
        print("session_id", session.id)
        print("summary", summary)
        print("OK activity tracking foundation")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
