// api/b48-sen-straight-time-floor-coverage.test.js
//
// Run:  node api/b48-sen-straight-time-floor-coverage.test.js
//
// THE STRAIGHT-TIME FLOOR BEYOND THE SHAPE ALREADY VERIFIED (hank b48).
//
// The confirmed-clean record for 144dfb71587e (2026-10-16) states its own
// limit: "one agency, one caregiver, one closed period and two visits with one
// approved correction each ... says nothing about premium (overtime) cases,
// multi-rate weeks or reopened periods." This file drives the shapes it named.
//
// CONCEPT: the straight-time floor stays a FLOOR in every shape -- a
// correction to a paid visit is priced at THAT visit's own rate, is never
// negative and never netted, names the closed period it belongs to, lands in
// exactly ONE later run, and says when an overtime premium may also be owed
// rather than computing one it cannot see.
//
//   O  overtime / multi-rate weeks     the real engine, api/_lib/sen-payroll.js
//   P  multiple closed periods         the real engine
//   G  multiple agencies, and reopen   the real pay-run handler in api/sd-data.js
//
// Exit: 0 all arms passed - 1 an arm FAILED

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || ['sen', 'floor', 'b48', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const senPayroll = require('./_lib/sen-payroll');

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

// ── FIXTURE ─────────────────────────────────────────────────────────────────
// Workweek starts Sunday. Two CLOSED periods, then the OPEN run.
const P1 = { period_start: '2026-09-13', period_end: '2026-09-26', paid_at: '2026-09-27T00:00:00Z' };
const P2 = { period_start: '2026-09-27', period_end: '2026-10-10', paid_at: '2026-10-11T00:00:00Z' };
const RUN = { start: '2026-10-11', end: '2026-10-24' };
const APPROVED_IN_RUN = '2026-10-14T10:00:00Z';

// E1's rate CHANGES MID-WEEK: $18 through Tue 2026-09-29, $22 from Wed 09-30.
// That is what makes a multi-rate workweek on this platform (rates are per
// caregiver per date, resolved by the shipped resolveRateFrom()).
// E2 is a flat $20.
const RATES = [
  { id: 'R1', employee_id: 'E1', rate_per_hour: 18, effective_on: '2026-01-01', term_on: '2026-09-29' },
  { id: 'R2', employee_id: 'E1', rate_per_hour: 22, effective_on: '2026-09-30' },
  { id: 'R3', employee_id: 'E2', rate_per_hour: 20, effective_on: '2026-01-01' }
];

function corr(field, original, proposed, approvedAt, id) {
  return { id: id || 'C-' + field + '-' + proposed, field: field, original_at: original, proposed_at: proposed,
           reason_code: 'FORGOT_TO_CLOCK_OUT', filed_by: 'E1', filed_at_server: '2026-10-01T10:00:00Z',
           status: 'approved', approved_by: 'S1', approved_at_server: approvedAt };
}
function visit(id, emp, day, inH, outH, corrections) {
  const v = { id: id, visit_id: id, assigned_employee_id: emp, scheduled_date: day,
              clock_in_at: day + 'T' + inH + ':00:00Z', clock_out_at: day + 'T' + outH + ':00:00Z' };
  if (corrections) v.clock_corrections = corrections;
  return v;
}

// THE OVERTIME WEEK, as paid: Sun-Tue 3 x 8h at $18 = 24h, Wed-Thu 2 x 9h at
// $22 = 18h. 42h in the week of 2026-09-27, inside closed P2.
//  - Thu 10-01 gets +60 min (out 17:00 -> 18:00), approved in the open run.
//  - Mon 09-28 gets -60 min (out 17:00 -> 16:00), approved in the open run.
const OT_WEEK = [
  visit('OT-SUN', 'E1', '2026-09-27', '09', '17'),
  visit('OT-MON', 'E1', '2026-09-28', '09', '17',
    [corr('clock_out_at', '2026-09-28T17:00:00Z', '2026-09-28T16:00:00Z', APPROVED_IN_RUN)]),
  visit('OT-TUE', 'E1', '2026-09-29', '09', '17'),
  visit('OT-WED', 'E1', '2026-09-30', '08', '17'),
  visit('OT-THU', 'E1', '2026-10-01', '08', '17',
    [corr('clock_out_at', '2026-10-01T17:00:00Z', '2026-10-01T18:00:00Z', APPROVED_IN_RUN)])
];

// The engine under test. Section M swaps in a MUTATED copy compiled from the
// real source text, re-runs the check that guards that behaviour, and requires red.
let ENG = senPayroll;
function run(visits, closed, period) {
  return ENG.computePayroll({
    visits: visits, period_start: (period || RUN).start, period_end: (period || RUN).end,
    week_start_day: 'sunday', closed_periods: closed,
    resolveRate: ENG.resolveRateFrom(RATES)
  });
}
const byVisit = (list, id) => (list || []).filter((x) => x.visit_id === id);

(async function () {
  console.log('SAIRNsenior straight-time floor -- overtime, multi-rate, multiple periods, multiple agencies');

  section('O. OVERTIME AND MULTI-RATE WEEKS (engine)');
  const o = run(OT_WEEK, [P1, P2]);
  await test('O0. the run is not refused', function () { assert.ok(!o.refused, JSON.stringify(o.refused)); });
  await test('O1. +60 min on the $22 visit is an ADJUSTMENT priced at THAT visit\'s rate: 2200 cents, not a weighted or 1.5x figure', function () {
    const a = byVisit(o.adjustments, 'OT-THU');
    assert.strictEqual(a.length, 1, 'adjustments for OT-THU: ' + a.length);
    assert.deepStrictEqual([a[0].minutes_delta, a[0].rate_cents_per_hour, a[0].cents_delta], [60, 2200, 2200]);
  });
  await test('O2. ...and premium_may_be_owed is TRUE: the as-paid week it belongs to was 42h (2520 min) in week 2026-09-27', function () {
    const a = byVisit(o.adjustments, 'OT-THU')[0];
    assert.deepStrictEqual([a.premium_may_be_owed, a.as_paid_week_minutes_seen, a.as_paid_week_start],
      [true, 2520, '2026-09-27']);
  });
  await test('O3. -60 min on the $18 visit is an OVERPAYMENT at $18 (1800 cents), flagged for a human, NOT an adjustment', function () {
    const ov = byVisit(o.overpayments, 'OT-MON');
    assert.strictEqual(byVisit(o.adjustments, 'OT-MON').length, 0, 'a downward correction became an adjustment');
    assert.strictEqual(ov.length, 1);
    assert.deepStrictEqual([ov[0].minutes_delta, ov[0].cents_delta, ov[0].requires_human_act], [-60, -1800, true]);
  });
  await test('O4. INVARIANT: total payable >= gross for every caregiver -- the overpayment is not netted into later pay', function () {
    (o.caregivers || []).forEach(function (c) {
      assert.ok(c.total_payable_cents >= c.gross_cents, c.employee_id + ': ' + c.total_payable_cents + ' < ' + c.gross_cents);
    });
  });
  await test('O5. a week below 40h that a correction pushes OVER 40 also says premium_may_be_owed (39h + 2h)', function () {
    // Week of 2026-10-04 (inside P2), E2 at $20: 39h as paid, +120 min approved in the run.
    const vs = [
      visit('U-SUN', 'E2', '2026-10-04', '08', '18'), visit('U-MON', 'E2', '2026-10-05', '08', '18'),
      visit('U-TUE', 'E2', '2026-10-06', '08', '18'),
      visit('U-WED', 'E2', '2026-10-07', '08', '17',
        [corr('clock_out_at', '2026-10-07T17:00:00Z', '2026-10-07T19:00:00Z', APPROVED_IN_RUN)])
    ];
    const r = run(vs, [P1, P2]);
    const a = byVisit(r.adjustments, 'U-WED')[0];
    assert.ok(a, 'no adjustment');
    assert.deepStrictEqual([a.as_paid_week_minutes_seen, a.minutes_delta, a.cents_delta, a.premium_may_be_owed],
      [2340, 120, 4000, true]);
  });
  await test('O6. CONTROL: a 30h week with +60 is NOT flagged true -- the flag stays null, never false', function () {
    const vs = [visit('L-MON', 'E2', '2026-10-05', '08', '18'), visit('L-TUE', 'E2', '2026-10-06', '08', '18'),
      visit('L-WED', 'E2', '2026-10-07', '08', '18',
        [corr('clock_out_at', '2026-10-07T18:00:00Z', '2026-10-07T19:00:00Z', APPROVED_IN_RUN)])];
    const a = byVisit(run(vs, [P1, P2]).adjustments, 'L-WED')[0];
    assert.deepStrictEqual([a.as_paid_week_minutes_seen, a.premium_may_be_owed], [1800, null]);
  });
  await test('O7. the OPEN run\'s own multi-rate overtime week uses the WEIGHTED regular rate (29 CFR 778.115), and an adjustment never enters it', function () {
    // Same 42h shape moved into the open run (week of 2026-10-11, E1 at $22
    // flat by then), plus the closed-period adjustment from O1.
    const vs = OT_WEEK.concat([
      visit('R-SUN', 'E1', '2026-10-11', '09', '17'), visit('R-MON', 'E1', '2026-10-12', '09', '17'),
      visit('R-TUE', 'E1', '2026-10-13', '09', '17'), visit('R-WED', 'E1', '2026-10-14', '08', '17'),
      visit('R-THU', 'E1', '2026-10-15', '08', '17')]);
    const r = run(vs, [P1, P2]);
    const c = r.caregivers.filter((x) => x.employee_id === 'E1')[0];
    const w = c.weeks.filter((x) => x.week_start === '2026-10-11')[0];
    // 42h at $22 flat: straight 92400, OT 120 min, premium 0.5 x 2200 x 2 = 2200.
    assert.deepStrictEqual([w.minutes, w.overtime_minutes, w.straight_time_cents, w.overtime_premium_cents, w.gross_cents],
      [2520, 120, 92400, 2200, 94600]);
    assert.strictEqual(c.weeks.length, 1, 'a closed-period week leaked into the open run: ' + c.weeks.map((x) => x.week_start));
    assert.strictEqual(c.adjustment_cents, 2200, 'the adjustment total');
    assert.strictEqual(c.total_payable_cents, c.gross_cents + 2200);
  });
  await test('O8. a MULTI-RATE overtime week in the open run: 20h at $18 + 22h at $22 -> regular rate 2009.52c, premium 2010c (half the WEIGHTED rate x 2h)', function () {
    const rates = [
      { id: 'X1', employee_id: 'E3', rate_per_hour: 18, effective_on: '2026-01-01', term_on: '2026-10-13' },
      { id: 'X2', employee_id: 'E3', rate_per_hour: 22, effective_on: '2026-10-14' }];
    const vs = [visit('M-SUN', 'E3', '2026-10-11', '08', '18'), visit('M-MON', 'E3', '2026-10-12', '08', '18'),
      visit('M-WED', 'E3', '2026-10-14', '07', '18'), visit('M-THU', 'E3', '2026-10-15', '07', '18')];
    const r = senPayroll.computePayroll({ visits: vs, period_start: RUN.start, period_end: RUN.end,
      week_start_day: 'sunday', closed_periods: [], resolveRate: senPayroll.resolveRateFrom(rates) });
    const w = r.caregivers[0].weeks[0];
    // straight = 20h x 1800 + 22h x 2200 = 36000 + 48400 = 84400; rate = 84400/42 = 2009.52; premium = 0.5 x 2009.52 x 2
    assert.deepStrictEqual([w.minutes, w.straight_time_cents, w.regular_rate_cents_per_hour, w.overtime_premium_cents, w.gross_cents],
      [2520, 84400, 2010, 2010, 86410]);
  });

  section('P. MULTIPLE CLOSED PERIODS (engine)');
  const pVisits = [
    // In P1, approved in the open run -> adjustment naming P1.
    visit('P1-A', 'E2', '2026-09-15', '09', '17',
      [corr('clock_out_at', '2026-09-15T17:00:00Z', '2026-09-15T17:30:00Z', APPROVED_IN_RUN)]),
    // In P1, approved DURING P2's window (2026-10-05) -> belongs to the P2 run only.
    visit('P1-B', 'E2', '2026-09-16', '09', '17',
      [corr('clock_out_at', '2026-09-16T17:00:00Z', '2026-09-16T18:00:00Z', '2026-10-05T10:00:00Z')]),
    // In P1, approved BEFORE P1 was paid -> part of what was paid; never an adjustment.
    visit('P1-C', 'E2', '2026-09-17', '09', '17',
      [corr('clock_out_at', '2026-09-17T17:00:00Z', '2026-09-17T19:00:00Z', '2026-09-20T10:00:00Z')]),
    // In P2, approved in the open run -> adjustment naming P2.
    visit('P2-A', 'E2', '2026-10-06', '09', '17',
      [corr('clock_out_at', '2026-10-06T17:00:00Z', '2026-10-06T17:45:00Z', APPROVED_IN_RUN)])
  ];
  const pRun = run(pVisits, [P1, P2]);
  await test('P1. two corrections in two DIFFERENT closed periods each post one adjustment naming ITS period and paid_at', function () {
    const a = byVisit(pRun.adjustments, 'P1-A'), b = byVisit(pRun.adjustments, 'P2-A');
    assert.deepStrictEqual([a.length, b.length], [1, 1]);
    assert.deepStrictEqual([a[0].closed_period_start, a[0].paid_at, a[0].minutes_delta, a[0].cents_delta],
      ['2026-09-13', P1.paid_at, 30, 1000]);
    assert.deepStrictEqual([b[0].closed_period_start, b[0].paid_at, b[0].minutes_delta, b[0].cents_delta],
      ['2026-09-27', P2.paid_at, 45, 1500]);
  });
  await test('P2. a correction approved during P2\'s window is NOT in the later run...', function () {
    assert.strictEqual(byVisit(pRun.adjustments, 'P1-B').length, 0);
  });
  await test('P3. ...it IS in the P2 run as it was computed then (only P1 closed) -- so it lands in exactly ONE run', function () {
    const then = run(pVisits, [P1], { start: P2.period_start, end: P2.period_end });
    const hit = byVisit(then.adjustments, 'P1-B');
    assert.deepStrictEqual([hit.length, hit[0] && hit[0].cents_delta], [1, 2000]);
  });
  await test('P4. a correction approved BEFORE its period was paid is part of what was paid: no adjustment in either later run', function () {
    const then = run(pVisits, [P1], { start: P2.period_start, end: P2.period_end });
    assert.deepStrictEqual([byVisit(pRun.adjustments, 'P1-C').length, byVisit(then.adjustments, 'P1-C').length,
      byVisit(pRun.overpayments, 'P1-C').length], [0, 0, 0]);
  });
  await test('P5. INVARIANT across all of P: payable >= gross and the adjustment total is the sum of the lines', function () {
    pRun.caregivers.forEach(function (c) {
      const lines = pRun.adjustments.filter((a) => a.employee_id === c.employee_id)
        .reduce((s, a) => s + a.cents_delta, 0);
      assert.deepStrictEqual([c.total_payable_cents >= c.gross_cents, c.adjustment_cents], [true, lines]);
    });
  });

  section('G. MULTIPLE AGENCIES, AND A REOPENED PERIOD (the real pay-run handler)');
  const fs = require('fs'), path = require('path'), Module = require('module');
  const { signSessionToken } = require('./_lib/auth');
  const SD_FILE = path.join(__dirname, 'sd-data.js');
  const SD_SRC = fs.readFileSync(SD_FILE, 'utf8');
  let SD_TEXT = SD_SRC;
  // Two agencies with IDENTICAL visit ids and employee ids. Only A has closed P1.
  const AGENCY = {
    'hash-agency-A': { closings: [{ closing_id: 'CL-A1', data: Object.assign({ kind: 'close' }, P1) }] },
    'hash-agency-B': { closings: [] },
    'hash-agency-R': { closings: [{ closing_id: 'CL-R1', data: Object.assign({ kind: 'close' }, P1) },
                                  { closing_id: 'CL-R2', data: { kind: 'reopen', reverses: 'CL-R1', reason: 'b48 fixture' } }] }
  };
  const sameVisit = { visit_id: 'P1-A', assigned_employee_id: 'E2', data: byVisit(pVisits, 'P1-A')[0] };
  // The licence mock reads the CURRENT hash, so one compiled handler can serve
  // two agencies in turn (G5, the warm-instance case cc b50 named as D9).
  let CURRENT_HASH = null;
  const lic = require.resolve('./_lib/license');
  function compileHandler() {
    delete require.cache[lic];
    require.cache[lic] = { id: lic, filename: lic, loaded: true, exports: { validateLicenseKey: async function () {
      return { valid: true, active: true, license_hash: CURRENT_HASH, trial_ends_at: null, stripe_subscription_id: null, app_id: 'sairnsenior' };
    } } };
    const m = new Module(SD_FILE, module);
    m.filename = SD_FILE; m.paths = Module._nodeModulePaths(__dirname);
    m._compile(SD_TEXT, SD_FILE);
    return m;
  }
  async function payRun(hash, warm) {
    const urls = [];
    CURRENT_HASH = hash;
    const m = warm || compileHandler();
    const prev = global.fetch;
    global.fetch = async function (url) {
      const u = String(url); urls.push(u);
      const scoped = /license_hash=eq\./.test(u);
      const mine = u.indexOf('license_hash=eq.' + encodeURIComponent(hash)) !== -1;
      const j = (rows) => ({ ok: true, status: 200, json: async () => rows, text: async () => JSON.stringify(rows) });
      if (/_employee_auth\?/.test(u)) return j([{ license_hash: hash, employee_id: 'mgr', role: 'owner', active: true }]);
      // AN UNSCOPED READ GETS EVERY AGENCY'S ROWS, as the real table would
      // (cc b50: the old mock answered [] here, so a dropped scope showed up as
      // A losing its data rather than as B SEEING A's). A read scoped to
      // another licence gets nothing.
      if (!scoped && /sen_period_closings\?/.test(u)) {
        return j([].concat.apply([], Object.keys(AGENCY).map((h) => AGENCY[h].closings)));
      }
      if (!mine) return j([]);
      if (/sen_visits\?/.test(u)) return j([sameVisit]);
      if (/sen_pay_rates\?/.test(u)) return j(RATES.map((r) => ({ rate_id: r.id, data: r })));
      if (/sen_period_closings\?/.test(u)) return j(AGENCY[hash].closings);
      if (/sen_settings\?/.test(u)) return j([]);
      return j([]);
    };
    const res = { statusCode: null, body: null, setHeader: function () { return res; },
                  status: function (c) { res.statusCode = c; return res; }, json: function (b) { res.body = b; return res; } };
    try {
      await m.exports({ method: 'POST', headers: { authorization: 'Bearer KEY',
        'x-sd-auth': signSessionToken({ app: 'sairnsenior', employee_id: 'mgr', role: 'owner', license_hash: hash }) },
        body: { action: 'payroll', resource: 'sen_visits',
                payload: { period_start: RUN.start, period_end: RUN.end, week_start_day: 'sunday' } } }, res);
    } finally { global.fetch = prev; }
    return { res: res, urls: urls };
  }
  const A = await payRun('hash-agency-A'), B = await payRun('hash-agency-B'), R = await payRun('hash-agency-R');
  await test('G1. agency A (P1 closed) gets the adjustment for its visit', function () {
    assert.strictEqual(A.res.statusCode, 200, JSON.stringify(A.res.body).slice(0, 200));
    assert.strictEqual(byVisit(A.res.body.data.adjustments, 'P1-A').length, 1);
  });
  await test('G2. agency B, with the SAME visit id and employee id but nothing closed, gets NO adjustment -- A\'s closing does not reach B', function () {
    assert.strictEqual(B.res.statusCode, 200, JSON.stringify(B.res.body).slice(0, 200));
    assert.strictEqual(byVisit(B.res.body.data.adjustments, 'P1-A').length, 0);
  });
  await test('G3. every visits / rates / closings / settings read each run made is scoped to ITS OWN licence hash', function () {
    [['hash-agency-A', A], ['hash-agency-B', B]].forEach(function (pair) {
      const reads = pair[1].urls.filter((u) => /sen_(visits|pay_rates|period_closings|settings)\?/.test(u));
      assert.ok(reads.length >= 4, pair[0] + ' made ' + reads.length + ' reads');
      reads.forEach(function (u) {
        assert.ok(u.indexOf('license_hash=eq.' + pair[0]) !== -1, pair[0] + ' read without its own scope: ' + u.slice(0, 120));
      });
    });
  });
  await test('G4. a REOPENED period is not frozen: close + reopen of P1 -> no adjustment, the visit is simply outside this run', function () {
    assert.strictEqual(R.res.statusCode, 200, JSON.stringify(R.res.body).slice(0, 200));
    assert.deepStrictEqual([byVisit(R.res.body.data.adjustments, 'P1-A').length, byVisit(R.res.body.data.overpayments, 'P1-A').length], [0, 0]);
  });

  await test('G5. ONE warm handler instance serves A then B: B still gets no adjustment -- nothing from A survives in module state', async function () {
    const warm = compileHandler();
    const wA = await payRun('hash-agency-A', warm), wB = await payRun('hash-agency-B', warm);
    assert.strictEqual(byVisit(wA.res.body.data.adjustments, 'P1-A').length, 1, 'warm A lost its adjustment');
    assert.strictEqual(wB.res.statusCode, 200, JSON.stringify(wB.res.body).slice(0, 200));
    assert.strictEqual(byVisit(wB.res.body.data.adjustments, 'P1-A').length, 0, 'warm B saw the A closing');
  });

  section('M. MUTANTS -- each must turn the arm that guards it red');
  const PAY_FILE = path.join(__dirname, '_lib', 'sen-payroll.js');
  const PAY_SRC = fs.readFileSync(PAY_FILE, 'utf8');
  function compileFrom(file, text) {
    const n = new Module(file, module); n.filename = file; n.paths = Module._nodeModulePaths(path.dirname(file));
    n._compile(text, file); return n.exports;
  }
  function mutant(from, to) {
    const k = PAY_SRC.split(from).length - 1;
    if (k !== 1) throw new Error('mutant anchor found ' + k + ' times: ' + from.slice(0, 60));
    return compileFrom(PAY_FILE, PAY_SRC.replace(from, to));
  }
  async function redUnder(eng, check, name) {
    ENG = eng;
    let red = false;
    try { check(); } catch (e) { red = true; } finally { ENG = senPayroll; }
    if (!red) throw new Error(name + ' survived');
  }
  await test('M1. price the delta at the RUN-START rate instead of the visit\'s own date -> O3 red', function () {
    return redUnder(mutant('const rateA = resolveRate(emp, serviceDate) || {};', 'const rateA = resolveRate(emp, start) || {};'),
      function () { assert.deepStrictEqual(byVisit(run(OT_WEEK, [P1, P2]).overpayments, 'OT-MON')[0].cents_delta, -1800); }, 'run-start rate');
  });
  await test('M2. drop the "pushed over 40h" half of the premium flag -> O5 red', function () {
    return redUnder(mutant('|| seen + a.minutes_delta > PREMIUM_THRESHOLD_MINUTES', ''),
      function () {
        const vs = [visit('U-SUN', 'E2', '2026-10-04', '08', '18'), visit('U-MON', 'E2', '2026-10-05', '08', '18'),
          visit('U-TUE', 'E2', '2026-10-06', '08', '18'),
          visit('U-WED', 'E2', '2026-10-07', '08', '17', [corr('clock_out_at', '2026-10-07T17:00:00Z', '2026-10-07T19:00:00Z', APPROVED_IN_RUN)])];
        assert.strictEqual(byVisit(run(vs, [P1, P2]).adjustments, 'U-WED')[0].premium_may_be_owed, true);
      }, 'no crossing check');
  });
  await test('M3. drop the approval-date window start (any approval before run end) -> P2 red', function () {
    return redUnder(mutant('return d >= start && d <= end;', 'return d <= end;'),
      function () { assert.strictEqual(byVisit(run(pVisits, [P1, P2]).adjustments, 'P1-B').length, 0); }, 'no window start');
  });
  await test('M4. every closed visit maps to the FIRST closed period -> P1 red', function () {
    return redUnder(mutant('const closedFor = (serviceDate) => closedPeriodFor(closedPeriods, serviceDate);',
      'const closedFor = (serviceDate) => (closedPeriodFor(closedPeriods, serviceDate) ? closedPeriods[0] : null);'),
      function () { assert.strictEqual(byVisit(run(pVisits, [P1, P2]).adjustments, 'P2-A')[0].paid_at, P2.paid_at); }, 'first-period');
  });
  // M5 (b48) asserted that an unscoped closings read made AGENCY A lose its
  // adjustment -- true only of the old mock, which answered an unscoped read
  // with []. With the realistic mock (every agency's rows) the same mutant
  // shows up as B SEEING A's closing, which is M6. Replaced, not weakened.
  await test('M6. the same unscoped closings read -> G2 red: B now SEES the A closing (the leak direction, with the realistic mock)', async function () {
    const from = "const lr = await fetch(rest('sen_period_closings?license_hash=eq.' + enc(licHash)";
    SD_TEXT = SD_SRC.replace(from, "const lr = await fetch(rest('sen_period_closings?x=1'");
    let leaked;
    try { const m = await payRun('hash-agency-B'); leaked = byVisit(m.res.body.data.adjustments, 'P1-A').length; }
    finally { SD_TEXT = SD_SRC; }
    assert.strictEqual(leaked, 1, 'expected the unscoped read to leak the A closing into B; got ' + leaked);
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
