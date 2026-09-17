"""Focused auth lifecycle regression tests against an explicitly approved runtime database."""

from __future__ import annotations

import asyncio
import os
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import delete, select, text


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_AUTH_RUNTIME_TESTS") != "1",
        reason="set RUN_AUTH_RUNTIME_TESTS=1 only for an approved disposable runtime database",
    ),
]


def _auth(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


async def _cleanup_user(user_id: int) -> None:
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        for table, column in (
            ("student_engagement_events", "student_id"),
            ("student_activity_sessions", "student_id"),
            ("auth_sessions", "user_id"),
            ("student_profiles", "user_id"),
            ("users", "id"),
        ):
            await db.execute(
                text(f"DELETE FROM {table} WHERE {column} = :user_id"),
                {"user_id": user_id},
            )
        await db.commit()


@asynccontextmanager
async def _disposable_student(client: httpx.AsyncClient):
    email = f"auth-runtime-{uuid.uuid4().hex}@example.com"
    password = secrets.token_urlsafe(24) + "Aa1!"
    response = await client.post(
        "/api/auth/register",
        json={
            "name": "Auth Runtime Test",
            "email": email,
            "password": password,
            "role": "student",
            "device_name": "Auth Test Device",
        },
        headers={"User-Agent": "EduMind-Android-Auth-Test"},
    )
    assert response.status_code == 200, response.text
    registration = response.json()
    user_id = registration["user"]["id"]
    try:
        yield email, password, registration
    finally:
        await _cleanup_user(user_id)


@pytest.fixture
async def auth_client():
    from app.db.session import engine
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://auth-test") as client:
            yield client
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_auth_lifecycle_rotation_last_seen_and_role_guard(auth_client: httpx.AsyncClient):
    from app.db.session import AsyncSessionLocal
    from app.models.auth_session import AuthSession

    async with _disposable_student(auth_client) as (email, password, registration):
        assert registration["access_token"]
        assert registration["refresh_token"]
        assert isinstance(registration["session_id"], int)
        assert registration["user"]["role"] == "student"

        login = await auth_client.post(
            "/api/auth/login",
            json={"email": email, "password": password, "device_name": "Android Test"},
        )
        assert login.status_code == 200
        original = login.json()
        assert original["requires_2fa"] is False

        me = await auth_client.get("/api/auth/me", headers=_auth(original["access_token"]))
        assert me.status_code == 200
        assert me.json()["id"] == registration["user"]["id"]

        account = await auth_client.get("/api/auth/account", headers=_auth(original["access_token"]))
        assert account.status_code == 200
        sessions = await auth_client.get("/api/auth/sessions", headers=_auth(original["access_token"]))
        assert sessions.status_code == 200
        assert len(sessions.json()) == 2

        bad_password_change = await auth_client.post(
            "/api/auth/change-password",
            json={
                "current_password": "not-the-password",
                "new_password": "AnotherPassword1!",
                "confirm_password": "AnotherPassword1!",
            },
            headers=_auth(original["access_token"]),
        )
        assert bad_password_change.status_code == 400
        disable_2fa = await auth_client.post(
            "/api/auth/2fa/disable",
            json={"password": "not-the-password"},
            headers=_auth(original["access_token"]),
        )
        assert disable_2fa.status_code == 400
        invalid_email_token = await auth_client.post(
            "/api/auth/verify-email",
            json={"token": "invalid-test-token"},
        )
        assert invalid_email_token.status_code == 400

        refreshed = await auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": original["refresh_token"]},
        )
        assert refreshed.status_code == 200
        first_rotation = refreshed.json()
        assert first_rotation["access_token"] != original["access_token"]
        assert first_rotation["refresh_token"] != original["refresh_token"]
        assert first_rotation["session_id"] == original["session_id"]

        replay = await auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": original["refresh_token"]},
        )
        assert replay.status_code == 401
        assert isinstance(replay.json().get("detail"), str)

        refreshed_again = await auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": first_rotation["refresh_token"]},
        )
        assert refreshed_again.status_code == 200
        current = refreshed_again.json()
        assert current["access_token"] != first_rotation["access_token"]
        assert current["refresh_token"] != first_rotation["refresh_token"]

        async with AsyncSessionLocal() as db:
            before = (await db.get(AuthSession, current["session_id"])).last_seen_at
        await asyncio.sleep(0.01)
        current_me = await auth_client.get("/api/auth/me", headers=_auth(current["access_token"]))
        assert current_me.status_code == 200
        async with AsyncSessionLocal() as db:
            after = (await db.get(AuthSession, current["session_id"])).last_seen_at
        assert after > before

        forbidden = await auth_client.get(
            "/api/teacher/setup/status",
            headers=_auth(current["access_token"]),
        )
        assert forbidden.status_code == 403

        logout = await auth_client.post(
            "/api/auth/logout",
            json={"refresh_token": current["refresh_token"]},
            headers=_auth(current["access_token"]),
        )
        assert logout.status_code == 200
        assert logout.json() == {"ok": True}
        revoked_access = await auth_client.get("/api/auth/me", headers=_auth(current["access_token"]))
        assert revoked_access.status_code == 401

        login_again = await auth_client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        latest = login_again.json()
        revoke_one = await auth_client.delete(
            f"/api/auth/sessions/{registration['session_id']}",
            headers=_auth(latest["access_token"]),
        )
        assert revoke_one.status_code == 200
        revoke_all = await auth_client.delete(
            "/api/auth/sessions",
            headers=_auth(latest["access_token"]),
        )
        assert revoke_all.status_code == 200
        assert (await auth_client.get("/api/auth/me", headers=_auth(latest["access_token"]))).status_code == 401


@pytest.mark.asyncio
async def test_refresh_rejects_expired_revoked_and_invalid_tokens(auth_client: httpx.AsyncClient):
    from app.db.session import AsyncSessionLocal
    from app.models.auth_session import AuthSession

    async with _disposable_student(auth_client) as (email, password, registration):
        async with AsyncSessionLocal() as db:
            session = await db.get(AuthSession, registration["session_id"])
            session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            await db.commit()
        expired = await auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": registration["refresh_token"]},
        )
        assert expired.status_code == 401

        login = await auth_client.post("/api/auth/login", json={"email": email, "password": password})
        active = login.json()
        async with AsyncSessionLocal() as db:
            session = await db.get(AuthSession, active["session_id"])
            session.revoked_at = datetime.now(timezone.utc)
            await db.commit()
        revoked = await auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": active["refresh_token"]},
        )
        assert revoked.status_code == 401

        invalid = await auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": secrets.token_urlsafe(48)},
        )
        assert invalid.status_code == 401
        assert isinstance(invalid.json().get("detail"), str)


@pytest.mark.asyncio
async def test_login_failure_has_stable_public_error(auth_client: httpx.AsyncClient):
    async with _disposable_student(auth_client) as (email, _password, _registration):
        response = await auth_client.post(
            "/api/auth/login",
            json={"email": email, "password": "wrong-password"},
        )
        assert response.status_code == 401
        assert response.json() == {"detail": "البريد أو كلمة المرور غير صحيحة"}
        assert "debug" not in response.text.lower()
