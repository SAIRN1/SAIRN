// api/sd-data-cross-tenant-dispatchers.test.js
//
// REQUIREMENT: on every generic dispatcher in api/sd-data.js, a valid, fully
//   authenticated session for tenant A cannot read, overwrite or enumerate
//   tenant B's rows.
//
// CROSS-TENANT-ISOLATION: dnt_ar, dnt_charges, dnt_coverage_rules, dnt_denial,
//   dnt_gfe, dnt_patients, dnt_payments, dnt_revenue, dnt_txplans,
//   sc_ar, sc_claims, sc_compliance, sc_credential_scope, sc_denial,
//   sc_denial_events, sc_revenue,
//   sd_aiquotes, sd_fin_jobs, sd_invoices, sd_negotiated_prices,
//   sd_order_history, sd_pricing_rules,
//   sv_audit_log, sv_billing, sv_compliance, sv_controlled, sv_patients,
//   sb_incidents, sb_payruns, sb_po, sb_recv, sb_ts,
//   bld_costs, bld_incidents, bld_price_points, bld_sub_bids,
//   leg_certs, leg_invoices, leg_preneed,
//   sf_accounts, sf_ledger, sf_vendor_prices,
//   sdn_discounts, sdn_invoices, sdn_contracts,
//   sd_hr_certs, sd_hr_employees,
//   bld_jobs, bld_checks, bld_pos, bld_change_orders, bld_lien_waivers,
//   bld_subs, bld_timesheet, bld_photo_analyses,
//   dnt_referrals, dnt_procedure_types, dnt_recall_outreach,
//   law_timeentries, law_clecredits, law_optx, law_pimedical,
//   law_mattertasks, law_matterdocs, law_mattermilestones,
//   sc_auth_requests, sc_coded_items, sc_hcc
//
// THE LAST TWENTY-TWO WERE ADDED 2026-09-23. Every one was Tier A and sat
// in cross_tenant_isolation_scope's NONE bucket -- no cross-tenant arm at
// all -- and LAW_RESOURCES had no unit in this file whatsoever, which is
// what an absent DISPATCHER looks like from the coverage side: not one
// resource missed, seven at once.
//
// AND THE PROSE HAS TO GO HERE RATHER THAN INSIDE THE LIST.
// declared_coverage() reads the CONTIGUOUS run of comment lines after the
// header above, so a paragraph inserted mid-list truncates the declaration
// silently -- the first attempt parsed 47 names against 68 driven, and
// every name after the paragraph credited nothing. The tool caught it by
// still reporting the new rows WEAK with 'does not DECLARE bld_jobs',
// which reads like a missing name and was a missing PARSE.
//
// sd_quote_requests is deliberately ABSENT from that list even though the plan
// groups it with SD_LOCAL_RESOURCES: it has its OWN named branch with its own
// soft-delete path and is not a member of that map, so no arm here drives it.
// It was declared here first, and the cross-check -- every declared resource
// must appear in UNITS -- caught it. That is the declaration mechanism's whole
// job: a claim somebody signs is only worth more than a guess if something
// checks the signature.
//
// Run:  node api/sd-data-cross-tenant-dispatchers.test.js
//
// ── WHAT THIS IS ──────────────────────────────────────────────────────────
// Phases 1 and 2 of docs/2026-09-21-cross-tenant-isolation-build-plan.md: the
// ten remaining generic-dispatcher units, covering the Tier A resources they
// serve. api/sd-data-cross-tenant-isolation.test.js is the eleventh (LAW) and
// is the reference this is transplanted from; read it first.
//
// ── ONE FILE, NOT TEN, AND THAT IS A DELIBERATE DEPARTURE FROM THE PLAN ───
// The plan says "one unit per claim, one test file each". That was written
// before the dispatchers were driven, and driving them showed the units differ
// only in three values: the map's owning app, the session role, and the id
// column. Ten near-identical files would be ten places for the mock to drift,
// and the mock IS the test -- the property every one of them rests on is that
// the fetch stand-in honours the eq. clauses in the URL. One harness, one
// mock, ten configurations keeps that property in a single place where a
// sabotage arm can hit it once for all of them. Said out loud rather than
// quietly done, because it contradicts a written plan.
//
// ── EVERY MEMBER IS DRIVEN INDIVIDUALLY ──────────────────────────────────
// Not one representative per map. A test that drives one member proves the
// dispatcher and proves nothing about whether the other members are still in
// its map -- which is the exact failure mode of "one parameterised test covers
// the map".
//
// ── THE THREE SHAPES ─────────────────────────────────────────────────────
//   L  list read   -- the refusal is an ABSENCE: 200 carrying only A's rows.
//                     Assert CONTENT, never length: a handler returning [] for
//                     everybody passes a length check and serves nobody.
//   W  write       -- the upsert is keyed on_conflict=license_hash,<idCol>.
//                     Drop license_hash from that key and A's write REPLACES
//                     B's row, with a normal 200 either way. Asserted on the
//                     conflict key and on the body carrying the HANDLER-derived
//                     hash rather than anything the caller sent.
//   Winj           -- a license_hash inside the payload must not move the row.
//
// ── WHAT THIS DOES NOT DO ────────────────────────────────────────────────
// It does not test the DATABASE. A wrong RLS policy or an over-wide GRANT
// passes every arm here. It asserts the APPLICATION half of tenant isolation,
// which is the half a refactor of api/sd-data.js can break.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['cross', 'tenant', 'dispatchers', 'fixture'].join('-');

