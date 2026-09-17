"""Personalization Engine types — experience HOW; Curriculum still owns WHAT."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

PERSONALIZATION_ENGINE_VERSION = "1.0.0"

# Curriculum owns these — Personalization Engine must never mutate them.
CURRICULUM_LOCKED_KEYS: tuple[str, ...] = (
    "official_cefr",
    "learning_focus",
    "objectives",
    "educational_objectives",
    "vocabulary_ids",
    "vocabulary_surface_forms",
    "vocabulary_targets",
    "grammar_topic_ids",
    "grammar_targets",
    "difficulty",
    "case_category",
    "case_archetype",
    "story_complexity_policy",
    "lesson_authoring_policy",
    "lexical_recycling_policy",
    "question_ladder_policy",
    "learning_stage",
    "mission_id",
    "mission_kind",
    "execution_mode",
    "evidence_intent",
    "curriculum_engine_version",
    "curriculum_progression",
    "progression_node_id",
    "progression_case_id",
    "progression_action",
)


@dataclass(frozen=True, slots=True)
class StudentCaseSignals:
    """Student signals used only for Educational Case experience adaptation."""

    student_id: int = 0
    age: int | None = None
    occupation: str = ""
    future_goal: str = ""
    learning_style: str = ""
    explanation_style: str = ""
    interests: tuple[str, ...] = ()
    hobbies: tuple[str, ...] = ()
    favorite_topics: tuple[str, ...] = ()
    avoided_topics: tuple[str, ...] = ()
    weak_skill_labels: tuple[str, ...] = ()
    recent_mistake_tags: tuple[str, ...] = ()
    completed_case_titles: tuple[str, ...] = ()
    used_settings: tuple[str, ...] = ()
    used_theme_keys: tuple[str, ...] = ()
    used_emotional_themes: tuple[str, ...] = ()
    used_decision_patterns: tuple[str, ...] = ()
    culture_hint: str = ""
    locale: str = "en"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(raw: dict[str, Any] | None) -> StudentCaseSignals:
        if not isinstance(raw, dict):
            return StudentCaseSignals()
        return StudentCaseSignals(
            student_id=int(raw.get("student_id") or 0),
            age=int(raw["age"]) if raw.get("age") not in (None, "") else None,
            occupation=str(raw.get("occupation") or ""),
            future_goal=str(raw.get("future_goal") or ""),
            learning_style=str(raw.get("learning_style") or ""),
            explanation_style=str(raw.get("explanation_style") or ""),
            interests=tuple(str(x) for x in (raw.get("interests") or []) if str(x).strip()),
            hobbies=tuple(str(x) for x in (raw.get("hobbies") or []) if str(x).strip()),
            favorite_topics=tuple(
                str(x) for x in (raw.get("favorite_topics") or []) if str(x).strip()
            ),
            avoided_topics=tuple(
                str(x) for x in (raw.get("avoided_topics") or []) if str(x).strip()
            ),
            weak_skill_labels=tuple(
                str(x) for x in (raw.get("weak_skill_labels") or []) if str(x).strip()
            ),
            recent_mistake_tags=tuple(
                str(x) for x in (raw.get("recent_mistake_tags") or []) if str(x).strip()
            ),
            completed_case_titles=tuple(
                str(x) for x in (raw.get("completed_case_titles") or []) if str(x).strip()
            ),
            used_settings=tuple(
                str(x) for x in (raw.get("used_settings") or []) if str(x).strip()
            ),
            used_theme_keys=tuple(
                str(x) for x in (raw.get("used_theme_keys") or []) if str(x).strip()
            ),
            used_emotional_themes=tuple(
                str(x) for x in (raw.get("used_emotional_themes") or []) if str(x).strip()
            ),
            used_decision_patterns=tuple(
                str(x) for x in (raw.get("used_decision_patterns") or []) if str(x).strip()
            ),
            culture_hint=str(raw.get("culture_hint") or ""),
            locale=str(raw.get("locale") or "en"),
        )


@dataclass(frozen=True, slots=True)
class PersonalizationDirective:
    """Experience-only directives for Claude/template authors."""

    engine_version: str = PERSONALIZATION_ENGINE_VERSION
    profile_fingerprint: str = ""
    theme_key: str = ""
    profession_key: str = ""
    age_band: str = ""
    interest_labels: tuple[str, ...] = ()
    setting_overlay: str = ""
    story_world_overlay: str = ""
    story_title_hint: str = ""
    character_names: tuple[str, ...] = ()
    character_roles: tuple[str, ...] = ()
    cultural_style: str = ""
    emotional_framing: str = ""
    dialogue_style: str = ""
    learning_style_hint: str = ""
    discussion_interest_hooks: tuple[str, ...] = ()
    alex_notes: tuple[str, ...] = ()
    avoided_settings: tuple[str, ...] = ()
    memory_reuse_blocked: tuple[str, ...] = ()
    applied: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine_version": self.engine_version,
            "profile_fingerprint": self.profile_fingerprint,
            "theme_key": self.theme_key,
            "profession_key": self.profession_key,
            "age_band": self.age_band,
            "interest_labels": list(self.interest_labels),
            "setting_overlay": self.setting_overlay,
            "story_world_overlay": self.story_world_overlay,
            "story_title_hint": self.story_title_hint,
            "character_names": list(self.character_names),
            "character_roles": list(self.character_roles),
            "cultural_style": self.cultural_style,
            "emotional_framing": self.emotional_framing,
            "dialogue_style": self.dialogue_style,
            "learning_style_hint": self.learning_style_hint,
            "discussion_interest_hooks": list(self.discussion_interest_hooks),
            "alex_notes": list(self.alex_notes),
            "avoided_settings": list(self.avoided_settings),
            "memory_reuse_blocked": list(self.memory_reuse_blocked),
            "applied": self.applied,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any] | None) -> PersonalizationDirective:
        if not isinstance(raw, dict):
            return PersonalizationDirective()
        return PersonalizationDirective(
            engine_version=str(raw.get("engine_version") or PERSONALIZATION_ENGINE_VERSION),
            profile_fingerprint=str(raw.get("profile_fingerprint") or ""),
            theme_key=str(raw.get("theme_key") or ""),
            profession_key=str(raw.get("profession_key") or ""),
            age_band=str(raw.get("age_band") or ""),
            interest_labels=tuple(
                str(x) for x in (raw.get("interest_labels") or []) if str(x).strip()
            ),
            setting_overlay=str(raw.get("setting_overlay") or ""),
            story_world_overlay=str(raw.get("story_world_overlay") or ""),
            story_title_hint=str(raw.get("story_title_hint") or ""),
            character_names=tuple(
                str(x) for x in (raw.get("character_names") or []) if str(x).strip()
            ),
            character_roles=tuple(
                str(x) for x in (raw.get("character_roles") or []) if str(x).strip()
            ),
            cultural_style=str(raw.get("cultural_style") or ""),
            emotional_framing=str(raw.get("emotional_framing") or ""),
            dialogue_style=str(raw.get("dialogue_style") or ""),
            learning_style_hint=str(raw.get("learning_style_hint") or ""),
            discussion_interest_hooks=tuple(
                str(x) for x in (raw.get("discussion_interest_hooks") or []) if str(x).strip()
            ),
            alex_notes=tuple(str(x) for x in (raw.get("alex_notes") or []) if str(x).strip()),
            avoided_settings=tuple(
                str(x) for x in (raw.get("avoided_settings") or []) if str(x).strip()
            ),
            memory_reuse_blocked=tuple(
                str(x) for x in (raw.get("memory_reuse_blocked") or []) if str(x).strip()
            ),
            applied=bool(raw.get("applied")),
        )


@dataclass(slots=True)
class CaseMemoryLedger:
    """Longitudinal Educational Case memory — diversify without changing curriculum."""

    schema_version: str = "1.0.0"
    used_theme_keys: list[str] = field(default_factory=list)
    used_settings: list[str] = field(default_factory=list)
    used_case_titles: list[str] = field(default_factory=list)
    used_categories: list[str] = field(default_factory=list)
    used_archetypes: list[str] = field(default_factory=list)
    used_emotional_themes: list[str] = field(default_factory=list)
    used_decision_patterns: list[str] = field(default_factory=list)
    used_stakeholder_patterns: list[str] = field(default_factory=list)
    used_vocabulary_worlds: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "used_theme_keys": list(self.used_theme_keys)[-40:],
            "used_settings": list(self.used_settings)[-40:],
            "used_case_titles": list(self.used_case_titles)[-40:],
            "used_categories": list(self.used_categories)[-40:],
            "used_archetypes": list(self.used_archetypes)[-40:],
            "used_emotional_themes": list(self.used_emotional_themes)[-40:],
            "used_decision_patterns": list(self.used_decision_patterns)[-40:],
            "used_stakeholder_patterns": list(self.used_stakeholder_patterns)[-40:],
            "used_vocabulary_worlds": list(self.used_vocabulary_worlds)[-40:],
        }

    @staticmethod
    def from_dict(raw: dict[str, Any] | None) -> CaseMemoryLedger:
        if not isinstance(raw, dict):
            return CaseMemoryLedger()

        def _list(key: str) -> list[str]:
            return [str(x) for x in (raw.get(key) or []) if str(x).strip()]

        return CaseMemoryLedger(
            schema_version=str(raw.get("schema_version") or "1.0.0"),
            used_theme_keys=_list("used_theme_keys"),
            used_settings=_list("used_settings"),
            used_case_titles=_list("used_case_titles"),
            used_categories=_list("used_categories"),
            used_archetypes=_list("used_archetypes"),
            used_emotional_themes=_list("used_emotional_themes"),
            used_decision_patterns=_list("used_decision_patterns"),
            used_stakeholder_patterns=_list("used_stakeholder_patterns"),
            used_vocabulary_worlds=_list("used_vocabulary_worlds"),
        )
