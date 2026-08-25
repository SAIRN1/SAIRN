// api/_lib/roofing-programs-endpoint.test.js
// Round-trip tests for the Phase 4d rf_company_programs branches of
// api/sd-data.js, through the REAL handler with a stubbed Supabase.
// Run: node api/_lib/roofing-programs-endpoint.test.js
//
// What this proves that the pure engine cannot: the roster-share requirement is
// computed from the REAL rf_certifications store and the REAL employee roster
// read server-side (never from the caller), 'evaluate' writes nothing, and the
// whole resource is gated above the narrow tier -- a crew member must not be
// able to read an aggregate of how many colleagues hold a credential.

const assert = require('assert');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://stub.test';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'k';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || 'stub-secret';

const auth = require('./auth');
let requests = [];
let store = { programs: [], employees: [], certs: [] };

function jsonRes(status, body) { return Promise.resolve({ status, ok: status >= 200 && status < 300, json: () => Promise.resolve(body), text: () => Promise.resolve(JSON.stringify(body)) }); }

global.fetch = function (url, opts) {
  opts = opts || {};
  const u = String(url); const method = opts.method || 'GET';
  requests.push({ url: u, method, body: opts.body ? JSON.parse(opts.body) : null });
  if (u.indexOf('license_keys') !== -1) return jsonRes(200, [{ key: 'RF', status: 'active', app_id: 'sairnroofing', trial_ends_at: null, stripe_subscription_id: 's' }]);
  if (u.indexOf('rf_company_programs') !== -1) {
    if (method === 'POST') { const row = JSON.parse(opts.body); store.programs = store.programs.filter((p) => p.program_id !== row.program_id).concat([row]); return jsonRes(200, [row]); }
    return jsonRes(200, store.programs);
  }
  if (u.indexOf('sairnroofing_employee_auth') !== -1) return jsonRes(200, store.employees);
  if (u.indexOf('rf_certifications') !== -1) return jsonRes(200, store.certs);
  return jsonRes(404, { message: 'unexpected' });
};

const handler = require('../sd-data');
const licHash = require('crypto').createHash('sha256').update('RF').digest('hex');
function tok(emp, role) { return auth.signSessionToken({ license_hash: licHash, app: 'sairnroofing', employee_id: emp, role }); }
const OWNER = tok('OWN', 'owner');
const EST = tok('EST', 'estimator');
const FM = tok('FM', 'foreman');

let passed = 0, failed = 0;
async function test(name, fn) { requests = []; try { await fn(); passed++; console.log('  ok - ' + name); } catch (e) { failed++; console.error('  FAIL - ' + name); console.error('    ' + e.message); } }
async function call(action, resource, payload, token) {
  const out = { code: null, body: null };
  const res = { status(c) { out.code = c; return res; }, json(b) { out.body = b; return res; } };
  const h = { authorization: 'Bearer RF' }; if (token) h['x-sd-auth'] = token;
  await handler({ method: 'POST', headers: h, body: { action, resource, payload } }, res);
  return out;
}

// A real roster and real Phase 3a certification records.
store.employees = [
  { employee_id: 'OWN', role: 'owner', active: true },
  { employee_id: 'FM', role: 'foreman', active: true },
  { employee_id: 'C1', role: 'crew', active: true },
  { employee_id: 'C2', role: 'crew', active: true },
  { employee_id: 'GONE', role: 'crew', active: false }
];
store.certs = [
  { entry_id: 'E1', employee_id: 'FM', record_type: 'installer_cert', recorded_at: '2026-01-01', data: { credential: 'Master Craftsman', expires_on: '2027-06-01' } },
  { entry_id: 'E2', employee_id: 'C1', record_type: 'installer_cert', recorded_at: '2026-01-01', data: { credential: 'Master Craftsman', expires_on: '2026-02-01' } }, // EXPIRED
  { entry_id: 'E3', employee_id: 'C1', record_type: 'installer_cert', recorded_at: '2026-06-01', data: { credential: 'Master Craftsman', expires_on: '2028-01-01' } }, // supersedes E2
  { entry_id: 'E4', employee_id: 'GONE', record_type: 'installer_cert', recorded_at: '2026-01-01', data: { credential: 'Master Craftsman', has_expiry: false } }
];

