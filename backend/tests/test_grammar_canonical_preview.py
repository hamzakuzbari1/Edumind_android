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
from app.services.language_grammar_activity_authoring.llm.lesson_schema import (
    CANONICAL_LESSON_SCHEMA_VERSION,
    METHODOLOGY_VERSION,
)
from app.services.language_grammar_canonical_authoring.preview import (
    GrammarCanonicalPreviewError,
    build_canonical_lesson_start_package,
    build_canonical_revision_preview_lesson,
)
from app.services.language_grammar_canonical_authoring.practice_evaluation import (
    GrammarPracticeEvaluationError,
    evaluate_canonical_revision_preview_practice,
    evaluate_canonical_revision_student_practice,
)
from app.services.language_grammar_canonical_authoring.validation import validate_raw_authoring_output
from app.services.language_grammar_canonical_lessons.hashing import compute_canonical_lesson_content_hash
from test_grammar_lesson_authoring_contract import _metadata, _valid_lesson
from test_grammar_canonical_sectioned_authoring import rich_be_practice_payload


class AsyncSessionAdapter:
    def __init__(self, sync_session):
        self.sync_session = sync_session

    async def get(self, model, ident):
        return self.sync_session.get(model, ident)

    async def execute(self, statement):
        return self.sync_session.execute(statement)


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


def _persist_revision(
    db,
    *,
    status: str = "reviewable",
    fixture: dict | None = None,
    lesson: GrammarCanonicalLesson | None = None,
    revision_number: int = 1,
    grammar_id: str = "gram_present_simple",
):
    fixture = fixture or _valid_lesson()
    now = datetime.now(timezone.utc)
    if lesson is None:
        lesson = GrammarCanonicalLesson(
            id=uuid.uuid4(),
            grammar_id=grammar_id,
            cefr_level="A2",
            locale="ar-SY",
            methodology_version=METHODOLOGY_VERSION,
            created_at=now,
            updated_at=now,
        )
        db.sync_session.add(lesson)
    validation = validate_raw_authoring_output(fixture, lesson=lesson)
    student_content = fixture["student_content"]
    server_metadata = fixture["server_teaching_metadata"]
    if validation.valid:
        student_content = validation.normalized_student_content or student_content
        server_metadata = validation.normalized_server_teaching_metadata or server_metadata
        content_hash = validation.content_hash
    else:
        content_hash = compute_canonical_lesson_content_hash(
            student_content_json=student_content,
            server_teaching_metadata_json=server_metadata,
            schema_version=CANONICAL_LESSON_SCHEMA_VERSION,
            methodology_version=METHODOLOGY_VERSION,
        )
    revision = GrammarCanonicalLessonRevision(
        id=uuid.uuid4(),
        lesson_id=lesson.id,
        revision_number=revision_number,
        status=status,
        student_content_json=student_content,
        server_teaching_metadata_json=server_metadata,
        schema_version=CANONICAL_LESSON_SCHEMA_VERSION,
        content_hash=content_hash,
        prompt_version="test.prompt",
        catalog_version="test.catalog",
        authoring_provider="fixture",
        authoring_model="fixture-model",
        created_at=now,
        updated_at=now,
        reviewed_at=now if status == "reviewable" else None,
    )
    db.sync_session.add(revision)
    db.sync_session.flush()
    return lesson, revision


