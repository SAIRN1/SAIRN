// api/_lib/roofing-gl-export.test.js
//
// Run:  node api/_lib/roofing-gl-export.test.js
//
// A5 is the accounting export, so the arms that matter are the ones about
// REFUSING rather than the ones about producing lines. A journal that imports
// is not a journal that is right, and every failure mode below lands as a
// clean import with a wrong trial balance -- the shape nobody notices until an
// accountant reconciles.
//
//   1. an unmapped account must REFUSE, never post to a default or suspense
//   2. an absent basis must REFUSE, never pick accrual because it is commoner
//   3. an unbalanced journal must return NOTHING, not the lines it managed
//   4. retainage must leave revenue alone and split only the receivable
//   5. an invoice with no summary must be NAMED, never silently dropped
//
// Arms 1, 2 and 5 all defend the same property from different sides: the
// export is complete or it does not exist. A partial journal is the one output
// that is worse than an error.

'use strict';
const assert = require('assert');
const G = require('./roofing-gl-export.js');
const B = require('./roofing-billing.js');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

const MAP = {
  accounts_receivable: '1200',
  retainage_receivable: '1210',
  revenue: '4000',
  sales_tax_payable: '2200',
  cash: '1000'
};

// Built through roofing-billing.js's own summarizeInvoice rather than with a
// hand-written total, which is the whole point of passing summaries in: if the
// two ever disagree, this suite disagrees with itself and says so.
function inv(id, items, taxRate, payments) {
  return { id: id, job_id: 'J-1', line_items: items, tax_rate: taxRate,
           payments: payments || [] };
}
function summarise(list) {
  const out = {};
  list.forEach(function (i) { out[i.id] = B.summarizeInvoice(i); });
  return out;
}

// FIELD NAMES AND UNITS TAKEN FROM roofing-billing.js, not guessed. The first
// draft used `qty` and a fractional tax rate; normalizeLineItems reads
// `quantity` and computeTotals treats tax_rate as a PERCENT (7.5 = 7.5%), so
// every total came back 0 and three arms failed on a fixture defect rather
// than a code one. Driving the real module is what surfaced it.
const ITEMS = [{ description: 'Tear-off and re-roof', quantity: 1, unit_price: 10000 }];

console.log('SAIRNroofing A5 -- the general-ledger export');

section('1. the account map is the contractor\'s, and an unmapped role REFUSES');

test('every role is required', () => {
  const r = G.validateAccountMap({});
  assert.strictEqual(r.problems.length, G.ACCOUNT_ROLES.length, JSON.stringify(r.problems));
});

test('a BLANK string is absent, not an account named ""', () => {
  const r = G.validateAccountMap(Object.assign({}, MAP, { revenue: '   ' }));
  assert.ok(r.problems.some(p => /revenue/.test(p)), JSON.stringify(r.problems));
});

test('an unmapped role refuses the WHOLE export and returns no lines', () => {
  const list = [inv('INV-1', ITEMS, 0)];
  const r = G.buildExport({ invoices: list, summaries: summarise(list) },
                          Object.assign({}, MAP, { revenue: '' }),
                          { basis: 'accrual' });
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.lines.length, 0,
    'it returned a partial journal -- the rows it could resolve, which is an '
    + 'unbalanced journal that looks complete');
});

test('nothing is ever posted to a default or suspense account', () => {
  // The failure this prevents: an export that "works" by inventing 9999.
  const src = require('fs').readFileSync(__dirname + '/roofing-gl-export.js', 'utf8');
  const code = src.split('\n').filter(l => !l.trim().startsWith('//')).join('\n');
  assert.ok(!/suspense/i.test(code), 'a suspense account appeared in the code');
  assert.ok(!/\|\|\s*'[0-9]{4}'/.test(code),
    'an account number is being defaulted with || in the code');
});

test('two roles sharing one account is ALLOWED and REPORTED', () => {
  const shared = Object.assign({}, MAP, { retainage_receivable: '1200' });
  const list = [inv('INV-1', ITEMS, 0)];
  const r = G.buildExport({ invoices: list, summaries: summarise(list) }, shared,
                          { basis: 'accrual' });
  assert.strictEqual(r.ok, true, JSON.stringify(r.problems));
  assert.strictEqual(r.shared_accounts.length, 1, JSON.stringify(r.shared_accounts));
  assert.ok(r.notes.some(n => /more than one role/.test(n)), JSON.stringify(r.notes));
});

section('2. the basis is STATED, never defaulted');

test('an absent basis refuses', () => {
  const list = [inv('INV-1', ITEMS, 0)];
  const r = G.buildExport({ invoices: list, summaries: summarise(list) }, MAP, {});
  assert.strictEqual(r.ok, false);
  assert.ok(r.problems.some(p => /basis is required/.test(p)), JSON.stringify(r.problems));
});

