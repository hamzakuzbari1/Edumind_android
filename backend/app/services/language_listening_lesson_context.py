"""Student-safe listening lesson context from stored generation metadata."""



from __future__ import annotations



from app.models.language.content import LanguageContentItem

from app.services.language_learning_facts.assembler import assemble_lesson_facts, assemble_progression_facts

from app.services.language_learning_facts.labels import slug_label

from app.services.language_learning_goal import GOAL_KEY

from app.services.language_learning_goal.profiles import profile_for_goal

from app.services.language_learning_goal.types import LearningGoal

from app.services.language_learning_narrative.builder import build_lesson_narrative

from app.services.language_listening_challenge.constants import LESSON_CHALLENGE_KEY

from app.services.language_listening_curriculum.memory import CURRICULUM_KEY

from app.services.language_listening_explainability.signals import extract_signals

from app.services.language_listening_explainability.facts import build_explainability_facts

from app.services.language_listening_intelligence import HISTORY_KEY





def _as_dict(value: object) -> dict:

    return value if isinstance(value, dict) else {}





def _question_types(body: dict) -> list[str]:

    out: list[str] = []

    for q in body.get("questions") or []:

        if not isinstance(q, dict):

            continue

        qtype = str(q.get("type") or "").strip()

        if qtype and qtype not in out:

            out.append(qtype)

    return out





def _resolve_learning_goal_id(body: dict) -> str | None:

    goal_meta = _as_dict(body.get(GOAL_KEY))

    raw = str(goal_meta.get("learning_goal") or "").strip()

    if not raw:

        conf = _as_dict(body.get("listening_confidence_lesson"))

        raw = str(conf.get("learning_goal") or "").strip()

    if not raw:

        return None

    try:

        return LearningGoal(raw).value

    except ValueError:

        return raw





def build_listening_lesson_coach_context(

    item: LanguageContentItem,

    *,

    official_cefr: str | None = None,

    target_cefr: str | None = None,

) -> dict:

    """Build student-facing lesson context — copy from Learning Narrative Builder (Phase 2.1)."""

    body = item.body_json or {}

    intel = _as_dict(body.get(HISTORY_KEY))

    curriculum = _as_dict(body.get(CURRICULUM_KEY))

    challenge = _as_dict(body.get(LESSON_CHALLENGE_KEY))



    lesson_level = item.level.value if item.level else str(intel.get("level") or "")

    official = str(official_cefr or "").upper() or None

    goal_id = _resolve_learning_goal_id(body)



    situation = str(intel.get("situation") or "").strip()

    difficulty_band = str(

        challenge.get("effective_difficulty_band") or intel.get("difficulty_band") or "normal"

    ).strip()

    challenge_level = str(challenge.get("challenge_level") or "normal").strip()



    objectives = [str(o) for o in (curriculum.get("objectives") or []) if o]

    skill_focus = [str(s) for s in (curriculum.get("skill_focus") or []) if s]

    q_types = _question_types(body)



    signals = extract_signals(body, cefr_level=lesson_level)

    lesson_facts = assemble_lesson_facts(

        body,

        lesson_id=item.id,

        lesson_title=item.title,

        lesson_level=lesson_level,

        official_level=official,

        journey_target_level=str(target_cefr or "").upper() or None,

    )

    explain_facts = build_explainability_facts(

        signals,

        official_level=official,

        journey_target_level=str(target_cefr or "").upper() or None,

        lesson_level=lesson_level,

    )

    progression = assemble_progression_facts(

        official_level=official,

        journey_target_level=str(target_cefr or "").upper() or None,

    )

    narrative = build_lesson_narrative(lesson_facts, explain_facts, progression=progression)



    goal_label: str | None = None

    if goal_id:

        try:

            goal_label = profile_for_goal(LearningGoal(goal_id)).label

        except ValueError:

            goal_label = slug_label(goal_id)



    q_count = len(body.get("questions") or [])

    estimated_minutes = max(3, q_count * 2) if q_count else None



    level_mismatch = bool(

        official and lesson_level and official != lesson_level.upper()

    )



    return {

        "learning_goal": goal_id,

        "learning_goal_label": goal_label,

        "situation": situation or None,

        "situation_label": narrative.situation_label,

        "title": item.title,

        "lesson_level": lesson_level or None,

        "official_cefr": official,

        "difficulty_band": difficulty_band or None,

        "challenge_level": challenge_level or None,

        "objectives": objectives,

        "skill_focus": skill_focus,

        "question_types": q_types,

        "selection_reason": narrative.reason_selected,

        "coach_focus": list(narrative.student_focus),

        "coach_why": narrative.why_this_lesson,

        "coach_reward": narrative.reward,

        "level_mismatch": level_mismatch,

        "level_mismatch_reason": narrative.level_note,

        "estimated_minutes": estimated_minutes,

        "narrative_format": str(intel.get("narrative_format") or "").strip() or None,

        "lesson_intent": str(curriculum.get("lesson_intent") or "").strip() or None,

    }





def listening_lesson_api_payload(

    item: LanguageContentItem,

    *,

    body: dict,

    audio_url: str | None,

    audio_available: bool,

    progress_out: dict,

    official_cefr: str | None = None,

    target_cefr: str | None = None,

) -> dict:

    coach = build_listening_lesson_coach_context(

        item, official_cefr=official_cefr, target_cefr=target_cefr

    )

    return {

        "id": item.id,

        "title": item.title,

        "level": item.level.value if item.level else coach.get("lesson_level") or "A1",

        "instructions": body.get("instructions"),

        "questions": body.get("questions") or [],

        "audio_url": audio_url,

        "audio_available": audio_available,

        "progress": progress_out,

        "coach": coach,

    }
