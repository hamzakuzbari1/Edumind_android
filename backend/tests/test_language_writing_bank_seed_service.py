from __future__ import annotations

import json

import pytest

from app.services.language_writing_bank_seed_service import (
    DEFAULT_DRAFT_PATH,
    EXPECTED_WORD_RANGES,
    build_dry_run_summary,
)


_requires_real_draft = pytest.mark.skipif(
    not DEFAULT_DRAFT_PATH.exists(), reason="backend/content_drafts/ is not present in this test environment"
)


@_requires_real_draft
def test_real_writing_draft_has_60_valid_prompts():
    summary = build_dry_run_summary()

    assert summary.errors == []
    assert summary.total_parsed == 60
    assert summary.distribution == {level: 10 for level in EXPECTED_WORD_RANGES}


@_requires_real_draft
def test_real_writing_draft_has_level_word_ranges():
    summary = build_dry_run_summary()

    for candidate in summary.candidates:
        assert (candidate.target_min_words, candidate.target_max_words) == EXPECTED_WORD_RANGES[candidate.level]


def _one_prompt_draft(path):
    path.write_text(
        json.dumps(
            {
                "writing_prompts": [
                    {
                        "stable_key": "writing_mvp_v1_A1_01",
                        "level": "A1",
                        "task_type": "short_message",
                        "prompt": "Write a short message (30-50 words) to a classmate about your favorite place.",
                        "target_min_words": 30,
                        "target_max_words": 50,
                        "rubric_focus": ["task_response", "basic_sentence_control"],
                        "expected_language_features": ["present simple", "basic adjectives"],
                        "student_instructions": "Write in English. Stay on topic. Do not use bullet points.",
                        "review_status": "draft",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return path


def test_single_prompt_draft_can_skip_batch_total_enforcement(tmp_path):
    draft_path = _one_prompt_draft(tmp_path / "writing.json")
    summary = build_dry_run_summary(draft_path, enforce_batch_totals=False)

    assert summary.errors == []
    assert len(summary.candidates) == 1
    assert summary.candidates[0].body_json["target_min_words"] == 30
    assert summary.candidates[0].body_json["target_max_words"] == 50
