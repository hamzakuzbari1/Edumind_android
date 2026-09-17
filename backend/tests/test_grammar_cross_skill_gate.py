from __future__ import annotations

import asyncio

import pytest

from app.services.language_grammar.enums import (
    GrammarEvidenceSourceSkill,
    GrammarMasteryState,
    GrammarObservationType,
)
from app.services.language_grammar_catalog.catalog import get_default_catalog
from app.services.language_grammar_evidence.types import GrammarEvidenceObservation
from app.services.language_grammar_mastery.engine import apply_observations, empty_snapshot
from app.services.language_grammar_mastery.service import completion_ready_ids
from app.services.language_grammar_integrity.attested_completion import resolve_server_score
from app.services.language_grammar_integrity.errors import GrammarIntegrityError


def _obs(
    skill: GrammarEvidenceSourceSkill,
    index: int,
    *,
    score: float = 100.0,
    attempt_count: int = 1,
    correct_count: int = 1,
) -> GrammarEvidenceObservation:
    return GrammarEvidenceObservation(
        observation_id=f"gate_{skill.value}_{index}",
        grammar_id="gram_be_present",
        context=f"gate:{skill.value}:{index}",
        attempt_count=attempt_count,
        correct_count=correct_count,
        observation_type=GrammarObservationType.summative,
        source_skill=skill,
        student_id=1001,
        language_id=1,
        observed_at=f"2026-01-01T00:00:{index:02d}Z",
        confidence=1.0,
        understanding_signal=score,
        accuracy_signal=score,
        fluency_signal=score,
        retention_signal=score,
        score=score,
    )


def _apply(*observations: GrammarEvidenceObservation):
    return apply_observations(
        empty_snapshot(student_id=1001, language_id=1),
        tuple(observations),
        catalog=get_default_catalog(),
    )


def test_grammar_topic_is_not_completed_until_all_four_skills_pass():
    snapshot = _apply(
        _obs(GrammarEvidenceSourceSkill.grammar_lesson, 1, attempt_count=14, correct_count=14),
        _obs(GrammarEvidenceSourceSkill.reading, 2),
        _obs(GrammarEvidenceSourceSkill.listening, 3),
        _obs(GrammarEvidenceSourceSkill.writing, 4),
    )
    record = snapshot.record_for("gram_be_present")

    assert record is not None
    assert record.state is not GrammarMasteryState.mastered
    assert completion_ready_ids(snapshot) == ()

    completed = apply_observations(
        snapshot,
        (_obs(GrammarEvidenceSourceSkill.speaking, 5),),
        catalog=get_default_catalog(),
    )

    assert completed.record_for("gram_be_present").state is GrammarMasteryState.mastered
    assert completion_ready_ids(completed) == ("gram_be_present",)


def test_grammar_topic_requires_full_fourteen_of_fourteen_grammar_practice():
    snapshot = _apply(
        _obs(GrammarEvidenceSourceSkill.grammar_lesson, 1, attempt_count=14, correct_count=13, score=92.8),
        _obs(GrammarEvidenceSourceSkill.reading, 2),
        _obs(GrammarEvidenceSourceSkill.listening, 3),
        _obs(GrammarEvidenceSourceSkill.writing, 4),
        _obs(GrammarEvidenceSourceSkill.speaking, 5),
    )
    record = snapshot.record_for("gram_be_present")

    assert record is not None
    assert record.state is not GrammarMasteryState.mastered
    assert completion_ready_ids(snapshot) == ()


def test_failed_writing_transfer_blocks_next_grammar_after_full_grammar_practice():
    snapshot = _apply(
        _obs(GrammarEvidenceSourceSkill.grammar_lesson, 1, attempt_count=14, correct_count=14),
        _obs(GrammarEvidenceSourceSkill.reading, 2),
        _obs(GrammarEvidenceSourceSkill.listening, 3),
        _obs(GrammarEvidenceSourceSkill.speaking, 4),
        _obs(GrammarEvidenceSourceSkill.writing, 5, score=40.0),
    )
    record = snapshot.record_for("gram_be_present")

    assert record is not None
    assert record.state is not GrammarMasteryState.mastered
    assert completion_ready_ids(snapshot) == ()

    recovered = apply_observations(
        snapshot,
        (_obs(GrammarEvidenceSourceSkill.writing, 6, score=70.0),),
        catalog=get_default_catalog(),
    )

    assert recovered.record_for("gram_be_present").state is GrammarMasteryState.mastered
    assert completion_ready_ids(recovered) == ("gram_be_present",)


def test_grammar_lesson_completion_score_requires_all_fourteen_correct():
    payload = {
        "practice_item_count": 14,
        "answer_key": {
            f"practice_{idx}": {"expected": [f"answer {idx}"], "task_type": "multiple_choice"}
            for idx in range(14)
        },
    }
    correct_answers = {f"practice_{idx}": f"answer {idx}" for idx in range(14)}
    wrong_answers = {**correct_answers, "practice_3": "wrong"}

    result = asyncio.run(
        resolve_server_score(
            skill="grammar_lesson",
            server_payload=payload,
            answers=correct_answers,
            response_text="",
            server_score=None,
        )
    )

    assert result.score == 100.0
    assert result.attempt_count == 14
    assert result.correct_count == 14

    with pytest.raises(GrammarIntegrityError) as exc:
        asyncio.run(
            resolve_server_score(
                skill="grammar_lesson",
                server_payload=payload,
                answers=wrong_answers,
                response_text="",
                server_score=None,
            )
        )

    assert exc.value.code == "grammar_practice_not_complete"
