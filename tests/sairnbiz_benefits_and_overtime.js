// tests/sairnbiz_benefits_and_overtime.js
//
// Run:  node tests/sairnbiz_benefits_and_overtime.js
//
// TWO CHANGES IN ONE PANEL'S NEIGHBOURHOOD, AND THEY FAIL DIFFERENTLY.
//
// (A) THE BENEFITS PLAN CARDS asserted things the app cannot know, to every
//     licence, in static markup. Three classes sat in one block and got three
//     treatments, which is the thing a future sweep is most likely to flatten:
//       * "Workers Comp: Active, BWC Ohio" -- a compliance assertion. REMOVED.
//         BWC is the OHIO Bureau of Workers' Compensation, one of four
//         monopolistic state funds, and "Active" asserts coverage is in force.
//       * "Employee Contrib. Avg 5.2%" and "Plan Assets (est.) $284,000" --
//         values that LOOK COMPUTED. REMOVED. An average implies a population
//         was summed; "(est.)" implies a method.
//       * provider names, premiums, renewal dates -- sample values that read as
//         sample values. KEPT and disclosed at block level.
//     The arms below hold all three, including that the rows still EXIST with a
//     not-tracked value rather than being deleted -- a card that quietly gets
//     shorter hides the absence instead of showing it.
//
// (B) THE OVERTIME THRESHOLD is read now. It was recorded and ignored, and the
//     on-screen reason for ignoring it -- "its hours are demo figures, not a
//     real store" -- stopped being true on 2026-09-15. A stale sentence was
//     holding a setting unwired on a premise that no longer existed.
//
// ── WHAT IS ACTUALLY WORTH DRIVING HERE ──────────────────────────────────
//
// 1. THE VALIDATION BOUNDS, because both ways of being wrong are silent. A
//    threshold of 0 makes EVERY recorded hour overtime and multiplies the week's
//    cost by 1.5; a threshold above 168 can never be reached so no hour is ever
//    overtime and the column reads 0 for ever. Neither looks wrong on screen.
//    Arms B3/B4 drive every rejected shape by name.
//
// 2. THAT BOTH SITES READ THE SAME NUMBER. rTS() renders the OT column and the
//    Est. Pay figure; csv('timesheet') writes the same two into a file somebody
//    costs a week against. Two copies of `t-40` are two places that can disagree
//    about what a person was paid. Arm C1 asserts no bare `t-40` survives.
//
// 3. THAT THE FUNCTION IS ACTUALLY REACHABLE FROM ITS CALLERS. It is defined at
//    ~:4959 and called at ~:3177 and ~:4844, which relies on hoisting inside one
//    script block. This app already carries a comment about `sairnCallClaude`
//    being declared in a SEPARATE IIFE and throwing a silent ReferenceError that
//    looked like a network failure. Arm C2 proves the arrangement by BLOCK, not
//    by eye.
//
// Set SB_HTML to a mutated copy for a negative control.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const html = fs.readFileSync(process.env.SB_HTML
  || path.join(__dirname, '..', 'sairnbiz.html'), 'utf8')
  .replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function grab(sig, terminator) {
  const at = html.indexOf(sig);
  assert.ok(at > 0, 'not found in sairnbiz.html: ' + sig);
  const end = html.indexOf(terminator, at);
  assert.ok(end > at, 'terminator not found after ' + sig);
  return html.slice(at, end + terminator.length);
}

