# Listening Deployment Checklist

Production hardening for the canonical listening stack (Phase 2.2 reservations + Phase 2.3 bundles).

**Do not deploy listening bundle endpoints without completing this checklist.**

---

## Migration order (required)

Listening canonical features depend on these Alembic revisions **in order**:

| Order | Revision | Purpose |
|-------|----------|---------|
| 1 | `0001_baseline` | Core schema |
| 2 | `0002_reference_seed` | Reference data |
| 3 | `0003_student_listening_content` | Personalized listening pool |
| 4 | `0004_language_analytics_xp` | Analytics / XP |
| 5 | `0005_language_progression` | Official CEFR, promotion JSON, progression events |
| 6 | `0006_language_listening_reservations` | Session reservation table (Phase 2.2) |

**Listening head revision:** `0006_language_listening_reservations`

### Apply migrations

```bash
cd backend
venv\Scripts\python.exe -m alembic current
venv\Scripts\python.exe -m alembic upgrade head
venv\Scripts\python.exe -m alembic current   # must show 0006_language_listening_reservations
```

---

## Verification commands

### 1. Deployment verification script

```bash
cd backend
venv\Scripts\python.exe scripts/verify_listening_deployment.py
```

Checks:

- Current vs latest Alembic revision
- Tables: `language_progression`, `language_progression_events`, `language_listening_reservations`
- Indexes from `0005` and `0006` migrations
- Flags: `listening_progression_ready`, `reservation_table_present`, `deployment_ready`

Exit code `0` = ready. Exit code `1` = do not release.

### 2. Health endpoint

```bash
curl http://127.0.0.1:8000/health
```

Expected fields when ready:

```json
{
  "status": "ok",
  "listening_progression_ready": true,
  "reservation_table_present": true,
  "current_alembic_revision": "0006_language_listening_reservations",
  "latest_alembic_revision": "0006_language_listening_reservations",
  "deployment_ready": true
}
```

When migrations are missing, `status` is `"degraded"` and boolean flags are `false`.

### 3. Startup logs

On backend start, look for either:

```
Listening deployment schema OK (revision=0006_language_listening_reservations, ...)
```

or:

```
LISTENING DEPLOYMENT NOT READY — run: alembic upgrade head | current_revision=... missing_tables=[...]
```

### 4. Structured API error (not HTTP 500)

If a listening bundle endpoint is called before migrations are applied, the API returns **503** with:

```json
{
  "error": "DATABASE_MIGRATION_REQUIRED",
  "message": "Listening deployment schema is not ready. Run Alembic migrations.",
  "missing_table": "language_listening_reservations",
  "required_migration": "0006_language_listening_reservations",
  "current_alembic_revision": "0005_language_progression",
  "latest_alembic_revision": "0006_language_listening_reservations",
  "missing_tables": ["language_listening_reservations"],
  "missing_indexes": []
}
```

Protected routes:

- `GET /api/student/languages/listening/journey`
- `GET /api/student/languages/listening/next`
- `GET /api/student/languages/listening/{id}`
- `POST /api/student/languages/listening/{id}/submit`
- `POST /api/student/languages/listening/{id}/skip`
- `POST /api/student/languages/listening/skip`

---

## Rollback notes

### Roll back reservation table only (Phase 2.2)

```bash
cd backend
venv\Scripts\python.exe -m alembic downgrade 0005_language_progression
```

This drops `language_listening_reservations`. Listening bundle endpoints will return **503** `DATABASE_MIGRATION_REQUIRED` (not 500).

### Roll back progression (Phase 4.2)

```bash
venv\Scripts\python.exe -m alembic downgrade 0004_language_analytics_xp
```

**Warning:** Drops `language_progression` and official CEFR storage. Only use in non-production or with backup.

### Production rollback policy

1. Take a DB snapshot before any downgrade.
2. Prefer forward-fix (`alembic upgrade head`) over downgrade in production.
3. After downgrade, run `verify_listening_deployment.py` and confirm expected degraded state.

---

## Production smoke tests

After deploy + migrations:

- [ ] `python scripts/verify_listening_deployment.py` → PASS
- [ ] `GET /health` → `deployment_ready: true`
- [ ] Authenticated `GET /api/student/languages/listening/journey` → **200** with `official_level`, `journey_target`, `narrative`
- [ ] Authenticated `GET /api/student/languages/listening/next` → **200** with `LessonExperienceBundle` shape
- [ ] Complete one lesson submit → **200** with `bundle.after_lesson`
- [ ] Refresh practice tab → same `lesson_id` (reservation pin)
- [ ] Backend startup log shows `Listening deployment schema OK`

---

## Promotion / progression tables

Promotion readiness and test state are stored in:

- `language_progression` (including `promotion_readiness_json`)
- `language_progression_events`

There is no separate promotion table. The deployment script treats `language_progression` as the promotion storage requirement.

---

## Related docs

- `backend/LANGUAGE-ADAPTIVE-LEARNING-PHASE-2.3-REPORT.md` — bundle architecture
- `docs/LISTENING_CANONICAL_EXPERIENCE_ARCHITECTURE.md` — canonical contracts
- `backend/scripts/verify_language_adaptive_learning_phase_2_2.py` — reservation regression
- `backend/scripts/verify_language_adaptive_learning_phase_2_3.py` — bundle regression
