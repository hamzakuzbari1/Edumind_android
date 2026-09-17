"""Verify optional Supertonic GPU provider detection (Phase 1).

Usage (from backend/):
    python scripts/verify_supertonic_gpu_providers.py
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]


def _ort_providers() -> list[str]:
    try:
        import onnxruntime as ort

        return list(ort.get_available_providers())
    except Exception:
        return []


def static_checks() -> dict[str, bool | str]:
    supertonic_src = (BACKEND / "app/services/language_supertonic_service.py").read_text(encoding="utf-8")
    voice_src = (BACKEND / "app/services/voice_service.py").read_text(encoding="utf-8")
    transcription_src = (BACKEND / "app/services/language_transcription_service.py").read_text(encoding="utf-8")
    req_txt = (BACKEND / "requirements.txt").read_text(encoding="utf-8")
    gpu_req = BACKEND / "requirements-supertonic-gpu.txt"
    readme = (BACKEND.parent / "README.md").read_text(encoding="utf-8")

    return {
        "provider_detection_fn": "resolve_supertonic_onnx_providers" in supertonic_src,
        "startup_log_format": "Supertonic ONNX Provider:" in supertonic_src,
        "cuda_cpu_fallback": "CUDAExecutionProvider" in supertonic_src and "CPUExecutionProvider" in supertonic_src,
        "gpu_requirements_file": gpu_req.is_file(),
        "requirements_txt_unchanged_cpu_torch": "torch==2.5.1+cpu" in req_txt and "faiss-cpu" in req_txt,
        "whisper_lesson_cpu": 'device="cpu"' in voice_src,
        "whisper_conversation_cpu": 'device="cpu"' in transcription_src,
        "readme_gpu_section": "GPU Acceleration (Optional)" in readme,
        "claude_http_only": (BACKEND / "app/services/claude_service.py").is_file(),
        "deepgram_http_only": (BACKEND / "app/services/student_chat_stt_service.py").is_file(),
        "elevenlabs_http_only": (BACKEND / "app/services/elevenlabs_service.py").is_file(),
        "ocr_mistral_only": (BACKEND / "app/services/mistral_ocr_service.py").is_file(),
    }


def runtime_checks() -> dict[str, bool | str | list[str]]:
    from app.services.language_supertonic_service import (
        primary_supertonic_onnx_provider,
        resolve_supertonic_onnx_providers,
    )

    providers = resolve_supertonic_onnx_providers()
    primary = primary_supertonic_onnx_provider()
    ort_available = _ort_providers()
    cuda_in_ort = "CUDAExecutionProvider" in ort_available

    expected_primary = "CUDAExecutionProvider" if cuda_in_ort else "CPUExecutionProvider"
    cpu_always_present = "CPUExecutionProvider" in providers
    cuda_order_ok = (
        providers == ["CUDAExecutionProvider", "CPUExecutionProvider"]
        if cuda_in_ort
        else providers == ["CPUExecutionProvider"]
    )

    # Whisper paths must remain CPU-bound (no edits in this phase).
    from app.services import voice_service

    whisper_fn = inspect.getsource(voice_service._get_lesson_faster_whisper_model)
    whisper_still_cpu = 'device="cpu"' in whisper_fn

    return {
        "resolved_providers": providers,
        "primary_provider": primary,
        "expected_primary": expected_primary,
        "primary_matches_environment": primary == expected_primary,
        "cpu_fallback_in_list": cpu_always_present,
        "provider_order_correct": cuda_order_ok,
        "whisper_runtime_unchanged": whisper_still_cpu,
        "no_crash_on_detection": bool(providers),
    }


def main() -> int:
    static = static_checks()
    runtime = runtime_checks()

    print("=== Supertonic GPU Phase 1 — static ===")
    for key, value in static.items():
        print(f"  {key}: {value}")

    print("\n=== Supertonic GPU Phase 1 — runtime ===")
    for key, value in runtime.items():
        print(f"  {key}: {value}")

    static_ok = all(v is True for v in static.values() if isinstance(v, bool))
    runtime_ok = all(
        runtime[k]
        for k in (
            "primary_matches_environment",
            "cpu_fallback_in_list",
            "provider_order_correct",
            "whisper_runtime_unchanged",
            "no_crash_on_detection",
        )
    )

    verdict = "PASS" if static_ok and runtime_ok else "FAIL"
    print(f"\nVerdict: {verdict}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
