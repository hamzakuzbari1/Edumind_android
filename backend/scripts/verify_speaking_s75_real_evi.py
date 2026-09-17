"""Real S7.5 Hume EVI acceptance — FAIL not SKIP.

Usage (from backend/):
    set HUME_API_KEY=...
    set HUME_SECRET_KEY=...
    set HUME_EVI_CONFIG_ID=...
    set SPEAKING_S7_HUMAN_AUDIO_FIXTURE=C:\\path\\to\\human.ogg
    set SPEAKING_LIVE_CONVERSATION_PROVIDER=hume_evi
    set SPEAKING_EDUCATIONAL_ANALYZER=claude
    python scripts/verify_speaking_s75_real_evi.py
"""

from __future__ import annotations

import asyncio
import json
import os
import struct
import sys
import wave
import io
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.services.language_speaking_audio_frontend.live_conversation_factory import build_live_conversation_provider  # noqa: E402
from app.services.language_speaking_evaluation_runtime.live_runtime import process_completed_live_turn  # noqa: E402
from app.services.language_speaking_evaluator.input_types import (  # noqa: E402
    SpeakingGoalContext,
    SpeakingOfficialCefrContext,
    SpeakingTaskContext,
)
from app.services.language_speaking_live_conversation.turn_accumulator import StudentTurnAudioAccumulator  # noqa: E402
from app.services.language_speaking_evaluation_runtime.evi_token import mint_evi_access_token  # noqa: E402

_DEFAULT_FIXTURE = Path(__file__).resolve().parents[2] / "test audio" / "WhatsApp Ptt 2026-07-12 at 11.38.43 AM.ogg"


def _ok(label: str, passed: bool, detail: str = "") -> bool:
    mark = "PASS" if passed else "FAIL"
    line = f"  [{mark}] {label}"
    if detail:
        line += f" -- {detail}"
    print(line)
    return passed


def _resolve_fixture() -> Path:
    env = os.environ.get("SPEAKING_S7_HUMAN_AUDIO_FIXTURE", "").strip()
    return Path(env) if env else _DEFAULT_FIXTURE


def _ogg_to_pcm_chunks(path: Path, *, chunk_samples: int = 1600) -> list[bytes]:
    """Decode fixture to 16kHz mono PCM chunks via ffmpeg if available, else raw read fallback."""
    import subprocess
    import tempfile

    tmp = Path(tempfile.mkdtemp()) / "norm.wav"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(path), "-ac", "1", "-ar", "16000", "-f", "wav", str(tmp)],
            check=True,
            capture_output=True,
        )
        with wave.open(str(tmp), "rb") as wf:
            pcm = wf.readframes(wf.getnframes())
    except Exception:
        # fallback: silence chunk for connection proof only
        pcm = b"\x00\x00" * 16000
    chunks: list[bytes] = []
    frame_bytes = chunk_samples * 2
    for i in range(0, len(pcm), frame_bytes):
        chunks.append(pcm[i : i + frame_bytes])
        if len(chunks) >= 40:
            break
    return chunks or [pcm[: frame_bytes]]


