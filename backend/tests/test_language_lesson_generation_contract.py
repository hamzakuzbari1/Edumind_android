from types import SimpleNamespace

from app.models.language.content import LanguageContentItem
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.services.language_learner_context_service import LanguageLearnerContext, StudentIdentity
from app.services.language_listening_service import (
    _is_current_personalized_listening_item,
    _listening_personalization_block,
)
from app.services.language_lesson_generation_service import _to_body


def _question(index: int) -> dict:
    return {
        "stem": f"Question {index}?",
        "choices": ["A", "B", "C", "D"],
        "correct_index": 0,
        "type": "detail",
        "explanation": "Because the speaker says it.",
        "evidence_quote": "A",
    }


def test_listening_generation_rejects_single_question_lessons() -> None:
    result = _to_body(
        "listening",
        "A2",
        {
            "title": "Short Clip",
            "audio_transcript": "I am a student. She is ready.",
            "questions": [_question(1)],
        },
    )

    assert result is None


def test_listening_generation_requires_exactly_four_questions() -> None:
    result = _to_body(
        "listening",
        "A2",
        {
            "title": "Grammar Listening Clip",
            "audio_transcript": "I am a student. She is ready. They are at home.",
            "questions": [_question(i) for i in range(1, 5)],
        },
    )

    assert result is not None
    assert len(result["body"]["questions"]) == 4


def test_language_content_item_maps_student_owner_and_grammar_stamp() -> None:
    item = LanguageContentItem(
        student_id=123,
        language_id=1,
        skill=LanguageSkill.listening,
        level=LanguageLevel.A2,
        content_type="lesson",
        title="Owned Grammar Listening",
        body_json={
            "source": "ai_personalized",
            "grammar_id": "gram_be_present",
            "grammar_title": "Present of be",
        },
    )

    assert item.student_id == 123
    assert item.body_json["grammar_id"] == "gram_be_present"


def test_listening_runtime_rejects_stale_non_grammar_reserved_lessons() -> None:
    stale = LanguageContentItem(
        language_id=1,
        skill=LanguageSkill.listening,
        level=LanguageLevel.B1,
        content_type="lesson",
        title="Old Shared Lesson",
        body_json={"questions": [_question(1)]},
    )
    current = LanguageContentItem(
        student_id=123,
        language_id=1,
        skill=LanguageSkill.listening,
        level=LanguageLevel.A2,
        content_type="lesson",
        title="Current Grammar Lesson",
        body_json={
            "source": "ai_personalized",
            "grammar_id": "gram_be_present",
            "questions": [_question(i) for i in range(1, 5)],
        },
    )

    assert _is_current_personalized_listening_item(
        stale,
        student_id=123,
        grammar_id="gram_be_present",
    ) is False
    assert _is_current_personalized_listening_item(
        current,
        student_id=123,
        grammar_id="gram_be_present",
    ) is True


def test_listening_personalization_block_preserves_level_context_and_diversity() -> None:
    learner = LanguageLearnerContext(
        student_identity=StudentIdentity(student_id=123),
        current_cefr_level="B1",
        effective_level="B1",
        interests=["technology", "community events"],
        future_goal="general English",
    )
    grammar_ctx = SimpleNamespace(
        grammar_id="gram_present_perfect",
        recommended_contexts=("recent experiences", "life updates"),
    )

    block, topics = _listening_personalization_block(
        learner=learner,
        grammar_ctx=grammar_ctx,
        level="B1",
        student_id=123,
        profile_hash="abc123",
        recent_titles=["Gate Change Announcement"],
    )

    assert "CEFR B1" in block
    assert "variation_seed" in block
    assert "Gate Change Announcement" in block
    assert "recent experiences" in block
    assert topics
