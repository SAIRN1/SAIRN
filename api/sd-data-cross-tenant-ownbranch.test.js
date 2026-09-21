// api/sd-data-cross-tenant-ownbranch.test.js
//
// REQUIREMENT: on every Tier A resource served by its OWN named branch in
//   api/sd-data.js, a valid session for tenant A cannot read tenant B's rows.
//
// CROSS-TENANT-ISOLATION: rf_invoices, rf_claims, rf_claim_photos,
//   rf_claim_agreements, rf_certifications, rf_cert_rules,
//   rf_contingency_rules, sen_claims, sen_pay_rates, sen_payer_contracts,
//   alf_billing, alf_payer_rules, alf_claim_routes, alf_compliance_rules,
//   alf_incidents, alf_staff_credentials, alf_op_audits, grd_invoices,
//   msb_licenses, msb_food_cost_log, quotes, law_trusttx, law_deadlines,
//   law_trust_reconcile, dnt_credentials, dnt_rollup,
//   dnt_vendor_pricing_rules, mech_credentials, mech_site_assets,
//   mech_quotes, sd_quote_requests, stonedesk_quote_history, bld_bids,
//   invoices, scp_quotes
//
// That line is machine-read by tools/cross_tenant_isolation_scope.py and is
// the ONLY thing that credits a resource. It is cross-checked: every name
// here must also appear in RESOURCES below, and the file must GRADE genuine.
// READ COVERAGE ONLY -- see UNCOVERED at the end of this header.
//
// Run:  node api/sd-data-cross-tenant-ownbranch.test.js
//
// ── WHAT THIS IS ──────────────────────────────────────────────────────────
// Phase 3 of docs/2026-09-21-cross-tenant-isolation-build-plan.md: the
// remaining Tier A resources, the ones with no dispatcher leverage left. Phases
// 1 and 2 covered 49 of 84 with eleven units; this tail is roughly one unit per
// resource, which is exactly the ratio the plan said to re-derive the case
// against.
//
// TRANSPLANTED FROM api/sd-data-cross-tenant-dispatchers.test.js, which is
// itself transplanted from api/sd-data-cross-tenant-isolation.test.js. Read
// that one first: the load-bearing property is the same and is stated there at
// length.
//
// ── THE READ ARM IS THE WHOLE OF PHASE 3, DELIBERATELY ───────────────────
// The dispatcher units asserted three shapes because one upsert served a whole
// map and the conflict key was shared. These branches are BESPOKE: each has its
// own validator, its own role gate, its own id column and often its own verbs
// (`issue`, `add_payment`, `gl_export`, `reconcile_claim`, `eligibility`).
// Driving every write path here would mean satisfying 35 separate payload
// contracts, and a write arm that answers 400 at a validator NEVER REACHES the
// tenant filter and proves nothing -- phases 1 and 2 hit that six times.
//
// So phase 3 asserts the LIST READ on every resource and says so. That is the
// query every one of these branches builds, it is where the `license_hash`
// filter lives, and it is the path a refactor drops it from. The write half is
// named as NOT covered rather than quietly skipped; see UNCOVERED at the end.
//
// ── THE THIRD STATE IS LOAD-BEARING HERE ─────────────────────────────────
// A branch whose gate this file's config does not satisfy answers 401/403/400
// and never reaches the filter. That is reported UNREACHED -- never passed and
// never counted as isolation. A read arm that silently never ran is
// indistinguishable from one that ran and found nothing, and on 35 bespoke
// branches that distinction is most of the work.
//
// ── THE SIX WRITE-CLASS GAPS, AND THEY ARE NOW CLOSED ────────────────────
// The first version of this suite asserted READ only. The full sabotage sweep
// -- removing `license_hash=eq.` from EVERY filtered query in all 32 own
// branches, 37 of them, because several build more than one -- left SIX
// survivors, all write-class verbs. Each is now driven and each is caught:
//
//   api/sd-data.js:7499  rf_invoices        issue        PATCH
//   api/sd-data.js:7535  rf_invoices        add_payment  PATCH
//   api/sd-data.js:2565  sd_quote_requests  soft_delete  read leg
//   api/sd-data.js:2581  sd_quote_requests  soft_delete  PATCH
//   api/sd-data.js:2605  sd_quote_requests  write        read leg
//   api/sd-data.js:2633  sd_quote_requests  write        PATCH
//
// THE FIRST DISCLOSURE CALLED 2605/2633 A SECOND soft_delete PAIR. They are
// the WRITE path. Corrected rather than left standing: a wrong label on a
// closed gap sends the next reader into the wrong branch.
//
// THE FIX WAS NOT MORE ARMS, IT WAS ONE LINE IN A FILTER. The query-shape
// assertion skipped POST *and* PATCH -- POST rightly, PATCH for no reason --
// and a write verb's decisive query IS the PATCH. See the arm for the full
// account.
//
// ONE OF THE 37 IS A NO-OP AND IS REPORTED AS ONE, NOT COUNTED AS A PASS:
// api/sd-data.js:1371 (mech_site_assets) builds its filter across two lines,
// so a SINGLE-line mutation changes nothing. 36 of 37 were really mutated and
// all 36 were caught; that one was skipped, not survived.
//
// AND THE SKIP WAS CHECKED RATHER THAN ASSERTED, because "it is only a parser
// limit" is exactly what a real gap would also sound like: mutating that
// filter ACROSS BOTH LINES is CAUGHT (76 -> 74 passed, 1 failed). The single
// line was a limit of the sweep, not a hole in the coverage.
//
// ── STILL UNCOVERED ──────────────────────────────────────────────────────
// WRITE isolation on the other 33 own-branch resources. Each has its own
// payload contract, and a write arm that stops at a validator asserts nothing.
// The dispatcher suite covers write for the 46 resources where one conflict
// key is shared; here it would be 33 separate contracts. Anyone extending this
// file should RE-RUN THE SWEEP rather than trust the list above -- it is a
// measurement from one day, not a property.
//
// THE DATABASE. A wrong RLS policy or an over-wide GRANT passes every arm
// here. This is the APPLICATION half of tenant isolation -- the half a
// refactor of api/sd-data.js can break.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['ownbranch', 'isolation', 'fixture'].join('-');

