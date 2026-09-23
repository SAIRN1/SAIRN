// api/sd-data-bld-tna-isolation.test.js
//
// REQUIREMENT: a valid, fully authenticated SAIRNbuild session for tenant A
//   cannot read or overwrite tenant B's training-needs assessments.
//
// CROSS-TENANT-ISOLATION: bld_tna
//
// Run:  node api/sd-data-bld-tna-isolation.test.js
//
// ── WHY THIS IS ITS OWN FILE AND NOT A ROW IN THE DISPATCHER SUITE ─────────
// api/sd-data-cross-tenant-dispatchers.test.js drives 150+ resources through
// one shared harness, and its [L] arm is built on a shape bld_tna does not
// have. FOUR STRUCTURAL DIFFERENCES, each of which breaks that arm on its own:
//
//   1. THE TABLE IS NOT THE RESOURCE. Every generic-dispatcher member queries
//      `rest(resource + '?...')`. bld_tna queries `bld_tna_assessments`. The
//      shared arm cannot even name the table it is asserting about.
//   2. THERE IS NO `data` COLUMN. The shared fixture seeds
//      `{license_hash, <idCol>, owner, data:{...}}` and reads `x.owner` back
//      off each returned row. This branch SELECTS a named column list and
//      re-projects it, so `owner` is not selected, not returned, and not
//      present -- the shared assertion would compare `[undefined]` against
//      `['A']` and fail for a reason that has nothing to do with tenancy.
//   3. THE KEY IS COMPOSITE. `on_conflict=license_hash,subject_employee_id,
//      perspective`. The shared [W] arm's model is one `idCol` and cannot
//      express a two-column business key.
//   4. A SECOND FILTER RUNS AFTER THE QUERY, IN MEMORY. For a caller outside
//      BLD_TNA_MANAGEMENT_ROLES the handler filters the fetched rows down to
//      `subject_employee_id === session.employee_id`. That filter can make a
//      one-row answer look correct while the tenant filter is missing, which
//      is the arm at the bottom of this file and the reason it exists.
//
// TEACHING THE SHARED ARM AN EXCEPTION FOR THIS ONE RESOURCE WAS REJECTED.
// The exception would have to make `owner`, the table name and the id column
// all optional, and every one of those three is load-bearing for the other
// 150+ members: a member whose fixture stops carrying `owner` yields `[]`,
// and an absence-only assertion passes `[]` for entirely the wrong reason.
// Weakening the arm that covers 150 resources to fit one is the wrong trade,
// so this resource pays for its own.
//
// ── THE ARM THAT ONLY EXISTS HERE ─────────────────────────────────────────
// EMPLOYEE IDS ARE PER TENANT, SO THEY COLLIDE. Both tenants have an `emp-1`.
// A non-management caller's answer is narrowed by `subject_employee_id ===
// session.employee_id` AFTER the fetch, so if the license_hash filter were
// dropped from the query, tenant A's `emp-1` would be handed tenant B's
// `emp-1` assessment -- one row, correctly shaped, plausibly their own, and
// belonging to another company's employee. No count assertion and no shape
// assertion can see that. The fixtures carry a tenant marker inside
// `responses` so the assertion is about WHOSE row came back.
//
// ── WHAT THIS DOES NOT DO ─────────────────────────────────────────────────
// It does not test the DATABASE, and it does not test the bld_tna PRIVACY
// gate (who may write a 'self' row, who may write a 'management' row). That
// gate is a separate question from tenancy and is not asserted here; the only
// thing these arms are about is whether tenant A can reach tenant B's rows.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['bld', 'tna', 'isolation', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const { signSessionToken } = require('./_lib/auth');

const HASH_A = 'tenant-A-hash';
const HASH_B = 'tenant-B-hash';
const TABLE = 'bld_tna_assessments';