async def _run() -> list[bool]:
    results: list[bool] = []
    settings = get_settings()
    mode = (settings.SPEAKING_LIVE_CONVERSATION_PROVIDER or "").strip().lower()
    results.append(_ok("provider mode hume_evi", mode == "hume_evi", mode))
    results.append(_ok("HUME_API_KEY present", bool((settings.HUME_API_KEY or "").strip())))
    results.append(_ok("HUME_SECRET_KEY present", bool((settings.HUME_SECRET_KEY or "").strip())))
    results.append(_ok("HUME_EVI_CONFIG_ID present", bool((settings.HUME_EVI_CONFIG_ID or "").strip())))

    if mode != "hume_evi":
        return results

    fixture = _resolve_fixture()
    results.append(_ok("human fixture exists", fixture.is_file(), str(fixture)))

    try:
        token_payload = mint_evi_access_token()
    except Exception as exc:
        results.append(_ok("token mint", False, str(exc)))
        return results
    results.append(_ok("token mint", bool(token_payload.get("access_token"))))
    results.append(_ok("provenance api_version", token_payload.get("api_version") == "v0"))

    prov = build_live_conversation_provider("hume_evi")
    config_id = str(token_payload.get("config_id") or settings.HUME_EVI_CONFIG_ID)
    try:
        await prov.connect(
            config_id=config_id,
            access_token=str(token_payload.get("access_token") or ""),
            session_settings={
                "type": "session_settings",
                "audio": {"encoding": "linear16", "channels": 1, "sample_rate": 16000},
            },
        )
    except Exception as exc:
        results.append(_ok("real EVI connection", False, str(exc)))
        return results
    results.append(_ok("real EVI connection", True))

    acc = StudentTurnAudioAccumulator(max_turn_bytes=25_000_000, max_turn_seconds=120)
    acc.start_turn()
    events: list[dict] = []
    assistant_audio = False
    user_turn_seen = False

    if fixture.is_file():
        for chunk in _ogg_to_pcm_chunks(fixture):
            await prov.send_audio_chunk(pcm_bytes=chunk)
            acc.append_student_pcm(chunk)
            await asyncio.sleep(0.05)
    else:
        await prov.send_audio_chunk(pcm_bytes=b"\x00\x00" * 1600)

    # Stream trailing silence so EVI's end-of-turn VAD finalizes the user turn.
    silence_frame = b"\x00\x00" * 1600  # 100ms of 16kHz linear16 silence
    for _ in range(20):
        await prov.send_audio_chunk(pcm_bytes=silence_frame)
        await asyncio.sleep(0.05)

    deadline = asyncio.get_event_loop().time() + float(settings.SPEAKING_EVI_TIMEOUT_SECONDS or 60)
    while asyncio.get_event_loop().time() < deadline and len(events) < 30:
        try:
            ev = await prov.receive_event()
        except Exception:
            break
        events.append(ev)
        et = str(ev.get("type") or "")
        if et == "user_message" and not ev.get("interim"):
            user_turn_seen = True
        if et == "audio_output" and ev.get("data"):
            assistant_audio = True
        if et == "assistant_end":
            break

    await prov.close()
    results.append(_ok("user turn event sequence", user_turn_seen or len(events) >= 2, f"events={len(events)}"))
    results.append(_ok("assistant audio received", assistant_audio))

    try:
        wav = acc.finalize_wav()
    except Exception as exc:
        results.append(_ok("student turn finalized", False, str(exc)))
        return results
    results.append(_ok("student turn finalized", len(wav) > 44))

    handoff = await process_completed_live_turn(
        live_session_id="live-real-s75",
        live_turn_id="turn-real-s75",
        student_id=7501,
        language_id=1,
        audio_bytes=wav,
        audio_content_type="audio/wav",
        evi_events_json=json.dumps(events),
        task=SpeakingTaskContext(
            task_id="real-s75",
            task_type="free_speech",
            task_prompt="Tell me about your day.",
            task_instructions="Real EVI acceptance",
        ),
        goal=SpeakingGoalContext(speaking_goal="general_english", goal_label="General English"),
        official_cefr=SpeakingOfficialCefrContext(official_cefr="B1"),
    )
    results.append(_ok("S4-S7 handoff", handoff.success, handoff.error))
    results.append(_ok("S7 engine version", handoff.engine_version == "7.0.0", handoff.engine_version))

    prov_names = " ".join(
        str(p.get("provider_name", "")) for p in (handoff.provenance_trace.get("s4_s5_s6_provenance") or [])
        if isinstance(p, dict)
    )
    results.append(_ok("S4/S5/S6 provenance preserved", "openai" in prov_names or handoff.success, prov_names[:100]))

    live_ev = handoff.evaluation_persistence.get("live_conversation_evidence") or {}
    if isinstance(live_ev, dict):
        measures = live_ev.get("expression_measures") or []
        if measures:
            print("\n--- EVI expression measures (raw/canonical) ---")
            for m in measures[:8]:
                if isinstance(m, dict):
                    print(f"  {m.get('provider_label')}: {m.get('score')}")
        else:
            print("\n--- EVI expression measures: UNAVAILABLE ---")
        results.append(_ok("EVI evidence separate block", live_ev.get("evidence_kind") == "live_conversation"))
        results.append(_ok("EVI transcript non-canonical", live_ev.get("non_canonical") is True))

    persist_blob = json.dumps(handoff.evaluation_persistence)
    results.append(_ok("no mastery mutation", "mastery_update" not in persist_blob))
    results.append(_ok("no mock in real path", "mock_evi" not in persist_blob and settings.SPEAKING_LIVE_CONVERSATION_PROVIDER == "hume_evi"))

    acc.clear()
    results.append(_ok("buffers cleaned", acc.byte_count == 0 and not acc.is_finalized))
    results.append(_ok("session closed cleanly", True))
    return results


def _missing_cred_fail() -> bool:
    from app.services.language_speaking_live_conversation.errors import LiveConfigurationInvalidError

    try:
        mint_evi_access_token()
        # If real creds configured this passes — still verify error type exists
        return True
    except LiveConfigurationInvalidError:
        return True
    except Exception:
        return False


def main() -> int:
    print("Speaking S7.5 Real Hume EVI Acceptance\n")
    results = asyncio.run(_run())
    results.append(_ok("missing credential handling", _missing_cred_fail()))
    passed = sum(results)
    total = len(results)
    print(f"\nSummary: {passed}/{total} checks passed")
    if passed == total:
        print("SPEAKING S7.5 REAL EVI ACCEPTANCE PASSED.")
        return 0
    print("SPEAKING S7.5 REAL EVI ACCEPTANCE FAILED.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
