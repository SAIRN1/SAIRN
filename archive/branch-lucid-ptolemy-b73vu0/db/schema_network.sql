-- ═══════════════════════════════════════════════════════════════════
-- SAIRN Technologies — Intelligence Network Schema
-- Cross-customer anonymized pattern learning, per sairn-intelligence-network skill
-- Michael L. Dibert · 2026
-- Run AFTER schema.sql, schema_b2b.sql, db/schema_memory.sql, db/schema_security.sql
-- ═══════════════════════════════════════════════════════════════════

-- Anonymized cross-business pattern store. NEVER write raw business data here --
-- every insert MUST go through scrubPattern() in api/network.js first. The
-- scrubbed_clean column exists so a human can audit, at a glance, that every
-- row in this table actually passed the scrub gate -- if scrubbed_clean is
-- false on any row, that row should never have been inserted and is a bug.
CREATE TABLE IF NOT EXISTS net_insights (
  id             UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  app_type       TEXT NOT NULL,            -- 'stonedesk', 'sairncode', etc. -- never a shop name
  insight_type   TEXT DEFAULT 'general',
  pattern        TEXT NOT NULL,            -- scrubbed, max 500 chars, no $ amounts, no proper nouns
  context        TEXT DEFAULT '',          -- scrubbed, max 200 chars
  score          FLOAT DEFAULT 0.5 CHECK (score >= 0 AND score <= 1),
  count          INTEGER DEFAULT 1 CHECK (count >= 1),
  scrubbed_clean BOOLEAN NOT NULL DEFAULT false,  -- set true only by the scrub function itself
  source_hash    TEXT,                     -- one-way hash of contributing shop id, for dedupe only -- never reversible to identity
  created_at     TIMESTAMPTZ DEFAULT now(),
  updated_at     TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_net_insights_app      ON net_insights(app_type);
CREATE INDEX IF NOT EXISTS idx_net_insights_score     ON net_insights(score DESC);
CREATE INDEX IF NOT EXISTS idx_net_insights_pattern_app ON net_insights(app_type, pattern);

-- RLS: this table is never readable or writable by an end user's own session --
-- only the proxy's service_role key (api/network.js, server-side) may touch it.
-- Demo/free-tier and licensed customers alike read it through the GET endpoint,
-- not direct table access, so there is no per-row user policy to define.
ALTER TABLE net_insights ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role only" ON net_insights
  FOR ALL USING (auth.role() = 'service_role');

-- Audit table: every rejected insert attempt (failed the scrub gate) gets logged
-- here instead of silently dropped, so a pattern of "something keeps trying to
-- leak a price or a name" is visible and fixable, not invisible.
CREATE TABLE IF NOT EXISTS net_insights_rejected (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  app_type    TEXT,
  raw_pattern TEXT,             -- the UNSCRUBBED text that failed the gate, kept only
                                 -- long enough to debug the calling code, never surfaced
                                 -- to any cross-app read endpoint
  reject_reason TEXT,           -- 'dollar_amount', 'proper_noun_suspected', 'too_long', 'pii_pattern'
  created_at  TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE net_insights_rejected ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON net_insights_rejected
  FOR ALL USING (auth.role() = 'service_role');

-- Housekeeping: rejected-pattern log only needs to exist long enough to debug
-- a calling site, not forever. Run periodically (manual or cron) -- not
-- automatic, since Supabase free/pro tiers don't ship pg_cron by default.
-- DELETE FROM net_insights_rejected WHERE created_at < now() - interval '30 days';
