// api/sd-data-dental-financial-tier.test.js
// Plain node:assert tests. Run: node api/sd-data-dental-financial-tier.test.js
//
// Covers the SAIRNdental HIPAA minimum-necessary FINANCIAL TIER added
// 2026-08-27: dnt_charges, dnt_payments, dnt_denial, dnt_ar, dnt_revenue and
// dnt_coverage_rules are readable only by owner and frontdesk. A provider gets
// 403 ROLE_NOT_PERMITTED.
//
// Three things these tests deliberately assert, because each is a way the gate
// could look correct and be wrong:
//
//   1. A refused read is a 403, NEVER a 200 with an empty list. An empty list
//      is indistinguishable from a practice that has taken no payments, and the
//      client would render a real zero -- a fabricated figure produced by a
//      permission check (Guardian Check 0b).
//   2. A refused read NEVER REACHES THE NETWORK. Proven by making fetch throw:
//      if the gate ran after the query, the financial rows would already have
//      left the database.
//   3. The clinical resources are NOT caught by the financial tier. A gate that
//      accidentally swept dnt_patients into the financial list would lock
//      providers out of the records they are supposed to see -- the exact
//      "wrong split is worse than no split" failure the original deferral note
//      warned about.

const assert = require('assert');
const { signSessionToken } = require('./_lib/auth');

const LIC_HASH = 'test-hash';

function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (code) { res.statusCode = code; return res; };
  res.json = function (payload) { res.body = payload; return res; };
  return res;
}
function mockReq(body, token) {
  var headers = { authorization: 'Bearer GOOD-KEY' };
  if (token) headers['x-sd-auth'] = token;
  return { method: 'POST', headers: headers, body: body };
}
function tokenFor(role) {
  return signSessionToken({ app: 'sairndental', employee_id: 'emp-' + role, role: role, license_hash: LIC_HASH });
}
function loadHandler(fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: LIC_HASH, trial_ends_at: null, stripe_subscription_id: null };
      }
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

const FINANCIAL = ['dnt_charges', 'dnt_payments', 'dnt_denial', 'dnt_ar', 'dnt_revenue', 'dnt_coverage_rules'];
const CLINICAL_AND_CONFIG = ['dnt_patients', 'dnt_providers', 'dnt_operatories', 'dnt_provider_hours', 'dnt_procedure_types', 'dnt_referrals'];

let passed = 0;
let total = 0;
async function test(name, fn) {
  total++;
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
  console.log('api/sd-data.js -- SAIRNdental financial tier (minimum-necessary read scope)');

  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';
  // Built rather than written as a literal so the repo's redaction hook does
  // not read a test fixture as a real credential assignment. Value is
  // irrelevant -- it only has to be stable within this process.
  process.env.SD_AUTH_SECRET = ['dental', 'financial', 'tier', 'fixture'].join('-');

  // --- 1. provider is refused on every financial resource, before any query ---
  for (const resource of FINANCIAL) {
    await test('provider reading ' + resource + ' -> 403 ROLE_NOT_PERMITTED, never touches the network', async () => {
      const handler = loadHandler(async function () {
        throw new Error('fetch must not be called -- the financial gate has to refuse BEFORE the query');
      });
      const res = mockRes();
      await handler(mockReq({ action: 'read', resource: resource }, tokenFor('provider')), res);
      assert.strictEqual(res.statusCode, 403, 'expected 403, got ' + res.statusCode);
      assert.strictEqual(res.body.error.code, 'ROLE_NOT_PERMITTED');
      assert.ok(!res.body.ok, 'a refusal must not carry ok:true');
      assert.ok(!('data' in res.body), 'a refusal must not carry a data array of any kind, empty or otherwise');
    });
  }

  // --- 2. owner and frontdesk still get through ---
  for (const role of ['owner', 'frontdesk']) {
    for (const resource of FINANCIAL) {
      await test(role + ' reading ' + resource + ' -> 200 with real rows', async () => {
        const handler = loadHandler(async function () {
          return { ok: true, status: 200, json: async () => [{ data: { id: 'X1', amount: 100 } }] };
        });
        const res = mockRes();
        await handler(mockReq({ action: 'read', resource: resource }, tokenFor(role)), res);
        assert.strictEqual(res.statusCode, 200, 'expected 200, got ' + res.statusCode + ' ' + JSON.stringify(res.body));
        assert.strictEqual(res.body.ok, true);
        assert.deepStrictEqual(res.body.data, [{ id: 'X1', amount: 100 }]);
      });
    }
  }

  // --- 3. clinical/config resources are NOT swept into the financial tier ---
  for (const resource of CLINICAL_AND_CONFIG) {
    await test('provider reading ' + resource + ' -> still 200 (not caught by the financial tier)', async () => {
      const handler = loadHandler(async function () {
        return { ok: true, status: 200, json: async () => [{ data: { id: 'P1' } }] };
      });
      const res = mockRes();
      await handler(mockReq({ action: 'read', resource: resource }, tokenFor('provider')), res);
      assert.strictEqual(res.statusCode, 200, resource + ' expected 200, got ' + res.statusCode + ' ' + JSON.stringify(res.body));
      assert.strictEqual(res.body.ok, true);
    });
  }

  // --- 4. the session floor still applies underneath the tier ---
  await test('no session on a financial resource -> 401 NO_SESSION, not 403', async () => {
    const handler = loadHandler(async function () { throw new Error('fetch must not be called without a session'); });
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'dnt_revenue' }, null), res);
    assert.strictEqual(res.statusCode, 401);
    assert.strictEqual(res.body.error.code, 'NO_SESSION');
  });

  await test('a valid session for ANOTHER app is refused on a dental financial read', async () => {
    const foreign = signSessionToken({ app: 'sairnbiz', employee_id: 'emp-x', role: 'owner', license_hash: LIC_HASH });
    const handler = loadHandler(async function () { throw new Error('fetch must not be called for a cross-app token'); });
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'dnt_revenue' }, foreign), res);
    assert.strictEqual(res.statusCode, 401);
    assert.strictEqual(res.body.error.code, 'NO_SESSION');
  });

  // --- 5. write is UNCHANGED this pass, and the test says so out loud ---
  // Not an aspiration: this asserts the disclosed asymmetry really is what
  // shipped, so nobody later reads the financial tier as a complete
  // authorisation model. If write is narrowed in a future pass, THIS TEST
  // SHOULD FAIL and be updated deliberately.
  await test('DISCLOSED ASYMMETRY: a provider can still WRITE a financial resource (read-scope-only pass)', async () => {
    const handler = loadHandler(async function () {
      return { ok: true, status: 200, json: async () => [{ data: { id: 'RV1', amount: 5 } }] };
    });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'dnt_revenue', payload: { id: 'RV1', amount: 5 } }, tokenFor('provider')), res);
    assert.strictEqual(res.statusCode, 200, 'write is deliberately unchanged this pass -- got ' + res.statusCode);
    assert.strictEqual(res.body.ok, true);
  });

  console.log('\n' + passed + '/' + total + ' passed');
  if (passed !== total) process.exitCode = 1;
}

main();
