# Writing W3.1 — Lesson Planning Architecture Report (FROZEN)

**Phase:** W3 final refinement + freeze
**Architecture version:** `3.1.0-frozen`
**Blueprint version:** `3.1.0`
**Status:** Complete — verification green
**Frozen dependencies:** Topic Universe v1.2.0, Coach Architecture v2.1.0-frozen

---

## Executive Summary

W3.1 completes and **freezes** the Lesson Planning architecture. The planner decides WHAT; the generator decides HOW (presentation only). No LLM, no runtime, no prompts.

---

## Pipeline (frozen)

```
Official CEFR → Goal Profile → Topic Universe → Knowledge Chain
  → Grammar/Vocab Progression → Context Complexity
  → Lesson Planner → Lesson Blueprint (versioned + hashed)
  → Writing Generator (blueprint only) → Writing Lesson
```

---

## W3.1 Refinements

### 1. Evaluation Plan

Every blueprint includes `EvaluationPlan`:

- Grammar / vocabulary / organization / task completion / goal alignment weights (sum = 1.0)
- Required outcomes
- Critical mistakes
- Stretch bonus criteria

Future evaluator phases **must reuse** this plan.

### 2. Structured Success Criteria

`StructuredSuccessCriteria` replaces free-form-only checkpoints:

- Minimum / maximum words
- Required grammar structures
- Required vocabulary lemmas
- Required output format
- Required objectives (+ optional stretch)

`success_criteria_labels` derived for student checklists.

### 3. Generator Isolation

Documented in `GENERATOR_ISOLATION.md`. Generator receives **only** `WritingLessonBlueprint` via `WritingGeneratorInput`. Must not read student, progression, topic universe, goal profiles, or progression services.

### 4. Blueprint Versioning

Every blueprint includes:

- `blueprint_version` (3.1.0)
- `schema_version` (3.1.0)
- `compatibility_notes`
- Lessons preserve version + hash when created (future runtime)

### 5. Blueprint Hash

`blueprint_hash.py` — SHA-256 of canonical educational payload. Same blueprint → same hash. Auditing and debugging only.

---

## Packages

| Package | Layer | Role |
|---------|-------|------|
| `language_writing_lesson_planner` | planning | WHAT — blueprint assembly |
| `language_writing_generation` | generation | HOW — presentation from blueprint |

---

## Verification

```bash
cd backend
python scripts/verify_writing_w3_lesson_planning.py
python scripts/verify_writing_w0_architecture.py
```

---

## Not Started

- W4 LLM generation / prompts
- Runtime API
- Frontend

---

## Stop Point

W3 frozen. Awaiting explicit approval before W4.
