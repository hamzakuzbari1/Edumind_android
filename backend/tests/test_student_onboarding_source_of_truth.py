"""Student onboarding source-of-truth and approved runtime regression tests."""

from __future__ import annotations

import os
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import select, text


class _RowsResult:
    def __init__(self, *, rows=None, scalar=None):
        self._rows = list(rows or [])
        self._scalar = scalar

    def scalars(self):
        return self

    def all(self):
        return self._rows

    def scalar_one_or_none(self):
        return self._scalar


class _FakeDb:
    def __init__(self, results):
        self._results = list(results)
        self.added = []
        self.flushed = False

    async def execute(self, _statement):
        return self._results.pop(0)

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        self.flushed = True


@pytest.mark.asyncio
async def test_student_flags_and_onboarding_status_share_profile_state(monkeypatch):
    from app.models.enrollment import OnboardingStep
    from app.services import onboarding_service, user_status_service

    profile = SimpleNamespace(
        grade=None,
        onboarding_step=OnboardingStep.grade,
        onboarding_completed_at=None,
        payment_completed_at=None,
    )

    async def profile_for_test(_db, _user_id):
        return profile

    monkeypatch.setattr(user_status_service, "get_student_profile", profile_for_test)
    monkeypatch.setattr(onboarding_service, "get_student_profile", profile_for_test)

    flags = await user_status_service.student_flags(None, 42)
    status = await onboarding_service.get_onboarding_status(
        _FakeDb([_RowsResult(), _RowsResult()]),
        42,
    )

    assert flags["onboarding_complete"] is False
    assert flags["payment_complete"] is False
    assert flags["onboarding_step"] == OnboardingStep.grade.value
    assert status.onboarding_complete == flags["onboarding_complete"]
    assert status.payment_complete == flags["payment_complete"]
    assert status.step == flags["onboarding_step"]
    assert status.grade == flags["grade"]

    profile.grade = 12
    profile.onboarding_step = OnboardingStep.complete
    profile.onboarding_completed_at = datetime.now(timezone.utc)

    completed_flags = await user_status_service.student_flags(None, 42)
    completed_status = await onboarding_service.get_onboarding_status(
        _FakeDb([_RowsResult(), _RowsResult()]),
        42,
    )
    assert completed_flags["onboarding_complete"] is True
    assert completed_flags["onboarding_step"] == OnboardingStep.complete.value
    assert completed_status.onboarding_complete is True
    assert completed_status.step == OnboardingStep.complete.value


@pytest.mark.asyncio
async def test_missing_student_profile_never_claims_completion(monkeypatch):
    from app.services import user_status_service

    async def no_profile(_db, _user_id):
        return None

    monkeypatch.setattr(user_status_service, "get_student_profile", no_profile)
    flags = await user_status_service.student_flags(None, 99)

    assert flags["onboarding_complete"] is False
    assert flags["payment_complete"] is False
    assert flags["onboarding_step"] == "grade"
    assert flags["grade"] is None


@pytest.mark.asyncio
async def test_complete_requires_teacher_choices(monkeypatch):
    from app.models.enrollment import OnboardingStep
    from app.services import onboarding_service

    profile = SimpleNamespace(
        grade=12,
        onboarding_step=OnboardingStep.teachers,
        onboarding_completed_at=None,
    )

    async def profile_for_test(_db, _user_id):
        return profile

    monkeypatch.setattr(onboarding_service, "get_student_profile", profile_for_test)

    with pytest.raises(HTTPException) as exc_info:
        await onboarding_service.complete_onboarding(
            _FakeDb([_RowsResult()]),
            42,
        )

    assert exc_info.value.status_code == 400
    assert profile.onboarding_completed_at is None
    assert profile.onboarding_step == OnboardingStep.teachers


@pytest.mark.asyncio
async def test_complete_persists_canonical_completed_state(monkeypatch):
    from app.models.enrollment import OnboardingStep, StudentCourseAccess
    from app.schemas.catalog import CoursePreviewOut
    from app.schemas.onboarding import OnboardingStatusOut
    from app.services import onboarding_service

    profile = SimpleNamespace(
        grade=12,
        onboarding_step=OnboardingStep.teachers,
        onboarding_completed_at=None,
    )
    choice = SimpleNamespace(subject_id=7, teacher_profile_id=8)
    course = SimpleNamespace(id=9)

    async def profile_for_test(_db, _user_id):
        return profile

    async def course_for_test(_db, **_kwargs):
        return course

    async def preview_for_test(_db, _course):
        return CoursePreviewOut(
            id=9,
            title="Runtime Course",
            subject_name="Subject",
            teacher_name="Teacher",
            teacher_image_url=None,
            grade=12,
            price=0,
            currency="SYP",
        )

    async def completed_status(_db, _user_id):
        return OnboardingStatusOut(
            step=OnboardingStep.complete.value,
            grade=12,
            onboarding_complete=True,
        )

    monkeypatch.setattr(onboarding_service, "get_student_profile", profile_for_test)
    monkeypatch.setattr(onboarding_service, "get_course_for_teacher_subject", course_for_test)
    monkeypatch.setattr(onboarding_service, "course_to_preview", preview_for_test)
    monkeypatch.setattr(onboarding_service, "get_onboarding_status", completed_status)

    db = _FakeDb([_RowsResult(rows=[choice]), _RowsResult(scalar=None)])
    previews, status = await onboarding_service.complete_onboarding(db, 42)

    assert profile.onboarding_step == OnboardingStep.complete
    assert profile.onboarding_completed_at is not None
    assert db.flushed is True
    assert any(isinstance(item, StudentCourseAccess) for item in db.added)
    assert [preview.id for preview in previews] == [9]
    assert status.onboarding_complete is True
    assert status.step == OnboardingStep.complete.value


