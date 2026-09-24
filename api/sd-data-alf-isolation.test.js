// api/sd-data-alf-isolation.test.js
//
// REQUIREMENT: a valid, fully authenticated SAIRNcare session for facility A
//   cannot read or overwrite facility B's residents, facility record, or
//   medication administration records.
//
// CROSS-TENANT-ISOLATION: alf_clients, alf_facility, alf_mar
//
// Run:  node api/sd-data-alf-isolation.test.js
//
// ── WHY A NEW FILE ────────────────────────────────────────────────────────
// All three graded WEAK, and the reason the grader gave for each was the same
// shape: the only suites naming them exercise no tenant boundary at all --
// tests/phi_cache_scoped_to_user.js, api/alf-append-only-fail-closed.test.js,
// tests/cron_schedules_do_not_collide.js. Those are good tests about other
// questions. WEAK is the more dangerous of the two empty states because it
// reads as partial coverage.
//
// They are also not rows the dispatcher suite can take: each is a bespoke
// branch, alf_mar's write goes through a stored procedure with no conflict
// key at all, and api/sd-data-cross-tenant-dispatchers.test.js is under
// another session's active claim while this lands.
//
// ── THE COLLISION SHAPE, TWICE, AND ONE OF THEM IS THE SHARPEST ON THE
// ── PLATFORM ─────────────────────────────────────────────────────────────
// alf_clients and alf_mar BOTH narrow their answer in memory after the query,
// to `assigned_employee_id === session.employee_id`, for any role outside
// their broad set. Employee ids are per tenant, so two facilities both have
// an `emp-1`.
//
// For alf_clients that means a caregiver is handed another facility's
// resident. For alf_mar it means a med aide is handed another facility's
// MEDICATION ADMINISTRATION RECORD -- who was given what controlled drug, by
// whom, and when. One row, correctly shaped, assigned to "them", and it is
// another facility's resident's clinical record. No count assertion and no
// shape assertion can see that, so every read arm below asserts WHOSE row
// came back using a marker the projection preserves.
//
// ── WHAT THIS DOES NOT DO ─────────────────────────────────────────────────
// It does not test the DATABASE, and it does not test the ROLE gates --
// alf_facility redacts rate fields from non-management, alf_mar refuses
// entry types by role, and alf_clients narrows by assignment. Those are
// separate questions. `owner` is used on the arms that are not about
// narrowing precisely so that no role rule can make an arm pass for a reason
// other than license_hash.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['alf', 'isolation', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const { signSessionToken } = require('./_lib/auth');

const HASH_A = 'tenant-A-hash';
const HASH_B = 'tenant-B-hash';
const APP = 'sairncare';

// The resources this suite drives, in the shape
// tools/cross_tenant_isolation_scope.py cross-checks a declaration against.
// `broad` is a role in the branch's broad-read set, `narrow` one that is a
// real ROLES_BY_APP.sairncare role and is NOT -- which is what makes the
// collision arms possible. alf_facility has no assignment narrowing, so it
// has no narrow role and says so with null rather than a placeholder.
const UNITS = [
  ['alf_clients', 'client_id', 'owner', 'caregiver'],
  ['alf_facility', 'facility_id', 'owner', null],
  ['alf_mar', 'entry_id', 'nursing', 'med_aide']
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
// is left -- the client_id, or nothing at all -- returns the other facility's
// row, and the content assertion fails.
//
// IT HONOURS `select=`, because all three branches ask for a named column
// list and two of them read specific fields back out of it. A mock handing
// back columns the real query never asked for would be testing a row shape
// the handler cannot receive.
//
// AN RPC POST IS ANSWERED SEPARATELY AND ITS BODY IS KEPT, because alf_mar's
// write has no conflict key to assert on: the tenant binding is an ARGUMENT
// (`p_license_hash`), which is the only thing tying the inserted row to a
// facility.
//
// EVERY WAY IT IS UNFAITHFUL RUNS IN THE SAFE DIRECTION: an unrecognised
// clause is not applied, so it returns MORE rows than PostgREST would and the
// content assertion fails LOUDER. No query shape makes it return FEWER. The
// negative control at the bottom drives that rather than asserting it.
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

// Fresh per call, with the REAL api/_lib/auth -- the licence-hash half of the
// tenant boundary lives inside verifySessionToken, and a stub there answers
// yes to part of the question this file asks.
function loadHandler(licHash, fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: licHash,
                 trial_ends_at: null, stripe_subscription_id: null, app_id: APP };
      }
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

