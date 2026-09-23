// tests/sf_operator_payee_match.js
//
// REQUIREMENT: ORC 2915.09(D)(1) forbids ANY compensation to a bingo game
//   operator. SAIRNveterans must raise the same confirm-these-are-separate
//   reason for a gaming-account cheque written to an operator by name as it
//   already raises for an operator who is also paid canteen staff.
//
// Run:  node tests/sf_operator_payee_match.js
//
// ── WHY THIS EXISTS ─────────────────────────────────────────────────────────
// Found 2026-09-23 while reading `sf_gaming_expenses` for its confidentiality
// tier, not by looking for it. `operatorEligibility()` checked the INDIRECT
// route with real care -- it matched each operator against the PAID canteen
// roster and said in its own words that paying the same person for canteen
// work while they operate the game "is the interaction (D)(1) is most easily
// breached by", and it kept a manual flag alongside because "a person can be
// paid by the lodge without appearing on the canteen roster".
//
// The DIRECT route was not checked at all. `sfAddExpense()` requires a payee
// and writes it to `sf_gaming_expenses`; grepping `payee` against the operator
// roster returned ZERO. So the app caught an operator who was also on the
// canteen payroll, and missed a cheque drawn on the segregated gaming account
// made out to that same operator by name -- which is the plainest form of the
// thing (D)(1) prohibits.
//
// ── A PROMPT, NOT A VERDICT, AND THAT IS THE DESIGN NOT A WEAKNESS ─────────
// A payee may legitimately be an operator's BUSINESS, or a landlord who also
// volunteers. So a name match raises a reason to confirm; it does NOT refuse
// the write and does NOT by itself make an operator ineligible in a way the
// post cannot explain. That is exactly the shape the canteen match already
// takes, and matching it was the instruction rather than an invention.
//
// ── THE ARM THAT MATTERS MOST IS THE NEGATIVE ONE ─────────────────────────
// A check of this shape earns its keep by being SILENT on the ordinary case.
// A post pays its landlord, its printer and its utility company out of the
// gaming account every month; if any of those raised a (D)(1) reason the panel
// would cry wolf and the real match would be ignored. Half the arms below are
// there to hold that line.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'sairnfreedom.html'), 'utf8');

let pass = 0, fail = 0;
const run = [];
function t(name, fn) { run.push([name, fn]); }
function section(s) { run.push([s, null]); }

// --- extract operatorEligibility verbatim from the app ---------------------

function extract(startAnchor, endAnchor, label) {
  const i = HTML.indexOf(startAnchor);
  assert.notStrictEqual(i, -1, 'could not find ' + label + ' -- anchor moved');
  assert.strictEqual(HTML.indexOf(startAnchor, i + 1), -1,
    label + ' anchor is not unique; the extraction would read the wrong copy');
  const j = HTML.indexOf(endAnchor, i);
  assert.notStrictEqual(j, -1, 'could not find the end of ' + label);
  return HTML.slice(i, j + endAnchor.length);
}

const SRC = extract(
  'function operatorEligibility(o){',
  '\n}',
  'operatorEligibility');

