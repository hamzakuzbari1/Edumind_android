from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app import models as _models  # noqa: F401
from app.db.base import Base
from app.models.language.grammar_canonical_lesson import (
    GrammarCanonicalLesson,
    GrammarCanonicalLessonRevision,
    GrammarCanonicalLessonRevisionUnitAttempt,
)
from app.models.user import User
from app.services.language_grammar_canonical_authoring import (
    CanonicalAuthoringAdapterRequest,
    CanonicalLessonIdentityInput,
    ExistingLLMSectionedCanonicalAuthoringAdapter,
    FixtureSectionedCanonicalAuthoringAdapter,
)
from app.services.language_grammar_canonical_authoring.blueprint_compaction import (
    deterministic_blueprint_stable_ids,
    normalize_compact_blueprint_plan,
    validate_compact_blueprint_plan,
)
from app.services.language_grammar_canonical_authoring.section_assembly import (
    assemble_canonical_lesson_from_units,
)
from app.services.language_grammar_canonical_authoring.section_prompts import (
    build_sectioned_prompt_bundle,
)
from app.services.language_grammar_practice_contract import (
    RICH_PRACTICE_REQUIRED_TOTAL,
    rich_practice_ids_for_grammar,
)
from app.services.language_grammar_canonical_authoring.section_validation import (
    validate_blueprint_unit,
    validate_concept_unit,
    validate_examples_unit,
    validate_practice_unit,
    validate_production_unit,
    validate_rules_unit,
)
from app.services.language_grammar_canonical_authoring.sectioned_workflow import (
    assemble_sectioned_revision,
    generate_sectioned_draft_revision,
    inspect_unit_attempt,
    list_revision_unit_attempts,
    retry_unit_attempt,
)
from app.services.language_grammar_canonical_authoring.unit_repository import (
    accept_unit_attempt,
    create_next_unit_attempt,
    get_accepted_unit_attempt,
    list_unit_attempts,
    supersede_accepted_unit_attempt,
)
from app.services.language_grammar_canonical_authoring.workflow import ensure_identity
from app.services.language_grammar_canonical_lessons import (
    GrammarCanonicalRevisionStatus,
    create_next_draft_revision,
    get_active_published_revision_by_lesson_id,
)
from app.services.language_grammar_pipeline.stages import _grammar_authoring_profile
from test_grammar_lesson_authoring_contract import _valid_lesson

IDENTITY = CanonicalLessonIdentityInput("gram_present_simple", "A2", "ar-SY")
BE_IDENTITY = CanonicalLessonIdentityInput(
    "gram_be_present",
    "A2",
    "ar-SY",
    "grammar_lesson_methodology_v2_arabic_first",
)


def _adapter_request() -> CanonicalAuthoringAdapterRequest:
    return CanonicalAuthoringAdapterRequest(
        grammar_id="gram_present_simple",
        display_name="Present Simple",
        cefr_level="A2",
        locale="ar-SY",
        methodology_version="grammar_lesson_methodology_v2_arabic_first",
        grammar_profile={
            "display_name": "Present Simple",
            "learning_objectives": ["Use present simple for routines"],
            "canonical_patterns": ["base verb", "verb-s"],
            "model_examples": ["I work every day.", "She works every day."],
            "common_mistakes": ["She work every day."],
            "support_grammar_targets": [],
        },
        learner_signals={"synthetic": True},
    )


def _be_profile() -> dict:
    return {
        "display_name": "Present of be",
        "learning_objectives": ["Use am/is/are for identity, location, and basic description"],
        "canonical_patterns": ["I am / I am not", "he/she/it is / is not", "you/we/they are / are not"],
        "required_form_keys": [
            "affirmative_am",
            "affirmative_is",
            "affirmative_are",
            "negative_am_not",
            "negative_is_not",
            "negative_are_not",
            "question_am",
            "question_is",
            "question_are",
            "short_answer_am",
            "short_answer_is",
            "short_answer_are",
        ],
        "permitted_realizations": ["am", "is", "are", "am not", "isn't", "aren't", "Are you ...?", "Yes, I am."],
        "functions": ["identity", "description/state", "location", "negative meaning", "yes/no question", "short answer"],
        "mistake_categories": ["be_deletion", "wrong_be_agreement", "missing_not", "statement_order_question", "do_does_with_be", "incomplete_short_answer"],
        "forbidden_extensions": ["past_be_was_were", "future_be", "present_perfect", "present_continuous", "modal_verbs", "detailed_wh_questions"],
        "model_examples": ["I am a student.", "She is at school.", "They are ready."],
        "common_mistakes": ["He are tired.", "Omitting be: She my friend."],
        "support_grammar_targets": [],
    }


def _be_form_teaching_notes() -> dict[str, str]:
    return {
        "affirmative_am": "Use with I in affirmative present be.",
        "affirmative_is": "Use with he, she, it, or singular nouns.",
        "affirmative_are": "Use with you, we, they, or plural nouns.",
        "negative_am_not": "Use am not to make I negative.",
        "negative_is_not": "Use is not or isn't after singular subjects.",
        "negative_are_not": "Use are not or aren't after plural subjects.",
        "question_am": "Move am before I in yes/no questions.",
        "question_is": "Move is before singular subjects in questions.",
        "question_are": "Move are before you, we, they, or plurals.",
        "short_answer_am": "Repeat am in short answers with I.",
        "short_answer_is": "Repeat is in short answers with singular subjects.",
        "short_answer_are": "Repeat are in short answers with plural subjects.",
    }


def _compact_be_plan() -> dict:
    return {
        "core_meaning": "Express identity, location, or description with be.",
        "english_need": "English requires a visible be verb between subject and meaning.",
        "arabic_contrast": "بالعربي ممكن نقول أنا طالب بدون فعل ظاهر، لكن الإنجليزية تحتاج am/is/are.",
        "form_teaching_notes": _be_form_teaching_notes(),
        "use_case_intents": [
            {"label": "identity", "meaning": "say who someone is"},
            {"label": "location", "meaning": "say where someone is"},
            {"label": "description", "meaning": "say how someone feels"},
        ],
        "example_intents": [
            {"meaning": "speaker identifies self"},
            {"meaning": "one person feels something"},
            {"meaning": "several people are in a place"},
        ],
        "mistake_intents": [
            {"error_type": "be_deletion", "misunderstanding": "Arabic meaning feels complete without visible be."},
            {"error_type": "wrong_be_agreement", "misunderstanding": "Learner chooses are with she or is with I."},
            {"error_type": "missing_not", "misunderstanding": "Learner forgets not when making be negative."},
            {"error_type": "statement_order_question", "misunderstanding": "Learner keeps statement order in yes/no questions."},
            {"error_type": "do_does_with_be", "misunderstanding": "Learner adds do or does before present be."},
            {"error_type": "incomplete_short_answer", "misunderstanding": "Learner answers yes or no without repeating be."},
        ],
        "practice_plan": ["recognition", "choice", "fill_blank", "reorder", "correction"],
        "production_goal": "Learner says who they are, where they are, and how they feel.",
        "cefr_language_guidance": "Arabic-first, simple terms, short English examples.",
        "single_appearance_topics": ["Arabic omission contrast", "subject agreement forms"],
    }


