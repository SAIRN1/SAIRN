// api/_lib/sc-denial-reconcile.js
//
// SAIRNcode denial reconciliation: does the hand-typed aggregate agree with the
// events actually logged?
//
// ── WHY THIS EXISTS ────────────────────────────────────────────────────────
// docs/2026-09-26-sairncode-rcm-panel-depth.md measured the eight enterprise RCM
// panels. `claims` scored 9/9; `prebill`, `hcc`, `drg`, `rac`, `denial`, `ar` and
// `revenue` each scored 6/9 and each was missing the same three DEEP signals --
// the resource is not named in executable endpoint code, it has no verb beyond
// generic CRUD, and therefore nothing to send. Every mention of `sc_denial`,
// `sc_ar` and `sc_revenue` in api/sd-data.js is inside a COMMENT: code-line count
// `sc_claims` 4, the other seven 0. All seven ride the generic SC_RESOURCES
// handler and have no per-resource rule, by construction.
//
// `denial` was named as the strongest of the seven to deepen first, for reasons
// that were measured rather than preferred: the most test attention of the seven
// (11 files against 3 each for prebill/hcc/drg/rac), a purpose-built second
// resource beside it, and a client function already computing real counts from it.
//
// ── WHAT IT COMPUTES, AND WHAT IT REFUSES TO ──────────────────────────────
// SAIRNcode stores denials twice, deliberately, and sairncode.html says why:
//
//   sc_denial        {id, code, cause, count, amount, status}
//                    an AGGREGATE -- one row per denial CODE with a MANUALLY
//                    ENTERED count, no payer and no date.
//   sc_denial_events {id, code, payer, reason, amount, date, specialty}
//                    one row per actual denial EVENT.
//
// The app's own comment: sc_denial "cannot answer 'which payer denies which codes
// most' because it never recorded payer or individual occurrences. sc_denial_events
// is the real fix."
//
// SO THE TWO CAN DISAGREE AND NOTHING CHECKS. A coder types count 12 against code
// 99213 while three events are logged; the dashboard reads the aggregate and the
// pattern panel reads the events, and both are presented as fact. That is the
// `law_trust_reconcile` shape -- two recorded sources for one quantity -- and it
// gets the same treatment: REPORT THE DISAGREEMENT, PICK NO SIDE.
//
// IT INVENTS NOTHING. Every figure returned is a count or a sum of rows the
// practice itself recorded. There is no predicted denial probability here, for the
// reason sairncode.html already states above scPreSubmissionRisk(): no calibrated
// model and no labelled outcome set exist, so a percentage would be a number with
// nothing behind it. This module produces counts and differences only.
//
// ── THE THIRD STATE IS NOT ZERO ────────────────────────────────────────────
// A code whose aggregate `count` is absent, non-numeric or negative is
// `no_aggregate_count` -- NOT a count of 0, and NOT "the events win". A missing
// number and a number that says none are different facts and only one of them was
// entered by a person.
//
// ── MONEY IS COMPARED IN CENTS ─────────────────────────────────────────────
// 0.1 + 0.2 !== 0.3, and an amount assembled from several rows will not equal a
// hand-typed total under `===` even when a human would call them the same. Both
// sides are rounded to whole cents and compared as integers, and the difference is
// returned in cents as well as in dollars so a caller never has to re-derive it
// from two floats.
//
// ── NOT WIRED, AND THAT IS DECLARED RATHER THAN DISCOVERED ─────────────────
// There is NO caller. api/sd-data.js is held by hank-queue13 (the
// alf_compliance_rules evaluate branch), so the one dispatch line that would make
// this reachable is deliberately not added here. THAT LEAVES AN ENGINE WITH NO
// CALLER, WHICH IS THE SAIRNmechanical G3 DEFECT -- engine, endpoint, registry and
// ten test arms present, and no client ever sending the action, with a panel
// subtitle claiming the computation anyway. It is recorded here, in the suite, and
// in a Tier A obligation precisely so it is not rediscovered as a finding.
//
// TO WIRE IT, three things and no more:
//   1. api/_resources/sairncode.js -- add 'reconcile' to sc_denial's extraActions
//      (the allowlist runs BEFORE any resource branch, so an undeclared handler is
//      unreachable; that is how the therapy_accumulator verb first shipped).
//   2. api/sd-data.js -- a branch on action === 'reconcile' && resource ===
//      'sc_denial' that reads both tables for the licence and returns
//      reconcile(aggregates, events).
//   3. sairncode.html -- send it. A declared verb nobody sends is the same defect
//      one layer along.
'use strict';

