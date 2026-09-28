// tests/sairnbuild_wip_percent_complete.js
//
// Run:  node tests/sairnbuild_wip_percent_complete.js
//
// REQUIREMENT: SAIRNbuild's WIP schedule must never report a job as further
//   along than its own numbers support, and must never derive earned revenue
//   from a cost forecast it knows is stale.
//
// ── WRITTEN BEFORE THE FIX, ON PURPOSE ──────────────────────────────────────
// Every arm below was written and RUN against the broken jobWIP() first. The
// failures they produced are recorded in the commit that fixes them. A
// regression test written after the fix only proves the fix is present, not that
// it was ever absent.
//
// ── THE DEFECT, AND IT IS THREE THINGS WEARING ONE FACE ─────────────────────
//
//     var pct = estTotal > 0 ? Math.min(1, costToDate / estTotal) : 0;
//     var earned = Math.round(pct * revised);
//
// where `estTotal = budgetFor(id)` -- the sum of the ORIGINAL `budget` on the
// job's cost rows -- and `revised = (job.value||0) + acceptedCOFor(id)`.
//
//   1. THE DENOMINATOR IS THE ORIGINAL BUDGET AND IS NEVER RE-FORECAST.
//      Percentage-of-completion needs cost incurred over ESTIMATED COST AT
//      COMPLETION. Cost-to-date over the original budget is the same number
//      only while the forecast still equals the budget, which is exactly the
//      condition that stops holding the moment a job goes sideways.
//
//   2. `Math.min(1, ...)` CAPS IT AT 100%. A job that has spent 130% of budget
//      reports 100% complete, so `earned` becomes the WHOLE contract -- the
//      maximum earned figure the arithmetic can produce -- and over/under
//      billing swings to its most UNDER-billed reading. The truth is the
//      opposite: the job is losing money and is probably over-billed.
//
//   3. AN ACCEPTED CHANGE ORDER MOVES THE NUMERATOR'S TWIN AND NOT THE
//      DENOMINATOR. `revisedValue()` adds an accepted CO's `amount` to the
//      contract. Nothing adds its COST to the budget, and a change-order record
//      in this app carries no cost field at all (id, job_id, description,
//      amount, labour_hrs, status, ...), so the app cannot infer it. So the
//      contract grows, the cost forecast does not, percent complete is computed
//      against a denominator that is too small, and earned revenue is
//      overstated twice over -- once by the inflated percent and once by the
//      larger contract it multiplies.
//
// WHY IT MATTERS MORE THAN AN ORDINARY WRONG NUMBER: this is the report a
// surety underwriter and a bank read, and the thing they read it FOR is profit
// fade -- margin quietly eroding as EAC rises. Capping percent complete at 100%
// and never re-forecasting removes precisely the signal they are looking for,
// and replaces it with the most reassuring number available.
//
// ── WHAT THE FIX DOES NOT DO, so no arm here asserts it ─────────────────────
// It does not invent a cost for a change order. That figure is not recorded
// anywhere in this app and guessing it would be a fabricated input feeding a
// money figure. It DISCLOSES that the forecast cannot include it, and refuses
// the derived figures rather than printing them.

'use strict';
const fs = require('fs');
const path = require('path');

const HTML = path.join(__dirname, '..', 'sairnbuild.html');
const src = fs.readFileSync(HTML, 'utf8');

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; console.log('  ok   ' + name); return; }
  fail++;
  console.log('  FAIL ' + name + '\n         expected ' + e + '\n         actual   ' + a);
}
function ok(name, cond, detail) {
  if (cond) { pass++; console.log('  ok   ' + name); return; }
  fail++;
  console.log('  FAIL ' + name + (detail ? '\n         ' + detail : ''));
}
function section(t) { console.log('\n' + t); }

// ── THE LIFT. jobWIP() is RUN, never reimplemented -- a second copy of this
// arithmetic in a test is a second declaration of the answer and the two drift.
// Same mechanism as tests/sairnbuild_budget_early_warning.js.
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
  if (i < 0) throw new Error('not found in sairnbuild.html: ' + decl);
  if (src.indexOf(decl, i + 1) !== -1) {
    throw new Error('declaration is not unique, so the lift could take the '
      + 'wrong one: ' + decl);
  }
  return balanced(i);
}