def test_present_be_official_profile_includes_expanded_scope():
    profile = _grammar_authoring_profile(("gram_be_present",))
    required = set(profile["required_form_keys"])

    assert {
        "affirmative_am",
        "affirmative_is",
        "affirmative_are",
        "negative_am_not",
        "negative_is_not",
        "negative_are_not",
        "question_am",
        "question_is",
        "question_are",
        "short_answer_am",
        "short_answer_is",
        "short_answer_are",
    }.issubset(required)
    assert {"identity", "description/state", "location", "negative meaning", "yes/no question", "short answer"}.issubset(
        set(profile["functions"])
    )
    assert {"isn't", "aren't", "Are you/we/they ...?", "Yes, I am."}.issubset(set(profile["permitted_realizations"]))
    assert {"be_deletion", "wrong_be_agreement", "do_does_with_be", "incomplete_short_answer"}.issubset(
        set(profile["mistake_categories"])
    )
    assert {"past_be_was_were", "future_be", "present_continuous", "detailed_wh_questions"}.issubset(
        set(profile["forbidden_extensions"])
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
            GrammarCanonicalLessonRevisionUnitAttempt.__table__,
        ],
    )
    Session = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with Session() as session:
        yield AsyncSessionAdapter(session)


def create_lesson_and_revision(db):
    identity = run(ensure_identity(db, IDENTITY))
    lesson = db.sync_session.get(GrammarCanonicalLesson, uuid.UUID(identity.data["canonical_lesson_id"]))
    revision = run(create_next_draft_revision(db, lesson_id=lesson.id))
    return lesson, revision


def blueprint() -> dict:
    return {
        "grammar_target": "gram_present_simple",
        "display_name": "Present Simple",
        "cefr_level": "A2",
        "locale": "ar-SY",
        "teaching_language_behavior": "Arabic-first with short English examples",
        "core_communicative_meaning": "Talk about habits and general facts.",
        "why_english_uses_it": "English marks repeated meaning and third-person agreement in the verb form.",
        "required_forms": ["base verb", "verb-s"],
        "subject_trigger_relationships": ["I/you/we/they -> base verb", "he/she/it -> verb-s"],
        "main_use_cases": ["habits", "facts"],
        "arabic_english_contrast": "بالعربي قد يكون التغيير أقل وضوحا، لكن الإنجليزية تطلب s مع he/she/it.",
        "likely_arabic_speaker_mistakes": ["She wake up early.", "I wakes up early."],
        "support_grammar_targets": [],
        "example_intentions": ["habit", "third person", "negative"],
        "mistake_intentions": ["missing -s", "overusing -s"],
        "practice_progression_plan": ["choice", "fill_blank", "reorder", "correction"],
        "production_goal": "Describe a real weekly routine.",
        "terminology_limits": "Use simple words: habit, fact, subject.",
        "stable_ids": {
            "examples": ["ex_1", "ex_2", "ex_3"],
            "noticing": "notice_1",
            "patterns": ["pat_1", "pat_2"],
            "use_cases": ["use_1", "use_2"],
            "mistakes": ["mistake_1", "mistake_2"],
            "understanding_checks": ["check_1", "check_2"],
            "guided_practice": ["practice_1", "practice_2", "practice_3", "practice_4"],
            "supported_production": ["produce_1"],
            "transfer": ["transfer_1"],
            "exit_check": {
                "recognition": "exit_recognition",
                "correction": "exit_correction",
                "production": "exit_production",
            },
        },
        "duplication_avoidance": ["Explain meaning in concept only", "Put forms in rules only"],
        "content_once": ["Arabic-English contrast", "third-person -s warning"],
        "cross_section_consistency": ["All practice uses habit/fact meaning"],
    }


def sectioned_fixture(*, bad_unit: str = "", changed_example: bool = False) -> dict:
    canonical = _valid_lesson()
    student = canonical["student_content"]
    metadata = canonical["server_teaching_metadata"]
    examples = list(student["model_examples"])
    if changed_example:
        examples[0] = dict(examples[0])
        examples[0]["sentence"] = "I study every evening."
        examples[0]["target_form"] = "study"
    units = {
        "blueprint": {"blueprint": blueprint()},
        "concept": {
            "public_payload": {
                "orientation": student["orientation"],
                "meaning_hook": student["meaning_hook"],
                "concept_explanation": student["concept_explanation"],
                "arabic_clarification": student["arabic_clarification"],
            }
        },
        "examples": {
            "public_payload": {
                "model_examples": examples,
                "noticing": student["noticing"],
                "use_cases": student["form_and_rules"]["use_cases"],
            },
            "private_metadata": {"noticing": metadata["noticing"]},
        },
        "rules": {
            "public_payload": {
                "patterns": student["form_and_rules"]["patterns"],
                "rule_notes": student["form_and_rules"]["rule_notes"],
                "arabic_english_contrast": student["arabic_clarification"]["arabic_english_contrast"],
                "contrasts_and_mistakes": student["contrasts_and_mistakes"],
                "visual_summary": student["form_and_rules"]["visual_summary"],
            }
        },
        "practice": {
            "public_payload": {
                "understanding_checks": student["understanding_checks"],
                "guided_practice": student["guided_practice"],
            },
            "private_metadata": {
                "understanding_checks": metadata["understanding_checks"],
                "guided_practice": metadata["guided_practice"],
            },
        },
        "production": {
            "public_payload": {
                "supported_production": student["supported_production"],
                "transfer": student["transfer"],
                "exit_check": student["exit_check"],
                "reflection": student["reflection"],
            },
            "private_metadata": {
                "supported_production": metadata["supported_production"],
                "transfer": metadata["transfer"],
                "exit_check": metadata["exit_check"],
            },
        },
    }
    if bad_unit == "concept":
        units["concept"]["public_payload"]["concept_explanation"] = {"arabic_concept_introduction": "Short."}
        units["concept"]["public_payload"]["arabic_clarification"] = {
            "arabic": None,
            "arabic_speaker_warning": None,
            "arabic_english_contrast": None,
        }
    elif bad_unit == "examples":
        units["examples"]["public_payload"]["model_examples"][0]["sentence"] = "I use Present Simple in a sentence."
    elif bad_unit == "rules":
        units["rules"]["public_payload"]["contrasts_and_mistakes"][0]["why"] = "This explanation is not Arabic."
    elif bad_unit == "practice":
        units["practice"]["public_payload"]["guided_practice"] = [
            item for item in units["practice"]["public_payload"]["guided_practice"] if item["type"] != "correction"
        ]
        units["practice"]["private_metadata"]["guided_practice"] = [
            item for item in units["practice"]["private_metadata"]["guided_practice"] if item["item_id"] != "practice_3"
        ]
    elif bad_unit == "production":
        units["production"]["public_payload"]["supported_production"][0]["prompt"] = "Write one sentence using Present Simple."
    return {"units": units}


