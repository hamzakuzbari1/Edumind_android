-- Vocabulary revamp Phase 7 — fixed, per-level word bank.
--
-- The old language_vocabulary_catalog table was created but never populated
-- (offline generator was removed in Phase 6). Rename it in place into the
-- new fixed word bank rather than standing up a parallel table, and drop
-- the never-used per-student "seen" tracking table (superseded by
-- language_vocabulary_progress, which is keyed by lemma already).

ALTER TABLE public.language_vocabulary_catalog RENAME TO language_vocabulary_word_bank;

ALTER TABLE public.language_vocabulary_word_bank
    RENAME CONSTRAINT language_vocabulary_catalog_pkey TO language_vocabulary_word_bank_pkey;

ALTER TABLE public.language_vocabulary_word_bank
    RENAME CONSTRAINT uq_language_vocabulary_catalog_word_level TO uq_language_vocabulary_word_bank_word_level;

ALTER INDEX public.ix_language_vocabulary_catalog_cefr_level RENAME TO ix_language_vocabulary_word_bank_cefr_level;
ALTER INDEX public.ix_language_vocabulary_catalog_word RENAME TO ix_language_vocabulary_word_bank_word;
ALTER INDEX public.ix_language_vocabulary_catalog_context_theme RENAME TO ix_language_vocabulary_word_bank_topic;

ALTER TABLE public.language_vocabulary_word_bank RENAME COLUMN translation TO translation_ar;
ALTER TABLE public.language_vocabulary_word_bank RENAME COLUMN context_theme TO topic;

ALTER TABLE public.language_vocabulary_word_bank
    ALTER COLUMN cefr_level DROP DEFAULT,
    ALTER COLUMN cefr_level TYPE language_level USING cefr_level::language_level;

ALTER TABLE public.language_vocabulary_word_bank
    ADD COLUMN example_sentence_ar text NOT NULL DEFAULT '',
    ADD COLUMN image_prompt text NOT NULL DEFAULT '',
    ADD COLUMN sort_order integer NOT NULL DEFAULT 0,
    ADD COLUMN updated_at timestamptz NOT NULL DEFAULT now();

DROP TABLE IF EXISTS public.language_vocabulary_catalog_seen;
