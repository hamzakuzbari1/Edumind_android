"""Apply migration 0044 when alembic chain is mixed. Safe to re-run."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text

from app.core.config import get_settings


def _table_exists(conn, table: str) -> bool:
    return conn.execute(
        text("SELECT 1 FROM information_schema.tables WHERE table_name = :t LIMIT 1"),
        {"t": table},
    ).fetchone() is not None


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
    with engine.begin() as conn:
        if not _table_exists(conn, "language_student_achievements"):
            conn.execute(
                text(
                    "CREATE TABLE language_student_achievements ("
                    "id SERIAL PRIMARY KEY, student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, "
                    "language_id INTEGER NOT NULL REFERENCES languages(id) ON DELETE CASCADE, "
                    "achievement_key VARCHAR(64) NOT NULL, unlocked_at TIMESTAMPTZ NOT NULL DEFAULT now(), "
                    "CONSTRAINT uq_language_student_achievement UNIQUE (student_id, language_id, achievement_key))"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX ix_language_student_achievements_student "
                    "ON language_student_achievements (student_id, language_id)"
                )
            )
        if not _table_exists(conn, "language_scenario_progress"):
            conn.execute(
                text(
                    "CREATE TABLE language_scenario_progress ("
                    "id SERIAL PRIMARY KEY, student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, "
                    "language_id INTEGER NOT NULL REFERENCES languages(id) ON DELETE CASCADE, "
                    "scenario_key VARCHAR(64) NOT NULL, scenario_id INTEGER, status VARCHAR(16) NOT NULL DEFAULT 'not_started', "
                    "completion_count INTEGER NOT NULL DEFAULT 0, best_score INTEGER NOT NULL DEFAULT 0, "
                    "best_scores_json JSONB, last_played_at TIMESTAMPTZ, first_completed_at TIMESTAMPTZ, "
                    "CONSTRAINT uq_language_scenario_progress_key UNIQUE (student_id, language_id, scenario_key))"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX ix_language_scenario_progress_student "
                    "ON language_scenario_progress (student_id, language_id)"
                )
            )
        if not _column_exists(conn, "language_analytics", "statistics_json"):
            conn.execute(text("ALTER TABLE language_analytics ADD COLUMN statistics_json JSONB"))
    print("Applied 0044 language analytics achievements schema")


if __name__ == "__main__":
    main()