def rich_be_practice_payload() -> tuple[dict, dict]:
    checks = [
        {"id": "practice_mc_1", "type": "multiple_choice", "round_title": "اختر الصحيح", "prompt": "اختر الشكل الصحيح.", "context": "I ___ a student.", "options": ["am", "is", "are"]},
        {"id": "practice_mc_2", "type": "multiple_choice", "round_title": "اختر الصحيح", "prompt": "اختر النفي الصحيح.", "options": ["We are not late.", "We not late.", "We is not late."]},
        {"id": "practice_mc_3", "type": "multiple_choice", "round_title": "اختر الصحيح", "prompt": "اختر السؤال الصحيح.", "options": ["Are you ready?", "Do you are ready?", "You are ready?"]},
    ]
    guided = [
        {"id": "practice_blank_1", "type": "fill_blank", "round_title": "أكمل الفراغ", "prompt": "أكمل الجملة.", "sentence_with_blank": "She _____ tired."},
        {"id": "practice_blank_2", "type": "fill_blank", "round_title": "أكمل الفراغ", "prompt": "أكمل الجملة.", "sentence_with_blank": "We _____ not late."},
        {"id": "practice_blank_3", "type": "fill_blank", "round_title": "أكمل الفراغ", "prompt": "أكمل السؤال.", "sentence_with_blank": "_____ he at home?"},
        {"id": "practice_build_1", "type": "sentence_builder", "round_title": "ركّب الجملة", "prompt": "ركّب جملة صحيحة.", "word_chips": ["She", "is", "a", "nurse"]},
        {"id": "practice_build_2", "type": "sentence_builder", "round_title": "ركّب الجملة", "prompt": "ركّب سؤالًا صحيحًا.", "word_chips": ["Are", "they", "at", "home"]},
        {"id": "practice_transform_1", "type": "transformation", "round_title": "حوّل الجملة", "prompt": "حوّلها إلى نفي.", "original_sentence": "They are ready.", "transformation_goal": "Make it negative."},
        {"id": "practice_transform_2", "type": "transformation", "round_title": "حوّل الجملة", "prompt": "حوّلها إلى سؤال.", "original_sentence": "She is at school.", "transformation_goal": "Make it a yes/no question."},
        {"id": "practice_correct_1", "type": "correction", "round_title": "صحّح الخطأ", "prompt": "صحّح الجملة.", "incorrect_sentence": "I student."},
        {"id": "practice_correct_2", "type": "correction", "round_title": "صحّح الخطأ", "prompt": "صحّح الجملة.", "incorrect_sentence": "Do you are ready?"},
        {"id": "practice_short_1", "type": "short_answer", "round_title": "جاوب واكتب", "prompt": "أجب بجواب قصير.", "context": "Are you tired today?"},
        {
            "id": "practice_open_1",
            "type": "open_response",
            "round_title": "جاوب واكتب",
            "prompt": "اكتب 2-4 جمل عن من أنت، أين أنت، وكيف تشعر اليوم.",
            "sentence_count_min": 2,
            "sentence_count_max": 4,
            "starters": ["I am ...", "I am at ...", "I am ... today."],
        },
    ]
    metadata = {
        "understanding_checks": [
            {"item_id": "practice_mc_1", "expected_answer": "am", "hint": "انظر إلى I.", "feedback_reasoning": "I تأخذ am."},
            {"item_id": "practice_mc_2", "expected_answer": "We are not late.", "hint": "النفي يحتاج not بعد are.", "feedback_reasoning": "مع we نستخدم are ثم not."},
            {"item_id": "practice_mc_3", "expected_answer": "Are you ready?", "hint": "ابدأ بـ are في السؤال.", "feedback_reasoning": "السؤال يبدأ بـ are قبل you."},
        ],
        "guided_practice": [
            {"item_id": "practice_blank_1", "expected_answer": "is", "hint": "She تأخذ is.", "feedback_reasoning": "She تأخذ is."},
            {"item_id": "practice_blank_2", "expected_answer": "are", "hint": "We تأخذ are.", "feedback_reasoning": "We تأخذ are."},
            {"item_id": "practice_blank_3", "expected_answer": "Is", "hint": "ابدأ بـ is مع he.", "feedback_reasoning": "في السؤال نضع is قبل he."},
            {"item_id": "practice_build_1", "expected_answer": "She is a nurse.", "hint": "ابدأ بالفاعل ثم is.", "feedback_reasoning": "She تأخذ is."},
            {"item_id": "practice_build_2", "expected_answer": "Are they at home?", "hint": "السؤال يبدأ بـ Are.", "feedback_reasoning": "في السؤال Are تأتي قبل they."},
            {"item_id": "practice_transform_1", "expected_answer": "They are not ready.", "hint": "أضف not بعد are.", "feedback_reasoning": "النفي يكون are not."},
            {"item_id": "practice_transform_2", "expected_answer": "Is she at school?", "hint": "حرّك is قبل she.", "feedback_reasoning": "السؤال يبدأ بـ is."},
            {"item_id": "practice_correct_1", "expected_answer": "I am a student.", "hint": "لا تحذف am.", "feedback_reasoning": "الإنجليزية تحتاج am مع I."},
            {"item_id": "practice_correct_2", "expected_answer": "Are you ready?", "hint": "لا تستخدم do مع be.", "feedback_reasoning": "be لا يأخذ do في السؤال."},
            {"item_id": "practice_short_1", "expected_answer": "Yes, I am. || No, I'm not.", "hint": "كرر am في الجواب القصير.", "feedback_reasoning": "الجواب القصير يكرر be."},
            {
                "item_id": "practice_open_1",
                "sample_answer": "I am a student. I am at home. I am happy today.",
                "success_criteria": ["2-4 sentences", "uses present be", "communicates identity/location/state"],
                "hint": "ابدأ بجمل قصيرة فيها I am.",
            },
        ],
    }
    return {"understanding_checks": checks, "guided_practice": guided}, metadata


def test_unit_attempt_persistence_retry_and_supersede(db):
    _lesson, revision = create_lesson_and_revision(db)
    attempt1 = run(create_next_unit_attempt(db, revision_id=revision.id, unit_key="concept"))
    attempt2 = run(create_next_unit_attempt(db, revision_id=revision.id, unit_key="concept"))

    assert attempt1.attempt_number == 1
    assert attempt2.attempt_number == 2
    assert len(run(list_unit_attempts(db, revision_id=revision.id, unit_key="concept"))) == 2

    run(
        accept_unit_attempt(
            db,
            attempt=attempt1,
            public_payload_json={"meaning_hook": {}},
            private_metadata_json={},
            blueprint_json=None,
            provider="fixture",
            model="fixture",
            prompt_version="test",
        )
    )
    with pytest.raises(IntegrityError):
        run(
            accept_unit_attempt(
                db,
                attempt=attempt2,
                public_payload_json={"meaning_hook": {"changed": True}},
                private_metadata_json={},
                blueprint_json=None,
                provider="fixture",
                model="fixture",
                prompt_version="test",
            )
        )


def test_accepted_attempt_may_be_explicitly_superseded(db):
    _lesson, revision = create_lesson_and_revision(db)
    attempt1 = run(create_next_unit_attempt(db, revision_id=revision.id, unit_key="examples"))
    run(
        accept_unit_attempt(
            db,
            attempt=attempt1,
            public_payload_json={"model_examples": []},
            private_metadata_json={},
            blueprint_json=None,
            provider="fixture",
            model="fixture",
            prompt_version="test",
        )
    )
    run(supersede_accepted_unit_attempt(db, attempt=attempt1))
    attempt2 = run(create_next_unit_attempt(db, revision_id=revision.id, unit_key="examples"))
    run(
        accept_unit_attempt(
            db,
            attempt=attempt2,
            public_payload_json={"model_examples": [{"id": "ex_1"}]},
            private_metadata_json={},
            blueprint_json=None,
            provider="fixture",
            model="fixture",
            prompt_version="test",
        )
    )
    assert attempt1.status == "superseded"
    assert run(get_accepted_unit_attempt(db, revision_id=revision.id, unit_key="examples")).id == attempt2.id


def test_blueprint_validation_accepts_valid_and_rejects_bad_shapes(db):
    lesson, _revision = create_lesson_and_revision(db)
    assert validate_blueprint_unit(blueprint(), lesson=lesson).valid

    wrong_identity = dict(blueprint(), grammar_target="gram_present_perfect")
    assert validate_blueprint_unit(wrong_identity, lesson=lesson).diagnostics_json["code"] == "blueprint_identity_mismatch"

    bad_support = dict(blueprint(), support_grammar_targets=["gram_third_conditional"])
    assert validate_blueprint_unit(bad_support, lesson=lesson).diagnostics_json["code"] == "invalid_support_target"

    dup = blueprint()
    dup["stable_ids"] = dict(dup["stable_ids"])
    dup["stable_ids"]["examples"] = ["ex_1", "ex_1"]
    assert validate_blueprint_unit(dup, lesson=lesson).diagnostics_json["code"] == "duplicate_stable_ids"


