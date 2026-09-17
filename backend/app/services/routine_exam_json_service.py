"""Post-OCR JSON structuring for routine exam schedules — Claude text LLM only (no images/PDFs)."""

from __future__ import annotations

from app.core.config import get_settings
from app.services.claude_service import generate_claude_text_sync, is_claude_configured

settings = get_settings()

_LLM_TIMEOUT_SECONDS = 120


def structure_exam_schedule_json_from_text(ocr_text: str, today: str) -> str:
    if not is_claude_configured():
        raise ValueError("ANTHROPIC_API_KEY is required to structure exam schedule JSON")

    prompt = (
        f"استخرج جدول الامتحانات من النص التالي (نتيجة OCR). اليوم: {today}.\n"
        "أرجع JSON فقط بدون أي نص إضافي:\n"
        '[{"subject": "اسم المادة بالعربي", "date": "YYYY-MM-DD", "time": "HH:MM أو null"}]\n'
        "إذا لا يوجد امتحانات: []\n\n"
        f"--- OCR TEXT ---\n{ocr_text}"
    )
    return generate_claude_text_sync(
        prompt,
        temperature=0.0,
        max_tokens=4096,
        timeout=float(_LLM_TIMEOUT_SECONDS),
    )
