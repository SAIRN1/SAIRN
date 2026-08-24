// api/_lib/dental-credentials-endpoint.test.js
// Round-trip tests for the dnt_cred_rules / dnt_credentials branches of
// api/sd-data.js, driven through the REAL exported handler with a stubbed
// Supabase REST layer.
// Run: node api/_lib/dental-credentials-endpoint.test.js
//
// WHY A STUB AND NOT THE LIVE DATABASE: these tables need
// sql/sairndental_credentials_schema.sql run in Supabase, which this session
// has no access to do. This file is therefore a SUBSTITUTE for the live
// write/read-back, not a replacement for it -- it proves the handler's own
// logic (append-only insert, the citation requirement, evaluate wiring,
// NOT_PROVISIONED honesty) against a fake store. The live round trip against
// production still has to be run once the migration is applied.
//
// The stub records every outbound request, so the tests can assert on the
// HTTP VERB AND HEADERS the handler actually used -- which is the only way to
// prove "append-only" mechanically: an upsert and an insert both return 200,
// and only the Prefer header tells them apart.

const assert = require('assert');

process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://stub.supabase.test';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'stub-service-key';

const realFetch = global.fetch;
let requests = [];
let store = { rules: [], creds: [] };
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

  // License validation (api/_lib/license.js) goes through the same fetch.
  if (u.indexOf('license_keys') !== -1) {
    return jsonRes(200, [{ key: 'DNT-TEST', status: 'active', app_id: 'sairndental', license_hash: 'HASH', trial_ends_at: null, stripe_subscription_id: 'sub_x' }]);
  }
  if (!tablesExist) return jsonRes(400, { message: 'relation "dnt_credentials" does not exist' });

  if (u.indexOf('dnt_cred_rules') !== -1) {
    if ((opts.method || 'GET') === 'POST') {
      const row = JSON.parse(opts.body);
      store.rules = store.rules.filter((r) => r.rule_id !== row.rule_id).concat([row]);
      return jsonRes(200, [row]);
    }
    return jsonRes(200, store.rules);
  }
  if (u.indexOf('dnt_credentials') !== -1) {
    if ((opts.method || 'GET') === 'POST') {
      const row = JSON.parse(opts.body);
      if (store.creds.some((c) => c.entry_id === row.entry_id)) {
        return jsonRes(409, { message: 'duplicate key value violates unique constraint' });
      }
      row.recorded_at = new Date(Date.now() + store.creds.length * 1000).toISOString();
      store.creds.push(row);
      return jsonRes(200, [row]);
    }
    return jsonRes(200, store.creds);
  }
  return jsonRes(404, { message: 'unexpected table' });
};

const handler = require('../sd-data');

let passed = 0, failed = 0;
async function test(name, fn) {
  requests = [];
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (err) { failed++; console.error('  FAIL - ' + name); console.error('    ' + err.message); }
}

async function call(action, resource, payload) {
  const out = { code: null, body: null };
  const res = { status(c) { out.code = c; return res; }, json(b) { out.body = b; return res; } };
  await handler({ method: 'POST', headers: { authorization: 'Bearer DNT-TEST' }, body: { action, resource, payload } }, res);
  return out;
}

const RULE = {
  rule_id: 'OH-CE-DENTIST-BIENNIAL', state: 'OH', requirement_type: 'continuing_education',
  role: 'dentist', effective_from: '1995-01-01', status: 'active',
  data: {
    hours_required: 30,
    authority: { citation: 'ORC 4715.141(A)', url: 'https://codes.ohio.gov/ohio-revised-code/section-4715.141', quote: 'Each licensed dentist shall complete biennially not less than thirty hours of continuing dental education', read_on: '2026-08-24' }
  }
};