function mockReq(body, licHash, employeeId, role) {
  return {
    method: 'POST',
    headers: {
      authorization: 'Bearer KEY-FOR-' + licHash,
      'x-sd-auth': signSessionToken({ app: APP, employee_id: employeeId,
                                      role: role, license_hash: licHash })
    },
    body: body
  };
}

async function call(licHash, employeeId, role, body, rows) {
  const calls = [];
  const h = loadHandler(licHash, postgrestMock(rows || [], calls));
  const res = mockRes();
  await h(mockReq(body, licHash, employeeId, role), res);
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

// Fixtures in the shape each SELECT asks for. The tenant marker lives inside
// `data`, which is what every one of these branches spreads into its
// response -- and it is the only field that survives all three projections.
function client(licHash, clientId, assignee, tenant) {
  return { license_hash: licHash, client_id: clientId,
           assigned_employee_id: assignee,
           data: { tenant: tenant, name: 'A Resident' } };
}
function facility(licHash, facilityId, tenant) {
  return { license_hash: licHash, facility_id: facilityId,
           data: { tenant: tenant, name: 'A Facility', bed_count: 40 } };
}
function marEntry(licHash, entryId, residentId, assignee, tenant) {
  return { license_hash: licHash, entry_id: entryId, resident_id: residentId,
           assigned_employee_id: assignee, entry_type: 'administration',
           data: { tenant: tenant, drug: 'A Drug', dose: '5mg' } };
}

(async function () {
  console.log('CROSS-TENANT ISOLATION -- SAIRNcare (' + UNITS.length + ' resources, '
    + 'two of them narrowed in memory after the query)');

  // ══ alf_clients ═════════════════════════════════════════════════════════
  section('alf_clients -- TWO FACILITIES, ONE emp-1');

  await test('alf_clients [L] a broad-read role sees ONLY facility A residents',
    async () => {
      const seeded = [client(HASH_A, 'C-A', 'emp-1', 'A'),
                      client(HASH_B, 'C-B', 'emp-9', 'B')];
      const { res, calls } = await call(HASH_A, 'emp-1', 'owner',
        { action: 'read', resource: 'alf_clients' }, seeded);
      reached(res, 'the facility A broad read');
      assert.deepStrictEqual(tenantsIn(res), ['A']);
      assert.ok(calls.some(function (c) {
        return c.url.indexOf('alf_clients?license_hash=eq.' + HASH_A) !== -1; }),
        'no query carried alf_clients?license_hash=eq.' + HASH_A + ': '
        + JSON.stringify(calls.map(function (c) { return c.url; })));
    });

  await test('alf_clients [L-rev] facility B sees only its own', async () => {
    const seeded = [client(HASH_A, 'C-A', 'emp-1', 'A'),
                    client(HASH_B, 'C-B', 'emp-9', 'B')];
    const { res } = await call(HASH_B, 'emp-9', 'owner',
      { action: 'read', resource: 'alf_clients' }, seeded);
    reached(res, 'the facility B broad read');
    assert.deepStrictEqual(tenantsIn(res), ['B'],
      'a handler hardcoded to one tenant passes the arm above and fails here');
  });

  await test('alf_clients [L-collide] a CAREGIVER named emp-1 gets their own '
    + 'facility\'s resident, not the other facility\'s emp-1 resident', async () => {
      // caregiver is outside ALF_BROAD_READ_ROLES, so the handler narrows the
      // FETCHED rows to assigned_employee_id === session.employee_id AFTER the
      // query. With the tenant filter dropped this caller is handed another
      // facility's resident: one row, correctly shaped, assigned to "them".
      const seeded = [client(HASH_A, 'C-A', 'emp-1', 'A'),
                      client(HASH_B, 'C-B', 'emp-1', 'B'),
                      client(HASH_B, 'C-B2', 'emp-1', 'B')];
      const { res } = await call(HASH_A, 'emp-1', 'caregiver',
        { action: 'read', resource: 'alf_clients' }, seeded);
      reached(res, 'the facility A caregiver read');
      assert.deepStrictEqual(tenantsIn(res), ['A'],
        'the caregiver was handed ' + JSON.stringify(tenantsIn(res))
        + ' -- every one of these rows is assigned to "emp-1" and only the '
        + 'tenant marker inside data tells them apart');
    });

  await test('alf_clients [W] A writing B\'s client id lands under A', async () => {
    const { res, calls } = await call(HASH_A, 'emp-1', 'owner',
      { action: 'write', resource: 'alf_clients',
        payload: { id: 'C-B', name: 'A Resident' } }, []);
    const post = firstPost(calls);
    if (!post) {
      UNREACHED.push(['alf_clients write', res.statusCode,
                      (res.body && res.body.error && res.body.error.code) || '']);
      assert.fail('UNREACHED: no upsert was sent; handler answered ' + res.statusCode
        + ' ' + JSON.stringify(res.body));
    }
    assert.ok(post.url.indexOf('on_conflict=license_hash,client_id') !== -1,
      'the conflict key is not license_hash,client_id: ' + post.url);
    assert.strictEqual(JSON.parse(post.opts.body).license_hash, HASH_A);
  });

  await test('alf_clients [Winj] a payload license_hash does not move the row',
    async () => {
      const { res, calls } = await call(HASH_A, 'emp-1', 'owner',
        { action: 'write', resource: 'alf_clients',
          payload: { id: 'C-X', name: 'A Resident', license_hash: HASH_B } }, []);
      const post = firstPost(calls);
      if (!post) {
        assert.fail('UNREACHED: no upsert; handler answered ' + res.statusCode
          + ' ' + JSON.stringify(res.body));
      }
      const sentCli = JSON.parse(post.opts.body);
      assert.strictEqual(sentCli.license_hash, HASH_A,
        'a license_hash inside the payload reached the stored row');
      // storedBlob() (api/_lib/blob.js, 2026-09-24): scope keys never reach
      // the stored data either.
      assert.ok(!('license_hash' in (sentCli.data || {})),
        'the payload license_hash was stored INSIDE the data blob');
    });

  // ══ alf_facility ════════════════════════════════════════════════════════
  section('alf_facility -- one row per facility, and the row IS the facility');

  await test('alf_facility [L] facility A sees only its own record', async () => {
    const seeded = [facility(HASH_A, 'F-A', 'A'), facility(HASH_B, 'F-B', 'B')];
    const { res, calls } = await call(HASH_A, 'emp-1', 'owner',
      { action: 'read', resource: 'alf_facility' }, seeded);
    reached(res, 'the facility A record read');
    assert.deepStrictEqual(tenantsIn(res), ['A'],
      'facility A was handed ' + JSON.stringify(tenantsIn(res)) + '. This branch '
      + 'has NO assignment narrowing at all, so license_hash is the only thing '
      + 'between one facility\'s record and another\'s.');
    assert.ok(calls.some(function (c) {
      return c.url.indexOf('alf_facility?license_hash=eq.' + HASH_A) !== -1; }));
  });

  await test('alf_facility [L-rev] facility B sees only its own', async () => {
    const seeded = [facility(HASH_A, 'F-A', 'A'), facility(HASH_B, 'F-B', 'B')];
    const { res } = await call(HASH_B, 'emp-9', 'owner',
      { action: 'read', resource: 'alf_facility' }, seeded);
    reached(res, 'the facility B record read');
    assert.deepStrictEqual(tenantsIn(res), ['B']);
  });

  await test('alf_facility [W] the conflict key carries license_hash', async () => {
    const { res, calls } = await call(HASH_A, 'emp-1', 'owner',
      { action: 'write', resource: 'alf_facility',
        payload: { id: 'F-B', name: 'A Facility' } }, []);
    const post = firstPost(calls);
    if (!post) {
      UNREACHED.push(['alf_facility write', res.statusCode,
                      (res.body && res.body.error && res.body.error.code) || '']);
      assert.fail('UNREACHED: no upsert was sent; handler answered ' + res.statusCode
        + ' ' + JSON.stringify(res.body));
    }
    assert.ok(post.url.indexOf('on_conflict=license_hash,facility_id') !== -1,
      'the conflict key is not license_hash,facility_id: ' + post.url
      + ' -- drop license_hash and two facilities share one facility record');
    assert.strictEqual(JSON.parse(post.opts.body).license_hash, HASH_A);
  });

  await test('alf_facility [Winj] a payload license_hash does not move the row',
    async () => {
      const { res, calls } = await call(HASH_A, 'emp-1', 'owner',
        { action: 'write', resource: 'alf_facility',
          payload: { id: 'F-X', name: 'A Facility', license_hash: HASH_B } }, []);
      const post = firstPost(calls);
      if (!post) {
        assert.fail('UNREACHED: no upsert; handler answered ' + res.statusCode
          + ' ' + JSON.stringify(res.body));
      }
      const sentFac = JSON.parse(post.opts.body);
      assert.strictEqual(sentFac.license_hash, HASH_A);
      assert.ok(!('license_hash' in (sentFac.data || {})),
        'the payload license_hash was stored INSIDE the data blob');
    });

  // ══ alf_mar ═════════════════════════════════════════════════════════════
  section('alf_mar -- the same collision, on a MEDICATION ADMINISTRATION RECORD');

  await test('alf_mar [L] a broad MAR role sees ONLY facility A entries', async () => {
    const seeded = [marEntry(HASH_A, 'M-A', 'C-A', 'emp-1', 'A'),
                    marEntry(HASH_B, 'M-B', 'C-B', 'emp-9', 'B')];
    const { res, calls } = await call(HASH_A, 'emp-1', 'nursing',
      { action: 'read', resource: 'alf_mar' }, seeded);
    reached(res, 'the facility A MAR read');
    assert.deepStrictEqual(tenantsIn(res), ['A']);
    assert.ok(calls.some(function (c) {
      return c.url.indexOf('alf_mar?license_hash=eq.' + HASH_A) !== -1; }));
  });

  await test('alf_mar [L-rev] facility B sees only its own', async () => {
    const seeded = [marEntry(HASH_A, 'M-A', 'C-A', 'emp-1', 'A'),
                    marEntry(HASH_B, 'M-B', 'C-B', 'emp-9', 'B')];
    const { res } = await call(HASH_B, 'emp-9', 'nursing',
      { action: 'read', resource: 'alf_mar' }, seeded);
    reached(res, 'the facility B MAR read');
    assert.deepStrictEqual(tenantsIn(res), ['B']);
  });

  await test('alf_mar [L-collide] a MED AIDE named emp-1 does not get the other '
    + 'facility\'s medication record', async () => {
      // THE SHARPEST VERSION OF THIS SHAPE ON THE PLATFORM. med_aide is inside
      // ALF_MAR_ROLES (so the branch is reachable) and outside
      // ALF_MAR_BROAD_ROLES (so the answer is narrowed to their own
      // assignments, in memory, after the query). Both facilities have an
      // emp-1. Drop the tenant filter and this caller is handed another
      // facility's resident's administration record -- drug, dose, and who
      // gave it -- as if it were their own patient's.
      const seeded = [marEntry(HASH_A, 'M-A', 'C-A', 'emp-1', 'A'),
                      marEntry(HASH_B, 'M-B', 'C-B', 'emp-1', 'B'),
                      marEntry(HASH_B, 'M-B2', 'C-B2', 'emp-1', 'B')];
      const { res } = await call(HASH_A, 'emp-1', 'med_aide',
        { action: 'read', resource: 'alf_mar' }, seeded);
      reached(res, 'the facility A med-aide MAR read');
      assert.deepStrictEqual(tenantsIn(res), ['A'],
        'the med aide was handed ' + JSON.stringify(tenantsIn(res))
        + ' -- every one of these entries is assigned to "emp-1" and only the '
        + 'tenant marker inside data tells them apart. This is PHI.');
    });

  await test('alf_mar [W] the tenant binding is an RPC ARGUMENT, not a conflict key',
    async () => {
      // alf_mar is append-only through a stored procedure, so there is no
      // `on_conflict=license_hash,...` to assert. `p_license_hash` is the ONLY
      // thing tying the inserted row to a facility, which makes it the whole
      // write-side boundary for this resource.
      //
      // The resident lookup in front of it is itself license_hash-filtered, so
      // the seeded resident has to be facility A's for this arm to reach the
      // RPC at all -- and a resident seeded under B would leave it UNREACHED
      // rather than passing.
      const { res, calls } = await call(HASH_A, 'emp-1', 'nursing',
        { action: 'write', resource: 'alf_mar',
          payload: { id: 'M-NEW', resident_id: 'C-A', entry_type: 'administration',
                     drug: 'A Drug' } },
        [client(HASH_A, 'C-A', 'emp-1', 'A')]);
      const post = calls.filter(function (c) {
        return c.opts && c.opts.method === 'POST' && /rpc\//.test(c.url); })[0];
      if (!post) {
        UNREACHED.push(['alf_mar write', res.statusCode,
                        (res.body && res.body.error && res.body.error.code) || '']);
        assert.fail('UNREACHED: no RPC call was sent; handler answered '
          + res.statusCode + ' ' + JSON.stringify(res.body));
      }
      const sent = JSON.parse(post.opts.body);
      assert.strictEqual(sent.p_license_hash, HASH_A,
        'the MAR entry was inserted under ' + JSON.stringify(sent.p_license_hash)
        + ' rather than the hash the handler derived from the bearer key');
      assert.strictEqual(sent.p_entry_id, 'M-NEW');
    });

  await test('alf_mar [Winj] a payload license_hash does not reach the RPC',
    async () => {
      const { res, calls } = await call(HASH_A, 'emp-1', 'nursing',
        { action: 'write', resource: 'alf_mar',
          payload: { id: 'M-NEW2', resident_id: 'C-A', entry_type: 'administration',
                     license_hash: HASH_B, p_license_hash: HASH_B, drug: 'A Drug' } },
        [client(HASH_A, 'C-A', 'emp-1', 'A')]);
      const post = calls.filter(function (c) {
        return c.opts && c.opts.method === 'POST' && /rpc\//.test(c.url); })[0];
      if (!post) {
        assert.fail('UNREACHED: no RPC call; handler answered ' + res.statusCode
          + ' ' + JSON.stringify(res.body));
      }
      const sentMar = JSON.parse(post.opts.body);
      assert.strictEqual(sentMar.p_license_hash, HASH_A,
        'a license_hash inside the payload reached the stored procedure');
      // storedBlob() strips the scope keys AND created_at from p_data --
      // created_at because the read maps the COLUMN and spreads the blob
      // after it, so a blob copy would shadow the real one (the
      // 2026-09-23T18:54:03Z review point 1, closed by this).
      const pd = sentMar.p_data || {};
      assert.ok(!('license_hash' in pd) && !('p_license_hash' in pd)
        && !('created_at' in pd),
        'a scope key or created_at was stored inside p_data: '
        + JSON.stringify(Object.keys(pd)));
    });

  // ══ THE SESSION HALF ════════════════════════════════════════════════════
  section('THE SESSION HALF -- a token minted for the other facility, and for '
    + 'another app');

  for (const [resource, , broadRole] of UNITS) {
    await test(resource + ' [S] facility B\'s token against facility A\'s licence '
      + 'is refused', async () => {
        const calls = [];
        const h = loadHandler(HASH_A, postgrestMock([], calls));
        const res = mockRes();
        await h({ method: 'POST',
                  headers: { authorization: 'Bearer KEY-FOR-' + HASH_A,
                             'x-sd-auth': signSessionToken({
                               app: APP, employee_id: 'emp-9', role: broadRole,
                               license_hash: HASH_B }) },
                  body: { action: 'read', resource: resource } }, res);
        assert.ok(res.statusCode === 401 || res.statusCode === 403,
          'a session signed for ' + HASH_B + ' was accepted against ' + HASH_A
          + ': ' + res.statusCode + ' ' + JSON.stringify(res.body));
        assert.ok(!calls.some(function (c) { return c.url.indexOf(resource) !== -1; }),
          'the refused request still queried ' + resource);
      });

    await test(resource + ' [S] a SAIRNvet token for the same tenant is refused',
      async () => {
        // Guardian Check 28's collision. `sairnvet` is used rather than any
        // app because SAIRNcare and SAIRNvet both hold clinical records, so a
        // missing expected-app argument here would cross the two apps with the
        // worst possible payload.
        const calls = [];
        const h = loadHandler(HASH_A, postgrestMock([], calls));
        const res = mockRes();
        await h({ method: 'POST',
                  headers: { authorization: 'Bearer KEY-FOR-' + HASH_A,
                             'x-sd-auth': signSessionToken({
                               app: 'sairnvet', employee_id: 'emp-1',
                               role: 'owner', license_hash: HASH_A }) },
                  body: { action: 'read', resource: resource } }, res);
        assert.ok(res.statusCode === 401 || res.statusCode === 403,
          'a SAIRNvet session reached SAIRNcare\'s ' + resource + ': '
          + res.statusCode + ' ' + JSON.stringify(res.body));
        assert.ok(!calls.some(function (c) { return c.url.indexOf(resource) !== -1; }),
          'the refused request still queried ' + resource);
      });
  }

  // ── THE NEGATIVE CONTROL ON THE MOCK ITSELF ─────────────────────────────
  section('THE NEGATIVE CONTROL -- the mock still distinguishes filtered from '
    + 'unfiltered, ANDs its clauses, and projects');
  await test('an unfiltered query returns BOTH tenants', async () => {
    const seeded = [client(HASH_A, 'C-A', 'emp-1', 'A'),
                    client(HASH_B, 'C-B', 'emp-1', 'B')];
    const f = postgrestMock(seeded, []);
    const unfiltered = await (await f('https://x/rest/v1/alf_clients')).json();
    assert.strictEqual(unfiltered.length, 2,
      'the mock returned ' + unfiltered.length + ' rows for a query with NO eq. '
      + 'clauses. It is not filtering, so every arm above proves nothing.');
    const filtered = await (await f('https://x/rest/v1/alf_clients?license_hash=eq.'
      + HASH_A)).json();
    assert.strictEqual(filtered.length, 1);
    const both = await (await f('https://x/rest/v1/alf_clients?license_hash=eq.'
      + HASH_A + '&client_id=eq.C-B')).json();
    assert.strictEqual(both.length, 0,
      'two eq. clauses must be ANDed: A\'s hash with B\'s client id matches nothing');
  });

  await test('the mock honours select=', async () => {
    const f = postgrestMock([client(HASH_A, 'C-A', 'emp-1', 'A')], []);
    const projected = await (await f('https://x/rest/v1/alf_clients?license_hash=eq.'
      + HASH_A + '&select=client_id,data')).json();
    assert.deepStrictEqual(Object.keys(projected[0]).sort(), ['client_id', 'data'],
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
