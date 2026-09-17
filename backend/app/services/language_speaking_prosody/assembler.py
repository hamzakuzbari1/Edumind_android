"""Assemble canonical SpeakingProsodyEvidenceResult from provider facts (S6)."""

from __future__ import annotations

from app.core.config import get_settings
from app.services.language_speaking_prosody.expression_mapping import normalize_expression_label
from app.services.language_speaking_prosody.issue_taxonomy import (
    ISSUE_FRAGMENTED_RHYTHM,
    ISSUE_FREQUENT_LONG_PAUSES,
    ISSUE_HIGH_PAUSE_DENSITY,
    ISSUE_LOW_ENERGY_VARIATION,
    ISSUE_LOW_PITCH_VARIATION,
    ISSUE_MONOTONE_DELIVERY,
    ISSUE_UNSTABLE_SPEAKING_RATE,
)
from app.services.language_speaking_prosody.skill_mapping import candidate_skills_for_issue
from app.services.language_speaking_prosody.types import (
    ExpressionObservation,
    ProsodyEvidenceSource,
    ProsodyIssueObservation,
    ProsodyProvenance,
    ProsodySignalObservation,
    SpeakingProsodyEvidenceResult,
    TurnSegmentObservation,
)

settings = get_settings()


def _signal_map(raw: dict[str, object]) -> dict[str, tuple[float, str, float]]:
    out: dict[str, tuple[float, str, float]] = {}
    for item in list(raw.get("signal_observations") or []):
        if not isinstance(item, dict):
            continue
        tag = str(item.get("signal_tag") or "")
        if not tag:
            continue
        out[tag] = (
            float(item.get("value") or 0.0),
            str(item.get("source") or ProsodyEvidenceSource.unavailable.value),
            float(item.get("reliability") or 0.0),
        )
    return out


def _classify_issues(signals: dict[str, tuple[float, str, float]]) -> list[ProsodyIssueObservation]:
    issues: list[ProsodyIssueObservation] = []
    pitch_std = signals.get("pitch_std_hz", (0.0, "", 0.0))[0]
    energy_std = signals.get("energy_std", (0.0, "", 0.0))[0]
    pause_density = signals.get("pause_density", (0.0, "", 0.0))[0]
    long_pause_count = signals.get("long_pause_count", (0.0, "", 0.0))[0]
    rate_cv = signals.get("speaking_rate_cv", (0.0, "", 0.0))[0]
    rhythm_reg = signals.get("rhythm_regularity", (1.0, "", 0.0))[0]

    low_pitch_thresh = float(settings.SPEAKING_PROSODY_LOW_PITCH_STD_HZ or 15.0)
    low_energy_thresh = float(settings.SPEAKING_PROSODY_LOW_ENERGY_STD or 0.02)
    high_pause_density = float(settings.SPEAKING_PROSODY_HIGH_PAUSE_DENSITY or 0.35)
    long_pause_min = float(settings.SPEAKING_PROSODY_LONG_PAUSE_SEC or 0.6)
    unstable_rate_cv = float(settings.SPEAKING_PROSODY_UNSTABLE_RATE_CV or 0.45)
    low_rhythm = float(settings.SPEAKING_PROSODY_LOW_RHYTHM_REGULARITY or 0.35)

    def _add(tag: str, reliability: float, source: ProsodyEvidenceSource) -> None:
        issues.append(
            ProsodyIssueObservation(
                issue_tag=tag,
                candidate_skill_ids=candidate_skills_for_issue(tag),
                evidence_reliability=reliability,
                source=source,
            )
        )

    if pitch_std > 0 and pitch_std < low_pitch_thresh:
        _add(ISSUE_LOW_PITCH_VARIATION, 0.7, ProsodyEvidenceSource.derived_acoustic)
        _add(ISSUE_MONOTONE_DELIVERY, 0.65, ProsodyEvidenceSource.derived_acoustic)
    if energy_std > 0 and energy_std < low_energy_thresh:
        _add(ISSUE_LOW_ENERGY_VARIATION, 0.65, ProsodyEvidenceSource.derived_acoustic)
    if pause_density >= high_pause_density:
        _add(ISSUE_HIGH_PAUSE_DENSITY, 0.7, ProsodyEvidenceSource.derived_acoustic)
    if long_pause_count >= 1 and long_pause_min > 0:
        _add(ISSUE_FREQUENT_LONG_PAUSES, 0.7, ProsodyEvidenceSource.derived_acoustic)
    if rate_cv >= unstable_rate_cv:
        _add(ISSUE_UNSTABLE_SPEAKING_RATE, 0.65, ProsodyEvidenceSource.derived_acoustic)
    if rhythm_reg > 0 and rhythm_reg < low_rhythm:
        _add(ISSUE_FRAGMENTED_RHYTHM, 0.65, ProsodyEvidenceSource.derived_acoustic)

    return issues


