"""Validate A0.3 with a disposable local PostgreSQL database only."""

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
BASELINE_HEAD = "0017_course_enrollment_entitlements"
HEAD = "0019_teacher_voice_consent"
MEDIA_COLUMNS = {
    "storage_bucket",
    "access_scope",
    "status",
    "checksum_sha256",
    "metadata_json",
    "updated_at",
    "deleted_at",
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


def migrate(
    snapshot: Path,
    database: str,
    pgpass: Path,
    operation: str,
    target: str,
) -> None:
    run_child(snapshot, database, pgpass, ["-m", "alembic", operation, target])


def insert_fixtures(engine: sa.Engine) -> dict[str, object]:
    with engine.begin() as connection:
        teacher_id = connection.execute(
            sa.text(
                """
                INSERT INTO users (email, name, hashed_password, role)
                VALUES ('a03-teacher@example.test', 'A0.3 Teacher', 'not-real', 'teacher')
                RETURNING id
                """
            )
        ).scalar_one()
        student_id = connection.execute(
            sa.text(
                """
                INSERT INTO users (email, name, hashed_password, role)
                VALUES ('a03-student@example.test', 'A0.3 Student', 'not-real', 'student')
                RETURNING id
                """
            )
        ).scalar_one()
        teacher_profile_id = connection.execute(
            sa.text(
                """
                INSERT INTO teacher_profiles (user_id, full_name, rating, student_count, active)
                VALUES (:user_id, 'A0.3 Teacher', 0, 0, true)
                RETURNING id
                """
            ),
            {"user_id": teacher_id},
        ).scalar_one()
        subject_id = connection.execute(
            sa.text(
                """
                INSERT INTO subjects (name_ar, slug, grade, is_active)
                VALUES ('A0.3 Media Test', 'a03-media', 12, true)
                RETURNING id
                """
            )
        ).scalar_one()
        course_id = connection.execute(
            sa.text(
                """
                INSERT INTO courses
                    (title, subject_id, teacher_profile_id, grade, price, currency,
                     thumbnail_url, banner_url, is_active, is_published)
                VALUES
                    ('A0.3 Course', :subject_id, :teacher_profile_id, 12, 0, 'SYP',
                     '/legacy/course-thumb.jpg', '/legacy/course-banner.jpg', true, true)
                RETURNING id
                """
            ),
            {"subject_id": subject_id, "teacher_profile_id": teacher_profile_id},
        ).scalar_one()

        legacy_ids = []
        for filename in ("legacy-a.pdf", "legacy-b.pdf"):
            legacy_ids.append(
                connection.execute(
                    sa.text(
                        """
                        INSERT INTO media_objects
                            (storage_provider, storage_key, public_url, original_filename,
                             uploaded_by_user_id)
                        VALUES ('local', 'shared/legacy-key', '/media/shared.pdf',
                                :filename, :user_id)
                        RETURNING id
                        """
                    ),
                    {"filename": filename, "user_id": teacher_id},
                ).scalar_one()
            )
        private_media_id = connection.execute(
            sa.text(
                """
                INSERT INTO media_objects
                    (storage_provider, storage_key, public_url, original_filename)
                VALUES ('local', 'private/legacy-key', NULL, 'private.bin')
                RETURNING id
                """
            )
        ).scalar_one()
        language_id = connection.execute(
            sa.text("SELECT id FROM languages ORDER BY id LIMIT 1")
        ).scalar_one()
        language_item_id = connection.execute(
            sa.text(
                """
                INSERT INTO language_content_items
                    (language_id, skill, level, content_type, title, media_object_id,
                     sort_order, is_published)
                VALUES (:language_id, 'listening', 'A1', 'lesson',
                        'A0.3 Language Media', :media_id, 0, false)
                RETURNING id
                """
            ),
            {"language_id": language_id, "media_id": legacy_ids[0]},
        ).scalar_one()
        document_id = connection.execute(
            sa.text(
                """
                INSERT INTO teacher_professional_documents
                    (teacher_profile_id, title, document_type, file_url, sort_order)
                VALUES (:profile_id, 'A0.3 Certificate', 'certificate',
                        '/legacy/certificate.pdf', 0)
                RETURNING id
                """
            ),
            {"profile_id": teacher_profile_id},
        ).scalar_one()
        voice_id = connection.execute(
            sa.text(
                """
                INSERT INTO teacher_voice_samples
                    (teacher_profile_id, storage_path, duration_seconds,
                     preview_audio_path, processing_status)
                VALUES (:profile_id, '/legacy/voice.wav', 12.5,
                        '/legacy/voice-preview.mp3', 'ready')
                RETURNING id
                """
            ),
            {"profile_id": teacher_profile_id},
        ).scalar_one()
        thread_id = connection.execute(
            sa.text(
                """
                INSERT INTO conversation_threads
                    (thread_type, student_id, teacher_user_id, course_id,
                     include_parent, created_by_user_id)
                VALUES ('teacher_student', :student_id, :teacher_id, :course_id,
                        false, :teacher_id)
                RETURNING id
                """
            ),
            {
                "student_id": student_id,
                "teacher_id": teacher_id,
                "course_id": course_id,
            },
        ).scalar_one()
        message_id = connection.execute(
            sa.text(
                """
                INSERT INTO conversation_messages
                    (thread_id, sender_id, body, message_kind, attachment_url,
                     attachment_name, attachment_mime, status)
                VALUES (:thread_id, :sender_id, 'legacy attachment', 'document',
                        '/legacy/message.pdf', 'message.pdf', 'application/pdf', 'sent')
                RETURNING id
                """
            ),
            {"thread_id": thread_id, "sender_id": teacher_id},
        ).scalar_one()
        return {
            "teacher": teacher_id,
            "course": course_id,
            "legacy_media": legacy_ids,
            "private_media": private_media_id,
            "language_item": language_item_id,
            "document": document_id,
            "voice": voice_id,
            "message": message_id,
        }


def expect_integrity_error(engine: sa.Engine, statement: str, params: dict) -> bool:
    try:
        with engine.begin() as connection:
            connection.execute(sa.text(statement), params)
    except sa.exc.IntegrityError:
        return True
    return False


def main() -> int:
    run_id = uuid.uuid4().hex[:12]
    database = f"edumind_media_{run_id}_{uuid.uuid4().hex[:16]}_test"
    pattern = re.compile(r"edumind_media_[a-f0-9]{12}_[a-f0-9]{16}_test")
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
    temp = tempfile.TemporaryDirectory(prefix="edumind_media_replay_")
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
                    "__pycache__", "*.pyc", ".env", ".env.*", "versions_archive"
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
            before = sa.inspect(engine)
            before_tables = set(before.get_table_names(schema="public"))
            before_media_columns = {
                column["name"] for column in before.get_columns("media_objects")
            }
            before_entity_columns = {
                table: {column["name"] for column in before.get_columns(table)}
                for table in (
                    "users",
                    "courses",
                    "teacher_professional_documents",
                    "teacher_voice_samples",
                )
            }
            before_language_fks = before.get_foreign_keys("language_content_items")
            fixture = insert_fixtures(engine)

            migrate(snapshot, database, pgpass, "upgrade", "head")
            with engine.connect() as connection:
                inspector = sa.inspect(connection)
                results["A"] = (
                    connection.execute(
                        sa.text("SELECT version_num FROM alembic_version")
                    ).scalar_one()
                    == HEAD
                    and set(inspector.get_table_names(schema="public"))
                    == before_tables | {
                        "conversation_message_attachments", "voice_consent_policies",
                        "teacher_voice_consents",
                    }
                    and {
                        column["name"] for column in inspector.get_columns("media_objects")
                    }
                    == before_media_columns | MEDIA_COLUMNS
                )

                legacy = connection.execute(
                    sa.text(
                        """
                        SELECT id, storage_provider, storage_key, public_url,
                               access_scope, status
                        FROM media_objects
                        WHERE id = ANY(:ids)
                        ORDER BY id
                        """
                    ),
                    {"ids": fixture["legacy_media"] + [fixture["private_media"]]},
                ).all()
                results["B"] = (
                    len(legacy) == 3
                    and all(row.access_scope == "legacy_public" for row in legacy[:2])
                    and legacy[2].access_scope == "private"
                    and all(row.status == "ready" for row in legacy)
                    and legacy[0].storage_key == legacy[1].storage_key
                    and legacy[0].public_url == legacy[1].public_url
                )

                checks = {
                    item["name"] for item in inspector.get_check_constraints("media_objects")
                }
                index = {
                    item["name"]: item for item in inspector.get_indexes("media_objects")
                }["uq_media_objects_canonical_storage_identity"]
                results["C"] = (
                    {
                        "ck_media_objects_access_scope",
                        "ck_media_objects_status",
                        "ck_media_objects_supabase_bucket",
                    }
                    <= checks
                    and index["unique"]
                    and index["column_names"]
                    == ["storage_provider", "storage_bucket", "storage_key"]
                )

            with engine.begin() as connection:
                supabase_media_id = connection.execute(
                    sa.text(
                        """
                        INSERT INTO media_objects
                            (storage_provider, storage_bucket, storage_key, access_scope,
                             status, checksum_sha256, metadata_json)
                        VALUES ('supabase', 'private-media', 'lessons/a03.pdf', 'private',
                                'ready', :checksum, CAST(:metadata AS jsonb))
                        RETURNING id
                        """
                    ),
                    {"checksum": "a" * 64, "metadata": '{"source":"a03"}'},
                ).scalar_one()
            results["D"] = expect_integrity_error(
                engine,
                """
                INSERT INTO media_objects
                    (storage_provider, storage_key, access_scope, status)
                VALUES ('supabase', 'lessons/no-bucket.pdf', 'private', 'ready')
                """,
                {},
            )
            results["E"] = expect_integrity_error(
                engine,
                """
                INSERT INTO media_objects
                    (storage_provider, storage_bucket, storage_key, access_scope, status)
                VALUES ('supabase', 'private-media', 'lessons/a03.pdf', 'private', 'ready')
                """,
                {},
            )
            with engine.connect() as connection:
                results["F"] = connection.execute(
                    sa.text(
                        """
                        SELECT count(*) FROM media_objects
                        WHERE storage_provider='local'
                          AND storage_key='shared/legacy-key'
                          AND public_url='/media/shared.pdf'
                        """
                    )
                ).scalar_one() == 2

            with engine.begin() as connection:
                reference_media_id = connection.execute(
                    sa.text(
                        """
                        INSERT INTO media_objects
                            (storage_provider, storage_key, access_scope, status)
                        VALUES ('local', 'refs/a03.bin', 'private', 'ready')
                        RETURNING id
                        """
                    )
                ).scalar_one()
                connection.execute(
                    sa.text(
                        "UPDATE users SET avatar_media_object_id=:media WHERE id=:id"
                    ),
                    {"media": reference_media_id, "id": fixture["teacher"]},
                )
                connection.execute(
                    sa.text(
                        """
                        UPDATE courses
                        SET thumbnail_media_object_id=:media, banner_media_object_id=:media
                        WHERE id=:id
                        """
                    ),
                    {"media": reference_media_id, "id": fixture["course"]},
                )
                connection.execute(
                    sa.text(
                        """
                        UPDATE teacher_professional_documents
                        SET media_object_id=:media WHERE id=:id
                        """
                    ),
                    {"media": reference_media_id, "id": fixture["document"]},
                )
                connection.execute(
                    sa.text(
                        """
                        UPDATE teacher_voice_samples
                        SET source_media_object_id=:media, preview_media_object_id=:media
                        WHERE id=:id
                        """
                    ),
                    {"media": reference_media_id, "id": fixture["voice"]},
                )
                connection.execute(
                    sa.text("DELETE FROM media_objects WHERE id=:id"),
                    {"id": reference_media_id},
                )
            with engine.connect() as connection:
                refs = connection.execute(
                    sa.text(
                        """
                        SELECT
                          (SELECT avatar_media_object_id FROM users WHERE id=:teacher),
                          (SELECT thumbnail_media_object_id FROM courses WHERE id=:course),
                          (SELECT banner_media_object_id FROM courses WHERE id=:course),
                          (SELECT media_object_id FROM teacher_professional_documents WHERE id=:doc),
                          (SELECT source_media_object_id FROM teacher_voice_samples WHERE id=:voice),
                          (SELECT preview_media_object_id FROM teacher_voice_samples WHERE id=:voice)
                        """
                    ),
                    {
                        "teacher": fixture["teacher"],
                        "course": fixture["course"],
                        "doc": fixture["document"],
                        "voice": fixture["voice"],
                    },
                ).one()
                entity_fks = {
                    table: {item["name"]: item for item in sa.inspect(connection).get_foreign_keys(table)}
                    for table in (
                        "users",
                        "courses",
                        "teacher_professional_documents",
                        "teacher_voice_samples",
                    )
                }
                results["G"] = (
                    all(value is None for value in refs)
                    and entity_fks["users"]["fk_users_avatar_media_object_id_media_objects"]["options"].get("ondelete") == "SET NULL"
                    and entity_fks["courses"]["fk_courses_thumbnail_media_object_id_media_objects"]["options"].get("ondelete") == "SET NULL"
                    and entity_fks["courses"]["fk_courses_banner_media_object_id_media_objects"]["options"].get("ondelete") == "SET NULL"
                    and entity_fks["teacher_professional_documents"]["fk_teacher_professional_documents_media_object_id_media_objects"]["options"].get("ondelete") == "SET NULL"
                    and entity_fks["teacher_voice_samples"]["fk_teacher_voice_samples_source_media_object_id_media_objects"]["options"].get("ondelete") == "SET NULL"
                    and entity_fks["teacher_voice_samples"]["fk_teacher_voice_samples_preview_media_object_id_media_objects"]["options"].get("ondelete") == "SET NULL"
                )

            with engine.begin() as connection:
                attachment_media = connection.execute(
                    sa.text(
                        """
                        INSERT INTO media_objects
                            (storage_provider, storage_key, access_scope, status)
                        VALUES
                            ('local', 'messages/second.pdf', 'private', 'ready'),
                            ('local', 'messages/first.png', 'private', 'ready')
                        RETURNING id
                        """
                    )
                ).scalars().all()
                connection.execute(
                    sa.text(
                        """
                        INSERT INTO conversation_message_attachments
                            (message_id, media_object_id, attachment_kind, display_name, sort_order)
                        VALUES
                            (:message, :second, 'document', 'second.pdf', 20),
                            (:message, :first, 'image', 'first.png', 10)
                        """
                    ),
                    {
                        "message": fixture["message"],
                        "second": attachment_media[0],
                        "first": attachment_media[1],
                    },
                )
            duplicate_attachment_rejected = expect_integrity_error(
                engine,
                """
                INSERT INTO conversation_message_attachments
                    (message_id, media_object_id, attachment_kind)
                VALUES (:message, :media, 'file')
                """,
                {"message": fixture["message"], "media": attachment_media[0]},
            )
            restricted_media_delete = expect_integrity_error(
                engine,
                "DELETE FROM media_objects WHERE id=:media",
                {"media": attachment_media[0]},
            )
            with engine.connect() as connection:
                ordered = connection.execute(
                    sa.text(
                        """
                        SELECT media_object_id FROM conversation_message_attachments
                        WHERE message_id=:message ORDER BY sort_order, id
                        """
                    ),
                    {"message": fixture["message"]},
                ).scalars().all()
                attachment_fks = {
                    item["name"]: item
                    for item in sa.inspect(connection).get_foreign_keys(
                        "conversation_message_attachments"
                    )
                }
                attachment_index = {
                    item["name"]: item
                    for item in sa.inspect(connection).get_indexes(
                        "conversation_message_attachments"
                    )
                }
            with engine.begin() as connection:
                connection.execute(
                    sa.text("DELETE FROM conversation_messages WHERE id=:message"),
                    {"message": fixture["message"]},
                )
            with engine.connect() as connection:
                attachments_left = connection.execute(
                    sa.text(
                        "SELECT count(*) FROM conversation_message_attachments WHERE message_id=:message"
                    ),
                    {"message": fixture["message"]},
                ).scalar_one()
                media_left = connection.execute(
                    sa.text("SELECT count(*) FROM media_objects WHERE id = ANY(:ids)"),
                    {"ids": attachment_media},
                ).scalar_one()
                results["H"] = (
                    ordered == [attachment_media[1], attachment_media[0]]
                    and duplicate_attachment_rejected
                    and restricted_media_delete
                    and attachments_left == 0
                    and media_left == 2
                    and attachment_fks["fk_conversation_message_attachments_message_id_messages"]["options"].get("ondelete") == "CASCADE"
                    and attachment_fks["fk_conversation_message_attachments_media_object"]["options"].get("ondelete") == "RESTRICT"
                    and attachment_index["ix_conversation_message_attachments_message_order"]["column_names"] == ["message_id", "sort_order", "id"]
                )

                results["I"] = (
                    connection.execute(
                        sa.text(
                            "SELECT media_object_id FROM language_content_items WHERE id=:id"
                        ),
                        {"id": fixture["language_item"]},
                    ).scalar_one()
                    == fixture["legacy_media"][0]
                    and sa.inspect(connection).get_foreign_keys("language_content_items")
                    == before_language_fks
                )

            orm_script = f'''
import os
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, selectinload
from app import models
from app.models.catalog import Course
from app.models.conversation import ConversationMessageAttachment
from app.models.teacher_profile_cv import TeacherProfessionalDocument
from app.models.teacher_voice import TeacherVoiceSample

engine = create_engine(os.environ["SYNC_DATABASE_URL"], hide_parameters=True)
with Session(engine) as session:
    course = session.get(Course, {fixture["course"]})
    document = session.get(TeacherProfessionalDocument, {fixture["document"]})
    voice = session.get(TeacherVoiceSample, {fixture["voice"]})
    assert course.thumbnail_url == "/legacy/course-thumb.jpg"
    assert course.banner_url == "/legacy/course-banner.jpg"
    assert document.file_url == "/legacy/certificate.pdf"
    assert voice.storage_path == "/legacy/voice.wav"
    assert voice.preview_audio_path == "/legacy/voice-preview.mp3"
    assert session.scalars(select(ConversationMessageAttachment)).all() == []
engine.dispose()
'''
            run_child(snapshot, database, pgpass, ["-c", orm_script])
            results["J"] = True

            drift_script = '''
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
    media_markers = (
        "storage_bucket", "access_scope", "checksum_sha256", "metadata_json",
        "deleted_at", "ck_media_objects_", "uq_media_objects_canonical_storage_identity",
    )
    affected = []
    for item in differences:
        rendered = repr(item)
        reference_drift = (
            ("'users'" in rendered and "avatar_media_object_id" in rendered)
            or (
                "'courses'" in rendered
                and any(marker in rendered for marker in ("thumbnail_media_object_id", "banner_media_object_id"))
            )
            or (
                "'teacher_professional_documents'" in rendered
                and "media_object_id" in rendered
            )
            or (
                "'teacher_voice_samples'" in rendered
                and any(marker in rendered for marker in ("source_media_object_id", "preview_media_object_id"))
            )
        )
        if (
            "conversation_message_attachments" in rendered
            or reference_drift
            or ("'media_objects'" in rendered and any(marker in rendered for marker in media_markers))
        ):
            affected.append(rendered)
    unrelated = [repr(item) for item in differences if repr(item) not in affected]
    if affected:
        raise AssertionError("Affected ORM drift: " + repr(affected))
    print("ORM_DRIFT=" + json.dumps({"affected": affected, "unrelated_count": len(unrelated), "unrelated_examples": unrelated[:8]}))
engine.dispose()
'''
            drift_output = run_child(snapshot, database, pgpass, ["-c", drift_script])
            for line in drift_output.splitlines():
                if line.startswith("ORM_DRIFT="):
                    diagnostics["orm_drift"] = json.loads(line.removeprefix("ORM_DRIFT="))

            migrate(snapshot, database, pgpass, "downgrade", BASELINE_HEAD)
            with engine.connect() as connection:
                inspector = sa.inspect(connection)
                downgraded_media = connection.execute(
                    sa.text(
                        """
                        SELECT id, storage_provider, storage_key, public_url
                        FROM media_objects WHERE id = ANY(:ids) ORDER BY id
                        """
                    ),
                    {"ids": fixture["legacy_media"] + [fixture["private_media"]]},
                ).all()
                legacy_paths = connection.execute(
                    sa.text(
                        """
                        SELECT
                          (SELECT thumbnail_url FROM courses WHERE id=:course),
                          (SELECT banner_url FROM courses WHERE id=:course),
                          (SELECT file_url FROM teacher_professional_documents WHERE id=:doc),
                          (SELECT storage_path FROM teacher_voice_samples WHERE id=:voice),
                          (SELECT preview_audio_path FROM teacher_voice_samples WHERE id=:voice),
                          (SELECT media_object_id FROM language_content_items WHERE id=:language)
                        """
                    ),
                    {
                        "course": fixture["course"],
                        "doc": fixture["document"],
                        "voice": fixture["voice"],
                        "language": fixture["language_item"],
                    },
                ).one()
                results["K"] = (
                    connection.execute(
                        sa.text("SELECT version_num FROM alembic_version")
                    ).scalar_one()
                    == BASELINE_HEAD
                    and "conversation_message_attachments"
                    not in inspector.get_table_names(schema="public")
                    and {
                        column["name"] for column in inspector.get_columns("media_objects")
                    }
                    == before_media_columns
                    and all(
                        {column["name"] for column in inspector.get_columns(table)}
                        == columns
                        for table, columns in before_entity_columns.items()
                    )
                    and len(downgraded_media) == 3
                    and legacy_paths
                    == (
                        "/legacy/course-thumb.jpg",
                        "/legacy/course-banner.jpg",
                        "/legacy/certificate.pdf",
                        "/legacy/voice.wav",
                        "/legacy/voice-preview.mp3",
                        fixture["legacy_media"][0],
                    )
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

    for label in "ABCDEFGHIJK":
        print(f"TEST_{label}={'PASS' if results.get(label) else 'FAIL'}")
    print("SOURCE_HEAD=" + HEAD)
    print("DIAGNOSTICS=" + json.dumps(diagnostics, ensure_ascii=True, default=str))
    return 0 if all(results.get(label) for label in "ABCDEFGHIJK") else 1


if __name__ == "__main__":
    sys.exit(main())
