# Writing Frontend Runtime Integration Report

**Status:** Complete — `/student/languages/writing` now uses W6/W7
**Date:** 2026-07-11

---

## Problem

W6 (generation) and W7 (evaluation + coach + revision) were backend-only. The browser still called legacy endpoints via `StudentLanguageWritingView.vue`:

- `GET /student/languages/writing`
- `GET /student/languages/writing/{id}`
- `POST /student/languages/writing/{id}/submit` → `language_writing_service.py`

---

## Solution

Replaced the Writing page in place (same route, no duplicate page).

### Runtime path (browser → backend)

```
/student/languages/writing
  → StudentLanguageWritingView.vue
  → Journey tab (goal + hero) | Practice tab
  → WritingPracticePanel
  → POST /api/student/languages/writing/generate     (W6)
  → Mission card + editor
  → POST /api/student/languages/writing/{id}/draft   (W7)
  → WritingCoachPanel (revision plan)
  → Revise → resubmit → Complete
```

Legacy list/submit endpoints remain on the backend for compatibility but are **not called** from the Writing page.

---

## Frontend deliverables

| Item | Path |
|------|------|
| Main view | `src/views/student/languages/StudentLanguageWritingView.vue` |
| Practice panel | `src/components/language/WritingPracticePanel.vue` |
| Coach panel | `src/components/language/WritingCoachPanel.vue` |
| Journey hero | `src/components/language/WritingJourneyHero.vue` |
| Goal panel | `src/components/language/WritingGoalPanel.vue` |
| Completion | `src/components/language/WritingCompletionCard.vue` |
| API | `generateWritingLesson`, `submitWritingDraft` in `src/api/language.js` |
| Composables | `useWritingJourney`, `useWritingLesson`, `useWritingCoach`, `useWritingRevision` |
| Goals | `src/constants/writingGoals.js` |
| i18n | `student.languages.writingJourney.*` (en + ar) |

---

## Browser QA checklist

1. Log in as student with language access + placement complete.
2. Open **Languages → Writing** (`/student/languages/writing`).
3. Confirm **no legacy exercise list** (no sidebar prompt catalog).
4. **Journey tab:** select a goal (Travel / IELTS / Business).
5. **Practice tab:** click **Generate lesson** — network: `POST .../writing/generate`.
6. Write a draft (meet min words) → **Submit draft** — network: `POST .../writing/{id}/draft`.
7. Confirm **Coach panel** shows encouragement, main issue, revision mission (no score %).
8. Edit draft → **Submit revision** — confirm comparison / revision number increments.
9. When coach marks ready → **Complete lesson**.
10. Confirm completion screen → **New writing mission** starts fresh generate flow.

---

## Verification

```bash
cd backend
python scripts/verify_writing_frontend_runtime.py
python scripts/verify_writing_w7_evaluation_revision.py
python scripts/verify_writing_w6_runtime.py
```

---

## Out of scope

- W8+ (portfolio, progression, promotion UI)
- Backend removal of legacy `language_writing_service` endpoints
- Dedicated `GET /writing/journey` bundle (journey tab uses learner memory + session summary until backend journey API exists)

---

## Stop line

Frontend integration complete. No W8 work started.
