// api/sairndental/complaint-respond.test.js
// Plain node:assert tests. Run: node api/sairndental/complaint-respond.test.js

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
  console.log('api/sairndental/complaint-respond.js');

  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  await test('missing Authorization header -> 401 NO_LICENSE', async () => {
    delete require.cache[require.resolve('../_lib/license')];
    require.cache[require.resolve('../_lib/license')] = { exports: { validateLicenseKey: async function () { throw new Error('should not be called with no header'); } } };
    delete require.cache[require.resolve('./complaint-respond.js')];
    var handler = require('./complaint-respond.js');
    var res = mockRes();
    await handler(mockReq({ complaint_id: 'COMP-1', action: 'reply', text: 'hi' }), res);
    assert.strictEqual(res.statusCode, 401);
    assert.strictEqual(res.body.error.code, 'NO_LICENSE');
  });

  await test('invalid license -> 401 INVALID_LICENSE', async () => {
    delete require.cache[require.resolve('../_lib/license')];
    require.cache[require.resolve('../_lib/license')] = { exports: { validateLicenseKey: async function () { return { valid: false }; } } };
    delete require.cache[require.resolve('./complaint-respond.js')];
    var handler = require('./complaint-respond.js');
    var res = mockRes();
    await handler(mockReq({ complaint_id: 'COMP-1', action: 'reply', text: 'hi' }, 'Bearer BAD-KEY'), res);
    assert.strictEqual(res.statusCode, 401);
    assert.strictEqual(res.body.error.code, 'INVALID_LICENSE');
  });

  await test('inactive license -> 403 LICENSE_INACTIVE', async () => {
    delete require.cache[require.resolve('../_lib/license')];
    require.cache[require.resolve('../_lib/license')] = { exports: { validateLicenseKey: async function () { return { valid: true, active: false }; } } };
    delete require.cache[require.resolve('./complaint-respond.js')];
    var handler = require('./complaint-respond.js');
    var res = mockRes();
    await handler(mockReq({ complaint_id: 'COMP-1', action: 'reply', text: 'hi' }, 'Bearer INACTIVE-KEY'), res);
    assert.strictEqual(res.statusCode, 403);
    assert.strictEqual(res.body.error.code, 'LICENSE_INACTIVE');
  });

  await test("action other than reply/resolve -> 400", async () => {
    delete require.cache[require.resolve('../_lib/license')];
    require.cache[require.resolve('../_lib/license')] = { exports: { validateLicenseKey: async function () { return { valid: true, active: true, license_hash: 'h' }; } } };
    delete require.cache[require.resolve('./complaint-respond.js')];
    var handler = require('./complaint-respond.js');
    var res = mockRes();
    await handler(mockReq({ complaint_id: 'COMP-1', action: 'delete' }, 'Bearer GOOD-KEY'), res);
    assert.strictEqual(res.statusCode, 400);
  });

  await test("action:'reply' with no text -> 400", async () => {
    delete require.cache[require.resolve('../_lib/license')];
    require.cache[require.resolve('../_lib/license')] = { exports: { validateLicenseKey: async function () { return { valid: true, active: true, license_hash: 'h' }; } } };
    delete require.cache[require.resolve('./complaint-respond.js')];
    var handler = require('./complaint-respond.js');
    var res = mockRes();
    await handler(mockReq({ complaint_id: 'COMP-1', action: 'reply' }, 'Bearer GOOD-KEY'), res);
    assert.strictEqual(res.statusCode, 400);
  });

  await test('unknown complaint_id -> 404 NOT_FOUND', async () => {
    delete require.cache[require.resolve('../_lib/license')];
    require.cache[require.resolve('../_lib/license')] = { exports: { validateLicenseKey: async function () { return { valid: true, active: true, license_hash: 'h' }; } } };
    global.fetch = async function () { return { ok: true, json: async function () { return []; } }; };
    delete require.cache[require.resolve('./complaint-respond.js')];
    var handler = require('./complaint-respond.js');
    var res = mockRes();
    await handler(mockReq({ complaint_id: 'NO-SUCH', action: 'resolve' }, 'Bearer GOOD-KEY'), res);
    assert.strictEqual(res.statusCode, 404);
    assert.strictEqual(res.body.error.code, 'NOT_FOUND');
  });

  await test("license_hash scoping -- valid license for practice A cannot reach practice B's complaint_id -> 404 NOT_FOUND", async () => {
    delete require.cache[require.resolve('../_lib/license')];
    require.cache[require.resolve('../_lib/license')] = { exports: { validateLicenseKey: async function () { return { valid: true, active: true, license_hash: 'practice-A-hash' }; } } };

    // Two rows seeded under two different license_hash values. The mock
    // filters on whichever eq. clauses are actually present in the query
    // URL (mirroring real PostgREST behavior), rather than just checking
    // for the presence of "license_hash=eq." as a substring -- so this
    // test only passes if the real code's query truly ANDs license_hash
    // together with complaint_id. If complaint-respond.js ever dropped
    // the license_hash filter, this mock would match complaint_id alone,
    // return practice B's row, and the handler would incorrectly
    // succeed instead of 404 -- which is exactly the regression this
    // test exists to catch.
    var rows = [
      { license_hash: 'practice-A-hash', complaint_id: 'A-COMP-1', access_token: 'tok-a', data: { messages: [] } },
      { license_hash: 'practice-B-hash', complaint_id: 'B-COMP-1', access_token: 'tok-b', data: { messages: [] } }
    ];
    global.fetch = async function (url) {
      var u = String(url);
      var mHash = u.match(/license_hash=eq\.([^&]+)/);
      var mId = u.match(/complaint_id=eq\.([^&]+)/);
      var matches = rows.filter(function (r) {
        if (mHash && r.license_hash !== decodeURIComponent(mHash[1])) return false;
        if (mId && r.complaint_id !== decodeURIComponent(mId[1])) return false;
        return true;
      });
      return { ok: true, json: async function () { return matches; } };
    };

    delete require.cache[require.resolve('./complaint-respond.js')];
    var handler = require('./complaint-respond.js');
    var res = mockRes();
    // Practice A's valid, active license -- but asking for practice B's complaint_id.
    await handler(mockReq({ complaint_id: 'B-COMP-1', action: 'resolve' }, 'Bearer GOOD-A-KEY'), res);
    assert.strictEqual(res.statusCode, 404);
    assert.strictEqual(res.body.error.code, 'NOT_FOUND');
  });

  console.log(passed + ' passed');
}

main();
