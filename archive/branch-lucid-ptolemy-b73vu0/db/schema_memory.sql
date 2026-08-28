-- ═══════════════════════════════════════════════════════════════════
-- SAIRN Technologies — Memory Schema
-- The NEXUS Cross-Module Intelligence Engine
-- Michael L. Dibert · 2026 · Patent Pending
-- ═══════════════════════════════════════════════════════════════════

-- User memory profile — one row per user, grows over time
CREATE TABLE IF NOT EXISTS user_memory (
  user_id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  facts                JSONB    NOT NULL DEFAULT '[]',
  summary              TEXT     DEFAULT '',
  last_updated         TIMESTAMPTZ DEFAULT now(),
  total_conversations  INTEGER  DEFAULT 0,
  apps_used            TEXT[]   DEFAULT '{}',
  created_at           TIMESTAMPTZ DEFAULT now()
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_user_memory_user_id ON user_memory(user_id);
CREATE INDEX IF NOT EXISTS idx_user_memory_updated ON user_memory(last_updated DESC);

-- RLS: users can only see their own memory
ALTER TABLE user_memory ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own memory"
  ON user_memory FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Service role can do everything"
  ON user_memory FOR ALL
  USING (true)
  WITH CHECK (true);

-- ═══════════════════════════════════════════════════════════════════
-- Example of what a memory row looks like after 2 weeks of use:
-- ═══════════════════════════════════════════════════════════════════
--
-- user_id: abc-123
-- facts: [
--   {"category":"PERSONAL",  "fact":"lives in Columbus, Ohio",              "confidence":"high", "app_id":"career",  "extracted_at":"2026-05-15"},
--   {"category":"FAMILY",    "fact":"has a 9-year-old son named Jake",      "confidence":"high", "app_id":"family",  "extracted_at":"2026-05-16"},
--   {"category":"CAREER",    "fact":"interviewing for senior PM role",      "confidence":"high", "app_id":"career",  "extracted_at":"2026-05-17"},
--   {"category":"MENTAL",    "fact":"anxiety spikes on Sunday evenings",    "confidence":"high", "app_id":"mind",    "extracted_at":"2026-05-18"},
--   {"category":"FOOD",      "fact":"son Jake is lactose intolerant",       "confidence":"high", "app_id":"kitchen", "extracted_at":"2026-05-19"},
--   {"category":"HEALTH",    "fact":"trying to sleep 7+ hours, struggles", "confidence":"high", "app_id":"health",  "extracted_at":"2026-05-20"},
--   {"category":"HOME",      "fact":"renting, lease up in August 2026",     "confidence":"high", "app_id":"home",    "extracted_at":"2026-05-21"},
-- ]
-- summary: "Working parent in Columbus, son Jake (9, lactose intolerant),
--           interviewing for senior PM role, manages anxiety, wants better sleep."
-- total_conversations: 14
-- apps_used: ["career","family","mind","kitchen","health","home","daily"]
--
-- Now imagine SAIRN Kitchen opening for the first time this week:
-- Claude already knows Jake is lactose intolerant.
-- No one had to tell it twice.
-- ═══════════════════════════════════════════════════════════════════
