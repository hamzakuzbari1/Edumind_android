"""5-section AI placement exam — a section-based, partly audio-native state machine.

Sections run in order: SPEAKING (audio-native via google-genai) -> LISTENING (adaptive audio MCQ)
-> READING (adaptive passage MCQ) -> WRITING (free text, AI-graded) -> INTERVIEW (Phase-2 guided
spoken follow-up seeded by Phase-1 evidence). Reading/listening/writing content is generated fresh
per attempt in a background task while the student does speaking. When the last section finishes, a
background task fuses everything into a per-skill CEFR report and unlocks the module.

The whole flow is driven by one ``exam_state`` JSON blob on the session row, and the frontend is
told exactly what to render next via the unified ``ExamStateOut`` contract:

  POST /initiate              -> resume an open exam, or build a fresh one (returns first state)
  GET  /{id}/state           -> current state (resume/polling; self-heals stalled content prep)
  POST /{id}/speaking/turn   -> (multipart audio) assess one spoken answer; speaking OR interview
  POST /{id}/answer          -> (MCQ) record a listening/reading answer; adaptive next/advance
  POST /{id}/writing         -> (text) record the writing answer; flow into the interview
  POST /{id}/abandon         -> drop an unfinished attempt so a fresh one can start
  GET  /{id}/report          -> poll for the final per-skill report
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import logging
import math
import re
import secrets
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal, get_db
from app.models.language.analytics import LanguageAnalytics
from app.models.language.content import LanguageContentItem
from app.models.language.enums import LanguageLevel, LanguageOnboardingStep, LanguageSkill
from app.models.language.exam import LanguageExamSession
from app.models.language.placement import LanguagePlacementQuestion, LanguagePlacementSection
from app.models.language.profile import LanguageStudentProfile
from app.models.profile import StudentProfile
from app.models.user import User
from app.schemas.language_exam import (
    CEFRLevel,
    ExamProcessingOut,
    ExamReportOut,
    ExamStateOut,
    LiveTranscriptionSessionOut,
    ListeningSubquestionOut,
    McqAnswerIn,
    McqPromptOut,
    MultiSkillReportSchema,
    SpeakingGradeSchema,
    SpeakingPromptOut,
    SpeakingTurnFeedbackOut,
    WritingAnswerIn,
    WritingGradeSchema,
    WritingPromptOut,
)
from app.services.language_access_service import require_active_language_subscription
from app.services.language_audio_security_service import ValidatedAudio, validate_placement_audio
from app.services.language_exam_service import (
    ALL_CEFR_LEVELS,
    adaptive_next_level,
    adaptive_result,
    ai_engine,
    build_verified_speaking_evidence,
    cefr_from_rank,
    cefr_rank,
    level_from_score10,
    overall_level,
)
from app.services.language_gap_fill_service import gap_fill_content_error, normalize_gap_fill_text
from app.services.language_level_utils import primary_focus_and_strength
from app.services.language_live_transcription_service import create_live_transcription_session
from app.services.language_placement_policy_service import (
    ensure_placement_retake_allowed,
    next_allowed_retake_at,
)
from app.services.language_placement_question_bank_service import (
    BoundaryTarget,
    bank_item_to_exam_item,
    fetch_bank_item_metadata,
    record_bank_item_answer,
    select_placement_bank_items,
)
from app.services.language_rate_limit_service import check, check_or_raise
from app.services.language_speaking_assessment_core_service import build_speaking_assessment_core
from app.services.language_subscription_service import ensure_language_profile, get_default_language
from app.services.language_transcription_service import transcribe_english_audio
from app.services.language_listening_tts import build_synthesis_segments
from app.services.language_tts_service import synthesize_exam_audio, synthesize_exam_audio_segments

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/student/languages/exam", tags=["Language Exam"])

SECTIONS = ["speaking", "listening", "reading", "writing"]
# Sections that work like the audio speaking flow (record -> assess -> next question).
# "interview" stays in this set (not in SECTIONS) so any already-persisted session that still
# has "interview" in its own exam_state["sections"] continues to route those turns correctly.
SPEAKING_LIKE = {"speaking", "interview"}
# "grammar_vocab" stays in MCQ_SECTIONS/PREPARED_SECTIONS (not SECTIONS) so any already-persisted
# session that still has "grammar_vocab" in its own exam_state["sections"] continues to route,
# render, and self-heal content for it correctly. New sessions never gain a "grammar_vocab" key
# (see initiate_exam) and every PREPARED_SECTIONS loop below is filtered to the session's own
# "sections" list, so this no longer runs for new sessions.
MCQ_SECTIONS = {"listening", "reading", "grammar_vocab"}
PREPARED_SECTIONS = {"listening", "reading", "grammar_vocab", "writing"}
SPEAKING_TURNS = 3
INTERVIEW_TURNS = 2  # Phase 2 — guided follow-up seeded by Phase 1 evidence.
ADAPTIVE_MAX_STEPS = 5  # MCQ sections: max adaptive questions before settling on a level.
MIN_MCQ_EVIDENCE_ITEMS = 3  # MCQ sections: don't settle on a level from fewer answered items than this.
READING_ADAPTIVE_MAX_STEPS = 7
READING_MIN_EVIDENCE_ITEMS = 5
WRITING_MIN_WORDS = 40
WRITING_TASK_TOTAL = 2
WRITING_TASK1_PROMPT = (
    "Write an email to a friend about a recent problem you had and how you solved it. "
    "Write 50-80 words."
)
WRITING_TASK1_MIN_WORDS = 50
WRITING_TASK1_MAX_WORDS = 80
WRITING_TASK2_ROUTE_LEVELS = {
    "A1_A2": ("A2", "A1"),
    "B1_B2": ("B2", "B1"),
    "C1_C2": ("C1", "C2"),
}
PLACEMENT_EXAM_DURATION_SECONDS = 60 * 60
PLACEMENT_EXAM_TIME_EXPIRED_MESSAGE = (
    "The 60-minute placement exam time is up. Please start a fresh attempt."
)
EVALUATION_LEASE_SECONDS = 15 * 60


# ---------------------------------------------------------------------------------------
# level / content helpers
# ---------------------------------------------------------------------------------------

async def _effective_level(db: AsyncSession, *, student_id: int, language_id: int) -> str:
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
    if analytics and analytics.speaking_level:
        return analytics.speaking_level.value
    return "A2"


async def _student_grade(db: AsyncSession, *, student_id: int) -> int | None:
    return (
        await db.execute(select(StudentProfile.grade).where(StudentProfile.user_id == student_id).limit(1))
    ).scalar_one_or_none()


def _new_adaptive_section(
    pool: dict[str, dict],
    start_level: str,
    *,
    dual_slot: bool = False,
    max_steps: int = ADAPTIVE_MAX_STEPS,
) -> dict:
    """Build the adaptive section state. Starts at the nearest available level to the estimate.

    dual_slot: Listening-only. When True, each pool[level] is {"mcq": item_or_none,
    "gap_fill": item_or_none} instead of a single flat item -- each present variant gets its own
    independent question_token. Reading/grammar_vocab/legacy listening never set this."""
    if pool and start_level not in pool:
        # Snap to the closest available rung.
        start_level = min(pool.keys(), key=lambda lv: abs(cefr_rank(CEFRLevel(lv)) - cefr_rank(CEFRLevel(start_level))))
    if dual_slot:
        tokenized_pool = {
            level: {
                variant: (
                    {**item, "question_token": str(item.get("question_token") or _new_exam_token())}
                    if item else None
                )
                for variant, item in slots.items()
            }
            for level, slots in pool.items()
        }
    else:
        tokenized_pool = {
            level: {**item, "question_token": str(item.get("question_token") or _new_exam_token())}
            for level, item in pool.items()
        }
    return {
        "mode": "adaptive",
        "pool": tokenized_pool,
        "current_level": start_level if tokenized_pool else "",
        "start_level": start_level,
        "asked": [],
        "max_steps": max_steps,
        "ready": bool(tokenized_pool),
        "done": False,
        "evidence_status": "missing_student_response" if tokenized_pool else "content_unavailable",
    }


def _new_exam_token() -> str:
    """Return an opaque per-prompt token; it is never derived from a database identifier."""
    return secrets.token_urlsafe(24)


def _state_revision(state: dict) -> int:
    try:
        return max(1, int(state.get("state_revision") or 1))
    except (TypeError, ValueError):
        return 1


def _bump_state_revision(state: dict) -> int:
    revision = _state_revision(state) + 1
    state["state_revision"] = revision
    return revision


def _ensure_state_protocol(state: dict) -> bool:
    """Upgrade an existing JSON state in-place without changing historical answers."""
    changed = False
    if not isinstance(state.get("state_revision"), int) or int(state.get("state_revision") or 0) < 1:
        state["state_revision"] = 1
        changed = True
    for section in MCQ_SECTIONS:
        for slot in (state.get(section, {}).get("pool") or {}).values():
            # Listening-only dual-slot shape: {"mcq": item_or_none, "gap_fill": item_or_none}.
            # A legacy in-flight listening pool (predating this shape) is still a flat item, not
            # a dict of only "mcq"/"gap_fill" keys -- handled by the isinstance/key check below.
            if section == "listening" and isinstance(slot, dict) and set(slot.keys()) <= {"mcq", "gap_fill"}:
                for item in slot.values():
                    if item and not item.get("question_token"):
                        item["question_token"] = _new_exam_token()
                        changed = True
                continue
            if not slot.get("question_token"):
                slot["question_token"] = _new_exam_token()
                changed = True
    for section in SPEAKING_LIKE:
        spoken = state.get(section, {})
        if spoken.get("pending_question") and not spoken.get("turn_token"):
            spoken["turn_token"] = _new_exam_token()
            changed = True
    writing = state.get("writing", {})
    if writing.get("prompt") and not writing.get("prompt_token"):
        writing["prompt_token"] = _new_exam_token()
        changed = True
    return changed


def _is_usable_audio_url(url: str | None) -> bool:
    value = str(url or "").strip()
    if not value:
        return False
    if value.startswith("/uploads/"):
        return True
    if value.startswith("http://") or value.startswith("https://"):
        return True
    return value.startswith("/language-assets/en/placement/listening/")


def _listening_text_from_body(body: dict | None) -> str:
    text = (
        (body or {}).get("audio_transcript")
        or (body or {}).get("text")
        or (body or {}).get("passage")
        or ""
    )
    return str(text).strip()


_FEMALE_LISTENING_CUES_RE = re.compile(
    r"\b(mrs\.?|ms\.?|miss|layla|leila|laila|nadia|maria|anna|sara|sarah|fatima|"
    r"my husband)\b",
    flags=re.IGNORECASE,
)


def _listening_tts_voice_for_text(text: str | None) -> str:
    """Pick a single-speaker placement-listening voice that does not contradict obvious cues."""

    cleaned = str(text or "")
    if _FEMALE_LISTENING_CUES_RE.search(cleaned):
        return (get_settings().LANGUAGE_SUPERTONIC_VOICE_FEMALE or "F1").strip() or "F1"
    return (get_settings().LANGUAGE_SUPERTONIC_VOICE_MALE or "M1").strip() or "M1"


def _listening_tts_segments_for_item(item: dict, audio_text: str | None) -> list[tuple[str, str]]:
    """Return gender-aware synthesis segments when a listening item carries speaker turns."""

    body = item.get("body") if isinstance(item, dict) else None
    if not isinstance(body, dict):
        return []
    body_audio_text = _listening_text_from_body(body)
    if not body_audio_text or body_audio_text.strip() != str(audio_text or "").strip():
        return []
    segments = build_synthesis_segments(body)
    if len(segments) <= 1:
        return []
    return segments


def _first_question(body: dict | None) -> dict | None:
    for q in (body or {}).get("questions") or []:
        choices = q.get("choices")
        ci = q.get("correct_index")
        # The correct index must point at a real option, else the item is unanswerable and would
        # always grade wrong, dragging the adaptive staircase down.
        if isinstance(choices, list) and len(choices) >= 2 and isinstance(ci, int) and 0 <= ci < len(choices):
            return q
    return None


async def _seeded_pool(
    db: AsyncSession, *, language_id: int, skill: LanguageSkill, levels: list[str]
) -> dict[str, dict]:
    """Seeded-bank fallback: one comprehension item per CEFR level -> {level: item}."""
    pool: dict[str, dict] = {}
    for lvl in levels:
        q = (
            select(LanguageContentItem)
            .where(
                LanguageContentItem.language_id == language_id,
                LanguageContentItem.skill == skill,
                LanguageContentItem.content_type == "lesson",
                LanguageContentItem.level == LanguageLevel(lvl),
                LanguageContentItem.is_published.is_(True),
            )
            .order_by(func.random())
            .limit(8)
        )
        for row in (await db.execute(q)).scalars().all():
            question = _first_question(row.body_json)
            if not question:
                continue
            body = row.body_json or {}
            audio_url = body.get("audio_url") if _is_usable_audio_url(body.get("audio_url")) else None
            audio_text = _listening_text_from_body(body)
            if skill == LanguageSkill.listening and not audio_url and not audio_text:
                continue
            item = {
                "content_id": row.id,
                "level": lvl,
                "passage": (body.get("passage") or body.get("text") or ""),
                "situation": (body.get("situation") or ""),
                "question": question.get("stem", ""),
                "options": list(question.get("choices") or []),
                "correct_index": int(question.get("correct_index")),
            }
            if audio_url:
                item["audio_url"] = str(audio_url)
            if audio_text:
                item["audio_text"] = audio_text
            pool[lvl] = item
            break
    return pool


def _is_valid_mcq_item(item: dict) -> bool:
    options = item.get("options")
    ci = item.get("correct_index")
    return isinstance(options, list) and len(options) >= 2 and isinstance(ci, int) and 0 <= ci < len(options)


def _is_valid_gap_fill_item(item: dict) -> bool:
    return gap_fill_content_error(item) is None


_STATIC_PLACEMENT_LISTENING_FALLBACKS: tuple[dict, ...] = (
    {
        "level": "A1",
        "audio_url": "/language-assets/en/placement/listening/q1.mp3",
        "audio_text": "Open your books.",
        "question": "What should you do?",
        "options": ["Close your books", "Open your books", "Stand up", "Go home"],
        "correct_index": 1,
    },
    {
        "level": "A2",
        "audio_url": "/language-assets/en/placement/listening/q3.mp3",
        "audio_text": "Turn left at the corner.",
        "question": "What direction?",
        "options": ["Left", "Right", "Straight", "Back"],
        "correct_index": 0,
    },
    {
        "level": "B1",
        "audio_url": "/language-assets/en/placement/listening/q4.mp3",
        "audio_text": "She has been studying for two hours.",
        "question": "When did she start?",
        "options": ["Two hours ago", "In two hours", "Yesterday", "Next week"],
        "correct_index": 0,
    },
    {
        "level": "B2",
        "audio_url": "/language-assets/en/placement/listening/q6.mp3",
        "audio_text": "He apologized for the inconvenience.",
        "question": "Why?",
        "options": ["He is proud", "He is sorry", "He is bored", "He is hungry"],
        "correct_index": 1,
    },
    {
        "level": "C1",
        "audio_url": "/language-assets/en/placement/listening/q8.mp3",
        "audio_text": "Her argument was compelling.",
        "question": "How was it?",
        "options": ["Weak", "Convincing", "Funny", "Short"],
        "correct_index": 1,
    },
    {
        "level": "C2",
        "audio_url": "/language-assets/en/placement/listening/q10.mp3",
        "audio_text": "The outcome was unprecedented.",
        "question": "What does it mean?",
        "options": ["Never happened before", "Very common", "Very small", "Very fast"],
        "correct_index": 0,
    },
)


def _static_placement_listening_pool(levels: list[str]) -> dict[str, dict]:
    """Source-controlled placement-listening fallback for environments with an empty DB bank.

    These items mirror the legacy placement seed rows and their checked-in audio assets, so the
    browser still receives real audio without calling AI/TTS or exposing a transcript.
    """

    wanted = set(levels)
    pool: dict[str, dict] = {}
    for raw in _STATIC_PLACEMENT_LISTENING_FALLBACKS:
        level = str(raw.get("level") or "")
        if level not in wanted or not _is_valid_mcq_item(raw) or not _is_usable_audio_url(raw.get("audio_url")):
            continue
        item = dict(raw)
        item.update(
            {
                "skill": "listening",
                "question_type": "mcq",
                "source": "static_placement_listening_fallback",
                "situation": "",
                "passage": "",
                "bank_item_id": None,
                "audio_meta": {"public_url": item["audio_url"]},
                "body": {
                    "audio_transcript": item["audio_text"],
                    "audio_url": item["audio_url"],
                },
            }
        )
        pool[level] = item
    return pool


def _legacy_placement_question_to_exam_item(
    row: LanguagePlacementQuestion,
    section: LanguagePlacementSection,
) -> dict | None:
    if section.skill != LanguageSkill.listening:
        return None
    prompt = row.prompt_json or {}
    answer_key = row.answer_key_json or {}
    level = str(row.level_hint or "").strip().upper()
    question = str(prompt.get("stem") or prompt.get("question") or "").strip()
    options = list(prompt.get("choices") or prompt.get("options") or [])
    correct_index = answer_key.get("correct_index")
    if level not in ALL_CEFR_LEVELS or not question:
        return None
    if not isinstance(correct_index, int) or isinstance(correct_index, bool):
        return None
    item = {
        "level": level,
        "skill": section.skill.value,
        "question_type": "mcq",
        "source": "legacy_placement_questions_fallback",
        "passage": str(prompt.get("passage") or ""),
        "situation": "",
        "question": question,
        "options": options,
        "correct_index": correct_index,
        "bank_item_id": None,
        "body": dict(prompt),
    }
    if not _is_valid_mcq_item(item):
        return None
    if section.skill == LanguageSkill.listening:
        audio_url = str(row.media_url or prompt.get("audio_url") or "").strip()
        audio_text = str(prompt.get("audio_transcript") or "").strip()
        if not _is_usable_audio_url(audio_url) or not audio_text:
            return None
        item.update(
            {
                "audio_url": audio_url,
                "audio_text": audio_text,
                "audio_meta": {"public_url": audio_url},
                "body": {**item["body"], "audio_url": audio_url},
            }
        )
    return item


async def _legacy_placement_mcq_pool(
    db: AsyncSession,
    *,
    language_id: int,
    skill: LanguageSkill,
    levels: list[str],
) -> dict[str, dict]:
    """Compatibility fallback for databases that still have legacy placement rows only."""

    wanted = set(levels)
    if not wanted:
        return {}
    rows = (
        await db.execute(
            select(LanguagePlacementQuestion, LanguagePlacementSection)
            .join(LanguagePlacementSection, LanguagePlacementSection.id == LanguagePlacementQuestion.section_id)
            .where(
                LanguagePlacementSection.language_id == language_id,
                LanguagePlacementSection.skill == skill,
            )
            .order_by(LanguagePlacementQuestion.sort_order.asc(), LanguagePlacementQuestion.id.asc())
        )
    ).all()
    pool: dict[str, dict] = {}
    for row, section in rows:
        item = _legacy_placement_question_to_exam_item(row, section)
        if not item:
            continue
        level = str(item.get("level") or "")
        if level in wanted and level not in pool:
            pool[level] = item
    return pool


# Phase 6: task bundles. A bundle is still one adaptive-pool item/passage (the
# staircase moves one CEFR level per passage exactly as before) -- only the *scoring* of that one
# passage now rolls up from several sub-answers. Strict majority: a 1-1 tie (2 blanks/subquestions)
# does NOT count as correct, only counts >half.
_BUNDLE_SUBQUESTION_COUNT = 3
_READING_BUNDLE_SUBQUESTION_COUNT = 4
_READING_MVP_SOURCE = "reading_mvp_v1_draft"
_BUNDLE_BLANK_COUNT = 3
_NOTE_TEMPLATE_TOKENS = ("{{1}}", "{{2}}", "{{3}}")
_READING_TEXT_RESPONSE_TYPES = {"short_answer", "constructed_response", "gap_fill"}
_READING_MATCHING_RESPONSE_TYPES = {"matching"}


def _majority_correct(flags: list[bool]) -> bool:
    return sum(flags) * 2 > len(flags)


def _is_valid_mcq_bundle_item(item: dict, *, expected_count: int = _BUNDLE_SUBQUESTION_COUNT) -> bool:
    subquestions = item.get("subquestions")
    if not isinstance(subquestions, list) or len(subquestions) != expected_count:
        return False
    for sq in subquestions:
        if not isinstance(sq, dict) or not str(sq.get("question") or "").strip():
            return False
        options = sq.get("options")
        ci = sq.get("correct_index")
        if not isinstance(options, list) or len(options) != 4:
            return False
        if not isinstance(ci, int) or isinstance(ci, bool) or not (0 <= ci < len(options)):
            return False
    return True


def _reading_subquestion_response_type(sq: dict) -> str:
    return str(sq.get("response_type") or "mcq").strip() or "mcq"


def _is_valid_reading_bundle_item(item: dict) -> bool:
    subquestions = item.get("subquestions")
    if not isinstance(subquestions, list) or len(subquestions) != _READING_BUNDLE_SUBQUESTION_COUNT:
        return False
    for sq in subquestions:
        if not isinstance(sq, dict) or not str(sq.get("question") or "").strip():
            return False
        response_type = _reading_subquestion_response_type(sq)
        if response_type == "mcq":
            options = sq.get("options")
            ci = sq.get("correct_index")
            if not isinstance(options, list) or len(options) != 4:
                return False
            if not isinstance(ci, int) or isinstance(ci, bool) or not (0 <= ci < len(options)):
                return False
        elif response_type in _READING_TEXT_RESPONSE_TYPES:
            accepted = sq.get("accepted_answers")
            max_words = sq.get("max_words", 12)
            if not isinstance(accepted, list) or not any(str(a or "").strip() for a in accepted):
                return False
            if not isinstance(max_words, int) or isinstance(max_words, bool) or not (1 <= max_words <= 30):
                return False
        elif response_type in _READING_MATCHING_RESPONSE_TYPES:
            matching_items = sq.get("matching_items")
            match_options = sq.get("match_options")
            correct_indices = sq.get("correct_indices")
            if not isinstance(matching_items, list) or not (2 <= len(matching_items) <= 5):
                return False
            if not all(isinstance(i, str) and i.strip() for i in matching_items):
                return False
            if not isinstance(match_options, list) or len(match_options) < len(matching_items):
                return False
            if not all(isinstance(o, str) and o.strip() for o in match_options):
                return False
            if not isinstance(correct_indices, list) or len(correct_indices) != len(matching_items):
                return False
            if any(not isinstance(i, int) or isinstance(i, bool) or not (0 <= i < len(match_options)) for i in correct_indices):
                return False
        else:
            return False
    return True


def _is_valid_gap_fill_bundle_item(item: dict) -> bool:
    blanks = item.get("blanks")
    note_template = item.get("note_template")
    if not isinstance(blanks, list) or len(blanks) != _BUNDLE_BLANK_COUNT:
        return False
    if not isinstance(note_template, str) or not note_template.strip():
        return False
    for token in _NOTE_TEMPLATE_TOKENS:
        if note_template.count(token) != 1:
            return False
    for blank in blanks:
        if not isinstance(blank, dict) or gap_fill_content_error(blank) is not None:
            return False
    return True


def _is_valid_mcq_pool_item(item: dict, *, skill: str) -> bool:
    """Validate pool items by skill.

    Reading placement now uses only curated passage bundles: one passage with exactly four
    subquestions. Legacy single-question Reading rows are intentionally rejected so they cannot
    leak back through old bank rows, boundary rows, or fallback content.
    """
    if skill == "reading":
        return _is_valid_reading_bundle_item(item)
    if skill == "listening":
        return _is_valid_mcq_item(item) or _is_valid_mcq_bundle_item(item, expected_count=_BUNDLE_SUBQUESTION_COUNT)
    return _is_valid_mcq_item(item)


def _is_valid_gap_fill_pool_item(item: dict) -> bool:
    """Listening only. Accepts either the legacy single-blank shape or the Phase 6 bundle shape."""
    return _is_valid_gap_fill_item(item) or _is_valid_gap_fill_bundle_item(item)


# Every 3rd Listening item (0-indexed position 2, 5, 8, ...) prefers Gap Fill; all other
# positions prefer MCQ. Position-based, not count-based, because the adaptive staircase can end
# at any point -- this keeps MCQ the majority for any attempt length without needing a fixed
# batch ratio.
_GAP_FILL_POSITION_MODULUS = 3
_GAP_FILL_POSITION_REMAINDER = 2


def _resolve_current_exam_item(sec: dict, current_level: str, *, dual_slot: bool = False) -> dict | None:
    """Resolve the single exam item to serve/score for this section at its current level.

    dual_slot=True (Listening only): sec["pool"][current_level] is
    {"mcq": item_or_none, "gap_fill": item_or_none}. Chooses a variant by position
    (len(sec["asked"]) % 3 == 2 prefers gap_fill, else mcq) and falls back to whichever variant
    is actually present if the preferred one is missing -- never blocks the exam over an absent
    Gap Fill candidate (e.g. while real Gap Fill rows remain inactive).

    dual_slot=False: unchanged flat-pool lookup (reading/grammar_vocab/legacy listening state).

    _build_state_out and answer_mcq must both call this the same way for the same section/level
    so the item shown to the student is always the item scored.
    """
    slot = (sec.get("pool") or {}).get(current_level)
    if not dual_slot:
        return slot
    if not isinstance(slot, dict):
        return None
    if "mcq" not in slot and "gap_fill" not in slot:
        # Not actually dual-slot shaped (e.g. a legacy in-flight session's flat listening item) --
        # use it as-is rather than misreading it as an empty dual-slot container.
        return slot
    asked_count = len(sec.get("asked") or [])
    prefer_gap_fill = asked_count % _GAP_FILL_POSITION_MODULUS == _GAP_FILL_POSITION_REMAINDER
    preferred, other = ("gap_fill", "mcq") if prefer_gap_fill else ("mcq", "gap_fill")
    return slot.get(preferred) or slot.get(other)


def _already_used_bank_item_ids(state: dict, skill: str) -> set[int]:
    """Bank item ids already asked for this skill in this exam session (session-scoped, P1.1).

    Reads state[skill]["asked"] only — sections with no "asked" list (e.g. "writing") naturally
    yield an empty set. Does not touch usage_count/correct_count or any lifetime/cross-session
    history."""
    asked = state.get(skill, {}).get("asked", []) or []
    return {int(a["bank_item_id"]) for a in asked if a.get("bank_item_id")}


def _mcq_continuation_level(
    *,
    pool_levels: set[str],
    asked_levels: set[str],
    asked_count: int,
    current: str,
    min_evidence_items: int = MIN_MCQ_EVIDENCE_ITEMS,
) -> str | None:
    """When the adaptive staircase converges/plateaus, decide whether to keep probing instead of
    settling on a level (P1.2 minimum evidence floor).

    Returns the next unasked pool level to ask (nearest to `current` by CEFR rank distance, same
    selection style as _new_adaptive_section's initial-level snap), or None if evidence is already
    sufficient (asked_count >= min_evidence_items) or the pool has no unasked levels left — in
    which case the caller should fall through to its existing completion path."""
    if asked_count >= min_evidence_items:
        return None
    remaining = [lv for lv in pool_levels if lv not in asked_levels]
    if not remaining:
        return None
    return min(remaining, key=lambda lv: abs(cefr_rank(CEFRLevel(lv)) - cefr_rank(CEFRLevel(current))))


def _min_evidence_for_section(section: str) -> int:
    return READING_MIN_EVIDENCE_ITEMS if section == "reading" else MIN_MCQ_EVIDENCE_ITEMS


def _reading_weighted_result(asked: list[dict]) -> tuple[CEFRLevel, float]:
    """Reading-specific placement score from all evidence, not just the highest correct rung.

    Correct answers contribute one band above the item as evidence that the learner can handle
    that difficulty; wrong answers contribute one band below it. The final estimate is the
    weighted floor of those signals with a small consistency boost for strong accuracy, capped by
    the highest level actually answered correctly so one low-level streak cannot over-place.
    """
    total = len(asked or [])
    if not total:
        return CEFRLevel.A2, 0.0

    correct_ranks: list[int] = []
    weighted_sum = 0.0
    weight_total = 0.0
    for answer in asked:
        try:
            rank = cefr_rank(CEFRLevel(answer["level"]))
        except (KeyError, TypeError, ValueError):
            continue
        weight = 1.0 + (rank * 0.08)
        if answer.get("correct"):
            correct_ranks.append(rank)
            signal = min(len(ALL_CEFR_LEVELS) - 1, rank + 1)
        else:
            signal = max(0, rank - 1)
        weighted_sum += signal * weight
        weight_total += weight

    correct_count = len(correct_ranks)
    pct = round(correct_count / total * 100, 1) if total else 0.0
    if not correct_ranks:
        valid_levels = []
        for answer in asked:
            try:
                valid_levels.append(CEFRLevel(answer["level"]))
            except (KeyError, TypeError, ValueError):
                pass
        lowest = min(valid_levels, key=cefr_rank) if valid_levels else CEFRLevel.A1
        return cefr_from_rank(cefr_rank(lowest) - 1), pct

    average_signal = weighted_sum / weight_total if weight_total else float(max(correct_ranks))
    boost = 0.5 if pct >= 75 else 0.25 if pct >= 60 else 0.0
    estimated_rank = math.floor(average_signal + boost)
    estimated_rank = min(estimated_rank, max(correct_ranks))
    return cefr_from_rank(estimated_rank), pct


def _boundary_situation(asked: list[dict]) -> tuple[str, str] | None:
    """Detect uncertainty between two adjacent CEFR levels from the two most-recently-answered
    items: one correct and the other, at the adjacent level, incorrect (P1.3).

    Returns the (low, high) level strings to confirm, or None if the last two answers don't
    straddle a single-band boundary (fewer than 2 answered, non-adjacent levels, or matching
    correctness — agreement isn't uncertainty)."""
    if len(asked) < 2:
        return None
    a, b = asked[-2], asked[-1]
    if bool(a.get("correct")) == bool(b.get("correct")):
        return None
    try:
        rank_a = cefr_rank(CEFRLevel(a["level"]))
        rank_b = cefr_rank(CEFRLevel(b["level"]))
    except ValueError:
        return None
    if abs(rank_a - rank_b) != 1:
        return None
    return (a["level"], b["level"]) if rank_a < rank_b else (b["level"], a["level"])


async def _boundary_confirmation_item(
    db: AsyncSession, *, language_id: int, skill: str, low: str, high: str, used_item_ids: set[int]
) -> dict | None:
    """Fetch one genuine boundary-tagged bank item for the (low, high) CEFR pair (P1.3), or None
    if the bank has no such item.

    select_placement_bank_items() falls back to a plain level-matched item when no boundary item
    exists, so the returned row's own boundary_low_level/boundary_high_level are checked here to
    confirm it's a real boundary hit and not that fallback in disguise."""
    boundary = BoundaryTarget(low=LanguageLevel(low), high=LanguageLevel(high))
    rows = await select_placement_bank_items(
        db,
        language_id=language_id,
        skill=skill,
        level=high,
        count=1,
        used_item_ids=used_item_ids,
        boundary=boundary,
    )
    if not rows:
        return None
    row = rows[0]
    if row.boundary_low_level != boundary.low or row.boundary_high_level != boundary.high:
        return None

    item = bank_item_to_exam_item(row)
    if not _is_valid_mcq_pool_item(item, skill=skill):
        return None
    if skill == "listening":
        if not _is_usable_audio_url(item.get("audio_url")):
            item["audio_url"] = None
        body = item.get("body") or {}
        audio_text = _listening_text_from_body(body)
        if item.get("content_id"):
            content = await db.get(LanguageContentItem, item["content_id"])
            body = content.body_json if content else body
            if not audio_text:
                audio_text = _listening_text_from_body(body)
        audio_url = (body or {}).get("audio_url")
        if not item.get("audio_url") and audio_text and _is_usable_audio_url(audio_url):
            item["audio_url"] = str(audio_url)
        if audio_text:
            item["audio_text"] = audio_text
        if not item.get("audio_url") and not item.get("audio_text"):
            return None
    item["source"] = "placement_qbank"
    return item


async def _question_bank_pool(
    db: AsyncSession,
    *,
    language_id: int,
    skill: str,
    levels: list[str],
    used_item_ids: set[int] | None = None,
) -> dict[str, dict]:
    """Reviewed question-bank items: one internal MCQ item per requested CEFR level."""
    pool: dict[str, dict] = {}
    for lvl in levels:
        for row in await select_placement_bank_items(
            db,
            language_id=language_id,
            skill=skill,
            level=lvl,
            count=12 if skill == "reading" else 4 if skill == "listening" else 1,
            used_item_ids=used_item_ids,
        ):
            if skill == "reading" and row.source != _READING_MVP_SOURCE:
                continue
            item = bank_item_to_exam_item(row)
            if not _is_valid_mcq_pool_item(item, skill=skill):
                continue
            if skill == "listening":
                if not _is_usable_audio_url(item.get("audio_url")):
                    item["audio_url"] = None
                body = item.get("body") or {}
                audio_text = _listening_text_from_body(body)
                if item.get("content_id"):
                    content = await db.get(LanguageContentItem, item["content_id"])
                    body = content.body_json if content else body
                    if not audio_text:
                        audio_text = _listening_text_from_body(body)
                audio_url = (body or {}).get("audio_url")
                if not item.get("audio_url") and audio_text and _is_usable_audio_url(audio_url):
                    item["audio_url"] = str(audio_url)
                if audio_text:
                    item["audio_text"] = audio_text
                if not item.get("audio_url") and not item.get("audio_text"):
                    continue
            item["source"] = "placement_qbank"
            pool[lvl] = item
            break
    return pool


async def _gap_fill_listening_pool(
    db: AsyncSession,
    *,
    language_id: int,
    levels: list[str],
    used_item_ids: set[int] | None = None,
) -> dict[str, dict]:
    """Listening-only: one internal Gap Fill candidate per requested CEFR level, when available.

    This is the only call site anywhere in the codebase permitted to pass allow_gap_fill=True.
    Still fully gated by is_active/is_verified like every other bank query -- while the real Gap
    Fill rows remain is_active=false (pending a separate, later activation phase), this returns
    nothing for every level and the Listening dual-slot pool degrades to MCQ-only, exactly as
    Listening behaves today.
    """
    pool: dict[str, dict] = {}
    for lvl in levels:
        for row in await select_placement_bank_items(
            db,
            language_id=language_id,
            skill="listening",
            level=lvl,
            count=4,
            used_item_ids=used_item_ids,
            allow_gap_fill=True,
        ):
            if row.question_type != "gap_fill":
                # allow_gap_fill=True also returns mcq rows -- the mcq variant is fetched
                # separately by _question_bank_pool; this loop only ever keeps gap_fill.
                continue
            item = bank_item_to_exam_item(row)
            if not _is_valid_gap_fill_pool_item(item):
                continue
            if not _is_usable_audio_url(item.get("audio_url")):
                item["audio_url"] = None
            body = item.get("body") or {}
            audio_text = _listening_text_from_body(body)
            if item.get("content_id"):
                content = await db.get(LanguageContentItem, item["content_id"])
                body = content.body_json if content else body
                if not audio_text:
                    audio_text = _listening_text_from_body(body)
            audio_url = (body or {}).get("audio_url")
            if not item.get("audio_url") and audio_text and _is_usable_audio_url(audio_url):
                item["audio_url"] = str(audio_url)
            if audio_text:
                item["audio_text"] = audio_text
            if not item.get("audio_url") and not item.get("audio_text"):
                continue
            item["source"] = "placement_qbank"
            pool[lvl] = item
            break
    return pool


async def _generated_pool(
    db: AsyncSession, *, language_id: int, levels: list[str]
) -> dict[str, dict]:
    """Last-resort fallback: verified AI-generated questions (no passage) -> {level: item}.

    Consumes the offline-built, second-LLM-verified `LanguageGeneratedQuestion` bank so a level is
    never left without a question when neither AI generation nor the passage-based lesson bank could
    supply one. Standalone (passage-less) use-of-English items, so reading-only.
    """
    from app.models.language.learner_model import LanguageGeneratedQuestion

    pool: dict[str, dict] = {}
    for lvl in levels:
        row = (
            await db.execute(
                select(LanguageGeneratedQuestion)
                .where(
                    LanguageGeneratedQuestion.language_id == language_id,
                    LanguageGeneratedQuestion.cefr_level == LanguageLevel(lvl),
                    LanguageGeneratedQuestion.verified.is_(True),
                )
                .order_by(func.random())
                .limit(1)
            )
        ).scalar_one_or_none()
        if not row:
            continue
        prompt = row.prompt_json or {}
        choices = prompt.get("choices") or []
        ci = prompt.get("correct_index")
        if len(choices) < 2 or not isinstance(ci, int) or not (0 <= ci < len(choices)):
            continue
        pool[lvl] = {
            "level": lvl,
            "passage": "",
            "situation": "",
            "question": prompt.get("stem", ""),
            "options": list(choices),
            "correct_index": int(prompt.get("correct_index")),
        }
    return pool


async def _mark_content_prep_unavailable(
    *, session_id: str, prep_token: str, error_code: str
) -> None:
    async with AsyncSessionLocal() as mark_db:
        sess = (
            await mark_db.execute(
                select(LanguageExamSession)
                .where(LanguageExamSession.id == session_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if not sess or sess.status != "in_progress":
            return
        state = copy.deepcopy(sess.exam_state or {})
        if str(state.get("content_prep_token") or "") != prep_token:
            return
        state["content_prep_status"] = "content_unavailable"
        state["content_prep_error_code"] = error_code
        session_sections = state.get("sections") or SECTIONS
        for section in PREPARED_SECTIONS:
            if section not in session_sections:
                continue
            if not state.get(section, {}).get("ready"):
                state.setdefault(section, {})["evidence_status"] = "content_unavailable"
        _bump_state_revision(state)
        sess.exam_state = state
        flag_modified(sess, "exam_state")
        await mark_db.commit()


async def _prepare_content(session_id: str, language_id: int, level: str) -> None:
    """Prepare placement content in two phases without a DB transaction during AI/TTS.

    Phase one snapshots all database-backed candidates and closes its transaction.  Phase two runs
    external generation and TTS using only detached dictionaries, then merges only the prepared
    sections into the latest JSON state under a short row lock.
    """
    prep_token = ""
    source_revision = 1
    l_pool: dict[str, dict] = {}
    l_gap_fill_pool: dict[str, dict] = {}
    try:
        # Database-only preparation.  Do not add AI/TTS calls inside this context.
        async with AsyncSessionLocal() as db:
            sess = await db.get(LanguageExamSession, session_id)
            if not sess or not sess.exam_state or sess.status != "in_progress":
                return
            source_state = copy.deepcopy(sess.exam_state or {})
            source_revision = _state_revision(source_state)
            prep_token = str(source_state.get("content_prep_token") or "")
            # New sessions no longer carry "grammar_vocab" in their own "sections" list (see
            # initiate_exam); only an already-persisted session that still lists it needs its
            # content (re)prepared here.
            needs_grammar_vocab = "grammar_vocab" in (source_state.get("sections") or SECTIONS)
            student_id = int(sess.student_id)
            analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
            reading_start_level = (
                analytics.reading_level.value
                if analytics and analytics.reading_level
                else level
            )
            listening_start_level = (
                analytics.listening_level.value
                if analytics and analytics.listening_level
                else level
            )
            if not check("placement_generation", f"{student_id}:{session_id}"):
                logger.warning(
                    "Placement content generation rate-limited session_id=%s user_id=%s",
                    session_id,
                    student_id,
                )
                await db.rollback()
                await _mark_content_prep_unavailable(
                    session_id=session_id,
                    prep_token=prep_token,
                    error_code="content_generation_rate_limited",
                )
                return

            r_pool = await _question_bank_pool(
                db, language_id=language_id, skill="reading", levels=ALL_CEFR_LEVELS,
                used_item_ids=_already_used_bank_item_ids(source_state, "reading"),
            )
            r_missing = [lv for lv in ALL_CEFR_LEVELS if lv not in r_pool]
            if r_missing:
                logger.warning(
                    "Reading placement bundle bank missing levels session_id=%s levels=%s",
                    session_id,
                    ",".join(r_missing),
                )
            g_pool = (
                await _question_bank_pool(
                    db,
                    language_id=language_id,
                    skill="grammar_vocab",
                    levels=ALL_CEFR_LEVELS,
                    used_item_ids=_already_used_bank_item_ids(source_state, "grammar_vocab"),
                )
                if needs_grammar_vocab
                else {}
            )
            l_used_item_ids = _already_used_bank_item_ids(source_state, "listening")
            l_pool = await _question_bank_pool(
                db, language_id=language_id, skill="listening", levels=ALL_CEFR_LEVELS,
                used_item_ids=l_used_item_ids,
            )
            l_gap_fill_pool = await _gap_fill_listening_pool(
                db, language_id=language_id, levels=ALL_CEFR_LEVELS,
                used_item_ids=l_used_item_ids,
            )
            l_missing = [lv for lv in ALL_CEFR_LEVELS if lv not in l_pool]
            l_seeded = await _seeded_pool(
                db,
                language_id=language_id,
                skill=LanguageSkill.listening,
                levels=l_missing,
            )
            for fallback_level, item in (
                await _legacy_placement_mcq_pool(
                    db,
                    language_id=language_id,
                    skill=LanguageSkill.listening,
                    levels=[lv for lv in ALL_CEFR_LEVELS if lv not in l_pool],
                )
            ).items():
                l_pool.setdefault(fallback_level, item)
            await db.rollback()

        # External-only preparation.  The database session above is closed before reaching here.
        start_level = level if level in ALL_CEFR_LEVELS else "B1"
        # Reading must stay on the curated MVP bundle bank: one passage with four subquestions.
        # Do not backfill missing levels with generated/seeded single-question items.
        reading_section = _new_adaptive_section(
            r_pool,
            reading_start_level if reading_start_level in ALL_CEFR_LEVELS else start_level,
            max_steps=READING_ADAPTIVE_MAX_STEPS,
        )
        grammar_vocab_section = _new_adaptive_section(g_pool, start_level) if needs_grammar_vocab else None

        for fallback_level, item in _static_placement_listening_pool(
            [lv for lv in ALL_CEFR_LEVELS if lv not in l_pool]
        ).items():
            l_pool.setdefault(fallback_level, item)

        missing = [lv for lv in ALL_CEFR_LEVELS if lv not in l_pool]
        try:
            generated_listening = (
                await ai_engine.generate_comprehension_set(skill="listening", levels=missing)
                if missing
                else None
            )
        except Exception:
            generated_listening = None
        for item in (generated_listening or {}).get("items", []):
            l_pool[item["level"]] = {
                "audio_text": item["text"],
                "situation": item["situation"],
                "question": item["question"],
                "options": item["options"],
                "correct_index": item["correct_index"],
                "level": item["level"],
            }
        for fallback_level, item in l_seeded.items():
            l_pool.setdefault(fallback_level, item)
        # Every TTS call runs after the DB context closed.  Missing audio removes that rung instead
        # of exposing its transcript or fabricating listening evidence.
        for listening_level, item in list(l_pool.items()):
            audio_url, _audio_text, _created = await _materialize_listening_audio(None, item)
            if not audio_url:
                l_pool.pop(listening_level, None)
        for gap_fill_level, item in list(l_gap_fill_pool.items()):
            audio_url, _audio_text, _created = await _materialize_listening_audio(None, item)
            if not audio_url:
                l_gap_fill_pool.pop(gap_fill_level, None)
        # Listening-only dual-slot pool: each level may hold an MCQ candidate, a Gap Fill
        # candidate, or both. Gap Fill only ever comes from reviewed bank rows (never the
        # seeded/AI-generated fallback paths, which are MCQ-only) and only appears once
        # allow_gap_fill=True finds an active+verified row for that level -- inert today since the
        # real Gap Fill rows are still is_active=false.
        l_dual_pool = {
            lvl: {"mcq": l_pool.get(lvl), "gap_fill": l_gap_fill_pool.get(lvl)}
            for lvl in set(l_pool) | set(l_gap_fill_pool)
        }
        listening_section = _new_adaptive_section(
            l_dual_pool,
            listening_start_level if listening_start_level in ALL_CEFR_LEVELS else start_level,
            dual_slot=True,
        )

        writing_prompt_payload = _writing_task1_payload()
        writing_prompt = str((writing_prompt_payload or {}).get("prompt") or "")
        writing_section = {
            "mode": "adaptive_two_task",
            "task_index": 1,
            "task_total": WRITING_TASK_TOTAL,
            "tasks": [dict(writing_prompt_payload)],
            "prompt": writing_prompt,
            "prompt_token": _new_exam_token() if writing_prompt else "",
            "min_words": int((writing_prompt_payload or {}).get("min_words") or WRITING_MIN_WORDS),
            "max_words": (writing_prompt_payload or {}).get("max_words"),
            "task_type": str((writing_prompt_payload or {}).get("task_type") or ""),
            "student_instructions": str((writing_prompt_payload or {}).get("student_instructions") or ""),
            "rubric_focus": list((writing_prompt_payload or {}).get("rubric_focus") or []),
            "expected_language_features": list((writing_prompt_payload or {}).get("expected_language_features") or []),
            "bank_item_id": (writing_prompt_payload or {}).get("bank_item_id"),
            "source": str((writing_prompt_payload or {}).get("source") or ""),
            "response": None,
            "ready": bool(writing_prompt),
            "done": False,
            "evidence_status": (
                "missing_student_response" if writing_prompt else "content_unavailable"
            ),
        }
        prepared = {
            "reading": reading_section,
            "listening": listening_section,
            "writing": writing_section,
        }
        if needs_grammar_vocab:
            prepared["grammar_vocab"] = grammar_vocab_section
        await _merge_prepared_content(
            session_id=session_id,
            prep_token=prep_token,
            source_revision=source_revision,
            prepared=prepared,
        )
    except Exception as exc:
        _cleanup_exam_audio(
            {"listening": {"pool": {**l_pool, **{f"gf_{lvl}": item for lvl, item in l_gap_fill_pool.items()}}}}
        )
        logger.warning(
            "Placement content preparation failed session_id=%s error_type=%s",
            session_id,
            type(exc).__name__,
        )
        if prep_token:
            await _mark_content_prep_unavailable(
                session_id=session_id,
                prep_token=prep_token,
                error_code="content_preparation_failed",
            )


async def _merge_prepared_content(
    *,
    session_id: str,
    prep_token: str,
    source_revision: int,
    prepared: dict[str, dict],
) -> bool:
    """Merge only prepared sections into the latest row under a short PostgreSQL lock."""
    async with AsyncSessionLocal() as merge_db:
        sess = (
            await merge_db.execute(
                select(LanguageExamSession)
                .where(LanguageExamSession.id == session_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if not sess or sess.status in {"abandoned", "completed", "failed", "evaluating"}:
            _cleanup_exam_audio(prepared)
            return False

        latest = copy.deepcopy(sess.exam_state or {})
        if str(latest.get("content_prep_token") or "") != prep_token:
            _cleanup_exam_audio(prepared)
            return False

        merged_any = False
        for section, value in prepared.items():
            current = latest.get(section, {})
            already_answered = bool(current.get("asked")) or bool(current.get("response")) or bool(current.get("done"))
            if already_answered or current.get("ready") is True:
                if section == "listening":
                    _cleanup_exam_audio({"listening": value})
                continue
            latest[section] = value
            merged_any = True

        if not merged_any:
            _cleanup_exam_audio(prepared)
            return False

        latest_sections = latest.get("sections") or SECTIONS
        latest["content_prep_status"] = (
            "completed"
            if all(
                latest.get(section, {}).get("ready")
                for section in PREPARED_SECTIONS
                if section in latest_sections
            )
            else "content_unavailable"
        )
        latest["content_prepared_from_revision"] = source_revision
        latest["content_prepared_at"] = datetime.now(timezone.utc).isoformat()
        _bump_state_revision(latest)
        sess.exam_state = latest
        flag_modified(sess, "exam_state")
        await merge_db.commit()
        return True


async def _writing_prompt(
    db: AsyncSession,
    *,
    language_id: int,
    level_str: str,
    include_generic: bool = True,
    used_item_ids: set[int] | None = None,
) -> dict | None:
    """Pull a reviewed/seeded writing prompt near the level; optionally fall back to generic."""
    try:
        lvl = LanguageLevel(level_str)
    except ValueError:
        lvl = LanguageLevel.A2
    for row in await select_placement_bank_items(
        db,
        language_id=language_id,
        skill="writing_prompt",
        level=lvl,
        count=1,
        used_item_ids=used_item_ids,
    ):
        item = bank_item_to_exam_item(row)
        prompt = str(item.get("question") or "").strip()
        if prompt:
            body = item.get("body") or {}
            return {
                "prompt": prompt,
                "min_words": _coerce_writing_word_limit(body.get("target_min_words") or body.get("min_words"), WRITING_MIN_WORDS),
                "max_words": _coerce_writing_word_limit(body.get("target_max_words"), None),
                "task_type": str(body.get("task_type") or item.get("subskill") or "").strip(),
                "student_instructions": str(body.get("student_instructions") or "").strip(),
                "rubric_focus": list(body.get("rubric_focus") or []),
                "expected_language_features": list(body.get("expected_language_features") or []),
                "bank_item_id": item.get("bank_item_id"),
                "source": str(row.source or ""),
            }
    if not include_generic:
        return None
    return (
        {
            "prompt": (
                "Write a short message (at least 40 words) describing a memorable day you had recently. "
                "Explain what happened, who you were with, and how you felt."
            ),
            "min_words": WRITING_MIN_WORDS,
            "max_words": None,
            "task_type": "fallback_short_message",
            "student_instructions": "Write in English. Stay on topic. Do not use bullet points.",
            "rubric_focus": [],
            "expected_language_features": [],
            "bank_item_id": None,
            "source": "generic_fallback",
        }
    )


def _coerce_writing_word_limit(value: object, default: int | None) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if parsed <= 0:
        return default
    return parsed


def _normalise_writing_prompt_payload(value: object) -> dict | None:
    if not value:
        return None
    if isinstance(value, dict):
        prompt = str(value.get("prompt") or "").strip()
        if not prompt:
            return None
        min_words = _coerce_writing_word_limit(value.get("min_words"), WRITING_MIN_WORDS)
        max_words = _coerce_writing_word_limit(value.get("max_words"), None)
        return {
            "prompt": prompt,
            "min_words": min_words,
            "max_words": max_words,
            "task_type": str(value.get("task_type") or "").strip(),
            "student_instructions": str(value.get("student_instructions") or "").strip(),
            "rubric_focus": list(value.get("rubric_focus") or []),
            "expected_language_features": list(value.get("expected_language_features") or []),
            "bank_item_id": value.get("bank_item_id"),
            "source": str(value.get("source") or "").strip(),
        }
    prompt = str(value).strip()
    if not prompt:
        return None
    return {
        "prompt": prompt,
        "min_words": WRITING_MIN_WORDS,
        "max_words": None,
        "task_type": "",
        "student_instructions": "",
        "rubric_focus": [],
        "expected_language_features": [],
        "bank_item_id": None,
        "source": "",
    }


def _writing_task1_payload() -> dict:
    return {
        "prompt": WRITING_TASK1_PROMPT,
        "min_words": WRITING_TASK1_MIN_WORDS,
        "max_words": WRITING_TASK1_MAX_WORDS,
        "task_type": "task1_anchor_email",
        "student_instructions": "Write in English. Stay on topic. Do not use bullet points.",
        "rubric_focus": [
            "task_fulfillment",
            "communicative_achievement",
            "organization",
            "grammar",
            "vocabulary",
        ],
        "expected_language_features": [
            "basic past tense",
            "clear sequencing",
            "everyday vocabulary",
            "email register",
        ],
        "bank_item_id": None,
        "source": "writing_task1_anchor",
        "route": "anchor",
    }


def _writing_task2_fallback_payload(route: str) -> dict:
    if route == "A1_A2":
        return {
            "prompt": (
                "Describe a memorable day in your life. Say where you were, who was with you, "
                "and what happened. Write 60-90 words."
            ),
            "min_words": 60,
            "max_words": 90,
            "task_type": "personal_narrative",
            "student_instructions": "Write in English. Stay on topic. Do not use bullet points.",
        }
    if route == "C1_C2":
        return {
            "prompt": (
                "Some people believe that final examinations should be replaced by continuous assessment. "
                "Write an essay discussing both approaches and give your own opinion. Write 200-250 words."
            ),
            "min_words": 200,
            "max_words": 250,
            "task_type": "discussion_essay",
            "student_instructions": "Write in English. Organize your ideas into clear paragraphs. Do not use bullet points.",
        }
    return {
        "prompt": (
            "If you could change one rule at your school, what would you change? Explain why and "
            "describe how this change would help students. Write 120-160 words."
        ),
        "min_words": 120,
        "max_words": 160,
        "task_type": "opinion_response",
        "student_instructions": "Write in English. Organize your ideas clearly. Do not use bullet points.",
    }


async def _writing_task2_prompt(
    db: AsyncSession,
    *,
    language_id: int,
    route: str,
    used_item_ids: set[int] | None = None,
) -> dict:
    levels = WRITING_TASK2_ROUTE_LEVELS.get(route) or WRITING_TASK2_ROUTE_LEVELS["B1_B2"]
    for level in levels:
        payload = await _writing_prompt(
            db,
            language_id=language_id,
            level_str=level,
            include_generic=False,
            used_item_ids=used_item_ids,
        )
        if payload:
            payload = dict(payload)
            payload["route"] = route
            return payload
    fallback = _writing_task2_fallback_payload(route)
    fallback.update({
        "rubric_focus": [],
        "expected_language_features": [],
        "bank_item_id": None,
        "source": f"writing_task2_{route.lower()}_fallback",
        "route": route,
    })
    return fallback


def _writing_route_from_score(score: float) -> str:
    if score < 4.5:
        return "A1_A2"
    if score < 7.5:
        return "B1_B2"
    return "C1_C2"


def _writing_route_from_level(level: CEFRLevel | str) -> str:
    try:
        rank = cefr_rank(CEFRLevel(str(level)))
    except ValueError:
        return "B1_B2"
    if rank <= cefr_rank(CEFRLevel.A2):
        return "A1_A2"
    if rank <= cefr_rank(CEFRLevel.B2):
        return "B1_B2"
    return "C1_C2"


def _writing_grade_to_dict(grade: WritingGradeSchema, *, fallback_route: str | None = None) -> dict:
    score = float(grade.score)
    task_fulfillment = grade.task_fulfillment or grade.task_achievement
    communicative = grade.communicative_achievement or grade.task_achievement
    organization = grade.organization or grade.coherence
    vocabulary = grade.vocabulary or grade.lexical
    spelling = grade.spelling_punctuation or min(vocabulary, grade.grammar)
    return {
        "level": grade.level.value,
        "score": round(score, 1),
        "route": fallback_route or _writing_route_from_score(score),
        "criteria": {
            "task_fulfillment": task_fulfillment,
            "communicative_achievement": communicative,
            "organization": organization,
            "grammar": grade.grammar,
            "vocabulary": vocabulary,
            "spelling_punctuation": spelling,
        },
        "feedback": grade.feedback,
    }


def _fallback_writing_task1_grade(text: str) -> dict:
    words = len(str(text or "").split())
    score = 4.0 if words < WRITING_TASK1_MIN_WORDS else 5.5
    route = _writing_route_from_score(score)
    return {
        "level": level_from_score10(score).value,
        "score": score,
        "route": route,
        "criteria": {},
        "feedback": "Preliminary writing routing used a fallback because the scorer was unavailable.",
        "fallback": True,
    }


def _fallback_writing_grade(task: dict) -> WritingGradeSchema:
    text = str(task.get("response") or "").strip()
    words = len(text.split())
    min_words = max(1, int(task.get("min_words") or WRITING_MIN_WORDS))
    max_words = int(task.get("max_words") or 0)
    length_ratio = min(1.0, words / min_words)
    has_sentence_punct = bool(re.search(r"[.!?]", text))
    sentence_count = len(re.findall(r"[.!?]", text))
    has_linkers = bool(re.search(r"\b(and|but|because|so|then|also|however|therefore|although|for example)\b", text, re.I))
    concise_bonus = 0.0 if max_words and words > max_words * 1.25 else 0.4
    base = 2.2 + (length_ratio * 3.4) + (0.7 if has_sentence_punct else 0.0) + min(1.0, sentence_count * 0.2) + (0.7 if has_linkers else 0.0) + concise_bonus
    score = round(max(2.0, min(6.4, base)), 1)
    grammar = round(max(2.0, min(6.2, score - (0.3 if not has_sentence_punct else 0.0))), 1)
    vocabulary = round(max(2.0, min(6.4, score + (0.2 if words >= min_words else -0.2))), 1)
    organization = round(max(2.0, min(6.4, score + (0.3 if has_linkers else -0.2))), 1)
    task_fulfillment = round(max(2.0, min(6.5, 2.5 + length_ratio * 3.6)), 1)
    communicative = round(max(2.0, min(6.3, score)), 1)
    spelling = round(max(2.0, min(6.2, grammar)), 1)
    weighted = round(
        task_fulfillment * 0.20
        + communicative * 0.15
        + organization * 0.20
        + grammar * 0.20
        + vocabulary * 0.20
        + spelling * 0.05,
        1,
    )
    return WritingGradeSchema(
        level=level_from_score10(weighted),
        task_achievement=task_fulfillment,
        coherence=organization,
        lexical=vocabulary,
        grammar=grammar,
        task_fulfillment=task_fulfillment,
        communicative_achievement=communicative,
        organization=organization,
        vocabulary=vocabulary,
        spelling_punctuation=spelling,
        score=weighted,
        feedback="Fallback writing score used because the AI writing scorer was temporarily unavailable.",
        detected_errors=[],
    )


def _fallback_speaking_grade(results: list[dict]) -> SpeakingGradeSchema:
    transcripts = [str(r.get("transcription") or "").strip() for r in results if str(r.get("transcription") or "").strip()]
    word_count = sum(len(t.split()) for t in transcripts)
    turn_count = len(transcripts)
    avg_words = word_count / max(1, turn_count)
    has_linkers = bool(re.search(r"\b(and|but|because|so|then|also|however|for example)\b", " ".join(transcripts), re.I))
    base = 2.4 + min(2.8, word_count / 70 * 2.8) + min(1.4, avg_words / 24 * 1.4) + (0.5 if has_linkers else 0.0)
    score = round(max(2.0, min(6.2, base)), 1)
    fluency = round(max(2.0, min(6.3, score + (0.2 if turn_count >= 2 else -0.2))), 1)
    lexical = round(max(2.0, min(6.2, score)), 1)
    grammar = round(max(2.0, min(6.1, score - 0.1)), 1)
    final_score = round((fluency + lexical + grammar) / 3, 1)
    return SpeakingGradeSchema(
        level=level_from_score10(final_score),
        fluency=fluency,
        lexical=lexical,
        grammar=grammar,
        pronunciation=0.0,
        score=final_score,
        feedback="Fallback speaking score used because the AI speaking scorer was temporarily unavailable.",
        detected_errors=[],
    )


def _error_field(error: object, field: str) -> str:
    if isinstance(error, dict):
        return str(error.get(field) or "")
    return str(getattr(error, field, "") or "")


def _compact_language_feedback_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"\s+", " ", text).strip()


def _student_answer_detected_errors(errors: list, answer_texts: list[str], *, limit: int = 5) -> list:
    """Keep only corrections whose original text appears in a student's own writing/speech."""
    haystacks = [
        compacted for compacted in (_compact_language_feedback_text(text) for text in answer_texts) if compacted
    ]
    if not haystacks:
        return []
    kept: list = []
    seen: set[tuple[str, str]] = set()
    for error in errors:
        original = _compact_language_feedback_text(_error_field(error, "original_text"))
        corrected = _compact_language_feedback_text(_error_field(error, "corrected_text"))
        if len(original) < 3 or not corrected:
            continue
        if not any(original in answer for answer in haystacks):
            continue
        key = (original, corrected)
        if key in seen:
            continue
        seen.add(key)
        kept.append(error)
        if len(kept) >= limit:
            break
    return kept


def _apply_writing_route_cap(level: CEFRLevel, route: str) -> CEFRLevel:
    rank = cefr_rank(level)
    if route == "A1_A2":
        return cefr_from_rank(min(rank, cefr_rank(CEFRLevel.B1)))
    if route == "B1_B2":
        return cefr_from_rank(min(rank, cefr_rank(CEFRLevel.B2)))
    return level


_SPEAKING_BANK_SCENARIO = {
    "scenario": "AI placement speaking assessment",
    "ai_persona": "an English placement examiner",
    "student_role": "a test-taker",
    "setting": "a spoken placement exam",
}


_SPEAKING_LEVEL_ORDER = [
    LanguageLevel.A1,
    LanguageLevel.A2,
    LanguageLevel.B1,
    LanguageLevel.B2,
    LanguageLevel.C1,
    LanguageLevel.C2,
]


def _adjacent_speaking_levels(level: LanguageLevel) -> list[LanguageLevel]:
    """CEFR levels exactly one band above/below the given level (closer direction first: up,
    then down), e.g. B1 -> [B2, A1]; A1 (no lower neighbor) -> [A2]; C2 (no higher neighbor) ->
    [C1]. Used only by _speaking_bank_prompt's diversity fallback -- never for scoring/level
    estimation, and never for any other bank skill."""
    try:
        rank = _SPEAKING_LEVEL_ORDER.index(level)
    except ValueError:
        return []
    neighbors = []
    if rank + 1 < len(_SPEAKING_LEVEL_ORDER):
        neighbors.append(_SPEAKING_LEVEL_ORDER[rank + 1])
    if rank - 1 >= 0:
        neighbors.append(_SPEAKING_LEVEL_ORDER[rank - 1])
    return neighbors


async def _speaking_bank_prompt(
    db: AsyncSession,
    *,
    language_id: int,
    level_str: str,
    used_item_ids: set[int] | None = None,
    recent_item_ids: set[int] | None = None,
    used_subskills: set[str] | None = None,
) -> dict | None:
    """Pull one verified, unused, MVP-marked speaking_prompt bank item at the target level, or
    None if the bank has nothing usable (caller falls back to live scenario/question generation)
    -- mirrors _writing_prompt's exact-level-then-fallback pattern.

    require_mvp_marker=True restricts selection to the curated MVP bank
    (body_json.review_status="mvp_approved_pending_full_review"), excluding older/legacy
    speaking_prompt rows seeded by the generic seed_placement_question_bank.py script that
    predate it -- those legacy rows are untouched (not deleted/deactivated), just never
    selected here.

    recent_item_ids is a soft cross-attempt exclusion: prefer prompts this student has not seen
    recently, then fall back to the same selection without the recent filter if the target band is
    thin. used_item_ids remains hard session-scoped exclusion so the same live attempt never asks
    the identical bank item twice.

    used_subskills, if given, is a soft diversity preference applied in priority order (never a
    hard requirement -- a thin bank can never fail to produce a prompt just because every
    remaining item shares an already-seen subskill):
      1. Target level, preferring a recent-unseen item whose subskill/task_type hasn't appeared
         this session.
      2. An adjacent CEFR level (+/-1 band), still preferring an unused subskill -- covers levels
         that today have exactly one subskill of their own (e.g. A1 = self_intro only, A2 =
         routine_description only), where a second turn at the same level would otherwise always
         repeat it even though a neighboring level has something fresh.
      3. Target level again, recent-unseen and unused bank_item_id only -- subskill may repeat.
      4. Repeat steps 1-3 without the recent filter, while still excluding this session's items.
      5. None -- caller falls back to live AI generation."""
    try:
        lvl = LanguageLevel(level_str)
    except ValueError:
        lvl = LanguageLevel.A2
    session_used_ids = {int(x) for x in (used_item_ids or set()) if x is not None}
    recent_ids = {int(x) for x in (recent_item_ids or set()) if x is not None}

    async def _at_level(
        level: LanguageLevel,
        *,
        exclude_subskills: set[str] | None,
        avoid_recent: bool,
    ) -> dict | None:
        excluded_ids = session_used_ids | (recent_ids if avoid_recent else set())
        for row in await select_placement_bank_items(
            db,
            language_id=language_id,
            skill="speaking_prompt",
            level=level,
            count=1,
            used_item_ids=excluded_ids,
            require_mvp_marker=True,
            exclude_subskills=exclude_subskills,
        ):
            item = bank_item_to_exam_item(row)
            if str(item.get("question") or "").strip():
                return item
        return None

    for avoid_recent in (True, False):
        if used_subskills:
            item = await _at_level(lvl, exclude_subskills=used_subskills, avoid_recent=avoid_recent)
            if item is not None:
                return item
            for neighbor in _adjacent_speaking_levels(lvl):
                item = await _at_level(neighbor, exclude_subskills=used_subskills, avoid_recent=avoid_recent)
                if item is not None:
                    return item

        item = await _at_level(lvl, exclude_subskills=None, avoid_recent=avoid_recent)
        if item is not None:
            return item

    return None


def _speaking_bank_question_text(item: dict) -> str:
    situation = str(item.get("situation") or "").strip()
    question = str(item.get("question") or "").strip()
    return f"{situation} {question}".strip() if situation else question


def _speaking_scenario_from_bank_item(item: dict) -> dict:
    """A generic, honest scenario descriptor for bank-sourced speaking turns -- curated items are
    independent semi-structured prompts, not a continuous roleplay, so persona/setting stay
    fixed for the session rather than switching per item (MVP simplification)."""
    return {**_SPEAKING_BANK_SCENARIO, "opening_question": _speaking_bank_question_text(item)}


def _already_used_speaking_bank_item_ids(state: dict, section: str) -> set[int]:
    """Bank item ids already asked in this session's speaking-like section. Mirrors
    _already_used_bank_item_ids (P1.1) for MCQ sections, but speaking's turn history lives under
    "results", not "asked"."""
    results = state.get(section, {}).get("results", []) or []
    return {int(r["bank_item_id"]) for r in results if r.get("bank_item_id")}


def _already_used_speaking_subskills(state: dict, section: str) -> set[str]:
    """Subskill/task_type values already asked in this session's speaking-like section -- used
    only as _speaking_bank_prompt's soft diversity preference (never a hard exclusion), so
    back-to-back turns avoid repeating the same task type (e.g. self_intro, self_intro) when a
    fresher one is available at the target level."""
    results = state.get(section, {}).get("results", []) or []
    return {str(r["bank_item_subskill"]) for r in results if r.get("bank_item_subskill")}


RECENT_SPEAKING_PROMPT_DAYS = 30
RECENT_SPEAKING_PROMPT_STUDENT_SESSIONS = 12
RECENT_SPEAKING_PROMPT_LANGUAGE_SESSIONS = 24


def _speaking_bank_ids_from_state(state: dict | None) -> set[int]:
    if not isinstance(state, dict):
        return set()
    ids: set[int] = set()

    def add_id(value: object) -> None:
        try:
            if value:
                ids.add(int(value))
        except (TypeError, ValueError):
            return

    for section in SPEAKING_LIKE:
        spoken = state.get(section) or {}
        add_id(spoken.get("pending_bank_item_id"))
        for result in spoken.get("results", []) or []:
            add_id(result.get("bank_item_id"))
    return ids


async def _recent_speaking_bank_item_ids(
    db: AsyncSession,
    *,
    language_id: int,
    student_id: int | None = None,
    session_limit: int = RECENT_SPEAKING_PROMPT_STUDENT_SESSIONS,
) -> set[int]:
    since = datetime.now(timezone.utc) - timedelta(days=RECENT_SPEAKING_PROMPT_DAYS)
    stmt = (
        select(LanguageExamSession.exam_state)
        .where(
            LanguageExamSession.language_id == language_id,
            LanguageExamSession.exam_state.isnot(None),
            LanguageExamSession.created_at >= since,
        )
        .order_by(LanguageExamSession.created_at.desc())
        .limit(max(1, int(session_limit or 1)))
    )
    if student_id is not None:
        stmt = stmt.where(LanguageExamSession.student_id == student_id)
    rows = (
        await db.execute(stmt)
    ).scalars().all()
    ids: set[int] = set()
    for state in rows:
        ids.update(_speaking_bank_ids_from_state(state))
    return ids


async def _recent_speaking_exclusion_ids(
    db: AsyncSession,
    *,
    language_id: int,
    student_id: int,
) -> set[int]:
    student_recent = await _recent_speaking_bank_item_ids(
        db,
        language_id=language_id,
        student_id=student_id,
        session_limit=RECENT_SPEAKING_PROMPT_STUDENT_SESSIONS,
    )
    language_recent = await _recent_speaking_bank_item_ids(
        db,
        language_id=language_id,
        student_id=None,
        session_limit=RECENT_SPEAKING_PROMPT_LANGUAGE_SESSIONS,
    )
    return student_recent | language_recent


# ---------------------------------------------------------------------------------------
# state -> output contract
# ---------------------------------------------------------------------------------------

def _current_section(state: dict) -> str | None:
    cursor = state.get("cursor", 0)
    sections = state.get("sections", SECTIONS)
    if cursor >= len(sections):
        return None
    return sections[cursor]


def _parse_exam_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _ensure_exam_timer(state: dict, *, now: datetime | None = None) -> bool:
    if not isinstance(state, dict):
        return False
    current = now or datetime.now(timezone.utc)
    changed = False
    try:
        duration = int(state.get("exam_duration_seconds") or 0)
    except (TypeError, ValueError):
        duration = 0
    if duration <= 0:
        duration = PLACEMENT_EXAM_DURATION_SECONDS
        state["exam_duration_seconds"] = duration
        changed = True

    started_at = _parse_exam_datetime(state.get("exam_started_at"))
    if started_at is None:
        started_at = current
        state["exam_started_at"] = started_at.isoformat()
        changed = True

    expires_at = _parse_exam_datetime(state.get("exam_expires_at"))
    if expires_at is None:
        state["exam_expires_at"] = (started_at + timedelta(seconds=duration)).isoformat()
        changed = True
    return changed


def _exam_remaining_seconds(state: dict, *, now: datetime | None = None) -> int:
    snapshot = dict(state or {})
    current = now or datetime.now(timezone.utc)
    _ensure_exam_timer(snapshot, now=current)
    expires_at = _parse_exam_datetime(snapshot.get("exam_expires_at"))
    if expires_at is None:
        return PLACEMENT_EXAM_DURATION_SECONDS
    return max(0, int(math.ceil((expires_at - current).total_seconds())))


def _exam_timer_payload(state: dict, *, now: datetime | None = None) -> dict:
    snapshot = dict(state or {})
    current = now or datetime.now(timezone.utc)
    _ensure_exam_timer(snapshot, now=current)
    remaining = _exam_remaining_seconds(snapshot, now=current)
    try:
        duration = int(snapshot.get("exam_duration_seconds") or PLACEMENT_EXAM_DURATION_SECONDS)
    except (TypeError, ValueError):
        duration = PLACEMENT_EXAM_DURATION_SECONDS
    return {
        "exam_duration_seconds": duration,
        "exam_started_at": _parse_exam_datetime(snapshot.get("exam_started_at")),
        "exam_expires_at": _parse_exam_datetime(snapshot.get("exam_expires_at")),
        "time_remaining_seconds": remaining,
        "time_expired": bool(snapshot.get("exam_time_expired")) or remaining <= 0,
    }


def _time_expired_detail(state: dict) -> dict:
    return {
        "code": "time_expired",
        "message": PLACEMENT_EXAM_TIME_EXPIRED_MESSAGE,
        "current_state_revision": _state_revision(state),
    }


def _expire_exam_if_needed(
    sess: LanguageExamSession,
    state: dict,
    *,
    now: datetime | None = None,
) -> bool:
    current = now or datetime.now(timezone.utc)
    changed = _ensure_exam_timer(state, now=current)
    if sess.status == "in_progress" and _exam_remaining_seconds(state, now=current) <= 0:
        state["exam_time_expired"] = True
        state["exam_time_expired_at"] = current.isoformat()
        state["evaluation"] = {
            **dict(state.get("evaluation") or {}),
            "evaluation_status": "time_expired",
            "error_code": "time_expired",
            "error_message": PLACEMENT_EXAM_TIME_EXPIRED_MESSAGE,
        }
        sess.status = "failed"
        sess.is_completed = False
        _bump_state_revision(state)
        changed = True
    return changed


def _expired_incomplete_exam_can_be_replaced(sess: LanguageExamSession, state: dict) -> bool:
    return (
        sess.status == "failed"
        and state.get("exam_time_expired") is True
        and sess.is_completed is not True
    )


async def _build_state_out(
    db: AsyncSession,
    sess: LanguageExamSession,
    *,
    last_feedback: SpeakingTurnFeedbackOut | None = None,
    resumed: bool = False,
    requested_section: str | None = None,
) -> ExamStateOut:
    """Render a state snapshot without locks or external AI/STT/TTS work.

    requested_section: free section navigation. When given and it's a real member of
    state["sections"], render THAT section instead of the session's internal progress cursor's
    section -- the cursor itself is never touched by viewing a different section (it still only
    ever advances past sections that are actually done, see _advance_if_section_done), so this is
    purely a rendering choice, not a state mutation. Falls back to the cursor's section when
    omitted or invalid, which is the exact prior behavior.
    """
    _ = db
    state = sess.exam_state or {}
    sections = state.get("sections", SECTIONS)
    cursor = state.get("cursor", 0)
    revision = _state_revision(state)
    completed_sections = [s for s in sections if state.get(s, {}).get("done")]
    timer = _exam_timer_payload(state)

    if sess.status in ("evaluating", "completed", "failed") or cursor >= len(sections):
        phase = sess.status if sess.status in ("completed", "failed") else "evaluating"
        evaluation = dict(state.get("evaluation") or {})
        evaluation_status = str(
            evaluation.get("evaluation_status") or evaluation.get("status") or "retry_required"
        )
        return ExamStateOut(
            session_id=sess.id, state_revision=revision, phase=phase, section_index=len(sections),
            section_total=len(sections), sections=sections, completed_sections=completed_sections,
            resumed=resumed,
            **timer,
            evidence_status="completed" if sess.status == "completed" else evaluation_status,
            error_code=evaluation.get("error_code"),
            error_message=evaluation.get("error_message"),
        )

    section = requested_section if requested_section in sections else sections[cursor]
    section_index = sections.index(section)

    # Reading/listening/writing content is generated in the background; until it's ready, tell the
    # frontend to show a loader and poll. (Older sessions without the flag are treated as ready.)
    if section in PREPARED_SECTIONS and not state.get(section, {}).get("ready", True):
        unavailable = (
            state.get(section, {}).get("evidence_status") == "content_unavailable"
            or state.get("content_prep_status") == "content_unavailable"
        )
        return ExamStateOut(
            session_id=sess.id,
            state_revision=revision,
            phase="content_unavailable" if unavailable else "preparing",
            section_index=section_index,
            section_total=len(sections), sections=sections, completed_sections=completed_sections,
            resumed=resumed,
            **timer,
            evidence_status="content_unavailable" if unavailable else "retry_required",
            error_code="content_unavailable" if unavailable else None,
            error_message=(
                "Required placement content is temporarily unavailable. Please retry."
                if unavailable
                else None
            ),
        )

    out = ExamStateOut(
        session_id=sess.id, state_revision=revision, phase=section, section_index=section_index,
        section_total=len(sections),
        sections=sections, completed_sections=completed_sections, last_feedback=last_feedback, resumed=resumed,
        **timer,
        evidence_status=str(state.get(section, {}).get("evidence_status") or "missing_student_response"),
    )

    if section in SPEAKING_LIKE:
        sp = state[section]
        scenario = state.get("speaking", {}).get("scenario", {})
        title = "Spoken interview" if section == "interview" else scenario.get("scenario", "Role-play")
        out.speaking = SpeakingPromptOut(
            scenario_title=title,
            setting="" if section == "interview" else scenario.get("setting", ""),
            examiner_message=sp.get("pending_question", ""),
            turn=sp.get("turn", 1),
            total_turns=sp.get("total_turns", INTERVIEW_TURNS if section == "interview" else SPEAKING_TURNS),
            turn_token=str(sp.get("turn_token") or ""),
        )
        out.turn_token = out.speaking.turn_token
    elif section in MCQ_SECTIONS:
        sec = state[section]
        item = _resolve_current_exam_item(sec, sec.get("current_level"), dual_slot=(section == "listening"))
        if item and not sec.get("done"):
            audio_url = None
            passage = item.get("passage") or None if section == "reading" else None
            situation = item.get("situation") or None if section == "listening" else None
            instructions = "Choose the best answer."
            if section == "listening":
                instructions = "Listen to the clip, then answer."
                audio_url = str(item.get("audio_url") or "") or None
                if not audio_url:
                    out.phase = "content_unavailable"
                    out.evidence_status = "content_unavailable"
                    out.error_code = "listening_audio_unavailable"
                    out.error_message = "Listening audio is temporarily unavailable. Please retry."
                    return out
            elif section == "reading":
                instructions = "Read the passage, then answer."
            elif section == "grammar_vocab":
                instructions = "Choose the most accurate English option."
            subquestions = item.get("subquestions")
            blanks = item.get("blanks")
            out.mcq = McqPromptOut(
                instructions=instructions,
                passage=passage,
                audio_url=audio_url,
                situation=situation,
                question=item.get("question", ""),
                options=item.get("options", []),
                item_index=len(sec.get("asked", [])),
                item_total=sec.get("max_steps", ADAPTIVE_MAX_STEPS),
                question_token=str(item.get("question_token") or ""),
                question_type=item.get("question_type", "mcq"),
                word_bank=item.get("word_bank"),
                subquestions=(
                    [
                        ListeningSubquestionOut(
                            question=sq.get("question", ""),
                            options=sq.get("options", []),
                            response_type=_reading_subquestion_response_type(sq),
                            max_words=sq.get("max_words"),
                            word_bank=sq.get("word_bank"),
                            matching_items=sq.get("matching_items"),
                            match_options=sq.get("match_options"),
                        )
                     for sq in subquestions]
                    if isinstance(subquestions, list) else None
                ),
                note_template=item.get("note_template"),
                blank_count=len(blanks) if isinstance(blanks, list) else None,
            )
            out.question_token = out.mcq.question_token
    elif section == "writing":
        wr = state["writing"]
        out.writing = WritingPromptOut(
            prompt=wr.get("prompt", ""),
            min_words=wr.get("min_words", WRITING_MIN_WORDS),
            max_words=wr.get("max_words"),
            task_type=str(wr.get("task_type") or ""),
            student_instructions=str(wr.get("student_instructions") or ""),
            task_index=int(wr.get("task_index") or 1),
            task_total=int(wr.get("task_total") or 1),
            prompt_token=str(wr.get("prompt_token") or ""),
        )
        out.prompt_token = out.writing.prompt_token

    return out


# Persistent Listening bank-audio cache (Phase 1: language_listening_bank_audio_backfill_service.py
# populates audio_meta_json for reachable rows). Kept as a literal here, not imported from that
# service module, to avoid a circular import -- that module already imports
# _listening_text_from_body from this one.
_LISTENING_BANK_CACHE_URL_PREFIX = "/uploads/language_placement_bank_audio/"
# Matches MIN_VALID_AUDIO_BYTES in the backfill service -- the same "is this a real clip or a
# truncated/corrupt write" sanity floor, re-applied here since the file on disk could have been
# deleted, corrupted, or truncated by something entirely outside the backfill script since then.
_MIN_VALID_BANK_CACHE_BYTES = 512


def _safe_upload_relative_path(relative: str | None) -> Path | None:
    """Resolve a candidate UPLOAD_DIR-relative path safely, refusing anything that would escape
    UPLOAD_DIR (parent traversal, an absolute path smuggled in as "relative", etc). Returns None
    if the input is empty, not a string, or resolves outside UPLOAD_DIR."""
    if not relative or not isinstance(relative, str):
        return None
    upload_root = Path(get_settings().UPLOAD_DIR).resolve()
    try:
        candidate = (upload_root / relative).resolve()
    except (OSError, ValueError):
        return None
    if not candidate.is_relative_to(upload_root):
        return None
    return candidate


def _is_valid_bank_cache_file(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size >= _MIN_VALID_BANK_CACHE_BYTES
    except OSError:
        return False


def _validate_local_bank_cache_url(
    url: str, audio_meta: dict | None, *, bank_item_id: int | None, expected_voice: str | None = None
) -> str | None:
    """For a persistent Listening bank-cache URL, confirm the underlying local file genuinely
    exists (and clears a trivial-size floor) before trusting it, so a deleted/corrupted/truncated
    cache entry falls through to runtime synthesis instead of serving a dead link. Any other URL
    (remote http(s)://, the source-controlled static listening assets) is returned unchanged --
    only this specific persistent local cache gets the extra scrutiny. Never logs the transcript,
    and only ever logs on rejection -- a normal valid cache hit produces no log output."""
    if not url.startswith(_LISTENING_BANK_CACHE_URL_PREFIX):
        return url

    if expected_voice and isinstance(audio_meta, dict) and audio_meta.get("voice") != expected_voice:
        logger.warning(
            "Listening bank-cache audio rejected: voice mismatch bank_item_id=%s expected_voice=%s",
            bank_item_id,
            expected_voice,
        )
        return None

    relative = (audio_meta or {}).get("storage_key") or url[len("/uploads/") :]
    path = _safe_upload_relative_path(relative)
    if path is None:
        logger.warning(
            "Listening bank-cache audio rejected: unsafe cache path bank_item_id=%s", bank_item_id
        )
        return None
    if not _is_valid_bank_cache_file(path):
        logger.warning(
            "Listening bank-cache audio rejected: missing or invalid file bank_item_id=%s", bank_item_id
        )
        return None
    return url


async def _resolve_listening_audio(db: AsyncSession | None, item: dict) -> str | None:
    """Return only audio that is tied to the same transcript as the question.

    If the audio cannot be tied to this item, the caller must generate it server-side or fail closed;
    the private transcript is never sent to the browser.
    """

    audio_text = str(item.get("audio_text") or "").strip() or _listening_text_from_body(item.get("body") or {})
    expected_voice = _listening_tts_voice_for_text(audio_text) if audio_text else None
    audio_url = item.get("audio_url")
    if _is_usable_audio_url(audio_url):
        validated = _validate_local_bank_cache_url(
            str(audio_url),
            item.get("audio_meta"),
            bank_item_id=item.get("bank_item_id"),
            expected_voice=expected_voice,
        )
        if validated:
            return validated

    content_item_id = item.get("content_id")
    if not content_item_id or db is None:
        return None

    content = await db.get(LanguageContentItem, content_item_id)
    body = content.body_json if content else {}
    body_audio_url = (body or {}).get("audio_url")
    if _listening_text_from_body(body) and _is_usable_audio_url(body_audio_url):
        return str(body_audio_url)
    return None


async def _resolve_listening_audio_text(db: AsyncSession | None, item: dict) -> str | None:
    text = str(item.get("audio_text") or "").strip()
    if text:
        return text
    text = _listening_text_from_body(item.get("body") or {})
    if text:
        return text

    content_item_id = item.get("content_id")
    if not content_item_id or db is None:
        return None
    content = await db.get(LanguageContentItem, content_item_id)
    body = content.body_json if content else {}
    text = _listening_text_from_body(body)
    return text or None


_LISTENING_TTS_TIMEOUT_S = 25


async def _materialize_listening_audio(
    db: AsyncSession | None, item: dict
) -> tuple[str | None, str | None, bool]:
    """Ensure a listening item has a real audio URL generated from its own transcript.

    Bounded by _LISTENING_TTS_TIMEOUT_S: a cold Supertonic engine can take minutes to load on the
    very first synthesis of a fresh process (one-time model download). Rather than letting that
    block this item -- and every later item in the same _prepare_content pass -- indefinitely, a
    slow attempt times out and this rung is dropped (existing graceful-degradation policy: missing
    audio removes the rung instead of exposing its transcript). The underlying engine load itself
    is not cancelled by this timeout (see _ensure_engine_loaded's asyncio.shield) -- it keeps
    warming up in the background, so the next item, the next retry, or the next session's attempt
    finds it already loaded and completes quickly."""

    audio_url = await _resolve_listening_audio(db, item)
    audio_text = await _resolve_listening_audio_text(db, item)
    if audio_url:
        return audio_url, audio_text, False
    if not audio_text:
        return None, None, False

    generated_url = None
    try:
        segments = _listening_tts_segments_for_item(item, audio_text)
        if segments:
            generated_url = await asyncio.wait_for(
                synthesize_exam_audio_segments(segments), timeout=_LISTENING_TTS_TIMEOUT_S
            )
        else:
            voice = _listening_tts_voice_for_text(audio_text)
            generated_url = await asyncio.wait_for(
                synthesize_exam_audio(audio_text, voice=voice), timeout=_LISTENING_TTS_TIMEOUT_S
            )
    except Exception as exc:  # pragma: no cover - model/runtime variance
        logger.warning("Placement listening TTS failed error_type=%s", type(exc).__name__)

    if _is_usable_audio_url(generated_url):
        item["audio_url"] = str(generated_url)
        item["audio_text"] = audio_text
        return str(generated_url), audio_text, True

    item["audio_text"] = audio_text
    return None, audio_text, False


def _advance_if_section_done(state: dict) -> None:
    """Move the cursor forward while the current section is marked done."""
    sections = state.get("sections", SECTIONS)
    while state.get("cursor", 0) < len(sections):
        section = sections[state["cursor"]]
        if state.get(section, {}).get("done"):
            state["cursor"] += 1
        else:
            break


_REQUEST_RECEIPT_LIMIT = 100


def _normalise_writing_text(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text or "").split())


def canonical_payload_hash(*, kind: str, payload: dict) -> str:
    """Hash a canonical operation payload for durable idempotency receipts."""
    encoded = json.dumps(
        {"kind": kind, **payload},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _request_receipt(
    state: dict,
    *,
    kind: str,
    request_id: str,
    payload_hash: str,
) -> dict | None:
    """Return the completed receipt, or reject reuse of an id with different input."""
    for receipt in state.get("request_receipts", []):
        # ``id`` is accepted only to read receipts produced by early phase-zero builds.
        stored_request_id = receipt.get("request_id") or receipt.get("id")
        if stored_request_id != request_id:
            continue
        if receipt.get("kind") == kind and secrets.compare_digest(
            str(receipt.get("payload_hash") or ""), payload_hash
        ):
            return receipt
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "idempotency_conflict",
                "message": "request_id was already used with a different payload.",
                "current_state_revision": _state_revision(state),
            },
        )
    return None


def _record_request(
    state: dict,
    *,
    kind: str,
    request_id: str,
    payload_hash: str,
    request_revision: int,
    token: str,
    result_reference: str,
) -> None:
    receipts = list(state.get("request_receipts", []))
    receipts.append(
        {
            "request_id": request_id,
            "kind": kind,
            "payload_hash": payload_hash,
            "state_revision": request_revision,
            "token": token,
            "result_reference": result_reference,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    state["request_receipts"] = receipts[-_REQUEST_RECEIPT_LIMIT:]


def _require_current_state(
    state: dict,
    *,
    supplied_revision: int,
    supplied_token: str,
    expected_token: str,
) -> None:
    _require_state_revision(state, supplied_revision=supplied_revision)
    current_revision = _state_revision(state)
    if not expected_token or not secrets.compare_digest(
        str(supplied_token), str(expected_token)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "stale_exam_state",
                "message": "The exam moved forward. Refresh the current question before retrying.",
                "current_state_revision": current_revision,
            },
        )


def _require_state_revision(state: dict, *, supplied_revision: int) -> None:
    current_revision = _state_revision(state)
    if supplied_revision != current_revision:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "stale_exam_state",
                "message": "The exam moved forward. Refresh the current question before retrying.",
                "current_state_revision": current_revision,
            },
        )


def _audio_hash_already_used(state: dict, audio_sha256: str) -> bool:
    return any(
        str(result.get("audio_sha256") or "") == audio_sha256
        for spoken_section in SPEAKING_LIKE
        for result in state.get(spoken_section, {}).get("results", [])
    )


def exam_evidence_statuses(state: dict) -> dict[str, str]:
    """Classify evidence without blaming the student for missing server-side content."""
    statuses: dict[str, str] = {}
    # Gated on the section's own key being present in state at all (not just "sections"
    # membership): a session that never had this section persists no dict for it (e.g. a
    # narrower exam variant, or an isolated single-section test fixture), and answer_mcq now
    # reaches this same finalize check that submit_writing/speaking_turn always have (free
    # navigation's _maybe_finalize fix) -- such a state must not be blocked on evidence for a
    # section it never had. A session that DOES carry a (possibly incomplete) dict for the
    # section is still held to the existing requirement regardless of "sections" membership,
    # preserving the original incomplete-exam guard exactly.
    session_sections = state.get("sections") or SECTIONS
    for section in (s for s in ("listening", "reading", "grammar_vocab") if s in state):
        section_state = state.get(section, {})
        declared = str(section_state.get("evidence_status") or "")
        if declared in {"content_unavailable", "retry_required", "unassessed"}:
            statuses[section] = declared
            continue
        if not section_state.get("ready", True) or not section_state.get("pool"):
            statuses[section] = "content_unavailable"
            continue
        asked = section_state.get("asked") or []
        valid = [
            answer
            for answer in asked
            if isinstance(answer.get("correct"), bool)
            and bool(answer.get("level"))
            and (
                # Legacy single-answer MCQ/Gap-Fill, a Listening bundle's multi-part answer
                # (chosen_indices/answer_texts), or a mixed Reading bundle's subquestion_answers
                # -- any one of these shapes is real recorded student evidence.
                isinstance(answer.get("chosen_index"), int)
                or isinstance(answer.get("chosen_indices"), list)
                or isinstance(answer.get("answer_text"), str)
                or isinstance(answer.get("answer_texts"), list)
                or isinstance(answer.get("subquestion_answers"), list)
            )
        ]
        if not valid or section_state.get("done") is not True:
            statuses[section] = "missing_student_response"
        else:
            statuses[section] = "completed"

    if "writing" in state:
        writing = state.get("writing", {})
        min_words = max(WRITING_MIN_WORDS, int(writing.get("min_words") or WRITING_MIN_WORDS))
        declared = str(writing.get("evidence_status") or "")
        if declared in {"content_unavailable", "retry_required", "unassessed"}:
            statuses["writing"] = declared
        elif not writing.get("ready", True) or not str(writing.get("prompt") or "").strip():
            statuses["writing"] = "content_unavailable"
        elif int(writing.get("task_total") or 1) > 1:
            tasks = writing.get("tasks") or []
            task_total = int(writing.get("task_total") or 1)
            completed_tasks = [
                task
                for task in tasks[:task_total]
                if len(str(task.get("response") or "").split())
                >= max(1, int(task.get("min_words") or WRITING_MIN_WORDS))
            ]
            if writing.get("done") is not True or len(completed_tasks) < task_total:
                statuses["writing"] = "missing_student_response"
            else:
                statuses["writing"] = "completed"
        elif writing.get("done") is not True or len(str(writing.get("response") or "").split()) < min_words:
            statuses["writing"] = "missing_student_response"
        else:
            statuses["writing"] = "completed"

    # New sessions have no "interview" entry and must not be blocked on it; old sessions that
    # still have "interview" must keep requiring it (same session_sections rule as above).
    spoken_defaults = [("speaking", SPEAKING_TURNS), ("interview", INTERVIEW_TURNS)]
    for section, default_turns in [(s, t) for s, t in spoken_defaults if s in session_sections]:
        spoken = state.get(section, {})
        declared = str(spoken.get("evidence_status") or "")
        if declared in {"content_unavailable", "retry_required", "unassessed"}:
            statuses[section] = declared
            continue
        required = max(1, int(spoken.get("total_turns") or default_turns))
        results = spoken.get("results") or []
        valid = [
            result
            for result in results
            if str(result.get("transcription") or "").strip()
            and str(result.get("audio_sha256") or "").strip()
            and str(result.get("question") or "").strip()
        ]
        distinct_audio = {str(result.get("audio_sha256")) for result in valid}
        if spoken.get("done") is not True or len(valid) < required or len(distinct_audio) < required:
            statuses[section] = "missing_student_response"
        else:
            statuses[section] = "completed"
    return statuses


def missing_exam_evidence(state: dict) -> dict[str, str]:
    """Return incomplete sections with a stable, report-safe reason."""
    messages = {
        "missing_student_response": "A required student response is missing.",
        "content_unavailable": "Required exam content is temporarily unavailable.",
        "scorer_unavailable": "The authoritative scorer is temporarily unavailable.",
        "retry_required": "This section must be retried.",
        "unassessed": "This section has not been authoritatively assessed.",
    }
    return {
        section: messages[section_status]
        for section, section_status in exam_evidence_statuses(state).items()
        if section_status != "completed"
    }


def _ensure_exam_evidence_complete(state: dict) -> None:
    missing = missing_exam_evidence(state)
    if missing:
        statuses = exam_evidence_statuses(state)
        technical = {
            section: section_status
            for section, section_status in statuses.items()
            if section_status in {"content_unavailable", "scorer_unavailable", "retry_required", "unassessed"}
        }
        if technical:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "exam_evidence_unavailable",
                    "message": "Required exam evidence is temporarily unavailable. Please retry.",
                    "section_statuses": statuses,
                    "retry_sections": list(technical),
                },
            )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "incomplete_exam",
                "message": "The placement test is missing required evidence.",
                "missing_sections": list(missing),
                "missing_evidence": missing,
                "section_statuses": statuses,
            },
        )


def _provisional_from_phase1(state: dict) -> tuple[CEFRLevel, str]:
    """Deterministic Phase-1 rollup: provisional level + the most uncertain/weak area."""
    levels: list[CEFRLevel] = []
    sp_results = state.get("speaking", {}).get("results", [])
    sp_levels = []
    for r in sp_results:
        try:
            sp_levels.append(CEFRLevel(r.get("estimated_level")))
        except (ValueError, TypeError):
            pass
    speaking_level = overall_level(sp_levels) if sp_levels else None

    def _comp_level(section: str) -> CEFRLevel | None:
        asked = state.get(section, {}).get("asked", [])
        if not asked:
            return None
        level, _ = _reading_weighted_result(asked) if section == "reading" else adaptive_result(asked)
        return level

    reading_level = _comp_level("reading")
    listening_level = _comp_level("listening")
    grammar_vocab_level = _comp_level("grammar_vocab")
    for lv in (speaking_level, reading_level, listening_level, grammar_vocab_level):
        if lv is not None:
            levels.append(lv)
    provisional = overall_level(levels) if levels else CEFRLevel.A2

    # The "uncertain band" = where the skills disagree most; weak area = lowest skill.
    named = [
        ("speaking", speaking_level),
        ("reading", reading_level),
        ("listening", listening_level),
        ("grammar/vocabulary", grammar_vocab_level),
    ]
    present = [(n, lv) for n, lv in named if lv is not None]
    weak = min(present, key=lambda x: cefr_rank(x[1]))[0] if present else "speaking"
    nxt = cefr_from_rank(cefr_rank(provisional) + 1)
    priming = (
        f"Provisional level ~{provisional.value}; weakest area so far is {weak}. "
        f"Probe the {provisional.value}/{nxt.value} boundary and pressure-test {weak}."
    )
    return provisional, priming


async def _ensure_interview_ready(state: dict) -> None:
    """Lazily build the Phase-2 priming + opening question when entering the interview section."""
    if _current_section(state) != "interview":
        return
    iv = state.setdefault("interview", {})
    if iv.get("pending_question"):
        return
    _, priming = _provisional_from_phase1(state)
    iv["priming"] = priming
    iv["total_turns"] = iv.get("total_turns", INTERVIEW_TURNS)
    iv["turn"] = iv.get("turn", 1)
    iv.setdefault("results", [])
    iv["pending_question"] = await ai_engine.interview_opening(
        priming=priming,
        scenario=state.get("speaking", {}).get("scenario", {}),
        learner_grade=state.get("learner_grade"),
    )
    iv["turn_token"] = _new_exam_token()
    iv["evidence_status"] = "missing_student_response"


# ---------------------------------------------------------------------------------------
# background final evaluation
# ---------------------------------------------------------------------------------------

# Realistic study time to climb one CEFR band (higher bands take longer); C2 = already top.
_WEEKS_TO_NEXT = {"A1": 10, "A2": 12, "B1": 16, "B2": 20, "C1": 24, "C2": 0}


def _weeks_to_next_level(level: CEFRLevel) -> int:
    return _WEEKS_TO_NEXT.get(level.value, 14)


def _reading_diagnostic_breakdown(asked: list[dict]) -> dict:
    by_subskill: dict[str, dict] = {}
    word_counts: list[int] = []
    levels_seen: list[str] = []
    questions_answered = 0

    def record_subskill(subskill_value: object, is_correct: bool) -> None:
        subskill = str(subskill_value or "comprehension").strip() or "comprehension"
        bucket = by_subskill.setdefault(
            subskill,
            {"answered": 0, "correct": 0, "score_percent": 0.0},
        )
        bucket["answered"] += 1
        if is_correct:
            bucket["correct"] += 1

    for answer in asked or []:
        level = str(answer.get("level") or "")
        if level and level not in levels_seen:
            levels_seen.append(level)
        sub_correct = answer.get("sub_correct")
        subskills = answer.get("subskills")
        if isinstance(sub_correct, list) and sub_correct:
            questions_answered += len(sub_correct)
            subskills_list = subskills if isinstance(subskills, list) else []
            fallback_subskill = answer.get("subskill") or "comprehension"
            for idx, flag in enumerate(sub_correct):
                record_subskill(
                    subskills_list[idx] if idx < len(subskills_list) else fallback_subskill,
                    bool(flag),
                )
        else:
            questions_answered += 1
            record_subskill(answer.get("subskill") or "comprehension", bool(answer.get("correct")))
        try:
            wc = int(answer.get("word_count") or 0)
        except (TypeError, ValueError):
            wc = 0
        if wc > 0:
            word_counts.append(wc)
    for bucket in by_subskill.values():
        bucket["score_percent"] = round(bucket["correct"] / bucket["answered"] * 100, 1) if bucket["answered"] else 0.0
    return {
        "items_answered": len(asked or []),
        "questions_answered": questions_answered,
        "levels_seen": levels_seen,
        "average_passage_word_count": round(sum(word_counts) / len(word_counts), 1) if word_counts else 0.0,
        "by_subskill": by_subskill,
    }


def _parse_utc(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def evaluation_lease_expired(state: dict, *, now: datetime | None = None) -> bool:
    evaluation = dict(state.get("evaluation") or {})
    current_status = str(evaluation.get("evaluation_status") or evaluation.get("status") or "")
    if current_status != "running":
        return True
    expiry = _parse_utc(evaluation.get("evaluation_lease_expires_at") or evaluation.get("lease_expires_at"))
    return expiry is None or expiry <= (now or datetime.now(timezone.utc))


def _evaluation_should_run(state: dict) -> bool:
    evaluation = dict(state.get("evaluation") or {})
    current_status = str(evaluation.get("evaluation_status") or evaluation.get("status") or "pending")
    return current_status in {"pending", "retry_required", "scorer_unavailable", "failed"} or (
        current_status == "running" and evaluation_lease_expired(state)
    )


async def _claim_evaluation_lease(session_id: str) -> tuple[str, dict, int, int] | None:
    """Atomically own an evaluation attempt, returning an immutable evidence snapshot."""
    now = datetime.now(timezone.utc)
    owner = uuid.uuid4().hex
    async with AsyncSessionLocal() as claim_db:
        sess = (
            await claim_db.execute(
                select(LanguageExamSession)
                .where(LanguageExamSession.id == session_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if not sess or sess.status != "evaluating" or sess.is_completed:
            return None
        if not check("placement_evaluation", f"{sess.student_id}:{session_id}"):
            return None
        state = copy.deepcopy(sess.exam_state or {})
        _ensure_exam_evidence_complete(state)
        evaluation = dict(state.get("evaluation") or {})
        current_status = str(evaluation.get("evaluation_status") or evaluation.get("status") or "pending")
        if current_status == "running" and not evaluation_lease_expired(state, now=now):
            return None
        evaluation.update(
            {
                "evaluation_status": "running",
                "evaluation_started_at": now.isoformat(),
                "evaluation_lease_expires_at": (
                    now + timedelta(seconds=EVALUATION_LEASE_SECONDS)
                ).isoformat(),
                "evaluation_attempt": int(
                    evaluation.get("evaluation_attempt") or evaluation.get("attempt") or 0
                )
                + 1,
                "evaluation_owner": owner,
            }
        )
        for old_key in ("status", "started_at", "attempt", "lease_expires_at"):
            evaluation.pop(old_key, None)
        state["evaluation"] = evaluation
        _bump_state_revision(state)
        sess.exam_state = state
        flag_modified(sess, "exam_state")
        await claim_db.commit()
        return owner, copy.deepcopy(state), sess.student_id, sess.language_id


async def _renew_evaluation_lease(session_id: str, owner: str) -> bool:
    """Extend a live owner's lease in a short, owner-fenced transaction."""
    async with AsyncSessionLocal() as lease_db:
        sess = (
            await lease_db.execute(
                select(LanguageExamSession)
                .where(LanguageExamSession.id == session_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if not sess or sess.status != "evaluating" or sess.is_completed:
            return False
        state = copy.deepcopy(sess.exam_state or {})
        evaluation = dict(state.get("evaluation") or {})
        if (
            str(evaluation.get("evaluation_status") or "") != "running"
            or not secrets.compare_digest(str(evaluation.get("evaluation_owner") or ""), owner)
        ):
            return False
        evaluation["evaluation_lease_expires_at"] = (
            datetime.now(timezone.utc) + timedelta(seconds=EVALUATION_LEASE_SECONDS)
        ).isoformat()
        state["evaluation"] = evaluation
        _bump_state_revision(state)
        sess.exam_state = state
        flag_modified(sess, "exam_state")
        await lease_db.commit()
        return True


async def _evaluation_lease_heartbeat(
    session_id: str,
    owner: str,
    stop: asyncio.Event,
) -> None:
    """Keep a healthy long-running scorer from being mistaken for a stale worker."""
    interval = max(0.1, min(30.0, EVALUATION_LEASE_SECONDS / 3.0))
    while True:
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
            return
        except asyncio.TimeoutError:
            try:
                if not await _renew_evaluation_lease(session_id, owner):
                    return
            except Exception as exc:  # A lost heartbeat leaves the ordinary expiry recovery intact.
                logger.warning(
                    "Evaluation lease heartbeat failed session_id=%s error_type=%s",
                    session_id,
                    type(exc).__name__,
                )
                return


async def _run_evaluation(session_id: str) -> None:
    """Own and heartbeat one evaluation; a live worker cannot be duplicated after lease expiry."""
    claim = await _claim_evaluation_lease(session_id)
    if claim is None:
        return
    owner = claim[0]
    stop_heartbeat = asyncio.Event()
    heartbeat = asyncio.create_task(
        _evaluation_lease_heartbeat(session_id, owner, stop_heartbeat)
    )
    try:
        await _run_claimed_evaluation(session_id, claim)
    finally:
        stop_heartbeat.set()
        await heartbeat


async def _run_claimed_evaluation(
    session_id: str,
    claim: tuple[str, dict, int, int],
) -> None:
    """Fuse the immutable claimed evidence, then owner-fence the atomic DB projection."""
    evaluation_owner, state, student_id, language_id = claim
    async with AsyncSessionLocal() as db:
        try:
            now = datetime.now(timezone.utc)
            # --- Shared: per-turn evidence block + effective-level guess.
            def _block(results: list[dict]) -> str:
                return "\n".join(
                    "<spoken_turn>\n"
                    f"<question>{r.get('question', '')}</question>\n"
                    f"<server_transcript>{r.get('transcription', '')}</server_transcript>\n"
                    f"<audio_duration_seconds>{r.get('audio_duration_seconds', '')}</audio_duration_seconds>\n"
                    "</spoken_turn>"
                    for r in results
                ) or "(none)"

            # --- Speaking: independent 4-criteria rubric over Phase-1 + Phase-2 turns.
            ph1_results = state.get("speaking", {}).get("results", [])
            ph2_results = state.get("interview", {}).get("results", [])
            sp_results = ph1_results + ph2_results
            # "interview" was a deliberate, intentional Phase-2 addition for sessions that have it
            # in their own persisted sections — for those, live_available still means "did the
            # interview actually produce results" (unchanged). For sessions with no "interview"
            # section at all (the new, no-interview design), there is no Phase 2 to be
            # "unavailable" — Phase-1 speaking evidence being complete is what "available" means.
            if "interview" in (state.get("sections") or SECTIONS):
                live_available = bool(ph2_results)
            else:
                live_available = len(ph1_results) >= SPEAKING_TURNS
            sp_evidence = build_verified_speaking_evidence(ph1_results, ph2_results)

            # Speaking Assessment Core (MVP evidence/auditability layer, additive/report-only --
            # see language_speaking_assessment_core_service.py): a read-only lookup of the
            # body_json metadata (review_status, expected_response_seconds) for whichever bank
            # items this session's speaking turns actually used, if any. Never mutates bank rows.
            speaking_bank_item_ids = {int(r["bank_item_id"]) for r in sp_results if r.get("bank_item_id")}
            speaking_bank_item_metadata = await fetch_bank_item_metadata(db, speaking_bank_item_ids)

            guess = await _effective_level(db, student_id=student_id, language_id=language_id)
            # Release the read transaction before any scorer call; no DB connection or row lock is
            # held while external AI work is in flight.
            await db.rollback()

            sp_detected: list = []
            scorer_fallback_used = False
            if sp_results:
                try:
                    sp_grade = await ai_engine.grade_speaking(evidence=sp_evidence, effective_level=guess)
                except Exception as exc:
                    logger.warning(
                        "Placement final speaking scorer unavailable; using fallback session_id=%s error_type=%s",
                        session_id,
                        type(exc).__name__,
                    )
                    sp_grade = _fallback_speaking_grade(sp_results)
                    scorer_fallback_used = True
                speaking_level, speaking_score = sp_grade.level, sp_grade.score
                speaking_breakdown = {
                    "fluency": sp_grade.fluency, "lexical": sp_grade.lexical,
                    "grammar": sp_grade.grammar,
                }
                sp_detected = list(sp_grade.detected_errors)
            else:
                raise RuntimeError("Verified speaking evidence is unavailable")

            speaking_assessment_core = build_speaking_assessment_core(
                results=sp_results,
                grade=sp_grade,
                expected_turns=SPEAKING_TURNS,
                llm_provider=get_settings().LLM_PROVIDER,
                prosody_provider=get_settings().SPEAKING_PROSODY_PROVIDER,
                bank_item_metadata=speaking_bank_item_metadata,
            )

            # --- Reading / Listening: adaptive (staircase) result.
            r_asked = state.get("reading", {}).get("asked", [])
            l_asked = state.get("listening", {}).get("asked", [])
            g_asked = state.get("grammar_vocab", {}).get("asked", [])
            reading_level, reading_pct = _reading_weighted_result(r_asked)
            listening_level, listening_pct = adaptive_result(l_asked)
            grammar_vocab_level, grammar_vocab_pct = adaptive_result(g_asked)
            r_correct, r_total = sum(1 for a in r_asked if a.get("correct")), len(r_asked)
            l_correct, l_total = sum(1 for a in l_asked if a.get("correct")), len(l_asked)
            g_correct, g_total = sum(1 for a in g_asked if a.get("correct")), len(g_asked)
            reading_breakdown = _reading_diagnostic_breakdown(r_asked)

            # --- Writing: AI grade.
            wr = state.get("writing", {})
            writing_tasks = [
                task
                for task in (wr.get("tasks") or [])
                if str(task.get("response") or "").strip()
            ]
            if not writing_tasks and str(wr.get("response") or "").strip():
                writing_tasks = [wr]
            task_weights = [0.35, 0.65] if len(writing_tasks) >= 2 else [1.0]
            writing_task_grades: list[dict] = []
            writing_detected: list = []
            weighted_score = 0.0
            weight_total = 0.0
            criteria_totals = {
                "task_fulfillment": 0.0,
                "communicative_achievement": 0.0,
                "organization": 0.0,
                "grammar": 0.0,
                "vocabulary": 0.0,
                "spelling_punctuation": 0.0,
            }
            for idx, task in enumerate(writing_tasks):
                try:
                    task_grade = await ai_engine.grade_writing(
                        prompt_text=task.get("prompt", ""),
                        answer=task.get("response", ""),
                        effective_level=guess,
                        target_min_words=task.get("min_words"),
                        target_max_words=task.get("max_words"),
                        task_type=task.get("task_type"),
                    )
                except Exception as exc:
                    logger.warning(
                        "Placement final writing scorer unavailable; using fallback session_id=%s task_index=%s error_type=%s",
                        session_id,
                        idx + 1,
                        type(exc).__name__,
                    )
                    task_grade = _fallback_writing_grade(task)
                    scorer_fallback_used = True
                weight = task_weights[idx] if idx < len(task_weights) else task_weights[-1]
                weighted_score += task_grade.score * weight
                weight_total += weight
                task_criteria = {
                    "task_fulfillment": task_grade.task_fulfillment or task_grade.task_achievement,
                    "communicative_achievement": task_grade.communicative_achievement or task_grade.task_achievement,
                    "organization": task_grade.organization or task_grade.coherence,
                    "grammar": task_grade.grammar,
                    "vocabulary": task_grade.vocabulary or task_grade.lexical,
                    "spelling_punctuation": task_grade.spelling_punctuation
                    or min(task_grade.vocabulary or task_grade.lexical, task_grade.grammar),
                }
                for key, value in task_criteria.items():
                    criteria_totals[key] += float(value) * weight
                writing_detected.extend(task_grade.detected_errors)
                writing_task_grades.append(
                    {
                        "task_index": idx + 1,
                        "task_type": task.get("task_type", ""),
                        "route": task.get("route", ""),
                        "level": task_grade.level.value,
                        "score": task_grade.score,
                        "word_count": len(str(task.get("response") or "").split()),
                        "target_min_words": task.get("min_words"),
                        "target_max_words": task.get("max_words"),
                        "feedback": task_grade.feedback,
                    }
                )
            if not writing_task_grades:
                raise RuntimeError("Verified writing evidence is unavailable")
            writing_score = round(weighted_score / weight_total, 1) if weight_total else 0.0
            writing_level = level_from_score10(writing_score)
            route = str((writing_tasks[-1] if writing_tasks else wr).get("route") or "")
            writing_level = _apply_writing_route_cap(writing_level, route)

            overall = overall_level([reading_level, listening_level, writing_level, speaking_level])

            # --- Cross-phase triangulation: do the spoken and written signals agree?
            #     Spoken = speaking interview; written-anchor = reading/listening/writing plus grammar/vocab.
            spoken_rank = cefr_rank(speaking_level)
            written_anchor_levels = [reading_level, listening_level, writing_level]
            if g_asked:
                written_anchor_levels.append(grammar_vocab_level)
            written_rank = cefr_rank(overall_level(written_anchor_levels))
            gap = spoken_rank - written_rank
            if not live_available:
                consistency = "live_phase_unavailable"
                confidence = 0.55
            elif abs(gap) <= 0:
                consistency = "consistent"
                confidence = 0.92
            elif abs(gap) == 1:
                consistency = "consistent"
                confidence = 0.8
            else:
                consistency = "speaking_stronger" if gap > 0 else "writing_stronger"
                confidence = 0.6
            # No acoustic scorer is present. Make that limitation visible and reduce confidence;
            # pronunciation is never inserted as a fabricated numeric criterion.
            confidence = min(confidence * 0.85, 0.78)
            if scorer_fallback_used:
                confidence = min(confidence, 0.55)

            # --- Narrative from all evidence. Pronunciation is deliberately unassessed because
            #     final grading receives verified transcripts, not the raw audio signal.
            grammar_evidence = (
                f"GRAMMAR/VOCAB: {g_correct}/{g_total} correct -> {grammar_vocab_level.value}\n\n"
                if g_asked
                else "GRAMMAR/VOCAB: not measured\n\n"
            )
            evidence = (
                "Weighting: verified speech transcripts support spoken coherence, grammar and "
                "vocabulary; pronunciation is unassessed. Written items anchor grammar and vocabulary.\n\n"
                f"PHASE 1 ΓÇö ROLE-PLAY SPEAKING:\n{_block(ph1_results)}\n\n"
                f"PHASE 2 ΓÇö GUIDED INTERVIEW:\n{_block(ph2_results)}\n\n"
                f"LISTENING: {l_correct}/{l_total} correct -> {listening_level.value}\n"
                f"READING: {r_correct}/{r_total} correct -> {reading_level.value}\n\n"
                f"{grammar_evidence}"
                f"WRITING (level {writing_level.value}, score {writing_score}):\n"
                + "\n\n".join(
                    f"Task {idx + 1}: {task.get('prompt','')}\nAnswer: {task.get('response','')}\n"
                    for idx, task in enumerate(writing_tasks)
                )
                + "\n"
                + "\n".join(
                    f"Task {grade_info['task_index']} feedback: {grade_info['feedback']}"
                    for grade_info in writing_task_grades
                )
                + "\n\n"
                f"Cross-phase consistency: {consistency}."
            )
            narrative = await ai_engine.build_final_narrative(evidence=evidence)
            recommendations = list(narrative.recommendations[:3])
            if scorer_fallback_used:
                recommendations = [
                    "Review this placement result, then retry report evaluation later to refresh detailed rubric feedback.",
                    *recommendations,
                ][:3]

            # --- Backend-computed guidance: strongest/weakest skill + time to next level.
            skill_levels = {
                "reading": reading_level, "listening": listening_level,
                "writing": writing_level, "speaking": speaking_level,
            }
            strongest = max(skill_levels.items(), key=lambda kv: cefr_rank(kv[1]))[0]
            weakest = min(skill_levels.items(), key=lambda kv: cefr_rank(kv[1]))[0]
            writing_breakdown = {
                key: round(value / weight_total, 1) if weight_total else 0.0
                for key, value in criteria_totals.items()
            }
            writing_breakdown["tasks"] = writing_task_grades
            writing_breakdown["weights"] = [0.35, 0.65] if len(writing_task_grades) >= 2 else [1.0]

            student_answer_texts = [
                str(task.get("response") or "")
                for task in writing_tasks
                if str(task.get("response") or "").strip()
            ] + [
                str(r.get("transcription") or "")
                for r in sp_results
                if str(r.get("transcription") or "").strip()
            ]
            detected = [] if scorer_fallback_used else _student_answer_detected_errors(
                writing_detected + sp_detected,
                student_answer_texts,
            )
            speaking_turns = [
                {
                    "question": r.get("question", ""),
                    "transcription": r.get("transcription", ""),
                    "grammar_vocab_feedback": r.get("grammar_vocab_feedback", ""),
                    "pronunciation_feedback": "Unassessed: no acoustic pronunciation scorer was used.",
                    "fluency_note": r.get("fluency_note", ""),
                }
                for r in sp_results
                if r.get("transcription")
            ]
            report = MultiSkillReportSchema(
                overall_level=overall,
                reading_level=reading_level,
                listening_level=listening_level,
                writing_level=writing_level,
                speaking_level=speaking_level,
                reading_score_percent=reading_pct,
                listening_score_percent=listening_pct,
                writing_score=writing_score,
                speaking_score=speaking_score,
                grammar_vocab_level=grammar_vocab_level if g_asked else None,
                grammar_vocab_score_percent=grammar_vocab_pct if g_asked else 0.0,
                summary=narrative.summary,
                strengths=narrative.strengths,
                weaknesses=narrative.weaknesses,
                detected_errors=detected[:8],
                recommended_starting_lesson_topic=narrative.recommended_starting_lesson_topic,
                strongest_skill=strongest,
                weakest_skill=weakest,
                recommendations=recommendations,
                weeks_to_next_level=_weeks_to_next_level(overall),
                writing_breakdown=writing_breakdown,
                reading_breakdown=reading_breakdown,
                speaking_breakdown=speaking_breakdown,
                speaking_turns=speaking_turns,
                confidence=round(confidence, 2),
                cross_phase_consistency=consistency,
                unassessed_components=["speaking.pronunciation"],
                scorer_fallback_used=scorer_fallback_used,
                speaking_assessment=speaking_assessment_core,
            )

            # Reacquire a short lock only after every external scorer has completed. The owner
            # check makes a stale worker harmless if another worker recovered an expired lease.
            await db.rollback()
            sess = (
                await db.execute(
                    select(LanguageExamSession)
                    .where(LanguageExamSession.id == session_id)
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if not sess or sess.status != "evaluating" or sess.is_completed:
                return
            latest_state = copy.deepcopy(sess.exam_state or {})
            latest_evaluation = dict(latest_state.get("evaluation") or {})
            if (
                str(latest_evaluation.get("evaluation_status") or "") != "running"
                or not secrets.compare_digest(
                    str(latest_evaluation.get("evaluation_owner") or ""), evaluation_owner
                )
            ):
                return
            state = latest_state
            now = datetime.now(timezone.utc)
            sess.assessment_report = report.model_dump(mode="json")
            sess.status = "completed"
            sess.is_completed = True
            sess.completed_at = now

            # --- Write authoritative per-skill levels to analytics.
            def _lvl(v: CEFRLevel) -> LanguageLevel:
                try:
                    return LanguageLevel(v.value)
                except ValueError:
                    return LanguageLevel.A1

            analytics = await db.get(
                LanguageAnalytics, {"student_id": sess.student_id, "language_id": sess.language_id}
            )
            if analytics is None:
                analytics = LanguageAnalytics(student_id=sess.student_id, language_id=sess.language_id)
                db.add(analytics)
            # Only persist a level for skills the exam actually measured. A skipped/empty section
            # defaulted to A2 above; claiming a level for an untested skill is misleading. When not
            # measured the column is left unchanged (None on a first exam, prior level on a retake),
            # so the UI shows "ΓÇö" instead of a fabricated A2.
            measured_pairs = [
                ("reading", reading_level, bool(r_asked)),
                ("listening", listening_level, bool(l_asked)),
                ("writing", writing_level, bool((wr.get("response") or "").strip())),
                ("speaking", speaking_level, bool(sp_results)),
            ]
            measured_cefr: list = []
            focus_levels: dict[str, str] = {}
            for skill_key, lvl, was_measured in measured_pairs:
                if was_measured:
                    setattr(analytics, f"{skill_key}_level", _lvl(lvl))
                    measured_cefr.append(lvl)
                    focus_levels[skill_key] = lvl.value
            analytics.overall_level_internal = _lvl(overall_level(measured_cefr) if measured_cefr else overall)
            # Persist the weakest measured skill so the daily plan personalises from day one.
            focus, _strength = primary_focus_and_strength(
                focus_levels
                or {
                    "reading": reading_level.value, "listening": listening_level.value,
                    "writing": writing_level.value, "speaking": speaking_level.value,
                }
            )
            if focus:
                analytics.primary_focus_skill = focus

            # --- Mark placement complete -> unlock the module.
            prof = (
                await db.execute(
                    select(LanguageStudentProfile).where(
                        LanguageStudentProfile.student_id == sess.student_id,
                        LanguageStudentProfile.language_id == sess.language_id,
                    )
                )
            ).scalar_one_or_none()
            if prof is None:
                prof = LanguageStudentProfile(student_id=sess.student_id, language_id=sess.language_id)
                db.add(prof)
            if not prof.placement_completed_at:
                prof.placement_completed_at = now
            prof.last_assessment_date = now
            prof.next_allowed_retake_date = next_allowed_retake_at(now)
            prof.onboarding_step = LanguageOnboardingStep.dashboard

            # Feed the exam's detected errors into Error Intelligence (same bank as conversation),
            # so recurring mistakes surface across BOTH features (best-effort).
            try:
                from app.services.language_error_intelligence_service import log_error

                for e in detected[:8]:
                    await log_error(
                        db, student_id=sess.student_id, language_id=sess.language_id,
                        error_type="grammar",
                        incorrect_form=(e.rule_explanation or e.original_text),
                        corrected_form=e.corrected_text,
                        context_sentence=e.original_text,
                    )
            except Exception:
                logger.warning(
                    "Exam error-intelligence logging failed session_id=%s user_id=%s",
                    session_id,
                    sess.student_id,
                )

            state["evaluation"] = {
                **dict(state.get("evaluation") or {}),
                "evaluation_status": "completed",
                "evaluation_completed_at": now.isoformat(),
                "evaluation_lease_expires_at": None,
            }
            _bump_state_revision(state)
            sess.exam_state = state
            flag_modified(sess, "exam_state")
            await db.commit()
            _cleanup_exam_audio(state)  # generated listening clips are no longer needed
            # Additive: seed the unified Learner Model from this placement (best-effort, never blocks).
            try:
                from app.services.language_learner_model_service import LanguageLearnerModelService

                # Seed ONLY skills the exam actually measured ΓÇö a skipped/empty section defaults to A2
                # above, and seeding that would fabricate "skill strength" for a skill never tested.
                seed_levels: dict[str, str] = {}
                if r_asked:
                    seed_levels["reading"] = reading_level.value
                if l_asked:
                    seed_levels["listening"] = listening_level.value
                if (wr.get("response") or "").strip():
                    seed_levels["writing"] = writing_level.value
                if sp_results:
                    seed_levels["speaking"] = speaking_level.value
                if seed_levels:
                    await LanguageLearnerModelService(db).seed_from_placement(
                        student_id=sess.student_id,
                        language_id=sess.language_id,
                        skill_levels=seed_levels,
                    )
            except Exception:  # pragma: no cover - never let seeding break the exam
                logger.warning(
                    "Learner-model placement seeding failed session_id=%s user_id=%s",
                    session_id,
                    sess.student_id,
                )
        except Exception as exc:  # pragma: no cover - safety net
            logger.error(
                "Exam evaluation failed session_id=%s error_type=%s",
                session_id,
                type(exc).__name__,
            )
            await db.rollback()
            sess = (
                await db.execute(
                    select(LanguageExamSession)
                    .where(LanguageExamSession.id == session_id)
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if sess and sess.status != "completed":
                failed_state = dict(sess.exam_state or {})
                current_evaluation = dict(failed_state.get("evaluation") or {})
                if not secrets.compare_digest(
                    str(current_evaluation.get("evaluation_owner") or ""), evaluation_owner
                ):
                    return
                failed_state["evaluation"] = {
                    **current_evaluation,
                    "evaluation_status": "scorer_unavailable",
                    "evaluation_lease_expires_at": None,
                    "error_code": "scorer_unavailable",
                    "error_message": "The authoritative scorer is temporarily unavailable. Retry evaluation.",
                    "evaluation_failed_at": datetime.now(timezone.utc).isoformat(),
                }
                _bump_state_revision(failed_state)
                sess.exam_state = failed_state
                flag_modified(sess, "exam_state")
                sess.status = "failed"
                await db.commit()


# ---------------------------------------------------------------------------------------
# endpoints
# ---------------------------------------------------------------------------------------

async def _load_session(
    db: AsyncSession,
    session_id: str,
    student: User | int,
    *,
    for_update: bool = False,
) -> LanguageExamSession:
    student_id = int(student if isinstance(student, int) else student.id)
    stmt = select(LanguageExamSession).where(
        LanguageExamSession.id == session_id,
        LanguageExamSession.student_id == student_id,
    )
    if for_update:
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    sess = (await db.execute(stmt)).scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam session not found")
    return sess


def _cleanup_exam_audio(state: dict) -> None:
    """Delete the edge-tts listening clips generated for this attempt (best-effort)."""
    base = Path(get_settings().UPLOAD_DIR)
    items: list[dict] = []
    for slot in (state.get("listening", {}).get("pool") or {}).values():
        # Listening-only dual-slot shape: {"mcq": item_or_none, "gap_fill": item_or_none}.
        # A legacy in-flight session's flat listening item is used as-is.
        if isinstance(slot, dict) and set(slot.keys()) <= {"mcq", "gap_fill"}:
            items.extend(v for v in slot.values() if v)
        elif slot:
            items.append(slot)
    for item in items:
        url = item.get("audio_url") or ""
        if not (url.startswith("/uploads/language_exam_audio/") or url.startswith("/uploads/exam_audio/")):
            continue
        try:
            (base / url[len("/uploads/") :]).unlink(missing_ok=True)
        except OSError:  # pragma: no cover
            pass


_PREP_RETRY_AFTER_S = 150
# Root cause (confirmed from logs): the Supertonic TTS engine is loaded lazily and cached for the
# lifetime of the process (see _tts_engine in language_supertonic_service.py). The very first
# synthesis after a fresh process start can trigger a one-time model download observed to take
# several minutes ("Fetching 26 files... [04:02<...]"); every listening bank row's audio_meta_json
# is empty (confirmed), so a normal run needs up to six sequential per-level TTS calls with no
# cache to fall back on. Each call is now individually bounded by _LISTENING_TTS_TIMEOUT_S (a slow
# item's rung is dropped, existing graceful-degradation policy -- the shared engine load itself is
# never cancelled, see _ensure_engine_loaded's asyncio.shield), so 150s (6 x 25s) comfortably covers
# the worst realistic case for one _prepare_content pass. A too-short value here causes
# _maybe_retrigger_prep to fire again while the first attempt is still legitimately in flight: the
# redundant second _prepare_content both wastes the first attempt's work (discarded at merge time
# as stale, see _merge_prepared_content's content_prep_token check) and burns an extra hit from the
# "placement_generation" rate limit (3 per 300s, keyed per session) for no benefit -- eventually
# exhausting it and landing the section in content_unavailable purely from self-inflicted retries,
# not genuine abuse.


def _maybe_retrigger_prep(sess: LanguageExamSession, language_id: int, background_tasks: BackgroundTasks) -> bool:
    """Self-heal: if the current section's content never got generated (background task died /
    server restarted), re-launch _prepare_content -- but not more often than every
    _PREP_RETRY_AFTER_S seconds (see that constant's comment for why the value matters).

    Clears the stale content_unavailable markers (per-section evidence_status and the top-level
    content_prep_error_code) that a prior failed attempt may have left behind. Without this, a
    freshly retriggered attempt would still read back as content_unavailable to the caller (see
    get_state's `unavailable` check, which also looks at the per-section evidence_status) even
    though a brand new _prepare_content is genuinely running -- silently defeating retry."""
    state = sess.exam_state or {}
    section = _current_section(state)
    if section not in PREPARED_SECTIONS:
        return False
    if state.get(section, {}).get("ready", True):
        return False
    unavailable_retry = (
        state.get("content_prep_status") == "content_unavailable"
        or state.get(section, {}).get("evidence_status") == "content_unavailable"
    )
    last = state.get("content_prep_at")
    now = datetime.now(timezone.utc)
    if last:
        try:
            if (
                not unavailable_retry
                and (now - datetime.fromisoformat(last)).total_seconds() < _PREP_RETRY_AFTER_S
            ):
                return False
        except (ValueError, TypeError):
            pass
    state["content_prep_at"] = now.isoformat()
    state["content_prep_token"] = _new_exam_token()
    state["content_prep_status"] = "preparing"
    state.pop("content_prep_error_code", None)
    session_sections = state.get("sections") or SECTIONS
    for prepared_section in PREPARED_SECTIONS:
        if prepared_section not in session_sections:
            continue
        if not state.get(prepared_section, {}).get("ready"):
            state.setdefault(prepared_section, {})["evidence_status"] = "retry_required"
    sess.exam_state = state
    flag_modified(sess, "exam_state")
    background_tasks.add_task(_prepare_content, sess.id, language_id, state.get("start_level_hint") or "A2")
    return True


def _schedule_evaluation_recovery(
    sess: LanguageExamSession,
    background_tasks: BackgroundTasks,
) -> bool:
    if sess.status != "evaluating" or not _evaluation_should_run(sess.exam_state or {}):
        return False
    background_tasks.add_task(_run_evaluation, sess.id)
    return True


@router.post("/initiate", response_model=ExamStateOut)
async def initiate_exam(
    background_tasks: BackgroundTasks,
    student: User = Depends(require_active_language_subscription()),
    db: AsyncSession = Depends(get_db),
):
    """Resume an open 4-skill exam, or build a fresh one (speaking ready now; the reading/listening/
    writing content is generated fresh in the background while the student does the speaking part)."""
    language = await get_default_language(db)

    active_stmt = (
        select(LanguageExamSession)
        .where(
            LanguageExamSession.student_id == student.id,
            LanguageExamSession.language_id == language.id,
            LanguageExamSession.status.in_(("in_progress", "evaluating")),
            LanguageExamSession.exam_state.isnot(None),
        )
        .order_by(LanguageExamSession.created_at.desc())
        .limit(1)
    )

    # Phase 1: serialize the decision, then release the lock before scenario generation.
    await db.execute(select(User.id).where(User.id == student.id).with_for_update())
    profile = await ensure_language_profile(db, student.id, language.id)
    existing = (await db.execute(active_stmt.with_for_update())).scalar_one_or_none()
    if existing:
        check_or_raise("placement_poll", f"{student.id}:{existing.id}")
        state = copy.deepcopy(existing.exam_state or {})
        protocol_changed = _ensure_state_protocol(state)
        timer_changed = _expire_exam_if_needed(existing, state)
        protocol_changed = protocol_changed or timer_changed
        if protocol_changed:
            existing.exam_state = state
            flag_modified(existing, "exam_state")
        if _expired_incomplete_exam_can_be_replaced(existing, state):
            await db.commit()
            existing = None
        else:
            if existing.status == "in_progress":
                protocol_changed = _maybe_retrigger_prep(existing, language.id, background_tasks) or protocol_changed
            elif existing.status == "evaluating":
                _schedule_evaluation_recovery(existing, background_tasks)
            if protocol_changed:
                state = copy.deepcopy(existing.exam_state or state)
                _bump_state_revision(state)
                existing.exam_state = state
                flag_modified(existing, "exam_state")
            await db.commit()
            return await _build_state_out(db, existing, resumed=True)

    ensure_placement_retake_allowed(profile)
    check_or_raise("placement_start", student.id)
    # Captured before commit: expire_on_commit would otherwise force a lazy reload of these
    # attributes on next access, which crashes (MissingGreenlet) once a slow external await
    # (the AI scenario call below) separates the commit from that access.
    student_id = int(student.id)
    language_id = int(language.id)
    await db.commit()

    # No row lock or database transaction remains open while the external examiner is called.
    level = await _effective_level(db, student_id=student_id, language_id=language_id)
    learner_grade = await _student_grade(db, student_id=student_id)
    await db.rollback()
    # MVP: prefer a curated, MVP-approved speaking_prompt bank item over live scenario/question
    # generation; fall back to the existing AI-generated (or grade-banded) path unchanged if the
    # bank has nothing usable for this level/language.
    recent_speaking_item_ids = await _recent_speaking_exclusion_ids(
        db,
        language_id=language_id,
        student_id=student_id,
    )
    opening_bank_item = await _speaking_bank_prompt(
        db,
        language_id=language_id,
        level_str=level,
        recent_item_ids=recent_speaking_item_ids,
    )
    if opening_bank_item is not None:
        scenario = _speaking_scenario_from_bank_item(opening_bank_item)
    else:
        scenario = await ai_engine.generate_scenario_and_opening(effective_level=level, learner_grade=learner_grade)

    # Phase 2: recheck under the same per-user lock. A concurrent initiate may have won while AI
    # was running, in which case its session is returned and this generated scenario is discarded.
    await db.execute(select(User.id).where(User.id == student_id).with_for_update())
    existing = (await db.execute(active_stmt.with_for_update())).scalar_one_or_none()
    if existing:
        state = copy.deepcopy(existing.exam_state or {})
        changed = _ensure_state_protocol(state)
        changed = _expire_exam_if_needed(existing, state) or changed
        if changed:
            existing.exam_state = state
            flag_modified(existing, "exam_state")
        if _expired_incomplete_exam_can_be_replaced(existing, state):
            await db.commit()
            existing = None
        else:
            if existing.status == "evaluating":
                _schedule_evaluation_recovery(existing, background_tasks)
            await db.commit()
            return await _build_state_out(db, existing, resumed=True)
    profile = await ensure_language_profile(db, student_id, language_id)
    ensure_placement_retake_allowed(profile)

    now = datetime.now(timezone.utc)
    state = {
        "version": 3,
        "state_revision": 1,
        "sections": list(SECTIONS),
        "cursor": 0,
        "start_level_hint": level,
        "learner_grade": learner_grade,
        "exam_duration_seconds": PLACEMENT_EXAM_DURATION_SECONDS,
        "exam_started_at": now.isoformat(),
        "exam_expires_at": (now + timedelta(seconds=PLACEMENT_EXAM_DURATION_SECONDS)).isoformat(),
        "exam_time_expired": False,
        "content_prep_at": now.isoformat(),
        "content_prep_token": _new_exam_token(),
        "content_prep_status": "preparing",
        "speaking": {
            "scenario": {
                "scenario": scenario["scenario"],
                "ai_persona": scenario["ai_persona"],
                "student_role": scenario["student_role"],
                "setting": scenario["setting"],
            },
            "total_turns": SPEAKING_TURNS,
            "turn": 1,
            "pending_question": scenario["opening_question"],
            # Retained so the turn-1 answer can record which bank item it came from (or None for
            # AI-generated/fallback questions), mirroring bank_item_id retention in MCQ sections.
            "pending_bank_item_id": opening_bank_item.get("bank_item_id") if opening_bank_item is not None else None,
            # Retained so the next turn's selection can prefer an unseen subskill/task_type (soft
            # diversity preference) -- never read by scoring.
            "pending_bank_item_subskill": opening_bank_item.get("subskill") if opening_bank_item is not None else None,
            "turn_token": _new_exam_token(),
            "results": [],
            "done": False,
            "evidence_status": "missing_student_response",
        },
        # Filled in by the background _prepare_content task (until then: not ready).
        "listening": {"mode": "adaptive", "pool": {}, "current_level": "", "asked": [], "max_steps": ADAPTIVE_MAX_STEPS, "ready": False, "done": False, "evidence_status": "retry_required"},
        "reading": {"mode": "adaptive", "pool": {}, "current_level": "", "asked": [], "max_steps": READING_ADAPTIVE_MAX_STEPS, "ready": False, "done": False, "evidence_status": "retry_required"},
        "writing": {
            "mode": "adaptive_two_task",
            "task_index": 1,
            "task_total": WRITING_TASK_TOTAL,
            "tasks": [],
            "prompt": "",
            "prompt_token": "",
            "min_words": WRITING_TASK1_MIN_WORDS,
            "max_words": WRITING_TASK1_MAX_WORDS,
            "response": None,
            "ready": False,
            "done": False,
            "evidence_status": "retry_required",
        },
        # No "interview" section for new sessions (product decision: guided interview removed).
        # _ensure_interview_ready/_provisional_from_phase1/interview_opening stay in place as
        # dormant compatibility code for any already-persisted session whose own "sections" list
        # still includes "interview".
        # No "grammar_vocab" section for new sessions either (product decision: dropped from the
        # active exam). _prepare_content/_maybe_retrigger_prep/_merge_prepared_content stay
        # gated on the session's own "sections" list so any already-persisted session that still
        # includes "grammar_vocab" keeps generating and scoring it exactly as before.
        "request_receipts": [],
    }
    sess = LanguageExamSession(
        student_id=student_id, language_id=language_id, current_step=1, max_steps=len(SECTIONS),
        exam_state=state, status="in_progress",
    )
    db.add(sess)
    await db.commit()
    background_tasks.add_task(_prepare_content, sess.id, language_id, level)
    return await _build_state_out(db, sess)


@router.get("/{session_id}/state", response_model=ExamStateOut)
async def get_state(
    session_id: str,
    background_tasks: BackgroundTasks,
    section: str | None = None,
    student: User = Depends(require_active_language_subscription()),
    db: AsyncSession = Depends(get_db),
):
    """section: free section navigation -- render a specific section (e.g. after a tab click)
    instead of the session's internal progress cursor's section. Purely a rendering choice; never
    mutates the cursor or any section's progress (see _build_state_out)."""
    sess = await _load_session(db, session_id, student, for_update=True)
    check_or_raise("placement_poll", f"{student.id}:{session_id}")
    state = copy.deepcopy(sess.exam_state or {})
    changed = _ensure_state_protocol(state)
    changed = _expire_exam_if_needed(sess, state) or changed
    if changed:
        sess.exam_state = state
        flag_modified(sess, "exam_state")
    if sess.status == "in_progress":
        changed = _maybe_retrigger_prep(sess, sess.language_id, background_tasks) or changed
    elif sess.status == "evaluating":
        _schedule_evaluation_recovery(sess, background_tasks)
    if changed:
        state = copy.deepcopy(sess.exam_state or state)
        _bump_state_revision(state)
        sess.exam_state = state
        flag_modified(sess, "exam_state")
    if changed or sess.status in {"in_progress", "evaluating"}:
        await db.commit()
    return await _build_state_out(db, sess, requested_section=section)


@router.post("/{session_id}/abandon")
async def abandon_exam(
    session_id: str,
    student: User = Depends(require_active_language_subscription()),
    db: AsyncSession = Depends(get_db),
):
    """Abandon an unfinished attempt so the student can start a fresh one (escape a stuck state)."""
    sess = await _load_session(db, session_id, student, for_update=True)
    check_or_raise("placement_abandon", f"{student.id}:{session_id}")
    if sess.status == "evaluating":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "evaluation_in_progress", "message": "Evaluation is already in progress."},
        )
    if sess.status in ("in_progress", "failed"):
        abandoned_state = copy.deepcopy(sess.exam_state or {})
        _ensure_state_protocol(abandoned_state)
        abandoned_state["abandoned_at"] = datetime.now(timezone.utc).isoformat()
        _bump_state_revision(abandoned_state)
        sess.exam_state = abandoned_state
        flag_modified(sess, "exam_state")
        sess.status = "abandoned"
        await db.commit()
        _cleanup_exam_audio(abandoned_state)
    return {"ok": True, "status": sess.status}


def _maybe_finalize(sess: LanguageExamSession, state: dict, background_tasks: BackgroundTasks) -> bool:
    """If all sections are done, flip to evaluating and schedule the unified grading."""
    if state.get("exam_time_expired") or _exam_remaining_seconds(state) <= 0:
        return False
    evaluation = dict(state.get("evaluation") or {})
    current_eval_status = str(evaluation.get("evaluation_status") or evaluation.get("status") or "")
    if sess.status == "in_progress" and _current_section(state) is None and current_eval_status not in {"pending", "running", "completed"}:
        _ensure_exam_evidence_complete(state)
        sess.status = "evaluating"
        state["evaluation"] = {
            **evaluation,
            "evaluation_status": "pending",
            "evaluation_started_at": None,
            "evaluation_lease_expires_at": None,
            "evaluation_attempt": int(evaluation.get("evaluation_attempt") or 0),
            "evaluation_owner": None,
        }
        background_tasks.add_task(_run_evaluation, sess.id)
        return True
    return False


async def _read_speaking_audio(file: UploadFile) -> ValidatedAudio:
    return await validate_placement_audio(file)


async def _verified_server_transcription(audio: ValidatedAudio):
    """Transcribe on the server and distinguish service failure from unusable speech."""
    stt = await transcribe_english_audio(
        audio.data,
        suffix=audio.suffix,
        audio_duration_s=audio.duration_seconds,
    )
    transcript = (stt.text or "").strip()
    error_code = str((stt.meta or {}).get("error_code") or "")
    if stt.engine in {"error", "disabled", "none"}:
        logger.warning(
            "Placement STT unavailable engine=%s",
            stt.engine,
        )
        client_error = error_code == "invalid_audio"
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
                if client_error
                else status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail={
                "code": error_code or "stt_unavailable",
                "evidence_status": "retry_required",
                "message": (
                    "The recording could not be decoded. Please record it again."
                    if client_error
                    else "Speech transcription is temporarily unavailable. Please try again."
                ),
            },
        )
    rejection_code = str((stt.meta or {}).get("rejection_code") or "")
    if rejection_code:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": rejection_code,
                "evidence_status": "retry_required",
                "message": "The recording did not contain enough clear English speech. Please record again.",
            },
        )
    if (
        not transcript
        or len(transcript.split()) < 2
        or stt.low_confidence
        or (stt.no_speech_prob is not None and stt.no_speech_prob >= 0.55)
    ):
        logger.warning(
            "Placement speech rejected engine=%s low_confidence=%s",
            stt.engine,
            stt.low_confidence,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "no_speech",
                "evidence_status": "retry_required",
                "message": "We could not hear a clear answer. Please check your microphone and record again.",
            },
        )
    return stt


@router.post("/{session_id}/speaking/live-transcription-session", response_model=LiveTranscriptionSessionOut)
async def create_speaking_live_transcription_session(
    session_id: str,
    student: User = Depends(require_active_language_subscription()),
    db: AsyncSession = Depends(get_db),
):
    """Mint a short-lived OpenAI Realtime ephemeral client secret for Speaking's live transcript
    preview (MVP, display-only). Scoped to transcription only -- never general model access -- and
    never the server's own OPENAI_API_KEY, which stays server-side.

    This is purely a UX convenience: the returned client_secret is used by the frontend to render
    a "Live transcript preview" while recording. It is never sent into grade_speaking, never
    affects final_level/confidence, and is entirely independent of the official post-submit STT
    pipeline that remains the sole grading source of truth. Fails safely (available=False) rather
    than raising whenever the feature is disabled, misconfigured, or the upstream call fails --
    the Speaking flow must continue exactly as before regardless of this endpoint's outcome.
    """
    sess = await _load_session(db, session_id, student, for_update=True)
    check_or_raise("placement_poll", f"{student.id}:{session_id}")
    state = copy.deepcopy(sess.exam_state or {})
    changed = _expire_exam_if_needed(sess, state)
    if changed:
        sess.exam_state = state
        flag_modified(sess, "exam_state")
        await db.commit()
    if state.get("exam_time_expired") or _exam_remaining_seconds(state) <= 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_time_expired_detail(state))
    if sess.status != "in_progress":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Exam is not in progress")
    result = await create_live_transcription_session()
    if result is None:
        return LiveTranscriptionSessionOut(available=False)
    return LiveTranscriptionSessionOut(available=True, **result)


@router.post("/{session_id}/speaking/turn", response_model=ExamStateOut)
async def speaking_turn(
    session_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    duration_seconds: float | None = Form(None, ge=0, le=180),
    request_id: str = Form(..., min_length=8, max_length=100),
    state_revision: int = Form(..., ge=1),
    turn_token: str = Form(..., min_length=16, max_length=200),
    section: str | None = Form(
        None,
        description=(
            "Free section navigation: which speaking-like section (speaking/interview) this turn "
            "answers. Optional, defaults to the session's current cursor section."
        ),
    ),
    student: User = Depends(require_active_language_subscription()),
    db: AsyncSession = Depends(get_db),
):
    """Transcribe once on the server, then merge the result under a short state lock."""
    sess = await _load_session(db, session_id, student)
    student_id = int(student.id)
    session_student_id = int(sess.student_id)
    language_id = int(sess.language_id)
    initial_status = str(sess.status)
    snapshot = copy.deepcopy(sess.exam_state or {})
    _ensure_exam_timer(snapshot)
    if snapshot.get("exam_time_expired") or _exam_remaining_seconds(snapshot) <= 0:
        sess = await _load_session(db, session_id, student_id, for_update=True)
        state = copy.deepcopy(sess.exam_state or {})
        if _expire_exam_if_needed(sess, state):
            sess.exam_state = state
            flag_modified(sess, "exam_state")
            await db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_time_expired_detail(state))
    # Free section navigation: falls back to the cursor's section exactly like before when omitted.
    section = section or _current_section(snapshot)
    spoken_snapshot = snapshot.get(section, {})
    question = str(spoken_snapshot.get("pending_question") or "")
    expected_token = str(spoken_snapshot.get("turn_token") or "")
    turn = int(spoken_snapshot.get("turn") or 1)
    total = int(
        spoken_snapshot.get("total_turns")
        or (INTERVIEW_TURNS if section == "interview" else SPEAKING_TURNS)
    )
    scenario = copy.deepcopy(snapshot.get("speaking", {}).get("scenario", {}))
    guess = await _effective_level(
        db,
        student_id=session_student_id,
        language_id=language_id,
    )
    await db.rollback()

    _ = duration_seconds  # Server-decoded duration is authoritative.
    check_or_raise("placement_audio_turn", f"{student_id}:{session_id}")
    audio = await _read_speaking_audio(file)
    payload_hash = canonical_payload_hash(
        kind="speaking_turn",
        payload={
            "session_id": session_id,
            "state_revision": state_revision,
            "turn_token": turn_token,
            "audio_sha256": audio.sha256,
            "section": section,
        },
    )
    existing_receipt = _request_receipt(
        snapshot,
        kind="speaking_turn",
        request_id=request_id,
        payload_hash=payload_hash,
    )
    if existing_receipt:
        current = await _load_session(db, session_id, student_id)
        current_state = current.exam_state or {}
        requested_section = section if not current_state.get(section, {}).get("done") else None
        return await _build_state_out(db, current, requested_section=requested_section)
    _require_state_revision(snapshot, supplied_revision=state_revision)
    if (
        initial_status != "in_progress"
        or section not in SPEAKING_LIKE
        or section not in snapshot.get("sections", [])
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "stale_exam_state", "current_state_revision": _state_revision(snapshot)},
        )
    _require_current_state(
        snapshot,
        supplied_revision=state_revision,
        supplied_token=turn_token,
        expected_token=expected_token,
    )
    if _audio_hash_already_used(snapshot, audio.sha256):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "duplicate_audio_evidence",
                "message": "Record a new answer for each speaking question.",
            },
        )
    stt = await _verified_server_transcription(audio)
    transcript = (stt.text or "").strip()
    assessment = await ai_engine.assess_speaking(
        transcript=transcript, scenario=scenario, question=question,
        turn=turn, total_turns=total, effective_level=guess, priming=spoken_snapshot.get("priming", ""),
        learner_grade=snapshot.get("learner_grade"),
    )

    # Re-read and validate after STT/AI. No row lock was held during either external call.
    sess = await _load_session(db, session_id, student_id, for_update=True)
    state = copy.deepcopy(sess.exam_state or {})
    if _expire_exam_if_needed(sess, state):
        sess.exam_state = state
        flag_modified(sess, "exam_state")
        await db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_time_expired_detail(state))
    existing_receipt = _request_receipt(
        state,
        kind="speaking_turn",
        request_id=request_id,
        payload_hash=payload_hash,
    )
    if existing_receipt:
        await db.commit()
        requested_section = section if not state.get(section, {}).get("done") else None
        return await _build_state_out(db, sess, requested_section=requested_section)
    # Re-validate the SAME (possibly non-cursor) section is still answerable in the freshly
    # reloaded state -- not whether it still equals the cursor's section, since free section
    # navigation means those can legitimately differ.
    current_spoken = state.get(section, {})
    _require_current_state(
        state,
        supplied_revision=state_revision,
        supplied_token=turn_token,
        expected_token=str(current_spoken.get("turn_token") or ""),
    )
    if (
        sess.status != "in_progress"
        or section not in SPEAKING_LIKE
        or section not in state.get("sections", [])
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "stale_exam_state", "current_state_revision": _state_revision(state)},
        )
    if _audio_hash_already_used(state, audio.sha256):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "duplicate_audio_evidence", "message": "Record a new answer for each question."},
        )

    sp = state[section]
    answered_bank_item_id = sp.get("pending_bank_item_id")
    answered_bank_item_subskill = sp.get("pending_bank_item_subskill")
    if answered_bank_item_id:
        await record_bank_item_answer(db, item_id=int(answered_bank_item_id), correct=False)
    sp.setdefault("results", []).append(
        {
            "question": question,
            "transcription": transcript,
            "grammar_vocab_feedback": assessment.grammar_vocab_feedback,
            "pronunciation_feedback": "",
            "pronunciation_status": "unassessed",
            "fluency_note": assessment.fluency_note,
            "estimated_level": assessment.estimated_level.value,
            "audio_sha256": audio.sha256,
            "audio_duration_seconds": audio.duration_seconds,
            "audio_mime_type": audio.mime_type,
            "stt_engine": stt.engine,
            "stt_model": stt.model,
            # Retained so the next turn's bank selection can exclude it via used_item_ids,
            # mirroring MCQ sections' bank_item_id retention (P1.1) -- scoring never reads this.
            "bank_item_id": int(answered_bank_item_id) if answered_bank_item_id else None,
            # Retained so the next turn's selection can prefer an unseen subskill/task_type (soft
            # diversity preference) -- never read by scoring.
            "bank_item_subskill": str(answered_bank_item_subskill) if answered_bank_item_subskill else None,
        }
    )

    feedback = SpeakingTurnFeedbackOut(
        transcription=transcript,
        grammar_vocab_feedback=assessment.grammar_vocab_feedback,
        pronunciation_feedback="Unassessed: no acoustic pronunciation scorer was used.",
        fluency_note=assessment.fluency_note,
    )

    if turn >= total:
        sp["done"] = True
        sp["pending_question"] = ""
        sp["pending_bank_item_id"] = None
        sp["pending_bank_item_subskill"] = None
        sp["turn_token"] = ""
        sp["evidence_status"] = "completed"
    else:
        sp["turn"] = turn + 1
        # MVP: prefer a curated bank prompt at the live estimated level (a light staircase) over
        # asking Claude to invent the next question; fall back to the existing AI-generated
        # question unchanged if the bank has nothing usable left. Interview (legacy, dormant)
        # keeps its own unmodified behavior -- this only applies to the live "speaking" section.
        next_bank_item = None
        if section == "speaking":
            recent_speaking_item_ids = await _recent_speaking_exclusion_ids(
                db,
                language_id=language_id,
                student_id=session_student_id,
            )
            next_bank_item = await _speaking_bank_prompt(
                db,
                language_id=language_id,
                level_str=assessment.estimated_level.value,
                used_item_ids=_already_used_speaking_bank_item_ids(state, section),
                recent_item_ids=recent_speaking_item_ids,
                used_subskills=_already_used_speaking_subskills(state, section),
            )
        if next_bank_item is not None:
            sp["pending_question"] = _speaking_bank_question_text(next_bank_item)
            sp["pending_bank_item_id"] = next_bank_item.get("bank_item_id")
            sp["pending_bank_item_subskill"] = next_bank_item.get("subskill")
        else:
            sp["pending_question"] = assessment.next_question or "Tell me more about that."
            sp["pending_bank_item_id"] = None
            sp["pending_bank_item_subskill"] = None
        sp["turn_token"] = _new_exam_token()
        sp["evidence_status"] = "missing_student_response"

    _advance_if_section_done(state)
    _maybe_finalize(sess, state, background_tasks)
    result_revision = _bump_state_revision(state)
    _record_request(
        state,
        kind="speaking_turn",
        request_id=request_id,
        payload_hash=payload_hash,
        request_revision=state_revision,
        token=turn_token,
        result_reference=f"{section}:{turn}:revision:{result_revision}",
    )
    sess.exam_state = state
    flag_modified(sess, "exam_state")
    await db.commit()
    requested_section = section if not state.get(section, {}).get("done") else None
    return await _build_state_out(db, sess, last_feedback=feedback, requested_section=requested_section)


