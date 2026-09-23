// api/sd-data-bespoke-branch-isolation.test.js
//
// REQUIREMENT: on the last five bespoke branches that graded WEAK, a valid,
//   fully authenticated session for tenant A cannot read or overwrite tenant
//   B's rows.
//
// CROSS-TENANT-ISOLATION: dnt_appointments, law_matters, rf_draws,
//   rf_proposals, rf_supplier_documents
//
// Run:  node api/sd-data-bespoke-branch-isolation.test.js
//
// ── WHY A NEW FILE ────────────────────────────────────────────────────────
// All five graded WEAK, which is the more dangerous of the two empty states
// because it reads as partial coverage. The reasons the grader gave were
// specific and none of them was "somebody wrote a weak test": these resources
// are named by suites about OTHER questions (role gates, append-only
// ordering, restore coherence, the tier-a review gate's own fixtures), and
// two are named by files that read a query with only ONE tenant in them --
// which passes a handler whose filter is present and wrong.
//
// They are also not rows the dispatcher suite can take today:
// api/sd-data-cross-tenant-dispatchers.test.js is under another session's
// active claim while this lands, and three of the five have a write shape
// that suite cannot express at all -- see below.
//
// ── THREE OF THE FIVE HAVE NO CONFLICT KEY, AND THAT IS THE FINDING ───────
// The dispatcher suite's [W] arm asserts `on_conflict=license_hash,<idCol>`:
// drop license_hash from that key and tenant A's write REPLACES tenant B's
// row. rf_proposals and rf_supplier_documents are APPEND-ONLY INSERTS with no
// conflict key at all, and alf_mar (covered in the sibling ALF suite) writes
// through a stored procedure. For those, THE BODY FIELD IS THE ENTIRE
// WRITE-SIDE TENANT BOUNDARY -- there is no key to carry it, no upsert to
// collide, and nothing else in the request that says whose row this is. An
// append-only table cannot overwrite another tenant's row; it can file a
// document under the wrong company, permanently, and be read back as theirs.
//
// So the [W] arms below split by shape rather than asserting one pattern:
//   conflict-key shape   dnt_appointments, law_matters, rf_draws
//   body-field shape     rf_proposals, rf_supplier_documents
//
// ── WHAT THIS DOES NOT DO ─────────────────────────────────────────────────
// It does not test the DATABASE, and it does not test the ROLE gates on these
// branches. `owner` is used throughout so no role rule can narrow an answer
// for a reason other than license_hash.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['bespoke', 'branch', 'isolation', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const { signSessionToken } = require('./_lib/auth');

const HASH_A = 'tenant-A-hash';
const HASH_B = 'tenant-B-hash';

// The resources this suite drives, in the shape
// tools/cross_tenant_isolation_scope.py cross-checks a declaration against.
// [resource, table-id column, app, role, other-app-for-the-collision-arm]
const UNITS = [
  ['dnt_appointments', 'appointment_id', 'sairndental', 'owner', 'sairnvet'],
  ['law_matters', 'matter_id', 'sairnlaw', 'owner', 'sairnbiz'],
  ['rf_draws', 'draw_id', 'sairnroofing', 'owner', 'sairnbuild'],
  ['rf_proposals', 'proposal_id', 'sairnroofing', 'owner', 'sairnbuild'],
  ['rf_supplier_documents', 'document_id', 'sairnroofing', 'owner', 'sairnbuild']
];

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
// `license_hash=eq.` from a handler and the mock matches on whatever clause
// is left -- a job_id, a provider_id, or nothing -- returns the other
// tenant's row, and the content assertion fails.
//
// IT HONOURS `select=`, because these branches ask for named column lists and
// read specific fields back out of them.
//
// EVERY WAY IT IS UNFAITHFUL RUNS IN THE SAFE DIRECTION: an unrecognised
// clause is not applied, so it returns MORE rows than PostgREST would and the
// assertion fails LOUDER. No query shape makes it return FEWER. The negative
// control at the bottom drives that rather than asserting it.
function postgrestMock(rows, calls) {
  return async function (url, opts) {
    const u = String(url);
    calls.push({ url: u, opts: opts || null });
    const q = u.indexOf('?') >= 0 ? u.slice(u.indexOf('?') + 1) : '';
    const eqs = [];
    let select = null;
    q.split('&').forEach(function (part) {
      const m = part.match(/^([a-z0-9_]+)=eq\.(.*)$/);
      if (m) { eqs.push([m[1], decodeURIComponent(m[2])]); return; }
      const s = part.match(/^select=(.*)$/);
      if (s) select = decodeURIComponent(s[1]).split(',').map(function (x) { return x.trim(); });
    });
    if (/_employee_auth\?/.test(u)) {
      const forHash = (eqs.filter(function (kv) { return kv[0] === 'license_hash'; })[0] || [])[1];
      return { ok: true, status: 200, json: async function () {
        return [{ license_hash: forHash || HASH_A, employee_id: 'emp-1',
                  role: 'owner', active: true }]; } };
    }
    if (opts && opts.method === 'POST') {
      const sent = JSON.parse(opts.body);
      return { ok: true, status: 200, text: async function () { return opts.body; },
               json: async function () { return [sent]; } };
    }
    if (opts && opts.method === 'PATCH') {
      return { ok: true, status: 200, json: async function () { return [{ data: {} }]; } };
    }
    const matches = rows.filter(function (r) {
      return eqs.every(function (kv) { return String(r[kv[0]]) === kv[1]; });
    }).map(function (r) {
      if (!select || select.indexOf('*') !== -1) return r;
      const out = {};
      select.forEach(function (c) { if (c in r) out[c] = r[c]; });
      return out;
    });
    return { ok: true, status: 200, json: async function () { return matches; } };
  };
}

