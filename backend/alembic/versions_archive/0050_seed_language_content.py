"""Seed English language learning content from generated JSON seed files.

Revision ID: 0050_seed_language_content
Revises: 0049_placement_listening_stems

Seed files live at: backend/alembic/seeds/language_content/<skill>_<level>.json
(e.g. reading_A1.json). Missing/invalid files are logged and skipped — never fatal.
"""

import json
import logging
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0050_seed_language_content"
down_revision = "0049_placement_listening_stems"
branch_labels = None
depends_on = None

logger = logging.getLogger("alembic.runtime.migration.0050_seed")

SKILLS = ["reading", "listening", "writing", "speaking"]
LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
CONTENT_TYPE = {
    "reading": "lesson",
    "listening": "lesson",
    "writing": "writing_prompt",
    "speaking": "speaking_prompt",
}
SEED_DIR = Path(__file__).parent.parent / "seeds" / "language_content"


def _validate(item, skill: str, level: str) -> tuple[bool, str]:
    if not isinstance(item, dict):
        return False, "item is not an object"
    if item.get("skill") != skill:
        return False, f"skill mismatch (got {item.get('skill')!r}, expected {skill!r})"
    if item.get("level") != level:
        return False, f"level mismatch (got {item.get('level')!r}, expected {level!r})"
    if not str(item.get("title") or "").strip():
        return False, "empty title"
    if not str(item.get("title_ar") or "").strip():
        return False, "empty title_ar"
    if item.get("content_type") != CONTENT_TYPE[skill]:
        return False, f"content_type mismatch (expected {CONTENT_TYPE[skill]!r})"
    body = item.get("body_json")
    if not isinstance(body, dict):
        return False, "body_json is not an object"

    if skill in ("reading", "listening"):
        questions = body.get("questions")
        if not isinstance(questions, list) or len(questions) < 1:
            return False, "body_json.questions must be a list with >= 1 item"
        for qi, q in enumerate(questions):
            if not isinstance(q, dict):
                return False, f"question {qi} is not an object"
            choices = q.get("choices")
            if not isinstance(choices, list) or len(choices) != 4:
                return False, f"question {qi} must have exactly 4 choices"
            ci = q.get("correct_index")
            if not isinstance(ci, int) or ci not in (0, 1, 2, 3):
                return False, f"question {qi} correct_index must be 0, 1, 2 or 3"
    elif skill == "writing":
        if not str(body.get("prompt") or "").strip():
            return False, "empty body_json.prompt"
        if not isinstance(body.get("min_words"), int):
            return False, "body_json.min_words must be an integer"
    elif skill == "speaking":
        if not str(body.get("prompt") or "").strip():
            return False, "empty body_json.prompt"
        if not isinstance(body.get("min_seconds"), int):
            return False, "body_json.min_seconds must be an integer"
    return True, ""


def _load(path: Path) -> list | None:
    if not path.exists():
        logger.warning("0050 seed: missing file %s — skipping", path.name)
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("0050 seed: invalid JSON in %s: %s", path.name, exc)
        return None
    if not isinstance(data, list):
        logger.error("0050 seed: %s is not a JSON array — skipping", path.name)
        return None
    return data


def upgrade() -> None:
    conn = op.get_bind()
    row = conn.execute(sa.text("SELECT id FROM languages WHERE code = 'en' LIMIT 1")).fetchone()
    if not row:
        logger.error("0050 seed: no language with code='en' — skipping content seed entirely")
        return
    lang_id = row[0]

    total_ins = total_skip = total_inv = 0
    for skill in SKILLS:
        for level in LEVELS:
            items = _load(SEED_DIR / f"{skill}_{level}.json")
            if items is None:
                continue
            ins = skip = inv = 0
            for i, item in enumerate(items):
                ok, reason = _validate(item, skill, level)
                if not ok:
                    inv += 1
                    logger.warning("0050 seed invalid [%s][%s] idx=%d: %s", skill, level, i, reason)
                    continue
                title = str(item["title"]).strip()
                exists = conn.execute(
                    sa.text(
                        "SELECT 1 FROM language_content_items "
                        "WHERE language_id = :lang "
                        "AND skill = cast(:skill as language_skill) "
                        "AND level = cast(:level as language_level) "
                        "AND title = :title LIMIT 1"
                    ),
                    {"lang": lang_id, "skill": skill, "level": level, "title": title},
                ).fetchone()
                if exists:
                    skip += 1
                    continue
                body = dict(item["body_json"])
                title_ar = str(item.get("title_ar") or "").strip()
                if title_ar:
                    body.setdefault("title_ar", title_ar)
                conn.execute(
                    sa.text(
                        "INSERT INTO language_content_items "
                        "(language_id, skill, level, content_type, title, body_json, sort_order, is_published, created_at) "
                        "VALUES (:lang, cast(:skill as language_skill), cast(:level as language_level), "
                        ":content_type, :title, cast(:body_json as jsonb), :sort_order, true, now())"
                    ),
                    {
                        "lang": lang_id,
                        "skill": skill,
                        "level": level,
                        "content_type": CONTENT_TYPE[skill],
                        "title": title,
                        "body_json": json.dumps(body, ensure_ascii=False),
                        "sort_order": int(item.get("sort_order") or 0),
                    },
                )
                ins += 1
            total_ins += ins
            total_skip += skip
            total_inv += inv
            logger.warning("0050 seed [%s][%s]: inserted=%d skipped=%d invalid=%d", skill, level, ins, skip, inv)
    logger.warning("0050 seed TOTAL: inserted=%d skipped=%d invalid=%d", total_ins, total_skip, total_inv)


def downgrade() -> None:
    conn = op.get_bind()
    row = conn.execute(sa.text("SELECT id FROM languages WHERE code = 'en' LIMIT 1")).fetchone()
    if not row:
        logger.warning("0050 seed downgrade: no language with code='en' — nothing to do")
        return
    lang_id = row[0]

    titles: list[str] = []
    for skill in SKILLS:
        for level in LEVELS:
            path = SEED_DIR / f"{skill}_{level}.json"
            if not path.exists():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            for item in data if isinstance(data, list) else []:
                if isinstance(item, dict):
                    t = str(item.get("title") or "").strip()
                    if t:
                        titles.append(t)

    if not titles:
        logger.warning("0050 seed downgrade: no seed files on disk — nothing deleted")
        return

    batch = 200
    for i in range(0, len(titles), batch):
        chunk = titles[i : i + batch]
        conn.execute(
            sa.text("DELETE FROM language_content_items WHERE language_id = :lang AND title = ANY(:titles)"),
            {"lang": lang_id, "titles": chunk},
        )
