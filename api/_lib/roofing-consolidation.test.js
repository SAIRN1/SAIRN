// api/_lib/roofing-consolidation.test.js
// Plain node:assert tests -- no framework, matching api/'s zero-npm-dependency
// convention. Run: node api/_lib/roofing-consolidation.test.js
//
// The central test is the INVARIANT: moving a branch between entities must
// change the buckets and must NOT change the grand total. If that ever fails,
// attribution has been stamped somewhere it should not be.

const assert = require('assert');
const c = require('./roofing-consolidation');

let passed = 0;
function test(name, fn) {
  try {
    fn();
    passed++;
    console.log('  ok - ' + name);
  } catch (e) {
    console.error('  FAIL - ' + name + '\n      ' + e.message);
    process.exitCode = 1;
  }
}

const entities = [
  { entity_id: 'ENT-A', legal_name: 'Alpha Roofing LLC' },
  { entity_id: 'ENT-B', legal_name: 'Beta Exteriors Inc' }
];
const locations = [
  { location_id: 'LOC-CBUS', name: 'Columbus', entity_id: 'ENT-A' },
  { location_id: 'LOC-DAY', name: 'Dayton', entity_id: 'ENT-A' },
  { location_id: 'LOC-CIN', name: 'Cincinnati', entity_id: 'ENT-B' },
  { location_id: 'LOC-TOL', name: 'Toledo', entity_id: null }        // never assigned
];
const rows = [
  { location_id: 'LOC-CBUS', total: 10000, paid: 10000, balance: 0 },
  { location_id: 'LOC-DAY', total: 5000, paid: 2000, balance: 3000 },
  { location_id: 'LOC-CIN', total: 8000, paid: 0, balance: 8000 },
  { location_id: 'LOC-TOL', total: 2000, paid: 1000, balance: 1000 },
  { location_id: 'LOC-DEFAULT', total: 1500, paid: 0, balance: 1500 }  // no such location row
];
const base = { entities: entities, locations: locations, rows: rows };

// ── the rollup ────────────────────────────────────────────────────────────

test('branches roll up into the entity their location currently names', () => {
  const r = c.consolidate(base);
  const a = r.entities.filter(x => x.entity_id === 'ENT-A')[0];
  const b = r.entities.filter(x => x.entity_id === 'ENT-B')[0];
  assert.strictEqual(a.total, 15000);
  assert.strictEqual(b.total, 8000);
  assert.deepStrictEqual(a.location_ids.sort(), ['LOC-CBUS', 'LOC-DAY']);
});

test('the two UNASSIGNED reasons are kept apart -- they need different fixes', () => {
  const r = c.consolidate(base);
  const noEnt = r.unassigned.filter(x => x.kind === 'unassigned')[0];
  const noLoc = r.unassigned.filter(x => x.kind === 'unknown_location')[0];
  assert.strictEqual(noEnt.total, 2000, 'a branch on file with no entity');
  assert.strictEqual(noLoc.total, 1500, 'a row naming a location that does not exist, incl. LOC-DEFAULT');
});

test('unassigned buckets are NOT inside `entities`, so a caller cannot total the wrong list', () => {
  const r = c.consolidate(base);
  assert.strictEqual(r.entities.length, 2);
  assert.strictEqual(r.entities.reduce((s, x) => s + x.total, 0), 23000);
  assert.strictEqual(r.grand_total, 26500, 'the whole book includes both unassigned buckets');
});

test('an entity with no invoices still appears, with the branches it owns', () => {
  const r = c.consolidate({ entities: entities, locations: locations, rows: [] });
  const b = r.entities.filter(x => x.entity_id === 'ENT-B')[0];
  assert.strictEqual(b.total, 0);
  assert.deepStrictEqual(b.location_ids, ['LOC-CIN'], 'it must not vanish from the consolidation');
});

// ── THE INVARIANT ─────────────────────────────────────────────────────────