test('an unknown basis refuses rather than falling back', () => {
  const list = [inv('INV-1', ITEMS, 0)];
  const r = G.buildExport({ invoices: list, summaries: summarise(list) }, MAP,
                          { basis: 'modified-accrual' });
  assert.strictEqual(r.ok, false);
});

test('ACCRUAL recognises revenue when the invoice is issued', () => {
  const list = [inv('INV-1', ITEMS, 0)];
  const r = G.buildExport({ invoices: list, summaries: summarise(list) }, MAP,
                          { basis: 'accrual' });
  assert.strictEqual(r.ok, true, JSON.stringify(r.problems));
  const rev = r.lines.filter(l => l.role === 'revenue');
  assert.strictEqual(rev.length, 1);
  assert.strictEqual(rev[0].credit, 10000);
  assert.strictEqual(r.lines.filter(l => l.role === 'accounts_receivable')[0].debit, 10000);
});

test('CASH recognises nothing until the payment arrives', () => {
  const noPay = [inv('INV-1', ITEMS, 0)];
  let r = G.buildExport({ invoices: noPay, summaries: summarise(noPay) }, MAP,
                        { basis: 'cash' });
  assert.strictEqual(r.ok, true, JSON.stringify(r.problems));
  assert.strictEqual(r.lines.length, 0, 'cash basis booked an unpaid invoice');

  const paid = [inv('INV-1', ITEMS, 0, [{ amount: 4000, method: 'check' }])];
  r = G.buildExport({ invoices: paid, summaries: summarise(paid) }, MAP, { basis: 'cash' });
  assert.strictEqual(r.lines.filter(l => l.role === 'cash')[0].debit, 4000);
  assert.strictEqual(r.lines.filter(l => l.role === 'revenue')[0].credit, 4000);
  assert.strictEqual(r.lines.filter(l => l.role === 'accounts_receivable').length, 0,
    'cash basis raised a receivable it never had');
});

test('...and the cash-basis tax limitation is DISCLOSED, not silently applied', () => {
  const paid = [inv('INV-1', ITEMS, 7, [{ amount: 1000 }])];
  const r = G.buildExport({ invoices: paid, summaries: summarise(paid) }, MAP,
                          { basis: 'cash' });
  assert.ok(r.notes.some(n => /sales tax is not separated/i.test(n)),
    'a partial payment was apportioned without saying so: ' + JSON.stringify(r.notes));
});

section('3. tax is a liability, not revenue');

test('accrual splits tax off the receivable into sales_tax_payable', () => {
  const list = [inv('INV-1', ITEMS, 7)];
  const s = summarise(list);
  const r = G.buildExport({ invoices: list, summaries: s }, MAP, { basis: 'accrual' });
  assert.strictEqual(r.ok, true, JSON.stringify(r.problems));
  const tax = r.lines.filter(l => l.role === 'sales_tax_payable');
  assert.strictEqual(tax.length, 1, JSON.stringify(r.lines));
  assert.strictEqual(tax[0].credit, s['INV-1'].tax);
  assert.strictEqual(r.lines.filter(l => l.role === 'revenue')[0].credit,
    Math.round((s['INV-1'].total - s['INV-1'].tax) * 100) / 100,
    'tax leaked into revenue');
});

test('a zero-tax invoice emits NO tax line at all', () => {
  const list = [inv('INV-1', ITEMS, 0)];
  const r = G.buildExport({ invoices: list, summaries: summarise(list) }, MAP,
                          { basis: 'accrual' });
  assert.strictEqual(r.lines.filter(l => l.role === 'sales_tax_payable').length, 0,
    'a 0.00 line is noise in a journal somebody reads by eye');
});

section('4. RETAINAGE is its own receivable -- the roofing-specific line');

test('retainage splits the receivable and leaves revenue whole', () => {
  const list = [inv('INV-1', ITEMS, 0)];
  const r = G.buildExport({ invoices: list, summaries: summarise(list),
                            retainage: { 'INV-1': 1000 } },
                          MAP, { basis: 'accrual' });
  assert.strictEqual(r.ok, true, JSON.stringify(r.problems));
  const ar = r.lines.filter(l => l.role === 'accounts_receivable')[0];
  const ret = r.lines.filter(l => l.role === 'retainage_receivable')[0];
  const rev = r.lines.filter(l => l.role === 'revenue')[0];
  assert.strictEqual(ret.debit, 1000, 'retainage was not held out');
  assert.strictEqual(ar.debit, 9000, 'the ordinary receivable was not reduced');
  assert.strictEqual(rev.credit, 10000,
    'retainage reduced REVENUE -- the work was performed and billed; only the '
    + 'collection is deferred, and booking less revenue understates the month');
});

test('no retainage means no retainage line', () => {
  const list = [inv('INV-1', ITEMS, 0)];
  const r = G.buildExport({ invoices: list, summaries: summarise(list) }, MAP,
                          { basis: 'accrual' });
  assert.strictEqual(r.lines.filter(l => l.role === 'retainage_receivable').length, 0);
});

