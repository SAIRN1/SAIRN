// api/_lib/dnt-rollup.test.js
//
// Run: node api/_lib/dnt-rollup.test.js
//
// The roll-up's job is not "produce numbers" -- it is "never produce a number
// that looks complete and is not". Every arm below is one of the four rules in
// the module header, tested in BOTH directions: the honest case must give a
// figure, and the unreadable/partial case must give null and say why. An
// assertion that only checks the happy path would pass against a function that
// silently returns 0 for everything it could not read, which is the exact
// defect this file exists to stop.
'use strict';
const assert = require('assert');
const { rollup, UNASSIGNED } = require('./dnt-rollup');
const { DEFAULT_LOCATION_ID } = require('./dnt-location');

let pass = 0, fail = 0;
function check(name, fn) {
  try { fn(); pass++; console.log('PASS ' + name); }
  catch (e) { fail++; console.log('FAIL ' + name + ' -- ' + e.message); }
}

const REGISTRY = [{ id: 'LOC-N', name: 'North office' },
                  { id: 'LOC-S', name: 'South office' }];
const METRICS = [
  { key: 'patients', resource: 'dnt_patients', kind: 'count', label: 'Patients' },
  { key: 'production', resource: 'dnt_charges', kind: 'sum', field: 'amount', label: 'Production' }
];

function base(overrides) {
  return Object.assign({
    registry: REGISTRY,
    metrics: METRICS,
    sets: {
      dnt_patients: { rows: [
        { id: 'P1', location_id: 'LOC-N' },
        { id: 'P2', location_id: 'LOC-N' },
        { id: 'P3', location_id: 'LOC-S' }
      ] },
      dnt_charges: { rows: [
        { id: 'C1', location_id: 'LOC-N', amount: 100 },
        { id: 'C2', location_id: 'LOC-S', amount: 250.5 }
      ] }
    }
  }, overrides || {});
}

function loc(out, id) {
  return out.locations.filter((l) => l.location_id === id)[0];
}

// ── THE HONEST CASE ────────────────────────────────────────────────────────
check('per-location counts and sums are what the rows say', () => {
  const out = rollup(base());
  assert.strictEqual(loc(out, 'LOC-N').metrics.patients.value, 2);
  assert.strictEqual(loc(out, 'LOC-S').metrics.patients.value, 1);
  assert.strictEqual(loc(out, 'LOC-N').metrics.production.value, 100);
  assert.strictEqual(loc(out, 'LOC-S').metrics.production.value, 250.5);
});

check('the totals line agrees with the buckets it is summed from', () => {
  const out = rollup(base());
  assert.strictEqual(out.totals.patients.value, 3);
  assert.strictEqual(out.totals.production.value, 350.5);
  assert.strictEqual(out.totals.patients.rows, 3);
});

check('a registered location with no rows reports 0, not absence', () => {
  const out = rollup(base({ sets: {
    dnt_patients: { rows: [{ id: 'P1', location_id: 'LOC-N' }] },
    dnt_charges: { rows: [] }
  } }));
  // 0 is a measurement and must be shown. An absent key would render as blank
  // and read as "no data", which is a different claim.
  assert.strictEqual(loc(out, 'LOC-S').metrics.patients.value, 0);
  assert.strictEqual(loc(out, 'LOC-S').metrics.patients.rows, 0);
});

check('a complete read discloses itself as complete', () => {
  assert.strictEqual(rollup(base()).disclosure.complete, true);
});

