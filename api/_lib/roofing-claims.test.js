// api/_lib/roofing-claims.test.js
// Plain node:assert tests. Run: node api/_lib/roofing-claims.test.js
//
// The money rule is the thing most worth testing exhaustively: the seven fields
// must stay separate, ACV must never be silently overwritten by rcv-depreciation,
// and a mismatch between them must SURFACE rather than be "corrected".

const assert = require('assert');
const c = require('./roofing-claims');

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log('  ok - ' + name); }
  catch (err) { failed++; console.error('  FAIL - ' + name); console.error('    ' + err.message); }
}

console.log('Money — the seven fields stay separate:');
test('all seven fields are named and distinct', () => {
  assert.strictEqual(c.MONEY_FIELDS.length, 7);
  assert.strictEqual(new Set(c.MONEY_FIELDS).size, 7);
  ['rcv', 'depreciation', 'acv', 'deductible', 'acv_check_received', 'final_invoice_submitted', 'recoverable_depreciation_released']
    .forEach((f) => assert.ok(c.MONEY_FIELDS.indexOf(f) !== -1, f + ' missing'));
});
test('normalize keeps each amount independent, never sums', () => {
  const n = c.normalizeMoney({ rcv: 20000, depreciation: 5000, acv: 15000, deductible: 1000 });
  assert.strictEqual(n.problems.length, 0);
  assert.strictEqual(n.money.rcv, 20000);
  assert.strictEqual(n.money.depreciation, 5000);
  assert.strictEqual(n.money.acv, 15000);
  assert.strictEqual(n.money.deductible, 1000);
  // No 'total' or 'amount' key invented.
  assert.ok(!('amount' in n.money) && !('total' in n.money));
});
test('ACV is stored AS ENTERED, never overwritten by rcv - depreciation', () => {
  // Carrier says ACV 14000, but rcv - dep = 15000. The entered value wins in
  // storage; the discrepancy is surfaced, not erased.
  const n = c.normalizeMoney({ rcv: 20000, depreciation: 6000, acv: 14000 });
  assert.strictEqual(n.money.acv, 14000);
  const s = c.summarizeMoney(n.money);
  assert.strictEqual(s.entered.acv, 14000);
  assert.strictEqual(s.derived.acv_implied, 14000); // 20000-6000
  assert.strictEqual(s.derived.acv_mismatch, false); // here they agree
});
test('a real mismatch is flagged, not fixed', () => {
  const n = c.normalizeMoney({ rcv: 20000, depreciation: 6000, acv: 13000 });
  const s = c.summarizeMoney(n.money);
  assert.strictEqual(s.entered.acv, 13000);       // untouched
  assert.strictEqual(s.derived.acv_implied, 14000);
  assert.strictEqual(s.derived.acv_mismatch, true);
});
test('depreciation_still_out reflects the release, the loss-of-release trap', () => {
  // Before the release: the whole depreciation is still out.
  let s = c.summarizeMoney(c.normalizeMoney({ depreciation: 6000 }).money);
  assert.strictEqual(s.derived.depreciation_still_out, 6000);
  // After a partial release:
  s = c.summarizeMoney(c.normalizeMoney({ depreciation: 6000, recoverable_depreciation_released: 4000 }).money);
  assert.strictEqual(s.derived.depreciation_still_out, 2000);
  // Fully released:
  s = c.summarizeMoney(c.normalizeMoney({ depreciation: 6000, recoverable_depreciation_released: 6000 }).money);
  assert.strictEqual(s.derived.depreciation_still_out, 0);
});
test('a negative amount is refused, not stored', () => {
  const n = c.normalizeMoney({ rcv: -5 });
  assert.ok(n.problems.some((p) => /rcv/.test(p)));
  assert.strictEqual(n.money.rcv, null);
});
test('a non-numeric amount is refused', () => {
  assert.ok(c.normalizeMoney({ rcv: 'lots' }).problems.length > 0);
});
test('milestone dates validate as dates, blank stays null', () => {
  const n = c.normalizeMoney({ acv_check_received: '2026-08-24', final_invoice_submitted: '' });
  assert.strictEqual(n.money.acv_check_received, '2026-08-24');
  assert.strictEqual(n.money.final_invoice_submitted, null);
  assert.ok(c.normalizeMoney({ acv_check_received: 'yesterday' }).problems.length > 0);
});
test('summarize never mutates the input and never invents a stored total', () => {
  const money = c.normalizeMoney({ rcv: 100, depreciation: 20, acv: 80 }).money;
  const before = JSON.stringify(money);
  c.summarizeMoney(money);
  assert.strictEqual(JSON.stringify(money), before);
});

