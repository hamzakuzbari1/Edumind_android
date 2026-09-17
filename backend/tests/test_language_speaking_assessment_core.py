"""Unit tests for the Speaking Assessment Core builder (MVP evidence/auditability layer).

Pure, deterministic, side-effect-free -- no database, no AI/LLM mocking needed. If any of these
tests ever needed to mock an LLM call or Hume client, that alone would prove the builder violated
its own "no second LLM call, no Hume of any kind" contract.
"""

from __future__ import annotations

import inspect

from app.schemas.language_exam import CEFRLevel, SpeakingGradeSchema
from app.services import language_speaking_assessment_core_service as core
from app.services.language_speaking_assessment_core_service import build_speaking_assessment_core


def _import_lines(module) -> list[str]:
    return [line for line in inspect.getsource(module).splitlines() if line.strip().startswith(("import ", "from "))]


def _grade(**overrides) -> SpeakingGradeSchema:
    values = dict(
        level=CEFRLevel.B1,
        fluency=6.0,
        lexical=5.5,
        grammar=7.0,
        pronunciation=0.0,
        score=6.2,
        feedback="Pronunciation was unassessed.",
        detected_errors=[],
    )
    values.update(overrides)
    return SpeakingGradeSchema(**values)


def _turn(
    *,
    question="Tell me about your day.",
    transcription="I went to school and studied English with my friends.",
    bank_item_id=None,
    bank_item_subskill=None,
    audio_duration_seconds=None,
    stt_engine=None,
) -> dict:
    turn = {"question": question, "transcription": transcription}
    if bank_item_id is not None:
        turn["bank_item_id"] = bank_item_id
    if bank_item_subskill is not None:
        turn["bank_item_subskill"] = bank_item_subskill
    if audio_duration_seconds is not None:
        turn["audio_duration_seconds"] = audio_duration_seconds
    if stt_engine is not None:
        turn["stt_engine"] = stt_engine
    return turn


_MVP_META = {"review_status": "mvp_approved_pending_full_review", "human_reviewed": False}


# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------


def test_versions_are_the_expected_mvp_labels_and_scoring_is_marked_unchanged():
    result = build_speaking_assessment_core(results=[], grade=None, expected_turns=3)
    assert result.speaking_assessment_core_version == "speaking_assessment_core_mvp_v1"
    assert result.speaking_rubric_version == "speaking_llm_transcript_rubric_v1"
    assert result.scoring_changed is False
    assert result.language_evaluation.scoring_changed is False


# ---------------------------------------------------------------------------
# Prompt evidence
# ---------------------------------------------------------------------------


def test_prompt_evidence_all_bank_turns_with_distinct_subskills():
    results = [
        _turn(bank_item_id=101, bank_item_subskill="self_intro"),
        _turn(bank_item_id=102, bank_item_subskill="routine_description"),
        _turn(bank_item_id=103, bank_item_subskill="past_narration"),
    ]
    result = build_speaking_assessment_core(results=results, grade=_grade(), expected_turns=3)
    ev = result.prompt_evidence
    assert ev.expected_turns == 3
    assert ev.turns_answered == 3
    assert ev.prompt_source == "mvp_speaking_prompt_bank"
    assert ev.unique_bank_items_count == 3
    assert ev.unique_subskills_count == 3
    assert ev.repeated_subskills is False
    assert ev.subskills_seen == ["past_narration", "routine_description", "self_intro"]
    assert ev.bank_item_ids_present is True
    assert ev.fallback_prompt_used is False


def test_prompt_evidence_detects_repeated_subskill_deterministically():
    results = [
        _turn(bank_item_id=201, bank_item_subskill="self_intro"),
        _turn(bank_item_id=202, bank_item_subskill="self_intro"),
        _turn(bank_item_id=203, bank_item_subskill="routine_description"),
    ]
    result = build_speaking_assessment_core(results=results, grade=_grade(), expected_turns=3)
    ev = result.prompt_evidence
    assert ev.unique_bank_items_count == 3
    assert ev.unique_subskills_count == 2
    assert ev.repeated_subskills is True


