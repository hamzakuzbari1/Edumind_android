"""Real PostgreSQL concurrency coverage for the placement exam state protocol.

These tests deliberately use independent ``AsyncSession`` instances.  Mocks are limited to
external audio/STT/AI work; row locking, JSONB writes, and endpoint state validation all execute
against the dedicated PostgreSQL test database.
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
import pytest_asyncio
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm.attributes import flag_modified

from app.api import language_exam
from app.models.language.analytics import LanguageAnalytics
from app.models.language.catalog import Language
from app.models.language.enums import LanguageLevel
from app.models.language.exam import LanguageExamSession
from app.models.language.profile import LanguageStudentProfile
from app.models.language.question_bank import LanguagePlacementQuestionBankItem
from app.models.user import User, UserRole
from app.schemas.language_exam import (
    CEFRLevel,
    ExamNarrativeSchema,
    McqAnswerIn,
    SpeakingGradeSchema,
    SpeakingTurnAssessment,
    WritingGradeSchema,
)
from app.services import language_exam_service
from app.services.language_audio_security_service import ValidatedAudio
from app.services.language_exam_service import ExamAIError
from app.services.language_placement_question_bank_service import select_placement_bank_items
from app.services.language_transcription_service import ConversationTranscription


pytestmark = [pytest.mark.postgresql, pytest.mark.concurrency]
_READING_MVP_SOURCE = "reading_mvp_v1_draft"


def _reading_bank_bundle_body() -> dict:
    return {
        "review_status": "mvp_approved_pending_full_review",
        "human_reviewed": False,
        "placement_metrics": {"subskill": "mixed_comprehension", "word_count": 42},
        "subquestions": [
            {
                "question": "What is the main idea?",
                "options": ["Correct answer", "Wrong answer", "Another wrong answer", "Not given"],
                "correct_index": 0,
                "response_type": "mcq",
                "subskill": "main_idea",
            },
            {
                "question": "Which detail is mentioned?",
                "options": ["Correct answer", "Wrong answer", "Another wrong answer", "Not given"],
                "correct_index": 0,
                "response_type": "mcq",
                "subskill": "specific_detail",
            },
            {
                "question": "What can be inferred?",
                "options": ["Correct answer", "Wrong answer", "Another wrong answer", "Not given"],
                "correct_index": 0,
                "response_type": "mcq",
                "subskill": "inference",
            },
            {
                "question": "What is the purpose of the text?",
                "options": ["Correct answer", "Wrong answer", "Another wrong answer", "Not given"],
                "correct_index": 0,
                "response_type": "mcq",
                "subskill": "purpose",
            },
        ],
    }


@pytest_asyncio.fixture
async def exam_record_factory(postgres_session_factory):
    """Create isolated ORM rows and remove every committed row after each test."""

    tracked_sessions: list[str] = []
    tracked_users: list[int] = []
    tracked_languages: list[int] = []

    async def create(*, state: dict, status: str = "in_progress") -> SimpleNamespace:
        marker = uuid.uuid4().hex
        async with postgres_session_factory() as db:
            student = User(
                email=f"placement-concurrency-{marker}@example.test",
                name="Placement concurrency student",
                hashed_password="not-used-in-tests",
                role=UserRole.student,
            )
            language = Language(
                code=f"t{marker[:12]}",
                name_en=f"Test language {marker[:8]}",
                name_ar=f"Test language {marker[:8]}",
                is_active=True,
            )
            db.add_all([student, language])
            await db.flush()

            exam = LanguageExamSession(
                id=uuid.uuid4().hex,
                student_id=student.id,
                language_id=language.id,
                current_step=1,
                max_steps=max(1, len(state.get("sections") or [])),
                exam_state=copy.deepcopy(state),
                status=status,
                is_completed=False,
            )
            db.add(exam)
            await db.commit()

            tracked_sessions.append(exam.id)
            tracked_users.append(student.id)
            tracked_languages.append(language.id)
            return SimpleNamespace(
                session_id=exam.id,
                student_id=student.id,
                language_id=language.id,
                student=SimpleNamespace(id=student.id),
            )

    yield create

    async with postgres_session_factory() as db:
        if tracked_users and tracked_languages:
            await db.execute(
                delete(LanguageAnalytics).where(
                    LanguageAnalytics.student_id.in_(tracked_users),
                    LanguageAnalytics.language_id.in_(tracked_languages),
                )
            )
            await db.execute(
                delete(LanguageStudentProfile).where(
                    LanguageStudentProfile.student_id.in_(tracked_users),
                    LanguageStudentProfile.language_id.in_(tracked_languages),
                )
            )
        if tracked_users:
            # Concurrent initiate creates an additional session after the factory returns, so
            # clean by owned student as well as by the factory's initially tracked ids.
            await db.execute(
                delete(LanguageExamSession).where(
                    LanguageExamSession.student_id.in_(tracked_users)
                )
            )
        elif tracked_sessions:
            await db.execute(
                delete(LanguageExamSession).where(LanguageExamSession.id.in_(tracked_sessions))
            )
        if tracked_users:
            await db.execute(delete(User).where(User.id.in_(tracked_users)))
        if tracked_languages:
            await db.execute(delete(Language).where(Language.id.in_(tracked_languages)))
        await db.commit()


def _preparing_state(*, revision: int = 3, prep_token: str = "prep-token-0000000000000001") -> dict:
    return {
        "version": 3,
        "state_revision": revision,
        "sections": ["speaking", "listening", "reading", "grammar_vocab", "writing"],
        "cursor": 0,
        "content_prep_token": prep_token,
        "content_prep_status": "preparing",
        "speaking": {
            "turn": 1,
            "total_turns": 3,
            "pending_question": "Tell me about your day.",
            "turn_token": "speaking-token-00000000000001",
            "results": [],
            "done": False,
            "evidence_status": "missing_student_response",
        },
        "listening": {"ready": False, "done": False, "asked": [], "pool": {}},
        "reading": {"ready": False, "done": False, "asked": [], "pool": {}},
        "grammar_vocab": {"ready": False, "done": False, "asked": [], "pool": {}},
        "writing": {"ready": False, "done": False, "response": None},
        "request_receipts": [],
    }


def _speaking_done_preparing_state(
    *, revision: int = 3, prep_token: str = "prep-token-0000000000000001"
) -> dict:
    """Mirrors _preparing_state() but with Speaking already completed (3/3) and the cursor
    advanced to listening -- the exact transition point where manual QA observed Listening's
    'This section is temporarily unavailable' after Speaking."""
    return {
        "version": 3,
        "state_revision": revision,
        "sections": ["speaking", "listening", "reading", "grammar_vocab", "writing"],
        "cursor": 1,
        "content_prep_token": prep_token,
        "content_prep_status": "preparing",
        "speaking": {
            "turn": 4,
            "total_turns": 3,
            "pending_question": "",
            "turn_token": "",
            "results": [
                {"question": "Q1", "transcription": "A1", "bank_item_id": 101, "estimated_level": "A2"},
                {"question": "Q2", "transcription": "A2", "bank_item_id": 102, "estimated_level": "A2"},
                {"question": "Q3", "transcription": "A3", "bank_item_id": 103, "estimated_level": "A2"},
            ],
            "done": True,
            "evidence_status": "completed",
        },
        "listening": {"ready": False, "done": False, "asked": [], "pool": {}},
        "reading": {"ready": False, "done": False, "asked": [], "pool": {}},
        "grammar_vocab": {"ready": False, "done": False, "asked": [], "pool": {}},
        "writing": {"ready": False, "done": False, "response": None},
        "request_receipts": [],
    }


async def _stored_exam(postgres_session_factory, session_id: str) -> LanguageExamSession:
    async with postgres_session_factory() as db:
        return (
            await db.execute(
                select(LanguageExamSession).where(LanguageExamSession.id == session_id)
            )
        ).scalar_one()


async def _wait_until_blocked(task: asyncio.Task, *, delay: float = 0.08) -> None:
    """Give PostgreSQL enough time to place the second actor behind the held row lock."""

    await asyncio.sleep(delay)
    assert not task.done(), "the second transaction unexpectedly bypassed the row lock"


def _install_fast_content_preparation(monkeypatch) -> None:
    """Replace content sources, not the PostgreSQL state/merge path, with deterministic data."""

    async def question_pool(_db, *, skill, **_kwargs):
        item = {
            "level": "A2",
            "question": f"Prepared {skill} question?",
            "options": ["one", "two"],
            "correct_index": 0,
        }
        if skill == "reading":
            item["passage"] = "A prepared reading passage."
        if skill == "listening":
            item["audio_url"] = "/language-assets/en/placement/listening/test.wav"
        return {"A2": item}

    async def empty_pool(*_args, **_kwargs):
        return {}

    async def writing_prompt(*_args, **_kwargs):
        return "Write about a memorable day."

    async def no_generated_content(**_kwargs):
        return {"items": []}

    monkeypatch.setattr(language_exam, "check", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(language_exam, "_question_bank_pool", question_pool)
    monkeypatch.setattr(language_exam, "_seeded_pool", empty_pool)
    monkeypatch.setattr(language_exam, "_generated_pool", empty_pool)
    monkeypatch.setattr(language_exam, "_writing_prompt", writing_prompt)
    monkeypatch.setattr(
        language_exam.ai_engine,
        "generate_comprehension_set",
        no_generated_content,
    )


async def test_prepare_content_preserves_concurrent_speaking_evidence(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    state = _preparing_state()
    record = await exam_record_factory(state=state)
    monkeypatch.setattr(language_exam, "AsyncSessionLocal", postgres_session_factory)
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(language_exam, "_effective_level", lambda *_args, **_kwargs: _async("A2"))
    _install_fast_content_preparation(monkeypatch)

    speaker_locked = asyncio.Event()
    release_speaker = asyncio.Event()
    evidence_bytes = b"server-verified-speaking-evidence"
    evidence_hash = hashlib.sha256(evidence_bytes).hexdigest()

    async def fake_read(_file) -> ValidatedAudio:
        return ValidatedAudio(
            data=evidence_bytes,
            mime_type="audio/webm",
            suffix=".webm",
            sha256=evidence_hash,
            duration_seconds=4.0,
        )

    async def fake_transcribe(_audio: ValidatedAudio) -> ConversationTranscription:
        return ConversationTranscription(
            text="I studied and then played football with my friends",
            engine="test-stt",
            model="test-model",
        )

    async def fake_assess(**kwargs) -> SpeakingTurnAssessment:
        return SpeakingTurnAssessment(
            transcription=kwargs["transcript"],
            grammar_vocab_feedback="No material issue.",
            pronunciation_feedback="",
            fluency_note="Coherent response.",
            estimated_level=CEFRLevel.A2,
            next_question="What did you enjoy most?",
        )

    original_load_session = language_exam._load_session

    async def pause_after_speaking_lock(db, session_id, student, *, for_update=False):
        exam = await original_load_session(
            db,
            session_id,
            student,
            for_update=for_update,
        )
        if for_update:
            speaker_locked.set()
            await asyncio.wait_for(release_speaker.wait(), timeout=5)
        return exam

    monkeypatch.setattr(language_exam, "_read_speaking_audio", fake_read)
    monkeypatch.setattr(language_exam, "_verified_server_transcription", fake_transcribe)
    monkeypatch.setattr(language_exam.ai_engine, "assess_speaking", fake_assess)
    monkeypatch.setattr(language_exam, "_load_session", pause_after_speaking_lock)

    async def submit_speaking() -> None:
        async with postgres_session_factory() as db:
            await language_exam.speaking_turn(
                record.session_id,
                BackgroundTasks(),
                file=SimpleNamespace(filename="verified.webm"),
                duration_seconds=None,
                request_id="speaking-request-0001",
                state_revision=state["state_revision"],
                turn_token=state["speaking"]["turn_token"],
                section=None,
                student=record.student,
                db=db,
            )

    speaker_task = asyncio.create_task(submit_speaking())
    await asyncio.wait_for(speaker_locked.wait(), timeout=5)
    prepare_task = asyncio.create_task(
        language_exam._prepare_content(record.session_id, record.language_id, "A2")
    )
    await _wait_until_blocked(prepare_task)
    release_speaker.set()
    await asyncio.wait_for(asyncio.gather(speaker_task, prepare_task), timeout=10)

    stored = await _stored_exam(postgres_session_factory, record.session_id)
    latest = stored.exam_state
    assert latest["speaking"]["results"][0]["audio_sha256"] == evidence_hash
    assert latest["speaking"]["turn"] == 2
    assert latest["speaking"]["turn_token"] != state["speaking"]["turn_token"]
    assert latest["request_receipts"][0]["request_id"] == "speaking-request-0001"
    assert all(latest[section]["ready"] is True for section in language_exam.PREPARED_SECTIONS)
    assert latest["state_revision"] == state["state_revision"] + 2


async def test_prepare_content_cannot_revive_an_abandoned_exam(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    state = _preparing_state(revision=10)
    record = await exam_record_factory(state=state)
    monkeypatch.setattr(language_exam, "AsyncSessionLocal", postgres_session_factory)
    _install_fast_content_preparation(monkeypatch)

    abandon_locked = asyncio.Event()
    release_abandon = asyncio.Event()

    async def abandon_under_lock() -> None:
        async with postgres_session_factory() as db:
            exam = (
                await db.execute(
                    select(LanguageExamSession)
                    .where(LanguageExamSession.id == record.session_id)
                    .with_for_update()
                )
            ).scalar_one()
            abandoned = copy.deepcopy(exam.exam_state or {})
            abandoned["abandoned_at"] = datetime.now(timezone.utc).isoformat()
            language_exam._bump_state_revision(abandoned)
            exam.exam_state = abandoned
            exam.status = "abandoned"
            flag_modified(exam, "exam_state")
            abandon_locked.set()
            await asyncio.wait_for(release_abandon.wait(), timeout=5)
            await db.commit()

    abandon_task = asyncio.create_task(abandon_under_lock())
    await asyncio.wait_for(abandon_locked.wait(), timeout=5)
    prepare_task = asyncio.create_task(
        language_exam._prepare_content(record.session_id, record.language_id, "A2")
    )
    await _wait_until_blocked(prepare_task)
    release_abandon.set()
    await asyncio.wait_for(asyncio.gather(abandon_task, prepare_task), timeout=10)

    stored = await _stored_exam(postgres_session_factory, record.session_id)
    latest = stored.exam_state
    assert stored.status == "abandoned"
    assert latest["abandoned_at"]
    assert latest["state_revision"] == state["state_revision"] + 1
    assert all(latest[section]["ready"] is False for section in language_exam.PREPARED_SECTIONS)


async def test_question_bank_pool_excludes_already_used_bank_item_ids(
    postgres_session_factory,
) -> None:
    """P1.1 mechanism: with a single seeded A2 reading item, passing its own id as
    used_item_ids must make it disappear from the pool — proving the exclusion this call site
    now wires through actually prevents reselection, not just that the parameter exists."""
    marker = uuid.uuid4().hex[:10]
    async with postgres_session_factory() as db:
        language = Language(
            code=f"p11-{marker}",
            name_en="P1.1 test language",
            name_ar="P1.1 test language",
            is_active=True,
        )
        db.add(language)
        await db.flush()
        bank_item = LanguagePlacementQuestionBankItem(
            language_id=language.id,
            skill="reading",
            level=LanguageLevel.A2,
            question_type="mcq",
            prompt_text="What is the main idea?",
            passage="A short passage.",
            options_json=["Correct answer", "Wrong answer", "Another wrong answer", "Not given"],
            correct_index=0,
            body_json=_reading_bank_bundle_body(),
            source=_READING_MVP_SOURCE,
            is_verified=True,
            is_active=True,
        )
        db.add(bank_item)
        await db.commit()
        language_id, bank_item_id = language.id, bank_item.id

    async with postgres_session_factory() as db:
        pool_without_exclusion = await language_exam._question_bank_pool(
            db, language_id=language_id, skill="reading", levels=["A2"]
        )
    assert "A2" in pool_without_exclusion
    assert pool_without_exclusion["A2"]["bank_item_id"] == bank_item_id

    async with postgres_session_factory() as db:
        pool_with_exclusion = await language_exam._question_bank_pool(
            db,
            language_id=language_id,
            skill="reading",
            levels=["A2"],
            used_item_ids={bank_item_id},
        )
    assert "A2" not in pool_with_exclusion


async def test_prepare_content_derives_used_item_ids_from_asked_entries_per_skill(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """P1.1 call-site wiring: _prepare_content must derive used_item_ids from each skill's own
    exam_state[skill]["asked"] entries and pass them into _question_bank_pool. Before this fix
    (used_item_ids not passed at this call site), the spy below would observe None for every
    skill instead of the ids actually recorded in "asked" — failing this exact assertion."""
    captured_used_ids: dict[str, set[int] | None] = {}

    async def spy_question_bank_pool(_db, *, skill, levels, used_item_ids=None, **_kwargs):
        captured_used_ids[skill] = used_item_ids
        return {}

    async def empty_pool(*_args, **_kwargs):
        return {}

    async def writing_prompt(*_args, **_kwargs):
        return "Write about a memorable day."

    async def no_generated_content(**_kwargs):
        return {"items": []}

    monkeypatch.setattr(language_exam, "AsyncSessionLocal", postgres_session_factory)
    monkeypatch.setattr(language_exam, "check", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(language_exam, "_question_bank_pool", spy_question_bank_pool)
    monkeypatch.setattr(language_exam, "_seeded_pool", empty_pool)
    monkeypatch.setattr(language_exam, "_generated_pool", empty_pool)
    monkeypatch.setattr(language_exam, "_writing_prompt", writing_prompt)
    monkeypatch.setattr(language_exam.ai_engine, "generate_comprehension_set", no_generated_content)

    state = _preparing_state()
    state["reading"]["asked"] = [
        {"level": "A2", "correct": True, "chosen_index": 0, "bank_item_id": 42}
    ]
    state["listening"]["asked"] = [
        {"level": "B1", "correct": False, "chosen_index": 1, "bank_item_id": 7}
    ]
    record = await exam_record_factory(state=state)

    await language_exam._prepare_content(record.session_id, record.language_id, "A2")

    assert captured_used_ids["reading"] == {42}
    assert captured_used_ids["listening"] == {7}
    assert captured_used_ids["grammar_vocab"] == set()


async def test_prepare_content_succeeds_for_listening_after_speaking_completes(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """After Speaking finishes (3/3, cursor advanced to listening), content preparation must
    succeed and populate a usable listening pool -- the exact transition point where manual QA
    observed 'This section is temporarily unavailable.'"""
    monkeypatch.setattr(language_exam, "AsyncSessionLocal", postgres_session_factory)
    monkeypatch.setattr(language_exam, "_effective_level", lambda *_args, **_kwargs: _async("A2"))
    _install_fast_content_preparation(monkeypatch)

    state = _speaking_done_preparing_state()
    record = await exam_record_factory(state=state)

    await language_exam._prepare_content(record.session_id, record.language_id, "A2")

    stored = await _stored_exam(postgres_session_factory, record.session_id)
    latest = stored.exam_state
    assert latest["listening"]["ready"] is True
    assert latest["listening"]["pool"]
    assert latest["content_prep_status"] == "completed"
    # Speaking's completed evidence must be untouched by content preparation.
    assert latest["speaking"]["results"] == state["speaking"]["results"]
    assert latest["speaking"]["done"] is True


async def test_prepare_content_rate_limited_marks_content_unavailable_correctly(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """When the placement_generation rate limit is exhausted, content prep must fail closed with
    a structured content_unavailable state (not silently hang or crash) -- this is the exact
    failure observed in manual QA (content_prep_error_code=content_generation_rate_limited)."""
    monkeypatch.setattr(language_exam, "AsyncSessionLocal", postgres_session_factory)
    monkeypatch.setattr(language_exam, "check", lambda *_args, **_kwargs: False)

    state = _speaking_done_preparing_state()
    record = await exam_record_factory(state=state)

    await language_exam._prepare_content(record.session_id, record.language_id, "A2")

    stored = await _stored_exam(postgres_session_factory, record.session_id)
    latest = stored.exam_state
    assert latest["content_prep_status"] == "content_unavailable"
    assert latest["content_prep_error_code"] == "content_generation_rate_limited"
    assert latest["listening"]["evidence_status"] == "content_unavailable"
    # Speaking evidence must remain untouched even on a failed prep attempt.
    assert latest["speaking"]["results"] == state["speaking"]["results"]


async def test_maybe_retrigger_prep_does_not_fire_before_the_debounce_window_elapses(
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """Regression for the root cause behind the Listening 'temporarily unavailable' bug: a
    too-short retry debounce let _maybe_retrigger_prep re-launch _prepare_content while the
    first, genuinely-still-running attempt (up to six sequential TTS calls plus LLM content
    generation) hadn't finished yet -- wasting its work (discarded as stale at merge time) and
    burning an extra hit from the 3-per-300s placement_generation rate limit for no benefit,
    eventually exhausting it. A prep attempt that only just started must not be retriggered."""
    state = _speaking_done_preparing_state()
    state["content_prep_at"] = datetime.now(timezone.utc).isoformat()
    record = await exam_record_factory(state=state)

    async with postgres_session_factory() as db:
        sess = await db.get(LanguageExamSession, record.session_id)
        triggered = language_exam._maybe_retrigger_prep(sess, record.language_id, BackgroundTasks())
        assert triggered is False
        assert sess.exam_state["content_prep_token"] == state["content_prep_token"]


async def test_maybe_retrigger_prep_fires_once_the_debounce_window_has_elapsed(
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """Complementary case: once _PREP_RETRY_AFTER_S has genuinely elapsed (e.g. the background
    task really did die -- server restart mid-generation), the self-heal retrigger must still
    fire so the section can recover without the user needing to abandon the exam."""
    state = _speaking_done_preparing_state()
    stale_at = datetime.now(timezone.utc) - timedelta(seconds=language_exam._PREP_RETRY_AFTER_S + 1)
    state["content_prep_at"] = stale_at.isoformat()
    record = await exam_record_factory(state=state)

    async with postgres_session_factory() as db:
        sess = await db.get(LanguageExamSession, record.session_id)
        triggered = language_exam._maybe_retrigger_prep(sess, record.language_id, BackgroundTasks())
        assert triggered is True
        assert sess.exam_state["content_prep_status"] == "preparing"
        assert sess.exam_state["content_prep_token"] != state["content_prep_token"]
        await db.commit()


async def test_retry_recovers_listening_after_a_transient_preparation_failure(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """End-to-end 'Retry section preparation' recovery: a session stuck in content_unavailable
    (e.g. from a prior rate-limited attempt) must actually resume and succeed once retried --
    proving the retry button is not a dead end, and that Speaking's completed evidence survives
    the whole failure-then-retry cycle untouched."""
    monkeypatch.setattr(language_exam, "AsyncSessionLocal", postgres_session_factory)
    monkeypatch.setattr(language_exam, "_effective_level", lambda *_args, **_kwargs: _async("A2"))

    state = _speaking_done_preparing_state()
    state["content_prep_status"] = "content_unavailable"
    state["content_prep_error_code"] = "content_generation_rate_limited"
    state["content_prep_at"] = (
        datetime.now(timezone.utc) - timedelta(seconds=language_exam._PREP_RETRY_AFTER_S + 1)
    ).isoformat()
    state["listening"]["evidence_status"] = "content_unavailable"
    record = await exam_record_factory(state=state)

    # "Retry section preparation" == GET /state -> _maybe_retrigger_prep (self-heal check).
    async with postgres_session_factory() as db:
        sess = await db.get(LanguageExamSession, record.session_id)
        triggered = language_exam._maybe_retrigger_prep(sess, record.language_id, BackgroundTasks())
        assert triggered is True
        await db.commit()

    # The re-launched background task itself now runs against real (succeeding) content sources.
    _install_fast_content_preparation(monkeypatch)
    await language_exam._prepare_content(record.session_id, record.language_id, "A2")

    stored = await _stored_exam(postgres_session_factory, record.session_id)
    latest = stored.exam_state
    assert latest["listening"]["ready"] is True
    assert latest["content_prep_status"] == "completed"
    # Speaking's completed evidence is preserved across the whole failure+retry cycle.
    assert latest["speaking"]["results"] == state["speaking"]["results"]
    assert latest["speaking"]["done"] is True


async def test_materialize_listening_audio_times_out_gracefully_instead_of_hanging(
    monkeypatch,
) -> None:
    """Root-cause regression: a cold Supertonic engine load observed to take several minutes on
    the very first synthesis of a fresh process (confirmed in production logs: 'Fetching 26
    files... [04:02<...]'). A single slow/hanging TTS call must not block content preparation
    indefinitely -- it must time out and gracefully drop this rung (existing policy: missing audio
    removes the rung instead of exposing its transcript), not hang or raise."""
    monkeypatch.setattr(language_exam, "_LISTENING_TTS_TIMEOUT_S", 0.05)

    async def hanging_synthesize(_text):
        await asyncio.sleep(1)
        return "/uploads/language_exam_audio/should-never-be-used.wav"

    monkeypatch.setattr(language_exam, "synthesize_exam_audio", hanging_synthesize)

    item = {"audio_text": "A slow item.", "level": "A2"}
    audio_url, audio_text, created = await language_exam._materialize_listening_audio(None, item)

    assert audio_url is None
    assert created is False
    assert audio_text == "A slow item."


async def test_maybe_retrigger_prep_clears_stale_evidence_status_and_error_code(
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """Regression for why retry appeared not to work even after the debounce fix: a prior failed
    attempt marks content_prep_error_code and the current section's own evidence_status as
    content_unavailable. Without clearing these on a fresh retrigger, get_state's own `unavailable`
    check (which ORs the per-section evidence_status together with the top-level
    content_prep_status) keeps reporting content_unavailable to the frontend even while a genuinely
    new _prepare_content attempt is running -- silently defeating retry."""
    state = _speaking_done_preparing_state()
    state["content_prep_status"] = "content_unavailable"
    state["content_prep_error_code"] = "content_generation_rate_limited"
    state["content_prep_at"] = (
        datetime.now(timezone.utc) - timedelta(seconds=language_exam._PREP_RETRY_AFTER_S + 1)
    ).isoformat()
    state["listening"]["evidence_status"] = "content_unavailable"
    record = await exam_record_factory(state=state)

    async with postgres_session_factory() as db:
        sess = await db.get(LanguageExamSession, record.session_id)
        triggered = language_exam._maybe_retrigger_prep(sess, record.language_id, BackgroundTasks())
        assert triggered is True
        assert sess.exam_state["content_prep_status"] == "preparing"
        assert "content_prep_error_code" not in sess.exam_state
        assert sess.exam_state["listening"]["evidence_status"] == "retry_required"
        await db.commit()


async def test_repeated_polling_within_debounce_schedules_exactly_one_attempt(
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """'Retry must start one clean preparation attempt, not multiple overlapping attempts' and
    'must not consume rate-limit quota repeatedly due to polling': simulating several /state polls
    landing within the same debounce window (e.g. rapid frontend auto-polling) must only ever
    schedule _prepare_content -- and therefore only ever consume one placement_generation
    rate-limit hit -- once, not once per poll."""
    state = _speaking_done_preparing_state()
    state["content_prep_at"] = (
        datetime.now(timezone.utc) - timedelta(seconds=language_exam._PREP_RETRY_AFTER_S + 1)
    ).isoformat()
    record = await exam_record_factory(state=state)

    results = []
    async with postgres_session_factory() as db:
        sess = await db.get(LanguageExamSession, record.session_id)
        for _ in range(5):
            results.append(language_exam._maybe_retrigger_prep(sess, record.language_id, BackgroundTasks()))
        await db.commit()

    assert results == [True, False, False, False, False]


async def test_stale_prep_token_cannot_overwrite_newer_successful_content(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """'Test that stale content_prep_token attempts cannot overwrite newer successful content':
    an old, superseded _prepare_content attempt (carrying a prep_token that no longer matches the
    session's current content_prep_token, e.g. because a retrigger already took over) must never
    merge its results over already-current data, even if it finishes after the newer attempt has
    already taken over."""
    monkeypatch.setattr(language_exam, "AsyncSessionLocal", postgres_session_factory)
    state = _speaking_done_preparing_state(prep_token="stale-token-0000000000000001")
    record = await exam_record_factory(state=state)

    # Simulate a newer attempt having already taken over before the stale one's work finishes.
    async with postgres_session_factory() as db:
        sess = await db.get(LanguageExamSession, record.session_id)
        new_state = {**sess.exam_state, "content_prep_token": "current-token-0000000000001"}
        sess.exam_state = new_state
        flag_modified(sess, "exam_state")
        await db.commit()

    stale_prepared = {
        "reading": {"ready": True, "pool": {"A2": {"question": "stale"}}},
        "listening": {"ready": True, "pool": {"A2": {"question": "stale", "audio_url": "/x.wav"}}},
        "grammar_vocab": {"ready": True, "pool": {"A2": {"question": "stale"}}},
        "writing": {"prompt": "stale prompt", "ready": True},
    }
    merged = await language_exam._merge_prepared_content(
        session_id=record.session_id,
        prep_token="stale-token-0000000000000001",
        source_revision=state["state_revision"],
        prepared=stale_prepared,
    )
    assert merged is False

    stored = await _stored_exam(postgres_session_factory, record.session_id)
    latest = stored.exam_state
    assert latest["content_prep_token"] == "current-token-0000000000001"
    assert latest["listening"]["ready"] is False
    assert not latest["listening"].get("pool")


def _mcq_state() -> dict:
    return {
        "version": 3,
        "state_revision": 7,
        "sections": ["reading"],
        "cursor": 0,
        "reading": {
            "mode": "adaptive",
            "pool": {
                "A2": {
                    "passage": "A short passage.",
                    "question": "Which answer is correct?",
                    "options": ["correct", "wrong"],
                    "correct_index": 0,
                    "question_token": "mcq-question-token-0000000001",
                },
                "B1": {
                    "passage": "The next passage.",
                    "question": "This must remain unanswered.",
                    "options": ["next correct", "next wrong"],
                    "correct_index": 0,
                    "question_token": "mcq-question-token-0000000002",
                },
            },
            "current_level": "A2",
            "asked": [],
            "max_steps": 2,
            "ready": True,
            "done": False,
            "evidence_status": "missing_student_response",
        },
        "request_receipts": [],
    }


async def test_two_concurrent_mcq_answers_only_apply_one_revision_and_token(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    state = _mcq_state()
    record = await exam_record_factory(state=state)
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_args, **_kwargs: None)

    async def submit(request_id: str):
        async with postgres_session_factory() as db:
            try:
                response = await language_exam.answer_mcq(
                    record.session_id,
                    McqAnswerIn(
                        choice_index=0,
                        request_id=request_id,
                        state_revision=state["state_revision"],
                        question_token=state["reading"]["pool"]["A2"]["question_token"],
                    ),
                    BackgroundTasks(),
                    student=record.student,
                    db=db,
                )
                return "ok", response
            except HTTPException as exc:
                await db.rollback()
                return "error", exc

    outcomes = await asyncio.wait_for(
        asyncio.gather(
            submit("concurrent-mcq-request-0001"),
            submit("concurrent-mcq-request-0002"),
        ),
        timeout=10,
    )

    successes = [value for kind, value in outcomes if kind == "ok"]
    failures = [value for kind, value in outcomes if kind == "error"]
    assert len(successes) == 1
    assert len(failures) == 1
    assert failures[0].status_code == 409
    assert failures[0].detail["code"] == "stale_exam_state"
    assert failures[0].detail["current_state_revision"] == state["state_revision"] + 1

    stored = await _stored_exam(postgres_session_factory, record.session_id)
    latest = stored.exam_state
    assert latest["state_revision"] == state["state_revision"] + 1
    assert latest["reading"]["asked"] == [
        {"level": "A2", "correct": True, "chosen_index": 0, "bank_item_id": None}
    ]
    assert latest["reading"]["current_level"] == "B1"
    assert len(latest["request_receipts"]) == 1


def _evidence_floor_state(section: str) -> dict:
    """Pool has 3 distinct levels (A1/A2/B1), but the plain 1-up-1-down staircase alone would
    converge after only 2 answers -- B2 (the level after two correct answers from A2) isn't in
    this pool, so adaptive_next_level returns None at asked_count=2. Used to prove the P1.2
    minimum-evidence floor (MIN_MCQ_EVIDENCE_ITEMS=3) forces one more question first."""
    return {
        "version": 3,
        "state_revision": 7,
        "sections": [section],
        "cursor": 0,
        section: {
            "mode": "adaptive",
            "pool": {
                "A1": {
                    "question": "A1 question?",
                    "options": ["correct", "wrong"],
                    "correct_index": 0,
                    "question_token": "evidence-floor-token-a1-000001",
                    "bank_item_id": 101,
                },
                "A2": {
                    "question": "A2 question?",
                    "options": ["correct", "wrong"],
                    "correct_index": 0,
                    "question_token": "evidence-floor-token-a2-000001",
                    "bank_item_id": 102,
                },
                "B1": {
                    "question": "B1 question?",
                    "options": ["correct", "wrong"],
                    "correct_index": 0,
                    "question_token": "evidence-floor-token-b1-000001",
                    "bank_item_id": 103,
                },
            },
            "current_level": "A2",
            "asked": [],
            "max_steps": 5,
            "ready": True,
            "done": False,
            "evidence_status": "missing_student_response",
        },
        "request_receipts": [],
    }


@pytest.mark.parametrize("section", ["reading", "listening", "grammar_vocab"])
async def test_mcq_section_keeps_probing_below_minimum_evidence_floor_before_completing(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
    section,
) -> None:
    """P1.2 Test D: reading/listening/grammar_vocab must not settle on a level from fewer than
    MIN_MCQ_EVIDENCE_ITEMS=3 answered items while the pool still has an unasked level, even though
    the plain staircase alone would stop after 2. Also covers Test E's P1.1 interaction: the
    continuation must still resolve to the pool's own distinct, already-deduped items."""
    state = _evidence_floor_state(section)
    record = await exam_record_factory(state=state)
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_args, **_kwargs: None)

    async def submit(request_id: str, choice_index: int):
        stored = await _stored_exam(postgres_session_factory, record.session_id)
        sec = stored.exam_state[section]
        token = sec["pool"][sec["current_level"]]["question_token"]
        async with postgres_session_factory() as db:
            return await language_exam.answer_mcq(
                record.session_id,
                McqAnswerIn(
                    choice_index=choice_index,
                    request_id=request_id,
                    state_revision=stored.exam_state["state_revision"],
                    question_token=token,
                ),
                BackgroundTasks(),
                student=record.student,
                db=db,
            )

    # Step 1: correct at A2 -> the staircase's own next level (B1) is in the pool -> ordinary
    # advance, unaffected by the evidence floor.
    await submit(f"evidence-floor-{section}-1", 0)
    stored = await _stored_exam(postgres_session_factory, record.session_id)
    sec = stored.exam_state[section]
    assert sec["done"] is False
    assert sec["current_level"] == "B1"
    assert len(sec["asked"]) == 1

    # Step 2: correct at B1 -> the staircase wants B2, which isn't in the pool, so
    # adaptive_next_level alone would stop here at only 2 answered items. The evidence floor must
    # force one more question (the only remaining pool level, A1) instead of finishing.
    await submit(f"evidence-floor-{section}-2", 0)
    stored = await _stored_exam(postgres_session_factory, record.session_id)
    sec = stored.exam_state[section]
    assert sec["done"] is False
    assert sec["current_level"] == "A1"
    assert sec["evidence_status"] == "missing_student_response"
    assert len(sec["asked"]) == 2

    # Step 3: wrong at A1 -> the staircase converges (stays at A1) and evidence now meets the
    # floor (3 answered) -> the section is allowed to complete normally.
    await submit(f"evidence-floor-{section}-3", 1)
    stored = await _stored_exam(postgres_session_factory, record.session_id)
    sec = stored.exam_state[section]
    assert sec["done"] is True
    assert sec["evidence_status"] == "completed"
    assert len(sec["asked"]) == 3

    # P1.1 compatibility: the evidence-floor continuation only ever selects among the pool's own
    # pre-deduped levels, so no bank_item_id repeats within this session's asked list.
    bank_item_ids = [a["bank_item_id"] for a in sec["asked"]]
    assert len(bank_item_ids) == len(set(bank_item_ids)) == 3


async def _insert_boundary_bank_item(
    postgres_session_factory,
    *,
    language_id: int,
    skill: str,
    level: str,
    low: str,
    high: str,
) -> int:
    """Seed one genuinely boundary-tagged, verified/active bank row so
    select_placement_bank_items(..., boundary=...) has something real to find (P1.3).

    Listening items additionally need a usable audio_url or _boundary_confirmation_item's own
    validity check (mirroring _question_bank_pool's) discards them for missing audio evidence."""
    is_reading = skill == "reading"
    body_json = _reading_bank_bundle_body() if is_reading else None
    options = (
        ["Correct answer", "Wrong answer", "Another wrong answer", "Not given"]
        if is_reading
        else ["boundary correct", "boundary wrong"]
    )
    async with postgres_session_factory() as db:
        item = LanguagePlacementQuestionBankItem(
            language_id=language_id,
            skill=skill,
            level=LanguageLevel(level),
            boundary_low_level=LanguageLevel(low),
            boundary_high_level=LanguageLevel(high),
            question_type="mcq",
            prompt_text="What is the main idea?" if is_reading else "Boundary confirmation question?",
            passage="A boundary reading passage with one clear main idea." if is_reading else None,
            options_json=["boundary correct", "boundary wrong"],
            correct_index=0,
            body_json=body_json,
            source=_READING_MVP_SOURCE if is_reading else "seed",
            is_verified=True,
            is_active=True,
            audio_meta_json=(
                {"public_url": "/language-assets/en/placement/listening/boundary-test.wav"}
                if skill == "listening"
                else None
            ),
        )
        item.options_json = options
        db.add(item)
        await db.commit()
        return item.id


def _boundary_prone_state(section: str) -> dict:
    """4-level pool (A1..B2): correct at A2, correct at B1, incorrect at B2 satisfies both the
    plain staircase (B1 already asked, so it converges) and the P1.2 evidence floor (3 answered),
    landing exactly on a B1/B2 disagreement -- the scenario P1.3 boundary confirmation should
    engage on."""

    def _item(level: str, bank_item_id: int) -> dict:
        return {
            "question": f"{level} question?",
            "options": ["correct", "wrong"],
            "correct_index": 0,
            "question_token": f"boundary-prone-token-{level.lower()}-000001",
            "bank_item_id": bank_item_id,
        }

    pre_asked = []
    if section == "reading":
        pre_asked = [
            {"level": "A1", "chosen_index": 0, "correct": True, "bank_item_id": 801},
            {"level": "C1", "chosen_index": 1, "correct": False, "bank_item_id": 805},
        ]

    return {
        "version": 3,
        "state_revision": 7,
        "sections": [section],
        "cursor": 0,
        section: {
            "mode": "adaptive",
            "pool": {
                "A1": _item("A1", 901),
                "A2": _item("A2", 902),
                "B1": _item("B1", 903),
                "B2": _item("B2", 904),
            },
            "current_level": "A2",
            "asked": pre_asked,
            "max_steps": 5,
            "ready": True,
            "done": False,
            "evidence_status": "missing_student_response",
        },
        "request_receipts": [],
    }


async def _drive_boundary_prone_state_to_trigger(postgres_session_factory, record, section: str) -> None:
    """Answer A2 (correct), B1 (correct), B2 (incorrect) -- leaves both the staircase and the
    P1.2 evidence floor satisfied, landing on a B1/B2 disagreement."""

    async def submit(request_id: str, level: str, choice_index: int):
        stored = await _stored_exam(postgres_session_factory, record.session_id)
        sec = stored.exam_state[section]
        token = sec["pool"][level]["question_token"]
        async with postgres_session_factory() as db:
            return await language_exam.answer_mcq(
                record.session_id,
                McqAnswerIn(
                    choice_index=choice_index,
                    request_id=request_id,
                    state_revision=stored.exam_state["state_revision"],
                    question_token=token,
                ),
                BackgroundTasks(),
                student=record.student,
                db=db,
            )

    await submit(f"boundary-{section}-1", "A2", 0)
    await submit(f"boundary-{section}-2", "B1", 0)
    await submit(f"boundary-{section}-3", "B2", 1)


@pytest.mark.parametrize("section", ["reading", "listening", "grammar_vocab"])
async def test_boundary_confirmation_asks_one_extra_question_when_a_matching_item_exists(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
    section,
) -> None:
    """P1.3 Tests A, F: a genuine B1/B2 boundary item exists and hasn't been used yet -- the
    section must ask exactly one more question built from that item (not zero), across all three
    MCQ sections, and then finish immediately once it's answered."""
    state = _boundary_prone_state(section)
    record = await exam_record_factory(state=state)
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_args, **_kwargs: None)
    boundary_item_id = await _insert_boundary_bank_item(
        postgres_session_factory,
        language_id=record.language_id,
        skill=section,
        level="B2",
        low="B1",
        high="B2",
    )

    await _drive_boundary_prone_state_to_trigger(postgres_session_factory, record, section)

    stored = await _stored_exam(postgres_session_factory, record.session_id)
    sec = stored.exam_state[section]
    assert sec["done"] is False
    assert sec["boundary_asked"] is True
    assert sec["evidence_status"] == "missing_student_response"
    assert len(sec["asked"]) == (5 if section == "reading" else 3)
    boundary_level_key = sec["current_level"]
    assert sec["pool"][boundary_level_key]["bank_item_id"] == boundary_item_id

    # Answer the boundary-confirmation question itself (incorrect here; a separate test proves the
    # cap holds when it's answered correctly too) -- the section must finish right after.
    answer_body = (
        McqAnswerIn(
            choice_indices=[1, 1, 1, 1],
            request_id=f"boundary-{section}-confirm",
            state_revision=stored.exam_state["state_revision"],
            question_token=sec["pool"][boundary_level_key]["question_token"],
        )
        if section == "reading"
        else McqAnswerIn(
            choice_index=1,
            request_id=f"boundary-{section}-confirm",
            state_revision=stored.exam_state["state_revision"],
            question_token=sec["pool"][boundary_level_key]["question_token"],
        )
    )
    async with postgres_session_factory() as db:
        await language_exam.answer_mcq(
            record.session_id,
            answer_body,
            BackgroundTasks(),
            student=record.student,
            db=db,
        )

    stored = await _stored_exam(postgres_session_factory, record.session_id)
    sec = stored.exam_state[section]
    assert sec["done"] is True
    assert sec["evidence_status"] == "completed"
    expected_asked_count = 6 if section == "reading" else 4
    assert len(sec["asked"]) == expected_asked_count
    assert sec["asked"][-1]["bank_item_id"] == boundary_item_id
    bank_item_ids = [a["bank_item_id"] for a in sec["asked"]]
    assert len(bank_item_ids) == len(set(bank_item_ids)) == expected_asked_count


