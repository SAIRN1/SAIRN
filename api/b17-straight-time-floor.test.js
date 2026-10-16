// api/b17-straight-time-floor.test.js
//
// Run:  node api/b17-straight-time-floor.test.js
//
// ROUTED BY fourth, b26, FINDING H2 (HIGH, on money). Driven by them against
// the real api/_lib/sen-payroll.js, section C:
//
//     UPWARD   (clock moved earlier) -> adjustment_cents= 2000  delta=[ 60]
//     DOWNWARD (clock moved later)   -> adjustment_cents=-2000  delta=[-60]
//                                       total_payable_cents=-2000
//
// `b.adjustment_cents += dCents` had no sign guard and `total_payable_cents =
// gross + b.adjustment_cents`. SO A SCHEDULER APPROVING A DOWNWARD CORRECTION
// SILENTLY DEDUCTED $20 FROM A LATER PERIOD'S WAGES.
//
// ── WHY A NEGATIVE ADJUSTMENT IS NOT AN ADJUSTMENT ───────────────────────
// fourth's decision, carried here as the requirement rather than re-argued:
// an adjustment line exists to PAY for work already performed and underpaid.
// A negative one is a WAGE DEDUCTION TO RECOVER AN OVERPAYMENT, which is a
// separate regulated act with its own conditions -- recoupment is permitted
// under the FLSA but not where the deduction takes a workweek below the
// minimum wage, and many states additionally require the employee's written
// authorisation. A payroll run must not perform one as a side effect of an
// approval, in a period the employee has not been told about.
//
// It is also the MIRROR of the harm F1 closed: F1 was sixty minutes unpaid by
// omission; this is sixty minutes removed by commission, which is worse
// because somebody chose it.
//
// ── THE THREE THINGS THIS SUITE REQUIRES ─────────────────────────────────
//   1. `adjustment_cents` is FLOORED AT 0 per visit.
//   2. The negative deltas are surfaced as their own `overpayments[]` list
//      carrying employee, visit, service date, minutes and cents -- requiring
//      a human act and NEVER netted into a payable total.
//   3. The invariant `total_payable_cents >= gross_cents`, which is the one
//      assertion that would have caught H2 with no knowledge of the cause.
//
// ── AND `premium_may_be_owed`, WHICH IS A THREE-STATE FLAG AND NEVER false
// fourth: "A disclosure that names a class is a note; a flag that names a
// person is payable." The FLSA premium on an adjustment's minutes stays a
// disclosed floor, with the condition that each adjustment SAYS when a
// premium may be owed.
//
// IT CAN BE true OR null AND NEVER false, and that is a measurement about
// what is knowable rather than a hedge. The as-paid weekly minutes are in
// hand only for the closed-period visits the CALLER happened to pass. If what
// we can see already reaches the threshold, more visits can only add, so
// `true` is sound. If what we can see does NOT reach it, an unseen visit in
// the same week could still push it over -- so the honest answer is CANNOT
// TELL, not "no premium". Arm A6 requires that, because a `false` here would
// be a fabricated clearance on somebody's overtime.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const fs = require('fs');
const path = require('path');

const PAYROLL_SRC = path.join(__dirname, '_lib', 'sen-payroll.js');

let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(l) { pass++; console.log('  ok       ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL     ' + l);
  if (why) console.log('           ' + String(why).slice(0, 600));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 600));
}
function is(c, l, why) { if (c) ok(l); else bad(l, why); }

// THE REAL MODULE. A reimplementation would pass against the unfixed code.
function freshPayroll(modPath) {
  const p = modPath || './_lib/sen-payroll';
  delete require.cache[require.resolve(p)];
  delete require.cache[require.resolve('./_lib/sen-evv-clock')];
  return require(p);
}

// ── fourth's b26 SECTION C FIXTURE, CARRIED FORWARD UNCHANGED ────────────
// Same visit and same rate as b16's freeze suite, so the numbers in this file
// are comparable to the ones the underpayment and the overpayment were both
// measured with: 240 minutes / 8000 cents as paid, at 2000 cents/hour.
const RATE_PER_HOUR = 20;                  // 2000 cents/hour
const DAY = '2026-10-05';                  // inside the CLOSED period
const REC_IN = '2026-10-05T09:00:00Z';
const REC_OUT = '2026-10-05T13:00:00Z';    // 240 min as paid
const COR_OUT_UP = '2026-10-05T14:00:00Z'; // 300 min -> +60, money OWED
const COR_OUT_DOWN = '2026-10-05T12:00:00Z'; // 180 min -> -60, OVERPAID

