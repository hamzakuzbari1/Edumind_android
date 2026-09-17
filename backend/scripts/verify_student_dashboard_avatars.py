"""Verify GET /student/dashboard includes teacher_image_url when profile has image."""

import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.test_users import TEST_USER_PASSWORD, default_test_email, is_test_user_email, require_test_user_email

BASE = "http://127.0.0.1:8000"


def main() -> int:
    if len(sys.argv) >= 3:
        email = require_test_user_email(sys.argv[1], action="avatar verification login")
        password = sys.argv[2]
    else:
        email = default_test_email("auth_student")
        password = TEST_USER_PASSWORD

    r = httpx.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    if r.status_code != 200:
        print(f"Login failed for {email}: {r.status_code}")
        if not is_test_user_email(email):
            print("Use a seeded test user: python scripts/seed_test_users.py --list")
        return 1

    token = r.json().get("access_token")
    print(f"Logged in as {email}")

    r = httpx.get(
        f"{BASE}/api/student/dashboard",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    print(f"grade={data.get('grade')} courses={len(data.get('courses') or [])}")
    for c in (data.get("courses") or [])[:5]:
        print(
            json.dumps(
                {
                    "id": c.get("id"),
                    "teacher_name": c.get("teacher_name"),
                    "teacher_image_url": c.get("teacher_image_url"),
                    "avatar_url": c.get("avatar_url"),
                },
                ensure_ascii=False,
            )
        )
    with_img = [c for c in data.get("courses") or [] if c.get("teacher_image_url")]
    print(f"Courses with teacher_image_url: {len(with_img)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
