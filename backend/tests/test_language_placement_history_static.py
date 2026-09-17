"""Runtime consolidation, read-only history, and public-upload regression tests."""

from __future__ import annotations

import importlib

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import delete, func, select

from app.api import language_student
from app.core.deps import AuthContext, get_auth_context
from app.db.session import get_db
from app.models.language.analytics import LanguageAnalytics
from app.models.language.assessment import LanguageAssessment, LanguageAssessmentSkillScore
from app.models.language.catalog import Language
from app.models.language.enums import LanguageLevel, LanguagePlacementAttemptStatus, LanguageSkill
from app.models.language.exam import LanguageExamSession
from app.models.language.placement import LanguagePlacementAttempt
from app.models.language.profile import LanguageStudentProfile
from app.models.user import User, UserRole
from app.schemas.language_placement import PlacementHistoryResultOut, PlacementHistorySkillOut
from app.services.language_placement_history_service import (
    coherent_ai_exam_session,
    coherent_legacy_assessment,
)
from app.main import _is_unsafe_public_upload_path


def test_legacy_placement_service_module_is_permanently_removed():
    """The deleted wizard service must stay uninstantiable, not merely uncalled."""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("app.services.language_placement_service")


@pytest.mark.parametrize(
    "path",
    [
        "/uploads/student_7/language_placement/file.wav",
        "/uploads/x/../student_7/language_placement/file.wav",
        "/uploads/x/%2e%2e/student_7/language_placement/file.wav",
        "/uploads/x/%252e%252e/student_7/language_placement/file.wav",
        r"/uploads/x\..\student_7\language_placement\file.wav",
    ],
)
def test_private_placement_path_normalization_rejects_every_variant(path):
    assert _is_unsafe_public_upload_path(path)


@pytest.mark.asyncio
async def test_real_asgi_upload_mount_never_serves_historical_placement_audio(
    api_client,
    asgi_app,
    tmp_path,
):
    upload_mount = next(route for route in asgi_app.routes if getattr(route, "name", None) == "uploads")
    static_app = upload_mount.app
    old_directory = static_app.directory
    old_directories = static_app.all_directories

    private_file = tmp_path / "student_7" / "language_placement" / "file.wav"
    private_file.parent.mkdir(parents=True)
    private_file.write_bytes(b"private-placement-audio")
    (tmp_path / "public.txt").write_text("public-control", encoding="utf-8")

    static_app.directory = str(tmp_path)
    static_app.all_directories = [str(tmp_path)]
    try:
        control = await api_client.get("/uploads/public.txt")
        assert control.status_code == 200
        assert control.text == "public-control"

        paths = [
            "/uploads/student_7/language_placement/file.wav",
            "/uploads/x/../student_7/language_placement/file.wav",
            "/uploads/x/%2e%2e/student_7/language_placement/file.wav",
            "/uploads/x/%252e%252e/student_7/language_placement/file.wav",
            r"/uploads/x\..\student_7\language_placement\file.wav",
        ]
        for path in paths:
            response = await api_client.get(path)
            assert response.status_code == 404, path
            assert response.content != b"private-placement-audio", path
    finally:
        static_app.directory = old_directory
        static_app.all_directories = old_directories


@pytest.mark.asyncio
async def test_legacy_execution_routes_are_not_registered_and_compatibility_is_inert(
    api_client,
    asgi_app,
):
    registered_paths = {getattr(route, "path", "") for route in asgi_app.routes}
    old_paths = {
        "/api/student/languages/placement/start",
        "/api/student/languages/placement/responses",
        "/api/student/languages/placement/speaking/upload",
        "/api/student/languages/placement/submit",
    }
    assert registered_paths.isdisjoint(old_paths)
    assert "/api/student/languages/placement/{legacy_path:path}" in registered_paths

    calls = [
        ("POST", "/api/student/languages/placement/start"),
        ("PUT", "/api/student/languages/placement/responses"),
        ("POST", "/api/student/languages/placement/speaking/upload"),
        ("POST", "/api/student/languages/placement/submit"),
    ]
    for method, path in calls:
        response = await api_client.request(
            method,
            path,
            content=b"malformed-body-that-must-not-be-parsed",
            headers={"Content-Type": "multipart/form-data; boundary=broken"},
        )
        assert response.status_code == 410
        assert response.json()["detail"]["code"] == "legacy_placement_removed"
        assert response.json()["detail"]["redirect"] == "/student/languages/exam"


