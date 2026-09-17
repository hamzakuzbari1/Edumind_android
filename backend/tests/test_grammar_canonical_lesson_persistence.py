from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app import models as _models  # noqa: F401 - ensure relationship targets are registered
from app.db.base import Base
from app.models.language.grammar_canonical_lesson import (
    GrammarCanonicalLesson,
    GrammarCanonicalLessonRevision,
)
from app.models.language.grammar_integrity import GrammarActivitySession
from app.models.user import User, UserRole
from app.schemas.language_grammar_student import GrammarLessonOut
from app.services.language_grammar_canonical_lessons import (
    GrammarCanonicalLessonError,
    GrammarCanonicalRevisionStatus,
    archive_revision,
    create_next_draft_revision,
    get_active_published_revision_by_identity,
    get_or_create_canonical_lesson,
    list_revisions_for_canonical_lesson,
    mark_revision_failed,
    mark_revision_generating,
    mark_revision_reviewable,
    mark_revision_status,
    mark_revision_validating,
    publish_reviewable_revision,
    store_or_update_draft_content,
)
from app.services.language_grammar_canonical_lessons.hashing import compute_canonical_lesson_content_hash

METHODOLOGY_VERSION = "grammar_lesson_methodology_v2_arabic_first"
SCHEMA_VERSION = "grammar_lesson_schema_v2"
STUDENT_CONTENT = {
    "sections": [{"id": "orientation", "arabic": "شرح عربي واضح للقاعدة."}],
}
SERVER_METADATA = {
    "items": [{"item_id": "practice_1", "expected_answer": "has lived"}],
}


class AsyncSessionAdapter:
    def __init__(self, sync_session):
        self.sync_session = sync_session

    def add(self, row):
        self.sync_session.add(row)

    async def flush(self):
        self.sync_session.flush()

    async def execute(self, statement):
        return self.sync_session.execute(statement)

    async def get(self, model, ident):
        return self.sync_session.get(model, ident)


def run(coro):
    return asyncio.run(coro)


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", future=True)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(connection, _connection_record):
        connection.execute("PRAGMA foreign_keys=ON")

    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE media_objects (id INTEGER PRIMARY KEY)"))
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            GrammarCanonicalLesson.__table__,
            GrammarCanonicalLessonRevision.__table__,
            GrammarActivitySession.__table__,
        ],
    )
    Session = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with Session() as session:
        yield AsyncSessionAdapter(session)


def create_user(db, user_id: int = 1) -> User:
    user = User(
        id=user_id,
        email=f"student{user_id}@example.com",
        name="Student",
        hashed_password="hash",
        role=UserRole.student,
    )
    db.sync_session.add(user)
    db.sync_session.flush()
    return user


def create_lesson(db, *, grammar_id: str = "gram_present_perfect", cefr: str = "B1", locale: str = "ar-SY"):
    return run(
        get_or_create_canonical_lesson(
            db,
            grammar_id=grammar_id,
            cefr_level=cefr,
            locale=locale,
            methodology_version=METHODOLOGY_VERSION,
        )
    )


def make_reviewable(db, revision):
    run(mark_revision_generating(db, revision_id=revision.id))
    run(
        store_or_update_draft_content(
            db,
            revision_id=revision.id,
            student_content_json=STUDENT_CONTENT,
            server_teaching_metadata_json=SERVER_METADATA,
            schema_version=SCHEMA_VERSION,
            prompt_version="prompt.v1",
            catalog_version="catalog.v1",
            authoring_provider="anthropic",
            authoring_model="claude",
            raw_artifact_ref="private-artifact-ref",
        )
    )
    run(mark_revision_validating(db, revision_id=revision.id))
    return run(mark_revision_reviewable(db, revision_id=revision.id))


