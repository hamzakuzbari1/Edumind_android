"""SaaS-style chart rendering for parent PDF reports."""

from __future__ import annotations

import io
from typing import Any

import numpy as np

from app.services.parent_report_pdf_arabic import ar
from app.services.parent_report_pdf_theme import (
    ACCENT,
    BG,
    BORDER,
    DANGER,
    GRID,
    INFO,
    PRIMARY,
    SECONDARY,
    SUCCESS,
    SURFACE,
    TEXT,
    TEXT_MUTED,
    WARNING,
)

DONUT_COLORS = [PRIMARY, SECONDARY, SUCCESS, WARNING, ACCENT]
HEAT_COLORS = ["#F1F5F9", "#DDD6FE", "#A78BFA", "#7C6CF0", "#5B21B6"]


def _setup_style() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "figure.facecolor": BG,
            "axes.facecolor": SURFACE,
            "axes.edgecolor": "none",
            "axes.labelcolor": TEXT_MUTED,
            "text.color": TEXT,
            "xtick.color": TEXT_MUTED,
            "ytick.color": TEXT_MUTED,
            "grid.color": GRID,
            "font.size": 9,
            "font.family": "sans-serif",
            "font.sans-serif": ["Tahoma", "Segoe UI", "Arial", "DejaVu Sans"],
        }
    )


def _to_png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
    import matplotlib.pyplot as plt

    plt.close(fig)
    return buf.getvalue()


def _smooth_xy(values: list[float]) -> tuple[np.ndarray, np.ndarray]:
    x = np.arange(len(values), dtype=float)
    y = np.array(values, dtype=float)
    if len(values) < 3:
        return x, y
    x_dense = np.linspace(0, len(values) - 1, num=max(len(values) * 8, 24))
    try:
        from scipy.interpolate import make_interp_spline

        spline = make_interp_spline(x, y, k=min(3, len(values) - 1))
        y_dense = spline(x_dense)
        y_dense = np.clip(y_dense, 0, None)
        return x_dense, y_dense
    except Exception:
        return x, y


def _style_ax(ax, *, title: str, ylabel: str) -> None:
    ax.set_title(ar(title), fontsize=10, fontweight="bold", color=TEXT, pad=12, loc="right")
    ax.set_ylabel(ar(ylabel), fontsize=8, color=TEXT_MUTED)
    ax.grid(axis="y", linestyle="--", alpha=0.45, linewidth=0.6)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.spines["bottom"].set_color(GRID)
    ax.set_facecolor(SURFACE)


def line_chart(
    points: list[dict],
    *,
    title: str,
    ylabel: str,
    color: str = PRIMARY,
) -> bytes:
    _setup_style()
    import matplotlib.pyplot as plt

    labels = [str(p.get("label", "")) for p in (points or [])]
    values = [float(p.get("value") or 0) for p in (points or [])]
    fig, ax = plt.subplots(figsize=(4.4, 2.7))
    fig.patch.set_facecolor(BG)

    if not labels:
        ax.text(0.5, 0.5, ar("لا توجد بيانات"), ha="center", va="center", fontsize=10, color=TEXT_MUTED)
        ax.set_axis_off()
    else:
        x_smooth, y_smooth = _smooth_xy(values)
        ax.fill_between(x_smooth, y_smooth, alpha=0.18, color=color)
        ax.plot(x_smooth, y_smooth, color=color, linewidth=2.8, solid_capstyle="round")
        ax.scatter(range(len(values)), values, color=color, s=28, zorder=4, edgecolors="white", linewidths=1.2)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=7)
        _style_ax(ax, title=title, ylabel=ylabel)

    return _to_png(fig)


def donut_chart(breakdown: dict[str, float], *, title: str) -> bytes:
    _setup_style()
    import matplotlib.pyplot as plt

    labels_ar = {
        "lessons": "الدروس",
        "quizzes": "الاختبارات",
        "ai_chat": "المحادثة الذكية",
        "video": "الفيديو",
        "other": "أخرى",
    }
    keys = ["lessons", "quizzes", "ai_chat", "video", "other"]
    values = [float(breakdown.get(k) or 0) for k in keys]
    labels = [ar(labels_ar[k]) for k in keys]
    fig, ax = plt.subplots(figsize=(4.4, 2.9))
    fig.patch.set_facecolor(BG)
    total = sum(values)
    if total <= 0:
        ax.text(0.5, 0.5, ar("لا توجد بيانات"), ha="center", va="center", fontsize=10, color=TEXT_MUTED)
        ax.set_axis_off()
    else:
        wedges, _, autotexts = ax.pie(
            values,
            colors=DONUT_COLORS,
            autopct=lambda p: f"{p:.0f}%" if p >= 6 else "",
            startangle=90,
            pctdistance=0.78,
            wedgeprops={"width": 0.44, "edgecolor": "white", "linewidth": 2},
        )
        for t in autotexts:
            t.set_fontsize(7)
            t.set_color("white")
            t.set_fontweight("bold")
        ax.legend(
            wedges,
            [f"{l} ({v:.0f} د)" for l, v in zip(labels, values)],
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            fontsize=7,
            frameon=False,
        )
        ax.set_title(ar(title), fontsize=10, fontweight="bold", color=TEXT, pad=10, loc="right")
    return _to_png(fig)


