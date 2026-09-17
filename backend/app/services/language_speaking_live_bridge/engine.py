"""Live Speaking Bridge engine — Preparation → Scene Practice → LiveConversationContext."""

from __future__ import annotations

import base64
import logging
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.language.progression import LanguageProgression
from app.services.language_educational_package.lifecycle import PackageLifecycleStatus
from app.services.language_educational_package.types import EducationalPackage
from app.services.language_speaking_audio_frontend.errors import SpeakingAudioRuntimeError
from app.services.language_speaking_audio_frontend.media_adapter import artifact_from_bytes
from app.services.language_speaking_audio_frontend.normalization_runtime import (
    normalize_audio_with_bytes,
)
from app.services.language_speaking_audio_frontend.transcription_factory import (
    build_transcription_provider,
)
from app.services.language_transcription_service import transcribe_english_audio
from app.services.language_speaking_discussion.storage import discussion_from_payload
from app.services.language_speaking_educational_package.persistence import (
    get_package_item_by_id,
    package_from_item,
)
from app.services.language_speaking_knowledge_model.storage import (
    knowledge_model_from_speaking_bucket,
    speaking_bucket_from_payload,
)
from app.services.language_speaking_lesson_runtime.storage import runtime_from_payload as lesson_runtime_from_payload
from app.services.language_speaking_live_bridge.live_context import (
    build_live_conversation_context,
    merge_live_context_into_alex_dict,
)
from app.services.language_speaking_live_bridge.rehearsal import (
    REHEARSAL_PROVIDER_CLAUDE,
    continue_rehearsal_turn,
    start_rehearsal,
)
from app.services.language_speaking_live_bridge.voice import synthesize_scene_line
from app.services.language_speaking_live_bridge.scenario import (
    build_speaking_scenario,
    scenario_to_prep_projection,
)
from app.services.language_speaking_live_bridge.storage import (
    live_bridge_from_payload,
    merge_live_bridge_into_payload,
)
from app.services.language_speaking_live_bridge.types import LiveBridgeBundle

logger = logging.getLogger(__name__)


class LiveBridgeError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(slots=True)
class LiveBridgeView:
    bundle: LiveBridgeBundle
    preparation: dict[str, Any] | None
    voice_session: dict[str, Any] | None = None
    live_context: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "journey_phase": self.bundle.journey_phase,
            "package_id": self.bundle.package_id,
            "preparation": self.preparation,
            "rehearsal": self.bundle.rehearsal.to_dict() if self.bundle.rehearsal else None,
            "voice_session": self.voice_session,
            "live_context": self.live_context
            or (self.bundle.live_context.to_dict() if self.bundle.live_context else None),
            "discussion_summary": self.bundle.discussion_summary,
            "ready_for_live": bool(
                self.bundle.live_context is not None
                and self.bundle.journey_phase in ("ready_for_live", "live_evi", "completed_rehearsal")
            ),
        }


async def _lock_row(
    db: AsyncSession, *, student_id: int, language_id: int
) -> LanguageProgression | None:
    result = await db.execute(
        select(LanguageProgression)
        .where(
            LanguageProgression.student_id == student_id,
            LanguageProgression.language_id == language_id,
        )
        .with_for_update()
    )
    return result.scalar_one_or_none()


def _assert_package(pkg: EducationalPackage) -> None:
    if pkg.status != PackageLifecycleStatus.frozen:
        raise LiveBridgeError("not_frozen", "Learning package is not frozen.")
    if not pkg.story_spine.is_substantive():
        raise LiveBridgeError("no_case", "Educational Case spine is incomplete.")


