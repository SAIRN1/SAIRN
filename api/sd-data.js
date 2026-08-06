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
const { verifySessionToken, tokenFromRequest } = require('./_lib/auth');

const RESOURCES = {
  profile: true, memory: true, employees: true, slabs: true, render_usage: true, shared_knowledge: true,
  // SAIRNgrounds (2026-08-05) -- see sql/sairngrounds_data_schema.sql. Read branches degrade to
  // an empty-but-ok response (provisioned:false) if that migration hasn't run yet, same pattern
  // as render_usage/shared_knowledge above, rather than hard-failing the whole panel.
  properties: true, jobs: true, quotes: true, golf_zones: true,
  // SAIRNscape (2026-08-06) -- see sql/sairnscape_data_schema.sql. Same graceful-degrade pattern.
  // Named 'scp_jobs'/'scp_quotes' rather than plain 'jobs'/'quotes' specifically to avoid
  // colliding with SAIRNgrounds' existing 'jobs'/'quotes' resource strings above -- two identical
  // resource names would each need an `if (resource==='jobs' && action==='read')` branch, and
  // only the first one in file order would ever match, silently routing SAIRNscape calls into
  // SAIRNgrounds' grd_jobs table. Caught before writing any branch, not after.
  customers: true, scp_jobs: true, scp_quotes: true, schedule: true, invoices: true,
  // StoneDesk Employee Profiles (2026-08-06) -- see sql/sd_employee_profiles_schema.sql.
  employee_profile: true
};
// Roles allowed to list every profile or write any profile -- mirrors the
// EMPLOYEES_*_ROLES pattern above. Self-read (own profile only, derived
// from the caller's own verified token) is allowed for every role and does
// not consult this list -- see the employee_profile branch below.
const EMPLOYEE_PROFILE_MANAGE_ROLES = { owner: true, admin: true };
// Word-frequency cap for the shared_knowledge topics map (2026-08-05) -- pruned to the top N by
// count on every write so a shop's row can't grow unbounded over the account's lifetime. See
// sql/sd_shared_knowledge_schema.sql for the full design/scope note.
const SHARED_KNOWLEDGE_TOPIC_CAP = 150;
// Generic filler words excluded from the shared topics map so "frequent topics" reflects actual
// stone-industry/company-specific vocabulary rather than common English words that would
// otherwise dominate any word-frequency count regardless of subject matter.
const SHARED_KNOWLEDGE_STOPWORDS = {
  about:1, after:1, again:1, their:1, there:1, these:1, thing:1, think:1, would:1, could:1,
  should:1, which:1, where:1, whose:1, other:1, still:1, going:1, doing:1, being:1, maybe:1,
  really:1, actually:1, something:1, someone:1, anyone:1, thanks:1, thank:1, please:1, hello:1,
  regarding:1, wanted:1, wondering:1, question:1, message:1
};
// Roles refused entirely for the employees resource (carries hourly_rate —
// payroll). Owner/Manager may read; Sales/Install may not, per the RBAC
// design in sql/sd_employee_auth_schema.sql. Manager additionally gets
// hourly_rate stripped from the response (see EMPLOYEES read branch below)
// — only Owner sees pay.
const EMPLOYEES_READ_DENIED_ROLES = { sales: true, install: true };
// Roles allowed to WRITE the employees resource (added 2026-08-03, closing
// the security-auditor finding that this branch used to trust an unverified
// body.app_id==='sairnbiz' string with no role check at all). Write access
// stays SAIRNbiz-only, matching this resource's original documented design
// ("employees is managed by SAIRNbiz; StoneDesk may only read it") — this
// fix replaces the unverified string with a verified SAIRNbiz session
// token, it does not also grant StoneDesk write access, which would have
// been a scope change beyond fixing the auth hole. owner/hr: HR manages
// employee records in SAIRNbiz's own role model; accounting/manager/staff
// do not get write access here (a default call, flagged as adjustable
// rather than blocking on it).
const EMPLOYEES_WRITE_ALLOWED_ROLES = { owner: true, hr: true };
// 64KB is not just this API's own choice -- sd_slabs has a DB-level CHECK constraint
// (sdslabs_data_size) enforcing the exact same 65536-byte ceiling on the `data` jsonb blob,
// confirmed empirically (2026-08-04) while building the bulk slab photo upload flow: a
// slabs-specific 500KB override was tried first (photos don't fit in 64KB), reached this API
// fine, then got rejected by Postgres anyway with a much less clear error. There's no per-
// resource override at the DB layer, so there can't usefully be one here either -- this cap
// stays uniform across every resource. The real fix for slabs' photo data lives client-side
// instead: stonedesk.html's bsuCompressUnderBudget() downscales/recompresses each photo to fit
// well under this ceiling before it's ever sent.
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
    res.status(400).json({ error: { message: 'resource must be one of: profile, memory, employees, slabs, render_usage, shared_knowledge, properties, jobs, quotes, golf_zones, customers, scp_jobs, scp_quotes, schedule, invoices' } });
    return;
  }

  // ── 64KB payload cap on writes (reject early, before any DB call) — see MAX_PAYLOAD_BYTES
  // above for why this is uniform across every resource, including slabs ──
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
    // RBAC gate (added alongside sql/sd_employee_auth_schema.sql +
    // api/sd-auth.js): this resource carries hourly_rate (payroll), so it's
    // the first real server-side role check in this file. Sales/Install are
    // refused outright; Owner/Manager may read, but Manager gets hourly_rate
    // stripped — only Owner sees pay. No session token at all -> refused,
    // same as an unrecognized role (fail closed, not open).
    if (resource === 'employees' && action === 'read') {
      // expectedApp:'stonedesk' matters here — without it, a valid SAIRNbiz
      // token (role 'staff'/'accounting'/etc, none of which appear in
      // EMPLOYEES_READ_DENIED_ROLES below since that list only names
      // StoneDesk roles) would slip through this gate unintentionally.
      // Caught while generalizing api/_lib/auth.js for api/sb-auth.js.
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'stonedesk');
      if (!session || EMPLOYEES_READ_DENIED_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Your role does not have access to employee records' } });
        return;
      }
      // No tenant identity -> nothing this shop is allowed to see. Honest empty.
      if (!lic.customer_email) { res.status(200).json({ ok: true, data: [] }); return; }
      const r = await fetch(rest(
        'employees?customer_email=eq.' + enc(lic.customer_email) +
        '&source_app=eq.sairnbiz&status=eq.Active&select=data'), { headers });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      let out = (rows || []).map((x) => x.data);
      if (session.role !== 'owner') {
        // Manager: full roster visibility, but never payroll. Shallow-copy
        // so we're not mutating whatever the upstream client library cached.
        out = out.map(function (e) {
          var copy = Object.assign({}, e);
          delete copy.hourly_rate;
          return copy;
        });
      }
      res.status(200).json({ ok: true, data: out });
      return;
    }
    // ── EMPLOYEES write (SAIRNbiz is the owner/writer of this resource) ────
    // The 405 that used to live here said "employees is managed by SAIRNbiz;
    // StoneDesk may only read it" -- correct on the read side, but it left
    // SAIRNbiz with no server-side write path at all, so SAIRNbiz kept doing
    // a direct client-side anon upsert that can never work (anon is locked
    // out of every table by design -- see this file's header). This branch is
    // that missing path.
    //
    // SECURITY (security-auditor finding, 2026-08-03): this used to gate
    // purely on body.app_id==='sairnbiz' -- a client-supplied string with no
    // verification at all. Any bearer of a shop's license key could set
    // that field and write/corrupt payroll data regardless of role,
    // completely bypassing the employees READ gate's RBAC above it. Fixed
    // by requiring a real SAIRNbiz session token (api/_lib/auth.js, minted
    // by api/sb-auth.js) with a signed `app`:'sairnbiz' claim and an
    // owner/hr role -- unforgeable, unlike the old body field. body.app_id
    // is now informational only (kept for the response), not a security
    // boundary.
    //
    // Conflict target is (customer_email, employee_id) -- verified against
    // the live table before writing this, not assumed: probing on_conflict
    // targets returns 42P10 for employee_id alone and for
    // source_app,employee_id, but resolves for customer_email,employee_id.
    // That is the composite the table is actually provisioned with, and it
    // matches D1b's tenancy model (customer_email is the tenant key here,
    // not license_hash -- employees deliberately differs from sd_slabs and
    // business_profiles in that respect).
    if (resource === 'employees' && action === 'write') {
      const sbSession = verifySessionToken(tokenFromRequest(req), licHash, 'sairnbiz');
      if (!sbSession || !EMPLOYEES_WRITE_ALLOWED_ROLES[sbSession.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Your role does not have write access to employee records' } });
        return;
      }
      // No tenant identity -> refuse rather than write untenanted rows that
      // no read could ever scope to (the read branch returns empty in the
      // same situation; writing here would silently orphan data).
      if (!lic.customer_email) {
        res.status(409).json({ error: { code: 'NO_TENANT', message: 'This license has no customer_email; employees cannot be scoped to a tenant' } });
        return;
      }
      const roster = Array.isArray(payload) ? payload : (payload && Array.isArray(payload.employees) ? payload.employees : null);
      if (!roster) {
        res.status(400).json({ error: { message: 'employees write expects payload to be an array of employees (or {employees:[...]})' } });
        return;
      }
      if (!roster.length) { res.status(200).json({ ok: true, data: [], written: 0 }); return; }
      const ts = nowISO();
      const rows = roster.map(function (e) {
        var emp = e || {};
        return {
          customer_email: lic.customer_email,
          employee_id: String(emp.employee_id || emp.id || ''),
          source_app: 'sairnbiz',
          status: emp.status || 'Active',
          data: emp.data || emp,
          updated_at: ts
        };
      });
      if (rows.some(function (r) { return !r.employee_id; })) {
        res.status(400).json({ error: { message: 'every employee needs an employee_id (or id)' } });
        return;
      }
      const r = await fetch(rest('employees?on_conflict=customer_email,employee_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify(rows)
      });
      const out = await r.json();
      if (!r.ok) return upstream(res, out);
      res.status(200).json({ ok: true, data: (out || []).map(function (x) { return x.data; }), written: (out || []).length });
      return;
    }

    // ── EMPLOYEE PROFILE (sd_employee_profiles, 2026-08-06) ─────────────────
    // Read has two modes: self-read (default -- any authenticated role reads
    // ONLY their own profile, derived from their own verified token, never a
    // client-supplied employee_id) and list-all (payload.all===true, owner/
    // admin only -- the management view). Write is always owner/admin only,
    // and always targets payload.employee_id explicitly (a manager setting
    // someone else's profile, never a self-write -- keeps "how should the AI
    // treat me" out of the hands of the person it describes).
    if (resource === 'employee_profile' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'stonedesk');
      if (!session) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'A valid employee session is required' } });
        return;
      }
      if (payload && payload.all === true) {
        if (!EMPLOYEE_PROFILE_MANAGE_ROLES[session.role]) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only Owner or Manager can view every employee profile' } });
          return;
        }
        const r = await fetch(rest('sd_employee_profiles?license_hash=eq.' + enc(licHash) + '&select=employee_id,experience_level,communication_style,notes'), { headers });
        if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
        const rows = await r.json();
        if (!r.ok) return upstream(res, rows);
        res.status(200).json({ ok: true, data: rows || [], provisioned: true });
        return;
      }
      const r = await fetch(rest('sd_employee_profiles?license_hash=eq.' + enc(licHash) + '&employee_id=eq.' + enc(session.employee_id) + '&select=employee_id,experience_level,communication_style,notes&limit=1'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: null, provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const row = Array.isArray(rows) && rows[0];
      res.status(200).json({ ok: true, data: row || null, provisioned: true });
      return;
    }
    if (resource === 'employee_profile' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'stonedesk');
      if (!session || !EMPLOYEE_PROFILE_MANAGE_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only Owner or Manager can set employee profiles' } });
        return;
      }
      const employee_id = String((payload.employee_id || '')).trim();
      const experience_level = payload.experience_level;
      const communication_style = payload.communication_style;
      const EXP_LEVELS = ['new', 'developing', 'experienced', 'veteran'];
      const STYLES = ['detailed', 'balanced', 'terse'];
      if (!employee_id || EXP_LEVELS.indexOf(experience_level) === -1 || STYLES.indexOf(communication_style) === -1) {
        res.status(400).json({ error: { message: 'employee_id, a valid experience_level (' + EXP_LEVELS.join('|') + '), and a valid communication_style (' + STYLES.join('|') + ') are required' } });
        return;
      }
      if (payload.notes && String(payload.notes).length > 2000) {
        res.status(400).json({ error: { message: 'notes max 2000 chars' } });
        return;
      }
      const r = await fetch(rest('sd_employee_profiles?on_conflict=license_hash,employee_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, employee_id, experience_level, communication_style,
          notes: payload.notes || null, updated_at: nowISO()
        })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Employee profiles table is not set up yet — run sql/sd_employee_profiles_schema.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0] : payload });
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

    // ── SAIRNGROUNDS: PROPERTIES / JOBS / QUOTES / GOLF ZONES (2026-08-05) ──────────────────
    // Four resources, same shape (license_hash + app_id-stamped 'sairngrounds' + jsonb data),
    // following the sd_slabs pattern verbatim -- see sql/sairngrounds_data_schema.sql. Read
    // branches degrade to an empty, ok:true response with provisioned:false if that migration
    // hasn't run yet (same graceful pattern as render_usage/shared_knowledge above), so the
    // client's panels render an honest empty state instead of a hard error.
    if (resource === 'properties' && action === 'read') {
      const r = await fetch(rest('grd_properties?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'properties' && action === 'write') {
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'property payload.id is required' } }); return; }
      const r = await fetch(rest('grd_properties?on_conflict=license_hash,property_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', property_id: String(payload.id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'jobs' && action === 'read') {
      const r = await fetch(rest('grd_jobs?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'jobs' && action === 'write') {
      if (!payload || !payload.id || !payload.property_id) { res.status(400).json({ error: { message: 'job payload.id and payload.property_id are required' } }); return; }
      const r = await fetch(rest('grd_jobs?on_conflict=license_hash,job_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', job_id: String(payload.id), property_id: String(payload.property_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'quotes' && action === 'read') {
      const r = await fetch(rest('grd_quotes?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'quotes' && action === 'write') {
      if (!payload || !payload.id || !payload.property_id) { res.status(400).json({ error: { message: 'quote payload.id and payload.property_id are required' } }); return; }
      const r = await fetch(rest('grd_quotes?on_conflict=license_hash,quote_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', quote_id: String(payload.id), property_id: String(payload.property_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'golf_zones' && action === 'read') {
      const r = await fetch(rest('grd_golf_zones?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'golf_zones' && action === 'write') {
      if (!payload || !payload.id || !payload.property_id) { res.status(400).json({ error: { message: 'zone payload.id and payload.property_id are required' } }); return; }
      const r = await fetch(rest('grd_golf_zones?on_conflict=license_hash,zone_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', zone_id: String(payload.id), property_id: String(payload.property_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }

    // ── SAIRNSCAPE: CUSTOMERS / JOBS / QUOTES / SCHEDULE / INVOICES (2026-08-06) ────────────
    // Same shape and graceful-degrade pattern as the SAIRNgrounds block above -- see
    // sql/sairnscape_data_schema.sql. Resource names 'scp_jobs'/'scp_quotes' (not plain
    // 'jobs'/'quotes') specifically to avoid the collision noted in the RESOURCES comment above.
    if (resource === 'customers' && action === 'read') {
      const r = await fetch(rest('scp_customers?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'customers' && action === 'write') {
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'customer payload.id is required' } }); return; }
      const r = await fetch(rest('scp_customers?on_conflict=license_hash,customer_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairnscape', customer_id: String(payload.id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNscape data tables are not set up yet — run sql/sairnscape_data_schema.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'scp_jobs' && action === 'read') {
      const r = await fetch(rest('scp_jobs?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'scp_jobs' && action === 'write') {
      if (!payload || !payload.id || !payload.customer_id) { res.status(400).json({ error: { message: 'job payload.id and payload.customer_id are required' } }); return; }
      const r = await fetch(rest('scp_jobs?on_conflict=license_hash,job_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairnscape', job_id: String(payload.id), customer_id: String(payload.customer_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNscape data tables are not set up yet — run sql/sairnscape_data_schema.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'scp_quotes' && action === 'read') {
      const r = await fetch(rest('scp_quotes?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'scp_quotes' && action === 'write') {
      if (!payload || !payload.id || !payload.customer_id) { res.status(400).json({ error: { message: 'quote payload.id and payload.customer_id are required' } }); return; }
      const r = await fetch(rest('scp_quotes?on_conflict=license_hash,quote_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairnscape', quote_id: String(payload.id), customer_id: String(payload.customer_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNscape data tables are not set up yet — run sql/sairnscape_data_schema.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'schedule' && action === 'read') {
      const r = await fetch(rest('scp_schedule?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'schedule' && action === 'write') {
      if (!payload || !payload.id || !payload.customer_id) { res.status(400).json({ error: { message: 'schedule payload.id and payload.customer_id are required' } }); return; }
      const r = await fetch(rest('scp_schedule?on_conflict=license_hash,schedule_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairnscape', schedule_id: String(payload.id), customer_id: String(payload.customer_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNscape data tables are not set up yet — run sql/sairnscape_data_schema.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'invoices' && action === 'read') {
      const r = await fetch(rest('scp_invoices?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'invoices' && action === 'write') {
      if (!payload || !payload.id || !payload.customer_id) { res.status(400).json({ error: { message: 'invoice payload.id and payload.customer_id are required' } }); return; }
      const r = await fetch(rest('scp_invoices?on_conflict=license_hash,invoice_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairnscape', invoice_id: String(payload.id), customer_id: String(payload.customer_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNscape data tables are not set up yet — run sql/sairnscape_data_schema.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }

    // ── RENDER USAGE (sd_render_usage — "Visualize on Your Kitchen" cap, 2026-08-04) ────────
    // Read-only here (display only, e.g. "12/75 renders used this month" in the UI). The
    // authoritative check-and-increment lives in api/sd-render.js at actual render time, never
    // trusting a client-reported count before the paid vendor call — deliberately no write
    // branch for this resource here, so a client can never self-report/reset its own usage.
    if (resource === 'render_usage' && action === 'read') {
      const month = new Date().toISOString().slice(0, 7);
      const r = await fetch(rest(
        'sd_render_usage?license_hash=eq.' + enc(licHash) + '&month=eq.' + enc(month) + '&select=count&limit=1'), { headers });
      if (r.status === 404 || r.status === 400) {
        // Migration not run yet — see sql/sd_render_usage_schema.sql. Report 0/not-provisioned
        // rather than erroring the whole panel over a missing table.
        res.status(200).json({ ok: true, data: { count: 0, provisioned: false } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const count = (Array.isArray(rows) && rows[0] && rows[0].count) || 0;
      res.status(200).json({ ok: true, data: { count: count, provisioned: true } });
      return;
    }

    // ── SHARED KNOWLEDGE (sd_shared_knowledge — "Claude learns the company", 2026-08-05) ────
    // One row per shop (license_hash), not per employee/device — see
    // sql/sd_shared_knowledge_schema.sql for the full scope note on what deliberately does NOT
    // carry forward from the old per-browser personalization module. No employee-token gate on
    // either action — this is aggregate topic-frequency data, not the payroll/pay-rate class of
    // sensitivity that got 'employees' and the subcontractor roster their per-role gates.
    if (resource === 'shared_knowledge' && action === 'read') {
      const r = await fetch(rest('sd_shared_knowledge?license_hash=eq.' + enc(licHash) + '&select=data&limit=1'), { headers });
      if (r.status === 404 || r.status === 400) {
        res.status(200).json({ ok: true, data: { topics: {}, totalQuestions: 0 }, provisioned: false });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const row = Array.isArray(rows) && rows[0];
      res.status(200).json({ ok: true, data: (row && row.data) || { topics: {}, totalQuestions: 0 }, provisioned: true });
      return;
    }
    if (resource === 'shared_knowledge' && action === 'write') {
      // payload: { words: ['countertop','waterfall',...] } -- extracted client-side from one
      // user message, same 5+-letter-word pattern the old per-browser module already used
      // (analyzeUserMessage's topicWords regex), just written to a shared row instead of
      // localStorage. Never raw message text — only the extracted word list ever leaves the
      // browser for this purpose.
      const words = Array.isArray(payload.words) ? payload.words.slice(0, 200) : [];
      // removeWords (2026-08-05): strikes exact keys from the topics map before the merge below
      // runs. Added specifically because no delete/edit path existed for this table at all —
      // a test artifact ("zephyrgranite", injected verifying cross-session propagation) needed
      // removing from a shop's real topics data without wiping the whole row. General-purpose
      // going forward, not a one-off: any bad/test/stale term can be struck the same way.
      const removeWords = Array.isArray(payload.removeWords) ? payload.removeWords.slice(0, 50) : [];
      // Read-current-then-write, same accepted non-atomic tradeoff as sd_render_usage's
      // increment (see that resource's own comment) — fine at this feature's real volume
      // (a handful of employees' chat activity, not high-frequency concurrent writes).
      let current = { topics: {}, totalQuestions: 0 };
      try {
        const r = await fetch(rest('sd_shared_knowledge?license_hash=eq.' + enc(licHash) + '&select=data&limit=1'), { headers });
        if (r.status === 404 || r.status === 400) {
          // Migration not run yet — see sql/sd_shared_knowledge_schema.sql. Refuse cleanly here
          // rather than letting the write below fail with an opaque 502 for the same reason
          // (found live: PostgREST returns PGRST205 "table not found in schema cache" for this
          // exact case, which the write POST further down would otherwise surface as a generic
          // "Data store error" with no hint what's actually wrong).
          res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Shared knowledge tracking is not set up yet — run sql/sd_shared_knowledge_schema.sql in Supabase first.' } });
          return;
        }
        if (r.ok) {
          const rows = await r.json();
          const row = Array.isArray(rows) && rows[0];
          if (row && row.data) current = row.data;
        }
      } catch (e) { /* fall through with the empty default rather than blocking the write */ }
      const topics = Object.assign({}, current.topics || {});
      removeWords.forEach((w) => { delete topics[String(w || '').toLowerCase().trim()]; });
      words.forEach((w) => {
        const word = String(w || '').toLowerCase().trim();
        if (word.length < 5 || word.length > 40 || SHARED_KNOWLEDGE_STOPWORDS[word]) return;
        topics[word] = (topics[word] || 0) + 1;
      });
      // Prune to the top N by count before writing back.
      const pruned = Object.entries(topics)
        .sort((a, b) => b[1] - a[1])
        .slice(0, SHARED_KNOWLEDGE_TOPIC_CAP)
        .reduce((acc, [k, v]) => { acc[k] = v; return acc; }, {});
      const newData = { topics: pruned, totalQuestions: (current.totalQuestions || 0) + (words.length ? 1 : 0) };
      const r2 = await fetch(rest('sd_shared_knowledge?on_conflict=license_hash'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, data: newData, updated_at: nowISO() })
      });
      const rows2 = await r2.json();
      if (!r2.ok) return upstream(res, rows2);
      res.status(200).json({ ok: true, data: newData });
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
