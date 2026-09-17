"""Phase 1 — Long-term Learner Memory (Adaptive Intelligence Layer).

Additive, extend-don't-fork. Persistent educational memory so the platform feels like it truly
knows the learner. NO new tables: it reuses what already exists —

- interests / goals / preferred activities / milestones -> `LanguageStudentProfile.preferences_json`
  (namespaced under a "memory" key; `reading_topics` is reused as a fallback for favorite topics).
- weaknesses -> DERIVED from the unified learner model (`ComponentMastery`, lowest p_mastery), never
  duplicated.
- last session summary -> read from `LanguageSpeakingConversationSession.summary_json`.

`get_prompt_context()` returns a token-efficient `[LEARNER MEMORY] … [/LEARNER MEMORY]` block that is
injected BEFORE existing prompts (never replacing them) — the Prompt Enrichment Pattern.
"""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.conversation import (
    LanguageSpeakingConversationSession,
    LanguageSpeakingConversationTurn,
)
from app.models.language.learner_model import ComponentMastery, KnowledgeComponent
from app.models.language.profile import LanguageStudentProfile

MEMORY_KEY = "memory"
# Free-form lists the learner controls; capped to stay token-efficient in the prompt.
LIST_FIELDS = ("interests", "favorite_topics", "learning_goals", "preferred_lesson_types")
MAX_ITEMS = 12
ITEM_MAX_LEN = 80
MAX_MILESTONES = 10
WEAKNESS_LIMIT = 5
# A component is "weak" while the learner is below this BKT mastery probability.
WEAK_MASTERY_BELOW = 0.6


# --------------------------------------------------------------------------------------------------
# Pure helpers (no I/O — unit-tested directly)
# --------------------------------------------------------------------------------------------------
def clean_list(values, *, cap: int = MAX_ITEMS, item_max: int = ITEM_MAX_LEN) -> list[str]:
    """Trim, de-dupe (case-insensitive, first wins), length-cap, count-cap a list of strings."""
    out: list[str] = []
    seen: set[str] = set()
    for v in values or []:
        if v is None:
            continue
        s = str(v).strip()
        if not s:
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s[:item_max])
        if len(out) >= cap:
            break
    return out


def format_memory_context(memory: dict | None, weaknesses: list[str], last_summary: str | None) -> str:
    """Token-efficient [LEARNER MEMORY] block. Returns "" when nothing is known (so we never
    inject an empty block / waste tokens)."""
    memory = memory or {}
    interests = memory.get("interests") or memory.get("favorite_topics") or []
    goals = memory.get("learning_goals") or []
    lesson_types = memory.get("preferred_lesson_types") or []
    milestones = memory.get("recent_milestones") or []

    lines: list[str] = []
    if interests:
        lines.append(f"Interests: {', '.join(interests)}")
    if goals:
        lines.append(f"Current goals: {', '.join(goals)}")
    if weaknesses:
        lines.append(f"Weak areas to gently reinforce: {', '.join(weaknesses)}")
    if lesson_types:
        lines.append(f"Preferred activities: {', '.join(lesson_types)}")
    if milestones:
        lines.append(f"Recent wins: {', '.join(milestones[-3:])}")
    if last_summary:
        lines.append(f"Last session: {last_summary}")

    if not lines:
        return ""
    return "[LEARNER MEMORY]\n" + "\n".join(lines) + "\n[/LEARNER MEMORY]"


def build_session_summary(*, turn_count: int, topics: list[str]) -> str:
    """A cheap, deterministic one-line session summary (no AI call) for the 'last session' context."""
    topics = clean_list(topics, cap=4)
    turns = max(int(turn_count or 0), 0)
    if topics:
        return f"Practised speaking ({turns} turns) on: {', '.join(topics)}."
    return f"Practised speaking ({turns} turns)."


# --------------------------------------------------------------------------------------------------
# Persistence (reuses existing tables/columns)
# --------------------------------------------------------------------------------------------------
async def _get_profile(
    db: AsyncSession, *, student_id: int, language_id: int
) -> LanguageStudentProfile | None:
    return (
        await db.execute(
            select(LanguageStudentProfile).where(
                LanguageStudentProfile.student_id == student_id,
                LanguageStudentProfile.language_id == language_id,
            )
        )
    ).scalar_one_or_none()