// The data accessors are stubbed, not lifted: they read localStorage and the
// point here is the arithmetic above them. Each stub is a plain array the arm
// sets, so a fixture is readable at the call site.
let COSTS = [], COS = [], DRAWS = [];
const NEEDED = [
  'function fmt(n){',
  'function committedFor(id){',
  'function actualFor(id){',
  'function budgetFor(id){',
  'function acceptedCOFor(id){',
  'function revisedValue(j){',
  'function jobWIP(j){'
];
// forecastFor() is the FIX's own function. Lifted if present, and its absence
// is a NAMED FAILURE rather than a skip -- a missing fix must not look like a
// passing test.
let forecastPresent = true;
let lifted;
try {
  lifted = NEEDED.map(fn).join('\n');
} catch (e) {
  console.log('CANNOT LIFT: ' + e.message);
  process.exit(2);
}
let forecastSrc = '';
try {
  forecastSrc = fn('function forecastFor(id){') + '\n'
              + fn('function hasForecastFor(id){');
} catch (e) {
  forecastPresent = false;
  forecastSrc = 'function forecastFor(id){ return budgetFor(id); }\n'
              + 'function hasForecastFor(id){ return false; }';
}

const api = new Function('__costs', '__cos', '__draws',
  'function costs(){return __costs();}\n'
  + 'function chgOrders(){return __cos();}\n'
  + 'function bldDraws(){return __draws();}\n'
  + 'function drawMoney(v){var n=Number(v);return isFinite(n)?n:0;}\n'
  + lifted + '\n' + forecastSrc + '\n'
  + 'return { jobWIP: jobWIP, budgetFor: budgetFor, forecastFor: forecastFor,'
  + '         revisedValue: revisedValue, actualFor: actualFor };'
)(() => COSTS, () => COS, () => DRAWS);

const JOB = { id: 'J-1', value: 100000 };
function scenario(opts) {
  COSTS = opts.costs || [];
  COS = opts.cos || [];
  DRAWS = opts.draws || [];
  return api.jobWIP(opts.job || JOB);
}
const cost = (budget, actual, forecast) => {
  const c = { job_id: 'J-1', budget: budget, committed: 0, actual: actual };
  if (forecast !== undefined) c.forecast = forecast;
  return c;
};
const draw = (received) => ({ job_id: 'J-1', amount_received: received });

console.log('SAIRNBUILD WIP -- percent complete must not flatter a job that is losing money');

section('THE LIFT ITSELF -- without this every arm below is vacuous');
ok('forecastFor() exists in sairnbuild.html', forecastPresent,
   'forecastFor(id) is absent, so there is no re-forecast mechanism and every '
   + 'arm below is testing the ORIGINAL budget under a new name. This is a '
   + 'FAILURE, not a skip: a stub was substituted only so the remaining arms '
   + 'still report something.');
ok('jobWIP() really runs and returns a shape', (function () {
  const w = scenario({ costs: [cost(100000, 50000)] });
  return w && typeof w === 'object' && 'costToDate' in w && 'pct' in w;
})(), 'the lifted jobWIP did not return a WIP row');

section('1. THE CAP -- a job over budget must not report itself complete');

// $130k spent against a $100k forecast. The job is 30% over and nowhere near
// done; the old code reported 100% and handed back the entire contract as
// earned revenue.
const over = scenario({ costs: [cost(100000, 130000)] });
ok('percent complete is NOT capped at 100% -- it reports the real ratio',
   over.pct !== null && over.pct > 1,
   'pct came back ' + JSON.stringify(over.pct) + '. 130000/100000 is 1.3. A cap '
   + 'at 1 here is the whole defect: it converts a 30% cost overrun into "this '
   + 'job is finished".');
ok('...and the forecast is reported STALE, because cost has passed it',
   Array.isArray(over.forecastStale) && over.forecastStale.length > 0,
   'forecastStale came back ' + JSON.stringify(over.forecastStale) + '. Costs '
   + 'exceeding the estimated cost at completion is proof the estimate is '
   + 'wrong, not a percentage above 100.');
check('...and earned revenue is REFUSED rather than reported as the whole contract',
  over.earned, null);
check('...and over/under billing is refused with it', over.overUnder, null);
check('...and the position says so instead of guessing', over.position, 'unknown');

section('2. AN ACCEPTED CHANGE ORDER -- value in the contract, cost in nothing');