const PAID_AT = '2026-10-16T00:00:00Z';
const CLOSED = { period_start: '2026-10-01', period_end: '2026-10-15', paid_at: PAID_AT };
const OPEN_START = '2026-10-16', OPEN_END = '2026-10-31';
const APPROVED_AT = '2026-10-20T10:00:00Z';   // inside the OPEN period

function correction(proposedAt) {
  return {
    id: 'C1', field: 'clock_out_at',
    original_at: REC_OUT, proposed_at: proposedAt,
    reason_code: 'FORGOT_TO_CLOCK_OUT',
    filed_by: 'E1', filed_at_server: '2026-10-06T10:00:00Z',
    status: 'approved', approved_by: 'S1', approved_at_server: APPROVED_AT
  };
}

function visit(opts) {
  const o = opts || {};
  const v = {
    id: o.id || 'V1', visit_id: o.id || 'V1',
    assigned_employee_id: o.emp || 'E1',
    scheduled_date: o.day || DAY,
    clock_in_at: o.in || REC_IN,
    clock_out_at: o.out || REC_OUT
  };
  if (o.correctTo) v.clock_corrections = [correction(o.correctTo)];
  return v;
}

function resolveRate() { return { status: 'applied', rate_per_hour: RATE_PER_HOUR }; }

function run(opts, modPath) {
  const senPayroll = freshPayroll(modPath);
  const o = opts || {};
  return senPayroll.computePayroll({
    visits: o.visits,
    period_start: o.period_start,
    period_end: o.period_end,
    week_start_day: 'sunday',
    closed_periods: o.closed_periods,
    resolveRate: resolveRate
  });
}

function cg(out, i) {
  return out && out.caregivers && out.caregivers[i || 0] ? out.caregivers[i || 0] : null;
}

// ── THE ABLATION HARNESS. Restores on EVERY path and HARD-EXITS if it does
//    not, because a mutant left on disk is worse than a red arm.
function ablate(anchor, replacement, fn) {
  const src = fs.readFileSync(PAYROLL_SRC, 'utf8');
  const n = src.split(anchor).length - 1;
  if (n !== 1) return { ok: false, why: 'anchor occurs ' + n + ' times, not 1' };
  const backup = src;
  try {
    fs.writeFileSync(PAYROLL_SRC, src.split(anchor).join(replacement));
    const back = fs.readFileSync(PAYROLL_SRC, 'utf8');
    if (back.indexOf(replacement) === -1) {
      return { ok: false, why: 'the mutant did not land on disk' };
    }
    return { ok: true, result: fn() };
  } finally {
    fs.writeFileSync(PAYROLL_SRC, backup);
    const restored = fs.readFileSync(PAYROLL_SRC, 'utf8');
    if (restored !== backup) {
      console.log('  HARD ERROR the ablation did not restore '
        + 'api/_lib/sen-payroll.js -- DO NOT COMMIT, the file on disk is a mutant');
      process.exit(1);
    }
  }
}

