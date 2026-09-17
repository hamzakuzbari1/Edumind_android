"""One-off timing probe for student planner page load APIs."""
import asyncio
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from httpx import ASGITransport, AsyncClient

from app.core.test_users import TEST_USER_PASSWORD, default_test_email
from app.main import app


async def time_get(c, path, headers, runs=3):
    times = []
    status = None
    size = 0
    for _ in range(runs):
        t0 = time.perf_counter()
        resp = await c.get(path, headers=headers)
        times.append((time.perf_counter() - t0) * 1000)
        status = resp.status_code
        size = len(resp.content)
    return status, times, size


async def main():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t", timeout=120) as c:
        email = default_test_email("auth_student")
        login = await c.post(
            "/api/auth/login",
            json={"email": email, "password": TEST_USER_PASSWORD},
        )
        if login.status_code != 200:
            print("login failed", login.status_code, login.text[:300])
            return

        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        endpoints = [
            ("planner_get (auto_generate=True)", "/api/student/planner"),
            ("planner_summary (auto_generate=False)", "/api/student/planner/summary"),
            ("student_dashboard", "/api/student/dashboard"),
        ]

        for label, path in endpoints:
            status, times, size = await time_get(c, path, headers)
            avg = sum(times) / len(times)
            print(
                f"{label}: status={status} "
                f"runs_ms={[round(t, 1) for t in times]} avg_ms={avg:.1f} size_kb={size / 1024:.1f}"
            )


if __name__ == "__main__":
    asyncio.run(main())
