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
// TWO FURTHER FINDINGS ARE REPORTED, NOT FIXED, because both change what a
// customer-facing number MEANS and that is a decision, not a patch. They are
// asserted here as the CURRENT behaviour so the decision is visible rather
// than lost:
//   * the roll-up computes its tier from committed ONLY (`actual:0`), while
//     costLineTier's own contract and every other panel use committed+actual.
//     So the same underlying data can be green in the roll-up and critical on
//     its own row -- which is exactly what f072765's "unified tier colours
//     across panels" claim says cannot happen.
//   * the Variance column is budget-committed and ignores `actual` entirely,
//     so a line with budget 100 / committed 0 / actual 100 shows a healthy
//     +100 variance in the cell directly beside a Critical tier badge.
//     Pre-dates f072765; adjacent cells contradicting each other all the same.

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

// ── REPORTED, NOT FIXED: pinned so the decision stays visible ─────────────
{
  check('KNOWN GAP -- the roll-up still computes its tier from committed '
    + 'only, so it can read green where the line reads critical',
    /costLineTier\(\{budget:b,committed:cm,actual:0\}\)/.test(fn('function rCostTbl(){')), true);
  check('KNOWN GAP -- Variance is budget-committed and ignores actual, so it '
    + 'can show healthy in the cell beside a Critical badge',
    /var v=\(c\.budget\|\|0\)-\(c\.committed\|\|0\);/.test(fn('function rCostTbl(){')), true);
  // The arithmetic those two gaps describe, stated as numbers rather than prose.
  check('a line spent entirely through `actual` is critical on its own row',
    costLineTier(line(1000, 0, 1000)), 'critical');
  check('...while the roll-up, fed committed only, calls the same data safe',
    costLineTier({ budget: 1000, committed: 0, actual: 0 }), null);
}

console.log((fail ? 'FAILED' : 'ok') + '  sairnbuild-budget-early-warning: ' +
  pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
