"""End-to-end placement exam coverage across student profiles.

These tests exercise the real exam endpoints for a complete attempt and the final evaluator's
level placement for weak/medium/strong evidence snapshots. AI/STT calls are mocked so the
placement logic stays deterministic.
"""

from __future__ import annotations

import copy
import hashlib
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.api import language_exam
from app.models.language.analytics import LanguageAnalytics
from app.models.language.exam import LanguageExamSession
from app.schemas.language_exam import (
    CEFRLevel,
    ExamNarrativeSchema,
    SpeakingGradeSchema,
    SpeakingTurnAssessment,
    WritingGradeSchema,
)
from tests.test_language_exam_api_integration import (
    _clear_exam_overrides,
    _install_exam_overrides,
    _seed_session,
)


def _words(prefix: str, count: int) -> str:
    return " ".join(f"{prefix}{idx}" for idx in range(count))


def _listening_item(level: str, token: str, *, correct_index: int = 0) -> dict:
    return {
        "level": level,
        "question": f"{level} listening question",
        "options": ["Correct answer", "Wrong answer"],
        "correct_index": correct_index,
        "audio_url": f"/uploads/language_exam_audio/{level.lower()}-test.wav",
        "question_token": token,
    }


def _reading_bundle(level: str, token: str) -> dict:
    return {
        "level": level,
        "question_type": "mcq",
        "passage": (
            f"This is a {level} reading passage. It has a clear main idea, a detail, "
            "one word to infer from context, and one sentence that tests purpose."
        ),
        "question": "Answer the questions about the passage.",
        "options": [],
        "question_token": token,
        "body": {
            "placement_metrics": {
                "subskill": "mixed_comprehension",
                "word_count": 34 + len(level),
                "avg_sentence_words": 11.5,
            }
        },
        "subquestions": [
            {
                "question": "What is the main idea?",
                "options": ["Correct main idea", "Wrong detail"],
                "correct_index": 0,
                "response_type": "mcq",
                "subskill": "main_idea",
            },
            {
                "question": "Which detail is mentioned?",
                "options": ["Correct detail", "Wrong detail"],
                "correct_index": 0,
                "response_type": "mcq",
                "subskill": "detail",
            },
            {
                "question": "Complete the phrase.",
                "accepted_answers": ["clear"],
                "max_words": 2,
                "case_sensitive": False,
                "response_type": "gap_fill",
                "word_bank": ["clear", "late", "heavy"],
                "subskill": "vocabulary_in_context",
            },
            {
                "question": "Match the ideas.",
                "matching_items": ["purpose", "support"],
                "match_options": ["to explain", "to support"],
                "correct_indices": [0, 1],
                "response_type": "matching",
                "subskill": "inference",
            },
        ],
    }


def _adaptive_section(skill: str, levels: list[str], *, start: str, max_steps: int) -> dict:
    pool = {}
    for level in levels:
        token = f"{skill}-{level.lower()}-question-token-0001"
        pool[level] = (
            _reading_bundle(level, token)
            if skill == "reading"
            else _listening_item(level, token)
        )
    return {
        "mode": "adaptive",
        "pool": pool,
        "current_level": start,
        "start_level": start,
        "asked": [],
        "max_steps": max_steps,
        "ready": True,
        "done": False,
        "evidence_status": "missing_student_response",
    }


def _full_attempt_state() -> dict:
    return {
        "version": 3,
        "state_revision": 1,
        "sections": ["speaking", "listening", "reading", "writing"],
        "cursor": 0,
        "request_receipts": [],
        "speaking": {
            "scenario": {"scenario": "School help desk", "setting": "A student asks for help."},
            "pending_question": "Tell me what you need help with today.",
            "turn_token": "speaking-turn-token-0001",
            "turn": 1,
            "total_turns": 3,
            "results": [],
            "ready": True,
            "done": False,
            "evidence_status": "missing_student_response",
        },
        "listening": _adaptive_section(
            "listening", ["A2", "B1", "B2"], start="A2", max_steps=3
        ),
        "reading": _adaptive_section("reading", ["A2", "B1", "B2"], start="A2", max_steps=3),
        "writing": {
            "ready": True,
            "prompt": "Write an email to a teacher about a class project. Write 50-80 words.",
            "prompt_token": "writing-task-token-0001",
            "min_words": 50,
            "max_words": 80,
            "task_index": 1,
            "task_total": 2,
            "task_type": "email",
            "route": "anchor",
            "tasks": [
                {
                    "prompt": "Write an email to a teacher about a class project. Write 50-80 words.",
                    "min_words": 50,
                    "max_words": 80,
                    "task_type": "email",
                    "route": "anchor",
                }
            ],
            "response": None,
            "done": False,
            "evidence_status": "missing_student_response",
        },
    }


