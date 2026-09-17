"""Student-personalized listening practice (Phase 2 personalization).

Each learner has their own listening lesson pool (`LanguageContentItem.student_id`).
`next_listening` returns the first lesson quickly (one sync generation when the pool is
empty), then schedules background prefill to TARGET. Supertonic TTS is unchanged.
"""

from __future__ import annotations

import logging
import hashlib
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.language.content import LanguageContentItem
from app.models.language.enums import LanguageContentProgressStatus, LanguageLevel, LanguageSkill
from app.models.language.progress import LanguageListeningProgress
from app.models.language.tts_cache import LanguageLessonAudioCache
from app.services.language_content_service import lesson_body_for_student, resolve_listening_audio
from app.services.language_generation_gate import (
    can_generate,
    note_failure as note_generation_failure,
    note_success as note_generation_success,
)
from app.services.language_learner_context_service import (
    LanguageLearnerContext,
    compute_listening_profile_hash,
    format_language_ai_context,
    get_language_learner_context,
    listening_generation_metadata,
)
from app.services.language_lesson_generation_service import generate_and_store
from app.services.language_listening_lesson_context import listening_lesson_api_payload
from app.services.language_listening_selection import select_deterministic_listening_lesson
from app.services.language_listening_reservation import listening_session_reservation_service
from app.services.language_subscription_service import get_default_language
from app.services.language_tts_service import get_lesson_audio

logger = logging.getLogger(__name__)

_PERSONALIZED_SOURCE = "ai_personalized"
TARGET_UNSEEN_LISTENING_POOL = 5
MAX_REFILL_ATTEMPTS = 3
MAX_STALE_REPLACEMENTS_PER_REFILL = 2
SYNC_FIRST_LESSON_COUNT = 1


def _content_item_has_student_owner() -> bool:
    return hasattr(LanguageContentItem, "student_id")


def _listening_body_question_count(item: LanguageContentItem | None) -> int:
    body = item.body_json if item is not None and isinstance(item.body_json, dict) else {}
    return len(body.get("questions") or [])


def _listening_body_grammar_id(item: LanguageContentItem | None) -> str:
    body = item.body_json if item is not None and isinstance(item.body_json, dict) else {}
    return str(body.get("grammar_id") or "").strip()


def _is_current_personalized_listening_item(
    item: LanguageContentItem | None,
    *,
    student_id: int,
    grammar_id: str | None,
) -> bool:
    if item is None:
        return False
    body = item.body_json if isinstance(item.body_json, dict) else {}
    if getattr(item, "student_id", None) != student_id:
        return False
    if body.get("source") != _PERSONALIZED_SOURCE:
        return False
    if _listening_body_question_count(item) != 4:
        return False
    stamped = _listening_body_grammar_id(item)
    if not stamped:
        return False
    return not grammar_id or stamped == grammar_id


async def _official_listening_cefr(db: AsyncSession, *, student_id: int, language_id: int) -> str | None:
    from app.services.language_progression_service import select_skill_level_str

    try:
        return await select_skill_level_str(
            db,
            student_id=student_id,
            language_id=language_id,
            skill=LanguageSkill.listening,
        )
    except Exception:
        return None


_CEFR_ORDER = ("A1", "A2", "B1", "B2", "C1", "C2")


def _next_cefr_level(level: str) -> str | None:
    norm = str(level or "").upper()
    if norm not in _CEFR_ORDER:
        return None
    idx = _CEFR_ORDER.index(norm)
    if idx + 1 >= len(_CEFR_ORDER):
        return norm
    return _CEFR_ORDER[idx + 1]


async def _target_listening_cefr(db: AsyncSession, *, student_id: int, language_id: int) -> str | None:
    official = await _official_listening_cefr(db, student_id=student_id, language_id=language_id)
    if not official:
        return None
    return _next_cefr_level(official)


def _empty_progress_out() -> dict:
    return {
        "status": "not_started",
        "score_percent": None,
        "completed_at": None,
        "attempt_count": 0,
    }


async def serialize_listening_lesson(
    db: AsyncSession,
    *,
    item: LanguageContentItem,
    student_id: int,
    progress_out: dict | None = None,
) -> dict:
    language = await get_default_language(db)
    return await _lesson_payload(
        db,
        item=item,
        student_id=student_id,
        language_id=language.id,
        progress_out=progress_out,
    )


