# Speaking Frontend Product Integration & Real Human QA Report

**Date:** 2026-07-12
**Status:** IMPLEMENTATION COMPLETE — **REAL HUMAN BROWSER ACCEPTANCE NOT YET PERFORMED**
**STOP boundary:** No S9, CEFR/stage/promotion/WPA/diagnostic planner

---

## 1. Frontend audit findings

- Core engine: `src/composables/useLiveConversation.js` — browser WS to Hume EVI, 16 kHz linear16 mic, 24 kHz playback, tool relay, completed-turn upload.
- Only live UI was `LanguageSpeakingLivePanel.vue` (developer-style: state chips, engine version alert, manual “Finish turn”).
- Entry: `/student/languages/speaking?mode=live` via mode toggle; not a first-class product experience.
- i18n branded assistant as “EVI”; no “Alex” keys.
- Backend returned raw `engine_result` (decimals/IDs) — no student-safe summary contract.
- **Critical defect:** `live_turn_id` minted once per session → S8 idempotency blocked adaptive mutations after turn 1.

## 2. Existing Speaking UI defects (found + addressed)

| Defect | Fix |
|--------|-----|
| Reused `live_turn_id` across turns | Fresh `_mintTurnId()` per completed handoff |
| Manual “Finish turn” upload UX | Auto handoff on finalized `user_message` |
| No mic pre-flight / denied recovery | `requesting_microphone` + friendly error + retry |
| No product states (connecting/listening/processing) | UI state machine in composable + shell |
| Raw engine version shown to student | Removed; uses `student_session_summary` only |
| “EVI” exposed in student copy | Replaced with “Alex” (EN+AR) |
| No post-session summary | `LanguageSpeakingSessionSummary.vue` + backend DTO |

## 3. Exact real browser flow

1. Student opens `/student/languages/speaking?mode=live`
2. Sees “Talk with Alex” hero + **Start speaking**
3. Mic permission → token → WS connect → session settings
4. Student speaks naturally; Alex responds via live audio
5. On finalized student turn → non-blocking **Reviewing your speaking…** → `POST /student/languages/speaking/live/turn`
6. Conversation continues; S8 mutates S2; S7.6 cache invalidated
7. Student taps **End conversation** → `ENDED` → session summary from canonical DTO

## 4. UI state machine (UI-only)

`idle → requesting_microphone → connecting → ready ↔ student_speaking → processing_turn → alex_speaking → reconnecting → error → ending → ended`

