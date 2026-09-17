"""Revision version comparison (W7) — structured improved/unchanged/regressed."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.services.language_writing_evaluator.evaluation_facts_types import WritingEvaluationFacts

COMPARISON_VERSION = "7.0.0"


class ComparisonChange(StrEnum):
    improved = "improved"
    unchanged = "unchanged"
    regressed = "regressed"


@dataclass(frozen=True, slots=True)
class DimensionComparison:
    dimension: str
    change: ComparisonChange
    before_score: float
    after_score: float


@dataclass(frozen=True, slots=True)
class RevisionComparisonResult:
    """Structured comparison between two evaluation fact snapshots."""

    from_revision: int
    to_revision: int
    dimensions: tuple[DimensionComparison, ...]
    improved: tuple[str, ...]
    unchanged: tuple[str, ...]
    regressed: tuple[str, ...]
    improvement_summary: str
    remaining_issues: tuple[str, ...]
    comparison_version: str = COMPARISON_VERSION

    def to_persistence_dict(self) -> dict[str, object]:
        return {
            "from_revision": self.from_revision,
            "to_revision": self.to_revision,
            "dimensions": [
                {
                    "dimension": d.dimension,
                    "change": d.change.value,
                    "before_score": round(d.before_score, 4),
                    "after_score": round(d.after_score, 4),
                }
                for d in self.dimensions
            ],
            "improved": list(self.improved),
            "unchanged": list(self.unchanged),
            "regressed": list(self.regressed),
            "improvement_summary": self.improvement_summary,
            "remaining_issues": list(self.remaining_issues),
            "comparison_version": self.comparison_version,
        }


def _change(before: float, after: float, *, threshold: float = 0.05) -> ComparisonChange:
    if after - before >= threshold:
        return ComparisonChange.improved
    if before - after >= threshold:
        return ComparisonChange.regressed
    return ComparisonChange.unchanged


def compare_evaluation_facts(
    before: WritingEvaluationFacts,
    after: WritingEvaluationFacts,
) -> RevisionComparisonResult:
    """Compare two evaluation snapshots — no free-form-only output."""
    pairs = (
        ("grammar", before.grammar_result, after.grammar_result),
        ("vocabulary", before.vocabulary_result, after.vocabulary_result),
        ("organization", before.organization_result, after.organization_result),
        ("task_completion", before.task_completion_result, after.task_completion_result),
        ("goal_alignment", before.goal_alignment_result, after.goal_alignment_result),
    )
    dimensions: list[DimensionComparison] = []
    improved: list[str] = []
    unchanged: list[str] = []
    regressed: list[str] = []

    for name, b, a in pairs:
        change = _change(b.score, a.score)
        dimensions.append(
            DimensionComparison(
                dimension=name,
                change=change,
                before_score=b.score,
                after_score=a.score,
            )
        )
        if change == ComparisonChange.improved:
            improved.append(name)
        elif change == ComparisonChange.regressed:
            regressed.append(name)
        else:
            unchanged.append(name)

    for weakness in before.weaknesses:
        if weakness not in after.weaknesses and weakness.replace("_", " ") not in " ".join(after.strengths):
            improved.append(f"issue:{weakness}")

    summary_parts = []
    if improved:
        summary_parts.append(f"Improved: {', '.join(improved[:4])}")
    if regressed:
        summary_parts.append(f"Regressed: {', '.join(regressed[:4])}")
    if not summary_parts:
        summary_parts.append("Overall performance is stable this revision.")

    return RevisionComparisonResult(
        from_revision=before.revision_number,
        to_revision=after.revision_number,
        dimensions=tuple(dimensions),
        improved=tuple(dict.fromkeys(improved)),
        unchanged=tuple(unchanged),
        regressed=tuple(regressed),
        improvement_summary="; ".join(summary_parts),
        remaining_issues=after.weaknesses,
    )
