"""One-shot: enable language listening access for seeded test student."""
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, text

from app.db.session import AsyncSessionLocal
from app.models.language.profile import LanguageStudentProfile
from app.models.user import User
from app.services.language_subscription_service import get_default_language, get_default_product


async def main() -> None:
    email = "test.auth.student@eduspark-test.dev"
    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == email))
        if not user:
            print(f"MISSING USER {email}")
            return
        language = await get_default_language(db)
        product = await get_default_product(db)
        now = datetime.now(timezone.utc)
        await db.execute(
            text(
                """
                INSERT INTO language_subscriptions (student_id, product_id, payment_status, activated_at, expires_at, created_at)
                VALUES (:sid, :pid, 'paid', :act, :exp, now())
                ON CONFLICT DO NOTHING
                """
            ),
            {
                "sid": user.id,
                "pid": product.id,
                "act": now,
                "exp": now.replace(year=now.year + 1),
            },
        )
        prof = await db.scalar(
            select(LanguageStudentProfile).where(
                LanguageStudentProfile.student_id == user.id,
                LanguageStudentProfile.language_id == language.id,
            )
        )
        if prof is None:
            prof = LanguageStudentProfile(student_id=user.id, language_id=language.id)
            db.add(prof)
        prof.placement_completed_at = now
        await db.execute(
            text(
                """
                INSERT INTO student_profiles (user_id, interests_json, difficulty, grade, onboarding_step, onboarding_completed_at, payment_completed_at)
                VALUES (:uid, '[]', 'medium', 10, 'complete', :now, :now)
                ON CONFLICT (user_id) DO UPDATE SET
                    onboarding_step = 'complete',
                    onboarding_completed_at = EXCLUDED.onboarding_completed_at,
                    payment_completed_at = EXCLUDED.payment_completed_at
                """
            ),
            {"uid": user.id, "now": now},
        )
        await db.commit()
        print(f"READY {email} id={user.id}")


asyncio.run(main())
