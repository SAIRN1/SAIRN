// tests/sairnlegacy_save_reentry.js
//
// REQUIREMENT: a second press of "Confirm Payment" while the first one's
// Pre-Need Trust write is still waiting on the server records NO second
// payment and adds NOTHING more to the plan's amount_paid -- and the hold is
// released once that write answers, is refused, or throws.
//
// Run:  node tests/sairnlegacy_save_reentry.js [path-to-sairnlegacy.html]
//
// THE DEFECT (cody b64 re-entry sweep, the shape cody b63 fixed in
// sairnmechanical saveDoc). confirmPayment pushes the payment onto the invoice
// and stores it, then -- for a Pre-Need Trust payment -- AWAITS the plan write
// BEFORE it closes the payment modal. The Confirm button stays live for that
// whole wait, and the second press re-reads the invoice the first press had
// already stored, so it pushed a SECOND payment and added the amount to the
// plan's amount_paid a second time. Money recorded twice, on a trust account.
//
//   P1  two presses while the plan write is pending: ONE payment, amount_paid
//       raised ONCE, and the second press is told why.
//   P2  once the write answers, the next press goes through.
//   P3  after a REFUSED write and after one that THROWS, the hold is released.
//   P4  CONTROL: a Cash payment (no plan write before the modal closes) is
//       unchanged -- one press, one payment, modal closed.
//
// confirmPayment is lifted from the shipped file by brace matching and run in
// a vm with stubs; no browser, no network. An extraction that fails exits 2.
// Exit: 0 all passed - 1 an arm FAILED - 2 COULD NOT RUN

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const FILE = process.argv[2] || path.join(__dirname, '..', 'sairnlegacy.html');
const html = fs.readFileSync(FILE, 'utf8').replace(/\r\n/g, '\n');

let pass = 0, fail = 0, finished = false;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  ok   ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '\n       ' + String(detail).slice(0, 400) : '')); }
}
function lift(head) {
  const i = html.indexOf(head);
  if (i < 0 || html.indexOf(head, i + 1) !== -1) {
    console.log('COULD NOT RUN: "' + head + '" found ' + (i < 0 ? 0 : 'more than one') + ' time(s) in ' + FILE);
    process.exit(2);
  }
  let k = html.indexOf('{', i), depth = 0;
  for (; k < html.length; k++) {
    if (html[k] === '{') depth++;
    else if (html[k] === '}' && --depth === 0) return html.slice(i, k + 1);
  }
  console.log('COULD NOT RUN: unbalanced ' + head); process.exit(2);
}
// The hold's declaration is lifted if it exists, so the pre-fix file (no
// declaration, no reference) runs unchanged and P1 measures the fix.
const guardDecl = (html.match(/var legPaymentSaving\s*=\s*false;/) || [''])[0];
const SRC = guardDecl + '\n' + lift('async function confirmPayment(){')
  + '\n' + lift('function invoiceTotal(inv){') + '\n' + lift('function invoicePaid(inv){');

const flush = () => new Promise((r) => setImmediate(r));

function world(source, push) {
  const store = {
    leg_invoices: JSON.stringify([{ id: 'IV-1', case_id: 'CASE-1', invoice_number: 'INV-1',
      line_items: [{ amount: 5000 }], payments: [], status: 'Draft' }]),
    leg_preneed: JSON.stringify([{ id: 'PN-1', linked_case_id: 'CASE-1', amount_paid: 1000 }])
  };
  const els = {};
  const el = (id) => (els[id] = els[id] || { id, value: '', textContent: '', classList: { add() {}, remove() {} } });
  el('pyamount').value = '250'; el('pysource').value = source;
  const ctx = {
    toasts: [], writes: [], closed: 0,
    JSON, Object, Array, Number, String, Promise,
    $: el, pyInvoiceId: 'IV-1',
    invoices: () => JSON.parse(store.leg_invoices), preneedPlans: () => JSON.parse(store.leg_preneed),
    st: (k, v) => { store[k] = JSON.stringify(v); return true; },
    legLocalToday: () => '2026-10-29',
    legWriteFailText: (r, f) => f,
    rInvoicing() {}, rPreneed() {},
    closePaymentModal: () => { ctx.closed++; },
    toast: (m) => ctx.toasts.push(String(m)),
    sdnData: (action, resource, rec) => { ctx.writes.push(resource); return push(resource, rec); }
  };
  vm.createContext(ctx); vm.runInContext(SRC, ctx);
  const inv = () => JSON.parse(store.leg_invoices)[0];
  const plan = () => JSON.parse(store.leg_preneed)[0];
  return { ctx, inv, plan };
}

