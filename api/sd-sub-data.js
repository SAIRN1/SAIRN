// api/sd-sub-data.js
// ---------------------------------------------------------------------------
// Subcontractor Portal (Phase 1) — roster, job assignment, and pay-tracking
// data endpoint. Separate from api/sd-data.js on purpose: this file's 'jobs'
// read action has to run in TWO different trust modes (office employee vs.
// the sub themselves) with different data returned, which is a different
// shape of problem than sd-data.js's single-trust-level resources, and
// keeping it physically separate makes the sub-facing filtering easier to
// verify by inspection.
//
// AUTH MODEL: every action requires a valid license key (Authorization:
// Bearer, same as every other StoneDesk data endpoint). Beyond that:
//   - 'roster' (read/write) and 'jobs' write: require a verified EMPLOYEE
//     session token (X-SD-Auth, app:'stonedesk'). Roster read allows any
//     employee role; roster/jobs write requires owner or admin — subs carry
//     pay-rate data, the same sensitivity class that got 'employees' its
//     first per-role gate in api/sd-data.js, applied here from the start
//     rather than waiting for a future finding to catch it.
//   - 'jobs' read: accepts EITHER an employee token (returns jobs for the
//     shop, optionally filtered to one sub_id from the request payload) OR
//     a SUB token (X-SD-Auth, app:'stonedesk_sub') — for a sub caller, the
//     sub_id filter is taken ONLY from the verified token's own identity
//     (verifySessionToken's returned `employee_id` field, which is the
//     shared token format's generic subject-id claim — reused as-is per
//     api/_lib/auth.js's "single source of truth, do not fork" header,
//     not a naming mistake), NEVER from the request body. This is the one
//     piece of logic in this whole feature that actually enforces "a sub
//     sees only their own job(s)" — everything else (the separate portal
//     UI, the separate token app namespace) is defense in depth on top of
//     this, not a substitute for it.
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SD_AUTH_SECRET
// ---------------------------------------------------------------------------

const { validateLicenseKey } = require('./_lib/license');
const { verifySessionToken, tokenFromRequest } = require('./_lib/auth');

