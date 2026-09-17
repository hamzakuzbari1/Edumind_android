# Writing W0 — Architecture Report

**Phase:** W0 (Architecture Preparation)
**Status:** Complete — **204/204 verification checks passed**
**Date:** 2026-07-11

---

## 1. Executive Summary

W0 establishes the canonical Writing skill package structure, data contracts, enums, ownership registry, schema plan, and verification harness. **No lesson generation, AI feedback, frontend, or progression behavior was implemented.**

Legacy `language_writing_service.py` is preserved unchanged. All new code is types/contracts only.

---

## 2. Backend Inventory (Existing Writing)

### Tier 1 — Primary runtime (reuse → migrate gradually)

| Module | Purpose | Owner today | W0 disposition |
|--------|---------|-------------|----------------|
| `language_writing_service.py` | List/get/submit prompts; AI+rule scoring | Legacy monolith | **Reuse** until W6+ replaces submit flow |
| `api/language_student.py` (writing routes) | REST CRUD for writing | API layer | **Reuse** → bundle routes in W7+ |
| `models/language/progress.py` (`LanguageWritingProgress`) | Submission persistence | Models | **Extend** per schema plan |
| `schemas/language_learning.py` (Writing*Out) | Legacy flat I/O | Schemas | **Replace** with `language_writing_bundles.py` in W7 |

### Tier 2 — Scoring (shared, internal to coach in future)

| Module | Disposition |
|--------|-------------|
| `language_placement_ai_scoring.py` (`score_writing_ai`) | **Reuse** as coach internal signal (W6) |
| `language_placement_scoring_service.py` (`score_writing`) | **Reuse** as fallback |
| `language_exam_service.py` (writing grade path) | **Replace** later — duplicate scoring |

### Tier 3 — Progression (partial)

| Module | Disposition |
|--------|-------------|
| `language_progression_service.py` | **Reuse** — maps `official_writing_cefr` |
| `language_official_promotion/` | **Extend** — listening-only today; writing in W10 |
| `language_writing_progression/` | **Missing → Created in W0** (types only) |

### Tier 4 — Content

| Asset | Disposition |
|-------|-------------|
| `alembic/seeds/language_content/writing_*.json` (60 prompts) | **Reuse** → migrate to Topic Universe in W13 |
| `language_lesson_generation_service.py` (writing branch) | **Extend** in W5 |

### Tier 5 — Cross-skill analytics (unchanged in W0)

~20 services reference writing for XP, hub, achievements, BKT — **reuse**, no W0 changes.

### Missing owners (addressed by new packages)

- `language_writing_progression/` — **Created**
- Official writing promotion engine — **Created** (`language_writing_official_promotion/`)
- WPA builder — **Created** (`language_writing_promotion_test/`)
- CEFR writing validator — **W5** (generation phase)
- Revision/coach loop — **Created** (types in W0, behavior W6)

---

## 3. Ownership Table

| Package | Single responsibility |
|---------|----------------------|
| `language_writing_topic_universe` | Canonical topic catalog, topic nodes, complexity curves |
| `language_writing_knowledge_chain` | Chain registry, nodes, prerequisites, chain progress |
| `language_writing_grammar_progression` | Grammar structure 4-state mastery |
| `language_writing_lexis_progression` | Categorized lemma 4-state mastery + balance plans |
| `language_writing_curriculum` | Selection, arc stages, goal profiles, anti-repetition |
| `language_writing_generation` | Generation metadata + `body_json` key conventions |
| `language_writing_explainability` | Writing facts assembly (`WritingLessonFacts`, `TrendFacts`) |
| `language_writing_revision` | Draft/revision lifecycle orchestration |
| `language_writing_coach` | Coach output contract, trend detection, personality |
| `language_writing_portfolio` | Educational archive — **never** affects scoring/progression |
| `language_writing_lesson_experience` | `WritingLessonExperienceBundle` assembly |
| `language_writing_journey` | `WritingJourneyBundle` assembly |
| `language_writing_progression` | Post-completion progression runtime |
| `language_writing_promotion_test` | Goal-specific WPA task bundles |
| `language_writing_official_promotion` | **Sole runtime writer** of `official_writing_cefr` |

**Shared infrastructure (not skill engines):**

- `language_writing/enums.py` — canonical enums
- `language_writing/ownership.py` — registry + DAG
- `language_learning_facts/` — shared facts patterns
- `language_learning_narrative/` — narrative builders (W7+)
- `language_learning_goal/` — extended in W2

---

## 4. Dependency Diagram

```
catalog layer
  topic_universe
  knowledge_chain ──► topic_universe
  grammar_progression
  lexis_progression

selection layer
  curriculum ──► topic_universe, knowledge_chain, grammar, lexis
  generation ──► topic_universe, knowledge_chain, curriculum

facts layer
  explainability ──► catalog + curriculum

pedagogy layer
  coach ──► grammar, lexis
  revision ──► coach

experience layer
  lesson_experience ──► explainability, revision, coach

journey layer
  journey ──► explainability, coach, progression, promotion_test

progression layer
  progression ──► explainability
  promotion_test ──► topic_universe, curriculum
  official_promotion ──► promotion_test, progression

portfolio (sidecar — no progression reads)
  portfolio ──► revision, coach
```

**Canonical delivery stack (unchanged):**

```
Facts (explainability)
    ↓
Learning Narrative (language_learning_narrative — W7+)
    ↓
Lesson Experience (language_writing_lesson_experience)
    ↓
Journey (language_writing_journey)
    ↓
Render-only Frontend (W12)
```

---

## 5. Package Tree

