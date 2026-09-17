"""CEFR differentiation policies for Curriculum Engine V2."""

from __future__ import annotations

from app.services.language_educational_package.question_ladder import (
    QuestionBand,
    QuestionLadderPolicy,
)
from app.services.language_speaking_curriculum_engine.types import (
    LessonAuthoringPolicy,
    LexicalRecyclingPolicy,
)


def lesson_authoring_policy_for_cefr(cefr: str) -> LessonAuthoringPolicy:
    level = (cefr or "A2").upper()
    if level == "A1":
        return LessonAuthoringPolicy(
            cefr="A1",
            min_story_beats=6,
            min_dialogue_turns=6,
            min_input_word_count=90,
            max_input_word_count=180,
            target_vocabulary_count=5,
            min_recycle_per_item=2,
            teaching_block_min_chars=140,
            reflection_prompt_count=2,
            sentence_complexity="very_simple_present",
            question_depth="literal_then_personal",
            reasoning_level="supported_choice",
            transfer_expectation="near_transfer_greeting",
            lesson_length_band="standard",
            difficulty="gentle",
        )
    if level == "A2":
        return LessonAuthoringPolicy(
            cefr="A2",
            min_story_beats=8,
            min_dialogue_turns=8,
            min_input_word_count=130,
            max_input_word_count=240,
            target_vocabulary_count=6,
            min_recycle_per_item=2,
            teaching_block_min_chars=160,
            reflection_prompt_count=2,
            sentence_complexity="simple_with_connectors",
            question_depth="literal_vocab_reason",
            reasoning_level="explain_why",
            transfer_expectation="personal_situation_reuse",
            lesson_length_band="standard",
            difficulty="standard",
        )
    if level in {"B1"}:
        return LessonAuthoringPolicy(
            cefr="B1",
            min_story_beats=9,
            min_dialogue_turns=9,
            min_input_word_count=160,
            max_input_word_count=300,
            target_vocabulary_count=7,
            min_recycle_per_item=3,
            teaching_block_min_chars=180,
            reflection_prompt_count=3,
            sentence_complexity="compound_with_opinion",
            question_depth="reason_experience",
            reasoning_level="justify_choice",
            transfer_expectation="new_context_reuse",
            lesson_length_band="extended",
            difficulty="stretch",
        )
    # B2+
    return LessonAuthoringPolicy(
        cefr="B2" if level.startswith("B") else level,
        min_story_beats=10,
        min_dialogue_turns=10,
        min_input_word_count=190,
        max_input_word_count=360,
        target_vocabulary_count=7,
        min_recycle_per_item=3,
        teaching_block_min_chars=200,
        reflection_prompt_count=3,
        sentence_complexity="nuanced_spoken_discourse",
        question_depth="experience_transfer",
        reasoning_level="analyze_effect",
        transfer_expectation="independent_strategy_transfer",
        lesson_length_band="extended",
        difficulty="challenging",
    )


def story_length_policy(
    *,
    cefr: str,
    vocabulary_count: int = 0,
    grammar_topic_count: int = 0,
    lesson_length_band: str | None = None,
) -> dict[str, int | str]:
    """Curriculum-owned Educational Case length band (Claude fills inside this band).

    Derived from CEFR × vocab count × grammar complexity × lesson_length_band.
    """
    base = lesson_authoring_policy_for_cefr(cefr)
    band = (lesson_length_band or base.lesson_length_band or "standard").lower()
    vocab_n = max(0, int(vocabulary_count or 0))
    grammar_n = max(0, int(grammar_topic_count or 0))

    min_words = base.min_input_word_count
    max_words = base.max_input_word_count
    beats = base.min_story_beats

    # Vocab pressure: more targets → slightly longer case, more beats
    extra_vocab = max(0, vocab_n - base.target_vocabulary_count)
    min_words += extra_vocab * 12
    max_words += extra_vocab * 18
    beats += min(2, extra_vocab // 2)

    # Grammar complexity pressure (placeholder topics still count lightly)
    min_words += grammar_n * 15
    max_words += grammar_n * 25
    if grammar_n >= 2:
        beats += 1

    if band in {"short", "compact"}:
        min_words = max(60, int(min_words * 0.85))
        max_words = max(min_words + 40, int(max_words * 0.85))
        beats = max(4, beats - 1)
    elif band in {"extended", "long"}:
        min_words = int(min_words * 1.15)
        max_words = int(max_words * 1.2)
        beats += 1

    return {
        "min_story_beats": beats,
        "min_dialogue_turns": beats,  # dual-read
        "min_input_word_count": min_words,
        "max_input_word_count": max(max_words, min_words + 40),
        "lesson_length_band": band,
    }


def lexical_recycling_policy_for_cefr(cefr: str) -> LexicalRecyclingPolicy:
    policy = lesson_authoring_policy_for_cefr(cefr)
    return LexicalRecyclingPolicy(
        min_appearances_per_item=policy.min_recycle_per_item,
        required_sections=(
            "input_material",
            "teaching_blocks_authored",
            "discussion",
            "mini_practice",
        ),
    )


def question_ladder_for_cefr_v2(cefr: str) -> QuestionLadderPolicy:
    """Richer ladders than minimal defaults — still backend-owned."""
    level = (cefr or "A2").upper()
    if level == "A1":
        return QuestionLadderPolicy(
            required_bands=(
                QuestionBand.literal,
                QuestionBand.vocabulary,
                QuestionBand.personal_opinion,
                QuestionBand.personal_experience,
            ),
            min_steps=4,
            max_steps=6,
        )
    if level == "A2":
        return QuestionLadderPolicy(
            required_bands=(
                QuestionBand.literal,
                QuestionBand.vocabulary,
                QuestionBand.reasoning,
                QuestionBand.personal_opinion,
                QuestionBand.personal_experience,
            ),
            min_steps=5,
            max_steps=7,
        )
    if level == "B1":
        return QuestionLadderPolicy(
            required_bands=(
                QuestionBand.literal,
                QuestionBand.vocabulary,
                QuestionBand.grammar_in_context,
                QuestionBand.reasoning,
                QuestionBand.personal_opinion,
                QuestionBand.real_world_transfer,
            ),
            min_steps=6,
            max_steps=8,
        )
    if level == "B2":
        return QuestionLadderPolicy(
            required_bands=(
                QuestionBand.literal,
                QuestionBand.vocabulary,
                QuestionBand.reasoning,
                QuestionBand.personal_opinion,
                QuestionBand.personal_experience,
                QuestionBand.real_world_transfer,
            ),
            min_steps=6,
            max_steps=9,
        )
    # C1+
    return QuestionLadderPolicy(
        required_bands=(
            QuestionBand.literal,
            QuestionBand.vocabulary,
            QuestionBand.reasoning,
            QuestionBand.personal_opinion,
            QuestionBand.personal_experience,
            QuestionBand.real_world_transfer,
        ),
        min_steps=7,
        max_steps=9,
    )