def _valid_be_rich_practice_lesson() -> dict:
    practice_public, practice_private = rich_be_practice_payload()
    arabic_intro = (
        "بالعربي نقدر نقول أنا طالب بدون فعل ظاهر بين أنا وطالب. "
        "لكن بالإنجليزي الجملة تحتاج فعل واضح يربط الشخص بالهوية أو المكان أو الحالة، وهذا الفعل هو be. "
        "لذلك لا نقول I student، بل نقول I am a student. "
        "الفكرة المهمة أن شكل be يتغير حسب الفاعل: I am، وhe/she/it is، وyou/we/they are. "
        "وعند النفي نضع not بعد be، وعند السؤال نحرك am/is/are قبل الفاعل."
    )
    student = {
        "orientation": {"teacher_script": "نبدأ بفكرة be في الحاضر من المعنى."},
        "meaning_hook": {
            "situation": "You introduce yourself and ask if a friend is ready.",
            "why_it_matters": "Present be helps you say who someone is, where they are, and how they feel.",
        },
        "model_examples": [
            {
                "id": "ex_1",
                "sentence": "I am a student.",
                "teaching_purpose": "identity",
                "target_form": "am",
                "arabic_meaning": "أنا طالب.",
                "arabic_explanation": "استخدمنا am لأن الفاعل هو I.",
            },
            {
                "id": "ex_2",
                "sentence": "She is tired.",
                "teaching_purpose": "state",
                "target_form": "is",
                "arabic_meaning": "هي متعبة.",
                "arabic_explanation": "استخدمنا is لأن الفاعل she يأخذ is.",
            },
            {
                "id": "ex_3",
                "sentence": "They are at home.",
                "teaching_purpose": "location",
                "target_form": "are",
                "arabic_meaning": "هم في البيت.",
                "arabic_explanation": "استخدمنا are لأن الفاعل they يأخذ are.",
            },
            {
                "id": "ex_4",
                "sentence": "Are you ready?",
                "teaching_purpose": "question",
                "target_form": "Are",
                "arabic_meaning": "هل أنت جاهز؟",
                "arabic_explanation": "في السؤال نضع are قبل الفاعل you.",
            },
        ],
        "noticing": {
            "id": "notice_1",
            "prompt": "ما الكلمة التي تتغير حسب الفاعل؟",
            "expected_observations": ["am/is/are تتغير حسب الفاعل."],
        },
        "concept_explanation": {
            "arabic_concept_introduction": arabic_intro,
            "english_bridge": "Use be to connect the subject with identity, place, or state.",
            "summary": "Choose am, is, or are from the subject first.",
        },
        "form_and_rules": {
            "patterns": [
                {"id": "pat_1", "pattern": "I + am", "meaning": "identity/state", "explanation": "مع I نستخدم am.", "example": "I am ready."},
                {"id": "pat_2", "pattern": "he/she/it + is", "meaning": "one person or thing", "explanation": "مع he/she/it نستخدم is.", "example": "She is ready."},
                {"id": "pat_3", "pattern": "you/we/they + are", "meaning": "you or plural", "explanation": "مع you/we/they نستخدم are.", "example": "They are ready."},
                {"id": "pat_4", "pattern": "be + subject?", "meaning": "yes/no question", "explanation": "في السؤال نحرك be قبل الفاعل.", "example": "Are you ready?"},
            ],
            "rule_notes": ["لا تحذف be.", "ضع not بعد be في النفي.", "ابدأ السؤال بـ am/is/are."],
            "use_cases": [
                {"id": "use_1", "label": "Identity", "explanation": "Say who someone is.", "example": "I am a student.", "arabic_explanation": "نربط I بالهوية student."},
                {"id": "use_2", "label": "Location", "explanation": "Say where someone is.", "example": "We are at home.", "arabic_explanation": "نربط we بالمكان at home."},
                {"id": "use_3", "label": "State", "explanation": "Say how someone feels.", "example": "She is tired.", "arabic_explanation": "نربط she بالحالة tired."},
            ],
            "visual_summary": [
                {"label": "I", "value": "am", "warning": None},
                {"label": "He / She / It", "value": "is", "warning": None},
                {"label": "You / We / They", "value": "are", "warning": None},
            ],
        },
        "arabic_clarification": {
            "arabic": arabic_intro,
            "arabic_speaker_warning": "لا تحذف am/is/are كما يحدث أحيانا عند التفكير بالعربي.",
            "arabic_english_contrast": "العربية قد تكمل المعنى بدون فعل ظاهر، لكن الإنجليزية تحتاج be في هذه الجمل.",
        },
        "contrasts_and_mistakes": [
            {"id": "mistake_1", "incorrect": "I student.", "correct": "I am a student.", "why": "الإنجليزية تحتاج am مع I، ولا يكفي وضع الاسم مباشرة.", "misunderstanding": "نقل تركيب أنا طالب من العربية إلى الإنجليزية."},
            {"id": "mistake_2", "incorrect": "She are tired.", "correct": "She is tired.", "why": "She تأخذ is وليس are.", "misunderstanding": "اختيار شكل be بدون النظر إلى الفاعل."},
            {"id": "mistake_3", "incorrect": "Do you are ready?", "correct": "Are you ready?", "why": "مع be لا نستخدم do في السؤال، بل نبدأ بـ are.", "misunderstanding": "خلط سؤال be مع أسئلة الأفعال العادية."},
        ],
        "understanding_checks": practice_public["understanding_checks"],
        "guided_practice": practice_public["guided_practice"],
        "supported_production": [
            {"id": "produce_1", "type": "production", "prompt": "اكتب ثلاث جمل قصيرة: من أنت؟ أين أنت؟ كيف تشعر؟", "scaffold": "I am ..."}
        ],
        "transfer": {
            "id": "transfer_1",
            "type": "transfer",
            "context": "A short message to a new classmate",
            "prompt": "Write a short introduction with identity, place, and feeling.",
        },
        "exit_check": {
            "recognition": {"id": "exit_recognition", "type": "choice", "prompt": "اختر الصحيح.", "options": ["She is ready.", "She are ready."]},
            "correction": {"id": "exit_correction", "type": "correction", "prompt": "صحح الجملة.", "incorrect_sentence": "I at home."},
            "production": {"id": "exit_production", "type": "production", "prompt": "اكتب جملة واحدة عن نفسك باستخدام am.", "scaffold": "I am ..."},
        },
        "reflection": {
            "summary": "تدربت على am/is/are في الهوية والمكان والحالة.",
            "encouragement": "اختيار be يبدأ من الفاعل.",
            "next_step": "اكتب جملة واحدة عن حالتك اليوم.",
        },
    }
    metadata = {
        **practice_private,
        "noticing": [_metadata("notice_1")],
        "supported_production": [{"item_id": "produce_1", "sample_answer": "I am a student. I am at home. I am happy.", "success_criteria": ["Uses present be."]}],
        "transfer": [{"item_id": "transfer_1", "sample_answer": "I am a student. I am in class. I am ready.", "success_criteria": ["Transfers present be to introduction."]}],
        "exit_check": [
            _metadata("exit_recognition", "She is ready."),
            _metadata("exit_correction", "I am at home."),
            {"item_id": "exit_production", "sample_answer": "I am ready.", "success_criteria": ["Uses am with I."]},
        ],
    }
    return {"student_content": student, "server_teaching_metadata": metadata}


