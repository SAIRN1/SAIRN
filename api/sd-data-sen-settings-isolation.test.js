// api/sd-data-sen-settings-isolation.test.js
//
// REQUIREMENT: a valid, fully authenticated SAIRNsenior session for tenant A
//   cannot read or overwrite tenant B's agency settings.
//
// CROSS-TENANT-ISOLATION: sen_settings
//
// Run:  node api/sd-data-sen-settings-isolation.test.js
//
// ── WHY THIS IS NOT A ROW IN THE DISPATCHER SUITE ─────────────────────────
// api/sd-data-cross-tenant-dispatchers.test.js seeds an `owner` marker at the
// row level and inside `data`, and its [L] arm reads `x.owner` back off each
// returned item. This branch re-projects to
// `{setting_key, value, updated_by, updated_at}`, so `owner` does not survive
// the response at any level the shared probe can reach. `value` IS the stored
// `data` blob, and that is the one place a tenant marker gets through -- which
// is what every read arm below asserts on.
//
// ── THE COLLISION, WHICH IS THE WHOLE RISK ON A KEYED SETTINGS TABLE ──────
// The key is `setting_key`, and it is NOT per tenant. Every agency configures
// `evv_config` -- the state and aggregator its electronic-visit-verification
// records are transmitted under -- and every agency configures
// `agency_profile`. So two real rows in two different companies carry the SAME
// key, the same shape, and different contents.
//
// Drop `license_hash=eq.` and tenant A is not handed an empty screen or an
// obviously foreign record: it is handed TWO rows both keyed `evv_config`, and
// whichever one the client reads first decides which state's EVV rules this
// agency's visits are filed under. A count assertion cannot see that and
// neither can a shape assertion.
//
// ── THIS IS THE SECOND FILE FOR ONE SHAPE, AND THAT IS SAID RATHER THAN
// ── HIDDEN ───────────────────────────────────────────────────────────────
// `rf_settings` is byte-for-byte the same branch shape and is covered in
// api/sd-data-roofing-projected-isolation.test.js, which means this platform
// now has TWO suites carrying the same mock for the same pattern -- exactly
// what the dispatcher suite's own header warns about ("ten near-identical
// files would be ten places for the mock to drift").
//
// IT IS DELIBERATE AND IT IS TEMPORARY. That file is under an open
// independent-review obligation right now; moving arms out of a suite while
// somebody is reviewing it makes the review point at code that is no longer
// there. Consolidating the two keyed-settings suites into one shape-scoped
// file is the right end state and is deferred until that review closes --
// written here so the next reader finds a stated intention rather than
// duplication nobody noticed.
//
// ── WHAT THIS DOES NOT DO ─────────────────────────────────────────────────
// It does not test the DATABASE, and it does not test the ROLE gate (only
// senAuth.MANAGEMENT_ROLES may write a setting). That is a separate question
// with its own suite.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['sen', 'settings', 'isolation', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const { signSessionToken } = require('./_lib/auth');

const HASH_A = 'tenant-A-hash';
const HASH_B = 'tenant-B-hash';
const APP = 'sairnsenior';
const TABLE = 'sen_settings';

// The table this suite drives, in the shape
// tools/cross_tenant_isolation_scope.py cross-checks a declaration against.
// `owner` is in senAuth.MANAGEMENT_ROLES so it gets past the write gate; the
// READ branch has no role narrowing at all, so license_hash is the only thing
// that can shorten an answer either way.
const UNITS = [
  ['sen_settings', 'setting_key', 'owner']
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
// `license_hash=eq.` from the handler and there is no clause left to filter
// on, both tenants' rows come back, and the content assertions fail.
//
// IT HONOURS `select=`, because this branch asks for a named column list and
// the response is built from those fields. A mock handing back columns the
// real query never asked for would be testing a row shape the handler cannot
// receive.
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
    // A credential lookup is not the query under test, and it is answered FOR
    // THE TENANT IN THE QUERY so it stays tenant-scoped rather than becoming a
    // hole in the suite that needs it.
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
      if (!select || select.indexOf('*') !== -1) return r;
      const out = {};
      select.forEach(function (c) { if (c in r) out[c] = r[c]; });
      return out;
    });
    return { ok: true, status: 200, json: async function () { return matches; } };
  };
}

// Fresh per call, with the REAL api/_lib/auth: the licence-hash half of the
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

async function call(licHash, role, body, rows) {
  const calls = [];
  const h = loadHandler(licHash, postgrestMock(rows || [], calls));
  const res = mockRes();
  await h(mockReq(body, licHash, 'emp-1', role), res);
  return { res: res, calls: calls };
}

