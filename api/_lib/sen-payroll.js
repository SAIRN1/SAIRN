// api/_lib/sen-payroll.js
// ---------------------------------------------------------------------------
// SAIRNSENIOR PAYROLL: GROSS PAY FROM CLOCKED VISITS. Pure -- no I/O, no
// fetch, no LLM. Same functional-core split as api/_lib/dnt-rollup.js,
// api/_lib/law-trust-reconcile.js and api/_lib/sairncode-kx-accumulator.js:
// the gate, the read and the 503 live in the caller.
//
// ── THE GAP, MEASURED BEFORE IT WAS BUILT ─────────────────────────────────
// SAIRNsenior captures REAL verified visits: GPS at clock-in and clock-out,
// ISO timestamps, a positive-duration check, an offline queue that replays the
// original timestamps unchanged. It then used those hours for exactly one
// thing -- `visitLabourCost()` feeding a BRANCH GROSS-MARGIN table.
//
// `sql/sairnsenior_pay_rates_schema.sql` says so in its own words: "THIS IS
// GROSS MARGIN, NOT PROFIT... Direct labour is the only cost here." And
// `sairnsenior.html` says "This measures completed WORK, not payroll status."
// Searched: no sen_payroll, no sen_timesheet, no sen_paystub, no payroll
// export anywhere in *.js, *.html or *.sql. The EVV loop reached BILLING in
// one click and reached PAY not at all.
//
// This is the pay leg. It computes GROSS PAY and stops there -- see the
// boundary at the bottom, which is the more useful half of this file.
//
// ── PAID ON WHAT WAS CLOCKED, NEVER ON WHAT WAS SCHEDULED ────────────────
// The single rule everything else follows from. `scheduled_start`/
// `scheduled_end` describe an intention; `clock_in_at`/`clock_out_at` describe
// a visit somebody actually made. Paying the schedule would pay for visits
// that did not happen and underpay ones that ran long, and it would do it
// invisibly, because the schedule is always present and always well-formed.
// api/_lib/sen-evv-readiness.js already refuses to substitute one for the
// other and says why -- "EVV verifies what happened, not what was planned" --
// and the same sentence decides payroll.
//
// ── THE REGULAR RATE IS A WEIGHTED AVERAGE, AND THIS IS THE PART MOST
// ── IMPLEMENTATIONS GET WRONG ────────────────────────────────────────────
// FLSA overtime is 1.5x THE REGULAR RATE, and when an employee works at more
// than one rate in a workweek the regular rate is the WEIGHTED AVERAGE of all
// straight-time earnings divided by all hours worked (29 C.F.R. §778.115) --
// not "the rate of whichever visit happened to cross hour 40". A caregiver on
// $18 for personal care and $22 for skilled hours who crosses 40 during a $18
// visit is not owed $27/hr; the correct premium is half the weighted average,
// applied to every overtime hour.
//
// This matters here specifically because home care aides ARE covered: the
// Department of Labor's 2013 Home Care Rule (effective 2015) withdrew the
// companionship exemption from THIRD-PARTY EMPLOYERS, which is exactly what a
// home care agency is. An agency that assumed the old exemption is the failure
// mode this engine exists to make visible.
//
// WHAT IS NOT DECIDED HERE, because it is a legal question and not an
// arithmetic one: live-in arrangements, sleep-time exclusions, and whether
// TRAVEL TIME BETWEEN CLIENTS is compensable (it generally is, under
// §785.38). None of it is inferred. A visit is paid; the gaps between visits
// are reported as UNPAID GAPS with their durations so an agency can see what
// it has not decided, rather than having a decision made for it silently.
//
// ── THE WORKWEEK IS A CHOICE AND IT IS STATED, NEVER ASSUMED ─────────────
// FLSA overtime is computed per fixed and regularly recurring 168-hour
// workweek, and the employer picks its start day. Defaulting silently to
// Sunday would compute a legally different answer for an agency whose week
// starts Monday -- the same hours, a different overtime total, with nothing on
// screen saying which week was used. `week_start_day` is required.
//
// ── FOUR RULES, THE SAME FOUR THIS PLATFORM'S OTHER ENGINES ARGUE FOR ────
//
// 1. AN UNPAYABLE VISIT IS EXCLUDED, COUNTED AND NAMED. No clock-out, a
//    non-positive duration, no rate in force, or two rates in force -- each
//    is its own reason. None is quietly treated as zero hours, because zero
//    hours is a measurement and "we could not tell" is not.
//
// 2. AN EXCLUDED VISIT MAKES THE PERIOD A FLOOR. `is_floor` is true and the
//    caller must not present the figure as a final pay run. Underpaying
//    somebody because a row was unreadable is a wage claim, not a rounding
//    error.
//
// 3. A CAREGIVER WITH NO RATE IS REPORTED, NEVER PRICED AT ZERO. A zero-dollar
//    line on a pay run reads as "worked for nothing" and is indistinguishable
//    from a correct zero.
//
// 4. EVERY FIGURE CARRIES ITS VISIT COUNT AND ITS HOURS, so a total can be
//    traced back to the visits it came from.
//
// MONEY IS INTEGER CENTS; HOURS ARE INTEGER MINUTES. Rounding money at every
// visit and summing produces a systematic difference against rounding once at
// the end, and on a pay run that difference is somebody's wages.
// ---------------------------------------------------------------------------