test('MOVING A BRANCH MOVES ITS WHOLE HISTORY and leaves the grand total alone', () => {
  const before = c.consolidate(base);
  const moved = locations.map(l => l.location_id === 'LOC-DAY' ? Object.assign({}, l, { entity_id: 'ENT-B' }) : l);
  const after = c.consolidate({ entities: entities, locations: moved, rows: rows });

  assert.strictEqual(before.entities.filter(x => x.entity_id === 'ENT-A')[0].total, 15000);
  assert.strictEqual(after.entities.filter(x => x.entity_id === 'ENT-A')[0].total, 10000);
  assert.strictEqual(after.entities.filter(x => x.entity_id === 'ENT-B')[0].total, 13000,
    'Dayton s ENTIRE history moved, not just invoices written after the move');
  assert.strictEqual(before.grand_total, after.grand_total,
    'if this ever fails, attribution has been stamped somewhere it should not be');
});

test('moving a branch OUT of every entity lands it in Unassigned, total still unchanged', () => {
  const before = c.consolidate(base);
  const moved = locations.map(l => l.location_id === 'LOC-CIN' ? Object.assign({}, l, { entity_id: null }) : l);
  const after = c.consolidate({ entities: entities, locations: moved, rows: rows });
  assert.strictEqual(after.entities.filter(x => x.entity_id === 'ENT-B')[0].total, 0);
  assert.strictEqual(after.unassigned.filter(x => x.kind === 'unassigned')[0].total, 10000);
  assert.strictEqual(before.grand_total, after.grand_total);
});

test('every result carries reconciles, so the invariant is checkable not assumed', () => {
  const r = c.consolidate(base);
  assert.strictEqual(r.reconciles, true);
  assert.strictEqual(r.input_total, r.grand_total);
});

// ── things that must not be swallowed ─────────────────────────────────────

test('a row with an unreadable total is COUNTED and the shortfall is stated', () => {
  const r = c.consolidate({ entities: entities, locations: locations,
    rows: rows.concat([{ location_id: 'LOC-CBUS', total: 'lots' }]) });
  assert.strictEqual(r.rows_unreadable, 1);
  assert.ok(/short by them/.test(r.problems.join(' ')));
  assert.strictEqual(r.grand_total, 26500, 'and it is in no bucket, rather than counted as zero silently');
});

test('a location naming an entity that is NOT on file is flagged, not quietly unassigned', () => {
  const r = c.consolidate({ entities: entities,
    locations: locations.concat([{ location_id: 'LOC-GHOST', name: 'Ghost', entity_id: 'ENT-NOPE' }]),
    rows: rows.concat([{ location_id: 'LOC-GHOST', total: 900, paid: 0, balance: 900 }]) });
  assert.ok(/names entity "ENT-NOPE", which is not on file/.test(r.problems.join(' ')));
  assert.strictEqual(r.unassigned.filter(x => x.kind === 'unassigned')[0].total, 2900);
  assert.strictEqual(r.reconciles, true);
});

test('paid and balance roll up beside the total', () => {
  const r = c.consolidate(base);
  const a = r.entities.filter(x => x.entity_id === 'ENT-A')[0];
  assert.strictEqual(a.paid, 12000);
  assert.strictEqual(a.balance, 3000);
  assert.strictEqual(r.grand_balance, 13500);
});

test('a missing balance is derived from total minus paid rather than treated as zero', () => {
  const r = c.consolidate({ entities: entities, locations: locations,
    rows: [{ location_id: 'LOC-CBUS', total: 1000, paid: 400 }] });
  assert.strictEqual(r.entities.filter(x => x.entity_id === 'ENT-A')[0].balance, 600);
});

// ── the preview ───────────────────────────────────────────────────────────

test('previewMove says what moves and proves the book does not change size', () => {
  const p = c.previewMove(Object.assign({}, base, { location_id: 'LOC-DAY', to_entity_id: 'ENT-B' }));
  assert.strictEqual(p.from_entity_id, 'ENT-A');
  assert.strictEqual(p.to_entity_id, 'ENT-B');
  assert.strictEqual(p.amount_moving, 5000);
  assert.strictEqual(p.from_total_before, 15000);
  assert.strictEqual(p.to_total_after, 13000);
  assert.strictEqual(p.grand_total_unchanged, true);
});

test('previewMove refuses without a location rather than previewing nothing', () => {
  const p = c.previewMove(base);
  assert.strictEqual(p.ok, false);
  assert.strictEqual(p.error.code, 'NO_LOCATION');
});

console.log(passed + ' passed');