def test_legacy_route_declares_no_auth_or_database_dependencies(asgi_app):
    """The compatibility route must be structurally incapable of authenticating or touching the DB.

    This checks the FastAPI dependency graph directly, so the guarantee holds even if a future
    change adds a body/query parameter to the handler without also adding a real dependency.
    """
    route = next(
        r
        for r in asgi_app.routes
        if getattr(r, "path", "") == "/api/student/languages/placement/{legacy_path:path}"
    )
    assert route.methods == {"POST", "PUT", "PATCH", "DELETE"}
    assert route.endpoint is language_student.legacy_placement_removed
    assert route.dependant.dependencies == []
    assert route.dependant.call is language_student.legacy_placement_removed


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.postgresql
async def test_legacy_routes_never_write_to_the_database_or_touch_placement_completed_at(
    api_client,
    postgres_session_factory,
):
    """Hitting every legacy mutation path must leave every placement-adjacent table untouched."""
    marker = datetime.now(timezone.utc).strftime("%H%M%S%f")
    async with postgres_session_factory() as db:
        student = User(
            email=f"legacy-inert-{marker}@example.test",
            name="Legacy inert student",
            hashed_password="not-used",
            role=UserRole.student,
        )
        language = Language(
            code=f"li{marker[-11:]}",
            name_en="Legacy inert language",
            name_ar="Legacy inert language",
            is_active=True,
        )
        db.add_all([student, language])
        await db.flush()
        profile = LanguageStudentProfile(
            student_id=student.id,
            language_id=language.id,
            placement_completed_at=None,
        )
        db.add(profile)
        await db.commit()
        student_id, language_id = student.id, language.id

    async def snapshot() -> dict[str, int]:
        async with postgres_session_factory() as db:
            counts = {}
            for label, model in (
                ("attempts", LanguagePlacementAttempt),
                ("assessments", LanguageAssessment),
                ("exam_sessions", LanguageExamSession),
            ):
                counts[label] = (
                    await db.execute(
                        select(func.count()).select_from(model).where(model.student_id == student_id)
                    )
                ).scalar_one()
            return counts

    before = await snapshot()
    try:
        calls = [
            ("POST", "/api/student/languages/placement/start"),
            ("PUT", "/api/student/languages/placement/responses"),
            ("POST", "/api/student/languages/placement/speaking/upload"),
            ("POST", "/api/student/languages/placement/submit"),
        ]
        for method, path in calls:
            response = await api_client.request(
                method,
                path,
                content=b"malformed-body-that-must-not-be-parsed",
                headers={"Content-Type": "multipart/form-data; boundary=broken"},
            )
            assert response.status_code == 410

        after = await snapshot()
        assert after == before

        async with postgres_session_factory() as db:
            refreshed = (
                await db.execute(
                    select(LanguageStudentProfile).where(
                        LanguageStudentProfile.student_id == student_id,
                        LanguageStudentProfile.language_id == language_id,
                    )
                )
            ).scalar_one()
        assert refreshed.placement_completed_at is None
    finally:
        async with postgres_session_factory() as db:
            await db.execute(
                delete(LanguageStudentProfile).where(LanguageStudentProfile.student_id == student_id)
            )
            await db.execute(delete(User).where(User.id == student_id))
            await db.execute(delete(Language).where(Language.id == language_id))
            await db.commit()


def _legacy_snapshot() -> PlacementHistoryResultOut:
    return PlacementHistoryResultOut(
        record_id="legacy:11",
        assessment_id=11,
        attempt_id=5,
        language_id=1,
        source="legacy",
        overall_level="A2",
        overall_calculation_method="bottleneck",
        completed_at=datetime(2025, 2, 3, tzinfo=timezone.utc),
        skills=[
            PlacementHistorySkillOut(skill=skill.value, score_percent=55.0, level="A2")
            for skill in LanguageSkill
        ],
    )


