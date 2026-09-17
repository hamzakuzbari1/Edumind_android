# Writing Feedback Layers (W2)

Strict separation — no duplication across layers.

## Pipeline

```
Student draft
    ↓
┌─────────────────────────────────────┐
│  Layer 1: Evaluation Facts          │  owner: language_writing_evaluator
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Layer 1b: Facts Bundle               │  owner: language_writing_explainability
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Layer 2: Learning Narrative        │  owner: language_learning_narrative (shared)
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Layer 2b: Coach Mission            │  owner: language_writing_coach/mission_layer
│  (mission, focus, goal, criteria)   │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Layer 3: Coach Narrative           │  owner: language_writing_coach
│  (revision plan — teaches)          │  + adaptive_tone (communication only)
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Layer 4: Student UI                │  owner: language_writing_bundles (API schemas)
└─────────────────────────────────────┘
```

## Ownership rules

| Layer | May contain | Must NOT contain |
|-------|-------------|------------------|
| **Evaluation Facts** | Dimension scores, issue codes, severity, `ready_to_complete_signal` | Encouragement, examples, teacher voice |
| **Facts Bundle** | CEFR, arc, goal, lifecycle, evaluation dict | Coach sentences, UI layout |
| **Learning Narrative** | `why_this_lesson`, `student_focus`, `coach_summary` (lesson scope) | Raw rubric scores, band numbers |
| **Coach Mission** | `todays_mission`, `todays_focus`, `success_criteria`, `expected_learning_outcomes` | Generated prompts, evaluator codes |
| **Coach Narrative** | Encouragement, priority fix, example, revision mission | Recomputed rubric (must use evaluation input) |
| **Student UI** | Mapped fields from revision plan + mission + composer | Internal signals, evaluator codes |

## Coach vs Evaluator

- **Evaluator** answers: *What happened in the writing?*
- **Coach** answers: *What should the student do next?*
- Same evaluation facts + different personality → different **voice**, identical **priority issue**.

## Duplication prevention

- `WritingEvaluationResult.to_facts_dict()` — internal only; never sent to frontend.
- `WritingRevisionPlan.to_student_dict()` — student-safe fields only.
- `CoachInternalSignals` — never in API schemas.
- Journey bundles receive **narrative summaries**, not raw evaluation payloads.

## Metadata keys (body_json)

| Key | Owner | Layer |
|-----|-------|-------|
| `writing_goal` | curriculum | selection |
| `writing_evaluation` | evaluator | evaluation |
| `writing_curriculum` | generation / catalog | catalog |
| `writing_coach_plan` | coach | pedagogy |
| `writing_facts` | explainability | facts |
