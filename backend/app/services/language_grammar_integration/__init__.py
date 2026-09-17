"""Grammar Integration (G3.1) — sole facade for Planner + skill resolve_targets.

RESPONSIBILITY: GrammarLearningSnapshot assembly, completed-topic sync,
and resolve_targets. Planner never queries engines directly.
"""

from __future__ import annotations

from app.services.language_grammar_integration.service import (
    GrammarIntegrationService,
    build_learning_snapshot,
    build_learning_snapshot_async,
    build_learning_snapshot_for_planner,
    resolve_targets,
    resolve_targets_from_snapshot,
    sync_completed_topics,
    sync_completed_topics_async,
)
from app.services.language_grammar_integration.types import (
    GRAMMAR_LEARNING_SNAPSHOT_VERSION,
    GrammarCompletedSyncResult,
    GrammarIntegrationPort,
    GrammarLearningSnapshot,
    GrammarMasteryPlanSummary,
    GrammarResolveTargetsRequest,
    GrammarResolveTargetsResult,
    GrammarReviewPlanItem,
    GrammarTopicPlanMeta,
)

PACKAGE_VERSION = "1.0.0"
RESPONSIBILITY = (
    "Sole facade for GrammarLearningSnapshot, completed-topic sync, and resolve_targets"
)

__all__ = [
    "GRAMMAR_LEARNING_SNAPSHOT_VERSION",
    "GrammarCompletedSyncResult",
    "GrammarIntegrationPort",
    "GrammarIntegrationService",
    "GrammarLearningSnapshot",
    "GrammarMasteryPlanSummary",
    "GrammarResolveTargetsRequest",
    "GrammarResolveTargetsResult",
    "GrammarReviewPlanItem",
    "GrammarTopicPlanMeta",
    "PACKAGE_VERSION",
    "RESPONSIBILITY",
    "build_learning_snapshot",
    "build_learning_snapshot_async",
    "build_learning_snapshot_for_planner",
    "resolve_targets",
    "resolve_targets_from_snapshot",
    "sync_completed_topics",
    "sync_completed_topics_async",
]