def test_compact_blueprint_plan_normalizes_server_owned_fields(db):
    identity = run(ensure_identity(db, BE_IDENTITY))
    lesson = db.sync_session.get(GrammarCanonicalLesson, uuid.UUID(identity.data["canonical_lesson_id"]))
    plan = _compact_be_plan()

    assert validate_compact_blueprint_plan(plan, lesson=lesson, grammar_profile=_be_profile())["status"] == "valid"
    normalized = normalize_compact_blueprint_plan(plan, lesson=lesson, grammar_profile=_be_profile())

    assert normalized["grammar_target"] == "gram_be_present"
    assert normalized["display_name"] == "Present of be"
    assert normalized["cefr_level"] == "A2"
    assert normalized["locale"] == "ar-SY"
    assert normalized["required_forms"] == list(_be_form_teaching_notes().keys())
    assert normalized["stable_ids"] == deterministic_blueprint_stable_ids()
    assert validate_blueprint_unit(normalized, lesson=lesson).valid


def test_compact_blueprint_rejects_echoed_identity_and_injects_server_mistake_categories(db):
    identity = run(ensure_identity(db, BE_IDENTITY))
    lesson = db.sync_session.get(GrammarCanonicalLesson, uuid.UUID(identity.data["canonical_lesson_id"]))

    echoed = dict(_compact_be_plan())
    echoed["grammar_target"] = "gram_be_present"
    assert (
        validate_compact_blueprint_plan(echoed, lesson=lesson, grammar_profile=_be_profile())["code"]
        == "server_owned_blueprint_field_echoed"
    )

    partial_notes = dict(_compact_be_plan())
    partial_notes["mistake_intents"] = [
        {"error_type": "be_deletion", "misunderstanding": "Arabic meaning feels complete without visible be."},
        {"error_type": "wrong_be_agreement", "misunderstanding": "Learner chooses the wrong subject form."},
        {"error_type": "do_does_with_be", "misunderstanding": "Learner adds do or does before be."},
    ]
    normalized = normalize_compact_blueprint_plan(partial_notes, lesson=lesson, grammar_profile=_be_profile())

    assert validate_compact_blueprint_plan(partial_notes, lesson=lesson, grammar_profile=_be_profile())["status"] == "valid"
    assert normalized["mistake_intentions"] == _be_profile()["mistake_categories"]
    assert set(normalized["mistake_teaching_notes"]) == {"be_deletion", "wrong_be_agreement", "do_does_with_be"}

    no_notes = dict(_compact_be_plan())
    no_notes.pop("mistake_intents")
    normalized_without_notes = normalize_compact_blueprint_plan(no_notes, lesson=lesson, grammar_profile=_be_profile())
    assert validate_compact_blueprint_plan(no_notes, lesson=lesson, grammar_profile=_be_profile())["status"] == "valid"
    assert normalized_without_notes["mistake_intentions"] == _be_profile()["mistake_categories"]
    assert normalized_without_notes["mistake_teaching_notes"] == {}


def test_compact_blueprint_rejects_unknown_mistake_category(db):
    identity = run(ensure_identity(db, BE_IDENTITY))
    lesson = db.sync_session.get(GrammarCanonicalLesson, uuid.UUID(identity.data["canonical_lesson_id"]))
    plan = dict(_compact_be_plan())
    plan["mistake_intents"] = [
        {"error_type": "be_deletion", "misunderstanding": "Arabic meaning feels complete without visible be."},
        {"error_type": "past_be_confusion", "misunderstanding": "Learner reaches for was or were."},
    ]

    diagnostics = validate_compact_blueprint_plan(plan, lesson=lesson, grammar_profile=_be_profile())

    assert diagnostics["code"] == "unknown_mistake_category"
    assert "past_be_confusion" in diagnostics["message"]


def test_compact_blueprint_rejects_non_server_form_extension_keys(db):
    identity = run(ensure_identity(db, BE_IDENTITY))
    lesson = db.sync_session.get(GrammarCanonicalLesson, uuid.UUID(identity.data["canonical_lesson_id"]))
    plan = dict(_compact_be_plan())
    plan["form_teaching_notes"] = {
        "am": "Use with I only.",
        "is": "Use with he, she, it, or one person.",
        "are": "Use with you, we, they, or plural subjects.",
        "negative_be": "Teach not after be.",
        "question_be": "Teach be before subject.",
        "short_answer_be": "Teach short answers with be.",
    }

    diagnostics = validate_compact_blueprint_plan(plan, lesson=lesson, grammar_profile=_be_profile())

    assert diagnostics["code"] == "invalid_form_teaching_notes_keys"
    assert "negative_be" in diagnostics["message"]


def test_compact_blueprint_rejects_present_be_forbidden_extensions(db):
    identity = run(ensure_identity(db, BE_IDENTITY))
    lesson = db.sync_session.get(GrammarCanonicalLesson, uuid.UUID(identity.data["canonical_lesson_id"]))
    plan = dict(_compact_be_plan())
    plan["example_intents"] = [{"meaning": "teach was and were for old identity"}]

    diagnostics = validate_compact_blueprint_plan(plan, lesson=lesson, grammar_profile=_be_profile())

    assert diagnostics["code"] == "forbidden_past_be"


def test_present_be_blueprint_rejects_stale_affirmative_only_scope(db):
    identity = run(ensure_identity(db, BE_IDENTITY))
    lesson = db.sync_session.get(GrammarCanonicalLesson, uuid.UUID(identity.data["canonical_lesson_id"]))
    stale = normalize_compact_blueprint_plan(_compact_be_plan(), lesson=lesson, grammar_profile=_be_profile())
    stale["required_forms"] = ["am", "is", "are"]

    diagnostics = validate_blueprint_unit(stale, lesson=lesson).diagnostics_json

    assert diagnostics["code"] == "blueprint_required_forms_mismatch"
    assert "negative_am_not" in diagnostics["message"]


def test_unit_validators_accept_valid_units_and_catch_required_failures(db):
    lesson, _revision = create_lesson_and_revision(db)
    fixture = sectioned_fixture()["units"]
    bp = blueprint()

    assert validate_concept_unit(fixture["concept"]["public_payload"], blueprint=bp, lesson=lesson).valid
    assert validate_examples_unit(fixture["examples"]["public_payload"], fixture["examples"]["private_metadata"], blueprint=bp, lesson=lesson).valid
    assert validate_rules_unit(fixture["rules"]["public_payload"], blueprint=bp, lesson=lesson).valid
    assert validate_practice_unit(fixture["practice"]["public_payload"], fixture["practice"]["private_metadata"], blueprint=bp).valid
    assert validate_production_unit(fixture["production"]["public_payload"], fixture["production"]["private_metadata"], blueprint=bp).valid

    assert validate_concept_unit(sectioned_fixture(bad_unit="concept")["units"]["concept"]["public_payload"], blueprint=bp, lesson=lesson).diagnostics_json["code"] == "concept_not_arabic_first"
    assert validate_examples_unit(sectioned_fixture(bad_unit="examples")["units"]["examples"]["public_payload"], fixture["examples"]["private_metadata"], blueprint=bp, lesson=lesson).diagnostics_json["code"] == "fake_grammar_name_example"
    assert validate_rules_unit(sectioned_fixture(bad_unit="rules")["units"]["rules"]["public_payload"], blueprint=bp, lesson=lesson).diagnostics_json["code"] == "missing_mistake_reason"
    assert validate_practice_unit(sectioned_fixture(bad_unit="practice")["units"]["practice"]["public_payload"], sectioned_fixture(bad_unit="practice")["units"]["practice"]["private_metadata"], blueprint=bp).diagnostics_json["code"] == "incomplete_practice_progression"
    assert validate_production_unit(sectioned_fixture(bad_unit="production")["units"]["production"]["public_payload"], fixture["production"]["private_metadata"], blueprint=bp).diagnostics_json["code"] == "generic_production_prompt"