// $50k spent of a $100k budget = 50%. An accepted $20k CO lifts the contract to
// $120k. Its COST is recorded nowhere, so the denominator is still $100k and
// percent complete is computed against a forecast that cannot be right.
const withCO = scenario({
  costs: [cost(100000, 50000)],
  cos: [{ job_id: 'J-1', amount: 20000, status: 'accepted' }]
});
check('the contract does include the accepted change order', withCO.revised || api.revisedValue(JOB), 120000);
ok('the forecast is reported STALE when an accepted CO has never been costed',
   Array.isArray(withCO.forecastStale) && withCO.forecastStale.length > 0,
   'forecastStale came back ' + JSON.stringify(withCO.forecastStale) + '. The '
   + 'contract grew by 20000 and the cost forecast did not move, and a change '
   + 'order record in this app carries no cost field at all -- so the app '
   + 'cannot know the new EAC and must say so.');
ok('...and the stale reason NAMES the change order rather than being generic',
   (withCO.forecastStale || []).join(' ').toLowerCase().indexOf('change order') !== -1,
   'the reasons were ' + JSON.stringify(withCO.forecastStale));
check('...and earned revenue is refused rather than multiplied by the bigger contract',
  withCO.earned, null);

// A DRAFT/SENT/REJECTED CO must NOT trigger this. Only an accepted one moves
// the contract, so only an accepted one creates the mismatch.
const draftCO = scenario({
  costs: [cost(100000, 50000)],
  cos: [{ job_id: 'J-1', amount: 20000, status: 'draft' },
        { job_id: 'J-1', amount: 9000, status: 'sent' },
        { job_id: 'J-1', amount: 5000, status: 'rejected' }]
});
check('CONTROL -- a draft, sent or rejected CO does NOT make the forecast stale',
  draftCO.forecastStale, []);
check('...and earned revenue is still computed on that job', draftCO.earned, 50000);

section('3. THE RE-FORECAST -- an explicit EAC is honoured and clears the staleness');

// The remedy a real WIP schedule uses: revise the estimate. A cost row carrying
// an explicit `forecast` is the re-forecast, and it is taken at its word.
const forecast = scenario({
  costs: [cost(100000, 50000, 125000)],
  cos: [{ job_id: 'J-1', amount: 20000, status: 'accepted' }]
});
check('forecastFor() uses the revised figure, not the original budget',
  api.forecastFor('J-1'), 125000);
check('...and the ORIGINAL budget is still reported separately',
  api.budgetFor('J-1'), 100000);
check('percent complete is cost over the REVISED forecast', forecast.pct, 0.4);
check('...and the forecast is no longer stale once it has been revised',
  forecast.forecastStale, []);
check('...and earned revenue is 40% of the 120000 revised contract',
  forecast.earned, 48000);

// PROFIT FADE, THE WHOLE POINT. Same cost to date, a bigger EAC: percent
// complete FALLS, earned revenue FALLS, and a job that looked under-billed
// turns out to be over-billed. This is the movement the old cap erased.
const fadeBefore = scenario({ costs: [cost(100000, 50000)], draws: [draw(55000)] });
const fadeAfter = scenario({ costs: [cost(100000, 50000, 200000)], draws: [draw(55000)] });
check('before the re-forecast: 50% earned 50000, billed 55000 -> over-billed 5000',
  [fadeBefore.pct, fadeBefore.earned, fadeBefore.overUnder, fadeBefore.position],
  [0.5, 50000, 5000, 'over_billed']);
check('after doubling the EAC: 25% earned 25000, billed 55000 -> over-billed 30000',
  [fadeAfter.pct, fadeAfter.earned, fadeAfter.overUnder, fadeAfter.position],
  [0.25, 25000, 30000, 'over_billed']);
ok('PROFIT FADE IS VISIBLE -- the same costs against a revised EAC move earned '
   + 'revenue DOWN',
   fadeAfter.earned < fadeBefore.earned && fadeAfter.overUnder > fadeBefore.overUnder,
   'earned went ' + fadeBefore.earned + ' -> ' + fadeAfter.earned + ' and '
   + 'over/under went ' + fadeBefore.overUnder + ' -> ' + fadeAfter.overUnder);

section('4. THE EDGES -- zero and absent are not the same as computable');

const noBudget = scenario({ costs: [cost(0, 5000)] });
check('no forecast at all: percent complete is NULL, not 0%', noBudget.pct, null);
ok('...and that is a stated reason rather than a silent zero',
   (noBudget.forecastStale || []).length > 0,
   'forecastStale was ' + JSON.stringify(noBudget.forecastStale)
   + '. A job with real spend and no budget reported 0% complete, which is the '
   + 'most reassuring reading available and was reached by dividing by nothing.');
check('...and earned revenue is refused', noBudget.earned, null);
const noCosts = scenario({ costs: [] });
check('a job with no cost rows at all also refuses rather than reporting 0%',
  [noCosts.pct, noCosts.earned, noCosts.position], [null, null, 'unknown']);
