// api/_lib/law-trust-reconcile.test.js
// REQUIREMENT: an attorney trust reconciliation cannot report balanced while a client
//   ledger is overdrawn, because trust-account arithmetic is a regulatory
//   obligation and not a report
//
//
// Run: node api/_lib/law-trust-reconcile.test.js
//
// Every arm is BOTH directions. A reconciliation that reported DISAGREES on
// everything would pass every "it caught the discrepancy" arm on its own, and a
// tautology like the client-side `ledgerVsClient` passes every "it agrees" arm.
// The pairs are what say anything.
'use strict';
const assert = require('assert');
const { reconcileTrustLedger: reconcile, cents, UNATTRIBUTED } = require('./law-trust-reconcile');

let pass = 0, fail = 0;
function t(name, fn) {
  try { fn(); pass++; console.log('PASS ' + name); }
  catch (e) { fail++; console.log('FAIL ' + name + ' -- ' + e.message); }
}

const D = (id, client, amt, date, extra) => Object.assign(
  { id: id, client_id: client, type: 'Deposit', amount: amt, date: date }, extra || {});
const W = (id, client, amt, date, extra) => Object.assign(
  { id: id, client_id: client, type: 'Disbursement', amount: amt, date: date }, extra || {});

// ── MONEY IS CENTS ─────────────────────────────────────────────────────────
t('money becomes integer cents, and an unreadable amount is null and not 0', () => {
  assert.strictEqual(cents(5000), 500000);
  assert.strictEqual(cents('1234.56'), 123456);
  assert.strictEqual(cents(0), 0, 'a real zero is money');
  assert.strictEqual(cents(''), null);
  assert.strictEqual(cents('abc'), null);
  assert.strictEqual(cents(undefined), null);
  assert.strictEqual(cents(null), null);
});

t('the classic float triple sums exactly in cents', () => {
  // 0.1 + 0.2 !== 0.3 in floats. The reconciliation must not manufacture a
  // one-cent discrepancy out of its own arithmetic.
  const out = reconcile({ rows: [
    D('T1', 'CL-1', 0.1, '2026-09-01'),
    D('T2', 'CL-1', 0.2, '2026-09-01'),
    W('T3', 'CL-1', 0.3, '2026-09-01')] });
  assert.strictEqual(out.legs.allocation_vs_ledger.ledger_cents, 0);
  assert.strictEqual(out.legs.allocation_vs_ledger.agrees, true);
});

// ── THE ABSENT LEG IS NOT AGREEMENT ────────────────────────────────────────
t('no bank statement and no device total is PARTIAL, never AGREES', () => {
  // This is the defect in the client's version: its `matches` is TRUE when
  // there is no statement, because `ledgerVsBank === null` is treated as fine.
  const out = reconcile({ rows: [D('T1', 'CL-1', 100, '2026-09-01')] });
  assert.strictEqual(out.status, 'PARTIAL');
  // ZERO, not one. allocation_vs_ledger is STRUCTURAL as of 2026-09-16 and is
  // not counted: driven, it cannot disagree -- both traversals skip on the
  // same two predicates, so the two sums are the same arithmetic over the same
  // survivors. Counting it made a reconciliation with no external leg and no
  // device leg look like it had compared something.
  assert.strictEqual(out.legs_compared, 0);
  assert.strictEqual(out.legs.bank_vs_ledger.agrees, null);
  assert.ok(/NOT COMPARED/.test(out.legs.bank_vs_ledger.why));
});

t('...and all three present and agreeing IS AGREES', () => {
  const out = reconcile({
    rows: [D('T1', 'CL-1', 100, '2026-09-01')],
    statements: [{ statement_date: '2026-09-30', bank_balance: 100 }],
    clientTotalCents: 10000,
  });
  assert.strictEqual(out.status, 'AGREES');
  assert.strictEqual(out.legs_compared, 2, 'the two legs that can actually '
    + 'disagree are the device leg and the bank leg');
});

// ── AND THE FALSIFIABLE HALF OF WHAT LEG 1 WAS SUPPOSED TO BE ──────────────
t('row conservation holds: every row is voided or in exactly one bucket', () => {
  const out = reconcile({
    rows: [D('T1', 'CL-1', 100, '2026-09-01'),
           D('T2', 'CL-2', 50, '2026-09-02'),
           { id: 'T3', client_id: 'CL-1', type: 'Deposit', amount: 25,
             date: '2026-09-03', status: 'Voided' },
           { id: 'T4', client_id: 'CL-2', type: 'Deposit', amount: 'abc',
             date: '2026-09-04' }],
  });
  assert.strictEqual(out.row_conservation.rows_in, 4);
  assert.strictEqual(out.row_conservation.rows_voided, 1);
  assert.strictEqual(out.row_conservation.rows_bucketed, 3);
  assert.strictEqual(out.row_conservation.holds, true);
});