async def test_boundary_confirmation_caps_at_one_question_when_answer_is_correct(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """P1.3 Test C: the cap must hold regardless of how the boundary-confirmation question itself
    is answered -- answering it correctly must not trigger a second boundary/staircase round."""
    section = "reading"
    state = _boundary_prone_state(section)
    record = await exam_record_factory(state=state)
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_args, **_kwargs: None)
    await _insert_boundary_bank_item(
        postgres_session_factory,
        language_id=record.language_id,
        skill=section,
        level="B2",
        low="B1",
        high="B2",
    )

    await _drive_boundary_prone_state_to_trigger(postgres_session_factory, record, section)
    stored = await _stored_exam(postgres_session_factory, record.session_id)
    sec = stored.exam_state[section]
    boundary_level_key = sec["current_level"]

    async with postgres_session_factory() as db:
        await language_exam.answer_mcq(
            record.session_id,
            McqAnswerIn(
                choice_indices=[0, 0, 0, 0],  # correct this time
                request_id="boundary-reading-confirm-correct",
                state_revision=stored.exam_state["state_revision"],
                question_token=sec["pool"][boundary_level_key]["question_token"],
            ),
            BackgroundTasks(),
            student=record.student,
            db=db,
        )

    stored = await _stored_exam(postgres_session_factory, record.session_id)
    sec = stored.exam_state[section]
    assert sec["done"] is True
    assert sec["evidence_status"] == "completed"
    assert len(sec["asked"]) == 6


