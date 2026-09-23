// api/sd-data-roofing-projected-isolation.test.js
//
// REQUIREMENT: on the three SAIRNroofing branches that RE-PROJECT their rows
//   before responding, a valid, fully authenticated session for tenant A
//   cannot read or overwrite tenant B's rows.
//
// CROSS-TENANT-ISOLATION: rf_settings, sub_assignments, rf_jobs
//
// Run:  node api/sd-data-roofing-projected-isolation.test.js
//
// ── WHY THESE THREE ARE NOT ROWS IN THE DISPATCHER SUITE ──────────────────
// api/sd-data-cross-tenant-dispatchers.test.js seeds every fixture with an
// `owner` marker at both the row level and inside `data`, and its [L] arm
// reads `x.owner` back off each returned item. That works for any branch that
// hands rows through, or that spreads `r.data` into its response. These three
// do NEITHER:
//
//   rf_settings     -> {setting_key, value, updated_by, updated_at}
//   sub_assignments -> summariseAssignment(x), a FIXED field list
//   rf_jobs         -> Object.assign({id, job_class, assigned_employee_id,
//                      location_id}, r.data), plus an in-memory narrowing
//
// rf_jobs' spread does carry `owner` through, and it graded WEAK rather than
// NONE for related reasons -- but it is here with the other two because the
// arm it actually needs is the one the shared harness cannot express at all.
// See THE COLLISION SHAPE below.
//
// THE SHARED ARM WAS NOT WIDENED TO FIT THEM, deliberately. Making `owner`
// optional there would weaken the probe for the 150+ members it covers: a
// member whose fixture stops carrying `owner` returns `[]`, and an
// absence-only assertion passes `[]` for entirely the wrong reason. Three
// resources pay for their own arms instead.
//
// ── THE COLLISION SHAPE, WHICH IS THE POINT OF THIS FILE ──────────────────
// All three of these resources are keyed on something TENANTS LEGITIMATELY
// SHARE, so the tenant filter is the ONLY thing separating two real rows that
// look identical:
//
//   rf_settings      two companies both configure `damage_threshold`
//   sub_assignments  two companies both have an assignment `AS-1`
//   rf_jobs          two companies both employ an `emp-1`
//
// Drop `license_hash=eq.` and the caller does not get an empty screen or an
// obviously foreign record -- they get a plausible one. A count assertion
// cannot see that and neither can a shape assertion, so every arm below
// asserts WHOSE row came back, using a marker the projection actually
// preserves.
//
// ── WHAT THIS DOES NOT DO ─────────────────────────────────────────────────
// It does not test the DATABASE, and it does not test the ROLE gates on these
// branches (who may write a company setting, who may assign a subcontractor,
// who may reassign a job). Those are separate questions with their own suites.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['roofing', 'projected', 'isolation', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const { signSessionToken } = require('./_lib/auth');

const HASH_A = 'tenant-A-hash';
const HASH_B = 'tenant-B-hash';
const APP = 'sairnroofing';

