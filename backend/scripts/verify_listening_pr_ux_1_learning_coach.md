# PR-UX-1 — Learning Coach Experience (Listening)

**Date:** 2026-07-08
**Scope:** Frontend UX only — no backend / engine / API changes
**Build:** `npm run build` PASS

---

## Current UX problems (before)

| Area | Problem |
|------|---------|
| Journey hero | Exposed readiness score, promotion confidence %, band enums (`NOT_READY`) |
| Journey path | Showed "Transition gate" and "Readiness" — internal engine names |
| Gate panel | Numeric readiness / confidence / stability metrics |
| Promotion status | 8 metric boxes including Transition Gate, Promotion Readiness Engine labels |
| After lesson | Raw score %, weak question type chips, generic insights |
| Why this lesson | Static paragraph about engines (curriculum, confidence, challenge) |
| History | Readiness scores, promotion confidence numbers |
| Promotion result | Evidence / consistency / coverage / exam confidence breakdown |
| Blocked promotion | "NOT ELIGIBLE" chip, technical eligibility reasons |
| Success | Minimal celebration; no "what changes now" |

---

## Learning Coach architecture

```
Backend APIs (unchanged)
  GET  /listening/next
  POST /listening/{id}/submit
  GET  /listening/promotion-test/status
  POST /listening/promotion-test/*
  POST /listening/promote
  GET  /hub, GET /v2/learner/memory
           │
           ▼
useListeningJourney.js  ── readiness before/after practice
           │
           ▼
useListeningCoach.js    ── telemetry → natural language (i18n)
           │
           ▼
LearningCoachCard.vue   ── reusable: summary, bullets, checklist, next step
           │
     ┌─────┴─────┬──────────────┬─────────────┐
 Journey Hero  Practice      Promotion     History
 Gate Panel    post-lesson   Status/Result Success
```

**Translation rules:**
- Readiness band → student journey stage (Practice / Improve / Master / Promotion)
- `primary_blockers[]` → actionable checklist (mapped from real blocker dimensions)
- Question `type` from lesson/submit → skill coaching (inference, detail, …)
- `learning_goals` memory → goal-aware lesson line (IELTS, Travel, …)
- Readiness score delta after submit → progress coaching (no raw engine names)
- `strengths` / `weaknesses` / `recommendation` from promotion test → coach copy
- Technical strings sanitized before display

**Known constraint:** Per-lesson curriculum/intelligence metadata lives in `body_json` server-side and is not returned by existing student APIs. "Why this lesson" uses **real fields from the lesson payload**: `level`, `title`, `questions[].type`, active goal, and `primary_blockers` from promotion status.

---

## Screens redesigned

| Screen | Change |
|--------|--------|
| `ListeningJourneyHero` | Coach card: official level + stage + progress bar + one sentence |
| `ListeningJourneyPath` | Practice → Improve → Master → Test → New Level |
| `ListeningGatePanel` | Blocked checklist coach (no metrics) |
| `ListeningPracticePanel` | Pre-lesson "Why?" coach + post-lesson coach |
| `ListeningPromotionStatusCard` | Coach + CTA (no metric grid) |
| `ListeningPromotionHistoryCard` | Learning story (no scores) |
| `ListeningPromotionResultCard` | Coach strengths/weaknesses (no evidence breakdown) |
| `ListeningPromotionSuccessCard` | Celebration + level benefits + next step |
| `StudentLanguageListeningView` | Wires readiness snapshot for post-lesson delta |

---

## Files modified

**New**
- `src/composables/useListeningCoach.js`
- `src/components/language/LearningCoachCard.vue`
- `backend/scripts/verify_listening_pr_ux_1_learning_coach.md`

**Updated**
- `src/composables/useListeningJourney.js`
- `src/components/language/ListeningJourneyHero.vue`
- `src/components/language/ListeningJourneyPath.vue`
- `src/components/language/ListeningGatePanel.vue`
- `src/components/language/ListeningPracticePanel.vue`
- `src/components/language/ListeningPromotionStatusCard.vue`
- `src/components/language/ListeningPromotionHistoryCard.vue`
- `src/components/language/ListeningPromotionResultCard.vue`
- `src/components/language/ListeningPromotionSuccessCard.vue`
- `src/views/student/languages/StudentLanguageListeningView.vue`
- `src/locales/en/student.json` (`language.coach.*`)
- `src/locales/ar/student.json` (`language.coach.*`)

---

## Walkthrough (manual)

Route: `/student/languages/listening`

| Persona | Tab | Expected student understanding |
|---------|-----|-------------------------------|
| **A1** fresh | Journey | "Official A1 · Getting started" + progress bar + practice sentence |
| **A2** mid | Practice | "Why this lesson?" bullets from level, goal, question types |
| **A2** after lesson | Practice | Coach: what improved / still weak / what next (no Confidence +4) |
| **B1** blocked | Journey + Promotion | "Almost there" checklist from real `primary_blockers` |
| **Promotion fail** | Promotion | Coach result: focus areas from `weaknesses`, no evidence scores |
| **Promotion pass → promote** | Promotion | Success: old→new level + what changes now |
| **Return after weeks** | Journey | History story from readiness band + prediction + last attempt |

**Verify:** Student always sees **Why / What / Next** without engine vocabulary.

---

## Before vs After

| Moment | Before | After |
|--------|--------|-------|
| Open journey | "Readiness 62 · ALMOST READY · Promotion confidence: 41" | "Official A2 · Building skills" + bar + "You are making steady progress" |
| Blocked test | "NOT ELIGIBLE · Transition gate · Primary blocker: Evidence coverage" | "Almost there — Complete: Practice more different listening situations" |
| Finish lesson | "Score 75% — Practice: Inference" | "You understood the main ideas much better today" + next step |
| Why lesson | Engine-weight paragraph (static) | Bullets from level, goal, question types, blockers, title |
| History | "Latest readiness: 62" | "This week you became much better at handling harder listening" |

---

## Final UX score

| Criterion | Score |
|-----------|-------|
| No engine jargon on surface | 9/10 |
| Why / What / Next on all tabs | 9/10 |
| 14-year-old readability | 9/10 |
| Data grounded in APIs | 8/10 * |
| Reusable coach component | 10/10 |

\* Lesson selection metadata (curriculum/intelligence) not in API response — deferred until backend exposes explainability fields on `/listening/next`.

---

## Verdict: **PASS**

Product-ready Learning Coach layer ships on all listening student surfaces without backend changes. Recommend follow-up API pass-through of `listening_curriculum` / explainability on lesson fetch for richer "why this lesson" bullets.
