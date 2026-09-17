"""Run QBank migrations against local PostgreSQL 16.14 using pgpass.conf.

This runner never loads repository dotenv files and refuses non-loopback servers.
"""

import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

import sqlalchemy as sa
from sqlalchemy.engine import URL

HOST = "localhost"
PORT = 5432
USER = "postgres"
VERSION_NUM = "160014"


def clean_environment(run_id):
    allowed = {
        "SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "COMSPEC",
        "PATHEXT", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "PGPASSFILE",
    }
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    pgpass = Path(env.get("PGPASSFILE") or Path(env["APPDATA"]) / "postgresql" / "pgpass.conf")
    if not pgpass.is_file():
        raise RuntimeError("Local pgpass.conf was not found")
    env.update(
        QBANK_DISPOSABLE_TESTS="1",
        QBANK_TEST_HOST=HOST,
        QBANK_TEST_PORT=str(PORT),
        QBANK_TEST_USER=USER,
        QBANK_TEST_RUN_ID=run_id,
        QBANK_TEST_SERVER_VERSION_NUM=VERSION_NUM,
        QBANK_ALLOW_LOCAL_5432="1",
        PGPASSFILE=str(pgpass),
        PYTHONDONTWRITEBYTECODE="1",
    )
    return env


def local_admin_engine():
    return sa.create_engine(
        URL.create("postgresql+psycopg2", username=USER, host=HOST, port=PORT, database="postgres"),
        isolation_level="AUTOCOMMIT",
        hide_parameters=True,
    )


def cleanup(run_id):
    prefix = "edumind_qbank_" + run_id + "_"
    pattern = re.compile(r"edumind_qbank_" + re.escape(run_id) + r"_[a-f0-9]{16}_test")
    engine = local_admin_engine()
    try:
        with engine.connect() as connection:
            names = connection.execute(
                sa.text("SELECT datname FROM pg_database WHERE datname LIKE :prefix"),
                {"prefix": prefix + "%"},
            ).scalars().all()
            for name in names:
                if not pattern.fullmatch(name):
                    raise RuntimeError("Refusing cleanup of unexpected database name")
                connection.execute(
                    sa.text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=:name AND pid<>pg_backend_pid()"),
                    {"name": name},
                )
                connection.exec_driver_sql('DROP DATABASE "' + name + '"')
                print("Removed disposable database " + name, flush=True)
    finally:
        engine.dispose()


def main():
    run_id = uuid.uuid4().hex[:12]
    try:
        env = clean_environment(run_id)
        os.environ["PGPASSFILE"] = env["PGPASSFILE"]
        engine = local_admin_engine()
        try:
            with engine.connect() as connection:
                row = connection.execute(sa.text(
                    "SELECT host(inet_server_addr()), inet_server_port(), current_user, "
                    "current_database(), current_setting('server_version_num'), "
                    "current_setting('server_version')"
                )).one()
                if row[0] not in ("127.0.0.1", "::1") or row[1] != PORT or row[2] != USER or row[3] != "postgres" or row[4] != VERSION_NUM:
                    raise RuntimeError("Local PostgreSQL identity/version check failed: " + repr(tuple(row)))
                print("LOCAL_POSTGRESQL=" + row[5] + " user=" + row[2] + " database=" + row[3], flush=True)
        finally:
            engine.dispose()

        script = Path(__file__).with_name("test_qbank_migrations.py")
        result = subprocess.run(
            [sys.executable, "-B", str(script)],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=900,
        )
        output = re.sub(r"postgresql(?:\+\w+)?://[^\s]+", "<redacted-database-url>", result.stdout + result.stderr)
        print(output, end="")
        return result.returncode
    except (RuntimeError, subprocess.TimeoutExpired, OSError, ValueError) as exc:
        print("LOCAL VALIDATION BLOCKED: " + str(exc), file=sys.stderr)
        return 1
    finally:
        cleanup(run_id)


if __name__ == "__main__":
    sys.exit(main())
