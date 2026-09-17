# Writing Generation Architecture (W5)

Design-only. No runtime. No LLM calls. No Gemini.

## Pipeline (frozen)

```
Lesson Blueprint (W3.1)
    ↓
Mission Builder (W4)
    ↓
Prompt Builder (W4)
    ↓
LLM (future — not W5)
    ↓
Response Normalizer     owner: response_normalizer.py
    ↓
Lesson Validator        owner: lesson_validator.py
    ↓
Repair Layer            owner: repair_layer.py
    ↓
Canonical Lesson        owner: canonical_lesson_types.py
    ↓
Generation Audit        owner: generation_audit.py
```

Orchestrated by `generation_pipeline.py` — accepts mock raw LLM output in W5.

## 1. Response Normalizer

- Parse raw LLM JSON (strip code fences)
- Map field aliases → canonical names
- Normalize enums (expected_output)
- Coerce string arrays
- Reject malformed structures
- **No blueprint access. No educational logic.**

## 2. Lesson Validator

Validates normalized draft against blueprint:

- Required fields
- Grammar metadata reference
- Vocabulary metadata reference
- Success criteria consistency
- Expected output match
- Constraints / word limits
- CEFR consistency
- Output schema completeness

## 3. Repair Layer

Structural repair only — copies from blueprint or Mission Builder:

- Missing checklist, tips, outcomes, criteria, constraints
- Enum casing normalization
- Empty optional arrays

**Never invents educational content.**

## 4. Canonical Lesson

`WritingCanonicalGeneratedLesson` — final persisted lesson shape with `generation_hash`.

## 5. Generation Audit

`WritingGenerationAuditRecord` persists:

- Blueprint version / schema / hash
- Prompt version / generator version / LLM version
- Generation hash / duration
- Validation result / repair result / outcome

## 6. Failure Strategy

See `FAILURE_STRATEGY.md` — retry, repair, hard failure, soft failure policies.

## Verification

```bash
python scripts/verify_writing_w5_generation.py
```

Stop after W5.
