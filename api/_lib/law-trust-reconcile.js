// api/_lib/law-trust-reconcile.js
// ---------------------------------------------------------------------------
// IOLTA RECONCILIATION FOR law_trusttx, SERVER-SIDE AND PURE.
//
// Items #46/#47, from the hover auditor's finding. Its statement of the
// principle is the specification:
//
//   "A genuine reconciliation needs THREE independent records to agree, not
//    two -- the bank statement, the ledger total, AND the sum of every
//    individual client/matter's own allocation within that ledger. The third
//    leg exists because the first two can agree perfectly while money has
//    still moved between two clients' individual allocations with the total
//    unchanged."
//
// And the warning that shaped this file more than the principle did:
//
//   "A 'three-way match' name is not automatically the same claim as a
//    three-way RECONCILIATION in the IOLTA sense unless the third leg is
//    genuinely independent per-entity attribution, NOT JUST A THIRD TOTAL
//    COMPUTED THE SAME WAY AS THE OTHER TWO."
//
// ── WHAT THE CLIENT ALREADY DOES, AND WHY IT IS NOT THIS ───────────────────
// sairnlaw.html:3134 `reconcileTrust()` already compares three figures. Read
// closely, one of its legs cannot fail:
//
//   clientIds = unique(tx.map(t => t.client_id))        // includes undefined
//   clientSum = sum over those ids of clientLedgerBalance(id, tx)
//
// Every row belongs to exactly one of those groups -- INCLUDING the rows with
// no client_id, which form the `undefined` group and are summed like any
// other. So `clientSum` PARTITIONS THE SAME ARRAY `ledgerBal` sums whole, and
// the two are equal by arithmetic. `ledgerVsClient` is a tautology that can
// only be disturbed by float summation order. That is precisely "a third total
// computed the same way as the other two".
//
// It is also CLIENT-SIDE, over ONE DEVICE'S localStorage. A device that has
// been offline, or whose writes returned "saved on this device only", will
// reconcile its own partial view and report agreement.
//
// ── SO THE INDEPENDENT LEGS HERE ARE THESE, AND THEY REALLY ARE INDEPENDENT ─
//   SERVER  the law_trusttx rows this licence actually holds server-side
//   CLIENT  the figure the device computed from its own store, passed in by
//           the caller. Two stores that can and do diverge on this platform --
//           "saved on this device only" is a whole failure class here.
//   BANK    a law_bankstatements row, entered by a human from a statement.
//
// Legs 1 and 3 are different records. Leg 2 is a different STORE of leg 1,
// which is a weaker independence than a bank statement and a real one: it is
// the only leg that can catch a sync divergence, and this file says which kind
// each leg is rather than calling them all "independent".
//
// ── AND THE AS-OF BUG, WHICH IS THE REAL DEFECT IN THE EXISTING CHECK ───────
// `reconcileTrust()` compares an ALL-TIME ledger balance against a bank
// balance that is true AS OF ONE DATE. Any deposit or disbursement recorded
// after the statement date makes them differ -- correctly, and the check
// reports it as a mismatch. A reconciliation that cannot distinguish "the
// books are wrong" from "three cheques cleared since Tuesday" is one nobody
// acts on, and an alarm nobody acts on is one that gets turned off.
//
// So the bank leg here compares the ledger AS OF THE STATEMENT DATE, and
// reports the post-statement movement separately as its own figure.
//
// ── MONEY IS INTEGER CENTS ─────────────────────────────────────────────────
// Not floats with a round-to-2 at the end. The hover auditor's own note on
// this names the FedEx/UPS precedent: two independently computed values from
// the same input, under different but individually legitimate rounding
// conventions, produce a real systematic mismatch at scale. A reconciliation
// whose own arithmetic drifts manufactures the discrepancies it exists to
// find.
// ---------------------------------------------------------------------------

'use strict';

// Rows with no client attribution. Its own bucket, never folded into a client
// and never dropped: folded in, it invents an allocation for a client who does
// not have it; dropped, the per-client sum quietly stops equalling the ledger
// and the check reports a discrepancy whose cause is the check.
const UNATTRIBUTED = '__unattributed__';

