// api/_lib/roofing-claims-endpoint.test.js
// Round-trip tests for the rf_claims / rf_claim_photos branches of
// api/sd-data.js, through the REAL handler with a stubbed Supabase.
// Run: node api/_lib/roofing-claims-endpoint.test.js
//
// Substitute for the live round trip (schema not yet run). Proves the handler's
// own logic: the assignment gate, the money-field separation on the way in and
// the derived summary on the way out, rf_claims mutability vs rf_claim_photos
// append-only, and evidence visibility following the claim's own gate.

const assert = require('assert');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://stub.test';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'k';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || 'stub-secret-for-tests';

const auth = require('./auth');
const realFetch = global.fetch;
let requests = [];
let store = { claims: [], photos: [] };
let tablesExist = true;

function jsonRes(status, body) {
  return Promise.resolve({ status, ok: status >= 200 && status < 300, json: () => Promise.resolve(body), text: () => Promise.resolve(JSON.stringify(body)) });
}
function parseEqClaim(u) { const m = u.match(/claim_id=eq\.([^&]+)/); return m ? decodeURIComponent(m[1]) : null; }

global.fetch = function (url, opts) {
  opts = opts || {};
  const u = String(url);
  const method = opts.method || 'GET';
  requests.push({ url: u, method, prefer: (opts.headers || {}).Prefer || null, body: opts.body ? JSON.parse(opts.body) : null });
  if (u.indexOf('license_keys') !== -1) return jsonRes(200, [{ key: 'RF', status: 'active', app_id: 'sairnroofing', trial_ends_at: null, stripe_subscription_id: 's' }]);
  if (!tablesExist) return jsonRes(400, { message: 'relation "rf_claims" does not exist' });
  if (u.indexOf('rf_claim_photos') !== -1) {
    if (method === 'POST') {
      const row = JSON.parse(opts.body);
      if (store.photos.some((p) => p.photo_id === row.photo_id)) return jsonRes(409, { message: 'duplicate key value violates unique constraint' });
      store.photos.push(row); return jsonRes(200, [row]);
    }
    const cid = parseEqClaim(u);
    return jsonRes(200, store.photos.filter((p) => !cid || p.claim_id === cid));
  }
  if (u.indexOf('rf_claims') !== -1) {
    if (method === 'POST') {
      const row = JSON.parse(opts.body);
      store.claims = store.claims.filter((c) => c.claim_id !== row.claim_id).concat([row]);
      return jsonRes(200, [row]);
    }
    const cid = parseEqClaim(u);
    return jsonRes(200, store.claims.filter((c) => !cid || c.claim_id === cid));
  }
  return jsonRes(404, { message: 'unexpected' });
};

const handler = require('../sd-data');
const licHash = require('crypto').createHash('sha256').update('RF').digest('hex');
function tokenFor(emp, role) { return auth.signSessionToken({ license_hash: licHash, app: 'sairnroofing', employee_id: emp, role }); }
const OWNER = tokenFor('OWN', 'owner');
const FOREMAN = tokenFor('FM', 'foreman');   // narrow role
const FOREMAN2 = tokenFor('FM2', 'foreman');

let passed = 0, failed = 0;
async function test(name, fn) { requests = []; try { await fn(); passed++; console.log('  ok - ' + name); } catch (e) { failed++; console.error('  FAIL - ' + name); console.error('    ' + e.message); } }
async function call(action, resource, payload, token) {
  const out = { code: null, body: null };
  const res = { status(c) { out.code = c; return res; }, json(b) { out.body = b; return res; } };
  const h = { authorization: 'Bearer RF' }; if (token) h['x-sd-auth'] = token;
  await handler({ method: 'POST', headers: h, body: { action, resource, payload } }, res);
  return out;
}

