"""One-off: reproduce manual quiz create API."""
import httpx
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    user="postgres",
    password="changeme",
    dbname="eduspark",
)
cur = conn.cursor()
cur.execute(
    """
    SELECT u.id, u.email, c.id
    FROM users u
    JOIN teacher_profiles tp ON tp.user_id = u.id
    JOIN courses c ON c.teacher_profile_id = tp.id
    WHERE u.role = 'teacher'
    LIMIT 1
    """
)
row = cur.fetchone()
conn.close()
if not row:
    raise SystemExit("no teacher course found")
_, email, course_id = row
print("teacher", email, "course", course_id)

for pwd in ("teacher123", "password123", "changeme"):
    login = httpx.post(
        "http://127.0.0.1:8000/api/auth/login",
        json={"email": email, "password": pwd},
        timeout=15,
    )
    if login.status_code != 200:
        continue
    token = login.json()["access_token"]
    payload = {
        "title": "Traceback Test Quiz",
        "description": None,
        "duration_minutes": 30,
        "passing_score_percent": 60,
        "is_published": False,
        "due_at": None,
    }
    create = httpx.post(
        f"http://127.0.0.1:8000/api/teacher/courses/{course_id}/manual-quizzes",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    print("password ok:", pwd)
    print("payload:", payload)
    print("status:", create.status_code)
    print("response:", create.text)
    break
else:
    raise SystemExit("login failed")
