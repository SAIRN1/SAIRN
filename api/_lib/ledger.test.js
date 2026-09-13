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

// ── entryFromTransfers: balanced by construction (item 41, phase A) ───────
//
// The point of these is NOT that the function balances the entries the tests
// happen to try. It is that no input CAN come out unbalanced, which is a
// different claim and needs the sweep at the bottom to support it.

const tf = (transfers, o) => L.entryFromTransfers({
  today: TODAY,
  entry: Object.assign({ entry_date: '2026-09-02', memo: 'Payroll run 2026-09-02', transfers }, o || {})
});

test('a single transfer becomes a balanced, postable two-line entry', () => {
  const r = tf([{ debit_account: '6010', credit_account: '1010', amount: 4000 }]);
  assert.strictEqual(r.postable, true, JSON.stringify(r.problems));
  assert.strictEqual(r.balanced, true);
  assert.strictEqual(r.lines.length, 2);
  assert.strictEqual(r.debit_total_cents, 400000);
  assert.strictEqual(r.credit_total_cents, 400000);
});

test('the 1:n case decomposes uniquely -- payroll is one debit against three credits', () => {
  const r = tf([
    { debit_account: '6010', credit_account: '2130', amount: 400 },
    { debit_account: '6010', credit_account: '2110', amount: 600 },
    { debit_account: '6010', credit_account: '1010', amount: 4000 },
  ]);
  assert.strictEqual(r.postable, true, JSON.stringify(r.problems));
  // FOUR lines, not six: the three 6010 debits aggregate into one.
  assert.strictEqual(r.lines.length, 4);
  const wages = r.lines.filter(l => l.account_code === '6010');
  assert.strictEqual(wages.length, 1, 'the debits did not aggregate');
  assert.strictEqual(wages[0].debit_cents, 500000);
});

test('debits and credits are aggregated SEPARATELY and never netted -- an account '
  + 'on both sides gets both lines', () => {
  const r = tf([
    { debit_account: '1010', credit_account: '1100', amount: 100 },
    { debit_account: '1100', credit_account: '4010', amount: 40 },
  ]);
  assert.strictEqual(r.postable, true, JSON.stringify(r.problems));
  const ar = r.lines.filter(l => l.account_code === '1100');
  assert.strictEqual(ar.length, 2, '1100 was netted instead of carrying both sides');
  assert.strictEqual(ar[0].credit_cents + ar[1].credit_cents, 10000);
  assert.strictEqual(ar[0].debit_cents + ar[1].debit_cents, 4000);
});

test('IT SAYS WHICH PATH BUILT IT -- the two paths carry different guarantees '
  + 'and return the same object', () => {
  assert.strictEqual(tf([{ debit_account: '6010', credit_account: '1010', amount: 1 }]).built_from, 'transfers');
  assert.strictEqual(L.validateEntry({ today: TODAY, entry: entry() }).built_from, 'lines');
});

test('it refuses without today, like every other entry point', () => {
  const r = L.entryFromTransfers({ entry: { transfers: [] } });
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.error.code, 'NO_TODAY');
});

test('a transfer to the SAME account is refused -- it balances perfectly and moves nothing', () => {
  const r = tf([{ debit_account: '1010', credit_account: '1010', amount: 50 }]);
  assert.strictEqual(r.postable, false);
  assert.ok(r.problems.some(p => /moves nothing/.test(p)), JSON.stringify(r.problems));
});

test('a zero or negative amount is refused rather than reversed silently', () => {
  [0, -5].forEach((amount) => {
    const r = tf([{ debit_account: '6010', credit_account: '1010', amount }]);
    assert.strictEqual(r.postable, false, 'amount ' + amount + ' was accepted');
    assert.ok(r.problems.some(p => /greater than zero/.test(p)));
  });
});

test('a STRING amount is refused, not coerced -- "1,200.00" parsed loosely is 1', () => {
  const r = tf([{ debit_account: '6010', credit_account: '1010', amount: '1200' }]);
  assert.strictEqual(r.postable, false);
  assert.ok(r.problems.some(p => /not a number/.test(p)), JSON.stringify(r.problems));
});

test('an account outside the chart is refused, and the message names the TRANSFER '
  + 'rather than a line index that would not map back to it', () => {
  const r = tf([{ debit_account: '9999', credit_account: '1010', amount: 10 }]);
  assert.strictEqual(r.postable, false);
  assert.ok(r.problems.some(p => /^transfer 0: debit_account "9999"/.test(p)), JSON.stringify(r.problems));
});

test('no transfers at all is refused', () => {
  const r = tf([]);
  assert.strictEqual(r.postable, false);
  assert.ok(r.problems.some(p => /at least one transfer/.test(p)));
});

test("validateEntry's other rules still apply -- a missing memo is still refused", () => {
  const r = tf([{ debit_account: '6010', credit_account: '1010', amount: 10 }], { memo: '  ' });
  assert.strictEqual(r.postable, false);
  assert.ok(r.problems.some(p => /needs a memo/.test(p)), JSON.stringify(r.problems));
});

test('BALANCED BY CONSTRUCTION: a deterministic sweep of 4,096 transfer sets, and '
  + 'not one of them can come out with debits != credits', () => {
  // No Math.random: a property test whose failing case cannot be reproduced is
  // not a property test. The codes and amounts are walked, not sampled.
  const codes = Object.keys(L.ACCOUNTS);
  let checked = 0, unbalanced = 0, postable = 0;
  for (let a = 0; a < 16; a++) {
    for (let b = 0; b < 16; b++) {
      for (let n = 1; n <= 4; n++) {
        for (let cents = 1; cents <= 4; cents++) {
          const transfers = [];
          for (let k = 0; k < n; k++) {
            transfers.push({
              debit_account: codes[(a + k) % codes.length],
              credit_account: codes[(b + k * 3 + 1) % codes.length],
              amount: (cents * 7 + k) / 100,
            });
          }
          const r = tf(transfers);
          checked++;
          if (r.debit_total_cents !== r.credit_total_cents) unbalanced++;
          if (r.postable) postable++;
        }
      }
    }
  }
  assert.strictEqual(checked, 4096);
  assert.strictEqual(unbalanced, 0, unbalanced + ' of ' + checked + ' came out unbalanced');
  // ACCURACY AND STABILITY ARE TWO NUMBERS: "0 unbalanced" would also be true
  // of a function that refused everything, so the sweep asserts the postable
  // count too. Some sets legitimately refuse -- a same-account transfer occurs
  // whenever the two walks collide -- so this is a floor, not an equality.
  assert.ok(postable > 3000, 'only ' + postable + ' of ' + checked
    + ' were postable -- the sweep is passing because the function refuses, not because it balances');
});

test('CONTROL: the sweep can actually fail -- an unbalanced line array is caught '
  + 'by the same assertion', () => {
  const bad = L.validateEntry({ today: TODAY, entry: entry({
    lines: [{ account_code: '1100', debit: 1200 }, { account_code: '4010', credit: 1100 }] }) });
  assert.notStrictEqual(bad.debit_total_cents, bad.credit_total_cents,
    'the control is a no-op -- it did not produce an unbalanced entry');
  assert.strictEqual(bad.postable, false);
});

console.log(passed + ' passed');
