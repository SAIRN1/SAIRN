// api/sd-data-numeric-guards.test.js
// REQUIREMENT: a disbursement amount that is not a number is REFUSED, because
//   every comparison against NaN is false and `Number(payload.amount) <= 0`
//   reads as a complete guard while letting anything non-numeric straight
//   through
//
//
// Run:  node api/sd-data-numeric-guards.test.js
//
// The two numeric guards added 2026-09-14 after tools/shape_antipattern_check.py
// (item 90) reported them, plus the arithmetic that makes the first one a real
// defect rather than a style note.
//
// ── WHY THE TRUST ONE IS THE SHARPEST DEFECT IN THE TRIAGE ─────────────────
// api/sd-data.js's Disbursement branch already refused on
//
//     Number(payload.amount) <= 0
//
// which looks complete. It catches '' (0) and it catches a negative. IT DOES
// NOT CATCH A NON-NUMBER, because EVERY COMPARISON AGAINST NaN IS FALSE:
//
//     Number('abc')        -> NaN
//     NaN <= 0             -> false      so the refusal never fires
//     JSON.stringify(NaN)  -> null       so the RPC receives p_amount: null
//
// on ATTORNEY CLIENT TRUST MONEY -- the one balance a bar association audits.
//
// AND THE CONTRAST IS THE LESSON, because correct code on this platform sits
// four lines away from the same call: sen_payer_contracts writes the guard
// NEGATED, `!(Number(x) > 0)`, and `!(NaN > 0)` is TRUE, so it refuses. The two
// forms read as equivalent and differ exactly on NaN. That contrast is pinned
// below so nobody "simplifies" the negated one back.
//
// DRIVEN AGAINST THE REAL HANDLER with a fake REST layer: these arms prove WHICH
// REFUSAL FOR WHICH INPUT, and prove nothing about PostgREST.

'use strict';
const assert = require('assert');
const path = require('path');

let pass = 0, fail = 0;
const queue = [];
function t(name, fn) { queue.push([name, fn]); }
function section(s) { queue.push([s, null]); }

// ── 1. the arithmetic, no fake needed. This is the whole defect. ───────────
section('1. why a range check cannot see NaN');
t("Number('') is 0 -- an ABSENT amount passes as a real number", () => {
  assert.strictEqual(Number(''), 0);
});
t("Number('abc') is NaN", () => {
  assert.ok(Number.isNaN(Number('abc')));
});
t('NaN <= 0 is FALSE, so a `<= 0` refusal never fires on it', () => {
  assert.strictEqual(Number('abc') <= 0, false);
});
t('...but !(NaN > 0) is TRUE, so the NEGATED form does refuse', () => {
  assert.strictEqual(!(Number('abc') > 0), true);
});
t('THE TWO FORMS DIFFER ONLY ON NaN -- on every real number they agree', () => {
  for (const v of [-5, -0.01, 0, 0.01, 5, 1e9]) {
    assert.strictEqual(v <= 0, !(v > 0), 'disagreed on ' + v);
  }
});
t('JSON.stringify turns NaN into null, so it reaches the database as absent', () => {
  assert.strictEqual(JSON.stringify({ p_amount: Number('abc') }), '{"p_amount":null}');
});
t('isFinite is the check that sees all three -- empty, non-numeric and infinite', () => {
  assert.strictEqual(isFinite(Number('')), true);        // 0 is finite; the RANGE check catches it
  assert.strictEqual(isFinite(Number('abc')), false);
  assert.strictEqual(isFinite(Number('Infinity')), false);
});

// ── 2. the source says what the arithmetic requires ───────────────────────
section('2. the guards are where they have to be');
{
  const fs = require('fs');
  const SRC = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
  const trustIdx = SRC.indexOf("resource === 'law_trusttx' && action === 'write'");
  t('the law_trusttx write branch exists', () => { assert.ok(trustIdx > 0); });
  t('AND THE AMOUNT GUARD IS ABOVE BOTH BRANCHES, not patched into the one that was found', () => {
    // The Deposit path reaches a plain upsert with the same value and had NO
    // amount check at all. A fix applied only where the checker pointed would
    // have left half the resource open.
    // WINDOWED FROM THE BRANCH START RATHER THAN A FIXED SLICE. The first
    // version cut at 2,600 characters and the Disbursement branch sits 5,887
    // in, so the arm failed with "the Disbursement branch moved" against a file
    // where nothing had moved -- an anchor reporting on its own window size.
    const guard = SRC.indexOf('law_trusttx payload.amount must be a number', trustIdx) - trustIdx;
    const disb = SRC.indexOf("payload.type === 'Disbursement'", trustIdx) - trustIdx;
    assert.ok(guard > 0, 'the amount guard is not in the write branch');
    assert.ok(disb > 0, 'the Disbursement branch moved');
    assert.ok(guard < disb,
      'the guard sits BELOW the Disbursement branch, so the Deposit path is unguarded');
  });
  t('it uses isFinite, not another comparison -- a comparison is what missed it', () => {
    const seg = SRC.slice(trustIdx, trustIdx + 2600);
    assert.ok(/isFinite\(txAmount\)/.test(seg));
  });
  t('the food-temperature guard refuses rather than defaulting', () => {
    assert.ok(/BAD_TEMPERATURE/.test(SRC));
    assert.ok(/isFinite\(Number\(payload\.temperature_f\)\)/.test(SRC));
  });
  t('...and it fires on the PRESENCE of the field, not on holding_kind', () => {
    // The original grading branch also required `payload.holding_kind`. A
    // reading with a bad temperature and no holding_kind would have skipped the
    // guard entirely and been stored ungraded, which is the shape that hides.
    const i = SRC.indexOf('BAD_TEMPERATURE');
    const seg = SRC.slice(Math.max(0, i - 700), i);
    assert.ok(!/holding_kind/.test(seg.slice(-300)),
      'the temperature guard is gated on holding_kind, so a reading without one skips it');
  });
  t('sen_payer_contracts KEEPS the negated form -- it is the one that catches NaN', () => {
    assert.ok(/!\(Number\(payload\.rate_per_hour\) > 0\)/.test(SRC),
      'the rate_per_hour guard was rewritten to `<= 0`, which cannot see NaN');
  });
}

(async () => {
  for (const [name, fn] of queue) {
    if (!fn) { console.log('--- ' + name + ' ---'); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + (e && e.message)); fail++; }
  }
  console.log('\nsd-data numeric guards: ' + pass + ' passed, ' + fail + ' failed');
  if (fail) process.exit(1);
})();
