# Speaking S8 — Canonical Evaluation Evidence to Knowledge Model Mutation Report

**Date:** 2026-07-12
**Bridge version:** `8.0.0`
**Status:** COMPLETE — STOP boundary respected (no S9 / CEFR / stage / promotion / frontend)

---

## 1. Audit findings

- S7 produced `candidate_skill_evidence` but **nothing mapped it into S2** before S8.
- `process_completed_live_turn` ran S4→S7 then `invalidate_live_context` and returned — Alex never saw updated learner state from live turns.
- `apply_observations_batch` rolls back the **entire** batch on first hard failure — bridge must pre-filter unknown skills and insufficient dimension overlap.
- Live path does **not** persist `engine_result` to DB (unchanged); S7.6 context reads S2 + optional persisted S7 only.

## 2. Scope decisions (confirmed)

- S8 **translates** existing S7 canonical facts into S2 observations only — no second evaluator.
- No S7 contract change (no proven blocker).
- Adaptive weak→improved proof uses **controlled** `SpeakingEvaluationEngineResult` fixtures + **real PostgreSQL** S2 mutation.
- Separate runtime wiring check proves `process_completed_live_turn` end-to-end with mocked S7 + real DB flush.

## 3. Ownership (additive, DAG-legal)

- Extended `language_speaking_evaluation_runtime` deps: `language_speaking_curriculum`, `language_speaking_knowledge_model`.
- Layer 11 → layer 5 import is legal; no `PACKAGE_LAYER` change.
- Description updated to mention S7→S2 knowledge bridge.
- No new package.

## 4. Bridge module layout

| File | Role |
|------|------|
| `knowledge_bridge_types.py` | `SpeakingKnowledgeMutationBridgeResult`, `SpeakingKnowledgeMutationStatus`, `SkippedCandidateEvidence` |
| `knowledge_bridge.py` | `build_speaking_skill_observations`, `apply_speaking_evaluation_to_knowledge_model` |

## 5. Single production mutation entry point

- **Only** `apply_speaking_evaluation_to_knowledge_model(db, …)` mutates S2 from live evaluation.
- Called from `process_completed_live_turn` when `db` is provided — after S7 success, **before** `invalidate_live_context`.

## 6. Reuse-only mapping (no re-evaluation)

Iterates `evaluation.candidate_skill_evidence` verbatim for:

- `performance`, `confidence`, `success`, `mistake_tags`, `evidence_dimensions`, `target_skill`, `communicative_impact`

Mints only:

- `observation_id` (deterministic SHA256)
- `observed_at` (= `evaluation.evaluated_at`)
- `context_id` (= `turn_reference` / live turn id)

## 7. Observation ID rule

```
observation_id = "obs-" + sha256(f"{student_id}:{session_id}:{turn_reference}:{engine_version}:{skill_id}:{source_dimension}")[:20]
```

Stable across same-turn retries (idempotent via `model.applied_observation_ids`); distinct turns → distinct IDs.

## 8. Context ID rule

- `context_id = turn_reference` = `live_turn_id` (not ephemeral `evaluation_id`).
- Same-turn retry → same context (no inflation).
- Documented in `knowledge_bridge.py` module docstring.

## 9. Pre-filter (batch-rollback safety)

Before `apply_observations_batch`:

- Unknown `skill_id` → `unknown_skill_ids` + `skipped_candidate_evidence` (never mutated).
- Empty or insufficient dimension overlap vs S1 `evidence_requirements` → `unavailable_dimensions` (no fake observation).

## 10. Dimension overlap examples (verified)

| Candidate source | Dimensions | `pattern:word_stress` |
|------------------|------------|------------------------|
| pronunciation | `phoneme_alignment`, `pronunciation_confidence` | **accepted** (≥2 overlap) |
| fluency_delivery | `pauses`, `speaking_rate`, `rhythm` | **rejected** (0 overlap with word evidence) |
| task_response | `semantic_task_response`, `meaning_success` | **rejected** (cannot fake pronunciation) |

## 11. Mutation status enum

`applied | no_observations | skipped_all | mutation_failed | s7_unavailable`

Surfaced on `LiveTurnEvaluationResult.mutation_status` and API `SpeakingLiveTurnOut.mutation_status`.

## 12. Runtime integration (`live_runtime.py`)

- Added `db: AsyncSession | None = None` to `process_completed_live_turn`.
- Order: S7 success → S8 mutate (if db) → `invalidate_live_context` → return.
- S7 failure: early return unchanged (no mutation).
- Mutation failure: catch, set `mutation_status=mutation_failed`, **preserve successful S7 result**.

## 13. API integration (`language_speaking_live.py`)

- `speaking_live_turn`: passes `db=db` into `process_completed_live_turn`.
- Default `target_skill_ids` changed from `("pattern:word_stress",)` to `()` — `target_skill` false unless real task target.
- Response includes `mutation_status`.