def heatmap_chart(cells: list[dict], *, title: str) -> bytes:
    _setup_style()
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap

    fig, ax = plt.subplots(figsize=(8.6, 2.4))
    fig.patch.set_facecolor(BG)
    if not cells:
        ax.text(0.5, 0.5, ar("لا توجد بيانات"), ha="center", va="center", fontsize=10, color=TEXT_MUTED)
        ax.set_axis_off()
    else:
        weeks: list[list[int]] = []
        week_labels: list[str] = []
        chunk: list[int] = []
        for cell in cells:
            chunk.append(int(cell.get("level") or 0))
            if len(chunk) == 7:
                weeks.append(chunk)
                week_labels.append(cell["date"][5:])
                chunk = []
        if chunk:
            while len(chunk) < 7:
                chunk.append(0)
            weeks.append(chunk)
            week_labels.append(cells[-1]["date"][5:])
        data = np.array(weeks).T if weeks else np.zeros((7, 1))
        cmap = ListedColormap(HEAT_COLORS)
        ax.imshow(data, aspect="auto", cmap=cmap, vmin=0, vmax=4)
        ax.set_yticks(range(7))
        ax.set_yticklabels([ar(d) for d in ["أ", "إ", "ث", "أ", "خ", "ج", "س"]], fontsize=8)
        ax.set_xticks(range(len(week_labels)))
        ax.set_xticklabels(week_labels, fontsize=7)
    ax.set_title(ar(title), fontsize=10, fontweight="bold", color=TEXT, pad=10, loc="right")
    return _to_png(fig)


def progress_bars_chart(courses: list[dict], *, title: str) -> bytes:
    _setup_style()
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8.6, max(2.6, len(courses) * 0.52 + 0.9)))
    fig.patch.set_facecolor(BG)
    if not courses:
        ax.text(0.5, 0.5, ar("لا توجد دورات"), ha="center", va="center", fontsize=10, color=TEXT_MUTED)
        ax.set_axis_off()
    else:
        titles = [ar((c.get("title") or "")[:26]) for c in courses]
        values = [float(c.get("completion") or 0) for c in courses]
        colors = [SUCCESS if v >= 80 else WARNING if v >= 50 else DANGER for v in values]
        y = list(range(len(titles)))
        ax.barh(y, values, color=colors, height=0.52, zorder=2, alpha=0.92)
        ax.set_yticks(y)
        ax.set_yticklabels(titles, fontsize=8)
        ax.set_xlim(0, 100)
        ax.set_xlabel(ar("نسبة الإكمال %"), fontsize=8)
        ax.invert_yaxis()
        for i, v in enumerate(values):
            ax.text(min(v + 2, 90), i, f"{v:.0f}%", va="center", fontsize=7, color=TEXT)
        ax.grid(axis="x", linestyle="--", alpha=0.4)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    ax.set_title(ar(title), fontsize=10, fontweight="bold", color=TEXT, pad=10, loc="right")
    return _to_png(fig)


def render_all_charts(report: dict[str, Any]) -> dict[str, bytes]:
    analytics = report.get("pdf_analytics") or {}
    lesson = report.get("lesson_history") or {}
    planner = report.get("planner_history") or {}

    return {
        "study_hours": line_chart(analytics.get("weekly_study_hours") or [], title="ساعات الدراسة — 8 أسابيع", ylabel="ساعات", color=PRIMARY),
        "grades": line_chart(analytics.get("weekly_grades") or [], title="تطور الدرجات — 8 أسابيع", ylabel="متوسط %", color=SECONDARY),
        "lessons": line_chart(lesson.get("weekly") or [], title="إكمال الدروس — 8 أسابيع", ylabel="دروس", color=SUCCESS),
        "planner": line_chart(planner.get("adherence_trend") or [], title="الالتزام بالخطة — 8 أسابيع", ylabel="%", color=INFO),
        "activity_donut": donut_chart(analytics.get("activity_breakdown") or {}, title="توزيع وقت التعلم"),
        "attendance_heatmap": heatmap_chart(analytics.get("attendance_heatmap") or [], title="خريطة النشاط اليومي"),
        "course_progress": progress_bars_chart(analytics.get("course_progress") or [], title="تقدم الدورات المسجّلة"),
    }
