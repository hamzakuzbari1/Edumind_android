"""Unit contracts for the phase-zero state and idempotency protocol."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.schemas.language_exam import CEFRLevel
from app.api.language_exam import (
    MCQ_SECTIONS,
    MIN_MCQ_EVIDENCE_ITEMS,
    PLACEMENT_EXAM_DURATION_SECONDS,
    READING_MIN_EVIDENCE_ITEMS,
    _already_used_bank_item_ids,
    _already_used_speaking_bank_item_ids,
    _boundary_situation,
    _ensure_exam_timer,
    _ensure_state_protocol,
    _exam_remaining_seconds,
    _expire_exam_if_needed,
    _expired_incomplete_exam_can_be_replaced,
    _is_valid_mcq_pool_item,
    _is_usable_audio_url,
    _legacy_placement_question_to_exam_item,
    _maybe_retrigger_prep,
    _mcq_continuation_level,
    _new_exam_token,
    _apply_writing_route_cap,
    _normalise_writing_prompt_payload,
    _record_request,
    _request_receipt,
    _require_current_state,
    _reading_diagnostic_breakdown,
    _reading_weighted_result,
    _speaking_bank_question_text,
    _state_revision,
    _static_placement_listening_pool,
    _writing_route_from_score,
    _writing_task1_payload,
    canonical_payload_hash,
    evaluation_lease_expired,
    exam_evidence_statuses,
)
from app.models.language.enums import LanguageSkill
from app.models.language.exam import LanguageExamSession
from app.models.language.placement import LanguagePlacementQuestion, LanguagePlacementSection


def test_prompt_tokens_are_opaque_and_not_reused():
    first = _new_exam_token()
    second = _new_exam_token()

    assert len(first) >= 24
    assert first != second
    assert not first.isdecimal()


def test_exam_timer_initializes_to_one_hour():
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    state = {}

    assert _ensure_exam_timer(state, now=now) is True

    assert state["exam_duration_seconds"] == PLACEMENT_EXAM_DURATION_SECONDS
    assert state["exam_started_at"] == now.isoformat()
    assert state["exam_expires_at"] == (
        now + timedelta(seconds=PLACEMENT_EXAM_DURATION_SECONDS)
    ).isoformat()
    assert _exam_remaining_seconds(state, now=now) == PLACEMENT_EXAM_DURATION_SECONDS


def test_expired_exam_marks_session_failed_without_completion():
    now = datetime(2026, 1, 1, 13, 0, tzinfo=timezone.utc)
    state = {
        "state_revision": 3,
        "exam_duration_seconds": PLACEMENT_EXAM_DURATION_SECONDS,
        "exam_started_at": (now - timedelta(seconds=PLACEMENT_EXAM_DURATION_SECONDS + 1)).isoformat(),
        "exam_expires_at": (now - timedelta(seconds=1)).isoformat(),
    }
    session = LanguageExamSession(
        id="expired-placement-session",
        student_id=1,
        language_id=1,
        exam_state=state,
        status="in_progress",
    )

    assert _expire_exam_if_needed(session, state, now=now) is True

    assert session.status == "failed"
    assert session.is_completed is False
    assert state["exam_time_expired"] is True
    assert state["evaluation"]["error_code"] == "time_expired"
    assert state["evaluation"]["evaluation_status"] == "time_expired"
    assert state["state_revision"] == 4


def test_expired_incomplete_exam_is_replaceable_but_completed_exam_is_not():
    failed_session = LanguageExamSession(
        id="expired-placement-session",
        student_id=1,
        language_id=1,
        exam_state={"exam_time_expired": True},
        status="failed",
        is_completed=False,
    )
    completed_session = LanguageExamSession(
        id="completed-placement-session",
        student_id=1,
        language_id=1,
        exam_state={"exam_time_expired": True},
        status="failed",
        is_completed=True,
    )

    assert _expired_incomplete_exam_can_be_replaced(failed_session, failed_session.exam_state) is True
    assert _expired_incomplete_exam_can_be_replaced(completed_session, completed_session.exam_state) is False


def test_existing_state_is_upgraded_without_touching_answers():
    state = {
        "reading": {"pool": {"A2": {"question": "Q"}}, "asked": [{"correct": True}]},
        "speaking": {"pending_question": "Speak", "results": [{"transcription": "hello"}]},
        "writing": {"prompt": "Write", "response": "existing answer"},
    }

    assert _ensure_state_protocol(state) is True
    assert _state_revision(state) == 1
    assert state["reading"]["pool"]["A2"]["question_token"]
    assert state["speaking"]["turn_token"]
    assert state["writing"]["prompt_token"]
    assert state["reading"]["asked"] == [{"correct": True}]
    assert state["writing"]["response"] == "existing answer"


def test_canonical_payload_hash_is_order_independent_and_input_sensitive():
    first = canonical_payload_hash(kind="mcq_answer", payload={"choice": 1, "token": "abc"})
    reordered = canonical_payload_hash(kind="mcq_answer", payload={"token": "abc", "choice": 1})
    changed = canonical_payload_hash(kind="mcq_answer", payload={"choice": 2, "token": "abc"})

    assert first == reordered
    assert first != changed
    assert len(first) == 64


def test_receipt_accepts_same_payload_and_rejects_conflicting_reuse():
    state = {"state_revision": 8}
    payload_hash = canonical_payload_hash(kind="writing_answer", payload={"text_sha256": "a" * 64})
    _record_request(
        state,
        kind="writing_answer",
        request_id="request-0001",
        payload_hash=payload_hash,
        request_revision=7,
        token="token-1234567890",
        result_reference="writing:revision:8",
    )

    receipt = _request_receipt(
        state,
        kind="writing_answer",
        request_id="request-0001",
        payload_hash=payload_hash,
    )
    assert receipt and receipt["result_reference"] == "writing:revision:8"

    with pytest.raises(HTTPException) as exc_info:
        _request_receipt(
            state,
            kind="writing_answer",
            request_id="request-0001",
            payload_hash="b" * 64,
        )
    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "idempotency_conflict"


def test_state_revision_and_prompt_token_must_both_match():
    state = {"state_revision": 5}
    _require_current_state(
        state,
        supplied_revision=5,
        supplied_token="token-1234567890",
        expected_token="token-1234567890",
    )

    for revision, token in ((4, "token-1234567890"), (5, "different-token-1")):
        with pytest.raises(HTTPException) as exc_info:
            _require_current_state(
                state,
                supplied_revision=revision,
                supplied_token=token,
                expected_token="token-1234567890",
            )
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail["code"] == "stale_exam_state"
        assert exc_info.value.detail["current_state_revision"] == 5


def test_evaluation_lease_distinguishes_active_and_expired_workers():
    now = datetime.now(timezone.utc)
    active = {
        "evaluation": {
            "evaluation_status": "running",
            "evaluation_lease_expires_at": (now + timedelta(minutes=2)).isoformat(),
        }
    }
    expired = {
        "evaluation": {
            "evaluation_status": "running",
            "evaluation_lease_expires_at": (now - timedelta(seconds=1)).isoformat(),
        }
    }

    assert evaluation_lease_expired(active, now=now) is False
    assert evaluation_lease_expired(expired, now=now) is True


def test_evidence_status_separates_server_content_failure_from_student_omission():
    state = {
        "reading": {"ready": False, "pool": {}, "evidence_status": "content_unavailable"},
        "listening": {"ready": True, "pool": {"A2": {}}, "asked": [], "done": False},
        "grammar_vocab": {"ready": True, "pool": {"A2": {}}, "asked": [], "done": False},
        "writing": {"ready": True, "prompt": "Write", "response": None, "done": False},
        "speaking": {"total_turns": 1, "results": [], "done": False},
    }

    statuses = exam_evidence_statuses(state)

    assert statuses["reading"] == "content_unavailable"
    assert statuses["listening"] == "missing_student_response"
    assert statuses["writing"] == "missing_student_response"


def test_static_placement_listening_pool_covers_all_cefr_levels_with_real_audio():
    pool = _static_placement_listening_pool(["A1", "A2", "B1", "B2", "C1", "C2"])

    assert set(pool) == {"A1", "A2", "B1", "B2", "C1", "C2"}
    for level, item in pool.items():
        assert item["level"] == level
        assert item["source"] == "static_placement_listening_fallback"
        assert _is_usable_audio_url(item.get("audio_url"))
        assert item.get("audio_text")
        assert item.get("question")
        assert len(item.get("options") or []) >= 2
        assert 0 <= item["correct_index"] < len(item["options"])
        assert item.get("bank_item_id") is None


def test_legacy_placement_listening_question_converts_to_current_exam_item():
    section = LanguagePlacementSection(language_id=1, skill=LanguageSkill.listening, title_ar="Listening")
    row = LanguagePlacementQuestion(
        section_id=7,
        question_type="mcq_listening",
        prompt_json={
            "stem": "What direction?",
            "choices": ["Left", "Right", "Straight", "Back"],
            "audio_transcript": "Turn left at the corner.",
        },
        media_url="/language-assets/en/placement/listening/q3.mp3",
        answer_key_json={"correct_index": 0},
        level_hint="A2",
        sort_order=2,
    )

    item = _legacy_placement_question_to_exam_item(row, section)

    assert item is not None
    assert item["level"] == "A2"
    assert item["skill"] == "listening"
    assert item["source"] == "legacy_placement_questions_fallback"
    assert item["question"] == "What direction?"
    assert item["options"] == ["Left", "Right", "Straight", "Back"]
    assert item["correct_index"] == 0
    assert item["audio_url"] == "/language-assets/en/placement/listening/q3.mp3"
    assert item["audio_text"] == "Turn left at the corner."
    assert item["bank_item_id"] is None


def test_legacy_placement_reading_single_question_is_not_used_as_current_reading_bundle():
    section = LanguagePlacementSection(language_id=1, skill=LanguageSkill.reading, title_ar="Reading")
    row = LanguagePlacementQuestion(
        section_id=8,
        question_type="mcq",
        prompt_json={
            "stem": 'Choose the correct meaning of: "rapid"',
            "choices": ["slow", "quick", "tired", "empty"],
        },
        answer_key_json={"correct_index": 1},
        level_hint="A1",
        sort_order=0,
    )

    item = _legacy_placement_question_to_exam_item(row, section)

    assert item is None


def test_content_unavailable_retry_bypasses_prep_debounce():
    now = datetime.now(timezone.utc)
    state = {
        "state_revision": 3,
        "sections": ["speaking", "listening", "reading", "writing"],
        "cursor": 1,
        "content_prep_token": "old-prep-token-00000000001",
        "content_prep_status": "content_unavailable",
        "content_prep_error_code": "content_preparation_failed",
        "content_prep_at": now.isoformat(),
        "speaking": {"done": True},
        "listening": {
            "ready": False,
            "done": False,
            "asked": [],
            "pool": {},
            "evidence_status": "content_unavailable",
        },
        "reading": {"ready": False, "done": False, "asked": [], "pool": {}},
        "writing": {"ready": False, "done": False, "response": None},
    }
    session = LanguageExamSession(
        id="retry-content-unavailable-session",
        student_id=1,
        language_id=1,
        exam_state=state,
        status="in_progress",
    )

    assert _maybe_retrigger_prep(session, 1, BackgroundTasks()) is True
    assert session.exam_state["content_prep_status"] == "preparing"
    assert "content_prep_error_code" not in session.exam_state
    assert session.exam_state["content_prep_token"] != "old-prep-token-00000000001"
    assert session.exam_state["listening"]["evidence_status"] == "retry_required"


def test_evidence_statuses_is_sections_driven_for_speaking_and_interview():
    """New no-interview sessions must not be blocked on evidence for a section they never have;
    old persisted sessions that still list "interview" in their own sections must still require
    it. This is the sections-driven fix that replaced a hardcoded (speaking, interview) tuple."""
    no_interview = {
        "sections": ["speaking", "writing"],
        "speaking": {"total_turns": 3, "results": [], "done": False},
        "writing": {"ready": True, "prompt": "Write", "response": None, "done": False},
    }
    statuses = exam_evidence_statuses(no_interview)
    assert "interview" not in statuses
    assert statuses["speaking"] == "missing_student_response"

    with_interview = {
        "sections": ["speaking", "writing", "interview"],
        "speaking": {"total_turns": 3, "results": [], "done": False},
        "writing": {"ready": True, "prompt": "Write", "response": None, "done": False},
        "interview": {"total_turns": 2, "results": [], "done": False},
    }
    statuses = exam_evidence_statuses(with_interview)
    assert statuses["interview"] == "missing_student_response"


def test_already_used_bank_item_ids_extracts_from_asked_entries():
    """P1.1: session-scoped exclusion set is built only from this skill's own "asked" entries;
    missing/None bank_item_id values are ignored; a skill with no "asked" list (e.g. "writing")
    yields an empty set rather than erroring."""
    state = {
        "reading": {
            "asked": [
                {"level": "A2", "correct": True, "chosen_index": 0, "bank_item_id": 5},
                {"level": "B1", "correct": False, "chosen_index": 1, "bank_item_id": 9},
                {"level": "B1", "correct": False, "chosen_index": 1, "bank_item_id": None},
            ]
        },
        "writing": {"response": "some text"},
    }
    assert _already_used_bank_item_ids(state, "reading") == {5, 9}
    assert _already_used_bank_item_ids(state, "writing") == set()
    assert _already_used_bank_item_ids(state, "listening") == set()


def test_mcq_continuation_level_keeps_probing_below_minimum_evidence():
    """P1.2 Test A: with fewer than MIN_MCQ_EVIDENCE_ITEMS answered and another pool level still
    unasked, the guard must pick a level to keep going rather than stopping. It picks the nearest
    remaining rung by CEFR rank distance (same style as _new_adaptive_section), not just any."""
    level = _mcq_continuation_level(
        pool_levels={"A2", "B1", "B2"},
        asked_levels={"A2"},
        asked_count=1,
        current="A2",
    )
    assert level == "B1"  # B1 (rank distance 1) is nearer to A2 than B2 (rank distance 2)


def test_mcq_continuation_level_stops_once_minimum_evidence_reached():
    """P1.2 Test B: once MIN_MCQ_EVIDENCE_ITEMS items are answered, the guard defers to the
    staircase's own stop signal even though the pool still has an unasked level left."""
    assert MIN_MCQ_EVIDENCE_ITEMS == 3
    level = _mcq_continuation_level(
        pool_levels={"A2", "B1", "B2", "C1"},
        asked_levels={"A2", "B1", "B2"},
        asked_count=3,
        current="B2",
    )
    assert level is None


