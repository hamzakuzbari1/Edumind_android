"""Types for Writing Curriculum & Arc (W0/W2)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_writing.enums import (
    ContextComplexity,
    ExpectedWritingOutput,
    LexisCategory,
    OfficialWritingCEFR,
    WritingArc,
    WritingCoachPersonality,
    WritingCoachTone,
    WritingFeedbackStyle,
    WritingGoal,
    WritingMissionStyle,
    WritingPromotionStyle,
    WritingRevisionStyle,
)
from app.services.language_writing_knowledge_chain.types import WritingKnowledgeChainNode
from app.services.language_writing_topic_universe.types import TopicSelectionContext


@dataclass(frozen=True, slots=True)
class WritingArcStageDefinition:
    """Layer 2 — macro curriculum arc stage."""

    arc_stage: WritingArc
    label: str
    description: str
    allowed_task_types: tuple[str, ...]
    allowed_genres: tuple[str, ...]
    min_word_count: int
    max_word_count: int
    min_cefr: OfficialWritingCEFR
    organization_scaffold_level: int  # 0=none, 3=full outline


@dataclass(frozen=True, slots=True)
class WritingCoachDefaults:
    """Default coach configuration for a learning goal."""

    personality: WritingCoachPersonality
    feedback_style: WritingFeedbackStyle
    revision_strictness: float = 0.5  # 0=gentle, 1=strict gate before complete
    max_revision_turns_hint: int | None = None  # None = coach decides via ready_to_complete


@dataclass(frozen=True, slots=True)
class WritingGoalProfile:
    """Complete writing goal profile — influences selection, mission, coach, WPA (W2.1 frozen)."""

    goal: WritingGoal
    label: str
    preferred_task_types: tuple[str, ...]
    preferred_genres: tuple[str, ...]
    preferred_mission_style: WritingMissionStyle
    preferred_writing_outputs: tuple[ExpectedWritingOutput, ...]
    preferred_vocabulary_categories: tuple[LexisCategory, ...]
    preferred_grammar_priorities: tuple[str, ...]
    preferred_coach_tone: WritingCoachTone
    preferred_revision_style: WritingRevisionStyle
    preferred_promotion_style: WritingPromotionStyle
    register: str
    vocabulary_style: str
    feedback_emphasis: tuple[str, ...]
    coach_defaults: WritingCoachDefaults
    feedback_style: WritingFeedbackStyle
    coach_personality_id: str
    preferred_topic_ids: tuple[str, ...] = ()
    knowledge_chain_preferences: tuple[str, ...] = ()
    style_directives: tuple[str, ...] = ()
    word_target_multiplier: float = 1.0
    time_limit_minutes: int | None = None
    vocabulary_category_weights: dict[str, float] = field(default_factory=dict)
    wpa_task_bundle_key: str = ""

    @property
    def promotion_style(self) -> WritingPromotionStyle:
        """Alias retained for W2.0 callers."""
        return self.preferred_promotion_style

    @property
    def grammar_focus_priorities(self) -> tuple[str, ...]:
        """Alias retained for W2.0 callers."""
        return self.preferred_grammar_priorities


@dataclass(frozen=True, slots=True)
class CurriculumSelectionScore:
    """Blended selection score breakdown."""

    total: float
    cefr_fit: float = 0.0
    arc_fit: float = 0.0
    chain_progression: float = 0.0
    goal_alignment: float = 0.0
    complexity_fit: float = 0.0
    lexis_balance: float = 0.0
    grammar_needs: float = 0.0
    anti_repetition: float = 0.0
    contributions: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WritingCurriculumRecommendation:
    """Output of curriculum selection engine (contract only — W0)."""

    chain_node: WritingKnowledgeChainNode
    topic_context: TopicSelectionContext
    arc_stage: WritingArc
    goal: WritingGoal
    context_complexity: ContextComplexity
    score: CurriculumSelectionScore
    selection_reason: str

    def to_metadata(self) -> dict[str, object]:
        return {
            "chain_id": self.chain_node.chain_id,
            "chain_node_id": self.chain_node.node_id,
            "topic_id": self.chain_node.topic_id.value,
            "arc_stage": self.arc_stage.value,
            "learning_goal": self.goal.value,
            "context_complexity": int(self.context_complexity),
            "selection_reason": self.selection_reason,
            "recommendation_score": round(self.score.total, 4),
            "score_breakdown": {
                k: round(v, 4)
                for k, v in {
                    "cefr_fit": self.score.cefr_fit,
                    "arc_fit": self.score.arc_fit,
                    "chain_progression": self.score.chain_progression,
                    "goal_alignment": self.score.goal_alignment,
                    "complexity_fit": self.score.complexity_fit,
                    "lexis_balance": self.score.lexis_balance,
                    "grammar_needs": self.score.grammar_needs,
                    "anti_repetition": self.score.anti_repetition,
                }.items()
            },
        }
