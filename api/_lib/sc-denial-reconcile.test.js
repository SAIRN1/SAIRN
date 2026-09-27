// api/_lib/sc-denial-reconcile.test.js
//
// Run:  node api/_lib/sc-denial-reconcile.test.js
//
// REQUIREMENT: SAIRNcode records denials twice -- sc_denial is a hand-typed
//   aggregate per code, sc_denial_events is one row per occurrence -- and no
//   code has ever compared the two, so a practice can read a dashboard that
//   nothing supports. This file holds the reconciler's refusals: a missing
//   aggregate count must NOT become a zero, money must compare in whole cents
//   rather than floats, "agrees" must count only codes that were actually
//   compared, and the reconciler must pick no side between the two sources.
//
// THE ENGINE HAS NO CALLER YET, AND THIS SUITE SAYS SO LOUDLY -- see section F.
// api/sd-data.js is held by hank-queue13, so the dispatch line is deliberately
// not added. An engine with no caller is the SAIRNmechanical G3 defect, and the
// only honest way to ship one is to assert its own unreachability so the next
// session meets the fact rather than discovering it.
//
// ── WHAT IS WORTH DRIVING ─────────────────────────────────────────────────
// SAIRNcode stores denials twice: sc_denial is a hand-typed AGGREGATE per code
// with no payer and no date, sc_denial_events is one row per real occurrence.
// Nothing has ever compared them. The arms below are about the ways a comparison
// like this quietly lies:
//
//   1. A MISSING COUNT READ AS ZERO. If an absent aggregate count becomes 0, every
//      code somebody has not filled in reports "events_higher" and the real
//      disagreements drown. Arms C1-C3.
//   2. MONEY IN FLOATS. Three events of 33.33 do not sum to a typed 99.99 under
//      ===, and an engine comparing floats reports a difference that is not real.
//      Arm D1 drives exactly that.
//   3. AGREEMENT INFLATED BY THINGS IT COULD NOT CHECK. `agrees` must count only
//      codes actually compared; not_comparable is its own tally. Arm E2.
//   4. ONE-SIDED CODES TREATED AS AGREEMENT. A code with events and no aggregate
//      row is the dashboard being blind, not a match. Arms B3/B4.
//
// Exit 0 clean / 1 findings.
'use strict';
const assert = require('assert');
const path = require('path');
const fs = require('fs');
// SC_DENIAL_MODULE points this at a MUTATED COPY, the same convention SD_HTML,
// MECH_HTML and DR_MODULE_DIR already carry. Without it a negative control has to
// edit the tracked module and remember to put it back, which is the shape that
// leaves a sabotaged file on disk when something interrupts.
const MODULE_PATH = process.env.SC_DENIAL_MODULE
  || path.join(__dirname, 'sc-denial-reconcile.js');
const { reconcile, cents, countOf, codeKey } = require(MODULE_PATH);

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }
const row = (out, code) => {
  const r = out.rows.find(x => x.code === code);
  assert.ok(r, 'no row for code ' + code + ' in ' + JSON.stringify(out.rows.map(x => x.code)));
  return r;
};

console.log('SAIRNcode -- the hand-typed denial aggregate vs the logged events');

// ── A. THE HELPERS ───────────────────────────────────────────────────────
section('A. the primitives, because every arm below rests on them');
test('A1. cents() rounds to whole cents and refuses what is not a number', () => {
  assert.strictEqual(cents(99.99), 9999);
  assert.strictEqual(cents('33.33'), 3333);
  assert.strictEqual(cents(0), 0, 'zero is a real amount and must not be null');
  [null, undefined, '', 'abc', NaN, Infinity].forEach(v =>
    assert.strictEqual(cents(v), null, JSON.stringify(v) + ' produced a number'));
});
test('A2. countOf() refuses a fraction, a negative and a non-number -- and keeps 0', () => {
  assert.strictEqual(countOf(12), 12);
  assert.strictEqual(countOf('3'), 3);
  assert.strictEqual(countOf(0), 0, 'a count of zero IS entered data and must survive');
  [null, undefined, '', 'abc', -1, 1.5, NaN].forEach(v =>
    assert.strictEqual(countOf(v), null, JSON.stringify(v) + ' was accepted as a count'));
});
test('A3. codeKey() trims and upper-cases, and keeps an empty code as its own bucket', () => {
  assert.strictEqual(codeKey(' 99213 '), '99213');
  assert.strictEqual(codeKey('j1745'), 'J1745');
  assert.strictEqual(codeKey(null), '',
    'a denial logged against no code must not vanish -- it is a data problem '
    + 'somebody should see');
});

