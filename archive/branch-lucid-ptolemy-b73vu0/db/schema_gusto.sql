-- ═══════════════════════════════════════════════════════════════════
-- SAIRN Technologies — Gusto Connection Schema
-- Michael L. Dibert · 2026
-- Run AFTER schema.sql and schema_b2b.sql
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS gusto_connections (
  shop_id                  TEXT PRIMARY KEY,
  company_uuid              TEXT,
  access_token             TEXT NOT NULL,
  refresh_token            TEXT NOT NULL,
  access_token_expires_at  TIMESTAMPTZ,
  environment              TEXT DEFAULT 'demo',  -- 'demo' | 'production'
  connected_at              TIMESTAMPTZ DEFAULT now(),
  updated_at                TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_gusto_connections_company ON gusto_connections(company_uuid);

-- RLS: tokens never readable by an end user's own session -- only the
-- proxy's service_role key (api/gusto.js) may touch this table.
ALTER TABLE gusto_connections ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON gusto_connections
  FOR ALL USING (auth.role() = 'service_role');
