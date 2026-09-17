-- Minimal setup when database "eduspark" already exists (use postgres superuser):
--   psql -U postgres -d eduspark -f backend/scripts/setup_local_db_simple.sql

CREATE EXTENSION IF NOT EXISTS vector;

-- Optional: create app user matching .env
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'eduspark') THEN
    CREATE USER eduspark WITH PASSWORD 'eduspark' LOGIN;
  ELSE
    ALTER USER eduspark WITH PASSWORD 'eduspark';
  END IF;
END
$$;

GRANT ALL ON SCHEMA public TO eduspark;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO eduspark;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO eduspark;
