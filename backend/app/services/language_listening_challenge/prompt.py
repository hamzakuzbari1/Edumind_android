"""Adaptive challenge prompt block for listening generation (Phase 3.3)."""

from __future__ import annotations

from app.services.language_cefr.listening_runtime import get_listening_generation_word_target
from app.services.language_listening_challenge.constants import TRANSCRIPT_LENGTH_MULTIPLIER
from app.services.language_listening_challenge.types import ChallengeLevel


_CHALLENGE_DIRECTIVES: dict[ChallengeLevel, tuple[str, ...]] = {
    ChallengeLevel.easy: (
        "Keep the transcript toward the shorter end of the CEFR word-count band.",
        "Use slow, clear delivery with explicit signposting and concrete details.",
        "Favour straightforward main-idea and detail questions with plainly distinct distractors.",
        "Minimise implicit information — state key facts directly in the audio.",
        "Question wording should be direct and unambiguous.",
    ),
    ChallengeLevel.normal: (
        "Target the mid-range of the CEFR transcript length band.",
        "Use natural conversational pace with a balanced mix of detail and inference items.",
        "Distractors should be plausible but separable with careful listening.",
        "Include a modest amount of implicit information that careful listeners can infer.",
        "Question complexity should match standard classroom listening practice.",
    ),
    ChallengeLevel.hard: (
        "Aim toward the upper end of the CEFR transcript length band (never exceed it).",
        "Use brisk, natural speech with denser information and overlapping points.",
        "Craft high-quality distractors that are close paraphrases of the transcript.",
        "Increase inference density — several answers require one logical step beyond the audio.",
        "Include implicit information the learner must connect across sentences.",
        "Question wording may use paraphrase and mild compression.",
    ),
    ChallengeLevel.exam: (
        "Use the upper CEFR transcript length bound with exam-style information density.",
        "Speech should be brisk and efficient, as in IELTS/Cambridge listening sections.",
        "Distractors must be exam-grade: near-synonyms, partial truths, and subtle scope shifts.",
        "Prioritise inference, attitude, and purpose questions with multi-step reasoning.",
        "Embed implicit information — answers should not be quoted verbatim.",
        "Question stems should mirror formal test wording; reasoning depth is high.",
    ),
}


def build_adaptive_challenge_prompt_block(
    cefr_level: str,
    challenge_level: ChallengeLevel,
    *,
    word_target: int | None = None,
) -> str:
    """Build [ADAPTIVE CHALLENGE] directives — adjusts difficulty within CEFR, never beyond it."""
    base_words = word_target or get_listening_generation_word_target(cefr_level)
    multiplier = TRANSCRIPT_LENGTH_MULTIPLIER.get(challenge_level.value, 1.0)
    target_words = max(20, round(base_words * multiplier))
    label = f"{cefr_level} {challenge_level.value.title()}"

    lines = [
        "[ADAPTIVE CHALLENGE]",
        f"- Challenge band: {label} (within CEFR {cefr_level} vocabulary and grammar only).",
        f"- Transcript length target: ~{target_words} words (must stay inside [CEFR PROFILE] bounds).",
    ]
    for directive in _CHALLENGE_DIRECTIVES[challenge_level]:
        lines.append(f"- {directive}")
    lines.append(
        "Do NOT change CEFR vocabulary band, grammar scope, or learning objectives. "
        "Only adjust challenge inside the current CEFR level."
    )
    lines.append("[/ADAPTIVE CHALLENGE]")
    return "\n".join(lines)
