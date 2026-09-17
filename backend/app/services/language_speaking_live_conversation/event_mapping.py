"""Map Hume EVI provider events to canonical live conversation facts (S7.5)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.services.language_speaking_live_conversation.types import (
    SpeakingLiveEvent,
    SpeakingLiveExpressionMeasure,
)


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _expression_from_models(models: object) -> tuple[SpeakingLiveExpressionMeasure, ...]:
    if not isinstance(models, dict):
        return ()
    prosody = models.get("prosody") or {}
    scores = prosody.get("scores") if isinstance(prosody, dict) else None
    if not isinstance(scores, dict):
        return ()
    out: list[SpeakingLiveExpressionMeasure] = []
    for label, score in scores.items():
        try:
            val = float(score)
        except (TypeError, ValueError):
            continue
        out.append(SpeakingLiveExpressionMeasure(provider_label=str(label), score=val))
    return tuple(out)


def map_evi_event(raw: dict[str, object]) -> SpeakingLiveEvent:
    """Preserve only fields present in the provider payload."""
    event_type = str(raw.get("type") or "unknown")
    canonical = event_type
    if event_type == "user_interruption":
        canonical = "interruption"
    elif event_type == "chat_metadata":
        canonical = "session_metadata"
    elif event_type == "audio_output":
        canonical = "assistant_audio"
    elif event_type == "assistant_end":
        canonical = "assistant_turn_end"
    elif event_type == "user_message":
        canonical = "user_turn_message"
    elif event_type == "assistant_message":
        canonical = "assistant_message"
    elif event_type == "error":
        canonical = "provider_error"
    return SpeakingLiveEvent(
        event_type=canonical,
        provider_event_type=event_type,
        payload=dict(raw),
        received_at=_now_iso(),
    )


def extract_user_message_facts(raw: dict[str, object]) -> tuple[str, tuple[SpeakingLiveExpressionMeasure, ...], tuple[int, int] | None]:
    transcript = ""
    msg = raw.get("message")
    if isinstance(msg, dict):
        transcript = str(msg.get("content") or msg.get("text") or "")
    measures = _expression_from_models(raw.get("models"))
    timing: tuple[int, int] | None = None
    time_block = raw.get("time")
    if isinstance(time_block, dict):
        begin = int(time_block.get("begin") or 0)
        end = int(time_block.get("end") or begin)
        timing = (begin, end)
    return transcript, measures, timing


def extract_chat_metadata(raw: dict[str, object]) -> tuple[str, str]:
    chat_id = str(raw.get("chat_id") or raw.get("id") or "")
    chat_group_id = str(raw.get("chat_group_id") or "")
    return chat_id, chat_group_id
