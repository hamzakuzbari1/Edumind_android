-- XP progression columns for language_analytics (award_language_xp idempotency + level bar).
ALTER TABLE public.language_analytics
    ADD COLUMN IF NOT EXISTS xp_keys_json jsonb,
    ADD COLUMN IF NOT EXISTS xp_total integer DEFAULT 0 NOT NULL,
    ADD COLUMN IF NOT EXISTS level_xp integer DEFAULT 0 NOT NULL;
