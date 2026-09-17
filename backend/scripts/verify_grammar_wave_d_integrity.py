"""Verify Wave D — Production Integrity Hardening.

Usage (from backend/):
    python scripts/verify_grammar_wave_d_integrity.py
"""

from __future__ import annotations

import ast
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"
INTEGRITY = SERVICES / "language_grammar_integrity"
CURRICULUM = BACKEND / "curriculum" / "english" / "grammar"
API_FILE = BACKEND / "app" / "api" / "language_grammar_student.py"
SCHEMA_FILE = BACKEND / "app" / "schemas" / "language_grammar_student.py"


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"  {name}: {status}{suffix}")
    return passed


def _parse_imports(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app.services."):
            parts = node.module.split(".")
            if len(parts) >= 3:
                imports.add(parts[2])
    return imports


def audit_architecture() -> list[bool]:
    print("[Audit 0 - Wave D architecture]")
    results: list[bool] = []
    for name in (
        "__init__.py",
        "types.py",
        "stamp.py",
        "sessions.py",
        "ledger.py",
        "attested_completion.py",
        "curriculum_version.py",
        "errors.py",
    ):
        results.append(_ok(f"package file {name}", (INTEGRITY / name).is_file()))

    from app.services.language_grammar.ownership import (
        ALLOWED_PACKAGE_DEPENDENCIES,
        FORBIDDEN_MASTERY_WRITERS,
        PACKAGE_LAYER,
        PACKAGE_OWNERSHIP,
    )

    results.append(_ok("ownership entry", "language_grammar_integrity" in PACKAGE_OWNERSHIP))
    results.append(
        _ok(
            "layer integrity",
            PACKAGE_LAYER.get("language_grammar_integrity") == "integrity",
        )
    )
    results.append(
        _ok(
            "forbidden mastery writer",
            "language_grammar_integrity" in FORBIDDEN_MASTERY_WRITERS,
        )
    )
    deps = ALLOWED_PACKAGE_DEPENDENCIES.get("language_grammar_integrity", frozenset())
    results.append(
        _ok(
            "integrity deps allowed",
            "language_grammar_pipeline" in deps and "language_grammar_skill_context" in deps,
            str(sorted(deps)),
        )
    )

    mig = BACKEND / "alembic" / "versions" / "0009_grammar_integrity.py"
    results.append(_ok("alembic 0009 exists", mig.is_file()))
    if mig.is_file():
        text = mig.read_text(encoding="utf-8")
        results.append(_ok("ledger table in migration", "grammar_evidence_ledger" in text))
        results.append(_ok("sessions table in migration", "grammar_activity_sessions" in text))
        results.append(
            _ok(
                "unique student+observation",
                "uq_grammar_evidence_ledger_student_obs" in text,
            )
        )

    model = BACKEND / "app" / "models" / "language" / "grammar_integrity.py"
    results.append(_ok("SQLAlchemy models exist", model.is_file()))

    schema = SCHEMA_FILE.read_text(encoding="utf-8")
    results.append(_ok("complete schema has activity_session_id", "activity_session_id" in schema))
    results.append(
        _ok(
            "complete schema has no client grammar_id field",
            "grammar_id: str" not in schema.split("class GrammarActivityCompleteIn")[1].split("class ")[0]
            if "class GrammarActivityCompleteIn" in schema
            else False,
        )
    )
    results.append(
        _ok(
            "complete schema has no client score field",
            "score:" not in schema.split("class GrammarActivityCompleteIn")[1].split("class ")[0]
            if "class GrammarActivityCompleteIn" in schema
            else False,
        )
    )

    api = API_FILE.read_text(encoding="utf-8")
    results.append(_ok("API uses activity_session_id", "activity_session_id=body.activity_session_id" in api))

    speaking_engine = (
        SERVICES / "language_speaking_curriculum_engine" / "engine.py"
    ).read_text(encoding="utf-8")
    results.append(
        _ok(
            "speaking enrich does not call select_grammar_targets",
            "select_grammar_targets(" not in speaking_engine,
        )
    )
    author = (
        SERVICES / "language_speaking_educational_package" / "author_pipeline.py"
    ).read_text(encoding="utf-8")
    results.append(_ok("speaking fail-closed on empty resolver", "resolver_empty_fail_closed" in author))

    prog = (SERVICES / "language_grammar_progression" / "service.py").read_text(encoding="utf-8")
    results.append(
        _ok(
            "progression has readonly loader",
            "load_grammar_progression_snapshot_readonly" in prog,
        )
    )
    mastery = (SERVICES / "language_grammar_mastery" / "service.py").read_text(encoding="utf-8")
    # get_grammar_mastery_snapshot must not lock
    snap_fn = mastery.split("async def get_grammar_mastery_snapshot", 1)[1].split(
        "\nasync def ", 1
    )[0]
    results.append(
        _ok(
            "mastery snapshot read has no FOR UPDATE lock call",
            "lock_grammar_mastery_row" not in snap_fn,
        )
    )

    results.append(_ok("curriculum still 53 topics", len(list(CURRICULUM.glob("gram_*.yaml"))) == 53))
    return results


def test_stamp_security() -> list[bool]:
    print("[P0-2 - Signed stamps]")
    results: list[bool] = []
    from app.services.language_grammar_integrity import (
        GrammarIntegrityError,
        issue_signed_stamp,
        verify_signed_stamp,
    )

    token = issue_signed_stamp(
        session_id="11111111-1111-1111-1111-111111111111",
        student_id=42,
        language_id=1,
        grammar_id="gram_present_perfect",
        skill="reading",
        curriculum_version="1.1.0",
    )
    claims = verify_signed_stamp(token, expected_student_id=42, expected_grammar_id="gram_present_perfect")
    results.append(_ok("valid stamp verifies", claims.grammar_id == "gram_present_perfect"))

    try:
        verify_signed_stamp(token + "x", expected_student_id=42)
        results.append(_ok("forged stamp rejected", False))
    except GrammarIntegrityError as exc:
        results.append(_ok("forged stamp rejected", exc.code == "stamp_forged", exc.code))

    try:
        verify_signed_stamp(token, expected_student_id=99)
        results.append(_ok("student mismatch rejected", False))
    except GrammarIntegrityError as exc:
        results.append(_ok("student mismatch rejected", exc.code == "stamp_student_mismatch", exc.code))

    try:
        verify_signed_stamp(token, expected_grammar_id="gram_past_simple")
        results.append(_ok("grammar mismatch rejected", False))
    except GrammarIntegrityError as exc:
        results.append(_ok("grammar mismatch rejected", exc.code == "stamp_grammar_mismatch", exc.code))

    expired = issue_signed_stamp(
        session_id="11111111-1111-1111-1111-111111111111",
        student_id=42,
        language_id=1,
        grammar_id="gram_present_perfect",
        skill="reading",
        curriculum_version="1.1.0",
        ttl_seconds=60,
        now=1_000_000,
    )
    try:
        verify_signed_stamp(expired, expected_student_id=42, now=1_000_000 + 120)
        results.append(_ok("expired stamp rejected", False))
    except GrammarIntegrityError as exc:
        results.append(_ok("expired stamp rejected", exc.code == "stamp_expired", exc.code))
    return results


def test_schema_forges() -> list[bool]:
    print("[P0-1 - Client forgeries rejected at schema/API contract]")
    results: list[bool] = []
    from app.schemas.language_grammar_student import GrammarActivityCompleteIn
    from pydantic import ValidationError

    ok = GrammarActivityCompleteIn(activity_session_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    results.append(_ok("session-only complete accepted", bool(ok.activity_session_id)))

    try:
        GrammarActivityCompleteIn(  # type: ignore[call-arg]
            activity_session_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            grammar_id="gram_present_perfect",
            score=100.0,
        )
        # Pydantic v2 ignores extra by default unless configured — check model fields
        fields = set(GrammarActivityCompleteIn.model_fields)
        results.append(_ok("schema has no grammar_id field", "grammar_id" not in fields))
        results.append(_ok("schema has no score field", "score" not in fields))
    except ValidationError:
        results.append(_ok("schema has no grammar_id field", True))
        results.append(_ok("schema has no score field", True))

    fields = set(GrammarActivityCompleteIn.model_fields)
    results.append(_ok("forged grammar_id not in schema", "grammar_id" not in fields))
    results.append(_ok("forged score not in schema", "score" not in fields))
    return results


def test_speaking_dual_authority_removed() -> list[bool]:
    print("[P0-3 - Speaking dual authority removed]")
    results: list[bool] = []
    src = (SERVICES / "language_speaking_curriculum_engine" / "engine.py").read_text(encoding="utf-8")
    results.append(
        _ok(
            "enrich does not call select_grammar_targets",
            "select_grammar_targets(" not in src,
        )
    )
    results.append(
        _ok(
            "enrich clears pack grammar authority",
            "NEVER choose grammar" in src or "must NEVER choose grammar" in src,
        )
    )
    catalog = (
        SERVICES / "language_speaking_curriculum_engine" / "grammar_catalog.py"
    ).read_text(encoding="utf-8")
    results.append(
        _ok(
            "select_grammar_targets documented as non-product",
            "must NOT call" in catalog or "product paths must NOT" in catalog,
        )
    )
    return results


def test_readonly_resolve() -> list[bool]:
    print("[P1-3 - Resolver reads do not write]")
    results: list[bool] = []
    integ = (SERVICES / "language_grammar_integration" / "service.py").read_text(encoding="utf-8")
    resolve_fn = integ.split("async def resolve_targets", 1)[1].split("\nasync def ", 1)[0].split(
        "\nclass ", 1
    )[0]
    results.append(
        _ok(
            "resolve_targets does not call evaluate_and_persist",
            "evaluate_and_persist" not in resolve_fn,
        )
    )
    results.append(
        _ok(
            "resolve uses get_grammar_progression_snapshot",
            "get_grammar_progression_snapshot" in resolve_fn,
        )
    )
    return results


def test_curriculum_version_pin() -> list[bool]:
    print("[P1-5 - Curriculum version pinning]")
    results: list[bool] = []
    from app.services.language_grammar_integrity import (
        CURRICULUM_VERSION_PIN,
        get_curriculum_version,
    )

    ver = get_curriculum_version()
    results.append(_ok("curriculum version non-empty", bool(ver)))
    results.append(_ok("pin constant set", CURRICULUM_VERSION_PIN == "1.1.0"))
    results.append(_ok("version looks like semver", "." in ver))
    return results


def test_attested_score_ignores_client() -> list[bool]:
    print("[P0-1 - Server score from session; client score ignored]")
    results: list[bool] = []
    from app.services.language_grammar_integrity.attested_completion import resolve_server_score

    async def _run():
        score = await resolve_server_score(
            skill="reading",
            server_payload={"answer_key": {"q1": 0, "q2": 1}},
            answers={"q1": {"choice_index": 0}, "q2": {"choice_index": 0}},
            response_text="",
            server_score=None,
        )
        return score

    score = asyncio.run(_run())
    results.append(_ok("server scores answers", abs(score - 50.0) < 0.01, str(score)))

    async def _override():
        return await resolve_server_score(
            skill="reading",
            server_payload={},
            answers=None,
            response_text="",
            server_score=88.0,
        )

    results.append(_ok("trusted server_score used", abs(asyncio.run(_override()) - 88.0) < 0.01))
    return results


def test_vocab_rejects_client_grammar() -> list[bool]:
    print("[P0-2 - Vocabulary forged stamp rejected]")
    results: list[bool] = []
    src = (SERVICES / "language_vocabulary_service.py").read_text(encoding="utf-8")
    results.append(
        _ok(
            "vocab submit rejects client grammar_id",
            "Client grammar_id is not accepted" in src,
        )
    )
    results.append(_ok("vocab submit uses activity_session_id", "activity_session_id" in src))
    results.append(
        _ok(
            "vocab no longer sets stamped=client",
            "stamped_grammar_id=stamped" not in src,
        )
    )
    return results


def test_speaking_forged_grammar() -> list[bool]:
    print("[P0-3 - Forged speaking grammar rejected]")
    results: list[bool] = []
    src = (
        SERVICES / "language_speaking_educational_package" / "author_pipeline.py"
    ).read_text(encoding="utf-8")
    results.append(_ok("forged speaking grammar string present", "forged_speaking_grammar" in src))
    results.append(_ok("fail closed reason present", "resolver_empty_fail_closed" in src))
    return results


def test_ownership_enforcement_static() -> list[bool]:
    print("[P1-4 - Activity/student ownership checks]")
    results: list[bool] = []
    progress = (SERVICES / "language_skill_progress_service.py").read_text(encoding="utf-8")
    results.append(_ok("reading checks activity_ownership", "activity_ownership" in progress))
    results.append(_ok("listening checks activity_ownership", "does not match this listening" in progress))
    writing = (SERVICES / "language_writing_service.py").read_text(encoding="utf-8")
    results.append(_ok("writing checks activity_ownership", "activity_ownership" in writing))
    sessions = (INTEGRITY / "sessions.py").read_text(encoding="utf-8")
    results.append(_ok("session enforces student_ownership", "student_ownership" in sessions))
    return results


def test_ledger_append_only_static() -> list[bool]:
    print("[P1-1/P1-2 - Evidence ledger + replay]")
    results: list[bool] = []
    ledger = (INTEGRITY / "ledger.py").read_text(encoding="utf-8")
    results.append(_ok("ledger uses savepoint", "begin_nested" in ledger))
    results.append(_ok("ledger returns duplicate", 'return "duplicate"' in ledger))
    results.append(_ok("ledger is insert-only helper", "db.add(row)" in ledger and ".update(" not in ledger))
    attested = (INTEGRITY / "attested_completion.py").read_text(encoding="utf-8")
    results.append(_ok("attested uses try_append_evidence", "try_append_evidence" in attested))
    results.append(_ok("duplicate observation error", "duplicate_observation" in attested))
    return results


def main() -> int:
    print("=== Wave D — Production Integrity Hardening ===\n")
    all_results: list[bool] = []
    all_results.extend(audit_architecture())
    all_results.extend(test_stamp_security())
    all_results.extend(test_schema_forges())
    all_results.extend(test_speaking_dual_authority_removed())
    all_results.extend(test_readonly_resolve())
    all_results.extend(test_curriculum_version_pin())
    all_results.extend(test_attested_score_ignores_client())
    all_results.extend(test_vocab_rejects_client_grammar())
    all_results.extend(test_speaking_forged_grammar())
    all_results.extend(test_ownership_enforcement_static())
    all_results.extend(test_ledger_append_only_static())

    passed = sum(1 for r in all_results if r)
    total = len(all_results)
    print(f"\n=== RESULT: {passed}/{total} PASS ===")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