// ── STRIPPING COMMENTS PROPERLY, AND THE LINE-PREFIX VERSION FAILED FIRST ──
// The arms below assert that certain strings are GONE from what the app renders.
// Every one of those strings is quoted verbatim in the comment that records
// removing it, so the arms must not read comments. The obvious filter -- drop
// lines starting with `//` or `<!--` -- went red against a correct file on the
// first run of this suite, because a multi-line `<!-- ... -->` block's
// CONTINUATION lines start with neither. Six of fourteen arms failed on prose.
//
// A REGEX WAS NOT USED, DELIBERATELY. tests/stonedesk_field_quote_wiring.js
// records two comment-strippers written for this and both deleted: a line filter
// that kept continuation lines (this exact bug), and a `/\*[\s\S]*?\*/` that
// matched across an unintended span and ate a real statement, taking a count
// from two to ZERO -- a false PASS in the other direction. So this is a state
// machine over one pass, which cannot over-reach: it only ever leaves a comment
// region when it sees that region's own terminator.
//
// IT IS NOT STRING-AWARE, and that limit is stated rather than hidden: a `//`
// inside a string literal would start a spurious line comment here. Checked for
// this file -- the arms all pass, and the strings being searched for are in
// markup rather than in JS literals, so the exposure is nil today. A suite
// asserting on JS string contents would need more than this.
const { stripComments } = require('./lib/strip_comments.js');
// Shared, because three suites grew three versions in one day and all three
// were wrong differently -- see that module's header. The naive inline version
// this replaces treated `/*` as a comment start anywhere, so
// `accept="image/*"` opened a block comment that swallowed the rest of the
// file and arm E1 failed against correct markup.
const codeOnly = stripComments(html);

console.log('SAIRNbiz -- the plan cards stop asserting Ohio, and the OT threshold is read');

// ── A. THE PLAN CARDS ────────────────────────────────────────────────────
section('A. the compliance assertion and the two look-computed figures');
test('A1. "BWC Ohio" appears in no rendered value', () => {
  assert.strictEqual(codeOnly.indexOf('BWC Ohio'), -1,
    'the Ohio Bureau of Workers\' Compensation is still named in markup shown to '
    + 'every licence, including employers in states it does not regulate');
});
test('A2. no row asserts workers-comp coverage is Active', () => {
  assert.ok(!/Workers Comp[^|]{0,80}Active/.test(codeOnly),
    'a workers-comp row still asserts Active. That is a statutory coverage status '
    + 'with penalties for a lapse, and this app holds no policy, carrier or '
    + 'effective date');
});
test('A3. the Workers Comp row still EXISTS and says what is not tracked', () => {
  // Deleting the row would hide the absence. The rule this app already uses is
  // that the app SAYS SO instead of showing a number.
  assert.ok(/Workers Comp/.test(codeOnly), 'the Workers Comp row was deleted rather than neutralised');
  const at = codeOnly.indexOf('Workers Comp');
  const row = codeOnly.slice(at, at + 400);
  assert.ok(/Not tracked/i.test(row), 'the Workers Comp row does not say it is not tracked: ' + row.slice(0, 200));
  assert.ok(/state-specific|state specific/i.test(row),
    'it does not say the regulator is state-specific, which is the half that was wrong');
});
test('A4. "Avg 5.2%" and "$284,000" appear in no rendered value', () => {
  ['5.2%', '284,000'].forEach(n => {
    assert.strictEqual(codeOnly.indexOf(n), -1,
      n + ' is still rendered. An average and an asset total are the two shapes on '
      + 'this panel a reader takes for measurements');
  });
});
test('A5. both 401(k) rows still exist and say NOT TRACKED', () => {
  ['Employee Contrib.', 'Plan Assets'].forEach(lbl => {
    const at = codeOnly.indexOf(lbl);
    assert.ok(at > 0, lbl + ' was deleted rather than neutralised');
    assert.ok(/Not tracked/i.test(codeOnly.slice(at, at + 350)),
      lbl + ' does not say it is not tracked');
  });
});
test('A6. the block carries an EXAMPLE-offering disclosure', () => {
  assert.ok(/EXAMPLE offering, not your plan/i.test(codeOnly),
    'the four cards carry no block-level disclosure, so the sample provider names '
    + 'and premiums still read as the customer\'s own plan');
  assert.ok(/shown to every SAIRNbiz licence/i.test(codeOnly),
    'the disclosure does not say the values are identical for every customer, '
    + 'which is the specific thing that made "BWC Ohio" wrong');
});
test('A7. THE ONE REAL NUMBER KEEPS ITS FIGURE -- $520 is used and stays', () => {
  // The sweep must not neutralise the value the KPIs actually fall back to.
  assert.ok(/\$520\/mo per employee/.test(codeOnly),
    'the $520 employer default lost its figure. It is the one value on these cards '
    + 'that a computation reads, and blanking it would break the KPI fallback');
  const at = codeOnly.indexOf('$520/mo per employee');
  assert.ok(/default/.test(codeOnly.slice(at, at + 260)),
    'the $520 line lost its own "default" disclosure');
});

