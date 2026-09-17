-- Listening session reservations (Phase 2.2).
-- One active reservation per (student_id, language_id) enforced via partial unique index.

CREATE TABLE IF NOT EXISTS public.language_listening_reservations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id integer NOT NULL,
    language_id integer NOT NULL,
    content_item_id integer NOT NULL,
    lifecycle_state character varying(32) NOT NULL DEFAULT 'reserved',
    reserved_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    reviewed_at timestamp with time zone,
    archived_at timestamp with time zone,
    archive_reason character varying(32),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT language_listening_reservations_student_id_fkey
        FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE,
    CONSTRAINT language_listening_reservations_language_id_fkey
        FOREIGN KEY (language_id) REFERENCES public.languages(id) ON DELETE CASCADE,
    CONSTRAINT language_listening_reservations_content_item_id_fkey
        FOREIGN KEY (content_item_id) REFERENCES public.language_content_items(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_language_listening_reservations_student_language
    ON public.language_listening_reservations (student_id, language_id);

CREATE INDEX IF NOT EXISTS ix_language_listening_reservations_content_item
    ON public.language_listening_reservations (content_item_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_language_listening_reservations_active
    ON public.language_listening_reservations (student_id, language_id)
    WHERE lifecycle_state IN ('reserved', 'started');
