"""Educational Case world ownership for speaking Learning Packages.

Planner / constraints produce skill-centered focus and a communicative Educational Case.
Alex is never an educational title, objective, or case owner — Alex only continues
the same case world.
"""

from __future__ import annotations

import re
from typing import Any

# Product / tutor names that must never seed curriculum copy.
_ALEX_FRAMING_RE = re.compile(
    r"\b("
    r"speak\s+with\s+alex|"
    r"talk\s+with\s+alex|"
    r"practice\s+with\s+alex|"
    r"conversation\s+with\s+alex|"
    r"ready\s+for\s+alex|"
    r"uses?\s+alex|"
    r"alex\s+time|"
    r"\balex\b"
    r")\b",
    re.IGNORECASE,
)

# Realistic Educational Case packs — conflict-driven, discussion-ready (not fantasy).
_THEME_WORLDS: dict[str, dict[str, Any]] = {
    "travel_greetings": {
        "scenario_type": "airport",
        "story_world": (
            "An international airport arrivals hall where a late arrival creates tension "
            "between a traveler and the person waiting to meet them."
        ),
        "communicative_goal": "Use travel greetings and clarifications when meeting someone under time pressure.",
        "character_hints": ("Anna", "Diego"),
        "story_title_hint": "Late at Arrivals",
        "conflict_seed": "The flight is late and the welcome becomes awkward and urgent.",
        "alex_continuation_scenario": (
            "Continue the same airport-arrival case: greet the traveler, manage the late "
            "arrival tension, exchange names, and keep the welcome human."
        ),
    },
    "speaking_rate": {
        "scenario_type": "workplace",
        "story_world": (
            "A team meeting room where one coworker rushes explanations and the other "
            "cannot follow the next step."
        ),
        "communicative_goal": "Speak at a clear, comfortable pace listeners can follow under meeting pressure.",
        "character_hints": ("Maya", "Jordan"),
        "story_title_hint": "Too Fast in the Meeting",
        "conflict_seed": "Rushing to finish creates misunderstanding about who owns the task.",
        "alex_continuation_scenario": (
            "Continue the same meeting case about speaking clearly and steadily so both "
            "people understand the next step."
        ),
    },
    "family_conflict": {
        "scenario_type": "family",
        "story_world": (
            "A family kitchen where relatives disagree about a sensitive plan that affects "
            "everyone living in the house."
        ),
        "communicative_goal": "Express disagreement respectfully and stay clear about feelings and needs.",
        "character_hints": ("Lina", "Omar"),
        "story_title_hint": "A Hard Family Talk",
        "conflict_seed": "Love and anger collide when one person wants change and the other resists.",
        "alex_continuation_scenario": (
            "Continue the same family case: stay with Lina and Omar in the kitchen and "
            "work through the unresolved disagreement without inventing a new setting."
        ),
    },
    "job_interview": {
        "scenario_type": "job_interview",
        "story_world": (
            "A hiring office where a candidate answers tough questions while managing "
            "nerves and honesty."
        ),
        "communicative_goal": "Answer interview questions clearly and handle unexpected follow-ups.",
        "character_hints": ("Sara", "Mr. Hayes"),
        "story_title_hint": "The Unexpected Interview Question",
        "conflict_seed": "A surprising question forces the candidate to choose between speed and honesty.",
        "alex_continuation_scenario": (
            "Continue the same interview case with Sara and Mr. Hayes — respond to the "
            "next question in the same office without changing worlds."
        ),
    },
    "travel_emergency": {
        "scenario_type": "travel_emergency",
        "story_world": (
            "A transit desk where a missed connection creates cost, time pressure, and "
            "frustration with staff."
        ),
        "communicative_goal": "Explain a travel emergency clearly and request practical help politely.",
        "character_hints": ("Noor", "agent Kim"),
        "story_title_hint": "Missed Connection",
        "conflict_seed": "The passenger needs a fast fix while the agent must follow rules.",
        "alex_continuation_scenario": (
            "Continue the same travel-emergency case at the transit desk with Noor and "
            "agent Kim until the next booking decision is clear."
        ),
    },
    "medical_visit": {
        "scenario_type": "medical",
        "story_world": (
            "A clinic consultation room where a patient must describe symptoms accurately "
            "and understand next steps."
        ),
        "communicative_goal": "Describe symptoms and confirm understanding of medical next steps.",
        "character_hints": ("Rami", "Dr. Ellis"),
        "story_title_hint": "What the Doctor Needs to Know",
        "conflict_seed": "Fear of sounding dramatic makes the patient leave out key details.",
        "alex_continuation_scenario": (
            "Continue the same clinic case with Rami and Dr. Ellis — clarify symptoms and "
            "the plan without inventing a new medical world."
        ),
    },
    "ethical_dilemma": {
        "scenario_type": "ethics",
        "story_world": (
            "A university office hours visit where a student discovers a classmate may have "
            "broken an integrity rule."
        ),
        "communicative_goal": "Discuss an ethical dilemma carefully and justify a responsible choice.",
        "character_hints": ("Hana", "Professor Cole"),
        "story_title_hint": "Should I Say Something?",
        "conflict_seed": "Loyalty to a friend conflicts with fairness to the class.",
        "alex_continuation_scenario": (
            "Continue the same university ethics case with Hana and Professor Cole about "
            "what to do next — same people, same problem."
        ),
    },
    "workplace_conflict": {
        "scenario_type": "workplace",
        "story_world": (
            "An open-plan office where two colleagues disagree about responsibility after "
            "a client complains."
        ),
        "communicative_goal": "Negotiate responsibility clearly without escalating blame.",
        "character_hints": ("Alexa", "Ben"),
        "story_title_hint": "Who Owns This Complaint?",
        "conflict_seed": "Both sides feel unfairly blamed and need a workable next step.",
        "alex_continuation_scenario": (
            "Continue the same workplace conflict with Alexa and Ben about the client "
            "complaint — stay in that office and timeline."
        ),
    },
    "immigration": {
        "scenario_type": "immigration",
        "story_world": (
            "A government appointments counter where incomplete paperwork risks delaying "
            "a residency process."
        ),
        "communicative_goal": "Explain a documentation problem calmly and request a clear next step.",
        "character_hints": ("Yusuf", "Officer Park"),
        "story_title_hint": "One Missing Document",
        "conflict_seed": "A missing form threatens the appointment outcome.",
        "alex_continuation_scenario": (
            "Continue the same immigration-counter case with Yusuf and Officer Park about "
            "the missing document and next appointment."
        ),
    },
    "everyday": {
        "scenario_type": "everyday",
        "story_world": (
            "A familiar everyday setting where a small misunderstanding grows into a "
            "spoken conflict that still needs a clear decision."
        ),
        "communicative_goal": "Handle an everyday spoken conflict clearly and repair understanding.",
        "character_hints": ("Sam", "Lee"),
        "story_title_hint": "A Small Everyday Conflict",
        "conflict_seed": "A simple request turns into confusion about expectations.",
        "alex_continuation_scenario": (
            "Continue the same everyday case with Sam and Lee until the misunderstanding "
            "is repaired — same place, same people."
        ),
    },
}


