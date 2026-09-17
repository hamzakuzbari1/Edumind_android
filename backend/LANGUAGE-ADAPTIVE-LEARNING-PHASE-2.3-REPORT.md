# Language Adaptive Learning — Phase 2.3 Report

**Phase:** 2.3 — Lesson Experience Builder + Journey Builder + Frontend Render-Only
**Status:** Complete (implementation)
**Builder version:** 2.3.0
**Architecture reference:** `docs/LISTENING_CANONICAL_EXPERIENCE_ARCHITECTURE.md` v3.0

---

## Summary

Phase 2.3 replaces the fragmented listening student experience with the canonical two-bundle architecture:

| Bundle | Builder | Scope |
|--------|---------|-------|
| `LessonExperienceBundle` | Lesson Experience Builder | One lesson — narrative, playback, after-lesson |
| `ListeningJourneyBundle` | Journey Builder | Journey — official level, target, personal goal, promotion, timeline, history |

The Vue frontend is now **render-only**: it fetches bundles and displays fields. All educational copy is produced server-side by the Learning Narrative Builder. The deprecated `useListeningCoach.js` composable (~663 lines) has been **deleted**.

---

## Part 1 — Lesson Experience Builder

### Files

| File | Role |
|------|------|
| `backend/app/schemas/language_listening_bundles.py` | Closed Pydantic contracts (`extra="forbid"`) |
| `backend/app/services/language_listening_lesson_experience/builder.py` | `build_lesson_experience_bundle()` |
| `backend/app/services/language_listening_lesson_experience/service.py` | Reservation + readiness orchestration |
| `backend/app/services/language_listening_lesson_experience/legacy_adapter.py` | Legacy `ListeningLessonOut` adapter (backward compat) |

### Contract compliance

**Allowed top-level keys only:** `lesson_id`, `lifecycle_state`, `official_level`, `lesson_level`, `level_note`, `lesson_title`, `lesson_type`, `situation`, `lesson_goal`, `narrative`, `playback`, `after_lesson`, `meta`

**Forbidden keys enforced:** `journey`, `promotion`, `history`, `personal_goal`, `journey_target`, `timeline_steps`, `coach`, `body_json`, `transcript`, unqualified `goal`/`learning_goal`/`target_goal`

**Lifecycle mapping:** Reservation row + progress + post-submit `after_lesson` → `queued | reserved | started | completed | reviewed`

---

## Part 2 — Journey Builder

### Files

| File | Role |
|------|------|
| `backend/app/services/language_listening_journey/builder.py` | `build_listening_journey_bundle()` |
| `backend/app/services/language_learning_facts/journey_assembler.py` | `assemble_journey_facts()` |
| `backend/app/services/language_learning_narrative/journey_builder.py` | `build_journey_narrative()` — all journey copy |

### Journey owns (lesson bundle does NOT)

- Official level
- Journey target
- Personal goal
- Timeline steps
- Promotion readiness / blockers
- History events
- Active lesson pointer
- Journey narrative (headline, step label, progress message, unlock checklist)

---

## Part 3 — API Layer

| Method | Path | Response |
|--------|------|----------|
| GET | `/student/languages/listening/journey` | `ListeningJourneyBundleOut` |
| GET | `/student/languages/listening/next` | `LessonExperienceBundleOut` |
| GET | `/student/languages/listening/{id}` | `LessonExperienceBundleOut` |
| POST | `/student/languages/listening/{id}/submit` | `ListeningLessonSubmitBundleOut` |

**Backward compatibility:** `bundle_to_legacy_payload()` preserves old `ListeningLessonOut` field names and embeds the canonical bundle under `bundle` for gradual migration. The list endpoint (`GET /listening`) continues using the legacy serializer.

**Submit response:** Returns mechanical grading (`passed`, `score_percent`, `question_results`) plus `bundle` with populated `after_lesson` narrative.

---

## Part 4 — Frontend Migration

### API client

- `fetchListeningJourney()` → `GET /listening/journey`
- `fetchNextListening()` → returns `LessonExperienceBundle`
- `submitListeningLesson()` → returns `ListeningLessonSubmitBundleOut`

### Composables

| Before | After |
|--------|-------|
| `useListeningCoach.js` (663 lines, copy generation) | **Deleted** |
| `useListeningJourney.js` (hub + memory + coach merge) | Fetches `ListeningJourneyBundle`; promotion test flow unchanged |

### Components migrated (render-only)

| Component | Source |
|-----------|--------|
| `ListeningJourneyHero` | `journey.narrative.*`, `journey.official_level`, `journey.journey_target` |
| `ListeningJourneyPath` | `journey.narrative.timeline_steps[]` |
| `ListeningGatePanel` | `journey.narrative.unlock_checklist[]`, `promotion_progress_message` |
| `ListeningPromotionHistoryCard` | `journey.narrative.history_events[]` |
| `ListeningPracticePanel` | `LessonExperienceBundle` — `narrative`, `playback`, `after_lesson` |
| `ListeningPromotionStatusCard` | Journey bundle narrative (promotion tab) |
| `ListeningPromotionResultCard` | Backend `result.recommendation` (no coach generation) |
| `ListeningPromotionSuccessCard` | Backend `result.summary`, `level_benefits` |