async def test_boundary_confirmation_completes_safely_when_no_matching_item_exists(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """P1.3 Test B: a boundary situation is detected (B1 correct, B2 incorrect) but the bank has no
    boundary-tagged item for that pair -- the section must complete safely at 3 answered items,
    not block, and not loop looking for one."""
    section = "reading"
    state = _boundary_prone_state(section)
    record = await exam_record_factory(state=state)
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_args, **_kwargs: None)
    # Deliberately no _insert_boundary_bank_item call -- the bank has nothing for this pair.

    await _drive_boundary_prone_state_to_trigger(postgres_session_factory, record, section)

    stored = await _stored_exam(postgres_session_factory, record.session_id)
    sec = stored.exam_state[section]
    assert sec["done"] is True
    assert sec["evidence_status"] == "completed"
    assert len(sec["asked"]) == 5
    # A boundary situation WAS detected and attempted (proving detection ran), it just found
    # nothing usable -- this must not be retried or left half-finished.
    assert sec["boundary_asked"] is True


async def test_boundary_confirmation_excludes_an_already_used_bank_item_id(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """P1.3 Test D: if the only matching boundary item's id is already recorded as used within
    this session, it must be excluded -- and since it's the only candidate, this looks identical
    to "no matching item" (Test B) from the outside, but exercises the used_item_ids filter
    specifically rather than an empty bank."""
    section = "reading"
    state = _boundary_prone_state(section)
    record = await exam_record_factory(state=state)
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_args, **_kwargs: None)
    boundary_item_id = await _insert_boundary_bank_item(
        postgres_session_factory,
        language_id=record.language_id,
        skill=section,
        level="B2",
        low="B1",
        high="B2",
    )

    # Pre-record that item id as already used for the pool's B2 entry, so by the time the
    # staircase answers B2, _already_used_bank_item_ids(state, "reading") already contains it.
    async with postgres_session_factory() as db:
        row = (
            await db.execute(select(LanguageExamSession).where(LanguageExamSession.id == record.session_id))
        ).scalar_one()
        exam_state = copy.deepcopy(row.exam_state)
        exam_state[section]["pool"]["B2"]["bank_item_id"] = boundary_item_id
        row.exam_state = exam_state
        flag_modified(row, "exam_state")
        await db.commit()

    await _drive_boundary_prone_state_to_trigger(postgres_session_factory, record, section)

    stored = await _stored_exam(postgres_session_factory, record.session_id)
    sec = stored.exam_state[section]
    assert sec["done"] is True
    assert sec["evidence_status"] == "completed"
    assert len(sec["asked"]) == 5
    assert sec["boundary_asked"] is True
    # The excluded id appears exactly once (the original B2 staircase answer) -- never again as a
    # freshly-injected boundary question, proving the exclusion actually suppressed it.
    matches = [a for a in sec["asked"] if a["bank_item_id"] == boundary_item_id]
    assert len(matches) == 1
    assert matches[0]["level"] == "B2"


