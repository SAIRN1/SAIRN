// api/sen-portal.js
// ---------------------------------------------------------------------------
// SAIRNsenior family/client portal links.
//
// Client/family is a DIFFERENT actor class from an employee, per explicit
// instruction -- not a PIN account, not an extension of
// sairnsenior_employee_auth (api/sen-auth.js). A portal link is a unique,
// revocable, scoped-to-exactly-one-client bearer token: possessing the
// token IS the credential, same model as a calendar-share link. There is
// no login step, no PIN, no session for the family/client side.
//
// SECURITY MODEL (see sql/sairnsenior_portal_links_schema.sql's header for
// the full statement): link_token is 256-bit crypto-random, looked up
// directly on every 'view' call, and the client_id it resolves to is NEVER
// supplied by the caller -- there is no client_id parameter on 'view' at
// all, only the token. A family member cannot access a different client's
// data by guessing or editing a parameter, because there isn't one.
//
// Actions:
//
//   create  { client_id, label }              (employee session required)
//     Generates a new link, returns { ok, token, url }. Permission
//     mirrors api/sd-data.js's sen_clients write gate: management/
//     coordinator/scheduler (broad tier) may create a link for any
//     client; a caregiver only for a client assigned to them.
//
//   revoke  { link_id }                        (employee session required)
//     Sets active=false, revoked_at=now(). Same permission tier as create.
//
//   list    { client_id? }                     (employee session required)
//     Lists links (label, created_at, last_accessed_at, active) for one
//     client, or -- broad tier only -- every link on the license if
//     client_id is omitted. Never returns link_token itself once created
//     -- if staff needs the URL again, revoke and create a new one; this
//     matches the platform's existing "never re-display a secret" rule
//     (PIN hashes are never returned either).
//
//   view    { token }                          (NO employee session, NO
//                                                license key -- the token
//                                                alone is the credential)
//     Returns read-only, deliberately minimal data for exactly the one
//     client the token resolves to: client name, and upcoming/recent
//     visits (date, time window, status only -- no caregiver identity,
//     no diagnosis, no authorized hours, no notes, no care plan tasks, no
//     billing data) -- a real minimum-necessary scope for an external,
//     unauthenticated party, narrower than any employee role gets.
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SD_AUTH_SECRET
// (the last one only for verifying employee sessions on create/revoke/list
// -- 'view' needs none of the three auth env vars beyond Supabase itself).
// ---------------------------------------------------------------------------

const crypto = require('crypto');
const { validateLicenseKey } = require('./_lib/license');
const { verifySessionToken, tokenFromRequest } = require('./_lib/auth');

