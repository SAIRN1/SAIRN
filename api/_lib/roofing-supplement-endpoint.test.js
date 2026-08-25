// api/_lib/roofing-supplement-endpoint.test.js
// Round-trip tests for the rf_claims 'reconcile' verb of api/sd-data.js,
// through the REAL handler with a stubbed Supabase.
// Run: node api/_lib/roofing-supplement-endpoint.test.js
//
// The wiring this proves that the pure engine cannot: reconcile reads the
// MEASURED quantities from the linked JOB server-side (never from the caller),
// honours the claim's assignment gate, writes nothing, and degrades honestly.

const assert = require('assert');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://stub.test';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'k';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || 'stub-secret';

const auth = require('./auth');
const realFetch = global.fetch;
let requests = [];
let store = { claims: [], jobs: [] };

function jsonRes(status, body) { return Promise.resolve({ status, ok: status >= 200 && status < 300, json: () => Promise.resolve(body), text: () => Promise.resolve(JSON.stringify(body)) }); }
function eqParam(u, k) { const m = u.match(new RegExp(k + '=eq\\.([^&]+)')); return m ? decodeURIComponent(m[1]) : null; }

global.fetch = function (url, opts) {
  opts = opts || {};
  const u = String(url); const method = opts.method || 'GET';
  requests.push({ url: u, method, body: opts.body ? JSON.parse(opts.body) : null });
  if (u.indexOf('license_keys') !== -1) return jsonRes(200, [{ key: 'RF', status: 'active', app_id: 'sairnroofing', trial_ends_at: null, stripe_subscription_id: 's' }]);
  if (u.indexOf('rf_jobs') !== -1) { const jid = eqParam(u, 'job_id'); return jsonRes(200, store.jobs.filter((j) => !jid || j.job_id === jid)); }
  if (u.indexOf('rf_claims') !== -1) {
    if (method === 'POST') { const row = JSON.parse(opts.body); store.claims = store.claims.filter((c) => c.claim_id !== row.claim_id).concat([row]); return jsonRes(200, [row]); }
    const cid = eqParam(u, 'claim_id'); return jsonRes(200, store.claims.filter((c) => !cid || c.claim_id === cid));
  }
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

// A job carrying a real measured scope as its latest measurement entry.
store.jobs.push({ job_id: 'J1', data: { measurement: { correction_history: [
  { quantities: { squares: 30, ridge_lf: 40, valley_lf: 60 }, changed_by: 'FM', changed_at: '2026-08-01T00:00:00Z' },
  { quantities: { squares: 30, ridge_lf: 44, valley_lf: 60 }, changed_by: 'FM', changed_at: '2026-08-10T00:00:00Z' } // LATEST -> ridge_lf 44
] } } });

const SUPP = {
  expected_items: [
    { item_key: 'ridge_cap', label: 'Ridge cap', measured_from: 'ridge_lf', unit: 'LF', unit_price: 8 },
    { item_key: 'valley_metal', label: 'Valley', measured_from: 'valley_lf', unit: 'LF', unit_price: 12 }
  ],
  adjuster_lines: [{ item_key: 'ridge_cap', quantity: 30, unit_price: 8 }], // ridge short (44-30=14), valley omitted
  asserted_lines: [{ reason_code: 'hidden_damage', description: 'Deck rot', quantity: 2, unit_price: 65, photo_ids: ['RFCPH-1'] }]
};

(async () => {
  console.log('Setup: a claim with stored supplement inputs, assigned to FM:');
  await test('claim writes with supplement inputs in data', async () => {
    const r = await call('write', 'rf_claims', { id: 'C1', job_id: 'J1', carrier: 'SF', claim_number: 'X', assigned_employee_id: 'FM', supplement: SUPP }, OWNER);
    assert.strictEqual(r.code, 200);
    assert.ok(store.claims[0].data.supplement, 'supplement stored on the claim');
  });

  console.log('\nReconcile — measured scope comes from the JOB, server-side:');
  await test('reconcile uses the LATEST job measurement (ridge_lf 44, not 40)', async () => {
    const r = await call('reconcile', 'rf_claims', { claim_id: 'C1' }, OWNER);
    assert.strictEqual(r.code, 200);
    assert.strictEqual(r.body.measured_from_job.ridge_lf, 44);
    const rc = r.body.worksheet.derived.find((d) => d.item_key === 'ridge_cap');
    assert.strictEqual(rc.expected_qty, 44);           // from the job, not the caller
    assert.strictEqual(rc.shortfall_qty, 14);          // 44 - 30
    assert.strictEqual(rc.supplement_amount, 112);     // 14 * 8
  });
  await test('an omitted item is priced at full measured quantity', async () => {
    const r = await call('reconcile', 'rf_claims', { claim_id: 'C1' }, OWNER);
    const v = r.body.worksheet.derived.find((d) => d.item_key === 'valley_metal');
    assert.strictEqual(v.status, 'omitted');
    assert.strictEqual(v.supplement_amount, 720);      // 60 * 12
  });
  await test('the asserted hidden-damage line with a photo is counted', async () => {
    const r = await call('reconcile', 'rf_claims', { claim_id: 'C1' }, OWNER);
    assert.strictEqual(r.body.worksheet.totals.asserted_supplement, 130); // 2*65
    assert.strictEqual(r.body.worksheet.totals.total_supplement, 112 + 720 + 130);
  });
  await test('a caller CANNOT substitute their own measured scope', async () => {
    // Even if the caller sends a bogus measured set, the engine reads the job.
    const r = await call('reconcile', 'rf_claims', { claim_id: 'C1', measured: { ridge_lf: 9999 } }, OWNER);
    const rc = r.body.worksheet.derived.find((d) => d.item_key === 'ridge_cap');
    assert.strictEqual(rc.expected_qty, 44); // still the job's value, caller's ignored
  });
  await test('a live unsaved supplement set can be previewed via payload', async () => {
    const preview = Object.assign({}, SUPP, { adjuster_lines: [{ item_key: 'ridge_cap', quantity: 44, unit_price: 8 }] }); // now matches
    const r = await call('reconcile', 'rf_claims', { claim_id: 'C1', supplement: preview }, OWNER);
    const rc = r.body.worksheet.derived.find((d) => d.item_key === 'ridge_cap');
    assert.strictEqual(rc.status, 'matched');
    // ...but the stored inputs are untouched -- reconcile writes nothing.
    assert.ok(store.claims[0].data.supplement.adjuster_lines[0].quantity === 30);
  });
  await test('reconcile writes NOTHING — proven from the requests', async () => {
    await call('reconcile', 'rf_claims', { claim_id: 'C1' }, OWNER);
    const writes = requests.filter((q) => q.method === 'POST' && q.url.indexOf('license_keys') === -1);
    assert.deepStrictEqual(writes, []);
  });

  console.log('\nGate + honest failure:');
  await test('the assigned foreman can reconcile their own claim', async () => {
    assert.strictEqual((await call('reconcile', 'rf_claims', { claim_id: 'C1' }, FM)).code, 200);
  });
  await test('a different foreman is 403', async () => {
    assert.strictEqual((await call('reconcile', 'rf_claims', { claim_id: 'C1' }, FM2)).code, 403);
  });
  await test('no session is 401', async () => {
    assert.strictEqual((await call('reconcile', 'rf_claims', { claim_id: 'C1' })).code, 401);
  });
  await test('reconcile requires claim_id', async () => {
    assert.strictEqual((await call('reconcile', 'rf_claims', {}, OWNER)).code, 400);
  });
  await test('an unknown claim is 404', async () => {
    assert.strictEqual((await call('reconcile', 'rf_claims', { claim_id: 'NOPE' }, OWNER)).code, 404);
  });
  await test('a claim whose job has no measurement returns has_measurement:false, not a crash', async () => {
    store.jobs.push({ job_id: 'J2', data: {} });
    await call('write', 'rf_claims', { id: 'C2', job_id: 'J2', carrier: 'A', claim_number: 'Y', assigned_employee_id: 'FM', supplement: SUPP }, OWNER);
    const r = await call('reconcile', 'rf_claims', { claim_id: 'C2' }, OWNER);
    assert.strictEqual(r.code, 200);
    assert.strictEqual(r.body.has_measurement, false);
    // With no measurement every expected item is no_measurement, zero supplement.
    assert.ok(r.body.worksheet.derived.every((d) => d.status === 'no_measurement'));
    assert.strictEqual(r.body.worksheet.totals.derived_supplement, 0);
  });

  global.fetch = realFetch;
  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  if (failed > 0) process.exit(1);
})();