def test_mcq_continuation_level_stops_safely_when_pool_exhausted():
    """P1.2 Test C: below the evidence floor but with no unasked pool level left, the guard must
    still return None (defer to the caller's existing completion path) instead of stranding the
    exam or looping — the pool being finite bounds this to "no infinite loop" by construction."""
    level = _mcq_continuation_level(
        pool_levels={"A2", "B1"},
        asked_levels={"A2", "B1"},
        asked_count=2,
        current="B1",
    )
    assert level is None


def test_reading_continuation_uses_five_item_evidence_floor():
    assert READING_MIN_EVIDENCE_ITEMS == 5
    level = _mcq_continuation_level(
        pool_levels={"A1", "A2", "B1", "B2", "C1", "C2"},
        asked_levels={"A2", "B1", "B2"},
        asked_count=3,
        current="B2",
        min_evidence_items=READING_MIN_EVIDENCE_ITEMS,
    )
    assert level == "C1"


def test_reading_continuation_stops_after_five_items():
    level = _mcq_continuation_level(
        pool_levels={"A1", "A2", "B1", "B2", "C1", "C2"},
        asked_levels={"A1", "A2", "B1", "B2", "C1"},
        asked_count=5,
        current="C1",
        min_evidence_items=READING_MIN_EVIDENCE_ITEMS,
    )
    assert level is None


