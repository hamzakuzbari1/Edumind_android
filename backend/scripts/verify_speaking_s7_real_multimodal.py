"""Real S7 multimodal acceptance — GPT-4o + wav2vec2 S5 + acoustic S6 + Claude S7.

FAIL (exit 1), not SKIP, when any layer uses mock or required API keys are missing.

Usage (from backend/):
    set SPEAKING_S7_HUMAN_AUDIO_FIXTURE=C:\\path\\to\\human_speech.ogg
    set SPEAKING_EDUCATIONAL_ANALYZER=claude
    python scripts/verify_speaking_s7_real_multimodal.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.services.claude_service import is_claude_configured  # noqa: E402
from app.services.language_speaking.enums import SpeakingAudioSource  # noqa: E402
from app.services.language_speaking_audio_frontend.media_adapter import artifact_from_bytes  # noqa: E402
from app.services.language_speaking_evaluation_runtime.evaluation_pipeline import process_speaking_evaluation  # noqa: E402
from app.services.language_speaking_evaluator.input_types import (  # noqa: E402
    SpeakingGoalContext,
    SpeakingOfficialCefrContext,
    SpeakingTaskContext,
)

NOW = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
_DEFAULT_FIXTURE = Path(__file__).resolve().parents[2] / "test audio" / "WhatsApp Ptt 2026-07-12 at 11.38.43 AM.ogg"
_SUPPORTED_SUFFIXES = frozenset({".wav", ".mp3", ".ogg", ".opus", ".m4a", ".webm", ".flac", ".aac"})


def _ok(label: str, passed: bool, detail: str = "") -> bool:
    mark = "PASS" if passed else "FAIL"
    line = f"  [{mark}] {label}"
    if detail:
        line += f" -- {detail}"
    print(line)
    return passed


def _resolve_fixture() -> Path:
    env = os.environ.get("SPEAKING_S7_HUMAN_AUDIO_FIXTURE", "").strip()
    if env:
        return Path(env)
    return _DEFAULT_FIXTURE


def _content_type(path: Path) -> str:
    return {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".ogg": "audio/ogg",
        ".opus": "audio/opus",
        ".m4a": "audio/mp4",
        ".webm": "audio/webm",
        ".flac": "audio/flac",
        ".aac": "audio/mp4",
    }.get(path.suffix.lower(), "application/octet-stream")


async def _run() -> list[bool]:
    results: list[bool] = []
    settings = get_settings()

    fixture = _resolve_fixture()
    results.append(_ok("human fixture exists", fixture.is_file(), str(fixture)))
    results.append(_ok("fixture suffix supported", fixture.suffix.lower() in _SUPPORTED_SUFFIXES, fixture.suffix))

    mode = (settings.SPEAKING_EDUCATIONAL_ANALYZER or "claude").strip().lower()
    results.append(_ok("S7 analyzer mode is claude", mode == "claude", mode))
    results.append(_ok("Claude configured", is_claude_configured()))
    results.append(_ok("OpenAI key present", bool(settings.OPENAI_API_KEY)))

    if not fixture.is_file():
        return results

    audio_bytes = fixture.read_bytes()
    artifact = artifact_from_bytes(
        audio_id="s7_real_human",
        session_id="session_s7_real",
        student_id=701,
        language_id=1,
        audio_bytes=audio_bytes,
        original_filename=fixture.name,
        content_type=_content_type(fixture),
        audio_source=SpeakingAudioSource.file_upload,
        captured_at=NOW,
    )

    task = SpeakingTaskContext(
        task_id="s7_real_prompt",
        task_type="free_speech",
        task_prompt="Tell me about your day and what you did this morning.",
        task_instructions="Speak naturally for up to one minute.",
        success_criteria=("Mentions morning activities", "Uses past tense"),
        target_skill_ids=("pattern:word_stress",),
    )

    turn = await process_speaking_evaluation(
        artifact,
        audio_bytes,
        task=task,
        goal=SpeakingGoalContext(speaking_goal="general_english", goal_label="General English"),
        official_cefr=SpeakingOfficialCefrContext(official_cefr="B1"),
        student_id=701,
        language_id=1,
        revision_number=1,
        language="en",
        initial_prompt=task.task_prompt,
        transcription_provider=None,
        pronunciation_provider=None,
        prosody_provider="acoustic",
    )

    results.append(_ok("pipeline success", turn.success, turn.error))
    if not turn.success or turn.evaluation is None:
        return results

    ev = turn.evaluation
    results.append(_ok("engine version 7.0.0", ev.engine_version == "7.0.0"))
    results.append(_ok("transcript captured", bool(ev.evidence_summary.availability.get("transcript", False) or ev.task_response.score > 0)))

    prov_names = [str(p.get("provider_name", "")).lower() for p in ev.provider_provenance if isinstance(p, dict)]
    prov_blob = " ".join(prov_names)
    results.append(_ok("S4 not mock", "mock" not in prov_blob or "openai" in prov_blob or "gpt" in prov_blob, prov_blob[:120]))
    results.append(_ok("S5 not mock-only", "mock" not in prov_blob or "wav2vec" in prov_blob, prov_blob[:120]))
    results.append(_ok("S6 acoustic provider", "acoustic" in prov_blob or any("acoustic" in str(p).lower() for p in prov_names)))

    edu = ev.educational_analysis
    results.append(_ok("S7 educational analysis present", edu is not None))
    if edu:
        results.append(_ok("S7 analyzer not mock", edu.source == "claude", edu.source))
        results.append(_ok("S7 analyzer available", edu.available))
        results.append(_ok("S7 model recorded", bool(edu.model_name), edu.model_name))

    print("\n--- Layer provenance ---")
    for p in ev.provider_provenance:
        if isinstance(p, dict):
            print(f"  evidence: provider={p.get('provider_name')} model={p.get('model_name')}")
    if edu:
        print(f"  S7 analyzer: source={edu.source} model={edu.model_name} version={edu.analyzer_version}")

    print("\n--- Canonical result summary ---")
    print(f"  evaluation_id={ev.evaluation_id}")
    print(f"  task_response.score={ev.task_response.score:.3f} status={ev.task_response.status.value}")
    print(f"  pronunciation.score={ev.pronunciation.score:.3f}")
    print(f"  fluency_delivery.score={ev.fluency_delivery.score:.3f}")
    print(f"  revision_ready={ev.revision_readiness.ready} blockers={list(ev.revision_readiness.blockers)}")
    print(f"  completion_eligible={ev.completion_eligibility.eligible}")
    if edu and edu.observed_cefr_estimate:
        print(f"  observed_cefr_estimate={edu.observed_cefr_estimate} (not official)")

    results.append(_ok("no mock in real S7 path", edu is not None and edu.source == "claude"))
    return results


def main() -> int:
    print("Speaking S7 Real Multimodal Acceptance\n")
    results = asyncio.run(_run())
    passed = sum(results)
    total = len(results)
    print(f"\nSummary: {passed}/{total} checks passed")
    if passed == total:
        print("SPEAKING S7 REAL MULTIMODAL ACCEPTANCE PASSED.")
        return 0
    print("SPEAKING S7 REAL MULTIMODAL ACCEPTANCE FAILED.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