def test_rich_present_be_practice_contract_validates_all_types_and_separate_options(db):
    identity = run(ensure_identity(db, BE_IDENTITY))
    lesson = db.sync_session.get(GrammarCanonicalLesson, uuid.UUID(identity.data["canonical_lesson_id"]))
    bp = normalize_compact_blueprint_plan(_compact_be_plan(), lesson=lesson, grammar_profile=_be_profile())
    public, private = rich_be_practice_payload()

    result = validate_practice_unit(public, private, blueprint=bp, lesson=lesson)

    assert result.valid
    tasks = [*public["understanding_checks"], *public["guided_practice"]]
    assert len(tasks) == RICH_PRACTICE_REQUIRED_TOTAL
    assert {task["id"] for task in tasks} == set(rich_practice_ids_for_grammar("gram_be_present"))
    assert [task["type"] for task in public["understanding_checks"]] == ["multiple_choice"] * 3

    bad = json.loads(json.dumps(public))
    bad["understanding_checks"][0]["options"] = ["am\nis\nare", "is", "are"]
    rejected = validate_practice_unit(bad, private, blueprint=bp, lesson=lesson)
    assert rejected.diagnostics_json["code"] == "concatenated_choice_options"


def test_rich_present_be_practice_injects_server_owned_open_response_metadata(db):
    identity = run(ensure_identity(db, BE_IDENTITY))
    lesson = db.sync_session.get(GrammarCanonicalLesson, uuid.UUID(identity.data["canonical_lesson_id"]))
    bp = normalize_compact_blueprint_plan(_compact_be_plan(), lesson=lesson, grammar_profile=_be_profile())
    public, private = rich_be_practice_payload()
    private["guided_practice"] = [
        record for record in private["guided_practice"] if record["item_id"] != "practice_open_1"
    ]

    result = validate_practice_unit(public, private, blueprint=bp, lesson=lesson)

    assert result.valid
    metadata_ids = {
        record["item_id"]
        for record in [
            *result.normalized_private_metadata["understanding_checks"],
            *result.normalized_private_metadata["guided_practice"],
        ]
    }
    assert "practice_open_1" in metadata_ids


def test_rich_present_be_practice_still_rejects_missing_closed_task_metadata(db):
    identity = run(ensure_identity(db, BE_IDENTITY))
    lesson = db.sync_session.get(GrammarCanonicalLesson, uuid.UUID(identity.data["canonical_lesson_id"]))
    bp = normalize_compact_blueprint_plan(_compact_be_plan(), lesson=lesson, grammar_profile=_be_profile())
    public, private = rich_be_practice_payload()
    private["guided_practice"] = [
        record for record in private["guided_practice"] if record["item_id"] != "practice_blank_1"
    ]

    result = validate_practice_unit(public, private, blueprint=bp, lesson=lesson)

    assert result.diagnostics_json["code"] == "missing_server_metadata"


def test_concept_validator_rejects_non_arabic_start_and_generic_opening(db):
    lesson, _revision = create_lesson_and_revision(db)
    fixture = sectioned_fixture()["units"]
    bp = blueprint()

    english_first = json.loads(json.dumps(fixture["concept"]["public_payload"]))
    english_first["concept_explanation"]["arabic_concept_introduction"] = "English starts here. " + english_first["concept_explanation"]["arabic_concept_introduction"]
    assert validate_concept_unit(english_first, blueprint=bp, lesson=lesson).diagnostics_json["code"] == "concept_not_arabic_first"

    generic = json.loads(json.dumps(fixture["concept"]["public_payload"]))
    generic["concept_explanation"]["arabic_concept_introduction"] = "مرحبا، اليوم سنتعلم القاعدة. " + generic["concept_explanation"]["arabic_concept_introduction"]
    assert validate_concept_unit(generic, blueprint=bp, lesson=lesson).diagnostics_json["code"] == "generic_filler_detected"

def test_present_be_concept_accepts_declared_negative_questions_and_short_answers(db):
    identity = run(ensure_identity(db, BE_IDENTITY))
    lesson = db.sync_session.get(GrammarCanonicalLesson, uuid.UUID(identity.data["canonical_lesson_id"]))
    bp = normalize_compact_blueprint_plan(_compact_be_plan(), lesson=lesson, grammar_profile=_be_profile())
    payload = {
        "orientation": {"teacher_script": "نبدأ بفكرة be في الحاضر من المعنى."},
        "meaning_hook": {
            "situation": "طالب يعرّف عن نفسه ويسأل صديقه إن كان جاهزا.",
            "why_it_matters": "be يربط الشخص بهويته أو مكانه أو حالته، ويظهر أيضا في النفي والسؤال القصير.",
        },
        "concept_explanation": {
            "arabic_concept_introduction": "بالعربي ممكن نقول أنا طالب بدون فعل ظاهر، لكن بالإنجليزي لا تكفي I student. نحتاج be مثل I am a student، ونستخدم not للنفي، ونقدم be في سؤال نعم/لا، ونكرر be في الجواب القصير.",
            "english_bridge": "Be connects subject to identity, location, state, negative meaning, yes/no questions, and short answers.",
            "summary": "اختَر صيغة be حسب الفاعل والمعنى.",
        },
        "arabic_clarification": {
            "arabic": "لا تحذف am/is/are في الإنجليزية. في السؤال نقول Are you ready? وليس Do you are ready?",
            "arabic_speaker_warning": "انتبه للتطابق: I am، she is، they are، وفي الجواب القصير نكرر نفس الصيغة.",
            "arabic_english_contrast": "العربية قد تستغني عن فعل ظاهر، أما الإنجليزية فتحتاج be في الإثبات والنفي والسؤال القصير.",
        },
    }

    assert validate_concept_unit(payload, blueprint=bp, lesson=lesson).valid


def test_present_be_concept_rejects_forbidden_extensions(db):
    identity = run(ensure_identity(db, BE_IDENTITY))
    lesson = db.sync_session.get(GrammarCanonicalLesson, uuid.UUID(identity.data["canonical_lesson_id"]))
    bp = normalize_compact_blueprint_plan(_compact_be_plan(), lesson=lesson, grammar_profile=_be_profile())
    base = {
        "orientation": {"teacher_script": "نبدأ بفكرة be في الحاضر."},
        "meaning_hook": {"situation": "تعريف بسيط.", "why_it_matters": "be يربط الفاعل بالمعنى."},
        "concept_explanation": {
            "arabic_concept_introduction": "بالعربي ممكن نقول أنا طالب بدون فعل ظاهر، لكن بالإنجليزي نحتاج be مثل I am a student.",
            "english_bridge": "Be connects subject to meaning.",
            "summary": "be في الحاضر فقط.",
        },
        "arabic_clarification": {
            "arabic": "لا نحذف be في الجملة الإنجليزية.",
            "arabic_speaker_warning": "انتبه للتطابق بين الفاعل و be.",
            "arabic_english_contrast": "العربية قد تخفي الفعل، أما الإنجليزية تحتاج be.",
        },
    }
    cases = [
        ("was and were are past be.", "past_be_scope_creep"),
        ("will be is future be.", "future_be_scope_creep"),
        ("has been is present perfect.", "perfect_be_scope_creep"),
        ("is studying uses be with -ing.", "continuous_scope_creep"),
        ("can be uses a modal.", "modal_be_scope_creep"),
        ("This teaches WH-question formation.", "wh_question_scope_creep"),
    ]
    for text, code in cases:
        payload = json.loads(json.dumps(base))
        payload["concept_explanation"]["arabic_concept_introduction"] += " " + text
        assert validate_concept_unit(payload, blueprint=bp, lesson=lesson).diagnostics_json["code"] == code


