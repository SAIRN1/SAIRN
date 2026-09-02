// api/stonedesk-track.js
// ---------------------------------------------------------------------------
// StoneDesk order-tracking links. The narrow, in-scope slice of competitive-gap
// audit GAP 8: a real customer with an order in progress can see where it is.
//
// ── WHY A TOKEN AND NOT A CUSTOMER PASSWORD ──
// A customer is a DIFFERENT ACTOR CLASS from an employee. Every credential on
// this platform lives in a *_employee_auth table with a PIN, a lockout and a
// provisioning role, and a customer has none of those. Building a customer
// password store would add a second credential database with no recovery path
// and no provisioning model, to solve a problem this platform already solved
// once: sql/sairnsenior_portal_links_schema.sql. This is that model, applied.
//
// The token IS the credential, like a calendar-share link -- 256-bit
// crypto-random, revocable, scoped to exactly one customer record. THE
// customer_id IS NEVER SUPPLIED BY THE CALLER on the public action: there is no
// customer_id parameter on 'view' at all, only the token, so nobody can reach
// another customer's job by editing one.
//
// ── WHAT A HOLDER OF THE TOKEN CAN SEE ──
// Their own name, their project description, and the stage it is at. NOT the
// quote amount, NOT internal notes, NOT the slab or its cost, NOT the referral
// source or the satisfaction rating. That is a real minimum-necessary scope,
// the same one api/sen-portal.js's 'view' applies, and the reason is the same:
// a link that can be forwarded should carry the least that still answers the
// question it exists to answer.
//
// Actions:
//   create { customer_id, label }   employee session, management only
//   revoke { link_id }              employee session, management only
//   list   { }                      employee session, management only --
//                                   never returns link_token once created
//   view   { token }                NO session, NO license key
// ---------------------------------------------------------------------------

const crypto = require('crypto');
const { verifySessionToken, tokenFromRequest } = require('./_lib/auth');
const { validateLicenseKey } = require('./_lib/license');

const MANAGEMENT = { owner: true, admin: true };

// The customer-facing wording for each stage. Kept here rather than shipped
// from the client so a customer and the shop cannot be shown two different
// vocabularies for the same record. An unknown stage says so rather than
// guessing at a friendly name for something this file has never seen.
const STAGE_TEXT = {
  quoted: 'Quote sent - waiting on your approval',
  approved: 'Approved - scheduling your template',
  templated: 'Templated - your measurements are taken',
  fabricating: 'In fabrication',
  scheduled: 'Scheduled for installation',
  complete: 'Completed'
};

