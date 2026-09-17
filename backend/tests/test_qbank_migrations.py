"""Run directly with unittest; database tests require explicit disposable settings.

No dotenv loading, create_all, stamping, or Supabase access is used here.
"""

import ast
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid

import sqlalchemy as sa
from sqlalchemy.engine import URL
from alembic.migration import MigrationContext
from alembic.operations import Operations

BACKEND = Path(__file__).resolve().parents[1]
VERSIONS = BACKEND / "alembic" / "versions"
Q3 = "0003_placement_qbank"
Q7 = "0007_placement_qbank"
BASELINE_HEAD = "0015_merge_vocabulary_fixed_bank"
COURSE_UNITS_HEAD = "0016_course_units"
ENROLLMENT_HEAD = "0017_course_enrollment_entitlements"
MEDIA_HEAD = "0018_media_storage_metadata"
HEAD = "0019_teacher_voice_consent"
TABLE = "language_placement_question_bank_items"
EXPECTED_GRAPH = {}
for chain in (
    (None, "0001_baseline", "0002_reference_seed", Q3, "0004_reading_v2_foundation"),
    ("0002_reference_seed", "0003_student_listening_content", "0004_language_analytics_xp", "0005_language_progression", "0006_language_listening_reservations", Q7, "0008_speaking_live_budget"),
    ("0008_speaking_live_budget", "0009_grammar_integrity", "0010_grammar_canonical_lessons", "0011_grammar_canonical_lesson_unit_attempts", "0012_grammar_canonical_unit_attempt_truncation", "0013_grammar_lesson_chat"),
    ("0008_speaking_live_budget", "0009_vocabulary_ai_foundation", "0010_vocabulary_mastery_counter", "0011_vocabulary_word_bank", "0012_word_bank_content_item_uniqueness"),
):
    EXPECTED_GRAPH.update({child: parent for parent, child in zip(chain, chain[1:])})
EXPECTED_GRAPH["0014_merge_reading_v2_and_grammar_chat"] = ("0004_reading_v2_foundation", "0013_grammar_lesson_chat")
EXPECTED_GRAPH[BASELINE_HEAD] = ("0014_merge_reading_v2_and_grammar_chat", "0012_word_bank_content_item_uniqueness")
EXPECTED_GRAPH[COURSE_UNITS_HEAD] = BASELINE_HEAD
EXPECTED_GRAPH[ENROLLMENT_HEAD] = COURSE_UNITS_HEAD
EXPECTED_GRAPH[MEDIA_HEAD] = ENROLLMENT_HEAD
EXPECTED_GRAPH[HEAD] = MEDIA_HEAD


def load(path):
    spec = importlib.util.spec_from_file_location("qbank_test_" + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MigrationContractTests(unittest.TestCase):
    def test_exact_graph_and_single_head(self):
        actual = {}
        parents = set()
        for path in VERSIONS.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
            values = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body
                      if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                      and n.targets[0].id in ("revision", "down_revision", "depends_on", "branch_labels")}
            self.assertIsNone(values["depends_on"])
            self.assertIsNone(values["branch_labels"])
            self.assertNotIn(values["revision"], actual)
            actual[values["revision"]] = values["down_revision"]
            parent = values["down_revision"]
            parents.update(parent if isinstance(parent, tuple) else [parent])
        self.assertEqual(EXPECTED_GRAPH, actual)
        self.assertEqual({HEAD}, set(actual) - parents)

    def test_historical_revisions_dispatch_identical_behavior(self):
        bodies = []
        for revision in (Q3, Q7):
            tree = ast.parse((VERSIONS / (revision + ".py")).read_text())
            bodies.append([ast.dump(n) for n in tree.body if isinstance(n, ast.FunctionDef)])
        self.assertEqual(*bodies)
        contract = load(VERSIONS / (Q3 + ".py"))._contract()
        self.assertEqual(28, len(contract.COLUMNS))
        self.assertEqual(6, len(contract.INDEXES))

    def test_helper_is_file_relative_and_application_independent(self):
        with tempfile.TemporaryDirectory(prefix="qbank_portability_") as tmp:
            target = Path(tmp) / "alembic"
            shutil.copytree(BACKEND / "alembic", target, ignore=shutil.ignore_patterns("__pycache__", "versions_archive"))
            for revision in (Q3, Q7):
                module = load(target / "versions" / (revision + ".py"))
                self.assertEqual(TABLE, module._contract().TABLE)
                with self.assertRaisesRegex(RuntimeError, "Downgrade blocked.*shared"):
                    module.downgrade()
        helper = ast.parse((BACKEND / "alembic/qbank_compat_v1.py").read_text())
        imports = []
        for node in ast.walk(helper):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any(name == "app" or name.startswith("app.") for name in imports))


