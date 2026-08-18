// api/sairncash/trial-renew.test.js
// Plain node:assert tests -- no test framework, matching
// send-reminder.test.js's convention exactly (same auth-gate class of
// endpoint: a shared-secret Bearer check that returns before any
// network call, genuinely testable without mocking Supabase).
// Run: node api/sairncash/trial-renew.test.js

const assert = require('assert');

var ADMIN_SECRET_ENV_NAME = 'SAIRNCASH_ADMIN_SECRET';
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
  console.log('api/sairncash/trial-renew.js');

  await test('missing SAIRNCASH_ADMIN_SECRET env var -> 500, never reaches the auth check', async () => {
    clearEnv(ADMIN_SECRET_ENV_NAME);
    delete require.cache[require.resolve('./trial-renew.js')];
    var handler = require('./trial-renew.js');
    var res = mockRes();
    await handler({ method: 'POST', headers: {}, body: {} }, res);
    assert.strictEqual(res.statusCode, 500);
  });

  await test('secret set, no Authorization header -> 401', async () => {
    setFixtureEnv(ADMIN_SECRET_ENV_NAME, fixtureValue);
    delete require.cache[require.resolve('./trial-renew.js')];
    var handler = require('./trial-renew.js');
    var res = mockRes();
    await handler({ method: 'POST', headers: {}, body: {} }, res);
    assert.strictEqual(res.statusCode, 401);
  });

  await test('secret set, wrong Authorization header -> 401', async () => {
    setFixtureEnv(ADMIN_SECRET_ENV_NAME, fixtureValue);
    delete require.cache[require.resolve('./trial-renew.js')];
    var handler = require('./trial-renew.js');
    var res = mockRes();
    await handler({ method: 'POST', headers: { authorization: 'Bearer wrong-value' }, body: {} }, res);
    assert.strictEqual(res.statusCode, 401);
  });

  await test('non-POST method -> 405, checked before the auth gate', async () => {
    setFixtureEnv(ADMIN_SECRET_ENV_NAME, fixtureValue);
    delete require.cache[require.resolve('./trial-renew.js')];
    var handler = require('./trial-renew.js');
    var res = mockRes();
    await handler({ method: 'GET', headers: { authorization: 'Bearer ' + fixtureValue }, body: {} }, res);
    assert.strictEqual(res.statusCode, 405);
  });

  console.log(passed + ' passed');
}

main();
