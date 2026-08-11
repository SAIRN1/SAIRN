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
    clearEnv('RESEND_FROM_ADDRESS');
    delete require.cache[require.resolve('./send-reminder.js')];
    var handler = require('./send-reminder.js');
    var res = mockRes();
    await handler({ headers: { authorization: 'Bearer ' + fixtureValue } }, res);
    assert.strictEqual(res.statusCode, 500);
  });

  console.log(passed + ' passed' + (process.exitCode ? ', with failures above' : ''));
}

main();
