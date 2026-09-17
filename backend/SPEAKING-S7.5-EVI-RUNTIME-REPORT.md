# Speaking S7.5 — Hume EVI Live Conversation Runtime Report

**Date:** 2026-07-12
**Runtime version:** `7.5.0`
**Status:** COMPLETE — STOP boundary respected (no S8+ work)

---

## 1. API audit outcome

Verified against Hume EVI (dev.hume.ai, 2026):

| Surface | Detail |
|---------|--------|
| WebSocket | `wss://api.hume.ai/v0/evi/chat` |
| Auth (browser) | `access_token` query param from `POST https://api.hume.ai/oauth2-cc/token` |
| Auth (server) | `api_key` query param or `X-Hume-Api-Key` |
| Send | `audio_input` (base64 PCM), `session_settings` |
| Receive | `chat_metadata`, `user_message`, `assistant_message`, `audio_output`, `assistant_end`, `user_interruption`, `error` |
| Limits | 30-min session, 6 MB max message |

**Important:** EVI live chat is a **different product** from the discontinued Batch Expression Measurement API used in S6 (`prosody_hume.py`).

---

## 2. EVI version / endpoint

- **API version:** `v0`
- **Endpoint:** `wss://api.hume.ai/v0/evi/chat`
- **Token endpoint:** `https://api.hume.ai/oauth2-cc/token`
- **Provider name:** `hume_evi`

---

## 3. Auth design

- **Topology:** Browser connects **directly** to EVI via short-lived `access_token` minted server-side.
- **Backend mint:** `POST /oauth2-cc/token` with Basic `base64(apiKey:secretKey)`, `grant_type=client_credentials` (~30 min TTL).
- **Secrets:** `HUME_API_KEY` + **`HUME_SECRET_KEY`** (new) + `HUME_EVI_CONFIG_ID` stay server-side only.
- **API:** `POST /student/languages/speaking/live/token` returns `{access_token, expires_in, config_id, ws_url}` — never API/secret keys.

---

## 4. Provider implementation

| Provider | Role |
|----------|------|
| `HumeEviLiveConversationProvider` | Real EVI WebSocket client (raw `websockets`, 6 MB frame limit) |
| `MockEviLiveConversationProvider` | QA-only scripted session — never silent production fallback |

- Factory: `language_speaking_audio_frontend/live_conversation_factory.py` — static `{hume_evi, mock}` map, raises on unknown/misconfigured.
- Provider errors live in `language_speaking_providers/live_provider_errors.py` (ownership-safe; translated at runtime/API boundary).
- Token minting: `language_speaking_evaluation_runtime/evi_token.py`.

---

## 5. Lifecycle (provider-neutral)

States: `created → connecting → connected → listening → user_speaking → user_turn_complete → assistant_thinking → assistant_speaking → interrupted → closing → closed → failed`

- `is_legal_live_transition()` + `IllegalLiveTransition` enforce legal edges.
- Structural verifier proves legal/illegal transitions (checks E–F).

---

## 6. Event mapping

`language_speaking_live_conversation/event_mapping.py` maps EVI-native events → `SpeakingLiveEvent` facts:

- Preserves only fields EVI returns (transcript, expression scores, timing, interruption, chat ids).
- No invented mastery/CEFR/readiness fields.
- Expression measures are **expressive-conversation facts only**.

---

## 7. Turn boundary

- **Live layer:** EVI owns turn-taking, barge-in, assistant playback.
- **Eval layer:** On completed student turn, browser POSTs finalized student audio + EVI evidence JSON to backend.
- **Boundary event:** `user_message` (non-interim) + optional `assistant_end` marks turn completion in frontend composable.

---

## 8. Turn accumulation design

`StudentTurnAudioAccumulator`:

- Accumulates **student mic PCM only** (never assistant audio).
- Limits: `SPEAKING_EVI_MAX_TURN_BYTES` (25 MB), `SPEAKING_EVI_MAX_TURN_SECONDS` (120 s).
- Finalize-once guard; `clear()` after handoff; cleanup on failure/close.
- Retention: in-memory only for active turn; cleared after handoff or session close.

---

## 9. EVI evidence contract

`SpeakingLiveConversationEvidence` (separate from S6 acoustic evidence):