const RESOURCES = { roster: true, jobs: true };
const WRITE_ALLOWED_ROLES = { owner: true, admin: true };
// Per-job photo/JSON cap — see sql/sd_sub_portal_schema.sql's size-cap note
// for why this is the ONLY enforced limit (no matching DB-level CHECK to
// drift out of sync with, unlike sd_slabs' earlier incident). 1.5MB is
// enough for a few real reference photos (site conditions, access notes)
// at reasonable compression — genuinely larger than a slab thumbnail needs
// to be, since a sub is using these to do the actual job, not just tell
// slabs apart in a picker.
const SUB_JOB_PAYLOAD_MAX_BYTES = 1.5 * 1024 * 1024;

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: { message: 'Method not allowed — POST only' } });
    return;
  }

  const authz = req.headers['authorization'] || '';
  const licenseKey = authz.startsWith('Bearer ') ? authz.slice(7).trim() : null;
  if (!licenseKey) {
    res.status(401).json({ error: { code: 'NO_LICENSE', message: 'Missing bearer license key' } });
    return;
  }

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
    res.status(400).json({ error: { message: 'resource must be one of: roster, jobs' } });
    return;
  }

  if (action === 'write') {
    const payloadBytes = Buffer.byteLength(JSON.stringify(payload), 'utf8');
    if (payloadBytes > SUB_JOB_PAYLOAD_MAX_BYTES) {
      res.status(413).json({
        error: { code: 'PAYLOAD_TOO_LARGE', message: 'Payload is ' + payloadBytes + ' bytes; the limit is ' + SUB_JOB_PAYLOAD_MAX_BYTES + ' bytes' }
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

  let lic;
  try {
    lic = await validateLicenseKey(licenseKey);
  } catch (err) {
    if (err.code === 'CONFIG') {
      res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
      return;
    }
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
    return;
  }
  if (!lic.valid) { res.status(401).json({ error: { code: 'INVALID_LICENSE', message: 'Unknown license key' } }); return; }
  if (!lic.active) { res.status(403).json({ error: { code: 'LICENSE_INACTIVE', message: 'This license is not active' } }); return; }

  const licHash = lic.license_hash;
  const sbHeaders = { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json' };
  const rest = (path) => SUPABASE_URL + '/rest/v1/' + path;
  const enc = encodeURIComponent;
  const nowISO = () => new Date().toISOString();

  const callerToken = tokenFromRequest(req);
  const employeeCaller = verifySessionToken(callerToken, licHash, 'stonedesk');
  const subCaller = verifySessionToken(callerToken, licHash, 'stonedesk_sub');

  try {
    // ── ROSTER ───────────────────────────────────────────────────────────
    if (resource === 'roster' && action === 'read') {
      if (!employeeCaller) { res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Sign in as an employee to view the subcontractor roster' } }); return; }
      const r = await fetch(rest('sd_subs?license_hash=eq.' + enc(licHash) + '&select=sub_id,name,phone,email,trade,active,created_at'), { headers: sbHeaders });
      const rows = await r.json();
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: rows || [] });
      return;
    }
    if (resource === 'roster' && action === 'write') {
      if (!employeeCaller || !WRITE_ALLOWED_ROLES[employeeCaller.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only Owner or Manager can manage the subcontractor roster' } });
        return;
      }
      const sub_id = String(payload.sub_id || '').trim();
      const name = String(payload.name || '').trim();
      if (!sub_id || !name) { res.status(400).json({ error: { message: 'sub_id and name are required' } }); return; }
      const r = await fetch(rest('sd_subs?on_conflict=license_hash,sub_id'), {
        method: 'POST',
        headers: Object.assign({}, sbHeaders, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, sub_id, name,
          phone: payload.phone || '', email: payload.email || '', trade: payload.trade || '',
          active: payload.active !== false, updated_at: nowISO()
        })
      });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) || payload });
      return;
    }

    // ── JOBS ─────────────────────────────────────────────────────────────
    if (resource === 'jobs' && action === 'read') {
      if (subCaller) {
        // Sub caller: sub_id comes ONLY from the verified token, never the
        // request body — this is the actual enforcement point for "a sub
        // sees only their own job(s)".
        const r = await fetch(rest('sd_sub_jobs?license_hash=eq.' + enc(licHash) + '&sub_id=eq.' + enc(subCaller.employee_id) + '&select=id,data,created_at,updated_at&order=created_at.desc'), { headers: sbHeaders });
        const rows = await r.json();
        if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
        if (!r.ok) return upstream(res, rows);
        const out = (rows || []).map((row) => Object.assign({ id: row.id }, row.data));
        res.status(200).json({ ok: true, data: out });
        return;
      }
      if (employeeCaller) {
        const subIdFilter = payload && payload.sub_id ? '&sub_id=eq.' + enc(String(payload.sub_id)) : '';
        const r = await fetch(rest('sd_sub_jobs?license_hash=eq.' + enc(licHash) + subIdFilter + '&select=id,sub_id,data,created_at,updated_at&order=created_at.desc'), { headers: sbHeaders });
        const rows = await r.json();
        if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
        if (!r.ok) return upstream(res, rows);
        const out = (rows || []).map((row) => Object.assign({ id: row.id, sub_id: row.sub_id }, row.data));
        res.status(200).json({ ok: true, data: out });
        return;
      }
      res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Sign in to view job assignments' } });
      return;
    }
    if (resource === 'jobs' && action === 'write') {
      if (!employeeCaller || !WRITE_ALLOWED_ROLES[employeeCaller.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only Owner or Manager can assign jobs or update pay status' } });
        return;
      }
      const sub_id = String(payload.sub_id || '').trim();
      if (!sub_id) { res.status(400).json({ error: { message: 'sub_id is required' } }); return; }
      const jobData = Object.assign({}, payload);
      delete jobData.sub_id; // sub_id is its own column, not duplicated inside `data`
      delete jobData.id;     // id is server-assigned/DB-assigned, never client-supplied
      jobData.updatedAt = nowISO();

      if (payload.id) {
        // Update an existing assignment (e.g. office marking it paid) —
        // scoped by license_hash AND id so one shop can never touch another's row.
        const r = await fetch(rest('sd_sub_jobs?license_hash=eq.' + enc(licHash) + '&id=eq.' + enc(String(payload.id))), {
          method: 'PATCH',
          headers: Object.assign({}, sbHeaders, { Prefer: 'return=representation' }),
          body: JSON.stringify({ sub_id, data: jobData, updated_at: nowISO() })
        });
        const rows = await r.json();
        if (!r.ok) return upstream(res, rows);
        const row = Array.isArray(rows) && rows[0];
        res.status(200).json({ ok: true, data: row ? Object.assign({ id: row.id, sub_id: row.sub_id }, row.data) : payload });
        return;
      }
      // New assignment.
      jobData.createdAt = jobData.createdAt || nowISO();
      const r = await fetch(rest('sd_sub_jobs'), {
        method: 'POST',
        headers: Object.assign({}, sbHeaders, { Prefer: 'return=representation' }),
        body: JSON.stringify({ license_hash: licHash, sub_id, data: jobData })
      });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const row = Array.isArray(rows) && rows[0];
      res.status(200).json({ ok: true, data: row ? Object.assign({ id: row.id, sub_id: row.sub_id }, row.data) : payload });
      return;
    }

    res.status(400).json({ error: { message: 'Unsupported action/resource combination' } });
  } catch (err) {
    console.error('api/sd-sub-data error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
  }
};

function upstream(res, detail) {
  console.error('sd-sub-data upstream error:', detail);
  res.status(502).json({ error: { message: 'Data store error — try again' } });
}