'use strict';

// THE ONLY require IN THIS FILE, and it does not break the purity the header
// claims: api/_lib/sen-evv-clock.js is itself pure -- no fetch, no I/O -- and
// what is imported is the single function that decides which clock value is in
// effect. The alternative was a second copy of the approval rule in a file
// that computes wages, which is the shape this platform keeps paying for.
const senEvvClock = require('./sen-evv-clock');

const MINUTES_PER_HOUR = 60;
const FLSA_WEEKLY_HOURS = 40;
// 1.5x total, i.e. the PREMIUM is an extra half of the regular rate. Expressed
// as the premium rather than the multiplier because that is how it is actually
// applied to a weighted average -- see the note on §778.115 above.
const FLSA_OVERTIME_PREMIUM_NUMERATOR = 1;
const FLSA_OVERTIME_PREMIUM_DENOMINATOR = 2;

const DAY_NAMES = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday',
  'friday', 'saturday'];

/** Money to integer cents, or null. null is NOT 0 -- rule 3. */
function cents(v) {
  if (v === undefined || v === null) return null;
  if (typeof v === 'string' && v.trim() === '') return null;
  const n = typeof v === 'number' ? v : Number(String(v).trim());
  if (!Number.isFinite(n) || n < 0) return null;
  return Math.round(n * 100);
}

/** An ISO instant to epoch ms, or null. Strict: a value this cannot read is
 *  not a time, and `new Date('whenever')` yielding NaN must not become 0. */
function instant(v) {
  if (typeof v !== 'string' || v.trim() === '') return null;
  const t = Date.parse(v.trim());
  return Number.isFinite(t) ? t : null;
}

/**
 * The start of the FLSA workweek containing `ms`, as a YYYY-MM-DD key.
 *
 * COMPUTED IN UTC, DELIBERATELY, and this is a stated limitation rather than a
 * hidden one: clock timestamps are stored as ISO instants and this engine has
 * no agency timezone to work in. A visit clocked late on a Saturday evening in
 * a western timezone can therefore land in the following UTC week. The caller
 * is told which week each visit was assigned to (`week_start`) so the boundary
 * is visible; resolving it properly needs an agency timezone, which the app
 * does not capture today and which this file will not invent.
 */
function weekStartKey(ms, weekStartDay) {
  const d = new Date(ms);
  const dow = d.getUTCDay();
  const delta = (dow - weekStartDay + 7) % 7;
  const start = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(),
    d.getUTCDate() - delta));
  return start.toISOString().slice(0, 10);
}

/**
 * @param {object} input
 *   visits         {Array}  sen_visits rows as the server holds them
 *   rates          {Array}  sen_pay_rates rows
 *   period_start   {string} YYYY-MM-DD inclusive
 *   period_end     {string} YYYY-MM-DD inclusive
 *   week_start_day {string} 'sunday'..'saturday' -- REQUIRED, see the header
 *   resolveRate    {function(employeeId, serviceDate) -> {status, rate_per_hour}}
 *                  injected so the app and the server share ONE rate
 *                  resolution. A second implementation of "which wage was in
 *                  force" is a second answer to somebody's pay.
 *   closed_periods {Array}  OPTIONAL. [{period_start, period_end, paid_at}].
 *                  A period that has been PAID. See the freeze note below.
 *                  Absent or empty means nothing is frozen and the answer is
 *                  identical to b15's.
 */