@pytest.mark.asyncio
async def test_history_api_uses_authenticated_owner_and_one_assessment_snapshot(
    api_client,
    asgi_app,
    monkeypatch,
):
    captured: dict[str, object] = {}

    async def auth_override():
        return AuthContext(user=SimpleNamespace(id=7, role=UserRole.student))

    async def db_override():
        yield SimpleNamespace()

    async def fake_history(db, *, student_id: int, limit: int = 20):
        captured.update(db=db, student_id=student_id, limit=limit)
        return [_legacy_snapshot()]

    monkeypatch.setattr(language_student, "list_placement_history", fake_history)
    asgi_app.dependency_overrides[get_auth_context] = auth_override
    asgi_app.dependency_overrides[get_db] = db_override
    try:
        response = await api_client.get(
            "/api/student/languages/placement-history?student_id=999"
        )
    finally:
        asgi_app.dependency_overrides.pop(get_auth_context, None)
        asgi_app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert captured["student_id"] == 7
    payload = response.json()
    assert payload["available"] is True
    assert payload["results"][0]["assessment_id"] == 11
    assert payload["results"][0]["record_id"] == "legacy:11"
    assert payload["results"][0]["source"] == "legacy"
    assert {row["skill"] for row in payload["results"][0]["skills"]} == {
        skill.value for skill in LanguageSkill
    }


@pytest.mark.integration
@pytest.mark.postgresql
async def test_history_api_reads_one_owned_assessment_without_mixing_live_analytics(
    api_client,
    asgi_app,
    postgres_session_factory,
):
    marker = datetime.now(timezone.utc).strftime("%H%M%S%f")
    completed_at = datetime(2025, 6, 15, 12, 30, tzinfo=timezone.utc)
    async with postgres_session_factory() as db:
        owner = User(
            email=f"history-owner-{marker}@example.test",
            name="History owner",
            hashed_password="not-used",
            role=UserRole.student,
        )
        other = User(
            email=f"history-other-{marker}@example.test",
            name="Other student",
            hashed_password="not-used",
            role=UserRole.student,
        )
        language = Language(
            code=f"h{marker[-12:]}",
            name_en="History test language",
            name_ar="History test language",
            is_active=True,
        )
        db.add_all([owner, other, language])
        await db.flush()

        attempts = [
            LanguagePlacementAttempt(
                student_id=student.id,
                language_id=language.id,
                status=LanguagePlacementAttemptStatus.submitted,
                submitted_at=completed_at,
            )
            for student in (owner, other)
        ]
        db.add_all(attempts)
        await db.flush()
        assessments = [
            LanguageAssessment(
                student_id=student.id,
                language_id=language.id,
                attempt_id=attempt.id,
                overall_level=level,
                overall_calculation_method="bottleneck",
                completed_at=completed_at,
            )
            for student, attempt, level in (
                (owner, attempts[0], LanguageLevel.B1),
                (other, attempts[1], LanguageLevel.C2),
            )
        ]
        db.add_all(assessments)
        await db.flush()
        for assessment, level, base_score in (
            (assessments[0], LanguageLevel.B1, 41.0),
            (assessments[1], LanguageLevel.C2, 91.0),
        ):
            db.add_all(
                [
                    LanguageAssessmentSkillScore(
                        assessment_id=assessment.id,
                        skill=skill,
                        score_percent=base_score + index,
                        level=level,
                    )
                    for index, skill in enumerate(LanguageSkill)
                ]
            )
        # Deliberately conflicting live analytics must not leak into the immutable assessment.
        db.add(
            LanguageAnalytics(
                student_id=owner.id,
                language_id=language.id,
                reading_level=LanguageLevel.C2,
                listening_level=LanguageLevel.C2,
                writing_level=LanguageLevel.C2,
                speaking_level=LanguageLevel.C2,
                overall_level_internal=LanguageLevel.C2,
            )
        )
        await db.commit()
        owner_id, other_id, language_id = owner.id, other.id, language.id
        assessment_ids = [assessment.id for assessment in assessments]
        attempt_ids = [attempt.id for attempt in attempts]

    async def auth_override():
        return AuthContext(user=SimpleNamespace(id=owner_id, role=UserRole.student))

    async def db_override():
        async with postgres_session_factory() as db:
            yield db

    asgi_app.dependency_overrides[get_auth_context] = auth_override
    asgi_app.dependency_overrides[get_db] = db_override
    try:
        response = await api_client.get(
            f"/api/student/languages/placement-history?student_id={other_id}"
        )
    finally:
        asgi_app.dependency_overrides.pop(get_auth_context, None)
        asgi_app.dependency_overrides.pop(get_db, None)

    try:
        assert response.status_code == 200
        payload = response.json()
        assert payload["available"] is True
        assert len(payload["results"]) == 1
        result = payload["results"][0]
        assert result["assessment_id"] == assessment_ids[0]
        assert result["source"] == "legacy"
        assert result["overall_level"] == "B1"
        assert result["completed_at"].startswith("2025-06-15T12:30:00")
        assert [row["score_percent"] for row in result["skills"]] == [41.0, 42.0, 43.0, 44.0]
        assert {row["level"] for row in result["skills"]} == {"B1"}
    finally:
        async with postgres_session_factory() as db:
            await db.execute(
                delete(LanguageAnalytics).where(
                    LanguageAnalytics.student_id.in_([owner_id, other_id])
                )
            )
            await db.execute(
                delete(LanguageAssessmentSkillScore).where(
                    LanguageAssessmentSkillScore.assessment_id.in_(assessment_ids)
                )
            )
            await db.execute(
                delete(LanguageAssessment).where(LanguageAssessment.id.in_(assessment_ids))
            )
            await db.execute(
                delete(LanguagePlacementAttempt).where(
                    LanguagePlacementAttempt.id.in_(attempt_ids)
                )
            )
            await db.execute(delete(User).where(User.id.in_([owner_id, other_id])))
            await db.execute(delete(Language).where(Language.id == language_id))
            await db.commit()


