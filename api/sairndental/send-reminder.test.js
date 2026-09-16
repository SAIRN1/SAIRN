// api/sairndental/send-reminder.test.js
// Plain node:assert tests -- no test framework, matching api/'s existing
// zero-npm-dependency convention (see api/_lib/auth.test.js).
// Run: node api/sairndental/send-reminder.test.js
//
// Covers only the auth-gate paths (the shared-secret check), which
// return before any network call -- genuinely testable without mocking
// fetch or a live Supabase/Resend connection. The full list-appointments
// -> send -> stamp flow needs a real (or live-mocked) Supabase + Resend
// environment and is covered by the plan's Task 6 live-verification
// steps instead, not here.

const assert = require('assert');

// THE CRON JITTER IS OFF IN TESTS, EXPLICITLY (2026-09-14). api/_lib/cron-jitter
// waits a bounded random interval before the appointment read so this job and
// /api/alf-alerts stop arriving at Supabase in the same instant. That is a
// PRODUCTION mitigation and tests should not pay for it: left on, this file
// took 17 seconds to make five assertions. Set here rather than detected inside
// the helper, because a helper that quietly behaves differently under test is a
// helper whose tested behaviour is not the shipped one.
process.env.SAIRN_CRON_JITTER_MS = '0';

var CRON_SECRET_ENV_NAME = 'CRON_' + 'SECRET';
// A fixture value for this local test process only -- never a real
// credential, deliberately generated at runtime so it can't be mistaken
// for one.
var fixtureValue = 'unit-test-fixture-' + Date.now() + '-' + Math.floor(Math.random() * 1e6);

function setFixtureEnv(name, value) { process.env[name] = value; }
function clearEnv(name) { delete process.env[name]; }

function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (code) { res.statusCode = code; return res; };
  res.json = function (payload) { res.body = payload; return res; };
  return res;
}

let passed = 0;
async function test(name, fn) {
  try {
    await fn();
    passed++;
    console.log('  ok - ' + name);
  } catch (err) {
    console.error('  FAIL - ' + name);
    console.error('    ' + err.message);
    process.exitCode = 1;
  }
}

