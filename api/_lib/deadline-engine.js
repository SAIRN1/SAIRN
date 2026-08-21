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

// Counts n days forward/backward, skipping intermediate weekends and legal
// holidays entirely (the day skipped does not count toward n). NEW,
// ADDITIVE -- does not replace or alter the existing business_days loop
// below, which is already tested; this is a separate call site so neither
// can regress the other. Used by Ohio's Civ.R. 6(A) short-period exclusion,
// and shaped identically to the business_days loop because both rules mean
// the same thing: skip non-business days while counting.
function countExcludingWeekendsAndHolidays(triggerDate, sign, n, calendars, jurisdiction, direction) {
  var cur = triggerDate;
  var remaining = n;
  var guard = 0;
  while (remaining > 0 && guard++ < 400) {
    cur = addDays(cur, sign);
    var h = holidayFor(calendars, jurisdiction, cur, direction);
    if (!h.known) {
      return { ok: false, code: 'NOT_PROVISIONED',
        message: 'No holiday calendar is loaded for ' + jurisdiction + (h.missingYear ? ' for ' + h.missingYear : '') + ', which this short-period computation requires.',
        missing: { jurisdiction: jurisdiction, year: h.missingYear || null } };
    }
    if (!isWeekend(cur) && !h.hit) remaining--;
  }
  return { ok: true, date: cur };
}

// ── Computation standards ─────────────────────────────────────────────────
// Named and versioned. FRAP 26(a) mirrors FRCP 6(a), so it maps to the SAME
// implementation rather than a second copy that could drift.
//
// Ohio Civ.R. 6(A) is NOT a copy of FRCP 6(a) and gets its own impl rather
// than being mapped onto frcp_6a, because one real mechanism differs: Ohio
// never adopted the federal 2009 amendment that unified day-counting for all
// period lengths. Civ.R. 6(A), verified directly (not assumed to have
// followed the federal 2009 change): "When the period of time prescribed or
// allowed is less than seven days, intermediate Saturdays, Sundays, and legal
// holidays shall be excluded in the computation." Periods of 7 days or more
// count every intermediate day exactly like FRCP 6(a) does. Encoding this as
// frcp_6a would silently drop the short-period exclusion and produce a date
// LATER than the true Ohio deadline on every Ohio period under 7 days --
// the dangerous direction.
var COMPUTATION_STANDARDS = {
  frcp_6a: { label: 'Fed. R. Civ. P. 6(a)', impl: 'frcp_6a' },
  frap_26a: { label: 'Fed. R. App. P. 26(a)', impl: 'frcp_6a' },
  bankr_9006a: { label: 'Fed. R. Bankr. P. 9006(a)', impl: 'frcp_6a' },
  ohio_civ_r_6a: { label: 'Ohio Civ.R. 6(A)', impl: 'ohio_civ_r_6a', short_period_exclusion_days: 7 }
};

// ── Service-extension standards (Phase 2, Gap 3) ──────────────────────────
// PREVIOUSLY A SINGLE GLOBAL ALLOWLIST, which was a latent defect: it held
// only the FRCP three and gated EVERY rule against them, so a FRAP rule whose
// own applies_when named a non-electronic method got no extension and reported
// service_extension_applied:false -- indistinguishable from "no extension was
// requested". It failed safe (an earlier date) but silently, which is the part
// that made it a defect rather than a conservative default.
//
// The two standards are not the same SHAPE, and that is why one allowlist
// could never serve both:
//   FRCP 6(d)  -- an ENUMERATED allowlist: mail, left with the clerk, other
//                 consented means.
//   FRAP 26(c) -- a NEGATIVE condition: 3 days are added when a paper is NOT
//                 served electronically. Electronic service is the exclusion,
//                 not the inclusion.
// Encoding the second as a list of "everything except electronic" would be a
// guess at the membership of that set. Each standard therefore carries its own
// predicate, and a rule naming a standard this engine does not implement is
// REFUSED VISIBLY rather than silently not extended.
var SERVICE_EXTENSION_STANDARDS = {
  frcp_6d: {
    label: 'Fed. R. Civ. P. 6(d)',
    shape: 'enumerated_allowlist',
    qualifies: function (method) {
      return method === 'mail' || method === 'left_with_clerk' || method === 'other_consented_means';
    }
  },
  frap_26c: {
    label: 'Fed. R. App. P. 26(c)',
    shape: 'negative_condition',
    qualifies: function (method) {
      // "3 days are added after the period would otherwise expire" when the
      // paper is NOT served electronically. Anything explicitly electronic is
      // excluded; an unstated method cannot be assumed non-electronic.
      if (!method) return false;
      return method !== 'electronic' && method !== 'electronic_service';
    }
  }
};