console.log('\nStatus pipeline — the seven real steps:');
test('seven ordered statuses, waiting is a flag not a step', () => {
  assert.strictEqual(c.CLAIM_STATUSES.length, 7);
  assert.strictEqual(c.CLAIM_STATUSES[0], 'loss_reported');
  assert.strictEqual(c.CLAIM_STATUSES[6], 'depreciation_released');
  assert.strictEqual(c.CLAIM_STATUSES.indexOf(c.WAITING_FLAG), -1);
});
test('status ordering is queryable', () => {
  assert.ok(c.statusIndex('adjuster_meeting') > c.statusIndex('loss_reported'));
  assert.ok(c.statusIndex('depreciation_released') > c.statusIndex('install_complete'));
  assert.strictEqual(c.statusIndex('nonsense'), -1);
});
test('isValidStatus gates the enum', () => {
  assert.ok(c.isValidStatus('scope_written'));
  assert.ok(!c.isValidStatus('done'));
});

console.log('\nClaim + photo validation:');
test('a claim needs id, job_id, carrier, claim_number', () => {
  assert.deepStrictEqual(c.validateClaim({ id: 'C1', job_id: 'J1', carrier: 'State Farm', claim_number: 'X' }), []);
  assert.ok(c.validateClaim({ id: 'C1' }).length >= 3);
});
test('a bad peril / policy_type / status / date is rejected', () => {
  assert.ok(c.validateClaim({ id: 'C1', job_id: 'J1', carrier: 'A', claim_number: 'X', peril: 'locusts' }).some((p) => /peril/.test(p)));
  assert.ok(c.validateClaim({ id: 'C1', job_id: 'J1', carrier: 'A', claim_number: 'X', policy_type: 'MAYBE' }).some((p) => /policy_type/.test(p)));
  assert.ok(c.validateClaim({ id: 'C1', job_id: 'J1', carrier: 'A', claim_number: 'X', status: 'flying' }).some((p) => /status/.test(p)));
  assert.ok(c.validateClaim({ id: 'C1', job_id: 'J1', carrier: 'A', claim_number: 'X', date_of_loss: '08/24/2026' }).some((p) => /date_of_loss/.test(p)));
});
test('a claim can be opened before any money is known', () => {
  // carrier + claim number first; money arrives over 45-90 days.
  assert.deepStrictEqual(c.validateClaim({ id: 'C1', job_id: 'J1', carrier: 'Allstate', claim_number: 'AL-9' }), []);
});
test('a photo needs id and claim_id, and validates phase/elevation', () => {
  assert.deepStrictEqual(c.validatePhoto({ id: 'P1', claim_id: 'C1', phase: 'tear_off', elevation: 'front' }), []);
  assert.ok(c.validatePhoto({ id: 'P1', claim_id: 'C1', phase: 'someday' }).some((p) => /phase/.test(p)));
  assert.ok(c.validatePhoto({ id: 'P1', claim_id: 'C1', elevation: 'sideways' }).some((p) => /elevation/.test(p)));
  assert.ok(c.validatePhoto({ id: 'P1' }).some((p) => /claim_id/.test(p)));
});
test('tear_off is an available evidence phase — it grounds the hidden-damage supplement', () => {
  assert.ok(c.PHOTO_PHASES.indexOf('tear_off') !== -1);
  assert.ok(c.PHOTO_PHASES.indexOf('adjuster_meeting') !== -1);
});

console.log('\n' + passed + ' passed, ' + failed + ' failed');
if (failed > 0) process.exit(1);