def assemble_prosody_evidence(
    raw: dict[str, object],
    *,
    audio_id: str,
    session_id: str,
    source_audio_id: str,
) -> SpeakingProsodyEvidenceResult:
    """Convert provider-native prosody dict to canonical S6 result."""
    provenance = ProsodyProvenance(
        provider_name=str(raw.get("provider_name") or "unknown"),
        model_name=str(raw.get("model") or ""),
        provider_version=str(raw.get("provider_version") or ""),
        processing_version=str(raw.get("processing_version") or "s6"),
    )

    expressions: list[ExpressionObservation] = []
    for item in list(raw.get("expression_observations") or []):
        if not isinstance(item, dict):
            continue
        label = str(item.get("provider_label") or "")
        conf = float(item.get("confidence") or 0.0)
        if not label:
            continue
        try:
            src = ProsodyEvidenceSource(str(item.get("source") or ProsodyEvidenceSource.direct_provider.value))
        except ValueError:
            src = ProsodyEvidenceSource.direct_provider
        expressions.append(
            ExpressionObservation(
                provider_label=label,
                normalized_tag=str(item.get("normalized_tag") or normalize_expression_label(label)),
                confidence=conf,
                source=src,
                segment_start_sec=float(item.get("segment_start_sec") or 0.0),
                segment_end_sec=float(item.get("segment_end_sec") or 0.0),
            )
        )

    signals: list[ProsodySignalObservation] = []
    for item in list(raw.get("signal_observations") or []):
        if not isinstance(item, dict):
            continue
        tag = str(item.get("signal_tag") or "")
        if not tag:
            continue
        try:
            src = ProsodyEvidenceSource(str(item.get("source") or ProsodyEvidenceSource.unavailable.value))
        except ValueError:
            src = ProsodyEvidenceSource.unavailable
        signals.append(
            ProsodySignalObservation(
                signal_tag=tag,
                value=float(item.get("value") or 0.0),
                source=src,
                reliability=float(item.get("reliability") or 0.0),
            )
        )

    turn_segments: list[TurnSegmentObservation] = []
    for item in list(raw.get("turn_segments") or []):
        if not isinstance(item, dict):
            continue
        turn_segments.append(
            TurnSegmentObservation(
                start_sec=float(item.get("start_sec") or 0.0),
                end_sec=float(item.get("end_sec") or 0.0),
                speaker_id=str(item.get("speaker_id") or ""),
            )
        )

    signal_map = _signal_map(raw)
    issue_obs = _classify_issues(signal_map)

    candidate_ids: set[str] = set()
    for issue in issue_obs:
        candidate_ids.update(issue.candidate_skill_ids)

    return SpeakingProsodyEvidenceResult(
        audio_id=audio_id,
        session_id=session_id,
        source_audio_id=source_audio_id or audio_id,
        provenance=provenance,
        expression_observations=tuple(expressions),
        signal_observations=tuple(signals),
        issue_observations=tuple(issue_obs),
        turn_segments=tuple(turn_segments),
        candidate_skill_ids=tuple(sorted(candidate_ids)),
        evidence_coverage=float(raw.get("evidence_coverage") or 0.0),
        evidence_reliability=float(raw.get("evidence_reliability") or 0.0),
        unavailable_evidence=tuple(str(u) for u in (raw.get("unavailable_evidence") or []) if u),
        quality_flags=tuple(str(q) for q in (raw.get("quality_flags") or []) if q),
        processing_warnings=tuple(str(w) for w in (raw.get("processing_warnings") or []) if w),
    )