def test_present_be_rules_cover_expanded_scope_with_real_forms_not_internal_keys(db):
    identity = run(ensure_identity(db, BE_IDENTITY))
    lesson = db.sync_session.get(GrammarCanonicalLesson, uuid.UUID(identity.data["canonical_lesson_id"]))
    bp = normalize_compact_blueprint_plan(_compact_be_plan(), lesson=lesson, grammar_profile=_be_profile())
    payload = {
        "patterns": [
            {
                "id": "pat_1",
                "pattern": "I am / I am not / Am I ...?",
                "example": "I am ready. I am not late. Am I ready? Yes, I am.",
            },
            {
                "id": "pat_2",
                "pattern": "he/she/it is / is not / Is she ...?",
                "example": "She is ready. She isn't late. Is she ready? No, she isn't.",
            },
            {
                "id": "pat_3",
                "pattern": "you/we/they are / are not / Are they ...?",
                "example": "They are home. They aren't outside. Are they home? Yes, they are.",
            },
        ],
        "rule_notes": [
            "Choose am, is, or are from the subject.",
            "Put not after be for negatives.",
            "Move be before the subject for yes/no questions.",
        ],
        "arabic_english_contrast": "Ø¨Ø§Ù„Ø¹Ø±Ø¨ÙŠ Ù‚Ø¯ Ù†Ø­Ø°Ù Ø§Ù„ÙØ¹Ù„ Ø§Ù„Ø¸Ø§Ù‡Ø±ØŒ Ù„ÙƒÙ† Ø§Ù„Ø¥Ù†Ø¬Ù„ÙŠØ²ÙŠØ© ØªØ­ØªØ§Ø¬ be.",
        "contrasts_and_mistakes": [
            {
                "id": "mistake_1",
                "incorrect": "I student.",
                "correct": "I am a student.",
                "why": "\u0644\u0627\u0632\u0645 \u0646\u0636\u0639 am \u0628\u064a\u0646 I \u0648\u0627\u0644\u0645\u0639\u0646\u0649 \u062d\u062a\u0649 \u062a\u0643\u0648\u0646 \u0627\u0644\u062c\u0645\u0644\u0629 \u0635\u062d\u064a\u062d\u0629 \u0628\u0627\u0644\u0625\u0646\u062c\u0644\u064a\u0632\u064a\u0629.",
                "misunderstanding": "Ø§Ù„Ø¹Ø±Ø¨ÙŠ Ø£Ø­ÙŠØ§Ù†Ø§ ÙŠØ­Ø°Ù Ø§Ù„ÙØ¹Ù„ Ø§Ù„Ø¸Ø§Ù‡Ø±.",
            },
            {
                "id": "mistake_2",
                "incorrect": "She are ready.",
                "correct": "She is ready.",
                "why": "\u0627\u0644\u0641\u0627\u0639\u0644 she \u064a\u0623\u062e\u0630 is \u0648\u0644\u064a\u0633 are \u0644\u0623\u0646\u0647 \u0645\u0641\u0631\u062f \u063a\u0627\u0626\u0628.",
                "misunderstanding": "Ø§Ù„Ø®Ø·Ø£ Ù‡Ù†Ø§ ÙÙŠ Ø§Ù„ØªØ·Ø§Ø¨Ù‚ Ù…Ø¹ Ø§Ù„ÙØ§Ø¹Ù„.",
            },
            {
                "id": "mistake_3",
                "incorrect": "Do you are ready?",
                "correct": "Are you ready?",
                "why": "\u0645\u0639 be \u0646\u0642\u062f\u0645 are \u0642\u0628\u0644 \u0627\u0644\u0641\u0627\u0639\u0644 \u0648\u0644\u0627 \u0646\u0633\u062a\u062e\u062f\u0645 do \u0641\u064a \u0627\u0644\u0633\u0624\u0627\u0644.",
                "misunderstanding": "Ø§Ù„Ø·Ø§Ù„Ø¨ ÙŠØ®Ù„Ø· Ø¨ÙŠÙ† be ÙˆØ£ÙØ¹Ø§Ù„ Ø£Ø®Ø±Ù‰.",
            },
        ],
        "visual_summary": [
            {"label": "I", "form": "am / am not / Am I ...? / Yes, I am."},
            {"label": "she", "form": "is / isn't / Is she ...? / No, she isn't."},
            {"label": "they", "form": "are / aren't / Are they ...? / Yes, they are."},
        ],
    }
    payload["contrasts_and_mistakes"].extend(
        [
            {
                "id": "mistake_4",
                "incorrect": "She is ready.",
                "correct": "She isn't ready.",
                "why": "\u0639\u0646\u062f\u0645\u0627 \u0646\u0631\u064a\u062f \u0627\u0644\u0646\u0641\u064a \u0644\u0627\u0632\u0645 \u0646\u0636\u064a\u0641 not \u0628\u0639\u062f is.",
                "misunderstanding": "Learner forgets not when making a negative sentence.",
            },
            {
                "id": "mistake_5",
                "incorrect": "You are ready?",
                "correct": "Are you ready?",
                "why": "\u0641\u064a \u0633\u0624\u0627\u0644 \u0646\u0639\u0645 \u0623\u0648 \u0644\u0627 \u0646\u0642\u062f\u0645 be \u0642\u0628\u0644 \u0627\u0644\u0641\u0627\u0639\u0644.",
                "misunderstanding": "Learner keeps statement order in a question.",
            },
            {
                "id": "mistake_6",
                "incorrect": "Yes.",
                "correct": "Yes, they are.",
                "why": "\u0627\u0644\u062c\u0648\u0627\u0628 \u0627\u0644\u0642\u0635\u064a\u0631 \u064a\u062d\u062a\u0627\u062c \u0646\u0641\u0633 \u0635\u064a\u063a\u0629 be \u0645\u0639 \u0627\u0644\u0641\u0627\u0639\u0644.",
                "misunderstanding": "Learner gives an incomplete short answer.",
            },
        ]
    )

    assert validate_rules_unit(payload, blueprint=bp, lesson=lesson).valid
    blob = json.dumps(payload, ensure_ascii=False)
    assert "affirmative_am" not in blob
    missing_question = json.loads(json.dumps(payload))
    missing_question["patterns"][2]["pattern"] = "you/we/they are / are not"
    missing_question["patterns"][2]["example"] = "They are home. They aren't outside."
    missing_question["visual_summary"][2]["form"] = "are / aren't / Yes, they are."
    missing_question["contrasts_and_mistakes"][2]["incorrect"] = "They home."
    missing_question["contrasts_and_mistakes"][2]["correct"] = "They are home."
    missing_question["contrasts_and_mistakes"][2]["misunderstanding"] = "Learner adds do/does before be."
    missing_question["contrasts_and_mistakes"][4]["correct"] = "She is ready."

    diagnostics = validate_rules_unit(missing_question, blueprint=bp, lesson=lesson).diagnostics_json

    assert diagnostics["code"] == "required_form_missing"
    assert "question_are" in diagnostics["message"]


