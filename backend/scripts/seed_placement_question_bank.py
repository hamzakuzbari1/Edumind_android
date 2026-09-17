"""Seed the reviewed placement question bank from existing language content.

Safety:
- Default mode is dry-run. Nothing is written unless --apply is passed.
- Requires the 0003_placement_qbank migration/table to exist.
- Idempotent by stable_key: existing rows are updated, missing rows are inserted.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, text

from app.db.session import AsyncSessionLocal
from app.models.language.catalog import Language
from app.models.language.content import LanguageContentItem
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.models.language.question_bank import LanguagePlacementQuestionBankItem


LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]


@dataclass(frozen=True)
class BankSeed:
    stable_key: str
    language_id: int
    skill: str
    level: LanguageLevel
    prompt_text: str
    question_type: str = "mcq"
    passage: str | None = None
    situation: str | None = None
    options_json: list[str] | None = None
    correct_index: int | None = None
    explanation: str | None = None
    subskill: str | None = None
    boundary_low_level: LanguageLevel | None = None
    boundary_high_level: LanguageLevel | None = None
    body_json: dict | None = None
    source: str = "content_seed"


GRAMMAR_VOCAB_ANCHORS: list[dict] = [
    {
        "key": "grammar_vocab:A1:be-present",
        "level": "A1",
        "subskill": "be_present",
        "prompt": "Choose the correct sentence.",
        "options": ["She am a student.", "She is a student.", "She are a student.", "She be a student."],
        "correct": 1,
        "explanation": "Use 'is' with she/he/it in the present simple.",
    },
    {
        "key": "grammar_vocab:A1:basic-place",
        "level": "A1",
        "subskill": "prepositions_place",
        "prompt": "Complete the sentence: The book is ___ the table.",
        "options": ["on", "at", "to", "of"],
        "correct": 0,
        "explanation": "Use 'on' when something is physically on top of a surface.",
    },
    {
        "key": "grammar_vocab:A2:past-simple",
        "level": "A2",
        "subskill": "past_simple",
        "prompt": "Choose the correct sentence.",
        "options": ["I go to the cinema yesterday.", "I went to the cinema yesterday.", "I gone to the cinema yesterday.", "I goes to the cinema yesterday."],
        "correct": 1,
        "explanation": "Use the past simple form 'went' with a finished past time like yesterday.",
    },
    {
        "key": "grammar_vocab:A2:comparative",
        "level": "A2",
        "subskill": "comparatives",
        "prompt": "Complete the sentence: This bag is ___ than that one.",
        "options": ["heavy", "heavier", "more heavy", "heaviest"],
        "correct": 1,
        "explanation": "For many short adjectives, add -er to make the comparative.",
    },
    {
        "key": "grammar_vocab:B1:present-perfect",
        "level": "B1",
        "subskill": "present_perfect",
        "prompt": "Choose the best option: I ___ this movie before.",
        "options": ["saw", "have seen", "am seeing", "was seeing"],
        "correct": 1,
        "explanation": "Use present perfect for life experience without a specific finished time.",
    },
    {
        "key": "grammar_vocab:B1:collocation-decision",
        "level": "B1",
        "subskill": "collocation",
        "prompt": "Choose the natural collocation.",
        "options": ["make a decision", "do a decision", "take a decision about homework", "create a decision"],
        "correct": 0,
        "explanation": "In general English, 'make a decision' is the standard collocation.",
    },
    {
        "key": "grammar_vocab:B2:conditionals",
        "level": "B2",
        "subskill": "conditionals",
        "prompt": "Choose the best sentence.",
        "options": ["If I would know, I tell you.", "If I knew, I would tell you.", "If I know, I would told you.", "If I knew, I will tell you."],
        "correct": 1,
        "explanation": "Use past simple + would for an unreal present conditional.",
    },
    {
        "key": "grammar_vocab:B2:linking-contrast",
        "level": "B2",
        "subskill": "discourse_markers",
        "prompt": "Complete the sentence: The plan is expensive; ___, it could save time later.",
        "options": ["because", "however", "so that", "unless"],
        "correct": 1,
        "explanation": "Use 'however' to introduce a contrast.",
    },
    {
        "key": "grammar_vocab:C1:inversion",
        "level": "C1",
        "subskill": "inversion",
        "prompt": "Choose the most natural advanced sentence.",
        "options": ["Rarely I have seen such dedication.", "Rarely have I seen such dedication.", "Rarely I saw such dedication.", "Rarely have seen I such dedication."],
        "correct": 1,
        "explanation": "After negative or limiting adverbs like 'rarely', use inversion: auxiliary + subject.",
    },
    {
        "key": "grammar_vocab:C1:nuance",
        "level": "C1",
        "subskill": "lexical_nuance",
        "prompt": "Which word best completes the sentence? The evidence was too ___ to support a firm conclusion.",
        "options": ["conclusive", "tenuous", "obvious", "inevitable"],
        "correct": 1,
        "explanation": "'Tenuous' means weak or not strongly supported.",
    },
    {
        "key": "grammar_vocab:C2:hedging",
        "level": "C2",
        "subskill": "academic_hedging",
        "prompt": "Choose the most precise academic sentence.",
        "options": ["This proves the theory is true in every case.", "This may lend support to the theory under certain conditions.", "This always makes the theory correct.", "This totally confirms all parts of the theory."],
        "correct": 1,
        "explanation": "Advanced academic English often uses careful hedging when evidence is limited.",
    },
    {
        "key": "grammar_vocab:C2:idiomatic-precision",
        "level": "C2",
        "subskill": "idiomatic_precision",
        "prompt": "Choose the sentence with the most natural idiomatic precision.",
        "options": ["The proposal opened a can of worms.", "The proposal opened a box of problems.", "The proposal opened many worms.", "The proposal opened a difficult animal."],
        "correct": 0,
        "explanation": "'Open a can of worms' is the idiom for creating complicated problems.",
    },
]


def _first_valid_question(body: dict | None) -> dict | None:
    for q in (body or {}).get("questions") or []:
        choices = q.get("choices")
        ci = q.get("correct_index")
        if isinstance(choices, list) and len(choices) == 4 and isinstance(ci, int) and 0 <= ci < 4:
            return q
    return None


def _content_seed(row: LanguageContentItem) -> BankSeed | None:
    body = row.body_json or {}
    level = row.level
    if row.skill in (LanguageSkill.reading, LanguageSkill.listening):
        q = _first_valid_question(body)
        if not q:
            return None
        return BankSeed(
            stable_key=f"content:{row.id}",
            language_id=row.language_id,
            skill=row.skill.value,
            level=level,
            subskill=str(q.get("subskill") or "comprehension"),
            prompt_text=str(q.get("stem") or q.get("question") or "").strip(),
            passage=str(body.get("passage") or body.get("text") or "").strip() or None,
            situation=str(body.get("situation") or "").strip() or None,
            options_json=[str(x) for x in (q.get("choices") or [])],
            correct_index=int(q.get("correct_index")),
            explanation=str(q.get("explanation") or "").strip() or None,
            body_json={"content_item_id": row.id, "title": row.title},
        )
    if row.skill == LanguageSkill.writing:
        prompt = str(body.get("prompt") or body.get("text") or row.title or "").strip()
        if not prompt:
            return None
        return BankSeed(
            stable_key=f"content:{row.id}",
            language_id=row.language_id,
            skill="writing_prompt",
            level=level,
            question_type="writing_prompt",
            prompt_text=prompt,
            subskill=str(body.get("subskill") or "writing_task"),
            body_json={"content_item_id": row.id, "min_words": body.get("min_words")},
        )
    if row.skill == LanguageSkill.speaking:
        prompt = str(body.get("prompt") or body.get("text") or row.title or "").strip()
        if not prompt:
            return None
        return BankSeed(
            stable_key=f"content:{row.id}",
            language_id=row.language_id,
            skill="speaking_prompt",
            level=level,
            question_type="speaking_prompt",
            prompt_text=prompt,
            subskill=str(body.get("subskill") or "speaking_task"),
            body_json={"content_item_id": row.id, "min_seconds": body.get("min_seconds")},
        )
    return None


def _anchor_seeds(language_id: int) -> list[BankSeed]:
    out: list[BankSeed] = []
    for item in GRAMMAR_VOCAB_ANCHORS:
        out.append(
            BankSeed(
                stable_key=item["key"],
                language_id=language_id,
                skill="grammar_vocab",
                level=LanguageLevel(item["level"]),
                subskill=item["subskill"],
                prompt_text=item["prompt"],
                options_json=list(item["options"]),
                correct_index=int(item["correct"]),
                explanation=item["explanation"],
                source="starter_anchor",
            )
        )
    return out


async def _table_exists(db) -> bool:
    result = await db.execute(text("SELECT to_regclass('public.language_placement_question_bank_items')"))
    return result.scalar_one_or_none() is not None


async def _language_id(db, code: str) -> int | None:
    return (
        await db.execute(select(Language.id).where(Language.code == code, Language.is_active.is_(True)).limit(1))
    ).scalar_one_or_none()


async def _existing_by_key(db, keys: list[str]) -> dict[str, LanguagePlacementQuestionBankItem]:
    if not keys:
        return {}
    rows = (
        await db.execute(
            select(LanguagePlacementQuestionBankItem).where(LanguagePlacementQuestionBankItem.stable_key.in_(keys))
        )
    ).scalars().all()
    return {r.stable_key: r for r in rows if r.stable_key}


def _apply_seed(row: LanguagePlacementQuestionBankItem, seed: BankSeed) -> None:
    row.language_id = seed.language_id
    row.skill = seed.skill
    row.level = seed.level
    row.boundary_low_level = seed.boundary_low_level
    row.boundary_high_level = seed.boundary_high_level
    row.subskill = seed.subskill
    row.question_type = seed.question_type
    row.prompt_text = seed.prompt_text
    row.passage = seed.passage
    row.situation = seed.situation
    row.options_json = seed.options_json
    row.correct_index = seed.correct_index
    row.explanation = seed.explanation
    row.body_json = seed.body_json
    row.source = seed.source
    row.is_verified = True
    row.is_active = True


async def main() -> int:
    parser = argparse.ArgumentParser(description="Seed placement question bank from existing curated content.")
    parser.add_argument("--language-code", default="en")
    parser.add_argument("--apply", action="store_true", help="Write changes. Default is dry-run.")
    parser.add_argument("--limit-per-skill-level", type=int, default=4)
    parser.add_argument(
        "--include-writing",
        action="store_true",
        help="Also seed legacy writing prompts from language content. Disabled by default; Writing uses its own curated bank.",
    )
    args = parser.parse_args()

    async with AsyncSessionLocal() as db:
        if not await _table_exists(db):
            print("Question-bank table is missing. Run Alembic migration 0003_placement_qbank first.")
            return 1

        language_id = await _language_id(db, args.language_code)
        if language_id is None:
            print(f"Active language {args.language_code!r} not found.")
            return 1

        seeds: list[BankSeed] = []
        skills = [LanguageSkill.reading, LanguageSkill.listening, LanguageSkill.speaking]
        if args.include_writing:
            skills.append(LanguageSkill.writing)
        for skill in skills:
            for level in LEVELS:
                rows = (
                    await db.execute(
                        select(LanguageContentItem)
                        .where(
                            LanguageContentItem.language_id == language_id,
                            LanguageContentItem.skill == skill,
                            LanguageContentItem.level == LanguageLevel(level),
                            LanguageContentItem.is_published.is_(True),
                        )
                        .order_by(LanguageContentItem.sort_order.asc(), LanguageContentItem.id.asc())
                        .limit(max(1, args.limit_per_skill_level))
                    )
                ).scalars().all()
                seeds.extend(seed for row in rows if (seed := _content_seed(row)) is not None)

        seeds.extend(_anchor_seeds(language_id))

        existing = await _existing_by_key(db, [s.stable_key for s in seeds])
        inserts = updates = 0
        if args.apply:
            for seed in seeds:
                row = existing.get(seed.stable_key)
                if row is None:
                    row = LanguagePlacementQuestionBankItem(stable_key=seed.stable_key)
                    db.add(row)
                    inserts += 1
                else:
                    updates += 1
                _apply_seed(row, seed)
            await db.commit()
        else:
            inserts = sum(1 for s in seeds if s.stable_key not in existing)
            updates = len(seeds) - inserts

        mode = "APPLY" if args.apply else "DRY-RUN"
        by_skill: dict[str, int] = {}
        for seed in seeds:
            by_skill[seed.skill] = by_skill.get(seed.skill, 0) + 1
        print(f"{mode}: seeds={len(seeds)} inserts={inserts} updates={updates}")
        for skill, count in sorted(by_skill.items()):
            print(f"  {skill}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