function computePayroll(input) {
  const i = input || {};
  const visits = Array.isArray(i.visits) ? i.visits : [];
  const start = typeof i.period_start === 'string' ? i.period_start : null;
  const end = typeof i.period_end === 'string' ? i.period_end : null;
  const dayIdx = DAY_NAMES.indexOf(String(i.week_start_day || '').toLowerCase());
  const resolveRate = typeof i.resolveRate === 'function' ? i.resolveRate : null;
  const closedIn = Array.isArray(i.closed_periods) ? i.closed_periods : [];

  // REFUSALS, NOT DEFAULTS. Each of these would otherwise produce a confident
  // pay run computed against something nobody chose.
  if (!start || !end) {
    return refusal('NO_PERIOD', 'A pay period start and end are required. '
      + 'Computing "everything on file" would pay visits already paid in an '
      + 'earlier run.');
  }
  if (dayIdx === -1) {
    return refusal('NO_WEEK_START', 'A workweek start day is required. FLSA '
      + 'overtime is computed per fixed 168-hour workweek and the employer '
      + 'chooses its start day; guessing Sunday would compute a legally '
      + 'different answer for an agency whose week starts Monday, with '
      + 'nothing on screen saying which was used.');
  }
  if (!resolveRate) {
    return refusal('NO_RATE_RESOLVER', 'No pay-rate resolver was supplied, so '
      + 'no wage could be established for any visit. Nothing was computed.');
  }

  // ══ PAID PERIODS ARE FROZEN (2026-10-15, b16 -- MICHAEL'S DECISION) ══════
  // A clock correction approved AFTER a pay run never rewrites a closed total.
  // It posts as an ADJUSTMENT LINE in the period where the approval happened.
  //
  // WHY, in one sentence: b15's F1 made an approved correction reach pay, and
  // the mirror of that fix is that it also reached pay runs ALREADY MADE --
  // a wage reported to a payer and auditable by a state EVV programme moving
  // because somebody approved a correction a week later. The b15 handoff named
  // it as worse than the underpayment it closed, and it is: the underpayment
  // is visible to the caregiver, a silently restated history is visible to
  // nobody.
  //
  // THE FREEZE IS A TIME, NOT A FLAG, and the time lives in
  // api/_lib/sen-evv-clock.js's effectiveClockAsOf -- the one function that
  // decides what "approved" means. A second copy of that rule in this file is
  // the exact shape of the defect F1 was.
  //
  // EVERY FIELD IS VALIDATED AND AN UNREADABLE paid_at REFUSES THE RUN. A
  // freeze that cannot say what instant it froze against would silently pick
  // one of the two answers, and both are wrong half the time.
  const closedPeriods = [];
  for (let ci = 0; ci < closedIn.length; ci += 1) {
    const c = closedIn[ci] || {};
    const cs = calendarDate(c.period_start);
    const ce = calendarDate(c.period_end);
    const paidMs = instant(c.paid_at);
    if (!cs || !ce || paidMs === null) {
      return refusal('UNDATED_CLOSED_PERIOD', 'A closed pay period was supplied '
        + 'that this engine cannot date: period_start=' + JSON.stringify(c.period_start)
        + ', period_end=' + JSON.stringify(c.period_end)
        + ', paid_at=' + JSON.stringify(c.paid_at) + '. Nothing was computed. '
        + 'A paid period is frozen as at the instant it was paid, so without '
        + 'that instant there is no way to tell which corrections were in the '
        + 'figure that was actually paid -- and guessing either way restates '
        + 'somebody\'s wages or withholds money they are owed.');
    }
    closedPeriods.push({ period_start: cs, period_end: ce, paid_at: c.paid_at,
                         paid_at_ms: paidMs });
  }
  // The closed period a SERVICE DATE falls in, or null. Service date and not
  // the clock instant, for the same reason the period bounds use it: it is
  // what the rate resolves against and what a payer matches on.
  const closedFor = (serviceDate) => {
    for (let k = 0; k < closedPeriods.length; k += 1) {
      const c = closedPeriods[k];
      if (serviceDate >= c.period_start && serviceDate <= c.period_end) return c;
    }
    return null;
  };
  // The period BEING RUN is reported as closed when it falls inside one, so a
  // caller showing a total can say whether it is a live computation or a
  // restatement of a frozen one.
  const runClosed = (start && end) ? closedFor(start) : null;
  const periodClosed = (runClosed && end <= runClosed.period_end)
    ? { period_start: runClosed.period_start, period_end: runClosed.period_end,
        paid_at: runClosed.paid_at }
    : null;

  const excluded = {
    no_clock_out: 0, no_clock_in: 0, non_positive_duration: 0,
    outside_period: 0, no_caregiver: 0, no_rate: 0, ambiguous_rate: 0,
  };
  const adjustments = [];
  const adjustmentsSkipped = [];
  let undatableTotal = 0;
  let pendingTotal = 0;
  const byCaregiver = Object.create(null);

  const bucket = (id) => {
    if (!byCaregiver[id]) {
      byCaregiver[id] = {
        employee_id: id, weeks: Object.create(null),
        visits_counted: 0, visits_excluded: 0, no_rate_visits: 0,
        // F1, 2026-10-15. Counted per caregiver so a wage that differs from
        // the recorded clock times can be RECONCILED against the EVV record
        // -- which is the whole purpose of keeping the trail. A figure that
        // silently disagrees with the clock is one nobody can check.
        corrected_clock_visits: 0,
        // b16. Money owed for a FROZEN period, paid in this one. Kept separate
        // from gross_cents so every existing caller's number keeps its
        // existing meaning -- the sum of the FLSA weeks in the period run.
        adjustment_cents: 0,
        adjustment_minutes: 0,
        adjustments: 0,
        // Approved corrections that carry no readable approval instant, so
        // they cannot be placed on either side of the freeze. Counted, never
        // silent.
        undatable_corrections: 0,
        // b17. A pending correction is a DISPUTE, counted so a pay run says
        // so rather than handing over a figure the caregiver is contesting.
        pending_corrections: 0,
        pending_correction_visits: 0,
      };
    }
    return byCaregiver[id];
  };

  visits.forEach((v) => {
    const row = v || {};
    const emp = (typeof row.assigned_employee_id === 'string')
      ? row.assigned_employee_id.trim() : '';
    if (!emp) { excluded.no_caregiver += 1; return; }
    const b = bucket(emp);

    // ── THE APPROVED CORRECTION IS THE TIME THAT GETS PAID (2026-10-15, F1)
    // These two lines read `row.clock_in_at` and `row.clock_out_at` RAW, and
    // `grep -c effectiveClock` over this file returned 0 -- while
    // api/_lib/sen-evv-clock.js says of effectiveClock() that the approval
    // rule is "implemented HERE, in the function payroll reads". Payroll was
    // not reading it. AN APPROVED CLOCK CORRECTION REACHED NOTHING: fourth's
    // b23 repro measured one visit with one approved correction at 240
    // minutes / 8000 cents, against 300 / 10000 with the correction applied.
    // SIXTY MINUTES AND 2000 CENTS UNPAID, per visit, per correction.
    //
    // IT IS THE MIRROR OF THE THING THAT WAS VERIFIED SAFE in the same
    // review: a PENDING correction also reached nothing, which was the
    // correct answer. Both came from one cause -- this module never looked at
    // `clock_corrections` at all -- and only one direction was harmless.
    //
    // THE SUBSTITUTION IS HERE AND NOT IN THE CALLER'S MAP. api/sd-data.js's
    // payroll branch already spreads `x.data`, so the corrections were always
    // on the row; fixing the map would fix ONE caller, and this module is the
    // authority for pay. Same lesson as the self-approval rule: a rule
    // enforced in one branch of one endpoint is a rule the next caller does
    // not get.
    //
    // ONE SOURCE FOR THE RULE. effectiveClock() decides what "approved"
    // means, including that an entry with NO `status` is approved -- every
    // correction written before 2026-10-14 was effective the moment it was
    // filed, and reading a missing status as pending here would silently
    // un-pay all of them. A second copy of that condition in this file is a
    // second thing to drift on a wage.
    //
    // AND THE GUARDS BELOW RUN ON THE EFFECTIVE VALUES, which is why the
    // substitution happens before them rather than after: an approved
    // correction that inverts a visit must be EXCLUDED as a non-positive
    // duration, not paid as a huge number. A substitution applied after the
    // ordering check would be a route around it.
    // The PERIOD is bounded by the service date, not by the clock instant --
    // the service date is what the rate is resolved against and what a payer
    // matches on, so using two different notions of "when" would let a visit
    // be paid in one period and billed in another.
    //
    // READ BEFORE THE CLOCK GUARDS AS OF b16, because the service date is what
    // decides WHICH FREEZE INSTANT this visit's clock is read as of. The GUARD
    // ORDER below is unchanged -- no_clock_in/no_clock_out/non_positive still
    // come before outside_period, so every exclusion count means what it meant.
    const serviceDate = (typeof row.scheduled_date === 'string')
      ? row.scheduled_date.trim() : '';
    const inClosed = serviceDate ? closedFor(serviceDate) : null;
    const inPeriod = !!serviceDate && serviceDate >= start && serviceDate <= end;

    // AS AT THE INSTANT THIS VISIT'S PERIOD WAS PAID, if it was. A visit in an
    // open period gets asOf null, which is current truth and is what b15 did.
    const asOf = inClosed ? inClosed.paid_at : null;
    const effIn = senEvvClock.effectiveClockAsOf(row, 'clock_in_at', asOf);
    const effOut = senEvvClock.effectiveClockAsOf(row, 'clock_out_at', asOf);
    const inMs = instant(effIn.corrected ? effIn.value : row.clock_in_at);
    const outMs = instant(effOut.corrected ? effOut.value : row.clock_out_at);
    const usedCorrection = !!(effIn.corrected || effOut.corrected);
    const undatableHere = (effIn.undatable || 0) + (effOut.undatable || 0);
    if (undatableHere) {
      b.undatable_corrections += undatableHere;
      undatableTotal += undatableHere;
    }
    // ── THE PENDING FIELDS REACH THE OUTPUT (2026-10-15, b17) ─────────────
    // ROUTED BY fourth/H1: effectiveClock() must KEEP pending, pending_count
    // and pending_entries. It does -- api/_lib/sen-evv-clock.js's own note
    // says a submission no screen shows is a submission nobody will ever
    // approve -- and until now THIS MODULE THREW THEM AWAY. It read `.value`,
    // `.corrected` and `.undatable` and nothing else.
    //
    // WHY THAT MATTERS ON A PAY RUN SPECIFICALLY: a pending correction means
    // the caregiver has SAID the recorded clock is wrong and nobody has ruled
    // on it. Payroll correctly pays the recorded time -- a self-asserted time
    // must not reach a wage -- but a run that does not SAY so hands over a
    // figure the caregiver is already disputing, and the dispute is invisible
    // on the only document anybody looks at. That is the whole shape of F1
    // again: the data was on the row and the consumer did not read it.
    //
    // COUNTED, NOT APPLIED. Nothing about what gets PAID changes here.
    const pendingHere = (effIn.pending_count || 0) + (effOut.pending_count || 0);
    if (pendingHere) {
      b.pending_corrections += pendingHere;
      b.pending_correction_visits += 1;
      pendingTotal += pendingHere;
    }

    // ── THE CARRY-FORWARD. A visit in a CLOSED period carrying an approval
    //    that landed AFTER that period was paid is money owed and not yet
    //    paid. It is posted here as an adjustment rather than added to the
    //    frozen total.
    //
    // IT POSTS IN THE PERIOD CONTAINING THE APPROVAL, which is what stops it
    // posting again in every period that follows forever. The cost of that
    // choice is stated rather than hidden: a period that is never run never
    // pays its adjustments, and `not_computed` says so.
    if (inClosed && !inPeriod) {
      const notYet = ((effIn.not_yet_entries || []).concat(effOut.not_yet_entries || []))
        .filter((e) => {
          const d = typeof e.approved_at_server === 'string'
            ? e.approved_at_server.slice(0, 10) : '';
          return d >= start && d <= end;
        });
      if (notYet.length) {
        const nowIn = senEvvClock.effectiveClockAsOf(row, 'clock_in_at', null);
        const nowOut = senEvvClock.effectiveClockAsOf(row, 'clock_out_at', null);
        const nIn = instant(nowIn.corrected ? nowIn.value : row.clock_in_at);
        const nOut = instant(nowOut.corrected ? nowOut.value : row.clock_out_at);
        const rateA = resolveRate(emp, serviceDate) || {};
        const rateACents = rateA.status === 'applied' ? cents(rateA.rate_per_hour) : null;
        // EVERY WAY THIS CAN FAIL IS NAMED AND NONE OF THEM IS A SILENT ZERO.
        // An adjustment that cannot be computed is a thing a human has to go
        // and look at, not a line worth 0 cents.
        let why = null;
        if (inMs === null || outMs === null || outMs <= inMs) why = 'as_paid_basis_unusable';
        else if (nIn === null || nOut === null || nOut <= nIn) why = 'corrected_basis_unusable';
        else if (rateACents === null) why = 'no_rate_on_service_date';
        if (why) {
          adjustmentsSkipped.push({ employee_id: emp, visit_id: row.id || row.visit_id || null,
            service_date: serviceDate, reason: why });
        } else {
          const asPaidMinutes = Math.round((outMs - inMs) / 60000);
          const nowMinutes = Math.round((nOut - nIn) / 60000);
          const dMin = nowMinutes - asPaidMinutes;
          if (dMin !== 0) {
            const dCents = Math.round(rateACents * dMin / MINUTES_PER_HOUR);
            adjustments.push({
              employee_id: emp,
              visit_id: row.id || row.visit_id || null,
              service_date: serviceDate,
              closed_period_start: inClosed.period_start,
              closed_period_end: inClosed.period_end,
              paid_at: inClosed.paid_at,
              as_paid_minutes: asPaidMinutes,
              corrected_minutes: nowMinutes,
              minutes_delta: dMin,
              rate_cents_per_hour: rateACents,
              cents_delta: dCents,
              approved_at_server: notYet.map((e) => e.approved_at_server)
            });
            b.adjustments += 1;
            b.adjustment_minutes += dMin;
            b.adjustment_cents += dCents;
          }
        }
      }
    }

    if (inMs === null) { excluded.no_clock_in += 1; b.visits_excluded += 1; return; }
    if (outMs === null) { excluded.no_clock_out += 1; b.visits_excluded += 1; return; }
    if (outMs <= inMs) {
      excluded.non_positive_duration += 1; b.visits_excluded += 1; return;
    }

    if (!inPeriod) {
      excluded.outside_period += 1; return;
    }

    const rate = resolveRate(emp, serviceDate) || {};
    if (rate.status === 'ambiguous') {
      // Two rates in force is a data problem with a wrong answer available:
      // picking either one pays a wage nobody chose. Refused per visit.
      excluded.ambiguous_rate += 1; b.visits_excluded += 1; return;
    }
    if (rate.status !== 'applied') {
      excluded.no_rate += 1; b.visits_excluded += 1; b.no_rate_visits += 1; return;
    }
    const rateCents = cents(rate.rate_per_hour);
    if (rateCents === null) {
      excluded.no_rate += 1; b.visits_excluded += 1; b.no_rate_visits += 1; return;
    }

    // MINUTES, then money once at the end. Rounding each visit to cents and
    // summing drifts against rounding the week once, and on a pay run the
    // drift is somebody's wages.
    const minutes = Math.round((outMs - inMs) / 60000);
    const wk = weekStartKey(inMs, dayIdx);
    if (!b.weeks[wk]) b.weeks[wk] = { week_start: wk, minutes: 0, straight_cents: 0, visits: 0 };
    const w = b.weeks[wk];
    w.minutes += minutes;
    // Straight-time earnings for this visit at ITS OWN rate. The weighted
    // average falls out of the sum, which is the whole point of §778.115.
    w.straight_cents += Math.round(rateCents * minutes / MINUTES_PER_HOUR);
    w.visits += 1;
    b.visits_counted += 1;
    if (usedCorrection) b.corrected_clock_visits += 1;
  });

  const caregivers = Object.keys(byCaregiver).sort().map((id) => {
    const b = byCaregiver[id];
    const weeks = Object.keys(b.weeks).sort().map((k) => {
      const w = b.weeks[k];
      const otMinutes = Math.max(0, w.minutes - FLSA_WEEKLY_HOURS * MINUTES_PER_HOUR);
      // THE WEIGHTED AVERAGE, in cents per hour, carried at full precision
      // until the single rounding below. Dividing early is where the classic
      // penny-per-hour payroll discrepancy comes from.
      const regularRateCentsPerHour = w.minutes > 0
        ? (w.straight_cents * MINUTES_PER_HOUR) / w.minutes
        : 0;
      const premiumCents = Math.round(
        regularRateCentsPerHour * otMinutes / MINUTES_PER_HOUR
        * FLSA_OVERTIME_PREMIUM_NUMERATOR / FLSA_OVERTIME_PREMIUM_DENOMINATOR);
      return {
        week_start: w.week_start,
        visits: w.visits,
        minutes: w.minutes,
        overtime_minutes: otMinutes,
        // Rounded here and nowhere else.
        regular_rate_cents_per_hour: Math.round(regularRateCentsPerHour),
        straight_time_cents: w.straight_cents,
        overtime_premium_cents: premiumCents,
        gross_cents: w.straight_cents + premiumCents,
      };
    });
    const isFloor = b.visits_excluded > 0;
    return {
      employee_id: b.employee_id,
      weeks: weeks,
      visits_counted: b.visits_counted,
      visits_excluded: b.visits_excluded,
      corrected_clock_visits: b.corrected_clock_visits,
      minutes: weeks.reduce((s, w) => s + w.minutes, 0),
      overtime_minutes: weeks.reduce((s, w) => s + w.overtime_minutes, 0),
      gross_cents: weeks.reduce((s, w) => s + w.gross_cents, 0),
      // b16. THREE NUMBERS AND NOT ONE. `gross_cents` keeps its existing
      // meaning (the FLSA weeks in the period run), `adjustment_cents` is what
      // a frozen period owes and this period pays, and `total_payable_cents`
      // is what the agency actually hands over. Folding the adjustment into
      // gross_cents would put a closed week's hours into an open week's
      // overtime computation, which is the freeze defeated one step removed.
      adjustment_cents: b.adjustment_cents,
      adjustment_minutes: b.adjustment_minutes,
      adjustments: b.adjustments,
      total_payable_cents: weeks.reduce((s, w) => s + w.gross_cents, 0) + b.adjustment_cents,
      undatable_corrections: b.undatable_corrections,
      pending_corrections: b.pending_corrections,
      pending_correction_visits: b.pending_correction_visits,
      // Rule 2 and rule 3, as two separate facts. A caregiver may be a floor
      // because a clock-out is missing (fixable on the visit) or because no
      // rate is on file (fixable on the rate table), and the two go to
      // different people.
      is_floor: isFloor,
      no_rate_visits: b.no_rate_visits,
    };
  });

  return {
    refused: null,
    period_start: start,
    period_end: end,
    week_start_day: DAY_NAMES[dayIdx],
    caregivers: caregivers,
    excluded: excluded,
    total_visits: visits.length,
    // ── THE FREEZE, IN THE OUTPUT (b16) ───────────────────────────────────
    // null when nothing is frozen, which is every caller that passes no
    // closed_periods. When it is set, the period total being shown is a
    // RESTATEMENT of a figure already paid and the caller must be able to say
    // so -- a frozen total presented as a live computation is the same lie as
    // a live one presented as frozen.
    period_closed: periodClosed,
    adjustments: adjustments,
    adjustment_cents: adjustments.reduce((s, a) => s + a.cents_delta, 0),
    // An adjustment that could NOT be computed. Never a zero-cent line: a
    // visit whose as-paid or corrected basis is unusable is something a human
    // has to look at, and a 0 would say the opposite.
    adjustments_skipped: adjustmentsSkipped,
    undatable_corrections: undatableTotal,
    // b17. Period-level, same reason as the per-caregiver pair: the person
    // looking at a total must be able to see that N corrections are waiting on
    // a scheduler's decision and are NOT in these figures.
    pending_corrections: pendingTotal,
    // Rule 2 at the period level: ANY exclusion anywhere makes the whole run
    // provisional, because a caller showing a period total has no way to know
    // which caregiver the missing row belonged to.
    is_floor: caregivers.some((c) => c.is_floor)
      || excluded.no_caregiver > 0,
    // NAMED RATHER THAN IMPLIED. Everything this does not compute, in the
    // output, so a caller cannot present it as a finished pay run.
    not_computed: [
      'Taxes, withholding and net pay. This is GROSS only.',
      'Travel time between clients, which is generally compensable under 29 '
        + 'C.F.R. §785.38 and is not inferable from visit records alone.',
      'Live-in arrangements and sleep-time exclusions.',
      'Paid leave, holiday premiums, shift differentials and bonuses, none of '
        + 'which this app records.',
      'State overtime rules that are more generous than the FLSA.',
      'THE OVERTIME CONSEQUENCE OF AN ADJUSTMENT. An adjustment line is '
        + 'straight time at the rate in force on the service date. If its '
        + 'minutes push the already-paid workweek past 40 hours there is an '
        + 'FLSA overtime premium owed on top, and recomputing it would mean '
        + 'reopening the frozen week this mechanism exists to protect. The '
        + 'adjustment is therefore a FLOOR on what is owed, not the whole of '
        + 'it.',
      'AN ADJUSTMENT POSTS IN THE PERIOD CONTAINING ITS APPROVAL, so a period '
        + 'that is never run never pays its adjustments. Nothing here sweeps '
        + 'for unposted ones.',
    ],
  };
}