async def _lesson_payload(
    db: AsyncSession,
    *,
    item: LanguageContentItem,
    student_id: int,
    language_id: int,
    progress_out: dict | None = None,
) -> dict:
    audio_url, audio_available = await _ensure_audio(db, item)
    body = lesson_body_for_student(item)
    official = await _official_listening_cefr(db, student_id=student_id, language_id=language_id)
    target = await _target_listening_cefr(db, student_id=student_id, language_id=language_id)
    return listening_lesson_api_payload(
        item,
        body=body,
        audio_url=audio_url,
        audio_available=audio_available,
        progress_out=progress_out or _empty_progress_out(),
        official_cefr=official,
        target_cefr=target,
    )


def listening_pool_deficit(remaining: int, *, target: int = TARGET_UNSEEN_LISTENING_POOL) -> int:
    """How many personalized lessons to generate so unseen count reaches the target."""
    return max(0, target - max(0, remaining))


def simulate_guaranteed_refill(
    valid_per_attempt: list[int],
    *,
    start_remaining: int = 0,
    target: int = TARGET_UNSEEN_LISTENING_POOL,
    max_attempts: int = MAX_REFILL_ATTEMPTS,
) -> tuple[int, int, int]:
    """Pure simulation of guaranteed refill for unit verification."""
    remaining = start_remaining
    total_generated = 0
    attempts_used = 0
    for made in valid_per_attempt:
        if attempts_used >= max_attempts:
            break
        deficit = listening_pool_deficit(remaining, target=target)
        if deficit <= 0:
            break
        attempts_used += 1
        stored = max(0, min(made, deficit))
        remaining += stored
        total_generated += stored
        if remaining >= target:
            break
    return remaining, total_generated, attempts_used


def _lesson_profile_hash(body: dict | None) -> str | None:
    if not body:
        return None
    value = body.get("generation_profile_hash")
    return str(value).strip() if value else None


def _personalized_pool_filters(
    *,
    student_id: int,
    language_id: int,
    level: str,
    active_only: bool = True,
    grammar_id: str | None = None,
):
    clauses = [
        LanguageContentItem.language_id == language_id,
        LanguageContentItem.skill == LanguageSkill.listening,
        LanguageContentItem.content_type == "lesson",
        LanguageContentItem.level == LanguageLevel(level),
    ]
    if _content_item_has_student_owner():
        clauses.extend(
            [
                LanguageContentItem.student_id == student_id,
                LanguageContentItem.body_json["source"].astext == _PERSONALIZED_SOURCE,
            ]
        )
        if grammar_id:
            clauses.append(LanguageContentItem.body_json["grammar_id"].astext == grammar_id)
    if active_only:
        clauses.extend(
            [
                LanguageContentItem.is_published.is_(True),
                or_(
                    LanguageContentItem.body_json["pool_stale"].astext.is_(None),
                    LanguageContentItem.body_json["pool_stale"].astext != "true",
                ),
            ]
        )
    return clauses


def _completed_ids_subquery(student_id: int):
    return select(LanguageListeningProgress.content_item_id).where(
        LanguageListeningProgress.student_id == student_id,
        LanguageListeningProgress.status == LanguageContentProgressStatus.completed,
    )


def _touched_ids_subquery(student_id: int):
    return select(LanguageListeningProgress.content_item_id).where(
        LanguageListeningProgress.student_id == student_id,
    )


async def _adaptive_level(db: AsyncSession, *, student_id: int, language_id: int) -> str:
    from app.services.language_progression_service import select_skill_level_str

    return await select_skill_level_str(
        db,
        student_id=student_id,
        language_id=language_id,
        skill=LanguageSkill.listening,
        default=LanguageLevel.A2,
    )


async def _current_listening_grammar_id(
    db: AsyncSession, *, student_id: int, language_id: int
) -> str | None:
    try:
        from app.services.language_grammar.enums import GrammarEvidenceSourceSkill
        from app.services.language_grammar_skill_context import build_skill_grammar_context

        ctx = await build_skill_grammar_context(
            db,
            student_id=student_id,
            language_id=language_id,
            source_skill=GrammarEvidenceSourceSkill.listening,
        )
        return ctx.grammar_id if ctx else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("current listening grammar resolution failed: %s", exc)
        return None


