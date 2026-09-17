"""Backend-owned PackageConstraints — sole educational input to the package author."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.services.language_educational_package.material_kinds import InputMaterialKind
from app.services.language_educational_package.question_ladder import (
    QuestionLadderPolicy,
    default_ladder_policy_for_cefr,
)

ELP_CONSTRAINTS_SCHEMA_VERSION = "2.4.0"


@dataclass(frozen=True, slots=True)
class TeachingBlockSpec:
    block_id: str
    kind: str
    target_skill_ids: tuple[str, ...] = ()
    max_len: int = 400

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_id": self.block_id,
            "kind": self.kind,
            "target_skill_ids": list(self.target_skill_ids),
            "max_len": self.max_len,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> TeachingBlockSpec:
        skills = raw.get("target_skill_ids") or []
        return TeachingBlockSpec(
            block_id=str(raw.get("block_id") or ""),
            kind=str(raw.get("kind") or "explanation"),
            target_skill_ids=tuple(str(s) for s in skills) if isinstance(skills, list) else (),
            max_len=int(raw.get("max_len") or 400),
        )


@dataclass(frozen=True, slots=True)
class EvidenceSlotSpec:
    step_id: str
    evidence_role: str
    ladder_band: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> EvidenceSlotSpec:
        return EvidenceSlotSpec(
            step_id=str(raw.get("step_id") or ""),
            evidence_role=str(raw.get("evidence_role") or "none"),
            ladder_band=str(raw.get("ladder_band") or "literal"),
        )


@dataclass(frozen=True, slots=True)
class ReflectionRequirements:
    prompt_count: int = 2

    def to_dict(self) -> dict[str, Any]:
        return {"prompt_count": self.prompt_count}

    @staticmethod
    def from_dict(raw: dict[str, Any] | None) -> ReflectionRequirements:
        if not isinstance(raw, dict):
            return ReflectionRequirements()
        return ReflectionRequirements(prompt_count=max(1, int(raw.get("prompt_count") or 2)))


@dataclass(frozen=True, slots=True)
class PackageConstraints:
    """Sole educational input to Claude author — never invent curriculum here."""

    skill: str
    official_cefr: str
    learning_stage: int
    mission_id: str
    mission_kind: str
    execution_mode: str
    evidence_intent: str
    blueprint_id: str
    blueprint_hash: str
    learning_focus: str
    objectives: tuple[str, ...]
    vocabulary_ids: tuple[str, ...]
    vocabulary_surface_forms: tuple[str, ...]
    grammar_topic_ids: tuple[str, ...]
    teaching_block_specs: tuple[TeachingBlockSpec, ...]
    weak_skill_labels: tuple[str, ...]
    difficulty: str
    scenario_type: str
    input_material_kind: InputMaterialKind
    lesson_length_band: str
    question_ladder_policy: QuestionLadderPolicy
    evidence_slot_plan: tuple[EvidenceSlotSpec, ...]
    reflection_requirements: ReflectionRequirements
    forbidden_behaviors: tuple[str, ...]
    locale: str = "en"
    mini_practice_task_id: str = ""
    schema_version: str = ELP_CONSTRAINTS_SCHEMA_VERSION
    # Curriculum Engine V2 — richer educational intelligence (optional for v1 payloads)
    vocabulary_targets: tuple[dict[str, Any], ...] = ()
    educational_objectives: tuple[dict[str, Any], ...] = ()
    grammar_targets: tuple[dict[str, Any], ...] = ()
    lesson_authoring_policy: dict[str, Any] | None = None
    lexical_recycling_policy: dict[str, Any] | None = None
    story_complexity_policy: dict[str, Any] | None = None
    curriculum_engine_version: str = ""
    # Story-world ownership (backend) — Claude authors story text inside this world.
    story_world: str = ""
    communicative_goal: str = ""
    character_hints: tuple[str, ...] = ()
    story_title_hint: str = ""
    authoring_day: str = ""
    daily_story_key: str = ""
    daily_story_seed: str = ""
    case_category: str = ""
    case_archetype: str = ""
    stakeholder_hints: tuple[str, ...] = ()
    # M8 — experience overlays only (never curriculum ownership)
    personalization: dict[str, Any] | None = None
    personalization_engine_version: str = ""
    # M9 — Curriculum Progression Graph placement
    curriculum_progression: dict[str, Any] | None = None
    progression_node_id: str = ""
    progression_case_id: str = ""
    progression_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "schema_version": self.schema_version,
            "skill": self.skill,
            "official_cefr": self.official_cefr.upper(),
            "learning_stage": self.learning_stage,
            "mission_id": self.mission_id,
            "mission_kind": self.mission_kind,
            "execution_mode": self.execution_mode,
            "evidence_intent": self.evidence_intent,
            "blueprint_id": self.blueprint_id,
            "blueprint_hash": self.blueprint_hash,
            "learning_focus": self.learning_focus,
            "objectives": list(self.objectives),
            "vocabulary_ids": list(self.vocabulary_ids),
            "vocabulary_surface_forms": list(self.vocabulary_surface_forms),
            "grammar_topic_ids": list(self.grammar_topic_ids),
            "teaching_block_specs": [b.to_dict() for b in self.teaching_block_specs],
            "weak_skill_labels": list(self.weak_skill_labels),
            "difficulty": self.difficulty,
            "scenario_type": self.scenario_type,
            "input_material_kind": self.input_material_kind.value,
            "lesson_length_band": self.lesson_length_band,
            "question_ladder_policy": self.question_ladder_policy.to_dict(),
            "evidence_slot_plan": [s.to_dict() for s in self.evidence_slot_plan],
            "reflection_requirements": self.reflection_requirements.to_dict(),
            "forbidden_behaviors": list(self.forbidden_behaviors),
            "locale": self.locale,
            "mini_practice_task_id": self.mini_practice_task_id,
            "vocabulary_targets": [dict(v) for v in self.vocabulary_targets],
            "educational_objectives": [dict(o) for o in self.educational_objectives],
            "grammar_targets": [dict(g) for g in self.grammar_targets],
            "story_world": self.story_world,
            "communicative_goal": self.communicative_goal,
            "character_hints": list(self.character_hints),
            "story_title_hint": self.story_title_hint,
            "authoring_day": self.authoring_day,
            "daily_story_key": self.daily_story_key,
            "daily_story_seed": self.daily_story_seed,
            "case_category": self.case_category,
            "case_archetype": self.case_archetype,
            "stakeholder_hints": list(self.stakeholder_hints),
            "progression_node_id": self.progression_node_id,
            "progression_case_id": self.progression_case_id,
            "progression_action": self.progression_action,
        }
        if self.lesson_authoring_policy:
            data["lesson_authoring_policy"] = dict(self.lesson_authoring_policy)
        if self.lexical_recycling_policy:
            data["lexical_recycling_policy"] = dict(self.lexical_recycling_policy)
        if self.story_complexity_policy:
            data["story_complexity_policy"] = dict(self.story_complexity_policy)
        if self.curriculum_engine_version:
            data["curriculum_engine_version"] = self.curriculum_engine_version
        if self.personalization:
            data["personalization"] = dict(self.personalization)
        if self.personalization_engine_version:
            data["personalization_engine_version"] = self.personalization_engine_version
        if self.curriculum_progression:
            data["curriculum_progression"] = dict(self.curriculum_progression)
        return data

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> PackageConstraints:
        if not isinstance(raw, dict):
            raise ValueError("PackageConstraints requires a dict")
        cefr = str(raw.get("official_cefr") or "A2").upper()
        kind_raw = str(raw.get("input_material_kind") or "story")
        try:
            kind = InputMaterialKind(kind_raw)
        except ValueError:
            kind = InputMaterialKind.custom
        blocks_raw = raw.get("teaching_block_specs") or []
        blocks = tuple(
            TeachingBlockSpec.from_dict(b)
            for b in blocks_raw
            if isinstance(b, dict) and str(b.get("block_id") or "")
        )
        slots_raw = raw.get("evidence_slot_plan") or []
        slots = tuple(
            EvidenceSlotSpec.from_dict(s) for s in slots_raw if isinstance(s, dict)
        )
        vocab_ids = tuple(str(x) for x in (raw.get("vocabulary_ids") or []) if x)
        surfaces = tuple(str(x) for x in (raw.get("vocabulary_surface_forms") or []) if x)
        if len(surfaces) < len(vocab_ids):
            surfaces = surfaces + tuple(vocab_ids[len(surfaces) :])
        vocab_targets_raw = raw.get("vocabulary_targets") or []
        vocab_targets = tuple(
            dict(v) for v in vocab_targets_raw if isinstance(v, dict) and v.get("vocabulary_id")
        )
        edu_obj_raw = raw.get("educational_objectives") or []
        edu_objectives = tuple(dict(o) for o in edu_obj_raw if isinstance(o, dict) and o.get("text"))
        grammar_targets_raw = raw.get("grammar_targets") or []
        grammar_targets = tuple(
            dict(g) for g in grammar_targets_raw if isinstance(g, dict) and g.get("grammar_topic_id")
        )
        lesson_policy = (
            dict(raw["lesson_authoring_policy"])
            if isinstance(raw.get("lesson_authoring_policy"), dict)
            else None
        )
        recycle_policy = (
            dict(raw["lexical_recycling_policy"])
            if isinstance(raw.get("lexical_recycling_policy"), dict)
            else None
        )
        complexity_policy = (
            dict(raw["story_complexity_policy"])
            if isinstance(raw.get("story_complexity_policy"), dict)
            else None
        )
        return PackageConstraints(
            skill=str(raw.get("skill") or "speaking"),
            official_cefr=cefr,
            learning_stage=int(raw.get("learning_stage") or 1),
            mission_id=str(raw.get("mission_id") or ""),
            mission_kind=str(raw.get("mission_kind") or "teaching"),
            execution_mode=str(raw.get("execution_mode") or "study"),
            evidence_intent=str(raw.get("evidence_intent") or "none"),
            blueprint_id=str(raw.get("blueprint_id") or ""),
            blueprint_hash=str(raw.get("blueprint_hash") or ""),
            learning_focus=str(raw.get("learning_focus") or ""),
            objectives=tuple(str(x) for x in (raw.get("objectives") or []) if x),
            vocabulary_ids=vocab_ids,
            vocabulary_surface_forms=surfaces[: len(vocab_ids)] if vocab_ids else surfaces,
            grammar_topic_ids=tuple(str(x) for x in (raw.get("grammar_topic_ids") or []) if x),
            teaching_block_specs=blocks,
            weak_skill_labels=tuple(str(x) for x in (raw.get("weak_skill_labels") or []) if x),
            difficulty=str(raw.get("difficulty") or "standard"),
            scenario_type=str(raw.get("scenario_type") or "general"),
            input_material_kind=kind,
            lesson_length_band=str(raw.get("lesson_length_band") or "standard"),
            question_ladder_policy=QuestionLadderPolicy.from_dict(
                raw.get("question_ladder_policy")  # type: ignore[arg-type]
                if isinstance(raw.get("question_ladder_policy"), dict)
                else default_ladder_policy_for_cefr(cefr).to_dict()
            ),
            evidence_slot_plan=slots,
            reflection_requirements=ReflectionRequirements.from_dict(
                raw.get("reflection_requirements")  # type: ignore[arg-type]
            ),
            forbidden_behaviors=tuple(
                str(x) for x in (raw.get("forbidden_behaviors") or [
                    "no_grammar_lecture",
                    "no_promotion_talk",
                    "no_cefr_claims",
                ])
            ),
            locale=str(raw.get("locale") or "en"),
            mini_practice_task_id=str(raw.get("mini_practice_task_id") or ""),
            schema_version=str(raw.get("schema_version") or ELP_CONSTRAINTS_SCHEMA_VERSION),
            vocabulary_targets=vocab_targets,
            educational_objectives=edu_objectives,
            grammar_targets=grammar_targets,
            lesson_authoring_policy=lesson_policy,
            lexical_recycling_policy=recycle_policy,
            story_complexity_policy=complexity_policy,
            curriculum_engine_version=str(raw.get("curriculum_engine_version") or ""),
            story_world=str(raw.get("story_world") or ""),
            communicative_goal=str(raw.get("communicative_goal") or ""),
            character_hints=tuple(
                str(x) for x in (raw.get("character_hints") or []) if str(x).strip()
            ),
            story_title_hint=str(raw.get("story_title_hint") or ""),
            authoring_day=str(raw.get("authoring_day") or ""),
            daily_story_key=str(raw.get("daily_story_key") or ""),
            daily_story_seed=str(raw.get("daily_story_seed") or ""),
            case_category=str(
                raw.get("case_category")
                or (
                    (raw.get("story_complexity_policy") or {}).get("case_category")
                    if isinstance(raw.get("story_complexity_policy"), dict)
                    else ""
                )
                or ""
            ),
            case_archetype=str(
                raw.get("case_archetype")
                or (
                    (raw.get("story_complexity_policy") or {}).get("case_archetype")
                    if isinstance(raw.get("story_complexity_policy"), dict)
                    else ""
                )
                or ""
            ),
            stakeholder_hints=tuple(
                str(x) for x in (raw.get("stakeholder_hints") or []) if str(x).strip()
            ),
            personalization=(
                dict(raw["personalization"])
                if isinstance(raw.get("personalization"), dict)
                else None
            ),
            personalization_engine_version=str(
                raw.get("personalization_engine_version") or ""
            ),
            curriculum_progression=(
                dict(raw["curriculum_progression"])
                if isinstance(raw.get("curriculum_progression"), dict)
                else None
            ),
            progression_node_id=str(raw.get("progression_node_id") or ""),
            progression_case_id=str(raw.get("progression_case_id") or ""),
            progression_action=str(raw.get("progression_action") or ""),
        )