// Retained as a read-only description of the FRCP set for callers and tests.
// NO LONGER used as a gate -- gating is per-standard above.
var SERVICE_METHODS_EXTENDING = { mail: true, left_with_clerk: true, other_consented_means: true };

// ── Multi-trigger resolution (Phase 2, Gap 1) ─────────────────────────────
// Some periods run from "the later of" two events -- FRAP 4(b)(1)(A) (14 days
// after the later of entry of judgment or the government's notice of appeal)
// and FRCP 12(a)(3) (60 days after service on the officer or on the US
// attorney, whichever is later) are the two this unlocks.
//
// REFUSES ON PARTIAL INPUT, deliberately. If only one of the named events has
// a date, the engine does NOT quietly fall back to single-trigger behaviour --
// that is precisely how such a rule computes a date that is too early roughly
// half the time, and too early is the direction that loses a right.
function resolveTrigger(rule, input) {
  var spec = rule.trigger_event;

  // Single-trigger rules: unchanged behaviour.
  if (typeof spec === 'string') {
    if (!toUTC(input.trigger_date)) {
      return { ok: false, code: 'BAD_TRIGGER_DATE', message: 'A trigger date in YYYY-MM-DD form is required.' };
    }
    return { ok: true, date: input.trigger_date, resolution: null };
  }

  if (!spec || !spec.resolve || !Array.isArray(spec.events) || spec.events.length < 2) {
    return { ok: false, code: 'BAD_RULE_TRIGGER', message: 'Rule ' + rule.rule_id + ' has a malformed multi-trigger specification.' };
  }
  if (spec.resolve !== 'later_of' && spec.resolve !== 'earlier_of') {
    return { ok: false, code: 'BAD_RULE_TRIGGER', message: 'Rule ' + rule.rule_id + ' uses resolve "' + spec.resolve + '"; only later_of and earlier_of are implemented.' };
  }

  var supplied = input.trigger_dates || {};
  var missing = spec.events.filter(function (e) { return !toUTC(supplied[e]); });
  if (missing.length) {
    return {
      ok: false, code: 'INCOMPLETE_TRIGGERS',
      message: 'This rule runs from the ' + spec.resolve.replace('_', ' ') + ' ' + spec.events.length +
        ' events, and ' + missing.length + ' of them has no date recorded. No deadline is computed from a partial set — ' +
        'resolving it from the events supplied would produce a date that is ' +
        (spec.resolve === 'later_of' ? 'too early' : 'too late') + ' whenever the missing event governs.',
      required_events: spec.events, missing_events: missing
    };
  }

  var dates = spec.events.map(function (e) { return supplied[e]; }).sort();
  var chosen = spec.resolve === 'later_of' ? dates[dates.length - 1] : dates[0];
  var governing = spec.events.filter(function (e) { return supplied[e] === chosen; });
  return {
    ok: true, date: chosen,
    resolution: { resolve: spec.resolve, events: spec.events, supplied: supplied, governing_event: governing[0] }
  };
}

