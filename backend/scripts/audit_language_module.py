"""Language module audit — API endpoints, DB cross-check, parent metrics.

Usage (API must be running on :8000):
  cd backend && python scripts/audit_language_module.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

import httpx
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import get_settings
from app.models.language.analytics import LanguageAnalytics
from app.models.language.catalog import Language
from app.models.language.content import LanguageContentItem
from app.models.language.engagement import LanguageStreak
from app.models.language.enums import LanguageContentProgressStatus, LanguageVocabularyStatus
from app.models.language.progress import (
    LanguageListeningProgress,
    LanguageReadingProgress,
    LanguageSpeakingProgress,
    LanguageVocabularyProgress,
    LanguageWritingProgress,
)
from app.services.language_hub_service import build_language_progress

BASE = "http://127.0.0.1:8000/api"
BUGS: list[str] = []
WARNINGS: list[str] = []


def login(client: httpx.Client, email: str, password: str) -> str | None:
    r = client.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        return None
    return r.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def check(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    line = f"[{status}] {name}" + (f" — {detail}" if detail else "")
    print(line)
    if not ok:
        BUGS.append(f"{name}: {detail}" if detail else name)


def db_session() -> Session:
    engine = create_engine(get_settings().DATABASE_URL_SYNC)
    return Session(engine)


def find_language_student(session: Session) -> tuple[int, str] | None:
    row = session.execute(
        text(
            """
            SELECT u.id, u.email
            FROM users u
            JOIN language_student_profiles p ON p.student_id = u.id
            JOIN language_subscriptions s ON s.student_id = u.id
            WHERE p.placement_completed_at IS NOT NULL
              AND s.activated_at IS NOT NULL
              AND (s.expires_at IS NULL OR s.expires_at > NOW())
            ORDER BY u.id
            LIMIT 1
            """
        )
    ).fetchone()
    if not row:
        return None
    return int(row[0]), str(row[1])


def make_test_token(user_id: int) -> str:
    from app.core.security import create_access_token

    return create_access_token({"sub": str(user_id)})


def audit_endpoints_testclient(student_id: int) -> dict:
    from fastapi.testclient import TestClient
    from app.main import app

    print("\n=== Student language API endpoints (TestClient) ===")
    client = TestClient(app)
    token = make_test_token(student_id)
    h = auth_headers(token)
    endpoints = [
        "/student/languages/access",
        "/student/languages/product",
        "/student/languages/hub",
        "/student/languages/reading",
        "/student/languages/listening",
        "/student/languages/progress",
        "/student/languages/vocabulary",
        "/student/languages/writing",
        "/student/languages/speaking",
    ]
    snapshots: dict = {}
    for path in endpoints:
        r = client.get(f"/api{path}", headers=h)
        ok = r.status_code == 200
        detail = f"HTTP {r.status_code}"
        if not ok:
            detail += f" {r.text[:200]}"
        check(f"GET {path}", ok, detail)
        if ok:
            snapshots[path] = r.json()

    for path, key, prefix in [
        ("/student/languages/reading", "lessons", "reading"),
        ("/student/languages/listening", "lessons", "listening"),
        ("/student/languages/vocabulary", "cards", "vocabulary"),
        ("/student/languages/writing", "prompts", "writing"),
        ("/student/languages/speaking", "prompts", "speaking"),
    ]:
        items = (snapshots.get(path) or {}).get(key) or []
        if items:
            iid = items[0]["id"]
            r = client.get(f"/api/student/languages/{prefix}/{iid}", headers=h)
            check(f"GET .../{prefix}/{{id}}", r.status_code == 200, f"HTTP {r.status_code}")
        else:
            WARNINGS.append(f"No items in {path} — detail endpoint not exercised for student {student_id}")

    return snapshots


def audit_parent_testclient(student_id: int) -> None:
    from fastapi.testclient import TestClient
    from app.main import app

    print("\n=== Parent dashboard language metrics (TestClient) ===")
    with db_session() as session:
        parent_row = session.execute(
            text(
                """
                SELECT u.id, u.email FROM users u
                JOIN parent_student_links psl ON psl.parent_id = u.id
                WHERE psl.student_id = :sid AND u.role = 'parent'
                LIMIT 1
                """
            ),
            {"sid": student_id},
        ).fetchone()

    if not parent_row:
        WARNINGS.append(f"No parent linked to student_id={student_id}")
        return

    parent_id, parent_email = int(parent_row[0]), str(parent_row[1])
    client = TestClient(app)
    r = client.get("/api/parent/dashboard", headers=auth_headers(make_test_token(parent_id)))
    check(f"GET /parent/dashboard (parent {parent_email})", r.status_code == 200, f"HTTP {r.status_code}")
    if r.status_code != 200:
        return
    lp = r.json().get("language_placement")
    check("parent.language_placement present", lp is not None)
    if not lp:
        return
    for f in (
        "language_code",
        "reading_level",
        "listening_level",
        "writing_level",
        "speaking_level",
        "overall_level",
        "skill_growth",
    ):
        check(f"parent.language_placement.{f}", lp.get(f) is not None, str(lp.get(f)))
    sg = lp.get("skill_growth") or {}
    for skill in ("reading", "listening", "writing", "speaking", "vocabulary"):
        check(f"parent.skill_growth.{skill}", skill in sg, "missing")


def count_completed_progress(session: Session, student_id: int, language_id: int) -> dict[str, int]:
    reading = session.execute(
        select(func.count())
        .select_from(LanguageReadingProgress)
        .join(LanguageContentItem, LanguageContentItem.id == LanguageReadingProgress.content_item_id)
        .where(
            LanguageReadingProgress.student_id == student_id,
            LanguageContentItem.language_id == language_id,
            LanguageContentItem.content_type == "lesson",
            LanguageContentItem.skill == "reading",
            LanguageReadingProgress.status == LanguageContentProgressStatus.completed,
        )
    ).scalar() or 0

    listening = session.execute(
        select(func.count())
        .select_from(LanguageListeningProgress)
        .join(LanguageContentItem, LanguageContentItem.id == LanguageListeningProgress.content_item_id)
        .where(
            LanguageListeningProgress.student_id == student_id,
            LanguageContentItem.language_id == language_id,
            LanguageContentItem.content_type == "lesson",
            LanguageContentItem.skill == "listening",
            LanguageListeningProgress.status == LanguageContentProgressStatus.completed,
        )
    ).scalar() or 0

    writing = session.execute(
        select(func.count())
        .select_from(LanguageWritingProgress)
        .join(LanguageContentItem, LanguageContentItem.id == LanguageWritingProgress.content_item_id)
        .where(
            LanguageWritingProgress.student_id == student_id,
            LanguageContentItem.language_id == language_id,
            LanguageContentItem.content_type == "writing_prompt",
            LanguageWritingProgress.completed_at.isnot(None),
        )
    ).scalar() or 0

    speaking = session.execute(
        select(func.count())
        .select_from(LanguageSpeakingProgress)
        .join(LanguageContentItem, LanguageContentItem.id == LanguageSpeakingProgress.content_item_id)
        .where(
            LanguageSpeakingProgress.student_id == student_id,
            LanguageContentItem.language_id == language_id,
            LanguageContentItem.content_type == "speaking_prompt",
            LanguageSpeakingProgress.completed_at.isnot(None),
        )
    ).scalar() or 0

    known_vocab = session.execute(
        select(func.count())
        .select_from(LanguageVocabularyProgress)
        .where(
            LanguageVocabularyProgress.student_id == student_id,
            LanguageVocabularyProgress.language_id == language_id,
            LanguageVocabularyProgress.status == LanguageVocabularyStatus.known,
        )
    ).scalar() or 0

    learning_vocab = session.execute(
        select(func.count())
        .select_from(LanguageVocabularyProgress)
        .where(
            LanguageVocabularyProgress.student_id == student_id,
            LanguageVocabularyProgress.language_id == language_id,
            LanguageVocabularyProgress.status == LanguageVocabularyStatus.learning,
        )
    ).scalar() or 0

    streak = session.execute(
        select(LanguageStreak).where(
            LanguageStreak.student_id == student_id,
            LanguageStreak.language_id == language_id,
        )
    ).scalar_one_or_none()

    return {
        "reading_completed": int(reading),
        "listening_completed": int(listening),
        "writing_completed": int(writing),
        "speaking_completed": int(speaking),
        "vocabulary_known": int(known_vocab),
        "vocabulary_learning": int(learning_vocab),
        "current_streak": int(streak.current_streak if streak else 0),
        "longest_streak": int(streak.longest_streak if streak else 0),
    }


def audit_tables(session: Session) -> None:
    print("\n=== Database tables ===")
    tables = session.execute(
        text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' "
            "AND tablename LIKE 'language_%' ORDER BY tablename"
        )
    ).fetchall()
    table_names = [t[0] for t in tables]
    print(f"language_* tables: {len(table_names)}")

    rev = session.execute(text("SELECT version_num FROM alembic_version")).scalar()
    print(f"alembic: {rev}")

    mig_dir = os.path.join(os.path.dirname(__file__), "..", "alembic", "versions")
    has_0009 = any("0009" in f for f in os.listdir(mig_dir))
    check("Migration 0009 file exists", has_0009)
    if not has_0009:
        WARNINGS.append("Fresh clone cannot run alembic upgrade head without 0009")

    empty = []
    for t in table_names:
        cnt = session.execute(text(f"SELECT count(*) FROM {t}")).scalar()
        if cnt == 0:
            empty.append(t)
    if empty:
        print("Empty tables:", ", ".join(empty))
        if "language_certificates" in empty:
            WARNINGS.append("language_certificates empty — no certificate issuance API yet")


async def cross_check_progress(student_id: int, api_progress: dict) -> None:
    from app.db.session import AsyncSessionLocal

    print("\n=== Progress API vs database ===")
    async with AsyncSessionLocal() as db:
        service_progress = await build_language_progress(db, student_id=student_id)

    with db_session() as session:
        lang = session.execute(select(Language).where(Language.code == "en")).scalar_one()
        db_counts = count_completed_progress(session, student_id, lang.id)

    pairs = [
        ("current_streak", db_counts["current_streak"]),
        ("longest_streak", db_counts["longest_streak"]),
        ("writing_completed", db_counts["writing_completed"]),
        ("speaking_completed", db_counts["speaking_completed"]),
        ("vocabulary_learned", db_counts["vocabulary_known"]),
        ("vocabulary_learning", db_counts["vocabulary_learning"]),
    ]
    for field, db_val in pairs:
        api_val = api_progress.get(field)
        check(f"progress.{field} matches DB", api_val == db_val, f"api={api_val} db={db_val}")
        if service_progress.get(field) != api_val:
            WARNINGS.append(f"Service vs API mismatch for {field}")

    with db_session() as session:
        lang = session.execute(select(Language).where(Language.code == "en")).scalar_one()
        analytics = session.execute(
            select(LanguageAnalytics).where(
                LanguageAnalytics.student_id == student_id,
                LanguageAnalytics.language_id == lang.id,
            )
        ).scalar_one_or_none()
        if analytics:
            check(
                "progress.vocabulary_count matches analytics.vocabulary_count",
                api_progress.get("vocabulary_count") == int(analytics.vocabulary_count or 0),
                f"api={api_progress.get('vocabulary_count')} db={analytics.vocabulary_count}",
            )


def project_root() -> str:
    backend_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.dirname(backend_dir)


def audit_frontend_files() -> None:
    print("\n=== Frontend route files ===")
    root = os.path.join(project_root(), "src", "views", "student", "languages")
    for f in [
        "StudentLanguagesHubView.vue",
        "StudentLanguageSubscribeView.vue",
        "StudentLanguagePlacementView.vue",
        "StudentLanguageReadingView.vue",
        "StudentLanguageListeningView.vue",
        "StudentLanguageProgressView.vue",
        "StudentLanguageVocabularyView.vue",
        "StudentLanguageWritingView.vue",
        "StudentLanguageSpeakingView.vue",
    ]:
        check(f"View exists: {f}", os.path.isfile(os.path.join(root, f)))


def main() -> int:
    print("Language Module Audit")
    print("=" * 50)
    audit_frontend_files()

    with db_session() as session:
        audit_tables(session)
        student = find_language_student(session)
        if not student:
            BUGS.append("No active placed language student found in DB")
            _write_report()
            return 1
        student_id, email = student
        print(f"\nTest student: {email} (id={student_id})")

        snapshots = audit_endpoints_testclient(student_id)
        asyncio.run(cross_check_progress(student_id, snapshots.get("/student/languages/progress", {})))
        audit_parent_testclient(student_id)

    print("\n=== Summary ===")
    print(f"Bugs: {len(BUGS)}, Warnings: {len(WARNINGS)}")
    for b in BUGS:
        print("  BUG:", b)
    for w in WARNINGS:
        print("  WARN:", w)

    _write_report()
    return 1 if BUGS else 0


def _write_report() -> None:
    out = os.path.join(project_root(), "docs", "_audit_raw.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"bugs": BUGS, "warnings": WARNINGS}, f, indent=2)


if __name__ == "__main__":
    raise SystemExit(main())