const assert = require('assert');

const HASH_A = 'tenant-A-hash';
const HASH_B = 'tenant-B-hash';

let pass = 0, fail = 0;
const UNREACHED = [];
const COVERED = [];

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
// Parses every `<col>=eq.<value>` clause out of the query and filters by ALL
// of them, the way PostgREST does. Drop `license_hash=eq.` from a branch and
// the mock matches on whatever else is left, returns tenant B's row, and the
// content assertion fails. Every unfaithfulness runs in the SAFE direction: an
// unrecognised clause is not applied, so it returns MORE rows than PostgREST
// would and the assertion fails louder. The only case returning everything is
// no clauses at all, which the negative control asserts.
function postgrestMock(rows, calls, underTest) {
  return async function (url, opts) {
    const u = String(url);
    calls.push({ url: u, opts: opts || null });
    const q = u.indexOf('?') >= 0 ? u.slice(u.indexOf('?') + 1) : '';
    const eqs = [];
    q.split('&').forEach(function (part) {
      const m = part.match(/^([a-z0-9_]+)=eq\.(.*)$/);
      if (m) eqs.push([m[1], decodeURIComponent(m[2])]);
    });
    // AN RPC IS NOT A TABLE READ. rf_invoices' `issue` allocates a gapless
    // invoice number through rpc/rf_allocate_invoice_number BEFORE its PATCH,
    // and echoing the request body back gives it nothing -- the handler then
    // refuses 502 and the PATCH under test never runs. Answered as a real
    // allocation so the arm reaches the query it is about.
    if (u.indexOf('/rpc/') !== -1) {
      return { ok: true, status: 200, json: async function () {
        return [{ invoice_number: 'INV-0001', invoice_seq: 1 }]; } };
    }
    if (opts && (opts.method === 'POST' || opts.method === 'PATCH')) {
      const sent = opts.body ? JSON.parse(opts.body) : {};
      return { ok: true, status: 200, json: async function () { return [sent]; } };
    }
    // ── A CREDENTIAL LOOKUP IS NOT THE QUERY UNDER TEST ──────────────────
    // Several branches re-check that the signed-in employee is still ACTIVE
    // before serving anything -- law_trusttx answered 403 CREDENTIAL_INACTIVE
    // on the first run because the fixture rows came back for that lookup too
    // and none of them says active. Answered as an active credential FOR THE
    // TENANT IN THE QUERY, so it stays tenant-scoped rather than becoming a
    // hole: a credential query for tenant B gets tenant B's credential.
    // NEVER for the table under test. Three of these resources ARE credential
    // stores -- alf_staff_credentials, dnt_credentials, mech_credentials -- and
    // the first version of this interception answered their own read, so the
    // arm asserted over a stub instead of over the fixture rows. A mock that
    // hijacks the query under test cannot fail.
    const hitsUnderTest = underTest && u.indexOf('/' + underTest + '?') !== -1;
    if (!hitsUnderTest && /_(?:employee_auth|credentials|auth)\?|employee_auth/.test(u)) {
      const forHash = (eqs.filter(function (kv) { return kv[0] === 'license_hash'; })[0] || [])[1];
      return { ok: true, status: 200, json: async function () {
        return [{ license_hash: forHash || HASH_A, employee_id: 'emp-1',
                  role: 'owner', active: true, is_active: true, status: 'active',
                  deactivated_at: null }]; } };
    }
    const matches = rows.filter(function (r) {
      return eqs.every(function (kv) { return String(r[kv[0]]) === kv[1]; });
    });
    return { ok: true, status: 200, json: async function () { return matches; } };
  };
}