def test_canonical_lesson_identity_uniqueness_and_distinct_dimensions(db):
    first = create_lesson(db)
    same = create_lesson(db)
    other_cefr = create_lesson(db, cefr="B2")
    other_locale = create_lesson(db, locale="en-US")

    assert first.id == same.id
    assert len({first.id, other_cefr.id, other_locale.id}) == 3

    duplicate = GrammarCanonicalLesson(
        id=uuid.uuid4(),
        grammar_id=first.grammar_id,
        cefr_level=first.cefr_level,
        locale=first.locale,
        methodology_version=first.methodology_version,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.sync_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db.sync_session.flush()


def test_revision_numbering_and_multiple_drafts(db):
    lesson = create_lesson(db)
    first = run(create_next_draft_revision(db, lesson_id=lesson.id))
    second = run(create_next_draft_revision(db, lesson_id=lesson.id))

    assert first.revision_number == 1
    assert second.revision_number == 2
    assert first.status == GrammarCanonicalRevisionStatus.DRAFT.value
    assert second.status == GrammarCanonicalRevisionStatus.DRAFT.value
    assert [r.id for r in run(list_revisions_for_canonical_lesson(db, lesson_id=lesson.id))] == [
        first.id,
        second.id,
    ]

    duplicate = GrammarCanonicalLessonRevision(
        lesson_id=lesson.id,
        revision_number=2,
        status="draft",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.sync_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db.sync_session.flush()


def test_state_transitions_and_invalid_publish_sources(db):
    lesson = create_lesson(db)
    draft = run(create_next_draft_revision(db, lesson_id=lesson.id))

    with pytest.raises(GrammarCanonicalLessonError, match="invalid_revision_transition"):
        run(mark_revision_status(db, revision_id=draft.id, status=GrammarCanonicalRevisionStatus.PUBLISHED))

    run(mark_revision_generating(db, revision_id=draft.id))
    run(mark_revision_failed(db, revision_id=draft.id, diagnostics_json={"code": "provider_failed"}))
    with pytest.raises(GrammarCanonicalLessonError, match="revision_not_publishable"):
        run(publish_reviewable_revision(db, lesson_id=lesson.id, revision_id=draft.id))

    archived = run(create_next_draft_revision(db, lesson_id=lesson.id))
    make_reviewable(db, archived)
    run(archive_revision(db, revision_id=archived.id))
    with pytest.raises(GrammarCanonicalLessonError, match="revision_not_publishable"):
        run(publish_reviewable_revision(db, lesson_id=lesson.id, revision_id=archived.id))


def test_publish_archives_previous_revision_and_keeps_one_published(db):
    lesson = create_lesson(db)
    first = run(create_next_draft_revision(db, lesson_id=lesson.id))
    make_reviewable(db, first)
    published_first = run(publish_reviewable_revision(db, lesson_id=lesson.id, revision_id=first.id))

    second = run(create_next_draft_revision(db, lesson_id=lesson.id))
    make_reviewable(db, second)
    published_second = run(publish_reviewable_revision(db, lesson_id=lesson.id, revision_id=second.id))

    assert published_first.status == GrammarCanonicalRevisionStatus.ARCHIVED.value
    assert published_first.archived_at is not None
    assert published_second.status == GrammarCanonicalRevisionStatus.PUBLISHED.value
    assert published_second.published_at is not None

    revisions = run(list_revisions_for_canonical_lesson(db, lesson_id=lesson.id))
    assert [revision.status for revision in revisions].count(GrammarCanonicalRevisionStatus.PUBLISHED.value) == 1


def test_different_lessons_can_each_have_one_published_revision(db):
    first_lesson = create_lesson(db, grammar_id="gram_present_perfect")
    second_lesson = create_lesson(db, grammar_id="gram_third_conditional", cefr="B2")
    first_revision = run(create_next_draft_revision(db, lesson_id=first_lesson.id))
    second_revision = run(create_next_draft_revision(db, lesson_id=second_lesson.id))

    make_reviewable(db, first_revision)
    make_reviewable(db, second_revision)

    assert run(publish_reviewable_revision(db, lesson_id=first_lesson.id, revision_id=first_revision.id)).status == "published"
    assert run(publish_reviewable_revision(db, lesson_id=second_lesson.id, revision_id=second_revision.id)).status == "published"


def test_publish_requires_reviewable_hash_and_matching_lesson(db):
    lesson = create_lesson(db)
    other_lesson = create_lesson(db, grammar_id="gram_third_conditional", cefr="B2")
    draft = run(create_next_draft_revision(db, lesson_id=lesson.id))

    with pytest.raises(GrammarCanonicalLessonError, match="revision_lesson_mismatch"):
        run(publish_reviewable_revision(db, lesson_id=other_lesson.id, revision_id=draft.id))

    reviewable = run(create_next_draft_revision(db, lesson_id=lesson.id))
    run(mark_revision_generating(db, revision_id=reviewable.id))
    run(mark_revision_validating(db, revision_id=reviewable.id))
    with pytest.raises(GrammarCanonicalLessonError, match="missing_student_content"):
        run(mark_revision_reviewable(db, revision_id=reviewable.id))

    manually_reviewable = GrammarCanonicalLessonRevision(
        lesson_id=lesson.id,
        revision_number=99,
        status=GrammarCanonicalRevisionStatus.REVIEWABLE.value,
        student_content_json=STUDENT_CONTENT,
        server_teaching_metadata_json=SERVER_METADATA,
        schema_version=SCHEMA_VERSION,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.sync_session.add(manually_reviewable)
    db.sync_session.flush()
    with pytest.raises(GrammarCanonicalLessonError, match="missing_content_hash"):
        run(publish_reviewable_revision(db, lesson_id=lesson.id, revision_id=manually_reviewable.id))


def test_published_content_is_immutable_but_new_revision_is_allowed(db):
    lesson = create_lesson(db)
    revision = run(create_next_draft_revision(db, lesson_id=lesson.id))
    make_reviewable(db, revision)
    run(publish_reviewable_revision(db, lesson_id=lesson.id, revision_id=revision.id))

    with pytest.raises(GrammarCanonicalLessonError, match="revision_content_immutable"):
        run(
            store_or_update_draft_content(
                db,
                revision_id=revision.id,
                student_content_json={"sections": []},
                server_teaching_metadata_json=SERVER_METADATA,
                schema_version=SCHEMA_VERSION,
            )
        )

    new_revision = run(create_next_draft_revision(db, lesson_id=lesson.id))
    assert new_revision.revision_number == 2


def test_active_published_revision_by_identity(db):
    lesson = create_lesson(db)
    revision = run(create_next_draft_revision(db, lesson_id=lesson.id))
    make_reviewable(db, revision)
    run(publish_reviewable_revision(db, lesson_id=lesson.id, revision_id=revision.id))

    active = run(
        get_active_published_revision_by_identity(
            db,
            grammar_id=lesson.grammar_id,
            cefr_level=lesson.cefr_level,
            locale=lesson.locale,
            methodology_version=lesson.methodology_version,
        )
    )
    assert active is not None
    assert active.id == revision.id


def test_content_hash_is_stable_and_methodology_sensitive():
    first = compute_canonical_lesson_content_hash(
        student_content_json=STUDENT_CONTENT,
        server_teaching_metadata_json=SERVER_METADATA,
        schema_version=SCHEMA_VERSION,
        methodology_version=METHODOLOGY_VERSION,
    )
    reordered = compute_canonical_lesson_content_hash(
        student_content_json={"sections": [{"arabic": "شرح عربي واضح للقاعدة.", "id": "orientation"}]},
        server_teaching_metadata_json={"items": [{"expected_answer": "has lived", "item_id": "practice_1"}]},
        schema_version=SCHEMA_VERSION,
        methodology_version=METHODOLOGY_VERSION,
    )
    changed_methodology = compute_canonical_lesson_content_hash(
        student_content_json=STUDENT_CONTENT,
        server_teaching_metadata_json=SERVER_METADATA,
        schema_version=SCHEMA_VERSION,
        methodology_version="grammar_lesson_methodology_v1",
    )

    assert first == reordered
    assert first != changed_methodology


def test_session_pin_nullable_and_fk_safe(db):
    create_user(db)
    lesson = create_lesson(db)
    revision = run(create_next_draft_revision(db, lesson_id=lesson.id))

    existing_session = GrammarActivitySession(
        student_id=1,
        language_id=1,
        grammar_id=lesson.grammar_id,
        skill="grammar_lesson",
        activity_type="lesson",
        lesson_id="legacy",
        stamp_token="stamp",
        server_payload_json={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    pinned_session = GrammarActivitySession(
        student_id=1,
        language_id=1,
        grammar_id=lesson.grammar_id,
        skill="grammar_lesson",
        activity_type="lesson",
        lesson_id="canonical",
        published_revision_id=revision.id,
        stamp_token="stamp",
        server_payload_json={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.sync_session.add_all([existing_session, pinned_session])
    db.sync_session.flush()

    assert existing_session.published_revision_id is None
    assert pinned_session.published_revision_id == revision.id
    assert pinned_session.published_revision.id == revision.id

    db.sync_session.delete(revision)
    db.sync_session.flush()
    db.sync_session.refresh(pinned_session)
    assert pinned_session.published_revision_id is None


def test_model_constraints_and_partial_published_index_are_declared():
    lesson_constraints = {constraint.name for constraint in GrammarCanonicalLesson.__table__.constraints}
    revision_constraints = {constraint.name for constraint in GrammarCanonicalLessonRevision.__table__.constraints}
    revision_indexes = {index.name: index for index in GrammarCanonicalLessonRevision.__table__.indexes}

    assert "uq_grammar_canonical_lessons_identity" in lesson_constraints
    assert "uq_grammar_canonical_lesson_revisions_number" in revision_constraints
    assert "ck_grammar_canonical_lesson_revisions_status" in revision_constraints
    published_index = revision_indexes["uq_grammar_canonical_lesson_revisions_one_published"]
    assert published_index.unique is True
    assert str(published_index.dialect_options["postgresql"]["where"]) == "status = 'published'"


def test_student_schema_does_not_expose_private_revision_fields():
    private_fields = {
        "server_teaching_metadata_json",
        "server_teaching_metadata",
        "diagnostics_json",
        "raw_artifact_ref",
        "approved_by_user_id",
        "expected_answer",
        "sample_answer",
        "feedback_reasoning",
        "content_hash",
    }
    assert private_fields.isdisjoint(set(GrammarLessonOut.model_fields))
