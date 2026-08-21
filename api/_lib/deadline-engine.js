// api/_lib/deadline-engine.js
// ---------------------------------------------------------------------------
// SAIRNlaw deadline computation. PURE -- no I/O, no fetch, no Supabase. Rules
// and holiday calendars are passed in; this module only computes. That is
// deliberate: a date computation in a legal product has to be testable against
// worked examples from the rule text without standing up a database.
//
// A wrong deadline here is malpractice exposure, not a bug. Every behaviour
// below traces to rule text that was read directly and is cited at the point
// it is implemented.
//
// ── WHAT VERIFICATION CHANGED, versus what an implementation from memory
//    would have produced ────────────────────────────────────────────────────
//
// 1. FRCP periods are CALENDAR days, not business days. Rule 6(a)(1)(B) says
//    to "count every day, including intermediate Saturdays, Sundays, and legal
//    holidays." Only the LAST day gets special treatment. Implementing FRCP as
//    business days is the classic error and it errs LATER than reality, which
//    is the dangerous direction.
//
// 2. The pre-2009 regime, under which periods shorter than 11 days EXCLUDED
//    intermediate weekends, is OBSOLETE. The 2009 amendment unified
//    computation so all day-periods count identically regardless of length.
//    Any implementation copied from an older form book is wrong here, and
//    would be wrong specifically on short deadlines, which are the urgent ones.
//
// 3. Rule 6(a)(6)'s "legal holiday" is DIRECTION-DEPENDENT. Federal holidays
//    and days declared by the President or Congress always count; a holiday
//    declared by the state where the district court sits counts only for
//    FORWARD-counted periods. A flat holiday array silently gets backward
//    counting wrong.
//
// 4. Rule 6(d)'s three added days produce a SECOND rollover. Verified against
//    the 2005 Advisory Committee Note, which states: "Three days are added
//    after the prescribed period otherwise expires under Rule 6(a).
//    Intermediate Saturdays, Sundays, and legal holidays are included in
//    counting these added three days. If the third day is a Saturday, Sunday,
//    or legal holiday, the last day to act is the next day that is not a
//    Saturday, Sunday, or legal holiday." So the order is: 6(a) period ->
//    roll -> +3 calendar days -> roll again. This was flagged as unverified
//    at design time and is now confirmed rather than assumed.
// ---------------------------------------------------------------------------

// ── Date primitives ───────────────────────────────────────────────────────
// Everything is an ISO 'YYYY-MM-DD' string handled in UTC. Local-time Date
// arithmetic is how off-by-one date bugs happen (this platform has already
// had one -- see the sairn_fdate_utc_bug entry), and a date that is off by one
// day here is a missed filing.
function toUTC(iso) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(iso || ''))) return null;
  var d = new Date(iso + 'T00:00:00Z');
  return isNaN(d.getTime()) ? null : d;
}
function fromUTC(d) { return d.toISOString().slice(0, 10); }
function addDays(iso, n) {
  var d = toUTC(iso);
  if (!d) return null;
  d.setUTCDate(d.getUTCDate() + n);
  return fromUTC(d);
}
function dayOfWeek(iso) { var d = toUTC(iso); return d ? d.getUTCDay() : null; } // 0=Sun 6=Sat
function isWeekend(iso) { var w = dayOfWeek(iso); return w === 0 || w === 6; }

// Anniversary arithmetic for months/years, with end-of-month clamping. Adding
// one month to 31 January yields 28/29 February, not 3 March -- the naive
// Date.setUTCMonth rolls over and would silently overshoot.
function addMonths(iso, n) {
  var d = toUTC(iso);
  if (!d) return null;
  var day = d.getUTCDate();
  d.setUTCDate(1);
  d.setUTCMonth(d.getUTCMonth() + n);
  var last = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0)).getUTCDate();
  d.setUTCDate(Math.min(day, last));
  return fromUTC(d);
}

// ── Holiday resolution ────────────────────────────────────────────────────
// calendars: { 'us-federal': { 2026: [{date,name,kind}, ...] } }
// `kind` is 'federal' | 'declared' | 'state'. Per FRCP 6(a)(6), the 'state'
// kind counts only when counting FORWARD.
function holidayFor(calendars, jurisdiction, iso, direction) {
  var byYear = calendars && calendars[jurisdiction];
  if (!byYear) return { known: false };
  var year = iso.slice(0, 4);
  var list = byYear[year] || byYear[Number(year)];
  if (!list) return { known: false, missingYear: year };
  for (var i = 0; i < list.length; i++) {
    if (list[i].date !== iso) continue;
    if (list[i].kind === 'state' && direction !== 'forward') continue; // 6(a)(6)
    return { known: true, hit: list[i] };
  }
  return { known: true, hit: null };
}

