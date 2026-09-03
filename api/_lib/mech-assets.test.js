// api/_lib/mech-assets.test.js
// Run: node api/_lib/mech-assets.test.js
//
// SAIRNmechanical's site asset registry -- capability #2 on the 2026-08-27
// competitive research's prioritised list, "prerequisite for A3, A5, A7, B8,
// G13. Table stakes -- every incumbent has it."
//
// The assertion that carries the most weight:
//
//   AN UNRECORDED REFRIGERANT CHARGE IS NEVER "BELOW THRESHOLD". EPA keys its
//   leak-repair provisions to a full charge at or above 50 lb (40 CFR 82.157).
//   Telling a shop a machine is under that when nobody ever weighed it is a
//   compliance claim with no evidence -- the same shape as the EPA 608 mistake
//   the credential engine was built to avoid: an answer that reads as
//   clearance.
//
//   And the engine issues no compliance VERDICT at all. Leak-rate percentages
//   differ by appliance category and the HFC picture has moved; encoding one
//   would be this app asserting current federal law from a hardcoded number.

'use strict';
const assert = require('assert');
const m = require('./mech-assets');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

const TODAY = '2026-09-02';
const asset = (o) => Object.assign({ asset_id: 'A1', asset_type: 'rtu' }, o);

// ---------------------------------------------------------------------------
section('THE ONE THAT MATTERS: an unweighed unit is not a cleared unit');

test('no recorded charge -> unknown_charge, NEVER below', () => {
  const r = m.refrigerantScope(asset({ refrigerant_type: 'r410a' }));
  assert.strictEqual(r.scope, 'unknown_charge');
  assert.match(r.reason, /cannot be applied/);
});

test('a non-numeric charge is unknown, not zero', () => {
  ['', 'about 40', null, undefined, NaN].forEach(function (v) {
    assert.strictEqual(m.refrigerantScope(asset({ refrigerant_type: 'r410a', refrigerant_charge_lb: v })).scope,
      'unknown_charge', 'accepted ' + JSON.stringify(v));
  });
});

test('a negative charge is unknown, not below', () => {
  assert.strictEqual(m.refrigerantScope(asset({ refrigerant_type: 'r410a', refrigerant_charge_lb: -5 })).scope, 'unknown_charge');
});

test('a genuine zero charge IS below -- somebody recorded it', () => {
  // 0 is falsy; a `||` guard would have called this unknown and lost a real
  // measurement.
  const r = m.refrigerantScope(asset({ refrigerant_type: 'r410a', refrigerant_charge_lb: 0 }));
  assert.strictEqual(r.scope, 'below');
  assert.strictEqual(r.charge_lb, 0);
});

test('"holds no refrigerant" is a real answer, distinct from unrecorded', () => {
  // A boiler or a pump. Collapsing this into unknown would flood the board
  // with unknowns that nobody can ever resolve.
  assert.strictEqual(m.refrigerantScope(asset({ refrigerant_type: 'none' })).scope, 'not_applicable');
});

// ---------------------------------------------------------------------------
section('the threshold, and the refusal to issue a verdict');

test('at or above 50 lb is at_or_above; the boundary is inclusive', () => {
  assert.strictEqual(m.refrigerantScope(asset({ refrigerant_type: 'r22', refrigerant_charge_lb: 50 })).scope, 'at_or_above');
  assert.strictEqual(m.refrigerantScope(asset({ refrigerant_type: 'r22', refrigerant_charge_lb: 49.9 })).scope, 'below');
});

test('the threshold and its citation travel WITH the answer', () => {
  // So the number the answer depends on can be checked rather than trusted.
  const r = m.refrigerantScope(asset({ refrigerant_type: 'r22', refrigerant_charge_lb: 60 }));
  assert.strictEqual(r.threshold_lb, 50);
  assert.strictEqual(r.citation, '40 CFR 82.157');
  assert.strictEqual(m.EPA_LEAK_THRESHOLD_LB, 50);
});

test('the threshold is overridable, not hardcoded into the answer', () => {
  assert.strictEqual(m.refrigerantScope(asset({ refrigerant_type: 'r22', refrigerant_charge_lb: 30 }), 25).scope, 'at_or_above');
});

test('IT NEVER ISSUES A VERDICT -- no "must", no leak rate, no schedule', () => {
  const r = m.refrigerantScope(asset({ refrigerant_type: 'r22', refrigerant_charge_lb: 60 }));
  assert.match(r.reason, /may be in scope/);
  assert.match(r.reason, /confirm against the current rule/);
  assert.ok(!/must|required to|quarterly|annually|%/.test(r.reason),
    'the engine stated an obligation it has not earned: ' + r.reason);
  const src = require('fs').readFileSync(require.resolve('./mech-assets.js'), 'utf8');
  assert.ok(!/\b(10|20|30)\s*%/.test(src.replace(/\/\/[^\n]*/g, '')),
    'a leak-rate percentage is encoded in the engine');
});

// ---------------------------------------------------------------------------
section('warranty reuses the shared boundary, in this app\'s words');

test('a future warranty is in_warranty', () => {
  assert.strictEqual(m.classifyWarranty(asset({ warranty_expires_on: '2028-01-01' }), TODAY).status, 'in_warranty');
});