def _completed_state(
    reading_pattern: list[tuple[str, bool]],
    listening_pattern: list[tuple[str, bool]],
    *,
    writing_route: str = "B1_B2",
) -> dict:
    state = _full_attempt_state()
    state["cursor"] = len(state["sections"])
    for idx in range(3):
        state["speaking"]["results"].append(
            {
                "question": f"Speaking question {idx + 1}",
                "transcription": f"Student response {idx + 1} with enough words for verified evidence.",
                "grammar_vocab_feedback": "Clear enough.",
                "fluency_note": "Connected response.",
                "estimated_level": "B1",
                "audio_sha256": hashlib.sha256(f"audio-{idx}".encode()).hexdigest(),
                "audio_duration_seconds": 12.0,
                "audio_mime_type": "audio/wav",
                "stt_engine": "test",
                "stt_model": "test-stt",
            }
        )
    state["speaking"]["done"] = True
    state["speaking"]["pending_question"] = ""
    state["speaking"]["turn_token"] = ""
    state["speaking"]["evidence_status"] = "completed"

    state["listening"]["asked"] = [
        {
            "level": level,
            "chosen_index": 0 if correct else 1,
            "correct": correct,
            "bank_item_id": None,
        }
        for level, correct in listening_pattern
    ]
    state["listening"]["done"] = True
    state["listening"]["evidence_status"] = "completed"

    state["reading"]["asked"] = [
        {
            "level": level,
            "question_type": "mcq",
            "question_count": 4,
            "subquestion_answers": [0, 0, "clear", [0, 1]] if correct else [1, 1, "late", [1, 0]],
            "sub_correct": [correct, correct, correct, correct],
            "subskills": ["main_idea", "detail", "vocabulary_in_context", "inference"],
            "subskill": "mixed_comprehension",
            "word_count": 80,
            "avg_sentence_words": 12.0,
            "correct": correct,
            "bank_item_id": None,
        }
        for level, correct in reading_pattern
    ]
    state["reading"]["done"] = True
    state["reading"]["evidence_status"] = "completed"

    task1 = {
        "prompt": "Write an email to a teacher about a class project. Write 50-80 words.",
        "response": _words("taskone", 60),
        "min_words": 50,
        "max_words": 80,
        "task_type": "email",
        "route": "anchor",
    }
    task2 = {
        "prompt": "Explain your opinion about a school rule. Write 120-160 words.",
        "response": _words("tasktwo", 130),
        "min_words": 120,
        "max_words": 160,
        "task_type": "opinion_paragraph",
        "route": writing_route,
    }
    state["writing"].update(
        {
            "tasks": [task1, task2],
            "task_index": 2,
            "task_total": 2,
            "prompt": task2["prompt"],
            "prompt_token": "writing-task-token-0002",
            "min_words": 120,
            "max_words": 160,
            "task_type": task2["task_type"],
            "route": task2["route"],
            "response": f"{task1['response']}\n\n{task2['response']}",
            "done": True,
            "evidence_status": "completed",
        }
    )
    state["evaluation"] = {
        "evaluation_status": "pending",
        "evaluation_started_at": None,
        "evaluation_lease_expires_at": None,
        "evaluation_attempt": 0,
        "evaluation_owner": None,
    }
    return state


def _speaking_grade(level: CEFRLevel, score: float) -> SpeakingGradeSchema:
    return SpeakingGradeSchema(
        level=level,
        fluency=score,
        lexical=score,
        grammar=score,
        pronunciation=0.0,
        score=score,
        feedback=f"Speaking placed at {level.value}.",
        detected_errors=[],
    )


def _writing_grade(level: CEFRLevel, score: float, *, route: str = "B1_B2") -> WritingGradeSchema:
    return WritingGradeSchema(
        level=level,
        task_achievement=score,
        coherence=score,
        lexical=score,
        grammar=score,
        task_fulfillment=score,
        communicative_achievement=score,
        organization=score,
        vocabulary=score,
        spelling_punctuation=score,
        score=score,
        feedback=f"Writing placed at {level.value}.",
        detected_errors=[],
    )


def _narrative(label: str) -> ExamNarrativeSchema:
    return ExamNarrativeSchema(
        summary=f"{label} placement summary.",
        strengths=["Uses understandable English."],
        weaknesses=["Needs targeted practice."],
        recommendations=["Read graded texts.", "Practise listening daily.", "Write short answers."],
        detected_errors=[],
        recommended_starting_lesson_topic="Placement follow-up lesson",
    )


async def _stored_session(postgres_session_factory, session_id: str) -> LanguageExamSession:
    async with postgres_session_factory() as db:
        return await db.get(LanguageExamSession, session_id)


