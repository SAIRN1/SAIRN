// api/legal-citator-feedback-attribution.test.js
//
// REQUIREMENT: a cl_feedback_log row records WHICH EMPLOYEE confirmed or
//   corrected a legal-treatment classification when the request carried a
//   signed-in session -- and records NULL, explicitly, when it did not.
//
// Run:  node api/legal-citator-feedback-attribution.test.js
//
// ── THE DEFECT THIS HOLDS (hover2 seq 951, found 2026-10-06) ──────────────
// `logRec` was built in the same function as `auditLookup()`, from the same
// `caller` variable resolved at api/legal-citator.js:184, and did not include
// employee_id at all. sql/sairnlaw_citator_schema.sql's cl_feedback_log had no
// employee column either, and the comment three lines above that table said
// "individual feedback stays attributable". Every row was attributable to a
// FIRM and to nobody -- an attorney confirming a classification other
// attorneys then rely on was unrecoverable. Not wrong; never captured.
//
// ── WHY THE NULL ARM IS AS IMPORTANT AS THE NAMED ARM ─────────────────────
// This endpoint's access control is the bearer licence key and the session
// token is OPTIONAL by design (api/legal-citator.js:178-183 says so, and
// why). So a row legitimately CAN have no person on it. A fix that invented a
// value for that case -- the firm owner, the licence, a placeholder string --
// would be worse than the omission, because it would read as evidence. The
// arms below assert the key is PRESENT and the value is NULL, which is a
// different claim from the key being absent.
//
// ── THE MIGRATION ARM IS WHY THIS FILE IS NOT TWO ASSERTIONS ──────────────
// The two columns arrive only via an `alter table` -- `create table if not
// exists` does nothing to a table that already exists -- so on any install
// running an earlier version of that schema file, PostgREST answers 400
// PGRST204 for an unknown column. "Data store error - try again" is advice
// that can never work. The arm drives the 503 and checks it names the file.
//
// ── WHAT THIS DOES NOT DO ─────────────────────────────────────────────────
// It does not test Supabase, it does not test the counter PATCH on
// cl_citing_treatments beyond letting it succeed, and it does NOT verify the
// SQL file against a real database -- the schema half of this fix is
// unverified against a live install by this suite and is stated as such
// rather than implied by a green run.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['citator', 'feedback', 'attribution', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const { signSessionToken } = require('./_lib/auth');

const HASH = 'law-firm-hash';
const APP = 'sairnlaw';
const TREATMENT_ID = '00000000-0000-4000-8000-000000000001';

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

// ── THE MOCK ──────────────────────────────────────────────────────────────
// Records every POST body so the arms can assert on the ROW THAT WOULD BE
// WRITTEN rather than on the handler's 200. `feedbackFails` lets one arm
// drive the unknown-column path instead of asserting the branch exists.
function sbMock(calls, opts) {
  const o = opts || {};
  return async function (url, init) {
    const u = String(url);
    calls.push({ url: u, init: init || null });
    if (/license_keys/.test(u)) {
      return { ok: true, status: 200, json: async function () {
        return [{ license_hash: HASH, active: true, app_id: APP }]; } };
    }
    if (/cl_feedback_log/.test(u)) {
      if (o.feedbackFails) {
        return { ok: false, status: o.feedbackStatus || 400,
                 text: async function () { return o.feedbackBody || ''; },
                 json: async function () { return {}; } };
      }
      return { ok: true, status: 201, text: async function () { return ''; },
               json: async function () { return []; } };
    }
    if (/cl_citing_treatments/.test(u)) {
      return { ok: true, status: 200, text: async function () { return ''; },
               json: async function () { return [{ feedback_confirm_count: 4,
                                                   feedback_correct_count: 1 }]; } };
    }
    if (/audit/.test(u)) {
      return { ok: true, status: 201, text: async function () { return ''; },
               json: async function () { return []; } };
    }
    return { ok: true, status: 200, text: async function () { return ''; },
             json: async function () { return []; } };
  };
}

