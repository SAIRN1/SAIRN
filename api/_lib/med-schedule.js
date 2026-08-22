// api/_lib/med-schedule.js
// SAIRNcare Phase 3: medication scheduling + missed/late-care detection.
//
// PURE -- no I/O. Same shape and reasoning as payer-routing.js and
// compliance-rules.js: the timing logic is testable against worked examples
// without a database or a clock.
//
// WHY THIS FILE HAD TO EXIST BEFORE ANY ALERTING COULD:
// the medication order's `schedule` field is FREE TEXT ("e.g. 08:00, 14:00,
// 20:00 or twice daily") and nothing in the app has ever parsed it. There was
// therefore nothing machine-readable to compute "past its window" against. An
// alert engine built on that field would either invent windows from prose or
// silently never fire -- both worse than no feature. So a structured
// `schedule_times` array is the real prerequisite, and this module owns it.
//
// MIGRATION IS LOSSLESS AND HONEST. An existing order has only free text.
// parseScheduleText() recovers explicit clock times ("08:00, 14:00") because
// those are unambiguous. It REFUSES to invent times for prose like "twice
// daily" -- there is no way to know whether that means 08:00/20:00 or
// 09:00/21:00, and a guessed window would produce false "late" alerts against
// real nurses. Those orders are reported as unschedulable until someone enters
// real times, never silently assigned a default.

'use strict';

const HHMM = /^([01]\d|2[0-3]):([0-5]\d)$/;

function isValidTime(t) { return HHMM.test(String(t || '')); }

// Pull explicit HH:MM clock times out of a free-text schedule. Returns
// { times: [...], confident: bool, reason }. confident=false means the text
// carried scheduling intent this parser will not guess at.
function parseScheduleText(text) {
  const raw = String(text || '').trim();
  if (!raw) return { times: [], confident: false, reason: 'No schedule was recorded on this order.' };
  const found = [];
  const re = /\b([01]?\d|2[0-3]):([0-5]\d)\s*(am|pm)?/gi;
  let m;
  while ((m = re.exec(raw)) !== null) {
    let h = Number(m[1]);
    const min = m[2];
    const mer = (m[3] || '').toLowerCase();
    if (mer === 'pm' && h < 12) h += 12;
    if (mer === 'am' && h === 12) h = 0;
    const t = String(h).padStart(2, '0') + ':' + min;
    if (isValidTime(t) && found.indexOf(t) === -1) found.push(t);
  }
  if (found.length) {
    found.sort();
    return { times: found, confident: true, reason: null };
  }
  // Deliberately NOT translated into times. Listing the phrases we recognise as
  // "meant something but was not explicit" is more useful than a silent empty.
  const vague = /\b(daily|bid|tid|qid|twice|three times|four times|every|nightly|morning|evening|bedtime|hs|prn|as needed|weekly)\b/i.test(raw);
  return {
    times: [],
    confident: false,
    reason: vague
      ? 'This order’s schedule is written as prose ("' + raw + '") rather than clock times. Enter explicit times to enable due-time tracking — this app will not guess what hours were meant.'
      : 'No clock times could be read from this order’s schedule ("' + raw + '").'
  };
}

// The times an order is actually scheduled for. Structured times always win;
// free text is only a fallback for orders written before schedule_times existed.
function scheduleTimesFor(order) {
  if (!order) return { times: [], source: 'none', confident: false, reason: 'No order supplied.' };
  if (Array.isArray(order.schedule_times) && order.schedule_times.length) {
    const times = order.schedule_times.filter(isValidTime).slice().sort();
    if (times.length !== order.schedule_times.length) {
      return { times: times, source: 'structured', confident: false, reason: 'Some recorded schedule times are not valid HH:MM values and were ignored.' };
    }
    return { times: times, source: 'structured', confident: true, reason: null };
  }
  const parsed = parseScheduleText(order.schedule);
  return { times: parsed.times, source: parsed.times.length ? 'parsed_from_text' : 'none', confident: parsed.confident, reason: parsed.reason };
}

// ── DUE TIMES AND LATENESS ───────────────────────────────────────────────
// All arithmetic is UTC-offset-free: callers pass a local "now" as an ISO
// string and a day string, and comparisons happen on those. Mixing a local
// clock into Date math is how off-by-one bugs happen, and this platform has
// already shipped one.
function minutesOfDay(hhmm) {
  const m = HHMM.exec(hhmm);
  if (!m) return null;
  return (Number(m[1]) * 60) + Number(m[2]);
}

