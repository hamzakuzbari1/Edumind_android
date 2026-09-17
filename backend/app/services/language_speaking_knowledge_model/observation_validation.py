"""Observation validation for Speaking Knowledge Model (S2)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.services.language_speaking_curriculum.evidence_ids import ALL_EVIDENCE_CODES
from app.services.language_speaking_curriculum.skill_catalog import SPEAKING_SKILL_GRAPH
from app.services.language_speaking_curriculum.types import SpeakingSkillNode
from app.services.language_speaking_knowledge_model.types import SpeakingSkillEvidenceObservation


@dataclass(frozen=True, slots=True)
class ValidationError:
    code: str
    message: str


def _parse_observed_at(value: str, *, now: datetime) -> datetime | ValidationError:
    if not value or not value.strip():
        return ValidationError("EMPTY_TIMESTAMP", "observed_at required")
    try:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(timezone.utc)
    except ValueError:
        return ValidationError("INVALID_TIMESTAMP", f"Invalid observed_at: {value}")
    if dt > now:
        return ValidationError("FUTURE_TIMESTAMP", "observed_at cannot be in the future")
    return dt


def validate_observation(
    observation: SpeakingSkillEvidenceObservation,
    *,
    now: datetime,
) -> tuple[SpeakingSkillNode | None, ValidationError | None]:
    if not observation.observation_id.strip():
        return None, ValidationError("EMPTY_OBSERVATION_ID", "observation_id required")

    node = SPEAKING_SKILL_GRAPH.node_by_id(observation.skill_id)
    if node is None:
        return None, ValidationError("UNKNOWN_SKILL", f"Unknown skill_id: {observation.skill_id}")

    if not (0.0 <= observation.performance <= 1.0):
        return None, ValidationError("INVALID_PERFORMANCE", "performance must be in [0, 1]")

    if not (0.0 <= observation.confidence <= 1.0):
        return None, ValidationError("INVALID_CONFIDENCE", "confidence must be in [0, 1]")

    if observation.communicative_impact is not None and not (
        0.0 <= observation.communicative_impact <= 1.0
    ):
        return None, ValidationError("INVALID_IMPACT", "communicative_impact must be in [0, 1]")

    parsed_time = _parse_observed_at(observation.observed_at, now=now)
    if isinstance(parsed_time, ValidationError):
        return None, parsed_time

    if not observation.context_id.strip():
        return None, ValidationError("EMPTY_CONTEXT", "context_id required for distinct-context counting")

    if not observation.evidence_dimensions:
        return None, ValidationError("EMPTY_DIMENSIONS", "evidence_dimensions required")

    for dim in observation.evidence_dimensions:
        if dim not in ALL_EVIDENCE_CODES:
            return None, ValidationError("UNKNOWN_DIMENSION", f"Unknown evidence dimension: {dim}")

    required = set(node.evidence_requirements.evidence_codes)
    observed = set(observation.evidence_dimensions)
    overlap = required & observed
    if len(overlap) < node.evidence_requirements.minimum_dimensions:
        return None, ValidationError(
            "INSUFFICIENT_DIMENSION_OVERLAP",
            f"Observation dimensions {sorted(observed)} do not satisfy "
            f"{node.skill_id} requirements {sorted(required)} "
            f"(minimum {node.evidence_requirements.minimum_dimensions})",
        )

    for tag in observation.mistake_tags:
        if not tag.strip():
            return None, ValidationError("MALFORMED_MISTAKE_TAG", "empty mistake tag")
        if len(tag) > 64:
            return None, ValidationError("MALFORMED_MISTAKE_TAG", f"mistake tag too long: {tag[:40]}")
        if " " in tag and ":" not in tag:
            return None, ValidationError("MALFORMED_MISTAKE_TAG", f"prose-like mistake tag rejected: {tag[:40]}")

    return node, None


from app.services.language_speaking_knowledge_model.types import EvidenceCoverage


def evidence_coverage_for_state(
    node: SpeakingSkillNode,
    observed_dimensions: dict[str, int],
) -> EvidenceCoverage:
    required = tuple(node.evidence_requirements.evidence_codes)
    observed = tuple(d for d in required if observed_dimensions.get(d, 0) > 0)
    missing = tuple(d for d in required if d not in observed)
    ratio = len(observed) / len(required) if required else 0.0
    return EvidenceCoverage(
        required_dimensions=required,
        observed_dimensions=observed,
        missing_dimensions=missing,
        coverage_ratio=ratio,
    )