// Fresh per call, with the REAL api/_lib/auth: the employee_id and role this
// suite is about arrive inside a signed token, and a stub there would be
// asserting the fixture rather than the handler.
function loadHandler(fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: HASH,
                 trial_ends_at: null, stripe_subscription_id: null, app_id: APP };
      }
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./legal-citator.js')];
  return require('./legal-citator.js');
}

function req(body, session) {
  const headers = { authorization: 'Bearer KEY-FOR-' + HASH };
  if (session) {
    headers['x-sd-auth'] = signSessionToken({
      app: APP, employee_id: session.employee_id, role: session.role,
      license_hash: HASH });
  }
  return { method: 'POST', headers: headers, body: body };
}

async function feedback(session, body, opts) {
  const calls = [];
  const h = loadHandler(sbMock(calls, opts));
  const res = mockRes();
  await h(req(Object.assign({ action: 'feedback', treatment_id: TREATMENT_ID,
                              feedback_action: 'confirmed' }, body || {}),
             session), res);
  return { res: res, calls: calls };
}

function feedbackRow(calls) {
  const c = calls.filter(function (x) {
    return /cl_feedback_log/.test(x.url) && x.init && x.init.method === 'POST';
  })[0];
  assert.ok(c, 'no POST to cl_feedback_log was made at all. Calls: '
    + JSON.stringify(calls.map(function (x) { return x.url; })));
  return JSON.parse(c.init.body);
}

