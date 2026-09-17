"""Arabic RTL text shaping and Pillow-based rendering for PDF cards."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Sequence

from app.services.parent_report_pdf_theme import (
    ACCENT,
    BG,
    BORDER,
    DANGER,
    HEADER_GRADIENT,
    PRIMARY,
    SUCCESS,
    SURFACE,
    TEXT,
    TEXT_MUTED,
    WARNING,
)

_FONT_CACHE: dict[int, object] = {}


def ar(text: str) -> str:
    """Shape Arabic for correct RTL display."""
    if not text:
        return ""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display

        return get_display(arabic_reshaper.reshape(str(text)))
    except Exception:
        return str(text)


def _font(size: int, *, bold: bool = False):
    if key := (size, bold):
        if key in _FONT_CACHE:
            return _FONT_CACHE[key]
    from PIL import ImageFont

    candidates = [
        Path(r"C:\Windows\Fonts\tahomabd.ttf" if bold else r"C:\Windows\Fonts\tahoma.ttf"),
        Path(r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf"),
        Path(r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"),
    ]
    for path in candidates:
        if path.is_file():
            font = ImageFont.truetype(str(path), size)
            _FONT_CACHE[key] = font
            return font
    font = ImageFont.load_default()
    _FONT_CACHE[key] = font
    return font


def _hex_rgb(color: str) -> tuple[int, int, int]:
    c = color.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _rounded_rect(draw, xy, radius: int, fill: str, outline: str | None = None):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline or fill, width=1)


def _gradient_header(draw, width: int, height: int):
    from PIL import Image

    c0 = _hex_rgb(HEADER_GRADIENT[0])
    c1 = _hex_rgb(HEADER_GRADIENT[1])
    for x in range(width):
        t = x / max(width - 1, 1)
        r = int(c0[0] + (c1[0] - c0[0]) * t)
        g = int(c0[1] + (c1[1] - c0[1]) * t)
        b = int(c0[2] + (c1[2] - c0[2]) * t)
        draw.line([(x, 0), (x, height)], fill=(r, g, b))


def _wrap_lines(text: str, font, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if font.getlength(trial) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _draw_rtl_text(
    draw,
    text: str,
    *,
    x_right: int,
    y: int,
    font,
    fill: str,
    max_width: int | None = None,
) -> int:
    """Draw shaped Arabic right-aligned; returns height used."""
    shaped = ar(text)
    if max_width:
        lines = _wrap_lines(shaped, font, max_width)
    else:
        lines = [shaped]
    line_h = font.size + 4
    for i, line in enumerate(lines):
        w = font.getlength(line)
        draw.text((x_right - w, y + i * line_h), line, font=font, fill=fill)
    return len(lines) * line_h


def render_png(width_px: int, height_px: int, draw_fn) -> bytes:
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (width_px, height_px), BG)
    draw = ImageDraw.Draw(img)
    draw_fn(draw, img)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def render_header_banner(
    *,
    width_px: int,
    student_name: str,
    grade: str,
    period: str,
    date_range: str,
    generated: str,
) -> bytes:
    h = 110

    def _draw(draw, img):
        from PIL import ImageDraw

        _gradient_header(draw, width_px, h)
        pad = 20
        _draw_rtl_text(
            draw,
            "تقرير EduSpark التحليلي",
            x_right=width_px - pad,
            y=16,
            font=_font(22, bold=True),
            fill="#FFFFFF",
        )
        sub = f"{student_name}  |  {grade}  |  {period}  ({date_range})"
        _draw_rtl_text(
            draw,
            sub,
            x_right=width_px - pad,
            y=52,
            font=_font(11),
            fill="#E8ECF4",
            max_width=width_px - 2 * pad,
        )
        _draw_rtl_text(
            draw,
            f"توليد: {generated}",
            x_right=width_px - pad,
            y=78,
            font=_font(9),
            fill="#CBD5E1",
        )

    return render_png(width_px, h, _draw)


def render_narrative_block(*, width_px: int, title: str, body: str) -> bytes:
    pad = 16
    line_w = width_px - 2 * pad

    def _draw(draw, img):
        y = pad
        _draw_rtl_text(draw, title, x_right=width_px - pad, y=y, font=_font(13, bold=True), fill=PRIMARY)
        y += 28
        y += _draw_rtl_text(
            draw, body, x_right=width_px - pad, y=y, font=_font(11), fill=TEXT, max_width=line_w
        )
        y += pad

    est_h = 80 + len(body) // 3
    return render_png(width_px, max(est_h, 100), _draw)


def render_executive_grid(*, width_px: int, blocks: dict[str, list[str]]) -> bytes:
    pad = 14
    labels = {
        "status": "كيف حال الطالب؟",
        "improved": "ما الذي تحسّن؟",
        "declined": "ما الذي تراجع؟",
        "attention": "ما الذي يحتاج انتباهاً؟",
        "focus": "تركيز الأسبوع القادم",
    }
    colors = {
        "status": PRIMARY,
        "improved": SUCCESS,
        "declined": DANGER,
        "attention": WARNING,
        "focus": ACCENT,
    }
    col_w = (width_px - pad * 3) // 2
    row_h = 88
    h = pad * 3 + row_h * 3

    def _draw(draw, img):
        keys = ["status", "improved", "declined", "attention", "focus"]
        positions = [(0, 0), (1, 0), (0, 1), (1, 1), (0, 2)]
        for key, (col, row) in zip(keys, positions):
            span = 2 if key == "focus" else 1
            cw = col_w if span == 1 else width_px - 2 * pad
            x0 = pad + col * (col_w + pad) if span == 1 else pad
            y0 = pad + row * (row_h + pad)
            x1 = x0 + cw
            y1 = y0 + row_h
            _rounded_rect(draw, (x0, y0, x1, y1), 12, SURFACE, BORDER)
            _draw_rtl_text(
                draw,
                labels[key],
                x_right=x1 - 10,
                y=y0 + 8,
                font=_font(10, bold=True),
                fill=colors[key],
            )
            items = blocks.get(key) or ["—"]
            if key == "status":
                text = str(blocks.get("status") or "—")
            elif isinstance(items, list):
                text = " • ".join(items[:3])
            else:
                text = str(items)
            _draw_rtl_text(
                draw,
                text,
                x_right=x1 - 10,
                y=y0 + 28,
                font=_font(9),
                fill=TEXT,
                max_width=cw - 16,
            )

    return render_png(width_px, h, _draw)


def render_kpi_strip(*, width_px: int, kpis: Sequence[dict]) -> bytes:
    pad = 12
    n = len(kpis)
    card_w = (width_px - pad * (n + 1)) // max(n, 1)
    h = 78

    def _draw(draw, img):
        for i, kpi in enumerate(kpis):
            x0 = pad + i * (card_w + pad)
            x1 = x0 + card_w
            _rounded_rect(draw, (x0, 8, x1, h - 8), 10, SURFACE, BORDER)
            trend = kpi.get("trend") or ""
            trend_color = kpi.get("trend_color") or TEXT_MUTED
            _draw_rtl_text(
                draw,
                kpi.get("label", ""),
                x_right=x1 - 8,
                y=14,
                font=_font(8),
                fill=TEXT_MUTED,
            )
            _draw_rtl_text(
                draw,
                str(kpi.get("value", "—")),
                x_right=x1 - 8,
                y=32,
                font=_font(16, bold=True),
                fill=TEXT,
            )
            if trend:
                _draw_rtl_text(
                    draw,
                    trend,
                    x_right=x1 - 8,
                    y=56,
                    font=_font(8, bold=True),
                    fill=trend_color,
                )

    return render_png(width_px, h, _draw)


def render_bullet_card(*, width_px: int, title: str, items: Sequence[str], accent: str = PRIMARY) -> bytes:
    pad = 14
    line_h = 18
    h = pad * 2 + 24 + max(len(items), 1) * line_h

    def _draw(draw, img):
        _rounded_rect(draw, (8, 8, width_px - 8, h - 8), 12, SURFACE, BORDER)
        _draw_rtl_text(draw, title, x_right=width_px - pad, y=pad, font=_font(12, bold=True), fill=accent)
        y = pad + 26
        for item in items:
            _draw_rtl_text(
                draw,
                f"• {item}",
                x_right=width_px - pad,
                y=y,
                font=_font(10),
                fill=TEXT,
                max_width=width_px - 2 * pad,
            )
            y += line_h

    return render_png(width_px, h, _draw)


def render_weekly_analysis(*, width_px: int, weeks: Sequence[dict]) -> bytes:
    pad = 12
    row_h = 52
    h = pad * 2 + len(weeks) * (row_h + 8)

    def _draw(draw, img):
        _draw_rtl_text(
            draw,
            "تحليل الأداء الأسبوعي",
            x_right=width_px - pad,
            y=pad,
            font=_font(13, bold=True),
            fill=PRIMARY,
        )
        y = pad + 28
        for wk in weeks:
            x0, x1 = 8, width_px - 8
            y1 = y + row_h
            _rounded_rect(draw, (x0, y, x1, y1), 10, SURFACE, BORDER)
            label = wk.get("label", "")
            _draw_rtl_text(draw, label, x_right=x1 - 10, y=y + 6, font=_font(10, bold=True), fill=TEXT)
            lines = wk.get("lines") or []
            ty = y + 22
            for line in lines[:3]:
                color = SUCCESS if line.startswith("↑") else DANGER if line.startswith("↓") else TEXT_MUTED
                _draw_rtl_text(draw, line, x_right=x1 - 10, y=ty, font=_font(9), fill=color, max_width=x1 - x0 - 20)
                ty += 14
            y = y1 + 8

    return render_png(width_px, max(h, 80), _draw)


def render_timeline_card(*, width_px: int, timeline: dict) -> bytes:
    h = 72

    def _draw(draw, img):
        _rounded_rect(draw, (8, 8, width_px - 8, h - 8), 12, SURFACE, BORDER)
        parts = [
            f"أفضل أسبوع: {timeline.get('best_week', '—')}",
            f"أضعف أسبوع: {timeline.get('worst_week', '—')}",
            f"أكثر أسبوع تحسّناً: {timeline.get('most_improved_week', '—')}",
        ]
        x = width_px - 16
        y = 16
        for p in parts:
            _draw_rtl_text(draw, p, x_right=x, y=y, font=_font(10), fill=TEXT)
            y += 18

    return render_png(width_px, h, _draw)


def render_alert_cards(*, width_px: int, risks: Sequence[dict], achievements: Sequence[dict]) -> bytes:
    pad = 12
    h = 200

    def _draw(draw, img):
        half = (width_px - pad * 3) // 2
        _draw_rtl_text(draw, "مؤشرات الخطر", x_right=width_px - pad - half - pad, y=8, font=_font(11, bold=True), fill=DANGER)
        _draw_rtl_text(draw, "إنجازات", x_right=width_px - pad, y=8, font=_font(11, bold=True), fill=SUCCESS)
        y0 = 30
        for i, risk in enumerate(risks[:3]):
            _rounded_rect(draw, (pad, y0 + i * 52, pad + half, y0 + i * 52 + 44), 8, "#FEF2F2", "#FECACA")
            _draw_rtl_text(
                draw,
                risk.get("title", ""),
                x_right=pad + half - 8,
                y=y0 + i * 52 + 8,
                font=_font(9, bold=True),
                fill=DANGER,
            )
            _draw_rtl_text(
                draw,
                risk.get("message", ""),
                x_right=pad + half - 8,
                y=y0 + i * 52 + 24,
                font=_font(8),
                fill=TEXT,
                max_width=half - 16,
            )
        rx = pad * 2 + half
        for i, ach in enumerate(achievements[:3]):
            _rounded_rect(draw, (rx, y0 + i * 52, rx + half, y0 + i * 52 + 44), 8, "#ECFDF5", "#A7F3D0")
            _draw_rtl_text(
                draw,
                ach.get("title", ""),
                x_right=rx + half - 8,
                y=y0 + i * 52 + 8,
                font=_font(9, bold=True),
                fill=SUCCESS,
            )
            _draw_rtl_text(
                draw,
                ach.get("value", ""),
                x_right=rx + half - 8,
                y=y0 + i * 52 + 24,
                font=_font(8),
                fill=TEXT,
                max_width=half - 16,
            )

    return render_png(width_px, h, _draw)


def render_comparison_table(*, width_px: int, rows: Sequence[dict]) -> bytes:
    pad = 12
    row_h = 28
    h = pad * 2 + 24 + len(rows) * row_h

    def _draw(draw, img):
        _draw_rtl_text(
            draw,
            "لوحة المقارنة",
            x_right=width_px - pad,
            y=pad,
            font=_font(13, bold=True),
            fill=PRIMARY,
        )
        y = pad + 26
        headers = ["المؤشر", "الحالي", "السابق", "التغيير"]
        col_w = (width_px - 24) // 4
        for j, htxt in enumerate(headers):
            x_right = width_px - 12 - j * col_w
            _draw_rtl_text(draw, htxt, x_right=x_right, y=y, font=_font(9, bold=True), fill=TEXT_MUTED)
        y += row_h
        for row in rows:
            vals = [row.get("label", ""), row.get("current", ""), row.get("previous", ""), row.get("change", "")]
            for j, val in enumerate(vals):
                color = TEXT
                if j == 3:
                    if str(val).startswith("▲"):
                        color = SUCCESS
                    elif str(val).startswith("▼"):
                        color = DANGER
                x_right = width_px - 12 - j * col_w
                _draw_rtl_text(draw, str(val), x_right=x_right, y=y, font=_font(9), fill=color)
            y += row_h

    return render_png(width_px, h, _draw)