/** YYYY-MM-DD or null. Strict for the same reason as everywhere else on this
 *  platform: `new Date` silently REPAIRS an impossible date rather than
 *  rejecting it, and a repaired `term_on` moves when a wage stopped applying. */
function calendarDate(v) {
  if (typeof v !== 'string') return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(v.trim());
  if (!m) return null;
  const y = Number(m[1]), mo = Number(m[2]), d = Number(m[3]);
  const dt = new Date(Date.UTC(y, mo - 1, d));
  if (dt.getUTCFullYear() !== y || dt.getUTCMonth() !== mo - 1
      || dt.getUTCDate() !== d) return null;
  return m[0].trim();
}

/**
 * Build a resolver over sen_pay_rates rows.
 *
 * ── SAME SEMANTICS AS THE CLIENT'S prInForce, AND THAT IS A KNOWN DUPLICATE
 * ── RATHER THAN A NEW ONE ─────────────────────────────────────────────────
 * `sairnsenior.html` already resolves in-force rates for the BRANCH MARGIN
 * analytic, and a single-file HTML app cannot require() this module. So the
 * duplication is real and is named here rather than discovered later: this is
 * the authority for PAY, that one is the authority for a cost report, and if
 * they ever disagree the pay figure is the one that matters. Do not add a
 * third.
 *
 * THE UNREADABLE TERM DATE RULE IS THE SUBTLE HALF and it is copied
 * deliberately, with its reason: a `term_on` that is present but unparseable
 * makes the rate NOT in force, rather than being skipped as though the field
 * were blank. Skipping it turns a superseded wage into an open-ended one and
 * keeps paying it forever.
 */
