// api/_lib/mech-assets.test.js
// REQUIREMENT: a mechanical asset is identified by a server-issued id and its service
//   history cannot be attributed to an asset the record does not name
//
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

// ---------------------------------------------------------------------------
section('THE SECOND RULE: 40 CFR 84.106, and it is NOT the first one');

// The case the whole feature exists for. `docs/2026-09-17-trades-audit-rederived.md`
// §2.1: "A 20 lb R-410A unit is correctly reported `below` the 82.157
// threshold, and has been in scope under 84.106 since January." If these two
// assertions ever agree, one of the rules has stopped being modelled.
test('a 20 lb HFC unit is BELOW under 82.157 and AT/ABOVE under 84.106', () => {
  const a = asset({ refrigerant_type: 'r410a', refrigerant_charge_lb: 20, hfc_gwp_over_53: true });
  assert.strictEqual(m.refrigerantScope(a).scope, 'below');
  assert.strictEqual(m.aimScope(a).scope, 'at_or_above');
});

test('the two carry DIFFERENT thresholds and DIFFERENT citations', () => {
  const a = asset({ refrigerant_type: 'r410a', refrigerant_charge_lb: 20, hfc_gwp_over_53: true });
  const s608 = m.refrigerantScope(a), aim = m.aimScope(a);
  assert.strictEqual(s608.threshold_lb, 50);
  assert.strictEqual(aim.threshold_lb, 15);
  assert.strictEqual(s608.citation, '40 CFR 82.157');
  assert.strictEqual(aim.citation, '40 CFR 84.106');
  assert.notStrictEqual(s608.citation, aim.citation);
});

// THE ONE THAT MATTERS FOR THIS RULE, and it is the twin of unknown_charge.
test('at/above 15 lb with NO substance stated is unknown_substance, NEVER below', () => {
  const r = m.aimScope(asset({ refrigerant_type: 'r410a', refrigerant_charge_lb: 40 }));
  assert.strictEqual(r.scope, 'unknown_substance');
  assert.notStrictEqual(r.scope, 'below');
  assert.notStrictEqual(r.scope, 'not_applicable');
  assert.match(r.reason, /NOT a finding that the rule does not apply/);
});

test('a stated NO is an answer and is not unknown_substance', () => {
  assert.strictEqual(
    m.aimScope(asset({ refrigerant_type: 'r717', refrigerant_charge_lb: 900, hfc_gwp_over_53: false })).scope,
    'not_applicable');
});

// Charge alone settles the negative, so the substance is not asked for.
test('under 15 lb is below whatever the substance is -- stated or not', () => {
  ['r410a', 'r744', 'other'].forEach(function (t) {
    [undefined, true, false].forEach(function (g) {
      assert.strictEqual(
        m.aimScope(asset({ refrigerant_type: t, refrigerant_charge_lb: 14.9, hfc_gwp_over_53: g })).scope,
        'below', t + ' / ' + String(g));
    });
  });
});

test('the boundary is INCLUSIVE at 15 lb, same as 50 lb is for 82.157', () => {
  const g = { refrigerant_type: 'r410a', hfc_gwp_over_53: true };
  assert.strictEqual(m.aimScope(asset(Object.assign({ refrigerant_charge_lb: 15 }, g))).scope, 'at_or_above');
  assert.strictEqual(m.aimScope(asset(Object.assign({ refrigerant_charge_lb: 14.99 }, g))).scope, 'below');
});

test('an unweighed unit is unknown_charge here too, not unknown_substance', () => {
  ['', '   ', 'about 40', null, undefined].forEach(function (v) {
    assert.strictEqual(m.aimScope(asset({ refrigerant_type: 'r410a', refrigerant_charge_lb: v, hfc_gwp_over_53: true })).scope,
      'unknown_charge', 'accepted ' + JSON.stringify(v));
  });
});

