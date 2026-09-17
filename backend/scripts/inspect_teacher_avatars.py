"""Inspect teacher profile images vs course card API fields."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal
from app.models.catalog import Course, TeacherProfile
from app.models.user import User  # noqa: F401 — register mapper
from app.services import student_courses_service
from app.utils.media_urls import teacher_avatar_url


async def main() -> None:
    async with AsyncSessionLocal() as db:
        profiles = await db.execute(
            select(TeacherProfile).where(TeacherProfile.image_url.isnot(None))
        )
        with_img = list(profiles.scalars().all())
        print(f"Teacher profiles with image_url: {len(with_img)}")
        for tp in with_img[:5]:
            print(f"  user_id={tp.user_id} name={tp.full_name!r} url={tp.image_url!r}")

        result = await db.execute(
            select(Course)
            .where(Course.is_published.is_(True))
            .options(selectinload(Course.teacher_profile), selectinload(Course.subject))
            .limit(3)
        )
        courses = list(result.scalars().all())
        print("\nSample published courses:")
        for c in courses:
            tp = c.teacher_profile
            pub = teacher_avatar_url(tp.image_url) if tp else None
            raw = repr(tp.image_url) if tp else None
            print(f"  course {c.id}: teacher={tp.full_name if tp else None} raw={raw} public={pub!r}")

        student = await db.scalar(
            select(User).where(User.role == "student").order_by(User.id).limit(1)
        )
        if student:
            dash = await student_courses_service.list_student_dashboard(db, student.id)
            sample = dash.courses[0] if dash.courses else None
            print(f"\nDashboard for student {student.id} ({student.email}):")
            print(f"  courses={len(dash.courses)}")
            if sample:
                print(
                    json.dumps(
                        {
                            "id": sample.id,
                            "teacher_name": sample.teacher_name,
                            "teacher_image_url": sample.teacher_image_url,
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )


if __name__ == "__main__":
    asyncio.run(main())
