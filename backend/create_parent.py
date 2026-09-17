import asyncio
from app.db.session import AsyncSessionLocal
from sqlalchemy import text
from passlib.context import CryptContext

pwd = CryptContext(schemes=["bcrypt"])
hashed = pwd.hash("parent123")

async def create():
    async with AsyncSessionLocal() as db:
        await db.execute(
            text("INSERT INTO users (email, name, hashed_password, role) VALUES (:e, :n, :p, 'parent') ON CONFLICT (email) DO NOTHING"),
            {"e": "parent@eduspark.sy", "n": "ولي الامر", "p": hashed}
        )
        r = await db.execute(text("SELECT id FROM users WHERE email='parent@eduspark.sy'"))
        pid = r.scalar_one()
        await db.execute(
            text("INSERT INTO parent_student_links (parent_id, student_id) VALUES (:p, 2) ON CONFLICT DO NOTHING"),
            {"p": pid}
        )
        await db.commit()
        print(f"Done — parent id={pid} linked to student 2")

asyncio.run(create())
