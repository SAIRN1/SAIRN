// api/_lib/sd-store.js
// ---------------------------------------------------------------------------
// Data-access layer for the StoneDesk Agent SDK (api/sd-agent.js).
//
// Talks to the same Supabase tables, under the same auth model, as
// api/sd-data.js (license_hash-scoped rows, service-role key, 64KB write
// cap) — see that file's header for the full rationale. This module
// intentionally does NOT import from or modify sd-data.js: the two are kept
// as separate, independently-evolvable callers of the same tables rather
// than sharing code, since sd-data.js is an HTTP handler (req/res), not a
// library of callable functions.
//
// Each exported function takes an already-validated `lic` object (from
// validateAndGate) rather than a raw license key, so a single license check
// covers an entire agent turn instead of one check per tool call.
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
// ---------------------------------------------------------------------------

const { validateLicenseKey } = require('./license');

const MAX_PAYLOAD_BYTES = 64 * 1024; // 65536, matches sd-data.js

function storeError(code, message) {
  const e = new Error(message);
  e.code = code;
  return e;
}

// Validates a bearer license key and applies the same Pattern 13 entitlement
// gate as sd-data.js (paid licenses bypass the trial; an expired trial with
// no Stripe subscription is refused). Throws a typed error on any failure
// so callers can map .code to the right HTTP status.
async function validateAndGate(licenseKey) {
  if (!licenseKey) throw storeError('NO_LICENSE', 'Missing bearer license key');

  let lic;
  try {
    lic = await validateLicenseKey(licenseKey);
  } catch (err) {
    if (err.code === 'CONFIG') throw storeError('CONFIG', err.message);
    throw storeError('UPSTREAM', 'Upstream connection error — try again');
  }

  if (!lic.valid) throw storeError('INVALID_LICENSE', 'Unknown license key');
  if (!lic.active) throw storeError('LICENSE_INACTIVE', 'This license is not active');

  // ── INERT ON EVERY LICENCE, AND ALWAYS HAS BEEN (2026-09-08) ──────────
  // `trial_ends_at` IS NOT A COLUMN on license_keys -- measured twice by two
  // other people: a run of sql/demo_license_keys_seed.sql failed 42703
  // `column "trial_ends_at" does not exist`, and db/schema_snapshot.json,
  // captured live 2026-09-02, lists eleven columns without it. So the field is
  // null on every licence, the `&&` short-circuits, and this 402 has never
  // been reached. Do not read it as enforcement.
  //
  // NOTHING IS DELETED AND NO COLUMN IS INVENTED HERE: which of those to do is
  // a billing decision and Stripe is not configured, so nobody is on a paid
  // plan to expire. api/license-trial-gate.test.js pins this AS-IS -- the day
  // the column is added, that suite goes red and names all three handlers.
  //
  // ── AN IDENTIFIER IS NOT A STATE (2026-09-15, item 100) ────────────────
  // This was `const isPaid = !!lic.stripe_subscription_id;`. A CANCELLED
  // SUBSCRIPTION KEEPS ITS ID FOREVER -- `sub_...` is the receipt that a
  // subscription once existed, never evidence that it exists now -- so that
  // expression could grant a paid tier and could never revoke one. Fixed
  // before B2B Stripe is configured rather than after, because the same fix
  // on a live billing system is a migration plus three call sites plus a
  // reconciliation job with real customers on it.
  //
  // THREE STATES, AND THE THIRD IS NOT FOLDED INTO EITHER OTHER:
  //   knownNotPaid  no subscription was EVER created, or the mirror says the
  //                 subscription is positively dead. This is the only state
  //                 that may refuse anybody.
  //   knownPaid     the mirror says it is active or trialing.
  //   cannotTell    an id exists and the mirror carries no state for it --
  //                 TODAY'S CASE, since license_keys has no
  //                 subscription_status column. It must NOT refuse: doing so
  //                 would 402 every real subscriber the day trial_ends_at is
  //                 added and this column is not. It must not grant either,
  //                 which is why it has its own name instead of being
  //                 absorbed into `knownPaid`.
  //
  // BEHAVIOUR IS UNCHANGED TODAY, deliberately. With no status column every
  // licence is either knownNotPaid (no id -- refusable, exactly as before) or
  // cannotTell (id present -- not refused, exactly as before). What changes is
  // that a positively-cancelled subscription can now be revoked at all.
  const subState = String(lic.subscription_status || '').trim().toLowerCase();
  const everSubscribed = !!lic.stripe_subscription_id;
  const knownPaid = everSubscribed && (subState === 'active' || subState === 'trialing');
  const knownNotPaid = !everSubscribed
    || subState === 'canceled' || subState === 'cancelled'
    || subState === 'unpaid' || subState === 'past_due'
    || subState === 'incomplete_expired';
  // THE CONDITION BELOW IS `knownNotPaid`, NOT `!knownPaid`, and that is the
  // whole fix in one line. `!knownPaid` would sweep cannot-tell in with
  // positively-not-paid and refuse a real subscriber. An earlier draft of this
  // block carried a named `cannotTell` const to make the third state visible;
  // it was removed because an unused binding is dormant code, and the
  // distinction lives here instead, where the decision is actually made.
  if (knownNotPaid && lic.trial_ends_at && new Date(lic.trial_ends_at).getTime() < Date.now()) {
    throw storeError('TRIAL_EXPIRED', 'Your trial has ended. Please subscribe to continue.');
  }

  return lic;
}

