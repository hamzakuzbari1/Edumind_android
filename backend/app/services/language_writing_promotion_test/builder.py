"""WPA session builder."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.services.language_writing.enums import OfficialWritingCEFR, PromotionStatus, WritingGoal
from app.services.language_writing_promotion_test.types import (
    GOAL_WPA_BUNDLE_KEYS,
    WritingPromotionBundle,
    WritingPromotionTask,
)

_TASKS: dict[str, tuple[WritingPromotionTask, ...]] = {
    "travel_complaint_request": (
        WritingPromotionTask(
            "wpa:travel:1",
            "complaint_email",
            "email",
            "Write a formal email complaining about a delayed flight and requesting a refund.",
            80,
            180,
            25,
            ("Task response", "Register", "Grammar accuracy"),
        ),
        WritingPromotionTask(
            "wpa:travel:2",
            "request_message",
            "message",
            "Write a polite message asking hotel staff to resolve a room problem.",
            60,
            150,
            20,
            ("Organization", "Vocabulary", "Politeness"),
        ),
    ),
    "business_email_report": (
        WritingPromotionTask(
            "wpa:biz:1",
            "business_email",
            "email",
            "Write a professional email scheduling a meeting and confirming agenda items.",
            70,
            160,
            20,
            ("Professional tone", "Clarity", "Structure"),
        ),
        WritingPromotionTask(
            "wpa:biz:2",
            "short_report",
            "report",
            "Write a brief report summarizing project outcomes and next steps.",
            90,
            200,
            25,
            ("Task completion", "Linking words", "Accuracy"),
        ),
    ),
    "ielts_task1_task2": (
        WritingPromotionTask(
            "wpa:ielts:1",
            "opinion_paragraph",
            "essay",
            "Write a paragraph explaining why you chose your field of study.",
            80,
            180,
            25,
            ("Task response", "Coherence", "Lexical range"),
        ),
        WritingPromotionTask(
            "wpa:ielts:2",
            "argument",
            "essay",
            "Write a paragraph presenting one advantage and one disadvantage of online learning.",
            90,
            200,
            25,
            ("Organization", "Grammar", "Development"),
        ),
    ),
    "general_mixed_practical": (
        WritingPromotionTask(
            "wpa:gen:1",
            "paragraph",
            "paragraph",
            "Write a paragraph describing your daily routine and why it helps your goals.",
            70,
            160,
            20,
            ("Clarity", "Grammar", "Vocabulary"),
        ),
        WritingPromotionTask(
            "wpa:gen:2",
            "message",
            "message",
            "Write a short message inviting a friend to an event.",
            50,
            120,
            15,
            ("Task response", "Organization", "Accuracy"),
        ),
    ),
}


def build_writing_promotion_session(
    *,
    student_id: int,
    language_id: int,
    official_cefr: OfficialWritingCEFR,
    target_cefr: OfficialWritingCEFR,
    goal: WritingGoal,
) -> WritingPromotionBundle:
    bundle_key = GOAL_WPA_BUNDLE_KEYS.get(goal, "general_mixed_practical")
    tasks = _TASKS.get(bundle_key, _TASKS["general_mixed_practical"])
    sid = f"wpa:{student_id}:{uuid.uuid4().hex[:12]}"
    return WritingPromotionBundle(
        session_id=sid,
        student_id=student_id,
        language_id=language_id,
        official_cefr=official_cefr,
        target_cefr=target_cefr,
        goal=goal,
        tasks=tasks,
        status=PromotionStatus.in_progress,
    )


def session_to_dict(bundle: WritingPromotionBundle) -> dict:
    return {
        "session_id": bundle.session_id,
        "student_id": bundle.student_id,
        "language_id": bundle.language_id,
        "official_cefr": bundle.official_cefr.value,
        "target_cefr": bundle.target_cefr.value,
        "goal": bundle.goal.value,
        "status": bundle.status.value,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "tasks": [
            {
                "task_id": t.task_id,
                "task_type": t.task_type,
                "genre": t.genre,
                "prompt": t.prompt,
                "min_words": t.min_words,
                "max_words": t.max_words,
                "time_limit_minutes": t.time_limit_minutes,
            }
            for t in bundle.tasks
        ],
    }
