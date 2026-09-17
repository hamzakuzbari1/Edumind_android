"""Repair student_profiles personalization columns from migration 0037.

Safe to re-run: only adds columns that are missing.
Migration: alembic/versions/0037_student_personalization_fields.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text

from app.core.config import get_settings


def _column_exists(conn, table: str, column: str) -> bool:
    return conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c LIMIT 1"
        ),
        {"t": table, "c": column},
    ).fetchone() is not None


def main() -> None:
    engine = create_engine(get_settings().DATABASE_URL.replace("+asyncpg", ""))
    added: list[str] = []
    with engine.begin() as conn:
        specs = [
            ("age", "ALTER TABLE student_profiles ADD COLUMN age INTEGER"),
            (
                "learning_style",
                "ALTER TABLE student_profiles ADD COLUMN learning_style VARCHAR(32) "
                "NOT NULL DEFAULT 'theoretical'",
            ),
            (
                "future_goal",
                "ALTER TABLE student_profiles ADD COLUMN future_goal VARCHAR(32) "
                "NOT NULL DEFAULT 'undecided'",
            ),
            (
                "preferred_explanation_style",
                "ALTER TABLE student_profiles ADD COLUMN preferred_explanation_style VARCHAR(32) "
                "NOT NULL DEFAULT 'normal'",
            ),
            (
                "hobbies_json",
                "ALTER TABLE student_profiles ADD COLUMN hobbies_json TEXT NOT NULL DEFAULT '[]'",
            ),
        ]
        for col, ddl in specs:
            if not _column_exists(conn, "student_profiles", col):
                conn.execute(text(ddl))
                added.append(col)
    if added:
        print(f"Added student_profiles columns: {', '.join(added)}")
    else:
        print("student_profiles personalization columns already present — no changes")


if __name__ == "__main__":
    main()
