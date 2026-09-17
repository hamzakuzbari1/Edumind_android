"""Read-only access to coherent historical placement assessments.

This module intentionally exposes no attempt lifecycle, scoring, upload, profile,
analytics, or learning-path mutation functions.  AI Language Exam is the only
runtime placement implementation.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.language.assessment import LanguageAssessment
from app.models.language.enums import LanguageSkill
from app.models.language.exam import LanguageExamSession
from app.schemas.language_exam import MultiSkillReportSchema
from app.schemas.language_placement import PlacementHistoryResultOut, PlacementHistorySkillOut


_REQUIRED_SKILLS = frozenset(skill.value for skill in LanguageSkill)


def coherent_legacy_assessment(
    assessment: LanguageAssessment,
) -> PlacementHistoryResultOut | None:
    """Serialize one complete assessment or decline to manufacture a partial result."""
    if not assessment.overall_level or not assessment.completed_at:
        return None

    rows_by_skill: dict[str, object] = {}
    for row in assessment.skill_scores or []:
        skill = row.skill.value if hasattr(row.skill, "value") else str(row.skill)
        if skill in rows_by_skill or not row.level:
            return None
        rows_by_skill[skill] = row
    if set(rows_by_skill) != _REQUIRED_SKILLS:
        return None

    skills = []
    for skill in LanguageSkill:
        row = rows_by_skill[skill.value]
        level = row.level.value if hasattr(row.level, "value") else str(row.level)
        skills.append(
            PlacementHistorySkillOut(
                skill=skill.value,
                score_percent=float(row.score_percent),
                level=level,
            )
        )

    overall = (
        assessment.overall_level.value
        if hasattr(assessment.overall_level, "value")
        else str(assessment.overall_level)
    )
    return PlacementHistoryResultOut(
        record_id=f"legacy:{assessment.id}",
        assessment_id=assessment.id,
        attempt_id=assessment.attempt_id,
        language_id=assessment.language_id,
        source="legacy",
        overall_level=overall,
        overall_calculation_method=assessment.overall_calculation_method,
        completed_at=assessment.completed_at,
        skills=skills,
    )


def coherent_ai_exam_session(
    session: LanguageExamSession,
) -> PlacementHistoryResultOut | None:
    """Serialize one completed AI exam solely from its persisted report and session metadata."""
    if (
        session.status != "completed"
        or session.is_completed is not True
        or not session.completed_at
        or not session.assessment_report
    ):
        return None
    try:
        report = MultiSkillReportSchema.model_validate(session.assessment_report)
    except Exception:
        return None

    skill_values = (
        ("reading", report.reading_score_percent, report.reading_level),
        ("listening", report.listening_score_percent, report.listening_level),
        ("writing", report.writing_score * 10.0, report.writing_level),
        ("speaking", report.speaking_score * 10.0, report.speaking_level),
    )
    version = (session.exam_state or {}).get("version")
    methodology = f"ai_exam_v{version}" if isinstance(version, int) and version > 0 else "ai_exam"
    return PlacementHistoryResultOut(
        record_id=f"ai_exam:{session.id}",
        exam_session_id=session.id,
        language_id=session.language_id,
        source="ai_exam",
        overall_level=report.overall_level.value,
        overall_calculation_method=methodology,
        completed_at=session.completed_at,
        skills=[
            PlacementHistorySkillOut(
                skill=skill,
                score_percent=round(float(score), 2),
                level=level.value,
            )
            for skill, score, level in skill_values
        ],
    )


def _completed_timestamp(value: datetime) -> float:
    aware = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return aware.timestamp()


async def list_placement_history(
    db: AsyncSession,
    *,
    student_id: int,
    limit: int = 20,
) -> list[PlacementHistoryResultOut]:
    """Return this student's coherent legacy and AI-exam snapshots, newest first."""
    bounded_limit = max(1, min(limit, 100))
    legacy_result = await db.execute(
        select(LanguageAssessment)
        .where(LanguageAssessment.student_id == student_id)
        .options(selectinload(LanguageAssessment.skill_scores))
        .order_by(LanguageAssessment.completed_at.desc(), LanguageAssessment.id.desc())
        .limit(100)
    )
    history: list[PlacementHistoryResultOut] = []
    for assessment in legacy_result.scalars().unique().all():
        snapshot = coherent_legacy_assessment(assessment)
        if snapshot is not None:
            history.append(snapshot)

    ai_result = await db.execute(
        select(LanguageExamSession)
        .where(
            LanguageExamSession.student_id == student_id,
            LanguageExamSession.status == "completed",
            LanguageExamSession.is_completed.is_(True),
        )
        .order_by(LanguageExamSession.completed_at.desc(), LanguageExamSession.id.desc())
        .limit(100)
    )
    for session in ai_result.scalars().all():
        snapshot = coherent_ai_exam_session(session)
        if snapshot is not None:
            history.append(snapshot)

    history.sort(key=lambda item: _completed_timestamp(item.completed_at), reverse=True)
    return history[:bounded_limit]
