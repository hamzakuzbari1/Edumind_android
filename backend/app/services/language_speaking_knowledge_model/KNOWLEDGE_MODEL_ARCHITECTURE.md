# Speaking Student Knowledge Model (S2)

## Storage decision

**Audited:** `LanguageProgression.promotion_readiness_json` is the shared per-student/language JSONB store. Writing uses `['writing']`; listening uses top-level keys; grammar/vocabulary mastery uses separate BKT tables (`language_learner_model_service`).

**Decision:** Persist the Speaking Knowledge Model at:

```
promotion_readiness_json.speaking.knowledge_model
```

The `speaking` bucket is a **sibling namespace** (like `writing`), not the promotion readiness score itself. Future S16 promotion readiness will use a separate sub-key (e.g. `speaking.readiness`) so mastery and readiness remain conceptually separated.

**Why not a new table:** Matches mature Writing/Listening JSON mutation patterns (`flag_modified`, row lock, atomic mutator). No migration required for S2.

**What S2 does NOT write:** `official_speaking_cefr`, `learning_stage_speaking`, `promotion_readiness_score`, readiness decisions.

## Skill state model (`StudentSpeakingSkillState`)

| Field | Range | Consumer |
|-------|-------|----------|
| `mastery` | 0–1 | S8 diagnostic priority |
| `confidence` | 0–1 | S8 uncertainty weighting |
| `stability` | 0–1 | S8 prerequisite trust, S2 status |
| `retention_risk` | 0–1 | S8 review scheduling |
| `evidence_count` | int | S1 requirement gates |
| `observed_dimensions` | map | S7/S8 coverage checks |
| `distinct_context_count` | int | S1 context requirements |
| `mistake_recurrence` | 0–1 | S8 remediation |
| `revision_improvement` | 0–1 | S12 coach revision narrative |
| `current_status` | enum | S8 summaries (cached) |
| `peak_mastery` / `peak_stability` | 0–1 | Retention / AT_RISK detection |

**Derived (not persisted):** `mastered_skill_ids`, `developing_skill_ids`, `at_risk_skill_ids`, `unseen_skill_ids`, `EvidenceCoverage` — computed from state + S1 graph.

## Observation contract (`SpeakingSkillEvidenceObservation`)

Canonical input from S7 evaluation facts. No provider payloads. Required: `observation_id`, `skill_id`, `observed_at`, `performance`, `confidence`, `evidence_dimensions`, `context_id`, `success`. Optional: `mistake_tags`, `revision_number`, `previous_observation_id`, `target_skill`, `communicative_impact`.

## Evidence validation

1. `skill_id` exists in S1 graph
2. Dimensions ∈ `ALL_EVIDENCE_CODES`
3. Overlap with node's `evidence_requirements` ≥ `minimum_dimensions`
4. Performance/confidence ∈ [0, 1]
5. `context_id` non-empty
6. `observed_at` valid, not in the future (relative to injected `now`)
7. Duplicate `observation_id` → idempotent no-op
8. Mistake tags: max 64 chars; prose-like tags (spaces without `:`) rejected

Unrelated dimensions cannot update a skill — validation rejects before engine runs.

## Mastery update formula

Evidence-weighted EMA (bounded):

```
weight = confidence × (1.0 if target_skill else 0.32)
alpha  = 0.18 × weight
mastery = clamp(mastery + alpha × (performance − mastery))
recent_performance = EMA(performance) with same alpha
```

One excellent observation cannot master a skill because `alpha ≤ 0.18` and S1 gates require counts, stability, contexts, and full dimension coverage.

## Confidence update

```
evidence_factor = 1 − exp(−0.35 × evidence_count × confidence)
confidence = clamp(0.7 × prev + 0.3 × evidence_factor × max(mastery, recent_performance))
```

Contradictory observations (|Δperformance| > 0.45) multiply confidence by 0.82.

## Stability logic

Blend of:
- **Variance** of last ≤6 performances (low variance → higher stability)
- **Consecutive successes** (capped at 5)
- **Distinct contexts** (capped at 4)
- **Mistake penalty** from recurrence

```
stability = 0.65 × prev + 0.35 × blended_components
```

First observation: `stability = 0`. Same-context revisions improve `revision_improvement` but do not inflate `distinct_context_count`.

## Mistake recurrence

Stable tags (e.g. `pronunciation:theta_to_s`) increment `mistake_patterns` and per-skill `mistake_tag_counts`. Coach prose is never stored as identity.

## Revision improvement

When `previous_observation_id` matches a history record:

```
revision_delta = performance_now − performance_prev
revision_improvement = clamp(revision_delta) if delta ≥ 0.08
```

Same-context revision success does not substitute for cross-context stability.

## Retention risk

Only for **previously demonstrated** skills (`peak_mastery ≥ 0.35` or `peak_stability ≥ 0.40`):

```
idle_ratio = days_since_last_practice / SRS_initial_interval
retention_risk = clamp(0.7 × idle_ratio × (1 − 0.5×stability) + 0.2×(1−recent_performance) + trend_penalty)
```

`UNSEEN` skills always have `retention_risk = 0`.

## Status derivation

| Status | Rule |
|--------|------|
| `unseen` | `evidence_count == 0` |
| `observed` | 1–2 observations, low mastery |
| `developing` | mastery ≥ 0.22 or evidence_count ≥ 3 |
| `stable` | stability ≥ 0.48 and mastery ≥ 0.22 |
| `mastered` | S1 `SkillMasteryRequirement` gate passes |
| `at_risk` | Previously demonstrated + `retention_risk ≥ 0.62` (not mastered) |

## Bounded history

- Per skill: **12** `observation_history` records (FIFO eviction)
- Global: **256** `applied_observation_ids` for idempotency (FIFO eviction)
- Aggregates (`mastery`, `stability`, `observed_dimensions`, peaks) survive eviction

## Graph version compatibility

`reconcile_model_with_graph()`:
- Unknown persisted `skill_id` → moved to `deprecated_skill_states` (not deleted)
- New catalog skills → reported in `CompatibilityReport.new_skill_ids`
- `graph_version` updated to current S1 version

## Future integration

- **S7:** Map `SpeakingEvaluationEngineResult` → `SpeakingSkillEvidenceObservation` list
- **S8:** Read `StudentSpeakingKnowledgeModel` for diagnostic next-skill selection (does not write mastery)

## S2 non-responsibilities

Audio, evaluation engines, diagnostic selection, lesson planning, coach, progression, promotion, official CEFR, frontend, LLM calls.

## Verification

```bash
python scripts/verify_speaking_s2_knowledge_model.py
python scripts/verify_speaking_s1_skill_graph.py
python scripts/verify_speaking_s0_architecture.py
```
