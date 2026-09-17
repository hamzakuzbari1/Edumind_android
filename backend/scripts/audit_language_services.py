"""Direct service-layer smoke test (no HTTP)."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, func, select, text

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.language.analytics import LanguageAnalytics
from app.models.language.catalog import Language
from app.models.language.engagement import LanguageStreak
from app.models.language.enums import LanguageSkill, LanguageVocabularyStatus
from app.models.language.progress import LanguageVocabularyProgress
from app.services.language_content_service import list_lessons
from app.services.language_hub_service import build_language_progress
from app.services.language_speaking_service import list_speaking
from app.services.language_vocabulary_service import list_vocabulary
from app.services.language_writing_service import list_writing
from app.services.parent_monitoring_service import _build_language_placement_summary


async def run(student_id: int) -> None:
    async with AsyncSessionLocal() as db:
        progress = await build_language_progress(db, student_id=student_id)
        parent = await _build_language_placement_summary(db, student_id)
        sl, ll, reading, _ = await list_lessons(db, student_id=student_id, skill=LanguageSkill.reading)
        _, ll2, listening, _ = await list_lessons(db, student_id=student_id, skill=LanguageSkill.listening)
        vocab = await list_vocabulary(db, student_id=student_id)
        writing = await list_writing(db, student_id=student_id)
        speaking = await list_speaking(db, student_id=student_id)

    engine = create_engine(get_settings().DATABASE_URL_SYNC)
    with engine.connect() as conn:
        lang_id = conn.execute(select(Language.id).where(Language.code == "en")).scalar()
        streak = conn.execute(
            select(LanguageStreak).where(
                LanguageStreak.student_id == student_id, LanguageStreak.language_id == lang_id
            )
        ).scalar_one_or_none()
        known = conn.execute(
            select(func.count())
            .select_from(LanguageVocabularyProgress)
            .where(
                LanguageVocabularyProgress.student_id == student_id,
                LanguageVocabularyProgress.language_id == lang_id,
                LanguageVocabularyProgress.status == LanguageVocabularyStatus.known,
            )
        ).scalar()
        analytics = conn.execute(
            select(LanguageAnalytics).where(
                LanguageAnalytics.student_id == student_id,
                LanguageAnalytics.language_id == lang_id,
            )
        ).scalar_one_or_none()

    print(f"student_id={student_id}")
    print(f"reading_lessons={len(reading)} (level {ll}) listening={len(listening)}")
    print(f"vocab_cards={len(vocab.get('cards', []))} writing={len(writing.get('prompts', []))} speaking={len(speaking.get('prompts', []))}")
    print(f"progress: streak={progress.get('current_streak')}/{progress.get('longest_streak')} vocab_learned={progress.get('vocabulary_learned')}")
    print(f"DB streak={streak.current_streak if streak else 0} known_vocab={known} analytics.vocabulary_count={analytics.vocabulary_count if analytics else 0}")
    print(f"progress match streak: {progress.get('current_streak') == (streak.current_streak if streak else 0)}")
    print(f"progress match vocab_count: {progress.get('vocabulary_count') == int(analytics.vocabulary_count or 0 if analytics else 0)}")
    print(f"parent overall={parent.get('overall_level') if parent else None} skill_growth keys={list((parent or {}).get('skill_growth', {}).keys())}")


if __name__ == "__main__":
    sid = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    asyncio.run(run(sid))