const ACTIONS = ['create', 'revoke', 'list', 'view'];
const MANAGEMENT_ROLES = { owner: true, billing: true };
const BROAD_ROLES = { owner: true, billing: true, coordinator: true, scheduler: true };

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: { message: 'Method not allowed — POST only' } });
    return;
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) {
      res.status(400).json({ error: { message: 'Invalid JSON body' } });
      return;
    }
  }
  body = body || {};
  const action = body.action;
  if (ACTIONS.indexOf(action) === -1) {
    res.status(400).json({ error: { message: 'action must be one of: ' + ACTIONS.join(', ') } });
    return;
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) {
    console.error('sen-portal: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }
  const headers = { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json' };
  const rest = (path) => SUPABASE_URL + '/rest/v1/' + path;
  const enc = encodeURIComponent;

  // ── 'view' is the one action with NO employee auth at all -- the token
  // is the entire credential. Handled first and separately, before any
  // license-key validation, since a family member has no license key.
  if (action === 'view') {
    const token = String(body.token || '').trim();
    if (!token || token.length < 20) { res.status(400).json({ error: { code: 'INVALID_LINK', message: 'This link is invalid.' } }); return; }
    try {
      const linkR = await fetch(rest('sen_portal_links?link_token=eq.' + enc(token) + '&active=eq.true&select=id,license_hash,client_id'), { headers });
      if (linkR.status === 404 || linkR.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Portal links are not set up yet.' } }); return; }
      const linkRows = await linkR.json();
      if (!linkR.ok) { res.status(502).json({ error: { message: 'Could not verify this link — try again.' } }); return; }
      const link = Array.isArray(linkRows) && linkRows[0];
      if (!link) { res.status(404).json({ error: { code: 'INVALID_LINK', message: 'This link is invalid or has been revoked.' } }); return; }

      // Mark accessed -- non-fatal if it fails, the read below still proceeds.
      fetch(rest('sen_portal_links?id=eq.' + enc(link.id)), {
        method: 'PATCH', headers, body: JSON.stringify({ last_accessed_at: new Date().toISOString() })
      }).catch(() => {});

      // The client_id came ONLY from the token lookup above -- never from
      // the request body. Fetch only the field actually used (name) --
      // no assigned_employee_id, no other client fields selected at all.
      const clientR = await fetch(rest('sen_clients?license_hash=eq.' + enc(link.license_hash) + '&client_id=eq.' + enc(link.client_id) + '&select=data'), { headers });
      const clientRows = await clientR.json();
      const clientRow = clientR.ok && Array.isArray(clientRows) && clientRows[0];
      const clientName = clientRow && clientRow.data && clientRow.data.name ? clientRow.data.name : 'this client';

      // Visits for this client, minimal fields only (date/start/end/status
      // in the map below) -- no caregiver identity is selected or returned
      // anywhere in this response.
      const visitsR = await fetch(rest('sen_visits?license_hash=eq.' + enc(link.license_hash) + '&select=data'), { headers });
      const visitsRows = visitsR.ok ? await visitsR.json() : [];
      const clientVisits = (Array.isArray(visitsRows) ? visitsRows : [])
        .filter((v) => v.data && v.data.client_id === link.client_id)
        .map((v) => ({
          scheduled_date: v.data.scheduled_date || null,
          scheduled_start: v.data.scheduled_start || null,
          scheduled_end: v.data.scheduled_end || null,
          status: v.data.status || 'scheduled'
        }))
        .sort((a, b) => String(b.scheduled_date || '').localeCompare(String(a.scheduled_date || '')))
        .slice(0, 20);

      res.status(200).json({ ok: true, client_name: clientName, visits: clientVisits });
      return;
    } catch (err) {
      console.error('api/sen-portal view error:', err);
      res.status(502).json({ error: { message: 'Upstream error — try again' } });
      return;
    }
  }

  // ── Every other action requires the normal employee auth: Bearer
  // license key + a real session token, same as every other endpoint.
  const authz = req.headers['authorization'] || '';
  const licenseKey = authz.startsWith('Bearer ') ? authz.slice(7).trim() : null;
  if (!licenseKey) { res.status(401).json({ error: { code: 'NO_LICENSE', message: 'Missing bearer license key' } }); return; }

  let lic;
  try {
    lic = await validateLicenseKey(licenseKey);
  } catch (err) {
    if (err.code === 'CONFIG') { res.status(500).json({ error: { message: 'Server configuration error — contact support' } }); return; }
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
    return;
  }
  if (!lic.valid) { res.status(401).json({ error: { code: 'INVALID_LICENSE', message: 'Unknown license key' } }); return; }
  if (!lic.active) { res.status(403).json({ error: { code: 'LICENSE_INACTIVE', message: 'This license is not active' } }); return; }

  const licHash = lic.license_hash;
  const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnsenior');
  if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }

  async function loadClientAssignee(clientId) {
    const r = await fetch(rest('sen_clients?license_hash=eq.' + enc(licHash) + '&client_id=eq.' + enc(clientId) + '&select=assigned_employee_id'), { headers });
    if (r.status === 404 || r.status === 400) { const e = new Error('not provisioned'); e.notProvisioned = true; throw e; }
    const rows = await r.json();
    if (!r.ok) { const e = new Error('lookup failed'); e.detail = rows; throw e; }
    return Array.isArray(rows) && rows[0];
  }
  function canManageClient(clientRow) {
    if (BROAD_ROLES[session.role]) return true;
    return !!(clientRow && clientRow.assigned_employee_id === session.employee_id);
  }

  try {
    if (action === 'create') {
      const clientId = String(body.client_id || '').trim();
      if (!clientId) { res.status(400).json({ error: { message: 'client_id is required' } }); return; }
      const clientRow = await loadClientAssignee(clientId);
      if (!canManageClient(clientRow)) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'You can only create a portal link for a client assigned to you' } });
        return;
      }
      const token = crypto.randomBytes(32).toString('hex');
      const label = body.label ? String(body.label).slice(0, 128) : null;
      const r = await fetch(rest('sen_portal_links'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairnsenior', link_token: token, client_id: clientId,
          label, created_by_employee_id: session.employee_id, active: true
        })
      });
      if (r.status === 404 || r.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Portal links are not set up yet — run sql/sairnsenior_portal_links_schema.sql in Supabase first.' } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) { res.status(502).json({ error: { message: 'Could not create link — try again' } }); return; }
      const row = Array.isArray(rows) && rows[0];
      res.status(200).json({ ok: true, id: row && row.id, token, label });
      return;
    }

    if (action === 'revoke') {
      const linkId = String(body.link_id || '').trim();
      if (!linkId) { res.status(400).json({ error: { message: 'link_id is required' } }); return; }
      const linkR = await fetch(rest('sen_portal_links?id=eq.' + enc(linkId) + '&license_hash=eq.' + enc(licHash) + '&select=client_id'), { headers });
      const linkRows = await linkR.json();
      const linkRow = linkR.ok && Array.isArray(linkRows) && linkRows[0];
      if (!linkRow) { res.status(404).json({ error: { message: 'Link not found' } }); return; }
      const clientRow = await loadClientAssignee(linkRow.client_id);
      if (!canManageClient(clientRow)) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'You can only revoke a portal link for a client assigned to you' } });
        return;
      }
      const r = await fetch(rest('sen_portal_links?id=eq.' + enc(linkId)), {
        method: 'PATCH', headers, body: JSON.stringify({ active: false, revoked_at: new Date().toISOString() })
      });
      if (!r.ok) { res.status(502).json({ error: { message: 'Could not revoke link — try again' } }); return; }
      res.status(200).json({ ok: true });
      return;
    }

    if (action === 'list') {
      const clientId = body.client_id ? String(body.client_id).trim() : null;
      let query = 'sen_portal_links?license_hash=eq.' + enc(licHash) + '&select=id,client_id,label,active,created_at,last_accessed_at,revoked_at';
      if (clientId) {
        const clientRow = await loadClientAssignee(clientId);
        if (!canManageClient(clientRow)) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'You can only view portal links for a client assigned to you' } });
          return;
        }
        query += '&client_id=eq.' + enc(clientId);
      } else if (!BROAD_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Specify a client_id, or ask management for the agency-wide list' } });
        return;
      }
      const r = await fetch(rest(query), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, links: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) { res.status(502).json({ error: { message: 'Could not load links — try again' } }); return; }
      res.status(200).json({ ok: true, links: rows || [], provisioned: true });
      return;
    }
  } catch (err) {
    if (err && err.notProvisioned) {
      res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Client tracking is not set up yet — run sql/sairnsenior_clients_schema.sql in Supabase first.' } });
      return;
    }
    console.error('api/sen-portal error:', err);
    res.status(502).json({ error: { message: 'Upstream error — try again' } });
    return;
  }
};