// Fresh per call, with the REAL api/_lib/auth: the licence-hash half of the
// tenant boundary lives inside verifySessionToken.
function loadHandler(licHash, app, fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: licHash,
                 trial_ends_at: null, stripe_subscription_id: null, app_id: app };
      }
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

function mockReq(body, licHash, app, role, employeeId) {
  return {
    method: 'POST',
    headers: {
      authorization: 'Bearer KEY-FOR-' + licHash,
      'x-sd-auth': signSessionToken({ app: app, employee_id: employeeId || 'emp-1',
                                      role: role, license_hash: licHash })
    },
    body: body
  };
}

async function call(unit, licHash, body, rows) {
  const [, , app, role] = unit;
  const calls = [];
  const h = loadHandler(licHash, app, postgrestMock(rows || [], calls));
  const res = mockRes();
  await h(mockReq(body, licHash, app, role), res);
  return { res: res, calls: calls };
}

const UNREACHED = [];
function reached(res, what) {
  if (res.statusCode !== 200) {
    UNREACHED.push([what, res.statusCode,
                    (res.body && res.body.error && res.body.error.code) || '']);
    assert.fail('UNREACHED: ' + what + ' answered ' + res.statusCode + ' '
      + JSON.stringify(res.body) + ' -- this arm never reached the tenant filter, '
      + 'so it proves nothing about isolation. Fix the fixture, do not relax the '
      + 'assertion.');
  }
}
function firstPost(calls) {
  return calls.filter(function (c) { return c.opts && c.opts.method === 'POST'; })[0];
}
function tenantsIn(res) {
  return ((res.body && res.body.data) || [])
    .map(function (r) { return r && r.tenant; })
    .sort();
}