async def _get_or_create_profile(
    db: AsyncSession, *, student_id: int, language_id: int
) -> LanguageStudentProfile:
    profile = await _get_profile(db, student_id=student_id, language_id=language_id)
    if profile is None:
        profile = LanguageStudentProfile(student_id=student_id, language_id=language_id)
        db.add(profile)
        await db.flush()
    return profile


async def get_weaknesses(
    db: AsyncSession, *, student_id: int, language_id: int, limit: int = WEAKNESS_LIMIT
) -> list[str]:
    """Lowest-mastery components (with real evidence) from the unified learner model."""
    rows = (
        await db.execute(
            select(KnowledgeComponent.title, KnowledgeComponent.code)
            .join(ComponentMastery, ComponentMastery.component_id == KnowledgeComponent.id)
            .where(
                ComponentMastery.student_id == student_id,
                ComponentMastery.language_id == language_id,
                ComponentMastery.evidence_count > 0,
                ComponentMastery.p_mastery < WEAK_MASTERY_BELOW,
            )
            .order_by(ComponentMastery.p_mastery.asc())
            .limit(limit)
        )
    ).all()
    out: list[str] = []
    for title, code in rows:
        label = (title or code or "").strip()
        if label and label not in out:
            out.append(label)

    # Phase 2 loop: fold in the learner's most recurring mistakes (best-effort) so the prompt
    # context gently steers practice toward them, alongside the low-mastery components.
    try:
        from app.services.language_error_intelligence_service import top_issue_labels

        for issue in await top_issue_labels(db, student_id=student_id, language_id=language_id):
            if issue and issue not in out:
                out.append(issue)
    except Exception:  # never let the error loop break memory context
        pass

    return out[:limit]


