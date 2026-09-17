"""Inspect PostgreSQL schema vs Alembic migrations 0003–0005 (read-only)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, inspect, text

from app.core.config import get_settings

settings = get_settings()
url = settings.DATABASE_URL_SYNC or settings.SYNC_DATABASE_URL
if not url:
    url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")

engine = create_engine(url)
insp = inspect(engine)

TABLES_0003 = {
    "course_quizzes",
    "course_quiz_questions",
    "course_quiz_attempts",
    "course_quiz_answers",
}
TABLES_0004 = {"teacher_voice_samples"}
TABLES_0005 = {
    "media_objects",
    "audit_logs",
    "auth_sessions",
    "student_grade_reports",
    "roles",
    "user_roles",
    "course_analytics",
    "teacher_analytics",
    "student_analytics",
    "ai_jobs",
}
COLUMNS_0005 = {
    "notifications": ["payload"],
    "lesson_assets": ["media_object_id", "mime_type", "file_size_bytes", "sort_order"],
}

report: dict = {}

with engine.connect() as conn:
    version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    tables = set(insp.get_table_names())

    enum_vals = conn.execute(
        text(
            """
            SELECT e.enumlabel
            FROM pg_type t
            JOIN pg_enum e ON t.oid = e.enumtypid
            WHERE t.typname = 'lessonassettype'
            ORDER BY e.enumsortorder
            """
        )
    ).fetchall()
    enum_labels = [r[0] for r in enum_vals]

    constraints = conn.execute(
        text(
            """
            SELECT conname FROM pg_constraint
            WHERE conrelid = 'lesson_assets'::regclass
              AND conname = 'uq_lesson_asset_type'
            """
        )
    ).fetchall()

    report = {
        "alembic_version": version,
        "table_count": len(tables),
        "0003": {t: t in tables for t in sorted(TABLES_0003)},
        "0004": {t: t in tables for t in sorted(TABLES_0004)},
        "0005_tables": {t: t in tables for t in sorted(TABLES_0005)},
        "0005_columns": {},
        "lessonassettype": enum_labels,
        "uq_lesson_asset_type_present": len(constraints) > 0,
    }

    for table, cols in COLUMNS_0005.items():
        if table not in tables:
            report["0005_columns"][table] = {c: False for c in cols}
            continue
        existing = {c["name"] for c in insp.get_columns(table)}
        report["0005_columns"][table] = {c: c in existing for c in cols}

    report["roles_row_count"] = (
        conn.execute(text("SELECT COUNT(*) FROM roles")).scalar() if "roles" in tables else 0
    )

print(json.dumps(report, indent=2))
