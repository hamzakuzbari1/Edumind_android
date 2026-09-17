-- Run as PostgreSQL superuser (adjust if your superuser is different):
--   psql -U postgres -f backend/scripts/setup_local_db.sql
--
-- Creates role + database for EduSpark Syria (dedicated DB, isolated from legacy shared `eduspark`).

-- Role (skip errors if already exists)
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'eduspark') THEN
    CREATE USER eduspark WITH PASSWORD 'eduspark' LOGIN;
  ELSE
    ALTER USER eduspark WITH PASSWORD 'eduspark';
  END IF;
END
$$;

-- Database (skip if you already created it manually)
SELECT 'CREATE DATABASE eduspark_syria OWNER eduspark'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'eduspark_syria')\gexec

GRANT ALL PRIVILEGES ON DATABASE eduspark_syria TO eduspark;

\c eduspark_syria

-- pgvector is OPTIONAL (default ENABLE_PGVECTOR=false; the schema does not require it).
-- Only enable if you install pgvector on the server AND set ENABLE_PGVECTOR=true:
--   CREATE EXTENSION IF NOT EXISTS vector;

GRANT ALL ON SCHEMA public TO eduspark;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO eduspark;