Mapped to student copy via i18n (e.g. “Connecting to Alex…”, “I'm listening”, “Reviewing your speaking…”).

## 5. Microphone behavior

- Pre-flight via `getUserMedia` (+ optional `permissions.query`)
- Denied/unavailable → friendly message + **Try again**
- Mic stream stopped on end/unmount
- No technical terms (PCM, linear16, sample rate) shown to student

## 6. EVI connection / playback behavior

- Token from `POST /student/languages/speaking/live/token` (access_token only)
- WS: `wss://api.hume.ai/v0/evi/chat?access_token=…&config_id=…`
- Student audio streamed as `audio_input`; Alex via `audio_output` (24 kHz PCM)
- Interruption stops playback (`user_interruption`)
- Best-effort reconnect (max 2 attempts) on unexpected close
- Clean close on end session

## 7. Completed-turn handoff proof

- **Student audio only:** handoff uses captured turn PCM → WAV blob from mic pipeline
- **Fresh turn ID:** `_mintTurnId()` per handoff → distinct S8 observations per turn
- **Duplicate guard:** `handoffInFlight` + `handoffTurnIds` set
- **API:** `submitSpeakingLiveTurn({ liveTurnId, … })` → `process_completed_live_turn` → S7 + S8 + `student_session_summary`
- Assistant messages never submitted as student evidence

## 8. Educational processing UX

- Non-blocking `processing_turn` indicator (“Reviewing your speaking…”)
- Live conversation continues (Alex can speak; mic pipeline active where safe)
- `mutation_status` used internally only; subtle info alert if personalization not updated

## 9. Transcript decision

- **Secondary, collapsible** transcript panel
- Finalized messages only (`finalized: true`)
- Clear **Alex** vs **You** labels; English transcript `dir="ltr"`
- Not primary UI — voice-first experience preserved

## 10. End-session behavior

- **End conversation** stops mic, playback, WS
- Finalizes pending turn if audio captured and not already in flight
- Handles races: ending during Alex speech, processing, or reconnect
- Transitions to `ended` → summary view

## 11. Session-summary contract decision

**Added** render-only backend contract (was missing):

- `SpeakingStudentSessionSummary` in `language_speaking_explainability/student_session_summary.py`
- Exposed on `SpeakingLiveTurnOut.student_session_summary` (Pydantic `extra="forbid"`)
- Frontend renders **only** this DTO — no raw `evaluation` parsing

## 12. Progress-visibility decision

- **No mastery percentages or S2 internals rendered**
- S2 has no approved student-facing projection yet → **blocker for journey/progress UI**
- This task prioritizes live session + per-turn/per-session summary only

## 13. Arabic/English i18n result

- All new strings under `student.languages.speaking.live.*` + `summary.*` in EN and AR
- Alex branding in both locales
- RTL via existing `applyDocumentLocale` + Vuetify `rtl`
- Product browser verifier: no raw i18n keys in shell

## 14. Desktop/mobile result

- Shell max-width 760px; sticky bottom controls with safe-area padding
- Mobile `@media (max-width: 600px)` adjustments
- Primary Start/End controls remain reachable

## 15. Accessibility result

- `aria-label` on primary actions
- `aria-live="polite"` status banner
- Keyboard-accessible buttons
- `prefers-reduced-motion` disables pulse animation

## 16. Error-state result

Friendly copy for: mic denied, mic unavailable, connection failure, reconnect failure, handoff failure, end-during-processing. No raw error codes or stack traces.

## 17. Browser verifier result

| Verifier | Result |
|----------|--------|
| `frontend/scripts/verify_speaking_product_browser.mjs` | **29/29 PASS** |
| `backend/scripts/verify_speaking_s75_evi_browser.mjs` | **14/14 PASS** (updated for new shell) |

## 18. Frozen/backend regression result

| Verifier | Result |
|----------|--------|
| S0 architecture | **529/529 PASS** |
| S8 knowledge bridge | **46/46 PASS** |
| Summary contract | **12/12 PASS** |
| S7.5 EVI runtime | **PASS** |
| S7.5 real EVI | **21/21 PASS** |
| S7.6 structural | **26/26 PASS** |
| S7.6 real EVI | **10/10 PASS** |

## 19. Exact manual human acceptance steps (for you)

1. **URL:** `http://localhost:5173/student/languages/speaking?mode=live` (or your deployed frontend URL)
2. **Login:** use your existing student test account (credentials not recorded here)
3. **Navigation:** Learn languages → Speaking → **Talk with Alex** tab
4. **Action:** click **Start speaking**; allow microphone when prompted
5. **Say (turn 1):** “Hi Alex, my name is [your name]. I work as a teacher and I enjoy reading in the evening.”
6. **Say (turn 2):** “Yesterday I visited the market and bought fresh vegetables for dinner.”
7. **Complete 2–3 natural turns** (wait for Alex replies between turns)
8. **Observe UI states:** Connecting to Alex… → I'm listening → Alex is speaking → Reviewing your speaking… (non-blocking)
9. **End:** click **End conversation**
10. **Verify summary:** session summary shows prose strengths/improvements/focus — no percentages, no “EVI/Hume/GPT”, no skill IDs

## 20. Runtime/DB evidence to inspect after your human test

After your session, Cursor will inspect:

- **API response:** `POST /student/languages/speaking/live/turn` → `student_session_summary` populated, `mutation_status=applied` (or documented skip reason)
- **PostgreSQL:** `language_progression.promotion_readiness_json` → `speaking.knowledge_model` skill states updated (distinct `observation_id` per turn)
- **S7.6 cache:** next `get_student_speaking_context` tool call reflects updated priority targets
- **Forbidden unchanged:** `official_speaking_cefr`, `learning_stage_speaking`, `promotion_readiness_score`

## 21. Files created/modified

**Created**

- `backend/app/services/language_speaking_explainability/student_session_summary.py`
- `backend/scripts/verify_speaking_summary_contract.py`
- `src/components/language/LanguageSpeakingLiveShell.vue`
- `src/components/language/LanguageSpeakingSessionSummary.vue`
- `frontend/scripts/verify_speaking_product_browser.mjs`
- `backend/SPEAKING-FRONTEND-PRODUCT-INTEGRATION-REPORT.md`

**Modified**

- `backend/app/services/language_speaking_explainability/__init__.py`
- `backend/app/services/language_speaking_evaluation_runtime/live_runtime.py`
- `backend/app/api/language_speaking_live.py`
- `src/composables/useLiveConversation.js`
- `src/views/student/languages/StudentLanguageSpeakingView.vue`
- `src/components/language/LanguageSpeakingModeToggle.vue`
- `src/locales/en/student.json`, `src/locales/ar/student.json`
- `backend/scripts/verify_speaking_s75_evi_browser.mjs`

## 22. Defects found and fixed

- Per-turn idempotency (reused `live_turn_id`)
- Missing student summary contract (backend + frontend)
- Developer-facing live panel replaced with product shell
- S0 RESPONSIBILITY docstring regression on explainability package

## 23. Remaining blockers

- **REAL HUMAN BROWSER ACCEPTANCE** — requires you to speak through the browser; not claimed in this report
- **Progress/journey UI** — needs future backend student-facing S2 projection
- **Legacy hardcoded English** in exercise/conversation panels (out of live scope)

## 24. Final readiness verdict

| Area | Verdict |
|------|---------|
| Backend summary contract | **READY** |
| Live conversation product UX | **READY for human QA** |
| Automated verifiers | **GREEN** |
| Real human browser acceptance | **PENDING — user must perform steps in §19** |

**Do not claim REAL HUMAN BROWSER ACCEPTED until after personal microphone test + DB inspection in §20.**
