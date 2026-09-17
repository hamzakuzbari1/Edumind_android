"""Verify parent attendance analytics aggregation."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.user import User, UserRole
from app.services.parent_attendance_analytics_service import build_parent_attendance_analytics


async def main() -> int:
    async with AsyncSessionLocal() as db:
        student = (
            await db.execute(select(User).where(User.role == UserRole.student).limit(1))
        ).scalar_one_or_none()
        if not student:
            print("No student found")
            return 1

        data = await build_parent_attendance_analytics(db, student.id)
        print("student_id", student.id)
        print("overview", data["overview"])
        print("weekly", data["weekly_analytics"]["period_label"], data["weekly_analytics"]["total_minutes"])
        print("monthly", data["monthly_analytics"]["period_label"], data["monthly_analytics"]["total_minutes"])
        print("login_history rows", len(data["login_history"]))
        print("daily_breakdown days", len(data["daily_breakdown"]))
        print("OK parent attendance analytics")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