async def _active_unseen_count(
    db: AsyncSession, *, student_id: int, language_id: int, level: str, grammar_id: str | None = None
) -> int:
    res = await db.execute(
        select(func.count())
        .select_from(LanguageContentItem)
        .where(
            *_personalized_pool_filters(
                student_id=student_id,
                language_id=language_id,
                level=level,
                active_only=True,
                grammar_id=grammar_id,
            ),
            LanguageContentItem.id.notin_(_completed_ids_subquery(student_id)),
        )
    )
    return int(res.scalar() or 0)


async def _unseen_personalized(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    level: str,
    newest: bool = False,
    grammar_id: str | None = None,
) -> LanguageContentItem | None:
    if newest:
        q = (
            select(LanguageContentItem)
            .where(
                *_personalized_pool_filters(
                    student_id=student_id, language_id=language_id, level=level, active_only=True,
                    grammar_id=grammar_id,
                ),
                LanguageContentItem.id.notin_(_completed_ids_subquery(student_id)),
            )
            .order_by(LanguageContentItem.id.desc())
            .limit(1)
        )
        return (await db.execute(q)).scalar_one_or_none()
    return await select_deterministic_listening_lesson(
        db,
        student_id=student_id,
        language_id=language_id,
        level=level,
        pool_filters_fn=lambda **kwargs: _personalized_pool_filters(**kwargs, grammar_id=grammar_id),
        completed_ids_subquery=_completed_ids_subquery,
    )


async def _retire_stale_unseen(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    current_hash: str,
    limit: int = MAX_STALE_REPLACEMENTS_PER_REFILL,
) -> int:
    if not _content_item_has_student_owner():
        return 0
    rows = (
        await db.execute(
            select(LanguageContentItem)
            .where(
                LanguageContentItem.student_id == student_id,
                LanguageContentItem.language_id == language_id,
                LanguageContentItem.skill == LanguageSkill.listening,
                LanguageContentItem.content_type == "lesson",
                LanguageContentItem.body_json["source"].astext == _PERSONALIZED_SOURCE,
                LanguageContentItem.is_published.is_(True),
                or_(
                    LanguageContentItem.body_json["pool_stale"].astext.is_(None),
                    LanguageContentItem.body_json["pool_stale"].astext != "true",
                ),
                LanguageContentItem.id.notin_(_completed_ids_subquery(student_id)),
                LanguageContentItem.id.notin_(_touched_ids_subquery(student_id)),
            )
            .order_by(LanguageContentItem.id.asc())
            .limit(limit * 3)
        )
    ).scalars().all()

    retired = 0
    now = datetime.now(timezone.utc).isoformat()
    for item in rows:
        if retired >= limit:
            break
        body = item.body_json or {}
        if _lesson_profile_hash(body) == current_hash:
            continue
        body = dict(body)
        body["pool_stale"] = True
        body["stale_at"] = now
        body["stale_reason"] = "profile_evolved"
        body["superseded_by_hash"] = current_hash
        item.body_json = body
        item.is_published = False
        flag_modified(item, "body_json")
        retired += 1

    if retired:
        await db.flush()
        logger.info(
            "Listening pool retired stale unseen lessons student=%s count=%s new_hash=%s",
            student_id,
            retired,
            current_hash,
        )
    return retired


async def _load_listening_pool_context(
    db: AsyncSession, *, student_id: int
) -> tuple[LanguageLearnerContext, str, str, dict[str, str]]:
    ctx = await get_language_learner_context(db, student_id=student_id)
    return (
        ctx,
        compute_listening_profile_hash(ctx),
        format_language_ai_context(ctx),
        listening_generation_metadata(ctx),
    )


async def _recent_student_listening_titles(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    level: str,
    limit: int = 6,
) -> list[str]:
    if not _content_item_has_student_owner():
        return []
    rows = (
        await db.execute(
            select(LanguageContentItem.title)
            .where(
                LanguageContentItem.student_id == student_id,
                LanguageContentItem.language_id == language_id,
                LanguageContentItem.skill == LanguageSkill.listening,
                LanguageContentItem.content_type == "lesson",
                LanguageContentItem.level == LanguageLevel(level),
            )
            .order_by(LanguageContentItem.id.desc())
            .limit(limit)
        )
    ).all()
    return [str(title).strip() for (title,) in rows if str(title or "").strip()]