// The function reaches for ageOn(), parseLocalDate(), localToday(), getStaff()
// and getGamingExpenses(). Each is stubbed by name, so a new dependency throws
// here instead of silently reading undefined.
function evaluate(operator, opts) {
  opts = opts || {};
  const ctx = {
    console,
    getStaff: () => opts.staff || [],
    getGamingExpenses: () => opts.expenses || [],
    localToday: () => '2026-09-23',
    parseLocalDate: (s) => { if (!s) return null; const p = String(s).split('-');
      return p.length === 3 ? new Date(Number(p[0]), Number(p[1]) - 1, Number(p[2])) : null; },
    ageOn: function (dob, onDate) {
      const d = ctx.parseLocalDate(dob), t2 = ctx.parseLocalDate(onDate);
      if (!d || !t2) return null;
      let age = t2.getFullYear() - d.getFullYear();
      const m = t2.getMonth() - d.getMonth();
      if (m < 0 || (m === 0 && t2.getDate() < d.getDate())) age--;
      return age;
    }
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(SRC + '\n', ctx);
  return ctx.operatorEligibility(operator);
}

const CITE = 'ORC 2915.09(D)(1)';
const ELIGIBLE = { name: 'Pat Doe', dob: '1980-01-01', felony: false, gambling: false,
                   compensated: false, paidCanteen: false };
const reasons = (r) => r.reasons.map(x => x.cite + ' :: ' + x.text);
const hasPayeeReason = (r) => r.reasons.some(x =>
  x.cite === CITE && /gaming account|payee|paid directly/i.test(x.text));

// ---------------------------------------------------------------------------
section('the direct route is raised');

t('a gaming-account payment to an operator by name raises (D)(1)', () => {
  const r = evaluate(ELIGIBLE, { expenses: [{ payee: 'Pat Doe', amount: 400 }] });
  assert.ok(hasPayeeReason(r),
    'no (D)(1) reason for a cheque made out to the operator: ' + JSON.stringify(reasons(r)));
  assert.strictEqual(r.eligible, false, 'a raised reason must clear `eligible`');
});

t('the match is case- and whitespace-insensitive, like the canteen match', () => {
  // The canteen match already normalises with trim().toLowerCase(); an operator
  // typed one way on one roster and another way on the other is the ordinary
  // case, not the exception.
  for (const payee of ['pat doe', '  PAT DOE  ', 'Pat  Doe'.replace(/\s+/g, ' ')]) {
    const r = evaluate(ELIGIBLE, { expenses: [{ payee, amount: 50 }] });
    assert.ok(hasPayeeReason(r), 'missed on payee ' + JSON.stringify(payee));
  }
});

t('one match among many ordinary payments is still found', () => {
  const r = evaluate(ELIGIBLE, { expenses: [
    { payee: 'Ohio Edison', amount: 210 },
    { payee: 'Pat Doe', amount: 75 },
    { payee: 'Miller Printing', amount: 90 }
  ] });
  assert.ok(hasPayeeReason(r), 'a single match inside a normal ledger was missed');
});

// ---------------------------------------------------------------------------
section('THE NEGATIVE ARMS -- it must be silent on the ordinary case');

t('an ordinary supplier ledger raises nothing', () => {
  const r = evaluate(ELIGIBLE, { expenses: [
    { payee: 'Ohio Edison', amount: 210 },
    { payee: 'Miller Printing', amount: 90 },
    { payee: 'Community Hall Rental LLC', amount: 800 }
  ] });
  assert.ok(!hasPayeeReason(r), 'cried wolf on suppliers: ' + JSON.stringify(reasons(r)));
  assert.strictEqual(r.eligible, true);
});

t('an empty ledger raises nothing', () => {
  const r = evaluate(ELIGIBLE, { expenses: [] });
  assert.ok(!hasPayeeReason(r));
  assert.strictEqual(r.eligible, true);
});

t('a SUBSTRING is not a match -- "Pat Doe" must not fire on "Pat Doe Supply Co"', () => {
  // The whole-value comparison is deliberate. A business named after its owner
  // is the commonest legitimate payee a post has, and a substring rule would
  // flag every one of them.
  const r = evaluate(ELIGIBLE, { expenses: [{ payee: 'Pat Doe Supply Co', amount: 300 }] });
  assert.ok(!hasPayeeReason(r),
    'substring matched, which flags every business named after its owner');
});

t('a blank or missing payee cannot match a blank operator name', () => {
  // Both sides are free text and either can be empty. An empty-equals-empty
  // match would fire on every expense for an operator whose name never loaded.
  const r = evaluate({ ...ELIGIBLE, name: '' }, { expenses: [{ payee: '', amount: 10 }] });
  assert.ok(!hasPayeeReason(r), 'empty matched empty');
  const r2 = evaluate(ELIGIBLE, { expenses: [{ amount: 10 }] });
  assert.ok(!hasPayeeReason(r2), 'a missing payee key matched');
});

// ---------------------------------------------------------------------------
section('it does not disturb what was already there');

t('the canteen match still fires on its own', () => {
  const r = evaluate(ELIGIBLE, { staff: [{ name: 'Pat Doe', paid: true }] });
  assert.ok(r.reasons.some(x => x.cite === CITE && /canteen roster/i.test(x.text)),
    'the pre-existing canteen match stopped firing: ' + JSON.stringify(reasons(r)));
});

t('unpaid canteen staff still raise nothing', () => {
  const r = evaluate(ELIGIBLE, { staff: [{ name: 'Pat Doe', paid: false }] });
  assert.strictEqual(r.eligible, true, JSON.stringify(reasons(r)));
});

t('the age, felony and gambling bars are untouched', () => {
  assert.ok(evaluate({ ...ELIGIBLE, dob: '2015-01-01' }).reasons
    .some(x => x.cite === 'ORC 2915.09(C)(7)'), 'the under-18 bar stopped firing');
  assert.ok(evaluate({ ...ELIGIBLE, dob: '' }).reasons
    .some(x => x.cite === 'ORC 2915.09(C)(7)'), 'the no-DOB bar stopped firing');
  assert.ok(evaluate({ ...ELIGIBLE, felony: true }).reasons
    .some(x => x.cite === 'ORC 2915.09(C)(8)'), 'the felony bar stopped firing');
  assert.ok(evaluate({ ...ELIGIBLE, gambling: true }).reasons
    .some(x => x.cite === 'ORC 2915.09(C)(8)'), 'the gambling bar stopped firing');
  assert.strictEqual(evaluate(ELIGIBLE).eligible, true, 'a clean operator is no longer eligible');
});

t('both routes at once produce TWO reasons, not one', () => {
  // They are different facts and a post confirming one has not answered the
  // other. Collapsing them would hide half of what has to be explained.
  const r = evaluate(ELIGIBLE, {
    staff: [{ name: 'Pat Doe', paid: true }],
    expenses: [{ payee: 'Pat Doe', amount: 120 }]
  });
  const d1 = r.reasons.filter(x => x.cite === CITE);
  assert.strictEqual(d1.length, 2, 'expected two distinct (D)(1) reasons, got ' + JSON.stringify(d1));
});

// ---------------------------------------------------------------------------
section('the control: this suite can fail');

t('deleting the payee arm turns the positive arms red', () => {
  // Proves the arms above test the new check and not some other reason that
  // happens to carry the same citation. The canteen arm is left in place, so
  // what is removed is exactly the thing under test.
  const cut = SRC.replace(/\n\s*\/\* ── THE DIRECT ROUTE[\s\S]*?\n(\s*)return \{ eligible:/, '\n$1return { eligible:');
  assert.notStrictEqual(cut, SRC, 'the control could not find the block to remove -- it would pass vacuously');
  const ctx = { console, getStaff: () => [], getGamingExpenses: () => [{ payee: 'Pat Doe', amount: 400 }],
    localToday: () => '2026-09-23',
    parseLocalDate: (s) => { if (!s) return null; const p = String(s).split('-');
      return p.length === 3 ? new Date(Number(p[0]), Number(p[1]) - 1, Number(p[2])) : null; },
    ageOn: () => 40 };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(cut + '\n', ctx);
  const r = ctx.operatorEligibility(ELIGIBLE);
  assert.ok(!r.reasons.some(x => x.cite === CITE),
    'the pre-fix body still raised (D)(1) -- the positive arms may pass for the wrong reason');
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