function main() {
  console.log('api/b17-straight-time-floor.test.js');
  console.log('  an adjustment is never negative; an overpayment is surfaced, never netted');

  // ── A1: THE DOWNWARD CORRECTION NO LONGER DEDUCTS ──────────────────────
  let down = null;
  try {
    down = run({ visits: [visit({ correctTo: COR_OUT_DOWN })],
                 period_start: OPEN_START, period_end: OPEN_END,
                 closed_periods: [CLOSED] });
    const c = cg(down);
    is(c && c.adjustment_cents === 0 && c.adjustments === 0,
       'A1. a DOWNWARD correction posts NO adjustment line and deducts nothing',
       c && ('adjustment_cents=' + c.adjustment_cents
             + ' adjustments=' + c.adjustments));
  } catch (e) { bad('A1. a DOWNWARD correction deducts nothing', e && e.stack); }

  // ── A2: THE INVARIANT. The one assertion that catches H2 blind. ─────────
  try {
    const c = cg(down);
    is(c && c.total_payable_cents >= c.gross_cents,
       'A2. INVARIANT total_payable_cents >= gross_cents on the downward case',
       c && ('total_payable=' + c.total_payable_cents + ' gross=' + c.gross_cents));
  } catch (e) { bad('A2. INVARIANT total_payable_cents >= gross_cents', e && e.stack); }

  // ── A3: THE OVERPAYMENT IS SURFACED, with every field fourth named ─────
  try {
    const ops = (down && down.overpayments) || [];
    const o = ops[0];
    is(ops.length === 1 && o && o.employee_id === 'E1' && o.visit_id === 'V1'
       && o.service_date === DAY && o.minutes_delta === -60
       && o.cents_delta === -2000 && o.cents_overpaid === 2000
       && o.requires_human_act === true,
       'A3. overpayments[] names employee, visit, service date, minutes and cents',
       JSON.stringify(ops));
  } catch (e) { bad('A3. overpayments[] carries the five named fields', e && e.stack); }

  // ── A4: AND IT IS NEVER NETTED INTO A PAYABLE TOTAL ────────────────────
  // Period level AND caregiver level, because netting at either one is the
  // deduction fourth found wearing a different name.
  try {
    const c = cg(down);
    is(down && down.adjustment_cents === 0
       && down.overpayment_cents === 2000
       && c && c.total_payable_cents === c.gross_cents
       && c.overpayment_cents === 2000 && c.overpayments === 1,
       'A4. the overpayment is reported and NOT netted, at both levels',
       down && ('period adj=' + down.adjustment_cents
         + ' period overpaid=' + down.overpayment_cents
         + ' cg total=' + (c && c.total_payable_cents)
         + ' cg gross=' + (c && c.gross_cents)));
  } catch (e) { bad('A4. the overpayment is not netted', e && e.stack); }

  // ── A5: CONTROL. THE UPWARD CASE MUST NOT MOVE. ────────────────────────
  // b16's F3 measured 2000 cents owed and paid forward. If this arm moves,
  // the sign guard has broken the thing F1 was built to fix.
  let up = null;
  try {
    up = run({ visits: [visit({ correctTo: COR_OUT_UP })],
               period_start: OPEN_START, period_end: OPEN_END,
               closed_periods: [CLOSED] });
    const c = cg(up);
    is(c && c.adjustment_cents === 2000 && c.adjustments === 1
       && c.total_payable_cents === c.gross_cents + 2000
       && (up.overpayments || []).length === 0,
       'A5. CONTROL -- the UPWARD correction still pays 2000 cents forward',
       c && ('adjustment_cents=' + c.adjustment_cents
             + ' total_payable=' + c.total_payable_cents
             + ' overpayments=' + JSON.stringify(up.overpayments)));
  } catch (e) { bad('A5. CONTROL -- the upward correction still pays', e && e.stack); }

  // ── A6: premium_may_be_owed IS true WHEN THE WEEK SEEN ALREADY CROSSES ─
  // 2400 minutes is 40 hours. Six 400-minute visits in the closed week put
  // the as-paid week AT the threshold before the adjustment's 60 minutes are
  // considered, so a premium may be owed on those minutes and the adjustment
  // must say so by name rather than leaving it to not_computed's class note.
  try {
    const big = [];
    for (let i = 0; i < 6; i++) {
      big.push(visit({ id: 'W' + i, day: '2026-10-05',
        in: '2026-10-0' + (5 + (i % 2)) + 'T06:00:00Z',
        out: '2026-10-0' + (5 + (i % 2)) + 'T12:40:00Z' }));   // 400 min
    }
    big.push(visit({ correctTo: COR_OUT_UP }));
    const out = run({ visits: big, period_start: OPEN_START, period_end: OPEN_END,
                      closed_periods: [CLOSED] });
    const a = (out.adjustments || [])[0];
    is(a && a.premium_may_be_owed === true
       && a.premium_threshold_minutes === 2400
       && typeof a.as_paid_week_minutes_seen === 'number'
       && a.as_paid_week_minutes_seen >= 2400,
       'A6. premium_may_be_owed is TRUE when the as-paid week SEEN already crosses 40h',
       a && JSON.stringify({ f: a.premium_may_be_owed,
         seen: a.as_paid_week_minutes_seen, thr: a.premium_threshold_minutes }));
  } catch (e) { bad('A6. premium_may_be_owed true on a crossing week', e && e.stack); }

  // ── A7: AND IT IS null, NEVER false, WHEN THE WEEK SEEN DOES NOT CROSS ─
  // THE ASYMMETRY IS THE WHOLE POINT. An unseen visit in the same closed week
  // can only ADD minutes, so "what I can see is under 40h" does not entitle
  // anybody to say no premium is owed. `false` here would be a fabricated
  // clearance on somebody's overtime.
  try {
    const a = (up && up.adjustments || [])[0];
    const hasFalse = JSON.stringify(up && up.adjustments || [])
      .indexOf('"premium_may_be_owed":false') !== -1;
    is(a && a.premium_may_be_owed === null && !hasFalse,
       'A7. premium_may_be_owed is null and NEVER false when the week cannot be ruled out',
       a && JSON.stringify({ f: a.premium_may_be_owed,
         seen: a.as_paid_week_minutes_seen, hasFalse: hasFalse }));
  } catch (e) { bad('A7. premium_may_be_owed is null, never false', e && e.stack); }

  // ── A8: THE OUTPUT SAYS RECOVERY IS NOT PERFORMED ──────────────────────
  // A list of overpayments with no statement that nothing is being recovered
  // is readable as "handled". It is not handled; it is reported.
  try {
    const nc = (down && down.not_computed || []).join(' | ');
    is(/overpayment/i.test(nc) && /recover|recoup/i.test(nc)
       && /written authorisation|authorization|minimum wage/i.test(nc),
       'A8. not_computed states that no overpayment is recovered and why',
       nc.slice(0, 400));
  } catch (e) { bad('A8. not_computed states no recovery is performed', e && e.stack); }

  // ── A9: THE INVARIANT OVER HOSTILE SHAPES, not one fixture ─────────────
  // H2 was found on one shape. The invariant is cheap enough to assert over
  // every caregiver of every run, so an adjustment path added later cannot
  // reintroduce a negative total without this going red.
  try {
    const shapes = [
      [visit({ correctTo: COR_OUT_DOWN })],
      [visit({ correctTo: COR_OUT_DOWN }), visit({ id: 'V2', emp: 'E2', correctTo: COR_OUT_DOWN })],
      [visit({ correctTo: COR_OUT_DOWN }), visit({ id: 'V3', correctTo: COR_OUT_UP })],
      [visit({ id: 'V4', in: REC_OUT, out: REC_IN, correctTo: COR_OUT_DOWN })],
      [visit({ correctTo: '2026-10-05T09:00:00Z' })],   // corrected == clock_in
      []
    ];
    let viol = [];
    shapes.forEach((vs, i) => {
      const out = run({ visits: vs, period_start: OPEN_START, period_end: OPEN_END,
                        closed_periods: [CLOSED] });
      (out.caregivers || []).forEach((c) => {
        if (!(c.total_payable_cents >= c.gross_cents)) {
          viol.push('shape ' + i + ' ' + c.employee_id + ' total='
            + c.total_payable_cents + ' gross=' + c.gross_cents);
        }
        if (c.adjustment_cents < 0) {
          viol.push('shape ' + i + ' ' + c.employee_id + ' NEGATIVE adjustment_cents='
            + c.adjustment_cents);
        }
      });
      if ((out.adjustment_cents || 0) < 0) {
        viol.push('shape ' + i + ' period adjustment_cents=' + out.adjustment_cents);
      }
    });
    is(viol.length === 0,
       'A9. the invariant holds over 6 shapes, including two caregivers and a reversed clock',
       viol.join(' ; '));
  } catch (e) { bad('A9. the invariant over hostile shapes', e && e.stack); }

  // ── A10: ABLATION. REMOVE THE SIGN GUARD AND A1/A2/A4 MUST GO RED. ─────
  // Without this arm, A1 could be passing because the fixture never produces
  // a negative delta at all -- which is exactly how a test that proves
  // nothing looks from the outside.
  const GUARD = 'if (dMin > 0) {';
  try {
    const r = ablate(GUARD, 'if (dMin !== 0) {', () => {
      const out = run({ visits: [visit({ correctTo: COR_OUT_DOWN })],
                        period_start: OPEN_START, period_end: OPEN_END,
                        closed_periods: [CLOSED] });
      const c = cg(out);
      return { adj: c && c.adjustment_cents, total: c && c.total_payable_cents,
               gross: c && c.gross_cents };
    });
    if (!r.ok) {
      cannot('A10. ABLATION -- without the sign guard the deduction returns', r.why);
    } else {
      is(r.result.adj === -2000 && r.result.total < r.result.gross,
         'A10. ABLATION -- without the sign guard the deduction returns (-2000, total < gross)',
         JSON.stringify(r.result));
    }
  } catch (e) { bad('A10. ABLATION -- the sign guard is what A1 tests', e && e.stack); }

  // ── A11: CONTROL. NO closed_periods -> the b15 answer, plus empty lists.
  try {
    const out = run({ visits: [visit({ correctTo: COR_OUT_DOWN })],
                      period_start: CLOSED.period_start, period_end: CLOSED.period_end });
    const c = cg(out);
    is(c && c.adjustment_cents === 0 && c.adjustments === 0
       && (out.overpayments || []).length === 0 && out.overpayment_cents === 0
       && c.total_payable_cents === c.gross_cents,
       'A11. CONTROL -- with no closed_periods there is no adjustment and no overpayment',
       c && JSON.stringify({ adj: c.adjustment_cents, ops: out.overpayments }));
  } catch (e) { bad('A11. CONTROL -- no closed_periods', e && e.stack); }

  console.log('');
  console.log('  ' + pass + ' passed, ' + fail + ' failed, ' + unproven + ' unproven');
  if (failed.length) console.log('  FAILED: ' + failed.join(', '));
  if (notProved.length) console.log('  UNPROVEN: ' + notProved.join(', '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
}

main();
