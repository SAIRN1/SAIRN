// api/_lib/roofing-billing.test.js
// Isolation suite for Phase 4b -- estimate -> proposal -> invoice.
// Every figure here was worked out by hand.

'use strict';
const test = require('node:test');
const assert = require('node:assert');
const b = require('./roofing-billing.js');

const LINES = [
  { description: 'Architectural shingles', quantity: 44, unit: 'SQ', unit_price: 325 },   // 14300
  { description: 'Ridge cap', quantity: 120, unit: 'LF', unit_price: 8.5 },               // 1020
  { description: 'Drip edge', quantity: 210, unit: 'LF', unit_price: 3.25 }               // 682.5
];



test('line amounts are recomputed, and a client-supplied amount is ignored', () => {
  const out = b.normalizeLineItems([{ description: 'x', quantity: 2, unit_price: 10, amount: 999999 }]);
  assert.strictEqual(out[0].amount, 20);
});

test('the subtotal is the sum of the recomputed lines', () => {
  // 14300 + 1020 + 682.50 = 16002.50
  const t = b.computeTotals(LINES, null, null);
  assert.strictEqual(t.subtotal, 16002.5);
  assert.strictEqual(t.tax, 0);
  assert.strictEqual(t.total, 16002.5);
  assert.strictEqual(t.tax_basis, 'none');
});

test('a tax RATE is a percent and is applied to the subtotal', () => {
  // 16002.50 * 7.5% = 1200.1875 -> 1200.19
  const t = b.computeTotals(LINES, 7.5, null);
  assert.strictEqual(t.tax, 1200.19);
  assert.strictEqual(t.total, 17202.69);
  assert.strictEqual(t.tax_basis, 'rate');
  assert.strictEqual(t.tax_rate, 7.5);
});

test('an explicit tax AMOUNT wins over a rate, and the disagreement is reported', () => {
  const t = b.computeTotals(LINES, 7.5, 500);
  assert.strictEqual(t.tax, 500);
  assert.strictEqual(t.tax_basis, 'amount');
  assert.ok(t.problems.some((p) => /both a tax rate and a tax amount/.test(p)));
});

test('no tax is given at all -> zero, and NOT a guessed rate', () => {
  const t = b.computeTotals(LINES, undefined, undefined);
  assert.strictEqual(t.tax, 0);
  assert.strictEqual(t.tax_rate, null);
});

test('a missing quantity or price is zero, not NaN', () => {
  const t = b.computeTotals([{ description: 'junk' }], null, null);
  assert.strictEqual(t.subtotal, 0);
  assert.strictEqual(t.line_items[0].amount, 0);
});

test('an ISSUED proposal must carry its own line items -- it snapshots the price', () => {
  const p = b.validateProposal({ id: 'P1', job_id: 'J1', event_type: 'issued', issued_on: '2026-08-25' });
  assert.ok(p.some((x) => /snapshots the price/.test(x)));
});

test('a decision must name the proposal it responds to, and carry a date', () => {
  const p = b.validateProposal({ id: 'P2', job_id: 'J1', event_type: 'accepted' });
  assert.ok(p.some((x) => /must name the issued proposal_id/.test(x)));
  assert.ok(p.some((x) => /decided_on/.test(x)));
});

test('acceptance by signature requires a signature; other methods do not', () => {
  const withSig = b.validateProposal({
    id: 'P2', job_id: 'J1', event_type: 'accepted', supersedes: 'P1',
    decided_on: '2026-08-26', acceptance_method: 'signature', accepted_by: 'Dana'
  });
  assert.ok(withSig.some((x) => /no signature was captured/.test(x)));
  const byEmail = b.validateProposal({
    id: 'P2', job_id: 'J1', event_type: 'accepted', supersedes: 'P1',
    decided_on: '2026-08-26', acceptance_method: 'email', accepted_by: 'Dana'
  });
  assert.deepStrictEqual(byEmail, []);
});

