"""Add a test lesson with quiz questions for feature testing."""
import asyncio, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import get_settings
from app.db.session import get_async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

async def seed():
    # Refuse to run against what looks like a production database (DEBUG=false).
    # This script writes directly to the DB with no dry-run mode, so a misconfigured
    # environment must fail loudly rather than seed test content into production.
    if not get_settings().DEBUG:
        raise RuntimeError(
            "Refusing to seed test quiz data: DEBUG is not enabled. This looks like a "
            "production database. Set DEBUG=true in .env if this is really a dev/test DB."
        )
    engine = get_async_engine()
    async with AsyncSession(engine) as db:
        r = await db.execute(text("SELECT id FROM users WHERE email='teacher@eduspark.sy'"))
        teacher_id = r.scalar_one()

        r2 = await db.execute(text("SELECT id FROM users WHERE email='student@eduspark.sy'"))
        student_id = r2.scalar_one()

        await db.execute(text("""
            INSERT INTO lessons (teacher_id, title, subject, status, raw_text, created_at)
            VALUES (:tid, 'قوانين نيوتن في الحركة', 'فيزياء', 'ready',
            'قوانين نيوتن الثلاثة: الأول: الجسم الساكن يبقى ساكناً والمتحرك يبقى متحركاً ما لم تؤثر قوة خارجية. الثاني: القوة تساوي الكتلة ضرب التسارع F=ma. الثالث: لكل فعل رد فعل مساوٍ ومعاكس.',
            NOW())
        """), {"tid": teacher_id})
        await db.commit()

        r3 = await db.execute(text(
            "SELECT id FROM lessons WHERE subject='فيزياء' AND teacher_id=:tid ORDER BY id DESC LIMIT 1"
        ), {"tid": teacher_id})
        lesson_id = r3.scalar_one()

        questions = [
            ("ما هو القانون الثاني لنيوتن؟", ["F=ma", "F=mv", "F=m/a", "F=a/m"], 0, "القوة = الكتلة × التسارع"),
            ("ماذا يحدث للجسم الساكن إذا لم تؤثر عليه قوة؟", ["يتحرك", "يبقى ساكناً", "يسقط", "يدور"], 1, "القانون الأول لنيوتن"),
            ("لكل فعل...", ["قوة مضاعفة", "رد فعل مساوٍ ومعاكس", "حركة دائرية", "توازن"], 1, "القانون الثالث"),
        ]
        for i, (q, opts, correct, hint) in enumerate(questions):
            await db.execute(text("""
                INSERT INTO quiz_questions (lesson_id, question, options_json, correct_index, hint, sort_order)
                VALUES (:lid, :q, :opts, :correct, :hint, :sort)
            """), {"lid": lesson_id, "q": q, "opts": json.dumps(opts, ensure_ascii=False), "correct": correct, "hint": hint, "sort": i})
        await db.commit()

        print(f"lesson_id={lesson_id}  student_id={student_id}")

asyncio.run(seed())