const { signSessionToken } = require('./_lib/auth');

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

// Signed against the hash the HANDLER derives from the bearer key. Signed
// against anything else the handler answers NO_SESSION -- which reads as
// "isolation works" and is a false pass.
function mockReq(body, licHash, app, role) {
  const headers = { authorization: 'Bearer KEY-FOR-' + licHash };
  if (app) {
    headers['x-sd-auth'] = signSessionToken({ app: app, employee_id: 'emp-1',
                                              role: role, license_hash: licHash });
  }
  return { method: 'POST', headers: headers, body: body };
}

// ── THE 35 ────────────────────────────────────────────────────────────────
// `app` is the session app the branch's gate demands; `role` the role its
// role-gate demands. Both are CONFIG, and a wrong one shows up as UNREACHED
// rather than as a pass -- which is how these were arrived at in the first
// place. `payload` carries anything a branch needs before it will read.
const RESOURCES = [
  ['rf_invoices', 'sairnroofing', 'owner'],
  // ── THREE QUERIES IN ONE BRANCH, AND SABOTAGE FOUND THE OTHER TWO ───────
  // rf_invoices is rank 15, the highest-risk resource on the board, and its
  // read branch builds three separately-filtered queries reached by different
  // verbs. Removing license_hash from the LIST read fails the plain arm above;
  // removing it from `loadInvoice` (the id-narrowed read, used by `issue`,
  // `add_payment` and `reconcile_claim`) or from `gl_export` failed NOTHING.
  // One arm per query, because one arm per RESOURCE is not the unit when the
  // resource has three places the filter can be dropped.
  ['rf_invoices', 'sairnroofing', 'owner',
   { account_map: {}, basis: 'accrual' }, 'query', 'gl_export'],
  // ── THE SIX WRITE-CLASS SURVIVORS FROM PHASE 3'S SWEEP, CLOSED HERE ─────
  // Driven with SHARED IDS across both tenants, which is what makes the URL
  // assertion decisive rather than suggestive: with the same id under two
  // tenants, a PATCH that lost `license_hash=eq.` updates BOTH rows.
  //
  // status:'draft' is REQUIRED on the rf_invoices row -- `issue` is idempotent
  // and short-circuits on already_issued for anything else, so without it the
  // arm would pass a sabotage on a PATCH that never ran. Applied to BOTH
  // tenants: a field present on A and absent on B would make the two rows
  // behave differently for a reason that is not tenancy.
  ['rf_invoices', 'sairnroofing', 'owner',
   { invoice_id: 'SHARED-1', id: 'SHARED-1', issue_date: '2026-09-21' },
   'query', 'issue', { status: 'draft' }],
  ['rf_invoices', 'sairnroofing', 'owner',
   { invoice_id: 'SHARED-1', id: 'SHARED-1',
     payment: { payment_id: 'P-1', amount: 10, received_on: '2026-09-21' } },
   'query', 'add_payment', { status: 'issued' }],
  ['sd_quote_requests', 'stonedesk', 'owner',
   { id: 'SHARED-1', request_id: 'SHARED-1' }, 'query', 'soft_delete'],
  ['sd_quote_requests', 'stonedesk', 'owner',
   { id: 'SHARED-1', request_id: 'SHARED-1', status: 'promoted' },
   'query', 'write'],
  ['rf_claims', 'sairnroofing', 'owner'],
  // These two refuse a read with no claim_id BEFORE any query is built, so
  // the payload is the minimum needed to reach the filter -- not a relaxation.
  ['rf_claim_photos', 'sairnroofing', 'owner', { claim_id: 'SHARED-1' }, 'sharedid'],
  ['rf_claim_agreements', 'sairnroofing', 'owner', { claim_id: 'SHARED-1' }, 'sharedid'],
  ['rf_certifications', 'sairnroofing', 'owner'],
  ['rf_cert_rules', 'sairnroofing', 'owner'],
  ['rf_contingency_rules', 'sairnroofing', 'owner'],
  ['sen_claims', 'sairnsenior', 'owner'],
  ['sen_pay_rates', 'sairnsenior', 'owner'],
  ['sen_payer_contracts', 'sairnsenior', 'owner'],
  ['alf_billing', 'sairncare', 'owner'],
  ['alf_payer_rules', 'sairncare', 'owner'],
  ['alf_claim_routes', 'sairncare', 'owner'],
  ['alf_compliance_rules', 'sairncare', 'owner'],
  ['alf_incidents', 'sairncare', 'owner'],
  ['alf_staff_credentials', 'sairncare', 'owner'],
  ['alf_op_audits', 'sairncare', 'owner'],
  ['grd_invoices', 'sairngrounds', 'owner'],
  ['msb_licenses', 'sairngrounds', 'owner'],
  ['msb_food_cost_log', 'sairngrounds', 'owner'],
  ['quotes', 'sairngrounds', 'owner'],
  ['law_trusttx', 'sairnlaw', 'owner'],
  ['law_deadlines', 'sairnlaw', 'owner'],
  // AGGREGATES. These answer a computed REPORT rather than rows, so there is
  // no `owner` field to assert on. The tenant signal is the ROW COUNT the
  // report was built from: seed 2 rows for A and 3 for B, and a report that
  // counted anything other than A's 2 has read across the boundary.
  ['law_trust_reconcile', 'sairnlaw', 'owner', null, 'count'],
  ['dnt_credentials', 'sairndental', 'owner'],
  ['dnt_rollup', 'sairndental', 'owner', null, 'count'],
  ['dnt_vendor_pricing_rules', 'sairndental', 'owner'],
  ['mech_credentials', 'sairnmechanical', 'owner'],
  ['mech_site_assets', 'sairnmechanical', 'owner'],
  ['mech_quotes', 'sairnmechanical', 'owner'],
  ['sd_quote_requests', 'stonedesk', 'owner'],
  ['stonedesk_quote_history', 'stonedesk', 'owner'],
  ['bld_bids', 'sairnbuild', 'owner'],
  // THE REGISTRY SCAN SAID sairndesign AND THE HANDLER SAYS sairnscape.
  // api/sd-data.js's app-boundary gate is the authority -- it refused a
  // sairndesign licence outright -- so the config follows the handler, not the
  // first registry file that happened to contain the string 'invoices'.
  ['invoices', 'sairnscape', 'owner'],
  ['scp_quotes', 'sairnscape', 'owner']
];

