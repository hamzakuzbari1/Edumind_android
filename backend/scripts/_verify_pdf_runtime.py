"""Runtime verification: prove which PDF builder executes (same code path as API)."""
from __future__ import annotations

import asyncio
import json
import logging
import sys
import traceback
from pathlib import Path

logging.basicConfig(level=logging.WARNING)
OUT = Path(__file__).resolve().parent / "_verify_pdf_runtime.out.json"


def analyze_pdf(data: bytes) -> dict:
    import fitz

    doc = fitz.open(stream=data, filetype="pdf")
    text = doc[0].get_text() if doc.page_count else ""
    info = {
        "page_count": doc.page_count,
        "bytes": len(data),
        "page1_has_old_marker": "مقارنة الفترات" in text and "جلسات الدخول" in text and "صفحة 1 من 3" not in text,
        "page1_has_new_marker": "تقرير EduSpark التحليلي" in text or "ملخص تنفيذي" in text,
        "page1_text_preview": text[:500],
    }
    doc.close()
    return info


async def run_export(student_id: int) -> dict:
    from app.db.session import AsyncSessionLocal
    from app.services.parent_historical_reports_service import build_parent_historical_report
    from app.services.parent_report_export_service import export_report_pdf

    result: dict = {
        "python": sys.executable,
        "export_report_pdf_file": export_report_pdf.__code__.co_filename,
    }

    try:
        import matplotlib

        result["matplotlib"] = matplotlib.__version__
    except Exception as exc:
        result["matplotlib_error"] = f"{type(exc).__name__}: {exc}"

    try:
        from app.services.parent_report_pdf_builder import build_dashboard_pdf

        result["build_dashboard_pdf_file"] = build_dashboard_pdf.__code__.co_filename
    except Exception as exc:
        result["builder_import_error"] = f"{type(exc).__name__}: {exc}"

    async with AsyncSessionLocal() as db:
        report = await build_parent_historical_report(db, student_id, period="this_month")
        result["has_pdf_analytics"] = bool(report.get("pdf_analytics"))
        try:
            pdf = export_report_pdf(report)
            pdf_path = Path(__file__).resolve().parent / "_verify_pdf_runtime.pdf"
            pdf_path.write_bytes(pdf)
            result["export_ok"] = True
            result["pdf_path"] = str(pdf_path)
            result.update(analyze_pdf(pdf))
        except Exception as exc:
            result["export_ok"] = False
            result["export_error"] = f"{type(exc).__name__}: {exc}"
            result["traceback"] = traceback.format_exc()
    return result


def main() -> None:
    # student 75 had engagement data in prior tests
    report = asyncio.run(run_export(75))
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