def test_prompt_evidence_detects_fallback_prompt_used_when_some_turns_have_no_bank_item():
    results = [
        _turn(bank_item_id=301, bank_item_subskill="self_intro"),
        _turn(bank_item_id=None, bank_item_subskill=None),  # AI-generated fallback question
        _turn(bank_item_id=302, bank_item_subskill="routine_description"),
    ]
    result = build_speaking_assessment_core(results=results, grade=_grade(), expected_turns=3)
    ev = result.prompt_evidence
    assert ev.fallback_prompt_used is True
    assert ev.bank_item_ids_present is True
    assert ev.prompt_source == "mvp_speaking_prompt_bank"


def test_prompt_evidence_all_fallback_reports_fallback_generated_source():
    results = [_turn(), _turn(), _turn()]  # no bank_item_id anywhere (old-style or AI fallback)
    result = build_speaking_assessment_core(results=results, grade=_grade(), expected_turns=3)
    ev = result.prompt_evidence
    assert ev.prompt_source == "fallback_generated"
    assert ev.bank_item_ids_present is False
    assert ev.fallback_prompt_used is True


def test_prompt_evidence_zero_turns_reports_unknown_source_and_no_fallback_claim():
    result = build_speaking_assessment_core(results=[], grade=None, expected_turns=3)
    ev = result.prompt_evidence
    assert ev.turns_answered == 0
    assert ev.prompt_source == "unknown"
    assert ev.fallback_prompt_used is False


def test_prompt_evidence_reports_mvp_review_status_when_metadata_resolves():
    results = [_turn(bank_item_id=401, bank_item_subskill="self_intro")]
    result = build_speaking_assessment_core(
        results=results, grade=_grade(), expected_turns=3, bank_item_metadata={401: _MVP_META}
    )
    assert result.prompt_evidence.prompt_review_status == "mvp_approved_pending_full_review"


# ---------------------------------------------------------------------------
# STT / transcript evidence
# ---------------------------------------------------------------------------


def test_stt_evidence_usable_when_all_transcripts_are_healthy():
    transcripts = [
        "I went to school and studied English with my friends.",
        "We played football after school in the park.",
        "Then I went home and had dinner with my family.",
    ]
    results = [_turn(transcription=t, stt_engine="openai") for t in transcripts]
    result = build_speaking_assessment_core(results=results, grade=_grade(), expected_turns=3)
    ev = result.stt_evidence
    expected_total = sum(len(t.split()) for t in transcripts)
    assert ev.provider == "openai"
    assert ev.transcripts_count == 3
    assert ev.empty_transcripts_count == 0
    assert ev.short_transcripts_count == 0
    assert ev.total_word_count == expected_total
    assert ev.average_words_per_turn == round(expected_total / 3, 1)
    assert ev.confidence_available is False
    assert ev.evidence_status == "usable"


def test_stt_evidence_insufficient_when_any_transcript_is_empty():
    results = [
        _turn(transcription="I went to school and studied English with my friends."),
        _turn(transcription=""),
        _turn(transcription="Then I went home and had dinner with my family."),
    ]
    result = build_speaking_assessment_core(results=results, grade=_grade(), expected_turns=3)
    ev = result.stt_evidence
    assert ev.empty_transcripts_count == 1
    assert ev.evidence_status == "insufficient"


def test_stt_evidence_unavailable_when_every_transcript_is_empty():
    results = [_turn(transcription=""), _turn(transcription="  "), _turn(transcription="")]
    result = build_speaking_assessment_core(results=results, grade=_grade(), expected_turns=3)
    ev = result.stt_evidence
    assert ev.transcripts_count == 3
    assert ev.empty_transcripts_count == 3
    assert ev.evidence_status == "unavailable"


def test_stt_evidence_zero_turns_is_unavailable():
    result = build_speaking_assessment_core(results=[], grade=None, expected_turns=3)
    assert result.stt_evidence.transcripts_count == 0
    assert result.stt_evidence.evidence_status == "unavailable"


