// tests/sv_boarding_revenue_coercion.js
//
// REQUIREMENT: SAIRNvet's Revenue MTD figure must survive a non-numeric rate
//   by losing that ROW, not the whole figure.
//
// Run:  node tests/sv_boarding_revenue_coercion.js
//
// ── WHAT THIS IS NOT, AND IT IS THE FIRST THING TO SAY ────────────────────
// This was dispatched as the same defect class as the StoneDesk tax folds
// fixed earlier the same day -- an uncoerced `(x || 0)` concatenating instead
// of adding. **IT IS NOT THAT, AND THAT WAS MEASURED BEFORE ANYTHING WAS
// CHANGED.** The expression is
//
//     s + (b.rate || 0) * days
//
// and `*` has no string overload, so the multiplication coerces before the
// addition ever sees the value. Driven with string rates of "500" and "250"
// over 3 days:
//
//     s + (b.rate||0)*days   ->  2250      (a number)
//     s + (b.rate||0)        ->  "0500250" (the concatenation class)
//
// tools/truthy_sum_check.py reports it anyway, and its own docstring says so:
// *"`s + (i.qty || 0) * (i.cost || 0)` is reported for the `+` and not for the
// `*`."* It calls itself a HAZARD reporter rather than a defect detector, and
// under that framing the report is correct. The baseline entry's own recorded
// reason was *"NOT ASSESSED ... whether it is a defect depends on whether
// anything can put a STRING in this field"*. It has now been assessed: a
// string can arrive (`sv_boarding` is server-synced, and the branch stores the
// payload), and it does no harm here.
//
// ── SO WHY CHANGE IT AT ALL ───────────────────────────────────────────────
// Because the multiplication rescues the STRING case and not the JUNK case.
// `"abc" * 3` is NaN, and one NaN poisons the whole reduce -- the KPI renders
// "$NaN" and every other booking's revenue disappears with it. `Number(x) || 0`
// costs that row and nothing else, which is the convention every other money
// fold on this platform now follows. A one-token change, and the arms below
// are mostly about proving the ordinary cases did not move.
//
// AND THE TIER ROW THAT CITED THIS WAS CORRECTED IN THE SAME CHANGE. It said
// the fold being uncoerced put the figure at risk of the concatenation class.
// It did not. Overstating evidence for a tier is the same error as
// understating it.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'sairnvet.html'), 'utf8');

let pass = 0, fail = 0;
const run = [];
function t(name, fn) { run.push([name, fn]); }
function section(s) { run.push([s, null]); }

// The reduce is lifted out of the file and driven, not modelled -- a copy of
// an expression can drift from the one that ships.
const FOLD_RE = /var revenue = list\.filter\([\s\S]*?\},0\);/;
const m = HTML.match(FOLD_RE);
if (!m) {
  console.log('COULD NOT RUN: the Revenue MTD fold anchor did not match. Nothing was verified.');
  process.exit(3);
}
const SRC = m[0];

// `thisMonth` is computed two lines ABOVE the fold in renderBoarding() and is
// a free variable inside it. Bound explicitly rather than widening the
// extraction to swallow those lines: a wider anchor is a more fragile one, and
// this keeps what is driven to exactly the expression under test.
function revenue(list, today) {
  const expr = SRC.replace(/^var\s+revenue\s*=\s*/, '').replace(/;$/, '');
  // eslint-disable-next-line no-new-func
  return new Function('list', 'thisMonth', 'return (' + expr + ');')(list, today.slice(0, 7));
}
const TODAY = '2026-09-15';
const stay = (rate, d1, d2) => ({ patient: 'Rex', service: 'Boarding', checkin: d1, checkout: d2, rate });

// ---------------------------------------------------------------------------
section('the ordinary cases, which must not have moved');

t('numeric rates give the same total they always did', () => {
  assert.strictEqual(revenue([stay(50, '2026-09-01', '2026-09-04')], TODAY), 150);
  assert.strictEqual(revenue([stay(50, '2026-09-01', '2026-09-04'),
                              stay(20, '2026-09-02', '2026-09-03')], TODAY), 170);
});

