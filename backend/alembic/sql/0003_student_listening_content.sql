-- Per-student personalized listening lessons (Phase 2 personalization).
-- NULL student_id = shared seed/nightly pool (unchanged). Non-null = owned by one student only.

ALTER TABLE public.language_content_items
    ADD COLUMN IF NOT EXISTS student_id integer;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_language_content_items_student_id'
    ) THEN
        ALTER TABLE public.language_content_items
            ADD CONSTRAINT fk_language_content_items_student_id
            FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_language_content_items_student_listening
    ON public.language_content_items (student_id, language_id, skill, level)
    WHERE student_id IS NOT NULL;