def _pick_listening_topic_lane(
    *,
    learner: LanguageLearnerContext | None,
    grammar_ctx,
    seed: str,
) -> str:
    lanes: list[str] = []
    if learner is not None:
        lanes.extend(str(v).strip() for v in learner.interests[:4] if str(v).strip())
        if learner.future_goal:
            lanes.append(str(learner.future_goal).strip())
    lanes.extend(str(v).strip() for v in getattr(grammar_ctx, "recommended_contexts", ()) if str(v).strip())
    if not lanes:
        lanes = [
            "home routine",
            "family conversation",
            "neighborhood errand",
            "class activity",
            "shop or cafe interaction",
            "health appointment",
            "community event",
            "simple work task",
        ]
    idx = int(seed[:4], 16) % len(lanes)
    return lanes[idx]


def _listening_personalization_block(
    *,
    learner: LanguageLearnerContext | None,
    grammar_ctx,
    level: str,
    student_id: int,
    profile_hash: str,
    recent_titles: list[str],
) -> tuple[str, str]:
    seed_source = "|".join(
        [
            str(student_id),
            str(level),
            str(getattr(grammar_ctx, "grammar_id", "")),
            str(profile_hash or ""),
            "|".join(recent_titles[:4]),
        ]
    )
    seed = hashlib.sha256(seed_source.encode("utf-8")).hexdigest()[:12]
    lane = _pick_listening_topic_lane(learner=learner, grammar_ctx=grammar_ctx, seed=seed)
    context_options = ", ".join(getattr(grammar_ctx, "recommended_contexts", ())[:4])
    avoid = "; ".join(recent_titles[:5])
    lines = [
        "LISTENING PERSONALIZATION (authoritative):",
        f"- actual lesson level: CEFR {level}",
        f"- scenario lane: {lane}",
        f"- variation_seed: {seed}",
        "- preserve the learner's adaptive/progression context above; do not flatten everyone into the same lesson.",
        "- create a fresh title, situation, names, details, and transcript; do not reuse stock wording.",
    ]
    if context_options:
        lines.append(f"- grammar-suitable context options: {context_options}")
    if avoid:
        lines.append(f"- avoid recent titles for this learner: {avoid}")
    topics = ", ".join(part for part in [lane, context_options] if part)
    return "\n".join(lines), topics


async def _has_audio_cache(db: AsyncSession, content_item_id: int) -> bool:
    row = (
        await db.execute(
            select(LanguageLessonAudioCache.id).where(
                LanguageLessonAudioCache.content_item_id == content_item_id,
                LanguageLessonAudioCache.voice_source == "supertonic",
            )
        )
    ).scalar_one_or_none()
    return row is not None


async def _pregenerate_lesson_audio(db: AsyncSession, *, content_item_id: int) -> bool:
    """Best-effort Supertonic synth + cache for one lesson (no-op if already cached)."""
    if await _has_audio_cache(db, content_item_id):
        return True
    item = await db.get(LanguageContentItem, content_item_id)
    if not item:
        return False
    url, available = await resolve_listening_audio(db, item)
    if available:
        return True
    try:
        tts = await get_lesson_audio(db, content_item_id=content_item_id)
        await db.commit()
        return bool(tts and tts.get("public_url"))
    except Exception as exc:  # pragma: no cover
        logger.warning("Listening pregenerate audio failed (%s): %s", content_item_id, exc)
        await db.rollback()
        return False


