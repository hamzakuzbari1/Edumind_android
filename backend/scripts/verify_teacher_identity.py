"""Verify teacher identity affects lesson chat style without changing facts.

Generates the same answer for one lesson with two teacher profiles:
- Teacher A: step_by_step + strict
- Teacher B: practical_examples + friendly

Usage (from backend/):
    python scripts/verify_teacher_identity.py
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
الميزات الرئيسية: تخزين البيانات، تنظيم البيانات، وتسهيل البحث والاسترجاع.
أمثلة: MySQL و PostgreSQL.
الجدول (Table) وحدة أساسية وتضم صفوفاً وأعمدة.
الاستعلام (Query) طلب لجلب أو تعديل البيانات.
""".strip()

SAMPLE_QUESTION = "ما هي قواعد البيانات؟"

LESSON_FACT_TERMS = (
    "قواعد البيانات",
    "تخزين",
    "تنظيم",
    "MySQL",
    "PostgreSQL",
)

TEACHER_A = {
    "label": "teacher_a_step_strict",
    "teacher_teaching_style": "step_by_step",
    "teacher_tone": "strict",
    "teacher_question_style": "explains_only",
    "teacher_motivation_level": "low",
    "teacher_display_name": "أستاذ سامر",
    "teacher_bio": "معلّم صارم يركّز على الدقة والخطوات.",
    "teacher_signature_phrase": "ركز معي بهذه النقطة.",
}

TEACHER_B = {
    "label": "teacher_b_practical_friendly",
    "teacher_teaching_style": "practical_examples",
    "teacher_tone": "friendly",
    "teacher_question_style": "mixed",
    "teacher_motivation_level": "high",
    "teacher_display_name": "أستاذة ليلى",
    "teacher_bio": "معلّمة ودودة تحب الأمثلة العملية.",
    "teacher_signature_phrase": "ممتاز، لنكمل.",
}


def _has_arabic(text: str) -> bool:
    return bool(re.search(r"[\u0600-\u06FF]", text or ""))


def _lesson_facts(text: str) -> dict[str, bool]:
    lowered = (text or "").lower()
    return {term: term.lower() in lowered for term in LESSON_FACT_TERMS}


def _structure_signals(text: str) -> dict[str, int | bool]:
    return {
        "numbered_list": bool(re.search(r"(?m)^\d+\.\s+", text or "")),
        "bullet_list": bool(re.search(r"(?m)^[-•]\s+", text or "")),
        "paragraph_breaks": text.count("\n\n") if text else 0,
        "word_count": len((text or "").split()),
        "strict_markers": len(re.findall(r"\b(يجب|دقيق|مباشر|فقط)\b", text or "")),
        "friendly_markers": len(re.findall(r"\b(ممتاز|رائع|منيح|تقدر)\b", text or "")),
        "example_markers": len(re.findall(r"\b(مثل|مثال|تطبيق|عملي)\b", text or "")),
    }


async def _generate(profile: dict) -> str:
    from app.services.ai_service import generate_tutor_reply

    return await generate_tutor_reply(
        SAMPLE_QUESTION,
        [SAMPLE_LESSON],
        persona_prompt="أنت معلّم مساعد في محادثة الدرس.",
        subject="علوم الحاسوب",
        grade="10",
        difficulty="medium",
        personality_mode="friendly_teacher",
        teacher_teaching_style=profile["teacher_teaching_style"],
        teacher_tone=profile["teacher_tone"],
        teacher_question_style=profile["teacher_question_style"],
        teacher_motivation_level=profile["teacher_motivation_level"],
        teacher_display_name=profile["teacher_display_name"],
        teacher_bio=profile["teacher_bio"],
        teacher_signature_phrase=profile["teacher_signature_phrase"],
    )


def _verify_teacher_maps() -> dict[str, bool]:
    from app.services.ai_service import (
        TEACHER_MOTIVATION,
        TEACHER_QUESTION_STYLE,
        TEACHER_TEACHING_STYLE,
        TEACHER_TONE,
        VALID_TEACHER_MOTIVATION_LEVELS,
        VALID_TEACHER_QUESTION_STYLES,
        VALID_TEACHER_TEACHING_STYLES,
        VALID_TEACHER_TONES,
    )

    return {
        "teaching_styles_complete": VALID_TEACHER_TEACHING_STYLES == set(TEACHER_TEACHING_STYLE),
        "tones_complete": VALID_TEACHER_TONES == set(TEACHER_TONE),
        "question_styles_complete": VALID_TEACHER_QUESTION_STYLES == set(TEACHER_QUESTION_STYLE),
        "motivation_complete": VALID_TEACHER_MOTIVATION_LEVELS == set(TEACHER_MOTIVATION),
    }


async def main() -> None:
    from app.core.config import get_settings
    from app.services.ai_service import AI_UNAVAILABLE_REPLY

    settings = get_settings()
    static_checks = _verify_teacher_maps()

    print("=== Static teacher profile checks ===")
    for key, ok in static_checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}: {key}")

    if not settings.GEMINI_API_KEY and settings.LLM_PROVIDER.lower() != "ollama":
        out = Path(__file__).resolve().parent / "teacher_identity_results.json"
        out.write_text(
            json.dumps({"static_checks": static_checks, "live_skipped": True}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print("\nSKIP: No GEMINI_API_KEY — live generation skipped.")
        print(f"Written: {out}")
        return

    results: dict[str, dict] = {}
    for profile in (TEACHER_A, TEACHER_B):
        reply = await _generate(profile)
        if not reply or reply.strip() == AI_UNAVAILABLE_REPLY.strip():
            out = Path(__file__).resolve().parent / "teacher_identity_results.json"
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

        results[profile["label"]] = {
            "profile": profile,
            "reply": reply,
            "reply_preview": reply[:500],
            "arabic": _has_arabic(reply),
            "lesson_facts": _lesson_facts(reply),
            "structure": _structure_signals(reply),
        }

    facts_a = sum(results[TEACHER_A["label"]]["lesson_facts"].values())
    facts_b = sum(results[TEACHER_B["label"]]["lesson_facts"].values())
    shared_facts = facts_a >= 3 and facts_b >= 3

    struct_a = results[TEACHER_A["label"]]["structure"]
    struct_b = results[TEACHER_B["label"]]["structure"]
    style_differs = (
        struct_a["numbered_list"] != struct_b["numbered_list"]
        or struct_a["example_markers"] != struct_b["example_markers"]
        or abs(struct_a["word_count"] - struct_b["word_count"]) >= 15
    )
    tone_differs = (
        struct_a["strict_markers"] != struct_b["strict_markers"]
        or struct_a["friendly_markers"] != struct_b["friendly_markers"]
    )

    summary = {
        "static_checks": static_checks,
        "all_arabic": all(v["arabic"] for v in results.values()),
        "shared_lesson_facts": shared_facts,
        "style_differs": style_differs,
        "tone_differs": tone_differs,
        "teachers": results,
    }

    out = Path(__file__).resolve().parent / "teacher_identity_results.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== Live generation checks ===")
    print(f"  {'PASS' if summary['all_arabic'] else 'FAIL'}: Arabic responses")
    print(f"  {'PASS' if shared_facts else 'FAIL'}: Shared lesson facts")
    print(f"  {'PASS' if style_differs else 'FAIL'}: Different teaching structure/signals")
    print(f"  {'PASS' if tone_differs else 'FAIL'}: Different tone signals")
    print(f"\nWritten: {out}")

    for key in results:
        print(f"\n--- {key} ---")
        print(results[key]["reply_preview"])


if __name__ == "__main__":
    asyncio.run(main())
