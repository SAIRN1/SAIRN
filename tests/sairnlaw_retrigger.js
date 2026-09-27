// tests/sairnlaw_retrigger.js
//
// Run:  node tests/sairnlaw_retrigger.js
//
// REQUIREMENT: `applyRetrigger` must not report a DISPOSED motion as pending.
//
// ── WHY THIS SUITE EXISTS, AND WHY IT IS THE FIRST ONE ─────────────────────
// `applyRetrigger` implements FRAP 4(a)(4)(A) and its state analogues -- a
// qualifying post-judgment motion does not EXTEND the appeal period, it
// REPLACES the trigger. It is seeded for US federal (two rules), Ohio App.R.
// 4(B)(2) and Massachusetts Rule 12(a)(2); api/legal-deadlines.js passes
// `body.retrigger_events` into it and maps its `MOTION_PENDING` refusal to 422.
//
// **AND NOTHING HAS EVER DRIVEN IT.** No test anywhere named `applyRetrigger`,
// `MOTION_PENDING` or `retrigger_events` before this file. Found by
// tools/ghost_field_read_scan.py: the element field `disposition_date` is READ
// in a gate and is not written, keyed, quoted or declared anywhere in the repo
// -- no schema, no validator, no fixture, no document. A live, seeded,
// endpoint-wired path whose input contract existed only inside the one line
// that read it.
//
// ── THE DEFECT THAT WAS THERE ──────────────────────────────────────────────
// One filter decided everything: `!toUTC(e.disposition_date)`. `toUTC` returns
// null for anything not strictly `YYYY-MM-DD`, so `12/31/2026`, `Dec 31 2026`,
// `2026-13-45` and a misspelled key all came back as "undisposed" and the
// caller was told, with a 422, that the appeal period HAD NOT STARTED.
//
// THAT IS THE DIRECTION THAT LOSES THE APPEAL. Being told the clock has not
// begun, in a message specific enough to be believed, on a motion that was
// disposed weeks ago. Section B is the arm that would have caught it.
//
// Every date below is chosen to be unambiguous in every format, or deliberately
// ambiguous where that is the point.

'use strict';
const assert = require('assert');
const path = require('path');
const e = require(path.join(__dirname, '..', 'api', '_lib', 'deadline-engine.js'));

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (err) { console.log('  FAIL ' + name + '\n       ' + err.message); fail++; }
}
function section(t) { console.log('\n' + t); }

// The REAL federal spec, copied field-for-field from
// sql/sairnlaw_deadline_seed_us_federal.json (frap-4a1A-civil-notice-of-appeal)
// rather than invented -- a fixture that does not match the seeded shape tests
// a rule nobody ships.
const FRAP = {
  retrigger: {
    on_events: ['rule_50b_motion', 'rule_52b_motion', 'rule_59_motion_new_trial',
                'rule_59_motion_alter_or_amend', 'rule_60_motion_within_28_days'],
    substitute_trigger: 'entry_of_order_disposing_of_last_remaining_motion',
    authority: 'Fed. R. App. P. 4(a)(4)(A)'
  }
};
const JUDGMENT = '2026-03-02';

function run(events, rule) {
  return e.applyRetrigger(rule || FRAP, JUDGMENT, { retrigger_events: events });
}

console.log('SAIRNlaw -- a disposed motion is never reported as pending\n');

