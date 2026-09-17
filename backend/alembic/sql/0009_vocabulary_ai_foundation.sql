-- Phase 1 foundation for AI-generated, interest-aware vocabulary.

ALTER TABLE public.language_vocabulary_progress
    ADD COLUMN IF NOT EXISTS is_difficult boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS fail_count integer NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS public.language_vocabulary_ai_daily_usage (
    id uuid PRIMARY KEY,
    student_id integer NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    usage_date date NOT NULL,
    generated_count integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_language_vocabulary_ai_daily_usage_student_date UNIQUE (student_id, usage_date)
);

CREATE INDEX IF NOT EXISTS ix_language_vocabulary_ai_daily_usage_student_id
    ON public.language_vocabulary_ai_daily_usage (student_id);
