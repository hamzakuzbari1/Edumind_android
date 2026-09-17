"""Format speaking corrections for display and TTS from Gemini correction payload."""

from __future__ import annotations

from app.services.language_grammar_service import correct_text

NO_CORRECTION_MESSAGE = "Excellent. No correction needed."


def _brief_explanation(errors: list) -> str:
    messages: list[str] = []
    for err in errors:
        if not isinstance(err, dict):
            continue
        msg = (err.get("message") or "").strip()
        if msg and msg not in messages:
            messages.append(msg)
    if not messages:
        return "Review your grammar, vocabulary, and sentence structure."
    if len(messages) == 1:
        return messages[0]
    return " ".join(messages[:3])


def build_correction_display(correction: dict | None) -> dict:
    """Structured correction block for UI and spoken prefix (Gemini payload unchanged)."""
    correction = correction or {}
    original = (correction.get("original") or "").strip()
    corrected = (correction.get("corrected") or "").strip()
    errors = correction.get("errors") or []
    if not isinstance(errors, list):
        errors = []

    has_errors = bool(correction.get("has_errors"))
    if has_errors and not original and not corrected:
        has_errors = False

    if not has_errors:
        return {
            "has_errors": False,
            "no_correction_message": NO_CORRECTION_MESSAGE,
            "speech_prefix": NO_CORRECTION_MESSAGE,
        }

    explanation = _brief_explanation(errors)
    your_sentence = original or corrected
    # Deterministic spelling/grammar backstop on top of the model's fix, so the
    # corrected sentence shown to the learner is clean every time.
    corrected_sentence = correct_text(corrected or original)

    speech_prefix = (
        f"Your sentence: {your_sentence}. "
        f"Corrected sentence: {corrected_sentence}. "
        f"Explanation: {explanation}"
    )

    return {
        "has_errors": True,
        "your_sentence": your_sentence,
        "corrected_sentence": corrected_sentence,
        "explanation": explanation,
        "speech_prefix": speech_prefix,
    }


def resolve_correction_display(evaluation: dict | None) -> dict:
    """Return stored correction_display or build from legacy evaluation.correction."""
    evaluation = evaluation or {}
    stored = evaluation.get("correction_display")
    if isinstance(stored, dict) and stored:
        return stored
    return build_correction_display(evaluation.get("correction"))


def build_spoken_reply_text(*, correction_display: dict, conversation_reply: str) -> str:
    """TTS script. On error: wrong sentence -> pause -> correct sentence -> pause -> reply.

    The explanation is kept on screen only (not spoken). ' ... ' yields an audible
    pause between segments so the learner hears the wrong line, then the fix, then the reply.
    """
    reply = (conversation_reply or "").strip()
    if not correction_display.get("has_errors"):
        return reply

    wrong = (correction_display.get("your_sentence") or "").strip().rstrip(".")
    corrected = (correction_display.get("corrected_sentence") or "").strip().rstrip(".")

    segments: list[str] = []
    if wrong:
        segments.append(f"You said. {wrong}.")
    if corrected:
        segments.append(f"The correct sentence is. {corrected}.")
    if reply:
        segments.append(reply)
    return " ... ".join(s for s in segments if s)


def build_spoken_segments(*, correction_display: dict, conversation_reply: str) -> list[dict]:
    """TTS segments for the reply audio.

    The audio speaks ONLY the conversational reply (slightly slowed for clarity) so the
    on-screen karaoke word-highlight stays in sync with what is heard. The correction is
    shown visually (red/green) and can be heard via the shadowing "Listen" button.
    """
    reply = (conversation_reply or "").strip()
    return [{"text": reply, "rate": "-8%"}] if reply else []
