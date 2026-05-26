-- ═══════════════════════════════════════════════════════════════════
-- SAIRN Technologies — Security Schema Additions
-- Run after schema.sql and schema_v2.sql
-- Michael L. Dibert · 2026
-- ═══════════════════════════════════════════════════════════════════

-- Security events table — anomaly detection, failed auth, injection attempts
CREATE TABLE IF NOT EXISTS security_events (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id     UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  ip_hash     TEXT,
  app_id      TEXT,
  event       TEXT NOT NULL,  -- 'usage_spike', 'injection_attempt', 'auth_failure', 'rate_limit'
  detail      TEXT,
  severity    TEXT DEFAULT 'info', -- 'info', 'warning', 'critical'
  created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_security_events_user    ON security_events(user_id);
CREATE INDEX IF NOT EXISTS idx_security_events_created ON security_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_security_events_event   ON security_events(event);

-- RLS — only service role can read security events
ALTER TABLE security_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON security_events FOR ALL USING (true);

-- Brute force tracking — failed login attempts per email
CREATE TABLE IF NOT EXISTS auth_failures (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  email_hash  TEXT NOT NULL,
  ip_hash     TEXT,
  created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_auth_failures_email   ON auth_failures(email_hash);
CREATE INDEX IF NOT EXISTS idx_auth_failures_created ON auth_failures(created_at DESC);

-- Auto-cleanup old records (keep 30 days)
CREATE OR REPLACE FUNCTION cleanup_old_security_records()
RETURNS void AS $$
BEGIN
  DELETE FROM security_events  WHERE created_at < now() - INTERVAL '30 days';
  DELETE FROM auth_failures     WHERE created_at < now() - INTERVAL '24 hours';
  DELETE FROM demo_calls        WHERE created_at < now() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;