test('a unit holding no refrigerant is not_applicable under both rules', () => {
  const a = asset({ refrigerant_type: 'none' });
  assert.strictEqual(m.refrigerantScope(a).scope, 'not_applicable');
  assert.strictEqual(m.aimScope(a).scope, 'not_applicable');
});

// ---------------------------------------------------------------------------
section('THE REPAIR CLOCK: it runs on a recorded date or it does not run');

test('no leak date means NO clock, and no invented deadline', () => {
  const c = m.aimRepairClock(asset({ refrigerant_charge_lb: 40, installed_on: '2020-01-01' }), TODAY);
  assert.strictEqual(c.state, 'no_leak_recorded');
  assert.strictEqual(c.repair_due_on, null);
  assert.strictEqual(c.days_left, null);
});

test('a malformed leak date is no clock, not a clock from a repaired date', () => {
  // isCalendarDate rejects 2026-02-31; `new Date` would SILENTLY REPAIR it to
  // 2026-03-03 and put a deadline three days late on the screen.
  ['2026-02-31', '09/02/2026', 'yesterday'].forEach(function (v) {
    const c = m.aimRepairClock(asset({ leak_detected_on: v }), TODAY);
    assert.strictEqual(c.state, 'no_leak_recorded', 'accepted ' + v);
    assert.strictEqual(c.repair_due_on, null);
  });
});

test('30 days from the recorded date, and the arithmetic crosses a month', () => {
  const c = m.aimRepairClock(asset({ leak_detected_on: '2026-08-20' }), TODAY);
  assert.strictEqual(c.repair_due_on, '2026-09-19');
  assert.strictEqual(c.repair_days, 30);
  assert.strictEqual(c.state, 'open');
  assert.strictEqual(c.days_left, 17);
});

test('past the window with no verification is OVERDUE, not still open', () => {
  const c = m.aimRepairClock(asset({ leak_detected_on: '2026-07-01' }), TODAY);
  assert.strictEqual(c.state, 'overdue');
  assert.ok(c.days_left < 0);
  assert.match(c.reason, /retrofit or retirement/);
});

// Recorded, never inferred: the clock stops because somebody wrote a date
// down, not because enough days went by.
test('a recorded verification stops the clock and starts the 10-day follow-up', () => {
  const c = m.aimRepairClock(asset({ leak_detected_on: '2026-08-20', leak_repair_verified_on: '2026-09-01' }), TODAY);
  assert.strictEqual(c.state, 'repair_verified');
  assert.strictEqual(c.followup_due_on, '2026-09-11');
  assert.strictEqual(c.followup_days, 10);
});

test('an overdue unit does NOT become verified by the passage of time', () => {
  assert.strictEqual(m.aimRepairClock(asset({ leak_detected_on: '2026-01-01' }), TODAY).state, 'overdue');
});

// ---------------------------------------------------------------------------
section('THE BOARD REPORTS BOTH AND SUMS NEITHER');

const TWO_RULE_FLEET = [
  // below 50, at/above 15, HFC stated -> disagrees across the two rules
  { asset_id: 'B1', customer_name: 'C', site_name: 'S', asset_type: 'rtu', refrigerant_type: 'r410a', refrigerant_charge_lb: 20, hfc_gwp_over_53: true },
  // at/above both
  { asset_id: 'B2', customer_name: 'C', site_name: 'S', asset_type: 'chiller', refrigerant_type: 'r134a', refrigerant_charge_lb: 900, hfc_gwp_over_53: true },
  // at/above 15, substance never stated
  { asset_id: 'B3', customer_name: 'C', site_name: 'S', asset_type: 'rtu', refrigerant_type: 'r410a', refrigerant_charge_lb: 30 },
  // below both
  { asset_id: 'B4', customer_name: 'C', site_name: 'S', asset_type: 'split_system', refrigerant_type: 'r410a', refrigerant_charge_lb: 8, hfc_gwp_over_53: true },
  // leak recorded and past the window
  { asset_id: 'B5', customer_name: 'C', site_name: 'S', asset_type: 'rtu', refrigerant_type: 'r410a', refrigerant_charge_lb: 40, hfc_gwp_over_53: true, leak_detected_on: '2026-07-01' }
];