// ── RULE 1: UNASSIGNED IS ITS OWN BUCKET ───────────────────────────────────
check('a row with no location goes to UNASSIGNED, never to the default office', () => {
  const out = rollup(base({ sets: {
    dnt_patients: { rows: [{ id: 'P1', location_id: 'LOC-N' }, { id: 'P9' }] },
    dnt_charges: { rows: [{ id: 'C9', amount: 40 }] }
  } }));
  assert.ok(out.unassigned, 'there must be an unassigned bucket');
  assert.strictEqual(out.unassigned.metrics.patients.value, 1);
  assert.strictEqual(out.unassigned.metrics.production.value, 40);
  // The pre-stamp charge must NOT have been attributed to an office that may
  // never have taken it. With a registry present and no row carrying
  // LOC-DEFAULT, that office does not appear at all -- which is a stronger
  // statement than "appears with 0": a two-office practice is not shown a third
  // bucket it does not have. (The earlier version of this assertion expected a
  // seeded LOC-DEFAULT with 0, and that seeding turned out to be the bug -- see
  // the comment on the `touch(DEFAULT_LOCATION_ID)` guard.)
  assert.strictEqual(loc(out, DEFAULT_LOCATION_ID), undefined);
  assert.strictEqual(out.totals.production.value, 40,
    'the charge is still in the total -- suppressed from an office, not lost');
});

check('UNASSIGNED is NOT in the locations list a client would iterate', () => {
  const out = rollup(base({ sets: {
    dnt_patients: { rows: [{ id: 'P9' }] }, dnt_charges: { rows: [] } } }));
  assert.strictEqual(out.locations.filter(
    (l) => l.location_id === UNASSIGNED).length, 0);
});

check('unassigned rows make the roll-up NOT complete, and it says so', () => {
  const out = rollup(base({ sets: {
    dnt_patients: { rows: [{ id: 'P1', location_id: 'LOC-N' }, { id: 'P9' }] },
    dnt_charges: { rows: [] } } }));
  assert.strictEqual(out.disclosure.complete, false,
    'per-location figures are not a complete partition when rows carry no location');
});

check('...but the unassigned bucket is still counted in the total', () => {
  const out = rollup(base({ sets: {
    dnt_patients: { rows: [{ id: 'P1', location_id: 'LOC-N' }, { id: 'P9' }] },
    dnt_charges: { rows: [] } } }));
  assert.strictEqual(out.totals.patients.value, 2,
    'dropping unassigned rows would make the total smaller than reality');
});

// ── RULE 2: AN UNREGISTERED LOCATION IS NOT HIDDEN ─────────────────────────
check('a location_id on rows but not in the registry gets its own bucket', () => {
  const out = rollup(base({ sets: {
    dnt_patients: { rows: [{ id: 'P1', location_id: 'LOC-GONE' }] },
    dnt_charges: { rows: [] } } }));
  const g = loc(out, 'LOC-GONE');
  assert.ok(g, 'a removed office still has history and must not vanish');
  assert.strictEqual(g.registered, false);
  assert.strictEqual(g.name, null);
  assert.deepStrictEqual(out.disclosure.unregistered_location_ids, ['LOC-GONE']);
});

// ── RULE 3: AN UNREADABLE RESOURCE SUPPRESSES, IT DOES NOT ZERO ────────────
check('an unreadable resource yields null, NEVER 0', () => {
  const out = rollup(base({ sets: {
    dnt_patients: { rows: [{ id: 'P1', location_id: 'LOC-N' }] },
    dnt_charges: { unreadable: 'NOT_PROVISIONED' } } }));
  assert.strictEqual(loc(out, 'LOC-N').metrics.production.value, null,
    '0 would read as "this office produced nothing"');
  assert.strictEqual(loc(out, 'LOC-N').metrics.production.unreadable, 'NOT_PROVISIONED');
});

check('...and the TOTAL for that metric is null too, not a partial sum', () => {
  const out = rollup(base({ sets: {
    dnt_patients: { rows: [{ id: 'P1', location_id: 'LOC-N' }] },
    dnt_charges: { unreadable: 'NOT_PROVISIONED' } } }));
  assert.strictEqual(out.totals.production.value, null);
  assert.strictEqual(out.totals.patients.value, 1,
    'the readable metric must survive -- suppression is per-resource');
});

check('...and the disclosure names the resource that could not be read', () => {
  const out = rollup(base({ sets: {
    dnt_patients: { rows: [] },
    dnt_charges: { unreadable: 'NOT_PROVISIONED' } } }));
  assert.strictEqual(out.disclosure.complete, false);
  assert.strictEqual(out.disclosure.unreadable.dnt_charges, 'NOT_PROVISIONED');
});

