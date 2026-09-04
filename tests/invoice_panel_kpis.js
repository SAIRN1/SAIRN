// tests/invoice_panel_kpis.js
//
// Run:  node tests/invoice_panel_kpis.js
//
// The Invoices panel was rebuilt and three of its consumers were never
// retargeted. All three failed silently, and all three were found by the
// missing-DOM-target triage on 2026-09-04 rather than by anyone using the app.
//
//  1. invUpdateKPIs() computed five real figures and wrote every one of them
//     into an id belonging to the OLD panel -- inv2-total, inv2-unpaid,
//     inv2-partial, inv2-paid, inv2-ar. The four tiles a shop actually sees
//     (inv2-kpi1..4: Total Outstanding, Overdue, Open Invoices, Collected MTD)
//     have therefore shown the hardcoded "$0 / $0 / 0 / $0" from their own
//     markup since the panel shipped. A shop with real unpaid invoices was told
//     it was owed nothing. Guardian Check 0b in its purest form, kept silent by
//     that function's local `if (el)`.
//
//     NOT A RENAME: the old ids counted invoices BY STATUS, the new tiles are
//     labelled with money and with "open". Mapping one onto the other would
//     have put a count under a heading reading "Total Outstanding".
//
//  2. invMarkPaid() zeroed inv.balance and THEN pushed
//     `{amount: inv.balance}`, so every "Marked paid" payment record said the
//     customer paid 0. That is wrong on its own, and it would also have held
//     Collected MTD at zero forever, because that figure sums payment records.
//
//  3. esigCreateInvoice() -- the "Create Invoice in StoneDesk" button under a
//     signed approval -- pre-filled inv-client / inv-amount / inv-desc, none of
//     which exists any more, using a local `if(el)el.value=v`. The panel
//     opened, every field was blank, and the toast said "Invoice pre-filled
//     with deposit amount -- review and save". A confident success message for
//     a thing that did not happen, on the step between a signed approval and
//     getting paid.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

function grab(sig) {
  const s = html.indexOf(sig);
  assert.ok(s > 0, 'not found in stonedesk.html: ' + sig);
  const rest = html.slice(s);
  const m = rest.match(/\r?\n\}(?=\r?\n)/);
  assert.ok(m, 'not terminated: ' + sig);
  return rest.slice(0, m.index + m[0].length);
}

const SRC = [
  'function invUpdateKPIs() {',
  'function invMarkPaid(id) {',
  'function esigCreateInvoice(clientName){'
].map(grab).join('\n\n');

// The four tiles as the markup declares them, read from the file so this suite
// still describes the real panel if the labels move.
const TILES = (() => {
  const out = {};
  const re = /id="(inv2-kpi[1-4])">([^<]*)<\/div><div class="kpi-label">([^<]+)</g;
  let m;
  while ((m = re.exec(html))) out[m[1]] = { markupDefault: m[2], label: m[3] };
  return out;
})();

function build(opts) {
  opts = opts || {};
  const els = {};
  const mk = (id, extra) => Object.assign({ id, value: '', textContent: '', style: {}, scrollIntoView() {} }, extra || {});
  ['inv2-kpi1', 'inv2-kpi2', 'inv2-kpi3', 'inv2-kpi4', 'ai-kpi-unpaid']
    .forEach(id => { els[id] = mk(id, { textContent: (TILES[id] || {}).markupDefault || '' }); });
  ['inv2-form', 'inv2-cust', 'inv2-amount', 'inv2-desc', 'inv2-num', 'inv2-date',
   'inv2-print-modal', 'est-total', 'est-quote-out'].forEach(id => { els[id] = mk(id); });
  (opts.absent || []).forEach(id => { delete els[id]; });
  if (opts.estTotal !== undefined && els['est-total']) els['est-total'].textContent = opts.estTotal;
  if (opts.quoteNum !== undefined && els['est-quote-out']) els['est-quote-out'].textContent = opts.quoteNum;

  const toasts = [], navs = [];
  const ctx = {
    console,
    document: { getElementById: id => els[id] || null },
    sd_invoices: opts.invoices || [],
    sdLocalToday: () => opts.today || '2026-09-04',
    invSaveStore: () => true,
    invGenNum: () => 'INV-0001',
    notify: () => {},
    showToast: m => toasts.push(m),
    sbNav: id => navs.push(id)
  };
  vm.createContext(ctx);
  vm.runInContext((opts.mutate ? opts.mutate(SRC) : SRC) +
    '\nthis.api={kpis:invUpdateKPIs,markPaid:invMarkPaid,createInvoice:esigCreateInvoice};', ctx);
  return { ctx, els, toasts, navs, api: ctx.api };
}
const txt = (b, id) => (b.els[id] || {}).textContent;

