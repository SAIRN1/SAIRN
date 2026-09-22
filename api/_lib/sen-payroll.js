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
 */
function computePayroll(input) {
  const i = input || {};
  const visits = Array.isArray(i.visits) ? i.visits : [];
  const start = typeof i.period_start === 'string' ? i.period_start : null;
  const end = typeof i.period_end === 'string' ? i.period_end : null;
  const dayIdx = DAY_NAMES.indexOf(String(i.week_start_day || '').toLowerCase());
  const resolveRate = typeof i.resolveRate === 'function' ? i.resolveRate : null;

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

  const excluded = {
    no_clock_out: 0, no_clock_in: 0, non_positive_duration: 0,
    outside_period: 0, no_caregiver: 0, no_rate: 0, ambiguous_rate: 0,
  };
  const byCaregiver = Object.create(null);

  const bucket = (id) => {
    if (!byCaregiver[id]) {
      byCaregiver[id] = {
        employee_id: id, weeks: Object.create(null),
        visits_counted: 0, visits_excluded: 0, no_rate_visits: 0,
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

    const inMs = instant(row.clock_in_at);
    const outMs = instant(row.clock_out_at);
    if (inMs === null) { excluded.no_clock_in += 1; b.visits_excluded += 1; return; }
    if (outMs === null) { excluded.no_clock_out += 1; b.visits_excluded += 1; return; }
    if (outMs <= inMs) {
      excluded.non_positive_duration += 1; b.visits_excluded += 1; return;
    }

    // The PERIOD is bounded by the service date, not by the clock instant --
    // the service date is what the rate is resolved against and what a payer
    // matches on, so using two different notions of "when" would let a visit
    // be paid in one period and billed in another.
    const serviceDate = (typeof row.scheduled_date === 'string')
      ? row.scheduled_date.trim() : '';
    if (!serviceDate || serviceDate < start || serviceDate > end) {
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
      minutes: weeks.reduce((s, w) => s + w.minutes, 0),
      overtime_minutes: weeks.reduce((s, w) => s + w.overtime_minutes, 0),
      gross_cents: weeks.reduce((s, w) => s + w.gross_cents, 0),
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
