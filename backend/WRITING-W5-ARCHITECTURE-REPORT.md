# Writing W5 — Generation Architecture Report

**Phase:** W5 — Writing Generation pipeline
**Architecture version:** `5.0.0`
**Status:** Complete — verification green
**Frozen dependencies:** Topic Universe v1.2.0, Coach v2.1.0-frozen, Planning v3.1.0-frozen, Lesson Experience v4.0.0-frozen

---

## Executive Summary

W5 completes the **Writing Generation architecture** from blueprint through canonical lesson and audit. It extends W4 (Mission Builder + Prompt Builder) with post-LLM processing stages. **No runtime, no LLM calls, no Gemini** — architecture, types, pipeline contract, and verification only.

---

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
Response Normalizer
    ↓
Lesson Validator
    ↓
Repair Layer
    ↓
Canonical Lesson
    ↓
Generation Audit
```

Orchestrated by `generation_pipeline.process_llm_generation()` — accepts mock raw LLM JSON in W5.

---

## 1. Response Normalizer

**Owner:** `response_normalizer.py`

| Responsibility | Detail |
|----------------|--------|
| Parse raw LLM output | JSON + code fence stripping |
| Normalize field names | Alias map → canonical names |
| Normalize enums | `ExpectedWritingOutput` casing |
| Normalize arrays | Coerce to `tuple[str, ...]` |
| Reject malformed | Invalid JSON, wrong types, missing required fields |

**Invariant:** No blueprint access. No educational logic.

---

## 2. Lesson Validator

**Owner:** `lesson_validator.py`

Validates `WritingNormalizedLessonDraft` against `WritingLessonBlueprint`:

- Required fields (title, context, instructions, prompt)
- Grammar metadata reference
- Vocabulary metadata reference
- Success criteria consistency
- Expected output match
- Constraints / word limits
- CEFR consistency
- Output schema completeness

**Invariant:** Validates only — does not repair.

---

## 3. Repair Layer

**Owner:** `repair_layer.py`

Structural repair from blueprint or Mission Builder:

| Missing / broken | Restored from |
|------------------|---------------|
| Checklist | Blueprint `success_criteria_labels` |
| Tips | Mission Builder |
| Learning outcomes | Blueprint |
| Success criteria | Blueprint |
| Constraints | Mission Builder |
| Expected output (enum) | Blueprint |
| Grammar / vocabulary display | Blueprint targets |

**Forbidden:** Invent grammar, vocabulary, outcomes, criteria, or change word limits / CEFR.

---

## 4. Canonical Lesson

**Owner:** `canonical_lesson_types.py`

`WritingCanonicalGeneratedLesson` — final lesson shape with:

- All student-visible presentation fields
- Blueprint traceability (id, version, schema, hash)
- `generation_hash` (SHA-256 of canonical payload + blueprint_hash)

---

## 5. Generation Audit

**Owner:** `generation_audit.py`

`WritingGenerationAuditRecord` persists:

| Field | Source |
|-------|--------|
| Blueprint version / schema / hash | Blueprint |
| Prompt version | Prompt Builder |
| Generator version | Pipeline |
| LLM version | Raw response metadata |
| Generation hash | `generation_hash.py` |
| Generation duration | Pipeline input |
| Validation result | Validator |
| Repair result | Repair Layer |
| Outcome | success / soft_failure / hard_failure |

---

## 6. Failure Strategy

Documented in `FAILURE_STRATEGY.md` and `failure_strategy.py`:

| Policy | Default |
|--------|---------|
| LLM retries | 2 on normalization failure |
| Repair passes | 1 |
| Hard failure | Unrecoverable after repair |
| Soft failure | Repair applied, validation passes |

---

## Component Ownership

| Component | Sole owner | Must not |
|-----------|------------|----------|
| JSON parse / field aliases | Normalizer | Access blueprint |
| Consistency validation | Validator | Call repair |
| Structural restore | Repair Layer | Invent content |
| Audit assembly | Generation Audit | Parse JSON |
| Orchestration | Generation Pipeline | Duplicate logic |

---

## Packages

| Module | W5 role |
|--------|---------|
| `response_normalizer.py` | Parse + normalize LLM output |
| `lesson_validator.py` | Blueprint consistency checks |
| `repair_layer.py` | Structural repair |
| `canonical_lesson_types.py` | Final lesson contract |
| `generation_hash.py` | Deterministic generation fingerprint |
| `generation_audit.py` | Audit record assembly |
| `generation_pipeline.py` | Pipeline orchestration |
| `failure_strategy.py` | Retry/repair/failure policies |

---

## Verification

```bash
cd backend
python scripts/verify_writing_w5_generation.py   # 58/58
python scripts/verify_writing_w4_lesson_experience.py
python scripts/verify_writing_w3_lesson_planning.py
python scripts/verify_writing_w0_architecture.py
```

---

## Explicitly Out of Scope (W5)

- Runtime lesson delivery
- LLM / Gemini invocation
- Grading / evaluation execution
- Database persistence
- Retry loop implementation

**Stop after W5.**