// The resource table this suite drives, in the shape
// tools/cross_tenant_isolation_scope.py cross-checks a declaration against.
// `managementRole` is in BLD_TNA_MANAGEMENT_ROLES and `memberRole` is not --
// both are real ROLES_BY_APP.sairnbuild roles, not invented ones.
const UNITS = [
  { map: 'bld_tna (bespoke, composite key, subject-narrowed)',
    app: 'sairnbuild', managementRole: 'owner', memberRole: 'pm',
    members: [['bld_tna', 'subject_employee_id', 'perspective']] }
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
// `license_hash=eq.` from the handler's query and the mock has nothing left
// to filter on, returns both tenants' rows, and the content assertions fail.
//
// TRANSPLANTED FROM api/sd-data-cross-tenant-dispatchers.test.js AND
// RE-QUALIFIED RATHER THAN COPIED, because byte-identical is not
// safe-in-context. Two differences were forced by this branch:
//
//   * IT HONOURS `select=`. The real query asks for eight named columns and
//     PostgREST returns those and nothing else. The shared mock returns whole
//     rows, which would hand this handler a `license_hash` column the real
//     database never sends it -- and the last assertion in the [L] arm is
//     that no license_hash reaches the response body. Asserting that against
//     a mock that could not have supplied one would be asserting nothing.
//   * THE 404/400 PROVISIONING BRANCH IS NEVER TAKEN. This mock always
//     answers 200, so `provisioned: false` cannot be the reason an arm looks
//     empty. An arm that came back empty because the table "does not exist"
//     would read exactly like isolation working.
//
// EVERY WAY IT IS UNFAITHFUL RUNS IN THE SAFE DIRECTION: an unrecognised
// clause is simply not applied, so the mock returns MORE rows than PostgREST
// would and the content assertion fails LOUDER. No query shape makes it
// return FEWER rows. The negative control at the bottom drives that both
// ways rather than asserting it in prose.
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
    // A credential lookup is not the query under test. bld_tna is not in
    // SD_SESSION_GATED today so this branch is not reached, and it is here
    // ANSWERED FOR THE TENANT IN THE QUERY rather than unconditionally, so
    // that if the resource is ever gated this stays a tenant-scoped answer
    // instead of becoming a hole in the suite that gated it.
    if (/_employee_auth\?/.test(u)) {
      const forHash = (eqs.filter(function (kv) { return kv[0] === 'license_hash'; })[0] || [])[1];
      return { ok: true, status: 200, json: async function () {
        return [{ license_hash: forHash || HASH_A, employee_id: 'emp-1',
                  role: 'owner', active: true }]; } };
    }
    if (opts && opts.method === 'POST') {
      const sent = JSON.parse(opts.body);
      return { ok: true, status: 200, json: async function () { return [sent]; } };
    }
    const matches = rows.filter(function (r) {
      return eqs.every(function (kv) { return String(r[kv[0]]) === kv[1]; });
    }).map(function (r) {
      if (!select) return r;
      const out = {};
      select.forEach(function (c) { if (c in r) out[c] = r[c]; });
      return out;
    });
    return { ok: true, status: 200, json: async function () { return matches; } };
  };
}

// Fresh per call. The handler caches nothing across requires, and a stale
// module would carry the previous tenant's licence stub into the next arm.
// _lib/auth is deliberately NOT stubbed: the tenant boundary on the session
// half lives inside verifySessionToken, and stubbing it away is exactly how
// api/sd-data-exec-context.test.js ended up asserting a role gate while
// asserting nothing at all about which tenant the session belonged to.
function loadHandler(licHash, fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: licHash,
                 trial_ends_at: null, stripe_subscription_id: null, app_id: 'sairnbuild' };
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
function mockReq(body, licHash, employeeId, role) {
  return {
    method: 'POST',
    headers: {
      authorization: 'Bearer KEY-FOR-' + licHash,
      'x-sd-auth': signSessionToken({ app: 'sairnbuild', employee_id: employeeId,
                                      role: role, license_hash: licHash })
    },
    body: body
  };
}

// A row in the shape the SELECT actually asks for. `responses` carries the
// tenant marker, because the two tenants' rows deliberately share a
// subject_employee_id in the collision arm and nothing else would tell them
// apart.
function row(licHash, subject, perspective, tenant) {
  return {
    license_hash: licHash,
    subject_employee_id: subject,
    perspective: perspective,
    assessor_employee_id: subject,
    responses: { tenant: tenant, q1: 4 },
    disc_responses: null,
    disc_profile: null,
    submitted_at: '2026-09-01T00:00:00.000Z',
    updated_at: '2026-09-01T00:00:00.000Z'
  };
}

function tenantsIn(res) {
  return ((res.body && res.body.data) || [])
    .map(function (r) { return r && r.responses && r.responses.tenant; })
    .sort();
}