Progress bar percent in hero is derived mechanically from timeline step `done` count (layout math only, not copy).

---

## Part 5 — Verification

### Script

```bash
cd backend
python scripts/verify_language_adaptive_learning_phase_2_3.py
```

**Checks:**
- LessonExperienceBundle contract (allowed keys, forbidden keys, schema rejection)
- ListeningJourneyBundle contract (no playback)
- Legacy adapter round-trip
- API route wiring audit
- Frontend render-only audit (no `useListeningCoach`, no coach function imports)
- Single Source Matrix component audit
- Regression invocation of Phase 2.1, 2.2, narrative ownership guard

> **Note:** Full script execution requires the backend Python environment (pydantic, fastapi, etc.). Static frontend audits pass; run the script inside your project venv before release.

### Regression suites to run

```bash
python scripts/verify_language_adaptive_learning_phase_2_1.py
python scripts/verify_language_adaptive_learning_phase_2_2.py
python scripts/verify_language_narrative_ownership_guard.py
python scripts/verify_language_adaptive_learning_phase_2_3.py
```

---

## Manual QA Checklist (Browser)

Use a student account with active language subscription. Test on desktop and mobile (375px width).

### Journey tab

- [ ] Page loads without console errors
- [ ] Hero shows `official_level`, `current_step_label`, `journey_target.label` from bundle
- [ ] Journey headline matches backend narrative (not locally generated)
- [ ] Timeline steps render with correct done/active states
- [ ] Gate panel shows `unlock_checklist` when promotion blocked
- [ ] Personal goal chips reflect `personal_goal.id`; saving goal refreshes journey
- [ ] History card shows `history_events`
- [ ] CTA buttons navigate to Practice / Promotion tabs

### Practice tab

- [ ] Start practice loads `LessonExperienceBundle` via `/listening/next`
- [ ] Mission card shows `narrative.student_focus`, `why_this_lesson`, `reward`
- [ ] Audio plays; MCQ form renders `playback.questions`
- [ ] Submit returns score + `after_lesson` headline/summary/improved/needs_practice
- [ ] Refresh during active lesson returns **same** `lesson_id` (reservation pin)
- [ ] Next clip loads a new bundle after completion

### Promotion tab

- [ ] Status card reflects `promotion.can_start_test`
- [ ] Start / resume test flows work (unchanged promotion test API)
- [ ] Result card shows backend `recommendation`
- [ ] Promote success shows level shift and backend summary

### Refresh & reservation

- [ ] Load practice → note `lesson_id` → refresh browser → same lesson
- [ ] Complete lesson → `/listening/next` returns different lesson
- [ ] Skip endpoint clears reservation (if exposed in UI)

### Mobile layout

- [ ] Journey hero stats stack on narrow screens
- [ ] Timeline readable without horizontal scroll
- [ ] Practice MCQ and submit button usable on touch
- [ ] Tab bar accessible

### Regression smoke

- [ ] No references to `lesson.coach` in network responses for `/listening/next`
- [ ] `/listening/journey` response has no `playback` key
- [ ] `/listening/next` response has no `journey`, `promotion`, or `personal_goal` keys

---

## Files changed (Phase 2.3)

### Backend (new)

- `app/schemas/language_listening_bundles.py`
- `app/services/language_listening_lesson_experience/` (builder, service, legacy_adapter)
- `app/services/language_listening_journey/` (builder)
- `app/services/language_learning_facts/journey_assembler.py`
- `app/services/language_learning_narrative/journey_builder.py`
- `scripts/verify_language_adaptive_learning_phase_2_3.py`

### Backend (modified)

- `app/api/language_student.py` — new routes + bundle response models
- `app/services/language_listening_service.py` — `next_listening` returns bundle
- `app/services/language_learning_facts/types.py` — journey fact types
- `app/services/language_learning_narrative/types.py` — journey narrative types

### Frontend (modified)

- `src/api/language.js`
- `src/composables/useListeningJourney.js`
- `src/views/student/languages/StudentLanguageListeningView.vue`
- `src/components/language/Listening*.vue` (8 components)

### Frontend (deleted)

- `src/composables/useListeningCoach.js`

---

## Stop boundary

Phase 2.3 is complete. **Do not proceed** to Phase 2.4+ without explicit approval.

---

## Known follow-ups (out of scope for 2.3)

- Run full verification + regression inside project venv and attach JSON output to CI
- Promotion success `level_benefits` — ensure promote API returns this array (frontend renders as-is)
- Optional dedicated `GET /listening/next/legacy` if external clients still require `ListeningLessonOut` shape