async def _stored_analytics(postgres_session_factory, student_id: int, language_id: int) -> LanguageAnalytics:
    async with postgres_session_factory() as db:
        return (
            await db.execute(
                select(LanguageAnalytics).where(
                    LanguageAnalytics.student_id == student_id,
                    LanguageAnalytics.language_id == language_id,
                )
            )
        ).scalar_one()


def _install_successful_final_graders(monkeypatch, *, level: CEFRLevel, score: float) -> None:
    async def grade_speaking(**_kwargs) -> SpeakingGradeSchema:
        return _speaking_grade(level, score)

    async def grade_writing(**_kwargs) -> WritingGradeSchema:
        return _writing_grade(level, score)

    async def build_final_narrative(**_kwargs) -> ExamNarrativeSchema:
        return _narrative(level.value)

    monkeypatch.setattr(language_exam.ai_engine, "grade_speaking", grade_speaking)
    monkeypatch.setattr(language_exam.ai_engine, "grade_writing", grade_writing)
    monkeypatch.setattr(language_exam.ai_engine, "build_final_narrative", build_final_narrative)


@pytest.mark.integration
@pytest.mark.postgresql
async def test_full_exam_student_attempt_advances_through_all_sections_and_completes_report(
    api_client, asgi_app, postgres_session_factory, monkeypatch
):
    state = _full_attempt_state()
    student_id, language_id, session_id = await _seed_session(postgres_session_factory, state)
    monkeypatch.setattr(language_exam, "AsyncSessionLocal", postgres_session_factory)
    monkeypatch.setattr(language_exam, "check", lambda *_args, **_kwargs: True)
    _install_successful_final_graders(monkeypatch, level=CEFRLevel.B1, score=5.6)

    audio_counter = 0

    async def read_audio(_file):
        nonlocal audio_counter
        audio_counter += 1
        return SimpleNamespace(
            data=b"test-audio",
            suffix=".wav",
            sha256=hashlib.sha256(f"full-flow-audio-{audio_counter}".encode()).hexdigest(),
            duration_seconds=12.0,
            mime_type="audio/wav",
        )

    async def transcribe(_audio):
        return SimpleNamespace(
            text="I need help with my school project and I can explain my ideas clearly.",
            engine="test",
            model="test-stt",
            meta={},
        )

    async def assess_speaking(**_kwargs) -> SpeakingTurnAssessment:
        return SpeakingTurnAssessment(
            transcription="I need help with my school project and I can explain my ideas clearly.",
            grammar_vocab_feedback="Mostly clear.",
            pronunciation_feedback="Unassessed.",
            fluency_note="Connected and relevant.",
            estimated_level=CEFRLevel.B1,
            next_question="Tell me one more detail.",
        )

    monkeypatch.setattr(language_exam, "_read_speaking_audio", read_audio)
    monkeypatch.setattr(language_exam, "_verified_server_transcription", transcribe)
    monkeypatch.setattr(language_exam.ai_engine, "assess_speaking", assess_speaking)

    dependencies = _install_exam_overrides(asgi_app, postgres_session_factory, student_id=student_id)
    try:
        current = (await api_client.get(f"/api/student/languages/exam/{session_id}/state")).json()
        assert current["phase"] == "speaking"

        for turn in range(1, 4):
            response = await api_client.post(
                f"/api/student/languages/exam/{session_id}/speaking/turn",
                data={
                    "request_id": f"full-speaking-turn-{turn:04d}",
                    "state_revision": str(current["state_revision"]),
                    "turn_token": current["turn_token"],
                    "section": "speaking",
                },
                files={"file": ("answer.wav", b"RIFF....WAVE", "audio/wav")},
            )
            assert response.status_code == 200
            current = response.json()

        assert current["phase"] == "listening"
        assert current["mcq"]["audio_url"]
        for answer_idx in range(3):
            response = await api_client.post(
                f"/api/student/languages/exam/{session_id}/answer",
                json={
                    "choice_index": 0,
                    "request_id": f"full-listening-{answer_idx:04d}",
                    "state_revision": current["state_revision"],
                    "question_token": current["question_token"],
                    "section": "listening",
                },
            )
            assert response.status_code == 200
            current = response.json()

        assert current["phase"] == "reading"
        assert current["mcq"]["subquestions"] and len(current["mcq"]["subquestions"]) == 4
        for answer_idx in range(3):
            response = await api_client.post(
                f"/api/student/languages/exam/{session_id}/answer",
                json={
                    "subquestion_answers": [0, 0, "clear", [0, 1]],
                    "request_id": f"full-reading-{answer_idx:04d}",
                    "state_revision": current["state_revision"],
                    "question_token": current["question_token"],
                    "section": "reading",
                },
            )
            assert response.status_code == 200
            current = response.json()

        assert current["phase"] == "writing"
        assert current["writing"]["task_index"] == 1
        assert current["writing"]["task_total"] == 2
        response = await api_client.post(
            f"/api/student/languages/exam/{session_id}/writing",
            json={
                "text": _words("firsttask", 60),
                "request_id": "full-writing-task-0001",
                "state_revision": current["state_revision"],
                "prompt_token": current["prompt_token"],
            },
        )
        assert response.status_code == 200
        current = response.json()
        assert current["phase"] == "writing"
        assert current["writing"]["task_index"] == 2
        assert current["writing"]["task_total"] == 2
        assert current["prompt_token"] != "writing-task-token-0001"

        response = await api_client.post(
            f"/api/student/languages/exam/{session_id}/writing",
            json={
                "text": _words("secondtask", 130),
                "request_id": "full-writing-task-0002",
                "state_revision": current["state_revision"],
                "prompt_token": current["prompt_token"],
            },
        )
        assert response.status_code == 202
    finally:
        _clear_exam_overrides(asgi_app, dependencies)

    stored = await _stored_session(postgres_session_factory, session_id)
    if stored.status != "completed":
        await language_exam._run_evaluation(session_id)
        stored = await _stored_session(postgres_session_factory, session_id)

    assert stored.status == "completed"
    assert stored.is_completed is True
    report = stored.assessment_report
    assert report["overall_level"] == "B1"
    assert report["speaking_level"] == "B1"
    assert report["writing_level"] == "B1"
    assert report["listening_level"] == "B2"
    assert report["reading_level"] == "B2"
    assert report["writing_breakdown"]["weights"] == [0.35, 0.65]
    assert len(report["writing_breakdown"]["tasks"]) == 2
    assert report["reading_breakdown"]["items_answered"] == 3

    analytics = await _stored_analytics(postgres_session_factory, student_id, language_id)
    assert analytics.overall_level_internal.value == "B1"
    assert analytics.primary_focus_skill in {"speaking", "writing"}


