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
const { validatePhotosPayload } = require('./_lib/dental-photo-validation');

// Resource registry (2026-08-21). Previously one shared object literal in
// this file that every SAIRN app appended to, alongside a separately
// hand-maintained error string listing the same names. Both were shared
// single lines, which is where every api/sd-data.js merge conflict actually
// happened -- verified against real history, not assumed: the handler
// branches below changed by 100+ lines in those same commits and merged
// cleanly every time, because each app appends in its own region.
//
// Each app now owns api/_resources/<app>.js. The map and the error text are
// both derived from that merge, so they can no longer drift apart -- they
// already had, with employee_profile valid in the map but missing from the
// hand-written list. See api/_resources/index.js for the full rationale.
//
// The request-handling branches were deliberately NOT moved: they close over
// ~15 handler-local bindings and serve 11 live apps, and they were never the
// source of the collisions.
const { RESOURCES, RESOURCE_LIST_TEXT } = require('./_resources');

const SC_RESOURCES = [
  'sc_denial', 'sc_revenue', 'sc_compliance', 'sc_fraud', 'sc_prebill',
  'sc_hcc', 'sc_drg', 'sc_query', 'sc_rac', 'sc_telehealth',
  'sc_anesthesia', 'sc_auth', 'sc_ar', 'sc_providers', 'sc_encoder', 'sc_claims', 'sc_scrubrules',
  'sc_denial_events', 'sc_eligibility', 'sc_settings', 'sc_auth_requests',
  'sc_specialty_checks', 'sc_specialty_checklists', 'sc_anesthesia_base_units',
  'sc_coded_items', 'sc_credential_scope', 'sc_pctc'
];
// Minimum data-retention any SAIRNcode practice may configure, in years.
// Enforced server-side rather than trusted from the client because a value
// written today is inherited by whatever purge mechanism is built later -- a
// tampered or mistaken small number here becomes real, irreversible medical-
// record loss years from now, long after anyone remembers setting it. The
// string 'indefinite' is the other valid value and means never purge.
const SC_RETENTION_FLOOR_YEARS = 10;
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
// CRM/Lead Pipeline privacy (2026-08-19, confirmed with Michael): a lead is
// visible only to management or the salesperson it's assigned to, platform
// rule not a StoneDesk-specific one-off -- see sql/sd_crm_schema.sql's own
// header. 'admin' is StoneDesk's Manager role (matches EMPLOYEES_* above
// and api/sd-auth.js's own "Only Owner or Manager" setup-action gate).
const CRM_MANAGEMENT_ROLES = { owner: true, admin: true };
// Void/override/QC-decision hard-gate role lists (2026-08-07) -- server-side
// mirror of each client's own authority-check role arrays (sairngrounds.html's
// GRD_QC_AUTHORITY_ROLES/MSB_VOID_AUTHORITY_ROLES, sairnscape.html's
// SCP_QC_AUTHORITY_ROLES), kept as the same values rather than imported
// from the client file since there's no shared module between them; if a
// client's role list ever changes, this one needs updating alongside it.
const GRD_QC_AUTHORITY_ROLES = ['owner', 'superintendent', 'manager'];
const MSB_VOID_AUTHORITY_ROLES = ['owner', 'superintendent', 'manager'];
const SCP_QC_AUTHORITY_ROLES = ['owner', 'crew_lead'];
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
  const isScResource = SC_RESOURCES.indexOf(resource) !== -1;
  // 'delete' is only ever valid for the SC_RESOURCES family (see that
  // block's own header comment for why) -- every other resource on this
  // endpoint keeps its original read/write-only behavior unchanged.
  if (action !== 'read' && action !== 'write' && !(action === 'delete' && isScResource)) {
    res.status(400).json({ error: { message: "action must be 'read' or 'write'" + (isScResource ? " or 'delete'" : '') } });
    return;
  }
  if (!RESOURCES[resource]) {
    res.status(400).json({ error: { message: 'resource must be one of: ' + RESOURCE_LIST_TEXT } });
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

    // ── CRM / LEAD PIPELINE (2026-08-19) ────────────────────────────────────────────────────
    // First real server sync sd_crm has ever had -- was pure localStorage before this (see
    // sql/sd_crm_schema.sql's own header). Read/write both require a real StoneDesk session
    // (X-SD-Auth) -- unlike shared_knowledge above, a lead is real customer-identifying sales
    // data, not aggregate topic-frequency noise, so there's no unauthenticated path at all.
    if (resource === 'sd_crm' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'stonedesk');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const r = await fetch(rest('sd_crm?license_hash=eq.' + enc(licHash) + '&select=lead_id,assigned_employee_id,data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      // Management sees every lead. A non-management caller sees only leads
      // assigned to them -- an UNASSIGNED lead (assigned_employee_id null) is
      // management-only-visible too, same as an assigned one belonging to
      // someone else: a fresh, untriaged lead shouldn't be visible firm-wide
      // by default any more than an already-assigned one should be visible
      // outside its owner. Flagged as the one real judgment call in this
      // design -- adjustable if Michael wants unassigned leads visible to
      // all sales reps instead (e.g. so they can self-claim).
      let out = rows || [];
      if (!CRM_MANAGEMENT_ROLES[session.role]) {
        out = out.filter((r) => r.assigned_employee_id === session.employee_id);
      }
      const data = out.map((r) => Object.assign({ id: r.lead_id, assigned_employee_id: r.assigned_employee_id || '' }, r.data));
      res.status(200).json({ ok: true, data, provisioned: true });
      return;
    }
    if (resource === 'sd_crm' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'stonedesk');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'sd_crm payload.id is required' } }); return; }
      const isManagement = !!CRM_MANAGEMENT_ROLES[session.role];
      const existingR = await fetch(rest('sd_crm?license_hash=eq.' + enc(licHash) + '&lead_id=eq.' + enc(payload.id) + '&select=assigned_employee_id'), { headers });
      if (existingR.status === 404 || existingR.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'CRM sync is not set up yet — run sql/sd_crm_schema.sql in Supabase first.' } });
        return;
      }
      const existingRows = await existingR.json();
      if (!existingR.ok) return upstream(res, existingRows);
      const existingRow = Array.isArray(existingRows) && existingRows[0];
      const requestedAssignee = payload.assigned_employee_id !== undefined
        ? (payload.assigned_employee_id || null)
        : (existingRow ? existingRow.assigned_employee_id : null);
      if (!isManagement) {
        // A non-management caller may only write a lead already assigned to
        // them, and may never change the assignment -- reassignment
        // (including self-assigning a currently-unassigned lead, which this
        // role can't even see per the read gate above) is management-only.
        if (existingRow && existingRow.assigned_employee_id !== session.employee_id) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'This lead is not assigned to you' } });
          return;
        }
        if (requestedAssignee !== session.employee_id) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can assign or reassign a lead' } });
          return;
        }
      }
      const leadData = Object.assign({}, payload);
      delete leadData.id;
      delete leadData.assigned_employee_id;
      const r = await fetch(rest('sd_crm?on_conflict=license_hash,lead_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, lead_id: String(payload.id),
          assigned_employee_id: requestedAssignee, data: leadData, updated_at: nowISO()
        })
      });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: Object.assign({ id: payload.id, assigned_employee_id: requestedAssignee || '' }, leadData) });
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

    // === SAIRNGROUNDS: SCHEDULE (2026-08-06, related-bug fix) ===
    // (this project's house style is plain === headers, not the Unicode
    // box-drawing dashes the surrounding sections in this file already use
    // -- not fixing those pre-existing ones here, out of scope for this fix)
    // sairngrounds.html's saveSched()/grdMarkScheduleComplete() called grdData('write','schedule',...)
    // -- the bare resource name 'schedule' was already claimed by SAIRNscape's block below
    // (parented by customer_id), so every SAIRNgrounds schedule write has been silently 400ing
    // since Item 9 shipped (grdData/scpData both swallow a non-ok response and return null,
    // and neither caller checked the return value, so nothing ever surfaced this). Found while
    // building the progress_photos route below and confirming which resource names were safe to
    // reuse as a template. Fixed here by giving SAIRNgrounds its own 'grd_schedule' resource name,
    // same disambiguation SAIRNscape's 'scp_jobs'/'scp_quotes' already use -- see the RESOURCES
    // comment above. sairngrounds.html's three call sites and grdSyncFromServer()'s resources
    // list were updated to match in the same push.
    if (resource === 'grd_schedule' && action === 'read') {
      const r = await fetch(rest('grd_schedule?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'grd_schedule' && action === 'write') {
      if (!payload || !payload.id || !payload.property_id) { res.status(400).json({ error: { message: 'schedule payload.id and payload.property_id are required' } }); return; }
      const r = await fetch(rest('grd_schedule?on_conflict=license_hash,schedule_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', schedule_id: String(payload.id), property_id: String(payload.property_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }

    // === SAIRNGROUNDS: PROGRESS PHOTOS / COMPLETION-GATE QC (2026-08-06, item 3 cross-device fix) ===
    // Real fix for the disclosed gap: grdData('write','progress_photos',...) had no route here at
    // all (only StoneDesk's separate api/sd-sub-data.js had a 'progress_photos' handler, scoped to
    // its own sd_progress_photos table/app). Every upload was localStorage-only, so a QC reviewer
    // on a different device never saw the crew's photo -- silently defeating the whole point of
    // the completion gate. Named 'grd_progress_photos' (not bare 'progress_photos') for the same
    // collision reason as grd_schedule above -- SAIRNscape needs the identical resource shape and
    // must not share a name with it. No qc-review-specific action: sairngrounds.html's
    // grdQcDecide() already reads the record, mutates qc_status/qc_by/qc_at locally, and re-sends
    // the WHOLE record through 'write' (same read-modify-write-the-whole-blob shape every other
    // resource in this file already uses) -- a separate action type would just be a second way to
    // do the same upsert.
    if (resource === 'grd_progress_photos' && action === 'read') {
      const r = await fetch(rest('grd_progress_photos?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'grd_progress_photos' && action === 'write') {
      if (!payload || !payload.id || !payload.schedule_id) { res.status(400).json({ error: { message: 'photo payload.id and payload.schedule_id are required' } }); return; }
      // QC-decision hard gate (2026-08-07): grdQcDecide() previously read-
      // modify-wrote the whole photo blob through this same generic 'write'
      // branch with ONLY grdHasQcAuthority()/self-QC checked client-side --
      // any valid license holder, any role, could POST a qc_status:'approved'
      // payload directly and the server would accept it, same gap class
      // StoneDesk's api/sd-sub-data.js already closed for its own
      // 'qc-review' action. A qc_status of 'approved'/'rejected' is what
      // marks THIS write as a QC decision (vs. the initial upload, which is
      // always 'pending') -- role and self-QC are both re-verified against
      // the server's own record of who captured the photo, not the client-
      // supplied payload.captured_by, so a forged captured_by can't be used
      // to spoof either check.
      if (payload.qc_status === 'approved' || payload.qc_status === 'rejected') {
        const grdCaller = verifySessionToken(tokenFromRequest(req), licHash, 'sairngrounds');
        if (!grdCaller || GRD_QC_AUTHORITY_ROLES.indexOf(grdCaller.role) === -1) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only Owner, Superintendent, or Manager can QC-review a progress photo' } });
          return;
        }
        const existingPhoto = await fetch(rest('grd_progress_photos?license_hash=eq.' + enc(licHash) + '&photo_id=eq.' + enc(String(payload.id)) + '&select=data&limit=1'), { headers });
        if (existingPhoto.status === 404 || existingPhoto.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema.sql in Supabase first.' } }); return; }
        const existingPhotoRows = await existingPhoto.json();
        if (!existingPhoto.ok) return upstream(res, existingPhotoRows);
        const existingPhotoRow = Array.isArray(existingPhotoRows) && existingPhotoRows[0];
        if (existingPhotoRow && existingPhotoRow.data && existingPhotoRow.data.captured_by === grdCaller.employee_id) {
          res.status(403).json({ error: { code: 'SELF_QC_FORBIDDEN', message: 'You cannot QC-review your own photo -- have someone else review it' } });
          return;
        }
      }
      const r = await fetch(rest('grd_progress_photos?on_conflict=license_hash,photo_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', photo_id: String(payload.id), schedule_id: String(payload.schedule_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }

    // === SAIRNGROUNDS: INVOICES / DREAMCLOSE (2026-08-06, sweep fix) ===
    // Same collision/missing-route bug class as grd_schedule and
    // grd_progress_photos above, found via a full resource-name sweep after
    // the user asked whether dcCreateInvoiceAndSchedule()'s reported PASS
    // was real. 'invoices' was already claimed by SAIRNscape's block below
    // (customer_id-scoped) -- every SAIRNgrounds invoice write (saveInv(),
    // DreamClose) has always 400'd, same silent failure as grd_schedule had.
    // 'dreamclose' had no route at all, anywhere, ever -- not a misread, a
    // real gap. The sweep also found ~18 more resource names used by
    // SAIRNgrounds/SAIRNscape client code with no matching route at all
    // (irrigation, merchandise/bar, training academy, invasive species,
    // water features, vendors, BOQ, ecosystem reports, generic designs) --
    // NOT fixed here, deliberately out of scope for this pass; see the
    // session report for the full list.
    if (resource === 'grd_invoices' && action === 'read') {
      const r = await fetch(rest('grd_invoices?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'grd_invoices' && action === 'write') {
      if (!payload || !payload.id || !payload.property_id) { res.status(400).json({ error: { message: 'invoice payload.id and payload.property_id are required' } }); return; }
      const r = await fetch(rest('grd_invoices?on_conflict=license_hash,invoice_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', invoice_id: String(payload.id), property_id: String(payload.property_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'grd_dreamclose' && action === 'read') {
      const r = await fetch(rest('grd_dreamclose?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'grd_dreamclose' && action === 'write') {
      if (!payload || !payload.id || !payload.property_id) { res.status(400).json({ error: { message: 'dreamclose payload.id and payload.property_id are required' } }); return; }
      const r = await fetch(rest('grd_dreamclose?on_conflict=license_hash,dreamclose_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', dreamclose_id: String(payload.id), property_id: String(payload.property_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }

    // === SAIRNGROUNDS: FULL RESOURCE SWEEP, PHASE 2 (2026-08-06) ===
    // See sql/sairngrounds_data_schema_phase2.sql for the full rationale --
    // every resource below previously had either no route at all or a bare
    // name colliding with SAIRNscape (same bug class as grd_schedule/
    // grd_invoices/grd_dreamclose above, just found by a full sweep instead
    // of one at a time). msb_* keeps its existing prefix (see that SQL
    // file own header for why); everything else here is grd_-prefixed.
    if (resource === 'grd_invasive_sightings' && action === 'read') {
      const r = await fetch(rest('grd_invasive_sightings?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'grd_invasive_sightings' && action === 'write') {
      if (!payload || !payload.id || !payload.property_id) { res.status(400).json({ error: { message: 'invasive sighting payload.id and payload.property_id are required' } }); return; }
      const r = await fetch(rest('grd_invasive_sightings?on_conflict=license_hash,sighting_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', sighting_id: String(payload.id), property_id: String(payload.property_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema_phase2.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'grd_ecosystem_reports' && action === 'read') {
      const r = await fetch(rest('grd_ecosystem_reports?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'grd_ecosystem_reports' && action === 'write') {
      if (!payload || !payload.id || !payload.property_id) { res.status(400).json({ error: { message: 'ecosystem report payload.id and payload.property_id are required' } }); return; }
      const r = await fetch(rest('grd_ecosystem_reports?on_conflict=license_hash,report_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', report_id: String(payload.id), property_id: String(payload.property_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema_phase2.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'grd_designs' && action === 'read') {
      const r = await fetch(rest('grd_designs?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'grd_designs' && action === 'write') {
      if (!payload || !payload.id || !payload.property_id) { res.status(400).json({ error: { message: 'design walk payload.id and payload.property_id are required' } }); return; }
      const r = await fetch(rest('grd_designs?on_conflict=license_hash,design_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', design_id: String(payload.id), property_id: String(payload.property_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema_phase2.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'grd_irr_controllers' && action === 'read') {
      const r = await fetch(rest('grd_irr_controllers?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'grd_irr_controllers' && action === 'write') {
      if (!payload || !payload.id || !payload.property_id) { res.status(400).json({ error: { message: 'irrigation controller payload.id and payload.property_id are required' } }); return; }
      const r = await fetch(rest('grd_irr_controllers?on_conflict=license_hash,controller_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', controller_id: String(payload.id), property_id: String(payload.property_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema_phase2.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'grd_irr_zones' && action === 'read') {
      const r = await fetch(rest('grd_irr_zones?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'grd_irr_zones' && action === 'write') {
      if (!payload || !payload.id || !payload.property_id) { res.status(400).json({ error: { message: 'irrigation zone payload.id and payload.property_id are required' } }); return; }
      const r = await fetch(rest('grd_irr_zones?on_conflict=license_hash,zone_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', zone_id: String(payload.id), property_id: String(payload.property_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema_phase2.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'grd_irr_schedules' && action === 'read') {
      const r = await fetch(rest('grd_irr_schedules?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'grd_irr_schedules' && action === 'write') {
      if (!payload || !payload.id || !payload.zone_id) { res.status(400).json({ error: { message: 'irrigation run schedule payload.id and payload.zone_id are required' } }); return; }
      const r = await fetch(rest('grd_irr_schedules?on_conflict=license_hash,irrsched_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', irrsched_id: String(payload.id), zone_id: String(payload.zone_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema_phase2.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'grd_water_features' && action === 'read') {
      const r = await fetch(rest('grd_water_features?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'grd_water_features' && action === 'write') {
      if (!payload || !payload.id || !payload.property_id) { res.status(400).json({ error: { message: 'water feature payload.id and payload.property_id are required' } }); return; }
      const r = await fetch(rest('grd_water_features?on_conflict=license_hash,feature_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', feature_id: String(payload.id), property_id: String(payload.property_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema_phase2.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'grd_training_courses' && action === 'read') {
      const r = await fetch(rest('grd_training_courses?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'grd_training_courses' && action === 'write') {
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'training course payload.id is required' } }); return; }
      const r = await fetch(rest('grd_training_courses?on_conflict=license_hash,course_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', course_id: String(payload.id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema_phase2.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'grd_training_completions' && action === 'read') {
      const r = await fetch(rest('grd_training_completions?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'grd_training_completions' && action === 'write') {
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'training completion payload.id is required' } }); return; }
      const r = await fetch(rest('grd_training_completions?on_conflict=license_hash,completion_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', completion_id: String(payload.id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema_phase2.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'grd_boq_rates' && action === 'read') {
      const r = await fetch(rest('grd_boq_rates?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'grd_boq_rates' && action === 'write') {
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'BOQ rate payload.id is required' } }); return; }
      const r = await fetch(rest('grd_boq_rates?on_conflict=license_hash,rate_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', rate_id: String(payload.id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema_phase2.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'grd_vendors' && action === 'read') {
      const r = await fetch(rest('grd_vendors?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'grd_vendors' && action === 'write') {
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'vendor payload.id is required' } }); return; }
      const r = await fetch(rest('grd_vendors?on_conflict=license_hash,vendor_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', vendor_id: String(payload.id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema_phase2.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'msb_products' && action === 'read') {
      const r = await fetch(rest('msb_products?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'msb_products' && action === 'write') {
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'product payload.id is required' } }); return; }
      const r = await fetch(rest('msb_products?on_conflict=license_hash,product_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', product_id: String(payload.id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema_phase2.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'msb_sales' && action === 'read') {
      const r = await fetch(rest('msb_sales?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'msb_sales' && action === 'write') {
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'sale payload.id is required' } }); return; }
      // Void hard gate (2026-08-07): confirmMsbVoid() previously read-modify-
      // wrote the whole sale blob through this same generic 'write' branch
      // with ONLY msbHasVoidAuthority() checked client-side -- any valid
      // license holder, any role, could POST a voided:true payload directly
      // and the server would accept it. payload.voided===true is what marks
      // THIS write as a void (a normal sale/checkout write never sets it),
      // so only that case needs the extra check.
      if (payload.voided === true) {
        const msbCaller = verifySessionToken(tokenFromRequest(req), licHash, 'sairngrounds');
        if (!msbCaller || MSB_VOID_AUTHORITY_ROLES.indexOf(msbCaller.role) === -1) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only Owner, Superintendent, or Manager can void a sale' } });
          return;
        }
      }
      const r = await fetch(rest('msb_sales?on_conflict=license_hash,sale_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', sale_id: String(payload.id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema_phase2.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'msb_licenses' && action === 'read') {
      const r = await fetch(rest('msb_licenses?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'msb_licenses' && action === 'write') {
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'license payload.id is required' } }); return; }
      const r = await fetch(rest('msb_licenses?on_conflict=license_hash,msblicense_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', msblicense_id: String(payload.id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema_phase2.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'msb_inventory_log' && action === 'read') {
      const r = await fetch(rest('msb_inventory_log?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'msb_inventory_log' && action === 'write') {
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'inventory log entry payload.id is required' } }); return; }
      const r = await fetch(rest('msb_inventory_log?on_conflict=license_hash,log_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', log_id: String(payload.id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema_phase2.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'msb_bottle_scans' && action === 'read') {
      const r = await fetch(rest('msb_bottle_scans?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'msb_bottle_scans' && action === 'write') {
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'bottle scan payload.id is required' } }); return; }
      const r = await fetch(rest('msb_bottle_scans?on_conflict=license_hash,scan_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', scan_id: String(payload.id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema_phase2.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'msb_food_scans' && action === 'read') {
      const r = await fetch(rest('msb_food_scans?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'msb_food_scans' && action === 'write') {
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'food scan payload.id is required' } }); return; }
      const r = await fetch(rest('msb_food_scans?on_conflict=license_hash,foodscan_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', foodscan_id: String(payload.id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema_phase2.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'msb_food_waste' && action === 'read') {
      const r = await fetch(rest('msb_food_waste?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'msb_food_waste' && action === 'write') {
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'waste log entry payload.id is required' } }); return; }
      const r = await fetch(rest('msb_food_waste?on_conflict=license_hash,waste_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', waste_id: String(payload.id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema_phase2.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'msb_food_cost_log' && action === 'read') {
      const r = await fetch(rest('msb_food_cost_log?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'msb_food_cost_log' && action === 'write') {
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'food cost log entry payload.id is required' } }); return; }
      const r = await fetch(rest('msb_food_cost_log?on_conflict=license_hash,costlog_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', costlog_id: String(payload.id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema_phase2.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'msb_sale_hours' && action === 'read') {
      const r = await fetch(rest('msb_sale_hours?license_hash=eq.' + enc(licHash) + '&select=data&limit=1'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const row = Array.isArray(rows) && rows[0];
      res.status(200).json({ ok: true, data: row ? row.data : [], provisioned: true });
      return;
    }
    if (resource === 'msb_sale_hours' && action === 'write') {
      if (!payload) { res.status(400).json({ error: { message: 'sale-hours config payload is required' } }); return; }
      const r = await fetch(rest('msb_sale_hours?on_conflict=license_hash'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds data tables are not set up yet — run sql/sairngrounds_data_schema_phase2.sql in Supabase first.' } }); return; }
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

    // === SAIRNSCAPE: FULL RESOURCE SWEEP, PHASE 2 (2026-08-06) ===
    // See sql/sairnscape_data_schema_phase2.sql -- same sweep as the
    // SAIRNgrounds block above, this is the SAIRNscape half of the six
    // shared resources.
    if (resource === 'scp_designs' && action === 'read') {
      const r = await fetch(rest('scp_designs?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'scp_designs' && action === 'write') {
      if (!payload || !payload.id || !payload.customer_id) { res.status(400).json({ error: { message: 'design walk payload.id and payload.customer_id are required' } }); return; }
      const r = await fetch(rest('scp_designs?on_conflict=license_hash,design_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairnscape', design_id: String(payload.id), customer_id: String(payload.customer_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNscape data tables are not set up yet — run sql/sairnscape_data_schema_phase2.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'scp_irr_controllers' && action === 'read') {
      const r = await fetch(rest('scp_irr_controllers?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'scp_irr_controllers' && action === 'write') {
      if (!payload || !payload.id || !payload.customer_id) { res.status(400).json({ error: { message: 'irrigation controller payload.id and payload.customer_id are required' } }); return; }
      const r = await fetch(rest('scp_irr_controllers?on_conflict=license_hash,controller_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairnscape', controller_id: String(payload.id), customer_id: String(payload.customer_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNscape data tables are not set up yet — run sql/sairnscape_data_schema_phase2.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'scp_irr_zones' && action === 'read') {
      const r = await fetch(rest('scp_irr_zones?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'scp_irr_zones' && action === 'write') {
      if (!payload || !payload.id || !payload.customer_id) { res.status(400).json({ error: { message: 'irrigation zone payload.id and payload.customer_id are required' } }); return; }
      const r = await fetch(rest('scp_irr_zones?on_conflict=license_hash,zone_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairnscape', zone_id: String(payload.id), customer_id: String(payload.customer_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNscape data tables are not set up yet — run sql/sairnscape_data_schema_phase2.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'scp_irr_schedules' && action === 'read') {
      const r = await fetch(rest('scp_irr_schedules?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'scp_irr_schedules' && action === 'write') {
      if (!payload || !payload.id || !payload.zone_id) { res.status(400).json({ error: { message: 'irrigation run schedule payload.id and payload.zone_id are required' } }); return; }
      const r = await fetch(rest('scp_irr_schedules?on_conflict=license_hash,irrsched_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairnscape', irrsched_id: String(payload.id), zone_id: String(payload.zone_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNscape data tables are not set up yet — run sql/sairnscape_data_schema_phase2.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'scp_water_features' && action === 'read') {
      const r = await fetch(rest('scp_water_features?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'scp_water_features' && action === 'write') {
      if (!payload || !payload.id || !payload.customer_id) { res.status(400).json({ error: { message: 'water feature payload.id and payload.customer_id are required' } }); return; }
      const r = await fetch(rest('scp_water_features?on_conflict=license_hash,feature_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairnscape', feature_id: String(payload.id), customer_id: String(payload.customer_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNscape data tables are not set up yet — run sql/sairnscape_data_schema_phase2.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'scp_vendors' && action === 'read') {
      const r = await fetch(rest('scp_vendors?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'scp_vendors' && action === 'write') {
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'vendor payload.id is required' } }); return; }
      const r = await fetch(rest('scp_vendors?on_conflict=license_hash,vendor_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairnscape', vendor_id: String(payload.id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNscape data tables are not set up yet — run sql/sairnscape_data_schema_phase2.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }

    // === SAIRNSCAPE: PROGRESS PHOTOS / COMPLETION-GATE QC (2026-08-06, item 3 cross-device fix) ===
    // Same fix and same reasoning as SAIRNgrounds' grd_progress_photos block above -- see that
    // block's comment. 'scp_progress_photos' (not bare 'progress_photos') for the same collision
    // reason 'scp_jobs'/'scp_quotes' already exist.
    if (resource === 'scp_progress_photos' && action === 'read') {
      const r = await fetch(rest('scp_progress_photos?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'scp_progress_photos' && action === 'write') {
      if (!payload || !payload.id || !payload.schedule_id) { res.status(400).json({ error: { message: 'photo payload.id and payload.schedule_id are required' } }); return; }
      // QC-decision hard gate (2026-08-07) -- same fix, same reasoning as
      // SAIRNgrounds' grd_progress_photos block above: role and self-QC are
      // both re-verified against the server's own record of who captured
      // the photo, not the client-supplied payload.captured_by.
      if (payload.qc_status === 'approved' || payload.qc_status === 'rejected') {
        const scpCaller = verifySessionToken(tokenFromRequest(req), licHash, 'sairnscape');
        if (!scpCaller || SCP_QC_AUTHORITY_ROLES.indexOf(scpCaller.role) === -1) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only Owner or Crew Lead can QC-review a progress photo' } });
          return;
        }
        const existingPhoto = await fetch(rest('scp_progress_photos?license_hash=eq.' + enc(licHash) + '&photo_id=eq.' + enc(String(payload.id)) + '&select=data&limit=1'), { headers });
        if (existingPhoto.status === 404 || existingPhoto.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNscape data tables are not set up yet — run sql/sairnscape_data_schema.sql in Supabase first.' } }); return; }
        const existingPhotoRows = await existingPhoto.json();
        if (!existingPhoto.ok) return upstream(res, existingPhotoRows);
        const existingPhotoRow = Array.isArray(existingPhotoRows) && existingPhotoRows[0];
        if (existingPhotoRow && existingPhotoRow.data && existingPhotoRow.data.captured_by === scpCaller.employee_id) {
          res.status(403).json({ error: { code: 'SELF_QC_FORBIDDEN', message: 'You cannot QC-review your own photo -- have someone else review it' } });
          return;
        }
      }
      const r = await fetch(rest('scp_progress_photos?on_conflict=license_hash,photo_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairnscape', photo_id: String(payload.id), schedule_id: String(payload.schedule_id), data: payload, updated_at: nowISO() })
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
    // either action for most apps — this is aggregate topic-frequency data, not the payroll/
    // pay-rate class of sensitivity that got 'employees' and the subcontractor roster their
    // per-role gates.
    //
    // SAIRNlegacy is the one deliberate exception (2026-08-19, confirmed with Michael): a
    // funeral home's "trending topics" can carry a grieving family's name and a real conflict
    // ("the Fenwick cremation dispute"), read closer to SAIRNlaw's privilege concern than to
    // any other app's shared-knowledge risk -- but unlike SAIRNlaw, there was no existing
    // per-question selector to gate on, and Michael's call was a real server-side PERMISSION
    // gate (management/owner-tier by default, individually grantable) rather than a content
    // gate. Scoped narrowly to app_id==='sairnlegacy' only -- zero behavior change for every
    // other app's shared_knowledge calls, which is why this check lives inline here rather than
    // as a blanket change to the branch above.
    async function legSharedKnowledgePermission() {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, 'sairnlegacy');
      if (!caller) return { ok: false, status: 401, code: 'NO_SESSION', message: 'Sign in first' };
      if (caller.role === 'owner' || caller.role === 'director') return { ok: true };
      // 'staff' -- checked fresh against the employee row on every call, not embedded in the
      // session token, so a revoke takes effect immediately rather than waiting out the
      // token's 12h lifetime.
      const r = await fetch(rest('sairnlegacy_employee_auth?license_hash=eq.' + enc(licHash) +
        '&employee_id=eq.' + enc(caller.employee_id) + '&active=eq.true&select=shared_knowledge_access&limit=1'), { headers });
      if (!r.ok) return { ok: false, status: 502, code: 'UPSTREAM', message: 'Could not verify access — try again' };
      const rows = await r.json();
      const row = Array.isArray(rows) && rows[0];
      if (row && row.shared_knowledge_access) return { ok: true };
      return { ok: false, status: 403, code: 'FORBIDDEN', message: 'This employee does not have shared-knowledge access — ask an Owner or Director to grant it' };
    }
    if (resource === 'shared_knowledge' && (action === 'read' || action === 'write') && body.app_id === 'sairnlegacy') {
      const perm = await legSharedKnowledgePermission();
      if (!perm.ok) { res.status(perm.status).json({ error: { code: perm.code, message: perm.message } }); return; }
    }
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

    // ── SAIRNDESIGN: sdn_clients PRIVACY GATE (2026-08-20) ──────────────────────────────────
    // Task 2 of the platform sales-lead-privacy rule (StoneDesk's sd_crm was item 1,
    // 2026-08-19): a client/lead is visible only to management (Owner/Office) or the designer
    // it's assigned to. This bespoke branch runs BEFORE the generic SDN_RESOURCES loop below
    // (which still handles sdn_clients too, unauthenticated) -- inserted first in file order so
    // it matches first, carving sdn_clients out of the generic ungated path the same way
    // StoneDesk's sd_crm and shared_knowledge's sairnlegacy carve-out were done. Every other
    // sdn_ resource (projects, spec items, moodboards, etc.) is unaffected, still fully
    // generic/ungated -- this rule is specifically about client/lead data, not the whole app.
    const SDN_CLIENT_MANAGEMENT_ROLES = { owner: true, office: true };
    if (resource === 'sdn_clients' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairndesign');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const r = await fetch(rest('sdn_clients?license_hash=eq.' + enc(licHash) + '&select=client_id,assigned_employee_id,data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      // Management sees every client. A non-management (designer) caller sees only clients
      // assigned to them -- an UNASSIGNED client is management-only-visible too, same
      // reasoning (and same confirmed-correct default, per Michael's call on StoneDesk's
      // build) as an already-assigned client belonging to someone else.
      let out = rows || [];
      if (!SDN_CLIENT_MANAGEMENT_ROLES[session.role]) {
        out = out.filter((r) => r.assigned_employee_id === session.employee_id);
      }
      const data = out.map((r) => Object.assign({ id: r.client_id, assigned_employee_id: r.assigned_employee_id || '' }, r.data));
      res.status(200).json({ ok: true, data, provisioned: true });
      return;
    }
    if (resource === 'sdn_clients' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairndesign');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'sdn_clients payload.id is required' } }); return; }
      const isManagement = !!SDN_CLIENT_MANAGEMENT_ROLES[session.role];
      const existingR = await fetch(rest('sdn_clients?license_hash=eq.' + enc(licHash) + '&client_id=eq.' + enc(payload.id) + '&select=assigned_employee_id'), { headers });
      if (existingR.status === 404 || existingR.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Client assignment tracking is not set up yet — run sql/sairndesign_clients_assignment_migration.sql in Supabase first.' } });
        return;
      }
      const existingRows = await existingR.json();
      if (!existingR.ok) return upstream(res, existingRows);
      const existingRow = Array.isArray(existingRows) && existingRows[0];
      const requestedAssignee = payload.assigned_employee_id !== undefined
        ? (payload.assigned_employee_id || null)
        : (existingRow ? existingRow.assigned_employee_id : null);
      if (!isManagement) {
        // A designer may only write a client already assigned to them, and may never change
        // the assignment -- reassignment (including self-assigning a currently-unassigned,
        // invisible-to-them client) is management-only.
        if (existingRow && existingRow.assigned_employee_id !== session.employee_id) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'This client is not assigned to you' } });
          return;
        }
        if (requestedAssignee !== session.employee_id) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can assign or reassign a client' } });
          return;
        }
      }
      const clientData = Object.assign({}, payload);
      delete clientData.id;
      delete clientData.assigned_employee_id;
      const r = await fetch(rest('sdn_clients?on_conflict=license_hash,client_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairndesign', client_id: String(payload.id),
          assigned_employee_id: requestedAssignee, data: clientData, updated_at: nowISO()
        })
      });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: Object.assign({ id: payload.id, assigned_employee_id: requestedAssignee || '' }, clientData) });
      return;
    }

    // ── SAIRNBUILD: bld_bids PRIVACY GATE (2026-08-20) ───────────────────────────────────────
    // Task 3 of the platform sales-lead-privacy rule (StoneDesk's sd_crm was item 1,
    // SAIRNdesign's sdn_clients was item 2): a bid is visible only to management (Owner/Office)
    // or the PM it's assigned to. Same shape as SAIRNdesign's sdn_clients gate directly above --
    // bespoke branch, runs before any generic resource loop, always returns. Unlike sdn_clients
    // (which was retrofitted onto an existing generic resource), bld_bids never had ANY server
    // sync before this, so there is no generic-loop fallback registered for it anywhere else in
    // this file -- this branch is the only code path that ever handles this resource.
    const BLD_BID_MANAGEMENT_ROLES = { owner: true, office: true };
    if (resource === 'bld_bids' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnbuild');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const r = await fetch(rest('bld_bids?license_hash=eq.' + enc(licHash) + '&select=bid_id,assigned_employee_id,data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      // Management sees every bid. A non-management (PM) caller sees only bids assigned to
      // them -- an UNASSIGNED bid is management-only-visible too, same reasoning (and same
      // confirmed-correct default, per Michael's call on StoneDesk's build) as an
      // already-assigned bid belonging to someone else.
      let out = rows || [];
      if (!BLD_BID_MANAGEMENT_ROLES[session.role]) {
        out = out.filter((r) => r.assigned_employee_id === session.employee_id);
      }
      const data = out.map((r) => Object.assign({ id: r.bid_id, assigned_employee_id: r.assigned_employee_id || '' }, r.data));
      res.status(200).json({ ok: true, data, provisioned: true });
      return;
    }
    if (resource === 'bld_bids' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnbuild');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'bld_bids payload.id is required' } }); return; }
      const isManagement = !!BLD_BID_MANAGEMENT_ROLES[session.role];
      const existingR = await fetch(rest('bld_bids?license_hash=eq.' + enc(licHash) + '&bid_id=eq.' + enc(payload.id) + '&select=assigned_employee_id'), { headers });
      if (existingR.status === 404 || existingR.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Bid assignment tracking is not set up yet — run sql/sairnbuild_bids_schema.sql in Supabase first.' } });
        return;
      }
      const existingRows = await existingR.json();
      if (!existingR.ok) return upstream(res, existingRows);
      const existingRow = Array.isArray(existingRows) && existingRows[0];
      const requestedAssignee = payload.assigned_employee_id !== undefined
        ? (payload.assigned_employee_id || null)
        : (existingRow ? existingRow.assigned_employee_id : null);
      if (!isManagement) {
        // A PM may only write a bid already assigned to them, and may never change the
        // assignment -- reassignment (including self-assigning a currently-unassigned,
        // invisible-to-them bid) is management-only.
        if (existingRow && existingRow.assigned_employee_id !== session.employee_id) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'This bid is not assigned to you' } });
          return;
        }
        if (requestedAssignee !== session.employee_id) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can assign or reassign a bid' } });
          return;
        }
      }
      const bidData = Object.assign({}, payload);
      delete bidData.id;
      delete bidData.assigned_employee_id;
      const r = await fetch(rest('bld_bids?on_conflict=license_hash,bid_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairnbuild', bid_id: String(payload.id),
          assigned_employee_id: requestedAssignee, data: bidData, updated_at: nowISO()
        })
      });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: Object.assign({ id: payload.id, assigned_employee_id: requestedAssignee || '' }, bidData) });
      return;
    }

    // ── SAIRNBUILD: bld_tna PRIVACY GATE (2026-08-20) ────────────────────────────────────────
    // Training Needs Assessment (Hennessy-Hicks-style, see sql/sairnbuild_tna_schema.sql for the
    // full methodology/provenance disclosure). Subject-based visibility, not assignee-based: a
    // non-management employee may only read/write rows ABOUT THEMSELVES (subject_employee_id ===
    // their own employee_id) -- both the 'self' row they filled out and any 'management' row a
    // supervisor filled out about them, per Michael's spec ("employee sees their own results").
    // Management may read every subject's rows ("management sees the analytical view across
    // their team") and may write 'management'-perspective rows for any subject. A 'self' row is
    // only ever writable by the subject themselves, including for a management-role caller
    // assessing THEIR OWN self-perspective -- self-report integrity, nobody fills it out on
    // someone else's behalf, matching the instrument's own single-rater design for that half.
    const BLD_TNA_MANAGEMENT_ROLES = { owner: true, office: true };
    if (resource === 'bld_tna' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnbuild');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const r = await fetch(rest('bld_tna_assessments?license_hash=eq.' + enc(licHash) +
        '&select=subject_employee_id,perspective,assessor_employee_id,responses,disc_responses,disc_profile,submitted_at,updated_at'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      let out = rows || [];
      if (!BLD_TNA_MANAGEMENT_ROLES[session.role]) {
        out = out.filter((r) => r.subject_employee_id === session.employee_id);
      }
      const data = out.map((r) => ({
        id: r.subject_employee_id + ':' + r.perspective,
        subject_employee_id: r.subject_employee_id, perspective: r.perspective,
        assessor_employee_id: r.assessor_employee_id, responses: r.responses || {},
        disc_responses: r.disc_responses || null, disc_profile: r.disc_profile || null,
        submitted_at: r.submitted_at, updated_at: r.updated_at
      }));
      res.status(200).json({ ok: true, data, provisioned: true });
      return;
    }
    if (resource === 'bld_tna' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnbuild');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const subjectId = String((payload && payload.subject_employee_id) || '').trim();
      const perspective = payload && payload.perspective;
      if (!subjectId || ['self', 'management'].indexOf(perspective) === -1) {
        res.status(400).json({ error: { message: 'bld_tna payload.subject_employee_id and a valid perspective (self|management) are required' } });
        return;
      }
      const isManagement = !!BLD_TNA_MANAGEMENT_ROLES[session.role];
      if (perspective === 'self') {
        if (subjectId !== session.employee_id) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'You can only complete your own self-assessment' } });
          return;
        }
      } else if (!isManagement) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can complete a management assessment' } });
        return;
      }
      const responses = (payload && payload.responses && typeof payload.responses === 'object') ? payload.responses : {};
      // DISC is a self-report communication-style questionnaire by design -- only meaningful
      // attached to the 'self' row, silently dropped off a 'management' write rather than
      // erroring, since a manager assessing someone else's DISC profile isn't a coherent action.
      const discResponses = (perspective === 'self' && payload && payload.disc_responses && typeof payload.disc_responses === 'object') ? payload.disc_responses : null;
      const discProfile = (perspective === 'self' && payload && payload.disc_profile && typeof payload.disc_profile === 'object') ? payload.disc_profile : null;
      const r = await fetch(rest('bld_tna_assessments?on_conflict=license_hash,subject_employee_id,perspective'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairnbuild', subject_employee_id: subjectId, perspective: perspective,
          assessor_employee_id: session.employee_id, responses: responses,
          disc_responses: discResponses, disc_profile: discProfile, updated_at: nowISO()
        })
      });
      // 404/400 here means the table itself doesn't exist yet (PostgREST's "not found in
      // schema cache" shape) -- a real, honest, currently-live state until Michael runs
      // sql/sairnbuild_tna_schema.sql, same as every other new table this session. No
      // isMissingTable() helper exists in this file (that's a *-auth.js-only helper, sd-data.js
      // never had one) -- checking the status code directly instead of importing one.
      if (r.status === 404 || r.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Training needs assessment tracking is not set up yet — run sql/sairnbuild_tna_schema.sql in Supabase first.' } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: { id: subjectId + ':' + perspective, subject_employee_id: subjectId, perspective: perspective, responses: responses, disc_responses: discResponses, disc_profile: discProfile } });
      return;
    }

    // ── SAIRNSENIOR: sen_clients HIPAA MINIMUM-NECESSARY PRIVACY GATE (2026-08-20) ───────────
    // Ground-up app (no prior client-only scaffold to replace, unlike sdn_clients/bld_bids
    // which retrofitted an existing gate onto data that predated it). A client is home-care PHI
    // (name, address, diagnosis, authorized services) -- a caregiver may only ever see clients
    // assigned to them; owner/billing (management) see every client. Same bespoke-branch shape
    // as sdn_clients/bld_bids/bld_tna -- assignee-based visibility, not the generic resource loop.
    // THREE-TIER fix (2026-08-20, this session): the original Phase 1 gate only had a
    // MANAGEMENT/everyone-else binary, which silently narrowed coordinator (and scheduler, not
    // named in Michael's approval either -- same judgment call applied to both, flagged here
    // rather than silently picked) down to the same own-assigned-only view as caregiver. The
    // approved scope was "coordinator = broad caseload visibility" -- a real third tier, not
    // "management" and not "caregiver." No team/caseload-grouping concept exists anywhere in
    // this app, so "broad caseload visibility" is implemented as full agency-wide READ (their
    // effective caseload is the whole roster, absent any per-team structure) -- but NOT
    // reassignment rights, which stay exactly where they were confirmed: management-only.
    const SEN_CLIENT_MANAGEMENT_ROLES = { owner: true, billing: true };
    const SEN_CLIENT_BROAD_READ_ROLES = { owner: true, billing: true, coordinator: true, scheduler: true };
    if (resource === 'sen_clients' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnsenior');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const r = await fetch(rest('sen_clients?license_hash=eq.' + enc(licHash) + '&select=client_id,assigned_employee_id,data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      // Management AND coordinator/scheduler (broad-read tier) see every client. Only a
      // caregiver is scoped to clients assigned to them -- an UNASSIGNED client is
      // management-only-visible too, same minimum-necessary reasoning as every other app's
      // assignment gate.
      let out = rows || [];
      if (!SEN_CLIENT_BROAD_READ_ROLES[session.role]) {
        out = out.filter((r) => r.assigned_employee_id === session.employee_id);
      }
      const data = out.map((r) => Object.assign({ id: r.client_id, assigned_employee_id: r.assigned_employee_id || '' }, r.data));
      res.status(200).json({ ok: true, data, provisioned: true });
      return;
    }
    if (resource === 'sen_clients' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnsenior');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'sen_clients payload.id is required' } }); return; }
      const isManagement = !!SEN_CLIENT_MANAGEMENT_ROLES[session.role];
      const isBroadRead = !!SEN_CLIENT_BROAD_READ_ROLES[session.role];
      const existingR = await fetch(rest('sen_clients?license_hash=eq.' + enc(licHash) + '&client_id=eq.' + enc(payload.id) + '&select=assigned_employee_id'), { headers });
      if (existingR.status === 404 || existingR.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Client tracking is not set up yet — run sql/sairnsenior_clients_schema.sql in Supabase first.' } });
        return;
      }
      const existingRows = await existingR.json();
      if (!existingR.ok) return upstream(res, existingRows);
      const existingRow = Array.isArray(existingRows) && existingRows[0];
      const requestedAssignee = payload.assigned_employee_id !== undefined
        ? (payload.assigned_employee_id || null)
        : (existingRow ? existingRow.assigned_employee_id : null);
      if (!isManagement && isBroadRead) {
        // Coordinator/scheduler (broad-read tier): may edit any client's details, matching
        // their agency-wide read access, but the assignment must stay exactly as it already
        // was (or exactly unassigned for a brand-new client) -- broad visibility for
        // coordination purposes is not the same as authority to assign or reassign a client,
        // which stays management-only regardless of how much this tier can see.
        const currentAssignee = existingRow ? existingRow.assigned_employee_id : null;
        if (requestedAssignee !== currentAssignee) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can assign or reassign a client' } });
          return;
        }
      } else if (!isManagement) {
        // Caregiver (narrow tier): may only touch a client already assigned to them, and a
        // brand-new client self-assigns to them on create -- matches saveClient()'s own
        // client-side logic (the same self-assign-on-create fix already proven correct on
        // SAIRNbuild's bld_bids).
        if (existingRow && existingRow.assigned_employee_id !== session.employee_id) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'This client is not assigned to you' } });
          return;
        }
        if (requestedAssignee !== session.employee_id) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can assign or reassign a client' } });
          return;
        }
      }
      const clientData = Object.assign({}, payload);
      delete clientData.id;
      delete clientData.assigned_employee_id;
      const r = await fetch(rest('sen_clients?on_conflict=license_hash,client_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairnsenior', client_id: String(payload.id),
          assigned_employee_id: requestedAssignee, data: clientData, updated_at: nowISO()
        })
      });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: Object.assign({ id: payload.id, assigned_employee_id: requestedAssignee || '' }, clientData) });
      return;
    }

    // ── SAIRNSENIOR: sen_caregivers (2026-08-20, closing the Phase 1 disclosed gap) ──────────
    // Employment/certification data, not client PHI -- lighter gate than sen_clients.
    // Read: any authenticated employee (scheduling/coordination needs the whole roster).
    // Write: management only (owner/billing) -- caregivers don't self-edit their own cert
    // records through this resource, matching every other app's roster-write pattern.
    if (resource === 'sen_caregivers' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnsenior');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const r = await fetch(rest('sen_caregivers?license_hash=eq.' + enc(licHash) + '&select=caregiver_id,data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const data = (rows || []).map((r) => Object.assign({ id: r.caregiver_id }, r.data));
      res.status(200).json({ ok: true, data, provisioned: true });
      return;
    }
    if (resource === 'sen_caregivers' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnsenior');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!SEN_CLIENT_MANAGEMENT_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can add or edit caregiver records' } });
        return;
      }
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'sen_caregivers payload.id is required' } }); return; }
      const caregiverData = Object.assign({}, payload);
      delete caregiverData.id;
      const r = await fetch(rest('sen_caregivers?on_conflict=license_hash,caregiver_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairnsenior', caregiver_id: String(payload.id),
          data: caregiverData, updated_at: nowISO()
        })
      });
      if (r.status === 404 || r.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Caregiver tracking is not set up yet — run sql/sairnsenior_caregivers_schema.sql in Supabase first.' } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: Object.assign({ id: payload.id }, caregiverData) });
      return;
    }

    // ── SAIRNSENIOR: sen_visits SCHEDULING + EVV (2026-08-20) ────────────────────────────────
    // Assignee-based read gate like sen_clients (caregiver sees only their own visits,
    // management/coordinator/scheduler see all). Write is a FIELD-LEVEL split, not a role-vs-
    // role split like sen_clients: scheduling fields (client, caregiver assignment, scheduled
    // time) are writable by management/coordinator/scheduler -- scheduling IS their job, unlike
    // client (re)assignment which stays management-only. EVV fields (clock in/out, GPS, service
    // notes) are writable ONLY by the assigned caregiver, and only on a visit that already
    // exists -- nobody schedules a visit by clocking into it.
    const SEN_VISIT_SCHEDULER_ROLES = { owner: true, billing: true, coordinator: true, scheduler: true };
    const SEN_VISIT_SCHEDULE_FIELDS = ['client_id', 'client_name', 'scheduled_date', 'scheduled_start', 'scheduled_end'];
    const SEN_VISIT_EVV_FIELDS = ['clock_in_at', 'clock_in_lat', 'clock_in_lng', 'clock_out_at', 'clock_out_lat', 'clock_out_lng', 'services_notes', 'status'];
    if (resource === 'sen_visits' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnsenior');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const r = await fetch(rest('sen_visits?license_hash=eq.' + enc(licHash) + '&select=visit_id,assigned_employee_id,data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      let out = rows || [];
      if (!SEN_VISIT_SCHEDULER_ROLES[session.role]) {
        out = out.filter((r) => r.assigned_employee_id === session.employee_id);
      }
      const data = out.map((r) => Object.assign({ id: r.visit_id, assigned_employee_id: r.assigned_employee_id || '' }, r.data));
      res.status(200).json({ ok: true, data, provisioned: true });
      return;
    }
    if (resource === 'sen_visits' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnsenior');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'sen_visits payload.id is required' } }); return; }
      const isScheduler = !!SEN_VISIT_SCHEDULER_ROLES[session.role];
      const existingR = await fetch(rest('sen_visits?license_hash=eq.' + enc(licHash) + '&visit_id=eq.' + enc(payload.id) + '&select=assigned_employee_id,data'), { headers });
      if (existingR.status === 404 || existingR.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Visit/EVV tracking is not set up yet — run sql/sairnsenior_visits_schema.sql in Supabase first.' } });
        return;
      }
      const existingRows = await existingR.json();
      if (!existingR.ok) return upstream(res, existingRows);
      const existingRow = Array.isArray(existingRows) && existingRows[0];
      let requestedAssignee;
      let visitData;
      if (isScheduler) {
        // Full write of the scheduling shape, including who it's assigned to. EVV fields are
        // NEVER accepted from a scheduler-tier caller, even on an edit -- preserved from
        // whatever the assigned caregiver already recorded, so a scheduler can never forge a
        // clock-in/out. This mirrors the field split, not just a role check.
        requestedAssignee = payload.assigned_employee_id !== undefined ? (payload.assigned_employee_id || null) : (existingRow ? existingRow.assigned_employee_id : null);
        visitData = Object.assign({}, existingRow ? existingRow.data : {});
        SEN_VISIT_SCHEDULE_FIELDS.forEach((f) => { if (payload[f] !== undefined) visitData[f] = payload[f]; });
        // A scheduler MAY set status to 'cancelled' (cancelling a visit is scheduling, not EVV)
        // but may not set any other EVV-controlled status value.
        if (payload.status === 'cancelled') visitData.status = 'cancelled';
        else if (existingRow && existingRow.data && existingRow.data.status) visitData.status = existingRow.data.status;
        else visitData.status = 'scheduled';
      } else {
        // Caregiver: must be the assigned party on an EXISTING visit -- cannot create a new
        // visit (that's scheduling) and cannot touch anyone else's. Only the EVV fields are
        // accepted; the scheduling fields are preserved exactly as they were, regardless of
        // what the payload contains.
        if (!existingRow) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only scheduling staff can create a new visit' } });
          return;
        }
        if (existingRow.assigned_employee_id !== session.employee_id) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'This visit is not assigned to you' } });
          return;
        }
        requestedAssignee = existingRow.assigned_employee_id;
        visitData = Object.assign({}, existingRow.data || {});
        SEN_VISIT_EVV_FIELDS.forEach((f) => { if (payload[f] !== undefined) visitData[f] = payload[f]; });
      }
      const r = await fetch(rest('sen_visits?on_conflict=license_hash,visit_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairnsenior', visit_id: String(payload.id),
          assigned_employee_id: requestedAssignee, data: visitData, updated_at: nowISO()
        })
      });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: Object.assign({ id: payload.id, assigned_employee_id: requestedAssignee || '' }, visitData) });
      return;
    }

    // ── SAIRNSENIOR: sen_claims BILLING (2026-08-20) ─────────────────────────────────────────
    // Management-only (owner/billing), both read and write, no assignee-based visibility --
    // financial/billing data, not clinical assignment data. A caregiver has no legitimate
    // minimum-necessary reason to see claim amounts or payer reimbursement status.
    if (resource === 'sen_claims' && (action === 'read' || action === 'write')) {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnsenior');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!SEN_CLIENT_MANAGEMENT_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can view or manage billing claims' } });
        return;
      }
      if (action === 'read') {
        const r = await fetch(rest('sen_claims?license_hash=eq.' + enc(licHash) + '&select=claim_id,data'), { headers });
        if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
        const rows = await r.json();
        if (!r.ok) return upstream(res, rows);
        const data = (rows || []).map((r) => Object.assign({ id: r.claim_id }, r.data));
        res.status(200).json({ ok: true, data, provisioned: true });
        return;
      }
      // write
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'sen_claims payload.id is required' } }); return; }
      const claimData = Object.assign({}, payload);
      delete claimData.id;
      const r = await fetch(rest('sen_claims?on_conflict=license_hash,claim_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairnsenior', claim_id: String(payload.id),
          data: claimData, updated_at: nowISO()
        })
      });
      if (r.status === 404 || r.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Billing claims tracking is not set up yet — run sql/sairnsenior_claims_schema.sql in Supabase first.' } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: Object.assign({ id: payload.id }, claimData) });
      return;
    }

    // ── SAIRNCARE: alf_clients RESIDENT PRIVACY GATE (2026-08-20) ────────────────────────────
    // Ground-up app (no prior scaffold to replace). A resident record is assisted-living PHI
    // (name, diagnosis, care level, payer type) -- same minimum-necessary reasoning as every
    // other assignment-based gate this session (sd_crm, sdn_clients, bld_bids, sen_clients).
    //
    // REAL FOUR-TIER GATE, not three like sen_clients -- built this way from the start per
    // Michael's confirmed instruction to use SAIRNsenior's already-fixed pattern, extended for
    // a real difference in this app's confirmed role scope (docs/superpowers/specs/2026-08-20-
    // sairncare-v1-scope.md): Activities Coordinator gets READ-ONLY broad roster access with
    // NO clinical or billing write authority at all -- a genuinely different tier than nursing's
    // broad-read-AND-edit (which mirrors sen_clients' coordinator/scheduler tier exactly).
    //   - MANAGEMENT (owner, billing): full read/write/reassign.
    //   - BROAD READ+EDIT (+ nursing): facility-wide read, may edit any resident's details, may
    //     NOT reassign -- same rule sen_clients already proved correct for coordinator/scheduler.
    //   - BROAD READ ONLY (+ activities): facility-wide read, ZERO write access of any kind --
    //     a write attempt from this tier is refused outright, not silently downgraded to
    //     "own-assigned-only" the way the pre-fix sen_clients bug did.
    //   - NARROW (med_aide, caregiver): own-assigned-residents-only, self-assign-on-create --
    //     identical shape to sen_clients' caregiver tier and bld_bids' original fix.
    // NULL assigned_employee_id = unassigned, management-only-visible, same default as every
    // prior app's assignment gate.
    const ALF_MANAGEMENT_ROLES = { owner: true, billing: true };
    const ALF_EDIT_ROLES = { owner: true, billing: true, nursing: true };
    const ALF_READ_ONLY_BROAD_ROLES = { activities: true };
    const ALF_BROAD_READ_ROLES = { owner: true, billing: true, nursing: true, activities: true };
    // Level-of-care history (2026-08-21, Phase 0 item 1) -- management-only write given the
    // direct billing consequence (generateInvoice() prorates a resident's monthly care charge
    // off this exact history), enforced below even for nursing, which can otherwise edit every
    // other resident field. care_level_history is APPEND-ONLY: the server checks the existing
    // array is an unmodified prefix of any incoming array, so past entries can never be
    // rewritten, only added to. sub_tier is meaningful only when level is assisted_living --
    // al1/al2/al3 migrate losslessly into it as {level:'assisted_living', sub_tier:'al1'|'al2'|'al3'}.
    const ALF_CARE_LEVELS = { independent_living: true, assisted_living: true, memory_care: true, skilled_nursing: true };
    const ALF_SUB_TIERS = { al1: true, al2: true, al3: true };
    // ccrc_contract_type (Phase 0 item 2) -- no dedicated write gate requested or added; it
    // follows the same tier as every other resident-record field (management + nursing
    // broad-edit + narrow tier on their own assigned resident), unlike care_level_history above.
    const ALF_CCRC_TYPES = { not_ccrc: true, lifecare: true, fee_for_service: true, modified: true, equity: true };
    if (resource === 'alf_clients' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const r = await fetch(rest('alf_clients?license_hash=eq.' + enc(licHash) + '&select=client_id,assigned_employee_id,data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      let out = rows || [];
      if (!ALF_BROAD_READ_ROLES[session.role]) {
        out = out.filter((r) => r.assigned_employee_id === session.employee_id);
      }
      const data = out.map((r) => Object.assign({ id: r.client_id, assigned_employee_id: r.assigned_employee_id || '' }, r.data));
      res.status(200).json({ ok: true, data, provisioned: true });
      return;
    }
    if (resource === 'alf_clients' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (ALF_READ_ONLY_BROAD_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Activities has read-only access to residents' } });
        return;
      }
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'alf_clients payload.id is required' } }); return; }
      const isManagement = !!ALF_MANAGEMENT_ROLES[session.role];
      const isBroadEdit = !!ALF_EDIT_ROLES[session.role];
      const existingR = await fetch(rest('alf_clients?license_hash=eq.' + enc(licHash) + '&client_id=eq.' + enc(payload.id) + '&select=assigned_employee_id,data'), { headers });
      if (existingR.status === 404 || existingR.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Resident tracking is not set up yet — run sql/sairncare_clients_schema.sql in Supabase first.' } });
        return;
      }
      const existingRows = await existingR.json();
      if (!existingR.ok) return upstream(res, existingRows);
      const existingRow = Array.isArray(existingRows) && existingRows[0];
      const existingClientData = existingRow ? (existingRow.data || {}) : null;
      const existingHistory = (existingClientData && Array.isArray(existingClientData.care_level_history)) ? existingClientData.care_level_history : [];
      // Resolve care_level_history BEFORE the role checks below so a rejected level-of-care
      // change never falls through and gets silently accepted as a same-tier field edit.
      let careLevelHistory = existingHistory;
      if (payload.care_level_history !== undefined) {
        if (!isManagement) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can change a resident’s level of care' } });
          return;
        }
        const incoming = payload.care_level_history;
        if (!Array.isArray(incoming) || incoming.length < existingHistory.length) {
          res.status(400).json({ error: { message: 'care_level_history can only be appended to, never edited or shortened' } });
          return;
        }
        for (let i = 0; i < existingHistory.length; i++) {
          if (JSON.stringify(incoming[i]) !== JSON.stringify(existingHistory[i])) {
            res.status(400).json({ error: { message: 'care_level_history entries cannot be modified once recorded' } });
            return;
          }
        }
        const newEntries = incoming.slice(existingHistory.length);
        for (let i = 0; i < newEntries.length; i++) {
          const entry = newEntries[i];
          if (!entry || !ALF_CARE_LEVELS[entry.level]) {
            res.status(400).json({ error: { message: 'Each care_level_history entry needs a valid level (independent_living, assisted_living, memory_care, or skilled_nursing)' } });
            return;
          }
          if (entry.level === 'assisted_living') {
            if (!ALF_SUB_TIERS[entry.sub_tier]) {
              res.status(400).json({ error: { message: 'assisted_living entries need a sub_tier of al1, al2, or al3' } });
              return;
            }
          } else if (entry.sub_tier) {
            res.status(400).json({ error: { message: 'sub_tier is only meaningful when level is assisted_living' } });
            return;
          }
          if (!entry.effective_date || !/^\d{4}-\d{2}-\d{2}$/.test(entry.effective_date)) {
            res.status(400).json({ error: { message: 'Each care_level_history entry needs a real effective_date (YYYY-MM-DD)' } });
            return;
          }
        }
        // changed_by/changed_at are ALWAYS server-stamped from the real session, never trusted
        // from the client -- same discipline as SAIRNlaw's verified_by.
        const stampedNow = nowISO();
        careLevelHistory = existingHistory.concat(newEntries.map((entry) => ({
          level: entry.level,
          sub_tier: entry.level === 'assisted_living' ? entry.sub_tier : null,
          effective_date: entry.effective_date,
          changed_by: session.employee_id,
          changed_at: stampedNow
        })));
      }
      let ccrcContractType = (existingClientData && existingClientData.ccrc_contract_type !== undefined) ? existingClientData.ccrc_contract_type : 'not_ccrc';
      if (payload.ccrc_contract_type !== undefined) {
        if (!ALF_CCRC_TYPES[payload.ccrc_contract_type]) {
          res.status(400).json({ error: { message: 'ccrc_contract_type must be one of: ' + Object.keys(ALF_CCRC_TYPES).join(', ') } });
          return;
        }
        ccrcContractType = payload.ccrc_contract_type;
      }
      const requestedAssignee = payload.assigned_employee_id !== undefined
        ? (payload.assigned_employee_id || null)
        : (existingRow ? existingRow.assigned_employee_id : null);
      if (!isManagement && isBroadEdit) {
        // Nursing: may edit any resident's details, matching facility-wide clinical
        // oversight, but assignment must stay exactly as it already was -- same rule
        // sen_clients already proved correct for its broad-read tier.
        const currentAssignee = existingRow ? existingRow.assigned_employee_id : null;
        if (requestedAssignee !== currentAssignee) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can assign or reassign a resident' } });
          return;
        }
      } else if (!isManagement) {
        // Med Aide / Caregiver (narrow tier): may only touch a resident already assigned
        // to them, and a brand-new resident self-assigns to them on create.
        if (existingRow && existingRow.assigned_employee_id !== session.employee_id) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'This resident is not assigned to you' } });
          return;
        }
        if (requestedAssignee !== session.employee_id) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can assign or reassign a resident' } });
          return;
        }
      }
      const clientData = Object.assign({}, payload);
      delete clientData.id;
      delete clientData.assigned_employee_id;
      clientData.care_level_history = careLevelHistory;
      clientData.ccrc_contract_type = ccrcContractType;
      // care_level stays a derived flat field for backward-compatible display (badges, careRateFor
      // callers, the AI-context summary) whenever real history exists -- computed here, not trusted
      // from the client, so the two can never drift apart. Pre-migration residents with no history
      // yet keep whatever flat value they already had.
      if (careLevelHistory.length > 0) {
        const lastLevel = careLevelHistory[careLevelHistory.length - 1];
        clientData.care_level = lastLevel.level === 'assisted_living' ? lastLevel.sub_tier : lastLevel.level;
      }
      const r = await fetch(rest('alf_clients?on_conflict=license_hash,client_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairncare', client_id: String(payload.id),
          assigned_employee_id: requestedAssignee, data: clientData, updated_at: nowISO()
        })
      });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: Object.assign({ id: payload.id, assigned_employee_id: requestedAssignee || '' }, clientData) });
      return;
    }

    // ── SAIRNCARE: alf_staff (2026-08-20, closing SAIRNsenior's Phase 1 gap proactively) ─────
    // Employment/certification data, not resident PHI -- lighter gate than alf_clients.
    // Read: any authenticated employee (scheduling/coverage needs the whole roster).
    // Write: management only (owner/billing) -- staff don't self-edit their own cert
    // records through this resource, matching sen_caregivers' identical pattern.
    if (resource === 'alf_staff' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const r = await fetch(rest('alf_staff?license_hash=eq.' + enc(licHash) + '&select=staff_id,data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const data = (rows || []).map((r) => Object.assign({ id: r.staff_id }, r.data));
      res.status(200).json({ ok: true, data, provisioned: true });
      return;
    }
    if (resource === 'alf_staff' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!ALF_MANAGEMENT_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can add or edit staff records' } });
        return;
      }
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'alf_staff payload.id is required' } }); return; }
      const staffData = Object.assign({}, payload);
      delete staffData.id;
      const r = await fetch(rest('alf_staff?on_conflict=license_hash,staff_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairncare', staff_id: String(payload.id),
          data: staffData, updated_at: nowISO()
        })
      });
      if (r.status === 404 || r.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Staff tracking is not set up yet — run sql/sairncare_staff_schema.sql in Supabase first.' } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: Object.assign({ id: payload.id }, staffData) });
      return;
    }

    // ── SAIRNCARE: alf_mar -- Medication Administration Record (2026-08-20) ──────────────────
    // Separate table AND separate gate from alf_clients/alf_staff -- see
    // sql/sairncare_mar_schema.sql's own header for both reasons in full
    // (high-frequency append-only events would blow past alf_clients'
    // 64KB cap; medication data carries scope-of-practice sensitivity that
    // the general resident-edit gate doesn't distinguish). Only owner,
    // nursing, med_aide may touch this resource at all -- billing,
    // caregiver, activities get a real 403, never silent access via the
    // general alf_clients write path. Real research pass (not assumed) run
    // before building this -- no single uniform ALF standard exists for
    // any of these; see SAIRN-ACTIVE-WORK.md for full sourcing.
    const ALF_MAR_ROLES = { owner: true, nursing: true, med_aide: true };
    const ALF_MAR_BROAD_ROLES = { owner: true, nursing: true };
    // medication_order/reconciliation/assessment_refusal are clinical-
    // decision entry types -- owner/nursing only, even though med_aide can
    // read them and can write the other two (routine execution) types.
    const ALF_MAR_ORDER_ROLES = { owner: true, nursing: true };
    const ALF_MAR_ENTRY_TYPES = ['medication_order', 'administration', 'count', 'reconciliation', 'assessment_refusal'];
    if (resource === 'alf_mar' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!ALF_MAR_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Medication records are not available to your role' } });
        return;
      }
      const r = await fetch(rest('alf_mar?license_hash=eq.' + enc(licHash) + '&select=entry_id,resident_id,assigned_employee_id,entry_type,data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      let out = rows || [];
      if (!ALF_MAR_BROAD_ROLES[session.role]) {
        out = out.filter((r) => r.assigned_employee_id === session.employee_id);
      }
      const data = out.map((r) => Object.assign({ id: r.entry_id, resident_id: r.resident_id, entry_type: r.entry_type, assigned_employee_id: r.assigned_employee_id || '' }, r.data));
      res.status(200).json({ ok: true, data, provisioned: true });
      return;
    }
    if (resource === 'alf_mar' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!ALF_MAR_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Medication records are not available to your role' } });
        return;
      }
      if (!payload || !payload.id || !payload.resident_id || !payload.entry_type) {
        res.status(400).json({ error: { message: 'alf_mar payload.id, payload.resident_id, and payload.entry_type are required' } });
        return;
      }
      if (ALF_MAR_ENTRY_TYPES.indexOf(payload.entry_type) === -1) {
        res.status(400).json({ error: { message: 'entry_type must be one of: ' + ALF_MAR_ENTRY_TYPES.join(', ') } });
        return;
      }
      // medication_order/reconciliation/assessment_refusal are clinical-
      // decision entry types -- owner/nursing only, even for a med_aide
      // who is otherwise allowed to write this table (administration and
      // count, the routine execution types, are the only ones med_aide
      // may create).
      if (payload.entry_type !== 'administration' && payload.entry_type !== 'count' && !ALF_MAR_ORDER_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management or nursing can log this entry type' } });
        return;
      }
      // Live-look-up the resident's CURRENT assignment -- never trust a
      // client-supplied assigned_employee_id for this table, same
      // discipline as alf_clients' own write path. This both denormalizes
      // the column for the read-filter above and enforces med_aide's
      // own-assigned-only restriction against real, current data.
      const residentR = await fetch(rest('alf_clients?license_hash=eq.' + enc(licHash) + '&client_id=eq.' + enc(payload.resident_id) + '&select=assigned_employee_id'), { headers });
      if (residentR.status === 404 || residentR.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Resident tracking is not set up yet — run sql/sairncare_clients_schema.sql in Supabase first.' } });
        return;
      }
      const residentRows = await residentR.json();
      if (!residentR.ok) return upstream(res, residentRows);
      const residentRow = Array.isArray(residentRows) && residentRows[0];
      if (!residentRow) { res.status(400).json({ error: { message: 'Unknown resident_id' } }); return; }
      const residentAssignee = residentRow.assigned_employee_id || null;
      if (!ALF_MAR_BROAD_ROLES[session.role] && residentAssignee !== session.employee_id) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'This resident is not assigned to you' } });
        return;
      }
      // Append-only integrity for the real event-log types: reject reusing
      // an id already recorded as this entry_type, rather than silently
      // overwriting a past administration/count record. medication_order
      // is deliberately excluded -- it's a real mutable-in-place order
      // (edit/discontinue), same upsert shape as alf_clients itself.
      if (payload.entry_type !== 'medication_order') {
        const existingR = await fetch(rest('alf_mar?license_hash=eq.' + enc(licHash) + '&entry_id=eq.' + enc(String(payload.id)) + '&select=id'), { headers });
        const existingRows = existingR.ok ? await existingR.json() : [];
        if (Array.isArray(existingRows) && existingRows.length > 0) {
          res.status(409).json({ error: { code: 'ALREADY_RECORDED', message: 'This entry has already been recorded and cannot be overwritten' } });
          return;
        }
      }
      const marData = Object.assign({}, payload);
      delete marData.id; delete marData.resident_id; delete marData.entry_type; delete marData.assigned_employee_id;
      const r = await fetch(rest('alf_mar?on_conflict=license_hash,entry_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairncare', entry_id: String(payload.id), resident_id: String(payload.resident_id),
          assigned_employee_id: residentAssignee, entry_type: payload.entry_type, data: marData, updated_at: nowISO()
        })
      });
      if (r.status === 404 || r.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'MAR tracking is not set up yet — run sql/sairncare_mar_schema.sql in Supabase first.' } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: Object.assign({ id: payload.id, resident_id: payload.resident_id, entry_type: payload.entry_type, assigned_employee_id: residentAssignee || '' }, marData) });
      return;
    }

    // ── SAIRNCARE: alf_billing -- private-pay + state-gated Medicaid HCBS (2026-08-20) ────────
    // Management only (owner, billing) -- financial data, not clinical, no assignee-based
    // visibility at all, same simplification sen_claims already established. Reuses
    // ALF_MANAGEMENT_ROLES from the alf_clients block above rather than redeclaring it.
    // room_board_amount and care_amount/hcbs_claim_amount stay separate fields end to end
    // (never summed server-side into one figure) -- see sql/sairncare_billing_schema.sql's
    // header for why: Medicaid HCBS never covers room/board, only the care portion.
    // entry_id is stable per resident+month (client sends the same id to regenerate/correct
    // a month's invoice) -- a real mutable record, not an append-only log like alf_mar.
    if (resource === 'alf_billing' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!ALF_MANAGEMENT_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Billing is not available to your role' } });
        return;
      }
      const r = await fetch(rest('alf_billing?license_hash=eq.' + enc(licHash) + '&select=entry_id,resident_id,data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const data = (rows || []).map((r) => Object.assign({ id: r.entry_id, resident_id: r.resident_id }, r.data));
      res.status(200).json({ ok: true, data, provisioned: true });
      return;
    }
    if (resource === 'alf_billing' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!ALF_MANAGEMENT_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Billing is not available to your role' } });
        return;
      }
      if (!payload || !payload.id || !payload.resident_id) {
        res.status(400).json({ error: { message: 'alf_billing payload.id and payload.resident_id are required' } });
        return;
      }
      const billingData = Object.assign({}, payload);
      delete billingData.id; delete billingData.resident_id;
      const r = await fetch(rest('alf_billing?on_conflict=license_hash,entry_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairncare', entry_id: String(payload.id), resident_id: String(payload.resident_id),
          data: billingData, updated_at: nowISO()
        })
      });
      if (r.status === 404 || r.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Billing tracking is not set up yet — run sql/sairncare_billing_schema.sql in Supabase first.' } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: Object.assign({ id: payload.id, resident_id: payload.resident_id }, billingData) });
      return;
    }

    // ── SAIRNCARE: alf_incidents -- Compliance/Incident Reporting (2026-08-20) ───────────────
    // Real research pass run before building (no code that pass) -- no single federal or
    // uniform ALF incident-reporting standard exists; deadlines vary by state (real sourced
    // examples: VA 24hr, MA 24hr, CA 7 days, FL 15 days, WA initial+5-day-followup), categories
    // converge much more (falls w/ injury, med errors, elopement, abuse/neglect allegations,
    // unexplained injury, unexpected death/hospitalization, behavioral incidents) -- see
    // sql/sairncare_incidents_schema.sql's own header and SAIRN-ACTIVE-WORK.md for full sourcing.
    // ASYMMETRIC gate, a deliberately different shape from every other alf_ resource this
    // session: ANY authenticated employee may CREATE a new report (mandatory-reporting-by-
    // whoever-witnessed-it, gating this would discourage reporting) but only management/
    // nursing/billing may READ the log or UPDATE an existing report afterward -- the original
    // filer cannot go back and alter their own submission once it exists.
    const ALF_INCIDENT_READ_ROLES = { owner: true, nursing: true, billing: true };
    if (resource === 'alf_incidents' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!ALF_INCIDENT_READ_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'The incident log is not available to your role' } });
        return;
      }
      const r = await fetch(rest('alf_incidents?license_hash=eq.' + enc(licHash) + '&select=entry_id,resident_id,data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const data = (rows || []).map((r) => Object.assign({ id: r.entry_id, resident_id: r.resident_id }, r.data));
      res.status(200).json({ ok: true, data, provisioned: true });
      return;
    }
    if (resource === 'alf_incidents' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'alf_incidents payload.id is required' } }); return; }
      const existingR = await fetch(rest('alf_incidents?license_hash=eq.' + enc(licHash) + '&entry_id=eq.' + enc(String(payload.id)) + '&select=id'), { headers });
      if (existingR.status === 404 || existingR.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Incident tracking is not set up yet — run sql/sairncare_incidents_schema.sql in Supabase first.' } });
        return;
      }
      const existingRows = existingR.ok ? await existingR.json() : [];
      const alreadyExists = Array.isArray(existingRows) && existingRows.length > 0;
      // Any authenticated employee may file a brand-new report. Once it exists, only
      // management/nursing/billing may update it (follow-up notes, status, state-reported
      // tracking) -- the filer's own write access ends the moment their report is saved.
      if (alreadyExists && !ALF_INCIDENT_READ_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management, nursing, or billing can update an incident report after it is filed' } });
        return;
      }
      const incidentData = Object.assign({}, payload);
      delete incidentData.id; delete incidentData.resident_id;
      const r = await fetch(rest('alf_incidents?on_conflict=license_hash,entry_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairncare', entry_id: String(payload.id), resident_id: payload.resident_id ? String(payload.resident_id) : null,
          data: incidentData, updated_at: nowISO()
        })
      });
      if (r.status === 404 || r.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Incident tracking is not set up yet — run sql/sairncare_incidents_schema.sql in Supabase first.' } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: Object.assign({ id: payload.id, resident_id: payload.resident_id || '' }, incidentData) });
      return;
    }

    // ── SAIRNCARE: alf_activities -- calendar + attendance (2026-08-20) ──────────────────────
    // Broad-read (any authenticated employee, same reasoning as SAIRNsenior's Compliance
    // panel treating operational data as non-PHI), narrow-write (owner + activities only --
    // planning/running activities is the Activities Coordinator's own real job, the same
    // scope-of-practice reasoning that shaped alf_mar in the other direction).
    const ALF_ACTIVITIES_WRITE_ROLES = { owner: true, activities: true };
    if (resource === 'alf_activities' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const r = await fetch(rest('alf_activities?license_hash=eq.' + enc(licHash) + '&select=entry_id,data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const data = (rows || []).map((r) => Object.assign({ id: r.entry_id }, r.data));
      res.status(200).json({ ok: true, data, provisioned: true });
      return;
    }
    if (resource === 'alf_activities' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!ALF_ACTIVITIES_WRITE_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management or the Activities Coordinator can manage the activities calendar' } });
        return;
      }
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'alf_activities payload.id is required' } }); return; }
      const activityData = Object.assign({}, payload);
      delete activityData.id;
      const r = await fetch(rest('alf_activities?on_conflict=license_hash,entry_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairncare', entry_id: String(payload.id), data: activityData, updated_at: nowISO()
        })
      });
      if (r.status === 404 || r.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Activities tracking is not set up yet — run sql/sairncare_activities_schema.sql in Supabase first.' } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: Object.assign({ id: payload.id }, activityData) });
      return;
    }

    // ── SAIRNCARE: alf_facility FACILITY PROFILE + LICENSING JURISDICTION (2026-08-21) ───────
    // See sql/sairncare_facility_schema.sql for why this moved off localStorage at all, and why
    // it is keyed by facility_id rather than license_hash alone (a CCRC campus holds more than
    // one license -- an SNF is separately licensed from the AL units it shares a campus with in
    // most states, under different statutes with different reporting rules).
    //
    // TWO-TIER GATE, with a REDACTION on read rather than a flat refusal:
    //   - WRITE: management only (owner, billing). A licensing state and a rate card are
    //     facility business facts, not clinical ones -- nursing holds facility-wide clinical
    //     edit authority and still has no business changing what the facility bills.
    //   - READ: any authenticated employee, BUT the rate card is stripped server-side for
    //     anyone outside management. Everyone genuinely needs the non-financial half (which
    //     licensing state this is, what the controlled-substance count policy is, what the
    //     incident-reporting deadline is -- a Med Aide running a narcotic count needs exactly
    //     that); nobody outside management needs the room-and-board rate. Same
    //     minimum-necessary reasoning that keeps alf_billing management-only, applied at field
    //     level instead of resource level because the non-financial half IS needed facility-wide.
    //
    // WHY THE REDACTION IS SAFE AGAINST A ROUND-TRIP WIPE: this client reads a record and writes
    // the whole object back, so a redacted read followed by a write would erase the rate card --
    // the exact silent-data-loss shape worth checking for here. It cannot happen, because write
    // is management-only and management's read is never redacted, so no caller can ever hold a
    // stripped copy AND be allowed to save it. If write is ever widened, this stops being true.
    const ALF_FACILITY_RATE_FIELDS = ['roomboard_rate', 'il_rate', 'al1_rate', 'al2_rate', 'al3_rate', 'mc_rate', 'snf_rate'];
    // Real USPS list, 50 states + DC, validated server-side so licensing_state can actually be
    // trusted by the compliance-rules engine later -- unlike this app's two pre-existing
    // free-text state-ish fields (the incident-deadline string and the HCBS waiver box), which
    // cannot be. Deliberately the FULL list, not just the four states the rules engine seeds on:
    // restricting input to OH/IN/MI/PA would encode a limit that does not exist in reality. An
    // unseeded state gets an honest "no rules loaded" from the engine, never silent coverage.
    const ALF_US_STATES = { AL:1,AK:1,AZ:1,AR:1,CA:1,CO:1,CT:1,DE:1,DC:1,FL:1,GA:1,HI:1,ID:1,IL:1,IN:1,IA:1,KS:1,KY:1,LA:1,ME:1,MD:1,MA:1,MI:1,MN:1,MS:1,MO:1,MT:1,NE:1,NV:1,NH:1,NJ:1,NM:1,NY:1,NC:1,ND:1,OH:1,OK:1,OR:1,PA:1,RI:1,SC:1,SD:1,TN:1,TX:1,UT:1,VT:1,VA:1,WA:1,WV:1,WI:1,WY:1 };
    if (resource === 'alf_facility' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const r = await fetch(rest('alf_facility?license_hash=eq.' + enc(licHash) + '&select=facility_id,data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const canSeeRates = !!ALF_MANAGEMENT_ROLES[session.role];
      const data = (rows || []).map((row) => {
        const out = Object.assign({ id: row.facility_id }, row.data);
        if (!canSeeRates) ALF_FACILITY_RATE_FIELDS.forEach((f) => { delete out[f]; });
        return out;
      });
      res.status(200).json({ ok: true, data, provisioned: true, rates_visible: canSeeRates });
      return;
    }
    if (resource === 'alf_facility' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!ALF_MANAGEMENT_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can change the facility profile' } });
        return;
      }
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'alf_facility payload.id is required' } }); return; }
      const facilityData = Object.assign({}, payload);
      delete facilityData.id;
      // An EMPTY licensing_state is allowed on purpose -- a facility that has not filled it in
      // yet is a real state of the world, and refusing the whole save would block unrelated
      // profile edits. A NON-EMPTY one that is not a real USPS code is refused outright rather
      // than stored, because a stored-but-wrong state is precisely what a rules engine would go
      // on to trust.
      if (facilityData.licensing_state !== undefined) {
        const wantState = String(facilityData.licensing_state || '').trim().toUpperCase();
        if (wantState && !ALF_US_STATES[wantState]) {
          res.status(400).json({ error: { code: 'BAD_STATE', message: 'licensing_state must be a two-letter US state or DC code' } });
          return;
        }
        facilityData.licensing_state = wantState;
      }
      const r = await fetch(rest('alf_facility?on_conflict=license_hash,facility_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairncare', facility_id: String(payload.id), data: facilityData, updated_at: nowISO()
        })
      });
      if (r.status === 404 || r.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'The facility profile is not set up yet — run sql/sairncare_facility_schema.sql in Supabase first.' } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: Object.assign({ id: payload.id }, facilityData) });
      return;
    }

    // ── SAIRNCARE: alf_signals -- passive-monitoring signal log (2026-08-21, Phase 0 item 3) ─
    // See sql/sairncare_signals_schema.sql for the full reasoning. Append-only, same integrity
    // rule as alf_mar's event-log entry types (409 on a reused id, never a silent overwrite).
    // NO risk_score, NO derived indicator of any kind -- read returns the raw rows plus a
    // {have, need} COVERAGE contract only: have = how many of ALF_SIGNAL_TYPES actually have at
    // least one real row for this facility, need = ALF_SIGNAL_TYPES.length. Both computed live
    // from real rows every time, never hardcoded, never a stand-in for an actual risk score.
    // WRITE is management-only for now -- no real monitoring device or integration exists
    // anywhere in this app yet, so there is no real caller to grant broader access to; this is
    // a narrower default than alf_mar's, a judgment call logged here rather than left silent,
    // and should be revisited the day a real device/integration is actually wired up.
    // READ is facility-wide for any authenticated employee, matching alf_activities' precedent
    // for non-clinical-decision, broadly-relevant data.
    const ALF_SIGNAL_TYPES = ['fall_detection', 'bed_exit', 'wandering_alert', 'activity_baseline'];
    if (resource === 'alf_signals' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const r = await fetch(rest('alf_signals?license_hash=eq.' + enc(licHash) + '&select=entry_id,resident_id,signal_type,data,recorded_at'), { headers });
      if (r.status === 404 || r.status === 400) {
        res.status(200).json({ ok: true, data: [], provisioned: false, coverage: { have: 0, need: ALF_SIGNAL_TYPES.length } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const rowList = rows || [];
      const data = rowList.map((r) => Object.assign({ id: r.entry_id, resident_id: r.resident_id, signal_type: r.signal_type, recorded_at: r.recorded_at }, r.data));
      const typesPresent = {};
      rowList.forEach((r) => { typesPresent[r.signal_type] = true; });
      const have = ALF_SIGNAL_TYPES.filter((t) => typesPresent[t]).length;
      res.status(200).json({ ok: true, data, provisioned: true, coverage: { have: have, need: ALF_SIGNAL_TYPES.length } });
      return;
    }
    if (resource === 'alf_signals' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!ALF_MANAGEMENT_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can record a monitoring signal' } });
        return;
      }
      if (!payload || !payload.id || !payload.resident_id || !payload.signal_type) {
        res.status(400).json({ error: { message: 'alf_signals payload.id, payload.resident_id, and payload.signal_type are required' } });
        return;
      }
      if (ALF_SIGNAL_TYPES.indexOf(payload.signal_type) === -1) {
        res.status(400).json({ error: { message: 'signal_type must be one of: ' + ALF_SIGNAL_TYPES.join(', ') } });
        return;
      }
      const existingR = await fetch(rest('alf_signals?license_hash=eq.' + enc(licHash) + '&entry_id=eq.' + enc(String(payload.id)) + '&select=id'), { headers });
      const existingRows = existingR.ok ? await existingR.json() : [];
      if (Array.isArray(existingRows) && existingRows.length > 0) {
        res.status(409).json({ error: { code: 'ALREADY_RECORDED', message: 'This signal has already been recorded and cannot be overwritten' } });
        return;
      }
      const signalData = Object.assign({}, payload);
      delete signalData.id; delete signalData.resident_id; delete signalData.signal_type;
      const recordedAt = payload.recorded_at || nowISO();
      delete signalData.recorded_at;
      const r = await fetch(rest('alf_signals'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairncare', entry_id: String(payload.id), resident_id: String(payload.resident_id),
          signal_type: payload.signal_type, data: signalData, recorded_at: recordedAt
        })
      });
      if (r.status === 404 || r.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Signal tracking is not set up yet — run sql/sairncare_signals_schema.sql in Supabase first.' } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: Object.assign({ id: payload.id, resident_id: payload.resident_id, signal_type: payload.signal_type, recorded_at: recordedAt }, signalData) });
      return;
    }

    // ── SAIRNDESIGN: 18 resources (2026-08-07, closing the whole-app sync gap) ─────────────
    // SAIRNdesign shipped Phases 1-4 calling sdnData('write', <bare resource name>, ...) at
    // ~27 call sites, but no 'sairndesign'-scoped resource was ever added to RESOURCES above --
    // every one of those writes has been hitting the 400 guard and silently falling back to
    // local-only storage since Phase 1. Every resource here is prefixed sdn_, not just the two
    // that would otherwise collide with SAIRNscape's bare 'schedule'/'invoices' below -- see
    // sql/sairndesign_data_schema.sql's own header for the full reasoning. None of these carry a
    // required parent-id column (unlike grd_*'s property_id) -- SAIRNdesign has no server-side
    // filtered read anywhere; every client read is "give me the whole array for this license,"
    // filtered client-side after, so the parent id living inside payload/data (same as every
    // other field) is sufficient. Same read/write shape as sd_slabs above (payload.id only, no
    // second required field) for exactly that reason.
    const SDN_RESOURCES = {
      sdn_clients: 'client_id', sdn_projects: 'project_id', sdn_specitems: 'specitem_id',
      sdn_proposals: 'proposal_id', sdn_vendors: 'vendor_id', sdn_samplerequests: 'samplerequest_id',
      sdn_team: 'team_id', sdn_moodboards: 'moodboard_id', sdn_colorcodes: 'colorcode_id',
      sdn_pos: 'po_id', sdn_invoices: 'invoice_id', sdn_timeentries: 'timeentry_id',
      sdn_schedule: 'schedule_id', sdn_samples: 'sample_id', sdn_contracts: 'contract_id',
      sdn_referrals: 'referral_id', sdn_discounts: 'discount_id', sdn_roomdims: 'roomdim_id'
    };
    if (SDN_RESOURCES[resource] && action === 'read') {
      const idCol = SDN_RESOURCES[resource];
      const r = await fetch(rest(resource + '?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (SDN_RESOURCES[resource] && action === 'write') {
      const idCol = SDN_RESOURCES[resource];
      if (!payload || payload.id === undefined || payload.id === null || payload.id === '') {
        res.status(400).json({ error: { message: resource + ' payload.id is required' } });
        return;
      }
      const r = await fetch(rest(resource + '?on_conflict=license_hash,' + idCol), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairndesign', [idCol]: String(payload.id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNdesign data tables are not set up yet — run sql/sairndesign_data_schema.sql in Supabase first.' } }); return; }
      // Invoice-per-proposal uniqueness (2026-08-10): once
      // sql/sairndesign_invoice_uniqueness.sql's index exists, a genuinely
      // new invoice for an already-invoiced proposal_id fails here with
      // Postgres 23505 (PostgREST maps it to 409) -- map it to a clean,
      // real rejection instead of the generic upstream() 502. Scoped to
      // sdn_invoices only: no other SDN_RESOURCES table has this
      // constraint, so this branch can never misfire for them. Inert (this
      // branch is simply unreachable) until that migration actually runs.
      if (r.status === 409 && resource === 'sdn_invoices') {
        res.status(409).json({ error: { code: 'DUPLICATE_INVOICE', message: 'This proposal already has an invoice.' } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }

    // ── SAIRNLEGACY: 36 resources (2026-08-07, same sync-gap fix as SAIRNdesign) ────────────
    // sairnlegacy.html already called every one of these leg_-prefixed at 55 call sites across
    // its 26 panels since Phase 1 -- unlike SAIRNdesign, no client-side resource renaming was
    // needed here, only this missing backend half. Same generic parametrized read/write pair as
    // SDN_RESOURCES above (one pair covering all 36, not 36 copy-pasted blocks) -- see that
    // block's own comment for why. See sql/sairnlegacy_data_schema.sql for the id-column naming
    // rule (mechanical singularization, not a bespoke name per table -- also logged there).
    const LEG_RESOURCES = {
      leg_aftercare: 'aftercare_id', leg_bookings: 'booking_id', leg_cases: 'case_id',
      leg_catererorders: 'catererorder_id', leg_caterers: 'caterer_id', leg_certs: 'cert_id',
      leg_clergy: 'clergy_id', leg_clergybookings: 'clergybooking_id', leg_cremations: 'cremation_id',
      leg_custodylog: 'custodylog_id', leg_deathrecords: 'deathrecord_id', leg_dispatches: 'dispatch_id',
      leg_documents: 'document_id', leg_facilities: 'facility_id', leg_floristorders: 'floristorder_id',
      leg_florists: 'florist_id', leg_gplservices: 'gplservice_id', leg_guestbook: 'guestbook_id',
      leg_insurance: 'insurance_id', leg_invoices: 'invoice_id', leg_keepsakeorders: 'keepsakeorder_id',
      leg_keepsakes: 'keepsake_id', leg_liverybookings: 'liverybooking_id', leg_liveryvendors: 'liveryvendor_id',
      leg_maintenance: 'maintenance_id', leg_memorials: 'memorial_id', leg_merch_catalog: 'merch_catalog_id',
      leg_merch_units: 'merch_unit_id', leg_monuments: 'monument_id', leg_obituaries: 'obituary_id',
      leg_petcases: 'petcase_id', leg_plots: 'plot_id', leg_preneed: 'preneed_id',
      leg_processions: 'procession_id', leg_tributes: 'tribute_id', leg_vehicles: 'vehicle_id'
    };
    if (LEG_RESOURCES[resource] && action === 'read') {
      const r = await fetch(rest(resource + '?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (LEG_RESOURCES[resource] && action === 'write') {
      const idCol = LEG_RESOURCES[resource];
      if (!payload || payload.id === undefined || payload.id === null || payload.id === '') {
        res.status(400).json({ error: { message: resource + ' payload.id is required' } });
        return;
      }
      // Reservation-lock hard gate (2026-08-10): the one transition on this
      // resource that can't be a blind merge -- two staff on two devices,
      // each holding a stale local copy showing 'Available', could otherwise
      // both pass their own client-side check and both upsert 'Reserved' for
      // different cases, silently overwriting each other (real risk: the
      // same physical casket/urn promised to two grieving families). Every
      // OTHER transition on this resource (release, mark Sold, catalog/unit
      // creation) keeps the blind-upsert semantics below -- this is a
      // narrow, resource+transition-specific gate. See
      // docs/superpowers/specs/2026-08-10-sairnlegacy-reservation-lock-design.md
      if (resource === 'leg_merch_units' && payload.status === 'Reserved') {
        const r = await fetch(rest(
          'leg_merch_units?license_hash=eq.' + enc(licHash) +
          '&merch_unit_id=eq.' + enc(String(payload.id)) +
          '&data->>status=eq.Available'
        ), {
          method: 'PATCH',
          headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
          body: JSON.stringify({ data: payload, updated_at: nowISO() })
        });
        if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlegacy data tables are not set up yet — run sql/sairnlegacy_data_schema.sql in Supabase first.' } }); return; }
        const rows = await r.json();
        if (!r.ok) return upstream(res, rows);
        if (!Array.isArray(rows) || rows.length === 0) {
          res.status(409).json({ error: { code: 'ALREADY_RESERVED', message: 'This unit could not be reserved -- it may have already been reserved or sold by someone else, or it has not finished syncing to the server yet.' } });
          return;
        }
        res.status(200).json({ ok: true, data: rows[0].data });
        return;
      }
      const r = await fetch(rest(resource + '?on_conflict=license_hash,' + idCol), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairnlegacy', [idCol]: String(payload.id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlegacy data tables are not set up yet — run sql/sairnlegacy_data_schema.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }

    // ── SAIRNDENTAL: 12 resources (2026-08-10) -- same generic read/write
    // pair as LEG_RESOURCES/SDN_RESOURCES above. sc_denial/sc_ar/
    // sc_revenue's data shape and KPI math are reused from SAIRNcode per
    // docs/superpowers/specs/2026-08-10-sairndental-design.md §6, but the
    // storage keys here are dnt_denial/dnt_ar/dnt_revenue -- a genuinely
    // separate namespace, not a shared table with SAIRNcode's own sc_
    // resources (checked for collision against every existing resource
    // string in this file before being added; none found). ──
    const DNT_RESOURCES = {
      dnt_patients: 'patient_id', dnt_providers: 'provider_id', dnt_operatories: 'operatory_id',
      dnt_provider_hours: 'provider_hour_id', dnt_procedure_types: 'procedure_type_id',
      dnt_coverage_rules: 'coverage_rule_id', dnt_charges: 'charge_id',
      dnt_payments: 'payment_id', dnt_denial: 'denial_id', dnt_ar: 'ar_id', dnt_revenue: 'revenue_id',
      dnt_referrals: 'referral_id'
    };
    if (DNT_RESOURCES[resource] && action === 'read') {
      const r = await fetch(rest(resource + '?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (DNT_RESOURCES[resource] && action === 'write') {
      const idCol = DNT_RESOURCES[resource];
      if (!payload || payload.id === undefined || payload.id === null || payload.id === '') {
        res.status(400).json({ error: { message: resource + ' payload.id is required' } });
        return;
      }
      const r = await fetch(rest(resource + '?on_conflict=license_hash,' + idCol), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairndental', [idCol]: String(payload.id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNdental data tables are not set up yet — run sql/sairndental_data_schema.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }

    // dnt_settings (2026-08-10) -- own dedicated handler, not the generic
    // DNT_RESOURCES block above, because booking_slug is a real promoted
    // column (unique index, resolved by the public booking endpoints)
    // that the generic block's payload doesn't populate. See
    // docs/superpowers/specs/2026-08-10-sairndental-availability-booking-design.md §1.
    if (resource === 'dnt_settings' && action === 'read') {
      const r = await fetch(rest('dnt_settings?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'dnt_settings' && action === 'write') {
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'dnt_settings payload.id is required' } }); return; }
      const r = await fetch(rest('dnt_settings?on_conflict=license_hash,settings_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairndental', settings_id: String(payload.id), data: payload,
          booking_slug: payload.booking_slug || null, updated_at: nowISO()
        })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNdental data tables are not set up yet — run sql/sairndental_data_schema.sql and sql/sairndental_availability_booking_schema.sql in Supabase first.' } }); return; }
      if (r.status === 409) { res.status(409).json({ error: { code: 'SLUG_TAKEN', message: 'This booking link is already in use by another practice — choose a different one.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }

    // dnt_complaints (2026-08-12) -- own dedicated handler, not the
    // generic DNT_RESOURCES block above, for two reasons: (1)
    // access_token is a real promoted column (unique index), same
    // reasoning as dnt_settings.booking_slug, resolved directly by
    // the public complaint endpoints; (2) this resource is READ-ONLY
    // through this generic Bearer-license path -- action:'write' is
    // explicitly rejected below, on purpose. All real mutations (new
    // complaint, patient reply, owner reply/resolve) go through the
    // dedicated read-then-append-write endpoints in
    // api/sairndental/public-complaint-submit.js,
    // public-complaint-thread.js, and complaint-respond.js instead,
    // specifically to avoid the exact race a full-record client
    // overwrite here would allow (a patient's reply landing between
    // this staff app's read and its write, silently dropped). See
    // docs/superpowers/specs/2026-08-12-sairndental-complaint-design.md §0/§1.
    if (resource === 'dnt_complaints' && action === 'read') {
      const r = await fetch(rest('dnt_complaints?license_hash=eq.' + enc(licHash) + '&select=data,updated_at&order=updated_at.desc'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => Object.assign({}, x.data, { updated_at: x.updated_at })), provisioned: true });
      return;
    }
    if (resource === 'dnt_complaints' && action === 'write') {
      res.status(400).json({ error: { code: 'READ_ONLY_RESOURCE', message: 'dnt_complaints cannot be written via this generic endpoint -- use api/sairndental/complaint-respond.js instead.' } });
      return;
    }

    // dnt_appointments (2026-08-10): promoted real columns
    // (provider_id/operatory_id/start_time/end_time/status), not the
    // generic DNT_RESOURCES block -- see
    // docs/superpowers/specs/2026-08-10-sairndental-availability-booking-design.md
    // §1 for why this resource specifically needs real columns (the
    // EXCLUDE constraints in sql/sairndental_availability_booking_schema.sql
    // can't check a jsonb-buried value). Every write -- staff-created or
    // self-scheduled via the separate public-book.js endpoint -- goes
    // through this same handler, so the double-booking protection covers
    // both paths, not just the public one.
    if (resource === 'dnt_appointments' && action === 'read') {
      const r = await fetch(rest('dnt_appointments?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'dnt_appointments' && action === 'write') {
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'dnt_appointments payload.id is required' } }); return; }
      // Security fix (2026-08-12): public-book.js already validates payload.photos
      // via validatePhotosPayload() before it ever reaches this table -- but this
      // generic write path is the SAME endpoint the authenticated staff app uses
      // for every other appointment write, and it applied zero validation of its
      // own. sairndental.html's rPending() renders each photo's data URL directly
      // into an <img src="..."> attribute unescaped (safe only because the public
      // path's regex forbids ", <, > from ever appearing) -- so a caller holding a
      // valid license key could reach this handler directly with a crafted
      // payload.photos entry and get a stored-XSS payload rendered into another
      // staff member's (including the owner's) authenticated session. Applying the
      // same validation here closes the gap at its source, independent of the
      // render-side H() fix in sairndental.html.
      const photosCheck = validatePhotosPayload(payload.photos);
      if (!photosCheck.ok) { res.status(400).json({ error: { code: photosCheck.code, message: photosCheck.message } }); return; }
      const r = await fetch(rest('dnt_appointments?on_conflict=license_hash,appointment_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairndental', appointment_id: String(payload.id), data: payload,
          provider_id: payload.provider_id || null, operatory_id: payload.operatory_id || null,
          start_time: payload.start_time || null, end_time: payload.end_time || null, status: payload.status || null,
          updated_at: nowISO()
        })
      });
      // 2026-08-11 fix: a bare `r.status === 400` used to be classified as
      // NOT_PROVISIONED unconditionally -- wrong, and it masked a real bug
      // (found live: an exclusion_violation from the EXCLUDE constraints
      // was itself coming back as 400, not 409, and got silently
      // mislabeled as "tables not set up" instead of the real conflict).
      // Read the real body first and only call it NOT_PROVISIONED if the
      // message actually says so -- otherwise log and surface the real
      // error via upstream().
      if (r.status === 404) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNdental data tables are not set up yet — run sql/sairndental_data_schema.sql and sql/sairndental_availability_booking_schema.sql in Supabase first.' } }); return; }
      if (r.status === 409 || r.status === 400) {
        const bodyText = await r.text();
        let bodyJson = null; try { bodyJson = JSON.parse(bodyText); } catch (e) {}
        const msg = (bodyJson && (bodyJson.message || bodyJson.details || bodyJson.hint)) || bodyText || '';
        if (/relation .* does not exist|does not exist/i.test(msg) && r.status === 400) {
          res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNdental data tables are not set up yet — run sql/sairndental_data_schema.sql and sql/sairndental_availability_booking_schema.sql in Supabase first.' } });
          return;
        }
        if (/exclusion|dntap_no_provider_overlap|dntap_no_operatory_overlap|duplicate key|unique constraint/i.test(msg)) {
          res.status(409).json({ error: { code: 'SLOT_TAKEN', message: 'This time slot conflicts with an existing appointment for this provider or operatory.' } });
          return;
        }
        console.error('dnt_appointments write error (status ' + r.status + '):', msg);
        res.status(502).json({ error: { message: 'Data store error — try again', detail: msg } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }

    // ── SAIRNlaw trust disbursement server-sync, step 1 (2026-08-16) ──────
    // See sql/sairnlaw_data_schema.sql and
    // docs/superpowers/specs/2026-08-14-sairnlaw-trust-data-schema-design.md.
    // No verifySessionToken/role check on any of these three resources --
    // see that spec's "Correction (2026-08-16)" section for why (sdnData()
    // never sends a session token to this endpoint; auth is the Bearer
    // license key alone, same as grd_jobs).
    // NOTE (2026-08-16, final review finding): these three read routes are
    // live but currently unreachable from the client -- sairnlaw.html has
    // zero sdnData('read',...) calls anywhere (grep-confirmed). Writes are
    // genuinely durable server-side; reads are still localStorage-only, so
    // this is write-through, not full cross-device sync yet. Wiring real
    // client-side reads (with local/server merge semantics) is deferred to
    // a separate future spec, not part of this pass.
    if (resource === 'law_clients' && action === 'read') {
      const r = await fetch(rest('law_clients?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'law_clients' && action === 'write') {
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'law_clients payload.id is required' } }); return; }
      const r = await fetch(rest('law_clients?on_conflict=license_hash,client_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairnlaw', client_id: String(payload.id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlaw data tables are not set up yet — run sql/sairnlaw_data_schema.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'law_matters' && action === 'read') {
      const r = await fetch(rest('law_matters?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'law_matters' && action === 'write') {
      if (!payload || !payload.id || !payload.client_id) { res.status(400).json({ error: { message: 'law_matters payload.id and payload.client_id are required' } }); return; }
      const r = await fetch(rest('law_matters?on_conflict=license_hash,matter_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairnlaw', matter_id: String(payload.id), client_id: String(payload.client_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlaw data tables are not set up yet — run sql/sairnlaw_data_schema.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    // SAIRNlaw deadlines (2026-08-21) -- FIXING A REAL PRE-EXISTING BREAK.
    // sairnlaw.html has called sdnData('write','law_deadlines') since before
    // this change against a resource with no branch here, so production
    // answered 400 while law_matters answered 200. It failed honestly (the
    // client toast says "server sync not yet enabled") but every deadline
    // lived on one browser and was lost with the profile.
    //
    // NOTE FOR THE NEXT PERSON ADDING A RESOURCE: registering the name in
    // api/_resources/<app>.js is NECESSARY BUT NOT SUFFICIENT. A registered
    // name with no branch passes the allowlist and then falls through to
    // "Unsupported action/resource combination" -- which is exactly what
    // law_deadlines returned until this branch existed. The registry split
    // removed the shared-map collision; it did not remove the handler.
    //
    // Same generic shape as the sc_* family: one row per entry, license_hash
    // scoped, jsonb data, keyed on entry_id. Deadlines carry no cross-record
    // invariant that would need a bespoke gate (unlike law_trusttx's balance
    // check), so the plain shape is correct here rather than under-built.
    if (resource === 'law_deadlines' && action === 'read') {
      const r = await fetch(rest('law_deadlines?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'law_deadlines' && action === 'write') {
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'law_deadlines payload.id is required' } }); return; }
      const r = await fetch(rest('law_deadlines?on_conflict=license_hash,entry_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairnlaw', entry_id: String(payload.id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlaw deadline tables are not set up yet \u2014 run sql/sairnlaw_deadline_rules_schema.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'law_trusttx' && action === 'read') {
      const r = await fetch(rest('law_trusttx?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'law_trusttx' && action === 'write') {
      if (!payload || !payload.id || !payload.matter_id || !payload.client_id) { res.status(400).json({ error: { message: 'law_trusttx payload.id, payload.matter_id, and payload.client_id are required' } }); return; }
      if (payload.type !== 'Deposit' && payload.type !== 'Disbursement') { res.status(400).json({ error: { message: "law_trusttx payload.type must be exactly 'Deposit' or 'Disbursement'" } }); return; }
      // Atomic deposit-void balance guard (2026-08-17, step 3a). Voiding a
      // Deposit is the one void that can DECREASE a client's balance (a
      // Disbursement-void only ever increases it, so it stays on the plain
      // upsert below, unguarded, same reasoning as step 2's Deposit-create/
      // void-in-general exemption). Routes through
      // law_check_and_void_deposit() instead of a plain upsert. See
      // docs/superpowers/specs/2026-08-17-sairnlaw-deposit-void-balance-guard-design.md.
      if (payload.status === 'Voided') {
        const r = await fetch(rest('rpc/law_check_and_void_deposit'), {
          method: 'POST',
          headers,
          body: JSON.stringify({
            p_license_hash: licHash, p_trusttx_id: String(payload.id),
            p_voided_reason: payload.voided_reason || null
          })
        });
        if (r.status === 404) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlaw data tables are not set up yet — run sql/sairnlaw_data_schema.sql and sql/sairnlaw_deposit_void_balance_guard.sql in Supabase first.' } }); return; }
        if (r.status === 400) {
          const bodyText = await r.text();
          let bodyJson = null; try { bodyJson = JSON.parse(bodyText); } catch (e) {}
          const msg = (bodyJson && bodyJson.message) || bodyText || '';
          if (/relation .* does not exist|function .* does not exist/i.test(msg)) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlaw data tables are not set up yet — run sql/sairnlaw_data_schema.sql and sql/sairnlaw_deposit_void_balance_guard.sql in Supabase first.' } }); return; }
          if (/^ALREADY_VOIDED/.test(msg)) { res.status(409).json({ error: { code: 'ALREADY_VOIDED', message: 'This transaction has already been voided.' } }); return; }
          if (/^NOT_FOUND/.test(msg)) { res.status(409).json({ error: { code: 'NOT_FOUND', message: 'This transaction could not be found on the server.' } }); return; }
          const balMatch = /VOID_WOULD_NEGATIVE_BALANCE: void of (-?[\d.]+) would leave balance (-?[\d.]+)/.exec(msg);
          if (balMatch) {
            const realBalance = Number(balMatch[2]);
            res.status(409).json({ error: { code: 'VOID_WOULD_NEGATIVE_BALANCE', message: 'Voiding this deposit would leave this client\'s real trust balance at $' + realBalance.toFixed(2) + ' — void rejected.', real_balance: realBalance } });
            return;
          }
          console.error('law_check_and_void_deposit error (status 400):', msg);
          res.status(502).json({ error: { message: 'Data store error — try again', detail: msg } });
          return;
        }
        if (!r.ok) { const rows = await r.json().catch(() => null); return upstream(res, rows); }
        const voidRpcResult = await r.json();
        const voidRow = Array.isArray(voidRpcResult) ? voidRpcResult[0] : voidRpcResult;
        res.status(200).json({ ok: true, data: (voidRow && voidRow.data) ? voidRow.data : payload });
        return;
      }
      // Atomic disbursement check-and-write (2026-08-16, step 2). A NEW
      // Disbursement (not a void -- a void write always carries
      // payload.status==='Voided', which stays on the plain upsert below)
      // routes through law_check_and_insert_disbursement() instead of a
      // plain upsert. That Postgres function takes an advisory lock scoped
      // to (license_hash, client_id), re-sums the client's real balance
      // server-side, and rejects atomically if the disbursement would go
      // negative -- closing the cross-device race saveTrustTransaction()'s
      // own local-only check (sairnlaw.html:2048-2050) cannot close on its
      // own. See docs/superpowers/specs/2026-08-16-sairnlaw-trust-disbursement-atomic-check-design.md.
      if (payload.type === 'Disbursement' && payload.status !== 'Voided') {
        if (payload.amount === undefined || payload.amount === null || Number(payload.amount) <= 0) { res.status(400).json({ error: { message: 'law_trusttx payload.amount is required and must be greater than 0 for a Disbursement' } }); return; }
        const r = await fetch(rest('rpc/law_check_and_insert_disbursement'), {
          method: 'POST',
          headers,
          body: JSON.stringify({
            p_license_hash: licHash, p_trusttx_id: String(payload.id), p_matter_id: String(payload.matter_id),
            p_client_id: String(payload.client_id), p_amount: Number(payload.amount), p_method: payload.method || null,
            p_reference_number: payload.reference_number || null, p_description: payload.description || null,
            p_tx_date: payload.date || null, p_created_at: payload.created_at || nowISO()
          })
        });
        if (r.status === 404) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlaw data tables are not set up yet — run sql/sairnlaw_data_schema.sql and sql/sairnlaw_trust_disbursement_atomic_check.sql in Supabase first.' } }); return; }
        if (r.status === 400) {
          const bodyText = await r.text();
          let bodyJson = null; try { bodyJson = JSON.parse(bodyText); } catch (e) {}
          const msg = (bodyJson && bodyJson.message) || bodyText || '';
          if (/relation .* does not exist|function .* does not exist/i.test(msg)) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlaw data tables are not set up yet — run sql/sairnlaw_data_schema.sql and sql/sairnlaw_trust_disbursement_atomic_check.sql in Supabase first.' } }); return; }
          const balMatch = /INSUFFICIENT_TRUST_BALANCE: disbursement (-?[\d.]+) exceeds balance (-?[\d.]+)/.exec(msg);
          if (balMatch) {
            const reqAmount = Number(balMatch[1]), realBalance = Number(balMatch[2]);
            res.status(409).json({ error: { code: 'INSUFFICIENT_TRUST_BALANCE', message: 'Disbursement of $' + reqAmount.toFixed(2) + ' exceeds this client\'s real trust balance of $' + realBalance.toFixed(2), real_balance: realBalance } });
            return;
          }
          console.error('law_check_and_insert_disbursement error (status 400):', msg);
          res.status(502).json({ error: { message: 'Data store error — try again', detail: msg } });
          return;
        }
        if (!r.ok) { const rows = await r.json().catch(() => null); return upstream(res, rows); }
        const rpcResult = await r.json();
        const row = Array.isArray(rpcResult) ? rpcResult[0] : rpcResult;
        res.status(200).json({ ok: true, data: row ? row.data : payload });
        return;
      }
      const r = await fetch(rest('law_trusttx?on_conflict=license_hash,trusttx_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairnlaw', trusttx_id: String(payload.id), matter_id: String(payload.matter_id), client_id: String(payload.client_id), amount: (payload.amount !== undefined && payload.amount !== null) ? Number(payload.amount) : null, type: payload.type || null, status: payload.status || 'Posted', data: payload, updated_at: nowISO() })
      });
      if (r.status === 404) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlaw data tables are not set up yet — run sql/sairnlaw_data_schema.sql in Supabase first.' } }); return; }
      if (r.status === 400) {
        const bodyText = await r.text();
        let bodyJson = null; try { bodyJson = JSON.parse(bodyText); } catch (e) {}
        const msg = (bodyJson && (bodyJson.message || bodyJson.details || bodyJson.hint)) || bodyText || '';
        if (/relation .* does not exist|does not exist/i.test(msg)) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlaw data tables are not set up yet — run sql/sairnlaw_data_schema.sql in Supabase first.' } }); return; }
        console.error('law_trusttx write error (status 400):', msg);
        res.status(502).json({ error: { message: 'Data store error — try again', detail: msg } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }

    if (isScResource) {
      if (action === 'read') {
        const r = await fetch(rest(resource + '?license_hash=eq.' + enc(licHash) + '&select=entry_id,data&order=created_at.asc'), { headers });
        if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
        const rows = await r.json();
        if (!r.ok) return upstream(res, rows);
        res.status(200).json({ ok: true, data: rows.map(function (row) { return row.data; }), provisioned: true });
        return;
      }
      if (action === 'write') {
        if (!payload || !payload.id) { res.status(400).json({ error: { message: 'payload.id is required' } }); return; }
        // Retention floor guard (2026-08-20, firewall audit layer 26). Only
        // applies to sc_settings; every other SC resource is unaffected.
        // Enforced here rather than in the UI because this value is intended
        // to drive a purge that does not exist yet -- by the time anything
        // acts on it, nobody will remember who typed it, so a below-floor
        // value must never reach storage in the first place.
        if (resource === 'sc_settings' && Object.prototype.hasOwnProperty.call(payload, 'retention_years')) {
          const rv = payload.retention_years;
          const numeric = Number(rv);
          const validIndefinite = rv === 'indefinite';
          const validNumber = Number.isFinite(numeric) && numeric >= SC_RETENTION_FLOOR_YEARS;
          if (!validIndefinite && !validNumber) {
            res.status(400).json({
              error: {
                code: 'RETENTION_BELOW_FLOOR',
                message: 'retention_years must be at least ' + SC_RETENTION_FLOOR_YEARS + ' years, or the string "indefinite".'
              }
            });
            return;
          }
        }
        // Sign-off gate (2026-08-20, Phase 2a hard requirement). Only
        // applies to sc_auth_requests, and only when the write is actually
        // trying to sign off -- setting signedOffBy at all, or moving
        // status to 'submitted'. Every other sc_auth_requests write (create
        // a draft, edit before review, log a payer decision after the fact)
        // is unaffected. Mirrors the delete gate immediately below in this
        // same file, byte for byte in spirit: a client-side "reviewed"
        // checkbox is a UI convenience, never the real boundary -- only a
        // real, currently-valid Compliance Admin session can make a request
        // submission-ready, regardless of what the client claims.
        if (resource === 'sc_auth_requests') {
          const attemptingSignOff = Object.prototype.hasOwnProperty.call(payload, 'signedOffBy') ||
            payload.status === 'submitted';
          if (attemptingSignOff) {
            const arCaller = verifySessionToken(tokenFromRequest(req), licHash, 'sairncode');
            if (!arCaller || arCaller.role !== 'admin') {
              res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only Compliance Admin can sign off a prior-auth request as submission-ready' } });
              return;
            }
            // The server sets signedOffBy from the verified session, not from
            // whatever the client sent -- a forged name in the payload must
            // never end up in the sign-off record.
            payload.signedOffBy = arCaller.employee_id;
            payload.signedOffAt = nowISO();
          }
        }
        const r = await fetch(rest(resource + '?on_conflict=license_hash,entry_id'), {
          method: 'POST',
          headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
          body: JSON.stringify({ license_hash: licHash, app_id: 'sairncode', entry_id: String(payload.id), data: payload, updated_at: nowISO() })
        });
        if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNcode data tables are not set up yet -- run sql/sairncode_data_schema.sql in Supabase first.' } }); return; }
        const rows = await r.json();
        if (!r.ok) return upstream(res, rows);
        res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
        return;
      }
      if (action === 'delete') {
        if (!payload || !payload.id) { res.status(400).json({ error: { message: 'payload.id is required' } }); return; }
        // Server-side RBAC re-check (2026-08-18, same discipline as
        // grd_progress_photos' QC-decision gate, a8afe3e) -- the client's
        // requireAdminForDelete() is a real UI convenience, never the actual
        // authorization boundary. Only a real, currently-valid SAIRNcode
        // admin session token can delete -- a tampered/forged client claim
        // of admin-ness is rejected here regardless of what the UI showed.
        const scCaller = verifySessionToken(tokenFromRequest(req), licHash, 'sairncode');
        if (!scCaller || scCaller.role !== 'admin') {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only Compliance Admin can delete records' } });
          return;
        }
        const r = await fetch(rest(resource + '?license_hash=eq.' + enc(licHash) + '&entry_id=eq.' + enc(String(payload.id))), {
          method: 'DELETE', headers: headers
        });
        if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNcode data tables are not set up yet -- run sql/sairncode_data_schema.sql in Supabase first.' } }); return; }
        if (!r.ok) { const errRows = await r.json().catch(function () { return null; }); return upstream(res, errRows); }
        res.status(200).json({ ok: true });
        return;
      }
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
