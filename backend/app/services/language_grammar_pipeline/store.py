"""In-memory replay artifact store for Grammar Learning Pipeline."""

from __future__ import annotations

from app.services.language_grammar_pipeline.errors import PipelineValidationError
from app.services.language_grammar_pipeline.types import PipelineReplayBundle

_STORE: dict[str, PipelineReplayBundle] = {}


def save_replay_bundle(bundle: PipelineReplayBundle) -> None:
    if not bundle.pipeline_id:
        raise PipelineValidationError("missing_pipeline_id", "Replay bundle requires pipeline_id")
    _STORE[bundle.pipeline_id] = bundle


def get_replay_bundle(pipeline_id: str) -> PipelineReplayBundle:
    if pipeline_id not in _STORE:
        raise PipelineValidationError(
            "replay_bundle_missing",
            f"No replay bundle for pipeline_id={pipeline_id}",
        )
    return _STORE[pipeline_id]


def reset_replay_store_for_tests() -> None:
    _STORE.clear()
