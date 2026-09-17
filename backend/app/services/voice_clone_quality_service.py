"""Voice clone quality scoring and rejection rules."""

from __future__ import annotations

import json
import logging
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.core.config import get_settings
from app.services.voice_service import _load_audio_mono_16k

logger = logging.getLogger(__name__)
settings = get_settings()

PREVIEW_SENTENCE = "مرحباً، أنا معلمك الذكي. سأشرح لك الدرس بأسلوبي المعتاد."

TIER_EXCELLENT = "excellent"
TIER_GOOD = "good"
TIER_FAIR = "fair"
TIER_POOR = "poor"
TIER_RE_RECORD = "re_record_required"

TIER_LABELS_AR = {
    TIER_EXCELLENT: "ممتاز",
    TIER_GOOD: "جيد",
    TIER_FAIR: "مقبول",
    TIER_POOR: "ضعيف",
    TIER_RE_RECORD: "يلزم إعادة التسجيل",
}


@dataclass
class VoiceQualityReport:
    quality_score: float = 0.0
    quality_tier: str = TIER_RE_RECORD
    quality_tier_label: str = TIER_LABELS_AR[TIER_RE_RECORD]
    transcript_quality: float = 0.0
    noise_score: float = 0.0
    speech_score: float = 0.0
    clone_confidence: float | None = None
    snr_db: float = 0.0
    silence_ratio: float = 0.0
    arabic_ratio: float = 0.0
    rejection_reasons: list[str] = field(default_factory=list)
    passed_auto_gate: bool = False
    production_ready: bool = False
    preview_audio_path: str | None = None

    def to_details_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


def classify_quality_tier(score: float) -> tuple[str, str]:
    if score >= 85:
        return TIER_EXCELLENT, TIER_LABELS_AR[TIER_EXCELLENT]
    if score >= 72:
        return TIER_GOOD, TIER_LABELS_AR[TIER_GOOD]
    if score >= 58:
        return TIER_FAIR, TIER_LABELS_AR[TIER_FAIR]
    if score >= 45:
        return TIER_POOR, TIER_LABELS_AR[TIER_POOR]
    return TIER_RE_RECORD, TIER_LABELS_AR[TIER_RE_RECORD]


def _load_audio_mono(path: Path):
    return _load_audio_mono_16k(path)


def score_transcript_quality(transcript: str) -> tuple[float, list[str]]:
    """0–100 transcript suitability for persona + clone QA."""
    reasons: list[str] = []
    text = (transcript or "").strip()
    if len(text) < 15:
        return 0.0, ["نص قصير جداً — لم يُتعرّف على كلام واضح"]

    tokens = re.findall(r"[\w\u0600-\u06FF]+", text.lower())
    if not tokens:
        return 0.0, ["لا يوجد كلمات م recognizable في النص"]

    arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
    alpha = sum(1 for c in text if c.isalpha())
    arabic_ratio = arabic_chars / max(alpha, 1)

    counts = Counter(tokens)
    top_token, top_freq = counts.most_common(1)[0]
    repeat_ratio = top_freq / len(tokens)

    short_latin = sum(1 for t in tokens if re.fullmatch(r"[a-z]{1,3}", t))
    latin_noise_ratio = short_latin / len(tokens)

    digit_ratio = sum(1 for c in text if c.isdigit()) / max(len(text), 1)

    if repeat_ratio >= 0.22 and len(top_token) <= 4:
        reasons.append(f"تكرار غير طبيعي للكلمة «{top_token}»")
    if latin_noise_ratio >= 0.25:
        reasons.append("نص يحتوي حروفاً لاتينية/رموزاً غير مفهومة")
    if arabic_ratio < 0.35:
        reasons.append("نسبة العربية منخفضة في النص المستخرج")
    if digit_ratio > 0.08:
        reasons.append("نسبة أرقام عالية في النص")

    score = 40.0
    score += min(35.0, arabic_ratio * 40.0)
    score += min(15.0, math.log1p(len(tokens)) * 3.0)
    score -= repeat_ratio * 45.0
    score -= latin_noise_ratio * 50.0
    score -= digit_ratio * 80.0

    if repeat_ratio >= 0.3 and len(top_token) <= 4:
        score = min(score, 20.0)

    return max(0.0, min(100.0, round(score, 1))), reasons


