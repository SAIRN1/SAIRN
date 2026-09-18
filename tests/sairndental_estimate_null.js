// tests/sairndental_estimate_null.js
// REQUIREMENT: a procedure fee that cannot be read as a number produces NO
//   insurance estimate and NO contribution to a treatment-plan total -- never a
//   $0 estimate and never a silent zero inside a figure a patient is asked to
//   accept
//
// Run:  node tests/sairndental_estimate_null.js
//
// ── WHY THIS EXISTS ────────────────────────────────────────────────────────
// computeEstimatedInsurance carried `Number(amount)||0`, and tpItemMoney
// carried `Number(item.fee)||0`. Both were flagged in the previous pass and
// left, because the PERSISTING path was already safe -- addChargeEntry passes an
// amount dntMoneyIn() has validated. The three DISPLAY callers were not: they
// pass a procedure's `default_fee` or a plan line's `fee`, practice-entered
// numbers that can be blank, carry a stray letter, or arrive as a pasted
// '1,200'.
//
// THE TREATMENT-PLAN TOTAL IS THE ONE THAT MATTERS. A plan is what a patient is
// asked to accept and sign. A line whose fee could not be read contributed a
// silent 0 to the plan's fee, insurance and patient-portion totals, so the
// figure presented to the patient was short by that line with nothing on screen
// saying so. `pf+=null` is `pf+0` in JavaScript -- the total comes out
// authoritative and wrong, which is the exact shape api/_lib/dnt-rollup.js
// refuses one layer up and the reason its rule is "NEVER 0. Zero is a
// measurement."
//
// DNT_HTML points this at a mutated copy so a negative control can prove the
// arms bite without patching the tracked file.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const html = fs.readFileSync(process.env.DNT_HTML
  || path.join(__dirname, '..', 'sairndental.html'), 'utf8')
  .replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function grab(sig, terminator) {
  const at = html.indexOf(sig);
  assert.ok(at > 0, 'not found in sairndental.html: ' + sig);
  const end = html.indexOf(terminator, at);
  assert.ok(end > at, 'terminator not found after ' + sig);
  return html.slice(at, end + terminator.length);
}

// The real functions, with only the coverage lookup and the patient stubbed --
// those are the app's data, not the arithmetic under test.
function ctxFor(coveragePercent, found) {
  const ctx = {
    console: console,
    lookupCoverage: () => ({ coveragePercent: coveragePercent, found: found }),
    H: (s) => String(s || ''),
  };
  vm.createContext(ctx);
  vm.runInContext([
    grab('function dntMoneyIn(v){', '\n}\n'),
    grab('function computeEstimatedInsurance(amount, payer, procedureTypeId){', '\n}\n'),
    grab('function tpItemMoney(item,patient){', '\n}\n'),
    grab('function tpPlanTotals(plan){', '\n}\n'),
    grab('function tpUnreadableNote(tot){', '\n}\n'),
    'function tpPatient(){return {insurance_payer:"Delta"};}',
  ].join('\n'), ctx);
  return ctx;
}

const UNREADABLE = [undefined, null, '', '   ', 'abc', '1,200', '$100', '12abc', true, [], -5];

// ---------------------------------------------------------------------------
section('1. THE ESTIMATE ITSELF');

test('an unreadable fee yields amount null and unreadable_fee true', () => {
  const c = ctxFor(50, true);
  UNREADABLE.forEach((v) => {
    const est = c.computeEstimatedInsurance(v, 'Delta', 'PR-1');
    assert.strictEqual(est.amount, null, 'accepted ' + JSON.stringify(String(v)));
    assert.strictEqual(est.unreadable_fee, true, 'not flagged: ' + JSON.stringify(String(v)));
  });
});

test('a readable fee still estimates, and a REAL zero still estimates zero', () => {
  const c = ctxFor(50, true);
  assert.strictEqual(c.computeEstimatedInsurance(200, 'Delta', 'PR-1').amount, 100);
  const z = c.computeEstimatedInsurance(0, 'Delta', 'PR-1');
  assert.strictEqual(z.amount, 0, 'a measured zero fee must still produce a zero estimate');
  assert.strictEqual(z.unreadable_fee, false, 'a measured zero was flagged unreadable');
});

// `found` answers "is there a coverage rule", which is about the PAYER. Merging
// the two would leave a caller unable to tell a normal absence of a rule from a
// data-entry error somebody has to go and fix.
test('`found` is NOT overloaded -- it still answers the payer question', () => {
  const noRule = ctxFor(50, false);
  const est = noRule.computeEstimatedInsurance('abc', 'Delta', 'PR-1');
  assert.strictEqual(est.found, false);
  assert.strictEqual(est.unreadable_fee, true);
  const withRule = ctxFor(50, true);
  assert.strictEqual(withRule.computeEstimatedInsurance('abc', 'Delta', 'PR-1').found, true,
    'an unreadable fee changed the answer to a question about the payer');
});

// ---------------------------------------------------------------------------
section('2. THE PLAN TOTAL: counted, never added');