test('the AIM block is its own block, with its own threshold and citation', () => {
  const b = m.evaluateRegistry(TWO_RULE_FLEET, TODAY);
  assert.strictEqual(b.aim.threshold_lb, 15);
  assert.strictEqual(b.aim.citation, '40 CFR 84.106');
  assert.strictEqual(b.aim.gwp_floor, 53);
  // NOT nested under refrigerant -- nesting would read as a refinement of one
  // rule rather than a second rule.
  assert.ok(!('aim' in b.refrigerant));
});

test('the two rules disagree on the same fleet, and both figures survive', () => {
  const b = m.evaluateRegistry(TWO_RULE_FLEET, TODAY);
  assert.strictEqual(b.refrigerant.at_or_above, 1);   // only the 900 lb chiller
  assert.strictEqual(b.aim.scope.at_or_above, 3);     // B1, B2, B5
  assert.notStrictEqual(b.refrigerant.at_or_above, b.aim.scope.at_or_above);
});

test('unknown_substance is surfaced beside the totals, never inside below', () => {
  const b = m.evaluateRegistry(TWO_RULE_FLEET, TODAY);
  assert.strictEqual(b.aim.unknown_substance_count, 1);
  assert.strictEqual(b.aim.scope.below, 1);           // B4 only. B3 is NOT here.
});

test('the overdue repair count is surfaced, not buried in the scope tally', () => {
  const b = m.evaluateRegistry(TWO_RULE_FLEET, TODAY);
  assert.strictEqual(b.aim.overdue_repair_count, 1);
  assert.strictEqual(b.aim.repair.overdue, 1);
  assert.strictEqual(b.aim.repair.no_leak_recorded, 4);
});

// THE STRUCTURAL REFUSAL. A single "in scope" number would be this app
// deciding which federal rule governs somebody's machine.
// A first draft of this test scanned the board for ANY number equal to the sum
// and it FAILED on a coincidence -- `refrigerant.below` was 4 and so was
// 1 + 3. Recorded rather than quietly rewritten, because the lesson is the
// test's, not the code's: a value-equality scan over a board of small counts
// collides by chance, and a check that fires on a coincidence teaches the next
// person to ignore it. What is asserted instead is the STRUCTURE: every count
// is reachable only through a block that names its own citation, so no reader
// and no caller can pick up a number without the rule that produced it.
test('the board publishes NO merged in-scope total across the two rules', () => {
  const b = m.evaluateRegistry(TWO_RULE_FLEET, TODAY);
  ['in_scope', 'total_in_scope', 'leak_scope', 'leak_rule_scope', 'refrigerant_scope', 'compliance']
    .forEach(function (k) { assert.ok(!(k in b), 'the board exposes a merged `' + k + '`'); });
  // Each rule's counts sit under a block carrying that rule's own citation,
  // and the citations differ.
  assert.strictEqual(b.citation, '40 CFR 82.157');
  assert.strictEqual(b.aim.citation, '40 CFR 84.106');
  assert.ok(!('citation' in b.refrigerant) || b.refrigerant.citation === b.citation);
  // And the two scope tallies are separate objects, not one shared reference
  // that a later edit could make both rules write into.
  assert.notStrictEqual(b.refrigerant, b.aim.scope);
  assert.ok(!('unknown_substance' in b.refrigerant),
    'the 82.157 tally has grown a state that belongs to 84.106 -- the two are merging');
});

test('every row carries both answers, separately named', () => {
  const b = m.evaluateRegistry(TWO_RULE_FLEET, TODAY);
  const r = b.rows.find(function (x) { return x.asset_id === 'B1'; });
  assert.strictEqual(r.refrigerant_scope, 'below');
  assert.strictEqual(r.aim_scope, 'at_or_above');
});