@router.post("/{session_id}/answer", response_model=ExamStateOut)
async def answer_mcq(
    session_id: str,
    body: McqAnswerIn,
    background_tasks: BackgroundTasks,
    student: User = Depends(require_active_language_subscription()),
    db: AsyncSession = Depends(get_db),
):
    """Record an MCQ answer and advance to the next item/section."""
    sess = await _load_session(db, session_id, student, for_update=True)
    student_id = int(student.id)
    state = copy.deepcopy(sess.exam_state or {})
    if _expire_exam_if_needed(sess, state):
        sess.exam_state = state
        flag_modified(sess, "exam_state")
        await db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_time_expired_detail(state))
    payload_hash = canonical_payload_hash(
        kind="mcq_answer",
        payload={
            "session_id": session_id,
            "state_revision": body.state_revision,
            "question_token": body.question_token,
            "choice_index": body.choice_index,
            "answer_text": body.answer_text,
            "choice_indices": body.choice_indices,
            "answer_texts": body.answer_texts,
            "subquestion_answers": body.subquestion_answers,
            "section": body.section,
        },
    )
    if _request_receipt(
        state,
        kind="mcq_answer",
        request_id=body.request_id,
        payload_hash=payload_hash,
    ):
        await db.commit()
        return await _build_state_out(db, sess, requested_section=body.section)
    _require_state_revision(state, supplied_revision=body.state_revision)
    # Free section navigation: the student may be answering a section other than the session's
    # internal progress cursor's section (e.g. jumped here via a tab click). Falls back to the
    # cursor's section, matching the prior (strictly sequential) behavior exactly when omitted.
    section = body.section or _current_section(state)
    if (
        sess.status != "in_progress"
        or section not in MCQ_SECTIONS
        or section not in state.get("sections", [])
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Not in an MCQ section")
    check_or_raise("placement_answer", f"{student_id}:{session_id}")

    sec = state[section]
    cur = sec.get("current_level")
    item = _resolve_current_exam_item(sec, cur, dual_slot=(section == "listening"))
    if sec.get("done") or not item:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No item awaiting an answer")
    _require_current_state(
        state,
        supplied_revision=body.state_revision,
        supplied_token=body.question_token,
        expected_token=str(item.get("question_token") or ""),
    )

    # question_type is resolved from the server-side item only -- never trusted/declared by the
    # client (McqAnswerIn has no question_type field). A missing/falsy value is an older
    # in-progress state blob or AI-fallback item predating this field; both were always MCQ.
    qtype = item.get("question_type") or "mcq"
    asked_entry: dict = {"level": cur}
    is_mcq_bundle = qtype == "mcq" and isinstance(item.get("subquestions"), list)
    is_gap_fill_bundle = qtype == "gap_fill" and isinstance(item.get("blanks"), list)

    if is_mcq_bundle:
        subquestions = item["subquestions"]
        sub_correct: list[bool] = []
        has_non_choice_answers = any(_reading_subquestion_response_type(sq) != "mcq" for sq in subquestions)
        if has_non_choice_answers:
            if (
                body.subquestion_answers is None
                or body.choice_index is not None
                or body.answer_text is not None
                or body.choice_indices is not None
                or body.answer_texts is not None
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This question requires subquestion_answers only.",
                )
            if len(body.subquestion_answers) != len(subquestions):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="subquestion_answers length must match the number of subquestions",
                )
            normalized_answers: list[int | str] = []
            for idx, (answer, sq) in enumerate(zip(body.subquestion_answers, subquestions)):
                response_type = _reading_subquestion_response_type(sq)
                if response_type == "mcq":
                    if not isinstance(answer, int) or isinstance(answer, bool):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"subquestion_answers[{idx}] must be an integer choice index",
                        )
                    options = sq.get("options") or []
                    if answer >= len(options):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"subquestion_answers[{idx}] out of range",
                        )
                    normalized_answers.append(answer)
                    sub_correct.append(answer == sq.get("correct_index"))
                elif response_type in _READING_TEXT_RESPONSE_TYPES:
                    if not isinstance(answer, str):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"subquestion_answers[{idx}] must be text",
                        )
                    max_words = int(sq.get("max_words") or 12)
                    if len(answer.split()) > max_words:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"Your answer for question {idx + 1} must be no more than {max_words} words.",
                        )
                    normalized_answer = normalize_gap_fill_text(answer, case_sensitive=bool(sq.get("case_sensitive", False)))
                    normalized_accepted = {
                        normalize_gap_fill_text(a, case_sensitive=bool(sq.get("case_sensitive", False)))
                        for a in (sq.get("accepted_answers") or [])
                    }
                    normalized_answers.append(normalized_answer)
                    sub_correct.append(normalized_answer in normalized_accepted)
                elif response_type in _READING_MATCHING_RESPONSE_TYPES:
                    if not isinstance(answer, list):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"subquestion_answers[{idx}] must be a list of match indices",
                        )
                    match_options = sq.get("match_options") or []
                    correct_indices = sq.get("correct_indices") or []
                    if len(answer) != len(correct_indices):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"subquestion_answers[{idx}] length must match the number of matching items",
                        )
                    if any(not isinstance(i, int) or isinstance(i, bool) or not (0 <= i < len(match_options)) for i in answer):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"subquestion_answers[{idx}] contains an out-of-range match index",
                        )
                    normalized_answers.append(list(answer))
                    sub_correct.append(list(answer) == list(correct_indices))
                else:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail={
                            "code": "content_unavailable",
                            "message": "This question is temporarily unavailable. Please retry.",
                        },
                    )
            asked_entry["subquestion_answers"] = normalized_answers
        else:
            if body.choice_indices is None or body.choice_index is not None or body.answer_text is not None or body.answer_texts is not None or body.subquestion_answers is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This question requires choice_indices only.",
                )
            if len(body.choice_indices) != len(subquestions):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="choice_indices length must match the number of subquestions",
                )
            for idx, (choice, sq) in enumerate(zip(body.choice_indices, subquestions)):
                options = sq.get("options") or []
                if choice >= len(options):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"choice_indices[{idx}] out of range",
                    )
                sub_correct.append(choice == sq.get("correct_index"))
            asked_entry["chosen_indices"] = list(body.choice_indices)
        correct = _majority_correct(sub_correct)
        asked_entry["sub_correct"] = sub_correct
        asked_entry["question_type"] = "mcq"
        asked_entry["question_count"] = len(subquestions)
        if section == "reading":
            subskills = [
                str(sq.get("subskill") or sq.get("reading_subskill") or item.get("subskill") or "").strip()
                for sq in subquestions
            ]
            if any(subskills):
                asked_entry["subskills"] = subskills
    elif qtype == "mcq":
        if body.choice_index is None or body.answer_text is not None or body.subquestion_answers is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This question requires choice_index only.",
            )
        if body.choice_index >= len(item.get("options", [])):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="choice_index out of range"
            )
        correct = body.choice_index == item.get("correct_index")
        # Exact pre-existing shape -- an existing test asserts equality on this dict, so no
        # question_type key is added here; only gap_fill entries carry the extra evidence fields.
        asked_entry["chosen_index"] = body.choice_index
    elif is_gap_fill_bundle:
        blanks = item["blanks"]
        if body.answer_texts is None or body.answer_text is not None or body.choice_index is not None or body.choice_indices is not None or body.subquestion_answers is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This question requires answer_texts only.",
            )
        if len(body.answer_texts) != len(blanks):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="answer_texts length must match the number of blanks",
            )
        for idx, blank in enumerate(blanks):
            malformed_field = gap_fill_content_error(blank)
            if malformed_field:
                logger.warning(
                    "Gap fill bundle blank content invalid session_id=%s bank_item_id=%s level=%s blank=%s field=%s",
                    session_id, item.get("bank_item_id"), cur, idx, malformed_field,
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "code": "content_unavailable",
                        "message": "This question is temporarily unavailable. Please retry.",
                    },
                )
        for idx, (answer_text, blank) in enumerate(zip(body.answer_texts, blanks)):
            max_words = blank["max_words"]
            if len(answer_text.split()) > max_words:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Your answer for blank {idx + 1} must be no more than {max_words} words.",
                )
        sub_correct = []
        normalized_answers = []
        for answer_text, blank in zip(body.answer_texts, blanks):
            case_sensitive = bool(blank.get("case_sensitive", False))
            normalized_answer = normalize_gap_fill_text(answer_text, case_sensitive=case_sensitive)
            normalized_accepted = {
                normalize_gap_fill_text(a, case_sensitive=case_sensitive)
                for a in blank["accepted_answers"]
            }
            normalized_answers.append(normalized_answer)
            sub_correct.append(normalized_answer in normalized_accepted)
        correct = _majority_correct(sub_correct)
        asked_entry["answer_texts"] = normalized_answers
        asked_entry["sub_correct"] = sub_correct
        asked_entry["question_type"] = "gap_fill"
    elif qtype == "gap_fill":
        if body.answer_text is None or body.choice_index is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This question requires answer_text only.",
            )
        malformed_field = gap_fill_content_error(item)
        if malformed_field:
            logger.warning(
                "Gap fill item content invalid session_id=%s bank_item_id=%s level=%s field=%s",
                session_id, item.get("bank_item_id"), cur, malformed_field,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "content_unavailable",
                    "message": "This question is temporarily unavailable. Please retry.",
                },
            )
        max_words = item["max_words"]
        if len(body.answer_text.split()) > max_words:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Your answer must be no more than {max_words} words.",
            )
        case_sensitive = bool(item.get("case_sensitive", False))
        normalized_answer = normalize_gap_fill_text(body.answer_text, case_sensitive=case_sensitive)
        normalized_accepted = {
            normalize_gap_fill_text(a, case_sensitive=case_sensitive)
            for a in item["accepted_answers"]
        }
        correct = normalized_answer in normalized_accepted
        asked_entry["chosen_index"] = None
        asked_entry["question_type"] = "gap_fill"
        # Never exposed publicly -- sec["asked"] is not part of any public response schema
        # (confirmed: McqPromptOut/ExamStateOut/MultiSkillReportSchema never read it for
        # MCQ_SECTIONS; unlike Speaking, there is no listening/reading/grammar_vocab per-turn
        # public detail).
        asked_entry["answer_text"] = normalized_answer
    else:
        logger.warning(
            "Unknown question_type rejected session_id=%s bank_item_id=%s level=%s question_type=%s",
            session_id, item.get("bank_item_id"), cur, qtype,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "content_unavailable",
                "message": "This question is temporarily unavailable. Please retry.",
            },
        )

    if section == "reading":
        metrics = (item.get("body") or {}).get("placement_metrics") or {}
        subskill = str(item.get("subskill") or metrics.get("subskill") or "").strip()
        if subskill:
            asked_entry["subskill"] = subskill
        if metrics:
            try:
                asked_entry["word_count"] = int(metrics.get("word_count") or 0)
            except (TypeError, ValueError):
                asked_entry["word_count"] = 0
            try:
                asked_entry["avg_sentence_words"] = float(metrics.get("avg_sentence_words") or 0.0)
            except (TypeError, ValueError):
                asked_entry["avg_sentence_words"] = 0.0

    bank_item_id = item.get("bank_item_id")
    if bank_item_id:
        await record_bank_item_answer(db, item_id=int(bank_item_id), correct=correct)
    asked_entry["correct"] = correct
    # Retained so a later _prepare_content run can exclude it via used_item_ids (P1.1) —
    # scoring/adaptive logic never reads this key.
    asked_entry["bank_item_id"] = int(bank_item_id) if bank_item_id else None
    sec.setdefault("asked", []).append(asked_entry)
    asked_levels = {a["level"] for a in sec["asked"]}

    if sec.pop("_awaiting_boundary_answer", False):
        # P1.3: the one allotted boundary-confirmation question has now been answered — the
        # section always finishes here (regardless of correctness), so it can never ask a second.
        sec["done"] = True
        sec["evidence_status"] = "completed"
    else:
        # Adaptive staircase: harder if correct, easier if wrong; stop when converged / out of steps.
        nxt = adaptive_next_level(
            current=cur, correct=correct, asked_levels=asked_levels,
            pool_levels=set(sec.get("pool", {}).keys()),
            asked_count=len(sec["asked"]), max_steps=sec.get("max_steps", ADAPTIVE_MAX_STEPS),
        )
        if nxt is None:
            continuation = _mcq_continuation_level(
                pool_levels=set(sec.get("pool", {}).keys()),
                asked_levels=asked_levels,
                asked_count=len(sec["asked"]),
                current=cur,
                min_evidence_items=_min_evidence_for_section(section),
            )
            boundary_item = None
            if continuation is None and not sec.get("boundary_asked"):
                boundary = _boundary_situation(sec["asked"])
                if boundary is not None:
                    sec["boundary_asked"] = True
                    low, high = boundary
                    boundary_item = await _boundary_confirmation_item(
                        db,
                        language_id=int(sess.language_id),
                        skill=section,
                        low=low,
                        high=high,
                        used_item_ids=_already_used_bank_item_ids(state, section),
                    )
            if continuation is not None:
                sec["current_level"] = continuation
                sec["evidence_status"] = "missing_student_response"
            elif boundary_item is not None:
                # P1.3: inject the boundary item under its own reported level so the existing
                # pool/current_level/asked machinery (and adaptive_result's CEFR parsing) needs no
                # changes; _awaiting_boundary_answer ensures this section finishes right after.
                boundary_item["question_token"] = _new_exam_token()
                level_key = boundary_item.get("level") or cur
                sec.setdefault("pool", {})[level_key] = boundary_item
                sec["current_level"] = level_key
                sec["_awaiting_boundary_answer"] = True
                sec["evidence_status"] = "missing_student_response"
            else:
                sec["done"] = True
                sec["evidence_status"] = "completed"
        else:
            sec["current_level"] = nxt
            sec["evidence_status"] = "missing_student_response"

    _advance_if_section_done(state)
    _maybe_finalize(sess, state, background_tasks)
    result_revision = _bump_state_revision(state)
    _record_request(
        state,
        kind="mcq_answer",
        request_id=body.request_id,
        payload_hash=payload_hash,
        request_revision=body.state_revision,
        token=body.question_token,
        result_reference=f"{section}:{cur}:revision:{result_revision}",
    )
    sess.exam_state = state
    flag_modified(sess, "exam_state")
    await db.commit()
    requested_section = section if not state.get(section, {}).get("done") else None
    return await _build_state_out(db, sess, requested_section=requested_section)