// The table this suite drives, in the shape
// tools/cross_tenant_isolation_scope.py cross-checks a declaration against.
// `role` is the one the read arms use: rf-auth's MANAGEMENT_ROLES is
// {owner, admin} and BROAD_READ_ROLES is {owner, admin, estimator}, so `owner`
// is the only role that cannot narrow a read for a reason other than
// license_hash. `narrowRole` is a real ROLES_BY_APP.sairnroofing role that is
// in NEITHER set -- which is what makes the rf_jobs collision arm possible.
const UNITS = [
  ['rf_settings', 'setting_key', 'owner'],
  ['sub_assignments', 'assignment_id', 'owner'],
  ['rf_jobs', 'job_id', 'owner', 'foreman']
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
// is left -- the app_id, the sub_id, or nothing at all -- returns the other
// tenant's row, and the content assertion fails.
//
// IT HONOURS `select=`, unlike the dispatcher suite's mock, and that is not
// cosmetic here: all three branches ask for a NAMED column list, and
// sub_assignments' response is built by a summariser that reads specific
// fields. A mock handing back columns the real query never asked for would be
// testing a row shape the handler never sees.
//
// EVERY WAY IT IS UNFAITHFUL RUNS IN THE SAFE DIRECTION: an unrecognised
// clause is simply not applied, so it returns MORE rows than PostgREST would
// and the content assertion fails LOUDER. No query shape makes it return
// FEWER. The negative control at the bottom drives that rather than asserting
// it in prose.
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
    // A credential lookup is not the query under test. Answered FOR THE TENANT
    // IN THE QUERY so it stays tenant-scoped rather than becoming a hole.
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

// Fresh per call. _lib/auth is deliberately NOT stubbed -- the licence-hash
// half of the tenant boundary lives inside verifySessionToken, and a stub
// there answers yes to part of the question this file is asking.
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
function rows(res) { return (res.body && res.body.data) || []; }

(async function () {
  console.log('CROSS-TENANT ISOLATION -- the SAIRNroofing branches whose response is a '
    + 'PROJECTION (' + UNITS.length + ' resources)');

  // ══ rf_settings ═════════════════════════════════════════════════════════
  // Keyed rows, one per setting. The response is
  // {setting_key, value, updated_by, updated_at} -- `value` IS the stored
  // `data` blob, which is the one place a tenant marker survives.
  function setting(licHash, key, tenant) {
    return { license_hash: licHash, setting_key: key,
             data: { tenant: tenant, damage_threshold: {} },
             updated_by: 'emp-1', updated_at: '2026-09-01T00:00:00.000Z' };
  }

  section('rf_settings -- BOTH TENANTS CONFIGURE THE SAME KEY, which is the '
    + 'whole risk');

  await test('rf_settings [L-collide] tenant A gets ITS OWN damage_threshold, '
    + 'not the other company\'s', async () => {
    // `damage_threshold` decides repair-vs-replace. It is not a per-tenant
    // name -- every roofing company configures the same key -- so if the
    // license_hash filter were dropped, tenant A would be handed TWO rows with
    // identical `setting_key` and whichever one the UI reads first would
    // silently decide whether a slope is called a total loss.
    const seeded = [
      setting(HASH_A, 'damage_threshold', 'A'),
      setting(HASH_B, 'damage_threshold', 'B')
    ];
    const { res, calls } = await call(HASH_A, 'emp-1', 'owner',
      { action: 'read', resource: 'rf_settings' }, seeded);
    reached(res, 'the tenant A rf_settings read');
    assert.deepStrictEqual(rows(res).map(function (r) { return r.value.tenant; }), ['A'],
      'tenant A was handed ' + JSON.stringify(rows(res).map(function (r) {
        return r.value && r.value.tenant; })) + '. Both rows carry setting_key '
      + '"damage_threshold", so nothing about the SHAPE of this answer is wrong '
      + '-- only whose it is.');
    assert.ok(calls.some(function (c) {
      return c.url.indexOf('rf_settings?license_hash=eq.' + HASH_A) !== -1; }),
      'no query carried rf_settings?license_hash=eq.' + HASH_A);
  });

  await test('rf_settings [L-rev] tenant B gets its own', async () => {
    const seeded = [
      setting(HASH_A, 'damage_threshold', 'A'),
      setting(HASH_B, 'damage_threshold', 'B')
    ];
    const { res } = await call(HASH_B, 'emp-1', 'owner',
      { action: 'read', resource: 'rf_settings' }, seeded);
    reached(res, 'the tenant B rf_settings read');
    assert.deepStrictEqual(rows(res).map(function (r) { return r.value.tenant; }), ['B'],
      'a handler hardcoded to one tenant passes the arm above and fails here');
  });

  await test('rf_settings [W] the upsert is keyed on license_hash AND setting_key',
    async () => {
      const { res, calls } = await call(HASH_A, 'emp-1', 'owner',
        { action: 'write', resource: 'rf_settings',
          payload: { setting_key: 'some_other_key', value: { tenant: 'A' } } }, []);
      const post = firstPost(calls);
      if (!post) {
        UNREACHED.push(['rf_settings write', res.statusCode,
                        (res.body && res.body.error && res.body.error.code) || '']);
        assert.fail('UNREACHED: no upsert was sent; handler answered ' + res.statusCode
          + ' ' + JSON.stringify(res.body));
      }
      // Drop license_hash from this key and the two companies share ONE
      // damage_threshold row -- tenant A's write would not corrupt B's data,
      // it would BECOME it.
      assert.ok(post.url.indexOf('on_conflict=license_hash,setting_key') !== -1,
        'the conflict key is not license_hash,setting_key: ' + post.url);
      assert.strictEqual(JSON.parse(post.opts.body).license_hash, HASH_A,
        'the row was written under the wrong tenant');
    });

  await test('rf_settings [Winj] a payload license_hash does not move the row',
    async () => {
      const { res, calls } = await call(HASH_A, 'emp-1', 'owner',
        { action: 'write', resource: 'rf_settings',
          payload: { setting_key: 'some_other_key', license_hash: HASH_B,
                     value: { tenant: 'A' } } }, []);
      const post = firstPost(calls);
      if (!post) {
        assert.fail('UNREACHED: no upsert; handler answered ' + res.statusCode
          + ' ' + JSON.stringify(res.body));
      }
      assert.strictEqual(JSON.parse(post.opts.body).license_hash, HASH_A,
        'a license_hash inside the payload reached the stored row');
    });

  // ══ sub_assignments ═════════════════════════════════════════════════════
  // summariseAssignment() returns a FIXED field list, so `owner` cannot
  // survive. `sub_id` does, and it is what these arms assert on.
  function assignment(licHash, aid, subId, appId) {
    return { license_hash: licHash, app_id: appId || APP, assignment_id: aid,
             sub_id: subId, job_id: 'J-1', scheduled_date: '2026-09-01',
             status: 'scheduled', amount: 100, payments: [], data: {},
             created_by: 'emp-1', updated_at: '2026-09-01T00:00:00.000Z' };
  }

  section('sub_assignments -- a FIXED summariser shape, and a SECOND boundary '
    + 'on the same row');

  await test('sub_assignments [L-collide] both tenants have an AS-1, and tenant A '
    + 'gets its own', async () => {
      const seeded = [
        assignment(HASH_A, 'AS-1', 'SUB-A'),
        assignment(HASH_B, 'AS-1', 'SUB-B')
      ];
      const { res, calls } = await call(HASH_A, 'emp-1', 'owner',
        { action: 'read', resource: 'sub_assignments' }, seeded);
      reached(res, 'the tenant A sub_assignments read');
      assert.deepStrictEqual(rows(res).map(function (r) { return r.sub_id; }), ['SUB-A'],
        'tenant A was handed ' + JSON.stringify(rows(res).map(function (r) {
          return r.sub_id; })) + '. Both rows are assignment AS-1 in the same '
        + 'shape; only the subcontractor on them differs.');
      assert.ok(calls.some(function (c) {
        return c.url.indexOf('sub_assignments?license_hash=eq.' + HASH_A) !== -1; }),
        'no query carried sub_assignments?license_hash=eq.' + HASH_A);
    });

  await test('sub_assignments [L-rev] tenant B gets its own', async () => {
    const seeded = [
      assignment(HASH_A, 'AS-1', 'SUB-A'),
      assignment(HASH_B, 'AS-1', 'SUB-B')
    ];
    const { res } = await call(HASH_B, 'emp-1', 'owner',
      { action: 'read', resource: 'sub_assignments' }, seeded);
    reached(res, 'the tenant B sub_assignments read');
    assert.deepStrictEqual(rows(res).map(function (r) { return r.sub_id; }), ['SUB-B']);
  });

  await test('sub_assignments [L-app] a row under the SAME tenant but another '
    + 'app_id does not come back', async () => {
      // THIS RESOURCE CARRIES TWO BOUNDARIES ON ONE ROW and the shared harness
      // has no notion of the second. `subcontractors`/`sub_assignments` are
      // shared tables with an app_id column, so the query ANDs
      // app_id=eq.sairnroofing alongside license_hash. Drop THAT clause and a
      // tenant sees its own rows from a different SAIRN app -- not a
      // cross-tenant leak, and still a leak.
      const seeded = [
        assignment(HASH_A, 'AS-1', 'SUB-A'),
        assignment(HASH_A, 'AS-2', 'SUB-OTHER-APP', 'sairnbuild')
      ];
      const { res } = await call(HASH_A, 'emp-1', 'owner',
        { action: 'read', resource: 'sub_assignments' }, seeded);
      reached(res, 'the app-scoped sub_assignments read');
      assert.deepStrictEqual(rows(res).map(function (r) { return r.sub_id; }), ['SUB-A'],
        'a sairnbuild row reached a sairnroofing read: ' + JSON.stringify(
          rows(res).map(function (r) { return r.sub_id; })));
    });

  await test('sub_assignments [W] the conflict key carries license_hash AND app_id',
    async () => {
      const { res, calls } = await call(HASH_A, 'emp-1', 'owner',
        { action: 'write', resource: 'sub_assignments',
          payload: { assignment_id: 'AS-1', sub_id: 'SUB-B' } }, []);
      const post = firstPost(calls);
      if (!post) {
        UNREACHED.push(['sub_assignments write', res.statusCode,
                        (res.body && res.body.error && res.body.error.code) || '']);
        assert.fail('UNREACHED: no upsert was sent; handler answered ' + res.statusCode
          + ' ' + JSON.stringify(res.body));
      }
      assert.ok(post.url.indexOf(
        'on_conflict=license_hash,app_id,assignment_id') !== -1,
        'the conflict key is not license_hash,app_id,assignment_id: ' + post.url
        + ' -- tenant A writing AS-1 would replace tenant B\'s AS-1');
      const sent = JSON.parse(post.opts.body);
      assert.strictEqual(sent.license_hash, HASH_A);
      assert.strictEqual(sent.app_id, APP,
        'the app_id was taken from somewhere other than the branch itself');
      assert.strictEqual(sent.created_by, 'emp-1',
        'created_by was not taken from the verified session');
    });

  await test('sub_assignments [Winj] a payload license_hash and app_id are ignored',
    async () => {
      const { res, calls } = await call(HASH_A, 'emp-1', 'owner',
        { action: 'write', resource: 'sub_assignments',
          payload: { assignment_id: 'AS-1', sub_id: 'SUB-B',
                     license_hash: HASH_B, app_id: 'sairnbuild',
                     created_by: 'somebody-else' } }, []);
      const post = firstPost(calls);
      if (!post) {
        assert.fail('UNREACHED: no upsert; handler answered ' + res.statusCode
          + ' ' + JSON.stringify(res.body));
      }
      const sent = JSON.parse(post.opts.body);
      assert.strictEqual(sent.license_hash, HASH_A,
        'a payload license_hash reached the stored row');
      assert.strictEqual(sent.app_id, APP,
        'a payload app_id reached the stored row -- the SECOND boundary is '
        + 'caller-controlled');
      assert.strictEqual(sent.created_by, 'emp-1',
        'a payload created_by overwrote the session identity');
    });

  // ══ rf_jobs ═════════════════════════════════════════════════════════════
  // Graded WEAK rather than NONE -- something already named it near a tenant
  // signal -- and WEAK on this resource is the more dangerous of the two
  // states, because it reads like partial coverage. The arm it needs is the
  // one below and nothing had it.
  function job(licHash, jobId, assignee, tenant) {
    return { license_hash: licHash, job_id: jobId, job_class: 'residential',
             assigned_employee_id: assignee, location_id: 'LOC-1',
             data: { tenant: tenant, name: 'A Job' } };
  }

  section('rf_jobs -- WEAK, and the narrowing that makes a dropped filter look '
    + 'like a correct answer');

  await test('rf_jobs [L] a broad-read role sees ONLY tenant A rows', async () => {
    const seeded = [job(HASH_A, 'J-A', 'emp-1', 'A'), job(HASH_B, 'J-B', 'emp-9', 'B')];
    const { res, calls } = await call(HASH_A, 'emp-1', 'owner',
      { action: 'read', resource: 'rf_jobs' }, seeded);
    reached(res, 'the tenant A rf_jobs broad read');
    assert.deepStrictEqual(rows(res).map(function (r) { return r.tenant; }), ['A']);
    assert.ok(calls.some(function (c) {
      return c.url.indexOf('rf_jobs?license_hash=eq.' + HASH_A) !== -1; }),
      'no query carried rf_jobs?license_hash=eq.' + HASH_A);
  });

  await test('rf_jobs [L-rev] tenant B sees only its own', async () => {
    const seeded = [job(HASH_A, 'J-A', 'emp-1', 'A'), job(HASH_B, 'J-B', 'emp-9', 'B')];
    const { res } = await call(HASH_B, 'emp-9', 'owner',
      { action: 'read', resource: 'rf_jobs' }, seeded);
    reached(res, 'the tenant B rf_jobs broad read');
    assert.deepStrictEqual(rows(res).map(function (r) { return r.tenant; }), ['B']);
  });

  await test('rf_jobs [L-collide] a FOREMAN named emp-1 gets their own company\'s '
    + 'job, not the other company\'s emp-1 job', async () => {
      // THE ARM THIS FILE EXISTS FOR, and it is the same shape bld_tna has.
      // Employee ids are per tenant, so both companies have an emp-1. For a
      // role outside BROAD_READ_ROLES the handler narrows the FETCHED rows to
      // `assigned_employee_id === session.employee_id` -- AFTER the query. So
      // with the license_hash filter dropped, this caller is handed the other
      // company's job: one row, correctly shaped, assigned to "them",
      // plausibly their own. Neither a count nor a shape assertion can see it.
      const seeded = [
        job(HASH_A, 'J-A', 'emp-1', 'A'),
        job(HASH_B, 'J-B', 'emp-1', 'B'),
        job(HASH_B, 'J-B2', 'emp-1', 'B')
      ];
      const { res } = await call(HASH_A, 'emp-1', 'foreman',
        { action: 'read', resource: 'rf_jobs' }, seeded);
      reached(res, 'the tenant A foreman read');
      assert.deepStrictEqual(rows(res).map(function (r) { return r.tenant; }), ['A'],
        'the foreman was handed ' + JSON.stringify(rows(res).map(function (r) {
          return r.tenant; })) + ' -- every one of these rows is assigned to '
        + '"emp-1" and only the tenant marker inside data tells them apart');
    });

  await test('rf_jobs [L-collide-rev] and the same id in tenant B gets B\'s',
    async () => {
      const seeded = [job(HASH_A, 'J-A', 'emp-1', 'A'), job(HASH_B, 'J-B', 'emp-1', 'B')];
      const { res } = await call(HASH_B, 'emp-1', 'foreman',
        { action: 'read', resource: 'rf_jobs' }, seeded);
      reached(res, 'the tenant B foreman read');
      assert.deepStrictEqual(rows(res).map(function (r) { return r.tenant; }), ['B']);
    });

  await test('rf_jobs [W] A writing a job id that exists in B lands under A',
    async () => {
      const { res, calls } = await call(HASH_A, 'emp-1', 'owner',
        { action: 'write', resource: 'rf_jobs',
          payload: { id: 'J-B', name: 'A Job', assigned_employee_id: 'emp-1' } }, []);
      const post = firstPost(calls);
      if (!post) {
        UNREACHED.push(['rf_jobs write', res.statusCode,
                        (res.body && res.body.error && res.body.error.code) || '']);
        assert.fail('UNREACHED: no upsert was sent; handler answered ' + res.statusCode
          + ' ' + JSON.stringify(res.body));
      }
      assert.ok(post.url.indexOf('on_conflict=license_hash,job_id') !== -1,
        'the conflict key is not license_hash,job_id: ' + post.url);
      assert.strictEqual(JSON.parse(post.opts.body).license_hash, HASH_A);
    });

  await test('rf_jobs [Winj] a payload license_hash does not move the row', async () => {
    const { res, calls } = await call(HASH_A, 'emp-1', 'owner',
      { action: 'write', resource: 'rf_jobs',
        payload: { id: 'J-X', name: 'A Job', license_hash: HASH_B,
                   assigned_employee_id: 'emp-1' } }, []);
    const post = firstPost(calls);
    if (!post) {
      assert.fail('UNREACHED: no upsert; handler answered ' + res.statusCode
        + ' ' + JSON.stringify(res.body));
    }
    assert.strictEqual(JSON.parse(post.opts.body).license_hash, HASH_A,
      'a license_hash inside the payload reached the stored row');
  });

  // ══ THE SESSION HALF ════════════════════════════════════════════════════
  section('THE SESSION HALF -- a token minted for the other tenant, and for '
    + 'another app');

  for (const [resource] of UNITS) {
    await test(resource + ' [S] tenant B\'s token against tenant A\'s licence '
      + 'is refused', async () => {
        const calls = [];
        const h = loadHandler(HASH_A, postgrestMock([], calls));
        const res = mockRes();
        await h({ method: 'POST',
                  headers: { authorization: 'Bearer KEY-FOR-' + HASH_A,
                             'x-sd-auth': signSessionToken({
                               app: APP, employee_id: 'emp-9', role: 'owner',
                               license_hash: HASH_B }) },
                  body: { action: 'read', resource: resource } }, res);
        assert.strictEqual(res.statusCode, 401,
          'a session signed for ' + HASH_B + ' was accepted against ' + HASH_A
          + ': ' + res.statusCode + ' ' + JSON.stringify(res.body));
        assert.ok(!calls.some(function (c) { return c.url.indexOf(resource) !== -1; }),
          'the refused request still queried ' + resource);
      });

    await test(resource + ' [S] a SAIRNbuild token for the same tenant is refused',
      async () => {
        const calls = [];
        const h = loadHandler(HASH_A, postgrestMock([], calls));
        const res = mockRes();
        await h({ method: 'POST',
                  headers: { authorization: 'Bearer KEY-FOR-' + HASH_A,
                             'x-sd-auth': signSessionToken({
                               app: 'sairnbuild', employee_id: 'emp-1',
                               role: 'owner', license_hash: HASH_A }) },
                  body: { action: 'read', resource: resource } }, res);
        assert.strictEqual(res.statusCode, 401,
          'a SAIRNbuild session reached SAIRNroofing\'s ' + resource + ': '
          + res.statusCode + ' ' + JSON.stringify(res.body));
      });
  }

  // ── THE NEGATIVE CONTROL ON THE MOCK ITSELF ─────────────────────────────
  section('THE NEGATIVE CONTROL -- the mock still distinguishes filtered from '
    + 'unfiltered, ANDs its clauses, and projects');
  await test('an unfiltered query returns BOTH tenants', async () => {
    const seeded = [setting(HASH_A, 'damage_threshold', 'A'),
                    setting(HASH_B, 'damage_threshold', 'B')];
    const f = postgrestMock(seeded, []);
    const unfiltered = await (await f('https://x/rest/v1/rf_settings')).json();
    assert.strictEqual(unfiltered.length, 2,
      'the mock returned ' + unfiltered.length + ' rows for a query with NO eq. '
      + 'clauses. It is not filtering, so every arm above proves nothing.');
    const filtered = await (await f('https://x/rest/v1/rf_settings?license_hash=eq.'
      + HASH_A)).json();
    assert.strictEqual(filtered.length, 1);
    const both = await (await f('https://x/rest/v1/rf_settings?license_hash=eq.'
      + HASH_A + '&setting_key=eq.nothing')).json();
    assert.strictEqual(both.length, 0,
      'two eq. clauses must be ANDed');
  });

  await test('the mock honours select=, and passes `*` through whole', async () => {
    const f = postgrestMock([assignment(HASH_A, 'AS-1', 'SUB-A')], []);
    const projected = await (await f('https://x/rest/v1/sub_assignments?license_hash=eq.'
      + HASH_A + '&select=assignment_id,sub_id')).json();
    assert.deepStrictEqual(Object.keys(projected[0]).sort(), ['assignment_id', 'sub_id'],
      'the mock ignored select= and returned ' + JSON.stringify(Object.keys(projected[0])));
    // `select=*` is a real query shape on this branch (the assignment gate's
    // subcontractor lookup uses it). Treating `*` as a column name would hand
    // the handler an EMPTY object and the gate would refuse for the wrong
    // reason.
    const whole = await (await f('https://x/rest/v1/subcontractors?license_hash=eq.'
      + HASH_A + '&select=*')).json();
    assert.ok(whole[0].license_hash === HASH_A,
      'select=* did not return the whole row');
  });

  if (UNREACHED.length) {
    console.log('\nUNREACHED -- arms that never got to the tenant filter:');
    UNREACHED.forEach(function (u) { console.log('  %s -> %s %s', u[0], u[1], u[2]); });
    console.log('These are NOT isolation failures and NOT passes.');
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