def test_successful_sectioned_generation_reaches_reviewable_without_publishing(db):
    adapter = FixtureSectionedCanonicalAuthoringAdapter(sectioned_fixture())
    result = run(generate_sectioned_draft_revision(db, identity=IDENTITY, adapter=adapter))
    revision = db.sync_session.get(GrammarCanonicalLessonRevision, uuid.UUID(result.data["revision_id"]))
    attempts = run(list_unit_attempts(db, revision_id=revision.id))

    assert result.ok is True
    assert revision.status == GrammarCanonicalRevisionStatus.REVIEWABLE.value
    assert revision.student_content_json
    assert revision.server_teaching_metadata_json
    assert len([attempt for attempt in attempts if attempt.status == "accepted"]) == 6
    assert run(get_active_published_revision_by_lesson_id(db, lesson_id=revision.lesson_id)) is None
    assert adapter.calls == ["blueprint", "concept", "examples", "rules", "practice", "production"]


def test_failed_unit_preserves_earlier_units_and_stops_generation(db):
    adapter = FixtureSectionedCanonicalAuthoringAdapter(sectioned_fixture(bad_unit="practice"))
    result = run(generate_sectioned_draft_revision(db, identity=IDENTITY, adapter=adapter))
    revision = db.sync_session.get(GrammarCanonicalLessonRevision, uuid.UUID(result.data["revision_id"]))
    attempts = run(list_unit_attempts(db, revision_id=revision.id))

    assert result.ok is False
    assert revision.status == GrammarCanonicalRevisionStatus.FAILED.value
    assert adapter.calls == ["blueprint", "concept", "examples", "rules", "practice"]
    assert {attempt.unit_key for attempt in attempts if attempt.status == "accepted"} == {"blueprint", "concept", "examples", "rules"}
    assert [attempt for attempt in attempts if attempt.unit_key == "practice" and attempt.status == "failed"]


def test_failed_blueprint_retry_creates_attempt_two_without_later_units(db):
    failed = {
        "units": {
            "blueprint": {
                "success": False,
                "diagnostics_json": {"code": "provider_incomplete_stop"},
                "stop_reason": "max_tokens",
                "output_tokens": 1500,
            }
        }
    }
    first = run(generate_sectioned_draft_revision(db, identity=BE_IDENTITY, adapter=FixtureSectionedCanonicalAuthoringAdapter(failed)))
    revision_id = uuid.UUID(first.data["revision_id"])
    revision = db.sync_session.get(GrammarCanonicalLessonRevision, revision_id)
    assert revision.status == GrammarCanonicalRevisionStatus.FAILED.value

    retry_fixture = {"units": {"blueprint": {"blueprint": _compact_be_plan()}}}
    retry_adapter = FixtureSectionedCanonicalAuthoringAdapter(retry_fixture)
    retry = run(retry_unit_attempt(db, revision_id=revision_id, unit_key="blueprint", adapter=retry_adapter))
    attempts = run(list_unit_attempts(db, revision_id=revision_id))

    assert retry.ok is True
    assert retry_adapter.calls == ["blueprint"]
    assert revision.status == GrammarCanonicalRevisionStatus.GENERATING.value
    assert [(attempt.unit_key, attempt.attempt_number, attempt.status) for attempt in attempts] == [
        ("blueprint", 1, "failed"),
        ("blueprint", 2, "accepted"),
    ]


def test_retry_learner_unit_blocks_stale_accepted_blueprint_without_new_attempt(db):
    identity = run(ensure_identity(db, BE_IDENTITY))
    lesson = db.sync_session.get(GrammarCanonicalLesson, uuid.UUID(identity.data["canonical_lesson_id"]))
    revision = run(create_next_draft_revision(db, lesson_id=lesson.id))
    stale = normalize_compact_blueprint_plan(_compact_be_plan(), lesson=lesson, grammar_profile=_be_profile())
    stale["required_forms"] = ["am", "is", "are"]
    attempt = run(create_next_unit_attempt(db, revision_id=revision.id, unit_key="blueprint"))
    run(
        accept_unit_attempt(
            db,
            attempt=attempt,
            public_payload_json=None,
            private_metadata_json=None,
            blueprint_json=stale,
            provider="fixture",
            model="fixture",
            prompt_version="stale-test",
            diagnostics_json={"status": "historically_accepted"},
        )
    )
    adapter = FixtureSectionedCanonicalAuthoringAdapter(sectioned_fixture())

    result = run(retry_unit_attempt(db, revision_id=revision.id, unit_key="concept", adapter=adapter))
    attempts = run(list_unit_attempts(db, revision_id=revision.id))

    assert result.ok is False
    assert result.message == "blueprint_required_forms_mismatch"
    assert adapter.calls == []
    assert [(item.unit_key, item.attempt_number, item.status) for item in attempts] == [("blueprint", 1, "accepted")]


def test_retry_only_failed_unit_then_assemble_reviewable(db):
    adapter = FixtureSectionedCanonicalAuthoringAdapter(sectioned_fixture(bad_unit="production"))
    result = run(generate_sectioned_draft_revision(db, identity=IDENTITY, adapter=adapter))
    revision_id = uuid.UUID(result.data["revision_id"])
    revision = db.sync_session.get(GrammarCanonicalLessonRevision, revision_id)
    assert revision.status == GrammarCanonicalRevisionStatus.FAILED.value

    retry_adapter = FixtureSectionedCanonicalAuthoringAdapter(sectioned_fixture())
    retry = run(retry_unit_attempt(db, revision_id=revision_id, unit_key="production", adapter=retry_adapter))
    assembled = run(assemble_sectioned_revision(db, revision_id=revision_id))

    assert retry.ok is True
    assert retry_adapter.calls == ["production"]
    assert assembled.ok is True
    assert revision.status == GrammarCanonicalRevisionStatus.REVIEWABLE.value


def test_assembly_is_deterministic_valid_and_hash_changes_with_unit(db):
    first = run(generate_sectioned_draft_revision(db, identity=IDENTITY, adapter=FixtureSectionedCanonicalAuthoringAdapter(sectioned_fixture())))
    second = run(generate_sectioned_draft_revision(db, identity=IDENTITY, adapter=FixtureSectionedCanonicalAuthoringAdapter(sectioned_fixture())))
    changed = run(generate_sectioned_draft_revision(db, identity=IDENTITY, adapter=FixtureSectionedCanonicalAuthoringAdapter(sectioned_fixture(changed_example=True))))

    first_revision = db.sync_session.get(GrammarCanonicalLessonRevision, uuid.UUID(first.data["revision_id"]))
    second_revision = db.sync_session.get(GrammarCanonicalLessonRevision, uuid.UUID(second.data["revision_id"]))
    changed_revision = db.sync_session.get(GrammarCanonicalLessonRevision, uuid.UUID(changed.data["revision_id"]))

    assert tuple(first_revision.student_content_json.keys()) == (
        "orientation",
        "meaning_hook",
        "model_examples",
        "noticing",
        "concept_explanation",
        "form_and_rules",
        "arabic_clarification",
        "contrasts_and_mistakes",
        "understanding_checks",
        "guided_practice",
        "supported_production",
        "transfer",
        "exit_check",
        "reflection",
    )
    assert first_revision.content_hash == second_revision.content_hash
    assert first_revision.content_hash != changed_revision.content_hash