// Rolls a landing date off a Saturday, Sunday or legal holiday. Forward
// periods roll forward; backward periods roll backward (Rule 6(a)(5)).
// Returns a refusal if a year's calendar is missing rather than treating an
// unknown year as holiday-free -- that would silently skip New Year's Day.
function rollOff(iso, calendars, jurisdiction, direction) {
  var step = direction === 'backward' ? -1 : 1;
  var cur = iso;
  for (var guard = 0; guard < 30; guard++) {
    var h = holidayFor(calendars, jurisdiction, cur, direction);
    if (!h.known) {
      return { ok: false, code: 'NOT_PROVISIONED',
        message: 'No holiday calendar is loaded for ' + jurisdiction +
          (h.missingYear ? ' for ' + h.missingYear : '') +
          '. The deadline is not computed rather than computed against an incomplete calendar.',
        missing: { jurisdiction: jurisdiction, year: h.missingYear || null } };
    }
    if (!isWeekend(cur) && !h.hit) return { ok: true, date: cur };
    cur = addDays(cur, step);
  }
  return { ok: false, code: 'ROLL_RUNAWAY', message: 'Could not find a non-holiday day within 30 days.' };
}

// ── Computation standards ─────────────────────────────────────────────────
// Named and versioned. FRAP 26(a) mirrors FRCP 6(a), so it maps to the SAME
// implementation rather than a second copy that could drift.
var COMPUTATION_STANDARDS = {
  frcp_6a: { label: 'Fed. R. Civ. P. 6(a)', impl: 'frcp_6a' },
  frap_26a: { label: 'Fed. R. App. P. 26(a)', impl: 'frcp_6a' },
  bankr_9006a: { label: 'Fed. R. Bankr. P. 9006(a)', impl: 'frcp_6a' }
};

var SERVICE_METHODS_EXTENDING = { mail: true, left_with_clerk: true, other_consented_means: true };

