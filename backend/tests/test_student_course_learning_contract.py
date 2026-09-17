from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException


class _Result:
    def __init__(self, *, scalar=None, rows=None):
        self._scalar = scalar
        self._rows = list(rows or [])

    def scalar_one_or_none(self):
        return self._scalar

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeDb:
    def __init__(self, *results):
        self._results = list(results)
        self.flushed = False

    async def execute(self, _statement):
        if not self._results:
            raise AssertionError("unexpected database execute")
        return self._results.pop(0)

    async def flush(self):
        self.flushed = True


def _course(**overrides):
    data = {
        "id": 10,
        "title": "Physics 12",
        "description": "Course description",
        "subject": SimpleNamespace(name_ar="الفيزياء"),
        "teacher_profile": SimpleNamespace(
            id=20,
            user_id=30,
            full_name="Teacher",
            image_url=None,
            active=True,
        ),
        "grade": 12,
        "price": 0,
        "currency": "SYP",
        "is_active": True,
        "is_published": True,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _lesson(**overrides):
    from app.models.lesson import LessonStatus

    data = {
        "id": 100,
        "course_id": 10,
        "unit_id": 1,
        "title": "Lesson",
        "description": None,
        "preview": None,
        "video_url": None,
        "pdf_path": None,
        "homework_path": None,
        "sort_order": 0,
        "status": LessonStatus.processed,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _access(**overrides):
    from app.models.enrollment import PaymentStatus

    data = {
        "id": 1,
        "student_id": 7,
        "course_id": 10,
        "payment_status": PaymentStatus.pending,
        "access_status": "active",
        "source": "manual_grant",
        "enrollment": SimpleNamespace(status="active"),
        "activated_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "expires_at": datetime(2027, 1, 1, tzinfo=timezone.utc),
        "unlocked_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "revoked_at": None,
        "revocation_reason": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _progress(**overrides):
    now = datetime(2026, 1, 2, tzinfo=timezone.utc)
    data = {
        "lesson_id": 100,
        "video_progress_percent": 0.0,
        "pdf_progress_percent": 0.0,
        "pdf_opened": False,
        "quiz_submitted": False,
        "quiz_score_percent": 0.0,
        "started_at": None,
        "updated_at": now,
        "completed_at": None,
        "completion_type": None,
        "completion_percentage": 0.0,
        "is_completed": False,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


@pytest.mark.asyncio
async def test_course_detail_returns_units_lessons_and_resume(monkeypatch):
    from app.services import student_courses_service as service

    unit_foundation = SimpleNamespace(id=1, title="Foundation", description=None, sort_order=2)
    unit_intro = SimpleNamespace(id=2, title="Intro", description=None, sort_order=1)
    lesson_in_progress = _lesson(id=100, unit_id=1, title="Vectors", sort_order=2)
    lesson_done = _lesson(id=101, unit_id=2, title="Measurement", sort_order=1)
    progress = _progress(
        lesson_id=100,
        video_progress_percent=45,
        completion_percentage=45,
        started_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
    )

    async def profile_for_test(_db, _student_id):
        return SimpleNamespace(id=77, grade=12)

    async def course_lessons_for_test(_db, _course_id):
        return [lesson_in_progress, lesson_done]

    async def course_units_for_test(_db, _course_id):
        return [unit_intro, unit_foundation]

    async def completed_for_test(_db, _student_id, _lesson_ids):
        return {101}

    async def progress_for_test(_db, _student_id, _lesson_ids):
        return {100: progress}

    async def caps_for_test(_db, _lesson):
        return {
            "has_video": True,
            "has_pdf": False,
            "has_homework": False,
            "has_ai_chat": False,
            "has_generated_quiz": False,
            "ai_status": "processed",
            "ai_ready": False,
            "quiz_ready": False,
            "ai_processing": False,
            "ai_error": False,
            "error_message": None,
            "chunk_count": 0,
            "quiz_question_count": 0,
        }

    monkeypatch.setattr(service, "get_student_profile", profile_for_test)
    monkeypatch.setattr(service, "_course_lessons", course_lessons_for_test)
    monkeypatch.setattr(service, "_course_units", course_units_for_test)
    monkeypatch.setattr(service, "_completed_lesson_ids", completed_for_test)
    monkeypatch.setattr(service, "_progress_map", progress_for_test)
    monkeypatch.setattr(service, "build_lesson_capabilities", caps_for_test)
    monkeypatch.setattr(service, "resolve_lesson_content_type", lambda _lesson: "video")
    monkeypatch.setattr(service, "assets_public_urls", lambda _lesson: {"video": "/uploads/v.mp4", "pdf": None, "homework": None})

    from app.services import messaging_service

    async def linked_parent_ids_for_test(_db, _student_id):
        return []

    async def existing_thread_for_test(*_args, **_kwargs):
        return None

    monkeypatch.setattr(messaging_service, "_linked_parent_ids", linked_parent_ids_for_test)
    monkeypatch.setattr(messaging_service, "_find_existing_course_thread", existing_thread_for_test)

    db = _FakeDb(_Result(scalar=_course()), _Result(scalar=_access()))
    detail = await service.get_student_course(db, student_id=7, course_id=10)

    assert detail.unlocked is True
    assert detail.access_status == "active"
    assert detail.access_source == "manual_grant"
    assert detail.enrollment_status == "active"
    assert [unit.title for unit in detail.units] == ["Intro", "Foundation"]
    assert detail.units[0].lessons[0].id == 101
    assert detail.units[0].lessons[0].unit_id == 2
    assert detail.units[1].lessons[0].completion_percent == 45
    assert [lesson.id for lesson in detail.lessons] == [101, 100]
    assert detail.resume_lesson is not None
    assert detail.resume_lesson.lesson_id == 100
    assert detail.resume_lesson.unit_title == "Foundation"


def test_canonical_access_status_takes_precedence_over_legacy_payment():
    from app.services.subscription_access_service import is_access_active

    assert is_access_active(_access(payment_status="pending", access_status="active")) is True
    assert is_access_active(_access(payment_status="paid", access_status="revoked")) is False
    assert is_access_active(_access(payment_status="paid", access_status="suspended")) is False
    assert is_access_active(
        _access(payment_status="paid", access_status="active", expires_at=datetime.now(timezone.utc) - timedelta(days=1))
    ) is False


@pytest.mark.asyncio
async def test_student_lesson_access_requires_visible_course_and_active_access(monkeypatch):
    from app.services import student_courses_service as service

    monkeypatch.setattr(service, "lesson_is_visible", lambda _lesson: True)

    db = _FakeDb(_Result(scalar=_course()), _Result(scalar=_access()))
    assert await service.student_has_lesson_access(db, 7, _lesson(video_url="/uploads/v.mp4")) is True

    denied_db = _FakeDb(_Result(scalar=_course()), _Result(scalar=_access(access_status="revoked")))
    assert await service.student_has_lesson_access(denied_db, 7, _lesson(video_url="/uploads/v.mp4")) is False


@pytest.mark.asyncio
async def test_get_progress_requires_access_before_creating_progress(monkeypatch):
    from app.services import lesson_completion_service as service

    async def lesson_for_test(_db, _lesson_id):
        return _lesson(video_url="/uploads/v.mp4")

    async def no_access(_db, _student_id, _lesson):
        return False

    async def should_not_create(*_args, **_kwargs):
        raise AssertionError("progress row must not be created without access")

    monkeypatch.setattr(service, "_get_lesson", lesson_for_test)
    monkeypatch.setattr(service, "student_has_lesson_access", no_access)
    monkeypatch.setattr(service, "get_or_create_progress", should_not_create)

    with pytest.raises(HTTPException) as exc_info:
        await service.progress_to_dict(_FakeDb(), student_id=7, lesson_id=100)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_progress_update_and_completion_use_valid_access(monkeypatch):
    from app.services import lesson_completion_service as service

    progress = _progress()

    async def lesson_for_test(_db, _lesson_id):
        return _lesson(video_url="/uploads/v.mp4")

    async def has_access(_db, _student_id, _lesson):
        return True

    async def progress_for_test(_db, _student_id, _lesson_id):
        return progress

    async def caps_for_test(_db, _lesson):
        return {
            "has_video": True,
            "has_pdf": False,
            "has_generated_quiz": False,
        }

    async def no_quiz_sync(*_args, **_kwargs):
        return None

    async def after_completed(*_args, **_kwargs):
        return None

    monkeypatch.setattr(service, "_get_lesson", lesson_for_test)
    monkeypatch.setattr(service, "student_has_lesson_access", has_access)
    monkeypatch.setattr(service, "get_or_create_progress", progress_for_test)
    monkeypatch.setattr(service, "build_lesson_capabilities", caps_for_test)
    monkeypatch.setattr(service, "_sync_quiz_data", no_quiz_sync)

    from app.services import integration_hooks

    monkeypatch.setattr(integration_hooks, "after_lesson_completed", after_completed)

    db = _FakeDb()
    updated = await service.update_lesson_progress(db, 7, 100, video_percent=95)
    assert db.flushed is True
    assert progress.started_at is not None
    assert updated["requirements"]["video_met"] is True
    assert updated["can_verify"] is True

    result = await service.verify_lesson_completion(db, 7, 100)
    assert result["success"] is True
    assert progress.completed_at is not None
    assert progress.completion_type == service.COMPLETION_TYPE_VERIFIED


def test_activate_paid_access_promotes_pending_and_sets_window():
    from app.core.config import get_settings
    from app.models.enrollment import PaymentStatus
    from app.services.subscription_access_service import activate_paid_access, is_access_active

    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    access = _access(
        payment_status=PaymentStatus.pending,
        access_status="pending",
        source=None,
        unlocked_at=None,
        activated_at=None,
        expires_at=None,
    )
    activate_paid_access(access, now)

    assert access.payment_status == PaymentStatus.paid
    assert access.access_status == "active"
    assert access.source == "payment"
    assert access.activated_at == now
    assert access.expires_at == now + timedelta(days=get_settings().SUBSCRIPTION_TERM_DAYS)
    assert is_access_active(access, now) is True


def test_activate_paid_access_extends_expiring_paid_window():
    from app.core.config import get_settings
    from app.models.enrollment import PaymentStatus
    from app.services.subscription_access_service import (
        activate_paid_access,
        subscription_lifecycle_status,
    )

    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    expires = now + timedelta(days=5)
    access = _access(
        payment_status=PaymentStatus.paid,
        access_status="active",
        expires_at=expires,
    )
    assert subscription_lifecycle_status(access, now) == "expiring_soon"
    activate_paid_access(access, now)
    assert access.expires_at == expires + timedelta(days=get_settings().SUBSCRIPTION_TERM_DAYS)
    assert subscription_lifecycle_status(access, now) == "active"


def test_activate_paid_access_does_not_restore_revoked():
    from app.models.enrollment import PaymentStatus
    from app.services.subscription_access_service import activate_paid_access, is_access_active

    access = _access(payment_status=PaymentStatus.paid, access_status="revoked")
    activate_paid_access(access, datetime.now(timezone.utc))
    assert access.access_status == "revoked"
    assert is_access_active(access) is False
