"""Vocabulary flashcards — review and progress."""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.language.content import LanguageContentItem
from app.models.language.engagement import LanguageActivityLog
from app.models.language.enums import LanguageLevel, LanguageSkill, LanguageVocabularyStatus
from app.models.language.progress import LanguageVocabularyProgress
from app.models.language.vocabulary_ai_usage import LanguageVocabularyAiDailyUsage
from app.schemas.language_learning import (
    VocabularyAiGenerateOut,
    VocabularyAiWordOut,
    VocabularyChallengeOut,
    WordAnalysisOut,
)
from app.services.ai_service import generate_llm_json
from app.services.language_analytics_service import refresh_language_analytics
from app.services.language_cache import TTLCache
from app.services.language_conversation_prompts import level_calibration_line

# Word analyses are stable and the LLM call is slow — cache aggressively (repeat lookups instant).
_WORD_CACHE = TTLCache()
_WORD_TTL = 7 * 24 * 3600  # 7 days
from app.services.language_content_service import get_content_item, list_content_items, normalize_word
from app.services.language_engagement_service import record_activity
from app.services.language_learner_events import record_challenge_results, record_vocabulary_review
from app.services.language_subscription_service import get_default_language
from app.services.language_vocabulary_sr_service import compute_sm2
from app.services.language_vocabulary_word_bank_service import serve_daily_words

logger = logging.getLogger(__name__)

CONTENT_TYPE = "vocabulary"

# A word is flagged "difficult" once it's been failed (SM-2 quality < 3) this many times.
DIFFICULT_FAIL_THRESHOLD = 3

# A "difficult" word is cleared after this many consecutive Good/Easy (quality >= 4) grades.
# Hard (quality == 3) is still a pass but breaks the streak without re-triggering fail_count.
CONSECUTIVE_GOOD_TO_CLEAR_DIFFICULT = 3

# Daily goal shown on the "words reviewed today" tracker.
DAILY_REVIEW_GOAL = 10

# AI-generated vocabulary batches are capped per student per day.
AI_GENERATION_DAILY_LIMIT = 10

_WORD_ANALYSIS_SYSTEM = (
    "You are an expert English vocabulary coach for an English-learning platform whose students are "
    "Syrian secondary-school learners. Explain words clearly at the requested CEFR level, in ENGLISH "
    "ONLY (never Arabic). Return ONLY valid JSON — no markdown, no code fences."
)