def test_reading_weighted_result_places_boundary_pattern_at_lower_stable_level():
    level, pct = _reading_weighted_result([
        {"level": "A2", "correct": True},
        {"level": "B1", "correct": True},
        {"level": "B2", "correct": False},
    ])
    assert level.value == "B1"
    assert pct == 66.7


def test_reading_weighted_result_resists_single_lucky_high_answer():
    level, pct = _reading_weighted_result([
        {"level": "A1", "correct": False},
        {"level": "A2", "correct": False},
        {"level": "B2", "correct": True},
    ])
    assert level.value == "A2"
    assert pct == 33.3


def test_reading_weighted_result_rewards_sustained_high_performance():
    level, pct = _reading_weighted_result([
        {"level": "A2", "correct": True},
        {"level": "B1", "correct": True},
        {"level": "B2", "correct": True},
        {"level": "C1", "correct": True},
        {"level": "C2", "correct": False},
    ])
    assert level.value == "C1"
    assert pct == 80.0


def test_reading_mcq_bundle_accepts_four_subquestions_only():
    item = {
        "subquestions": [
            {"question": f"Q{i}?", "options": ["A", "B", "C", "D"], "correct_index": 0}
            for i in range(4)
        ]
    }
    legacy_single_item = {"options": ["A", "B", "C", "D"], "correct_index": 0}
    assert _is_valid_mcq_pool_item(item, skill="reading") is True
    assert _is_valid_mcq_pool_item(legacy_single_item, skill="reading") is False
    assert _is_valid_mcq_pool_item({**item, "subquestions": item["subquestions"][:3]}, skill="reading") is False
    assert _is_valid_mcq_pool_item({**item, "subquestions": item["subquestions"][:3]}, skill="listening") is True