const assert = require('assert');
const path = require('path');

const HASH_A = 'tenant-A-hash';
const HASH_B = 'tenant-B-hash';

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}

// ── THE MOCK. THIS IS THE TEST. ───────────────────────────────────────────
// It parses every `<col>=eq.<value>` clause out of the query string and
// filters the seeded rows by ALL of them, the way PostgREST does. Drop
// `license_hash=eq.` from the handler and the mock matches on the remaining
// clause alone, returns tenant B's row, and the content assertion fails.
//
// EVERY WAY IT IS UNFAITHFUL RUNS IN THE SAFE DIRECTION, checked rather than
// hoped (and confirmed by CC's review of the reference): an unrecognised
// clause -- an uppercase or dotted column, `and=(...)`/`or=(...)`, `not.`,
// `in.` -- is simply not applied, so the mock returns MORE rows than PostgREST
// would and the content assertion fails LOUDER. The only case returning
// everything is `eqs` empty, which is the no-filter case the negative control
// at the bottom asserts. No query shape makes it return FEWER rows.
//
// AND EVERY ARM ASSERTS A'S ROW IS PRESENT, not only that B's is absent:
// `String(r[col]) === value` means a filter on a column the fixtures do not
// carry matches nothing and yields [], which an absence-only assertion would
// pass for entirely the wrong reason.
function postgrestMock(rows, calls) {
  return async function (url, opts) {
    const u = String(url);
    calls.push({ url: u, opts: opts || null });
    const q = u.indexOf('?') >= 0 ? u.slice(u.indexOf('?') + 1) : '';
    const eqs = [];
    q.split('&').forEach(function (part) {
      const m = part.match(/^([a-z0-9_]+)=eq\.(.*)$/);
      if (m) eqs.push([m[1], decodeURIComponent(m[2])]);
    });
    // ── A CREDENTIAL LOOKUP IS NOT THE QUERY UNDER TEST (2026-09-21) ─────
    // api/sd-data.js's session gate re-checks that the signed-in employee is
    // STILL ACTIVE, and it does that with a real read of the app's employee
    // table. Without an answer here, SAIRNfreedom's newly gated resources
    // answered CREDENTIAL_INACTIVE and eight arms went UNREACHED.
    //
    // ANSWERED FOR THE TENANT IN THE QUERY, so it stays tenant-scoped rather
    // than becoming a hole: a credential lookup for tenant B gets tenant B's
    // credential. And never for a table under test -- no credential store is
    // in UNITS today, but the discipline is cheap and the ownbranch suite
    // already had to learn it the hard way.
    if (/_employee_auth\?/.test(u)) {
      const forHash = (eqs.filter(function (kv) { return kv[0] === 'license_hash'; })[0] || [])[1];
      return { ok: true, status: 200, json: async function () {
        return [{ license_hash: forHash || HASH_A, employee_id: 'emp-1',
                  role: 'post.govern', active: true }]; } };
    }
    if (opts && opts.method === 'POST') {
      const sent = JSON.parse(opts.body);
      return { ok: true, status: 200, json: async function () { return [sent]; } };
    }
    if (opts && opts.method === 'PATCH') {
      return { ok: true, status: 200, json: async function () { return [{ data: {} }]; } };
    }
    const matches = rows.filter(function (r) {
      return eqs.every(function (kv) { return String(r[kv[0]]) === kv[1]; });
    });
    return { ok: true, status: 200, json: async function () { return matches; } };
  };
}

