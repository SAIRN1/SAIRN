// api/_lib/roofing-credentials-endpoint.test.js
// Round-trip tests for the rf_cert_rules / rf_certifications branches of
// api/sd-data.js, through the REAL exported handler with a stubbed Supabase.
// Run: node api/_lib/roofing-credentials-endpoint.test.js
//
// A SUBSTITUTE for the live round trip, not a replacement:
// sql/sairnroofing_certifications_schema.sql has not been run in Supabase.
// This proves the handler's own logic -- role gating, self-read narrowing,
// append-only insert, the expiry-unspecified refusal, evaluate wiring.
//
// The role gate is the part most worth testing here rather than live: it
// decides who may assert a qualification about whom, and a live test would
// need four real sessions to cover what four stubbed tokens cover exactly.

const assert = require('assert');

process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://stub.supabase.test';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'stub-key';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || 'stub-session-signing-secret-for-tests';

const auth = require('./auth');
const realFetch = global.fetch;
let requests = [];
let store = { rules: [], certs: [] };
let tablesExist = true;

function jsonRes(status, body) {
  return Promise.resolve({
    status: status, ok: status >= 200 && status < 300,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body))
  });
}

global.fetch = function (url, opts) {
  opts = opts || {};
  const u = String(url);
  requests.push({ url: u, method: opts.method || 'GET', prefer: (opts.headers || {}).Prefer || null, body: opts.body ? JSON.parse(opts.body) : null });
  if (u.indexOf('license_keys') !== -1) {
    return jsonRes(200, [{ key: 'RF-TEST', status: 'active', app_id: 'sairnroofing', trial_ends_at: null, stripe_subscription_id: 'sub_x' }]);
  }
  if (!tablesExist) return jsonRes(400, { message: 'relation "rf_certifications" does not exist' });
  if (u.indexOf('rf_cert_rules') !== -1) {
    if ((opts.method || 'GET') === 'POST') {
      const row = JSON.parse(opts.body);
      store.rules = store.rules.filter((r) => r.rule_id !== row.rule_id).concat([row]);
      return jsonRes(200, [row]);
    }
    return jsonRes(200, store.rules);
  }
  if (u.indexOf('rf_certifications') !== -1) {
    if ((opts.method || 'GET') === 'POST') {
      const row = JSON.parse(opts.body);
      if (store.certs.some((c) => c.entry_id === row.entry_id)) {
        return jsonRes(409, { message: 'duplicate key value violates unique constraint' });
      }
      row.recorded_at = new Date(Date.now() + store.certs.length * 1000).toISOString();
      store.certs.push(row);
      return jsonRes(200, [row]);
    }
    return jsonRes(200, store.certs);
  }
  return jsonRes(404, { message: 'unexpected table' });
};

const handler = require('../sd-data');

// Real session tokens, minted by the real signer -- not hand-faked strings.
const LICENSE = 'RF-TEST';
const licHash = require('crypto').createHash('sha256').update(LICENSE).digest('hex');
function tokenFor(employeeId, role) {
  return auth.signSessionToken({ license_hash: licHash, app: 'sairnroofing', employee_id: employeeId, role: role });
}

let passed = 0, failed = 0;
async function test(name, fn) {
  requests = [];
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (err) { failed++; console.error('  FAIL - ' + name); console.error('    ' + err.message); }
}

async function call(action, resource, payload, token) {
  const out = { code: null, body: null };
  const res = { status(c) { out.code = c; return res; }, json(b) { out.body = b; return res; } };
  const headers = { authorization: 'Bearer ' + LICENSE };
  if (token) headers['x-sd-auth'] = token;
  await handler({ method: 'POST', headers: headers, body: { action, resource, payload } }, res);
  return out;
}

const OWNER = tokenFor('EMP-OWNER', 'owner');
const ESTIMATOR = tokenFor('EMP-EST', 'estimator');
const CREW_A = tokenFor('EMP-A', 'crew');
const CREW_B = tokenFor('EMP-B', 'crew');

const RULE = {
  rule_id: 'OH-ROOFING-NO-STATE-LICENSE', state: 'OH', requirement_type: 'state_licensing',
  effective_from: '2003-01-01', status: 'active',
  data: {
    state_license_required: false,
    licensed_trades: ['HVAC', 'refrigeration', 'electrical', 'plumbing', 'hydronics'],
    authority: { citation: 'ORC 4740.01', url: 'https://codes.ohio.gov/ohio-revised-code/section-4740.01', quote: 'the word "roofing" does not appear', read_on: '2026-08-24' }
  }
};

