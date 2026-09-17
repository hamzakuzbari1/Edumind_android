"""Test teacher_setup_service.set_profile_image persists without HTTP auth."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.test_users import default_test_email
from app.db.session import AsyncSessionLocal
from app.models.catalog import TeacherProfile
from app.models.user import User
from app.services.teacher_setup_service import save_profile_image, set_profile_image


async def main() -> int:
    test_email = default_test_email("auth_teacher")
    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == test_email))
        if not user:
            print(f"Test teacher not found ({test_email}). Run: python scripts/seed_test_users.py")
            return 1

        test_url = f"/uploads/teachers/{user.id}/avatar_service_test.jpg"
        save_profile_image(user.id, "avatar_service_test.jpg", b"\xff\xd8\xff\xd9")
        out = await set_profile_image(db, user, test_url)
        await db.commit()
        row = await db.scalar(select(TeacherProfile).where(TeacherProfile.user_id == user.id))
        print("service response image_url:", out.image_url)
        print("DB image_url:", row.image_url if row else None)
        ok = row and row.image_url == test_url
        print("PASS" if ok else "FAIL")
        return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
