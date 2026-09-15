// tests/dnt_rollup_review_probe.js
//
// Run:  node tests/dnt_rollup_review_probe.js
//
// INDEPENDENT REVIEW of api/_lib/dnt-rollup.js (af5aeddf, Fourth/Ted), raised
// under the Tier A independent-review rule that 77bedb27 recorded. The brief
// named three things to look at: the owner-only gate, the arithmetic, and the
// rule that an unreadable resource yields null rather than 0 -- plus whether
// the UNASSIGNED bucket can ever be rendered as an office.
//
// ── REPORT-ONLY AND EXIT 0, DELIBERATELY ──────────────────────────────────
// Same precedent as tests/failsafe/countersign_coverage_probe.py: this is a
// review finding on somebody else's file, and turning it into a failing suite
// would block every other session's push on a defect they did not write and
// cannot land a fix for from their own claim. It PRINTS, it does not gate.
// Delete this file when the findings are closed -- it is a review artefact,
// not standing coverage.
//
// ── WHAT THE REVIEW CONFIRMED AS CORRECT, said first ──────────────────────
// The gate is genuinely owner-only: DNT_MANAGEMENT_ROLES is `{ owner: true }`
// (api/sd-data.js:10102), so "practice management only" is accurate and not a
// wider table wearing a narrow name. No row-level data leaves the branch. The
// UNASSIGNED bucket cannot be rendered as an office -- it is filtered out of
// `locations` AND hoisted to its own key, and it stays out even when a
// registry entry deliberately claims the id `__unassigned__`. The
// LOC-DEFAULT-seeding fix is right, and the reasoning recorded for it is the
// reason the phantom-bucket case does not come back.
//
// Both of the author's suites pass: dnt-rollup.test.js 19/19 and
// dnt-rollup-endpoint.test.js 12/12. Neither finding below is visible to them,
// which is why they are printed here rather than argued in prose.

'use strict';

const path = require('path');
const { rollup } = require(path.join(__dirname, '..', 'api', '_lib', 'dnt-rollup'));

let findings = 0;
function finding(n, title) {
  findings++;
  console.log('\n=== FINDING ' + n + ': ' + title + ' ===');
}
function line(k, v) { console.log('  ' + k.padEnd(16) + ' ' + v); }

// The endpoint's EXACT metric list and order, copied from api/sd-data.js's
// dnt_rollup branch. Using the real order matters: finding 1 is order-
// dependent, so a probe with its own invented order would be arguing about a
// configuration the product does not ship.
const ENDPOINT_METRICS = [
  { key: 'patients', resource: 'dnt_patients', kind: 'count', label: 'Patients' },
  { key: 'appointments', resource: 'dnt_appointments', kind: 'count', label: 'Appointments' },
  { key: 'production', resource: 'dnt_charges', kind: 'sum', field: 'amount', label: 'Production' }
];

console.log('independent review -- api/_lib/dnt-rollup.js');

// ── FINDING 1 ─────────────────────────────────────────────────────────────
finding(1, 'a metric is reported UNMEASURABLE because a LATER metric found a '
  + 'bucket it did not have');

// An ordinary two-office practice. Every patient and appointment is stamped.
// ONE charge predates stampLocation and carries no location -- which is the
// exact population rule 1 exists to handle, so this is not an exotic fixture.
const ordinary = rollup({
  registry: [{ id: 'LOC-A', name: 'Downtown' }, { id: 'LOC-B', name: 'Northside' }],
  sets: {
    dnt_patients: { rows: [{ location_id: 'LOC-A' }, { location_id: 'LOC-B' }] },
    dnt_appointments: { rows: [{ location_id: 'LOC-A' }, { location_id: 'LOC-A' }] },
    dnt_charges: { rows: [{ location_id: 'LOC-A', amount: 400 }, { amount: 150 }] }
  },
  metrics: ENDPOINT_METRICS
});

line('patients', JSON.stringify(ordinary.totals.patients));
line('appointments', JSON.stringify(ordinary.totals.appointments));
line('production', JSON.stringify(ordinary.totals.production));
line('unreadable', JSON.stringify(ordinary.disclosure.unreadable));
console.log(`
  Two patients were read and attributed. Two appointments were read and
  attributed. Both totals report null with reason "suppressed", and
  disclosure.unreadable is EMPTY -- so a client cannot even tell the owner
  which resource it supposedly failed on, because nothing failed.

  THE CAUSE. Each metric seeds a cell on every bucket that exists WHEN IT RUNS
  (dnt-rollup.js:151). A later metric's row pass can create a NEW bucket via
  touch() -- here the unassigned one, from the single legacy charge -- and that
  bucket never gets a cell for the earlier metrics. The totals loop then reads
  \`if (!cell || cell.value === null) suppressed = true\` (:178), and a MISSING
  cell is treated identically to a SUPPRESSED one.

  Missing and suppressed are not the same fact. Missing means "this office has
  no rows for this resource", which is 0. Suppressed means "we could not read
  the resource", which is null. Collapsing them is the same merge the file's
  own rule 3 forbids, running in the opposite direction.

  IT IS ORDER-DEPENDENT, which is the part that makes it a defect rather than a
  policy: the same data with the metrics listed in a different order reports
  different numbers.`);

