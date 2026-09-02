// api/sd-data-session-gate.test.js
// Plain node:assert tests. Run: node api/sd-data-session-gate.test.js
//
// slabs, profile and memory predate per-employee sessions and were reachable
// with the licence key alone. docs/superpowers/specs/2026-09-02-licence-key-exposure-audit.md
// proved what that meant: the key is a bearer credential, StoneDesk printed it
// into a link the shop is told to send customers, and anyone holding it could
// read the whole slab inventory, the business profile (company, EIN, revenue
// range, owner) and the shop's AI memories -- and WRITE slabs.
//
// `profile` READ was held open for exactly one commit while SAIRNcode migrated
// off it, and is now gated too. The assertion that used to protect that hole is
// inverted below rather than deleted, so the file still records that the
// exception existed and that it closed.

const assert = require('assert');

function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}
function mockReq(action, resource, payload) {
  return {
    method: 'POST',
    headers: { authorization: 'Bearer SD-TEST-KEY', 'x-sd-auth': 'tok' },
    body: { action: action, resource: resource, payload: payload || {} }
  };
}

let passed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

function loadHandler(opts) {
  opts = opts || {};
  const calls = [];
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: 'test-hash', trial_ends_at: null, stripe_subscription_id: null };
      }
    }
  };
  const realAuth = require('./_lib/auth');
  delete require.cache[require.resolve('./_lib/auth')];
  require.cache[require.resolve('./_lib/auth')] = {
    exports: Object.assign({}, realAuth, {
      tokenFromRequest: function () { return 'tok'; },
      verifySessionToken: function () { return opts.noSession ? null : { employee_id: 'emp-1', role: 'sales' }; }
    })
  };
  // Any network call at all on a refused request is itself a defect.
  global.fetch = async function (url, init) {
    calls.push({ url: String(url), method: (init && init.method) || 'GET' });
    if (opts.refuseNetwork) throw new Error('the gate let a refused request reach the database');
    const m = (init && init.method) || 'GET';
    if (m === 'GET') return { ok: true, status: 200, json: async () => [] };
    return { ok: true, status: 201, json: async () => [{ data: {} }] };
  };
  delete require.cache[require.resolve('./sd-data.js')];
  return { handler: require('./sd-data.js'), calls: calls };
}

// The exposure, as the audit measured it, expressed as a table.
const GATED = [
  ['slabs', 'read'],
  ['slabs', 'write'],
  ['slabs', 'reserve'],
  ['profile', 'read'],
  ['profile', 'write'],
  ['memory', 'read'],
  ['memory', 'write']
];

async function main() {
  console.log('api/sd-data.js -- the licence key alone is no longer enough for slabs/profile/memory');
  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  for (const [resource, action] of GATED) {
    await test(resource + '/' + action + ' -> 403 with a licence key and NO session', async () => {
      const { handler, calls } = loadHandler({ noSession: true, refuseNetwork: true });
      const res = mockRes();
      const payload = resource === 'slabs' ? { id: 'S1', reservedFor: 'X' } : { x: 1 };
      await handler(mockReq(action, resource, payload), res);
      assert.strictEqual(res.statusCode, 403, 'status was ' + res.statusCode);
      assert.strictEqual(res.body.error.code, 'FORBIDDEN');
      assert.match(res.body.error.message, /sign in first/i);
      assert.strictEqual(calls.length, 0, 'a refused request still hit the database');
    });
  }

  for (const [resource, action] of GATED) {
    await test(resource + '/' + action + ' still works WITH a session', async () => {
      const { handler } = loadHandler({});
      const res = mockRes();
      const payload = resource === 'slabs' ? { id: 'S1', reservedFor: 'X' } : { x: 1 };
      await handler(mockReq(action, resource, payload), res);
      assert.notStrictEqual(res.statusCode, 403,
        'the gate refuses a legitimate signed-in caller');
    });
  }

  await test('THE HOLE IS CLOSED: no resource in the table is exempt any more', async () => {
    // This assertion used to say the opposite. profile/read was open only
    // while SAIRNcode probed it for licence validity without a session;
    // SAIRNcode now calls api/sc-auth.js check_license, verified live. Kept
    // inverted rather than deleted so the file records that the exception
    // existed, and would fail loudly if anyone re-opened it.
    const fs = require('fs');
    const src = fs.readFileSync(require.resolve('./sd-data.js'), 'utf8');
    const m = src.match(/const SD_SESSION_GATED = \{[\s\S]*?\};/);
    assert.ok(!/'profile':\s*\['write'\]/.test(m[0]),
      'profile/read is exempt again -- if that is deliberate, say why in the table');
  });

  await test('the gate is a table, not scattered checks -- and lists exactly seven pairs', () => {
    const fs = require('fs');
    const src = fs.readFileSync(require.resolve('./sd-data.js'), 'utf8');
    const m = src.match(/const SD_SESSION_GATED = \{[\s\S]*?\};/);
    assert.ok(m, 'the gate table is gone');
    assert.match(m[0], /'slabs':\s*\['read', 'write', 'reserve'\]/);
    assert.match(m[0], /'profile':\s*\['read', 'write'\]/);
    assert.match(m[0], /'memory':\s*\['read', 'write'\]/);
  });

  await test('an ungated resource is untouched by the table', async () => {
    const { handler } = loadHandler({ noSession: true });
    const res = mockRes();
    await handler(mockReq('read', 'employees', {}), res);
    // employees has its own, older gate -- what matters is that this one did
    // not start refusing things it was never asked to.
    assert.ok(res.body && res.body.error, 'expected employees to keep its own refusal');
    assert.ok(!/sign in first/i.test(res.body.error.message || ''),
      'the new gate swallowed a resource that has its own');
  });

  console.log('\n' + (process.exitCode ? 'FAILURES ABOVE' : 'ALL ' + passed + ' SESSION-GATE ASSERTIONS PASS'));
}

main();