(async () => {
  console.log('Auth gating:');
  await test('no session is refused on every action', async () => {
    for (const a of ['read', 'write', 'evaluate']) {
      const r = await call(a, 'rf_certifications', {});
      assert.strictEqual(r.code, 401, a + ' should 401');
    }
  });
  await test('a crew member cannot write a rule', async () => {
    const r = await call('write', 'rf_cert_rules', RULE, CREW_A);
    assert.strictEqual(r.code, 403);
  });
  await test('a crew member cannot record a certification — not even their own', async () => {
    const r = await call('write', 'rf_certifications', {
      id: 'RFCERT-SELF', employee_id: 'EMP-A', record_type: 'osha_card', has_expiry: false
    }, CREW_A);
    assert.strictEqual(r.code, 403);
    assert.strictEqual(store.certs.length, 0, 'self-certification must not reach the store');
  });

  console.log('\nRules — citation required:');
  await test('a rule with no authority is refused', async () => {
    const bad = JSON.parse(JSON.stringify(RULE));
    delete bad.data.authority;
    const r = await call('write', 'rf_cert_rules', bad, OWNER);
    assert.strictEqual(r.code, 400);
    assert.strictEqual(r.body.error.code, 'NO_AUTHORITY');
  });
  await test('a cited rule writes, reads back, and records who verified it', async () => {
    assert.strictEqual((await call('write', 'rf_cert_rules', RULE, OWNER)).code, 200);
    const r = await call('read', 'rf_cert_rules', {}, CREW_A);
    assert.strictEqual(r.code, 200, 'crew may READ rules — they need to know their own trade');
    assert.strictEqual(r.body.data[0].data.state_license_required, false);
    assert.strictEqual(store.rules[0].verified_by, 'EMP-OWNER');
  });

  console.log('\nCertifications — the expiry contract:');
  await test('a record with neither expires_on nor has_expiry:false is refused', async () => {
    const r = await call('write', 'rf_certifications', {
      id: 'RFCERT-X', employee_id: 'EMP-A', record_type: 'safety_training', credential: 'Fall Protection'
    }, OWNER);
    assert.strictEqual(r.code, 400);
    assert.strictEqual(r.body.error.code, 'EXPIRY_UNSPECIFIED');
  });
  await test('has_expiry:false is accepted with no date — a lifetime OSHA card', async () => {
    const r = await call('write', 'rf_certifications', {
      id: 'RFCERT-1', employee_id: 'EMP-A', record_type: 'osha_card',
      credential: 'OSHA 30', has_expiry: false
    }, OWNER);
    assert.strictEqual(r.code, 200);
  });
  await test('a dated record is accepted', async () => {
    const r = await call('write', 'rf_certifications', {
      id: 'RFCERT-2', employee_id: 'EMP-A', record_type: 'safety_training',
      credential: 'Fall Protection', expires_on: '2026-09-23'
    }, OWNER);
    assert.strictEqual(r.code, 200);
  });
  await test('an unknown record_type is refused', async () => {
    const r = await call('write', 'rf_certifications', {
      id: 'RFCERT-Y', employee_id: 'EMP-A', record_type: 'gaf_master_elite', has_expiry: false
    }, OWNER);
    assert.strictEqual(r.code, 400);
  });
  await test('the write is a plain INSERT and stamps recorded_by from the token', async () => {
    const ins = requests.filter((q) => q.method === 'POST' && q.url.indexOf('rf_certifications') !== -1).slice(-1)[0];
    await call('write', 'rf_certifications', {
      id: 'RFCERT-3', employee_id: 'EMP-B', record_type: 'installer_cert',
      credential: 'Tesla Certified', expires_on: '2027-06-01'
    }, OWNER);
    const q = requests.filter((r) => r.method === 'POST' && r.url.indexOf('rf_certifications') !== -1).slice(-1)[0];
    assert.strictEqual(q.url.indexOf('on_conflict'), -1, 'must not upsert');
    assert.strictEqual(String(q.prefer).indexOf('merge-duplicates'), -1, 'must not merge');
    assert.strictEqual(q.body.data.recorded_by, 'EMP-OWNER');
  });
  await test('reusing an entry id is refused, not merged', async () => {
    const r = await call('write', 'rf_certifications', {
      id: 'RFCERT-1', employee_id: 'EMP-A', record_type: 'osha_card', has_expiry: false
    }, OWNER);
    assert.strictEqual(r.code, 409);
    assert.strictEqual(r.body.error.code, 'DUPLICATE_ENTRY');
  });

  console.log('\nSelf-read narrowing — derived from the token, never the payload:');
  await test('management sees every record', async () => {
    const r = await call('read', 'rf_certifications', {}, OWNER);
    assert.strictEqual(r.body.data.length, 3);
  });
  await test('a broad-read role sees every record', async () => {
    const r = await call('read', 'rf_certifications', {}, ESTIMATOR);
    assert.strictEqual(r.body.data.length, 3);
  });
  await test('crew A sees ONLY their own two records', async () => {
    const r = await call('read', 'rf_certifications', {}, CREW_A);
    assert.strictEqual(r.body.data.length, 2);
    assert.ok(r.body.data.every((x) => x.employee_id === 'EMP-A'));
  });
  await test('crew B cannot widen their view by claiming another employee_id', async () => {
    const r = await call('read', 'rf_certifications', { employee_id: 'EMP-A' }, CREW_B);
    assert.strictEqual(r.body.data.length, 1);
    assert.strictEqual(r.body.data[0].employee_id, 'EMP-B');
  });

  console.log('\nEvaluate — compute-only:');
  await test('the board classifies the 30-day boundary exactly', async () => {
    const r = await call('evaluate', 'rf_certifications', { today: '2026-08-24' }, OWNER);
    assert.strictEqual(r.code, 200);
    const fall = r.body.board.items.find((i) => i.entry_id === 'RFCERT-2');
    assert.strictEqual(fall.days, 30);
    assert.strictEqual(fall.status, 'expiring');
  });
  await test('the lifetime card reads current, and is not action_required', async () => {
    const r = await call('evaluate', 'rf_certifications', { today: '2026-08-24' }, OWNER);
    const card = r.body.board.items.find((i) => i.entry_id === 'RFCERT-1');
    assert.strictEqual(card.status, 'current');
    assert.strictEqual(card.no_expiry, true);
    assert.strictEqual(r.body.board.action_required, 1);
  });
  await test('the Ohio licensing answer comes back sourced when a state is asked', async () => {
    const r = await call('evaluate', 'rf_certifications', { today: '2026-08-24', state: 'OH' }, OWNER);
    assert.strictEqual(r.body.licensing.ok, true);
    assert.strictEqual(r.body.licensing.rule.data.state_license_required, false);
  });
  await test('an unseeded state refuses by name inside the board response', async () => {
    const r = await call('evaluate', 'rf_certifications', { today: '2026-08-24', state: 'CA' }, OWNER);
    assert.strictEqual(r.body.licensing.ok, false);
    assert.strictEqual(r.body.licensing.error.code, 'NO_RULE_FOR_STATE');
    assert.deepStrictEqual(r.body.coverage.uncovered_states, ['CA']);
  });
  await test('crew A\'s board contains only crew A\'s records', async () => {
    const r = await call('evaluate', 'rf_certifications', { today: '2026-08-24' }, CREW_A);
    assert.ok(r.body.board.items.every((i) => i.employee_id === 'EMP-A'));
  });
  await test('evaluate writes NOTHING — proven from the requests issued', async () => {
    await call('evaluate', 'rf_certifications', { today: '2026-08-24' }, OWNER);
    const writes = requests.filter((q) => q.method === 'POST' && q.url.indexOf('license_keys') === -1);
    assert.deepStrictEqual(writes, []);
  });

  console.log('\nHonest failure before the migration is run:');
  await test('read reports provisioned:false', async () => {
    tablesExist = false;
    const r = await call('read', 'rf_certifications', {}, OWNER);
    assert.strictEqual(r.code, 200);
    assert.strictEqual(r.body.provisioned, false);
  });
  await test('write names the exact SQL file', async () => {
    const r = await call('write', 'rf_certifications', {
      id: 'RFCERT-9', employee_id: 'EMP-A', record_type: 'osha_card', has_expiry: false
    }, OWNER);
    assert.strictEqual(r.code, 503);
    assert.ok(r.body.error.message.indexOf('sairnroofing_certifications_schema.sql') !== -1);
  });
  await test('evaluate degrades to provisioned:false, never a fake empty board', async () => {
    const r = await call('evaluate', 'rf_certifications', {}, OWNER);
    assert.strictEqual(r.body.provisioned, false);
    assert.strictEqual(r.body.board, null);
    tablesExist = true;
  });

  global.fetch = realFetch;
  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  if (failed > 0) process.exit(1);
})();
