-- ═══════════════════════════════════════════════════════════════════
-- SAIRN Technologies — Enterprise Token Schema
-- Prevents any company from ever crashing due to token exhaustion
-- Michael L. Dibert · 2026 · Patent Pending
-- ═══════════════════════════════════════════════════════════════════

-- ── ORGANIZATIONS (Enterprise accounts) ──────────────────────────
-- One org = one company (e.g. Goodyear, a vet clinic, a funeral home)
-- All users in an org share the same token pool
CREATE TABLE IF NOT EXISTS organizations (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name            TEXT NOT NULL,
  plan            TEXT NOT NULL DEFAULT 'b2b_starter',
  status          TEXT NOT NULL DEFAULT 'active', -- active, suspended, trial
  monthly_budget  BIGINT DEFAULT 5000000,         -- tokens/mo (-1 = unlimited)
  auto_scale      BOOLEAN DEFAULT false,           -- never cut off if true
  contact_email   TEXT,
  stripe_customer TEXT,
  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now()
);

-- ── ORG FIELD ON USERS ────────────────────────────────────────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id);
ALTER TABLE users ADD COLUMN IF NOT EXISTS org_role TEXT DEFAULT 'member'; -- admin, member

-- ── ORG FIELD ON USAGE_LOGS ──────────────────────────────────────
-- Allows querying total org usage in one call
ALTER TABLE usage_logs ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_org_id ON usage_logs(org_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_org_month ON usage_logs(org_id, created_at DESC);

-- ── USAGE ALERTS ─────────────────────────────────────────────────
-- Tracks which alerts have been fired so we don't spam
CREATE TABLE IF NOT EXISTS usage_alerts (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id     UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  org_id      UUID REFERENCES organizations(id),
  plan        TEXT,
  alert_type  TEXT NOT NULL, -- warn_80, warn_95, limit_reached, auto_scaled
  tokens_used BIGINT,
  budget      BIGINT,
  message     TEXT,
  actioned    BOOLEAN DEFAULT false,
  created_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_alerts_user ON usage_alerts(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_org  ON usage_alerts(org_id, created_at DESC);

-- ── TOKEN PLAN DEFINITIONS ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS token_plans (
  plan_id         TEXT PRIMARY KEY,
  display_name    TEXT NOT NULL,
  monthly_tokens  BIGINT NOT NULL, -- -1 = unlimited
  price_monthly   NUMERIC(10,2),
  auto_scale      BOOLEAN DEFAULT false,
  stripe_price_id TEXT,
  description     TEXT
);

INSERT INTO token_plans VALUES
-- Consumer
('trialing',      'Free Trial',           100000,      0,      false, null,                       '14-day trial'),
('individual',    'Individual',           500000,       9.99,  false, 'price_individual',         'Single user, one app'),
('family',        'Family Plan',          1500000,      19.99, false, 'price_family',             'All 19 NEXUS apps'),
('legal',         'Legal Plan',           750000,       19.99, false, 'price_legal',              'SAIRN Legal enhanced'),
-- B2B
('b2b_starter',   'B2B Starter',          5000000,     199,    false, 'price_b2b_starter',        '~5M tokens/mo, 3 users'),
('b2b_pro',       'B2B Professional',     15000000,    299,    false, 'price_b2b_pro',            '~15M tokens/mo, unlimited users'),
('b2b_business',  'B2B Business',         40000000,    499,    false, 'price_b2b_business',       '~40M tokens/mo, full features'),
-- Enterprise
('enterprise_s',  'Enterprise Standard',  100000000,  2000,   false, 'price_enterprise_s',       '~100M tokens/mo'),
('enterprise_m',  'Enterprise Plus',      500000000,  5000,   true,  'price_enterprise_m',       '~500M tokens/mo, auto-scale'),
('enterprise_l',  'Enterprise Unlimited', -1,         0,      true,  null,                       'Custom contract, never cut off')
ON CONFLICT (plan_id) DO UPDATE SET
  monthly_tokens = EXCLUDED.monthly_tokens,
  price_monthly  = EXCLUDED.price_monthly,
  auto_scale     = EXCLUDED.auto_scale;

-- ── TOKEN USAGE SUMMARY VIEW ──────────────────────────────────────
-- Fast lookup for any org's current month usage
CREATE OR REPLACE VIEW org_token_usage AS
SELECT
  org_id,
  DATE_TRUNC('month', created_at) AS month,
  SUM(tokens_in + tokens_out)     AS tokens_used,
  SUM(cost_usd)                   AS cost_usd,
  COUNT(*)                        AS call_count
FROM usage_logs
WHERE org_id IS NOT NULL
GROUP BY org_id, DATE_TRUNC('month', created_at);

-- ── CLEANUP ───────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION cleanup_token_records()
RETURNS void AS $$
BEGIN
  DELETE FROM usage_alerts WHERE created_at < now() - INTERVAL '90 days' AND actioned = true;
  DELETE FROM demo_calls    WHERE created_at < now() - INTERVAL '7 days';
  DELETE FROM security_events WHERE created_at < now() - INTERVAL '30 days' AND severity = 'info';
END;
$$ LANGUAGE plpgsql;

-- ═══════════════════════════════════════════════════════════════════
-- WHAT THIS MEANS FOR GOODYEAR:
-- org_id = goodyear-uuid
-- plan = enterprise_l (unlimited, auto_scale = true)
-- All 68,000 employees share one org_id
-- Usage tracked at org level → one bill, one limit
-- auto_scale = true → NEVER cut off, bill overages monthly
-- At 80% usage → email their IT admin
-- At 95% usage → email + Slack
-- At 100% → still works, just billed for overage
-- ZERO CRASHES. EVER.
-- ═══════════════════════════════════════════════════════════════════