@router.post("/{session_id}/writing")
async def submit_writing(
    session_id: str,
    body: WritingAnswerIn,
    background_tasks: BackgroundTasks,
    student: User = Depends(require_active_language_subscription()),
    db: AsyncSession = Depends(get_db),
):
    """Record the writing answer and flow into the Phase-2 spoken interview (or finalize)."""
    sess = await _load_session(db, session_id, student)
    session_language_id = int(sess.language_id)
    student_id = int(student.id)
    snapshot = copy.deepcopy(sess.exam_state or {})
    _ensure_exam_timer(snapshot)
    if snapshot.get("exam_time_expired") or _exam_remaining_seconds(snapshot) <= 0:
        sess = await _load_session(db, session_id, student_id, for_update=True)
        state = copy.deepcopy(sess.exam_state or {})
        if _expire_exam_if_needed(sess, state):
            sess.exam_state = state
            flag_modified(sess, "exam_state")
            await db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_time_expired_detail(state))
    payload_hash = canonical_payload_hash(
        kind="writing_answer",
        payload={
            "session_id": session_id,
            "state_revision": body.state_revision,
            "prompt_token": body.prompt_token,
            "text_sha256": hashlib.sha256(
                _normalise_writing_text(body.text).encode("utf-8")
            ).hexdigest(),
        },
    )
    if _request_receipt(
        snapshot,
        kind="writing_answer",
        request_id=body.request_id,
        payload_hash=payload_hash,
    ):
        requested_section = "writing" if not snapshot.get("writing", {}).get("done") else None
        return await _build_state_out(db, sess, requested_section=requested_section)
    _require_state_revision(snapshot, supplied_revision=body.state_revision)
    # Free section navigation: writing is answerable whenever it's a real member of this
    # session's sections, regardless of the internal progress cursor's position. The explicit
    # done-check is required here (unlike MCQ sections/speaking, which already fail closed on a
    # spent question_token/turn_token) since a completed writing prompt_token is never cleared --
    # without this, a student could jump back and silently overwrite an already-scored response.
    if (
        sess.status != "in_progress"
        or "writing" not in snapshot.get("sections", [])
        or snapshot.get("writing", {}).get("done")
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Not in the writing section")
    _require_current_state(
        snapshot,
        supplied_revision=body.state_revision,
        supplied_token=body.prompt_token,
        expected_token=str(snapshot.get("writing", {}).get("prompt_token") or ""),
    )
    check_or_raise("placement_answer", f"{student.id}:{session_id}")

    min_words = snapshot.get("writing", {}).get("min_words", WRITING_MIN_WORDS)
    if len(body.text.split()) < min_words:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Your answer must be at least {min_words} words.",
        )

    writing_snapshot = snapshot.get("writing", {})
    task_index = max(1, int(writing_snapshot.get("task_index") or 1))
    task_total = max(1, int(writing_snapshot.get("task_total") or 1))
    is_intermediate_writing_task = task_index < task_total
    preliminary_grade: dict | None = None
    next_writing_prompt: dict | None = None
    prospective = copy.deepcopy(snapshot)

    await db.rollback()
    if is_intermediate_writing_task:
        try:
            grade = await ai_engine.grade_writing(
                prompt_text=writing_snapshot.get("prompt", ""),
                answer=body.text,
                effective_level=await _effective_level(db, student_id=student_id, language_id=session_language_id),
                target_min_words=writing_snapshot.get("min_words"),
                target_max_words=writing_snapshot.get("max_words"),
                task_type=writing_snapshot.get("task_type"),
            )
            preliminary_grade = _writing_grade_to_dict(grade)
        except Exception as exc:
            logger.warning(
                "Preliminary writing routing used fallback session_id=%s error_type=%s",
                session_id,
                type(exc).__name__,
            )
            preliminary_grade = _fallback_writing_task1_grade(body.text)
        route = str(preliminary_grade.get("route") or "B1_B2")
        next_writing_prompt = await _writing_task2_prompt(
            db,
            language_id=session_language_id,
            route=route,
            used_item_ids={
                int(task.get("bank_item_id"))
                for task in (writing_snapshot.get("tasks") or [])
                if task.get("bank_item_id")
            },
        )
        await db.rollback()
    else:
        # Build the interview opening from a prospective snapshot outside any lock/transaction.
        prospective["writing"]["response"] = body.text
        prospective["writing"]["done"] = True
        prospective["writing"]["evidence_status"] = "completed"
        _advance_if_section_done(prospective)
        try:
            await _ensure_interview_ready(prospective)
        except Exception as exc:
            logger.warning(
                "Placement interview preparation failed session_id=%s error_type=%s",
                session_id,
                type(exc).__name__,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "content_unavailable",
                    "message": "The interview prompt is temporarily unavailable. Please retry.",
                },
            ) from None

    # Merge under a fresh short lock and reject any state that moved while AI was running.
    sess = await _load_session(db, session_id, student_id, for_update=True)
    state = copy.deepcopy(sess.exam_state or {})
    if _expire_exam_if_needed(sess, state):
        sess.exam_state = state
        flag_modified(sess, "exam_state")
        await db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_time_expired_detail(state))
    if _request_receipt(
        state,
        kind="writing_answer",
        request_id=body.request_id,
        payload_hash=payload_hash,
    ):
        await db.commit()
        requested_section = "writing" if not state.get("writing", {}).get("done") else None
        return await _build_state_out(db, sess, requested_section=requested_section)
    if (
        sess.status != "in_progress"
        or "writing" not in state.get("sections", [])
        or state.get("writing", {}).get("done")
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "stale_exam_state", "current_state_revision": _state_revision(state)},
        )
    _require_current_state(
        state,
        supplied_revision=body.state_revision,
        supplied_token=body.prompt_token,
        expected_token=str(state.get("writing", {}).get("prompt_token") or ""),
    )
    writing_state = state["writing"]
    task_index = max(1, int(writing_state.get("task_index") or 1))
    task_total = max(1, int(writing_state.get("task_total") or 1))
    tasks = list(writing_state.get("tasks") or [])
    current_task = {
        "prompt": writing_state.get("prompt", ""),
        "min_words": writing_state.get("min_words", WRITING_MIN_WORDS),
        "max_words": writing_state.get("max_words"),
        "task_type": writing_state.get("task_type", ""),
        "student_instructions": writing_state.get("student_instructions", ""),
        "rubric_focus": list(writing_state.get("rubric_focus") or []),
        "expected_language_features": list(writing_state.get("expected_language_features") or []),
        "bank_item_id": writing_state.get("bank_item_id"),
        "source": writing_state.get("source", ""),
        "route": writing_state.get("route", "anchor"),
        "response": body.text,
        "word_count": len(body.text.split()),
    }
    if preliminary_grade:
        current_task["preliminary_grade"] = preliminary_grade
    task_slot = task_index - 1
    if task_slot < len(tasks):
        tasks[task_slot] = {**tasks[task_slot], **current_task}
    else:
        tasks.append(current_task)

    finalizing = False
    if task_index < task_total and next_writing_prompt:
        next_task = dict(next_writing_prompt)
        tasks.append(next_task)
        writing_state.update(
            {
                "tasks": tasks,
                "task_index": task_index + 1,
                "task_total": task_total,
                "prompt": str(next_task.get("prompt") or ""),
                "prompt_token": _new_exam_token(),
                "min_words": int(next_task.get("min_words") or WRITING_MIN_WORDS),
                "max_words": next_task.get("max_words"),
                "task_type": str(next_task.get("task_type") or ""),
                "student_instructions": str(next_task.get("student_instructions") or ""),
                "rubric_focus": list(next_task.get("rubric_focus") or []),
                "expected_language_features": list(next_task.get("expected_language_features") or []),
                "bank_item_id": next_task.get("bank_item_id"),
                "source": str(next_task.get("source") or ""),
                "route": str(next_task.get("route") or ""),
                "response": None,
                "done": False,
                "evidence_status": "missing_student_response",
            }
        )
    else:
        writing_state["tasks"] = tasks
        writing_state["response"] = "\n\n".join(
            str(task.get("response") or "").strip() for task in tasks if str(task.get("response") or "").strip()
        )
        writing_state["done"] = True
        writing_state["evidence_status"] = "completed"
        _advance_if_section_done(state)
        if _current_section(state) == "interview":
            state["interview"] = copy.deepcopy(prospective["interview"])
        finalizing = _maybe_finalize(sess, state, background_tasks)
    result_revision = _bump_state_revision(state)
    _record_request(
        state,
        kind="writing_answer",
        request_id=body.request_id,
        payload_hash=payload_hash,
        request_revision=body.state_revision,
        token=body.prompt_token,
        result_reference=f"writing:revision:{result_revision}",
    )
    sess.exam_state = state
    flag_modified(sess, "exam_state")
    await db.commit()
    if finalizing:
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=ExamProcessingOut(
                session_id=sess.id,
                message="Analyzing every skill and generating your placement report...",
            ).model_dump(),
        )
    requested_section = "writing" if not state.get("writing", {}).get("done") else None
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=(await _build_state_out(db, sess, requested_section=requested_section)).model_dump(),
    )