// ── THE FIXTURES ──────────────────────────────────────────────────────────
// Each row is in the shape its branch's SELECT asks for, and every one
// carries the tenant marker inside `data` -- the only field that survives all
// five of these projections. The READ payloads are the minimum each branch
// needs before it will issue a query at all: rf_proposals is per JOB and
// refuses without one, and that job id is deliberately the SAME in both
// tenants, because a shared scoping key is exactly what makes a dropped
// tenant filter return a plausible answer rather than an empty one.
const READ = {
  dnt_appointments: { payload: {} },
  law_matters: { payload: {} },
  rf_draws: { payload: {} },
  rf_proposals: { payload: { job_id: 'J-1' } },
  rf_supplier_documents: { payload: {} }
};
function seed(resource, licHash, id, tenant) {
  const base = { license_hash: licHash, data: { tenant: tenant } };
  if (resource === 'dnt_appointments') {
    return Object.assign(base, { appointment_id: id, provider_id: 'PR-1' });
  }
  if (resource === 'law_matters') {
    return Object.assign(base, { matter_id: id });
  }
  if (resource === 'rf_draws') {
    return Object.assign(base, { draw_id: id, job_id: 'J-1', draw_no: 1,
      period_end: '2026-06-30', pct_complete: 50, amount: 1000,
      retainage_pct: 10, status: 'requested' });
  }
  if (resource === 'rf_proposals') {
    return Object.assign(base, { proposal_id: id, job_id: 'J-1',
      event_type: 'issued', supersedes: null, recorded_by: 'emp-1',
      created_at: '2026-09-01T00:00:00.000Z' });
  }
  // rf_supplier_documents' SELECT has NO `data` column at all -- its payload
  // is `lines`, `notes`, `supplier_ref`. So neither `data.tenant` nor a
  // top-level `tenant` survives its projection, and the marker has to live in
  // a column the query actually asks for. Found by the arm coming back []
  // rather than by reading the select list, which is the mock honouring
  // `select=` doing its job.
  return Object.assign(base, { document_id: id, doc_type: 'invoice',
    po_number: 'PO-1', supplier: 'A Supplier', supplier_ref: tenant,
    created_at: '2026-09-01T00:00:00.000Z' });
}
// The two branches that hand rows straight through rather than spreading
// `data` need the marker at the TOP level, so seed() puts it in both places
// for those and tenantsIn() reads whichever survived.
// WHICH FIELD CARRIES THE MARKER IS PER RESOURCE, and it is stated rather
// than sniffed. Each of these five projects differently -- two hand back
// `x.data`, one spreads the whole row, one spreads `x.data` and re-adds
// columns, and rf_supplier_documents projects to a named column list with no
// `data` column in it at all. A markers() that guessed would quietly read
// `undefined` from a resource whose shape changed and compare [] against [],
// which is the absence-only failure this suite exists to avoid.
const MARKER = {
  dnt_appointments: function (x) { return x && x.tenant; },
  law_matters: function (x) { return x && x.tenant; },
  // rf_draws spreads the WHOLE ROW, so the marker survives -- but only
  // inside `data`, because drawSelect has no column called `tenant` and the
  // mock honours select=. Found by the arm failing, not by reading the
  // select list.
  rf_draws: function (x) { return x && x.data && x.data.tenant; },
  rf_proposals: function (x) { return x && x.tenant; },
  rf_supplier_documents: function (x) { return x && x.supplier_ref; }
};
function markers(res, resource) {
  const of = MARKER[resource];
  assert.ok(of, 'no marker extractor configured for ' + resource);
  return ((res.body && res.body.data) || []).map(of).filter(Boolean).sort();
}

// The minimum payload each WRITE needs to get past its own front door to the
// line under test. Nothing here weakens an isolation assertion -- an arm that
// cannot get through is reported UNREACHED rather than passed.
const WRITE = {
  dnt_appointments: { id: 'AP-B', patient_id: 'P-1', provider_id: 'PR-1',
                      starts_at: '2026-10-01T09:00:00.000Z' },
  law_matters: { id: 'M-B', matter_id: 'M-B', client_id: 'CL-1', name: 'A Matter' },
  rf_draws: { id: 'DR-B', draw_id: 'DR-B', job_id: 'J-1', draw_no: 1,
              period_end: '2026-06-30', pct_complete: 50, amount: 1000,
              retainage_pct: 10 },
  rf_proposals: { id: 'PP-B', job_id: 'J-1', event_type: 'issued',
                  issued_on: '2026-09-01',
                  line_items: [{ description: 'A line', amount: 100 }] },
  rf_supplier_documents: { document_id: 'SD-B', doc_type: 'invoice',
                           po_number: 'PO-1', supplier: 'A Supplier',
                           doc_date: '2026-09-01',
                           lines: [{ item_code: 'X', description: 'A line',
                                     qty: 1, unit_price: 10 }] }
};
// Which of the two write shapes each resource has. Stated per resource rather
// than sniffed from the response, so a branch that CHANGES shape breaks this
// table loudly instead of silently taking the other assertion.
const CONFLICT_KEY = {
  dnt_appointments: 'on_conflict=license_hash,appointment_id',
  law_matters: 'on_conflict=license_hash,matter_id',
  rf_draws: 'on_conflict=license_hash,draw_id'
};