test('an acceptance always records WHO accepted', () => {
  const p = b.validateProposal({
    id: 'P2', job_id: 'J1', event_type: 'accepted', supersedes: 'P1',
    decided_on: '2026-08-26', acceptance_method: 'phone'
  });
  assert.ok(p.some((x) => /accepted_by is required/.test(x)));
});

test('proposalState: no proposals is its own answer', () => {
  const s = b.proposalState([]);
  assert.strictEqual(s.status, 'none');
  assert.strictEqual(s.issued_count, 0);
});

test('proposalState: an issued proposal with no decision is awaiting_decision', () => {
  const s = b.proposalState([{ proposal_id: 'P1', event_type: 'issued', issued_on: '2026-08-25', line_items: LINES }]);
  assert.strictEqual(s.status, 'awaiting_decision');
  assert.strictEqual(s.totals.total, 16002.5);
});

test('proposalState: a decision on the LATEST proposal decides it', () => {
  const s = b.proposalState([
    { proposal_id: 'P1', event_type: 'issued', issued_on: '2026-08-25', line_items: LINES },
    { proposal_id: 'P2', event_type: 'accepted', supersedes: 'P1', decided_on: '2026-08-26' }
  ]);
  assert.strictEqual(s.status, 'accepted');
  assert.strictEqual(s.decision.proposal_id, 'P2');
});

test('proposalState: a DECLINE on a superseded proposal does not stick to the re-quote', () => {
  // Re-quoting after a decline is ordinary. The old decline must not decide
  // the new price.
  const s = b.proposalState([
    { proposal_id: 'P1', event_type: 'issued', issued_on: '2026-08-25', line_items: LINES },
    { proposal_id: 'PD', event_type: 'declined', supersedes: 'P1', decided_on: '2026-08-26' },
    { proposal_id: 'P3', event_type: 'issued', issued_on: '2026-08-27', line_items: LINES }
  ]);
  assert.strictEqual(s.latest.proposal_id, 'P3');
  assert.strictEqual(s.status, 'awaiting_decision');
  assert.strictEqual(s.decision, null);
  assert.strictEqual(s.superseded_count, 1);
});

test('proposalState: the snapshot is what is priced, not any live estimate', () => {
  // The second proposal carries DIFFERENT lines. The state must price the
  // snapshot it was issued with.
  const cheaper = [{ description: 'Shingles', quantity: 44, unit: 'SQ', unit_price: 300 }];
  const s = b.proposalState([
    { proposal_id: 'P1', event_type: 'issued', issued_on: '2026-08-25', line_items: LINES },
    { proposal_id: 'P2', event_type: 'issued', issued_on: '2026-08-27', line_items: cheaper }
  ]);
  assert.strictEqual(s.totals.total, 13200);
});

test('an invoice needs an issue_date once it is issued', () => {
  const p = b.validateInvoice({ id: 'I1', job_id: 'J1', status: 'issued' });
  assert.ok(p.some((x) => /issued invoice needs an issue_date/.test(x)));
});

test('a draft invoice does not need an issue date', () => {
  assert.deepStrictEqual(b.validateInvoice({ id: 'I1', job_id: 'J1', status: 'draft' }), []);
});

test('summarizeInvoice: balance is total minus payments, and it is DERIVED', () => {
  const inv = {
    line_items: LINES, tax_rate: null, tax: null,
    payments: [{ payment_id: 'PAY1', amount: 10000, received_on: '2026-09-01' }]
  };
  const s = b.summarizeInvoice(inv);
  assert.strictEqual(s.total, 16002.5);
  assert.strictEqual(s.paid, 10000);
  assert.strictEqual(s.balance, 6002.5);
  assert.strictEqual(s.settlement, 'outstanding');
});

test('summarizeInvoice: a fully paid invoice settles exactly', () => {
  const s = b.summarizeInvoice({ line_items: LINES, payments: [{ amount: 16002.5 }] });
  assert.strictEqual(s.balance, 0);
  assert.strictEqual(s.settlement, 'settled');
});

test('summarizeInvoice: OVERPAID is a real state, not a hidden negative', () => {
  const s = b.summarizeInvoice({ line_items: LINES, payments: [{ amount: 20000 }] });
  assert.strictEqual(s.settlement, 'overpaid');
  assert.ok(s.balance < 0);
});