// ── THE AS-OF FIX, WHICH IS THE REAL DEFECT IN THE EXISTING CHECK ──────────
t('the bank leg compares the ledger AS OF the statement date', () => {
  // Statement says 100 on the 15th. A deposit landed on the 20th. The books
  // are RIGHT and an all-time comparison would call this a discrepancy.
  const out = reconcile({
    rows: [D('T1', 'CL-1', 100, '2026-09-10'),
           D('T2', 'CL-1', 250, '2026-09-20')],
    statements: [{ statement_date: '2026-09-15', bank_balance: 100 }],
  });
  assert.strictEqual(out.legs.bank_vs_ledger.agrees, true,
    'the as-of balance matches the statement');
  assert.strictEqual(out.legs.bank_vs_ledger.ledger_as_of_cents, 10000);
  assert.strictEqual(out.legs.bank_vs_ledger.movement_after_statement_cents, 25000,
    'the post-statement movement is REPORTED, not hidden and not blamed');
});

t('...and a REAL bank discrepancy is still caught', () => {
  // Without this arm, "compare as of the date" would pass equally against a
  // leg that always agrees.
  const out = reconcile({
    rows: [D('T1', 'CL-1', 100, '2026-09-10')],
    statements: [{ statement_date: '2026-09-15', bank_balance: 90 }],
  });
  assert.strictEqual(out.legs.bank_vs_ledger.agrees, false);
  assert.strictEqual(out.status, 'DISAGREES');
  assert.deepStrictEqual(out.legs_disagreeing, ['bank_vs_ledger']);
});

t('the LATEST statement is used, by date and not by array order', () => {
  const out = reconcile({
    rows: [D('T1', 'CL-1', 100, '2026-09-10')],
    statements: [{ statement_date: '2026-09-30', bank_balance: 100 },
                 { statement_date: '2026-08-31', bank_balance: 0 }],
  });
  assert.strictEqual(out.legs.bank_vs_ledger.statement_date, '2026-09-30');
});

t('a statement with an unreadable date or balance is not usable', () => {
  const out = reconcile({
    rows: [D('T1', 'CL-1', 100, '2026-09-10')],
    statements: [{ statement_date: 'last Tuesday', bank_balance: 100 },
                 { statement_date: '2026-09-30', bank_balance: '' }],
  });
  assert.strictEqual(out.legs.bank_vs_ledger.agrees, null,
    'an unparseable statement must not be treated as a comparison');
});

t('a transaction with an unreadable DATE is counted nowhere and REPORTED', () => {
  // The dangerous middle case: put it before the statement and it corrupts the
  // as-of figure; put it after and it hides. Neither, and say so.
  const out = reconcile({
    rows: [D('T1', 'CL-1', 100, '2026-09-10'),
           D('T2', 'CL-1', 999, null)],
    statements: [{ statement_date: '2026-09-15', bank_balance: 100 }],
  });
  assert.strictEqual(out.legs.bank_vs_ledger.agrees, true);
  assert.strictEqual(out.legs.bank_vs_ledger.undated_rows, 1);
});

// ── THE DEVICE LEG: THE ONLY ONE THAT SEES A SYNC DIVERGENCE ───────────────
t('a device whose own total differs from the server is caught', () => {
  const out = reconcile({
    rows: [D('T1', 'CL-1', 100, '2026-09-01')],
    clientTotalCents: 60000,
  });
  assert.strictEqual(out.legs.device_vs_server.agrees, false);
  assert.strictEqual(out.status, 'DISAGREES');
});

t('...and an agreeing device is not reported as a divergence', () => {
  const out = reconcile({
    rows: [D('T1', 'CL-1', 100, '2026-09-01')],
    clientTotalCents: 10000,
  });
  assert.strictEqual(out.legs.device_vs_server.agrees, true);
});

