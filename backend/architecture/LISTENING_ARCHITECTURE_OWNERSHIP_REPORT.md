# Listening — Architecture Ownership Report

**Phase:** 2.1.1 — Narrative Ownership Guard
**Status:** Active enforcement via static guard
**Guard script:** `backend/scripts/verify_language_narrative_ownership_guard.py`

---

## Architecture Rule

> **Learning Narrative Builder is the only owner of student-facing educational copy.**

Allowed producer path:

```
app/services/language_learning_narrative/
├── builder.py          ← primary student copy owner
├── legacy_adapter.py   ← backward-compat bridge to Phase 3.4 types
├── types.py            ← narrative output schemas (no runtime copy)
└── __init__.py
```

Verification fails if **new** educational prose appears outside this package.

---

## Facts Owners

| Component | Path | Owns | Must NOT emit |
|-----------|------|------|----------------|
| **Facts Layer** | `language_learning_facts/` | Structured lesson/journey facts | Student sentences |
| **Signal extraction** | `language_listening_explainability/signals.py` | Raw metadata → signals | Student sentences |
| **Explainability Facts** | `language_listening_explainability/facts.py` | `ExplainabilityFacts` | Student sentences |
| **Curriculum Engine** | `language_listening_curriculum/` | Scores, objectives, intents | Student sentences |
| **Intelligence Engine** | `language_listening_intelligence/` | Plans, situations, rotation | Student sentences |
| **Goal Engine** | `language_learning_goal/` | Goal alignment, profiles (LLM) | Student UI copy |
| **Challenge Engine** | `language_listening_challenge/` | Bands, streaks, adjustments | Student sentences |
| **Confidence Engine** | `language_listening_confidence/` | Coverage, mastery, evidence | Student sentences |
| **Promotion / Stage** | `language_learning_stage/`, promotion services | Readiness facts | Student sentences (journey copy → Phase 2.2) |
| **Lesson context adapter** | `language_listening_lesson_context.py` | Maps narrative → legacy `coach` dict | **No inline templates** (Phase 2.1) |

### Internal generation (excluded from student-copy guard)

| Path | Purpose |
|------|---------|
| `**/prompt.py` | LLM generation directives |
| `**/profiles.py` | Style directives for transcript generation |

These feed the model; they are not student UI API copy.

---

## Narrative Owners

| Owner | Module | Student copy fields |
|-------|--------|---------------------|
| **Learning Narrative Builder** | `language_learning_narrative/builder.py` | `reason_selected`, `why_this_lesson`, `student_focus`, `expected_improvement`, `reward`, `coach_summary`, `challenge_reason`, `next_after_this`, `level_note`, `after_lesson.*` |
| **Legacy adapter** | `language_learning_narrative/legacy_adapter.py` | Maps narrative → `LessonExplainability`, `StudentSummary` for Phase 3.4 callers |

---

## Legacy Adapters (backward compatibility)

| Adapter | Input | Output | Remove when |
|---------|-------|--------|-------------|
| `legacy_lesson_explainability()` | `LessonNarrative` + `ExplainabilityFacts` | `LessonExplainability` | Lesson Experience Builder ships (Phase 2.2) |
| `legacy_student_summary()` | `LessonNarrative` + facts | `StudentSummary` | Lesson Experience Builder ships |
| `build_listening_lesson_coach_context()` | Narrative builder | Legacy `coach` API dict | `LessonExperienceBundle` replaces coach |
| `build_student_summary()` / `build_lesson_explainability()` | Thin wrappers | Legacy types | Phase 2.2 API reshape |

---

## Deprecated Generators (frozen debt)

These modules still contain prose **outside** the narrative owner. Fingerprints are frozen in:

`backend/architecture/listening_narrative_debt_manifest.json`

| Module | Violations | Nature | Target removal |
|--------|------------|--------|----------------|
| `language_listening_explainability/teacher_summary.py` | 8 strings | Teacher-facing explainability prose | Phase 2.2+ (teacher facts + narrative) |
| `language_listening_explainability/learning_path.py` | 6 strings | Journey `next_recommendation` prose | Journey Builder (Phase 2.2) |

**Guard rule:** Debt manifest must not grow. Any new fingerprint outside `language_learning_narrative/` fails CI verification.

---

## Remaining Technical Debt

| ID | Item | Owner today | Target owner | Phase |
|----|------|-------------|--------------|-------|
| D1 | Teacher summary prose | `teacher_summary.py` | Teacher facts + narrative (or admin-only API) | 2.2+ |
| D2 | Learning path `next_recommendation` prose | `learning_path.py` | Journey Builder + narrative | 2.2 |
| D3 | Legacy `LessonExplainability` / `StudentSummary` types | explainability package | Remove after bundle migration | 2.2 |
| D4 | Legacy `coach` dict on listening API | `language_listening_lesson_context.py` | `LessonExperienceBundle.narrative` | 2.2 |
| D5 | Frontend `useListeningCoach` composition | Vue composables | Render-only bundles | 2.2 (frontend) |

---

## Guard Implementation

| Artifact | Purpose |
|----------|---------|
| `app/architecture/narrative_ownership_guard.py` | AST scanner + heuristics |
| `scripts/verify_language_narrative_ownership_guard.py` | CLI verification |
| `architecture/listening_narrative_debt_manifest.json` | Frozen grandfathered violations |

### Detection layers

1. **Phrase catalog** — "Great work", "You improved", "Practice more", etc.
2. **Second-person coaching** — `\b(you|your)\b` + educational verbs
3. **Mission openers** — "This lesson", "Today you", "Curriculum selected"
4. **Teacher prose patterns** — confidence/journey recommendation strings
5. **Deprecated generator sweep** — extra scrutiny on `*_summary.py`, `learning_path.py`
6. **Docstring exclusion** — AST docstrings not counted as violations

### Required before Phase 2.2

```bash
cd backend
python scripts/verify_language_narrative_ownership_guard.py
python scripts/verify_language_adaptive_learning_phase_2_1.py
```

Both must PASS.

---

## Single Owner Summary

| Visible to student | Single owner | Allowed source |
|--------------------|--------------|----------------|
| Lesson mission copy | Learning Narrative Builder | `language_learning_narrative/builder.py` |
| Post-lesson copy | Learning Narrative Builder | `build_after_lesson_narrative()` |
| Coach API fields (interim) | Learning Narrative Builder via adapter | `language_listening_lesson_context.py` maps narrative only |
| Engine reasoning | Facts Layer | No sentences |
| Journey timeline copy | **Not yet migrated** | Debt: `learning_path.py` → Journey Builder in 2.2 |
| Teacher dashboard copy | **Not yet migrated** | Debt: `teacher_summary.py` |

---

**Document version:** 1.0 (Phase 2.1.1)