// ── B. THE FOUR DISAGREEMENT SHAPES ──────────────────────────────────────
section('B. the shapes a real practice produces');
const AGG = [
  { id: 'a1', code: '99213', cause: 'Missing modifier', count: 12, amount: 1200 },
  { id: 'a2', code: '97110', cause: '—', count: 2, amount: 200 },
  { id: 'a3', code: 'J1745', cause: 'Prior auth', count: 5, amount: 5000 },
  { id: 'a4', code: '99396', cause: 'Frequency', count: '', amount: 300 },
];
const EVT = [
  { id: 'e1', code: '99213', payer: 'Aetna', reason: 'Modifier', amount: 100, date: '2026-09-01' },
  { id: 'e2', code: '99213', payer: 'Aetna', reason: 'Modifier', amount: 100, date: '2026-09-02' },
  { id: 'e3', code: '97110', payer: 'Cigna', reason: 'Units', amount: 100, date: '2026-09-03' },
  { id: 'e4', code: '97110', payer: 'Cigna', reason: 'Units', amount: 100, date: '2026-09-04' },
  { id: 'e5', code: '97110', payer: 'Cigna', reason: 'Units', amount: 100, date: '2026-09-05' },
  { id: 'e6', code: '80053', payer: 'UHC', reason: 'Bundled', amount: 45, date: '2026-09-06' },
  { id: 'e7', code: '99396', payer: 'BCBS', reason: 'Frequency', amount: 150, date: '2026-09-07' },
];
const OUT = reconcile(AGG, EVT);
test('B1. AGGREGATE HIGHER: 12 typed, 2 logged', () => {
  const r = row(OUT, '99213');
  assert.strictEqual(r.state, 'aggregate_higher');
  assert.strictEqual(r.aggregate_count, 12);
  assert.strictEqual(r.event_count, 2);
  assert.strictEqual(r.count_difference, -10);
  assert.ok(/does not decide which/.test(r.reason),
    'the reason asserts which side is right: ' + r.reason);
});
test('B2. EVENTS HIGHER: 2 typed, 3 logged', () => {
  const r = row(OUT, '97110');
  assert.strictEqual(r.state, 'events_higher');
  assert.strictEqual(r.count_difference, 1);
});
test('B3. AGGREGATE ONLY is not agreement -- nothing supports the count', () => {
  const r = row(OUT, 'J1745');
  assert.strictEqual(r.state, 'aggregate_only');
  assert.ok(/says nothing supports it/.test(r.reason),
    'it claims the count is wrong rather than unsupported: ' + r.reason);
});
test('B4. EVENTS ONLY is not agreement -- the dashboard is blind to it', () => {
  const r = row(OUT, '80053');
  assert.strictEqual(r.state, 'events_only');
  assert.strictEqual(r.aggregate_count, null);
  assert.ok(/dashboard reads/.test(r.reason));
});
test('B5. worst disagreement first, and an uncomparable code is not sorted as zero', () => {
  assert.strictEqual(OUT.rows[0].code, '99213', 'the -10 difference is not first');
  const last = OUT.rows[OUT.rows.length - 1];
  assert.strictEqual(last.state, 'no_aggregate_count',
    'the code that could not be compared should sort with the unknowns, not among '
    + 'the agreements; got ' + last.code + '/' + last.state);
});

// ── C. THE MISSING COUNT ─────────────────────────────────────────────────
section('C. a missing aggregate count is not a count of zero');
test('C1. an empty count is `no_aggregate_count`', () => {
  const r = row(OUT, '99396');
  assert.strictEqual(r.state, 'no_aggregate_count');
  assert.strictEqual(r.aggregate_count, null);
  assert.strictEqual(r.count_difference, null,
    'a difference was computed against a count nobody entered');
});
test('C2. ...and it says so in words', () => {
  assert.ok(/NOT a count of zero/.test(row(OUT, '99396').reason));
});
test('C3. a count of ZERO is real data and IS compared', () => {
  const o = reconcile([{ code: 'X1', count: 0, amount: 0 }],
                      [{ code: 'X1', amount: 10 }]);
  const r = row(o, 'X1');
  assert.strictEqual(r.state, 'events_higher',
    'an entered zero must be compared, not treated as absent; got ' + r.state);
  assert.strictEqual(r.count_difference, 1);
});

// ── D. MONEY ─────────────────────────────────────────────────────────────
section('D. amounts in cents, because floats do not add up');
test('D1. three events of 33.33 match a typed 99.99 exactly', () => {
  const o = reconcile([{ code: 'F1', count: 3, amount: 99.99 }],
                      [{ code: 'F1', amount: 33.33 }, { code: 'F1', amount: 33.33 },
                       { code: 'F1', amount: 33.33 }]);
  const r = row(o, 'F1');
  // 33.33*3 === 99.99000000000001 in float arithmetic.
  assert.strictEqual(r.amount_difference_cents, 0,
    'a float comparison reported a difference that is not real: '
    + r.amount_difference_cents + ' cents');
  assert.strictEqual(r.state, 'agrees');
});
test('D2. a real money difference is returned in cents AND dollars', () => {
  const r = row(OUT, '99213');
  assert.strictEqual(r.aggregate_cents, 120000);
  assert.strictEqual(r.event_cents, 20000);
  assert.strictEqual(r.amount_difference_cents, -100000);
  assert.strictEqual(r.amount_difference, -1000,
    'the dollar figure must be derived here, not left for a caller to divide');
});
test('D3. an event with an unusable amount still COUNTS as an occurrence', () => {
  const o = reconcile([{ code: 'M1', count: 2, amount: 50 }],
                      [{ code: 'M1', amount: 50 }, { code: 'M1', amount: 'n/a' }]);
  const r = row(o, 'M1');
  assert.strictEqual(r.event_count, 2,
    'dropping the row would make the event count disagree with the number of rows '
    + 'a user can see in the table');
  assert.strictEqual(o.totals.events_missing_amount, 1,
    'the unusable amount is not counted anywhere, so nobody can see it exists');
});