section('5. IT BALANCES, OR IT RETURNS NOTHING');

test('a real export balances to the cent', () => {
  const list = [inv('INV-1', ITEMS, 7, [{ amount: 3000 }]),
                inv('INV-2', [{ description: 'Repair', quantity: 3, unit_price: 412.33 }], 6.25)];
  const r = G.buildExport({ invoices: list, summaries: summarise(list),
                            retainage: { 'INV-2': 77.77 } },
                          MAP, { basis: 'accrual' });
  assert.strictEqual(r.ok, true, JSON.stringify(r.problems));
  assert.strictEqual(r.totals.difference, 0,
    'debits ' + r.totals.debits + ' vs credits ' + r.totals.credits);
});

// ── THE BALANCE GUARD IS UNREACHABLE FROM ANY CURRENT INPUT, AND THAT IS A
// ── FINDING RATHER THAN A REASON TO DELETE IT.
// Two corruptions of summarizeInvoice's output were tried -- a total that does
// not equal its parts, and a tax the total does not include -- and BOTH stay
// balanced. The arithmetic is why: debits are always `total`, credits are
// always `(total - tax) + tax`, and retainage splits the debit rather than
// adding to it. No summary, however wrong, can unbalance this journal.
//
// The guard stays, and the reason is written down so a later reader does not
// remove it as dead code: it fires the day somebody adds a line type that does
// not self-balance -- a discount, a write-off, a credit note -- which is
// exactly when nobody would be looking for it. What CANNOT be claimed is that
// it has been seen to fire on real input, so the second arm drives its
// arithmetic directly rather than pretending an end-to-end case exists.
test('no corruption of a summary can unbalance the journal -- by construction', () => {
  const list = [inv('INV-1', ITEMS, 0)];
  const wrongTotal = summarise(list);
  wrongTotal['INV-1'] = Object.assign({}, wrongTotal['INV-1'], { total: 12345 });
  const wrongTax = summarise(list);
  wrongTax['INV-1'] = Object.assign({}, wrongTax['INV-1'], { tax: 500 });
  [wrongTotal, wrongTax].forEach(function (s) {
    const r = G.buildExport({ invoices: list, summaries: s }, MAP, { basis: 'accrual' });
    assert.strictEqual(r.ok, true, JSON.stringify(r.problems));
    assert.strictEqual(r.totals.difference, 0,
      'a corrupted summary DID unbalance it -- if that is now possible the '
      + 'guard is reachable and this arm should drive it end to end: '
      + JSON.stringify(r.totals));
  });
});

test('...so the guard is driven at its own arithmetic instead', () => {
  const t = G.totalsOf([{ debit: 100, credit: 0 }, { debit: 0, credit: 99.99 }]);
  assert.strictEqual(t.difference, 0.01, JSON.stringify(t));
  assert.strictEqual(G.totalsOf([{ debit: 100, credit: 0 }, { debit: 0, credit: 100 }]).difference, 0);
});

section('6. an invoice that cannot be exported is NAMED, never dropped');

test('a missing summary is skipped, counted, and disclosed', () => {
  const list = [inv('INV-1', ITEMS, 0), inv('INV-2', ITEMS, 0)];
  const s = summarise(list);
  delete s['INV-2'];
  const r = G.buildExport({ invoices: list, summaries: s }, MAP, { basis: 'accrual' });
  assert.strictEqual(r.ok, true, JSON.stringify(r.problems));
  assert.strictEqual(r.skipped.length, 1, JSON.stringify(r.skipped));
  assert.strictEqual(r.skipped[0].invoice, 'INV-2');
  assert.ok(r.notes.some(n => /NOT exported/.test(n)),
    'the skip is not surfaced in notes, so a month short one invoice looks '
    + 'complete: ' + JSON.stringify(r.notes));
});

section('7. the CSV, and it is deliberately not IIF');

test('toCsv emits a header and one row per line', () => {
  const list = [inv('INV-1', ITEMS, 7)];
  const r = G.buildExport({ invoices: list, summaries: summarise(list) }, MAP,
                          { basis: 'accrual' });
  const csv = G.toCsv(r);
  const rows = csv.split('\r\n');
  assert.strictEqual(rows.length, 1 + r.lines.length, csv);
  assert.ok(/^date,account,role,debit,credit,memo,reference$/.test(rows[0]), rows[0]);
});

test('a refused export produces NO csv at all', () => {
  const r = G.buildExport({ invoices: [] }, MAP, {});
  assert.strictEqual(G.toCsv(r), null,
    'a refused export produced a file, which is how a partial journal reaches '
    + 'an accountant');
});

test('nothing here claims to be IIF or a QuickBooks connection', () => {
  const src = require('fs').readFileSync(__dirname + '/roofing-gl-export.js', 'utf8');
  const code = src.split('\n').filter(l => !l.trim().startsWith('//')).join('\n');
  assert.ok(!/\.iif|intuit|oauth/i.test(code),
    'the module claims an integration it does not have');
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
