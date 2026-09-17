"""Tests for curated lesson insights resolution and normalization."""

from types import SimpleNamespace

from app.services.lesson_curated_insights_service import (
    _normalize_concepts,
    _normalize_takeaways,
    apply_teacher_insight_overrides,
    resolve_lesson_insights,
)


def test_normalize_takeaways_truncates_and_dedupes():
    items = _normalize_takeaways(
        [
            "الخلايا هي الوحدة الأساسية للكائنات الحية.",
            "الخلايا هي الوحدة الأساسية للكائنات الحية.",
            "x" * 200,
        ]
    )
    assert len(items) == 2
    assert len(items[1]) <= 120


def test_normalize_concepts_filters_generic_words():
    concepts = _normalize_concepts(["الخلية", "الدرس", "الغشاء الخلوي", "المفاهيم"])
    assert "الخلية" in concepts
    assert "الغشاء الخلوي" in concepts
    assert "الدرس" not in concepts
    assert "المفاهيم" not in concepts


def test_teacher_override_wins_over_cached():
    lesson = SimpleNamespace(
        insights_json={
            "teacher_takeaways": ["فكرة من المعلّم"],
            "teacher_concepts": ["الخلية"],
            "takeaways": ["قديم"],
            "concepts": ["قديم"],
            "source": "gemini",
        }
    )
    result = resolve_lesson_insights(lesson, "نص طويل للدرس عن الخلايا والغشاء والنواة")
    assert result["summary"] == ["فكرة من المعلّم"]
    assert result["keywords"] == ["الخلية"]


def test_apply_teacher_overrides_updates_payload():
    lesson = SimpleNamespace(insights_json=None)
    apply_teacher_insight_overrides(
        lesson,
        takeaways=["أفكار المعلّم"],
        concepts=["النواة"],
    )
    assert lesson.insights_json["teacher_takeaways"] == ["أفكار المعلّم"]
    assert lesson.insights_json["teacher_concepts"] == ["النواة"]
    # Both takeaways and concepts are teacher-provided here (no prior AI insights existed at all,
    # insights_json started as None) — a complete override, which apply_teacher_insight_overrides
    # labels "teacher" (matching the same rule applied consistently elsewhere in this module,
    # e.g. lesson_curated_insights_service.py:171). "mixed" means a *partial* override where the
    # other field still reflects prior/AI content, which isn't the case here.
    assert lesson.insights_json["source"] == "teacher"
