"""Verify student learning memory influences lesson chat emphasis.

Student A: weak in networking
Student B: strong in networking
Same lesson question — expect same facts, different emphasis.

Usage (from backend/):
    python scripts/verify_student_learning_memory.py
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SAMPLE_LESSON = """
الشبكات

الشبكة هي مجموعة أجهزة متصلة لتبادل البيانات.
البروتوكول قواعد تواصل بين الأجهزة.
TCP بروتوكول موثوق يرسل البيانات بالترتيب.
IP مسؤول عن التوجيه بين الشبكات.
الميزات: مشاركة الموارد، التواصل، نقل البيانات.
""".strip()

SAMPLE_QUESTION = "ما هو بروتوكول TCP؟"

LESSON_FACT_TERMS = ("TCP", "بروتوكول", "موثوق", "IP", "الشبكة")

STUDENT_A_MEMORY = {
    "learning_memory_summary": (
        "مواضيع ضعيفة: الشبكات\n"
        "أخطاء/سوء فهم متكرر: الفرق بين TCP و UDP (×2)"
    ),
    "weak_topics": ["الشبكات"],
    "strong_topics": [],
    "repeated_mistakes": ["الفرق بين TCP و UDP"],
    "recent_lessons": ["مقدمة الشبكات (علوم الحاسوب)"],
}

STUDENT_B_MEMORY = {
    "learning_memory_summary": "مواضيع قوية: الشبكات",
    "weak_topics": [],
    "strong_topics": ["الشبكات"],
    "repeated_mistakes": [],
    "recent_lessons": ["الشبكات المتقدمة (علوم الحاسوب)", "مقدمة الشبكات (علوم الحاسوب)"],
}


def _has_arabic(text: str) -> bool:
    return bool(re.search(r"[\u0600-\u06FF]", text or ""))


def _lesson_facts(text: str) -> dict[str, bool]:
    return {term: term in (text or "") for term in LESSON_FACT_TERMS}


def _emphasis_signals(text: str) -> dict[str, int]:
    return {
        "careful_markers": len(re.findall(r"\b(خطوة|ببطء|ركّز|تذكير|مراجعة|بالتفصيل)\b", text or "")),
        "fast_markers": len(re.findall(r"\b(باختصار|سريع|متقدم|كما تعرف|بما أنك)\b", text or "")),
        "numbered_steps": len(re.findall(r"(?m)^\d+\.\s+", text or "")),
        "word_count": len((text or "").split()),
    }


async def _generate(memory: dict) -> str:
    from app.services.ai_service import generate_tutor_reply

    return await generate_tutor_reply(
        SAMPLE_QUESTION,
        [SAMPLE_LESSON],
        persona_prompt="أنت معلّم مساعد.",
        subject="علوم الحاسوب",
        grade="10",
        difficulty="medium",
        personality_mode="friendly_teacher",
        **memory,
    )


def _verify_service_helpers() -> dict[str, bool]:
    from app.services import student_learning_profile_service as svc

    class _Profile:
        weak_topics_json = "[]"
        strong_topics_json = "[]"
        repeated_mistakes_json = "[]"
        lesson_history_json = "[]"
        memory_summary = None

    profile = _Profile()
    svc.update_weaknesses(profile, topic="الشبكات", subject="علوم الحاسوب", source="quiz")
    weak = json.loads(profile.weak_topics_json)
    svc.update_strengths(profile, topic="الشبكات", subject="علوم الحاسوب", source="quiz")
    strong = json.loads(profile.strong_topics_json)
    summary = svc.generate_memory_summary(profile)

    kwargs = svc.learning_chat_kwargs(
        {
            "learning_memory_summary": summary,
            "weak_topics": svc.topic_labels(weak),
            "strong_topics": svc.topic_labels(strong),
            "repeated_mistakes": [],
            "recent_lessons": [],
        }
    )

    return {
        "weakness_tracking": len(weak) == 1 and weak[0].get("topic") == "الشبكات",
        "strength_clears_weak": len(json.loads(profile.weak_topics_json)) == 0,
        "strength_tracking": len(strong) == 1,
        "memory_summary_arabic": "مواضيع قوية" in summary,
        "learning_chat_kwargs": "learning_memory_summary" in kwargs,
    }


async def main() -> None:
    from app.core.config import get_settings
    from app.services.ai_service import AI_UNAVAILABLE_REPLY

    settings = get_settings()
    static_checks = _verify_service_helpers()

    print("=== Static learning memory checks ===")
    for key, ok in static_checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}: {key}")

    if not settings.GEMINI_API_KEY and settings.LLM_PROVIDER.lower() != "ollama":
        out = Path(__file__).resolve().parent / "student_learning_memory_results.json"
        out.write_text(
            json.dumps({"static_checks": static_checks, "live_skipped": True}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print("\nSKIP: No GEMINI_API_KEY — live generation skipped.")
        print(f"Written: {out}")
        return

    replies: dict[str, dict] = {}
    for label, memory in (("student_a_weak", STUDENT_A_MEMORY), ("student_b_strong", STUDENT_B_MEMORY)):
        reply = await _generate(memory)
        if not reply or reply.strip() == AI_UNAVAILABLE_REPLY.strip():
            out = Path(__file__).resolve().parent / "student_learning_memory_results.json"
            out.write_text(
                json.dumps(
                    {"static_checks": static_checks, "live_skipped": True, "reason": "ai_unavailable"},
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            print("\nSKIP live checks: AI unavailable.")
            print(f"Written: {out}")
            return

        replies[label] = {
            "memory": memory,
            "reply": reply,
            "reply_preview": reply[:500],
            "arabic": _has_arabic(reply),
            "lesson_facts": _lesson_facts(reply),
            "emphasis": _emphasis_signals(reply),
        }

    facts_ok = all(sum(r["lesson_facts"].values()) >= 3 for r in replies.values())
    emphasis_differs = (
        replies["student_a_weak"]["emphasis"]["careful_markers"]
        != replies["student_b_strong"]["emphasis"]["careful_markers"]
        or replies["student_a_weak"]["emphasis"]["numbered_steps"]
        != replies["student_b_strong"]["emphasis"]["numbered_steps"]
        or abs(
            replies["student_a_weak"]["emphasis"]["word_count"]
            - replies["student_b_strong"]["emphasis"]["word_count"]
        )
        >= 10
    )

    summary = {
        "static_checks": static_checks,
        "all_arabic": all(r["arabic"] for r in replies.values()),
        "shared_lesson_facts": facts_ok,
        "emphasis_differs": emphasis_differs,
        "students": replies,
    }

    out = Path(__file__).resolve().parent / "student_learning_memory_results.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== Live generation checks ===")
    print(f"  {'PASS' if summary['all_arabic'] else 'FAIL'}: Arabic responses")
    print(f"  {'PASS' if facts_ok else 'FAIL'}: Shared lesson facts")
    print(f"  {'PASS' if emphasis_differs else 'FAIL'}: Memory influences emphasis/structure")
    print(f"\nWritten: {out}")

    for label in replies:
        print(f"\n--- {label} ---")
        print(replies[label]["reply_preview"])


if __name__ == "__main__":
    asyncio.run(main())
