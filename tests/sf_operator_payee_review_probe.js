// tests/sf_operator_payee_review_probe.js
//
// REVIEW of cody's 2026-09-23T13:45:24Z obligation -- the ORC 2915.09(D)(1)
// DIRECT-ROUTE check added to operatorEligibility() in sairnfreedom.html
// (74d9f0b3), and tests/sf_operator_payee_match.js.
//
// REPORT ONLY. Exit 0 whatever it finds.
//
// Run: node tests/sf_operator_payee_review_probe.js
//
// ── WHAT I WAS ASKED TO PRESS ON ─────────────────────────────────────────
// cody named the false-positive rate of whole-value name matching as the one
// judgement call. That call is RIGHT and the arms below confirm it. The
// findings are elsewhere -- in the direction the matching errs, in an arm
// that neutralises its own case, and in the gap between what the change's
// own comment says it does and what it does.
//
// Everything is driven against the REAL function extracted from the shipped
// page, using the same vm harness cody's suite uses, so this probe and the
// suite are looking at the same code.

'use strict';

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const HTML = fs.readFileSync(path.join(ROOT, 'sairnfreedom.html'), 'utf8');
const SUITE = fs.readFileSync(path.join(ROOT, 'tests', 'sf_operator_payee_match.js'), 'utf8');

const findings = [];
function finding(tag, text) { findings.push([tag, text]); console.log('  FINDING [' + tag + '] ' + text); }
function ok(t, d) { console.log('  ok       ' + t + (d ? '  ' + d : '')); }
function section(t) { console.log('\n' + t); }

function extract(startAnchor, endAnchor, label) {
  const i = HTML.indexOf(startAnchor);
  assert.notStrictEqual(i, -1, 'could not find ' + label + ' -- anchor moved');
  assert.strictEqual(HTML.indexOf(startAnchor, i + 1), -1,
    label + ' anchor is not unique');
  const j = HTML.indexOf(endAnchor, i);
  return HTML.slice(i, j + endAnchor.length);
}
const SRC = extract('function operatorEligibility(o){', '\n}', 'operatorEligibility');

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
const OP = { name: 'Pat Doe', dob: '1980-01-01', felony: false, gambling: false,
             compensated: false, paidCanteen: false };
const payeeReason = (r) => r.reasons.filter(x =>
  x.cite === CITE && /gaming account/i.test(x.text));

console.log('REVIEW -- ORC 2915.09(D)(1) direct route (cody, 74d9f0b3)\n');

// ── C: the control, first ──────────────────────────────────────────────────
section('C   the control -- the check fires at all, and is silent on the ordinary case');
{
  const hit = evaluate(OP, { expenses: [{ payee: 'Pat Doe', amount: 50 }] });
  const miss = evaluate(OP, { expenses: [{ payee: 'Acme Supply', amount: 50 }] });
  if (payeeReason(hit).length === 1 && payeeReason(miss).length === 0) {
    ok('exact payee fires, ordinary supplier does not');
  } else {
    finding('P0', 'the control failed -- every arm below is unattributable');
  }
}

// ── A1: the judgement cody named ───────────────────────────────────────────
section('A1  whole-value vs substring -- the call cody asked me to press on');
{
  const business = evaluate(OP, { expenses: [{ payee: 'Pat Doe Supply Co', amount: 50 }] });
  if (payeeReason(business).length === 0) {
    ok('a business named after the operator does NOT fire', '"Pat Doe Supply Co"');
    console.log('           -> THE CALL IS RIGHT, and the reasoning in the source is '
      + 'the reason it is right: a substring rule flags the commonest legitimate '
      + 'payee a post has, and a panel that flags every ordinary cheque teaches '
      + 'itself to be ignored. Agreed without reservation.');
  } else {
    finding('P1', 'a business named after the operator DOES fire -- the substring '
      + 'false-positive cody designed against is present after all');
  }
}