(async () => {
  console.log('1. one payment at a time while the Pre-Need Trust write is pending');
  {
    // EVERY pending write is answered below -- an unanswered one would leave
    // the async IIFE unsettled, and node exits 0 on that with nothing printed.
    const answers = [];
    let pending = true;
    const w = world('Pre-Need Trust', (res) => (res === 'leg_preneed' && pending
      ? new Promise((r) => { answers.push(r); }) : Promise.resolve({ id: 'x' })));
    const first = w.ctx.confirmPayment();
    await flush();
    const second = w.ctx.confirmPayment();   // the double press, plan write still pending
    await flush();
    check('P1 a second press while the plan write is pending records NO second payment, raises amount_paid ONCE, and says so',
      w.inv().payments.length === 1 && w.plan().amount_paid === 1250
        && w.ctx.toasts.some((t) => /Still recording/.test(t)),
      JSON.stringify({ payments: w.inv().payments.length, amount_paid: w.plan().amount_paid, toasts: w.ctx.toasts }));
    pending = false;
    answers.forEach((r) => r({ id: 'PN-1' }));
    await first; await second; await flush();
    const before = { n: w.inv().payments.length, paid: w.plan().amount_paid };
    await w.ctx.confirmPayment();
    check('P2 once the plan write answers, the next press goes through: one more payment, amount_paid +250',
      w.inv().payments.length === before.n + 1 && w.plan().amount_paid === before.paid + 250,
      JSON.stringify({ before, payments: w.inv().payments.length, amount_paid: w.plan().amount_paid }));
  }
  console.log('2. the hold is released whichever way the write ends');
  for (const [label, push] of [
    ['a REFUSED plan write', (res) => Promise.resolve(res === 'leg_preneed' ? null : { id: 'x' })],
    ['a plan write that THROWS', (res) => { if (res === 'leg_preneed') return Promise.reject(new Error('offline')); return Promise.resolve({ id: 'x' }); }]
  ]) {
    const w = world('Pre-Need Trust', push);
    let threw = 0;
    try { await w.ctx.confirmPayment(); } catch (e) { threw++; }
    try { await w.ctx.confirmPayment(); } catch (e) { threw++; }
    check('P3 after ' + label + ' the next press is not held: two presses, two payments',
      w.inv().payments.length === 2 && !w.ctx.toasts.some((t) => /Still recording/.test(t)),
      JSON.stringify({ threw, payments: w.inv().payments.length, toasts: w.ctx.toasts }));
  }
  console.log('3. control');
  {
    const w = world('Cash', () => Promise.resolve({ id: 'x' }));
    await w.ctx.confirmPayment();
    check('P4 CONTROL: a Cash payment records one payment, closes the modal and touches no plan',
      w.inv().payments.length === 1 && w.ctx.closed === 1 && w.plan().amount_paid === 1000
        && w.ctx.toasts.some((t) => /^Payment recorded/.test(t)),
      JSON.stringify({ payments: w.inv().payments.length, closed: w.ctx.closed, toasts: w.ctx.toasts }));
  }
  finished = true;
  console.log('\n' + (fail ? 'FAILED' : 'ok') + '  sairnlegacy save re-entry: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('COULD NOT RUN: ' + e.stack); process.exit(2); });
// An arm left waiting on a promise nobody settles ends the process with the
// IIFE unsettled -- node exits 0 on that. It must read as COULD NOT RUN.
process.on('exit', (code) => { if (!finished) { console.log('COULD NOT RUN: the run ended before its last arm'); process.exitCode = 2; } });