// A caller must not be able to move both rules with one knob.
test('the two thresholds are independently overridable', () => {
  const b = m.evaluateRegistry(TWO_RULE_FLEET, TODAY, { threshold_lb: 25, aim_threshold_lb: 5 });
  assert.strictEqual(b.threshold_lb, 25);
  assert.strictEqual(b.aim.threshold_lb, 5);
});

test('overriding only the 608 threshold leaves 84.106 at 15', () => {
  const b = m.evaluateRegistry(TWO_RULE_FLEET, TODAY, { threshold_lb: 25 });
  assert.strictEqual(b.aim.threshold_lb, 15);
});

// ── THE THIRD RULE: A STATE ONE, WITH AN AXIS NEITHER FEDERAL LIMB HAS ─────
// The arm that matters is the BOUNDARY one. 40 CFR 82.157 reaches 50 lb or
// more; the CARB program reaches MORE THAN 50 lb. A shared threshold constant
// with a shared comparison would have answered one of those wrongly at exactly
// 50 and nothing would have said so.
section('THE THIRD RULE: 17 CCR 95380, and it is a CALIFORNIA rule');

const CA = { asset_id: 'K1', customer_name: 'C', site_name: 'S', site_state: 'CA',
             asset_type: 'chiller', refrigerant_type: 'r134a' };

test('no state recorded is unknown_jurisdiction -- NOT below, NOT out of scope', () => {
  const r = m.carbScope({ asset_type: 'rtu', refrigerant_type: 'r410a',
                          refrigerant_charge_lb: 900, gwp_over_150: true });
  assert.strictEqual(r.scope, 'unknown_jurisdiction');
  assert.ok(/NOT a finding/.test(r.reason), r.reason);
});

test('a site outside California is not_applicable, and the state is NAMED', () => {
  const r = m.carbScope(Object.assign({}, CA, { site_state: 'OH',
    refrigerant_charge_lb: 900, gwp_over_150: true }));
  assert.strictEqual(r.scope, 'not_applicable');
  assert.ok(/recorded in OH/.test(r.reason), r.reason);
});

test('the state is case- and space-insensitive, because a roster types it by hand', () => {
  assert.strictEqual(m.carbScope(Object.assign({}, CA, { site_state: ' ca ',
    refrigerant_charge_lb: 900, gwp_over_150: true })).scope, 'at_or_above');
});

test('THE BOUNDARY: at exactly 50 lb the federal rule is IN and CARB is OUT', () => {
  const asset = { asset_id: 'K', customer_name: 'C', site_name: 'S', site_state: 'CA',
                  asset_type: 'chiller', refrigerant_type: 'r134a',
                  refrigerant_charge_lb: 50, hfc_gwp_over_53: true, gwp_over_150: true };
  assert.strictEqual(m.refrigerantScope(asset).scope, 'at_or_above');
  assert.strictEqual(m.carbScope(asset).scope, 'below');
});

test('...and one tenth of a pound over, CARB is in scope too', () => {
  assert.strictEqual(m.carbScope(Object.assign({}, CA,
    { refrigerant_charge_lb: 50.1, gwp_over_150: true })).scope, 'at_or_above');
});

test('above the threshold with the substance unstated is unknown_substance', () => {
  const r = m.carbScope(Object.assign({}, CA, { refrigerant_charge_lb: 900 }));
  assert.strictEqual(r.scope, 'unknown_substance');
  assert.ok(/NOT a finding/.test(r.reason), r.reason);
});

test('THE ONE SOUND DEDUCTION: at or below GWP 53 is necessarily below 150, so the contractor is not asked twice', () => {
  const r = m.carbScope(Object.assign({}, CA,
    { refrigerant_charge_lb: 900, hfc_gwp_over_53: false }));
  assert.strictEqual(r.scope, 'not_applicable');
  assert.strictEqual(r.derived_from, 'hfc_gwp_over_53');
});

test('NEGATIVE CONTROL: the CONVERSE is not taken -- above 53 says NOTHING about 150, and a refrigerant in the 54-149 band must stay unknown', () => {
  const r = m.carbScope(Object.assign({}, CA,
    { refrigerant_charge_lb: 900, hfc_gwp_over_53: true }));
  assert.strictEqual(r.scope, 'unknown_substance');
});