check('a resource not supplied at all is suppressed, not silently skipped', () => {
  // The failure mode: a caller forgets to fetch one set and the roll-up
  // cheerfully reports every office as having produced nothing.
  const out = rollup(base({ sets: {
    dnt_patients: { rows: [{ id: 'P1', location_id: 'LOC-N' }] } } }));
  assert.strictEqual(loc(out, 'LOC-N').metrics.production.value, null);
  assert.strictEqual(out.totals.production.value, null);
});

// ── RULE 4: EVERY FIGURE CARRIES ITS ROW COUNT ─────────────────────────────
check('every cell carries the number of rows behind it', () => {
  const out = rollup(base());
  assert.strictEqual(loc(out, 'LOC-N').metrics.production.rows, 1);
  assert.strictEqual(loc(out, 'LOC-S').metrics.production.rows, 1);
});

// ── SHAPES AND EDGES ───────────────────────────────────────────────────────
check('location_id nested inside data is read the same as a top-level one', () => {
  const out = rollup(base({ sets: {
    dnt_patients: { rows: [{ id: 'P1', data: { location_id: 'LOC-S' } }] },
    dnt_charges: { rows: [{ id: 'C1', data: { location_id: 'LOC-S', amount: 12 } }] } } }));
  assert.strictEqual(loc(out, 'LOC-S').metrics.patients.value, 1);
  assert.strictEqual(loc(out, 'LOC-S').metrics.production.value, 12);
});

check('a blank or whitespace location_id is UNASSIGNED, not a location named " "', () => {
  const out = rollup(base({ sets: {
    dnt_patients: { rows: [{ id: 'P1', location_id: '   ' }] },
    dnt_charges: { rows: [] } } }));
  assert.strictEqual(out.unassigned.metrics.patients.value, 1);
  assert.strictEqual(out.locations.filter((l) => l.location_id.trim() === '').length, 0);
});

check('a non-numeric amount contributes 0 rather than NaN poisoning the total', () => {
  const out = rollup(base({ sets: {
    dnt_patients: { rows: [] },
    dnt_charges: { rows: [
      { id: 'C1', location_id: 'LOC-N', amount: 'not a number' },
      { id: 'C2', location_id: 'LOC-N', amount: 10 }] } } }));
  assert.strictEqual(loc(out, 'LOC-N').metrics.production.value, 10);
  // The row still counts -- it exists, it just carries no readable amount.
  assert.strictEqual(loc(out, 'LOC-N').metrics.production.rows, 2);
});

check('an empty registry still reports the implicit single practice', () => {
  const out = rollup(base({ registry: [], sets: {
    dnt_patients: { rows: [{ id: 'P1', location_id: DEFAULT_LOCATION_ID }] },
    dnt_charges: { rows: [] } } }));
  assert.strictEqual(loc(out, DEFAULT_LOCATION_ID).metrics.patients.value, 1);
  assert.strictEqual(out.disclosure.registry_size, 0);
});

// ---- THE TWO INDEPENDENT-REVIEW FINDINGS (Hank, ce7764fa, 2026-09-15) ------
// Both were real, both are fixed, and both get a regression arm here rather
// than living on in a report-only probe. Each is paired with the case that must
// still behave the old way, because a fix that changed everything would pass a
// one-directional arm just as well as a fix that changed the right thing.