(async () => {
  console.log('Rules — write, read back, and the citation requirement:');

  await test('a rule without data.authority is REFUSED', async () => {
    const r = await call('write', 'dnt_cred_rules', Object.assign({}, RULE, { data: { hours_required: 30 } }));
    assert.strictEqual(r.code, 400);
    assert.strictEqual(r.body.error.code, 'NO_AUTHORITY');
    assert.strictEqual(store.rules.length, 0, 'nothing should have been stored');
  });

  await test('a rule missing only the quote is still refused', async () => {
    const noQuote = JSON.parse(JSON.stringify(RULE));
    delete noQuote.data.authority.quote;
    const r = await call('write', 'dnt_cred_rules', noQuote);
    assert.strictEqual(r.body.error.code, 'NO_AUTHORITY');
  });

  await test('a fully cited rule writes and reads back intact', async () => {
    const w = await call('write', 'dnt_cred_rules', RULE);
    assert.strictEqual(w.code, 200);
    const r = await call('read', 'dnt_cred_rules', {});
    assert.strictEqual(r.code, 200);
    assert.strictEqual(r.body.data.length, 1);
    assert.strictEqual(r.body.data[0].rule_id, 'OH-CE-DENTIST-BIENNIAL');
    assert.strictEqual(r.body.data[0].data.hours_required, 30);
    assert.strictEqual(r.body.data[0].data.authority.citation, 'ORC 4715.141(A)');
    assert.ok(r.body.coverage.covered_states.indexOf('OH') !== -1);
  });

  console.log('\nCredential records — append-only, proven from the request itself:');

  await test('a write is a plain INSERT, never an upsert', async () => {
    const w = await call('write', 'dnt_credentials', {
      id: 'DCRED-1', provider_id: 'PV-1', record_type: 'state_license',
      state: 'OH', number: 'D-12345', expires_on: '2026-09-23'
    });
    assert.strictEqual(w.code, 200);
    const insert = requests.filter((q) => q.method === 'POST' && q.url.indexOf('dnt_credentials') !== -1)[0];
    assert.ok(insert, 'no insert was issued');
    // The proof: no on_conflict in the URL, and no merge-duplicates in Prefer.
    assert.strictEqual(insert.url.indexOf('on_conflict'), -1, 'URL must not carry on_conflict');
    assert.strictEqual(String(insert.prefer).indexOf('merge-duplicates'), -1, 'Prefer must not merge duplicates');
    // license_hash is DERIVED (sha256 of the bearer key) by api/_lib/license.js,
    // not taken from the license_keys row -- asserted as a real hash rather
    // than a literal so this test cannot pass on a trusted-from-the-row value.
    assert.ok(/^[0-9a-f]{64}$/.test(insert.body.license_hash), 'license_hash must be a derived sha256');
    assert.strictEqual(insert.body.app_id, 'sairndental');
  });

  await test('reusing an entry id is refused as a duplicate, not silently merged', async () => {
    const w = await call('write', 'dnt_credentials', {
      id: 'DCRED-1', provider_id: 'PV-1', record_type: 'state_license', state: 'OH', expires_on: '2030-01-01'
    });
    assert.strictEqual(w.code, 409);
    assert.strictEqual(w.body.error.code, 'DUPLICATE_ENTRY');
  });

  await test('an unknown record_type is refused', async () => {
    const w = await call('write', 'dnt_credentials', { id: 'DCRED-X', provider_id: 'PV-1', record_type: 'malpractice' });
    assert.strictEqual(w.code, 400);
  });

  await test('records read back with entry_id, provider_id and the payload merged', async () => {
    const r = await call('read', 'dnt_credentials', {});
    assert.strictEqual(r.code, 200);
    assert.strictEqual(r.body.data.length, 1);
    assert.strictEqual(r.body.data[0].entry_id, 'DCRED-1');
    assert.strictEqual(r.body.data[0].number, 'D-12345');
    assert.strictEqual(r.body.data[0].record_type, 'state_license');
  });

  console.log('\nEvaluate — the board, computed server-side from what was really stored:');

  await test('the stored licence shows as expiring at the 30-day boundary', async () => {
    const r = await call('evaluate', 'dnt_credentials', { today: '2026-08-24' });
    assert.strictEqual(r.code, 200);
    assert.strictEqual(r.body.board.counts.expiring, 1);
    assert.strictEqual(r.body.board.items[0].days, 30);
    assert.strictEqual(r.body.board.action_required, 1);
  });

  await test('one day later the same record is one day closer, not reclassified', async () => {
    const r = await call('evaluate', 'dnt_credentials', { today: '2026-08-25' });
    assert.strictEqual(r.body.board.items[0].days, 29);
    assert.strictEqual(r.body.board.items[0].status, 'expiring');
  });

  await test('a superseding record replaces the earlier one on the board', async () => {
    await call('write', 'dnt_credentials', {
      id: 'DCRED-2', provider_id: 'PV-1', record_type: 'state_license',
      state: 'OH', number: 'D-12345', expires_on: '2028-09-23'
    });
    const r = await call('evaluate', 'dnt_credentials', { today: '2026-08-24' });
    assert.strictEqual(r.body.board.counts.expiring, 0);
    assert.strictEqual(r.body.board.counts.ok, 1);
    // Both rows are still on disk -- superseded, not deleted.
    assert.strictEqual(store.creds.length, 2);
  });

  await test('a DEA record uses the 60-day window and flags an unattested MATE', async () => {
    await call('write', 'dnt_credentials', {
      id: 'DCRED-3', provider_id: 'PV-1', record_type: 'dea_registration',
      number: 'BX1234567', expires_on: '2026-10-23', mate_attested: false
    });
    const r = await call('evaluate', 'dnt_credentials', { today: '2026-08-24' });
    const dea = r.body.board.items.filter((i) => i.record_type === 'dea_registration')[0];
    assert.strictEqual(dea.days, 60);
    assert.strictEqual(dea.status, 'expiring');
    assert.strictEqual(dea.warn_days, 60);
    assert.strictEqual(r.body.board.mate_outstanding, 1);
  });

  await test('a CE cycle takes its hours from the stored rule and names it', async () => {
    await call('write', 'dnt_credentials', {
      id: 'DCRED-4', provider_id: 'PV-1', record_type: 'ce_cycle',
      state: 'OH', role: 'dentist', cycle_start: '2025-01-01', cycle_end: '2026-12-31', hours_logged: 5
    });
    const r = await call('evaluate', 'dnt_credentials', { today: '2026-08-24' });
    const ce = r.body.board.items.filter((i) => i.record_type === 'ce_cycle')[0];
    assert.strictEqual(ce.hours_required, 30);
    assert.strictEqual(ce.hours_required_from, 'rule:OH-CE-DENTIST-BIENNIAL');
    assert.strictEqual(ce.status, 'behind');
  });

  await test('evaluate writes NOTHING — proven from the requests it issued', async () => {
    await call('evaluate', 'dnt_credentials', { today: '2026-08-24' });
    const writes = requests.filter((q) => q.method === 'POST' && q.url.indexOf('license_keys') === -1);
    assert.deepStrictEqual(writes, [], 'evaluate issued a write');
  });

  console.log('\nHonest failure when the migration has not been run:');

  await test('read reports provisioned:false rather than an error', async () => {
    tablesExist = false;
    const r = await call('read', 'dnt_credentials', {});
    assert.strictEqual(r.code, 200);
    assert.strictEqual(r.body.provisioned, false);
    assert.deepStrictEqual(r.body.data, []);
  });

  await test('write says exactly which SQL file to run', async () => {
    const w = await call('write', 'dnt_credentials', { id: 'DCRED-9', provider_id: 'PV-1', record_type: 'state_license', expires_on: '2027-01-01' });
    assert.strictEqual(w.code, 503);
    assert.strictEqual(w.body.error.code, 'NOT_PROVISIONED');
    assert.ok(w.body.error.message.indexOf('sairndental_credentials_schema.sql') !== -1);
  });

  await test('evaluate degrades to provisioned:false, never a fake empty board', async () => {
    const r = await call('evaluate', 'dnt_credentials', { today: '2026-08-24' });
    assert.strictEqual(r.code, 200);
    assert.strictEqual(r.body.provisioned, false);
    assert.strictEqual(r.body.board, null);
    tablesExist = true;
  });

  global.fetch = realFetch;
  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  if (failed > 0) process.exit(1);
})();
