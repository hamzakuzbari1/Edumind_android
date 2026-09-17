# Speaking Audio Frontend Architecture (S3)

**Phase:** S3 — Audio Frontend Contracts (architecture only)
**Status:** Complete
**Frozen layers:** S0 (architecture), S1 (skill graph), S2 (knowledge model) — do not modify

---

## Target runtime flow

```
Voice Input (browser mic / file upload / future LiveKit stream)
    ↓
SpeakingAudioArtifact (raw)
    ↓
Normalization boundary → NormalizedAudioArtifact
    ↓
Provider orchestration (future S4+ implementations)
    ├── SpeechTranscriptionProvider  → TranscriptEvidence
    ├── SpeechEmbeddingProvider      → SpeechEmbeddingEvidence
    ├── PhonemeAlignmentProvider     → PhonemeAlignmentEvidence
    └── AcousticFeatureProvider      → ProsodyFeatureEvidence
    ↓
SpeakingAudioEvidenceBundle
    ↓
Future S4–S7 Analysis Engines
    ├── Pronunciation Assessment
    ├── Fluency Analysis
    ├── Grammar Analysis
    ├── Vocabulary Tracking
    ├── Conversation State
    └── Student Knowledge Model (S2 — via SpeakingSkillEvidenceObservation in S7)
    ↓
Future Teaching Planner → Lesson Generator → Expressive TTS
```

---

## Ownership

| Package | Owns |
|---------|------|
| `language_speaking_audio_session` | Session record, lifecycle state machine |
| `language_speaking_audio_frontend` | Audio artifacts, normalization contracts, evidence families, evidence bundle assembly |
| `language_speaking_providers` | Provider ABCs and capability dataclasses (S0, frozen) |
| `language_speaking_legacy_adapter` | Legacy → canonical mapping gateway (S0, frozen) |

**Dependency rules:**
- `language_speaking_audio_frontend` may import only `language_speaking_providers` (+ shared infra).
- `language_speaking_audio_session` has no speaking-package dependencies.
- Educational packages (evaluator, coach, knowledge_model) must NOT import audio frontend or provider SDKs.
- S2 knowledge model receives audio-derived data only via `SpeakingSkillEvidenceObservation` (S7 bridge).

---

## Canonical contracts

### Raw audio input
`SpeakingAudioArtifact` / `SpeakingAudioInput` — metadata + storage reference only. No raw bytes in educational objects.

### Normalization
`NormalizedAudioArtifact` — mono PCM/WAV at 16 kHz target. Contract only in S3; ffmpeg processing deferred to S4+.

### Session lifecycle
`SpeakingAudioSessionRecord` with `SpeakingAudioLifecycleState`:
`created → uploading → uploaded → normalizing → ready → processing → processed`
with `failed` and `expired` reachable from any active state.

### Evidence families
Four provider-neutral families: `TranscriptEvidence`, `SpeechEmbeddingEvidence`, `PhonemeAlignmentEvidence`, `ProsodyFeatureEvidence`.

### Evidence bundle
`SpeakingAudioEvidenceBundle` — one bundle per audio clip with explicit availability map. Missing capability is explicit (None + availability=false), never faked.

---

## Provider capability composition

No single provider supports everything. Future composition examples:

| Provider | Capabilities |
|----------|-------------|
| WhisperX | transcription, word_timestamps, segment_timestamps, phoneme_alignment |
| WavLM / HuBERT | speech_embeddings |
| SpeechBrain | phoneme_alignment, pronunciation_features |
| OpenSMILE / Praat | pitch, energy, pauses, rhythm, stress, intonation |
| LiveKit | streaming transport |

Capability discovery via `ProviderCapabilityDescriptor` + `compute_evidence_availability()`.

---

## Provenance

Every evidence family preserves: `provider_name`, `model_name`, `provider_version`, `processing_version`, `generated_at`. Downstream engines consume canonical fields, not raw provider responses.

---

## Quality / warnings

`AudioEvidenceQualityFlag` — evidence reliability context only. Must NOT directly decide student mastery. Examples: `low_audio_quality`, `alignment_unavailable`, `partial_processing`.

---

## Retention and privacy boundaries

| Asset | Retention |
|-------|-----------|
| Raw audio | Short-lived. Delete after evidence extraction. |
| Normalized audio | Short-lived. Delete on session expiry. |
| Derived evidence | Long-lived. Persisted as bundle / SpeakingSpeechEvidence. |
| Embeddings | Opaque `embedding_reference` only. No raw vectors in educational objects. |
| Ownership | All artifacts scoped to `student_id` + `session_id`. |

See `legacy_mapping.py` → `AUDIO_RETENTION_BOUNDARIES` for full specification.

---

## Legacy boundary

Legacy speaking modules remain running. Mapping documented in:
- `language_speaking_legacy_adapter` (S0 frozen gateway)
- `language_speaking_audio_frontend/legacy_mapping.py` (S3 contract map)

No UI migration. No endpoint replacement. No hotfixes to unrelated legacy issues.

### Known runtime blockers (documented, not fixed in S3)
1. `mastery_settings_attr` — evolution service reads wrong config attr
2. `tts_signature_mismatch` — conversation service passes wrong kwargs to TTS wrapper
3. `dual_level_system` — analytics.speaking_level vs official_speaking_cefr inconsistency

---

## S3 scope boundaries

**In S3:** Contracts, validators, session lifecycle, capability discovery, bundle assembly, legacy mapping documentation.

**Not in S3:** Provider implementations (WhisperX, WavLM, SpeechBrain, OpenSMILE, Praat, LiveKit), ffmpeg processing, pronunciation/fluency scoring, evaluation, progression, lesson generation, frontend changes, S2 knowledge model changes.

---

## S4 readiness

S3 provides the contracts that S4 (provider implementations) will plug into. S4 may implement:
- Legacy transcription adapter (`language_transcription_service` → `SpeechTranscriptionProvider`)
- Normalization pipeline (ffmpeg → `NormalizedAudioArtifact`)
- Provider composition orchestrator in audio frontend

S4 must NOT modify S0/S1/S2 frozen layers or S3 contracts without a proven blocking defect.
