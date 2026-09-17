"""Offline canonical grammar lesson authoring workflow CLI.

Usage from repo root:
    backend/.venv311/Scripts/python.exe backend/scripts/grammar_canonical_lessons.py --help

This operator tool never runs in student runtime. Real sectioned provider calls
require --real-provider plus --confirm-outbound-claude so tests cannot call
Claude by accident.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.language_grammar_canonical_authoring import (  # noqa: E402
    ExistingLLMCanonicalAuthoringAdapter,
    ExistingLLMSectionedCanonicalAuthoringAdapter,
    FixtureCanonicalAuthoringAdapter,
    FixtureSectionedCanonicalAuthoringAdapter,
    GrammarCanonicalAuthoringWorkflowError,
)
from app.services.language_grammar_canonical_authoring.sectioned_workflow import (  # noqa: E402
    assemble_sectioned_revision,
    generate_sectioned_draft_revision,
    inspect_unit_attempt,
    list_revision_unit_attempts,
    retry_unit_attempt,
    supersede_unit_attempt,
)
from app.services.language_grammar_canonical_authoring.workflow import (  # noqa: E402
    archive_canonical_revision,
    ensure_identity,
    generate_draft_revision,
    inspect_revision,
    list_canonical_revisions,
    publish_revision,
    retry_failed_revision,
    validate_revision,
)
from app.services.language_grammar_canonical_authoring.types import (  # noqa: E402
    CanonicalLessonIdentityInput,
    DEFAULT_METHODOLOGY_VERSION,
)
from app.services.language_grammar_canonical_lessons import GrammarCanonicalLessonError  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline canonical grammar lesson authoring workflow")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_identity_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--grammar-id", required=True)
        p.add_argument("--cefr-level", required=True)
        p.add_argument("--locale", default="ar-SY")
        p.add_argument("--methodology-version", default=DEFAULT_METHODOLOGY_VERSION)

    identity = sub.add_parser("identity", help="Create or retrieve canonical lesson identity")
    add_identity_args(identity)

    generate = sub.add_parser("generate-draft", help="Create and validate a new draft revision")
    add_identity_args(generate)
    adapter = generate.add_mutually_exclusive_group(required=True)
    adapter.add_argument("--fixture-json", help="Local fixture JSON file; never calls a provider")
    adapter.add_argument("--real-provider", action="store_true", help="Explicitly use configured real provider")
    generate.add_argument("--provider-id", default="")
    generate.add_argument("--artifact-dir", default="")

    sectioned = sub.add_parser("generate-sectioned-draft", help="Create a sectioned canonical draft revision")
    add_identity_args(sectioned)
    sectioned_adapter = sectioned.add_mutually_exclusive_group(required=True)
    sectioned_adapter.add_argument("--fixture-json", help="Local sectioned fixture JSON file; never calls a provider")
    sectioned_adapter.add_argument("--real-provider", action="store_true", help="Explicitly use configured Claude provider")
    sectioned.add_argument("--confirm-outbound-claude", action="store_true", help="Required with --real-provider")
    sectioned.add_argument("--artifact-dir", default="")

    validate = sub.add_parser("validate", help="Validate an existing revision")
    validate.add_argument("--revision-id", required=True)

    inspect = sub.add_parser("inspect", help="Print student-safe revision inspection")
    inspect.add_argument("--revision-id", required=True)
    inspect.add_argument("--private-diagnostics", action="store_true")
    inspect.add_argument("--write-artifact", action="store_true")
    inspect.add_argument("--write-html-artifact", action="store_true")
    inspect.add_argument("--artifact-dir", default="")

    publish = sub.add_parser("publish", help="Publish a reviewable revision")
    publish.add_argument("--revision-id", required=True)

    archive = sub.add_parser("archive", help="Archive a revision")
    archive.add_argument("--revision-id", required=True)

    list_cmd = sub.add_parser("list", help="List concise revision metadata")
    list_cmd.add_argument("--grammar-id", default="")
    list_cmd.add_argument("--cefr-level", default="")
    list_cmd.add_argument("--locale", default="")
    list_cmd.add_argument("--methodology-version", default="")
    list_cmd.add_argument("--status", default="")

    retry = sub.add_parser("retry", help="Create a new draft revision from a failed or stale generating revision")
    retry.add_argument("--revision-id", required=True)

    units = sub.add_parser("units", help="List unit attempts for a revision")
    units.add_argument("--revision-id", required=True)
    units.add_argument("--unit-key", default="")

    inspect_unit = sub.add_parser("inspect-unit", help="Inspect one unit attempt safely")
    inspect_unit.add_argument("--attempt-id", required=True)
    inspect_unit.add_argument("--private-diagnostics", action="store_true")

    retry_unit = sub.add_parser("retry-unit", help="Retry one failed sectioned unit")
    retry_unit.add_argument("--revision-id", required=True)
    retry_unit.add_argument("--unit-key", required=True)
    retry_unit_adapter = retry_unit.add_mutually_exclusive_group(required=True)
    retry_unit_adapter.add_argument("--fixture-json", help="Local sectioned fixture JSON file; never calls a provider")
    retry_unit_adapter.add_argument("--real-provider", action="store_true", help="Explicitly use configured Claude provider")
    retry_unit.add_argument("--confirm-outbound-claude", action="store_true", help="Required with --real-provider")
    retry_unit.add_argument("--supersede-accepted", action="store_true")
    retry_unit.add_argument("--artifact-dir", default="")

    assemble = sub.add_parser("assemble", help="Assemble accepted sectioned units into a reviewable revision")
    assemble.add_argument("--revision-id", required=True)

    supersede = sub.add_parser("supersede-unit", help="Explicitly supersede an accepted unit attempt")
    supersede.add_argument("--attempt-id", required=True)

    return parser


async def run_command(args: argparse.Namespace) -> int:
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            result = await _dispatch(db, args)
            await db.commit()
        except (GrammarCanonicalAuthoringWorkflowError, GrammarCanonicalLessonError, ValueError) as exc:
            await db.rollback()
            _print_json({"ok": False, "error": _safe_error(exc), "message": str(exc)})
            return 1
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            _print_json({"ok": False, "error": "unexpected_error", "message": str(exc)[:300]})
            return 1
    _print_json({"ok": result.ok, "message": result.message, **result.data})
    return 0 if result.ok else 1


async def _dispatch(db, args: argparse.Namespace):
    if args.command == "identity":
        return await ensure_identity(db, _identity_from_args(args))
    if args.command == "generate-draft":
        adapter = (
            FixtureCanonicalAuthoringAdapter(args.fixture_json)
            if args.fixture_json
            else ExistingLLMCanonicalAuthoringAdapter(provider_id=args.provider_id or None)
        )
        return await generate_draft_revision(
            db,
            identity=_identity_from_args(args),
            adapter=adapter,
            artifact_dir=Path(args.artifact_dir) if args.artifact_dir else None,
        )
    if args.command == "generate-sectioned-draft":
        if args.real_provider and not args.confirm_outbound_claude:
            raise ValueError("--real-provider requires --confirm-outbound-claude for sectioned authoring")
        adapter = (
            FixtureSectionedCanonicalAuthoringAdapter(args.fixture_json)
            if args.fixture_json
            else ExistingLLMSectionedCanonicalAuthoringAdapter(allow_outbound=True, max_calls=6)
        )
        return await generate_sectioned_draft_revision(
            db,
            identity=_identity_from_args(args),
            adapter=adapter,
            artifact_dir=Path(args.artifact_dir) if args.artifact_dir else None,
        )
    if args.command == "validate":
        return await validate_revision(db, revision_id=_uuid(args.revision_id))
    if args.command == "inspect":
        return await inspect_revision(
            db,
            revision_id=_uuid(args.revision_id),
            include_private_diagnostics=bool(args.private_diagnostics),
            write_artifact=bool(args.write_artifact),
            write_html_artifact=bool(args.write_html_artifact),
            artifact_dir=Path(args.artifact_dir) if args.artifact_dir else None,
        )
    if args.command == "publish":
        return await publish_revision(db, revision_id=_uuid(args.revision_id))
    if args.command == "archive":
        return await archive_canonical_revision(db, revision_id=_uuid(args.revision_id))
    if args.command == "list":
        return await list_canonical_revisions(
            db,
            grammar_id=args.grammar_id or None,
            cefr_level=args.cefr_level or None,
            locale=args.locale or None,
            methodology_version=args.methodology_version or None,
            status=args.status or None,
        )
    if args.command == "retry":
        return await retry_failed_revision(db, revision_id=_uuid(args.revision_id))
    if args.command == "units":
        return await list_revision_unit_attempts(
            db,
            revision_id=_uuid(args.revision_id),
            unit_key=args.unit_key or None,
        )
    if args.command == "inspect-unit":
        return await inspect_unit_attempt(
            db,
            attempt_id=_uuid(args.attempt_id),
            include_private_diagnostics=bool(args.private_diagnostics),
        )
    if args.command == "retry-unit":
        if args.real_provider and not args.confirm_outbound_claude:
            raise ValueError("--real-provider requires --confirm-outbound-claude for sectioned authoring")
        adapter = (
            FixtureSectionedCanonicalAuthoringAdapter(args.fixture_json)
            if args.fixture_json
            else ExistingLLMSectionedCanonicalAuthoringAdapter(allow_outbound=True, max_calls=6)
        )
        return await retry_unit_attempt(
            db,
            revision_id=_uuid(args.revision_id),
            unit_key=args.unit_key,
            adapter=adapter,
            supersede_accepted=bool(args.supersede_accepted),
            artifact_dir=Path(args.artifact_dir) if args.artifact_dir else None,
        )
    if args.command == "assemble":
        return await assemble_sectioned_revision(db, revision_id=_uuid(args.revision_id))
    if args.command == "supersede-unit":
        return await supersede_unit_attempt(db, attempt_id=_uuid(args.attempt_id))
    raise ValueError(f"Unknown command: {args.command}")


def _identity_from_args(args: argparse.Namespace) -> CanonicalLessonIdentityInput:
    return CanonicalLessonIdentityInput(
        grammar_id=args.grammar_id,
        cefr_level=args.cefr_level,
        locale=args.locale,
        methodology_version=args.methodology_version,
    )


def _uuid(raw: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(raw))
    except ValueError as exc:
        raise ValueError("Invalid revision UUID") from exc


def _safe_error(exc: Exception) -> str:
    return str(getattr(exc, "code", "") or exc.__class__.__name__)


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return asyncio.run(run_command(args))


if __name__ == "__main__":
    raise SystemExit(main())