def test_stt_evidence_limited_when_transcripts_are_short_but_not_empty():
    results = [
        _turn(transcription="Yes okay"),  # 2 words -- below the short threshold, non-empty
        _turn(transcription="I went to school and studied English with my friends."),
        _turn(transcription="Then I went home and had dinner with my family."),
    ]
    result = build_speaking_assessment_core(results=results, grade=_grade(), expected_turns=3)
    ev = result.stt_evidence
    assert ev.empty_transcripts_count == 0
    assert ev.short_transcripts_count == 1
    assert ev.evidence_status == "limited"


def test_stt_evidence_insufficient_when_every_turn_is_short():
    results = [_turn(transcription="Yes"), _turn(transcription="No way"), _turn(transcription="Okay")]
    result = build_speaking_assessment_core(results=results, grade=_grade(), expected_turns=3)
    assert result.stt_evidence.short_transcripts_count == 3
    assert result.stt_evidence.evidence_status == "insufficient"


def test_stt_evidence_confidence_is_never_invented():
    results = [_turn()]
    result = build_speaking_assessment_core(results=results, grade=_grade(), expected_turns=3)
    assert result.stt_evidence.confidence_available is False


# ---------------------------------------------------------------------------
# Language evaluation (read-only restatement of grade_speaking -- no second LLM call)
# ---------------------------------------------------------------------------


def test_language_evaluation_copies_existing_grade_speaking_result_without_a_second_llm_call():
    grade = _grade(level=CEFRLevel.B1, fluency=6.0, lexical=5.5, grammar=7.0, score=6.2)
    result = build_speaking_assessment_core(
        results=[_turn()], grade=grade, expected_turns=3, llm_provider="claude"
    )
    ev = result.language_evaluation
    assert ev.provider == "claude"
    assert ev.source == "grade_speaking"
    assert ev.dimensions["fluency"] == 6.0
    assert ev.dimensions["lexical"] == 5.5
    assert ev.dimensions["grammar"] == 7.0
    assert ev.dimensions["pronunciation"] == "unassessed"
    assert ev.estimated_cefr == "B1"
    assert ev.score == 6.2
    assert ev.scoring_changed is False
    # This module has no way to reach the network -- there is no ai_engine/http import here at
    # all, so this test (and the whole module) cannot accidentally exercise a real LLM call.
    assert "ai_engine" not in inspect.getsource(core)
    assert not any("hume" in line.lower() for line in _import_lines(core))


def test_language_evaluation_handles_missing_grade_without_crashing():
    result = build_speaking_assessment_core(results=[_turn()], grade=None, expected_turns=3)
    ev = result.language_evaluation
    assert ev.dimensions == {"pronunciation": "unassessed"}
    assert ev.estimated_cefr == ""
    assert ev.score is None


# ---------------------------------------------------------------------------
# Prosody / delivery evidence (derived from duration + transcript only)
# ---------------------------------------------------------------------------


def test_prosody_evidence_computes_speech_rate_from_duration_and_word_count():
    results = [
        _turn(transcription=" ".join(["word"] * 20), audio_duration_seconds=10.0),  # 120 wpm
        _turn(transcription=" ".join(["word"] * 8), audio_duration_seconds=8.0),  # 60 wpm
    ]
    result = build_speaking_assessment_core(
        results=results, grade=_grade(), expected_turns=3, prosody_provider="acoustic"
    )
    ev = result.prosody_evidence
    assert ev.provider == "derived_duration_transcript"
    assert ev.runtime_status == "partial"
    assert ev.speech_rate_wpm == [120.0, 60.0]
    assert ev.average_speech_rate_wpm == 90.0
    assert ev.acoustic_metrics_available is False
    assert ev.pause_metrics_available is False
    assert ev.rhythm_metrics_available is False
    assert ev.evi_runtime_status == "not_implemented"


def test_prosody_evidence_reports_unavailable_with_no_duration_data_and_does_not_require_audio():
    results = [_turn(), _turn()]  # no audio_duration_seconds anywhere
    result = build_speaking_assessment_core(results=results, grade=_grade(), expected_turns=3)
    ev = result.prosody_evidence
    assert ev.runtime_status == "unavailable"
    assert ev.speech_rate_wpm == [None, None]
    assert ev.average_speech_rate_wpm is None
    assert ev.response_duration_status == "unknown"


