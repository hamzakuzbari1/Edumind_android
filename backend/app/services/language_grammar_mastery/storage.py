"""Typed Grammar Mastery storage under promotion_readiness_json['grammar']['mastery']."""

from __future__ import annotations

from typing import Any

from app.services.language_grammar.enums import (
    GrammarEvidenceSourceSkill,
    GrammarMasteryState,
    GrammarReinforcementSkill,
)
from app.services.language_grammar.ownership import GRAMMAR_JSONB_NAMESPACE
from app.services.language_grammar.types import GRAMMAR_STORAGE_MASTERY_KEY
from app.services.language_grammar_mastery.types import (
    GRAMMAR_MASTERY_SCHEMA_VERSION,
    GrammarMasteryDimensions,
    GrammarMasteryRecord,
    GrammarMasterySnapshot,
    build_dimensions,
)


def mastery_bucket_from_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    root = dict((payload or {}).get(GRAMMAR_JSONB_NAMESPACE) or {})
    return dict(root.get(GRAMMAR_STORAGE_MASTERY_KEY) or {})


def merge_mastery_into_payload(
    payload: dict[str, Any] | None,
    bucket: dict[str, Any],
) -> dict[str, Any]:
    out = dict(payload or {})
    root = dict(out.get(GRAMMAR_JSONB_NAMESPACE) or {})
    root[GRAMMAR_STORAGE_MASTERY_KEY] = dict(bucket)
    out[GRAMMAR_JSONB_NAMESPACE] = root
    return out


def _parse_skill(raw: str) -> GrammarReinforcementSkill | GrammarEvidenceSourceSkill:
    try:
        return GrammarReinforcementSkill(raw)
    except ValueError:
        return GrammarEvidenceSourceSkill(raw)


def _float_map(raw: Any) -> dict[str, float]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, float] = {}
    for key, value in raw.items():
        k = str(key or "").strip()
        if not k:
            continue
        try:
            out[k] = float(value)
        except (TypeError, ValueError):
            continue
    return out


def _int_map(raw: Any) -> dict[str, int]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, int] = {}
    for key, value in raw.items():
        k = str(key or "").strip()
        if not k:
            continue
        try:
            out[k] = max(0, int(value))
        except (TypeError, ValueError):
            continue
    return out


def _record_from_dict(raw: dict[str, Any], *, student_id: int, language_id: int) -> GrammarMasteryRecord:
    dims_raw = dict(raw.get("dimensions") or {})
    # Always re-derive overall — never trust stored overall as source of truth.
    dims = build_dimensions(
        understanding=float(dims_raw.get("understanding") or 0.0),
        accuracy=float(dims_raw.get("accuracy") or 0.0),
        fluency=float(dims_raw.get("fluency") or 0.0),
        retention=float(dims_raw.get("retention") or 0.0),
    )
    coverage_raw = raw.get("skill_coverage") or []
    coverage = frozenset(_parse_skill(str(s)) for s in coverage_raw)
    state_raw = str(raw.get("state") or GrammarMasteryState.unknown.value)
    try:
        state = GrammarMasteryState(state_raw)
    except ValueError as exc:
        raise ValueError(f"Corrupted mastery state: {state_raw}") from exc
    return GrammarMasteryRecord(
        student_id=student_id,
        language_id=language_id,
        grammar_id=str(raw.get("grammar_id") or ""),
        state=state,
        dimensions=dims,
        confidence=float(raw.get("confidence") or 0.0),
        stability=float(raw.get("stability") or 0.0),
        retention_risk=float(raw.get("retention_risk") or 0.0),
        evidence_count=int(raw.get("evidence_count") or 0),
        distinct_context_count=int(raw.get("distinct_context_count") or 0),
        skill_coverage=coverage,
        best_score_by_skill=_float_map(raw.get("best_score_by_skill")),
        best_attempt_count_by_skill=_int_map(raw.get("best_attempt_count_by_skill")),
        best_correct_count_by_skill=_int_map(raw.get("best_correct_count_by_skill")),
        introduced_at=raw.get("introduced_at"),
        last_seen_at=raw.get("last_seen_at"),
        last_updated_at=raw.get("last_updated_at"),
        last_mastered_at=raw.get("last_mastered_at"),
    )


def snapshot_from_bucket(
    bucket: dict[str, Any] | None,
    *,
    student_id: int,
    language_id: int,
) -> GrammarMasterySnapshot:
    raw = dict(bucket or {})
    records_raw = raw.get("records") or []
    records = tuple(
        _record_from_dict(dict(item), student_id=student_id, language_id=language_id)
        for item in records_raw
        if isinstance(item, dict)
    )
    applied = frozenset(str(x) for x in (raw.get("applied_observation_ids") or []) if str(x).strip())
    contexts_raw = dict(raw.get("contexts_by_grammar_id") or {})
    contexts: dict[str, frozenset[str]] = {
        str(gid): frozenset(str(c) for c in (vals or []) if str(c).strip())
        for gid, vals in contexts_raw.items()
    }
    return GrammarMasterySnapshot(
        student_id=student_id,
        language_id=language_id,
        records=tuple(sorted(records, key=lambda r: r.grammar_id)),
        applied_observation_ids=applied,
        contexts_by_grammar_id=contexts,
        schema_version=int(raw.get("schema_version") or GRAMMAR_MASTERY_SCHEMA_VERSION),
        enabled=True,
    )


def bucket_from_snapshot(snapshot: GrammarMasterySnapshot) -> dict[str, Any]:
    """Persist mastery state. overall_mastery stored for convenience but re-derived on load."""
    records: list[dict[str, Any]] = []
    for rec in snapshot.records:
        records.append(
            {
                "grammar_id": rec.grammar_id,
                "state": rec.state.value,
                "dimensions": {
                    "understanding": rec.dimensions.understanding,
                    "accuracy": rec.dimensions.accuracy,
                    "fluency": rec.dimensions.fluency,
                    "retention": rec.dimensions.retention,
                    "overall_mastery": rec.dimensions.overall_mastery,
                },
                "confidence": rec.confidence,
                "stability": rec.stability,
                "retention_risk": rec.retention_risk,
                "evidence_count": rec.evidence_count,
                "distinct_context_count": rec.distinct_context_count,
                "skill_coverage": sorted(s.value for s in rec.skill_coverage),
                "best_score_by_skill": dict(sorted(rec.best_score_by_skill.items())),
                "best_attempt_count_by_skill": dict(sorted(rec.best_attempt_count_by_skill.items())),
                "best_correct_count_by_skill": dict(sorted(rec.best_correct_count_by_skill.items())),
                "introduced_at": rec.introduced_at,
                "last_seen_at": rec.last_seen_at,
                "last_updated_at": rec.last_updated_at,
                "last_mastered_at": rec.last_mastered_at,
            }
        )
    return {
        "schema_version": GRAMMAR_MASTERY_SCHEMA_VERSION,
        "records": records,
        "applied_observation_ids": sorted(snapshot.applied_observation_ids),
        "contexts_by_grammar_id": {
            gid: sorted(ctxs) for gid, ctxs in sorted(snapshot.contexts_by_grammar_id.items())
        },
    }
