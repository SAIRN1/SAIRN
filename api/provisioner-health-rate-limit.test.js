// api/provisioner-health-rate-limit.test.js
// Plain node:assert, matching api/sairndental/public-complaint-submit.test.js's
// convention. Run: node api/provisioner-health-rate-limit.test.js
//
// THIS ENDPOINT IS THE ONLY THING THAT CAN SAY WHETHER THE AI RATE LIMITER'S
// ATOMICITY FIX IS ACTUALLY IN FORCE, and until 2026-09-17 it had no test at
// all -- a check with no check on it, answering a question nobody else can.
//
// The arms below exist because the endpoint has to distinguish THREE worlds
// that are easy to conflate, and it got two of them wrong:
//
//   A. no function          -> RACY_FALLBACK
//   B. the 3-arg function   -> ATOMIC app ceiling, NO tenant sub-budget
//   C. the 6-arg function   -> ATOMIC app ceiling AND tenant sub-budget
//
// B AND C ANSWER A 3-ARG CALL IDENTICALLY, structurally: the tenant migration
// DROPS the 3-arg function and replaces it with a 6-arg one whose last three
// parameters default to null, because an overload would make every 3-arg call
// ambiguous and take the platform down. Only a call carrying the tenant
// arguments separates them.
//
// AND THEY REFUSE AN EMPTY app_id DIFFERENTLY -- the 3-arg one RETURNS
// {error:'app_id required'} as HTTP 200, the 6-arg one RAISES and reaches us as
// a 4xx. The old test for "the function exists" demanded the 200 shape only, so
// world C read as UNKNOWN: RUNNING THE TENANT MIGRATION WOULD HAVE LOOKED LIKE
// A REGRESSION IN THE CHECK WHOSE JOB IS TO SAY THE FIX IS IN FORCE.

const assert = require('assert');

function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (p) { res.body = p; return res; };
  res.setHeader = function () { return res; };
  res.end = function () { return res; };
  return res;
}
function mockReq() {
  return { method: 'POST', headers: { authorization: 'Bearer TEST-KEY-2026' },
           body: { action: 'rate_limit_health' } };
}

let passed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (err) {
    console.error('  FAIL - ' + name);
    console.error('    ' + err.message);
    process.exitCode = 1;
  }
}

// The two real refusal bodies, written out rather than paraphrased -- the whole
// point of accepting two shapes is that they do not look alike.
var RETURNED_REFUSAL = { error: 'app_id required' };
var RAISED_REFUSAL = {
  code: '22023', message: 'sairn_ai_rate_limit_consume: p_app_id is required'
};

// `world` decides what the RPC does. `calls` records the argument sets, so an
// arm can assert that the second probe was made AT ALL -- an endpoint that
// never asks the tenant question would otherwise pass every content assertion
// by reporting the default.
function load(world, calls) {
  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  var licPath = require.resolve('./_lib/license');
  delete require.cache[licPath];
  require.cache[licPath] = { exports: {
    validateLicenseKey: async function () {
      return { valid: true, active: true, app_id: 'stonedesk', license_hash: 'h' };
    },
    hashLicense: function () { return 'h'; }
  } };

  global.fetch = async function (url, opts) {
    var args = JSON.parse(opts.body);
    var tenant = Object.prototype.hasOwnProperty.call(args, 'p_tenant_key');
    calls.push(tenant ? 'tenant' : 'base');
    var r = world(tenant);
    return { ok: r.status === 200, status: r.status,
             json: async function () { return r.body; },
             text: async function () { return JSON.stringify(r.body); } };
  };
  delete require.cache[require.resolve('./provisioner-health.js')];
  return require('./provisioner-health.js');
}

