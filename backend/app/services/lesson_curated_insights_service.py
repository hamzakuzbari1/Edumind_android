"""AI-curated lesson takeaways and key concepts with teacher override and caching."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.catalog import TeacherProfile
from app.models.lesson import Lesson
from app.services.lesson_insights import build_lesson_insights

logger = logging.getLogger(__name__)
settings = get_settings()

MAX_TAKEAWAYS = 5
MIN_TAKEAWAYS = 3
MAX_CONCEPTS = 5
MIN_CONCEPTS = 3
MAX_TAKEAWAY_CHARS = 120
LESSON_TEXT_SAMPLE_CHARS = 9000

GENERIC_CONCEPTS = {
    "الدرس",
    "المادة",
    "الفصل",
    "الوحدة",
    "المحتوى",
    "المعلومات",
    "الموضوع",
    "العنوان",
    "الصفحة",
    "الطالب",
    "المعلم",
    "التعليم",
    "الشرح",
    "النص",
    "الفكرة",
    "الأفكار",
    "المفهوم",
    "المفاهيم",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_string_list(values: list | None, *, max_items: int, max_chars: int | None = None) -> list[str]:
    if not values:
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in values:
        text = re.sub(r"\s+", " ", str(raw or "").strip())
        if not text:
            continue
        if max_chars and len(text) > max_chars:
            text = text[: max_chars - 1].rstrip() + "…"
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
        if len(cleaned) >= max_items:
            break
    return cleaned


def _normalize_takeaways(values: list | None) -> list[str]:
    return _clean_string_list(values, max_items=MAX_TAKEAWAYS, max_chars=MAX_TAKEAWAY_CHARS)


def _normalize_concepts(values: list | None) -> list[str]:
    items = _clean_string_list(values, max_items=MAX_CONCEPTS)
    return [item for item in items if item.casefold() not in GENERIC_CONCEPTS and len(item) >= 2]


def _insights_payload(lesson: Lesson) -> dict:
    raw = lesson.insights_json
    return dict(raw) if isinstance(raw, dict) else {}


def _teacher_takeaways(payload: dict) -> list[str]:
    return _normalize_takeaways(payload.get("teacher_takeaways"))


def _teacher_concepts(payload: dict) -> list[str]:
    return _normalize_concepts(payload.get("teacher_concepts"))


def _cached_takeaways(payload: dict) -> list[str]:
    return _normalize_takeaways(payload.get("takeaways"))


def _cached_concepts(payload: dict) -> list[str]:
    return _normalize_concepts(payload.get("concepts"))


def resolve_lesson_insights(lesson: Lesson, fallback_text: str) -> dict[str, list[str]]:
    """Resolve display insights: teacher override → cached → extractive fallback."""
    payload = _insights_payload(lesson)
    teacher_takeaways = _teacher_takeaways(payload)
    teacher_concepts = _teacher_concepts(payload)
    cached_takeaways = _cached_takeaways(payload)
    cached_concepts = _cached_concepts(payload)

    takeaways = teacher_takeaways or cached_takeaways
    concepts = teacher_concepts or cached_concepts

    extracted = build_lesson_insights(
        fallback_text or "",
        max_bullets=MAX_TAKEAWAYS,
        max_keywords=MAX_CONCEPTS,
    )

    if not takeaways:
        takeaways = _normalize_takeaways(extracted.get("summary"))
    if not concepts:
        concepts = _normalize_concepts(extracted.get("keywords"))

    return {
        "summary": takeaways[:MAX_TAKEAWAYS],
        "keywords": concepts[:MAX_CONCEPTS],
    }


def apply_teacher_insight_overrides(
    lesson: Lesson,
    *,
    takeaways: list[str] | None = None,
    concepts: list[str] | None = None,
) -> None:
    payload = _insights_payload(lesson)

    if takeaways is not None:
        normalized = _normalize_takeaways(takeaways)
        payload["teacher_takeaways"] = normalized or None
        if normalized:
            payload["takeaways"] = normalized

    if concepts is not None:
        normalized = _normalize_concepts(concepts)
        payload["teacher_concepts"] = normalized or None
        if normalized:
            payload["concepts"] = normalized

    teacher_takeaways = _teacher_takeaways(payload)
    teacher_concepts = _teacher_concepts(payload)
    if teacher_takeaways and teacher_concepts:
        payload["source"] = "teacher"
    elif teacher_takeaways or teacher_concepts:
        payload["source"] = "mixed"
    payload["updated_at"] = _utc_now_iso()
    lesson.insights_json = payload or None


def clear_cached_insights_preserve_teacher(lesson: Lesson) -> None:
    payload = _insights_payload(lesson)
    teacher_takeaways = payload.get("teacher_takeaways")
    teacher_concepts = payload.get("teacher_concepts")
    if teacher_takeaways or teacher_concepts:
        lesson.insights_json = {
            "teacher_takeaways": teacher_takeaways,
            "teacher_concepts": teacher_concepts,
            "source": "teacher" if teacher_takeaways and teacher_concepts else "mixed",
            "updated_at": _utc_now_iso(),
        }
    else:
        lesson.insights_json = None


def _teacher_persona_lines(teacher_profile: TeacherProfile | None, lesson: Lesson) -> dict[str, str]:
    if not teacher_profile:
        return {
            "teacher_name": lesson.teacher.name if lesson.teacher else "المعلّم",
            "teaching_style": "واضح ومباشر",
            "tone": "ودود ومشجّع",
            "question_style": "يفتح بأسئلة بسيطة",
            "signature": "",
        }
    return {
        "teacher_name": (
            teacher_profile.teacher_display_name
            or teacher_profile.full_name
            or (lesson.teacher.name if lesson.teacher else "المعلّم")
        ),
        "teaching_style": teacher_profile.teacher_teaching_style or "واضح ومباشر",
        "tone": teacher_profile.teacher_tone or "ودود ومشجّع",
        "question_style": teacher_profile.teacher_question_style or "يفتح بأسئلة بسيطة",
        "signature": (teacher_profile.teacher_signature_phrase or "").strip(),
    }


def _build_curated_prompt(lesson: Lesson, lesson_text: str, teacher_profile: TeacherProfile | None) -> tuple[str, str]:
    persona = _teacher_persona_lines(teacher_profile, lesson)
    sample = (lesson_text or "")[:LESSON_TEXT_SAMPLE_CHARS]
    signature_line = (
        f'\nعبارة المعلّم المميزة: "{persona["signature"]}"'
        if persona["signature"]
        else ""
    )
    system = (
        "أنت معلّم عربي ممتاز تلخّص الدرس للطالب بأسلوب إنساني واضح. "
        "لا تنسخ نص الدرس حرفياً ولا تُخرج فقرات OCR طويلة. "
        "اكتب كما لو أنك تهمس للطالب: ماذا يجب أن يتذكر غداً؟"
    )
    prompt = f"""المادة: {lesson.subject}
