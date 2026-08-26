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
    rollover_suffix_forward: '', rollover_suffix_backward: '' }
};

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
var JURISDICTION_COVERAGE = {
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
  }
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
function applyServiceCompletion(cstd, txDate, serviceTime, calendars, jurisdiction) {
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
  var badDay = isWeekend(txDate) || h.hit;
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
  var rolled = rollOff(addDays(txDate, 1), calendars, jurisdiction, 'forward');
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
    if (std.short_period_exclusion_days && countValue < std.short_period_exclusion_days) {
      var shortRes = countExcludingWeekendsAndHolidays(triggerDate, sign, countValue, calendars, jurisdiction, direction);
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
      var startRes = rollOff(addDays(triggerDate, sign), calendars, jurisdiction, direction);
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
      if (!isWeekend(cur) && !hb.hit) remaining--;
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
    var res = resolveTrigger(rr, input, rrStd);
    if (!res.ok) return res;
    var ret = applyRetrigger(rr, res.date, input);
    if (!ret.ok) return ret;
    resolvedByRule[rr.rule_id] = { date: ret.date, resolution: res.resolution,
      period_resolution: res.period_resolution || null, count_override: res.count_override || null,
      retrigger: ret.retriggered ? ret : null };
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
      var comp = applyServiceCompletion(cstd, triggerDate, input.service_time, input.calendars, input.jurisdiction);
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
  var rolled = rollOff(base, input.calendars, input.jurisdiction, direction);
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
          if (!isWeekend(extended) && !hcd.hit) left--;
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
      var rolled2 = rollOff(extended, input.calendars, input.jurisdiction, direction);
      if (!rolled2.ok) return rolled2;
      if (rolled2.date !== extended) {
        steps.push({ step: 'rollover_after_extension', detail: 'The added day fell on a Saturday, Sunday or legal holiday, so the last day to act is the next day that is not.', authority: extLabel + (stdKey === 'frcp_6d' ? ', 2005 Advisory Committee Note' : ''), date: rolled2.date });
      }
      result = rolled2.date;
      extension = { state: 'applied', standard: stdKey, days_added: addN, unit: addUnit,
        detail: addN + ' ' + addUnit.replace(/_/g, ' ') + ' added under ' + extLabel + '.' };
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
  holidayFor, rollOff, countExcludingWeekendsAndHolidays, computeDeadline,
  resolveTrigger, resolvePeriods, computeBasePeriod, applyRetrigger,
  COMPUTATION_STANDARDS, SERVICE_METHODS_EXTENDING, SERVICE_EXTENSION_STANDARDS,
  SERVICE_COMPLETION_STANDARDS, applyServiceCompletion,
  JURISDICTION_COVERAGE
};
