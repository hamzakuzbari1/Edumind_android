"""Seed isolated test users for automated scripts (never touches real accounts).

Usage (from backend/):
    python scripts/seed_test_users.py
    python scripts/seed_test_users.py --list
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.core.test_users import TEST_USER_PASSWORD, TEST_USER_SPECS, verified_at_for
from app.db.session import AsyncSessionLocal
from app.models.catalog import TeacherProfile
from app.models.enrollment import OnboardingStep
from app.models.profile import StudentProfile
from app.models.student_gamification import StudentAchievement, StudentXp
from app.models.user import User, UserRole


async def _upsert_user(db, spec) -> User:
    role_map = {
        "student": UserRole.student,
        "teacher": UserRole.teacher,
        "parent": UserRole.parent,
    }
    role = role_map[spec.role]
    email = spec.email.lower()

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            email=email,
            name=spec.name,
            hashed_password=hash_password(TEST_USER_PASSWORD),
            role=role,
            email_verified_at=verified_at_for(spec),
        )
        db.add(user)
        await db.flush()
    else:
        user.name = spec.name
        user.role = role
        user.hashed_password = hash_password(TEST_USER_PASSWORD)
        user.email_verified_at = verified_at_for(spec)

    if role == UserRole.student:
        profile = await db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
        if profile is None:
            db.add(
                StudentProfile(
                    user_id=user.id,
                    interests_json="[]",
                    difficulty="medium",
                    onboarding_step=OnboardingStep.grade,
                    grade=10,
                )
            )
        elif profile.grade is None:
            profile.grade = 10

    if role == UserRole.teacher:
        tp = await db.scalar(select(TeacherProfile).where(TeacherProfile.user_id == user.id))
        if tp is None:
            db.add(
                TeacherProfile(
                    user_id=user.id,
                    full_name=spec.name,
                    bio="Automated test teacher — do not use in production UI",
                    rating=0.0,
                    student_count=0,
                    active=True,
                )
            )

    if spec.key == "gamification":
        xp = await db.scalar(select(StudentXp).where(StudentXp.student_id == user.id))
        if xp is None:
            db.add(StudentXp(student_id=user.id, total_xp=120, level=2, awarded_keys_json="[]"))
        has_badge = await db.scalar(
            select(StudentAchievement.id).where(
                StudentAchievement.student_id == user.id,
                StudentAchievement.achievement_key == "test_seed_badge",
            )
        )
        if has_badge is None:
            db.add(
                StudentAchievement(
                    student_id=user.id,
                    achievement_key="test_seed_badge",
                    icon="🧪",
                    title="Test Badge",
                    description="Seeded for gamification script tests",
                    unlocked_at=datetime.now(timezone.utc),
                )
            )

    return user


async def seed_test_users() -> list[tuple[str, int]]:
    # Refuse to run against what looks like a production database (DEBUG=false).
    # This script writes directly to the DB with no dry-run mode, so a misconfigured
    # environment must fail loudly rather than seed test accounts into production.
    if not get_settings().DEBUG:
        raise RuntimeError(
            "Refusing to seed test users: DEBUG is not enabled. This looks like a "
            "production database. Set DEBUG=true in .env if this is really a dev/test DB."
        )
    created: list[tuple[str, int]] = []
    async with AsyncSessionLocal() as db:
        for spec in TEST_USER_SPECS:
            user = await _upsert_user(db, spec)
            created.append((spec.key, user.id))
        await db.commit()
    return created


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed isolated @eduspark-test.dev users")
    parser.add_argument("--list", action="store_true", help="Print test user catalog and exit")
    args = parser.parse_args()

    if args.list:
        print(f"Password for all test users: {TEST_USER_PASSWORD}\n")
        for spec in TEST_USER_SPECS:
            verified = "verified" if spec.email_verified else "unverified"
            print(f"  [{spec.key}] {spec.email} ({spec.role}, {verified})")
            print(f"      {spec.purpose}")
        return 0

    rows = asyncio.run(seed_test_users())
    print(f"Seeded {len(rows)} test user(s). Password: {TEST_USER_PASSWORD}")
    for key, user_id in rows:
        spec = next(s for s in TEST_USER_SPECS if s.key == key)
        print(f"  {key}: id={user_id} email={spec.email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