def test_reading_bundle_accepts_mixed_short_answer_subquestions():
    item = {
        "subquestions": [
            {"question": "Q1?", "options": ["A", "B", "C", "D"], "correct_index": 0},
            {"question": "Q2?", "options": ["A", "B", "C", "D"], "correct_index": 1},
            {"question": "Q3?", "response_type": "short_answer", "accepted_answers": ["because it saves time"], "max_words": 8},
            {"question": "Q4?", "response_type": "short_answer", "accepted_answers": ["a cautious tone"], "max_words": 8},
        ]
    }
    assert _is_valid_mcq_pool_item(item, skill="reading") is True


def test_reading_bundle_accepts_gap_fill_and_matching_subquestions():
    item = {
        "subquestions": [
            {"question": "Q1?", "options": ["A", "B", "C", "D"], "correct_index": 0},
            {"question": "Q2?", "response_type": "gap_fill", "accepted_answers": ["apples"], "max_words": 3},
            {
                "question": "Match each prompt.",
                "response_type": "matching",
                "matching_items": ["Place", "Reason"],
                "match_options": ["the market", "fresh fruit", "a school", "a bus"],
                "correct_indices": [0, 1],
            },
            {"question": "Q4?", "response_type": "short_answer", "accepted_answers": ["she likes them"], "max_words": 6},
        ]
    }
    assert _is_valid_mcq_pool_item(item, skill="reading") is True