@pytest.mark.integration
@pytest.mark.postgresql
@pytest.mark.parametrize(
    ("reading_pattern", "listening_pattern", "writing_route", "grade_level", "grade_score", "expected"),
    [
        (
            [("A1", False), ("A2", False), ("B1", False)],
            [("A1", False), ("A2", False), ("B1", False)],
            "A1_A2",
            CEFRLevel.A1,
            2.5,
            {"reading": "A1", "listening": "A1", "writing": "A1", "speaking": "A1", "overall": "A1"},
        ),
        (
            [("A2", True), ("B1", True), ("B2", False)],
            [("A2", True), ("B1", True), ("B2", False)],
            "B1_B2",
            CEFRLevel.B1,
            5.6,
            {"reading": "B1", "listening": "B1", "writing": "B1", "speaking": "B1", "overall": "B1"},
        ),
        (
            [("B1", True), ("B2", True), ("C1", True), ("C2", False)],
            [("B1", True), ("B2", True), ("C1", True), ("C2", False)],
            "C1_C2",
            CEFRLevel.C1,
            8.4,
            {"reading": "C1", "listening": "C1", "writing": "C1", "speaking": "C1", "overall": "C1"},
        ),
    ],
)
async def test_completed_exam_evaluation_places_expected_levels_for_student_profiles(
    postgres_session_factory,
    monkeypatch,
    reading_pattern,
    listening_pattern,
    writing_route,
    grade_level,
    grade_score,
    expected,
):
    state = _completed_state(reading_pattern, listening_pattern, writing_route=writing_route)
    student_id, language_id, session_id = await _seed_session(
        postgres_session_factory, copy.deepcopy(state), status="evaluating"
    )
    monkeypatch.setattr(language_exam, "AsyncSessionLocal", postgres_session_factory)
    monkeypatch.setattr(language_exam, "check", lambda *_args, **_kwargs: True)
    _install_successful_final_graders(monkeypatch, level=grade_level, score=grade_score)

    await language_exam._run_evaluation(session_id)

    stored = await _stored_session(postgres_session_factory, session_id)
    assert stored.status == "completed"
    assert stored.is_completed is True
    report = stored.assessment_report
    assert report["reading_level"] == expected["reading"]
    assert report["listening_level"] == expected["listening"]
    assert report["writing_level"] == expected["writing"]
    assert report["speaking_level"] == expected["speaking"]
    assert report["overall_level"] == expected["overall"]
    assert report["summary"] == f"{grade_level.value} placement summary."
    assert report["unassessed_components"] == ["speaking.pronunciation"]

    analytics = await _stored_analytics(postgres_session_factory, student_id, language_id)
    assert analytics.reading_level.value == expected["reading"]
    assert analytics.listening_level.value == expected["listening"]
    assert analytics.writing_level.value == expected["writing"]
    assert analytics.speaking_level.value == expected["speaking"]
    assert analytics.overall_level_internal.value == expected["overall"]
