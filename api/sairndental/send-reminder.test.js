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

  console.log(passed + ' passed' + (process.exitCode ? ', with failures above' : ''));
}

main();
