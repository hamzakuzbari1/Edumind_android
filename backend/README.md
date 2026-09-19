# EduSpark Backend

## Docker

Docker runs the FastAPI service only. The API uses the shared Supabase DEV
PostgreSQL and Supabase Storage configured in the local ignored
`backend/.env`; Docker does not start a local PostgreSQL service.

Prerequisites: Docker Desktop.

From the repository root:

```bash
# First run: create backend/.env from backend/.env.example and fill in
# authorized shared DEV values locally.
docker compose up --build
```

The API is available at http://localhost:8000 and its interactive docs are at
http://localhost:8000/docs.

```bash
docker compose down
docker compose logs -f api
docker compose up --build
```

Android runs outside Docker from Android Studio, an emulator, or a physical
device. For explicit local Android development only, set `APP_ENV=local` and
`API_BASE_URL=http://10.0.2.2:8000`. Shared builds continue using the hosted
Render API. Never commit `backend/.env`; a host Python `.venv` is optional when
using Docker.

## Local run (no Docker)

```bash
# 1. PostgreSQL running on localhost with pgvector
psql -U postgres -f scripts/setup_local_db.sql

# 2. From backend/
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-voice.txt

python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Docs: http://127.0.0.1:8000/docs

Loads `.env` from project root (`../.env`).

## API

- `POST /api/auth/register` · `POST /api/auth/login`
- Teacher upload/process · Student lessons/chat/quiz/profile

## Database migrations

```bash
alembic upgrade head
```

## Clean demo data (one-time)

```bash
python scripts/purge_demo_data.py --audit   # list demo rows
python scripts/purge_demo_data.py           # delete demo rows
```

Removes all `*@eduspark.sy` accounts and legacy seeded teachers (e.g. أحمد الحسين، كريم العلي).

Optional reference subjects only (no demo users):

```bash
python scripts/seed_reference_subjects.py
```

## Listening placement bank-audio backfill

Pre-synthesizes and persists audio for the currently reachable Listening placement bank items
(`skill="listening"`, active, verified, with a resolvable transcript), so the live AI Exam prefers
this cached audio over synthesizing it fresh on every attempt. Safe to re-run any time — it's a
no-op once every eligible row already has valid, on-disk cached audio.

```bash
python scripts/backfill_listening_bank_audio.py                    # dry-run: report scope only
python scripts/backfill_listening_bank_audio.py --apply             # generate + persist audio
python scripts/backfill_listening_bank_audio.py --apply --force      # force-regenerate everything
python scripts/backfill_listening_bank_audio.py --apply --item-id 23 # target one bank item
```

- Default is always dry-run; nothing is written until `--apply` is passed.
- Never runs automatically — there is no server-startup hook for it.
- The first `--apply` run on a host/volume with no cached Supertonic model weights yet will
  trigger a one-time, multi-minute model download (existing Supertonic behavior, unchanged here).
- Re-run this command after any change to a listening bank item's transcript, after a fresh
  database/reseed, or after losing the `uploads/` tree independently of the database — it is the
  reproducible mechanism for restoring cached audio in every one of those cases.
