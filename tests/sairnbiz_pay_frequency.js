// tests/sairnbiz_pay_frequency.js
//
// Run:  node tests/sairnbiz_pay_frequency.js
//
// SAIRNbiz pay frequency and benefit proration, tested where it can actually
// be wrong. Every assertion here corresponds to a real defect that shipped:
//
//   * 80h/32h was BIWEEKLY hard-coded as if it were universal, so a monthly-paid
//     salesperson was costed at two weeks' hours;
//   * $520 was a MONTHLY employer benefit charged once per PAY PERIOD, which on
//     a biweekly cycle billed $13,520/yr for a $6,240 benefit;
//   * the real per-employee `ben.cost` an owner typed into the Benefits panel
//     was never read at all;
//   * ytd_payroll extrapolated gross x 13 while 80h implied 26 periods, so the
//     app contradicted itself about how long a year is.
//
// None of those throw. Each is a green app producing a confident wrong number,
// which is why these assertions check ARITHMETIC rather than absence of errors.
//
// The functions are lifted out of the real file rather than reimplemented, so a
// change to sairnbiz.html that breaks them fails here.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

// Line endings normalised so the slice markers can be written with plain \n --
// same reason tests/sairnbuild_server_backup.js does it.
const html = fs.readFileSync(path.join(__dirname, '..', 'sairnbiz.html'), 'utf8')
  .replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

// Anchored on the source itself rather than line numbers, which move.
function slice(startMark, endMark) {
  const a = html.indexOf(startMark);
  assert.ok(a > 0, 'not found in sairnbiz.html: ' + startMark);
  const b = html.indexOf(endMark, a);
  assert.ok(b > a, 'end marker not found after ' + startMark);
  return html.slice(a, b);
}

const helpersSrc = slice('var SB_PAY_FREQ = {', 'function sbPayrollTotals(){');
const totalsSrc = slice('function sbPayrollTotals(){', '\nfunction rPay()');
const hiringSrc = slice('function computeHiringCostImpact(', '\nfunction rDash()');

function harness(roster) {
  const store = { sb_emps: JSON.stringify(roster || []) };
  const ctx = {
    console, JSON, Math, Number, Object, isFinite,
    ld: (k, d) => { try { const r = store[k]; return r === undefined ? d : JSON.parse(r); } catch (e) { return d; } }
  };
  vm.createContext(ctx);
  vm.runInContext(helpersSrc + '\n' + totalsSrc + '\n' + hiringSrc, ctx);
  return ctx;
}

const near = (a, b, tol, msg) =>
  assert.ok(Math.abs(a - b) < (tol === undefined ? 0.01 : tol),
    (msg || '') + ' expected ~' + b + ', got ' + a);

const FT = (extra) => Object.assign({ status: 'Active', type: 'Full Time', rate: 30 }, extra || {});
const PT = (extra) => Object.assign({ status: 'Active', type: 'Part Time', rate: 30 }, extra || {});

// ── 1. BACKWARDS COMPATIBILITY IS EXACT, NOT APPROXIMATE ──────────────────
// The whole change is safe only if an existing roster with no pay_freq keeps
// producing the numbers it produced yesterday. 40 x 52 / 26 must be exactly 80.
section('backwards compatibility: an existing roster does not move');

test('full time with no frequency recorded is still 80 hours', () => {
  const c = harness([]);
  assert.strictEqual(c.sbHoursPerPeriod(FT()), 80);
});

test('part time with no frequency recorded is still 32 hours', () => {
  const c = harness([]);
  assert.strictEqual(c.sbHoursPerPeriod(PT()), 32);
});

test('gross per period for an unmigrated employee is unchanged', () => {
  const c = harness([]);
  assert.strictEqual(c.sbGrossPerPeriod(FT({ rate: 30 })), 2400);
});

// ── 2. FREQUENCY DRIVES HOURS ─────────────────────────────────────────────
section('hours per period follow the employee, not the app');

test('weekly full time is 40 hours', () => {
  const c = harness([]);
  assert.strictEqual(c.sbHoursPerPeriod(FT({ pay_freq: 'Weekly' })), 40);
});

test('semi-monthly full time is 86.67 hours', () => {
  const c = harness([]);
  near(c.sbHoursPerPeriod(FT({ pay_freq: 'Semi-monthly' })), 86.67);
});

test('monthly full time is 173.33 hours', () => {
  const c = harness([]);
  near(c.sbHoursPerPeriod(FT({ pay_freq: 'Monthly' })), 173.33);
});

