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
  employee_profile: true,
  // SAIRNgrounds schedule + progress-photo QC (2026-08-06, related-bug + item-3 cross-device fix)
  // -- see the block comments below for why these are prefixed rather than reusing 'schedule'/
  // 'progress_photos' bare.
  grd_schedule: true, grd_progress_photos: true,
  // SAIRNgrounds invoices + DreamClose (2026-08-06, sweep fix) -- 'invoices' bare was already
  // claimed by SAIRNscape below (customer_id-scoped); 'dreamclose' never had a route at all.
  grd_invoices: true, grd_dreamclose: true,
  // SAIRNscape progress-photo QC (2026-08-06) -- same fix, same prefixing reason.
  scp_progress_photos: true,
  // Full resource-name sweep, phase 2 (2026-08-06) -- see
  // sql/sairngrounds_data_schema_phase2.sql and
  // sql/sairnscape_data_schema_phase2.sql for the complete rationale.
  grd_invasive_sightings: true, grd_ecosystem_reports: true, grd_designs: true, grd_irr_controllers: true, grd_irr_zones: true, grd_irr_schedules: true, grd_water_features: true, grd_training_courses: true, grd_training_completions: true, grd_boq_rates: true, grd_vendors: true, msb_products: true, msb_sales: true, msb_licenses: true, msb_inventory_log: true, msb_bottle_scans: true, msb_food_scans: true, msb_food_waste: true, msb_food_cost_log: true, msb_sale_hours: true,
  scp_designs: true, scp_irr_controllers: true, scp_irr_zones: true, scp_irr_schedules: true, scp_water_features: true, scp_vendors: true,
  // SAIRNdesign (2026-08-07) -- see sql/sairndesign_data_schema.sql. sdn_ prefix on every one of
  // these, not just 'sdn_schedule'/'sdn_invoices' which would otherwise collide with the bare
  // 'schedule'/'invoices' names already claimed above -- consistency across all 18, not a mixed
  // scheme. Closes the whole-app sync gap described in that SQL file's header.
  sdn_clients: true, sdn_projects: true, sdn_specitems: true, sdn_proposals: true, sdn_vendors: true,
  sdn_samplerequests: true, sdn_team: true, sdn_moodboards: true, sdn_colorcodes: true, sdn_pos: true,
  sdn_invoices: true, sdn_timeentries: true, sdn_schedule: true, sdn_samples: true, sdn_contracts: true,
  sdn_referrals: true, sdn_discounts: true, sdn_roomdims: true,
  // SAIRNlegacy (2026-08-07) -- see sql/sairnlegacy_data_schema.sql. All 36 prefixed leg_.
  leg_aftercare: true, leg_bookings: true, leg_cases: true, leg_catererorders: true, leg_caterers: true,
  leg_certs: true, leg_clergy: true, leg_clergybookings: true, leg_cremations: true, leg_custodylog: true,
  leg_deathrecords: true, leg_dispatches: true, leg_documents: true, leg_facilities: true, leg_floristorders: true,
  leg_florists: true, leg_gplservices: true, leg_guestbook: true, leg_insurance: true, leg_invoices: true,
  leg_keepsakeorders: true, leg_keepsakes: true, leg_liverybookings: true, leg_liveryvendors: true,
  leg_maintenance: true, leg_memorials: true, leg_merch_catalog: true, leg_merch_units: true, leg_monuments: true,
  leg_obituaries: true, leg_petcases: true, leg_plots: true, leg_preneed: true, leg_processions: true,
  leg_tributes: true, leg_vehicles: true,
  // SAIRNdental (2026-08-10) -- see sql/sairndental_data_schema.sql. All 12 prefixed dnt_.
  dnt_patients: true, dnt_providers: true, dnt_operatories: true, dnt_provider_hours: true,
  dnt_procedure_types: true, dnt_coverage_rules: true, dnt_appointments: true, dnt_charges: true,
  dnt_payments: true, dnt_denial: true, dnt_ar: true, dnt_revenue: true,
  // SAIRNdental availability + booking (2026-08-10) -- see
  // sql/sairndental_availability_booking_schema.sql. dnt_appointments was
  // already added above but gets its OWN dedicated read/write handler
  // below (not the generic DNT_RESOURCES block) because it now has real
  // promoted columns the EXCLUDE constraints check against -- still
  // listed here since this map only gates "is this a known resource
  // string," not which code path handles it.
  dnt_settings: true, dnt_referrals: true, dnt_complaints: true
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
  if (action !== 'read' && action !== 'write') {
    res.status(400).json({ error: { message: "action must be 'read' or 'write'" } });
    return;
  }
  if (!RESOURCES[resource]) {
    res.status(400).json({ error: { message: 'resource must be one of: profile, memory, employees, slabs, render_usage, shared_knowledge, properties, jobs, quotes, golf_zones, customers, scp_jobs, scp_quotes, schedule, invoices, grd_schedule, grd_progress_photos, scp_progress_photos, grd_invoices, grd_dreamclose, grd_invasive_sightings, grd_ecosystem_reports, grd_designs, grd_irr_controllers, grd_irr_zones, grd_irr_schedules, grd_water_features, grd_training_courses, grd_training_completions, grd_boq_rates, grd_vendors, msb_products, msb_sales, msb_licenses, msb_inventory_log, msb_bottle_scans, msb_food_scans, msb_food_waste, msb_food_cost_log, msb_sale_hours, scp_designs, scp_irr_controllers, scp_irr_zones, scp_irr_schedules, scp_water_features, scp_vendors, sdn_clients, sdn_projects, sdn_specitems, sdn_proposals, sdn_vendors, sdn_samplerequests, sdn_team, sdn_moodboards, sdn_colorcodes, sdn_pos, sdn_invoices, sdn_timeentries, sdn_schedule, sdn_samples, sdn_contracts, sdn_referrals, sdn_discounts, sdn_roomdims, leg_aftercare, leg_bookings, leg_cases, leg_catererorders, leg_caterers, leg_certs, leg_clergy, leg_clergybookings, leg_cremations, leg_custodylog, leg_deathrecords, leg_dispatches, leg_documents, leg_facilities, leg_floristorders, leg_florists, leg_gplservices, leg_guestbook, leg_insurance, leg_invoices, leg_keepsakeorders, leg_keepsakes, leg_liverybookings, leg_liveryvendors, leg_maintenance, leg_memorials, leg_merch_catalog, leg_merch_units, leg_monuments, leg_obituaries, leg_petcases, leg_plots, leg_preneed, leg_processions, leg_tributes, leg_vehicles, dnt_patients, dnt_providers, dnt_operatories, dnt_provider_hours, dnt_procedure_types, dnt_coverage_rules, dnt_appointments, dnt_charges, dnt_payments, dnt_denial, dnt_ar, dnt_revenue, dnt_settings, dnt_referrals, dnt_complaints' } });
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
