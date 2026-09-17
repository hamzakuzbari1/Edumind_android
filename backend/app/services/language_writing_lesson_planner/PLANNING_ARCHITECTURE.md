# Writing Lesson Planning Architecture (W3.1 — FROZEN)

Design-only. No LLM. No prompt building. Planner and Generator are strictly separated.

**Status:** FROZEN — future phases must reuse this architecture.

## Pipeline

```
Official CEFR → Goal Profile → Topic Universe → Knowledge Chain
  → Grammar/Vocab Progression → Context Complexity
  → Lesson Planner (no LLM)
  → Lesson Blueprint (versioned + hashed)
  → Writing Generator (blueprint only)
  → Writing Lesson
```

## Lesson Blueprint (W3.1)

Canonical contract. Every blueprint includes:

| Field group | Contents |
|-------------|----------|
| **Versioning** | `blueprint_version`, `schema_version`, `compatibility_notes`, `blueprint_hash` |
| **Targets** | grammar/vocabulary targets, review/stretch, outcomes |
| **Success** | `StructuredSuccessCriteria` + derived `success_criteria_labels` |
| **Evaluation** | `EvaluationPlan` — weights, required outcomes, critical mistakes, stretch bonus |
| **Context** | CEFR, goal, topic, node, arc, complexity, coach personality |

### Structured Success Criteria

- Minimum / maximum words
- Required grammar structures
- Required vocabulary lemmas
- Required output format
- Required objective completion

Not free-form text only — labels are derived for checklists.

### Evaluation Plan

Future `language_writing_evaluator` must reuse:

- Grammar / vocabulary / organization / task completion / goal alignment weights
- Required outcomes
- Critical mistakes
- Stretch bonus criteria

## Generator isolation

See `language_writing_generation/GENERATOR_ISOLATION.md`.

Generator input = `WritingGeneratorInput(blueprint=...)` only.

## Blueprint hash

`blueprint_hash.py` — SHA-256 of canonical educational payload. Same blueprint → same hash. Auditing only.

## Verification

```bash
python scripts/verify_writing_w3_lesson_planning.py
```
