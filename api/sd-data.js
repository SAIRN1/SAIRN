// api/sd-data.js
// ---------------------------------------------------------------------------
// StoneDesk (and other license-gated SAIRN apps) data-sync endpoint.
//
// WHY THIS EXISTS: the browser anon/publishable key can never reach these
// tables — RLS locks anon out entirely (confirmed 401 on every table). The
// StoneDesk client used to call sb.from('business_profiles' | 'ai_memories'
// | 'employees' | 'slabs') directly and every call silently failed. All of
// that now routes here, where the service-role key does the work, scoped to
// the caller's validated license.
//
// NOT part of api/agent/* — that namespace is the on-prem firewall-traversal
// connector, a different subsystem. This is app data sync (decision D3).
//
// AUTH MODEL: Authorization: Bearer <license_key>. The license_key is a bearer
// secret — holding it grants access to that shop's data, the same trust model
// as the agent token in api/agent/*. Fine for the license-gated model; add
// rate-limiting + key rotation before wide multi-tenant exposure. The key is
// taken from the Authorization header (never the body or URL) so it never
// lands in request logs. The StoneDesk-owned tables are keyed by
// license_hash = sha256(license_key), so the raw key never appears in their
// rows or in the server→Supabase query URLs either.
//
// SIZE CAP: writes whose payload exceeds 64KB are rejected with 413 before any
// DB call (a matching CHECK constraint in the schema is the backstop).
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
// ---------------------------------------------------------------------------

const { validateLicenseKey } = require('./_lib/license');