// Build the list of scheduled doses for one resident-day, each with its window.
// graceMinutes is the facility's own policy, passed in -- NOT a default this
// module invents. No ALF regulation surveyed sets a universal administration
// window, so a hardcoded number here would be a fabricated standard.
function dosesForDay(order, dayStr, graceMinutes) {
  const sched = scheduleTimesFor(order);
  if (!sched.times.length) {
    return { ok: false, schedulable: false, reason: sched.reason, order_id: order && order.id, times: [] };
  }
  if (order && order.prn) {
    return { ok: false, schedulable: false, reason: 'PRN (as-needed) orders have no scheduled due time, so they are never "late".', order_id: order.id, times: [] };
  }
  if (order && order.discontinued) {
    return { ok: false, schedulable: false, reason: 'This order is discontinued.', order_id: order.id, times: [] };
  }
  if (order && order.start_date && dayStr < order.start_date) {
    return { ok: false, schedulable: false, reason: 'This order does not start until ' + order.start_date + '.', order_id: order.id, times: [] };
  }
  const grace = Number(graceMinutes);
  if (!isFinite(grace) || grace < 0) {
    return { ok: false, schedulable: false, reason: 'A facility administration-window (grace) policy in minutes is required — this app does not assume one.', order_id: order && order.id, times: [] };
  }
  return {
    ok: true, schedulable: true, order_id: order.id, source: sched.source,
    times: sched.times.map((t) => ({
      time: t,
      due_at: dayStr + 'T' + t,
      late_after_minutes: grace,
      minutes_of_day: minutesOfDay(t)
    }))
  };
}

// Given the day's scheduled doses and the administrations actually recorded,
// return which doses are still outstanding and which are late.
//
// A dose counts as GIVEN if a real administration entry exists for that order
// on that day whose recorded time falls within the window. Nothing is inferred
// from the absence of a record other than "not recorded" -- which is exactly
// what a missed-care alert is supposed to surface.
function evaluateDay(opts) {
  opts = opts || {};
  const order = opts.order;
  const dayStr = opts.day;
  const nowMinutes = opts.now_minutes_of_day;
  const doses = dosesForDay(order, dayStr, opts.grace_minutes);
  if (!doses.ok) return { ok: false, schedulable: false, reason: doses.reason, order_id: doses.order_id, findings: [] };
  if (typeof nowMinutes !== 'number' || !isFinite(nowMinutes)) {
    return { ok: false, schedulable: true, reason: 'The current time of day is required to determine lateness.', order_id: order.id, findings: [] };
  }
  const admins = (opts.administrations || []).filter((a) =>
    a && a.medication_id === order.id && String(a.day || '') === dayStr
  );
  const findings = doses.times.map((d) => {
    // Match an administration to a dose by nearest scheduled time, so two doses
    // of the same drug on one day cannot both be satisfied by one record.
    const match = admins.find((a) => a.matched_dose_time === d.time)
      || admins.find((a) => !a._used && Math.abs((minutesOfDay(String(a.time || '')) || -9999) - d.minutes_of_day) <= d.late_after_minutes);
    if (match) match._used = true;
    const minutesLate = nowMinutes - (d.minutes_of_day + d.late_after_minutes);
    let status;
    if (match) status = 'given';
    else if (nowMinutes < d.minutes_of_day) status = 'upcoming';
    else if (minutesLate <= 0) status = 'due_now';
    else status = 'late';
    return {
      order_id: order.id,
      medication: order.name || '',
      resident_id: order.resident_id || null,
      high_priority: !!order.high_priority,
      controlled_substance: !!order.controlled_substance,
      scheduled_time: d.time,
      due_at: d.due_at,
      status: status,
      minutes_late: status === 'late' ? minutesLate : 0,
      recorded_administration_id: match ? match.id : null
    };
  });
  return {
    ok: true, schedulable: true, order_id: order.id, day: dayStr,
    source: doses.source, findings: findings,
    late_count: findings.filter((f) => f.status === 'late').length
  };
}

// Roll a whole facility's orders up into the alert set for one moment.
// Returns ONLY real findings computed from real records -- there is no
// "estimated" or "projected" anything here.
function facilityAlerts(opts) {
  opts = opts || {};
  const orders = opts.orders || [];
  const results = [];
  const unschedulable = [];
  orders.forEach((o) => {
    const r = evaluateDay({
      order: o, day: opts.day, now_minutes_of_day: opts.now_minutes_of_day,
      grace_minutes: opts.grace_minutes, administrations: opts.administrations
    });
    if (!r.ok) {
      // Surfaced, not swallowed: an order nobody can schedule is itself a
      // finding a DON needs to see, and it is the single most likely way this
      // feature would silently under-report.
      unschedulable.push({ order_id: r.order_id, medication: o.name || '', resident_id: o.resident_id || null, reason: r.reason });
      return;
    }
    r.findings.forEach((f) => results.push(f));
  });
  const late = results.filter((f) => f.status === 'late');
  return {
    ok: true,
    day: opts.day,
    late: late,
    due_now: results.filter((f) => f.status === 'due_now'),
    upcoming: results.filter((f) => f.status === 'upcoming'),
    given: results.filter((f) => f.status === 'given'),
    unschedulable: unschedulable,
    coverage: {
      have: orders.length - unschedulable.length,
      need: orders.length,
      note: unschedulable.length
        ? unschedulable.length + ' of ' + orders.length + ' active orders cannot be tracked for lateness because they have no explicit clock times.'
        : null
    }
  };
}

module.exports = {
  isValidTime,
  parseScheduleText,
  scheduleTimesFor,
  minutesOfDay,
  dosesForDay,
  evaluateDay,
  facilityAlerts
};