test('an unreadable line contributes NOTHING and is COUNTED', () => {
  const c = ctxFor(50, true);
  const tot = c.tpPlanTotals({ patient_id: 'P1', items: [
    { fee: 200, procedure_type_id: 'PR-1', phase: 1 },
    { fee: '1,200', procedure_type_id: 'PR-2', phase: 1 },   // parseFloat would say 1
    { fee: '', procedure_type_id: 'PR-3', phase: 1 },
  ] });
  assert.strictEqual(tot.fee, 200, 'an unreadable fee leaked into the plan total: ' + tot.fee);
  assert.strictEqual(tot.insurance, 100);
  assert.strictEqual(tot.unreadable, 2, 'the unreadable lines are not counted');
  assert.strictEqual(tot.complete, false, 'a short total reported itself complete');
  // An unreadable line has no coverage answer either, so it counts as uncovered.
  //
  // ── AND A RECORDED NON-FINDING, BECAUSE THE HONEST ANSWER IS "EQUIVALENT" ─
  // Deleting the `return` from the unreadable branch is an EQUIVALENT MUTANT on
  // this code, and no assertion here kills it -- correctly. The line then falls
  // through to `fee+=m.fee` with m.fee === null, and `fee+=null` is `fee+0`; it
  // also reaches `if(!m.covered)uncovered++`, and m.covered is false for an
  // unreadable line, so `uncovered` lands on the same number by the other route.
  // Identical output, every field.
  //
  // I WROTE AN ARM TO KILL IT FIRST AND IT DID NOT, which is the useful part.
  // Contorting a suite until an equivalent mutant dies produces an assertion
  // that pins an implementation detail and calls it a behaviour. The `return`
  // stays because it states the intent and because it keeps holding if
  // `covered` ever becomes true for an unreadable line -- not because a test
  // can currently tell the difference.
  assert.strictEqual(tot.uncovered, 2,
    'an unreadable line is not counted as uncovered');
});

test('a plan with every fee readable is COMPLETE', () => {
  const c = ctxFor(50, true);
  const tot = c.tpPlanTotals({ patient_id: 'P1', items: [
    { fee: 200, procedure_type_id: 'PR-1' }, { fee: 100, procedure_type_id: 'PR-2' },
  ] });
  assert.strictEqual(tot.fee, 300);
  assert.strictEqual(tot.unreadable, 0);
  assert.strictEqual(tot.complete, true);
});

test('NULL IS NEVER ADDED -- the +0 coercion is the whole defect', () => {
  const c = ctxFor(50, true);
  const m = c.tpItemMoney({ fee: 'abc', procedure_type_id: 'PR-1' }, { insurance_payer: 'Delta' });
  assert.strictEqual(m.fee, null, 'an unreadable line reports a number');
  assert.strictEqual(m.insurance, null);
  assert.strictEqual(m.patient, null);
  assert.strictEqual(m.unreadable, true);
  // The proof that the sum would have been silently wrong: 0 + null === 0.
  assert.strictEqual(0 + m.fee, 0, 'JavaScript changed; the premise of this arm is gone');
});

// ---------------------------------------------------------------------------
section('3. THE SCREEN SAYS SO -- a count nobody renders is the same omission');

test('the disclosure renders whenever a total is short', () => {
  const c = ctxFor(50, true);
  const tot = c.tpPlanTotals({ patient_id: 'P1', items: [
    { fee: 200, procedure_type_id: 'PR-1' }, { fee: 'abc', procedure_type_id: 'PR-2' },
  ] });
  const note = c.tpUnreadableNote(tot);
  assert.ok(/1 item/.test(note), 'the count is missing: ' + note);
  assert.ok(/NOT included in the totals/.test(note), 'it does not say they are excluded: ' + note);
  assert.ok(/short by an unknown amount/.test(note),
    'it does not say the total is short: ' + note);
});

test('...and renders NOTHING when the plan is complete', () => {
  const c = ctxFor(50, true);
  const tot = c.tpPlanTotals({ patient_id: 'P1', items: [{ fee: 200, procedure_type_id: 'PR-1' }] });
  assert.strictEqual(c.tpUnreadableNote(tot), '',
    'a warning on every plan is a warning nobody reads');
});

test('EVERY place a plan total is shown carries the disclosure', () => {
  // Three render sites today. A fourth added without it is the defect returning,
  // so the count is pinned rather than the sites listed loosely.
  const sites = html.split('\n').filter((l) => /tpPlanTotals\(/.test(l));
  assert.ok(sites.length >= 3, 'the plan-total render sites moved: ' + sites.length);
  assert.ok(/tpUnreadableNote\(tot\)/.test(html),
    'the builder total does not carry the disclosure');
  assert.ok(/fee\(s\) UNREADABLE &mdash; total is short/.test(html),
    'the plan LIST column does not disclose a short total');
  // The phase subtotal must skip too, or a phase is short while the plan says so.
  const detail = grab('function openTxPlanDetail(', '\n}\n');
  assert.ok(/if\(!m\.unreadable\)\{pf\+=m\.fee/.test(detail),
    'the phase subtotal still adds an unreadable line, so a phase is short with '
    + 'nothing beside it saying so');
});

// ---------------------------------------------------------------------------
section('4. THE TWO DISPLAY NOTES');

test('both coverage notes check unreadable BEFORE found', () => {
  // Under `found` it renders "Estimated insurance: $0.00" -- a claim about the
  // payer made from a fee nobody could read.
  const hits = html.split('est.unreadable_fee').length - 1;
  assert.ok(hits >= 2, 'only ' + hits + ' of the two coverage notes check the unreadable case');
  assert.ok(/DNT_UNREADABLE_FEE_NOTE/.test(html), 'there is no shared sentence for it');
  // TERMINATED ON THE SEMICOLON, NOT THE NEWLINE. The first version of this arm
  // grabbed to '\n' and the constant spans two lines, so it tested the first
  // half of its own subject and reported a FALSE NEGATIVE -- the mirror of the
  // existence-assertion false positives caught elsewhere this session, and just
  // as capable of sending somebody to fix code that is already right.
  const note = grab('var DNT_UNREADABLE_FEE_NOTE=', "fee.';");
  assert.ok(/not a \$0 estimate/.test(note),
    'the sentence does not rule out a zero estimate having been shown: ' + note);
  assert.ok(/NO estimate is shown/.test(note),
    'the sentence does not say that no estimate is shown: ' + note);
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' ESTIMATE-NULL ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
