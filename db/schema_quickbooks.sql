-- ═══════════════════════════════════════════════════════════════════
-- SAIRN Technologies — QuickBooks Online Connection Schema
-- Michael L. Dibert · 2026
-- Run AFTER schema.sql and schema_b2b.sql
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS qb_connections (
  shop_id                  TEXT PRIMARY KEY,   -- matches public.shops.id or app-level shop identifier
  realm_id                 TEXT NOT NULL,      -- QuickBooks company ID
  access_token             TEXT NOT NULL,
  refresh_token            TEXT NOT NULL,
  access_token_expires_at  TIMESTAMPTZ,
  environment              TEXT DEFAULT 'sandbox',  -- 'sandbox' | 'production'
  connected_at              TIMESTAMPTZ DEFAULT now(),
  updated_at                TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_qb_connections_realm ON qb_connections(realm_id);

-- RLS: tokens never readable by an end user's own session -- only the
-- proxy's service_role key (api/quickbooks.js) may touch this table.
ALTER TABLE qb_connections ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON qb_connections
  FOR ALL USING (auth.role() = 'service_role');
