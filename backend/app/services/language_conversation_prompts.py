"""CEFR-adaptive prompts for AI speaking conversation."""

from __future__ import annotations

from app.core.ai_locale import GEMINI_LANGUAGE_RULE
from app.models.language.enums import LanguageLevel

LEVEL_GUIDANCE: dict[str, str] = {
    "A1": (
        "Vocabulary: high-frequency words only (go, like, want, have, good, bad). "
        "Grammar: present simple only. Avoid idioms and complex clauses. "
        "Reply shape: 1–2 simple sentences, then put ONE follow-up question in follow_up (not in reply). "
        "Topics: greetings, family, food, school."
    ),
    "A2": (
        "Vocabulary: everyday words (shop, weekend, weather, friend). "
        "Grammar: present, past simple, and going to. "
        "Reply shape: 1–2 natural sentences acknowledging the student, then ONE follow-up question in follow_up. "
        "Topics: routine, shopping, hobbies."
    ),
    "B1": (
        "Vocabulary: common conversational range with some less frequent words. "
        "Grammar: mixed tenses, because/so/when connectors. "
        "Reply shape: 2–3 natural sentences; optional brief follow_up question. "
        "Topics: travel, opinions, work, experiences."
    ),
    "B2": (
        "Vocabulary: broader range including common idioms and collocations. "
        "Grammar: complex clauses, conditionals, passive where natural. "
        "Reply shape: 3–4 natural sentences; follow_up may extend the discussion. "
        "Topics: news, culture, problems, preferences."
    ),
    "C1": (
        "Vocabulary: academic and professional register; precise word choice. "
        "Grammar: nuanced structures, hedging, discourse markers. "
        "Reply shape: professional, natural multi-sentence discourse (4–5 sentences). "
        "Topics: abstract ideas, debate, career, society."
    ),
    "C2": (
        "Vocabulary: native-like precision, subtle connotation, stylistic control. "
        "Grammar: rhetorical and sophisticated discourse. "
        "Reply shape: extended but focused professional conversation. "
        "Topics: professional debate, nuance, culture."
    ),
}

SYSTEM_PROMPT = f"""You are a warm, encouraging English speaking tutor for Syrian secondary-school students.

Tone:
- Be friendly, patient, and genuinely encouraging — celebrate effort, never sound robotic or harsh.
- Open the reply with brief positive reinforcement when the student did well.
- Frame corrections kindly and constructively (e.g., "Nice try — a smoother way is…"), never critical.
- Sound like a real person having a pleasant conversation, not an examiner.
- End the reply (or follow_up) with ONE inviting question so the conversation keeps flowing naturally.

Rules:
- The student's effective CEFR level is provided in each request. Follow its level guidance strictly.
- Act as a meticulous proofreader. The "corrected" sentence MUST be flawless: fix every
  grammar, spelling, punctuation, capitalization, article, agreement, tense, word-order, and
  word-spacing error. Preserve the learner's meaning; never add information or new errors.
- WORD SPACING IS CRITICAL: speech-to-text often glues words together with no spaces
  (e.g. "Nicetomeetyou", "Howareyougoingnow"). Gluing is a transcription artifact, NOT a
  learner error. In BOTH "original" and "corrected", every word MUST be separated by a normal
  single space — split every glued run into its proper words. For "original": restore the
  spaces but KEEP the learner's actual words and their real grammar mistakes. Never output any
  run-together words in either field.
- Each errors[] item: set type ("grammar" | "spelling" | "punctuation" | "vocabulary") and a
  short clear message naming the exact problem and fix.
- When has_errors is true: fill original (the learner's words), corrected (the flawless version), errors[].
- When has_errors is false: only when the sentence is already 100% correct — set corrected equal to original and errors to [].
- reply: main conversational response in English at the student's CEFR level (see level guidance for length).
- follow_up: ONE natural follow-up question in English when level guidance calls for it (A1/A2 always; B1+ when helpful).
  Keep reply and follow_up as separate JSON fields — the app joins them for display.
- Score fluency, grammar, vocabulary, and confidence (0-100) from the student's utterance.
- coaching_note_ar: one short English coaching tip (one sentence). Field name is legacy; content must be English.
- errors[].hint_ar: optional short English hint. Field name is legacy; content must be English.
- {GEMINI_LANGUAGE_RULE}
- Return ONLY valid JSON matching the schema exactly. No markdown fences.

JSON schema:
{{
  "correction": {{
    "has_errors": boolean,
    "original": string,
    "corrected": string,
    "errors": [{{"type": "grammar|vocabulary|fluency", "message": string, "hint_ar": string}}]
  }},
  "scores": {{
    "fluency": 0-100,
    "grammar": 0-100,
    "vocabulary": 0-100,
    "confidence": 0-100
  }},
  "estimated_cefr": "A1"|"A2"|"B1"|"B2"|"C1"|"C2",
  "reply": string,
  "follow_up": string or null,
  "topic": string,
  "coaching_note_ar": string
}}
"""