def test_preview_projects_reviewable_revision_without_private_metadata(db):
    _lesson, revision = _persist_revision(db)

    preview = run(build_canonical_revision_preview_lesson(db, revision_id=revision.id))
    dumped = json.dumps(preview, ensure_ascii=False)

    assert preview["lesson_id"] == "canonical-review-preview"
    assert preview["generation_mode"] == "llm_canonical_grammar_lesson_authoring"
    assert preview["authoring_status"] == "ready"
    assert preview["methodology_version"] == METHODOLOGY_VERSION
    assert preview["lesson_schema_version"] == CANONICAL_LESSON_SCHEMA_VERSION
    assert preview["revision_id"] == str(revision.id)
    assert preview["canonical_revision_id"] == str(revision.id)
    assert preview["display_name"] == "Present simple"
    assert preview["activity_session_id"] == ""
    assert "student_content" in preview
    assert "server_teaching_metadata" not in preview
    for private_key in (
        "expected_answer",
        "sample_answer",
        "hint",
        "feedback_reasoning",
        "success_criteria",
        "similar_retry_prompt",
        "validation_metadata",
    ):
        assert private_key not in dumped


def test_preview_rejects_non_reviewable_revision(db):
    _lesson, revision = _persist_revision(db, status="draft")

    with pytest.raises(GrammarCanonicalPreviewError) as exc:
        run(build_canonical_revision_preview_lesson(db, revision_id=revision.id))

    assert exc.value.code == "revision_not_reviewable"


def test_preview_rejects_private_student_content(db):
    fixture = _valid_lesson()
    fixture["student_content"]["guided_practice"][0]["expected_answer"] = "They work every day."
    _lesson, revision = _persist_revision(db, fixture=fixture)

    with pytest.raises(GrammarCanonicalPreviewError) as exc:
        run(build_canonical_revision_preview_lesson(db, revision_id=revision.id))

    assert exc.value.code == "revision_payload_invalid"


def _evaluate(db, revision_id, item_id, response, attempt_number=1):
    return run(
        evaluate_canonical_revision_preview_practice(
            db,
            revision_id=revision_id,
            item_id=item_id,
            learner_response=response,
            attempt_number=attempt_number,
        )
    )


def _evaluate_student(db, revision_id, item_id, response, attempt_number=1, allow_reviewable=False):
    return run(
        evaluate_canonical_revision_student_practice(
            db,
            revision_id=revision_id,
            item_id=item_id,
            learner_response=response,
            attempt_number=attempt_number,
            allow_reviewable=allow_reviewable,
        )
    )


def test_preview_practice_correct_choice_is_accepted_without_private_metadata(db):
    _lesson, revision = _persist_revision(db)

    result = _evaluate(db, revision.id, "check_1", "She works.")
    payload = result.to_dict()
    dumped = json.dumps(payload, ensure_ascii=False)

    assert payload == {
        "correct": True,
        "feedback": "صحيح. اخترت الشكل المناسب للجملة.",
        "hint": None,
        "may_continue": True,
        "attempt_number": 1,
    }
    for private_key in (
        "expected_answer",
        "sample_answer",
        "success_criteria",
        "feedback_reasoning",
        "similar_retry_prompt",
        "validation_metadata",
    ):
        assert private_key not in dumped