async def _generate_pool_lessons(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    level: str,
    count: int,
    learner_context: str,
    metadata: dict[str, str],
    learner: LanguageLearnerContext | None = None,
) -> int:
    if count <= 0 or not can_generate():
        return 0
    if not _content_item_has_student_owner():
        try:
            made = await generate_and_store(
                db,
                language_id=language_id,
                skill="listening",
                level=level,
                count=count,
                adaptive_context=learner_context,
            )
            if made:
                note_generation_success()
                await db.commit()
                return int(made)
            note_generation_failure()
        except Exception as exc:  # pragma: no cover
            logger.warning("Listening shared-pool generation failed level=%s count=%s: %s", level, count, exc)
            note_generation_failure()
            await db.rollback()
        return 0
    # Wave C: resolver-first grammar stamp + shared prompt block.
    from app.services.language_grammar.enums import GrammarEvidenceSourceSkill
    from app.services.language_grammar_skill_context import (
        build_skill_grammar_context,
        merge_prompt_context,
    )

    grammar_ctx = await build_skill_grammar_context(
        db,
        student_id=student_id,
        language_id=language_id,
        source_skill=GrammarEvidenceSourceSkill.listening,
    )
    if grammar_ctx is None:
        return 0
    recent_titles = await _recent_student_listening_titles(
        db,
        student_id=student_id,
        language_id=language_id,
        level=level,
    )
    personalization, topics = _listening_personalization_block(
        learner=learner,
        grammar_ctx=grammar_ctx,
        level=level,
        student_id=student_id,
        profile_hash=str(metadata.get("generation_profile_hash") or ""),
        recent_titles=recent_titles,
    )
    adaptive = f"{merge_prompt_context(learner_context, grammar_ctx)}\n\n{personalization}"
    extras: dict = dict(metadata or {})
    extras.update(grammar_ctx.as_stamp_dict())
    try:
        made = await generate_and_store(
            db,
            language_id=language_id,
            skill="listening",
            level=level,
            count=count,
            topics=topics,
            adaptive_context=adaptive,
            student_id=student_id,
            source=_PERSONALIZED_SOURCE,
            body_extras=extras,
        )
        if made:
            note_generation_success()
            await db.commit()
            return int(made)
        note_generation_failure()
    except Exception as exc:  # pragma: no cover
        logger.warning("Listening pool generation failed student=%s count=%s: %s", student_id, count, exc)
        note_generation_failure()
        await db.rollback()
    return 0


async def _evolve_pool(
    db: AsyncSession, *, student_id: int, language_id: int, current_hash: str
) -> int:
    retired = await _retire_stale_unseen(
        db,
        student_id=student_id,
        language_id=language_id,
        current_hash=current_hash,
    )
    if retired:
        await db.commit()
    return retired


async def background_fill_listening_pool(db: AsyncSession, *, student_id: int) -> int:
    """Fill pool to TARGET one lesson (+ audio) at a time. Called from background task only."""
    language = await get_default_language(db)
    level = await _adaptive_level(db, student_id=student_id, language_id=language.id)
    grammar_id = await _current_listening_grammar_id(db, student_id=student_id, language_id=language.id)
    ctx, current_hash, learner_context, metadata = await _load_listening_pool_context(
        db, student_id=student_id
    )
    await _evolve_pool(db, student_id=student_id, language_id=language.id, current_hash=current_hash)

    total_generated = 0
    consecutive_failures = 0
    while True:
        active = await _active_unseen_count(
            db, student_id=student_id, language_id=language.id, level=level, grammar_id=grammar_id
        )
        if listening_pool_deficit(active) <= 0 or not can_generate():
            break
        if consecutive_failures >= MAX_REFILL_ATTEMPTS:
            break

        made = await _generate_pool_lessons(
            db,
            student_id=student_id,
            language_id=language.id,
            level=level,
            count=1,
            learner_context=learner_context,
            metadata=metadata,
            learner=ctx,
        )
        if made:
            consecutive_failures = 0
            total_generated += made
            newest = await _unseen_personalized(
                db,
                student_id=student_id,
                language_id=language.id,
                level=level,
                newest=True,
                grammar_id=grammar_id,
            )
            if newest:
                await _pregenerate_lesson_audio(db, content_item_id=newest.id)
            logger.info(
                "Listening background lesson student=%s active_before=%s generated=1 hash=%s",
                student_id,
                active,
                current_hash,
            )
        else:
            consecutive_failures += 1

    # Pregenerate audio for any pool lessons still missing cache (e.g. sync-only audio so far).
    rows = (
        await db.execute(
            select(LanguageContentItem.id)
            .where(
                *_personalized_pool_filters(
                    student_id=student_id,
                    language_id=language.id,
                    level=level,
                    active_only=True,
                    grammar_id=grammar_id,
                ),
                LanguageContentItem.id.notin_(_completed_ids_subquery(student_id)),
            )
            .order_by(LanguageContentItem.id.asc())
        )
    ).scalars().all()
    for content_id in rows:
        if not await _has_audio_cache(db, content_id):
            await _pregenerate_lesson_audio(db, content_item_id=content_id)

    active = await _active_unseen_count(
        db, student_id=student_id, language_id=language.id, level=level, grammar_id=grammar_id
    )
    if active < TARGET_UNSEEN_LISTENING_POOL:
        logger.warning(
            "Listening background prefill below target student=%s active=%s target=%s",
            student_id,
            active,
            TARGET_UNSEEN_LISTENING_POOL,
        )
    return total_generated


