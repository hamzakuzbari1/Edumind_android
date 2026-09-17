"""Validate A0.1 against a disposable local PostgreSQL database.

The runner never loads repository dotenv files and refuses non-loopback servers.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import uuid

import sqlalchemy as sa
from sqlalchemy.engine import URL


BACKEND = Path(__file__).resolve().parents[1]
HOST = "localhost"
PORT = 5432
USER = "postgres"
EXPECTED_VERSION_NUM = "160014"
BASELINE_HEAD = "0015_merge_vocabulary_fixed_bank"
HEAD = "0019_teacher_voice_consent"


def _pgpass_path() -> Path:
    path = Path(
        os.environ.get("PGPASSFILE")
        or Path(os.environ["APPDATA"]) / "postgresql" / "pgpass.conf"
    )
    if not path.is_file():
        raise RuntimeError("Local pgpass.conf was not found")
    return path


def _admin_engine() -> sa.Engine:
    return sa.create_engine(
        URL.create(
            "postgresql+psycopg2",
            username=USER,
            host=HOST,
            port=PORT,
            database="postgres",
        ),
        isolation_level="AUTOCOMMIT",
        hide_parameters=True,
    )


def _database_url(database: str, *, async_driver: bool = False) -> str:
    driver = "postgresql+asyncpg" if async_driver else "postgresql+psycopg2"
    return URL.create(
        driver,
        username=USER,
        host=HOST,
        port=PORT,
        database=database,
    ).render_as_string(hide_password=False)


def _child_env(database: str, pgpass: Path) -> dict[str, str]:
    allowed = {
        "SYSTEMROOT",
        "WINDIR",
        "PATH",
        "TEMP",
        "TMP",
        "COMSPEC",
        "PATHEXT",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
    }
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    sync_url = _database_url(database)
    env.update(
        DATABASE_URL=_database_url(database, async_driver=True),
        SYNC_DATABASE_URL=sync_url,
        DATABASE_URL_SYNC=sync_url,
        JWT_SECRET=secrets.token_hex(32),
        DEBUG="true",
        ENABLE_FAISS="false",
        ENABLE_WHISPER="false",
        ENABLE_EMBEDDINGS="false",
        PGPASSFILE=str(pgpass),
        PYTHONDONTWRITEBYTECODE="1",
    )
    return env


def _run_child(snapshot: Path, database: str, pgpass: Path, args: list[str]) -> str:
    result = subprocess.run(
        [sys.executable, "-B", *args],
        cwd=snapshot,
        env=_child_env(database, pgpass),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    output = result.stdout + result.stderr
    output = re.sub(
        r"postgresql(?:\+\w+)?://[^\s]+",
        "<redacted-database-url>",
        output,
    )
    if result.returncode:
        raise RuntimeError("Child command failed:\n" + output)
    return output


def _migrate(snapshot: Path, database: str, pgpass: Path, operation: str, target: str) -> None:
    _run_child(snapshot, database, pgpass, ["-m", "alembic", operation, target])


def _insert_fixtures(engine: sa.Engine) -> dict[str, object]:
    with engine.begin() as connection:
        teacher_id = connection.execute(
            sa.text(
                """
                INSERT INTO users (email, name, hashed_password, role)
                VALUES ('a01-teacher@example.test', 'A0.1 Teacher', 'not-a-real-password', 'teacher')
                RETURNING id
                """
            )
        ).scalar_one()
        teacher_profile_id = connection.execute(
            sa.text(
                """
                INSERT INTO teacher_profiles
                    (user_id, full_name, rating, student_count, active)
                VALUES (:user_id, 'A0.1 Teacher', 0, 0, true)
                RETURNING id
                """
            ),
            {"user_id": teacher_id},
        ).scalar_one()
        subject_id = connection.execute(
            sa.text(
                """
                INSERT INTO subjects (name_ar, slug, grade, is_active)
                VALUES ('اختبار الوحدات', 'a01-course-units', 12, true)
                RETURNING id
                """
            )
        ).scalar_one()

        course_ids: dict[str, int] = {}
        for key, title in (
            ("a", "A0.1 Course A"),
            ("b", "A0.1 Course B"),
            ("empty", "A0.1 Empty Course"),
        ):
            course_ids[key] = connection.execute(
                sa.text(
                    """
                    INSERT INTO courses
                        (title, subject_id, teacher_profile_id, grade, price, currency, is_active, is_published)
                    VALUES (:title, :subject_id, :teacher_profile_id, 12, 0, 'SYP', true, true)
                    RETURNING id
                    """
                ),
                {
                    "title": title,
                    "subject_id": subject_id,
                    "teacher_profile_id": teacher_profile_id,
                },
            ).scalar_one()

        lesson_specs = (
            ("a1", course_ids["a"], "A0.1 Lesson A1", 10),
            ("a2", course_ids["a"], "A0.1 Lesson A2", 20),
            ("b1", course_ids["b"], "A0.1 Lesson B1", 7),
            ("orphan", None, "A0.1 Course-less Lesson", 3),
        )
        lesson_ids: dict[str, int] = {}
        for key, course_id, title, sort_order in lesson_specs:
            lesson_ids[key] = connection.execute(
                sa.text(
                    """
                    INSERT INTO lessons
                        (teacher_id, course_id, title, subject, grade, status, sort_order, is_visible)
                    VALUES (:teacher_id, :course_id, :title, 'A0.1', '12', 'draft', :sort_order, true)
                    RETURNING id
                    """
                ),
                {
                    "teacher_id": teacher_id,
                    "course_id": course_id,
                    "title": title,
                    "sort_order": sort_order,
                },
            ).scalar_one()

        before = connection.execute(
            sa.text("SELECT id, course_id, sort_order FROM lessons ORDER BY id")
        ).all()
        return {"courses": course_ids, "lessons": lesson_ids, "before": before}


def _orm_check(snapshot: Path, database: str, pgpass: Path) -> str:
    script = r'''
import json
import os
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, selectinload
from app import models
from app.db.base import Base
from app.models.catalog import Course, CourseUnit

engine = create_engine(os.environ["SYNC_DATABASE_URL"], hide_parameters=True)
with Session(engine) as session:
    courses = session.scalars(
        select(Course)
        .where(Course.title.like("A0.1 Course%"))
        .options(selectinload(Course.lessons), selectinload(Course.units))
        .order_by(Course.id)
    ).all()
    assert [lesson.title for lesson in courses[0].lessons] == ["A0.1 Lesson A1", "A0.1 Lesson A2"]
    assert [lesson.sort_order for lesson in courses[0].lessons] == [10, 20]
    assert len(courses[0].units) == 1
    assert [lesson.id for lesson in courses[0].units[0].lessons] == [lesson.id for lesson in courses[0].lessons]

with engine.connect() as connection:
    differences = compare_metadata(
        MigrationContext.configure(
            connection,
            opts={"compare_type": True, "compare_server_default": True},
        ),
        Base.metadata,
    )
    affected = [repr(item) for item in differences if "course_units" in repr(item) or "unit_id" in repr(item)]
    unrelated = [repr(item) for item in differences if repr(item) not in affected]
    if affected:
        raise AssertionError("Affected ORM drift: " + repr(affected))
    print(
        "ORM_DRIFT="
        + json.dumps(
            {
                "affected": affected,
                "unrelated_count": len(unrelated),
                "includes_courses_lesson_id": any(
                    "courses" in item and "lesson_id" in item for item in unrelated
                ),
                "unrelated_examples": unrelated[:8],
            },
            ensure_ascii=True,
        )
    )
engine.dispose()
'''
    return _run_child(snapshot, database, pgpass, ["-c", script])


def main() -> int:
    run_id = uuid.uuid4().hex[:12]
    database = f"edumind_course_units_{run_id}_{uuid.uuid4().hex[:16]}_test"
    pattern = re.compile(r"edumind_course_units_[a-f0-9]{12}_[a-f0-9]{16}_test")
    if not pattern.fullmatch(database):
        raise RuntimeError("Unsafe disposable database name")

    pgpass = _pgpass_path()
    admin = _admin_engine()
    temp = tempfile.TemporaryDirectory(prefix="edumind_course_units_replay_")
    snapshot = Path(temp.name) / "backend"
    snapshot.mkdir()
    results: dict[str, bool] = {}
    unrelated_drift: dict[str, object] = {}

    try:
        with admin.connect() as connection:
            identity = connection.execute(
                sa.text(
                    "SELECT host(inet_server_addr()), inet_server_port(), current_user, "
                    "current_database(), current_setting('server_version_num')"
                )
            ).one()
            if (
                identity[0] not in ("127.0.0.1", "::1")
                or identity[1] != PORT
                or identity[2] != USER
                or identity[3] != "postgres"
                or identity[4] != EXPECTED_VERSION_NUM
            ):
                raise RuntimeError("Local PostgreSQL identity/version check failed")
            connection.exec_driver_sql(f'CREATE DATABASE "{database}"')

        for name in ("app", "alembic"):
            shutil.copytree(
                BACKEND / name,
                snapshot / name,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".env", ".env.*", "versions_archive"),
            )
        shutil.copy2(BACKEND / "alembic.ini", snapshot / "alembic.ini")
        if any(path.exists() for path in (snapshot / ".env", snapshot.parent / ".env")):
            raise RuntimeError("Disposable snapshot must not contain dotenv files")

        engine = sa.create_engine(
            URL.create(
                "postgresql+psycopg2",
                username=USER,
                host=HOST,
                port=PORT,
                database=database,
            ),
            hide_parameters=True,
        )
        try:
            _migrate(snapshot, database, pgpass, "upgrade", BASELINE_HEAD)
            inspector = sa.inspect(engine)
            before_tables = set(inspector.get_table_names(schema="public"))
            before_lesson_columns = {column["name"] for column in inspector.get_columns("lessons")}
            before_course_columns = {column["name"] for column in inspector.get_columns("courses")}
            fixture = _insert_fixtures(engine)

            _migrate(snapshot, database, pgpass, "upgrade", "head")
            with engine.connect() as connection:
                results["A"] = connection.execute(
                    sa.text("SELECT version_num FROM alembic_version")
                ).scalar_one() == HEAD

                courses = fixture["courses"]
                lessons = fixture["lessons"]
                units = connection.execute(
                    sa.text(
                        "SELECT id, course_id, title, sort_order, is_visible "
                        "FROM course_units ORDER BY course_id, id"
                    )
                ).mappings().all()
                units_by_course: dict[int, list[object]] = {}
                for unit in units:
                    units_by_course.setdefault(unit["course_id"], []).append(unit)

                current_lessons = connection.execute(
                    sa.text("SELECT id, course_id, unit_id, sort_order FROM lessons ORDER BY id")
                ).mappings().all()
                by_id = {row["id"]: row for row in current_lessons}
                results["B"] = (
                    len(units_by_course.get(courses["a"], [])) == 1
                    and units_by_course[courses["a"]][0]["title"] == "عام"
                    and all(by_id[lessons[key]]["unit_id"] == units_by_course[courses["a"]][0]["id"] for key in ("a1", "a2"))
                    and [(row["id"], row["course_id"], row["sort_order"]) for row in current_lessons]
                    == [tuple(row) for row in fixture["before"]]
                )
                results["C"] = (
                    len(units_by_course.get(courses["a"], [])) == 1
                    and len(units_by_course.get(courses["b"], [])) == 1
                    and units_by_course[courses["a"]][0]["id"] != units_by_course[courses["b"]][0]["id"]
                )
                results["D"] = courses["empty"] not in units_by_course
                results["E"] = (
                    by_id[lessons["orphan"]]["course_id"] is None
                    and by_id[lessons["orphan"]]["unit_id"] is None
                )

                inspector = sa.inspect(connection)
                after_tables = set(inspector.get_table_names(schema="public"))
                after_lesson_columns = {column["name"] for column in inspector.get_columns("lessons")}
                after_course_columns = {column["name"] for column in inspector.get_columns("courses")}
                constraints = {item["name"]: item for item in inspector.get_foreign_keys("lessons")}
                checks = {item["name"]: item for item in inspector.get_check_constraints("lessons")}
                indexes = {item["name"]: item for item in inspector.get_indexes("course_units")}
                uniques = {item["name"]: item for item in inspector.get_unique_constraints("course_units")}
                schema_ok = (
                    # The fixture starts before A0.1; head includes all four A0 additions.
                    after_tables == before_tables | {
                        "course_units", "course_enrollments",
                        "conversation_message_attachments", "voice_consent_policies",
                        "teacher_voice_consents",
                    }
                    and after_lesson_columns == before_lesson_columns | {"unit_id"}
                    and after_course_columns == before_course_columns | {
                        "thumbnail_media_object_id", "banner_media_object_id"
                    }
                    and "lesson_id" in after_course_columns
                    and constraints["fk_lessons_course_unit"]["constrained_columns"] == ["course_id", "unit_id"]
                    and constraints["fk_lessons_course_unit"]["referred_columns"] == ["course_id", "id"]
                    and constraints["fk_lessons_course_unit"]["options"].get("ondelete") == "RESTRICT"
                    and "ck_lessons_unit_requires_course" in checks
                    and indexes["ix_course_units_course_sort_id"]["column_names"] == ["course_id", "sort_order", "id"]
                    and uniques["uq_course_units_course_id_id"]["column_names"] == ["course_id", "id"]
                )
                if not schema_ok:
                    raise AssertionError("A0.1 schema validation failed")

            unit_a = units_by_course[fixture["courses"]["a"]][0]["id"]
            try:
                with engine.begin() as connection:
                    connection.execute(
                        sa.text("UPDATE lessons SET unit_id=:unit_id WHERE id=:lesson_id"),
                        {"unit_id": unit_a, "lesson_id": fixture["lessons"]["b1"]},
                    )
            except sa.exc.IntegrityError:
                results["F"] = True
            else:
                results["F"] = False

            orm_output = _orm_check(snapshot, database, pgpass)
            results["G"] = True
            for line in orm_output.splitlines():
                if line.startswith("ORM_DRIFT="):
                    unrelated_drift = json.loads(line.removeprefix("ORM_DRIFT="))

            _migrate(snapshot, database, pgpass, "downgrade", BASELINE_HEAD)
            with engine.connect() as connection:
                inspector = sa.inspect(connection)
                downgraded_lessons = connection.execute(
                    sa.text("SELECT id, course_id, sort_order FROM lessons ORDER BY id")
                ).all()
                results["H"] = (
                    "course_units" not in inspector.get_table_names(schema="public")
                    and "unit_id" not in {column["name"] for column in inspector.get_columns("lessons")}
                    and "lesson_id" in {column["name"] for column in inspector.get_columns("courses")}
                    and downgraded_lessons == fixture["before"]
                    and connection.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one() == BASELINE_HEAD
                )
        finally:
            engine.dispose()

        for label in "ABCDEFGH":
            print(f"TEST_{label}={'PASS' if results.get(label) else 'FAIL'}")
        print("SOURCE_HEAD=" + HEAD)
        print("UNRELATED_ORM_DRIFT=" + json.dumps(unrelated_drift, ensure_ascii=True))
        return 0 if all(results.get(label) for label in "ABCDEFGH") else 1
    except Exception as exc:
        print("VALIDATION_ERROR=" + str(exc), file=sys.stderr)
        for label in "ABCDEFGH":
            print(f"TEST_{label}={'PASS' if results.get(label) else 'FAIL'}")
        return 1
    finally:
        if pattern.fullmatch(database):
            try:
                with admin.connect() as connection:
                    connection.execute(
                        sa.text(
                            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                            "WHERE datname=:database AND pid<>pg_backend_pid()"
                        ),
                        {"database": database},
                    )
                    connection.exec_driver_sql(f'DROP DATABASE IF EXISTS "{database}"')
            finally:
                admin.dispose()
        temp.cleanup()


if __name__ == "__main__":
    sys.exit(main())
