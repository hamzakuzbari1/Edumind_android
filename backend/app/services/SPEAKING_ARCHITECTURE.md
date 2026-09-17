# Speaking System Architecture (S0 Foundation)

This document defines the **target architecture**, **package boundaries**, **dependency rules**,
**data retention policy**, and **legacy freeze policy** for the Speaking skill. S0 establishes
contracts only — no WhisperX, WavLM, SpeechBrain, OpenSMILE, Praat, LiveKit, or new model calls.

---

## Target runtime flow

Batch uploads and future streaming converge on the same canonical path:

```
Browser mic / file upload / (future LiveKit stream)
  → SpeakingAudioSession
  → Audio Frontend (provider orchestration)
  → SpeakingSpeechEvidence
  → Analysis engines (pronunciation, fluency, prosody, educational analyzer)
  → Speaking Rule Engine
  → SpeakingEvaluationEngineResult
  → Coach (render-only) + Explainability + Progression
  → SpeakingSpeechOutputProvider (Supertonic)
```

**Single source of truth:** `SpeakingEvaluationEngineResult` owns pass/fail/readiness gates.
Educational analyzer and coach add facts and copy only — they never decide promotion or official CEFR.

---

## Package layers

| Layer | Packages |
|-------|----------|
| Session | `language_speaking_audio_session` |
| Providers | `language_speaking_providers` |
| Audio | `language_speaking_audio_frontend` |
| Analysis | `language_speaking_pronunciation`, `_fluency`, `_prosody`, `_educational_analyzer` |
| Evaluation | `language_speaking_evaluator` |
| Curriculum | `language_speaking_curriculum`, `_knowledge_model`, `_diagnostic` |
| Planning | `language_speaking_lesson_planner` |
| Generation | `language_speaking_generation` |
| Policy | `language_speaking_interruption` |
| Pedagogy | `language_speaking_coach` |
| Facts | `language_speaking_explainability` |
| Runtime | `language_speaking_evaluation_runtime` |
| Experience | `language_speaking_lesson_experience` |
| Journey | `language_speaking_journey` |
| Progression | `language_speaking_progression`, `_learning_stage`, `_transition_gate`, `_promotion_*`, `_official_promotion` |
| Legacy | `language_speaking_legacy_adapter` |

Shared enums and core types live in `language_speaking/` (not a skill engine).

Full ownership registry: `language_speaking/ownership.py`.

---

## Dependency rules

1. **Providers** may be imported only by `language_speaking_audio_frontend`, `language_speaking_providers`, and `language_speaking_legacy_adapter` — never by coach, journey, or API layers.
2. **Educational analyzer** produces JSON facts only; **rule engine** owns PASS/FAIL/READY/COMPLETE.
3. **Progression engines** consume `SpeakingEvaluationEngineResult` only; never raw audio or provider SDKs.
4. **Coach** consumes evaluation + diagnostic priority; never selects the first STT/grammar error.
5. **Official CEFR** (`official_speaking_cefr`) is writable only by `language_speaking_official_promotion` at runtime (+ initial placement bulk write in `language_progression_service`).
6. **Legacy adapter** is the only package that may import flat legacy modules (`language_conversation_service`, etc.).
7. **Frontend** is render-only — no readiness formulas, stage math, or pronunciation thresholds.
8. **ElevenLabs is excluded** from Speaking speech output; Supertonic is the target provider.

---

## Provider boundaries (S0 contracts)

| Provider ABC | Legacy impl (frozen) | Future impl (post-S3+) |
|--------------|---------------------|------------------------|
| `SpeechTranscriptionProvider` | OpenAI transcribe + faster-whisper | WhisperX adapter (optional) |
| `SpeechEmbeddingProvider` | None | WavLM/HuBERT adapter |
| `PhonemeAlignmentProvider` | None | SpeechBrain / forced alignment |
| `AcousticFeatureProvider` | None (prosody = LLM guess today) | OpenSMILE / Praat adapter |
| `SpeakingEducationalAnalyzerProvider` | Claude via conversation AI service | Structured JSON contract |
| `SpeakingSpeechOutputProvider` | Supertonic via reply TTS service | Supertonic (default) |

Capability dataclasses declare supported controls (voice, rate, delivery metadata). No fake unsupported prosody knobs.