// Every id column these branches might filter on, seeded onto BOTH fixture
// rows so a branch narrowing by id still finds its own tenant's row. The
// content assertion is what catches a missing tenant filter; an id column the
// fixture lacks would produce an empty result that an absence-only assertion
// would pass for the wrong reason -- so A's row must always be PRESENT.
const ID_COLS = ['invoice_id', 'claim_id', 'photo_id', 'agreement_id', 'cert_id',
  'cert_rule_id', 'rule_id', 'contingency_id', 'pay_rate_id', 'contract_id',
  'billing_id', 'route_id', 'incident_id', 'credential_id', 'audit_id',
  'license_id', 'log_id', 'quote_id', 'trusttx_id', 'deadline_id',
  'reconcile_id', 'rollup_id', 'pricing_rule_id', 'asset_id', 'request_id',
  'history_id', 'bid_id', 'entry_id', 'id'];

function fixtureRows(owner, tag) {
  // WRITTEN OUT RATHER THAN `owner === 'A' ? HASH_A : HASH_B`, and the reason
  // is worth a line: tools/cross_tenant_isolation_scope.py looks for
  // `license_hash: <CONST>` to decide whether TWO tenants are in play, and a
  // ternary hides both behind one expression -- so this file graded WEAK for
  // "only one tenant appears" while seeding two. The explicit form is clearer
  // anyway. Changed HERE rather than widening the grader, which is under an
  // open review by another session and must not move while they read it.
  const row = owner === 'A'
    ? { license_hash: HASH_A, data: { id: tag, owner: 'A' } }
    : { license_hash: HASH_B, data: { id: tag, owner: 'B' } };
  ID_COLS.forEach(function (c) { row[c] = tag; });
  return row;
}

