# Knowledge Chain Node Metadata Specification (W1.2)

Every node in the Writing Topic Universe **must** define the following fields.
Lessons generated in future phases inherit this metadata via `body_json.writing_curriculum`.

## Hierarchy (mandatory)

```
Official CEFR → Curriculum Arc → Topic → Knowledge Chain → Lesson
```

**v1.2 topology:** All chains are `ChainTopology.linear`. See `FUTURE_GRAPH_BRANCHING.md`.

## Pedagogy fields (W1.2)

| Field | Purpose | Used by (future) |
|-------|---------|------------------|
| `learning_outcomes` | Educational expectations — what the student should achieve | Coach framing, Portfolio, Journey |
| `learning_objectives` | Skill-level targets (granular) | Generation, Coach |
| `common_mistakes` | Expected error patterns (`category: description`) | AI Coach guidance |
| `difficulty_drivers` | Why the lesson is hard (beyond complexity number) | Coach explanations, Journey |
| `prerequisite_skills` | Educational prerequisites (beyond graph links) | Selection, future branching |

**Important:** Learning outcomes are **not** feedback and **not** scores. They describe intent.

### Learning outcomes (examples)

- Write a formal email.
- Explain a problem clearly.
- Use linking words.
- Use past simple correctly.
- Request politely.

### Common mistakes (categories)

- `grammar:` — tense, agreement, sentence structure
- `vocabulary:` — misuse, imprecision, register
- `organization:` — paragraphing, sequence, clarity
- `tone:` — too casual, too aggressive
- `formatting:` — email layout, essay structure

### Difficulty drivers (examples)

- Formal language and professional register
- Longer response — more content to organize
- Multiple ideas with reasons and examples
- Topic-specific vocabulary to use accurately
- Complex timeline — events must be ordered clearly
- Real-world stakes — writing must work for a real audience

### Prerequisite skills (examples)

- Can write paragraphs.
- Understands email structure.
- Knows past simple.
- Knows basic connectors (because, however, therefore).
- Completed prior step: {previous node label}

## Core metadata (W1.1+)

See prior sections for grammar, vocabulary, time estimates, expected output, CEFR complexity ranges, and graph links.

## Auto-enrichment

`metadata_enrichment.py` derives W1.2 fields at catalog build time. Catalog authors may override via `N(..., outcomes=, mistakes=, drivers=, prerequisites=)`.

## Storage (future phases)

```json
{
  "writing_curriculum": {
    "learning_outcomes": ["Write a formal email", "Request politely"],
    "common_mistakes": ["tone: Register too casual for the audience"],
    "difficulty_drivers": ["Formal language and professional register"],
    "prerequisite_skills": ["Knows past simple", "Understands email structure"]
  }
}
```

## Validation

```bash
python scripts/verify_writing_topic_universe.py
```
