"""Real pronunciation provider — wav2vec2 espeak-IPA CTC + phonemizer (S5 production).

Observed phonemes come from acoustic CTC inference on normalized 16 kHz mono PCM WAV.
Expected phonemes come from espeak-ng via phonemizer (en-us IPA).
Alignment uses Needleman-Wunsch — never transcript text match alone.
"""

from __future__ import annotations

import asyncio
import io
import logging
import re
import wave
from typing import Any

import numpy as np

from app.core.config import get_settings
from app.services.language_speaking_providers.capabilities import PhonemeAlignmentCapabilities
from app.services.language_speaking_providers.providers import PhonemeAlignmentProvider
from app.services.model_cache import configure_model_cache

logger = logging.getLogger(__name__)
settings = get_settings()

_model_bundle: dict[str, Any] | None = None
_phonemizer_backend = None

# CTC blank/special tokens to skip in decoded output.
_SKIP_LABELS = frozenset({"<pad>", "<s>", "</s>", "<unk>", "|", ""})

# Strip IPA stress/diacritics for alignment comparison.
_STRESS_RE = re.compile(r"[ˈˌːˑ]")


def _resolve_model_id() -> str:
    return (settings.SPEAKING_PRONUNCIATION_MODEL or "facebook/wav2vec2-lv-60-espeak-cv-ft").strip()


def _normalize_phoneme(symbol: str) -> str:
    s = _STRESS_RE.sub("", (symbol or "").strip())
    # espeak model may use ASCII fallbacks
    mapping = {"T": "θ", "D": "ð", "S": "s", "@": "ə", "r": "ɹ"}
    return mapping.get(s, s)


def _decode_wav_bytes(audio_bytes: bytes) -> tuple[np.ndarray, int]:
    """Decode mono PCM WAV to float32 numpy array."""
    if not audio_bytes:
        return np.array([], dtype=np.float32), 16000
    with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)
    if sample_width == 2:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sample_width == 4:
        samples = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"unsupported sample width: {sample_width}")
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return samples, sample_rate


def _configure_espeak_paths() -> None:
    """Best-effort espeak-ng discovery (Windows dev + Linux Docker)."""
    import os
    from pathlib import Path

    if os.environ.get("PHONEMIZER_ESPEAK_LIBRARY"):
        return
    candidates = [
        Path(r"C:\Program Files\eSpeak NG\libespeak-ng.dll"),
        Path(r"C:\Program Files (x86)\eSpeak NG\libespeak-ng.dll"),
        Path("/usr/lib/x86_64-linux-gnu/libespeak-ng.so.1"),
        Path("/usr/lib/libespeak-ng.so.1"),
    ]
    for lib in candidates:
        if lib.is_file():
            os.environ["PHONEMIZER_ESPEAK_LIBRARY"] = str(lib)
            espeak_dir = str(lib.parent)
            path = os.environ.get("PATH", "")
            if espeak_dir not in path:
                os.environ["PATH"] = espeak_dir + os.pathsep + path
            break


def _get_phonemizer():
    global _phonemizer_backend
    if _phonemizer_backend is not None:
        return _phonemizer_backend
    _configure_espeak_paths()
    from phonemizer.backend import EspeakBackend

    _phonemizer_backend = EspeakBackend(
        language="en-us",
        preserve_punctuation=False,
        with_stress=False,
        language_switch="remove-flags",
    )
    return _phonemizer_backend


def _phonemize_word(word: str) -> list[str]:
    w = (word or "").strip().lower()
    if not w:
        return []
    try:
        backend = _get_phonemizer()
        ipa = backend.phonemize([w], strip=True, njobs=1)[0]
    except Exception as exc:
        logger.warning("phonemizer failed for %r: %s", w, exc)
        return []
    # Split IPA string into individual phoneme characters (espeak style).
    chars = [_normalize_phoneme(c) for c in ipa.replace(" ", "") if c.strip()]
    return [c for c in chars if c]


def _phonemize_text(text: str) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """Return flat expected phonemes and per-word phoneme lists."""
    words = [w for w in re.findall(r"[a-zA-Z']+", (text or "").lower()) if w]
    word_phonemes: list[tuple[str, list[str]]] = []
    flat: list[str] = []
    for word in words:
        ph = _phonemize_word(word)
        word_phonemes.append((word, ph))
        flat.extend(ph)
    return flat, word_phonemes


