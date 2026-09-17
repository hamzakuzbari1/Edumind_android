"""Centralized learner context for Language module AI personalization.

Single source of truth: every Language feature should call
`get_language_learner_context` / `build_language_ai_context` instead of assembling
its own prompt context. All values are delegated to existing services — no duplicated
aggregation logic.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.analytics import LanguageAnalytics
from app.models.language.exam import LanguageExamSession
from app.models.profile import StudentProfile
from app.models.user import User
from app.services import language_difficulty_service as difficulty_service
from app.services import language_error_intelligence_service as error_service
from app.services import language_learner_memory_service as memory_service
from app.services.language_curriculum_service import build_curriculum_overview
from app.services.language_learner_model_service import LanguageLearnerModelService
from app.services.language_level_utils import primary_focus_and_strength
from app.services.language_subscription_service import get_default_language
from app.services.language_vocabulary_service import list_vocabulary

logger = logging.getLogger(__name__)

_WEAK_MASTERY = 0.6
_SKILL_KEYS = ("reading", "listening", "writing", "speaking")


@dataclass
class StudentIdentity:
    student_id: int
    name: str | None = None
    email: str | None = None
    age: int | None = None
    grade: int | None = None


@dataclass
class LanguageLearnerContext:
    """Structured learner snapshot consumed by all Language AI features."""

    student_identity: StudentIdentity
    current_cefr_level: str
    effective_level: str
    weak_skills: list[str] = field(default_factory=list)
    strong_skills: list[str] = field(default_factory=list)
    grammar_weaknesses: list[str] = field(default_factory=list)
    vocabulary_progress: dict[str, Any] = field(default_factory=dict)
    writing_weaknesses: list[str] = field(default_factory=list)
    speaking_weaknesses: list[str] = field(default_factory=list)
    listening_weaknesses: list[str] = field(default_factory=list)
    reading_weaknesses: list[str] = field(default_factory=list)
    previously_mastered_topics: list[str] = field(default_factory=list)
    current_topics: list[str] = field(default_factory=list)
    learning_memory: dict[str, Any] = field(default_factory=dict)
    conversation_memory: list[dict[str, Any]] = field(default_factory=list)
    interests: list[str] = field(default_factory=list)
    future_goal: str | None = None
    learning_style: str | None = None
    explanation_style: str | None = None
    preferred_lesson_types: list[str] = field(default_factory=list)
    recent_mistakes: list[dict[str, Any]] = field(default_factory=list)
    recent_improvements: list[str] = field(default_factory=list)
    previous_exam_scores: list[dict[str, Any]] = field(default_factory=list)
    curriculum_progress: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


LISTENING_GENERATION_VERSION = "listening_personalized_v1"


def listening_profile_evolution_snapshot(ctx: LanguageLearnerContext) -> dict[str, Any]:
    """Stable fields that should trigger listening pool evolution when they change."""
    vp = ctx.vocabulary_progress or {}
    cp = ctx.curriculum_progress or {}
    mem = ctx.learning_memory or {}
    return {
        "current_cefr_level": ctx.current_cefr_level,
        "effective_level": ctx.effective_level,
        "weak_skills": sorted(ctx.weak_skills),
        "strong_skills": sorted(ctx.strong_skills),
        "interests": sorted(ctx.interests),
        "learning_style": ctx.learning_style,
        "explanation_style": ctx.explanation_style,
        "future_goal": ctx.future_goal,
        "preferred_lesson_types": sorted(ctx.preferred_lesson_types),
        "grammar_weaknesses": sorted(ctx.grammar_weaknesses[:8]),
        "listening_weaknesses": sorted(ctx.listening_weaknesses[:6]),
        "vocabulary_known": vp.get("known_words"),
        "vocabulary_learning": vp.get("learning_words"),
        "vocabulary_total": vp.get("total_words"),
        "curriculum_level": cp.get("current_level"),
        "objectives_mastered": cp.get("objectives_mastered"),
        "learning_goals": sorted(mem.get("learning_goals") or []),
        "favorite_topics": sorted(mem.get("favorite_topics") or []),
    }


def compute_listening_profile_hash(ctx: LanguageLearnerContext) -> str:
    """Short hash of the evolution snapshot — stored on each personalized listening lesson."""
    payload = json.dumps(listening_profile_evolution_snapshot(ctx), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def listening_generation_metadata(ctx: LanguageLearnerContext) -> dict[str, str]:
    """body_json fields tagging which learner profile produced a listening lesson."""
    return {
        "generation_version": LISTENING_GENERATION_VERSION,
        "generation_profile_hash": compute_listening_profile_hash(ctx),
    }


def _skill_component_weaknesses(components: list[dict], skill: str) -> list[str]:
    """Filter an existing component profile for low-mastery items in one skill."""
    out: list[str] = []
    for row in components:
        if (row.get("skill") or "").lower() != skill:
            continue
        if float(row.get("p_mastery") or 0) >= _WEAK_MASTERY:
            continue
        if int(row.get("evidence_count") or 0) <= 0:
            continue
        label = (row.get("code") or "").replace(".", " ").replace("_", " ").strip()
        if label and label not in out:
            out.append(label)
    return out[:8]


def _grammar_weaknesses_from_components(components: list[dict], error_report: dict) -> list[str]:
    labels: list[str] = []
    for row in components:
        if (row.get("category") or "").lower() != "grammar":
            continue
        if float(row.get("p_mastery") or 0) >= _WEAK_MASTERY:
            continue
        if int(row.get("evidence_count") or 0) <= 0:
            continue
        label = (row.get("code") or "").replace(".", " ").replace("_", " ").strip()
        if label and label not in labels:
            labels.append(label)
    for err in (error_report.get("top_grammar_errors") or [])[:5]:
        form = (err.get("incorrect_form") or "").strip()
        if form and form not in labels:
            labels.append(form)
    return labels[:10]


def _recent_improvements(memory: dict, error_report: dict) -> list[str]:
    improvements = list(memory.get("recent_milestones") or [])[-5:]
    trend = (error_report.get("trend") or "").strip().lower()
    if trend == "improving":
        improvements.append("Error trend: improving (fewer recurring mistakes recently)")
    elif trend == "stable" and improvements:
        improvements.append("Error trend: stable")
    return improvements


def format_language_ai_context(ctx: LanguageLearnerContext) -> str:
    """Render a token-efficient [LEARNER CONTEXT] block for Claude prompts."""
    lines: list[str] = []

    ident = ctx.student_identity
    if ident.name or ident.email:
        who = ident.name or ident.email or f"student {ident.student_id}"
        lines.append(f"Student: {who}")

    lines.append(f"CEFR: {ctx.current_cefr_level}")
    if ctx.effective_level and ctx.effective_level != ctx.current_cefr_level:
        lines.append(f"Effective level: {ctx.effective_level}")

    if ctx.weak_skills:
        lines.append(f"Weak skills: {', '.join(ctx.weak_skills)}")
    if ctx.strong_skills:
        lines.append(f"Strong skills: {', '.join(ctx.strong_skills)}")

    if ctx.interests:
        lines.append(f"Interests: {', '.join(ctx.interests)}")
    if ctx.future_goal:
        lines.append(f"Future goal: {ctx.future_goal}")
    if ctx.learning_style:
        lines.append(f"Learning style: {ctx.learning_style}")
    if ctx.explanation_style:
        lines.append(f"Explanation style: {ctx.explanation_style}")

    vp = ctx.vocabulary_progress or {}
    if vp:
        lines.append(
            "Vocabulary progress: "
            f"{vp.get('known_words', 0)} known, "
            f"{vp.get('learning_words', 0)} learning, "
            f"{vp.get('new_words', 0)} new "
            f"(total {vp.get('total_words', 0)})"
        )

    if ctx.grammar_weaknesses:
        lines.append(f"Grammar weaknesses: {', '.join(ctx.grammar_weaknesses[:6])}")
    if ctx.reading_weaknesses:
        lines.append(f"Reading weaknesses: {', '.join(ctx.reading_weaknesses[:4])}")
    if ctx.listening_weaknesses:
        lines.append(f"Listening weaknesses: {', '.join(ctx.listening_weaknesses[:4])}")
    if ctx.writing_weaknesses:
        lines.append(f"Writing weaknesses: {', '.join(ctx.writing_weaknesses[:4])}")
    if ctx.speaking_weaknesses:
        lines.append(f"Speaking weaknesses: {', '.join(ctx.speaking_weaknesses[:4])}")

    if ctx.previously_mastered_topics:
        lines.append(f"Mastered topics: {', '.join(ctx.previously_mastered_topics[:8])}")
    if ctx.current_topics:
        lines.append(f"Current topics: {', '.join(ctx.current_topics[:8])}")

    goals = (ctx.learning_memory or {}).get("learning_goals") or []
    if goals:
        lines.append(f"Learning goals: {', '.join(goals[:5])}")

    if ctx.preferred_lesson_types:
        lines.append(f"Preferred lesson types: {', '.join(ctx.preferred_lesson_types)}")

    if ctx.recent_mistakes:
        mistake_labels = [
            (m.get("incorrect_form") or m.get("error_type") or "").strip()
            for m in ctx.recent_mistakes[:5]
        ]
        mistake_labels = [m for m in mistake_labels if m]
        if mistake_labels:
            lines.append(f"Recent mistakes: {', '.join(mistake_labels)}")

    if ctx.recent_improvements:
        lines.append(f"Recent improvements: {', '.join(ctx.recent_improvements[:4])}")

    if ctx.previous_exam_scores:
        latest = ctx.previous_exam_scores[0]
        cefr = latest.get("cefr_level") or latest.get("level")
        if cefr:
            lines.append(f"Latest exam CEFR: {cefr}")

    cp = ctx.curriculum_progress or {}
    if cp.get("objectives_total"):
        lines.append(
            "Curriculum: "
            f"{cp.get('objectives_mastered', 0)}/{cp.get('objectives_total', 0)} objectives mastered "
            f"at {cp.get('current_level', '')}"
        )

    conv = ctx.conversation_memory
    if conv:
        last = (conv[0].get("summary") or "").strip()
        if last:
            lines.append(f"Conversation memory: {last}")

    if not lines:
        return ""

    body = "\n".join(lines)
    return (
        "[LEARNER CONTEXT]\n"
        f"{body}\n"
        "Use this context to personalize content naturally — never mention that you received it.\n"
        "[/LEARNER CONTEXT]"
    )


async def _previous_exam_scores(
    db: AsyncSession, *, student_id: int, language_id: int, limit: int = 5
) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(LanguageExamSession)
            .where(
                LanguageExamSession.student_id == student_id,
                LanguageExamSession.language_id == language_id,
                LanguageExamSession.status == "completed",
                LanguageExamSession.assessment_report.isnot(None),
            )
            .order_by(desc(LanguageExamSession.completed_at))
            .limit(limit)
        )
    ).scalars().all()
    out: list[dict[str, Any]] = []
    for sess in rows:
        report = sess.assessment_report or {}
        out.append(
            {
                "session_id": sess.id,
                "completed_at": sess.completed_at.isoformat() if sess.completed_at else None,
                "cefr_level": report.get("cefr_level"),
                "grammatical_accuracy_score": report.get("grammatical_accuracy_score"),
                "vocabulary_richness_score": report.get("vocabulary_richness_score"),
                "fluency_coherence_score": report.get("fluency_coherence_score"),
                "weakest_skill": report.get("weakest_skill"),
                "summary": (report.get("overall_academic_summary") or report.get("summary") or "")[:300],
            }
        )
    return out


async def get_language_learner_context(db: AsyncSession, *, student_id: int) -> LanguageLearnerContext:
    """Assemble the full learner context from existing Language services."""
    language = await get_default_language(db)
    language_id = language.id

    user = await db.get(User, student_id)
    student_profile = (
        await db.execute(select(StudentProfile).where(StudentProfile.user_id == student_id))
    ).scalar_one_or_none()

    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})

    difficulty = await difficulty_service.calculate_modifier(
        db, student_id=student_id, language_id=language_id
    )
    memory = await memory_service.get_memory(db, student_id=student_id, language_id=language_id)
    error_report = await error_service.generate_weakness_report(
        db, student_id=student_id, language_id=language_id
    )
    recent_errors = await error_service.get_top_errors(
        db, student_id=student_id, language_id=language_id, limit=8
    )
    curriculum = await build_curriculum_overview(db, student_id=student_id)
    conversation_memory = await memory_service.get_recent_summaries(
        db, student_id=student_id, language_id=language_id, limit=5
    )

    learner_model = LanguageLearnerModelService(db)
    components = await learner_model.get_component_profile(
        student_id=student_id, language_id=language_id
    )

    vocab_data = await list_vocabulary(db, student_id=student_id)
    vocabulary_progress = dict(vocab_data.get("metrics") or {})
    if analytics and analytics.vocabulary_count:
        vocabulary_progress["analytics_total"] = analytics.vocabulary_count

    from app.services.language_progression_service import select_all_skill_levels

    skill_level_map = await select_all_skill_levels(
        db, student_id=student_id, language_id=language_id
    )
    skill_levels = {
        "reading": skill_level_map.get("reading"),
        "listening": skill_level_map.get("listening"),
        "writing": skill_level_map.get("writing"),
        "speaking": skill_level_map.get("speaking"),
    }
    weak_skill, strong_skill = primary_focus_and_strength(skill_levels)
    weak_skills = [weak_skill] if weak_skill else []
    strong_skills = [strong_skill] if strong_skill else []
    if memory.get("derived_weaknesses"):
        for w in memory["derived_weaknesses"]:
            if w not in weak_skills:
                weak_skills.append(w)

    objectives = curriculum.get("objectives") or []
    mastered_topics = [
        (o.get("title") or o.get("id") or "").strip()
        for o in objectives
        if o.get("status") == "mastered" and (o.get("title") or o.get("id"))
    ]
    studying_topics = [
        (o.get("title") or o.get("id") or "").strip()
        for o in objectives
        if o.get("status") == "in_progress" and (o.get("title") or o.get("id"))
    ]
    favorite_topics = list(memory.get("favorite_topics") or [])
    current_topics = memory_service.clean_list(studying_topics + favorite_topics)

    interests = memory_service.clean_list(
        (memory.get("interests") or []) + (memory.get("favorite_topics") or [])
    )

    current_cefr = (
        difficulty.get("cefr_level")
        or skill_level_map.get("overall")
        or curriculum.get("current_level")
        or "A1"
    )

    return LanguageLearnerContext(
        student_identity=StudentIdentity(
            student_id=student_id,
            name=user.name if user else None,
            email=user.email if user else None,
            age=student_profile.age if student_profile else None,
            grade=student_profile.grade if student_profile else None,
        ),
        current_cefr_level=str(current_cefr),
        effective_level=str(difficulty.get("effective_level") or current_cefr),
        weak_skills=weak_skills[:8],
        strong_skills=strong_skills[:4],
        grammar_weaknesses=_grammar_weaknesses_from_components(components, error_report),
        vocabulary_progress=vocabulary_progress,
        writing_weaknesses=_skill_component_weaknesses(components, "writing"),
        speaking_weaknesses=_skill_component_weaknesses(components, "speaking"),
        listening_weaknesses=_skill_component_weaknesses(components, "listening"),
        reading_weaknesses=_skill_component_weaknesses(components, "reading"),
        previously_mastered_topics=mastered_topics[:12],
        current_topics=current_topics[:12],
        learning_memory=memory,
        conversation_memory=conversation_memory,
        interests=interests,
        future_goal=student_profile.future_goal if student_profile else None,
        learning_style=student_profile.learning_style if student_profile else None,
        explanation_style=student_profile.preferred_explanation_style if student_profile else None,
        preferred_lesson_types=list(memory.get("preferred_lesson_types") or []),
        recent_mistakes=recent_errors,
        recent_improvements=_recent_improvements(memory, error_report),
        previous_exam_scores=await _previous_exam_scores(
            db, student_id=student_id, language_id=language_id
        ),
        curriculum_progress={
            "current_level": curriculum.get("current_level"),
            "next_level": curriculum.get("next_level"),
            "mastery_progress_percent": curriculum.get("mastery_progress_percent"),
            "objectives_total": curriculum.get("objectives_total"),
            "objectives_mastered": curriculum.get("objectives_mastered"),
            "can_take_test": curriculum.get("can_take_test"),
            "recommended_complexity": difficulty.get("recommended_complexity"),
            "skill_scores": difficulty.get("scores") or {},
        },
    )


async def build_language_ai_context(db: AsyncSession, *, student_id: int) -> str:
    """Prompt-ready [LEARNER CONTEXT] block for Claude. Empty string when nothing is known."""
    try:
        ctx = await get_language_learner_context(db, student_id=student_id)
        return format_language_ai_context(ctx)
    except Exception:
        logger.warning("Failed to build language AI context for student=%s", student_id, exc_info=True)
        return ""