def test_prosody_evidence_not_implemented_for_a_non_acoustic_provider():
    results = [_turn(audio_duration_seconds=10.0)]
    result = build_speaking_assessment_core(
        results=results, grade=_grade(), expected_turns=3, prosody_provider="hume"
    )
    ev = result.prosody_evidence
    assert ev.runtime_status == "not_implemented"
    assert ev.provider == "hume"
    assert ev.evi_runtime_status == "not_implemented"


def test_prosody_evidence_classifies_response_duration_against_expected_range():
    results = [_turn(bank_item_id=501, audio_duration_seconds=5.0)]  # below min=10
    meta = {501: {"expected_response_seconds": {"min": 10, "target": 20, "max": 45}}}
    result = build_speaking_assessment_core(
        results=results, grade=_grade(), expected_turns=3, bank_item_metadata=meta
    )
    ev = result.prosody_evidence
    assert ev.response_duration_status == "under"
    assert ev.short_response_turns == 1


def test_prosody_evidence_very_short_response_turn_is_counted():
    results = [_turn(audio_duration_seconds=2.0)]  # below the absolute very-short floor
    result = build_speaking_assessment_core(results=results, grade=_grade(), expected_turns=3)
    assert result.prosody_evidence.very_short_response_turns == 1


def test_prosody_module_never_imports_hume_anything():
    """Static guard: the module must never import any Hume-related symbol -- this task explicitly
    forbids calling Hume EVI or Hume Expression Measurement for MVP prosody. (The module's own
    docstrings legitimately mention "Hume" to document that it is deliberately NOT used, so this
    checks import statements specifically rather than the full source text.)"""
    assert not any("hume" in line.lower() for line in _import_lines(core))


# ---------------------------------------------------------------------------
# Review flags
# ---------------------------------------------------------------------------


def test_review_flags_missing_turns():
    results = [_turn(bank_item_id=601, bank_item_subskill="self_intro")]
    result = build_speaking_assessment_core(results=results, grade=_grade(), expected_turns=3)
    assert "missing_speaking_turns" in result.review_flags


def test_review_flags_insufficient_transcript_evidence_from_empty_responses():
    results = [_turn(transcription=""), _turn(transcription=""), _turn(transcription="")]
    result = build_speaking_assessment_core(results=results, grade=_grade(), expected_turns=3)
    assert "insufficient_speaking_transcript_evidence" in result.review_flags


def test_review_flags_very_short_responses():
    results = [
        _turn(audio_duration_seconds=2.0, bank_item_id=701),
        _turn(audio_duration_seconds=10.0, bank_item_id=702),
        _turn(audio_duration_seconds=10.0, bank_item_id=703),
    ]
    result = build_speaking_assessment_core(results=results, grade=_grade(), expected_turns=3)
    assert "very_short_speaking_responses" in result.review_flags


def test_review_flags_mvp_pending_review_does_not_force_needs_human_review():
    results = [
        _turn(bank_item_id=801, bank_item_subskill="self_intro", audio_duration_seconds=15.0),
        _turn(bank_item_id=802, bank_item_subskill="routine_description", audio_duration_seconds=15.0),
        _turn(bank_item_id=803, bank_item_subskill="past_narration", audio_duration_seconds=15.0),
    ]
    meta = {i: _MVP_META for i in (801, 802, 803)}
    result = build_speaking_assessment_core(
        results=results, grade=_grade(), expected_turns=3, bank_item_metadata=meta
    )
    assert "speaking_prompts_pending_full_review" in result.review_flags
    assert result.needs_human_review is False


def test_review_flags_fallback_prompt_used():
    results = [_turn(bank_item_id=None), _turn(bank_item_id=901), _turn(bank_item_id=902)]
    result = build_speaking_assessment_core(results=results, grade=_grade(), expected_turns=3)
    assert "fallback_speaking_prompt_used" in result.review_flags


def test_review_flags_pronunciation_unassessed_is_always_present():
    result = build_speaking_assessment_core(results=[_turn()], grade=_grade(), expected_turns=3)
    assert "pronunciation_unassessed" in result.review_flags


