# Phase 2.1 — Facts Layer + Learning Narrative Foundation

**Status:** Complete
**Scope:** Facts Layer, Explainability Facts refactor, Learning Narrative Builder
**Not in scope:** Journey Builder, Lesson Experience Builder, Session Reservation, frontend migration, API redesign

---

## Implementation Summary

Phase 2.1 introduces two new backend packages and refactors explainability to a **facts-first** pipeline while preserving all existing API shapes via legacy adapters.

### New packages

| Package | Path | Role |
|---------|------|------|
| **Facts Layer** | `app/services/language_learning_facts/` | Assembles structured, language-neutral facts from stored metadata |
| **Learning Narrative Builder** | `app/services/language_learning_narrative/` | Sole owner of lesson-scoped student educational copy |

### Refactored modules

| Module | Change |
|--------|--------|
| `language_listening_explainability/signals.py` | **New** — signal extraction (breaks circular imports) |
| `language_listening_explainability/facts.py` | **New** — `ExplainabilityFacts` + `build_explainability_facts()` |
| `language_listening_explainability/builder.py` | Prose removed; legacy wrapper delegates to facts → narrative |
| `language_listening_explainability/engine.py` | Facts-first orchestration; `ExplainabilityResult.facts` added |
| `language_listening_explainability/student_summary.py` | Delegates to narrative legacy adapter |
| `language_listening_lesson_context.py` | Coach copy now sourced from Learning Narrative Builder |

---

## Architecture Impact

### Pipeline (Phase 2.1)

```
body_json metadata
      ↓
extract_signals() → ExplainabilitySignals
      ↓
assemble_lesson_facts() → LessonFactsBundle
build_explainability_facts() → ExplainabilityFacts
      ↓
build_lesson_narrative() → LessonNarrative   ← ONLY student copy owner
      ↓
legacy adapters → LessonExplainability / StudentSummary / coach fields
```

### Explainability role change

| Before | After |
|--------|-------|
| `build_lesson_explainability()` emitted full English sentences | `build_explainability_facts()` emits structured facts only |
| `build_student_summary()` constructed student prose | Narrative builder + `legacy_student_summary()` adapter |
| Coach context built inline templates | Coach fields mapped from `LessonNarrative` |

### Backward compatibility

- `generate_listening_explainability()` signature unchanged (optional kwargs added for progression context)
- `ExplainabilityResult` retains `lesson`, `student_summary`, `teacher_summary`, `learning_path`
- `ExplainabilityResult.facts` added (optional, populated in Phase 2.1)
- `build_listening_lesson_coach_context()` returns identical dict keys; values now from narrative builder
- Existing listening API responses unchanged (no route or schema changes)

### Documented debt (Phase 2.2+)

- `teacher_summary.py` and `learning_path.py` still contain teacher/journey prose (allowlisted)
- Legacy adapters still produce `StudentSummary` / `LessonExplainability` for Phase 3.4 callers
- Goal engine `selection_reason` strings remain diagnostic codes in metadata (not student copy)

---

## Verification Results

### Phase 2.1 script

```bash
python scripts/verify_language_adaptive_learning_phase_2_1.py
```

| Check | Result |
|-------|--------|
| narrative_package | PASS |
| facts_package | PASS |
| explainability_facts_module | PASS |
| no_student_copy_in_facts_explain | PASS |
| facts_no_student_phrases | PASS |
| result_has_facts | PASS |
| legacy_lesson_fields_populated | PASS |
| legacy_student_fields_populated | PASS |
| narrative_all_required | PASS |
| lesson_context_adapter | PASS |

**OVERALL: PASS**

### Regression (Phase 3.4)

```bash
python scripts/verify_language_adaptive_learning_phase_3_4.py
```

| Check | Result |
|-------|--------|
| Static audit (8 checks) | PASS |
| Simulation 500 lessons (6 checks) | PASS |
| missing_mandatory_fields | 0 |
| grounded_explanations | 500/500 |
| avg_coverage_completeness | 1.0 |

**OVERALL: PASS**

---

## Key Types

### `ExplainabilityFacts` (facts only)

Structured fields include:

- `selection_rationale` — primary engine, intent, stage, scores, goal alignment
- `situation` — situation_id, category, format, pace, difficulty band
- `curriculum_objectives`, `skill_focus`, `review_objectives`, `question_types`
- `weak_objectives` — `ObjectiveConfidenceFact` list
- `level_context` — official/lesson levels, mismatch codes
- `challenge` — band, score, streaks, reason codes
- `goal` — lesson_goal_id, alignment, hints
- `promotion_context` — readiness band, estimated remaining (when provided)
- `next_planning_signal_codes` — machine codes, not sentences

### `LessonNarrative` (student copy)

Owned fields:

- `reason_selected`, `why_this_lesson`, `student_focus`, `expected_improvement`
- `reward`, `coach_summary`, `challenge_reason`, `next_after_this`
- `situation_label`, `level_note`

---

## Known Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Legacy adapters duplicate some narrative in `LessonExplainability` fields | Medium | Remove adapters in Phase 2.2 when Lesson Experience Builder ships |
| Teacher/learning-path prose still outside narrative builder | Low | Phase 2.2+ journey builder migration |
| Coach copy wording changed slightly (now narrative-driven) | Low | Frontend unchanged; QA smoke recommended |
| Circular import between facts and explainability | Resolved | `signals.py` extraction module |

---

## Files Added

- `app/services/language_learning_facts/` (4 modules)
- `app/services/language_learning_narrative/` (4 modules)
- `app/services/language_listening_explainability/facts.py`
- `app/services/language_listening_explainability/signals.py`
- `scripts/verify_language_adaptive_learning_phase_2_1.py`
- `LANGUAGE-ADAPTIVE-LEARNING-PHASE-2.1-REPORT.md`

## Files Modified

- `app/services/language_listening_explainability/builder.py`
- `app/services/language_listening_explainability/engine.py`
- `app/services/language_listening_explainability/student_summary.py`
- `app/services/language_listening_explainability/teacher_summary.py`
- `app/services/language_listening_explainability/types.py`
- `app/services/language_listening_explainability/__init__.py`
- `app/services/language_listening_lesson_context.py`

---

## Next Phase (not started)

**Phase 2.2:** Session Reservation + Lesson Experience Builder + API reshape per canonical architecture v3.0.
