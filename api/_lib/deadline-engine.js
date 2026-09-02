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

// WHICH DAYS ARE "THE WEEKEND" IS A PER-JURISDICTION FACT, NOT A CONSTANT.
// Every rule seeded to date names both weekend days -- "a Saturday, a Sunday,
// or a legal holiday" -- so [Sun, Sat] is the right default and every existing
// computation standard is unchanged by this parameter existing.
//
// LOUISIANA IS THE FIRST JURISDICTION WHERE THE ASSUMPTION IS AFFIRMATIVELY
// WRONG, which is why this became a parameter rather than staying a literal.
// La. C.C.P. art. 5059(A) rolls the last day only "unless it is a legal
// holiday" -- it never names Saturday or Sunday in its own right -- and
// La. R.S. 1:55(A)(1) makes SUNDAYS a statewide legal holiday while making
// "the whole of every Saturday" one ONLY in the parish of Orleans, the city of
// Baton Rouge, the parishes of the 2nd and 6th congressional districts except
// Ascension, and those of the 14th and 31st judicial districts. Everywhere
// else in the state a Saturday is an ordinary day, and rolling off it produces
// a date LATER than the true deadline -- the direction that misses a filing,
// and one a coverage disclosure cannot repair.
//
// A STANDARD DECLARING A MALFORMED weekend_days IS A HARD FAILURE, NOT A
// SILENT FALLBACK. Falling back to the default would restore exactly the
// behaviour a jurisdiction declared wrong, and it would do it invisibly. The
// check runs once at module load, below the standards table.
var DEFAULT_WEEKEND_DAYS = [0, 6]; // Sunday, Saturday
function isWeekend(iso, weekendDays) {
  var w = dayOfWeek(iso);
  if (w === null) return false;
  var set = Array.isArray(weekendDays) ? weekendDays : DEFAULT_WEEKEND_DAYS;
  return set.indexOf(w) !== -1;
}

// ── The trigger-document discriminator ───────────────────────────────────
// WHAT THIS EXISTS FOR. computeDeadline() counts from whatever date it is
// handed and has never asked what that date MEANS. For most rules the trigger
// is unambiguous -- a party was served, a motion was filed -- and the caller
// cannot get it wrong. For 48 seeded rows it is a TERM OF ART naming one
// specific document, and four states start the appeal clock four different
// ways: Texas from the SIGNING of the judgment, Florida from its RENDITION,
// six jurisdictions from its ENTRY on the docket, New York from SERVICE of a
// copy with written notice of entry. West Virginia uses two different
// documents within one state -- R. App. P. 5(b) runs from the final order OR
// the mandate, 5(f) from the judgment.
//
// A CALLER CONFLATING THEM GETS A WRONG DATE AND NO REFUSAL, AND THE TWO
// CLASSES FAIL IN OPPOSITE DIRECTIONS. Supplying an EARLIER document's date
// than the rule means reports EARLY, which is safe. Supplying a LATER one --
// the docket-entry date where the rule means the signing date, say -- reports
// LATE. Thirty-one of the forty-eight are APPELLATE, where a late notice of
// appeal is jurisdictional and not curable, so this platform's standing rule
// since Kentucky applies: a gap that can report LATE refuses rather than
// discloses.
//
// SO THE ROW DECLARES ITS DOCUMENT AND THE CALLER MUST AFFIRM IT. Prose in a
// seed note was rejected as the fix -- it was already there, and it is
// invisible at the point the date is read, which is the same reason
// JURISDICTION_COVERAGE exists rather than a comment.
//
//   trigger_document: {
//     id:             matched against input.trigger_document
//     label:          what the date must BE, in an attorney's words
//     not_the:        what it must NOT be -- the conflation being guarded
//     authority:      the rule that makes it a term of art
//     on_unconfirmed: 'refuse' | 'warn'
//   }
//
// 'refuse' for the appellate class, 'warn' for the civil one. It is declared
// PER ROW rather than derived from the domain on purpose: a default computed
// from another field is exactly the kind of invisible rule this change exists
// to remove, and one day a civil row will need to refuse.
//
// A MALFORMED DECLARATION REFUSES rather than degrading to 'warn'. This is
// in-code data, so a defect is a bug, and the safe direction for a bug in the
// guard is to withhold the date.
var TRIGGER_DOCUMENT_KEYS = ['id', 'label', 'not_the', 'authority', 'on_unconfirmed'];
function triggerDocumentDefects(td) {
  var bad = [];
  if (td === undefined || td === null) return bad;
  if (typeof td !== 'object' || Array.isArray(td)) return ['must be an object'];
  TRIGGER_DOCUMENT_KEYS.forEach(function (k) {
    if (typeof td[k] !== 'string' || !td[k].trim()) bad.push('missing or empty ' + k);
  });
  if (td.on_unconfirmed !== undefined
      && td.on_unconfirmed !== 'refuse' && td.on_unconfirmed !== 'warn') {
    bad.push('on_unconfirmed is ' + JSON.stringify(td.on_unconfirmed) + ', expected "refuse" or "warn"');
  }
  return bad;
}

// Returns null when the rule declares no document, or a resolution object the
// caller can act on. Pure: it decides, it does not compute.
function resolveTriggerDocument(rule, input) {
  var td = rule.trigger_document;
  if (!td) return null;
  var defects = triggerDocumentDefects(td);
  if (defects.length) {
    return { ok: false, code: 'INVALID_TRIGGER_DOCUMENT',
      message: 'Rule ' + rule.rule_id + ' declares a malformed trigger_document (' + defects.join('; ') +
        '). The date is withheld rather than computed from an unchecked trigger.' };
  }
  var supplied = input && input.trigger_document;
  if (supplied && supplied !== td.id) {
    // An affirmative WRONG answer is worse than silence, so this refuses
    // whatever on_unconfirmed says.
    return { ok: false, code: 'TRIGGER_DOCUMENT_MISMATCH',
      message: 'This rule runs from ' + td.label + ' (' + td.authority + '), and the date supplied was affirmed to be "' +
        supplied + '" instead. Those are different documents and they bear different dates. No deadline is computed.',
      expected: td.id, supplied: supplied, label: td.label, not_the: td.not_the, authority: td.authority };
  }
  if (!supplied) {
    if (td.on_unconfirmed === 'refuse') {
      return { ok: false, code: 'TRIGGER_DOCUMENT_UNCONFIRMED',
        message: 'This period runs from ' + td.label + ' (' + td.authority + '), which is NOT ' + td.not_the +
          '. Those documents bear different dates, and supplying the wrong one produces a deadline that is LATE -- ' +
          'on an appellate clock that is not curable. Confirm the date supplied is that document by sending ' +
          'trigger_document: "' + td.id + '". No date is guessed.',
        expected: td.id, label: td.label, not_the: td.not_the, authority: td.authority };
    }
    return { ok: true, state: 'unconfirmed', expected: td.id, label: td.label,
      not_the: td.not_the, authority: td.authority,
      detail: 'This period runs from ' + td.label + ' (' + td.authority + '), NOT ' + td.not_the +
        '. The caller did not confirm which document the date supplied came from. Both readings of this rule ' +
        'report EARLIER than the true deadline rather than later, so a date is returned -- but confirm it by ' +
        'sending trigger_document: "' + td.id + '" before relying on it.' };
  }
  return { ok: true, state: 'confirmed', expected: td.id, label: td.label,
    not_the: td.not_the, authority: td.authority,
    detail: 'The caller confirmed the date supplied is ' + td.label + ' (' + td.authority + ').' };
}

// ── The MULTI-SLOT form, for multi-trigger rules ─────────────────────────
// A rule whose trigger_event is a spec rather than a string has SEVERAL events,
// and only some of them name a document. Across the four seeded cross-appeal
// rows, four of the eight limbs are terms of art and four are not: the filing
// or service of a notice of appeal has one unambiguous date, and forcing a
// declaration on it would say "this is the date the notice was filed, not the
// date it was filed" -- noise that trains a reader to skim.
//
// So `trigger_documents` is a MAP keyed by the limb's own event name, and a
// limb with no entry is unguarded on purpose. The key is the vocabulary the
// caller already uses for trigger_dates and that rules_status already reports
// as requires_dates, so nothing new has to be learned to answer it.
//
// THE CALLER SENDS A MAP, NOT A LIST OF CONFIRMED EVENTS. A bare list can only
// say "I confirm" and never "I confirm it is THIS document", which would throw
// away the MISMATCH refusal. That is not theoretical here: Ohio App.R. 4(B)(1)
// runs its guarded limb from ENTRY of the final order and Tex. R. App. P.
// 26.1(d) runs its from SIGNING of the judgment, and a caller with both
// matters open can affirm the wrong one.
//
// REFUSAL IS ALL-OR-NOTHING. Every one of these rules resolves later_of, so an
// unverified limb can always be the limb that governs; returning the other
// limb's date would be returning an answer that is correct only if the
// unverified limb happens to lose, which cannot be known without using the
// unverified date.
function triggerDocumentsDefects(map) {
  if (map === undefined || map === null) return [];
  if (typeof map !== 'object' || Array.isArray(map)) return ['must be an object keyed by event name'];
  var keys = Object.keys(map);
  if (!keys.length) return ['must not be empty -- omit the field instead of declaring nothing'];
  var bad = [];
  keys.forEach(function (k) {
    var one = triggerDocumentDefects(map[k]);
    one.forEach(function (d) { bad.push(k + ': ' + d); });
    if (map[k] && map[k].id && map[k].id !== k) {
      // The key says WHICH LIMB and the id says WHICH DOCUMENT. They are the
      // same string on every current row, and a mismatch is far more likely to
      // be a copy-paste slip than a real distinction -- so it is refused
      // rather than silently honoured in one direction or the other.
      bad.push(k + ': id "' + map[k].id + '" does not match its key');
    }
  });
  return bad;
}

// Returns null when the rule declares none, a refusal, or a per-event map of
// resolutions. Pure: it decides, it does not compute.
function resolveTriggerDocuments(rule, input) {
  var map = rule.trigger_documents;
  if (!map) return null;
  var defects = triggerDocumentsDefects(map);
  if (defects.length) {
    return { ok: false, code: 'INVALID_TRIGGER_DOCUMENT',
      message: 'Rule ' + rule.rule_id + ' declares a malformed trigger_documents map (' + defects.join('; ') +
        '). The date is withheld rather than computed from unchecked triggers.' };
  }
  var supplied = (input && input.trigger_documents) || {};
  if (typeof supplied !== 'object' || Array.isArray(supplied)) {
    return { ok: false, code: 'INVALID_TRIGGER_DOCUMENT',
      message: 'trigger_documents must be an object mapping each guarded limb event to the document id being affirmed for it.' };
  }
  var out = {};
  var events = Object.keys(map);
  for (var i = 0; i < events.length; i++) {
    var ev = events[i], td = map[ev], got = supplied[ev];
    if (got && got !== td.id) {
      return { ok: false, code: 'TRIGGER_DOCUMENT_MISMATCH',
        message: 'The "' + ev + '" limb of this rule runs from ' + td.label + ' (' + td.authority +
          '), and the date supplied for it was affirmed to be "' + got + '" instead. Those are different ' +
          'documents and they bear different dates. No deadline is computed.',
        limb: ev, expected: td.id, supplied: got, label: td.label, not_the: td.not_the, authority: td.authority };
    }
    if (!got) {
      if (td.on_unconfirmed === 'refuse') {
        return { ok: false, code: 'TRIGGER_DOCUMENT_UNCONFIRMED',
          message: 'The "' + ev + '" limb of this rule runs from ' + td.label + ' (' + td.authority +
            '), which is NOT ' + td.not_the + '. This rule takes the LATER of its limbs, so an unverified ' +
            'limb can be the one that governs and no partial answer is safe. Confirm the date supplied for ' +
            'that limb by sending trigger_documents: {"' + ev + '": "' + td.id + '"}. No date is guessed.',
          limb: ev, expected: td.id, label: td.label, not_the: td.not_the, authority: td.authority };
      }
      out[ev] = { state: 'unconfirmed', expected: td.id, label: td.label, not_the: td.not_the,
        authority: td.authority,
        detail: 'The "' + ev + '" limb runs from ' + td.label + ' (' + td.authority + '), NOT ' + td.not_the +
          '. The caller did not confirm which document that date came from.' };
    } else {
      out[ev] = { state: 'confirmed', expected: td.id, label: td.label, not_the: td.not_the,
        authority: td.authority,
        detail: 'The caller confirmed the date supplied for the "' + ev + '" limb is ' + td.label +
          ' (' + td.authority + ').' };
    }
  }
  return { ok: true, limbs: out };
}

// Returns null if valid, or a string naming the defect. Exported so the
// load-time check and its test assert the SAME function rather than two
// implementations that can drift.
function weekendDaysDefect(v) {
  if (v === undefined || v === null) return null; // not declared -- the default applies
  if (!Array.isArray(v)) return 'must be an array of day numbers';
  if (!v.length) return 'must not be empty -- a jurisdiction with no weekend days declares [] nowhere; omit the property instead';
  for (var i = 0; i < v.length; i++) {
    if (typeof v[i] !== 'number' || !isFinite(v[i]) || v[i] % 1 !== 0 || v[i] < 0 || v[i] > 6) {
      return 'contains ' + JSON.stringify(v[i]) + ', which is not an integer day number 0-6 (0=Sunday)';
    }
  }
  return null;
}

// Used only by the terminal-day-rule audit step, which has to name the day of
// the week in prose an attorney reads. Indexed to match dayOfWeek above.
var WEEKDAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

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
//
// ── WHAT BELONGS IN A CALENDAR: THE STATUTORY TEST, NOT THE CLOSURE
//    SCHEDULE. Read this before "completing" any calendar. ──────────────────
// A calendar here holds days a rule MAKES a legal holiday. It does NOT hold
// days a courthouse merely happens to be closed. Those are different sets and
// the difference is load-bearing.
//
// Established while seeding Pennsylvania (Phase 3), where the two diverge
// most: the AOPC publishes a per-county matrix in which individual counties
// elect to stay OPEN on particular holidays and add closures of their own.
// Pa.R.J.A. 107(b) omits a last day falling on a day "made a legal holiday by
// the laws of this Commonwealth or of the United States" -- a statutory test,
// not an attendance record. So the PA calendars deliberately EXCLUDE the day
// after Thanksgiving, Christmas Eve, primary election days and county-specific
// closures, even though Pennsylvania courts commonly close on them.
//
// WHY THIS IS NOT A GAP TO BE HELPFULLY FILLED IN LATER: everywhere else in
// this system an omitted holiday makes the computed date EARLIER than the
// truth, which is the safe direction -- you file early. Adding a day that no
// statute makes a holiday inverts that. The engine then rolls a deadline it
// should not have rolled and reports a date LATER than the real one, and a
// date that is late is how a filing is missed. A calendar padded with observed
// closures is therefore more dangerous than one that is honestly incomplete.
//
// If a future jurisdiction has the same shape -- a published closure schedule
// that is broader than, or varies locally from, the statutory holiday list --
// encode the statute and disclose the divergence in the seed's authority note.
// Do not reconcile the two by adding the closure days.
//
// ── AMENDED 2026-08-25: THAT RULE IS CONDITIONAL ON WHAT THE RULE'S OWN TEST
//    IS, AND NORTH CAROLINA IS THE COUNTER-EXAMPLE. ────────────────────────
// The paragraph above is right for Pennsylvania because Pa.R.J.A. 107(b) asks a
// STATUTORY question -- is the day "made a legal holiday by the laws of this
// Commonwealth or of the United States". Where the rule asks that, the statute
// is the answer and a closure schedule is not.
//
// N.C. R. Civ. P. 6(a) (G.S. 1A-1, Rule 6(a)) asks the OPPOSITE question. It
// rolls off "a Saturday, Sunday or a legal holiday WHEN THE COURTHOUSE IS
// CLOSED FOR TRANSACTIONS", never cites G.S. 103-4, and that qualifier makes
// actual closure the test. Encoding the statute there would be wrong, and wrong
// in the dangerous direction: G.S. 103-4(a) declares roughly nine days the
// Judicial Branch does not close for -- Robert E. Lee's Birthday, Greek
// Independence Day, the Halifax Resolves anniversary, Confederate Memorial Day,
// the Mecklenburg Declaration anniversary, Washington's Birthday, First
// Responders Day, Columbus Day, Yom Kippur and general election day -- and each
// would roll a deadline LATER than the truth.
//
// SO THE RULE IS: read the rule's own test first, then pick the source that
// answers THAT question. A statutory test takes the statute even where courts
// close more often; a closure test takes the published closure schedule even
// where the statute lists more days. Neither is a default. What does not change
// is the direction check -- whichever source is chosen, ask which way an error
// in it moves the date, and prefer the source that fails EARLY.
//
// (Michigan has the same shape in weaker form: MCR 8.110(D)(2)(c) expressly
// authorises local administrative orders modifying the schedule, so its
// calendars are the MCR default rather than a guarantee for any given court.)
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

// Was service made by ONE method only, by several, or is it not stated?
//
// EXCLUSIVITY IS NOT A METHOD. Every service-extension standard before this
// asked only WHICH method was used, which `service_method` answers on its own.
// Two rules ask something the singular field cannot express -- whether that
// method was the ONLY one used:
//
//   Utah URCP 6(c)                      "service is made EXCLUSIVELY BY MAIL"
//   Fla. R. Gen. Prac. & Jud. Admin.
//     2.514(b)                          "service is made BY ONLY MAIL"
//
// So `service_methods` is a SEPARATE, OPTIONAL input holding the full set the
// caller actually used. It is consulted ONLY for this test; qualification still
// runs on `service_method` exactly as before, so no existing jurisdiction's
// behaviour moves and no existing row needs editing.
//
// Returns:
//   'exclusive' -- the set is exactly the one qualifying method
//   'combined'  -- the set holds that method AND at least one other
//   'unknown'   -- no set was supplied, so the question cannot be answered
//
// A set that does NOT contain service_method at all is 'combined' rather than
// an error: the caller has contradicted themselves, and the safe reading of a
// contradiction is the one that adds no days.
function exclusivityOf(input) {
  var set = input && input.service_methods;
  if (!Array.isArray(set) || set.length === 0) return 'unknown';
  if (set.length === 1 && set[0] === input.service_method) return 'exclusive';
  return 'combined';
}

// Rolls a landing date off a Saturday, Sunday or legal holiday. Forward
// periods roll forward; backward periods roll backward (Rule 6(a)(5)).
// Returns a refusal if a year's calendar is missing rather than treating an
// unknown year as holiday-free -- that would silently skip New Year's Day.
function rollOff(iso, calendars, jurisdiction, direction, weekendDays) {
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
    if (!isWeekend(cur, weekendDays) && !h.hit) return { ok: true, date: cur };
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
function countExcludingWeekendsAndHolidays(triggerDate, sign, n, calendars, jurisdiction, direction, weekendDays) {
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
    if (!isWeekend(cur, weekendDays) && !h.hit) remaining--;
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
// base_period_suffix / rollover_suffix_forward / rollover_suffix_backward are
// per-standard, not hardcoded onto the step-builders below, because the FRCP
// family's (1)(A)-(B) / (1)(C) / (5) sub-lettering is a real feature of THAT
// rule's text (FRAP 26(a) and Bankr. R. 9006(a) were both harmonized to the
// same structure in 2009) and is not universal. Ohio Civ.R. 6(A) is a single
// unlettered paragraph with no such subsections -- citing "(1)(A)-(B)" on an
// Ohio audit-trail step would assert a subsection that does not exist in the
// rule text, which is exactly the kind of small citation inaccuracy this
// engine's audit trail is supposed to prevent (see this file's own header:
// "the audit trail is part of the product, not a debug aid").
var COMPUTATION_STANDARDS = {
  frcp_6a: { label: 'Fed. R. Civ. P. 6(a)', impl: 'frcp_6a', base_period_suffix: '(1)(A)-(B)', months_years_suffix: '(1)(C)', rollover_suffix_forward: '(1)(C)', rollover_suffix_backward: '(5)' },
  frap_26a: { label: 'Fed. R. App. P. 26(a)', impl: 'frcp_6a', base_period_suffix: '(1)(A)-(B)', months_years_suffix: '(1)(C)', rollover_suffix_forward: '(1)(C)', rollover_suffix_backward: '(5)' },
  bankr_9006a: { label: 'Fed. R. Bankr. P. 9006(a)', impl: 'frcp_6a', base_period_suffix: '(1)(A)-(B)', months_years_suffix: '(1)(C)', rollover_suffix_forward: '(1)(C)', rollover_suffix_backward: '(5)' },
  ohio_civ_r_6a: { label: 'Ohio Civ.R. 6(A)', impl: 'ohio_civ_r_6a', short_period_exclusion_days: 7, base_period_suffix: '', months_years_suffix: '', rollover_suffix_forward: '', rollover_suffix_backward: '' },
  // Indiana T.R. 6(A). Verified independently against the rule text rather
  // than inherited from Ohio because the two only LOOK alike: both use a
  // seven-day threshold, but Indiana's exclusion set is strictly WIDER --
  // "intermediate Saturdays, Sundays, legal holidays, and days on which the
  // office is closed must be excluded". The office-closed limb has no Ohio
  // or federal analog and is NOT modelled by this engine, which has no field
  // for a given clerk's office closures. See ohio_civ_r_6a's own entry for
  // why a shared threshold is not evidence of a shared rule.
  indiana_tr_6a: { label: 'Ind. T.R. 6(A)', impl: 'indiana_tr_6a', short_period_exclusion_days: 7, base_period_suffix: '', months_years_suffix: '', rollover_suffix_forward: '', rollover_suffix_backward: '' },
  // Michigan MCR 1.108. Maps to the frcp_6a IMPLEMENTATION -- straight
  // calendar counting, roll only the last day -- because Michigan genuinely
  // works that way, NOT because two states before it happened to share a
  // mechanism. Verified explicitly: MCR 1.108 contains NO short-period
  // exclusion of any kind. Ohio's and Indiana's seven-day rule does not
  // generalise, and declaring short_period_exclusion_days here would have
  // pushed every short Michigan deadline LATER than the true date.
  //
  // Its subrule numbering is real and citable, unlike Ohio's and Indiana's
  // unlettered paragraphs: (1) carries both the day-exclusion and the
  // last-day rollover, (3) carries months/years. Backward counting is left
  // BLANK on purpose -- MCR 1.108 does not address backward-counted periods,
  // and citing (1) for behaviour the rule never describes would repeat the
  // citation defect already fixed once in this file.
  michigan_mcr_1108: { label: 'Mich. Ct. R. 1.108', impl: 'frcp_6a', base_period_suffix: '(1)', months_years_suffix: '(3)', rollover_suffix_forward: '(1)', rollover_suffix_backward: '' },
  // Pennsylvania Pa.R.J.A. 107 (201 Pa. Code Sec. 107). Like Michigan and
  // unlike Ohio and Indiana, it has NO short-period exclusion -- verified by
  // reading all four subdivisions, not inferred from the two states that do.
  //
  // THIS STANDARD REPLACED A RESCINDED ONE. Pa.R.C.P. 106 (231 Pa. Code
  // Sec. 106) was RESCINDED effective 2024-01-01 and its computation rules
  // were consolidated into Pa.R.J.A. 107, added 2023-11-03 effective
  // 2024-01-01. Rules citing this standard therefore carry an effective_from
  // of 2024-01-01, and a Pennsylvania matter triggered before that date is
  // REFUSED rather than computed -- the pre-2024 text was never read
  // verbatim here, so encoding it would be exactly the guess this engine
  // exists to refuse. That refusal is the intended behaviour, not a gap.
  //
  // Subdivision lettering is real and citable: (a) days, (b) the last-day
  // omission, (d) months. Backward left blank -- Rule 107 does not address
  // backward-counted periods.
  pa_rja_107: { label: 'Pa.R.J.A. 107', impl: 'frcp_6a', base_period_suffix: '(a)', months_years_suffix: '(d)', rollover_suffix_forward: '(b)', rollover_suffix_backward: '' },
  // Illinois 5 ILCS 70/1.11 (Statute on Statutes). Read verbatim from the
  // Illinois General Assembly's own site on 2026-08-23; the whole operative
  // text is one unnumbered paragraph:
  //
  //   "The time within which any act provided by law is to be done shall be
  //    computed by excluding the first day and including the last, unless the
  //    last day is Saturday or Sunday or is a holiday as defined or fixed in
  //    any statute now or hereafter in force in this State, and then it shall
  //    also be excluded. If the day succeeding such Saturday, Sunday or
  //    holiday is also a holiday or a Saturday or Sunday then such succeeding
  //    day shall also be excluded."
  //
  // Maps to the frcp_6a IMPLEMENTATION -- straight calendar counting, roll
  // only the last day, cascading until a day that is none of those -- because
  // Illinois genuinely works that way, NOT because most states before it did.
  // Verified explicitly: 1.11 contains NO short-period exclusion of any kind,
  // so it follows Michigan and Pennsylvania, not Ohio and Indiana. Declaring
  // short_period_exclusion_days here would have pushed every short Illinois
  // deadline LATER than the true date. The cascade sentence is the same
  // behaviour FRCP 6(a)(1)(C) produces by saying "continue to run until"; it
  // is stated explicitly in Illinois rather than implied.
  //
  // All four suffixes are BLANK on purpose. 1.11 has no subdivisions to cite
  // -- unlike Michigan's (1)/(3) and Pennsylvania's (a)/(b)/(d) -- so citing
  // one would invent a subdivision, and 1.11 does not address backward-counted
  // periods or months/years at all.
  //
  // NOTE ON HOLIDAYS: 1.11 does not define "holiday". It incorporates whatever
  // is "defined or fixed in any statute now or hereafter in force in this
  // State", which is 205 ILCS 630/17(a). That is a STATUTORY list, and it is
  // NOT the same as the list Illinois courts actually close on (Supreme Court
  // order M.R. 5272). They disagree in both directions. The calendars encode
  // the statutory list because that is what 1.11's own words key on; see
  // sql/sairnlaw_deadline_calendars_illinois.json for the full disclosure.
  illinois_5ilcs70_111: { label: '5 ILCS 70/1.11', impl: 'frcp_6a', base_period_suffix: '', months_years_suffix: '', rollover_suffix_forward: '', rollover_suffix_backward: '' },
  // Florida, Fla. R. Gen. Prac. & Jud. Admin. 2.514. Read verbatim from The
  // Florida Bar's official rule book (July 1, 2026 edition) on 2026-08-23.
  //
  // THIS ONE IS NOT A REUSE, AND THE EARLIER SCOPING SAID IT WOULD BE.
  // Florida was proposed as "data-only, no engine change" on the strength of
  // its short-period exclusion matching Ohio's seven-day threshold. Reading
  // the rule end to end showed that was wrong, and wrong in the dangerous
  // direction:
  //
  //   2.514(a)(1)(A) "begin counting from the next day that is not a
  //                   Saturday, Sunday, or legal holiday"
  //   FRCP 6(a)(1)(A) "exclude the day of the event that triggers the period"
  //
  // Florida shifts the START of the count to the next business day and counts
  // that day as day one. FRCP starts counting the very next calendar day.
  // Every Florida deadline triggered on a Friday, or the day before a
  // holiday, differs. Hence shifted_start, and hence this note -- the
  // mistake was in the plan, not in the rule.
  //
  // short_period_exclusion_days IS 7, per 2.514(a)(2): "When the period stated
  // in days is less than 7 days, Saturdays, Sundays, and legal holidays are
  // not counted." Same threshold as Ohio and Indiana, verified independently
  // from Florida's own text rather than carried across -- the shared number
  // is a coincidence of drafting, not evidence of a shared rule, which is the
  // standing lesson from Ohio/Indiana/Michigan in this file.
  //
  // Backward counting IS addressed, unlike Michigan, Pennsylvania and
  // Illinois: 2.514(a)(5) defines "next day" as forward after an event and
  // backward before one, so rollover_suffix_backward can cite (a)(5) honestly.
  //
  // LEGAL HOLIDAY IS NARROWER THAN THE STATUTE. 2.514(a)(6)(A) does not
  // incorporate all of Fla. Stat. 110.117 -- it enumerates nine specific
  // observances. See the calendar file for what that excludes and why.
  //
  // NOT MODELLED, deliberately: the chief-justice extension limb, which
  // appears three times in this rule -- in (a)(1)(C), (a)(3)(C) and
  // (a)(6)(B). It is Florida's hurricane mechanism: the chief justice may
  // extend time by order, and a day falling within such an extension is
  // treated like a holiday. It is unknowable in advance and the engine has no
  // field for it, exactly like Indiana's office-closed limb in T.R. 6(A) and
  // Illinois's Governor-proclamation limb in 205 ILCS 630/17(a). 2.514(a)(6)(B)
  // carries a second unmodellable limb in the same breath -- "any day observed
  // as a holiday by the clerk's office or as designated by the chief justice
  // or chief judge". A Florida date from this engine is therefore correct only
  // absent an emergency order; during hurricane season that is a real caveat,
  // not a formality, and it is surfaced to the user rather than buried here.
  // ── CALIFORNIA: TWO STANDARDS, NOT ONE ──────────────────────────────────
  // California splits its time computation across two authorities, and which
  // one governs depends on what created the deadline:
  //
  //   ca_ccp_12_12a  a period fixed by STATUTE (Code of Civil Procedure and
  //                  every other code) -- CCP 12, 12a, 12b, 12c
  //   ca_crc_1_10    a period fixed by the RULES OF COURT -- Cal. R. Ct. 1.10
  //
  // A single blanket "California" standard would cite the wrong authority on
  // roughly half the rows. The two texts happen to produce the same arithmetic
  // today, which is exactly why one standard is tempting and wrong: the audit
  // trail an attorney follows has to name the authority that actually governs
  // the deadline in front of them, and the two can diverge on amendment.
  //
  // NO ENGINE CHANGE WAS NEEDED. That prediction was carried forward as
  // UNVERIFIED after Florida disproved the same prediction, and was then
  // checked rather than assumed: CCP 12 excludes the first day and includes
  // the last, with no short-period exclusion and no shifted start, and
  // Rule 1.10(a) says the same in different words. Both map to frcp_6a.
  //
  // CCP 12, verbatim: "The time in which any act provided by law is to be done
  // is computed by excluding the first day, and including the last, unless the
  // last day is a holiday, and then it is also excluded."
  //
  // BACKWARD COUNTING IS ADDRESSED, and by its own section: CCP 12c(a), added
  // 2011, covers acts due "no later than a specified number of days before a
  // hearing date" and directs counting backward from the hearing, excluding
  // the hearing day per section 12. So the backward suffix cites 12c, not 12 --
  // Michigan, Pennsylvania and Illinois all leave it blank because their rules
  // are silent, and California's is not.
  //
  // THE HOLIDAY DEFINITION IS THE SUBTLE PART, and it is not "the state
  // holiday list". CCP 12a(a) defines holiday as "all day on Saturdays, all
  // holidays specified in Section 135 and, to the extent provided in Section
  // 12b, all days that by terms of Section 12b are required to be considered
  // as holidays." CCP 135 then takes Gov. Code 6700's list, keeps only FULL
  // days, and carves five of them back out. See the calendar file.
  //
  // NOT MODELLED, flagged not dropped -- CCP 12b: "If any city, county, state,
  // or public office, other than a branch office, is closed for the whole of
  // any day, insofar as the business of that office is concerned, that day
  // shall be considered as a holiday for the purposes of computing time under
  // Sections 12 and 12a." An office-closed limb, unknowable in advance, and
  // the same class as Indiana's T.R. 6(A) limb, Illinois's
  // Governor-proclamation limb and Florida's chief-justice limb.
  ca_ccp_12_12a: { label: 'Cal. Code Civ. Proc. 12, 12a', impl: 'frcp_6a',
    base_period_suffix: '', months_years_suffix: '',
    rollover_suffix_forward: '', rollover_suffix_backward: 'c' },
  // Cal. R. Ct. 1.10(a), verbatim: "The time in which any act provided by
  // these rules is to be performed is computed by excluding the first day and
  // including the last, unless the last day is a Saturday, Sunday, or other
  // legal holiday, and then it is also excluded." 1.10(b) carries the
  // extension to the next non-holiday day.
  //
  // Note this text names Saturday and Sunday EXPLICITLY, where CCP 12a reaches
  // Saturday through its own definition and Sunday only via Gov. Code
  // 6700(a)(1). Same result, different route -- another reason to keep the two
  // standards separate rather than treat one as an alias of the other.
  //
  // Backward is left BLANK: Rule 1.10 does not address backward-counted
  // periods. CCP 12c does, but 12c is a statute and citing it under a
  // rules-of-court standard would attribute to Rule 1.10 something it never
  // says -- the citation defect already fixed once in this file for Michigan.
  ca_crc_1_10: { label: 'Cal. R. Ct. 1.10', impl: 'frcp_6a',
    base_period_suffix: '(a)', months_years_suffix: '',
    rollover_suffix_forward: '(b)', rollover_suffix_backward: '' },
  fl_rgpja_2514: { label: 'Fla. R. Gen. Prac. & Jud. Admin. 2.514', impl: 'frcp_6a',
    shifted_start: true, short_period_exclusion_days: 7,
    base_period_suffix: '(a)(1)(A)-(B)', months_years_suffix: '',
    rollover_suffix_forward: '(a)(1)(C)', rollover_suffix_backward: '(a)(5)' },
  // ── TEXAS: TWO STANDARDS, AND THEY GENUINELY DIVERGE ────────────────────
  // California also has two standards, but there the split is about citing
  // the right authority for identical arithmetic. Texas is a stronger case:
  // the two rules PRODUCE DIFFERENT DATES, so treating them as one would be
  // wrong on the numbers, not merely wrong in the audit trail.
  //
  //   tx_trcp_4   Tex. R. Civ. P. 4      -- HAS a short-period exclusion
  //   tx_trap_41  Tex. R. App. P. 4.1(a) -- has NONE
  //
  // Both read verbatim from the Texas Judicial Branch's own published rule
  // books on 2026-08-24, each one read end to end rather than one being
  // inferred from the other.
  //
  // Tex. R. Civ. P. 4, verbatim: "In computing any period of time prescribed
  // or allowed by these rules, by order of court, or by any applicable
  // statute, the day of the act, event, or default after which the designated
  // period of time begins to run is not to be included. The last day of the
  // period so computed is to be included, unless it is a Saturday, Sunday, or
  // legal holiday, in which event the period runs until the end of the next
  // day which is not a Saturday, Sunday, or legal holiday. Saturdays, Sundays,
  // and legal holidays shall not be counted for any purpose in any time period
  // of five days or less in these rules, except that Saturdays, Sundays, and
  // legal holidays shall be counted for purpose of the three-day periods in
  // Rules 21 and 21a, extending other periods by three days when service is
  // made by mail."
  //
  // ── THE THRESHOLD IS 6 AND THAT IS NOT A TYPO. READ THIS BEFORE EDITING. ─
  // short_period_exclusion_days is compared with a STRICT less-than at the
  // call site (countValue < std.short_period_exclusion_days). Ohio, Indiana
  // and Florida all say "less than seven days", so 7 is the literal number in
  // their rule AND the right value here. Texas says "five days or less",
  // which is <= 5, which is < 6. The literal number in the Texas rule is FIVE
  // and the correct value in this field is SIX.
  //
  // Writing 5 here would silently stop excluding weekends on exactly the
  // five-day periods the rule is aimed at, producing a date EARLIER than the
  // true Texas deadline. Writing 7 would exclude them on six- and seven-day
  // periods the rule does not reach, producing a date LATER -- the direction
  // that misses a filing. Neither would throw. This is the third jurisdiction
  // whose short-period threshold had to be read rather than carried across,
  // and the first where the rule's number and this field's number differ.
  //
  // CURRENTLY UNREACHABLE BY CONSTRUCTION, AND KEPT ANYWAY. No Texas rule
  // seeded today has a base period of five days or less -- the shortest is 20.
  // The property is declared because it is a property of Rule 4, not of the
  // rows that happen to exist, and omitting it would leave a live trap for
  // whoever seeds the first short Texas period. Same call already made for
  // StoneDesk's last-active-admin guard: reachability is a property of the
  // current rule set, not of the rule.
  //
  // THE EXCEPTION CLAUSE NEEDS NO CODE, AND THAT WAS VERIFIED RATHER THAN
  // ASSUMED. Rule 4 carves the Rule 21/21a three-day periods out of the
  // exclusion, so those three days count Saturdays, Sundays and holidays even
  // though three is under the threshold. The exclusion here only ever runs in
  // the base-period branch, and the service-extension branch adds plain
  // calendar days, so the carve-out is satisfied structurally. Checked against
  // both call sites; if the extension path is ever changed to consult a
  // standard's short-period property, Texas breaks and this note is the reason.
  //
  // Rule 4 is a single unlettered paragraph, so every suffix is BLANK -- same
  // reasoning as Ohio, Indiana and Illinois. It does not address backward
  // counting or months and years.
  tx_trcp_4: { label: 'Tex. R. Civ. P. 4', impl: 'frcp_6a',
    short_period_exclusion_days: 6,
    base_period_suffix: '', months_years_suffix: '',
    rollover_suffix_forward: '', rollover_suffix_backward: '' },
  // Tex. R. App. P. 4.1(a), verbatim: "The day of an act, event, or default
  // after which a designated period begins to run is not included when
  // computing a period prescribed or allowed by these rules, by court order,
  // or by statute. The last day of the period is included, but if that day is
  // a Saturday, Sunday, or legal holiday, the period extends to the end of the
  // next day that is not a Saturday, Sunday, or legal holiday."
  //
  // NO SHORT-PERIOD EXCLUSION -- verified by reading 4.1 in full, not inferred
  // from the fact that the civil rule in the same state has one. Declaring one
  // here would push Texas's 20-day accelerated appeal and every shorter
  // appellate period LATER than the true deadline. Within a single state the
  // two rules disagree, which is the sharpest available illustration of why
  // this engine never carries a computation standard across a rule family.
  //
  // Subdivision lettering is real and citable here, unlike Rule 4: (a) carries
  // both the day-exclusion and the last-day rollover. Backward is BLANK --
  // 4.1 does not address backward-counted periods.
  //
  // NOT MODELLED: 4.1(b), the clerk's-office-closed limb -- "if the clerk's
  // office where the document is to be filed is closed or inaccessible during
  // regular hours on the last day for filing the document, the period for
  // filing the document extends to the end of the next day when the clerk's
  // office is open and accessible." Unknowable in advance, same class as
  // Indiana's T.R. 6(A) limb, Illinois's Governor-proclamation limb, Florida's
  // chief-justice limb and California's CCP 12b. Note it is a limb of the
  // APPELLATE rule only: Tex. R. Civ. P. 4 has no equivalent, despite a
  // widely repeated secondary claim that it does.
  tx_trap_41: { label: 'Tex. R. App. P. 4.1', impl: 'frcp_6a',
    base_period_suffix: '(a)', months_years_suffix: '(a)',
    rollover_suffix_forward: '(a)', rollover_suffix_backward: '' },
  // ── NEW YORK: THE COMPUTATION RULE IS NOT IN THE CPLR AT ALL ────────────
  // Every other jurisdiction here computes time under the same body of rules
  // that sets its deadlines. New York does not. The CPLR contains no general
  // computation provision, so the arithmetic comes from the General
  // Construction Law, a different statute entirely:
  //
  //   Gen. Constr. Law 20    counting
  //   Gen. Constr. Law 25-a  what happens when the last day is bad
  //   Gen. Constr. Law 24    what counts as a public holiday
  //
  // THE LINK IS IN THE STATUTE'S OWN WORDS, which is worth stating because the
  // equivalent link in Texas is not. Gen. Constr. Law 110: "This chapter is
  // applicable to every statute unless its general object, or the context of
  // the language construed, or other provisions of law indicate that a
  // different meaning or application was intended from that required to be
  // given by this chapter." The CPLR is a statute and indicates no different
  // application. Contrast tx_trcp_4, where the rule says "legal holiday" and
  // never cites a definition.
  //
  // Gen. Constr. Law 20, verbatim: "A number of days specified as a period
  // from a certain day within which or after or before which an act is
  // authorized or required to be done means such number of calendar days
  // exclusive of the calendar day from which the reckoning is made. If such
  // period is a period of two days, Saturday, Sunday or a public holiday must
  // be excluded from the reckoning if it is an intervening day between the day
  // from which the reckoning is made and the last day of the period. In
  // computing any specified period of time from a specified event, the day
  // upon which the event happens is deemed the day from which the reckoning is
  // made. The day from which any specified period of time is reckoned shall be
  // excluded in making the reckoning."
  //
  // Gen. Constr. Law 25-a(1), verbatim: "When any period of time, computed
  // from a certain day, within which or after which or before which an act is
  // authorized or required to be done, ends on a Saturday, Sunday or a public
  // holiday, such act may be done on the next succeeding business day..."
  //
  // ── THE TWO-DAY LIMB IS DELIBERATELY NOT DECLARED, AND THAT IS A JUDGMENT
  //    CALL RATHER THAN AN OVERSIGHT. READ BEFORE ADDING IT. ────────────────
  // Section 20's second sentence is a short-period exclusion, so the reflex is
  // to set short_period_exclusion_days the way Ohio, Indiana, Florida and
  // Texas do. That would be WRONG here, for two independent reasons:
  //
  //   1. SCOPE. This engine's property means "exclude for every period shorter
  //      than N", tested as countValue < N. Section 20's limb applies to a
  //      period of EXACTLY two days -- "If such period is a period of two
  //      days". Declaring 3 would also capture one-day periods, which the
  //      sentence never reaches.
  //   2. MECHANISM. The other four states exclude Saturdays, Sundays and
  //      holidays from the COUNT. Section 20 excludes such a day only when it
  //      is "an intervening day between the day from which the reckoning is
  //      made and the last day of the period" -- a narrower operation on a
  //      two-day span than the general skip-while-counting loop performs.
  //
  // No New York rule seeded here has a two-day period; the shortest is 20. So
  // the limb is unreachable by the current row set either way, and declaring a
  // property that misstates it would be worse than leaving it out. If a
  // two-day New York period is ever seeded, this limb must be implemented on
  // its own terms and NOT by setting short_period_exclusion_days. Contrast
  // tx_trcp_4, which DOES declare its (equally unreachable) threshold, because
  // there the rule's mechanism and this engine's property genuinely match.
  //
  // BACKWARD COUNTING IS LEFT BLANK ON PURPOSE. Section 25-a's opening does
  // reach a period computed "before which an act is authorized or required to
  // be done", but its only remedy is "the next succeeding business day" --
  // forward. What that means for a backward-counted period is not resolved by
  // the text, and extending a backward deadline forward would push it past the
  // event it is measured against. No backward New York rule is seeded, and the
  // suffix stays empty rather than citing 25-a for behaviour it does not
  // describe -- the citation defect already fixed once in this file.
  //
  // Section 20 has no subdivisions to cite, so the base suffix is blank; 25-a
  // is numbered and its rollover limb really is subdivision 1.
  ny_gcl_20: { label: 'N.Y. Gen. Constr. Law 20, 25-a', impl: 'frcp_6a',
    base_period_suffix: '', months_years_suffix: '',
    rollover_suffix_forward: ' 25-a(1)', rollover_suffix_backward: '' },
  // ── GEORGIA: THE CIVIL PRACTICE ACT DELEGATES ITS ARITHMETIC OUT ────────
  // Like New York, Georgia does not compute time in the same body of rules
  // that sets its deadlines -- but it says so expressly rather than leaving
  // it to a general applicability clause. O.C.G.A. 9-11-6(a), verbatim:
  // "In computing any period of time prescribed or allowed by this chapter,
  // by the rules of any court, by order of court, or by an applicable
  // statute, the computation rules prescribed in paragraph (3) of subsection
  // (d) of Code Section 1-3-1 shall be used."
  //
  // So the operative text is O.C.G.A. 1-3-1(d)(3), verbatim: "Except as
  // otherwise provided by time period computations specifically applying to
  // other laws, when a period of time measured in days, weeks, months, years,
  // or other measurements of time except hours is prescribed for the exercise
  // of any privilege or the discharge of any duty, the first day shall not be
  // counted but the last day shall be counted; and, if the last day falls on
  // Saturday or Sunday, the party having such privilege or duty shall have
  // through the following Monday to exercise the privilege or to discharge
  // the duty. When the last day prescribed for such action falls on a public
  // and legal holiday as set forth in Code Section 1-4-1, the party having
  // the privilege or duty shall have through the next business day to
  // exercise the privilege or to discharge the duty. When the period of time
  // prescribed is less than seven days, intermediate Saturdays, Sundays, and
  // legal holidays shall be excluded in the computation."
  //
  // SHORT-PERIOD EXCLUSION IS 7, verified from Georgia's own words and not
  // carried across: "less than seven days" is < 7, so 7 is both the number in
  // the rule and the right value here. That matches Ohio, Indiana and Florida
  // and differs from Texas, where the rule says "five days or less" and this
  // field has to be 6. Reachable in Georgia, unlike in Texas: O.C.G.A.
  // 9-11-6(d) sets a five-day motion-notice period, and the two 15-day
  // periods in 9-11-12(a)(2) sit just above the threshold, so a maintainer
  // seeding anything shorter will hit this branch for real.
  //
  // ── THE ROLLOVER IS TWO SENTENCES, AND WHETHER THEY CASCADE IS THE ONE
  //    GENUINELY UNSETTLED THING HERE. READ BEFORE CHANGING. ───────────────
  // Sentence one sends a last day falling on Saturday or Sunday "through the
  // following Monday". Sentence two sends a last day falling on a public and
  // legal holiday "through the next business day". Neither sentence says what
  // happens when the last day is a SATURDAY and the following Monday is a
  // holiday -- which is every Saturday before Memorial Day, Labor Day,
  // Columbus Day, Washington's Birthday and King's Birthday.
  //
  //   Non-cascading reading: sentence one applies, deadline is that Monday,
  //                          and sentence two never fires because the LAST DAY
  //                          was the Saturday, not the holiday.
  //   Cascading reading:     sentence one extends the period so the Monday is
  //                          now "the last day prescribed", sentence two then
  //                          catches it, and the deadline is Tuesday.
  //
  // This engine takes the CASCADING reading, which is what rollOff does
  // naturally. Three reasons, and the first is the weakest: a Georgia
  // deadline-calculator source states the cascade explicitly on exactly the
  // Saturday-before-Memorial-Day facts. That is secondary and is recorded as
  // secondary. The second is textual: sentence two's remedy is "the next
  // BUSINESS day", a phrase that already means neither a weekend nor a
  // holiday, which reads as a legislature thinking in business days rather
  // than in single hops. The third is practical: the non-cascading reading
  // fixes a filing deadline on a day the courthouse is shut.
  //
  // NOTE THIS IS THE ONE PLACE IN THIS ENGINE WHERE AN UNSETTLED READING WAS
  // RESOLVED TOWARD THE LATER DATE. Everywhere else -- Texas's 21a sequencing
  // most recently -- ambiguity was resolved toward the earlier date because
  // late is what misses a filing. It is resolved the other way here because
  // the earlier date is not actually available to file on: a party told
  // "Monday" when Monday is Memorial Day cannot act on it, so the earlier
  // reading protects nobody. If that reasoning is ever shown wrong, this is
  // the line to change, and the fix is a per-standard flag on rollOff rather
  // than a change to rollOff itself, which every other jurisdiction relies on.
  //
  // MONTHS AND YEARS ARE ADDRESSED, unlike in most of this engine's states:
  // 1-3-1(d)(3) opens on a period "measured in days, weeks, months, years, or
  // other measurements of time except hours", so the months suffix can cite it
  // honestly. HOURS ARE EXPRESSLY CARVED OUT and no Georgia rule seeded here
  // is hour-based, so nothing falls through to day counting.
  //
  // Backward counting is NOT addressed and the suffix is left blank. Both
  // rollover sentences run forward only ("through the following Monday", "the
  // next business day"), and no backward Georgia rule is seeded.
  ga_ocga_1_3_1_d3: { label: 'O.C.G.A. 1-3-1(d)(3)', impl: 'frcp_6a',
    short_period_exclusion_days: 7,
    base_period_suffix: '', months_years_suffix: '',
    rollover_suffix_forward: '', rollover_suffix_backward: '' },
  // ── WEST VIRGINIA: TWO STANDARDS, BECAUSE THE STATE REALLY HAS TWO ───────
  // Every other jurisdiction in this engine computes time one way. West
  // Virginia computes it two DIFFERENT ways depending on which court's rules
  // govern, and the two differ on a mechanism this engine models. Both were
  // read verbatim on 2026-08-25 and neither was inferred from the other.
  //
  // ── wv_rcp_6a: THE 2025 RESTYLED CIVIL RULE ──────────────────────────────
  // The Supreme Court of Appeals adopted amendments on 2024-01-31 effective
  // 2025-01-01 -- the first substantial revision since 1998 -- and Rule 6 was
  // rewritten into the modern federal shape. W. Va. R. Civ. P. 6(a)(1),
  // verbatim: "When the period is stated in days or a longer unit of time,
  // exclude the day of the event that triggers the period; (A) count every
  // day, including intermediate Saturdays, Sundays and legal holidays; and
  // (B) include the last day of the period but if the last day is a Saturday,
  // a Sunday or legal holiday, the period continues to run until the end of
  // the next day that is not a Saturday, Sunday, or legal holiday."
  //
  // NO SHORT-PERIOD EXCLUSION, AND THAT IS A CHANGE, NOT AN ABSENCE. The
  // FORMER rule (read verbatim from the court's own "Former West Virginia
  // Rules of Civil Procedure") said: "When the period of time prescribed or
  // allowed is fewer than 11 days, intermediate Saturdays, Sundays, and legal
  // holidays shall be excluded in the computation." That limb is GONE from the
  // 2025 text -- "count every day" is now unqualified. Declaring
  // short_period_exclusion_days here would push every short West Virginia
  // civil deadline LATER than the true date, the direction that misses a
  // filing. Note the former threshold was 11, not the 7 that Ohio, Indiana and
  // Georgia use, so it could not have been carried across from them either.
  //
  // ONLY THE 2025 TEXT IS SEEDED. Every wv civil row carries
  // effective_from 2025-01-01, so a period running from an earlier date is
  // REFUSED rather than computed under a rule whose text was not read here.
  // See the seed readme for the separate, unmodelled problem that Rule 86 keys
  // applicability to when the CASE was commenced, not to the trigger date.
  //
  // The sub-lettering is real but is NOT the federal lettering: West Virginia
  // put "exclude the day of the event" in the flush text of (1) and relettered
  // the federal (B) and (C) as (A) and (B). Citing "(1)(A)-(B)" for the base
  // period the way frcp_6a does would point at the wrong subparagraphs, so the
  // base period cites (1) and the forward rollover cites (1)(B).
  //
  // BACKWARD COUNTING IS ADDRESSED, unlike in most of this engine's states.
  // Rule 6(a)(5), verbatim: "The 'next day' is determined by continuing to
  // count forward when the period is measured after an event and backward when
  // measured before an event." So the backward suffix is a real citation here.
  //
  // NOT MODELLED: Rule 6(a)(3), which extends a filing deadline when the
  // clerk's office is inaccessible. This engine has no inaccessibility input
  // and does not guess one. A deadline computed across a closure will be
  // EARLIER than the true one, which files early.
  wv_rcp_6a: { label: 'W. Va. R. Civ. P. 6(a)', impl: 'frcp_6a',
    base_period_suffix: '(1)', months_years_suffix: '(1)',
    rollover_suffix_forward: '(1)(B)', rollover_suffix_backward: '(5)' },
  // ── wv_rap_39a: THE APPELLATE RULE, WHICH IS NOT THE SAME RULE ───────────
  // W. Va. R. App. P. 39(a), verbatim: "In computing any period of time
  // prescribed by these rules, by an order of the Intermediate Court or the
  // Supreme Court, or by any applicable statute, the day of the act, event, or
  // default from which the designated period of time begins to run shall not
  // be included. The last day of the period shall be included, unless it is a
  // Saturday, a Sunday, or a legal holiday, in which event the period extends
  // until the end of the next day which is not a Saturday, a Sunday, or a
  // legal holiday. When the period of time prescribed or allowed is less than
  // seven days, intermediate Saturdays, Sundays, and legal holidays shall be
  // excluded in the computation."
  //
  // THE APPELLATE RULE KEPT A SHORT-PERIOD EXCLUSION THAT THE CIVIL RULE
  // DROPPED, and at a different threshold from the one the civil rule used to
  // have (7 here, formerly 11 there). Two standards is therefore the only
  // correct encoding; mapping West Virginia onto one would be wrong for one
  // half of the state's practice no matter which half was chosen.
  //
  // 39(a) is a single unlettered paragraph, so every suffix is blank -- the
  // same treatment Ohio and Indiana get, and for the same reason.
  //
  // BACKWARD IS BLANK ON PURPOSE. 39(a)'s only remedy is that "the period
  // extends until the end of the next day" -- forward. It does not describe a
  // backward-counted period and no backward wv row is seeded.
  //
  // ── THE HOLIDAY LISTS DIFFER AND ONE CALENDAR CANNOT SERVE BOTH ──────────
  // 39(a) defines "legal holiday" for itself and expressly names "Juneteenth
  // Day". R. Civ. P. 6(a)(6) does not, and cannot reach it: 6(a)(6)(C) counts
  // a day "declared a holiday by the Governor or President of the United
  // States or any other legal holiday so designated by the West Virginia
  // Legislature" -- it OMITS CONGRESS, which is what created Juneteenth
  // National Independence Day, and W. Va. Code 2-2-1(a) does not list it.
  //
  // Calendars are keyed by jurisdiction and year only, so the single `wv`
  // calendar encodes the CIVIL list and omits Juneteenth. The direction of the
  // resulting error is the reason that is acceptable and the reason the
  // opposite choice would not be: omitting a day makes an APPELLATE deadline
  // land one day EARLY, which files early, while adding it would roll CIVIL
  // deadlines that the civil rule does not roll and report a date LATE. That
  // is the same rule already stated for the Pennsylvania calendars at the top
  // of this file. Disclosed on every wv appellate row and in the calendar.
  // impl is its own string, not Ohio's, even though the two share a seven-day
  // threshold -- see ohio_civ_r_6a and indiana_tr_6a above on why a shared
  // threshold is not evidence of a shared rule.
  wv_rap_39a: { label: 'W. Va. R. App. P. 39(a)', impl: 'wv_rap_39a',
    short_period_exclusion_days: 7,
    base_period_suffix: '', months_years_suffix: '',
    rollover_suffix_forward: '', rollover_suffix_backward: '' },
  // ── NORTH CAROLINA: G.S. 1A-1, Rule 6(a) ────────────────────────────────
  // Its Rules of Civil Procedure are STATUTES -- Chapter 1A, Rule 6 is
  // G.S. 1A-1, Rule 6 -- so the whole text is public on the General Assembly's
  // own site. Read verbatim 2026-08-25:
  //
  //   "In computing any period of time prescribed or allowed by these rules, by
  //    order of court, or by any applicable statute, including rules, orders or
  //    statutes respecting publication of notices, the day of the act, event,
  //    default or publication after which the designated period of time begins
  //    to run is not to be included. The last day of the period so computed is
  //    to be included, unless it is a Saturday, Sunday or a legal holiday when
  //    the courthouse is closed for transactions, in which event the period
  //    runs until the end of the next day which is not a Saturday, Sunday, or a
  //    legal holiday when the courthouse is closed for transactions. When the
  //    period of time prescribed or allowed is less than seven days,
  //    intermediate Saturdays, Sundays, and holidays shall be excluded in the
  //    computation. A half holiday shall be considered as other days and not as
  //    a holiday."
  //
  // SHORT-PERIOD EXCLUSION IS 7, from "less than seven days" -- verified from
  // North Carolina's own words, not carried across from the four other states
  // that happen to use the same threshold.
  //
  // THE RULE STATES TWO DIFFERENT HOLIDAY TESTS IN CONSECUTIVE SENTENCES, and
  // it is worth knowing which one this engine implements. The last-day rollover
  // tests "a legal holiday WHEN THE COURTHOUSE IS CLOSED for transactions"; the
  // short-period exclusion tests plain "holidays", with no closure qualifier.
  // Read literally the second sentence could reach a G.S. 103-4 day the
  // courthouse stays open for -- Columbus Day, say -- and exclude it from the
  // count, lengthening a short period. This engine applies ONE calendar to
  // both, and that calendar is the closure schedule, so a short North Carolina
  // period counts such a day rather than skipping it. That is the EARLIER
  // result and therefore the safe one, and it is a choice, not an oversight.
  // See the calendar's readme for why the closure schedule is the right source
  // for the rollover, which is the sentence that governs most rows here.
  //
  // BACKWARD IS BLANK, AND NO BACKWARD ROW IS SEEDED. Rule 6(a) speaks only of
  // "the last day of the period" running "until the end of the next day" --
  // forward. It never defines what the next day means for a period counted
  // BEFORE an event, and North Carolina really has such periods: Rule 6(d)
  // requires a written motion and notice of hearing "not later than five days
  // before the time specified for the hearing", and an opposing affidavit "at
  // least two days before the hearing". Neither is seeded, because rolling them
  // in either direction would be this engine guessing at a rule that is silent,
  // and because the two-day one carries its own service definition anyway
  // ("service shall mean personal delivery, facsimile transmission, or other
  // means such that the party actually receives the affidavit within the
  // required time") which is actual receipt, not the ordinary service rule.
  // Same call already made for ny_gcl_20's backward suffix, for the same
  // reason. Contrast W. Va. R. Civ. P. 6(a)(5) and Fla. 2.514(a)(5), which do
  // define it, and KRS 446.030(1)(b), which defines it the OTHER way (a
  // backward North Carolina-style period rolling FORWARD) -- three jurisdictions,
  // three answers, so there is no default to fall back on.
  //
  // Rule 6 is lettered but its subsections are not sub-numbered, so the base
  // period and the rollover both sit in (a) and there is no separate
  // months/years provision to cite. NOT MODELLED: the half-holiday sentence
  // needs no code (no half holiday is ever put in the calendar), and Rule 6(f)'s
  // Address Confidentiality Program extension is discussed at nc_rcp_6e below.
  nc_rcp_6a: { label: 'N.C. R. Civ. P. 6(a) (G.S. 1A-1, Rule 6(a))', impl: 'nc_rcp_6a',
    short_period_exclusion_days: 7,
    base_period_suffix: '', months_years_suffix: '',
    rollover_suffix_forward: '', rollover_suffix_backward: '' },
  // ── WASHINGTON: THE ONE RULE THAT NAMES ITS OWN HOLIDAY STATUTE ─────────
  // CR 6(a), verbatim: "In computing any period of time prescribed or allowed
  // by these rules, by the local rules of any superior court, by order of
  // court, or by any applicable statute, the day of the act, event, or default
  // from which the designated period of time begins to run shall not be
  // included. The last day of the period so computed shall be included, unless
  // it is a Saturday, a Sunday or a legal holiday, in which event the period
  // runs until the end of the next day which is neither a Saturday, a Sunday
  // nor a legal holiday. LEGAL HOLIDAYS ARE PRESCRIBED IN RCW 1.16.050. When
  // the period of time prescribed or allowed is less than 7 days, intermediate
  // Saturdays, Sundays and legal holidays shall be excluded in the
  // computation."
  //
  // THAT ONE SENTENCE SETTLES WHAT FOUR OTHER JURISDICTIONS LEFT OPEN. Texas's
  // Rule 4 says "legal holiday" and never cites Gov't Code 662.021; Kentucky's
  // RAP 6(A) and KRS 446.030 both say it and neither defines it; West Virginia
  // defines it two different ways in two bodies of rules; North Carolina asks a
  // different question entirely (is the courthouse closed). Washington points
  // at a statute by number, so its calendar needs no judgment call -- and the
  // statute then excludes its own decoys expressly, because RCW 1.16.050(7)
  // says the days it lists "may not be considered legal holidays for any
  // purpose". See the calendar readme.
  //
  // SHORT-PERIOD EXCLUSION IS 7, from "less than 7 days" -- Washington's own
  // number, verified here and not carried across from the four other states
  // that happen to share it. Reachable: CR 6(d) sets a 5-day motion-notice
  // period and a 1-day affidavit period, and CR 12(a)(A)/(B) set 10-day
  // responsive-pleading periods, all under the threshold.
  //
  // BACKWARD IS BLANK, AND NO BACKWARD ROW IS SEEDED. CR 6(a) provides only
  // that "the period runs until the end of the next day" -- forward. It never
  // says what the next day means for a period counted BEFORE an event, and
  // Washington has such periods: CR 6(d) requires a written motion and notice
  // of hearing "not later than 5 days before the time specified for the
  // hearing" and opposing affidavits "not later than 1 day before the
  // hearing". Neither is seeded. Rolling them in either direction would be a
  // guess, and the jurisdictions that DO define it disagree three ways --
  // W. Va. R. Civ. P. 6(a)(5) and Fla. 2.514(a)(5) roll backward, KRS
  // 446.030(1)(b) rolls FORWARD. Same call already made for ny_gcl_20 and
  // nc_rcp_6a.
  //
  // CR 6 is lettered but not sub-numbered, so the base period and the rollover
  // both sit in (a) and there is no separate months/years provision to cite.
  wa_cr_6a: { label: 'Wash. Super. Ct. Civ. R. 6(a)', impl: 'wa_cr_6a',
    short_period_exclusion_days: 7,
    base_period_suffix: '', months_years_suffix: '',
    rollover_suffix_forward: '', rollover_suffix_backward: '' },
  // ── NEW JERSEY: R. 1:3-1 ────────────────────────────────────────────────
  // Verbatim: "In computing any period of time fixed by rule or court order,
  // the day of the act or event from which the designated period begins to run
  // is not to be included. The last day of the period so computed is to be
  // included, unless it is a Saturday, Sunday or legal holiday, in which event
  // the period runs until the end of the next day which is neither a Saturday,
  // Sunday nor legal holiday. In computing a period of time of less than 7
  // days, Saturday, Sunday and legal holidays shall be excluded."
  //
  // SHORT-PERIOD EXCLUSION IS 7, from "less than 7 days" -- New Jersey's own
  // number, read here rather than carried across from the five other states
  // that share it. Note the wording omits "intermediate", which every other
  // such rule includes; nothing in this engine turns on that, because the
  // exclusion only ever applies to days between the trigger and the end, but
  // it is recorded so a future reader does not think a word was dropped.
  //
  // "FIXED BY RULE OR COURT ORDER" -- AND NOT BY STATUTE. Every comparable rule
  // seeded so far reaches statutory periods too: Washington's CR 6(a) covers
  // time prescribed "by any applicable statute", North Carolina's Rule 6(a)
  // says "or by any applicable statute", West Virginia's says the same. New
  // Jersey's does not. A New Jersey deadline fixed by STATUTE rather than by
  // these rules is therefore outside R. 1:3-1's own terms, and no such row is
  // seeded. If one is ever added, do not assume this standard governs it.
  //
  // BACKWARD IS BLANK, AND NO BACKWARD ROW IS SEEDED. The rule provides only
  // that "the period runs until the end of the next day" -- forward -- and says
  // nothing about a period counted before an event. Same call as ny_gcl_20,
  // nc_rcp_6a and wa_cr_6a; the three jurisdictions that DO define it disagree
  // (W. Va. and Florida roll backward, KRS 446.030(1)(b) rolls forward).
  //
  // R. 1:3-1 is a single unnumbered paragraph, so every suffix is blank.
  //
  // ── ITS HOLIDAY LIST COMES FROM A COURT ORDER, NOT A STATUTE ────────────
  // R. 1:3-1 says "legal holiday" and names nothing, which puts New Jersey with
  // Texas, Kentucky and Arizona rather than with Washington. What saves it is
  // that the Supreme Court of New Jersey ISSUES AN ORDER each court year
  // designating the legal holidays by date, so an authoritative list exists
  // even though the rule does not point at one. N.J.S.A. 36:1-1 is NOT that
  // list and must not be used -- it is a negotiable-instruments statute, it
  // makes every Saturday a public holiday, and its subsection (d) expressly
  // removes Lincoln's Birthday while subsection (a) still lists it. See the
  // calendar readme.
  nj_r_1_3_1: { label: 'N.J. Ct. R. 1:3-1', impl: 'nj_r_1_3_1',
    short_period_exclusion_days: 7,
    base_period_suffix: '', months_years_suffix: '',
    rollover_suffix_forward: '', rollover_suffix_backward: '' },
  // ── VIRGINIA: A STATUTE COMPUTES THE TIME, NOT A RULE ───────────────────
  // Va. Code § 1-210(A), verbatim: "When an act of the General Assembly or rule
  // of court requires that an act be performed a prescribed amount of time
  // before a motion or proceeding, the day of such motion or proceeding shall
  // not be counted against the time allowed, but the day on which such act is
  // performed may be counted as part of the time. When an act of the General
  // Assembly or rule of court requires that an act be performed within a
  // prescribed amount of time after any event or judgment, the day on which the
  // event or judgment occurred shall not be counted against the time allowed."
  //
  // § 1-210(B), verbatim: "When the last day for performing an act during the
  // course of a judicial proceeding falls on a Saturday, Sunday, legal holiday,
  // or any day or part of a day on which the clerk's office is closed as
  // authorized by an act of the General Assembly, the act may be performed on
  // the next day that is not a Saturday, Sunday, legal holiday, or day or part
  // of a day on which the clerk's office is closed as authorized by an act of
  // the General Assembly."
  //
  // THIS IS THE EXACT INVERSE OF NEW JERSEY, AND THE PAIR IS WHY NEITHER WAS
  // ASSUMED FROM THE OTHER. N.J. R. 1:3-1 computes time fixed "by rule or court
  // order" and NOT by statute. Va. Code § 1-210 is itself a STATUTE and reaches
  // time fixed by "an act of the General Assembly OR rule of court" -- both.
  // A Virginia deadline fixed by statute is inside this standard's terms where
  // the equivalent New Jersey one is outside R. 1:3-1's.
  //
  // NO SHORT-PERIOD EXCLUSION, AND THAT WAS CHECKED RATHER THAN ASSUMED.
  // Six seeded jurisdictions exclude intermediate weekends and holidays from
  // short periods (Ohio and Indiana at "less than seven days", New Jersey,
  // North Carolina, Washington and West Virginia at seven). Virginia has no
  // such provision anywhere: not in § 1-210, and not in the Rules -- a search
  // of the complete published Rules for "intermediate Saturdays", "less than
  // seven days" and "less than 7 days" returns nothing. Every intermediate day
  // counts no matter how short the period. `short_period_exclusion_days` is
  // therefore ABSENT rather than set, which is the same treatment the federal
  // standard gets and for the same reason.
  //
  // BACKWARD IS DEFINED, UNLIKE NEW JERSEY, NORTH CAROLINA AND WASHINGTON.
  // § 1-210(A)'s first sentence expressly handles an act required "a prescribed
  // amount of time BEFORE a motion or proceeding" -- the day of the motion is
  // not counted, the day the act is performed may be. That is a real backward
  // direction in the statute's own words, so the suffix names (A). No backward
  // row is seeded in this batch even so; the seed is forward-only, and the
  // standard is honest about the statute rather than about the row set.
  //
  // ── ITS HOLIDAY LIST: A DERIVABLE CORE AND AN UNKNOWABLE LAYER ──────────
  // § 1-210 says "legal holiday" and names no statute, which puts Virginia with
  // Texas, Kentucky, Arizona and New Jersey rather than with Washington. What
  // makes it seedable is § 17.1-207(A), which requires every clerk's office to
  // be kept open "on every day except Saturday ... and Sunday, and the days
  // provided for in § 2.2-3300" -- so the statutory list IS reachable, by the
  // closure statute rather than by a cross-reference in § 1-210 itself.
  //
  // WHAT IS NOT REACHABLE, AND RIDES AS A DISCLOSURE ON EVERY VIRGINIA RESULT:
  //   § 1-210(F)  "any day on which the Governor authorizes the closing of the
  //               state government shall be considered a legal holiday" -- an
  //               executive act announced ad hoc, never knowable in advance.
  //   § 17.1-207  a clerk MAY also close on locality-adopted holidays, on
  //               Christmas Eve, and on days a chief or presiding judge
  //               authorizes for a health or safety threat. All discretionary,
  //               all per-locality.
  // THE OMISSION FAILS IN THE SAFE DIRECTION and that is why it is disclosed
  // rather than refused. An unmodelled closure means the computed date lands on
  // a day the office was in fact shut, and § 1-210(B) would roll the true
  // deadline LATER -- so this engine reports EARLY, never late. That is the
  // opposite of Kentucky, which is refused because encoding KRS 2.110 would run
  // late. See JURISDICTION_COVERAGE below for the text that ships with results.
  va_code_1_210: { label: 'Va. Code § 1-210', impl: 'va_code_1_210',
    base_period_suffix: '(A)', months_years_suffix: '(A)',
    rollover_suffix_forward: '(B)', rollover_suffix_backward: '(A)' },
  // ── MASSACHUSETTS: THE RULE NAMES ITS OWN HOLIDAY STATUTE ────────────────
  // Mass. R. Civ. P. 6(a), verbatim in full:
  //
  //   "In computing any period of time prescribed or allowed by these rules,
  //    by order of court, or by any applicable statute or rule, the day of the
  //    act, event, or default after which the designated period of time begins
  //    to run shall not be included. The last day of the period so computed
  //    shall be included, unless it is a Saturday, a Sunday, or a legal
  //    holiday, in which event the period runs until the end of the next day
  //    which is not a Saturday, a Sunday, or a legal holiday. When the period
  //    of time prescribed or allowed is less than 7 days, intermediate
  //    Saturdays, Sundays, and legal holidays shall be excluded in the
  //    computation. As used in this rule and in Rule 77(c), 'legal holiday'
  //    includes those days specified in Mass. G.L. c. 4, § 7 and any other day
  //    appointed as a holiday by the President or the Congress of the United
  //    States or designated by the laws of the Commonwealth."
  //
  // THE HOLIDAY QUESTION IS ANSWERED IN THE RULE'S OWN TEXT, which puts
  // Massachusetts with WASHINGTON and against Texas, Arizona and Kentucky.
  // CR 6(a) in Washington says "Legal holidays are prescribed in RCW
  // 1.16.050"; Rule 6(a) here names Mass. G.L. c. 4, § 7. Neither needs the
  // bundled lawyer's question that Texas, Kentucky, Illinois, West Virginia
  // and Arizona are all waiting on. Rule 77(b) then keeps the clerk's office
  // closed "on all days except Saturdays, Sundays, and legal holidays" -- the
  // same defined term, so the statute governs closure and rolling alike.
  //
  // SHORT-PERIOD EXCLUSION AT SEVEN, READ NOT ASSUMED. "less than 7 days" is
  // the rule's own wording, and 7 is therefore both the literal number in the
  // rule and the correct value for this field, which is compared with a strict
  // less-than. Same as New Jersey, North Carolina, Washington and West
  // Virginia's appellate rule; NOT Arizona's eleven.
  //
  // BACKWARD IS LEFT BLANK, like New Jersey, North Carolina and Washington and
  // unlike Virginia. Rule 6(a) speaks only of a period that "begins to run"
  // after an act, event or default; it says nothing about a period counted
  // backward from a hearing. No backward row is seeded and none may be added
  // without reading a rule that actually defines the direction.
  //
  // ── THE COVERAGE GAP IS GEOGRAPHIC, WHICH IS NEW HERE ───────────────────
  // Mass. G.L. c. 4, § 7, Cl. 18 makes Evacuation Day (17 March) and Bunker
  // Hill Day (17 June) legal holidays "with respect to SUFFOLK COUNTY ONLY".
  // holidayFor() keys a calendar by jurisdiction and year, so one `ma`
  // calendar cannot express a day that is a holiday in one county and not in
  // the other thirteen. West Virginia's two lists split by BODY OF RULES
  // (civil vs appellate); this one splits by PLACE, and no field exists for
  // place at all.
  //
  // ENCODED STATEWIDE, DISCLOSED FOR SUFFOLK, and the direction is why:
  // including the two days would roll deadlines in thirteen counties LATE,
  // while omitting them can only ever run EARLY in Suffolk. The same clause
  // also requires Suffolk offices to "be open for business and appropriately
  // staffed" on both days, so whether a Rule 6(a) period rolls off them at all
  // is an open question -- which makes the omission either CORRECT or EARLY,
  // never late, on both readings. SUFFOLK COUNTY IS BOSTON: this is the
  // busiest venue in the Commonwealth and the disclosure says so out loud.
  ma_rcp_6a: { label: 'Mass. R. Civ. P. 6(a)', impl: 'ohio_civ_r_6a',
    short_period_exclusion_days: 7,
    base_period_suffix: '', months_years_suffix: '',
    rollover_suffix_forward: '', rollover_suffix_backward: '' },
  // ── MISSOURI: THE HOLIDAY BASIS IS BY CONVERGENCE, NOT CROSS-REFERENCE ──
  // Mo. R. Civ. P. 44.01(a), verbatim:
  //
  //   "In computing any period of time prescribed or allowed by these rules, by
  //    order of court, or by any applicable statute, the day of the act, event,
  //    or default after which the designated period of time begins to run is not
  //    to be included. The last day of the period so computed is to be included,
  //    unless it is a Saturday, Sunday or a legal holiday, in which event the
  //    period runs until the end of the next day which is neither a Saturday,
  //    Sunday nor a legal holiday. When the period of time prescribed or allowed
  //    is less than seven days, intermediate Saturdays, Sundays and legal
  //    holidays shall be excluded in the computation."
  //
  // THE RULE SAYS "legal holiday" AND NAMES NO STATUTE, and RSMo 9.010 is titled
  // "Public holidays" and never uses the phrase. That is the IDENTICAL lexical
  // gap that helped refuse Kentucky, so it was checked the same way and came out
  // the opposite way:
  //   KENTUCKY  KRS 2.110 lists four days its courts do NOT close for and OMITS
  //             Thanksgiving, so encoding it rolls deadlines LATE. Fatal.
  //   MISSOURI  RSMo 9.010's thirteen days match the State of Missouri's own
  //             published holiday schedule day for day, Thanksgiving included,
  //             with no listed day the state stays open for.
  // Both readings therefore converge on the same thirteen days and neither can
  // roll LATE. The wording gap is a real question of law and belongs in the
  // bundled lawyer's question; it is not a safety problem. See
  // JURISDICTION_COVERAGE, which discloses the basis rather than hiding it.
  //
  // SHORT-PERIOD EXCLUSION AT SEVEN, READ NOT ASSUMED. "less than seven days" is
  // the rule's own wording, and this field is compared with a strict less-than,
  // so 7 is both the literal number in the rule and the right value here. Same
  // as New Jersey, North Carolina, Washington, Massachusetts and West Virginia's
  // appellate rule -- and NOT Tennessee's or Arizona's eleven, which is the
  // number a neighbouring-state analogy would have supplied.
  //
  // BACKWARD IS LEFT BLANK. 44.01(a) speaks only of a period that "begins to
  // run" after an act, event or default and says nothing about counting backward
  // from a hearing. No backward row is seeded and none may be added without a
  // rule that actually defines the direction.
  mo_rule_44_01_a: { label: 'Mo. R. Civ. P. 44.01(a)', impl: 'ohio_civ_r_6a',
    short_period_exclusion_days: 7,
    base_period_suffix: '', months_years_suffix: '',
    rollover_suffix_forward: '', rollover_suffix_backward: '' },
  // ── MINNESOTA: DAYS ARE DAYS, AND THE EXCLUSION IS OPT-IN PER RULE ───────
  // Minn. R. Civ. P. 6.01(a), verbatim on the parts that decide these fields:
  //
  //   "(1) Period Stated in Days or a Longer Unit of Time. When the period is
  //    stated in days or a longer unit of time: (A) exclude the day of the event
  //    that triggers the period; (B) COUNT EVERY DAY, INCLUDING INTERMEDIATE
  //    SATURDAYS, SUNDAYS, AND LEGAL HOLIDAYS; and (C) include the last day of
  //    the period, but if the last day is a Saturday, Sunday, or legal holiday,
  //    the period continues to run until the end of the next day that is not a
  //    Saturday, Sunday, or legal holiday.
  //    (2) Periods Shorter than 7 Days. ONLY IF EXPRESSLY SO PROVIDED by any
  //    other rule or statute, a time period that is less than 7 days may exclude
  //    intermediate Saturdays, Sundays, and legal holidays."
  //
  // NO short_period_exclusion_days FIELD AT ALL, AND THAT IS THE READ. Minnesota
  // took the 2009-federal "days are days" approach, so the default is to count
  // every intermediate day -- like the FRCP family and unlike Ohio, Indiana,
  // Florida, NJ, NC, WA, MA, MO (7), Tennessee and Arizona (11). Setting 7 here
  // because most neighbours use 7 would exclude weekends from every short
  // Minnesota period and push those deadlines LATER than the rule provides.
  //
  // AND THE SHAPE IS DIFFERENT FROM EVERY OTHER SEEDED STATE, which is worth
  // more than the value. 6.01(a)(2) does not set a threshold at all -- it makes
  // the exclusion an OPT-IN that an individual rule or statute may grant. This
  // field is standard-level, so it cannot express "off by default, on for these
  // particular rules". No seeded Minnesota row expressly provides the exclusion,
  // so the absence is correct today; a row that did would need a ROW-LEVEL
  // mechanism that does not exist yet. Do not solve that by setting 7 here.
  //
  // BACKWARD IS EXPRESSLY DEFINED, unlike NJ, NC, WA, MA, MO and WI. 6.01(c):
  // "The 'next day' is determined by continuing to count forward when the period
  // is measured after an event and BACKWARD WHEN MEASURED BEFORE AN EVENT." So
  // the backward suffix is real. No backward row is seeded in this batch even
  // so; the standard is honest about the rule rather than about the row set.
  //
  // THE ROLLOVER KEYS ON THE HOLIDAY LIST, not on courthouse closure. That is
  // what separates Minnesota from Wisconsin, whose 801.15(1)(b) rolls on "a day
  // the clerk of courts office is closed" and uses its holiday list only for the
  // intermediate-day exclusion. Minnesota has a closure limb too -- 6.01(a)(4),
  // inaccessibility of the Court Administrator's office -- but it is ADDITIONAL
  // to the Saturday/Sunday/holiday rollover rather than a replacement for it,
  // which is why omitting it can only ever report EARLY. See JURISDICTION_COVERAGE.
  //
  // NOT MODELLED: 6.01(a)(3) periods stated in HOURS. This engine has no hours
  // unit (calendar_days, business_days, months, years). No hours-based row is
  // seeded; one would be a real addition, not a config change.
  mn_rcp_6_01: { label: 'Minn. R. Civ. P. 6.01', impl: 'frcp_6a',
    base_period_suffix: '(a)(1)', months_years_suffix: '(a)(1)',
    rollover_suffix_forward: '(a)(1)(C)', rollover_suffix_backward: '(c)' },

  // CONNECTICUT. Declared so its one seeded rule resolves to a named standard
  // rather than UNKNOWN_STANDARD. IT DOES NOT COMPUTE TODAY AND IS NOT MEANT
  // TO: no `ct` holiday calendar is loaded, so rollOff returns NOT_PROVISIONED
  // on EVERY date -- it consults the calendar before it looks at the weekday --
  // and no Connecticut deadline is produced at all. That refusal IS the hold on
  // the rollover basis (see below); it is enforced by the missing calendar, not
  // by anyone remembering to leave it out.
  //
  // NO SHORT-PERIOD EXCLUSION, AND FOR ONCE IT IS ON THE RECORD RATHER THAN
  // INFERRED. Sec. 63-2: "Time shall be counted by calendar, not working,
  // days." The phrase "intermediate Saturdays" appears ZERO times in the whole
  // 699-page Practice Book. So no short_period_exclusion_days -- not 7
  // (NJ/NC/WA/MA/MO), not 11 (TN/AZ/WI). This matters more here than usual
  // because Sec. 10-8's summary-process limb is THREE days.
  //
  // THE COUNTING RULE LIVES IN THE APPELLATE CHAPTER, AND THAT IS A DISCLOSED
  // WEAKNESS, NOT A TIDY CITATION. Sec. 63-2 sits under RULES OF APPELLATE
  // PROCEDURE, yet it is the ONLY day-counting provision in the book: the
  // string "first day shall" occurs exactly ONCE, there, and there is no
  // trial-court equivalent under any phrasing searched. Two things argue it
  // still reaches a trial-court filing -- it governs "any documents ... under
  // these rules or an order of the court", and its own rollover sentence names
  // "the office of the clerk of the TRIAL COURT or of the appellate clerk".
  // Neither is conclusive. If 63-2 does NOT reach trial-court pleadings, the
  // first-day/last-day convention here is assumed rather than sourced, and a
  // wrong assumption there computes LATE -- the direction that loses a filing.
  // It is tolerable ONLY because nothing computes: see the refusal above.
  //
  // THE ROLLOVER SUFFIX NAMES BOTH SECTIONS BECAUSE THE RULE IS IN BOTH.
  // 63-2 supplies the counting; Sec. 7-17, under SUPERIOR COURT -- GENERAL
  // PROVISIONS, supplies the trial-court rollover: "If the last day for filing
  // any matter in the clerk's office falls on a day on which such office is not
  // open ... then the last day for filing shall be the next business day upon
  // which such office is open." Citing only 63-2 on the rollover step of a
  // trial-court deadline would send an attorney to the appellate rules for a
  // Superior Court answer.
  //
  // AND THE ROLLOVER KEYS ON CLERK'S-OFFICE CLOSURE, NOT ON A HOLIDAY LIST --
  // THIS IS THE WISCONSIN HAZARD. Neither section names Saturday or Sunday.
  // "Holiday" appears five times in the Practice Book and not once as a
  // definition or a computation rule. Weekends come out right only by accident
  // of fact (clerks' offices are shut then). Encoding Conn. Gen. Stat. Sec. 1-4's
  // statutory holiday list as the calendar would be WRONG IN THE LATE DIRECTION
  // on any listed day a clerk's office is in fact open -- exactly what left
  // Wisconsin gated. The operative artifact is the Judicial Branch's published
  // court-closure schedule, which makes Connecticut ingest-not-derive like NC,
  // NJ, MD and OK.
  //
  // DO NOT ADD A `ct` CALENDAR UNTIL THE FIRST-DAY-CONVENTION SOURCING
  // QUESTION IS ANSWERED -- DOING SO WOULD SILENTLY COMPUTE LATE. That is TWO
  // blockers, not one, and they are independent: (1) does Sec. 63-2 reach
  // Superior Court pleadings at all (the paragraph above this one), and
  // (2) is the calendar built from the Judicial Branch closure schedule
  // rather than the Sec. 1-4 statutory list. Both fail in the LATE direction.
  // Fixing only the second one and shipping a calendar is the specific
  // mistake this comment exists to prevent -- it would look like the hazard
  // had been dealt with while the first-day convention was still assumed.
  // Hard block confirmed on Michael's direction 2026-08-27.
  ct_pb_63_2: { label: 'Conn. Practice Book Sec. 63-2', impl: 'frcp_6a',
    base_period_suffix: '', months_years_suffix: '',
    rollover_suffix_forward: ' with Sec. 7-17', rollover_suffix_backward: '' },

  // UTAH. The first jurisdiction seeded whose ROLLOVER CLAUSE NAMES BOTH
  // WEEKEND DAYS ITSELF, so the standing weekend-coverage check stops at step
  // one and no holiday statute has to be consulted for it. 6(a)(1)(C): "if the
  // last day is a Saturday, Sunday, or legal holiday, the period continues to
  // run until the end of the next day that is not a Saturday, Sunday or legal
  // holiday." Compare Louisiana, where the same shape is affirmatively WRONG.
  //
  // NO SHORT-PERIOD EXCLUSION, STATED AFFIRMATIVELY. 6(a)(1)(B) counts "every
  // day, including intermediate Saturdays, Sundays, and legal holidays" -- the
  // 2009-federal "days are days", like Minnesota. So the field is ABSENT, not
  // zero: six seeded states use 7 and three use 11, and copying either would
  // push every short Utah deadline later than the rule provides.
  //
  // BACKWARD IS EXPRESSLY DEFINED, so the backward suffix is real rather than
  // blank. 6(a)(5): the "next day" is found by "continuing to count forward
  // when the period is measured after an event and BACKWARD WHEN MEASURED
  // BEFORE AN EVENT." Real, like Minnesota's 6.01(c), unlike NJ/NC/WA/MA/MO/WI
  // where it had to be left empty. No backward ROW is seeded in this batch even
  // so -- the standard is honest about the rule, not about the row set.
  //
  // NO SERVICE-EXTENSION STANDARD IS DECLARED, AND THAT IS THE POINT.
  // URCP 6(c) adds SEVEN days -- not three -- but only when service is made
  // "exclusively by mail under Rule 5(b)(3)(C)(i)". This engine carries ONE
  // `service_method` field and cannot express "by mail AND BY NOTHING ELSE",
  // so a caller who says `mail` for a party also served by e-mail would get +7
  // and a LATE date. Seven days is a large overshoot in the direction that
  // loses a filing. NO ROW IN THE UTAH SEED CARRIES A service_extension, and
  // none may until the engine can express exclusive-vs-combined service --
  // tracked as its own engine change, the same way the service-COMPLETION
  // mechanism was, rather than worked around per row. Held on Michael's
  // direction 2026-08-27.
  //
  // NO SERVICE-COMPLETION STANDARD EITHER, for the opposite reason: URCP
  // 5(b)(4) says service by mail or electronic means is "complete upon
  // sending", with no time-of-day condition. That makes the completion date
  // the date the caller already supplies, so a standard here would be a
  // mechanism that never moves anything -- dormant by construction. Missouri's
  // exists because its 5 p.m. rule genuinely shifts the trigger date.
  //
  // THE CALENDAR STOPS AT 2026-12-31 ON PURPOSE. Utah Code 63G-1-301 is
  // superseded 1/1/2027 and the successor moves Juneteenth, breaking URCP
  // 6(a)(6)(E)'s own "third Monday of June" shorthand in eight of the next
  // nine years -- three days apart in 2027. holidayFor returns known:false for
  // an unlisted year, so every 2027+ Utah computation refuses NOT_PROVISIONED
  // by itself. See tools/gen_ut_calendar.py before extending it.
  ut_urcp_6: { label: 'Utah R. Civ. P. 6', impl: 'frcp_6a',
    base_period_suffix: '(a)(1)', months_years_suffix: '(a)(1)',
    rollover_suffix_forward: '(a)(1)(C)', rollover_suffix_backward: '(a)(5)' },

  // NEVADA. Restyled onto the federal model effective 1 March 2019, and the
  // SECOND jurisdiction whose rollover clause names both weekend days itself,
  // after Utah. 6(a)(1)(C): "if the last day is a Saturday, Sunday, or legal
  // holiday, the period continues to run until the end of the next day that is
  // not a Saturday, Sunday, or legal holiday." The standing weekend-coverage
  // check stops at step one; no holiday statute is consulted for it.
  //
  // NO SHORT-PERIOD EXCLUSION. 6(a)(1)(B) counts "every day, including
  // intermediate Saturdays, Sundays, and legal holidays" -- the 2009-federal
  // rule. ABSENT, not zero.
  //
  // BACKWARD IS EXPRESSLY DEFINED by 6(a)(5), so the backward suffix is real
  // rather than the blank NJ/NC/WA/MA/MO/WI carry.
  //
  // THE HOLIDAY DEFINITION IS A SINGLE CLEAN POINTER, and that is worth more
  // than it sounds. 6(a)(6): "'Legal holiday' means any day set aside as a
  // legal holiday by NRS 236.015." There is no in-rule list to reconcile
  // against the statute -- which is exactly what made Utah's Juneteenth
  // question messy, where URCP 6(a)(6)(E) restates the statute in its own words
  // and the 2027 amendment breaks the restatement. Nevada cannot drift that way.
  //
  // NOT MODELLED: 6(a)(2) states periods in HOURS with its own hour-granular
  // rollover, and this engine has no hours unit. 6(a)(4)(A) ends the last day
  // at 11:59 p.m. for electronic filing -- a filing cutoff, not a date shift.
  // 6(a)(3)'s clerk-inaccessibility limb is ADDITIONAL to the rollover rather
  // than a replacement for it (Minnesota's 6.01(a)(4) shape, NOT Wisconsin's),
  // so omitting it can only report EARLY.
  nv_nrcp_6: { label: 'Nev. R. Civ. P. 6', impl: 'frcp_6a',
    base_period_suffix: '(a)(1)', months_years_suffix: '(a)(1)',
    rollover_suffix_forward: '(a)(1)(C)', rollover_suffix_backward: '(a)(5)' },

  // OREGON. The rollover names Saturday SEPARATELY and folds Sunday into the
  // holiday definition: "unless it is a Saturday or a legal holiday, INCLUDING
  // SUNDAY". That drafting is the whole reason Oregon is safe where Louisiana
  // is blocked -- both states' holiday statutes make Sunday a holiday, but only
  // Oregon's procedural rule names Saturday in its own right. isWeekend() is
  // correct here because of how ORCP 10 A is written, not because of ORS 187.
  //
  // SHORT-PERIOD EXCLUSION AT SEVEN, and Oregon states the one thing every
  // other jurisdiction leaves open: the threshold is measured on the period
  // "(WITHOUT REGARD TO SECTION B OF THIS RULE)" -- section B being the service
  // extension. So the 7-day test runs on the BASE period, before the three days
  // are added. That is already how this engine works (the exclusion is applied
  // during base-period counting, before any extension), so the rule and the
  // implementation agree -- but it is asserted in the Oregon test rather than
  // assumed, because Maryland leaves the identical question open and a future
  // change made for Maryland could silently break Oregon.
  //
  // NO BACKWARD PROVISION EXISTS, so the backward suffix is blank -- the
  // NJ/NC/WA/MA/MO/WI position, not Minnesota's, Utah's or Nevada's.
  //
  // A CARVE-OUT WORTH KNOWING: ORCP 10 A ends "This section does not apply to
  // any time limitation governed by ORS 174.120", which is the STATUTORY
  // computation rule for periods fixed by statute rather than by the ORCP.
  // 174.120 counts the same way but has NO short-period exclusion at all, so a
  // statutory Oregon period computed under this standard would wrongly drop
  // intermediate days. Every seeded Oregon row takes its period from the ORCP,
  // so the carve-out is not reached -- but a statutory row must not use this
  // standard.
  or_orcp_10: { label: 'Or. R. Civ. P. 10', impl: 'frcp_6a',
    short_period_exclusion_days: 7,
    base_period_suffix: ' A', months_years_suffix: ' A',
    rollover_suffix_forward: ' A', rollover_suffix_backward: '' },

  // OKLAHOMA. Statutory civil procedure -- the Oklahoma Pleading Code, Title
  // 12 -- so the computation rule is a statute rather than a court rule.
  //
  // IT HAS LOUISIANA'S ROLLOVER SHAPE AND ONE CLAUSE SAVES IT. 2006(A)(1)
  // rolls the last day only if it "is a legal holiday as defined by Section
  // 82.1 of Title 25 ... or any other day when the office of the court clerk
  // does not remain open" -- SATURDAY AND SUNDAY ARE NOT NAMED. That is
  // exactly the structure that BLOCKED Louisiana, where art. 5059 rolls only
  // on "a legal holiday" and R.S. 1:55 makes Saturday a holiday in some
  // parishes only. Oklahoma resolves it in the first eight words of its
  // holiday statute: 25 O.S. 82.1(A) opens "Each Saturday, Sunday", statewide,
  // with no county qualification. So isWeekend() is correct for Oklahoma -- by
  // a different textual route than any common-law state, but correct, and only
  // because of a statute the computation rule points at rather than anything
  // in the computation rule itself.
  //
  // THE SHORT-PERIOD THRESHOLD IS ELEVEN, joining Tennessee, Arizona,
  // Wisconsin and Alabama, and not the 7 of six other states nor Minnesota's,
  // Utah's and Nevada's absence.
  //
  // AND SIX SECTIONS ARE EXPRESSLY CARVED OUT OF THAT EXCLUSION: "Except for
  // the times provided in Sections 765, 990.3, 1148.4, 1148.5, 1148.5A, and
  // 1756 of this title". A row seeded under any of those must count EVERY
  // intermediate day regardless of period length. This is an ENUMERATED
  // opt-out -- narrower and more tractable than Louisiana's open-ended
  // "expressly excluded" and Minnesota's open-ended opt-in -- but a
  // standard-level flag cannot express it, and none of the six is in this
  // batch. SEEDING ONE LATER WITHOUT NOTICING WOULD SILENTLY APPLY AN
  // EXCLUSION THE STATUTE REMOVES, computing LATE.
  //
  // THE CLERK-CLOSURE LIMB APPEARS IN BOTH the rollover and the exclusion, and
  // it is a PARTIAL-closure test -- "does not remain open for public business
  // until the regularly scheduled closing time" -- broader than a simple
  // closed/open test and the same breadth as Oregon's. It is ADDITIONAL to the
  // holiday list rather than a replacement, so omitting it reports EARLY.
  //
  // NO BACKWARD PROVISION, so the backward suffix is blank.
  ok_12_2006: { label: '12 O.S. § 2006', impl: 'frcp_6a',
    short_period_exclusion_days: 11,
    base_period_suffix: '(A)(1)', months_years_suffix: '(A)(1)',
    rollover_suffix_forward: '(A)(1)', rollover_suffix_backward: '' },

  // SOUTH CAROLINA. The rollover names both weekend days AND takes its holiday
  // basis from TWO lists at once: "unless it is a Saturday, Sunday OR A STATE
  // OR FEDERAL HOLIDAY". That union is the first in this platform -- every
  // earlier jurisdiction keys on one list, or on two STATE lists (Wisconsin) --
  // and it is not optional: Juneteenth and Columbus Day are federal holidays
  // and are absent from S.C. Code 53-5-10, so a state-only calendar reports
  // EARLY. The union is built and asserted in tools/gen_sc_calendar.py.
  //
  // SHORT-PERIOD EXCLUSION AT SEVEN -- "when the period of time prescribed or
  // allowed is less than seven days" -- matching NJ, NC, WA, MA, MO and WV
  // appellate, and not TN/AZ/WI's 11, Oklahoma's 11, or the absence in
  // Minnesota, Utah and Nevada.
  //
  // "A HALF HOLIDAY SHALL BE CONSIDERED AS OTHER DAYS AND NOT AS A HOLIDAY" --
  // an express carve-out with no analogue in any seeded state. It is INERT
  // today, because nothing in 53-5-10 is a half holiday, but it is the rule
  // pre-emptively refusing a category rather than an omission, and it must not
  // be quietly dropped if 53-5-10 ever gains one.
  //
  // NO BACKWARD PROVISION. Rule 6(a) addresses only a period that "begins to
  // run" after an act, so the backward suffix is blank -- the NJ/NC/WA/MA/MO/WI
  // position. Rule 6(d)'s ten-day motion notice and two-day affidavit periods
  // are BACKWARD and are therefore NOT seeded, even though the two-day period
  // is the one row that would exercise the seven-day exclusion.
  sc_rcp_6: { label: 'S.C. R. Civ. P. 6', impl: 'frcp_6a',
    short_period_exclusion_days: 7,
    base_period_suffix: '(a)', months_years_suffix: '(a)',
    rollover_suffix_forward: '(a)', rollover_suffix_backward: '' },
  // FOURTEEN. The longest short-period threshold in the platform, and the
  // number is the whole point of giving Arkansas its own standard rather
  // than reusing a neighbour's. Six seeded states use 7, three use 11, and
  // Minnesota, Utah and Nevada have none. Copying any of them computes
  // EARLY on Arkansas periods of 7-13 days, and ARCP 6(c)'s 10-day response
  // and 5-day reply both fall inside that band, so it is load-bearing on
  // real rows rather than academic.
  //
  // DO NOT REASON FROM FRCP 6(a) HERE, even though the Reporter's Notes say
  // Rule 6 is 'practically identical to FRCP 6'. The federal rule abolished
  // the exclusion in 2009; Arkansas moved the other way -- 11 days in 1986
  // 'consistently with the federal rule', and 14 since.
  ar_rcp_6: { label: 'Ark. R. Civ. P. 6', impl: 'frcp_6a',
    short_period_exclusion_days: 14,
    base_period_suffix: '(a)', months_years_suffix: '(a)',
    rollover_suffix_forward: '(a)', rollover_suffix_backward: '' },
  // ELEVEN, matching Tennessee, Arizona and Wisconsin -- NOT the 7 of NJ,
  // NC, WA, MA, MO and SC, and not Arkansas's 14. Wisconsin's own Judicial
  // Council Note explains why the platform sees both numbers: states that
  // tracked the 1985 federal amendment moved 7 -> 11, and the federal rule
  // then abolished the exclusion outright in 2009. The split is a vintage
  // artefact, not a policy difference, which is exactly why it cannot be
  // guessed from a neighbour.
  al_rcp_6: { label: 'Ala. R. Civ. P. 6', impl: 'frcp_6a',
    short_period_exclusion_days: 11,
    base_period_suffix: '(a)', months_years_suffix: '(a)',
    rollover_suffix_forward: '(a)(3)', rollover_suffix_backward: '' },
  // ELEVEN, like Alabama, Tennessee and Arizona.
  //
  // WISCONSIN USES TWO DIFFERENT TESTS IN ONE SUBSECTION, and this standard
  // can only honour one of them. Sec. 801.15(1)(b) rolls the LAST DAY unless
  // it is "a day the clerk of courts office is closed" -- a courthouse-
  // CLOSURE test -- while excluding INTERMEDIATE days on the statutory
  // holiday LIST in 801.15(1)(a). Every other jurisdiction here uses one
  // basis for both.
  //
  // The calendar therefore carries only days on which EVERY county's clerk
  // is closed, read from the court system's own 2026 closure schedule --
  // three days out of the fifteen it lists. That is correct for the rollover
  // test and DELIBERATELY UNDER-INCLUSIVE for the exclusion test, which
  // reports EARLY and never LATE. See JURISDICTION_COVERAGE.wi.
  wi_801_15: { label: 'Wis. Stat. Sec. 801.15', impl: 'frcp_6a',
    short_period_exclusion_days: 11,
    base_period_suffix: '(1)(b)', months_years_suffix: '(1)(b)',
    rollover_suffix_forward: '(1)(b)', rollover_suffix_backward: '' },
  // ── THE THRESHOLD IS 8 AND THAT IS NOT A TYPO. READ BEFORE EDITING. ──
  // Md. Rule 1-203(a): "if the period of time allowed is SEVEN DAYS OR
  // LESS, intermediate Saturdays, Sundays, and holidays are not counted."
  // That is <= 7, which is < 8, and this field is compared with a STRICT
  // less-than. The literal number in the Maryland rule is SEVEN and the
  // correct value here is EIGHT -- the second jurisdiction after Texas
  // ("five days or less" -> 6) where the rule's number and this field's
  // number differ. Writing 7 would stop excluding on exactly the seven-day
  // periods the rule is aimed at, reporting EARLIER than the true deadline.
  //
  // ── AND THE EXCLUSION IS FORWARD-ONLY, WHICH NOTHING ELSE HERE IS. ──
  // Md. Rule 1-203(b) computes a backward period counting "all days prior
  // thereto, INCLUDING intervening Saturdays, Sundays, and holidays" --
  // the (a) exclusion deliberately does not carry across -- and then rolls
  // the latest day BACKWARD to "the first preceding day which is not a
  // Saturday, Sunday, or holiday." Reusing forward logic backward would
  // drop days the rule counts and report LATER than the true date, which
  // on a backward period means telling someone they may still serve after
  // the last lawful day. Hence short_period_exclusion_directions.
  md_rule_1_203: { label: 'Md. Rule 1-203', impl: 'frcp_6a',
    short_period_exclusion_days: 8,
    short_period_exclusion_directions: ['forward'],
    base_period_suffix: '(a)', months_years_suffix: '(a)',
    rollover_suffix_forward: '(a)(1)', rollover_suffix_backward: '(b)' },
  // NO SHORT-PERIOD EXCLUSION, AND THE ABSENCE IS DELIBERATE. K.S.A.
  // 60-206(a)(1)(B) says "count every day, INCLUDING intermediate Saturdays,
  // Sundays and legal holidays" -- Kansas adopted the 2010 restyling that
  // abolished the exclusion federally, so it joins Minnesota, Utah and
  // Nevada in having none at all. Declaring a threshold here would exclude
  // days the statute counts and report LATER than the true deadline, which
  // is the direction that misses a filing. The field is simply absent, the
  // same way it is for the FRCP family.
  ks_60_206: { label: 'K.S.A. 60-206', impl: 'frcp_6a',
    base_period_suffix: '(a)', months_years_suffix: '(a)',
    rollover_suffix_forward: '(a)(1)(C)', rollover_suffix_backward: '' },
  // MISSISSIPPI. Miss. R. Civ. P. 6(a), the whole computation limb verbatim:
  //
  //   "the day of the act, event, or default from which the designated period
  //    of time begins to run shall not be included. The last day of the period
  //    so computed shall be included, unless it is a Saturday, a Sunday, or a
  //    legal holiday, AS DEFINED BY STATUTE, OR ANY OTHER DAY WHEN THE
  //    COURTHOUSE OR THE CLERK'S OFFICE IS IN FACT CLOSED, whether with or
  //    without legal authority ... When the period of time prescribed or
  //    allowed is LESS THAN SEVEN DAYS, intermediate Saturdays, Sundays, and
  //    legal holidays shall be excluded in the computation. In the event any
  //    legal holiday falls on a Sunday, the next following day shall be a
  //    legal holiday."
  //
  // SEVEN, AND IT IS A STRICT LESS-THAN, which is what the field already means
  // at the call site. Same threshold as Ohio, Indiana, Florida, New Jersey,
  // North Carolina, Washington, Massachusetts, Missouri and South Carolina --
  // read independently here, not carried across, because the neighbours
  // disagree wildly (Alabama and Wisconsin 11, Maryland 8, Arkansas 14, Texas
  // 6, and Kansas, Minnesota, Utah and Nevada none at all).
  //
  // NO PER-DIRECTION SPLIT. Unlike Md. Rule 1-203(b), Rule 6(a) says nothing
  // about backward periods at all, so the exclusion is left applying in both
  // directions, which is the plain reading of "the period of time prescribed
  // or allowed is less than seven days".
  //
  // ⚠ NO MISSISSIPPI ROW MAY BE SEEDED BACKWARD WHILE THE CALENDAR IS THE
  // TWO-DAY INTERSECTION. This is the one place where this jurisdiction can
  // compute LATE, and the seed avoids it by construction rather than by luck.
  // The ms calendar deliberately carries only the two holidays Miss. Code Ann.
  // Sec. 3-3-7(2) forbids a county to substitute away (see
  // JURISDICTION_COVERAGE.ms), so it is knowably missing days that really are
  // legal holidays in most counties.
  //
  // Under-inclusion is EARLY, and therefore safe, in both FORWARD mechanisms:
  // a last day that should have rolled forward off a holiday stays where it is
  // (sooner), and a short period that should have excluded a holiday counts it
  // (sooner). COUNTING BACKWARD IT INVERTS IN BOTH. A short backward period
  // excludes fewer days than the rule requires, and a backward last day that
  // should have rolled BACK off a holiday does not roll at all -- each lands
  // CLOSER to the trigger, i.e. LATER than the true last date to act, which is
  // the direction that lets a party serve or file too late.
  //
  // THE LENGTH OF THE PERIOD DOES NOT RESCUE IT. An earlier draft of this seed
  // carried Rule 56(c) -- "the motion shall be served at least ten days before
  // the time fixed for the hearing" -- on the reasoning that ten clears the
  // seven-day threshold so the exclusion never fires. That is true of the
  // exclusion and irrelevant to the ROLLOVER: a hearing on 7 May 2026 counts
  // back to Monday 27 April, Confederate Memorial Day, which this calendar
  // omits because Sec. 3-3-7(2) lets a county trade it away. In a county that
  // still observes it the true last day is Friday 24 April. So Rule 56(c),
  // Rule 6(d)'s five-day motion notice and its one-day opposing affidavit are
  // ALL omitted. Seeding a Mississippi backward row needs a complete
  // county-level calendar, not a longer period.
  //
  // THE SUFFIX IS BARE "(a)". Rule 6 is not subdivided past the letter -- the
  // computation, the rollover, the short-period exclusion and the Sunday shift
  // are four sentences of one unnumbered paragraph.
  ms_r_civ_p_6: { label: 'Miss. R. Civ. P. 6', impl: 'frcp_6a',
    short_period_exclusion_days: 7,
    base_period_suffix: '(a)', months_years_suffix: '(a)',
    rollover_suffix_forward: '(a)', rollover_suffix_backward: '(a)' },
  // NEW MEXICO. Rule 1-006(A) NMRA, restyled in 2014 to follow the federal
  // rule and amended again effective 31 December 2024. Two paragraphs matter
  // here and the second one is the reason this jurisdiction can do something
  // Mississippi could not:
  //
  //   (A)(2)(a) "When the period is stated in days but the number of days is
  //             TEN (10) DAYS OR LESS ... exclude intermediate Saturdays,
  //             Sundays, and legal holidays"
  //   (A)(6)    "The 'NEXT DAY' is determined by continuing to count FORWARD
  //             when the period is measured after an event and BACKWARD when
  //             measured before an event."
  //
  // ELEVEN, NOT TEN. "Ten days or less" is <= 10, which is < 11, and this
  // field is a strict less-than at the call site. Third jurisdiction after
  // Texas ("five days or less" -> 6) and Maryland ("seven days or less" -> 8)
  // where the rule's own number and the field's number differ, and the one
  // place writing the rule's number would silently drop the ten-day rows --
  // Rule 1-012(A)(1) and (A)(2) are both exactly ten.
  //
  // (A)(6) IS AN EXPRESS DIRECTION RULE AND IT IS RARE. Only Fla. R. Gen.
  // Prac. & Jud. Admin. 2.514(a)(5) says the same thing among the states
  // seeded. It is what makes a SHORT BACKWARD row safe here: Rule 1-055(B)'s
  // three-day notice of an application for default judgment is exactly the
  // shape Mississippi had to refuse, and New Mexico can seed it because the
  // rule states which way "next day" runs and the calendar is the judiciary's
  // own complete published list rather than a defensive intersection.
  //
  // THE HOLIDAY DEFINITION IS THE KANSAS SHAPE, NOT THE WISCONSIN ONE.
  // (A)(7): "'Legal holiday' means the day that the following are observed BY
  // THE JUDICIARY", then a named list, then "(b) any other day observed as a
  // holiday by the judiciary". New Mexico's district courts are state
  // administered and the Chief Justice publishes one schedule for the whole
  // branch, so that schedule IS the statutory test rather than a proxy for it.
  //
  // ONE CARVE-OUT THE ENGINE CANNOT SEE, recorded so nobody encodes it later:
  // (A)(2)(b) says the ten-day exclusion "shall not apply to any statutory
  // notice that is required to be given prior to the filing of an action" --
  // the committee commentary gives the Uniform Owner-Resident Relations Act's
  // three-day notice to pay rent as the example. No such notice is seeded, and
  // one must not be seeded on this standard: it would be excluded when the
  // rule says to count straight through.
  nm_1_006: { label: 'Rule 1-006 NMRA', impl: 'frcp_6a',
    short_period_exclusion_days: 11,
    base_period_suffix: '(A)', months_years_suffix: '(A)',
    rollover_suffix_forward: '(A)(1)(c)', rollover_suffix_backward: '(A)(6)' },
  // IDAHO. I.R.C.P. 2.2(a)(1), and note the NUMBER: Idaho restyled its civil
  // rules in 2016 and moved computation from Rule 6 to RULE 2.2. A citation to
  // "Idaho Rule 6" is a citation to nothing since 1 July 2016.
  //
  //   "(1) Generally. When the period is stated in days or a longer unit of
  //    time: (A) exclude the day of the event that triggers the period;
  //    (B) COUNT EVERY DAY, INCLUDING INTERMEDIATE SATURDAYS, SUNDAYS, AND
  //    LEGAL HOLIDAYS; and (C) include the last day of the period, but if the
  //    last day is a Saturday, Sunday, or legal holiday, the period continues
  //    to run until the end of the next day that is not a Saturday, Sunday, or
  //    legal holiday."
  //
  // NO SHORT-PERIOD EXCLUSION, AND THE ABSENCE IS DELIBERATE. Idaho took the
  // 2009 federal restyling wholesale, so it joins Minnesota, Utah, Nevada and
  // Kansas in having none at all. Declaring any threshold here would exclude
  // days the rule counts and report LATER than the true deadline. The field is
  // simply absent, and the test asserts it is undefined rather than small --
  // which matters more in Idaho than usual, because its two Rule 12(a)(2) rows
  // are FOURTEEN days and its Rule 59 rows are fourteen: under Alabama's or
  // Wisconsin's 11 they would still count straight through, but under
  // Arkansas's 14 they would not.
  //
  // THE HOLIDAY REFERENT IS A STATUTE THE RULE NEVER NAMES. I.R.C.P. 2.2 says
  // "legal holiday" and stops; nothing in the Idaho Rules of Civil Procedure
  // or the Idaho Appellate Rules defines it. Idaho Code Sec. 73-108 ("Holidays
  // enumerated") is the referent, and Sec. 67-5302(15)(a) confirms the chain by
  // pointing back at it in terms -- "Holidays are enumerated in section 73-108,
  // Idaho Code." See JURISDICTION_COVERAGE.id for why that still leaves one
  // date contested.
  //
  // NO DIRECTION RULE, SO NO BACKWARD ROW IS SEEDED. 2.2(a)(1)(C) rolls to "the
  // NEXT day" and says nothing about a period measured before an event -- the
  // Mississippi shape, not the New Mexico one, where 1-006(A)(6) settles it
  // expressly. Idaho has real backward periods worth having (Rule 55(a)(1) and
  // 55(b)(2) each require three days' notice, and Rule 56(b)(2) runs 28/14/7
  // days before a hearing) and none of them is seeded. The reason is in the
  // coverage entry: one annually-recurring date is contested, and an omitted
  // holiday that should have rolled a BACKWARD deadline further back leaves it
  // closer to the trigger, i.e. later than the rule allows.
  id_ircp_2_2: { label: 'I.R.C.P. 2.2', impl: 'frcp_6a',
    base_period_suffix: '(a)', months_years_suffix: '(a)',
    rollover_suffix_forward: '(a)(1)(C)', rollover_suffix_backward: '' },
  // NEBRASKA. THE COMPUTATION RULE IS A STATUTE AND THE COURT RULE SAYS SO.
  // Neb. Ct. R. Pldg. § 6-1106(a): "Neb. Rev. Stat. § 25-2221 governs the
  // computation of time periods." So unlike Idaho, where the referent had to be
  // traced, Nebraska's rule names its own statute in its first line.
  //
  // Neb. Rev. Stat. § 25-2221, first paragraph, verbatim:
  //
  //   "Except as may be otherwise more specifically provided, the period of
  //    time within which an act is to be done in any action or proceeding shall
  //    be computed by excluding the day of the act, event, or default after
  //    which the designated period of time begins to run. The last day of the
  //    period so computed shall be included unless it is a Saturday, a Sunday,
  //    or a day during which the offices of courts of record may be legally
  //    closed as provided in this section, in which event the period shall run
  //    until the end of the next day on which the office will be open."
  //
  // NO SHORT-PERIOD EXCLUSION. There is no intermediate-day rule at all -- the
  // statute excludes the trigger day, counts to the last day, and rolls. Sixth
  // seeded jurisdiction with none, after Minnesota, Utah, Nevada, Kansas and
  // Idaho.
  //
  // THE ROLLOVER TEST IS "A DAY DURING WHICH THE OFFICES OF COURTS OF RECORD
  // MAY BE LEGALLY CLOSED AS PROVIDED IN THIS SECTION" -- and the same section
  // then enumerates those days. The list IS the test, which is the Kansas and
  // New Mexico shape rather than the Wisconsin one, and it is stronger here
  // than in either: the statute does not point outward at another list, it
  // carries its own.
  //
  // NO SUFFIXES. § 25-2221 is a single unsubdivided section; there is no
  // paragraph to cite past the number, so every suffix is empty rather than
  // guessed.
  //
  // NOTE FOR ANYONE ADDING A BACKWARD ROW: the statute says the period "shall
  // run until the end of the NEXT day on which the office will be open" and
  // says nothing about a period measured before an event -- the Mississippi and
  // Idaho shape, not New Mexico's. No backward row is seeded. The calendar here
  // is materially more complete than Idaho's, so the case is weaker, but the
  // question has not been read out of any Nebraska text and is not being
  // guessed.
  ne_25_2221: { label: 'Neb. Rev. Stat. § 25-2221', impl: 'frcp_6a',
    base_period_suffix: '', months_years_suffix: '',
    rollover_suffix_forward: '', rollover_suffix_backward: '' },
  // HAWAIʻI. Haw. R. Civ. P. 6(a) -- and the referent is EXPRESS, which is
  // exactly what Idaho's was not. The rule ends: "As used in these rules,
  // 'holiday' shall mean any day designated as such pursuant to SECTION 8-1 OF
  // THE HAWAIʻI REVISED STATUTES." Idaho's I.R.C.P. 2.2 says "legal holiday"
  // and stops, and three competing lists had to be sorted out. Hawaiʻi names
  // its section.
  //
  // SEVEN, a strict less-than: "When the period of time prescribed or allowed
  // is LESS THAN 7 DAYS, intermediate Saturdays, Sundays and holidays shall be
  // excluded in the computation." Same threshold as ten other seeded states,
  // read here rather than carried.
  //
  // NOTE WHAT IT ROLLS OFF: "a Saturday, a Sunday or A HOLIDAY" -- the rule
  // uses the bare word "holiday" throughout and never says "legal holiday",
  // which is why the definitional sentence at the end of 6(a) is load-bearing
  // rather than decorative.
  //
  // NO DIRECTION RULE, SO NO BACKWARD ROW IS SEEDED -- the Mississippi, Idaho
  // and Nebraska shape, not New Mexico's. Hawaiʻi has two backward periods
  // worth having and neither is seeded: Rule 6(d) requires a written motion and
  // notice of hearing to be served NOT LESS THAN 18 DAYS before the hearing,
  // which is the longest motion-notice period of any seeded jurisdiction, and
  // opposing affidavits not less than 8 days before. Both clear the seven-day
  // threshold, so the short-period exclusion is not the obstacle -- the missing
  // direction rule is.
  //
  // RULE 6 WAS AMENDED VERY RECENTLY AND TWICE: "further amended July 9, 2025,
  // effective January 1, 2026; further corrected December 19, 2025; further
  // amended May 21, 2026, effective July 1, 2026." The text encoded here is the
  // current one. WHAT those amendments changed was NOT determined -- the
  // judiciary publishes an amendment history but no redline in this document,
  // and guessing would be worse than saying so.
  hi_hrcp_6: { label: 'Haw. R. Civ. P. 6', impl: 'frcp_6a',
    short_period_exclusion_days: 7,
    base_period_suffix: '(a)', months_years_suffix: '(a)',
    rollover_suffix_forward: '(a)', rollover_suffix_backward: '' },
  // NEW HAMPSHIRE. N.H. Super. Ct. R. 2, quoted here IN FULL because it is the
  // shortest computation rule on this platform and the quote is the argument:
  //
  //   "In computing any period of time prescribed or allowed by these rules, by
  //    order of court, or by applicable law, the day of the act, event, or
  //    default after which the designated period of time begins to run shall
  //    not be included. The last day of the period so computed shall be
  //    included, unless it is a Saturday, Sunday, or a legal holiday, in which
  //    event the period shall extend until the end of the next day that is not
  //    a Saturday, Sunday, or a legal holiday AS SPECIFIED IN RSA CH. 288, AS
  //    AMENDED."
  //
  // Two sentences. That is the whole rule.
  //
  // NO SHORT-PERIOD EXCLUSION AT ANY LENGTH -- there is no sentence excluding
  // intermediate Saturdays, Sundays or holidays from a short period, so every
  // period counts straight through. Joins MN/UT/NV/KS/ID/NE. It matters more
  // here than the tally suggests: FOUR seeded New Hampshire rows are TEN days,
  // which Arkansas's 14-day threshold and Alabama's and Wisconsin's 11 would
  // all have excluded weekends from. The field is left undefined rather than
  // set to something small, and a test asserts that.
  //
  // ★ THE HOLIDAY REFERENT NAMES A CHAPTER, NOT A SECTION, AND THAT DISTINCTION
  // ALREADY DECIDED A DATE ONCE. Haw. R. Civ. P. 6(a) named HRS Sec. 8-1 by
  // number, so HRS Sec. 8-2's weekend observance sat OUTSIDE the reference and
  // Hawaiʻi's calendar omits the shifted Friday as a reading. Rule 2 reaches
  // "RSA CH. 288", so RSA 288:2 is INSIDE the reference and is carried. It then
  // turns out not to matter in 2026, for a reason worth stating: RSA 288:2 is a
  // SUNDAY RULE ONLY -- "When any holiday listed in RSA 288:1 falls on Sunday,
  // the following day shall be observed as a holiday" -- with no Saturday limb
  // at all. 4 July 2026 is a Saturday and there is no Friday 3 July observance
  // here, not by interpretation but because no clause could produce one. Idaho
  // and Nebraska both carry 3 July 2026 from Saturday-shift clauses inside the
  // very sections their rules cite. Four jurisdictions, three reasons, one date.
  //
  // NO SUBDIVISIONS, SO EVERY SUFFIX IS EMPTY RATHER THAN GUESSED. Rule 2 is a
  // single unlettered, unnumbered paragraph -- the Nebraska position.
  //
  // ★ AND THERE IS NO SERVICE-EXTENSION STANDARD TO PAIR WITH THIS ONE. New
  // Hampshire is the FIRST seeded jurisdiction with no mailed-service extension
  // of any kind: the phrases "shall be added", "additional days" and
  // "prescribed period" do not occur anywhere in the civil rules or in the
  // Supplemental Rules for Electronic Filing. The reason is structural rather
  // than an omission -- New Hampshire runs its periods from FILING and from THE
  // DATE ON THE CLERK'S NOTICE where the FRCP family runs them from SERVICE, so
  // there is nothing to compensate for. Rule 12(e) and Rule 43 each name the
  // delivery method in the same sentence and then decline to let it matter. Do
  // NOT add an entry to SERVICE_EXTENSION_STANDARDS for nh; a three-day
  // extension copied from a neighbour reports LATE on every New Hampshire
  // deadline.
  //
  // NO DIRECTION RULE, SO NO BACKWARD ROW IS SEEDED -- Rule 2 extends to "the
  // NEXT day" and says nothing about a period measured before an event, the
  // Mississippi/Idaho/Nebraska/Hawaiʻi shape rather than New Mexico's. The one
  // being given up is unusual enough to name: Rule 26(b) requires deposition
  // notice "at least 3 days, EXCLUSIVE OF THE DAY OF SERVICE AND THE DAY OF
  // CAPTION" -- a period carrying its own both-endpoints-excluded convention
  // that Rule 2 does not supply.
  //
  // NO NON-EXTENDABLE LIST, WHICH IS ALSO UNUSUAL. Hawaiʻi's Rule 6(b) freezes
  // six rules and reaches into the appellate rules; Idaho's 2.2(b)(3) freezes
  // six. Rule 2 says nothing about extension at all, and Rule 1(d) lets the
  // court "waive the application of any rule" as justice may require.
  nh_scr_2: { label: 'N.H. Super. Ct. R. 2', impl: 'frcp_6a',
    base_period_suffix: '', months_years_suffix: '',
    rollover_suffix_forward: '', rollover_suffix_backward: '' },
  // Delaware SUPERIOR COURT Civil Rule 6(a). THE COURT IS PART OF THE NAME AND
  // NOT DECORATION: Del. Ct. Ch. R. 6 is a DIFFERENT computation on the same
  // subject, and a Chancery deadline computed under this standard is computed
  // under the wrong rule. The two differ on the rollover basis, on what "legal
  // holiday" means, on whether backward periods are addressed at all, and on
  // whether an hours unit exists; they agree only on the 11-day threshold.
  // Chancery is deliberately NOT seeded and would take its own standard,
  // de_ct_ch_r_6. See docs/sairnlaw-delaware-deadline-seed-gate.md sec. 5.4.
  //
  // ELEVEN, joining Alabama and Wisconsin -- not the 7 of NJ, NC, WA, MA, MO
  // and SC, and not Arkansas's 14. It is load-bearing here rather than
  // theoretical: Rule 59(b)'s new-trial period is TEN days, so it sits under
  // the threshold and excludes intermediate weekends and holidays.
  //
  // THE RULE NAMES BOTH WEEKEND DAYS ITSELF -- "unless it is a Saturday or
  // Sunday, or other legal holiday" -- so the [Sat, Sun] default is correct and
  // NO weekend_days declaration belongs here. Checked deliberately, because
  // this landed the same day the per-jurisdiction weekend flag shipped and
  // 1 Del. C. sec. 501(a)(11) makes SATURDAYS a statutory holiday while never
  // listing Sunday at all -- the exact inverse of Louisiana. That inversion
  // changes nothing, because Rule 6(a) does not defer the weekend question to
  // the statute the way La. C.C.P. art. 5059(A) does.
  //
  // NOT MODELLED, and the reason it is a disclosure rather than a refusal:
  // the rule also rolls off "any other day on which the office of the
  // Prothonotary is closed" and runs to the next day that office is OPEN.
  // That limb REPLACES nothing -- it sits beside the weekend/holiday test in
  // the same sentence -- so omitting a closure day returns the earlier
  // unrolled date, which is EARLY and safe. Same limb Indiana T.R. 6(A)
  // carries. See JURISDICTION_COVERAGE.de.
  //
  // NO SUBDIVISION SUFFIXES. Rule 6(a) is one unnumbered paragraph carrying
  // the exclusion, the rollover and the holiday definition together, so every
  // suffix is empty rather than invented -- the New Hampshire treatment.
  de_super_ct_civ_r_6a: { label: 'Del. Super. Ct. Civ. R. 6(a)', impl: 'frcp_6a',
    short_period_exclusion_days: 11,
    base_period_suffix: '', months_years_suffix: '',
    rollover_suffix_forward: '', rollover_suffix_backward: '' },
  // Montana DISTRICT COURT Rule 6(a). THE COURT IS PART OF THE NAME FOR THE
  // SAME REASON IT IS IN DELAWARE'S, and the trap here is arguably sharper
  // because both rules are numbered 6 and both sit in Title 25 of the same
  // code. Mont. Just. & City Ct. R. Civ. P. 6 (Title 25 ch. 23) is a DIFFERENT
  // computation on the same subject: it defines "legal holiday" not at all, has
  // no clerk-inaccessibility limb, no hours unit, no backward "next day" rule,
  // and its mail extension is MAIL ONLY and lengthens the period rather than
  // running after it expires. Justice and City Court is deliberately NOT seeded
  // and would take its own standard, mt_jc_r_6. See
  // docs/sairnlaw-montana-deadline-seed-gate.md sec. 6.
  //
  // NO short_period_exclusion_days, AND THAT IS THE LOAD-BEARING ABSENCE.
  // Rule 6(a)(1)(B) says "count every day, INCLUDING intermediate Saturdays,
  // Sundays, and legal holidays" -- the post-2009 federal text. Montana has no
  // threshold at all, so a 7 borrowed from NJ/NC/WA/MA/MO/SC or an 11 borrowed
  // from its own neighbour Delaware would silently lengthen every period under
  // that threshold and report LATE. Three seeded rows are 14 days and two are
  // 7; all five would move.
  //
  // THE RULE NAMES BOTH WEEKEND DAYS ITSELF -- "if the last day is a Saturday,
  // Sunday, or legal holiday" -- so the [Sat, Sun] default is correct and NO
  // weekend_days declaration belongs here. Checked deliberately, because
  // MCA 1-1-216(1)(a) makes each SUNDAY a statutory legal holiday and never
  // lists Saturday at all. That is Louisiana's shape, not Delaware's inverse of
  // it, and it changes nothing here for the same reason it changed nothing
  // there: Rule 6(a)(1)(C) does not defer the weekend question to the statute.
  //
  // FEDERAL SUBDIVISION NUMBERING, VERIFIED RATHER THAN ASSUMED FROM THE
  // FAMILY: (a)(1)(A)-(B) is the base count, (a)(1)(C) the rollover, and
  // (a)(5) the backward "next day" rule -- which Montana ADDRESSES EXPRESSLY,
  // unlike Delaware's Superior Court rule. Two seeded rows are backward and
  // depend on it.
  //
  // NOT MODELLED, and disclosed rather than refused: Rule 6(a)(3) extends the
  // time for filing when the clerk's office is inaccessible. It is an
  // ADDITIONAL limb sitting beside the weekend/holiday test, not a replacement
  // for it -- the Minnesota/Utah shape -- so omitting an inaccessible day
  // returns the earlier unrolled date, which is EARLY and safe. Contrast
  // Wisconsin, where the closure test REPLACES the holiday test and the
  // omission could not be made safe. See JURISDICTION_COVERAGE.mt.
  mt_rcp_6a: { label: 'Mont. R. Civ. P. 6(a)', impl: 'frcp_6a',
    base_period_suffix: '(1)(A)-(B)', months_years_suffix: '(1)(C)',
    rollover_suffix_forward: '(1)(C)', rollover_suffix_backward: '(5)' }
};

// A MALFORMED weekend_days FAILS AT LOAD, LOUDLY, AND TAKES THE MODULE WITH
// IT. The alternative -- ignoring a bad value and using [Sun, Sat] -- would
// silently restore the exact behaviour a jurisdiction declared wrong, and it
// would do so on a code path nothing observes. A standard is in-code data, so
// a defect here is a bug rather than bad input, and a bug that stops the
// engine loading is caught by the first test that requires it.
//
// NOTE ON DIRECTION, because "fails safe" is not a property this one has: a
// missing roll makes a FORWARD deadline earlier (safe) and a BACKWARD one
// later (unsafe). There is no fallback that is safe in both directions, which
// is the second reason this refuses rather than defaults.
(function validateWeekendDayDeclarations() {
  var bad = [];
  Object.keys(COMPUTATION_STANDARDS).forEach(function (k) {
    var defect = weekendDaysDefect(COMPUTATION_STANDARDS[k].weekend_days);
    if (defect) bad.push(k + '.weekend_days ' + defect);
  });
  if (bad.length) {
    throw new Error('deadline-engine: invalid weekend_days declaration(s): ' + bad.join('; '));
  }
})();

// ── Per-jurisdiction coverage disclosure ──────────────────────────────────
// A jurisdiction whose calendar is knowably INCOMPLETE in a way the engine
// cannot refuse on declares it here, and the text rides on the top level of
// every successful computation for that jurisdiction rather than being buried
// in one rule's authority note.
//
// The distinction that decides whether a gap belongs here or in a refusal:
//   REFUSED   the gap can make the engine report a date that is LATE, or the
//             engine cannot tell whether it would. A late date loses a filing.
//             New Jersey's missing 2027 and Kentucky's holiday basis are both
//             this, and both refuse.
//   DISCLOSED the gap can only ever make the engine report a date that is
//             EARLY. Filing before the true deadline is safe; being told a
//             deadline has passed when it has not is a usability cost, not a
//             malpractice one. Refusing here would buy no safety.
// Nothing is added to this table without deciding which of the two it is.
//
// ── THE THIRD CATEGORY, AND IT IS AN EXCEPTION TO THE RULE ABOVE ──────────
// Added 2026-09-01 on Michael's direction, after an audit found the one entry
// that does not fit the dichotomy hiding inside an 'early' label.
//
//   DISCLOSED-LATE  the gap can make the engine report a date that is LATE,
//                   and refusing is not available because the trigger is
//                   discretionary, per-office and published nowhere this
//                   engine can read. It carries direction: 'late' AND a
//                   late_exposure block naming the authority and the concrete
//                   risk, so it cannot be read as one more safe omission.
//
// THERE IS EXACTLY ONE, AND THAT IS THE POINT. Alabama's Ala. Code
// Sec. 1-3-8(f)(1) lets a state office STAY OPEN on a state holiday on sixty
// days' notice; if a court did that and this engine rolled off the day anyway,
// the date shown is LATER than the true deadline. Every other entry here is
// EARLY-only. A second one must be a deliberate decision, not a default -- the
// invariant below refuses to load an entry that is ambiguous about which it is.
//
// `direction` IS WORST-CASE, NOT TYPICAL. Alabama's other two gaps are EARLY
// and safe; the field still reads 'late', because a caller switching on it is
// asking "can this be late?" and for Alabama the answer is yes.
var JURISDICTION_COVERAGE = {
  ks: {
    complete: false,
    direction: 'early',
    summary: 'Kansas legal holidays declared ad hoc by the President or Congress after the Judicial Branch publishes its annual list are NOT modelled, and the chief justice may suspend these computation rules in an emergency. This date may be EARLIER than the true deadline, never later.',
    detail: "K.S.A. 60-206(a)(6) defines \"legal holiday\" as any day declared a holiday by the President, by Congress, by the Kansas legislature, OR \"any day observed as a holiday by order of the Kansas supreme court\". This calendar is the Judicial Branch's own published annual list, which is the fourth limb and the one that governs the courts. TWO GAPS, BOTH EARLY. (1) An AD HOC day declared by the President or Congress after the annual list is published -- a national day of mourning, say -- is a legal holiday under the first two limbs and is not here; omitting it reports EARLIER than the true deadline. (2) A half holiday is expressly NOT a holiday (\"A half holiday is considered as other days and not as a holiday\") and is correctly absent, which is noted so nobody adds one. WHAT IS NOT A GAP, and the contrast with Wisconsin is the point: the schedule says a court \"may defer observing a holiday\" and that a district court \"may remain open on any of these designated holidays\" with the chief judge's and the judicial administrator's approval. That changes practical access, NOT the statutory definition -- 60-206(a)(6) keys on the day being OBSERVED BY ORDER OF THE SUPREME COURT, statewide, not on whether a particular courthouse opened. Wisconsin keys its rollover on actual closure and therefore could not use its list at all; Kansas keys on the order, so the list IS the legal test. Finally, the chief justice may extend or suspend these computation rules entirely during an emergency under 60-206(e) and K.S.A. 20-172, which no engine can anticipate."
  },
  md: {
    complete: false,
    direction: 'early',
    summary: 'Maryland also rolls the last day when the clerk\'s office is closed or closed for PART of a day, which is per-court and not knowable in advance. This date may be EARLIER than the true deadline, never later.',
    detail: "Md. Rule 1-203(a)(2) rolls the last day on a SECOND, non-holiday trigger the calendar cannot express: \"the act to be done is the filing of a paper in court and the office of the clerk of that court on the last day of the period is not open, OR IS CLOSED FOR A PART OF THE DAY.\" That reaches weather, emergencies and partial-day closures, is published per court at mdcourts.gov/administration/closingsdelays rather than in any annual list, and is not knowable in advance. Omitting it can only make a computed date EARLIER than the true one. THE HOLIDAY LIST ITSELF IS INGESTED, NOT DERIVED, and is complete for the year it covers: Rule 1-202(l) points at State Personnel and Pensions Sec. 9-201, whose paragraph (14) reaches \"each other day that the President of the United States or the Governor designates for general cessation of business\" -- arbitrary by construction, and the Judiciary has published TWO observed days for one holiday in a past year. So the calendar is taken from the Judiciary's own published list rather than generated, and a year it does not cover is REFUSED rather than derived. NOTE ALSO THE WRONG-SOURCE TRAP, recorded because the obvious statute is the wrong one twice over: General Provisions Sec. 1-302 rolls only on \"a Sunday or legal holiday\" with no Saturday roll (reporting EARLY), and Sec. 1-111 adds Good Friday, Lincoln's Birthday, Maryland Day and Defenders' Day, which are NOT court holidays (reporting LATE). Rule 1-203's own committee note settles it: \"This section supersedes Code, General Provisions Article, Sec. 1-302 to the extent of any inconsistency.\" The correct chain is Rule 1-203 -> Rule 1-202(l) -> SPP Sec. 9-201."
  },
  // ADDED 2026-09-01 on Michael's direction: JURISDICTION_COVERAGE is the
  // contract for an EARLY-direction omission, and Utah and Nevada are migrated
  // onto it. Both previously declared NO entry and asserted that absence in
  // their own suites, on the view that their gaps were "row-level". An audit
  // the same day measured that claim and it did not hold -- only 2 of Utah's 9
  // rows and 2 of Nevada's 10 carried any omission-flavoured authority note,
  // and the ones sampled explained rule STRUCTURE rather than naming these
  // omissions, so a caller was told through neither channel. The majority of
  // seeded states already used this table; these two now match them.
  de: {
    complete: false,
    direction: 'early',
    summary: 'SUPERIOR COURT ONLY -- the Court of Chancery is a different computation and is not seeded. Delaware also rolls the last day off any day the Prothonotary office is closed, and its holiday definition reaches days appointed by the Governor or the Chief Justice; neither is modelled, and Sussex County Return Day is omitted. Every omission makes this date EARLIER than the true deadline, never later.',
    detail: "SCOPE FIRST, BECAUSE IT IS THE ONE THAT COULD BE READ AS COVERAGE NOBODY OFFERED: these rows are Del. Super. Ct. Civ. R. 6(a) and the Superior Court civil rules. Del. Ct. Ch. R. 6 is a DIFFERENT computation -- it rolls off Saturday, Sunday and legal holidays with Register in Chancery inaccessibility as a SEPARATE additional limb, defines legal holiday as days declared by the Governor or identified in 1 Del. C. sec. 501 with NO Chief Justice limb, addresses backward periods expressly in 6(a)(4), and carries an hours unit in 6(a)(2). The two agree only on the 11-day short-period threshold. A Chancery deadline must not be computed from these rows. THE PROTHONOTARY LIMB IS NOT MODELLED: Rule 6(a) rolls the last day off \"any other day on which the office of the Prothonotary is closed\" and runs to the next day that office is OPEN, which is per-county and unknowable in advance; omitting it returns the earlier unrolled date and is EARLY. THE HOLIDAY DEFINITION HAS AN OPEN-ENDED LIMB: \"legal holidays\" are those \"provided by statute or appointed by the Governor or the Chief Justice\", and appointed days are underivable -- the Idaho and Hawaii shape. SUSSEX COUNTY RETURN DAY IS OMITTED, and it is unsafe in BOTH directions if modelled naively: 1 Del. C. sec. 501(a)(13) makes it a holiday only in Sussex County and only \"after 12:00 Noon\", so it is county-scoped like Massachusetts's Suffolk County AND a half day, and treating it as a full statewide rolling day would report LATE. Omitting it reports EARLY in Sussex County and is exactly correct in New Castle and Kent. For 2026 that day is Thursday 5 November. WHAT IS NOT OMITTED, and is worth stating because the neighbouring state answered it the other way: THE GENERAL ELECTION DAY IS CARRIED. Sec. 501(a)(12) makes \"the day of the General Election as it biennially occurs\" a holiday, and Del. Const. art. V sec. 1 fixes the general election \"biennially on the Tuesday next after the first Monday in the month of November\" -- the same term, in a constitutional provision, one reference away. New Hampshire's equivalent day was OMITTED because RSA ch. 652 never defines the term its holiday statute uses and dating it required a second statute using a different one. Delaware has no such gap, so the day is a citation rather than a reading: Tuesday 3 November 2026."
  },
  ut: {
    complete: false,
    direction: 'early',
    summary: 'Utah omits the clerk-inaccessibility rollover, two party-status rules the engine has no field for, the inmate mailbox rule, and governor-proclaimed days. Every omission makes this date EARLIER than the true deadline, never later. The calendar covers 2026 ONLY -- any other year is refused rather than derived.',
    detail: "URCP 6(a)(3)'s clerk's-office INACCESSIBILITY rollover is ADDITIONAL to the Saturday/Sunday/holiday rollover rather than a replacement for it -- the Minnesota 6.01(a)(4) shape, NOT Wisconsin's, where the closure test REPLACES the holiday test -- so omitting it can only report EARLY. URCP 6(d) runs the period from the SERVICE date instead of the FILING date for a party who is both unrepresented AND without an e-filing account, which is keyed on party status and this engine has no field for it. URCP 6(e)'s inmate mailbox rule, and its separate 'calculated from the date the papers are received by the court' limb, are likewise unmodelled. On holidays: limb (M) and Utah Code Sec. 63G-1-301(5) governor's proclamations are open-ended and underivable, and Good Friday is omitted on the reading that limb (M) sweeps the statute. THE CALENDAR IS CAPPED AT 2026 ON PURPOSE and a later year is REFUSED with NOT_PROVISIONED rather than generated, so the cap cannot silently produce a wrong date."
  },
  nv: {
    complete: false,
    direction: 'early',
    summary: 'Nevada omits presidentially appointed days of public fast or thanksgiving, the hours-granular rollover in NRCP 6(a)(2), the electronic-filing cutoff in 6(a)(4)(A), and the clerk-inaccessibility limb in 6(a)(3). Every omission makes this date EARLIER than the true deadline, never later.',
    detail: "The calendar is NRS 236.015(1) in full -- including NEVADA DAY, which the statute fixes at October 31 but directs be observed on the last Friday in October, and FAMILY DAY, the Friday following the fourth Thursday in November, neither of which exists on any other calendar here -- with the NRS 236.015(3) both-ways observation shift applied. That shift is enumerated to exactly five days (1 January, 19 June, 4 July, 11 November and 25 December), so it is NOT applied to the others; that is the statute's own limit and not an omission. WHAT IS OMITTED, all EARLY: presidentially appointed days of public fast or thanksgiving, which are ad hoc and not encodable; NRCP 6(a)(2), which states periods in HOURS with its own hour-granular rollover, and this engine has no hours unit; 6(a)(4)(A), which ends the last day at 11:59 p.m. for electronic filing -- a filing cutoff rather than a date shift; and 6(a)(3)'s clerk-inaccessibility limb, which like Utah's is ADDITIONAL to the ordinary rollover rather than a replacement for it."
  },
  wi: {
    complete: false,
    direction: 'early',
    summary: 'Wisconsin rolls the last day on COURTHOUSE CLOSURE, not on the statutory holiday list, and its clerks are county officers who diverge. This calendar carries only the three days every county is closed statewide, so a date may be EARLIER than the true deadline, never later.',
    detail: "Wis. Stat. Sec. 801.15(1)(b) uses TWO DIFFERENT TESTS in one subsection, and no single calendar can honour both. The LAST DAY rolls unless it is \"a day the clerk of courts office is closed\" -- a courthouse-CLOSURE test. INTERMEDIATE days, in periods under 11 days, are excluded on the statutory holiday LIST in 801.15(1)(a). Wisconsin's clerks of circuit court are COUNTY officers, and the court system's own 2026 Circuit Court Closure Schedule shows they genuinely diverge: of the fifteen holidays it lists, 67 of 72 counties are not closed all day on Juneteenth, 69 of 72 on Indigenous Peoples' / Columbus Day, and 60 of 72 on Washington's Birthday. Encoding the statutory list for the rollover would therefore roll deadlines in counties whose courthouse was OPEN -- LATER than the statute allows, the direction that loses a filing. THIS CALENDAR INSTEAD CARRIES ONLY THE STATEWIDE INTERSECTION: the three days on which EVERY county is marked closed all day -- New Year's Day, Memorial Day and Thanksgiving Day. That is correct for the rollover test and deliberately UNDER-inclusive for the exclusion test, so a computed date may be EARLIER than the true deadline and can never be later. TWO FURTHER GAPS, both also EARLY: Sec. 995.20 makes the municipal election day a legal holiday in every 1st class city (Milwaukee) and lets counties of 750,000 or more provide holidays by ordinance, neither of which a jurisdiction+year calendar can express; and a county closed for weather or a local event is not here either. THE CALENDAR IS 2026 ONLY -- the court system publishes no 2027 schedule yet, and a later year would have to be derived from the statutory list, which is the thing this design exists to avoid. Before relying on a Wisconsin date that falls on or near a listed holiday, check that county's own closure schedule at wicourts.gov/courts/circuit."
  },
  al: {
    complete: false,
    // WORST CASE, not typical -- see the DISCLOSED-LATE note above. Two of
    // Alabama's three gaps are EARLY and safe; this reads 'late' because one
    // of them is not, and that is the only answer a caller can act on.
    direction: 'late',
    late_exposure: {
      authority: 'Ala. Code Sec. 1-3-8(f)(1)',
      summary: 'A state office may STAY OPEN on a state holiday on sixty days written notice. If a court does that and this engine rolls the deadline off that day anyway, the date shown is LATER than the true deadline.',
      why_not_refused: 'The trigger is discretionary, per-office, and published nowhere this engine can read, so there is no signal to refuse on. Refusing every Alabama date that lands on or near a listed holiday would withdraw the whole jurisdiction to guard against a rare exercise of a notice provision.',
      caller_action: 'Before relying on an Alabama date that falls on or near a listed holiday, confirm that the court was in fact closed.'
    },
    summary: 'Alabama county-scoped holidays and weather closures are NOT modelled (both EARLY, safe). ONE EXCEPTION RUNS LATE and is disclosed rather than modelled: Ala. Code 1-3-8(f)(1) lets an office stay OPEN on a state holiday on 60 days notice, and this engine would roll off that day anyway.',
    detail: "The calendar is the union Ala. R. Civ. P. 6(a)(4) requires -- the eleven days the rule names, plus \"any other day declared a holiday by the President or Congress or as prescribed by Sec. 1-3-8\" -- derived for 2026 and checked by day-of-week. TWO GAPS RUN EARLY AND ARE SAFE. (1) MARDI GRAS: Sec. 1-3-8(e)(1) makes it a holiday and closes all state offices in BALDWIN AND MOBILE COUNTIES only, and a jurisdiction+year calendar cannot express a two-county day; omitting it is correct in the other 65 counties and EARLY in those two. (2) Rule 6(a)(3) also rolls the last day when \"weather or other conditions make the clerk's office inaccessible\", which is unknowable in advance; omitting it is EARLY. ONE GAP RUNS LATE, AND IT IS FLAGGED RATHER THAN BURIED: Sec. 1-3-8(f)(1) lets a state office STAY OPEN on a state holiday on sixty days' written notice. If a court did that and this engine rolled the deadline off that day anyway, the date shown would be LATER than the true deadline -- the direction that loses a filing. It is discretionary, per-office and not published anywhere this engine can read, so it cannot be modelled; it is disclosed instead. The same question in a sharper form is WISCONSIN, and the two were resolved differently -- corrected 2026-09-01, this sentence previously said Wisconsin was not seeded and it has been since August. Wis. Stat. 801.15(1)(b) rolls on \"a day the clerk of courts office is closed\" rather than on any list, and that state's own 2026 closure schedule shows counties genuinely open on listed holidays; Wisconsin resolved it by carrying ONLY the three days every county is closed, which is under-inclusive and therefore EARLY. Alabama cannot do the same, because its exposure is a discretionary notice provision rather than a published schedule to intersect. Before relying on an Alabama date that falls on or near a listed holiday, confirm that the court was in fact closed."
  },
  ar: {
    complete: false,
    direction: 'early',
    summary: 'Arkansas court closures beyond the statewide legal holidays are NOT modelled, and the calendar covers 2026 only. This date may be EARLIER than the true deadline, never later.',
    detail: "The calendar is the union Ark. R. Civ. P. 6(a) requires -- \"designated as a holiday by the President or Congress of the United States or designated by the laws of this State\" -- transcribed for 2026 from the Arkansas Secretary of State's own 2026 State Holidays sheet and 5 U.S.C. 6103(a). TWO THINGS IT DOES NOT ENCODE, both of which can only push the true deadline LATER. (1) Rule 6(a) also rolls off \"other day when the clerk's office is closed\", and rolls forward only to \"the next day that the clerk's office is open\" -- both limbs are per-court and unknowable in advance, and the 2003 amendment added them to codify Honeycutt v. Fanning, 349 Ark. 324, 78 S.W.3d 96 (2002). (2) Ark. Code Ann. 1-5-101(a) includes \"an employee's birthday\" as a state holiday; it is a floating personal-leave day rather than a calendar date, Rule 6(a) incorporates the state list wholesale without filtering, and it is not modellable either way. If the computed date falls on a day the relevant clerk's office was in fact closed, the true deadline rolls to the next open day and is LATER than shown -- confirm the local court's own closure schedule before relying on a date that falls near one. SEPARATELY, the calendar is 2026 ONLY: the Secretary of State publishes no 2027 sheet yet, and Ark. Code Ann. 1-5-101(b)'s observance shift has never been read on a primary source, so later years are REFUSED rather than derived."
  },
  va: {
    complete: false,
    direction: 'early',
    summary: 'Virginia court closures beyond the statewide statutory holidays are NOT modelled. This date may be EARLIER than the true deadline, never later.',
    detail: 'The calendar encodes Saturdays, Sundays and the legal holidays in Va. Code § 2.2-3300, which § 17.1-207(A) requires every clerk\'s office to close for statewide. It does NOT encode two further categories that Va. Code § 1-210(B) also rolls off, because neither is knowable in advance: (1) § 1-210(F) makes any day the Governor authorizes the closing of state government a legal holiday, announced ad hoc; (2) § 17.1-207 lets a clerk also close on locality-adopted holidays, on Christmas Eve, and on days a chief or presiding judge authorizes for a health or safety threat — all discretionary and all per-locality. If the computed date below falls on a day the relevant clerk\'s office was in fact closed, the true deadline rolls to the next open day and is LATER than shown. Confirm the local court\'s own closure schedule before relying on a date that falls near one of these.'
  },
  // MASSACHUSETTS. The FIRST gap in this table that is GEOGRAPHIC rather than
  // temporal or discretionary: two days are legal holidays in one county and
  // in no other, and a calendar keyed by jurisdiction+year has no field for
  // place. Named explicitly rather than folded into a general "local closures"
  // sentence, because a Massachusetts practitioner can check this one against
  // a single fact -- which county the matter is in -- and act on it.
  ma: {
    complete: false,
    direction: 'early',
    summary: 'SUFFOLK COUNTY (Boston) has two legal holidays no other Massachusetts county has, and they are NOT modelled. In Suffolk County this date may be EARLIER than the true deadline, never later. Everywhere else in the Commonwealth this calendar is complete.',
    detail: 'The calendar encodes Saturdays, Sundays and the statewide legal holidays in Mass. G.L. c. 4, § 7, Cl. 18, which Mass. R. Civ. P. 6(a) incorporates by name. Clause 18 additionally makes Evacuation Day (17 March) and Bunker Hill Day (17 June) legal holidays "with respect to Suffolk county only". A holiday calendar here is keyed by jurisdiction and year and has no notion of county, so those two days are omitted. THE OMISSION IS SAFE IN BOTH DIRECTIONS OF THE OPEN QUESTION: if a Rule 6(a) period does roll off them in Suffolk, this date is EARLY by one day when it lands on or just after 17 March or 17 June; if it does not — and the same clause requires all state and municipal offices in Suffolk to "be open for business and appropriately staffed" on both days, which is a real argument that it does not — then this date is simply correct. It is never late. Outside Suffolk County the two days are not legal holidays at all and nothing is missing. Rule 6(a) also reaches "any other day appointed as a holiday by the President or the Congress of the United States", which is ad hoc and not knowable in advance; that limb is likewise not encoded and fails in the same EARLY direction. If your matter is in Suffolk County and this date falls on or shortly after 17 March or 17 June, confirm it by hand.'
  },
  // MISSOURI. Two gaps, both EARLY, and one of them is a divergence between a
  // statute and what the state administratively observes -- a shape no other
  // jurisdiction in this table has yet.
  mo: {
    complete: false,
    direction: 'early',
    summary: 'Missouri court closures beyond the statutory list in RSMo 9.010 are NOT modelled, including the substitute days the state observes when a holiday falls on a Saturday. This date may be EARLIER than the true deadline, never later.',
    detail: 'The calendar encodes Saturdays, Sundays and the thirteen public holidays in RSMo 9.010. Two things it does NOT encode, both of which can only ever make this date EARLIER than the true deadline: (1) ADMINISTRATIVELY OBSERVED SUBSTITUTE DAYS. RSMo 9.010 shifts a holiday only "when any of such holidays falls upon Sunday" and says nothing about Saturday, but the State of Missouri observes a substitute weekday anyway — for example Friday 3 July 2026 for a Saturday 4 July 2026. The statute creates no such substitute, so it is not encoded; if the courthouse is in fact shut on that observed day, the true deadline rolls to the next open day and is LATER than shown. (2) THE BASIS ITSELF IS BY CONVERGENCE, NOT BY CROSS-REFERENCE. Mo. R. Civ. P. 44.01(a) rolls off "a legal holiday" and names no statute, while RSMo 9.010 is titled "Public holidays". The two are treated as the same list because the days in 9.010 match the holiday schedule published by the State of Missouri day for day, with Thanksgiving included and no listed day the state stays open for — so both readings of "legal holiday" produce the same thirteen days and neither can roll a deadline LATE. That convergence was checked, not assumed, precisely because the identical wording gap in Kentucky (KRS 2.110, also titled "Public holidays") DIVERGES from what its courts do and fails in the LATE direction. If a computed date falls on or just after the observed substitute for a Saturday holiday, confirm the closure schedule of the local court before relying on it.'
  },
  // MINNESOTA. Three gaps, all EARLY -- and one INFERENCE whose error direction
  // is LATE, which is disclosed as an inference rather than presented as fact.
  // That last part is why this entry reads differently from the other three:
  // Virginia, Massachusetts and Missouri all disclose things the engine does not
  // model, whereas Minnesota also discloses something the engine DOES model on a
  // reading that a lawyer has not confirmed.
  mn: {
    complete: false,
    direction: 'early',
    summary: 'Three Minnesota closure categories are NOT modelled and can only make this date EARLIER, never later. Separately, Indigenous Peoples Day IS counted on a reading of Rule 6.01(d) that has not been confirmed by counsel — if that reading is wrong, a date landing near the second Monday in October could be LATE.',
    detail: 'The calendar encodes Saturdays, Sundays and the eleven holidays in Minn. Stat. 645.44 subd. 5, which Minn. R. Civ. P. 6.01(d) incorporates by name. THREE THINGS ARE NOT ENCODED, ALL OF WHICH CAN ONLY REPORT EARLY: (1) THE FRIDAY AFTER THANKSGIVING. 645.44 subd. 5(a) gives non-executive branches, including the judiciary, the OPTION whether to observe it, and Rule 6.01(d) second limb does not reach it because the U.S. mail operates that day. Omitting it is the safe default; if the Judiciary does observe it, a deadline landing there rolls later than shown. (2) ONE-OFF DAYS THE U.S. MAIL DOES NOT OPERATE for reasons other than a federal holiday, which Rule 6.01(d) counts but which are not knowable in advance. (3) DAYS THE COURT ADMINISTRATOR OFFICE IS INACCESSIBLE under Rule 6.01(a)(4), which extends filing to the first accessible day. Note that limb is ADDITIONAL to the Saturday/Sunday/holiday rollover rather than a replacement for it, which is exactly why omitting it is safe here and why Minnesota does not have the problem Wisconsin does. AND ONE INFERENCE, DISCLOSED AS SUCH: INDIGENOUS PEOPLES DAY, the second Monday in October, IS encoded. The judiciary merely has the OPTION to observe it under 645.44 subd. 5(a), but Rule 6.01(d) independently counts any day that the U.S. mail does not operate, and that Monday is the federal Columbus Day on which mail does not run. This engine therefore treats it as a legal holiday regardless of the branch option. THAT IS A READING OF THE RULE AND NOT A QUOTED HOLDING. It is the only place in this jurisdiction where the engine could be LATE rather than early, and it is the one item here worth confirming with counsel. If a computed date falls on or just after the second Monday in October, or near the Friday after Thanksgiving, check it by hand.'
  },
  ms: {
    complete: false,
    direction: 'early',
    summary: 'The Mississippi calendar carries only the TWO holidays a county is forbidden by statute to substitute away — the third Monday in January and 11 November. Every other Mississippi court holiday is omitted on purpose, so this date may be EARLIER than the true deadline, never later. Confirm the relevant county courthouse\'s own schedule before relying on a date that falls near any other holiday.',
    detail: 'THREE STATUTES HAVE TO AGREE BEFORE A DAY CAN GO IN THIS CALENDAR, AND FOR MOST MISSISSIPPI HOLIDAYS THEY DO NOT. (1) Miss. R. Civ. P. 6(a) rolls the last day off "a legal holiday, AS DEFINED BY STATUTE, or any other day when the courthouse or the clerk\'s office is IN FACT CLOSED, whether with or without legal authority." (2) Miss. Code Ann. Sec. 3-3-7(1) supplies that definition — ten days — but opens "EXCEPT AS OTHERWISE PROVIDED IN SUBSECTION (2)", and Sec. 3-3-7(2) lets the governing authorities of ANY municipality or county declare, by order spread upon its minutes, "Mardi Gras Day or any one (1) other day during the year, to be a legal holiday" IN LIEU OF any one of them — expressly excepting only the third Monday in January (Robert E. Lee\'s and Dr. Martin Luther King, Jr.\'s birthdays) and the eleventh day of November (Armistice or Veterans\' Day). (3) Miss. Code Ann. Sec. 25-1-99 then makes closure mandatory — "the courthouse SHALL be closed on all state holidays as set forth in Section 3-3-7" — but only for the days that are still Sec. 3-3-7 holidays in that county. THIS IS NOT THEORETICAL. Jackson County publishes a ten-item holiday schedule that lists GOOD FRIDAY, which is not in Sec. 3-3-7 at all, and omits the last Monday in April (Confederate Memorial Day), which is: a one-for-one Sec. 3-3-7(2) substitution, on the record, in a real county. A statewide calendar carrying 27 April 2026 would roll a Jackson County deadline off a day that courthouse was OPEN, and report LATER than Rule 6(a) allows. That is the direction that loses a filing, so the day is not carried. THE CALENDAR IS THEREFORE THE STATUTORY INTERSECTION: the two days Sec. 3-3-7(2) forbids any county to trade away. New Year\'s Day, Washington\'s Birthday, Confederate Memorial Day, National Memorial Day and Jefferson Davis\'s birthday, Independence Day, Labor Day, Thanksgiving and Christmas are all ABSENT, and every one of those absences reports EARLY. FOUR FURTHER GAPS, ALL EARLY. (a) Sec. 25-1-99 says the courthouse "MAY be closed on the Friday immediately preceding" a Saturday holiday — permissive, per county. 4 July 2026 is a Saturday and the Supreme Court closed the Gartin Justice Building on Friday 3 July, but no county is obliged to; that Friday is not here. (b) Thanksgiving is "the day fixed by proclamation by the Governor", and Sec. 25-1-99 leaves it to each board of supervisors whether to close for "those holidays created by executive order of the Governor" — the Governor\'s customary extra Thanksgiving-Friday and Christmas-Eve/New-Year\'s-Eve days are discretionary county by county and are not here. (c) Rule 6(a)\'s "in fact closed, whether with or without legal authority" limb reaches weather, emergencies and local closures, which no annual calendar can express. (d) A county that HAS adopted Mardi Gras or another substitute day has a holiday this calendar does not carry; omitting it is also early. THE SUNDAY SHIFT IS MANDATORY AND IS MODELLED WHERE IT BITES: Sec. 3-3-7(1) and Rule 6(a) both say a legal holiday falling on a Sunday makes the next day a legal holiday. No Sec. 3-3-7 holiday falls on a Sunday in 2026, so the shift is dormant this year rather than absent. 2026 ONLY: a later year is REFUSED rather than derived. THE ONE PLACE MISSISSIPPI COULD COMPUTE LATE IS CLOSED BY CONSTRUCTION, NOT BY LUCK: under-inclusion only reports EARLY while the count runs FORWARD. Counting BACKWARD it inverts — a period under seven days excludes fewer intermediate holidays than Rule 6(a) requires, and a last day that should have rolled back off an omitted holiday does not roll at all — so both land closer to the trigger, i.e. LATER than the true last date to act. NO MISSISSIPPI ROW IS SEEDED BACKWARD AT ALL. Rule 6(d)\'s five-day motion notice, its one-day opposing affidavit and Rule 56(c)\'s ten-day service of a summary-judgment motion are all omitted — including the ten-day one, whose length clears the seven-day exclusion threshold and does nothing about the rollover limb (a hearing on 7 May 2026 counts back to Monday 27 April, Confederate Memorial Day, which this calendar omits). Seeding a Mississippi backward row needs a complete county-level calendar, not a longer period.'
  },
  nm: {
    complete: false,
    direction: 'early',
    summary: 'The New Mexico calendar is the Chief Justice\'s own published 2026 branch holiday schedule and is complete for that year, but Rule 1-006(A)(4) separately extends a filing deadline whenever the court is closed or unavailable for filing — weather, technology, or anything else — which no annual calendar can express. This date may be EARLIER than the true deadline, never later. 2027 is REFUSED rather than derived.',
    detail: 'THE CALENDAR IS THE STATUTORY TEST HERE, NOT A PROXY FOR IT, and that is worth stating because the two most recent states seeded were the opposite. Rule 1-006(A)(7) NMRA: "\'Legal holiday\' means the day that the following are observed BY THE JUDICIARY", then eleven named days, then "(b) any other day observed as a holiday by the judiciary." New Mexico\'s district courts are state administered and the Chief Justice publishes ONE schedule for the whole branch, so the schedule is the legal fact the rule points at — the Kansas shape. Wisconsin and Mississippi both key on something a county can vary, which is why their calendars are deliberately under-inclusive intersections and this one is not. THE 2026 SCHEDULE IS TRANSCRIBED, NOT DERIVED, from the memorandum of Chief Justice David K. Thomson dated 19 November 2025, and every one of its eleven 2026 dates was checked against its printed weekday. TWO OF THEM CANNOT BE DERIVED FROM ANY RULE: Presidents\' Day is observed on FRIDAY 27 NOVEMBER 2026, the day after Thanksgiving — Rule 1-006(A)(7)(a) says so in a parenthetical, "(traditionally observed on the day after Thanksgiving)", and no other seeded jurisdiction moves a holiday across the calendar like that — and Independence Day is observed on FRIDAY 3 JULY 2026 because 4 July is a Saturday. WHAT IS NOT MODELLED, AND IT IS ALWAYS EARLY: Rule 1-006(A)(4) extends the time for FILING whenever "the court is closed or is unavailable for filing at any time that the court is regularly open", which the committee commentary says contemplates "weather, technological problems, or other circumstances", and which a person relying on it must be prepared to demonstrate. That is per-court and unknowable in advance; omitting it can only make a computed date sooner than the true one. Nor is Rule 1-006(A)(3)\'s HOURS arithmetic modelled — no seeded row is stated in hours. Nor is Rule 1-006(A)(5)\'s definition of when the last day ends, which is midnight for electronic filing and closing time for everything else: this engine returns a DATE, and on that date the cut-off differs by filing method. 2027 IS REFUSED RATHER THAN DERIVED, and the temptation here is unusually specific: the 2026 memorandum announces one 2027 date, New Year\'s Day on Friday 1 January 2027. Building a 2027 calendar out of that single entry would let 2027 deadlines compute against a calendar missing ten of its eleven days, which reads as an answer rather than as the refusal it should be. THE ONE PLACE A READING WAS MADE RATHER THAN QUOTED: Rule 1-006(C) grants three days after service by mail, facsimile or court-facility deposit, and says nothing about whether it reaches service of PROCESS. Rule 1-005(A) governs "every pleading subsequent to the original complaint", original process is Rule 1-004, and Rule 1-006(C) defines its own third method by cross-reference into Rule 1-005(C)(1)(e) — so no row triggered by service of the summons and complaint carries the extension. Withholding it reports EARLY; granting it on a mailed summons would report LATE.'
  },
  id: {
    complete: false,
    direction: 'early',
    summary: 'Idaho publishes THREE different holiday lists that do not agree, and this calendar is the one the rule points at — Idaho Code Sec. 73-108. It omits JUNETEENTH, which the Secretary of State publishes as a state holiday and some Idaho courts close for, because Sec. 73-108 does not enumerate it. It also omits any day appointed ad hoc by the President or the Governor. Every omission can only make this date EARLIER than the true deadline, never later. No backward row is seeded, for the same reason. Check any Idaho date falling on or just after 19 June by hand.',
    detail: 'THREE LISTS, AND THEY DISAGREE IN BOTH DIRECTIONS. (1) IDAHO CODE Sec. 73-108, "Holidays enumerated", is what I.R.C.P. 2.2\'s undefined term "legal holiday" refers to — nothing in the Idaho Rules of Civil Procedure or the Idaho Appellate Rules defines it, and Idaho Code Sec. 67-5302(15)(a) confirms the chain by saying so in terms: "Holidays are enumerated in section 73-108, Idaho Code." That list has ELEVEN entries and NO JUNETEENTH, and it carries BOTH observance shifts as mandatory statute: "Any legal holiday that falls on Saturday, the preceding Friday shall be a holiday and any legal holiday enumerated herein other than Sunday that falls on Sunday, the following Monday shall be a holiday." (2) THE SECRETARY OF STATE\'S published State Holidays list DOES carry Juneteenth on Friday 19 June 2026, and does NOT apply the Saturday shift — it prints Independence Day as Saturday 4 July. So it disagrees with the statute in both directions at once. (3) ACTUAL COURT CLOSURES are a third set again: the Idaho Supreme Court published a release headed "Idaho Courts to be Open July 2 & 6" for 2026, keeping courts open as essential services on days other parts of state government close, while at least one county trial court publishes a 2026 schedule that DOES close for Juneteenth. THIS CALENDAR IS SET (1), THE STATUTE, AND IS DELIBERATELY UNDER-INCLUSIVE. Juneteenth is the contested date: it is not enumerated in Sec. 73-108, so it could only be a legal holiday through that section\'s open limb — "every day appointed by the President of the United States, or by the governor of this state, for a public fast, thanksgiving, or holiday" — which is a proclamation this engine cannot read. Omitting it means a forward deadline landing on 19 June is reported as due that day when the true deadline may roll to the 22nd: EARLIER, which is safe. Adding it would roll a deadline off a day that may be fully countable: LATER, which is not. The same reasoning omits every other ad-hoc presidential or gubernatorial day. WHAT IS IN AND WHY IT COULD NOT BE COPIED: FRIDAY 3 JULY 2026 IS A LEGAL HOLIDAY BY STATUTE, because 4 July 2026 is a Saturday and the shift is mandatory — the Secretary of State\'s own list does not show it. COLUMBUS DAY, the second Monday in October, IS enumerated and IS carried, unlike Oregon, which omits it. The Sunday-to-Monday limb is mandatory and simply dormant in 2026: no Sec. 73-108 holiday falls on a Sunday this year. NO BACKWARD ROW IS SEEDED, AND IDAHO HAS GOOD ONES. Rule 55(a)(1) requires three days\' written notice before entry of DEFAULT — unusual, most states require notice only before default JUDGMENT — Rule 55(b)(2) requires three days before the default-judgment hearing, and Rule 56(b)(2) runs 28, 14 and 7 days before a summary-judgment hearing, with the motion itself due 90 days before trial. None is seeded. Under-inclusion is EARLY only while the count runs forward; counting backward, a holiday that should have rolled the date further from the trigger and does not leaves it CLOSER, which is later than the rule allows. With Juneteenth genuinely contested and recurring every year, that is not a risk worth taking for a three-day notice period. Seeding Idaho backward rows needs the Juneteenth question answered, not a longer period. ONE MORE GAP, ALSO EARLY: Rule 2.2(a)(2) extends the time for FILING whenever "the clerk\'s office is inaccessible", which is per-court and unknowable in advance, and is a separate limb from the holiday list rather than part of it. 2027 IS REFUSED rather than derived — the Sec. 73-108 rules would generate it, but the ad-hoc limb and the Juneteenth question would still be open, and a generated year hides that behind a confident answer.'
  },
  ne: {
    complete: false,
    direction: 'early',
    summary: 'The Nebraska calendar is the list Neb. Rev. Stat. Sec. 25-2221 carries in its own text, and it is one of the fullest on the platform \u2014 Arbor Day, Juneteenth, Columbus/Indigenous Peoples\' Day and the day after Thanksgiving are all in it. What it cannot express is the statute\'s two open limbs: a specific court closed by order of the Chief Justice, and days declared by proclamation of the Governor. Both are unknowable in advance, and omitting them can only make this date EARLIER, never later. 2027 is REFUSED rather than derived.',
    detail: 'THE STATUTE CARRIES ITS OWN LIST, WHICH IS UNUSUAL AND IS WHAT MAKES THIS CALENDAR STRONG. Neb. Ct. R. Pldg. Sec. 6-1106(a) says \"Neb. Rev. Stat. Sec. 25-2221 governs the computation of time periods\", and Sec. 25-2221 then rolls the last day off \"a day during which the offices of courts of record may be legally closed AS PROVIDED IN THIS SECTION\" \u2014 and enumerates those days in the next sentence. The rollover test and the holiday list are the same text, so there is no chain to trace and no second publisher to disagree with. Contrast Idaho, seeded the same day, where the rule left \"legal holiday\" undefined and three different lists competed. IT IS ONE OF THE FULLEST LISTS SEEDED: New Year\'s Day; MLK; President\'s Day; ARBOR DAY, the last Friday in April, which appears on no other calendar in this platform and which Nebraska invented; Memorial Day; JUNETEENTH; Independence Day; Labor Day; \"Indigenous Peoples\' Day and Columbus Day\" as one day under two names; Veterans Day; Thanksgiving; THE DAY AFTER THANKSGIVING, enumerated in the statute itself; and Christmas. Both observance shifts are mandatory statute in both directions \u2014 Sunday to the following Monday, Saturday to the preceding Friday \u2014 so Friday 3 July 2026 is DERIVED rather than transcribed. THE CONTRAST WITH IDAHO IS EXACT, AND THEY ARE NEIGHBOURS: Idaho Code Sec. 73-108 has NO Juneteenth and NO day after Thanksgiving; Nebraska has both, plus Arbor Day. Three days of difference between two adjacent statutory lists, which is why neither may be read across. THE FEDERAL-OVERRIDE CLAUSE IS REAL, UNIQUE, AND DORMANT IN 2026. Sec. 25-2221 ends: \"If the date designated by the state for observance of any legal holiday pursuant to this section, EXCEPT VETERANS DAY, is different from the date of observance of such holiday pursuant to a FEDERAL holiday schedule, the FEDERAL holiday schedule shall be observed.\" No other seeded jurisdiction subordinates its own dates to the federal calendar. Every 2026 date was checked against the federal schedule and none diverges, so the clause changes nothing this year \u2014 but it is live law, it is not modelled, and a year in which the two schedules split would need it applied by hand. Veterans Day is expressly carved out of it and therefore always takes the state date. TWO OPEN LIMBS, BOTH EARLY, NEITHER MODELLABLE: \"days on which a specifically designated court is closed BY ORDER OF THE CHIEF JUSTICE of the Supreme Court\", which is per-court rather than statewide and is the only place Nebraska resembles Wisconsin; and \"all days declared by law or PROCLAMATION OF THE GOVERNOR to be holidays\". Omitting either means a deadline landing on such a day is reported as due that day when the true one rolls: earlier, and safe. NOTE THE STATUTE SAYS COURTS \"MAY BE CLOSED\" ON THESE DAYS, NOT MUST, and then designates them \"nonjudicial days\". The rollover test keys on that legal designation rather than on whether a particular courthouse opened, so a court sitting on a nonjudicial day does not unmake the roll \u2014 the same reasoning that let Kansas use its published list and stopped Wisconsin using its. NO BACKWARD ROW IS SEEDED. The statute says the period \"shall run until the end of the NEXT day on which the office will be open\" and says nothing about a period measured before an event \u2014 the Mississippi and Idaho shape, not New Mexico\'s. This calendar is materially more complete than Idaho\'s so the case is weaker here, but the direction question has not been read out of any Nebraska text and is not being guessed. 2027 IS REFUSED rather than derived, even though the statutory rules would generate it mechanically, because the two open limbs and the federal-override clause would still be unresolved and a generated year hides that behind a confident answer. A CURRENCY WARNING THAT IS NOT ABOUT HOLIDAYS: the Nebraska Judicial Branch publishes the PRIOR versions of both Article 11 and Article 3 alongside the current ones \u2014 correctly labelled, fully intact, and one click away. The 1 January 2025 amendments changed real numbers: the post-motion responsive pleading went from 20 days to 21, and the court-ordered reply from 15 days to 21. Every seeded row carries the current number with an effective_from of 2025-01-01, so a pre-2025 trigger REFUSES rather than answering with a number that was not yet law.'
  },
  fl: {
    complete: false,
    direction: 'early',
    summary: 'Florida rolls the last day off any day \"within a time extended by ORDER OF THE CHIEF JUSTICE\" -- the hurricane mechanism -- and off any day observed as a holiday by the CLERK\'S OFFICE or designated by the CHIEF JUDGE. None of the three can be known in advance and none is modelled. A Florida date from this engine is correct only in the absence of such an order; during hurricane season that is a real caveat, not a formality. Every omission makes this date EARLIER than the true deadline, never later.',
    detail: 'THREE UNKNOWABLE ROLLOVER SOURCES, ALL IN ONE RULE. Fla. R. Gen. Prac. & Jud. Admin. 2.514 reaches the chief justice\'s emergency orders in THREE separate places, not one. (a)(1)(C): \"include the last day of the period except if the last day is Saturday, Sunday, a legal holiday, OR FALLS WITHIN A TIME EXTENDED BY ORDER OF THE CHIEF JUSTICE, then the last day will fall on the next day that is not Saturday, Sunday, a legal holiday, or any period of time extended through an order of the chief justice.\" (a)(3)(C) says the same for periods stated in HOURS. (a)(6)(B) then defines \"legal holiday\" to include \"any day observed as a holiday BY THE CLERK\'S OFFICE or as designated by the CHIEF JUSTICE OR CHIEF JUDGE\" -- which is a third and a fourth source again, and the chief-JUDGE limb is per-circuit rather than statewide, the only place Florida resembles Wisconsin. THIS IS FLORIDA\'S HURRICANE MECHANISM AND IT IS USED. The Supreme Court of Florida issues administrative orders extending time in affected circuits after a storm, and a day inside such an order is treated exactly like a holiday by (a)(1)(C). No engine can read an order that has not issued, and no calendar can carry a date that depends on one. WHY THE DIRECTION IS EARLY, AND THE CONDITION THAT MAKES IT SO. Omitting a day that should have been rolled off means the engine returns the unrolled, sooner date -- filing early is safe. That holds because EVERY SEEDED FLORIDA ROW IS FORWARD AND NO SHORTER THAN 20 DAYS: none is backward, none is stated in hours, and none is under the 7-day threshold at 2.514(a)(2). If a backward Florida row is ever added, THIS REASONING STOPS BEING TRUE -- 2.514(a)(5) defines \"next day\" as counting backward for a period measured before an event, and an omitted holiday on a backward count leaves the date CLOSER to the trigger, which is later than the rule allows. Re-read this entry before seeding one. THE CALENDAR IS THE RULE\'S NINE OBSERVANCES, NOT THE STATE\'S HOLIDAY LIST. 2.514(a)(6)(A) enumerates exactly nine days set aside by Fla. Stat. 110.117 -- New Year\'s Day, Martin Luther King, Jr.\'s Birthday, Memorial Day, Independence Day, Labor Day, Veterans\' Day, Thanksgiving Day, THE FRIDAY AFTER THANKSGIVING DAY, and Christmas Day -- and the rule reaches only those, not all of 110.117. Florida\'s list is genuinely shorter than Illinois\'s fifteen or the federal eleven, and padding it to match a neighbour would extend real deadlines that Florida law does not extend. The both-way observance shift in 110.117(1) IS modelled: a holiday falling on Saturday is observed the preceding Friday, on Sunday the following Monday. Calendars cover 2026 through 2031. TWO MORE THINGS NOT MODELLED, NEITHER AFFECTING A SEEDED ROW. 2.514(a)(3)\'s HOURS arithmetic -- no seeded Florida row is stated in hours. And 2.514(a)(4)\'s split cut-off, \"11:59:59 p.m., eastern time for electronic filing or for service by any means\" versus \"when the clerk\'s office is scheduled to close\" for everything else: this engine returns a DATE, and on that date the deadline expires at a different moment depending on how the paper is filed. BEFORE RELYING ON A FLORIDA DATE THAT FALLS DURING OR SHORTLY AFTER A DECLARED EMERGENCY, check the Supreme Court of Florida\'s administrative orders and the relevant clerk\'s own closure schedule.'
  },
  hi: {
    complete: false,
    direction: 'early',
    summary: 'The Hawaiʻi calendar is the thirteen fixed and derivable holidays HRS Sec. 8-1 designates -- the section Haw. R. Civ. P. 6(a) names by number. THREE THINGS ARE DELIBERATELY OMITTED, each because including it could report LATE: the Sec. 8-2 weekend observance shift, which for 2026 means FRIDAY 3 JULY; the general election day, which Sec. 8-1 makes a holiday only \"in the county wherein the election is held\"; and any day proclaimed by the President or the Governor. Every omission makes this date EARLIER, never later. Check any Hawaiʻi date falling in early July or on a general election day by hand.',
    detail: 'THE REFERENT IS EXPRESS, WHICH IS EXACTLY WHAT IDAHO\'S WAS NOT. Haw. R. Civ. P. 6(a) ends: \"As used in these rules, \'holiday\' shall mean any day designated as such pursuant to SECTION 8-1 of the Hawaiʻi Revised Statutes.\" No chain to trace and no competing list -- contrast Idaho, where the rule said \"legal holiday\" and stopped and three published lists disagreed. THIRTEEN DATES FOR 2026, and FOUR OF THEM EXIST ON NO OTHER CALENDAR IN THIS PLATFORM: PRINCE JONAH KUHIO KALANIANAOLE DAY (26 March), KING KAMEHAMEHA I DAY (11 June), STATEHOOD DAY (the third Friday in August), and GOOD FRIDAY -- Hawaiʻi is the only seeded state to make Good Friday a legal holiday, and the provision survived an Establishment Clause challenge (932 F.2d 765). Good Friday is DERIVED from the computus, not transcribed: 3 April in 2026. Equally, NO JUNETEENTH, NO Columbus or Indigenous Peoples\' Day, and NO day after Thanksgiving -- so a calendar copied from Nebraska would add three days Hawaiʻi does not have and miss four it does. OMISSION 1, AND IT IS A READING RATHER THAN AN OVERSIGHT: THE SEC. 8-2 SHIFT. HRS Sec. 8-2 provides that a state holiday falling on Sunday is observed the following Monday and one falling on Saturday is observed the PRECEDING FRIDAY. But Rule 6(a) incorporates SECTION 8-1 BY NUMBER, and Sec. 8-2\'s shifted day is designated pursuant to Sec. 8-2, not Sec. 8-1. Idaho and Nebraska both carry their shifts because in those states the shift clause sits in the SAME section the rule points at; Hawaiʻi\'s does not. Both readings are respectable and the direction decides: omitting the shifted day reports EARLIER, carrying it would roll a deadline off a possibly-countable day and report LATER. IN 2026 THIS AFFECTS EXACTLY ONE DATE -- 4 July is a Saturday, so Sec. 8-2 would make FRIDAY 3 JULY 2026 an observed holiday and this calendar does not carry it. A practitioner will treat that Friday as a court holiday. Check any date landing in that week by hand. No other Sec. 8-1 holiday falls on a Saturday or Sunday in 2026. OMISSION 2: THE GENERAL ELECTION DAY. Sec. 8-1 designates \"all election days, except primary and special election days, IN THE COUNTY WHEREIN THE ELECTION IS HELD\" -- county-scoped by its own words, and requiring a second statute to fix the date. Neither was resolved on a primary source here, so the day is omitted rather than computed. For an even-numbered year the general election falls in early November and would be statewide in practice; a Hawaiʻi deadline landing on a general election day needs checking. OMISSION 3: \"any day designated by proclamation by the President of the United States or by the governor as a holiday\" -- the open limb every jurisdiction has and none can model. NO BACKWARD ROW IS SEEDED, AND HAWAIʻI HAS THE LONGEST MOTION NOTICE ON THE PLATFORM. Rule 6(d) requires a written motion and notice of hearing to be served NOT LESS THAN 18 DAYS before the hearing, and opposing affidavits not less than 8 days before. Both clear the seven-day exclusion threshold, so that is not the obstacle -- Rule 6(a) simply rolls to \"the NEXT day\" and says nothing about a period measured before an event, the Mississippi, Idaho and Nebraska shape rather than New Mexico\'s. RULE 6 WAS AMENDED TWICE IN THE LAST YEAR -- \"further amended July 9, 2025, effective January 1, 2026; further corrected December 19, 2025; further amended May 21, 2026, effective July 1, 2026\" -- and Rule 36 once, effective 1 January 2026. The text encoded is the current one. WHAT those amendments changed was not determined: the judiciary publishes an amendment history and no redline, and guessing would be worse than recording the gap. 2026 ONLY: a later year is REFUSED rather than derived. Twelve of the thirteen dates would generate mechanically and Good Friday from the computus, which is precisely why generating is refused -- it would hide the Sec. 8-2, election-day and proclamation questions behind a confident answer.'
  },
  nh: {
    complete: false,
    direction: 'early',
    summary: 'The New Hampshire calendar is the ten dated holidays RSA 288:1 enumerates — the chapter N.H. Super. Ct. R. 2 names. ONE ENTRY IS DELIBERATELY OMITTED: RSA 288:1 makes \"the day on which the biennial election is held\" a legal holiday, and 2026 is an even-numbered year, so such a day exists — TUESDAY 3 NOVEMBER 2026 on the only statute that dates a statewide November election, RSA 653:7, which calls it the \"state general election\" and never uses the words \"biennial election\". Omitting it makes a date EARLIER, never later. Check any New Hampshire deadline falling in the first week of November 2026 by hand. Note separately that New Hampshire has NO mailed-service extension of any kind, which is a feature of its rules and not a gap in this seed.',
    detail: 'THE REFERENT NAMES A CHAPTER, NOT A SECTION, AND THAT DISTINCTION ALREADY DECIDED A DATE ONCE. N.H. Super. Ct. R. 2 rolls the last day off \"a Saturday, Sunday, or a legal holiday AS SPECIFIED IN RSA CH. 288, AS AMENDED\". Haw. R. Civ. P. 6(a) named HRS Sec. 8-1 by number, so the weekend-observance section beside it fell OUTSIDE the reference and Hawaii omits its shifted Friday as a reading. Here RSA 288:2 is INSIDE the reference and IS carried. IT THEN TURNS OUT NOT TO MATTER IN 2026, AND THE REASON IS WORTH STATING: RSA 288:2 reads in full \"When any holiday listed in RSA 288:1 falls on Sunday, the following day shall be observed as a holiday\" — A SUNDAY RULE ONLY, with no Saturday limb at all. 4 July 2026 is a SATURDAY, so New Hampshire has NO Friday 3 July observance, not by interpretation but because no clause could produce one. Idaho Code Sec. 73-108 and Neb. Rev. Stat. Sec. 25-2221 both shift a Saturday holiday back to the Friday and both calendars carry 3 July 2026; Hawaii omits it as a reading; New Hampshire omits it because the rule does not exist. Four jurisdictions, three reasons, one date. And NO RSA 288:1 holiday falls on a Sunday in 2026, checked date by date, so the shift that does exist is dormant this year. THE LIST IS CLOSED, WHICH NO OTHER SEEDED HOLIDAY STATUTE IS. Idaho and Hawaii both end with a day appointed by the President or the governor; Kansas reaches any day observed by order of the supreme court; Nebraska subordinates its dates to the federal schedule and adds a governor-proclamation limb. RSA 288:1 enumerates and stops: \"...and Christmas Day are legal holidays.\" There is no proclamation limb to disclose, which removes the open-ended gap every other jurisdiction here has to declare. THE ONE OMISSION IS THE BIENNIAL ELECTION DAY, AND IT IS THE ONE JUDGMENT CALL IN THIS SEED. RSA 288:1 lists \"the day on which the biennial election is held\" among the legal holidays. 2026 is an even-numbered year so such a day exists. DATING IT REQUIRES A SECOND STATUTE THAT DOES NOT USE THE SAME WORD: RSA 653:7 provides that \"the state general election shall be held on the first Tuesday following the first Monday in November of every even-numbered year\", which for 2026 is TUESDAY 3 NOVEMBER 2026; and RSA ch. 652, the election-law definitions chapter, defines \"election\" (652:1), \"regular election\" (652:2), \"state election\" (652:3) and \"state general election\" (652:4) and NEVER DEFINES \"biennial election\". The identification is near-certain and it is still a reading across two chapters. THE DIRECTION DECIDES IT: omitting a holiday returns the unrolled, sooner date, and filing early is safe; carrying a day that is not a holiday returns a date one day LATE and loses the filing. So it is omitted and named here. A New Hampshire deadline landing on Tuesday 3 November 2026 should be checked by hand; no other 2026 date is affected. THE SAME CALL WAS MADE ON HAWAII\'S ELECTION DAY for a related but not identical reason — Hawaii\'s is county-scoped by the statute\'s own words, New Hampshire\'s is statewide and merely undated. TWO CONDITIONAL CLAUSES ARE LIVE LAW, NOT MODELLED, AND DORMANT IN 2026. Memorial Day is \"the last Monday in May ... OR, ON A DATE TO COINCIDE WITH THE FEDERAL OBSERVANCE IF IT IS HELD ON A DIFFERENT DAY\"; the federal observance under 5 U.S.C. 6103 is also the last Monday in May, so both fall on 25 May 2026 and the clause moves nothing. Thanksgiving is \"Thanksgiving Day, WHENEVER APPOINTED\", which names no date at all; it is seeded as the fourth Thursday, which is what 5 U.S.C. 6103 fixes federally and what every appointment in living memory has been, and that is a CONVENTION rather than a transcription. THE JUDICIAL BRANCH PUBLISHES ITS OWN COURT-HOLIDAY SCHEDULE AND IT IS NOT THE LEGAL TEST. courts.nh.gov lists \"Court Holidays - 2026\" as a PDF posted 11 June 2025, and a 2027 one beside it. NEITHER WAS READ — both refuse every automated route available here — and that is recorded rather than guessed at. It would not change this calendar: Rule 2 keys the rollover on a day being \"a legal holiday as specified in RSA ch. 288\", not on whether a courthouse opened. This is the KANSAS POSITION INVERTED. There the statute keys on a day being observed BY ORDER OF THE SUPREME COURT, so the Judicial Branch list IS the legal test; here the statute keys on the legislature\'s enumeration, so the courts\' own list is practical information and nothing more. A day the New Hampshire courts close that RSA 288:1 does not name remains a countable day under Rule 2, and a practitioner should still check it before relying on being able to file. NO BACKWARD ROW IS SEEDED, AND THE ONE BEING GIVEN UP IS UNUSUAL. Rule 2 extends to \"the NEXT day\" and says nothing about a period measured before an event — the Mississippi, Idaho, Nebraska and Hawaii shape, not New Mexico\'s. Rule 26(b) requires deposition notice \"at least 3 days, EXCLUSIVE OF THE DAY OF SERVICE AND THE DAY OF CAPTION, before the day on which they are to be taken\", a period carrying its own both-endpoints-excluded convention that Rule 2 does not supply and this engine cannot express. Also unseeded and backward: Rule 5(a)(8) dispositive motions not less than 120 days before trial, Rule 5(a)(9) other pre-trial motions not later than 14 days before trial, and Rule 35 trial-management filings 14 days before the conference. AN EFFECTIVE-DATE WARNING THAT IS NOT ABOUT HOLIDAYS. The New Hampshire Judicial Branch publishes these rules with NO amendment history and NO per-rule effective dates — checked on the combined page and on an individual rule page, and in sharp contrast to Hawaii, Idaho, Nebraska and New Mexico, which all print bracketed amendment notes. Every effective_from in this seed therefore comes from the ADOPTION ORDER of 22 May 2013 (\"The amendments shall take effect October 1, 2013\") and from the rule set\'s own PREAMBLE in that order (\"They take effect on October 1, 2013, and apply to civil actions pending or filed in superior court on or after that date\"), a preamble the currently-published web version does not reproduce. Each seeded row was then diffed against that order sentence by sentence. TWO REAL PERIODS WERE DROPPED FOR WANT OF A DATE: Rule 13A\'s ten-day reply to an objection and three-day notice to the clerk, and Rule 12\'s thirty-day summary-judgment objection with its twenty-day reply — all current, all post-dating the 2013 adoption, none carrying a published effective date. A caller needing either must not compute it from this seed. 2026 ONLY: a later year is REFUSED rather than derived. All ten dates would generate mechanically, which is precisely why generating is refused — it would hide the biennial-election question behind a confident answer, and it would be wrong in a second way, since 2027 is an ODD year in which the election limb produces no day at all and a generator that silently dropped it would look identical to one that had reasoned about it.'
  },
  mt: {
    complete: false,
    direction: 'early',
    summary: 'DISTRICT COURT ONLY -- the Montana Justice and City Court Rules of Civil Procedure are a DIFFERENT computation, numbered Rule 6 in the same title of the same code, and are not seeded. Montana also extends the time for filing when the clerk\'s office is inaccessible, and Rule 6(a)(6) reaches days declared by the President or the Governor and, for forward periods only, any other day declared a holiday by the state; none of those is modelled. Every omission makes this date EARLIER than the true deadline, never later.',
    detail: "SCOPE FIRST, BECAUSE THE COLLISION IS SHARPER HERE THAN IN DELAWARE: these rows are Mont. R. Civ. P. 6(a) and the Montana Rules of Civil Procedure, MCA Title 25 ch. 20, which govern the DISTRICT COURTS. Mont. Just. & City Ct. R. Civ. P. 6 sits in MCA Title 25 ch. 23, is also called Rule 6, and is a different computation in four ways that all move dates: it contains NO definition of \"legal holiday\" at all, so nothing narrows MCA 1-1-216 the way Rule 6(a)(6) does; it has NO clerk-inaccessibility limb; it has NO backward \"next day\" rule, so a period measured before an event has no stated rollover direction; and its mail extension is MAIL ONLY and reads \"3 days must be added to the prescribed period\" -- period-lengthening with ONE rollover -- against District Court Rule 6(d)'s \"3 days are added AFTER the period would otherwise expire\", which rolls, adds, and rolls again. A Justice or City Court deadline must not be computed from these rows. THE CLERK-INACCESSIBILITY LIMB IS NOT MODELLED: Rule 6(a)(3) extends the time for filing to the first accessible day when the clerk's office is inaccessible. It is an ADDITIONAL limb beside the weekend/holiday test rather than a replacement for it -- the Minnesota and Utah shape, not the Wisconsin one -- so omitting an inaccessible day returns the earlier unrolled date and is EARLY. Closures are per-court and published nowhere this engine can read. THE HOLIDAY DEFINITION HAS TWO OPEN LIMBS AND ONE ASYMMETRY. Rule 6(a)(6)(B) reaches \"any day declared a holiday by the President of the United States or by the Governor of this state\", which is open-ended and underivable -- the Idaho and Hawaii shape. Rule 6(a)(6)(C) reaches, FOR PERIODS MEASURED AFTER AN EVENT ONLY, \"any other day declared a holiday by the state\". So Montana's holiday set is genuinely WIDER for forward periods than for backward ones, and this calendar carries the MCA 1-1-216 enumeration, which is the same in both directions. THE ONE PLACE THAT ASYMMETRY BITES IS PRESIDENTS' DAY, AND IT IS CARRIED IN BOTH DIRECTIONS DELIBERATELY. Rule 6(a)(6)(A) names \"the day set aside by statute for observing ... Lincoln's and Washington's Birthdays\" -- which was MCA 1-1-216(1)(d)'s own wording, verbatim, when the rule was adopted in 2011 and remained so through the 2023 edition. Ch. 561, L. 2025 renamed that entry \"Presidents' Day\" and left the third Monday in February exactly where it was; the rule's list was not conformed. The day is therefore reached by (A) on any ordinary reading and, for forward periods, by (C) beyond argument, since the State plainly declares it. Carrying it forward is certain; carrying it BACKWARD is the safe direction on the residual reading question, because a backward period that fails to roll off a holiday reports a date LATER than the true one. For 2026 that day is Monday 16 February. WHAT IS NOT OMITTED, and both are citations rather than readings: THE SATURDAY OBSERVANCE SHIFT IS CARRIED. MCA 1-1-216(2)(b), added by Ch. 131, L. 2013, provides that a holiday in (1)(b) through (1)(l) falling on a Saturday makes the PRECEDING FRIDAY a holiday, and Rule 6(a)(6)(A) reaches \"the day SET ASIDE BY STATUTE FOR OBSERVING\" the named holidays -- an observance reference, so the shifted day is inside it. 4 July 2026 is a Saturday, so FRIDAY 3 JULY 2026 is a Montana legal holiday and this calendar carries it. Contrast Hawaii, whose rule names HRS Sec. 8-1 BY NUMBER and leaves the Sec. 8-2 shift outside, and New Hampshire, whose shift clause has no Saturday limb at all. AND THE STATE GENERAL ELECTION DAY IS CARRIED. Rule 6(a)(6)(A) names \"state general election day\" IN THE RULE'S OWN LIST, MCA 1-1-216(1)(l) makes it a legal holiday under the same words, and MCA 13-1-104(1) fixes it on \"the first Tuesday after the first Monday in November\" -- for 2026 TUESDAY 3 NOVEMBER, verified by weekday. This is a shorter reach than Delaware's, which needed the state constitution, and the opposite of New Hampshire's, where the holiday statute used a term the election code never defines. NO SHORT-PERIOD EXCLUSION EXISTS IN MONTANA and its absence is not a gap: Rule 6(a)(1)(B) counts \"every day, including intermediate Saturdays, Sundays, and legal holidays\", so the five seeded rows shorter than 15 days are straight calendar counts. A threshold borrowed from a neighbour would report them LATE. NOT MODELLED AND NOT A DATE QUESTION: Rule 6(a)(4) ends the last day at midnight for electronic filing but \"when the clerk's office is scheduled to close\" for filing by other means. This engine computes a DATE and expresses no time of day, so a paper filing made after the counter closes on the correct date is late by a rule this seed cannot express. 2026 ONLY: a later year is REFUSED rather than derived. Every date here would generate mechanically, which is precisely why generating is refused -- 2027 is an ODD year in which the general election limb produces no state general election day, and a generator that silently dropped it would look identical to one that had reasoned about it."
  }
};

// THE DISCLOSED-LATE CATEGORY IS SELF-ENFORCING. An entry cannot be ambiguous
// about whether it carries a late-direction exposure: 'late' without the block,
// or the block without 'late', is a load-time failure rather than a quiet
// mislabel. Same standard as the weekend_days check above and for the same
// reason -- this is in-code data, so a defect here is a bug, and a bug that
// stops the engine loading is caught by the first test that requires it.
// Exported so the invariant and its test assert the SAME function rather than
// two implementations that can drift -- the weekendDaysDefect pattern.
// Returns an array of defect strings; empty means the table is well formed.
function coverageTableDefects(table) {
  var REQUIRED_LATE_KEYS = ['authority', 'summary', 'why_not_refused', 'caller_action'];
  var bad = [];
  Object.keys(table).forEach(function (k) {
    var e = table[k];
    if (e.direction !== 'early' && e.direction !== 'late') {
      bad.push(k + '.direction is ' + JSON.stringify(e.direction) + ', expected "early" or "late"');
    }
    if (e.direction === 'late' && !e.late_exposure) {
      bad.push(k + " declares direction 'late' with no late_exposure block naming the authority and the risk");
    }
    if (e.late_exposure && e.direction !== 'late') {
      bad.push(k + " carries a late_exposure block but direction is '" + e.direction + "'");
    }
    if (e.late_exposure) {
      REQUIRED_LATE_KEYS.forEach(function (rk) {
        if (!e.late_exposure[rk]) bad.push(k + '.late_exposure is missing ' + rk);
      });
    }
  });
  return bad;
}
(function validateCoverageDeclarations() {
  var bad = coverageTableDefects(JURISDICTION_COVERAGE);
  if (bad.length) {
    throw new Error('deadline-engine: invalid JURISDICTION_COVERAGE declaration(s): ' + bad.join('; '));
  }
})();

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
// ── SEQUENCING: WHERE THE ADDED DAYS GO RELATIVE TO THE ROLLOVER ──────────
// Every standard declares `sequence`, because the rules genuinely disagree and
// the difference moves real dates. Two shapes exist:
//
//   'roll_then_add_then_roll'  the base period expires, its last day is rolled
//                              off a weekend or holiday, THEN the days are
//                              added, then the result is rolled again.
//   'add_to_period_then_roll'  the days LENGTHEN the period itself, so there
//                              is only ever one period and one rollover, at
//                              the end of the lengthened period.
//
// This is not a stylistic choice. It is written into the rules, in words:
//
//   FRCP 6(d)      "3 days are added after the period would otherwise expire
//                   under Rule 6(a)"                        -> roll first
//   Fla. 2.514(b)  "5 days are added after the period that would otherwise
//                   expire under subdivision (a)"           -> roll first
//   CPLR 2103(b)(2) "five days shall be added to the prescribed period"
//                                                           -> no interim roll
//
// FRCP's order was verified against the 2005 Advisory Committee Note, quoted
// in this file's header. New York's was verified the other way: 2103(b)(2)
// never mentions expiration, it lengthens "the prescribed period", and
// Gen. Constr. Law 25-a then acts once on the end of that single lengthened
// period.
//
// THE DIFFERENCE IS NOT COSMETIC AND IT RUNS IN THE DANGEROUS DIRECTION.
// Worked example, caught by a failing test rather than by reading: a 20-day
// CPLR 3133(a) period triggered 2026-06-01 expires Sunday 2026-06-21.
//   roll first: -> Mon 06-22, +5 -> Sat 06-27, roll -> Mon 06-29
//   add first:  -> 06-21 + 5 -> Fri 06-26, no roll needed -> Fri 06-26
// Three days apart, and the FRCP sequencing is the LATER of the two. A date
// that is late is how a filing is missed, so a standard that does not declare
// its sequencing must never be given the benefit of the doubt.
//
// Default is 'roll_then_add_then_roll' for any standard that omits the field,
// which preserves the behaviour every pre-existing standard was tested under.
var SERVICE_EXTENSION_STANDARDS = {
  frcp_6d: {
    label: 'Fed. R. Civ. P. 6(d)',
    sequence: 'roll_then_add_then_roll',
    shape: 'enumerated_allowlist',
    qualifies: function (method) {
      return method === 'mail' || method === 'left_with_clerk' || method === 'other_consented_means';
    }
  },
  frap_26c: {
    label: 'Fed. R. App. P. 26(c)',
    // "3 days are added after the period would otherwise expire" -- same
    // sequencing words as FRCP 6(d).
    sequence: 'roll_then_add_then_roll',
    shape: 'negative_condition',
    qualifies: function (method) {
      // "3 days are added after the period would otherwise expire" when the
      // paper is NOT served electronically. Anything explicitly electronic is
      // excluded; an unstated method cannot be assumed non-electronic.
      if (!method) return false;
      return method !== 'electronic' && method !== 'electronic_service';
    }
  },
  // Florida 2.514(b), verbatim: "When a party may or must act within a
  // specified time after service and service is made by only mail, 5 days are
  // added after the period that would otherwise expire under subdivision (a)."
  //
  // FIVE days, not the FRCP's three -- a rule that would be easy to carry
  // across from frcp_6d and get wrong by two days on every mailed Florida
  // service. And narrower than FRCP 6(d) in what qualifies: 6(d) extends for
  // mail, leaving with the clerk, or other consented means; 2.514(b) extends
  // for mail and nothing else, and only when service was by mail ONLY. A
  // mixed method that includes e-mail does not qualify, which is why the
  // allowlist here is a single value rather than frcp_6d's three.
  fl_rgpja_2514b: {
    label: 'Fla. R. Gen. Prac. & Jud. Admin. 2.514(b)',
    // "5 days are added after the period that would otherwise expire under
    // subdivision (a)" -- expressly after expiration, like the FRCP family.
    sequence: 'roll_then_add_then_roll',
    shape: 'enumerated_allowlist',
    qualifies: function (method) { return method === 'mail'; }
  },
  // Tex. R. Civ. P. 21a(c), verbatim: "Whenever a party has the right or is
  // required to do some act within a prescribed period after the service of a
  // notice or other paper upon him and the notice or paper is served upon him
  // by mail, three days shall be added to the prescribed period."
  //
  // THREE days like FRCP 6(d), but MAIL ONLY like Florida's five -- so it
  // matches neither existing standard and gets its own. 21a(a)(2) lists the
  // methods available for a document not filed electronically: "in person, by
  // mail, by commercial delivery service, by fax, by email, or by such other
  // manner as the court in its discretion may direct." Subdivision (c) then
  // extends for exactly one of them. Commercial delivery service, fax, email
  // and electronic service through the filing manager all get NO added days,
  // even though 21a(b) gives each its own completion rule. Reading (b)'s list
  // of methods as the set that qualifies under (c) is the available mistake
  // here, and it would add three days that Texas law does not add.
  //
  // Note what this standard does NOT reach: the citation. 21a(a) opens by
  // covering every paper required to be served under Rule 21, "other than the
  // citation to be served upon the filing of a cause of action." So the
  // Rule 99 answer deadline takes no service extension at all -- that is the
  // law rather than an omission, and the Rule 99 row carries no
  // service_extension for that reason.
  tx_trcp_21a: {
    label: 'Tex. R. Civ. P. 21a(c)',
    // ── CORRECTED. This shipped in cc6899b with no sequence declared, which
    //    defaulted it to the FRCP order, and that appears to be wrong. ──────
    // Texas uses New York's wording, not the federal wording, and the
    // difference is the whole question:
    //
    //   FRCP 6(d)       "3 days are added AFTER THE PERIOD WOULD OTHERWISE
    //                    EXPIRE under Rule 6(a)"
    //   Fla. 2.514(b)   "5 days are added AFTER THE PERIOD that would
    //                    otherwise expire under subdivision (a)"
    //   Tex. R. Civ. P. 21a(c)  "three days shall be added TO THE PRESCRIBED
    //                    PERIOD"
    //
    // Texas conspicuously lacks the "after the period would otherwise expire"
    // language that both rules it most resembles have, and Rule 4 describes
    // the same three days from its own side as "extending other periods by
    // three days when service is made by mail" -- extending the period, not
    // following its expiry.
    //
    // WHAT THIS IS BASED ON, STATED PLAINLY. No Texas appellate authority
    // squarely on the order of operations was found. The change rests on the
    // two rules' own words plus two independent secondary sources that both
    // state the addition comes first and the terminal-day check second. That
    // is weaker than the FRCP position, which is settled by the 2005 Advisory
    // Committee Note quoted in this file's header, and it is recorded as such
    // rather than presented as equally certain.
    //
    // IT ALSO MOVES IN THE SAFE DIRECTION, which is why it is made rather than
    // deferred pending better authority. The previous behaviour rolled the
    // base period first and produced a LATER date; adding to the period first
    // produces an earlier one. Where the reading is uncertain and one option
    // is late, the late option is the one that misses a filing.
    //
    // Found by New York, not by Texas: the identical wording in CPLR
    // 2103(b)(2) made a New York test fail, and the same wording was already
    // sitting in the Texas standard undeclared.
    sequence: 'add_to_period_then_roll',
    shape: 'enumerated_allowlist',
    qualifies: function (method) { return method === 'mail'; }
  },
  // ── GEORGIA: THIRD JURISDICTION IN A ROW WITH THE "TO THE PERIOD" SHAPE ──
  // O.C.G.A. 9-11-6(e), verbatim: "Whenever a party has the right or is
  // required to do some act or take some proceedings within a prescribed
  // period after the service of a notice or other paper, OTHER THAN PROCESS,
  // upon him or her, and the notice or paper is served upon the party by mail
  // or e-mail, three days shall be added to the prescribed period."
  //
  // SEQUENCING WAS READ FIRST THIS TIME, NOT DISCOVERED BY A FAILING TEST.
  // Georgia says "added to the prescribed period" -- New York's and Texas's
  // wording, not the federal "after the period would otherwise expire". Three
  // of the four states seeded in this batch use the period-lengthening shape
  // and only Florida follows the FRCP. Whatever intuition suggests the federal
  // order is the default across American practice, the sample here says
  // otherwise, and every new jurisdiction gets this read before it is seeded.
  //
  // "OTHER THAN PROCESS" IS AN EXPRESS CARVE-OUT, and it is the cleanest one
  // in this engine. Texas reaches the same result by 21a(a) excluding "the
  // citation to be served upon the filing of a cause of action", and New York
  // by 2103(b) governing only papers served "upon an attorney" -- both
  // inferences from scope. Georgia says the words. So the O.C.G.A. 9-11-12
  // answer deadline, which runs from service of the summons and complaint,
  // takes no extension, and that is the statute talking rather than a reading.
  //
  // E-MAIL IS INCLUDED BY THE TEXT AND ITS SCOPE IS ACTIVELY CONTESTED.
  // 9-11-6(e) names "mail or e-mail" on its face. But whether it reaches
  // service generated by an electronic filing service provider was litigated
  // in Speckhals v. Golf & Tennis Pro Shop, Inc.: the trial court held the
  // three days did NOT apply to such e-service, the Court of Appeals affirmed
  // under its Rule 36, and the Supreme Court of Georgia DENIED certiorari in
  // 2024 -- with a statement from Justice Warren that the text "does not
  // appear to support" that construction and that it would cause confusion
  // across Georgia. So the question is unresolved by any binding decision.
  //
  // WHAT THIS ENGINE DOES ABOUT THAT: it extends for 'email' because the
  // statute says e-mail, and it does NOT accept a distinct EFSP service method
  // at all, so a caller cannot get a silent answer to the contested question.
  // The seed rows carry the warning. This is disclosed rather than resolved --
  // picking a side of a live dispute is not something a date calculator should
  // do quietly, in either direction.
  ga_ocga_9_11_6_e: {
    label: 'O.C.G.A. 9-11-6(e)',
    // "three days shall be added TO THE PRESCRIBED PERIOD" -- period-
    // lengthening, so one rollover at the end. Read before seeding, not after.
    sequence: 'add_to_period_then_roll',
    shape: 'enumerated_allowlist',
    qualifies: function (method) { return method === 'mail' || method === 'email'; }
  },
  // ── NEW YORK: PER-METHOD AMOUNTS, AND ONE OF THEM IS A BUSINESS DAY ──────
  // The second standard in this engine whose amount depends on the method
  // (California was the first), and the FIRST whose extension is measured in
  // business days rather than calendar days.
  //
  // CPLR 2103(b)(2), verbatim: "service by mail shall be complete upon
  // mailing; where a period of time prescribed by law is measured from the
  // service of a paper and service is by mail, five days shall be added to the
  // prescribed period if the mailing is made within the state and six days if
  // the mailing is made from outside the state but within the geographic
  // boundaries of the United States".
  //
  // CPLR 2103(b)(6), verbatim: "Where a period of time prescribed by law is
  // measured from the service of a paper and service is by overnight delivery,
  // one business day shall be added to the prescribed period."
  //
  // ONE BUSINESS DAY IS NOT ONE CALENDAR DAY. Overnight service on a Friday
  // adds a day that lands on Monday, and more across a holiday weekend.
  // Treating it as a calendar day would produce a date EARLIER than the true
  // deadline -- the direction that loses a right. Handled by the same branch
  // that counts California's court days, which is why that branch now accepts
  // both unit names; the two rules use different words for the same operation.
  //
  // A BARE 'mail' IS REJECTED, exactly as in California and for the same
  // reason: the amount genuinely depends on where the mailing was made, and
  // guessing the in-state five would be wrong by one whenever the mailing came
  // from another state. Callers must supply mail_within_state or
  // mail_outside_state_within_us.
  //
  // MAILING FROM OUTSIDE THE UNITED STATES GETS NO ENTRY, DELIBERATELY.
  // 2103(b)(2) provides five days in-state and six from outside the state
  // "but within the geographic boundaries of the United States", and then
  // stops. It states no amount for a mailing from abroad. California's
  // CCP 1013(a) does address that case and gives 20 days; New York's does not,
  // and borrowing California's number would be inventing law. A caller
  // supplying such a method gets a visible not_qualifying refusal rather than
  // a silent in-state five.
  //
  // NO ADDED DAYS FOR FACSIMILE OR ELECTRONIC SERVICE. 2103(b)(5) and (b)(7)
  // each define when that service is complete and neither adds time -- only
  // (b)(2) and (b)(6) carry an added-days clause. This is the available
  // mistake in New York practice, because e-filing feels like it should behave
  // like mail. Any contrary provision in the rules of the chief administrator
  // referred to by (b)(7) was NOT read for this seed, so nothing is assumed
  // in either direction; what is encoded is what CPLR 2103(b) itself says.
  //
  // WHAT THIS STANDARD DOES NOT REACH: service of the SUMMONS. 2103(b) governs
  // service "upon an attorney" of "papers to be served upon a party in a
  // pending action". The CPLR 320(a) appearance clock and the CPLR 3012(c)
  // answer clock both run from service of process under CPLR 308 and the
  // related sections, not from service of a paper on an attorney, so those
  // rows carry no service extension. Same shape as Texas's citation exclusion,
  // reached by a different route.
  ny_cplr_2103b: {
    label: 'N.Y. CPLR 2103(b)(2), (b)(6)',
    // "five days shall be added TO THE PRESCRIBED PERIOD" -- the days lengthen
    // the period rather than following its expiry, so Gen. Constr. Law 25-a
    // acts once, on the end of the lengthened period. See the sequencing note
    // above the standards table; getting this wrong runs three days LATE.
    sequence: 'add_to_period_then_roll',
    shape: 'enumerated_allowlist_with_per_method_amount',
    qualifies: function (method) {
      return ({ mail_within_state: 1, mail_outside_state_within_us: 1, overnight_delivery: 1 })[method] === 1;
    },
    amount: function (method) {
      var table = {
        mail_within_state: { add: 5, unit: 'calendar_days' },
        mail_outside_state_within_us: { add: 6, unit: 'calendar_days' },
        overnight_delivery: { add: 1, unit: 'business_days' }
      };
      return table[method] || null;
    }
  },
  // ── CALIFORNIA: THE AMOUNT DEPENDS ON THE METHOD ────────────────────────
  // Every standard above adds one fixed number of calendar days for any
  // qualifying method. California does not, and encoding it as if it did
  // would be wrong by up to fifteen days.
  //
  // CCP 1013(a), verbatim, for service by MAIL: the period "shall be extended
  // five calendar days, upon service by mail, if the place of address and the
  // place of mailing is within the State of California, 10 calendar days if
  // either the place of mailing or the place of address is outside the State
  // of California but within the United States, 12 calendar days if the place
  // of address is the Secretary of State's address confidentiality program
  // ..., and 20 calendar days if either the place of mailing or the place of
  // address is outside the United States".
  //
  // CCP 1013(c) (Express Mail or another overnight-delivery method) and
  // 1013(e) (facsimile, permitted only by written agreement) each extend by
  // "two court days". CCP 1010.6(a)(3)(B) extends electronic service by "two
  // court days" as well.
  //
  // COURT DAYS, NOT CALENDAR DAYS, for those three. Two court days across a
  // weekend is four calendar days and across a holiday weekend more; treating
  // them as calendar days yields a date EARLIER than the true deadline. The
  // engine counts them properly -- see the court_days branch in the extension
  // application below, added for this.
  //
  // THE EXCLUSIONS ARE THE MOST IMPORTANT PART AND ARE HANDLED BY ABSENCE,
  // NOT BY CODE HERE. Both sections say the extension "shall not apply to
  // extend the time for filing notice of intention to move for new trial,
  // notice of intention to move to vacate judgment pursuant to Section 663a,
  // or notice of appeal." So California's three Rule 8.104 appellate rows
  // carry NO service_extension at all -- that is deliberate and now has a
  // verbatim citation behind it, where before it was simply unread.
  //
  // Method names are the caller's vocabulary, so all four mail variants are
  // spelled out rather than inferred from a single 'mail'. A bare 'mail' with
  // no location qualifier is NOT accepted: the amount genuinely depends on
  // facts the engine cannot see, and guessing the in-state five would be
  // wrong by 5, 7 or 15 days whenever the guess is wrong.
  ca_ccp_1013_1010_6: {
    label: 'Cal. Code Civ. Proc. 1013, 1010.6',
    // CCP 1013(a) extends the period "if served by mail" and the settled
    // practice this engine shipped under is the FRCP sequencing. NOT
    // re-verified against 1013's own words during the New York work, so it is
    // declared explicitly to preserve existing behaviour rather than silently
    // inheriting a default -- and it is named here as a row worth re-reading
    // the next time California is touched.
    sequence: 'roll_then_add_then_roll',
    shape: 'enumerated_allowlist_with_per_method_amount',
    qualifies: function (method) {
      return ({
        mail_within_california: 1, mail_outside_california_within_us: 1,
        mail_to_address_confidentiality_program: 1, mail_outside_us: 1,
        express_mail: 1, overnight_delivery: 1, fax: 1,
        electronic: 1, electronic_service: 1
      })[method] === 1;
    },
    amount: function (method) {
      var table = {
        mail_within_california: { add: 5, unit: 'calendar_days' },
        mail_outside_california_within_us: { add: 10, unit: 'calendar_days' },
        mail_to_address_confidentiality_program: { add: 12, unit: 'calendar_days' },
        mail_outside_us: { add: 20, unit: 'calendar_days' },
        express_mail: { add: 2, unit: 'court_days' },
        overnight_delivery: { add: 2, unit: 'court_days' },
        fax: { add: 2, unit: 'court_days' },
        electronic: { add: 2, unit: 'court_days' },
        electronic_service: { add: 2, unit: 'court_days' }
      };
      return table[method] || null;
    }
  },
  // ── WEST VIRGINIA: THE RULE'S CROSS-REFERENCE CONTRADICTS ITS OWN
  //    PARENTHETICAL, AND THIS ENGINE REFUSES RATHER THAN PICKING A SIDE ────
  // W. Va. R. Civ. P. 6(e), verbatim: "When a party may or shall act within a
  // specified time after being served and service is made under Rule
  // 5(b)(2)(C) (mail), (D) (leaving with the clerk), or (F) (other means
  // consented to), 3 days are added after the period would otherwise expire
  // under Rule 6(a)."
  //
  // But West Virginia's Rule 5(b)(2) is NOT the federal Rule 5(b)(2). It
  // inserts a state-specific (E) -- "in counties where West Virginia E-Filing
  // is utilized, by electronic service pursuant to Rule 15 of the West
  // Virginia Trial Court Rules, or otherwise by ... facsimile" -- which pushes
  // the federal (E) and (F) down one letter. So, verbatim:
  //
  //   5(b)(2)(F)  "sending it by other ELECTRONIC means if the person
  //                consented in writing"
  //   5(b)(2)(G)  "delivering it by any OTHER MEANS that the person consented
  //                to in writing"
  //
  // 6(e) points at (F) and then labels it "(other means consented to)", which
  // is the text of (G). The pointer and the parenthetical name two different
  // subparagraphs. The cause is visible: 6(e) was carried over from FRCP 6(d),
  // where (F) really is "other means consented to", and was not renumbered
  // when (E) was inserted above it.
  //
  // THE TWO READINGS GIVE OPPOSITE ANSWERS on the one method that matters.
  // Read by the pointer, West Virginia adds three days for consented-to
  // ELECTRONIC service -- which the federal rule deliberately does not, having
  // removed exactly that extension in 2016. Read by the parenthetical, it adds
  // three days for non-electronic consented delivery and nothing for
  // electronic, matching the federal policy.
  //
  // BOTH CONTESTED METHODS ARE REFUSED VISIBLY rather than resolved. The usual
  // tie-break in this engine -- resolve toward the earlier date, because late
  // is what misses a filing -- would mean adding nothing, and that is exactly
  // the failure mode this file already fixed once: a silent no-extension is
  // indistinguishable from "no extension was requested", so the caller never
  // learns there was a question. mail and left_with_clerk are unaffected; both
  // readings agree on them, and they are the ordinary cases.
  //
  // NOT COVERED AT ALL, IN EITHER READING: service under 5(b)(2)(E), the West
  // Virginia E-Filing and facsimile subparagraph. 6(e) does not list (E) under
  // any construction, so e-filed service carries no extension. That is the
  // available mistake in West Virginia practice for the same reason it is in
  // New York -- e-service feels like it should behave like mail.
  wv_rcp_6e: {
    label: 'W. Va. R. Civ. P. 6(e)',
    // "3 days are added AFTER THE PERIOD WOULD OTHERWISE EXPIRE under Rule
    // 6(a)" -- the federal order, read before seeding rather than caught by a
    // failing test. THIS IS A CHANGE: the FORMER rule said "3 days shall be
    // added TO THE PRESCRIBED PERIOD", the New York and Georgia shape. West
    // Virginia is the first jurisdiction in this engine whose service-extension
    // SEQUENCING flipped over time, which is the strongest evidence yet that
    // the standing habit of reading this wording per jurisdiction is worth
    // keeping -- here it would also have had to be read per DATE.
    sequence: 'roll_then_add_then_roll',
    shape: 'enumerated_allowlist',
    qualifies: function (method) {
      return method === 'mail' || method === 'left_with_clerk';
    },
    // Optional, checked BEFORE qualifies. A method listed here is one the rule
    // text does not resolve, so no date is offered for it in either direction.
    contested: function (method) {
      return method === 'other_electronic_means_consented' ||
             method === 'other_means_consented';
    }
  },
  // ── NORTH CAROLINA: MAIL AND ONLY MAIL ──────────────────────────────────
  // N.C. R. Civ. P. 6(e) (G.S. 1A-1, Rule 6(e)), verbatim: "Whenever a party
  // has the right to do some act or take some proceedings within a prescribed
  // period after the service of a notice or other paper upon him and the notice
  // or paper is served upon him by mail, three days shall be added to the
  // prescribed period."
  //
  // THE NARROWEST ALLOWLIST IN THIS ENGINE, and deliberately so. Mail is the
  // only method named. North Carolina's Rule 5(b) authorises service through
  // the court's electronic filing system, by email to an address of record, by
  // confirmed telefacsimile and by hand -- and 6(e) reaches NONE of them. This
  // is the available mistake in North Carolina practice and it is worth stating
  // next to its neighbours, because three jurisdictions seeded in two days
  // answer it three different ways: Kentucky's eFiling Rules 13(6) says
  // electronic service "is treated the same as service by mail under CR 6.05
  // for the purpose of adding three (3) days"; West Virginia's 6(e) is contested
  // on its face and refused; North Carolina's simply does not cover it. Nothing
  // about e-service extensions generalises across states.
  //
  // SEQUENCING IS PERIOD-LENGTHENING, read up front rather than caught by a
  // failing test: "three days shall be ADDED TO THE PRESCRIBED PERIOD" -- the
  // New York, Georgia and pre-2025 West Virginia shape, not the federal
  // after-expiry order. One period, one rollover, at the end.
  //
  // WHAT THIS STANDARD DOES NOT REACH: service of the summons and complaint.
  // Rule 5(b1) excepts "pleadings and papers whose service is governed by Rule
  // 4", and 6(e) runs from "the service of a notice or other paper". So the
  // Rule 12(a)(1) answer deadline carries no extension -- reached by scope, the
  // same route as West Virginia, where Georgia gets there by express words
  // ("other than process") and Texas and New York by inference.
  //
  // ── RULE 6(f) IS NOT IMPLEMENTED, AND IT IS NOT AN OVERSIGHT ─────────────
  // Rule 6(f), verbatim: "Whenever a person participating in the Address
  // Confidentiality Program established by Chapter 15C of the General Statutes
  // has a legal right to act within a prescribed period of 10 days or less
  // after the service of a notice or other paper upon the program participant,
  // and the notice or paper is served upon the program participant by mail,
  // five days shall be added to the prescribed period."
  //
  // FIVE days rather than three, but conditioned on THE LENGTH OF THE BASE
  // PERIOD -- "a prescribed period of 10 days or less".
  //
  // THE BLOCKER MOVED WHEN VIRGINIA WAS SEEDED, AND DID NOT VANISH. This note
  // used to say the shape needed was "an amount() that also receives the base
  // period", and that shape now EXISTS: amount(method, ctx) is handed
  // ctx.base_period_count and ctx.base_period_unit, built for Va. Sup. Ct.
  // R. 1:7 and deliberately made general enough to serve this rule too.
  //
  // What still blocks 6(f) is the OTHER condition in its own text: it applies
  // only to "a person participating in the Address Confidentiality Program".
  // That is a fact about the SERVED PARTY, not about the method, the period or
  // the date, and this engine accepts no input carrying it. Inventing one on
  // the way past a Virginia seed would be exactly the speculative widening this
  // file avoids. It needs its own decision about where that fact comes from and
  // whether a caller can be trusted to assert it.
  //
  // Unchanged: no seeded North Carolina row is 10 days or shorter, so 6(f) is
  // unreachable in the current row set either way; it must be implemented
  // before any such row is added, and the omission fails in the EARLY direction
  // (three days added instead of five) rather than late.
  nc_rcp_6e: {
    label: 'N.C. R. Civ. P. 6(e) (G.S. 1A-1, Rule 6(e))',
    sequence: 'add_to_period_then_roll',
    shape: 'enumerated_allowlist',
    qualifies: function (method) { return method === 'mail'; }
  },
  // ── WASHINGTON: MAIL ONLY, AND PERIOD-LENGTHENING ───────────────────────
  // CR 6(e), verbatim: "Whenever a party has the right or is required to do
  // some act or take some proceedings within a prescribed period after the
  // service of a notice or other paper upon the party and the notice or paper
  // is served upon the party by mail, 3 days shall be added to the prescribed
  // period."
  //
  // "ADDED TO THE PRESCRIBED PERIOD" -- period-lengthening, one rollover at the
  // end of the single lengthened period. Read up front rather than caught by a
  // failing test, per the standing habit. Same shape as North Carolina, New
  // York, Georgia and pre-2025 West Virginia; NOT the federal after-expiry
  // order.
  //
  // MAIL AND ONLY MAIL. CR 5(b)(7) authorises service "by any other means,
  // including facsimile or electronic means, consented to in writing by the
  // person served or as authorized under local court rule", and CR 6(e) does
  // not reach any of it. That makes five states with five different answers on
  // whether electronic service extends -- Kentucky's eFiling Rules 13(6)
  // expressly treats it as mail and adds three days, West Virginia's 6(e) is
  // contested on its face and is refused in code, North Carolina and Washington
  // simply do not cover it, and California adds two COURT days. Nothing about
  // e-service extensions generalises across states, and this comment exists so
  // the next jurisdiction is read rather than assumed.
  //
  // WHAT THIS DOES NOT REACH: service of the summons. CR 12(a)(1) runs its
  // 20-day answer period from service "pursuant to rule 4", and CR 6(e) extends
  // a period run after "the service of a notice or other paper". Same scope
  // route as West Virginia and North Carolina.
  wa_cr_6e: {
    label: 'Wash. Super. Ct. Civ. R. 6(e)',
    sequence: 'add_to_period_then_roll',
    shape: 'enumerated_allowlist',
    qualifies: function (method) { return method === 'mail'; }
  },
  // Del. Super. Ct. Civ. R. 6(e), verbatim on the operative sentence:
  //   "Whenever a party has the right to or is required to do some act or take
  //    some proceeding within a prescribed period after being served and
  //    service is by mail, 3 days shall be added to the prescribed period."
  //
  // MAIL ONLY, AND NOT AN EXCLUSIVITY RULE. Checked against the Utah/Florida
  // shape deliberately, since both were live when this was written: the text
  // says "service is by mail" with no "only", "exclusively" or equivalent, so
  // it takes no requires_exclusive and a caller supplying service_methods
  // changes nothing. There is no electronic, facsimile or consented-means limb
  // to reconcile -- unlike the FRCP family, this rule has exactly one method.
  //
  // "ADDED TO THE PRESCRIBED PERIOD" IS WHY THE SEQUENCE IS
  // add_to_period_then_roll RATHER THAN after_base_period. The three days
  // lengthen the period itself, so the weekend/holiday rollover acts ONCE, on
  // the end of the lengthened period. Rolling first and then adding would give
  // a different date whenever the unrolled last day lands on a weekend.
  //
  // THE SECOND SENTENCE IS A LIMIT ON WHO, NOT ON HOW MANY DAYS: "The
  // additional 3-day period applies only to actions taken by parties and does
  // not apply to actions taken by the Court." Every seeded Delaware row is a
  // party's act, so the limb is satisfied by construction rather than modelled.
  de_super_ct_civ_r_6e: {
    label: 'Del. Super. Ct. Civ. R. 6(e)',
    sequence: 'add_to_period_then_roll',
    shape: 'enumerated_allowlist',
    qualifies: function (method) { return method === 'mail'; }
  },
  // ── MONTANA: THE PRE-2016 FEDERAL SET, ELECTRONIC LIMB AND ALL ──────────
  // Mont. R. Civ. P. 6(d), verbatim in full:
  //
  //   "When a party may or must act within a specified time after service and
  //    service is made under Rule 5(b)(2)(C), (D), or (E), or (F), 3 days are
  //    added after the period would otherwise expire under Rule 6(a)."
  //
  // THIS IS NOT frcp_6d AND REUSING THAT STANDARD WOULD BE WRONG BY THREE DAYS
  // ON EVERY CONSENTED ELECTRONIC SERVICE. Federal Rule 6(d) was amended in
  // 2016 to DROP subparagraph (E) -- electronic service -- from the list.
  // Montana's rule still carries it, so a Montana party served by e-mail with
  // written consent gets the three days and a federal one does not. The four
  // Rule 5(b)(2) limbs this reaches, read from Rule 5 rather than assumed from
  // the federal numbering:
  //   (C) mailing to the last known address           -> mail
  //   (D) leaving it with the court clerk where the
  //       person has no known address                 -> left_with_clerk
  //   (E) sending it by electronic means where the
  //       person consented IN WRITING                 -> electronic, email
  //   (F) delivering it by any other means the person
  //       consented to IN WRITING                     -> other_consented_means
  // Rule 5(b)(2)(A) handing it to the person and (B) leaving it at an office or
  // dwelling are NOT in the list and add nothing.
  //
  // THE WRITTEN CONSENT IN (E) AND (F) IS NOT EXPRESSIBLE AS A METHOD TOKEN and
  // is not modelled. It does not need to be: service by an unconsented
  // electronic means is not service under Rule 5(b)(2) at all, so a caller who
  // reports it has already reported something the rules do not recognise. Same
  // treatment as Massachusetts, whose 6(d) also extends for electronic service.
  //
  // "ADDED AFTER THE PERIOD WOULD OTHERWISE EXPIRE UNDER RULE 6(a)" IS WHY THE
  // SEQUENCE IS roll_then_add_then_roll. Those are the federal words, and they
  // are the OPPOSITE of the Justice and City Court rule in the same title,
  // whose 6.C says "3 days must be added to the prescribed period" --
  // period-lengthening, one rollover. Two rules numbered 6, in one code, with
  // opposite sequencing; the difference moves real dates whenever the unrolled
  // last day lands on a weekend.
  //
  // NOT AN EXCLUSIVITY RULE. Checked against the Utah and Florida shape
  // deliberately: the text says "service is made under Rule 5(b)(2)(C), (D), or
  // (E), or (F)" with no "only", "exclusively" or equivalent, so it takes no
  // requires_exclusive and a caller supplying service_methods changes nothing.
  //
  // WHAT IT DOES NOT REACH: service of the summons and complaint. Rule 6(d) is
  // expressly gated on service "made under Rule 5(b)(2)", and a summons and
  // complaint go out under Rule 4. That is a citation rather than a reading,
  // which is why the Montana answer row carries no extension and needs no
  // open-question note -- contrast Delaware, where Rule 6(e) says only "after
  // being served" and the same question is still open.
  mt_rcp_6d: {
    label: 'Mont. R. Civ. P. 6(d)',
    sequence: 'roll_then_add_then_roll',
    shape: 'enumerated_allowlist',
    qualifies: function (method) {
      return ({ mail: 1, left_with_clerk: 1, electronic: 1, email: 1, other_consented_means: 1 })[method] === 1;
    }
  },
  // ── NEW JERSEY: FIVE DAYS, AND ORDINARY MAIL IS NOT "MAIL" ──────────────
  // R. 1:3-3, verbatim: "When service of a notice or paper is made by ordinary
  // mail, and a rule or court order allows the party served a period of time
  // after the service thereof within which to take some action, 5 days shall be
  // added to the period." Amended February 8, 2022, effective April 1, 2022.
  //
  // FIVE DAYS, NOT THREE. Only Florida's 2.514(b) and Arizona's Rule 6(c)
  // (unseeded) also add five; the federal rule, West Virginia, North Carolina,
  // Washington, Georgia and Texas all add three, and New York and California
  // vary by method. There is no default to fall back on, which is why every
  // jurisdiction's amount is read rather than inherited.
  //
  // "ADDED TO THE PERIOD" -- period-lengthening, one rollover at the end.
  //
  // THE QUALIFYING METHOD IS ordinary_mail AND DELIBERATELY NOT mail. This is
  // the narrowest allowlist in the engine and the name carries the reason.
  // R. 1:5-2 authorises, for service on a party, "registered or certified mail,
  // return receipt requested, and simultaneously by ordinary mail", and for
  // service on an attorney, ordinary mail, email to an address listed on an
  // approved electronic court system, handing it over, or leaving it at the
  // office. Only the ordinary-mail limb extends. Accepting a bare "mail" here
  // would silently add five days to a certified-mail service that R. 1:3-3 does
  // not obviously reach; refusing it produces a visible not_qualifying instead,
  // which is the behaviour this engine already chose when it stopped letting a
  // silent no-extension look like "none requested".
  //
  // WHAT THIS DOES NOT REACH: the summons and complaint, served under R. 4:4-4
  // rather than by ordinary mail under R. 1:5-2. Same scope route as West
  // Virginia, North Carolina and Washington.
  nj_r_1_3_3: {
    label: 'N.J. Ct. R. 1:3-3',
    sequence: 'add_to_period_then_roll',
    shape: 'enumerated_allowlist',
    qualifies: function (method) { return method === 'ordinary_mail'; }
  },
  // ── VIRGINIA: THE AMOUNT DEPENDS ON WHAT TIME OF DAY SERVICE FINISHED ────
  // Va. Sup. Ct. R. 1:7, verbatim in full:
  //
  //   "Whenever a party is required or permitted under these Rules, or by
  //    direction of the court, to do an act within a prescribed period of days
  //    after service of a paper upon counsel of record,
  //    (a) No days will be added if the paper is served by:
  //    (1) manual delivery no later than 5:00 p.m. by counsel, counsel's agent
  //        or courier, or a commercial delivery service making same-day
  //        delivery;
  //    (2) facsimile transmission completed no later than 5:00 p.m.; or
  //    (3) electronic mail transmitted no later than 5:00 p.m.
  //    (b) One day will be added to the prescribed time if the paper is served
  //        by:
  //    (1) placing the paper in the hands of a commercial delivery service
  //        before midnight for next-day delivery, or
  //    (2) completion of the following after 5:00 p.m. but before midnight:
  //        (A) manual delivery by counsel, counsel's agent or courier, or a
  //        commercial delivery service making same-day delivery; (B)
  //        transmission by facsimile; or (C) transmission by electronic mail.
  //    (c) three days will be added to the prescribed time if the paper is
  //        served by mail. With respect to Parts Five and Five A of the Rules,
  //        this Rule applies only to the time for filing a brief in opposition."
  //
  // FOUR METHODS ARE WORTH 0 OR 1 DAY DEPENDING ONLY ON THE CLOCK. Manual
  // delivery, facsimile, electronic mail and same-day commercial delivery each
  // add nothing at or before 5:00 p.m. and one day after it. No other seeded
  // jurisdiction conditions an amount on time of day, and amount(method) could
  // not express it -- see the context note at the application site.
  //
  // A MISSING service_time IS REFUSED, NOT GUESSED. Defaulting to 0 would be
  // the EARLY direction and defaulting to 1 the LATE one; the rule allows both
  // and the engine knows which only if it is told. This is the one refusal in
  // this file the caller can always fix, and the message says exactly how.
  //
  // COMMERCIAL DELIVERY IS TWO METHODS, NOT ONE, because the rule splits it by
  // the SERVICE BOUGHT rather than by the clock: same-day delivery is treated
  // like manual delivery and follows the 5:00 p.m. cutoff, while next-day
  // delivery adds one day whenever it was handed over before midnight. A single
  // 'commercial_delivery' would have to guess which was purchased, so the two
  // are named separately and a bare 'commercial_delivery' does not qualify.
  //
  // "ADDED TO THE PRESCRIBED TIME" -- period-lengthening, one rollover at the
  // end, the same shape as New Jersey, North Carolina, Washington and New York
  // and NOT the federal after-expiry order. Read from the rule's own words up
  // front rather than caught by a failing test.
  //
  // WHAT THIS DOES NOT REACH: service of the summons and complaint. R. 1:7 runs
  // from "service of a paper upon counsel of record", and Rule 3:8(a)'s answer
  // period runs from service of the summons and complaint on the defendant, who
  // has no counsel of record yet. Same scope route as West Virginia, North
  // Carolina, Washington and New Jersey. It also reaches only periods fixed
  // "under these Rules, or by direction of the court" -- NOT statutory periods,
  // which is the narrower scope its own opening gives it even though the
  // computation statute § 1-210 is broader. No statutory-period row is seeded.
  //
  // PARTS FIVE AND FIVE A ARE CARVED OUT by (c)'s final sentence and no
  // appellate row is seeded, so the carve-out is unreachable today. It is
  // recorded because a future Virginia appellate batch must honour it: there,
  // R. 1:7 reaches ONLY the time for filing a brief in opposition.
  va_rule_1_7: {
    label: 'Va. Sup. Ct. R. 1:7',
    sequence: 'add_to_period_then_roll',
    shape: 'enumerated_allowlist_with_per_method_amount',
    qualifies: function (method) {
      return ({
        manual_delivery: 1, facsimile: 1, electronic_mail: 1,
        commercial_delivery_same_day: 1, commercial_delivery_next_day: 1, mail: 1
      })[method] === 1;
    },
    amount: function (method, ctx) {
      // Fixed amounts first: neither depends on the clock.
      if (method === 'mail') return { add: 3, unit: 'calendar_days' };
      if (method === 'commercial_delivery_next_day') return { add: 1, unit: 'calendar_days' };

      // The remaining four turn on the 5:00 p.m. cutoff.
      var t = ctx && ctx.service_time;
      if (!t || !/^([01]\d|2[0-3]):[0-5]\d$/.test(String(t))) {
        return { refuse: {
          code: 'SERVICE_TIME_REQUIRED',
          message: 'Va. Sup. Ct. R. 1:7 adds NO days for service by ' + String(method).replace(/_/g, ' ') +
            ' completed at or before 5:00 p.m., and ONE day for the same service completed after 5:00 p.m. but before midnight. ' +
            (t ? 'The service_time supplied ("' + t + '") is not a 24-hour HH:MM time. '
               : 'No service_time was supplied. ') +
            'The engine will not choose between the two: guessing 0 days would report a date EARLIER than the true deadline and guessing 1 day LATER. Supply service_time as HH:MM in 24-hour form (for example "16:45" or "17:30") and the extension will be computed. The date below is computed WITHOUT any extension.'
        } };
      }
      var parts = String(t).split(':');
      var minutes = (Number(parts[0]) * 60) + Number(parts[1]);
      // "no later than 5:00 p.m." includes 17:00 exactly; "after 5:00 p.m."
      // begins at 17:01. The boundary minute is worth a test of its own.
      return (minutes <= 17 * 60)
        ? { add: 0, unit: 'calendar_days' }
        : { add: 1, unit: 'calendar_days' };
    }
  },
  // ── MASSACHUSETTS: THREE DAYS FOR ELECTRONIC SERVICE TOO ────────────────
  // Mass. R. Civ. P. 6(d), verbatim in full:
  //
  //   "Whenever a party has the right or is required to do some act within a
  //    prescribed period after the service of a notice or other papers upon
  //    the party and the notice or paper is served upon the party by mail, by
  //    e-mail pursuant to Rule 5(b)(1), or otherwise electronically, including
  //    through the Electronic Filing Service Provider pursuant to Rule 7(b) of
  //    the Massachusetts Rules of Electronic Filing, three (3) days shall be
  //    added to the prescribed period."
  //
  // THE ELECTRONIC LIMB IS THE WHOLE POINT AND IT IS THE OPPOSITE OF FEDERAL
  // PRACTICE. FRCP 6(d) STOPPED extending for electronic service in 2016;
  // Massachusetts extends for it expressly, and names three separate routes
  // (e-mail under Rule 5(b)(1), "or otherwise electronically", and the
  // Electronic Filing Service Provider under Mass. R. Elec. Fil. 7(b)). North
  // Carolina's 6(e), by contrast, reaches MAIL AND ONLY MAIL, and West
  // Virginia's 6(e) is contested precisely because its electronic limb is
  // ambiguous. Three neighbouring answers; this one was read, not inherited.
  // Kentucky's eFiling Rules 13(6) is the closest match found so far.
  //
  // "SHALL BE ADDED TO THE PRESCRIBED PERIOD" -- period-lengthening, one
  // rollover at the end, the same shape as New Jersey, North Carolina,
  // Washington, New York and Virginia, and NOT the federal after-expiry order.
  // Read from the rule's own words up front rather than caught by a test.
  //
  // WHAT THIS DOES NOT REACH: service of the summons and complaint. R. 6(d)
  // runs from "the service of a notice or other papers upon the party", which
  // is Rule 5 service between parties; a summons and complaint go out under
  // Rule 4. Same scope route as West Virginia, North Carolina, Washington,
  // New Jersey and Virginia. The answer row therefore carries no extension.
  //
  // ONE MASSACHUSETTS ROW REFUSES THIS EXTENSION BY THE RULE'S OWN WORDS, and
  // it is worth knowing before someone "fixes" it: R. 33(a)(4)'s 40-day period
  // says "The period of time set forth in the previous sentence shall be
  // deemed to include the three day period allowed pursuant to Rule 6(d)."
  // The three days are already inside the 40. Adding them again would extend a
  // deadline the rule does not extend, so that row deliberately carries no
  // service_extension at all. See its note in the seed.
  ma_rcp_6d: {
    label: 'Mass. R. Civ. P. 6(d)',
    sequence: 'add_to_period_then_roll',
    shape: 'enumerated_allowlist',
    qualifies: function (method) {
      return ({ mail: 1, email: 1, electronic: 1, efiling_service_provider: 1 })[method] === 1;
    }
  },
  // ── MISSOURI: MAIL AND ONLY MAIL, BECAUSE THE OTHER METHODS ARE HANDLED
  //    BY A COMPLETION RULE INSTEAD ─────────────────────────────────────────
  // Mo. R. Civ. P. 44.01(d), verbatim in full:
  //
  //   "Whenever a party has the right or is required to do some act or take some
  //    proceedings within a prescribed period after the service of a notice or
  //    other paper upon the party and the notice or paper is served by mail,
  //    three days shall be added to the prescribed period."
  //
  // MAIL-ONLY ON ITS FACE, AND UNLIKE TENNESSEE THAT READING IS CORRECT -- but
  // it is only correct once the SERVICE rule has been read. Tenn. R. Civ. P.
  // 6.05 is worded almost identically and IS wrong read alone, because Tenn.
  // R. 5.02(2)(c) and (3)(e) deem e-mail and E-service to be mail. Missouri's
  // R. 43.01(d) contains no such deeming provision; it moves WHEN SERVICE IS
  // COMPLETE instead. So electronic service in Missouri collects NO days here
  // and is governed by SERVICE_COMPLETION_STANDARDS.mo_rule_43_01_d.
  //
  // DO NOT WIDEN qualifies() TO ELECTRONIC METHODS. Doing so would add three
  // days the rule does not give AND double up with the completion shift, which
  // is why the endpoint validator refuses any row listing one method under both
  // mechanisms.
  //
  // "ADDED TO THE PRESCRIBED PERIOD" -- period-lengthening, one rollover at the
  // end, like New Jersey, North Carolina, Washington, New York, Virginia and
  // Massachusetts, and NOT the federal after-expiry order.
  mo_rule_44_01_d: {
    label: 'Mo. R. Civ. P. 44.01(d)',
    sequence: 'add_to_period_then_roll',
    shape: 'enumerated_allowlist',
    qualifies: function (method) { return method === 'mail'; }
  },
  // ── MINNESOTA: MAIL GETS THREE, EVERYTHING ELSE GETS THE CLOCK ──────────
  // Minn. R. Civ. P. 6.01(e), verbatim in full:
  //
  //   "Whenever a party has the right or is required to do some act or take some
  //    proceedings within a prescribed period after the service of a notice or
  //    other document upon the party, and the notice or document is served upon
  //    the party by United States Mail, THREE DAYS shall be added to the
  //    prescribed period. If service is made BY ANY MEANS OTHER THAN UNITED
  //    STATES MAIL and accomplished AFTER 5:00 P.M. local Minnesota time on the
  //    day of service, ONE ADDITIONAL DAY shall be added to the prescribed
  //    period."
  //
  // THE SECOND LIMB IS A NEGATIVE CONDITION, NOT AN ALLOWLIST, and that is the
  // thing most likely to be got wrong by copying a neighbour. It reaches "any
  // means other than United States Mail" -- facsimile, e-mail, the e-filing
  // system, personal delivery, leaving it at an office, anything. Every other
  // state with a clock rule ENUMERATES the methods it covers: Virginia names
  // four, Wisconsin names three, Missouri names three. Minnesota names none and
  // catches the complement. A qualifies() copied from any of them would silently
  // give 0 days to a method Minnesota does extend for -- EARLY, and wrong.
  //
  // SO qualifies() RETURNS TRUE FOR EVERYTHING, and amount() does the work. A
  // non-mail method served before 5:00 p.m. legitimately yields {add: 0}, which
  // reports as `applied` with 0 days -- the same honest shape Virginia uses for
  // its at-or-before-5:00-p.m. case, and deliberately NOT `not_qualifying`,
  // which would mean the rule grants nothing for that method at all.
  //
  // THE BOUNDARY IS CLEAN, UNLIKE WISCONSIN'S. "after 5:00 p.m." means 17:00
  // exactly is NOT after -- the same reading Va. R. 1:7's "no later than 5:00
  // p.m." compels. Wisconsin's "completed between 5 p.m. and midnight" is
  // genuinely ambiguous at 17:00 and is recorded as such in its gate.
  //
  // AND THERE IS NO MIDNIGHT CEILING. The limb turns only on "after 5:00 p.m.
  // ... on the day of service". Missouri's and Virginia's both stop at midnight;
  // Minnesota's does not need to, because it is measured against the day of
  // service rather than against a window.
  //
  // A service_time IS REQUIRED for any non-mail method and the engine REFUSES
  // rather than guessing, because 0 and 1 are both available and only the caller
  // knows which. Soft refusal, like Virginia: the date is still computable
  // without the extension, so it is returned with the refusal attached. Contrast
  // Missouri's HARD refusal, which is a different mechanism entirely -- there an
  // unknown time means an unknown period START.
  mn_rcp_6_01_e: {
    label: 'Minn. R. Civ. P. 6.01(e)',
    sequence: 'add_to_period_then_roll',
    shape: 'negative_condition_with_per_method_amount',
    qualifies: function () { return true; },
    amount: function (method, ctx) {
      if (method === 'mail' || method === 'us_mail') return { add: 3, unit: 'calendar_days' };
      var t = ctx && ctx.service_time;
      if (!t || !/^([01]\d|2[0-3]):[0-5]\d$/.test(String(t))) {
        return { refuse: {
          code: 'SERVICE_TIME_REQUIRED',
          message: 'Minn. R. Civ. P. 6.01(e) adds NOTHING for service by ' + String(method).replace(/_/g, ' ') +
            ' accomplished at or before 5:00 p.m. local Minnesota time, and ONE day for the same service ' +
            'accomplished after 5:00 p.m. on the day of service. ' +
            (t ? 'The service_time supplied ("' + t + '") is not a 24-hour HH:MM time. '
               : 'No service_time was supplied. ') +
            'The engine will not choose between the two: guessing 0 days would report a date EARLIER than the true deadline and guessing 1 day LATER. Supply service_time as HH:MM in 24-hour form (for example "16:45" or "17:30") and the extension will be computed. The date below is computed WITHOUT any extension.'
        } };
      }
      var parts = String(t).split(':');
      var minutes = (Number(parts[0]) * 60) + Number(parts[1]);
      // "after 5:00 p.m." begins at 17:01; 17:00 exactly is not after it.
      return (minutes <= 17 * 60)
        ? { add: 0, unit: 'calendar_days' }
        : { add: 1, unit: 'calendar_days' };
    }
  },

  // NEVADA. Textually the federal rule, and it gets its own entry rather than
  // being mapped onto frcp_6d so the audit trail cites Nevada to a Nevada
  // practitioner. NRCP 6(d): "When a party may or must act within a specified
  // time after being served and service is made under Rule 5(b)(2)(C) (mail),
  // (D) (leaving with the clerk), or (F) (other means consented to), 3 days are
  // added after the period would otherwise expire under Rule 6(a)."
  //
  // "ADDED AFTER THE PERIOD WOULD OTHERWISE EXPIRE" is the federal sequencing,
  // so roll_then_add_then_roll -- not the add_to_period_then_roll that Texas,
  // New York, Georgia, North Carolina, Washington, New Jersey, Virginia,
  // Massachusetts, Missouri and Minnesota use. Read from the words, not assumed
  // from the number being three.
  //
  // WEST VIRGINIA'S DEFECT WAS CHECKED FOR HERE AND IS ABSENT. WV's 6(e) points
  // at Rule 5(b)(2)(F) while labelling it "(other means consented to)", which is
  // the text of its (G) -- the pointer and the parenthetical name different
  // subparagraphs, and this engine refuses both contested methods rather than
  // choosing a reading. Nevada is worded identically, so NRCP 5(b)(2) was read
  // directly: (A) handing, (B) leaving at office/dwelling, (C) MAILING,
  // (D) LEAVING WITH THE COURT CLERK, (E) electronic, (F) DELIVERING BY ANY
  // OTHER MEANS CONSENTED TO IN WRITING. Every pointer matches its
  // parenthetical. Nothing to refuse. Recorded as a CHECKED negative rather
  // than an unexamined one, because the check is the only thing that separates
  // this from West Virginia.
  //
  // ELECTRONIC SERVICE UNDER (E) TAKES NOTHING, because 6(d) does not list it.
  // That is the available mistake in Nevada practice for the same reason it is
  // in West Virginia and New York -- e-service feels like it should behave like
  // mail. It is not an omission here; it is the rule.
  //
  // NO EXCLUSIVITY CONDITION, unlike Utah's URCP 6(c), whose seven days apply
  // only to service made "exclusively by mail" and which this engine therefore
  // cannot express. Nevada's is a plain method allowlist and seeds normally.
  nv_nrcp_6_d: {
    label: 'Nev. R. Civ. P. 6(d)',
    sequence: 'roll_then_add_then_roll',
    shape: 'enumerated_allowlist',
    qualifies: function (method) {
      return method === 'mail' || method === 'left_with_clerk' || method === 'other_consented_means';
    }
  },

  // UTAH. HELD OUT OF THE SEED FROM 2026-08-27 UNTIL THE EXCLUSIVITY MECHANISM
  // EXISTED, which is the whole reason that mechanism was built. URCP 6(c):
  //
  //   "When a party may or must act within a specified time after service and
  //    service is made EXCLUSIVELY BY MAIL under Rule 5(b)(3)(C)(i), 7 days are
  //    added after the period would otherwise expire under paragraph (a)."
  //
  // SEVEN, not three. Every seeded jurisdiction except California adds three or
  // five; copying a neighbour's three here computes FOUR DAYS EARLY on every
  // mailed Utah period. The number is the easy part.
  //
  // THE HARD PART IS "EXCLUSIVELY", and it is why this row waited. Until the
  // engine could be told the whole SET of methods used, applying seven days on
  // a bare service_method of `mail` meant guessing that mail was the only
  // method -- and being wrong by a WEEK in the LATE direction whenever it was
  // not. Seeding it with a disclosure would have been the wrong trade: seven
  // days is far too large an overshoot to assume.
  //
  // SO THIS ROW SETS on_unknown_exclusivity: 'refuse', WHERE FLORIDA'S SETS
  // 'assume_exclusive'. The two differ deliberately and the reasons are
  // different, not arbitrary:
  //   - Florida (2.514(b), five days) was ALREADY LIVE and answering, and its
  //     assumption is usually right -- a Florida party served by mail is
  //     typically one for whom portal e-service is unavailable, so "only mail"
  //     is usually literally true. Refusing would report EARLY on most mailed
  //     Florida answers, trading a rare late error for a frequent early one.
  //   - Utah has no existing arithmetic to preserve, and 5(b)(3)(C) permits
  //     mail only where the party "does not have an electronic filing account
  //     OR EMAIL" -- so a Utah party served by mail may well also have been
  //     served another way. Seven days is too much to assume on that.
  //
  // SCOPE: 6(c) points at Rule 5(b)(3)(C)(i) specifically, so like FRCP 6(d)
  // and Nev. R. Civ. P. 6(d) it reaches only papers served between parties.
  // Utah's summons goes out under Rule 4, so NEITHER answer-to-summons row
  // carries this -- the same reading that corrected the two federal rows.
  ut_urcp_6_c: {
    label: 'Utah R. Civ. P. 6(c)',
    sequence: 'roll_then_add_then_roll',
    shape: 'enumerated_allowlist',
    qualifies: function (method) { return method === 'mail'; }
  },

  // OREGON. The BROADEST enumeration in the platform, and the only rule that
  // states its own Rule 4 / Rule 5 scope split outright. ORCP 10 B:
  //
  //   "EXCEPT FOR SERVICE OF SUMMONS, whenever a party has the right to or is
  //    required to do some act within a prescribed period after the service of
  //    a notice or other document upon that party and the notice or document is
  //    served by MAIL, E-MAIL, FACSIMILE COMMUNICATION, OR ELECTRONIC SERVICE,
  //    3 days shall be added to the prescribed period."
  //
  // ALL FOUR METHODS QUALIFY, INCLUDING E-MAIL AND ELECTRONIC SERVICE. That is
  // the opposite of Nevada, West Virginia, New York and the federal rule, where
  // e-service deliberately takes nothing, and it matches Massachusetts and
  // Arkansas. An allowlist copied from the federal family would UNDER-count and
  // compute EARLY.
  //
  // "ADDED TO THE PRESCRIBED PERIOD" -> add_to_period_then_roll, the
  // period-lengthening order, not the federal after-expiry one.
  //
  // "EXCEPT FOR SERVICE OF SUMMONS" IS THE SENTENCE'S FIRST CLAUSE, and it
  // removes the single most repeated inference in this engine. Every other
  // jurisdiction required working out from WHICH RULE authorises the service
  // whether an answer deadline takes the extension -- an inference that had
  // been got wrong on two federal rows, and that Arkansas states in a proviso.
  // Oregon says it in four words at the front. No Oregon row running from
  // service of the summons carries this standard.
  //
  // NO EXCLUSIVITY CONDITION -- Utah's and Florida's problem does not appear.
  or_orcp_10_b: {
    label: 'Or. R. Civ. P. 10 B',
    sequence: 'add_to_period_then_roll',
    shape: 'enumerated_allowlist',
    qualifies: function (method) {
      return method === 'mail' || method === 'email' ||
             method === 'facsimile' || method === 'electronic';
    }
  },

  // OKLAHOMA. 12 O.S. 2006(D), verbatim on the operative part:
  //
  //   "the notice or paper is served upon the party by MAIL, THIRD-PARTY
  //    COMMERCIAL CARRIER OR ELECTRONIC MEANS, three (3) days shall be ADDED
  //    TO THE PRESCRIBED PERIOD"
  //
  // "Added to the prescribed period" -> add_to_period_then_roll, the
  // period-lengthening order, not the federal after-expiry one.
  //
  // ELECTRONIC MEANS QUALIFIES, as in Oregon, Massachusetts and Arkansas and
  // unlike Nevada, West Virginia, New York and the federal rule. And Oklahoma
  // is the ONLY seeded jurisdiction naming THIRD-PARTY COMMERCIAL CARRIER as
  // its own category -- Texas lists commercial delivery service among its
  // service methods but extends for mail alone, so the two must not be read
  // across.
  //
  // WHAT THIS STANDARD DOES NOT COVER, AND MUST NOT BE MADE TO: the proviso in
  // the same subsection. "provided, however, when a summons and petition are
  // served by mail, a defendant shall serve an answer within twenty (20) days
  // or thirty-five (35) days ... AFTER THE DATE OF RECEIPT OR IF REFUSED, THE
  // DATE OF REFUSAL of the summons and petition". That is a DIFFERENT TRIGGER,
  // not a different amount -- the answer runs from receipt or refusal rather
  // than from service, and takes NO three days. It is seeded as its own rows
  // with receipt/refusal trigger names; a caller who supplied a service date
  // to the ordinary answer row instead would compute EARLY.
  ok_12_2006_d: {
    label: '12 O.S. § 2006(D)',
    sequence: 'add_to_period_then_roll',
    shape: 'enumerated_allowlist',
    qualifies: function (method) {
      return method === 'mail' || method === 'third_party_commercial_carrier' ||
             method === 'electronic';
    }
  },

  // SOUTH CAROLINA. FIVE days, not three, and the rule's own drafting Note
  // says why: "This Rule 6(e) is the same as the Federal Rule except that the
  // additional time to take an act after service is by mail is INCREASED FROM
  // 3 TO 5 DAYS." Every seeded state adds three except California's and New
  // York's per-method tables and New Jersey's five. A three-day extension
  // carried over from a neighbour computes TWO DAYS EARLY on every mailed
  // South Carolina period.
  //
  // IT ALSO REACHES SERVICE UPON A STATUTORY AGENT, which no other seeded rule
  // does: "served upon him by mail OR UPON A PERSON DESIGNATED BY STATUTE TO
  // ACCEPT SERVICE". That is its own method here, not a variety of mail.
  //
  // E-MAIL IS THE OPEN QUESTION, AND THE DEFAULT IS DELIBERATE. A web search
  // returns, as Rule 6(e), a sentence extending the five days to e-mail. THAT
  // SENTENCE IS NOT IN RULE 6(e) -- the rule was read verbatim from
  // sccourts.org and contains no e-mail language at all. The 2022 Supreme
  // Court order "RE: Service by E-Mail in the Trial Courts" (Appellate Case
  // No. 2022-000029, 6 May 2022) was then read end to end: paragraphs (a)
  // through (f), and NO time-extension provision whatsoever.
  //
  // So on the two primary sources actually read, whether the five days reach
  // e-mail is UNRESOLVED. THE DIRECTION DECIDES THE DEFAULT: if e-mail does
  // collect them and we omit them, the date is EARLY -- safe. If it does not
  // and we add them, the date is LATE -- the direction that misses a filing.
  // So e-mail does NOT qualify here, and the seed discloses the question.
  // Do not widen this on the strength of a search summary.
  sc_rcp_6_e: {
    label: 'S.C. R. Civ. P. 6(e)',
    sequence: 'add_to_period_then_roll',
    shape: 'enumerated_allowlist',
    qualifies: function (method) {
      return method === 'mail' || method === 'statutory_agent';
    }
  },
  // ARCP 6(d). THREE BUSINESS DAYS, and every word of that matters.
  //
  // BUSINESS DAYS, NOT CALENDAR DAYS. Almost every other extension on this
  // platform adds calendar days; writing calendar_days here out of habit
  // would compute EARLY across every weekend the extension spans. The unit
  // lives on the rule row, not here, but it is stated here because this is
  // where someone copying a neighbour would look.
  //
  // ELECTRONIC SERVICE IS EXPRESSLY INCLUDED -- 'e-mail or service through
  // the court's electronic filing system pursuant to Rule 5(b)(2)'. That is
  // the OPPOSITE of the federal rule, Nevada, West Virginia and New York,
  // where e-service is deliberately outside the extension. An allowlist
  // copied from any of them under-counts and computes EARLY.
  //
  // THE ANSWER CARVE-OUT IS NOT HANDLED HERE, DELIBERATELY. 6(d)'s proviso
  // withholds the three days from an answer when the summons was served by
  // mail or commercial delivery under Rule 4. That is a property of the ROW,
  // so the Rule 12(a)(1) rows simply carry no service_extension at all --
  // the same shape the federal 12(a)(1)(A)(i) row was corrected to on
  // 2026-08-27. Arkansas states in its own text what FRCP 6(d) leaves to be
  // inferred from a cross-reference.
  ar_rcp_6_d: {
    label: 'Ark. R. Civ. P. 6(d)',
    // 'three (3) business days shall be added to the prescribed period' --
    // the days lengthen the period rather than following its expiry, so the
    // weekend/holiday rollover acts once, on the end of the lengthened
    // period. Same reading as N.Y. CPLR 2103(b).
    sequence: 'add_to_period_then_roll',
    shape: 'enumerated_allowlist',
    qualifies: function (method) {
      return ({ mail: 1, commercial_delivery: 1, electronic: 1, email: 1,
        efiling_service_provider: 1 })[method] === 1;
    }
  },
  // Ala. R. Civ. P. 6(d). THE ORDER IS FEDERAL, AND THAT IS THE TRAP.
  // "3 days are added AFTER THE PERIOD WOULD OTHERWISE EXPIRE under Rule
  // 6(a)" -- roll the base period first, add three, then roll again. Nearly
  // every state seeded recently is period-lengthening instead (NJ, NC, WA,
  // NY, VA, MA, MO, MN, SC, and Arkansas above), and the two orders give
  // DIFFERENT dates whenever the unrolled last day lands on a weekend or
  // holiday. The error is not consistently in the safe direction -- it
  // depends where the base period falls -- so this is read from 6(d)'s own
  // words rather than inherited.
  //
  // E-FILING-SYSTEM SERVICE DOES GET THE THREE DAYS, enumerated in the rule
  // itself alongside mail: "service is made under Rule 5(b)(2)(C) (by mail)
  // or (E) (through the court's electronic-filing system)".
  //
  // AND THE ANSWER ROW STILL TAKES NOTHING. 6(d) reaches service made under
  // RULE 5(b)(2) only; a summons and complaint go out under Rule 4. Same
  // structure as the federal rule, and the same correction the federal rows
  // needed on 2026-08-27 -- Arkansas says it in a proviso, Alabama leaves it
  // to the cross-reference, and the answer is the same.
  al_rcp_6_d: {
    label: 'Ala. R. Civ. P. 6(d)',
    sequence: 'roll_then_add_then_roll',
    shape: 'enumerated_allowlist',
    qualifies: function (method) {
      return ({ mail: 1, efiling_service_provider: 1, electronic: 1 })[method] === 1;
    }
  },
  // Wis. Stat. Sec. 801.15(5). THIS IS VIRGINIA'S MECHANISM, NOT MISSOURI'S.
  // The 5 p.m. clock decides HOW MANY DAYS ARE ADDED (0 or 1), not when
  // service was complete -- so it reuses the existing amount(method, ctx)
  // shape and needs no new engine mechanism. Missouri's service-COMPLETION
  // table is not involved.
  //
  // Fifth distinct answer on electronic service across the states gated:
  //   Massachusetts  +3, in the time rule
  //   Tennessee      service rule DEEMS it mail -> +3
  //   Missouri       +0, the TRIGGER DATE moves
  //   Maryland       +0, expressly negated
  //   Wisconsin      +1 if completed between 5 p.m. and midnight, else +0
  //
  // TWO BOUNDARY READINGS, BOTH DELIBERATE AND BOTH DISCLOSED:
  // (1) EXACTLY 17:00 ADDS NOTHING. The statute says "completed between 5
  //     p.m. and midnight", and "between" does not settle whether 5 p.m.
  //     itself is inside. Virginia's text is explicit where this is not.
  //     Reading 17:00 as inside would add a day and report LATER than the
  //     true deadline; reading it as outside reports EARLIER. The engine
  //     takes the earlier reading, because a date that is too early costs a
  //     day of preparation and a date that is too late costs the filing.
  // (2) A TRANSMISSION AFTER MIDNIGHT BUT BEFORE 5 P.M. -- 02:00, say -- is
  //     NOT "between 5 p.m. and midnight" and adds NOTHING. A naive
  //     "after 5 p.m." implementation would wrongly add a day.
  wi_801_15_5: {
    label: 'Wis. Stat. Sec. 801.15(5)',
    // "shall be added to the prescribed period" -- the days lengthen the
    // period, so the rollover acts once, at the end.
    sequence: 'add_to_period_then_roll',
    shape: 'enumerated_allowlist_with_per_method_amount',
    qualifies: function (method) {
      return ({ mail: 1, facsimile: 1, electronic_mail: 1,
        efiling_service_provider: 1 })[method] === 1;
    },
    amount: function (method, ctx) {
      // Mail is a fixed three and does not touch the clock.
      if (method === 'mail') return { add: 3, unit: 'calendar_days' };

      var t = ctx && ctx.service_time;
      if (!t || !/^([01]\d|2[0-3]):[0-5]\d$/.test(String(t))) {
        return { refuse: {
          code: 'SERVICE_TIME_REQUIRED',
          message: 'Wis. Stat. Sec. 801.15(5)(b) adds ONE day for service by ' +
            String(method).replace(/_/g, ' ') + ' completed between 5 p.m. and midnight, and NOTHING for the ' +
            'same service completed at any other hour -- including after midnight and before 5 p.m. ' +
            (t ? 'The service_time supplied ("' + t + '") is not a 24-hour HH:MM time. '
               : 'No service_time was supplied. ') +
            'The engine will not choose between the two: guessing 1 day would report a date LATER than the ' +
            'true deadline. Supply service_time as HH:MM in 24-hour form (for example "16:45" or "17:30"). ' +
            'The date below is computed WITHOUT any extension.'
        } };
      }
      // Strictly AFTER 17:00 and before midnight. 17:00 exactly is outside.
      var mins = parseInt(String(t).slice(0, 2), 10) * 60 + parseInt(String(t).slice(3), 10);
      return (mins > 17 * 60)
        ? { add: 1, unit: 'calendar_days' }
        : { add: 0, unit: 'calendar_days' };
    }
  },
  // Md. Rule 1-203(c). Three days for MAIL ONLY -- Maryland is the fourth
  // distinct answer on electronic service and its answer is that there is
  // no electronic limb at all: (c) names mail and nothing else.
  //
  // ── IT REFUSES ON A SHORT PERIOD, AND THAT IS THE WHOLE POINT. ──
  // 1-203(c) adds three days "to the prescribed period". 1-203(a) drops
  // intermediate weekends and holidays when "the period of time allowed is
  // seven days or less". So a mailed 7-day period arguably becomes a
  // 10-day period, which is more than seven, which would FLIP the
  // intermediate days from excluded to counted and change the date. Two
  // live readings:
  //   (A) "the period of time allowed" means the period AFTER the mail
  //       extension -> the exclusion is lost -> an EARLIER date;
  //   (B) it means the underlying rule's period -> the exclusion survives
  //       and the three days are appended -> a LATER date.
  // No committee note, no cross-reference and no controlling authority was
  // found. They diverge on any mailed period of 4-7 days.
  //
  // THIS CANNOT BE RESOLVED BY PICKING THE SAFE SIDE, because which
  // reading is safe depends on the period -- unlike every other ambiguity
  // on this platform, where one direction is always the conservative one.
  // So the engine REFUSES and returns the unextended date, the same call
  // already made for West Virginia's contested Rule 6(e). Michael's
  // decision, 2026-08-30.
  md_rule_1_203_c: {
    label: 'Md. Rule 1-203(c)',
    sequence: 'add_to_period_then_roll',
    shape: 'enumerated_allowlist_with_per_method_amount',
    qualifies: function (method) { return method === 'mail'; },
    amount: function (method, ctx) {
      var n = ctx && ctx.base_period_count;
      var unit = ctx && ctx.base_period_unit;
      if (unit === 'calendar_days' && typeof n === 'number' && n <= 7) {
        return { refuse: {
          code: 'CONTESTED_SHORT_PERIOD_INTERACTION',
          message: 'Md. Rule 1-203(c) adds three days for service by mail, and Md. Rule 1-203(a) drops ' +
            'intermediate Saturdays, Sundays and holidays when the period allowed is seven days or less. ' +
            'This period is ' + n + ' days, so the two provisions interact and Maryland has not said how: ' +
            'if the three days make the period "more than seven days", the intermediate days become ' +
            'COUNTED and the deadline moves EARLIER; if the seven-day test looks at the underlying rule ' +
            'instead, they stay excluded and the three days are appended, moving it LATER. No committee ' +
            'note, cross-reference or controlling authority resolves it. The engine will not choose: ' +
            'unlike the other ambiguities it handles, there is no consistently safe side here -- which ' +
            'reading is conservative depends on the length of the period. The date below is computed ' +
            'WITHOUT the three days. Add them by hand only after deciding which reading applies.'
        } };
      }
      return { add: 3, unit: 'calendar_days' };
    }
  },
  // K.S.A. 60-206(d). THE ORDER IS FEDERAL after-expiry -- "three days are
  // added AFTER THE PERIOD WOULD OTHERWISE EXPIRE under subsection (a)" --
  // the same sequencing words as FRCP 6(d) and Alabama's Rule 6(d), and the
  // opposite of the period-lengthening order most recently seeded states use.
  //
  // AND THERE IS NO ELECTRONIC LIMB AT ALL. 60-206(d) reaches service under
  // K.S.A. 60-205(b)(2)(C) (mail) or (D) (leaving with the clerk) and nothing
  // else. E-mail and e-filing get NOTHING, which is the federal position and
  // the opposite of Arkansas, Alabama and Massachusetts. A qualifies() copied
  // from any of those would over-count and report LATE.
  ks_60_206_d: {
    label: 'K.S.A. 60-206(d)',
    sequence: 'roll_then_add_then_roll',
    shape: 'enumerated_allowlist',
    qualifies: function (method) {
      return method === 'mail' || method === 'left_with_clerk';
    }
  },
  // MISSISSIPPI. Miss. R. Civ. P. 6(e), verbatim and complete:
  //
  //   "Whenever a party has the right or is required to do some act or take
  //    some proceedings within a prescribed period after the service of a
  //    notice or other paper upon him and the notice or paper is served upon
  //    him BY MAIL, three days shall be ADDED TO THE PRESCRIBED PERIOD. This
  //    subdivision does not apply to responses to service of summons under
  //    Rule 4."
  //
  // "ADDED TO THE PRESCRIBED PERIOD" -> add_to_period_then_roll, the
  // period-lengthening order, and NOT the federal after-expiry order Kansas
  // and Alabama use. The two diverge whenever the unextended last day lands on
  // a weekend or a holiday.
  //
  // MAIL AND NOTHING ELSE, AND THAT IS THE FINDING, because Mississippi has
  // had electronic service since 1989. Rule 5(b)(1) expressly permits service
  // "by transmitting it to him by electronic means", by "leaving it with the
  // clerk of the court", and by "transmitting it to the clerk by electronic
  // means"; Rule 5(b)(2) routes service through the Mississippi Electronic
  // Court System wherever a court has adopted it by local rule. Rule 6(e) was
  // never widened to reach any of them. So e-mail, the MEC system and
  // leaving-with-the-clerk all get ZERO -- unlike Kansas, which does extend
  // for leaving with the clerk, and unlike Arkansas, Alabama, Massachusetts,
  // Oregon and Oklahoma, which all extend for electronic service. Copying any
  // of those qualifies() here over-counts and reports LATE.
  //
  // THE RULE 4 CARVE-OUT IS EXPRESS, not inferred from the Rule 5/Rule 4
  // distinction the way it is federally. No answer row triggered by service of
  // the summons and complaint carries this extension at all; the seed omits
  // service_extension from those rows rather than relying on a caller not to
  // pass a service_method.
  ms_r_civ_p_6_e: {
    label: 'Miss. R. Civ. P. 6(e)',
    sequence: 'add_to_period_then_roll',
    shape: 'enumerated_allowlist',
    qualifies: function (method) {
      return method === 'mail';
    }
  },
  // NEW MEXICO. Rule 1-006(C) NMRA as amended effective 31 December 2024,
  // verbatim and complete:
  //
  //   "When a party may or must act within a specified time after service and
  //    service is made by MAIL, FACSIMILE, or by DEPOSIT AT A LOCATION
  //    DESIGNATED FOR AN ATTORNEY AT A COURT FACILITY under Rule
  //    1-005(C)(1)(e) NMRA, three (3) days are ADDED AFTER THE PERIOD WOULD
  //    OTHERWISE EXPIRE under Paragraph A. Intermediate Saturdays, Sundays,
  //    and legal holidays ARE INCLUDED in counting these added three (3) days.
  //    If the third day is a Saturday, Sunday, or legal holiday, the last day
  //    to act is the next day that is not a Saturday, Sunday, or legal
  //    holiday."
  //
  // ⚠ ELECTRONIC TRANSMISSION WAS REMOVED, AND EVERY SECONDARY SOURCE STILL
  // SAYS OTHERWISE. Supreme Court Order No. S-1-RCR-2023-00046, approved 1
  // November 2024 and effective for all cases pending or filed on or after 31
  // December 2024, struck "electronic transmission," from this list. The
  // approved-amendment PDF shows it bracketed for deletion and the CLEAN text
  // in the official NMRA compilation no longer contains it -- both were read,
  // because a redline alone is not the operative text. Granting three days for
  // e-service or e-filing here reports THREE DAYS LATE, and that is the answer
  // a search engine will hand you: the pre-2024 wording is still what most
  // secondary sources quote.
  //
  // THE ASYMMETRY IS REAL AND IS NOT A DRAFTING SLIP TO BE "FIXED" HERE.
  // Rule 1-005(C)(1)(b) makes "sending a copy by facsimile OR electronic
  // transmission" one sub-limb of what "delivering a copy" means -- the two
  // are siblings in the service rule -- and Rule 1-006(C) now extends for one
  // and not the other. Encode what the time rule says, not what the symmetry
  // suggests.
  //
  // "ADDED AFTER THE PERIOD WOULD OTHERWISE EXPIRE" -> roll_then_add_then_roll,
  // the federal order, and the rule then spells out both halves of that
  // sequence explicitly: the three added days count straight through weekends
  // and holidays even when the BASE period was a ten-day-or-less period that
  // excluded them, and the result rolls again if it lands badly. New Mexico is
  // the only seeded jurisdiction whose text states the whole sequence rather
  // than leaving the second roll to be inferred.
  //
  // NO ROW TRIGGERED BY SERVICE OF PROCESS CARRIES THIS, and there is no
  // express carve-out saying so -- the same position as Wisconsin, resolved
  // the same way. Rule 1-005(A) governs "every pleading SUBSEQUENT TO THE
  // ORIGINAL COMPLAINT", original process is Rule 1-004, and Rule 1-006(C)
  // defines its own third method by cross-reference INTO Rule 1-005(C)(1)(e).
  // That is a structural reading and not a quotation, so it is resolved in the
  // safe direction: withholding the three days reports EARLY, granting them on
  // a mailed summons would report LATE.
  nm_1_006_c: {
    label: 'Rule 1-006(C) NMRA',
    sequence: 'roll_then_add_then_roll',
    shape: 'enumerated_allowlist',
    qualifies: function (method) {
      return method === 'mail' || method === 'facsimile' ||
             method === 'court_facility_deposit';
    }
  },
  // IDAHO. I.R.C.P. 2.2(c), verbatim and complete -- it is one sentence, and
  // the shortest service-extension provision of any seeded jurisdiction:
  //
  //   "(c) Additional Time After Service by Mail. When a party may or must act
  //    within a specified time after service and service is made BY MAIL, 3
  //    days are ADDED TO THE SPECIFIED TIME."
  //
  // "ADDED TO THE SPECIFIED TIME" -> add_to_period_then_roll, the
  // period-lengthening order, not the federal after-expiry one.
  //
  // MAIL AND NOTHING ELSE, and unlike Mississippi that is not a survival from
  // an older draft -- Idaho wrote this rule from scratch in 2016, when
  // electronic service was already routine, and still reached only mail.
  // E-mail, the iCourt e-filing system, facsimile and hand delivery all get
  // ZERO.
  //
  // ⚠ IT SAYS "AFTER SERVICE", NOT "AFTER SERVICE OF A NOTICE OR OTHER PAPER",
  // AND THAT ONE MISSING PHRASE DECIDES A ROW. Miss. R. Civ. P. 6(e) reaches
  // "the service of a NOTICE or other paper", which is why Mississippi's
  // post-motion row -- triggered by "notice of the court's action" -- carries
  // the extension. Idaho's Rule 12(a)(2)(A) runs from "notice of the court's
  // action" too, but Rule 2.2(c) has no notice limb, so that row carries
  // NOTHING here. Two states, near-identical triggers, opposite answers, and
  // the difference is four words in the time rule.
  //
  // NO ROW TRIGGERED BY SERVICE OF PROCESS CARRIES THIS. There is no express
  // Rule 4 carve-out -- the Wisconsin and New Mexico position, resolved the
  // same way. I.R.C.P. 5(a)(1)(B) reaches "a pleading filed AFTER THE ORIGINAL
  // COMPLAINT"; original process is Rule 4. Withholding reports EARLY, granting
  // on a mailed summons would report LATE.
  id_ircp_2_2_c: {
    label: 'I.R.C.P. 2.2(c)',
    sequence: 'add_to_period_then_roll',
    shape: 'enumerated_allowlist',
    qualifies: function (method) {
      return method === 'mail';
    }
  },
  // NEBRASKA. Neb. Ct. R. Pldg. § 6-1106(c), verbatim:
  //
  //   "Additional Time After Service by Mail. When a party may or must act
  //    within a specified time after being served and service is made under
  //    § 6-1105(b)(3)(C), 3 days are ADDED AFTER THE PERIOD WOULD OTHERWISE
  //    EXPIRE."
  //
  // ★ THE COURT SETTLED THIS ENGINE'S EXACT AMBIGUITY IN 2024, IN WRITING.
  // Comment [2] to § 6-1106: "The original version of the rule provided that 3
  // days were added to the applicable time period when a document was served by
  // mail. IT WAS UNCLEAR WHETHER THE 3 DAYS WERE ADDED TO THE TIME PERIOD ITSELF
  // OR AT THE END OF THE TIME PERIOD as computed by § 25-2221. In 2024, the
  // provision ... was reworded to clarify that the 3 days are added after the
  // period would otherwise expire."
  //
  // That is the add_to_period_then_roll / roll_then_add_then_roll distinction,
  // named by a court, identified as genuinely ambiguous, and resolved by
  // amendment. Every other jurisdiction here had to be read for it. Nebraska
  // says which one it is and why the words changed -- and it means every
  // Nebraska mailed deadline computed against the PRE-2025 rule text may be a
  // day out.
  //
  // Comment [3] then works an example, which the test asserts verbatim: "answers
  // to interrogatories are normally due 30 days after service ... If the 30th
  // day is a Saturday, the period would expire on Monday ... Adding 3 days after
  // the period would otherwise expire (Monday) extends the period to Thursday."
  //
  // MAIL ONLY, AND THE DRAFTING IS THE SHARPEST ON THE PLATFORM. It does not say
  // "by mail" -- it cross-references ONE lettered subparagraph, § 6-1105(b)(3)(C),
  // out of six sibling methods sitting beside it: (A) handing it to the person,
  // (B) leaving it at an office or residence, (C) MAILING, (D) email, (E) a
  // designated delivery service under Neb. Rev. Stat. § 25-505.01(1)(d), and
  // (F) any other consented or court-authorised means. Electronic service
  // through the court-authorized service provider is a separate limb again,
  // § 6-1105(b)(2). Five named alternatives get nothing, and the rule picked one
  // by letter.
  ne_6_1106_c: {
    label: 'Neb. Ct. R. Pldg. § 6-1106(c)',
    sequence: 'roll_then_add_then_roll',
    shape: 'enumerated_allowlist',
    qualifies: function (method) {
      return method === 'mail';
    }
  },
  // HAWAIʻI. Haw. R. Civ. P. 6(e), verbatim:
  //
  //   "Whenever a party has the right or is required to do some act or take
  //    some proceedings within a prescribed period after the service of a
  //    NOTICE OR OTHER PAPER upon the party and the notice or paper is served
  //    upon the party BY MAIL, 2 DAYS shall be ADDED TO THE PRESCRIBED PERIOD."
  //
  // ★ TWO DAYS, NOT THREE, AND HAWAIʻI IS THE ONLY SEEDED JURISDICTION THAT
  // SAYS TWO. Every FRCP-family state adds three; South Carolina and New Jersey
  // add five; California and New York use per-method tables. An `add: 3` copied
  // from any neighbour over-counts by a day on every mailed Hawaiʻi deadline,
  // which is the direction that reports LATE. The amount lives on each seeded
  // row as `add: 2` and a test asserts no row carries 3.
  //
  // MAIL ONLY -- no electronic limb, no commercial carrier, nothing else.
  //
  // "ADDED TO THE PRESCRIBED PERIOD" -> add_to_period_then_roll, the
  // period-lengthening order, not the federal after-expiry one.
  //
  // AND IT HAS THE NOTICE LIMB, WHICH IS A THIRD ANSWER TO A QUESTION TWO
  // STATES ALREADY SPLIT ON. Miss. R. Civ. P. 6(e) reaches "the service of a
  // NOTICE or other paper" and its post-motion row therefore takes the days;
  // I.R.C.P. 2.2(c) and Neb. Ct. R. Pldg. § 6-1106(c) reach only "after
  // service" and theirs do not. Hawaiʻi's wording matches Mississippi's, so
  // its Rule 12(a)(3)(A) row -- triggered by "notice of the court's action" --
  // DOES take the two days. Four states, the same trigger words, two answers,
  // decided every time by the time rule rather than the pleading rule.
  hi_hrcp_6_e: {
    label: 'Haw. R. Civ. P. 6(e)',
    sequence: 'add_to_period_then_roll',
    shape: 'enumerated_allowlist',
    qualifies: function (method) {
      return method === 'mail';
    }
  }
};

// ── Service-COMPLETION standards ──────────────────────────────────────────
// A THIRD MECHANISM, AND IT IS NOT THE OTHER TWO. Everything in
// SERVICE_EXTENSION_STANDARDS above answers "how many days are ADDED to the
// period". This table answers a different question entirely: "on what date was
// service COMPLETE", which decides the date the period RUNS FROM. It is applied
// BEFORE the base period is computed, not after.
//
// WHY IT EXISTS. Three states were read in a row and gave three different
// answers about electronic service, none of which could be inferred from the
// others:
//
//   MASSACHUSETTS  R. 6(d) grants three days for e-mail and other electronic
//                  service in the TIME RULE ITSELF.
//   TENNESSEE      R. 6.05 says "by mail" and nothing else -- but R. 5.02(2)(c)
//                  and (3)(e) DEEM an emailed or E-served document "a document
//                  that was mailed for purposes of computation of time under
//                  Rule 6", so it collects the same three days by a deeming
//                  provision in the SERVICE rule.
//   MISSOURI       R. 44.01(d) says "by mail" and the service rule does NOT
//                  deem. Instead R. 43.01(d) and R. 103.08(a) move WHEN SERVICE
//                  IS COMPLETE. Electronic service gets NO added days at all,
//                  and the period simply starts later.
//
// Reading any one of those three time rules alone produces a wrong answer for
// the other two. That is the standing habit this table encodes: READ THE
// SERVICE RULE BEFORE CONCLUDING WHAT A TIME RULE REACHES.
//
// NOT THE SAME AS Va. Sup. Ct. R. 1:7, which also turns on 5:00 p.m. Virginia's
// cutoff decides the AMOUNT ADDED (0 days or 1); Missouri's decides the TRIGGER
// DATE. Virginia ignores weekends in that decision; Missouri's rule pushes off
// Saturdays, Sundays and legal holidays as well. They share a clock and nothing
// else, and `service_time` is deliberately reused as the input for both.
//
// A MISSING service_time IS A HARD REFUSAL HERE, UNLIKE VIRGINIA'S. Virginia
// can still return a real date computed without an extension, so its refusal is
// soft (ok:true, extension refused). This one cannot: if the completion date is
// unknown then the period's START is unknown, so there is no date to return at
// all. Refusing outright is the only honest option, and the message says what
// to supply.
var SERVICE_COMPLETION_STANDARDS = {
  // Mo. R. Civ. P. 43.01(d), verbatim on the limb this implements:
  //   "Service by facsimile transmission or electronic mail is complete upon
  //    transmission, except that a transmission made on a Saturday, Sunday, or
  //    legal holiday, or after 5:00 p.m. shall be complete on the next day that
  //    is not a Saturday, Sunday, or legal holiday."
  //
  // Mo. R. Civ. P. 103.08(a) states the same rule for service through the
  // electronic filing system, expressly "for the purposes of calculating the
  // time for filing a response".
  //
  // MAIL IS DELIBERATELY NOT GOVERNED. The same subsection says "Service by
  // mail is complete upon mailing", full stop -- no cutoff, no weekend shift.
  // Mail instead collects three days under R. 44.01(d). The two mechanisms are
  // mutually exclusive in Missouri and a method must never be in both.
  mo_rule_43_01_d: {
    label: 'Mo. R. Civ. P. 43.01(d)',
    // "after 5:00 p.m." begins at 17:01; a transmission AT 17:00 is not after
    // it. Same boundary reading as Va. R. 1:7's "no later than 5:00 p.m.", and
    // the boundary minute gets its own test.
    cutoff_minutes: 17 * 60,
    governs: function (method) {
      return ({ facsimile: 1, email: 1, efiling_service: 1 })[method] === 1;
    }
  }
};

// Applies a completion standard to the date service was transmitted, returning
// the date service was COMPLETE. Pure: no calendar mutation, and it refuses
// through the same NOT_PROVISIONED path rollOff already uses when the year is
// not loaded.
function applyServiceCompletion(cstd, txDate, serviceTime, calendars, jurisdiction, weekendDays) {
  var t = serviceTime;
  if (!t || !/^([01]\d|2[0-3]):[0-5]\d$/.test(String(t))) {
    return { ok: false, code: 'SERVICE_COMPLETION_TIME_REQUIRED',
      message: 'Under ' + cstd.label + ' this service method is complete on transmission ONLY if the transmission was made before ' +
        '5:00 p.m. on a day that is not a Saturday, Sunday or legal holiday; otherwise it is complete on the next such day. ' +
        (t ? 'The service_time supplied ("' + t + '") is not a 24-hour HH:MM time. ' : 'No service_time was supplied. ') +
        'That decides the date the period RUNS FROM, not merely how many days are added, so no deadline is computed without it: ' +
        'guessing a time before 5:00 p.m. would report a period starting EARLIER than it truly did and guessing after would report it LATER. ' +
        'Supply service_time as HH:MM in 24-hour form (for example "16:45" or "17:30").' };
  }
  var parts = String(t).split(':');
  var minutes = (Number(parts[0]) * 60) + Number(parts[1]);

  // Is the transmission day itself a Saturday, Sunday or legal holiday? Asked
  // through holidayFor so an unloaded year refuses rather than reading as "not
  // a holiday", which would silently skip the shift.
  var h = holidayFor(calendars, jurisdiction, txDate, 'forward');
  if (!h.known) {
    return { ok: false, code: 'NOT_PROVISIONED',
      message: 'No holiday calendar is loaded for ' + jurisdiction +
        (h.missingYear ? ' for ' + h.missingYear : '') +
        '. Whether service was complete on the day of transmission cannot be determined, so no deadline is computed.',
      missing: { jurisdiction: jurisdiction, year: h.missingYear || null } };
  }
  var badDay = isWeekend(txDate, weekendDays) || h.hit;
  var afterCutoff = minutes > cstd.cutoff_minutes;

  if (!badDay && !afterCutoff) {
    return { ok: true, date: txDate, shifted: false,
      detail: 'Service by this method is complete upon transmission. The transmission was made at ' + t +
        ', before 5:00 p.m., on a day that is not a Saturday, Sunday or legal holiday, so service was complete on ' +
        txDate + ' and the period runs from that date.' };
  }
  // "shall be complete on the NEXT day that is not a Saturday, Sunday, or legal
  // holiday" -- strictly after the transmission date, hence the +1 before the
  // roll. rollOff alone would return the transmission date itself whenever that
  // date is already a good day, which is wrong for the after-5:00-p.m. limb.
  var rolled = rollOff(addDays(txDate, 1), calendars, jurisdiction, 'forward', weekendDays);
  if (!rolled.ok) return rolled;
  return { ok: true, date: rolled.date, shifted: true,
    detail: 'The transmission was made ' +
      (badDay && afterCutoff ? 'after 5:00 p.m. and on a Saturday, Sunday or legal holiday'
        : badDay ? 'on a Saturday, Sunday or legal holiday'
        : 'at ' + t + ', after 5:00 p.m.') +
      ', so under ' + cstd.label + ' service was not complete on ' + txDate +
      ' but on the next day that is not a Saturday, Sunday or legal holiday, ' + rolled.date +
      '. The period runs from that date.' };
}

// Retained as a read-only description of the FRCP set for callers and tests.
// NO LONGER used as a gate -- gating is per-standard above.
var SERVICE_METHODS_EXTENDING = { mail: true, left_with_clerk: true, other_consented_means: true };

// ── Base-period computation, shared ───────────────────────────────────────
// EXTRACTED, NOT REWRITTEN. This is the block that used to sit inline in
// computeDeadline, moved out verbatim so that the period-resolution shape
// below can call the SAME code rather than a second copy of it.
//
// The reason that matters more than tidiness: resolve_periods has to compute
// each limb's end date to find out which one governs, and every subtlety in
// here would otherwise have to be duplicated -- the short-period exclusion,
// Florida's shifted start, month arithmetic with end-of-month clamping, the
// business-day loop, and the refusal when a holiday year is missing. A second
// copy would drift, and it would drift silently, because the two would only
// disagree on the boundary cases nobody tests by hand.
//
// Returns { ok, date, detail, authority } so the caller decides whether to
// push an audit step. Refusals are returned unchanged for the caller to
// propagate.
function computeBasePeriod(std, triggerDate, countValue, unit, direction, sign, calendars, jurisdiction, ruleId) {
  if (unit === 'calendar_days') {
    // Short-period weekend/holiday exclusion: gated on the STANDARD
    // declaring short_period_exclusion_days, not on a specific impl string or
    // jurisdiction, because more than one state's rule uses this exact
    // mechanism (Ohio Civ.R. 6(A) and Indiana T.R. 6(A) both read "less than
    // seven days... excluded" -- verified independently for each, not
    // assumed from one to the other) with a shared authority label per
    // standard so the audit trail still cites the RIGHT state's rule. Never
    // fires for an FRCP-family rule, which declares no such property.
    //
    // PER-DIRECTION, added 2026-08-30 for Maryland. Optional and absent
    // everywhere else, so every existing standard behaves exactly as before:
    // when short_period_exclusion_directions is undefined the exclusion
    // applies in both directions, which is what the other twelve standards
    // that declare a threshold mean.
    //
    // MARYLAND IS THE FIRST JURISDICTION WHERE FORWARD AND BACKWARD DIFFER,
    // and they differ in the rule's own words. Md. Rule 1-203(a) drops
    // intermediate Saturdays, Sundays and holidays when the period is seven
    // days or less. Md. Rule 1-203(b) counts backward periods "including
    // intervening Saturdays, Sundays, and holidays" -- the exclusion
    // deliberately does NOT carry across. An engine that reused the forward
    // logic backward would drop days the rule counts and report a date LATER
    // than the true one on every short backward Maryland period, which is the
    // direction that lets a party serve too late.
    if (std.short_period_exclusion_days && countValue < std.short_period_exclusion_days
        && (!std.short_period_exclusion_directions
            || std.short_period_exclusion_directions.indexOf(direction) !== -1)) {
      var shortRes = countExcludingWeekendsAndHolidays(triggerDate, sign, countValue, calendars, jurisdiction, direction, std.weekend_days);
      if (!shortRes.ok) return shortRes;
      return { ok: true, date: shortRes.date, authority: std.label,
        detail: 'Excluded the trigger day and counted ' + countValue + ' days ' + direction +
          ', excluding intermediate Saturdays, Sundays and legal holidays because the period is less than ' +
          std.short_period_exclusion_days + ' days.' };
    }
    if (std.shifted_start) {
      // SHIFTED START. Florida's Fla. R. Gen. Prac. & Jud. Admin. 2.514(a)(1)(A)
      // does NOT say "exclude the day of the event that triggers the period"
      // the way FRCP 6(a)(1)(A) does. It says "begin counting from the next
      // day that is not a Saturday, Sunday, or legal holiday" -- so the count
      // starts at the next BUSINESS day, and that day is day one.
      //
      // The difference is real and it is not one day in the usual case, it is
      // however many days it takes to clear a weekend or holiday. A 30-day
      // period triggered on a Friday: FRCP counts Saturday as day one and
      // lands on a Sunday, rolling to the Monday; Florida starts counting the
      // Monday and lands two days later. Reusing the FRCP branch here -- which
      // is what "Florida is data-only" would have meant -- would have been
      // wrong on every Florida deadline triggered on a Friday or the day
      // before a holiday.
      //
      // Gated on the STANDARD declaring shifted_start, not on a jurisdiction
      // string, so a second state with this shape needs no new code -- the
      // same design already used for short_period_exclusion_days.
      //
      // Direction-aware by 2.514(a)(5): "The 'next day' is determined by
      // continuing to count forward when the period is measured after an event
      // and backward when measured before an event." rollOff already walks in
      // the direction it is given, so a backward Florida period shifts to the
      // preceding business day rather than the following one.
      var startRes = rollOff(addDays(triggerDate, sign), calendars, jurisdiction, direction, std.weekend_days);
      if (!startRes.ok) return startRes;
      var firstCounted = startRes.date;
      return { ok: true, date: addDays(firstCounted, sign * (countValue - 1)),
        authority: std.label + (std.base_period_suffix || ''),
        detail: 'Began counting from ' + firstCounted + ', the ' + (direction === 'backward' ? 'preceding' : 'next') +
          ' day that is not a Saturday, Sunday or legal holiday, and counted that day as day one. Counted ' + countValue +
          ' days ' + direction + ' from there, including intermediate weekends and holidays.' };
    }
    return { ok: true, date: addDays(triggerDate, sign * countValue),
      authority: std.label + (std.base_period_suffix || ''),
      detail: 'Excluded the trigger day and counted ' + countValue + ' calendar days ' + direction +
        ', including intermediate weekends and holidays.' };
  }
  if (unit === 'months' || unit === 'years') {
    return { ok: true, date: addMonths(triggerDate, sign * countValue * (unit === 'years' ? 12 : 1)),
      authority: std.label + (std.months_years_suffix || ''),
      detail: 'Counted ' + countValue + ' ' + unit + ' ' + direction + ' by anniversary date, clamped to end of month.' };
  }
  if (unit === 'business_days') {
    // Supported because other jurisdictions really do count this way. It is
    // NOT how the FRCP counts, and no FRCP rule may use it.
    var cur = triggerDate, remaining = countValue, guard = 0;
    while (remaining > 0 && guard++ < 400) {
      cur = addDays(cur, sign);
      var hb = holidayFor(calendars, jurisdiction, cur, direction);
      if (!hb.known) {
        return { ok: false, code: 'NOT_PROVISIONED',
          message: 'No holiday calendar is loaded for ' + jurisdiction + (hb.missingYear ? ' for ' + hb.missingYear : '') + ', which business-day counting requires.',
          missing: { jurisdiction: jurisdiction, year: hb.missingYear || null } };
      }
      if (!isWeekend(cur, std.weekend_days) && !hb.hit) remaining--;
    }
    return { ok: true, date: cur, authority: null,
      detail: 'Counted ' + countValue + ' business days ' + direction + ', skipping weekends and holidays.' };
  }
  return { ok: false, code: 'UNKNOWN_UNIT',
    message: 'Rule ' + ruleId + ' uses unit "' + unit + '", which this engine does not implement.' };
}

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
//
// ── resolve_periods: THE LATER OF TWO COMPUTED PERIODS ────────────────────
// The shape above resolves between DATES and then applies ONE count. A whole
// family of rules needs something it cannot express: two limbs that each run
// from a different event AND for a different number of days, with the later
// (or earlier) of the two RESULTS governing.
//
//   O.C.G.A. 9-11-36(a)(2)   30 days after the request, but a defendant is not
//                            required to answer before 45 days after service
//                            of process
//   Ohio App.R. 4(B)(1)      "within the appeal time period otherwise
//                            prescribed by this rule or within ten days of the
//                            filing of the first notice of appeal"
//   N.Y. CPLR 5513(c)        "within ten days after such service or within the
//                            time limited by subdivision (a) or (b) ...
//                            whichever is longer"
//   Fed. R. Civ. P. 15(a)(3) "within the time remaining to respond to the
//                            original pleading or within 14 days after service
//                            of the amended pleading, whichever is later"
//
// WHY THIS IS A REAL CAPABILITY AND NOT A DATA WORKAROUND. Georgia's was first
// encoded as an ordinary later_of and shipped a date FIFTEEN DAYS EARLY on a
// self-executing admission -- later_of picked the later trigger date and then
// applied the single 30-day count to it, when the limb that won needed 45. It
// was caught by hand arithmetic, not by a test. Anything that resolves between
// dates before the counts are applied is wrong for this family, in the
// direction that forfeits the right.
//
// EACH LIMB IS COMPUTED THROUGH computeBasePeriod, the same function the main
// pipeline uses, so every limb gets the standard's short-period exclusion,
// shifted start, month clamping and missing-calendar refusal. The winner's
// trigger date AND its count are then handed back, and the main pipeline runs
// normally from there -- rollover, cap and service extension all apply to the
// winning limb exactly as they would to any single-trigger rule.
//
// COMPARING UNROLLED BASE DATES IS SOUND, and this is the one thing here worth
// proving rather than asserting. rollOff is monotonic non-decreasing for a
// forward period: if a <= b then the first good day at or after a is at or
// before the first good day at or after b. So max(roll(a), roll(b)) equals
// roll(max(a, b)), and likewise for min. Rolling both limbs and comparing
// therefore gives the same final date as comparing raw and rolling the winner.
// The second is chosen because it keeps one rollover step in the audit trail
// instead of two discarded ones.
//
// REFUSES ON PARTIAL INPUT for the same reason the date-resolving shape does,
// and the message names which direction the error would have run.
//
// FORWARD ONLY. Every rule of this shape read so far measures forward. What
// "the later of two periods" means when both run backward is not settled by
// any text read here, and the monotonicity argument above would need redoing
// for a backward roll. Refused rather than guessed.
function resolvePeriods(rule, input, std) {
  var spec = rule.trigger_event;
  var limbs = spec.limbs;
  if (!Array.isArray(limbs) || limbs.length < 2) {
    return { ok: false, code: 'BAD_RULE_TRIGGER',
      message: 'Rule ' + rule.rule_id + ' declares resolve_periods but does not list at least two limbs.' };
  }
  if (spec.resolve_periods !== 'later_of' && spec.resolve_periods !== 'earlier_of') {
    return { ok: false, code: 'BAD_RULE_TRIGGER',
      message: 'Rule ' + rule.rule_id + ' uses resolve_periods "' + spec.resolve_periods + '"; only later_of and earlier_of are implemented.' };
  }
  for (var li = 0; li < limbs.length; li++) {
    var L = limbs[li];
    if (!L || !L.event || !L.count || typeof L.count.value !== 'number' || !L.count.unit) {
      return { ok: false, code: 'BAD_RULE_TRIGGER',
        message: 'Rule ' + rule.rule_id + ' has a limb missing an event or a well-formed count. Each limb carries its OWN count -- that is the entire point of this shape.' };
    }
    if ((L.count.direction || 'forward') !== 'forward') {
      return { ok: false, code: 'PERIOD_RESOLUTION_DIRECTION',
        message: 'Rule ' + rule.rule_id + ' applies resolve_periods to a backward-counted limb. Only forward limbs are implemented; what "the later of two periods" means running backward has not been read from any rule text.' };
    }
  }

  var supplied = input.trigger_dates || {};
  var missing = limbs.filter(function (L) { return !toUTC(supplied[L.event]); }).map(function (L) { return L.event; });
  if (missing.length) {
    return {
      ok: false, code: 'INCOMPLETE_TRIGGERS',
      message: 'This rule is the ' + spec.resolve_periods.replace('_', ' ') + ' ' + limbs.length +
        ' separately computed periods, each running from its own event for its own number of days, and ' +
        missing.length + (missing.length === 1 ? ' of them has' : ' of them have') + ' no date recorded. No deadline is computed from a partial set — ' +
        'resolving it from the limbs supplied would produce a date that is ' +
        (spec.resolve_periods === 'later_of' ? 'too early' : 'too late') + ' whenever the missing limb governs.',
      required_events: limbs.map(function (L) { return L.event; }), missing_events: missing
    };
  }

  var computed = [];
  for (var i = 0; i < limbs.length; i++) {
    var lb = limbs[i];
    var res = computeBasePeriod(std, supplied[lb.event], Number(lb.count.value), lb.count.unit,
      'forward', 1, input.calendars, input.jurisdiction, rule.rule_id);
    if (!res.ok) return res;
    computed.push({ limb: lb, trigger: supplied[lb.event], end: res.date });
  }
  var sorted = computed.slice().sort(function (a, b) { return a.end < b.end ? -1 : a.end > b.end ? 1 : 0; });
  var winner = spec.resolve_periods === 'later_of' ? sorted[sorted.length - 1] : sorted[0];

  return {
    ok: true,
    date: winner.trigger,
    count_override: { value: Number(winner.limb.count.value), unit: winner.limb.count.unit, direction: 'forward' },
    period_resolution: {
      resolve: spec.resolve_periods,
      governing_event: winner.limb.event,
      governing_label: winner.limb.label || null,
      limbs: computed.map(function (c) {
        return { event: c.limb.event, label: c.limb.label || null, trigger_date: c.trigger,
          count: c.limb.count.value + ' ' + c.limb.count.unit, period_ends: c.end,
          governs: c === winner };
      })
    }
  };
}

function resolveTrigger(rule, input, std) {
  var spec = rule.trigger_event;

  // Single-trigger rules: unchanged behaviour.
  if (typeof spec === 'string') {
    if (!toUTC(input.trigger_date)) {
      return { ok: false, code: 'BAD_TRIGGER_DATE', message: 'A trigger date in YYYY-MM-DD form is required.' };
    }
    return { ok: true, date: input.trigger_date, resolution: null };
  }

  // Two-limb period resolution is a different shape from date resolution and
  // is dispatched before it, because a spec carrying `limbs` has no `events`.
  if (spec && spec.resolve_periods) return resolvePeriods(rule, input, std);

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
        ' events, and ' + missing.length + (missing.length === 1 ? ' of them has' : ' of them have') + ' no date recorded. No deadline is computed from a partial set — ' +
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
  //
  // AN EXACT SINGLE-TRIGGER MATCH WINS OVER MEMBERSHIP IN A MULTI-TRIGGER
  // SPEC. Without this, one event name that is BOTH a rule's own trigger and
  // one limb of another rule's "later of" spec pulls in both rules, and the
  // multi-trigger one then aborts the whole computation with
  // INCOMPLETE_TRIGGERS naming events the caller never asked about.
  //
  // That was not hypothetical. 'service_on_united_states_attorney' is the
  // trigger for FRCP 12(a)(2) AND one limb of 12(a)(3)'s spec, so asking for
  // the plain 60-day 12(a)(2) deadline could never return a date -- it always
  // refused, describing a different rule. Found in Phase 4 while sweeping
  // every seeded rule for provenance, after the UI had already started
  // offering that option: a dropdown entry that can never produce a date is
  // exactly the class of defect making the panel reachable was meant to end.
  //
  // Membership matching is KEPT for names that no single-trigger rule claims,
  // because there INCOMPLETE_TRIGGERS is the genuinely useful answer -- it
  // names the other dates needed. The rule is only that an exact match wins,
  // never that membership stops working.
  var exact = inDomain.filter(function (r) {
    return typeof r.trigger_event === 'string' && r.trigger_event === input.trigger_event;
  });
  var byId = inDomain.filter(function (r) {
    return r.trigger_event && typeof r.trigger_event !== 'string' && r.trigger_event.id === input.trigger_event;
  });
  var byMember = inDomain.filter(function (r) {
    return r.trigger_event && typeof r.trigger_event !== 'string' &&
      Array.isArray(r.trigger_event.events) &&
      r.trigger_event.id !== input.trigger_event &&
      r.trigger_event.events.indexOf(input.trigger_event) !== -1;
  });
  // A caller who supplied trigger_dates is explicitly asking for a
  // multi-trigger rule, so membership still counts for them even when a
  // single-trigger rule shares the name.
  var matching = (exact.length || byId.length)
    ? exact.concat(byId).concat(input.trigger_dates ? byMember : [])
    : byMember;
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
    // The standard is needed BEFORE resolution now, because resolve_periods
    // computes each limb's period to find out which governs, and that uses the
    // same computation standard the main pipeline will. Looked up here and
    // refused here rather than later, so an unknown standard on a
    // period-resolving rule fails with the same message as on any other.
    var rrStd = COMPUTATION_STANDARDS[rr.computation];
    if (!rrStd) {
      return { ok: false, code: 'UNKNOWN_STANDARD',
        message: 'Rule ' + rr.rule_id + ' names computation standard "' + rr.computation + '", which this engine does not implement.' };
    }
    // THE MULTI-SLOT GUARD RUNS HERE, NOT BESIDE ITS SINGULAR SIBLING, AND THE
    // PLACEMENT IS THE WHOLE POINT. resolveTrigger() dispatches a
    // resolve_periods spec into resolvePeriods(), which calls
    // computeBasePeriod() for EVERY limb. The singular guard sits ~40 lines
    // below, after the winning rule is chosen -- correct there, because a
    // single-trigger rule computes nothing until then. Putting the plural one
    // in the same place would read correctly, return the right refusal code,
    // and still have done the arithmetic it exists to prevent.
    var rrDocs = resolveTriggerDocuments(rr, input);
    if (rrDocs && rrDocs.ok === false) return rrDocs;

    var res = resolveTrigger(rr, input, rrStd);
    if (!res.ok) return res;
    var ret = applyRetrigger(rr, res.date, input);
    if (!ret.ok) return ret;
    resolvedByRule[rr.rule_id] = { date: ret.date, resolution: res.resolution,
      period_resolution: res.period_resolution || null, count_override: res.count_override || null,
      retrigger: ret.retriggered ? ret : null, trigger_documents: rrDocs };
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

  // The discriminator runs BEFORE any arithmetic. A refusal here must not be
  // reachable only after a date has already been computed -- the point is that
  // no date exists to be misread.
  var triggerDocument = resolveTriggerDocument(rule, input);
  if (triggerDocument && triggerDocument.ok === false) return triggerDocument;

  // COUNT COMES FROM THE WINNING LIMB on a period-resolving rule, and such a
  // rule carries NO rule.count at all -- there is no single number to put
  // there, and storing a representative one would be a fabricated field that
  // the engine then ignores. The validator enforces its absence.
  var count = resolved.count_override || rule.count || {};
  var direction = count.direction === 'backward' ? 'backward' : 'forward';
  var sign = direction === 'backward' ? -1 : 1;
  var steps = [];

  // ── SERVICE COMPLETION: adjust the date the period RUNS FROM ─────────────
  // Applied HERE, before any counting, because it changes the period's START
  // rather than its length. See SERVICE_COMPLETION_STANDARDS for why this is a
  // third mechanism and not a variant of the service extension.
  //
  // Ordering matters and is deliberate: completion is resolved AFTER trigger
  // resolution and retriggering (so it applies to the date the period really
  // runs from) and BEFORE the base period, the cap and the service extension.
  // A rule may in principle carry both a completion standard and an extension
  // standard -- in Missouri they are mutually exclusive by method, because mail
  // takes the extension and never the completion rule, and fax/e-mail/e-filing
  // take the completion rule and never the extension.
  var completion = null;
  if (rule.service_completion && input.service_method) {
    var cKey = rule.service_completion.standard;
    var cstd = SERVICE_COMPLETION_STANDARDS[cKey];
    if (!cstd) {
      // Refused HARD, not silently skipped. An unknown completion standard
      // means the period's start is unverified, and a date computed from an
      // unverified start is exactly the quiet wrongness this engine exists to
      // avoid. The validator also rejects such a row at write time.
      return { ok: false, code: 'UNKNOWN_COMPLETION_STANDARD',
        message: 'Rule ' + rule.rule_id + ' names service-completion standard "' + cKey +
          '", which this engine does not implement. The date the period runs from cannot be verified, so no deadline is computed.' };
    }
    if (cstd.governs(input.service_method)) {
      var comp = applyServiceCompletion(cstd, triggerDate, input.service_time, input.calendars, input.jurisdiction, std.weekend_days);
      if (!comp.ok) return comp;
      completion = { state: comp.shifted ? 'shifted' : 'complete_on_transmission',
        standard: cKey, transmitted: triggerDate, complete_on: comp.date, detail: comp.detail };
      if (comp.shifted) {
        steps.push({ step: 'service_completion', detail: comp.detail,
          authority: cstd.label, date: comp.date });
      }
      triggerDate = comp.date;
    } else {
      // The method is real but this standard does not reach it -- in Missouri,
      // mail. Reported distinctly from "no completion rule exists" so a reader
      // can tell the rule was considered and correctly declined.
      completion = { state: 'not_governed', standard: cKey, transmitted: triggerDate,
        complete_on: triggerDate,
        detail: 'Service by ' + String(input.service_method).replace(/_/g, ' ') + ' is not governed by ' +
          cstd.label + ', so the period runs from the date supplied.' };
    }
  }

  // ── DESIGNATED-PERIOD RULES (Phase 6) ────────────────────────────────────
  // Some rules do not set a deadline at all. They set a FLOOR on a period that
  // one party chooses. Ohio Civ.R. 33(A) and 36(A)(1) and Ind. T.R. 33(C) and
  // 36(A) all read "within a period designated by the party submitting ... not
  // less than" 28 or 30 days. The operative deadline is whatever was actually
  // designated; the number in the rule is only the minimum a valid request may
  // demand.
  //
  // Phase 5 refused to seed these at all rather than state a floor as though it
  // were a deadline -- a date that is not the user's deadline whenever the
  // request designated longer, which is most of the time. This shape is what
  // lets them be expressed honestly: the designated period is a REQUIRED INPUT,
  // and the rule's own number is used only to validate it.
  //
  // A BELOW-FLOOR DESIGNATION IS REFUSED, NOT SILENTLY RAISED TO THE FLOOR.
  // Computing the floor instead would answer a question nobody asked and would
  // paper over a defective request; the caller is told the designation is
  // invalid and what the floor is. Whether a below-floor designation voids the
  // request outright or is merely unenforceable as to timing is a question of
  // law, not of arithmetic, and this engine does not pick between them -- it
  // refuses and names the floor so a human decides.
  var designatedDays = null;
  if (rule.designated_period) {
    var dp = rule.designated_period;
    var supplied = input.designated_period_days;
    if (supplied === undefined || supplied === null || supplied === '') {
      return { ok: false, code: 'DESIGNATED_PERIOD_REQUIRED',
        message: 'This rule does not set a deadline. It sets a floor: the period is whatever ' +
          (dp.designated_by || 'the requesting party') + ' designated in the request, and it may not be less than ' +
          dp.min + ' ' + (dp.unit || 'calendar_days').replace(/_/g, ' ') +
          '. Supply the period actually designated and the date will be computed from that.',
        floor: { min: dp.min, unit: dp.unit || 'calendar_days', designated_by: dp.designated_by || null },
        authority: rule.authority ? rule.authority.citation : null };
    }
    var n = Number(supplied);
    if (!isFinite(n) || Math.floor(n) !== n || n <= 0) {
      return { ok: false, code: 'BAD_DESIGNATED_PERIOD',
        message: 'The designated period must be a whole number of ' + (dp.unit || 'calendar_days').replace(/_/g, ' ') + '.' };
    }
    if (n < dp.min) {
      return { ok: false, code: 'DESIGNATED_PERIOD_BELOW_FLOOR',
        message: 'The request designated ' + n + ' ' + (dp.unit || 'calendar_days').replace(/_/g, ' ') +
          ', but ' + (rule.authority ? rule.authority.citation : 'this rule') + ' permits no less than ' + dp.min +
          '. No date is computed. Whether a request designating less than the minimum is void, or merely ' +
          'unenforceable as to timing, is a question of law this engine does not decide — check the rule and the ' +
          'request before treating either number as the deadline.',
        designated: n, floor: { min: dp.min, unit: dp.unit || 'calendar_days' },
        authority: rule.authority ? rule.authority.citation : null };
    }
    designatedDays = n;
    steps.push({ step: 'designated_period',
      detail: 'This rule sets no fixed deadline. ' + (dp.designated_by || 'The requesting party') +
        ' designated ' + n + ' ' + (dp.unit || 'calendar_days').replace(/_/g, ' ') + ', which is at or above the rule’s minimum of ' +
        dp.min + '. The period below is counted from the designated figure, not from the minimum.',
      authority: rule.authority ? rule.authority.citation : null, date: triggerDate });
  }

  // Both of these are recorded BEFORE the base period, because each changed
  // what the base period counts from. They are separate step kinds from
  // 'service_extension' on purpose -- one moves the start, the other adds to
  // the end, and conflating them in the audit trail would misdescribe the law.
  if (resolved.period_resolution) {
    var pr = resolved.period_resolution;
    steps.push({
      step: 'period_resolution',
      detail: 'This deadline is the ' + pr.resolve.replace('_', ' ') + ' ' + pr.limbs.length +
        ' separately computed periods. ' +
        pr.limbs.map(function (L) {
          return (L.label || L.event) + ': ' + L.count + ' from ' + L.trigger_date + ' ends ' + L.period_ends + (L.governs ? ' <- governs' : '');
        }).join('; ') + '. The counts differ per limb, so the later of the two TRIGGER DATES is not the answer — ' +
        'each period is computed in full and the results compared.',
      authority: rule.authority ? rule.authority.citation : null,
      date: pr.limbs.filter(function (L) { return L.governs; })[0].period_ends
    });
  }
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
  //
  // countValue is the number the period is ACTUALLY counted from. For an
  // ordinary rule that is rule.count.value. For a designated-period rule it is
  // the figure the requesting party designated, already validated at or above
  // the rule's floor -- the rule's own number is a minimum and must never be
  // the thing counted, which is the entire reason these rules were refused in
  // Phase 5 rather than seeded as fixed periods.
  var countValue = designatedDays === null ? Number(count.value) : designatedDays;
  var baseRes = computeBasePeriod(std, triggerDate, countValue, count.unit, direction, sign,
    input.calendars, input.jurisdiction, rule.rule_id);
  if (!baseRes.ok) return baseRes;
  var base = baseRes.date;
  steps.push({ step: 'base_period', detail: baseRes.detail, authority: baseRes.authority, date: base });

  // ── TERMINAL DAY RULE: A NAMED WEEKDAY STRICTLY AFTER THE PERIOD ─────────
  // Tex. R. Civ. P. 99(b): the citation "shall direct the defendant to file a
  // written answer to the plaintiff's petition on or before 10:00 a.m. on the
  // Monday next after the expiration of twenty days after the date of service
  // thereof."
  //
  // This is a THIRD shape, distinct from both of the ones already here:
  //   shifted_start        moves where the count BEGINS   (Florida)
  //   rollover             moves a bad landing day OFF it (everyone)
  //   terminal_day_rule    moves the deadline to a NAMED WEEKDAY after the
  //                        period expires, whether or not the landing day was
  //                        a weekend or holiday at all
  //
  // Rollover cannot express it. Rollover only fires when the last day is a
  // Saturday, Sunday or holiday, and it stops at the first day that is none of
  // those. Texas moves the deadline to Monday from ANY weekday -- a period
  // expiring on a Wednesday still goes to the following Monday, which rollover
  // would never touch. Modelling this as "count 20 then roll" would be right
  // only when day 20 happens to fall on a weekend, and would produce a date up
  // to six days EARLY the rest of the time.
  //
  // STRICTLY AFTER, AND THAT IS THE WHOLE DIFFICULTY. The rule says the Monday
  // next after the EXPIRATION of the twenty days. The twenty days expire at the
  // end of day twenty, so when day twenty is itself a Monday the deadline is
  // the Monday of the FOLLOWING WEEK, seven days later, not that same day.
  // Proctor v. Green, 673 S.W.2d 390, 392 (Tex. App.-Houston [1st Dist.] 1984)
  // is reported as holding exactly that: "When the twentieth day falls on
  // Monday, the appearance day is the Monday of the following week."
  //
  // Provenance of that quote, stated plainly rather than dressed up: the
  // opinion text was NOT read on a free primary-source site -- CourtListener
  // confirms the case, court, date and citation but serves no accessible full
  // text, and the two databases carrying it refused automated access. The
  // quote comes from a legal database's rendering of the opinion. The engine
  // does not rest on it: the same result follows from Rule 99(b)'s own words,
  // because a period that expires at the end of a Monday cannot have its
  // "Monday next after" be that same Monday. The case is confirmatory, and the
  // rule row cites Rule 99(b) as its authority, not the case.
  //
  // THE EXPIRATION DAY IS NOT ROLLED FIRST. This is the trap, and it is the
  // one the Proctor facts settle. There, service produced a twentieth day of
  // Sunday 3 July 1983; the court took the Monday next after as 4 July 1983 --
  // the very next day -- and only then applied Rule 4 to move it off the
  // holiday to Tuesday 5 July. Had day twenty been rolled off the Sunday to
  // Monday 4 July first, the "Monday next after" would have been 11 July and
  // the whole case would have come out differently. So the order is fixed:
  // count the period, find the named weekday strictly after it, THEN roll.
  // The rollOff call below is deliberately left downstream of this block.
  //
  // Gated on a RULE property rather than a computation standard, because the
  // Monday requirement lives in Rule 99, not in Rule 4. Several other Texas
  // rules use the identical phrase (Rules 15, 122, 330(a), 606, 619, 659 and
  // 687 among them), so the shape is reusable within Texas -- but it belongs
  // to each of those rules, not to the state's computation standard, and
  // hanging it on tx_trcp_4 would silently apply it to the discovery rows,
  // which have no Monday requirement at all.
  if (rule.terminal_day_rule) {
    var tdr = rule.terminal_day_rule;
    if (tdr.kind !== 'next_weekday_strictly_after') {
      return { ok: false, code: 'UNKNOWN_TERMINAL_DAY_RULE',
        message: 'Rule ' + rule.rule_id + ' names terminal day rule "' + tdr.kind +
          '", which this engine does not implement. No date is computed rather than one being produced by the ordinary path, which would silently ignore the rule.' };
    }
    if (direction !== 'forward') {
      // Every rule of this shape found so far measures forward from service.
      // A backward one would have to mean the named weekday BEFORE the period,
      // and nothing read so far says that. Refused rather than guessed.
      return { ok: false, code: 'TERMINAL_DAY_RULE_DIRECTION',
        message: 'Rule ' + rule.rule_id + ' applies a named-weekday terminal day rule to a backward-counted period. This engine implements that shape only for forward periods, and does not assume what the backward equivalent would mean.' };
    }
    var want = Number(tdr.weekday);
    if (!(want >= 0 && want <= 6)) {
      return { ok: false, code: 'UNKNOWN_TERMINAL_DAY_RULE',
        message: 'Rule ' + rule.rule_id + ' names weekday "' + tdr.weekday + '", which is not a day of the week (0 = Sunday through 6 = Saturday).' };
    }
    var expiry = base;
    // STRICTLY after: always advance at least one day, so an expiry that is
    // already the named weekday moves a full week rather than standing still.
    var walk = addDays(expiry, 1);
    for (var tg = 0; tg < 7 && dayOfWeek(walk) !== want; tg++) walk = addDays(walk, 1);
    base = walk;
    steps.push({ step: 'terminal_day_rule',
      detail: 'The ' + countValue + '-day period expired on ' + expiry + ' (' + (tdr.expiry_label || 'a ' + WEEKDAY_NAMES[dayOfWeek(expiry)]) +
        '). This rule sets the deadline at the ' + WEEKDAY_NAMES[want] + ' next AFTER that expiration, so the deadline moves to ' + base +
        '. Because "after" is strict, an expiration falling on a ' + WEEKDAY_NAMES[want] + ' moves a full week, not to that same day.' +
        (tdr.time_of_day ? ' NOTE: this rule sets a time of day as well — ' + tdr.time_of_day + ' — and this engine computes dates only. The deadline is that hour on this date, not the end of it.' : ''),
      authority: (rule.authority && rule.authority.citation) || null, date: base });
  }

  // Rule 6(a)(1)(C) / 6(a)(5): roll the LAST day only.
  var rolled = rollOff(base, input.calendars, input.jurisdiction, direction, std.weekend_days);
  if (!rolled.ok) return rolled;
  if (rolled.date !== base) {
    // Direction-aware wording. A backward period rolls to the PRECEDING
    // business day, and describing that as "the next day" in the audit trail
    // an attorney reads would state the opposite of what the engine did --
    // the same class of small inaccuracy as the citation-suffix defect fixed
    // in Phase 3, and more misleading here because the reader's instinct for
    // "next day" is forward.
    steps.push({ step: 'rollover',
      detail: direction === 'backward'
        ? 'The last day fell on a Saturday, Sunday or legal holiday, so the period runs BACK to the preceding day that is not — counting backward, because this period is measured before an event.'
        : 'The last day fell on a Saturday, Sunday or legal holiday, so the period runs to the next day that is not.',
      authority: std.label + (direction === 'backward' ? (std.rollover_suffix_backward || '') : (std.rollover_suffix_forward || '')), date: rolled.date });
  }
  var result = rolled.date;

  // ── CAP: EARLIER OF A COMPUTED PERIOD AND A DATE SOMEONE ELSE CHOSE ──────
  // Fed. R. Civ. P. 45(d)(2)(B): objections to a subpoena are due "before the
  // earlier of the time specified for compliance or 14 days after the subpoena
  // is served." Ohio Civ.R. 45(C)(3) states the same logic in different words.
  //
  // This is NOT designated_period and the difference matters. There the other
  // party chooses a DAY COUNT and the rule sets a floor under it, so the
  // engine validates their number and counts from it. Here the other party
  // chooses a DATE, the rule computes its own period independently, and
  // whichever falls first governs. One is a floor on an input; this is a
  // ceiling on an output.
  //
  // THE CAP DATE IS NOT ROLLED. The computed period is a period and gets
  // Rule 6(a) treatment; the compliance date is a fixed date the issuing party
  // wrote into the subpoena and is not a period being computed. Rolling it
  // would move the deadline LATER than the subpoena allows, which is the
  // direction that loses the right -- and it would do so by applying a rule
  // that does not govern that date.
  //
  // REQUIRED, NOT OPTIONAL. Without the compliance date there is no way to
  // know which limb governs, and defaulting to the computed period would
  // silently produce the later of the two whenever the subpoena demanded
  // sooner. Refused instead.
  var cap = null;
  if (rule.cap) {
    var capSpec = rule.cap;
    var capSupplied = input.cap_date;
    if (!toUTC(capSupplied)) {
      return { ok: false, code: 'CAP_DATE_REQUIRED',
        message: 'This deadline is the EARLIER of two dates: ' + count.value + ' ' +
          String(count.unit).replace(/_/g, ' ') + ' after the trigger, or ' +
          (capSpec.label || 'a date fixed by the other party') +
          '. Supply that date — without it there is no way to tell which one governs, and assuming the computed period would produce the later of the two whenever the other is sooner.',
        required_cap: { event: capSpec.event || null, label: capSpec.label || null },
        authority: rule.authority ? rule.authority.citation : null };
    }
    if (capSupplied < result) {
      steps.push({ step: 'cap_applied',
        detail: (capSpec.label || 'The date fixed by the other party') + ' (' + capSupplied +
          ') falls BEFORE the computed period, which would have ended ' + result +
          '. The earlier of the two governs, so it is the deadline. That date is used exactly as given and is not rolled off a weekend or holiday — it is a date fixed in the document, not a period this rule computes.',
        authority: rule.authority ? rule.authority.citation : null, date: capSupplied });
      cap = { state: 'applied', cap_date: capSupplied, computed_period_would_have_been: result, governs: 'cap' };
      result = capSupplied;
    } else if (capSupplied === result) {
      steps.push({ step: 'cap_tie',
        detail: (capSpec.label || 'The date fixed by the other party') + ' falls on exactly the same day the computed period ends (' +
          result + '). Both limbs give the same deadline.',
        authority: rule.authority ? rule.authority.citation : null, date: result });
      cap = { state: 'tie', cap_date: capSupplied, computed_period_would_have_been: result, governs: 'both' };
    } else {
      steps.push({ step: 'cap_not_applied',
        detail: (capSpec.label || 'The date fixed by the other party') + ' (' + capSupplied +
          ') falls AFTER the computed period, so the computed period is the earlier of the two and governs.',
        authority: rule.authority ? rule.authority.citation : null, date: result });
      cap = { state: 'not_applied', cap_date: capSupplied, computed_period_would_have_been: result, governs: 'computed_period' };
    }
  }

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
    } else if (typeof extStd.contested === 'function' && extStd.contested(input.service_method)) {
      // REFUSED VISIBLY, and reported DISTINCTLY from not_qualifying. The two
      // mean opposite things: not_qualifying says the rule clearly grants no
      // extension for this method, while this says the rule's own text does not
      // settle whether it does. Collapsing the second into the first would
      // assert settled law that is not settled, and would do it silently.
      // Today only W. Va. R. Civ. P. 6(e) declares this -- its subparagraph
      // pointer and its parenthetical name different subparagraphs; see that
      // standard's note.
      extension = { state: 'refused_contested_standard', standard: stdKey, days_added: 0,
        detail: 'Whether ' + extLabel + ' extends for service by ' + String(input.service_method).replace(/_/g, ' ') +
          ' is not resolved by the rule\'s own text, so no days were added and no date is offered for this method. The deadline below is computed WITHOUT an extension and may therefore be EARLIER than the true one. Resolve the extension by hand before relying on it.' };
      steps.push({ step: 'service_extension_refused',
        detail: 'The rule text does not settle whether this service method extends the period. No days were added.',
        authority: extLabel, date: result });
    } else if (!extStd.qualifies(input.service_method)) {
      extension = { state: 'not_qualifying', standard: stdKey, days_added: 0,
        detail: 'Service by ' + String(input.service_method).replace(/_/g, ' ') + ' does not qualify for an extension under ' + extLabel + ' (' + extStd.shape.replace(/_/g, ' ') + ').' };
    } else if (ext.requires_exclusive && exclusivityOf(input) === 'combined') {
      // EXCLUSIVITY IS NOT A METHOD -- it is a statement about the WHOLE SET of
      // methods used, and until 2026-08-27 this engine could not express it.
      //
      // Two rules need it. Utah URCP 6(c): 7 days "when ... service is made
      // EXCLUSIVELY BY MAIL under Rule 5(b)(3)(C)(i)". Florida R. Gen. Prac. &
      // Jud. Admin. 2.514(b): 5 days "when ... service is made BY ONLY MAIL".
      // Same condition, different words. Every other seeded extension asks only
      // WHICH method was used, which one field answers.
      //
      // The caller states the full set in `service_methods`. When it holds the
      // qualifying method AND something else, the condition FAILS and no days
      // are added -- reported distinctly from not_qualifying, because the two
      // mean different things: not_qualifying says this method never extends,
      // this says it would have but service was not exclusive.
      extension = { state: 'not_exclusive', standard: stdKey, days_added: 0,
        detail: extLabel + ' extends only where service was made by ' + String(input.service_method).replace(/_/g, ' ') +
          ' AND BY NOTHING ELSE. The methods supplied were ' + (input.service_methods || []).join(', ').replace(/_/g, ' ') +
          ', so the exclusivity condition is not met and no days were added.' };
      steps.push({ step: 'service_extension_refused',
        detail: 'The rule extends only for exclusive service by this method, and more than one method was used. No days were added.',
        authority: extLabel, date: result });
    } else if (ext.requires_exclusive && exclusivityOf(input) === 'unknown' && ext.on_unknown_exclusivity === 'refuse') {
      // REFUSED VISIBLY, the Virginia-missing-service_time pattern: the engine
      // will not guess a fact the caller can simply state. Chosen per rule
      // rather than globally, because the two jurisdictions differ in what is
      // at stake -- see on_unknown_exclusivity in the rule shape notes.
      extension = { state: 'refused_unverified_exclusivity', standard: stdKey, days_added: 0,
        detail: extLabel + ' adds days only where service was made by ' + String(input.service_method).replace(/_/g, ' ') +
          ' AND BY NOTHING ELSE, and only one method was supplied — which does not say whether it was the only one used. ' +
          'The engine will not assume exclusivity here: doing so would report a date LATER than the true deadline whenever ' +
          'another method was also used. Supply service_methods as the full list of methods actually used (for example ' +
          '["mail"] or ["mail","email"]) and the extension will be computed. The date below is computed WITHOUT it.' };
      steps.push({ step: 'service_extension_refused',
        detail: 'Whether service was exclusive is not known, and this rule refuses rather than assuming it. No days were added.',
        authority: extLabel, date: result });
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
      // AMOUNT AND UNIT CAN COME FROM THE STANDARD, NOT ONLY THE ROW.
      // Every standard before California added one fixed number of calendar
      // days for any qualifying method, so `ext.add` on the rule was enough.
      // California is not like that: CCP 1013 adds 5, 10, 12 or 20 CALENDAR
      // days depending on where the mail was sent from and to, and CCP 1013(c)
      // and (e) and CCP 1010.6(a)(3)(B) each add 2 COURT days. That table is
      // law, not row data, so it lives on the standard via an optional
      // amount(method) and every rule row simply points at the standard.
      // Standards without amount() are untouched and keep using ext.add.
      // ── amount() RECEIVES A CONTEXT, NOT ONLY A METHOD ──────────────────
      // Until Virginia, every per-method amount varied by METHOD ALONE, so
      // amount(method) was enough. Two real rules break that, in two different
      // ways, and both were documented as blocked on the same missing shape:
      //
      //   Va. Sup. Ct. R. 1:7   the amount depends on the TIME OF DAY service
      //                         was completed -- 0 days at or before 5:00 p.m.,
      //                         1 day after 5:00 p.m. but before midnight, for
      //                         the same method.
      //   N.C. R. Civ. P. 6(f)  the amount depends on the LENGTH OF THE BASE
      //                         PERIOD -- five days rather than three, but only
      //                         on "a prescribed period of 10 days or less".
      //
      // One addition serves both: amount() is handed a context object carrying
      // the facts it may need. The context is populated from what the engine
      // already knows at this point, so no caller changes for a standard that
      // does not read it, and every existing amount() ignores the second
      // argument and behaves exactly as before.
      //
      // NOTE ON 6(f): the MECHANISM now exists, but 6(f) itself is still not
      // implemented -- it additionally needs to know whether the served party
      // is an Address Confidentiality Program participant, which is a fact
      // about the PARTY and not an input this engine accepts today. No seeded
      // North Carolina row is 10 days or shorter, so it remains unreachable.
      // See its standard's note. It is named here so the next reader knows the
      // blocker moved rather than vanished.
      var amtCtx = {
        service_time: input.service_time || null,
        base_period_count: countValue,
        base_period_unit: count.unit
      };
      var amt = (typeof extStd.amount === 'function') ? extStd.amount(input.service_method, amtCtx) : null;

      // A standard may REFUSE rather than return an amount, when the context
      // it needs was not supplied. It must not fall through to ext.add: that
      // would silently pick one of the amounts the rule allows and present it
      // as computed. Reported as its own state for the same reason the other
      // three refusals are distinct from each other -- this one is the only
      // one the CALLER can fix, by supplying the missing fact.
      var refused = !!(amt && amt.refuse);
      if (refused) {
        extension = { state: 'refused_missing_context', standard: stdKey, days_added: 0,
          detail: amt.refuse.message };
        steps.push({ step: 'service_extension_refused',
          detail: amt.refuse.message,
          authority: extLabel, date: result });
      }
      // Everything below applies the extension, and is skipped entirely on a
      // refusal so that `result` keeps the unextended date the other refusal
      // states also return.
      if (!refused) {
      var addN = amt ? Number(amt.add) : Number(ext.add);
      var addUnit = (amt && amt.unit) || ext.unit || 'calendar_days';

      // ── WHERE THE ADDED DAYS START FROM ────────────────────────────────
      // See the sequencing note above SERVICE_EXTENSION_STANDARDS. A standard
      // whose rule says the days are added to THE PERIOD counts them from the
      // period's own unrolled last day, so the interim rollover applied above
      // is not part of the computation at all. A standard whose rule says the
      // days are added AFTER the period expires counts them from the rolled
      // date, which is what `result` already holds.
      //
      // Defaulting to the rolled date preserves the behaviour every standard
      // that predates this field was tested under.
      var seq = extStd.sequence || 'roll_then_add_then_roll';
      var addFrom = result;
      if (seq === 'add_to_period_then_roll') {
        if (cap) {
          // A cap fixes the deadline against a date the other party chose,
          // then this shape would re-derive from the unrolled period and throw
          // that away. No rule declares both today. Refused rather than
          // resolved by picking an order nobody has read.
          return { ok: false, code: 'CAP_EXTENSION_SEQUENCE_UNRESOLVED',
            message: 'Rule ' + rule.rule_id + ' declares both a cap and a service extension that is added to the period rather than after it expires. Which governs has not been read from any rule text, so no date is computed.' };
        }
        addFrom = base;
        if (rolled.date !== base) {
          steps.push({ step: 'rollover_superseded',
            detail: 'The interim rollover above does NOT apply to this deadline. Under ' + extLabel +
              ' the added days lengthen the period itself rather than following its expiry, so there is one period and one rollover, taken at the end. The added days are counted from ' + base +
              ', the unrolled last day of the base period, not from ' + rolled.date + '.',
            authority: extLabel, date: base });
        }
      }
      var extended, extDetail;
      if (addUnit === 'court_days' || addUnit === 'business_days') {
        // COURT DAYS ARE NOT CALENDAR DAYS. A two-court-day extension over a
        // weekend is four calendar days, and over a holiday weekend more.
        // Counting them as calendar days would produce a date EARLIER than the
        // true deadline, which is the direction that loses a filing.
        //
        // 'business_days' shares this branch rather than getting its own,
        // because the two rules describe the same operation in different
        // words: California's CCP 1013(c)/(e) and 1010.6(a)(3)(B) say "two
        // court days", New York's CPLR 2103(b)(6) says "one business day", and
        // both mean skip weekends and legal holidays while counting. The unit
        // name is preserved in the audit trail below so each cites its own
        // rule's wording rather than being normalised to the other's -- the
        // same reason Florida's "at least five days" was not normalised to
        // California's flat five.
        extended = addFrom;
        var left = addN, cdGuard = 0;
        while (left > 0 && cdGuard++ < 400) {
          extended = addDays(extended, sign);
          var hcd = holidayFor(input.calendars, input.jurisdiction, extended, direction);
          if (!hcd.known) {
            return { ok: false, code: 'NOT_PROVISIONED',
              message: 'No holiday calendar is loaded for ' + input.jurisdiction + (hcd.missingYear ? ' for ' + hcd.missingYear : '') + ', which court-day counting requires.',
              missing: { jurisdiction: input.jurisdiction, year: hcd.missingYear || null } };
          }
          if (!isWeekend(extended, std.weekend_days) && !hcd.hit) left--;
        }
        extDetail = addN + ' ' + addUnit.replace(/_/g, ' ') + ' added because service was by ' + String(input.service_method).replace(/_/g, ' ') +
          ', counted after the base period expired and SKIPPING weekends and legal holidays (' +
          addUnit.replace(/_/g, ' ') + ', not calendar days).';
      } else {
        extended = addDays(addFrom, sign * addN);
        extDetail = addN + ' days added because service was by ' + String(input.service_method).replace(/_/g, ' ') + ', counted ' +
          (seq === 'add_to_period_then_roll'
            ? 'as a lengthening of the period itself from its unrolled last day'
            : 'after the base period expired') +
          ', and including intermediate weekends and holidays.';
      }
      steps.push({ step: 'service_extension', detail: extDetail, authority: extLabel, date: extended });
      var rolled2 = rollOff(extended, input.calendars, input.jurisdiction, direction, std.weekend_days);
      if (!rolled2.ok) return rolled2;
      if (rolled2.date !== extended) {
        steps.push({ step: 'rollover_after_extension', detail: 'The added day fell on a Saturday, Sunday or legal holiday, so the last day to act is the next day that is not.', authority: extLabel + (stdKey === 'frcp_6d' ? ', 2005 Advisory Committee Note' : ''), date: rolled2.date });
      }
      result = rolled2.date;
      // APPLIED, but say so DIFFERENTLY when an exclusivity condition had to be
      // ASSUMED rather than checked. The arithmetic is identical -- deliberately,
      // on Michael's direction 2026-08-27 -- because for Florida the assumption
      // is usually right: a party served by mail is typically one for whom
      // portal e-service is unavailable, so "only mail" is usually literally
      // true, and refusing here would report EARLY on most mailed Florida
      // answers. But an assumption that can only fail LATE must never be
      // invisible, which is what it was before this state existed.
      var assumedExclusive = !!(ext.requires_exclusive && exclusivityOf(input) === 'unknown');
      extension = assumedExclusive
        ? { state: 'applied_exclusivity_assumed', standard: stdKey, days_added: addN, unit: addUnit,
            detail: addN + ' ' + addUnit.replace(/_/g, ' ') + ' added under ' + extLabel + ' — BUT ' + extLabel +
              ' adds them only where service was made by ' + String(input.service_method).replace(/_/g, ' ') +
              ' AND BY NOTHING ELSE, and only one method was supplied. Exclusivity was ASSUMED, not verified. ' +
              'If the same paper was also served by another method the true deadline is ' + addN + ' ' +
              addUnit.replace(/_/g, ' ') + ' EARLIER than the date below. Supply service_methods as the full list ' +
              'actually used to have this checked.' }
        : { state: 'applied', standard: stdKey, days_added: addN, unit: addUnit,
            detail: addN + ' ' + addUnit.replace(/_/g, ' ') + ' added under ' + extLabel + '.' };
      if (assumedExclusive) {
        steps.push({ step: 'service_extension_exclusivity_assumed',
          detail: 'This rule extends only for exclusive service by this method. Only one method was supplied, so exclusivity was assumed. The date is LATE by ' +
            addN + ' if another method was also used.',
          authority: extLabel, date: result });
      }
      }
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
    // Present only for rules that declare a service-completion standard. This
    // reports a change to the date the period RAN FROM, which is a different
    // fact from any extension and must not be collapsed into one -- a caller
    // reading only `trigger_date` would otherwise see the date they supplied
    // and have no way to learn the period actually started later. Null for
    // every rule with no completion standard.
    service_completion: completion,
    // Present only for a jurisdiction whose calendar is knowably incomplete in
    // a way that can only ever report EARLY. Top level, not inside rule.authority,
    // because a caller must not have to read a rule note to learn that the
    // date carries a caveat. Null for every jurisdiction with no declared gap.
    coverage: JURISDICTION_COVERAGE[input.jurisdiction] || null,
    // Present only for rules whose trigger names one specific document. Top
    // level for the same reason coverage is: a caller must not have to read a
    // rule note to learn that the date they supplied had to be a particular
    // document's. Null for every rule with no such ambiguity.
    trigger_document: triggerDocument,
    // The multi-trigger form. Null for every single-trigger rule, and for a
    // multi-trigger rule whose limbs are all unambiguous acts.
    trigger_documents: resolved.trigger_documents ? resolved.trigger_documents.limbs : null,
    // Present only for rules that declare a cap. Reports which limb governed
    // AND what the other one would have been, because "your deadline is
    // earlier than the rule's own period because of what the subpoena said"
    // is a materially different thing for an attorney to see than a bare date.
    cap: cap,
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
  DEFAULT_WEEKEND_DAYS, weekendDaysDefect, coverageTableDefects,
  triggerDocumentDefects, resolveTriggerDocument,
  triggerDocumentsDefects, resolveTriggerDocuments,
  holidayFor, rollOff, countExcludingWeekendsAndHolidays, computeDeadline,
  resolveTrigger, resolvePeriods, computeBasePeriod, applyRetrigger,
  COMPUTATION_STANDARDS, SERVICE_METHODS_EXTENDING, SERVICE_EXTENSION_STANDARDS,
  SERVICE_COMPLETION_STANDARDS, applyServiceCompletion,
  JURISDICTION_COVERAGE
};
