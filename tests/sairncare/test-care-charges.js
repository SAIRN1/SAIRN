// Isolated test of api/_lib/care-charges.js (Phase 3 item 2).
// PURE engine, run against the REAL module.
'use strict';
const path = require('path');
const c = require(path.join(__dirname, '..', '..', 'api/_lib/care-charges.js'));

let pass = 0, fail = 0;
function check(n, f) { try { f(); pass++; console.log('PASS ' + n); } catch (e) { fail++; console.log('FAIL ' + n + ' -- ' + e.message); } }
function assertEq(a, b, msg) {
  if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error((msg || 'mismatch') + ': expected ' + JSON.stringify(b) + ' got ' + JSON.stringify(a));
}
function assertTrue(v, msg) { if (!v) throw new Error(msg || 'expected truthy'); }

const RATES = { med_admin_rate: 2.5, activity_rate: 10 };
function ev(id, type, date, extra) {
  return Object.assign({ id: id, type: type, resident_id: 'RES-1', date: date }, extra || {});
}

check('a charge is produced only from a real documented event, and carries its id', () => {
  const r = c.deriveCharges({
    month: '2026-08', resident_id: 'RES-1', rate_card: RATES,
    events: [ev('E1', 'medication_administration', '2026-08-03')]
  });
  assertEq(r.ok, true);
  assertEq(r.lines.length, 1);
  assertEq(r.lines[0].event_id, 'E1', 'every line must be walkable back to its source document');
  assertEq(r.lines[0].amount, 2.5);
});

check('quantities multiply the unit rate', () => {
  const r = c.deriveCharges({
    month: '2026-08', resident_id: 'RES-1', rate_card: RATES,
    events: [ev('E1', 'activity_attendance', '2026-08-03', { quantity: 3 })]
  });
  assertEq(r.lines[0].amount, 30);
  assertEq(r.lines[0].unit_rate, 10);
});

check('an UNPRICED documented service is surfaced, never billed at zero and never dropped', () => {
  const r = c.deriveCharges({
    month: '2026-08', resident_id: 'RES-1', rate_card: RATES,
    events: [ev('E2', 'adl_assessment', '2026-08-05')]
  });
  assertEq(r.lines.length, 0, 'must not create a zero-dollar line');
  assertEq(r.unpriced.length, 1);
  assertEq(r.unpriced[0].event_id, 'E2');
  assertTrue(/not being billed until a rate is set/.test(r.unpriced[0].reason));
  assertEq(r.total, 0);
});

check('the reconciliation contract states the gap as a number', () => {
  const r = c.deriveCharges({
    month: '2026-08', resident_id: 'RES-1', rate_card: RATES,
    events: [ev('E1', 'medication_administration', '2026-08-03'), ev('E2', 'adl_assessment', '2026-08-05')]
  });
  assertEq(r.reconciliation, {
    documented_chargeable_events: 2, billed_events: 1, unbilled_events: 1, fully_reconciled: false
  });
});

check('fully_reconciled is true only when nothing documented went unbilled', () => {
  const r = c.deriveCharges({
    month: '2026-08', resident_id: 'RES-1', rate_card: RATES,
    events: [ev('E1', 'medication_administration', '2026-08-03')]
  });
  assertEq(r.reconciliation.fully_reconciled, true);
});

check('non-billable documentation is classified, not treated as an error or a charge', () => {
  const r = c.deriveCharges({
    month: '2026-08', resident_id: 'RES-1', rate_card: RATES,
    events: [ev('E9', 'incident_report', '2026-08-06')]
  });
  assertEq(r.lines.length, 0);
  assertEq(r.unpriced.length, 0);
  assertEq(r.unbillable_event_types.length, 1);
  assertEq(r.reconciliation.documented_chargeable_events, 0, 'a non-chargeable document is not a chargeable event');
});

