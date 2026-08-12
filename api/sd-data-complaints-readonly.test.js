// api/sd-data-complaints-readonly.test.js
// Plain node:assert tests. Run: node api/sd-data-complaints-readonly.test.js
//
// Narrow coverage for spec §7's "enforced read-only" guarantee: a write
// action against dnt_complaints through the generic api/sd-data.js path
// must return a clean 400 READ_ONLY_RESOURCE, never a silent success, and
// must never reach the network (proven by making fetch throw). Also checks
// the read path still works as a lightweight positive-path sanity check.

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
  console.log('api/sd-data.js -- dnt_complaints read-only enforcement');

  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  await test("write action against dnt_complaints -> 400 READ_ONLY_RESOURCE, never touches the network", async () => {
    delete require.cache[require.resolve('./_lib/license')];
    require.cache[require.resolve('./_lib/license')] = {
      exports: {
        validateLicenseKey: async function () {
          return { valid: true, active: true, license_hash: 'test-hash', trial_ends_at: null, stripe_subscription_id: null };
        }
      }
    };
    global.fetch = async function () { throw new Error('fetch should never be called for a write against a read-only resource'); };
    delete require.cache[require.resolve('./sd-data.js')];
    var handler = require('./sd-data.js');
    var res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_complaints', payload: { id: 'x' } }, 'Bearer GOOD-KEY'), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'READ_ONLY_RESOURCE');
  });

  await test('read action against dnt_complaints still works -> 200 {ok:true, data:[]}', async () => {
    delete require.cache[require.resolve('./_lib/license')];
    require.cache[require.resolve('./_lib/license')] = {
      exports: {
        validateLicenseKey: async function () {
          return { valid: true, active: true, license_hash: 'test-hash', trial_ends_at: null, stripe_subscription_id: null };
        }
      }
    };
    global.fetch = async function () { return { ok: true, status: 200, json: async function () { return []; } }; };
    delete require.cache[require.resolve('./sd-data.js')];
    var handler = require('./sd-data.js');
    var res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'dnt_complaints' }, 'Bearer GOOD-KEY'), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.ok, true);
    assert.deepStrictEqual(res.body.data, []);
  });

  console.log(passed + ' passed');
}

main();