def test_history_serializer_declines_partial_or_duplicate_assessments():
    def score(skill):
        return SimpleNamespace(skill=skill, score_percent=60.0, level=LanguageLevel.B1)

    assessment = SimpleNamespace(
        id=1,
        attempt_id=2,
        language_id=3,
        overall_level=LanguageLevel.B1,
        overall_calculation_method="bottleneck",
        completed_at=datetime.now(timezone.utc),
        skill_scores=[score(skill) for skill in LanguageSkill],
    )
    coherent = coherent_legacy_assessment(assessment)
    assert coherent is not None
    assert coherent.overall_level == "B1"
    assert [row.skill for row in coherent.skills] == [skill.value for skill in LanguageSkill]

    assessment.skill_scores.pop()
    assert coherent_legacy_assessment(assessment) is None

    assessment.skill_scores.append(score(LanguageSkill.writing))
    assert coherent_legacy_assessment(assessment) is None


def test_ai_history_serializer_uses_only_one_completed_session_report():
    report = {
        "overall_level": "B1",
        "reading_level": "B2",
        "listening_level": "B1",
        "writing_level": "B1",
        "speaking_level": "A2",
        "reading_score_percent": 78.0,
        "listening_score_percent": 65.0,
        "writing_score": 6.4,
        "speaking_score": 4.8,
        "unassessed_components": ["speaking.pronunciation"],
    }
    session = SimpleNamespace(
        id="abc123",
        language_id=1,
        status="completed",
        is_completed=True,
        completed_at=datetime.now(timezone.utc),
        assessment_report=report,
        exam_state={"version": 3},
    )

    snapshot = coherent_ai_exam_session(session)

    assert snapshot is not None
    assert snapshot.record_id == "ai_exam:abc123"
    assert snapshot.source == "ai_exam"
    assert snapshot.overall_calculation_method == "ai_exam_v3"
    assert snapshot.assessment_id is None
    assert {row.skill: row.score_percent for row in snapshot.skills} == {
        "reading": 78.0,
        "listening": 65.0,
        "writing": 64.0,
        "speaking": 48.0,
    }

    session.status = "failed"
    assert coherent_ai_exam_session(session) is None
