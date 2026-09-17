"""Verify lesson chat Arabic formatting and personality personalization.

Tests kid_friendly, strict_teacher, and exam_prep modes against the same
Arabic lesson context. Checks Arabic output, tone variation, shared lesson
facts, and structured formatting (lists, paragraphs, bold).

Usage (from backend/):
    python scripts/verify_lesson_chat_arabic_personalization.py
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SAMPLE_LESSON = """
قواعد البيانات

قواعد البيانات هي أنظمة تُستخدم لتخزين وتنظيم المعلومات بشكل منظم.
الميزات الرئيسية لتخزين البيانات: تخزين البيانات، تنظيم البيانات، وتسهيل البحث والاسترجاع.
أمثلة على أنظمة قواعد البيانات: MySQL و PostgreSQL.
الجدول (Table) هو وحدة أساسية داخل قاعدة البيانات وتضم صفوفاً وأعمدة.
الاستعلام (Query) هو طلب لجلب أو تعديل البيانات من الجدول.
""".strip()

SAMPLE_QUESTION = "ما هي قواعد البيانات؟"

LESSON_FACT_TERMS = (
    "قواعد البيانات",
    "تخزين",
    "تنظيم",
    "MySQL",
    "PostgreSQL",
)

PERSONALITY_PROFILES = {
    "kid_friendly": {
        "grade": "3",
        "age": 8,
        "difficulty": "easy",
        "personality_mode": "kid_friendly",
        "academic_interests": ["علوم الحاسوب"],
        "personal_hobbies": ["الرسم"],
        "learning_style": "step_by_step",
        "future_goal": "undecided",
        "preferred_explanation_style": "normal",
    },
    "strict_teacher": {
        "grade": "10",
        "age": 16,
        "difficulty": "hard",
        "personality_mode": "strict_teacher",
        "academic_interests": ["الرياضيات"],
        "personal_hobbies": ["القراءة"],
        "learning_style": "theoretical",
        "future_goal": "engineer",
        "preferred_explanation_style": "normal",
    },
    "exam_prep": {
        "grade": "12",
        "age": 18,
        "difficulty": "hard",
        "personality_mode": "exam_prep",
        "academic_interests": ["علوم الحاسوب"],
        "personal_hobbies": ["البرمجة"],
        "learning_style": "step_by_step",
        "future_goal": "engineer",
        "preferred_explanation_style": "detailed",
    },
}


def _has_arabic(text: str) -> bool:
    return bool(re.search(r"[\u0600-\u06FF]", text or ""))


def _has_formatting(text: str) -> dict[str, bool]:
    return {
        "numbered_list": bool(re.search(r"(?m)^\d+\.\s+", text or "")),
        "bullet_list": bool(re.search(r"(?m)^[-•]\s+", text or "")),
        "bold_terms": bool(re.search(r"\*\*[^*]+\*\*", text or "")),
        "paragraph_breaks": "\n\n" in (text or "") or bool(re.search(r"(?m)^[^\n]+$\n[^\n\d•-]", text or "")),
    }


def _contains_lesson_facts(text: str) -> dict[str, bool]:
    lowered = (text or "").lower()
    return {term: term.lower() in lowered for term in LESSON_FACT_TERMS}


def _tone_signals(text: str) -> dict[str, int]:
    """Rough lexical signals — not a tone classifier, but useful for diff checks."""
    signals = {
        "simple_words": len(re.findall(r"\b(شي|بسيط|سهل|مثل)\b", text or "")),
        "exam_words": len(re.findall(r"\b(امتحان|مهم|انتبه|خطأ|شائع)\b", text or "")),
        "strict_words": len(re.findall(r"\b(يجب|دقيق|مباشر|فقط)\b", text or "")),
        "avg_sentence_len": 0,
    }
    sentences = re.split(r"[.؟!?\n]+", text or "")
    lengths = [len(s.split()) for s in sentences if s.strip()]
    signals["avg_sentence_len"] = round(sum(lengths) / len(lengths), 1) if lengths else 0
    return signals


async def _generate(profile: dict) -> str:
    from app.services.ai_service import generate_tutor_reply

    return await generate_tutor_reply(
        SAMPLE_QUESTION,
        [SAMPLE_LESSON],
        persona_prompt="أنت معلّم مساعد.",
        subject="علوم الحاسوب",
        grade=str(profile["grade"]),
        difficulty=profile["difficulty"],
        student_age=profile.get("age"),
        academic_interests=profile.get("academic_interests") or [],
        personal_hobbies=profile.get("personal_hobbies") or [],
        learning_style=profile.get("learning_style"),
        future_goal=profile.get("future_goal"),
        preferred_explanation_style=profile.get("preferred_explanation_style"),
        personality_mode=profile.get("personality_mode"),
    )


def _verify_budgets() -> dict:
    from app.services.ai_service import ANSWER_BUDGETS, _answer_budget

    expected = {
        "short": {"words": 80, "tokens": 300, "chars": 900},
        "normal": {"words": 300, "tokens": 900, "chars": 3500},
        "detailed": {"words": 700, "tokens": 2000, "chars": 7000},
    }
    budget_ok = all(
        ANSWER_BUDGETS[key][field] == expected[key][field]
        for key in expected
        for field in expected[key]
    )
    neutral_q = "أريد معلومات عن قواعد البيانات والجداول"
    pref_short = _answer_budget(neutral_q, preferred_explanation_style="short")
    pref_detailed = _answer_budget(neutral_q, preferred_explanation_style="detailed")
    definition_normal = _answer_budget("ما هو الجدول؟", preferred_explanation_style=None)

    return {
        "budget_values_ok": budget_ok,
        "preferred_short_forced": pref_short["words"] == 80,
        "preferred_detailed_forced": pref_detailed["words"] == 700,
        "definition_routes_normal": definition_normal["words"] == 300,
    }


async def main() -> None:
    from app.core.config import get_settings
    from app.services.ai_service import AI_UNAVAILABLE_REPLY

    settings = get_settings()

    static_checks = _verify_budgets()
    print("=== Static budget checks ===")
    for key, ok in static_checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}: {key}")

    if not settings.GEMINI_API_KEY and settings.LLM_PROVIDER.lower() != "ollama":
        print("\nSKIP: No GEMINI_API_KEY and LLM_PROVIDER is not ollama — live generation skipped.")
        out = Path(__file__).resolve().parent / "lesson_chat_arabic_personalization_results.json"
        out.write_text(
            json.dumps({"static_checks": static_checks, "live_skipped": True}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Written: {out}")
        return

    results: dict[str, dict] = {}
    for key, profile in PERSONALITY_PROFILES.items():
        reply = await _generate(profile)
        if not reply or reply.strip() == AI_UNAVAILABLE_REPLY.strip():
            print("\nSKIP live checks: AI unavailable (no Gemini/Ollama).")
            out = Path(__file__).resolve().parent / "lesson_chat_arabic_personalization_results.json"
            out.write_text(
                json.dumps(
                    {"static_checks": static_checks, "live_skipped": True, "reason": "ai_unavailable"},
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            print(f"Written: {out}")
            return
        formatting = _has_formatting(reply)
        facts = _contains_lesson_facts(reply)
        results[key] = {
            "profile": profile,
            "reply": reply,
            "reply_preview": (reply or "")[:500],
            "arabic": _has_arabic(reply),
            "formatting": formatting,
            "lesson_facts": facts,
            "tone_signals": _tone_signals(reply),
        }

    tones = {k: v["tone_signals"] for k, v in results.items()}
    tone_varies = len({json.dumps(t, sort_keys=True) for t in tones.values()}) > 1

    shared_facts = all(
        sum(v["lesson_facts"].values()) >= 3 for v in results.values()
    )
    all_arabic = all(v["arabic"] for v in results.values())
    formatted = all(
        v["formatting"]["numbered_list"] or v["formatting"]["bullet_list"]
        for v in results.values()
    )

    summary = {
        "static_checks": static_checks,
        "all_arabic": all_arabic,
        "tone_varies": tone_varies,
        "shared_lesson_facts": shared_facts,
        "structured_formatting": formatted,
        "profiles": results,
    }

    out = Path(__file__).resolve().parent / "lesson_chat_arabic_personalization_results.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== Live generation checks ===")
    print(f"  {'PASS' if all_arabic else 'FAIL'}: Arabic responses")
    print(f"  {'PASS' if tone_varies else 'FAIL'}: Different tone signals across profiles")
    print(f"  {'PASS' if shared_facts else 'FAIL'}: Shared lesson facts (>=3 terms each)")
    print(f"  {'PASS' if formatted else 'FAIL'}: Lists or bullets in replies")
    print(f"\nWritten: {out}")

    for key in results:
        print(f"\n--- {key} ---")
        print(results[key]["reply_preview"])


if __name__ == "__main__":
    asyncio.run(main())