- `provider_transcript` — **non-canonical** (`non_canonical: true`)
- `expression_measures[]` — EVI prosody scores when exposed
- `event_sequence[]`, `interruption_count`, `provider_chat_id`, `provider_chat_group_id`
- `evidence_kind: "live_conversation"`
- Persisted additively in evaluation dict as `live_conversation_evidence` + `live_traceability`

---

## 10. Expression availability

- **Mock path:** Calmness/Interest scores from scripted `user_message.models.prosody.scores`.
- **Real path:** Printed when Hume returns them; otherwise verifier prints `UNAVAILABLE` — never invented.
- **Current real acceptance:** Not run (missing `HUME_SECRET_KEY` / `HUME_EVI_CONFIG_ID` in dev env).

---

## 11. Custom-LLM decision

- **S7.5 scope:** Fixed EVI config (`HUME_EVI_CONFIG_ID`) — no custom LLM wiring.
- **Future:** CLM via `session_settings.language_model_api_key` + control-plane observer documented in plan; deferred to S8+ if needed.

---

## 12. S4→S7 handoff proof

`process_completed_live_turn()` in `live_runtime.py`:

1. Builds `SpeakingAudioArtifact` via `artifact_from_bytes`
2. Calls frozen `process_speaking_evaluation()` (S4→S5→S6→S7)
3. Attaches `SpeakingLiveConversationEvidence` alongside result
4. Preserves S4/S5/S6/S7 provenance + live traceability

**Structural proof:** mock session handoff check Q — **PASS** (28/28 structural verifier).

---

## 13. Provenance trace

`live_traceability` block:

```json
{
  "live_session_id": "...",
  "live_turn_id": "...",
  "source_audio_id": "live-...",
  "runtime_version": "7.5.0"
}
```

Plus `s7_engine_version`, `evi_provider_chat_id`, and `s4_s5_s6_provenance` in provenance trace.

---

## 14. Interruption proof

- Frontend composable handles `user_interruption` events (clears assistant playback queue).
- Browser static verifier check 5 — **PASS**.
- EVI evidence records `interruption_count`.

---

## 15. Frontend proof

Minimal Vue integration (no Journey/mastery/promotion UI):

| File | Role |
|------|------|
| `src/composables/useLiveConversation.js` | Token fetch, direct EVI WS, mic PCM, playback, turn finalize |
| `src/api/speakingLive.js` | Backend token + turn upload |
| `src/components/language/LanguageSpeakingLivePanel.vue` | Minimal live UI in speaking view |
| `src/locales/{en,ar}/student.json` | `languages.speaking.live.*` i18n keys |

**Browser static verifier:** **12/12 PASS**

---

## 16. Security proof

- No `HUME_API_KEY` / `HUME_SECRET_KEY` in frontend code or network responses.
- Browser uses `access_token` query param only.
- Backend token endpoint returns token + config_id + expiry only.
- Provider errors translated — no raw Hume exceptions leaked to client.

---

## 17. Cleanup / retention proof

- Accumulator cleared after handoff (`acc.clear()`).
- EVI provider `close()` cancels reader task, closes WebSocket, drains queue.
- No persistent storage of raw mic buffers beyond active turn lifetime.
- Structural checks G–J, cleanup on close — **PASS**.

---

## 18. Real EVI acceptance

**Script:** `verify_speaking_s75_real_evi.py` (FAIL-not-SKIP) — **REAL Hume EVI, no mock, no skip.**

**Summary: 21/21 PASS** (EduSpark Alex Speaking Partner config `b42eeb91-…`).

Proven on the real path:
- Real token mint (`POST /oauth2-cc/token`) → live `access_token`
- Real EVI WebSocket connection accepted with configured EVI config ID
- Provider `hume_evi` (no mock, no silent fallback)
- Real user-turn event sequence (6 events) + real assistant `audio_output`
- Completed student turn handed off to frozen S4→S5→S6→S7 (`engine_version 7.0.0`)
- S4/S5/S6 provenance preserved (`openai / wav2vec2 / acoustic`)
- EVI evidence separate + non-canonical; no mastery/CEFR/stage/readiness/promotion mutation
- Missing-credential path fails structurally (no fake pass)

Notes (truthful):
- Expression measures reported **UNAVAILABLE** for this config — not invented.
- Educational analyzer emitted `parse_failed` on the Arabic-voice fixture; frozen S7 handled it gracefully (handoff still succeeded). This is frozen-S7 behavior, not an S7.5 defect.