section('A. the paths that were already right');
test('A1. a rule with no retrigger spec passes the trigger through untouched', () => {
  const r = e.applyRetrigger({}, JUDGMENT, { retrigger_events: [
    { event: 'rule_59_motion_new_trial', disposition_date: '2026-04-01' }] });
  assert.strictEqual(r.ok, true);
  assert.strictEqual(r.date, JUDGMENT);
  assert.strictEqual(r.retriggered, false);
});
test('A2. an event that is NOT in on_events does not retrigger -- a motion the '
  + 'rule does not name must not move an appeal deadline', () => {
  const r = run([{ event: 'motion_for_attorney_fees', disposition_date: '2026-04-01' }]);
  assert.strictEqual(r.ok, true);
  assert.strictEqual(r.date, JUDGMENT);
  assert.strictEqual(r.retriggered, false);
});
test('A3. one disposed qualifying motion REPLACES the trigger with its '
  + 'disposition date and reports the authority', () => {
  const r = run([{ event: 'rule_59_motion_new_trial', disposition_date: '2026-04-01' }]);
  assert.strictEqual(r.ok, true, JSON.stringify(r));
  assert.strictEqual(r.date, '2026-04-01');
  assert.strictEqual(r.retriggered, true);
  assert.strictEqual(r.replaced, JUDGMENT);
  assert.strictEqual(r.authority, 'Fed. R. App. P. 4(a)(4)(A)');
});
test('A4. "the LAST such remaining motion" governs -- the latest disposition '
  + 'wins regardless of the order sent', () => {
  const r = run([
    { event: 'rule_50b_motion', disposition_date: '2026-06-11' },
    { event: 'rule_59_motion_new_trial', disposition_date: '2026-04-01' },
    { event: 'rule_52b_motion', disposition_date: '2026-05-02' }]);
  assert.strictEqual(r.date, '2026-06-11', JSON.stringify(r));
  assert.strictEqual(r.motions.length, 3);
});
test('A5. a genuinely pending motion still refuses MOTION_PENDING, and names '
  + 'which one -- this is the behaviour being preserved, not changed', () => {
  const r = run([
    { event: 'rule_59_motion_new_trial', disposition_date: '2026-04-01' },
    { event: 'rule_50b_motion' }]);
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.code, 'MOTION_PENDING');
  assert.deepStrictEqual(r.pending, ['rule_50b_motion']);
});
test('A6. ...and an explicit null or blank disposition is pending too, because '
  + '"we have not got an order yet" is how a docket records that', () => {
  for (const v of [null, '', '   ']) {
    const r = run([{ event: 'rule_50b_motion', disposition_date: v }]);
    assert.strictEqual(r.code, 'MOTION_PENDING', 'value ' + JSON.stringify(v));
  }
});

section('B. THE ARM THAT MATTERS: an unreadable date is not a pending motion');
test('B1. a US-format date on a DISPOSED motion is refused as '
  + 'BAD_DISPOSITION_DATE -- it used to answer MOTION_PENDING, i.e. "your '
  + 'appeal period has not started", on a motion decided months earlier', () => {
  const r = run([{ event: 'rule_59_motion_new_trial', disposition_date: '12/31/2026' }]);
  assert.strictEqual(r.ok, false, JSON.stringify(r));
  assert.strictEqual(r.code, 'BAD_DISPOSITION_DATE',
    'got ' + r.code + ' -- MOTION_PENDING here is the defect this suite exists for');
});
test('B2. ...and the refusal NAMES the offending value and the accepted format, '
  + 'because a caller who cannot see which field to fix will guess', () => {
  const r = run([{ event: 'rule_59_motion_new_trial', disposition_date: '12/31/2026' }]);
  assert.ok(/"12\/31\/2026"/.test(r.message), r.message);
  assert.ok(/YYYY-MM-DD/.test(r.message), r.message);
  assert.deepStrictEqual(r.malformed,
    [{ event: 'rule_59_motion_new_trial', disposition_date: '12/31/2026' }]);
});
test('B3. ...and it says IN THE MESSAGE that this is not the same answer as '
  + 'pending, so the distinction survives a copy-paste of the string', () => {
  const r = run([{ event: 'rule_50b_motion', disposition_date: 'Dec 31 2026' }]);
  assert.ok(/NOT the same answer/.test(r.message), r.message);
  assert.ok(/pending/.test(r.message), r.message);
});
test('B4. the shapes that pass the format regex and are still not dates -- '
  + '2026-13-45 has the right SHAPE and no such day exists', () => {
  for (const v of ['2026-13-45', '2026-02-30', '0000-00-00']) {
    const r = run([{ event: 'rule_50b_motion', disposition_date: v }]);
    assert.strictEqual(r.code, 'BAD_DISPOSITION_DATE', 'value ' + v + ' -> ' + r.code);
  }
});
test('B5. a NON-OBJECT element is refused, not read as pending -- '
  + 'retrigger_events is caller-supplied and ["rule_50b_motion"] is the '
  + 'obvious wrong shape to send', () => {
  const r = run(['rule_50b_motion']);
  // A bare string has no `event`, so it does not qualify in the first place and
  // the trigger passes through. What must NOT happen is a pending refusal built
  // from a shape this function cannot read.
  assert.notStrictEqual(r.code, 'MOTION_PENDING', JSON.stringify(r));
});
test('B6. one bad date among good ones refuses the WHOLE computation rather '
  + 'than quietly computing from the readable subset -- the excluded motion '
  + 'could be the last one, which is the one that governs', () => {
  const r = run([
    { event: 'rule_59_motion_new_trial', disposition_date: '2026-04-01' },
    { event: 'rule_50b_motion', disposition_date: '11/20/2026' }]);
  assert.strictEqual(r.code, 'BAD_DISPOSITION_DATE', JSON.stringify(r));
  assert.strictEqual(r.malformed.length, 1);
});
test('B7. BAD_DISPOSITION_DATE is checked BEFORE MOTION_PENDING, so a request '
  + 'with both gets the actionable answer -- a pending motion is the '
  + 'caller\'s docket, an unreadable date is the caller\'s typo', () => {
  const r = run([
    { event: 'rule_50b_motion' },
    { event: 'rule_59_motion_new_trial', disposition_date: '12/31/2026' }]);
  assert.strictEqual(r.code, 'BAD_DISPOSITION_DATE', JSON.stringify(r));
});