def test_review_flags_missing_bank_prompt_metadata_when_lookup_incomplete():
    results = [_turn(bank_item_id=1001, bank_item_subskill="self_intro")]
    result = build_speaking_assessment_core(
        results=results, grade=_grade(), expected_turns=3, bank_item_metadata={}
    )
    assert "missing_bank_prompt_metadata" in result.review_flags


# ---------------------------------------------------------------------------
# needs_human_review: only for deterministic evidence problems, never for score/MVP/EVI/pronunciation
# ---------------------------------------------------------------------------


def test_needs_human_review_true_for_missing_turns():
    results = [_turn(bank_item_id=1101, bank_item_subskill="self_intro")]
    result = build_speaking_assessment_core(results=results, grade=_grade(), expected_turns=3)
    assert result.needs_human_review is True


def test_needs_human_review_true_for_insufficient_transcript_evidence():
    results = [_turn(transcription=""), _turn(transcription=""), _turn(transcription="")]
    result = build_speaking_assessment_core(results=results, grade=_grade(), expected_turns=3)
    assert result.needs_human_review is True


def test_needs_human_review_true_for_unexpected_fallback_prompt_use():
    results = [
        _turn(bank_item_id=None, audio_duration_seconds=15.0),
        _turn(bank_item_id=1201, bank_item_subskill="self_intro", audio_duration_seconds=15.0),
        _turn(bank_item_id=1202, bank_item_subskill="routine_description", audio_duration_seconds=15.0),
    ]
    result = build_speaking_assessment_core(results=results, grade=_grade(), expected_turns=3)
    assert result.needs_human_review is True


def test_needs_human_review_false_for_a_clean_complete_session_regardless_of_low_score():
    results = [
        _turn(bank_item_id=1301, bank_item_subskill="self_intro", audio_duration_seconds=15.0),
        _turn(bank_item_id=1302, bank_item_subskill="routine_description", audio_duration_seconds=15.0),
        _turn(bank_item_id=1303, bank_item_subskill="past_narration", audio_duration_seconds=15.0),
    ]
    low_score_grade = _grade(level=CEFRLevel.A1, fluency=1.0, lexical=1.0, grammar=1.0, score=1.0)
    result = build_speaking_assessment_core(results=results, grade=low_score_grade, expected_turns=3)
    assert result.needs_human_review is False


# ---------------------------------------------------------------------------
# Backward compatibility -- old/minimal sessions must never crash
# ---------------------------------------------------------------------------


def test_old_minimal_speaking_state_does_not_crash():
    """Matches the exact shape of pre-existing/legacy results: only question/transcription (no
    bank_item_id, bank_item_subskill, audio_duration_seconds, or stt_engine at all)."""
    old_style_results = [
        {"question": f"Speaking question {i}", "transcription": f"Verified speaking response number {i}"}
        for i in range(3)
    ]
    result = build_speaking_assessment_core(results=old_style_results, grade=_grade(), expected_turns=3)
    assert result.prompt_evidence.bank_item_ids_present is False
    assert result.prosody_evidence.runtime_status == "unavailable"
    assert result.stt_evidence.transcripts_count == 3


def test_missing_bank_item_metadata_mapping_does_not_crash():
    results = [_turn(bank_item_id=1401, bank_item_subskill="self_intro")]
    result = build_speaking_assessment_core(results=results, grade=_grade(), expected_turns=3, bank_item_metadata=None)
    assert result.prompt_evidence.bank_item_ids_present is True
    assert "missing_bank_prompt_metadata" in result.review_flags


def test_missing_audio_duration_does_not_crash():
    results = [_turn(audio_duration_seconds=None)]
    result = build_speaking_assessment_core(results=results, grade=_grade(), expected_turns=3)
    assert result.prosody_evidence.speech_rate_wpm == [None]


def test_completely_empty_session_does_not_crash():
    result = build_speaking_assessment_core(results=[], grade=None, expected_turns=3)
    assert result.prompt_evidence.turns_answered == 0
    assert result.needs_human_review is True
