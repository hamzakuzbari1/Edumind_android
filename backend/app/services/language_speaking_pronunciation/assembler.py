"""Assemble canonical SpeakingPronunciationEvidenceResult from provider facts (S5)."""

from __future__ import annotations

from app.services.language_speaking_pronunciation.issue_taxonomy import (
    classify_phoneme_omission,
    classify_phoneme_substitution,
)
from app.services.language_speaking_pronunciation.skill_mapping import candidate_skills_for_issue
from app.services.language_speaking_pronunciation.types import (
    PhonemeAlignmentOperation,
    PhonemeObservation,
    PronunciationIssueObservation,
    PronunciationProvenance,
    PronunciationReferenceSource,
    SpeakingPronunciationEvidenceResult,
    WordPronunciationObservation,
)


def _map_operation(raw: str) -> PhonemeAlignmentOperation:
    try:
        return PhonemeAlignmentOperation(raw)
    except ValueError:
        if raw in {"sub", "substitute"}:
            return PhonemeAlignmentOperation.substitution
        if raw in {"del", "delete", "omit"}:
            return PhonemeAlignmentOperation.omission
        if raw in {"ins", "insert"}:
            return PhonemeAlignmentOperation.insertion
        return PhonemeAlignmentOperation.match


def assemble_pronunciation_evidence(
    raw: dict[str, object],
    *,
    audio_id: str,
    session_id: str,
    reference_source: PronunciationReferenceSource,
    reference_text: str,
) -> SpeakingPronunciationEvidenceResult:
    """Convert provider-native pronunciation dict to canonical S5 result."""
    provenance = PronunciationProvenance(
        provider_name=str(raw.get("provider_name") or "unknown"),
        model_name=str(raw.get("model") or ""),
        provider_version=str(raw.get("provider_version") or ""),
        processing_version=str(raw.get("processing_version") or "s5"),
        reference_source=reference_source,
    )

    phoneme_obs: list[PhonemeObservation] = []
    word_obs: list[WordPronunciationObservation] = []
    issue_obs: list[PronunciationIssueObservation] = []
    seen_issue_keys: set[tuple[str, str, str, str]] = set()
    word_issue_tags: dict[str, list[str]] = {}

    for item in list(raw.get("phoneme_observations") or []):
        if not isinstance(item, dict):
            continue
        op = _map_operation(str(item.get("operation") or "match"))
        po = PhonemeObservation(
            expected_phoneme=str(item.get("expected_phoneme") or ""),
            observed_phoneme=str(item.get("observed_phoneme") or ""),
            start_sec=float(item.get("start_sec") or 0.0),
            end_sec=float(item.get("end_sec") or 0.0),
            alignment_confidence=float(item.get("alignment_confidence") or 0.0),
            operation=op,
            word_reference=str(item.get("word_reference") or ""),
            position=int(item.get("position") or 0),
        )
        phoneme_obs.append(po)

        word_ref = po.word_reference
        issue_tag: str | None = None
        if op == PhonemeAlignmentOperation.substitution:
            issue_tag = classify_phoneme_substitution(po.expected_phoneme, po.observed_phoneme)
        elif op == PhonemeAlignmentOperation.omission:
            issue_tag = classify_phoneme_omission(
                po.expected_phoneme,
                po.observed_phoneme,
                word_final=bool(item.get("word_final")),
            )
        if issue_tag:
            key = (issue_tag, word_ref, po.expected_phoneme, po.observed_phoneme)
            if key not in seen_issue_keys:
                seen_issue_keys.add(key)
                issue_obs.append(
                    PronunciationIssueObservation(
                        issue_tag=issue_tag,
                        word_reference=word_ref,
                        expected_phoneme=po.expected_phoneme,
                        observed_phoneme=po.observed_phoneme,
                        candidate_skill_ids=candidate_skills_for_issue(issue_tag),
                        evidence_reliability=po.alignment_confidence,
                    )
                )
            if word_ref:
                tags = word_issue_tags.setdefault(word_ref, [])
                if issue_tag not in tags:
                    tags.append(issue_tag)

    for item in list(raw.get("word_observations") or []):
        if not isinstance(item, dict):
            continue
        word = str(item.get("word") or "")
        tags = tuple(word_issue_tags.get(word) or item.get("issue_tags") or [])
        tags = tuple(str(t) for t in tags if t)
        word_obs.append(
            WordPronunciationObservation(
                word=word,
                start_sec=float(item.get("start_sec") or 0.0),
                end_sec=float(item.get("end_sec") or 0.0),
                expected_phonemes=tuple(str(p) for p in (item.get("expected_phonemes") or [])),
                observed_phonemes=tuple(str(p) for p in (item.get("observed_phonemes") or [])),
                phoneme_observations=tuple(
                    p
                    for p in phoneme_obs
                    if p.word_reference == str(item.get("word") or "")
                ),
                word_confidence=float(item.get("word_confidence") or 0.0),
                issue_tags=tags,
            )
        )

    coverage = float(raw.get("evidence_coverage") or 0.0)
    reliability = float(raw.get("evidence_reliability") or 0.0)
    unavailable = tuple(str(u) for u in (raw.get("unavailable_evidence") or []) if u)
    warnings = tuple(str(w) for w in (raw.get("processing_warnings") or []) if w)

    return SpeakingPronunciationEvidenceResult(
        audio_id=audio_id,
        session_id=session_id,
        reference_source=reference_source,
        reference_text=reference_text,
        provenance=provenance,
        analyzed_words=tuple(word_obs),
        phoneme_observations=tuple(phoneme_obs),
        issue_observations=tuple(issue_obs),
        evidence_coverage=coverage,
        evidence_reliability=reliability,
        unavailable_evidence=unavailable,
        processing_warnings=warnings,
    )
