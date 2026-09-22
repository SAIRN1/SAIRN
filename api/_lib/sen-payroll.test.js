// api/_lib/sen-payroll.test.js
// REQUIREMENT: gross pay is computed from CLOCKED hours at the rate in force
//   on the service date, overtime uses the WEIGHTED-AVERAGE regular rate, and
//   a visit that cannot be priced is excluded and named rather than paid at
//   zero
//
// Run: node api/_lib/sen-payroll.test.js
//
// THE ARM THAT MATTERS MOST IS THE WEIGHTED AVERAGE. FLSA overtime is 1.5x the
// REGULAR RATE, and when an employee works at more than one rate in a workweek
// that rate is the weighted average of straight-time earnings over hours
// worked (29 C.F.R. §778.115) -- not the rate of whichever visit happened to
// cross hour 40. An engine that used the crossing visit's rate would agree
// with this one on every single-rate week and be wrong on every mixed one, so
// a suite that only tested one rate would prove nothing about the thing most
// likely to be wrong.
'use strict';
const assert = require('assert');
const { computePayroll, cents, weekStartKey, DAY_NAMES, resolveRateFrom } = require('./sen-payroll');

let pass = 0, fail = 0;
function t(name, fn) {
  try { fn(); pass += 1; console.log('  ok   ' + name); }
  catch (e) { fail += 1; console.log('  FAIL ' + name + '\n         ' + e.message); }
}

// A visit is `hours` long starting at 09:00 UTC on `date`.
const visit = (date, hours, o) => Object.assign({
  id: 'V-' + date + '-' + hours,
  assigned_employee_id: 'E1',
  scheduled_date: date,
  clock_in_at: date + 'T09:00:00.000Z',
  clock_out_at: date + 'T' + String(9 + hours).padStart(2, '0') + ':00:00.000Z',
}, o);

const flatRate = (perHour) => () => ({ status: 'applied', rate_per_hour: perHour });

const run = (o) => computePayroll(Object.assign({
  period_start: '2026-03-01', period_end: '2026-03-31',
  week_start_day: 'sunday', resolveRate: flatRate(20),
}, o));

console.log('SAIRNsenior payroll -- clocked hours, weighted-average overtime, '
  + 'and nothing paid at a zero it cannot justify\n');

// ── THE BASICS ──────────────────────────────────────────────────────────
t('gross is clocked hours at the rate in force', () => {
  const r = run({ visits: [visit('2026-03-02', 8)] });
  const c = r.caregivers[0];
  assert.strictEqual(c.minutes, 480);
  assert.strictEqual(c.gross_cents, 16000, '8h at $20 = $160.00');
  assert.strictEqual(c.overtime_minutes, 0);
  assert.strictEqual(c.is_floor, false);
});
t('pay follows the CLOCK, never the schedule', () => {
  // Scheduled 09:00-17:00; actually clocked 09:00-11:00.
  const r = run({
    visits: [visit('2026-03-02', 2, {
      scheduled_start: '09:00', scheduled_end: '17:00',
    })],
  });
  assert.strictEqual(r.caregivers[0].minutes, 120,
    'paying the schedule would pay for six hours nobody worked, invisibly, '
    + 'because the schedule is always present and always well-formed');
});