const { signSessionToken } = require('./_lib/auth');

// Fresh per call. The handler caches nothing across requires, and a stale
// module would carry the previous tenant's licence stub into the next arm.
function loadHandler(licHash, appId, fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: licHash,
                 trial_ends_at: null, stripe_subscription_id: null, app_id: appId };
      }
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

// The session token is signed against the hash the HANDLER derives from the
// bearer key. Sign it against anything else and the handler answers
// NO_SESSION -- which reads as "isolation works" and is a false pass.
function mockReq(body, licHash, app, role) {
  const headers = { authorization: 'Bearer KEY-FOR-' + licHash };
  // `app === null` means the branch has NO session gate and no token can be
  // signed for it. Sending one anyway would be inventing a credential the
  // handler never asks for, and would hide that the gate is absent.
  if (app) {
    headers['x-sd-auth'] = signSessionToken({ app: app, employee_id: 'emp-1',
                                              role: role, license_hash: licHash });
  }
  return { method: 'POST', headers: headers, body: body };
}

// ── THE UNITS ─────────────────────────────────────────────────────────────
// app  : the session app the dispatcher's gate demands (third argument to
//        verifySessionToken -- without it a valid session for another SAIRN
//        app would pass, which is Guardian Check 28's collision).
//        `null` means the branch has NO session gate -- see SF_RESOURCES.
// role : the role its role-gate demands, where it has one.
// members: [resource, idCol, payloadExtras?] . idCol comes from the map in
//        sd-data.js and is what the upsert's on_conflict key must carry
//        alongside license_hash.
//
// ── WHY SOME MEMBERS CARRY payloadExtras, AND WHY THAT IS NOT CHEATING ────
// Several resources validate their payload BEFORE the upsert -- a coverage
// rule needs a payer, a denial needs a patient and an amount, a timesheet
// needs a Monday and six numbers. An arm whose payload fails validation
// answers 400 and NEVER REACHES the conflict key, so it proves nothing about
// tenancy. The extras exist to get past the resource's own front door to the
// line under test, and they are the MINIMUM each validator demands -- nothing
// here weakens an isolation assertion. An arm that still cannot get through
// is reported UNREACHED rather than passed, which is the whole point of that
// list: a write arm that silently never ran is indistinguishable from one
// that ran and found nothing.
const WRITE_BLOCKED = {
  // Needs a co-signature from api/sv-witness.js -- a second employee
  // confirming a controlled-substance entry. Forging one in a test would be
  // forging the control itself, so the WRITE arm is disclosed as not covered
  // and the READ arm still asserts list isolation for this resource.
  sv_controlled: 'the controlled-substance register requires a witness '
    + 'co-signature (api/sv-witness.js); forging one here would be forging the '
    + 'control. READ isolation is covered; WRITE is not.'
};
const UNITS = [
  { map: 'DNT_RESOURCES', app: 'sairndental', role: 'owner', members: [
    ['dnt_ar', 'ar_id'], ['dnt_charges', 'charge_id'],
    ['dnt_coverage_rules', 'coverage_rule_id',
      { payer: 'Acme', procedure_type_id: 'PT-1', coverage_percent: 50 }],
    ['dnt_denial', 'denial_id',
      { patient_id: 'P-1', amount: 100, denied_on: '2026-09-01', code: 'CO-45',
        stage: 'none' }],
    ['dnt_gfe', 'gfe_id'],
    ['dnt_patients', 'patient_id',
      { name: 'A Patient', date_of_birth: '1980-01-01', dob: '1980-01-01',
        guardian: { name: 'G', phone: '555' } }],
    ['dnt_payments', 'payment_id'], ['dnt_revenue', 'revenue_id'],
    ['dnt_txplans', 'txplan_id',
      { patient_id: 'P-1', title: 'Plan',
        status: 'proposed',
        items: [{ procedure_type_id: 'PT-1', fee: 100 }] }],
    ['dnt_referrals', 'referral_id',
      { direction: 'outgoing', patient_name: 'A Patient',
        external_party: 'Dr Example, Oral Surgery',
        reason: 'Third molar evaluation', date: '2026-09-01',
        status: 'Pending' }],
    ['dnt_procedure_types', 'procedure_type_id',
      { cdt_code: 'D1110', description: 'Prophylaxis, adult' }],
    ['dnt_recall_outreach', 'outreach_id',
      { procedure_type_id: 'PT-1', patient_id: 'P-1', on: '2026-09-01',
        channel: 'phone', outcome: 'booked' }]] },
  { map: 'SV_RESOURCES', app: 'sairnvet', role: 'owner', members: [
    ['sv_audit_log', 'audit_log_id'], ['sv_billing', 'billing_id'],
    ['sv_compliance', 'compliance_id'], ['sv_controlled', 'controlled_id'],
    ['sv_patients', 'patient_id']] },
  { map: 'BLD_RESOURCES', app: 'sairnbuild', role: 'owner', members: [
    ['bld_costs', 'cost_id'], ['bld_incidents', 'incident_id'],
    ['bld_price_points', 'price_point_id'], ['bld_sub_bids', 'sub_bid_id'],
    // ── EIGHT MORE, 2026-09-23. Every one is Tier A and every one sat in
    //    cross_tenant_isolation_scope's NONE bucket -- a Tier A resource with
    //    no cross-tenant arm at all. They go through the SAME generic
    //    dispatcher as the four above, which is exactly why each is driven
    //    SEPARATELY rather than assumed: the risk this catches is a resource
    //    wired to a bespoke branch that forgot the filter, and that is
    //    invisible until the resource itself is driven.
    ['bld_jobs', 'job_id'], ['bld_checks', 'check_id'],
    ['bld_pos', 'po_id'], ['bld_change_orders', 'change_order_id'],
    ['bld_lien_waivers', 'lien_waiver_id'], ['bld_subs', 'sub_id'],
    ['bld_timesheet', 'timesheet_id'],
    ['bld_photo_analyses', 'photo_analysis_id']] },
  { map: 'SDN_RESOURCES', app: 'sairndesign', role: 'owner', members: [
    ['sdn_discounts', 'discount_id'], ['sdn_invoices', 'invoice_id'],
    ['sdn_contracts', 'contract_id']] },
  { map: 'LEG_RESOURCES', app: 'sairnlegacy', role: 'owner', members: [
    ['leg_certs', 'cert_id'], ['leg_invoices', 'invoice_id'],
    ['leg_preneed', 'preneed_id']] },
  { map: 'SC_RESOURCES', app: 'sairncode', role: 'admin', members: [
    ['sc_ar', 'entry_id'], ['sc_claims', 'entry_id'],
    ['sc_compliance', 'entry_id'], ['sc_credential_scope', 'entry_id'],
    ['sc_denial', 'entry_id'], ['sc_denial_events', 'entry_id'],
    ['sc_revenue', 'entry_id'],
    ['sc_auth_requests', 'entry_id'], ['sc_coded_items', 'entry_id'],
    ['sc_hcc', 'entry_id']] },
  // ── LAW_RESOURCES HAD NO UNIT HERE AT ALL (added 2026-09-23) ───────────
  // Seven Tier A SAIRNlaw resources sat in the NONE bucket together, which is
  // what an absent UNIT looks like from the coverage side: not one resource
  // missed, a whole dispatcher never driven. law_trusttx and the other phase-2
  // rows are gated separately and are covered elsewhere.
  { map: 'LAW_RESOURCES', app: 'sairnlaw', role: 'owner', members: [
    ['law_timeentries', 'timeentry_id',
      { matter_id: 'M-1', billing_code: 'L110', hours: 1, rate: 250, billable: true }],
    ['law_clecredits', 'clecredit_id'],
    ['law_optx', 'optx_id'], ['law_pimedical', 'pimedical_id'],
    ['law_mattertasks', 'mattertask_id'], ['law_matterdocs', 'matterdoc_id'],
    ['law_mattermilestones', 'mattermilestone_id']] },
  { map: 'SD_LOCAL_RESOURCES', app: 'stonedesk', role: 'owner', members: [
    ['sd_aiquotes', 'aiquote_id'], ['sd_fin_jobs', 'fin_job_id'],
    ['sd_invoices', 'invoice_id'], ['sd_negotiated_prices', 'negotiated_price_id'],
    ['sd_order_history', 'order_id'], ['sd_pricing_rules', 'pricing_rule_id']] },
  // ── THIS BRANCH HAD NO SESSION GATE, AND NOW IT DOES (2026-09-21) ───────
  // The first version of this entry read `app: null, role: null` and recorded
  // why: SF_RESOURCES went straight from the map test to the query,
  // `sairnfreedom` was not in ROLES_BY_APP so no token could be signed for it,
  // and three Tier A resources -- sf_accounts, sf_ledger, sf_vendor_prices --
  // were authorised by the LICENCE ALONE. That was reported as a separate
  // finding rather than worked around, and it has since been fixed: the app
  // got a credential table, a ROLES_BY_APP entry, api/sf-auth.js, an X-SD-Auth
  // header, and those three resources are in SD_SESSION_GATED.
  //
  // SO THE CONFIG CHANGES, NOT THE ASSERTION. The gate answering 403 turned
  // eight arms RED as UNREACHED rather than letting them pass, which is the
  // third state doing exactly its job -- a config that no longer matches the
  // handler is not an isolation failure and is not a pass.
  //
  // post.govern is the app's SOLE governance capability, from its own
  // CAPABILITIES array. The gate asks for identity, not rank, so any active
  // capability would reach the query; this one is used because it is the one
  // bootstrap mints.
  { map: 'SF_RESOURCES', app: 'sairnfreedom', role: 'post.govern', members: [
    ['sf_accounts', 'account_id'], ['sf_ledger', 'ledger_id'],
    ['sf_vendor_prices', 'vendor_price_id']] },
  { map: 'SB_RESOURCES', app: 'sairnbiz', role: 'owner', members: [
    ['sb_incidents', 'incident_id'], ['sb_payruns', 'payrun_id'],
    ['sb_po', 'po_id'], ['sb_recv', 'recv_id'],
    // week must be a real MONDAY and hours exactly six finite 0..24 values.
    ['sb_ts', 'ts_id',
      { emp: 'E-1', week: '2026-09-21', hours: [8, 8, 8, 8, 8, 0] }]] },
  { map: 'SD_HR', app: 'stonedesk', role: 'owner', members: [
    ['sd_hr_employees', 'employee_key'], ['sd_hr_certs', 'cert_key']] }
];