/** Money to integer cents, or null when the value is not money at all.
 *  null is NOT 0 -- a row whose amount cannot be read is a row that cannot be
 *  reconciled, and calling it zero is the silent-omission shape this whole
 *  file is about. */
function cents(v) {
  if (v === undefined || v === null) return null;
  if (typeof v === 'string' && v.trim() === '') return null;
  const n = typeof v === 'number' ? v : Number(String(v).trim());
  if (!Number.isFinite(n)) return null;
  // Round at the boundary, once, and never again. Math.round on a .5 cent is
  // the only rounding decision in this file and it is stated here.
  return Math.round(n * 100);
}

function isVoided(row) {
  return String((row && row.status) || '') === 'Voided';
}

/** A YYYY-MM-DD date, or null. Deliberately strict: a date this cannot read
 *  must not silently become "today" or "the epoch", both of which would put
 *  every transaction on the wrong side of the as-of boundary.
 *
 *  ── IT WAS A SHAPE CHECK AND NOT A DATE CHECK (fixed 2026-09-18) ─────────
 *  The regex alone accepted `2026-02-31` and `2026-02-29` in a non-leap year.
 *  That is the exact defect api/_lib/credential-expiry.js records having fixed
 *  platform-wide: "the old body validated the SHAPE of a date and not the DATE
 *  ... `new Date` does not reject an impossible date, it SILENTLY REPAIRS IT."
 *  Here the consequence is specific and it is money: an impossible
 *  `statement_date` would have been used as the as-of boundary, and an
 *  impossible `cleared_on` would have marked an uncleared cheque as cleared and
 *  dropped it out of the outstanding set -- moving the expected bank balance by
 *  the amount of that cheque.
 *
 *  FOUND BY A TEST WRITTEN FOR SOMETHING ELSE. The arm was checking that an
 *  unreadable `cleared_on` is not a clearance, and it failed because the date
 *  was read. This function's own comment claimed "deliberately strict" while it
 *  was not, which is why it survived a reading.
 *
 *  The shared helper is the platform's one answer to what a date is; using it
 *  here removes the second opinion rather than correcting it. */
const isCalendarDate = require('./calendar-date').isCalendarDate;
function dayOf(v) {
  if (typeof v !== 'string') return null;
  const t = v.trim();
  return isCalendarDate(t) ? t : null;
}

/**
 * @param {object} input
 *   rows          {Array}  law_trusttx rows as the server holds them
 *   statements    {Array}  law_bankstatements rows
 *   clientTotalCents {number|null|undefined}
 *                          what the DEVICE computed, in cents. Optional --
 *                          absent means that leg was not supplied, which is
 *                          reported as NOT COMPARED and never as agreement.
 * @returns {object}
 */
