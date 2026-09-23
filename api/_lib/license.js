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

// ── app_scope: WHICH APP IS THIS LICENCE FOR (2026-09-23) ─────────────────
// `expectedApp` is OPTIONAL and every pre-existing caller omits it. Omitted,
// the verdict is 'not-asked' and nothing about this function's behaviour
// changes -- api/sd-data.js, api/sd-render.js and _lib/sd-store.js are
// byte-identical to yesterday.
//
// WHY IT IS A PARAMETER RATHER THAN A NEW EXPORT. Forty-seven test files
// replace this module in require.cache with a fake exporting only
// validateLicenseKey. An earlier fix on this file extracted a helper into a
// new export and broke SIXTEEN suites at once -- undefined at call time, which
// `node --check` cannot see because it is a runtime error. A new parameter is
// invisible to a fake that ignores it, and a fake that omits `app_scope` from
// its return yields undefined, which is not 'mismatch', so a test double fails
// OPEN rather than refusing every call in a suite that is not about licences.
//
// THREE STATES, AND ONLY THE MIDDLE ONE IS REFUSABLE:
//   'match'          the licence names this app
//   'mismatch'       it names a DIFFERENT registered app  -> callers refuse
//   'unattributable' cannot tell -- refusing would be a guess
//   'not-asked'      the caller did not supply an app
//
// UNATTRIBUTABLE IS ADMITTED ON PURPOSE. api/_resources/index.js already took
// this posture and wrote the reason down: nothing read `lic.app_id` before
// 2026-09-04, so there is no evidence every live licence has it set, and
// refusing an unrecognised one breaks a real customer nobody can enumerate.
// "cannot attribute -> cannot judge". Fail-closed in the wrong direction is
// still wrong.
//
// AND THE JUDGE IS NOT EXEMPT: an `expectedApp` the registry does not know is
// also 'unattributable'. api/sd-sub-auth.js mints tokens for 'stonedesk_sub',
// which is not a registered app -- had that name been passed, every judgement
// would have collapsed to cannot-tell while the endpoint looked guarded.
//
// The registry's own normApp does the case/whitespace handling. Requiring it
// lazily keeps module-load cost and ordering unchanged for the callers that
// never ask.
function appScope(licAppId, expectedApp) {
  if (expectedApp === undefined || expectedApp === null) return 'not-asked';
  const reg = require('../_resources');
  if (!reg.isKnownApp(expectedApp)) return 'unattributable';
  if (!reg.isKnownApp(licAppId)) return 'unattributable';
  return reg.normApp(licAppId) === reg.normApp(expectedApp) ? 'match' : 'mismatch';
}

async function validateLicenseKey(key, expectedApp) {
  const out = {
    valid: false,
    active: false,
    customer_email: null,
    plan_tier: null,
    app_id: null,
    trial_ends_at: null,
    stripe_subscription_id: null,
    subscription_status: null,
    license_hash: null,
    app_scope: appScope(null, expectedApp),
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
  // ── SUBSCRIPTION STATE, READ IF PRESENT (2026-09-15, item 100) ──────────
  // `stripe_subscription_id` is an IDENTIFIER. A cancelled subscription keeps
  // its `sub_...` forever, so the id is the receipt that a subscription once
  // existed and is never evidence that it exists now. Three handlers derived a
  // paid tier from its mere presence, which is a gate that can never revoke.
  //
  // THIS COLUMN DOES NOT EXIST TODAY AND NOTHING IS INVENTED BY READING IT.
  // The query above is `select=*` precisely so a newly-added column is read if
  // present and simply absent before its migration -- the same treatment
  // trial_ends_at already gets, and the same sentence four lines up says so.
  // Absent, it normalises to null, and the call sites treat null as
  // CANNOT-TELL rather than as either answer.
  out.subscription_status = row.subscription_status || null;
  // Recomputed now that the row's app_id is known. The initial value above is
  // the no-row answer, so an unknown key never carries a 'match' or a
  // 'mismatch' it could be read through.
  out.app_scope = appScope(out.app_id, expectedApp);
  return out;
}

module.exports = { validateLicenseKey, hashLicense };