@pytest.mark.asyncio
async def test_complete_without_published_course_does_not_invent_one(monkeypatch):
    from app.models.enrollment import OnboardingStep, StudentCourseAccess
    from app.schemas.onboarding import OnboardingStatusOut
    from app.services import onboarding_service

    profile = SimpleNamespace(
        grade=12,
        onboarding_step=OnboardingStep.teachers,
        onboarding_completed_at=None,
    )
    choice = SimpleNamespace(subject_id=7, teacher_profile_id=8)

    async def profile_for_test(_db, _user_id):
        return profile

    async def no_course(_db, **_kwargs):
        return None

    async def completed_status(_db, _user_id):
        return OnboardingStatusOut(
            step=OnboardingStep.complete.value,
            grade=12,
            onboarding_complete=True,
        )

    monkeypatch.setattr(onboarding_service, "get_student_profile", profile_for_test)
    monkeypatch.setattr(onboarding_service, "get_course_for_teacher_subject", no_course)
    monkeypatch.setattr(onboarding_service, "get_onboarding_status", completed_status)

    db = _FakeDb([_RowsResult(rows=[choice])])
    previews, status = await onboarding_service.complete_onboarding(db, 42)

    assert profile.onboarding_step == OnboardingStep.complete
    assert profile.onboarding_completed_at is not None
    assert previews == []
    assert not any(isinstance(item, StudentCourseAccess) for item in db.added)
    assert status.onboarding_complete is True



@pytest.mark.asyncio
async def test_teacher_and_parent_flag_semantics_are_unchanged(monkeypatch):
    from app.models.user import UserRole
    from app.services import user_status_service

    async def teacher_is_complete(_db, _user_id):
        return True

    monkeypatch.setattr(user_status_service, "teacher_setup_complete", teacher_is_complete)

    teacher = SimpleNamespace(id=1, role=UserRole.teacher)
    parent = SimpleNamespace(id=2, role=UserRole.parent)
    teacher_flags = await user_status_service.build_user_extras(None, teacher)
    parent_flags = await user_status_service.build_user_extras(None, parent)

    assert teacher_flags == {
        "onboarding_complete": True,
        "needs_payment": False,
        "payment_complete": True,
        "teacher_setup_complete": True,
        "onboarding_step": "complete",
        "grade": None,
    }
    assert parent_flags == {
        "onboarding_complete": True,
        "needs_payment": False,
        "payment_complete": True,
        "teacher_setup_complete": True,
        "onboarding_step": "complete",
        "grade": None,
    }