// ── Trigger substitution (Phase 2, Gap 2) ─────────────────────────────────
// FRAP 4(a)(4)(A): a qualifying post-judgment motion does NOT extend the
// appeal period. It REPLACES the trigger -- "the time to file an appeal runs
// for all parties from the entry of the order disposing of the last such
// remaining motion."
//
// This function returns a NEW TRIGGER DATE and never a number of days, so the
// distinction is enforced by the type it returns rather than by a comment. A
// future maintainer cannot accidentally route this through the extension path,
// because the extension path consumes a day count and this produces a date.
//
// REFUSES when a qualifying motion is recorded as pending but undisposed: the
// period genuinely has not begun, and any date would be invented.
function applyRetrigger(rule, currentTriggerDate, input) {
  var spec = rule.retrigger;
  if (!spec) return { ok: true, date: currentTriggerDate, retriggered: false };

  var events = input.retrigger_events || [];
  var qualifying = events.filter(function (e) {
    return (spec.on_events || []).indexOf(e.event) !== -1;
  });
  if (!qualifying.length) return { ok: true, date: currentTriggerDate, retriggered: false };

  var undisposed = qualifying.filter(function (e) { return !toUTC(e.disposition_date); });
  if (undisposed.length) {
    return {
      ok: false, code: 'MOTION_PENDING',
      message: undisposed.length + ' qualifying motion' + (undisposed.length === 1 ? ' is' : 's are') +
        ' recorded as pending with no disposition date. Under this rule the period runs from the disposition of the last such motion, so it has not started yet — no date is computed rather than one being estimated.',
      pending: undisposed.map(function (e) { return e.event; }),
      authority: spec.authority || null
    };
  }

  // "the last such remaining motion" -- the latest disposition governs.
  var dispositions = qualifying.map(function (e) { return e.disposition_date; }).sort();
  var last = dispositions[dispositions.length - 1];
  return {
    ok: true, date: last, retriggered: true,
    replaced: currentTriggerDate,
    substitute_trigger: spec.substitute_trigger || 'disposition_of_last_qualifying_motion',
    motions: qualifying.map(function (e) { return e.event; }),
    authority: spec.authority || null
  };
}

