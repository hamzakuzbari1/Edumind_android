# Failure Strategy (W5)

Architecture-only. No runtime LLM. Documents how future generation runtime handles failures.

## Outcome Classification

| Outcome | Meaning | Lesson persisted? |
|---------|---------|-------------------|
| **success** | Normalize → validate pass; no repair needed | Yes |
| **soft_failure** | Repair restored structural fields from blueprint/mission | Yes (with audit flag) |
| **hard_failure** | Unrecoverable structural or consistency failure | No |

## Retry Policy

| Condition | Retry? | Max attempts |
|-----------|--------|--------------|
| Invalid JSON / not object | Yes | 2 |
| Missing required field (pre-repair) | Yes (re-prompt) | 2 |
| Hard validation after repair | No | — |
| Max retries exceeded | — | Hard failure |

Backoff: 500ms, 1500ms (future runtime).

**W5 does not implement retries** — policy is documented in `failure_strategy.py`.

## Repair Policy

Repair runs **once** when validation reports errors or warnings.

| Issue | Repair action | Source |
|-------|---------------|--------|
| Missing checklist | `restore_checklist_from_blueprint` | Blueprint |
| Missing tips | `restore_tips_from_mission` | Mission Builder |
| Missing learning outcomes | `restore_learning_outcomes_from_blueprint` | Blueprint |
| Missing success criteria | `restore_success_criteria_from_blueprint` | Blueprint |
| Missing constraints | `restore_constraints_from_mission` | Mission Builder |
| Wrong enum casing | `normalize_enum_casing` | Blueprint enum |
| Empty optional arrays | `fill_empty_optional_array` | Mission Builder |

**Forbidden repairs** (never applied):

- Invent grammar targets, vocabulary, outcomes, or criteria
- Change word limits or CEFR band
- Modify evaluation plan

## Hard Failure

Triggered when:

- Normalization fails after max retries
- Required fields still missing after repair
- Grammar/vocabulary/expected_output mismatch persists after repair

Pipeline returns `GenerationOutcome.hard_failure`. Audit record persisted; no canonical lesson.

## Soft Failure

Triggered when repair restored one or more fields from blueprint/mission but final validation passes.

Pipeline returns `GenerationOutcome.soft_failure`. Canonical lesson persisted with `repair_applied=true` in audit.

## Component Boundaries

| Component | May repair? | May retry LLM? |
|-----------|-------------|----------------|
| Response Normalizer | No | No |
| Lesson Validator | No | No |
| Repair Layer | Yes (structural) | No |
| Generation Pipeline | Orchestrates repair | Future runtime only |
