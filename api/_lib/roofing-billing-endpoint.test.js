// api/_lib/roofing-billing-endpoint.test.js
// Round-trip tests for the Phase 4b rf_proposals / rf_invoices branches of
// api/sd-data.js, through the REAL handler with a stubbed Supabase.
// Run: node api/_lib/roofing-billing-endpoint.test.js
//
// What this proves that the pure engine cannot: a proposal is append-only and
// stores the price it was issued with, invoice numbers come from the allocator
// and 'issue' is IDEMPOTENT (re-issuing must never burn a second number), a
// payment is appended by the SERVER one entry at a time, an issued invoice
// cannot be edited, and the claim comparison reads the claim server-side.

const assert = require('assert');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://stub.test';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'k';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || 'stub-secret';

const auth = require('./auth');
let requests = [];
let store = { jobs: [], claims: [], proposals: [], invoices: [] };
let counter = 1;

function jsonRes(status, body) { return Promise.resolve({ status, ok: status >= 200 && status < 300, json: () => Promise.resolve(body), text: () => Promise.resolve(JSON.stringify(body)) }); }
function eqParam(u, k) { const m = u.match(new RegExp(k + '=eq\\.([^&]+)')); return m ? decodeURIComponent(m[1]) : null; }

global.fetch = function (url, opts) {
  opts = opts || {};
  const u = String(url); const method = opts.method || 'GET';
  requests.push({ url: u, method, body: opts.body ? JSON.parse(opts.body) : null });
  if (u.indexOf('license_keys') !== -1) return jsonRes(200, [{ key: 'RF', status: 'active', app_id: 'sairnroofing', trial_ends_at: null, stripe_subscription_id: 's' }]);
  if (u.indexOf('rpc/rf_allocate_invoice_number') !== -1) {
    const seq = counter++;
    return jsonRes(200, [{ invoice_number: 'INV-' + String(seq).padStart(5, '0'), invoice_seq: seq, prefix: 'INV' }]);
  }
  if (u.indexOf('rf_proposals') !== -1) {
    if (method === 'POST') {
      const row = JSON.parse(opts.body);
      if (store.proposals.some((p) => p.proposal_id === row.proposal_id)) return jsonRes(409, { message: 'duplicate key value violates unique constraint' });
      store.proposals.push(row); return jsonRes(200, [row]);
    }
    const jid = eqParam(u, 'job_id'), pid = eqParam(u, 'proposal_id'), ev = eqParam(u, 'event_type');
    return jsonRes(200, store.proposals.filter((p) => (!jid || p.job_id === jid) && (!pid || p.proposal_id === pid) && (!ev || p.event_type === ev)));
  }
  if (u.indexOf('rf_invoices') !== -1) {
    if (method === 'POST') { const row = JSON.parse(opts.body); store.invoices = store.invoices.filter((i) => i.invoice_id !== row.invoice_id).concat([row]); return jsonRes(200, [row]); }
    if (method === 'PATCH') {
      const iid = eqParam(u, 'invoice_id'); const patch = JSON.parse(opts.body);
      store.invoices = store.invoices.map((i) => (i.invoice_id === iid ? Object.assign({}, i, patch) : i));
      return jsonRes(200, store.invoices.filter((i) => i.invoice_id === iid));
    }
    const iid = eqParam(u, 'invoice_id'), jid = eqParam(u, 'job_id');
    return jsonRes(200, store.invoices.filter((i) => (!iid || i.invoice_id === iid) && (!jid || i.job_id === jid)));
  }
  if (u.indexOf('rf_claims') !== -1) {
    const cid = eqParam(u, 'claim_id'); return jsonRes(200, store.claims.filter((c) => !cid || c.claim_id === cid));
  }
  if (u.indexOf('rf_jobs') !== -1) {
    const jid = eqParam(u, 'job_id'); return jsonRes(200, store.jobs.filter((j) => !jid || j.job_id === jid));
  }
  return jsonRes(404, { message: 'unexpected' });
};