(async function () {
  console.log('CROSS-TENANT ISOLATION -- the last five WEAK bespoke branches');

  for (const unit of UNITS) {
    const [resource, , app, role] = unit;
    section(resource + '  (' + app + ', role ' + role + ')');

    await test(resource + ' [L] tenant A sees ONLY tenant A rows', async () => {
      const rows = [seed(resource, HASH_A, 'A-1', 'A'),
                    seed(resource, HASH_B, 'B-1', 'B')];
      const { res, calls } = await call(unit, HASH_A,
        Object.assign({ action: 'read', resource: resource }, READ[resource]), rows);
      reached(res, 'the tenant A ' + resource + ' read');
      assert.deepStrictEqual(markers(res, resource), ['A'],
        'tenant A read returned ' + JSON.stringify(markers(res, resource)) + ' -- anything '
        + 'other than exactly ["A"] means the license_hash filter is absent, '
        + 'ANDed wrong, or the rows returned are not the rows it filtered');
      assert.ok(calls.some(function (c) {
        return c.url.indexOf(resource + '?license_hash=eq.' + HASH_A) !== -1; }),
        'no query carried ' + resource + '?license_hash=eq.' + HASH_A + ': '
        + JSON.stringify(calls.map(function (c) { return c.url; })));
    });

    await test(resource + ' [L-rev] tenant B sees ONLY tenant B rows', async () => {
      // A handler hardcoded to one tenant passes every A-only arm and fails here.
      const rows = [seed(resource, HASH_A, 'A-1', 'A'),
                    seed(resource, HASH_B, 'B-1', 'B')];
      const { res } = await call(unit, HASH_B,
        Object.assign({ action: 'read', resource: resource }, READ[resource]), rows);
      reached(res, 'the tenant B ' + resource + ' read');
      assert.deepStrictEqual(markers(res, resource), ['B'],
        'tenant B read returned ' + JSON.stringify(markers(res, resource)));
    });

    await test(resource + ' [W] A writing B\'s id lands under A, not B', async () => {
      const { res, calls } = await call(unit, HASH_A,
        { action: 'write', resource: resource, payload: WRITE[resource] },
        [seed(resource, HASH_A, 'A-1', 'A')]);
      const post = firstPost(calls);
      if (!post) {
        UNREACHED.push([resource + ' write', res.statusCode,
                        (res.body && res.body.error && res.body.error.code) || '']);
        assert.fail('UNREACHED: no insert or upsert was sent; the handler answered '
          + res.statusCode + ' ' + JSON.stringify(res.body) + '. This arm never '
          + 'reached the write, so it proves nothing.');
      }
      const key = CONFLICT_KEY[resource];
      if (key) {
        assert.ok(post.url.indexOf(key) !== -1,
          'the upsert conflict key is not ' + key + ': ' + post.url
          + ' -- drop license_hash from it and tenant A overwrites tenant B');
      } else {
        // APPEND-ONLY: there is no conflict key, so the assertion is that
        // there is no UPSERT either. If one ever appears without license_hash
        // in its key, this arm has to be rewritten rather than quietly passing
        // on the body check alone.
        assert.ok(post.url.indexOf('on_conflict=') === -1,
          resource + ' grew a conflict key (' + post.url + ') and this arm still '
          + 'only checks the body. Re-read the branch: an upsert keyed without '
          + 'license_hash is a cross-tenant overwrite this assertion cannot see.');
      }
      const sent = JSON.parse(post.opts.body);
      assert.strictEqual(sent.license_hash, HASH_A,
        'the row was written under ' + JSON.stringify(sent.license_hash)
        + ' rather than the hash the handler derived from the bearer key');
    });

    await test(resource + ' [Winj] a payload license_hash does not move the row',
      async () => {
        const { res, calls } = await call(unit, HASH_A,
          { action: 'write', resource: resource,
            payload: Object.assign({}, WRITE[resource],
              { license_hash: HASH_B, app_id: 'sairnbiz' }) },
          [seed(resource, HASH_A, 'A-1', 'A')]);
        const post = firstPost(calls);
        if (!post) {
          assert.fail('UNREACHED: nothing was written; handler answered '
            + res.statusCode + ' ' + JSON.stringify(res.body));
        }
        assert.strictEqual(JSON.parse(post.opts.body).license_hash, HASH_A,
          'a license_hash INSIDE the payload reached the stored row');
      });

    await test(resource + ' [S] tenant B\'s token against tenant A\'s licence is '
      + 'refused', async () => {
        const calls = [];
        const h = loadHandler(HASH_A, app, postgrestMock(
          [seed(resource, HASH_A, 'A-1', 'A')], calls));
        const res = mockRes();
        await h({ method: 'POST',
                  headers: { authorization: 'Bearer KEY-FOR-' + HASH_A,
                             'x-sd-auth': signSessionToken({
                               app: app, employee_id: 'emp-9', role: role,
                               license_hash: HASH_B }) },
                  body: Object.assign({ action: 'read', resource: resource },
                                      READ[resource]) }, res);
        assert.ok(res.statusCode === 401 || res.statusCode === 403,
          'a session signed for ' + HASH_B + ' was accepted against ' + HASH_A
          + ': ' + res.statusCode + ' ' + JSON.stringify(res.body));
        assert.ok(!calls.some(function (c) { return c.url.indexOf(resource) !== -1; }),
          'the refused request still queried ' + resource);
      });

    await test(resource + ' [S] a ' + unit[4] + ' token for the same tenant is '
      + 'refused', async () => {
        // Guardian Check 28's collision: without the expected-app argument a
        // genuine session for another SAIRN app under the same licence would
        // reach this branch.
        const calls = [];
        const h = loadHandler(HASH_A, app, postgrestMock(
          [seed(resource, HASH_A, 'A-1', 'A')], calls));
        const res = mockRes();
        await h({ method: 'POST',
                  headers: { authorization: 'Bearer KEY-FOR-' + HASH_A,
                             'x-sd-auth': signSessionToken({
                               app: unit[4], employee_id: 'emp-1', role: 'owner',
                               license_hash: HASH_A }) },
                  body: Object.assign({ action: 'read', resource: resource },
                                      READ[resource]) }, res);
        assert.ok(res.statusCode === 401 || res.statusCode === 403,
          'a ' + unit[4] + ' session reached ' + app + '\'s ' + resource + ': '
          + res.statusCode + ' ' + JSON.stringify(res.body));
      });
  }

  // ── THE NEGATIVE CONTROL ON THE MOCK ITSELF ─────────────────────────────
  section('THE NEGATIVE CONTROL -- the mock still distinguishes filtered from '
    + 'unfiltered, ANDs its clauses, and projects');
  await test('an unfiltered query returns BOTH tenants', async () => {
    const rows = [seed('law_matters', HASH_A, 'A-1', 'A'),
                  seed('law_matters', HASH_B, 'B-1', 'B')];
    const f = postgrestMock(rows, []);
    const unfiltered = await (await f('https://x/rest/v1/law_matters')).json();
    assert.strictEqual(unfiltered.length, 2,
      'the mock returned ' + unfiltered.length + ' rows for a query with NO eq. '
      + 'clauses. It is not filtering, so every arm above proves nothing.');
    const filtered = await (await f('https://x/rest/v1/law_matters?license_hash=eq.'
      + HASH_A)).json();
    assert.strictEqual(filtered.length, 1);
    const both = await (await f('https://x/rest/v1/law_matters?license_hash=eq.'
      + HASH_A + '&matter_id=eq.B-1')).json();
    assert.strictEqual(both.length, 0,
      'two eq. clauses must be ANDed: A\'s hash with B\'s id matches nothing');
  });

  await test('the mock honours select=', async () => {
    const f = postgrestMock([seed('rf_draws', HASH_A, 'A-1', 'A')], []);
    const projected = await (await f('https://x/rest/v1/rf_draws?license_hash=eq.'
      + HASH_A + '&select=draw_id,data')).json();
    assert.deepStrictEqual(Object.keys(projected[0]).sort(), ['data', 'draw_id'],
      'the mock ignored select= and returned '
      + JSON.stringify(Object.keys(projected[0])));
  });

  if (UNREACHED.length) {
    console.log('\nUNREACHED -- arms that never got to the tenant filter:');
    UNREACHED.forEach(function (u) { console.log('  %s -> %s %s', u[0], u[1], u[2]); });
    console.log('These are NOT isolation failures and NOT passes.');
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
