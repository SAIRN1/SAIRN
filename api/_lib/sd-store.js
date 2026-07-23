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

  const isPaid = !!lic.stripe_subscription_id;
  if (!isPaid && lic.trial_ends_at && new Date(lic.trial_ends_at).getTime() < Date.now()) {
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