const handler = require('../sd-data');
const licHash = require('crypto').createHash('sha256').update('RF').digest('hex');
function tok(emp, role) { return auth.signSessionToken({ license_hash: licHash, app: 'sairnroofing', employee_id: emp, role }); }
const OWNER = tok('OWN', 'owner');
const EST = tok('EST', 'estimator');
const FM = tok('FM', 'foreman');
const OTHER = tok('OTH', 'foreman');

let passed = 0, failed = 0;
async function test(name, fn) { requests = []; try { await fn(); passed++; console.log('  ok - ' + name); } catch (e) { failed++; console.error('  FAIL - ' + name); console.error('    ' + e.message); } }
async function call(action, resource, payload, token) {
  const out = { code: null, body: null };
  const res = { status(c) { out.code = c; return res; }, json(b) { out.body = b; return res; } };
  const h = { authorization: 'Bearer RF' }; if (token) h['x-sd-auth'] = token;
  await handler({ method: 'POST', headers: h, body: { action, resource, payload } }, res);
  return out;
}
function inv(id) { return store.invoices.filter((i) => i.invoice_id === id)[0]; }

store.jobs.push({ job_id: 'J1', assigned_employee_id: 'FM', location_id: 'LOC-CBUS' });
store.claims.push({ claim_id: 'C1', data: { rcv: 15000, deductible: 2500, final_invoice_submitted: '2026-09-05' } });

const LINES = [
  { description: 'Shingles', quantity: 44, unit: 'SQ', unit_price: 325 },  // 14300
  { description: 'Ridge cap', quantity: 120, unit: 'LF', unit_price: 8.5 } // 1020
]; // subtotal 15320