def test_preview_practice_recognition_accepts_concise_observation(db):
    _lesson, revision = _persist_revision(db)

    result = _evaluate(db, revision.id, "notice_1", "adds s")

    assert result.correct is True
    assert result.may_continue is True


def test_student_practice_evaluates_published_revision_without_private_metadata(db):
    _lesson, revision = _persist_revision(db, status="published")

    result = _evaluate_student(db, revision.id, "check_1", "She works.").to_dict()
    dumped = json.dumps(result, ensure_ascii=False)

    assert result["correct"] is True
    assert result["may_continue"] is True
    for private_key in (
        "expected_answer",
        "sample_answer",
        "success_criteria",
        "feedback_reasoning",
        "similar_retry_prompt",
        "validation_metadata",
    ):
        assert private_key not in dumped


def test_student_practice_reviewable_revision_requires_explicit_dev_allowance(db):
    _lesson, revision = _persist_revision(db, status="reviewable")

    with pytest.raises(GrammarPracticeEvaluationError) as blocked:
        _evaluate_student(db, revision.id, "check_1", "She works.")
    allowed = _evaluate_student(db, revision.id, "check_1", "She works.", allow_reviewable=True)

    assert blocked.value.code == "revision_not_available"
    assert allowed.correct is True
    assert allowed.may_continue is True


def test_preview_practice_wrong_choice_gets_hint_then_second_attempt_reveals_answer(db):
    _lesson, revision = _persist_revision(db)

    first = _evaluate(db, revision.id, "check_1", "She work.", attempt_number=1).to_dict()
    second = _evaluate(db, revision.id, "check_1", "She work.", attempt_number=2).to_dict()

    assert first["correct"] is False
    assert first["may_continue"] is False
    assert first["hint"]
    assert "She works." not in first["feedback"]
    assert second["correct"] is False
    assert second["may_continue"] is True
    assert second["hint"] is None
    assert "She works" in second["feedback"]


def test_preview_practice_fill_blank_normalization(db):
    _lesson, revision = _persist_revision(db)

    result = _evaluate(db, revision.id, "check_2", "  Drinks.  ")

    assert result.correct is True
    assert result.may_continue is True


def test_preview_practice_reorder_preserves_word_order(db):
    _lesson, revision = _persist_revision(db)

    correct = _evaluate(db, revision.id, "practice_4", ["She", "works", "today"])
    wrong = _evaluate(db, revision.id, "practice_4", ["works", "She", "today"])

    assert correct.correct is True
    assert wrong.correct is False


def test_preview_practice_correction_requires_complete_sentence(db):
    _lesson, revision = _persist_revision(db)

    correct = _evaluate(db, revision.id, "practice_3", "He goes to school.")
    partial = _evaluate(db, revision.id, "practice_3", "goes")

    assert correct.correct is True
    assert partial.correct is False


def test_preview_rich_practice_evaluates_all_task_types_without_private_metadata(db):
    _lesson, revision = _persist_revision(db, fixture=_valid_be_rich_practice_lesson(), grammar_id="gram_be_present")
    preview = run(build_canonical_revision_preview_lesson(db, revision_id=revision.id))
    tasks = [*preview["student_content"]["understanding_checks"], *preview["student_content"]["guided_practice"]]

    assert len(tasks) == 14
    assert [task["type"] for task in preview["student_content"]["understanding_checks"]] == ["multiple_choice"] * 3

    cases = {
        "practice_mc_1": "am",
        "practice_blank_1": "is",
        "practice_build_1": ["She", "is", "a", "nurse"],
        "practice_transform_1": "They are not ready.",
        "practice_correct_2": "Are you ready?",
        "practice_short_1": "Yes, I am.",
        "practice_open_1": "I am a student. I am at home. I am happy today.",
    }
    for item_id, answer in cases.items():
        payload = _evaluate(db, revision.id, item_id, answer).to_dict()
        dumped = json.dumps(payload, ensure_ascii=False)
        assert payload["correct"] is True
        assert payload["may_continue"] is True
        for private_key in (
            "expected_answer",
            "sample_answer",
            "success_criteria",
            "feedback_reasoning",
            "validation_metadata",
        ):
            assert private_key not in dumped


