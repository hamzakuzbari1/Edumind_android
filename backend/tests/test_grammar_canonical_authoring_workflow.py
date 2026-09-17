from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app import models as _models  # noqa: F401
from app.db.base import Base
from app.models.language.grammar_canonical_lesson import (
    GrammarCanonicalLesson,
    GrammarCanonicalLessonRevision,
)
from app.models.user import User
from app.services.language_grammar_canonical_authoring import (
    CanonicalAuthoringAdapterRequest,
    CanonicalAuthoringAdapterResult,
    CanonicalLessonIdentityInput,
    FixtureCanonicalAuthoringAdapter,
    GrammarCanonicalAuthoringWorkflowError,
    archive_canonical_revision,
    ensure_identity,
    generate_draft_revision,
    inspect_revision,
    list_canonical_revisions,
    publish_revision,
    retry_failed_revision,
    validate_revision,
)
from app.services.language_grammar_canonical_authoring.artifacts import write_student_safe_review_html_artifact
from app.services.language_grammar_canonical_authoring.validation import validate_persisted_revision_payload
from app.services.language_grammar_canonical_lessons import (
    GrammarCanonicalRevisionStatus,
    create_next_draft_revision,
    get_active_published_revision_by_lesson_id,
    mark_revision_generating,
    mark_revision_reviewable,
    mark_revision_validating,
    store_or_update_draft_content,
)
from test_grammar_lesson_authoring_contract import _valid_lesson

IDENTITY = CanonicalLessonIdentityInput(
    grammar_id="gram_present_simple",
    cefr_level="A2",
    locale="ar-SY",
)


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


class FailingAdapter:
    def generate(self, request: CanonicalAuthoringAdapterRequest) -> CanonicalAuthoringAdapterResult:
        return CanonicalAuthoringAdapterResult(
            success=False,
            provider_id="fake",
            authoring_model="fake-model",
            diagnostics_json={"code": "provider_failed", "message": "fixture failure"},
        )


class ExplodingAdapter:
    def generate(self, request: CanonicalAuthoringAdapterRequest) -> CanonicalAuthoringAdapterResult:
        raise RuntimeError("network disabled in test")


def run(coro):
    return asyncio.run(coro)


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", future=True)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(connection, _connection_record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            GrammarCanonicalLesson.__table__,
            GrammarCanonicalLessonRevision.__table__,
        ],
    )
    Session = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with Session() as session:
        yield AsyncSessionAdapter(session)


def valid_fixture() -> dict:
    return _valid_lesson()


def invalid_generic_fixture() -> dict:
    fixture = _valid_lesson()
    fixture["student_content"]["orientation"]["teacher_script"] = "Welcome! Today we focus on Present Simple."
    fixture["student_content"]["model_examples"][0]["sentence"] = "I use Present Simple in a short sentence."
    return fixture


def invalid_private_leak_fixture() -> dict:
    fixture = _valid_lesson()
    fixture["student_content"]["guided_practice"][0]["expected_answer"] = "They play."
    return fixture


def invalid_progression_fixture() -> dict:
    fixture = _valid_lesson()
    fixture["student_content"]["guided_practice"][0]["type"] = "production"
    fixture["student_content"]["guided_practice"][0]["scaffold"] = "I usually ..."
    return fixture


def create_identity(db):
    return run(ensure_identity(db, IDENTITY))


def load_revision(db, revision_id: str):
    return db.sync_session.get(GrammarCanonicalLessonRevision, uuid.UUID(revision_id))


def test_identity_workflow_create_reuse_and_rejects_invalid_inputs(db):
    first = run(ensure_identity(db, IDENTITY))
    second = run(ensure_identity(db, IDENTITY))

    assert first.data["created"] is True
    assert second.data["created"] is False
    assert first.data["canonical_lesson_id"] == second.data["canonical_lesson_id"]

    with pytest.raises(GrammarCanonicalAuthoringWorkflowError, match="invalid_grammar_target"):
        run(ensure_identity(db, CanonicalLessonIdentityInput("gram_not_real", "A2", "ar-SY")))
    with pytest.raises(GrammarCanonicalAuthoringWorkflowError, match="invalid_cefr_level"):
        run(ensure_identity(db, CanonicalLessonIdentityInput("gram_present_simple", "Z9", "ar-SY")))
    with pytest.raises(GrammarCanonicalAuthoringWorkflowError, match="invalid_locale"):
        run(ensure_identity(db, CanonicalLessonIdentityInput("gram_present_simple", "A2", "fr-FR")))


