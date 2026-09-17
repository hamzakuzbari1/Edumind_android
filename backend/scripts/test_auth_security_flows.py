"""Safe auth/security integration tests — test users only."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.security import hash_password, verify_password
from app.core.test_users import TEST_USER_PASSWORD, default_test_email, require_test_user_email
from app.db.session import AsyncSessionLocal
from app.models.email_token import EmailTokenPurpose
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, ResetPasswordRequest
from app.models.two_factor import TwoFactorMethod, TwoFactorPurpose
from app.services import account_security_service, password_reset_service
from app.services.two_factor_service import (
    disable_two_factor,
    verify_login_challenge,
)
from app.services.email_token_service import create_email_token
from app.services.email_verification_service import verify_email_with_token

BASE = "http://127.0.0.1:8000"


async def _get_test_user(email: str) -> User:
    require_test_user_email(email, action="auth security test")
    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == email.lower()))
        if not user:
            raise RuntimeError(f"Test user missing: {email}. Run: python scripts/seed_test_users.py")
        return user


async def test_password_reset_flow() -> None:
    email = default_test_email("password_reset")
    require_test_user_email(email)
    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == email))
        assert user is not None
        raw, _ = await create_email_token(db, user, EmailTokenPurpose.password_reset, expire_hours=1)
        new_password = "ResetTest456!"
        await password_reset_service.reset_password_with_token(
            db,
            ResetPasswordRequest(token=raw, new_password=new_password, confirm_password=new_password),
        )
        await db.commit()
        await db.refresh(user)
        assert verify_password(new_password, user.hashed_password)
        user.hashed_password = hash_password(TEST_USER_PASSWORD)
        await db.commit()
    print("[password_reset] OK")


async def test_email_verification_flow() -> None:
    email = default_test_email("email_verify")
    require_test_user_email(email)
    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.email_verified_at = None
        await db.flush()
        raw, _ = await create_email_token(db, user, EmailTokenPurpose.verification, expire_hours=1)
        await verify_email_with_token(db, raw)
        await db.commit()
        await db.refresh(user)
        assert user.email_verified_at is not None
        user.email_verified_at = None
        await db.commit()
    print("[email_verify] OK")


async def test_account_security_change_password() -> None:
    email = default_test_email("account_security")
    require_test_user_email(email)
    temp_password = "SecurityTest789!"
    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.hashed_password = hash_password(TEST_USER_PASSWORD)
        await db.commit()
        await db.refresh(user)
        await account_security_service.change_password(
            db,
            user,
            ChangePasswordRequest(
                current_password=TEST_USER_PASSWORD,
                new_password=temp_password,
                confirm_password=temp_password,
            ),
        )
        await db.commit()
        await db.refresh(user)
        assert verify_password(temp_password, user.hashed_password)
        user.hashed_password = hash_password(TEST_USER_PASSWORD)
        await db.commit()
    print("[account_security] OK")


def test_gamification_profile() -> None:
    email = default_test_email("gamification")
    require_test_user_email(email)
    login = httpx.post(
        f"{BASE}/api/auth/login",
        json={"email": email, "password": TEST_USER_PASSWORD},
        timeout=15,
    )
    if login.status_code != 200:
        raise RuntimeError(f"Gamification login failed: {login.status_code} {login.text[:200]}")
    token = login.json()["access_token"]
    r = httpx.get(
        f"{BASE}/api/student/gamification",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Gamification profile failed: {r.status_code} {r.text[:200]}")
    data = r.json()
    if data.get("total_xp", 0) < 1:
        raise RuntimeError("Expected seeded XP on gamification test user")
    print("[gamification] OK")


def test_http_login() -> None:
    for key in ("auth_student", "auth_teacher", "auth_parent"):
        email = default_test_email(key)
        require_test_user_email(email)
        r = httpx.post(
            f"{BASE}/api/auth/login",
            json={"email": email, "password": TEST_USER_PASSWORD},
            timeout=15,
        )
        if r.status_code != 200:
            raise RuntimeError(f"Login failed for {email}: {r.status_code} {r.text[:200]}")
    print("[http_login] OK")


async def test_two_factor_flow() -> None:
    email = default_test_email("two_factor")
    require_test_user_email(email)
    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.two_factor_enabled = False
        user.two_factor_method = None
        await db.commit()

    login_r = httpx.post(
        f"{BASE}/api/auth/login",
        json={"email": email, "password": TEST_USER_PASSWORD},
        timeout=15,
    )
    if login_r.status_code != 200 or login_r.json().get("requires_2fa"):
        raise RuntimeError(f"Expected normal login before 2FA enabled: {login_r.text[:200]}")

    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == email))
        user.two_factor_enabled = True
        user.two_factor_method = TwoFactorMethod.email.value
        await db.commit()

    challenge_r = httpx.post(
        f"{BASE}/api/auth/login",
        json={"email": email, "password": TEST_USER_PASSWORD},
        timeout=15,
    )
    data = challenge_r.json()
    if challenge_r.status_code != 200 or not data.get("requires_2fa"):
        raise RuntimeError(f"Expected 2FA challenge: {challenge_r.text[:200]}")

    bad = httpx.post(
        f"{BASE}/api/auth/verify-2fa",
        json={"challenge_token": data["challenge_token"], "code": "000000"},
        timeout=15,
    )
    if bad.status_code not in (400, 429):
        raise RuntimeError(f"Expected wrong-code rejection, got {bad.status_code}")

    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == email))
        from app.services.two_factor_service import _create_challenge

        token, code, _ = await _create_challenge(db, user, TwoFactorPurpose.login)
        await db.commit()
        await verify_login_challenge(db, token, code)
        await db.commit()
        user = await db.scalar(select(User).where(User.email == email))
        await disable_two_factor(db, user, TEST_USER_PASSWORD)
        await db.commit()

    print("[two_factor] OK")


async def main() -> int:
    await _get_test_user(default_test_email("password_reset"))
    test_http_login()
    await test_password_reset_flow()
    await test_email_verification_flow()
    await test_account_security_change_password()
    test_gamification_profile()
    await test_two_factor_flow()
    print("\nAll auth/security test-user flows passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