test('gwp_over_150 stated false is not_applicable, and it wins over the deduction', () => {
  assert.strictEqual(m.carbScope(Object.assign({}, CA,
    { refrigerant_charge_lb: 900, gwp_over_150: false, hfc_gwp_over_53: true })).scope,
    'not_applicable');
});

test('no charge recorded in California is unknown_charge, never below', () => {
  assert.strictEqual(m.carbScope(Object.assign({}, CA, { gwp_over_150: true })).scope,
    'unknown_charge');
});

test('a unit holding no refrigerant is not_applicable even in California', () => {
  assert.strictEqual(m.carbScope(Object.assign({}, CA,
    { refrigerant_type: 'none', refrigerant_charge_lb: 900 })).scope, 'not_applicable');
});

test('the scope answer says what this app does NOT assert', () => {
  const r = m.carbScope(Object.assign({}, CA,
    { refrigerant_charge_lb: 900, gwp_over_150: true }));
  assert.ok(/does NOT encode their frequency or deadlines/.test(r.reason), r.reason);
});

test('the board reports the third rule as its OWN block, with its own citation and an unknown_jurisdiction count the federal tallies do not have', () => {
  const b = m.evaluateRegistry(TWO_RULE_FLEET.concat([
    Object.assign({}, CA, { asset_id: 'K9', refrigerant_charge_lb: 900, gwp_over_150: true })
  ]), TODAY);
  assert.strictEqual(b.carb.citation, '17 CCR 95380 et seq.');
  assert.strictEqual(b.carb.gwp_floor, 150);
  assert.strictEqual(b.carb.state, 'CA');
  assert.strictEqual(b.carb.scope.at_or_above, 1);
  // Every TWO_RULE_FLEET row has no site_state at all.
  assert.strictEqual(b.carb.unknown_jurisdiction_count, TWO_RULE_FLEET.length);
  assert.ok(/NOT encoded/.test(b.carb.not_asserted), b.carb.not_asserted);
});

test('the three tallies are SEPARATE -- no merged "in scope" number exists', () => {
  const b = m.evaluateRegistry(TWO_RULE_FLEET, TODAY);
  assert.ok(b.refrigerant && b.aim && b.carb);
  assert.ok(!('in_scope' in b), 'a merged verdict appeared');
});

test('every row carries the third rule beside the other two, and site_state is normalised on the row', () => {
  const b = m.evaluateRegistry([Object.assign({}, CA, { asset_id: 'K7',
    site_state: 'ca', refrigerant_charge_lb: 900, gwp_over_150: true })], TODAY);
  assert.strictEqual(b.rows[0].site_state, 'CA');
  assert.strictEqual(b.rows[0].carb_scope, 'at_or_above');
  assert.ok(b.rows[0].carb_reason);
});

test('the CARB threshold and GWP floor are independently overridable, and overriding them does not move either federal rule', () => {
  const b = m.evaluateRegistry(TWO_RULE_FLEET, TODAY,
    { carb_threshold_lb: 5, carb_gwp_floor: 9 });
  assert.strictEqual(b.carb.threshold_lb, 5);
  assert.strictEqual(b.carb.gwp_floor, 9);
  assert.strictEqual(b.aim.threshold_lb, 15);
  assert.strictEqual(b.threshold_lb, 50);
});

// The engine still asserts no GWP figure for any named refrigerant -- the
// substance is stated by the contractor, for the reason the header gives.
test('the module carries NO refrigerant-to-GWP table', () => {
  const src = require('fs').readFileSync(require.resolve('./mech-assets.js'), 'utf8');
  assert.ok(!/GWP_TABLE|GWP_BY_REFRIGERANT|r410a\s*:\s*[0-9]/i.test(src),
    'a GWP figure is asserted in this file -- it must be stated by the contractor');
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' MECH-ASSET ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