check('another resident’s documentation never lands on this resident’s charges', () => {
  const r = c.deriveCharges({
    month: '2026-08', resident_id: 'RES-1', rate_card: RATES,
    events: [Object.assign(ev('E1', 'medication_administration', '2026-08-03'), { resident_id: 'RES-2' })]
  });
  assertEq(r.lines.length, 0);
  assertEq(r.total, 0);
});

check('another month’s documentation never lands on this month', () => {
  const r = c.deriveCharges({
    month: '2026-08', resident_id: 'RES-1', rate_card: RATES,
    events: [ev('E1', 'medication_administration', '2026-07-31'), ev('E2', 'medication_administration', '2026-09-01')]
  });
  assertEq(r.lines.length, 0);
});

check('a zero or negative documented quantity is refused, not billed', () => {
  const r = c.deriveCharges({
    month: '2026-08', resident_id: 'RES-1', rate_card: RATES,
    events: [ev('E1', 'activity_attendance', '2026-08-03', { quantity: 0 }), ev('E2', 'activity_attendance', '2026-08-04', { quantity: -2 })]
  });
  assertEq(r.lines.length, 0);
  assertEq(r.unpriced.length, 2);
});

check('lines come back in date order', () => {
  const r = c.deriveCharges({
    month: '2026-08', resident_id: 'RES-1', rate_card: RATES,
    events: [ev('E3', 'medication_administration', '2026-08-20'), ev('E1', 'medication_administration', '2026-08-02')]
  });
  assertEq(r.lines.map((l) => l.event_id), ['E1', 'E3']);
});

check('a bad month and a missing resident are refused', () => {
  assertEq(c.deriveCharges({ month: 'August', resident_id: 'RES-1' }).error.code, 'BAD_MONTH');
  assertEq(c.deriveCharges({ month: '2026-08' }).error.code, 'NO_RESIDENT');
});

check('totals round to cents rather than carrying float noise', () => {
  const r = c.deriveCharges({
    month: '2026-08', resident_id: 'RES-1', rate_card: { med_admin_rate: 0.1 },
    events: [ev('A', 'medication_administration', '2026-08-01'), ev('B', 'medication_administration', '2026-08-02'), ev('C', 'medication_administration', '2026-08-03')]
  });
  assertEq(r.total, 0.3, '0.1 x 3 must be 0.3, not 0.30000000000000004');
});

// ── reconciliation against an existing invoice ───────────────────────────
check('reconciling shows exactly what a regenerate added, removed and changed', () => {
  const derived = c.deriveCharges({
    month: '2026-08', resident_id: 'RES-1', rate_card: RATES,
    events: [ev('E1', 'medication_administration', '2026-08-01'), ev('E2', 'activity_attendance', '2026-08-02')]
  });
  const prior = [
    { event_id: 'E1', amount: 2.5 },
    { event_id: 'E_GONE', amount: 7 }
  ];
  const rec = c.reconcileAgainstInvoice(derived, prior);
  assertEq(rec.added.map((l) => l.event_id), ['E2']);
  assertEq(rec.removed.map((l) => l.event_id), ['E_GONE']);
  assertEq(rec.unchanged_count, 1);
  assertEq(rec.net_change, 3, '+10 activity, -7 removed');
});

check('a changed amount for the same event is reported as changed, not as add+remove', () => {
  const derived = c.deriveCharges({
    month: '2026-08', resident_id: 'RES-1', rate_card: { med_admin_rate: 5 },
    events: [ev('E1', 'medication_administration', '2026-08-01')]
  });
  const rec = c.reconcileAgainstInvoice(derived, [{ event_id: 'E1', amount: 2.5 }]);
  assertEq(rec.changed, [{ event_id: 'E1', from: 2.5, to: 5 }]);
  assertEq(rec.added.length, 0);
  assertEq(rec.removed.length, 0);
  assertEq(rec.net_change, 2.5);
});


