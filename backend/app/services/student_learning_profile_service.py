"""Centralized student learning memory for lesson chat."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage
from app.models.learning_profile import StudentLearningProfile
from app.models.lesson import Lesson
from app.models.progress import StudentLessonProgress
from app.models.quiz import QuizAttempt, QuizQuestion

MAX_WEAK_TOPICS = 20
MAX_STRONG_TOPICS = 20
MAX_REPEATED_MISTAKES = 15
MAX_LESSON_HISTORY = 30

TopicEntry = dict[str, Any]
MistakeEntry = dict[str, Any]
LessonHistoryEntry = dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_list(raw: str | None) -> list:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _dump_list(items: list) -> str:
    return json.dumps(items, ensure_ascii=False)


def _normalize_topic(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    return cleaned[:120]


def _topic_key(subject: str, label: str) -> str:
    subject_part = _normalize_topic(subject)
    label_part = _normalize_topic(label)
    return f"{subject_part} — {label_part}" if label_part else subject_part


async def get_or_create_learning_profile(
    db: AsyncSession, student_id: int
) -> StudentLearningProfile:
    result = await db.execute(
        select(StudentLearningProfile).where(StudentLearningProfile.user_id == student_id)
    )
    profile = result.scalar_one_or_none()
    if profile:
        return profile
    profile = StudentLearningProfile(user_id=student_id)
    db.add(profile)
    await db.flush()
    return profile


def _upsert_topic(entries: list[TopicEntry], *, topic: str, subject: str, source: str) -> list[TopicEntry]:
    key = _topic_key(subject, topic)
    updated: list[TopicEntry] = []
    found = False
    for item in entries:
        if item.get("key") == key:
            found = True
            updated.append(
                {
                    **item,
                    "count": int(item.get("count") or 0) + 1,
                    "last_seen": _now_iso(),
                    "source": source,
                }
            )
        else:
            updated.append(item)
    if not found:
        updated.append(
            {
                "key": key,
                "topic": _normalize_topic(topic),
                "subject": _normalize_topic(subject),
                "source": source,
                "count": 1,
                "last_seen": _now_iso(),
            }
        )
    updated.sort(key=lambda x: x.get("last_seen") or "", reverse=True)
    return updated[:MAX_WEAK_TOPICS]


def _remove_topic(entries: list[TopicEntry], *, topic: str, subject: str) -> list[TopicEntry]:
    key = _topic_key(subject, topic)
    return [item for item in entries if item.get("key") != key]


def _upsert_mistake(
    entries: list[MistakeEntry],
    *,
    question: str,
    subject: str,
    lesson_id: int,
    hint: str | None = None,
) -> list[MistakeEntry]:
    label = _normalize_topic(question)
    key = _topic_key(subject, label)
    updated: list[MistakeEntry] = []
    found = False
    for item in entries:
        if item.get("key") == key:
            found = True
            updated.append(
                {
                    **item,
                    "wrong_count": int(item.get("wrong_count") or 0) + 1,
                    "last_seen": _now_iso(),
                    "hint": hint or item.get("hint"),
                }
            )
        else:
            updated.append(item)
    if not found:
        updated.append(
            {
                "key": key,
                "question": label,
                "subject": _normalize_topic(subject),
                "lesson_id": lesson_id,
                "wrong_count": 1,
                "last_seen": _now_iso(),
                "hint": hint,
            }
        )
    updated.sort(key=lambda x: (int(x.get("wrong_count") or 0), x.get("last_seen") or ""), reverse=True)
    return updated[:MAX_REPEATED_MISTAKES]


def _upsert_lesson_history(
    entries: list[LessonHistoryEntry],
    *,
    lesson: Lesson,
    quiz_score_percent: float | None = None,
    completed: bool = False,
    interaction: bool = False,
) -> list[LessonHistoryEntry]:
    updated = [item for item in entries if item.get("lesson_id") != lesson.id]
    existing = next((item for item in entries if item.get("lesson_id") == lesson.id), None)
    entry: LessonHistoryEntry = {
        "lesson_id": lesson.id,
        "title": lesson.title,
        "subject": lesson.subject,
        "last_seen": _now_iso(),
        "interaction_count": int((existing or {}).get("interaction_count") or 0),
        "quiz_score_percent": (existing or {}).get("quiz_score_percent"),
        "completed_at": (existing or {}).get("completed_at"),
    }
    if quiz_score_percent is not None:
        entry["quiz_score_percent"] = quiz_score_percent
    if completed:
        entry["completed_at"] = _now_iso()
    if interaction:
        entry["interaction_count"] = int(entry.get("interaction_count") or 0) + 1
    if existing and not interaction:
        entry["interaction_count"] = int(existing.get("interaction_count") or 0)
    updated.insert(0, entry)
    return updated[:MAX_LESSON_HISTORY]


def update_strengths(profile: StudentLearningProfile, *, topic: str, subject: str, source: str) -> None:
    weak = _load_list(profile.weak_topics_json)
    profile.weak_topics_json = _dump_list(_remove_topic(weak, topic=topic, subject=subject))
    strong = _load_list(profile.strong_topics_json)
    profile.strong_topics_json = _dump_list(
        _upsert_topic(strong, topic=topic, subject=subject, source=source)[:MAX_STRONG_TOPICS]
    )


def update_weaknesses(profile: StudentLearningProfile, *, topic: str, subject: str, source: str) -> None:
    strong = _load_list(profile.strong_topics_json)
    profile.strong_topics_json = _dump_list(_remove_topic(strong, topic=topic, subject=subject))
    weak = _load_list(profile.weak_topics_json)
    profile.weak_topics_json = _dump_list(
        _upsert_topic(weak, topic=topic, subject=subject, source=source)[:MAX_WEAK_TOPICS]
    )


def generate_memory_summary(profile: StudentLearningProfile) -> str:
    weak = _load_list(profile.weak_topics_json)
    strong = _load_list(profile.strong_topics_json)
    mistakes = _load_list(profile.repeated_mistakes_json)
    history = _load_list(profile.lesson_history_json)

    weak_labels = [item.get("topic") or item.get("key") for item in weak[:8] if item]
    strong_labels = [item.get("topic") or item.get("key") for item in strong[:8] if item]
    mistake_labels = [
        f"{item.get('question')} (×{item.get('wrong_count', 1)})"
        for item in mistakes[:5]
        if item.get("question")
    ]
    recent_lessons = [
        f"{item.get('title')} ({item.get('subject')})"
        for item in history[:5]
        if item.get("title")
    ]

    parts: list[str] = []
    if weak_labels:
        parts.append("مواضيع ضعيفة: " + "، ".join(weak_labels))
    if strong_labels:
        parts.append("مواضيع قوية: " + "، ".join(strong_labels))
    if mistake_labels:
        parts.append("أخطاء/سوء فهم متكرر: " + "؛ ".join(mistake_labels))
    if recent_lessons:
        parts.append("دروس حديثة: " + "، ".join(recent_lessons))

    summary = "\n".join(parts) if parts else "لا توجد ذاكرة تعليمية محفوظة بعد."
    profile.memory_summary = summary
    return summary


async def aggregate_progress(db: AsyncSession, student_id: int) -> StudentLearningProfile:
    """Rebuild learning memory from quiz results, lesson progress, and chat history."""
    profile = await get_or_create_learning_profile(db, student_id)
    weak: list[TopicEntry] = []
    strong: list[TopicEntry] = []
    mistakes: list[MistakeEntry] = []
    history: list[LessonHistoryEntry] = []

    attempts = await db.execute(
        select(QuizAttempt, Lesson)
        .join(Lesson, Lesson.id == QuizAttempt.lesson_id)
        .where(QuizAttempt.student_id == student_id)
        .order_by(QuizAttempt.created_at.desc())
        .limit(50)
    )
    for attempt, lesson in attempts.all():
        questions_result = await db.execute(
            select(QuizQuestion).where(QuizQuestion.lesson_id == lesson.id).order_by(QuizQuestion.sort_order)
        )
        questions = questions_result.scalars().all()
        total = len(questions) or max(attempt.correct_count, 1)
        score_percent = round((attempt.correct_count / total) * 100) if total else 0
        topic = lesson.subject or lesson.title
        if score_percent < 60:
            weak = _upsert_topic(weak, topic=topic, subject=lesson.subject, source="quiz")
        elif score_percent >= 80:
            strong = _upsert_topic(strong, topic=topic, subject=lesson.subject, source="quiz")

        answers: dict = {}
        try:
            answers = json.loads(attempt.answers_json or "{}")
        except Exception:
            pass
        for q in questions:
            selected = answers.get(str(q.id), answers.get(q.id, -1))
            if int(selected) != q.correct_index:
                mistakes = _upsert_mistake(
                    mistakes,
                    question=q.question,
                    subject=lesson.subject,
                    lesson_id=lesson.id,
                    hint=q.hint,
                )

        history = _upsert_lesson_history(
            history, lesson=lesson, quiz_score_percent=float(score_percent)
        )

    progress_rows = await db.execute(
        select(StudentLessonProgress, Lesson)
        .join(Lesson, Lesson.id == StudentLessonProgress.lesson_id)
        .where(StudentLessonProgress.student_id == student_id)
        .order_by(StudentLessonProgress.updated_at.desc())
        .limit(MAX_LESSON_HISTORY)
    )
    for prog, lesson in progress_rows.all():
        history = _upsert_lesson_history(
            history,
            lesson=lesson,
            quiz_score_percent=float(prog.quiz_score_percent or 0) or None,
            completed=prog.completed_at is not None,
        )
        if prog.quiz_submitted and (prog.quiz_score_percent or 0) < 60:
            weak = _upsert_topic(
                weak, topic=lesson.subject or lesson.title, subject=lesson.subject, source="lesson"
            )
        elif prog.completed_at and (prog.quiz_score_percent or 0) >= 80:
            strong = _upsert_topic(
                strong, topic=lesson.subject or lesson.title, subject=lesson.subject, source="lesson"
            )

    chat_rows = await db.execute(
        select(ChatMessage, Lesson)
        .join(Lesson, Lesson.id == ChatMessage.lesson_id)
        .where(ChatMessage.student_id == student_id, ChatMessage.role == "student")
        .order_by(ChatMessage.created_at.desc())
        .limit(40)
    )
    seen_questions: dict[str, int] = {}
    for msg, lesson in chat_rows.all():
        history = _upsert_lesson_history(history, lesson=lesson, interaction=True)
        qtext = _normalize_topic(msg.content)
        if len(qtext) < 8:
            continue
        key = _topic_key(lesson.subject, qtext)
        seen_questions[key] = seen_questions.get(key, 0) + 1
        if seen_questions[key] >= 2:
            mistakes = _upsert_mistake(
                mistakes,
                question=qtext,
                subject=lesson.subject,
                lesson_id=lesson.id,
                hint="سؤال متكرر في المحادثة",
            )
            weak = _upsert_topic(
                weak, topic=lesson.subject or qtext[:40], subject=lesson.subject, source="chat"
            )

    profile.weak_topics_json = _dump_list(weak[:MAX_WEAK_TOPICS])
    profile.strong_topics_json = _dump_list(strong[:MAX_STRONG_TOPICS])
    profile.repeated_mistakes_json = _dump_list(mistakes[:MAX_REPEATED_MISTAKES])
    profile.lesson_history_json = _dump_list(history[:MAX_LESSON_HISTORY])
    generate_memory_summary(profile)
    await db.flush()
    return profile


async def record_quiz_result(
    db: AsyncSession,
    student_id: int,
    lesson: Lesson,
    questions: list[QuizQuestion],
    answers: dict,
    score_percent: int,
) -> StudentLearningProfile:
    profile = await get_or_create_learning_profile(db, student_id)
    topic = lesson.subject or lesson.title
    if score_percent < 60:
        update_weaknesses(profile, topic=topic, subject=lesson.subject, source="quiz")
    elif score_percent >= 80:
        update_strengths(profile, topic=topic, subject=lesson.subject, source="quiz")

    for q in questions:
        selected = answers.get(str(q.id), answers.get(q.id, -1))
        if int(selected) != q.correct_index:
            mistakes = _load_list(profile.repeated_mistakes_json)
            profile.repeated_mistakes_json = _dump_list(
                _upsert_mistake(
                    mistakes,
                    question=q.question,
                    subject=lesson.subject,
                    lesson_id=lesson.id,
                    hint=q.hint,
                )
            )

    history = _load_list(profile.lesson_history_json)
    profile.lesson_history_json = _dump_list(
        _upsert_lesson_history(history, lesson=lesson, quiz_score_percent=float(score_percent))
    )
    generate_memory_summary(profile)
    await db.flush()
    return profile


async def record_lesson_completion(db: AsyncSession, student_id: int, lesson_id: int) -> None:
    lesson = await db.get(Lesson, lesson_id)
    if not lesson:
        return
    profile = await get_or_create_learning_profile(db, student_id)
    history = _load_list(profile.lesson_history_json)
    profile.lesson_history_json = _dump_list(
        _upsert_lesson_history(history, lesson=lesson, completed=True)
    )
    prog_result = await db.execute(
        select(StudentLessonProgress).where(
            StudentLessonProgress.student_id == student_id,
            StudentLessonProgress.lesson_id == lesson_id,
        )
    )
    prog = prog_result.scalar_one_or_none()
    if prog and (prog.quiz_score_percent or 0) >= 80:
        update_strengths(
            profile,
            topic=lesson.subject or lesson.title,
            subject=lesson.subject,
            source="lesson",
        )
    generate_memory_summary(profile)
    await db.flush()


async def record_chat_interaction(
    db: AsyncSession,
    student_id: int,
    lesson: Lesson,
    question_text: str,
) -> None:
    profile = await get_or_create_learning_profile(db, student_id)
    history = _load_list(profile.lesson_history_json)
    profile.lesson_history_json = _dump_list(
        _upsert_lesson_history(history, lesson=lesson, interaction=True)
    )

    qtext = _normalize_topic(question_text)
    if len(qtext) >= 8:
        prior = await db.execute(
            select(ChatMessage)
            .where(
                ChatMessage.student_id == student_id,
                ChatMessage.lesson_id == lesson.id,
                ChatMessage.role == "student",
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(10)
        )
        matches = sum(
            1
            for msg in prior.scalars().all()
            if _normalize_topic(msg.content)[:40] == qtext[:40]
        )
        if matches >= 2:
            mistakes = _load_list(profile.repeated_mistakes_json)
            profile.repeated_mistakes_json = _dump_list(
                _upsert_mistake(
                    mistakes,
                    question=qtext,
                    subject=lesson.subject,
                    lesson_id=lesson.id,
                    hint="سؤال متكرر في المحادثة",
                )
            )
            update_weaknesses(
                profile,
                topic=lesson.subject or qtext[:40],
                subject=lesson.subject,
                source="chat",
            )

    generate_memory_summary(profile)
    await db.flush()


def topic_labels(entries: list) -> list[str]:
    labels: list[str] = []
    for item in entries:
        label = item.get("topic") or item.get("key")
        if label and label not in labels:
            labels.append(str(label))
    return labels


def mistake_labels(entries: list) -> list[str]:
    out: list[str] = []
    for item in entries:
        q = item.get("question")
        if q:
            out.append(str(q))
    return out


def recent_lesson_labels(entries: list) -> list[str]:
    out: list[str] = []
    for item in entries:
        title = item.get("title")
        subject = item.get("subject")
        if title:
            out.append(f"{title} ({subject})" if subject else str(title))
    return out


async def get_learning_context_for_chat(
    db: AsyncSession,
    student_id: int,
    *,
    lesson: Lesson | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    if refresh:
        profile = await aggregate_progress(db, student_id)
    else:
        profile = await get_or_create_learning_profile(db, student_id)
        if not profile.memory_summary:
            profile = await aggregate_progress(db, student_id)

    weak = _load_list(profile.weak_topics_json)
    strong = _load_list(profile.strong_topics_json)
    mistakes = _load_list(profile.repeated_mistakes_json)
    history = _load_list(profile.lesson_history_json)

    summary = profile.memory_summary or generate_memory_summary(profile)
    return {
        "learning_memory_summary": summary,
        "weak_topics": topic_labels(weak),
        "strong_topics": topic_labels(strong),
        "repeated_mistakes": mistake_labels(mistakes),
        "recent_lessons": recent_lesson_labels(history),
    }


def learning_chat_kwargs(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "learning_memory_summary": context.get("learning_memory_summary"),
        "weak_topics": context.get("weak_topics") or [],
        "strong_topics": context.get("strong_topics") or [],
        "repeated_mistakes": context.get("repeated_mistakes") or [],
        "recent_lessons": context.get("recent_lessons") or [],
    }