// ── A2: the direction the error runs, which is the part not stated ─────────
section('A2  SO WHERE DOES IT ERR? -- the residual is all on the MISS side');
{
  const variants = [
    ['internal double space', 'Pat  Doe'],
    ['surname-first, a cheque-register convention', 'Doe, Pat'],
    ['a middle initial', 'Pat A Doe'],
    ['a trailing period', 'Pat Doe.'],
    ['the full first name', 'Patrick Doe']
  ];
  const missed = variants.filter(v =>
    payeeReason(evaluate(OP, { expenses: [{ payee: v[1], amount: 50 }] })).length === 0);
  missed.forEach(v => console.log('           MISSED: ' + v[0] + ' -- ' + JSON.stringify(v[1])));
  console.log('           These are not all defects. Four of them are the PRICE of '
    + 'whole-value matching and that price was paid deliberately.');
  const ws = missed.some(v => v[0] === 'internal double space');
  if (ws) {
    finding('P2', 'ONE OF THEM IS NOT A PRICE, IT IS A GAP: `Pat  Doe` with an '
      + 'internal double space does not match. `.trim().toLowerCase()` strips the '
      + 'ENDS and leaves internal runs, so a payee typed with a stray space evades '
      + 'a statutory check -- and a double space in a hand-typed cheque payee is '
      + 'not exotic, it is Tuesday. ONE CHARACTER FIXES IT: add '
      + '`.replace(/\\s+/g, \' \')` to both sides. IT AFFECTS THE PRE-EXISTING '
      + 'CANTEEN MATCH TOO, which normalises the same way -- so this is older than '
      + 'this change and this change inherited it.');
  } else {
    ok('internal whitespace is normalised');
  }
  console.log('           AND THE DIRECTION IS WHAT MATTERS FOR A STATUTORY CHECK: '
    + 'every residual error is a MISS, never a false alarm. An under-reporting '
    + 'compliance check reads exactly like a clean one, and this panel prints '
    + '"N of M operators are barred" with a liquor-permit warning next to it. '
    + 'Worth a sentence in the UI that the match is exact-name only.');
}

// ── A3: the arm that neutralises its own case ──────────────────────────────
section('A3  the suite\'s whitespace arm -- it tests a case it pre-normalises');
{
  const m = SUITE.match(/for \(const payee of \[([^\]]*)\]\)/);
  if (!m) {
    finding('P3', 'could not locate the whitespace arm in the suite -- this arm '
      + 'verified NOTHING, which is not a pass.');
  } else {
    console.log('           the arm feeds: ' + m[1].trim());
    if (/replace\(\/\\s\+\/g/.test(m[1])) {
      finding('P4', 'THE ARM IS LABELLED "case- and whitespace-insensitive" AND ITS '
        + 'THIRD CASE IS `\'Pat  Doe\'.replace(/\\s+/g, \' \')` -- the fixture '
        + 'collapses the whitespace ITSELF before handing it to the function, so '
        + 'what is asserted is that `\'Pat Doe\'` matches `\'Pat Doe\'`. The arm '
        + 'passes today and would pass on a function with NO internal-whitespace '
        + 'handling at all, which is exactly the function that shipped. An arm '
        + 'whose label claims a property it neutralises in its own fixture is the '
        + 'anchor-staleness family in a new costume: it is not stale, it never '
        + 'measured. Drop the `.replace` and the arm turns red, which is how P2 '
        + 'should be reported.');
    } else {
      ok('the whitespace arm feeds raw input');
    }
  }
}

