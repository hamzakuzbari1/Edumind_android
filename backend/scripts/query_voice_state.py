import json
from pathlib import Path

import psycopg2

out = Path(__file__).resolve().parent / "voice_state_out.json"

conn = psycopg2.connect(host="localhost", port=5432, user="postgres", password="changeme", dbname="eduspark")
cur = conn.cursor()

cur.execute(
    """
    SELECT u.id, u.email, tp.id, tvs.id, tvs.processing_status, tvs.storage_path, tvs.duration_seconds
    FROM users u
    JOIN teacher_profiles tp ON tp.user_id = u.id
    LEFT JOIN teacher_voice_samples tvs ON tvs.teacher_profile_id = tp.id
    WHERE u.role = 'teacher'
    ORDER BY u.id, tvs.uploaded_at DESC NULLS LAST
    """
)
teachers = cur.fetchall()

cur.execute(
    """
    SELECT l.id, l.title, l.teacher_id, l.status::text, c.id, tp.user_id
    FROM lessons l
    JOIN courses c ON c.id = l.course_id
    JOIN teacher_profiles tp ON tp.id = c.teacher_profile_id
    WHERE l.status::text = 'processed'
    ORDER BY l.id DESC
    LIMIT 10
    """
)
lessons = cur.fetchall()

cur.execute("SELECT id, email FROM users WHERE role = 'student' ORDER BY id LIMIT 10")
students = cur.fetchall()

cur.execute(
    """
    SELECT cm.id, cm.lesson_id, cm.role, LEFT(cm.content, 200), cm.created_at
    FROM chat_messages cm
    WHERE cm.role = 'ai' AND cm.content LIKE '%EDUSPARK_AUDIO%'
    ORDER BY cm.id DESC
    LIMIT 5
    """
)
audio_msgs = cur.fetchall()

conn.close()
out.write_text(
    json.dumps(
        {"teachers": teachers, "lessons": lessons, "students": students, "audio_messages": audio_msgs},
        ensure_ascii=False,
        indent=2,
        default=str,
    ),
    encoding="utf-8",
)
print(str(out))