// ── OVERTIME, AND THE WEIGHTED AVERAGE ──────────────────────────────────
t('over 40 hours in a workweek earns a half-rate premium on the excess', () => {
  // 5 x 9h = 45h in one week at $20.
  const days = ['2026-03-02', '2026-03-03', '2026-03-04', '2026-03-05', '2026-03-06'];
  const r = run({ visits: days.map((d) => visit(d, 9)) });
  const c = r.caregivers[0];
  assert.strictEqual(c.minutes, 45 * 60);
  assert.strictEqual(c.overtime_minutes, 5 * 60);
  // 45h straight at $20 = $900; premium = 5h x $10 = $50.
  assert.strictEqual(c.gross_cents, 90000 + 5000);
});
t('THE ONE THAT SEPARATES A CORRECT ENGINE FROM A PLAUSIBLE ONE: overtime uses '
  + 'the WEIGHTED AVERAGE of the week, not the rate of the crossing visit', () => {
  // 30h at $18 then 15h at $30 = 45h. Straight = 540 + 450 = $990.
  // Weighted average = 990/45 = $22.00. Premium = 5h x $11 = $55.
  // An engine using the CROSSING visit's rate ($30) would give 5h x $15 = $75.
  const rate = (emp, date) => ({
    status: 'applied', rate_per_hour: date >= '2026-03-05' ? 30 : 18,
  });
  const r = run({
    resolveRate: rate,
    visits: [
      visit('2026-03-02', 10), visit('2026-03-03', 10), visit('2026-03-04', 10),
      visit('2026-03-05', 10), visit('2026-03-06', 5),
    ],
  });
  const w = r.caregivers[0].weeks[0];
  assert.strictEqual(w.minutes, 45 * 60);
  assert.strictEqual(w.straight_time_cents, 99000, 'straight time is $990.00');
  assert.strictEqual(w.regular_rate_cents_per_hour, 2200,
    'the regular rate is the weighted average, $22.00/hr');
  assert.strictEqual(w.overtime_premium_cents, 5500,
    'premium is 5h at half of $22 = $55.00, NOT 5h at half of $30 = $75.00');
});
t('...and exactly 40 hours earns no premium at all', () => {
  const r = run({
    visits: [visit('2026-03-02', 10), visit('2026-03-03', 10),
      visit('2026-03-04', 10), visit('2026-03-05', 10)],
  });
  assert.strictEqual(r.caregivers[0].overtime_minutes, 0);
  assert.strictEqual(r.caregivers[0].gross_cents, 80000);
});
t('hours in DIFFERENT workweeks do not combine into overtime', () => {
  // 30h in one week and 30h in the next is 60h and NO overtime.
  const r = run({
    visits: [visit('2026-03-03', 10), visit('2026-03-04', 10), visit('2026-03-05', 10),
      visit('2026-03-10', 10), visit('2026-03-11', 10), visit('2026-03-12', 10)],
  });
  const c = r.caregivers[0];
  assert.strictEqual(c.weeks.length, 2);
  assert.strictEqual(c.overtime_minutes, 0,
    'overtime is per 168-hour workweek, never per pay period');
});
t('the WORKWEEK START DAY changes the answer, which is why it is required', () => {
  // Sat 7 Mar + Sun 8 Mar, 30h each. Sunday-start splits them; Monday-start
  // puts both in the same week and creates 20h of overtime.
  const vs = [visit('2026-03-07', 15), visit('2026-03-07', 15, { id: 'b' }),
    visit('2026-03-08', 15, { id: 'c' }), visit('2026-03-08', 15, { id: 'd' })];
  const sun = run({ visits: vs, week_start_day: 'sunday' });
  const mon = run({ visits: vs, week_start_day: 'monday' });
  assert.notStrictEqual(sun.caregivers[0].overtime_minutes,
    mon.caregivers[0].overtime_minutes,
    'if the start day made no difference, requiring it would be ceremony');
});

