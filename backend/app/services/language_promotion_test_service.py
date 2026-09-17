"""Level-up (promotion) test — confirm mastery of the current level, then unlock the next.

A short MCQ test for the current CEFR level (AI-generated, cached, curated fallback). The
answer key is held server-side keyed by a test_id; on a passing score we mark the current
level's curriculum objectives as mastered and advance the learner's speaking level.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.language.analytics import LanguageAnalytics
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.models.language.progress import LanguageCurriculumProgress
from app.services.ai_service import generate_llm_json
from app.services.claude_service import is_claude_configured
from app.services.language_curriculum_service import _current_level, get_level_curriculum
from app.services.language_engagement_service import record_activity
from app.services.language_level_utils import CEFR_RANK, RANK_CEFR
from app.services.language_subscription_service import get_default_language

logger = logging.getLogger(__name__)
settings = get_settings()

PASS_RATIO = 0.8
_TEST_TTL = 60 * 30
# test_id -> (expiry, level, [correct_index per question])
_tests: dict[str, tuple[float, str, list[int]]] = {}

_SYSTEM = (
    "You write CEFR level-check multiple-choice questions. For the given level, produce 6 "
    "questions testing grammar, vocabulary and usage at that level. "
    'Return ONLY JSON: {"questions": [{"prompt": str, "choices": [str, str, str, str], "correct_index": 0-3}]}'
)

# Reliable fallback bank (4 questions per level).
_CURATED: dict[str, list[dict]] = {
    "A1": [
        {"prompt": "She ___ a student.", "choices": ["is", "are", "am", "be"], "correct_index": 0},
        {"prompt": "Choose the plural: one book, two ___", "choices": ["book", "books", "bookes", "books'"], "correct_index": 1},
        {"prompt": "___ name is Omar.", "choices": ["My", "Me", "I", "Mine"], "correct_index": 0},
        {"prompt": "I ___ coffee every morning.", "choices": ["drinks", "drink", "drinking", "drank"], "correct_index": 1},
    ],
    "A2": [
        {"prompt": "Yesterday I ___ to the market.", "choices": ["go", "goes", "went", "gone"], "correct_index": 2},
        {"prompt": "This box is ___ than that one.", "choices": ["heavy", "heavier", "heaviest", "more heavy"], "correct_index": 1},
        {"prompt": "We ___ travel next week.", "choices": ["are going to", "go", "went", "gone"], "correct_index": 0},
        {"prompt": "There ___ some apples on the table.", "choices": ["is", "are", "be", "was"], "correct_index": 1},
    ],
    "B1": [
        {"prompt": "I ___ here for three years.", "choices": ["live", "lived", "have lived", "living"], "correct_index": 2},
        {"prompt": "If I had time, I ___ exercise more.", "choices": ["will", "would", "did", "have"], "correct_index": 1},
        {"prompt": "She said she ___ tired.", "choices": ["is", "was", "be", "been"], "correct_index": 1},
        {"prompt": "Choose the best linker: It rained, ___ we stayed home.", "choices": ["but", "so", "or", "nor"], "correct_index": 1},
    ],
    "B2": [
        {"prompt": "The report ___ by the team yesterday.", "choices": ["wrote", "was written", "has written", "writes"], "correct_index": 1},
        {"prompt": "___ the cost, the project is worthwhile.", "choices": ["Despite", "Although", "However", "Because"], "correct_index": 0},
        {"prompt": "He'd rather ___ than argue.", "choices": ["to leave", "leaving", "leave", "left"], "correct_index": 2},
        {"prompt": "Pick the collocation: make a ___", "choices": ["decision", "homework", "mistake'", "advice"], "correct_index": 0},
    ],
    "C1": [
        {"prompt": "Hardly ___ when the phone rang.", "choices": ["I had arrived", "had I arrived", "I arrived", "did I arrive"], "correct_index": 1},
        {"prompt": "Choose the hedge: This ___ suggests a trend.", "choices": ["definitely", "arguably", "obviously", "never"], "correct_index": 1},
        {"prompt": "The proposal, ___ ambitious, lacks funding.", "choices": ["while", "despite", "because", "unless"], "correct_index": 0},
        {"prompt": "Pick the precise verb: The findings ___ the theory.", "choices": ["say", "tell", "corroborate", "speak"], "correct_index": 2},
    ],
    "C2": [
        {"prompt": "Were it not for her help, the plan ___ failed.", "choices": ["will have", "would have", "had", "has"], "correct_index": 1},
        {"prompt": "Choose the most nuanced: a ___ distinction", "choices": ["big", "subtle", "loud", "fast"], "correct_index": 1},
        {"prompt": "Not only ___ late, but he also forgot.", "choices": ["he was", "was he", "he is", "is he"], "correct_index": 1},
        {"prompt": "Pick the idiom: to ___ the bullet", "choices": ["eat", "bite", "throw", "drop"], "correct_index": 1},
    ],
}


def _parse(raw: str) -> list[dict] | None:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip())
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1:
        return None
    try:
        data = json.loads(text[s : e + 1])
    except json.JSONDecodeError:
        return None
    qs = data.get("questions")
    return qs if isinstance(qs, list) and qs else None


async def _questions_for(level: str) -> list[dict]:
    if is_claude_configured():
        try:
            raw = await generate_llm_json(
                f"Write the CEFR {level} level-check now.", system=_SYSTEM, temperature=0.4, max_output_tokens=8192
            )
            parsed = _parse(raw)
            if parsed:
                out = []
                for q in parsed[:6]:
                    choices = [str(c) for c in (q.get("choices") or [])][:4]
                    ci = q.get("correct_index")
                    if len(choices) == 4 and isinstance(ci, int) and 0 <= ci <= 3 and q.get("prompt"):
                        out.append({"prompt": str(q["prompt"]), "choices": choices, "correct_index": ci})
                if len(out) >= 4:
                    return out
        except Exception as exc:
            logger.warning("Promotion test AI generation failed for %s: %s", level, exc)
    return _CURATED.get(level, _CURATED["A1"])


def _cleanup() -> None:
    now = time.time()
    for k in [k for k, v in _tests.items() if v[0] < now]:
        _tests.pop(k, None)


async def build_promotion_test(db: AsyncSession, *, student_id: int) -> dict:
    language = await get_default_language(db)
    level, _ = await _current_level(db, student_id=student_id, language_id=language.id)
    cur_rank = CEFR_RANK.get(LanguageLevel(level), 1)
    next_level = RANK_CEFR.get(cur_rank + 1)
    eligible = next_level is not None
    if not eligible:
        return {
            "test_id": "",
            "level": level,
            "pass_ratio": PASS_RATIO,
            "questions": [],
            "eligible": False,
            "next_level": None,
        }

    questions = await _questions_for(level)
    test_id = uuid.uuid4().hex
    _cleanup()
    _tests[test_id] = (time.time() + _TEST_TTL, level, [q["correct_index"] for q in questions])
    return {
        "test_id": test_id,
        "level": level,
        "pass_ratio": PASS_RATIO,
        "questions": [{"id": i, "prompt": q["prompt"], "choices": q["choices"]} for i, q in enumerate(questions)],
        "eligible": True,
        "next_level": next_level.value,
    }


async def grade_promotion_test(db: AsyncSession, *, student_id: int, test_id: str, answers: dict) -> dict:
    language = await get_default_language(db)
    entry = _tests.get(test_id)
    if not entry or entry[0] < time.time():
        await record_activity(
            db,
            student_id=student_id,
            language_id=language.id,
            event_type="promotion_test_attempt",
            skill=LanguageSkill.speaking,
            payload_json={"passed": False, "promoted": False, "expired": True, "test_id": test_id},
        )
        return {"score_percent": 0, "correct": 0, "total": 0, "passed": False, "promoted": False, "new_level": None, "expired": True}

    _, level, key = entry
    total = len(key)
    correct = sum(1 for i, ci in enumerate(key) if int(answers.get(str(i), answers.get(i, -1))) == ci)
    score = round(correct / total * 100) if total else 0
    passed = total > 0 and (correct / total) >= PASS_RATIO

    promoted = False
    new_level = level
    if passed:
        promoted, new_level = await _promote(db, student_id=student_id, language_id=language.id, level=level)
    _tests.pop(test_id, None)

    await record_activity(
        db,
        student_id=student_id,
        language_id=language.id,
        event_type="promotion_test_attempt",
        skill=LanguageSkill.speaking,
        payload_json={
            "passed": passed,
            "promoted": promoted,
            "expired": False,
            "test_id": test_id,
            "level": level,
            "new_level": new_level,
            "score_percent": score,
            "correct": correct,
            "total": total,
        },
    )

    return {
        "score_percent": score,
        "correct": correct,
        "total": total,
        "passed": passed,
        "promoted": promoted,
        "new_level": new_level,
        "expired": False,
    }


async def _promote(db: AsyncSession, *, student_id: int, language_id: int, level: str) -> tuple[bool, str]:
    """Mark current-level objectives mastered and advance the speaking level."""
    now = datetime.now(timezone.utc)
    objectives = await get_level_curriculum(level)
    obj_ids = [o["id"] for o in objectives]
    if obj_ids:
        existing = await db.execute(
            select(LanguageCurriculumProgress).where(
                LanguageCurriculumProgress.student_id == student_id,
                LanguageCurriculumProgress.objective_id.in_(obj_ids),
            )
        )
        by_id = {r.objective_id: r for r in existing.scalars().all()}
        for oid in obj_ids:
            row = by_id.get(oid)
            if row is None:
                row = LanguageCurriculumProgress(student_id=student_id, language_id=language_id, objective_id=oid)
                db.add(row)
            row.status = "mastered"
            row.mastered_at = now

    new_level = level
    cur_rank = CEFR_RANK.get(LanguageLevel(level), 1)
    promoted = cur_rank < 6
    if promoted:
        nxt = RANK_CEFR[cur_rank + 1]
        nxt_rank = CEFR_RANK[nxt]
        analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
        if analytics is None:
            analytics = LanguageAnalytics(student_id=student_id, language_id=language_id)
            db.add(analytics)
        # The level-up test confirms mastery of the current (bottleneck) level, so raise every
        # skill still at/below it to the next level (skills already ahead are left untouched).
        for attr in ("reading_level", "listening_level", "writing_level", "speaking_level"):
            cur = getattr(analytics, attr)
            cur_r = CEFR_RANK.get(cur, 0) if cur else 0
            if cur_r < nxt_rank:
                setattr(analytics, attr, nxt)
        # Keep adaptive-difficulty state in sync so it does not immediately pull skills back down.
        from app.models.language.adaptive import LanguageSkillLevelState

        states = await db.execute(
            select(LanguageSkillLevelState).where(
                LanguageSkillLevelState.student_id == student_id,
                LanguageSkillLevelState.language_id == language_id,
            )
        )
        for st in states.scalars().all():
            if CEFR_RANK.get(st.current_level, 0) < nxt_rank:
                st.current_level = nxt
                st.consecutive_pass_count = 0
                st.consecutive_fail_count = 0
                st.last_level_change_at = now
        new_level = nxt.value
    await db.flush()
    return promoted, new_level