def _load_model_bundle() -> dict[str, Any]:
    global _model_bundle
    if _model_bundle is not None:
        return _model_bundle

    configure_model_cache()
    _configure_espeak_paths()
    import torch
    from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

    model_id = _resolve_model_id()
    logger.info("Loading S5 wav2vec2 pronunciation model=%s device=cpu", model_id)
    processor = Wav2Vec2Processor.from_pretrained(model_id)
    model = Wav2Vec2ForCTC.from_pretrained(model_id)
    model.eval()
    _model_bundle = {
        "processor": processor,
        "model": model,
        "model_id": model_id,
        "torch": torch,
    }
    return _model_bundle


def _ctc_decode_with_timings(
    audio: np.ndarray,
    sample_rate: int,
) -> tuple[list[str], list[tuple[float, float, float]]]:
    """Greedy CTC decode; return phonemes and (start_sec, end_sec, confidence) per token."""
    bundle = _load_model_bundle()
    torch = bundle["torch"]
    processor = bundle["processor"]
    model = bundle["model"]

    if len(audio) == 0:
        return [], []

    target_sr = processor.feature_extractor.sampling_rate
    if sample_rate != target_sr:
        # Simple linear resample when rates differ (S4 should already be 16kHz).
        duration = len(audio) / sample_rate
        new_len = int(duration * target_sr)
        if new_len < 1:
            return [], []
        x_old = np.linspace(0, 1, num=len(audio), endpoint=False)
        x_new = np.linspace(0, 1, num=new_len, endpoint=False)
        audio = np.interp(x_new, x_old, audio).astype(np.float32)
        sample_rate = target_sr

    inputs = processor(audio, sampling_rate=sample_rate, return_tensors="pt", padding=True)
    with torch.no_grad():
        logits = model(inputs.input_values).logits[0]

    probs = torch.softmax(logits, dim=-1)
    pred_ids = torch.argmax(logits, dim=-1).tolist()

    # Frame stride: product of wav2vec2 conv strides (lv-60 => 320 samples @ 16kHz ≈ 20ms).
    conv_stride = getattr(model.config, "conv_stride", [5, 2, 2, 2, 2, 2, 2])
    if isinstance(conv_stride, (list, tuple)):
        stride_samples = 1
        for s in conv_stride:
            stride_samples *= int(s)
    else:
        stride_samples = int(conv_stride or 320)
    frame_stride_sec = float(stride_samples) / float(sample_rate) if sample_rate else 0.02
    if frame_stride_sec <= 0:
        frame_stride_sec = 0.02

    id2token = processor.tokenizer.convert_ids_to_tokens
    phonemes: list[str] = []
    timings: list[tuple[float, float, float]] = []

    prev_id: int | None = None
    run_start: int | None = None
    run_confidences: list[float] = []

    def _flush_run(end_frame: int) -> None:
        nonlocal run_start, run_confidences
        if run_start is None or prev_id is None:
            run_start = None
            run_confidences = []
            return
        token = id2token(prev_id)
        if token in _SKIP_LABELS:
            run_start = None
            run_confidences = []
            return
        ph = _normalize_phoneme(token)
        if not ph:
            run_start = None
            run_confidences = []
            return
        start_sec = run_start * frame_stride_sec
        end_sec = (end_frame + 1) * frame_stride_sec
        conf = float(sum(run_confidences) / len(run_confidences)) if run_confidences else 0.0
        phonemes.append(ph)
        timings.append((start_sec, end_sec, conf))
        run_start = None
        run_confidences = []

    for frame_idx, token_id in enumerate(pred_ids):
        if token_id == prev_id:
            if prev_id is not None:
                run_confidences.append(float(probs[frame_idx, token_id]))
            continue
        _flush_run(frame_idx - 1)
        prev_id = token_id
        run_start = frame_idx
        run_confidences = [float(probs[frame_idx, token_id])]

    _flush_run(len(pred_ids) - 1)
    return phonemes, timings