def test_student_safe_unit_inspection_excludes_private_metadata(db):
    result = run(generate_sectioned_draft_revision(db, identity=IDENTITY, adapter=FixtureSectionedCanonicalAuthoringAdapter(sectioned_fixture())))
    revision_id = uuid.UUID(result.data["revision_id"])
    attempts = run(list_unit_attempts(db, revision_id=revision_id, unit_key="practice"))
    accepted = [attempt for attempt in attempts if attempt.status == "accepted"][0]
    inspection = run(inspect_unit_attempt(db, attempt_id=accepted.id))
    blob = json.dumps(inspection.data, ensure_ascii=True, sort_keys=True)

    assert "public_payload" in inspection.data
    assert "expected_answer" not in blob
    assert "sample_answer" not in blob
    assert "feedback_reasoning" not in blob
    assert "hint" not in blob
    assert "raw_response_text" not in blob


def test_cli_sectioned_command_parsing():
    from scripts.grammar_canonical_lessons import build_parser

    parser = build_parser()
    args = parser.parse_args([
        "generate-sectioned-draft",
        "--grammar-id",
        "gram_present_simple",
        "--cefr-level",
        "A2",
        "--fixture-json",
        "fixture.json",
    ])
    assert args.command == "generate-sectioned-draft"
    assert args.fixture_json == "fixture.json"

    units = parser.parse_args(["units", "--revision-id", str(uuid.uuid4()), "--unit-key", "practice"])
    assert units.command == "units"

    with pytest.raises(SystemExit):
        parser.parse_args(["generate-sectioned-draft", "--grammar-id", "gram_present_simple", "--cefr-level", "A2"])


def test_cli_sectioned_real_provider_requires_confirmation():
    from scripts.grammar_canonical_lessons import _dispatch, build_parser

    parser = build_parser()
    args = parser.parse_args([
        "generate-sectioned-draft",
        "--grammar-id",
        "gram_present_simple",
        "--cefr-level",
        "A2",
        "--locale",
        "ar-SY",
        "--real-provider",
    ])

    with pytest.raises(ValueError, match="confirm-outbound-claude"):
        run(_dispatch(None, args))


def test_real_sectioned_adapter_uses_unit_budget_metadata_and_call_limit():
    calls = []

    def fake_generate(prompt, *, system, temperature, max_output_tokens, timeout):
        calls.append(
            {
                "prompt": prompt,
                "system": system,
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
                "timeout": timeout,
            }
        )
        return SimpleNamespace(
            text=json.dumps({"blueprint": blueprint()}),
            model="claude-test",
            stop_reason="end_turn",
            input_tokens=123,
            output_tokens=456,
        )

    adapter = ExistingLLMSectionedCanonicalAuthoringAdapter(
        allow_outbound=True,
        max_calls=1,
        provider_id="claude",
        json_result_generator=fake_generate,
        timeout_seconds=30.0,
    )
    result = adapter.generate_blueprint(_adapter_request())

    assert result.success is True
    assert result.structured_payload["grammar_target"] == "gram_present_simple"
    assert result.stop_reason == "end_turn"
    assert result.input_tokens == 123
    assert result.output_tokens == 456
    assert result.truncated is False
    assert result.json_parse_passed is True
    assert calls[0]["max_output_tokens"] == 1500

    blocked = adapter.generate_blueprint(_adapter_request())
    assert blocked.success is False
    assert blocked.diagnostics_json["code"] == "sectioned_call_limit_exceeded"
    assert len(calls) == 1


def test_concept_prompt_budget_allows_expanded_arabic_first_scope():
    bundle = build_sectioned_prompt_bundle(
        unit_key="concept",
        request=CanonicalAuthoringAdapterRequest(
            grammar_id="gram_be_present",
            display_name="Present of be",
            cefr_level="A2",
            locale="ar-SY",
            methodology_version="grammar_lesson_methodology_v2_arabic_first",
            grammar_profile=_be_profile(),
            learner_signals={"synthetic": True},
        ),
        blueprint=normalize_compact_blueprint_plan(
            _compact_be_plan(),
            lesson=SimpleNamespace(grammar_id="gram_be_present", cefr_level="A2", locale="ar-SY"),
            grammar_profile=_be_profile(),
        ),
        accepted_prior_units={},
    )

    assert bundle.max_tokens == 3000


def test_rules_prompt_budget_allows_expanded_present_be_scope():
    bundle = build_sectioned_prompt_bundle(
        unit_key="rules",
        request=CanonicalAuthoringAdapterRequest(
            grammar_id="gram_be_present",
            display_name="Present of be",
            cefr_level="A2",
            locale="ar-SY",
            methodology_version="grammar_lesson_methodology_v2_arabic_first",
            grammar_profile=_be_profile(),
            learner_signals={"synthetic": True},
        ),
        blueprint=normalize_compact_blueprint_plan(
            _compact_be_plan(),
            lesson=SimpleNamespace(grammar_id="gram_be_present", cefr_level="A2", locale="ar-SY"),
            grammar_profile=_be_profile(),
        ),
        accepted_prior_units={},
    )

    assert bundle.max_tokens == 3400


def test_practice_prompt_budget_allows_expanded_present_be_scope():
    bundle = build_sectioned_prompt_bundle(
        unit_key="practice",
        request=CanonicalAuthoringAdapterRequest(
            grammar_id="gram_be_present",
            display_name="Present of be",
            cefr_level="A2",
            locale="ar-SY",
            methodology_version="grammar_lesson_methodology_v2_arabic_first",
            grammar_profile=_be_profile(),
            learner_signals={"synthetic": True},
        ),
        blueprint=normalize_compact_blueprint_plan(
            _compact_be_plan(),
            lesson=SimpleNamespace(grammar_id="gram_be_present", cefr_level="A2", locale="ar-SY"),
            grammar_profile=_be_profile(),
        ),
        accepted_prior_units={},
    )

    assert bundle.max_tokens == 8000


def test_production_prompt_budget_allows_expanded_present_be_scope():
    bundle = build_sectioned_prompt_bundle(
        unit_key="production",
        request=CanonicalAuthoringAdapterRequest(
            grammar_id="gram_be_present",
            display_name="Present of be",
            cefr_level="A2",
            locale="ar-SY",
            methodology_version="grammar_lesson_methodology_v2_arabic_first",
            grammar_profile=_be_profile(),
            learner_signals={"synthetic": True},
        ),
        blueprint=normalize_compact_blueprint_plan(
            _compact_be_plan(),
            lesson=SimpleNamespace(grammar_id="gram_be_present", cefr_level="A2", locale="ar-SY"),
            grammar_profile=_be_profile(),
        ),
        accepted_prior_units={},
    )

    assert bundle.max_tokens == 3000


def test_real_sectioned_adapter_rejects_truncated_response():
    def fake_generate(prompt, *, system, temperature, max_output_tokens, timeout):
        return SimpleNamespace(
            text='{"blueprint":',
            model="claude-test",
            stop_reason="max_tokens",
            input_tokens=10,
            output_tokens=max_output_tokens,
        )

    adapter = ExistingLLMSectionedCanonicalAuthoringAdapter(
        allow_outbound=True,
        max_calls=6,
        provider_id="claude",
        json_result_generator=fake_generate,
        timeout_seconds=30.0,
    )
    result = adapter.generate_blueprint(_adapter_request())

    assert result.success is False
    assert result.truncated is True
    assert result.json_parse_passed is False
    assert result.diagnostics_json["code"] == "provider_incomplete_stop"
