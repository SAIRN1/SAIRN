// tests/sairnbuild_budget_early_warning.js
//
// Run:  node tests/sairnbuild_budget_early_warning.js
//
// SAIRNbuild's AI Budget Early Warning, driven verbatim from sairnbuild.html.
//
// WHY THIS FILE EXISTS. `f072765` ("correct 5 issues from AI Budget Early
// Warning final review") was self-reviewed only, and the open-work index
// carried it as "never independently re-reviewed". This is that pass, made
// durable: each of the five corrections gets an assertion, so a later edit
// that undoes one fails here instead of being rediscovered by a customer.
//
// WHAT THE RE-REVIEW FOUND THAT THE SELF-REVIEW DID NOT, and it is the
// two-files-one-change class every time: `f072765` changed costLineTier()'s
// CONTRACT -- budget<=0 with real spend became 'critical' instead of null --
// and did not revisit the one consumer whose display assumed the old
// contract. The Cost Code Roll-up hardcodes `pct` to 0 when there is no
// budget, so the row printed "$5,000 / $0 - 0%" and a zero-width bar in
// CRITICAL RED. Colour and number, same row, saying opposite things. Fixed
// 2026-09-04 and pinned below.
//
// TWO FURTHER FINDINGS WERE RAISED FOR A DECISION AND THEN FIXED TOGETHER on
// Michael's call, 2026-09-04, because they were one root cause -- `actual`
// being dropped -- wearing two faces:
//   * the roll-up computed its tier from committed ONLY (`actual:0`), while
//     costLineTier's own contract and every other panel use committed+actual.
//     The same data could read green in the roll-up and critical on its own
//     row -- exactly what f072765's "unified tier colours across panels"
//     claim says cannot happen.
//   * Variance was budget-committed and ignored `actual` entirely, so a line
//     with budget 100 / committed 0 / actual 100 showed a healthy +100 in the
//     cell directly beside a Critical badge. It now reads 0.
//
// FOUR sites carried the old arithmetic, not the two the review named: the
// panel KPI, the per-row cell, the roll-up, and the CSV export -- the last of
// which takes the number off the screen entirely, into a spreadsheet where no
// badge sits beside it to contradict. Every one is pinned below.
//
// THIS MAKES A REPORTED NUMBER WORSE wherever `actual` is non-zero. That is
// the correction, not a regression, and it is why the KPI sub-label now names
// its basis and the export column was renamed rather than quietly recomputed.

'use strict';
const fs = require('fs');
const path = require('path');

const HTML = path.join(__dirname, '..', 'sairnbuild.html');
const src = fs.readFileSync(HTML, 'utf8');

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

function balanced(start) {
  let i = src.indexOf('{', start), depth = 0;
  for (; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') { depth--; if (!depth) return src.slice(start, i + 1); }
  }
  throw new Error('unbalanced from ' + start);
}
function fn(decl) {
  const i = src.indexOf(decl);
  if (i < 0) throw new Error('not found: ' + decl);
  return balanced(i);
}
function objVar(name) {
  const m = src.match(new RegExp('var ' + name + '\\s*=\\s*(\\{[^;]*\\});'));
  if (!m) throw new Error('not found: var ' + name);
  return 'var ' + name + ' = ' + m[1] + ';';
}

const api = new Function(
  fn('function costLineTier(c){') + '\n' +
  objVar('TIER_LABEL') + '\n' +
  objVar('TIER_COLOR') + '\n' +
  objVar('TIER_BADGE') + '\n' +
  fn('function jobTierFromCosts(jobId, allCosts){') + '\n' +
  'return { costLineTier: costLineTier, jobTierFromCosts: jobTierFromCosts,' +
  '         TIER_LABEL: TIER_LABEL, TIER_COLOR: TIER_COLOR, TIER_BADGE: TIER_BADGE };'
)();

const { costLineTier, jobTierFromCosts, TIER_LABEL, TIER_COLOR, TIER_BADGE } = api;
const line = (budget, committed, actual, job) =>
  ({ budget, committed, actual, job_id: job || 'J-1' });