// A resource the handler refuses for a reason OTHER than tenancy -- a missing
// role, a validation rule, an unrelated 400 -- must not be silently scored as
// isolated. THE THIRD STATE: an arm that could not reach the code it is about
// reports UNREACHED, never pass and never fail-as-isolation.
const UNREACHED = [];

async function listRead(unit, resource, idCol) {
  const rows = [
    { license_hash: HASH_A, [idCol]: 'A-1', data: { id: 'A-1', owner: 'A' } },
    { license_hash: HASH_B, [idCol]: 'B-1', data: { id: 'B-1', owner: 'B' } }
  ];
  const calls = [];
  const h = loadHandler(HASH_A, unit.app, postgrestMock(rows, calls));
  const res = mockRes();
  await h(mockReq({ action: 'read', resource: resource }, HASH_A, unit.app, unit.role), res);
  return { res: res, calls: calls };
}

(async function () {
  console.log('CROSS-TENANT ISOLATION -- the generic dispatchers (phases 1 and 2)');

  for (const unit of UNITS) {
    section(unit.map + '  (' + unit.app + ', role ' + unit.role + ') -- '
      + unit.members.length + ' Tier A member(s)');

    for (const [resource, idCol, extras] of unit.members) {
      // ── SHAPE L ──────────────────────────────────────────────────────────
      await test(resource + ' [L] tenant A sees ONLY tenant A rows', async () => {
        const { res, calls } = await listRead(unit, resource, idCol);
        if (res.statusCode !== 200) {
          UNREACHED.push([resource, 'read', res.statusCode,
                          (res.body && res.body.error && res.body.error.code) || '']);
          assert.fail('UNREACHED: the read answered ' + res.statusCode + ' '
            + JSON.stringify(res.body) + ' -- this arm never reached the tenant '
            + 'filter, so it proves nothing about isolation. Fix the unit config '
            + '(app/role), do not relax the assertion.');
        }
        const got = (res.body && res.body.data) || [];
        const owners = got.map(function (x) { return x && x.owner; }).sort();
        assert.deepStrictEqual(owners, ['A'],
          'tenant A read returned ' + JSON.stringify(owners) + ' -- anything other '
          + 'than exactly ["A"] means the license_hash filter is absent, ANDed '
          + 'wrong, or the rows returned are not the rows it filtered');
        assert.ok(calls.some(function (c) {
          return c.url.indexOf('license_hash=eq.' + HASH_A) !== -1; }),
          'no query carried license_hash=eq.' + HASH_A + ': '
          + JSON.stringify(calls.map(function (c) { return c.url; })));
      });

      // ── SHAPE W ──────────────────────────────────────────────────────────
      if (WRITE_BLOCKED[resource]) {
        console.log('  --   ' + resource + ' [W] NOT COVERED: ' + WRITE_BLOCKED[resource]);
        continue;
      }
      await test(resource + ' [W] A writing B\'s id lands under A, not B', async () => {
        const calls = [];
        const h = loadHandler(HASH_A, unit.app, postgrestMock([], calls));
        const res = mockRes();
        const payload = Object.assign(
          { id: 'B-1', amount: 1, name: 'x', entry_id: 'B-1',
            patient_id: 'P-1', customer_id: 'C-1', stolen: true },
          extras || {}, { id: 'B-1' });
        await h(mockReq({ action: 'write', resource: resource, payload: payload },
                        HASH_A, unit.app, unit.role), res);
        const post = calls.filter(function (c) { return c.opts && c.opts.method === 'POST'; })[0];
        if (!post) {
          UNREACHED.push([resource, 'write', res.statusCode,
                          (res.body && res.body.error && res.body.error.code) || '']);
          assert.fail('UNREACHED: no upsert was sent; the handler answered '
            + res.statusCode + ' ' + JSON.stringify(res.body) + '. This arm never '
            + 'reached the conflict key, so it proves nothing.');
        }
        assert.ok(post.url.indexOf('on_conflict=license_hash,') !== -1,
          'the upsert conflict key does not lead with license_hash: ' + post.url
          + ' -- drop license_hash from it and tenant A overwrites tenant B');
        const sent = JSON.parse(post.opts.body);
        assert.strictEqual(sent.license_hash, HASH_A,
          'the row was written under ' + JSON.stringify(sent.license_hash)
          + ' rather than the hash the handler derived from the bearer key');
      });
    }

    // ── SHAPE L, THE OTHER DIRECTION, once per unit ───────────────────────
    // A handler hardcoded to one tenant passes every A-only arm above.
    const [firstRes, firstId, firstExtras] = unit.members[0];
    await test(unit.map + ' [L-rev] tenant B sees ONLY tenant B rows', async () => {
      const rows = [
        { license_hash: HASH_A, [firstId]: 'A-1', data: { id: 'A-1', owner: 'A' } },
        { license_hash: HASH_B, [firstId]: 'B-1', data: { id: 'B-1', owner: 'B' } }
      ];
      const h = loadHandler(HASH_B, unit.app, postgrestMock(rows, []));
      const res = mockRes();
      await h(mockReq({ action: 'read', resource: firstRes }, HASH_B, unit.app, unit.role), res);
      if (res.statusCode !== 200) {
        assert.fail('UNREACHED: ' + res.statusCode + ' ' + JSON.stringify(res.body));
      }
      const owners = ((res.body && res.body.data) || []).map(function (x) { return x && x.owner; });
      assert.deepStrictEqual(owners, ['B'],
        'tenant B read returned ' + JSON.stringify(owners) + '. BOTH DIRECTIONS ARE '
        + 'DRIVEN DELIBERATELY: a handler hardcoded to one tenant passes every '
        + 'A-only arm above and fails here.');
    });

    // ── SHAPE Winj, once per unit ─────────────────────────────────────────
    await test(unit.map + ' [Winj] a payload license_hash does not move the row', async () => {
      const calls = [];
      const h = loadHandler(HASH_A, unit.app, postgrestMock([], calls));
      const res = mockRes();
      await h(mockReq({ action: 'write', resource: firstRes,
                        payload: Object.assign(
                          { id: 'X-1', license_hash: HASH_B, amount: 1, name: 'x',
                            entry_id: 'X-1', patient_id: 'P-1', customer_id: 'C-1' },
                          firstExtras || {}, { id: 'X-1', license_hash: HASH_B }) },
                      HASH_A, unit.app, unit.role), res);
      const post = calls.filter(function (c) { return c.opts && c.opts.method === 'POST'; })[0];
      if (!post) {
        assert.fail('UNREACHED: no upsert was sent; handler answered ' + res.statusCode
          + ' ' + JSON.stringify(res.body));
      }
      const sent = JSON.parse(post.opts.body);
      assert.strictEqual(sent.license_hash, HASH_A,
        'a license_hash INSIDE the payload reached the stored row as '
        + JSON.stringify(sent.license_hash) + '. The handler must use the hash it '
        + 'derived from the bearer key and nothing else.');
    });
  }

  // ── THE NEGATIVE CONTROL ON THE MOCK ITSELF ─────────────────────────────
  section('THE NEGATIVE CONTROL -- the mock still distinguishes filtered from unfiltered');
  await test('an unfiltered query returns BOTH tenants', async () => {
    const rows = [
      { license_hash: HASH_A, invoice_id: 'A-1', data: { owner: 'A' } },
      { license_hash: HASH_B, invoice_id: 'B-1', data: { owner: 'B' } }
    ];
    const f = postgrestMock(rows, []);
    const unfiltered = await (await f('https://x/rest/v1/t?select=data')).json();
    assert.strictEqual(unfiltered.length, 2,
      'the mock returned ' + unfiltered.length + ' rows for a query with NO eq. '
      + 'clauses. It is not filtering, so every arm above proves nothing.');
    const filtered = await (await f('https://x/rest/v1/t?license_hash=eq.'
      + HASH_A + '&select=data')).json();
    assert.strictEqual(filtered.length, 1,
      'the mock returned ' + filtered.length + ' rows for a filtered query');
    const both = await (await f('https://x/rest/v1/t?license_hash=eq.' + HASH_A
      + '&invoice_id=eq.B-1&select=data')).json();
    assert.strictEqual(both.length, 0,
      'two eq. clauses must be ANDed: A\'s hash with B\'s id matches nothing');
  });

  if (UNREACHED.length) {
    console.log('\nUNREACHED -- arms that never got to the tenant filter:');
    UNREACHED.forEach(function (u) {
      console.log('  %s %s -> %s %s', u[0], u[1], u[2], u[3]);
    });
    console.log('These are NOT isolation failures and NOT passes. They are a');
    console.log('unit config (app/role) that does not match the handler\'s gate.');
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
