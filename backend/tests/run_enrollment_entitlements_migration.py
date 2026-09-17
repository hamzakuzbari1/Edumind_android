"""Validate A0.2 with a disposable local PostgreSQL database."""

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
BASELINE_HEAD = "0016_course_units"
HEAD = "0019_teacher_voice_consent"
NEW_ACCESS_COLUMNS = {
    "enrollment_id",
    "access_status",
    "source",
    "source_payment_item_id",
    "granted_by_user_id",
    "granted_at",
    "revoked_at",
    "revocation_reason",
    "updated_at",
}


def pgpass_path() -> Path:
    path = Path(
        os.environ.get("PGPASSFILE")
        or Path(os.environ["APPDATA"]) / "postgresql" / "pgpass.conf"
    )
    if not path.is_file():
        raise RuntimeError("Local pgpass.conf was not found")
    return path


def database_url(database: str, *, async_driver: bool = False) -> str:
    return URL.create(
        "postgresql+asyncpg" if async_driver else "postgresql+psycopg2",
        username=USER,
        host=HOST,
        port=PORT,
        database=database,
    ).render_as_string(hide_password=False)


def child_env(database: str, pgpass: Path) -> dict[str, str]:
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
    sync_url = database_url(database)
    env.update(
        DATABASE_URL=database_url(database, async_driver=True),
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


def run_child(snapshot: Path, database: str, pgpass: Path, args: list[str]) -> str:
    result = subprocess.run(
        [sys.executable, "-B", *args],
        cwd=snapshot,
        env=child_env(database, pgpass),
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


def migrate(snapshot: Path, database: str, pgpass: Path, operation: str, target: str) -> None:
    run_child(snapshot, database, pgpass, ["-m", "alembic", operation, target])


def insert_fixtures(engine: sa.Engine) -> dict[str, object]:
    with engine.begin() as connection:
        teacher_id = connection.execute(
            sa.text(
                """
                INSERT INTO users (email, name, hashed_password, role)
                VALUES ('a02-teacher@example.test', 'A0.2 Teacher', 'not-real', 'teacher')
                RETURNING id
                """
            )
        ).scalar_one()
        paid_student_id = connection.execute(
            sa.text(
                """
                INSERT INTO users (email, name, hashed_password, role)
                VALUES ('a02-paid@example.test', 'A0.2 Paid Student', 'not-real', 'student')
                RETURNING id
                """
            )
        ).scalar_one()
        pending_student_id = connection.execute(
            sa.text(
                """
                INSERT INTO users (email, name, hashed_password, role)
                VALUES ('a02-pending@example.test', 'A0.2 Pending Student', 'not-real', 'student')
                RETURNING id
                """
            )
        ).scalar_one()
        teacher_profile_id = connection.execute(
            sa.text(
                """
                INSERT INTO teacher_profiles (user_id, full_name, rating, student_count, active)
                VALUES (:user_id, 'A0.2 Teacher', 0, 0, true)
                RETURNING id
                """
            ),
            {"user_id": teacher_id},
        ).scalar_one()
        subject_id = connection.execute(
            sa.text(
                """
                INSERT INTO subjects (name_ar, slug, grade, is_active)
                VALUES ('A0.2 Enrollment Test', 'a02-enrollment', 12, true)
                RETURNING id
                """
            )
        ).scalar_one()

        course_ids = {}
        for key, title in (("paid", "A0.2 Paid Course"), ("pending", "A0.2 Pending Course")):
            course_ids[key] = connection.execute(
                sa.text(
                    """
                    INSERT INTO courses
                        (title, subject_id, teacher_profile_id, grade, price, currency,
                         is_active, is_published)
                    VALUES
                        (:title, :subject_id, :teacher_profile_id, 12, 100, 'SYP', true, true)
                    RETURNING id
                    """
                ),
                {
                    "title": title,
                    "subject_id": subject_id,
                    "teacher_profile_id": teacher_profile_id,
                },
            ).scalar_one()

        paid_access_id = connection.execute(
            sa.text(
                """
                INSERT INTO student_course_access
                    (student_id, course_id, payment_status, unlocked_at, activated_at,
                     expires_at, created_at)
                VALUES
                    (:student_id, :course_id, 'paid', now() - interval '2 days',
                     now() - interval '2 days', now() + interval '30 days',
                     now() - interval '3 days')
                RETURNING id
                """
            ),
            {"student_id": paid_student_id, "course_id": course_ids["paid"]},
        ).scalar_one()
        pending_access_id = connection.execute(
            sa.text(
                """
                INSERT INTO student_course_access
                    (student_id, course_id, payment_status, created_at)
                VALUES (:student_id, :course_id, 'pending', now() - interval '1 day')
                RETURNING id
                """
            ),
            {"student_id": pending_student_id, "course_id": course_ids["pending"]},
        ).scalar_one()

        paid_payment_id = connection.execute(
            sa.text(
                """
                INSERT INTO payments
                    (student_id, total_amount, currency, method, status, reference, paid_at)
                VALUES (:student_id, 100, 'SYP', 'card', 'paid', 'A02-PAID', now())
                RETURNING id
                """
            ),
            {"student_id": paid_student_id},
        ).scalar_one()
        paid_item_id = connection.execute(
            sa.text(
                """
                INSERT INTO payment_items
                    (payment_id, course_id, unit_price, product_type)
                VALUES (:payment_id, :course_id, 100, 'course')
                RETURNING id
                """
            ),
            {"payment_id": paid_payment_id, "course_id": course_ids["paid"]},
        ).scalar_one()

        pending_payment_id = connection.execute(
            sa.text(
                """
                INSERT INTO payments
                    (student_id, total_amount, currency, method, status, reference)
                VALUES (:student_id, 100, 'SYP', 'cash', 'pending', 'A02-PENDING')
                RETURNING id
                """
            ),
            {"student_id": pending_student_id},
        ).scalar_one()
        connection.execute(
            sa.text(
                """
                INSERT INTO payment_items
                    (payment_id, course_id, unit_price, product_type)
                VALUES (:payment_id, :course_id, 100, 'course')
                """
            ),
            {"payment_id": pending_payment_id, "course_id": course_ids["pending"]},
        )

        access_before = connection.execute(
            sa.text(
                """
                SELECT id, student_id, course_id, payment_status::text, unlocked_at,
                       activated_at, expires_at, created_at
                FROM student_course_access
                ORDER BY id
                """
            )
        ).all()
        payments_before = connection.execute(
            sa.text("SELECT row_to_json(p) FROM payments p ORDER BY id")
        ).scalars().all()
        items_before = connection.execute(
            sa.text("SELECT row_to_json(i) FROM payment_items i ORDER BY id")
        ).scalars().all()
        return {
            "students": {"paid": paid_student_id, "pending": pending_student_id},
            "courses": course_ids,
            "access": {"paid": paid_access_id, "pending": pending_access_id},
            "paid_item_id": paid_item_id,
            "access_before": access_before,
            "payments_before": payments_before,
            "items_before": items_before,
        }


def main() -> int:
    run_id = uuid.uuid4().hex[:12]
    database = f"edumind_entitlements_{run_id}_{uuid.uuid4().hex[:16]}_test"
    pattern = re.compile(r"edumind_entitlements_[a-f0-9]{12}_[a-f0-9]{16}_test")
    if not pattern.fullmatch(database):
        raise RuntimeError("Unsafe disposable database name")

    pgpass = pgpass_path()
    admin = sa.create_engine(
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
    temp = tempfile.TemporaryDirectory(prefix="edumind_entitlements_replay_")
    snapshot = Path(temp.name) / "backend"
    snapshot.mkdir()
    results: dict[str, bool] = {}
    diagnostics: dict[str, object] = {}

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
                ignore=shutil.ignore_patterns(
                    "__pycache__",
                    "*.pyc",
                    ".env",
                    ".env.*",
                    "versions_archive",
                ),
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
            migrate(snapshot, database, pgpass, "upgrade", BASELINE_HEAD)
            inspector = sa.inspect(engine)
            before_tables = set(inspector.get_table_names(schema="public"))
            before_access_columns = {
                column["name"] for column in inspector.get_columns("student_course_access")
            }
            before_payment_columns = {
                column["name"] for column in inspector.get_columns("payments")
            }
            before_item_columns = {
                column["name"] for column in inspector.get_columns("payment_items")
            }
            fixture = insert_fixtures(engine)

            migrate(snapshot, database, pgpass, "upgrade", "head")
            results["A"] = True
            with engine.connect() as connection:
                current = connection.execute(
                    sa.text("SELECT version_num FROM alembic_version")
                ).scalars().all()
                inspector = sa.inspect(connection)
                after_tables = set(inspector.get_table_names(schema="public"))
                after_access_columns = {
                    column["name"]
                    for column in inspector.get_columns("student_course_access")
                }
                after_payment_columns = {
                    column["name"] for column in inspector.get_columns("payments")
                }
                after_item_columns = {
                    column["name"] for column in inspector.get_columns("payment_items")
                }
                enrollment_indexes = {
                    item["name"]: item for item in inspector.get_indexes("course_enrollments")
                }
                enrollment_checks = {
                    item["name"]: item
                    for item in inspector.get_check_constraints("course_enrollments")
                }
                enrollment_fks = {
                    item["name"]: item
                    for item in inspector.get_foreign_keys("course_enrollments")
                }
                access_fks = {
                    item["name"]: item
                    for item in inspector.get_foreign_keys("student_course_access")
                }
                access_checks = {
                    item["name"]: item
                    for item in inspector.get_check_constraints("student_course_access")
                }
                partial_definition = connection.execute(
                    sa.text(
                        """
                        SELECT indexdef FROM pg_indexes
                        WHERE schemaname = 'public'
                          AND tablename = 'course_enrollments'
                          AND indexname = 'uq_course_enrollments_current_student_course'
                        """
                    )
                ).scalar_one()
                schema_ok = (
                    current == [HEAD]
                    and after_tables == before_tables | {
                        "course_enrollments", "conversation_message_attachments",
                        "voice_consent_policies", "teacher_voice_consents",
                    }
                    and after_access_columns == before_access_columns | NEW_ACCESS_COLUMNS
                    and after_payment_columns == before_payment_columns
                    and after_item_columns == before_item_columns
                    and "ck_course_enrollments_status" in enrollment_checks
                    and "ck_course_enrollments_source" in enrollment_checks
                    and "ck_student_course_access_access_status" in access_checks
                    and enrollment_fks["fk_course_enrollments_student_id_users"][
                        "options"
                    ].get("ondelete") == "CASCADE"
                    and enrollment_fks["fk_course_enrollments_course_id_courses"][
                        "options"
                    ].get("ondelete") == "CASCADE"
                    and enrollment_fks[
                        "fk_course_enrollments_source_payment_item_id_payment_items"
                    ]["options"].get("ondelete") == "SET NULL"
                    and access_fks[
                        "fk_student_course_access_enrollment_id_course_enrollments"
                    ]["options"].get("ondelete") == "SET NULL"
                    and enrollment_indexes["ix_course_enrollments_student_course"][
                        "column_names"
                    ] == ["student_id", "course_id"]
                    and enrollment_indexes["ix_course_enrollments_course_student"][
                        "column_names"
                    ] == ["course_id", "student_id"]
                    and enrollment_indexes["ix_course_enrollments_status"][
                        "column_names"
                    ] == ["status"]
                )
                partial_ok = (
                    "UNIQUE INDEX" in partial_definition
                    and "(student_id, course_id)" in partial_definition
                    and "status" in partial_definition
                    and all(
                        value in partial_definition
                        for value in ("pending", "active", "paused")
                    )
                )
                results["A"] = schema_ok and partial_ok
                diagnostics["schema"] = schema_ok
                diagnostics["partial_unique_index"] = partial_ok
                paid = connection.execute(
                    sa.text(
                        """
                        SELECT access.payment_status::text, access.access_status,
                               access.enrollment_id, access.source,
                               access.source_payment_item_id, enrollment.status,
                               enrollment.source, enrollment.source_payment_item_id
                        FROM student_course_access AS access
                        JOIN course_enrollments AS enrollment
                          ON enrollment.id = access.enrollment_id
                        WHERE access.id = :access_id
                        """
                    ),
                    {"access_id": fixture["access"]["paid"]},
                ).one()
                results["B"] = (
                    paid[0] == "paid"
                    and paid[1] == "active"
                    and paid[2] is not None
                    and paid[3] == "payment"
                    and paid[4] == fixture["paid_item_id"]
                    and paid[5] == "active"
                    and paid[6] == "payment"
                    and paid[7] == fixture["paid_item_id"]
                )

                pending = connection.execute(
                    sa.text(
                        """
                        SELECT payment_status::text, enrollment_id, access_status
                        FROM student_course_access
                        WHERE id = :access_id
                        """
                    ),
                    {"access_id": fixture["access"]["pending"]},
                ).one()
                pending_enrollments = connection.execute(
                    sa.text(
                        """
                        SELECT count(*) FROM course_enrollments
                        WHERE student_id = :student_id AND course_id = :course_id
                        """
                    ),
                    {
                        "student_id": fixture["students"]["pending"],
                        "course_id": fixture["courses"]["pending"],
                    },
                ).scalar_one()
                results["C"] = (
                    pending == ("pending", None, "pending")
                    and pending_enrollments == 0
                )

                payments_after = connection.execute(
                    sa.text("SELECT row_to_json(p) FROM payments p ORDER BY id")
                ).scalars().all()
                items_after = connection.execute(
                    sa.text("SELECT row_to_json(i) FROM payment_items i ORDER BY id")
                ).scalars().all()
                results["F"] = (
                    payments_after == fixture["payments_before"]
                    and items_after == fixture["items_before"]
                )

            with engine.begin() as connection:
                for status in ("completed", "withdrawn", "cancelled"):
                    connection.execute(
                        sa.text(
                            """
                            INSERT INTO course_enrollments
                                (student_id, course_id, status, source,
                                 enrolled_at, created_at, updated_at)
                            VALUES
                                (:student_id, :course_id, :status, 'legacy',
                                 now(), now(), now())
                            """
                        ),
                        {
                            "student_id": fixture["students"]["paid"],
                            "course_id": fixture["courses"]["paid"],
                            "status": status,
                        },
                    )
            with engine.connect() as connection:
                historical = connection.execute(
                    sa.text(
                        """
                        SELECT status FROM course_enrollments
                        WHERE student_id = :student_id AND course_id = :course_id
                          AND status IN ('completed', 'withdrawn', 'cancelled')
                        ORDER BY status
                        """
                    ),
                    {
                        "student_id": fixture["students"]["paid"],
                        "course_id": fixture["courses"]["paid"],
                    },
                ).scalars().all()
                results["D"] = historical == ["cancelled", "completed", "withdrawn"]

            try:
                with engine.begin() as connection:
                    connection.execute(
                        sa.text(
                            """
                            INSERT INTO course_enrollments
                                (student_id, course_id, status, source,
                                 enrolled_at, created_at, updated_at)
                            VALUES
                                (:student_id, :course_id, 'paused', 'legacy',
                                 now(), now(), now())
                            """
                        ),
                        {
                            "student_id": fixture["students"]["paid"],
                            "course_id": fixture["courses"]["paid"],
                        },
                    )
            except sa.exc.IntegrityError:
                results["E"] = True
            else:
                results["E"] = False

            orm_script = f"""
import os
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, selectinload
from app import models
from app.models.enrollment import CourseEnrollment, StudentCourseAccess
from app.services.subscription_access_service import is_access_active

engine = create_engine(os.environ["SYNC_DATABASE_URL"], hide_parameters=True)
with Session(engine) as session:
    access = session.scalar(
        select(StudentCourseAccess)
        .where(StudentCourseAccess.id == {fixture["access"]["paid"]})
        .options(
            selectinload(StudentCourseAccess.course),
            selectinload(StudentCourseAccess.enrollment),
        )
    )
    assert access is not None
    assert access.payment_status.value == "paid"
    assert is_access_active(access)
    assert access.course is not None
    assert access.enrollment is not None
    assert access.enrollment.status == "active"
    assert session.scalar(
        select(CourseEnrollment).where(
            CourseEnrollment.id == access.enrollment_id
        )
    ) is not None
engine.dispose()
"""
            run_child(snapshot, database, pgpass, ["-c", orm_script])
            results["G"] = True

            drift_script = """
import json
import os
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine
from app import models
from app.db.base import Base

engine = create_engine(os.environ["SYNC_DATABASE_URL"], hide_parameters=True)
with engine.connect() as connection:
    differences = compare_metadata(
        MigrationContext.configure(
            connection,
            opts={"compare_type": True, "compare_server_default": True},
        ),
        Base.metadata,
    )
    markers = (
        "course_enrollments",
        "enrollment_id",
        "access_status",
        "source_payment_item_id",
        "granted_by_user_id",
        "granted_at",
        "revoked_at",
        "revocation_reason",
    )
    affected = [
        repr(item)
        for item in differences
        if any(marker in repr(item) for marker in markers)
    ]
    unrelated = [repr(item) for item in differences if repr(item) not in affected]
    if affected:
        raise AssertionError("Affected ORM drift: " + repr(affected))
    print(
        "ORM_DRIFT="
        + json.dumps(
            {
                "affected": affected,
                "unrelated_count": len(unrelated),
                "unrelated_examples": unrelated[:8],
            },
            ensure_ascii=True,
        )
    )
engine.dispose()
"""
            drift_output = run_child(snapshot, database, pgpass, ["-c", drift_script])
            for line in drift_output.splitlines():
                if line.startswith("ORM_DRIFT="):
                    diagnostics["orm_drift"] = json.loads(
                        line.removeprefix("ORM_DRIFT=")
                    )

            migrate(snapshot, database, pgpass, "downgrade", BASELINE_HEAD)
            with engine.connect() as connection:
                inspector = sa.inspect(connection)
                downgraded_columns = {
                    column["name"]
                    for column in inspector.get_columns("student_course_access")
                }
                access_after = connection.execute(
                    sa.text(
                        """
                        SELECT id, student_id, course_id, payment_status::text, unlocked_at,
                               activated_at, expires_at, created_at
                        FROM student_course_access
                        ORDER BY id
                        """
                    )
                ).all()
                payments_after = connection.execute(
                    sa.text("SELECT row_to_json(p) FROM payments p ORDER BY id")
                ).scalars().all()
                items_after = connection.execute(
                    sa.text("SELECT row_to_json(i) FROM payment_items i ORDER BY id")
                ).scalars().all()
                revision = connection.execute(
                    sa.text("SELECT version_num FROM alembic_version")
                ).scalar_one()
                results["H"] = (
                    "course_enrollments"
                    not in inspector.get_table_names(schema="public")
                    and downgraded_columns == before_access_columns
                    and access_after == fixture["access_before"]
                    and payments_after == fixture["payments_before"]
                    and items_after == fixture["items_before"]
                    and revision == BASELINE_HEAD
                )
        finally:
            engine.dispose()
    except Exception as exc:
        diagnostics["error"] = str(exc)
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

    for label in "ABCDEFGH":
        print(f"TEST_{label}={'PASS' if results.get(label) else 'FAIL'}")
    print("SOURCE_HEAD=" + HEAD)
    print("DIAGNOSTICS=" + json.dumps(diagnostics, ensure_ascii=True, default=str))
    return 0 if all(results.get(label) for label in "ABCDEFGH") else 1


if __name__ == "__main__":
    sys.exit(main())