// ── f072765 correction 2: zero budget with real spend is CRITICAL ──────────
// It used to return null, so a cost line being spent against with no budget
// entered -- the state a line is in the moment a PO lands before anyone
// budgets it -- was silently the SAFEST thing on the screen.
check('no budget, real committed spend -> critical',
  costLineTier(line(0, 5000, 0)), 'critical');
check('no budget, real actual spend -> critical',
  costLineTier(line(0, 0, 5000)), 'critical');
check('no budget and no spend is not a risk, it is unstarted',
  costLineTier(line(0, 0, 0)), null);
check('a negative budget is treated as no budget',
  costLineTier(line(-100, 1, 0)), 'critical');

// ── the thresholds, and that they read committed+actual, not actual alone ──
// "Early" means before the money moves; committed spend that has not been
// paid yet is the whole point of the feature.
check('69% is below the first tier', costLineTier(line(1000, 690, 0)), null);
check('70% is watch', costLineTier(line(1000, 700, 0)), 'watch');
check('80% is warning', costLineTier(line(1000, 800, 0)), 'warning');
check('90% is critical', costLineTier(line(1000, 900, 0)), 'critical');
// 500 + 300 = 800 = warning. Neither half reaches even the watch threshold on
// its own, so this fails outright if the two are not added.
check('committed and actual are SUMMED, not read one at a time',
  costLineTier(line(1000, 500, 300)), 'warning');
check('and neither half alone would have tiered at all',
  [costLineTier(line(1000, 500, 0)), costLineTier(line(1000, 0, 300))], [null, null]);
check('actual alone still tiers', costLineTier(line(1000, 0, 950)), 'critical');

// ── the job rollup is worst-of, not an average ─────────────────────────────
{
  const all = [line(1000, 950, 0, 'J-1'), line(1000, 10, 0, 'J-1'), line(1000, 10, 0, 'J-1')];
  check('one critical line makes the JOB critical, however many are fine',
    jobTierFromCosts('J-1', all), 'critical');
  check('an average would have said null here -- it must not',
    jobTierFromCosts('J-1', all) === null, false);
  check('a job with no lines has no tier', jobTierFromCosts('J-9', all), null);
  check('lines belonging to another job are not counted',
    jobTierFromCosts('J-2', all.concat([line(1000, 10, 0, 'J-2')])), null);
}

// ── f072765 correction 4: one tier, one colour, everywhere ────────────────
// The claim was "identical badge class/color for the identical tier". That is
// checkable mechanically rather than by eye.
{
  const tiers = Object.keys(TIER_LABEL).sort();
  check('every tier has a label, a colour and a badge class',
    [Object.keys(TIER_COLOR).sort(), Object.keys(TIER_BADGE).sort()], [tiers, tiers]);
  tiers.forEach((t) => {
    check('the ' + t + ' badge class is defined in the stylesheet',
      new RegExp('\\.' + TIER_BADGE[t] + '\\{').test(src), true);
  });
  check('the retired .tw2 class has no callers left', /tw2/.test(src), false);
}

