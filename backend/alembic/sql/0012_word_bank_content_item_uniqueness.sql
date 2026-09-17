-- Vocabulary revamp Phase 7 follow-up — close a race condition in the word bank's
-- get-or-create sharing mechanism. _get_or_create_content_item() was a plain
-- check-then-insert with no DB-level uniqueness backing it: two concurrent requests
-- for the same never-before-seen (level, word) could both miss the SELECT and both
-- INSERT, creating two content items for what should be one shared, cached row.
--
-- Scoped to source='word_bank' only — legacy pre-word-bank rows (content_type=
-- 'vocabulary', source='ai_generated' or unset) already contain a handful of
-- pre-existing duplicates from the old ungated live-LLM flow, and per prior
-- direction those are left as orphaned history, not backfilled or constrained.
CREATE UNIQUE INDEX uq_language_content_items_word_bank_word_level
    ON public.language_content_items (language_id, level, ((body_json ->> 'word')))
    WHERE content_type = 'vocabulary' AND body_json ->> 'source' = 'word_bank';
