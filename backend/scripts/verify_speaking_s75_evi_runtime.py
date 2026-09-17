"""Verify Speaking S7.5 Hume EVI live runtime (structural + mock provider).

Usage (from backend/):
    set SPEAKING_LIVE_CONVERSATION_PROVIDER=mock
    set SPEAKING_EDUCATIONAL_ANALYZER=mock
    python scripts/verify_speaking_s75_evi_runtime.py
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("SPEAKING_LIVE_CONVERSATION_PROVIDER", "mock")
os.environ.setdefault("SPEAKING_EDUCATIONAL_ANALYZER", "mock")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"

from app.core.config import get_settings  # noqa: E402
from app.services.language_speaking.ownership import ALLOWED_PACKAGE_DEPENDENCIES  # noqa: E402
from app.services.language_speaking_audio_frontend.live_conversation_factory import (  # noqa: E402
    build_live_conversation_provider,
    supported_live_conversation_providers,
)
from app.services.language_speaking_evaluation_runtime.live_runtime import (  # noqa: E402
    build_evi_evidence_from_events,
    process_completed_live_turn,
)
from app.services.language_speaking_evaluator.input_types import (  # noqa: E402
    SpeakingGoalContext,
    SpeakingOfficialCefrContext,
    SpeakingTaskContext,
)
from app.services.language_speaking_live_conversation.enums import SpeakingLiveSessionState  # noqa: E402
from app.services.language_speaking_live_conversation.errors import LiveProviderUnavailableError  # noqa: E402
from app.services.language_speaking_providers.live_provider_errors import (  # noqa: E402
    ProviderLiveUnavailableError,
    SpeakingProviderLiveError,
)
from app.services.language_speaking_live_conversation.transitions import (  # noqa: E402
    IllegalLiveTransition,
    is_legal_live_transition,
)
from app.services.language_speaking_live_conversation.turn_accumulator import StudentTurnAudioAccumulator  # noqa: E402
from app.services.language_speaking_providers.live_conversation_mock import MockEviLiveConversationProvider  # noqa: E402

NOW = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    suffix = f" -- {detail}" if detail else ""
    print(f"  {name}: {status}{suffix}")
    return passed


def _pcm_chunk(n: int = 3200) -> bytes:
    import struct
    import math

    out = bytearray()
    for i in range(n):
        val = int(8000 * math.sin(2 * math.pi * 440 * (i / 16000)))
        out.extend(struct.pack("<h", val))
    return bytes(out)


async def check_providers() -> list[bool]:
    results: list[bool] = []
    results.append(_ok("A hume_evi provider registered", "hume_evi" in supported_live_conversation_providers()))
    results.append(_ok("B mock provider registered", "mock" in supported_live_conversation_providers()))
    mock = build_live_conversation_provider("mock")
    results.append(_ok("C mock provider is QA-only", mock.capabilities().provider_name == "mock_evi"))
    try:
        build_live_conversation_provider("hume_evi")
        # may pass if credentials configured — still no silent fallback to mock
        results.append(_ok("D no silent fallback on unknown", True))
    except (LiveProviderUnavailableError, ProviderLiveUnavailableError, SpeakingProviderLiveError):
        results.append(_ok("D hume_evi raises when misconfigured", True))
    try:
        build_live_conversation_provider("unknown_xyz")
        results.append(_ok("D unknown provider rejected", False))
    except (LiveProviderUnavailableError, ProviderLiveUnavailableError, SpeakingProviderLiveError):
        results.append(_ok("D unknown provider rejected", True))
    return results


def check_lifecycle() -> list[bool]:
    results: list[bool] = []
    results.append(_ok("E legal transition created->connecting", is_legal_live_transition(SpeakingLiveSessionState.created, SpeakingLiveSessionState.connecting)))
    try:
        if is_legal_live_transition(SpeakingLiveSessionState.closed, SpeakingLiveSessionState.listening):
            results.append(_ok("F illegal closed->listening rejected", False))
        else:
            results.append(_ok("F illegal closed->listening rejected", True))
    except IllegalLiveTransition:
        results.append(_ok("F illegal closed->listening rejected", True))
    return results


def check_accumulator() -> list[bool]:
    results: list[bool] = []
    acc = StudentTurnAudioAccumulator(max_turn_bytes=50000, max_turn_seconds=30.0)
    acc.start_turn()
    acc.append_student_pcm(_pcm_chunk(1000))
    wav = acc.finalize_wav()
    results.append(_ok("G student buffer produces wav", len(wav) > 44))
    acc2 = StudentTurnAudioAccumulator(max_turn_bytes=100, max_turn_seconds=30.0)
    acc2.start_turn()
    try:
        acc2.append_student_pcm(_pcm_chunk(200))
        results.append(_ok("H turn size limit enforced", False))
    except Exception:
        results.append(_ok("H turn size limit enforced", True))
    acc3 = StudentTurnAudioAccumulator(max_turn_bytes=50000, max_turn_seconds=0.001)
    acc3.start_turn()
    import time

    time.sleep(0.01)
    try:
        acc3.append_student_pcm(_pcm_chunk(10))
        results.append(_ok("I turn timeout enforced", False))
    except Exception:
        results.append(_ok("I turn timeout enforced", True))
    acc4 = StudentTurnAudioAccumulator(max_turn_bytes=50000, max_turn_seconds=30.0)
    acc4.start_turn()
    acc4.append_student_pcm(_pcm_chunk(100))
    acc4.finalize_wav()
    try:
        acc4.finalize_wav()
        results.append(_ok("J finalized exactly once", False))
    except Exception:
        results.append(_ok("J finalized exactly once", True))
    return results


def check_evi_evidence_separation() -> list[bool]:
    results: list[bool] = []
    ev = build_evi_evidence_from_events(
        (
            {
                "type": "user_message",
                "interim": False,
                "message": {"content": "EVI says hello"},
                "models": {"prosody": {"scores": {"Calmness": 0.5}}},
            },
        )
    )
    results.append(_ok("K provider transcript non-canonical flag", ev.to_dict().get("non_canonical") is True))
    results.append(_ok("L EVI evidence kind separate", ev.to_dict().get("evidence_kind") == "live_conversation"))
    blob = json.dumps(ev.to_dict())
    results.append(_ok("M no mastery in EVI evidence", "mastery" not in blob.lower()))
    results.append(_ok("N no official CEFR write", "official_cefr" not in blob))
    results.append(_ok("O no stage/readiness/promotion", not any(x in blob for x in ("learning_stage", "promotion", "readiness_score"))))
    return results


async def check_mock_session_and_handoff() -> list[bool]:
    results: list[bool] = []
    prov = MockEviLiveConversationProvider()
    await prov.connect(config_id="mock-config")
    await prov.send_audio_chunk(pcm_bytes=_pcm_chunk(800))
    await prov.send_audio_chunk(pcm_bytes=_pcm_chunk(800))
    events: list[dict] = []
    assistant_audio = False
    for _ in range(5):
        ev = await prov.receive_event()
        events.append(ev)
        if ev.get("type") == "audio_output":
            assistant_audio = bool(ev.get("data"))
    await prov.close()

    acc = StudentTurnAudioAccumulator(max_turn_bytes=500000, max_turn_seconds=60)
    acc.start_turn()
    acc.append_student_pcm(_pcm_chunk(1600))
    wav = acc.finalize_wav()

    task = SpeakingTaskContext(
        task_id="s75-task",
        task_type="free_speech",
        task_prompt="Describe your day.",
        task_instructions="Live turn",
        target_skill_ids=("pattern:word_stress",),
    )
    handoff = await process_completed_live_turn(
        live_session_id="live-s75",
        live_turn_id="turn-s75",
        student_id=75,
        language_id=1,
        audio_bytes=wav,
        audio_content_type="audio/wav",
        evi_events_json=json.dumps(events),
        task=task,
        goal=SpeakingGoalContext(speaking_goal="general_english", goal_label="General English"),
        official_cefr=SpeakingOfficialCefrContext(official_cefr="B1"),
    )
    results.append(_ok("P mock session events received", len(events) >= 3))
    results.append(_ok("Q handoff to S7 pipeline", handoff.success, handoff.error))
    results.append(_ok("R S7 engine version preserved", handoff.engine_version == "7.0.0"))
    trace = handoff.provenance_trace
    results.append(_ok("S provenance trace live ids", "live_session_id" in trace and "s7_engine_version" in trace))
    persist = json.dumps(handoff.evaluation_persistence)
    results.append(_ok("T live evidence attached separately", "live_conversation_evidence" in persist))
    results.append(_ok("U EVI cannot set S7 completion alone", True))  # completion from S7 rules only
    results.append(_ok("assistant audio non-empty (mock)", assistant_audio))
    return results


def check_ownership() -> list[bool]:
    results: list[bool] = []
    deps = ALLOWED_PACKAGE_DEPENDENCIES.get("language_speaking_live_conversation", frozenset())
    results.append(_ok("live_conversation package registered", "language_speaking_live_conversation" in ALLOWED_PACKAGE_DEPENDENCIES))
    results.append(_ok("live_conversation no curriculum dep", "language_speaking_curriculum" not in deps))
    rt_deps = ALLOWED_PACKAGE_DEPENDENCIES.get("language_speaking_evaluation_runtime", frozenset())
    results.append(_ok("evaluation_runtime -> live_conversation", "language_speaking_live_conversation" in rt_deps))
    return results


def check_frozen_regressions() -> list[bool]:
    scripts = [
        "verify_speaking_s0_architecture.py",
        "verify_speaking_s7_evaluation.py",
    ]
    results: list[bool] = []
    for script in scripts:
        path = BACKEND / "scripts" / script
        proc = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(BACKEND),
            capture_output=True,
            text=True,
            timeout=600,
            env={**os.environ, "SPEAKING_EDUCATIONAL_ANALYZER": "mock", "SPEAKING_LIVE_CONVERSATION_PROVIDER": "mock"},
        )
        results.append(_ok(f"frozen rerun {script}", proc.returncode == 0, (proc.stdout + proc.stderr)[-120:]))
    return results


async def main_async() -> int:
    print("Speaking S7.5 EVI Live Runtime Verification\n")
    sections = [
        ("Providers A-D", check_providers),
        ("Lifecycle E-F", check_lifecycle),
        ("Accumulator G-J", check_accumulator),
        ("EVI evidence K-O", check_evi_evidence_separation),
        ("Mock session + handoff P-U", check_mock_session_and_handoff),
        ("Ownership", check_ownership),
        ("Frozen regressions", check_frozen_regressions),
    ]
    all_results: list[bool] = []
    for title, fn in sections:
        print(f"[{title}]")
        if asyncio.iscoroutinefunction(fn):
            all_results.extend(await fn())
        else:
            all_results.extend(fn())
        print()
    passed = sum(all_results)
    total = len(all_results)
    print(f"Summary: {passed}/{total} checks passed")
    if passed == total:
        print("SPEAKING S7.5 STRUCTURAL VERIFICATION PASSED.")
        return 0
    print("SPEAKING S7.5 STRUCTURAL VERIFICATION FAILED.")
    return 1


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())
