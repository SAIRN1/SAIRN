// api/sairndental/public-complaint-thread.test.js
// Plain node:assert tests. Run: node api/sairndental/public-complaint-thread.test.js

const assert = require('assert');

function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (code) { res.statusCode = code; return res; };
  res.json = function (payload) { res.body = payload; return res; };
  res.setHeader = function (key, value) { return res; };
  res.end = function () { return res; };
  return res;
}
function mockReq(body) {
  return { method: 'POST', headers: {}, body: body };
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
  console.log('api/sairndental/public-complaint-thread.js');

  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  await test('missing token -> 400, never calls fetch', async () => {
    delete require.cache[require.resolve('../_lib/dental-public')];
    require.cache[require.resolve('../_lib/dental-public')] = { exports: { checkAndIncrementRateLimit: async function () { return { allowed: true }; } } };
    global.fetch = function () { throw new Error('fetch should never be called for a request that fails validation'); };
    delete require.cache[require.resolve('./public-complaint-thread.js')];
    var handler = require('./public-complaint-thread.js');
    var res = mockRes();
    await handler(mockReq({}), res);
    assert.strictEqual(res.statusCode, 400);
  });

  await test('unknown token -> 404 UNKNOWN_TOKEN', async () => {
    delete require.cache[require.resolve('../_lib/dental-public')];
    require.cache[require.resolve('../_lib/dental-public')] = { exports: { checkAndIncrementRateLimit: async function () { return { allowed: true }; } } };
    global.fetch = async function () { return { ok: true, json: async function () { return []; } }; };
    delete require.cache[require.resolve('./public-complaint-thread.js')];
    var handler = require('./public-complaint-thread.js');
    var res = mockRes();
    await handler(mockReq({ token: 'no-such-token' }), res);
    assert.strictEqual(res.statusCode, 404);
    assert.strictEqual(res.body.error.code, 'UNKNOWN_TOKEN');
  });

  await test('reply over 4000 chars -> 400 MESSAGE_TOO_LONG, never calls fetch', async () => {
    delete require.cache[require.resolve('../_lib/dental-public')];
    require.cache[require.resolve('../_lib/dental-public')] = { exports: { checkAndIncrementRateLimit: async function () { throw new Error('should not be called -- length check comes first'); } } };
    global.fetch = function () { throw new Error('fetch should never be called for a request that fails validation'); };
    delete require.cache[require.resolve('./public-complaint-thread.js')];
    var handler = require('./public-complaint-thread.js');
    var res = mockRes();
    await handler(mockReq({ token: 'tok-1', reply: 'x'.repeat(4001) }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'MESSAGE_TOO_LONG');
  });

  await test('reply rate-limited -> 429, never calls fetch', async () => {
    delete require.cache[require.resolve('../_lib/dental-public')];
    require.cache[require.resolve('../_lib/dental-public')] = { exports: { checkAndIncrementRateLimit: async function () { return { allowed: false }; } } };
    global.fetch = function () { throw new Error('fetch should never be called once rate-limited'); };
    delete require.cache[require.resolve('./public-complaint-thread.js')];
    var handler = require('./public-complaint-thread.js');
    var res = mockRes();
    await handler(mockReq({ token: 'tok-1', reply: 'hi' }), res);
    assert.strictEqual(res.statusCode, 429);
    assert.strictEqual(res.body.error.code, 'RATE_LIMITED');
  });

  await test('load-only (no reply) never rate-limit-checked', async () => {
    var rlCalled = false;
    delete require.cache[require.resolve('../_lib/dental-public')];
    require.cache[require.resolve('../_lib/dental-public')] = { exports: { checkAndIncrementRateLimit: async function () { rlCalled = true; return { allowed: true }; } } };
    global.fetch = async function () { return { ok: true, json: async function () { return [{ license_hash: 'h', complaint_id: 'COMP-1', data: { status: 'New', patient_name: '', messages: [] } }]; } }; };
    delete require.cache[require.resolve('./public-complaint-thread.js')];
    var handler = require('./public-complaint-thread.js');
    var res = mockRes();
    await handler(mockReq({ token: 'tok-1' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(rlCalled, false);
  });

  console.log(passed + ' passed');
}

main();
