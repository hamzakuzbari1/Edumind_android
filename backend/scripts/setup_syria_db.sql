-- EduSpark Syria — dedicated PostgreSQL database (isolated from legacy shared `eduspark`).
-- Run as superuser:
--   psql -U postgres -f backend/scripts/setup_syria_db.sql

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'eduspark') THEN
    CREATE USER eduspark WITH PASSWORD 'eduspark' LOGIN;
  ELSE
    ALTER USER eduspark WITH PASSWORD 'eduspark';
  END IF;
END
$$;

SELECT 'CREATE DATABASE eduspark_syria OWNER eduspark'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'eduspark_syria')\gexec

GRANT ALL PRIVILEGES ON DATABASE eduspark_syria TO eduspark;

\c eduspark_syria

-- pgvector is OPTIONAL (default ENABLE_PGVECTOR=false; the schema does not require it).
-- Only enable if you install pgvector on the server AND set ENABLE_PGVECTOR=true:
--   CREATE EXTENSION IF NOT EXISTS vector;

GRANT ALL ON SCHEMA public TO eduspark;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO eduspark;