async function main() {
  console.log('api/sairndental/send-reminder.js');

  await test('missing shared-secret env var -> 500, never reaches the auth check', async () => {
    clearEnv(CRON_SECRET_ENV_NAME);
    delete require.cache[require.resolve('./send-reminder.js')];
    var handler = require('./send-reminder.js');
    var res = mockRes();
    await handler({ headers: {} }, res);
    assert.strictEqual(res.statusCode, 500);
  });

  await test('shared-secret set, no Authorization header -> 401', async () => {
    setFixtureEnv(CRON_SECRET_ENV_NAME, fixtureValue);
    delete require.cache[require.resolve('./send-reminder.js')];
    var handler = require('./send-reminder.js');
    var res = mockRes();
    await handler({ headers: {} }, res);
    assert.strictEqual(res.statusCode, 401);
  });

  await test('shared-secret set, wrong Authorization header -> 401', async () => {
    setFixtureEnv(CRON_SECRET_ENV_NAME, fixtureValue);
    delete require.cache[require.resolve('./send-reminder.js')];
    var handler = require('./send-reminder.js');
    var res = mockRes();
    await handler({ headers: { authorization: 'Bearer not-' + fixtureValue } }, res);
    assert.strictEqual(res.statusCode, 401);
  });

  await test('shared-secret set, correct Authorization header, but no Supabase/Resend env -> 500 (never a false 200)', async () => {
    setFixtureEnv(CRON_SECRET_ENV_NAME, fixtureValue);
    clearEnv('SUPABASE_URL');
    clearEnv('SUPABASE_SERVICE_ROLE_KEY');
    clearEnv('RESEND_API_KEY');
    clearEnv('RESEND_FROM_EMAIL');
    delete require.cache[require.resolve('./send-reminder.js')];
    var handler = require('./send-reminder.js');
    var res = mockRes();
    await handler({ headers: { authorization: 'Bearer ' + fixtureValue } }, res);
    assert.strictEqual(res.statusCode, 500);
  });

  await test('the sender variable is RESEND_FROM_EMAIL, not the RESEND_FROM_ADDRESS that never existed', async () => {
    // The regression this file exists for as of 2026-08-24. RESEND_FROM_ADDRESS
    // has never been set in this Vercel project, so reading it made the guard
    // below fail on every single hourly firing since the file shipped -- the
    // cron 500'd for months and never sent one reminder. Setting only the four
    // REAL variable names must be enough to get past the config guard.
    setFixtureEnv(CRON_SECRET_ENV_NAME, fixtureValue);
    setFixtureEnv('SUPABASE_URL', 'https://fixture.invalid');
    setFixtureEnv('SUPABASE_SERVICE_ROLE_KEY', 'fixture-key');
    setFixtureEnv('RESEND_API_KEY', 'fixture-key');
    setFixtureEnv('RESEND_FROM_EMAIL', 'alerts@fixture.invalid');
    clearEnv('RESEND_FROM_ADDRESS');
    var realFetch = global.fetch;
    global.fetch = async function () { throw new Error('upstream unreachable in test'); };
    delete require.cache[require.resolve('./send-reminder.js')];
    var handler = require('./send-reminder.js');
    var res = mockRes();
    await handler({ headers: { authorization: 'Bearer ' + fixtureValue } }, res);
    global.fetch = realFetch;
    // 502/500 from the unreachable upstream is fine and expected. What must NOT
    // happen is the config guard rejecting a fully-configured environment.
    assert.notStrictEqual(res.statusCode, null);
    assert.ok(
      !res.body || !res.body.error || res.body.error.message !== 'Server configuration error',
      'a correctly configured environment must get past the config guard'
    );
  });

  // ── THE REFUSAL THAT ACTUALLY FAILED, TWENTY-THREE TIMES ────────────────
  // `dnt_appointments list failed 504` -- count=23 in Vercel's runtime-error
  // table between 2026-09-12 and 2026-09-14. Every one of those runs returned
  // 502 and wrote NO heartbeat.
  //
  // AND THE CONSEQUENCE WAS A FALSE GREEN, NOT A GAP, which makes this the
  // sharper half of the same defect found in api/audit-checkpoint.js on the
  // same day. That job refused on EVERY run, so it produced NEVER_BEAT --
  // visibly wrong. This one succeeds most hours and failed about one in three,
  // so the last successful beat stayed fresh and cron-watchdog reported
  // `/api/sairndental/send-reminder=ok` throughout. The failures were
  // invisible to the monitor and were found in the provider's error table
  // instead -- which is the work the heartbeat exists so nobody has to do.
  await test('A FAILED APPOINTMENT READ STILL BEATS -- a false green is worse '
    + 'than a gap', async () => {
    setFixtureEnv(CRON_SECRET_ENV_NAME, fixtureValue);
    setFixtureEnv('SUPABASE_URL', 'https://fixture.invalid');
    setFixtureEnv('SUPABASE_SERVICE_ROLE_KEY', 'fixture-key');
    setFixtureEnv('RESEND_API_KEY', 'fixture-key');
    setFixtureEnv('RESEND_FROM_EMAIL', 'alerts@fixture.invalid');
    var beats = [];
    var realFetch = global.fetch;
    // The 504 that really happened, and a captured heartbeat table so a beat
    // can be OBSERVED rather than assumed. Without this the beat POST would
    // fall through to whatever the stub returns, beat() would swallow the
    // result by design, and no arm could tell a job that beat from one that
    // did not.
    global.fetch = async function (url, init) {
      if (String(url).indexOf('sairn_cron_heartbeat') !== -1) {
        beats.push(JSON.parse(init.body));
        return { ok: true, status: 201, text: async function () { return ''; } };
      }
      return { ok: false, status: 504,
               text: async function () { return 'Gateway Timeout'; },
               json: async function () { return {}; } };
    };
    delete require.cache[require.resolve('./send-reminder.js')];
    var handler = require('./send-reminder.js');
    var res = mockRes();
    await handler({ headers: { authorization: 'Bearer ' + fixtureValue } }, res);
    global.fetch = realFetch;
    assert.strictEqual(res.statusCode, 502);
    assert.strictEqual(beats.length, 1, 'it refused without beating');
    assert.strictEqual(beats[0].job, '/api/sairndental/send-reminder');
    assert.strictEqual(beats[0].outcome, 'failed',
      'nothing was scanned and nothing sent -- that is not `partial`');
    assert.strictEqual(beats[0].detail.error, 'APPOINTMENT_LIST_FAILED');
    assert.strictEqual(beats[0].detail.http, 504);
    assert.strictEqual(beats[0].expected_interval_seconds, 3600,
      'beat() refuses an intervalless beat outright, which would leave the '
      + 'job looking silent anyway');
  });

  // THE CONTROL. Without it the arm above is satisfied by a handler that beats
  // `failed` on every path, including a clean sweep.
  await test('CONTROL: a CLEAN sweep beats, and not as a failure', async () => {
    setFixtureEnv(CRON_SECRET_ENV_NAME, fixtureValue);
    var beats = [];
    var realFetch = global.fetch;
    global.fetch = async function (url, init) {
      if (String(url).indexOf('sairn_cron_heartbeat') !== -1) {
        beats.push(JSON.parse(init.body));
        return { ok: true, status: 201, text: async function () { return ''; } };
      }
      return { ok: true, status: 200,
               text: async function () { return '[]'; },
               json: async function () { return []; } };
    };
    delete require.cache[require.resolve('./send-reminder.js')];
    var handler = require('./send-reminder.js');
    var res = mockRes();
    await handler({ headers: { authorization: 'Bearer ' + fixtureValue } }, res);
    global.fetch = realFetch;
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(beats.length, 1);
    assert.strictEqual(beats[0].outcome, 'ok');
    assert.strictEqual(beats[0].detail.error, undefined,
      'a clean sweep is reporting an error');
  });

  console.log(passed + ' passed' + (process.exitCode ? ', with failures above' : ''));
}

main();
