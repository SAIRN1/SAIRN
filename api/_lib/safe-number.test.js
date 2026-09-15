// api/_lib/safe-number.test.js
//
// Run:  node api/_lib/safe-number.test.js
//
// Control for the recombination in api/_lib/safe-number.js.
//
// THE ARMS THAT MATTER ARE NOT "does it parse a number". They are the three
// that justify the module existing at all:
//
//   * section 2 -- `''` is the FALLBACK for config and `null` for a
//     measurement. If those two ever agree, the split has collapsed and one of
//     the two jobs is being done wrong.
//   * section 4 -- parseFloat's PARTIAL PARSE is refused. `'1,200'` becoming 1
//     is the dangerous failure, because 1 is a plausible number and NaN is not.
//   * section 6 -- the module reproduces what every existing platform fix
//     already does. A recombination that changes an answer somewhere is a
//     REWRITE wearing a consolidation's name, and the migration would carry a
//     behaviour change nobody reviewed.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { configNumber, measureNumber, sumMeasurements } = require('./safe-number.js');

let pass = 0, fail = 0;
const queue = [];
function t(name, fn) { queue.push([name, fn]); }
function section(s) { queue.push([s, null]); }

// ════════════════════════════════════════════════════════════════════════════
section('1. the ordinary case, both functions');
t('a real number is returned unchanged', () => {
  assert.strictEqual(configNumber(42, 7), 42);
  assert.strictEqual(measureNumber(42), 42);
  assert.strictEqual(configNumber('42', 7), 42);
  assert.strictEqual(measureNumber('42'), 42);
});
t('whitespace around a number is fine -- that is formatting, not absence', () => {
  assert.strictEqual(configNumber(' 12 ', 7), 12);
  assert.strictEqual(measureNumber(' 12 '), 12);
});
t('a real ZERO survives both -- it is a value, not an absence', () => {
  assert.strictEqual(configNumber('0', 7), 0);
  assert.strictEqual(measureNumber('0'), 0);
  assert.strictEqual(measureNumber(0), 0);
});
t('negatives and decimals survive', () => {
  assert.strictEqual(measureNumber('-3.5'), -3.5);
  assert.strictEqual(configNumber('-3.5', 1), -3.5);
});

// ════════════════════════════════════════════════════════════════════════════
section('2. THE SPLIT -- the same input must give two different answers');
t("'' is the FALLBACK for config and NULL for a measurement", () => {
  assert.strictEqual(configNumber('', 7), 7);
  assert.strictEqual(measureNumber(''), null);
});
t('...and so are undefined and null', () => {
  assert.strictEqual(configNumber(undefined, 7), 7);
  assert.strictEqual(configNumber(null, 7), 7);
  assert.strictEqual(measureNumber(undefined), null);
  assert.strictEqual(measureNumber(null), null);
});
t('NEITHER ever returns a bare 0 for an absent value', () => {
  // The whole trap in one arm. `Number('')`, `Number(null)` and `Number([])`
  // are all 0, and 0 is a measurement.
  ['', null, undefined, [], false].forEach((v) => {
    assert.notStrictEqual(measureNumber(v), 0,
      JSON.stringify(v) + ' must not measure as zero');
  });
  assert.strictEqual(configNumber('', 0), 0,
    '...but a caller whose FALLBACK is 0 gets 0, because that is a choice');
});
t('a config whose legal range INCLUDES zero is the case that breaks the '
  + 'copied idiom', () => {
  // The rate limiters guard with `> 0`, so `Number('') === 0` is rejected by
  // accident. A jitter, a retry count or a grace period may legally be 0, and
  // the same shape then reads '' as "switched off, on purpose".
  assert.strictEqual(configNumber('', 500, { min: 0 }), 500,
    'blank must mean "nobody chose", never "chose zero"');
  assert.strictEqual(configNumber('0', 500, { min: 0 }), 0,
    '...and an explicit zero must still be honoured');
});

// ════════════════════════════════════════════════════════════════════════════
section('3. config: a value outside the range FALLS BACK, it is not clamped');
t('below min falls back', () => {
  assert.strictEqual(configNumber('-5', 10, { min: 0 }), 10);
});
t('above max falls back', () => {
  assert.strictEqual(configNumber('1000', 10, { max: 100 }), 10);
});
t('a non-integer falls back when integer is required', () => {
  assert.strictEqual(configNumber('2.5', 3, { integer: true }), 3);
  assert.strictEqual(configNumber('2', 3, { integer: true }), 2);
});
t('CLAMPING WOULD HIDE THE MISCONFIGURATION, which is why it falls back', () => {
  // A clamp returns a working system configured by nobody. The fallback is at
  // least the documented default, and the operator's wrong value is still
  // wrong in the environment where somebody can see it.
  assert.notStrictEqual(configNumber('1000', 10, { max: 100 }), 100);
});
t('a non-finite FALLBACK throws rather than returning NaN from the safe branch', () => {
  assert.throws(() => configNumber('x', NaN), /finite/);
  assert.throws(() => configNumber('x', undefined), /finite/);
});

