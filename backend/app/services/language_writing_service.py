"""Writing prompts — Phase 1 rule-based scoring (no AI)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import StudentProfile
from app.models.language.content import LanguageContentItem
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.models.language.progress import LanguageWritingProgress
from app.services.language_adaptive_service import record_lesson_result
from app.services.language_analytics_service import refresh_language_analytics
from app.services.language_content_service import get_content_item, list_content_items, pass_threshold_for_item
from app.services.language_curriculum_service import credit_skill_objectives
from app.services.language_engagement_service import record_activity
from app.services.language_grammar.enums import GrammarEvidenceSourceSkill
from app.services.language_grammar_skill_context import (
    SkillGrammarContext,
    build_skill_grammar_context,
    complete_current_skill_activity_async,
)
from app.services.language_learner_events import record_scored_practice
from app.services.language_learner_model_service import LanguageLearnerModelService, LearningEvent
from app.services.language_validation import count_sentences, validate_writing_submission
from app.services.language_placement_ai_scoring import score_writing_ai
from app.services.language_placement_scoring_service import percent_to_level, score_writing
from app.services.language_subscription_service import get_default_language

CONTENT_TYPE = "writing_prompt"
logger = logging.getLogger(__name__)

LEVEL_RANK = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}

LEVEL_DEFAULT_COMPONENT = {
    "A1": "grammar.present_simple",
    "A2": "grammar.past_tenses",
    "B1": "writing.cohesion_linkers",
    "B2": "grammar.conditionals",
    "C1": "writing.formal_register",
    "C2": "writing.formal_register",
}


def _grammar_writing_instruction(ctx: SkillGrammarContext | None) -> str:
    if ctx is None:
        return ""
    targets = ", ".join(ctx.grammar_targets[:4]) or ctx.display_name
    examples = "; ".join(ctx.examples[:3])
    instruction = (
        f"Grammar focus: {ctx.display_name}. You must use this grammar directly in your answer "
        f"at least three times, not only mention the grammar name. Useful forms: {targets}."
    )
    if examples:
        instruction += f" Model examples: {examples}."
    return instruction


def _with_grammar_writing_instruction(prompt: str, ctx: SkillGrammarContext | None) -> str:
    instruction = _grammar_writing_instruction(ctx)
    base = (prompt or "").strip()
    if not instruction or instruction in base:
        return base
    return f"{base}\n\n{instruction}" if base else instruction

COMPONENT_LABELS = {
    "grammar.present_simple": "Present simple and basic sentence structure",
    "grammar.past_tenses": "Past tense accuracy",
    "grammar.present_perfect": "Present perfect and life experiences",
    "writing.cohesion_linkers": "Paragraph organization and linking words",
    "grammar.conditionals": "Conditionals and complex sentences",
    "writing.formal_register": "Formal register and precise style",
}

COMPONENT_HINTS = {
    "grammar.present_simple": "Build clear, correct simple sentences.",
    "grammar.past_tenses": "Write about past events with accurate verbs.",
    "grammar.present_perfect": "Connect past experience to the present.",
    "writing.cohesion_linkers": "Organize ideas with first, then, because, however.",
    "grammar.conditionals": "Explain situations using if, would, could, and results.",
    "writing.formal_register": "Use a more formal tone and precise vocabulary.",
}

CRITERION_LABELS = {
    "task_achievement": "Task",
    "coherence_cohesion": "Organization",
    "grammar_accuracy": "Grammar accuracy",
    "grammar_range": "Grammar range",
    "lexical_resource": "Vocabulary",
    "mechanics": "Spelling and punctuation",
}

LEVEL_REQUIREMENTS = {
    "A1": (25, 3),
    "A2": (45, 4),
    "B1": (80, 6),
    "B2": (120, 8),
    "C1": (160, 10),
    "C2": (200, 12),
}

GRADE_LEVEL_CAP = {
    "early_primary": "A1",
    "upper_primary": "A2",
    "middle_school": "B1",
    "secondary": "C2",
    "unknown": "C2",
}

PROFILE_COMPONENTS = [
    ("task_response", "Task response"),
    ("sentence_structure", "Sentence structure"),
    ("grammar_accuracy", "Grammar accuracy"),
    ("vocabulary_range", "Vocabulary range"),
    ("spelling_punctuation", "Spelling and punctuation"),
    ("organization", "Organization"),
]

PROFILE_BASE_BY_LEVEL = {
    "A1": {
        "task_response": 45,
        "sentence_structure": 30,
        "grammar_accuracy": 30,
        "vocabulary_range": 35,
        "spelling_punctuation": 40,
        "organization": 25,
    },
    "A2": {
        "task_response": 55,
        "sentence_structure": 45,
        "grammar_accuracy": 45,
        "vocabulary_range": 45,
        "spelling_punctuation": 50,
        "organization": 40,
    },
    "B1": {
        "task_response": 65,
        "sentence_structure": 58,
        "grammar_accuracy": 55,
        "vocabulary_range": 58,
        "spelling_punctuation": 60,
        "organization": 55,
    },
    "B2": {
        "task_response": 72,
        "sentence_structure": 68,
        "grammar_accuracy": 65,
        "vocabulary_range": 68,
        "spelling_punctuation": 70,
        "organization": 66,
    },
    "C1": {
        "task_response": 80,
        "sentence_structure": 76,
        "grammar_accuracy": 74,
        "vocabulary_range": 76,
        "spelling_punctuation": 78,
        "organization": 74,
    },
    "C2": {
        "task_response": 86,
        "sentence_structure": 84,
        "grammar_accuracy": 82,
        "vocabulary_range": 84,
        "spelling_punctuation": 84,
        "organization": 82,
    },
}

PROFILE_CRITERIA_MAP = {
    "task_achievement": ("task_response",),
    "coherence_cohesion": ("organization",),
    "grammar_accuracy": ("grammar_accuracy",),
    "grammar_range": ("sentence_structure",),
    "lexical_resource": ("vocabulary_range",),
    "mechanics": ("spelling_punctuation",),
}

COMPONENT_PROFILE_MAP = {
    "grammar.present_simple": ("sentence_structure", "grammar_accuracy", "spelling_punctuation"),
    "grammar.past_tenses": ("grammar_accuracy", "sentence_structure"),
    "grammar.present_perfect": ("grammar_accuracy", "sentence_structure"),
    "writing.cohesion_linkers": ("organization", "task_response"),
    "grammar.conditionals": ("sentence_structure", "grammar_accuracy"),
    "writing.formal_register": ("task_response", "vocabulary_range", "organization"),
}

PROFILE_FOCUS_TO_COMPONENT = {
    "task_response": "writing.cohesion_linkers",
    "sentence_structure": "grammar.present_simple",
    "grammar_accuracy": "grammar.present_simple",
    "vocabulary_range": "writing.formal_register",
    "spelling_punctuation": "grammar.present_simple",
    "organization": "writing.cohesion_linkers",
}

PROFILE_STEP_LABELS = {
    "task_response": "Answer the task directly",
    "sentence_structure": "Build clearer sentences",
    "grammar_accuracy": "Fix the target grammar",
    "vocabulary_range": "Use a better word bank",
    "spelling_punctuation": "Proofread spelling and punctuation",
    "organization": "Organize ideas in order",
}

NEXT_LEVEL = {"A1": "A2", "A2": "B1", "B1": "B2", "B2": "C1", "C1": "C2", "C2": None}

CHECKPOINT_REQUIREMENTS = {
    "required_prompts": 6,
    "required_average": 75,
    "required_rewrites": 2,
    "required_components": 2,
}


def _sentence_count(text: str) -> int:
    return count_sentences(text)


def _level_str(level) -> str:
    value = getattr(level, "value", level)
    value = str(value or "A1").upper()
    return value if value in LEVEL_RANK else "A1"


def _grade_band(grade: int | None) -> str:
    if not grade:
        return "unknown"
    if grade <= 4:
        return "early_primary"
    if grade <= 6:
        return "upper_primary"
    if grade <= 9:
        return "middle_school"
    return "secondary"


def _practice_level_for_grade(level: str, grade_band: str) -> str:
    cap = GRADE_LEVEL_CAP.get(grade_band, "C2")
    return level if LEVEL_RANK.get(level, 1) <= LEVEL_RANK.get(cap, 6) else cap


def _requirements_for_context(level: str, grade_band: str) -> tuple[int, int]:
    words, sentences = LEVEL_REQUIREMENTS.get(level, LEVEL_REQUIREMENTS["A1"])
    if level == "A1" and grade_band == "early_primary":
        return 12, 3
    if level == "A1" and grade_band == "upper_primary":
        return 18, 3
    if level == "A2" and grade_band in {"early_primary", "upper_primary"}:
        return 35, 4
    return words, sentences


def _clamp_percent(value, default: int = 0) -> int:
    try:
        number = float(value)
    except Exception:
        number = float(default)
    return int(round(max(0.0, min(100.0, number))))


def _mini_lesson_for_component(component: str, *, level: str) -> dict:
    if component == "grammar.past_tenses":
        return {
            "title": "Past tense check",
            "explanation": "Use past verbs when the action already happened.",
            "examples": ["I went to school.", "We played football.", "She visited her friend."],
            "micro_practice": "Find two verbs in your draft and make sure they are in the past.",
        }
    if component == "grammar.present_perfect":
        return {
            "title": "Present perfect check",
            "explanation": "Use have or has plus the past participle for experiences and recent results.",
            "examples": ["I have learned new words.", "She has finished the project."],
            "micro_practice": "Add one sentence that starts with I have or I have never.",
        }
    if component == "writing.cohesion_linkers":
        return {
            "title": "Paragraph order",
            "explanation": "Put ideas in a clear order so the reader can follow your thinking.",
            "examples": ["First, we chose a topic.", "Then, we made a plan.", "Finally, we presented it."],
            "micro_practice": "Add first, then, because, or finally to connect two ideas.",
        }
    if component == "grammar.conditionals":
        return {
            "title": "If sentences",
            "explanation": "Use if plus would or could to explain a possible change and result.",
            "examples": ["If I had more time, I would read more.", "If we worked together, we could finish faster."],
            "micro_practice": "Add one sentence with if and would or could.",
        }
    if component == "writing.formal_register":
        return {
            "title": "Formal tone",
            "explanation": "Write politely, avoid slang, and make the request or opinion clear.",
            "examples": ["I am writing to ask for permission.", "I would appreciate your support."],
            "micro_practice": "Replace one casual phrase with a more polite phrase.",
        }
    return {
        "title": "Simple sentence check",
        "explanation": "A clear sentence usually has a subject, a verb, and one complete idea.",
        "examples": ["I study English.", "My teacher helps me.", "We play in the school yard."],
        "micro_practice": "Check that each sentence has a subject and a verb.",
    }


def _scaffold_for_prompt(*, level: str, grade_band: str, component: str) -> dict:
    if level == "A1":
        return {
            "exercise_type": "sentence_building" if grade_band == "early_primary" else "short_sentences",
            "word_bank": ["school", "teacher", "class", "friend", "study", "like", "go", "play"],
            "sentence_starters": ["I go to", "I study", "My teacher", "I like"],
            "checklist": ["Write 3 complete sentences.", "Use I, my, or we.", "End each sentence with a period."],
            "rewrite_instruction": "Rewrite your answer with clearer simple sentences and correct punctuation.",
        }
    if level == "A2":
        return {
            "exercise_type": "guided_paragraph",
            "word_bank": ["because", "then", "after", "usually", "yesterday", "enjoyed", "helped", "needed"],
            "sentence_starters": ["Yesterday,", "I felt", "Then I", "I liked it because"],
            "checklist": ["Write one clear paragraph.", "Use because, and, but, or then.", "Check past or present tense."],
            "rewrite_instruction": "Rewrite your paragraph with better linking words and corrected verb tense.",
        }
    if level == "B1":
        return {
            "exercise_type": "organized_paragraph",
            "word_bank": ["first", "however", "because", "for example", "finally", "improve", "support", "result"],
            "sentence_starters": ["First,", "For example,", "However,", "Finally,"],
            "checklist": ["Open with the main idea.", "Add details or examples.", "Finish with a clear ending."],
            "rewrite_instruction": "Rewrite with a stronger topic sentence, examples, and a clear ending.",
        }
    if level == "B2":
        return {
            "exercise_type": "extended_response",
            "word_bank": ["would", "could", "although", "therefore", "benefit", "challenge", "solution", "impact"],
            "sentence_starters": ["If I could change one thing,", "Although this may be difficult,", "This would help because"],
            "checklist": ["Explain your opinion.", "Use at least one complex sentence.", "Support the idea with a reason."],
            "rewrite_instruction": "Rewrite with more precise reasons and at least one stronger complex sentence.",
        }
    return {
        "exercise_type": "formal_extended_writing",
        "word_bank": ["request", "proposal", "benefit", "support", "appreciate", "therefore", "regarding", "consider"],
        "sentence_starters": ["I am writing to", "I would like to request", "This would benefit", "Thank you for considering"],
        "checklist": ["Use a formal opening.", "Explain the purpose clearly.", "Close politely."],
        "rewrite_instruction": "Rewrite with a more formal register, clearer purpose, and more precise vocabulary.",
    }


def _student_context(grade_band: str) -> dict:
    if grade_band == "early_primary":
        return {
            "audience": "your teacher",
            "place": "your classroom",
            "project": "a class poster",
            "problem": "keeping the classroom clean",
            "event": "a fun school day",
            "tone": "simple and polite",
        }
    if grade_band == "upper_primary":
        return {
            "audience": "your English teacher",
            "place": "your school",
            "project": "a school club activity",
            "problem": "helping new students feel welcome",
            "event": "a school trip",
            "tone": "clear and polite",
        }
    if grade_band == "middle_school":
        return {
            "audience": "your class teacher",
            "place": "your school",
            "project": "a student club project",
            "problem": "improving study time at school",
            "event": "a group presentation",
            "tone": "organized and respectful",
        }
    return {
        "audience": "your school coordinator",
        "place": "your school",
        "project": "a student-led community project",
        "problem": "improving the learning environment",
        "event": "a school debate or presentation",
        "tone": "formal and precise",
    }


def _component_from_focus(value: str | None, *, level: str) -> str:
    text = (value or "").strip().lower()
    if not text:
        return LEVEL_DEFAULT_COMPONENT.get(level, "grammar.present_simple")
    if text in COMPONENT_LABELS:
        return text
    if "past" in text:
        return "grammar.past_tenses"
    if "present perfect" in text or "experience" in text:
        return "grammar.present_perfect"
    if "condition" in text or "would" in text:
        return "grammar.conditionals"
    if "formal" in text or "register" in text:
        return "writing.formal_register"
    if "cohesion" in text or "link" in text or "paragraph" in text or "organ" in text:
        return "writing.cohesion_linkers"
    if "present" in text or "sentence" in text:
        return "grammar.present_simple"
    return LEVEL_DEFAULT_COMPONENT.get(level, "grammar.present_simple")


def _personalized_prompt_spec(*, level: str, grade_band: str, component: str) -> dict:
    words, sentences = _requirements_for_context(level, grade_band)
    ctx = _student_context(grade_band)

    specs = {
        "grammar.present_simple": {
            "title": "Three Sentences About My School" if level == "A1" else "My School Routine",
            "task_type": "short_sentences" if level == "A1" else "short_paragraph",
            "topic": "school",
            "prompt": (
                "Write 3 simple sentences about your school day. Say where you go, what you study, "
                "and one thing you like. Use clear present simple sentences."
                if level == "A1"
                else f"Write about your normal day at {ctx['place']}. Say when you arrive, what subjects "
                "you study, and one thing you like. Use clear present simple sentences."
            ),
        },
        "grammar.past_tenses": {
            "title": "Yesterday at School" if level in {"A1", "A2"} else "A School Day I Remember",
            "task_type": "short_story" if level in {"A1", "A2"} else "story",
            "topic": "school",
            "prompt": (
                "Write about one thing you did at school yesterday. Use past tense verbs like went, played, learned, or helped."
                if level == "A1"
                else f"Write about {ctx['event']} that happened recently. Explain what happened first, "
                "what you did, and how you felt at the end. Use past tense verbs."
            ),
        },
        "grammar.present_perfect": {
            "title": "What I Have Learned This Year",
            "task_type": "reflective_paragraph",
            "topic": "learning",
            "prompt": (
                "Write about two things you have learned in English this year. Explain what you have "
                "improved, what you still need to practise, and why it matters to you."
            ),
        },
        "writing.cohesion_linkers": {
            "title": "Plan a School Project",
            "task_type": "structured_paragraph",
            "topic": "school_project",
            "prompt": (
                f"Write a structured paragraph about {ctx['project']}. Use linking words like first, "
                "then, because, however, and finally. Explain the goal, the steps, and the result."
            ),
        },
        "grammar.conditionals": {
            "title": "If I Could Improve My School",
            "task_type": "opinion",
            "topic": "school_improvement",
            "prompt": (
                f"Write about {ctx['problem']}. Explain what you would change if you could, what "
                "might happen after the change, and why it would help students."
            ),
        },
        "writing.formal_register": {
            "title": "Formal Request About a School Project",
            "task_type": "formal_email",
            "topic": "school_project",
            "prompt": (
                f"Write a formal email to {ctx['audience']} asking for permission to organize "
                f"{ctx['project']}. Explain the purpose, the benefits for students, and what support "
                f"you need. Use a {ctx['tone']} tone."
            ),
        },
    }
    spec = specs.get(component, specs[LEVEL_DEFAULT_COMPONENT.get(level, "grammar.present_simple")])
    scaffold = _scaffold_for_prompt(level=level, grade_band=grade_band, component=component)
    return {
        **spec,
        **scaffold,
        "min_words": words,
        "min_sentences": sentences,
        "target_component": component,
        "target_focus": COMPONENT_LABELS.get(component, component),
        "practice_hint": COMPONENT_HINTS.get(component, "Write clearly and revise your answer."),
        "mini_lesson": _mini_lesson_for_component(component, level=level),
    }


def _infer_task_type(text: str) -> str:
    lower = text.lower()
    if "email" in lower:
        return "email"
    if "message" in lower or "reply" in lower:
        return "message"
    if "story" in lower:
        return "story"
    if "opinion" in lower or "argue" in lower or "agree" in lower:
        return "opinion"
    if "describe" in lower or "write about" in lower:
        return "short_paragraph"
    return "guided_writing"


def _infer_topic(text: str) -> str:
    lower = text.lower()
    topics = {
        "school": ("school", "class", "teacher", "classmate"),
        "family": ("family", "mother", "father", "brother", "sister"),
        "daily_routine": ("routine", "morning", "wake", "daily"),
        "travel": ("trip", "travel", "train", "bus", "delay"),
        "shopping": ("shop", "supermarket", "buy", "price", "dinner"),
        "home": ("home", "apartment", "room", "flatmate"),
        "food": ("food", "cafe", "dinner", "coffee"),
    }
    for topic, keys in topics.items():
        if any(k in lower for k in keys):
            return topic
    return "general"


def _prompt_metadata(item) -> dict:
    body = item.body_json or {}
    level = _level_str(item.level)
    text = f"{item.title or ''} {body.get('prompt') or ''} {body.get('instructions') or ''}"
    target = (
        body.get("target_component")
        or body.get("component_code")
        or body.get("grammar_focus")
        or body.get("target_focus")
    )
    component = _component_from_focus(str(target or ""), level=level)
    lower = text.lower()
    if not target:
        if any(k in lower for k in ("yesterday", "last ", "ago", "trip", "delay", "visited", "went")):
            component = "grammar.past_tenses"
        elif any(k in lower for k in ("have you", "experience", "ever", "already", "yet")):
            component = "grammar.present_perfect"
        elif any(k in lower for k in ("first", "then", "finally", "because", "although", "however", "paragraph")):
            component = "writing.cohesion_linkers"
        elif any(k in lower for k in ("if ", "would", "could", "condition")):
            component = "grammar.conditionals"
        elif any(k in lower for k in ("formal", "complaint", "application", "professional")):
            component = "writing.formal_register"

    grade_band = body.get("grade_band") or body.get("grade_range") or "unknown"
    scaffold = _scaffold_for_prompt(level=level, grade_band=str(grade_band), component=component)
    return {
        "target_component": component,
        "target_focus": COMPONENT_LABELS.get(component, component),
        "practice_hint": COMPONENT_HINTS.get(component, "Write clearly and revise your answer."),
        "task_type": body.get("task_type") or _infer_task_type(text),
        "topic": body.get("topic") or _infer_topic(text),
        "grade_band": grade_band,
        "exercise_type": body.get("exercise_type") or scaffold["exercise_type"],
        "word_bank": body.get("word_bank") or scaffold["word_bank"],
        "sentence_starters": body.get("sentence_starters") or scaffold["sentence_starters"],
        "checklist": body.get("checklist") or scaffold["checklist"],
        "mini_lesson": body.get("mini_lesson") or _mini_lesson_for_component(component, level=level),
        "rewrite_instruction": body.get("rewrite_instruction") or scaffold["rewrite_instruction"],
    }


def _is_visible_to_student(item, *, student_id: int) -> bool:
    body = item.body_json or {}
    owner = body.get("personalized_for_student_id")
    return owner in (None, "", student_id, str(student_id))


def _visible_items_for_student(items: list, *, student_id: int) -> list:
    return [item for item in items if _is_visible_to_student(item, student_id=student_id)]


async def _ensure_personalized_prompt(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    level: str,
    grade_band: str,
    component: str,
    grammar_ctx: SkillGrammarContext | None = None,
) -> LanguageContentItem | None:
    try:
        level_enum = LanguageLevel(level)
    except ValueError:
        level_enum = LanguageLevel.A1

    spec = _personalized_prompt_spec(level=level, grade_band=grade_band, component=component)
    source_version = "personalized_writing_path_v2"
    desired_body = {
        "prompt": _with_grammar_writing_instruction(spec["prompt"], grammar_ctx),
        "min_words": spec["min_words"],
        "min_sentences": spec["min_sentences"],
        "task_type": spec["task_type"],
        "topic": spec["topic"],
        "exercise_type": spec["exercise_type"],
        "word_bank": spec["word_bank"],
        "sentence_starters": spec["sentence_starters"],
        "checklist": spec["checklist"],
        "mini_lesson": spec["mini_lesson"],
        "rewrite_instruction": spec["rewrite_instruction"],
        "target_component": spec["target_component"],
        "target_focus": spec["target_focus"],
        "practice_hint": spec["practice_hint"],
        "grade_band": grade_band,
        "level_source": level,
        "personalized": True,
        "personalized_for_student_id": student_id,
        "source": source_version,
        "pass_threshold_percent": 70,
    }
    if grammar_ctx is not None:
        desired_body.update(
            {
                "grammar_id": grammar_ctx.grammar_id,
                "display_code": grammar_ctx.display_code,
                "grammar_title": grammar_ctx.display_name,
                "grammar_targets": list(grammar_ctx.grammar_targets),
                "grammar_source_skill": grammar_ctx.source_skill.value,
            }
        )
    existing_result = await db.execute(
        select(LanguageContentItem)
        .where(
            LanguageContentItem.language_id == language_id,
            LanguageContentItem.skill == LanguageSkill.writing,
            LanguageContentItem.content_type == CONTENT_TYPE,
            LanguageContentItem.level == level_enum,
            LanguageContentItem.is_published.is_(True),
        )
        .order_by(LanguageContentItem.sort_order, LanguageContentItem.id)
    )
    for item in existing_result.scalars().all():
        body = item.body_json or {}
        if (
            body.get("personalized_for_student_id") in (student_id, str(student_id))
            and body.get("target_component") == component
            and body.get("level_source") == level
        ):
            if body.get("source") != source_version:
                item.title = spec["title"]
                item.body_json = {**body, **desired_body}
                await db.flush()
            return item

    item = LanguageContentItem(
        language_id=language_id,
        skill=LanguageSkill.writing,
        level=level_enum,
        content_type=CONTENT_TYPE,
        title=spec["title"],
        sort_order=-1000,
        is_published=True,
        body_json=desired_body,
    )
    db.add(item)
    await db.flush()
    return item


def _criterion_feedback(metrics: dict, score_percent: float) -> str:
    feedback = (metrics or {}).get("feedback")
    if feedback:
        return str(feedback)
    if score_percent >= 80:
        return "Strong draft. Rewrite once to make the organization and word choice even clearer."
    if score_percent >= 60:
        return "Good start. Improve the weakest criterion below, then send a cleaner rewrite."
    return "This draft needs more support. Focus on the recommendation below and rewrite with clearer sentences."


def _next_focus_from_metrics(metrics: dict, *, level: str, target_component: str) -> dict:
    criteria = (metrics or {}).get("criteria") or {}
    if not criteria:
        return {
            "component_code": target_component,
            "label": COMPONENT_LABELS.get(target_component, target_component),
            "reason": COMPONENT_HINTS.get(target_component, "Practice this focus in the next draft."),
        }
    lowest_key = min(criteria, key=lambda k: float(criteria.get(k) or 0))
    if lowest_key == "coherence_cohesion":
        code = "writing.cohesion_linkers"
    elif lowest_key in ("grammar_accuracy", "grammar_range"):
        code = target_component if target_component.startswith("grammar.") else LEVEL_DEFAULT_COMPONENT.get(level, target_component)
    elif lowest_key == "mechanics":
        code = "grammar.present_simple"
    else:
        code = target_component
    label = COMPONENT_LABELS.get(code, code)
    criterion = CRITERION_LABELS.get(lowest_key, lowest_key.replace("_", " ").title())
    return {
        "component_code": code,
        "label": label,
        "reason": f"Your lowest writing criterion was {criterion}. Focus on {label.lower()} in the rewrite.",
    }


def _ensure_criteria(
    metrics: dict,
    *,
    score_percent: float,
    word_count: int,
    min_words: int,
    sentence_count: int,
    min_sentences: int,
) -> dict:
    criteria = dict((metrics or {}).get("criteria") or {})
    if criteria:
        return {key: _clamp_percent(value) for key, value in criteria.items()}

    length_score = min(100.0, (word_count / max(1, min_words)) * 100.0)
    sentence_score = min(100.0, (sentence_count / max(1, min_sentences)) * 100.0)
    mechanics = 85 if (metrics or {}).get("has_sentence_punct") else 45
    fallback = {
        "task_achievement": length_score,
        "coherence_cohesion": (sentence_score * 0.7) + 15,
        "grammar_accuracy": score_percent,
        "grammar_range": min(score_percent, (sentence_score * 0.6) + 30),
        "lexical_resource": (length_score * 0.75) + 10,
        "mechanics": mechanics,
    }
    return {key: _clamp_percent(value) for key, value in fallback.items()}


def _criteria_to_profile(criteria: dict) -> dict[str, list[int]]:
    profile_values: dict[str, list[int]] = {key: [] for key, _label in PROFILE_COMPONENTS}
    for criterion, value in (criteria or {}).items():
        for profile_key in PROFILE_CRITERIA_MAP.get(criterion, ()):
            profile_values.setdefault(profile_key, []).append(_clamp_percent(value))
    return profile_values


def _component_profile_keys(component: str) -> tuple[str, ...]:
    return COMPONENT_PROFILE_MAP.get(component, ("sentence_structure", "grammar_accuracy"))


def _writing_skill_breakdown(
    progress_map: dict[int, LanguageWritingProgress],
    *,
    weak_components: list[dict],
    level: str,
) -> list[dict]:
    scores = dict(PROFILE_BASE_BY_LEVEL.get(level, PROFILE_BASE_BY_LEVEL["A1"]))
    evidence: dict[str, int] = {key: 0 for key, _label in PROFILE_COMPONENTS}
    collected: dict[str, list[int]] = {key: [] for key, _label in PROFILE_COMPONENTS}

    for progress in progress_map.values():
        metrics = progress.metrics_json or {}
        criteria = metrics.get("criteria") or {}
        if not criteria and progress.score_percent is not None:
            criteria = {
                "task_achievement": progress.score_percent,
                "coherence_cohesion": progress.score_percent,
                "grammar_accuracy": progress.score_percent,
                "grammar_range": progress.score_percent,
                "lexical_resource": progress.score_percent,
                "mechanics": progress.score_percent,
            }
        for key, values in _criteria_to_profile(criteria).items():
            collected.setdefault(key, []).extend(values)

    for key, values in collected.items():
        if values:
            evidence[key] = len(values)
            scores[key] = _clamp_percent(sum(values) / len(values))

    for component in weak_components:
        component_code = str(component.get("code") or "")
        mastery = component.get("mastery_percent")
        if mastery is None:
            mastery = float(component.get("p_mastery") or 0.0) * 100.0
        mastery_score = _clamp_percent(mastery)
        if mastery_score <= 0 and int(component.get("evidence_count") or 0) == 0:
            mastery_score = min(scores.values()) if scores else 30
        for profile_key in _component_profile_keys(component_code):
            scores[profile_key] = min(scores.get(profile_key, 50), max(15, mastery_score))

    rows = []
    for key, label in PROFILE_COMPONENTS:
        score = _clamp_percent(scores.get(key, 0))
        if score >= 75:
            status_label = "strong"
        elif score >= 55:
            status_label = "developing"
        else:
            status_label = "needs_practice"
        rows.append({
            "code": key,
            "label": label,
            "score_percent": score,
            "status": status_label,
            "evidence_count": evidence.get(key, 0),
        })
    rows.sort(key=lambda row: (row["score_percent"], row["evidence_count"]))
    return rows


def _writing_plan_steps(*, skill_breakdown: list[dict], level: str, grade_band: str) -> list[dict]:
    weakest = skill_breakdown[:2] or [{"code": "sentence_structure", "label": "Sentence structure"}]
    steps = []
    for index, item in enumerate(weakest, start=1):
        code = str(item.get("code") or "sentence_structure")
        steps.append({
            "order": index,
            "status": "current" if index == 1 else "next",
            "focus_code": code,
            "title": PROFILE_STEP_LABELS.get(code, item.get("label") or code),
            "description": f"Practice this at {level} with a task that fits {grade_band.replace('_', ' ')}.",
        })
    steps.append({
        "order": len(steps) + 1,
        "status": "rewrite",
        "focus_code": "rewrite",
        "title": "Rewrite after feedback",
        "description": "Improve Draft 1 using the mini lesson, then compare the new draft with the old one.",
    })
    next_level = NEXT_LEVEL.get(level)
    steps.append({
        "order": len(steps) + 1,
        "status": "checkpoint",
        "focus_code": "checkpoint",
        "title": f"Mini checkpoint for {next_level}" if next_level else "Maintain C2 writing",
        "description": "Unlock this after enough completed tasks, rewrites, and a stable average score.",
    })
    return steps


def _checkpoint_status(progress_map: dict[int, LanguageWritingProgress], *, level: str) -> dict:
    requirements = dict(CHECKPOINT_REQUIREMENTS)
    completed = [p for p in progress_map.values() if p.completed_at]
    scores = [float(p.score_percent) for p in completed if p.score_percent is not None]
    all_scores = [float(p.score_percent) for p in progress_map.values() if p.score_percent is not None]
    average_score = round(sum(scores) / len(scores), 1) if scores else (round(sum(all_scores) / len(all_scores), 1) if all_scores else None)
    rewrites = 0
    covered_components = set()
    for progress in progress_map.values():
        metrics = progress.metrics_json or {}
        attempts = metrics.get("attempts") or []
        if len(attempts) >= 2:
            try:
                first_score = float(attempts[0].get("score_percent") or 0.0)
                last_score = float(attempts[-1].get("score_percent") or 0.0)
                if last_score >= first_score + 3:
                    rewrites += 1
            except Exception:
                pass
        component = metrics.get("target_component")
        if component and progress.completed_at:
            covered_components.add(str(component))

    prompt_ratio = min(1.0, len(completed) / max(1, requirements["required_prompts"]))
    average_ratio = min(1.0, (average_score or 0.0) / requirements["required_average"])
    rewrite_ratio = min(1.0, rewrites / max(1, requirements["required_rewrites"]))
    component_ratio = min(1.0, len(covered_components) / max(1, requirements["required_components"]))
    progress_percent = _clamp_percent(((prompt_ratio + average_ratio + rewrite_ratio + component_ratio) / 4.0) * 100.0)
    missing = []
    if len(completed) < requirements["required_prompts"]:
        missing.append(f"Complete {requirements['required_prompts'] - len(completed)} more writing tasks.")
    if (average_score or 0.0) < requirements["required_average"]:
        missing.append(f"Reach an average of {requirements['required_average']}%.")
    if rewrites < requirements["required_rewrites"]:
        missing.append(f"Improve {requirements['required_rewrites'] - rewrites} more rewrite task.")
    if len(covered_components) < requirements["required_components"]:
        missing.append("Cover one more writing focus.")

    return {
        "ready": not missing and bool(NEXT_LEVEL.get(level)),
        "level": level,
        "next_level": NEXT_LEVEL.get(level),
        "progress_percent": progress_percent,
        "completed_prompts": len(completed),
        "required_prompts": requirements["required_prompts"],
        "average_score_percent": average_score,
        "required_average": requirements["required_average"],
        "improved_rewrites": rewrites,
        "required_rewrites": requirements["required_rewrites"],
        "covered_components": sorted(covered_components),
        "required_components": requirements["required_components"],
        "missing": missing,
    }


def _rewrite_prompt(next_focus: dict, metadata: dict) -> str:
    focus = next_focus.get("label") or metadata.get("target_focus") or "the weakest part"
    instruction = metadata.get("rewrite_instruction") or "Rewrite your answer using the feedback."
    return f"{instruction} Focus especially on {str(focus).lower()}."


def _component_score(component_code: str, criteria: dict, *, default_score: float) -> float:
    criteria = criteria or {}
    if component_code == "writing.cohesion_linkers":
        return float(criteria.get("coherence_cohesion") or default_score)
    if component_code == "writing.formal_register":
        values = [criteria.get("task_achievement"), criteria.get("lexical_resource"), criteria.get("coherence_cohesion")]
    elif component_code == "grammar.conditionals":
        values = [criteria.get("grammar_range"), criteria.get("grammar_accuracy")]
    elif component_code in {"grammar.past_tenses", "grammar.present_perfect"}:
        values = [criteria.get("grammar_accuracy"), criteria.get("grammar_range")]
    else:
        values = [criteria.get("grammar_accuracy"), criteria.get("grammar_range"), criteria.get("mechanics")]
    numbers = [float(value) for value in values if value is not None]
    return min(numbers) if numbers else float(default_score)


def _attempt_history(
    *,
    previous_metrics: dict,
    submitted_at: datetime,
    text: str,
    score_percent: float,
    word_count: int,
    sentence_count: int,
    criteria: dict,
    feedback: str,
) -> tuple[list[dict], int, float | None, float | None]:
    attempts = list((previous_metrics or {}).get("attempts") or [])
    previous_score = None
    if attempts:
        try:
            previous_score = float(attempts[-1].get("score_percent"))
        except Exception:
            previous_score = None
    attempt_number = len(attempts) + 1
    improvement = round(float(score_percent) - previous_score, 1) if previous_score is not None else None
    attempts.append({
        "number": attempt_number,
        "submitted_at": submitted_at.isoformat(),
        "text": text,
        "score_percent": round(float(score_percent), 1),
        "word_count": int(word_count),
        "sentence_count": int(sentence_count),
        "criteria": criteria,
        "feedback": feedback,
    })
    return attempts[-6:], attempt_number, previous_score, improvement


async def _writing_progress_map(db: AsyncSession, *, student_id: int, ids: list[int]) -> dict[int, LanguageWritingProgress]:
    if not ids:
        return {}
    result = await db.execute(
        select(LanguageWritingProgress).where(
            LanguageWritingProgress.student_id == student_id,
            LanguageWritingProgress.content_item_id.in_(ids),
        )
    )
    return {p.content_item_id: p for p in result.scalars().all()}


async def _all_writing_progress(db: AsyncSession, *, student_id: int) -> dict[int, LanguageWritingProgress]:
    result = await db.execute(
        select(LanguageWritingProgress).where(LanguageWritingProgress.student_id == student_id)
    )
    return {p.content_item_id: p for p in result.scalars().all()}


def _progress_out(progress: LanguageWritingProgress | None) -> dict:
    if not progress:
        return {
            "submitted_text": None,
            "word_count": 0,
            "score_percent": None,
            "completed_at": None,
            "submitted_at": None,
            "metrics": {},
            "feedback": "",
            "criteria": {},
            "flags": {},
            "attempts": [],
            "attempt_count": 0,
            "attempt_number": 0,
            "previous_score_percent": None,
            "improvement_percent": None,
            "rewrite_required": False,
            "rewrite_prompt": "",
            "mini_lesson": None,
        }
    metrics = progress.metrics_json or {}
    attempts = metrics.get("attempts") or []
    return {
        "submitted_text": progress.submitted_text,
        "word_count": progress.word_count,
        "score_percent": progress.score_percent,
        "completed_at": progress.completed_at,
        "submitted_at": progress.submitted_at,
        "metrics": metrics,
        "feedback": _criterion_feedback(metrics, float(progress.score_percent or 0.0)),
        "criteria": metrics.get("criteria") or {},
        "flags": metrics.get("flags") or {},
        "scoring_version": progress.scoring_version,
        "level_estimate": progress.level_estimate.value if progress.level_estimate else None,
        "attempts": attempts,
        "attempt_count": len(attempts),
        "attempt_number": metrics.get("attempt_number") or len(attempts),
        "previous_score_percent": metrics.get("previous_score_percent"),
        "improvement_percent": metrics.get("improvement_percent"),
        "rewrite_required": bool(metrics.get("rewrite_required")),
        "rewrite_prompt": metrics.get("rewrite_prompt") or "",
        "mini_lesson": metrics.get("mini_lesson"),
    }


def _prompt_out(
    item,
    progress: LanguageWritingProgress | None,
    *,
    recommended_id: int | None = None,
    recommended_reason: str = "",
    grammar_ctx: SkillGrammarContext | None = None,
) -> dict:
    body = item.body_json or {}
    metadata = _prompt_metadata(item)
    return {
        "id": item.id,
        "title": item.title,
        "level": item.level.value if item.level else None,
        "prompt": _with_grammar_writing_instruction(body.get("prompt") or "", grammar_ctx),
        "prompt_ar": body.get("prompt_ar"),
        "grammar_id": grammar_ctx.grammar_id if grammar_ctx else body.get("grammar_id"),
        "grammar_title": grammar_ctx.display_name if grammar_ctx else body.get("grammar_title"),
        "min_words": int(body.get("min_words") or 20),
        "min_sentences": int(body.get("min_sentences") or 2),
        "target_component": metadata["target_component"],
        "target_focus": metadata["target_focus"],
        "practice_hint": metadata["practice_hint"],
        "task_type": metadata["task_type"],
        "topic": metadata["topic"],
        "exercise_type": metadata["exercise_type"],
        "word_bank": metadata["word_bank"],
        "sentence_starters": metadata["sentence_starters"],
        "checklist": metadata["checklist"],
        "mini_lesson": metadata["mini_lesson"],
        "rewrite_instruction": metadata["rewrite_instruction"],
        "recommended": item.id == recommended_id,
        "recommendation_reason": recommended_reason if item.id == recommended_id else "",
        "progress": _progress_out(progress),
    }


async def _student_grade(db: AsyncSession, *, student_id: int) -> int | None:
    return await db.scalar(select(StudentProfile.grade).where(StudentProfile.user_id == student_id).limit(1))


async def _writing_component_profile(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    level: str,
) -> list[dict]:
    profile = await LanguageLearnerModelService(db).get_component_profile(
        student_id=student_id, language_id=language_id
    )
    max_rank = LEVEL_RANK.get(level, 1)
    writing = [
        c for c in profile
        if c.get("skill") == "writing" and LEVEL_RANK.get(str(c.get("cefr_level") or "A1"), 1) <= max_rank
    ]
    if not writing:
        code = LEVEL_DEFAULT_COMPONENT.get(level, "grammar.present_simple")
        return [{
            "code": code,
            "label": COMPONENT_LABELS.get(code, code),
            "category": "writing",
            "cefr_level": level,
            "p_mastery": 0.0,
            "confidence": 0.0,
            "evidence_count": 0,
            "mastery_percent": 0,
        }]
    writing.sort(key=lambda c: (float(c.get("p_mastery") or 0.0), int(c.get("evidence_count") or 0)))
    return [
        {
            **c,
            "label": COMPONENT_LABELS.get(c.get("code"), c.get("code")),
            "mastery_percent": int(round(float(c.get("p_mastery") or 0.0) * 100)),
        }
        for c in writing[:4]
    ]


async def _writing_items_for_level(
    db: AsyncSession,
    *,
    language_id: int,
    level: str,
    student_id: int,
) -> list[LanguageContentItem]:
    try:
        level_enum = LanguageLevel(level)
    except ValueError:
        level_enum = LanguageLevel.A1
    result = await db.execute(
        select(LanguageContentItem)
        .where(
            LanguageContentItem.language_id == language_id,
            LanguageContentItem.skill == LanguageSkill.writing,
            LanguageContentItem.content_type == CONTENT_TYPE,
            LanguageContentItem.level == level_enum,
            LanguageContentItem.is_published.is_(True),
        )
        .order_by(LanguageContentItem.sort_order, LanguageContentItem.id)
    )
    return _visible_items_for_student(list(result.scalars().all()), student_id=student_id)


def _focused_items(
    items: list[LanguageContentItem],
    *,
    personalized_id: int | None,
    weak_components: list[dict],
    limit: int = 6,
) -> list[LanguageContentItem]:
    focus_codes = [str(c.get("code") or "") for c in weak_components if c.get("code")]
    personalized = [item for item in items if item.id == personalized_id]
    related = [
        item for item in items
        if item.id != personalized_id and _prompt_metadata(item).get("target_component") in focus_codes
    ]
    filler = [item for item in items if item.id != personalized_id and item not in related]
    return [*personalized, *related, *filler][:limit]


def _recommend_prompt(
    items: list,
    progress_map: dict[int, LanguageWritingProgress],
    *,
    weak_components: list[dict],
) -> tuple[int | None, str]:
    if not items:
        return None, ""
    focus_order = [str(c.get("code") or "") for c in weak_components if c.get("code")]
    scored: list[tuple[float, int, str]] = []
    for item in items:
        body = item.body_json or {}
        metadata = _prompt_metadata(item)
        progress = progress_map.get(item.id)
        score = 0.0
        reason = "Recommended from your current writing level."
        target = metadata["target_component"]
        if body.get("personalized"):
            score += 72
            reason = f"Recommended because your writing path is focusing on {metadata['target_focus']}."
        if target in focus_order:
            idx = focus_order.index(target)
            score += 60 - (idx * 8)
            reason = f"Recommended because your next focus is {metadata['target_focus']}."
        if not progress:
            score += 24
        elif progress.completed_at:
            score -= 18
        elif progress.score_percent is not None and progress.score_percent < 70:
            score += 18
            reason = "Recommended because your last attempt still needs a rewrite."
        else:
            score += 6
        score -= float(item.sort_order or 0) / 1000.0
        scored.append((score, item.id, reason))
    scored.sort(reverse=True)
    return scored[0][1], scored[0][2]


async def list_writing(db: AsyncSession, *, student_id: int) -> dict:
    student_level, lesson_level, _items = await list_content_items(
        db,
        student_id=student_id,
        content_type=CONTENT_TYPE,
        skill=LanguageSkill.writing,
        level_skill=LanguageSkill.writing,
    )
    language = await get_default_language(db)
    grammar_ctx = await build_skill_grammar_context(
        db,
        student_id=student_id,
        language_id=language.id,
        source_skill=GrammarEvidenceSourceSkill.writing,
    )
    grade = await _student_grade(db, student_id=student_id)
    grade_band = _grade_band(grade)
    placement_level = _level_str(student_level)
    practice_level = _practice_level_for_grade(placement_level, grade_band)
    items = await _writing_items_for_level(
        db,
        language_id=language.id,
        level=practice_level,
        student_id=student_id,
    )
    weak_components = await _writing_component_profile(
        db, student_id=student_id, language_id=language.id, level=practice_level
    )
    all_prog = await _all_writing_progress(db, student_id=student_id)
    skill_breakdown = _writing_skill_breakdown(all_prog, weak_components=weak_components, level=practice_level)
    primary_weakness = skill_breakdown[0] if skill_breakdown else None
    profile_component = PROFILE_FOCUS_TO_COMPONENT.get(str((primary_weakness or {}).get("code") or ""))
    if profile_component:
        next_focus = {
            "code": profile_component,
            "label": COMPONENT_LABELS.get(profile_component, profile_component),
            "category": "writing",
            "cefr_level": practice_level,
            "mastery_percent": (primary_weakness or {}).get("score_percent", 0),
            "reason": (primary_weakness or {}).get("label"),
        }
    else:
        next_focus = weak_components[0] if weak_components else {}
    personalized = await _ensure_personalized_prompt(
        db,
        student_id=student_id,
        language_id=language.id,
        level=practice_level,
        grade_band=grade_band,
        component=str(next_focus.get("code") or LEVEL_DEFAULT_COMPONENT.get(practice_level, "grammar.present_simple")),
        grammar_ctx=grammar_ctx,
    )
    if personalized and all(item.id != personalized.id for item in items):
        items = [personalized, *items]
    items = _focused_items(items, personalized_id=personalized.id if personalized else None, weak_components=weak_components)
    prog = await _writing_progress_map(db, student_id=student_id, ids=[i.id for i in items])
    recommended_id, recommended_reason = _recommend_prompt(items, prog, weak_components=weak_components)
    if personalized:
        personalized_progress = prog.get(personalized.id)
        if not personalized_progress or not personalized_progress.completed_at:
            personalized_metadata = _prompt_metadata(personalized)
            recommended_id = personalized.id
            recommended_reason = f"Recommended because your writing path is focusing on {personalized_metadata['target_focus']}."
    plan_steps = _writing_plan_steps(skill_breakdown=skill_breakdown, level=practice_level, grade_band=grade_band)
    checkpoint = _checkpoint_status(all_prog, level=practice_level)
    completed = checkpoint["completed_prompts"]
    scores = [float(p.score_percent) for p in all_prog.values() if p.score_percent is not None]
    return {
        "student_level": student_level.value,
        "lesson_level": practice_level,
        "recommended_prompt_id": recommended_id,
        "recommended_reason": recommended_reason,
        "writing_profile": {
            "level": placement_level,
            "practice_level": practice_level,
            "grade": grade,
            "grade_band": grade_band,
            "next_focus": next_focus,
            "primary_weakness": primary_weakness,
            "weak_components": weak_components,
            "skill_breakdown": skill_breakdown,
            "plan_steps": plan_steps,
            "checkpoint": checkpoint,
            "completed_prompts": completed,
            "total_prompts": checkpoint["required_prompts"],
            "average_score_percent": round(sum(scores) / len(scores), 1) if scores else None,
        },
        "prompts": [
            _prompt_out(
                i,
                prog.get(i.id),
                recommended_id=recommended_id,
                recommended_reason=recommended_reason,
                grammar_ctx=grammar_ctx,
            )
            for i in items
        ],
    }


async def get_writing_prompt(db: AsyncSession, *, student_id: int, prompt_id: int) -> dict:
    item = await get_content_item(
        db,
        student_id=student_id,
        content_id=prompt_id,
        content_type=CONTENT_TYPE,
        skill=LanguageSkill.writing,
        level_skill=LanguageSkill.writing,
    )
    if not item or not _is_visible_to_student(item, student_id=student_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise is not available")
    prog = await _writing_progress_map(db, student_id=student_id, ids=[item.id])
    language = await get_default_language(db)
    grammar_ctx = await build_skill_grammar_context(
        db,
        student_id=student_id,
        language_id=language.id,
        source_skill=GrammarEvidenceSourceSkill.writing,
    )
    return _prompt_out(item, prog.get(item.id), grammar_ctx=grammar_ctx)


async def _record_writing_component(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    component_code: str,
    score_percent: float,
) -> bool:
    if not component_code:
        return False
    try:
        cm = await LanguageLearnerModelService(db).process_event(
            LearningEvent(
                student_id=student_id,
                language_id=language_id,
                component_code=component_code,
                correct=float(score_percent) >= 60.0,
                source="writing",
                response_quality=max(0, min(5, round(float(score_percent) / 20.0))),
            ),
            commit=False,
            sync_cefr=False,
        )
        return cm is not None
    except Exception:
        return False


async def submit_writing(
    db: AsyncSession,
    *,
    student_id: int,
    prompt_id: int,
    response_text: str,
) -> dict:
    item = await get_content_item(
        db,
        student_id=student_id,
        content_id=prompt_id,
        content_type=CONTENT_TYPE,
        skill=LanguageSkill.writing,
        level_skill=LanguageSkill.writing,
    )
    if not item or not _is_visible_to_student(item, student_id=student_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise is not available")
    body = item.body_json or {}
    metadata = _prompt_metadata(item)
    level = _level_str(item.level)
    min_words = int(body.get("min_words") or 20)
    min_sentences = int(body.get("min_sentences") or 2)
    text, wc, sc = validate_writing_submission(
        response_text,
        min_words=min_words,
        min_sentences=min_sentences,
    )

    language = await get_default_language(db)
    grammar_ctx = await build_skill_grammar_context(
        db,
        student_id=student_id,
        language_id=language.id,
        source_skill=GrammarEvidenceSourceSkill.writing,
    )

    # Real CEFR grading when available; otherwise the rule heuristic. Track which one ran.
    prompt_text = _with_grammar_writing_instruction(
        body.get("prompt") or body.get("instructions") or "",
        grammar_ctx,
    )
    ai_writing = await score_writing_ai(text=text, prompt=prompt_text)
    if ai_writing:
        score_pct, metrics = ai_writing
        scoring_version = "ai_rubric_v2"
    else:
        score_pct, metrics = score_writing({"text": text}, min_words=min_words)
        scoring_version = "rule_v1"
    criteria = _ensure_criteria(
        metrics,
        score_percent=float(score_pct),
        word_count=wc,
        min_words=min_words,
        sentence_count=sc,
        min_sentences=min_sentences,
    )
    metrics["criteria"] = criteria
    metrics["sentence_count"] = sc
    metrics["min_sentences"] = min_sentences
    metrics["target_component"] = metadata["target_component"]
    metrics["target_focus"] = metadata["target_focus"]
    metrics["task_type"] = metadata["task_type"]
    metrics["topic"] = metadata["topic"]
    threshold = pass_threshold_for_item(item)
    meets_threshold = score_pct >= threshold and wc >= min_words and sc >= min_sentences
    next_focus = _next_focus_from_metrics(
        metrics,
        level=level,
        target_component=metadata["target_component"],
    )
    metrics["next_focus"] = next_focus
    metrics["feedback"] = _criterion_feedback(metrics, float(score_pct))
    metrics["mini_lesson"] = metadata["mini_lesson"]
    metrics["rewrite_prompt"] = _rewrite_prompt(next_focus, metadata)
    component_code = str(next_focus.get("component_code") or metadata["target_component"])
    metrics["component_practice_score"] = _component_score(component_code, criteria, default_score=float(score_pct))

    result = await db.execute(
        select(LanguageWritingProgress).where(
            LanguageWritingProgress.student_id == student_id,
            LanguageWritingProgress.content_item_id == prompt_id,
        )
    )
    progress = result.scalar_one_or_none()
    already_completed = bool(progress.completed_at) if progress else False
    previous_metrics = progress.metrics_json if progress and progress.metrics_json else {}
    submitted_at = datetime.now(timezone.utc)
    attempts, attempt_number, previous_score, improvement = _attempt_history(
        previous_metrics=previous_metrics,
        submitted_at=submitted_at,
        text=text,
        score_percent=float(score_pct),
        word_count=wc,
        sentence_count=sc,
        criteria=criteria,
        feedback=metrics["feedback"],
    )
    completed = already_completed or (meets_threshold and (attempt_number >= 2 or float(score_pct) >= 85.0))
    rewrite_required = not completed
    metrics["attempts"] = attempts
    metrics["attempt_number"] = attempt_number
    metrics["previous_score_percent"] = previous_score
    metrics["improvement_percent"] = improvement
    metrics["rewrite_required"] = rewrite_required
    metrics["meets_threshold"] = meets_threshold
    if not progress:
        progress = LanguageWritingProgress(student_id=student_id, content_item_id=prompt_id, submitted_text=text)
        db.add(progress)
    progress.submitted_text = text
    progress.word_count = wc
    progress.score_percent = float(score_pct)
    progress.metrics_json = metrics
    progress.ai_evaluation_json = metrics if scoring_version == "ai_rubric_v2" else None
    progress.level_estimate = percent_to_level(float(score_pct))
    progress.scoring_version = scoring_version
    progress.submitted_at = submitted_at
    if completed and not progress.completed_at:
        progress.completed_at = submitted_at
    await db.flush()

    event = "writing_completed" if completed else "writing_submitted"
    await record_activity(
        db,
        student_id=student_id,
        language_id=language.id,
        event_type=event,
        skill=LanguageSkill.writing,
        payload_json={
            "content_item_id": prompt_id,
            "title": item.title,
            "score_percent": score_pct,
            "passed": completed,
            "meets_threshold": meets_threshold,
            "attempt_number": attempt_number,
        },
    )
    await refresh_language_analytics(db, student_id=student_id, language_id=language.id)
    await record_lesson_result(
        db, student_id=student_id, language_id=language.id, skill=LanguageSkill.writing, score_percent=float(score_pct)
    )
    await credit_skill_objectives(
        db, student_id=student_id, language_id=language.id, skill=LanguageSkill.writing,
        score_percent=float(score_pct), passed=completed,
    )
    if completed:
        from app.services.language_xp_service import award_language_xp

        await award_language_xp(db, student_id=student_id, language_id=language.id, activity="writing", key=f"writing:{prompt_id}")
    recorded_component = await _record_writing_component(
        db,
        student_id=student_id,
        language_id=language.id,
        component_code=component_code,
        score_percent=float(metrics.get("component_practice_score") or score_pct),
    )
    if not recorded_component:
        await record_scored_practice(
            db, student_id=student_id, language_id=language.id, skill=LanguageSkill.writing,
            level=item.level, score_percent=float(score_pct), source="writing",
        )
    if completed:
        try:
            await complete_current_skill_activity_async(
                db,
                student_id=student_id,
                language_id=language.id,
                skill=GrammarEvidenceSourceSkill.writing,
                score=float(score_pct),
                activity_id=f"writing:{prompt_id}:{attempt_number}",
                activity_type="writing",
                lesson_id=str(prompt_id),
                context=f"writing:{prompt_id}",
                observation_id=f"ev_writing_{prompt_id}_{attempt_number}",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("grammar writing evidence completion failed: %s", exc)
    return {
        "prompt_id": prompt_id,
        "score_percent": float(score_pct),
        "passed": completed,
        "meets_threshold": meets_threshold,
        "word_count": wc,
        "sentence_count": sc,
        "completed_at": progress.completed_at,
        "status": "completed" if progress.completed_at else ("rewrite_required" if rewrite_required else "in_progress"),
        "criteria": criteria,
        "flags": metrics.get("flags") or {},
        "feedback": metrics.get("feedback") or "",
        "next_focus": next_focus,
        "target_component": metadata["target_component"],
        "target_focus": metadata["target_focus"],
        "scoring_version": scoring_version,
        "attempt_number": attempt_number,
        "previous_score_percent": previous_score,
        "improvement_percent": improvement,
        "rewrite_required": rewrite_required,
        "rewrite_prompt": metrics["rewrite_prompt"],
        "mini_lesson": metrics["mini_lesson"],
    }