def _parse_json_object(raw: str) -> dict | None:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip())
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1:
        return None
    try:
        data = json.loads(text[s : e + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


async def say_word(word: str) -> dict:
    """Synthesize the spoken word (edge-tts, no quota) so the learner can HEAR it. {audio_url, available}."""
    from app.services.language_tts_service import synthesize_exam_audio

    url = await synthesize_exam_audio((word or "").strip()[:80])
    return {"audio_url": url, "available": bool(url)}


async def assess_word_pronunciation(
    db: AsyncSession, *, student_id: int, language_id: int, word: str, data: bytes, suffix: str = ".webm"
) -> dict:
    """Grade the learner SAYING a word: did they say the right word + how clear, with a fix tip.

    Reuses assess_pronunciation (audio model) and persists a pronunciation-history row (Phase 6)."""
    from app.services.language_pronunciation_service import (
        assess_pronunciation,
        store_pronunciation_score,
        word_similarity,
    )

    word = (word or "").strip()
    result = await assess_pronunciation(data, suffix=suffix, expected_text=word)
    if not result:
        return {
            "available": False, "overall_score": 0, "said_target": False, "transcript": "",
            "tip": "The pronunciation check is unavailable right now — please try again.", "issue": "", "target": word,
        }

    transcript = (result.get("transcript") or "").strip()
    said_target = word_similarity(transcript, word) >= 60
    issue = ""
    for w in result.get("words") or []:
        if str(w.get("word", "")).lower().strip(".,!?;:") == word.lower():
            issue = w.get("issue") or ""
            break

    # Persist to pronunciation history/trends (source=vocabulary), best-effort.
    try:
        await store_pronunciation_score(
            db, student_id=student_id, language_id=language_id, result=result, source="vocabulary"
        )
    except Exception:
        pass

    return {
        "available": True,
        "overall_score": int(result.get("overall_score") or 0),
        "said_target": said_target,
        "transcript": transcript,
        "issue": issue,
        "tip": result.get("note") or "",
        "target": word,
    }


def _from_dictionary(word: str) -> WordAnalysisOut | None:
    """Build a word card from the offline WordNet dictionary (no Gemini, no quota). None if unknown."""
    from app.services.language_dictionary_service import lookup as dict_lookup

    entries = dict_lookup(word, max_entries=3)
    if not entries:
        return None
    first = entries[0]
    definition = (first.get("definition") or "").strip()
    if not definition:
        return None
    examples = first.get("examples") or []
    synonyms: list[str] = []
    for e in entries:
        for s in e.get("synonyms") or []:
            s = str(s).replace("_", " ").strip()
            if s and s.lower() != word.lower() and s not in synonyms:
                synonyms.append(s)
    return WordAnalysisOut(
        word=word,
        part_of_speech=str(first.get("part_of_speech") or "").strip(),
        definition=definition,
        example_sentence=str(examples[0]).strip() if examples else "",
        pronunciation_tip="",
        synonyms=synonyms[:4],
        cefr_level="",
    )


async def analyze_word(*, word: str, level: str = "A2") -> WordAnalysisOut:
    """Word meaning, LOCAL-FIRST: try the offline WordNet dictionary (free, instant, works without
    Gemini), then fall back to Gemini only for words WordNet doesn't have. Cached by (word, level)."""
    word = (word or "").strip()
    cache_key = (word.lower(), level)
    cached = _WORD_CACHE.get(cache_key)
    if cached is not None:
        return cached

    # 1) Offline dictionary — covers most content words with no quota cost.
    local = _from_dictionary(word)
    if local is not None:
        _WORD_CACHE.set(cache_key, local, _WORD_TTL)
        return local

    # 2) Gemini fallback (e.g. phrases or words WordNet lacks) — only when reachable.
    prompt = (
        f'Analyze the English word "{word}" for a {level} learner.\n'
        "Return ONLY JSON with EXACTLY these keys: "
        'word, part_of_speech (noun/verb/adjective/adverb/...), '
        "definition (a simple English definition at the learner's level), "
        "example_sentence (a natural sentence using the word, suitable for the level), "
        "pronunciation_tip (a short hint, e.g. IPA or which syllable is stressed), "
        "synonyms (a list of up to 4 simpler English synonyms), "
        "cefr_level (the word's own CEFR level: A1|A2|B1|B2|C1|C2)."
        + level_calibration_line(level)
    )
    try:
        raw = await generate_llm_json(
            prompt, system=_WORD_ANALYSIS_SYSTEM, temperature=0.3, max_output_tokens=512
        )
        data = _parse_json_object(raw)
        if data:
            data.setdefault("word", word)
            if not isinstance(data.get("synonyms"), list):
                data["synonyms"] = []
            result = WordAnalysisOut.model_validate(data)
            _WORD_CACHE.set(cache_key, result, _WORD_TTL)  # cache successful analyses only
            return result
    except Exception as exc:  # pragma: no cover - LLM variance
        logger.warning("Word analysis failed for %r: %s", word, exc)
    return WordAnalysisOut(word=word, definition="(Analysis is temporarily unavailable. Please try again.)")


async def get_student_target_level(
    db: AsyncSession, *, student_id: int, language_id: int
) -> LanguageLevel:
    """CEFR level to target for AI vocabulary generation.

    Currently reading-skill level only (matches the flashcard deck's own level
    logic in language_content_service.list_content_items). This is the single
    seam to change once Reading/Listening levels should be blended in (e.g.
    max() or an average across skills) — every caller in this module goes
    through this function, not select_skill_level directly.
    """
    from app.services.language_progression_service import select_skill_level

    return await select_skill_level(
        db,
        student_id=student_id,
        language_id=language_id,
        skill=LanguageSkill.reading,
        default=LanguageLevel.A2,
    )


async def _get_or_create_today_usage(
    db: AsyncSession, *, student_id: int
) -> LanguageVocabularyAiDailyUsage:
    today = datetime.now(timezone.utc).date()
    row = (
        await db.execute(
            select(LanguageVocabularyAiDailyUsage).where(
                LanguageVocabularyAiDailyUsage.student_id == student_id,
                LanguageVocabularyAiDailyUsage.usage_date == today,
            )
        )
    ).scalar_one_or_none()
    if row:
        return row
    now = datetime.now(timezone.utc)
    row = LanguageVocabularyAiDailyUsage(
        student_id=student_id, usage_date=today, generated_count=0, created_at=now, updated_at=now
    )
    db.add(row)
    await db.flush()
    return row


async def generate_ai_vocabulary_batch(
    db: AsyncSession, *, student_id: int, count: int = AI_GENERATION_DAILY_LIMIT
) -> VocabularyAiGenerateOut:
    """Today's vocabulary batch, capped at 10/day, served from the student's level's fixed word bank
    (see language_vocabulary_word_bank_service) and auto-scheduled for SM-2.

    Level comes from get_student_target_level (the Reading/Listening blending seam). Words come from
    the pre-generated, deterministic per-level bank — not a live LLM call — so every student at a
    given level eventually studies the same curated set, in the same order, which reading/writing
    can later build content around. Every served word is immediately upserted into the same
    spaced-repetition table the flashcard deck reads from, so it shows up for review right away —
    there is exactly one SM-2 authority (language_vocabulary_sr_service).
    """
    language = await get_default_language(db)
    level = await get_student_target_level(db, student_id=student_id, language_id=language.id)

    usage = await _get_or_create_today_usage(db, student_id=student_id)
    if usage.generated_count >= AI_GENERATION_DAILY_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily AI vocabulary generation limit reached",
        )
    count = max(1, min(int(count or AI_GENERATION_DAILY_LIMIT), AI_GENERATION_DAILY_LIMIT - usage.generated_count))

    served = await serve_daily_words(db, student_id=student_id, language_id=language.id, level=level, count=count)
    if not served:
        # Student has exhausted this level's bank for now (or the bank isn't seeded yet).
        return VocabularyAiGenerateOut(
            words=[],
            generated_today=usage.generated_count,
            remaining_today=AI_GENERATION_DAILY_LIMIT - usage.generated_count,
        )

    words = [
        VocabularyAiWordOut(
            content_id=item.id,
            word=bw.word,
            part_of_speech=bw.part_of_speech,
            definition=bw.definition,
            example_sentence=bw.example_sentence,
            example_sentence_ar=bw.example_sentence_ar,
            translation_ar=bw.translation_ar,
            image_prompt=bw.image_prompt,
            cefr_level=bw.cefr_level.value,
        )
        for bw, item in served
    ]

    usage.generated_count += len(words)
    usage.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return VocabularyAiGenerateOut(
        words=words,
        generated_today=usage.generated_count,
        remaining_today=AI_GENERATION_DAILY_LIMIT - usage.generated_count,
    )


_CHALLENGE_SYSTEM = (
    "You are an adaptive vocabulary-review generator for an English-learning platform whose students "
    "are Syrian secondary-school learners. Write natural English at the requested CEFR level. Output "
    "is ENGLISH ONLY (never Arabic). Return ONLY valid JSON — no markdown, no code fences."
)


def _collect_review_words(cards: list[dict], *, limit: int = 6) -> list[str]:
    """Today's review set: SM-2 due words first, padded with other known/learning words if few."""
    due = [c["word"] for c in cards if c.get("due") and c.get("word")]
    words = list(dict.fromkeys(due))[:limit]
    if len(words) < 3:
        extra = [c["word"] for c in cards if c.get("word") and c["word"] not in words]
        words = list(dict.fromkeys(words + extra))[:limit]
    return words


async def generate_vocabulary_challenge(db: AsyncSession, *, student_id: int) -> VocabularyChallengeOut:
    """Build a fill-in-the-blanks paragraph from the student's due vocabulary (English only)."""
    data = await list_vocabulary(db, student_id=student_id)
    level = data.get("student_level") or "A2"
    words = _collect_review_words(data.get("cards", []))
    if len(words) < 2:
        return VocabularyChallengeOut(
            words=words,
            context_hint="You have no vocabulary to review yet — learn a few words first, then come back.",
        )

    prompt = (
        f"The student needs to review these English words today: {', '.join(words)}.\n"
        f"Write ONE cohesive short paragraph (3-5 sentences) at {level} level that naturally uses ALL of "
        "them, then turn it into a fill-in-the-blanks challenge." + level_calibration_line(level) + "\n"
        "Return ONLY JSON with EXACTLY: "
        'paragraph_challenge (the paragraph with each target word replaced by [blank1], [blank2], ... in order), '
        "context_hint (a short ENGLISH hint about what the paragraph is about), "
        'blanks_mapping (object mapping each "[blankN]" to its correct word), '
        "options_pool (a shuffled list = all the correct words PLUS exactly 2 plausible distractor words)."
    )
    try:
        raw = await generate_llm_json(
            prompt, system=_CHALLENGE_SYSTEM, temperature=0.6, max_output_tokens=900
        )
        parsed = _parse_json_object(raw)
        if parsed:
            mapping = parsed.get("blanks_mapping") if isinstance(parsed.get("blanks_mapping"), dict) else {}
            pool = parsed.get("options_pool") if isinstance(parsed.get("options_pool"), list) else []
            pool = [str(o) for o in pool]
            # Guarantee every correct answer is selectable.
            for correct in mapping.values():
                if correct not in pool:
                    pool.append(str(correct))
            return VocabularyChallengeOut(
                words=words,
                paragraph_challenge=str(parsed.get("paragraph_challenge") or ""),
                context_hint=str(parsed.get("context_hint") or ""),
                blanks_mapping={str(k): str(v) for k, v in mapping.items()},
                options_pool=pool,
            )
    except Exception as exc:  # pragma: no cover - LLM variance
        logger.warning("Vocabulary challenge generation failed: %s", exc)

    # Fallback: no AI paragraph, but still let the student review the words.
    return VocabularyChallengeOut(
        words=words,
        context_hint="The interactive challenge is temporarily unavailable — review these words instead.",
        options_pool=words,
    )


async def save_word(db: AsyncSession, *, student_id: int, word: str) -> dict:
    """Add a word the student met (e.g. tapped while reading) to their vocabulary bank.

    Goes through the same spaced-repetition upsert lesson vocab uses, so it is scheduled for review
    (due now) and shows up alongside the rest of the learner's words. Idempotent per lemma.
    """
    language = await get_default_language(db)
    lemma = normalize_word(word or "")
    if not lemma:
        return {"saved": False, "word": ""}

    # Cards in the vocabulary view are content items joined to progress by lemma, so a progress row
    # alone would be invisible (yet still counted as "due"). Ensure a vocabulary card exists for the
    # word — created at the learner's reading level, enriched lazily on first view.
    from app.models.language.analytics import LanguageAnalytics
    from app.models.language.enums import LanguageLevel

    existing = (
        await db.execute(
            select(LanguageContentItem)
            .where(
                LanguageContentItem.language_id == language.id,
                LanguageContentItem.content_type == CONTENT_TYPE,
                func.lower(LanguageContentItem.body_json["word"].astext) == lemma,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing is None:
        analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language.id})
        level = (analytics.reading_level if analytics and analytics.reading_level else LanguageLevel.A2)
        db.add(
            LanguageContentItem(
                language_id=language.id, skill=LanguageSkill.reading, level=level, content_type=CONTENT_TYPE,
                title=lemma, body_json={"word": lemma, "source": "saved"}, is_published=True, sort_order=0,
            )
        )
        await db.flush()

    from app.services.language_engagement_service import upsert_vocabulary_from_lesson

    await upsert_vocabulary_from_lesson(db, student_id=student_id, language_id=language.id, lemmas=[lemma])
    return {"saved": True, "word": lemma}


async def submit_vocabulary_challenge(
    db: AsyncSession, *, student_id: int, results: list[dict]
) -> dict:
    """Grade a finished daily challenge into the learner model (source='daily').

    Feeds one piece of evidence per blank without touching the flashcard SM-2 schedule (the
    flashcard review path stays the single authority for per-word spaced repetition).
    """
    language = await get_default_language(db)
    recorded = await record_challenge_results(
        db, student_id=student_id, language_id=language.id, results=results
    )
    correct = sum(1 for r in (results or []) if r.get("correct"))
    total = len(results or [])
    if total:
        await record_activity(
            db,
            student_id=student_id,
            language_id=language.id,
            event_type="vocabulary_challenge_completed",
            skill=LanguageSkill.reading,
            payload_json={"correct": correct, "total": total},
        )
    return {"recorded": recorded, "correct": correct, "total": total}


async def _progress_by_lemma(
    db: AsyncSession, *, student_id: int, language_id: int, lemmas: list[str]
) -> dict[str, LanguageVocabularyProgress]:
    if not lemmas:
        return {}
    result = await db.execute(
        select(LanguageVocabularyProgress).where(
            LanguageVocabularyProgress.student_id == student_id,
            LanguageVocabularyProgress.language_id == language_id,
            LanguageVocabularyProgress.lemma.in_(lemmas),
        )
    )
    return {p.lemma: p for p in result.scalars().all()}


async def _get_or_create_progress(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    lemma: str,
) -> LanguageVocabularyProgress:
    result = await db.execute(
        select(LanguageVocabularyProgress).where(
            LanguageVocabularyProgress.student_id == student_id,
            LanguageVocabularyProgress.language_id == language_id,
            LanguageVocabularyProgress.lemma == lemma,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        return row
    row = LanguageVocabularyProgress(
        student_id=student_id,
        language_id=language_id,
        lemma=lemma,
        status=LanguageVocabularyStatus.new,
        review_count=0,
        mastery_score=0.0,
    )
    db.add(row)
    await db.flush()
    return row


async def vocabulary_metrics(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    content_ids: list[int],
) -> dict:
    total_words = len(content_ids)
    if total_words == 0:
        return {
            "total_words": 0,
            "known_words": 0,
            "learning_words": 0,
            "new_words": 0,
            "reviewed_today": 0,
            "daily_review_goal": DAILY_REVIEW_GOAL,
        }
    items = await db.execute(select(LanguageContentItem).where(LanguageContentItem.id.in_(content_ids)))
    lemmas = []
    for item in items.scalars().all():
        body = item.body_json or {}
        w = normalize_word(body.get("word") or "")
        if w:
            lemmas.append(w)
    prog_map = await _progress_by_lemma(db, student_id=student_id, language_id=language_id, lemmas=lemmas)
    known = learning = new = 0
    for lemma in lemmas:
        p = prog_map.get(lemma)
        if not p or p.status == LanguageVocabularyStatus.new:
            new += 1
        elif p.status == LanguageVocabularyStatus.known:
            known += 1
        elif p.status == LanguageVocabularyStatus.learning:
            learning += 1
    reviewed_today = await _count_reviewed_today(db, student_id=student_id, language_id=language_id)
    return {
        "total_words": total_words,
        "known_words": known,
        "learning_words": learning,
        "new_words": new,
        "reviewed_today": reviewed_today,
        "daily_review_goal": DAILY_REVIEW_GOAL,
    }


async def _count_reviewed_today(db: AsyncSession, *, student_id: int, language_id: int) -> int:
    today = datetime.now(timezone.utc).date()
    return (
        await db.execute(
            select(func.count()).select_from(LanguageActivityLog).where(
                LanguageActivityLog.student_id == student_id,
                LanguageActivityLog.language_id == language_id,
                LanguageActivityLog.event_type == "vocabulary_reviewed",
                func.date(LanguageActivityLog.created_at) == today,
            )
        )
    ).scalar_one()


def _is_due(progress: LanguageVocabularyProgress | None, now: datetime) -> bool:
    """A card is due when it is not yet 'known' and its next review is now/overdue (or unscheduled)."""
    if progress is None:
        return True
    if progress.status == LanguageVocabularyStatus.known:
        return False
    nra = progress.next_review_at
    if nra is None:
        return True
    if nra.tzinfo is None:
        nra = nra.replace(tzinfo=timezone.utc)
    return nra <= now


def _card_out(item: LanguageContentItem, progress: LanguageVocabularyProgress | None) -> dict:
    body = item.body_json or {}
    word = body.get("word") or ""
    st = progress.status.value if progress else LanguageVocabularyStatus.new.value
    return {
        "id": item.id,
        "word": word,
        "translation_ar": body.get("translation_ar"),
        "example": body.get("example"),
        "example_ar": body.get("example_ar"),
        "part_of_speech": body.get("part_of_speech"),
        "level": item.level.value if item.level else None,
        "status": st,
        "enriched": bool(str(body.get("translation_ar") or "").strip()),
        "review_count": int(progress.review_count if progress else 0),
        "last_reviewed_at": progress.last_reviewed_at if progress else None,
        "next_review_at": progress.next_review_at if progress else None,
        "due": _is_due(progress, datetime.now(timezone.utc)),
        "is_difficult": bool(progress.is_difficult if progress else False),
        "image_url": body.get("image_url"),
    }


async def _ensure_enriched(db: AsyncSession, item: LanguageContentItem) -> None:
    """Lazy AI enrichment: fill a 'stub' word (no definition) once via analyze_word, then cache it
    into body_json so it's free forever. This lets the bank scale to thousands of cheap word stubs.
    """
    body = dict(item.body_json or {})
    word = str(body.get("word") or "").strip()
    if not word or str(body.get("translation_ar") or "").strip():
        return  # no word, or already enriched
    level = item.level.value if item.level else "A2"
    analysis = await analyze_word(word=word, level=level)
    definition = (analysis.definition or "").strip()
    if not definition or "unavailable" in definition.lower():
        return  # AI not available right now — leave as a stub, try again next view
    body["translation_ar"] = definition
    if analysis.example_sentence:
        body["example"] = analysis.example_sentence
    if analysis.part_of_speech:
        body["part_of_speech"] = analysis.part_of_speech
    item.body_json = body
    flag_modified(item, "body_json")
    await db.commit()


async def list_vocabulary(db: AsyncSession, *, student_id: int) -> dict:
    language = await get_default_language(db)
    student_level, lesson_level, items = await list_content_items(
        db,
        student_id=student_id,
        content_type=CONTENT_TYPE,
        skill=None,
        level_skill=LanguageSkill.reading,
    )
    lemmas = [normalize_word((i.body_json or {}).get("word") or "") for i in items]
    lemmas = [l for l in lemmas if l]
    prog_map = await _progress_by_lemma(db, student_id=student_id, language_id=language.id, lemmas=lemmas)

    # list_content_items returns every published (shared/global) item at the student's level —
    # correct for lessons/reading passages, but vocabulary content items are shared across every
    # student once created (get_or_create_word_image, word-bank get-or-create), so without this
    # filter every student's Review Bank showed the WHOLE level bank instead of just the words
    # actually served to them. A LanguageVocabularyProgress row is the one signal that a word was
    # actually served to this student (daily batch, save_word, or a lesson encounter).
    served_items = [
        item for item in items if normalize_word((item.body_json or {}).get("word") or "") in prog_map
    ]

    cards = []
    for item in served_items:
        lemma = normalize_word((item.body_json or {}).get("word") or "")
        cards.append(_card_out(item, prog_map.get(lemma)))
    metrics = await vocabulary_metrics(
        db,
        student_id=student_id,
        language_id=language.id,
        content_ids=[i.id for i in served_items],
    )
    return {
        "student_level": student_level.value,
        "lesson_level": lesson_level.value if lesson_level else None,
        "metrics": metrics,
        "cards": cards,
    }


async def get_vocabulary_card(db: AsyncSession, *, student_id: int, content_id: int) -> dict:
    language = await get_default_language(db)
    item = await get_content_item(
        db,
        student_id=student_id,
        content_id=content_id,
        content_type=CONTENT_TYPE,
        skill=None,
        level_skill=LanguageSkill.reading,
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    await _ensure_enriched(db, item)  # fill stub words on first view (cached afterwards)
    lemma = normalize_word((item.body_json or {}).get("word") or "")
    prog_map = await _progress_by_lemma(db, student_id=student_id, language_id=language.id, lemmas=[lemma])
    return _card_out(item, prog_map.get(lemma))


async def review_vocabulary(
    db: AsyncSession,
    *,
    student_id: int,
    content_id: int,
    quality: int,
) -> dict:
    """Grade a vocabulary card with SM-2 (single unified review path).

    `quality` is an SM-2 recall grade 0-5 (UI sends 1=Again, 3=Hard, 4=Good, 5=Easy).
    Scheduling fields (ease/interval/repetition/next_review_at) and status are all updated
    together so the flashcard and the spaced-repetition schedule never diverge.
    """
    if not isinstance(quality, int) or quality < 0 or quality > 5:
        raise HTTPException(status_code=400, detail="quality must be between 0 and 5")
    language = await get_default_language(db)
    item = await get_content_item(
        db,
        student_id=student_id,
        content_id=content_id,
        content_type=CONTENT_TYPE,
        skill=None,
        level_skill=LanguageSkill.reading,
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    lemma = normalize_word((item.body_json or {}).get("word") or "")
    if not lemma:
        raise HTTPException(status_code=400, detail="Invalid card")
    progress = await _get_or_create_progress(
        db, student_id=student_id, language_id=language.id, lemma=lemma
    )

    ease, interval, repetition = compute_sm2(
        float(progress.ease_factor or 2.5),
        int(progress.interval_days or 1),
        int(progress.repetition_number or 0),
        quality,
    )
    now = datetime.now(timezone.utc)
    progress.ease_factor = ease
    progress.interval_days = interval
    progress.repetition_number = repetition
    progress.review_count = int(progress.review_count or 0) + 1
    progress.last_reviewed_at = now
    progress.next_review_at = now + timedelta(days=interval)

    became_known = False
    if repetition >= 5 and quality >= 4:
        if progress.status != LanguageVocabularyStatus.known:
            became_known = True
        progress.status = LanguageVocabularyStatus.known
        progress.mastery_score = 1.0
    elif quality >= 3:
        progress.status = LanguageVocabularyStatus.learning
        progress.mastery_score = min(0.99, repetition / 5.0)
    else:
        progress.status = LanguageVocabularyStatus.new
        progress.mastery_score = max(0.0, float(progress.mastery_score or 0.0) - 0.2)
        progress.fail_count = int(progress.fail_count or 0) + 1
        if progress.fail_count >= DIFFICULT_FAIL_THRESHOLD:
            progress.is_difficult = True

    if quality >= 4:
        progress.consecutive_good_count = int(progress.consecutive_good_count or 0) + 1
        if progress.is_difficult and progress.consecutive_good_count >= CONSECUTIVE_GOOD_TO_CLEAR_DIFFICULT:
            progress.is_difficult = False
    else:
        # Hard (3) still passes but breaks the "in a row" streak; a fail (<3) breaks it too.
        progress.consecutive_good_count = 0

    await db.flush()
    # Vocabulary earns XP via the daily mission ("review due words" task), not per word,
    # so spaced-repetition stays unlimited for practice without farming XP.
    await record_activity(
        db,
        student_id=student_id,
        language_id=language.id,
        event_type="vocabulary_reviewed",
        skill=LanguageSkill.reading,
        payload_json={"content_item_id": item.id, "word": lemma, "title": item.title, "quality": quality},
    )
    await refresh_language_analytics(db, student_id=student_id, language_id=language.id)
    await record_vocabulary_review(db, student_id=student_id, language_id=language.id, quality=quality)
    return _card_out(item, progress)
