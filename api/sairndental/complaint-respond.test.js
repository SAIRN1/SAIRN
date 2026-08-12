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

  console.log(passed + ' passed');
}

main();
