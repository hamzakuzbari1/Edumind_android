-- Run once if content_chunks was created with pgvector and startup fails:
-- psql -U postgres -d eduspark -f backend/scripts/reset_content_chunks.sql

DROP TABLE IF EXISTS content_chunks CASCADE;
