# Backend tests

Run the complete backend suite from the repository root with one command:

```powershell
docker compose run --rm --build backend-test
```

The command starts an isolated PostgreSQL 16 service, rebuilds the test image, resets only the
`eduspark_test` database, applies Alembic through `head`, and runs `pytest`. The image copies only
`backend/tests`; `backend/scripts/test_*.py` are outside pytest's configured collection roots.

The database reset is guarded by the expected `_test` database name, the dedicated `db-test`
hostname, and `TEST_DATABASE_RESET_ALLOWED=1`. Never point the test service at production data.
