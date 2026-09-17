# Generator Isolation (W3.1 FROZEN)

The Writing Generator receives **ONLY** the `WritingLessonBlueprint`.

## Allowed input

```python
WritingGeneratorInput(
    blueprint=WritingLessonBlueprint,  # sole educational source
    generator_version="3.1.0",
    locale="en",  # presentation locale only
)
```

## Forbidden reads

The generator must **never** access:

| Source | Reason |
|--------|--------|
| Student / student_id | Identity belongs to API layer |
| Progression snapshots | Planner already merged progression into blueprint |
| Topic Universe catalog | Topic/node frozen in blueprint |
| Goal Profiles | Goal frozen in blueprint |
| Grammar Progression service | Targets frozen in blueprint |
| Vocabulary Progression service | Targets frozen in blueprint |
| Knowledge Chain registry | Node metadata frozen in blueprint |
| Curriculum selection engine | Selection done before blueprint |
| `LessonPlannerInput` | Planner-internal only |

## Forbidden imports (generation package)

The `language_writing_generation` package may import:

- `language_writing_lesson_planner` — **blueprint types only**

It must **not** import:

- `language_writing_curriculum`
- `language_writing_topic_universe`
- `language_writing_knowledge_chain`
- `language_writing_grammar_progression`
- `language_writing_lexis_progression`
- `language_writing_progression`
- `language_writing_coach`
- `language_writing_evaluator`

## Forbidden decisions

See `GENERATOR_FORBIDDEN_DECISIONS` in `lesson_planner/types.py`.

## Lesson metadata

Generated lessons must preserve:

- `blueprint_version`
- `schema_version`
- `blueprint_hash`

So audits can trace which blueprint produced the lesson.

## Future LLM phases (W4+)

LLM may rephrase presentation text only. It must not alter:

- `evaluation_plan` weights
- `success_criteria` structured fields
- `learning_outcomes`
- `blueprint_hash`
