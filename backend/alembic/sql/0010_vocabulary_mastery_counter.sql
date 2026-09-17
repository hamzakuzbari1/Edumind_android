-- Phase 3: consecutive Good/Easy counter to clear is_difficult.

ALTER TABLE public.language_vocabulary_progress
    ADD COLUMN IF NOT EXISTS consecutive_good_count integer NOT NULL DEFAULT 0;