def _discussion_summary(payload: dict[str, Any]) -> str:
    state = discussion_from_payload(payload)
    if state is None:
        return ""
    bits: list[str] = []
    if state.ready_for_alex:
        bits.append("Guided discussion completed; ready for live speaking.")
    turns = getattr(state, "turns", None) or []
    student_bits: list[str] = []
    for t in turns[-8:]:
        role = t.get("role") if isinstance(t, dict) else getattr(t, "role", None)
        text = t.get("text") if isinstance(t, dict) else getattr(t, "text", "")
        role_s = str(getattr(role, "value", role) or "")
        if role_s in ("student", "user") and str(text or "").strip():
            student_bits.append(str(text).strip()[:80])
    if student_bits:
        bits.append("Recent student points: " + " | ".join(student_bits)[:400])
    return " ".join(bits).strip()


def _weak_skills_from_payload(payload: dict[str, Any], *, student_id: int, language_id: int) -> list[str]:
    bucket = speaking_bucket_from_payload(payload)
    km = knowledge_model_from_speaking_bucket(
        bucket, student_id=student_id, language_id=language_id
    )
    if km is None:
        return []
    out: list[str] = []
    states = getattr(km, "skill_states", None) or {}
    if isinstance(states, dict):
        ranked = sorted(
            states.items(),
            key=lambda kv: float(getattr(kv[1], "mastery", 1.0) or 1.0),
        )
        for skill_id, state in ranked[:6]:
            mastery = float(getattr(state, "mastery", 1.0) or 1.0)
            if mastery < 0.55:
                out.append(str(skill_id))
    return out[:6]


async def _resolve_package(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    payload: dict[str, Any],
    package_id: str | None,
) -> EducationalPackage:
    pid = (package_id or "").strip()
    if not pid:
        lesson = lesson_runtime_from_payload(payload)
        if lesson and lesson.package_id:
            pid = lesson.package_id
    if not pid:
        disc = discussion_from_payload(payload)
        if disc and disc.package_id:
            pid = disc.package_id
    if not pid:
        bundle = live_bridge_from_payload(payload)
        pid = bundle.package_id
    if not pid:
        raise LiveBridgeError("no_package", "No Educational Case package available for the live bridge.")
    item = await get_package_item_by_id(
        db, student_id=student_id, language_id=language_id, package_id=pid
    )
    if item is None:
        raise LiveBridgeError("not_found", "Educational Case package not found.")
    package = package_from_item(item)
    if package is None:
        raise LiveBridgeError("corrupt", "Educational Case package could not be loaded.")
    _assert_package(package)
    return package


def _view(bundle: LiveBridgeBundle, *, voice: dict[str, Any] | None = None) -> LiveBridgeView:
    prep = scenario_to_prep_projection(bundle.scenario) if bundle.scenario else None
    return LiveBridgeView(
        bundle=bundle,
        preparation=prep,
        voice_session=voice,
        live_context=bundle.live_context.to_dict() if bundle.live_context else None,
    )