check('FINDING 1: a bucket created by a LATER metric still reports the earlier ones', () => {
  // The exact reported shape: a two-office practice, every patient and
  // appointment stamped, ONE legacy charge with no location. That charge
  // creates the unassigned bucket during the LAST metric's row pass. Before the
  // fix the earlier metrics had no cell on it, and the totals loop read a
  // MISSING cell as a SUPPRESSED one -- so patients and appointments came back
  // null with `disclosure.unreadable` EMPTY.
  const out = rollup({
    registry: REGISTRY,
    metrics: [
      { key: 'patients', resource: 'dnt_patients', kind: 'count' },
      { key: 'appointments', resource: 'dnt_appts', kind: 'count' },
      { key: 'production', resource: 'dnt_charges', kind: 'sum', field: 'amount' }
    ],
    sets: {
      dnt_patients: { rows: [{ id: 'P1', location_id: 'LOC-N' },
                             { id: 'P2', location_id: 'LOC-S' }] },
      dnt_appts: { rows: [{ id: 'A1', location_id: 'LOC-N' },
                          { id: 'A2', location_id: 'LOC-S' }] },
      dnt_charges: { rows: [{ id: 'C1', location_id: 'LOC-N', amount: 300 },
                            { id: 'C0', amount: 250 }] }
    }
  });
  assert.strictEqual(out.totals.patients.value, 2, 'patients was read and must report');
  assert.strictEqual(out.totals.appointments.value, 2);
  assert.strictEqual(out.unassigned.metrics.patients.value, 0,
    'the unassigned bucket has no patients -- 0 is a measurement, null is not');
  assert.strictEqual(out.unassigned.metrics.patients.rows, 0);
  assert.deepStrictEqual(out.disclosure.unreadable, {},
    'nothing failed, so nothing may be named as unreadable');
});

check('...and the answer does not depend on the ORDER of the metric list', () => {
  // The order-dependence is what made finding 1 a defect rather than a policy.
  // A number that is a function of argument order is not a measurement.
  const sets = {
    dnt_patients: { rows: [{ id: 'P1', location_id: 'LOC-N' }] },
    dnt_charges: { rows: [{ id: 'C0', amount: 250 }] }
  };
  const A = { key: 'patients', resource: 'dnt_patients', kind: 'count' };
  const B = { key: 'production', resource: 'dnt_charges', kind: 'sum', field: 'amount' };
  const first = rollup({ registry: REGISTRY, metrics: [A, B], sets: sets });
  const second = rollup({ registry: REGISTRY, metrics: [B, A], sets: sets });
  assert.strictEqual(first.totals.patients.value, second.totals.patients.value);
  assert.strictEqual(first.totals.production.value, second.totals.production.value);
  assert.strictEqual(first.totals.patients.value, 1);
});

check('THE OTHER DIRECTION: a genuinely unreadable RESOURCE is still null, not 0', () => {
  // Finding 1's fix turns missing cells into 0. It must not have turned
  // SUPPRESSED cells into 0 as well -- that would undo rule 3 completely.
  const out = rollup(base({ sets: {
    dnt_patients: { rows: [{ id: 'P1', location_id: 'LOC-N' }] },
    dnt_charges: { unreadable: 'NOT_PROVISIONED' } } }));
  assert.strictEqual(loc(out, 'LOC-N').metrics.production.value, null);
  assert.strictEqual(out.totals.production.value, null);
});

check('FINDING 2: rows whose summed field is unreadable are COUNTED and named', () => {
  // Four charges, three with no readable amount. The arithmetic is unchanged --
  // an unreadable amount still contributes 0 rather than NaN -- but the report
  // may no longer assert it is whole.
  const out = rollup(base({ sets: {
    dnt_patients: { rows: [] },
    dnt_charges: { rows: [
      { id: 'C1', location_id: 'LOC-N', amount: 100 },
      { id: 'C2', location_id: 'LOC-N', amount: '' },
      { id: 'C3', location_id: 'LOC-N', amount: 'n/a' },
      { id: 'C4', location_id: 'LOC-N' }
    ] } } }));
  assert.strictEqual(loc(out, 'LOC-N').metrics.production.value, 100,
    'the arithmetic is deliberately unchanged');
  assert.strictEqual(loc(out, 'LOC-N').metrics.production.unreadable_rows, 3);
  assert.strictEqual(out.totals.production.unreadable_rows, 3);
  assert.strictEqual(out.disclosure.unreadable_field_rows, 3);
  assert.strictEqual(out.disclosure.complete, false,
    'a figure short by an unknown amount may not assert that it is whole');
});

