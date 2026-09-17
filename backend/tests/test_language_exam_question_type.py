"""Tests for exposing LanguagePlacementQuestionBankItem.question_type through the AI Exam state
API (feat(listening): expose question type in exam state).

All current MCQ_SECTIONS items (listening, reading, grammar_vocab) resolve to "mcq" today, via
either a real bank item dict (which already carries "question_type") or an older/AI-fallback item
dict (which does not) -- _build_state_out must default the latter to "mcq" rather than raising or
omitting the field. Most tests call _build_state_out directly with db=None, mirroring the existing
_ = db no-op in that function (confirmed by reading it) -- no Postgres needed for these.

Existing MCQ answer-submission (choice_index/answer_mcq) and audio-cache-validation tests are not
duplicated here; they are exercised by re-running the existing suites documented in this feature's
final report.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.api.language_exam import _build_state_out


def _session(*, section: str, item: dict, sections: list[str] | None = None):
    sections = sections or [section]
    state = {
        "version": 3,
        "state_revision": 1,
        "sections": sections,
        "cursor": 0,
        section: {
            "ready": True,
            "pool": {"A2": item},
            "current_level": "A2",
            "asked": [],
            "max_steps": 1,
            "done": False,
        },
    }
    return SimpleNamespace(id="session-1", exam_state=state, status="in_progress")


def _listening_item(**overrides) -> dict:
    item = {
        "level": "A2",
        "question": "What is this mainly about?",
        "options": ["A", "B", "C", "D"],
        "correct_index": 0,
        "audio_text": "A private transcript that must never reach the client.",
        "audio_url": "/uploads/language_exam_audio/test-clip.wav",
        "question_token": "question-type-test-token-0001",
    }
    item.update(overrides)
    return item


# 1. A current Listening question appears in the state response with question_type == "mcq".
async def test_listening_item_exposes_mcq_question_type():
    item = _listening_item(question_type="mcq")
    sess = _session(section="listening", item=item)
    out = await _build_state_out(None, sess)
    assert out.mcq is not None
    assert out.mcq.question_type == "mcq"


# 2. Reading and Grammar/Vocab prompts remain compatible with the same schema.
@pytest.mark.parametrize("section", ["reading", "grammar_vocab"])
async def test_reading_and_grammar_vocab_items_expose_mcq_question_type(section):
    item = {
        "level": "A2",
        "question": "Choose the best option.",
        "options": ["A", "B", "C", "D"],
        "correct_index": 1,
        "passage": "A short reading passage." if section == "reading" else "",
        "question_token": f"question-type-test-token-{section}",
        "question_type": "mcq",
    }
    sess = _session(section=section, item=item)
    out = await _build_state_out(None, sess)
    assert out.mcq is not None
    assert out.mcq.question_type == "mcq"


# 3. An older internal item dict without a question_type key returns question_type == "mcq".
async def test_item_without_question_type_key_defaults_to_mcq():
    item = _listening_item()
    assert "question_type" not in item
    sess = _session(section="listening", item=item)
    out = await _build_state_out(None, sess)
    assert out.mcq is not None
    assert out.mcq.question_type == "mcq"


# 4. An item explicitly containing question_type = "mcq" preserves that value.
async def test_item_with_explicit_mcq_question_type_is_preserved():
    item = _listening_item(question_type="mcq")
    sess = _session(section="listening", item=item)
    out = await _build_state_out(None, sess)
    assert out.mcq.question_type == "mcq"


# 5. The state response still does not expose correct_index.
# 6. The state response still does not expose the Listening transcript or audio_text.
async def test_state_response_still_hides_correct_index_and_transcript():
    item = _listening_item(question_type="mcq")
    sess = _session(section="listening", item=item)
    out = await _build_state_out(None, sess)
    encoded = out.model_dump_json()
    assert "correct_index" not in encoded
    assert "private transcript" not in encoded.lower()
    assert out.mcq.question_type == "mcq"