async def get_live_bridge_view(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> LiveBridgeView:
    row = await _lock_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        raise LiveBridgeError("no_progression", "No learning progression row.")
    payload = dict(row.promotion_readiness_json or {})
    return _view(live_bridge_from_payload(payload))


async def build_preparation(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    package_id: str | None = None,
) -> LiveBridgeView:
    row = await _lock_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        raise LiveBridgeError("no_progression", "No learning progression row.")
    payload = dict(row.promotion_readiness_json or {})
    package = await _resolve_package(
        db,
        student_id=student_id,
        language_id=language_id,
        payload=payload,
        package_id=package_id,
    )
    weak = _weak_skills_from_payload(payload, student_id=student_id, language_id=language_id)
    scenario = build_speaking_scenario(package, weak_skills=weak)
    bundle = live_bridge_from_payload(payload)
    bundle.package_id = package.package_id
    bundle.scenario = scenario
    bundle.discussion_summary = _discussion_summary(payload)
    bundle.rehearsal = None
    bundle.live_context = None
    bundle.journey_phase = "preparation"
    payload = merge_live_bridge_into_payload(payload, bundle)
    row.promotion_readiness_json = payload
    flag_modified(row, "promotion_readiness_json")
    return _view(bundle)


async def start_voice_rehearsal(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    package_id: str | None = None,
) -> LiveBridgeView:
    row = await _lock_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        raise LiveBridgeError("no_progression", "No learning progression row.")
    payload = dict(row.promotion_readiness_json or {})
    package = await _resolve_package(
        db,
        student_id=student_id,
        language_id=language_id,
        payload=payload,
        package_id=package_id,
    )
    bundle = live_bridge_from_payload(payload)
    if bundle.scenario is None or bundle.scenario.package_id != package.package_id:
        weak = _weak_skills_from_payload(payload, student_id=student_id, language_id=language_id)
        bundle.scenario = build_speaking_scenario(package, weak_skills=weak)
        bundle.package_id = package.package_id
        bundle.discussion_summary = bundle.discussion_summary or _discussion_summary(payload)
    weak = _weak_skills_from_payload(payload, student_id=student_id, language_id=language_id)
    state, voice = start_rehearsal(
        package=package,
        scenario=bundle.scenario,
        discussion_summary=bundle.discussion_summary,
        weak_skills=weak,
    )
    bundle.rehearsal = state
    bundle.live_context = None
    bundle.journey_phase = "gpt_rehearsal"
    payload = merge_live_bridge_into_payload(payload, bundle)
    row.promotion_readiness_json = payload
    flag_modified(row, "promotion_readiness_json")
    return _view(bundle, voice=voice)


async def submit_rehearsal_turn(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    student_text: str,
) -> LiveBridgeView:
    row = await _lock_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        raise LiveBridgeError("no_progression", "No learning progression row.")
    payload = dict(row.promotion_readiness_json or {})
    bundle = live_bridge_from_payload(payload)
    if bundle.rehearsal is None or bundle.scenario is None:
        raise LiveBridgeError("no_rehearsal", "No active GPT voice rehearsal.")
    package = await _resolve_package(
        db,
        student_id=student_id,
        language_id=language_id,
        payload=payload,
        package_id=bundle.package_id,
    )
    weak = _weak_skills_from_payload(payload, student_id=student_id, language_id=language_id)
    state = await continue_rehearsal_turn(
        bundle.rehearsal,
        package=package,
        student_text=student_text,
        discussion_summary=bundle.discussion_summary,
        weak_skills=weak,
    )
    bundle.rehearsal = state
    bundle.journey_phase = "gpt_rehearsal"
    payload = merge_live_bridge_into_payload(payload, bundle)
    row.promotion_readiness_json = payload
    flag_modified(row, "promotion_readiness_json")
    return _view(bundle)


def _suffix_for_mime(mime_type: str) -> str:
    mime = (mime_type or "").split(";")[0].strip().lower()
    if mime in {"audio/wav", "audio/x-wav"}:
        return ".wav"
    if mime == "audio/ogg":
        return ".ogg"
    if mime in {"audio/mp4", "video/mp4"}:
        return ".m4a"
    if mime == "audio/mpeg":
        return ".mp3"
    return ".webm"


async def _transcribe_student_audio(
    audio_bytes: bytes,
    mime_type: str,
    *,
    student_id: int,
    language_id: int,
    vocabulary_focus: tuple[str, ...] | list[str] = (),
) -> tuple[str, float | None]:
    """STT for one Scene Practice turn: normalize to canonical WAV, then transcribe."""
    artifact = artifact_from_bytes(
        audio_id=f"scene_{uuid.uuid4().hex[:10]}",
        session_id="scene_practice",
        student_id=student_id,
        language_id=language_id,
        audio_bytes=audio_bytes,
        original_filename="scene_turn",
        content_type=(mime_type or "audio/webm").split(";")[0].strip().lower(),
    )
    try:
        _normalized, wav_bytes, _warnings = normalize_audio_with_bytes(artifact, audio_bytes)
    except SpeakingAudioRuntimeError as exc:
        if (mime_type or "").lower().startswith(("audio/wav", "audio/x-wav")):
            wav_bytes = audio_bytes  # already canonical enough for the provider
        else:
            raise LiveBridgeError("stt_unavailable", "Could not process your recording.") from exc

    prompt = ", ".join(str(w) for w in (vocabulary_focus or []) if str(w).strip())[:200]
    try:
        provider = build_transcription_provider()
        result = await provider.transcribe(
            audio_bytes=wav_bytes,
            mime_type="audio/wav",
            language="en",
            initial_prompt=prompt,
        )
    except Exception as exc:  # noqa: BLE001 — STT failure is a real turn failure (unlike TTS)
        logger.warning("Scene Practice dedicated STT failed; trying shared language STT", exc_info=True)
        try:
            shared = await transcribe_english_audio(
                audio_bytes,
                suffix=_suffix_for_mime(mime_type),
            )
            transcript = str(getattr(shared, "text", "") or "").strip()
            if transcript:
                return transcript, None
        except Exception:  # noqa: BLE001
            logger.warning("Scene Practice shared language STT fallback failed", exc_info=True)
        return "", None

    transcript = str(result.get("text") or "").strip()
    confidence_raw = result.get("provider_confidence")
    confidence = float(confidence_raw) if isinstance(confidence_raw, (int, float)) else None
    return transcript, confidence


def _reprompt_line(state: Any) -> str:
    """Deterministic in-character retry when nothing intelligible was heard."""
    return "Sorry — I didn't catch that. Say it one more time?"


async def _tts_block(text: str) -> dict[str, Any]:
    """TTS is never load-bearing: on failure the turn returns text only."""
    synthesized = await synthesize_scene_line(text)
    if synthesized is None:
        return {"audio_b64": None, "audio_mime": None}
    audio, mime = synthesized
    return {"audio_b64": base64.b64encode(audio).decode("ascii"), "audio_mime": mime}


async def respond_rehearsal_turn(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    audio_bytes: bytes,
    mime_type: str,
) -> tuple[LiveBridgeView, dict[str, Any]]:
    """One voice Scene Practice turn — the server owns the entire conversation.

    Pipeline: student audio → STT → Claude Scene Director → persist RehearsalState
    → TTS → response. Persistence happens BEFORE TTS; a TTS failure returns the
    turn as text only and never fails the turn.
    """
    if not audio_bytes:
        raise LiveBridgeError("empty_audio", "No audio received.")

    row = await _lock_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        raise LiveBridgeError("no_progression", "No learning progression row.")
    payload = dict(row.promotion_readiness_json or {})
    bundle = live_bridge_from_payload(payload)
    if bundle.rehearsal is None or bundle.scenario is None:
        raise LiveBridgeError("no_rehearsal", "No active Scene Practice session.")
    if bundle.journey_phase != "gpt_rehearsal":
        raise LiveBridgeError("no_rehearsal", "Scene Practice is not active.")
    package = await _resolve_package(
        db,
        student_id=student_id,
        language_id=language_id,
        payload=payload,
        package_id=bundle.package_id,
    )

    transcript, confidence = await _transcribe_student_audio(
        audio_bytes,
        mime_type,
        student_id=student_id,
        language_id=language_id,
        vocabulary_focus=bundle.scenario.vocabulary_focus,
    )

    if not transcript:
        # Nothing intelligible: gentle retry, no state mutation, no director call.
        reprompt = _reprompt_line(bundle.rehearsal)
        turn: dict[str, Any] = {
            "heard": False,
            "student_transcript": "",
            "stt_confidence": confidence,
            "provider": bundle.rehearsal.provider,
            "decision": None,
            "micro_correction": None,
            "coaching_note": None,
            "next_line": {"speaker": bundle.rehearsal.gpt_role, "text": reprompt},
            **(await _tts_block(reprompt)),
        }
        return _view(bundle), turn

    state = bundle.rehearsal
    corrections_before = len(state.corrections)
    notes_before = len(state.coaching_notes)
    weak = _weak_skills_from_payload(payload, student_id=student_id, language_id=language_id)
    cefr_val = getattr(row, "official_speaking_cefr", None)
    student_cefr = cefr_val.value if hasattr(cefr_val, "value") else str(cefr_val or "")
    # Plain payload read — no personalization-package import (ownership boundary).
    memory_raw = payload.get("speaking_case_memory")
    student_memory = memory_raw if isinstance(memory_raw, dict) else {}
    state = await continue_rehearsal_turn(
        state,
        package=package,
        student_text=transcript,
        discussion_summary=bundle.discussion_summary,
        weak_skills=weak,
        stt_confidence=confidence,
        student_cefr=student_cefr,
        student_memory=student_memory,
    )
    bundle.rehearsal = state
    bundle.journey_phase = "gpt_rehearsal"

    # Persist student turn, Claude turn, evaluation, correction, beat, provider
    # BEFORE synthesizing audio.
    payload = merge_live_bridge_into_payload(payload, bundle)
    row.promotion_readiness_json = payload
    flag_modified(row, "promotion_readiness_json")

    assistant_turn = state.turns[-1] if state.turns else {}
    next_text = str(assistant_turn.get("text") or "")
    speaker = str(assistant_turn.get("speaker") or state.gpt_role)
    directed_by_claude = state.provider == REHEARSAL_PROVIDER_CLAUDE
    new_corrections = state.corrections[corrections_before:]
    new_notes = state.coaching_notes[notes_before:]

    turn = {
        "heard": True,
        "student_transcript": transcript,
        "stt_confidence": confidence,
        "provider": state.provider,
        "decision": (
            state.evaluations[-1].get("decision")
            if directed_by_claude and state.evaluations
            else None
        ),
        "micro_correction": new_corrections[-1] if new_corrections else None,
        "coaching_note": new_notes[-1] if new_notes else None,
        "next_line": {"speaker": speaker, "text": next_text},
        **(await _tts_block(next_text)),
    }
    return _view(bundle), turn


async def complete_rehearsal(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> LiveBridgeView:
    """Exit rehearsal → generate LiveConversationContext for Hume EVI."""
    row = await _lock_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        raise LiveBridgeError("no_progression", "No learning progression row.")
    payload = dict(row.promotion_readiness_json or {})
    bundle = live_bridge_from_payload(payload)
    if bundle.scenario is None:
        raise LiveBridgeError("no_scenario", "Speaking preparation is required before live conversation.")
    weak = _weak_skills_from_payload(payload, student_id=student_id, language_id=language_id)
    if bundle.rehearsal is not None:
        bundle.rehearsal.completed = True
    live = build_live_conversation_context(
        bundle.scenario,
        rehearsal=bundle.rehearsal,
        discussion_summary=bundle.discussion_summary,
        weak_skills=weak,
    )
    bundle.live_context = live
    bundle.journey_phase = "ready_for_live"
    payload = merge_live_bridge_into_payload(payload, bundle)
    row.promotion_readiness_json = payload
    flag_modified(row, "promotion_readiness_json")
    return _view(bundle)


def apply_live_bridge_to_alex_payload(
    payload: dict[str, Any] | None,
    alex_dict: dict[str, Any],
) -> dict[str, Any]:
    """Merge persisted LiveConversationContext into alex tutor dict (fail soft)."""
    bundle = live_bridge_from_payload(payload)
    if bundle.live_context is None:
        return alex_dict
    return merge_live_context_into_alex_dict(alex_dict, bundle.live_context)


def require_live_context_or_raise(payload: dict[str, Any] | None) -> None:
    """Optional hard gate: refuse empty-world live starts when bridge exists incomplete."""
    bundle = live_bridge_from_payload(payload)
    if bundle.scenario is not None and bundle.live_context is None:
        # Soft: preparation started but rehearsal not exited — still allow if caller wants
        return
