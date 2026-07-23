// api/_lib/license.js
// ---------------------------------------------------------------------------
// SHARED license-key validation. Single source of truth — do NOT fork this.
// Called by BOTH api/sd-data.js (this data endpoint's auth) and Pattern 13's
// entitlement gate, so the two checks can never drift apart (decision D4).
//
// Files under api/_lib are NOT routed by Vercel (leading underscore) — this is
// an importable helper, not an endpoint.
//
// Returns a plain object both callers can use:
//   { valid, active, customer_email, plan_tier, app_id, license_hash, key }
//     valid          — the key exists in license_keys
//     active         — status === 'active'
//     customer_email — tenant identity (used to scope employees, etc.)
//     plan_tier      — license_keys.plan  (what Pattern 13 gates on)
//     app_id         — the app the key was issued for
//     license_hash   — sha256(license_key) hex; the key the StoneDesk-owned
//                      data tables are scoped by, so the raw key never appears
//                      in their rows or query URLs
//     key            — the raw key echoed back (callers should prefer
//                      license_hash for storage/lookups)
//
// NOTE (honest residual): validation itself still looks up the pre-existing
// license_keys table by its raw `key` column, so the raw key appears in THAT
// one query URL. license_keys is owned by the license-generation system;
// hashing it too is a separate cross-system change, out of scope here.
//
// Throws (rather than returning) only on operational failures so callers can
// map them to the right HTTP status:
//   err.code === 'CONFIG'   -> missing env, respond 500
//   err.code === 'UPSTREAM' -> Supabase unreachable/errored, respond 502
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
// ---------------------------------------------------------------------------

const crypto = require('crypto');

function hashLicense(key) {
  return crypto.createHash('sha256').update(key).digest('hex');
}

async function validateLicenseKey(key) {
  const out = {
    valid: false,
    active: false,
    customer_email: null,
    plan_tier: null,
    app_id: null,
    trial_ends_at: null,
    stripe_subscription_id: null,
    license_hash: null,
    key: (typeof key === 'string' ? key : null)
  };

  if (!key || typeof key !== 'string') return out;

  out.license_hash = hashLicense(key);

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) {
    const e = new Error('SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in environment');
    e.code = 'CONFIG';
    throw e;
  }

  const headers = { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY };
  // select=* so newly-added columns (e.g. trial_ends_at) are read if present
  // and simply absent (not a 400) before their migration is applied.
  const url = SUPABASE_URL +
    '/rest/v1/license_keys?key=eq.' + encodeURIComponent(key) +
    '&select=*&limit=1';

  let res;
  try {
    res = await fetch(url, { headers });
  } catch (err) {
    const e = new Error('license_keys lookup network error: ' + err.message);
    e.code = 'UPSTREAM';
    throw e;
  }

  if (!res.ok) {
    const e = new Error('license_keys lookup failed: HTTP ' + res.status);
    e.code = 'UPSTREAM';
    throw e;
  }

  const rows = await res.json();
  if (!Array.isArray(rows) || rows.length === 0) {
    return out; // valid stays false — unknown key
  }

  const row = rows[0];
  out.valid = true;
  out.active = String(row.status || '').trim().toLowerCase() === 'active';
  out.customer_email = row.customer_email || null;
  out.plan_tier = row.plan || null;
  out.app_id = row.app_id || null;
  out.trial_ends_at = row.trial_ends_at || null;
  out.stripe_subscription_id = row.stripe_subscription_id || null;
  return out;
}

module.exports = { validateLicenseKey, hashLicense };
