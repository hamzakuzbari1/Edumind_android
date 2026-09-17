# Writing W4 — Lesson Experience Architecture Report

**Phase:** W4 — Lesson Experience assembly
**Architecture version:** `4.0.0`
**Status:** Complete — verification green
**Frozen dependencies:** Topic Universe v1.2.0, Coach v2.1.0-frozen, Lesson Planning v3.1.0-frozen

---

## Executive Summary

W4 defines the **assembly architecture** for the Writing Lesson Experience. It does **not** implement runtime, LLM calls, or grading. The Lesson Blueprint (W3.1 frozen) is the sole educational input to two parallel consumers:

1. **Mission Builder** — student-facing mission assembly
2. **Prompt Builder** — structured LLM prompt assembly (future runtime)

The **Student Lesson Experience** is the canonical object for everything visible to the student.

---

## Pipeline (frozen)

```
Lesson Blueprint (W3.1)
    ↓
Mission Builder ──→ Student Lesson Experience
    ↓
Prompt Builder ──→ LLM (future — not W4)
```

Mission Builder and Prompt Builder are **parallel consumers** of the same blueprint. Prompt Builder does not read Student Lesson Experience.

---

## 1. Mission Builder

**Owner:** `language_writing_generation/mission_builder.py`

Assembles `WritingStudentMission` from blueprint only:

| Output field | Source |
|--------------|--------|
| Mission Title | Blueprint goal + node label |
| Mission Context | `narrative_why` |
| Instructions | Blueprint targets (format, grammar, vocab, task) |
| Constraints | Success criteria + time plan |
| Success Criteria | `success_criteria_labels` |
| Estimated Time | `time_plan` |
| Learning Outcomes | `learning_outcomes` |
| Tips | `difficulty_drivers` + `common_mistakes` |
| Checklist | `success_criteria_labels` |

**Invariant:** Mission Builder never makes educational decisions.

---

## 2. Prompt Builder

**Owner:** `language_writing_generation/prompt_builder.py`

Assembles `WritingPromptBundle` from blueprint only:

| Section | Content |
|---------|---------|
| SYSTEM | Presentation-only assistant rules |
| ROLE | Goal profile role |
| MISSION | Situation + prompt seed + mission style |
| GRAMMAR | Primary / secondary / review targets |
| VOCABULARY | Primary / secondary lemmas |
| OUTPUT FORMAT | Expected writing output |
| CONSTRAINTS | Word count, genre, task, CEFR, complexity |
| SUCCESS CRITERIA | Outcomes + checklist |
| RULES | Preserve objectives; no new targets |

**Invariant:** Prompt Builder receives **only** the blueprint. No student, database, progression, topic universe, or knowledge chains.

---

## 3. Generator / LLM Boundary

Documented in `LLM_BOUNDARY.md`.

The LLM (future) receives **only** `WritingPromptBundle.to_prompt_dict()`. It must not access:

- Student / student_id
- Database
- Progression
- Topic Universe
- Knowledge Chains
- Raw `WritingLessonBlueprint`

---

## 4. Student Lesson Experience

**Owner:** `language_writing_lesson_experience/`

`WritingStudentLessonExperience` — canonical student-visible object:

- Mission Title · Writing Context · Instructions · Checklist
- Learning Outcomes · Estimated Time · Expected Output
- Constraints · Success Criteria · Tips · Writing Prompt
- Blueprint traceability (id, version, schema version, hash)

Assembled via `assemble_student_lesson_experience(blueprint)` which calls Mission Builder and wraps output — no field re-derivation.

---

## 5. No Duplicated Assembly

| Component | Role |
|-----------|------|
| `mission_builder.py` | Sole owner of mission field assembly |
| `prompt_builder.py` | Sole owner of prompt section assembly |
| `experience_assembler.py` | Wraps mission into student lesson |
| `mission_assembly.py` | W3 legacy shim — delegates to Mission Builder |

---

## Packages

| Package | Layer | W4 role |
|---------|-------|---------|
| `language_writing_lesson_planner` | planning | Blueprint source (frozen W3.1) |
| `language_writing_generation` | generation | Mission Builder + Prompt Builder |
| `language_writing_lesson_experience` | experience | Student Lesson Experience assembly |

---

## Verification

```bash
cd backend
python scripts/verify_writing_w4_lesson_experience.py
```

Prior phases remain frozen:

```bash
python scripts/verify_writing_w3_lesson_planning.py
python scripts/verify_writing_w0_architecture.py
```

---

## Explicitly Out of Scope (W4)

- Runtime lesson delivery
- LLM invocation
- Grading / evaluation execution
- Coach integration in student lesson object
- Journey / portfolio fields

Stop after W4.
