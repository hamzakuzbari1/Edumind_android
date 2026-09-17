# Writing W7 — Evaluation & Revision Runtime Report

**Phase:** W7 — Evaluation & Revision
**Runtime version:** `7.0.0`
**Status:** Complete — verification green
**Frozen dependencies:** W0–W6 unchanged

---

## Executive Summary

W7 implements the **Writing Evaluation and Revision runtime** with strict evaluator/coach separation. The evaluator computes structured facts against the Lesson Blueprint `evaluation_plan`. The coach teaches from facts via the Learning Narrative layer — it never computes scores.

**Not in W7:** portfolio, progression, promotion, analytics.

---

## Pipeline (implemented)

```
Student Draft
  → Writing Evaluator (blueprint evaluation_plan)
  → Evaluation Facts
  → Facts Assembler
  → Learning Narrative
  → Writing Coach (revision plan)
  → Revision Session / Comparison
  → Re-evaluation (unlimited turns)
  → Completion (blueprint success criteria)
```

---

## Components

| Component | Owner | Role |
|-----------|-------|------|
| Evaluator engine | `language_writing_evaluator/engine.py` | Rubric facts only |
| Evaluation facts | `evaluation_facts_types.py` | Canonical persisted facts |
| Facts assembler | `language_writing_explainability/facts_assembler.py` | `WritingFactsBundle` |
| Learning narrative | `explainability/writing_narrative.py` | Student copy, no scores |
| Coach renderer | `language_writing_coach/renderer.py` | Revision plan from facts |
| Version comparison | `language_writing_revision/comparison.py` | improved/unchanged/regressed |
| Completion | `language_writing_revision/completion.py` | Blueprint criteria only |
| Persistence | `language_writing_revision/persistence.py` | Drafts, facts, coach, history |
| Orchestration | `language_writing_evaluation_runtime/pipeline.py` | Full turn processing |

---

## API

- `POST /api/student/languages/writing/{content_item_id}/draft` — submit draft for evaluation + coach feedback

Requires W6 lesson with `writing_blueprint` in `body_json`.

---

## Persistence keys

- `writing_evaluation_facts`
- `writing_coach_plan`
- `writing_revision_session`
- `writing_completion`

---

## Verification

```bash
cd backend
python scripts/verify_writing_w7_evaluation_revision.py
```

Manual QA: `language_writing_evaluation_runtime/MANUAL_QA_CHECKLIST.md`

Automated manual QA script:

```bash
python scripts/manual_qa_writing_w7.py --goal travel
python scripts/manual_qa_writing_w7.py --goal ielts
python scripts/manual_qa_writing_w7.py --goal business
```

---

## Stop after W7

No portfolio, progression, promotion, or analytics work started.