async def get_last_summary(db: AsyncSession, *, student_id: int, language_id: int) -> str | None:
    """Most recent conversation session summary, if any."""
    sj = (
        await db.execute(
            select(LanguageSpeakingConversationSession.summary_json)
            .where(
                LanguageSpeakingConversationSession.student_id == student_id,
                LanguageSpeakingConversationSession.language_id == language_id,
                LanguageSpeakingConversationSession.summary_json.isnot(None),
            )
            .order_by(desc(LanguageSpeakingConversationSession.started_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    if not sj:
        return None
    if isinstance(sj, dict):
        text = (sj.get("summary") or sj.get("text") or "").strip()
        return text or None
    return str(sj).strip() or None


async def get_memory(db: AsyncSession, *, student_id: int, language_id: int) -> dict:
    """Full memory profile: stored fields + derived weaknesses + last session summary."""
    profile = await _get_profile(db, student_id=student_id, language_id=language_id)
    prefs = (profile.preferences_json or {}) if profile else {}
    mem = dict(prefs.get(MEMORY_KEY) or {})

    favorite_topics = mem.get("favorite_topics") or []
    if not favorite_topics and prefs.get("reading_topics"):
        favorite_topics = clean_list(prefs.get("reading_topics"))

    weaknesses = await get_weaknesses(db, student_id=student_id, language_id=language_id)
    last_summary = await get_last_summary(db, student_id=student_id, language_id=language_id)

    return {
        "interests": clean_list(mem.get("interests") or []),
        "favorite_topics": favorite_topics,
        "learning_goals": clean_list(mem.get("learning_goals") or []),
        "preferred_lesson_types": clean_list(mem.get("preferred_lesson_types") or []),
        "recent_milestones": list(mem.get("recent_milestones") or [])[-MAX_MILESTONES:],
        "derived_weaknesses": weaknesses,
        "last_session_summary": last_summary,
    }


async def update_memory(
    db: AsyncSession, *, student_id: int, language_id: int, updates: dict
) -> dict:
    """Update the learner-controlled memory fields (interests/goals/etc.). Returns the full memory."""
    profile = await _get_or_create_profile(db, student_id=student_id, language_id=language_id)
    prefs = dict(profile.preferences_json or {})
    mem = dict(prefs.get(MEMORY_KEY) or {})
    for field in LIST_FIELDS:
        if field in updates and updates[field] is not None:
            mem[field] = clean_list(updates[field])
    prefs[MEMORY_KEY] = mem
    profile.preferences_json = prefs  # reassign so SQLAlchemy tracks the JSONB change
    await db.flush()
    return await get_memory(db, student_id=student_id, language_id=language_id)


async def add_milestone(
    db: AsyncSession, *, student_id: int, language_id: int, milestone: str
) -> None:
    """Append a milestone (rolling, capped) — e.g. a CEFR level-up or a streak record."""
    text = (milestone or "").strip()
    if not text:
        return
    profile = await _get_or_create_profile(db, student_id=student_id, language_id=language_id)
    prefs = dict(profile.preferences_json or {})
    mem = dict(prefs.get(MEMORY_KEY) or {})
    milestones = list(mem.get("recent_milestones") or [])
    milestones.append(text[:120])
    mem["recent_milestones"] = milestones[-MAX_MILESTONES:]
    prefs[MEMORY_KEY] = mem
    profile.preferences_json = prefs
    await db.flush()


async def get_recent_summaries(
    db: AsyncSession, *, student_id: int, language_id: int, limit: int = 10
) -> list[dict]:
    """Recent conversation-session summaries (newest first) for the /memory/summary endpoint."""
    rows = (
        await db.execute(
            select(
                LanguageSpeakingConversationSession.id,
                LanguageSpeakingConversationSession.summary_json,
                LanguageSpeakingConversationSession.turn_count,
                LanguageSpeakingConversationSession.started_at,
                LanguageSpeakingConversationSession.ended_at,
            )
            .where(
                LanguageSpeakingConversationSession.student_id == student_id,
                LanguageSpeakingConversationSession.language_id == language_id,
                LanguageSpeakingConversationSession.summary_json.isnot(None),
            )
            .order_by(desc(LanguageSpeakingConversationSession.started_at))
            .limit(limit)
        )
    ).all()
    out: list[dict] = []
    for sid, sj, turn_count, started_at, ended_at in rows:
        text = ""
        if isinstance(sj, dict):
            text = (sj.get("summary") or sj.get("text") or "").strip()
        if not text:
            continue
        out.append(
            {
                "session_id": sid,
                "summary": text,
                "turn_count": int(turn_count or 0),
                "started_at": started_at,
                "ended_at": ended_at,
            }
        )
    return out


async def get_prompt_context(db: AsyncSession, *, student_id: int, language_id: int) -> str:
    """The [LEARNER MEMORY] block to inject before an existing prompt ("" when nothing known)."""
    data = await get_memory(db, student_id=student_id, language_id=language_id)
    return format_memory_context(
        {
            "interests": data["interests"],
            "favorite_topics": data["favorite_topics"],
            "learning_goals": data["learning_goals"],
            "preferred_lesson_types": data["preferred_lesson_types"],
            "recent_milestones": data["recent_milestones"],
        },
        data["derived_weaknesses"],
        data["last_session_summary"],
    )


async def summarize_session(db: AsyncSession, *, session_id: int) -> str | None:
    """Store a cheap deterministic summary on a conversation session's summary_json (at session end).

    Reuses the existing column; no AI call. Returns the summary text (or None if the session had no
    learner speech). Skips sessions that already carry a richer summary (e.g. scenario feedback)."""
    session = await db.get(LanguageSpeakingConversationSession, session_id)
    if session is None:
        return None
    existing = session.summary_json or {}
    if isinstance(existing, dict) and existing.get("summary"):
        return existing["summary"]

    turns = (
        await db.execute(
            select(LanguageSpeakingConversationTurn)
            .where(LanguageSpeakingConversationTurn.session_id == session_id)
            .order_by(LanguageSpeakingConversationTurn.turn_index)
        )
    ).scalars().all()
    spoke = [t for t in turns if (t.user_transcript or "").strip()]
    if not spoke:
        return None

    topics = [(t.evaluation_json or {}).get("topic") for t in spoke if isinstance(t.evaluation_json, dict)]
    summary = build_session_summary(turn_count=len(spoke), topics=[t for t in topics if t])
    sj = dict(existing) if isinstance(existing, dict) else {}
    sj["summary"] = summary
    session.summary_json = sj  # reassign so SQLAlchemy tracks the JSONB change
    await db.flush()
    return summary
