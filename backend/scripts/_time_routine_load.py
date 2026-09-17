"""Time routine page load APIs."""
import asyncio
import logging
import time
import sys
from pathlib import Path

logging.disable(logging.CRITICAL)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from httpx import ASGITransport, AsyncClient

from app.core.test_users import TEST_USER_PASSWORD, default_test_email
from app.main import app


async def main():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t", timeout=180) as c:
        email = default_test_email("auth_student")
        login = await c.post("/api/auth/login", json={"email": email, "password": TEST_USER_PASSWORD})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        for label, path in [
            ("routine_profile", "/api/student/routine/profile"),
            ("routine_week", "/api/student/routine/week"),
            ("routine_week_2nd", "/api/student/routine/week"),
            ("planner_get", "/api/student/planner"),
            ("student_dashboard", "/api/student/dashboard"),
        ]:
            t0 = time.perf_counter()
            r = await c.get(path, headers=headers)
            ms = (time.perf_counter() - t0) * 1000
            print(f"{label}: status={r.status_code} ms={ms:.1f} size_kb={len(r.content)/1024:.1f}")
            if path.endswith("/week") and r.status_code == 200:
                body = r.json()
                if body.get("regenerated"):
                    print(f"  -> regenerated={body.get('regenerated')} slots_saved={body.get('slots_saved')}")


if __name__ == "__main__":
    asyncio.run(main())