async function read(licHash, employeeId, role, rows) {
  const calls = [];
  const h = loadHandler(licHash, postgrestMock(rows, calls));
  const res = mockRes();
  await h(mockReq({ action: 'read', resource: 'bld_tna' }, licHash, employeeId, role), res);
  return { res: res, calls: calls };
}

// An arm that could not reach the code it is about reports UNREACHED, never
// pass and never fail-as-isolation.
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

(async function () {
  const unit = UNITS[0];
  console.log('CROSS-TENANT ISOLATION -- ' + unit.map);

  section('READ -- a management caller, where the ONLY thing that can narrow the '
    + 'answer is license_hash');

  await test('bld_tna [L] tenant A sees ONLY tenant A rows', async () => {
    const rows = [
      row(HASH_A, 'emp-A1', 'self', 'A'),
      row(HASH_A, 'emp-A2', 'management', 'A'),
      row(HASH_B, 'emp-B1', 'self', 'B')
    ];
    const { res, calls } = await read(HASH_A, 'emp-A1', unit.managementRole, rows);
    reached(res, 'the tenant A management read');
    assert.deepStrictEqual(tenantsIn(res), ['A', 'A'],
      'tenant A read returned ' + JSON.stringify(tenantsIn(res)) + ' -- anything '
      + 'other than exactly ["A","A"] means the license_hash filter is absent, '
      + 'ANDed wrong, or the rows returned are not the rows it filtered');
    // A's rows are PRESENT, not merely B's absent: a filter on a column the
    // fixtures do not carry matches nothing and yields [], which an
    // absence-only assertion would pass for entirely the wrong reason.
    assert.deepStrictEqual(
      res.body.data.map(function (r) { return r.id; }).sort(),
      ['emp-A1:self', 'emp-A2:management'],
      'the projected ids are not A\'s two rows');
    assert.ok(calls.some(function (c) {
      return c.url.indexOf(TABLE + '?license_hash=eq.' + HASH_A) !== -1; }),
      'no query carried ' + TABLE + '?license_hash=eq.' + HASH_A + ': '
      + JSON.stringify(calls.map(function (c) { return c.url; })));
  });

  await test('bld_tna [L-rev] tenant B sees ONLY tenant B rows', async () => {
    // A handler hardcoded to one tenant passes every A-only arm above.
    const rows = [
      row(HASH_A, 'emp-A1', 'self', 'A'),
      row(HASH_B, 'emp-B1', 'self', 'B')
    ];
    const { res } = await read(HASH_B, 'emp-B1', unit.managementRole, rows);
    reached(res, 'the tenant B management read');
    assert.deepStrictEqual(tenantsIn(res), ['B'],
      'tenant B read returned ' + JSON.stringify(tenantsIn(res)) + '. BOTH '
      + 'DIRECTIONS ARE DRIVEN DELIBERATELY: a handler hardcoded to one tenant '
      + 'passes the A-only arm above and fails here.');
  });

  await test('bld_tna [L] no license_hash reaches the response body', async () => {
    // The named SELECT is what strips it. If somebody widens that select to
    // `*` or passes rows through unprojected, the tenant key of every row
    // starts being served to the browser.
    const { res } = await read(HASH_A, 'emp-A1', unit.managementRole,
      [row(HASH_A, 'emp-A1', 'self', 'A')]);
    reached(res, 'the projection read');
    assert.ok(JSON.stringify(res.body).indexOf('license_hash') === -1,
      'the response body carries a license_hash: ' + JSON.stringify(res.body));
  });

  section('READ -- the arm the shared harness cannot express: TWO TENANTS WITH '
    + 'THE SAME EMPLOYEE ID');

  await test('bld_tna [L-collide] a non-management caller gets THEIR OWN emp-1 row, '
    + 'not the other tenant\'s emp-1 row', async () => {
    // Employee ids are per tenant, so both companies have an emp-1. For a
    // caller outside BLD_TNA_MANAGEMENT_ROLES the answer is narrowed to
    // subject_employee_id === session.employee_id AFTER the fetch. Drop the
    // license_hash filter and this caller is handed another company's
    // employee's assessment: one row, correctly shaped, plausibly their own.
    const rows = [
      row(HASH_A, 'emp-1', 'self', 'A'),
      row(HASH_B, 'emp-1', 'self', 'B'),
      row(HASH_B, 'emp-1', 'management', 'B')
    ];
    const { res } = await read(HASH_A, 'emp-1', unit.memberRole, rows);
    reached(res, 'the tenant A non-management read');
    assert.deepStrictEqual(tenantsIn(res), ['A'],
      'the caller was handed ' + JSON.stringify(tenantsIn(res)) + '. A count or a '
      + 'shape assertion cannot see this failure -- both tenants\' rows are the '
      + 'same employee id in the same shape, and only the tenant marker inside '
      + 'responses tells them apart.');
  });

  await test('bld_tna [L-collide-rev] and the same caller in tenant B gets B\'s',
    async () => {
      const rows = [
        row(HASH_A, 'emp-1', 'self', 'A'),
        row(HASH_B, 'emp-1', 'self', 'B')
      ];
      const { res } = await read(HASH_B, 'emp-1', unit.memberRole, rows);
      reached(res, 'the tenant B non-management read');
      assert.deepStrictEqual(tenantsIn(res), ['B'],
        'tenant B\'s emp-1 was handed ' + JSON.stringify(tenantsIn(res)));
    });

  section('WRITE -- the composite conflict key');

  await test('bld_tna [W] A assessing an employee id that exists in B lands under A',
    async () => {
      const calls = [];
      const h = loadHandler(HASH_A, postgrestMock([], calls));
      const res = mockRes();
      await h(mockReq({ action: 'write', resource: 'bld_tna',
                        payload: { subject_employee_id: 'emp-B1',
                                   perspective: 'management',
                                   responses: { tenant: 'A', q1: 2 } } },
                      HASH_A, 'emp-A1', unit.managementRole), res);
      const post = calls.filter(function (c) { return c.opts && c.opts.method === 'POST'; })[0];
      if (!post) {
        UNREACHED.push(['bld_tna write', res.statusCode,
                        (res.body && res.body.error && res.body.error.code) || '']);
        assert.fail('UNREACHED: no upsert was sent; the handler answered '
          + res.statusCode + ' ' + JSON.stringify(res.body) + '. This arm never '
          + 'reached the conflict key, so it proves nothing.');
      }
      // THE KEY IS COMPOSITE AND ALL THREE COLUMNS MATTER. Drop license_hash
      // and tenant A's management assessment of its own emp-B1 REPLACES the
      // other company's row for the same id and perspective, with a normal
      // 200 either way.
      assert.ok(post.url.indexOf(
        'on_conflict=license_hash,subject_employee_id,perspective') !== -1,
        'the upsert conflict key is not license_hash,subject_employee_id,'
        + 'perspective: ' + post.url + ' -- drop license_hash from it and tenant '
        + 'A overwrites tenant B\'s row for the same employee id');
      const sent = JSON.parse(post.opts.body);
      assert.strictEqual(sent.license_hash, HASH_A,
        'the row was written under ' + JSON.stringify(sent.license_hash)
        + ' rather than the hash the handler derived from the bearer key');
      assert.strictEqual(sent.assessor_employee_id, 'emp-A1',
        'the assessor was taken from the payload rather than the verified session');
    });

  await test('bld_tna [Winj] a payload license_hash does not move the row', async () => {
    const calls = [];
    const h = loadHandler(HASH_A, postgrestMock([], calls));
    const res = mockRes();
    await h(mockReq({ action: 'write', resource: 'bld_tna',
                      payload: { subject_employee_id: 'emp-A1', perspective: 'self',
                                 license_hash: HASH_B, app_id: 'sairnbiz',
                                 responses: { tenant: 'A' } } },
                    HASH_A, 'emp-A1', unit.managementRole), res);
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
    assert.strictEqual(sent.app_id, 'sairnbuild',
      'an app_id INSIDE the payload reached the stored row as '
      + JSON.stringify(sent.app_id));
  });

  section('THE SESSION HALF -- a token minted for the other tenant');

  await test('bld_tna [S] tenant B\'s token against tenant A\'s licence is refused',
    async () => {
      // verifySessionToken checks the token's license_hash against the one the
      // handler derived from the bearer key. This is the OTHER half of the
      // tenant boundary and the fetch-mock arms above cannot see it: they sign
      // every token correctly by construction.
      const calls = [];
      const h = loadHandler(HASH_A, postgrestMock(
        [row(HASH_A, 'emp-A1', 'self', 'A')], calls));
      const res = mockRes();
      await h({ method: 'POST',
                headers: { authorization: 'Bearer KEY-FOR-' + HASH_A,
                           'x-sd-auth': signSessionToken({
                             app: 'sairnbuild', employee_id: 'emp-B1',
                             role: 'owner', license_hash: HASH_B }) },
                body: { action: 'read', resource: 'bld_tna' } }, res);
      assert.strictEqual(res.statusCode, 401,
        'a session signed for ' + HASH_B + ' was accepted against ' + HASH_A
        + ': ' + res.statusCode + ' ' + JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'NO_SESSION');
      assert.ok(!calls.some(function (c) { return c.url.indexOf(TABLE) !== -1; }),
        'the refused request still queried ' + TABLE);
    });

  await test('bld_tna [S] a SAIRNbiz token for the same tenant is refused', async () => {
    // Guardian Check 28's collision: without the third argument to
    // verifySessionToken, a genuine session for another SAIRN app under the
    // same licence would reach this branch.
    const calls = [];
    const h = loadHandler(HASH_A, postgrestMock(
      [row(HASH_A, 'emp-A1', 'self', 'A')], calls));
    const res = mockRes();
    await h({ method: 'POST',
              headers: { authorization: 'Bearer KEY-FOR-' + HASH_A,
                         'x-sd-auth': signSessionToken({
                           app: 'sairnbiz', employee_id: 'emp-A1',
                           role: 'owner', license_hash: HASH_A }) },
              body: { action: 'read', resource: 'bld_tna' } }, res);
    assert.strictEqual(res.statusCode, 401,
      'a SAIRNbiz session reached SAIRNbuild\'s assessments: ' + res.statusCode
      + ' ' + JSON.stringify(res.body));
    assert.ok(!calls.some(function (c) { return c.url.indexOf(TABLE) !== -1; }),
      'the refused request still queried ' + TABLE);
  });

  // ── THE NEGATIVE CONTROL ON THE MOCK ITSELF ─────────────────────────────
  section('THE NEGATIVE CONTROL -- the mock still distinguishes filtered from '
    + 'unfiltered, and still projects');
  await test('an unfiltered query returns BOTH tenants', async () => {
    const rows = [row(HASH_A, 'emp-1', 'self', 'A'), row(HASH_B, 'emp-1', 'self', 'B')];
    const f = postgrestMock(rows, []);
    const unfiltered = await (await f('https://x/rest/v1/' + TABLE)).json();
    assert.strictEqual(unfiltered.length, 2,
      'the mock returned ' + unfiltered.length + ' rows for a query with NO eq. '
      + 'clauses. It is not filtering, so every arm above proves nothing.');
    const filtered = await (await f('https://x/rest/v1/' + TABLE
      + '?license_hash=eq.' + HASH_A)).json();
    assert.strictEqual(filtered.length, 1,
      'the mock returned ' + filtered.length + ' rows for a filtered query');
    const both = await (await f('https://x/rest/v1/' + TABLE + '?license_hash=eq.'
      + HASH_A + '&subject_employee_id=eq.emp-9')).json();
    assert.strictEqual(both.length, 0,
      'two eq. clauses must be ANDed: A\'s hash with an absent subject matches nothing');
  });

  await test('the mock honours select= -- so the projection assertion is real', async () => {
    const f = postgrestMock([row(HASH_A, 'emp-1', 'self', 'A')], []);
    const projected = await (await f('https://x/rest/v1/' + TABLE + '?license_hash=eq.'
      + HASH_A + '&select=subject_employee_id,perspective')).json();
    assert.deepStrictEqual(Object.keys(projected[0]).sort(),
      ['perspective', 'subject_employee_id'],
      'the mock ignored select= and returned ' + JSON.stringify(Object.keys(projected[0]))
      + '. The "no license_hash in the body" arm would then be asserting that the '
      + 'handler drops a column the mock never sent, which is not the claim.');
  });

  if (UNREACHED.length) {
    console.log('\nUNREACHED -- arms that never got to the tenant filter:');
    UNREACHED.forEach(function (u) { console.log('  %s -> %s %s', u[0], u[1], u[2]); });
    console.log('These are NOT isolation failures and NOT passes.');
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
