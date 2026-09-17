# PR-STAB-4 — Listening Progression Frontend Integration

Verification checklist for the listening promotion student journey.
**Backend:** unchanged (APIs only). **Scope:** listening only.

---

## Architecture

| Layer | Responsibility |
|-------|----------------|
| `src/api/language.js` | Thin wrappers for status, start, submit, promote |
| `src/composables/useListeningPromotion.js` | Single status cache, phase state machine, deduped status fetch |
| `StudentLanguageListeningPromotionView.vue` | Route orchestrator (`dashboard` → `session` → `result` → `success`) |
| `ListeningPromotion*Card.vue` | Status, session, result, success, history UI |
| `/student/languages/listening/promotion` | Dedicated promotion journey route |
| `/student/languages/listening` | Entry card linking to promotion route |

### API mapping (existing endpoints only)

| UI section | Endpoint | Method |
|------------|----------|--------|
| Promotion status + history | `/student/languages/listening/promotion-test/status` | GET |
| Start / resume session | `/student/languages/listening/promotion-test/start` | POST |
| Submit test | `/student/languages/listening/promotion-test/submit` | POST |
| Official promotion | `/student/languages/listening/promote` | POST |

### Status field mapping

| Display | API source |
|---------|------------|
| Official CEFR | `readiness.official_cefr` |
| Readiness band | `eligibility.readiness_status` / `readiness.status` |
| Readiness score | `readiness.readiness_score` |
| Stage band | `readiness.status` |
| Transition gate | `stability.prediction` |
| Promotion confidence | `stability.promotion_confidence` |
| Eligibility | `eligibility.eligible`, `eligibility.reason` |
| Primary blocker | `readiness.primary_blockers[0]` |
| Recommendations | `stability.prediction`, `latest_result.recommendation` |

Start button shown only when `eligibility.eligible === true` **and** `readiness.status === 'PROMOTION_AVAILABLE'`.

---

## Files added / modified

### Added
- `src/composables/useListeningPromotion.js`
- `src/views/student/languages/StudentLanguageListeningPromotionView.vue`
- `src/components/language/ListeningPromotionStatusCard.vue`
- `src/components/language/ListeningPromotionHistoryCard.vue`
- `src/components/language/ListeningPromotionSessionCard.vue`
- `src/components/language/ListeningPromotionResultCard.vue`
- `src/components/language/ListeningPromotionSuccessCard.vue`
- `backend/scripts/verify_listening_progression_frontend_pr_4.md`

### Modified
- `src/api/language.js` — promotion API functions
- `src/constants/app.js` — `STUDENT_LANGUAGES_LISTENING_PROMOTION`
- `src/router/index.js` — promotion route
- `src/views/student/languages/StudentLanguageListeningView.vue` — entry card
- `src/locales/en/student.json` — `listeningPromotion` strings
- `src/locales/ar/student.json` — `listeningPromotion` strings

---

## Manual verification

### 1. Complete student journey

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open `/student/languages/listening` | Entry card visible → promotion route |
| 2 | Open `/student/languages/listening/promotion` | Status loads (single GET status) |
| 3 | When `PROMOTION_AVAILABLE` | **Start Test** button shown |
| 4 | Start test | POST start → 5 assessments, timer, progress |
| 5 | Answer all 5, submit | POST submit → PASS/BORDERLINE/FAIL result |
| 6 | On PASS | **Promote** button shown |
| 7 | Promote | POST promote → old CEFR ↓ new CEFR, stage reset, next lesson |
| 8 | Continue | Returns to listening practice |

**Result:** PASS / FAIL

---

### 2. Empty states

| Case | Expected |
|------|----------|
| No promotion attempts | History card shows empty state |
| No primary blockers | Blocker section hidden |
| No recommendations | Recommendations list hidden |

**Result:** PASS / FAIL

---

### 3. Loading states

| Case | Expected |
|------|----------|
| Initial status load | `LoadingState` skeleton |
| Start test | Button loading spinner |
| Submit test | Submit button loading |
| Promote | Promote button loading |

**Result:** PASS / FAIL

---

### 4. Error states

| Case | Expected |
|------|----------|
| Status API failure | Error alert, no crash |
| Start when not eligible (403) | API reason shown |
| Submit duplicate (409) | Error alert, status refreshed |
| Expired session (410) | Expired message on session card |
| Promote when denied (409) | Warning alert with reason |

**Result:** PASS / FAIL

---

### 5. Promotion flow guards

| Case | Expected |
|------|----------|
| Not `PROMOTION_AVAILABLE` | No start button; readiness progress shown |
| Active session exists | Resume button (start returns existing session) |
| FAIL / BORDERLINE result | No promote button |
| PASS result | Promote button visible |

**Result:** PASS / FAIL

---

### 6. Promotion history

| Case | Expected |
|------|----------|
| After submit | `last_attempt`, `latest_result` reflected |
| Readiness score | Shown from status |
| Promotion confidence | Shown from `stability` |

**Result:** PASS / FAIL

---

### 7. No duplicated API calls

| Check | Expected |
|-------|----------|
| Mount promotion page | One GET `/promotion-test/status` |
| Start test | One POST `/start` (no extra status before start) |
| After submit | One POST `/submit` + one status refresh |
| After promote | One POST `/promote` + one status refresh |

**Result:** PASS / FAIL

---

## Regression

| Area | Check | Result |
|------|-------|--------|
| Listening practice | `/student/languages/listening` still loads adaptive clips | PASS / FAIL |
| Language module tabs | Other routes unaffected | PASS / FAIL |
| Backend | No Python/service changes in this PR | PASS |
| STAB-1/2/3 | Backend verify scripts unchanged | PASS |

---

## Summary

| Section | Result |
|---------|--------|
| Complete student journey | PASS / FAIL |
| Empty states | PASS / FAIL |
| Loading states | PASS / FAIL |
| Error states | PASS / FAIL |
| Promotion flow | PASS / FAIL |
| Promotion history | PASS / FAIL |
| No duplicate API calls | PASS / FAIL |
| Regression | PASS / FAIL |

**Overall PR-STAB-4:** PASS / FAIL
