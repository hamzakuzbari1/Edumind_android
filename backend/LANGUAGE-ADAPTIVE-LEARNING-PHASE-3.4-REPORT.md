# LANGUAGE-ADAPTIVE-LEARNING-PHASE-3.4-REPORT

**Phase:** 3.4 — Learning Path & Explainability Engine
**Status:** PASS
**Date:** 2026-07-07

---

## Goal

Expose **why** every listening lesson was chosen in a structured, educational way — using only real recommendation signals. The explainability layer is **read-only** and never influences recommendations.

---

## Architecture

```
body_json (stored at generation)
  listening_intelligence
  listening_curriculum
  listening_learning_goal
  listening_confidence_lesson
  listening_challenge_lesson
  questions[].type

preferences_json (live learner state, optional)
  listening_confidence
  listening_challenge

generate_listening_explainability()   [READ-ONLY]
  → extract_signals()
  → build_lesson_explainability()
  → build_learning_path()
  → build_teacher_summary()
  → build_student_summary()
  → measure_explainability() telemetry
```

**Protected (not modified):** CEFR, Quality, Intelligence, Curriculum, Goal, Confidence, Evidence, Challenge engines, audio, frontend, generation service.

---

## Files

| Action | File |
|--------|------|
| **Created** | `app/services/language_listening_explainability/__init__.py` |
| **Created** | `app/services/language_listening_explainability/types.py` |
| **Created** | `app/services/language_listening_explainability/builder.py` |
| **Created** | `app/services/language_listening_explainability/learning_path.py` |
| **Created** | `app/services/language_listening_explainability/teacher_summary.py` |
| **Created** | `app/services/language_listening_explainability/student_summary.py` |
| **Created** | `app/services/language_listening_explainability/telemetry.py` |
| **Created** | `app/services/language_listening_explainability/engine.py` |
| **Created** | `scripts/verify_language_adaptive_learning_phase_3_4.py` |

---

## Data Flow

1. **Input:** Lesson `body_json` metadata from generation (5 engine keys) + optional live `ConfidenceState` / `ChallengeState`.
2. **Extract:** `extract_signals()` reads metadata only — no scoring, no re-recommendation.
3. **Explain:** Text built by interpolating factual values (intent, scores, situation, challenge band, confidence snapshot, etc.).
4. **Path:** `build_learning_path()` uses `compute_confidence_telemetry()` and `level_objectives()` for journey status.
5. **Summaries:** Teacher/student views derived from telemetry + lesson explainability + goal profiles (read-only).
6. **Output:** `ExplainabilityResult` with lesson, path, summaries, telemetry.

---

## Explainability Schema

```json
{
  "cefr_level": "B1",
  "lesson": {
    "why_this_lesson": "...",
    "why_this_topic": "...",
    "why_this_format": "...",
    "why_this_difficulty": "...",
    "why_these_questions": "...",
    "current_focus": "...",
    "current_goal": "...",
    "challenge_reason": "...",
    "confidence_reason": "...",
    "review_reason": "...",
    "next_recommendation": "...",
    "teacher_note": "...",
    "student_tip": "..."
  },
  "learning_path": { "journey_title": "Listening Journey", "objectives": [...] },
  "teacher_summary": { "strengths": [], "weaknesses": [], ... },
  "student_summary": { "what_improved": "...", ... },
  "telemetry": { "generation_time_ms": 6.2, "signals_used": [], "missing_signals": [], "coverage_completeness": 1.0 }
}
```

All strings are composed from recorded signals — no invented reasons.

---

## Learning Path Schema

Per objective (Main Idea, Detail, Inference, Purpose, Tone, Prediction, Opinion, Speaker Intention, Bias):

| Field | Source |
|-------|--------|
| `confidence` | `ConfidenceState.objectives[oid].confidence` |
| `coverage` | `coverage_score` property |
| `mastery` | `mastery_score` property |
| `status` | Not Started / Learning / Practicing / Review / Mastered |
| `next_recommendation` | Factual next step from status + review queue |

Status rules (explainability-only mapping):
- **Mastered** — `is_mastered`
- **Review** — in `review_due` queue
- **Not Started** — `exposure_count == 0`
- **Learning** — confidence &lt; 0.55
- **Practicing** — otherwise

---

## Teacher Summary

Derived from `compute_confidence_telemetry()`, challenge telemetry, and lesson signals:

- **Strengths** — high-confidence objectives with optional positive trend
- **Weaknesses** — under-confident objectives
- **Recent improvement** — objectives with trend &gt; 0.03
- **Current bottleneck** — lowest mastery journey objective
- **Recommended next challenge** — current challenge band + score + last adjustment
- **Review priorities** — `review_due` list
- **Suggested transcript styles** — narrative format / arc from intelligence metadata
- **Suggested situations** — lesson situation + goal profile preferred situations

---

## Student Summary

Derived from lesson metadata + confidence telemetry:

- **What improved** — positive confidence trends
- **What needs practice** — skill focus + under-confident objectives
- **Why today's lesson matters** — challenge band, situation, intent, objectives
- **How helps future** — knowledge node chain or next recommendation
- **Study tip** — evidence gaps (missing axes) or lesson student tip
- **Motivational sentence** — mastered count + promotion count (factual)

---

## Telemetry

| Metric | Description |
|--------|-------------|
| `generation_time_ms` | Wall time to build explainability |
| `signals_used` | Which of 7 expected signal groups were present |
| `missing_signals` | Expected groups absent from input |
| `coverage_completeness` | Fraction of expected signals present (0–1) |

---

## Verification (500 lessons, B1)

| Check | Result |
|-------|--------|
| Package + modules exist | PASS |
| Generation service untouched | PASS |
| No missing mandatory fields | PASS (0/6500) |
| Explanations grounded in real signals | PASS (500/500) |
| Teacher summary consistency | PASS (500/500) |
| Student summary consistency | PASS (500/500) |
| Learning path correctness | PASS (500/500) |
| Signal coverage completeness | PASS (avg 1.0) |
| Avg generation time | 6.2 ms |

```bash
python scripts/verify_language_adaptive_learning_phase_3_4.py
```

---

## Regression

| Phase | Result |
|-------|--------|
| 3.3 Challenge | PASS (re-run) |
| **3.4 Explainability** | **PASS** |

---

## PASS / FAIL

**PASS**