(async function () {
  console.log('legal-citator feedback -- employee attribution (hover2 seq 951)');

  section('A SIGNED-IN EMPLOYEE -- the half that was missing entirely');

  await test('the row NAMES the employee who confirmed the classification',
    async () => {
      const { res, calls } = await feedback(
        { employee_id: 'emp-attorney-3', role: 'attorney' });
      assert.strictEqual(res.statusCode, 200,
        'the feedback action answered ' + res.statusCode + ' '
        + JSON.stringify(res.body) + ' -- this arm never reached the insert.');
      const row = feedbackRow(calls);
      assert.strictEqual(row.employee_id, 'emp-attorney-3',
        'cl_feedback_log row carried employee_id ' + JSON.stringify(row.employee_id)
        + '. The caller is resolved at api/legal-citator.js:184 and used by '
        + 'auditLookup() for every other action; this row is built in the same '
        + 'function from the same variable. Row: ' + JSON.stringify(row));
    });

  await test('...and their ROLE, because "an attorney confirmed this" and "a '
    + 'paralegal confirmed this" are different facts about the same row',
    async () => {
      const { calls } = await feedback(
        { employee_id: 'emp-attorney-3', role: 'attorney' });
      assert.strictEqual(feedbackRow(calls).employee_role, 'attorney',
        'employee_role came back ' + JSON.stringify(feedbackRow(calls).employee_role));
    });

  await test('...and nothing else about the row changed -- the fields that '
    + 'were already right are still right', async () => {
      const { calls } = await feedback(
        { employee_id: 'emp-attorney-3', role: 'attorney' },
        { feedback_action: 'corrected', corrected_to: 'distinguished',
          note: 'the holding was narrowed, not overruled' });
      const row = feedbackRow(calls);
      assert.strictEqual(row.license_hash, HASH, JSON.stringify(row));
      assert.strictEqual(row.app_id, APP, JSON.stringify(row));
      assert.strictEqual(row.treatment_id, TREATMENT_ID, JSON.stringify(row));
      assert.strictEqual(row.action, 'corrected', JSON.stringify(row));
      assert.strictEqual(row.corrected_to, 'distinguished', JSON.stringify(row));
      assert.strictEqual(row.note, 'the holding was narrowed, not overruled',
        JSON.stringify(row));
    });

  section('NO SESSION -- NULL is the right answer and must be WRITTEN, not '
    + 'omitted');

  await test('the key is PRESENT and the value is NULL, which is a different '
    + 'claim from the key being absent', async () => {
      const { res, calls } = await feedback(null);
      assert.strictEqual(res.statusCode, 200,
        'a session-less feedback answered ' + res.statusCode + ' '
        + JSON.stringify(res.body) + '. The session token is OPTIONAL on this '
        + 'endpoint by design -- requiring one here would be a different change '
        + 'from the one this suite covers.');
      const row = feedbackRow(calls);
      assert.ok('employee_id' in row,
        'employee_id is absent from the row rather than null. Row: '
        + JSON.stringify(row));
      assert.strictEqual(row.employee_id, null,
        'employee_id is ' + JSON.stringify(row.employee_id) + ' for a request '
        + 'with no session. Inventing a value -- the owner, the licence, a '
        + 'placeholder -- would be worse than the original omission, because it '
        + 'would read as evidence.');
      assert.strictEqual(row.employee_role, null, JSON.stringify(row));
    });

  section('THE MIGRATION -- the two columns arrive via `alter table`, and '
    + '`create table if not exists` does nothing to a live table');

  await test('an unknown-column 400 is reported as NOT_PROVISIONED naming the '
    + 'SQL file, not as "try again"', async () => {
      const { res } = await feedback(
        { employee_id: 'emp-1', role: 'owner' }, null,
        { feedbackFails: true, feedbackStatus: 400,
          feedbackBody: '{"code":"PGRST204","message":"Could not find the '
            + '\'employee_id\' column of \'cl_feedback_log\' in the schema cache"}' });
      assert.strictEqual(res.statusCode, 503,
        'answered ' + res.statusCode + ' ' + JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'NOT_PROVISIONED',
        JSON.stringify(res.body));
      assert.ok(/sairnlaw_citator_schema\.sql/.test(res.body.error.message),
        'the refusal does not name the file to run: '
        + JSON.stringify(res.body.error.message) + '. "Try again" is advice that '
        + 'can never work for a migration that has not run.');
      assert.ok(/[Nn]othing was recorded/.test(res.body.error.message),
        'the refusal does not say nothing was recorded: '
        + JSON.stringify(res.body.error.message));
    });

  await test('NEGATIVE HALF: an unrelated insert failure is still a 502, so '
    + 'the new branch did not swallow every error into NOT_PROVISIONED',
    async () => {
      const { res } = await feedback(
        { employee_id: 'emp-1', role: 'owner' }, null,
        { feedbackFails: true, feedbackStatus: 500,
          feedbackBody: 'upstream exploded' });
      assert.strictEqual(res.statusCode, 502,
        'answered ' + res.statusCode + ' ' + JSON.stringify(res.body)
        + '. A 500 from the data store is not a missing migration, and reporting '
        + 'it as one would send an operator to run SQL that is already applied.');
    });

  section('NEGATIVE CONTROLS');

  await test('the mock really does capture the POST body -- otherwise every '
    + 'arm above is asserting on a fixture', async () => {
      const calls = [];
      const f = sbMock(calls, {});
      await f('https://x/rest/v1/cl_feedback_log',
              { method: 'POST', body: JSON.stringify({ probe: 1 }) });
      assert.strictEqual(feedbackRow(calls).probe, 1,
        'feedbackRow() did not read back what was posted: '
        + JSON.stringify(calls));
    });

  await test('a bad feedback_action is still rejected at 400 before any row is '
    + 'written -- the validation this branch already had', async () => {
      const { res, calls } = await feedback(
        { employee_id: 'emp-1', role: 'owner' },
        { feedback_action: 'maybe' });
      assert.strictEqual(res.statusCode, 400,
        'answered ' + res.statusCode + ' ' + JSON.stringify(res.body));
      assert.ok(!calls.some(function (x) {
        return /cl_feedback_log/.test(x.url) && x.init && x.init.method === 'POST';
      }), 'a rejected feedback_action still wrote a row: '
        + JSON.stringify(calls.map(function (x) { return x.url; })));
    });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
