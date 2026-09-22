// api/_lib/deadline-period-count.test.js
//
// REQUIREMENT: a period count is PARSED from its raw value, so an absent
// count cannot become a legal deadline on the trigger date itself.
//
// ── THE DEFECT, AND WHY THE OBVIOUS FIX IS THE WRONG ONE ───────────────────
// Four sites in deadline-engine.js read `Number(x.count.value)` with no check
// of any kind. That coercion maps FOUR different inputs to the same 0:
//
//     Number(0)      0     a real zero
//     Number('')     0     an absent count
//     Number(null)   0     a missing field
//     Number([])     0     a malformed one
//
// and 0 is a LEGITIMATE count here: Md. Rule 2-311(b) has a zero-count limb
// whose deadline is the supplied date itself. So after the coercion there is
// nothing left to check -- the distinction the engine needs is already gone.
//
// THE FIRST ATTEMPT AT THIS FIX GUARDED THE COERCED RESULT with
// `!(countValue > 0)` and two suites went red on the spot: deadline-maryland
// and deadline-limb-scope both assert the zero-count limb works. The guard
// was refusing a real rule. The idea was right and the BOUNDARY was wrong,
// which is the whole of "parse, don't validate" -- validate the raw value,
// where the distinction still exists, not the number it collapses into.
//
// `'7 days'` is in here because it is the other half of the same trap:
// Number() gives NaN and refuses it, but parseInt() would have said 7 and
// computed a deadline from a string nobody parsed.

const path = require('path');
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const ROOT = path.join(__dirname, '..', '..');
const SRC = fs.readFileSync(path.join(ROOT, 'api/_lib/deadline-engine.js'), 'utf8');

// Extracted by brace balance rather than required, because the engine's
// exports do not include this helper and reaching into a module's private
// function through its exports would be testing a different thing.
function grab(name) {
  const start = SRC.indexOf('function ' + name + '(');
  assert.ok(start > 0, 'not found in deadline-engine.js: ' + name);
  let depth = 0;
  for (let i = start; i < SRC.length; i++) {
    if (SRC[i] === '{') depth++;
    else if (SRC[i] === '}') {
      depth--;
      if (depth === 0) return SRC.slice(start, i + 1);
    }
  }
  throw new Error('unbalanced: ' + name);
}

const ctx = {};
vm.createContext(ctx);
vm.runInContext(grab('periodCount'), ctx);

let pass = 0, fail = 0;
function t(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(s) { console.log('\n' + s); }

section('ACCEPTED -- and ZERO is the one that matters');

[[0, 'a real zero, which Md. Rule 2-311(b) genuinely uses'],
 [7, 'an ordinary count'],
 ['7', 'a numeric string, which the rule data does use'],
 ['0', 'zero written as a string']
].forEach(function (c) {
  t('accepts ' + JSON.stringify(c[0]) + ' -- ' + c[1], function () {
    const r = ctx.periodCount(c[0], 'R-1', 'the limb');
    assert.strictEqual(r.ok, true, JSON.stringify(r));
    assert.strictEqual(r.value, Number(c[0]));
  });
});

section('REFUSED -- every one of these is Number()-indistinguishable from 0 '
        + 'or silently wrong');

[['', "Number('') is 0, so an absent count became a deadline on the trigger date"],
 [null, 'Number(null) is 0, same result from a missing field'],
 [undefined, 'a missing key'],
 [[], 'Number([]) is 0 as well'],
 ['   ', 'whitespace coerces to 0 too'],
 ['7 days', 'Number is NaN, but parseInt would have said 7'],
 ['abc', 'plainly not a number'],
 [-3, 'a negative period'],
 [Infinity, 'non-finite'],
 [NaN, 'NaN -- and a `< 0` guard alone cannot see it']
].forEach(function (c) {
  t('refuses ' + JSON.stringify(c[0]) + ' -- ' + c[1], function () {
    const r = ctx.periodCount(c[0], 'R-1', 'the limb');
    assert.strictEqual(r.ok, false, 'ACCEPTED it: ' + JSON.stringify(r));
    assert.strictEqual(r.code, 'INVALID_PERIOD_COUNT');
    assert.match(r.message, /R-1/, 'the refusal does not name the rule, so '
      + 'nobody can find which rule to fix');
  });
});

section('THE DISTINCTION Number() DESTROYS, stated as an arm');

t('a real 0 and an absent count are the SAME after Number() and DIFFERENT '
  + 'after periodCount', function () {
    assert.strictEqual(Number(0), Number(''));          // the defect
    assert.strictEqual(ctx.periodCount(0, 'R', 'x').ok, true);
    assert.strictEqual(ctx.periodCount('', 'R', 'x').ok, false);
  });

section('THE ENGINE ACTUALLY USES IT -- a helper nothing calls is not a fix');

// ── ASSERTED ON CODE, NOT ON TEXT, AND THESE TWO ARMS HAD TO LEARN IT ─────
// The first version searched the whole file for `Number(lb.count.value)` and
// for `!(countValue > 0)`. Both matched -- inside the COMMENTS that quote the
// old code to record what was replaced. The arms reported the defect as still
// present while the fix was in place and working, which is the same
// self-matching failure that bit a StoneDesk arm earlier the same day.
// Comments are stripped before matching, so an arm cannot be satisfied or
// defeated by prose about the thing it checks.
const CODE = SRC.replace(/^\s*\/\/.*$/gm, '');

t('both limb call sites parse rather than coerce', function () {
  assert.ok(!/Number\(lb\.count\.value\)/.test(CODE),
    'the limb loop still coerces with Number()');
  assert.ok(!/Number\(winner\.limb\.count\.value\)/.test(CODE),
    'count_override still re-coerces instead of reusing the parsed value');
  assert.match(CODE, /periodCount\(lb\.count && lb\.count\.value/,
    'the limb loop does not call periodCount');
});

t('computeBasePeriod keeps its own last-line guard, in the NaN-safe form',
  function () {
    const body = grab('computeBasePeriod').replace(/^\s*\/\/.*$/gm, '');
    assert.match(body, /!isFinite\(countValue\)/,
      'the non-finite arm is gone -- a `< 0` comparison cannot see NaN');
    assert.ok(!/!\(countValue > 0\)/.test(body),
      'the guard refuses zero again, which is a real Maryland rule');
    assert.match(body, /countValue < 0/,
      'the negative arm is gone');
  });

console.log('\n' + pass + ' passed, ' + fail + ' failed');
if (fail) { console.log('FAILURES ABOVE'); process.exit(1); }