@router.post(
    "/{session_id}/evaluation/retry",
    response_model=ExamProcessingOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_exam_evaluation(
    session_id: str,
    background_tasks: BackgroundTasks,
    student: User = Depends(require_active_language_subscription()),
    db: AsyncSession = Depends(get_db),
):
    """Retry a failed authoritative evaluation without recollecting or duplicating evidence."""
    sess = await _load_session(db, session_id, student, for_update=True)
    check_or_raise("placement_evaluation_request", f"{student.id}:{session_id}")
    state = copy.deepcopy(sess.exam_state or {})
    if sess.status == "evaluating":
        evaluation = dict(state.get("evaluation") or {})
        evaluation_status = str(
            evaluation.get("evaluation_status") or evaluation.get("status") or "pending"
        )
        # A committed pending lease already represents a queued evaluation.  Treat a concurrent
        # retry as the same operation instead of bumping the revision and scheduling a duplicate.
        if evaluation_status == "pending" or (
            evaluation_status == "running" and not evaluation_lease_expired(state)
        ):
            await db.commit()
            return ExamProcessingOut(
                session_id=sess.id,
                message="Placement evaluation is already in progress.",
            )
        if evaluation_status != "running":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "evaluation_retry_not_allowed",
                    "message": "This evaluation cannot be retried from its current state.",
                },
            )
        # The former worker lost its lease. Clear ownership so exactly one new worker can claim it.
        evaluation.update(
            {
                "evaluation_status": "pending",
                "evaluation_owner": None,
                "evaluation_lease_expires_at": None,
                "retry_requested_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        state["evaluation"] = evaluation
        _bump_state_revision(state)
        sess.exam_state = state
        flag_modified(sess, "exam_state")
        await db.commit()
        background_tasks.add_task(_run_evaluation, sess.id)
        return ExamProcessingOut(
            session_id=sess.id,
            message="A stale placement evaluation has been queued again.",
        )
    if sess.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "evaluation_retry_not_allowed", "message": "This evaluation cannot be retried."},
        )
    _ensure_exam_evidence_complete(state)
    state["evaluation"] = {
        **dict(state.get("evaluation") or {}),
        "evaluation_status": "pending",
        "evaluation_owner": None,
        "evaluation_lease_expires_at": None,
        "retry_requested_at": datetime.now(timezone.utc).isoformat(),
    }
    _bump_state_revision(state)
    sess.exam_state = state
    flag_modified(sess, "exam_state")
    sess.status = "evaluating"
    await db.commit()
    background_tasks.add_task(_run_evaluation, sess.id)
    return ExamProcessingOut(
        session_id=sess.id,
        message="Placement evaluation has been queued again.",
    )


@router.get("/{session_id}/report", response_model=ExamReportOut)
async def get_exam_report(
    session_id: str,
    student: User = Depends(require_active_language_subscription()),
    db: AsyncSession = Depends(get_db),
):
    """Poll for the final per-skill report (frontend shows a loader until status == completed)."""
    sess = await _load_session(db, session_id, student)
    check_or_raise("placement_poll", f"{student.id}:{session_id}")
    report = None
    if sess.assessment_report:
        try:
            report = MultiSkillReportSchema.model_validate(sess.assessment_report)
        except Exception:
            report = None
    evaluation = (sess.exam_state or {}).get("evaluation") or {}
    error_code = str(evaluation.get("error_code") or "") or None
    error_message = str(evaluation.get("error_message") or "")
    if not error_message and error_code:
        error_message = "Placement evaluation failed. You can retry it."
    return ExamReportOut(
        session_id=sess.id, status=sess.status, is_completed=sess.is_completed,
        report=report, completed_at=sess.completed_at,
        error_code=error_code,
        error_message=error_message or None,
    )