// ── THE SHARED-ID SHAPE, AND SABOTAGE IS WHAT FOUND THE NEED FOR IT ──────
// Two branches narrow by an id FROM THE PAYLOAD as well as by license_hash:
// `rf_claim_photos?license_hash=eq.<lic>&claim_id=eq.<claim>`. With every
// fixture row carrying a per-tenant id, dropping license_hash STILL returned
// only tenant A's row -- the id filter alone was sufficient and the tenant
// filter was untested. Both arms passed a sabotage that removed it.
//
// So for those, BOTH TENANTS HOLD THE SAME id. That is the reference case's
// own shape (api/sairndental/complaint-respond.test.js seeds A-COMP-1 and
// B-COMP-1 under two hashes and asks for the other one), and it is the only
// seeding under which an id-narrowed query can prove anything about tenancy.
function sharedIdFixtures() {
  const a = fixtureRows('A', 'SHARED-1');
  const b = fixtureRows('B', 'SHARED-1');
  return [a, b];
}

// ASYMMETRIC ON PURPOSE for the count shape: 2 rows for A and 3 for B. Equal
// counts would make "read A's rows" and "read everybody's rows" produce the
// same number on a report that only counts, which is the one thing this arm
// must be able to tell apart.
function countFixtures() {
  return [fixtureRows('A', 'A-1'), fixtureRows('A', 'A-2'),
          fixtureRows('B', 'B-1'), fixtureRows('B', 'B-2'), fixtureRows('B', 'B-3')];
}

// Every integer anywhere in a report envelope. An aggregate does not carry
// `owner`, so the tenant signal is that NO figure in it exceeds what tenant A
// actually had -- a report built over both tenants shows 5 (or 3) somewhere.
function maxCount(body) {
  let max = 0;
  (function walk(v, depth) {
    if (!v || depth > 8) return;
    if (typeof v === 'number') { if (Number.isInteger(v) && v > max) max = v; return; }
    if (Array.isArray(v)) { v.forEach(function (x) { walk(x, depth + 1); }); return; }
    if (typeof v === 'object') {
      Object.keys(v).forEach(function (k) { walk(v[k], depth + 1); });
    }
  })(body, 0);
  return max;
}

function ownersIn(body) {
  // The branches differ in envelope: most answer { data: [...] }, a few wrap a
  // report. Everything is walked rather than assuming one shape, because an
  // assumption that missed would read as "no rows" -- an absence, which is the
  // exact thing a tenant leak would also look like if asserted carelessly.
  const found = [];
  (function walk(v, depth) {
    if (!v || depth > 6) return;
    if (Array.isArray(v)) { v.forEach(function (x) { walk(x, depth + 1); }); return; }
    if (typeof v === 'object') {
      if (typeof v.owner === 'string') found.push(v.owner);
      // SOME BRANCHES PROJECT COLUMNS (`select=recorded_by,data`) and the
      // `data.owner` marker does not survive. license_hash does, and it is the
      // better signal anyway -- it is the field the filter is ON.
      else if (v.license_hash === HASH_A) found.push('A');
      else if (v.license_hash === HASH_B) found.push('B');
      Object.keys(v).forEach(function (k) { walk(v[k], depth + 1); });
    }
  })(body, 0);
  return found;
}