// ── f072765 corrections 1 and 3, which are structural ─────────────────────
// rDash() and rCostTbl() cannot be driven without the DOM, so the two
// properties are asserted against the source. Both are one-token changes that
// a later edit could undo without any test noticing.
{
  const dash = fn('function rDash(){');
  check('the Early Warning block iterates ACTIVE jobs, not all jobs -- a '
    + 'completed job must stop being flagged as an overrun risk',
    /act\.forEach\(function\s*\(j\)\s*\{\s*var t=jobTierFromCosts/.test(dash), true);
  check('and it no longer hardcodes its badge classes',
    /c:TIER_BADGE\[t\]/.test(dash), true);

  const tbl = fn('function rCostTbl(){');
  check('the job-level badge is computed against the FULL cost list, so the '
    + 'panel\'s own job/kind filter cannot hide a job\'s true risk',
    /var allCostsForTier=costs\(\);/.test(tbl), true);
  check('and it is that full list that is passed in, not the filtered one',
    /jobTierFromCosts\(c\.job_id,\s*allCostsForTier\)/.test(tbl), true);
}

// ── the roll-up contradiction found by this re-review ─────────────────────
// The roll-up has no function of its own -- it is rendered at the end of
// rCostTbl(), which is why a change to costLineTier() could reach it without
// anyone opening a file named after it.
{
  const body = fn('function rCostTbl(){');
  check('the roll-up no longer prints a percentage when there is no budget',
    /pctText=hasBudget\?\(pct\+'%'\):\(cm>0\?'no budget set':'--'\)/.test(body), true);
  check('and the bar is full rather than empty when spend has no budget, so '
    + 'the bar agrees with the critical colour beside it',
    /barPct=hasBudget\?Math\.min\(100,pct\):\(cm>0\?100:0\)/.test(body), true);
}

// ── ONE BASIS FOR SPEND, EVERYWHERE (fixed 2026-09-04) ────────────────────
//
// These four assertions replaced two that pinned the OLD, inconsistent
// behaviour as a known gap. Both gaps had the same root cause -- `actual` was
// dropped -- so they were closed together.
//
// The worked case, which is the whole point: a line with budget 100,
// committed 0, actual 100 is CRITICAL on its own row. Under the old
// arithmetic the Variance cell beside that badge read a healthy +100. It now
// reads 0. Two numbers describing one line, agreeing.
{
  const tbl = fn('function rCostTbl(){');
  check('the line spent entirely through `actual` is critical',
    costLineTier(line(100, 0, 100)), 'critical');
  check('the panel Variance KPI subtracts committed AND actual',
    /var variance=budget-\(committed\+actual\);/.test(tbl), true);
  check('so does the per-row Variance cell, beside the badge it must agree with',
    /var v=\(c\.budget\|\|0\)-\(\(c\.committed\|\|0\)\+\(c\.actual\|\|0\)\);/.test(tbl), true);
  check('the roll-up now ACCUMULATES actual instead of dropping it',
    /if\(!byCode\[k\]\)byCode\[k\]=\{budget:0,committed:0,actual:0\};/.test(tbl), true);
  check('and tiers on the real committed+actual, not on committed with a '
    + 'hardcoded actual:0',
    /costLineTier\(\{budget:b,committed:byCode\[k\]\.committed,actual:byCode\[k\]\.actual\}\)/.test(tbl), true);
  check('the number the roll-up PRINTS moved with the colour, so the bar and '
    + 'its label are still describing the same quantity',
    /var b=byCode\[k\]\.budget,cm=byCode\[k\]\.committed\+byCode\[k\]\.actual;/.test(tbl), true);
  check('no committed-only variance survives anywhere in the panel',
    /\(c\.budget\|\|0\)-\(c\.committed\|\|0\)/.test(tbl), false);
  // The label is part of the fix: this makes a reported number WORSE wherever
  // actual is non-zero, and a reader who assumes the old basis would think
  // the figure had broken rather than changed.
  check('the KPI sub-label names the basis, in both its states',
    (src.match(/Budget less committed\+actual/g) || []).length, 2);
  check('and the old wording is gone', /Budget less committed</.test(src), false);
}

// ── the CSV export carries the same arithmetic off the screen ─────────────
// It is the one place the number reaches a customer's spreadsheet, where no
// badge sits beside it to contradict.
{
  const exp = src.slice(src.indexOf("rows=[['Job','Cost Code','Kind'"), src.indexOf("} else if(type==='changeorders')"));
  check('the export subtracts committed AND actual',
    /\(c\.budget\|\|0\)-\(\(c\.committed\|\|0\)\+\(c\.actual\|\|0\)\)/.test(exp), true);
  check('and its header says which quantity the column now holds',
    /'Variance \(budget less committed\+actual\)'/.test(exp), true);
}

console.log((fail ? 'FAILED' : 'ok') + '  sairnbuild-budget-early-warning: ' +
  pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
