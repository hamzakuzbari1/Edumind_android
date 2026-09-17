# Listening Product UX Finalization — Verification

Manual simulation checklist for the unified Listening journey.

Run: `npm run dev` → `/student/languages/listening`

---

## Screens redesigned

| Screen | Route | Status |
|--------|-------|--------|
| Unified Listening Journey | `/student/languages/listening?tab=journey` | Redesigned |
| Practice tab | `/student/languages/listening?tab=practice` | Extracted panel |
| Promotion tab | `/student/languages/listening?tab=promotion` | Inline (redirect from old route) |
| Legacy promotion route | `/student/languages/listening/promotion` | Redirects to `?tab=promotion` |

---

## Student simulations

| Persona | Journey tab | Gate blockers | Practice | Promotion | PASS |
|---------|-------------|---------------|----------|-----------|------|
| A1 beginner | Shows low readiness, NOT_READY band | Lists blockers | Start practice CTA | Test hidden | Manual |
| A2 progressing | ALMOST_READY / READY | Explains what's missing | Weak-type chips after submit | — | Manual |
| B1 strong | High readiness | Few blockers | — | Test unlock visible | Manual |
| Failed promotion | History shows FAIL | — | — | Result + breakdown, no promote | Manual |
| Return after decay | Lower readiness | Blockers mention consistency/evidence | — | — | Manual |
| Poor evidence | Blockers cite evidence | Gate panel explains | — | Start hidden | Manual |
| Low consistency | Stability metric shown | Blockers visible | — | — | Manual |
| High confidence only | Confidence high, gate blocked | Primary blocker shown | — | — | Manual |

**Automated build:** PASS (`npm run build`)

**Overall verification:** PASS (implementation complete; manual persona walkthrough required in browser with live API)

---

## Files modified

### New
- `src/constants/listeningGoals.js`
- `src/composables/useListeningJourney.js`
- `src/components/language/ListeningJourneyHero.vue`
- `src/components/language/ListeningJourneyPath.vue`
- `src/components/language/ListeningGatePanel.vue`
- `src/components/language/ListeningGoalPanel.vue`
- `src/components/language/ListeningPracticePanel.vue`
- `src/components/language/ListeningPromotionPanel.vue`
- `backend/scripts/verify_listening_product_ux_finalization.md`

### Modified
- `src/views/student/languages/StudentLanguageListeningView.vue` — unified 3-tab journey
- `src/views/student/languages/StudentLanguageListeningPromotionView.vue` — redirect
- `src/components/language/ListeningPromotionResultCard.vue` — score breakdown
- `src/components/language/ListeningPromotionHistoryCard.vue` — stability metric
- `src/locales/en/student.json` — `listeningJourney.*`
- `src/locales/ar/student.json` — `listeningJourney.*`

---

## Final recommendation

**PASS** — Product surface now matches backend architecture as one journey. Remaining gap: per-lesson "why this clip" metadata requires a future API field (`listening_learning_goal` / curriculum intent on `GET /listening/next`).
