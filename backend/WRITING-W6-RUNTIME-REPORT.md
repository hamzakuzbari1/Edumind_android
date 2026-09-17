# Writing W6 — Runtime Implementation Report

**Phase:** W6 — first implementation phase
**Runtime version:** `6.0.0`
**Status:** Complete — verification green (mock provider)
**Frozen dependencies:** W0–W5 architecture unchanged

---

## Executive Summary

W6 implements the **Writing Runtime** using the frozen W0–W5 pipeline. Claude is the generation engine, accessed **only** through `WritingModelProvider.generate()`. Educational decisions remain in the Lesson Blueprint; Claude rephrases presentation only.

**Not in W6:** evaluator, grading, revision, scoring, portfolio, progression, promotion.

---

## Runtime Pipeline (implemented)

```
Student
  → Lesson Planner → Lesson Blueprint
  → Mission Builder → Prompt Builder
  → WritingModelProvider → Claude
  → Response Normalizer → Lesson Validator → Repair Layer
  → Canonical Lesson → Generation Audit → persist → Student
```

Entry points:

- `generate_writing_lesson()` — core runtime
- `generate_writing_lesson_for_student()` — API service wrapper
- `POST /api/student/languages/writing/generate` — HTTP endpoint

---

## 1. WritingModelProvider

**Package:** `language_writing_runtime/`

| Property / method | Purpose |
|-------------------|---------|
| `generate()` | Sole LLM invocation path |
| `provider_name` | e.g. `claude`, `mock` |
| `model_name` | e.g. `claude-sonnet-5` |
| `temperature` | Generation temperature |
| `max_tokens` | Output token limit |
| `capabilities` | Future flags (JSON mode, streaming, local) |

Factory: `get_writing_model_provider()` — supports `claude`, `mock`; prepared for GPT/Gemini/local without architecture change.

---

## 2. Claude Runtime

**Module:** `providers/claude_writing_provider.py`

- Input: `WritingPromptBundle` (via `WritingModelGenerateRequest`)
- Output: raw JSON text (`WritingModelGenerateResponse`)
- Uses `claude_service.generate_claude_json` — **only** inside provider
- Maps timeouts/rate limits to `WritingRuntimeException` (structured errors)

---

## 3. Generation Runtime

**Module:** `generation_runtime.py`

Connects frozen components without duplicated logic:

1. `assemble_blueprint`
2. `build_prompt_from_blueprint`
3. `WritingModelProvider.generate`
4. `process_llm_generation` (W5 frozen pipeline)

Retry on normalization failure per W5 failure strategy.

---

## 4. Persistence

**Module:** `persistence.py`

Stored in `LanguageContentItem.body_json`:

- `writing_blueprint` — full blueprint dict
- `writing_generation` — W5 audit + `model_name`, `provider_name`, `runtime_version`
- `canonical_lesson` — student-facing lesson
- Legacy-compatible `prompt`, `min_words`, `max_words`

---

## 5. Error Handling

**Module:** `errors.py`

Structured `WritingRuntimeError` codes — no raw Anthropic exceptions in API responses:

| Code | Scenario |
|------|----------|
| `provider_timeout` | Claude timeout |
| `provider_rate_limit` | Rate limit |
| `provider_unavailable` | Missing API key |
| `malformed_json` | Normalization failure |
| `validation_failure` | Post-repair validation fail |
| `repair_success` | Soft failure — lesson OK |
| `generation_gate_closed` | Circuit breaker |

---

## 6. Configuration

| Setting | Default |
|---------|---------|
| `WRITING_MODEL_PROVIDER` | `claude` |
| `WRITING_GENERATION_TEMPERATURE` | `0.3` |
| `WRITING_GENERATION_MAX_TOKENS` | `4096` |
| `WRITING_GENERATION_TIMEOUT_SECONDS` | `120` |

Use `WRITING_MODEL_PROVIDER=mock` for offline verification.

---

## Verification

```bash
cd backend
python scripts/verify_writing_w6_runtime.py
python scripts/manual_qa_writing_w6.py --goal travel
python scripts/manual_qa_writing_w6.py --goal ielts
python scripts/manual_qa_writing_w6.py --goal business
```

Prior frozen phases remain valid:

```bash
python scripts/verify_writing_w5_generation.py
python scripts/verify_writing_w4_lesson_experience.py
```

---

## Manual QA

See `language_writing_runtime/MANUAL_QA_CHECKLIST.md`.

---

## Stop after W6

No evaluator, revision, scoring, portfolio, progression, or promotion work started.
