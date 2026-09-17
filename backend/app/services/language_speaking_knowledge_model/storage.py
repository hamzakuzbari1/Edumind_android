"""Persistence contract for Speaking Knowledge Model (S2).

Storage location:
  LanguageProgression.promotion_readiness_json['speaking']['knowledge_model']

This is intentionally separate from future promotion readiness data in the same
``speaking`` bucket (S16+). Knowledge model state must not be stored at the
``speaking`` root level mixed with readiness scores.
"""

from __future__ import annotations

from typing import Any

from app.services.language_speaking_curriculum.types import SPEAKING_SKILL_GRAPH_VERSION
from app.services.language_speaking_knowledge_model.types import (
    KNOWLEDGE_MODEL_SCHEMA_VERSION,
    MistakePatternSummary,
    StudentSpeakingKnowledgeModel,
    StudentSpeakingSkillState,
    skill_state_from_dict,
    skill_state_to_dict,
)

SPEAKING_BUCKET_KEY = "speaking"
KNOWLEDGE_MODEL_KEY = "knowledge_model"


def empty_knowledge_model(*, student_id: int, language_id: int) -> StudentSpeakingKnowledgeModel:
    return StudentSpeakingKnowledgeModel(
        student_id=student_id,
        language_id=language_id,
        schema_version=KNOWLEDGE_MODEL_SCHEMA_VERSION,
        graph_version=SPEAKING_SKILL_GRAPH_VERSION,
    )


def knowledge_model_to_dict(model: StudentSpeakingKnowledgeModel) -> dict[str, Any]:
    return {
        "schema_version": model.schema_version,
        "graph_version": model.graph_version,
        "student_id": model.student_id,
        "language_id": model.language_id,
        "skill_states": {
            sid: skill_state_to_dict(st) for sid, st in model.skill_states.items()
        },
        "deprecated_skill_states": {
            sid: skill_state_to_dict(st) for sid, st in model.deprecated_skill_states.items()
        },
        "mistake_patterns": {
            tag: {
                "mistake_tag": mp.mistake_tag,
                "occurrence_count": mp.occurrence_count,
                "recent_occurrence_count": mp.recent_occurrence_count,
                "last_seen_at": mp.last_seen_at,
                "affected_contexts": list(mp.affected_contexts),
            }
            for tag, mp in model.mistake_patterns.items()
        },
        "applied_observation_ids": dict(model.applied_observation_ids),
        "total_observations": model.total_observations,
        "last_updated_at": model.last_updated_at,
        "compatibility_notes": list(model.compatibility_notes),
    }


def knowledge_model_from_dict(
    raw: dict[str, Any] | None,
    *,
    student_id: int,
    language_id: int,
) -> StudentSpeakingKnowledgeModel:
    if not isinstance(raw, dict):
        return empty_knowledge_model(student_id=student_id, language_id=language_id)

    skill_states: dict[str, StudentSpeakingSkillState] = {}
    raw_skills = raw.get("skill_states") or {}
    if isinstance(raw_skills, dict):
        for sid, st_raw in raw_skills.items():
            if isinstance(st_raw, dict):
                state = skill_state_from_dict(st_raw)
                state.skill_id = str(sid)
                skill_states[str(sid)] = state

    deprecated: dict[str, StudentSpeakingSkillState] = {}
    raw_dep = raw.get("deprecated_skill_states") or {}
    if isinstance(raw_dep, dict):
        for sid, st_raw in raw_dep.items():
            if isinstance(st_raw, dict):
                state = skill_state_from_dict(st_raw)
                state.skill_id = str(sid)
                deprecated[str(sid)] = state

    mistake_patterns: dict[str, MistakePatternSummary] = {}
    raw_mp = raw.get("mistake_patterns") or {}
    if isinstance(raw_mp, dict):
        for tag, mp_raw in raw_mp.items():
            if isinstance(mp_raw, dict):
                mistake_patterns[str(tag)] = MistakePatternSummary(
                    mistake_tag=str(mp_raw.get("mistake_tag", tag)),
                    occurrence_count=int(mp_raw.get("occurrence_count", 0)),
                    recent_occurrence_count=int(mp_raw.get("recent_occurrence_count", 0)),
                    last_seen_at=mp_raw.get("last_seen_at"),
                    affected_contexts=[str(c) for c in (mp_raw.get("affected_contexts") or [])],
                )

    applied = raw.get("applied_observation_ids") or {}
    if not isinstance(applied, dict):
        applied = {}

    return StudentSpeakingKnowledgeModel(
        student_id=int(raw.get("student_id", student_id)),
        language_id=int(raw.get("language_id", language_id)),
        schema_version=str(raw.get("schema_version", KNOWLEDGE_MODEL_SCHEMA_VERSION)),
        graph_version=str(raw.get("graph_version", "")),
        skill_states=skill_states,
        deprecated_skill_states=deprecated,
        mistake_patterns=mistake_patterns,
        applied_observation_ids={str(k): str(v) for k, v in applied.items()},
        total_observations=int(raw.get("total_observations", 0)),
        last_updated_at=raw.get("last_updated_at"),
        compatibility_notes=[str(n) for n in (raw.get("compatibility_notes") or [])],
    )


def knowledge_model_from_speaking_bucket(
    speaking_bucket: dict[str, Any] | None,
    *,
    student_id: int,
    language_id: int,
) -> StudentSpeakingKnowledgeModel:
    if not isinstance(speaking_bucket, dict):
        return empty_knowledge_model(student_id=student_id, language_id=language_id)
    raw = speaking_bucket.get(KNOWLEDGE_MODEL_KEY)
    return knowledge_model_from_dict(raw if isinstance(raw, dict) else None, student_id=student_id, language_id=language_id)


def merge_knowledge_model_into_speaking_bucket(
    speaking_bucket: dict[str, Any] | None,
    model: StudentSpeakingKnowledgeModel,
) -> dict[str, Any]:
    """Preserve unrelated keys in the speaking bucket (e.g. future readiness)."""
    bucket = dict(speaking_bucket) if isinstance(speaking_bucket, dict) else {}
    bucket[KNOWLEDGE_MODEL_KEY] = knowledge_model_to_dict(model)
    return bucket


def speaking_bucket_from_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    raw = payload.get(SPEAKING_BUCKET_KEY)
    return dict(raw) if isinstance(raw, dict) else {}