const SHARE_REQ = {
  req_id: 'R1', label: 'Half the roster hold Master Craftsman',
  kind: 'employee_credential_share', credential: 'Master Craftsman',
  denominator: 'all_active', threshold: 50, source: 'our programme agreement rev C'
};
const ATTESTED_REQ = {
  req_id: 'R2', label: 'General liability', kind: 'insurance_minimum',
  threshold: 1000000, unit: 'USD', attested_value: 2000000,
  attested_on: '2026-08-01', source: 'our COI'
};

(async () => {
  console.log('\nGating -- company standing is management-level:');
  await test('management can write a programme', async () => {
    const r = await call('write', 'rf_company_programs', {
      id: 'RFPRG-1', manufacturer: 'TestCo', program_name: 'Test Elite',
      status: 'not_enrolled', requirements: [SHARE_REQ, ATTESTED_REQ]
    }, OWNER);
    assert.strictEqual(r.code, 200);
  });
  await test('an estimator can READ but not WRITE', async () => {
    assert.strictEqual((await call('read', 'rf_company_programs', {}, EST)).code, 200);
    assert.strictEqual((await call('write', 'rf_company_programs', { id: 'X', manufacturer: 'M', program_name: 'N' }, EST)).code, 403);
  });
  await test('a FOREMAN cannot read it at all -> 403', async () => {
    // The share requirement exposes how many colleagues hold a credential.
    // That aggregate is not a crew member's business, which is why this is
    // gated harder than rf_certifications' own evaluate.
    const r = await call('read', 'rf_company_programs', {}, FM);
    assert.strictEqual(r.code, 403);
    assert.strictEqual(r.body.data, undefined);
  });
  await test('a foreman cannot evaluate either -> 403, with no programmes leaked', async () => {
    const r = await call('evaluate', 'rf_company_programs', {}, FM);
    assert.strictEqual(r.code, 403);
    assert.strictEqual(r.body.programs, undefined);
  });
  await test('no session -> 401 on both verbs', async () => {
    assert.strictEqual((await call('read', 'rf_company_programs', {}, null)).code, 401);
    assert.strictEqual((await call('evaluate', 'rf_company_programs', {}, null)).code, 401);
  });
  await test('updated_by is server-stamped, not taken from the caller', async () => {
    const r = await call('write', 'rf_company_programs', {
      id: 'RFPRG-STAMP', manufacturer: 'TestCo', program_name: 'Stamp', updated_by: 'SOMEONE-ELSE'
    }, OWNER);
    assert.strictEqual(r.code, 200);
    const posted = requests.filter((q) => q.method === 'POST' && q.url.indexOf('rf_company_programs') !== -1).pop();
    assert.strictEqual(posted.body.updated_by, 'OWN');
  });
  await test('a programme with no manufacturer is refused -> 400', async () => {
    const r = await call('write', 'rf_company_programs', { id: 'X', program_name: 'N' }, OWNER);
    assert.strictEqual(r.code, 400);
    assert.match(r.body.error.message, /manufacturer/);
  });

  console.log('\nThe rollup is computed from the REAL 3a store:');
  await test('the share uses the live roster and live certification records', async () => {
    // Active pool = OWN, FM, C1, C2 (4). Current Master Craftsman holders:
    // FM (E1) and C1 (E3 supersedes the expired E2). GONE is inactive and must
    // not count even though their card never expires. 2/4 = 50%.
    const r = await call('evaluate', 'rf_company_programs', { today: '2026-08-25' }, OWNER);
    assert.strictEqual(r.code, 200);
    const prog = r.body.programs.filter((p) => p.program_id === 'RFPRG-1')[0];
    const share = prog.requirements.filter((q) => q.req_id === 'R1')[0];
    assert.strictEqual(share.basis, 'computed');
    assert.strictEqual(share.pool_size, 4);
    assert.strictEqual(share.holders, 2);
    assert.strictEqual(share.actual, 50);
    assert.deepStrictEqual(share.holder_ids.sort(), ['C1', 'FM']);
  });
  await test('latestByKey is applied -- the superseded EXPIRED record does not win', async () => {
    const r = await call('evaluate', 'rf_company_programs', { today: '2026-08-25' }, OWNER);
    const share = r.body.programs.filter((p) => p.program_id === 'RFPRG-1')[0].requirements[0];
    assert.ok(share.holder_ids.indexOf('C1') !== -1, 'C1 holds the later, unexpired card');
  });
  await test('roster_size counts only ACTIVE employees', async () => {
    const r = await call('evaluate', 'rf_company_programs', {}, OWNER);
    assert.strictEqual(r.body.roster_size, 4);
  });
  await test('the caller CANNOT supply the roster or the certifications', async () => {
    const r = await call('evaluate', 'rf_company_programs', {
      today: '2026-08-25',
      roster: [{ employee_id: 'FAKE', role: 'crew', active: true }],
      certifications: [{ employee_id: 'FAKE', record_type: 'installer_cert', credential: 'Master Craftsman', has_expiry: false }]
    }, OWNER);
    const share = r.body.programs.filter((p) => p.program_id === 'RFPRG-1')[0].requirements[0];
    assert.strictEqual(share.pool_size, 4);          // still the real roster
    assert.ok(share.holder_ids.indexOf('FAKE') === -1);
  });
  await test('the attested requirement is counted but marked self-reported', async () => {
    const r = await call('evaluate', 'rf_company_programs', { today: '2026-08-25' }, OWNER);
    const prog = r.body.programs.filter((p) => p.program_id === 'RFPRG-1')[0];
    const att = prog.requirements.filter((q) => q.req_id === 'R2')[0];
    assert.strictEqual(att.basis, 'attested');
    assert.strictEqual(att.status, 'met');
    assert.match(att.detail, /self-reported, not verified/);
  });
  await test('the verdict is appears_met, and never the word eligible', async () => {
    const r = await call('evaluate', 'rf_company_programs', { today: '2026-08-25' }, OWNER);
    const prog = r.body.programs.filter((p) => p.program_id === 'RFPRG-1')[0];
    assert.strictEqual(prog.verdict, 'appears_met');
    assert.ok(JSON.stringify(prog.verdict).indexOf('eligible') === -1);
  });
  await test('the not-regulatory disclosure comes back over the wire', async () => {
    const r = await call('evaluate', 'rf_company_programs', {}, OWNER);
    const prog = r.body.programs.filter((p) => p.program_id === 'RFPRG-1')[0];
    assert.match(prog.disclosures.not_regulatory, /voluntary and commercial/);
    assert.match(prog.disclosures.thresholds_are_yours, /not verified against TestCo/);
  });

  console.log('\nevaluate is compute-only:');
  await test('evaluate WRITES NOTHING', async () => {
    requests = [];
    await call('evaluate', 'rf_company_programs', {}, OWNER);
    const writes = requests.filter((q) => q.method !== 'GET' && q.url.indexOf('license_keys') === -1);
    assert.strictEqual(writes.length, 0, JSON.stringify(writes.map((w) => w.url)));
  });
  await test('a programme with no requirements says so rather than passing', async () => {
    const r = await call('evaluate', 'rf_company_programs', {}, OWNER);
    const stamp = r.body.programs.filter((p) => p.program_id === 'RFPRG-STAMP')[0];
    assert.strictEqual(stamp.verdict, 'no_requirements_entered');
  });

  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  if (failed) process.exit(1);
})();