section('C. the endpoint maps the new code to 400, not 422');
{
  const fs = require('fs');
  const src = fs.readFileSync(path.join(__dirname, '..', 'api', 'legal-deadlines.js'), 'utf8');
  test('C1. MOTION_PENDING is still in the 422 list -- 422 means "the request '
    + 'is complete and the clock has not begun"', () => {
    assert.ok(/'MOTION_PENDING'/.test(src) && /!==\s*-1\s*\?\s*422/.test(src), 'mapping moved');
  });
  test('C2. BAD_DISPOSITION_DATE is NOT in that list, so it falls to 400 -- and '
    + 'the file NAMES it there, so the mapping is a decision rather than a '
    + 'default nobody chose', () => {
    const list = /\[([^\]]*)\]\.indexOf\(result\.code\)/.exec(src);
    assert.ok(list, 'the 422 list is gone -- this arm is now testing nothing');
    assert.ok(!/BAD_DISPOSITION_DATE/.test(list[1]),
      'BAD_DISPOSITION_DATE is in the 422 list: ' + list[1]);
    assert.ok(/BAD_DISPOSITION_DATE/.test(src),
      'the code is not mentioned in the endpoint at all, so its 400 is an '
      + 'accident of the default rather than a recorded choice');
  });
}

section('D. NEGATIVE CONTROLS -- both arms must be shown to fail');
test('D1. CONTROL: asserting an unreadable date yields MOTION_PENDING FAILS, '
  + 'so section B is distinguishing two codes and not passing on one', () => {
  let caught = 0;
  try {
    assert.strictEqual(
      run([{ event: 'rule_50b_motion', disposition_date: '12/31/2026' }]).code,
      'MOTION_PENDING');
  } catch (err) { caught++; }
  assert.strictEqual(caught, 1);
});
test('D2. CONTROL: asserting a GENUINELY pending motion yields '
  + 'BAD_DISPOSITION_DATE FAILS, so the new branch has not swallowed the old '
  + 'one -- a refusal that fires on everything is not a distinction', () => {
  let caught = 0;
  try {
    assert.strictEqual(run([{ event: 'rule_50b_motion' }]).code, 'BAD_DISPOSITION_DATE');
  } catch (err) { caught++; }
  assert.strictEqual(caught, 1);
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
