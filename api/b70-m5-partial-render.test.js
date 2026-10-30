// hank b70 (M5 render): a STALE deposit in transit (b69, api/_lib/law-trust-
// reconcile.js) must REACH the Trust Accounting panel as "Partly reconciled"
// with the bank leg's reason -- not "Reconciled".
//
// This drives sairnlaw.html's REAL rTrust() and LAW_RECON_STATUS, cut from the
// file, against the REAL reconciler's output. Only the server round-trip
// (trustReconcileServer) and the DOM are stubbed. It is NOT the live check:
// that needs an authenticated SAIRNlaw session, which this session does not
// hold (b70 handoff, M5L).
//
// Arm X feeds the same panel a FRESH deposit in transit and requires
// "Reconciled", so the PARTIAL arm cannot pass on a panel that never says
// anything else.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const { reconcileTrustLedger } = require('./_lib/law-trust-reconcile');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'sairnlaw.html'), 'utf8');
let passed = 0, failed = 0;
function arm(name, ok, detail) {
  if (ok) { passed++; console.log('  ok   ' + name); }
  else { failed++; console.log('  FAIL ' + name + (detail ? '  -- ' + detail : '')); }
}

function cut(startSig) {
  const i = HTML.indexOf(startSig);
  if (i < 0 || HTML.indexOf(startSig, i + 1) !== -1) return null;
  const j = HTML.indexOf('\nfunction ', i + startSig.length);
  return j < 0 ? null : HTML.slice(i, j);
}
const statusSrc = (HTML.match(/var LAW_RECON_STATUS=\{[\s\S]*?\n\};/) || [])[0];
const rTrustSrc = cut('function rTrust(){');
const hSrc = (HTML.match(/^function H\(s\)\{[^\n]*\}$/m) || [])[0];
if (!statusSrc || !rTrustSrc || !hSrc) {
  console.log('COULD NOT RUN: LAW_RECON_STATUS, rTrust() or H() not found exactly once in sairnlaw.html');
  process.exit(2);
}

const D = (id, c, a, d, x) => Object.assign({ id, client_id: c, type: 'Deposit', amount: a, date: d }, x || {});
function books(depDate) {
  return reconcileTrustLedger({
    rows: [D('T1', 'CL-A', 1000, '2026-09-01', { cleared_on: '2026-09-02' }),
           D('T2', 'CL-B', 500, '2026-09-03', { cleared_on: '2026-09-04' }),
           D('T9', 'CL-B', 40, depDate, { cleared: false })],
    statements: [{ statement_date: '2026-09-30', bank_balance: 1500 }],
    clientTotalCents: 154000,
  });
}

async function render(result) {
  const els = {};
  const el = (id) => (els[id] = els[id] || { id, innerHTML: '', textContent: '', style: {} });
  const ctx = {
    $: el, fmt: (n) => '$' + Number(n).toFixed(2),
    lawRenderDemoNotice() {}, rCountersignQueue() {}, fillMatterSelects() {},
    trustTransactions: () => [], trustFigures: () => ({ bankBal: 1500, ledgerBal: 1540, clientSum: 1540 }),
    clientLedgerBalance: () => 0, clientLabel: (c) => c,
    trustReconcileServer: () => Promise.resolve({ ok: true, result }),
    lawTrustLastResult: null, console,
  };
  vm.createContext(ctx);
  vm.runInContext(hSrc + '\n' + statusSrc + '\n' + rTrustSrc, ctx);
  ctx.rTrust();
  await new Promise((r) => setTimeout(r, 0));
  await new Promise((r) => setTimeout(r, 0));
  return els['tr-reconcile-result'] ? els['tr-reconcile-result'].innerHTML : '';
}

(async () => {
  const stale = books('2026-07-01');
  arm('the reconciler itself returns PARTIAL for a 91-day-old deposit in transit', stale.status === 'PARTIAL', stale.status);
  const html = await render(stale);
  arm('the panel badge reads "Partly reconciled", not "Reconciled"',
    /Partly reconciled/.test(html) && !/>&#10003; Reconciled/.test(html), html.slice(0, 200));
  arm('the panel shows the bank leg\'s reason, naming the stale deposit',
    /NOT RECONCILED ON THIS LEG ALONE/.test(html) && /more than 30 days/.test(html), html.slice(0, 400));

  const fresh = books('2026-09-28');
  const htmlFresh = await render(fresh);
  arm('X. CONTROL: a FRESH deposit in transit renders "Reconciled" -- the panel can say both',
    fresh.status === 'AGREES' && /Reconciled/.test(htmlFresh) && !/Partly reconciled/.test(htmlFresh), htmlFresh.slice(0, 200));

  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  process.exit(failed ? 1 : 0);
})();