// ── The engine ────────────────────────────────────────────────────────────
// input: {
//   trigger_date, trigger_event, jurisdiction, domain,
//   service_method (optional), rules[], calendars{}
// }
function computeDeadline(input) {
  input = input || {};
  var triggerDate = input.trigger_date;
  if (!toUTC(triggerDate)) {
    return { ok: false, code: 'BAD_TRIGGER_DATE', message: 'A trigger date in YYYY-MM-DD form is required. Nothing is computed from today’s date.' };
  }
  if (!input.trigger_event) {
    return { ok: false, code: 'NO_TRIGGER_EVENT', message: 'A trigger event is required. The engine never infers what started the clock.' };
  }

  var all = input.rules || [];
  var inJurisdiction = all.filter(function (r) { return r.jurisdiction === input.jurisdiction; });
  if (!inJurisdiction.length) {
    return { ok: false, code: 'NOT_PROVISIONED',
      message: 'No deadline rules are loaded for ' + input.jurisdiction + '. No date is produced.',
      missing: { jurisdiction: input.jurisdiction } };
  }
  var inDomain = inJurisdiction.filter(function (r) { return r.domain === input.domain; });
  if (!inDomain.length) {
    return { ok: false, code: 'NOT_PROVISIONED',
      message: 'No rules are loaded for ' + input.domain + ' in ' + input.jurisdiction + '.',
      missing: { jurisdiction: input.jurisdiction, domain: input.domain },
      domains_available: inJurisdiction.map(function (r) { return r.domain; }).filter(function (v, i, a) { return a.indexOf(v) === i; }) };
  }

  var matching = inDomain.filter(function (r) { return r.trigger_event === input.trigger_event; });
  if (!matching.length) {
    return { ok: false, code: 'NO_MATCHING_RULE',
      message: 'No rule covers the trigger event "' + input.trigger_event + '".',
      triggers_available: inDomain.map(function (r) { return r.trigger_event; }).filter(function (v, i, a) { return a.indexOf(v) === i; }) };
  }

  // Effective-window selection: the rule as it stood at the TRIGGER date, not
  // as it stands today. This is the whole reason rules are versioned data.
  var inForce = matching.filter(function (r) {
    var from = r.effective_from || '0000-01-01';
    var to = r.effective_to || '9999-12-31';
    return triggerDate >= from && triggerDate <= to;
  });
  if (!inForce.length) {
    return { ok: false, code: 'NO_RULE_IN_FORCE',
      message: 'A rule exists for this trigger but none was in force on ' + triggerDate + '.',
      windows: matching.map(function (r) { return { rule_id: r.rule_id, effective_from: r.effective_from, effective_to: r.effective_to }; }) };
  }
  if (inForce.length > 1) {
    // Ambiguity is refused, never resolved by picking one. Overlapping
    // effective windows are a data defect that a human must fix.
    return { ok: false, code: 'AMBIGUOUS_RULE',
      message: inForce.length + ' rules were in force on ' + triggerDate + ' for this trigger. Overlapping effective windows must be corrected before a date can be computed.',
      rule_ids: inForce.map(function (r) { return r.rule_id; }) };
  }

  var rule = inForce[0];
  var std = COMPUTATION_STANDARDS[rule.computation];
  if (!std) {
    return { ok: false, code: 'UNKNOWN_STANDARD',
      message: 'Rule ' + rule.rule_id + ' names computation standard "' + rule.computation + '", which this engine does not implement.' };
  }

  var count = rule.count || {};
  var direction = count.direction === 'backward' ? 'backward' : 'forward';
  var sign = direction === 'backward' ? -1 : 1;
  var steps = [];

  // Rule 6(a)(1)(A): exclude the day of the triggering event.
  // Rule 6(a)(1)(B): count every intermediate day, weekends and holidays
  // included. So for calendar days this is plain arithmetic from the trigger.
  var base;
  if (count.unit === 'calendar_days') {
    base = addDays(triggerDate, sign * Number(count.value));
    steps.push({ step: 'base_period', detail: 'Excluded the trigger day and counted ' + count.value + ' calendar days ' + direction + ', including intermediate weekends and holidays.', authority: std.label + '(1)(A)-(B)', date: base });
  } else if (count.unit === 'months' || count.unit === 'years') {
    base = addMonths(triggerDate, sign * Number(count.value) * (count.unit === 'years' ? 12 : 1));
    steps.push({ step: 'base_period', detail: 'Counted ' + count.value + ' ' + count.unit + ' ' + direction + ' by anniversary date, clamped to end of month.', authority: std.label + '(1)(C)', date: base });
  } else if (count.unit === 'business_days') {
    // Supported because other jurisdictions really do count this way. It is
    // NOT how the FRCP counts, and no FRCP rule may use it.
    base = triggerDate;
    var remaining = Number(count.value);
    var guard = 0;
    while (remaining > 0 && guard++ < 400) {
      base = addDays(base, sign);
      var hb = holidayFor(input.calendars, input.jurisdiction, base, direction);
      if (!hb.known) {
        return { ok: false, code: 'NOT_PROVISIONED',
          message: 'No holiday calendar is loaded for ' + input.jurisdiction + (hb.missingYear ? ' for ' + hb.missingYear : '') + ', which business-day counting requires.',
          missing: { jurisdiction: input.jurisdiction, year: hb.missingYear || null } };
      }
      if (!isWeekend(base) && !hb.hit) remaining--;
    }
    steps.push({ step: 'base_period', detail: 'Counted ' + count.value + ' business days ' + direction + ', skipping weekends and holidays.', date: base });
  } else {
    return { ok: false, code: 'UNKNOWN_UNIT', message: 'Rule ' + rule.rule_id + ' uses unit "' + count.unit + '", which this engine does not implement.' };
  }

  // Rule 6(a)(1)(C) / 6(a)(5): roll the LAST day only.
  var rolled = rollOff(base, input.calendars, input.jurisdiction, direction);
  if (!rolled.ok) return rolled;
  if (rolled.date !== base) {
    steps.push({ step: 'rollover', detail: 'The last day fell on a Saturday, Sunday or legal holiday, so the period runs to the next day that is not.', authority: std.label + (direction === 'backward' ? '(5)' : '(1)(C)'), date: rolled.date });
  }
  var result = rolled.date;

  // Rule 6(d): +3 days for certain service methods, then roll AGAIN.
  // Order verified against the 2005 Advisory Committee Note (quoted in this
  // file's header), not assumed.
  var extensionApplied = false;
  if (input.service_method && rule.service_extension) {
    var ext = rule.service_extension;
    var qualifies = (ext.applies_when || []).indexOf(input.service_method) !== -1 &&
      SERVICE_METHODS_EXTENDING[input.service_method] === true;
    if (qualifies) {
      var extended = addDays(result, sign * Number(ext.add));
      steps.push({ step: 'service_extension', detail: ext.add + ' days added because service was by ' + input.service_method.replace(/_/g, ' ') + ', counted after the base period expired and including intermediate weekends and holidays.', authority: ext.standard === 'frcp_6d' ? 'Fed. R. Civ. P. 6(d)' : ext.standard, date: extended });
      var rolled2 = rollOff(extended, input.calendars, input.jurisdiction, direction);
      if (!rolled2.ok) return rolled2;
      if (rolled2.date !== extended) {
        steps.push({ step: 'rollover_after_extension', detail: 'The third added day fell on a Saturday, Sunday or legal holiday, so the last day to act is the next day that is not.', authority: 'Fed. R. Civ. P. 6(d), 2005 Advisory Committee Note', date: rolled2.date });
      }
      result = rolled2.date;
      extensionApplied = true;
    }
  }

  return {
    ok: true,
    due_date: result,
    trigger_date: triggerDate,
    trigger_event: input.trigger_event,
    service_extension_applied: extensionApplied,
    rule: {
      rule_id: rule.rule_id,
      label: rule.label,
      computation: rule.computation,
      computation_label: std.label,
      authority: rule.authority,
      effective_from: rule.effective_from,
      effective_to: rule.effective_to,
      version: rule.version
    },
    // The audit trail is part of the product, not a debug aid: an attorney has
    // to be able to see how the date was reached and follow it to the rule.
    steps: steps
  };
}

module.exports = {
  toUTC, fromUTC, addDays, addMonths, dayOfWeek, isWeekend,
  holidayFor, rollOff, computeDeadline,
  COMPUTATION_STANDARDS, SERVICE_METHODS_EXTENDING
};
