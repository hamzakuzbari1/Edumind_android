"""Test auth endpoints (API must be running). Usage: python scripts/test_api.py"""

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.test_users import TEST_USER_PASSWORD, default_test_email

BASE = "http://127.0.0.1:8000"


def main() -> int:
    print("Testing EduSpark API at", BASE)

    try:
        r = httpx.get(f"{BASE}/health", timeout=10)
        r.raise_for_status()
        print("[health]", r.json())
    except Exception as exc:
        print("[health] FAILED — is uvicorn running?", exc)
        return 1

    accounts = [
        (default_test_email("auth_teacher"), TEST_USER_PASSWORD, "teacher"),
        (default_test_email("auth_student"), TEST_USER_PASSWORD, "student"),
        (default_test_email("auth_parent"), TEST_USER_PASSWORD, "parent"),
    ]

    for email, password, role in accounts:
        r = httpx.post(
            f"{BASE}/api/auth/login",
            json={"email": email, "password": password},
            timeout=15,
        )
        if r.status_code != 200:
            print(f"[login {role}] FAILED", r.status_code, r.text)
            print("Run: python scripts/seed_test_users.py")
            return 1
        data = r.json()
        print(f"[login {role}] OK — token received for", data["user"]["name"])

    print("\nAll auth checks passed (test users only).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