// A row in the shape the SELECT asks for. `data` carries the tenant marker
// because both tenants' rows deliberately share a `setting_key` and nothing
// else would tell them apart.
function setting(licHash, key, tenant) {
  return { license_hash: licHash, app_id: APP, setting_key: key,
           data: { tenant: tenant, state: 'OH', aggregator: 'other' },
           updated_by: 'emp-1', updated_at: '2026-09-01T00:00:00.000Z' };
}
function tenantsIn(res) {
  return ((res.body && res.body.data) || [])
    .map(function (r) { return r && r.value && r.value.tenant; })
    .sort();
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

(async function () {
  const [resource, keyCol, role] = UNITS[0];
  console.log('CROSS-TENANT ISOLATION -- ' + resource + ' (keyed on ' + keyCol
    + ', projected response)');

  section('READ -- both agencies configure the SAME key, which is the whole risk');

  await test(resource + ' [L-collide] tenant A gets ITS OWN evv_config, not the '
    + 'other agency\'s', async () => {
      const seeded = [setting(HASH_A, 'evv_config', 'A'),
                      setting(HASH_B, 'evv_config', 'B')];
      const { res, calls } = await call(HASH_A, role,
        { action: 'read', resource: resource }, seeded);
      reached(res, 'the tenant A read');
      assert.deepStrictEqual(tenantsIn(res), ['A'],
        'tenant A was handed ' + JSON.stringify(tenantsIn(res)) + '. BOTH rows are '
        + 'keyed "evv_config" in the same shape, so nothing about this answer LOOKS '
        + 'wrong -- only whose it is. A wrong one files an agency\'s '
        + 'electronic-visit-verification records under another state\'s aggregator.');
      assert.ok(calls.some(function (c) {
        return c.url.indexOf(TABLE + '?license_hash=eq.' + HASH_A) !== -1; }),
        'no query carried ' + TABLE + '?license_hash=eq.' + HASH_A + ': '
        + JSON.stringify(calls.map(function (c) { return c.url; })));
    });

  await test(resource + ' [L-rev] tenant B gets its own', async () => {
    // A handler hardcoded to one tenant passes the arm above and fails here.
    const seeded = [setting(HASH_A, 'evv_config', 'A'),
                    setting(HASH_B, 'evv_config', 'B')];
    const { res } = await call(HASH_B, role,
      { action: 'read', resource: resource }, seeded);
    reached(res, 'the tenant B read');
    assert.deepStrictEqual(tenantsIn(res), ['B'],
      'tenant B was handed ' + JSON.stringify(tenantsIn(res)));
  });

  await test(resource + ' [L] every one of A\'s keys comes back, and only A\'s',
    async () => {
      // Presence as well as absence: a filter on a column the fixtures do not
      // carry matches nothing and yields [], which an absence-only assertion
      // would pass for entirely the wrong reason.
      const seeded = [setting(HASH_A, 'evv_config', 'A'),
                      setting(HASH_A, 'agency_profile', 'A'),
                      setting(HASH_B, 'evv_config', 'B'),
                      setting(HASH_B, 'agency_profile', 'B')];
      const { res } = await call(HASH_A, role,
        { action: 'read', resource: resource }, seeded);
      reached(res, 'the two-key read');
      assert.deepStrictEqual(tenantsIn(res), ['A', 'A']);
      assert.deepStrictEqual(
        res.body.data.map(function (r) { return r.setting_key; }).sort(),
        ['agency_profile', 'evv_config']);
    });

  await test(resource + ' [L] no license_hash reaches the response body', async () => {
    // The named SELECT and the projection are what strip it. Widen that select
    // to `*`, or pass rows through unprojected, and every agency's tenant key
    // starts being served to a browser.
    const { res } = await call(HASH_A, role,
      { action: 'read', resource: resource }, [setting(HASH_A, 'evv_config', 'A')]);
    reached(res, 'the projection read');
    assert.ok(JSON.stringify(res.body).indexOf('license_hash') === -1,
      'the response body carries a license_hash: ' + JSON.stringify(res.body));
  });

  section('WRITE -- the conflict key, which is what keeps two agencies\' '
    + 'evv_config apart in storage');

  await test(resource + ' [W] A writing evv_config lands under A, not over B',
    async () => {
      const { res, calls } = await call(HASH_A, role,
        { action: 'write', resource: resource,
          payload: { setting_key: 'evv_config',
                     value: { state: 'OH', aggregator: 'other', tenant: 'A' } } }, []);
      const post = firstPost(calls);
      if (!post) {
        UNREACHED.push([resource + ' write', res.statusCode,
                        (res.body && res.body.error && res.body.error.code) || '']);
        assert.fail('UNREACHED: no upsert was sent; the handler answered '
          + res.statusCode + ' ' + JSON.stringify(res.body) + '. This arm never '
          + 'reached the conflict key, so it proves nothing.');
      }
      // Drop license_hash from this key and the two agencies SHARE one
      // evv_config row: tenant A's save does not corrupt tenant B's setting,
      // it BECOMES it, with a normal 200 either way.
      assert.ok(post.url.indexOf('on_conflict=license_hash,setting_key') !== -1,
        'the conflict key is not license_hash,setting_key: ' + post.url);
      const sent = JSON.parse(post.opts.body);
      assert.strictEqual(sent.license_hash, HASH_A,
        'the row was written under ' + JSON.stringify(sent.license_hash)
        + ' rather than the hash the handler derived from the bearer key');
      assert.strictEqual(sent.app_id, APP,
        'the app_id was taken from somewhere other than the branch itself');
    });

  await test(resource + ' [Winj] a payload license_hash and app_id are ignored',
    async () => {
      const { res, calls } = await call(HASH_A, role,
        { action: 'write', resource: resource,
          payload: { setting_key: 'evv_config', license_hash: HASH_B,
                     app_id: 'sairnbiz',
                     value: { state: 'OH', aggregator: 'other', tenant: 'A' } } }, []);
      const post = firstPost(calls);
      if (!post) {
        assert.fail('UNREACHED: no upsert; handler answered ' + res.statusCode
          + ' ' + JSON.stringify(res.body));
      }
      const sent = JSON.parse(post.opts.body);
      assert.strictEqual(sent.license_hash, HASH_A,
        'a license_hash INSIDE the payload reached the stored row as '
        + JSON.stringify(sent.license_hash));
      assert.strictEqual(sent.app_id, APP,
        'a payload app_id reached the stored row as ' + JSON.stringify(sent.app_id));
    });

  section('THE SESSION HALF -- a token minted for the other tenant, and for '
    + 'another app');

  await test(resource + ' [S] tenant B\'s token against tenant A\'s licence is refused',
    async () => {
      const calls = [];
      const h = loadHandler(HASH_A, postgrestMock(
        [setting(HASH_A, 'evv_config', 'A')], calls));
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
      assert.ok(!calls.some(function (c) { return c.url.indexOf(TABLE) !== -1; }),
        'the refused request still queried ' + TABLE);
    });

  await test(resource + ' [S] a SAIRNbiz token for the same tenant is refused',
    async () => {
      // Guardian Check 28's collision: without the third argument to
      // verifySessionToken a genuine session for another SAIRN app under the
      // same licence would reach this branch.
      const calls = [];
      const h = loadHandler(HASH_A, postgrestMock(
        [setting(HASH_A, 'evv_config', 'A')], calls));
      const res = mockRes();
      await h({ method: 'POST',
                headers: { authorization: 'Bearer KEY-FOR-' + HASH_A,
                           'x-sd-auth': signSessionToken({
                             app: 'sairnbiz', employee_id: 'emp-1', role: 'owner',
                             license_hash: HASH_A }) },
                body: { action: 'read', resource: resource } }, res);
      assert.strictEqual(res.statusCode, 401,
        'a SAIRNbiz session reached SAIRNsenior\'s agency settings: '
        + res.statusCode + ' ' + JSON.stringify(res.body));
      assert.ok(!calls.some(function (c) { return c.url.indexOf(TABLE) !== -1; }),
        'the refused request still queried ' + TABLE);
    });

  // ── THE NEGATIVE CONTROL ON THE MOCK ITSELF ─────────────────────────────
  section('THE NEGATIVE CONTROL -- the mock still distinguishes filtered from '
    + 'unfiltered, ANDs its clauses, and projects');
  await test('an unfiltered query returns BOTH tenants', async () => {
    const seeded = [setting(HASH_A, 'evv_config', 'A'),
                    setting(HASH_B, 'evv_config', 'B')];
    const f = postgrestMock(seeded, []);
    const unfiltered = await (await f('https://x/rest/v1/' + TABLE)).json();
    assert.strictEqual(unfiltered.length, 2,
      'the mock returned ' + unfiltered.length + ' rows for a query with NO eq. '
      + 'clauses. It is not filtering, so every arm above proves nothing.');
    const filtered = await (await f('https://x/rest/v1/' + TABLE
      + '?license_hash=eq.' + HASH_A)).json();
    assert.strictEqual(filtered.length, 1);
    const both = await (await f('https://x/rest/v1/' + TABLE + '?license_hash=eq.'
      + HASH_A + '&setting_key=eq.nothing')).json();
    assert.strictEqual(both.length, 0,
      'two eq. clauses must be ANDed: A\'s hash with an absent key matches nothing');
  });

  await test('the mock honours select= -- so the projection assertion is real',
    async () => {
      const f = postgrestMock([setting(HASH_A, 'evv_config', 'A')], []);
      const projected = await (await f('https://x/rest/v1/' + TABLE
        + '?license_hash=eq.' + HASH_A + '&select=setting_key,data')).json();
      assert.deepStrictEqual(Object.keys(projected[0]).sort(), ['data', 'setting_key'],
        'the mock ignored select= and returned '
        + JSON.stringify(Object.keys(projected[0])) + '. The "no license_hash in the '
        + 'body" arm would then be asserting that the handler drops a column the '
        + 'mock never sent, which is not the claim.');
    });

  if (UNREACHED.length) {
    console.log('\nUNREACHED -- arms that never got to the tenant filter:');
    UNREACHED.forEach(function (u) { console.log('  %s -> %s %s', u[0], u[1], u[2]); });
    console.log('These are NOT isolation failures and NOT passes.');
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
