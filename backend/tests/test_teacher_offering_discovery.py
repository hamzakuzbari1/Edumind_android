from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.core.demo_guard import is_demo_email
from app.models.catalog import Course, TeacherProfileGrade, TeacherProfileSubject
from app.services import catalog_service, teacher_setup_service
from app.services.student_courses_service import _is_real_catalog_teacher


class _Result:
    def __init__(self, *, rows=None, scalars=None):
        self._rows = list(rows if rows is not None else scalars or [])

    def all(self):
        return self._rows

    def scalars(self):
        return self

    def unique(self):
        return self

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class _RecordingDb:
    def __init__(self, results):
        self._results = list(results)
        self.added = []
        self.flushed = False

    async def execute(self, _statement):
        if not self._results:
            raise AssertionError("unexpected database execute")
        return self._results.pop(0)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed = True


def _subject(*, subject_id=4, grade=12, slug="math", name_ar="رياضيات", is_active=True):
    return SimpleNamespace(id=subject_id, grade=grade, slug=slug, name_ar=name_ar, is_active=is_active)


def test_setup_does_not_auto_create_courses():
    assert not hasattr(teacher_setup_service, "ensure_teacher_offering_courses")
    assert not hasattr(teacher_setup_service, "ensure_offering_courses_for_grade")


@pytest.mark.asyncio
async def test_update_teaching_reinserts_subject_and_grade_links_without_courses(monkeypatch):
    added = []
    math = _subject()

    class Db(_RecordingDb):
        def add(self, obj):
            added.append(obj)

    db = Db(
        [
            _Result(scalars=[math]),
            _Result(rows=[]),
            _Result(rows=[]),
        ]
    )
    tp = SimpleNamespace(id=9, setup_completed_at=datetime.now(timezone.utc))
    user = SimpleNamespace(id=3)

    async def _profile(_db, _user):
        return tp

    async def _status(_db, _user):
        return SimpleNamespace(subject_ids=[4], grades=[12])

    monkeypatch.setattr(teacher_setup_service, "get_or_create_teacher_profile", _profile)
    monkeypatch.setattr(teacher_setup_service, "get_setup_status", _status)

    status = await teacher_setup_service.update_teaching(db, user, [4], [12])

    assert status.subject_ids == [4]
    assert any(isinstance(obj, TeacherProfileSubject) and obj.subject_id == 4 for obj in added)
    assert any(isinstance(obj, TeacherProfileGrade) and obj.grade == 12 for obj in added)
    assert not any(isinstance(obj, Course) for obj in added)


@pytest.mark.asyncio
async def test_complete_setup_does_not_insert_a_course(monkeypatch):
    added = []
    tp = SimpleNamespace(id=9, full_name="معلم الرياضيات", setup_completed_at=None)
    user = SimpleNamespace(id=3, name="معلم الرياضيات")

    class Db(_RecordingDb):
        def add(self, obj):
            added.append(obj)

    db = Db([_Result(rows=[(1,)])])

    async def _profile(_db, _user):
        return tp

    async def _status(_db, _user):
        return SimpleNamespace(setup_complete=True, subject_ids=[4], grades=[12])

    monkeypatch.setattr(teacher_setup_service, "get_or_create_teacher_profile", _profile)
    monkeypatch.setattr(teacher_setup_service, "get_setup_status", _status)

    await teacher_setup_service.complete_setup(db, user)

    assert tp.setup_completed_at is not None
    assert not any(isinstance(obj, Course) for obj in added)


@pytest.mark.asyncio
async def test_list_teachers_includes_completed_math_teacher_without_course():
    subject = _subject()
    teacher = SimpleNamespace(
        id=11,
        full_name="معلم الرياضيات",
        image_url=None,
        bio="Math",
        rating=4.8,
        student_count=0,
        active=True,
        setup_completed_at=datetime.now(timezone.utc),
        user=SimpleNamespace(email="math.teacher@school.sy", role="teacher"),
    )

    class Db:
        async def get(self, _model, _id):
            return subject

        async def execute(self, _statement):
            return _Result(scalars=[teacher])

    cards = await catalog_service.list_teachers_for_subject(Db(), subject_id=4, grade=12)
    assert [card.id for card in cards] == [11]
    assert cards[0].subject_name == "رياضيات"


@pytest.mark.asyncio
async def test_list_teachers_excludes_wrong_grade_subject_mismatch():
    class Db:
        async def get(self, _model, _id):
            return _subject(grade=11)

        async def execute(self, _statement):
            raise AssertionError("must not query teachers when subject grade mismatches")

    cards = await catalog_service.list_teachers_for_subject(Db(), subject_id=4, grade=12)
    assert cards == []


@pytest.mark.asyncio
async def test_list_teachers_excludes_demo_seed_teacher():
    subject = _subject()
    teacher = SimpleNamespace(
        id=11,
        full_name="أحمد الحسين",
        image_url=None,
        bio=None,
        rating=4.8,
        student_count=0,
        active=True,
        setup_completed_at=datetime.now(timezone.utc),
        user=SimpleNamespace(email="teacher@eduspark.sy", role="teacher"),
    )

    class Db:
        async def get(self, _model, _id):
            return subject

        async def execute(self, _statement):
            return _Result(scalars=[teacher])

    cards = await catalog_service.list_teachers_for_subject(Db(), subject_id=4, grade=12)
    assert cards == []


def test_demo_guard_does_not_hide_real_eduspark_teacher():
    assert is_demo_email("math.teacher@eduspark.sy") is False
    assert is_demo_email("teacher@eduspark.sy") is True


def test_real_catalog_teacher_rejects_non_teacher_role():
    course = SimpleNamespace(
        teacher_profile=SimpleNamespace(
            full_name="Real Teacher",
            user=SimpleNamespace(email="real@school.sy", role="student"),
        )
    )
    assert _is_real_catalog_teacher(course) is False


def test_real_catalog_teacher_accepts_completed_math_teacher():
    course = SimpleNamespace(
        teacher_profile=SimpleNamespace(
            full_name="معلم الرياضيات",
            user=SimpleNamespace(email="math.teacher@school.sy", role="teacher"),
        )
    )
    assert _is_real_catalog_teacher(course) is True
