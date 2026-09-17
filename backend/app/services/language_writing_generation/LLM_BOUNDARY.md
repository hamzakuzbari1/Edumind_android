# LLM Generator Boundary (W4)

The LLM receives **only** `WritingPromptBundle` output from the Prompt Builder.

## Allowed input to LLM (future runtime)

```
WritingPromptBundle.to_prompt_dict()
  ├── system
  ├── role
  ├── mission
  ├── grammar
  ├── vocabulary
  ├── output_format
  ├── constraints
  ├── success_criteria
  └── rules
```

Plus optional `locale` for presentation language — not educational content.

## Forbidden direct access

The LLM runtime must **never** read:

| Source | Reason |
|--------|--------|
| Student / student_id | Privacy; not in blueprint |
| Database | All targets frozen in blueprint |
| Progression | Merged at plan time |
| Topic Universe | Frozen in blueprint |
| Knowledge Chains | Frozen in blueprint |
| Goal Profiles | Frozen in blueprint |
| Raw `WritingLessonBlueprint` | LLM uses prompt bundle only |

## Pipeline (frozen)

```
Lesson Blueprint
    ↓
Mission Builder ──→ Student Lesson Experience (student UI)
    ↓
Prompt Builder ──→ LLM (wording only, future W5+)
```

Mission Builder and Prompt Builder are **parallel consumers** of the same blueprint. Prompt Builder does not read Student Lesson Experience.

## Educational invariant

LLM may rephrase presentation. It must not alter objectives, grammar targets, vocabulary targets, or success criteria encoded in the prompt sections.
