"""Derived acoustic prosody signals from normalized WAV (S6).

DERIVED_ACOUSTIC_EVIDENCE only — numpy/scipy on mono PCM WAV.
Does not fabricate word-aligned pause locations.
"""

from __future__ import annotations

import io
import wave
from typing import Any

import numpy as np

from app.core.config import get_settings

settings = get_settings()


def _decode_wav(audio_bytes: bytes) -> tuple[np.ndarray, int]:
    if not audio_bytes:
        return np.array([], dtype=np.float32), 16000
    with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
    if sample_width == 2:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    else:
        samples = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return samples, sample_rate


def _frame_rms(samples: np.ndarray, frame_len: int, hop: int) -> np.ndarray:
    if len(samples) < frame_len:
        return np.array([], dtype=np.float32)
    frames = []
    for start in range(0, len(samples) - frame_len + 1, hop):
        chunk = samples[start : start + frame_len]
        frames.append(float(np.sqrt(np.mean(chunk**2))))
    return np.array(frames, dtype=np.float32)


def _estimate_pitch_hz(frame: np.ndarray, sample_rate: int) -> float:
    if len(frame) < 64 or float(np.max(np.abs(frame))) < 1e-4:
        return 0.0
    corr = np.correlate(frame, frame, mode="full")
    corr = corr[len(corr) // 2 :]
    corr[0] = 0.0
    min_lag = int(sample_rate / 400)
    max_lag = int(sample_rate / 70)
    if max_lag >= len(corr):
        max_lag = len(corr) - 1
    if min_lag >= max_lag:
        return 0.0
    segment = corr[min_lag:max_lag]
    if segment.size == 0:
        return 0.0
    lag = int(np.argmax(segment)) + min_lag
    if lag <= 0:
        return 0.0
    return float(sample_rate / lag)


def derive_acoustic_prosody(audio_bytes: bytes) -> dict[str, Any]:
    """Return derived signal observations dict fragments."""
    signals: list[dict[str, object]] = []
    unavailable: list[str] = []
    warnings: list[str] = []

    samples, sr = _decode_wav(audio_bytes)
    duration = len(samples) / sr if sr else 0.0
    if duration < 0.08:
        unavailable.append("audio_too_short")
        return {"signal_observations": [], "unavailable_evidence": unavailable, "processing_warnings": warnings}

    rms = float(np.sqrt(np.mean(samples**2))) if len(samples) else 0.0
    if rms < 0.005:
        unavailable.append("evidence_unreliable")
        warnings.append("low_audio_energy")
        return {"signal_observations": [], "unavailable_evidence": unavailable, "processing_warnings": warnings}

    frame_len = max(int(sr * 0.025), 1)
    hop = max(int(sr * 0.010), 1)
    rms_frames = _frame_rms(samples, frame_len, hop)
    silence_thresh = max(float(settings.SPEAKING_PROSODY_SILENCE_RMS or 0.015), rms * 0.15)
    voiced = rms_frames >= silence_thresh

    # Pause segments (derived, not word-aligned).
    pause_segments: list[tuple[float, float]] = []
    in_pause = False
    pause_start = 0
    for i, is_silent in enumerate(voiced):
        t = i * hop / sr
        if is_silent and not in_pause:
            in_pause = True
            pause_start = t
        elif not is_silent and in_pause:
            in_pause = False
            pause_segments.append((pause_start, t))
    if in_pause:
        pause_segments.append((pause_start, len(voiced) * hop / sr))

    long_pause_sec = float(settings.SPEAKING_PROSODY_LONG_PAUSE_SEC or 0.6)
    pause_durations = [end - start for start, end in pause_segments]
    total_pause = sum(pause_durations)
    long_pause_count = sum(1 for d in pause_durations if d >= long_pause_sec)
    pause_density = total_pause / duration if duration else 0.0
    speech_time = max(duration - total_pause, 0.001)
    speech_to_silence = speech_time / max(total_pause, 0.001)

    signals.extend(
        [
            {"signal_tag": "pause_count", "value": float(len(pause_segments)), "source": "derived_acoustic", "reliability": 0.75},
            {"signal_tag": "total_pause_duration_sec", "value": float(total_pause), "source": "derived_acoustic", "reliability": 0.75},
            {"signal_tag": "mean_pause_duration_sec", "value": float(np.mean(pause_durations) if pause_durations else 0.0), "source": "derived_acoustic", "reliability": 0.7},
            {"signal_tag": "long_pause_count", "value": float(long_pause_count), "source": "derived_acoustic", "reliability": 0.75},
            {"signal_tag": "pause_density", "value": float(pause_density), "source": "derived_acoustic", "reliability": 0.75},
            {"signal_tag": "speech_to_silence_ratio", "value": float(speech_to_silence), "source": "derived_acoustic", "reliability": 0.7},
        ]
    )

    # Energy variation.
    if rms_frames.size:
        signals.append({"signal_tag": "energy_mean", "value": float(np.mean(rms_frames)), "source": "derived_acoustic", "reliability": 0.8})
        signals.append({"signal_tag": "energy_std", "value": float(np.std(rms_frames)), "source": "derived_acoustic", "reliability": 0.8})
        signals.append({"signal_tag": "energy_peak", "value": float(np.max(rms_frames)), "source": "derived_acoustic", "reliability": 0.8})

    # Pitch on voiced frames.
    pitch_vals: list[float] = []
    for i, is_voiced in enumerate(voiced):
        if not is_voiced:
            continue
        start = i * hop
        end = min(start + frame_len, len(samples))
        f0 = _estimate_pitch_hz(samples[start:end], sr)
        if 70.0 <= f0 <= 400.0:
            pitch_vals.append(f0)
    if pitch_vals:
        arr = np.array(pitch_vals, dtype=np.float32)
        signals.extend(
            [
                {"signal_tag": "pitch_mean_hz", "value": float(np.mean(arr)), "source": "derived_acoustic", "reliability": 0.65},
                {"signal_tag": "pitch_std_hz", "value": float(np.std(arr)), "source": "derived_acoustic", "reliability": 0.65},
                {"signal_tag": "pitch_range_hz", "value": float(np.max(arr) - np.min(arr)), "source": "derived_acoustic", "reliability": 0.65},
            ]
        )
    else:
        unavailable.append("pitch_estimation_unavailable")

    # Speaking rate proxy: voiced frames per minute (syllable proxy).
    voiced_sec = float(np.sum(voiced) * hop / sr)
    if voiced_sec > 0:
        rate_proxy = (voiced_sec / duration) * 120.0  # arbitrary scale for evidence
        signals.append({"signal_tag": "speaking_rate_proxy", "value": rate_proxy, "source": "derived_acoustic", "reliability": 0.55})
        # Coefficient of variation on RMS voiced regions as rhythm stability proxy.
        if rms_frames.size > 2:
            cv = float(np.std(rms_frames) / (np.mean(rms_frames) + 1e-6))
            signals.append({"signal_tag": "speaking_rate_cv", "value": cv, "source": "derived_acoustic", "reliability": 0.55})
            rhythm_reg = max(0.0, min(1.0, 1.0 - cv))
            signals.append({"signal_tag": "rhythm_regularity", "value": rhythm_reg, "source": "derived_acoustic", "reliability": 0.55})
    else:
        unavailable.append("speaking_rate_unavailable")

    unavailable.append("word_aligned_pauses_unavailable")

    return {
        "signal_observations": signals,
        "pause_segments": [{"start_sec": s, "end_sec": e} for s, e in pause_segments],
        "unavailable_evidence": unavailable,
        "processing_warnings": warnings,
    }
