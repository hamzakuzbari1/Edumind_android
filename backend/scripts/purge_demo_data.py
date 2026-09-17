"""Remove demo/seed users, teacher profiles, courses, and enrollments.

Usage (from backend/):
    python scripts/purge_demo_data.py          # purge
    python scripts/purge_demo_data.py --audit  # list only, no deletes
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, or_, select

from app.core.demo_guard import DEMO_TEACHER_NAMES, is_demo_email, is_demo_teacher_name
from app.db.session import AsyncSessionLocal
from app.models.attendance import StudentAttendanceRecord
from app.models.activity import StudentActivityEvent
from app.models.catalog import Course, TeacherProfile, TeacherProfileGrade, TeacherProfileSubject
from app.models.chat import ChatMessage
from app.models.enrollment import (
    Payment,
    PaymentItem,
    StudentCourseAccess,
    StudentSubjectChoice,
    StudentTeacherChoice,
)
from app.models.lesson import ContentChunk, Lesson, LessonAsset
from app.models.planner import PlannerChatMessage, PlannerLifeEvent, PlannerProfile, PlannerScheduleSlot
from app.models.profile import StudentProfile
from app.models.progress import StudentLessonProgress
from app.models.quiz import QuizAttempt, QuizQuestion
from app.db.sql_types import user_role_equals
from app.models.user import User, UserRole


async def _safe_execute(db, stmt) -> None:
    try:
        await db.execute(stmt)
    except Exception as exc:
        if "does not exist" in str(exc).lower() or "undefinedtable" in str(exc).lower():
            return
        raise


async def _delete_lessons_for_course_ids(db, course_ids: list[int]) -> None:
    if not course_ids:
        return
    lesson_ids = list(
        (await db.execute(select(Lesson.id).where(Lesson.course_id.in_(course_ids)))).scalars()
    )
    if lesson_ids:
        await db.execute(delete(LessonAsset).where(LessonAsset.lesson_id.in_(lesson_ids)))
        await db.execute(delete(QuizAttempt).where(QuizAttempt.lesson_id.in_(lesson_ids)))
        await db.execute(delete(QuizQuestion).where(QuizQuestion.lesson_id.in_(lesson_ids)))
        await db.execute(delete(ChatMessage).where(ChatMessage.lesson_id.in_(lesson_ids)))
        await db.execute(delete(ContentChunk).where(ContentChunk.lesson_id.in_(lesson_ids)))
        await db.execute(
            delete(StudentLessonProgress).where(StudentLessonProgress.lesson_id.in_(lesson_ids))
        )
        await db.execute(delete(Lesson).where(Lesson.id.in_(lesson_ids)))


async def _delete_teacher_profiles(db, tp_ids: list[int]) -> None:
    if not tp_ids:
        return
    course_ids = list(
        (await db.execute(select(Course.id).where(Course.teacher_profile_id.in_(tp_ids)))).scalars()
    )
    if course_ids:
        await db.execute(delete(PaymentItem).where(PaymentItem.course_id.in_(course_ids)))
        await db.execute(delete(StudentCourseAccess).where(StudentCourseAccess.course_id.in_(course_ids)))
        await db.execute(
            delete(StudentTeacherChoice).where(StudentTeacherChoice.teacher_profile_id.in_(tp_ids))
        )
        await _delete_lessons_for_course_ids(db, course_ids)
        await db.execute(delete(Course).where(Course.id.in_(course_ids)))
    await db.execute(
        delete(TeacherProfileSubject).where(TeacherProfileSubject.teacher_profile_id.in_(tp_ids))
    )
    await db.execute(
        delete(TeacherProfileGrade).where(TeacherProfileGrade.teacher_profile_id.in_(tp_ids))
    )
    await db.execute(delete(TeacherProfile).where(TeacherProfile.id.in_(tp_ids)))


async def _collect_demo_user_ids(db) -> list[int]:
    from app.core.demo_guard import DEMO_EMAILS

    result = await db.execute(
        select(User.id, User.email, User.name, User.role).where(
            or_(
                User.email.ilike("%@eduspark.sy"),
                User.email.in_(tuple(DEMO_EMAILS)),
            )
        )
    )
    return [row[0] for row in result.all()]


async def _collect_demo_teacher_profile_ids(db) -> list[int]:
    ids: set[int] = set()
    if DEMO_TEACHER_NAMES:
        by_name = await db.execute(
            select(TeacherProfile.id, TeacherProfile.full_name, TeacherProfile.user_id).where(
                TeacherProfile.full_name.in_(tuple(DEMO_TEACHER_NAMES))
            )
        )
        for row in by_name.all():
            ids.add(row[0])
    demo_user_ids = await _collect_demo_user_ids(db)
    if demo_user_ids:
        by_user = await db.execute(
            select(TeacherProfile.id).where(TeacherProfile.user_id.in_(demo_user_ids))
        )
        ids.update(by_user.scalars().all())
    return list(ids)


async def audit() -> None:
    async with AsyncSessionLocal() as db:
        print("=== Demo users (@eduspark.sy) ===")
        from app.core.demo_guard import DEMO_EMAILS

        users = (
            await db.execute(
                select(User.id, User.email, User.name, User.role).where(
                    or_(
                        User.email.ilike("%@eduspark.sy"),
                        User.email.in_(tuple(DEMO_EMAILS)),
                    )
                )
            )
        ).all()
        if not users:
            print("  (none)")
        for uid, email, name, role in users:
            print(f"  user_id={uid} email={email} name={name} role={role.value}")

        print("\n=== Demo-named teacher profiles ===")
        profiles = (
            await db.execute(
                select(TeacherProfile.id, TeacherProfile.full_name, TeacherProfile.user_id).where(
                    TeacherProfile.full_name.in_(tuple(DEMO_TEACHER_NAMES))
                )
            )
        ).all()
        if not profiles:
            print("  (none)")
        for pid, full_name, user_id in profiles:
            print(f"  profile_id={pid} full_name={full_name!r} user_id={user_id}")

        print("\n=== All teachers in student catalog (published courses) ===")
        catalog = (
            await db.execute(
                select(
                    TeacherProfile.id,
                    TeacherProfile.full_name,
                    User.email,
                    Course.id,
                    Course.title,
                )
                .join(User, TeacherProfile.user_id == User.id)
                .join(Course, Course.teacher_profile_id == TeacherProfile.id)
                .where(
                    TeacherProfile.active.is_(True),
                    Course.is_active.is_(True),
                    Course.is_published.is_(True),
                    user_role_equals(UserRole.teacher),
                )
                .order_by(TeacherProfile.full_name)
            )
        ).all()
        for pid, full_name, email, cid, title in catalog:
            flag = ""
            if is_demo_email(email) or is_demo_teacher_name(full_name):
                flag = " [DEMO]"
            print(f"  profile_id={pid} {full_name} <{email}> course={cid} {title!r}{flag}")


async def purge() -> None:
    async with AsyncSessionLocal() as db:
        demo_user_ids = await _collect_demo_user_ids(db)
        demo_tp_ids = await _collect_demo_teacher_profile_ids(db)

        if not demo_user_ids and not demo_tp_ids:
            print("No demo users or demo teacher profiles found — database already clean.")
            return

        if demo_tp_ids:
            print(f"Removing {len(demo_tp_ids)} demo teacher profile(s): {demo_tp_ids}")
            await _delete_teacher_profiles(db, demo_tp_ids)

        if demo_user_ids:
            users = (
                await db.execute(select(User).where(User.id.in_(demo_user_ids)))
            ).scalars().all()
            print(f"Removing {len(users)} demo user(s): {', '.join(u.email for u in users)}")

            await db.execute(delete(Lesson).where(Lesson.teacher_id.in_(demo_user_ids)))
            await db.execute(
                delete(StudentLessonProgress).where(StudentLessonProgress.student_id.in_(demo_user_ids))
            )
            await db.execute(delete(QuizAttempt).where(QuizAttempt.student_id.in_(demo_user_ids)))
            await db.execute(
                delete(StudentAttendanceRecord).where(StudentAttendanceRecord.student_id.in_(demo_user_ids))
            )
            await db.execute(
                delete(StudentActivityEvent).where(StudentActivityEvent.student_id.in_(demo_user_ids))
            )
            await db.execute(
                delete(StudentCourseAccess).where(StudentCourseAccess.student_id.in_(demo_user_ids))
            )
            await db.execute(
                delete(StudentTeacherChoice).where(StudentTeacherChoice.student_id.in_(demo_user_ids))
            )
            await db.execute(
                delete(StudentSubjectChoice).where(StudentSubjectChoice.student_id.in_(demo_user_ids))
            )
            await db.execute(delete(Payment).where(Payment.student_id.in_(demo_user_ids)))
            await db.execute(
                delete(PlannerScheduleSlot).where(PlannerScheduleSlot.student_id.in_(demo_user_ids))
            )
            await db.execute(delete(PlannerLifeEvent).where(PlannerLifeEvent.student_id.in_(demo_user_ids)))
            await db.execute(
                delete(PlannerChatMessage).where(PlannerChatMessage.student_id.in_(demo_user_ids))
            )
            await db.execute(delete(PlannerProfile).where(PlannerProfile.student_id.in_(demo_user_ids)))
            await db.execute(delete(StudentProfile).where(StudentProfile.user_id.in_(demo_user_ids)))
            await db.execute(delete(User).where(User.id.in_(demo_user_ids)))

        await db.commit()
        print("Done. Demo data removed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit or purge EduSpark demo data")
    parser.add_argument("--audit", action="store_true", help="List demo rows only")
    args = parser.parse_args()
    if args.audit:
        asyncio.run(audit())
    else:
        asyncio.run(purge())


if __name__ == "__main__":
    main()