/** Whole cents from a dollar amount, or null if there is no usable number. */
function cents(v) {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  if (!isFinite(n)) return null;
  return Math.round(n * 100);
}

/** A non-negative integer count, or null. `null` means NOT ENTERED, never zero. */
function countOf(v) {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  if (!isFinite(n) || Math.floor(n) !== n || n < 0) return null;
  return n;
}

/** Codes are compared case-insensitively and trimmed; CPT/HCPCS are not
 *  case-bearing and '99213 ' typed with a trailing space is the same code. An
 *  empty code is its own bucket rather than being dropped -- a denial logged
 *  against no code is a data problem somebody should see. */
function codeKey(c) {
  return String(c === null || c === undefined ? '' : c).trim().toUpperCase();
}

/**
 * reconcile(aggregates, events) -> { rows, totals, limits }
 *
 * `rows` is one entry per code appearing in either store, sorted by the largest
 * absolute count difference first, so the worst disagreement is at the top.
 * Nothing is filtered out: a code that agrees is returned with state 'agrees'
 * because a caller showing only problems cannot report a denominator.
 */
function reconcile(aggregates, events) {
  const aggs = Array.isArray(aggregates) ? aggregates : [];
  const evs = Array.isArray(events) ? events : [];

  const byCode = new Map();
  const touch = (k) => {
    if (!byCode.has(k)) {
      byCode.set(k, {
        code: k,
        aggregate_rows: 0,
        aggregate_count: null,
        aggregate_cents: null,
        event_count: 0,
        event_cents: 0,
        causes: [],
      });
    }
    return byCode.get(k);
  };

  // ── AGGREGATE SIDE. More than one aggregate row per code is possible -- the
  // client appends and nothing dedupes -- so they are SUMMED and the row count
  // is reported. A caller that saw only the summed figure could not tell one row
  // of 12 from twelve rows of 1, and those are different data-entry stories.
  aggs.forEach((a) => {
    if (!a || typeof a !== 'object') return;
    const r = touch(codeKey(a.code));
    r.aggregate_rows += 1;
    const c = countOf(a.count);
    if (c !== null) r.aggregate_count = (r.aggregate_count || 0) + c;
    const m = cents(a.amount);
    if (m !== null) r.aggregate_cents = (r.aggregate_cents || 0) + m;
    const cause = String(a.cause === null || a.cause === undefined ? '' : a.cause).trim();
    if (cause && cause !== '—' && r.causes.indexOf(cause) === -1) r.causes.push(cause);
  });

  // ── EVENT SIDE. One row IS one denial, so the count is the row count and is
  // never read off a field. An event with an unusable amount still counts as an
  // occurrence -- dropping it would make the event count disagree with the
  // number of rows a user can see in the table.
  let events_missing_amount = 0;
  evs.forEach((e) => {
    if (!e || typeof e !== 'object') return;
    const r = touch(codeKey(e.code));
    r.event_count += 1;
    const m = cents(e.amount);
    if (m === null) events_missing_amount += 1;
    else r.event_cents += m;
  });

  const rows = Array.from(byCode.values()).map((r) => {
    let state, reason;
    if (r.aggregate_rows === 0) {
      state = 'events_only';
      reason = r.event_count + ' event(s) logged and no aggregate row for this code. '
        + 'The aggregate table is what the dashboard reads.';
    } else if (r.aggregate_count === null) {
      state = 'no_aggregate_count';
      reason = 'The aggregate row carries no usable count, so the two cannot be '
        + 'compared. This is NOT a count of zero -- nobody has entered one.';
    } else if (r.event_count === 0) {
      state = 'aggregate_only';
      reason = 'An aggregate count of ' + r.aggregate_count + ' with no logged events. '
        + 'Nothing here says the count is wrong; it says nothing supports it.';
    } else if (r.aggregate_count === r.event_count) {
      state = 'agrees';
      reason = 'The aggregate count and the number of logged events are both '
        + r.event_count + '.';
    } else if (r.aggregate_count > r.event_count) {
      state = 'aggregate_higher';
      reason = 'The aggregate says ' + r.aggregate_count + ' and '
        + r.event_count + ' event(s) are logged. Either events are unlogged or the '
        + 'aggregate is overstated; this does not decide which.';
    } else {
      state = 'events_higher';
      reason = 'The aggregate says ' + r.aggregate_count + ' and '
        + r.event_count + ' event(s) are logged. The aggregate is behind the log, '
        + 'or it was never updated; this does not decide which.';
    }
    const cd = (r.aggregate_count === null) ? null : r.event_count - r.aggregate_count;
    const md = (r.aggregate_cents === null) ? null : r.event_cents - r.aggregate_cents;
    return {
      code: r.code,
      state: state,
      reason: reason,
      aggregate_rows: r.aggregate_rows,
      aggregate_count: r.aggregate_count,
      event_count: r.event_count,
      count_difference: cd,
      aggregate_cents: r.aggregate_cents,
      event_cents: r.event_cents,
      // Returned in cents AND dollars so no caller re-derives it from two floats.
      amount_difference_cents: md,
      amount_difference: md === null ? null : md / 100,
      causes: r.causes,
    };
  });

  // Worst disagreement first; a null difference sorts with the unknowns rather
  // than as zero, because could-not-compare is not agreement.
  rows.sort((a, b) => {
    const ax = a.count_difference === null ? -1 : Math.abs(a.count_difference);
    const bx = b.count_difference === null ? -1 : Math.abs(b.count_difference);
    if (bx !== ax) return bx - ax;
    return a.code < b.code ? -1 : a.code > b.code ? 1 : 0;
  });

  const tally = (s) => rows.filter((r) => r.state === s).length;
  return {
    rows: rows,
    totals: {
      codes: rows.length,
      agrees: tally('agrees'),
      aggregate_higher: tally('aggregate_higher'),
      events_higher: tally('events_higher'),
      aggregate_only: tally('aggregate_only'),
      events_only: tally('events_only'),
      // COUNTED SEPARATELY AND NEVER ADDED TO `agrees`. A code that cannot be
      // compared is not a code that matches.
      not_comparable: tally('no_aggregate_count'),
      aggregate_rows: aggs.length,
      event_rows: evs.length,
      events_missing_amount: events_missing_amount,
    },
    limits: [
      'It picks no side. Neither store is treated as authoritative, because both '
      + 'are entered by hand and the app has never said which governs.',
      'The aggregate carries no payer and no date, so a disagreement cannot be '
      + 'attributed to a payer or a period. That is a property of sc_denial, not '
      + 'of this comparison.',
      'no_aggregate_count is a THIRD STATE and is never folded into `agrees`. A '
      + 'missing count and a count of zero are different facts.',
      'Amounts are compared in whole cents. A sub-cent difference is invisible '
      + 'here and that is deliberate; floats assembled from several rows do not '
      + 'equal a typed total under strict equality.',
      'It says nothing about whether any denial was correct, appealable or timely. '
      + 'No deadline, no payer rule and no probability is computed anywhere in '
      + 'this module.',
    ],
  };
}

module.exports = { reconcile, cents, countOf, codeKey };
