"""Validate the language-content seed JSON files WITHOUT touching the database.

Mirrors the validation in alembic/versions/0050_seed_language_content.py. Exits 1 if any
item is invalid, 0 if all valid (or if there are no seed files yet).
"""

import json
import sys
from pathlib import Path

SKILLS = ["reading", "listening", "writing", "speaking"]
LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
CONTENT_TYPE = {
    "reading": "lesson",
    "listening": "lesson",
    "writing": "writing_prompt",
    "speaking": "speaking_prompt",
}
SEED_DIR = Path(__file__).resolve().parent.parent / "alembic" / "seeds" / "language_content"


def validate(item, skill: str, level: str) -> tuple[bool, str]:
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


def main() -> int:
    files = sorted(SEED_DIR.glob("*.json")) if SEED_DIR.exists() else []
    if not files:
        print("No seed files found")
        return 0

    total_items = total_valid = total_invalid = 0
    for skill in SKILLS:
        for level in LEVELS:
            path = SEED_DIR / f"{skill}_{level}.json"
            if not path.exists():
                continue
            try:
                items = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                print(f"[{skill:<9}][{level}] INVALID FILE: {exc}")
                total_invalid += 1
                continue
            if not isinstance(items, list):
                print(f"[{skill:<9}][{level}] INVALID FILE: not a JSON array")
                total_invalid += 1
                continue

            valid = invalid = 0
            problems: list[tuple[int, str]] = []
            for i, item in enumerate(items):
                ok, reason = validate(item, skill, level)
                if ok:
                    valid += 1
                else:
                    invalid += 1
                    problems.append((i, reason))
            total_items += len(items)
            total_valid += valid
            total_invalid += invalid
            print(f"[{skill:<9}][{level}] items={len(items):<3} valid={valid:<3} invalid={invalid}")
            for idx, reason in problems:
                print(f"  INVALID item {idx}: {reason}")

    print(f"\nTOTAL  items={total_items}  valid={total_valid}  invalid={total_invalid}")
    return 1 if total_invalid else 0


if __name__ == "__main__":
    sys.exit(main())