function supabaseHeaders(extra) {
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  return Object.assign({
    apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json'
  }, extra || {});
}
function rest(path) { return process.env.SUPABASE_URL + '/rest/v1/' + path; }
function enc(v) { return encodeURIComponent(String(v)); }
function nowISO() { return new Date().toISOString(); }

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-SD-Auth');
  if (req.method === 'OPTIONS') { res.status(204).end(); return; }
  if (req.method !== 'POST') { res.status(405).json({ error: { message: 'POST only' } }); return; }
  if (!process.env.SUPABASE_URL || !process.env.SUPABASE_SERVICE_ROLE_KEY) {
    res.status(500).json({ error: { message: 'Server configuration error' } }); return;
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) { res.status(400).json({ error: { message: 'Invalid JSON body' } }); return; }
  }
  body = body || {};
  const action = body.action;
  const headers = supabaseHeaders();

  try {
    // ── THE PUBLIC ACTION. No session, no license key, no customer_id. ──
    if (action === 'view') {
      const token = String(body.token || '');
      // Length-checked before it reaches the database. A token is a fixed
      // shape; anything else is not a near miss, it is not a token.
      if (!/^[a-f0-9]{64}$/.test(token)) {
        res.status(404).json({ error: { code: 'NOT_FOUND', message: 'This tracking link is not valid. Ask the shop for a new one.' } });
        return;
      }
      const lr = await fetch(rest('sd_order_links?link_token=eq.' + enc(token) +
        '&select=id,license_hash,job_id,label,active&limit=1'), { headers });
      if (lr.status === 404 || lr.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Order tracking is not set up yet - please call the shop.' } });
        return;
      }
      const lrows = await lr.json();
      const link = (Array.isArray(lrows) && lrows[0]) || null;
      // A revoked link and a link that never existed answer the SAME way, so a
      // revoked link cannot be distinguished from a guess.
      if (!link || link.active !== true) {
        res.status(404).json({ error: { code: 'NOT_FOUND', message: 'This tracking link is not valid. Ask the shop for a new one.' } });
        return;
      }
      const cr = await fetch(rest('sd_customers?license_hash=eq.' + enc(link.license_hash) +
        '&customer_id=eq.' + enc(link.job_id) + '&select=data&limit=1'), { headers });
      const crows = cr.ok ? await cr.json() : [];
      const cust = (Array.isArray(crows) && crows[0] && crows[0].data) || null;
      if (!cust) {
        res.status(404).json({ error: { code: 'NOT_FOUND', message: 'That job is no longer on file. Please call the shop.' } });
        return;
      }
      // Recorded before the response is built, and never treated as a reason to
      // fail the read: a failed access log must not deny a customer their status.
      fetch(rest('sd_order_links?id=eq.' + enc(link.id)), {
        method: 'PATCH', headers: Object.assign({}, headers, { Prefer: 'return=minimal' }),
        body: JSON.stringify({ last_accessed_at: nowISO() })
      }).catch(() => {});

      const stage = String(cust.status || '');
      // A shop's public profile supplies the name and phone, so the page can
      // tell a customer who to call. It is the same published row the catalog
      // uses -- nothing internal is read here.
      const sr = await fetch(rest('sd_public_shop?license_hash=eq.' + enc(link.license_hash) + '&select=data&limit=1'), { headers });
      const srows = sr.ok ? await sr.json() : [];
      const shop = (Array.isArray(srows) && srows[0] && srows[0].data) || {};

      res.status(200).json({
        ok: true,
        customer_name: String(cust.name || ''),
        project: String(cust.project || ''),
        material: String(cust.material || ''),
        stage: stage,
        // An unrecognised stage is reported as unrecognised. Inventing a
        // friendly label for a status this file has never seen would tell a
        // customer something nobody wrote.
        stage_text: STAGE_TEXT[stage] || '',
        stage_known: Object.prototype.hasOwnProperty.call(STAGE_TEXT, stage),
        shop: { name: String(shop.shop_name || ''), phone: String(shop.phone || '') }
      });
      return;
    }

    // ── EVERYTHING ELSE NEEDS A REAL EMPLOYEE SESSION ──
    const authz = req.headers['authorization'] || '';
    const licenseKey = authz.startsWith('Bearer ') ? authz.slice(7).trim() : null;
    if (!licenseKey) { res.status(401).json({ error: { code: 'NO_LICENSE', message: 'Missing bearer license key' } }); return; }
    let lic;
    try { lic = await validateLicenseKey(licenseKey); }
    catch (err) { res.status(502).json({ error: { message: 'Upstream connection error - try again' } }); return; }
    if (!lic.valid) { res.status(401).json({ error: { code: 'INVALID_LICENSE', message: 'Unknown license key' } }); return; }
    if (!lic.active) { res.status(403).json({ error: { code: 'LICENSE_INACTIVE', message: 'This license is not active' } }); return; }

    const session = verifySessionToken(tokenFromRequest(req), lic.license_hash, 'stonedesk');
    if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
    if (!MANAGEMENT[session.role]) {
      res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only an owner or admin can issue or revoke a tracking link' } });
      return;
    }
    const licHash = lic.license_hash;

    if (action === 'create') {
      const customerId = String(body.customer_id || '');
      if (!customerId) { res.status(400).json({ error: { message: 'customer_id is required' } }); return; }
      // The customer must exist on THIS license before a link is issued.
      // Issuing a link for a record that is not there would produce a URL that
      // 404s on first use, which a shop would reasonably read as the link being
      // broken rather than the job being absent.
      const cr = await fetch(rest('sd_customers?license_hash=eq.' + enc(licHash) +
        '&customer_id=eq.' + enc(customerId) + '&select=customer_id&limit=1'), { headers });
      if (cr.status === 404 || cr.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Order tracking is not set up yet - run sql/stonedesk_public_surface_schema.sql in Supabase first.' } });
        return;
      }
      const crows = await cr.json();
      if (!Array.isArray(crows) || !crows[0]) {
        res.status(404).json({ error: { code: 'NOT_FOUND', message: 'That customer is not on file, so a link would point at nothing' } });
        return;
      }
      const token = crypto.randomBytes(32).toString('hex');
      const linkId = 'OL-' + Date.now() + '-' + Math.floor(Math.random() * 1000);
      const w = await fetch(rest('sd_order_links'), {
        method: 'POST', headers: Object.assign({}, headers, { Prefer: 'return=minimal' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'stonedesk', link_id: linkId,
          link_token: token, job_id: customerId,
          label: String(body.label || '').slice(0, 200), active: true
        })
      });
      if (w.status === 404 || w.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Order tracking is not set up yet - run sql/stonedesk_public_surface_schema.sql in Supabase first.' } });
        return;
      }
      if (!w.ok) { res.status(502).json({ error: { message: 'Could not create the link' } }); return; }
      // The token is returned EXACTLY ONCE, here. 'list' never returns it
      // again -- the same never-re-display-a-secret rule the PIN hashes follow.
      res.status(200).json({ ok: true, link_id: linkId, token: token });
      return;
    }

    if (action === 'revoke') {
      const linkId = String(body.link_id || '');
      if (!linkId) { res.status(400).json({ error: { message: 'link_id is required' } }); return; }
      const w = await fetch(rest('sd_order_links?license_hash=eq.' + enc(licHash) + '&link_id=eq.' + enc(linkId)), {
        method: 'PATCH', headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
        body: JSON.stringify({ active: false, revoked_at: nowISO() })
      });
      const rows = await w.json();
      if (!w.ok) { res.status(502).json({ error: { message: 'Could not revoke the link' } }); return; }
      if (!Array.isArray(rows) || !rows.length) {
        res.status(404).json({ error: { code: 'NOT_FOUND', message: 'That link is not on this license' } });
        return;
      }
      res.status(200).json({ ok: true, link_id: linkId });
      return;
    }

    if (action === 'list') {
      const r = await fetch(rest('sd_order_links?license_hash=eq.' + enc(licHash) +
        '&select=link_id,job_id,label,active,created_at,last_accessed_at,revoked_at'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) { res.status(502).json({ error: { message: 'Could not list the links' } }); return; }
      // link_token is deliberately absent from the select above, not filtered
      // out afterwards -- a secret that is never fetched cannot be leaked by a
      // later change to this response shape.
      res.status(200).json({ ok: true, provisioned: true, data: rows || [] });
      return;
    }

    res.status(400).json({ error: { message: "action must be 'create', 'revoke', 'list' or 'view'" } });
  } catch (err) {
    console.error('stonedesk-track error:', err);
    res.status(502).json({ error: { message: 'Something went wrong - please try again' } });
  }
};
