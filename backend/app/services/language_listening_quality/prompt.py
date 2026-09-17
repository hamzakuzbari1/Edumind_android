"""Prompt enrichment for human-like listening generation (Phase 2.1)."""

from __future__ import annotations

from app.services.language_listening_quality.rotation import build_listening_quality_spec
from app.services.language_listening_quality.types import (
    ListeningQualitySpec,
    TranscriptFormatHint,
)

_NARRATIVE_GUIDANCE: dict[str, str] = {
    "setup_development_resolution": (
        "Clear three-part flow: establish context, develop the situation with connected details, "
        "then close with a natural outcome or next step."
    ),
    "problem_investigation_outcome": (
        "Present a concrete problem, explore it through questions or actions, resolve or partially resolve it."
    ),
    "journey_with_complication": (
        "Follow a sequence of events where a complication appears and is handled realistically."
    ),
    "compare_and_conclude": (
        "Compare two options, views, or approaches, then conclude with a reasoned takeaway."
    ),
    "interview_exploration": (
        "Host introduces the topic, guest develops ideas with examples, host synthesizes before closing."
    ),
    "announcement_and_action": (
        "State the purpose early, give essential details, end with what the listener should do or remember."
    ),
}

_OPENING_GUIDANCE: dict[str, str] = {
    "scene_setting": "Open by placing the listener in a specific place and moment.",
    "direct_address": "Open with a natural direct address to the audience or interlocutor.",
    "in_medias_res": "Begin mid-action or mid-conversation, then clarify context shortly after.",
    "question_hook": "Open with a relevant question that the passage then explores.",
    "contextual_preview": "Briefly preview why this listening matters before the main content.",
}

_ENDING_GUIDANCE: dict[str, str] = {
    "summary_sign_off": "Close with a concise summary and natural sign-off.",
    "call_to_action": "End with a clear action, appointment, or next step.",
    "reflective_close": "End with a brief reflection or implication.",
    "next_steps": "End by stating what happens next in the situation.",
    "open_question": "End with one thoughtful question left open (appropriate for interviews/podcasts).",
}

_PACE_GUIDANCE: dict[str, str] = {
    "slow_clear": "Short clauses, explicit transitions, pauses between key points.",
    "conversational": "Natural spoken rhythm with contractions and linked ideas.",
    "brisk_informative": "Efficient delivery typical of announcements or news updates.",
    "dynamic_multi_speaker": "Varied turn lengths, occasional overlap or interruption where natural.",
}

_FORMAT_GUIDANCE: dict[TranscriptFormatHint, str] = {
    TranscriptFormatHint.monologue: (
        "Single-speaker monologue: use natural pacing, clear transitions, concrete examples, "
        "and at least one opinion or reasoned point. Avoid list-like fact dumping."
    ),
    TranscriptFormatHint.dialogue: (
        "Two-speaker dialogue: give each speaker a distinct personality and register. "
        "Vary turn length; allow brief interruptions or clarifications. Avoid robotic alternation."
    ),
    TranscriptFormatHint.interview: (
        "Interview format: host guides with follow-up questions; guest answers with examples. "
        "Different speaking styles for host vs guest."
    ),
    TranscriptFormatHint.discussion: (
        "Multi-speaker discussion: speakers may agree, disagree politely, and build on each other's points."
    ),
    TranscriptFormatHint.panel: (
        "Panel format: moderator frames issues; panelists contribute distinct perspectives."
    ),
    TranscriptFormatHint.lecture: (
        "Lecture/seminar clip: introduce concept, illustrate with example, state implication."
    ),
    TranscriptFormatHint.news: (
        "News bulletin: lead with the headline fact, add supporting detail, concise sign-off."
    ),
}


def _authenticity_rules(level: str) -> str:
    if level == "A1":
        return (
            "Authenticity (A1): simple self-identification is allowed when the situation requires it, "
            "but prefer a realistic task (buying food, asking directions) over a biography monologue."
        )
    return (
        "Authenticity: avoid textbook self-introduction patterns unless the situation naturally requires them. "
        "Do NOT open with 'My name is…', 'I like…', or 'I go to school…' unless the scenario demands it. "
        "Prefer realistic Cambridge/IELTS-style contexts over generic learner monologues."
    )