function resolveRateFrom(rates) {
  const list = Array.isArray(rates) ? rates : [];
  return function resolve(employeeId, serviceDate) {
    const on = calendarDate(serviceDate);
    if (!on) return { status: 'none', reason: 'The visit has no usable service date.' };
    const key = String(employeeId || '').trim();
    if (!key) return { status: 'none', reason: 'The visit names no caregiver.' };
    const mine = list.filter((r) => String((r && r.employee_id) || '').trim() === key);
    const live = mine.filter((r) => {
      const eff = calendarDate(r.effective_on);
      if (!eff || eff > on) return false;
      if (r.term_on !== undefined && r.term_on !== null && String(r.term_on) !== '') {
        const term = calendarDate(r.term_on);
        if (!term) return false;
        if (term < on) return false;
      }
      return true;
    });
    if (!live.length) {
      return { status: 'none', reason: mine.length
        ? 'This caregiver has ' + mine.length + ' pay rate(s) on file but none in force on ' + on + '.'
        : 'No pay rate is on file for this caregiver.' };
    }
    if (live.length > 1) {
      return { status: 'ambiguous', count: live.length,
        reason: live.length + ' pay rates are in force on ' + on
          + '. None is applied: paying a wage nobody chose is worse than '
          + 'refusing. Give one of them an end date.' };
    }
    return { status: 'applied', rate_per_hour: live[0].rate_per_hour };
  };
}

function refusal(code, message) {
  return {
    refused: { code: code, message: message },
    caregivers: [], excluded: null, total_visits: 0, is_floor: true,
    not_computed: [],
  };
}

module.exports = {
  computePayroll,
  resolveRateFrom,
  calendarDate,
  cents,
  instant,
  weekStartKey,
  DAY_NAMES,
  FLSA_WEEKLY_HOURS,
};