def test_generate_draft_success_creates_reviewable_revision_without_publishing(db, tmp_path):
    result = run(
        generate_draft_revision(
            db,
            identity=IDENTITY,
            adapter=FixtureCanonicalAuthoringAdapter(valid_fixture()),
            artifact_dir=tmp_path,
        )
    )
    revision = load_revision(db, result.data["revision_id"])

    assert result.ok is True
    assert revision.status == GrammarCanonicalRevisionStatus.REVIEWABLE.value
    assert revision.content_hash
    assert revision.raw_artifact_ref
    assert revision.authoring_provider == "fixture"
    assert run(get_active_published_revision_by_lesson_id(db, lesson_id=revision.lesson_id)) is None


def test_generate_draft_parser_validator_and_provider_failures_create_failed_revisions(db, tmp_path):
    parser_result = run(
        generate_draft_revision(
            db,
            identity=IDENTITY,
            adapter=FixtureCanonicalAuthoringAdapter({"success": True, "raw_response_text": "{not json"}),
            artifact_dir=tmp_path,
        )
    )
    validator_result = run(
        generate_draft_revision(
            db,
            identity=IDENTITY,
            adapter=FixtureCanonicalAuthoringAdapter(invalid_generic_fixture()),
            artifact_dir=tmp_path,
        )
    )
    provider_result = run(generate_draft_revision(db, identity=IDENTITY, adapter=FailingAdapter(), artifact_dir=tmp_path))
    exception_result = run(generate_draft_revision(db, identity=IDENTITY, adapter=ExplodingAdapter(), artifact_dir=tmp_path))

    for result in (parser_result, validator_result, provider_result, exception_result):
        revision = load_revision(db, result.data["revision_id"])
        assert result.ok is False
        assert revision.status == GrammarCanonicalRevisionStatus.FAILED.value
        assert revision.content_hash is None

    assert load_revision(db, validator_result.data["revision_id"]).diagnostics_json["code"] == "generic_filler_detected"


def test_validate_command_promotes_valid_draft_and_fails_bad_content(db):
    identity = create_identity(db)
    lesson = db.sync_session.get(GrammarCanonicalLesson, uuid.UUID(identity.data["canonical_lesson_id"]))
    good = run(create_next_draft_revision(db, lesson_id=lesson.id))
    good.student_content_json = valid_fixture()["student_content"]
    good.server_teaching_metadata_json = valid_fixture()["server_teaching_metadata"]
    good.schema_version = "grammar_lesson_authoring_v2"
    good.created_at = good.updated_at = datetime.now(timezone.utc)
    db.sync_session.flush()

    result = run(validate_revision(db, revision_id=good.id))
    assert result.ok is True
    assert good.status == GrammarCanonicalRevisionStatus.REVIEWABLE.value
    assert good.content_hash

    bad = run(create_next_draft_revision(db, lesson_id=lesson.id))
    bad.student_content_json = invalid_private_leak_fixture()["student_content"]
    bad.server_teaching_metadata_json = invalid_private_leak_fixture()["server_teaching_metadata"]
    bad.schema_version = "grammar_lesson_authoring_v2"
    db.sync_session.flush()
    failed = run(validate_revision(db, revision_id=bad.id))
    assert failed.ok is False
    assert bad.status == GrammarCanonicalRevisionStatus.FAILED.value
    assert bad.diagnostics_json["code"] == "server_metadata_exposed"

    progression = run(create_next_draft_revision(db, lesson_id=lesson.id))
    progression.student_content_json = invalid_progression_fixture()["student_content"]
    progression.server_teaching_metadata_json = invalid_progression_fixture()["server_teaching_metadata"]
    progression.schema_version = "grammar_lesson_authoring_v2"
    db.sync_session.flush()
    failed_progression = run(validate_revision(db, revision_id=progression.id))
    assert failed_progression.ok is False
    assert progression.diagnostics_json["code"] == "invalid_practice_progression"


def test_published_validation_is_read_only(db):
    generated = run(generate_draft_revision(db, identity=IDENTITY, adapter=FixtureCanonicalAuthoringAdapter(valid_fixture())))
    published = run(publish_revision(db, revision_id=uuid.UUID(generated.data["revision_id"])))
    revision = load_revision(db, published.data["published_revision_id"])
    before_status = revision.status
    before_diagnostics = dict(revision.diagnostics_json or {})

    checked = run(validate_revision(db, revision_id=revision.id))

    assert checked.ok is True
    assert revision.status == before_status
    assert dict(revision.diagnostics_json or {}) == before_diagnostics


def test_inspection_is_student_safe_and_can_write_review_artifact(db, tmp_path):
    generated = run(generate_draft_revision(db, identity=IDENTITY, adapter=FixtureCanonicalAuthoringAdapter(valid_fixture())))
    result = run(
        inspect_revision(
            db,
            revision_id=uuid.UUID(generated.data["revision_id"]),
            write_artifact=True,
            write_html_artifact=True,
            artifact_dir=tmp_path,
        )
    )
    blob = json.dumps(result.data, ensure_ascii=True, sort_keys=True)

    assert "learner_sections" in result.data
    assert "expected_answer" not in blob
    assert "sample_answer" not in blob
    assert "feedback_reasoning" not in blob
    assert "server_teaching_metadata" not in blob
    assert "raw_response_text" not in blob
    assert "review_artifact_ref" in result.data
    assert "review_html_artifact_ref" in result.data


