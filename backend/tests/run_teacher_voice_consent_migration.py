"""Validate A0.4 with a disposable local PostgreSQL database only."""

from __future__ import annotations

import hashlib
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
BASELINE_HEAD = "0018_media_storage_metadata"
HEAD = "0019_teacher_voice_consent"


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


def expect_integrity_error(engine: sa.Engine, statement: str, params: dict) -> bool:
    try:
        with engine.begin() as connection:
            connection.execute(sa.text(statement), params)
    except sa.exc.IntegrityError:
        return True
    return False


def insert_legacy_fixture(engine: sa.Engine) -> dict[str, object]:
    with engine.begin() as connection:
        teacher_id = connection.execute(
            sa.text(
                """
                INSERT INTO users (email, name, hashed_password, role)
                VALUES ('a04-teacher@example.test', 'A0.4 Teacher', 'not-real', 'teacher')
                RETURNING id
                """
            )
        ).scalar_one()
        actor_id = connection.execute(
            sa.text(
                """
                INSERT INTO users (email, name, hashed_password, role)
                VALUES ('a04-actor@example.test', 'A0.4 Actor', 'not-real', 'teacher')
                RETURNING id
                """
            )
        ).scalar_one()
        second_teacher_id = connection.execute(
            sa.text(
                """
                INSERT INTO users (email, name, hashed_password, role)
                VALUES ('a04-second@example.test', 'A0.4 Second', 'not-real', 'teacher')
                RETURNING id
                """
            )
        ).scalar_one()
        profile_id = connection.execute(
            sa.text(
                """
                INSERT INTO teacher_profiles (user_id, full_name, rating, student_count, active)
                VALUES (:user_id, 'A0.4 Teacher', 0, 0, true)
                RETURNING id
                """
            ),
            {"user_id": teacher_id},
        ).scalar_one()
        second_profile_id = connection.execute(
            sa.text(
                """
                INSERT INTO teacher_profiles (user_id, full_name, rating, student_count, active)
                VALUES (:user_id, 'A0.4 Second', 0, 0, true)
                RETURNING id
                """
            ),
            {"user_id": second_teacher_id},
        ).scalar_one()
        media_ids = connection.execute(
            sa.text(
                """
                INSERT INTO media_objects
                    (storage_provider, storage_key, access_scope, status, original_filename)
                VALUES
                    ('local', 'a04/source.wav', 'private', 'ready', 'source.wav'),
                    ('local', 'a04/preview.mp3', 'private', 'ready', 'preview.mp3')
                RETURNING id
                """
            )
        ).scalars().all()
        sample_id = connection.execute(
            sa.text(
                """
                INSERT INTO teacher_voice_samples
                    (teacher_profile_id, storage_path, source_media_object_id,
                     duration_seconds, processing_status, transcript, persona_prompt,
                     elevenlabs_voice_id, quality_score, quality_tier,
                     clone_confidence, transcript_quality, noise_score, speech_score,
                     preview_audio_path, preview_media_object_id, teacher_accepted,
                     quality_details_json)
                VALUES
                    (:profile, '/legacy/a04/source.wav', :source_media, 75.5, 'ready',
                     'legacy transcript', 'legacy persona', 'legacy-voice-id', 91.0,
                     'excellent', 88.0, 90.0, 4.0, 92.0,
                     '/legacy/a04/preview.mp3', :preview_media, true,
                     :quality_details)
                RETURNING id
                """
            ),
            {
                "profile": profile_id,
                "source_media": media_ids[0],
                "preview_media": media_ids[1],
                "quality_details": '{"legacy":true}',
            },
        ).scalar_one()
        sample_before = connection.execute(
            sa.text(
                "SELECT to_jsonb(s)::text FROM teacher_voice_samples s WHERE id=:id"
            ),
            {"id": sample_id},
        ).scalar_one()
        return {
            "teacher": teacher_id,
            "actor": actor_id,
            "profile": profile_id,
            "second_profile": second_profile_id,
            "sample": sample_id,
            "sample_before": sample_before,
        }