## 14. Isolation (unchanged, proven)

| Path | Mutates S2? |
|------|-------------|
| `dispatch_evi_tool` / `get_student_speaking_context` | **No** (read-only) |
| S7 evaluation failure | **No** |
| `process_completed_live_turn` without `db` | **No** |
| Completed authenticated turn with `db` | **Yes** |

## 15. Forbidden writes (proven on real PostgreSQL)

Unchanged after S8 mutations:

- `official_speaking_cefr`, `learning_stage_speaking`, `promotion_readiness_score`, `version`
- Sibling JSONB: `writing`, `listening_official_promotions`, `speaking.readiness`
- No direct `promotion_readiness_json` top-level CEFR/stage edits outside `speaking.knowledge_model` bucket

## 16. Idempotency (real PostgreSQL)

- Same turn + same evaluation retried → `evidence_count` stable.
- `applied_observation_ids` deduplicates deterministic `observation_id`.

## 17. Adaptive loop proof (controlled S7 + real S2)

**Turn 1 (weak):** `performance=0.2`, `success=False` on `pattern:word_stress`
**Turn 2 (improved):** `performance=0.85`, `success=True`, distinct `turn_reference`

Observed on real `language_progression` row (rolled back):

- Mastery increased turn 1 → turn 2
- `evidence_count` grew
- `assemble_student_speaking_live_context` output changed (priority targets / learner state)

**Label:** controlled S7 fixtures + real PostgreSQL mutation (not seeded S2).

## 18. Runtime wiring proof (real DB flush)

- Mocked `process_speaking_evaluation` + real `db` session on existing progression row.
- `handoff.mutation_status == "applied"` and S7 result preserved.

## 19. S7.6 cache invalidation

- `invalidate_live_context` still called after successful completed turn (post-mutation).
- Next `get_student_speaking_context` reloads fresh S2 from DB.

## 20. Verifier summary

`scripts/verify_speaking_s8_knowledge_bridge.py` — **46/46 PASS**

Checks A–AE cover: entry point, ownership, build rules, real Postgres, idempotency, adaptive loop, isolation, forbidden writes, batch atomicity, frozen S0–S7.6 subprocess reruns.

## 21. Frozen structural regressions (embedded in S8 verifier)

| Verifier | Result |
|----------|--------|
| S0 architecture | 525/525 PASS |
| S1 skill graph | 51/51 PASS |
| S2 knowledge model | 52/52 PASS |
| S3 audio frontend | 106/106 PASS |
| S4 audio runtime | PASS |
| S5 pronunciation | 27/27 PASS |
| S6 prosody | 39/39 PASS |
| S7 evaluation | 50/50 PASS |
| S7.5 EVI runtime | PASS |
| S7.6 EVI student context | 26/26 PASS |

## 22. Real EVI regressions (post-S8)

| Verifier | Result |
|----------|--------|
| `verify_speaking_s75_real_evi.py` | **21/21 PASS** |
| `verify_speaking_s76_real_evi.py` | **10/10 PASS** |
| `verify_speaking_s75_evi_browser.mjs` | **14/14 PASS** |

## 23. Files changed / added

**Added**

- `language_speaking_evaluation_runtime/knowledge_bridge_types.py`
- `language_speaking_evaluation_runtime/knowledge_bridge.py`
- `scripts/verify_speaking_s8_knowledge_bridge.py`
- `SPEAKING-S8-KNOWLEDGE-BRIDGE-REPORT.md`

**Modified**

- `language_speaking/ownership.py`
- `language_speaking_evaluation_runtime/live_runtime.py`
- `language_speaking_evaluation_runtime/__init__.py`
- `app/api/language_speaking_live.py`

## 24. Adaptive loop diagram (closed)

```
Completed EVI student turn
  → S7 process_speaking_evaluation
  → candidate_skill_evidence
  → S8 build_speaking_skill_observations
  → apply_speaking_evaluation_to_knowledge_model
  → mutate_speaking_knowledge_model (SELECT FOR UPDATE, flush)
  → invalidate_live_context
  → next get_student_speaking_context reads updated S2
```

## 25. Explicit real vs controlled labeling

| Proof | Mode |
|-------|------|
| S2 JSONB persistence, idempotency, forbidden-write preservation | **Real PostgreSQL** |
| Weak→improved mastery/context change | **Controlled S7 fixtures** + **Real PostgreSQL mutation** |
| `process_completed_live_turn` wiring | **Mocked S7** + **Real DB session** |
| S7.5/S7.6 real EVI | **Real Hume credentials** (regression only; S8 does not add EVI changes) |

## 26. STOP boundary

S8 is **COMPLETE**. Not started (per plan):

- Official CEFR / stage / promotion readiness / WPA
- Diagnostic planner, new EVI tools, mastery table migration
- Frontend redesign
- Direct `promotion_readiness_json` edits outside S2 APIs

**Next phase (S9+) is out of scope until explicitly requested.**