// ── SAME-DAY ORDER IS DETERMINISTIC, 2026-09-22 ────────────────────────────
// The sort was on `date` alone. Array.prototype.sort is stable, so same-day
// rows kept INSERTION order -- the order the three event sources were
// concatenated in, and within each source the order the server returned rows.
// Two of those three reads carried no `order=` clause, so two identical
// regenerations could list one day's doses differently on a table whose first
// column is Date.
//
// THE MONEY WAS NEVER WRONG and these arms say so explicitly: the total is a
// sum and reconcileAgainstInvoice() keys on event_id, so the regenerate-diff
// was order-independent throughout. What moved is the order a biller reads.
check('same-day lines are ordered deterministically, not by arrival', () => {
  const forward = c.deriveCharges({
    month: '2026-08', resident_id: 'RES-1', rate_card: RATES,
    events: [ev('E3', 'medication_administration', '2026-08-03'),
      ev('E1', 'medication_administration', '2026-08-03'),
      ev('E2', 'medication_administration', '2026-08-03')]
  });
  const reversed = c.deriveCharges({
    month: '2026-08', resident_id: 'RES-1', rate_card: RATES,
    events: [ev('E2', 'medication_administration', '2026-08-03'),
      ev('E1', 'medication_administration', '2026-08-03'),
      ev('E3', 'medication_administration', '2026-08-03')]
  });
  assertEq(forward.lines.map((l) => l.event_id), ['E1', 'E2', 'E3'],
    'same-day rows must not depend on the order the server returned them');
  assertEq(reversed.lines.map((l) => l.event_id), forward.lines.map((l) => l.event_id),
    'two identical regenerations must produce the identical row order');
});

check('...and date still beats the tiebreak, so the table is chronological', () => {
  const r = c.deriveCharges({
    month: '2026-08', resident_id: 'RES-1', rate_card: RATES,
    events: [ev('A9', 'medication_administration', '2026-08-20'),
      ev('Z1', 'medication_administration', '2026-08-02')]
  });
  assertEq(r.lines.map((l) => l.date), ['2026-08-02', '2026-08-20'],
    'the id tiebreak must never outrank the date -- Z1 is earlier and sorts first');
});

check('the UNPRICED list is ordered too -- it is rendered with dates as well', () => {
  // No rate for an activity, so both land in `unpriced` rather than in lines.
  const r = c.deriveCharges({
    month: '2026-08', resident_id: 'RES-1', rate_card: { med_admin_rate: 2.5 },
    events: [ev('U2', 'activity_attendance', '2026-08-09'),
      ev('U1', 'activity_attendance', '2026-08-04')]
  });
  assertEq(r.unpriced.length, 2);
  assertEq(r.unpriced.map((u) => u.event_id), ['U1', 'U2'],
    'an unordered list of what a home is NOT being paid for is the one this '
    + 'view exists to make readable');
});

check('THE PAIRED NEGATIVE: ordering changed no money and no diff', () => {
  const events = [ev('E3', 'medication_administration', '2026-08-03'),
    ev('E1', 'medication_administration', '2026-08-03')];
  const a = c.deriveCharges({ month: '2026-08', resident_id: 'RES-1', rate_card: RATES, events: events });
  const b = c.deriveCharges({
    month: '2026-08', resident_id: 'RES-1', rate_card: RATES,
    events: events.slice().reverse()
  });
  assertEq(a.total, b.total, 'the total is a sum and was never order-sensitive');
  assertEq(a.total, 5);
  // The diff keys on event_id, so a reordered derivation reconciles as
  // entirely unchanged against the other one's lines.
  const rec = c.reconcileAgainstInvoice(a, b.lines);
  assertEq(rec.added.length, 0);
  assertEq(rec.removed.length, 0);
  assertEq(rec.changed.length, 0);
  assertEq(rec.net_change, 0,
    'if reordering could move the diff, the audit trail this endpoint exists '
    + 'to produce would have been wrong -- it was not, and that is the half '
    + 'of this finding that was overstated before it was checked');
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