الصف: {lesson.grade}
عنوان الدرس: {lesson.title}
المعلّم: {persona["teacher_name"]}
أسلوب الشرح: {persona["teaching_style"]}
نبرة المعلّم: {persona["tone"]}
أسلوب الأسئلة: {persona["question_style"]}{signature_line}

نص الدرس (للاستيعاب فقط — لا تنسخه):
---
{sample}
---

أعد JSON فقط بهذا الشكل:
{{"takeaways":["..."],"concepts":["..."]}}

قواعد takeaways:
- من {MIN_TAKEAWAYS} إلى {MAX_TAKEAWAYS} عناصر
- جملة واحدة لكل عنصر
- {MAX_TAKEAWAY_CHARS} حرفاً كحد أقصى
- ما يجب أن يتذكره الطالب غداً
- ليس فقرة طويلة ولا نسخاً من النص

قواعد concepts:
- من {MIN_CONCEPTS} إلى {MAX_CONCEPTS} مفاهيم
- أهم ما قد يُسأل عنه في الاختبار
- ليس أسماء عشوائية ولا كلمات عامة ولا عناوين فصول
- مفردات أو عبارات قصيرة دقيقة من الدرس
"""
    return system, prompt


async def _generate_claude_insights(
    lesson: Lesson,
    lesson_text: str,
    teacher_profile: TeacherProfile | None,
) -> dict[str, list[str]] | None:
    from app.services.claude_service import is_claude_configured
    from app.services.ai_service import generate_llm_json

    if not is_claude_configured():
        return None
    system, prompt = _build_curated_prompt(lesson, lesson_text, teacher_profile)
    try:
        raw = await generate_llm_json(
            prompt,
            system=system,
            temperature=0.35,
            max_output_tokens=1024,
        )
        if not raw:
            return None
        data = json.loads(raw)
        takeaways = _normalize_takeaways(data.get("takeaways"))
        concepts = _normalize_concepts(data.get("concepts"))
        if len(takeaways) < 1 and len(concepts) < 1:
            return None
        return {"takeaways": takeaways, "concepts": concepts}
    except Exception as exc:
        logger.warning("Claude curated insights failed for lesson %s: %s", lesson.id, exc)
        return None


async def curate_and_cache_lesson_insights(
    db: AsyncSession,
    lesson: Lesson,
    lesson_text: str,
    teacher_profile: TeacherProfile | None = None,
) -> None:
    """Generate/cache curated insights once during lesson processing."""
    payload = _insights_payload(lesson)
    teacher_takeaways = _teacher_takeaways(payload)
    teacher_concepts = _teacher_concepts(payload)

    takeaways = teacher_takeaways[:]
    concepts = teacher_concepts[:]
    source = "teacher" if takeaways and concepts else payload.get("source")

    if not takeaways or not concepts:
        claude_result = await _generate_claude_insights(lesson, lesson_text, teacher_profile)
        if claude_result:
            if not takeaways:
                takeaways = claude_result.get("takeaways", [])
            if not concepts:
                concepts = claude_result.get("concepts", [])
            source = "teacher" if (teacher_takeaways or teacher_concepts) else "claude"
        else:
            extracted = build_lesson_insights(
                lesson_text,
                max_bullets=MAX_TAKEAWAYS,
                max_keywords=MAX_CONCEPTS,
            )
            if not takeaways:
                takeaways = _normalize_takeaways(extracted.get("summary"))
            if not concepts:
                concepts = _normalize_concepts(extracted.get("keywords"))
            source = "teacher" if (teacher_takeaways or teacher_concepts) else "extracted"

    if teacher_takeaways and teacher_concepts:
        source = "teacher"
    elif teacher_takeaways or teacher_concepts:
        source = "mixed"

    lesson.insights_json = {
        "teacher_takeaways": teacher_takeaways or None,
        "teacher_concepts": teacher_concepts or None,
        "takeaways": takeaways[:MAX_TAKEAWAYS],
        "concepts": concepts[:MAX_CONCEPTS],
        "source": source or "extracted",
        "generated_at": _utc_now_iso(),
    }
    await db.flush()
