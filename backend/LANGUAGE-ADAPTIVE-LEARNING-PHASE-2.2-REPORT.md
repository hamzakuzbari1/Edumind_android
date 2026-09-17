# Phase 2.2 — Session Reservation + Lesson Lifecycle + Deterministic Selection

**Status:** Complete
**Scope:** Session Reservation Service, Lesson Lifecycle, Deterministic Lesson Selection
**Not in scope:** Journey Builder, Lesson Experience Builder, frontend migration, Phase 2.3

---

## Implementation Summary

Phase 2.2 pins one listening lesson per `(student_id, language_id)` until the student completes or skips it. Random selection is removed from the listening path; the deterministic ranker chooses the next lesson only when no active reservation exists.

### New packages

| Package | Path | Role |
|---------|------|------|
| **Session Reservation** | `app/services/language_listening_reservation/` | Reserve, load, release, complete, skip, expire; lifecycle enforcement |
| **Deterministic Selection** | `app/services/language_listening_selection/` | Rank eligible candidates; no random ordering |

### New persistence

| Artifact | Path | Role |
|----------|------|------|
| Migration | `alembic/versions/0006_language_listening_reservations.py` | `language_listening_reservations` table |
| SQL | `alembic/sql/0006_language_listening_reservations.sql` | Partial unique index on active reservations |
| Model | `app/models/language/reservation.py` | `LanguageListeningReservation` ORM |

### Modified modules

| Module | Change |
|--------|--------|
| `language_listening_service.py` | `next_listening` uses reservation pin; removed `func.random()`; added `skip_listening()` |
| `language_skill_progress_service.py` | `submit_listening` calls `complete_reservation()` after submit |
| `language_student.py` | `POST /listening/{content_id}/skip`, `POST /listening/skip`; detail touches `started` state |
| `models/language/__init__.py` | Exports reservation model |

---

## Architecture Impact

### Reservation flow (GET /next)

```
GET /listening/next
      ↓
_resolve_listening_item()
      ↓
resolve_reserved_lesson()
      ├─ active reservation? → return pinned content_item_id (mark started)
      ├─ expired?              → archive + run selector
      └─ none?                 → select_deterministic_listening_lesson() → create reservation
      ↓
serialize_listening_lesson()  (API shape unchanged)
```

### Deterministic ranking order

Lower sort key wins:

1. **Weakest Objective** — minimum objective `coverage_score` from confidence state
2. **Review Priority** — review intent / review objectives → 0, else 1
3. **Curriculum Priority** — higher `recommendation_score` wins (negated in sort key)
4. **Oldest Candidate** — `created_at` timestamp (fallback: `sort_order`)
5. **Difficulty Match** — normal before stretch/hard
6. **Stable Tie Break** — `content_item.id ASC`

No `random()`, `func.random()`, or `ORDER BY RANDOM()` in the listening selection path.

### Lesson lifecycle

**Pool semantics (content items):** `created` → `queued` (documented, not persisted on reservation rows)

**Reservation row transitions:**

| From | To | Trigger |
|------|-----|---------|
| `reserved` | `started` | First `/next` or lesson detail view |
| `reserved` | `archived` | Skip or expire |
| `started` | `completed` | Lesson submit |
| `started` | `archived` | Skip or expire |
| `completed` | `reviewed` | Chained on complete |
| `reviewed` | `archived` | Terminal cleanup (future) |

Illegal transitions raise `IllegalLifecycleTransitionError`.

**Active reservation states:** `reserved`, `started`
**Enforcement:** partial unique index `uq_language_listening_reservations_active` on `(student_id, language_id)` WHERE lifecycle in active states.

### Reservation rules

| Action | Behavior |
|--------|----------|
| **Refresh / double refresh** | Returns same pinned lesson; selector not invoked |
| **Skip** | Archives active reservation; next `/next` runs selector |
| **Complete** | Submit archives reservation through `completed` → `reviewed` |
| **Expire** | TTL default 24h; expired pin archived on load |
| **Parallel create** | `IntegrityError` → rollback → reload winner reservation |

### Backward compatibility

- `ListeningLessonOut` and existing `/listening/next` response shape unchanged
- New skip endpoints are additive
- Background pool prefill still uses deterministic `id DESC` for newest-first generation (not student-facing selection)

---

## Verification Results

### Phase 2.2 script

```bash
python scripts/verify_language_adaptive_learning_phase_2_2.py
```

| Check | Result |
|-------|--------|
| Migration + model present | PASS |
| No random in listening path | PASS |
| Legal / illegal lifecycle transitions | PASS |
| Ranking (review priority, determinism, tie-break) | PASS |
| Refresh same lesson | PASS |
| Create uses selector when no pin | PASS |
| Expire clears reservation | PASS |
| Skip releases reservation | PASS |
| Complete reservation | PASS |
| Parallel race (IntegrityError reload) | PASS |
| Selection reproducibility | PASS |

**OVERALL: PASS**

### Regression suites

| Suite | Script | Result |
|-------|--------|--------|
| Phase 2.1 Facts + Narrative | `verify_language_adaptive_learning_phase_2_1.py` | PASS |
| Narrative Ownership Guard | `verify_language_narrative_ownership_guard.py` | PASS |
| Phase 3.4 Explainability | `verify_language_adaptive_learning_phase_3_4.py` | PASS |
| Learning Stage 5.1 | `verify_language_learning_stage_phase_5_1.py` | PASS |
| Learning Stage 5.1.1 | `verify_language_learning_stage_phase_5_1_1.py` | PASS |
| Transition Gate 5.2 | `verify_language_transition_gate_phase_5_2.py` | PASS |
| Promotion Readiness 5.3 | `verify_language_promotion_readiness_phase_5_3.py` | PASS |
| Promotion Stability 5.3.1 | `verify_language_promotion_stability_phase_5_3_1.py` | PASS |
| Promotion Test 5.4 | `verify_language_promotion_test_phase_5_4.py` | PASS |
| Official Promotion 5.5 | `verify_language_official_promotion_phase_5_5.py` | PASS |
| Official Promotion API | `verify_language_official_promotion_api_pr_3.py` | PASS |

No regressions observed in Stage, Gate, Readiness, Promotion, or Official Promotion suites.

---

## Known Risks

1. **Migration required in production** — Run Alembic `0006` before deploying; without it reservation persistence fails at runtime.
2. **Integration coverage gap** — Phase 2.2 verify uses unit/mocked tests; end-to-end DB tests for concurrent `/next` under real Postgres load are not yet automated.
3. **Skip without content_id** — `POST /listening/skip` clears any active pin; clients must not call skip while another tab is mid-lesson unless intentional.
4. **TTL edge case** — A reservation expiring mid-lesson will re-select on next `/next`; student may see a different lesson after long idle sessions (>24h default).
5. **Completed lessons in pool** — Skipped lessons remain in the unseen pool unless separately excluded by progress filters; selector may re-offer skipped content on a future cycle (pre-existing pool semantics).
6. **Grandfathered narrative debt** — `teacher_summary.py` and `learning_path.py` prose remains (Phase 2.1.1 guard); unchanged by Phase 2.2.

---

## Next Steps (Phase 2.3 — not started)

Per canonical architecture v3.0, Phase 2.3 would introduce:

- Lesson Experience Builder (`LessonExperienceBundle`)
- Listening Journey Builder (`ListeningJourneyBundle`)
- Frontend migration to canonical bundles

**Phase 2.2 stops here.** Do not auto-start Phase 2.3.