def main() -> int:
    run_id = uuid.uuid4().hex[:12]
    database = f"edumind_voice_consent_{run_id}_{uuid.uuid4().hex[:16]}_test"
    pattern = re.compile(
        r"edumind_voice_consent_[a-f0-9]{12}_[a-f0-9]{16}_test"
    )
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
    temp = tempfile.TemporaryDirectory(prefix="edumind_voice_consent_replay_")
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
            before_sample_columns = {
                column["name"]
                for column in before.get_columns("teacher_voice_samples")
            }
            fixture = insert_legacy_fixture(engine)

            migrate(snapshot, database, pgpass, "upgrade", "head")
            with engine.connect() as connection:
                inspector = sa.inspect(connection)
                tables = set(inspector.get_table_names(schema="public"))
                policy_columns = {
                    column["name"]
                    for column in inspector.get_columns("voice_consent_policies")
                }
                consent_columns = {
                    column["name"]
                    for column in inspector.get_columns("teacher_voice_consents")
                }
                sample_columns = {
                    column["name"]
                    for column in inspector.get_columns("teacher_voice_samples")
                }
                policy_indexes = {
                    item["name"]: item
                    for item in inspector.get_indexes("voice_consent_policies")
                }
                policy_uniques = {
                    item["name"]: item
                    for item in inspector.get_unique_constraints(
                        "voice_consent_policies"
                    )
                }
                consent_indexes = {
                    item["name"]: item
                    for item in inspector.get_indexes("teacher_voice_consents")
                }
                consent_checks = {
                    item["name"]
                    for item in inspector.get_check_constraints(
                        "teacher_voice_consents"
                    )
                }
                consent_fks = {
                    item["name"]: item
                    for item in inspector.get_foreign_keys("teacher_voice_consents")
                }
                sample_fks = {
                    item["name"]: item
                    for item in inspector.get_foreign_keys("teacher_voice_samples")
                }
                active_index_def = connection.execute(
                    sa.text(
                        """
                        SELECT indexdef FROM pg_indexes
                        WHERE schemaname='public'
                          AND tablename='teacher_voice_consents'
                          AND indexname='uq_teacher_voice_consents_active_teacher_profile'
                        """
                    )
                ).scalar_one()
                expected_policy_columns = {
                    "id", "policy_key", "version", "title", "policy_text",
                    "content_sha256", "policy_uri", "effective_at", "retired_at",
                    "created_at",
                }
                expected_consent_columns = {
                    "id", "teacher_profile_id", "consenting_user_id", "policy_id",
                    "status", "source", "granted_at", "revoked_at",
                    "revoked_by_user_id", "revocation_reason", "evidence_json",
                    "created_at", "updated_at",
                }
                schema_ok = (
                    connection.execute(
                        sa.text("SELECT version_num FROM alembic_version")
                    ).scalar_one() == HEAD
                    and tables == before_tables | {
                        "voice_consent_policies", "teacher_voice_consents"
                    }
                    and len(tables) == 133
                    and policy_columns == expected_policy_columns
                    and consent_columns == expected_consent_columns
                    and sample_columns == before_sample_columns | {"voice_consent_id"}
                    and policy_uniques["uq_voice_consent_policies_key_version"]["column_names"] == ["policy_key", "version"]
                    and policy_indexes["ix_voice_consent_policies_key_effective"]["column_names"] == ["policy_key", "effective_at"]
                    and {
                        "ck_teacher_voice_consents_status",
                        "ck_teacher_voice_consents_source",
                        "ck_teacher_voice_consents_state",
                    } <= consent_checks
                    and consent_indexes["ix_teacher_voice_consents_teacher_profile_id"]["column_names"] == ["teacher_profile_id"]
                    and consent_indexes["ix_teacher_voice_consents_consenting_user_id"]["column_names"] == ["consenting_user_id"]
                    and consent_indexes["ix_teacher_voice_consents_policy_id"]["column_names"] == ["policy_id"]
                    and consent_indexes["ix_teacher_voice_consents_status"]["column_names"] == ["status"]
                    and consent_indexes["uq_teacher_voice_consents_active_teacher_profile"]["unique"]
                    and "status" in active_index_def
                    and "granted" in active_index_def
                    and consent_fks["fk_teacher_voice_consents_teacher_profile"]["options"].get("ondelete") == "CASCADE"
                    and consent_fks["fk_teacher_voice_consents_consenting_user"]["options"].get("ondelete") == "RESTRICT"
                    and consent_fks["fk_teacher_voice_consents_policy"]["options"].get("ondelete") == "RESTRICT"
                    and consent_fks["fk_teacher_voice_consents_revoked_by_user"]["options"].get("ondelete") == "SET NULL"
                    and sample_fks["fk_teacher_voice_samples_voice_consent"]["options"].get("ondelete") == "SET NULL"
                )
                results["A"] = schema_ok
                results["I"] = (
                    connection.execute(
                        sa.text("SELECT count(*) FROM voice_consent_policies")
                    ).scalar_one() == 0
                    and connection.execute(
                        sa.text("SELECT count(*) FROM teacher_voice_consents")
                    ).scalar_one() == 0
                )
                sample_after = connection.execute(
                    sa.text(
                        """
                        SELECT (to_jsonb(s) - 'voice_consent_id')::text,
                               voice_consent_id
                        FROM teacher_voice_samples s WHERE id=:id
                        """
                    ),
                    {"id": fixture["sample"]},
                ).one()
                results["H"] = (
                    sample_after[0] == fixture["sample_before"]
                    and sample_after[1] is None
                )

                table_names = tables
                language_tables = {
                    name
                    for name in table_names
                    if name == "languages"
                    or name.startswith(("language_", "grammar_", "speaking_live_"))
                }
                diagnostics["regression"] = {
                    "a01": "course_units" in table_names
                    and "unit_id" in {
                        column["name"] for column in inspector.get_columns("lessons")
                    },
                    "a02": "course_enrollments" in table_names
                    and {
                        "enrollment_id", "access_status", "source",
                        "source_payment_item_id", "granted_by_user_id",
                        "granted_at", "revoked_at", "revocation_reason", "updated_at",
                    } <= {
                        column["name"]
                        for column in inspector.get_columns("student_course_access")
                    },
                    "a03": {
                        "storage_bucket", "access_scope", "status", "checksum_sha256",
                        "metadata_json", "updated_at", "deleted_at",
                    } <= {
                        column["name"] for column in inspector.get_columns("media_objects")
                    }
                    and {
                        "fk_teacher_voice_samples_source_media_object_id_media_objects",
                        "fk_teacher_voice_samples_preview_media_object_id_media_objects",
                    } <= set(sample_fks),
                    "language": len(language_tables) == 56,
                    "qbank": sum(
                        name == "language_placement_question_bank_items"
                        for name in table_names
                    ) == 1,
                }

            policy_text = "Disposable local migration validation policy."
            policy_hash = hashlib.sha256(policy_text.encode()).hexdigest()
            with engine.begin() as connection:
                policy_id = connection.execute(
                    sa.text(
                        """
                        INSERT INTO voice_consent_policies
                            (policy_key, version, title, policy_text, content_sha256,
                             policy_uri, effective_at)
                        VALUES
                            ('teacher_voice_processing', '1.0', 'A0.4 Test Policy',
                             :text, :digest, 'https://example.test/policy/1.0', now())
                        RETURNING id
                        """
                    ),
                    {"text": policy_text, "digest": policy_hash},
                ).scalar_one()
                first_consent_id = connection.execute(
                    sa.text(
                        """
                        INSERT INTO teacher_voice_consents
                            (teacher_profile_id, consenting_user_id, policy_id, status,
                             source, granted_at, evidence_json)
                        VALUES
                            (:profile, :user_id, :policy, 'granted', 'web', now(),
                             CAST(:evidence AS jsonb))
                        RETURNING id
                        """
                    ),
                    {
                        "profile": fixture["profile"],
                        "user_id": fixture["teacher"],
                        "policy": policy_id,
                        "evidence": '{"test":"local"}',
                    },
                ).scalar_one()
            with engine.connect() as connection:
                valid = connection.execute(
                    sa.text(
                        """
                        SELECT status, source, revoked_at, policy_id
                        FROM teacher_voice_consents WHERE id=:id
                        """
                    ),
                    {"id": first_consent_id},
                ).one()
                results["B"] = valid == ("granted", "web", None, policy_id)

            results["C"] = expect_integrity_error(
                engine,
                """
                INSERT INTO teacher_voice_consents
                    (teacher_profile_id, consenting_user_id, policy_id, status,
                     source, granted_at)
                VALUES (:profile, :user_id, :policy, 'granted', 'android', now())
                """,
                {
                    "profile": fixture["profile"],
                    "user_id": fixture["teacher"],
                    "policy": policy_id,
                },
            )

            with engine.begin() as connection:
                connection.execute(
                    sa.text(
                        """
                        UPDATE teacher_voice_consents
                        SET status='revoked', revoked_at=now(),
                            revoked_by_user_id=:actor,
                            revocation_reason='local lifecycle test', updated_at=now()
                        WHERE id=:id
                        """
                    ),
                    {"actor": fixture["actor"], "id": first_consent_id},
                )
                second_consent_id = connection.execute(
                    sa.text(
                        """
                        INSERT INTO teacher_voice_consents
                            (teacher_profile_id, consenting_user_id, policy_id, status,
                             source, granted_at)
                        VALUES (:profile, :user_id, :policy, 'granted', 'android', now())
                        RETURNING id
                        """
                    ),
                    {
                        "profile": fixture["profile"],
                        "user_id": fixture["teacher"],
                        "policy": policy_id,
                    },
                ).scalar_one()
            with engine.connect() as connection:
                lifecycle = connection.execute(
                    sa.text(
                        """
                        SELECT status, revoked_at IS NOT NULL
                        FROM teacher_voice_consents
                        WHERE teacher_profile_id=:profile ORDER BY id
                        """
                    ),
                    {"profile": fixture["profile"]},
                ).all()
                results["D"] = lifecycle == [("revoked", True), ("granted", False)]

            invalid_granted = expect_integrity_error(
                engine,
                """
                INSERT INTO teacher_voice_consents
                    (teacher_profile_id, consenting_user_id, policy_id, status,
                     source, granted_at, revoked_at)
                VALUES (:profile, :user_id, :policy, 'granted', 'import', now(), now())
                """,
                {
                    "profile": fixture["second_profile"],
                    "user_id": fixture["actor"],
                    "policy": policy_id,
                },
            )
            invalid_revoked = expect_integrity_error(
                engine,
                """
                INSERT INTO teacher_voice_consents
                    (teacher_profile_id, consenting_user_id, policy_id, status,
                     source, granted_at, revoked_at)
                VALUES (:profile, :user_id, :policy, 'revoked', 'admin_recorded',
                        now(), NULL)
                """,
                {
                    "profile": fixture["second_profile"],
                    "user_id": fixture["actor"],
                    "policy": policy_id,
                },
            )
            results["E"] = invalid_granted and invalid_revoked

            with engine.begin() as connection:
                policy_v2 = connection.execute(
                    sa.text(
                        """
                        INSERT INTO voice_consent_policies
                            (policy_key, version, title, policy_text, content_sha256,
                             effective_at)
                        VALUES
                            ('teacher_voice_processing', '2.0', 'A0.4 Test Policy V2',
                             :text, :digest, now())
                        RETURNING id
                        """
                    ),
                    {"text": policy_text + " v2", "digest": hashlib.sha256((policy_text + " v2").encode()).hexdigest()},
                ).scalar_one()
            duplicate_policy = expect_integrity_error(
                engine,
                """
                INSERT INTO voice_consent_policies
                    (policy_key, version, title, policy_text, content_sha256, effective_at)
                VALUES ('teacher_voice_processing', '1.0', 'Duplicate', :text, :digest, now())
                """,
                {"text": policy_text, "digest": policy_hash},
            )
            with engine.connect() as connection:
                versions = connection.execute(
                    sa.text(
                        """
                        SELECT version FROM voice_consent_policies
                        WHERE policy_key='teacher_voice_processing' ORDER BY version
                        """
                    )
                ).scalars().all()
                results["F"] = policy_v2 != policy_id and versions == ["1.0", "2.0"] and duplicate_policy

            with engine.begin() as connection:
                connection.execute(
                    sa.text(
                        "UPDATE teacher_voice_samples SET voice_consent_id=:consent WHERE id=:sample"
                    ),
                    {"consent": second_consent_id, "sample": fixture["sample"]},
                )
            policy_restricted = expect_integrity_error(
                engine,
                "DELETE FROM voice_consent_policies WHERE id=:id",
                {"id": policy_id},
            )
            with engine.begin() as connection:
                linked = connection.execute(
                    sa.text(
                        "SELECT voice_consent_id FROM teacher_voice_samples WHERE id=:id"
                    ),
                    {"id": fixture["sample"]},
                ).scalar_one()
                connection.execute(
                    sa.text("DELETE FROM teacher_voice_consents WHERE id=:id"),
                    {"id": second_consent_id},
                )
            with engine.connect() as connection:
                sample_link_after_delete = connection.execute(
                    sa.text(
                        "SELECT voice_consent_id FROM teacher_voice_samples WHERE id=:id"
                    ),
                    {"id": fixture["sample"]},
                ).scalar_one()
                revoked_history = connection.execute(
                    sa.text(
                        "SELECT count(*) FROM teacher_voice_consents WHERE id=:id AND status='revoked'"
                    ),
                    {"id": first_consent_id},
                ).scalar_one()
                results["G"] = (
                    linked == second_consent_id
                    and policy_restricted
                    and sample_link_after_delete is None
                    and revoked_history == 1
                )

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
    affected = [
        repr(item) for item in differences
        if "voice_consent_policies" in repr(item)
        or "teacher_voice_consents" in repr(item)
        or "voice_consent_id" in repr(item)
    ]
    unrelated = [repr(item) for item in differences if repr(item) not in affected]
    if affected:
        raise AssertionError("Affected ORM drift: " + repr(affected))
    print("ORM_DRIFT=" + json.dumps({"affected": affected, "unrelated_count": len(unrelated), "unrelated_examples": unrelated[:8]}))