// ════════════════════════════════════════════════════════════════════════════
section('4. parseFloat\'s PARTIAL PARSE is refused, and this is the sharp one');
t("'12abc' is UNREADABLE, not 12", () => {
  assert.strictEqual(measureNumber('12abc'), null,
    'parseFloat returns 12 here -- a plausible wrong number, which is worse '
    + 'than NaN because nothing looks wrong');
  assert.strictEqual(configNumber('12abc', 5), 5);
});
t("'1,200' is UNREADABLE, not 1", () => {
  assert.strictEqual(measureNumber('1,200'), null,
    'parseFloat returns 1 for a thousands-separated amount');
});
t("'$1,200' is unreadable under both, and stays unreadable", () => {
  assert.strictEqual(measureNumber('$1,200'), null);
});
t('the module does NOT strip currency or separators', () => {
  // Repairing it here would be this module guessing a locale: `1,200` is one
  // thousand two hundred in one and one-point-two in another.
  const src = fs.readFileSync(path.join(__dirname, 'safe-number.js'), 'utf8');
  assert.ok(!/replace\(\s*\/[^/]*[,$][^/]*\//.test(src),
    'no currency/separator stripping may creep in');
});
t('Infinity is not a measurement', () => {
  assert.strictEqual(measureNumber(Infinity), null);
  assert.strictEqual(measureNumber('Infinity'), null);
  assert.strictEqual(configNumber('Infinity', 9), 9);
});
t('booleans and arrays are not numbers, however JavaScript feels about it', () => {
  // Number(true) === 1, Number([]) === 0, Number(['5']) === 5.
  [true, false, [], ['5'], {}].forEach((v) => {
    assert.strictEqual(measureNumber(v), null, JSON.stringify(v));
    assert.strictEqual(configNumber(v, 9), 9, JSON.stringify(v));
  });
});

// ════════════════════════════════════════════════════════════════════════════
section('5. sumMeasurements NAMES what it could not read');
t('a clean column sums with zero unread', () => {
  assert.deepStrictEqual(sumMeasurements([1, 2, 3]), { value: 6, counted: 3, unread: 0 });
});
t('THE CASE FROM THE dnt_rollup REVIEW', () => {
  // 100 + null + '' + '$1,200' + '12abc' reported {value:112, rows:5} with
  // complete:true. The row count made it look well-founded.
  const out = sumMeasurements([100, null, '', '$1,200', '12abc']);
  assert.strictEqual(out.value, 100, 'only the one readable amount is summed');
  assert.strictEqual(out.counted, 1);
  assert.strictEqual(out.unread, 4,
    'and four unreadable amounts are NAMED rather than silently contributing 0');
});
t('an explicit zero is COUNTED, not unread', () => {
  const out = sumMeasurements([0, 0, null]);
  assert.deepStrictEqual(out, { value: 0, counted: 2, unread: 1 });
});
t('an empty column is honestly empty rather than an error', () => {
  assert.deepStrictEqual(sumMeasurements([]), { value: 0, counted: 0, unread: 0 });
  assert.deepStrictEqual(sumMeasurements(null), { value: 0, counted: 0, unread: 0 });
});

// ════════════════════════════════════════════════════════════════════════════
section('6. IT REPRODUCES EVERY EXISTING PLATFORM FIX -- consolidation, not rewrite');
t('ai-rate-limit.dailyLimit(): unset / blank / junk / 0 all fall back', () => {
  const D = 200;
  [undefined, '', 'abc', '0', '-5'].forEach((raw) => {
    assert.strictEqual(configNumber(raw, D, { min: 1 }), D, JSON.stringify(raw));
  });
  assert.strictEqual(configNumber('50', D, { min: 1 }), 50);
});
t('cron-jitter.jitterMs(): blank falls back, and ZERO IS HONOURED', () => {
  // The one existing fix that had to get the empty-string check right, because
  // it allows >= 0. This is the arm that would fail against the copied idiom.
  assert.strictEqual(configNumber('', 3000, { min: 0 }), 3000);
  assert.strictEqual(configNumber('0', 3000, { min: 0 }), 0);
  assert.strictEqual(configNumber('1500', 3000, { min: 0 }), 1500);
});
t('dental-bi.coerce(number): undefined / null / blank are null, junk is null', () => {
  [undefined, null, '', 'abc'].forEach((raw) => {
    assert.strictEqual(measureNumber(raw), null, JSON.stringify(raw));
  });
  assert.strictEqual(measureNumber('7.25'), 7.25);
});
t('the header CITES the call sites it consolidates, so the claim is checkable', () => {
  const src = fs.readFileSync(path.join(__dirname, 'safe-number.js'), 'utf8');
  ['ai-rate-limit.js', 'anon-rate-limit.js', 'cron-jitter.js', 'dental-bi.js']
    .forEach((f) => assert.ok(src.indexOf(f) !== -1, f + ' should be cited'));
});
t('...and those files still exist, so the citations are not rotting', () => {
  ['ai-rate-limit.js', 'anon-rate-limit.js', 'cron-jitter.js', 'dental-bi.js']
    .forEach((f) => assert.ok(fs.existsSync(path.join(__dirname, f)), f));
});

(async () => {
  for (const [name, fn] of queue) {
    if (!fn) { console.log('--- ' + name + ' ---'); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
  }
  console.log('\nsafe-number: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