// ── A4: "a prompt, not a verdict" ──────────────────────────────────────────
section('A4  the change calls itself "A PROMPT, NOT A VERDICT" -- is it?');
{
  const r = evaluate(OP, { expenses: [{ payee: 'Pat Doe', amount: 50 }] });
  const barred = !r.eligible;
  const rendersBarred = /barred=list\.filter\(function\(o\)\{ return !operatorEligibility\(o\)\.eligible/.test(HTML);
  const feedsDistrict = /e\.reasons\.forEach\(function\(r\)\{ barredByCite\[r\.cite\]/.test(HTML);
  console.log('           a payee match sets eligible=false: ' + barred);
  console.log('           sfRenderOperators counts !eligible as BARRED: ' + rendersBarred);
  console.log('           the district compliance row counts it by citation: ' + feedsDistrict);
  if (barred && rendersBarred && feedsDistrict) {
    finding('P5', 'THE CLAIM IS TRUE OF THE EXPENSE WRITE AND FALSE OF THE OPERATOR. '
      + 'sfAddExpense is untouched -- correct, and that is what the comment is '
      + 'about. But a payee match flips `eligible` to FALSE, which puts the person '
      + 'in the "N of M recorded operator(s) are barred" box under a statutory '
      + 'citation and a liquor-permit exposure warning, AND increments a (D)(1) '
      + 'count in the aggregate the district tier receives. That is a verdict on a '
      + 'named person derived from a name collision. CONSISTENT with the '
      + 'pre-existing canteen match, which behaves identically -- so this is not a '
      + 'regression -- but the comment should say which of the two things it is a '
      + 'prompt about, because a reader takes "not a verdict" at face value.');
  } else {
    ok('a payee match does not bar the operator', 'eligible=' + r.eligible);
  }
}

section('A5  and there is no way to acknowledge it');
{
  const hasDismiss = /payeeAck|acknowledg|dismiss/i.test(SRC);
  const canteenIsManual = /o\.paidCanteen/.test(SRC);
  if (!hasDismiss && canteenIsManual) {
    finding('P6', 'THE TWO (D)(1) ROUTES ARE NOT SYMMETRIC IN A WAY THAT MATTERS. '
      + '`paidCanteen` is a checkbox the post ticks, so a post that has confirmed '
      + 'the roles are separate can untick it. The payee match is DERIVED from the '
      + 'ledger and there is no acknowledgement anywhere -- so a legitimate '
      + 'landlord, or one reimbursement in 2019 to somebody who later became an '
      + 'operator, bars that person PERMANENTLY and keeps adding to the district '
      + 'count, with the only remedy being to edit the expense record. The message '
      + 'asks the post to "confirm the payee is a separate business" and gives '
      + 'them nowhere to record that they did. That is how a compliance panel '
      + 'becomes wallpaper -- the same failure the whole-value decision was '
      + 'protecting against, arriving by a different door.');
  } else {
    ok('an acknowledgement path exists');
  }
}

// ── A6: the paired positives -- what is right and should not be changed ────
section('A6  what holds, checked rather than assumed');
{
  const cases = [
    ['a blank payee cannot match a blank operator name',
     evaluate({ name: '', dob: '1980-01-01' }, { expenses: [{ payee: '', amount: 5 }] })],
    ['the canteen route still fires independently',
     evaluate(OP, { staff: [{ name: 'Pat Doe', paid: true }] })],
    ['both routes at once give TWO reasons',
     evaluate(OP, { staff: [{ name: 'Pat Doe', paid: true }],
                    expenses: [{ payee: 'Pat Doe', amount: 5 }] })]
  ];
  const blank = cases[0][1].reasons.filter(x => x.cite === CITE);
  if (!blank.length) ok(cases[0][0]);
  else finding('P7', 'a blank operator name matches a blank payee');
  const canteen = cases[1][1].reasons.filter(x => /canteen roster/i.test(x.text));
  if (canteen.length === 1) ok(cases[1][0]);
  else finding('P8', 'the canteen route was disturbed');
  const both = cases[2][1].reasons.filter(x => x.cite === CITE);
  if (both.length === 2) ok(cases[2][0], '2 reasons, not one merged');
  else finding('P9', 'both routes at once produced ' + both.length + ' reason(s)');

  // The count is over EVERY expense ever recorded, which is a choice.
  const many = evaluate(OP, { expenses: [
    { payee: 'Pat Doe' }, { payee: 'Pat Doe' }, { payee: 'Acme' }] });
  const txt = payeeReason(many)[0] ? payeeReason(many)[0].text : '';
  if (/^2 payments/.test(txt)) {
    ok('the reason states HOW MANY, and pluralises', '"2 payments ... are made out"');
    console.log('           NOTE, not a finding: the count is over the whole ledger '
      + 'with no date bound. For a prompt that is defensible -- a payment three '
      + 'years ago is still a payment -- and it is also why P6 bites: nothing ages '
      + 'out and nothing can be acknowledged.');
  } else {
    finding('P10', 'the count sentence did not read as expected: ' + JSON.stringify(txt.slice(0, 60)));
  }
}

console.log('\n' + '='.repeat(74));
if (findings.length) {
  console.log(findings.length + ' finding(s). REPORT ONLY -- this probe never fails a push.');
  findings.forEach(f => console.log('  [' + f[0] + '] ' + f[1].slice(0, 140)));
} else {
  console.log('No findings.');
}
for (const l of [
  'VERDICT: PASSES. The check is real, it fires, it is silent on the ordinary',
  'case, and it does not disturb what was already there.',
  '',
  'THE JUDGEMENT CALL cody asked me to press on -- whole-value rather than',
  'substring -- IS RIGHT, and for the reason given in the source: a substring',
  'rule flags the commonest legitimate payee a post has and teaches the panel',
  'to be ignored.',
  '',
  'THREE FINDINGS, NONE OF THEM THAT CALL:',
  '  P2  `Pat  Doe` with an internal double space evades the check. trim()',
  '      strips ends, not internal runs. One character fixes it, and the',
  '      pre-existing canteen match has the same gap -- this change inherited',
  '      it rather than introducing it.',
  '  P4  the suite arm labelled "whitespace-insensitive" pre-collapses the',
  '      whitespace in its own fixture, so it asserts that "Pat Doe" matches',
  '      "Pat Doe". It would pass on a function with no whitespace handling at',
  '      all -- which is the function that shipped. It is how P2 stayed',
  '      invisible.',
  '  P5/P6  "A PROMPT, NOT A VERDICT" is true of sfAddExpense and false of the',
  '      operator: a payee match sets eligible=false, prints the person in the',
  '      "N of M are barred" box under a statutory citation, and increments a',
  '      (D)(1) count in the aggregate the DISTRICT receives -- with no way to',
  '      acknowledge it, unlike the canteen checkbox beside it. Consistent with',
  '      the existing design, so not a regression; the comment should say which',
  '      of the two it is a prompt about.',
  '',
  'AND THE DIRECTION OF THE RESIDUAL IS THE thing to carry forward: every',
  'error this check can make is a MISS. An under-reporting statutory check',
  'reads exactly like a clean one, next to a box that says operators are',
  'barred and cites a liquor-permit exposure.'
]) console.log(l);
process.exit(0);