def _nw_align(
    expected: list[str],
    observed: list[str],
    *,
    match_score: float = 2.0,
    mismatch_score: float = -1.0,
    gap_score: float = -1.0,
) -> list[tuple[str, str, str]]:
    """Needleman-Wunsch: returns list of (expected, observed, operation)."""
    n, m = len(expected), len(observed)
    score = [[0.0] * (m + 1) for _ in range(n + 1)]
    trace = [[None] * (m + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        score[i][0] = score[i - 1][0] + gap_score
        trace[i][0] = ("up",)
    for j in range(1, m + 1):
        score[0][j] = score[0][j - 1] + gap_score
        trace[0][j] = ("left",)

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            match = score[i - 1][j - 1] + (
                match_score if expected[i - 1] == observed[j - 1] else mismatch_score
            )
            delete = score[i - 1][j] + gap_score
            insert = score[i][j - 1] + gap_score
            best = max(match, delete, insert)
            score[i][j] = best
            if best == match:
                trace[i][j] = ("diag",)
            elif best == delete:
                trace[i][j] = ("up",)
            else:
                trace[i][j] = ("left",)

    alignments: list[tuple[str, str, str]] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and trace[i][j] == ("diag",):
            exp, obs = expected[i - 1], observed[j - 1]
            op = "match" if exp == obs else "substitution"
            alignments.append((exp, obs, op))
            i -= 1
            j -= 1
        elif i > 0 and (j == 0 or trace[i][j] == ("up",)):
            alignments.append((expected[i - 1], "", "omission"))
            i -= 1
        else:
            alignments.append(("", observed[j - 1], "insertion"))
            j -= 1
    alignments.reverse()
    return alignments


def _analyze_sync(
    audio_bytes: bytes,
    *,
    reference_text: str,
) -> dict[str, object]:
    model_id = _resolve_model_id()
    warnings: list[str] = []
    unavailable: list[str] = []

    if not audio_bytes:
        return {
            "provider_name": "wav2vec2",
            "model": model_id,
            "provider_version": "transformers-wav2vec2-ctc",
            "processing_version": "s5_wav2vec2",
            "reference_text": reference_text,
            "phoneme_observations": [],
            "word_observations": [],
            "evidence_coverage": 0.0,
            "evidence_reliability": 0.0,
            "unavailable_evidence": ["audio_missing"],
            "processing_warnings": ["audio_missing"],
        }

    ref = (reference_text or "").strip()
    if not ref:
        return {
            "provider_name": "wav2vec2",
            "model": model_id,
            "provider_version": "transformers-wav2vec2-ctc",
            "processing_version": "s5_wav2vec2",
            "reference_text": "",
            "phoneme_observations": [],
            "word_observations": [],
            "evidence_coverage": 0.0,
            "evidence_reliability": 0.0,
            "unavailable_evidence": ["reference_missing"],
            "processing_warnings": ["reference_missing"],
        }

    audio, sample_rate = _decode_wav_bytes(audio_bytes)
    duration_sec = len(audio) / sample_rate if sample_rate else 0.0
    min_conf = float(settings.SPEAKING_PRONUNCIATION_MIN_CONFIDENCE or 0.15)

    if duration_sec < 0.08:
        return {
            "provider_name": "wav2vec2",
            "model": model_id,
            "provider_version": "transformers-wav2vec2-ctc",
            "processing_version": "s5_wav2vec2",
            "reference_text": ref,
            "phoneme_observations": [],
            "word_observations": [],
            "evidence_coverage": 0.0,
            "evidence_reliability": 0.0,
            "unavailable_evidence": ["audio_too_short"],
            "processing_warnings": ["audio_too_short"],
        }

    # Acoustic signal quality gate — low RMS => unreliable evidence.
    rms = float(np.sqrt(np.mean(audio**2))) if len(audio) else 0.0
    if rms < 0.005:
        return {
            "provider_name": "wav2vec2",
            "model": model_id,
            "provider_version": "transformers-wav2vec2-ctc",
            "processing_version": "s5_wav2vec2",
            "reference_text": ref,
            "phoneme_observations": [],
            "word_observations": [],
            "evidence_coverage": 0.0,
            "evidence_reliability": 0.0,
            "unavailable_evidence": ["evidence_unreliable"],
            "processing_warnings": ["low_audio_energy"],
        }

    try:
        observed_phonemes, obs_timings = _ctc_decode_with_timings(audio, sample_rate)
    except Exception as exc:
        logger.exception("CTC decode failed")
        raise RuntimeError(f"pronunciation CTC decode failed: {exc}") from exc

    if not observed_phonemes:
        unavailable.append("phoneme_decode_empty")
        warnings.append("phoneme_decode_empty")

    expected_flat, word_phoneme_map = _phonemize_text(ref)
    if not expected_flat:
        unavailable.append("expected_phonemes_unavailable")
        warnings.append("g2p_failed")

    alignments = _nw_align(expected_flat, observed_phonemes) if expected_flat else []

    # Map observed timing index for substitution/match ops.
    obs_idx = 0
    phoneme_observations: list[dict[str, object]] = []
    position = 0
    word_idx = 0
    word_char_counts = [len(ph) for _, ph in word_phoneme_map]
    char_in_word = 0
    current_word = word_phoneme_map[0][0] if word_phoneme_map else ""

    for exp, obs, op in alignments:
        if word_phoneme_map and word_idx < len(word_phoneme_map):
            current_word = word_phoneme_map[word_idx][0]
        start_sec, end_sec, conf = 0.0, 0.0, 0.0
        if op != "omission" and obs_idx < len(obs_timings):
            start_sec, end_sec, conf = obs_timings[obs_idx]
            obs_idx += 1
        word_final = False
        if word_phoneme_map and word_idx < len(word_phoneme_map):
            char_in_word += 1 if exp else 0
            if exp and char_in_word >= word_char_counts[word_idx]:
                word_final = True
                char_in_word = 0
                word_idx = min(word_idx + 1, len(word_phoneme_map) - 1)

        phoneme_observations.append(
            {
                "expected_phoneme": exp,
                "observed_phoneme": obs,
                "start_sec": start_sec,
                "end_sec": end_sec,
                "alignment_confidence": conf,
                "operation": op,
                "word_reference": current_word,
                "position": position,
                "word_final": word_final,
            }
        )
        position += 1

    # Build word-level observations.
    word_observations: list[dict[str, object]] = []
    for word, exp_ph in word_phoneme_map:
        word_ph_obs = [p for p in phoneme_observations if p.get("word_reference") == word]
        obs_ph = [str(p.get("observed_phoneme") or "") for p in word_ph_obs if p.get("observed_phoneme")]
        confs = [
            float(p.get("alignment_confidence") or 0.0)
            for p in word_ph_obs
            if p.get("alignment_confidence")
        ]
        word_conf = sum(confs) / len(confs) if confs else 0.0
        starts = [float(p.get("start_sec") or 0.0) for p in word_ph_obs]
        ends = [float(p.get("end_sec") or 0.0) for p in word_ph_obs]
        issue_tags: list[str] = []  # Tags assembled in language_speaking_pronunciation layer.
        word_observations.append(
            {
                "word": word,
                "start_sec": min(starts) if starts else 0.0,
                "end_sec": max(ends) if ends else 0.0,
                "expected_phonemes": exp_ph,
                "observed_phonemes": obs_ph,
                "word_confidence": word_conf,
                "issue_tags": issue_tags,
            }
        )

    analyzed = len(expected_flat)
    matched = sum(1 for p in phoneme_observations if p.get("operation") == "match")
    coverage = matched / analyzed if analyzed else 0.0
    confidences = [
        float(p.get("alignment_confidence") or 0.0)
        for p in phoneme_observations
        if p.get("alignment_confidence")
    ]
    reliability = sum(confidences) / len(confidences) if confidences else 0.0
    if reliability < min_conf and phoneme_observations:
        warnings.append("low_alignment_confidence")
        unavailable.append("evidence_unreliable")

    return {
        "provider_name": "wav2vec2",
        "model": model_id,
        "provider_version": "transformers-wav2vec2-ctc",
        "processing_version": "s5_wav2vec2",
        "reference_text": ref,
        "phoneme_observations": phoneme_observations,
        "word_observations": word_observations,
        "evidence_coverage": round(coverage, 4),
        "evidence_reliability": round(reliability, 4),
        "unavailable_evidence": unavailable,
        "processing_warnings": warnings,
    }


class RealPronunciationProvider(PhonemeAlignmentProvider):
    """Production pronunciation via wav2vec2 espeak-IPA CTC + phonemizer G2P."""

    def capabilities(self) -> PhonemeAlignmentCapabilities:
        return PhonemeAlignmentCapabilities(
            supports_forced_alignment=True,
            supports_phoneme_confidence=True,
            min_audio_duration_sec=0.08,
            provider_name="wav2vec2",
        )

    async def align(
        self,
        *,
        audio_bytes: bytes,
        transcript: str,
        reference_text: str = "",
    ) -> dict[str, object]:
        ref = (reference_text or transcript or "").strip()
        timeout = max(1, int(settings.SPEAKING_PRONUNCIATION_TIMEOUT_SECONDS or 120))
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    _analyze_sync,
                    audio_bytes,
                    reference_text=ref,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError as exc:
            raise TimeoutError("Pronunciation analysis timed out") from exc
