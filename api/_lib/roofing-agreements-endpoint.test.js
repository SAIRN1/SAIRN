// api/_lib/roofing-agreements-endpoint.test.js
// Round-trip tests for the rf_claim_agreements and rf_contingency_rules
// branches of api/sd-data.js, through the REAL handler with a stubbed Supabase.
// Run: node api/_lib/roofing-agreements-endpoint.test.js
//
// What this proves that the pure engine cannot: the agreement store is genuinely
// append-only (no UPDATE path exists), recorded_by is server-stamped, a
// rescission cannot name an agreement on a claim the caller cannot see, the
// governing rule is chosen from the SIGNED state rather than from the caller,
// and agreement_status writes nothing.

const assert = require('assert');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://stub.test';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'k';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || 'stub-secret';

const auth = require('./auth');
let requests = [];
let store = { claims: [], agreements: [], rules: [] };

function jsonRes(status, body) { return Promise.resolve({ status, ok: status >= 200 && status < 300, json: () => Promise.resolve(body), text: () => Promise.resolve(JSON.stringify(body)) }); }
function eqParam(u, k) { const m = u.match(new RegExp(k + '=eq\\.([^&]+)')); return m ? decodeURIComponent(m[1]) : null; }

global.fetch = function (url, opts) {
  opts = opts || {};
  const u = String(url); const method = opts.method || 'GET';
  requests.push({ url: u, method, body: opts.body ? JSON.parse(opts.body) : null });
  if (u.indexOf('license_keys') !== -1) return jsonRes(200, [{ key: 'RF', status: 'active', app_id: 'sairnroofing', trial_ends_at: null, stripe_subscription_id: 's' }]);
  if (u.indexOf('rf_contingency_rules') !== -1) {
    if (method === 'POST') { const row = JSON.parse(opts.body); store.rules = store.rules.filter((r) => r.rule_id !== row.rule_id).concat([row]); return jsonRes(200, [row]); }
    const st = eqParam(u, 'state'); const status = eqParam(u, 'status');
    return jsonRes(200, store.rules.filter((r) => (!st || r.state === st) && (!status || r.status === status)));
  }
  if (u.indexOf('rf_claim_agreements') !== -1) {
    if (method === 'POST') {
      const row = JSON.parse(opts.body);
      if (store.agreements.some((a) => a.agreement_id === row.agreement_id)) return jsonRes(409, { message: 'duplicate key value violates unique constraint' });
      store.agreements.push(row); return jsonRes(200, [row]);
    }
    const cid = eqParam(u, 'claim_id'); const aid = eqParam(u, 'agreement_id'); const ev = eqParam(u, 'event_type');
    return jsonRes(200, store.agreements.filter((a) => (!cid || a.claim_id === cid) && (!aid || a.agreement_id === aid) && (!ev || a.event_type === ev)));
  }
  if (u.indexOf('rf_claims') !== -1) {
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

store.claims.push({ claim_id: 'C1', assigned_employee_id: 'FM', data: {} });
store.claims.push({ claim_id: 'C-CO', assigned_employee_id: 'FM', data: { insurer_denial_at: '2026-09-01T09:00:00.000Z' } });
store.claims.push({ claim_id: 'C-STAMP', assigned_employee_id: 'FM', data: {} });

const OH_RULE = {
  id: 'RFCON-OH-HSSA-CANCEL', state: 'OH', trigger_event: 'execution', count: 3,
  unit: 'business_days', business_day_basis: 'oh_hssa', status: 'active',
  data: {
    authority: 'Ohio Rev. Code 1345.22', notice_required: true, form_required: true,
    indefinite_if_noncompliant: true, applies_only_when_solicited: true
  }
};
const CO_RULE = {
  id: 'RFCON-CO-6-22-104', state: 'CO', trigger_event: 'insurer_denial', count: 72,
  unit: 'hours', status: 'active',
  data: { authority: 'C.R.S. 6-22-104', notice_required: false, form_required: false, indefinite_if_noncompliant: false }
};
function exec(over) {
  return Object.assign({
    id: 'RFAGR-1', claim_id: 'C1', event_type: 'executed', signer_name: 'A Homeowner',
    signature_data: 'data:image/png;base64,AAAA', signing_venue: 'buyer_residence',
    executed_at: '2026-08-03T15:00:00.000Z', state: 'OH',
    notice_given: true, cancellation_form_given: true
  }, over || {});
}

(async () => {
  console.log('\nrf_contingency_rules -- management-only, citation-enforced:');
  await test('management can write a rule', async () => {
    const r = await call('write', 'rf_contingency_rules', OH_RULE, OWNER);
    assert.strictEqual(r.code, 200);
  });
  await test('a foreman CANNOT write a rule -> 403', async () => {
    const r = await call('write', 'rf_contingency_rules', CO_RULE, FM);
    assert.strictEqual(r.code, 403);
  });
  await test('a rule with NO authority citation is refused at the endpoint -> 400', async () => {
    const bad = Object.assign({}, CO_RULE, { data: {} });
    const r = await call('write', 'rf_contingency_rules', bad, OWNER);
    assert.strictEqual(r.code, 400);
    assert.match(r.body.error.message, /authority citation/);
  });
  await test('verified_by is server-stamped from the session, not the payload', async () => {
    await call('write', 'rf_contingency_rules', Object.assign({}, CO_RULE, { verified_by: 'SOMEONE-ELSE' }), OWNER);
    const posted = requests.filter((q) => q.method === 'POST' && q.url.indexOf('rf_contingency_rules') !== -1).pop();
    assert.strictEqual(posted.body.verified_by, 'OWN');
  });
  await test('any signed-in role can READ the rules', async () => {
    const r = await call('read', 'rf_contingency_rules', {}, FM);
    assert.strictEqual(r.code, 200);
    assert.ok(r.body.data.length >= 1);
  });

  console.log('\nrf_claim_agreements -- append-only, gated, server-stamped:');
  await test('the assigned foreman can record an executed agreement', async () => {
    const r = await call('write', 'rf_claim_agreements', exec(), FM);
    assert.strictEqual(r.code, 200);
  });
  await test('recorded_by is server-stamped, and a caller-supplied one is discarded', async () => {
    // Asserted inside the same test as the write -- `requests` is cleared per
    // test, so checking it from the next test read an empty list and passed
    // vacuously until it did not.
    const r = await call('write', 'rf_claim_agreements', exec({ id: 'RFAGR-STAMP', claim_id: 'C-STAMP', recorded_by: 'SOMEONE-ELSE' }), FM);
    assert.strictEqual(r.code, 200);
    const posted = requests.filter((q) => q.method === 'POST' && q.url.indexOf('rf_claim_agreements') !== -1).pop();
    assert.strictEqual(posted.body.recorded_by, 'FM');
    assert.strictEqual(r.body.data.recorded_by, 'FM');
  });
  await test('a DIFFERENT foreman cannot record on that claim -> 403', async () => {
    const r = await call('write', 'rf_claim_agreements', exec({ id: 'RFAGR-X' }), FM2);
    assert.strictEqual(r.code, 403);
  });
  await test('no session -> 401', async () => {
    const r = await call('write', 'rf_claim_agreements', exec({ id: 'RFAGR-Y' }), null);
    assert.strictEqual(r.code, 401);
  });
  await test('an executed row with no signature is refused -> 400', async () => {
    const r = await call('write', 'rf_claim_agreements', exec({ id: 'RFAGR-Z', signature_data: '' }), FM);
    assert.strictEqual(r.code, 400);
    assert.match(r.body.error.message, /signature_data/);
  });
  await test('APPEND-ONLY: re-using an agreement id is refused -> 409, never an overwrite', async () => {
    const r = await call('write', 'rf_claim_agreements', exec({ signer_name: 'Someone Else' }), FM);
    assert.strictEqual(r.code, 409);
    assert.strictEqual(r.body.error.code, 'ALREADY_RECORDED');
    const stored = store.agreements.filter((a) => a.agreement_id === 'RFAGR-1');
    assert.strictEqual(stored.length, 1);
    assert.strictEqual(stored[0].data.signer_name, 'A Homeowner'); // original survived
  });
  await test('there is NO update verb on rf_claim_agreements at all', async () => {
    const r = await call('update', 'rf_claim_agreements', exec(), FM);
    assert.notStrictEqual(r.code, 200);
  });

  console.log('\nRescission is a second row, and it must name a real target:');
  await test('a rescission naming a NON-EXISTENT agreement is refused -> 400', async () => {
    const r = await call('write', 'rf_claim_agreements', { id: 'RFAGR-R0', claim_id: 'C1', event_type: 'rescinded', supersedes: 'RFAGR-NOPE', rescinded_at: '2026-08-05T00:00:00Z' }, FM);
    assert.strictEqual(r.code, 400);
    assert.strictEqual(r.body.error.code, 'NO_SUCH_AGREEMENT');
  });
  await test('a rescission with no supersedes at all is refused -> 400', async () => {
    const r = await call('write', 'rf_claim_agreements', { id: 'RFAGR-R1', claim_id: 'C1', event_type: 'rescinded', rescinded_at: '2026-08-05T00:00:00Z' }, FM);
    assert.strictEqual(r.code, 400);
    assert.match(r.body.error.message, /supersedes/);
  });

  console.log('\nagreement_status -- compute-only, rule chosen from the SIGNED state:');
  await test('the Ohio rule is applied and the window is open', async () => {
    const r = await call('agreement_status', 'rf_claim_agreements', { claim_id: 'C1' }, FM);
    assert.strictEqual(r.code, 200);
    assert.strictEqual(r.body.state, 'OH');
    assert.strictEqual(r.body.agreement_status.rule_applied, 'RFCON-OH-HSSA-CANCEL');
    assert.strictEqual(r.body.agreement_status.deadline_at, '2026-08-06T23:59:59.999Z');
  });
  await test('the caller CANNOT choose the governing state', async () => {
    const r = await call('agreement_status', 'rf_claim_agreements', { claim_id: 'C1', state: 'CO' }, FM);
    assert.strictEqual(r.body.state, 'OH'); // still the signed state
    assert.strictEqual(r.body.agreement_status.rule_applied, 'RFCON-OH-HSSA-CANCEL');
  });
  await test('agreement_status WRITES NOTHING', async () => {
    requests = [];
    await call('agreement_status', 'rf_claim_agreements', { claim_id: 'C1' }, FM);
    assert.strictEqual(requests.filter((q) => q.method === 'POST' && q.url.indexOf('license_keys') === -1).length, 0);
  });
  await test('a different foreman gets 403 and no status body', async () => {
    const r = await call('agreement_status', 'rf_claim_agreements', { claim_id: 'C1' }, FM2);
    assert.strictEqual(r.code, 403);
    assert.strictEqual(r.body.agreement_status, undefined);
  });
  await test('the Colorado trigger reads the denial date from the CLAIM, not the caller', async () => {
    await call('write', 'rf_claim_agreements', exec({ id: 'RFAGR-CO', claim_id: 'C-CO', state: 'CO' }), FM);
    const r = await call('agreement_status', 'rf_claim_agreements', { claim_id: 'C-CO', denial_at: '2020-01-01T00:00:00Z' }, FM);
    assert.strictEqual(r.body.agreement_status.trigger, 'insurer_denial');
    assert.strictEqual(r.body.agreement_status.trigger_at, '2026-09-01T09:00:00.000Z');
    assert.strictEqual(r.body.agreement_status.deadline_at, '2026-09-04T09:00:00.000Z');
  });
  await test('a state with no rule on file returns no_rule, not a fabricated date', async () => {
    store.claims.push({ claim_id: 'C-WY', assigned_employee_id: 'FM', data: {} });
    await call('write', 'rf_claim_agreements', exec({ id: 'RFAGR-WY', claim_id: 'C-WY', state: 'WY' }), FM);
    const r = await call('agreement_status', 'rf_claim_agreements', { claim_id: 'C-WY' }, FM);
    assert.strictEqual(r.body.agreement_status.status, 'no_rule');
    assert.strictEqual(r.body.agreement_status.deadline_at, null);
  });
  await test('an unsigned claim reports unsigned rather than erroring', async () => {
    store.claims.push({ claim_id: 'C-NEW', assigned_employee_id: 'FM', data: {} });
    const r = await call('agreement_status', 'rf_claim_agreements', { claim_id: 'C-NEW' }, FM);
    assert.strictEqual(r.code, 200);
    assert.strictEqual(r.body.agreement_status.status, 'unsigned');
  });
  await test('a recorded rescission flips the status and survives a re-read', async () => {
    await call('write', 'rf_claim_agreements', { id: 'RFAGR-R2', claim_id: 'C1', event_type: 'rescinded', supersedes: 'RFAGR-1', rescinded_at: '2026-08-05T10:00:00.000Z', rescission_reason: 'homeowner changed their mind' }, FM);
    const r = await call('agreement_status', 'rf_claim_agreements', { claim_id: 'C1' }, FM);
    assert.strictEqual(r.body.agreement_status.status, 'rescinded');
    assert.ok(r.body.agreement_status.rescission);
    const chain = await call('read', 'rf_claim_agreements', { claim_id: 'C1' }, FM);
    assert.strictEqual(chain.body.data.length, 2); // both rows survive -- nothing was overwritten
  });
  await test('the signature blob is NOT shipped on an ordinary read, but is flagged present', async () => {
    const r = await call('read', 'rf_claim_agreements', { claim_id: 'C1' }, FM);
    const ex = r.body.data.filter((a) => a.event_type === 'executed')[0];
    assert.strictEqual(ex.signature_data, undefined);
    assert.strictEqual(ex.has_signature, true);
  });
  await test('include_signature:true returns the real signature', async () => {
    const r = await call('read', 'rf_claim_agreements', { claim_id: 'C1', include_signature: true }, FM);
    const ex = r.body.data.filter((a) => a.event_type === 'executed')[0];
    assert.strictEqual(ex.signature_data, 'data:image/png;base64,AAAA');
  });
  await test('missing claim_id -> 400; unknown claim -> 404', async () => {
    assert.strictEqual((await call('agreement_status', 'rf_claim_agreements', {}, FM)).code, 400);
    assert.strictEqual((await call('agreement_status', 'rf_claim_agreements', { claim_id: 'NOPE' }, FM)).code, 404);
  });

  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  if (failed) process.exit(1);
})();