// ── RULE 1 AND 3: AN UNPAYABLE VISIT IS NAMED, NEVER PAID AT ZERO ───────
t('a visit with no clock-out is EXCLUDED and named, not paid as zero hours', () => {
  const r = run({
    visits: [visit('2026-03-02', 8), visit('2026-03-03', 8, { clock_out_at: null })],
  });
  assert.strictEqual(r.excluded.no_clock_out, 1);
  assert.strictEqual(r.caregivers[0].minutes, 480, 'only the complete visit is paid');
  assert.strictEqual(r.caregivers[0].is_floor, true);
});
t('a NON-POSITIVE duration is its own reason, not a zero-hour visit', () => {
  const r = run({
    visits: [visit('2026-03-02', 8, {
      clock_in_at: '2026-03-02T12:00:00.000Z',
      clock_out_at: '2026-03-02T11:00:00.000Z',
    })],
  });
  assert.strictEqual(r.excluded.non_positive_duration, 1);
  assert.strictEqual(r.caregivers.length, 1);
  assert.strictEqual(r.caregivers[0].gross_cents, 0);
  assert.strictEqual(r.caregivers[0].is_floor, true);
});
t('NO RATE ON FILE is excluded and counted separately from other exclusions', () => {
  const r = run({
    resolveRate: () => ({ status: 'none', reason: 'No pay rate is on file' }),
    visits: [visit('2026-03-02', 8)],
  });
  assert.strictEqual(r.excluded.no_rate, 1);
  assert.strictEqual(r.caregivers[0].no_rate_visits, 1);
  assert.strictEqual(r.caregivers[0].gross_cents, 0);
  assert.strictEqual(r.caregivers[0].is_floor, true,
    'a zero-dollar line that reads as "worked for nothing" is '
    + 'indistinguishable from a correct zero unless it is marked');
});
t('TWO rates in force is refused per visit rather than picking one', () => {
  const r = run({
    resolveRate: () => ({ status: 'ambiguous', candidates: [{}, {}] }),
    visits: [visit('2026-03-02', 8)],
  });
  assert.strictEqual(r.excluded.ambiguous_rate, 1);
  assert.strictEqual(r.caregivers[0].gross_cents, 0,
    'picking either rate pays a wage nobody chose');
});
t('THE PAIRED POSITIVE: a clean period is NOT a floor', () => {
  const r = run({ visits: [visit('2026-03-02', 8), visit('2026-03-03', 8)] });
  assert.strictEqual(r.is_floor, false);
  assert.strictEqual(r.caregivers[0].is_floor, false,
    'if every run read as a floor the flag would be decoration');
});

// ── THE PERIOD BOUNDARY ─────────────────────────────────────────────────
t('a visit outside the pay period is excluded, not carried in', () => {
  const r = run({ visits: [visit('2026-02-27', 8), visit('2026-03-02', 8)] });
  assert.strictEqual(r.excluded.outside_period, 1);
  assert.strictEqual(r.caregivers[0].minutes, 480);
});
t('a visit with no caregiver belongs to nobody and is counted as such', () => {
  const r = run({ visits: [visit('2026-03-02', 8, { assigned_employee_id: '' })] });
  assert.strictEqual(r.excluded.no_caregiver, 1);
  assert.strictEqual(r.caregivers.length, 0, 'no caregiver may be invented');
  assert.strictEqual(r.is_floor, true);
});

// ── REFUSALS, NOT DEFAULTS ──────────────────────────────────────────────
t('no pay period is a REFUSAL, not "everything on file"', () => {
  const r = computePayroll({ visits: [], week_start_day: 'sunday', resolveRate: flatRate(20) });
  assert.strictEqual(r.refused.code, 'NO_PERIOD');
});
t('no workweek start day is a REFUSAL, not a silent Sunday', () => {
  const r = computePayroll({
    visits: [], period_start: '2026-03-01', period_end: '2026-03-31',
    resolveRate: flatRate(20),
  });
  assert.strictEqual(r.refused.code, 'NO_WEEK_START');
});
t('no rate resolver is a REFUSAL, not a run where everybody earns nothing', () => {
  const r = computePayroll({
    visits: [], period_start: '2026-03-01', period_end: '2026-03-31',
    week_start_day: 'sunday',
  });
  assert.strictEqual(r.refused.code, 'NO_RATE_RESOLVER');
});

// ── WHAT IT DOES NOT COMPUTE IS IN THE OUTPUT ───────────────────────────
t('the output NAMES what it does not compute, so nobody can file it', () => {
  const r = run({ visits: [visit('2026-03-02', 8)] });
  const joined = r.not_computed.join(' ');
  assert.ok(/GROSS only/i.test(joined), 'net pay must be disclaimed');
  assert.ok(/785\.38/.test(joined), 'travel time must be named');
  assert.ok(/[Ll]ive-in/.test(joined), 'live-in must be named');
  assert.ok(r.not_computed.length >= 4);
});