test('an unrecognised stored frequency falls back rather than producing NaN', () => {
  const c = harness([]);
  // A bad string must not make payroll NaN. This is the failure mode that
  // would be invisible: NaN formats as "$NaN" in one KPI and silently
  // poisons every total it is added to.
  assert.strictEqual(c.sbPayFreq(FT({ pay_freq: 'Fortnightly' })), 'Biweekly');
  assert.strictEqual(c.sbHoursPerPeriod(FT({ pay_freq: 'Fortnightly' })), 80);
  assert.strictEqual(c.sbPayFreqIsDefault(FT({ pay_freq: 'Fortnightly' })), true);
});

test('a recorded frequency is not reported as a default', () => {
  const c = harness([]);
  assert.strictEqual(c.sbPayFreqIsDefault(FT({ pay_freq: 'Monthly' })), false);
});

// ── 3. ANNUAL PAY IS FREQUENCY-INDEPENDENT ────────────────────────────────
// This is the property that makes the whole model defensible: changing how
// often someone is paid must not change what they are paid in a year.
section('changing frequency never changes annual pay');

test('the same employee annualises identically on all four cycles', () => {
  const c = harness([]);
  const expected = 30 * 40 * 52; // 62,400
  ['Weekly', 'Biweekly', 'Semi-monthly', 'Monthly'].forEach((f) => {
    assert.strictEqual(c.sbAnnualGross(FT({ pay_freq: f })), expected, 'on ' + f);
  });
});

test('per-period gross x periods-per-year reconstructs annual gross', () => {
  const c = harness([]);
  ['Weekly', 'Biweekly', 'Semi-monthly', 'Monthly'].forEach((f) => {
    const e = FT({ pay_freq: f });
    near(c.sbGrossPerPeriod(e) * c.sbPeriodsPerYear(e), c.sbAnnualGross(e), 1, 'on ' + f);
  });
});

// ── 4. THE BENEFIT BUG ────────────────────────────────────────────────────
// $520 is a MONTHLY figure. Charged once per biweekly period it costs $13,520
// a year instead of $6,240 -- the 2.17x overstatement that was live.
section('benefits prorate from a monthly figure');

test('the default benefit prorates to $240 on a biweekly cycle', () => {
  const c = harness([]);
  near(c.sbBenefitPerPeriod(FT()), 520 * 12 / 26); // 240
});

test('the default benefit is the full $520 on a monthly cycle', () => {
  const c = harness([]);
  near(c.sbBenefitPerPeriod(FT({ pay_freq: 'Monthly' })), 520);
});

test('annual benefit cost is $6,240 on every cycle, not $13,520 on some', () => {
  const c = harness([]);
  ['Weekly', 'Biweekly', 'Semi-monthly', 'Monthly'].forEach((f) => {
    const e = FT({ pay_freq: f });
    near(c.sbBenefitPerPeriod(e) * c.sbPeriodsPerYear(e), 6240, 0.01, 'on ' + f);
  });
});

test('THE ORIGINAL DEFECT: the recorded employer cost is actually read', () => {
  const c = harness([]);
  const e = FT({ pay_freq: 'Monthly', ben: { health: true, cost: 840 } });
  // Before the fix this returned 520 no matter what the owner typed.
  near(c.sbBenefitPerPeriod(e), 840);
  assert.strictEqual(c.sbBenefitIsAssumed(e), false);
});

test('a recorded cost prorates too, rather than being charged whole per period', () => {
  const c = harness([]);
  near(c.sbBenefitPerPeriod(FT({ pay_freq: 'Biweekly', ben: { cost: 840 } })), 840 * 12 / 26);
});

test('a blank or zero cost counts as not recorded, not as a real $0', () => {
  const c = harness([]);
  // saveBenEnroll() writes 0 for an empty field. Treating that as a genuine
  // $0 benefit would understate labour cost for every unenrolled employee.
  const e = FT({ ben: { health: false, cost: 0 } });
  assert.strictEqual(c.sbBenefitIsAssumed(e), true);
  near(c.sbBenefitPerPeriod(e), 520 * 12 / 26);
});

// ── 5. TOTALS ACROSS A MIXED ROSTER ───────────────────────────────────────
section('a mixed-frequency roster totals correctly and discloses its mix');

test('the measured case from the finding now uses the recorded $840', () => {
  // Two active full-timers, one carrying $840. Before the fix this returned
  // benefits $1,040 (2 x $520) and the $840 was ignored entirely.
  const c = harness([
    FT({ pay_freq: 'Monthly', ben: { cost: 840 } }),
    FT({ pay_freq: 'Monthly' })
  ]);
  const t = c.sbPayrollTotals();
  near(t.benefits, 840 + 520);
  assert.strictEqual(t.employees_on_assumed_benefit_cost, 1);
});