def _question_design_rules(spec: ListeningQualitySpec) -> str:
    emphasis = ", ".join(spec.listening_question_emphasis)
    return (
        "Question design (listening-dependent):\n"
        f"- Prioritize types that require understanding the passage: {emphasis}.\n"
        "- Every question must be unanswerable without listening to this specific transcript.\n"
        "- Use distractors that paraphrase the audio, not unrelated general knowledge.\n"
        "- Include at least one question about order, intention, inference, or purpose when allowed by [CEFR PROFILE]."
    )


_DIFFICULTY_GUIDANCE: dict[str, str] = {
    "easy": (
        "Difficulty (easy, same CEFR level): stay within profile bounds but target the lower half of "
        "word count, simpler connectors, and clear explicit information."
    ),
    "normal": (
        "Difficulty (normal, same CEFR level): target the ideal word count and typical complexity "
        "for this level."
    ),
    "challenging": (
        "Difficulty (challenging, same CEFR level): stay within profile bounds but target the upper "
        "word count, richer vocabulary, and denser reasoning without exceeding CEFR limits."
    ),
}


def build_listening_quality_prompt_block(
    level: str,
    *,
    themes: str = "",
    topics: str = "",
    seed: str | None = None,
    quality_spec: ListeningQualitySpec | None = None,
    difficulty_band: str | None = None,
) -> str:
    """Render the [LISTENING QUALITY] enrichment block for Claude generation."""
    if quality_spec is None:
        spec = build_listening_quality_spec(level, themes=themes, topics=topics, seed=seed)
    else:
        spec = quality_spec
    avoid_line = "; ".join(spec.avoid_topics)
    difficulty_line = ""
    if difficulty_band and difficulty_band in _DIFFICULTY_GUIDANCE:
        difficulty_line = f"\n{_DIFFICULTY_GUIDANCE[difficulty_band]}\n"

    return (
        "[LISTENING QUALITY]\n"
        "Produce authentic educational listening material in the style of Cambridge, IELTS, TOEFL, "
        "Oxford, or British Council — not generic AI filler text.\n\n"
        f"Real-life situation: {spec.situation.value.replace('_', ' ')} — {spec.situation_brief}\n"
        f"Transcript format: {spec.format_hint.value} ({spec.speaker_count} speaker(s))\n"
        f"Narrative arc: {_NARRATIVE_GUIDANCE[spec.narrative_arc.value]}\n"
        f"Opening style: {_OPENING_GUIDANCE[spec.opening_style.value]}\n"
        f"Ending style: {_ENDING_GUIDANCE[spec.ending_style.value]}\n"
        f"Pace: {_PACE_GUIDANCE[spec.pace.value]}\n"
        f"{difficulty_line}\n"
        f"Format guidance:\n{_FORMAT_GUIDANCE[spec.format_hint]}\n\n"
        f"{_authenticity_rules(spec.level)}\n\n"
        "Narrative flow:\n"
        "- Beginning: orient the listener without isolated fact lists.\n"
        "- Development: connect ideas with cause, contrast, or sequence.\n"
        "- Ending: close naturally using the chosen ending style.\n\n"
        f"Topic diversity: avoid overused themes ({avoid_line}). "
        "Do not default to school, daily routine, or family unless the rotated situation requires it.\n\n"
        "Output diversity: vary speaker count, pace, opening, ending, and structure across lessons. "
        "Do not reuse the same template or stock phrases.\n\n"
        f"{_question_design_rules(spec)}\n"
        "[/LISTENING QUALITY]"
    )


def listening_quality_spec_snapshot(
    level: str,
    *,
    themes: str = "",
    topics: str = "",
    seed: str | None = None,
) -> dict[str, object]:
    """Structured snapshot for verification scripts."""
    spec = build_listening_quality_spec(level, themes=themes, topics=topics, seed=seed)
    return {
        "level": spec.level,
        "situation": spec.situation.value,
        "format_hint": spec.format_hint.value,
        "speaker_count": spec.speaker_count,
        "narrative_arc": spec.narrative_arc.value,
        "opening_style": spec.opening_style.value,
        "ending_style": spec.ending_style.value,
        "pace": spec.pace.value,
        "listening_question_emphasis": spec.listening_question_emphasis,
    }