// ── ATTRIBUTION: THE LEG THE CLIENT'S VERSION CANNOT FAIL ──────────────────
t('an UNATTRIBUTED row gets its own bucket and is still in the ledger', () => {
  const out = reconcile({ rows: [
    D('T1', 'CL-1', 100, '2026-09-01'),
    D('T2', null, 50, '2026-09-01')] });
  assert.strictEqual(out.unattributed_present, true);
  const un = out.clients.filter((c) => c.client_id === UNATTRIBUTED)[0];
  assert.ok(un, 'the unattributed bucket exists');
  assert.strictEqual(un.attributed, false);
  assert.strictEqual(un.cents, 5000);
  assert.strictEqual(out.legs.allocation_vs_ledger.ledger_cents, 15000,
    'it is in the ledger total -- dropping it would invent a discrepancy');
  assert.strictEqual(out.legs.allocation_vs_ledger.agrees, true);
});

t('a blank or whitespace client_id is UNATTRIBUTED, not a client named " "', () => {
  const out = reconcile({ rows: [D('T1', '   ', 100, '2026-09-01')] });
  assert.strictEqual(out.clients.length, 1);
  assert.strictEqual(out.clients[0].client_id, UNATTRIBUTED);
});

// ── VOIDED, EXCLUDED CONSISTENTLY BY EVERY LEG ─────────────────────────────
t('a VOIDED row is excluded from every leg and the count is reported', () => {
  // Excluded by one leg and not another is how a reconciliation invents a
  // discrepancy out of its own filters.
  const out = reconcile({
    rows: [D('T1', 'CL-1', 100, '2026-09-01'),
           D('T2', 'CL-1', 999, '2026-09-01', { status: 'Voided' })],
    statements: [{ statement_date: '2026-09-30', bank_balance: 100 }],
    clientTotalCents: 10000,
  });
  assert.strictEqual(out.voided_rows_excluded, 1);
  assert.strictEqual(out.legs.allocation_vs_ledger.ledger_cents, 10000);
  assert.strictEqual(out.status, 'AGREES');
});

// ── A NEGATIVE CLIENT BALANCE IS A DIFFERENT CONTROL FAILING ───────────────
t('a NEGATIVE client allocation is named separately, not as rounding', () => {
  // The per-client disbursement gate should make this impossible. If one
  // appears, that gate did not hold, and calling it a reconciliation
  // difference would send somebody to look in the wrong place.
  const out = reconcile({ rows: [
    D('T1', 'CL-1', 100, '2026-09-01'),
    W('T2', 'CL-2', 40, '2026-09-01')] });
  assert.deepStrictEqual(out.negative_clients, ['CL-2']);
});

t('...and a healthy ledger reports no negative clients', () => {
  const out = reconcile({ rows: [D('T1', 'CL-1', 100, '2026-09-01')] });
  assert.deepStrictEqual(out.negative_clients, []);
});

// ── UNREADABLE AMOUNTS AND UNREADABLE ROWS ─────────────────────────────────
t('an unreadable AMOUNT is counted as unreadable, not as zero', () => {
  const out = reconcile({ rows: [
    D('T1', 'CL-1', 100, '2026-09-01'),
    D('T2', 'CL-1', 'n/a', '2026-09-01')] });
  assert.strictEqual(out.unreadable_rows, 1);
  assert.strictEqual(out.clients[0].unreadable_rows, 1);
  assert.strictEqual(out.clients[0].rows, 2, 'the row still counts as a row');
  assert.strictEqual(out.legs.allocation_vs_ledger.ledger_cents, 10000);
});

t('rows that could not be READ AT ALL is CANNOT_RECONCILE, not an empty ledger', () => {
  const out = reconcile({ rows: null, statements: [] });
  assert.strictEqual(out.status, 'CANNOT_RECONCILE');
  assert.strictEqual(out.legs.allocation_vs_ledger, undefined);
});

t('an EMPTY ledger is a real measurement and is not CANNOT_RECONCILE', () => {
  const out = reconcile({ rows: [] });
  assert.strictEqual(out.legs.allocation_vs_ledger.ledger_cents, 0);
  assert.strictEqual(out.status, 'PARTIAL', 'no bank, no device -- still partial');
});

// ── AND THE SHAPE, SO NO SINGLE BOOLEAN CREEPS BACK IN ─────────────────────
t('there is NO single `matches` boolean', () => {
  const out = reconcile({ rows: [D('T1', 'CL-1', 100, '2026-09-01')] });
  assert.strictEqual(out.matches, undefined,
    "the client's `matches` is TRUE when there is no bank statement -- a green "
    + 'verdict from a comparison never made. `status` names what happened.');
  assert.ok(['AGREES', 'PARTIAL', 'DISAGREES', 'CANNOT_RECONCILE']
    .indexOf(out.status) !== -1);
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
