# Speaking S7.6 — Real EVI Student Speaking Context Tool Report

**Date:** 2026-07-12
**Context version:** `7.6.0`
**Status:** COMPLETE — STOP boundary respected (no S8)

---

## 1. Audit findings

- S7.5 live runtime worked end-to-end but **`get_student_speaking_context` was NOT WIRED** (no tool_call consumption, no tool_response).
- Browser-direct EVI topology confirmed: `tool_call` arrives at browser WS; backend serves authenticated relay via `POST /speaking/live/tool`.
- Pre-existing defect fixed: [`language_speaking_live.py`](backend/app/api/language_speaking_live.py) imported non-existent `app.api.deps` and `rate_limit_service` (app could not start via router).
- S7 persisted `engine_result` read path exists but live flow still does not write it (read-only per plan — S7 marked unavailable when absent).

## 2. Exact Hume tool event contract observed

**Receive `tool_call`:**
```json
{ "type": "tool_call", "name": "get_student_speaking_context", "parameters": "{}", "response_required": true, "tool_call_id": "<uuid>", "tool_type": "function" }
```

**Send `tool_response`:**
```json
{ "type": "tool_response", "tool_call_id": "<matching-id>", "content": "<compact-json-string>", "tool_name": "get_student_speaking_context", "tool_type": "function" }
```

**Send `tool_error` (safe fallback):**
```json
{ "type": "tool_error", "tool_call_id": "<matching-id>", "error": "...", "content": "...", "level": "warn" }
```

Real acceptance observed live `tool_call` from EduSpark Alex config after `user_input` nudge.

## 3. Ownership decision

- **Owner:** `language_speaking_coach` (pedagogy layer — read-only pedagogical context aggregation).
- **Additive edges:** `coach → curriculum`, `coach → knowledge_model` (DAG-legal; layer 5 < 9).
- **Dispatch/cache:** `language_speaking_evaluation_runtime/evi_tool_runtime.py` (already depends on `coach`; no `providers` import to preserve S0).

## 4. Student identity / ownership design

- Identity **always** from JWT via `require_language_learning_ready()` → `student.id`.
- Tool `parameters.student_id` is **ignored** if it conflicts with authenticated student (logged, never authoritative).
- `student_reference` = opaque `spk-{sha256(salt:student_id)[:16]}` — no email/PII.

## 5. Canonical context sources

| Source | Read path |
|--------|-----------|
| S1 | `SPEAKING_SKILL_GRAPH.node_by_id()` for labels/types |
| S2 | `LanguageProgression.promotion_readiness_json["speaking"]["knowledge_model"]` via `knowledge_model_from_speaking_bucket` |
| S7 | Latest `LanguageSpeakingConversationTurn.evaluation_json["engine_result"]` or `LanguageSpeakingProgress.ai_evaluation_json["engine_result"]` → `evaluation_result_from_dict` (if present) |

## 6. StudentSpeakingLiveContext contract

Frozen dataclass in [`language_speaking_coach/types.py`](backend/app/services/language_speaking_coach/types.py):

- `context_version`, `student_reference`, `speaking_goal`, `learner_state`
- `priority_skill_targets[]`, `recurring_mistake_patterns[]`, `retention_review_targets[]`
- `recent_strengths[]`, `recent_revision_needs[]`, `conversation_guidance[]`
- `unavailable_context[]`, `generated_at`

## 7. Priority summarization rule

Deterministic read-only ordering:

1. Union S2 at-risk / weak-mastery skills + S7 failed `candidate_skill_evidence`
2. Rank by `(retention_risk desc, mastery asc, confidence asc)` → top 5
3. Recurring mistakes: mistake tags by `occurrence_count desc` → top 5
4. Retention targets: skills with `retention_risk >= 0.55` → top 5
5. Revision needs: only when persisted S7 result exists

## 8. Conversation guidance derivation

Template-based from evidence (not numeric scores to Alex):

- New learner: warm prompts, short turns, minimal correction
- Returning learner: natural partner tone, priority skill opportunities, gentle mistake revisits, longer thinking time when revision needs exist

## 9. EVI compact serialization + size budget

- `serialize_live_context_for_evi()` → compact JSON, **max 2000 chars** (`EVI_CONTEXT_MAX_CHARS`)
- Strips raw skill IDs from priority block in EVI payload (labels + reasons only)
- No raw JSONB, no mastery numerics, no secrets

