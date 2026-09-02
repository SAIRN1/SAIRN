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
const { getExecContext } = require('./_lib/exec-context');
const dntLocation = require('./_lib/dnt-location');
const payerRouting = require('./_lib/payer-routing');
const complianceRules = require('./_lib/compliance-rules');
const careCharges = require('./_lib/care-charges');
const opAudit = require('./_lib/op-audit');
const rfAuth = require('./rf-auth');
const senAuth = require('./sen-auth');
const senEvvReadiness = require('./_lib/sen-evv-readiness');
// SAIRNsenior EVV aggregators (2026-08-27). Must stay in sync with the selector in
// sairnsenior.html's Settings panel -- these are the four real state EVV aggregators
// plus an honest 'other', because several states run their own and forcing a wrong
// choice from the four would store a false compliance declaration. Storing one of
// these records WHICH aggregator the agency must submit to; it does NOT transmit
// anything. See sql/sairnsenior_settings_schema.sql for why that distinction is
// written down rather than assumed.
const SEN_EVV_AGGREGATORS = ['sandata', 'hhaexchange', 'tellus', 'carebridge', 'other'];
const dentalCreds = require('./_lib/dental-credentials');
const roofingCreds = require('./_lib/roofing-credentials');
const roofingClaims = require('./_lib/roofing-claims');
const roofingSupplement = require('./_lib/roofing-supplement');
const roofingAgreements = require('./_lib/roofing-agreements');
const roofingLocations = require('./_lib/roofing-locations');
const roofingPrograms = require('./_lib/roofing-programs');
const roofingBilling = require('./_lib/roofing-billing');
const roofingDamage = require('./_lib/roofing-damage-assessment');

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
const { RESOURCES, RESOURCE_LIST_TEXT, EXTRA_ACTIONS } = require('./_resources');