def analyze_audio_signal(path: Path) -> tuple[float, float, float, float, list[str]]:
    """Returns noise_score, speech_score, snr_db, silence_ratio, reasons (0–100 scales)."""
    reasons: list[str] = []
    try:
        audio, _sr = _load_audio_mono(path)
    except Exception as exc:
        logger.warning("Audio analysis failed for %s: %s", path, exc)
        return 0.0, 0.0, 0.0, 1.0, ["تعذر تحليل الملف الصوتي"]

    import numpy as np

    if audio.size == 0:
        return 0.0, 0.0, 0.0, 1.0, ["ملف صوتي فارغ"]

    peak = float(np.max(np.abs(audio)))
    if peak > 0.99:
        reasons.append("تشبع في الإشارة — قد يكون الصوت مشوّهاً")
    if peak < 0.02:
        reasons.append("مستوى الصوت منخفض جداً")

    hop = max(1, len(audio) // 120)
    rms_vals = [
        float(np.sqrt(np.mean(audio[i : i + hop] ** 2)))
        for i in range(0, len(audio) - hop, hop)
    ]
    if not rms_vals:
        return 0.0, 0.0, 0.0, 1.0, ["لا توجد بيانات كافية للتحليل"]

    silence_threshold = max(0.008, float(np.percentile(rms_vals, 20)) * 0.6)
    silent = sum(1 for r in rms_vals if r < silence_threshold)
    silence_ratio = silent / len(rms_vals)

    active = [r for r in rms_vals if r >= silence_threshold]
    if not active:
        return 0.0, 0.0, 0.0, silence_ratio, ["التسجيل صامت تقريباً"]

    signal_rms = float(np.mean(active))
    noise_floor = float(np.percentile(rms_vals, 15)) or 1e-6
    snr_db = 20.0 * math.log10(max(signal_rms, 1e-6) / max(noise_floor, 1e-6))

    # Speech consistency: lower variance in active RMS = more stable
    active_std = float(np.std(active))
    consistency = 1.0 - min(1.0, active_std / max(signal_rms, 1e-6))
    speech_score = max(0.0, min(100.0, consistency * 100.0))

    # Noise score from SNR + silence
    snr_component = max(0.0, min(100.0, (snr_db - 8.0) * 4.5))
    silence_penalty = silence_ratio * 55.0
    noise_score = max(0.0, min(100.0, snr_component - silence_penalty + 15.0))

    if silence_ratio > 0.45:
        reasons.append("فترات صمت طويلة في التسجيل")
    if snr_db < 12:
        reasons.append("ضجيج خلفية مرتفع")
    if speech_score < 45:
        reasons.append("تفاوت كبير في مستوى الكلام")

    return (
        round(noise_score, 1),
        round(speech_score, 1),
        round(snr_db, 1),
        round(silence_ratio, 3),
        reasons,
    )


def _envelope_correlation(reference: Path, preview: Path) -> float:
    """0-100 similarity proxy between reference timbre envelope and generated preview."""
    try:
        ref, _ = _load_audio_mono(reference)
        prev, _ = _load_audio_mono(preview)
    except Exception:
        return 0.0

    import numpy as np

    hop = 1600  # ~100ms at 16kHz

    def envelope(signal: np.ndarray) -> np.ndarray:
        vals = [
            float(np.sqrt(np.mean(signal[i : i + hop] ** 2)))
            for i in range(0, len(signal) - hop, hop)
        ]
        if not vals:
            return np.zeros(1)
        arr = np.asarray(vals, dtype=np.float32)
        return (arr - arr.mean()) / (arr.std() + 1e-8)

    ea = envelope(ref)
    eb = envelope(prev)
    n = min(len(ea), len(eb))
    if n < 4:
        return 0.0
    corr = float(np.dot(ea[:n], eb[:n]) / n)
    return max(0.0, min(100.0, round((corr + 1.0) * 50.0, 1)))


def compute_overall_quality_score(
    *,
    transcript_quality: float,
    noise_score: float,
    speech_score: float,
    duration_seconds: float,
) -> float:
    duration_factor = 1.0
    min_sec = float(settings.VOICE_SAMPLE_MIN_SECONDS)
    if duration_seconds < min_sec + 5:
        duration_factor = 0.92
    elif duration_seconds >= min_sec + 20:
        duration_factor = 1.05

    raw = (
        transcript_quality * 0.35
        + noise_score * 0.30
        + speech_score * 0.25
        + min(100.0, duration_seconds) * 0.10
    ) * duration_factor
    return max(0.0, min(100.0, round(raw, 1)))


def estimate_clone_confidence(
    *,
    reference_path: Path,
    preview_path: Path | None,
    quality_score: float,
    transcript_quality: float,
) -> float | None:
    if preview_path and preview_path.exists():
        envelope_sim = _envelope_correlation(reference_path, preview_path)
        combined = envelope_sim * 0.55 + quality_score * 0.25 + transcript_quality * 0.20
        return max(0.0, min(100.0, round(combined, 1)))

    # Heuristic-only fallback (never production-grade)
    heuristic = quality_score * 0.5 + transcript_quality * 0.5
    return max(0.0, min(55.0, round(heuristic * 0.55, 1)))


def evaluate_rejection(
    report: VoiceQualityReport,
) -> None:
    """Populate rejection_reasons and passed_auto_gate."""
    min_tq = float(settings.VOICE_CLONE_MIN_TRANSCRIPT_QUALITY)
    min_q = float(settings.VOICE_CLONE_AUTO_REJECT_QUALITY)
    min_conf = float(settings.VOICE_CLONE_MIN_CLONE_CONFIDENCE)

    if report.transcript_quality < min_tq:
        report.rejection_reasons.append(
            "جودة النص المستخرج منخفضة — سجّل مرة أخرى وتحدّث بوضوح بالعربية"
        )
    if report.quality_score < min_q:
        report.rejection_reasons.append("جودة العينة الصوتية منخفضة جداً — يلزم إعادة التسجيل")
    if report.noise_score < 40:
        report.rejection_reasons.append("ضجيج أو صمت زائد — استخدم مكاناً هادئاً وميكروفوناً أوضح")
    if report.speech_score < 35:
        report.rejection_reasons.append("الكلام غير متسق في التسجيل")
    if report.quality_tier == TIER_RE_RECORD:
        report.rejection_reasons.append("العينة غير مناسبة لاستنساخ الصوت")

    if report.clone_confidence is not None and report.clone_confidence < min_conf:
        if settings.ENABLE_TTS:
            report.rejection_reasons.append(
                f"ثقة الاستنساخ منخفضة ({int(report.clone_confidence)}%) — جرّب تسجيلاً أوضح"
            )

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for r in report.rejection_reasons:
        if r not in seen:
            seen.add(r)
            unique.append(r)
    report.rejection_reasons = unique

    report.passed_auto_gate = len(report.rejection_reasons) == 0
    report.production_ready = False


def is_production_ready_sample(
    *,
    processing_status: str,
    quality_score: float | None,
    clone_confidence: float | None,
    teacher_accepted: bool,
) -> bool:
    if processing_status != "ready" or not teacher_accepted:
        return False
    if quality_score is None or clone_confidence is None:
        return False
    return (
        quality_score >= float(settings.VOICE_CLONE_MIN_QUALITY_SCORE)
        and clone_confidence >= float(settings.VOICE_CLONE_MIN_CLONE_CONFIDENCE)
    )


async def analyze_voice_sample(
    path: Path,
    *,
    transcript: str,
    duration_seconds: float,
    sample_id: int,
) -> VoiceQualityReport:
    """Full quality pipeline with optional generated-preview comparison."""
    report = VoiceQualityReport()

    tq, tq_reasons = score_transcript_quality(transcript)
    report.transcript_quality = tq
    report.rejection_reasons.extend(tq_reasons)

    noise, speech, snr, silence, audio_reasons = analyze_audio_signal(path)
    report.noise_score = noise
    report.speech_score = speech
    report.snr_db = snr
    report.silence_ratio = silence
    report.rejection_reasons.extend(audio_reasons)

    report.quality_score = compute_overall_quality_score(
        transcript_quality=tq,
        noise_score=noise,
        speech_score=speech,
        duration_seconds=duration_seconds,
    )
    tier, tier_label = classify_quality_tier(report.quality_score)
    report.quality_tier = tier
    report.quality_tier_label = tier_label

    preview_path: Path | None = None

    report.clone_confidence = estimate_clone_confidence(
        reference_path=path,
        preview_path=preview_path,
        quality_score=report.quality_score,
        transcript_quality=report.transcript_quality,
    )

    evaluate_rejection(report)
    return report
