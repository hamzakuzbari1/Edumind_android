"""Diagnose empty GET /student/languages/reading — run from backend/: python scripts/investigate_reading_lessons.py"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

from app.core.config import get_settings

settings = get_settings()
url = settings.DATABASE_URL_SYNC or settings.sync_database_url
engine = create_engine(url)


def main() -> None:
    with engine.connect() as conn:
        print("=== Alembic revision ===")
        try:
            rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            print(f"  current: {rev}")
        except Exception as e:
            print(f"  alembic_version error: {e}")

        print("\n=== languages ===")
        langs = conn.execute(text("SELECT id, code FROM languages")).fetchall()
        for row in langs:
            print(f"  id={row[0]} code={row[1]}")

        print("\n=== language_content_items totals ===")
        total = conn.execute(text("SELECT COUNT(*) FROM language_content_items")).scalar()
        print(f"  total rows: {total}")

        print("\n=== published reading by level ===")
        rows = conn.execute(
            text(
                """
                SELECT level::text, COUNT(*)
                FROM language_content_items
                WHERE skill::text = 'reading' AND is_published = true
                GROUP BY level
                ORDER BY level
                """
            )
        ).fetchall()
        if not rows:
            print("  (none)")
        for lv, cnt in rows:
            print(f"  {lv}: {cnt}")

        print("\n=== seed_key sample (c1_*) ===")
        seeds = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM language_content_items
                WHERE body_json->>'seed_key' LIKE 'c1_%'
                """
            )
        ).scalar()
        print(f"  c1 seed rows: {seeds}")

        print("\n=== attempt_count column (migration 0010) ===")
        try:
            conn.execute(text("SELECT attempt_count FROM language_reading_progress LIMIT 1"))
            print("  language_reading_progress.attempt_count: present")
        except Exception as e:
            conn.rollback()
            print(f"  missing: {e}")

        print("\n=== students with language analytics (reading_level) ===")
        analytics = conn.execute(
            text(
                """
                SELECT a.student_id, u.email, a.reading_level::text, a.listening_level::text
                FROM language_analytics a
                LEFT JOIN users u ON u.id = a.student_id
                ORDER BY a.student_id
                LIMIT 20
                """
            )
        ).fetchall()
        if not analytics:
            print("  (no language_analytics rows)")
        for row in analytics:
            print(f"  student_id={row[0]} email={row[1]} reading={row[2]} listening={row[3]}")

        print("\n=== placement completed profiles ===")
        profs = conn.execute(
            text(
                """
                SELECT p.student_id, u.email, p.placement_completed_at IS NOT NULL AS done
                FROM language_student_profiles p
                LEFT JOIN users u ON u.id = p.student_id
                LIMIT 20
                """
            )
        ).fetchall()
        for row in profs:
            print(f"  student_id={row[0]} email={row[1]} placement_done={row[2]}")

        # Simulate API filter for each analytics reading level
        print("\n=== simulated list_lessons counts per student reading_level ===")
        for row in analytics:
            sid, _, reading_level, _ = row
            if not reading_level:
                reading_level = "A1"
            cnt = conn.execute(
                text(
                    """
                    SELECT COUNT(*) FROM language_content_items c
                    JOIN languages l ON l.id = c.language_id AND l.code = 'en'
                    WHERE c.skill::text = 'reading'
                      AND c.level::text = :level
                      AND c.is_published = true
                    """
                ),
                {"level": reading_level},
            ).scalar()
            print(f"  student_id={sid} reading_level={reading_level} -> matching lessons: {cnt}")


if __name__ == "__main__":
    main()