def test_reading_diagnostic_breakdown_counts_bundle_subskills():
    breakdown = _reading_diagnostic_breakdown([
        {
            "level": "B1",
            "correct": True,
            "sub_correct": [True, False, True, True],
            "subskills": ["main_idea", "inference", "specific_detail", "vocabulary_in_context"],
            "word_count": 140,
        }
    ])

    assert breakdown["items_answered"] == 1
    assert breakdown["questions_answered"] == 4
    assert breakdown["average_passage_word_count"] == 140
    assert breakdown["by_subskill"]["main_idea"]["score_percent"] == 100.0
    assert breakdown["by_subskill"]["inference"]["score_percent"] == 0.0


def test_exam_evidence_statuses_accepts_mixed_reading_bundle_answers():
    state = {
        "sections": ["reading"],
        "reading": {
            "ready": True,
            "pool": {"A2": {"question": "Read and answer."}},
            "asked": [
                {
                    "level": "A2",
                    "correct": True,
                    "subquestion_answers": [0, 1, "two parts", "pleased"],
                }
            ],
            "done": True,
            "evidence_status": "completed",
        },
    }

    assert exam_evidence_statuses(state)["reading"] == "completed"


def test_writing_prompt_payload_preserves_target_range_and_task_type():
    payload = _normalise_writing_prompt_payload(
        {
            "prompt": "Write a short message (30-50 words) to a classmate.",
            "min_words": 30,
            "max_words": 50,
            "task_type": "short_message",
            "student_instructions": "Write in English. Stay on topic.",
            "rubric_focus": ["task_response"],
            "expected_language_features": ["present simple"],
            "bank_item_id": 12,
            "source": "writing_mvp_v1_draft",
        }
    )

    assert payload == {
        "prompt": "Write a short message (30-50 words) to a classmate.",
        "min_words": 30,
        "max_words": 50,
        "task_type": "short_message",
        "student_instructions": "Write in English. Stay on topic.",
        "rubric_focus": ["task_response"],
        "expected_language_features": ["present simple"],
        "bank_item_id": 12,
        "source": "writing_mvp_v1_draft",
    }


def test_adaptive_writing_task1_anchor_has_visible_word_range():
    payload = _writing_task1_payload()

    assert payload["min_words"] == 50
    assert payload["max_words"] == 80
    assert "50-80 words" in payload["prompt"]
    assert payload["task_type"] == "task1_anchor_email"


def test_adaptive_writing_routes_and_caps_levels():
    assert _writing_route_from_score(4.4) == "A1_A2"
    assert _writing_route_from_score(4.5) == "B1_B2"
    assert _writing_route_from_score(7.5) == "C1_C2"
    assert _apply_writing_route_cap(CEFRLevel.C1, "A1_A2") == CEFRLevel.B1
    assert _apply_writing_route_cap(CEFRLevel.C2, "B1_B2") == CEFRLevel.B2
    assert _apply_writing_route_cap(CEFRLevel.C2, "C1_C2") == CEFRLevel.C2