async def list_personalized_listening(
    db: AsyncSession, *, student_id: int
) -> tuple[str, list[LanguageContentItem], dict[int, LanguageListeningProgress]]:
    language = await get_default_language(db)
    level = await _adaptive_level(db, student_id=student_id, language_id=language.id)
    rows = (
        await db.execute(
            select(LanguageContentItem)
            .where(
                *_personalized_pool_filters(
                    student_id=student_id, language_id=language.id, level=level, active_only=True
                ),
            )
            .order_by(LanguageContentItem.id.desc())
        )
    ).scalars().all()
    items = list(rows)
    progress_map: dict[int, LanguageListeningProgress] = {}
    if items:
        ids = [i.id for i in items]
        prog = await db.execute(
            select(LanguageListeningProgress).where(
                LanguageListeningProgress.student_id == student_id,
                LanguageListeningProgress.content_item_id.in_(ids),
            )
        )
        progress_map = {p.content_item_id: p for p in prog.scalars().all()}
    return level, items, progress_map


async def _ensure_audio(db: AsyncSession, item: LanguageContentItem) -> tuple[str | None, bool]:
    audio_url, audio_available = await resolve_listening_audio(db, item)
    if audio_available:
        return audio_url, audio_available
    try:
        tts = await get_lesson_audio(db, content_item_id=item.id)
        await db.commit()
        if tts and tts.get("public_url"):
            return tts["public_url"], True
    except Exception as exc:  # pragma: no cover
        logger.warning("Listening audio synthesis failed (%s): %s", item.id, exc)
    return None, False


def _needs_background_prefill(active_unseen: int) -> bool:
    return listening_pool_deficit(active_unseen) > 0 and can_generate()


async def _resolve_listening_item(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    level: str,
    learner_context: str,
    metadata: dict[str, str],
    grammar_id: str | None = None,
    learner: LanguageLearnerContext | None = None,
) -> LanguageContentItem | None:
    async def _select() -> LanguageContentItem | None:
        active = await _active_unseen_count(
            db, student_id=student_id, language_id=language_id, level=level, grammar_id=grammar_id
        )
        if active == 0 and can_generate():
            await _generate_pool_lessons(
                db,
                student_id=student_id,
                language_id=language_id,
                level=level,
                count=SYNC_FIRST_LESSON_COUNT,
                learner_context=learner_context,
                metadata=metadata,
                learner=learner,
            )
        return await _unseen_personalized(
            db, student_id=student_id, language_id=language_id, level=level, grammar_id=grammar_id
        )

    resolved = await listening_session_reservation_service.resolve_reserved_lesson(
        db,
        student_id=student_id,
        language_id=language_id,
        select_lesson_fn=_select,
    )
    if resolved is None:
        return None
    item = await db.get(LanguageContentItem, resolved.content_item_id)
    if _is_current_personalized_listening_item(item, student_id=student_id, grammar_id=grammar_id):
        return item
    # Stale pin — content removed; clear and re-select once.
    logger.warning(
        "Listening reservation points to missing content student=%s content=%s — recovering",
        student_id,
        resolved.content_item_id,
    )
    await listening_session_reservation_service.skip_reservation(
        db,
        student_id=student_id,
        language_id=language_id,
        content_item_id=resolved.content_item_id,
    )
    await db.commit()
    recovered = await listening_session_reservation_service.resolve_reserved_lesson(
        db,
        student_id=student_id,
        language_id=language_id,
        select_lesson_fn=_select,
    )
    if recovered is None:
        return None
    recovered_item = await db.get(LanguageContentItem, recovered.content_item_id)
    if _is_current_personalized_listening_item(recovered_item, student_id=student_id, grammar_id=grammar_id):
        return recovered_item
    await listening_session_reservation_service.skip_reservation(
        db,
        student_id=student_id,
        language_id=language_id,
        content_item_id=recovered.content_item_id,
    )
    return None


