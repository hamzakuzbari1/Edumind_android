"""Serialize / deserialize / fingerprint ActivitySpecification (G3.35)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.services.language_grammar_activity_spec.enums import ActivityDifficulty
from app.services.language_grammar_activity_spec.types import (
    ActivityAssetRef,
    ActivityReference,
    ActivitySpecification,
    ActivityVersionSet,
    CompletionRule,
    EvidenceDeclaration,
    ExpectedOutputSpec,
    LocalizedText,
    ProviderMetadata,
)


def localized_to_dict(text: LocalizedText) -> dict[str, Any]:
    return {"values": dict(text.values), "default_locale": text.default_locale}


def localized_from_dict(raw: dict[str, Any] | None) -> LocalizedText:
    data = dict(raw or {})
    return LocalizedText(
        values={str(k): str(v) for k, v in dict(data.get("values") or {}).items()},
        default_locale=str(data.get("default_locale") or "en"),
    )


def specification_to_dict(spec: ActivitySpecification) -> dict[str, Any]:
    return {
        "activity_id": spec.activity_id,
        "activity_type": spec.activity_type,
        "grammar_topic": spec.grammar_topic,
        "lesson_id": spec.lesson_id,
        "step_id": spec.step_id,
        "title": localized_to_dict(spec.title),
        "goal": localized_to_dict(spec.goal),
        "instructions": localized_to_dict(spec.instructions),
        "difficulty": spec.difficulty.value,
        "estimated_duration_seconds": spec.estimated_duration_seconds,
        "grammar_targets": list(spec.grammar_targets),
        "expected_outputs": [
            {
                "output_id": o.output_id,
                "output_type": o.output_type,
                "required": o.required,
                "options": list(o.options),
                "constraints": dict(o.constraints),
            }
            for o in spec.expected_outputs
        ],
        "evaluation_mode": spec.evaluation_mode,
        "completion_rules": [
            {"rule_id": r.rule_id, "kind": r.kind, "params": dict(r.params)}
            for r in spec.completion_rules
        ],
        "hints": [localized_to_dict(h) for h in spec.hints],
        "assets": [
            {
                "asset_id": a.asset_id,
                "kind": a.kind,
                "uri": a.uri,
                "locale": a.locale,
                "metadata": dict(a.metadata),
            }
            for a in spec.assets
        ],
        "references": [
            {
                "ref_id": r.ref_id,
                "kind": r.kind,
                "label": localized_to_dict(r.label),
            }
            for r in spec.references
        ],
        "evidence": [
            {
                "evidence_id": e.evidence_id,
                "evidence_kind": e.evidence_kind,
                "grammar_targets": list(e.grammar_targets),
                "observation_types_hint": list(e.observation_types_hint),
                "required": e.required,
                "notes": e.notes,
            }
            for e in spec.evidence
        ],
        "provider_metadata": {
            "provider_id": spec.provider_metadata.provider_id,
            "provider_version": spec.provider_metadata.provider_version,
            "generation_mode": spec.provider_metadata.generation_mode,
            "extras": dict(spec.provider_metadata.extras),
        },
        "localization_default_locale": spec.localization_default_locale,
        "supported_locales": list(spec.supported_locales),
        "versions": {
            "activity_schema_version": spec.versions.activity_schema_version,
            "provider_version": spec.versions.provider_version,
            "planner_version": spec.versions.planner_version,
            "blueprint_version": spec.versions.blueprint_version,
            "catalog_version": spec.versions.catalog_version,
            "grammar_schema_version": spec.versions.grammar_schema_version,
            "package_version": spec.versions.package_version,
        },
        "fingerprint": spec.fingerprint,
        "payload": dict(spec.payload),
    }


def specification_from_dict(raw: dict[str, Any]) -> ActivitySpecification:
    versions_raw = dict(raw.get("versions") or {})
    return ActivitySpecification(
        activity_id=str(raw["activity_id"]),
        activity_type=str(raw["activity_type"]),
        grammar_topic=str(raw["grammar_topic"]),
        lesson_id=str(raw["lesson_id"]),
        step_id=str(raw["step_id"]),
        title=localized_from_dict(dict(raw.get("title") or {})),
        goal=localized_from_dict(dict(raw.get("goal") or {})),
        instructions=localized_from_dict(dict(raw.get("instructions") or {})),
        difficulty=ActivityDifficulty(str(raw.get("difficulty") or ActivityDifficulty.guided.value)),
        estimated_duration_seconds=int(raw.get("estimated_duration_seconds") or 0),
        grammar_targets=tuple(str(x) for x in (raw.get("grammar_targets") or ())),
        expected_outputs=tuple(
            ExpectedOutputSpec(
                output_id=str(o["output_id"]),
                output_type=str(o["output_type"]),
                required=bool(o.get("required", True)),
                options=tuple(o.get("options") or ()),
                constraints={str(k): str(v) for k, v in dict(o.get("constraints") or {}).items()},
            )
            for o in (raw.get("expected_outputs") or [])
            if isinstance(o, dict)
        ),
        evaluation_mode=str(raw.get("evaluation_mode") or ""),
        completion_rules=tuple(
            CompletionRule(
                rule_id=str(r["rule_id"]),
                kind=str(r["kind"]),
                params={str(k): str(v) for k, v in dict(r.get("params") or {}).items()},
            )
            for r in (raw.get("completion_rules") or [])
            if isinstance(r, dict)
        ),
        hints=tuple(localized_from_dict(dict(h)) for h in (raw.get("hints") or []) if isinstance(h, dict)),
        assets=tuple(
            ActivityAssetRef(
                asset_id=str(a["asset_id"]),
                kind=str(a.get("kind") or "media"),
                uri=str(a.get("uri") or ""),
                locale=a.get("locale"),
                metadata={str(k): str(v) for k, v in dict(a.get("metadata") or {}).items()},
            )
            for a in (raw.get("assets") or [])
            if isinstance(a, dict)
        ),
        references=tuple(
            ActivityReference(
                ref_id=str(r["ref_id"]),
                kind=str(r.get("kind") or "grammar_topic"),
                label=localized_from_dict(dict(r.get("label") or {})),
            )
            for r in (raw.get("references") or [])
            if isinstance(r, dict)
        ),
        evidence=tuple(
            EvidenceDeclaration(
                evidence_id=str(e["evidence_id"]),
                evidence_kind=str(e["evidence_kind"]),
                grammar_targets=tuple(str(x) for x in (e.get("grammar_targets") or ())),
                observation_types_hint=tuple(str(x) for x in (e.get("observation_types_hint") or ())),
                required=bool(e.get("required", True)),
                notes=str(e.get("notes") or ""),
            )
            for e in (raw.get("evidence") or [])
            if isinstance(e, dict)
        ),
        provider_metadata=ProviderMetadata(
            provider_id=str((raw.get("provider_metadata") or {}).get("provider_id") or ""),
            provider_version=str((raw.get("provider_metadata") or {}).get("provider_version") or ""),
            generation_mode=str((raw.get("provider_metadata") or {}).get("generation_mode") or ""),
            extras={
                str(k): str(v)
                for k, v in dict((raw.get("provider_metadata") or {}).get("extras") or {}).items()
            },
        ),
        localization_default_locale=str(raw.get("localization_default_locale") or "en"),
        supported_locales=tuple(str(x) for x in (raw.get("supported_locales") or ("en",))),
        versions=ActivityVersionSet(
            activity_schema_version=int(versions_raw.get("activity_schema_version") or 1),
            provider_version=str(versions_raw.get("provider_version") or ""),
            planner_version=str(versions_raw.get("planner_version") or ""),
            blueprint_version=str(versions_raw.get("blueprint_version") or ""),
            catalog_version=str(versions_raw.get("catalog_version") or ""),
            grammar_schema_version=int(versions_raw.get("grammar_schema_version") or 1),
            package_version=str(versions_raw.get("package_version") or ""),
        ),
        fingerprint=str(raw.get("fingerprint") or ""),
        payload={str(k): str(v) for k, v in dict(raw.get("payload") or {}).items()},
    )


def fingerprint_specification(spec: ActivitySpecification) -> str:
    """Deterministic content fingerprint (excludes existing fingerprint field)."""
    payload = specification_to_dict(spec)
    payload["fingerprint"] = ""
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def with_fingerprint(spec: ActivitySpecification) -> ActivitySpecification:
    """Return a copy with fingerprint set from content."""
    fp = fingerprint_specification(spec)
    return ActivitySpecification(
        activity_id=spec.activity_id,
        activity_type=spec.activity_type,
        grammar_topic=spec.grammar_topic,
        lesson_id=spec.lesson_id,
        step_id=spec.step_id,
        title=spec.title,
        goal=spec.goal,
        instructions=spec.instructions,
        difficulty=spec.difficulty,
        estimated_duration_seconds=spec.estimated_duration_seconds,
        grammar_targets=spec.grammar_targets,
        expected_outputs=spec.expected_outputs,
        evaluation_mode=spec.evaluation_mode,
        completion_rules=spec.completion_rules,
        hints=spec.hints,
        assets=spec.assets,
        references=spec.references,
        evidence=spec.evidence,
        provider_metadata=spec.provider_metadata,
        localization_default_locale=spec.localization_default_locale,
        supported_locales=spec.supported_locales,
        versions=spec.versions,
        fingerprint=fp,
        payload=spec.payload,
    )