test('the frequency mix and both assumption counts are reported', () => {
  const c = harness([
    FT({ pay_freq: 'Monthly', ben: { cost: 900 } }),
    FT({ pay_freq: 'Weekly' }),
    FT() // no frequency recorded at all
  ]);
  const t = c.sbPayrollTotals();
  // Compared through JSON rather than deepStrictEqual: the object is created
  // inside the vm realm, so its prototype is not this realm's Object.prototype
  // and a strict deep-equal fails on identical data. A test that fails for a
  // reason unrelated to the code under test is worse than no test.
  assert.deepStrictEqual(JSON.parse(JSON.stringify(t.frequencies)), { Monthly: 1, Weekly: 1, Biweekly: 1 });
  assert.strictEqual(t.employees_on_default_frequency, 1);
  assert.strictEqual(t.employees_on_assumed_benefit_cost, 2);
});

test('inactive employees are excluded from every figure', () => {
  const c = harness([FT(), FT({ status: 'Terminated' }), FT({ status: 'On Leave' })]);
  assert.strictEqual(c.sbPayrollTotals().employees, 1);
});

test('annual_gross is a real sum, not a period multiplier', () => {
  // The defect this replaces: ytd was gross x 13 while 80h implied 26 periods.
  // On a mixed roster no single multiplier can be right, so there is none.
  const c = harness([FT({ pay_freq: 'Weekly' }), FT({ pay_freq: 'Monthly' })]);
  const t = c.sbPayrollTotals();
  assert.strictEqual(t.annual_gross, 2 * 30 * 40 * 52);
  // And it is emphatically NOT the old formula.
  assert.notStrictEqual(t.annual_gross, t.gross * 13);
});

test('an empty roster reports zeros rather than NaN', () => {
  const c = harness([]);
  const t = c.sbPayrollTotals();
  assert.strictEqual(t.employees, 0);
  assert.strictEqual(t.gross, 0);
  assert.strictEqual(t.benefits, 0);
  assert.strictEqual(t.annual_gross, 0);
});

test('a missing rate contributes 0 rather than NaN', () => {
  // checkPayrollAnomalies() flags this employee as critical, but the totals
  // still have to render while the flag is on screen.
  const c = harness([FT({ rate: undefined })]);
  const t = c.sbPayrollTotals();
  assert.strictEqual(t.gross, 0);
  assert.ok(isFinite(t.total), 'total must stay finite');
});

// ── 6. THE HIRING PROJECTION USES THE SAME MATHS ──────────────────────────
// This is the drift guard. The projection is a comparison against the current
// fully-loaded cost; if it kept its own 80/32 and flat $520 while payroll
// prorated, the "cost of the hire" would be inflated by the difference.
section('hiring cost impact cannot drift from payroll');

const PAYROLL_STUB = { total_labor_cost: 10000 };
const PL_STUB = { net_income: 5000, revenue: 50000, net_margin_pct: 10 };

test('an omitted frequency gives the biweekly answer, not an error', () => {
  const c = harness([]);
  const r = c.computeHiringCostImpact(30, 'Full Time', PAYROLL_STUB, PL_STUB);
  assert.strictEqual(r.new_role_hours_per_period, 80);
  assert.strictEqual(r.new_role_pay_frequency, 'Biweekly');
  assert.strictEqual(r.new_role_pay_frequency_assumed, true);
});

test('the new role benefit prorates like everyone else', () => {
  const c = harness([]);
  near(c.computeHiringCostImpact(30, 'Full Time', PAYROLL_STUB, PL_STUB, 'Biweekly').new_role_benefit,
    520 * 12 / 26);
  near(c.computeHiringCostImpact(30, 'Full Time', PAYROLL_STUB, PL_STUB, 'Monthly').new_role_benefit,
    520);
});

test('frequency changes the per-period cost but never the annual cost', () => {
  const c = harness([]);
  const w = c.computeHiringCostImpact(30, 'Full Time', PAYROLL_STUB, PL_STUB, 'Weekly');
  const m = c.computeHiringCostImpact(30, 'Full Time', PAYROLL_STUB, PL_STUB, 'Monthly');
  assert.ok(w.new_role_gross < m.new_role_gross, 'a weekly cheque is smaller than a monthly one');
  assert.strictEqual(w.new_role_annual_gross, m.new_role_annual_gross);
});

test('the projection reconciles against the payroll helpers exactly', () => {
  const c = harness([]);
  const r = c.computeHiringCostImpact(42, 'Part Time', PAYROLL_STUB, PL_STUB, 'Semi-monthly');
  const synthetic = { type: 'Part Time', pay_freq: 'Semi-monthly', rate: 42 };
  assert.strictEqual(r.new_role_gross, c.sbGrossPerPeriod(synthetic));
  assert.strictEqual(r.new_role_benefit, c.sbBenefitPerPeriod(synthetic));
  assert.strictEqual(r.new_role_hours_per_period, c.sbHoursPerPeriod(synthetic));
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
