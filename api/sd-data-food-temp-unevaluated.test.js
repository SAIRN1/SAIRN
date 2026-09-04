// api/sd-data-food-temp-unevaluated.test.js
// Run: node api/sd-data-food-temp-unevaluated.test.js
//
// SAIRNcare food-temperature records: the reading is ALWAYS stored, and the
// verdict is withheld when this facility's own thresholds could not be read.
//
// ══ WHAT WAS WRONG ════════════════════════════════════════════════════════
// The alf_facility read fell back to `{}`, and evaluateFoodTemp() falls back
// to the FDA Food Code figures when no override is supplied. So an unreadable
// facility record meant a facility with a STRICTER local limit was silently
// graded against the LOOSER national one -- a cold-holding reading that should
// fail at their 40F recorded as a PASS at the FDA 41F, in the compliance log,
// with nothing saying the local limit had not been applied.
//
// ══ WHY IT IS NOT FIXED BY REFUSING THE WRITE ═════════════════════════════
// Michael's call, and it is the right one: refusing would mean refusing to
// store a real observation somebody physically performed, and that observation
// IS the compliance artifact. Losing it is worse than not grading it. So the
// temperature lands and `passed` stays null with a stated reason -- the same
// shape as api/_lib/mech-assets.js's `unknown_charge` and
// api/_lib/roofing-asset-registry.js's `no_service_life_recorded`.
//
// ══ THE DISTINCTION THIS FILE EXISTS TO HOLD ══════════════════════════════
// NOT CONFIGURED and COULD NOT BE READ are different answers.
//   * A facility that has set no thresholds is still graded against the FDA
//     figures, which are a real published default, and evaluateFoodTemp
//     records `usedOverride` so the record says which applied. Unchanged.
//   * A facility whose thresholds could not be READ is not graded at all.
// Collapsing those two would either stop grading everyone or resume the
// substitution this fixed.

'use strict';
const assert = require('assert');
const path = require('path');

function mockRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}
function reply(status, json) {
  return { ok: status >= 200 && status < 300, status, json: async () => json };
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
      validateLicenseKey: async () => ({ valid: true, active: true, license_hash: 'test-hash' })
    }
  };
  const realAuth = require('./_lib/auth');
  delete require.cache[require.resolve('./_lib/auth')];
  require.cache[require.resolve('./_lib/auth')] = {
    exports: Object.assign({}, realAuth, {
      tokenFromRequest: () => 'tok',
      verifySessionToken: () => ({ employee_id: 'nurse-1', role: opts.role || 'nursing' })
    })
  };
  global.fetch = async (url, init) => {
    const method = (init && init.method) || 'GET';
    calls.push({ url: String(url), method, body: init && init.body });
    if (method === 'GET' && /alf_facility/.test(String(url))) {
      return opts.facilityStatus === 200
        ? reply(200, opts.facilityRows || [])
        : reply(opts.facilityStatus || 200, { message: 'nope' });
    }
    if (method === 'GET' && /alf_op_audits/.test(String(url))) return reply(200, []);
    if (method === 'GET') return reply(200, []);
    return reply(201, [JSON.parse(init.body)]);
  };
  delete require.cache[require.resolve('./sd-data.js')];
  return { handler: require('./sd-data.js'), calls };
}

function req(payload) {
  return {
    method: 'POST',
    headers: { authorization: 'Bearer CARE-TEST', 'x-sd-auth': 'tok' },
    body: { action: 'write', resource: 'alf_op_audits', payload }
  };
}
// 39F is BELOW the FDA cold_max (41F) and so would PASS on the national
// default. A facility that set 38F would fail it. That gap is the whole point.
const READING = {
  id: 'OPA-TEST-1', record_type: 'food_temp', holding_kind: 'cold',
  temperature_f: 39, observed_on: '2026-09-04'
};

function writtenBody(calls) {
  const post = calls.find((c) => c.method === 'POST' && /alf_op_audits/.test(c.url));
  assert.ok(post, 'no write was issued -- the reading was refused, which is the thing this must not do');
  return JSON.parse(post.body);
}

async function main() {
  console.log('SAIRNcare food temp: always record the reading, never substitute a threshold');
  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  // ── the facility read fails ─────────────────────────────────────────────
  for (const status of [401, 403, 500, 503]) {
    await test('facility read HTTP ' + status + ' -> the reading is STILL WRITTEN', async () => {
      const { handler, calls } = loadHandler({ facilityStatus: status });
      const res = mockRes();
      await handler(req(READING), res);
      assert.strictEqual(res.statusCode, 200, 'the observation was refused rather than recorded');
      const body = writtenBody(calls);
      assert.strictEqual(body.data.temperature_f, 39, 'the temperature itself was lost');
    });

    await test('facility read HTTP ' + status + ' -> passed is NULL, not a verdict', async () => {
      const { handler, calls } = loadHandler({ facilityStatus: status });
      await handler(req(READING), mockRes());
      const body = writtenBody(calls);
      assert.strictEqual(body.passed, null,
        'a pass/fail was recorded against a threshold that could not be read');
      assert.strictEqual(body.data.evaluation.evaluated, false);
      assert.strictEqual(body.data.evaluation.state, 'facility_threshold_unavailable');
      assert.match(body.data.evaluation.note, /NOT graded/);
    });
  }

  await test('a non-array facility body is treated the same way', async () => {
    const { handler, calls } = loadHandler({ facilityStatus: 200, facilityRows: { oops: true } });
    await handler(req(READING), mockRes());
    const body = writtenBody(calls);
    assert.strictEqual(body.passed, null);
    assert.strictEqual(body.data.evaluation.state, 'facility_threshold_unavailable');
  });

  // ── the facility read succeeds ──────────────────────────────────────────
  await test('a facility with its OWN stricter threshold fails a 39F cold reading', async () => {
    // The case the bug hid: 39F passes the FDA 41F and fails this facility's 38F.
    const { handler, calls } = loadHandler({
      facilityStatus: 200, facilityRows: [{ data: { food_thresholds: { cold_max_f: 38 } } }]
    });
    await handler(req(READING), mockRes());
    const body = writtenBody(calls);
    assert.strictEqual(body.passed, false,
      'the facility threshold was not applied -- this is the substitution the fix removes');
    assert.strictEqual(body.data.evaluation.evaluated, undefined,
      'a real evaluation should not carry the not-evaluated marker');
  });

  await test('the SAME reading passes on the FDA default when no threshold is set', async () => {
    // NOT CONFIGURED is deliberately still graded. Only COULD NOT READ is not.
    const { handler, calls } = loadHandler({ facilityStatus: 200, facilityRows: [{ data: {} }] });
    await handler(req(READING), mockRes());
    const body = writtenBody(calls);
    assert.strictEqual(body.passed, true);
    assert.ok(!body.data.evaluation.state, 'a configured-absent facility must still be graded');
  });

  await test('an empty facility table is graded, not withheld', async () => {
    const { handler, calls } = loadHandler({ facilityStatus: 200, facilityRows: [] });
    await handler(req(READING), mockRes());
    const body = writtenBody(calls);
    assert.strictEqual(body.passed, true);
  });

  // ── the shape is gone ───────────────────────────────────────────────────
  await test('the fail-open facility read is gone from the food-temp branch', () => {
    const fs = require('fs');
    const src = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8')
      .split('\n').filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');
    assert.ok(!/const facRows = facR\.ok \? await facR\.json\(\)\.catch\(\(\) => \[\]\) : \[\]/.test(src),
      'the food-temp branch still falls back to an empty facility record');
  });

  console.log('\n' + passed + ' assertions passed');
}

main();
