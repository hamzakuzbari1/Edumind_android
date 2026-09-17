# LANGUAGE-ADAPTIVE-LEARNING-PHASE-3.3-REPORT

**Phase:** 3.3 — Adaptive Challenge Engine
**Status:** PASS
**Date:** 2026-07-07

---

## Goal

Continuously adjust listening **challenge** inside the learner's **current CEFR level** — never changing CEFR vocabulary, grammar, or objectives. Challenge bands: Easy → Normal → Hard → Exam (per CEFR level, e.g. B1 Easy … B1 Exam).

---

## Architecture

```
submit_listening()
  → update confidence + evidence (unchanged)
  → record_challenge_from_lesson()   [NEW]
  → hysteresis promote/demote one step
  → save preferences_json["listening_challenge"]

generate_and_store_listening()
  → load confidence + challenge state
  → recommend_challenge_adaptive_listening_plan()   [NEW wrapper]
      wraps recommend_confidence_aware_listening_plan scoring
      adds ~7.5% challenge-alignment blend
  → _build_prompt()
      [CEFR] + [QUALITY] + [CURRICULUM] + [GOAL] + [ADAPTIVE CHALLENGE]   [NEW block]
      quality difficulty_band overridden by challenge mapping
  → store body_json["listening_challenge_lesson"]
```

**Protected (not modified):** CEFR engine/validator, Listening Quality Layer, Intelligence Layer, Curriculum Engine, Goal Engine, Confidence Engine, Evidence Engine, frontend, audio.

---

## Files Modified / Created

| Action | File |
|--------|------|
| **Created** | `app/services/language_listening_challenge/__init__.py` |
| **Created** | `app/services/language_listening_challenge/types.py` |
| **Created** | `app/services/language_listening_challenge/constants.py` |
| **Created** | `app/services/language_listening_challenge/scoring.py` |
| **Created** | `app/services/language_listening_challenge/adjustment.py` |
| **Created** | `app/services/language_listening_challenge/record.py` |
| **Created** | `app/services/language_listening_challenge/storage.py` |
| **Created** | `app/services/language_listening_challenge/prompt.py` |
| **Created** | `app/services/language_listening_challenge/telemetry.py` |
| **Created** | `app/services/language_listening_challenge/engine.py` |
| **Modified** | `app/services/language_lesson_generation_service.py` |
| **Modified** | `app/services/language_skill_progress_service.py` |
| **Created** | `scripts/verify_language_adaptive_learning_phase_3_3.py` |
| **Modified** | `scripts/verify_language_adaptive_learning_phase_3_1.py` (wrapper chain) |
| **Modified** | `scripts/verify_language_adaptive_learning_phase_3_2.py` (wrapper chain) |

---

## Challenge Algorithm

**Challenge score** (0–1) computed from the last **15 lessons**:

| Input | Weight |
|-------|--------|
| Accuracy | 28% |
| Confidence trend | 18% |
| Evidence growth (coverage delta) | 14% |
| Review performance | 10% |
| Success/failure streak | 12% |
| Time spent | 6% |
| Hint usage (penalty) | 6% |
| Retries (penalty) | 6% |

Recent 5-lesson average blended at 28% for responsiveness. Global confidence trend adds 12% when history is sparse.

**Storage:** `preferences_json["listening_challenge"]` per CEFR level.

---

## Promotion Algorithm

1. After each lesson, compute per-lesson performance score.
2. If lesson score ≥ **0.62** → increment `promote_streak`; decay `demote_streak`.
3. When `promote_streak ≥ 4` **and** aggregate `challenge_score ≥ 0.68`:
   - Move **one step up**: easy→normal→hard→exam.
   - Reset streaks; increment `promotion_count`; log reason in `adjustment_history`.

Never skip levels. Never promote easy→exam directly.

---

## Demotion Algorithm

1. If lesson score ≤ **0.40** → increment `demote_streak`; decay `promote_streak`.
2. When `demote_streak ≥ 4` **and** aggregate `challenge_score ≤ 0.42`:
   - Move **one step down**: exam→hard→normal→easy.
   - Reset streaks; increment `demotion_count`; log reason.

Hysteresis gap (0.68 promote vs 0.42 demote) prevents oscillation. Neutral lessons decay both streaks.

---

## Curriculum Integration

- `recommend_challenge_adaptive_listening_plan()` re-scores intelligence candidates with existing curriculum + goal + confidence + evidence blend, then adds **challenge match** at **7.5%** influence (5–10% band).
- Challenge maps to intelligence `difficulty_band`: easy/normal/challenging/challenging (exam).
- `[ADAPTIVE CHALLENGE]` prompt block adjusts transcript length, speech speed, distractor quality, inference density, implicit information, question complexity — all **within CEFR bounds**.

---

## Telemetry

`compute_challenge_telemetry()` tracks:

- Current challenge level
- Challenge score
- Promotion / demotion counts
- Promote / demote streaks
- Per-lesson history (last 15)
- Adjustment history with reason
- Average lesson performance score

Lesson metadata key: `listening_challenge_lesson`.

---

## Simulation (1000 lessons, B1, mixed outcomes)

### Before (confidence-only)

- Difficulty distribution fixed by intelligence rotation: easy 33%, normal 33%, challenging 33%.
- No within-CEFR challenge adaptation.

### After (adaptive challenge)

| Metric | Value |
|--------|-------|
| Total adjustments | 4 |
| Promotions | 3 |
| Demotions | 1 |
| Illegal jumps (≠1 step) | 0 |
| Oscillation events | 0 |
| Average challenge index | 1.205 (above normal baseline 1.0) |
| Evolution L100→L1000 | easy → easy → easy → exam → exam |
| Final challenge | exam |
| Avg plan-challenge match | 0.676 |

Adjustment trail (sequential, one step each):

1. L75: normal → easy (weak early phase)
2. L620: easy → normal
3. L624: normal → hard
4. L628: hard → exam

---

## Regression

| Phase | Result |
|-------|--------|
| 3.1 Goal-Aware | PASS |
| 3.2 Confidence | PASS |
| 3.2.1 Evidence | PASS |
| **3.3 Challenge** | **PASS** |

---

## Verification Command

```bash
python scripts/verify_language_adaptive_learning_phase_3_3.py
```

---

## PASS / FAIL

**PASS** — All static checks, simulation checks, and regressions passed.
