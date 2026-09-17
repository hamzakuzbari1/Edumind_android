"""Deterministic fingerprints for pipeline replay."""

from __future__ import annotations

import hashlib
import json

from app.services.language_grammar_pipeline.types import PipelineRequest, PipelineReplayBundle


def fingerprint_pipeline_request(request: PipelineRequest) -> str:
    payload = {
        "student_id": request.student_id,
        "language_id": request.language_id,
        "student_response": (request.student_response or "").strip(),
        "expected_patterns": list(request.expected_patterns),
        "activity_type": request.activity_type,
        "as_of": request.as_of,
        "mode": request.mode.value,
        "use_llm_authoring": bool(request.use_llm_authoring),
        "grammar_targets": list(
            request.replay_bundle.grammar_targets
            if request.replay_bundle is not None
            else (
                request.specification.grammar_targets
                if request.specification is not None
                else (
                    (request.learning_snapshot.current_grammar_id,)
                    if request.learning_snapshot and request.learning_snapshot.current_grammar_id
                    else ()
                )
            )
        ),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def fingerprint_replay_bundle(bundle: PipelineReplayBundle) -> str:
    payload = {
        "pipeline_id": bundle.pipeline_id,
        "lesson_id": bundle.blueprint.lesson_id,
        "activity_id": bundle.specification.activity_id,
        "student_response": (bundle.student_response or "").strip(),
        "grammar_targets": list(bundle.grammar_targets),
        "expected_patterns": list(bundle.expected_patterns),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
