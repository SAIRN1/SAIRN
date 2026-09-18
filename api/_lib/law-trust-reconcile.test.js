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

t('a transaction with an unreadable DATE is counted nowhere and NOT COMPARED', () => {
  // The dangerous middle case: put it before the statement and it corrupts the
  // as-of figure; put it after and it hides. Neither, and say so.
  //
  // ── THIS ASSERTION USED TO PIN THE DEFECT (corrected 2026-09-18) ────────
  // It read `assert.strictEqual(out.legs.bank_vs_ledger.agrees, true)` -- a
  // GREEN verdict on a fixture where $999 of client trust money is in the
  // ledger and in no comparison at all. The undated_rows assertion beside it
  // was right and was doing all the work; the `agrees: true` beside it was the
  // half that made the whole thing safe-looking. An independent review found it
  // in the product, and it turned out the suite was holding it in place.
  //
  // `agrees` is now NULL with the reason named, because a comparison over part
  // of the ledger is not a reconciliation of it -- the same distinction this
  // file already draws when a leg was never supplied.
  const out = reconcile({
    rows: [D('T1', 'CL-1', 100, '2026-09-10'),
           D('T2', 'CL-1', 999, null)],
    statements: [{ statement_date: '2026-09-15', bank_balance: 100 }],
  });
  assert.strictEqual(out.legs.bank_vs_ledger.agrees, null,
    'a bank leg computed over part of the ledger reported agreement');
  assert.strictEqual(out.legs.bank_vs_ledger.undated_rows, 1);
  assert.strictEqual(out.legs.bank_vs_ledger.undated_cents, 99900,
    'the amount that fell outside the comparison is not reported');
  assert.match(out.legs.bank_vs_ledger.why, /NOT COMPARED/);
  // And the money identity is what makes it visible without reading a leg.
  assert.strictEqual(out.money_conservation.holds, false);
  assert.strictEqual(out.money_conservation.unaccounted_cents, 99900);
  // NOT 'AGREES'. It is also not 'DISAGREES' -- nothing here says the books are
  // wrong, only that part of them was never compared.
  assert.strictEqual(out.status, 'PARTIAL');
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

// ═══════════════════════════════════════════════════════════════════════════
// MONEY CONSERVATION ACROSS THE DATE SPLIT (2026-09-18)
//
// row_conservation asks whether every ROW ended up somewhere. This is the same
// question about the MONEY, and it is the defect an independent review of this
// file found: an UNDATED row is excluded from BOTH sides of the statement
// split, so `asOf + afterStatement` silently stops equalling the ledger.
// ═══════════════════════════════════════════════════════════════════════════

t('THE ONE: an undated deposit no longer produces AGREES over money nothing reconciled', () => {
  // The exact fixture from the review. Two legs compare -- device and bank --
  // and before this change both agreed while $500 sat in the ledger and in no
  // comparison, with the only cue an `undated_rows: 1` nested inside a leg
  // that said `agrees: true`.
  const out = reconcile({
    rows: [D('T1', 'CL-1', 100, '2026-09-01'),
           D('T2', 'CL-2', 500, null)],
    statements: [{ statement_date: '2026-09-15', bank_balance: 100 }],
    clientTotalCents: 60000,
  });
  assert.notStrictEqual(out.status, 'AGREES',
    'the whole defect: a green verdict over 50000 cents nothing reconciled');
  assert.strictEqual(out.status, 'PARTIAL');
  assert.strictEqual(out.money_conservation.holds, false);
  assert.strictEqual(out.money_conservation.unaccounted_cents, 50000);
  assert.strictEqual(out.legs.device_vs_server.agrees, true,
    'the device leg is unaffected -- it compares totals, not a date split');
});

t('THE CONTROL: the same money DATED after the statement is accounted, and AGREES', () => {
  // This is what makes the case above a defect rather than a limitation.
  // Post-statement money IS reported -- movement_after_statement_cents names it
  // and a reader can see where it went. Undated money was dropped, and the two
  // were presented identically.
  const out = reconcile({
    rows: [D('T1', 'CL-1', 100, '2026-09-01'),
           D('T2', 'CL-2', 500, '2026-09-20')],
    statements: [{ statement_date: '2026-09-15', bank_balance: 100 }],
    clientTotalCents: 60000,
  });
  assert.strictEqual(out.status, 'AGREES');
  assert.strictEqual(out.legs.bank_vs_ledger.movement_after_statement_cents, 50000);
  assert.strictEqual(out.money_conservation.holds, true);
  assert.strictEqual(out.money_conservation.unaccounted_cents, 0);
});

t('the identity is NULL with no statement, never true', () => {
  // There is no date split to conserve across, and reporting `holds: true` for
  // an identity nothing evaluated is the shape this file refuses everywhere.
  const out = reconcile({ rows: [D('T1', 'CL-1', 100, '2026-09-01')] });
  assert.strictEqual(out.money_conservation.holds, null);
  assert.match(out.money_conservation.why, /NOT an identity that held/);
});

t('a BROKEN money identity is PARTIAL, not DISAGREES', () => {
  // Nothing here says the books are wrong. It says part of them was never
  // compared, which is a different answer and must not be reported as a
  // discrepancy the data does not support.
  const out = reconcile({
    rows: [D('T1', 'CL-1', 100, '2026-09-01'), D('T2', 'CL-2', 500, null)],
    statements: [{ statement_date: '2026-09-15', bank_balance: 100 }],
    clientTotalCents: 60000,
  });
  assert.strictEqual(out.status, 'PARTIAL');
  assert.deepStrictEqual(out.legs_disagreeing, []);
});

// ═══════════════════════════════════════════════════════════════════════════
// OUTSTANDING ITEMS (2026-09-18)
//
// The second review finding: an uncleared cheque dated before the statement
// made the bank leg read DISAGREES while the books were entirely right. There
// was no cleared / outstanding concept anywhere in the module, the endpoint or
// the schema. It is the commonest legitimate ledger-versus-bank difference in
// trust accounting.
// ═══════════════════════════════════════════════════════════════════════════

t('THE ONE: an uncleared cheque no longer reads as a discrepancy', () => {
  // $140 in, $40 cheque written on the 14th and not yet cleared. The bank still
  // shows $140; the books show $100. Both are right.
  const out = reconcile({
    rows: [D('T1', 'CL-1', 140, '2026-09-01', { cleared_on: '2026-09-02' }),
           W('T2', 'CL-1', 40, '2026-09-14', { cleared: false })],
    statements: [{ statement_date: '2026-09-15', bank_balance: 140 }],
  });
  const b = out.legs.bank_vs_ledger;
  assert.strictEqual(b.clearance_tracked, true);
  assert.strictEqual(b.ledger_as_of_cents, 10000);
  assert.strictEqual(b.outstanding_cents, -4000, 'the uncleared cheque is not outstanding');
  assert.strictEqual(b.outstanding_disbursements, 1);
  assert.strictEqual(b.expected_bank_cents, 14000);
  assert.strictEqual(b.agrees, true,
    'a correct set of books with an uncleared cheque still reads as a discrepancy');
});

t('a DEPOSIT IN TRANSIT is outstanding the other way', () => {
  // Recorded on the 14th, not in the bank by the 15th. The bank is LOWER than
  // the books, and that is also correct.
  const out = reconcile({
    rows: [D('T1', 'CL-1', 100, '2026-09-01', { cleared_on: '2026-09-02' }),
           D('T2', 'CL-1', 60, '2026-09-14', { cleared: false })],
    statements: [{ statement_date: '2026-09-15', bank_balance: 100 }],
  });
  const b = out.legs.bank_vs_ledger;
  assert.strictEqual(b.outstanding_cents, 6000);
  assert.strictEqual(b.outstanding_deposits_in_transit, 1);
  assert.strictEqual(b.agrees, true);
});

t('a clearance dated AFTER the statement is still outstanding as of it', () => {
  // The whole point of an as-of comparison. A cheque that cleared on the 20th
  // had not cleared on the 15th.
  const out = reconcile({
    rows: [D('T1', 'CL-1', 140, '2026-09-01', { cleared_on: '2026-09-02' }),
           W('T2', 'CL-1', 40, '2026-09-14', { cleared_on: '2026-09-20' })],
    statements: [{ statement_date: '2026-09-15', bank_balance: 140 }],
  });
  assert.strictEqual(out.legs.bank_vs_ledger.outstanding_cents, -4000);
  assert.strictEqual(out.legs.bank_vs_ledger.agrees, true);
});

t('a REAL discrepancy is still caught when clearance IS tracked', () => {
  // The adjustment must not become a way for any difference to be explained.
  const out = reconcile({
    rows: [D('T1', 'CL-1', 140, '2026-09-01', { cleared_on: '2026-09-02' })],
    statements: [{ statement_date: '2026-09-15', bank_balance: 900 }],
  });
  assert.strictEqual(out.legs.bank_vs_ledger.agrees, false);
  assert.strictEqual(out.status, 'DISAGREES');
});

t('UNTRACKED clearance still COMPARES, and discloses the limit', () => {
  // The first version of this change returned null the moment no row carried
  // clearance information -- which is every practice today, since nothing has
  // ever written the field. That removes the only externally-sourced leg from
  // every existing licence, and a leg permanently NOT COMPARED is its own alarm
  // nobody reads. So the old comparison stands and the limit is stated.
  const out = reconcile({
    rows: [D('T1', 'CL-1', 100, '2026-09-01')],
    statements: [{ statement_date: '2026-09-15', bank_balance: 100 }],
  });
  const b = out.legs.bank_vs_ledger;
  assert.strictEqual(b.clearance_tracked, false);
  assert.strictEqual(b.agrees, true, 'the pre-existing comparison was withdrawn');
  assert.match(b.why, /WITHOUT AN OUTSTANDING-ITEM ADJUSTMENT/);
  assert.match(b.why, /check the outstanding items before treating it as an error/);
});

t('an unreadable cleared_on is NOT a clearance', () => {
  // Same strictness every other date in this file keeps: `new Date` silently
  // repairs an impossible date, and a cheque "cleared" on 2026-02-31 would
  // otherwise drop out of the outstanding set.
  const out = reconcile({
    rows: [W('T1', 'CL-1', 40, '2026-09-14', { cleared_on: '2026-02-31' })],
    statements: [{ statement_date: '2026-09-15', bank_balance: 0 }],
  });
  // The row says nothing readable about clearing, so it is not counted as
  // stated and not counted as outstanding -- it is simply untracked.
  assert.strictEqual(out.legs.bank_vs_ledger.clearance_stated_rows, 0);
  assert.strictEqual(out.legs.bank_vs_ledger.outstanding_cents, 0);
});

t('a VOIDED row is outstanding nowhere', () => {
  const out = reconcile({
    rows: [D('T1', 'CL-1', 100, '2026-09-01', { cleared_on: '2026-09-02' }),
           W('T2', 'CL-1', 40, '2026-09-14', { cleared: false, status: 'Voided' })],
    statements: [{ statement_date: '2026-09-15', bank_balance: 100 }],
  });
  assert.strictEqual(out.legs.bank_vs_ledger.outstanding_cents, 0);
  assert.strictEqual(out.legs.bank_vs_ledger.agrees, true);
});

t('AN IMPOSSIBLE DATE IS NOT A DATE -- found by the arm above, fixed in dayOf', () => {
  // The module's own dayOf() was a SHAPE check, so 2026-02-31 passed. The
  // consequence here is money: an impossible statement_date becomes the as-of
  // boundary, and an impossible cleared_on marks an uncleared cheque cleared
  // and moves the expected bank balance by its amount.
  const impossible = reconcile({
    rows: [D('T1', 'CL-1', 100, '2026-09-01')],
    statements: [{ statement_date: '2026-02-31', bank_balance: 100 }],
  });
  assert.strictEqual(impossible.legs.bank_vs_ledger.agrees, null,
    'an impossible statement date was used as the as-of boundary');
  const leap = reconcile({
    rows: [D('T1', 'CL-1', 100, '2024-02-29')],
    statements: [{ statement_date: '2024-02-29', bank_balance: 100 }],
  });
  assert.strictEqual(leap.legs.bank_vs_ledger.agrees, true,
    'a REAL leap day was rejected -- the fix over-corrected');
  const notLeap = reconcile({
    rows: [D('T1', 'CL-1', 100, '2026-02-28')],
    statements: [{ statement_date: '2026-02-29', bank_balance: 100 }],
  });
  assert.strictEqual(notLeap.legs.bank_vs_ledger.agrees, null,
    'Feb 29 in a non-leap year was accepted');
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
