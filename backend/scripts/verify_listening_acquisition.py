"""Verify Listening acquisition UX — no HTTP 404 on /listening/next for gated students."""

from __future__ import annotations

import httpx

QA_EMAILS = [
    "qa.listening.student-a@eduspark-test.dev",
    "qa.listening.student-b@eduspark-test.dev",
    "qa.listening.student-c@eduspark-test.dev",
    "qa.listening.student-d@eduspark-test.dev",
    "qa.listening.student-e@eduspark-test.dev",
    "qa.listening.student-f@eduspark-test.dev",
    "qa.listening.student-g@eduspark-test.dev",
]
PASSWORD = "TestOnly123!"
API = "http://127.0.0.1:8000"


def _login(email: str) -> str:
    r = httpx.post(f"{API}/api/auth/login", json={"email": email, "password": PASSWORD}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def main() -> int:
    failures: list[str] = []
    for email in QA_EMAILS:
        try:
            token = _login(email)
        except Exception as exc:
            failures.append(f"{email}: login failed — {exc}")
            continue
        headers = {"Authorization": f"Bearer {token}"}
        r = httpx.get(f"{API}/api/student/languages/listening/next", headers=headers, timeout=120)
        if r.status_code == 404:
            failures.append(f"{email}: still returns 404")
            continue
        if r.status_code != 200:
            failures.append(f"{email}: HTTP {r.status_code}")
            continue
        body = r.json()
        outcome = body.get("outcome")
        if outcome not in ("lesson_ready", "acquisition_pending"):
            failures.append(f"{email}: invalid outcome {outcome!r}")
            continue
        if outcome == "lesson_ready" and not body.get("bundle"):
            failures.append(f"{email}: lesson_ready without bundle")
        if outcome == "acquisition_pending":
            acq = body.get("acquisition") or {}
            if not acq.get("message_key"):
                failures.append(f"{email}: missing message_key")
            if acq.get("temporary_failure") and acq.get("status") != "temporary_failure":
                failures.append(f"{email}: inconsistent temporary_failure flag")

        rj = httpx.get(f"{API}/api/student/languages/listening/journey", headers=headers, timeout=60)
        if rj.status_code != 200:
            failures.append(f"{email}: journey HTTP {rj.status_code}")

    if failures:
        print("FAIL")
        for f in failures:
            print(" -", f)
        return 1
    print("PASS — all QA personas return 200 acquisition contract on /listening/next")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