// ── B. THE THRESHOLD, DRIVEN ─────────────────────────────────────────────
function otCtx(stored) {
  const src = [
    grab('function sbCfg(){', '\n}'),
    grab('function sbOtThreshold(){', '\n}'),
    grab('function sbOtThresholdNote(){', '\n}')
  ].join('\n\n');
  const ctx = {
    JSON, Object, Number, String, Math, isFinite,
    ld: (k, d) => (stored === undefined ? d : stored),
    console: { log() {}, warn() {} }
  };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(src, ctx, { filename: 'sairnbiz-ot-extract.js' });
  return ctx;
}

section('B. the threshold validates, and both ways of being wrong are refused');
test('B1. no stored config -> 40', () => {
  assert.strictEqual(otCtx(undefined).sbOtThreshold(), 40);
});
test('B2. a STRING from the number input is honoured', () => {
  // The input gives `.value`, so the stored value is '35' and never 35.
  assert.strictEqual(otCtx({ fy: 'January', ot: '35', terms: 'Net 30' }).sbOtThreshold(), 35);
});
test('B3. every unusable shape falls back to 40, by name', () => {
  const bad = { "'' (empty)": '', "'abc'": 'abc', '0': 0, "'0'": '0',
                '-5': -5, '169': 169, '1000': 1000, 'null': null };
  Object.keys(bad).forEach(label => {
    const got = otCtx({ fy: 'x', ot: bad[label], terms: 'y' }).sbOtThreshold();
    assert.strictEqual(got, 40,
      label + ' produced a threshold of ' + got + '. A threshold of 0 makes EVERY '
      + 'hour overtime and multiplies the week\'s cost by 1.5; one above 168 can '
      + 'never be reached so no hour is ever overtime. Neither looks wrong on screen');
  });
});
test('B4. the usable boundaries ARE honoured -- 1 and 168', () => {
  assert.strictEqual(otCtx({ fy: 'x', ot: 1, terms: 'y' }).sbOtThreshold(), 1);
  assert.strictEqual(otCtx({ fy: 'x', ot: 168, terms: 'y' }).sbOtThreshold(), 168,
    '168 is the hours in a week and is reachable; rejecting it would be an '
    + 'off-by-one in the refusal');
});
test('B5. the note names the number, and flags a non-federal one', () => {
  const n40 = otCtx(undefined).sbOtThresholdNote();
  assert.ok(/above 40 hours per week/.test(n40), n40);
  assert.ok(!/Shop Settings/.test(n40), 'the default 40 should not be announced as a setting');
  const n35 = otCtx({ fy: 'x', ot: '35', terms: 'y' }).sbOtThresholdNote();
  assert.ok(/above 35 hours per week/.test(n35) && /Shop Settings/.test(n35),
    'a non-40 threshold must say a setting produced it -- otherwise a changed '
    + 'setting silently changes a money figure: ' + n35);
});
test('B6. A REJECTED VALUE IS REPORTED, not silently swapped for 40', () => {
  const n = otCtx({ fy: 'x', ot: '0', terms: 'y' }).sbOtThresholdNote();
  assert.ok(/was NOT used/.test(n) && /"0"/.test(n),
    'a rejected setting is replaced by 40 and nothing says so, so a user who typed '
    + '0 sees a normal-looking OT column and believes their setting took effect: ' + n);
});
test('B7. a blank setting is NOT reported as rejected -- it was never set', () => {
  const n = otCtx({ fy: 'x', ot: '', terms: 'y' }).sbOtThresholdNote();
  assert.ok(!/was NOT used/.test(n),
    'an empty setting is an absent one, and reporting it as rejected would put a '
    + 'complaint on every default install: ' + n);
});

