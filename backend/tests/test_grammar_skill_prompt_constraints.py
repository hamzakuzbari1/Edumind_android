from app.services.language_grammar.enums import GrammarCEFRBand, GrammarEvidenceSourceSkill
from app.services.language_grammar_skill_context.types import SkillGrammarContext
from app.services.language_speaking_discussion.engine import (
    _effective_turn_limit,
    _require_current_lesson_package,
    _student_answer_is_enough,
    DiscussionRuntimeError,
)
from app.services.language_speaking_service import _with_grammar_speaking_instruction
from app.services.language_writing_service import _with_grammar_writing_instruction
from app.services.language_educational_package.types import (
    CorrectionMode,
    DiscussionEvidenceRole,
    DiscussionStep,
    QuestionBand,
)


def _grammar_ctx(skill: GrammarEvidenceSourceSkill) -> SkillGrammarContext:
    return SkillGrammarContext(
        grammar_id="gram_be_present",
        display_code="BE-PRESENT",
        display_name="Present of be",
        cefr_band=GrammarCEFRBand.A2,
        source_skill=skill,
        grammar_targets=("am", "is", "are", "is not"),
        examples=("I am ready.", "She is tired.", "They are at home."),
    )


def test_writing_prompt_requires_direct_current_grammar_use():
    prompt = _with_grammar_writing_instruction(
        "Write a short paragraph about your day.",
        _grammar_ctx(GrammarEvidenceSourceSkill.writing),
    )

    assert "Grammar focus: Present of be" in prompt
    assert "use this grammar directly" in prompt
    assert "at least three times" in prompt
    assert "am, is, are" in prompt


def test_speaking_prompt_requires_direct_current_grammar_use():
    prompt = _with_grammar_speaking_instruction(
        "Talk about yourself for 30 seconds.",
        _grammar_ctx(GrammarEvidenceSourceSkill.speaking),
    )

    assert "Grammar focus: Present of be" in prompt
    assert "use this grammar directly" in prompt
    assert "at least two times" in prompt
    assert "I am ready." in prompt


def test_discussion_step_has_single_effective_followup_and_clear_advance_threshold():
    step = DiscussionStep(
        step_id="step_1",
        ladder_band=QuestionBand.literal,
        prompt="What would you do?",
        success_cues=[],
        evidence_role=DiscussionEvidenceRole.formative,
        allowed_correction_mode=CorrectionMode.micro,
        max_assistant_turns=3,
    )

    assert _effective_turn_limit(step) == 1
    assert _student_answer_is_enough("They is") is False
    assert _student_answer_is_enough("They are at home today") is True


def test_discussion_runtime_rejects_stale_package_for_current_lesson():
    lesson = type("Lesson", (), {"package_id": "elp_current"})()

    _require_current_lesson_package(lesson, "elp_current")

    try:
        _require_current_lesson_package(lesson, "elp_old")
    except DiscussionRuntimeError as exc:
        assert exc.code == "stale_runtime"
    else:
        raise AssertionError("Expected stale discussion package to be rejected")
