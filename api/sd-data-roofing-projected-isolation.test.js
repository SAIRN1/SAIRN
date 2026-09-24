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
    // ── THE MOCK IS TABLE-BLIND BY DEFAULT, AND THAT IS ONLY SAFE FOR A
    //    SINGLE-TABLE FIXTURE (2026-09-24) ──────────────────────────────────
    // It filters the seeded array by the query's `=eq.` clauses and nothing
    // else, so with a fixture spanning several tables EVERY query gets every
    // row of that tenant. Harmless while each arm seeded one table; wrong the
    // moment one does not. The rf_locations arms seed locations, buildings,
    // jobs and sections together, and the sections row carries a
    // `building_id` with no `location_id` -- so the BUILDINGS query returned
    // it too, `bldLoc['BL-1']` was overwritten with undefined by last-write-
    // wins, and the entity chain resolved to nothing. The CONTROL arm caught
    // it: the refusal arm was green and the paired positive was not.
    //
    // A row may now declare `__table`, and is then matched ONLY for that
    // table. Rows without it behave exactly as before, so every arm written
    // against the old mock is untouched.
    const table = (u.split('/rest/v1/')[1] || '').split('?')[0];
    const matches = rows.filter(function (r) {
      if (r.__table && r.__table !== table) return false;
      return eqs.every(function (kv) { return String(r[kv[0]]) === kv[1]; });
    }).map(function (r) {
      if (!select || select.indexOf('*') !== -1) return r;
      const out = {};
      select.forEach(function (c) { if (c in r && c !== '__table') out[c] = r[c]; });
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

  // ══ rf_locations -- THE FIVE READS NOTHING DROVE ════════════════════════
  // FOUND 2026-09-24 while discharging a review. `rf_locations` has SIX
  // license_hash-filtered read sites in api/sd-data.js and the isolation arm
  // drives exactly ONE of them. Measured, not inferred: removing the tenant
  // filter from each of the other five in turn left both roofing suites
  // completely green.
  //
  //   :7149  drawEntityFilter()      -- rf_draws read, only when payload.entity_id is set
  //   :7368  the roof-section filter -- rf_roof_sections read, same condition
  //   :8344  rf_entities consolidate/preview_move, location attribution
  //   :8347  ...its FALLBACK, taken when the entity_id column is absent (400)
  //   :8446  ...the rf_locations read's OWN fallback, same condition
  //
  // THE DIFFERENCE BETWEEN COVERING A RESOURCE AND COVERING A QUERY. An
  // arm-per-resource harness reports rf_locations as GENUINE and means one
  // query; the tenant filter is written six times and five of them could be
  // deleted without a single arm going red. Two of the five are FALLBACK
  // paths, which is the worse half: they run only when the first select fails,
  // so they are exactly the code a normal test run never reaches.
  //
  // EVERY ARM BELOW IS A COLLISION ARM, same design as the rest of this file.
  // Both tenants own a location called `LOC-1`, mapped to DIFFERENT entities.
  // That is realistic -- a location id is not a per-tenant name -- and it is
  // what makes the assertion content-based rather than a count.
  function rlLoc(licHash, entityId) {
    return { __table: 'rf_locations', license_hash: licHash,
             location_id: 'LOC-1', name: 'Main', active: true,
             entity_id: entityId, data: { tenant: licHash } };
  }
  function rlJob(licHash, id, locationId) {
    return { __table: 'rf_jobs', license_hash: licHash, job_id: id,
             location_id: locationId, data: { id: id } };
  }
  function rlDraw(licHash, id, jobId) {
    return { __table: 'rf_draws', license_hash: licHash, draw_id: id,
             job_id: jobId, data: { id: id, amount: 100 } };
  }
  function rlBuilding(licHash, id, locationId) {
    return { __table: 'rf_buildings', license_hash: licHash, building_id: id,
             location_id: locationId, data: { id: id } };
  }
  function rlSection(licHash, id, buildingId) {
    return { __table: 'rf_roof_sections', license_hash: licHash,
             section_id: id, building_id: buildingId, status: 'active',
             data: { id: id } };
  }
  function rlEntity(licHash, id) {
    return { __table: 'rf_entities', license_hash: licHash, entity_id: id,
             legal_name: id + ' Roofing', data: { id: id } };
  }

  section('rf_locations -- the FIVE reads no arm drove, and two of them are '
    + 'FALLBACK paths');

  await test('rf_locations [L-draws] the draw entity filter resolves locations '
    + 'from tenant A ONLY -- asking for the OTHER tenant\'s entity matches '
    + 'nothing', async () => {
    // A's LOC-1 belongs to ENT-A; B's LOC-1 belongs to ENT-B. Asking as A for
    // ENT-B must match no location, so no job, so no draw. Drop the tenant
    // filter on the rf_locations read at :7149 and B's LOC-1 -> ENT-B enters
    // the map, A's job at LOC-1 resolves to ENT-B, and A's own draw comes
    // back under another company's entity.
    const seeded = [
      rlLoc(HASH_A, 'ENT-A'), rlLoc(HASH_B, 'ENT-B'),
      rlJob(HASH_A, 'J-A', 'LOC-1'), rlDraw(HASH_A, 'D-A1', 'J-A')
    ];
    const { res } = await call(HASH_A, 'emp-1', 'owner',
      { action: 'read', resource: 'rf_draws', payload: { entity_id: 'ENT-B' } },
      seeded);
    reached(res, 'the rf_draws read with an entity filter');
    // THE KEY IS `draw_id`, NOT `id`. This branch responds with the PROJECTED
    // row plus a summary, so `id` is undefined on every item -- an arm mapping
    // `id` compares [undefined] against ['D-A1'] and fails the CONTROL while
    // the refusal arm passes on an empty list. Caught by the control, which is
    // exactly what it is for.
    assert.deepStrictEqual(rows(res).map(function (d) { return d.draw_id; }), [],
      'tenant A asked for tenant B\'s entity and got draws back: '
      + JSON.stringify(rows(res)));
  });

  await test('rf_locations [L-draws-rev] CONTROL: asking for tenant A\'s OWN '
    + 'entity DOES return the draw', async () => {
    // Without this the arm above is satisfied by a filter that returns
    // nothing for every entity -- including a handler that simply broke.
    const seeded = [
      rlLoc(HASH_A, 'ENT-A'), rlLoc(HASH_B, 'ENT-B'),
      rlJob(HASH_A, 'J-A', 'LOC-1'), rlDraw(HASH_A, 'D-A1', 'J-A')
    ];
    const { res } = await call(HASH_A, 'emp-1', 'owner',
      { action: 'read', resource: 'rf_draws', payload: { entity_id: 'ENT-A' } },
      seeded);
    reached(res, 'the rf_draws read with its own entity filter');
    assert.deepStrictEqual(rows(res).map(function (d) { return d.draw_id; }), ['D-A1'],
      'the entity filter dropped tenant A\'s own draw: ' + JSON.stringify(rows(res)));
  });

  await test('rf_locations [L-sections] the roof-section entity filter resolves '
    + 'locations from tenant A ONLY', async () => {
    // section -> building -> location -> entity. Same collision, one hop
    // longer, and a different read site (:7368).
    const seeded = [
      rlLoc(HASH_A, 'ENT-A'), rlLoc(HASH_B, 'ENT-B'),
      rlBuilding(HASH_A, 'BL-1', 'LOC-1'), rlSection(HASH_A, 'S-A1', 'BL-1')
    ];
    const { res } = await call(HASH_A, 'emp-1', 'owner',
      { action: 'read', resource: 'rf_roof_sections',
        payload: { entity_id: 'ENT-B' } }, seeded);
    reached(res, 'the rf_roof_sections read with an entity filter');
    // ASSERTED ON THE BRANCH'S OWN DECLARED FILTER ACCOUNTING, not on the item
    // shape: the read responds with `data: evaluated`, sections passed through
    // the registry evaluator, so no identity key survives predictably. The
    // branch already publishes `entity_filter` and `filtered_out` precisely so
    // a filtered list cannot look unfiltered -- which makes them the right
    // things to assert and not a fallback.
    assert.strictEqual(rows(res).length, 0,
      'tenant A asked for tenant B\'s entity and got sections back: '
      + JSON.stringify(res.body));
    assert.strictEqual(res.body.filtered_out, 1,
      'the branch did not report hiding tenant A\'s section, so the filter '
      + 'either did not run or hid it silently: ' + JSON.stringify(res.body));
  });

  await test('rf_locations [L-sections-rev] CONTROL: tenant A\'s OWN entity '
    + 'returns the section', async () => {
    const seeded = [
      rlLoc(HASH_A, 'ENT-A'), rlLoc(HASH_B, 'ENT-B'),
      rlBuilding(HASH_A, 'BL-1', 'LOC-1'), rlSection(HASH_A, 'S-A1', 'BL-1')
    ];
    const { res } = await call(HASH_A, 'emp-1', 'owner',
      { action: 'read', resource: 'rf_roof_sections',
        payload: { entity_id: 'ENT-A' } }, seeded);
    reached(res, 'the rf_roof_sections read with its own entity filter');
    assert.strictEqual(rows(res).length, 1,
      'the entity filter dropped tenant A\'s own section: '
      + JSON.stringify(res.body));
    assert.strictEqual(res.body.filtered_out, 0,
      'the branch reported hiding a section when nothing should have been '
      + 'hidden: ' + JSON.stringify(res.body));
  });

  // ── THE FALLBACK PATHS, which is the half a normal run never reaches ─────
  // Both :8347 and :8446 exist because the `entity_id` column may not be
  // present on a half-migrated app: the first select answers 400 and the
  // handler retries WITHOUT that column. api/sd-data.js argues for that
  // fallback in its own words -- "every branch would VANISH from a working app
  // because a feature they never asked for was added". It is the right design
  // AND it is a second copy of the tenant filter that only executes in a state
  // no test had ever put the handler into.
  //
  // The wrapper below is the minimum that reaches it: any select naming
  // `entity_id` answers 400 ONCE per table, exactly as PostgREST would for an
  // absent column, and everything else goes to the real mock.
  function withMissingEntityColumn(rows_, calls, onlyTable) {
    const inner = postgrestMock(rows_, calls);
    const refused = {};
    return async function (url, opts) {
      const u = String(url);
      const table = (u.split('/rest/v1/')[1] || '').split('?')[0];
      // SCOPED TO ONE TABLE when asked. The consolidation reads rf_entities
      // with a select that also names entity_id, and refusing THAT one makes
      // the branch bail before it ever reaches the locations fallback -- an
      // arm that would have driven nothing while looking like it drove the
      // hard path.
      if ((!onlyTable || table === onlyTable)
          && /select=[^&]*entity_id/.test(u) && !refused[table]) {
        refused[table] = true;
        calls.push({ url: u, opts: opts || null, forced400: true });
        return { ok: false, status: 400,
                 json: async function () { return { message: 'column does not exist' }; },
                 text: async function () { return 'column rf_locations.entity_id does not exist'; } };
      }
      return inner(u, opts);
    };
  }

  async function callMissingColumn(licHash, body, rows_, onlyTable) {
    const calls = [];
    const h = loadHandler(licHash,
      withMissingEntityColumn(rows_ || [], calls, onlyTable));
    const res = mockRes();
    await h(mockReq(body, licHash, 'emp-1', 'owner'), res);
    return { res: res, calls: calls };
  }

  await test('rf_locations [L-fallback] the entity-column FALLBACK read is '
    + 'still tenant-scoped -- the copy of the filter nothing had executed',
  async () => {
    const seeded = [rlLoc(HASH_A, 'ENT-A'), rlLoc(HASH_B, 'ENT-B')];
    const { res, calls } = await callMissingColumn(HASH_A,
      { action: 'read', resource: 'rf_locations' }, seeded);
    reached(res, 'the rf_locations read on a half-migrated app');
    // THE ARM IS ONLY MEANINGFUL IF THE FALLBACK ACTUALLY RAN. Asserted, not
    // assumed: a wrapper that stopped forcing the 400 would leave this arm
    // testing the SAME line the existing arm already covers.
    assert.ok(calls.some(function (c) { return c.forced400; }),
      'the first select was never refused, so the fallback path did not run');
    assert.ok(calls.some(function (c) {
      return /rf_locations\?/.test(c.url) && !/entity_id/.test(c.url)
             && c.url.indexOf('license_hash=eq.' + HASH_A) !== -1; }),
      'the fallback read carried no license_hash for tenant A: '
      + JSON.stringify(calls.map(function (c) { return c.url; })));
    assert.deepStrictEqual(
      rows(res).map(function (x) { return (x.data && x.data.tenant) || x.tenant; })
        .filter(function (x) { return x !== undefined; }),
      [HASH_A],
      'the fallback read returned another tenant\'s locations: '
      + JSON.stringify(rows(res)));
  });

  await test('rf_locations [L-entities] the rf_entities consolidation resolves '
    + 'its location attribution from tenant A ONLY', async () => {
    const seeded = [
      rlLoc(HASH_A, 'ENT-A'), rlLoc(HASH_B, 'ENT-B'),
      rlEntity(HASH_A, 'ENT-A'), rlEntity(HASH_B, 'ENT-B')
    ];
    const { res, calls } = await call(HASH_A, 'emp-1', 'owner',
      { action: 'consolidate', resource: 'rf_entities', payload: {} }, seeded);
    // This branch can legitimately refuse for reasons that are not about
    // tenancy, so the QUERY assertion is the one that must hold either way:
    // whatever it did, the location read it made was tenant A's.
    const locCalls = calls.filter(function (c) { return /rf_locations\?/.test(c.url); });
    assert.ok(locCalls.length > 0,
      'the consolidation made no rf_locations read at all, so this arm drove '
      + 'nothing -- exit ' + res.statusCode + ' '
      + JSON.stringify(res.body && res.body.error));
    locCalls.forEach(function (c) {
      assert.ok(c.url.indexOf('license_hash=eq.' + HASH_A) !== -1,
        'a consolidation location read carried no tenant filter: ' + c.url);
    });
  });

  await test('rf_locations [L-entities-fallback] the CONSOLIDATION\'s own '
    + 'entity-column fallback read is tenant-scoped too -- the sixth and last '
    + 'copy of this filter', async () => {
    // The one the first five arms still did not reach. :8344 is the
    // consolidation's location read and :8347 is its retry when `entity_id`
    // is absent -- a copy of the tenant filter that executes only on a
    // half-migrated app, inside a branch that attributes money to entities.
    // The wrapper is scoped to rf_locations so the rf_entities read above it
    // still succeeds and the branch actually gets this far.
    const seeded = [
      rlLoc(HASH_A, 'ENT-A'), rlLoc(HASH_B, 'ENT-B'),
      rlEntity(HASH_A, 'ENT-A'), rlEntity(HASH_B, 'ENT-B')
    ];
    const { res, calls } = await callMissingColumn(HASH_A,
      { action: 'consolidate', resource: 'rf_entities', payload: {} },
      seeded, 'rf_locations');
    assert.ok(calls.some(function (c) { return c.forced400; }),
      'the entity-column select was never refused, so the fallback did not run '
      + 'and this arm is testing the same line as [L-entities]');
    const locCalls = calls.filter(function (c) {
      return /rf_locations\?/.test(c.url) && !c.forced400; });
    assert.ok(locCalls.length > 0,
      'the consolidation made no fallback rf_locations read -- exit '
      + res.statusCode + ' ' + JSON.stringify(res.body && res.body.error));
    locCalls.forEach(function (c) {
      assert.ok(c.url.indexOf('license_hash=eq.' + HASH_A) !== -1,
        'the consolidation fallback location read carried no tenant filter: '
        + c.url);
    });
  });

  if (UNREACHED.length) {
    console.log('\nUNREACHED -- arms that never got to the tenant filter:');
    UNREACHED.forEach(function (u) { console.log('  %s -> %s %s', u[0], u[1], u[2]); });
    console.log('These are NOT isolation failures and NOT passes.');
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
