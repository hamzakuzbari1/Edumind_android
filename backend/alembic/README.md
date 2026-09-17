## Alembic migrations (PostgreSQL)

EduSpark uses **Alembic** for schema evolution. Do **not** use `create_all()` in production.

### Common commands

From `backend/`:

- Create a new migration (autogenerate):
  - `alembic revision --autogenerate -m "message"`
- Apply migrations:
  - `alembic upgrade head`
- Roll back one:
  - `alembic downgrade -1`

### Notes

- Alembic uses a **synchronous** URL (`postgresql+psycopg2://`) via `SYNC_DATABASE_URL` or `DATABASE_URL_SYNC`.
- FastAPI runtime continues to use `DATABASE_URL` (`postgresql+asyncpg://`).
- Autogenerate relies on importing `app.models` inside `alembic/env.py` to populate `Base.metadata`.

### `0002_lesson_asset_enum`

Creates PostgreSQL enum `lessonassettype` (`video`, `pdf`, `homework`) and converts
`lesson_assets.asset_type` from `VARCHAR` when needed. Required for multi-asset lesson uploads.

Verify after upgrade:

```sql
SELECT unnest(enum_range(NULL::lessonassettype));
```