def test_min_mcq_evidence_guard_is_scoped_to_mcq_sections_only():
    """P1.2 Test E (scope guard): the evidence floor only ever applies inside answer_mcq, which is
    gated to MCQ_SECTIONS. Speaking and writing must never be members of that set, or a future
    refactor could silently apply this MCQ-only guard to non-MCQ sections."""
    assert MCQ_SECTIONS == {"listening", "reading", "grammar_vocab"}
    assert "speaking" not in MCQ_SECTIONS
    assert "writing" not in MCQ_SECTIONS
    assert "interview" not in MCQ_SECTIONS


def test_boundary_situation_detects_adjacent_disagreement():
    """P1.3: one correct item at the lower level and the adjacent-level item incorrect is exactly
    the canonical uncertainty pattern -- must return (low, high) in rank order."""
    asked = [
        {"level": "B1", "correct": True, "chosen_index": 0, "bank_item_id": 1},
        {"level": "B2", "correct": False, "chosen_index": 1, "bank_item_id": 2},
    ]
    assert _boundary_situation(asked) == ("B1", "B2")


def test_boundary_situation_is_order_independent():
    """The same disagreement, encountered in the opposite asking order, still resolves to
    (low, high) by CEFR rank rather than by which one was asked first."""
    asked = [
        {"level": "B2", "correct": False, "chosen_index": 1, "bank_item_id": 2},
        {"level": "B1", "correct": True, "chosen_index": 0, "bank_item_id": 1},
    ]
    assert _boundary_situation(asked) == ("B1", "B2")


def test_boundary_situation_none_when_levels_agree():
    """Two adjacent levels both answered the same way (both correct or both incorrect) is
    consistent performance, not uncertainty -- no boundary situation."""
    asked = [
        {"level": "A2", "correct": True, "chosen_index": 0, "bank_item_id": 1},
        {"level": "B1", "correct": True, "chosen_index": 0, "bank_item_id": 2},
    ]
    assert _boundary_situation(asked) is None


def test_boundary_situation_none_when_levels_are_not_adjacent():
    """A disagreement that spans more than one CEFR band (e.g. a P1.2-forced jump) isn't a single
    boundary -- there's no one line to confirm, so no boundary situation is reported."""
    asked = [
        {"level": "A1", "correct": True, "chosen_index": 0, "bank_item_id": 1},
        {"level": "B1", "correct": False, "chosen_index": 1, "bank_item_id": 2},
    ]
    assert _boundary_situation(asked) is None


def test_boundary_situation_none_with_fewer_than_two_answers():
    """Nothing to compare yet -- must not raise, must not fabricate a boundary from one answer."""
    assert _boundary_situation([]) is None
    assert _boundary_situation([{"level": "A2", "correct": True, "chosen_index": 0}]) is None


def test_speaking_bank_question_text_combines_situation_and_question():
    """MVP speaking-bank wiring: the displayed question folds the bank item's short scenario
    framing in front of the actual prompt text."""
    item = {"situation": "A friend asks about your day.", "question": "Tell me about your day."}
    assert _speaking_bank_question_text(item) == "A friend asks about your day. Tell me about your day."


def test_speaking_bank_question_text_falls_back_to_question_only_without_situation():
    assert _speaking_bank_question_text({"situation": "", "question": "Tell me about your day."}) == (
        "Tell me about your day."
    )
    assert _speaking_bank_question_text({"question": "Tell me about your day."}) == "Tell me about your day."
    assert _speaking_bank_question_text({"situation": "   ", "question": "  Tell me.  "}) == "Tell me."


def test_already_used_speaking_bank_item_ids_reads_from_results_not_asked():
    """Speaking's turn history lives under "results", not "asked" (unlike MCQ sections) -- this
    must read the right key and ignore missing/None bank_item_id values, mirroring
    _already_used_bank_item_ids's contract for MCQ sections (P1.1)."""
    state = {
        "speaking": {
            "results": [
                {"bank_item_id": 5, "estimated_level": "A2"},
                {"bank_item_id": None, "estimated_level": "B1"},
                {"bank_item_id": 9, "estimated_level": "B1"},
            ],
            "asked": [{"bank_item_id": 999}],  # must NOT be read for a speaking-like section
        },
        "writing": {"response": "some text"},
    }
    assert _already_used_speaking_bank_item_ids(state, "speaking") == {5, 9}
    assert _already_used_speaking_bank_item_ids(state, "writing") == set()
    assert _already_used_speaking_bank_item_ids(state, "interview") == set()