```
backend/app/services/
├── language_writing/
│   ├── __init__.py
│   ├── enums.py
│   └── ownership.py
├── language_writing_topic_universe/
├── language_writing_knowledge_chain/
├── language_writing_grammar_progression/
├── language_writing_lexis_progression/
├── language_writing_curriculum/
├── language_writing_generation/
├── language_writing_explainability/
├── language_writing_revision/
├── language_writing_coach/
├── language_writing_portfolio/
├── language_writing_lesson_experience/
├── language_writing_journey/
├── language_writing_progression/
├── language_writing_promotion_test/
├── language_writing_official_promotion/
└── language_writing_service.py          # legacy — preserved

backend/app/schemas/
└── language_writing_bundles.py          # API contracts (W0)

backend/alembic/sql/
└── W0_writing_schema_plan.sql           # planned DDL — not applied

backend/scripts/
└── verify_writing_w0_architecture.py
```

Each `language_writing_*/` package contains `__init__.py` (RESPONSIBILITY) + `types.py` (contracts).

---

## 6. Canonical Data Contracts (W0)

| Contract | Owner package |
|----------|---------------|
| `WritingTopicNode` | topic_universe |
| `WritingKnowledgeChainNode` | knowledge_chain |
| `WritingArcStageDefinition`, `WritingGoalProfile` | curriculum |
| `WritingGenerationSpec`, `WritingCurriculumMetadata` | generation |
| `WritingGrammarState` | grammar_progression |
| `WritingLexisState`, `LexisBalancePlan` | lexis_progression |
| `WritingLessonFacts`, `ContextComplexityFacts`, `TrendFacts` | explainability |
| `WritingDraft`, `WritingRevision`, `WritingRevisionSession` | revision |
| `WritingFeedback`, `CoachTrendSnapshot` | coach |
| `WritingMission`, `WritingLessonExperienceBundle` | lesson_experience |
| `WritingJourneyBundle` | journey |
| `WritingPortfolioEntry` | portfolio |
| `WritingPromotionBundle`, `WritingGoalPromotionBundle` | promotion_test |
| `WritingOfficialPromotionResult` | official_promotion |
| `WritingProgressionResult` | progression |

API Pydantic mirrors: `language_writing_bundles.py`

---

## 7. Enums (`language_writing/enums.py`)

- `OfficialWritingCEFR`, `WritingArc`, `WritingGoal`, `WritingCoachPersonality`
- `ContextComplexity` (1–5), `LexisCategory`, `GrammarState`, `LexisState`
- `WritingLessonLifecycle`, `WritingRevisionStatus`, `PromotionStatus`
- `WritingTopicId` (16 canonical topics v1)

---

## 8. Schema Plan

Documented in `alembic/sql/W0_writing_schema_plan.sql` (comment-only — **not migrated in W0**):

- Extend `language_writing_progress` (lifecycle, draft history, coach turns)
- `language_writing_reservations`
- `language_writing_lexis_state` (with category)
- `language_writing_grammar_state`
- `language_writing_chain_progress`
- `language_writing_trend_snapshot`
- `language_writing_portfolio_entry`
- `context_complexity` in `body_json.writing_curriculum`

---

## 9. Architecture Validation

| Rule | Result |
|------|--------|
| Single ownership per package | PASS |
| No circular imports (types modules) | PASS |
| Layer DAG respected | PASS |
| Facts/narrative separation | PASS |
| Portfolio isolated from progression | PASS |
| Lesson bundle forbids journey keys | PASS |
| No API/frontend imports in packages | PASS |
| Legacy service preserved | PASS |

---

## 10. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Legacy monolith coupling** | High | Gradual migration; legacy API stays until W7 bundles ship |
| **Schema migration scope** | High | Apply incrementally W1–W6; plan documented |
| **`LanguageWritingProgress` lacks lifecycle** | High | First migration in W1 or W6 before revision loop |
| **Dual scoring paths** (practice vs exam) | Medium | Consolidate in W6 coach engine |
| **Goal enum divergence** | Medium | `WritingGoal` vs `LearningGoal` — unify in W2 |
| **Portfolio/progression isolation** | Medium | Enforced in ownership + verification |
| **Topic catalog maintenance** | Medium | Versioned catalog in W1; no ad-hoc generation |
| **TrendFacts ownership** | Low | Facts shape in explainability; coach produces `CoachTrendSnapshot` |
| **Performance (draft history JSONB)** | Low | Cap draft history size in W6 |
| **Frontend still legacy** | Expected | W12 rewrite; no W0 change |

---

## 11. Verification

```bash
cd backend
python scripts/verify_writing_w0_architecture.py
```

**Result: 204/204 PASS**

---

## 12. W1 Readiness Decision

| Criterion | Status |
|-----------|--------|
| Package structure complete | ✅ |
| Ownership registry complete | ✅ |
| Contracts + enums defined | ✅ |
| Schema plan documented | ✅ |
| Verification green | ✅ |
| No forbidden W0 scope creep | ✅ |

### Decision: **W1 READY**

W1 may begin: **Topic Universe + Three-layer catalog** (`language_writing_topic_universe`, `language_writing_knowledge_chain`, arc definitions in curriculum).

**Gate before W7:** W6-QA mandatory browser vertical slice (per approved architecture).

---

## 13. Approval Checklist (W0 complete)

- [x] 15 writing packages with real ownership
- [x] Canonical enums and contracts
- [x] API bundle schemas (closed contracts)
- [x] Schema plan (no premature migration)
- [x] Ownership DAG + layer rules
- [x] Verification script green
- [x] Legacy service preserved
- [x] Portfolio/progression boundary enforced

**W0 complete. Awaiting explicit go-ahead for W1.**