// ── E. TOTALS ────────────────────────────────────────────────────────────
section('E. the totals do not flatter');
test('E1. every code appears exactly once and the denominator is published', () => {
  assert.strictEqual(OUT.totals.codes, 5, JSON.stringify(OUT.rows.map(r => r.code)));
  assert.strictEqual(OUT.totals.aggregate_rows, 4);
  assert.strictEqual(OUT.totals.event_rows, 7);
});
test('E2. `agrees` counts ONLY codes that were compared', () => {
  assert.strictEqual(OUT.totals.agrees, 0);
  assert.strictEqual(OUT.totals.not_comparable, 1,
    'the uncomparable code must have its own tally rather than inflating agrees');
  const named = OUT.totals.agrees + OUT.totals.aggregate_higher + OUT.totals.events_higher
    + OUT.totals.aggregate_only + OUT.totals.events_only + OUT.totals.not_comparable;
  assert.strictEqual(named, OUT.totals.codes,
    'the six state tallies do not add to the code count, so a state is unreported');
});
test('E3. MULTIPLE aggregate rows for one code are summed AND counted', () => {
  const o = reconcile([{ code: 'D1', count: 1, amount: 10 }, { code: 'D1', count: 1, amount: 10 }],
                      [{ code: 'D1', amount: 10 }, { code: 'D1', amount: 10 }]);
  const r = row(o, 'D1');
  assert.strictEqual(r.aggregate_count, 2);
  assert.strictEqual(r.aggregate_rows, 2,
    'one row of 2 and two rows of 1 are different data-entry stories and a caller '
    + 'seeing only the sum cannot tell them apart');
  assert.strictEqual(r.state, 'agrees');
});
test('E4. garbage rows do not throw and do not silently become a code', () => {
  const o = reconcile([null, 'x', { code: 'G1', count: 1, amount: 1 }],
                      [undefined, 7, { code: 'G1', amount: 1 }]);
  assert.strictEqual(o.totals.codes, 1);
  assert.strictEqual(row(o, 'G1').state, 'agrees');
});
test('E5. empty input is empty, not an error and not a pass', () => {
  const o = reconcile([], []);
  assert.strictEqual(o.totals.codes, 0);
  assert.strictEqual(o.rows.length, 0);
  assert.ok(Array.isArray(o.limits) && o.limits.length >= 4,
    'the limits travel with every answer, including the empty one');
});
test('E6. THE LIMITS SAY IT PICKS NO SIDE and computes no probability', () => {
  const j = OUT.limits.join(' ');
  assert.ok(/picks no side/i.test(j), 'the limits do not say it is not authoritative');
  assert.ok(/no payer and no date/i.test(j),
    'the limits do not name the aggregate\'s missing fields, so a reader could '
    + 'think a disagreement is attributable to a payer');
  assert.ok(/probability/i.test(j),
    'the limits do not state that no probability is computed, which is the one '
    + 'claim this app has explicitly refused elsewhere');
});

// ── F. THE UNREACHABILITY, ASSERTED ──────────────────────────────────────
section('F. it has no caller, and that is asserted rather than left to be found');
test('F1. no client sends a `reconcile` action for sc_denial', () => {
  const app = fs.readFileSync(path.join(__dirname, '..', '..', 'sairncode.html'), 'utf8');
  const wired = /scData\(\s*'reconcile'/.test(app);
  assert.strictEqual(wired, false,
    'sairncode.html now sends `reconcile`. GOOD -- but this arm and section F\'s '
    + 'comment are now stale and must be rewritten, and the tier-a obligation '
    + 'recording the gap should be discharged.');
});
test('F2. the registry does not declare the verb yet', () => {
  const reg = fs.readFileSync(path.join(__dirname, '..', '_resources', 'sairncode.js'), 'utf8');
  assert.strictEqual(/'reconcile'/.test(reg), false,
    'the verb is declared. If it is declared and not sent, that is exactly the '
    + 'SAIRNmechanical G3 state -- declared, tested, unreachable -- and is worse '
    + 'than not declaring it.');
});
test('F3. the module says out loud that it is unwired, and how to wire it', () => {
  const src = fs.readFileSync(MODULE_PATH, 'utf8');
  assert.ok(/There is NO caller/.test(src), 'the header does not state the gap');
  assert.ok(/TO WIRE IT, three things/.test(src),
    'the header does not say what wiring it takes, so the next session re-derives it');
  assert.ok(/G3/.test(src),
    'the header does not name the defect class it is deliberately sitting in');
});

console.log('\n' + (fail ? 'FAIL' : 'ALL') + ' -- ' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