test('inside the window is expiring; past is expired', () => {
  assert.strictEqual(m.classifyWarranty(asset({ warranty_expires_on: '2026-09-20' }), TODAY).status, 'expiring');
  assert.strictEqual(m.classifyWarranty(asset({ warranty_expires_on: '2026-01-01' }), TODAY).status, 'expired');
});

test('has_warranty:false is "none" -- checked and out, not unchecked', () => {
  assert.strictEqual(m.classifyWarranty(asset({ has_warranty: false }), TODAY).status, 'none');
});

test('no date and no answer is UNKNOWN, never in_warranty', () => {
  assert.strictEqual(m.classifyWarranty(asset({}), TODAY).status, 'unknown');
});

test('it uses the SHARED primitive, and maps "valid" to its own word', () => {
  // If it spoke the primitive's vocabulary it would leak 'valid' into a UI
  // that says in_warranty everywhere else.
  const src = require('fs').readFileSync(require.resolve('./mech-assets.js'), 'utf8');
  assert.match(src, /require\('\.\/credential-expiry'\)/);
  assert.strictEqual(m.classifyWarranty(asset({ warranty_expires_on: '2028-01-01' }), TODAY).status !== 'valid', true);
  assert.strictEqual(m.DEFAULT_WARN_DAYS, require('./credential-expiry').DEFAULT_WARN_DAYS);
});

// ---------------------------------------------------------------------------
section('the registry board');

const FLEET = [
  asset({ asset_id: 'A1', customer_name: 'Ruiz Foods', site_name: 'Plant 1', refrigerant_type: 'r22', refrigerant_charge_lb: 120, warranty_expires_on: '2028-01-01' }),
  asset({ asset_id: 'A2', customer_name: 'Ruiz Foods', site_name: 'Plant 1', refrigerant_type: 'r410a', refrigerant_charge_lb: 12, has_warranty: false }),
  asset({ asset_id: 'A3', customer_name: 'Ruiz Foods', site_name: 'Plant 2', refrigerant_type: 'r410a', warranty_expires_on: '2026-09-10' }),
  asset({ asset_id: 'A4', customer_name: 'Chen Retail', site_name: 'Store 3', asset_type: 'boiler', refrigerant_type: 'none' })
];

test('counts assets and derives sites from the rows', () => {
  const b = m.evaluateRegistry(FLEET, TODAY);
  assert.strictEqual(b.ok, true);
  assert.strictEqual(b.counts.assets, 4);
  assert.strictEqual(b.counts.sites, 3);
});

test('the unknowns are surfaced beside the totals, not buried', () => {
  const b = m.evaluateRegistry(FLEET, TODAY);
  assert.strictEqual(b.refrigerant.at_or_above, 1);
  assert.strictEqual(b.refrigerant.below, 1);
  assert.strictEqual(b.refrigerant.not_applicable, 1);
  assert.strictEqual(b.refrigerant.unknown_charge, 1);
  assert.strictEqual(b.unknown_charge_count, 1);
  // A4 has neither a warranty date nor has_warranty:false -- nobody checked.
  assert.strictEqual(b.unknown_warranty_count, 1);
});

test('warranty states are counted separately from refrigerant scope', () => {
  const b = m.evaluateRegistry(FLEET, TODAY);
  assert.strictEqual(b.warranty.in_warranty, 1);
  assert.strictEqual(b.warranty.expiring, 1);
  assert.strictEqual(b.warranty.none, 1);
  assert.strictEqual(b.warranty.unknown, 1);
});

test('the board carries the threshold it used', () => {
  const b = m.evaluateRegistry(FLEET, TODAY, { threshold_lb: 25 });
  assert.strictEqual(b.threshold_lb, 25);
  assert.strictEqual(b.refrigerant.at_or_above, 1);
});

test('an asset with no id is dropped rather than shown as blank', () => {
  const b = m.evaluateRegistry(FLEET.concat([{ asset_type: 'rtu' }, null, 'x']), TODAY);
  assert.strictEqual(b.counts.assets, 4);
});

test('an empty registry is an empty board, not an error and not a verdict', () => {
  const b = m.evaluateRegistry([], TODAY);
  assert.strictEqual(b.ok, true);
  assert.strictEqual(b.counts.assets, 0);
  assert.strictEqual(b.rows.length, 0);
});

test('a bad today is refused rather than compared against', () => {
  assert.strictEqual(m.evaluateRegistry([], 'today').ok, false);
});

test('it issues NO aggregate site-compliance verdict', () => {
  // That is a join into agreements and certificates that does not exist yet.
  // Inventing it from asset rows alone is the fabricated-KPI shape this app
  // was cleaned of on 2026-08-27.
  const b = m.evaluateRegistry(FLEET, TODAY);
  assert.ok(!('compliant' in b) && !('compliance' in b) && !('score' in b));
});

test('the module ships NO seeded assets', () => {
  const src = require('fs').readFileSync(require.resolve('./mech-assets.js'), 'utf8');
  assert.ok(!/const SEED|SAMPLE_|DEMO_|Carrier 48TC/.test(src));
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' MECH-ASSET ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