## 10. Cache design and invalidation

- `LiveContextCache`: in-memory `(student_id, language_id)` keyed, TTL 120s
- No Redis; no cross-student leakage
- `invalidate_live_context()` called after successful `process_completed_live_turn` (S4→S7 handoff)

## 11. Tool failure behavior

- Lookup failure → safe `limited_context` serialized response (via `tool_error.content` or limited JSON in relay)
- Never fabricates weaknesses; never returns another student's context
- Session/conversation continues (structural + real proof)

## 12. Files created / modified

**New:**
- `language_speaking_coach/live_context.py`
- `language_speaking_coach/live_context_loader.py`
- `language_speaking_coach/evi_serialization.py`
- `language_speaking_evaluation_runtime/evi_tool_runtime.py`
- `scripts/verify_speaking_s76_evi_student_context.py`
- `scripts/verify_speaking_s76_real_evi.py`

**Modified:**
- `language_speaking/ownership.py`
- `language_speaking_coach/types.py`, `__init__.py`
- `language_speaking_providers/providers.py`, `live_conversation_hume.py`, `live_conversation_mock.py`
- `language_speaking_evaluation_runtime/live_runtime.py`, `__init__.py`
- `app/api/language_speaking_live.py`
- `src/api/speakingLive.js`, `src/composables/useLiveConversation.js`
- `scripts/verify_speaking_s75_evi_browser.mjs`

## 13. Structural verification results

**`verify_speaking_s76_evi_student_context.py`: 26/26 PASS**

Checks A–T including allowlist, ownership override rejection, new learner, S2/S1/S7 summarization, serialization budget, cache, tool round-trip, failure safety, frozen S0 + S7.5 reruns.

## 14. Real Hume tool-call acceptance results

**`verify_speaking_s76_real_evi.py`: 10/10 PASS**

## 15. Real tool_call event proof

Live session emitted `type: tool_call`, `name: get_student_speaking_context`, with real `tool_call_id` from Hume EVI (EduSpark Alex config).

## 16. Real tool_response proof

Backend `handle_evi_tool_call` dispatched allowlisted tool and sent `tool_response` with matching `tool_call_id` and compact context JSON over WebSocket.

## 17. Conversation continuation proof

After real `tool_response`, EVI emitted `assistant_message` / `assistant_end` — conversation continued normally.

## 18. Security / isolation proof

- No `HUME_SECRET_KEY` / API keys in frontend or tool payload
- Relay endpoint returns only tool content; auth via JWT
- `student_id` in tool parameters cannot override authenticated student
- No mastery/CEFR/stage/readiness/promotion writes in S7.6 path

## 19. Frozen regression results

| Verifier | Result |
|----------|--------|
| S0 architecture | 519/519 PASS |
| S1 | 51/51 PASS |
| S2 | 52/52 PASS |
| S3 | ready PASS |
| S4 | ready PASS |
| S5 | ready PASS |
| S6 | 39/39 PASS |
| S7 | 50/50 PASS |
| S7.5 structural | 28/28 PASS |
| S7.5 browser | 14/14 PASS |
| S7.5 real EVI | 21/21 PASS |

## 20. Defects found and fixed

1. Broken API imports in `language_speaking_live.py` (app startup blocker).
2. Circular import coach↔evaluation_runtime (lazy import + local engine_result key).
3. S0 violation `evaluation_runtime → providers` (removed provider import from tool runtime).
4. `_revision_needs` slice bug on dict.
5. Real verifier post-tool wait too short (extended deadline after tool_response).

## 21. Known limitations

- S7 revision needs unavailable in production until canonical `engine_result` is persisted by a future additive write (explicitly out of S7.6 scope).
- Real tool elicitation may depend on Hume dashboard system prompt; verifier uses `user_input` nudge. Recommended prompt line (if not already in dashboard):

  > At the start of each new conversation, call get_student_speaking_context before your first reply so you can adapt naturally to this learner.

- EVI expression measures may remain UNAVAILABLE depending on config (truthfully reported, never invented).

## 22. S8 readiness decision

**S7.6 REAL TOOL INTEGRATION ACCEPTED.**

**NOT READY for S8** (progression, promotion, diagnostic curriculum, S2 mutation, Journey UI). Next optional step: persist canonical S7 `engine_result` on live turn completion so tool grounding includes fresh revision needs in production.

**STOP — do not start S8.**