async function main() {
  console.log('api/provisioner-health.js -- rate_limit_health');

  await test('WORLD B (3-arg only): ATOMIC, and the tenant sub-budget is reported ABSENT',
    async () => {
      var calls = [];
      var h = load(function (tenant) {
        return tenant ? { status: 404, body: { message: 'no function matches' } }
                      : { status: 200, body: RETURNED_REFUSAL };
      }, calls);
      var res = mockRes();
      await h(mockReq(), res);
      assert.strictEqual(res.body.state, 'ATOMIC');
      assert.strictEqual(res.body.tenant_state, 'APP_CEILING_ONLY');
      assert.strictEqual(res.body.tenant_subbudget, false);
      assert.deepStrictEqual(calls, ['base', 'tenant'],
        'the tenant question must actually be ASKED -- a default answer is not a measurement');
    });

  await test('...and its message says the fairness gap out loud, without claiming the tenant property',
    async () => {
      var calls = [];
      var h = load(function (tenant) {
        return tenant ? { status: 404, body: {} } : { status: 200, body: RETURNED_REFUSAL };
      }, calls);
      var res = mockRes();
      await h(mockReq(), res);
      var m = res.body.message;
      assert.ok(/ONE LICENCE CAN EXHAUST/i.test(m),
        'the consequence must be stated, not left implied by a false boolean');
      assert.ok(/sairn_ai_tenant_subbudget_2026-09-15\.sql/.test(m),
        'a gap with no named remedy is a complaint');
      assert.ok(!/one licence cannot exhaust/i.test(m),
        'this is the overclaim the split exists to remove');
    });

  // THE ARM THAT WOULD HAVE CAUGHT THE OLD DEFECT. Before 2026-09-17 the
  // existence test demanded HTTP 200 with a returned error object, so the 6-arg
  // function -- which RAISES -- came back as UNKNOWN. Running the migration
  // would have made a correct upgrade look like a broken limiter.
  await test('WORLD C (6-arg): a RAISED refusal still proves the function exists -- not UNKNOWN',
    async () => {
      var calls = [];
      var h = load(function () { return { status: 400, body: RAISED_REFUSAL }; }, calls);
      var res = mockRes();
      await h(mockReq(), res);
      assert.strictEqual(res.body.state, 'ATOMIC',
        'a function that refuses by RAISING is still a function that exists');
      assert.strictEqual(res.body.atomic, true);
    });

  await test('...and WORLD C reports the tenant sub-budget as LIVE', async () => {
    var calls = [];
    var h = load(function () { return { status: 400, body: RAISED_REFUSAL }; }, calls);
    var res = mockRes();
    await h(mockReq(), res);
    assert.strictEqual(res.body.tenant_state, 'SUB_BUDGETED');
    assert.strictEqual(res.body.tenant_subbudget, true);
    assert.ok(/one licence cannot exhaust the whole ceiling/i.test(res.body.message));
  });

  await test('WORLD A (absent): RACY_FALLBACK, and the tenant question is NOT ASKED',
    async () => {
      var calls = [];
      var h = load(function () { return { status: 404, body: {} } }, calls);
      var res = mockRes();
      await h(mockReq(), res);
      assert.strictEqual(res.body.state, 'RACY_FALLBACK');
      assert.strictEqual(res.body.tenant_state, 'NOT_APPLICABLE');
      assert.deepStrictEqual(calls, ['base'],
        'reporting "no sub-budget" about a limiter that does not exist is a true sentence ' +
        'pointing at the wrong problem');
    });

  await test('CONTROL: the three worlds do not all produce the same answer',
    async () => {
      var out = [];
      for (var w of [
        function () { return { status: 404, body: {} }; },
        function (t) { return t ? { status: 404, body: {} } : { status: 200, body: RETURNED_REFUSAL }; },
        function () { return { status: 400, body: RAISED_REFUSAL }; }
      ]) {
        var res = mockRes();
        await (load(w, []))(mockReq(), res);
        out.push(res.body.state + '/' + res.body.tenant_state);
      }
      assert.strictEqual(new Set(out).size, 3,
        'if two worlds answer identically the endpoint is not measuring what it claims: ' + out.join(' '));
    });

  await test('an UNEXPECTED base status claims nothing in either direction', async () => {
    var h = load(function () { return { status: 503, body: { message: 'upstream' } }; }, []);
    var res = mockRes();
    await h(mockReq(), res);
    assert.strictEqual(res.body.state, 'UNKNOWN');
    assert.strictEqual(res.body.atomic, false);
    assert.strictEqual(res.body.tenant_state, 'NOT_APPLICABLE');
  });

  console.log(passed + ' passed');
}

main();
