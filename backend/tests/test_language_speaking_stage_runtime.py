from types import SimpleNamespace

import pytest

from app.services.language_speaking.enums import SpeakingLearningStage
from app.services.language_speaking_learning_stage import stage_runtime as runtime
from app.services.language_speaking_transition_gate.types import (
    TRANSITION_GATE_SCHEMA_VERSION,
    TRANSITION_POLICY_VERSION,
    SpeakingStageTransitionDecision,
    SpeakingStageTransitionDecisionKind,
)


@pytest.mark.asyncio
async def test_auto_speaking_stage_evaluation_uses_locked_row_cefr(monkeypatch) -> None:
    row = SimpleNamespace(
        official_speaking_cefr="A1",
        learning_stage_speaking=1,
        promotion_readiness_json={},
    )
    captured: dict[str, str] = {}

    async def fake_ensure_progression_row(*args, **kwargs):
        return row

    async def fake_lock_speaking_progression_row(*args, **kwargs):
        return row

    def fake_snapshot_from_locked_row(*args, official_cefr: str, **kwargs):
        captured["official_cefr"] = official_cefr
        return SimpleNamespace(
            official_cefr=official_cefr,
            current_stage=SpeakingLearningStage.foundation,
            snapshot_fingerprint="snap_a1",
        )

    def fake_evaluate_transition_gate(snapshot):
        return SpeakingStageTransitionDecision(
            schema_version=TRANSITION_GATE_SCHEMA_VERSION,
            policy_version=TRANSITION_POLICY_VERSION,
            official_cefr=snapshot.official_cefr,
            current_stage=snapshot.current_stage,
            target_stage=None,
            decision=SpeakingStageTransitionDecisionKind.stay,
            authorized=False,
            signal_fingerprint=snapshot.snapshot_fingerprint,
            requirements=(),
            blocking_reasons=("insufficient_evidence",),
            advisory_reasons=(),
            satisfied_requirements=(),
            unknown_requirements=(),
            decision_fingerprint="decision_a1_stay",
        )

    monkeypatch.setattr(runtime, "ensure_progression_row", fake_ensure_progression_row)
    monkeypatch.setattr(runtime, "lock_speaking_progression_row", fake_lock_speaking_progression_row)
    monkeypatch.setattr(runtime, "_build_snapshot_from_locked_row", fake_snapshot_from_locked_row)
    monkeypatch.setattr(
        "app.services.language_speaking_transition_gate.rules.evaluate_speaking_transition_gate",
        fake_evaluate_transition_gate,
    )

    result = await runtime.evaluate_and_persist_speaking_stage(
        None, student_id=123, language_id=1
    )

    assert captured["official_cefr"] == "A1"
    assert result.stage_written is False
    assert result.new_stage == SpeakingLearningStage.foundation
