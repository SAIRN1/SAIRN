// api/_lib/roofing-damage-assessment-endpoint.test.js
// Round-trip tests for rf_settings read/write and the rf_claims 'assess_damage'
// verb of api/sd-data.js, through the REAL handler with a stubbed Supabase.
// Run: node api/_lib/roofing-damage-assessment-endpoint.test.js
//
// What this proves that the pure engine cannot: the threshold is read from
// rf_settings SERVER-side and never taken from the caller unless it is an
// explicit, recorded override; the assignment gate holds; the write gate is
// management-only; updated_by comes from the verified session and not the
// payload; a missing threshold degrades honestly instead of falling back to a
// convention; and assess_damage writes NOTHING.

const assert = require('assert');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://stub.test';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'k';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || 'stub-secret';

const auth = require('./auth');
let requests = [];
let store = { claims: [], settings: [] };
let settingsProvisioned = true;

function jsonRes(status, body) { return Promise.resolve({ status, ok: status >= 200 && status < 300, json: () => Promise.resolve(body), text: () => Promise.resolve(JSON.stringify(body)) }); }
function eqParam(u, k) { const m = u.match(new RegExp(k + '=eq\\.([^&]+)')); return m ? decodeURIComponent(m[1]) : null; }

global.fetch = function (url, opts) {
  opts = opts || {};
  const u = String(url); const method = opts.method || 'GET';
  requests.push({ url: u, method, body: opts.body ? JSON.parse(opts.body) : null });
  if (u.indexOf('license_keys') !== -1) return jsonRes(200, [{ key: 'RF', status: 'active', app_id: 'sairnroofing', trial_ends_at: null, stripe_subscription_id: 's' }]);
  if (u.indexOf('rf_settings') !== -1) {
    if (!settingsProvisioned) return jsonRes(404, { code: 'PGRST205', message: 'relation "public.rf_settings" does not exist' });
    if (method === 'POST') { const row = JSON.parse(opts.body); store.settings = store.settings.filter((s) => s.setting_key !== row.setting_key).concat([row]); return jsonRes(200, [row]); }
    const k = eqParam(u, 'setting_key'); return jsonRes(200, store.settings.filter((s) => !k || s.setting_key === k));
  }
  if (u.indexOf('rf_claims') !== -1) {
    if (method === 'POST') { const row = JSON.parse(opts.body); store.claims = store.claims.filter((c) => c.claim_id !== row.claim_id).concat([row]); return jsonRes(200, [row]); }
    const cid = eqParam(u, 'claim_id'); return jsonRes(200, store.claims.filter((c) => !cid || c.claim_id === cid));
  }
  if (u.indexOf('rf_jobs') !== -1) return jsonRes(200, [{ job_id: 'J1', data: {} }]);
  return jsonRes(404, { message: 'unexpected' });
};

const handler = require('../sd-data');
const licHash = require('crypto').createHash('sha256').update('RF').digest('hex');
function tok(emp, role) { return auth.signSessionToken({ license_hash: licHash, app: 'sairnroofing', employee_id: emp, role }); }
const OWNER = tok('OWN', 'owner');
const FM = tok('FM', 'foreman');
const FM2 = tok('FM2', 'foreman');

let passed = 0, failed = 0;
async function test(name, fn) { requests = []; try { await fn(); passed++; console.log('  ok - ' + name); } catch (e) { failed++; console.error('  FAIL - ' + name); console.error('    ' + e.message); } }
async function call(action, resource, payload, token) {
  const out = { code: null, body: null };
  const res = { status(c) { out.code = c; return res; }, json(b) { out.body = b; return res; } };
  const h = { authorization: 'Bearer RF' }; if (token) h['x-sd-auth'] = token;
  await handler({ method: 'POST', headers: h, body: { action, resource, payload } }, res);
  return out;
}

const GOOD = { hail: { hits_per_test_square: 8, source: 'Company standard 2026 field manual p.14' } };

