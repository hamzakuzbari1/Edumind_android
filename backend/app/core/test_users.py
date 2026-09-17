"""Isolated test accounts — scripts must never mutate real user credentials."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

TEST_EMAIL_DOMAIN = "@eduspark-test.dev"
TEST_USER_PASSWORD = "TestOnly123!"


class TestUserGuardError(RuntimeError):
    """Raised when a script attempts credential changes on a non-test account."""


@dataclass(frozen=True, slots=True)
class TestUserSpec:
    key: str
    email: str
    name: str
    role: str
    purpose: str
    email_verified: bool = True


TEST_USER_SPECS: tuple[TestUserSpec, ...] = (
    TestUserSpec("auth_student", "test.auth.student@eduspark-test.dev", "Test Student", "student", "general auth API checks"),
    TestUserSpec("auth_teacher", "test.auth.teacher@eduspark-test.dev", "Test Teacher", "teacher", "general auth API checks"),
    TestUserSpec("auth_parent", "test.auth.parent@eduspark-test.dev", "Test Parent", "parent", "general auth API checks"),
    TestUserSpec(
        "password_reset",
        "test.password@eduspark-test.dev",
        "Test Password Reset",
        "student",
        "password reset / forgot-password flow tests",
    ),
    TestUserSpec(
        "email_verify",
        "test.verify@eduspark-test.dev",
        "Test Email Verify",
        "student",
        "email verification token tests",
        email_verified=False,
    ),
    TestUserSpec(
        "account_security",
        "test.security@eduspark-test.dev",
        "Test Account Security",
        "student",
        "change email/password security center tests",
    ),
    TestUserSpec(
        "gamification",
        "test.gamification@eduspark-test.dev",
        "Test Gamification",
        "student",
        "XP, badges, achievements tests",
    ),
    TestUserSpec(
        "two_factor",
        "test.2fa@eduspark-test.dev",
        "Test Two Factor",
        "student",
        "2FA enable/login flow tests",
    ),
)

TEST_USERS_BY_KEY: dict[str, TestUserSpec] = {spec.key: spec for spec in TEST_USER_SPECS}
TEST_USERS_BY_EMAIL: dict[str, TestUserSpec] = {spec.email.lower(): spec for spec in TEST_USER_SPECS}


def is_test_user_email(email: str | None) -> bool:
    if not email:
        return False
    normalized = email.strip().lower()
    if normalized in TEST_USERS_BY_EMAIL:
        return True
    return normalized.endswith(TEST_EMAIL_DOMAIN)


def require_test_user_email(email: str, *, action: str = "credential mutation") -> str:
    """Block scripts from changing passwords/tokens on real accounts."""
    normalized = email.strip().lower()
    if not is_test_user_email(normalized):
        raise TestUserGuardError(
            f"Refusing {action} for non-test account {normalized!r}. "
            f"Use seeded @eduspark-test.dev users only. Run: python scripts/seed_test_users.py"
        )
    return normalized


def default_test_email(purpose: str = "auth_student") -> str:
    spec = TEST_USERS_BY_KEY.get(purpose)
    if not spec:
        raise KeyError(f"Unknown test user purpose: {purpose}")
    return spec.email


def verified_at_for(spec: TestUserSpec) -> datetime | None:
    if spec.email_verified:
        return datetime.now(timezone.utc)
    return None