@unittest.skipUnless(os.getenv("QBANK_DISPOSABLE_TESTS") == "1", "explicit local disposable PostgreSQL required")
class PostgreSQLMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        host = os.environ.get("QBANK_TEST_HOST", "127.0.0.1")
        port = int(os.environ["QBANK_TEST_PORT"])
        if host not in ("127.0.0.1", "localhost") or port == 5432:
            if host not in ("127.0.0.1", "localhost") or os.environ.get("QBANK_ALLOW_LOCAL_5432") != "1":
                raise RuntimeError("Refusing non-loopback or unapproved PostgreSQL port")
        cls.password = os.environ.get("QBANK_TEST_PASSWORD")
        cls.user = os.environ.get("QBANK_TEST_USER", "qbank_test")
        cls.run_id = os.environ.get("QBANK_TEST_RUN_ID", uuid.uuid4().hex[:12])
        if not re.fullmatch(r"[a-f0-9]{12}", cls.run_id):
            raise RuntimeError("QBANK_TEST_RUN_ID must be a 12-character lowercase hex value")
        cls.base_url = URL.create("postgresql+psycopg2", username=cls.user, password=cls.password, host=host, port=port, database="postgres")
        cls.admin = sa.create_engine(cls.base_url, isolation_level="AUTOCOMMIT", hide_parameters=True)
        with cls.admin.connect() as conn:
            version = conn.execute(sa.text("SELECT current_setting('server_version_num')")).scalar_one()
            expected = os.environ.get("QBANK_TEST_SERVER_VERSION_NUM", "170006")
            if version != expected:
                raise RuntimeError("Disposable PostgreSQL version mismatch: expected " + expected + "; found " + version)
        cls.databases = []
        cls.temp = tempfile.TemporaryDirectory(prefix="edumind_qbank_replay_")
        cls.snapshot = Path(cls.temp.name) / "backend"
        cls.snapshot.mkdir()
        for name in ("app", "alembic"):
            shutil.copytree(BACKEND / name, cls.snapshot / name,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".env", ".env.*", "versions_archive"))
        shutil.copy2(BACKEND / "alembic.ini", cls.snapshot / "alembic.ini")
        if any(p.exists() for p in (cls.snapshot / ".env", cls.snapshot.parent / ".env")):
            raise RuntimeError("Disposable snapshot must not have dotenv files")
        cls.modules = [load(cls.snapshot / "alembic/versions" / (r + ".py")) for r in (Q3, Q7)]

    @classmethod
    def tearDownClass(cls):
        for name in cls.databases:
            assert re.fullmatch(
                r"edumind_qbank_" + re.escape(cls.run_id) + r"_[a-f0-9]{16}_test",
                name,
            )
            with cls.admin.connect() as conn:
                conn.exec_driver_sql('DROP DATABASE "' + name + '" WITH (FORCE)')
        cls.admin.dispose()
        cls.temp.cleanup()

    def new_database(self):
        name = "edumind_qbank_" + self.run_id + "_" + uuid.uuid4().hex[:16] + "_test"
        with self.admin.connect() as conn:
            conn.exec_driver_sql('CREATE DATABASE "' + name + '"')
        self.databases.append(name)
        return name

    def engine(self, name):
        return sa.create_engine(self.base_url.set(database=name), hide_parameters=True)

    def child_env(self, name):
        allowed = {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "COMSPEC", "PATHEXT", "USERPROFILE"}
        env = {k: v for k, v in os.environ.items() if k.upper() in allowed}
        sync = self.base_url.set(database=name).render_as_string(hide_password=False)
        async_url = self.base_url.set(database=name, drivername="postgresql+asyncpg").render_as_string(hide_password=False)
        env.update(SYNC_DATABASE_URL=sync, DATABASE_URL_SYNC=sync, DATABASE_URL=async_url,
                   JWT_SECRET=secrets.token_hex(32), DEBUG="true", PYTHONDONTWRITEBYTECODE="1",
                   ENABLE_FAISS="false", ENABLE_WHISPER="false", ENABLE_EMBEDDINGS="false")
        return env

    def run_child(self, name, args, success=True):
        result = subprocess.run([sys.executable, "-B", *args], cwd=self.snapshot,
                                env=self.child_env(name), capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=180)
        output = result.stdout + result.stderr
        if self.password:
            output = output.replace(self.password, "<redacted>")
        output = re.sub(r"postgresql(?:\+\w+)?://[^\s]+", "<redacted-database-url>", output)
        if success:
            self.assertEqual(0, result.returncode, output)
        else:
            self.assertNotEqual(0, result.returncode, output)
        return output

    def migrate(self, name, target="head", operation="upgrade", success=True):
        return self.run_child(name, ["-m", "alembic", operation, target], success)

    def insert_fixture(self, name):
        engine = self.engine(name)
        try:
            with engine.begin() as conn:
                return conn.execute(sa.text("INSERT INTO public." + TABLE +
                    " (language_id,skill,level,prompt_text,stable_key) VALUES (1,'reading','A1','Preserve this fixture','repair-fixture') RETURNING id")).scalar_one()
        finally:
            engine.dispose()

    def snapshot_table(self, conn):
        return {
            "rows": conn.execute(sa.text("SELECT row_to_json(q) FROM public." + TABLE + " q ORDER BY id")).scalars().all(),
            "columns": [tuple(r) for r in conn.execute(sa.text("SELECT column_name,udt_schema,udt_name,is_nullable,character_maximum_length,column_default,is_identity FROM information_schema.columns WHERE table_schema='public' AND table_name=:table ORDER BY ordinal_position"), {"table": TABLE})],
            "indexes": [tuple(r) for r in conn.execute(sa.text("SELECT indexname,indexdef FROM pg_indexes WHERE schemaname='public' AND tablename=:table ORDER BY indexname"), {"table": TABLE})],
            "constraints": [tuple(r) for r in conn.execute(sa.text("SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid=to_regclass(:table) ORDER BY conname"), {"table": "public." + TABLE})],
            "sequence": tuple(conn.execute(sa.text("SELECT last_value,is_called FROM public." + TABLE + "_id_seq")).one()),
            "oid": conn.execute(sa.text("SELECT to_regclass(:table)::oid"), {"table": "public." + TABLE}).scalar_one(),
        }

    def assert_head(self, name, fixture_id=None):
        engine = self.engine(name)
        try:
            with engine.connect() as conn:
                self.assertEqual([HEAD], conn.execute(sa.text("SELECT version_num FROM public.alembic_version")).scalars().all())
                names = set(sa.inspect(conn).get_table_names(schema="public"))
                self.assertEqual(133, len(names))
                language = {n for n in names if n == "languages" or n.startswith(("language_", "grammar_", "speaking_live_"))}
                self.assertEqual(56, len(language))
                critical = {"users", "teacher_profiles", "student_profiles", "subjects", "courses", "lessons", "student_course_access", "lesson_assets", "media_objects", "content_chunks", "ai_jobs", "quiz_questions", "quiz_attempts", "course_quizzes", "course_quiz_questions", "course_quiz_attempts", "course_quiz_answers", "conversation_threads", "conversation_participants", "conversation_messages", "notifications"}
                self.assertTrue(critical <= names)
                self.assertEqual({"student", "teacher", "parent", "admin", "support"}, set(conn.execute(sa.text("SELECT slug FROM public.roles")).scalars()))
                for table, count in {"languages": 1, "language_products": 1, "language_placement_sections": 4, "language_placement_questions": 26, "language_conversation_scenarios": 13}.items():
                    self.assertEqual(count, conn.execute(sa.text("SELECT count(*) FROM public." + table)).scalar_one(), table)
                self.assertGreater(conn.execute(sa.text("SELECT count(*) FROM public.language_content_items")).scalar_one(), 0)
                self.assertEqual(0, conn.execute(sa.text("SELECT count(*) FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname='public' AND NOT convalidated")).scalar_one())
                self.assertTrue(sa.inspect(conn).get_foreign_keys("lessons"))
                self.assertTrue(sa.inspect(conn).get_foreign_keys("student_course_access"))
                before = self.snapshot_table(conn)
                for module in self.modules:
                    with Operations.context(MigrationContext.configure(conn)):
                        module.upgrade()
                        module.upgrade()
                        with self.assertRaisesRegex(RuntimeError, "Downgrade blocked.*shared"):
                            module.downgrade()
                    self.assertEqual(before, self.snapshot_table(conn))
                if fixture_id is not None:
                    self.assertEqual(fixture_id, before["rows"][0]["id"])
                    self.assertEqual("Preserve this fixture", before["rows"][0]["prompt_text"])
                result = conn.execute(sa.text("INSERT INTO public." + TABLE + " (language_id,skill,level,prompt_text) VALUES (1,'reading','A1','Sequence check') RETURNING id")).scalar_one()
                self.assertGreater(result, fixture_id or 0)
                conn.rollback()
        finally:
            engine.dispose()

    def test_clean_replay_and_orm_parity(self):
        name = self.new_database()
        self.migrate(name)
        self.assert_head(name)
        script = """
import json
from sqlalchemy import create_engine
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from app import models
from app.db.base import Base
import os
engine=create_engine(os.environ['SYNC_DATABASE_URL'],hide_parameters=True)
with engine.connect() as conn:
    qbank=lambda obj,name,type_,reflected,compare_to: (name=='language_placement_question_bank_items' if type_=='table' else True)
    ctx=MigrationContext.configure(conn,opts={'compare_type':True,'compare_server_default':True,'include_object':qbank})
    focused=compare_metadata(ctx,Base.metadata)
    if focused: raise AssertionError('QBank ORM drift: '+repr(focused))
    full=compare_metadata(MigrationContext.configure(conn,opts={'compare_type':True,'compare_server_default':True}),Base.metadata)
    print('ORM_PARITY_REPORT='+json.dumps({'qbank_differences':0,'full_differences':[repr(d) for d in full]}))
engine.dispose()
"""
        output = self.run_child(name, ["-c", script])
        for line in output.splitlines():
            if line.startswith("ORM_PARITY_REPORT="):
                print(line, flush=True)

    def historical_path(self, revision, parent):
        name = self.new_database()
        self.migrate(name, revision)
        fixture = self.insert_fixture(name)
        output = self.migrate(name, parent, operation="downgrade", success=False)
        self.assertIn("Downgrade blocked at " + revision, output)
        engine = self.engine(name)
        try:
            with engine.connect() as conn:
                self.assertEqual([revision], conn.execute(sa.text("SELECT version_num FROM public.alembic_version")).scalars().all())
        finally:
            engine.dispose()
        self.migrate(name)
        self.assert_head(name, fixture)

    def test_0003_first(self):
        self.historical_path(Q3, "0002_reference_seed")

    def test_0007_first(self):
        self.historical_path(Q7, "0006_language_listening_reservations")

    def test_both_revision_identities_and_repeat_head(self):
        name = self.new_database()
        self.migrate(name, Q3)
        fixture = self.insert_fixture(name)
        self.migrate(name, Q7)
        engine = self.engine(name)
        try:
            with engine.connect() as conn:
                self.assertEqual({Q3, Q7}, set(conn.execute(sa.text("SELECT version_num FROM public.alembic_version")).scalars()))
        finally:
            engine.dispose()
        self.migrate(name)
        self.assert_head(name, fixture)
        self.migrate(name)
        self.assert_head(name, fixture)

    def test_schema_drift_is_rejected_without_changes(self):
        name = self.new_database()
        self.migrate(name)
        self.insert_fixture(name)
        table = "public." + TABLE
        cases = {
            "missing column": [f"ALTER TABLE {table} DROP COLUMN reviewer_note"],
            "nullable": [f"ALTER TABLE {table} ALTER COLUMN prompt_text DROP NOT NULL"],
            "varchar length": [f"ALTER TABLE {table} ALTER COLUMN skill TYPE varchar(40)"],
            "default": [f"ALTER TABLE {table} ALTER COLUMN usage_count SET DEFAULT 9"],
            "sequence": [f"ALTER TABLE {table} ALTER COLUMN id DROP DEFAULT"],
            "sequence increment": [f"ALTER SEQUENCE {table}_id_seq INCREMENT BY 2"],
            "foreign target": [f"ALTER TABLE {table} DROP CONSTRAINT {TABLE}_language_id_fkey", f"ALTER TABLE {table} ADD FOREIGN KEY (language_id) REFERENCES public.roles(id) ON DELETE CASCADE"],
            "delete action": [f"ALTER TABLE {table} DROP CONSTRAINT {TABLE}_media_object_id_fkey", f"ALTER TABLE {table} ADD FOREIGN KEY (media_object_id) REFERENCES public.media_objects(id) ON DELETE CASCADE"],
            "unique missing": [f"ALTER TABLE {table} DROP CONSTRAINT {TABLE}_stable_key_key"],
            "index columns": ["DROP INDEX public.ix_lpq_bank_lookup", f"CREATE INDEX ix_lpq_bank_lookup ON {table} (skill,language_id,level,is_verified,is_active)"],
            "index order": ["DROP INDEX public.ix_lpq_bank_lookup", f"CREATE INDEX ix_lpq_bank_lookup ON {table} (language_id DESC,skill,level,is_verified,is_active)"],
            "index uniqueness": ["DROP INDEX public.ix_lpq_bank_lookup", f"CREATE UNIQUE INDEX ix_lpq_bank_lookup ON {table} (language_id,skill,level,is_verified,is_active)"],
            "index expression": ["DROP INDEX public.ix_lpq_bank_lookup", f"CREATE INDEX ix_lpq_bank_lookup ON {table} (language_id,lower(skill),level,is_verified,is_active)"],
            "enum schema": ["CREATE SCHEMA qbank_drift", "CREATE TYPE qbank_drift.language_level AS ENUM ('A1','A2','B1','B2','C1','C2')", f"ALTER TABLE {table} ALTER COLUMN level TYPE qbank_drift.language_level USING level::text::qbank_drift.language_level"],
            "enum labels": ["ALTER TYPE public.language_level RENAME VALUE 'C2' TO 'C3'"],
        }
        engine = self.engine(name)
        try:
            for label, statements in cases.items():
                with self.subTest(drift=label), engine.connect() as conn:
                    tx = conn.begin()
                    try:
                        for statement in statements:
                            conn.exec_driver_sql(statement)
                        before = self.snapshot_table(conn)
                        for module in self.modules:
                            with Operations.context(MigrationContext.configure(conn)):
                                with self.assertRaisesRegex(RuntimeError, "QBank schema drift:"):
                                    module.upgrade()
                            self.assertEqual(before, self.snapshot_table(conn))
                    finally:
                        tx.rollback()
            self.assert_head(name, 1)
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main(verbosity=2)