async def test_min_evidence_floor_still_applies_before_boundary_confirmation(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """P1.3 Test E: P1.2's minimum evidence floor must still take priority. A disagreement at only
    2 answered items (below MIN_MCQ_EVIDENCE_ITEMS=3) must trigger the P1.2 continuation, not a
    boundary-confirmation question -- even when a genuinely matching boundary item exists."""
    section = "reading"
    state = _evidence_floor_state(section)
    record = await exam_record_factory(state=state)
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_args, **_kwargs: None)
    # A genuinely matching A2/B1 boundary item exists in the bank -- it must not be reached yet.
    await _insert_boundary_bank_item(
        postgres_session_factory,
        language_id=record.language_id,
        skill=section,
        level="B1",
        low="A2",
        high="B1",
    )

    async def submit(request_id: str, level: str, choice_index: int):
        stored = await _stored_exam(postgres_session_factory, record.session_id)
        sec = stored.exam_state[section]
        token = sec["pool"][level]["question_token"]
        async with postgres_session_factory() as db:
            return await language_exam.answer_mcq(
                record.session_id,
                McqAnswerIn(
                    choice_index=choice_index,
                    request_id=request_id,
                    state_revision=stored.exam_state["state_revision"],
                    question_token=token,
                ),
                BackgroundTasks(),
                student=record.student,
                db=db,
            )

    await submit("evidence-before-boundary-1", "A2", 0)  # correct
    await submit("evidence-before-boundary-2", "B1", 1)  # incorrect -> A2/B1 disagreement, but only 2 answered

    stored = await _stored_exam(postgres_session_factory, record.session_id)
    sec = stored.exam_state[section]
    assert sec["done"] is False
    assert sec["current_level"] == "A1"  # P1.2's continuation, not the boundary item
    assert not sec.get("boundary_asked")
    assert len(sec["asked"]) == 2


def _speaking_state() -> dict:
    return {
        "version": 3,
        "state_revision": 13,
        "sections": ["speaking"],
        "cursor": 0,
        "learner_grade": None,
        "speaking": {
            "scenario": {
                "scenario": "At a community event",
                "ai_persona": "Host",
                "student_role": "Guest",
                "setting": "Community hall",
            },
            "turn": 1,
            "total_turns": 2,
            "pending_question": "What brought you to this event?",
            "turn_token": "speaking-current-token-00000001",
            "results": [],
            "done": False,
            "evidence_status": "missing_student_response",
        },
        "request_receipts": [],
    }


