"""Map LessonExperienceBundle → legacy ListeningLessonOut shape (Phase 2.3 adapter)."""

from __future__ import annotations

from app.schemas.language_listening_bundles import LessonExperienceBundleOut


def bundle_to_legacy_payload(bundle: LessonExperienceBundleOut) -> dict:
    """Preserve old API field names for gradual migration / regression tests."""
    n = bundle.narrative
    p = bundle.playback
    return {
        "id": bundle.lesson_id,
        "title": bundle.lesson_title,
        "level": bundle.lesson_level,
        "instructions": p.instructions,
        "questions": [q.model_dump() for q in p.questions],
        "audio_url": p.audio_url,
        "audio_available": p.audio_available,
        "progress": p.progress.model_dump(),
        "coach": {
            "learning_goal": bundle.lesson_goal.id,
            "learning_goal_label": bundle.lesson_goal.label,
            "situation": bundle.situation,
            "situation_label": bundle.situation,
            "title": bundle.lesson_title,
            "lesson_level": bundle.lesson_level,
            "official_cefr": bundle.official_level,
            "selection_reason": n.reason_selected,
            "coach_focus": list(n.student_focus),
            "coach_why": n.why_this_lesson,
            "coach_reward": n.reward,
            "level_mismatch": bool(bundle.level_note),
            "level_mismatch_reason": bundle.level_note,
        },
        "meta": bundle.meta.model_dump(),
        "bundle": bundle.model_dump(mode="json"),
    }