def _auth(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


async def _cleanup_user(user_id: int) -> None:
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        for table, column in (
            ("student_engagement_events", "student_id"),
            ("student_activity_sessions", "student_id"),
            ("student_course_access", "student_id"),
            ("student_teacher_choices", "student_id"),
            ("student_subject_choices", "student_id"),
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
    email = f"onboarding-runtime-{uuid.uuid4().hex}@example.com"
    password = secrets.token_urlsafe(24) + "Aa1!"
    response = await client.post(
        "/api/auth/register",
        json={
            "name": "Onboarding Runtime Test",
            "email": email,
            "password": password,
            "role": "student",
            "device_name": "Onboarding Test Device",
        },
    )
    assert response.status_code == 200, response.text
    registration = response.json()
    try:
        yield email, password, registration
    finally:
        await _cleanup_user(registration["user"]["id"])


@pytest.fixture
async def onboarding_client():
    from app.db.session import engine
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://onboarding-test") as client:
            yield client
    finally:
        await engine.dispose()


runtime_test = pytest.mark.skipif(
    os.getenv("RUN_ONBOARDING_RUNTIME_TESTS") != "1",
    reason="set RUN_ONBOARDING_RUNTIME_TESTS=1 only for approved Supabase DEV verification",
)


@pytest.mark.integration
@runtime_test
@pytest.mark.asyncio
async def test_new_student_and_grade_state_persist_across_login(onboarding_client):
    from app.db.session import AsyncSessionLocal
    from app.models.enrollment import OnboardingStep
    from app.models.profile import StudentProfile

    async with _disposable_student(onboarding_client) as (email, password, registration):
        registered_user = registration["user"]
        assert registered_user["onboarding_complete"] is False
        assert registered_user["onboarding_step"] == OnboardingStep.grade.value

        headers = _auth(registration["access_token"])
        me = await onboarding_client.get("/api/auth/me", headers=headers)
        status_response = await onboarding_client.get(
            "/api/student/onboarding/status",
            headers=headers,
        )
        assert me.status_code == 200
        assert status_response.status_code == 200
        assert me.json()["onboarding_complete"] is False
        assert status_response.json()["onboarding_complete"] is False
        assert me.json()["onboarding_step"] == status_response.json()["step"] == "grade"

        saved = await onboarding_client.put(
            "/api/student/onboarding/grade",
            json={"grade": 12},
            headers=headers,
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["step"] == OnboardingStep.subjects.value
        assert saved.json()["grade"] == 12

        async with AsyncSessionLocal() as db:
            profile = (
                await db.execute(
                    select(StudentProfile).where(
                        StudentProfile.user_id == registered_user["id"]
                    )
                )
            ).scalar_one()
            assert profile.grade == 12
            assert profile.onboarding_step == OnboardingStep.subjects
            assert profile.onboarding_completed_at is None

        login = await onboarding_client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        assert login.status_code == 200
        restored = login.json()
        assert restored["user"]["onboarding_complete"] is False
        assert restored["user"]["onboarding_step"] == OnboardingStep.subjects.value

        refreshed = await onboarding_client.post(
            "/api/auth/refresh",
            json={"refresh_token": restored["refresh_token"]},
        )
        assert refreshed.status_code == 200
        assert refreshed.json()["user"]["onboarding_complete"] is False
        assert refreshed.json()["user"]["onboarding_step"] == OnboardingStep.subjects.value


@pytest.mark.integration
@runtime_test
@pytest.mark.asyncio
async def test_full_onboarding_restores_completed_state_when_catalog_exists(onboarding_client):
    from app.db.session import AsyncSessionLocal
    from app.models.catalog import Course, TeacherProfile

    async with AsyncSessionLocal() as db:
        candidate = (
            await db.execute(
                select(Course)
                .join(TeacherProfile, Course.teacher_profile_id == TeacherProfile.id)
                .where(
                    Course.is_active.is_(True),
                    Course.is_published.is_(True),
                    TeacherProfile.active.is_(True),
                )
                .order_by(Course.id)
                .limit(1)
            )
        ).scalar_one_or_none()

    if candidate is None:
        pytest.skip("Supabase DEV has no active published course for onboarding verification")

    async with _disposable_student(onboarding_client) as (email, password, registration):
        headers = _auth(registration["access_token"])
        grade = await onboarding_client.put(
            "/api/student/onboarding/grade",
            json={"grade": candidate.grade},
            headers=headers,
        )
        assert grade.status_code == 200, grade.text

        visible_subjects = await onboarding_client.get(
            "/api/catalog/subjects",
            params={"grade": candidate.grade},
            headers=headers,
        )
        assert visible_subjects.status_code == 200, visible_subjects.text
        assert candidate.subject_id in {
            subject["id"] for subject in visible_subjects.json()
        }

        visible_teachers = await onboarding_client.get(
            "/api/catalog/teachers",
            params={
                "subject_id": candidate.subject_id,
                "grade": candidate.grade,
            },
            headers=headers,
        )
        assert visible_teachers.status_code == 200, visible_teachers.text
        assert candidate.teacher_profile_id in {
            teacher["id"] for teacher in visible_teachers.json()
        }

        subjects = await onboarding_client.put(
            "/api/student/onboarding/subjects",
            json={"subject_ids": [candidate.subject_id]},
            headers=headers,
        )
        assert subjects.status_code == 200, subjects.text
        assert subjects.json()["step"] == "teachers"
        assert subjects.json()["selected_subject_ids"] == [candidate.subject_id]

        teachers = await onboarding_client.put(
            "/api/student/onboarding/teachers",
            json={
                "choices": [
                    {
                        "subject_id": candidate.subject_id,
                        "teacher_profile_id": candidate.teacher_profile_id,
                    }
                ]
            },
            headers=headers,
        )
        assert teachers.status_code == 200, teachers.text
        assert teachers.json()["step"] == "teachers"
        assert teachers.json()["teacher_choices"] == [
            {
                "subject_id": candidate.subject_id,
                "teacher_profile_id": candidate.teacher_profile_id,
            }
        ]

        complete = await onboarding_client.post(
            "/api/student/onboarding/complete",
            headers=headers,
        )
        assert complete.status_code == 200, complete.text
        assert complete.json()["ok"] is True

        me = await onboarding_client.get("/api/auth/me", headers=headers)
        status_response = await onboarding_client.get(
            "/api/student/onboarding/status",
            headers=headers,
        )
        assert me.json()["onboarding_complete"] is True
        assert me.json()["onboarding_step"] == "complete"
        assert status_response.json()["onboarding_complete"] is True
        assert status_response.json()["step"] == "complete"

        logout = await onboarding_client.post(
            "/api/auth/logout",
            json={"refresh_token": registration["refresh_token"]},
            headers=headers,
        )
        assert logout.status_code == 200

        login = await onboarding_client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        assert login.status_code == 200
        restored = login.json()
        assert restored["user"]["onboarding_complete"] is True
        assert restored["user"]["onboarding_step"] == "complete"