check('...and a literal 0 is READABLE, so an honest zero is not counted as unreadable', () => {
  // The false-positive direction. 0 means zero; blank means nothing. Collapsing
  // them would make `complete` false on every practice that ever wrote a
  // zero-value charge, which is the alarm that gets learned and then ignored.
  const out = rollup(base({ sets: {
    dnt_patients: { rows: [] },
    dnt_charges: { rows: [
      { id: 'C1', location_id: 'LOC-N', amount: 0 },
      { id: 'C2', location_id: 'LOC-N', amount: '0.00' }
    ] } } }));
  assert.strictEqual(loc(out, 'LOC-N').metrics.production.unreadable_rows, 0);
  assert.strictEqual(out.disclosure.unreadable_field_rows, 0);
  assert.strictEqual(out.disclosure.complete, true);
});

check('a COUNT metric never reports unreadable rows -- it has no field to read', () => {
  const out = rollup(base());
  assert.strictEqual(loc(out, 'LOC-N').metrics.patients.unreadable_rows, 0);
});

check('no ranking, no best-performer, no period change is emitted', () => {
  const out = rollup(base());
  const keys = Object.keys(out).sort().join(',');
  assert.strictEqual(keys, 'disclosure,locations,totals,unassigned',
    'a scoreboard is a judgement dressed as a number; this returns figures only');
});


// ── THE UNREAD-FIELD DISCLOSURE, added 2026-09-15 with the fix ──────────────
// The arm at :199 above pins the ARITHMETIC and is deliberately unchanged: an
// unreadable amount still contributes 0 and the row is still counted. These
// pin the half that was missing -- that the roll-up SAYS so.
check('an unreadable amount is COUNTED as unread, not silently zero', () => {
  const out = rollup(base({ sets: {
    dnt_patients: { rows: [] },
    dnt_charges: { rows: [
      { id: 'C1', location_id: 'LOC-N', amount: 100 },
      { id: 'C2', location_id: 'LOC-N', amount: '' },
      { id: 'C3', location_id: 'LOC-N', amount: 'n/a' },
      { id: 'C4', location_id: 'LOC-N' }] } } }));
  const cell = loc(out, 'LOC-N').metrics.production;
  assert.strictEqual(cell.value, 100);
  assert.strictEqual(cell.rows, 4, 'every row still counts -- it exists');
  assert.strictEqual(cell.unread, 3, 'and three amounts could not be read');
});

check('...and complete goes FALSE, so a client is not told to stop looking', () => {
  const out = rollup(base({ sets: {
    dnt_patients: { rows: [] },
    dnt_charges: { rows: [
      { id: 'C1', location_id: 'LOC-N', amount: 100 },
      { id: 'C2', location_id: 'LOC-N', amount: '' }] } } }));
  assert.strictEqual(out.disclosure.complete, false);
  assert.strictEqual(out.disclosure.unread_fields, 1);
});

check('CONTROL: a clean column still reports complete with unread 0', () => {
  // Without this, "unread makes complete false" is also satisfied by a module
  // that never reports complete at all.
  const out = rollup(base({ sets: {
    dnt_patients: { rows: [] },
    dnt_charges: { rows: [
      { id: 'C1', location_id: 'LOC-N', amount: 100 },
      { id: 'C2', location_id: 'LOC-N', amount: 0 }] } } }));
  assert.strictEqual(loc(out, 'LOC-N').metrics.production.unread, 0);
  assert.strictEqual(out.disclosure.unread_fields, 0);
  assert.strictEqual(out.disclosure.complete, true);
  assert.strictEqual(loc(out, 'LOC-N').metrics.production.value, 100,
    'an explicit 0 is a measurement and is summed, not skipped');
});

check('parseFloat\'s PARTIAL PARSE no longer sneaks a plausible wrong number in', () => {
  // '12abc' was silently 12 and '1,200' was silently 1 under parseFloat. A
  // plausible wrong number is worse than an unreadable one.
  const out = rollup(base({ sets: {
    dnt_patients: { rows: [] },
    dnt_charges: { rows: [
      { id: 'C1', location_id: 'LOC-N', amount: '12abc' },
      { id: 'C2', location_id: 'LOC-N', amount: '1,200' }] } } }));
  const cell = loc(out, 'LOC-N').metrics.production;
  assert.strictEqual(cell.value, 0);
  assert.strictEqual(cell.unread, 2);
});


console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