async def test_two_concurrent_audio_files_cannot_fill_two_speaking_turns(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    state = _speaking_state()
    record = await exam_record_factory(state=state)
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(language_exam, "_effective_level", lambda *_args, **_kwargs: _async("A2"))

    async def fake_read(file) -> ValidatedAudio:
        content = str(file.filename).encode("utf-8")
        return ValidatedAudio(
            data=content,
            mime_type="audio/webm",
            suffix=".webm",
            sha256=hashlib.sha256(content).hexdigest(),
            duration_seconds=3.0,
        )

    async def fake_transcribe(audio: ValidatedAudio) -> ConversationTranscription:
        return ConversationTranscription(
            text=f"I came to meet neighbours and help with the event {audio.sha256[:4]}",
            engine="test-stt",
            model="test-model",
        )

    assess_arrivals = 0
    assess_lock = asyncio.Lock()
    both_assessing = asyncio.Event()

    async def fake_assess(**kwargs) -> SpeakingTurnAssessment:
        nonlocal assess_arrivals
        async with assess_lock:
            assess_arrivals += 1
            if assess_arrivals == 2:
                both_assessing.set()
        await asyncio.wait_for(both_assessing.wait(), timeout=5)
        return SpeakingTurnAssessment(
            transcription=kwargs["transcript"],
            grammar_vocab_feedback="No material issue.",
            pronunciation_feedback="",
            fluency_note="Coherent response.",
            estimated_level=CEFRLevel.A2,
            next_question="What activity would you like to join next?",
        )

    monkeypatch.setattr(language_exam, "_read_speaking_audio", fake_read)
    monkeypatch.setattr(language_exam, "_verified_server_transcription", fake_transcribe)
    monkeypatch.setattr(language_exam.ai_engine, "assess_speaking", fake_assess)

    async def submit(filename: str, request_id: str):
        async with postgres_session_factory() as db:
            try:
                response = await language_exam.speaking_turn(
                    record.session_id,
                    BackgroundTasks(),
                    file=SimpleNamespace(filename=filename),
                    duration_seconds=None,
                    request_id=request_id,
                    state_revision=state["state_revision"],
                    turn_token=state["speaking"]["turn_token"],
                    section=None,
                    student=record.student,
                    db=db,
                )
                return "ok", response
            except HTTPException as exc:
                await db.rollback()
                return "error", exc

    outcomes = await asyncio.wait_for(
        asyncio.gather(
            submit("first.webm", "concurrent-speaking-request-1"),
            submit("second.webm", "concurrent-speaking-request-2"),
        ),
        timeout=10,
    )

    successes = [value for kind, value in outcomes if kind == "ok"]
    failures = [value for kind, value in outcomes if kind == "error"]
    assert len(successes) == 1
    assert len(failures) == 1
    assert failures[0].status_code == 409
    assert failures[0].detail["code"] == "stale_exam_state"

    stored = await _stored_exam(postgres_session_factory, record.session_id)
    latest = stored.exam_state
    assert latest["state_revision"] == state["state_revision"] + 1
    assert latest["speaking"]["turn"] == 2
    assert len(latest["speaking"]["results"]) == 1
    assert len(latest["request_receipts"]) == 1


def _fake_assess_ok(next_question: str = "What activity would you like to join next?"):
    async def fake_assess(**kwargs) -> SpeakingTurnAssessment:
        return SpeakingTurnAssessment(
            transcription=kwargs["transcript"],
            grammar_vocab_feedback="No material issue.",
            pronunciation_feedback="",
            fluency_note="Coherent response.",
            estimated_level=CEFRLevel.A2,
            next_question=next_question,
        )

    return fake_assess


async def test_stale_speaking_turn_resubmission_is_rejected_safely_and_does_not_corrupt_state(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """Direct (non-racing) regression for the QA-observed stale-answer warning: once a turn has
    been successfully answered and the exam has moved on, a second submission carrying the
    now-stale state_revision/turn_token (e.g. a delayed upload whose response arrived late, or a
    leftover browser tab) must be rejected with a clean, structured 409 -- and must not mutate the
    exam state at all (no extra turn advance, no extra result, no revision bump)."""
    state = _speaking_state()
    record = await exam_record_factory(state=state)
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(language_exam, "_effective_level", lambda *_args, **_kwargs: _async("A2"))
    await _fake_audio_and_stt(monkeypatch)
    monkeypatch.setattr(language_exam.ai_engine, "assess_speaking", _fake_assess_ok())

    stale_revision = state["state_revision"]
    stale_token = state["speaking"]["turn_token"]

    async with postgres_session_factory() as db:
        await language_exam.speaking_turn(
            record.session_id,
            BackgroundTasks(),
            file=SimpleNamespace(filename="first.webm"),
            duration_seconds=None,
            request_id="direct-stale-request-1",
            state_revision=stale_revision,
            turn_token=stale_token,
            section=None,
            student=record.student,
            db=db,
        )

    stored_after_first = await _stored_exam(postgres_session_factory, record.session_id)
    state_after_first = stored_after_first.exam_state
    assert state_after_first["speaking"]["turn"] == 2
    assert len(state_after_first["speaking"]["results"]) == 1

    # A second submission arrives late, still carrying the turn-1 (now stale) revision/token --
    # e.g. a delayed upload whose response the client never saw, retried against stale local state.
    with pytest.raises(HTTPException) as exc_info:
        async with postgres_session_factory() as db:
            await language_exam.speaking_turn(
                record.session_id,
                BackgroundTasks(),
                file=SimpleNamespace(filename="stale-retry.webm"),
                duration_seconds=None,
                request_id="direct-stale-request-2",
                state_revision=stale_revision,
                turn_token=stale_token,
                section=None,
                student=record.student,
                db=db,
            )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "stale_exam_state"

    stored_after_stale = await _stored_exam(postgres_session_factory, record.session_id)
    state_after_stale = stored_after_stale.exam_state
    assert state_after_stale["speaking"]["turn"] == 2, "the rejected stale retry must not advance the turn further"
    assert len(state_after_stale["speaking"]["results"]) == 1, "the rejected stale retry must not add a second result"
    assert state_after_stale["state_revision"] == state_after_first["state_revision"], (
        "the rejected stale retry must not bump the state revision"
    )


async def test_valid_speaking_turn_answer_advances_exactly_once(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """A single, valid, current-state submission must advance the speaking section by exactly
    one turn, append exactly one result, and bump state_revision by exactly one -- no more, no
    less. Complements the concurrency test above by isolating the plain, non-racing happy path."""
    state = _speaking_state()
    record = await exam_record_factory(state=state)
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(language_exam, "_effective_level", lambda *_args, **_kwargs: _async("A2"))
    await _fake_audio_and_stt(monkeypatch)
    monkeypatch.setattr(language_exam.ai_engine, "assess_speaking", _fake_assess_ok())

    async with postgres_session_factory() as db:
        response = await language_exam.speaking_turn(
            record.session_id,
            BackgroundTasks(),
            file=SimpleNamespace(filename="only-submission.webm"),
            duration_seconds=None,
            request_id="direct-valid-request-1",
            state_revision=state["state_revision"],
            turn_token=state["speaking"]["turn_token"],
            section=None,
            student=record.student,
            db=db,
        )

    assert response.state_revision == state["state_revision"] + 1

    stored = await _stored_exam(postgres_session_factory, record.session_id)
    latest = stored.exam_state
    assert latest["state_revision"] == state["state_revision"] + 1
    assert latest["speaking"]["turn"] == 2
    assert len(latest["speaking"]["results"]) == 1
    assert latest["speaking"]["evidence_status"] == "missing_student_response"
    assert latest["request_receipts"] and len(latest["request_receipts"]) == 1


async def _insert_speaking_bank_item(
    postgres_session_factory,
    *,
    language_id: int,
    level: str,
    prompt_text: str,
    situation: str = "",
    subskill: str = "self_intro",
) -> int:
    """Seed one verified, active speaking_prompt bank item -- MVP items are usable immediately,
    unlike the MCQ/writing bank tests which don't need is_verified toggled explicitly."""
    async with postgres_session_factory() as db:
        item = LanguagePlacementQuestionBankItem(
            language_id=language_id,
            skill="speaking_prompt",
            level=LanguageLevel(level),
            question_type="speaking_prompt",
            prompt_text=prompt_text,
            situation=situation or None,
            subskill=subskill,
            source="draft_seed",
            is_verified=True,
            is_active=True,
            body_json={
                "grade_band": ["mixed_school"],
                "expected_response_seconds": {"min": 10, "target": 20, "max": 45},
                "review_status": "mvp_approved_pending_full_review",
                "human_reviewed": False,
            },
        )
        db.add(item)
        await db.commit()
        return item.id


async def _fake_audio_and_stt(monkeypatch) -> None:
    async def fake_read(file) -> ValidatedAudio:
        content = str(file.filename).encode("utf-8")
        return ValidatedAudio(
            data=content,
            mime_type="audio/webm",
            suffix=".webm",
            sha256=hashlib.sha256(content).hexdigest(),
            duration_seconds=3.0,
        )

    async def fake_transcribe(audio: ValidatedAudio) -> ConversationTranscription:
        return ConversationTranscription(
            text=f"A reasonable spoken answer {audio.sha256[:6]}", engine="test-stt", model="test-model"
        )

    monkeypatch.setattr(language_exam, "_read_speaking_audio", fake_read)
    monkeypatch.setattr(language_exam, "_verified_server_transcription", fake_transcribe)


async def test_initiate_exam_and_speaking_turns_use_verified_bank_prompts_with_staircase_and_no_repeats(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """MVP wiring Tests C, D, E: a new speaking session must pull its opening question, and every
    subsequent turn's question, from verified speaking_prompt bank items -- following the live
    per-turn estimated_level as a light staircase, never repeating an item, and never falling
    back to the AI's own next_question/generated scenario when a bank item is available (proven
    via a distinctive "poison" value that must never surface)."""
    record = await exam_record_factory(
        state={"version": 3, "state_revision": 1, "sections": [], "cursor": 0},
        status="abandoned",
    )
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(language_exam, "_effective_level", lambda *_args, **_kwargs: _async("A2"))
    monkeypatch.setattr(language_exam, "_student_grade", lambda *_args, **_kwargs: _async(None))

    async def poison_generate_scenario(**_kwargs) -> dict:
        return {
            "scenario": "POISON",
            "ai_persona": "POISON",
            "student_role": "POISON",
            "setting": "POISON",
            "opening_question": "POISON_SHOULD_NOT_APPEAR",
        }

    monkeypatch.setattr(language_exam.ai_engine, "generate_scenario_and_opening", poison_generate_scenario)

    a2_id = await _insert_speaking_bank_item(
        postgres_session_factory,
        language_id=record.language_id,
        level="A2",
        prompt_text="Tell me about your day.",
        situation="A friend asks about your day.",
    )
    b1_id = await _insert_speaking_bank_item(
        postgres_session_factory,
        language_id=record.language_id,
        level="B1",
        prompt_text="Tell me about a memorable trip.",
        situation="A friend asks about travel.",
    )
    c1_id = await _insert_speaking_bank_item(
        postgres_session_factory,
        language_id=record.language_id,
        level="C1",
        prompt_text="Discuss how technology changes society.",
        situation="A thoughtful discussion.",
    )

    async with postgres_session_factory() as db:
        student = await db.get(User, record.student_id)
        language = await db.get(Language, record.language_id)
        monkeypatch.setattr(language_exam, "get_default_language", lambda _db: _async(language))
        initiate_response = await language_exam.initiate_exam(BackgroundTasks(), student=student, db=db)

    stored = await _stored_exam(postgres_session_factory, initiate_response.session_id)
    sp = stored.exam_state["speaking"]
    assert sp["pending_question"] != "POISON_SHOULD_NOT_APPEAR"
    assert "Tell me about your day." in sp["pending_question"]
    assert sp["pending_bank_item_id"] == a2_id

    # assess_speaking runs once per turn including the last (the "done" check happens after
    # assessment), so this needs one value per turn even though turn 3's estimate is never used
    # for further selection.
    call_levels = iter([CEFRLevel.B1, CEFRLevel.C1, CEFRLevel.C1])

    async def fake_assess(**kwargs) -> SpeakingTurnAssessment:
        return SpeakingTurnAssessment(
            transcription=kwargs["transcript"],
            grammar_vocab_feedback="No material issue.",
            pronunciation_feedback="",
            fluency_note="Coherent response.",
            estimated_level=next(call_levels),
            next_question="POISON_SHOULD_NOT_APPEAR",
        )

    await _fake_audio_and_stt(monkeypatch)
    monkeypatch.setattr(language_exam.ai_engine, "assess_speaking", fake_assess)

    async def submit_turn(filename: str, request_id: str):
        stored = await _stored_exam(postgres_session_factory, initiate_response.session_id)
        sp = stored.exam_state["speaking"]
        async with postgres_session_factory() as db:
            return await language_exam.speaking_turn(
                initiate_response.session_id,
                BackgroundTasks(),
                file=SimpleNamespace(filename=filename),
                duration_seconds=None,
                request_id=request_id,
                state_revision=stored.exam_state["state_revision"],
                turn_token=sp["turn_token"],
                section=None,
                student=record.student,
                db=db,
            )

    await submit_turn("turn1.webm", "mvp-staircase-turn-1")
    stored = await _stored_exam(postgres_session_factory, initiate_response.session_id)
    sp = stored.exam_state["speaking"]
    assert sp["pending_question"] != "POISON_SHOULD_NOT_APPEAR"
    assert "memorable trip" in sp["pending_question"]
    assert sp["pending_bank_item_id"] == b1_id

    await submit_turn("turn2.webm", "mvp-staircase-turn-2")
    stored = await _stored_exam(postgres_session_factory, initiate_response.session_id)
    sp = stored.exam_state["speaking"]
    assert sp["pending_question"] != "POISON_SHOULD_NOT_APPEAR"
    assert "technology changes society" in sp["pending_question"]
    assert sp["pending_bank_item_id"] == c1_id

    await submit_turn("turn3.webm", "mvp-staircase-turn-3")
    stored = await _stored_exam(postgres_session_factory, initiate_response.session_id)
    sp = stored.exam_state["speaking"]
    assert sp["done"] is True
    assert sp["total_turns"] == 3  # speaking remains 3 turns for MVP
    assert len(sp["results"]) == 3
    bank_item_ids = [r["bank_item_id"] for r in sp["results"]]
    assert bank_item_ids == [a2_id, b1_id, c1_id]
    assert len(set(bank_item_ids)) == 3  # no repeated speaking prompt within the session


async def test_speaking_uses_ai_fallback_when_no_verified_bank_item_available(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """MVP wiring Test F: when the bank has nothing usable (none seeded for this fresh language),
    the exam must still work via the existing AI-generated scenario/next-question path --
    fallback compatibility is fully preserved."""
    record = await exam_record_factory(
        state={"version": 3, "state_revision": 1, "sections": [], "cursor": 0},
        status="abandoned",
    )
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(language_exam, "_effective_level", lambda *_args, **_kwargs: _async("A2"))
    monkeypatch.setattr(language_exam, "_student_grade", lambda *_args, **_kwargs: _async(None))

    async def generate_scenario(**_kwargs) -> dict:
        return {
            "scenario": "At a community event",
            "ai_persona": "Host",
            "student_role": "Guest",
            "setting": "Community hall",
            "opening_question": "What brought you to the event?",
        }

    monkeypatch.setattr(language_exam.ai_engine, "generate_scenario_and_opening", generate_scenario)

    async with postgres_session_factory() as db:
        language = await db.get(Language, record.language_id)
        monkeypatch.setattr(language_exam, "get_default_language", lambda _db: _async(language))
        initiate_response = await language_exam.initiate_exam(BackgroundTasks(), student=record.student, db=db)

    stored = await _stored_exam(postgres_session_factory, initiate_response.session_id)
    sp = stored.exam_state["speaking"]
    assert sp["pending_question"] == "What brought you to the event?"
    assert sp["pending_bank_item_id"] is None

    async def fake_assess(**kwargs) -> SpeakingTurnAssessment:
        return SpeakingTurnAssessment(
            transcription=kwargs["transcript"],
            grammar_vocab_feedback="No material issue.",
            pronunciation_feedback="",
            fluency_note="Coherent response.",
            estimated_level=CEFRLevel.A2,
            next_question="What activity would you like to join next?",
        )

    await _fake_audio_and_stt(monkeypatch)
    monkeypatch.setattr(language_exam.ai_engine, "assess_speaking", fake_assess)

    async with postgres_session_factory() as db:
        await language_exam.speaking_turn(
            initiate_response.session_id,
            BackgroundTasks(),
            file=SimpleNamespace(filename="a.webm"),
            duration_seconds=None,
            request_id="fallback-turn-1",
            state_revision=stored.exam_state["state_revision"],
            turn_token=sp["turn_token"],
            section=None,
            student=record.student,
            db=db,
        )

    stored = await _stored_exam(postgres_session_factory, initiate_response.session_id)
    sp = stored.exam_state["speaking"]
    assert sp["pending_question"] == "What activity would you like to join next?"
    assert sp["pending_bank_item_id"] is None
    assert sp["results"][0]["bank_item_id"] is None


async def _insert_legacy_speaking_bank_item(
    postgres_session_factory, *, language_id: int, level: str, prompt_text: str, situation: str = ""
) -> int:
    """Seed one active+verified speaking_prompt row shaped like the pre-existing legacy rows
    produced by the older, generic scripts/seed_placement_question_bank.py script (source=
    content_seed, generic subskill=speaking_task, stable_key like "content:<id>", no
    review_status/human_reviewed marker in body_json) -- these must never be selected for MVP
    speaking placement even though they are active+verified, same as the real local DB rows this
    regression guards against."""
    async with postgres_session_factory() as db:
        item = LanguagePlacementQuestionBankItem(
            language_id=language_id,
            skill="speaking_prompt",
            level=LanguageLevel(level),
            question_type="speaking_prompt",
            prompt_text=prompt_text,
            situation=situation or None,
            subskill="speaking_task",
            source="content_seed",
            stable_key=f"content:{uuid.uuid4().hex[:12]}",
            is_verified=True,
            is_active=True,
            body_json={"content_item_id": 999, "min_seconds": 10},
        )
        db.add(item)
        await db.commit()
        return item.id


async def test_speaking_bank_prompt_prefers_mvp_row_over_legacy_row_at_same_level(
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """Regression test for the MVP-only speaking selection gate: given one legacy (pre-MVP,
    generic) speaking_prompt row and one MVP-marked speaking_prompt row at the same CEFR level,
    _speaking_bank_prompt must return the MVP row, never the legacy row -- even though both are
    active+verified and therefore equally eligible under the shared, skill-agnostic
    is_active/is_verified filter alone."""
    record = await exam_record_factory(
        state={"version": 3, "state_revision": 1, "sections": [], "cursor": 0},
        status="abandoned",
    )
    legacy_id = await _insert_legacy_speaking_bank_item(
        postgres_session_factory,
        language_id=record.language_id,
        level="A2",
        prompt_text="LEGACY_SHOULD_NOT_BE_SELECTED",
    )
    mvp_id = await _insert_speaking_bank_item(
        postgres_session_factory,
        language_id=record.language_id,
        level="A2",
        prompt_text="Tell me about your day.",
        situation="A friend asks about your day.",
    )

    async with postgres_session_factory() as db:
        item = await language_exam._speaking_bank_prompt(db, language_id=record.language_id, level_str="A2")

    assert item is not None
    assert item["bank_item_id"] == mvp_id
    assert item["bank_item_id"] != legacy_id
    assert "LEGACY_SHOULD_NOT_BE_SELECTED" not in item["question"]


async def test_speaking_bank_prompt_ignores_legacy_rows_entirely_and_falls_back(
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """When only a legacy (pre-MVP) speaking_prompt row exists at a level -- no MVP-marked row --
    _speaking_bank_prompt must return None (triggering the existing AI-generation fallback), not
    silently hand back the legacy row. Proves true exclusion, not just a same-level preference,
    and that the bank having *some* row at a level must never mask the fallback path."""
    record = await exam_record_factory(
        state={"version": 3, "state_revision": 1, "sections": [], "cursor": 0},
        status="abandoned",
    )
    await _insert_legacy_speaking_bank_item(
        postgres_session_factory,
        language_id=record.language_id,
        level="B2",
        prompt_text="LEGACY_SHOULD_NOT_BE_SELECTED",
    )

    async with postgres_session_factory() as db:
        item = await language_exam._speaking_bank_prompt(db, language_id=record.language_id, level_str="B2")

    assert item is None


async def test_select_placement_bank_items_require_mvp_marker_excludes_legacy_rows(
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """Direct service-level proof: select_placement_bank_items(..., require_mvp_marker=True)
    never returns a legacy speaking_prompt row, while require_mvp_marker=False (the default,
    used by every other bank skill: reading/listening/grammar_vocab/writing_prompt) is completely
    unaffected -- the same legacy row IS returned without the flag."""
    record = await exam_record_factory(
        state={"version": 3, "state_revision": 1, "sections": [], "cursor": 0},
        status="abandoned",
    )
    legacy_id = await _insert_legacy_speaking_bank_item(
        postgres_session_factory,
        language_id=record.language_id,
        level="C1",
        prompt_text="Legacy prompt text.",
    )

    async with postgres_session_factory() as db:
        without_flag = await select_placement_bank_items(
            db, language_id=record.language_id, skill="speaking_prompt", level="C1", count=5,
        )
        with_flag = await select_placement_bank_items(
            db,
            language_id=record.language_id,
            skill="speaking_prompt",
            level="C1",
            count=5,
            require_mvp_marker=True,
        )

    assert legacy_id in {row.id for row in without_flag}
    assert legacy_id not in {row.id for row in with_flag}
    assert with_flag == []


async def test_speaking_bank_prompt_prefers_unused_subskill_over_already_used_one(
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """QA observation: prompts can repeat the same subskill/task_type back to back (e.g.
    self_intro, self_intro) even though bank_item_id itself is never repeated. Given two eligible
    MVP-marked items at the same level, one whose subskill already appeared this session and one
    whose subskill is fresh, _speaking_bank_prompt must prefer the fresh one."""
    record = await exam_record_factory(
        state={"version": 3, "state_revision": 1, "sections": [], "cursor": 0},
        status="abandoned",
    )
    used_id = await _insert_speaking_bank_item(
        postgres_session_factory,
        language_id=record.language_id,
        level="A2",
        prompt_text="SELF_INTRO_ALREADY_USED",
        subskill="self_intro",
    )
    fresh_id = await _insert_speaking_bank_item(
        postgres_session_factory,
        language_id=record.language_id,
        level="A2",
        prompt_text="ROUTINE_DESCRIPTION_FRESH",
        subskill="routine_description",
    )

    async with postgres_session_factory() as db:
        item = await language_exam._speaking_bank_prompt(
            db, language_id=record.language_id, level_str="A2", used_subskills={"self_intro"}
        )

    assert item is not None
    assert item["bank_item_id"] == fresh_id
    assert item["bank_item_id"] != used_id
    assert item["subskill"] == "routine_description"


async def test_speaking_bank_prompt_avoids_recently_seen_student_or_language_items(
    postgres_session_factory,
    exam_record_factory,
) -> None:
    record = await exam_record_factory(
        state={"version": 3, "state_revision": 1, "sections": [], "cursor": 0},
        status="completed",
    )
    recent_id = await _insert_speaking_bank_item(
        postgres_session_factory,
        language_id=record.language_id,
        level="A2",
        prompt_text="Recently used prompt.",
        subskill="routine_description",
    )
    fresh_id = await _insert_speaking_bank_item(
        postgres_session_factory,
        language_id=record.language_id,
        level="A2",
        prompt_text="Fresh prompt.",
        subskill="simple_preference",
    )
    async with postgres_session_factory() as db:
        row = (await db.execute(select(LanguageExamSession).where(LanguageExamSession.id == record.session_id))).scalar_one()
        row.exam_state = {
            "version": 3,
            "sections": ["speaking"],
            "speaking": {"results": [{"bank_item_id": recent_id, "bank_item_subskill": "routine_description"}]},
        }
        flag_modified(row, "exam_state")
        await db.commit()

    async with postgres_session_factory() as db:
        recent_ids = await language_exam._recent_speaking_exclusion_ids(
            db,
            language_id=record.language_id,
            student_id=record.student_id,
        )
        item = await language_exam._speaking_bank_prompt(
            db,
            language_id=record.language_id,
            level_str="A2",
            recent_item_ids=recent_ids,
        )

    assert recent_id in recent_ids
    assert item is not None
    assert item["bank_item_id"] == fresh_id


async def test_speaking_bank_prompt_allows_recent_item_when_bank_is_too_thin(
    postgres_session_factory,
    exam_record_factory,
) -> None:
    record = await exam_record_factory(
        state={"version": 3, "state_revision": 1, "sections": [], "cursor": 0},
        status="completed",
    )
    only_id = await _insert_speaking_bank_item(
        postgres_session_factory,
        language_id=record.language_id,
        level="B1",
        prompt_text="Only available prompt.",
        subskill="past_narration",
    )

    async with postgres_session_factory() as db:
        item = await language_exam._speaking_bank_prompt(
            db,
            language_id=record.language_id,
            level_str="B1",
            recent_item_ids={only_id},
        )

    assert item is not None
    assert item["bank_item_id"] == only_id


async def test_speaking_bank_prompt_falls_back_to_used_subskill_when_none_unused_available(
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """The diversity rule is a preference, not a hard requirement: if every eligible item at the
    target level shares an already-used subskill, _speaking_bank_prompt must still return a valid
    prompt (the same one it would have returned without the preference) rather than failing or
    falling all the way back to AI generation just because no fresh subskill exists."""
    record = await exam_record_factory(
        state={"version": 3, "state_revision": 1, "sections": [], "cursor": 0},
        status="abandoned",
    )
    only_id = await _insert_speaking_bank_item(
        postgres_session_factory,
        language_id=record.language_id,
        level="B1",
        prompt_text="ONLY_ITEM_AT_THIS_LEVEL",
        subskill="self_intro",
    )

    async with postgres_session_factory() as db:
        item = await language_exam._speaking_bank_prompt(
            db, language_id=record.language_id, level_str="B1", used_subskills={"self_intro"}
        )

    assert item is not None, "a thin bank must still produce a prompt when no unused subskill exists"
    assert item["bank_item_id"] == only_id


async def test_select_placement_bank_items_exclude_subskills_is_a_soft_optional_filter(
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """Direct service-level proof: exclude_subskills narrows results when passed, and has zero
    effect when omitted -- confirming the diversity filter is purely additive/opt-in, exactly like
    require_mvp_marker, and cannot affect any other bank skill since only _speaking_bank_prompt
    ever passes it."""
    record = await exam_record_factory(
        state={"version": 3, "state_revision": 1, "sections": [], "cursor": 0},
        status="abandoned",
    )
    item_id = await _insert_speaking_bank_item(
        postgres_session_factory,
        language_id=record.language_id,
        level="C2",
        prompt_text="Nuanced argument prompt.",
        subskill="nuanced_argument",
    )

    async with postgres_session_factory() as db:
        without_exclusion = await select_placement_bank_items(
            db, language_id=record.language_id, skill="speaking_prompt", level="C2", count=5,
            require_mvp_marker=True,
        )
        with_exclusion = await select_placement_bank_items(
            db, language_id=record.language_id, skill="speaking_prompt", level="C2", count=5,
            require_mvp_marker=True, exclude_subskills=["nuanced_argument"],
        )

    assert item_id in {row.id for row in without_exclusion}
    assert item_id not in {row.id for row in with_exclusion}
    assert with_exclusion == []


async def test_speaking_bank_prompt_falls_back_to_adjacent_level_for_unused_subskill(
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """Regression for the QA-observed repeated self_intro/self_intro: when the target level's
    only subskill has already been used this session (e.g. A1 = self_intro only), and no other
    subskill exists at that level, _speaking_bank_prompt must search an adjacent CEFR level
    (+/-1 band) for an unused subskill before ever repeating the used one -- priority order steps
    1 then 2."""
    record = await exam_record_factory(
        state={"version": 3, "state_revision": 1, "sections": [], "cursor": 0},
        status="abandoned",
    )
    used_a1_id = await _insert_speaking_bank_item(
        postgres_session_factory,
        language_id=record.language_id,
        level="A1",
        prompt_text="ALREADY_USED_SELF_INTRO",
        subskill="self_intro",
    )
    fresh_a2_id = await _insert_speaking_bank_item(
        postgres_session_factory,
        language_id=record.language_id,
        level="A2",
        prompt_text="FRESH_ROUTINE_DESCRIPTION",
        subskill="routine_description",
    )

    async with postgres_session_factory() as db:
        item = await language_exam._speaking_bank_prompt(
            db,
            language_id=record.language_id,
            level_str="A1",
            used_item_ids={used_a1_id},
            used_subskills={"self_intro"},
        )

    assert item is not None
    assert item["bank_item_id"] == fresh_a2_id
    assert item["subskill"] == "routine_description"
    assert item["level"] == "A2", "must genuinely come from the adjacent level, not the target level"


async def test_speaking_bank_prompt_falls_back_to_same_level_repeat_when_no_adjacent_unused_subskill(
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """The adjacent-level search is still a soft preference, not a hard requirement (priority
    order step 3): if neither the target level nor any adjacent level has an unused subskill,
    selection must still return a valid, not-yet-used prompt at the target level -- even though
    its subskill repeats -- rather than failing the turn."""
    record = await exam_record_factory(
        state={"version": 3, "state_revision": 1, "sections": [], "cursor": 0},
        status="abandoned",
    )
    used_id = await _insert_speaking_bank_item(
        postgres_session_factory,
        language_id=record.language_id,
        level="A1",
        prompt_text="ALREADY_USED_SELF_INTRO",
        subskill="self_intro",
    )
    other_id = await _insert_speaking_bank_item(
        postgres_session_factory,
        language_id=record.language_id,
        level="A1",
        prompt_text="SECOND_SELF_INTRO_ITEM",
        subskill="self_intro",
    )

    async with postgres_session_factory() as db:
        item = await language_exam._speaking_bank_prompt(
            db,
            language_id=record.language_id,
            level_str="A1",
            used_item_ids={used_id},
            used_subskills={"self_intro"},
        )

    assert item is not None, "must still produce a prompt when no unused subskill exists anywhere nearby"
    assert item["bank_item_id"] == other_id
    assert item["bank_item_id"] != used_id


async def test_speaking_bank_prompt_adjacent_level_search_still_excludes_legacy_rows(
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """The adjacent-level tier must apply the same MVP-only filter as the target-level tier: a
    legacy (pre-MVP) row at the adjacent level must never be selected just because it's the only
    candidate there -- selection must fall through and safely return None (triggering the
    existing AI-generation fallback) rather than ever surfacing a legacy row."""
    record = await exam_record_factory(
        state={"version": 3, "state_revision": 1, "sections": [], "cursor": 0},
        status="abandoned",
    )
    used_a1_id = await _insert_speaking_bank_item(
        postgres_session_factory,
        language_id=record.language_id,
        level="A1",
        prompt_text="ALREADY_USED_SELF_INTRO",
        subskill="self_intro",
    )
    await _insert_legacy_speaking_bank_item(
        postgres_session_factory,
        language_id=record.language_id,
        level="A2",
        prompt_text="LEGACY_SHOULD_NOT_BE_SELECTED",
    )

    async with postgres_session_factory() as db:
        item = await language_exam._speaking_bank_prompt(
            db,
            language_id=record.language_id,
            level_str="A1",
            used_item_ids={used_a1_id},
            used_subskills={"self_intro"},
        )

    assert item is None


async def test_old_in_flight_speaking_session_without_pending_bank_item_id_still_works(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """MVP wiring Test G: a session created before this change (its "speaking" dict predates the
    pending_bank_item_id key entirely) must keep working exactly as before -- falling back to
    AI-generated next_question, with no crash from the new .get("pending_bank_item_id")."""
    state = _speaking_state()  # pre-existing fixture, deliberately has no pending_bank_item_id key
    record = await exam_record_factory(state=state)
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(language_exam, "_effective_level", lambda *_args, **_kwargs: _async("A2"))

    async def fake_assess(**kwargs) -> SpeakingTurnAssessment:
        return SpeakingTurnAssessment(
            transcription=kwargs["transcript"],
            grammar_vocab_feedback="No material issue.",
            pronunciation_feedback="",
            fluency_note="Coherent response.",
            estimated_level=CEFRLevel.A2,
            next_question="What activity would you like to join next?",
        )

    await _fake_audio_and_stt(monkeypatch)
    monkeypatch.setattr(language_exam.ai_engine, "assess_speaking", fake_assess)

    async with postgres_session_factory() as db:
        await language_exam.speaking_turn(
            record.session_id,
            BackgroundTasks(),
            file=SimpleNamespace(filename="a.webm"),
            duration_seconds=None,
            request_id="old-session-turn-1",
            state_revision=state["state_revision"],
            turn_token=state["speaking"]["turn_token"],
            section=None,
            student=record.student,
            db=db,
        )

    stored = await _stored_exam(postgres_session_factory, record.session_id)
    sp = stored.exam_state["speaking"]
    assert sp["pending_question"] == "What activity would you like to join next?"
    assert sp["results"][0]["bank_item_id"] is None
    assert sp["done"] is False
    assert sp["turn"] == 2


async def test_speaking_stt_wait_does_not_hold_the_exam_row_lock(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """The slow STT phase must run after releasing every transaction and row lock."""

    state = _speaking_state()
    record = await exam_record_factory(state=state)
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(language_exam, "_effective_level", lambda *_args, **_kwargs: _async("A2"))

    audio = ValidatedAudio(
        data=b"single-server-audio",
        mime_type="audio/webm",
        suffix=".webm",
        sha256=hashlib.sha256(b"single-server-audio").hexdigest(),
        duration_seconds=3.0,
    )
    stt_started = asyncio.Event()
    release_stt = asyncio.Event()

    async def fake_read(_file) -> ValidatedAudio:
        return audio

    async def waiting_stt(_audio: ValidatedAudio) -> ConversationTranscription:
        stt_started.set()
        await asyncio.wait_for(release_stt.wait(), timeout=5)
        return ConversationTranscription(
            text="I came to meet my neighbours and help organize this event",
            engine="test-stt",
            model="test-model",
        )

    async def fake_assess(**kwargs) -> SpeakingTurnAssessment:
        return SpeakingTurnAssessment(
            transcription=kwargs["transcript"],
            grammar_vocab_feedback="No material issue.",
            pronunciation_feedback="",
            fluency_note="Coherent response.",
            estimated_level=CEFRLevel.A2,
            next_question="What would you organize next?",
        )

    monkeypatch.setattr(language_exam, "_read_speaking_audio", fake_read)
    monkeypatch.setattr(language_exam, "_verified_server_transcription", waiting_stt)
    monkeypatch.setattr(language_exam.ai_engine, "assess_speaking", fake_assess)

    async def submit():
        async with postgres_session_factory() as db:
            return await language_exam.speaking_turn(
                record.session_id,
                BackgroundTasks(),
                file=SimpleNamespace(filename="single.webm"),
                duration_seconds=None,
                request_id="single-speaking-request-0001",
                state_revision=state["state_revision"],
                turn_token=state["speaking"]["turn_token"],
                section=None,
                student=record.student,
                db=db,
            )

    submit_task = asyncio.create_task(submit())
    await asyncio.wait_for(stt_started.wait(), timeout=5)

    # NOWAIT is intentional: this would raise LockNotAvailableError immediately if speaking_turn
    # retained the row lock (or even an earlier SELECT FOR UPDATE) during STT.
    async with postgres_session_factory() as competing_db:
        locked = (
            await competing_db.execute(
                select(LanguageExamSession)
                .where(LanguageExamSession.id == record.session_id)
                .with_for_update(nowait=True)
            )
        ).scalar_one()
        assert locked.id == record.session_id
        await competing_db.rollback()

    release_stt.set()
    response = await asyncio.wait_for(submit_task, timeout=10)
    assert response.state_revision == state["state_revision"] + 1

    stored = await _stored_exam(postgres_session_factory, record.session_id)
    assert len(stored.exam_state["speaking"]["results"]) == 1


async def _async(value):
    return value


async def test_two_concurrent_initiates_create_one_active_exam(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """The two-phase initiate flow must recheck under the per-user PostgreSQL row lock."""

    # An abandoned historical row supplies the real user/language identities without being an
    # active attempt that initiate_exam could resume.
    record = await exam_record_factory(
        state={"version": 3, "state_revision": 1, "sections": [], "cursor": 0},
        status="abandoned",
    )
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        language_exam,
        "get_default_language",
        lambda _db: _async(SimpleNamespace(id=record.language_id)),
    )
    monkeypatch.setattr(language_exam, "_effective_level", lambda *_args, **_kwargs: _async("A2"))
    monkeypatch.setattr(language_exam, "_student_grade", lambda *_args, **_kwargs: _async(None))

    scenario_arrivals = 0
    scenario_lock = asyncio.Lock()
    both_generating = asyncio.Event()

    async def generate_scenario(**_kwargs) -> dict:
        nonlocal scenario_arrivals
        async with scenario_lock:
            scenario_arrivals += 1
            if scenario_arrivals == 2:
                both_generating.set()
        await asyncio.wait_for(both_generating.wait(), timeout=5)
        return {
            "scenario": "At a community event",
            "ai_persona": "Host",
            "student_role": "Guest",
            "setting": "Community hall",
            "opening_question": "What brought you to the event?",
        }

    monkeypatch.setattr(
        language_exam.ai_engine,
        "generate_scenario_and_opening",
        generate_scenario,
    )

    async def initiate():
        async with postgres_session_factory() as db:
            return await language_exam.initiate_exam(
                BackgroundTasks(),
                student=record.student,
                db=db,
            )

    responses = await asyncio.wait_for(
        asyncio.gather(initiate(), initiate()),
        timeout=15,
    )

    assert scenario_arrivals == 2
    assert responses[0].session_id == responses[1].session_id
    async with postgres_session_factory() as db:
        active = (
            await db.execute(
                select(LanguageExamSession).where(
                    LanguageExamSession.student_id == record.student_id,
                    LanguageExamSession.language_id == record.language_id,
                    LanguageExamSession.status.in_(("in_progress", "evaluating")),
                )
            )
        ).scalars().all()
    assert len(active) == 1
    assert active[0].id == responses[0].session_id


async def test_new_exam_session_never_includes_interview_in_sections(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """Product decision: new AI Exam sessions must never include "interview" in their persisted
    sections. Speaking stays mandatory and unaffected (its own section is unchanged)."""
    assert "interview" not in language_exam.SECTIONS
    assert "speaking" in language_exam.SECTIONS
    assert language_exam.SPEAKING_TURNS == 3

    record = await exam_record_factory(
        state={"version": 3, "state_revision": 1, "sections": [], "cursor": 0},
        status="abandoned",
    )
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        language_exam,
        "get_default_language",
        lambda _db: _async(SimpleNamespace(id=record.language_id)),
    )
    monkeypatch.setattr(language_exam, "_effective_level", lambda *_args, **_kwargs: _async("A2"))
    monkeypatch.setattr(language_exam, "_student_grade", lambda *_args, **_kwargs: _async(None))

    async def generate_scenario(**_kwargs) -> dict:
        return {
            "scenario": "At a community event",
            "ai_persona": "Host",
            "student_role": "Guest",
            "setting": "Community hall",
            "opening_question": "What brought you to the event?",
        }

    monkeypatch.setattr(language_exam.ai_engine, "generate_scenario_and_opening", generate_scenario)

    async with postgres_session_factory() as db:
        student = await db.get(User, record.student_id)
        response = await language_exam.initiate_exam(BackgroundTasks(), student=student, db=db)

    stored = await _stored_exam(postgres_session_factory, response.session_id)
    assert "interview" not in stored.exam_state["sections"]
    assert "interview" not in stored.exam_state
    assert stored.exam_state["speaking"]["total_turns"] == 3


async def test_initiate_exam_does_not_touch_expired_student_attributes_after_ai_call(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """Regression test for a live MissingGreenlet 500: initiate_exam must not read
    student.id/language.id as bare ORM attributes after the mid-function commit that precedes
    the external AI call. In production, expire_on_commit marks them stale and a slow-enough
    network call lets the connection pool recycle the connection; the next bare attribute read
    then tries an implicit lazy-reload outside any awaited call and raises MissingGreenlet.

    That exact failure is connection-pool-timing dependent (confirmed empirically: a 50ms
    asyncio.sleep between commit and the next access was not sufficient to reproduce it against
    the test database, even against the unfixed code). To make this a reliable regression guard
    rather than a flaky timing-dependent one, this test forces the same *condition* the
    production bug depends on — student/language becoming unusable after the pre-AI-call commit —
    by expiring and detaching them from the session at exactly that point. Real ORM objects are
    used for both (unlike the concurrent-initiate test above, which passes a SimpleNamespace for
    student and so never exercises this at all). Without the fix, this raises
    sqlalchemy.orm.exc.DetachedInstanceError from the same lines the real MissingGreenlet did.
    """

    record = await exam_record_factory(
        state={"version": 3, "state_revision": 1, "sections": [], "cursor": 0},
        status="abandoned",
    )
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(language_exam, "_effective_level", lambda *_args, **_kwargs: _async("A2"))
    monkeypatch.setattr(language_exam, "_student_grade", lambda *_args, **_kwargs: _async(None))

    async def generate_scenario(**_kwargs) -> dict:
        return {
            "scenario": "At a community event",
            "ai_persona": "Host",
            "student_role": "Guest",
            "setting": "Community hall",
            "opening_question": "What brought you to the event?",
        }

    monkeypatch.setattr(language_exam.ai_engine, "generate_scenario_and_opening", generate_scenario)

    async with postgres_session_factory() as db:
        student = await db.get(User, record.student_id)
        language = await db.get(Language, record.language_id)
        monkeypatch.setattr(language_exam, "get_default_language", lambda _db: _async(language))

        real_commit = db.commit
        expired_once = False

        async def commit_then_expire_and_detach():
            nonlocal expired_once
            await real_commit()
            if not expired_once:
                expired_once = True
                db.expire(student)
                db.expire(language)
                db.expunge(student)
                db.expunge(language)

        monkeypatch.setattr(db, "commit", commit_then_expire_and_detach)

        response = await language_exam.initiate_exam(
            BackgroundTasks(),
            student=student,
            db=db,
        )

    assert response.session_id is not None
    async with postgres_session_factory() as db:
        active = (
            await db.execute(
                select(LanguageExamSession).where(
                    LanguageExamSession.student_id == record.student_id,
                    LanguageExamSession.status.in_(("in_progress", "evaluating")),
                )
            )
        ).scalar_one()
    assert active.id == response.session_id


def _completed_evidence_state() -> dict:
    objective = {
        "ready": True,
        "pool": {"A2": {"question": "q", "options": ["a"], "correct_index": 0}},
        "asked": [{"level": "A2", "correct": True, "chosen_index": 0}],
        "done": True,
        "evidence_status": "completed",
    }
    speaking_results = [
        {
            "question": f"Speaking question {index}",
            "transcription": f"Verified speaking response number {index}",
            "audio_sha256": hashlib.sha256(f"speaking-{index}".encode()).hexdigest(),
        }
        for index in range(3)
    ]
    return {
        "version": 3,
        "state_revision": 21,
        "sections": list(language_exam.SECTIONS),
        "cursor": len(language_exam.SECTIONS),
        "listening": copy.deepcopy(objective),
        "reading": copy.deepcopy(objective),
        "grammar_vocab": copy.deepcopy(objective),
        "writing": {
            "ready": True,
            "prompt": "Write a detailed response.",
            "min_words": 40,
            "response": " ".join(f"word{index}" for index in range(45)),
            "done": True,
            "evidence_status": "completed",
        },
        "speaking": {
            "total_turns": 3,
            "results": speaking_results,
            "done": True,
            "evidence_status": "completed",
        },
        # No "interview" section — matches a genuine no-interview session (product decision:
        # guided interview removed; "sections" already derives from language_exam.SECTIONS above,
        # which no longer includes it).
        "evaluation": {
            "evaluation_status": "pending",
            "evaluation_attempt": 0,
            "evaluation_owner": None,
            "evaluation_lease_expires_at": None,
        },
        "request_receipts": [],
    }


async def test_evaluation_lease_has_one_owner_and_one_expired_lease_successor(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    record = await exam_record_factory(state=_completed_evidence_state(), status="evaluating")
    monkeypatch.setattr(language_exam, "AsyncSessionLocal", postgres_session_factory)
    monkeypatch.setattr(language_exam, "check", lambda *_args, **_kwargs: True)

    initial_claims = await asyncio.wait_for(
        asyncio.gather(
            language_exam._claim_evaluation_lease(record.session_id),
            language_exam._claim_evaluation_lease(record.session_id),
        ),
        timeout=10,
    )
    initial_winners = [claim for claim in initial_claims if claim is not None]
    assert len(initial_winners) == 1
    first_owner = initial_winners[0][0]

    stored = await _stored_exam(postgres_session_factory, record.session_id)
    assert stored.exam_state["evaluation"]["evaluation_owner"] == first_owner
    assert stored.exam_state["evaluation"]["evaluation_attempt"] == 1

    async with postgres_session_factory() as db:
        exam = (
            await db.execute(
                select(LanguageExamSession)
                .where(LanguageExamSession.id == record.session_id)
                .with_for_update()
            )
        ).scalar_one()
        expired = copy.deepcopy(exam.exam_state or {})
        expired["evaluation"]["evaluation_lease_expires_at"] = (
            datetime.now(timezone.utc) - timedelta(seconds=1)
        ).isoformat()
        exam.exam_state = expired
        flag_modified(exam, "exam_state")
        await db.commit()

    recovery_claims = await asyncio.wait_for(
        asyncio.gather(
            language_exam._claim_evaluation_lease(record.session_id),
            language_exam._claim_evaluation_lease(record.session_id),
        ),
        timeout=10,
    )
    recovery_winners = [claim for claim in recovery_claims if claim is not None]
    assert len(recovery_winners) == 1
    successor_owner = recovery_winners[0][0]
    assert successor_owner != first_owner

    stored = await _stored_exam(postgres_session_factory, record.session_id)
    evaluation = stored.exam_state["evaluation"]
    assert evaluation["evaluation_status"] == "running"
    assert evaluation["evaluation_owner"] == successor_owner
    assert evaluation["evaluation_attempt"] == 2
    assert datetime.fromisoformat(evaluation["evaluation_lease_expires_at"]) > datetime.now(
        timezone.utc
    )


async def test_two_concurrent_evaluation_retries_enqueue_one_worker(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    state = _completed_evidence_state()
    state["state_revision"] = 31
    state["evaluation"] = {
        "evaluation_status": "scorer_unavailable",
        "evaluation_attempt": 1,
        "evaluation_owner": None,
        "evaluation_lease_expires_at": None,
        "error_code": "scorer_unavailable",
    }
    record = await exam_record_factory(state=state, status="failed")
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_args, **_kwargs: None)

    backgrounds = [BackgroundTasks(), BackgroundTasks()]

    async def retry(index: int):
        async with postgres_session_factory() as db:
            return await language_exam.retry_exam_evaluation(
                record.session_id,
                backgrounds[index],
                student=record.student,
                db=db,
            )

    responses = await asyncio.wait_for(
        asyncio.gather(retry(0), retry(1)),
        timeout=10,
    )

    assert all(response.session_id == record.session_id for response in responses)
    assert sum(len(background.tasks) for background in backgrounds) == 1
    stored = await _stored_exam(postgres_session_factory, record.session_id)
    assert stored.status == "evaluating"
    assert stored.exam_state["evaluation"]["evaluation_status"] == "pending"
    assert stored.exam_state["state_revision"] == state["state_revision"] + 1


async def test_ai_grading_failure_completes_with_low_confidence_fallback_report(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    record = await exam_record_factory(state=_completed_evidence_state(), status="evaluating")
    monkeypatch.setattr(language_exam, "AsyncSessionLocal", postgres_session_factory)
    monkeypatch.setattr(language_exam, "check", lambda *_args, **_kwargs: True)

    async def unavailable_speaking_grader(**_kwargs):
        raise ExamAIError("authoritative speaking scorer unavailable")

    monkeypatch.setattr(language_exam.ai_engine, "grade_speaking", unavailable_speaking_grader)

    await language_exam._run_evaluation(record.session_id)

    stored = await _stored_exam(postgres_session_factory, record.session_id)
    evaluation = stored.exam_state["evaluation"]
    assert stored.status == "completed"
    assert stored.is_completed is True
    assert stored.assessment_report is not None
    assert stored.assessment_report["scorer_fallback_used"] is True
    assert stored.assessment_report["confidence"] <= 0.55
    assert evaluation["evaluation_status"] == "completed"
    assert evaluation.get("error_code") is None
    assert evaluation["evaluation_lease_expires_at"] is None

    async with postgres_session_factory() as db:
        analytics = await db.get(
            LanguageAnalytics,
            {"student_id": record.student_id, "language_id": record.language_id},
        )
        profile = (
            await db.execute(
                select(LanguageStudentProfile).where(
                    LanguageStudentProfile.student_id == record.student_id,
                    LanguageStudentProfile.language_id == record.language_id,
                )
            )
        ).scalar_one_or_none()
    assert analytics is not None
    assert profile is not None


async def test_malformed_ai_grading_output_completes_with_fallback_report(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """Schema-invalid AI grading output should no longer strand the student on a failed final
    page; the evaluator completes with a clearly marked low-confidence fallback report."""

    record = await exam_record_factory(state=_completed_evidence_state(), status="evaluating")
    monkeypatch.setattr(language_exam, "AsyncSessionLocal", postgres_session_factory)
    monkeypatch.setattr(language_exam, "check", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(language_exam.ai_engine, "_mock", False)

    async def malformed_llm_json(*_args, **_kwargs):
        # Schema-invalid: "fluency" is out of the 0.0-10.0 range Pydantic enforces.
        return (
            '{"level": "B1", "fluency": 999.0, "lexical": 5.0, "grammar": 5.0, '
            '"pronunciation": 0.0, "score": 5.0}'
        )

    monkeypatch.setattr(language_exam_service, "generate_llm_json", malformed_llm_json)

    await language_exam._run_evaluation(record.session_id)

    stored = await _stored_exam(postgres_session_factory, record.session_id)
    evaluation = stored.exam_state["evaluation"]
    assert stored.status == "completed"
    assert stored.is_completed is True
    assert stored.assessment_report is not None
    assert stored.assessment_report["scorer_fallback_used"] is True
    assert stored.assessment_report["confidence"] <= 0.55
    assert evaluation["evaluation_status"] == "completed"
    assert evaluation.get("error_code") is None

    async with postgres_session_factory() as db:
        analytics = await db.get(
            LanguageAnalytics,
            {"student_id": record.student_id, "language_id": record.language_id},
        )
        profile = (
            await db.execute(
                select(LanguageStudentProfile).where(
                    LanguageStudentProfile.student_id == record.student_id,
                    LanguageStudentProfile.language_id == record.language_id,
                )
            )
        ).scalar_one_or_none()
    assert analytics is not None
    assert profile is not None


async def test_evaluation_heartbeat_prevents_a_second_live_worker(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """A healthy slow scorer renews its lease, so no second billable evaluation starts."""

    record = await exam_record_factory(state=_completed_evidence_state(), status="evaluating")
    monkeypatch.setattr(language_exam, "AsyncSessionLocal", postgres_session_factory)
    monkeypatch.setattr(language_exam, "check", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(language_exam, "EVALUATION_LEASE_SECONDS", 1)

    first_grader_waiting = asyncio.Event()
    release_first_grader = asyncio.Event()
    grader_calls = 0
    grader_call_lock = asyncio.Lock()

    speaking_grade = SpeakingGradeSchema(
        level=CEFRLevel.B1,
        fluency=5.0,
        lexical=5.0,
        grammar=5.0,
        pronunciation=0.0,
        score=5.0,
        feedback="Pronunciation was unassessed.",
        detected_errors=[],
    )
    writing_grade = WritingGradeSchema(
        level=CEFRLevel.B1,
        task_achievement=5.0,
        coherence=5.0,
        lexical=5.0,
        grammar=5.0,
        score=5.0,
        feedback="A complete response.",
        detected_errors=[],
    )
    narrative = ExamNarrativeSchema(
        summary="The verified evidence supports a conservative B1 placement.",
        strengths=["Communicates connected ideas."],
        weaknesses=["Needs more grammatical range."],
        recommendations=["Practise connected speech.", "Review verb forms.", "Read daily."],
        detected_errors=[],
        recommended_starting_lesson_topic="Past and present verb forms",
    )

    async def controlled_speaking_grade(**_kwargs) -> SpeakingGradeSchema:
        nonlocal grader_calls
        async with grader_call_lock:
            grader_calls += 1
            call_number = grader_calls
        if call_number == 1:
            first_grader_waiting.set()
            await asyncio.wait_for(release_first_grader.wait(), timeout=10)
        return speaking_grade

    async def successful_writing_grade(**_kwargs) -> WritingGradeSchema:
        return writing_grade

    async def successful_narrative(**_kwargs) -> ExamNarrativeSchema:
        return narrative

    monkeypatch.setattr(language_exam.ai_engine, "grade_speaking", controlled_speaking_grade)
    monkeypatch.setattr(language_exam.ai_engine, "grade_writing", successful_writing_grade)
    monkeypatch.setattr(language_exam.ai_engine, "build_final_narrative", successful_narrative)

    original_next_retake = language_exam.next_allowed_retake_at
    projection_calls = 0

    def counted_next_retake(now):
        nonlocal projection_calls
        projection_calls += 1
        return original_next_retake(now)

    monkeypatch.setattr(language_exam, "next_allowed_retake_at", counted_next_retake)

    stale_worker = asyncio.create_task(language_exam._run_evaluation(record.session_id))
    await asyncio.wait_for(first_grader_waiting.wait(), timeout=5)
    # Wait beyond the original one-second lease. The heartbeat must have extended it.
    await asyncio.sleep(1.2)
    successor_worker = asyncio.create_task(language_exam._run_evaluation(record.session_id))
    await asyncio.wait_for(successor_worker, timeout=10)
    release_first_grader.set()
    await asyncio.wait_for(stale_worker, timeout=10)

    stored = await _stored_exam(postgres_session_factory, record.session_id)
    assert stored.status == "completed"
    assert stored.is_completed is True
    assert stored.assessment_report is not None
    assert stored.exam_state["evaluation"]["evaluation_status"] == "completed"
    assert stored.exam_state["evaluation"]["evaluation_attempt"] == 1
    assert grader_calls == 1
    assert projection_calls == 1

    async with postgres_session_factory() as db:
        analytics_rows = (
            await db.execute(
                select(LanguageAnalytics).where(
                    LanguageAnalytics.student_id == record.student_id,
                    LanguageAnalytics.language_id == record.language_id,
                )
            )
        ).scalars().all()
        profile_rows = (
            await db.execute(
                select(LanguageStudentProfile).where(
                    LanguageStudentProfile.student_id == record.student_id,
                    LanguageStudentProfile.language_id == record.language_id,
                )
            )
        ).scalars().all()
    assert len(analytics_rows) == 1
    assert len(profile_rows) == 1


async def test_no_interview_exam_completes_without_live_phase_unavailable_penalty(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """A fully-evidenced no-interview session (3 speaking turns + listening/reading/grammar_vocab
    + writing, no "interview" section at all) must reach evaluation, complete normally, and set
    placement_completed_at through the ordinary AI Exam completion flow. It must NOT be penalized
    with cross_phase_consistency="live_phase_unavailable" (and the accompanying low confidence
    cap) merely because interview was intentionally removed by design — that label previously
    meant "the interview phase ran but produced no results", not "there was no interview phase to
    begin with"."""

    state = _completed_evidence_state()
    assert "interview" not in state["sections"]
    record = await exam_record_factory(state=state, status="evaluating")
    monkeypatch.setattr(language_exam, "AsyncSessionLocal", postgres_session_factory)
    monkeypatch.setattr(language_exam, "check", lambda *_args, **_kwargs: True)

    speaking_grade = SpeakingGradeSchema(
        level=CEFRLevel.B1, fluency=5.0, lexical=5.0, grammar=5.0, pronunciation=0.0,
        score=5.0, feedback="Pronunciation was unassessed.", detected_errors=[],
    )
    writing_grade = WritingGradeSchema(
        level=CEFRLevel.B1, task_achievement=5.0, coherence=5.0, lexical=5.0, grammar=5.0,
        score=5.0, feedback="A complete response.", detected_errors=[],
    )
    narrative = ExamNarrativeSchema(
        summary="No-interview placement.",
        strengths=["Communicates clearly."],
        weaknesses=["Needs more grammatical range."],
        recommendations=["Practise connected speech.", "Review verb forms.", "Read daily."],
        detected_errors=[],
        recommended_starting_lesson_topic="Past and present verb forms",
    )

    async def successful_speaking_grade(**_kwargs) -> SpeakingGradeSchema:
        return speaking_grade

    async def successful_writing_grade(**_kwargs) -> WritingGradeSchema:
        return writing_grade

    async def successful_narrative(**_kwargs) -> ExamNarrativeSchema:
        return narrative

    monkeypatch.setattr(language_exam.ai_engine, "grade_speaking", successful_speaking_grade)
    monkeypatch.setattr(language_exam.ai_engine, "grade_writing", successful_writing_grade)
    monkeypatch.setattr(language_exam.ai_engine, "build_final_narrative", successful_narrative)

    await language_exam._run_evaluation(record.session_id)

    stored = await _stored_exam(postgres_session_factory, record.session_id)
    assert stored.status == "completed"
    assert stored.is_completed is True
    assert stored.assessment_report is not None
    assert "interview" not in (stored.exam_state.get("sections") or [])
    assert stored.assessment_report["cross_phase_consistency"] != "live_phase_unavailable"
    assert stored.assessment_report["confidence"] > 0.5

    async with postgres_session_factory() as db:
        profile = (
            await db.execute(
                select(LanguageStudentProfile).where(
                    LanguageStudentProfile.student_id == record.student_id,
                    LanguageStudentProfile.language_id == record.language_id,
                )
            )
        ).scalar_one()
    assert profile.placement_completed_at is not None


async def test_placement_completed_at_is_set_once_and_survives_a_retake(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """AI Exam completion is the sole writer of placement_completed_at; a retake must not reset it."""

    record = await exam_record_factory(state=_completed_evidence_state(), status="evaluating")
    monkeypatch.setattr(language_exam, "AsyncSessionLocal", postgres_session_factory)
    monkeypatch.setattr(language_exam, "check", lambda *_args, **_kwargs: True)

    speaking_grade = SpeakingGradeSchema(
        level=CEFRLevel.B1,
        fluency=5.0,
        lexical=5.0,
        grammar=5.0,
        pronunciation=0.0,
        score=5.0,
        feedback="Pronunciation was unassessed.",
        detected_errors=[],
    )
    writing_grade = WritingGradeSchema(
        level=CEFRLevel.B1,
        task_achievement=5.0,
        coherence=5.0,
        lexical=5.0,
        grammar=5.0,
        score=5.0,
        feedback="A complete response.",
        detected_errors=[],
    )
    narrative = ExamNarrativeSchema(
        summary="First placement.",
        strengths=["Communicates connected ideas."],
        weaknesses=["Needs more grammatical range."],
        recommendations=["Practise connected speech.", "Review verb forms.", "Read daily."],
        detected_errors=[],
        recommended_starting_lesson_topic="Past and present verb forms",
    )

    async def successful_speaking_grade(**_kwargs) -> SpeakingGradeSchema:
        return speaking_grade

    async def successful_writing_grade(**_kwargs) -> WritingGradeSchema:
        return writing_grade

    async def successful_narrative(**_kwargs) -> ExamNarrativeSchema:
        return narrative

    monkeypatch.setattr(language_exam.ai_engine, "grade_speaking", successful_speaking_grade)
    monkeypatch.setattr(language_exam.ai_engine, "grade_writing", successful_writing_grade)
    monkeypatch.setattr(language_exam.ai_engine, "build_final_narrative", successful_narrative)

    await language_exam._run_evaluation(record.session_id)

    async def _load_profile() -> LanguageStudentProfile:
        async with postgres_session_factory() as db:
            return (
                await db.execute(
                    select(LanguageStudentProfile).where(
                        LanguageStudentProfile.student_id == record.student_id,
                        LanguageStudentProfile.language_id == record.language_id,
                    )
                )
            ).scalar_one()

    profile = await _load_profile()
    assert profile.placement_completed_at is not None
    first_completed_at = profile.placement_completed_at
    first_last_assessment = profile.last_assessment_date

    # Simulate a retake: a second, independently-completed session for the same student/language.
    async with postgres_session_factory() as db:
        second_exam = LanguageExamSession(
            id=uuid.uuid4().hex,
            student_id=record.student_id,
            language_id=record.language_id,
            current_step=1,
            max_steps=len(language_exam.SECTIONS),
            exam_state=copy.deepcopy(_completed_evidence_state()),
            status="evaluating",
            is_completed=False,
        )
        db.add(second_exam)
        await db.commit()
        second_session_id = second_exam.id

    await language_exam._run_evaluation(second_session_id)

    second_stored = await _stored_exam(postgres_session_factory, second_session_id)
    assert second_stored.status == "completed"
    assert second_stored.is_completed is True

    profile = await _load_profile()
    assert profile.placement_completed_at == first_completed_at
    assert profile.last_assessment_date is not None
    assert profile.last_assessment_date >= first_last_assessment


def _completed_evidence_state_with_mvp_bank_turns(bank_item_ids: list[int]) -> dict:
    """Same shape as _completed_evidence_state(), but with realistic MVP-bank-backed speaking
    turns (bank_item_id/bank_item_subskill/audio_duration_seconds/stt_engine populated) so the
    Speaking Assessment Core's bank-metadata lookup and evidence fields have real data to reflect."""
    state = _completed_evidence_state()
    subskills = ["self_intro", "routine_description", "past_narration"]
    state["speaking"]["results"] = [
        {
            "question": f"Speaking question {index}",
            "transcription": f"Verified speaking response number {index} with enough words to be healthy.",
            "audio_sha256": hashlib.sha256(f"speaking-{index}".encode()).hexdigest(),
            "audio_duration_seconds": 15.0,
            "stt_engine": "openai",
            "bank_item_id": bank_item_ids[index],
            "bank_item_subskill": subskills[index],
        }
        for index in range(3)
    ]
    return state


async def test_final_report_includes_speaking_assessment_core_with_expected_versions_and_evidence(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """Versioning/report test: the final assessment_report must additively carry
    assessment_core_version, speaking_assessment_core_version, speaking_rubric_version,
    scoring_changed=false, and evidence reflecting the real MVP-bank-backed turns used."""
    monkeypatch.setattr(language_exam, "check", lambda *_args, **_kwargs: True)

    record = await exam_record_factory(
        state={"version": 3, "state_revision": 1, "sections": [], "cursor": 0}, status="abandoned"
    )
    bank_item_ids = [
        await _insert_speaking_bank_item(
            postgres_session_factory,
            language_id=record.language_id,
            level="B1",
            prompt_text=f"Prompt {i}",
            subskill=subskill,
        )
        for i, subskill in enumerate(["self_intro", "routine_description", "past_narration"])
    ]

    state = _completed_evidence_state_with_mvp_bank_turns(bank_item_ids)
    record = await exam_record_factory(state=state, status="evaluating")
    monkeypatch.setattr(language_exam, "AsyncSessionLocal", postgres_session_factory)

    speaking_grade = SpeakingGradeSchema(
        level=CEFRLevel.B1, fluency=6.0, lexical=5.5, grammar=7.0, pronunciation=0.0,
        score=6.2, feedback="Pronunciation was unassessed.", detected_errors=[],
    )
    writing_grade = WritingGradeSchema(
        level=CEFRLevel.B1, task_achievement=5.0, coherence=5.0, lexical=5.0, grammar=5.0,
        score=5.0, feedback="A complete response.", detected_errors=[],
    )
    narrative = ExamNarrativeSchema(
        summary="Placement complete.", strengths=["Communicates connected ideas."],
        weaknesses=["Needs more grammatical range."],
        recommendations=["Practise connected speech.", "Review verb forms.", "Read daily."],
        detected_errors=[], recommended_starting_lesson_topic="Past and present verb forms",
    )
    monkeypatch.setattr(language_exam.ai_engine, "grade_speaking", lambda **_kwargs: _async(speaking_grade))
    monkeypatch.setattr(language_exam.ai_engine, "grade_writing", lambda **_kwargs: _async(writing_grade))
    monkeypatch.setattr(language_exam.ai_engine, "build_final_narrative", lambda **_kwargs: _async(narrative))

    await language_exam._run_evaluation(record.session_id)

    stored = await _stored_exam(postgres_session_factory, record.session_id)
    report = stored.assessment_report
    assert report["assessment_core_version"] == "ai_exam_assessment_core_v1"

    sa = report["speaking_assessment"]
    assert sa["speaking_assessment_core_version"] == "speaking_assessment_core_mvp_v1"
    assert sa["speaking_rubric_version"] == "speaking_llm_transcript_rubric_v1"
    assert sa["scoring_changed"] is False
    assert sa["language_evaluation"]["scoring_changed"] is False

    prompt_evidence = sa["prompt_evidence"]
    assert prompt_evidence["expected_turns"] == 3
    assert prompt_evidence["turns_answered"] == 3
    assert prompt_evidence["prompt_source"] == "mvp_speaking_prompt_bank"
    assert prompt_evidence["unique_bank_items_count"] == 3
    assert prompt_evidence["unique_subskills_count"] == 3
    assert prompt_evidence["repeated_subskills"] is False
    assert prompt_evidence["fallback_prompt_used"] is False
    assert prompt_evidence["prompt_review_status"] == "mvp_approved_pending_full_review"
    assert "speaking_prompts_pending_full_review" in sa["review_flags"]
    assert sa["needs_human_review"] is False

    stt_evidence = sa["stt_evidence"]
    assert stt_evidence["transcripts_count"] == 3
    assert stt_evidence["empty_transcripts_count"] == 0
    assert stt_evidence["confidence_available"] is False
    assert stt_evidence["evidence_status"] == "usable"

    prosody_evidence = sa["prosody_evidence"]
    assert prosody_evidence["provider"] == "derived_duration_transcript"
    assert prosody_evidence["runtime_status"] == "partial"
    assert prosody_evidence["evi_runtime_status"] == "not_implemented"
    assert prosody_evidence["acoustic_metrics_available"] is False
    assert prosody_evidence["pause_metrics_available"] is False
    assert prosody_evidence["rhythm_metrics_available"] is False


async def test_speaking_assessment_core_does_not_change_final_scoring_or_completion_behavior(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """No-scoring-change test: adding the Speaking Assessment Core must not alter the final CEFR
    level, the confidence value, or placement_completed_at behavior -- proven by asserting the
    exact values the pre-existing (unmodified) grading formula would produce for these fixed,
    known mocked inputs."""
    monkeypatch.setattr(language_exam, "check", lambda *_args, **_kwargs: True)
    record = await exam_record_factory(state=_completed_evidence_state(), status="evaluating")
    monkeypatch.setattr(language_exam, "AsyncSessionLocal", postgres_session_factory)

    speaking_grade = SpeakingGradeSchema(
        level=CEFRLevel.B1, fluency=6.0, lexical=5.5, grammar=7.0, pronunciation=0.0,
        score=6.2, feedback="Pronunciation was unassessed.", detected_errors=[],
    )
    writing_grade = WritingGradeSchema(
        level=CEFRLevel.B1, task_achievement=5.0, coherence=5.0, lexical=5.0, grammar=5.0,
        score=5.0, feedback="A complete response.", detected_errors=[],
    )
    narrative = ExamNarrativeSchema(
        summary="Placement complete.", strengths=["Communicates connected ideas."],
        weaknesses=["Needs more grammatical range."],
        recommendations=["Practise connected speech.", "Review verb forms.", "Read daily."],
        detected_errors=[], recommended_starting_lesson_topic="Past and present verb forms",
    )
    monkeypatch.setattr(language_exam.ai_engine, "grade_speaking", lambda **_kwargs: _async(speaking_grade))
    monkeypatch.setattr(language_exam.ai_engine, "grade_writing", lambda **_kwargs: _async(writing_grade))
    monkeypatch.setattr(language_exam.ai_engine, "build_final_narrative", lambda **_kwargs: _async(narrative))

    await language_exam._run_evaluation(record.session_id)

    stored = await _stored_exam(postgres_session_factory, record.session_id)
    report = stored.assessment_report
    # Unchanged scoring fields -- identical to what the pre-existing formula produces for this
    # exact mocked grade (score is taken verbatim from grade_speaking's own output, never
    # recomputed by the assessment core).
    assert report["speaking_level"] == "B1"
    assert report["speaking_score"] == 6.2
    assert report["speaking_breakdown"] == {"fluency": 6.0, "lexical": 5.5, "grammar": 7.0}
    # Written anchor (reading/listening at A2, writing at B1) sits one CEFR band from spoken (B1)
    # for this fixture -- abs(gap) == 1, still "consistent", base confidence 0.8 before the
    # existing no-acoustic-scorer discount (*0.85, capped at 0.78): round(0.8 * 0.85, 2) == 0.68.
    assert report["confidence"] == round(min(0.8 * 0.85, 0.78), 2)
    assert report["cross_phase_consistency"] == "consistent"
    assert report["unassessed_components"] == ["speaking.pronunciation"]
    assert stored.status == "completed"
    assert stored.is_completed is True

    async with postgres_session_factory() as db:
        profile = (
            await db.execute(
                select(LanguageStudentProfile).where(
                    LanguageStudentProfile.student_id == record.student_id,
                    LanguageStudentProfile.language_id == record.language_id,
                )
            )
        ).scalar_one()
    assert profile.placement_completed_at is not None


async def test_speaking_turn_result_shape_is_unchanged_by_live_transcription_preview_feature(
    monkeypatch,
    postgres_session_factory,
    exam_record_factory,
) -> None:
    """Backend test 5/5 for the live speaking transcript preview (Task K): submitting a speaking
    turn through the existing, unmodified /speaking/turn flow must still produce exactly the same
    persisted result shape as before this feature -- proving the new live-caption endpoint is
    purely additive and never touches the real submit/grading path."""
    state = _speaking_state()
    record = await exam_record_factory(state=state)
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(language_exam, "_effective_level", lambda *_args, **_kwargs: _async("A2"))
    await _fake_audio_and_stt(monkeypatch)
    monkeypatch.setattr(language_exam.ai_engine, "assess_speaking", _fake_assess_ok())

    async with postgres_session_factory() as db:
        await language_exam.speaking_turn(
            record.session_id,
            BackgroundTasks(),
            file=SimpleNamespace(filename="live-caption-regression.webm"),
            duration_seconds=None,
            request_id="live-caption-regression-request-1",
            state_revision=state["state_revision"],
            turn_token=state["speaking"]["turn_token"],
            section=None,
            student=record.student,
            db=db,
        )

    stored = await _stored_exam(postgres_session_factory, record.session_id)
    results = stored.exam_state["speaking"]["results"]
    assert len(results) == 1
    turn_result = results[0]
    assert set(turn_result.keys()) == {
        "question", "transcription", "grammar_vocab_feedback", "pronunciation_feedback",
        "pronunciation_status", "fluency_note", "estimated_level", "audio_sha256",
        "audio_duration_seconds", "audio_mime_type", "stt_engine", "stt_model",
        "bank_item_id", "bank_item_subskill",
    }
    assert turn_result["pronunciation_status"] == "unassessed"
    assert turn_result["transcription"]
    # None of the new live-transcription concepts leak anywhere into the persisted, graded turn.
    serialized = str(turn_result).lower()
    for forbidden in ("client_secret", "live_transcription", "realtime", "ephemeral"):
        assert forbidden not in serialized
