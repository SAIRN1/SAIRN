// tests/sairnbiz_1099_threshold.js
//
//   node tests/sairnbiz_1099_threshold.js
//
// THE 1099 THRESHOLD, WHICH WAS $600 AND HAD BEEN WRONG SINCE 1 JANUARY 2026.
//
// SAIRNbiz's vendor screen counted a vendor as 1099-required at $600 YTD. That
// figure had stood since 1954 and stopped being right for payments made after
// 31 December 2025:
//
//   IRS, Instructions for Forms 1099-MISC and 1099-NEC (Rev. December 2026):
//   "For tax years beginning after 2025, the minimum threshold amount for
//   reporting certain payments required to be reported on certain information
//   returns and/or perform backup withholding on those payments increased to
//   $2,000 and may be adjusted for inflation beginning in calendar year 2027."
//   P.L. 119-21.
//
// ── WHY THESE ARMS EXIST RATHER THAN A ONE-LINE CONSTANT SWAP ─────────────
// Swapping 600 for 2000 is right for 2026 and wrong twice:
//
//   * it is wrong for 2025 data, which this app can still be opened on, and
//     the YTD figure is keyed on `new Date().getFullYear()`;
//   * it goes STALE IN 2027, because indexing begins that year -- which is
//     exactly how 600 became wrong, quietly, over seventy-one years. A second
//     hardcoded constant repeats the defect one indexation later.
//
// So the threshold is year-keyed and 2027+ is returned as a BASE with
// certain:false, and the screen says so. The arms below pin all three states,
// and the third is the one a constant cannot express.
//
// ── WHAT IS NOT ASSERTED ─────────────────────────────────────────────────
// Not that any vendor is or is not 1099-required. These arms check the
// threshold the app applies and what it tells a reader about it.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const REPO = path.dirname(__dirname);
const src = fs.readFileSync(path.join(REPO, 'sairnbiz.html'), 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

// Lift the function out of the app rather than reimplementing it. A copy in
// the test is a second declaration of the answer and drifts from the first.
function lift(name) {
  const at = src.indexOf('function ' + name + '(');
  assert.notStrictEqual(at, -1, 'function ' + name + ' not found in sairnbiz.html');
  // to the closing brace at column 0
  const end = src.indexOf('\n}', at);
  assert.notStrictEqual(end, -1, name + ' has no column-0 closing brace');
  return src.slice(at, end + 2);
}

const ctx = vm.createContext({});
vm.runInContext(lift('sb1099Threshold'), ctx);

(function () {
  console.log('SAIRNBIZ 1099 THRESHOLD -- $600 before 2026, $2,000 from 2026');

  section('THE THREE STATES');
  test('2025 and earlier is $600', function () {
    [2020, 2024, 2025].forEach(function (y) {
      const t = ctx.sb1099Threshold(y);
      assert.strictEqual(t.amount, 600, y + ' returned ' + t.amount);
      assert.strictEqual(t.certain, true, y + ' should be certain');
    });
  });

  test('2026 is $2,000 and CERTAIN', function () {
    const t = ctx.sb1099Threshold(2026);
    assert.strictEqual(t.amount, 2000, 'got ' + t.amount);
    assert.strictEqual(t.certain, true);
    assert.ok(/119-21|December 2026/.test(t.note),
      'the 2026 note does not cite the authority: ' + t.note);
  });

  test('2027 and beyond is NOT certain -- indexing starts that year', function () {
    [2027, 2030, 2040].forEach(function (y) {
      const t = ctx.sb1099Threshold(y);
      assert.strictEqual(t.certain, false,
        y + ' was reported as certain. Indexing begins in calendar year 2027, '
        + 'so the published figure for ' + y + ' is not knowable from here -- '
        + 'and a hardcoded 2000 going stale is how 600 got here.');
      assert.ok(/inflation/i.test(t.note) && String(t.note).indexOf(String(y)) !== -1,
        'the ' + y + ' note does not name the year or the indexing: ' + t.note);
    });
  });

  test('the uncertain years still return a usable FLOOR, not null', function () {
    // A null would blank the screen, and a blank threshold is read as "no
    // threshold" -- which under-files, the direction this whole feature exists
    // to prevent.
    assert.strictEqual(ctx.sb1099Threshold(2030).amount, 2000);
  });

  section('THE APP USES IT -- a correct function nothing calls is not a fix');
  test('the vendor count compares against the threshold, not a literal', function () {
    assert.ok(/spendOf\(x\)\s*>=\s*thr\.amount/.test(src),
      'rVends no longer compares against thr.amount');
    assert.ok(!/spendOf\(x\)\s*>=\s*600/.test(src),
      'a literal 600 comparison is back in rVends');
  });
  test('the at-risk disclosure uses the same threshold', function () {
    assert.ok(/spendOf\(x\)<thr\.amount&&\(spendOf\(x\)\+u\)>=thr\.amount/.test(src),
      'the undated-prior-year disclosure is back on a literal, so it would '
      + 'name vendors against a different threshold than the count above it');
  });
  test('the KPI subtitle is WRITTEN from the threshold, not typed into markup',
    function () {
      assert.ok(!/\$600\+ paid/.test(src),
        'the markup still hardcodes "$600+ paid" under the 1099 tile -- a '
        + 'screen showing a figure the computation is not using');
      assert.ok(/vn-1099-sub/.test(src) && /sub\.textContent\s*=\s*fmt\(thr\.amount\)/.test(src),
        'the subtitle is no longer derived from thr.amount');
    });
  test('an uncertain year is visibly marked on the tile, not silently shown',
    function () {
      assert.ok(/thr\.certain\?''\:' \(base -- see note\)'/.test(src)
                || /certain\s*\?\s*''\s*:/.test(src),
        'the subtitle no longer distinguishes a certain threshold from a base');
    });

  section('CONTROL -- these arms must be able to fail');
  test('the lifted function is the real one and really runs', function () {
    assert.strictEqual(typeof ctx.sb1099Threshold, 'function');
    // Without this, every arm above is satisfied by a stub returning anything.
    assert.notStrictEqual(ctx.sb1099Threshold(2025).amount,
                          ctx.sb1099Threshold(2026).amount,
      'the function returns the same amount for 2025 and 2026, so it is not '
      + 'year-keyed at all and the arms above are checking one value twice');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