// ── HELPERS ─────────────────────────────────────────────────────────────
t('cents() refuses what is not money, and null is not zero', () => {
  assert.strictEqual(cents(undefined), null);
  assert.strictEqual(cents('abc'), null);
  assert.strictEqual(cents(-1), null);
  assert.strictEqual(cents(0), 0);
  assert.strictEqual(cents('18.50'), 1850);
});
t('weekStartKey lands on the chosen day for every day of the week', () => {
  DAY_NAMES.forEach((name, idx) => {
    const key = weekStartKey(Date.parse('2026-03-04T12:00:00Z'), idx);
    assert.strictEqual(new Date(key + 'T00:00:00Z').getUTCDay(), idx,
      'week starting ' + name + ' must begin on a ' + name);
  });
});
t('a malformed visit does not take the whole pay run out', () => {
  const r = run({ visits: [null, undefined, 7, visit('2026-03-02', 8)] });
  assert.strictEqual(r.caregivers[0].gross_cents, 16000);
});

// -- THE RATE RESOLVER, WHICH IS WHERE A WAGE COMES FROM -----------------
t('resolveRateFrom applies the rate in force on the service date', () => {
  const resolve = resolveRateFrom([
    { employee_id: 'E1', rate_per_hour: 18, effective_on: '2026-01-01', term_on: '2026-02-28' },
    { employee_id: 'E1', rate_per_hour: 20, effective_on: '2026-03-01' },
  ]);
  assert.strictEqual(resolve('E1', '2026-02-10').rate_per_hour, 18);
  assert.strictEqual(resolve('E1', '2026-03-10').rate_per_hour, 20);
});
t('THE SUBTLE ONE: a term_on that is present but UNREADABLE makes the rate NOT '
  + 'in force, rather than being skipped as though the field were blank', () => {
  const resolve = resolveRateFrom([
    { employee_id: 'E1', rate_per_hour: 18, effective_on: '2026-01-01', term_on: 'whenever' },
  ]);
  assert.strictEqual(resolve('E1', '2026-03-10').status, 'none',
    'skipping it turns a superseded wage into an open-ended one and keeps '
    + 'paying it forever');
});
t('...and an IMPOSSIBLE effective date is not silently repaired', () => {
  const resolve = resolveRateFrom([
    { employee_id: 'E1', rate_per_hour: 18, effective_on: '2026-02-31' },
  ]);
  assert.strictEqual(resolve('E1', '2026-03-10').status, 'none');
});
t('two rates in force on the same day is AMBIGUOUS, never the first one', () => {
  const resolve = resolveRateFrom([
    { employee_id: 'E1', rate_per_hour: 18, effective_on: '2026-01-01' },
    { employee_id: 'E1', rate_per_hour: 25, effective_on: '2026-02-01' },
  ]);
  assert.strictEqual(resolve('E1', '2026-03-10').status, 'ambiguous');
});
t('one caregiver never borrows another caregiver rate', () => {
  const resolve = resolveRateFrom([
    { employee_id: 'E2', rate_per_hour: 30, effective_on: '2026-01-01' },
  ]);
  assert.strictEqual(resolve('E1', '2026-03-10').status, 'none');
});
t('END TO END: the resolver drives computePayroll with no injected stub', () => {
  const r = computePayroll({
    period_start: '2026-03-01', period_end: '2026-03-31', week_start_day: 'sunday',
    resolveRate: resolveRateFrom([
      { employee_id: 'E1', rate_per_hour: 20, effective_on: '2026-01-01' },
    ]),
    visits: [visit('2026-03-02', 8)],
  });
  assert.strictEqual(r.caregivers[0].gross_cents, 16000);
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
