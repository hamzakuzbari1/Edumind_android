"""Probe historical-report for first parent with a linked student."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.parent_link import ParentStudentLink
from app.services.parent_historical_reports_service import build_parent_historical_report

OUT = Path(__file__).resolve().parent / "_probe_historical_report_db.out.json"


async def main() -> None:
    result: dict = {}
    async with AsyncSessionLocal() as db:
        row = await db.execute(select(ParentStudentLink).limit(1))
        link = row.scalar_one_or_none()
        if not link:
            result["error"] = "no_parent_student_links"
            OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
            return
        sid = link.student_id
        result["student_id"] = sid
        result["parent_id"] = link.parent_id
        try:
            report = await build_parent_historical_report(db, sid, period="this_week")
            result["ok"] = True
            result["has_data"] = report.get("has_data")
            result["has_pdf_analytics"] = bool(report.get("pdf_analytics"))
            result["keys"] = sorted(report.keys())
        except Exception as exc:
            import traceback

            result["ok"] = False
            result["error"] = f"{type(exc).__name__}: {exc}"
            result["traceback"] = traceback.format_exc()
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
