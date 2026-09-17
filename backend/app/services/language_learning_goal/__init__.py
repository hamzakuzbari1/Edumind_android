"""Goal-Aware Learning Engine — listening adaptation by learner goal (Phase 3.1)."""

from app.services.language_learning_goal.engine import GOAL_KEY, recommend_goal_aware_listening_plan
from app.services.language_learning_goal.prompt import build_learning_goal_prompt_block
from app.services.language_learning_goal.profiles import all_profiles, profile_for_goal
from app.services.language_learning_goal.resolver import (
    enrich_topics_for_goal,
    match_learning_goal,
    parse_learning_goal_from_context,
    resolve_learning_goal,
)
from app.services.language_learning_goal.scoring import DEFAULT_GOAL_INFLUENCE, GOAL_WEIGHTS, blend_scores
from app.services.language_learning_goal.types import (
    GoalAlignmentScore,
    GoalAwareRecommendation,
    LearningGoal,
    LearningGoalProfile,
)

__all__ = (
    "GOAL_KEY",
    "DEFAULT_GOAL_INFLUENCE",
    "GOAL_WEIGHTS",
    "GoalAlignmentScore",
    "GoalAwareRecommendation",
    "LearningGoal",
    "LearningGoalProfile",
    "all_profiles",
    "blend_scores",
    "build_learning_goal_prompt_block",
    "enrich_topics_for_goal",
    "match_learning_goal",
    "parse_learning_goal_from_context",
    "profile_for_goal",
    "recommend_goal_aware_listening_plan",
    "resolve_learning_goal",
)
