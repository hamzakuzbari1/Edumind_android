# Writing Lesson Experience Architecture (W4)

Design-only. No runtime. No LLM calls. No grading.

## Pipeline

```
Lesson Blueprint (W3.1 frozen)
    ↓
Mission Builder          owner: language_writing_generation/mission_builder.py
    ↓
Student Lesson Experience owner: language_writing_lesson_experience/
    ↓
Prompt Builder           owner: language_writing_generation/prompt_builder.py
    ↓
LLM                      (future — not W4)
```

## 1. Mission Builder

Assembles `WritingStudentMission` from blueprint:

- Mission Title · Mission Context · Instructions · Constraints
- Success Criteria · Estimated Time · Learning Outcomes · Tips · Checklist

Never makes educational decisions.

## 2. Prompt Builder

Assembles `WritingPromptBundle` from blueprint only:

SYSTEM · ROLE · MISSION · GRAMMAR · VOCABULARY · OUTPUT FORMAT · CONSTRAINTS · SUCCESS CRITERIA · RULES

Never reads Student Lesson Experience or student data.

## 3. Student Lesson Experience

`WritingStudentLessonExperience` — canonical student-visible object:

Mission · Writing Context · Instructions · Checklist · Learning Outcomes · Estimated Time · Expected Output · Constraints · Tips · Writing Prompt

## 4. No duplicated assembly

- **Mission Builder** — sole owner of mission field assembly
- **Prompt Builder** — sole owner of prompt section assembly
- **Experience Assembler** — wraps mission into student lesson (no field re-derivation)
- **mission_assembly.py** — legacy W3 shim delegating to Mission Builder

## Verification

```bash
python scripts/verify_writing_w4_lesson_experience.py
```
