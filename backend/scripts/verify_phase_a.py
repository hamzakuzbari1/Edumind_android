"""Phase A verification — run from backend/: python scripts/verify_phase_a.py"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import create_engine, select, text, update

from app.core.config import get_settings

BASE = "http://127.0.0.1:8000/api"
PREFIX = "phase_a_verify"


def j(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


def section(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def login(client: httpx.Client, email: str, password: str) -> str:
    r = client.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    if r.status_code >= 400:
        print("login failed", r.status_code, r.text)
    r.raise_for_status()
    data = r.json()
    return data["access_token"]


def main() -> int:
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL_SYNC)
    issues: list[str] = []

    section("2. Database — payment_items schema sample")
    with engine.connect() as conn:
        r = conn.execute(
            text(
                "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
                "WHERE table_name = 'payment_items' AND column_name IN "
                "('product_type','course_id','language_product_id') ORDER BY column_name"
            )
        )
        for row in r:
            print(dict(row._mapping))

    section("3–4. Prepare test students via DB + HTTP")
    emails = {
        "no_lang": f"{PREFIX}_no_lang@example.com",
        "active_lang": f"{PREFIX}_active_lang@example.com",
        "expired_lang": f"{PREFIX}_expired_lang@example.com",
        "course_pay": f"{PREFIX}_course@example.com",
    }
    password = "verify1234"

    client = httpx.Client(timeout=30.0)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                DELETE FROM language_subscriptions WHERE student_id IN (
                  SELECT id FROM users WHERE email LIKE :pat
                );
                DELETE FROM language_student_profiles WHERE student_id IN (
                  SELECT id FROM users WHERE email LIKE :pat
                );
                DELETE FROM student_profiles WHERE user_id IN (
                  SELECT id FROM users WHERE email LIKE :pat
                );
                DELETE FROM users WHERE email LIKE :pat;
                """
            ),
            {"pat": f"{PREFIX}_%@example.com"},
        )

    for key, email in emails.items():
        reg = client.post(
            f"{BASE}/auth/register",
            json={
                "name": f"Verify {key}",
                "email": email,
                "password": password,
                "role": "student",
            },
        )
        if reg.status_code not in (200, 201):
            print(f"register {email}:", reg.status_code, reg.text)

    with engine.begin() as conn:
        # Mark onboarding + payment complete for verify users
        for email in emails.values():
            conn.execute(
                text(
                    """
                    INSERT INTO student_profiles (user_id, interests_json, difficulty, onboarding_step, onboarding_completed_at, payment_completed_at)
                    SELECT u.id, '[]', 'medium', 'complete', now(), now()
                    FROM users u WHERE u.email = :e
                    ON CONFLICT (user_id) DO UPDATE SET
                      onboarding_step = 'complete',
                      onboarding_completed_at = COALESCE(student_profiles.onboarding_completed_at, now()),
                      payment_completed_at = COALESCE(student_profiles.payment_completed_at, now())
                    """
                ),
                {"e": email},
            )

        # Active language subscription
        active_id = conn.execute(
            text("SELECT id FROM users WHERE email = :e"), {"e": emails["active_lang"]}
        ).scalar()
        expired_id = conn.execute(
            text("SELECT id FROM users WHERE email = :e"), {"e": emails["expired_lang"]}
        ).scalar()
        product_id = conn.execute(text("SELECT id FROM language_products LIMIT 1")).scalar()
        now = datetime.now(timezone.utc)
        conn.execute(
            text(
                """
                INSERT INTO language_subscriptions
                (student_id, product_id, payment_status, activated_at, expires_at, created_at)
                VALUES (:sid, :pid, 'paid', :act, :exp, now())
                """
            ),
            {
                "sid": active_id,
                "pid": product_id,
                "act": now - timedelta(days=30),
                "exp": now + timedelta(days=335),
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO language_subscriptions
                (student_id, product_id, payment_status, activated_at, expires_at, created_at)
                VALUES (:sid, :pid, 'paid', :act, :exp, now())
                """
            ),
            {
                "sid": expired_id,
                "pid": product_id,
                "act": now - timedelta(days=400),
                "exp": now - timedelta(days=35),
            },
        )

    section("3a. Student WITHOUT language subscription — GET /access")
    try:
        tok = login(client, emails["no_lang"], password)
        r = client.get(
            f"{BASE}/student/languages/access",
            headers={"Authorization": f"Bearer {tok}"},
        )
        print("HTTP", r.status_code)
        print(j(r.json()))
        data = r.json()
        if data.get("subscribed"):
            issues.append("no_lang student should not be subscribed")
        if data.get("redirect") != "/student/languages/subscribe":
            issues.append(f"no_lang redirect unexpected: {data.get('redirect')}")
    except Exception as e:
        issues.append(f"no_lang access: {e}")
        print("ERROR", e)

    section("3b. Student WITH active language subscription — GET /access")
    try:
        tok = login(client, emails["active_lang"], password)
        r = client.get(
            f"{BASE}/student/languages/access",
            headers={"Authorization": f"Bearer {tok}"},
        )
        print("HTTP", r.status_code)
        print(j(r.json()))
        data = r.json()
        if not data.get("subscribed"):
            issues.append("active_lang should be subscribed")
        if data.get("status") not in ("active", "expiring_soon"):
            issues.append(f"active_lang status: {data.get('status')}")
    except Exception as e:
        issues.append(f"active_lang access: {e}")
        print("ERROR", e)

    section("3c. Student WITH expired language subscription — GET /access")
    try:
        tok = login(client, emails["expired_lang"], password)
        r = client.get(
            f"{BASE}/student/languages/access",
            headers={"Authorization": f"Bearer {tok}"},
        )
        print("HTTP", r.status_code)
        print(j(r.json()))
        data = r.json()
        if data.get("subscribed"):
            issues.append("expired_lang should not be subscribed")
        if data.get("status") != "expired":
            issues.append(f"expired_lang status expected expired, got {data.get('status')}")
    except Exception as e:
        issues.append(f"expired_lang access: {e}")
        print("ERROR", e)

    section("3d. Subscribe flow — POST /subscribe (no_lang)")
    try:
        tok = login(client, emails["no_lang"], password)
        r = client.post(
            f"{BASE}/student/languages/subscribe",
            headers={"Authorization": f"Bearer {tok}"},
            json={"method": "card"},
        )
        print("HTTP", r.status_code)
        print(j(r.json()))
        r.raise_for_status()
        r2 = client.get(
            f"{BASE}/student/languages/access",
            headers={"Authorization": f"Bearer {tok}"},
        )
        print("--- access after subscribe ---")
        print(j(r2.json()))
        if not r2.json().get("subscribed"):
            issues.append("no_lang not subscribed after subscribe")
    except Exception as e:
        issues.append(f"subscribe flow: {e}")
        print("ERROR", e)

    section("4a. Course payment regression — demo-checkout")
    try:
        tok = login(client, emails["course_pay"], password)
        checkout = client.get(
            f"{BASE}/student/payments/checkout",
            headers={"Authorization": f"Bearer {tok}"},
        )
        print("GET checkout HTTP", checkout.status_code)
        checkout_data = checkout.json()
        print(j(checkout_data))
        if not checkout_data.get("items"):
            print("SKIP course checkout — no unpaid courses in catalog for test user")
        else:
            pay = client.post(
                f"{BASE}/student/payments/demo-checkout",
                headers={"Authorization": f"Bearer {tok}"},
                json={"method": "card"},
            )
            print("POST demo-checkout HTTP", pay.status_code)
            print(j(pay.json()))
            pay.raise_for_status()
            with engine.connect() as conn:
                rows = conn.execute(
                    text(
                        "SELECT pi.id, pi.product_type, pi.course_id, pi.language_product_id, p.status "
                        "FROM payment_items pi JOIN payments p ON p.id = pi.payment_id "
                        "JOIN users u ON u.id = p.student_id WHERE u.email = :e ORDER BY pi.id DESC LIMIT 5"
                    ),
                    {"e": emails["course_pay"]},
                ).fetchall()
                print("--- payment_items rows ---")
                for row in rows:
                    print(dict(row._mapping))
                if rows and rows[0].product_type != "course":
                    issues.append("course payment item product_type != course")
                if rows and rows[0].course_id is None:
                    issues.append("course payment item course_id is null")
    except Exception as e:
        issues.append(f"course payment: {e}")
        print("ERROR", e)

    section("4b. Language payment_items row after subscribe")
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT pi.id, pi.product_type, pi.course_id, pi.language_product_id "
                    "FROM payment_items pi JOIN payments p ON p.id = pi.payment_id "
                    "JOIN users u ON u.id = p.student_id WHERE u.email = :e AND pi.product_type = 'language'"
                ),
                {"e": emails["no_lang"]},
            ).fetchall()
            print("language payment_items:")
            for row in rows:
                print(dict(row._mapping))
            if not rows:
                issues.append("no language payment_items for subscribed user")
            elif rows[0].language_product_id is None:
                issues.append("language payment_item missing language_product_id")
    except Exception as e:
        issues.append(f"language payment_items check: {e}")

    section("GET /student/languages/product (public catalog)")
    try:
        r = client.get(f"{BASE}/student/languages/product")
        print("HTTP", r.status_code)
        print(j(r.json()))
    except Exception as e:
        issues.append(f"product endpoint: {e}")

    client.close()

    section("SUMMARY")
    if issues:
        print("ISSUES FOUND:")
        for i in issues:
            print(" -", i)
        return 1
    print("All automated API/DB checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
