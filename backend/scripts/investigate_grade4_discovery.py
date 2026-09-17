"""Investigate Grade 4 student / teacher course discovery mismatch."""
from __future__ import annotations

import json
from sqlalchemy import create_engine, text

from app.core.config import get_settings

def j(rows):
    return json.dumps([dict(r._mapping) for r in rows], ensure_ascii=False, indent=2, default=str)


def main():
    e = create_engine(get_settings().DATABASE_URL_SYNC)
    with e.connect() as c:
        print("=" * 70)
        print("1. TEACHER PROFILES (all)")
        print("=" * 70)
        r = c.execute(text("""
            SELECT tp.id AS teacher_profile_id, tp.user_id, tp.full_name, tp.active,
                   tp.setup_completed_at IS NOT NULL AS setup_done,
                   u.email, u.role::text AS role
            FROM teacher_profiles tp
            JOIN users u ON u.id = tp.user_id
            ORDER BY tp.id DESC
        """))
        print(j(r))

        print("\n" + "=" * 70)
        print("2. GRADE 4 SUBJECTS (catalog)")
        print("=" * 70)
        r = c.execute(text("""
            SELECT id, name_ar, slug, grade, is_active
            FROM subjects WHERE grade = 4 ORDER BY name_ar
        """))
        print(j(r))

        print("\n" + "=" * 70)
        print("3. ALL COURSES (recent, with subject + teacher)")
        print("=" * 70)
        r = c.execute(text("""
            SELECT c.id, c.title, c.grade AS course_grade, c.is_published, c.is_active,
                   c.subject_id, s.name_ar AS subject_name, s.grade AS subject_grade, s.slug,
                   c.teacher_profile_id, tp.full_name AS teacher_name, tp.active AS teacher_active,
                   u.email AS teacher_email,
                   (SELECT COUNT(*) FROM lessons l WHERE l.course_id = c.id) AS lesson_count
            FROM courses c
            JOIN subjects s ON s.id = c.subject_id
            JOIN teacher_profiles tp ON tp.id = c.teacher_profile_id
            JOIN users u ON u.id = tp.user_id
            ORDER BY c.id DESC
            LIMIT 20
        """))
        print(j(r))

        print("\n" + "=" * 70)
        print("4. GRADE 4 COURSES — discovery filter breakdown")
        print("=" * 70)
        r = c.execute(text("""
            SELECT c.id, c.title, c.grade, c.is_published, c.is_active,
                   s.id AS subject_id, s.name_ar, s.grade AS subject_grade,
                   tp.id AS tp_id, tp.full_name, tp.active AS teacher_active,
                   u.email,
                   CASE WHEN c.grade = 4 THEN 'ok' ELSE 'FAIL course.grade' END AS grade_match,
                   CASE WHEN s.grade = 4 THEN 'ok' ELSE 'FAIL subject.grade' END AS subject_grade_match,
                   CASE WHEN c.is_published THEN 'ok' ELSE 'FAIL not published' END AS pub,
                   CASE WHEN c.is_active THEN 'ok' ELSE 'FAIL not active' END AS act,
                   CASE WHEN tp.active THEN 'ok' ELSE 'FAIL teacher inactive' END AS teacher_act
            FROM courses c
            JOIN subjects s ON s.id = c.subject_id
            JOIN teacher_profiles tp ON tp.id = c.teacher_profile_id
            JOIN users u ON u.id = tp.user_id
            WHERE c.grade = 4 OR s.grade = 4 OR s.name_ar ILIKE '%علوم%' OR c.title ILIKE '%علوم%'
            ORDER BY c.id DESC
        """))
        print(j(r))

        print("\n" + "=" * 70)
        print("5. STUDENTS with grade 4 in student_profiles")
        print("=" * 70)
        r = c.execute(text("""
            SELECT u.id, u.email, u.name, sp.grade, sp.onboarding_step::text,
                   sp.onboarding_completed_at IS NOT NULL AS onboarding_done
            FROM users u
            JOIN student_profiles sp ON sp.user_id = u.id
            WHERE u.role::text = 'student' AND sp.grade = 4
            ORDER BY u.id
        """))
        print(j(r))

        print("\n" + "=" * 70)
        print("6. SIMULATE GET /catalog/teachers?grade=4&subject_id=<science>")
        print("=" * 70)
        sci = c.execute(text("""
            SELECT id, name_ar, slug FROM subjects
            WHERE grade = 4 AND (slug ILIKE '%science%' OR name_ar ILIKE '%علوم%')
        """)).fetchall()
        print("Science-like subjects:", [dict(x._mapping) for x in sci])
        for sub in sci:
            sid = sub.id
            r = c.execute(text("""
                SELECT DISTINCT tp.id, tp.full_name, tp.active, c.id AS course_id,
                       c.is_published, c.is_active, c.grade
                FROM teacher_profiles tp
                JOIN users u ON u.id = tp.user_id
                JOIN courses c ON c.teacher_profile_id = tp.id
                WHERE tp.active = true
                  AND u.role::text = 'teacher'
                  AND c.subject_id = :sid
                  AND c.grade = 4
                  AND c.is_active = true
                  AND c.is_published = true
            """), {"sid": sid})
            rows = r.fetchall()
            print(f"\n  subject_id={sid} ({sub.name_ar}): {len(rows)} teachers")
            for row in rows:
                print("   ", dict(row._mapping))

        print("\n" + "=" * 70)
        print("7. RECENT LESSONS (grade 4 / science)")
        print("=" * 70)
        r = c.execute(text("""
            SELECT l.id, l.title, l.status::text, l.grade, l.subject, l.course_id,
                   c.is_published AS course_published, c.grade AS course_grade,
                   s.name_ar AS course_subject_name
            FROM lessons l
            LEFT JOIN courses c ON c.id = l.course_id
            LEFT JOIN subjects s ON s.id = c.subject_id
            WHERE l.grade = 4 OR c.grade = 4 OR l.subject ILIKE '%علوم%' OR s.name_ar ILIKE '%علوم%'
            ORDER BY l.id DESC
            LIMIT 15
        """))
        print(j(r))

        print("\n" + "=" * 70)
        print("8. ORPHAN: lessons with course_id NULL or missing course")
        print("=" * 70)
        r = c.execute(text("""
            SELECT l.id, l.title, l.grade, l.subject, l.course_id, l.teacher_id, l.status::text
            FROM lessons l
            WHERE l.course_id IS NULL
               OR NOT EXISTS (SELECT 1 FROM courses c WHERE c.id = l.course_id)
            ORDER BY l.id DESC
            LIMIT 10
        """))
        print(j(r))


if __name__ == "__main__":
    main()