(async () => {
  console.log('rf_settings write gate and validation:');
  await test('a foreman cannot change a company setting', async () => {
    const r = await call('write', 'rf_settings', { setting_key: 'damage_threshold', value: GOOD }, FM);
    assert.strictEqual(r.code, 403);
    assert.strictEqual(store.settings.length, 0, 'nothing may be written on a refused call');
  });
  await test('a threshold with no source is REFUSED at storage, not just at compute', async () => {
    const r = await call('write', 'rf_settings', { setting_key: 'damage_threshold', value: { hail: { hits_per_test_square: 8 } } }, OWNER);
    assert.strictEqual(r.code, 400);
    assert.strictEqual(r.body.error.code, 'INVALID_SETTING');
    assert.ok(/source is required/.test(r.body.error.message));
  });
  await test('management stores a valid threshold', async () => {
    const r = await call('write', 'rf_settings', { setting_key: 'damage_threshold', value: GOOD }, OWNER);
    assert.strictEqual(r.code, 200);
    assert.strictEqual(store.settings[0].data.hail.hits_per_test_square, 8);
  });
  await test('updated_by comes from the SESSION, not the payload', async () => {
    await call('write', 'rf_settings', { setting_key: 'damage_threshold', value: GOOD, updated_by: 'FORGED' }, OWNER);
    assert.strictEqual(store.settings[0].updated_by, 'OWN', 'a forged updated_by must never be stored');
  });
  await test('any authenticated employee can READ the threshold they are measured against', async () => {
    const r = await call('read', 'rf_settings', {}, FM);
    assert.strictEqual(r.code, 200);
    assert.strictEqual(r.body.data[0].value.hail.hits_per_test_square, 8);
  });

  console.log('\nassess_damage — threshold resolution:');
  store.claims.push({ claim_id: 'C1', assigned_employee_id: 'FM', data: {
    peril: 'hail',
    damage_assessment: { peril: 'hail', slopes: [
      { slope_label: 'North', test_squares: 1, hits: 9, photo_ids: ['RFCPH-1'] },
      { slope_label: 'South', test_squares: 1, hits: 2, photo_ids: ['RFCPH-2'] },
      { slope_label: 'East' }
    ] }
  } });

  await test('the company threshold is read server-side and applied', async () => {
    const r = await call('assess_damage', 'rf_claims', { claim_id: 'C1' }, OWNER);
    assert.strictEqual(r.code, 200);
    assert.strictEqual(r.body.assessment.ok, true);
    assert.strictEqual(r.body.assessment.threshold.hits_per_test_square, 8);
    assert.strictEqual(r.body.assessment.threshold_is_override, false);
    assert.deepStrictEqual(r.body.assessment.summary, {
      slopes_total: 3, meets_threshold: 1, below_threshold: 1, insufficient_evidence: 1, unassessed_slopes_remain: true
    });
  });
  await test('assess_damage WRITES NOTHING', async () => {
    await call('assess_damage', 'rf_claims', { claim_id: 'C1' }, OWNER);
    assert.strictEqual(requests.filter((q) => q.method === 'POST' && /rf_claims|rf_settings/.test(q.url)).length, 0);
  });
  await test('a per-claim override wins AND is reported as an override', async () => {
    const r = await call('assess_damage', 'rf_claims', { claim_id: 'C1', assessment: {
      peril: 'hail',
      threshold_override: { hits_per_test_square: 2, source: 'Carrier bulletin 2026-03' },
      slopes: [{ slope_label: 'South', test_squares: 1, hits: 2 }]
    } }, OWNER);
    assert.strictEqual(r.body.assessment.threshold_is_override, true);
    assert.strictEqual(r.body.assessment.slopes[0].outcome, 'meets_threshold');
    assert.strictEqual(r.body.assessment.threshold.source, 'Carrier bulletin 2026-03');
  });
  await test('no configured threshold for the peril refuses and SAYS SO -- no fallback convention', async () => {
    store.claims = store.claims.map((c) => Object.assign({}, c, { data: Object.assign({}, c.data, { peril: 'wind', damage_assessment: Object.assign({}, c.data.damage_assessment, { peril: 'wind' }) }) }));
    const r = await call('assess_damage', 'rf_claims', { claim_id: 'C1' }, OWNER);
    assert.strictEqual(r.code, 200);
    assert.strictEqual(r.body.assessment.ok, false, 'must refuse, never assume 8');
    assert.ok(/No damage threshold is configured for peril "wind"/.test(r.body.threshold_missing));
    store.claims = store.claims.map((c) => Object.assign({}, c, { data: Object.assign({}, c.data, { peril: 'hail', damage_assessment: Object.assign({}, c.data.damage_assessment, { peril: 'hail' }) }) }));
  });

  console.log('\nassess_damage — gates and honest degradation:');
  await test('an unassigned foreman is refused', async () => {
    const r = await call('assess_damage', 'rf_claims', { claim_id: 'C1' }, FM2);
    assert.strictEqual(r.code, 403);
  });
  await test('the assigned foreman may assess their own claim', async () => {
    const r = await call('assess_damage', 'rf_claims', { claim_id: 'C1' }, FM);
    assert.strictEqual(r.code, 200);
  });
  await test('no session is 401, not a silent empty result', async () => {
    const r = await call('assess_damage', 'rf_claims', { claim_id: 'C1' }, null);
    assert.strictEqual(r.code, 401);
  });
  await test('an unprovisioned rf_settings degrades to 503 NOT_PROVISIONED naming the right file', async () => {
    settingsProvisioned = false;
    const r = await call('assess_damage', 'rf_claims', { claim_id: 'C1' }, OWNER);
    assert.strictEqual(r.code, 503);
    assert.strictEqual(r.body.error.code, 'NOT_PROVISIONED');
    assert.ok(/sairnroofing_settings_schema\.sql/.test(r.body.error.message), 'must name its OWN migration file, not another one');
    settingsProvisioned = true;
  });

  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  process.exit(failed ? 1 : 0);
})();