def is_alex_framed_text(value: str | None) -> bool:
    text = (value or "").strip()
    if not text:
        return False
    return bool(_ALEX_FRAMING_RE.search(text))


def sanitize_educational_text(value: str | None, *, fallback: str) -> str:
    """Drop Alex/product framing; keep real educational wording."""
    text = (value or "").strip()
    if not text or is_alex_framed_text(text):
        return (fallback or "").strip() or "Today's speaking lesson"
    return text


def sanitize_objective_list(objectives: list[str], *, focus: str) -> list[str]:
    cleaned: list[str] = []
    for obj in objectives:
        text = sanitize_educational_text(str(obj or ""), fallback="")
        if text:
            cleaned.append(text)
    if cleaned:
        return cleaned
    return [f"Use {focus} clearly in a real spoken situation."]


def theme_key_for_skills(skill_ids: list[str], learning_focus: str) -> str:
    """Map skills/focus to a realistic Educational Case theme."""
    blob = " ".join([*(skill_ids or []), learning_focus or ""]).lower()
    if "travel_greeting" in blob or "greeting" in blob or "airport" in blob:
        return "travel_greetings"
    if (
        "appropriate_rate" in blob
        or "speaking rate" in blob
        or "fluency" in blob
        or "pace" in blob
    ):
        return "speaking_rate"
    if any(k in blob for k in ("family", "divorce", "parent", "relative")):
        return "family_conflict"
    if any(k in blob for k in ("interview", "job", "hiring", "cv", "resume")):
        return "job_interview"
    if any(k in blob for k in ("emergency", "missed flight", "connection", "passport")):
        return "travel_emergency"
    if any(k in blob for k in ("medical", "doctor", "clinic", "health", "symptom")):
        return "medical_visit"
    if any(k in blob for k in ("ethic", "honesty", "integrity", "cheat", "university")):
        return "ethical_dilemma"
    if any(k in blob for k in ("workplace", "colleague", "boss", "office", "client")):
        return "workplace_conflict"
    if any(k in blob for k in ("immigration", "visa", "residency", "document")):
        return "immigration"
    if "polite" in blob or "request" in blob:
        return "everyday"
    return "everyday"


def build_educational_world(
    *,
    skill_ids: list[str],
    skill_label: str,
) -> dict[str, Any]:
    """Backend-owned Educational Case world for PackageConstraints (not Alex curriculum)."""
    label = sanitize_educational_text(skill_label, fallback="Today's speaking lesson")
    theme = theme_key_for_skills(skill_ids, label)
    base = dict(_THEME_WORLDS.get(theme) or _THEME_WORLDS["everyday"])
    goal = sanitize_educational_text(
        str(base.get("communicative_goal") or ""),
        fallback=f"Practise {label} in a real spoken situation.",
    )
    return {
        "theme": theme,
        "learning_focus": label,
        "scenario_type": str(base["scenario_type"]),
        "story_world": str(base["story_world"]),
        "communicative_goal": goal if label.lower() in goal.lower() else f"{goal} Focus: {label}.",
        "character_hints": list(base.get("character_hints") or ("Sam", "Lee")),
        "story_title_hint": str(base.get("story_title_hint") or "Today's Case"),
        "conflict_seed": str(base.get("conflict_seed") or ""),
        "alex_continuation_scenario": str(base.get("alex_continuation_scenario") or ""),
    }


def educational_mission_title(kind_value: str, skill_label: str) -> str:
    """Human mission titles describe the lesson skill — never Alex."""
    label = sanitize_educational_text(skill_label, fallback="Speaking")
    kind = (kind_value or "").lower()
    if kind == "teaching":
        return f"Learn: {label}"
    if kind == "noticing":
        return f"Notice: {label}"
    if kind == "guided_practice":
        return f"Guided practice: {label}"
    if kind == "speak":
        return label
    if kind == "feedback":
        return f"Feedback on {label}"
    if kind == "transfer":
        return f"Transfer: {label}"
    if kind == "retention_review":
        return f"Review: {label}"
    return label
