// api/sd-data-appointments-photos.test.js
// Plain node:assert tests. Run: node api/sd-data-appointments-photos.test.js
//
// Regression test for the 2026-08-12 stored-XSS fix: api/sd-data.js's
// generic dnt_appointments write path previously applied zero validation
// to payload.photos, unlike api/sairndental/public-book.js (the only other
// writer of this field), which always validated via validatePhotosPayload().
// sairndental.html's rPending() renders each photo's data URL directly into
// an <img src="..."> attribute -- safe only because public-book.js's regex
// forbids ", <, > from ever appearing in a stored photo. This generic write
// path let any holder of a valid license key bypass that regex entirely and
// plant a stored-XSS payload that would fire in another staff member's
// (including the owner's) authenticated session. Fixed by applying the same
// validatePhotosPayload() check here, at the source, independent of the
// render-side H() escaping fix in sairndental.html.

const assert = require('assert');

function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (code) { res.statusCode = code; return res; };
  res.json = function (payload) { res.body = payload; return res; };
  return res;
}
function mockReq(body, authz) {
  return { method: 'POST', headers: authz ? { authorization: authz } : {}, body: body };
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
  console.log('api/sd-data.js -- dnt_appointments photos validation (stored-XSS regression)');

  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  await test('a photo payload that could break out of the <img src="..."> attribute -> 400 INVALID_PHOTO, never touches the network', async () => {
    delete require.cache[require.resolve('./_lib/license')];
    require.cache[require.resolve('./_lib/license')] = {
      exports: {
        validateLicenseKey: async function () {
          return { valid: true, active: true, license_hash: 'test-hash', trial_ends_at: null, stripe_subscription_id: null };
        }
      }
    };
    global.fetch = async function () { throw new Error('fetch should never be called once photo validation rejects the payload'); };
    delete require.cache[require.resolve('./sd-data.js')];
    var handler = require('./sd-data.js');
    var res = mockRes();
    var maliciousPayload = { id: 'AP-1', photos: ['"><img src=x onerror=alert(document.cookie)>'] };
    await handler(mockReq({ action: 'write', resource: 'dnt_appointments', payload: maliciousPayload }, 'Bearer GOOD-KEY'), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'INVALID_PHOTO');
  });

  await test('too many photos -> 400 TOO_MANY_PHOTOS, never touches the network', async () => {
    delete require.cache[require.resolve('./_lib/license')];
    require.cache[require.resolve('./_lib/license')] = {
      exports: {
        validateLicenseKey: async function () {
          return { valid: true, active: true, license_hash: 'test-hash', trial_ends_at: null, stripe_subscription_id: null };
        }
      }
    };
    global.fetch = async function () { throw new Error('fetch should never be called once photo validation rejects the payload'); };
    delete require.cache[require.resolve('./sd-data.js')];
    var handler = require('./sd-data.js');
    var res = mockRes();
    var onePixel = 'data:image/jpeg;base64,AAAA';
    var payload = { id: 'AP-2', photos: [onePixel, onePixel, onePixel, onePixel] };
    await handler(mockReq({ action: 'write', resource: 'dnt_appointments', payload: payload }, 'Bearer GOOD-KEY'), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'TOO_MANY_PHOTOS');
  });

  await test('a well-formed photos payload (or none at all) still reaches the real write', async () => {
    delete require.cache[require.resolve('./_lib/license')];
    require.cache[require.resolve('./_lib/license')] = {
      exports: {
        validateLicenseKey: async function () {
          return { valid: true, active: true, license_hash: 'test-hash', trial_ends_at: null, stripe_subscription_id: null };
        }
      }
    };
    var fetchCalled = false;
    global.fetch = async function () {
      fetchCalled = true;
      return { ok: true, status: 200, json: async function () { return [{ data: { id: 'AP-3' } }]; } };
    };
    delete require.cache[require.resolve('./sd-data.js')];
    var handler = require('./sd-data.js');
    var res = mockRes();
    var payload = { id: 'AP-3', photos: ['data:image/jpeg;base64,AAAA'] };
    await handler(mockReq({ action: 'write', resource: 'dnt_appointments', payload: payload }, 'Bearer GOOD-KEY'), res);
    assert.strictEqual(fetchCalled, true);
    assert.strictEqual(res.statusCode, 200);
  });

  console.log(passed + ' passed');
}

main();