// The SAIRNcode resource family, which shares one generic handler below and is
// the only family with a real 'delete' verb.
//
// DERIVED, not re-listed (2026-08-24). This was a second hand-maintained copy
// of the same 28 names that api/_resources/sairncode.js already owned -- the
// last duplicated resource list left in this file after the 2026-08-21 registry
// split, and the same drift class that split was created to end (the old
// hand-kept error string had already lost employee_profile). It stayed in sync
// by luck, not by construction: verified identical at the moment it was
// replaced, and the SAIRNcode DME commit (`9e54b47`) had to edit this array and
// the registry file in the same change to keep it that way.
const SC_RESOURCES = require('./_resources/sairncode').resources;
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
  // Verbs beyond the universal read/write are declared per resource in
  // api/_resources/<app>.js and merged into EXTRA_ACTIONS. Today that is
  // 'delete' for the 28-resource SAIRNcode family, plus three compute-only
  // verbs owned by one resource each: 'route' (alf_payer_rules), 'evaluate'
  // (alf_compliance_rules) and 'derive_charges' (alf_billing).
  //
  // REPLACES three hand-written `action === 'x' && resource === 'y'` flags
  // that lived here (2026-08-24). Those were a third place to edit when adding
  // a resource, separate from both the registry and the handler branch, and
  // the note this block used to carry recorded what missing it costs:
  // "registering a resource and adding a handler branch is NOT enough, this
  // gate must allow the verb too, or the branch is unreachable and returns a
  // confusing 400 (found exactly that way here)." The verb now lives next to
  // the resource that owns it, so the two cannot be added apart.
  //
  // Deliberately still narrow: a verb reaches exactly the resources whose own
  // app granted it. Nothing here widens a verb to all 171 resources.
  const extraAllowed = EXTRA_ACTIONS[resource] || [];
  const isExtraAction = extraAllowed.indexOf(action) !== -1;
  if (action !== 'read' && action !== 'write' && !isExtraAction) {
    // Message text unchanged from the flag-based version on purpose: 'delete'
    // is the only extra verb it has ever named, and a resource-accurate list
    // here would change real response bodies. Worth doing separately, on its
    // own evidence, not as a side effect of this refactor.
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

    // ── SUPPLIER LEAD TIMES ([0072], 2026-09-02) ────────────────────────────
    // sql/sd_supplier_lead_times_schema.sql. Read is any authenticated
    // employee -- a fabricator needs to know whether the slab will land before
    // the install date. Write is owner/admin: a lead time drives customer
    // commitments and supplier negotiations, the same sensitivity class that
    // gates the roster.
    //
    // THE WRITE PATH HAS TWO SHAPES AND THEY ARE NOT INTERCHANGEABLE.
    //   quoted   -- what a supplier SAYS. Set directly.
    //   observe  -- a REAL receipt (ordered_at, received_at), folded into the
    //               running observed_* columns by api/_lib/job-risk.js.
    // They are never merged into one number here or in storage. Which one a
    // projection used is reported to the caller, because "quotes 14, last four
    // took 31" is the most useful thing this data can say.
    if (resource === 'supplier_lead_times' && (action === 'read' || action === 'write')) {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'stonedesk');
      if (!session) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'A valid employee session is required' } });
        return;
      }
      const norm = (v) => String(v == null ? '' : v).trim().toLowerCase();
      const sel = 'sd_supplier_lead_times?license_hash=eq.' + enc(licHash) +
        '&select=supplier,material,quoted_days,observed_total_days,observed_n,observed_min_days,observed_max_days,last_observed_at,notes,updated_at';

      if (action === 'read') {
        const r = await fetch(rest(sel), { headers });
        if (r.status === 404 || r.status === 400) {
          res.status(200).json({ ok: true, data: [], provisioned: false });
          return;
        }
        const rows = await r.json();
        if (!r.ok) return upstream(res, rows);
        res.status(200).json({ ok: true, data: rows || [], provisioned: true });
        return;
      }

      if (!EMPLOYEE_PROFILE_MANAGE_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only Owner or Manager can set supplier lead times' } });
        return;
      }
      const supplier = norm(payload && payload.supplier);
      const material = norm(payload && payload.material);
      if (!supplier || !material) {
        res.status(400).json({ error: { message: 'supplier and material are required' } });
        return;
      }
      const mode = (payload && payload.mode) === 'observe' ? 'observe' : 'quoted';
      if (mode === 'quoted') {
        const q = payload.quoted_days;
        if (q !== null && (!Number.isInteger(Number(q)) || Number(q) < 0 || Number(q) > 730)) {
          res.status(400).json({ error: { message: 'quoted_days must be null or a whole number of days between 0 and 730' } });
          return;
        }
      }

      // Read-then-fold-then-write, server side, so two tabs cannot race into a
      // lost observation. Same reasoning as the style profile.
      const cur = await fetch(rest(sel + '&supplier=eq.' + enc(supplier) + '&material=eq.' + enc(material) + '&limit=1'), { headers });
      if (cur.status === 404 || cur.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Supplier lead times table is not set up — run sql/sd_supplier_lead_times_schema.sql' } });
        return;
      }
      const curRows = await cur.json();
      if (!cur.ok) return upstream(res, curRows);
      let row = (Array.isArray(curRows) && curRows[0]) || null;

      if (mode === 'observe') {
        const risk = require('./_lib/job-risk');
        const folded = risk.observeReceipt(row, payload.ordered_at, payload.received_at);
        if (!folded.applied) {
          // A refused observation is a 400, not a silent no-op. "Received
          // before it was ordered" is a data-entry error the shop must see.
          res.status(400).json({ error: { code: 'BAD_OBSERVATION', message: folded.reason } });
          return;
        }
        row = folded.row;
        row.observed_days = folded.days;
      } else {
        row = Object.assign({}, row || {}, { quoted_days: payload.quoted_days === null ? null : Number(payload.quoted_days) });
      }

      const body = {
        license_hash: licHash, supplier, material,
        quoted_days: row.quoted_days == null ? null : row.quoted_days,
        observed_total_days: row.observed_total_days || 0,
        observed_n: row.observed_n || 0,
        observed_min_days: row.observed_min_days == null ? null : row.observed_min_days,
        observed_max_days: row.observed_max_days == null ? null : row.observed_max_days,
        last_observed_at: row.last_observed_at || null,
        notes: payload.notes === undefined ? (row.notes || null) : (String(payload.notes || '').trim() || null),
        updated_at: nowISO()
      };
      const w = await fetch(rest('sd_supplier_lead_times?on_conflict=license_hash,supplier,material'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify(body)
      });
      if (w.status === 404 || w.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Supplier lead times table is not set up — run sql/sd_supplier_lead_times_schema.sql' } });
        return;
      }
      const wRows = await w.json();
      if (!w.ok) return upstream(res, wRows);
      res.status(200).json({ ok: true, provisioned: true, data: (Array.isArray(wRows) && wRows[0]) || body, observed_days: row.observed_days });
      return;
    }

    // ── EXECUTIVE SUITE ADVISOR CONTEXT (2026-09-02) ────────────────────────
    // See api/_lib/exec-context.js for what these strings are and why they no
    // longer live in stonedesk.html: they carry SAIRN's own chart of accounts,
    // the StoneDesk price book, and the provisional-patent filing dates. That
    // file is served whole to every customer, so View Source read all of it.
    //
    // READ ONLY. There is no write action and no table -- the module IS the
    // store, so there is nothing to provision and nothing to seed.
    //
    // OWNER/ADMIN, ENFORCED HERE. The 2026-09-02 showPanel() gate is the same
    // check in the browser, and a browser check is advice: the page it lives in
    // is downloadable and editable. This is the copy that actually decides.
    if (resource === 'exec_context' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'stonedesk');
      if (!session) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'A valid employee session is required' } });
        return;
      }
      if (session.role !== 'owner' && session.role !== 'admin') {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'The Executive Suite is limited to Owner and Manager accounts' } });
        return;
      }
      // An unknown role is a 400, never a fallback to some other role's
      // context -- quietly serving the CFO's chart of accounts to a request
      // for 'sales' is the exact failure this endpoint was built to end.
      const ctx = getExecContext((payload && payload.role) || '');
      if (!ctx) {
        res.status(400).json({ error: { code: 'UNKNOWN_ROLE', message: 'role must be one of: ceo, cfo, cto' } });
        return;
      }
      res.status(200).json({ ok: true, data: { role: String(payload.role).trim().toLowerCase(), system: ctx } });
      return;
    }

    // ── STYLE PROFILE (sairn_style_profiles, 2026-09-02) ────────────────────
    // The NEXUS per-user style profile. See
    // docs/2026-09-02-nexus-style-profile-design.md and
    // api/_lib/style-profile.js.
    //
    // SELF ONLY, BOTH DIRECTIONS. employee_id comes from the verified session
    // token and never from the body -- there is no read-anyone and no
    // write-anyone action, deliberately. How a colleague writes is not roster
    // data, and the manager-visible case is already covered by
    // sd_employee_profiles, which this deliberately does not duplicate.
    //
    // WRITE TAKES AN OBSERVATION, NOT A MESSAGE. The client runs
    // styleProfile.analyse() locally and posts the resulting counts, so the
    // user's raw text is never transmitted here. The merge happens server-side
    // so two tabs cannot race each other into a lost update -- the row is read,
    // folded, and written in one request rather than the client sending a whole
    // profile it computed from a stale copy.
    if (resource === 'style_profile' && (action === 'read' || action === 'write')) {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'stonedesk');
      if (!session) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'A valid employee session is required' } });
        return;
      }
      const styleLib = require('./_lib/style-profile');
      const meId = session.employee_id;
      const sel = 'sairn_style_profiles?license_hash=eq.' + enc(licHash) +
        '&employee_id=eq.' + enc(meId) + '&select=employee_id,app_id,data,samples,updated_at&limit=1';

      // VALIDATE BEFORE TOUCHING THE DATABASE. A malformed observation is
      // malformed whether or not the table exists, and doing this first means a
      // bad payload cannot be masked by a provisioning answer.
      if (action === 'write') {
        const o = payload && payload.observation;
        if (!o || typeof o !== 'object' || !o.samples) {
          res.status(400).json({ error: { message: 'observation is required' } });
          return;
        }
        // Guard against a client posting a whole conversation as one "sample".
        if (Number(o.samples) !== 1) {
          res.status(400).json({ error: { code: 'ONE_AT_A_TIME', message: 'Post one observation per message' } });
          return;
        }
      }

      const cur = await fetch(rest(sel), { headers });
      if (cur.status === 404 || cur.status === 400) {
        // Table not provisioned.
        //
        // THE TWO ACTIONS MUST NOT ANSWER THE SAME WAY HERE, and the first
        // version of this branch got it wrong: it returned {ok:true,
        // provisioned:false} for BOTH, so a WRITE against a missing table came
        // back 200 ok -- a silent success for something that stored nothing.
        // Caught by driving the live endpoint before the table existed, not by
        // reading the code. A read has genuinely nothing to report; a write
        // FAILED and has to say so.
        if (action === 'read') {
          res.status(200).json({ ok: true, data: null, provisioned: false });
        } else {
          res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Style profiles table is not set up — run sql/sairn_style_profiles_schema.sql' } });
        }
        return;
      }
      const curRows = await cur.json();
      if (!cur.ok) return upstream(res, curRows);
      const existing = (Array.isArray(curRows) && curRows[0]) || null;

      if (action === 'read') {
        res.status(200).json({
          ok: true, provisioned: true,
          data: existing ? existing.data : null,
          samples: existing ? existing.samples : 0
        });
        return;
      }

      // Validated above, before the database was touched. Deliberately NOT
      // re-checked here: two copies of one rule is how they drift apart.
      const obs = payload.observation;
      const merged = styleLib.mergeObservation(existing ? existing.data : null, obs);
      const w = await fetch(rest('sairn_style_profiles?on_conflict=license_hash,employee_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, employee_id: meId, app_id: 'stonedesk',
          data: merged, samples: merged.samples, updated_at: nowISO()
        })
      });
      if (w.status === 404 || w.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Style profiles table is not set up — run sql/sairn_style_profiles_schema.sql' } });
        return;
      }
      const wRows = await w.json();
      if (!w.ok) return upstream(res, wRows);
      res.status(200).json({ ok: true, provisioned: true, data: merged, samples: merged.samples });
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

    // ── SLAB RESERVATION -- COMPARE-AND-SWAP (2026-09-02) ───────────────────
    // The double-sale. Three places in stonedesk.html did
    // `rs.status='reserved'; rs.reservedFor=customer;` with NO check of what
    // was already there, and the 'write' branch above is a blind upsert
    // (resolution=merge-duplicates), so the second salesperson to save simply
    // overwrote the first -- destroying `reservedFor`, the only record of who
    // had the slab. Both quotes then displayed the same physical slab as
    // theirs, and on the POS path the invoice was written BEFORE the slab was
    // touched, so money was taken against it either way.
    //
    // Preventing that is the single thing every competing product builds its
    // yard workflow around; iBlocky puts "niente più doppie vendite" second on
    // its own homepage. StoneDesk had no mechanism for it at all.
    //
    // A CLIENT-SIDE CHECK CANNOT DO THIS. sdSlabs is a localStorage array
    // loaded once per session, so a second device's reservation is not even
    // visible to the first. The decision has to be made where both requests
    // arrive, which is here.
    //
    // ATOMIC DESPITE THE READ. The read builds the merged jsonb blob; the
    // write then asserts, in its own WHERE clause, that status and reservedFor
    // are still exactly what the read saw. If another request won in between,
    // PostgREST matches zero rows and this returns 409 -- it does not overwrite
    // and it does not silently succeed. Optimistic concurrency, one statement.
    if (resource === 'slabs' && action === 'reserve') {
      const slabId = payload && payload.id;
      const who = String((payload && payload.reservedFor) || '').trim();
      if (!slabId) {
        res.status(400).json({ error: { code: 'NO_SLAB_ID', message: 'slab payload.id is required' } });
        return;
      }
      if (!who) {
        res.status(400).json({ error: { code: 'NO_HOLDER', message: 'reservedFor is required -- a reservation with nobody to hold it is not a reservation' } });
        return;
      }
      const base = 'sd_slabs?license_hash=eq.' + enc(licHash) + '&slab_id=eq.' + enc(String(slabId));

      const cur = await fetch(rest(base + '&select=data,updated_at'), { headers });
      const curRows = await cur.json();
      if (!cur.ok) return upstream(res, curRows);

      // Absent server-side means no other device has claimed it either, so a
      // plain INSERT is correct -- and it is a PLAIN insert, not the upsert the
      // 'write' branch uses, precisely so that two devices racing on the same
      // unsynced slab collide on the unique index instead of clobbering.
      if (!Array.isArray(curRows) || !curRows.length) {
        const merged = Object.assign({}, payload, { status: 'reserved', reservedFor: who });
        delete merged.reservedFor_expected;
        const ins = await fetch(rest('sd_slabs'), {
          method: 'POST',
          headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
          body: JSON.stringify({
            license_hash: licHash, app_id: 'stonedesk',
            slab_id: String(slabId), data: merged, updated_at: nowISO()
          })
        });
        const insRows = await ins.json();
        if (ins.status === 409) {
          res.status(409).json({ error: { code: 'ALREADY_RESERVED', message: 'Another device reserved this slab a moment ago. Reload the slab list and pick again.' } });
          return;
        }
        if (!ins.ok) return upstream(res, insRows);
        res.status(200).json({ ok: true, data: (Array.isArray(insRows) && insRows[0]) ? insRows[0].data : merged, created: true });
        return;
      }

      const row = curRows[0].data || {};
      const curUpdated = curRows[0].updated_at == null ? null : String(curRows[0].updated_at);
      const curStatus = row.status == null ? null : String(row.status);
      const curWho = row.reservedFor == null ? null : String(row.reservedFor);

      // Consumed is terminal. The slab has been cut; there is nothing to hold.
      if (curStatus === 'consumed') {
        res.status(409).json({ error: { code: 'SLAB_CONSUMED', message: 'That slab has already been consumed and cannot be reserved.' } });
        return;
      }
      // Already held by someone else. Naming the holder is the whole point --
      // "unavailable" sends a salesperson hunting, "held for Ruiz kitchen"
      // ends the question.
      if (curStatus === 'reserved' && curWho && curWho !== who) {
        res.status(409).json({
          error: {
            code: 'ALREADY_RESERVED',
            message: 'That slab is already reserved for ' + curWho + '.',
            reservedFor: curWho
          }
        });
        return;
      }

      const merged = Object.assign({}, row, payload, { status: 'reserved', reservedFor: who });
      // THE COMPARE. Re-asserts the exact state the read saw; a change by any
      // other request in between matches zero rows.
      // KEYED ON updated_at, NOT ON THE JSONB FIELDS, AND THAT IS A CORRECTION.
      // The first version of this guarded on `data->>status` and
      // `data->>reservedFor` with quoted values. It passed twelve unit
      // assertions and FAILED EVERY REAL RESERVATION: driven against the
      // deployed API, a plain in-stock slab with no concurrency at all came
      // back RESERVATION_RACE, because the predicate never matched anything.
      // The tests passed because the stub returned a row regardless of the
      // filter -- they proved a PATCH was issued, not that PostgREST agreed
      // with it. Only live-driving found it.
      //
      // updated_at is a plain timestamptz column: no JSON path, no identifier
      // case-folding, no value quoting to get wrong. It is also a STRICTLY
      // STRONGER guard, because every writer on this table stamps it -- the
      // 'write' branch above and this branch both do -- so it also catches
      // changes to fields the old predicate never looked at.
      const guard = '&updated_at=' + (curUpdated === null ? 'is.null' : 'eq.' + enc(curUpdated));
      const upd = await fetch(rest(base + guard), {
        method: 'PATCH',
        headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
        body: JSON.stringify({ data: merged, updated_at: nowISO() })
      });
      const updRows = await upd.json();
      if (!upd.ok) return upstream(res, updRows);
      if (!Array.isArray(updRows) || !updRows.length) {
        // Zero rows changed: the slab moved under us between the read and the
        // write. Reported as the conflict it is, never retried automatically --
        // a retry here would be a loop that eventually wins the double-sale.
        res.status(409).json({ error: { code: 'RESERVATION_RACE', message: 'Someone else changed this slab while you were reserving it. Reload the slab list and pick again.' } });
        return;
      }
      res.status(200).json({ ok: true, data: updRows[0].data });
      return;
    }

    // ── SLAB LINEAGE: BLOCKS / BUNDLES / HISTORY (2026-08-22, Phase 1b) ─────────────────────
    // block -> bundle -> slab -> remnant. See sql/sd_slab_lineage_schema.sql for why these are
    // sibling tables rather than fields on sd_slabs' jsonb blob (that blob is capped at 65536
    // bytes and ~55KB of it is already photo, so unbounded per-slab history would make a record
    // more likely to fail the longer it is used).
    //
    // All three follow the sd_slabs read/write shape exactly -- payload.id only, no role gate --
    // rather than sd_crm's session-gated shape, and that is a deliberate decision, not an
    // oversight: a quarry block, a bundle and a slab movement are yard/inventory facts, the same
    // class as the slab record they hang off, which has never required a session. Gating lineage
    // more tightly than the slab it describes would mean a coder could see the slab but not
    // where it came from. If slabs ever gain a session gate, these three move with them.
    //
    // Each returns provisioned:false rather than an error when its table is missing, so an
    // un-run migration degrades to "no lineage yet" instead of breaking the Slabs panel.
    const SD_LINEAGE = {
      sd_blocks:       { idCol: 'block_id',  label: 'blocks' },
      sd_bundles:      { idCol: 'bundle_id', label: 'bundles' },
      sd_slab_history: { idCol: 'event_id',  label: 'slab history' }
    };
    if (SD_LINEAGE[resource] && (action === 'read' || action === 'write')) {
      const cfg = SD_LINEAGE[resource];
      if (action === 'read') {
        const r = await fetch(rest(resource + '?license_hash=eq.' + enc(licHash) + '&select=' + cfg.idCol + ',data'), { headers });
        if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
        const rows = await r.json();
        if (!r.ok) return upstream(res, rows);
        res.status(200).json({
          ok: true,
          data: (rows || []).map((x) => Object.assign({ id: x[cfg.idCol] }, x.data)),
          provisioned: true
        });
        return;
      }
      if (!payload || payload.id === undefined || payload.id === null || payload.id === '') {
        res.status(400).json({ error: { message: resource + ' payload.id is required' } });
        return;
      }
      const row = { license_hash: licHash, app_id: 'stonedesk', data: payload, updated_at: nowISO() };
      row[cfg.idCol] = String(payload.id);
      const w = await fetch(rest(resource + '?on_conflict=license_hash,' + cfg.idCol), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify(row)
      });
      if (w.status === 404 || w.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Slab ' + cfg.label + ' sync is not set up yet — run sql/sd_slab_lineage_schema.sql in Supabase first.' } });
        return;
      }
      const wrows = await w.json();
      if (!w.ok) return upstream(res, wrows);
      res.status(200).json({ ok: true, data: (Array.isArray(wrows) && wrows[0]) ? wrows[0].data : payload });
      return;
    }
    // ── HR ONBOARDING (2026-08-29) ──────────────────────────────────────────────────────────
    // Backs stonedesk-hr.html. Same generic id-keyed shape as SD_LINEAGE above, and
    // DELIBERATELY NOT the same gate. Lineage is unauthenticated because the slab record it
    // describes is; this is personnel data -- name, pay rate, phone, email, and training
    // history about identifiable people -- so it requires a real session AND management role,
    // the same owner/admin pair that already gates the Grant and Revoke Sign-In Access cards
    // in stonedesk.html. Copying SD_LINEAGE's gate along with its shape would have published
    // the shop's payroll to anyone holding the licence key.
    //
    // NO DELETE BRANCH, on purpose. sql/sd_hr_schema.sql grants only select/insert/update, and
    // removing an employee from the roster must not take their OSHA 1910.1053(k)(3) silica
    // training record with them. The client's "Remove employee" marks status instead.
    const SD_HR = {
      sd_hr_employees: { idCol: 'employee_key', label: 'employees' },
      sd_hr_certs:     { idCol: 'cert_key',     label: 'training records' }
    };
    if (SD_HR[resource] && (action === 'read' || action === 'write')) {
      const cfg = SD_HR[resource];
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'stonedesk');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (session.role !== 'owner' && session.role !== 'admin') {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only an Owner or Manager can view or change HR records' } });
        return;
      }
      if (action === 'read') {
        const r = await fetch(rest(resource + '?license_hash=eq.' + enc(licHash) + '&select=' + cfg.idCol + ',data'), { headers });
        // Un-run migration degrades to "nothing recorded yet" rather than breaking the page,
        // same as the lineage tables -- but provisioned:false is reported so the client can
        // say so out loud instead of showing a convincing empty list.
        if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
        const rows = await r.json();
        if (!r.ok) return upstream(res, rows);
        res.status(200).json({
          ok: true,
          data: (rows || []).map((x) => Object.assign({ id: x[cfg.idCol] }, x.data)),
          provisioned: true
        });
        return;
      }
      if (!payload || payload.id === undefined || payload.id === null || payload.id === '') {
        res.status(400).json({ error: { message: resource + ' payload.id is required' } });
        return;
      }
      const hrRow = { license_hash: licHash, app_id: 'stonedesk', data: payload, updated_at: nowISO() };
      hrRow[cfg.idCol] = String(payload.id);
      const hw = await fetch(rest(resource + '?on_conflict=license_hash,' + cfg.idCol), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify(hrRow)
      });
      if (hw.status === 404 || hw.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'HR ' + cfg.label + ' storage is not set up yet — run sql/sd_hr_schema.sql in Supabase first.' } });
        return;
      }
      const hwrows = await hw.json();
      if (!hw.ok) return upstream(res, hwrows);
      res.status(200).json({ ok: true, data: (Array.isArray(hwrows) && hwrows[0]) ? hwrows[0].data : payload });
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
    // === SAIRNGROUNDS: ON-COURSE CADDIE (2026-09-02) ===
    // Rounds and cart orders, both property-scoped, both grd_-prefixed for the
    // same collision reason documented above for grd_schedule/grd_invoices --
    // SAIRNscape would want an identically-shaped 'rounds' one day and a bare
    // name would silently 400 one of the two apps.
    //
    // WHY THESE NEED THE SERVER AT ALL, rather than staying localStorage-only
    // like the msb_* panels did at first: pace of play is the loop back into
    // operations (SAIRNGROUNDS-SCOPE.md section 5a item 5), and a cart order is
    // useless to the Pro Shop if it never leaves the player's phone. Both are
    // read by somebody other than the device that wrote them, which is exactly
    // the line where localStorage stops being enough.
    if (resource === 'grd_rounds' && action === 'read') {
      const r = await fetch(rest('grd_rounds?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'grd_rounds' && action === 'write') {
      if (!payload || !payload.id || !payload.property_id) { res.status(400).json({ error: { message: 'round payload.id and payload.property_id are required' } }); return; }
      const r = await fetch(rest('grd_rounds?on_conflict=license_hash,round_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', round_id: String(payload.id), property_id: String(payload.property_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds caddie tables are not set up yet — run sql/sairngrounds_caddie_schema.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'grd_cart_orders' && action === 'read') {
      const r = await fetch(rest('grd_cart_orders?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'grd_cart_orders' && action === 'write') {
      if (!payload || !payload.id || !payload.property_id) { res.status(400).json({ error: { message: 'cart order payload.id and payload.property_id are required' } }); return; }
      const r = await fetch(rest('grd_cart_orders?on_conflict=license_hash,order_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairngrounds', order_id: String(payload.id), property_id: String(payload.property_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNgrounds caddie tables are not set up yet — run sql/sairngrounds_caddie_schema.sql in Supabase first.' } }); return; }
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

    // ── SAIRNSENIOR: sen_referral_sources + sen_referrals (2026-09-02) ──────────
    // Competitive-gap audit item A7 -- the referral-source relationship layer
    // (hospitals, SNFs, discharge planners, physician practices). Mosai is built
    // entirely around it; AxisCare, Aaniie, Alora and KanTime do not publish it.
    //
    // GATED ON THE INTAKE ROLES, not on management alone and not on every
    // employee. A referral row carries a PROSPECTIVE client's name and the reason
    // they were referred -- that is PHI about someone who is not yet a client, so
    // a caregiver has no business in the pipeline. But coordinators and
    // schedulers are the people who actually take the referral call, so
    // management-only (the sen_claims gate) would put the work out of reach of
    // the people doing it. SEN_CLIENT_BROAD_READ_ROLES is exactly that set.
    //
    // WRITE IS THE SAME SET, deliberately: whoever can see a referral is whoever
    // logs its outcome, and splitting them would mean a coordinator could read a
    // pipeline they cannot update, which is how a stale pipeline happens.
    // sen_training_rules and sen_training_records ride the same gate and the
    // same branch (2026-09-02, competitive-gap audit A6). Same reasoning, one
    // step further: a training record is employment data about a named
    // caregiver and a rule is the requirement it is measured against, so
    // schedulers and coordinators -- who decide who can be sent to a visit --
    // need both, and a caregiver has no business reading the roster's
    // compliance standing. Management-only would put it out of reach of the
    // people staffing the schedule.
    const SEN_REFERRAL_RESOURCES = {
      sen_referral_sources: 'source_id', sen_referrals: 'referral_id',
      sen_training_rules: 'rule_id', sen_training_records: 'record_id'
    };
    if (SEN_REFERRAL_RESOURCES[resource] && (action === 'read' || action === 'write')) {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnsenior');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!SEN_CLIENT_BROAD_READ_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'These records are limited to management, coordinators and schedulers' } });
        return;
      }
      const idCol = SEN_REFERRAL_RESOURCES[resource];
      if (action === 'read') {
        const r = await fetch(rest(resource + '?license_hash=eq.' + enc(licHash) + '&select=' + idCol + ',data'), { headers });
        if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
        const rows = await r.json();
        if (!r.ok) return upstream(res, rows);
        const data = (rows || []).map((x) => Object.assign({ id: x[idCol] }, x.data));
        res.status(200).json({ ok: true, data, provisioned: true });
        return;
      }
      if (!payload || !payload.id) { res.status(400).json({ error: { message: resource + ' payload.id is required' } }); return; }
      const body = Object.assign({}, payload);
      delete body.id;
      const r = await fetch(rest(resource + '?on_conflict=license_hash,' + idCol), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify(Object.assign(
          { license_hash: licHash, app_id: 'sairnsenior', data: body, updated_at: nowISO() },
          { [idCol]: String(payload.id) }
        ))
      });
      if (r.status === 404 || r.status === 400) {
        const setupFile = (resource.indexOf('training') !== -1)
          ? 'sql/sairnsenior_training_schema.sql'
          : 'sql/sairnsenior_referrals_schema.sql';
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'That table is not set up yet — run ' + setupFile + ' in Supabase first.' } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: Object.assign({ id: payload.id }, body) });
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

    // ── SAIRNSENIOR: sen_visits EVV SUBMISSION READINESS (2026-08-27) ────────────────────────
    // COMPUTE-ONLY. Reads visits, clients and caregivers, runs the pure engine in
    // api/_lib/sen-evv-readiness.js, and WRITES NOTHING -- no row created, none updated,
    // no submission recorded. There is deliberately no submission log yet, because there
    // is no transmission yet and an empty table would imply otherwise.
    //
    // WHY THIS EXISTS: SAIRNsenior cannot currently produce a compliant EVV record for any
    // visit, and it is four separate gaps across three tables (no service type anywhere, no
    // client member ID, no state caregiver ID, and GPS that is optional by design at
    // sairnsenior.html:1195/:1209). This reports them per visit so the real cost of
    // compliance is visible BEFORE anyone commits to the field work. It adds no schema and
    // captures no new field -- report-only, on purpose.
    //
    // Management + coordinator/scheduler. A caregiver seeing their own visit flagged
    // non-compliant is a supervisory conversation, not a field notification.
    if (resource === 'sen_visits' && action === 'readiness') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnsenior');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const SEN_READINESS_ROLES = { owner: true, billing: true, coordinator: true, scheduler: true };
      if (!SEN_READINESS_ROLES[session.role]) { res.status(403).json({ error: { code: 'FORBIDDEN', message: 'EVV readiness is available to management, coordinators and schedulers' } }); return; }

      const vr = await fetch(rest('sen_visits?license_hash=eq.' + enc(licHash) + '&select=visit_id,assigned_employee_id,data'), { headers });
      if (vr.status === 404 || vr.status === 400) { res.status(200).json({ ok: true, provisioned: false, data: null }); return; }
      const vrows = await vr.json();
      if (!vr.ok) return upstream(res, vrows);
      const visitList = (vrows || []).map((x) => Object.assign(
        { id: x.visit_id, assigned_employee_id: x.assigned_employee_id || '' }, x.data));

      // Clients and caregivers are read for their identifiers only. If either table is
      // unprovisioned the engine still runs and reports the reference as unresolved --
      // an honest "could not be found" beats refusing the whole report.
      const cr = await fetch(rest('sen_clients?license_hash=eq.' + enc(licHash) + '&select=client_id,data'), { headers });
      const clientsById = {};
      if (cr.ok) {
        (await cr.json() || []).forEach((x) => { clientsById[x.client_id] = Object.assign({ id: x.client_id }, x.data); });
      }
      const gr = await fetch(rest('sen_caregivers?license_hash=eq.' + enc(licHash) + '&select=caregiver_id,data'), { headers });
      const caregiversById = {};
      if (gr.ok) {
        (await gr.json() || []).forEach((x) => { caregiversById[x.caregiver_id] = Object.assign({ id: x.caregiver_id }, x.data); });
      }

      // The configured operating state comes from sen_settings, never the caller's payload
      // -- readiness must describe the agency's real declared state, not one a client
      // asked for. Absent settings is a real answer ('none_configured'), not an error.
      let evvState = null;
      const sr = await fetch(rest('sen_settings?license_hash=eq.' + enc(licHash) + '&setting_key=eq.evv_config&select=data'), { headers });
      if (sr.ok) {
        const srows = await sr.json();
        if (Array.isArray(srows) && srows[0] && srows[0].data) evvState = srows[0].data.state || null;
      }

      res.status(200).json({
        ok: true, provisioned: true,
        data: senEvvReadiness.summarize(visitList, clientsById, caregiversById, { state: evvState })
      });
      return;
    }

    // ── SAIRNSENIOR: sen_settings AGENCY CONFIGURATION (2026-08-27) ──────────────────────────
    // Keyed rows, one per setting -- same shape as rf_settings (2026-08-26), copied
    // deliberately rather than re-derived. Holds 'agency_profile' and 'evv_config'.
    //
    // WHY THIS EXISTS: both previously lived ONLY in localStorage
    // (sairnsenior.html :1452/:1461/:1470/:1476). EVV is federally mandated by the
    // 21st Century Cures Act and the state/aggregator pair decides where a visit record
    // is supposed to go -- holding it device-local meant it did not survive a browser-data
    // clear, did not follow the user to a second machine, and was invisible to everyone
    // else at the agency, while the Settings panel reported it as saved. Found by the
    // 2026-08-26 competitive-gap audit, section 5.1.
    //
    // READ is open to any authenticated employee -- a caregiver who can see WHICH state
    // and aggregator the agency operates under can make sense of the EVV rules applied to
    // their own visits; hiding it buys nothing and makes the visit screen unexplainable.
    // WRITE is management-only: the operating state is a compliance declaration, not a
    // preference. MANAGEMENT_ROLES is IMPORTED from api/sen-auth.js rather than re-listed
    // -- see that file's export note for why.
    if (resource === 'sen_settings' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnsenior');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const r = await fetch(rest('sen_settings?license_hash=eq.' + enc(licHash) + '&select=setting_key,data,updated_by,updated_at'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({
        ok: true, provisioned: true,
        data: (rows || []).map((x) => ({ setting_key: x.setting_key, value: x.data, updated_by: x.updated_by, updated_at: x.updated_at }))
      });
      return;
    }
    if (resource === 'sen_settings' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnsenior');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!senAuth.MANAGEMENT_ROLES[session.role]) { res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can change an agency setting' } }); return; }
      const key = payload && payload.setting_key;
      if (!key || typeof key !== 'string') { res.status(400).json({ error: { message: 'sen_settings: setting_key is required' } }); return; }
      const value = (payload && payload.value) || {};
      // Validate KNOWN keys before storing, so a malformed compliance declaration never
      // reaches an agency's screen looking authoritative. Unknown keys are stored as-is --
      // this is a settings store, not a schema registry -- but the two that exist today
      // decide real behaviour and are checked.
      if (key === 'evv_config') {
        const problems = [];
        const st = typeof value.state === 'string' ? value.state.trim().toUpperCase() : '';
        // Two letters only. A free-text state is what makes a per-state EVV rule
        // unmatchable later, and it is cheaper to refuse now than to reconcile it once
        // a transmission path exists.
        if (!/^[A-Z]{2}$/.test(st)) problems.push('state must be a 2-letter code (e.g. OH)');
        // The allowlist matches the selector in sairnsenior.html exactly. 'other' is a
        // real, honest option -- several states run their own aggregator -- and is kept
        // rather than forcing a wrong choice from the four named ones.
        if (SEN_EVV_AGGREGATORS.indexOf(value.aggregator) === -1) {
          problems.push('aggregator must be one of: ' + SEN_EVV_AGGREGATORS.join(', '));
        }
        if (problems.length) { res.status(400).json({ error: { code: 'INVALID_SETTING', message: 'sen_settings evv_config: ' + problems.join('; ') } }); return; }
        value.state = st;
      }
      if (key === 'agency_profile') {
        if (typeof value.agency_name !== 'string' || !value.agency_name.trim()) {
          res.status(400).json({ error: { code: 'INVALID_SETTING', message: 'sen_settings agency_profile: agency_name is required' } }); return;
        }
        if (value.agency_name.length > 200) {
          res.status(400).json({ error: { code: 'INVALID_SETTING', message: 'sen_settings agency_profile: agency_name is too long (max 200)' } }); return;
        }
      }
      const r = await fetch(rest('sen_settings?on_conflict=license_hash,setting_key'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        // updated_by comes from the VERIFIED session, never from the payload -- a forged
        // name in the body must not end up on the record of who changed the agency's
        // declared operating state.
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairnsenior', setting_key: String(key),
          data: value, updated_by: session.employee_id, updated_at: nowISO()
        })
      });
      if (r.status === 404 || r.status === 400) {
        const bt = await r.text();
        if (/relation .* does not exist|PGRST205|does not exist/i.test(bt)) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Agency settings are not set up yet — run sql/sairnsenior_settings_schema.sql in Supabase first.' } }); return; }
        console.error('sen_settings write error (status ' + r.status + '):', bt);
        res.status(502).json({ error: { message: 'Data store error — try again' } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const saved = Array.isArray(rows) && rows[0];
      res.status(200).json({
        ok: true,
        data: { setting_key: key, value: (saved && saved.data) || value, updated_by: session.employee_id, updated_at: (saved && saved.updated_at) || nowISO() }
      });
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

    // ── SAIRNROOFING: rf_jobs ASSIGNMENT-BASED PRIVACY GATE (2026-08-24, Phase 1) ────────────
    // Ground-up app. Same bespoke assignee-based-visibility shape as every other app's gate
    // (sd_crm, sdn_clients, bld_bids, sen_clients, alf_clients) -- a job is visible to
    // management, to the broad-read tier, or to whoever it's assigned to.
    //
    // THREE-TIER, built this way from the start rather than rediscovered -- the scope doc
    // (docs/superpowers/specs/2026-08-24-sairnroofing-v1-scope.md sec.3) named both bugs this
    // gate must not repeat:
    //   (1) SAIRNsenior's Phase 1 gate shipped as a MANAGEMENT/everyone-else binary and silently
    //       narrowed its real broad-read tier (coordinator/scheduler) down to own-assigned-only
    //       until fixed 2026-08-20. This gate ships with the real three tiers from commit one.
    //   (2) SAIRNbuild's bld_bids needed a fix so a narrow-tier user's brand-new record
    //       self-assigns to them on create rather than landing unassigned or assignable to
    //       someone else. The NARROW branch below does that from the start.
    //
    // Role tiers imported from api/rf-auth.js rather than re-listed here -- that file's own
    // header states re-listing role names in a second place is exactly the drift that caused
    // bug (1) above (one code path used senIsManagement() where the rest used
    // senIsBroadRead()). Both files now read from one source.
    //   MANAGEMENT  owner, admin            -- full read/write/reassign.
    //   BROAD_READ  owner, admin, estimator -- sees and may edit every job (needs the whole
    //               board to quote and to work a storm canvass), but may NOT reassign --
    //               assignment authority stays management-only regardless of read breadth,
    //               same rule sen_clients' broad-read tier already proved correct.
    //   NARROW      foreman, crew           -- own assigned jobs only; a brand-new job
    //               self-assigns to them on create.
    // Null assigned_employee_id = unassigned, management-only-visible, same default as every
    // prior app's assignment gate.
    const RF_MANAGEMENT_ROLES = rfAuth.MANAGEMENT_ROLES;
    const RF_BROAD_READ_ROLES = rfAuth.BROAD_READ_ROLES;
    // Read by the Tesla Solar Roof capability check in the write branch below.
    const RF_EMPLOYEE_TABLE = 'sairnroofing_employee_auth';
    if (resource === 'rf_jobs' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const r = await fetch(rest('rf_jobs?license_hash=eq.' + enc(licHash) + '&select=job_id,job_class,assigned_employee_id,location_id,data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      let out = rows || [];
      if (!RF_BROAD_READ_ROLES[session.role]) {
        out = out.filter((r) => r.assigned_employee_id === session.employee_id);
      }
      const data = out.map((r) => Object.assign({ id: r.job_id, job_class: r.job_class || 'residential', assigned_employee_id: r.assigned_employee_id || '', location_id: r.location_id || roofingLocations.DEFAULT_LOCATION_ID }, r.data));
      res.status(200).json({ ok: true, data, provisioned: true });
      return;
    }
    if (resource === 'rf_jobs' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'rf_jobs payload.id is required' } }); return; }
      const isManagement = !!RF_MANAGEMENT_ROLES[session.role];
      const isBroadRead = !!RF_BROAD_READ_ROLES[session.role];
      const existingR = await fetch(rest('rf_jobs?license_hash=eq.' + enc(licHash) + '&job_id=eq.' + enc(payload.id) + '&select=assigned_employee_id,location_id,data'), { headers });
      if (existingR.status === 404 || existingR.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Job tracking is not set up yet — run sql/sairnroofing_jobs_schema.sql in Supabase first.' } });
        return;
      }
      const existingRows = await existingR.json();
      if (!existingR.ok) return upstream(res, existingRows);
      const existingRow = Array.isArray(existingRows) && existingRows[0];
      const existingJobData = existingRow ? (existingRow.data || {}) : {};
      const requestedAssignee = payload.assigned_employee_id !== undefined
        ? (payload.assigned_employee_id || null)
        : (existingRow ? existingRow.assigned_employee_id : null);
      if (!isManagement && isBroadRead) {
        // Estimator (broad-read tier): may edit any job's details, matching their whole-board
        // read access, but the assignment must stay exactly as it already was (or exactly
        // unassigned for a brand-new job) -- broad visibility to quote is not the same as
        // authority to assign or reassign a job.
        const currentAssignee = existingRow ? existingRow.assigned_employee_id : null;
        if (requestedAssignee !== currentAssignee) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can assign or reassign a job' } });
          return;
        }
      } else if (!isManagement) {
        // Foreman/crew (narrow tier): may only touch a job already assigned to them, and a
        // brand-new job self-assigns to them on create -- same fix already proven correct on
        // SAIRNbuild's bld_bids.
        if (existingRow && existingRow.assigned_employee_id !== session.employee_id) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'This job is not assigned to you' } });
          return;
        }
        if (requestedAssignee !== session.employee_id) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can assign or reassign a job' } });
          return;
        }
      }
      // ── Phase 2: measurement (Aufmaß-style field correction) ────────────────────────────
      // `data` is a whole-document replace on every write (Postgres upsert, not a JSON merge),
      // same as every other resource on this endpoint -- so measurement and estimate, which are
      // edited from separate tabs, must be explicitly carried forward when a call doesn't touch
      // them, or an ordinary "edit the job name" save from the Overview tab would silently wipe
      // out a completed measurement or estimate. The base fields (name/address/status) stay on
      // the existing convention of "the client always sends the full record" -- this app has no
      // other case of two independent sub-editors sharing one document.
      //
      // DELIBERATELY SIMPLER than alf_clients' care_level_history: that resource requires the
      // client to resend the entire history array so the server can diff it for a preserved
      // prefix. Here the client sends exactly ONE new entry (measurement_correction) and the
      // server appends it -- less for the client to get wrong, and still genuinely append-only
      // because the server does the appending, not the client. No separate derived "current"
      // field either: the last entry in correction_history IS the current reading, so there is
      // nothing that can drift out of sync with it.
      //
      // No role restriction beyond the assignment checks already run above -- the whole point of
      // the Aufmaß pattern (scope doc sec.3) is that a foreman's field correction on their own
      // assigned job updates the takeoff directly, the same access they already have to edit
      // anything else on that job.
      let measurement = existingJobData.measurement || null;
      if (payload.measurement_correction !== undefined) {
        const entry = payload.measurement_correction;
        if (!entry || typeof entry !== 'object' || !entry.quantities || typeof entry.quantities !== 'object') {
          res.status(400).json({ error: { message: 'measurement_correction.quantities is required' } });
          return;
        }
        const priorHistory = (measurement && Array.isArray(measurement.correction_history)) ? measurement.correction_history : [];
        const stampedEntry = {
          quantities: entry.quantities,
          reason: String(entry.reason || '').slice(0, 500),
          source: entry.source === 'ai' ? 'ai' : 'manual',
          changed_by: session.employee_id,
          changed_at: nowISO()
        };
        measurement = { correction_history: priorHistory.concat([stampedEntry]) };
      }

      // ── Phase 2: estimate (materials + pricing) ─────────────────────────────────────────
      // Pricing is estimator/management work per the confirmed role scope -- narrow tier
      // (foreman/crew) can submit a measurement correction on their own job above, but cannot
      // price one. Unit costs are always caller-supplied and never defaulted here: inventing a
      // per-square-foot number would be exactly the fabricated-figure class Guardian checks for.
      // Line totals and the subtotal ARE recomputed server-side from qty*unit_cost rather than
      // trusted from the client, so a client-side arithmetic bug can't silently save a wrong total.
      const RF_MATERIALS = {
        asphalt: true, metal: true, slate: true, copper: true, wood_shake: true,
        tpo: true, epdm: true, modified_bitumen: true,
        gaf_timberline_solar: true, tesla_solar_roof: true, certainteed_solarshingle: true
      };
      let estimate = existingJobData.estimate || null;
      if (payload.estimate !== undefined) {
        if (!isManagement && !isBroadRead) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management or an estimator can price a job' } });
          return;
        }
        const est = payload.estimate;
        if (!est || typeof est !== 'object' || !RF_MATERIALS[est.material]) {
          res.status(400).json({ error: { message: 'estimate.material must be one of: ' + Object.keys(RF_MATERIALS).join(', ') } });
          return;
        }
        // Tesla Solar Roof capability gate (scope doc sec.3): "installable only by Tesla Energy
        // crews or Tesla Certified Installers -- a capability gate, not merely a price line."
        // Checked against the job's assigned installer, not the caller pricing the job -- an
        // estimator quoting the job is very likely not the person who will be on the roof.
        if (est.material === 'tesla_solar_roof') {
          if (!requestedAssignee) {
            res.status(400).json({ error: { message: 'Tesla Solar Roof requires an assigned installer before it can be estimated -- assign a foreman or crew member to this job first.' } });
            return;
          }
          const installerR = await fetch(rest(RF_EMPLOYEE_TABLE + '?license_hash=eq.' + enc(licHash) + '&employee_id=eq.' + enc(requestedAssignee) + '&select=certifications'), { headers });
          const installerRows = await installerR.json();
          if (!installerR.ok) return upstream(res, installerRows);
          const installerCerts = (Array.isArray(installerRows) && installerRows[0] && installerRows[0].certifications) || {};
          if (installerCerts.tesla_certified !== true) {
            res.status(400).json({ error: { code: 'NOT_TESLA_CERTIFIED', message: 'The assigned installer (' + requestedAssignee + ') is not Tesla Certified. Certify them (Owner-only) or choose a different material.' } });
            return;
          }
        }
        const lineItems = Array.isArray(est.line_items) ? est.line_items : [];
        let subtotal = 0;
        const computedItems = lineItems.map((item) => {
          const qty = Number(item && item.qty) || 0;
          const unitCost = Number(item && item.unit_cost) || 0;
          const total = qty * unitCost;
          subtotal += total;
          return { label: String((item && item.label) || '').slice(0, 200), qty, unit: String((item && item.unit) || '').slice(0, 40), unit_cost: unitCost, total };
        });
        const status = ['draft', 'reviewed', 'sent'].indexOf(est.status) !== -1 ? est.status : 'draft';
        estimate = {
          material: est.material, line_items: computedItems, subtotal, total: subtotal,
          status, updated_by: session.employee_id, updated_at: nowISO()
        };
      }

      const jobClass = payload.job_class === 'commercial' ? 'commercial' : 'residential';
      const jobData = Object.assign({}, payload);
      delete jobData.id;
      delete jobData.job_class;
      delete jobData.assigned_employee_id;
      delete jobData.measurement_correction;
      delete jobData.estimate;
      delete jobData.location_id;
      jobData.measurement = measurement;
      jobData.estimate = estimate;
      // ── Phase 4a: location attribution ──────────────────────────────────────────────────
      // Stamped on EVERY write, defaulting so a single-branch shop and every
      // job that already existed behave exactly as before. This is the part
      // that cannot be added later: a job saved with no location can never be
      // attributed to one afterwards, because the fact was never captured.
      // An EXISTING job keeps its location unless this write names a new one --
      // otherwise an ordinary "edit the job name" save from the Overview tab
      // would silently move the job to the default branch, which is the same
      // whole-document-replace trap the measurement/estimate carry-forward
      // above already exists to prevent.
      const locationId = (payload.location_id !== undefined)
        ? roofingLocations.stampLocation(payload).location_id
        : ((existingRow && existingRow.location_id) || roofingLocations.DEFAULT_LOCATION_ID);
      const r = await fetch(rest('rf_jobs?on_conflict=license_hash,job_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairnroofing', job_id: String(payload.id), job_class: jobClass,
          assigned_employee_id: requestedAssignee, location_id: locationId,
          data: jobData, updated_at: nowISO()
        })
      });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: Object.assign({ id: payload.id, job_class: jobClass, assigned_employee_id: requestedAssignee || '', location_id: locationId }, jobData) });
      return;
    }

    // ── SAIRNROOFING: rf_photos measurement photo capture (2026-08-24, Phase 2) ─────────────
    // Same tier gate as rf_jobs, keyed off the target job's own assigned_employee_id rather than
    // re-deriving a separate rule -- a photo is visible to whoever can already see the job it
    // belongs to. captured_by is ALWAYS the caller's own session.employee_id, never trusted from
    // the client, same discipline as sd_progress_photos' captured_by_id.
    if ((resource === 'rf_photos') && (action === 'read' || action === 'write')) {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const jobId = String((payload && payload.job_id) || '').trim();
      if (!jobId) { res.status(400).json({ error: { message: 'rf_photos payload.job_id is required' } }); return; }
      const jobR = await fetch(rest('rf_jobs?license_hash=eq.' + enc(licHash) + '&job_id=eq.' + enc(jobId) + '&select=assigned_employee_id'), { headers });
      if (jobR.status === 404 || jobR.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Job tracking is not set up yet — run sql/sairnroofing_jobs_schema.sql in Supabase first.' } });
        return;
      }
      const jobRows = await jobR.json();
      if (!jobR.ok) return upstream(res, jobRows);
      const job = Array.isArray(jobRows) && jobRows[0];
      if (!job) { res.status(404).json({ error: { code: 'NOT_FOUND', message: 'No such job on this license' } }); return; }
      const canSeeJob = RF_BROAD_READ_ROLES[session.role] || job.assigned_employee_id === session.employee_id;
      if (!canSeeJob) { res.status(403).json({ error: { code: 'FORBIDDEN', message: 'This job is not assigned to you' } }); return; }

      if (action === 'read') {
        const r = await fetch(rest('rf_photos?license_hash=eq.' + enc(licHash) + '&job_id=eq.' + enc(jobId) + '&select=id,captured_by,data,created_at&order=created_at.asc'), { headers });
        if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
        const rows = await r.json();
        if (!r.ok) return upstream(res, rows);
        const data = (rows || []).map((p) => Object.assign({ id: p.id, captured_by: p.captured_by, created_at: p.created_at }, p.data));
        res.status(200).json({ ok: true, data, provisioned: true });
        return;
      }

      // write
      if (!payload.photo_base64 || typeof payload.photo_base64 !== 'string') {
        res.status(400).json({ error: { message: 'rf_photos payload.photo_base64 is required' } });
        return;
      }
      const photoData = {
        photo_base64: payload.photo_base64,
        ai_analysis: String(payload.ai_analysis || '').slice(0, 20000),
        parsed_quantities: (payload.parsed_quantities && typeof payload.parsed_quantities === 'object') ? payload.parsed_quantities : null
      };
      const r = await fetch(rest('rf_photos'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairnroofing', job_id: jobId,
          captured_by: session.employee_id, data: photoData
        })
      });
      const rows = await r.json();
      if (r.status === 404 || r.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Photo capture is not set up yet — run sql/sairnroofing_photos_schema.sql in Supabase first.' } });
        return;
      }
      if (!r.ok) return upstream(res, rows);
      const saved = Array.isArray(rows) && rows[0];
      res.status(200).json({ ok: true, data: Object.assign({ id: saved && saved.id, captured_by: session.employee_id }, photoData) });
      return;
    }

    // ── SAIRNROOFING: rf_cert_rules + rf_certifications (2026-08-24, Phase 3a) ───────────────
    // Per-employee certifications and licensing rules. Evaluation logic is PURE and lives in
    // api/_lib/roofing-credentials.js; these branches are storage + gating only.
    //
    // GATE: unlike rf_jobs, this is NOT assignment-based. A certification is employment data,
    // not job data -- there is no assignee to key on. Rules are readable by any authenticated
    // employee (a crew member has a real interest in what their own trade requires) and
    // writable by management only. Certification records are readable by management and
    // broad-read roles, and ALWAYS by the employee they are about -- self-read is derived from
    // the caller's own verified token, never from a claimed id in the payload. Writes are
    // management-only: a certification record is an assertion about someone's qualifications,
    // and self-certification would defeat the point.
    if (resource === 'rf_cert_rules' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const r = await fetch(rest('rf_cert_rules?license_hash=eq.' + enc(licHash) + '&select=rule_id,state,requirement_type,role,effective_from,effective_to,status,data,verified_by'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false, coverage: { covered_states: [], uncovered_states: [], detail: [] } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const data = (rows || []).map((x) => ({
        rule_id: x.rule_id, state: x.state, requirement_type: x.requirement_type,
        role: x.role || null, effective_from: x.effective_from, effective_to: x.effective_to,
        status: x.status || 'active', verified_by: x.verified_by || '', data: x.data || {}
      }));
      const claimed = Array.isArray(payload && payload.claimed_states) && payload.claimed_states.length
        ? payload.claimed_states.map((s) => String(s).toUpperCase())
        : Array.from(new Set(data.map((x) => x.state)));
      res.status(200).json({ ok: true, data, provisioned: true, coverage: roofingCreds.credentialCoverage(data, claimed) });
      return;
    }
    if (resource === 'rf_cert_rules' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!rfAuth.MANAGEMENT_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can change licensing rules' } });
        return;
      }
      if (!payload || !payload.rule_id || !payload.state || !payload.requirement_type || !payload.effective_from) {
        res.status(400).json({ error: { message: 'rf_cert_rules requires rule_id, state, requirement_type, and effective_from' } });
        return;
      }
      // A requirement with no source is the fabricated-number class this seed format exists to
      // prevent, so it is refused at the API rather than discouraged in a comment.
      const auth = payload.data && payload.data.authority;
      if (!auth || !auth.citation || !auth.quote || !auth.read_on) {
        res.status(400).json({ error: { code: 'NO_AUTHORITY', message: 'rf_cert_rules requires data.authority with citation, quote, and read_on — a requirement with no source cannot be stored' } });
        return;
      }
      const r = await fetch(rest('rf_cert_rules?on_conflict=license_hash,rule_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairnroofing', rule_id: String(payload.rule_id),
          state: String(payload.state).toUpperCase(), requirement_type: payload.requirement_type,
          role: payload.role || null, effective_from: payload.effective_from,
          effective_to: payload.effective_to || null, status: payload.status || 'active',
          data: payload.data || {}, verified_by: session.employee_id, updated_at: nowISO()
        })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Certification tracking is not set up yet — run sql/sairnroofing_certifications_schema.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'rf_certifications' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const r = await fetch(rest('rf_certifications?license_hash=eq.' + enc(licHash) + '&select=entry_id,employee_id,record_type,data,recorded_at&order=recorded_at.asc'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      let out = (rows || []).map((x) => Object.assign({}, x.data || {}, {
        entry_id: x.entry_id, employee_id: x.employee_id,
        record_type: x.record_type, recorded_at: x.recorded_at
      }));
      // Narrow roles see only their own records — filtered server-side against the token's
      // own employee_id, never against anything the caller sent.
      if (!rfAuth.MANAGEMENT_ROLES[session.role] && !rfAuth.BROAD_READ_ROLES[session.role]) {
        out = out.filter((x) => x.employee_id === session.employee_id);
      }
      res.status(200).json({ ok: true, data: out, provisioned: true });
      return;
    }
    if (resource === 'rf_certifications' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!rfAuth.MANAGEMENT_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can record a certification' } });
        return;
      }
      if (!payload || !payload.id || !payload.employee_id || !payload.record_type) {
        res.status(400).json({ error: { message: 'rf_certifications requires payload.id, payload.employee_id, and payload.record_type' } });
        return;
      }
      if (!roofingCreds.RECORD_TYPES[payload.record_type]) {
        res.status(400).json({ error: { message: 'rf_certifications record_type must be one of: osha_card, safety_training, installer_cert, local_license' } });
        return;
      }
      // A record must either declare it has no expiry or carry one. Refused here as well as by
      // the table CHECK so the caller gets a readable reason instead of a Postgres constraint
      // name — an OSHA card with no federal expiry is a real, valid case, and a genuinely
      // missing renewal date is a real gap; conflating them was the bug this prevents.
      if (payload.has_expiry !== false && !payload.expires_on) {
        res.status(400).json({ error: { code: 'EXPIRY_UNSPECIFIED', message: 'Set expires_on, or set has_expiry:false to record a credential that genuinely does not expire (e.g. an OSHA Outreach card)' } });
        return;
      }
      // APPEND-ONLY: a plain insert, deliberately not an upsert. A correction is a new row that
      // supersedes; the table grant withholds update/delete as the backstop.
      const r = await fetch(rest('rf_certifications'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairnroofing', entry_id: String(payload.id),
          employee_id: String(payload.employee_id), record_type: payload.record_type,
          data: Object.assign({}, payload, { recorded_by: session.employee_id })
        })
      });
      if (r.status === 404) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Certification tracking is not set up yet — run sql/sairnroofing_certifications_schema.sql in Supabase first.' } }); return; }
      if (r.status === 400 || r.status === 409) {
        const bodyText = await r.text();
        let bodyJson = null; try { bodyJson = JSON.parse(bodyText); } catch (e) {}
        const msg = (bodyJson && (bodyJson.message || bodyJson.details || bodyJson.hint)) || bodyText || '';
        if (/relation .* does not exist|does not exist/i.test(msg)) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Certification tracking is not set up yet — run sql/sairnroofing_certifications_schema.sql in Supabase first.' } }); return; }
        if (/duplicate key|unique constraint/i.test(msg)) { res.status(409).json({ error: { code: 'DUPLICATE_ENTRY', message: 'A certification record with this id already exists. Records are append-only — write a new record to supersede, do not reuse an id.' } }); return; }
        if (/rfcd_expiry_check/i.test(msg)) { res.status(400).json({ error: { code: 'EXPIRY_UNSPECIFIED', message: 'Set expires_on, or set has_expiry:false for a credential that genuinely does not expire' } }); return; }
        console.error('rf_certifications write error (status ' + r.status + '):', msg);
        res.status(502).json({ error: { message: 'Data store error — try again', detail: msg } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? Object.assign({}, rows[0].data || {}, { recorded_at: rows[0].recorded_at }) : payload });
      return;
    }
    // Compute-only. Reads both tables, writes nothing.
    if (resource === 'rf_certifications' && action === 'evaluate') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const today = (payload && payload.today) || nowISO().slice(0, 10);
      const cr = await fetch(rest('rf_certifications?license_hash=eq.' + enc(licHash) + '&select=entry_id,employee_id,record_type,data,recorded_at'), { headers });
      if (cr.status === 404 || cr.status === 400) { res.status(200).json({ ok: true, provisioned: false, board: null }); return; }
      const credRows = await cr.json();
      if (!cr.ok) return upstream(res, credRows);
      const rr = await fetch(rest('rf_cert_rules?license_hash=eq.' + enc(licHash) + '&select=rule_id,state,requirement_type,role,effective_from,effective_to,status,data'), { headers });
      const ruleRows = (rr.status === 404 || rr.status === 400) ? [] : await rr.json();
      let records = (credRows || []).map((x) => Object.assign({}, x.data || {}, {
        entry_id: x.entry_id, employee_id: x.employee_id,
        record_type: x.record_type, recorded_at: x.recorded_at
      }));
      // Same narrowing as the read branch — a crew member's board shows their own records only.
      if (!rfAuth.MANAGEMENT_ROLES[session.role] && !rfAuth.BROAD_READ_ROLES[session.role]) {
        records = records.filter((x) => x.employee_id === session.employee_id);
      }
      const rules = (Array.isArray(ruleRows) ? ruleRows : []).map((x) => ({
        rule_id: x.rule_id, state: x.state, requirement_type: x.requirement_type,
        role: x.role || null, effective_from: x.effective_from, effective_to: x.effective_to,
        status: x.status || 'active', data: x.data || {}
      }));
      const board = roofingCreds.evaluateBoard(records, rules, today);
      if (!board.ok) { res.status(400).json({ error: board.error }); return; }
      const stateAsked = payload && payload.state;
      const licensing = stateAsked
        ? roofingCreds.selectLicensingRule(rules, { state: stateAsked, on_date: today })
        : null;
      res.status(200).json({
        ok: true, provisioned: true, board: board,
        licensing: licensing,
        federal: roofingCreds.federalRules(rules, today).map((r2) => ({ rule_id: r2.rule_id, label: r2.data && r2.data.label })),
        coverage: roofingCreds.credentialCoverage(rules, stateAsked ? [stateAsked] : [])
      });
      return;
    }

    // ── SAIRNROOFING: rf_claims + rf_claim_photos (2026-08-24, Phase 3b) ─────────────────────
    // Insurance claim record and tagged photo evidence. Money-field and status
    // logic is PURE and lives in api/_lib/roofing-claims.js; these branches are
    // storage + gating only.
    //
    // GATE: assignment-based, three-tier, the same shape as rf_jobs -- a claim
    // belongs to a job and carries the estimator/foreman handling it. Management
    // and broad-read see every claim; a narrow role sees only claims assigned to
    // them, filtered server-side against the token's own employee_id. A null
    // assignee is management-only, matching every prior assignment gate.
    //
    // rf_claims is MUTABLE (a claim evolves over 45-90 days), so writes upsert.
    // rf_claim_photos is APPEND-ONLY evidence -- a plain insert, no update path.
    if (resource === 'rf_claims' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const r = await fetch(rest('rf_claims?license_hash=eq.' + enc(licHash) + '&select=claim_id,job_id,assigned_employee_id,status,data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      let data = (rows || []).map((x) => Object.assign({}, x.data || {}, {
        claim_id: x.claim_id, job_id: x.job_id, assigned_employee_id: x.assigned_employee_id || null, status: x.status
      }));
      // Money summary is computed on read and never stored -- see roofing-claims.js.
      data = data.map((c) => Object.assign(c, { money_summary: roofingClaims.summarizeMoney(c) }));
      if (!rfAuth.MANAGEMENT_ROLES[session.role] && !rfAuth.BROAD_READ_ROLES[session.role]) {
        data = data.filter((c) => c.assigned_employee_id === session.employee_id);
      }
      res.status(200).json({ ok: true, data, provisioned: true, statuses: roofingClaims.CLAIM_STATUSES });
      return;
    }
    if (resource === 'rf_claims' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const isManagement = !!rfAuth.MANAGEMENT_ROLES[session.role];
      const isBroad = !!rfAuth.BROAD_READ_ROLES[session.role];
      const problems = roofingClaims.validateClaim(payload);
      if (problems.length) { res.status(400).json({ error: { message: 'rf_claims: ' + problems.join('; ') } }); return; }
      // A narrow role may only write a claim already assigned to them -- never
      // reassign it, and never touch an unassigned one. Checked against the
      // stored row, not against what the caller sent.
      const existingR = await fetch(rest('rf_claims?license_hash=eq.' + enc(licHash) + '&claim_id=eq.' + enc(payload.id) + '&select=assigned_employee_id'), { headers });
      if (existingR.status === 404 || existingR.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Claims are not set up yet — run sql/sairnroofing_claims_schema.sql in Supabase first.' } }); return; }
      const existingRows = await existingR.json();
      const existing = Array.isArray(existingRows) && existingRows[0];
      if (!isManagement && !isBroad) {
        if (!existing || existing.assigned_employee_id !== session.employee_id) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'You can only update a claim assigned to you' } });
          return;
        }
      }
      // Assignment is a management/broad-read decision. A narrow role's write
      // keeps whatever assignee is already stored; it cannot set or change it.
      const assignee = (isManagement || isBroad)
        ? (payload.assigned_employee_id || null)
        : (existing ? existing.assigned_employee_id : null);
      const norm = roofingClaims.normalizeMoney(payload);
      if (norm.problems.length) { res.status(400).json({ error: { message: 'rf_claims money: ' + norm.problems.join('; ') } }); return; }
      // The stored data blob: everything the caller sent, with the money fields
      // REPLACED by their normalized separate values (never a collapsed total),
      // and a derived money_summary explicitly NOT persisted.
      const dataBlob = Object.assign({}, payload, norm.money);
      delete dataBlob.money_summary;
      delete dataBlob.id;
      const r = await fetch(rest('rf_claims?on_conflict=license_hash,claim_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairnroofing', claim_id: String(payload.id),
          job_id: String(payload.job_id), assigned_employee_id: assignee,
          status: payload.status || 'loss_reported', data: dataBlob, updated_at: nowISO()
        })
      });
      if (r.status === 404 || r.status === 400) {
        const bt = await r.text(); let bj = null; try { bj = JSON.parse(bt); } catch (e) {}
        const msg = (bj && (bj.message || bj.details || bj.hint)) || bt || '';
        if (/relation .* does not exist|does not exist/i.test(msg)) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Claims are not set up yet — run sql/sairnroofing_claims_schema.sql in Supabase first.' } }); return; }
        if (/rfclm_status_check/i.test(msg)) { res.status(400).json({ error: { message: 'status must be one of: ' + roofingClaims.CLAIM_STATUSES.join(', ') } }); return; }
        console.error('rf_claims write error (status ' + r.status + '):', msg);
        res.status(502).json({ error: { message: 'Data store error — try again', detail: msg } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const saved = Array.isArray(rows) && rows[0];
      res.status(200).json({ ok: true, data: saved ? Object.assign({}, saved.data, { claim_id: saved.claim_id, status: saved.status, money_summary: roofingClaims.summarizeMoney(saved.data) }) : payload });
      return;
    }
    if (resource === 'rf_claim_photos' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      // Photos are read for a specific claim. Visibility follows the claim's own
      // assignment gate: the caller must be able to see the claim to see its
      // evidence.
      const claimId = payload && payload.claim_id;
      if (!claimId) { res.status(400).json({ error: { message: 'rf_claim_photos read requires payload.claim_id' } }); return; }
      const claimR = await fetch(rest('rf_claims?license_hash=eq.' + enc(licHash) + '&claim_id=eq.' + enc(claimId) + '&select=assigned_employee_id'), { headers });
      if (claimR.status === 404 || claimR.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const claimRows = await claimR.json();
      const claim = Array.isArray(claimRows) && claimRows[0];
      if (!claim) { res.status(200).json({ ok: true, data: [] }); return; }
      if (!rfAuth.MANAGEMENT_ROLES[session.role] && !rfAuth.BROAD_READ_ROLES[session.role] && claim.assigned_employee_id !== session.employee_id) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'You can only see evidence for a claim assigned to you' } });
        return;
      }
      const r = await fetch(rest('rf_claim_photos?license_hash=eq.' + enc(licHash) + '&claim_id=eq.' + enc(claimId) + '&select=photo_id,claim_id,captured_by,data,created_at&order=created_at.asc'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, provisioned: true, data: (rows || []).map((x) => Object.assign({}, x.data || {}, { photo_id: x.photo_id, claim_id: x.claim_id, captured_by: x.captured_by, created_at: x.created_at })) });
      return;
    }
    if (resource === 'rf_claim_photos' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const problems = roofingClaims.validatePhoto(payload);
      if (problems.length) { res.status(400).json({ error: { message: 'rf_claim_photos: ' + problems.join('; ') } }); return; }
      // Must be able to see the claim to attach evidence to it.
      const claimR = await fetch(rest('rf_claims?license_hash=eq.' + enc(licHash) + '&claim_id=eq.' + enc(payload.claim_id) + '&select=assigned_employee_id'), { headers });
      if (claimR.status === 404 || claimR.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Claims are not set up yet — run sql/sairnroofing_claims_schema.sql in Supabase first.' } }); return; }
      const claimRows = await claimR.json();
      const claim = Array.isArray(claimRows) && claimRows[0];
      if (!claim) { res.status(404).json({ error: { code: 'NO_CLAIM', message: 'No such claim — create the claim before attaching evidence to it' } }); return; }
      if (!rfAuth.MANAGEMENT_ROLES[session.role] && !rfAuth.BROAD_READ_ROLES[session.role] && claim.assigned_employee_id !== session.employee_id) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'You can only attach evidence to a claim assigned to you' } });
        return;
      }
      // APPEND-ONLY: evidence, not editable data. Plain insert.
      const dataBlob = Object.assign({}, payload); delete dataBlob.id;
      const r = await fetch(rest('rf_claim_photos'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairnroofing', photo_id: String(payload.id),
          claim_id: String(payload.claim_id), captured_by: session.employee_id, data: dataBlob
        })
      });
      if (r.status === 404) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Claims are not set up yet — run sql/sairnroofing_claims_schema.sql in Supabase first.' } }); return; }
      if (r.status === 400 || r.status === 409 || r.status === 413) {
        const bt = await r.text(); let bj = null; try { bj = JSON.parse(bt); } catch (e) {}
        const msg = (bj && (bj.message || bj.details || bj.hint)) || bt || '';
        if (/relation .* does not exist|does not exist/i.test(msg)) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Claims are not set up yet — run sql/sairnroofing_claims_schema.sql in Supabase first.' } }); return; }
        if (/duplicate key|unique constraint/i.test(msg)) { res.status(409).json({ error: { code: 'DUPLICATE_ENTRY', message: 'A photo with this id already exists. Evidence is append-only — capture a new photo, do not reuse an id.' } }); return; }
        if (/rfcph_data_size/i.test(msg)) { res.status(413).json({ error: { code: 'PAYLOAD_TOO_LARGE', message: 'This photo is over the 1.5MB limit — recompress before upload' } }); return; }
        console.error('rf_claim_photos write error (status ' + r.status + '):', msg);
        res.status(502).json({ error: { message: 'Data store error — try again', detail: msg } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const saved = Array.isArray(rows) && rows[0];
      res.status(200).json({ ok: true, data: saved ? Object.assign({}, saved.data, { photo_id: saved.photo_id, captured_by: saved.captured_by }) : payload });
      return;
    }
    // ── SAIRNROOFING: rf_settings, company-level configuration (2026-08-26) ─────────────────
    // Keyed rows, one per setting. Currently holds 'damage_threshold' for the
    // repair-vs-replace engine. READ is open to any authenticated employee (a
    // foreman needs to see the threshold their assessment was measured
    // against, or the number on screen is unexplainable); WRITE is
    // management-only, matching rf_contingency_rules -- a threshold that
    // decides whether a slope is called total is not one coder's preference.
    if (resource === 'rf_settings' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const r = await fetch(rest('rf_settings?license_hash=eq.' + enc(licHash) + '&select=setting_key,data,updated_by,updated_at'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({
        ok: true, provisioned: true,
        data: (rows || []).map((x) => ({ setting_key: x.setting_key, value: x.data, updated_by: x.updated_by, updated_at: x.updated_at }))
      });
      return;
    }
    if (resource === 'rf_settings' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!rfAuth.MANAGEMENT_ROLES[session.role]) { res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can change a company setting' } }); return; }
      const key = payload && payload.setting_key;
      if (!key || typeof key !== 'string') { res.status(400).json({ error: { message: 'rf_settings: setting_key is required' } }); return; }
      const value = (payload && payload.value) || {};
      // Validate KNOWN keys before storing. The engine refuses to compute from
      // a threshold with no source; refuse to STORE one too, so a bad row never
      // reaches a contractor's screen -- the same rule rf_contingency_rules
      // applies to its citations, for the same reason.
      if (key === 'damage_threshold') {
        const problems = [];
        const perils = roofingDamage.PERILS;
        const present = perils.filter((p) => value[p]);
        if (!present.length) problems.push('at least one of ' + perils.join('/') + ' must be configured');
        present.forEach((p) => {
          roofingDamage.validateThreshold(value[p]).forEach((m) => problems.push(p + ': ' + m));
        });
        if (problems.length) { res.status(400).json({ error: { code: 'INVALID_SETTING', message: 'rf_settings damage_threshold: ' + problems.join('; ') } }); return; }
      }
      const r = await fetch(rest('rf_settings?on_conflict=license_hash,setting_key'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        // updated_by comes from the VERIFIED session, never from the payload --
        // a forged name in the body must not end up on the record of who
        // changed a threshold.
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairnroofing', setting_key: String(key),
          data: value, updated_by: session.employee_id, updated_at: nowISO()
        })
      });
      if (r.status === 404 || r.status === 400) {
        const bt = await r.text();
        if (/relation .* does not exist|PGRST205|does not exist/i.test(bt)) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Company settings are not set up yet — run sql/sairnroofing_settings_schema.sql in Supabase first.' } }); return; }
        console.error('rf_settings write error (status ' + r.status + '):', bt);
        res.status(502).json({ error: { message: 'Data store error — try again' } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const saved = Array.isArray(rows) && rows[0];
      res.status(200).json({ ok: true, data: { setting_key: key, value: saved ? saved.data : value, updated_by: session.employee_id } });
      return;
    }

    // ── SHARED: subcontractor directory + assignments (2026-09-02) ──────────────────
    // Tier-A gap A3 from the worldwide competitive-gap audit. SAIRNroofing is
    // the first consumer; the tables and the engine are deliberately unprefixed
    // and app_id-scoped so SAIRNbuild and (later, as its own guarded migration)
    // StoneDesk can use the same ones rather than a third copy.
    //
    // COMPLIANCE IS COMPUTED ON READ, NEVER STORED. Whether a certificate is
    // valid depends on today's date, so a stored verdict is wrong the morning
    // after it is written -- the same reason rf_claim_agreements computes its
    // rescission clock instead of persisting it.
    if ((resource === 'subcontractors' || resource === 'sub_assignments') &&
        (action === 'read' || action === 'write')) {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const subs = require('./_lib/subcontractor-compliance');
      const APP = 'sairnroofing';

      if (resource === 'subcontractors' && action === 'read') {
        const r = await fetch(rest('subcontractors?license_hash=eq.' + enc(licHash) +
          '&app_id=eq.' + enc(APP) +
          '&select=sub_id,name,trade,phone,email,active,coi_carrier,coi_policy_no,coi_expiry,licence_no,licence_expiry,w9_on_file,data,updated_at'), { headers });
        if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
        const rows = await r.json();
        if (!r.ok) return upstream(res, rows);
        // `today` comes from the CALLER, and the engine refuses to run without
        // it. A server-side clock here would compute compliance in UTC for a
        // contractor working in local time -- the defect class fixed across
        // nine SAIRNvet panels on 2026-09-01.
        const today = (payload && payload.today) || null;
        const required = (payload && Array.isArray(payload.required)) ? payload.required : [];
        // warn_days FORWARDED. Caught by tools/sairn_seam_check.py on this very
        // branch before it shipped: the engine reads input.warn_days and this
        // call site did not set it, so the review window was pinned to the
        // engine default and no caller could change it. Identical to the
        // roofing-programs warn_days gap the same tool found this morning --
        // which is the argument for the tool, not against this code.
        //
        // A bad value is REFUSED rather than silently ignored: the engine
        // accepts only a number, so "45" as a string would fall back to the
        // default while the caller believed it had set 45.
        let warnDays;
        if (payload && payload.warn_days !== undefined && payload.warn_days !== null) {
          const wd = payload.warn_days;
          if (typeof wd !== 'number' || !isFinite(wd) || Math.floor(wd) !== wd || wd < 0 || wd > 365) {
            res.status(400).json({ error: { code: 'BAD_WARN_DAYS', message: 'warn_days must be a whole number of days between 0 and 365, sent as a JSON number' } });
            return;
          }
          warnDays = wd;
        }
        const evaluated = (rows || []).map((x) => {
          const ev = subs.evaluateSubcontractor({ subcontractor: x, today: today, required: required, warn_days: warnDays });
          return Object.assign({}, x, { compliance: ev.ok ? ev : null, compliance_error: ev.ok ? null : ev.error });
        });
        res.status(200).json({ ok: true, provisioned: true, today: today, data: evaluated });
        return;
      }

      if (resource === 'subcontractors' && action === 'write') {
        if (!rfAuth.MANAGEMENT_ROLES[session.role]) { res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can change the subcontractor roster' } }); return; }
        const subId = payload && payload.sub_id;
        const name = payload && typeof payload.name === 'string' ? payload.name.trim() : '';
        if (!subId || typeof subId !== 'string') { res.status(400).json({ error: { message: 'subcontractors: sub_id is required' } }); return; }
        if (!name) { res.status(400).json({ error: { message: 'subcontractors: name is required' } }); return; }
        // Dates are validated before storage, not after. An unreadable expiry
        // reads as 'unreadable' in the engine, which is honest but useless to a
        // contractor -- refusing it here means it never gets that far.
        const badDate = ['coi_expiry', 'licence_expiry'].filter((k) => {
          const v = payload[k];
          return v !== undefined && v !== null && v !== '' && !/^\d{4}-\d{2}-\d{2}$/.test(String(v));
        });
        if (badDate.length) { res.status(400).json({ error: { code: 'BAD_DATE', message: 'subcontractors: ' + badDate.join(', ') + ' must be YYYY-MM-DD' } }); return; }
        const row = {
          license_hash: licHash, app_id: APP, sub_id: subId, name: name,
          trade: payload.trade || null, phone: payload.phone || null, email: payload.email || null,
          active: payload.active !== false,
          coi_carrier: payload.coi_carrier || null, coi_policy_no: payload.coi_policy_no || null,
          coi_expiry: payload.coi_expiry || null,
          licence_no: payload.licence_no || null, licence_expiry: payload.licence_expiry || null,
          w9_on_file: payload.w9_on_file === true,
          data: payload.data || {}, updated_at: new Date().toISOString()
        };
        const w = await fetch(rest('subcontractors?on_conflict=license_hash,app_id,sub_id'), {
          method: 'POST',
          headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
          body: JSON.stringify(row)
        });
        const saved = await w.json();
        if (!w.ok) return upstream(res, saved);
        res.status(200).json({ ok: true, data: Array.isArray(saved) ? saved[0] : saved });
        return;
      }

      if (resource === 'sub_assignments' && action === 'read') {
        const r = await fetch(rest('sub_assignments?license_hash=eq.' + enc(licHash) +
          '&app_id=eq.' + enc(APP) +
          '&select=assignment_id,sub_id,job_id,scheduled_date,status,amount,payments,data,created_by,updated_at'), { headers });
        if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
        const rows = await r.json();
        if (!r.ok) return upstream(res, rows);
        // The raw `payments` array rides along beside the summary. Not folded
        // into summariseAssignment: a summariser that hands its own input back
        // has a muddier contract, and this is a round-trip concern, not a
        // compliance one. Without it an editor cannot ADD a payment -- the
        // write is a whole-row upsert, so appending needs the existing array,
        // and a UI that could not see it would silently wipe payment history
        // the first time anyone edited an assignment.
        res.status(200).json({
          ok: true, provisioned: true,
          data: (rows || []).map((x) => Object.assign(
            subs.summariseAssignment(x),
            { payments: Array.isArray(x.payments) ? x.payments : [] }
          ))
        });
        return;
      }

      if (resource === 'sub_assignments' && action === 'write') {
        if (!rfAuth.MANAGEMENT_ROLES[session.role]) { res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can assign a subcontractor' } }); return; }
        const aid = payload && payload.assignment_id;
        const subId = payload && payload.sub_id;
        if (!aid || !subId) { res.status(400).json({ error: { message: 'sub_assignments: assignment_id and sub_id are required' } }); return; }
        if (payload.status !== undefined && subs.ASSIGNMENT_STATUSES.indexOf(payload.status) === -1) {
          res.status(400).json({ error: { code: 'BAD_STATUS', message: 'sub_assignments: status must be one of ' + subs.ASSIGNMENT_STATUSES.join(', ') } });
          return;
        }
        // THE GATE THAT MAKES THIS WORTH BUILDING. A subcontractor whose
        // insurance has lapsed must not be schedulable, and the refusal has to
        // happen HERE rather than in the UI -- a client-side check is a
        // suggestion. `required` and `today` come from the caller so an
        // operator sets their own policy; with neither, nothing is required and
        // only an inactive sub is refused.
        const today = payload.today || null;
        // warn_days FORWARDED to the gate, added 2026-09-02. Found by
        // tools/sairn_seam_check.py the moment it learned to follow one level
        // of whole-object delegation -- canAssign() hands its input straight to
        // evaluateSubcontractor(), so its real dependencies were invisible to
        // the tool and this omission had been sitting behind a CANNOT TELL.
        //
        // It does not change WHO IS REFUSED: `blocking` is missing/expired/
        // unreadable and the warn window only classifies 'expiring'. What it
        // changes is the `evaluation` this endpoint hands back with the
        // refusal -- its warnings were computed at the engine's default 30
        // days no matter what the operator had configured, so the assignment
        // gate and the directory board could disagree about the same sub on
        // the same day. Narrow, and exactly the kind of thing that is only
        // ever found by a tool.
        let gateWarn;
        if (payload.warn_days !== undefined && payload.warn_days !== null) {
          const gwd = payload.warn_days;
          if (typeof gwd !== 'number' || !isFinite(gwd) || Math.floor(gwd) !== gwd || gwd < 0 || gwd > 365) {
            res.status(400).json({ error: { code: 'BAD_WARN_DAYS', message: 'warn_days must be a whole number of days between 0 and 365, sent as a JSON number' } });
            return;
          }
          gateWarn = gwd;
        }
        const required = Array.isArray(payload.required) ? payload.required : [];
        if (required.length) {
          const sr = await fetch(rest('subcontractors?license_hash=eq.' + enc(licHash) +
            '&app_id=eq.' + enc(APP) + '&sub_id=eq.' + enc(subId) + '&select=*&limit=1'), { headers });
          const srows = sr.ok ? await sr.json() : null;
          const theSub = Array.isArray(srows) && srows[0];
          if (!theSub) { res.status(400).json({ error: { code: 'NO_SUCH_SUB', message: 'sub_assignments: no subcontractor with that sub_id' } }); return; }
          const gate = subs.canAssign({ subcontractor: theSub, today: today, required: required, warn_days: gateWarn });
          if (!gate.ok) { res.status(400).json({ error: gate.error }); return; }
          if (!gate.allowed) {
            res.status(409).json({ error: { code: 'NOT_ASSIGNABLE', message: 'Cannot assign: ' + gate.reasons.join('; '), reasons: gate.reasons } });
            return;
          }
        }
        const row = {
          license_hash: licHash, app_id: APP, assignment_id: aid, sub_id: subId,
          job_id: payload.job_id || null,
          scheduled_date: payload.scheduled_date || null,
          status: payload.status || 'scheduled',
          amount: typeof payload.amount === 'number' ? payload.amount : null,
          payments: Array.isArray(payload.payments) ? payload.payments : [],
          data: payload.data || {},
          created_by: session.employee_id, updated_at: new Date().toISOString()
        };
        const w = await fetch(rest('sub_assignments?on_conflict=license_hash,app_id,assignment_id'), {
          method: 'POST',
          headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
          body: JSON.stringify(row)
        });
        const saved = await w.json();
        if (!w.ok) return upstream(res, saved);
        res.status(200).json({ ok: true, data: subs.summariseAssignment(Array.isArray(saved) ? saved[0] : saved) });
        return;
      }
    }

    // ── SAIRNROOFING: manufacturer warranties (2026-09-02) ─────────────────────────
    // Tier-A gap A1. Two resources: the tiers this contractor can offer (and
    // what certification each is gated on) and the per-job warranty with its
    // registration clock.
    //
    // NOTHING IS SEEDED AND NOTHING IS COMPUTED FROM MANUFACTURER DATA. Every
    // tier, condition and registration window comes from the contractor's own
    // programme agreement with a source they name -- the same 2026-08-25
    // decision rf_company_programs was built under. api/_lib/roofing-
    // warranties.js reports an unsourced tier as unusable rather than
    // evaluating it.
    if ((resource === 'rf_warranty_tiers' || resource === 'rf_job_warranties') &&
        (action === 'read' || action === 'write')) {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const warr = require('./_lib/roofing-warranties');

      // `today` comes from the CALLER and the engine refuses without it. A
      // server clock here computes a registration deadline in UTC for a
      // contractor working in local time -- the defect class fixed across nine
      // SAIRNvet panels on 2026-09-01.
      const wToday = (payload && payload.today) || null;
      // warn_days FORWARDED and a bad value REFUSED, not silently ignored:
      // the engine takes only a whole number, so "45" as a string would fall
      // back to the default while the caller believed it had set 45. This is
      // the exact gap tools/sairn_seam_check.py found in roofing-programs and
      // again in the subcontractor endpoint on 2026-09-02.
      let wWarn;
      if (payload && payload.warn_days !== undefined && payload.warn_days !== null) {
        const wd = payload.warn_days;
        if (typeof wd !== 'number' || !isFinite(wd) || Math.floor(wd) !== wd || wd < 0 || wd > 365) {
          res.status(400).json({ error: { code: 'BAD_WARN_DAYS', message: 'warn_days must be a whole number of days between 0 and 365, sent as a JSON number' } });
          return;
        }
        wWarn = wd;
      }

      if (resource === 'rf_warranty_tiers' && action === 'read') {
        if (!rfAuth.MANAGEMENT_ROLES[session.role] && !rfAuth.BROAD_READ_ROLES[session.role]) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Warranty tiers are management-level information' } });
          return;
        }
        const r = await fetch(rest('rf_warranty_tiers?license_hash=eq.' + enc(licHash) +
          '&select=tier_id,manufacturer,tier_name,requires_program_id,source,notes,active,data,updated_by&order=manufacturer.asc'), { headers });
        if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
        const rows = await r.json();
        if (!r.ok) return upstream(res, rows);
        // The availability verdict needs the company's programme standing, so
        // it is read here rather than asking the browser to join two lists and
        // re-implement the gate client-side.
        const pr = await fetch(rest('rf_company_programs?license_hash=eq.' + enc(licHash) +
          '&select=program_id,program_name,status,expires_on,has_expiry'), { headers });
        const programs = pr.ok ? await pr.json() : [];
        const ev = warr.tierAvailability({ today: wToday, tiers: rows || [], programs: programs || [], warn_days: wWarn });
        res.status(200).json({
          ok: true, provisioned: true, today: wToday,
          data: rows || [],
          availability: ev.ok ? ev : null,
          availability_error: ev.ok ? null : ev.error,
          // Stated so the UI cannot quietly present a gate that never ran.
          programs_provisioned: pr.ok
        });
        return;
      }

      if (resource === 'rf_warranty_tiers' && action === 'write') {
        if (!rfAuth.MANAGEMENT_ROLES[session.role]) { res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can define warranty tiers' } }); return; }
        const tierId = payload && typeof payload.tier_id === 'string' ? payload.tier_id.trim() : '';
        const mfr = payload && typeof payload.manufacturer === 'string' ? payload.manufacturer.trim() : '';
        const tName = payload && typeof payload.tier_name === 'string' ? payload.tier_name.trim() : '';
        if (!tierId || !mfr || !tName) { res.status(400).json({ error: { message: 'rf_warranty_tiers: tier_id, manufacturer and tier_name are required' } }); return; }
        const w = await fetch(rest('rf_warranty_tiers?on_conflict=license_hash,tier_id'), {
          method: 'POST',
          headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
          body: JSON.stringify({
            license_hash: licHash, tier_id: tierId, manufacturer: mfr, tier_name: tName,
            requires_program_id: (payload.requires_program_id || '').trim() || null,
            source: (payload.source || '').trim() || null,
            notes: (payload.notes || '').trim() || null,
            active: payload.active !== false,
            data: payload.data || {}, updated_by: session.employee_id, updated_at: nowISO()
          })
        });
        const saved = await w.json();
        if (!w.ok) return upstream(res, saved);
        res.status(200).json({ ok: true, data: Array.isArray(saved) ? saved[0] : saved });
        return;
      }

      if (resource === 'rf_job_warranties' && action === 'read') {
        const r = await fetch(rest('rf_job_warranties?license_hash=eq.' + enc(licHash) +
          '&select=warranty_id,job_id,manufacturer,tier_id,tier_name,status,installed_on,registered_on,register_within_days,registration_number,coverage_years,coverage_expires_on,notes,data,updated_by&order=installed_on.desc'), { headers });
        if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
        const rows = await r.json();
        if (!r.ok) return upstream(res, rows);
        // Registration deadlines and coverage are COMPUTED ON READ, never
        // stored: both depend on today's date, so a stored verdict is wrong the
        // morning after it is written.
        const out = (rows || []).map((x) => {
          const ev = warr.evaluateWarranty({ warranty: x, today: wToday, warn_days: wWarn });
          return Object.assign({}, x, { evaluation: ev.ok ? ev : null, evaluation_error: ev.ok ? null : ev.error });
        });
        res.status(200).json({ ok: true, provisioned: true, today: wToday, data: out });
        return;
      }

      if (resource === 'rf_job_warranties' && action === 'write') {
        if (!rfAuth.MANAGEMENT_ROLES[session.role]) { res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can record a warranty' } }); return; }
        const wid = payload && typeof payload.warranty_id === 'string' ? payload.warranty_id.trim() : '';
        if (!wid) { res.status(400).json({ error: { message: 'rf_job_warranties: warranty_id is required' } }); return; }
        if (payload.status !== undefined && warr.WARRANTY_STATUSES.indexOf(payload.status) === -1) {
          res.status(400).json({ error: { code: 'BAD_STATUS', message: 'rf_job_warranties: status must be one of ' + warr.WARRANTY_STATUSES.join(', ') } });
          return;
        }
        // Dates are refused here rather than stored and reported as garbled
        // later -- an unreadable installation date silently disables the whole
        // registration clock, which is the one thing this feature is for.
        const badDate = ['installed_on', 'registered_on', 'coverage_expires_on'].filter((k) => {
          const v = payload[k];
          return v !== undefined && v !== null && v !== '' && !/^\d{4}-\d{2}-\d{2}$/.test(String(v));
        });
        if (badDate.length) { res.status(400).json({ error: { code: 'BAD_DATE', message: 'rf_job_warranties: ' + badDate.join(', ') + ' must be YYYY-MM-DD' } }); return; }
        // The DB carries the same rule (rfjw_registered_needs_date); refusing
        // here too gives the user a sentence instead of a Postgres error.
        if (payload.status === 'registered' && !payload.registered_on) {
          res.status(400).json({ error: { code: 'NO_REGISTERED_ON', message: 'rf_job_warranties: a registered warranty needs the date it was registered' } });
          return;
        }
        const numOrNull = (v) => (typeof v === 'number' && isFinite(v) && Math.floor(v) === v && v >= 0) ? v : null;
        const w = await fetch(rest('rf_job_warranties?on_conflict=license_hash,warranty_id'), {
          method: 'POST',
          headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
          body: JSON.stringify({
            license_hash: licHash, warranty_id: wid,
            job_id: (payload.job_id || '').trim() || null,
            manufacturer: (payload.manufacturer || '').trim() || null,
            tier_id: (payload.tier_id || '').trim() || null,
            tier_name: (payload.tier_name || '').trim() || null,
            status: payload.status || 'not_registered',
            installed_on: payload.installed_on || null,
            registered_on: payload.registered_on || null,
            register_within_days: numOrNull(payload.register_within_days),
            registration_number: (payload.registration_number || '').trim() || null,
            coverage_years: numOrNull(payload.coverage_years),
            coverage_expires_on: payload.coverage_expires_on || null,
            notes: (payload.notes || '').trim() || null,
            data: payload.data || {}, updated_by: session.employee_id, updated_at: nowISO()
          })
        });
        const saved = await w.json();
        if (!w.ok) return upstream(res, saved);
        res.status(200).json({ ok: true, data: Array.isArray(saved) ? saved[0] : saved });
        return;
      }
    }

    // ── SAIRNROOFING: repair-vs-replace evidence assessment (2026-08-26) ────────────────────
    // Compute-only, same shape as 'reconcile' above. Reads the slope evidence
    // rows stored on the claim and the company's configured threshold, runs the
    // deterministic engine in api/_lib/roofing-damage-assessment.js, returns the
    // per-slope result. Writes nothing -- looking at whether a slope meets a
    // threshold must never record that it does.
    //
    // IT DOES NOT SAY A ROOF SHOULD BE REPLACED. The carrier decides that; this
    // reports whether recorded evidence meets a configured number, with the
    // number and its source attached. That is the public-adjuster boundary
    // documented at length in api/_lib/roofing-supplement.js and again at the
    // top of the damage-assessment engine. No LLM anywhere in this path.
    if (resource === 'rf_claims' && action === 'assess_damage') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const claimId = payload && payload.claim_id;
      if (!claimId) { res.status(400).json({ error: { message: 'assess_damage requires payload.claim_id' } }); return; }
      const cr = await fetch(rest('rf_claims?license_hash=eq.' + enc(licHash) + '&claim_id=eq.' + enc(claimId) + '&select=claim_id,assigned_employee_id,data'), { headers });
      if (cr.status === 404 || cr.status === 400) { res.status(200).json({ ok: true, provisioned: false, assessment: null }); return; }
      const cRows = await cr.json();
      const claim = Array.isArray(cRows) && cRows[0];
      if (!claim) { res.status(404).json({ error: { code: 'NO_CLAIM', message: 'No such claim' } }); return; }
      // Same assignment gate as reading the claim: you must be able to see it.
      if (!rfAuth.MANAGEMENT_ROLES[session.role] && !rfAuth.BROAD_READ_ROLES[session.role] && claim.assigned_employee_id !== session.employee_id) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'You can only assess a claim assigned to you' } });
        return;
      }
      const claimData = claim.data || {};
      const assessInput = (payload && payload.assessment) || claimData.damage_assessment || {};
      const peril = assessInput.peril || claimData.peril || null;

      // THRESHOLD RESOLUTION, and the order matters. A per-claim override wins,
      // and is reported AS an override so it is never mistaken for the company
      // number. Otherwise the company setting for this peril is used. If
      // neither exists the engine refuses -- it never falls back to a
      // convention, because a convention on screen with nothing behind it is
      // the fabricated-authority pattern Check 0b exists for.
      let threshold = null, isOverride = false, thresholdMissing = null;
      if (assessInput.threshold_override && assessInput.threshold_override.hits_per_test_square !== undefined) {
        threshold = assessInput.threshold_override;
        isOverride = true;
      } else {
        const sr = await fetch(rest('rf_settings?license_hash=eq.' + enc(licHash) + '&setting_key=eq.damage_threshold&select=data'), { headers });
        if (sr.status === 404 || sr.status === 400) {
          res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Company settings are not set up yet — run sql/sairnroofing_settings_schema.sql in Supabase first.' } });
          return;
        }
        const sRows = await sr.json();
        if (!sr.ok) return upstream(res, sRows);
        const stored = (Array.isArray(sRows) && sRows[0] && sRows[0].data) || {};
        threshold = peril ? stored[peril] : null;
        if (!threshold) thresholdMissing = peril
          ? 'No damage threshold is configured for peril "' + peril + '". Set one in Company Settings, citing its source.'
          : 'This claim has no peril recorded, so no threshold can be selected.';
      }

      // THE PHOTO IDS COME FROM THE SERVER, NOT THE PAYLOAD (2026-08-26).
      // A slope only counts as evidenced if it cites a photo that really
      // exists on THIS claim, so a caller cannot evidence a slope -- and
      // therefore cannot reach meets_threshold -- by inventing an id. Same
      // discipline Phase 3c established for the measured scope. A cited id
      // that resolves to nothing comes back named, not silently dropped.
      const phr = await fetch(rest('rf_claim_photos?license_hash=eq.' + enc(licHash) + '&claim_id=eq.' + enc(claimId) + '&select=photo_id'), { headers });
      // An absent photos table means "cannot verify", NOT "nothing verifies".
      // Passing [] there would fail every slope on a licence whose photo table
      // has not been provisioned -- the engine reports not_verified instead.
      const phRows = (phr.status === 404 || phr.status === 400) ? null : await phr.json();
      const claimPhotoIds = Array.isArray(phRows) ? phRows.map((x) => x.photo_id) : undefined;

      const result = roofingDamage.assess({
        slopes: assessInput.slopes,
        threshold: threshold,
        peril: peril,
        threshold_is_override: isOverride,
        claim_photo_ids: claimPhotoIds
      });
      res.status(200).json({
        ok: true, provisioned: true, claim_id: claimId,
        threshold_missing: thresholdMissing,
        assessment: result
      });
      return;
    }

    // ── SAIRNROOFING: supplement reconciliation (2026-08-24, Phase 3c) ───────────────────────
    // Compute-only. Reads the claim's stored supplement inputs and the linked
    // job's measured quantities, runs the DETERMINISTIC engine in
    // api/_lib/roofing-supplement.js, and returns the worksheet. Writes nothing
    // -- the inputs are saved via a normal rf_claims write into
    // data.supplement; the worksheet is derived on demand and never persisted,
    // the same discipline as the money_summary. No LLM anywhere in this path.
    if (resource === 'rf_claims' && action === 'reconcile') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const claimId = payload && payload.claim_id;
      if (!claimId) { res.status(400).json({ error: { message: 'reconcile requires payload.claim_id' } }); return; }
      const cr = await fetch(rest('rf_claims?license_hash=eq.' + enc(licHash) + '&claim_id=eq.' + enc(claimId) + '&select=claim_id,job_id,assigned_employee_id,data'), { headers });
      if (cr.status === 404 || cr.status === 400) { res.status(200).json({ ok: true, provisioned: false, worksheet: null }); return; }
      const cRows = await cr.json();
      const claim = Array.isArray(cRows) && cRows[0];
      if (!claim) { res.status(404).json({ error: { code: 'NO_CLAIM', message: 'No such claim' } }); return; }
      // Same assignment gate as reading the claim: you must be able to see it.
      if (!rfAuth.MANAGEMENT_ROLES[session.role] && !rfAuth.BROAD_READ_ROLES[session.role] && claim.assigned_employee_id !== session.employee_id) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'You can only reconcile a claim assigned to you' } });
        return;
      }
      // Measured quantities come from the linked job's LATEST measurement entry
      // -- the authoritative Phase 2 scope, read server-side, never taken from
      // the caller (the whole point is to compare against the real measurement).
      const jr = await fetch(rest('rf_jobs?license_hash=eq.' + enc(licHash) + '&job_id=eq.' + enc(claim.job_id) + '&select=data'), { headers });
      const jRows = (jr.status === 404 || jr.status === 400) ? [] : await jr.json();
      const jobData = (Array.isArray(jRows) && jRows[0] && jRows[0].data) || {};
      const history = (jobData.measurement && Array.isArray(jobData.measurement.correction_history)) ? jobData.measurement.correction_history : [];
      const measured = history.length ? (history[history.length - 1].quantities || {}) : {};
      // Supplement inputs (expected mapping, imported adjuster lines, asserted
      // lines) live on the claim. The caller may also pass a live, unsaved set
      // to preview before saving -- payload wins if present, otherwise stored.
      const supp = (payload && payload.supplement) || claim.data.supplement || {};
      const worksheet = roofingSupplement.reconcile({
        measured: measured,
        expected_items: supp.expected_items,
        adjuster_lines: supp.adjuster_lines,
        asserted_lines: supp.asserted_lines,
        tolerance: supp.tolerance
      });
      res.status(200).json({
        ok: true, provisioned: true, claim_id: claimId, job_id: claim.job_id,
        measured_from_job: measured, has_measurement: history.length > 0,
        worksheet: worksheet
      });
      return;
    }

    // ── SAIRNROOFING: estimate -> proposal -> invoice (2026-08-25, Phase 4b) ─────────────────
    // The job-visibility gate, mirroring rfClaimGate. Proposals follow job
    // visibility (a foreman assigned a job can already see its estimate, so
    // hiding the proposal would be inconsistent); INVOICES DO NOT -- what the
    // customer was billed and what they have paid is billing information a
    // crew member has no operational need for. Michael's call 2026-08-25.
    const rfJobGate = async (lh, hdrs, jobId, session, response) => {
      const jr = await fetch(rest('rf_jobs?license_hash=eq.' + enc(lh) + '&job_id=eq.' + enc(jobId) + '&select=job_id,assigned_employee_id,location_id'), { headers: hdrs });
      if (jr.status === 404 || jr.status === 400) {
        response.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Jobs are not set up yet — run sql/sairnroofing_jobs_schema.sql in Supabase first.' } });
        return { ok: false };
      }
      const rows = await jr.json();
      const job = Array.isArray(rows) && rows[0];
      if (!job) { response.status(404).json({ error: { code: 'NO_JOB', message: 'No such job' } }); return { ok: false }; }
      if (!rfAuth.MANAGEMENT_ROLES[session.role] && !rfAuth.BROAD_READ_ROLES[session.role] && job.assigned_employee_id !== session.employee_id) {
        response.status(403).json({ error: { code: 'FORBIDDEN', message: 'You can only work on a job assigned to you' } });
        return { ok: false };
      }
      return { ok: true, job: job };
    };

    if (resource === 'rf_proposals' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const jobId = payload && payload.job_id;
      if (!jobId) { res.status(400).json({ error: { message: 'rf_proposals read requires payload.job_id' } }); return; }
      const gate = await rfJobGate(licHash, headers, jobId, session, res);
      if (!gate.ok) return;
      const r = await fetch(rest('rf_proposals?license_hash=eq.' + enc(licHash) + '&job_id=eq.' + enc(jobId) + '&select=proposal_id,job_id,event_type,supersedes,recorded_by,data,created_at&order=created_at.asc'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false, state: null }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      // Same reasoning as rf_claim_agreements: an acceptance signature is up to
      // 1.5MB and nothing renders it, so it is stripped unless asked for.
      const withSig = payload && payload.include_signature === true;
      const events = (rows || []).map((x) => {
        const blob = Object.assign({}, x.data || {});
        if (!withSig) { delete blob.signature_data; blob.has_signature = !!(x.data && x.data.signature_data); }
        return Object.assign(blob, {
          proposal_id: x.proposal_id, job_id: x.job_id, event_type: x.event_type,
          supersedes: x.supersedes, recorded_by: x.recorded_by, created_at: x.created_at
        });
      });
      res.status(200).json({
        ok: true, provisioned: true, data: events,
        state: roofingBilling.proposalState(events),
        events: roofingBilling.PROPOSAL_EVENTS,
        acceptance_methods: roofingBilling.ACCEPTANCE_METHODS
      });
      return;
    }
    if (resource === 'rf_proposals' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      // Pricing is estimator/management work, matching the Phase 2 estimate
      // block -- a foreman may SEE the proposal on their job but cannot issue
      // one or record a customer's decision on it.
      if (!rfAuth.MANAGEMENT_ROLES[session.role] && !rfAuth.BROAD_READ_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management or an estimator can issue or decide a proposal' } });
        return;
      }
      const problems = roofingBilling.validateProposal(payload);
      if (problems.length) { res.status(400).json({ error: { message: 'rf_proposals: ' + problems.join('; ') } }); return; }
      const gate = await rfJobGate(licHash, headers, payload.job_id, session, res);
      if (!gate.ok) return;
      if (payload.event_type !== 'issued') {
        // A decision must name a real ISSUED proposal on THIS job. Checked
        // server-side against the stored chain -- otherwise a stray supersedes
        // could decide a proposal on a job the caller cannot see.
        const pr = await fetch(rest('rf_proposals?license_hash=eq.' + enc(licHash) + '&job_id=eq.' + enc(payload.job_id) + '&proposal_id=eq.' + enc(payload.supersedes) + '&event_type=eq.issued&select=proposal_id'), { headers });
        const pRows = (pr.status === 404 || pr.status === 400) ? [] : await pr.json();
        if (!Array.isArray(pRows) || !pRows.length) {
          res.status(400).json({ error: { code: 'NO_SUCH_PROPOSAL', message: 'That job has no issued proposal with the id being responded to' } });
          return;
        }
      }
      const blob = Object.assign({}, payload);
      ['id', 'job_id', 'event_type', 'supersedes'].forEach((k) => { delete blob[k]; });
      // The price is SNAPSHOT and recomputed server-side, never trusted from
      // the client and never a pointer at the live estimate.
      if (payload.event_type === 'issued') {
        const totals = roofingBilling.computeTotals(payload.line_items, payload.tax_rate, payload.tax);
        blob.line_items = totals.line_items;
        blob.subtotal = totals.subtotal;
        blob.total = totals.total;
        // Tax is stored as the user EXPRESSED it, not as computeTotals worked
        // it out -- see taxFieldsToStore's header. Writing the derived figure
        // back made it an input on the next read, which is what made a
        // rate-priced proposal report tax_basis 'amount' forever after.
        delete blob.tax_rate; delete blob.tax;
        Object.assign(blob, roofingBilling.taxFieldsToStore(payload.tax_rate, payload.tax));
      }
      const r = await fetch(rest('rf_proposals'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairnroofing', proposal_id: String(payload.id),
          job_id: String(payload.job_id), event_type: payload.event_type,
          supersedes: payload.supersedes || null,
          recorded_by: session.employee_id, data: blob
        })
      });
      if (r.status === 404 || r.status === 400 || r.status === 409) {
        const bt = await r.text();
        if (/relation .* does not exist|does not exist/i.test(bt)) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Proposals are not set up yet — run sql/sairnroofing_billing_schema.sql in Supabase first.' } }); return; }
        if (/duplicate key|unique/i.test(bt)) { res.status(409).json({ error: { code: 'ALREADY_RECORDED', message: 'A proposal with that id already exists — append-only, ids are never reused' } }); return; }
        res.status(400).json({ error: { message: 'Data store rejected the proposal', detail: bt } }); return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const saved = Array.isArray(rows) && rows[0];
      res.status(200).json({ ok: true, data: saved ? Object.assign({}, saved.data, { proposal_id: saved.proposal_id, event_type: saved.event_type, recorded_by: saved.recorded_by }) : payload });
      return;
    }

    // Invoices: management/broad-read only, read AND write. No narrow tier.
    if (resource === 'rf_invoices' && (action === 'read' || action === 'write' || action === 'issue' || action === 'add_payment' || action === 'reconcile_claim')) {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!rfAuth.MANAGEMENT_ROLES[session.role] && !rfAuth.BROAD_READ_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Billing is management-level information' } });
        return;
      }
      const loadInvoice = async (invId) => {
        const r = await fetch(rest('rf_invoices?license_hash=eq.' + enc(licHash) + '&invoice_id=eq.' + enc(invId) + '&select=invoice_id,invoice_number,invoice_seq,job_id,location_id,claim_id,status,issue_date,due_date,data,payments,created_by'), { headers });
        if (r.status === 404 || r.status === 400) return { missing: 'table' };
        const rows = await r.json();
        return { row: Array.isArray(rows) && rows[0] };
      };
      const shape = (x) => Object.assign({}, x.data || {}, {
        invoice_id: x.invoice_id, invoice_number: x.invoice_number, invoice_seq: x.invoice_seq,
        job_id: x.job_id, location_id: x.location_id, claim_id: x.claim_id, status: x.status,
        issue_date: x.issue_date, due_date: x.due_date, payments: x.payments || [], created_by: x.created_by
      });

      if (action === 'read') {
        let q = 'rf_invoices?license_hash=eq.' + enc(licHash) + '&select=invoice_id,invoice_number,invoice_seq,job_id,location_id,claim_id,status,issue_date,due_date,data,payments,created_by&order=created_at.desc';
        if (payload && payload.job_id) q += '&job_id=eq.' + enc(String(payload.job_id));
        const r = await fetch(rest(q), { headers });
        if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
        const rows = await r.json();
        if (!r.ok) return upstream(res, rows);
        res.status(200).json({
          ok: true, provisioned: true,
          // summary is DERIVED on every read and never persisted -- see the
          // schema header for why there is no balance column.
          data: (rows || []).map((x) => { const inv = shape(x); return Object.assign(inv, { summary: roofingBilling.summarizeInvoice(inv) }); }),
          statuses: roofingBilling.INVOICE_STATUSES,
          payment_methods: roofingBilling.PAYMENT_METHODS
        });
        return;
      }

      if (action === 'write') {
        const problems = roofingBilling.validateInvoice(payload);
        if (problems.length) { res.status(400).json({ error: { message: 'rf_invoices: ' + problems.join('; ') } }); return; }
        const gate = await rfJobGate(licHash, headers, payload.job_id, session, res);
        if (!gate.ok) return;
        const existing = await loadInvoice(String(payload.id));
        if (existing.missing === 'table') { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Invoicing is not set up yet — run sql/sairnroofing_billing_schema.sql in Supabase first.' } }); return; }
        // An ISSUED or PAID invoice is a document the customer holds. Editing
        // its money after the fact is exactly what a void-and-reissue exists to
        // avoid, so only the status may move once it has left draft.
        if (existing.row && existing.row.status !== 'draft' && payload.status !== 'void') {
          res.status(409).json({ error: { code: 'NOT_A_DRAFT', message: 'This invoice has been issued. Void it and raise a new one rather than editing what the customer already has.' } });
          return;
        }
        const totals = roofingBilling.computeTotals(payload.line_items, payload.tax_rate, payload.tax);
        const blob = Object.assign({}, payload);
        ['id', 'job_id', 'location_id', 'claim_id', 'status', 'issue_date', 'due_date', 'payments', 'invoice_number', 'invoice_seq'].forEach((k) => { delete blob[k]; });
        blob.line_items = totals.line_items;
        blob.subtotal = totals.subtotal;
        blob.total = totals.total;
        // Same rule as the proposal branch above: persist the question, not
        // the answer. See taxFieldsToStore in api/_lib/roofing-billing.js.
        delete blob.tax_rate; delete blob.tax;
        Object.assign(blob, roofingBilling.taxFieldsToStore(payload.tax_rate, payload.tax));
        const body = {
          license_hash: licHash, app_id: 'sairnroofing', invoice_id: String(payload.id),
          job_id: String(payload.job_id),
          location_id: (gate.job && gate.job.location_id) || roofingLocations.DEFAULT_LOCATION_ID,
          claim_id: payload.claim_id || null,
          status: payload.status || (existing.row ? existing.row.status : 'draft'),
          issue_date: payload.issue_date || (existing.row ? existing.row.issue_date : null),
          due_date: payload.due_date || null,
          data: blob, created_by: (existing.row && existing.row.created_by) || session.employee_id,
          updated_at: nowISO()
        };
        // The number is NEVER allocated here -- only the 'issue' verb does that,
        // so a draft cannot burn a sequence number and leave a gap. An existing
        // invoice keeps whatever it already has; a new one is written with an
        // EXPLICIT null rather than by omission, so the intent is on the wire
        // instead of resting on a column default.
        body.invoice_number = existing.row ? existing.row.invoice_number : null;
        body.invoice_seq = existing.row ? existing.row.invoice_seq : null;
        const r = await fetch(rest('rf_invoices?on_conflict=license_hash,invoice_id'), {
          method: 'POST',
          headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
          body: JSON.stringify(body)
        });
        if (r.status === 404 || r.status === 400) {
          const bt = await r.text();
          if (/relation .* does not exist|does not exist/i.test(bt)) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Invoicing is not set up yet — run sql/sairnroofing_billing_schema.sql in Supabase first.' } }); return; }
          if (/rfinv_issued_needs_number/i.test(bt)) { res.status(400).json({ error: { message: 'An invoice cannot leave draft without a number — use the issue action, which allocates one.' } }); return; }
          res.status(400).json({ error: { message: 'Data store rejected the invoice', detail: bt } }); return;
        }
        const rows = await r.json();
        if (!r.ok) return upstream(res, rows);
        const saved = Array.isArray(rows) && rows[0];
        const inv = saved ? shape(saved) : payload;
        res.status(200).json({ ok: true, data: Object.assign(inv, { summary: roofingBilling.summarizeInvoice(inv) }) });
        return;
      }

      if (action === 'issue') {
        const invId = payload && payload.invoice_id;
        if (!invId) { res.status(400).json({ error: { message: 'issue requires payload.invoice_id' } }); return; }
        const found = await loadInvoice(String(invId));
        if (found.missing === 'table') { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Invoicing is not set up yet — run sql/sairnroofing_billing_schema.sql in Supabase first.' } }); return; }
        if (!found.row) { res.status(404).json({ error: { code: 'NO_INVOICE', message: 'No such invoice' } }); return; }
        if (found.row.status !== 'draft') {
          // Idempotent rather than an error: re-issuing must NOT allocate a
          // second number, which would burn one and break the gapless
          // sequence in the one direction nobody can fix afterwards.
          res.status(200).json({ ok: true, already_issued: true, invoice_number: found.row.invoice_number, invoice_seq: found.row.invoice_seq, status: found.row.status });
          return;
        }
        const issueDate = (payload && payload.issue_date) || nowISO().slice(0, 10);
        const alloc = await fetch(rest('rpc/rf_allocate_invoice_number'), {
          method: 'POST', headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
          body: JSON.stringify({ p_license_hash: licHash, p_location_id: found.row.location_id || roofingLocations.DEFAULT_LOCATION_ID })
        });
        const allocRows = await alloc.json();
        if (!alloc.ok) return upstream(res, allocRows);
        const got = Array.isArray(allocRows) ? allocRows[0] : allocRows;
        if (!got || !got.invoice_number) { res.status(502).json({ error: { message: 'The invoice number allocator returned nothing — the invoice was NOT issued' } }); return; }
        const r = await fetch(rest('rf_invoices?license_hash=eq.' + enc(licHash) + '&invoice_id=eq.' + enc(String(invId))), {
          method: 'PATCH', headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
          body: JSON.stringify({ status: 'issued', invoice_number: got.invoice_number, invoice_seq: got.invoice_seq, issue_date: issueDate, updated_at: nowISO() })
        });
        const rows = await r.json();
        if (!r.ok) return upstream(res, rows);
        const saved = Array.isArray(rows) && rows[0];
        res.status(200).json({ ok: true, invoice_number: got.invoice_number, invoice_seq: got.invoice_seq, issue_date: issueDate, data: saved ? shape(saved) : null });
        return;
      }

      if (action === 'add_payment') {
        const invId = payload && payload.invoice_id;
        if (!invId) { res.status(400).json({ error: { message: 'add_payment requires payload.invoice_id' } }); return; }
        const entry = payload && payload.payment;
        const problems = roofingBilling.validatePayment(entry);
        if (problems.length) { res.status(400).json({ error: { message: 'payment: ' + problems.join('; ') } }); return; }
        const found = await loadInvoice(String(invId));
        if (found.missing === 'table') { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Invoicing is not set up yet — run sql/sairnroofing_billing_schema.sql in Supabase first.' } }); return; }
        if (!found.row) { res.status(404).json({ error: { code: 'NO_INVOICE', message: 'No such invoice' } }); return; }
        if (found.row.status === 'draft') { res.status(400).json({ error: { code: 'NOT_ISSUED', message: 'Issue the invoice before recording a payment against it' } }); return; }
        if (found.row.status === 'void') { res.status(400).json({ error: { code: 'VOID_INVOICE', message: 'This invoice is void — a payment cannot be recorded against it' } }); return; }
        const prior = Array.isArray(found.row.payments) ? found.row.payments : [];
        if (prior.some((p) => p && p.payment_id === entry.payment_id)) {
          res.status(409).json({ error: { code: 'ALREADY_RECORDED', message: 'A payment with that id is already on this invoice' } });
          return;
        }
        if (entry.amount < 0 && !prior.some((p) => p && p.payment_id === entry.reverses)) {
          res.status(400).json({ error: { code: 'NO_SUCH_PAYMENT', message: 'That reversal names a payment which is not on this invoice' } });
          return;
        }
        // THE SERVER APPENDS. The client sends ONE entry and never the array,
        // the same shape as rf_jobs' measurement_correction -- so the history
        // is genuinely append-only rather than append-only by convention.
        const stamped = Object.assign({}, entry, { recorded_by: session.employee_id, recorded_at: nowISO() });
        const next = prior.concat([stamped]);
        const r = await fetch(rest('rf_invoices?license_hash=eq.' + enc(licHash) + '&invoice_id=eq.' + enc(String(invId))), {
          method: 'PATCH', headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
          body: JSON.stringify({ payments: next, updated_at: nowISO() })
        });
        const rows = await r.json();
        if (!r.ok) return upstream(res, rows);
        const saved = Array.isArray(rows) && rows[0];
        const inv = saved ? shape(saved) : null;
        res.status(200).json({ ok: true, data: inv, summary: inv ? roofingBilling.summarizeInvoice(inv) : null });
        return;
      }

      if (action === 'reconcile_claim') {
        const invId = payload && payload.invoice_id;
        if (!invId) { res.status(400).json({ error: { message: 'reconcile_claim requires payload.invoice_id' } }); return; }
        const found = await loadInvoice(String(invId));
        if (found.missing === 'table') { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Invoicing is not set up yet — run sql/sairnroofing_billing_schema.sql in Supabase first.' } }); return; }
        if (!found.row) { res.status(404).json({ error: { code: 'NO_INVOICE', message: 'No such invoice' } }); return; }
        const inv = shape(found.row);
        let claim = null;
        if (found.row.claim_id) {
          // The claim is read SERVER-SIDE from the stored link, never taken
          // from the caller -- the whole point is comparing against the real
          // claim record.
          const cr = await fetch(rest('rf_claims?license_hash=eq.' + enc(licHash) + '&claim_id=eq.' + enc(found.row.claim_id) + '&select=claim_id,data'), { headers });
          const cRows = (cr.status === 404 || cr.status === 400) ? [] : await cr.json();
          const row = Array.isArray(cRows) && cRows[0];
          if (row) claim = Object.assign({}, row.data || {}, { claim_id: row.claim_id });
        }
        res.status(200).json({
          ok: true, invoice_id: inv.invoice_id, claim_id: found.row.claim_id || null,
          summary: roofingBilling.summarizeInvoice(inv),
          reconciliation: roofingBilling.reconcileAgainstClaim(inv, claim)
        });
        return;
      }
    }

    // ── SAIRNROOFING: manufacturer programmes, company level (2026-08-25, Phase 4d) ──────────
    // Voluntary commercial programmes, NOT regulation. Read is management-only:
    // unlike state licensing (which a foreman needs to know they personally
    // hold), a company's standing in GAF Master Elite is commercial strategy,
    // and the roster-share requirement exposes how many colleagues hold a
    // credential -- an aggregate a crew member has no need for.
    if (resource === 'rf_company_programs' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!rfAuth.MANAGEMENT_ROLES[session.role] && !rfAuth.BROAD_READ_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Company programme standing is management-level information' } });
        return;
      }
      const r = await fetch(rest('rf_company_programs?license_hash=eq.' + enc(licHash) + '&select=program_id,manufacturer,program_name,status,obtained_on,expires_on,has_expiry,requirements,data,updated_by&order=manufacturer.asc'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({
        ok: true, provisioned: true,
        data: (rows || []).map((x) => Object.assign({}, x.data || {}, {
          program_id: x.program_id, manufacturer: x.manufacturer, program_name: x.program_name,
          status: x.status, obtained_on: x.obtained_on, expires_on: x.expires_on,
          has_expiry: x.has_expiry, requirements: x.requirements || [], updated_by: x.updated_by
        })),
        statuses: roofingPrograms.PROGRAM_STATUSES,
        computed_kinds: roofingPrograms.COMPUTED_KINDS,
        denominators: roofingPrograms.DENOMINATORS
      });
      return;
    }
    if (resource === 'rf_company_programs' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!rfAuth.MANAGEMENT_ROLES[session.role]) { res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can record a programme' } }); return; }
      const problems = roofingPrograms.validateProgram(payload);
      if (problems.length) { res.status(400).json({ error: { message: 'rf_company_programs: ' + problems.join('; ') } }); return; }
      const blob = Object.assign({}, payload);
      ['id', 'manufacturer', 'program_name', 'status', 'obtained_on', 'expires_on', 'has_expiry', 'requirements'].forEach((k) => { delete blob[k]; });
      const r = await fetch(rest('rf_company_programs?on_conflict=license_hash,program_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairnroofing', program_id: String(payload.id),
          manufacturer: String(payload.manufacturer), program_name: String(payload.program_name),
          status: payload.status || 'not_enrolled',
          obtained_on: payload.obtained_on || null,
          expires_on: payload.expires_on || null,
          has_expiry: payload.has_expiry !== false,
          requirements: Array.isArray(payload.requirements) ? payload.requirements : [],
          data: blob, updated_by: session.employee_id, updated_at: nowISO()
        })
      });
      if (r.status === 404 || r.status === 400) {
        const bt = await r.text();
        if (/relation .* does not exist|does not exist/i.test(bt)) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Programmes are not set up yet — run sql/sairnroofing_programs_schema.sql in Supabase first.' } }); return; }
        if (/rfprg_expiry_coherent/i.test(bt)) { res.status(400).json({ error: { message: 'A programme recorded as held needs either a renewal date or an explicit "does not expire" — the two cases must stay distinguishable.' } }); return; }
        res.status(400).json({ error: { message: 'Data store rejected the programme', detail: bt } }); return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: Array.isArray(rows) && rows[0] });
      return;
    }
    // Compute-only. Reads the programmes, the ROSTER and the Phase 3a
    // certification records server-side, runs the engine, writes nothing.
    if (resource === 'rf_company_programs' && action === 'evaluate') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!rfAuth.MANAGEMENT_ROLES[session.role] && !rfAuth.BROAD_READ_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Company programme standing is management-level information' } });
        return;
      }
      const today = (payload && payload.today) || nowISO().slice(0, 10);
      const pr = await fetch(rest('rf_company_programs?license_hash=eq.' + enc(licHash) + '&select=program_id,manufacturer,program_name,status,obtained_on,expires_on,has_expiry,requirements'), { headers });
      if (pr.status === 404 || pr.status === 400) { res.status(200).json({ ok: true, provisioned: false, programs: [] }); return; }
      const progRows = await pr.json();
      if (!pr.ok) return upstream(res, progRows);
      // The roster and the certification records are read WHOLE here, not
      // narrowed to the caller: a company-level share is by definition an
      // aggregate over everyone, which is exactly why this verb is gated to
      // management/broad-read above rather than being open like 'evaluate' on
      // rf_certifications.
      const er = await fetch(rest('sairnroofing_employee_auth?license_hash=eq.' + enc(licHash) + '&select=employee_id,role,active'), { headers });
      const empRows = (er.status === 404 || er.status === 400) ? [] : await er.json();
      const cr = await fetch(rest('rf_certifications?license_hash=eq.' + enc(licHash) + '&select=entry_id,employee_id,record_type,data,recorded_at'), { headers });
      const certRows = (cr.status === 404 || cr.status === 400) ? [] : await cr.json();
      const records = roofingCreds.latestByKey((Array.isArray(certRows) ? certRows : []).map((x) => Object.assign({}, x.data || {}, {
        entry_id: x.entry_id, employee_id: x.employee_id, record_type: x.record_type, recorded_at: x.recorded_at
      })));
      const roster = (Array.isArray(empRows) ? empRows : []).map((e) => ({
        employee_id: e.employee_id, role: e.role, active: e.active !== false
      }));
      // warn_days FORWARDED 2026-09-01. The engine has read `input.warn_days`
      // since it was written and this call site never set it, so the expiry
      // warning window was pinned to DEFAULT_WARN_DAYS (30) and no caller could
      // change it. Found by tools/sairn_seam_check.py on its first real run --
      // the same engine-reads-it, endpoint-never-sends-it shape that ran
      // SAIRNlaw's Florida deadline five days late for five days.
      //
      // A BAD VALUE IS REFUSED, NOT SILENTLY DROPPED. The engine accepts only
      // `typeof === 'number'`, so a caller sending "45" as a string would have
      // been ignored and would have got the 30-day default back while believing
      // it had set 45. That is the same silent-default failure in miniature, so
      // it 400s instead.
      let warnDays;
      if (payload && payload.warn_days !== undefined && payload.warn_days !== null) {
        const wd = payload.warn_days;
        if (typeof wd !== 'number' || !isFinite(wd) || Math.floor(wd) !== wd || wd < 0 || wd > 365) {
          res.status(400).json({ error: { code: 'BAD_WARN_DAYS', message: 'warn_days must be a whole number of days between 0 and 365, sent as a JSON number' } });
          return;
        }
        warnDays = wd;
      }
      const programs = (Array.isArray(progRows) ? progRows : []).map((x) => roofingPrograms.evaluateProgram({
        program: {
          program_id: x.program_id, manufacturer: x.manufacturer, program_name: x.program_name,
          requirements: x.requirements || [],
          standing: { status: x.status, obtained_on: x.obtained_on, expires_on: x.expires_on, has_expiry: x.has_expiry }
        },
        roster: roster, certifications: records, today: today, warn_days: warnDays
      }));
      res.status(200).json({
        ok: true, provisioned: true, today: today,
        roster_size: roster.filter((e) => e.active).length,
        programs: programs
      });
      return;
    }

    // ── SAIRNROOFING: locations + crew scheduling (2026-08-25, Phase 4a) ─────────────────────
    // location_id is ATTRIBUTION, not access control -- see the header of
    // api/_lib/roofing-locations.js. Nothing below grants or restricts anything
    // on the basis of location, and that is deliberate.
    if (resource === 'rf_locations' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      // Any signed-in role: a foreman needs to know which branch a job belongs
      // to, and the list is company structure, not sensitive data.
      const r = await fetch(rest('rf_locations?license_hash=eq.' + enc(licHash) + '&select=location_id,name,active,data&order=name.asc'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, provisioned: true, data: (rows || []).map((x) => Object.assign({}, x.data || {}, { location_id: x.location_id, name: x.name, active: x.active })), default_location_id: roofingLocations.DEFAULT_LOCATION_ID });
      return;
    }
    if (resource === 'rf_locations' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!rfAuth.MANAGEMENT_ROLES[session.role]) { res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can add or edit a location' } }); return; }
      const problems = roofingLocations.validateLocation(payload);
      if (problems.length) { res.status(400).json({ error: { message: 'rf_locations: ' + problems.join('; ') } }); return; }
      const blob = Object.assign({}, payload); delete blob.id; delete blob.name; delete blob.active;
      const r = await fetch(rest('rf_locations?on_conflict=license_hash,location_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairnroofing', location_id: String(payload.id),
          name: String(payload.name), active: payload.active !== false,
          data: blob, updated_at: nowISO()
        })
      });
      if (r.status === 404 || r.status === 400) {
        const bt = await r.text();
        if (/relation .* does not exist|does not exist/i.test(bt)) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Locations are not set up yet — run sql/sairnroofing_locations_schema.sql in Supabase first.' } }); return; }
        res.status(400).json({ error: { message: 'Data store rejected the location', detail: bt } }); return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: Array.isArray(rows) && rows[0] });
      return;
    }
    if (resource === 'rf_schedule' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      let q = 'rf_schedule?license_hash=eq.' + enc(licHash) + '&select=schedule_id,job_id,location_id,scheduled_date,status,crew,data,created_by&order=scheduled_date.asc';
      if (payload && payload.from) q += '&scheduled_date=gte.' + enc(String(payload.from));
      if (payload && payload.to) q += '&scheduled_date=lte.' + enc(String(payload.to));
      const r = await fetch(rest(q), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      // The narrow-tier filter needs each row's JOB assignee, so the job
      // assignments are read once and indexed rather than per row.
      let assignees = {};
      if (!rfAuth.MANAGEMENT_ROLES[session.role] && !rfAuth.BROAD_READ_ROLES[session.role]) {
        const jr = await fetch(rest('rf_jobs?license_hash=eq.' + enc(licHash) + '&select=job_id,assigned_employee_id'), { headers });
        const jRows = (jr.status === 404 || jr.status === 400) ? [] : await jr.json();
        (Array.isArray(jRows) ? jRows : []).forEach((j) => { assignees[j.job_id] = j.assigned_employee_id; });
      }
      const data = (rows || [])
        .filter((x) => roofingLocations.canSeeSchedule(session, x, assignees[x.job_id], rfAuth.MANAGEMENT_ROLES, rfAuth.BROAD_READ_ROLES))
        .map((x) => Object.assign({}, x.data || {}, {
          schedule_id: x.schedule_id, job_id: x.job_id, location_id: x.location_id,
          scheduled_date: x.scheduled_date, status: x.status, crew: x.crew || [], created_by: x.created_by
        }));
      res.status(200).json({ ok: true, provisioned: true, data, statuses: roofingLocations.SCHEDULE_STATUSES });
      return;
    }
    if (resource === 'rf_schedule' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      // Putting a named person on a crew for a given day IS an assignment
      // decision, and rf_jobs already holds that only management assigns or
      // reassigns. Broad-read (estimator) can see the whole board but does not
      // staff it -- quoting a job is not the same authority as sending people
      // to it. A crew member changing their own day's STATUS goes through
      // 'set_status' below, which cannot touch the crew, the job or the date.
      if (!rfAuth.MANAGEMENT_ROLES[session.role]) { res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can schedule a crew' } }); return; }
      const problems = roofingLocations.validateSchedule(payload);
      if (problems.length) { res.status(400).json({ error: { message: 'rf_schedule: ' + problems.join('; ') } }); return; }
      // The job must exist, and the day inherits ITS location rather than
      // taking one from the caller -- a crew day cannot be attributed to a
      // branch the job does not belong to.
      const jr = await fetch(rest('rf_jobs?license_hash=eq.' + enc(licHash) + '&job_id=eq.' + enc(payload.job_id) + '&select=job_id,location_id'), { headers });
      if (jr.status === 404 || jr.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Jobs are not set up yet — run sql/sairnroofing_jobs_schema.sql in Supabase first.' } }); return; }
      const jRows = await jr.json();
      const job = Array.isArray(jRows) && jRows[0];
      if (!job) { res.status(404).json({ error: { code: 'NO_JOB', message: 'No such job — create the job before scheduling a day on it' } }); return; }
      const blob = Object.assign({}, payload);
      ['id', 'job_id', 'location_id', 'scheduled_date', 'status', 'crew'].forEach((k) => { delete blob[k]; });
      const r = await fetch(rest('rf_schedule?on_conflict=license_hash,schedule_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairnroofing', schedule_id: String(payload.id),
          job_id: String(payload.job_id),
          location_id: job.location_id || roofingLocations.DEFAULT_LOCATION_ID,
          scheduled_date: payload.scheduled_date,
          status: payload.status || 'planned',
          crew: roofingLocations.normalizeCrew(payload.crew),
          data: blob, created_by: session.employee_id, updated_at: nowISO()
        })
      });
      if (r.status === 404 || r.status === 400) {
        const bt = await r.text();
        if (/relation .* does not exist|does not exist/i.test(bt)) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Scheduling is not set up yet — run sql/sairnroofing_locations_schema.sql in Supabase first.' } }); return; }
        res.status(400).json({ error: { message: 'Data store rejected the schedule entry', detail: bt } }); return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const saved = Array.isArray(rows) && rows[0];
      // WHO IS NOW DOUBLE-BOOKED, reported WITH the save (2026-09-02, gap A2).
      // It does NOT refuse, deliberately, and that is the opposite call from
      // the subcontractor assignment gate above: two jobs in one day is a
      // normal roofing day -- a small repair in the morning and another on the
      // same street after lunch -- so a hard block would be wrong, and a wrong
      // block is how a gate gets routed around. What is wrong is doing it by
      // ACCIDENT, so it is named loudly and the operator decides.
      //
      // Computed AFTER the write against the stored row, not against the
      // payload, so what is reported is what is actually on the board.
      let conflictReport = null;
      try {
        const cr = await fetch(rest('rf_schedule?license_hash=eq.' + enc(licHash) +
          '&scheduled_date=eq.' + enc(String(payload.scheduled_date)) +
          '&select=schedule_id,job_id,scheduled_date,status,crew'), { headers });
        if (cr.ok) {
          const sameDay = await cr.json();
          const cap = require('./_lib/roofing-crew-capacity');
          const rep = cap.conflictsFor({
            schedule: Array.isArray(sameDay) ? sameDay : [],
            candidate: saved || { schedule_id: String(payload.id), job_id: String(payload.job_id), scheduled_date: payload.scheduled_date, status: payload.status || 'planned', crew: roofingLocations.normalizeCrew(payload.crew) }
          });
          if (rep.ok) conflictReport = rep;
        }
      } catch (e) {
        // A failure to REPORT must never fail the save that already happened.
        // Left null, which the client renders as "not checked" rather than as
        // "clear" -- an unchecked day shown as clear is the silent failure.
        console.error('rf_schedule conflict report failed:', e && e.message);
      }
      res.status(200).json({ ok: true, data: saved ? Object.assign({}, saved.data, { schedule_id: saved.schedule_id, job_id: saved.job_id, location_id: saved.location_id, scheduled_date: saved.scheduled_date, status: saved.status, crew: saved.crew, created_by: saved.created_by }) : payload, conflicts: conflictReport });
      return;
    }
    // ── CREW LOAD (2026-09-02, gap A2) ─────────────────────────────────────
    // Compute-only. Reads the schedule over an explicit range and reports who
    // is on how many jobs each day. Writes nothing: looking at whether the
    // week is overbooked must never change the week -- the same shape as
    // rf_certifications 'evaluate' and rf_claim_agreements 'agreement_status'.
    if (resource === 'rf_schedule' && action === 'crew_load') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      // Management-level: a crew-wide capacity board shows who else is working
      // and where, which is exactly the aggregate the narrow tier is kept from
      // on the schedule read above. Letting it through here would be a way
      // around that filter.
      if (!rfAuth.MANAGEMENT_ROLES[session.role] && !rfAuth.BROAD_READ_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Crew load across the company is management-level information' } });
        return;
      }
      const cap = require('./_lib/roofing-crew-capacity');
      // from/to come from the CALLER and the engine refuses without them. A
      // server-side "this week" would compute a contractor's week in UTC.
      const from = (payload && payload.from) || null;
      const to = (payload && payload.to) || null;
      if (!from || !to) { res.status(400).json({ error: { code: 'NO_RANGE', message: 'crew_load requires from and to (YYYY-MM-DD)' } }); return; }
      const r = await fetch(rest('rf_schedule?license_hash=eq.' + enc(licHash) +
        '&scheduled_date=gte.' + enc(String(from)) + '&scheduled_date=lte.' + enc(String(to)) +
        '&select=schedule_id,job_id,scheduled_date,status,crew'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, provisioned: false, load: null }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const ev = cap.crewLoad({ schedule: rows || [], from: from, to: to });
      if (!ev.ok) { res.status(400).json({ error: ev.error }); return; }
      res.status(200).json({ ok: true, provisioned: true, load: ev });
      return;
    }
    // A crew member marking their own day. Status ONLY -- it cannot move the
    // day, change the job, or add anyone to the crew, so it is not a backdoor
    // around the management-only write above.
    if (resource === 'rf_schedule' && action === 'set_status') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const schedId = payload && payload.schedule_id;
      const status = payload && payload.status;
      if (!schedId) { res.status(400).json({ error: { message: 'set_status requires payload.schedule_id' } }); return; }
      if (roofingLocations.SCHEDULE_STATUSES.indexOf(status) === -1) { res.status(400).json({ error: { message: 'status must be one of: ' + roofingLocations.SCHEDULE_STATUSES.join(', ') } }); return; }
      const sr = await fetch(rest('rf_schedule?license_hash=eq.' + enc(licHash) + '&schedule_id=eq.' + enc(schedId) + '&select=schedule_id,job_id,crew'), { headers });
      if (sr.status === 404 || sr.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Scheduling is not set up yet — run sql/sairnroofing_locations_schema.sql in Supabase first.' } }); return; }
      const sRows = await sr.json();
      const entry = Array.isArray(sRows) && sRows[0];
      if (!entry) { res.status(404).json({ error: { code: 'NO_SCHEDULE', message: 'No such scheduled day' } }); return; }
      const jr2 = await fetch(rest('rf_jobs?license_hash=eq.' + enc(licHash) + '&job_id=eq.' + enc(entry.job_id) + '&select=assigned_employee_id'), { headers });
      const jRows2 = (jr2.status === 404 || jr2.status === 400) ? [] : await jr2.json();
      const assignee = (Array.isArray(jRows2) && jRows2[0] && jRows2[0].assigned_employee_id) || null;
      if (!roofingLocations.canSeeSchedule(session, entry, assignee, rfAuth.MANAGEMENT_ROLES, rfAuth.BROAD_READ_ROLES)) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'You are not on that day' } });
        return;
      }
      const r = await fetch(rest('rf_schedule?license_hash=eq.' + enc(licHash) + '&schedule_id=eq.' + enc(schedId)), {
        method: 'PATCH',
        headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
        body: JSON.stringify({ status: status, updated_at: nowISO() })
      });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const saved = Array.isArray(rows) && rows[0];
      res.status(200).json({ ok: true, schedule_id: schedId, status: saved ? saved.status : status });
      return;
    }

    // ── SAIRNROOFING: the claim assignment gate, factored out ────────────────────────────────
    // Phase 5 adds three more branches that all need the SAME check the claim
    // read, the photo branches and `reconcile` already perform: load the claim
    // server-side and refuse a narrow-tier caller who is not its assignee.
    // Written once here rather than a fourth, fifth and sixth hand-copy --
    // api/rf-auth.js's own header names duplicated role lists as SAIRNsenior's
    // root cause, and three more copies is how that recurs.
    //
    // DELIBERATELY NOT retrofitted onto the existing 3b/3c branches in this
    // commit. Those are live and verified; rewriting them is a separate change
    // with its own verification, not something to fold into a feature commit.
    // Logged as open work instead.
    //
    // Returns { ok: true, claim } or { ok: false } having ALREADY sent the
    // response, so every caller can simply `if (!gate.ok) return;`.
    const rfClaimGate = async (lh, hdrs, claimId, session, response) => {
      const cr = await fetch(rest('rf_claims?license_hash=eq.' + enc(lh) + '&claim_id=eq.' + enc(claimId) + '&select=claim_id,assigned_employee_id,data'), { headers: hdrs });
      if (cr.status === 404 || cr.status === 400) {
        response.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Claims are not set up yet — run sql/sairnroofing_claims_schema.sql in Supabase first.' } });
        return { ok: false };
      }
      const rows = await cr.json();
      const claim = Array.isArray(rows) && rows[0];
      if (!claim) {
        response.status(404).json({ error: { code: 'NO_CLAIM', message: 'No such claim' } });
        return { ok: false };
      }
      if (!rfAuth.MANAGEMENT_ROLES[session.role] && !rfAuth.BROAD_READ_ROLES[session.role] && claim.assigned_employee_id !== session.employee_id) {
        response.status(403).json({ error: { code: 'FORBIDDEN', message: 'You can only work on a claim assigned to you' } });
        return { ok: false };
      }
      return { ok: true, claim: claim };
    };

    // ── SAIRNROOFING: contingency agreement + rescission rules (2026-08-25, Phase 5) ─────────
    // The last piece of §5.3. rf_contingency_rules is the per-state rule store
    // (read by anyone signed in -- a foreman standing on a roof needs to know
    // the cancellation window; write is management-only, because a rescission
    // rule is a compliance assertion, not job data).
    if (resource === 'rf_contingency_rules' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const r = await fetch(rest('rf_contingency_rules?license_hash=eq.' + enc(licHash) + '&select=rule_id,state,trigger_event,count,unit,business_day_basis,status,data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: rows || [], provisioned: true });
      return;
    }
    if (resource === 'rf_contingency_rules' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!rfAuth.MANAGEMENT_ROLES[session.role]) { res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can set a contingency rule' } }); return; }
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'rf_contingency_rules payload.id is required' } }); return; }
      // The engine refuses to compute from a rule with no citation; refuse to
      // STORE one too, so a bad row never reaches a contractor's screen.
      const ruleProblems = roofingAgreements.validateRule({
        trigger: payload.trigger_event, count: Number(payload.count), unit: payload.unit,
        authority: payload.data && payload.data.authority
      });
      if (ruleProblems.length) { res.status(400).json({ error: { message: 'rf_contingency_rules: ' + ruleProblems.join('; ') } }); return; }
      const r = await fetch(rest('rf_contingency_rules?on_conflict=license_hash,rule_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairnroofing', rule_id: String(payload.id),
          state: String(payload.state || '').toUpperCase(), trigger_event: payload.trigger_event,
          count: Number(payload.count), unit: payload.unit,
          business_day_basis: payload.business_day_basis || null,
          effective_from: payload.effective_from || nowISO().slice(0, 10),
          effective_to: payload.effective_to || null,
          status: payload.status || 'active', data: payload.data || {},
          verified_by: session.employee_id, updated_at: nowISO()
        })
      });
      if (r.status === 404 || r.status === 400) {
        const bt = await r.text();
        if (/relation .* does not exist|does not exist/i.test(bt)) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Contingency rules are not set up yet — run sql/sairnroofing_agreements_schema.sql in Supabase first.' } }); return; }
        res.status(400).json({ error: { message: 'Data store rejected the rule', detail: bt } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: Array.isArray(rows) && rows[0] });
      return;
    }
    // rf_claim_agreements: APPEND-ONLY. There is no update verb and no update
    // grant -- a rescission is a NEW row naming the executed one it supersedes.
    if (resource === 'rf_claim_agreements' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const claimId = payload && payload.claim_id;
      if (!claimId) { res.status(400).json({ error: { message: 'rf_claim_agreements read requires payload.claim_id' } }); return; }
      const gate = await rfClaimGate(licHash, headers, claimId, session, res);
      if (!gate.ok) return;
      const r = await fetch(rest('rf_claim_agreements?license_hash=eq.' + enc(licHash) + '&claim_id=eq.' + enc(claimId) + '&select=agreement_id,claim_id,event_type,supersedes,recorded_by,data,created_at'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      // The signature image is up to 1.5MB and NOTHING in the panel renders it
      // -- the record table shows who signed and when. Shipping it on every
      // claim open would be a megabyte per agreement for nothing, so it is
      // stripped unless a caller explicitly asks (payload.include_signature),
      // which is what a future "show me the signed copy" view would pass.
      const withSig = payload && payload.include_signature === true;
      const data = (rows || []).map((x) => {
        const blob = Object.assign({}, x.data || {});
        if (!withSig) { delete blob.signature_data; blob.has_signature = !!(x.data && x.data.signature_data); }
        return Object.assign(blob, {
          agreement_id: x.agreement_id, claim_id: x.claim_id, event_type: x.event_type,
          supersedes: x.supersedes, recorded_by: x.recorded_by, created_at: x.created_at
        });
      });
      res.status(200).json({ ok: true, data, provisioned: true });
      return;
    }
    if (resource === 'rf_claim_agreements' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const problems = roofingAgreements.validateAgreement(payload);
      if (problems.length) { res.status(400).json({ error: { message: 'rf_claim_agreements: ' + problems.join('; ') } }); return; }
      const gate = await rfClaimGate(licHash, headers, payload.claim_id, session, res);
      if (!gate.ok) return;
      // A rescission must name a real executed row on THIS claim. Checked
      // server-side against the stored chain, never trusted from the caller --
      // otherwise a stray supersedes value could void an agreement on a claim
      // the caller cannot even see.
      if (payload.event_type === 'rescinded') {
        const pr = await fetch(rest('rf_claim_agreements?license_hash=eq.' + enc(licHash) + '&claim_id=eq.' + enc(payload.claim_id) + '&agreement_id=eq.' + enc(payload.supersedes) + '&event_type=eq.executed&select=agreement_id'), { headers });
        const pRows = (pr.status === 404 || pr.status === 400) ? [] : await pr.json();
        if (!Array.isArray(pRows) || !pRows.length) {
          res.status(400).json({ error: { code: 'NO_SUCH_AGREEMENT', message: 'That claim has no executed agreement with the id being superseded' } });
          return;
        }
      }
      const dataBlob = Object.assign({}, payload);
      delete dataBlob.id; delete dataBlob.claim_id; delete dataBlob.event_type; delete dataBlob.supersedes;
      const r = await fetch(rest('rf_claim_agreements'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairnroofing', agreement_id: String(payload.id),
          claim_id: String(payload.claim_id), event_type: payload.event_type,
          supersedes: payload.supersedes || null,
          recorded_by: session.employee_id,   // server-stamped, never client-supplied
          data: dataBlob
        })
      });
      if (r.status === 404 || r.status === 400 || r.status === 409) {
        const bt = await r.text();
        if (/relation .* does not exist|does not exist/i.test(bt)) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Contingency agreements are not set up yet — run sql/sairnroofing_agreements_schema.sql in Supabase first.' } }); return; }
        if (/duplicate key|rfagr_license_hash_agreement_id_key|unique/i.test(bt)) { res.status(409).json({ error: { code: 'ALREADY_RECORDED', message: 'An agreement with that id already exists — append-only, ids are never reused' } }); return; }
        res.status(400).json({ error: { message: 'Data store rejected the agreement', detail: bt } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const saved = Array.isArray(rows) && rows[0];
      res.status(200).json({ ok: true, data: saved ? Object.assign({}, saved.data, { agreement_id: saved.agreement_id, event_type: saved.event_type, recorded_by: saved.recorded_by }) : payload });
      return;
    }
    // Compute-only: the rescission clock. Reads the claim's agreement chain and
    // the state rule server-side, runs the deterministic engine, writes nothing
    // -- the same discipline as 'reconcile' and money_summary. No LLM.
    if (resource === 'rf_claim_agreements' && action === 'agreement_status') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnroofing');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const claimId = payload && payload.claim_id;
      if (!claimId) { res.status(400).json({ error: { message: 'agreement_status requires payload.claim_id' } }); return; }
      const gate = await rfClaimGate(licHash, headers, claimId, session, res);
      if (!gate.ok) return;
      const ar = await fetch(rest('rf_claim_agreements?license_hash=eq.' + enc(licHash) + '&claim_id=eq.' + enc(claimId) + '&select=agreement_id,event_type,supersedes,data'), { headers });
      const aRows = (ar.status === 404 || ar.status === 400) ? [] : await ar.json();
      const events = (Array.isArray(aRows) ? aRows : []).map((x) => Object.assign({}, x.data || {}, {
        agreement_id: x.agreement_id, event_type: x.event_type, supersedes: x.supersedes
      }));
      // The state comes from the SIGNED AGREEMENT, not from the caller -- the
      // rule that governs is the one for the state the contract was signed in.
      const latestExec = events.filter((e) => e.event_type === 'executed').sort((a, b) => new Date(a.executed_at || 0) - new Date(b.executed_at || 0)).pop();
      const state = latestExec ? String(latestExec.state || '').toUpperCase() : null;
      let rule = null;
      if (state) {
        const rr = await fetch(rest('rf_contingency_rules?license_hash=eq.' + enc(licHash) + '&state=eq.' + enc(state) + '&status=eq.active&select=rule_id,state,trigger_event,count,unit,business_day_basis,data'), { headers });
        const rRows = (rr.status === 404 || rr.status === 400) ? [] : await rr.json();
        const row = Array.isArray(rRows) && rRows[0];
        if (row) {
          rule = Object.assign({}, row.data || {}, {
            rule_id: row.rule_id, state: row.state, trigger: row.trigger_event,
            count: Number(row.count), unit: row.unit, business_day_basis: row.business_day_basis
          });
        }
      }
      // The Colorado-shaped trigger needs the insurer's written-denial date,
      // which lives on the claim record, not on the agreement.
      const status = roofingAgreements.evaluateAgreement({
        rule: rule, events: events,
        denial_at: (gate.claim.data && gate.claim.data.insurer_denial_at) || null,
        now: nowISO()
      });
      res.status(200).json({ ok: true, provisioned: true, claim_id: claimId, state: state, agreement_status: status });
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
      // ── PHARMACY-ORDER REVIEW GATE (2026-08-22, Phase 3 item 1) ────────────────────────
      // A pharmacy-sourced order arrives via api/alf-pharmacy.js as pending_review and is
      // NOT active on the MAR until a clinician accepts it. Removing manual transcription
      // is the safety win; removing clinical review would not be, so acceptance is a real
      // gated action rather than an automatic consequence of delivery.
      if (payload.entry_type === 'medication_order' && payload.pharmacy_status !== undefined) {
        // med_aide can read the MAR and administer, but must never be the one who clears a
        // pharmacy order into active use -- that is a clinical-decision act, same boundary
        // that already keeps medication_order creation to owner/nursing.
        if (!ALF_MAR_ORDER_ROLES[session.role]) {
          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management or nursing can review a pharmacy order' } });
          return;
        }
        const allowedStatuses = { pending_review: true, accepted: true, rejected: true };
        if (!allowedStatuses[payload.pharmacy_status]) {
          res.status(400).json({ error: { message: 'pharmacy_status must be one of: ' + Object.keys(allowedStatuses).join(', ') } });
          return;
        }
        // Stamped from the real session, never trusted from the client -- same discipline as
        // care_level_history.changed_by and the payer/compliance rules' verified_by.
        if (payload.pharmacy_status === 'accepted' || payload.pharmacy_status === 'rejected') {
          marData.reviewed_by = session.employee_id;
          marData.reviewed_at = nowISO();
        }
      }
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
    // ── SAIRNCARE: documentation -> charges (2026-08-22, Phase 3 item 2) ───────────────────
    // Reads the resident's REAL recorded documentation for the month (MAR administrations,
    // ADL assessments, activity attendance) and returns the charge lines it implies, each
    // carrying the id of the exact document behind it. Derivation logic is PURE and lives in
    // api/_lib/care-charges.js.
    //
    // WRITES NOTHING. The month's invoice is still created by the existing alf_billing write
    // path; this only removes the manual re-keying step between what was documented and what
    // gets billed, which is where revenue leaks. A documented service with no configured rate
    // comes back in `unpriced` rather than being billed at zero or silently dropped.
    if (resource === 'alf_billing' && action === 'derive_charges') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!ALF_MANAGEMENT_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Billing is not available to your role' } });
        return;
      }
      if (!payload || !payload.resident_id || !payload.month) {
        res.status(400).json({ error: { message: 'derive_charges requires resident_id and month' } });
        return;
      }
      const events = [];
      // MAR administrations -- one documented dose given is one documented service.
      const marR = await fetch(rest('alf_mar?license_hash=eq.' + enc(licHash) + '&resident_id=eq.' + enc(String(payload.resident_id)) + '&select=entry_id,entry_type,data'), { headers });
      if (marR.ok) {
        const marRows = await marR.json().catch(() => []);
        (marRows || []).forEach((row) => {
          if (row.entry_type !== 'administration') return;
          const d = row.data || {};
          // Only a dose actually GIVEN is billable. A refusal or a hold is real
          // documentation but is not a delivered service, and billing it would be
          // billing for care that did not happen.
          if (d.status && d.status !== 'given') return;
          const at = String(d.administered_at || d.recorded_at || '');
          events.push({
            id: row.entry_id, type: 'medication_administration',
            resident_id: String(payload.resident_id), date: at.slice(0, 10),
            description: d.medication_name || d.name || ''
          });
        });
      }
      // ADL assessments live inside the resident's own alf_clients record.
      const cliR = await fetch(rest('alf_clients?license_hash=eq.' + enc(licHash) + '&client_id=eq.' + enc(String(payload.resident_id)) + '&select=data'), { headers });
      if (cliR.ok) {
        const cliRows = await cliR.json().catch(() => []);
        const cd = (Array.isArray(cliRows) && cliRows[0] && cliRows[0].data) || {};
        (cd.adl_assessments || []).forEach((a) => {
          events.push({
            id: a.id, type: 'adl_assessment',
            resident_id: String(payload.resident_id), date: a.date, description: 'Katz ADL assessment'
          });
        });
      }
      // Activity attendance.
      const actR = await fetch(rest('alf_activities?license_hash=eq.' + enc(licHash) + '&select=entry_id,data'), { headers });
      if (actR.ok) {
        const actRows = await actR.json().catch(() => []);
        (actRows || []).forEach((row) => {
          const d = row.data || {};
          const attendees = d.attendees || d.attendee_ids || [];
          if (Array.isArray(attendees) && attendees.indexOf(String(payload.resident_id)) !== -1) {
            events.push({
              id: row.entry_id, type: 'activity_attendance',
              resident_id: String(payload.resident_id), date: d.date || '', description: d.name || d.title || ''
            });
          }
        });
      }
      const facR = await fetch(rest('alf_facility?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      const facRows = facR.ok ? await facR.json().catch(() => []) : [];
      const rateCard = (Array.isArray(facRows) && facRows[0] && facRows[0].data) || {};
      const derived = careCharges.deriveCharges({
        month: payload.month, resident_id: String(payload.resident_id), rate_card: rateCard, events: events
      });
      if (!derived.ok) { res.status(200).json(derived); return; }
      // If the month's invoice already exists, show exactly what a regenerate would
      // change -- the audit trail that replaces the manual reconciliation.
      const invId = 'INV-' + payload.resident_id + '-' + payload.month;
      const invR = await fetch(rest('alf_billing?license_hash=eq.' + enc(licHash) + '&entry_id=eq.' + enc(invId) + '&select=data'), { headers });
      const invRows = invR.ok ? await invR.json().catch(() => []) : [];
      const priorLines = (Array.isArray(invRows) && invRows[0] && invRows[0].data && invRows[0].data.charge_lines) || [];
      derived.reconciliation_vs_invoice = careCharges.reconcileAgainstInvoice(derived, priorLines);
      derived.invoice_exists = !!(Array.isArray(invRows) && invRows.length);
      res.status(200).json(derived);
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

    // ── SAIRNCARE: alf_payer_rules + alf_claim_routes (2026-08-22, Phase 1) ─────────────────
    // Payer/billing-routing engine. The rule-matching and routing logic itself is PURE and
    // lives in api/_lib/payer-routing.js so it can be tested against the source bulletins'
    // own worked examples without any infrastructure; this branch is only storage + gating.
    //
    // GATE: read is open to any authenticated employee (a Med Aide needs to know a resident's
    // stay is HCBS-billed and that room and board is excluded); write is MANAGEMENT-ONLY,
    // same as alf_billing, because these rules determine what gets billed to a government
    // payer. A 'route' action is read-only in the database sense (it computes a decision) but
    // is likewise management-gated, because its output is a billing instruction.
    //
    // WHY RULES ARE DATA: Indiana published a billing mandate on 2025-12-04 effective
    // 2026-01-01, then paused it on 2025-12-31 -- one day before it took effect. Hardcoding
    // would have shipped a rule obsolete before its own effective date.
    const ALF_PAYER_PROGRAMS = { medicaid_hcbs: true, hospice_ma: true };
    const ALF_RULE_STATUSES = { active: true, never_in_force: true };
    if (resource === 'alf_payer_rules' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const r = await fetch(rest('alf_payer_rules?license_hash=eq.' + enc(licHash) + '&select=rule_id,state,program,effective_from,effective_to,status,data,verified_by'), { headers });
      if (r.status === 404 || r.status === 400) {
        res.status(200).json({ ok: true, data: [], provisioned: false, coverage: { have: 0, need: 0, covered_states: [], uncovered_states: [] } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const data = (rows || []).map((x) => ({
        rule_id: x.rule_id, state: x.state, program: x.program,
        effective_from: x.effective_from, effective_to: x.effective_to,
        status: x.status || 'active', verified_by: x.verified_by || '', data: x.data || {}
      }));
      // Coverage is computed against the states the caller says it cares about, so an
      // uncovered state shows up as a real gap rather than an empty list that reads like
      // "nothing to bill". Same {have, need} contract as alf_signals.
      const claimed = Array.isArray(payload && payload.claimed_states) && payload.claimed_states.length
        ? payload.claimed_states.map((s) => String(s).toUpperCase())
        : Array.from(new Set(data.filter((x) => x.program === 'medicaid_hcbs').map((x) => x.state)));
      res.status(200).json({ ok: true, data, provisioned: true, coverage: payerRouting.hcbsCoverage(data, claimed) });
      return;
    }
    if (resource === 'alf_payer_rules' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!ALF_MANAGEMENT_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can change billing rules' } });
        return;
      }
      if (!payload || !payload.rule_id || !payload.state || !payload.program || !payload.effective_from) {
        res.status(400).json({ error: { message: 'alf_payer_rules requires rule_id, state, program, and effective_from' } });
        return;
      }
      if (!ALF_PAYER_PROGRAMS[payload.program]) {
        res.status(400).json({ error: { message: 'program must be one of: ' + Object.keys(ALF_PAYER_PROGRAMS).join(', ') } });
        return;
      }
      const ruleState = String(payload.state).trim().toUpperCase();
      // 'US' is allowed alongside the USPS list because the hospice/MA rule is federal, not
      // state-specific -- rejecting it would force a real federal rule to masquerade as a state one.
      if (ruleState !== 'US' && !ALF_US_STATES[ruleState]) {
        res.status(400).json({ error: { code: 'BAD_STATE', message: 'state must be a two-letter US state, DC, or US for a federal rule' } });
        return;
      }
      const ruleStatus = payload.status || 'active';
      if (!ALF_RULE_STATUSES[ruleStatus]) {
        res.status(400).json({ error: { message: 'status must be one of: ' + Object.keys(ALF_RULE_STATUSES).join(', ') } });
        return;
      }
      if (payload.effective_to && payload.effective_to < payload.effective_from) {
        res.status(400).json({ error: { message: 'effective_to cannot precede effective_from — mark a rule that never took effect with status never_in_force instead' } });
        return;
      }
      // A rule with no resolvable authority is refused outright. A billing rule nobody can
      // trace to a real published source is exactly what should never end up determining a
      // government-payer claim -- same standard SAIRNlaw's deadline rules already hold.
      const ruleData = payload.data || {};
      const auth = ruleData.authority || {};
      if (!auth.citation || !/^https?:\/\//.test(String(auth.url || ''))) {
        res.status(400).json({ error: { code: 'NO_AUTHORITY', message: 'Every billing rule needs an authority citation and a resolvable source URL' } });
        return;
      }
      const r = await fetch(rest('alf_payer_rules?on_conflict=license_hash,rule_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairncare', rule_id: String(payload.rule_id),
          state: ruleState, program: payload.program,
          effective_from: payload.effective_from, effective_to: payload.effective_to || null,
          status: ruleStatus, data: ruleData,
          // Stamped from the real session, never trusted from the client -- same as
          // care_level_history's changed_by and SAIRNlaw's verified_by.
          verified_by: session.employee_id, updated_at: nowISO()
        })
      });
      if (r.status === 404 || r.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Billing rules are not set up yet — run sql/sairncare_payer_rules_schema.sql in Supabase first.' } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: Object.assign({ rule_id: payload.rule_id, state: ruleState, verified_by: session.employee_id }, ruleData) });
      return;
    }
    // Compute a routing decision. Deliberately does NOT write anything -- persisting the
    // decision is a separate explicit alf_claim_routes write, so previewing a route can
    // never silently create a billing record.
    if (resource === 'alf_payer_rules' && action === 'route') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!ALF_MANAGEMENT_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can route a claim' } });
        return;
      }
      if (!payload || !payload.program || !payload.service_month) {
        res.status(400).json({ error: { message: 'route requires program and service_month' } });
        return;
      }
      const rr = await fetch(rest('alf_payer_rules?license_hash=eq.' + enc(licHash) + '&select=rule_id,state,program,effective_from,effective_to,status,data'), { headers });
      if (rr.status === 404 || rr.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Billing rules are not set up yet — run sql/sairncare_payer_rules_schema.sql in Supabase first.' } });
        return;
      }
      const ruleRows = await rr.json();
      if (!rr.ok) return upstream(res, ruleRows);
      const wantState = String(payload.state || (payload.program === 'hospice_ma' ? 'US' : '')).trim().toUpperCase();
      const candidates = (ruleRows || []).filter((x) =>
        x.program === payload.program && x.state === wantState &&
        payerRouting.ruleInForce({ effective_from: x.effective_from, effective_to: x.effective_to, status: x.status }, payload.service_month)
      );
      if (!candidates.length) {
        // Names the state explicitly rather than returning an empty success -- an uncovered
        // state must never look like "nothing to bill".
        res.status(200).json({
          ok: false,
          error: {
            code: 'NO_RULE_FOR_STATE',
            message: 'No ' + payload.program + ' rule is loaded and in force for ' + (wantState || '(no state given)') +
                     ' in ' + payload.service_month + '. This state is not covered — do not bill it from this app until a real, sourced rule is loaded.'
          }
        });
        return;
      }
      if (candidates.length > 1) {
        // Refuses rather than picking one, same as SAIRNlaw's AMBIGUOUS_RULE.
        res.status(200).json({
          ok: false,
          error: {
            code: 'AMBIGUOUS_RULE',
            message: 'More than one ' + payload.program + ' rule is in force for ' + wantState + ' in ' + payload.service_month +
                     ': ' + candidates.map((c) => c.rule_id).join(', ') + '. Narrow the effective dates so exactly one applies.'
          }
        });
        return;
      }
      const rule = Object.assign({}, candidates[0]);
      const result = payload.program === 'hospice_ma'
        ? payerRouting.routeHospiceClaim(Object.assign({}, payload, { rule: rule }))
        : payerRouting.routeHcbsClaim(Object.assign({}, payload, { rule: rule }));
      res.status(200).json(result);
      return;
    }
    if (resource === 'alf_claim_routes' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!ALF_MANAGEMENT_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Billing is not available to your role' } });
        return;
      }
      const r = await fetch(rest('alf_claim_routes?license_hash=eq.' + enc(licHash) + '&select=entry_id,resident_id,service_month,data,decided_by,created_at'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const data = (rows || []).map((x) => Object.assign({
        id: x.entry_id, resident_id: x.resident_id, service_month: x.service_month,
        decided_by: x.decided_by || '', created_at: x.created_at
      }, x.data));
      res.status(200).json({ ok: true, data, provisioned: true });
      return;
    }
    if (resource === 'alf_claim_routes' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!ALF_MANAGEMENT_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Billing is not available to your role' } });
        return;
      }
      if (!payload || !payload.id || !payload.resident_id || !payload.service_month) {
        res.status(400).json({ error: { message: 'alf_claim_routes requires id, resident_id, and service_month' } });
        return;
      }
      // Append-only: a routing decision records how a real claim was billed. If the
      // determination changes, that is a NEW decision with its own timestamp, not an edit
      // erasing what was previously believed and acted upon. Same rule as alf_mar events.
      const existingR = await fetch(rest('alf_claim_routes?license_hash=eq.' + enc(licHash) + '&entry_id=eq.' + enc(String(payload.id)) + '&select=id'), { headers });
      const existingRows = existingR.ok ? await existingR.json() : [];
      if (Array.isArray(existingRows) && existingRows.length > 0) {
        res.status(409).json({ error: { code: 'ALREADY_RECORDED', message: 'This routing decision has already been recorded and cannot be overwritten' } });
        return;
      }
      const routeData = Object.assign({}, payload);
      delete routeData.id; delete routeData.resident_id; delete routeData.service_month;
      const r = await fetch(rest('alf_claim_routes'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairncare', entry_id: String(payload.id),
          resident_id: String(payload.resident_id), service_month: String(payload.service_month),
          data: routeData, decided_by: session.employee_id
        })
      });
      if (r.status === 404 || r.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Claim routing is not set up yet — run sql/sairncare_payer_rules_schema.sql in Supabase first.' } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: Object.assign({ id: payload.id, resident_id: payload.resident_id, service_month: payload.service_month, decided_by: session.employee_id }, routeData) });
      return;
    }

    // ── SAIRNCARE: alf_compliance_rules + alf_staff_credentials (2026-08-22, Phase 2) ───────
    // Compliance-rules engine (staffing ratios, training hours, licensure model) plus the
    // staff credentialing store the training checks read from. Evaluation logic is PURE and
    // lives in api/_lib/compliance-rules.js; this branch is storage + gating only, same split
    // as Phase 1's payer-routing.
    //
    // GATE: rules are readable by any authenticated employee (a caregiver has a real interest
    // in the training hours their own state requires of them) and writable by management only.
    // Credential records are readable by management and nursing (nursing holds facility-wide
    // clinical oversight and is who actually chases an expiring certification), and a staff
    // member may always read their OWN records. Writes are management-only: a training record
    // is an assertion about someone's qualifications, and self-certification would defeat it.
    const ALF_CRED_READ_ROLES = { owner: true, billing: true, nursing: true };
    const ALF_COMPLIANCE_TYPES = { staffing: true, training: true, licensure: true };
    const ALF_CRED_RECORD_TYPES = { training_hours: true, credential: true };
    if (resource === 'alf_compliance_rules' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const r = await fetch(rest('alf_compliance_rules?license_hash=eq.' + enc(licHash) + '&select=rule_id,state,requirement_type,facility_class,effective_from,effective_to,status,data,verified_by'), { headers });
      if (r.status === 404 || r.status === 400) {
        res.status(200).json({ ok: true, data: [], provisioned: false, coverage: { have: 0, need: 0, detail: [], uncovered_states: [] } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const data = (rows || []).map((x) => ({
        rule_id: x.rule_id, state: x.state, requirement_type: x.requirement_type,
        facility_class: x.facility_class, effective_from: x.effective_from, effective_to: x.effective_to,
        status: x.status || 'active', verified_by: x.verified_by || '', data: x.data || {}
      }));
      const claimed = Array.isArray(payload && payload.claimed_states) && payload.claimed_states.length
        ? payload.claimed_states.map((s) => String(s).toUpperCase())
        : Array.from(new Set(data.map((x) => x.state)));
      res.status(200).json({ ok: true, data, provisioned: true, coverage: complianceRules.complianceCoverage(data, claimed) });
      return;
    }
    if (resource === 'alf_compliance_rules' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!ALF_MANAGEMENT_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can change compliance rules' } });
        return;
      }
      if (!payload || !payload.rule_id || !payload.state || !payload.requirement_type || !payload.effective_from) {
        res.status(400).json({ error: { message: 'alf_compliance_rules requires rule_id, state, requirement_type, and effective_from' } });
        return;
      }
      if (!ALF_COMPLIANCE_TYPES[payload.requirement_type]) {
        res.status(400).json({ error: { message: 'requirement_type must be one of: ' + Object.keys(ALF_COMPLIANCE_TYPES).join(', ') } });
        return;
      }
      const cState = String(payload.state).trim().toUpperCase();
      if (!ALF_US_STATES[cState]) {
        res.status(400).json({ error: { code: 'BAD_STATE', message: 'state must be a two-letter US state or DC code' } });
        return;
      }
      const cStatus = payload.status || 'active';
      if (!ALF_RULE_STATUSES[cStatus]) {
        res.status(400).json({ error: { message: 'status must be one of: ' + Object.keys(ALF_RULE_STATUSES).join(', ') } });
        return;
      }
      if (payload.effective_to && payload.effective_to < payload.effective_from) {
        res.status(400).json({ error: { message: 'effective_to cannot precede effective_from — mark a rule that never took effect with status never_in_force instead' } });
        return;
      }
      // Same standard as the payer rules: a requirement nobody can trace to a published
      // source must never end up telling a facility it is or is not compliant.
      const cData = payload.data || {};
      const cAuth = cData.authority || {};
      if (!cAuth.citation || !/^https?:\/\//.test(String(cAuth.url || ''))) {
        res.status(400).json({ error: { code: 'NO_AUTHORITY', message: 'Every compliance rule needs an authority citation and a resolvable source URL' } });
        return;
      }
      const r = await fetch(rest('alf_compliance_rules?on_conflict=license_hash,rule_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairncare', rule_id: String(payload.rule_id),
          state: cState, requirement_type: payload.requirement_type,
          facility_class: payload.facility_class || null,
          effective_from: payload.effective_from, effective_to: payload.effective_to || null,
          status: cStatus, data: cData, verified_by: session.employee_id, updated_at: nowISO()
        })
      });
      if (r.status === 404 || r.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Compliance rules are not set up yet — run sql/sairncare_compliance_schema.sql in Supabase first.' } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: Object.assign({ rule_id: payload.rule_id, state: cState, verified_by: session.employee_id }, cData) });
      return;
    }
    // Compute a compliance finding. Reads rules AND, for training checks, the real recorded
    // credential hours. Writes nothing.
    if (resource === 'alf_compliance_rules' && action === 'evaluate') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!payload || !payload.requirement_type || !payload.state) {
        res.status(400).json({ error: { message: 'evaluate requires state and requirement_type' } });
        return;
      }
      const rr = await fetch(rest('alf_compliance_rules?license_hash=eq.' + enc(licHash) + '&select=rule_id,state,requirement_type,facility_class,effective_from,effective_to,status,data'), { headers });
      if (rr.status === 404 || rr.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Compliance rules are not set up yet — run sql/sairncare_compliance_schema.sql in Supabase first.' } });
        return;
      }
      const ruleRows = await rr.json();
      if (!rr.ok) return upstream(res, ruleRows);
      const opts = Object.assign({}, payload, { on_date: payload.on_date || nowISO().slice(0, 10) });
      let result;
      if (payload.requirement_type === 'staffing') result = complianceRules.evaluateStaffing(ruleRows || [], opts);
      else if (payload.requirement_type === 'licensure') result = complianceRules.describeLicensure(ruleRows || [], opts);
      else result = complianceRules.evaluateTraining(ruleRows || [], opts);
      res.status(200).json(result);
      return;
    }
    if (resource === 'alf_staff_credentials' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const r = await fetch(rest('alf_staff_credentials?license_hash=eq.' + enc(licHash) + '&select=entry_id,staff_id,record_type,data,recorded_by,created_at'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      let out = rows || [];
      // A staff member outside the credentialing roles sees only their own records --
      // enough to know what training they personally owe, without exposing the roster's
      // qualifications. Same minimum-necessary reasoning as the resident privacy gate.
      if (!ALF_CRED_READ_ROLES[session.role]) {
        out = out.filter((x) => x.staff_id === session.employee_id);
      }
      const data = out.map((x) => Object.assign({
        id: x.entry_id, staff_id: x.staff_id, record_type: x.record_type,
        recorded_by: x.recorded_by || '', created_at: x.created_at
      }, x.data));
      res.status(200).json({ ok: true, data, provisioned: true, scoped_to_self: !ALF_CRED_READ_ROLES[session.role] });
      return;
    }
    if (resource === 'alf_staff_credentials' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!ALF_MANAGEMENT_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can record a training or credential entry' } });
        return;
      }
      if (!payload || !payload.id || !payload.staff_id || !payload.record_type) {
        res.status(400).json({ error: { message: 'alf_staff_credentials requires id, staff_id, and record_type' } });
        return;
      }
      if (!ALF_CRED_RECORD_TYPES[payload.record_type]) {
        res.status(400).json({ error: { message: 'record_type must be one of: ' + Object.keys(ALF_CRED_RECORD_TYPES).join(', ') } });
        return;
      }
      if (payload.record_type === 'training_hours' && !(Number(payload.hours) > 0)) {
        res.status(400).json({ error: { message: 'A training_hours record needs a positive hours value' } });
        return;
      }
      // Append-only: a completed-training assertion is exactly the class of record that must
      // not be quietly edited later. A correction is a NEW entry, never an overwrite.
      const existingR = await fetch(rest('alf_staff_credentials?license_hash=eq.' + enc(licHash) + '&entry_id=eq.' + enc(String(payload.id)) + '&select=id'), { headers });
      const existingRows = existingR.ok ? await existingR.json() : [];
      if (Array.isArray(existingRows) && existingRows.length > 0) {
        res.status(409).json({ error: { code: 'ALREADY_RECORDED', message: 'This credential record has already been recorded and cannot be overwritten' } });
        return;
      }
      const credData = Object.assign({}, payload);
      delete credData.id; delete credData.staff_id; delete credData.record_type;
      const r = await fetch(rest('alf_staff_credentials'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairncare', entry_id: String(payload.id),
          staff_id: String(payload.staff_id), record_type: payload.record_type,
          data: credData, recorded_by: session.employee_id
        })
      });
      if (r.status === 404 || r.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Staff credentialing is not set up yet — run sql/sairncare_compliance_schema.sql in Supabase first.' } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: Object.assign({ id: payload.id, staff_id: payload.staff_id, record_type: payload.record_type, recorded_by: session.employee_id }, credData) });
      return;
    }

    // ── SAIRNCARE: alf_op_audits -- operational-audit layer (2026-08-22, Phase 3 item 5) ────
    // Food safety, sanitation, emergency-preparedness drills. See
    // sql/sairncare_op_audit_schema.sql for why this is deliberately NOT part of the
    // clinical eMAR. Evaluation logic (temperature thresholds, cooling stages, drill
    // intervals) is PURE and lives in api/_lib/op-audit.js.
    //
    // GATE, and it is intentionally the INVERSE of alf_mar's shape:
    //   WRITE  -- any authenticated employee. The people who actually take a cooler
    //             temperature or run an evacuation drill are dietary, housekeeping and
    //             maintenance staff. They have no business in the MAR, and locking them
    //             out of their own compliance log to keep them out of the MAR would make
    //             the log useless. Recording an observation is not a clinical act.
    //   READ   -- any authenticated employee. Operational compliance is not resident PHI.
    //   REVIEW -- management only. Sign-off is the privileged act, deliberately separate
    //             from recording, so the person who took the reading is not the person
    //             who attests the log was reviewed.
    const ALF_OPA_TYPES = { food_temp: true, sanitation: true, emergency_drill: true };
    if (resource === 'alf_op_audits' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const r = await fetch(rest('alf_op_audits?license_hash=eq.' + enc(licHash) + '&select=entry_id,record_type,observed_on,passed,data,recorded_by,reviewed_by,reviewed_at,created_at'), { headers });
      if (r.status === 404 || r.status === 400) {
        res.status(200).json({ ok: true, data: [], provisioned: false, summary: opAudit.summarise([]) });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      // The authoritative columns are applied AFTER the jsonb blob, never before. Spreading
      // data last would let a client-supplied `passed` inside the blob override the value the
      // server actually computed -- the write path already refuses to trust it, and this is
      // the matching half of that guarantee on the way back out. Caught by a test that
      // recorded an out-of-tolerance temperature with passed:true and read it back.
      const data = (rows || []).map((x) => Object.assign({}, x.data, {
        id: x.entry_id, record_type: x.record_type, observed_on: x.observed_on, passed: x.passed,
        recorded_by: x.recorded_by || '', reviewed_by: x.reviewed_by || '', reviewed_at: x.reviewed_at || null,
        created_at: x.created_at
      }));
      res.status(200).json({ ok: true, data, provisioned: true, summary: opAudit.summarise(data) });
      return;
    }
    if (resource === 'alf_op_audits' && action === 'write') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!payload || !payload.id || !payload.record_type) {
        res.status(400).json({ error: { message: 'alf_op_audits requires id and record_type' } });
        return;
      }
      if (!ALF_OPA_TYPES[payload.record_type]) {
        res.status(400).json({ error: { message: 'record_type must be one of: ' + Object.keys(ALF_OPA_TYPES).join(', ') } });
        return;
      }
      // A review/sign-off is management-only, and is the ONLY part of this resource that is.
      const isReview = payload.reviewed !== undefined;
      if (isReview && !ALF_MANAGEMENT_ROLES[session.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only management can sign off an operational audit record' } });
        return;
      }
      // Append-only for new observations. A sign-off is the one permitted update, so a
      // reused id is only accepted when it is genuinely a review of an existing record.
      const existingR = await fetch(rest('alf_op_audits?license_hash=eq.' + enc(licHash) + '&entry_id=eq.' + enc(String(payload.id)) + '&select=entry_id,record_type,observed_on,passed,data,recorded_by'), { headers });
      if (existingR.status === 404 || existingR.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'The operational audit log is not set up yet — run sql/sairncare_op_audit_schema.sql in Supabase first.' } });
        return;
      }
      const existingRows = existingR.ok ? await existingR.json() : [];
      const existing = Array.isArray(existingRows) && existingRows[0];
      if (existing && !isReview) {
        res.status(409).json({ error: { code: 'ALREADY_RECORDED', message: 'This observation has already been recorded and cannot be overwritten. Record a new entry instead.' } });
        return;
      }
      if (isReview && !existing) {
        res.status(404).json({ error: { code: 'NO_SUCH_RECORD', message: 'There is no operational audit record with that id to sign off.' } });
        return;
      }

      let body;
      if (isReview) {
        // A sign-off must not be able to quietly rewrite the observation it signs.
        // Only the review stamp changes; the observed values are carried forward
        // from what is already stored, not from the client's payload.
        body = {
          license_hash: licHash, app_id: 'sairncare', entry_id: String(payload.id),
          record_type: existing.record_type, observed_on: existing.observed_on,
          passed: existing.passed, data: existing.data, recorded_by: existing.recorded_by,
          reviewed_by: session.employee_id, reviewed_at: nowISO()
        };
      } else {
        const opData = Object.assign({}, payload);
        delete opData.id; delete opData.record_type; delete opData.reviewed;
        // `passed` lives in its own column and is server-determined for anything with a real
        // measurement. Stripping it from the blob too means there is no second copy that
        // could ever disagree with the column -- defence in depth alongside the read-path fix.
        delete opData.passed;
        // Where the record carries a real measurement, evaluate it here rather than
        // trusting a client-supplied pass/fail -- the threshold is the point of the record.
        let passed = null;
        if (payload.record_type === 'food_temp' && payload.holding_kind && payload.temperature_f !== undefined) {
          const facR = await fetch(rest('alf_facility?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
          const facRows = facR.ok ? await facR.json().catch(() => []) : [];
          const fac = (Array.isArray(facRows) && facRows[0] && facRows[0].data) || {};
          const evalRes = opAudit.evaluateFoodTemp({
            holding_kind: payload.holding_kind, temperature_f: payload.temperature_f,
            thresholds: fac.food_thresholds || {}
          });
          if (!evalRes.ok) { res.status(400).json({ error: evalRes.error }); return; }
          passed = evalRes.passed;
          opData.evaluation = evalRes;
        } else if (payload.passed !== undefined) {
          passed = !!payload.passed;
        }
        body = {
          license_hash: licHash, app_id: 'sairncare', entry_id: String(payload.id),
          record_type: payload.record_type,
          observed_on: payload.observed_on || nowISO().slice(0, 10),
          passed: passed, data: opData, recorded_by: session.employee_id
        };
      }
      const w = await fetch(rest('alf_op_audits?on_conflict=license_hash,entry_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify(body)
      });
      if (w.status === 404 || w.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'The operational audit log is not set up yet — run sql/sairncare_op_audit_schema.sql in Supabase first.' } });
        return;
      }
      const wrows = await w.json();
      if (!w.ok) return upstream(res, wrows);
      res.status(200).json({ ok: true, data: Object.assign({ id: payload.id, record_type: body.record_type, passed: body.passed, recorded_by: body.recorded_by, reviewed_by: body.reviewed_by || '' }, body.data) });
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
    // ── SAIRNDENTAL SESSION GATE (2026-08-27, EMERGENCY) ────────────────────────────────────
    // Until today EVERY dnt_* branch below ran with NO session check at all --
    // a caller holding only the licence key could read dnt_patients and get
    // names and dates of birth back. Proven live before the fix, 8 rows, 200 OK.
    // The app's "auth" was `DEFAULT_PINS={owner:'1234',...}` compared in the
    // browser (sairndental.html:678), so the server never knew who was acting.
    //
    // This gate is the minimum that closes that: a VALID, app-scoped, unexpired
    // session for THIS licence. The third argument is not optional -- without it
    // a valid session for another SAIRN app would pass, because role names like
    // 'owner' exist in several apps' vocabularies (Guardian Check 28).
    //
    // PARTIALLY ROLE-TIERED AS OF 2026-08-27. This gate is still the floor --
    // every dnt_* call needs a valid session -- but it is no longer the whole
    // story. The FINANCIAL tier is layered on top of it in the read branch
    // below. Provider-scoped PATIENT read is still open and is BLOCKED on a
    // missing employee_id <-> provider_id link, not merely deferred; the full
    // reasoning is in api/dnt-auth.js's role-model header and must be read
    // before anyone attempts it.
    //
    // The PUBLIC dental paths are unaffected and were checked before this went
    // in: api/sairndental/public-book.js, public-availability.js and
    // public-complaint-submit.js talk to Supabase directly and never route
    // through this file, so patient self-booking still works with no session.
    const dntGate = (response) => {
      const s = verifySessionToken(tokenFromRequest(req), licHash, 'sairndental');
      if (!s) { response.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return null; }
      return s;
    };

    // ── SAIRNDENTAL MINIMUM-NECESSARY TIERING, FINANCIAL TIER (2026-08-27) ──
    // Closes the FIRST half of the open item recorded in api/dnt-auth.js's role
    // header. That header said tiering was "deferred, not decided" because all
    // three dental roles have a real reason to touch PATIENT records. That is
    // true of patients. It is NOT true of practice financials, and this is the
    // half that could be settled without guessing.
    //
    // Michael's decision, 2026-08-27: financial data gets its OWN tier, separate
    // from clinical access. Read-scope only this pass -- write is deliberately
    // left exactly as it was (see the asymmetry note below).
    //
    // WHY frontdesk IS IN THE FINANCIAL TIER AND provider IS NOT: the front desk
    // takes payment at checkout, posts charges, and verifies benefits -- that is
    // the job. A treating clinician has no minimum-necessary reason to read what
    // the practice collected, what is in A/R, or which claims a payer denied.
    // Same reasoning that keeps sen_claims (:2241) and alf_billing (:2454)
    // management-only in their apps, adjusted for the fact that this app has no
    // billing role: the nearest real equivalent is frontdesk, so the tier is
    // {owner, frontdesk} rather than {owner} alone. Making it owner-only would
    // have locked the front desk out of taking a payment, which is not a
    // privacy improvement, it is a broken practice.
    //
    // dnt_coverage_rules is in this tier deliberately. It looks clinical because
    // it names procedures, but its content is what a PLAN PAYS -- benefit and
    // reimbursement rules, read by whoever is verifying coverage. That is front
    // desk work, not chair-side work.
    //
    // ⚠ READ-SIDE ONLY, AND THAT ASYMMETRY IS DELIBERATE, NOT AN OVERSIGHT.
    // Write for these resources is unchanged and still open to all three roles.
    // So a provider can still WRITE dnt_revenue even though they can no longer
    // READ it. That is a narrowing of DISCLOSURE, which is what HIPAA
    // minimum-necessary is actually about, and it is a real improvement over
    // "any authenticated employee sees everything." It is NOT a complete
    // authorisation model, and nothing here should be described as one.
    // Narrowing write is a separate, larger pass: this client reads a record and
    // writes the whole object back, so write rules and any future FIELD-level
    // redaction have to be designed together or the redacted half gets wiped on
    // the next save -- exactly the hazard alf_facility's own comment documents
    // at :4645, where redaction is only safe BECAUSE write is management-only.
    // Mirrors api/dnt-auth.js's MANAGEMENT_ROLES. Declared here rather than
    // imported because sd-data.js does not require dnt-auth.js (that file is a
    // request handler, not a lib) -- if the two ever diverge, dnt-auth.js is the
    // source of truth and this is the copy to correct.
    const DNT_MANAGEMENT_ROLES = { owner: true };
    const DNT_FINANCIAL_ROLES = { owner: true, frontdesk: true };
    const DNT_FINANCIAL_RESOURCES = {
      dnt_charges: true, dnt_payments: true, dnt_denial: true,
      dnt_ar: true, dnt_revenue: true, dnt_coverage_rules: true,
      // A good faith estimate is a priced document about one named patient --
      // expected charges per service code, alongside their name and date of
      // birth. It belongs on the financial side for the same reason dnt_charges
      // does, and the roles that gate it (owner, front desk) are the ones who
      // actually issue estimates under 45 CFR 149.610.
      dnt_gfe: true
    };

    // ── SAIRNDENTAL: PROVIDER-SCOPED PATIENT READ (2026-08-27, scope extended) ──
    // The second half of minimum-necessary tiering. Michael's decisions:
    //   - a provider reads ONLY patients they are linked to, never practice-wide;
    //   - an UNLINKED provider sees NOTHING (see-nothing, not see-everything) --
    //     an unlinked provider defaulting to full read is the same shape of gap
    //     this whole pass exists to close;
    //   - but the block must be a "not set up yet" state with an obvious fix
    //     path, never a dead end.
    //
    // THE LINK THAT MAKES THIS POSSIBLE, and why it had to be built first.
    // dnt_appointments.provider_id references a dnt_providers row id ("PV-…",
    // minted client-side). An auth employee_id is a free-text string chosen at
    // bootstrap. NOTHING joined them, so the obvious filter
    // (provider_id === session.employee_id) would have matched zero rows and
    // handed every provider an empty patient list with a 200 OK -- a permission
    // check manufacturing a false empty state. The link is now an explicit
    // `linked_employee_id` field on the dnt_providers DATA BLOB: no migration,
    // because dnt_providers is (license_hash, provider_id, data jsonb).
    //
    // WHY THE UNLINKED CASE IS A 403 AND NOT AN EMPTY 200: same reasoning as the
    // financial tier above. "No patients" and "you are not linked yet" are
    // completely different facts, and only one of them is worth showing a
    // clinician. A distinct code lets the client say which, and point at the fix.
    const DNT_PATIENT_BROAD_READ_ROLES = { owner: true, frontdesk: true };

    // Resolves the caller to their dnt_providers row. Returns:
    //   { provisioned:false }              -> registry table not set up yet
    //   { provisioned:true, providerId:null } -> authenticated, but no link set
    //   { provisioned:true, providerId:'PV-…' }
    const dntLinkedProvider = async (session) => {
      const pr = await fetch(rest('dnt_providers?license_hash=eq.' + enc(licHash) + '&select=provider_id,data'), { headers });
      if (pr.status === 404 || pr.status === 400) return { provisioned: false, providerId: null };
      const prows = await pr.json();
      if (!pr.ok || !Array.isArray(prows)) return { provisioned: false, providerId: null };
      const match = prows.filter((x) => x && x.data && x.data.linked_employee_id === session.employee_id)[0];
      return { provisioned: true, providerId: match ? (match.data.id || match.provider_id) : null };
    };

    // The patient set a linked provider may see: every patient they have an
    // appointment with. Uses the PROMOTED provider_id column, so the filter runs
    // in the database rather than over a full table read. patient_id lives in the
    // appointment's data blob (it was never promoted), so it is read out here.
    const dntPatientIdsForProvider = async (providerId) => {
      const ar = await fetch(rest('dnt_appointments?license_hash=eq.' + enc(licHash) +
        '&provider_id=eq.' + enc(providerId) + '&select=data'), { headers });
      if (!ar.ok) return null;
      const arows = await ar.json();
      if (!Array.isArray(arows)) return null;
      const ids = {};
      arows.forEach((x) => { if (x && x.data && x.data.patient_id) ids[String(x.data.patient_id)] = true; });
      return ids;
    };

    const DNT_RESOURCES = {
      dnt_patients: 'patient_id', dnt_providers: 'provider_id', dnt_operatories: 'operatory_id',
      dnt_provider_hours: 'provider_hour_id', dnt_procedure_types: 'procedure_type_id',
      dnt_coverage_rules: 'coverage_rule_id', dnt_charges: 'charge_id',
      dnt_payments: 'payment_id', dnt_denial: 'denial_id', dnt_ar: 'ar_id', dnt_revenue: 'revenue_id',
      dnt_referrals: 'referral_id', dnt_gfe: 'gfe_id'
    };
    // Patient-scoped resources: the record itself is about a specific patient.
    // dnt_referrals is here deliberately -- it carries patient_id and a clinical
    // reason, so leaving it practice-wide would have leaked exactly what scoping
    // dnt_patients was meant to stop.
    // dnt_gfe joins them for the same reason: the record names one patient and
    // carries their date of birth, so leaving it practice-wide would undo the
    // scoping dnt_patients exists to enforce.
    const DNT_PATIENT_SCOPED_RESOURCES = { dnt_patients: 'id', dnt_referrals: 'patient_id', dnt_gfe: 'patient_id' };
    if (DNT_RESOURCES[resource] && action === 'read') {
      const dntSess = dntGate(res);
      if (!dntSess) return;
      // 403, not an empty 200. An empty list would be indistinguishable from a
      // practice that has taken no payments yet, and the client would render a
      // real zero -- a fabricated figure produced by a permission check, which
      // is the exact silent-failure shape Guardian Check 0b exists to catch.
      if (DNT_FINANCIAL_RESOURCES[resource] && !DNT_FINANCIAL_ROLES[dntSess.role]) {
        res.status(403).json({ error: { code: 'ROLE_NOT_PERMITTED', message: 'Financial records are limited to the practice owner and front desk' } });
        return;
      }
      // Provider-scoped patient read. Owner and front desk keep practice-wide
      // visibility -- the front desk has to be able to find any patient to book
      // or check one in, which is the job.
      let dntScopeIds = null;
      if (DNT_PATIENT_SCOPED_RESOURCES[resource] && !DNT_PATIENT_BROAD_READ_ROLES[dntSess.role]) {
        const link = await dntLinkedProvider(dntSess);
        if (!link.provisioned) {
          res.status(200).json({ ok: true, data: [], provisioned: false });
          return;
        }
        if (!link.providerId) {
          res.status(403).json({
            error: {
              code: 'PROVIDER_NOT_LINKED',
              message: 'Your sign-in is not linked to a provider yet, so no patient records are shown. Ask the practice owner to open the Providers panel and link your login to your provider record.'
            }
          });
          return;
        }
        dntScopeIds = await dntPatientIdsForProvider(link.providerId);
        if (!dntScopeIds) { res.status(502).json({ error: { code: 'SCOPE_LOOKUP_FAILED', message: 'Could not determine your patient list. Try again.' } }); return; }
      }
      const r = await fetch(rest(resource + '?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      let dntOut = (rows || []).map((x) => x.data);
      if (dntScopeIds) {
        const key = DNT_PATIENT_SCOPED_RESOURCES[resource];
        dntOut = dntOut.filter((d) => d && d[key] != null && dntScopeIds[String(d[key])] === true);
      }
      res.status(200).json({ ok: true, data: dntOut, provisioned: true });
      return;
    }
    if (DNT_RESOURCES[resource] && action === 'write') {
      const dntWSess = dntGate(res);
      if (!dntWSess) return;
      // PROVIDER REGISTRY IS OWNER-ONLY TO WRITE (2026-08-27). Found while
      // building the link: rProviders/addProvider had no role check at all, so
      // any authenticated role could add or alter the practice's provider roster
      // -- and once linked_employee_id exists on that record, that roster IS the
      // access-control table for patient scoping. Anyone who can edit it can
      // grant themselves a patient list. READ stays open to every authenticated
      // role on purpose: provider NAMES are rendered all over this app
      // (appointments, hours, credentials), and hiding them would break it.
      if (resource === 'dnt_providers' && !DNT_MANAGEMENT_ROLES[dntWSess.role]) {
        res.status(403).json({ error: { code: 'ROLE_NOT_PERMITTED', message: 'Only the practice owner can change the provider roster' } });
        return;
      }
      // One login links to at most ONE provider. Without this, two provider rows
      // could carry the same linked_employee_id and dntLinkedProvider() would
      // silently pick whichever sorted first -- a scoping decision made by row
      // order. Refused explicitly instead.
      if (resource === 'dnt_providers' && payload && payload.linked_employee_id) {
        const dupR = await fetch(rest('dnt_providers?license_hash=eq.' + enc(licHash) + '&select=provider_id,data'), { headers });
        if (dupR.ok) {
          const dupRows = await dupR.json();
          const clash = (Array.isArray(dupRows) ? dupRows : []).filter((x) =>
            x && x.data && x.data.linked_employee_id === payload.linked_employee_id && String(x.provider_id) !== String(payload.id))[0];
          if (clash) {
            res.status(409).json({ error: { code: 'EMPLOYEE_ALREADY_LINKED', message: 'That login is already linked to another provider. Unlink it there first.' } });
            return;
          }
        }
      }
      const idCol = DNT_RESOURCES[resource];
      if (!payload || payload.id === undefined || payload.id === null || payload.id === '') {
        res.status(400).json({ error: { message: resource + ' payload.id is required' } });
        return;
      }
      // Multi-location write-side capture (2026-08-24). Stamped here rather
      // than trusted from the client so a row can never be written without
      // an attributable location -- that is the one part of the location
      // model that cannot be added retroactively. Defaults to the implicit
      // single-practice location, so this is invisible to existing clients.
      const locStamped = dntLocation.stampLocation(payload);
      const r = await fetch(rest(resource + '?on_conflict=license_hash,' + idCol), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairndental', [idCol]: String(payload.id), data: locStamped, updated_at: nowISO() })
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
      if (!dntGate(res)) return;
      const r = await fetch(rest('dnt_settings?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'dnt_settings' && action === 'write') {
      if (!dntGate(res)) return;
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'dnt_settings payload.id is required' } }); return; }
      // The minimal locations registry lives on this row as
      // data.locations[] -- see api/_lib/dnt-location.js for why it is here
      // and not in a new table. Validated rather than stored blindly: a
      // duplicate location id would silently split one office's history in
      // two, and that is not recoverable once rows are attributed to it.
      // settings itself is NOT location-stamped -- it is practice-level
      // config and, today, one row per license.
      const locCheck = dntLocation.validateLocations(payload.locations);
      if (!locCheck.ok) { res.status(400).json({ error: { code: locCheck.code, message: locCheck.message } }); return; }
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
      if (!dntGate(res)) return;
      const r = await fetch(rest('dnt_complaints?license_hash=eq.' + enc(licHash) + '&select=data,updated_at&order=updated_at.desc'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => Object.assign({}, x.data, { updated_at: x.updated_at })), provisioned: true });
      return;
    }
    if (resource === 'dnt_complaints' && action === 'write') {
      if (!dntGate(res)) return;
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
      const dntASess = dntGate(res);
      if (!dntASess) return;
      // Provider-scoped, same rule as dnt_patients: a provider sees only their
      // own appointments. This one filters in the DATABASE on the promoted
      // provider_id column rather than reading everything and discarding --
      // appointment rows carry patient photos and are up to ~1.26 MB each
      // (dntap_data_size), so a practice-wide read to throw most of it away
      // would be both a privacy and a payload problem.
      let dntApptFilter = '';
      if (!DNT_PATIENT_BROAD_READ_ROLES[dntASess.role]) {
        const link = await dntLinkedProvider(dntASess);
        if (!link.provisioned) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
        if (!link.providerId) {
          res.status(403).json({
            error: {
              code: 'PROVIDER_NOT_LINKED',
              message: 'Your sign-in is not linked to a provider yet, so no appointments are shown. Ask the practice owner to open the Providers panel and link your login to your provider record.'
            }
          });
          return;
        }
        dntApptFilter = '&provider_id=eq.' + enc(link.providerId);
      }
      const r = await fetch(rest('dnt_appointments?license_hash=eq.' + enc(licHash) + dntApptFilter + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'dnt_appointments' && action === 'write') {
      if (!dntGate(res)) return;
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
      // Same write-side location capture as the generic block above. The
      // EXCLUDE constraints are deliberately NOT changed: operatory overlap
      // already implies a location (an operatory is a room at one office),
      // and provider overlap must stay location-blind because a dentist
      // cannot be in two offices at once.
      const apptStamped = dntLocation.stampLocation(payload);
      const r = await fetch(rest('dnt_appointments?on_conflict=license_hash,appointment_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairndental', appointment_id: String(payload.id), data: apptStamped,
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

    // ── SAIRNDENTAL: dnt_cred_rules + dnt_credentials (2026-08-24) ─────────
    // Licensing/credentialing. Evaluation logic is PURE and lives in
    // api/_lib/dental-credentials.js; these branches are storage + shaping
    // only, the same split as SAIRNcare's compliance-rules and payer-routing.
    //
    // ── RE-GATED 2026-08-29. The comment that used to sit here was correct
    // when it was written and became false without anyone noticing, which is
    // the whole story of this defect. It read: "NO PER-EMPLOYEE ROLE GATE, and
    // that is deliberate rather than an oversight: SAIRNdental has no employee
    // auth (there is no api/dnt-auth.js and no verifySessionToken caller
    // anywhere in this app's branches) ... A role check written here would be
    // decoration -- there is no session to check it against ... whoever adds
    // employee auth to SAIRNdental knows to re-gate this."
    //
    // Employee auth WAS added. api/dnt-auth.js exists, dntGate() above calls
    // verifySessionToken, and every branch here has had a real session to check
    // against ever since -- but nobody came back to do the re-gating the comment
    // asked for. So `dnt_cred_rules` write kept the license-key-era posture: any
    // signed-in employee, provider or front desk included, could rewrite a STATE
    // CREDENTIALING REQUIREMENT. That is the same class of assertion the write
    // path already refuses to store without a citation, so leaving who may make
    // it unrestricted was the inconsistency.
    //
    // Write is now owner-only, matching rf_cert_rules / alf_compliance_rules,
    // the two other reference tables of exactly this shape. READ IS UNCHANGED
    // and stays session-only on purpose: a provider needs to see what their
    // state requires of them, and a rule is not sensitive -- it is published law.
    // Same read-wide/write-narrow split those two apps already use.
    if (resource === 'dnt_cred_rules' && action === 'read') {
      if (!dntGate(res)) return;
      const r = await fetch(rest('dnt_cred_rules?license_hash=eq.' + enc(licHash) + '&select=rule_id,state,requirement_type,role,effective_from,effective_to,status,data,verified_by'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false, coverage: { covered_states: [], uncovered_states: [], detail: [] } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const data = (rows || []).map((x) => ({
        rule_id: x.rule_id, state: x.state, requirement_type: x.requirement_type,
        role: x.role || null, effective_from: x.effective_from, effective_to: x.effective_to,
        status: x.status || 'active', verified_by: x.verified_by || '', data: x.data || {}
      }));
      const claimed = Array.isArray(payload && payload.claimed_states) && payload.claimed_states.length
        ? payload.claimed_states.map((s) => String(s).toUpperCase())
        : Array.from(new Set(data.map((x) => x.state)));
      res.status(200).json({ ok: true, data, provisioned: true, coverage: dentalCreds.credentialCoverage(data, claimed) });
      return;
    }
    if (resource === 'dnt_cred_rules' && action === 'write') {
      const dntRuleSess = dntGate(res);
      if (!dntRuleSess) return;
      if (!DNT_MANAGEMENT_ROLES[dntRuleSess.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only the practice owner can change credentialing rules' } });
        return;
      }
      if (!payload || !payload.rule_id || !payload.state || !payload.requirement_type || !payload.effective_from) {
        res.status(400).json({ error: { message: 'dnt_cred_rules requires rule_id, state, requirement_type, and effective_from' } });
        return;
      }
      // A rule without a real citation is exactly the fabricated-number class
      // this whole seed format exists to prevent, so it is refused at the API,
      // not merely discouraged in the seed file's comments.
      const auth = payload.data && payload.data.authority;
      if (!auth || !auth.citation || !auth.quote || !auth.read_on) {
        res.status(400).json({ error: { code: 'NO_AUTHORITY', message: 'dnt_cred_rules requires data.authority with citation, quote, and read_on — a requirement with no source cannot be stored' } });
        return;
      }
      const r = await fetch(rest('dnt_cred_rules?on_conflict=license_hash,rule_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairndental', rule_id: String(payload.rule_id),
          state: String(payload.state).toUpperCase(), requirement_type: payload.requirement_type,
          role: payload.role || null, effective_from: payload.effective_from,
          effective_to: payload.effective_to || null, status: payload.status || 'active',
          // Was the literal string 'license' -- the honest stamp back when the
          // only thing this endpoint could prove was that SOMEONE held the
          // practice key. Now that the gate above proves which owner made the
          // assertion, record them, same as rf_cert_rules does. Server-derived,
          // never client-supplied. `verified_by` is in the fingerprint's
          // INERT_COLUMNS, so re-loading a seed under this change cannot make
          // tools/sairn_load_state_check.py report false drift.
          data: payload.data || {}, verified_by: dntRuleSess.employee_id, updated_at: nowISO()
        })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNdental credentialing tables are not set up yet — run sql/sairndental_credentials_schema.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'dnt_credentials' && action === 'read') {
      if (!dntGate(res)) return;
      const r = await fetch(rest('dnt_credentials?license_hash=eq.' + enc(licHash) + '&select=entry_id,provider_id,record_type,data,recorded_at&order=recorded_at.asc'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({
        ok: true, provisioned: true,
        data: (rows || []).map((x) => Object.assign({}, x.data || {}, {
          entry_id: x.entry_id, provider_id: x.provider_id,
          record_type: x.record_type, recorded_at: x.recorded_at
        }))
      });
      return;
    }
    if (resource === 'dnt_credentials' && action === 'write') {
      if (!dntGate(res)) return;
      if (!payload || !payload.id || !payload.provider_id || !payload.record_type) {
        res.status(400).json({ error: { message: 'dnt_credentials requires payload.id, payload.provider_id, and payload.record_type' } });
        return;
      }
      if (!dentalCreds.RECORD_TYPES[payload.record_type]) {
        res.status(400).json({ error: { message: "dnt_credentials record_type must be one of: state_license, dea_registration, ce_cycle, certification" } });
        return;
      }
      // APPEND-ONLY: a plain insert, deliberately NOT an upsert. A correction
      // is a new row that supersedes (the reader takes the latest per
      // provider/type/subject), never an overwrite of the original assertion
      // that a named clinician held a real licence on a real date. The table
      // grant withholds update/delete as the backstop, so a future upsert here
      // would fail loudly rather than silently rewriting history.
      const r = await fetch(rest('dnt_credentials'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: 'sairndental', entry_id: String(payload.id),
          provider_id: String(payload.provider_id), record_type: payload.record_type,
          data: payload
        })
      });
      if (r.status === 404) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNdental credentialing tables are not set up yet — run sql/sairndental_credentials_schema.sql in Supabase first.' } }); return; }
      if (r.status === 400 || r.status === 409) {
        const bodyText = await r.text();
        let bodyJson = null; try { bodyJson = JSON.parse(bodyText); } catch (e) {}
        const msg = (bodyJson && (bodyJson.message || bodyJson.details || bodyJson.hint)) || bodyText || '';
        if (/relation .* does not exist|does not exist/i.test(msg)) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNdental credentialing tables are not set up yet — run sql/sairndental_credentials_schema.sql in Supabase first.' } }); return; }
        if (/duplicate key|unique constraint/i.test(msg)) { res.status(409).json({ error: { code: 'DUPLICATE_ENTRY', message: 'A credential record with this id already exists. Records are append-only — write a new record to supersede, do not reuse an id.' } }); return; }
        console.error('dnt_credentials write error (status ' + r.status + '):', msg);
        res.status(502).json({ error: { message: 'Data store error — try again', detail: msg } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? Object.assign({}, rows[0].data || {}, { recorded_at: rows[0].recorded_at }) : payload });
      return;
    }
    // Compute-only. Reads both tables, writes nothing — see the verb note in
    // api/_resources/sairndental.js.
    if (resource === 'dnt_credentials' && action === 'evaluate') {
      if (!dntGate(res)) return;
      const today = (payload && payload.today) || nowISO().slice(0, 10);
      const rr = await fetch(rest('dnt_credentials?license_hash=eq.' + enc(licHash) + '&select=entry_id,provider_id,record_type,data,recorded_at'), { headers });
      if (rr.status === 404 || rr.status === 400) { res.status(200).json({ ok: true, provisioned: false, board: null }); return; }
      const credRows = await rr.json();
      if (!rr.ok) return upstream(res, credRows);
      const ruleRes = await fetch(rest('dnt_cred_rules?license_hash=eq.' + enc(licHash) + '&select=rule_id,state,requirement_type,role,effective_from,effective_to,status,data'), { headers });
      const ruleRows = (ruleRes.status === 404 || ruleRes.status === 400) ? [] : await ruleRes.json();
      const records = (credRows || []).map((x) => Object.assign({}, x.data || {}, {
        entry_id: x.entry_id, provider_id: x.provider_id,
        record_type: x.record_type, recorded_at: x.recorded_at
      }));
      const rules = (Array.isArray(ruleRows) ? ruleRows : []).map((x) => ({
        rule_id: x.rule_id, state: x.state, requirement_type: x.requirement_type,
        role: x.role || null, effective_from: x.effective_from, effective_to: x.effective_to,
        status: x.status || 'active', data: x.data || {}
      }));
      const board = dentalCreds.evaluateBoard(records, rules, today);
      if (!board.ok) { res.status(400).json({ error: board.error }); return; }
      res.status(200).json({
        ok: true, provisioned: true, board: board,
        coverage: dentalCreds.credentialCoverage(rules, Array.from(new Set(records.map((r2) => String(r2.state || '').toUpperCase()).filter(Boolean))))
      });
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
        // sc_settings ROLE GATE (2026-08-23, policy decided by Michael:
        // Compliance Admin only). These are PRACTICE-LEVEL settings -- the
        // practice name printed on output, the payer payment-cycle reference,
        // and the records-retention policy -- not one coder's preferences, so
        // a single coder should not be able to change what the whole practice
        // sees. Read stays open to every authenticated role (coder/biller/
        // auditor can all see the policy that governs them); only the write
        // is narrowed.
        //
        // Enforced HERE and not only in the UI, for the same reason as the
        // sc_auth_requests sign-off gate below: a hidden button is a
        // convenience, never a boundary. The client's own role string is
        // never trusted -- the role is read from the verified session token,
        // which carries an app claim so a valid session for a DIFFERENT SAIRN
        // app cannot satisfy it (Check 28).
        //
        // This narrows behaviour that was previously open to any authenticated
        // session, including retention_years, which has been writable by any
        // role since 2026-08-20. That is the intended change, not a side
        // effect. The retention FLOOR guard below is unchanged and still
        // applies to admins too -- a role check and a value check are
        // different controls and neither replaces the other.
        if (resource === 'sc_settings') {
          const scSetCaller = verifySessionToken(tokenFromRequest(req), licHash, 'sairncode');
          if (!scSetCaller) {
            res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } });
            return;
          }
          if (scSetCaller.role !== 'admin') {
            res.status(403).json({
              error: {
                code: 'FORBIDDEN',
                message: 'Only a Compliance Admin can change practice-level settings. Your changes were not saved.'
              }
            });
            return;
          }
        }
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
        if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: scNotProvisionedMessage(resource) } }); return; }
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
        if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: scNotProvisionedMessage(resource) } }); return; }
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