test('summarizeInvoice: a reversal reduces the paid total', () => {
  const s = b.summarizeInvoice({
    line_items: LINES,
    payments: [{ payment_id: 'PAY1', amount: 10000 }, { payment_id: 'PAY2', amount: -10000, reverses: 'PAY1' }]
  });
  assert.strictEqual(s.paid, 0);
  assert.strictEqual(s.payment_count, 2); // both rows survive
});

test('a negative payment must name what it reverses', () => {
  const p = b.validatePayment({ payment_id: 'PAY2', amount: -500, received_on: '2026-09-02' });
  assert.ok(p.some((x) => /must name the payment_id it reverses/.test(x)));
});

test('a zero payment is refused', () => {
  assert.ok(b.validatePayment({ payment_id: 'P', amount: 0, received_on: '2026-09-02' }).length);
});

test('reconcile: no claim linked is not an error', () => {
  const r = b.reconcileAgainstClaim({ line_items: LINES }, null);
  assert.strictEqual(r.linked, false);
});

test('reconcile: invoicing MORE than the claim RCV points at a supplement', () => {
  const r = b.reconcileAgainstClaim({ line_items: LINES, issue_date: '2026-09-01' }, { claim_id: 'C1', rcv: 15000 });
  assert.strictEqual(r.variance, 1002.5);
  assert.ok(r.notes.some((n) => /MORE than the claim's RCV/.test(n)));
});

test('reconcile: invoicing LESS warns that something approved may be missing', () => {
  const r = b.reconcileAgainstClaim({ line_items: LINES }, { claim_id: 'C1', rcv: 20000 });
  assert.ok(r.variance < 0);
  assert.ok(r.notes.some((n) => /LESS than the claim's RCV/.test(n)));
});

test('reconcile: a claim with NO RCV cannot be compared, and says so rather than treating it as zero', () => {
  const r = b.reconcileAgainstClaim({ line_items: LINES }, { claim_id: 'C1' });
  assert.strictEqual(r.variance, null);
  assert.strictEqual(r.claim_rcv, null);
  assert.ok(r.notes.some((n) => /no RCV recorded/.test(n)));
});

test('reconcile: the deductible is flagged as not waivable', () => {
  const r = b.reconcileAgainstClaim({ line_items: LINES }, { claim_id: 'C1', rcv: 16002.5, deductible: 2500 });
  assert.ok(r.notes.some((n) => /not waivable/.test(n)));
});

test('reconcile: the date milestone is compared, not assumed', () => {
  const same = b.reconcileAgainstClaim({ line_items: LINES, issue_date: '2026-09-01' }, { claim_id: 'C1', final_invoice_submitted: '2026-09-01' });
  assert.strictEqual(same.milestone, 'matches');
  const diff = b.reconcileAgainstClaim({ line_items: LINES, issue_date: '2026-09-01' }, { claim_id: 'C1', final_invoice_submitted: '2026-09-05' });
  assert.strictEqual(diff.milestone, 'differs');
  const invOnly = b.reconcileAgainstClaim({ line_items: LINES, issue_date: '2026-09-01' }, { claim_id: 'C1' });
  assert.strictEqual(invOnly.milestone, 'invoice_only');
  const neither = b.reconcileAgainstClaim({ line_items: LINES }, { claim_id: 'C1' });
  assert.strictEqual(neither.milestone, 'not_submitted');
});

test('reconcile: the two-records disclosure rides on the result', () => {
  const r = b.reconcileAgainstClaim({ line_items: LINES }, { claim_id: 'C1', rcv: 100 });
  assert.match(r.disclosure, /information, not a correction/);
});

test('the vocabularies are closed', () => {
  assert.deepStrictEqual(b.PROPOSAL_EVENTS, ['issued', 'accepted', 'declined', 'withdrawn']);
  assert.deepStrictEqual(b.INVOICE_STATUSES, ['draft', 'issued', 'paid', 'void']);
  assert.ok(b.ACCEPTANCE_METHODS.indexOf('signature') !== -1);
});