async def skip_listening(db: AsyncSession, *, student_id: int, content_id: int | None = None) -> bool:
    """Clear active reservation so the next request runs deterministic selection again."""
    language = await get_default_language(db)
    return await listening_session_reservation_service.skip_reservation(
        db,
        student_id=student_id,
        language_id=language.id,
        content_item_id=content_id,
    )


async def next_listening(db: AsyncSession, *, student_id: int) -> tuple[dict | None, bool]:
    """Next clip — respects session reservation pin; deterministic when selecting."""
    language = await get_default_language(db)
    level = await _adaptive_level(db, student_id=student_id, language_id=language.id)

    ctx, current_hash, learner_context, metadata = await _load_listening_pool_context(
        db, student_id=student_id
    )
    await _evolve_pool(db, student_id=student_id, language_id=language.id, current_hash=current_hash)

    grammar_id = await _current_listening_grammar_id(db, student_id=student_id, language_id=language.id)
    item = await _resolve_listening_item(
        db,
        student_id=student_id,
        language_id=language.id,
        level=level,
        learner_context=learner_context,
        metadata=metadata,
        grammar_id=grammar_id,
        learner=ctx,
    )
    if item is None:
        return None, False

    prog = await db.execute(
        select(LanguageListeningProgress).where(
            LanguageListeningProgress.student_id == student_id,
            LanguageListeningProgress.content_item_id == item.id,
        )
    )
    progress = prog.scalar_one_or_none()
    progress_out = _empty_progress_out()
    if progress is not None:
        progress_out = {
            "status": progress.status.value if progress.status else "not_started",
            "score_percent": float(progress.score_percent) if progress.score_percent is not None else None,
            "completed_at": progress.completed_at,
            "attempt_count": int(progress.attempt_count or 0),
        }

    from app.services.language_listening_lesson_experience.service import build_student_lesson_bundle

    bundle = await build_student_lesson_bundle(
        db,
        item=item,
        student_id=student_id,
        language_id=language.id,
        progress_out=progress_out,
    )
    lesson = bundle.model_dump(mode="json")
    playback = lesson.get("playback") or {}
    if not playback.get("instructions"):
        playback["instructions"] = "Listen and answer the questions."
        lesson["playback"] = playback

    active_after = await _active_unseen_count(
        db, student_id=student_id, language_id=language.id, level=level, grammar_id=grammar_id
    )
    # Wave D: per-student attested session for grammar evidence.
    try:
        from app.services.language_content_service import get_answer_key
        from app.services.language_grammar.enums import GrammarEvidenceSourceSkill
        from app.services.language_grammar_integrity import issue_and_stamp_for_context
        from app.services.language_grammar_skill_context import build_skill_grammar_context

        grammar_ctx = await build_skill_grammar_context(
            db,
            student_id=student_id,
            language_id=language.id,
            source_skill=GrammarEvidenceSourceSkill.listening,
        )
        if grammar_ctx is not None:
            session = await issue_and_stamp_for_context(
                db,
                student_id=student_id,
                language_id=language.id,
                grammar_ctx=grammar_ctx,
                skill=GrammarEvidenceSourceSkill.listening,
                activity_type="listening",
                lesson_id=str(item.id),
                content_item_id=int(item.id),
                server_payload={"answer_key": get_answer_key(item.body_json)},
            )
            lesson.setdefault("meta", {})
            lesson["meta"]["activity_session_id"] = str(session.id)
            lesson["meta"]["grammar_id"] = grammar_ctx.grammar_id
            lesson["meta"]["grammar_title"] = grammar_ctx.display_name
    except Exception as exc:  # noqa: BLE001
        logger.warning("listening activity session issue failed: %s", exc)
    needs_audio_prefill = not bool(playback.get("audio_available"))
    return lesson, _needs_background_prefill(active_after) or needs_audio_prefill
