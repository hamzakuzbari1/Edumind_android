"""Premium 5-page parent analytics PDF — Pillow Arabic cards + embedded charts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import fitz

from app.services.parent_report_pdf_arabic import (
    render_alert_cards,
    render_bullet_card,
    render_comparison_table,
    render_executive_grid,
    render_header_banner,
    render_kpi_strip,
    render_narrative_block,
    render_timeline_card,
    render_weekly_analysis,
)
from app.services.parent_report_pdf_charts import render_all_charts
from app.services.parent_report_pdf_theme import BG, TEXT_MUTED


def _hex_fitz(color: str) -> tuple[float, float, float]:
    c = color.lstrip("#")
    return int(c[0:2], 16) / 255, int(c[2:4], 16) / 255, int(c[4:6], 16) / 255


PAGE_W, PAGE_H = 595, 842
MARGIN = 24
CONTENT_W = PAGE_W - 2 * MARGIN
PX = int(CONTENT_W * 2.2)  # ~2x for crisp PNG embed


def _insert_png(page: fitz.Page, rect: fitz.Rect, png: bytes) -> None:
    page.insert_image(rect, stream=png, keep_proportion=False)


def _footer(page: fitz.Page, n: int, total: int) -> None:
    bg = _hex_fitz(BG)
    muted = _hex_fitz(TEXT_MUTED)
    page.draw_rect(fitz.Rect(MARGIN, PAGE_H - 22, PAGE_W - MARGIN, PAGE_H - 14), color=bg, fill=bg)
    page.insert_text(
        (PAGE_W / 2 - 40, PAGE_H - 16),
        f"EduSpark  |  {n}/{total}",
        fontsize=7,
        color=muted,
    )


def build_dashboard_pdf(report: dict[str, Any]) -> bytes:
    analytics = report.get("pdf_analytics") or {}
    charts = render_all_charts(report)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total_pages = 5

    doc = fitz.open()

    # ── Page 1: Executive Summary ──
    p1 = doc.new_page(width=PAGE_W, height=PAGE_H)
    y = MARGIN
    banner = render_header_banner(
        width_px=PX,
        student_name=report.get("student_name", ""),
        grade=report.get("grade_label", ""),
        period=report.get("period_label", ""),
        date_range=f"{report.get('start_date', '')} → {report.get('end_date', '')}",
        generated=generated,
    )
    bh = 110 * (CONTENT_W / PX)
    _insert_png(p1, fitz.Rect(MARGIN, y, PAGE_W - MARGIN, y + bh), banner)
    y += bh + 8

    narrative = render_narrative_block(
        width_px=PX,
        title="الملخص السردي",
        body=analytics.get("narrative_summary") or "",
    )
    nh = 95
    _insert_png(p1, fitz.Rect(MARGIN, y, PAGE_W - MARGIN, y + nh), narrative)
    y += nh + 6

    exec_png = render_executive_grid(width_px=PX, blocks=analytics.get("executive_summary") or {})
    eh = 200
    _insert_png(p1, fitz.Rect(MARGIN, y, PAGE_W - MARGIN, y + eh), exec_png)
    y += eh + 6

    kpi_png = render_kpi_strip(width_px=PX, kpis=analytics.get("kpi_strip") or [])
    _insert_png(p1, fitz.Rect(MARGIN, y, PAGE_W - MARGIN, y + 72), kpi_png)
    y += 78

    alerts = render_alert_cards(
        width_px=PX,
        risks=analytics.get("risk_indicators") or [],
        achievements=analytics.get("achievements") or [],
    )
    _insert_png(p1, fitz.Rect(MARGIN, y, PAGE_W - MARGIN, min(y + 185, PAGE_H - 28)), alerts)
    _footer(p1, 1, total_pages)

    # ── Page 2: Comparison Dashboard ──
    p2 = doc.new_page(width=PAGE_W, height=PAGE_H)
    y = MARGIN
    cmp_png = render_comparison_table(width_px=PX, rows=analytics.get("comparison_rows") or [])
    ch = 150
    _insert_png(p2, fitz.Rect(MARGIN, y, PAGE_W - MARGIN, y + ch), cmp_png)
    y += ch + 8

    insights_png = render_bullet_card(
        width_px=PX,
        title="رؤى لولي الأمر",
        items=analytics.get("parent_insights") or [],
    )
    _insert_png(p2, fitz.Rect(MARGIN, y, PAGE_W - MARGIN, y + 100), insights_png)
    y += 106

    col_w = (CONTENT_W - 8) / 2
    ch_h = 175
    _insert_png(p2, fitz.Rect(MARGIN, y, MARGIN + col_w, y + ch_h), charts["study_hours"])
    _insert_png(p2, fitz.Rect(MARGIN + col_w + 8, y, PAGE_W - MARGIN, y + ch_h), charts["grades"])
    _footer(p2, 2, total_pages)

    # ── Page 3: Weekly Performance ──
    p3 = doc.new_page(width=PAGE_W, height=PAGE_H)
    y = MARGIN
    weekly_png = render_weekly_analysis(width_px=PX, weeks=analytics.get("weekly_performance") or [])
    wh = min(340, PAGE_H - 2 * MARGIN - 90)
    _insert_png(p3, fitz.Rect(MARGIN, y, PAGE_W - MARGIN, y + wh), weekly_png)
    y += wh + 6

    timeline_png = render_timeline_card(width_px=PX, timeline=analytics.get("performance_timeline") or {})
    _insert_png(p3, fitz.Rect(MARGIN, y, PAGE_W - MARGIN, y + 68), timeline_png)
    y += 74
    _insert_png(p3, fitz.Rect(MARGIN, y, MARGIN + col_w, y + ch_h), charts["lessons"])
    _insert_png(p3, fitz.Rect(MARGIN + col_w + 8, y, PAGE_W - MARGIN, y + ch_h), charts["planner"])
    _footer(p3, 3, total_pages)

    # ── Page 4: Learning Analytics ──
    p4 = doc.new_page(width=PAGE_W, height=PAGE_H)
    y = MARGIN
    _insert_png(p4, fitz.Rect(MARGIN, y, MARGIN + col_w + 10, y + 195), charts["activity_donut"])
    _insert_png(p4, fitz.Rect(MARGIN, y + 200, PAGE_W - MARGIN, PAGE_H - 36), charts["course_progress"])
    _footer(p4, 4, total_pages)

    # ── Page 5: Attendance & Activity ──
    p5 = doc.new_page(width=PAGE_W, height=PAGE_H)
    y = MARGIN
    _insert_png(p5, fitz.Rect(MARGIN, y, PAGE_W - MARGIN, y + 155), charts["attendance_heatmap"])
    y += 161
    att = report.get("attendance_history") or {}
    summary_items = [
        f"إجمالي الجلسات: {att.get('total_sessions', 0)}",
        f"ساعات الدراسة: {att.get('total_study_hours', 0)}",
        f"معدل الحضور: {analytics.get('attendance_rate', 0):.0f}%",
    ]
    sum_png = render_bullet_card(width_px=PX, title="ملخص الحضور", items=summary_items)
    _insert_png(p5, fitz.Rect(MARGIN, y, PAGE_W - MARGIN, y + 85), sum_png)
    _footer(p5, 5, total_pages)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes
