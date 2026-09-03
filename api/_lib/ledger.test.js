// api/_lib/ledger.test.js
// Plain node:assert tests. Run: node api/_lib/ledger.test.js
//
// This is a general ledger. The tests that matter are the ones that make it
// REFUSE. An accounting system that accepts a wrong entry is worse than one
// that has no entries, because the wrong one gets believed.

const assert = require('assert');
const L = require('./ledger');

let passed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n      ' + e.message); process.exitCode = 1; }
}

const TODAY = '2026-09-02';
const entry = (o) => Object.assign({
  entry_date: '2026-09-02', memo: 'Invoice INV-1001 issued',
  lines: [{ account_code: '1100', debit: 1200 }, { account_code: '4010', credit: 1200 }]
}, o || {});

// ── it refuses to assume ──────────────────────────────────────────────────

test('every entry point REFUSES without today rather than defaulting to UTC now', () => {
  ['validateEntry', 'reversalOf', 'trialBalance'].forEach((fn) => {
    const r = L[fn]({});
    assert.strictEqual(r.ok, false, fn + ' should refuse');
    assert.strictEqual(r.error.code, 'NO_TODAY');
  });
});

// ── THE RULE ──────────────────────────────────────────────────────────────

test('a balanced entry is postable, and reports both totals', () => {
  const r = L.validateEntry({ today: TODAY, entry: entry() });
  assert.strictEqual(r.balanced, true);
  assert.strictEqual(r.postable, true);
  assert.strictEqual(r.debit_total, 1200);
  assert.strictEqual(r.credit_total, 1200);
  assert.deepStrictEqual(r.problems, []);
});

test('AN UNBALANCED ENTRY IS REFUSED, and the message carries both totals and the gap', () => {
  const r = L.validateEntry({ today: TODAY, entry: entry({
    lines: [{ account_code: '1100', debit: 1200 }, { account_code: '4010', credit: 1150 }] }) });
  assert.strictEqual(r.balanced, false);
  assert.strictEqual(r.postable, false);
  assert.ok(/does not balance: debits 1200 vs credits 1150, out by 50/.test(r.problems.join(' ')),
    'a refusal nobody can act on without redoing the arithmetic is half a refusal: ' + r.problems.join(' '));
});

test('a SINGLE-SIDED entry is refused BY NAME -- it is what the old ledger did', () => {
  const r = L.validateEntry({ today: TODAY, entry: entry({ lines: [{ account_code: '1010', debit: 500 }] }) });
  assert.strictEqual(r.postable, false);
  assert.ok(/at least two lines/.test(r.problems.join(' ')));
  assert.ok(/not double-entry/.test(r.problems.join(' ')));
});

test('an all-zero entry is refused rather than counted as balanced', () => {
  const r = L.validateEntry({ today: TODAY, entry: entry({
    lines: [{ account_code: '1100', debit: 0, credit: 0 }, { account_code: '4010', debit: 0, credit: 0 }] }) });
  assert.strictEqual(r.balanced, false);
  assert.ok(/not an entry|neither a debit nor a credit/.test(r.problems.join(' ')));
});

// ── money is compared in cents, not floats ────────────────────────────────

test('a sum that floating point gets wrong still balances', () => {
  // 0.1 + 0.2 !== 0.3 as floats. In cents it is exact, and a ledger that
  // decides balance on a float comparison refuses correct entries.
  const r = L.validateEntry({ today: TODAY, entry: entry({ lines: [
    { account_code: '1100', debit: 0.1 }, { account_code: '1200', debit: 0.2 },
    { account_code: '4010', credit: 0.3 }] }) });
  assert.strictEqual(r.balanced, true, 'float arithmetic would have refused this: ' + r.problems.join(' '));
});

test('a sub-cent difference is caught rather than rounded away', () => {
  const r = L.validateEntry({ today: TODAY, entry: entry({ lines: [
    { account_code: '1100', debit: 100.005 }, { account_code: '4010', credit: 100 }] }) });
  assert.strictEqual(r.balanced, false);
});

// ── a line must be unambiguous ────────────────────────────────────────────

test('a line with BOTH a debit and a credit is refused, not netted', () => {
  const r = L.validateEntry({ today: TODAY, entry: entry({ lines: [
    { account_code: '1100', debit: 100, credit: 40 }, { account_code: '4010', credit: 60 }] }) });
  assert.strictEqual(r.postable, false);
  assert.ok(/carries BOTH/.test(r.problems.join(' ')));
});

test('a NEGATIVE amount is refused -- post the other side instead', () => {
  const r = L.validateEntry({ today: TODAY, entry: entry({ lines: [
    { account_code: '1100', debit: -500 }, { account_code: '4010', credit: -500 }] }) });
  assert.strictEqual(r.postable, false);
  assert.ok(/negative/.test(r.problems.join(' ')));
});

test('a STRING amount is refused, never coerced', () => {
  const r = L.validateEntry({ today: TODAY, entry: entry({ lines: [
    { account_code: '1100', debit: '1,200.00' }, { account_code: '4010', credit: 1200 }] }) });
  assert.strictEqual(r.postable, false);
  assert.ok(/not a number/.test(r.problems.join(' ')),
    '"1,200.00" parsed loosely becomes 1, and a ledger is the last place to discover that');
});

