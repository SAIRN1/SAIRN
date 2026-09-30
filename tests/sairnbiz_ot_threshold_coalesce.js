// tests/sairnbiz_ot_threshold_coalesce.js
//
// REQUIREMENT: a rejectable overtime threshold is REPORTED as rejected, and the
//   value the user actually typed is what the validator sees.
//
// Run:  node tests/sairnbiz_ot_threshold_coalesce.js
//
// ── THE DEFECT, AND IT IS ONE LAYER ABOVE WHERE EVERY ARM DROVE ───────────
// sairnbiz.html:4959-4962, sbCfg():
//
//     return c ? { fy: c.fy || d.fy, ot: c.ot || d.ot, terms: c.terms || d.terms } : d;
//
// `0` and `''` are FALSY, so a user who types 0 -- or clears the field -- has
// their value replaced by 40 BEFORE sbOtThreshold() is ever called. The
// validation's `n <= 0` branch at :4988 is therefore UNREACHABLE for exactly
// those two values, and sbOtThresholdNote() at :4995 compares 40 against 40 and
// reports nothing.
//
// cody's own obligation text names this case as the reason the note exists:
// "a user who typed 0 would otherwise see a normal-looking column and believe
// the setting took effect." That is what happens today.
//
// THE EXISTING ARMS CANNOT SEE IT because they call sbOtThreshold() with a raw
// value. The bug is in what decides what raw ever is. EVERY ARM BELOW DRIVES
// THE REAL CHAIN FROM STORED CONFIG -- sbCfg -> sbOtThreshold -> the note --
// which is the only ordering in which the defect exists.
//
// ── WHAT IS AND IS NOT WRONG ──────────────────────────────────────────────
// 0 and '' both land on 40, the statutory default, so no PAY FIGURE is wrong.
// What is wrong is the silence: the one value cody singles out as most
// dangerous to accept quietly is accepted quietly.

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const SRC = fs.readFileSync(path.join(__dirname, '..', 'sairnbiz.html'), 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

// ── THE THREE FUNCTIONS, LIFTED OUT OF THE REAL FILE ──────────────────────
// Extracted by name from sairnbiz.html rather than re-typed here: a re-typed
// copy is a second source that drifts, and this suite would then be testing a
// paraphrase of the fix rather than the fix. If any extraction fails the suite
// refuses rather than falling back to a copy.
function extract(fnName) {
  const start = SRC.indexOf('function ' + fnName + '(');
  assert.ok(start !== -1, 'could not find function ' + fnName + ' in sairnbiz.html');
  let depth = 0, i = SRC.indexOf('{', start), end = -1;
  for (let k = i; k < SRC.length; k++) {
    if (SRC[k] === '{') depth++;
    else if (SRC[k] === '}') { depth--; if (depth === 0) { end = k; break; } }
  }
  assert.ok(end !== -1, 'unbalanced braces reading ' + fnName);
  return SRC.slice(start, end + 1);
}

const SOURCE = ['sbCfg', 'sbOtThreshold', 'sbOtThresholdNote'].map(extract).join('\n');

function chain(stored) {
  // `ld` is the app's storage reader; here it returns whatever the test stored.
  // Nothing else from the page is needed, which is itself the point: the defect
  // lives entirely inside these three functions.
  const sandbox = new Function('ld', SOURCE + '\n'
    + 'return { threshold: sbOtThreshold(), note: sbOtThresholdNote(), '
    + 'rawSeen: sbCfg().ot };');
  return sandbox(function () { return stored; });
}

function reportsRejected(note) {
  return /NOT used/.test(note);
}

(async () => {

section('1. THE DEFECT -- a rejectable value must be REPORTED, not swallowed');

test('a typed 0 falls back to 40 AND SAYS SO', () => {
  const r = chain({ ot: 0 });
  assert.strictEqual(r.threshold, 40, 'threshold = ' + r.threshold);
  assert.ok(reportsRejected(r.note),
    'a user who typed 0 is told nothing. sbOtThreshold saw '
    + JSON.stringify(r.rawSeen) + ' and the note reads: ' + r.note);
});

test('a CLEARED field falls back to 40 and is NOT reported -- the stated rule', () => {
  // THIS ARM ASSERTED THE OPPOSITE UNTIL IT WAS DRIVEN, and the correction is
  // cody's to make, not mine: "A blank setting is deliberately NOT reported as
  // rejected -- an absent setting is not a typo." A cleared field IS blank, and
  // sbOtThresholdNote's `String(raw).trim() !== ''` implements exactly that.
  //
  // So '' is NOT part of the defect. The defect is the typed 0 alone: 0 is a
  // value somebody chose, it is outside 1-168, and it was being swallowed.
  // Bundling '' into the finding would have overstated it.
  //
  // The fix still changes what the validator SEES for '' -- rawSeen is now ''
  // rather than 40 -- which is harmless and is pinned by the arm below so a
  // later change cannot start reporting blanks without somebody deciding to.
  const r = chain({ ot: '' });
  assert.strictEqual(r.threshold, 40);
  assert.ok(!reportsRejected(r.note),
    'a blank setting is now reported as a rejection, which contradicts the '
    + 'stated rule that an absent setting is not a typo: ' + r.note);
});

test('...and the validator SEES the typed value, not a substitute', () => {
  // The assertion that pins the FIX rather than its symptom. If sbCfg keeps
  // coalescing, rawSeen is 40 and the note can never know a 0 was typed.
  assert.strictEqual(chain({ ot: 0 }).rawSeen, 0,
    'sbCfg replaced the typed 0 before validation could see it');
  assert.strictEqual(chain({ ot: '' }).rawSeen, '',
    'sbCfg replaced the cleared field before validation could see it');
});

// ── A CLEARED FIELD IS REPORTED TOO (2026-09-30) ─────────────────────────
// THIS ARM EXISTS BECAUSE THE LIVE RUN FOUND WHAT THIS SUITE HAD EXCUSED.
// Driven on the deployed URL against SB-TEST-2026: typing 0 and saving
// reported correctly; CLEARING the box and saving said only "Overtime is
// computed above 40 hours per week." An earlier version of this file called
// that "harmless for the verdict", and it is not.
//
// saveSettings() stores `$('ss-ot').value`, so a cleared box PERSISTS as the
// empty string, and loadSettings() puts it straight back -- the Shop Settings
// screen shows an EMPTY overtime box while payroll computes at 40. One stored
// setting, two answers on two screens. Same shape as SAIRNbuild's 0% markup
// rendering as 18% on the bid form.
test('a SAVED-EMPTY threshold falls back to 40 AND SAYS SO', () => {
  const r = chain({ ot: '' });
  assert.strictEqual(r.threshold, 40, 'a cleared field must land on 40');
  assert.ok(/SAVED EMPTY/.test(r.note),
    'a user who cleared the box is told nothing about it. The Shop Settings '
    + 'screen will show an empty field while payroll uses 40. Note was: '
    + r.note);
});

test('a saved-empty note does NOT claim the value was out of range', () => {
  // '' is not "outside 1-168" -- it is absent from a setting somebody saved.
  // Reusing the out-of-range sentence would be a true refusal with a false
  // reason, which is worse than silence because it sends the reader to check
  // a number they never typed.
  const r = chain({ ot: '' });
  assert.ok(!/outside/.test(r.note), 'wrong reason given: ' + r.note);
});

section('2. WHAT MUST NOT CHANGE');

test('an ABSENT setting is NOT reported as rejected', () => {
  // cody's stated rule: "an absent setting is not a typo." A fresh licence with
  // no saved config, and a config saved before this key existed, are both
  // absent -- neither is a rejection.
  [null, { fy: 'January' }, { ot: undefined }].forEach((stored) => {
    const r = chain(stored);
    assert.strictEqual(r.threshold, 40, JSON.stringify(stored));
    assert.ok(!reportsRejected(r.note),
      'an absent setting was reported as rejected for ' + JSON.stringify(stored)
      + ': ' + r.note);
  });
});

test('every genuinely rejectable value still falls back AND is reported', () => {
  [-5, 'abc', 500, 169, -0.5].forEach((v) => {
    const r = chain({ ot: v });
    assert.strictEqual(r.threshold, 40, JSON.stringify(v) + ' -> ' + r.threshold);
    assert.ok(reportsRejected(r.note), JSON.stringify(v) + ': ' + r.note);
  });
});

test('every VALID value is honoured and NOT reported', () => {
  [[1, 1], [40, 40], [168, 168], [37.5, 37.5]].forEach(([v, want]) => {
    const r = chain({ ot: v });
    assert.strictEqual(r.threshold, want, JSON.stringify(v));
    assert.ok(!reportsRejected(r.note),
      'a valid threshold was reported as rejected: ' + JSON.stringify(v));
  });
});

test('the OTHER two config keys keep their defaults when absent', () => {
  // The fix touches how sbCfg substitutes. fy and terms are strings whose only
  // falsy value is '', and an empty string there is genuinely "unset" -- so
  // their behaviour must not move.
  const r = new Function('ld', SOURCE + '\nreturn sbCfg();')(
    function () { return null; });
  assert.strictEqual(r.fy, 'January');
  assert.strictEqual(r.terms, 'Net 30');
});

section('3. THE KNOWN-BAD CONTROL');

test('KNOWN-BAD CONTROL: the PRE-FIX note is caught if reintroduced', () => {
  // The note before 2026-09-30, written out rather than regex-patched onto the
  // new one. It excluded a blank from `rejected` explicitly, which is what the
  // live run on the deployed URL exposed.
  //
  // Without this control the two SAVED-EMPTY arms above prove only that the
  // current note happens to contain the phrase -- not that the phrase is
  // produced BY the branch that was added, and not that its absence is
  // detectable.
  const OLD_NOTE = "function sbOtThresholdNote(){"
    + "  var n=sbOtThreshold();"
    + "  var raw=sbCfg().ot;"
    + "  var rejected=(String(raw).trim()!=='' && Number(raw)!==n);"
    + "  return 'Overtime is computed above '+n+' hours per week'+"
    + "    (n!==40?' (set in Shop Settings, not the federal 40)':'')+"
    + "    (rejected?' -- the recorded setting '+JSON.stringify(String(raw))"
    + "      +' is outside 1-168 and was NOT used':'')+'.';"
    + "}";
  const patched = [extract('sbCfg'), extract('sbOtThreshold'), OLD_NOTE]
    .join(String.fromCharCode(10));
  const old = (stored) => new Function('ld', patched
    + String.fromCharCode(10)
    + 'return { threshold: sbOtThreshold(), note: sbOtThresholdNote() };')(
      function () { return stored; });

  const blank = old({ ot: '' });
  assert.ok(!/SAVED EMPTY/.test(blank.note),
    'the OLD note already reported a saved-empty threshold, so the arms above '
    + 'are not testing the new branch. Note was: ' + blank.note);
  // And the old note must still be RIGHT about everything it did cover --
  // otherwise this control is failing for its own reason.
  assert.ok(/NOT used/.test(old({ ot: 0 }).note),
    'the reconstructed OLD note does not even report a typed 0, so it is not '
    + 'the code that shipped and this control proves nothing');
});

test('KNOWN-BAD CONTROL: the || coalesce is CAUGHT if reintroduced', () => {
  // The OLD sbCfg, written out rather than regex-patched onto the new one: a
  // patch that produces broken code fails for its own reason and looks like
  // proof. This is the exact body that shipped before the fix.
  const OLD_SBCFG = "function sbCfg(){"
    + "  var d={fy:'January',ot:40,terms:'Net 30'};"
    + "  try{ var c=ld('sb_cfg',null);"
    + "    return c?{fy:c.fy||d.fy,ot:c.ot||d.ot,terms:c.terms||d.terms}:d;"
    + "  }catch(e){ return d; }"
    + "}";
  const NL2 = String.fromCharCode(10);
  const rest = ['sbOtThreshold', 'sbOtThresholdNote'].map(extract).join(NL2);
  const body = OLD_SBCFG + NL2 + rest + NL2
    + 'return { threshold: sbOtThreshold(), note: sbOtThresholdNote(), '
    + 'rawSeen: sbCfg().ot };';
  const r = new Function('ld', body)(function () { return { ot: 0 }; });
  assert.strictEqual(r.rawSeen, 40,
    'the old sbCfg did not swallow the 0, so this control is not reproducing '
    + 'the defect it exists to reproduce');
  assert.ok(!reportsRejected(r.note),
    'the old sbCfg still reported the rejection, so the arms above would pass '
    + 'with the bug present: ' + r.note);
  // ...and the SHIPPED one does not behave that way, which is the pairing.
  assert.strictEqual(chain({ ot: 0 }).rawSeen, 0,
    'the shipped sbCfg behaves like the old one');
});

test('...and the SHIPPED source no longer contains the falsy coalesce on ot', () => {
  const cfg = extract('sbCfg');
  assert.ok(!/ot:\s*c\.ot\s*\|\|/.test(cfg),
    'sbCfg still coalesces ot on falsiness: ' + cfg);
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' OT-THRESHOLD COALESCE ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);

})();
