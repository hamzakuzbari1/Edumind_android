"""CEFR-adaptive Story / Educational Case Complexity Policy — Curriculum Engine owned."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from app.services.language_speaking_curriculum_engine.case_taxonomy import (
    case_archetype_for_cefr,
    select_case_category,
)


@dataclass(frozen=True, slots=True)
class StoryComplexityPolicy:
    """Backend-owned Educational Case difficulty band for one CEFR level."""

    cefr: str
    min_words: int
    max_words: int
    paragraph_count_min: int
    paragraph_count_max: int
    sentence_complexity: str
    max_sentence_length: int
    characters_min: int
    characters_max: int
    story_events_min: int
    story_events_max: int
    conflict_depth: str
    decision_points: int
    twists: int
    timeline_complexity: str
    emotional_depth: str
    reading_complexity: str
    required_grammar_topic_count: int
    required_vocabulary_reuse: int
    reasoning_level: str
    reflection_depth: int
    discussion_depth: str
    # M7 — Educational Case sophistication (not just length)
    case_category: str = "daily_life"
    case_archetype: str = "simple_daily_one_problem_one_solution"
    decision_complexity: str = "one_obvious_solution"
    ethical_complexity: str = "none"
    social_complexity: str = "dyad"
    emotional_complexity: str = "basic"
    ambiguity_level: str = "low"
    viewpoint_count: int = 1
    stakeholder_count: int = 2
    possible_solution_count: int = 1
    ending_type: str = "open_obvious"
    locations_max: int = 1
    allow_nested_clauses: bool = False
    allow_figurative_language: bool = False
    ambiguous_ending: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "cefr": self.cefr.upper(),
            "min_words": self.min_words,
            "max_words": self.max_words,
            "paragraph_count_min": self.paragraph_count_min,
            "paragraph_count_max": self.paragraph_count_max,
            "paragraph_count": self.paragraph_count_min,
            "sentence_complexity": self.sentence_complexity,
            "max_sentence_length": self.max_sentence_length,
            "characters_min": self.characters_min,
            "characters_max": self.characters_max,
            "story_events_min": self.story_events_min,
            "story_events_max": self.story_events_max,
            "story_events": self.story_events_min,
            "conflict_depth": self.conflict_depth,
            "decision_points": self.decision_points,
            "twists": self.twists,
            "timeline_complexity": self.timeline_complexity,
            "emotional_depth": self.emotional_depth,
            "reading_complexity": self.reading_complexity,
            "required_grammar_topic_count": self.required_grammar_topic_count,
            "required_vocabulary_reuse": self.required_vocabulary_reuse,
            "reasoning_level": self.reasoning_level,
            "reflection_depth": self.reflection_depth,
            "discussion_depth": self.discussion_depth,
            "case_category": self.case_category,
            "case_archetype": self.case_archetype,
            "decision_complexity": self.decision_complexity,
            "ethical_complexity": self.ethical_complexity,
            "social_complexity": self.social_complexity,
            "emotional_complexity": self.emotional_complexity,
            "ambiguity_level": self.ambiguity_level,
            "viewpoint_count": self.viewpoint_count,
            "stakeholder_count": self.stakeholder_count,
            "possible_solution_count": self.possible_solution_count,
            "ending_type": self.ending_type,
            "locations_max": self.locations_max,
            "allow_nested_clauses": self.allow_nested_clauses,
            "allow_figurative_language": self.allow_figurative_language,
            "ambiguous_ending": self.ambiguous_ending,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any] | None) -> StoryComplexityPolicy | None:
        if not isinstance(raw, dict):
            return None
        events = int(raw.get("story_events_min") or raw.get("story_events") or 3)
        paras = int(raw.get("paragraph_count_min") or raw.get("paragraph_count") or 3)
        return StoryComplexityPolicy(
            cefr=str(raw.get("cefr") or "A2").upper(),
            min_words=int(raw.get("min_words") or 90),
            max_words=int(raw.get("max_words") or 220),
            paragraph_count_min=paras,
            paragraph_count_max=int(raw.get("paragraph_count_max") or max(paras, paras + 2)),
            sentence_complexity=str(raw.get("sentence_complexity") or "simple"),
            max_sentence_length=int(raw.get("max_sentence_length") or 14),
            characters_min=int(raw.get("characters_min") or 2),
            characters_max=int(raw.get("characters_max") or 3),
            story_events_min=events,
            story_events_max=int(raw.get("story_events_max") or max(events, events + 2)),
            conflict_depth=str(raw.get("conflict_depth") or "simple"),
            decision_points=int(raw.get("decision_points") or 1),
            twists=int(raw.get("twists") or 0),
            timeline_complexity=str(raw.get("timeline_complexity") or "single_episode"),
            emotional_depth=str(raw.get("emotional_depth") or "light"),
            reading_complexity=str(raw.get("reading_complexity") or "basic"),
            required_grammar_topic_count=int(raw.get("required_grammar_topic_count") or 1),
            required_vocabulary_reuse=int(raw.get("required_vocabulary_reuse") or 2),
            reasoning_level=str(raw.get("reasoning_level") or "basic"),
            reflection_depth=int(raw.get("reflection_depth") or 2),
            discussion_depth=str(raw.get("discussion_depth") or "literal_plus"),
            case_category=str(raw.get("case_category") or "daily_life"),
            case_archetype=str(
                raw.get("case_archetype") or "simple_daily_one_problem_one_solution"
            ),
            decision_complexity=str(raw.get("decision_complexity") or "one_obvious_solution"),
            ethical_complexity=str(raw.get("ethical_complexity") or "none"),
            social_complexity=str(raw.get("social_complexity") or "dyad"),
            emotional_complexity=str(raw.get("emotional_complexity") or "basic"),
            ambiguity_level=str(raw.get("ambiguity_level") or "low"),
            viewpoint_count=int(raw.get("viewpoint_count") or 1),
            stakeholder_count=int(raw.get("stakeholder_count") or 2),
            possible_solution_count=int(raw.get("possible_solution_count") or 1),
            ending_type=str(raw.get("ending_type") or "open_obvious"),
            locations_max=int(raw.get("locations_max") or 1),
            allow_nested_clauses=bool(raw.get("allow_nested_clauses", False)),
            allow_figurative_language=bool(raw.get("allow_figurative_language", False)),
            ambiguous_ending=bool(raw.get("ambiguous_ending", False)),
        )


def _sophistication_for_cefr(cefr: str) -> dict[str, Any]:
    level = (cefr or "A2").upper()
    if level.startswith("C"):
        level = "C1"
    table: dict[str, dict[str, Any]] = {
        "A1": {
            "decision_complexity": "one_obvious_solution",
            "ethical_complexity": "none",
            "social_complexity": "dyad_one_location",
            "emotional_complexity": "basic_visible",
            "ambiguity_level": "very_low",
            "viewpoint_count": 1,
            "stakeholder_count": 2,
            "possible_solution_count": 1,
            "ending_type": "open_obvious_next_step",
            "discussion_depth": "literal_understanding_simple_opinion",
        },
        "A2": {
            "decision_complexity": "simple_choice_two_options",
            "ethical_complexity": "light_fairness",
            "social_complexity": "small_misunderstanding",
            "emotional_complexity": "small_emotional_reasoning",
            "ambiguity_level": "low",
            "viewpoint_count": 2,
            "stakeholder_count": 2,
            "possible_solution_count": 2,
            "ending_type": "open_simple_dilemma",
            "discussion_depth": "literal_vocab_simple_reasoning",
        },
        "B1": {
            "decision_complexity": "several_solutions_tradeoffs",
            "ethical_complexity": "personal_responsibility",
            "social_complexity": "work_or_university_pressure",
            "emotional_complexity": "mixed_motivations",
            "ambiguity_level": "moderate",
            "viewpoint_count": 3,
            "stakeholder_count": 3,
            "possible_solution_count": 3,
            "ending_type": "open_multiple_paths",
            "discussion_depth": "reasoning_comparison_alternatives",
        },
        "B2": {
            "decision_complexity": "competing_valid_options",
            "ethical_complexity": "ethical_dilemma",
            "social_complexity": "institutional_and_personal",
            "emotional_complexity": "hidden_motivations",
            "ambiguity_level": "high",
            "viewpoint_count": 4,
            "stakeholder_count": 4,
            "possible_solution_count": 4,
            "ending_type": "open_several_valid_opinions",
            "discussion_depth": "ethical_judgment_tradeoffs_evidence",
        },
        "C1": {
            "decision_complexity": "no_single_correct_answer",
            "ethical_complexity": "advanced_public_ethics",
            "social_complexity": "policy_corporate_or_legal_web",
            "emotional_complexity": "long_term_consequence_empathy",
            "ambiguity_level": "very_high",
            "viewpoint_count": 5,
            "stakeholder_count": 6,
            "possible_solution_count": 5,
            "ending_type": "ambiguous_long_term_open",
            "discussion_depth": "critical_policy_counterarguments",
        },
    }
    return dict(table.get(level) or table["A2"])


def story_complexity_policy_for_cefr(
    cefr: str,
    *,
    skill_ids: list[str] | None = None,
    learning_focus: str = "",
    scenario_type: str = "",
) -> StoryComplexityPolicy:
    """Return CEFR Educational Case complexity including case taxonomy seed."""
    level = (cefr or "A2").upper()
    category = select_case_category(
        cefr=level,
        skill_ids=skill_ids,
        learning_focus=learning_focus,
        scenario_type=scenario_type,
    )
    archetype = case_archetype_for_cefr(level)
    soph = _sophistication_for_cefr(level)

    if level == "A1":
        base = StoryComplexityPolicy(
            cefr="A1",
            min_words=90,
            max_words=150,
            paragraph_count_min=3,
            paragraph_count_max=4,
            sentence_complexity="present_simple_short",
            max_sentence_length=12,
            characters_min=2,
            characters_max=2,
            story_events_min=3,
            story_events_max=3,
            conflict_depth="one_simple_conflict",
            decision_points=1,
            twists=0,
            timeline_complexity="single_location_episode",
            emotional_depth="basic_visible_feelings",
            reading_complexity="very_easy",
            required_grammar_topic_count=1,
            required_vocabulary_reuse=2,
            reasoning_level="supported_choice",
            reflection_depth=2,
            discussion_depth=str(soph["discussion_depth"]),
            locations_max=1,
            allow_nested_clauses=False,
            allow_figurative_language=False,
            ambiguous_ending=False,
        )
    elif level == "A2":
        base = StoryComplexityPolicy(
            cefr="A2",
            min_words=130,
            max_words=220,
            paragraph_count_min=4,
            paragraph_count_max=5,
            sentence_complexity="present_and_past_with_connectors",
            max_sentence_length=16,
            characters_min=2,
            characters_max=3,
            story_events_min=4,
            story_events_max=5,
            conflict_depth="simple_dilemma",
            decision_points=1,
            twists=0,
            timeline_complexity="short_sequence",
            emotional_depth="small_emotional_reasoning",
            reading_complexity="easy",
            required_grammar_topic_count=2,
            required_vocabulary_reuse=2,
            reasoning_level="explain_why",
            reflection_depth=2,
            discussion_depth=str(soph["discussion_depth"]),
            locations_max=1,
            allow_nested_clauses=False,
            allow_figurative_language=False,
            ambiguous_ending=False,
        )
    elif level == "B1":
        base = StoryComplexityPolicy(
            cefr="B1",
            min_words=220,
            max_words=350,
            paragraph_count_min=6,
            paragraph_count_max=8,
            sentence_complexity="past_present_future_cause_effect",
            max_sentence_length=22,
            characters_min=3,
            characters_max=4,
            story_events_min=6,
            story_events_max=8,
            conflict_depth="multiple_viewpoints",
            decision_points=2,
            twists=1,
            timeline_complexity="reported_sequence",
            emotional_depth="mixed_motivations",
            reading_complexity="intermediate",
            required_grammar_topic_count=2,
            required_vocabulary_reuse=3,
            reasoning_level="justify_choice",
            reflection_depth=3,
            discussion_depth=str(soph["discussion_depth"]),
            locations_max=2,
            allow_nested_clauses=True,
            allow_figurative_language=False,
            ambiguous_ending=False,
        )
    elif level in {"B2"} or level.startswith("B2"):
        base = StoryComplexityPolicy(
            cefr="B2",
            min_words=350,
            max_words=550,
            paragraph_count_min=8,
            paragraph_count_max=10,
            sentence_complexity="mixed_grammar_complex_connectors",
            max_sentence_length=28,
            characters_min=4,
            characters_max=5,
            story_events_min=8,
            story_events_max=10,
            conflict_depth="ethical_conflict_hidden_motivations",
            decision_points=3,
            twists=2,
            timeline_complexity="multi_decision_arc",
            emotional_depth="hidden_and_conflicting_emotions",
            reading_complexity="upper_intermediate",
            required_grammar_topic_count=3,
            required_vocabulary_reuse=3,
            reasoning_level="analyze_effect",
            reflection_depth=4,
            discussion_depth=str(soph["discussion_depth"]),
            locations_max=2,
            allow_nested_clauses=True,
            allow_figurative_language=False,
            ambiguous_ending=False,
        )
    else:
        base = StoryComplexityPolicy(
            cefr="C1" if level.startswith("C") else level,
            min_words=550,
            max_words=900,
            paragraph_count_min=10,
            paragraph_count_max=15,
            sentence_complexity="advanced_embedded_clauses",
            max_sentence_length=36,
            characters_min=5,
            characters_max=7,
            story_events_min=10,
            story_events_max=15,
            conflict_depth="social_legal_ethical_ambiguity",
            decision_points=4,
            twists=3,
            timeline_complexity="non_linear_or_multi_thread",
            emotional_depth="critical_empathy_and_ambiguity",
            reading_complexity="advanced",
            required_grammar_topic_count=3,
            required_vocabulary_reuse=3,
            reasoning_level="defend_and_critique",
            reflection_depth=5,
            discussion_depth=str(soph["discussion_depth"]),
            locations_max=3,
            allow_nested_clauses=True,
            allow_figurative_language=True,
            ambiguous_ending=True,
        )

    return replace(
        base,
        case_category=category.value,
        case_archetype=archetype,
        decision_complexity=str(soph["decision_complexity"]),
        ethical_complexity=str(soph["ethical_complexity"]),
        social_complexity=str(soph["social_complexity"]),
        emotional_complexity=str(soph["emotional_complexity"]),
        ambiguity_level=str(soph["ambiguity_level"]),
        viewpoint_count=int(soph["viewpoint_count"]),
        stakeholder_count=max(int(soph["stakeholder_count"]), base.characters_min),
        possible_solution_count=int(soph["possible_solution_count"]),
        ending_type=str(soph["ending_type"]),
    )


CHARACTER_NAME_POOL: tuple[str, ...] = (
    "Sam",
    "Lee",
    "Maya",
    "Jordan",
    "Noor",
    "Omar",
    "Hana",
    "Rami",
    "Sara",
    "Diego",
    "Anna",
    "Kim",
)

INSTITUTIONAL_STAKEHOLDER_POOL: tuple[str, ...] = (
    "the manager",
    "the admissions office",
    "the clinic desk",
    "the airline desk",
    "the company board",
    "the local council",
    "the client's team",
    "the public",
)


def expand_character_hints(
    hints: list[str] | tuple[str, ...],
    policy: StoryComplexityPolicy,
) -> list[str]:
    """Ensure character_hints satisfy characters_min..characters_max."""
    out = [str(h).strip() for h in hints if str(h).strip()]
    i = 0
    while len(out) < policy.characters_min:
        candidate = CHARACTER_NAME_POOL[i % len(CHARACTER_NAME_POOL)]
        i += 1
        if candidate not in out:
            out.append(candidate)
    if len(out) > policy.characters_max:
        out = out[: policy.characters_max]
    return out


def build_stakeholder_hints(
    characters: list[str] | tuple[str, ...],
    policy: StoryComplexityPolicy,
) -> list[str]:
    """Named people + institutional stakeholders to match stakeholder_count."""
    stakeholders = [str(c).strip() for c in characters if str(c).strip()]
    i = 0
    while len(stakeholders) < policy.stakeholder_count:
        role = INSTITUTIONAL_STAKEHOLDER_POOL[i % len(INSTITUTIONAL_STAKEHOLDER_POOL)]
        i += 1
        if role not in stakeholders:
            stakeholders.append(role)
    return stakeholders[: max(policy.stakeholder_count, len(stakeholders))]