(async () => {
  console.log('Claim write + money separation:');
  await test('no session is refused', async () => {
    assert.strictEqual((await call('write', 'rf_claims', { id: 'C1' })).code, 401);
  });
  await test('a claim missing carrier/claim_number is refused', async () => {
    const r = await call('write', 'rf_claims', { id: 'C1', job_id: 'J1' }, OWNER);
    assert.strictEqual(r.code, 400);
    assert.ok(/carrier/.test(r.body.error.message) && /claim_number/.test(r.body.error.message));
  });
  await test('a valid claim writes, and the money fields are stored SEPARATELY', async () => {
    const r = await call('write', 'rf_claims', {
      id: 'C1', job_id: 'J1', carrier: 'State Farm', claim_number: 'SF-1', assigned_employee_id: 'FM',
      status: 'scope_written', peril: 'hail', policy_type: 'RCV',
      rcv: 20000, depreciation: 6000, acv: 13000, deductible: 1000
    }, OWNER);
    assert.strictEqual(r.code, 200);
    const stored = store.claims[0].data;
    assert.strictEqual(stored.rcv, 20000);
    assert.strictEqual(stored.depreciation, 6000);
    assert.strictEqual(stored.acv, 13000);      // stored as entered, NOT rcv-dep=14000
    assert.strictEqual(stored.deductible, 1000);
    assert.ok(!('amount' in stored) && !('total' in stored), 'no collapsed total invented');
    // The derived summary is NOT persisted.
    assert.ok(!('money_summary' in stored), 'money_summary must not be stored');
  });
  await test('the write response carries a DERIVED money_summary that flags the acv mismatch', async () => {
    const r = await call('write', 'rf_claims', {
      id: 'C1', job_id: 'J1', carrier: 'State Farm', claim_number: 'SF-1', assigned_employee_id: 'FM',
      rcv: 20000, depreciation: 6000, acv: 13000
    }, OWNER);
    const s = r.body.data.money_summary;
    assert.strictEqual(s.entered.acv, 13000);
    assert.strictEqual(s.derived.acv_implied, 14000);
    assert.strictEqual(s.derived.acv_mismatch, true);
  });
  await test('a bad status is refused with the real enum', async () => {
    const r = await call('write', 'rf_claims', { id: 'C9', job_id: 'J1', carrier: 'A', claim_number: 'X', status: 'flying' }, OWNER);
    assert.strictEqual(r.code, 400);
    assert.ok(/loss_reported/.test(r.body.error.message));
  });
  await test('a negative money amount is refused', async () => {
    const r = await call('write', 'rf_claims', { id: 'C8', job_id: 'J1', carrier: 'A', claim_number: 'X', rcv: -1 }, OWNER);
    assert.strictEqual(r.code, 400);
    assert.ok(/rcv/.test(r.body.error.message));
  });

  console.log('\nMutable claim vs append-only evidence:');
  await test('rf_claims write is an UPSERT (it is mutable)', async () => {
    await call('write', 'rf_claims', { id: 'C1', job_id: 'J1', carrier: 'State Farm', claim_number: 'SF-1', assigned_employee_id: 'FM', status: 'install_complete' }, OWNER);
    const q = requests.filter((r) => r.method === 'POST' && r.url.indexOf('rf_claims') !== -1)[0];
    assert.ok(q.url.indexOf('on_conflict') !== -1, 'claims must upsert');
    assert.ok(String(q.prefer).indexOf('merge-duplicates') !== -1);
    assert.strictEqual(store.claims.length, 1, 'same claim updated in place, not duplicated');
    assert.strictEqual(store.claims[0].status, 'install_complete');
  });

  console.log('\nAssignment gate:');
  await test('the assigned foreman can update their own claim but NOT reassign it', async () => {
    const r = await call('write', 'rf_claims', { id: 'C1', job_id: 'J1', carrier: 'State Farm', claim_number: 'SF-1', assigned_employee_id: 'FM2', status: 'depreciation_released' }, FOREMAN);
    assert.strictEqual(r.code, 200);
    assert.strictEqual(store.claims[0].assigned_employee_id, 'FM', 'a narrow role cannot reassign — stays FM');
    assert.strictEqual(store.claims[0].status, 'depreciation_released', 'but their content edit landed');
  });
  await test('a different foreman cannot touch a claim not assigned to them', async () => {
    const r = await call('write', 'rf_claims', { id: 'C1', job_id: 'J1', carrier: 'X', claim_number: 'Y', status: 'loss_reported' }, FOREMAN2);
    assert.strictEqual(r.code, 403);
  });
  await test('a foreman reads only their own claims', async () => {
    await call('write', 'rf_claims', { id: 'C2', job_id: 'J2', carrier: 'Allstate', claim_number: 'AL-2', assigned_employee_id: 'FM2' }, OWNER);
    const own = await call('read', 'rf_claims', {}, FOREMAN);
    assert.ok(own.body.data.every((c) => c.assigned_employee_id === 'FM'));
    const mgmt = await call('read', 'rf_claims', {}, OWNER);
    assert.strictEqual(mgmt.body.data.length, 2, 'management sees both');
  });
  await test('read attaches a money_summary and the status list', async () => {
    const r = await call('read', 'rf_claims', {}, OWNER);
    assert.ok(r.body.data[0].money_summary);
    assert.strictEqual(r.body.statuses.length, 7);
  });

  console.log('\nEvidence photos — append-only, visibility follows the claim:');
  await test('a photo needs an existing claim', async () => {
    const r = await call('write', 'rf_claim_photos', { id: 'P1', claim_id: 'NOPE', phase: 'tear_off' }, OWNER);
    assert.strictEqual(r.code, 404);
    assert.strictEqual(r.body.error.code, 'NO_CLAIM');
  });
  await test('a valid photo writes append-only, stamped with the capturer', async () => {
    const r = await call('write', 'rf_claim_photos', { id: 'P1', claim_id: 'C1', phase: 'tear_off', elevation: 'rear', damage_type: 'deck_rot' }, FOREMAN);
    assert.strictEqual(r.code, 200);
    const q = requests.filter((x) => x.method === 'POST' && x.url.indexOf('rf_claim_photos') !== -1)[0];
    assert.strictEqual(q.url.indexOf('on_conflict'), -1, 'evidence must not upsert');
    assert.strictEqual(q.body.captured_by, 'FM');
  });
  await test('reusing a photo id is refused, not merged', async () => {
    const r = await call('write', 'rf_claim_photos', { id: 'P1', claim_id: 'C1', phase: 'completion' }, FOREMAN);
    assert.strictEqual(r.code, 409);
  });
  await test('a foreman cannot attach evidence to another foreman\'s claim', async () => {
    const r = await call('write', 'rf_claim_photos', { id: 'P2', claim_id: 'C2', phase: 'tear_off' }, FOREMAN);
    assert.strictEqual(r.code, 403);
  });
  await test('evidence read requires claim_id and follows the same gate', async () => {
    assert.strictEqual((await call('read', 'rf_claim_photos', {}, OWNER)).code, 400);
    const own = await call('read', 'rf_claim_photos', { claim_id: 'C1' }, FOREMAN);
    assert.strictEqual(own.code, 200);
    assert.strictEqual(own.body.data.length, 1);
    const blocked = await call('read', 'rf_claim_photos', { claim_id: 'C2' }, FOREMAN);
    assert.strictEqual(blocked.code, 403);
  });

  console.log('\nHonest failure before migration:');
  await test('read reports provisioned:false, write names the SQL file', async () => {
    tablesExist = false;
    assert.strictEqual((await call('read', 'rf_claims', {}, OWNER)).body.provisioned, false);
    const w = await call('write', 'rf_claims', { id: 'C1', job_id: 'J1', carrier: 'A', claim_number: 'X' }, OWNER);
    assert.strictEqual(w.code, 503);
    assert.ok(w.body.error.message.indexOf('sairnroofing_claims_schema.sql') !== -1);
    tablesExist = true;
  });

  global.fetch = realFetch;
  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  if (failed > 0) process.exit(1);
})();