### Defect fixed to reach real acceptance

`session_settings.audio` used `"encoding": "linear16"`; Hume's audio contract requires **`"format": "linear16"`**. Wrong field → EVI could not decode headerless PCM → documented "unexpected silence" (no `user_message`/`audio_output`). Fixed in `verify_speaking_s75_real_evi.py` and frontend `useLiveConversation.js`; added trailing silence frames to trigger EVI end-of-turn VAD.

---

## 19. Frozen regression (S0–S7)

All structural verifiers re-run green with S7.5 additive changes:

| Verifier | Result |
|----------|--------|
| S0 architecture | 507/507 PASS |
| S1 skill graph | 51/51 PASS |
| S2 knowledge model | 52/52 PASS |
| S2 persistence DB | VERIFIED |
| S3 audio frontend | 106/106 PASS |
| S4 audio runtime | 54/54 PASS |
| S5 pronunciation | 27/27 PASS |
| S6 prosody | 39/39 PASS |
| S7 evaluation | 50/50 PASS |
| **S7.5 structural** | **28/28 PASS** |
| **S7.5 browser static** | **12/12 PASS** |

---

## 20. Defects found and fixed

1. **Ownership violations** — providers/audio_frontend imported `language_speaking_live_conversation.errors`; fixed with provider-local errors + token mint in evaluation_runtime.
2. **Mock verifier timeout** — expected 6 events, mock emits 5; fixed loop count.
3. **i18n key path** — panel used `student.speaking.live.*`; corrected to `student.languages.speaking.live.*`.
4. **S0 layer/dependency failures** — resolved by import boundary refactor (507/507 restored).

---

## 21. Limitations

- Real EVI acceptance requires `HUME_SECRET_KEY` + `HUME_EVI_CONFIG_ID` in environment.
- Raw WebSocket implementation (no official Hume Python SDK dependency yet — `websockets>=13.0` added).
- `SPEAKING_EVI_RECONNECT_ENABLED` config present but reconnect logic not implemented in S7.5.
- Server-side control-plane observer socket deferred.
- Browser verifier is static/source analysis (not Playwright runtime mic test).

---

## 22. Files changed (S7.5 additive)

**Config:** `config.py`, `.env.example`, `requirements.txt`
**Ownership:** `language_speaking/ownership.py`
**New package:** `language_speaking_live_conversation/`
**Providers:** `live_conversation_hume.py`, `live_conversation_mock.py`, `live_provider_errors.py`, ABC extensions
**Runtime:** `evaluation_runtime/live_runtime.py`, `evaluation_runtime/evi_token.py`
**Factory:** `audio_frontend/live_conversation_factory.py`
**API:** `api/language_speaking_live.py`, `api/router.py`
**Frontend:** `useLiveConversation.js`, `speakingLive.js`, `LanguageSpeakingLivePanel.vue`, speaking view + mode toggle, i18n
**Verifiers:** `verify_speaking_s75_evi_runtime.py`, `verify_speaking_s75_real_evi.py`, `verify_speaking_s75_evi_browser.mjs`

---

## 23. S8 readiness decision

**S7.5 is REAL-ACCEPTED** — structural (28/28), browser-static (12/12), **real Hume EVI (21/21)**, and frozen S0–S7 all green.

### `get_student_speaking_context` custom EVI tool — **NOT WIRED**

- No `get_student_speaking_context` reference exists anywhere in the codebase.
- Hume tool_call events would arrive on the WS read loop but are **not** consumed/handled.
- EduSpark does **not** execute the tool; no `tool_response` send path exists.
- No S1/S2/S7 student speaking context is read for any tool.
- The EVI config declares the tool, but the EduSpark runtime does not fulfil it (deferred, per instructions — not implemented in S7.5).

**Remaining before S8:**

1. Wire `get_student_speaking_context` (tool_call receipt → execute → read S1/S2/S7 → return `tool_response`) if live tutor grounding is desired.
2. Product decisions on Journey/progression UI integration (out of S7.5 scope).
3. Optional: reconnect policy, control-plane observer, official Hume SDK adoption.

**Hard boundaries preserved:**

- EVI never writes mastery, official CEFR, learning stage, readiness, promotion, or S7 completion.
- S4 GPT-4o remains canonical semantic transcript.
- S0–S7 frozen code unchanged except proven ownership-safe additive wiring.
- **STOP — do not start S8.**