const exact = scenario({ costs: [cost(100000, 100000)], draws: [draw(100000)] });
check('exactly at forecast is 100% and is NOT stale -- the boundary is not an overrun',
  [exact.pct, exact.forecastStale, exact.earned, exact.position],
  [1, [], 100000, 'level']);

section('5. THE FIGURES THAT LEAVE THE SCREEN -- the table, the KPI and the CSV');

// EVERY CONSUMER, because the budget-early-warning review found FOUR sites
// carrying one piece of arithmetic and the CSV was the one nobody checked --
// the number goes into a spreadsheet where no badge sits beside it to
// contradict it.
// THE WINDOW IS BOUNDED BY THE BLOCK'S OWN END, not by a character count. A
// fixed +1400 was the first draft and it silently truncated the block the
// moment the fix made it longer -- a window that shrinks to exclude the code it
// is meant to read reports the absence of whatever fell off the end.
const wipStart = src.indexOf("$('rp-wiptbody')");
const wipEnd = src.indexOf('No active jobs', wipStart);
if (wipStart < 0 || wipEnd < 0) { throw new Error('WIP table block not found'); }
const wipTable = src.slice(wipStart, wipEnd);
// THE ARM ASSERTS THE PATH, NOT ONE SPELLING OF IT, and the first draft of it
// did the opposite -- it looked for the literal `w.earned === null` and the fix
// routes both refusable figures through one `money()` helper instead, so a
// correct implementation failed. That is the same over-narrow-criteria mistake
// the anchor checker made this morning, in a test rather than a tool. It now
// requires BOTH halves: a null branch exists, and the two refusable figures go
// through it rather than to fmt() directly.
ok('the WIP table renders a REFUSAL rather than a blank when earned is null',
   /===\s*null/.test(wipTable)
   && /money\(w\.earned\)|w\.earned\s*===?\s*null/.test(wipTable)
   && /money\(w\.overUnder\)|w\.overUnder\s*===?\s*null/.test(wipTable),
   'the WIP table body does not route the refusable figures through a null '
   + 'branch, so `fmt(null)` decides what a reader sees -- and fmt() prints $0, '
   + 'which reads as a real zero. Window checked:\n' + wipTable.slice(0, 500));
ok('...and it shows the STALE marker against the forecast',
   /forecastStale/.test(wipTable),
   'the table never mentions forecastStale, so the one thing that says the '
   + 'denominator is wrong is invisible on the report');

const csvBlock = src.slice(src.indexOf("type==='reports_wip'"),
                           src.indexOf("type==='reports_wip'") + 900);
ok('the CSV export does not emit a percent it refused on screen',
   /forecastStale|=== *null|w\.position/.test(csvBlock),
   'the reports_wip export still writes Math.round(w.pct*100) and w.earned '
   + 'unconditionally, so a refused figure becomes a number in a spreadsheet');
ok('...and the CSV carries the forecast basis as its own column',
   /Forecast|Stale|Basis/i.test(csvBlock),
   'the export has no column saying whether the percent rests on an original '
   + 'budget or a revised forecast, which is the difference the whole fix is '
   + 'about');

const kpi = src.slice(src.indexOf('var overBilled='), src.indexOf('var overBilled=') + 700);
ok('the Over-Billed KPI counts a POSITION rather than a number greater than zero',
   /position\s*===\s*'over_billed'/.test(kpi),
   'it still filters on `jobWIP(j).overUnder>0`. With overUnder refused as '
   + 'null, `null > 0` is false, so every job whose forecast is stale drops '
   + 'SILENTLY out of the count -- a refusal turning into a clean bill, which '
   + 'is worse than the capped percentage it replaced');
ok('...and the jobs it could not judge are surfaced, not dropped',
   /unknown/.test(kpi),
   'nothing counts the jobs whose position is unknown, so they are invisible');

section('6. THE PROSE -- a fixed number under an unfixed sentence is not fixed');
ok('the panel note no longer defines % complete as cost over TOTAL ESTIMATED COST '
   + 'without saying which estimate',
   /revised|forecast|re-forecast/i.test(
     src.slice(src.indexOf('% Complete = cost to date'),
               src.indexOf('% Complete = cost to date') + 600)),
   'the note still reads "cost to date / total estimated cost" with no word '
   + 'about which estimate, which is the ambiguity that let the original '
   + 'budget sit in that slot for the life of the panel');

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
