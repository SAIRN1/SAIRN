// api/sairndental/public-complaint-submit.test.js
// Plain node:assert tests -- no test framework, matching
// api/sairndental/public-book.test.js's existing convention.
// Run: node api/sairndental/public-complaint-submit.test.js
//
// Covers only the pre-network-call validation paths (required fields,
// message length cap, rate limiting). The full
// resolveSlug -> Supabase insert flow needs a real Supabase
// environment and is covered by Task 10's live verification instead.

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
  console.log('api/sairndental/public-complaint-submit.js');

  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  delete require.cache[require.resolve('../_lib/dental-public')];
  require.cache[require.resolve('../_lib/dental-public')] = {
    exports: {
      resolveSlug: function () { throw new Error('resolveSlug should not be called in validation tests'); },
      checkAndIncrementRateLimit: async function () { return { allowed: true }; }
    }
  };
  global.fetch = function () { throw new Error('fetch should never be called for a request that fails validation'); };
  delete require.cache[require.resolve('./public-complaint-submit.js')];
  var handler = require('./public-complaint-submit.js');

  await test('missing slug -> 400, never calls fetch', async () => {
    var res = mockRes();
    await handler(mockReq({ message: 'Hello' }), res);
    assert.strictEqual(res.statusCode, 400);
  });

  await test('missing message -> 400, never calls fetch', async () => {
    var res = mockRes();
    await handler(mockReq({ slug: 'test-practice' }), res);
    assert.strictEqual(res.statusCode, 400);
  });

  await test('message over 4000 chars -> 400 MESSAGE_TOO_LONG, never calls fetch', async () => {
    var res = mockRes();
    await handler(mockReq({ slug: 'test-practice', message: 'x'.repeat(4001) }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'MESSAGE_TOO_LONG');
  });

  await test('rate-limited -> 429, never calls fetch', async () => {
    require.cache[require.resolve('../_lib/dental-public')].exports.checkAndIncrementRateLimit = async function () { return { allowed: false }; };
    delete require.cache[require.resolve('./public-complaint-submit.js')];
    var rlHandler = require('./public-complaint-submit.js');
    var res = mockRes();
    await rlHandler(mockReq({ slug: 'test-practice', message: 'Hello' }), res);
    assert.strictEqual(res.statusCode, 429);
    assert.strictEqual(res.body.error.code, 'RATE_LIMITED');
  });

  await test('field-whitelist regression (design spec §1/§7): happy-path insert payload.data has exactly {id, patient_name, status, messages, created_at}, nothing else', async () => {
    var capturedBody = null;
    delete require.cache[require.resolve('../_lib/dental-public')];
    require.cache[require.resolve('../_lib/dental-public')] = {
      exports: {
        resolveSlug: async function () { return 'hash-abc'; },
        checkAndIncrementRateLimit: async function () { return { allowed: true }; }
      }
    };
    global.fetch = async function (url, opts) {
      capturedBody = JSON.parse(opts.body);
      return { ok: true, json: async function () { return [capturedBody]; }, text: async function () { return ''; } };
    };
    delete require.cache[require.resolve('./public-complaint-submit.js')];
    var handler = require('./public-complaint-submit.js');
    var res = mockRes();
    await handler(mockReq({ slug: 'test-practice', message: 'Front desk was rude', patient_name: 'Jane' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.ok(res.body.token, 'expected a token in the response');
    assert.ok(capturedBody, 'expected fetch to have been called with a body');
    var dataKeys = Object.keys(capturedBody.data).sort();
    assert.deepStrictEqual(dataKeys, ['created_at', 'id', 'messages', 'patient_name', 'status']);
    assert.strictEqual(capturedBody.data.status, 'New');
    assert.strictEqual(capturedBody.data.messages.length, 1);
    assert.strictEqual(capturedBody.data.messages[0].from, 'patient');
    assert.strictEqual(capturedBody.data.messages[0].text, 'Front desk was rude');
  });

  console.log(passed + ' passed');
}

main();