function reconcileTrustLedger(input) {
  const rows = Array.isArray(input && input.rows) ? input.rows : null;
  const statements = Array.isArray(input && input.statements)
    ? input.statements : [];

  if (rows === null) {
    return {
      status: 'CANNOT_RECONCILE',
      why: 'the trust transactions could not be read',
      legs: {}, clients: [], unreadable_rows: null,
    };
  }

  // ── per-client allocations, in cents ────────────────────────────────────
  const byClient = {};
  let unreadable = 0;
  let voided = 0;
  rows.forEach((row) => {
    if (isVoided(row)) { voided += 1; return; }
    const id = (row && typeof row.client_id === 'string' && row.client_id.trim())
      ? row.client_id.trim() : UNATTRIBUTED;
    const b = byClient[id] || (byClient[id] = {
      client_id: id, attributed: id !== UNATTRIBUTED,
      cents: 0, rows: 0, unreadable_rows: 0,
    });
    b.rows += 1;
    const c = cents(row && row.amount);
    if (c === null) { b.unreadable_rows += 1; unreadable += 1; return; }
    const isDeposit = String((row && row.type) || '') === 'Deposit';
    b.cents += isDeposit ? c : -c;
  });

  const clients = Object.keys(byClient).sort().map((k) => byClient[k]);
  const allocationCents = clients.reduce((s, c) => s + c.cents, 0);

  // ── the ledger total, summed INDEPENDENTLY of the per-client pass ───────
  // Deliberately a second traversal rather than a sum of the buckets. Summing
  // the buckets would make this leg agree by construction, which is exactly
  // the tautology this file exists to replace -- and the whole point is that
  // it CAN disagree: a row dropped by the attribution pass and kept by this
  // one is the bug the leg is for.
  let ledgerCents = 0;
  rows.forEach((row) => {
    if (isVoided(row)) return;
    const c = cents(row && row.amount);
    if (c === null) return;
    ledgerCents += (String((row && row.type) || '') === 'Deposit') ? c : -c;
  });

  // ── the bank leg, AS OF the statement date ─────────────────────────────
  const dated = statements
    .map((s) => ({ date: dayOf(s && s.statement_date),
                   cents: cents(s && s.bank_balance) }))
    .filter((s) => s.date !== null && s.cents !== null)
    .sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));
  const latest = dated.length ? dated[dated.length - 1] : null;

  let asOfCents = null;
  let afterStatementCents = null;
  let undatedRows = 0;
  let undatedCents = 0;
  // ── OUTSTANDING ITEMS (2026-09-18) ────────────────────────────────────
  // A row is OUTSTANDING when the ledger has it on or before the statement
  // date and the BANK has not yet taken it -- an uncleared cheque, or a deposit
  // in transit. Before this, an uncleared $40 cheque made the bank leg read
  // DISAGREES while the books were entirely right, and that lands in the same
  // bucket as "the books are wrong". This file's own sentence applies: an alarm
  // that cannot tell those apart is one nobody acts on, and one nobody acts on
  // gets turned off. It is the commonest legitimate ledger-versus-bank
  // difference in trust accounting and it was not modelled at all.
  let outstandingCents = 0;      // signed: deposits in transit +, uncleared cheques -
  let outstandingDeposits = 0;
  let outstandingDisbursements = 0;
  let clearanceStated = 0;       // rows that say ANYTHING about clearing
  if (latest) {
    asOfCents = 0;
    afterStatementCents = 0;
    rows.forEach((row) => {
      if (isVoided(row)) return;
      const c = cents(row && row.amount);
      if (c === null) return;
      const signed = (String((row && row.type) || '') === 'Deposit') ? c : -c;
      const d = dayOf(row && row.date);
      if (d === null) { undatedRows += 1; undatedCents += signed; return; }
      if (d <= latest.date) {
        asOfCents += signed;
        // `cleared_on` is a DATE, same strictness as every other date here: a
        // value this cannot read is not a clearance. `cleared === false` is an
        // explicit statement that it has not cleared and counts as stated.
        const clearedOn = dayOf(row && row.cleared_on);
        const saysCleared = clearedOn !== null || row.cleared === true || row.cleared === false;
        if (saysCleared) clearanceStated += 1;
        // Outstanding = recorded in the ledger by the statement date, and NOT
        // cleared the bank by it. A clearance dated AFTER the statement is
        // still outstanding as of that statement, which is the whole point of
        // an as-of comparison.
        const clearedByStatement = (clearedOn !== null && clearedOn <= latest.date)
          || (clearedOn === null && row.cleared === true);
        if (!clearedByStatement && saysCleared) {
          outstandingCents += signed;
          if (signed >= 0) outstandingDeposits += 1; else outstandingDisbursements += 1;
        }
      } else {
        afterStatementCents += signed;
      }
    });
  }

  // ── the legs, each reported separately and never collapsed ─────────────
  const supplied = input && input.clientTotalCents;
  const deviceCents = (typeof supplied === 'number' && Number.isFinite(supplied))
    ? supplied : null;

  const legs = {
    // ── LEG 1 CANNOT FAIL TODAY, AND SAYING SO IS THE POINT (2026-09-16) ──
    // This was described as one that "CAN genuinely fail: a row the attribution
    // pass loses shows up here as a difference". DRIVEN, IT DOES NOT. Both
    // traversals skip on the same two predicates -- isVoided(), and cents()
    // returning null -- and differ only in which bucket they add to, so the
    // two sums are the same arithmetic over the same survivors. Every shape
    // tried returns agrees:true: an unreadable amount, a missing client_id, a
    // non-string client_id, a voided row, and all of them mixed.
    //
    // That is the same defect this file's own commit was named for -- "the leg
    // the existing check was asked about could not fail" -- reappearing in its
    // replacement. It is left in place because the arithmetic is worth
    // reporting, and it is LABELLED so a reader cannot mistake agreement here
    // for evidence, and EXCLUDED from legs_compared so it cannot make a
    // reconciliation look more compared than it is.
    //
    // The conservation check below is the falsifiable half: it asks whether
    // every row ENDED UP SOMEWHERE, which the two sums cannot ask because they
    // both drop the same rows before summing.
    allocation_vs_ledger: {
      allocation_cents: allocationCents,
      ledger_cents: ledgerCents,
      agrees: allocationCents === ledgerCents,
      structural: true,
      independence: 'NOT independent -- same survivors, same arithmetic, two '
        + 'traversals that skip on identical predicates. It cannot disagree '
        + 'while those predicates match, so it is reported and NOT counted '
        + 'among the compared legs.',
    },
    // Leg 2. Two different STORES of the same record.
    device_vs_server: deviceCents === null ? {
      agrees: null,
      why: 'the device did not supply its own total, so this leg was NOT '
        + 'COMPARED. That is not agreement.',
      independence: 'different store, same record',
    } : {
      device_cents: deviceCents,
      server_cents: ledgerCents,
      agrees: deviceCents === ledgerCents,
      independence: 'different store, same record -- the only leg that can '
        + 'catch a sync divergence',
    },
    // Leg 3. The genuinely external one.
    bank_vs_ledger: latest === null ? {
      agrees: null,
      why: 'no usable bank statement on file, so this leg was NOT COMPARED. '
        + 'It is the only externally-sourced leg, and without it this is not '
        + 'an IOLTA reconciliation.',
      independence: 'external record',
    } : {
      statement_date: latest.date,
      bank_cents: latest.cents,
      ledger_as_of_cents: asOfCents,
      // ── THE REAL BANK-REC IDENTITY (2026-09-18) ───────────────────────
      //   bank = ledger_as_of - outstanding
      // An uncleared cheque is IN the ledger as a negative and NOT in the bank,
      // so subtracting a negative puts the bank ABOVE the books -- which is
      // exactly what a real statement shows and what the old comparison called
      // a disagreement.
      outstanding_cents: outstandingCents,
      outstanding_deposits_in_transit: outstandingDeposits,
      outstanding_disbursements: outstandingDisbursements,
      expected_bank_cents: asOfCents - outstandingCents,
      // ── AND THE THIRD STATE, WHICH IS THE ONE THAT MATTERS ────────────
      // If NOT ONE ROW says anything about clearing, this cannot tell "every
      // item cleared" from "nobody records clearance". Treating silence as
      // fully-cleared would make every practice with an uncleared cheque read
      // DISAGREES, which is the alarm this change exists to stop; treating it
      // as fully-outstanding would invent a reconciliation nobody performed.
      // So `agrees` is NULL and the reason says which fact is missing.
      // ── WHAT `agrees` COMPARES, AND WHY IT IS NOT NULL WHEN CLEARANCE IS
      // ── UNTRACKED. The first version of this change returned null the
      // moment no row carried clearance information -- which is EVERY practice
      // today, since nothing has ever written the field. That would have
      // removed the only externally-sourced leg from every existing licence to
      // fix an over-sensitivity, and a leg that is permanently NOT COMPARED is
      // its own kind of alarm nobody reads. Recorded because it was the wrong
      // call and was driven before it shipped: five existing assertions went
      // from true/false to null, which is what surfaced it.
      //
      // So: when clearance IS tracked the comparison is the real bank-rec
      // identity, bank = as_of - outstanding. When it is NOT, the comparison is
      // the same one this leg has always made, and `clearance_tracked: false`
      // plus the sentence below say that a difference may be an outstanding
      // cheque rather than an error. The limit is DISCLOSED rather than
      // swallowing the answer.
      clearance_tracked: clearanceStated > 0,
      clearance_stated_rows: clearanceStated,
      // UNDATED ROWS STILL FORCE NULL, and that is a different fact: it is not
      // that the comparison might be over-sensitive, it is that part of the
      // ledger was in neither side of it.
      agrees: undatedRows
        ? null
        : (clearanceStated === 0
          ? latest.cents === asOfCents
          : latest.cents === (asOfCents - outstandingCents)),
      why: undatedRows
        ? 'NOT COMPARED. ' + undatedRows + ' transaction(s) carry no date, so '
          + 'they fall on neither side of the statement and the as-of figure is '
          + 'short by ' + undatedCents + ' cents. A comparison over part of the '
          + 'ledger is not a reconciliation of it.'
        : (clearanceStated === 0
          ? 'COMPARED WITHOUT AN OUTSTANDING-ITEM ADJUSTMENT. No transaction '
            + 'records whether it has cleared the bank, so an uncleared cheque or '
            + 'a deposit in transit is indistinguishable here from a real '
            + 'difference -- and both are normal in a trust account. If this leg '
            + 'disagrees, check the outstanding items before treating it as an '
            + 'error. Record `cleared_on` (or `cleared: false`) on trust '
            + 'transactions and this leg adjusts for them.'
          : ''),
      movement_after_statement_cents: afterStatementCents,
      undated_rows: undatedRows,
      undated_cents: undatedCents,
      independence: 'external record -- compared AS OF the statement date and '
        + 'ADJUSTED for outstanding items, because an all-time ledger total, a '
        + 'point-in-time bank balance, and a bank balance that has not yet seen '
        + 'last week\'s cheques are three different quantities',
    },
  };

  // ── ROW CONSERVATION: DID EVERY ROW END UP SOMEWHERE? ──────────────────
  // The falsifiable half of leg 1. The two sums cannot see a row that both
  // passes drop; this can, because it counts rows rather than money and the
  // buckets are built by the attribution pass alone.
  //
  // THE IDENTITY: every row is either VOIDED or in exactly one client bucket,
  // and every unreadable amount is counted inside the bucket it landed in. It
  // holds today by construction, and it BREAKS the moment a future edit adds a
  // skip to one pass and not the other -- which is precisely the change leg 1
  // was supposed to catch and cannot.
  const bucketedRows = clients.reduce((s2, c) => s2 + c.rows, 0);
  const bucketedUnreadable = clients.reduce((s2, c) => s2 + c.unreadable_rows, 0);
  const conservation = {
    rows_in: rows.length,
    rows_voided: voided,
    rows_bucketed: bucketedRows,
    holds: (voided + bucketedRows) === rows.length
      && bucketedUnreadable === unreadable,
    why: 'every row is either voided or in exactly one client bucket, and '
      + 'every unreadable amount is counted inside its bucket. A row dropped '
      + 'by one pass and kept by the other breaks this and moves nothing in '
      + 'the money legs.',
  };

  // ── MONEY CONSERVATION ACROSS THE DATE SPLIT (2026-09-18) ─────────────
  // row_conservation above asks whether every ROW ended up somewhere. This asks
  // the same question of the MONEY, one axis over, and it is the defect my own
  // review of this file found:
  //
  //   asOf + afterStatement must equal the ledger total, over the same
  //   readable, non-voided rows.
  //
  // It silently did not, because an UNDATED row is excluded from BOTH sides of
  // the split. Driven before the fix: one dated $100 deposit plus one UNDATED
  // $500 deposit, with the device leg supplied so two legs compared, returned
  // status AGREES with 50000 cents reconciled by nothing -- the only cue a
  // `undated_rows: 1` nested inside a leg that said `agrees: true`.
  //
  // THE CONTROL IS WHAT MAKES IT A DEFECT RATHER THAN A LIMIT. The same $500
  // DATED after the statement also returns AGREES, and there it is honest:
  // movement_after_statement_cents reports it and a reader can see where the
  // money went. Post-statement money was ACCOUNTED; undated money was DROPPED;
  // the two were presented identically. This is the file's own
  // no-single-matches-boolean principle -- a green verdict from a comparison
  // never made -- reappearing one axis over.
  //
  // NULL WHEN THERE IS NO STATEMENT, never true: with no bank leg there is no
  // date split to conserve across, and reporting `holds: true` for an identity
  // nothing evaluated is the shape this whole file refuses.
  const moneyConservation = latest === null ? {
    holds: null,
    why: 'no usable bank statement, so there is no date split to conserve '
      + 'across. NOT an identity that held.',
  } : {
    ledger_cents: ledgerCents,
    as_of_cents: asOfCents,
    after_statement_cents: afterStatementCents,
    undated_cents: undatedCents,
    unaccounted_cents: ledgerCents - asOfCents - afterStatementCents,
    holds: (asOfCents + afterStatementCents) === ledgerCents,
    why: 'every readable, non-voided row falls on exactly one side of the '
      + 'statement date, so the two sides must sum to the ledger. An UNDATED '
      + 'row falls on neither and breaks this -- its money is in the ledger and '
      + 'in no comparison.',
  };

  const compared = Object.keys(legs).filter(
    (k) => legs[k].agrees !== null && !legs[k].structural);
  const disagreeing = compared.filter((k) => legs[k].agrees === false);

  // NO SINGLE `matches` BOOLEAN. The client's version returns one, and it is
  // TRUE when there is no bank statement -- a green verdict from a comparison
  // that was never made. `status` names what actually happened instead.
  // A BROKEN CONSERVATION IDENTITY IS A DISAGREEMENT, not a note. If rows are
  // going missing between the passes, every figure below is computed over an
  // unknown subset and none of it should read as agreement.
  // A BROKEN MONEY IDENTITY IS NOT A DISAGREEMENT AND NOT AN AGREEMENT. Nothing
  // here says the books are wrong -- it says part of the ledger was never
  // compared, which is a CANNOT-RECONCILE about a subset. Folding it into
  // DISAGREES would report a discrepancy the data does not support; folding it
  // into AGREES is the bug. It gets the third answer, and `bank_vs_ledger`
  // already refuses to return true while undated rows exist, so the two agree.
  let status;
  if (disagreeing.length || !conservation.holds) status = 'DISAGREES';
  // ── THIS LINE CANNOT FIRE TODAY, AND SAYING SO IS THE POINT ────────────
  // Driven: sabotaging it away leaves the suite GREEN. The money identity can
  // only break when a row has no readable date, and an undated row already
  // makes `bank_vs_ledger.agrees` null, which drops `compared` below two and
  // reaches the PARTIAL on the next line anyway. So the two paths coincide.
  //
  // It is KEPT AND LABELLED rather than deleted, the same treatment this file
  // gives `allocation_vs_ledger`: it states the intent, and it is the line that
  // keeps holding if a future change ever lets the identity break for a reason
  // other than an undated row -- a row filtered out of one traversal and not
  // the other, say, which is exactly the class row_conservation exists for.
  // A belt-and-braces line presented as a working check would be the
  // over-claim; a labelled one is not.
  else if (moneyConservation.holds === false) status = 'PARTIAL';
  else if (compared.length < 2) status = 'PARTIAL';
  else status = 'AGREES';

  return {
    status: status,
    row_conservation: conservation,
    money_conservation: moneyConservation,
    legs_compared: compared.length,
    legs_disagreeing: disagreeing,
    legs: legs,
    clients: clients,
    // A client whose allocation is NEGATIVE means the per-client disbursement
    // gate did not hold. It is not a reconciliation difference; it is a
    // failure of a different control, and it is named separately so it cannot
    // be read as rounding.
    negative_clients: clients.filter((c) => c.cents < 0).map((c) => c.client_id),
    unattributed_present: Object.prototype.hasOwnProperty.call(byClient, UNATTRIBUTED),
    voided_rows_excluded: voided,
    unreadable_rows: unreadable,
  };
}

module.exports = { reconcileTrustLedger, cents, UNATTRIBUTED };