def test_html_review_artifact_uses_student_safe_labels(tmp_path):
    path = write_student_safe_review_html_artifact(
        revision_id="review-1",
        base_dir=tmp_path,
        inspection={
            "canonical_identity": {
                "grammar_id": "gram_be_present",
                "display_name": "Present of be",
                "cefr_level": "A2",
                "locale": "ar-SY",
            },
            "revision": {"revision_number": 1, "status": "reviewable", "content_hash": "hash"},
            "learner_sections": {
                "understand": {},
                "see_how_it_works": {
                    "model_examples": [
                        {
                            "id": "ex_1",
                            "sentence": "She is ready.",
                            "target_form": "affirmative_is",
                            "arabic_explanation": "\u0646\u0633\u062a\u062e\u062f\u0645 is \u0645\u0639 she.",
                        }
                    ]
                },
                "rules_and_mistakes": {},
                "guided_practice": {},
                "use_it_yourself": {},
            },
        },
    )
    html = open(path, encoding="utf-8").read()

    assert "Present of be" in html
    assert "gram_be_present" not in html
    assert "affirmative_is" not in html
    assert ">is</" in html
    assert "ex_1" not in html


def test_publish_rules_archive_previous_and_reject_repeated_or_failed_publish(db):
    first = run(generate_draft_revision(db, identity=IDENTITY, adapter=FixtureCanonicalAuthoringAdapter(valid_fixture())))
    second = run(generate_draft_revision(db, identity=IDENTITY, adapter=FixtureCanonicalAuthoringAdapter(valid_fixture())))

    first_pub = run(publish_revision(db, revision_id=uuid.UUID(first.data["revision_id"])))
    second_pub = run(publish_revision(db, revision_id=uuid.UUID(second.data["revision_id"])))
    first_revision = load_revision(db, first_pub.data["published_revision_id"])
    second_revision = load_revision(db, second_pub.data["published_revision_id"])

    assert first_revision.status == GrammarCanonicalRevisionStatus.ARCHIVED.value
    assert second_revision.status == GrammarCanonicalRevisionStatus.PUBLISHED.value
    assert second_pub.data["previous_revision_archived"] == str(first_revision.id)

    with pytest.raises(GrammarCanonicalAuthoringWorkflowError, match="revision_not_publishable"):
        run(publish_revision(db, revision_id=second_revision.id))

    failed = run(generate_draft_revision(db, identity=IDENTITY, adapter=FailingAdapter()))
    with pytest.raises(GrammarCanonicalAuthoringWorkflowError, match="revision_not_publishable"):
        run(publish_revision(db, revision_id=uuid.UUID(failed.data["revision_id"])))


def test_archive_and_list_commands(db):
    generated = run(generate_draft_revision(db, identity=IDENTITY, adapter=FixtureCanonicalAuthoringAdapter(valid_fixture())))
    archived = run(archive_canonical_revision(db, revision_id=uuid.UUID(generated.data["revision_id"])))
    listed = run(list_canonical_revisions(db, grammar_id="gram_present_simple", status="archived"))

    assert archived.ok is True
    assert archived.data["status"] == "archived"
    assert len(listed.data["revisions"]) == 1
    assert listed.data["revisions"][0]["revision_id"] == generated.data["revision_id"]


def test_retry_preserves_failed_revision_and_creates_new_revision_number(db):
    failed = run(generate_draft_revision(db, identity=IDENTITY, adapter=FailingAdapter()))
    failed_revision = load_revision(db, failed.data["revision_id"])
    retry = run(retry_failed_revision(db, revision_id=failed_revision.id))
    new_revision = load_revision(db, retry.data["new_revision_id"])

    assert failed_revision.status == GrammarCanonicalRevisionStatus.FAILED.value
    assert failed_revision.diagnostics_json
    assert new_revision.status == GrammarCanonicalRevisionStatus.DRAFT.value
    assert new_revision.revision_number == failed_revision.revision_number + 1


def test_cli_parser_requires_explicit_generation_adapter():
    from scripts.grammar_canonical_lessons import build_parser

    parser = build_parser()
    args = parser.parse_args(["identity", "--grammar-id", "gram_present_simple", "--cefr-level", "A2"])
    assert args.command == "identity"

    with pytest.raises(SystemExit):
        parser.parse_args(["generate-draft", "--grammar-id", "gram_present_simple", "--cefr-level", "A2"])
