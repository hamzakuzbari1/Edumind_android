"""Skip onboarding for testing — run: python scripts/skip_onboarding.py email@example.com"""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.session import AsyncSessionLocal
from sqlalchemy import text

async def skip(email):
    async with AsyncSessionLocal() as db:
        # Get user
        r = await db.execute(text("SELECT id, role FROM users WHERE email=:e"), {"e": email})
        user = r.fetchone()
        if not user:
            print(f"User not found: {email}")
            return
        if user.role != "student":
            print(f"Not a student: {email}")
            return

        # Mark onboarding + payment as complete
        await db.execute(text("""
            INSERT INTO student_profiles (user_id, interests_json, difficulty, grade, onboarding_step, onboarding_completed_at, payment_completed_at)
            VALUES (:uid, '[]', 'medium', 10, 'complete', NOW(), NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                onboarding_step = 'complete',
                onboarding_completed_at = NOW(),
                payment_completed_at = NOW()
        """), {"uid": user.id})
        await db.commit()
        print(f"Done — {email} can now login without payment")

email = sys.argv[1] if len(sys.argv) > 1 else "student@eduspark.sy"
asyncio.run(skip(email))