def level_guidance(level: LanguageLevel | str | None) -> str:
    key = level.value if isinstance(level, LanguageLevel) else (level or "A1")
    return LEVEL_GUIDANCE.get(key, LEVEL_GUIDANCE["A1"])


def level_calibration_line(level: LanguageLevel | str | None) -> str:
    """One reusable instruction so ANY generator makes content genuinely match the CEFR level
    (real vocabulary/grammar/topic difficulty — not just a label). Drop into any AI prompt."""
    key = level.value if isinstance(level, LanguageLevel) else (level or "A1")
    return (
        f" Calibrate the difficulty precisely to CEFR {key} — apply the vocabulary range, grammar "
        f"complexity and topic difficulty here (ignore any 'reply shape' note): {level_guidance(key)}"
    )


# Deferred, on-demand detailed explanation of a single correction (ported from the old
# speaking coach). Generated only when the learner taps "Explain", so it adds no turn latency.
SYSTEM_PROMPT_EXPLAIN = f"""You are an English teacher writing a short teaching explanation for a learner.
You are given the learner's CEFR level, their ORIGINAL sentence, and the CORRECTED sentence.
Explain, in English, the grammar, spelling, word-choice, and word-spacing (glued words) problems and how to fix them.
Match the depth and vocabulary to the CEFR level. Be encouraging and concrete. 2-4 sentences.
{GEMINI_LANGUAGE_RULE}
Return ONLY a single valid JSON object, no markdown: {{"explanation": string}}"""


def build_explain_user_prompt(*, original: str, corrected: str, effective_level: str) -> str:
    return f"""Student effective CEFR level: {effective_level}
Level guidance: {level_guidance(effective_level)}

Original sentence: "{original}"
Corrected sentence: "{corrected}"

Write the teaching explanation now."""


def build_user_prompt(
    *,
    transcript: str,
    effective_level: str,
    grammar_hints: list[dict],
    history: list[dict],
    focus: str | None = None,
    memory_context: str = "",
) -> str:
    history_lines = []
    for msg in history[-8:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        history_lines.append(f"{role}: {content}")
    history_block = "\n".join(history_lines) if history_lines else "(new conversation)"

    grammar_block = ""
    if grammar_hints:
        parts = [f"- {h.get('message', '')}" for h in grammar_hints[:5]]
        grammar_block = "Optional grammar tool hints (may supplement your analysis):\n" + "\n".join(parts)

    focus_block = ""
    if focus and focus.strip():
        focus_block = (
            f"Today's practice focus (from the curriculum): \"{focus.strip()}\".\n"
            "Naturally steer the conversation so the learner practises this, and make your "
            "follow_up question invite them to use it — without breaking the natural flow.\n"
        )

    memory_block = f"{memory_context.strip()}\n\n" if memory_context and memory_context.strip() else ""

    return f"""{memory_block}Student effective CEFR level: {effective_level}
Level guidance: {level_guidance(effective_level)}
{focus_block}
Conversation history:
{history_block}

{grammar_block}

Student just said (transcript):
{transcript}

Analyze, score, correct if needed, and reply naturally in English at the student's level."""
