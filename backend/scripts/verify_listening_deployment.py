"""Verify listening deployment schema before release.

Usage (from backend/):
    python scripts/verify_listening_deployment.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.listening_deployment import (
    LISTENING_HEAD_MIGRATION,
    REQUIRED_INDEXES,
    REQUIRED_TABLES,
    inspect_listening_deployment,
)
from app.db.session import AsyncSessionLocal


def _print_section(title: str) -> None:
    print(f"\n--- {title} ---")


async def main() -> int:
    report: dict = {
        "ok": False,
        "tables": {},
        "indexes": {},
        "alembic": {},
        "listening": {},
    }

    async with AsyncSessionLocal() as db:
        status = await inspect_listening_deployment(db)

    report["listening"] = status.to_dict()
    report["alembic"] = {
        "current_revision": status.current_alembic_revision,
        "latest_revision": status.latest_alembic_revision,
        "at_head": status.current_alembic_revision == status.latest_alembic_revision,
        "listening_head": LISTENING_HEAD_MIGRATION,
    }

    _print_section("Alembic revision")
    print(f"  current:  {status.current_alembic_revision or '(none)'}")
    print(f"  latest:   {status.latest_alembic_revision or '(unknown)'}")
    print(f"  at_head:  {report['alembic']['at_head']}")

    _print_section("Required tables (progression + reservation + promotion storage)")
    for table, migration in REQUIRED_TABLES.items():
        present = table not in status.missing_tables
        report["tables"][table] = {"present": present, "migration": migration}
        mark = "OK" if present else "MISSING"
        print(f"  [{mark}] {table} ({migration})")

    _print_section("Required indexes")
    for index_name, migration in REQUIRED_INDEXES.items():
        present = index_name not in status.missing_indexes
        report["indexes"][index_name] = {"present": present, "migration": migration}
        mark = "OK" if present else "MISSING"
        print(f"  [{mark}] {index_name} ({migration})")

    _print_section("Listening readiness flags")
    print(f"  listening_progression_ready:  {status.listening_progression_ready}")
    print(f"  reservation_table_present:    {status.reservation_table_present}")
    print(f"  deployment_ready:             {status.deployment_ready}")

    report["ok"] = status.deployment_ready

    print("\n--- JSON summary ---")
    print(json.dumps(report, indent=2))

    if status.deployment_ready:
        print("\nListening deployment verification: PASS")
        return 0

    print("\nListening deployment verification: FAIL")
    if status.missing_tables:
        print(f"  Run: alembic upgrade head  (missing tables → {status.missing_tables[0]})")
    elif status.missing_indexes:
        print(f"  Re-run migration or restore indexes: {list(status.missing_indexes)}")
    elif not report["alembic"]["at_head"]:
        print(f"  Run: alembic upgrade head  (current={status.current_alembic_revision})")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
