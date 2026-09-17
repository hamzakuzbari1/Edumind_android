"""Grammar Mastery (G2.2) — sole authority for per-topic grammar proficiency.

RESPONSIBILITY: Internal mastery dimensions + overall_mastery + state; sole scorer
of mastery updates from validated Grammar Evidence.
"""

from __future__ import annotations

from app.services.language_grammar_mastery.engine import (
    GrammarMasteryError,
    apply_observation,
    apply_observations,
    disabled_mastery_snapshot,
    empty_snapshot,
)
from app.services.language_grammar_mastery.flags import (
    grammar_engine_enabled,
    grammar_engine_select_enabled,
)
from app.services.language_grammar_mastery.policy import (
    DEFAULT_MASTERY_SCORING_POLICY_ID,
    DefaultWeightedMasteryScoringPolicy,
    MasteryDimensionInputs,
    MasteryScoringPolicy,
    OVERALL_WEIGHT_ACCURACY,
    OVERALL_WEIGHT_FLUENCY,
    OVERALL_WEIGHT_RETENTION,
    OVERALL_WEIGHT_UNDERSTANDING,
    derive_overall_via_policy,
    get_active_mastery_scoring_policy,
    get_default_mastery_scoring_policy,
    set_active_mastery_scoring_policy,
)
from app.services.language_grammar_mastery.service import (
    apply_evidence_and_persist,
    completion_ready_ids,
    compute_mastery_from_evidence,
    get_grammar_mastery_snapshot,
    public_views,
)
from app.services.language_grammar_mastery.types import (
    GRAMMAR_MASTERY_SCHEMA_VERSION,
    GrammarMasteryDimensions,
    GrammarMasteryRecord,
    GrammarMasterySnapshot,
    PublicGrammarMasteryView,
    build_dimensions,
    derive_overall_mastery,
    to_public_view,
)

PACKAGE_VERSION = "1.0.1"
RESPONSIBILITY = (
    "Internal mastery dimensions + overall_mastery + state; sole scorer of mastery updates"
)

__all__ = [
    "DEFAULT_MASTERY_SCORING_POLICY_ID",
    "DefaultWeightedMasteryScoringPolicy",
    "GRAMMAR_MASTERY_SCHEMA_VERSION",
    "GrammarMasteryDimensions",
    "GrammarMasteryError",
    "GrammarMasteryRecord",
    "GrammarMasterySnapshot",
    "MasteryDimensionInputs",
    "MasteryScoringPolicy",
    "OVERALL_WEIGHT_ACCURACY",
    "OVERALL_WEIGHT_FLUENCY",
    "OVERALL_WEIGHT_RETENTION",
    "OVERALL_WEIGHT_UNDERSTANDING",
    "PACKAGE_VERSION",
    "PublicGrammarMasteryView",
    "RESPONSIBILITY",
    "apply_evidence_and_persist",
    "apply_observation",
    "apply_observations",
    "build_dimensions",
    "completion_ready_ids",
    "compute_mastery_from_evidence",
    "derive_overall_mastery",
    "derive_overall_via_policy",
    "disabled_mastery_snapshot",
    "empty_snapshot",
    "get_active_mastery_scoring_policy",
    "get_default_mastery_scoring_policy",
    "get_grammar_mastery_snapshot",
    "grammar_engine_enabled",
    "grammar_engine_select_enabled",
    "public_views",
    "set_active_mastery_scoring_policy",
    "to_public_view",
]