// ── The engine ────────────────────────────────────────────────────────────
// input: {
//   trigger_date, trigger_event, jurisdiction, domain,
//   service_method (optional), rules[], calendars{}
// }
function computeDeadline(input) {
  input = input || {};
  // A trigger DATE is validated later, per-rule, because a multi-trigger rule
  // takes its dates from trigger_dates rather than trigger_date. What is
  // required unconditionally is knowing WHICH event started the clock -- the
  // engine never infers that, and never falls back to today.
  if (!input.trigger_event) {
    return { ok: false, code: 'NO_TRIGGER_EVENT', message: 'A trigger event is required. The engine never infers what started the clock.' };
  }
  if (!toUTC(input.trigger_date) && !input.trigger_dates) {
    return { ok: false, code: 'BAD_TRIGGER_DATE', message: 'A trigger date in YYYY-MM-DD form is required (or trigger_dates for a multi-trigger rule). Nothing is computed from today’s date.' };
  }
  var triggerDate = input.trigger_date;

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

  // A rule's trigger_event is either a string, or a multi-trigger spec whose
  // events[] the caller names instead. Both are matched here so a caller does
  // not need to know which shape a rule uses before asking for it.
  var matching = inDomain.filter(function (r) {
    if (typeof r.trigger_event === 'string') return r.trigger_event === input.trigger_event;
    if (r.trigger_event && Array.isArray(r.trigger_event.events)) {
      return r.trigger_event.events.indexOf(input.trigger_event) !== -1 ||
        r.trigger_event.id === input.trigger_event;
    }
    return false;
  });
  if (!matching.length) {
    return { ok: false, code: 'NO_MATCHING_RULE',
      message: 'No rule covers the trigger event "' + input.trigger_event + '".',
      triggers_available: inDomain.reduce(function (acc, r) {
        if (typeof r.trigger_event === 'string') { if (acc.indexOf(r.trigger_event) === -1) acc.push(r.trigger_event); }
        else if (r.trigger_event && Array.isArray(r.trigger_event.events)) {
          r.trigger_event.events.forEach(function (e) { if (acc.indexOf(e) === -1) acc.push(e); });
        }
        return acc;
      }, []) };
  }

  // Resolve each candidate's trigger date BEFORE the effective-window filter,
  // because a multi-trigger or retriggered rule may resolve to a different
  // date than the one supplied, and the window must be tested against the date
  // the period actually runs from.
  var resolvedByRule = {};
  for (var ri = 0; ri < matching.length; ri++) {
    var rr = matching[ri];
    var res = resolveTrigger(rr, input);
    if (!res.ok) return res;
    var ret = applyRetrigger(rr, res.date, input);
    if (!ret.ok) return ret;
    resolvedByRule[rr.rule_id] = { date: ret.date, resolution: res.resolution, retrigger: ret.retriggered ? ret : null };
  }

  // Effective-window selection: the rule as it stood at the TRIGGER date, not
  // as it stands today. This is the whole reason rules are versioned data.
  var inForce = matching.filter(function (r) {
    var from = r.effective_from || '0000-01-01';
    var to = r.effective_to || '9999-12-31';
    var d = resolvedByRule[r.rule_id].date;
    return d >= from && d <= to;
  });
  if (!inForce.length) {
    return { ok: false, code: 'NO_RULE_IN_FORCE',
      message: 'A rule exists for this trigger but none was in force on the date the period runs from.',
      windows: matching.map(function (r) { return { rule_id: r.rule_id, effective_from: r.effective_from, effective_to: r.effective_to }; }) };
  }
  if (inForce.length > 1) {
    // Ambiguity is refused, never resolved by picking one. Overlapping
    // effective windows are a data defect that a human must fix.
    return { ok: false, code: 'AMBIGUOUS_RULE',
      message: inForce.length + ' rules were in force for this trigger on the date the period runs from. Overlapping effective windows must be corrected before a date can be computed.',
      rule_ids: inForce.map(function (r) { return r.rule_id; }) };
  }

  var rule = inForce[0];
  var resolved = resolvedByRule[rule.rule_id];
  // From here on, triggerDate is the date the period ACTUALLY runs from --
  // after multi-trigger resolution and after any trigger substitution.
  triggerDate = resolved.date;
  var std = COMPUTATION_STANDARDS[rule.computation];
  if (!std) {
    return { ok: false, code: 'UNKNOWN_STANDARD',
      message: 'Rule ' + rule.rule_id + ' names computation standard "' + rule.computation + '", which this engine does not implement.' };
  }

  var count = rule.count || {};
  var direction = count.direction === 'backward' ? 'backward' : 'forward';
  var sign = direction === 'backward' ? -1 : 1;
  var steps = [];

  // Both of these are recorded BEFORE the base period, because each changed
  // what the base period counts from. They are separate step kinds from
  // 'service_extension' on purpose -- one moves the start, the other adds to
  // the end, and conflating them in the audit trail would misdescribe the law.
  if (resolved.resolution) {
    steps.push({
      step: 'multi_trigger_resolution',
      detail: 'This period runs from the ' + resolved.resolution.resolve.replace('_', ' ') + ' ' +
        resolved.resolution.events.length + ' events. ' + resolved.resolution.governing_event +
        ' governs, on ' + resolved.date + '.',
      authority: rule.authority ? rule.authority.citation : null,
      date: resolved.date
    });
  }
  if (resolved.retrigger) {
    steps.push({
      step: 'trigger_substitution',
      detail: 'A qualifying motion (' + resolved.retrigger.motions.join(', ') + ') replaced the original trigger of ' +
        resolved.retrigger.replaced + '. The period runs from the disposition of the last such motion, not from the original event, and no days are added.',
      authority: resolved.retrigger.authority || (rule.authority ? rule.authority.citation : null),
      date: resolved.date
    });
  }

  // Rule 6(a)(1)(A): exclude the day of the triggering event.
  // Rule 6(a)(1)(B): count every intermediate day, weekends and holidays
  // included. So for calendar days this is plain arithmetic from the trigger.
  var base;
  if (count.unit === 'calendar_days') {
    // Ohio Civ.R. 6(A): periods under 7 days exclude intermediate weekends
    // and legal holidays -- the pre-2009 federal mechanism that Ohio never
    // repealed. Gated on the STANDARD's impl, not on jurisdiction, so this
    // never silently fires for an FRCP-family rule.
    if (std.impl === 'ohio_civ_r_6a' && Number(count.value) < (std.short_period_exclusion_days || Infinity)) {
      var ohRes = countExcludingWeekendsAndHolidays(triggerDate, sign, Number(count.value), input.calendars, input.jurisdiction, direction);
      if (!ohRes.ok) return ohRes;
      base = ohRes.date;
      steps.push({ step: 'base_period', detail: 'Excluded the trigger day and counted ' + count.value + ' days ' + direction + ', excluding intermediate Saturdays, Sundays and legal holidays because the period is less than ' + std.short_period_exclusion_days + ' days.', authority: std.label, date: base });
    } else {
      base = addDays(triggerDate, sign * Number(count.value));
      steps.push({ step: 'base_period', detail: 'Excluded the trigger day and counted ' + count.value + ' calendar days ' + direction + ', including intermediate weekends and holidays.', authority: std.label + '(1)(A)-(B)', date: base });
    }
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
  // The four outcomes are now DISTINGUISHABLE. Previously all of them except
  // 'applied' collapsed to service_extension_applied:false, so a rule that
  // asked for an extension the engine could not evaluate looked identical to
  // a claim where none was requested. That silence was the defect.
  var extension = { state: 'not_requested', standard: null, days_added: 0, detail: 'No service method was supplied, so no service extension was considered.' };

  if (rule.service_extension) {
    var ext = rule.service_extension;
    var stdKey = ext.standard;
    var extStd = SERVICE_EXTENSION_STANDARDS[stdKey];
    var extLabel = extStd ? extStd.label : stdKey;

    if (!input.service_method) {
      extension = { state: 'not_requested', standard: stdKey, days_added: 0,
        detail: 'This rule can extend under ' + extLabel + ', but no service method was supplied, so no extension was applied.' };
    } else if (!extStd) {
      // REFUSED VISIBLY. The engine does not know this standard's condition,
      // so it will not guess -- and it says so rather than returning a date
      // that quietly omits an extension the rule may well require.
      extension = { state: 'refused_unknown_standard', standard: stdKey, days_added: 0,
        detail: 'This rule extends under "' + stdKey + '", which this engine does not implement. No extension was applied and the date below may therefore be EARLIER than the true deadline. Verify the extension by hand before relying on it.' };
      steps.push({ step: 'service_extension_refused',
        detail: 'Extension under "' + stdKey + '" could not be evaluated: the standard is not implemented. No days were added.',
        authority: null, date: result });
    } else if (!extStd.qualifies(input.service_method)) {
      extension = { state: 'not_qualifying', standard: stdKey, days_added: 0,
        detail: 'Service by ' + String(input.service_method).replace(/_/g, ' ') + ' does not qualify for an extension under ' + extLabel + ' (' + extStd.shape.replace(/_/g, ' ') + ').' };
    } else if ((ext.applies_when || []).length && (ext.applies_when || []).indexOf(input.service_method) === -1) {
      // The standard would extend, but THIS RULE's own applies_when does not
      // list the method. Reported distinctly from the standard declining it,
      // because the two mean different things: one is the law, one is this
      // row's data, and only the second is fixable by editing the rule.
      extension = { state: 'not_listed_by_rule', standard: stdKey, days_added: 0,
        detail: extLabel + ' would extend for service by ' + String(input.service_method).replace(/_/g, ' ') + ', but rule ' + rule.rule_id + ' does not list that method in applies_when. No extension was applied.' };
      steps.push({ step: 'service_extension_refused',
        detail: 'The standard permits an extension for this service method, but this rule does not list it. No days were added — check whether the rule row is incomplete.',
        authority: extLabel, date: result });
    } else {
      var extended = addDays(result, sign * Number(ext.add));
      steps.push({ step: 'service_extension', detail: ext.add + ' days added because service was by ' + String(input.service_method).replace(/_/g, ' ') + ', counted after the base period expired and including intermediate weekends and holidays.', authority: extLabel, date: extended });
      var rolled2 = rollOff(extended, input.calendars, input.jurisdiction, direction);
      if (!rolled2.ok) return rolled2;
      if (rolled2.date !== extended) {
        steps.push({ step: 'rollover_after_extension', detail: 'The added day fell on a Saturday, Sunday or legal holiday, so the last day to act is the next day that is not.', authority: extLabel + (stdKey === 'frcp_6d' ? ', 2005 Advisory Committee Note' : ''), date: rolled2.date });
      }
      result = rolled2.date;
      extension = { state: 'applied', standard: stdKey, days_added: Number(ext.add),
        detail: ext.add + ' days added under ' + extLabel + '.' };
    }
  } else if (input.service_method) {
    extension = { state: 'not_requested', standard: null, days_added: 0,
      detail: 'A service method was supplied, but this rule defines no service extension, so none applies.' };
  }

  return {
    ok: true,
    due_date: result,
    trigger_date: triggerDate,
    trigger_event: input.trigger_event,
    // Boolean retained for existing callers; `service_extension` carries the
    // state they need to distinguish a refusal from an absence.
    service_extension_applied: extension.state === 'applied',
    service_extension: extension,
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
  holidayFor, rollOff, countExcludingWeekendsAndHolidays, computeDeadline,
  resolveTrigger, applyRetrigger,
  COMPUTATION_STANDARDS, SERVICE_METHODS_EXTENDING, SERVICE_EXTENSION_STANDARDS
};