engine.dispose()
'''
            drift_output = run_child(snapshot, database, pgpass, ["-c", drift_script])
            for line in drift_output.splitlines():
                if line.startswith("ORM_DRIFT="):
                    diagnostics["orm_drift"] = json.loads(
                        line.removeprefix("ORM_DRIFT=")
                    )

            migrate(snapshot, database, pgpass, "downgrade", BASELINE_HEAD)
            with engine.connect() as connection:
                inspector = sa.inspect(connection)
                downgraded_tables = set(inspector.get_table_names(schema="public"))
                sample_after_downgrade = connection.execute(
                    sa.text(
                        "SELECT to_jsonb(s)::text FROM teacher_voice_samples s WHERE id=:id"
                    ),
                    {"id": fixture["sample"]},
                ).scalar_one()
                results["J"] = (
                    connection.execute(
                        sa.text("SELECT version_num FROM alembic_version")
                    ).scalar_one() == BASELINE_HEAD
                    and "voice_consent_policies" not in downgraded_tables
                    and "teacher_voice_consents" not in downgraded_tables
                    and {
                        column["name"]
                        for column in inspector.get_columns("teacher_voice_samples")
                    } == before_sample_columns
                    and sample_after_downgrade == fixture["sample_before"]
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

    for label in "ABCDEFGHIJ":
        print(f"TEST_{label}={'PASS' if results.get(label) else 'FAIL'}")
    print("SOURCE_HEAD=" + HEAD)
    print("DIAGNOSTICS=" + json.dumps(diagnostics, ensure_ascii=True, default=str))
    return 0 if all(results.get(label) for label in "ABCDEFGHIJ") else 1


if __name__ == "__main__":
    sys.exit(main())