---

## Retention boundaries

| Data class | What it holds | Retention / access |
|------------|---------------|-------------------|
| **Raw audio** | Original WebM/WAV bytes | Short-lived session storage; delete after evidence extraction unless user/consent policy requires longer. Not passed to progression or journey. |
| **SpeakingSpeechEvidence** | Transcript, word timings, phoneme alignments (when available), pause markers, prosody features, embedding refs | Persisted per turn as derived evidence; canonical input to evaluation. Retained for trend/diagnostic use under speaking JSONB buckets (S2+). |
| **SpeakingEvaluationEngineResult** | Dimension facts, criterion statuses, pass/fail gates | Persisted on turn/session rows; sole input to progression, coach priority, explainability. |
| **Skill mastery** | Per-node mastery, confidence, evidence codes | Namespaced under `promotion_readiness_json["speaking"]` (mirror Writing). Not computed from raw audio directly. |
| **Official CEFR** | `official_speaking_cefr` on `language_progression` | Updated only by official promotion engine after SPA PASS (S18+). |

Progression must never read provider SDK outputs or raw audio — only canonical evaluation and mastery records.

---

## Legacy freeze policy

Flat legacy modules under `app/services/` are **frozen** — no new features, no new imports from new speaking packages except via `language_speaking_legacy_adapter`.

| Legacy module | Canonical target (S7+) |
|---------------|------------------------|
| `language_transcription_service` | `SpeechTranscriptionProvider` |
| `language_pronunciation_service` | Pronunciation analysis engine |
| `language_conversation_service` | `language_speaking_evaluation_runtime` |
| `language_conversation_ai_service` | `SpeakingEducationalAnalyzerProvider` |
| `language_speaking_feedback_service` | Evaluation runtime (prompt path) |
| `language_speaking_service` | Lesson experience |
| `language_speaking_evolution_service` | Progression (migrate off `analytics.speaking_level`) |
| `language_speaking_coach_service` | Coach (**unwired** — replace with `language_speaking_coach`) |
| `language_shadowing_service` | Lesson experience (shadowing) |
| `language_conversation_scenario_service` | Lesson experience (scenarios) |
| `language_reply_tts_service` | `SpeakingSpeechOutputProvider` |
| `speaking_coach_service` | Standalone `/speaking/coach` API (separate from main flow) |

S0 adapter may be a no-op passthrough. S7+ routes turns through canonical evaluation while legacy HTTP routes remain stable.

---

## Runtime blockers (hotfix track — not fixed in S0)

These are verified production risks. Fix in a small hotfix PR before or alongside S1; do not implement in S0.

| ID | Location | Issue | Impact |
|----|----------|-------|--------|
| `mastery_settings_attr` | `language_speaking_evolution_service.py:148` | Reads `LANGUAGE_MASTERY_WINDOW` but config defines `LANGUAGE_MASTERY_WINDOW_SIZE` | Conversation level update may raise `AttributeError` every turn |
| `tts_signature_mismatch` | `language_conversation_service.py:325` | Calls `synthesize_english_reply(segments=, voice=)` but wrapper accepts `text=` only | Sync reply TTS may fail with `TypeError` |
| `dual_level_system` | `language_speaking_evolution_service` | Writes `analytics.speaking_level`; `official_speaking_cefr` unused by speaking runtime | Inconsistent CEFR across modules until S15–S18 |
| `dead_coach_module` | `language_speaking_coach_service.py` | Rich coach logic never called from main submit flow | Confusion for implementers; wasted prior work |

Also tracked in `language_speaking_legacy_adapter.adapter.KNOWN_RUNTIME_BLOCKERS`.

---

## S0 scope vs later phases

**S0 (this foundation):** Package skeleton, enums, ownership DAG, provider ABCs, canonical type stubs, legacy adapter interface, official CEFR ownership guard, this document, `verify_speaking_s0_architecture.py`.

**Not in S0:** Model implementations, skill graph data, frontend changes, progression wiring, new API routes, phoneme engines.

**S1 readiness:** Do not start S1 until S0 verification passes, legacy boundary is frozen, and hotfix blockers are fixed or explicitly shimmed.

See the S0 audit plan for the full S0–S21 roadmap.