// NOT_PROVISIONED message for the generic SC_RESOURCES branch (2026-08-25).
// This branch serves ~29 sc_* resources spread across a dozen different
// migration files, but both call sites used to hardcode
// "run sql/sairncode_data_schema.sql" -- wrong for every resource that has
// its own file. Following that message runs an already-applied migration
// whose `create table if not exists` is a silent no-op, so the operator
// concludes the table is fine and looks elsewhere. That is exactly what
// happened to sc_specialty_checks / sc_anesthesia_base_units / sc_pctc,
// which sat unprovisioned from 2026-08-20 until the 2026-08-25 sweep.
//
// Deliberately NOT a resource->filename map: the map would need a new row
// every time a resource is added and would rot the same way the single
// hardcoded name did. Naming the resource and telling the operator to grep
// for it cannot go stale.
function scNotProvisionedMessage(resource) {
  return 'SAIRNcode table "' + resource + '" is not set up yet -- run the migration that creates it ' +
    '(grep sql/ for "' + resource + '"; it is one of the sql/sairncode_*_schema.sql files) in Supabase first.';
}

// Flatten a stored data jsonb blob back into the flat object the client expects,
// with any promoted columns (shop_id, created_at) merged on top.
function flat(data, extra) {
  return Object.assign({}, data || {}, extra || {});
}

function upstream(res, detail) {
  console.error('sd-data upstream error:', detail);
  res.status(502).json({ error: { message: 'Data store error — try again' } });
}