function supabaseHeaders() {
  return {
    apikey: process.env.SUPABASE_SERVICE_ROLE_KEY,
    Authorization: 'Bearer ' + process.env.SUPABASE_SERVICE_ROLE_KEY,
    'Content-Type': 'application/json'
  };
}

function restUrl(path) {
  const SUPABASE_URL = process.env.SUPABASE_URL;
  if (!SUPABASE_URL || !process.env.SUPABASE_SERVICE_ROLE_KEY) {
    throw storeError('CONFIG', 'SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in environment variables');
  }
  return SUPABASE_URL + '/rest/v1/' + path;
}

const enc = encodeURIComponent;
const nowISO = () => new Date().toISOString();

// Flatten a stored data jsonb blob back into a flat object, with any
// promoted columns (shop_id, created_at) merged on top — same shape sd-data.js
// returns to the StoneDesk client, so agent tool output looks the same.
function flat(data, extra) {
  return Object.assign({}, data || {}, extra || {});
}

async function readProfile(lic) {
  const r = await fetch(restUrl(
    'business_profiles?license_hash=eq.' + enc(lic.license_hash) +
    '&app_id=eq.stonedesk&select=data,shop_id&limit=1'), { headers: supabaseHeaders() });
  const rows = await r.json();
  if (!r.ok) throw storeError('UPSTREAM', 'Profile lookup failed');
  const row = Array.isArray(rows) && rows[0];
  return row ? flat(row.data, { shop_id: row.shop_id }) : null;
}

async function readSlabs(lic) {
  const r = await fetch(restUrl(
    'sd_slabs?license_hash=eq.' + enc(lic.license_hash) + '&select=data'), { headers: supabaseHeaders() });
  const rows = await r.json();
  if (!r.ok) throw storeError('UPSTREAM', 'Slab lookup failed');
  return (rows || []).map((x) => x.data);
}

async function writeSlab(lic, slab) {
  if (!slab || slab.id === undefined || slab.id === null || slab.id === '') {
    throw storeError('BAD_INPUT', 'slab.id is required');
  }
  const payloadBytes = Buffer.byteLength(JSON.stringify(slab), 'utf8');
  if (payloadBytes > MAX_PAYLOAD_BYTES) {
    throw storeError('PAYLOAD_TOO_LARGE', 'Slab payload is ' + payloadBytes + ' bytes; the limit is ' + MAX_PAYLOAD_BYTES + ' (64KB)');
  }
  const r = await fetch(restUrl('sd_slabs?on_conflict=license_hash,slab_id'), {
    method: 'POST',
    headers: Object.assign({}, supabaseHeaders(), { Prefer: 'resolution=merge-duplicates,return=representation' }),
    body: JSON.stringify({
      license_hash: lic.license_hash,
      app_id: 'stonedesk',
      slab_id: String(slab.id),
      data: slab,
      updated_at: nowISO()
    })
  });
  const rows = await r.json();
  if (!r.ok) throw storeError('UPSTREAM', 'Slab write failed');
  return (Array.isArray(rows) && rows[0]) ? rows[0].data : slab;
}

async function readMemories(lic) {
  const r = await fetch(restUrl(
    'ai_memories?license_hash=eq.' + enc(lic.license_hash) +
    '&select=data,created_at&order=created_at.desc&limit=10'), { headers: supabaseHeaders() });
  const rows = await r.json();
  if (!r.ok) throw storeError('UPSTREAM', 'Memory lookup failed');
  return (rows || []).map((x) => flat(x.data, { created_at: x.created_at }));
}

async function writeMemory(lic, memory) {
  const payload = memory || {};
  const payloadBytes = Buffer.byteLength(JSON.stringify(payload), 'utf8');
  if (payloadBytes > MAX_PAYLOAD_BYTES) {
    throw storeError('PAYLOAD_TOO_LARGE', 'Memory payload is ' + payloadBytes + ' bytes; the limit is ' + MAX_PAYLOAD_BYTES + ' (64KB)');
  }
  // Stamp shop_id from the profile so memories link the way the client expects.
  let shopId = null;
  try {
    const pr = await fetch(restUrl(
      'business_profiles?license_hash=eq.' + enc(lic.license_hash) +
      '&app_id=eq.stonedesk&select=shop_id&limit=1'), { headers: supabaseHeaders() });
    const prows = await pr.json();
    shopId = (Array.isArray(prows) && prows[0]) ? prows[0].shop_id : null;
  } catch (e) { /* non-fatal — memory still saves unlinked */ }

  const r = await fetch(restUrl('ai_memories'), {
    method: 'POST',
    headers: Object.assign({}, supabaseHeaders(), { Prefer: 'return=representation' }),
    body: JSON.stringify({ license_hash: lic.license_hash, app_id: 'stonedesk', shop_id: shopId, data: payload })
  });
  const rows = await r.json();
  if (!r.ok) throw storeError('UPSTREAM', 'Memory write failed');
  const row = Array.isArray(rows) && rows[0];
  return row ? flat(row.data, { created_at: row.created_at }) : payload;
}

module.exports = {
  validateAndGate,
  readProfile,
  readSlabs,
  writeSlab,
  readMemories,
  writeMemory
};
