"""Speaking Assessment Core: an additive, MVP evidence/auditability layer for the AI Exam's final
Speaking report section.

Builds a structured, deterministic, side-effect-free summary of the evidence behind a session's
speaking result -- which prompts were used, whether transcripts were usable, a read-only
restatement of the existing grade_speaking() output, and a lightweight duration+transcript-derived
delivery proxy. This never re-scores, never calls an LLM or Hume, and never mutates anything; it
only describes evidence that already exists by the time the final report is built.

Explicitly out of scope for this module (per product decision): Hume EVI live-conversation runtime,
Hume Expression Measurement, Supertonic prompt playback, any new scoring formula, and any change to
grade_speaking, level_from_score10, or the final confidence calculation.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.schemas.language_exam import (
    SpeakingAssessmentCore,
    SpeakingLanguageEvaluation,
    SpeakingProsodyEvidence,
    SpeakingPromptEvidence,
    SpeakingSttEvidence,
)

# Conservative, deterministic evidence-availability thresholds (word/second counts, never scores).
# A low grade is not an evidence problem; an empty, missing, or very short transcript/response is.
_SHORT_TRANSCRIPT_WORD_THRESHOLD = 5
_FALLBACK_MIN_RESPONSE_SECONDS = 8.0
_VERY_SHORT_RESPONSE_SECONDS = 4.0
_MVP_REVIEW_STATUS = "mvp_approved_pending_full_review"


def _word_count(text: Any) -> int:
    return len(str(text or "").split())


def _cefr_value(level: Any) -> str:
    return str(getattr(level, "value", level) or "")


def _build_prompt_evidence(
    results: list[dict], *, expected_turns: int, bank_item_metadata: dict[int, dict]
) -> SpeakingPromptEvidence:
    turns_answered = len(results)
    bank_item_ids = [int(r["bank_item_id"]) for r in results if r.get("bank_item_id")]
    subskills_seen = [str(r["bank_item_subskill"]) for r in results if r.get("bank_item_subskill")]
    unique_bank_item_ids = set(bank_item_ids)
    unique_subskills = sorted(set(subskills_seen))
    bank_item_ids_present = bool(bank_item_ids)
    fallback_prompt_used = any(not r.get("bank_item_id") for r in results)

    if turns_answered == 0:
        prompt_source = "unknown"
    elif bank_item_ids_present:
        prompt_source = "mvp_speaking_prompt_bank"
    else:
        prompt_source = "fallback_generated"

    review_statuses = {
        str(meta.get("review_status"))
        for item_id in unique_bank_item_ids
        for meta in [bank_item_metadata.get(item_id) or {}]
        if meta.get("review_status")
    }
    prompt_review_status = next(iter(review_statuses)) if len(review_statuses) == 1 else ""

    return SpeakingPromptEvidence(
        prompt_source=prompt_source,
        prompt_review_status=prompt_review_status,
        expected_turns=expected_turns,
        turns_answered=turns_answered,
        unique_bank_items_count=len(unique_bank_item_ids),
        unique_subskills_count=len(unique_subskills),
        repeated_subskills=len(subskills_seen) > len(set(subskills_seen)),
        subskills_seen=unique_subskills,
        bank_item_ids_present=bank_item_ids_present,
        fallback_prompt_used=fallback_prompt_used,
    )


def _build_stt_evidence(results: list[dict]) -> SpeakingSttEvidence:
    transcripts_count = len(results)
    providers = [str(r["stt_engine"]) for r in results if r.get("stt_engine")]
    provider = providers[0] if providers else ""

    word_counts = [_word_count(r.get("transcription")) for r in results]
    empty_transcripts_count = sum(1 for wc in word_counts if wc == 0)
    short_transcripts_count = sum(1 for wc in word_counts if 0 < wc < _SHORT_TRANSCRIPT_WORD_THRESHOLD)
    total_word_count = sum(word_counts)
    average_words_per_turn = round(total_word_count / transcripts_count, 1) if transcripts_count else 0.0

    if transcripts_count == 0 or empty_transcripts_count == transcripts_count:
        evidence_status = "unavailable"
    elif empty_transcripts_count > 0 or short_transcripts_count >= transcripts_count:
        evidence_status = "insufficient"
    elif short_transcripts_count > 0:
        evidence_status = "limited"
    else:
        evidence_status = "usable"

    return SpeakingSttEvidence(
        provider=provider,
        transcripts_count=transcripts_count,
        empty_transcripts_count=empty_transcripts_count,
        short_transcripts_count=short_transcripts_count,
        total_word_count=total_word_count,
        average_words_per_turn=average_words_per_turn,
        confidence_available=False,
        evidence_status=evidence_status,
    )


def _build_language_evaluation(grade: Any, *, llm_provider: str) -> SpeakingLanguageEvaluation:
    if grade is None:
        return SpeakingLanguageEvaluation(provider=llm_provider, dimensions={"pronunciation": "unassessed"})
    return SpeakingLanguageEvaluation(
        provider=llm_provider,
        dimensions={
            "fluency": getattr(grade, "fluency", None),
            "lexical": getattr(grade, "lexical", None),
            "grammar": getattr(grade, "grammar", None),
            "pronunciation": "unassessed",
        },
        estimated_cefr=_cefr_value(getattr(grade, "level", "")),
        score=getattr(grade, "score", None),
    )


def _classify_duration(actual: float, expected: dict | None) -> str | None:
    if not isinstance(expected, dict):
        return None
    try:
        lo = float(expected.get("min"))
        hi = float(expected.get("max"))
    except (TypeError, ValueError):
        return None
    if actual < lo:
        return "under"
    if actual > hi:
        return "over"
    return "within"


def _build_prosody_evidence(
    results: list[dict], *, prosody_provider: str, bank_item_metadata: dict[int, dict]
) -> SpeakingProsodyEvidence:
    if prosody_provider != "acoustic":
        # Any other configured provider (e.g. a future "hume") is not implemented in this task --
        # never silently pretend to have real acoustic evidence for it.
        return SpeakingProsodyEvidence(provider=prosody_provider, runtime_status="not_implemented")

    speech_rates: list[float | None] = []
    duration_classifications: list[str] = []
    short_response_turns = 0
    very_short_response_turns = 0
    any_usable_data = False

    for r in results:
        duration = r.get("audio_duration_seconds")
        if not isinstance(duration, (int, float)) or duration <= 0:
            speech_rates.append(None)
            continue

        any_usable_data = True
        word_count = _word_count(r.get("transcription"))
        speech_rates.append(round((word_count / duration) * 60, 1) if word_count > 0 else None)

        expected = None
        item_id = r.get("bank_item_id")
        if item_id:
            expected = (bank_item_metadata.get(int(item_id)) or {}).get("expected_response_seconds")

        min_expected = None
        if isinstance(expected, dict):
            try:
                min_expected = float(expected.get("min"))
            except (TypeError, ValueError):
                min_expected = None
        threshold = min_expected if min_expected is not None else _FALLBACK_MIN_RESPONSE_SECONDS
        if duration < threshold:
            short_response_turns += 1
        if duration < _VERY_SHORT_RESPONSE_SECONDS:
            very_short_response_turns += 1

        classification = _classify_duration(duration, expected)
        if classification:
            duration_classifications.append(classification)

    numeric_rates = [r for r in speech_rates if r is not None]
    average_rate = round(sum(numeric_rates) / len(numeric_rates), 1) if numeric_rates else None

    if duration_classifications:
        counts = Counter(duration_classifications)
        max_count = max(counts.values())
        # Deterministic tie-break: under > over > within -- a short response is the more
        # actionable evidence signal to surface first when turns disagree.
        priority = {"under": 0, "over": 1, "within": 2}
        response_duration_status = min(
            (status for status, count in counts.items() if count == max_count),
            key=lambda status: priority[status],
        )
    else:
        response_duration_status = "unknown"

    return SpeakingProsodyEvidence(
        provider="derived_duration_transcript",
        runtime_status="partial" if any_usable_data else "unavailable",
        speech_rate_wpm=speech_rates,
        average_speech_rate_wpm=average_rate,
        response_duration_status=response_duration_status,
        short_response_turns=short_response_turns,
        very_short_response_turns=very_short_response_turns,
        acoustic_metrics_available=False,
        pause_metrics_available=False,
        rhythm_metrics_available=False,
        evi_runtime_status="not_implemented",
    )


def _build_review_flags(
    *,
    prompt_evidence: SpeakingPromptEvidence,
    stt_evidence: SpeakingSttEvidence,
    prosody_evidence: SpeakingProsodyEvidence,
    bank_item_metadata_missing: bool,
) -> list[str]:
    flags: list[str] = []
    if prompt_evidence.prompt_review_status == _MVP_REVIEW_STATUS:
        flags.append("speaking_prompts_pending_full_review")
    if prompt_evidence.turns_answered < prompt_evidence.expected_turns:
        flags.append("missing_speaking_turns")
    if stt_evidence.evidence_status in ("insufficient", "unavailable"):
        flags.append("insufficient_speaking_transcript_evidence")
    if prosody_evidence.very_short_response_turns > 0:
        flags.append("very_short_speaking_responses")
    if prompt_evidence.repeated_subskills:
        flags.append("repeated_speaking_subskill")
    if prompt_evidence.fallback_prompt_used:
        flags.append("fallback_speaking_prompt_used")
    if prosody_evidence.runtime_status == "not_implemented":
        flags.append("prosody_runtime_not_implemented")
    if prosody_evidence.runtime_status == "partial":
        flags.append("prosody_evidence_partial")
    # Always true for MVP -- explanatory, never a human-review trigger on its own.
    flags.append("pronunciation_unassessed")
    if bank_item_metadata_missing:
        flags.append("missing_bank_prompt_metadata")
    return flags


def build_speaking_assessment_core(
    *,
    results: list[dict],
    grade: Any,
    expected_turns: int,
    llm_provider: str = "claude",
    prosody_provider: str = "acoustic",
    bank_item_metadata: dict[int, dict] | None = None,
) -> SpeakingAssessmentCore:
    """Build the Speaking Assessment Core evidence object for the final report.

    Pure and side-effect-free: every input is a plain value already available by the time the
    final report is built (no DB access, no LLM call, no randomness, no wall-clock reads).
    `bank_item_metadata` is an optional, caller-supplied {bank_item_id: body_json} mapping (see
    language_placement_question_bank_service.fetch_bank_item_metadata for the read-only lookup);
    passing None, or an incomplete mapping, degrades safely rather than raising -- old sessions
    without bank_item_id/bank_item_subskill/audio_duration_seconds are handled the same way.
    """
    results = results or []
    bank_item_metadata = bank_item_metadata or {}

    prompt_evidence = _build_prompt_evidence(
        results, expected_turns=expected_turns, bank_item_metadata=bank_item_metadata
    )
    stt_evidence = _build_stt_evidence(results)
    language_evaluation = _build_language_evaluation(grade, llm_provider=llm_provider)
    prosody_evidence = _build_prosody_evidence(
        results, prosody_provider=prosody_provider, bank_item_metadata=bank_item_metadata
    )

    referenced_ids = {int(r["bank_item_id"]) for r in results if r.get("bank_item_id")}
    bank_item_metadata_missing = bool(referenced_ids) and any(
        item_id not in bank_item_metadata for item_id in referenced_ids
    )

    review_flags = _build_review_flags(
        prompt_evidence=prompt_evidence,
        stt_evidence=stt_evidence,
        prosody_evidence=prosody_evidence,
        bank_item_metadata_missing=bank_item_metadata_missing,
    )

    needs_human_review = (
        prompt_evidence.turns_answered < prompt_evidence.expected_turns
        or stt_evidence.evidence_status in ("insufficient", "unavailable")
        or prompt_evidence.fallback_prompt_used
    )

    return SpeakingAssessmentCore(
        prompt_evidence=prompt_evidence,
        stt_evidence=stt_evidence,
        language_evaluation=language_evaluation,
        prosody_evidence=prosody_evidence,
        review_flags=review_flags,
        needs_human_review=needs_human_review,
    )
