-- ================================================================
-- SAIRN Technologies -- License Keys Schema
-- Stores auto-generated license keys issued on Stripe checkout.
-- Run in Supabase SQL Editor after schema.sql.
-- Michael L. Dibert -- SAIRN Technologies -- 2026
-- ================================================================

CREATE TABLE IF NOT EXISTS license_keys (
  id                     UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  key                    TEXT        UNIQUE NOT NULL,
  app_id                 TEXT        NOT NULL,
  shop_name              TEXT,
  customer_email         TEXT,
  stripe_customer_id     TEXT,
  stripe_subscription_id TEXT,
  plan                   TEXT        NOT NULL DEFAULT 'b2b_starter',
  status                 TEXT        NOT NULL DEFAULT 'active',  -- active | cancelled | suspended
  created_at             TIMESTAMPTZ DEFAULT now(),
  updated_at             TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_lk_key    ON license_keys(key);
CREATE INDEX IF NOT EXISTS idx_lk_email  ON license_keys(customer_email);
CREATE INDEX IF NOT EXISTS idx_lk_stripe ON license_keys(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_lk_app    ON license_keys(app_id, status);

-- Service role only -- keys must never be exposed to browser clients
ALTER TABLE license_keys ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON license_keys FOR ALL USING (true);

-- Auto-update updated_at on every write
CREATE OR REPLACE FUNCTION update_license_key_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_license_keys_updated_at ON license_keys;
CREATE TRIGGER trg_license_keys_updated_at
  BEFORE UPDATE ON license_keys
  FOR EACH ROW EXECUTE FUNCTION update_license_key_timestamp();