console.log('StoneDesk Invoices -- four KPI tiles that had never been written\n');

section('the tiles exist and say what they are');

test('the four tiles are in the markup with the labels this suite assumes', () => {
  assert.deepStrictEqual(Object.keys(TILES).sort(), ['inv2-kpi1', 'inv2-kpi2', 'inv2-kpi3', 'inv2-kpi4']);
  assert.strictEqual(TILES['inv2-kpi1'].label, 'Total Outstanding');
  assert.strictEqual(TILES['inv2-kpi2'].label, 'Overdue');
  assert.strictEqual(TILES['inv2-kpi3'].label, 'Open Invoices');
  assert.strictEqual(TILES['inv2-kpi4'].label, 'Collected MTD');
});

test('their markup defaults really are the zeroes a shop was seeing', () => {
  assert.strictEqual(TILES['inv2-kpi1'].markupDefault, '$0');
  assert.strictEqual(TILES['inv2-kpi3'].markupDefault, '0');
});

section('each tile is computed from what its own label claims');

const INVOICES = [
  // open, overdue
  { id: 'A', status: 'Unpaid', amount: 1000, deposit: 0, balance: 1000, due: '2026-08-01', payments: [] },
  // open, not yet due
  { id: 'B', status: 'Partial', amount: 2000, deposit: 500, balance: 1500, due: '2026-10-01',
    payments: [{ amount: 500, date: '2026-09-02', method: 'Card', note: 'Deposit' }] },
  // paid, this month
  { id: 'C', status: 'Paid', amount: 400, deposit: 400, balance: 0, due: '2026-09-01',
    payments: [{ amount: 400, date: '2026-09-03', method: 'Check', note: 'Deposit' }] },
  // paid, LAST month -- must not count toward Collected MTD
  { id: 'D', status: 'Paid', amount: 900, deposit: 900, balance: 0, due: '2026-08-15',
    payments: [{ amount: 900, date: '2026-08-20', method: 'Card', note: 'Deposit' }] }
];

test('Total Outstanding is money owed, not a count of invoices', () => {
  const b = build({ invoices: INVOICES });
  b.api.kpis();
  assert.strictEqual(txt(b, 'inv2-kpi1'), '$2,500.00');
});

test('Overdue counts only open balances whose due date has passed', () => {
  const b = build({ invoices: INVOICES });
  b.api.kpis();
  assert.strictEqual(txt(b, 'inv2-kpi2'), '$1,000.00', 'B is open but not due until October');
});

test('Open Invoices is a count of everything not Paid', () => {
  const b = build({ invoices: INVOICES });
  b.api.kpis();
  assert.strictEqual(txt(b, 'inv2-kpi3'), 2);
});

test('Collected MTD sums PAYMENT records in this month, not invoice dates', () => {
  const b = build({ invoices: INVOICES });
  b.api.kpis();
  assert.strictEqual(txt(b, 'inv2-kpi4'), '$900.00',
    "B's 500 and C's 400 are this month; D's 900 was last month");
});

test('an invoice with no due date is outstanding but never overdue', () => {
  const b = build({ invoices: [{ status: 'Unpaid', balance: 700, payments: [] }] });
  b.api.kpis();
  assert.strictEqual(txt(b, 'inv2-kpi1'), '$700.00');
  assert.strictEqual(txt(b, 'inv2-kpi2'), '$0.00', 'a missing due date read as overdue');
});

test('an empty ledger shows real zeroes, which is a fact and not a placeholder', () => {
  const b = build({ invoices: [] });
  b.api.kpis();
  assert.strictEqual(txt(b, 'inv2-kpi1'), '$0.00');
  assert.strictEqual(txt(b, 'inv2-kpi3'), 0);
});

section('invMarkPaid records what was actually settled');

