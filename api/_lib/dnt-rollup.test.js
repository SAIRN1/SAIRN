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

check('no ranking, no best-performer, no period change is emitted', () => {
  const out = rollup(base());
  const keys = Object.keys(out).sort().join(',');
  assert.strictEqual(keys, 'disclosure,locations,totals,unassigned',
    'a scoreboard is a judgement dressed as a number; this returns figures only');
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