(async () => {
  console.log('\nProposals -- append-only, and the price is SNAPSHOT:');
  await test('an estimator can issue a proposal', async () => {
    const r = await call('write', 'rf_proposals', {
      id: 'P1', job_id: 'J1', event_type: 'issued', issued_on: '2026-08-25', line_items: LINES
    }, EST);
    assert.strictEqual(r.code, 200);
  });
  await test('the totals were recomputed server-side and STORED on the row', async () => {
    const row = store.proposals.filter((p) => p.proposal_id === 'P1')[0];
    assert.strictEqual(row.data.subtotal, 15320);
    assert.strictEqual(row.data.total, 15320);
    assert.strictEqual(row.data.line_items[0].amount, 14300);
  });
  await test('a client-supplied total is ignored, not trusted', async () => {
    await call('write', 'rf_proposals', {
      id: 'P-FAKE', job_id: 'J1', event_type: 'issued', issued_on: '2026-08-25',
      line_items: [{ description: 'x', quantity: 1, unit_price: 10, amount: 999999 }], total: 999999, subtotal: 999999
    }, EST);
    const row = store.proposals.filter((p) => p.proposal_id === 'P-FAKE')[0];
    assert.strictEqual(row.data.total, 10);
  });
  await test('an issued proposal with no line items is refused -> 400', async () => {
    const r = await call('write', 'rf_proposals', { id: 'P-X', job_id: 'J1', event_type: 'issued', issued_on: '2026-08-25' }, EST);
    assert.strictEqual(r.code, 400);
    assert.match(r.body.error.message, /snapshots the price/);
  });
  await test('a FOREMAN can READ proposals on their own job', async () => {
    const r = await call('read', 'rf_proposals', { job_id: 'J1' }, FM);
    assert.strictEqual(r.code, 200);
    assert.ok(r.body.state);
  });
  await test('...but cannot issue one -> 403', async () => {
    assert.strictEqual((await call('write', 'rf_proposals', { id: 'P-FM', job_id: 'J1', event_type: 'issued', issued_on: '2026-08-25', line_items: LINES }, FM)).code, 403);
  });
  await test('an UNRELATED foreman cannot read them at all -> 403', async () => {
    assert.strictEqual((await call('read', 'rf_proposals', { job_id: 'J1' }, OTHER)).code, 403);
  });
  await test('a decision naming a non-existent proposal -> 400', async () => {
    const r = await call('write', 'rf_proposals', { id: 'PD', job_id: 'J1', event_type: 'accepted', supersedes: 'NOPE', decided_on: '2026-08-26', acceptance_method: 'email', accepted_by: 'Dana' }, EST);
    assert.strictEqual(r.code, 400);
    assert.strictEqual(r.body.error.code, 'NO_SUCH_PROPOSAL');
  });
  await test('acceptance without a signature is allowed when the method is not signature', async () => {
    const r = await call('write', 'rf_proposals', { id: 'PA', job_id: 'J1', event_type: 'accepted', supersedes: 'P1', decided_on: '2026-08-26', acceptance_method: 'email', accepted_by: 'Dana Homeowner' }, EST);
    assert.strictEqual(r.code, 200);
  });
  await test('re-using a proposal id is refused -> 409 (append-only)', async () => {
    const r = await call('write', 'rf_proposals', { id: 'P1', job_id: 'J1', event_type: 'issued', issued_on: '2026-08-27', line_items: LINES }, EST);
    assert.strictEqual(r.code, 409);
  });
  await test('the signature is not shipped on an ordinary read', async () => {
    await call('write', 'rf_proposals', {
      id: 'P2', job_id: 'J1', event_type: 'issued', issued_on: '2026-08-28', line_items: LINES
    }, EST);
    await call('write', 'rf_proposals', {
      id: 'PA2', job_id: 'J1', event_type: 'accepted', supersedes: 'P2', decided_on: '2026-08-29',
      acceptance_method: 'signature', accepted_by: 'Dana', signature_data: 'data:image/png;base64,AAAA'
    }, EST);
    const r = await call('read', 'rf_proposals', { job_id: 'J1' }, EST);
    const acc = r.body.data.filter((p) => p.proposal_id === 'PA2')[0];
    assert.strictEqual(acc.signature_data, undefined);
    assert.strictEqual(acc.has_signature, true);
    const full = await call('read', 'rf_proposals', { job_id: 'J1', include_signature: true }, EST);
    assert.strictEqual(full.body.data.filter((p) => p.proposal_id === 'PA2')[0].signature_data, 'data:image/png;base64,AAAA');
  });

  console.log('\nInvoices -- management/broad-read only, no narrow tier at all:');
  await test('a foreman cannot read invoices even on their own job -> 403', async () => {
    const r = await call('read', 'rf_invoices', { job_id: 'J1' }, FM);
    assert.strictEqual(r.code, 403);
    assert.strictEqual(r.body.data, undefined);
  });
  await test('no session -> 401', async () => {
    assert.strictEqual((await call('read', 'rf_invoices', {}, null)).code, 401);
  });
  await test('a draft invoice saves with no number and no issue date', async () => {
    const r = await call('write', 'rf_invoices', { id: 'I1', job_id: 'J1', claim_id: 'C1', status: 'draft', line_items: LINES, bill_to: 'Dana Homeowner', terms: 'Net 30' }, OWNER);
    assert.strictEqual(r.code, 200);
    assert.strictEqual(inv('I1').invoice_number, null);
    assert.strictEqual(r.body.data.summary.total, 15320);
  });
  await test('the invoice inherits the JOB location, not one from the caller', async () => {
    await call('write', 'rf_invoices', { id: 'I1', job_id: 'J1', claim_id: 'C1', status: 'draft', line_items: LINES, location_id: 'LOC-ELSEWHERE' }, OWNER);
    assert.strictEqual(inv('I1').location_id, 'LOC-CBUS');
  });
  await test('a payment cannot be recorded against a DRAFT -> 400', async () => {
    const r = await call('add_payment', 'rf_invoices', { invoice_id: 'I1', payment: { payment_id: 'PAY1', amount: 100, received_on: '2026-09-01' } }, OWNER);
    assert.strictEqual(r.code, 400);
    assert.strictEqual(r.body.error.code, 'NOT_ISSUED');
  });

  console.log('\nIssuing -- the gapless number, allocated once:');
  await test('issue allocates the first number', async () => {
    const r = await call('issue', 'rf_invoices', { invoice_id: 'I1', issue_date: '2026-09-01' }, OWNER);
    assert.strictEqual(r.code, 200);
    assert.strictEqual(r.body.invoice_number, 'INV-00001');
    assert.strictEqual(inv('I1').status, 'issued');
  });
  await test('re-issuing is IDEMPOTENT and does NOT burn a second number', async () => {
    // Burning a number is the one failure nobody can fix afterwards: the
    // sequence has a hole and no record of why.
    const before = counter;
    const r = await call('issue', 'rf_invoices', { invoice_id: 'I1' }, OWNER);
    assert.strictEqual(r.code, 200);
    assert.strictEqual(r.body.already_issued, true);
    assert.strictEqual(r.body.invoice_number, 'INV-00001');
    assert.strictEqual(counter, before, 'the allocator must not have been called again');
  });
  await test('a second invoice gets the NEXT number, with no gap', async () => {
    await call('write', 'rf_invoices', { id: 'I2', job_id: 'J1', status: 'draft', line_items: LINES }, OWNER);
    const r = await call('issue', 'rf_invoices', { invoice_id: 'I2' }, OWNER);
    assert.strictEqual(r.body.invoice_number, 'INV-00002');
  });
  await test('issuing an unknown invoice -> 404', async () => {
    assert.strictEqual((await call('issue', 'rf_invoices', { invoice_id: 'NOPE' }, OWNER)).code, 404);
  });

  console.log('\nAn issued invoice is a document the customer holds:');
  await test('editing an issued invoice is refused -> 409 NOT_A_DRAFT', async () => {
    const r = await call('write', 'rf_invoices', { id: 'I1', job_id: 'J1', status: 'issued', issue_date: '2026-09-01', line_items: [{ description: 'cheaper', quantity: 1, unit_price: 1 }] }, OWNER);
    assert.strictEqual(r.code, 409);
    assert.strictEqual(r.body.error.code, 'NOT_A_DRAFT');
  });
  await test('the stored money survived the attempt', async () => {
    assert.strictEqual(inv('I1').data.total, 15320);
  });
  await test('voiding IS allowed', async () => {
    await call('write', 'rf_invoices', { id: 'I2', job_id: 'J1', status: 'void', issue_date: '2026-09-01', line_items: LINES }, OWNER);
    assert.strictEqual(inv('I2').status, 'void');
  });
  await test('a payment against a VOID invoice is refused', async () => {
    const r = await call('add_payment', 'rf_invoices', { invoice_id: 'I2', payment: { payment_id: 'PX', amount: 10, received_on: '2026-09-02' } }, OWNER);
    assert.strictEqual(r.code, 400);
    assert.strictEqual(r.body.error.code, 'VOID_INVOICE');
  });

  console.log('\nPayments -- the SERVER appends, one entry at a time:');
  await test('a payment is appended and the balance is derived', async () => {
    const r = await call('add_payment', 'rf_invoices', { invoice_id: 'I1', payment: { payment_id: 'PAY1', amount: 10000, received_on: '2026-09-05', method: 'insurance_check' } }, OWNER);
    assert.strictEqual(r.code, 200);
    assert.strictEqual(r.body.summary.paid, 10000);
    assert.strictEqual(r.body.summary.balance, 5320);
    assert.strictEqual(r.body.summary.settlement, 'outstanding');
  });
  await test('recorded_by is server-stamped on the entry', async () => {
    assert.strictEqual(inv('I1').payments[0].recorded_by, 'OWN');
  });
  await test('the client CANNOT send the whole payments array', async () => {
    // Only payload.payment is read; a payments array in the payload is ignored,
    // so a client cannot rewrite history by resending it.
    await call('add_payment', 'rf_invoices', {
      invoice_id: 'I1', payments: [], payment: { payment_id: 'PAY2', amount: 5320, received_on: '2026-09-10', method: 'check' }
    }, OWNER);
    assert.strictEqual(inv('I1').payments.length, 2);
  });
  await test('the invoice now settles exactly', async () => {
    const r = await call('read', 'rf_invoices', { job_id: 'J1' }, OWNER);
    const i1 = r.body.data.filter((x) => x.invoice_id === 'I1')[0];
    assert.strictEqual(i1.summary.balance, 0);
    assert.strictEqual(i1.summary.settlement, 'settled');
  });
  await test('a duplicate payment id is refused -> 409', async () => {
    const r = await call('add_payment', 'rf_invoices', { invoice_id: 'I1', payment: { payment_id: 'PAY1', amount: 1, received_on: '2026-09-11' } }, OWNER);
    assert.strictEqual(r.code, 409);
  });
  await test('a reversal naming a payment not on this invoice is refused', async () => {
    const r = await call('add_payment', 'rf_invoices', { invoice_id: 'I1', payment: { payment_id: 'PAYR', amount: -100, received_on: '2026-09-11', reverses: 'NOT-HERE' } }, OWNER);
    assert.strictEqual(r.code, 400);
    assert.strictEqual(r.body.error.code, 'NO_SUCH_PAYMENT');
  });
  await test('a valid reversal appends and both entries survive', async () => {
    const r = await call('add_payment', 'rf_invoices', { invoice_id: 'I1', payment: { payment_id: 'PAYR', amount: -5320, received_on: '2026-09-11', reverses: 'PAY2' } }, OWNER);
    assert.strictEqual(r.code, 200);
    assert.strictEqual(r.body.summary.paid, 10000);
    assert.strictEqual(inv('I1').payments.length, 3);
  });

  console.log('\nreconcile_claim -- information, and the claim is read server-side:');
  await test('the comparison uses the linked claim, not a caller-supplied one', async () => {
    const r = await call('reconcile_claim', 'rf_invoices', { invoice_id: 'I1', claim: { rcv: 999999 } }, OWNER);
    assert.strictEqual(r.code, 200);
    assert.strictEqual(r.body.reconciliation.claim_rcv, 15000);
    assert.strictEqual(r.body.reconciliation.variance, 320);
  });
  await test('the variance points at a supplement rather than reading as an error', async () => {
    const r = await call('reconcile_claim', 'rf_invoices', { invoice_id: 'I1' }, OWNER);
    assert.ok(r.body.reconciliation.notes.some((n) => /belongs in a supplement/.test(n)));
    assert.match(r.body.reconciliation.disclosure, /information, not a correction/);
  });
  await test('the date milestone difference is surfaced', async () => {
    const r = await call('reconcile_claim', 'rf_invoices', { invoice_id: 'I1' }, OWNER);
    assert.strictEqual(r.body.reconciliation.milestone, 'differs');
  });
  await test('reconcile_claim writes NOTHING', async () => {
    requests = [];
    await call('reconcile_claim', 'rf_invoices', { invoice_id: 'I1' }, OWNER);
    const writes = requests.filter((q) => q.method !== 'GET' && q.url.indexOf('license_keys') === -1);
    assert.strictEqual(writes.length, 0, JSON.stringify(writes.map((w) => w.url + ' ' + w.method)));
  });
  await test('an unlinked invoice reconciles honestly rather than erroring', async () => {
    const r = await call('reconcile_claim', 'rf_invoices', { invoice_id: 'I2' }, OWNER);
    assert.strictEqual(r.body.reconciliation.linked, false);
  });

  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  if (failed) process.exit(1);
})();