const RESOURCES = { profile: true, memory: true, employees: true, slabs: true };
const MAX_PAYLOAD_BYTES = 64 * 1024; // 65536

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: { message: 'Method not allowed — POST only' } });
    return;
  }

  // ── license_key from Authorization: Bearer (kept out of body/URL/logs) ──
  const authz = req.headers['authorization'] || '';
  const licenseKey = authz.startsWith('Bearer ') ? authz.slice(7).trim() : null;
  if (!licenseKey) {
    res.status(401).json({ error: { code: 'NO_LICENSE', message: 'Missing bearer license key' } });
    return;
  }

  // ── parse + validate the request envelope ──
  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) {
      res.status(400).json({ error: { message: 'Invalid JSON body' } });
      return;
    }
  }
  const action = body && body.action;
  const resource = body && body.resource;
  const payload = (body && body.payload) || {};
  if (action !== 'read' && action !== 'write') {
    res.status(400).json({ error: { message: "action must be 'read' or 'write'" } });
    return;
  }
  if (!RESOURCES[resource]) {
    res.status(400).json({ error: { message: 'resource must be one of: profile, memory, employees, slabs' } });
    return;
  }

  // ── 64KB payload cap on writes (reject early, before any DB call) ──
  if (action === 'write') {
    const payloadBytes = Buffer.byteLength(JSON.stringify(payload), 'utf8');
    if (payloadBytes > MAX_PAYLOAD_BYTES) {
      res.status(413).json({
        error: {
          code: 'PAYLOAD_TOO_LARGE',
          message: 'Payload is ' + payloadBytes + ' bytes; the limit is ' + MAX_PAYLOAD_BYTES + ' (64KB)'
        }
      });
      return;
    }
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) {
    console.error('SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in environment variables');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }

  // ── LICENSE VALIDATION (shared with Pattern 13's entitlement gate — D4) ──
  let lic;
  try {
    lic = await validateLicenseKey(licenseKey);
  } catch (err) {
    if (err.code === 'CONFIG') {
      console.error('sd-data config error:', err.message);
      res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
      return;
    }
    console.error('sd-data license validation error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
    return;
  }
  if (!lic.valid) {
    res.status(401).json({ error: { code: 'INVALID_LICENSE', message: 'Unknown license key' } });
    return;
  }
  if (!lic.active) {
    res.status(403).json({ error: { code: 'LICENSE_INACTIVE', message: 'This license is not active' } });
    return;
  }

  // ── ◆ PATTERN 13 ENTITLEMENT GATE ◆ ─────────────────────────────────────
  // A paid license (has a Stripe subscription) bypasses the trial entirely.
  // Otherwise, once the trial window has passed, refuse with 402 TRIAL_EXPIRED.
  // A null/absent trial_ends_at (e.g. before the migration, or intentionally
  // unset) is treated as "not expired" and allowed through. Stripe wiring that
  // sets stripe_subscription_id is a separate task; this is enforcement only.
  const isPaid = !!lic.stripe_subscription_id;
  if (!isPaid && lic.trial_ends_at && new Date(lic.trial_ends_at).getTime() < Date.now()) {
    res.status(402).json({ error: { code: 'TRIAL_EXPIRED', message: 'Your trial has ended. Please subscribe to continue.' } });
    return;
  }

  // license_hash is what the StoneDesk-owned tables are keyed by (never the raw key).
  const licHash = lic.license_hash;

  const headers = {
    apikey: SERVICE_KEY,
    Authorization: 'Bearer ' + SERVICE_KEY,
    'Content-Type': 'application/json'
  };
  const rest = (path) => SUPABASE_URL + '/rest/v1/' + path;
  const enc = encodeURIComponent;
  const nowISO = () => new Date().toISOString();

  try {
    // ── PROFILE ──────────────────────────────────────────────────────────
    if (resource === 'profile' && action === 'read') {
      const r = await fetch(rest(
        'business_profiles?license_hash=eq.' + enc(licHash) +
        '&app_id=eq.stonedesk&select=data,shop_id&limit=1'), { headers });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const row = Array.isArray(rows) && rows[0];
      res.status(200).json({ ok: true, data: row ? flat(row.data, { shop_id: row.shop_id }) : null });
      return;
    }
    if (resource === 'profile' && action === 'write') {
      const r = await fetch(rest('business_profiles?on_conflict=license_hash,app_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'stonedesk', data: payload, updated_at: nowISO() })
      });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const row = Array.isArray(rows) && rows[0];
      res.status(200).json({ ok: true, data: row ? flat(row.data, { shop_id: row.shop_id }) : payload });
      return;
    }

    // ── MEMORY ───────────────────────────────────────────────────────────
    if (resource === 'memory' && action === 'read') {
      const r = await fetch(rest(
        'ai_memories?license_hash=eq.' + enc(licHash) +
        '&select=data,created_at&order=created_at.desc&limit=10'), { headers });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => flat(x.data, { created_at: x.created_at })) });
      return;
    }
    if (resource === 'memory' && action === 'write') {
      // Stamp shop_id from the profile so memories link the way the client expects.
      let shopId = null;
      try {
        const pr = await fetch(rest(
          'business_profiles?license_hash=eq.' + enc(licHash) +
          '&app_id=eq.stonedesk&select=shop_id&limit=1'), { headers });
        const prows = await pr.json();
        shopId = (Array.isArray(prows) && prows[0]) ? prows[0].shop_id : null;
      } catch (e) { /* non-fatal — memory still saves unlinked */ }
      const r = await fetch(rest('ai_memories'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'stonedesk', shop_id: shopId, data: payload })
      });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const row = Array.isArray(rows) && rows[0];
      res.status(200).json({ ok: true, data: row ? flat(row.data, { created_at: row.created_at }) : payload });
      return;
    }

    // ── EMPLOYEES (read-only from StoneDesk; scoped by customer_email — D1b) ─
    if (resource === 'employees' && action === 'read') {
      // No tenant identity -> nothing this shop is allowed to see. Honest empty.
      if (!lic.customer_email) { res.status(200).json({ ok: true, data: [] }); return; }
      const r = await fetch(rest(
        'employees?customer_email=eq.' + enc(lic.customer_email) +
        '&source_app=eq.sairnbiz&status=eq.Active&select=data'), { headers });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data) });
      return;
    }
    if (resource === 'employees' && action === 'write') {
      res.status(405).json({ error: { code: 'READ_ONLY', message: 'employees is managed by SAIRNbiz; StoneDesk may only read it' } });
      return;
    }

    // ── SLABS (sd_slabs — D2) ────────────────────────────────────────────
    if (resource === 'slabs' && action === 'read') {
      const r = await fetch(rest('sd_slabs?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data) });
      return;
    }
    if (resource === 'slabs' && action === 'write') {
      if (!payload || payload.id === undefined || payload.id === null || payload.id === '') {
        res.status(400).json({ error: { message: 'slab payload.id is required' } });
        return;
      }
      const r = await fetch(rest('sd_slabs?on_conflict=license_hash,slab_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'stonedesk',
          slab_id: String(payload.id), data: payload, updated_at: nowISO()
        })
      });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }

    // Should be unreachable given the guards above.
    res.status(400).json({ error: { message: 'Unsupported action/resource combination' } });
  } catch (err) {
    console.error('api/sd-data error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
  }
};

// Flatten a stored data jsonb blob back into the flat object the client expects,
// with any promoted columns (shop_id, created_at) merged on top.
function flat(data, extra) {
  return Object.assign({}, data || {}, extra || {});
}

function upstream(res, detail) {
  console.error('sd-data upstream error:', detail);
  res.status(502).json({ error: { message: 'Data store error — try again' } });
}