test('an account code outside the chart is refused', () => {
  const r = L.validateEntry({ today: TODAY, entry: entry({ lines: [
    { account_code: '9999', debit: 100 }, { account_code: '4010', credit: 100 }] }) });
  assert.strictEqual(r.postable, false);
  assert.ok(/not in the chart of accounts/.test(r.problems.join(' ')));
});

test('an entry with no memo is refused', () => {
  const r = L.validateEntry({ today: TODAY, entry: entry({ memo: '' }) });
  assert.strictEqual(r.postable, false);
  assert.ok(/needs a memo/.test(r.problems.join(' ')));
});

test('a refusal names EVERY problem, not the first', () => {
  const r = L.validateEntry({ today: TODAY, entry: entry({ memo: '', entry_date: 'soon', lines: [
    { account_code: '9999', debit: 100 }, { account_code: '4010', credit: 90 }] }) });
  assert.ok(r.problems.length >= 4, 'got ' + JSON.stringify(r.problems));
});

// ── reversal is the only correction ───────────────────────────────────────

test('a reversal swaps the sides and does NOT negate the amounts', () => {
  const r = L.reversalOf({ today: TODAY, entry: {
    entry_id: 'JE-1', status: 'posted', memo: 'Invoice INV-1001 issued', source_app: 'sairnbiz',
    lines: [{ account_code: '1100', debit: 1200, credit: 0 }, { account_code: '4010', debit: 0, credit: 1200 }] } });
  assert.strictEqual(r.ok, true);
  assert.strictEqual(r.entry.lines[0].credit, 1200);
  assert.strictEqual(r.entry.lines[0].debit, 0);
  assert.strictEqual(r.entry.lines[1].debit, 1200);
  assert.ok(r.entry.lines.every(l => l.debit >= 0 && l.credit >= 0),
    'a negative debit is not a credit in any ledger a reader would recognise');
  assert.ok(/Reversal of JE-1/.test(r.entry.memo));
  // And the mirror must itself be postable.
  const v = L.validateEntry({ today: TODAY, entry: r.entry });
  assert.strictEqual(v.postable, true);
});

test('only a POSTED entry can be reversed', () => {
  const r = L.reversalOf({ today: TODAY, entry: { entry_id: 'JE-2', status: 'draft', lines: [] } });
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.error.code, 'NOT_POSTED');
});

// ── trial balance ─────────────────────────────────────────────────────────

test('the trial balance totals by account and reports in_balance', () => {
  const t = L.trialBalance({ today: TODAY, lines: [
    { account_code: '1100', debit: 1200, credit: 0 }, { account_code: '4010', debit: 0, credit: 1200 },
    { account_code: '1010', debit: 1200, credit: 0 }, { account_code: '1100', debit: 0, credit: 1200 }] });
  assert.strictEqual(t.in_balance, true);
  assert.strictEqual(t.debit_total, 2400);
  const ar = t.accounts.filter(a => a.account_code === '1100')[0];
  assert.strictEqual(ar.balance, 0, 'invoiced then paid nets AR to zero');
  const cash = t.accounts.filter(a => a.account_code === '1010')[0];
  assert.strictEqual(cash.balance, 1200, 'a debit increases an asset');
  const rev = t.accounts.filter(a => a.account_code === '4010')[0];
  assert.strictEqual(rev.balance, 1200, 'a credit increases revenue, shown positive on its normal side');
});

test('an out-of-balance book is REPORTED, not quietly summed', () => {
  const t = L.trialBalance({ today: TODAY, lines: [
    { account_code: '1100', debit: 100, credit: 0 }, { account_code: '4010', debit: 0, credit: 90 }] });
  assert.strictEqual(t.in_balance, false);
  assert.strictEqual(t.difference, 10);
});

test('an UNREADABLE stored line is counted and declared, never dropped', () => {
  const t = L.trialBalance({ today: TODAY, lines: [
    { account_code: '1100', debit: 100, credit: 0 }, { account_code: '4010', debit: 0, credit: 100 },
    { account_code: '9999', debit: 50, credit: 0 }] });
  assert.strictEqual(t.lines_skipped, 1);
  assert.strictEqual(t.in_balance, true);
  assert.ok(/short by them/.test(t.problems.join(' ')),
    'a trial balance that silently omits rows balances for the wrong reason');
});

// ── the module surface ────────────────────────────────────────────────────

test('the chart of accounts is a closed list, and every entry in it is typed', () => {
  Object.keys(L.ACCOUNTS).forEach(k => {
    assert.ok(/^[0-9]{4}$/.test(k), k + ' is not a four-digit code');
    assert.ok(['asset','liability','equity','revenue','expense'].indexOf(L.ACCOUNTS[k].type) !== -1,
      k + ' has no valid type');
  });
});

test('this module cannot reach the network -- it decides, the endpoint acts', () => {
  const src = require('fs').readFileSync(__dirname + '/ledger.js', 'utf8');
  ['fetch(', "require('https')", 'XMLHttpRequest'].forEach(n =>
    assert.strictEqual(src.indexOf(n), -1, 'found "' + n + '"'));
});

console.log(passed + ' passed');
