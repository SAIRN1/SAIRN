// tests/sairnbuild_settings_prefill_coalesce.js
//
// REQUIREMENT: a default markup or retainage the builder deliberately STORED AS
//   ZERO is what the new-bid and new-draw forms prefill. Not 18. Not 10.
//
// Run:  node tests/sairnbuild_settings_prefill_coalesce.js
//
// ── THE DEFECT, FOUND BY THE SWEEP FOR THE sairnbiz CLASS ─────────────────
// sairnbuild.html, two sites:
//
//   :4660  $('bm-markup').value  = bldSettings().default_markup_pct    || 18;
//   :5586  $('drm-retpct').value = bldSettings().default_retainage_pct || 10;
//
// `0` is falsy. A builder who sets default markup to 0% -- a real setting, for
// cost-plus and time-and-materials work -- or retainage to 0% -- also real,
// plenty of contracts hold nothing back -- has that value STORED as 0 and
// DISPLAYED as 0% on the settings screen (:7286-7290, :7304, which all use
// `|| 0` and are correct), and then the form that consumes it prefills 18 or
// 10 instead.
//
// THIS IS WORSE THAN THE sairnbiz CASE IN ONE RESPECT. There the two figures
// both landed on the statutory 40 and only the silence was wrong. Here the
// settings panel and the form that uses the setting DISAGREE ABOUT THE SAME
// STORED NUMBER, on screen, at the same time -- and markup and retainage are
// both money. There is no validator to report a rejection, so the silent
// substitution is the entire defect rather than half of it.
//
// ── WHY THE CALL SITE AND NOT bldSettings() ───────────────────────────────
// bldSettings() at :7282 ALREADY supplies 18 and 10 when `bld_settings` is
// absent entirely -- `ld('bld_settings', {default_retainage_pct:10,
// default_markup_pct:18, cost_codes:[]})`. So the `|| 18` at the call site is
// redundant for the case it looks like it is for, and destructive for the case
// it is not. The fix substitutes on ABSENT only, exactly as sbCfg() now does.
//
// ── THE CODE UNDER TEST IS THE REAL BYTES ─────────────────────────────────
// bldSettings() is extracted from sairnbuild.html by name, and each prefill
// STATEMENT is extracted by its own target id from the real file. Nothing here
// is a retyped copy: a retyped copy is a second source that drifts, and this
// suite would then be asserting on a paraphrase of the fix. If an extraction
// fails, the suite REFUSES -- it does not fall back to a copy.

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const FILE = path.join(__dirname, '..', 'sairnbuild.html');
const SRC = fs.readFileSync(FILE, 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function extractFn(name, src) {
  const start = src.indexOf('function ' + name + '(');
  assert.ok(start !== -1, 'could not find function ' + name + ' in sairnbuild.html');
  let depth = 0, end = -1;
  for (let k = src.indexOf('{', start); k < src.length; k++) {
    if (src[k] === '{') depth++;
    else if (src[k] === '}') { depth--; if (depth === 0) { end = k; break; } }
  }
  assert.ok(end !== -1, 'unbalanced braces reading ' + name);
  return src.slice(start, end + 1);
}

// The prefill statement, taken out of the real file. It must resolve to
// exactly one statement: zero means the site moved and this suite is no longer
// testing it, more than one means it cannot say which it took. Both refuse
// rather than pick.
//
// TWO NAIVE VERSIONS OF THIS FAILED AND BOTH FAILURES ARE WORTH KEEPING.
//
//   (1) anchoring on the DOM id alone: `$('bm-markup').value=` appears TWICE,
//       here and at :4675 in the EDIT path, where `b.markup||0` is correct
//       because 0 stays 0. The id cannot tell them apart.
//   (2) anchoring on `bldSettings().default_markup_pct` and scanning BACKWARDS
//       to the nearest `;`, `{` or newline: the fixed expression wraps the
//       value in `(function(m){return m==null?18:m})(...)`, so the backward
//       scan stopped at that `{` and handed back `return m==null?18:m})(...);`
//       -- "Illegal return statement". The extractor was reading the shape of
//       the fix rather than the statement.
//
// So: start at the ASSIGNMENT, end at the first `;` OUTSIDE any bracket, and
// disambiguate the two sites by requiring the statement to read the settings
// getter. Exactly one must qualify; zero or several refuse.
function extractStatement(targetId, src) {
  const needle = "$('" + targetId + "').value=";
  const found = [];
  let from = 0;
  for (;;) {
    const at = src.indexOf(needle, from);
    if (at === -1) break;
    from = at + needle.length;
    let depth = 0, end = -1;
    for (let k = from; k < src.length; k++) {
      const c = src[k];
      if (c === '(' || c === '{' || c === '[') depth++;
      else if (c === ')' || c === '}' || c === ']') depth--;
      else if (c === ';' && depth === 0) { end = k; break; }
    }
    if (end === -1) continue;
    found.push(src.slice(at, end + 1));
  }
  const qualifying = found.filter(function (s) { return s.indexOf('bldSettings') !== -1; });
  assert.strictEqual(qualifying.length, 1,
    'expected exactly one `' + needle + '` statement that reads bldSettings(); '
    + 'found ' + qualifying.length + ' of ' + found.length + ' total. This '
    + 'suite can no longer say what it is testing.');
  return qualifying[0];
}

// ── the harness: real bldSettings, real prefill statement, stubbed DOM ─────
function prefill(targetId, field, stored, src) {
  const body = extractFn('bldSettings', src) + '\n'
    + 'var __v = null;\n'
    + 'function $(id){ return { set value(v){ __v = v; }, get value(){ return __v; } }; }\n'
    + extractStatement(targetId, src) + '\n'
    + 'return __v;';
  // `ld` is the app's storage reader. It is given the test's stored object, or
  // is left to return its own fallback when the key is genuinely absent --
  // which is the distinction the whole fix turns on.
  return new Function('ld', body)(function (key, fallback) {
    return stored === undefined ? fallback : stored;
  });
}

const CASES = [
  ['bm-markup', 'default_markup_pct', 18],
  ['drm-retpct', 'default_retainage_pct', 10],
];

section('A stored ZERO must survive to the form');
for (const [targetId, field, dflt] of CASES) {
  test(field + ': a stored 0 prefills 0, not ' + dflt, function () {
    const o = {}; o[field] = 0; o.cost_codes = [];
    const got = prefill(targetId, field, o, SRC);
    assert.strictEqual(got, 0,
      'stored 0 reached the form as ' + JSON.stringify(got)
      + '. The settings screen shows 0% and this form shows ' + got + '%.');
  });
}

section('A genuinely ABSENT setting must still default');
for (const [targetId, field, dflt] of CASES) {
  test(field + ': an absent key still defaults to ' + dflt, function () {
    // The whole bld_settings key missing -- bldSettings()'s own fallback.
    assert.strictEqual(prefill(targetId, field, undefined, SRC), dflt);
  });
  test(field + ': a present object missing the field defaults to ' + dflt,
    function () {
      // bld_settings exists from an older version without this field.
      assert.strictEqual(prefill(targetId, field, { cost_codes: [] }, SRC), dflt);
    });
  test(field + ': an explicit null defaults to ' + dflt, function () {
    const o = {}; o[field] = null;
    assert.strictEqual(prefill(targetId, field, o, SRC), dflt);
  });
}

section('Ordinary values are untouched');
for (const [targetId, field] of CASES) {
  for (const v of [1, 7.5, 33]) {
    test(field + ': ' + v + ' passes through', function () {
      const o = {}; o[field] = v;
      assert.strictEqual(prefill(targetId, field, o, SRC), v);
    });
  }
}

section('An empty string is NOT silently turned into the default');
// saveDefaults() at :7310-7311 stores parseFloat(value)||0, so '' can only
// reach the store as 0, never as ''. Asserting on '' would be asserting on a
// state the app cannot produce. What IS asserted is the reachable one: the
// stored 0 above. This section exists so the omission is deliberate and
// visible rather than an untested gap.
test('saveDefaults stores a cleared field as 0, so 0 is the reachable case',
  function () {
    const n = SRC.split("s.default_markup_pct=parseFloat($('dfm-markup').value)||0;").length - 1;
    assert.strictEqual(n, 1,
      'the saveDefaults line this reasoning rests on is no longer in the file '
      + '(' + n + ' matches), so the claim that 0 is the only reachable state '
      + 'is no longer checked');
  });

section('KNOWN-BAD CONTROL: reintroduce the falsy coalesce');
// Without this the arms above pass on any code that happens to be right, and
// say nothing about whether they can SEE the defect. The control mutates the
// real bytes back to the broken form and requires the zero arms to go red.
for (const [targetId, field, dflt] of CASES) {
  test(field + ': the broken `|| ' + dflt + '` form fails the zero arm',
    function () {
      const stmt = extractStatement(targetId, SRC);
      const at = SRC.indexOf(stmt);
      const brokenStmt = "$('" + targetId + "').value=bldSettings()."
        + field + '||' + dflt + ';';
      assert.notStrictEqual(brokenStmt, stmt,
        'the mutation did not change the statement, so this control mutates '
        + 'nothing');
      const broken = SRC.slice(0, at) + brokenStmt + SRC.slice(at + stmt.length);
      const o = {}; o[field] = 0; o.cost_codes = [];
      const got = prefill(targetId, field, o, broken);
      assert.strictEqual(got, dflt,
        'the reintroduced falsy coalesce did NOT produce ' + dflt
        + ' (got ' + JSON.stringify(got) + '), so this control is not '
        + 'exercising the defect and the arms above prove nothing');
      // And the absent case must still work in the broken version -- otherwise
      // the control is failing for its own reason rather than for the defect.
      assert.strictEqual(prefill(targetId, field, undefined, broken), dflt);
    });
}

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