const reordered = rollup({
  registry: [{ id: 'LOC-A', name: 'Downtown' }, { id: 'LOC-B', name: 'Northside' }],
  sets: {
    dnt_patients: { rows: [{ location_id: 'LOC-A' }, { location_id: 'LOC-B' }] },
    dnt_appointments: { rows: [{ location_id: 'LOC-A' }, { location_id: 'LOC-A' }] },
    dnt_charges: { rows: [{ location_id: 'LOC-A', amount: 400 }, { amount: 150 }] }
  },
  metrics: [ENDPOINT_METRICS[2], ENDPOINT_METRICS[1], ENDPOINT_METRICS[0]]
});
line('patients (reordered)', JSON.stringify(reordered.totals.patients));
line('production (reordered)', JSON.stringify(reordered.totals.production));
console.log(`
  DIRECTION: fail-closed. It reports null where a real number existed, so
  nobody acts on a wrong figure -- but the whole value of rule 3 is that null
  MEANS something, and a null that fires on an ordinary practice with one
  legacy row is the alarm that gets learned and then ignored.

  SUGGESTED FIX, one line: seed the new bucket's missing cells when touch()
  creates it mid-pass, or treat a missing cell in the totals loop as
  { value: 0, rows: 0 } rather than as suppression. The second is smaller and
  is correct by the file's own definition -- a bucket with no rows for a
  resource genuinely measured zero of it.`);

// ── FINDING 2 ─────────────────────────────────────────────────────────────
finding(2, 'an unreadable AMOUNT contributes 0 and the report still says '
  + 'complete: true');

const amounts = rollup({
  registry: [{ id: 'LOC-1', name: 'Main' }],
  sets: {
    dnt_patients: { rows: [] },
    dnt_appointments: { rows: [] },
    dnt_charges: {
      rows: [
        { location_id: 'LOC-1', amount: 100 },
        { location_id: 'LOC-1', amount: '' },     // field left blank on a form
        { location_id: 'LOC-1', amount: 'n/a' },  // typed, unparseable
        { location_id: 'LOC-1' }                  // absent entirely
      ]
    }
  },
  metrics: ENDPOINT_METRICS
});
line('production', JSON.stringify(amounts.totals.production));
line('complete', String(amounts.disclosure.complete));

// ── CLOSED 2026-09-15, AND THE VERDICT IS DERIVED RATHER THAN WRITTEN DOWN ──
// The prose below describes the behaviour as it was WHEN THIS PROBE WAS
// WRITTEN, and it is kept because it is the argument that got the fix made.
// But a narrative that outlives the defect it describes starts contradicting
// the numbers printed two lines above it -- the same shape as a tool printing
// a hardcoded "the gap is open" under a line reading "0 of 6". So the closure
// is MEASURED here, from this run's own output, and this block says which of
// the two a reader is looking at.
const f2Closed = amounts.disclosure.complete === false
  && amounts.totals.production
  && amounts.totals.production.unread > 0;
if (f2Closed) {
  findings -= 1;
  console.log(`
  >> CLOSED. Measured on THIS RUN: the total now carries unread=${amounts.totals.production.unread}
  >> and complete is false. The fix was the one suggested below -- the
  >> arithmetic is unchanged and dnt-rollup.test.js:199 still passes; what
  >> changed is that the unread fields are NAMED and complete stops asserting
  >> wholeness. The narrative that follows is the original finding, kept as the
  >> record of why, and it no longer describes current behaviour.`);
}
console.log(`
  THIS ONE IS A DISAGREEMENT, NOT AN OVERSIGHT, and it has to be raised as
  such: dnt-rollup.test.js:199 has an arm named "a non-numeric amount
  contributes 0 rather than NaN poisoning the total" asserting exactly this
  behaviour. It was considered and chosen.

  The objection is narrow. The file's rule 3 says, about an unreadable
  resource: "NEVER 0. Zero is a measurement." Three of these four charges have
  no readable amount, and the report answers $100 across 4 rows with
  disclosure.complete = TRUE -- an authoritative figure, short by an unknown
  amount, positively asserting that it is whole. That is rule 3's own sentence,
  one level down, at the FIELD rather than the RESOURCE.

  The row count is a real mitigation: 4 rows against $100 is visible to
  somebody who looks. But nothing NAMES it, and \`complete: true\` tells a
  client not to look.

  SUGGESTED FIX, also small and NOT a behaviour change to the arithmetic: count
  the rows whose summed field could not be read, report them per metric, and
  make disclosure.complete false when that count is non-zero. The existing arm
  keeps passing -- the total stays 10, the rows stay 2 -- and the report stops
  claiming completeness it has not got.`);

// ── NOT FINDINGS, recorded so the next reviewer does not re-derive them ────
console.log('\n=== CHECKED AND CORRECT ===');
console.log(`  * the gate is owner-only in fact, not just in wording
  * no row-level data leaves the branch -- counts and sums only
  * UNASSIGNED is never rendered as an office, and stays out even when a
    registry entry claims the id '__unassigned__'
  * an unreadable SETTINGS table refuses the whole report with 503 rather than
    reporting every office as unregistered
  * summing buckets rather than re-walking rows means the totals line cannot
    disagree with the per-office figures
  * one COSMETIC note, not raised as a finding: disclosure.registry_size counts
    a registry entry that will never render as an office (the '__unassigned__'
    case above reports 2). Contrived input, no consequence.`);

console.log('\n' + findings + ' finding(s). Report-only: exit 0 by design.');
process.exit(0);
