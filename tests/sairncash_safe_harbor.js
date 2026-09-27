// tests/sairncash_safe_harbor.js
//
// REQUIREMENT: SAIRNcash must never recommend a quarterly set-aside BELOW the
//   IRS required annual payment / 4, because the underpayment penalty it exposes
//   the user to has no reasonable-cause waiver.
//
// Run:  node tests/sairncash_safe_harbor.js
//
// ── WRITTEN BEFORE THE FIX, ON PURPOSE ──────────────────────────────────────
// Every figure below is quoted from the 2026 Form 1040-ES, read directly rather
// than recalled. The arms were written and RUN against the broken code first;
// the failures they produced are recorded in the commit that fixes them. A
// regression test written after the fix only proves the fix is present, not that
// it was ever absent.
//
// ── THE DEFECT ──────────────────────────────────────────────────────────────
// 1040-ES, General Rule, verbatim: you owe a penalty unless your payments cover
// "the smaller of: a. 90% of the tax to be shown on your 2026 tax return, or
// b. 100% of the tax shown on your 2025 tax return."
//
// So `Math.min` IS the statute and is NOT the bug. The bug is the FIRST term.
// `calcQuarterlySetAside` computed it as
//
//     estAnnual = calcTotalTax(ytdNetProfit, ...)
//
// -- the tax on the profit earned SO FAR, labelled on screen as "Estimated
// annual tax (SE + federal income)". Early in the year that figure is near
// zero, `min` therefore selects it over the prior-year basis, and the app
// recommends a set-aside a fraction of the size of the one that avoids the
// penalty. The min is right; the thing being minimised was the wrong number.
//
// A freelancer on $120,000/yr with a $20,000 prior-year tax, asking on 31 March:
//   what the code said : 90% x tax($30,000)  -> about $1,350/quarter
//   what the IRS wants : min(90% x tax($120,000), 100% x $20,000)/4 -> $5,000
// A 73% shortfall, on a penalty with no reasonable-cause waiver (IRC 6654(e)
// provides only the de minimis, first-year, and casualty/disaster exceptions --
// "I used an app" is not among them).
//
// ── AND FOUR MORE, ALL VERIFIED AGAINST THE SAME DOCUMENT ──────────────────
// * MFS: 1040-ES line 12b, verbatim -- "If the AGI shown on your 2025 return is
//   more than $150,000 ($75,000 if married filing separately for 2026), enter
//   110% of your 2025 tax". One boolean called `prior_year_agi_over_150k` cannot
//   express two thresholds.
// * TAX YEAR: sumIncome()/sumDeductions() summed EVERY cached entry. Entries
//   carry a `date`, so the data was there and the aggregation ignored it -- the
//   figure called "YTD" was all-time.
// * QBI: 1040-ES Estimated Tax Worksheet line 2b is "If you can take the
//   qualified business income deduction, enter the estimated amount of the
//   deduction", and it reduces taxable income BEFORE the tax is figured.
//   Omitting it OVERSTATES the tax.
// * HoH 24% band: the 1040-ES Schedule Z top is $201,750. The app had $201,775,
//   which is SINGLE's figure (Schedule X). A $25 copy.
//
// ── WHAT IS DELIBERATELY NOT ASSERTED ──────────────────────────────────────
// Nothing here says any figure is filing-ready. These arms check that the app
// does not recommend LESS than the safe harbor, that its own labels describe
// what it computed, and that where it cannot know something it says so. Whether
// a user's real return matches is not a thing a static test can decide.

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const FILE = path.resolve(__dirname, '..', 'sairncash.html');
const src = fs.readFileSync(FILE, 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

// ── THE LIFT. The app's own functions are RUN here, never reimplemented: a
// copy of the tax maths in a test is a second declaration of the answer, and
// the two drift. Same discipline as tests/sairnbiz_1099_threshold.js.
function lift(name) {
  const at = src.indexOf('function ' + name + '(');
  assert.notStrictEqual(at, -1, 'function ' + name + ' not found in sairncash.html');
  const end = src.indexOf('\n}', at);
  assert.notStrictEqual(end, -1, name + ' has no column-0 closing brace');
  return src.slice(at, end + 2);
}
// A const declaration may be one line (`const X = {a:1};`) or a block ending
// in a column-0 `};`. The first version of this handled only the block form and
// reported a present constant as missing -- which aborted the whole suite and
// looked exactly like an unfixed app.
function liftConst(name) {
  const at = src.indexOf('const ' + name + ' = ');
  assert.notStrictEqual(at, -1, 'const ' + name + ' not found in sairncash.html');
  const lineEnd = src.indexOf('\n', at);
  const oneLine = src.slice(at, lineEnd);
  if (/;\s*$/.test(oneLine)) return oneLine;
  const end = src.indexOf('\n};', at);
  assert.notStrictEqual(end, -1,
    name + ' is neither a one-line declaration nor a block with a column-0 '
    + 'closing brace, so it cannot be lifted');
  return src.slice(at, end + 3);
}

const ctx = vm.createContext({ console: console });
const NEEDED_CONSTS = ['TAX_YEAR_2026'];
const NEEDED_FNS = ['calcSeTax', 'calcAdditionalMedicare', 'bracketTax',
                    'calcTotalTax', 'calcQuarterlySetAside'];
// Functions the FIX introduces. Lifted if present, and their absence is a
// FAILURE with the reason named -- not a skip, which would make a missing fix
// look like a passing test.
const FIX_FNS = ['projectAnnualFromYtd', 'calcQbiDeduction', 'entriesForTaxYear',
                 'safeHarborAgiThreshold'];
const FIX_CONSTS = ['SAFE_HARBOR_110_AGI_THRESHOLD', 'QBI_CERTAIN_CEILING',
                    'QBI_MIN_DEDUCTION', 'QBI_MIN_QBI_FOR_MINIMUM'];

const missing = [];
for (const c of NEEDED_CONSTS.concat(FIX_CONSTS)) {
  try { vm.runInContext(liftConst(c), ctx); } catch (e) { missing.push('const ' + c); }
}
for (const f of NEEDED_FNS.concat(FIX_FNS)) {
  try { vm.runInContext(lift(f), ctx); } catch (e) { missing.push('function ' + f); }
}

(function () {
  console.log('SAIRNCASH SAFE HARBOR -- the app must never recommend less than the IRS floor');
  if (missing.length) {
    console.log('  MISSING FROM sairncash.html (not a skip -- these are failures):');
    missing.forEach(function (m) { console.log('    ' + m); });
  }

  section('THE LIFT ITSELF -- without this every arm below is vacuous');
  test('every function and constant the arms need is present', function () {
    assert.deepStrictEqual(missing, [],
      'missing: ' + JSON.stringify(missing) + '. An absent function is not a '
      + 'skipped check; the arms below would pass on a stub and this is the '
      + 'only place that can say so.');
  });
  if (missing.length) {
    console.log('\n' + pass + ' passed, ' + (fail) + ' failed'
      + '  -- ABORTING: the lift is incomplete, so no behaviour was checked.');
    process.exit(1);
  }

  // `const` in a vm script lands in the context's global LEXICAL scope, not as
  // a property of the sandbox object -- so `ctx.TAX_YEAR_2026` is undefined
  // while the lifted functions can see it perfectly. Read it as an expression.
  // The first version of this read the property and got `undefined`, which made
  // two real bracket arms fail with "Cannot read properties of undefined"
  // instead of comparing anything.
  const evalIn = function (expr) { return vm.runInContext(expr, ctx); };
  const T = evalIn('TAX_YEAR_2026');
  const SH = evalIn('SAFE_HARBOR_110_AGI_THRESHOLD');
  // Copied OUT of the vm realm into a host array, for the same prototype
  // reason as above.
  const bandTops = function (status) {
    const out = [];
    for (let i = 0; i < 6; i++) out.push(T.brackets[status][i][0]);
    return out;
  };
  const taxOn = function (profit, status) {
    return ctx.calcTotalTax(profit, status, 0).totalTax;
  };

  // ── ITEM 1 ──────────────────────────────────────────────────────────────
  section('1. THE CURRENT-YEAR LEG MUST BE AN ANNUALISED PROJECTION');

  test('a freelancer 3 months in is not told to set aside a quarter of the right figure', function () {
    // $10,000/month. On 31 March, YTD = $30,000, annual pace = $120,000.
    // 1040-ES: required annual payment = smaller of 90% of 2026 tax, or 100%
    // of 2025 tax ($20,000 here, AGI under the threshold).
    const r = ctx.calcQuarterlySetAside(30000, 'single', 20000, 80000,
                                        new Date('2026-03-31T12:00:00Z'));
    const correctAnnual = Math.min(0.9 * taxOn(120000, 'single'), 20000);
    assert.ok(Math.abs(r.quarterlyAmount - correctAnnual / 4) < 1,
      'recommended $' + r.quarterlyAmount.toFixed(2) + '/quarter; the IRS floor '
      + 'is $' + (correctAnnual / 4).toFixed(2) + '. The current-year leg is '
      + 'being computed on the $30,000 earned so far instead of the $120,000 '
      + 'annual pace, so `min` selects a near-zero basis. This is the defect: '
      + 'the penalty it exposes has no reasonable-cause waiver.');
  });

  test('the WORST case -- no prior-year figure, January -- is not near zero', function () {
    // The prior-year leg is what accidentally rescued the earlier arm. With no
    // prior-year tax there is nothing to min against, so the YTD bug is the
    // whole answer and the shortfall is unbounded.
    const r = ctx.calcQuarterlySetAside(12500, 'single', null, null,
                                        new Date('2026-01-31T12:00:00Z'));
    const correct = 0.9 * taxOn(150000, 'single') / 4;
    assert.ok(r.quarterlyAmount > correct * 0.9,
      'recommended $' + r.quarterlyAmount.toFixed(2) + '/quarter on a $150,000 '
      + 'annual pace; 90% of the projected annual tax is $' + correct.toFixed(2)
      + '/quarter. Tax on one month of profit is not "the tax to be shown on '
      + 'your 2026 tax return".');
  });

  test('`estAnnual` is the projected ANNUAL tax, because the screen calls it that', function () {
    const r = ctx.calcQuarterlySetAside(30000, 'single', null, null,
                                        new Date('2026-03-31T12:00:00Z'));
    // ASSERTED AGAINST THE PROJECTION THE CODE REPORTS, not against a round
    // number. 31 March noon is ~0.2452 of the year, not 0.25 -- the first
    // version of this arm expected tax($120,000) exactly and failed by $684 on
    // CORRECT code. A test that hardcodes a calendar fraction that does not
    // exist is asserting its own arithmetic, not the app's.
    assert.ok(Math.abs(r.estAnnual - taxOn(r.projectedAnnualProfit, 'single')) < 1,
      'estAnnual is $' + Number(r.estAnnual).toFixed(2) + ' but the tax on the '
      + 'projection it reports ($' + Number(r.projectedAnnualProfit).toFixed(2)
      + ') is $' + taxOn(r.projectedAnnualProfit, 'single').toFixed(2)
      + '. The UI labels this field "Estimated annual tax (SE + federal '
      + 'income)". A field whose label says annual and whose value is '
      + 'year-to-date is the fabricated-figure shape, not a rounding question.');
    assert.ok(Math.abs(r.projectedAnnualProfit - 120000) / 120000 < 0.03,
      'projectedAnnualProfit is ' + r.projectedAnnualProfit + '; $30,000 at the '
      + 'end of Q1 annualises to about $120,000 (within 3% -- the quarter is '
      + 'not exactly a quarter of a 365-day year). The projection must be '
      + 'REPORTED, not just used, or a reader cannot tell which number the '
      + 'estimate rests on.');
  });

  test('min() IS the statute -- the prior-year basis wins when it is smaller', function () {
    // Income UP this year: 90% of the bigger current-year tax exceeds last
    // year's tax, so the prior-year basis is the legal floor and the app must
    // NOT recommend the larger figure. Over-recommending is not a penalty, but
    // it is still the wrong answer and it is the user's cash.
    const r = ctx.calcQuarterlySetAside(100000, 'single', 8000, 40000,
                                        new Date('2026-06-30T12:00:00Z'));
    assert.strictEqual(Math.round(r.safeHarborBasis), 8000,
      'basis was ' + Math.round(r.safeHarborBasis) + '; last year\'s tax of '
      + '$8,000 is smaller than 90% of this year\'s projected tax and is '
      + 'therefore the required annual payment (1040-ES line 12c: "Enter the '
      + 'smaller of line 12a or 12b").');
  });

  test('...and 90% of the projection wins when income genuinely dropped', function () {
    const r = ctx.calcQuarterlySetAside(5000, 'single', 40000, 200000,
                                        new Date('2026-06-30T12:00:00Z'));
    // Same correction as above: 30 June noon is ~0.4959 of the year, so the
    // projection is about $10,083 rather than exactly $10,000.
    const ninety = 0.9 * taxOn(r.projectedAnnualProfit, 'single');
    assert.ok(Math.abs(r.safeHarborBasis - ninety) < 1,
      'basis was ' + r.safeHarborBasis.toFixed(2) + ', expected 90% of the '
      + 'projected tax (' + ninety.toFixed(2) + '). A user whose income '
      + 'collapsed must not be held to 110% of a big prior year -- that is what '
      + 'the 90% leg is for.');
  });

  test('a mid-quarter date projects on elapsed time, and reports the fraction', function () {
    const r = ctx.calcQuarterlySetAside(50000, 'single', null, null,
                                        new Date('2026-07-02T12:00:00Z'));
    assert.ok(r.elapsedFraction > 0.49 && r.elapsedFraction < 0.51,
      'elapsedFraction was ' + r.elapsedFraction + ' on 2 July; about 0.5 was '
      + 'expected. The projection is only as good as this number and it is '
      + 'returned so a caller can show it.');
  });

  test('1 January does not divide by zero or project an infinite profit', function () {
    const r = ctx.calcQuarterlySetAside(0, 'single', 20000, 80000,
                                        new Date('2026-01-01T00:00:01Z'));
    assert.ok(isFinite(r.projectedAnnualProfit) && isFinite(r.quarterlyAmount),
      'projection was ' + r.projectedAnnualProfit + ' and the quarterly figure '
      + 'was ' + r.quarterlyAmount + '. On the first day of the year the '
      + 'elapsed fraction is ~0 and a naive divide produces Infinity or NaN, '
      + 'which renders as "$NaN" beside a tax deadline.');
    assert.strictEqual(Math.round(r.quarterlyAmount), 5000,
      'with no profit yet, the prior-year basis ($20,000) is the only real '
      + 'number available and must be what is recommended; got '
      + r.quarterlyAmount);
  });

  // ── ITEM 2 ──────────────────────────────────────────────────────────────
  section('2. THE 110% TRIGGER IS $75,000 FOR MFS, NOT $150,000');

  test('the threshold table matches the 1040-ES verbatim figures', function () {
    assert.strictEqual(SH.mfs, 75000,
      'MFS threshold is ' + SH.mfs + '. 1040-ES '
      + 'line 12b: "more than $150,000 ($75,000 if married filing separately '
      + 'for 2026)".');
    ['single', 'hoh', 'mfj'].forEach(function (s) {
      assert.strictEqual(SH[s], 150000,
        s + ' threshold is ' + SH[s]
        + ', expected 150000');
    });
  });

  test('an MFS filer with $80,000 prior-year AGI gets 110%', function () {
    const r = ctx.calcQuarterlySetAside(200000, 'mfs', 30000, 80000,
                                        new Date('2026-06-30T12:00:00Z'));
    assert.strictEqual(r.priorYearPct, 1.10,
      'priorYearPct was ' + r.priorYearPct + '. $80,000 is over the MFS '
      + '$75,000 threshold, so the prior-year basis is 110% x $30,000 = '
      + '$33,000. At 100% this user is $3,000 short for the year and the '
      + 'penalty has no reasonable-cause waiver.');
    assert.strictEqual(Math.round(r.priorYearBasis), 33000,
      'priorYearBasis was ' + Math.round(r.priorYearBasis));
  });

  test('a SINGLE filer with the same $80,000 AGI gets 100%', function () {
    const r = ctx.calcQuarterlySetAside(200000, 'single', 30000, 80000,
                                        new Date('2026-06-30T12:00:00Z'));
    assert.strictEqual(r.priorYearPct, 1.0,
      'priorYearPct was ' + r.priorYearPct + ' for a single filer at $80,000, '
      + 'which is under $150,000. Applying 110% here over-collects -- it is not '
      + 'a penalty risk, but it is still the wrong number and it is the user\'s '
      + 'cash.');
  });

  test('an MFS filer at $70,000 gets 100% -- the threshold is not simply lowered for everyone', function () {
    const r = ctx.calcQuarterlySetAside(200000, 'mfs', 30000, 70000,
                                        new Date('2026-06-30T12:00:00Z'));
    assert.strictEqual(r.priorYearPct, 1.0,
      'priorYearPct was ' + r.priorYearPct + ' at $70,000 MFS, under the '
      + '$75,000 threshold.');
  });

  test('a LEGACY profile carrying only the old over-$150k boolean is marked UNCERTAIN, not guessed', function () {
    // THE MIGRATION HAZARD, AND IT ONLY BITES MFS. The stored field was
    // `prior_year_agi_over_150k`. An MFS user with $90,000 of prior-year AGI
    // correctly answered NO to that question and is over their real $75,000
    // threshold -- so silently reading the old boolean under-recommends exactly
    // the users this fix is for. It must be surfaced, not resolved by
    // assumption.
    const legacy = ctx.calcQuarterlySetAside(200000, 'mfs', 30000,
                                             { legacyOver150k: false },
                                             new Date('2026-06-30T12:00:00Z'));
    assert.strictEqual(legacy.agiBasisUncertain, true,
      'an MFS profile with only the legacy boolean reported '
      + 'agiBasisUncertain=' + legacy.agiBasisUncertain + '. The old field '
      + 'asked about $150,000; the MFS threshold is $75,000, so a "no" answer '
      + 'does not establish that 110% is inapplicable.');
    const legacySingle = ctx.calcQuarterlySetAside(200000, 'single', 30000,
                                                   { legacyOver150k: false },
                                                   new Date('2026-06-30T12:00:00Z'));
    assert.strictEqual(legacySingle.agiBasisUncertain, false,
      'a SINGLE profile with the legacy boolean is NOT uncertain -- the old '
      + 'question and the real threshold are the same $150,000. Marking it '
      + 'uncertain anyway would make the warning meaningless by appearing for '
      + 'everybody.');
  });

  // ── ITEM 3 ──────────────────────────────────────────────────────────────
  section('3. ENTRIES MUST BE SPLIT BY TAX YEAR');

  test('last year\'s entries do not count toward this year', function () {
    const entries = [
      { amount: 5000, date: '2025-11-02T10:00:00Z' },
      { amount: 7000, date: '2026-02-11T10:00:00Z' },
      { amount: 3000, date: '2026-12-30T10:00:00Z' }
    ];
    const r = ctx.entriesForTaxYear(entries, 2026);
    assert.strictEqual(r.entries.length, 2,
      'kept ' + r.entries.length + ' of 3 entries for 2026. The $5,000 from '
      + 'November 2025 is last year\'s income and inflates both the projection '
      + 'and the tax.');
    assert.strictEqual(r.entries.reduce(function (s, e) { return s + e.amount; }, 0),
      10000, 'the 2026 total is wrong');
  });

  test('an entry that cannot be placed in a year is COUNTED, not dropped', function () {
    // Dropping it understates income and the set-aside; counting it silently
    // may put last year's money in this year. Neither is decidable here, so it
    // is surfaced -- the third state, same as everywhere else on this platform.
    const entries = [
      { amount: 7000, date: '2026-02-11T10:00:00Z' },
      { amount: 2000 },
      { amount: 400, date: 'not a date' }
    ];
    const r = ctx.entriesForTaxYear(entries, 2026);
    assert.strictEqual(r.unplaceable.length, 2,
      'unplaceable was ' + r.unplaceable.length + ', expected 2. An entry with '
      + 'no readable date is real money that cannot be attributed to a year. '
      + 'Silently dropping it understates the set-aside; silently keeping it '
      + 'may book last year\'s income this year. It gets reported.');
    assert.ok(r.entries.every(function (e) { return e.amount !== 2000; }),
      'an undated entry was folded into the year total without being '
      + 'distinguishable from a dated one.');
  });

  test('created_at is the fallback, because addIncomeEntry always writes it', function () {
    const ts = Date.UTC(2026, 4, 1);
    const r = ctx.entriesForTaxYear([{ amount: 900, created_at: ts }], 2026);
    assert.strictEqual(r.entries.length, 1,
      'an entry with created_at but no `date` was not placed. Both writers set '
      + 'created_at, so treating its absence as unplaceable would report a '
      + 'problem that does not exist.');
    assert.strictEqual(r.unplaceable.length, 0);
  });

  test('the app actually CALLS the year split -- BOTH totals, checked separately', function () {
    // ── THE ABLATION THAT CAUGHT THIS ARM BEING DEAD ────────────────────
    // The first version sliced the region BETWEEN sumIncome and sumDeductions
    // and searched it for `entriesForTaxYear`. Unwiring sumIncome alone left
    // all 31 arms green, because sumDeductions' call was inside the region. One
    // of two halves wired is exactly the half-fix this arm exists to catch, and
    // it is the third time today a presence check stood in for a per-site one.
    // Each body is now sliced and asserted on its own.
    ['sumIncome', 'sumDeductions'].forEach(function (fn) {
      const at = src.indexOf('function ' + fn + '(');
      assert.notStrictEqual(at, -1, fn + ' is gone');
      const end = src.indexOf('\n}', at);
      const body = src.slice(at, end);
      assert.ok(/entriesForTaxYear/.test(body),
        fn + '() does not go through entriesForTaxYear, so its total is still '
        + 'ALL-TIME rather than this tax year. Body was:\n' + body);
      assert.ok(/currentTaxYear\(\)/.test(body),
        fn + '() calls entriesForTaxYear but not with currentTaxYear(), so '
        + 'whichever year it is filtering to, it is not this one.');
    });
  });

  // ── ITEM 4 ──────────────────────────────────────────────────────────────
  section('4. THE QBI DEDUCTION -- applied, or disclosed, never silently absent');

  test('the QBI deduction is applied and REDUCES the tax', function () {
    const withQbi = ctx.calcTotalTax(100000, 'single', 0, { applyQbi: true }).totalTax;
    const without = ctx.calcTotalTax(100000, 'single', 0, { applyQbi: false }).totalTax;
    assert.ok(withQbi < without,
      'tax with QBI (' + withQbi.toFixed(2) + ') is not lower than without ('
      + without.toFixed(2) + '). 1040-ES Estimated Tax Worksheet line 2b takes '
      + 'the deduction off taxable income before the tax is figured, so '
      + 'omitting it OVERSTATES what the user must set aside.');
  });

  test('it is 20% of QBI, capped at 20% of taxable income before the deduction', function () {
    const d = ctx.calcQbiDeduction(80000, 60000, 'single');
    assert.ok(Math.abs(d.deduction - 12000) < 1,
      'deduction was ' + d.deduction + '; 20% of $60,000 taxable income is '
      + '$12,000, which is lower than 20% of $80,000 QBI and is therefore the '
      + 'cap that binds.');
  });

  test('the $400 minimum applies from $1,000 of QBI (2026, new)', function () {
    // 1040-ES What's New, verbatim: "beginning in 2026, if you have a minimum
    // of $1,000 in total qualified business income from an active trade or
    // business, you may be able to claim a minimum QBID of $400."
    const d = ctx.calcQbiDeduction(1500, 40000, 'single');
    assert.ok(d.deduction >= 400,
      'deduction was ' + d.deduction + ' on $1,500 of QBI. 20% would be $300; '
      + 'the 2026 minimum is $400.');
    const below = ctx.calcQbiDeduction(900, 40000, 'single');
    assert.ok(below.deduction < 400,
      'the $400 minimum was applied at $900 of QBI, below the stated $1,000 '
      + 'floor.');
  });

  test('THE HONEST PART -- above the phase-in it says it cannot tell', function () {
    // The W-2 wage / UBIA limits and the SSTB phase-out begin at a taxable
    // income threshold this session COULD NOT VERIFY for 2026: the 1040-ES and
    // Pub 505 both give only the phase-in RANGE ($150,000 MFJ / $75,000 other)
    // and neither states the threshold. So the simple 20% rule is applied where
    // it is right and the estimate is marked UNCERTAIN where it may not be --
    // rather than a guessed constant, which is the failure this whole codebase
    // keeps recording.
    const high = ctx.calcQbiDeduction(400000, 380000, 'single');
    assert.strictEqual(high.certain, false,
      'a $380,000 taxable income reported certain=' + high.certain + '. Above '
      + 'the 199A threshold the W-2/UBIA limits and the SSTB phase-out apply '
      + 'and the flat 20% is not the answer.');
    assert.ok(/not verif|could not|unverified/i.test(String(high.note)),
      'the note does not say the threshold is unverified: ' + high.note);
    const low = ctx.calcQbiDeduction(50000, 40000, 'single');
    assert.strictEqual(low.certain, true,
      'a $40,000 taxable income reported certain=' + low.certain + '. Marking '
      + 'every figure uncertain is the same as marking none.');
  });

  // ── ITEM 5 ──────────────────────────────────────────────────────────────
  section('5. HoH AND MFS BRACKETS, against the 2026 Form 1040-ES');

  test('HoH band tops match Schedule Z -- including the $201,750 that is NOT single\'s', function () {
    // Schedule Z, 2026 Form 1040-ES. Every boundary re-derived from the
    // cumulative tax figures printed on the form rather than read off a
    // mangled column: 1,770 / 7,740 / 16,155 / 39,207 / 56,631 / 191,171.
    const want = [17700, 67450, 105700, 201750, 256200, 640600];
    // JOINED, NOT deepStrictEqual. `T` comes out of the vm context, so
    // T.brackets.hoh is an Array with the VM realm's Array.prototype --
    // deepStrictEqual compares prototypes and fails on two arrays whose
    // contents are identical, printing them side by side looking the same.
    // That cost a confusing red run; the shape of the comparison is the fix.
    const got = bandTops('hoh');
    assert.strictEqual(got.join(','), want.join(','),
      'HoH band tops are ' + JSON.stringify(got) + ', expected '
      + JSON.stringify(want) + '. The 24% top is $201,750 on Schedule Z; '
      + '$201,775 is SINGLE\'s figure from Schedule X. Copying it across is the '
      + 'same defect class as the formulary\'s cross-species dose.');
  });

  test('MFS band tops match Schedule Y-2', function () {
    const want = [12400, 50400, 105700, 201775, 256225, 384350];
    const got = bandTops('mfs');
    assert.strictEqual(got.join(','), want.join(','),
      'MFS band tops are ' + JSON.stringify(got) + ', expected '
      + JSON.stringify(want));
  });

  test('the HoH cumulative tax at each band top matches the form', function () {
    // THE REAL CHECK. Band tops alone can be right while the rates are wrong;
    // these six figures are printed on the form and pin both at once.
    [[17700, 1770], [67450, 7740], [105700, 16155],
     [201750, 39207], [256200, 56631], [640600, 191171]].forEach(function (p) {
      const got = ctx.bracketTax(p[0], 'hoh');
      assert.ok(Math.abs(got - p[1]) < 1,
        'bracketTax(' + p[0] + ', hoh) = ' + got.toFixed(2) + ', the 1040-ES '
        + 'Schedule Z says ' + p[1]);
    });
  });

  test('the MFS cumulative tax at each band top matches the form', function () {
    [[12400, 1240], [50400, 5800], [105700, 17966],
     [201775, 41024], [256225, 58448], [384350, 103291.75]].forEach(function (p) {
      const got = ctx.bracketTax(p[0], 'mfs');
      assert.ok(Math.abs(got - p[1]) < 1,
        'bracketTax(' + p[0] + ', mfs) = ' + got.toFixed(2) + ', the 1040-ES '
        + 'Schedule Y-2 says ' + p[1]);
    });
  });

  test('CONTROL -- single and MFJ still match too, so a shared edit cannot pass unnoticed', function () {
    [[12400, 1240, 'single'], [50400, 5800, 'single'], [105700, 17966, 'single'],
     [201775, 41024, 'single'], [256225, 58448, 'single'], [640600, 192979.25, 'single'],
     [24800, 2480, 'mfj'], [100800, 11600, 'mfj'], [211400, 35932, 'mfj'],
     [403550, 82048, 'mfj'], [512450, 116896, 'mfj'], [768700, 206583.50, 'mfj']
    ].forEach(function (p) {
      const got = ctx.bracketTax(p[0], p[2]);
      assert.ok(Math.abs(got - p[1]) < 1,
        'bracketTax(' + p[0] + ', ' + p[2] + ') = ' + got.toFixed(2)
        + ', the 1040-ES says ' + p[1]);
    });
  });

  // ── ITEM 6 ──────────────────────────────────────────────────────────────
  section('6. THE 1099-K THRESHOLD -- and the thing it is NOT');

  test('no WRONG 1099-K figure is present anywhere in the app', function () {
    // Checked across the whole repository before anything was written: there was
    // no 1099-K reference at all, in any file. So there was no wrong number to
    // correct -- the finding was an ABSENCE, in an app whose users are paid
    // through exactly the platforms that file this form.
    const bad = [/\$?600\b[^)]{0,40}1099-?K/i, /1099-?K[^.]{0,60}\$?600\b/i,
                 /1099-?K[^.]{0,60}\$?2,?000\b/i, /1099-?K[^.]{0,60}\$?5,?000\b/i];
    bad.forEach(function (re) {
      assert.ok(!re.test(src),
        'the app pairs a 1099-K with the wrong threshold (matched ' + re + '). '
        + '2026 is over $20,000 AND more than 200 transactions. $600 was the '
        + 'ARPA figure that never took effect, $2,000 is the 1099-NEC threshold '
        + 'fixed separately in SAIRNbiz, and $5,000 was a transition year.');
    });
  });

  test('the AI is told BOTH conditions, because either alone is wrong', function () {
    assert.ok(/\$20,000 AND more than 200 transactions/.test(src),
      'the system prompt does not state both 1099-K conditions. Over $20,000 on '
      + 'its own is not the threshold -- the transaction count must also be '
      + 'exceeded, and a freelancer with $50,000 across 40 invoices is under it.');
  });

  test('...and that it is a PAYER filing rule, not an income-reporting floor', function () {
    // THE ARM THAT MATTERS. The dangerous misreading is not the number, it is
    // "no 1099-K arrived, so I do not report it". An app for self-employed
    // people must never leave that available.
    assert.ok(/NOT a threshold on what the user owes tax on/i.test(src),
      'the prompt states the threshold without stating what it is not. The '
      + 'threshold governs when the PLATFORM files the form; the income is '
      + 'taxable either way, and platforms send the form below the threshold '
      + 'too.');
    assert.ok(/[Nn]ever tell a user that income under \$20,000/.test(src),
      'the prompt does not explicitly forbid the "under the threshold so not '
      + 'reportable" answer, which is the one that costs the user money.');
  });

  // ── CONTROLS ────────────────────────────────────────────────────────────
  section('CONTROL -- these arms must be able to fail');

  test('the lifted functions are the real ones and really run', function () {
    assert.strictEqual(typeof ctx.calcQuarterlySetAside, 'function');
    // Without this, a stub returning one value satisfies most arms above.
    const a = ctx.calcQuarterlySetAside(30000, 'single', null, null,
                                        new Date('2026-03-31T12:00:00Z'));
    const b = ctx.calcQuarterlySetAside(30000, 'single', null, null,
                                        new Date('2026-12-31T12:00:00Z'));
    assert.notStrictEqual(Math.round(a.quarterlyAmount), Math.round(b.quarterlyAmount),
      'the same YTD profit on 31 March and 31 December produces the same '
      + 'recommendation, so the date is not being used at all and every '
      + 'projection arm above is checking one value twice.');
  });

  test('the file really is sairncash.html and is big enough to be the app', function () {
    assert.ok(src.length > 80000, 'sairncash.html read as ' + src.length
      + ' bytes -- too small to be the app, so any absence assertion above is '
      + 'vacuous.');
    assert.ok(src.indexOf('Estimated annual tax') !== -1,
      'the string "Estimated annual tax" is absent, so the label arm is not '
      + 'checking the thing it names.');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