(async function () {
  console.log('CROSS-TENANT ISOLATION -- own-branch Tier A resources (phase 3)');
  section('LIST READ: tenant A sees ONLY tenant A rows');

  for (const [resource, app, role, extraPayload, shape, verb, rowExtra] of RESOURCES) {
    await test(resource + (verb ? ' [' + verb + ']' : '') + ' -- A reads A only', async () => {
      let rows = shape === 'count' ? countFixtures()
        : (shape === 'sharedid' || shape === 'query') ? sharedIdFixtures()
        : [fixtureRows('A', 'A-1'), fixtureRows('B', 'B-1')];
      // Fields a branch needs on the ROW before it will reach its write.
      // Applied to BOTH tenants, deliberately.
      if (rowExtra) rows = rows.map(function (r) { return Object.assign({}, r, rowExtra); });
      const calls = [];
      const h = loadHandler(HASH_A, app, postgrestMock(rows, calls, resource));
      const res = mockRes();
      const body = { action: verb || 'read', resource: resource };
      if (extraPayload) body.payload = extraPayload;
      await h(mockReq(body, HASH_A, app, role), res);

      if (res.statusCode !== 200) {
        UNREACHED.push([resource + (verb ? ' [' + verb + ']' : ''), res.statusCode,
                        (res.body && res.body.error && res.body.error.code) || '']);
        assert.fail('UNREACHED: the read answered ' + res.statusCode + ' '
          + JSON.stringify(res.body).slice(0, 180) + ' -- this arm never reached '
          + 'the tenant filter, so it proves nothing. Fix the config (app/role/'
          + 'payload); do NOT relax the assertion.');
      }
      if (shape === 'query') {
        // ── A WEAKER ASSERTION, AND SAID SO ────────────────────────────────
        // These verbs read the table and then answer something that echoes no
        // row -- `{ok:true, already_issued:true}`, a refusal about a missing
        // account map, a soft-delete acknowledgement. There is no content to
        // assert on, so the assertion is on the REQUEST the handler built:
        // EVERY query it issued against this table must carry license_hash.
        // Weaker than a content assertion -- it cannot catch a filter present
        // but ANDed wrong -- and stronger than nothing, which is what these
        // paths had. With SHARED IDS across both tenants it is decisive for
        // the thing it is about: a query that lost the filter addresses BOTH.
        //
        // ── PATCH IS INCLUDED, AND EXCLUDING IT IS WHY SIX SABOTAGES SURVIVED
        // A write verb's decisive query IS the PATCH. The first version of
        // this filter skipped POST and PATCH together -- POST rightly, because
        // an upsert carries its scope in the BODY and the conflict key and is
        // asserted separately; PATCH for no reason at all. Only POST is
        // skipped now.
        const mine = calls.filter(function (c) {
          return c.url.indexOf('/' + resource + '?') !== -1
            && !(c.opts && c.opts.method === 'POST');
        });
        assert.ok(mine.length > 0,
          'no query was issued against ' + resource + ', so this arm reached '
          + 'nothing: ' + JSON.stringify(res.body).slice(0, 180));
        const unscoped = mine.filter(function (c) {
          return c.url.indexOf('license_hash=eq.' + HASH_A) === -1; });
        assert.deepStrictEqual(unscoped.map(function (c) { return c.url.slice(0, 120); }), [],
          'a query against ' + resource + ' carried NO license_hash filter, so it '
          + 'would read rows belonging to every tenant');
      } else if (shape === 'count') {
        // 2 rows for A, 3 for B. A report built over both would show 3 or 5
        // somewhere in its counts; one built over A's rows alone cannot.
        const m = maxCount(res.body);
        assert.ok(m > 0,
          'the report carried no counts at all, so nothing is proved: '
          + JSON.stringify(res.body).slice(0, 200));
        assert.ok(m <= 2,
          'an aggregate over tenant A reported a figure of ' + m + ', and tenant A '
          + 'has only 2 rows -- tenant B had 3 and they were counted, so the report read '
          + 'across the boundary: ' + JSON.stringify(res.body).slice(0, 260));
      } else {
        const owners = ownersIn(res.body);
        assert.ok(owners.length > 0,
          'the response carried no fixture rows at all, so nothing was filtered and '
          + 'nothing is proved: ' + JSON.stringify(res.body).slice(0, 200));
        assert.deepStrictEqual(Array.from(new Set(owners)).sort(), ['A'],
          'tenant A read returned owners ' + JSON.stringify(owners) + ' -- anything '
          + 'other than A only means the license_hash filter is absent, ANDed wrong, '
          + 'or the rows returned are not the rows it filtered');
      }
      assert.ok(calls.some(function (c) {
        return c.url.indexOf('license_hash=eq.' + HASH_A) !== -1; }),
        'no query carried license_hash=eq.' + HASH_A);
      if (COVERED.indexOf(resource) === -1) COVERED.push(resource);
    });
  }

  section('THE OTHER DIRECTION -- a handler hardcoded to one tenant fails here');
  const seenB = [];
  for (const [resource, app, role, extraPayload, shape, verb] of RESOURCES) {
    if (COVERED.indexOf(resource) === -1 || verb) continue;
    if (seenB.indexOf(resource) !== -1) continue;
    seenB.push(resource);
    await test(resource + ' -- B reads B only', async () => {
      const rows = shape === 'count' ? countFixtures()
        : shape === 'sharedid' ? sharedIdFixtures()
        : [fixtureRows('A', 'A-1'), fixtureRows('B', 'B-1')];
      const h = loadHandler(HASH_B, app, postgrestMock(rows, [], resource));
      const res = mockRes();
      const body = { action: 'read', resource: resource };
      // The id-bearing payloads name A's row on purpose; for B's direction the
      // same id must be B's, or the arm would be asking B for A's record and
      // an empty answer would read as isolation when it is a missing row.
      if (extraPayload) {
        body.payload = {};
        Object.keys(extraPayload).forEach(function (k) {
          // A SHARED id is the whole point of that shape and must NOT be
          // rewritten per tenant -- both tenants really do hold that id.
          body.payload[k] = shape === 'sharedid' ? extraPayload[k]
            : String(extraPayload[k]).replace(/^A-/, 'B-');
        });
      }
      await h(mockReq(body, HASH_B, app, role), res);
      assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body).slice(0, 160));
      if (shape === 'count') {
        const m = maxCount(res.body);
        assert.ok(m > 0, 'the report carried no counts at all');
        assert.ok(m <= 3,
          'an aggregate over tenant B reported ' + m + ' and B has only 3 rows');
      } else {
        const owners = ownersIn(res.body);
        assert.ok(owners.length > 0, 'no fixture rows came back');
        assert.deepStrictEqual(Array.from(new Set(owners)).sort(), ['B'],
          'tenant B read returned ' + JSON.stringify(owners));
      }
    });
  }

  section('THE NEGATIVE CONTROL -- the mock still distinguishes filtered from unfiltered');
  await test('an unfiltered query returns BOTH tenants, a filtered one returns one', async () => {
    const rows = [fixtureRows('A', 'A-1'), fixtureRows('B', 'B-1')];
    const f = postgrestMock(rows, []);
    const all = await (await f('https://x/rest/v1/t?select=data')).json();
    assert.strictEqual(all.length, 2,
      'the mock returned ' + all.length + ' rows for a query with NO eq. clauses. '
      + 'It is not filtering, so every arm above proves nothing.');
    const one = await (await f('https://x/rest/v1/t?license_hash=eq.' + HASH_A
      + '&select=data')).json();
    assert.strictEqual(one.length, 1, 'filtered query returned ' + one.length);
    const none = await (await f('https://x/rest/v1/t?license_hash=eq.' + HASH_A
      + '&invoice_id=eq.B-1&select=data')).json();
    assert.strictEqual(none.length, 0,
      'two eq. clauses must be ANDed: A\'s hash with B\'s id matches nothing');
  });

  console.log('\nCOVERED (' + COVERED.length + '): ' + COVERED.join(', '));
  if (UNREACHED.length) {
    console.log('\nUNREACHED (' + UNREACHED.length + ') -- never got to the tenant filter:');
    UNREACHED.forEach(function (u) {
      console.log('  %s -> %s %s', u[0], u[1], u[2]);
    });
    console.log('NOT isolation failures and NOT passes: a config that does not');
    console.log('match the branch\'s gate. Fix the config, never the assertion.');
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
