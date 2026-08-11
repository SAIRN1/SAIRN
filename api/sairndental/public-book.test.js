// api/sairndental/public-book.test.js
// Plain node:assert tests -- no test framework, matching api/'s existing
// zero-npm-dependency convention (see api/_lib/auth.test.js).
// Run: node api/sairndental/public-book.test.js
//
// Covers only the pre-network-call validation paths (existing
// required-field check + the new photos validation). The full
// resolveSlug -> Supabase -> insert flow needs a real (or live-mocked)
// Supabase environment and is covered by the plan's Task 5 live
// verification instead, not here.

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

var VALID_BASE = {
  slug: 'test-practice', patient: { name: 'Jane Doe', dob: '1990-01-01', phone: '555-0100' },
  provider_id: 'PV-1', procedure_type_id: 'PC-1', start_time: '2026-08-13T14:00:00.000Z'
};

async function main() {
  console.log('api/sairndental/public-book.js');

  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  var originalFetch = global.fetch;
  var originalRequire = require;

  // Set up mocks before requiring public-book
  delete require.cache[require.resolve('../_lib/dental-public')];
  require.cache[require.resolve('../_lib/dental-public')] = {
    exports: {
      resolveSlug: function () { throw new Error('resolveSlug should not be called in validation tests'); },
      checkAndIncrementRateLimit: async function () { return { allowed: true }; }
    }
  };

  global.fetch = function () { throw new Error('fetch should never be called for a request that fails validation'); };
  delete require.cache[require.resolve('./public-book.js')];
  var handler = require('./public-book.js');

  await test('missing required field (existing regression: no patient.name) -> 400, never calls fetch', async () => {
    var res = mockRes();
    var body = Object.assign({}, VALID_BASE, { patient: { dob: '1990-01-01', phone: '555-0100' } });
    await handler(mockReq(body), res);
    assert.strictEqual(res.statusCode, 400);
  });

  await test('4 photos -> 400 TOO_MANY_PHOTOS, never calls fetch', async () => {
    var res = mockRes();
    var body = Object.assign({}, VALID_BASE, { photos: ['data:image/jpeg;base64,AAAA', 'data:image/jpeg;base64,AAAA', 'data:image/jpeg;base64,AAAA', 'data:image/jpeg;base64,AAAA'] });
    await handler(mockReq(body), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'TOO_MANY_PHOTOS');
  });

  await test('a malformed photo entry -> 400 INVALID_PHOTO, never calls fetch', async () => {
    var res = mockRes();
    var body = Object.assign({}, VALID_BASE, { photos: ['not-a-real-data-url'] });
    await handler(mockReq(body), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'INVALID_PHOTO');
  });

  await test('an oversized combined photos payload -> 400 PHOTOS_TOO_LARGE, never calls fetch', async () => {
    var res = mockRes();
    var big = 'data:image/jpeg;base64,' + 'A'.repeat(1.3 * 1024 * 1024);
    var body = Object.assign({}, VALID_BASE, { photos: [big] });
    await handler(mockReq(body), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'PHOTOS_TOO_LARGE');
  });

  global.fetch = originalFetch;
  console.log(passed + ' passed' + (process.exitCode ? ', with failures above' : ''));
}

main();
