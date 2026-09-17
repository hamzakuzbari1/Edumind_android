# Speaking S7 — Hybrid Multimodal Evaluation Engine Report

**Date:** 2026-07-12
**Engine version:** `7.0.0`
**Status:** COMPLETE — STOP boundary respected (no S8+ work)

---

## 1. Audit outcome

- `language_speaking_evaluator/` had stub `SpeakingEvaluationEngineResult` v0.1.0 never constructed.
- S7 completes the package: rule engine + Claude educational analyzer + hybrid merge + runtime orchestrator.
- Legacy flat evaluation paths remain frozen and unchanged.

## 2. Architecture

```
Student audio
  → S4 transcript (GPT-4o)
  → S5 pronunciation (wav2vec2)
  → S6 prosody (acoustic derived)
  → rule_engine → SpeakingRuleEvaluationFacts
  → educational_analyzer → SpeakingEducationalFacts
  → hybrid_merge → SpeakingEvaluationEngineResult
```

## 3. Provider / model / version

| Layer | Provider | Model / version |
|-------|----------|-----------------|
| S4 | openai | gpt-4o-transcribe |
| S5 | wav2vec2 | facebook/wav2vec2-lv-60-espeak-cv-ft |
| S6 | acoustic | numpy-derived-prosody-v1 |
| S7 analyzer | claude | claude-sonnet-5 (configurable) |
| S7 engine | hybrid | 7.0.0 |

## 4. Canonical contract

- `SpeakingEvaluationEngineResult` v7.0.0 with IDs, task/goal/CEFR context, `evidence_summary`, 10 dimensions, strengths/weaknesses, revision vs completion separation, educational analysis attachment, candidate skill evidence, explanation, provenance.
- `to_persistence_dict()` + `evaluation_result_from_dict()` roundtrip verified.

## 5. Semantic design

- Rule engine owns acoustic/pronunciation/prosody gates and deterministic task keyword overlap.
- Claude owns semantic interpretation (task, grammar, vocabulary, coherence, goal, observed CEFR estimate).
- LLM never invents phonemes, pitch, or pauses not in evidence summaries.

## 6. Traceability guards

- Acoustic-claim sanitizer drops emotional inferences and flags untraceable pronunciation/prosody prose.
- Parser rejects forbidden decision fields (`pass`, `fail`, `promotion`, `official_cefr`, etc.).

## 7. CEFR design

- `official_cefr_context` passed in only — never mutated.
- `observed_cefr_estimate` from analyzer is educational observation only; stored in `cefr_validation` notes.

## 8. Revision design

- `revision_readiness` from rule gates + merge blockers.
- `single_revision_priority` from analyzer enriches explanation only.

## 9. Readiness vs completion

- `revision_readiness` and `completion_eligibility` are separate dataclasses.
- Completion requires rule task overlap AND edu task score — acoustic strength cannot bypass off-topic responses.

## 10. Candidate skill bridge

- `build_candidate_skill_evidence()` maps S5/S6 `candidate_skill_ids` + task target skills.
- No S2 `apply_observation` / mastery mutation in S7.

## 11. Persistence

Additive JSONB homes (no migration):
- `LanguageSpeakingConversationTurn.evaluation_json["engine_result"]`
- `LanguageSpeakingProgress.ai_evaluation_json["engine_result"]`

## 12. Config

- `SPEAKING_EDUCATIONAL_ANALYZER=claude|mock|off` added to `config.py` and `.env.example`.

## 13. Packages created/updated

**New:** `language_speaking_educational_analyzer/` (types, prompt, parser, mock, analyzer)
**New evaluator modules:** `input_types`, `rule_facts_types`, `rule_engine`, `candidate_skill_evidence`, `hybrid_merge`, `engine`, `facts_deserialize`
**New runtime:** `evaluation_pipeline.process_speaking_evaluation`
**Verifiers:** `verify_speaking_s7_evaluation.py`, `verify_speaking_s7_real_multimodal.py`

## 14. Ownership

- No `ownership.py` changes.
- Evaluator imports only allowed deps; curriculum graph validation in verifiers only.

## 15. Structural verification

**50/50 PASS** — architecture, parser, rule engine, roundtrip, merge guards, skill bridge, evidence codes, scenarios A–T, frozen S0–S6 reruns.

## 16. Real multimodal acceptance

**16/16 PASS** on human fixture:
`test audio/WhatsApp Ptt 2026-07-12 at 11.38.43 AM.ogg`

Provenance printed:
- S4: openai / gpt-4o-transcribe
- S5: wav2vec2 / facebook/wav2vec2-lv-60-espeak-cv-ft
- S6: acoustic / numpy-derived-prosody-v1
- S7: claude / claude-sonnet-5

## 17. Sample real result

- task_response.score=0.353 (not_met)
- pronunciation.score=0.000
- fluency_delivery.score=0.282
- revision_ready=False
- completion_eligible=False
- observed_cefr_estimate=A2 (not official)

## 18. Scenario matrix A–T

All 20 synthetic scenarios PASS with mock analyzer (empty transcript, off-topic, grammar errors, missing S5/S6, force_complete blocked, etc.).

## 19. Frozen regressions

S0, S3, S4, S5, S6 verifiers rerun green from S7 structural script.

## 20. Defects found

- Circular import between `evaluation_result` and `candidate_skill_evidence` — resolved by keeping dataclass in `evaluation_result.py`.
- S0 RESPONSIBILITY docstring missing on new analyzer package — fixed.

## 21. Limitations

- In-engine skill graph validation deferred to verifiers (no evaluator→curriculum edge).
- DB writes deferred to S8 integration boundary.
- Interaction dimension limited for single-turn evaluation.

## 22. No S2/CEFR/stage mutation

Verified: no mastery, official CEFR, learning stage, or progression writes in S7 code path.

## 23. No Writing imports

Evaluator stack has zero imports from `language_writing_*` packages.

## 24. Analyzer failure behavior

Claude failures log warning and return `unavailable_speaking_facts` — never silent mock in production `claude` mode.

## 25. force_complete guard

`force_complete=True` cannot bypass semantic completion gate; blocker recorded when requested but ineligible.

## 26. S8 readiness

S7 delivers a single canonical `SpeakingEvaluationEngineResult` + persistence dict + full multimodal pipeline entrypoint. S8 may wire API persistence, S2 observation application, coach/explainability render-only consumers, and frontend integration.

---

**STOP:** S2 mutation, progression, promotion, lesson generation, EVI, and frontend redesign are out of scope for S7.