def test_start_package_prefers_published_revision_without_private_metadata(db):
    _lesson, revision = _persist_revision(db, status="published")

    package = run(
        build_canonical_lesson_start_package(
            db,
            grammar_id="gram_present_simple",
            cefr_level="A2",
            locale="ar-SY",
        )
    )
    dumped = json.dumps(package, ensure_ascii=False)

    assert package is not None
    assert package["lesson_id"] == f"canonical-{revision.id}"
    assert package["revision_id"] == str(revision.id)
    assert package["canonical_revision_id"] == str(revision.id)
    assert package["generation_mode"] == "published_canonical_grammar_lesson"
    assert package["authoring_status"] == "ready"
    assert "server_teaching_metadata" not in package
    for private_key in (
        "expected_answer",
        "sample_answer",
        "hint",
        "feedback_reasoning",
        "success_criteria",
        "similar_retry_prompt",
        "validation_metadata",
    ):
        assert private_key not in dumped


def test_start_package_uses_reviewable_only_when_allowed(db):
    _lesson, revision = _persist_revision(db, status="reviewable")

    blocked = run(
        build_canonical_lesson_start_package(
            db,
            grammar_id="gram_present_simple",
            cefr_level="A2",
            locale="ar-SY",
        )
    )
    allowed = run(
        build_canonical_lesson_start_package(
            db,
            grammar_id="gram_present_simple",
            cefr_level="A2",
            locale="ar-SY",
            allow_reviewable=True,
        )
    )

    assert blocked is None
    assert allowed is not None
    assert allowed["lesson_id"] == f"canonical-{revision.id}"
    assert allowed["revision_id"] == str(revision.id)
    assert allowed["generation_mode"] == "reviewable_canonical_grammar_lesson"


def test_start_package_can_use_same_grammar_cefr_fallback_when_allowed(db):
    _lesson, revision = _persist_revision(db, status="reviewable")

    blocked = run(
        build_canonical_lesson_start_package(
            db,
            grammar_id="gram_present_simple",
            cefr_level="A1",
            locale="ar-SY",
            allow_reviewable=True,
        )
    )
    allowed = run(
        build_canonical_lesson_start_package(
            db,
            grammar_id="gram_present_simple",
            cefr_level="A1",
            locale="ar-SY",
            allow_reviewable=True,
            allow_cefr_fallback=True,
        )
    )

    assert blocked is None
    assert allowed is not None
    assert allowed["lesson_id"] == f"canonical-{revision.id}"
    assert allowed["cefr_level"] == "A2"


def test_preview_open_response_hint_then_second_attempt_model(db):
    _lesson, revision = _persist_revision(db, fixture=_valid_be_rich_practice_lesson(), grammar_id="gram_be_present")

    first = _evaluate(db, revision.id, "practice_open_1", "I happy.", attempt_number=1).to_dict()
    second = _evaluate(db, revision.id, "practice_open_1", "I happy.", attempt_number=2).to_dict()

    assert first["correct"] is False
    assert first["may_continue"] is False
    assert first["hint"]
    assert "I am a student" not in first["feedback"]
    assert second["correct"] is False
    assert second["may_continue"] is True
    assert second["hint"] is None
    assert "I am a student" in second["feedback"]


def test_preview_practice_unknown_or_other_revision_task_is_rejected(db):
    first_fixture = _valid_lesson()
    lesson, first_revision = _persist_revision(db, fixture=first_fixture)
    other_fixture = _valid_lesson()
    other_fixture["student_content"]["understanding_checks"][0]["id"] = "other_check"
    other_fixture["server_teaching_metadata"]["understanding_checks"][0]["item_id"] = "other_check"
    _other_lesson, other_revision = _persist_revision(
        db,
        fixture=other_fixture,
        lesson=lesson,
        revision_number=2,
    )

    with pytest.raises(GrammarPracticeEvaluationError) as unknown:
        _evaluate(db, first_revision.id, "missing_task", "anything")
    with pytest.raises(GrammarPracticeEvaluationError) as other_revision_task:
        _evaluate(db, other_revision.id, "check_1", "She works.")

    assert unknown.value.code == "unknown_task_id"
    assert other_revision_task.value.code == "unknown_task_id"


def test_preview_practice_evaluation_does_not_create_progress_or_completion_writes(db):
    _lesson, revision = _persist_revision(db)
    revisions_before = db.sync_session.query(GrammarCanonicalLessonRevision).count()
    lessons_before = db.sync_session.query(GrammarCanonicalLesson).count()

    result = _evaluate(db, revision.id, "practice_1", "They play.")

    assert result.correct is True
    assert db.sync_session.query(GrammarCanonicalLessonRevision).count() == revisions_before
    assert db.sync_session.query(GrammarCanonicalLesson).count() == lessons_before
