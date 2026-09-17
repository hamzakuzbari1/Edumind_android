"""Speaking curriculum (S1).

RESPONSIBILITY: Skill dependency graph catalog and node metadata.
Sole owner of Speaking skill prerequisite relationships.
"""

from app.services.language_speaking_curriculum.evidence_ids import ALL_EVIDENCE_CODES
from app.services.language_speaking_curriculum.skill_catalog import (
    SPEAKING_SKILL_GRAPH,
    build_speaking_skill_graph,
)
from app.services.language_speaking_curriculum.trace import SpeakingSkillGraphTrace
from app.services.language_speaking_curriculum.types import (
    LANGUAGE_SPEAKING_CURRICULUM_VERSION,
    SPEAKING_SKILL_GRAPH_VERSION,
    SPEAKING_SKILL_SCHEMA_VERSION,
    SkillEvidenceRequirement,
    SkillMasteryRequirement,
    SpeakingSkillGraph,
    SpeakingSkillNode,
    SpacedRepetitionProfile,
)
from app.services.language_speaking_curriculum.validator import (
    GraphValidationIssue,
    GraphValidationResult,
    validate_skill_graph,
)

__all__ = [
    "ALL_EVIDENCE_CODES",
    "GraphValidationIssue",
    "GraphValidationResult",
    "LANGUAGE_SPEAKING_CURRICULUM_VERSION",
    "SPEAKING_SKILL_GRAPH",
    "SPEAKING_SKILL_GRAPH_VERSION",
    "SPEAKING_SKILL_SCHEMA_VERSION",
    "SkillEvidenceRequirement",
    "SkillMasteryRequirement",
    "SpeakingSkillGraph",
    "SpeakingSkillGraphTrace",
    "SpeakingSkillNode",
    "SpacedRepetitionProfile",
    "build_speaking_skill_graph",
    "validate_skill_graph",
]