// ── C. BOTH CALL SITES, AND REACHABILITY ─────────────────────────────────
section('C. one number, two callers, and the callers can see it');
test('C1. no bare `t-40` overtime computation survives', () => {
  const bare = codeOnly.split('\n').filter(l => /Math\.max\(0,\s*t\s*-\s*40\)/.test(l));
  assert.deepStrictEqual(bare, [],
    'a hardcoded 40 still computes overtime somewhere: ' + JSON.stringify(bare)
    + ' -- two places that can disagree about what somebody was paid');
  const calls = (codeOnly.match(/Math\.max\(0,\s*t\s*-\s*sbOtThreshold\(\)\)/g) || []).length;
  assert.strictEqual(calls, 2,
    'expected exactly 2 overtime computations through the helper (the panel and '
    + 'the CSV export), found ' + calls);
});
test('C2. REACHABILITY: definition and both callers are in ONE script block', () => {
  // The real failure this guards is the one this app already recorded:
  // sairnCallClaude declared in a SEPARATE IIFE, throwing a silent
  // ReferenceError that was caught and shown as a network error. Proven by
  // block boundaries rather than by reading.
  const blocks = [];
  const re = /<script[^>]*>/g;
  let m;
  while ((m = re.exec(html)) !== null) {
    const start = m.index + m[0].length;
    const end = html.indexOf('</script>', start);
    blocks.push([start, end === -1 ? html.length : end]);
  }
  const blockOf = (idx) => blocks.findIndex(([a, b]) => idx >= a && idx < b);
  const defAt = html.indexOf('function sbOtThreshold(){');
  const callIdx = [];
  const cre = /Math\.max\(0,\s*t\s*-\s*sbOtThreshold\(\)\)/g;
  while ((m = cre.exec(html)) !== null) callIdx.push(m.index);
  assert.strictEqual(callIdx.length, 2, 'expected 2 call sites, found ' + callIdx.length);
  const db = blockOf(defAt);
  assert.ok(db >= 0, 'the definition is outside every <script> block');
  callIdx.forEach((i, n) => assert.strictEqual(blockOf(i), db,
    'call site ' + (n + 1) + ' is in script block ' + blockOf(i) + ' and the '
    + 'definition is in block ' + db + ' -- function declarations do not hoist '
    + 'across blocks, so this is a ReferenceError at run time'));
});
test('C3. the threshold reaches the SCREEN and the FILE, not just the maths', () => {
  assert.ok(/sbOtThresholdNote\(\)/.test(codeOnly),
    'nothing displays which threshold produced the OT column');
  const uses = (codeOnly.match(/sbOtThresholdNote\(\)/g) || []).length;
  assert.ok(uses >= 2,
    'the note is used ' + uses + ' time(s); it belongs on the panel AND in the CSV, '
    + 'because an OT column in a spreadsheet is uninterpretable without the rule '
    + 'that made it');
});
test('C4. the Settings disclosure no longer claims the setting is unused', () => {
  const at = codeOnly.indexOf('Overtime Threshold (hrs/week)');
  assert.ok(at > 0, 'the Overtime Threshold input is gone');
  const near = codeOnly.slice(at, at + 900);
  assert.ok(!/not yet used/.test(near),
    'the input still says "not yet used" beside a setting that is now used');
  assert.ok(/<strong>Used\.<\/strong>/.test(near), 'it does not say it is used: ' + near.slice(0, 200));
});
test('C5. the save toast no longer calls the threshold unused', () => {
  const t = grab("function saveSettings(){", "\n}");
  assert.ok(!/overtime threshold are recorded but not yet used/.test(t),
    'saveSettings still reports the threshold as inert');
  assert.ok(/now drives the Timesheets OT column/.test(t),
    'the toast does not say what the threshold now affects: ' + t.slice(-300));
});

console.log('\n' + (fail ? 'FAIL' : 'ALL') + ' -- ' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