t('a grooming row is a flat charge, not rate x days', () => {
  assert.strictEqual(revenue([{ service: 'Full Groom', checkin: '2026-09-05',
                                checkout: '2026-09-05', rate: 75 }], TODAY), 75);
});

t('an empty list, and a row outside the month, both give 0', () => {
  assert.strictEqual(revenue([], TODAY), 0);
  assert.strictEqual(revenue([stay(50, '2026-08-01', '2026-08-04')], TODAY), 0);
});

t('a same-day boarding stay still counts one day, not zero', () => {
  assert.strictEqual(revenue([stay(40, '2026-09-06', '2026-09-06')], TODAY), 40);
});

// ---------------------------------------------------------------------------
section('the case the multiplication ALREADY handled');

t('string rates were never the concatenation class here', () => {
  // Kept as an arm rather than a comment: if somebody later removes the `*
  // days` -- splitting the flat and per-day paths, say -- this goes red and
  // names the reason, instead of the hazard silently becoming real.
  assert.strictEqual(revenue([stay('50', '2026-09-01', '2026-09-04')], TODAY), 150);
  assert.strictEqual(revenue([stay('50', '2026-09-01', '2026-09-04'),
                              stay('20', '2026-09-02', '2026-09-03')], TODAY), 170);
});

t('THE CONTROL: the same data through a BARE fold does concatenate', () => {
  // Proves the arm above passes because of the multiplication and not because
  // string rates are harmless in general.
  const bare = [{ rate: '50' }, { rate: '20' }].reduce((s, b) => s + (b.rate || 0), 0);
  assert.strictEqual(bare, '05020');
  assert.strictEqual(typeof bare, 'string');
});

// ---------------------------------------------------------------------------
section('the case the multiplication did NOT handle -- why this changed');

t('one junk rate costs THAT ROW, not the whole figure', () => {
  // Pre-fix: "abc" * 3 is NaN, NaN poisons the reduce, and the KPI renders
  // "$NaN" -- every other booking's revenue vanishes with it.
  const got = revenue([stay(50, '2026-09-01', '2026-09-04'),
                       stay('abc', '2026-09-02', '2026-09-05')], TODAY);
  assert.ok(!Number.isNaN(got), 'a junk rate still poisons the whole figure: ' + got);
  assert.strictEqual(got, 150, 'expected the good row to survive alone, got ' + got);
});

t('a null, undefined or missing rate is 0 rather than NaN', () => {
  for (const r of [null, undefined]) {
    const got = revenue([stay(r, '2026-09-01', '2026-09-03')], TODAY);
    assert.strictEqual(got, 0, String(r) + ' gave ' + got);
  }
  const got = revenue([{ service: 'Boarding', checkin: '2026-09-01', checkout: '2026-09-03' }], TODAY);
  assert.strictEqual(got, 0, 'a missing rate gave ' + got);
});

t('THE CONTROL: the PRE-FIX expression really did produce NaN', () => {
  const pre = [{ rate: 50 }, { rate: 'abc' }].reduce((s, b) => s + (b.rate || 0) * 3, 0);
  assert.ok(Number.isNaN(pre),
    'the pre-fix expression no longer NaNs -- the arm above may pass for the wrong reason');
});

// ---------------------------------------------------------------------------
section('the detector can see this shape again');

t('sairnvet.html::b.rate is no longer grandfathered', () => {
  const base = JSON.parse(fs.readFileSync(
    path.join(__dirname, '..', 'tools', 'truthy_sum_baseline.json'), 'utf8'));
  assert.ok(!Object.prototype.hasOwnProperty.call(base.grandfathered || {}, 'sairnvet.html::b.rate'),
    'still grandfathered, so the checker still cannot fail on it');
});

t('...and exactly one entry was removed, not a swathe', () => {
  const base = JSON.parse(fs.readFileSync(
    path.join(__dirname, '..', 'tools', 'truthy_sum_baseline.json'), 'utf8'));
  const n = Object.keys(base.grandfathered || {}).length;
  assert.strictEqual(n, 45, 'grandfathered is ' + n + ', expected 45 (46 - 1)');
});

// ---------------------------------------------------------------------------
(async () => {
  for (const [name, fn] of run) {
    if (fn === null) { console.log('--- ' + name + ' ---'); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
  }
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
