"""Verify Phase 2.3 evolving listening personalization."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal
from app.models.language.analytics import LanguageAnalytics
from app.models.language.content import LanguageContentItem
from app.models.language.enums import LanguageContentProgressStatus, LanguageLevel, LanguageSkill
from app.models.language.progress import LanguageListeningProgress
from app.models.language.profile import LanguageStudentProfile
from app.services.language_learner_context_service import (
    compute_listening_profile_hash,
    get_language_learner_context,
)
from app.services.language_listening_service import (
    MAX_STALE_REPLACEMENTS_PER_REFILL,
    _active_unseen_count,
    _refill_personalized_pool,
    _retire_stale_unseen,
)
from app.services.language_subscription_service import get_default_language

STUDENT_ID = 64


async def lesson_stats(db, student_id: int, language_id: int, level: str) -> dict:
    rows = (
        await db.execute(
            select(LanguageContentItem)
            .where(
                LanguageContentItem.student_id == student_id,
                LanguageContentItem.skill == LanguageSkill.listening,
            )
            .order_by(LanguageContentItem.id)
        )
    ).scalars().all()
    active = [r for r in rows if r.is_published and not (r.body_json or {}).get("pool_stale")]
    stale = [r for r in rows if (r.body_json or {}).get("pool_stale")]
    completed_ids = set(
        (
            await db.execute(
                select(LanguageListeningProgress.content_item_id).where(
                    LanguageListeningProgress.student_id == student_id,
                    LanguageListeningProgress.status == LanguageContentProgressStatus.completed,
                )
            )
        ).scalars().all()
    )
    hashes = {(r.body_json or {}).get("generation_profile_hash") for r in rows}
    return {
        "total": len(rows),
        "active": len(active),
        "stale": len(stale),
        "completed": len(completed_ids),
        "hashes": {h for h in hashes if h},
        "levels": sorted({r.level.value for r in rows if r.level}),
    }


async def main() -> None:
    ok = True
    async with AsyncSessionLocal() as db:
        language = await get_default_language(db)
        analytics = await db.get(
            LanguageAnalytics, {"student_id": STUDENT_ID, "language_id": language.id}
        )
        if not analytics:
            analytics = LanguageAnalytics(student_id=STUDENT_ID, language_id=language.id)
            db.add(analytics)
        analytics.listening_level = LanguageLevel.A2
        profile = (
            await db.execute(
                select(LanguageStudentProfile).where(
                    LanguageStudentProfile.student_id == STUDENT_ID,
                    LanguageStudentProfile.language_id == language.id,
                )
            )
        ).scalar_one_or_none()
        if profile:
            prefs = dict(profile.preferences_json or {})
            mem = dict(prefs.get("memory") or {})
            mem["interests"] = ["football", "music"]
            prefs["memory"] = mem
            profile.preferences_json = prefs
        await db.commit()

        ctx_a2 = await get_language_learner_context(db, student_id=STUDENT_ID)
        hash_a2 = compute_listening_profile_hash(ctx_a2)
        print(f"Step 1: A2 profile hash={hash_a2}")

        generated = await _refill_personalized_pool(
            db, student_id=STUDENT_ID, language_id=language.id, level="A2"
        )
        print(f"  Initial refill generated={generated}")
        stats1 = await lesson_stats(db, STUDENT_ID, language.id, "A2")
        print(f"  Pool stats: {stats1}")

        # Complete one lesson — must survive evolution
        first = (
            await db.execute(
                select(LanguageContentItem)
                .where(
                    LanguageContentItem.student_id == STUDENT_ID,
                    LanguageContentItem.skill == LanguageSkill.listening,
                    LanguageContentItem.is_published.is_(True),
                )
                .order_by(LanguageContentItem.id)
                .limit(1)
            )
        ).scalar_one_or_none()
        if first:
            db.add(
                LanguageListeningProgress(
                    student_id=STUDENT_ID,
                    content_item_id=first.id,
                    status=LanguageContentProgressStatus.completed,
                    score_percent=80.0,
                    completed_at=datetime.now(timezone.utc),
                    attempt_count=1,
                )
            )
            completed_id = first.id
            await db.commit()
            print(f"  Marked completed lesson id={completed_id}")
        else:
            completed_id = None
            ok = False

        # Evolve learner: B1 + new interests
        analytics.listening_level = LanguageLevel.B1
        if profile:
            prefs = dict(profile.preferences_json or {})
            mem = dict(prefs.get("memory") or {})
            mem["interests"] = ["programming", "robotics", "space"]
            prefs["memory"] = mem
            profile.preferences_json = prefs
        await db.commit()

        ctx_b1 = await get_language_learner_context(db, student_id=STUDENT_ID)
        hash_b1 = compute_listening_profile_hash(ctx_b1)
        print(f"\nStep 2: evolved B1 hash={hash_b1} (changed={hash_a2 != hash_b1})")
        ok = ok and hash_a2 != hash_b1

        retired = await _retire_stale_unseen(
            db,
            student_id=STUDENT_ID,
            language_id=language.id,
            current_hash=hash_b1,
            limit=MAX_STALE_REPLACEMENTS_PER_REFILL,
        )
        await db.commit()
        stats2 = await lesson_stats(db, STUDENT_ID, language.id, "B1")
        print(f"  Retired stale unseen={retired} stats={stats2}")
        ok = ok and retired > 0

        if completed_id:
            completed_row = await db.get(LanguageContentItem, completed_id)
            completed_prog = (
                await db.execute(
                    select(LanguageListeningProgress).where(
                        LanguageListeningProgress.student_id == STUDENT_ID,
                        LanguageListeningProgress.content_item_id == completed_id,
                    )
                )
            ).scalar_one_or_none()
            print(
                f"  Completed lesson preserved: row_exists={completed_row is not None} "
                f"still_completed={completed_prog.status.value if completed_prog else None}"
            )
            ok = ok and completed_row is not None
            ok = ok and completed_prog and completed_prog.status == LanguageContentProgressStatus.completed

        generated2 = await _refill_personalized_pool(
            db, student_id=STUDENT_ID, language_id=language.id, level="B1"
        )
        active_b1 = await _active_unseen_count(
            db, student_id=STUDENT_ID, language_id=language.id, level="B1"
        )
        new_rows = (
            await db.execute(
                select(LanguageContentItem)
                .where(
                    LanguageContentItem.student_id == STUDENT_ID,
                    LanguageContentItem.skill == LanguageSkill.listening,
                    LanguageContentItem.level == LanguageLevel.B1,
                    LanguageContentItem.is_published.is_(True),
                )
                .order_by(LanguageContentItem.id.desc())
                .limit(3)
            )
        ).scalars().all()
        new_hashes = {(r.body_json or {}).get("generation_profile_hash") for r in new_rows}
        print(f"\nStep 3: B1 refill generated={generated2} active_unseen_b1={active_b1}")
        print(f"  New lesson hashes sample={new_hashes}")
        ok = ok and hash_b1 in new_hashes

        stats3 = await lesson_stats(db, STUDENT_ID, language.id, "B1")
        print(f"  Final stats: {stats3}")
        ok = ok and stats3["completed"] >= 1

    print("\nPASS" if ok else "\nFAIL")


if __name__ == "__main__":
    asyncio.run(main())