test('the payment record carries the balance, not zero', () => {
  const inv = { id: 'A', status: 'Unpaid', balance: 1250, payments: [] };
  const b = build({ invoices: [inv] });
  b.api.markPaid('A');
  assert.strictEqual(inv.payments.length, 1);
  assert.strictEqual(inv.payments[0].amount, 1250, 'the payment history said the customer paid nothing');
  assert.strictEqual(inv.balance, 0);
  assert.strictEqual(inv.status, 'Paid');
});

test('...and that payment then shows up in Collected MTD', () => {
  // The two defects were connected: a zeroed payment amount would have held
  // this tile at $0 forever for every manually-paid invoice.
  const inv = { id: 'A', status: 'Unpaid', balance: 1250, due: '2026-09-01', payments: [] };
  const b = build({ invoices: [inv] });
  b.api.markPaid('A');
  b.api.kpis();
  assert.strictEqual(txt(b, 'inv2-kpi4'), '$1,250.00');
});

section('Create Invoice actually pre-fills, or says it did not');

test('a signed approval pre-fills the REAL fields and opens the form', () => {
  const b = build({ estTotal: '$8,400.00', quoteNum: 'Q-1042' });
  b.api.createInvoice('Main Street Stone');
  assert.strictEqual(b.els['inv2-cust'].value, 'Main Street Stone');
  assert.strictEqual(b.els['inv2-amount'].value, 4200, 'the 50% deposit was not written');
  assert.match(String(b.els['inv2-desc'].value), /50% Deposit — Q-1042/);
  assert.strictEqual(b.els['inv2-form'].style.display, 'block',
    'the form was pre-filled while still hidden');
  assert.deepStrictEqual(b.navs, ['invoices']);
});

test('it fills the invoice number and date only if they are empty', () => {
  const b = build({ estTotal: '$1,000.00' });
  b.api.createInvoice('X');
  assert.strictEqual(b.els['inv2-num'].value, 'INV-0001');
  assert.strictEqual(b.els['inv2-date'].value, '2026-09-04');
});

test('a missing invoice panel is REPORTED, not silently skipped', () => {
  const b = build({ estTotal: '$8,400.00', absent: ['inv2-cust'] });
  b.api.createInvoice('Main Street Stone');
  assert.match(b.toasts.join(' | '), /nothing was pre-filled/i,
    'toasts were: ' + b.toasts.join(' | '));
  assert.ok(!/pre-filled with the 50% deposit/.test(b.toasts.join(' | ')));
});

test('a $0 quote total is called out rather than saved as a $0 deposit', () => {
  const b = build({ estTotal: '', quoteNum: 'Q-1' });
  b.api.createInvoice('X');
  assert.match(b.toasts.join(' | '), /read as \$0/);
});

section('MUTATION: put the old ids back and the tiles go dark again');

test('MUTANT: writing to the old ids leaves all four tiles at their markup defaults', () => {
  const UNFIX = src => {
    const out = src
      .replace("s('inv2-kpi1', money(outstanding));", "s('inv2-ar', money(outstanding));")
      .replace("s('inv2-kpi2', money(overdue));", "s('inv2-unpaid', money(overdue));")
      .replace("s('inv2-kpi3', open.length);", "s('inv2-total', open.length);")
      .replace("s('inv2-kpi4', money(collected));", "s('inv2-paid', money(collected));");
    assert.notStrictEqual(out, src, 'no tile write was found -- this mutation asserts nothing');
    return out;
  };
  const b = build({ invoices: INVOICES, mutate: UNFIX });
  b.api.kpis();
  ['inv2-kpi1', 'inv2-kpi2', 'inv2-kpi3', 'inv2-kpi4'].forEach(id => {
    assert.strictEqual(txt(b, id), TILES[id].markupDefault,
      id + ' changed -- the mutant did not reproduce the defect');
  });
  assert.strictEqual(txt(b, 'inv2-kpi1'), '$0',
    'a shop owed $2,500 was shown $0, which is what shipped');
});

test('no live code writes to the five retired ids any more', () => {
  ['inv2-total', 'inv2-unpaid', 'inv2-partial', 'inv2-paid', 'inv2-ar'].forEach(id => {
    const hits = html.split('\n').filter(l =>
      l.indexOf("'" + id + "'") !== -1 && l.trim().indexOf('//') !== 0);
    assert.deepStrictEqual(hits, [], id + ' is still referenced: ' + hits.join(' | '));
  });
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
if (fail) process.exitCode = 1;
