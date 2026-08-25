// api/_lib/roofing-agreements.js
// SAIRNroofing Phase 5 (final piece) -- the contingency agreement as a tracked
// document with a signature state, and its rescission clock.
//
// PURE -- no I/O. Everything here is arithmetic over a stored rule and a stored
// agreement. No LLM anywhere in this path, for the same reason as the supplement
// engine: a rescission deadline is a date a court can check, not an opinion.
//
// ── WHY THE RULE IS PER-STATE DATA AND NOT A CONSTANT ────────────────────
// Three states were read directly before this file was written, and they
// disagree on every axis that matters:
//
//   Colorado  C.R.S. 6-22-104 -- rescind within 72 HOURS after the insurer's
//             WRITTEN DENIAL (not after signing). 6-22-103 additionally
//             enumerates required contract terms and a bold hold-in-trust
//             clause. Notably the right does NOT extend to supplemental
//             services whose damage could not reasonably have been foreseen at
//             the initial inspection -- which is precisely this app's
//             `asserted` / hidden_damage supplement class.
//   Florida   Fla. Stat. 489.147 -- cancel within 10 DAYS after EXECUTION, for
//             contracts entered into on events under a declared state of
//             emergency; and omitting the prohibited-practices notice lets the
//             owner void the contract after ten days.
//   Texas     Bus. & Com. 27.02 -- no rescission right at all in that section;
//             what it mandates is a 12-point BOLDFACE deductible notice.
//   Ohio      R.C. 1345.21-.28 (Home Solicitation Sales Act) -- three BUSINESS
//             days from the transaction, and it is conditional: it applies to a
//             sale solicited away from the seller's fixed place of business,
//             which is exactly the storm-chasing door-knock. See INDEFINITE
//             below.
//
// Different trigger events, different units, different conditions. A single
// hardcoded template would be wrong in three of four jurisdictions, so the rule
// is a row with a citation -- the same shape rf_cert_rules already uses for
// licensing, and for the same reason.
//
// ── THE INDEFINITE CASE IS THE WHOLE POINT ───────────────────────────────
// Ohio R.C. 1345.23 requires BOTH a conspicuous written notice of the right to
// cancel AND a separate, detachable, duplicate "Notice of Cancellation" form.
// If the seller fails to provide them, the buyer's right to cancel does not
// expire -- it runs until the seller complies. A roofer who skipped the form
// has open-ended exposure on every contract they ever signed, and no calendar
// anywhere shows it. That is a mechanical check against real data, which is the
// class of thing this platform exists to do, so it is modelled explicitly
// rather than collapsed into an ordinary deadline.
//
// ── WHAT THIS FILE DELIBERATELY DOES NOT DO ──────────────────────────────
// It does not generate statutory notice TEXT. The rule row carries the
// mechanical facts (trigger, count, unit, whether a form is required, what
// non-compliance does) plus its citation; the verbatim notice wording is
// contractor-entered with a named source, never authored here. Inventing
// statutory language would be the exact fabrication class Guardian exists to
// catch, and a notice that is close but not verbatim is worse than none.

'use strict';

// An agreement's history is APPEND-ONLY -- rescission is a new row, never an
// edit to the executed one. An executed agreement is evidence, and evidence
// that can be rewritten afterwards is not evidence (the same argument
// sql/sairnroofing_claims_schema.sql already makes for rf_claim_photos).
const AGREEMENT_EVENTS = ['executed', 'rescinded'];

// What starts the clock. Read from the statutes above, not invented.
const RESCISSION_TRIGGERS = [
  'execution',      // FL 489.147(6), OH 1345.22 -- from the date of the transaction
  'insurer_denial'  // CO 6-22-104 -- from the insurer's WRITTEN denial
];

const RESCISSION_UNITS = ['business_days', 'calendar_days', 'hours'];

// ── "BUSINESS DAY" IS NOT A UNIVERSAL TERM, AND ASSUMING IT WAS WAS A BUG ─
// The first version of this file excluded Saturday and Sunday, which is the
// ordinary meaning and is WRONG in Ohio. R.C. 1345.21 defines a business day
// for the Home Solicitation Sales Act as "any calendar day except Sunday, or
// the following business holidays" -- SATURDAY COUNTS. On a Thursday signing
// that is the difference between a Monday and a Tuesday deadline, in the
// direction that costs the contractor a day of exposure they did not know they
// had. Caught by reading the definitions section rather than the operative one.
//
// So the basis is a property of the RULE, not of this file. And because Ohio
// enumerates its eleven holidays by name, they can be applied exactly instead
// of disclosed as a shortfall.
const BUSINESS_DAY_BASES = ['oh_hssa', 'mon_fri'];

// The eleven holidays named in R.C. 1345.21, computed rather than listed per
// year. The statute names the days; it does not provide for observed-day
// shifting when one falls on a Sunday, so none is applied and the result says
// so.
function nthWeekdayUTC(year, monthIdx, dow, n) {
  const d = new Date(Date.UTC(year, monthIdx, 1));
  let count = 0;
  for (;;) {
    if (d.getUTCDay() === dow) { count += 1; if (count === n) return d; }
    d.setUTCDate(d.getUTCDate() + 1);
  }
}
function lastWeekdayUTC(year, monthIdx, dow) {
  const d = new Date(Date.UTC(year, monthIdx + 1, 0));
  while (d.getUTCDay() !== dow) d.setUTCDate(d.getUTCDate() - 1);
  return d;
}
function ohioHssaHolidays(year) {
  const k = function (d) { return d.toISOString().slice(0, 10); };
  return [
    k(new Date(Date.UTC(year, 0, 1))),        // New Year's day
    k(nthWeekdayUTC(year, 0, 1, 3)),          // Martin Luther King day -- 3rd Monday in January
    k(nthWeekdayUTC(year, 1, 1, 3)),          // Presidents' day -- 3rd Monday in February
    k(lastWeekdayUTC(year, 4, 1)),            // Memorial day -- last Monday in May
    k(new Date(Date.UTC(year, 5, 19))),       // Juneteenth day
    k(new Date(Date.UTC(year, 6, 4))),        // Independence day
    k(nthWeekdayUTC(year, 8, 1, 1)),          // Labor day -- 1st Monday in September
    k(nthWeekdayUTC(year, 9, 1, 2)),          // Columbus day -- 2nd Monday in October
    k(new Date(Date.UTC(year, 10, 11))),      // Veterans day
    k(nthWeekdayUTC(year, 10, 4, 4)),         // Thanksgiving day -- 4th Thursday in November
    k(new Date(Date.UTC(year, 11, 25)))       // Christmas day
  ];
}

// Where the contract was signed. Ohio's Act turns on this and nothing else in
// the record can stand in for it, so it is captured at signing rather than
// inferred later.
const SIGNING_VENUES = ['buyer_residence', 'seller_place_of_business', 'other'];

function isNum(n) { return typeof n === 'number' && isFinite(n); }
function parseDate(v) {
  if (!v) return null;
  const d = new Date(v);
  return isNaN(d.getTime()) ? null : d;
}

// Business-day arithmetic under the named basis.
//
//   oh_hssa  -- R.C. 1345.21: every day except Sunday and the eleven named
//               holidays. Saturday counts. Holidays ARE applied exactly.
//   mon_fri  -- the ordinary meaning, for a state whose statute has not been
//               read yet. Holidays are NOT applied, and every result computed
//               on this basis says so (disclosures.holidays_applied === false)
//               rather than hiding the shortfall.
function addBusinessDays(start, n, basis) {
  const d = new Date(start.getTime());
  const holidayCache = Object.create(null);
  const isOhioHoliday = function (dt) {
    const y = dt.getUTCFullYear();
    if (!holidayCache[y]) holidayCache[y] = ohioHssaHolidays(y);
    return holidayCache[y].indexOf(dt.toISOString().slice(0, 10)) !== -1;
  };
  let added = 0;
  while (added < n) {
    d.setUTCDate(d.getUTCDate() + 1);
    const dow = d.getUTCDay();
    if (basis === 'oh_hssa') {
      if (dow !== 0 && !isOhioHoliday(d)) added += 1;
    } else if (dow !== 0 && dow !== 6) {
      added += 1;
    }
  }
  return d;
}

// Validate a rule row before anything is computed from it. A rule that is
// wrong is worse than a rule that is absent, because the absent one shows an
// honest empty state and the wrong one shows a confident date.
function validateRule(rule) {
  const problems = [];
  if (!rule || typeof rule !== 'object') return ['no rule supplied'];
  if (RESCISSION_TRIGGERS.indexOf(rule.trigger) === -1) problems.push('trigger must be one of: ' + RESCISSION_TRIGGERS.join(', '));
  if (RESCISSION_UNITS.indexOf(rule.unit) === -1) problems.push('unit must be one of: ' + RESCISSION_UNITS.join(', '));
  if (!isNum(rule.count) || rule.count <= 0) problems.push('count must be a positive number');
  if (!rule.authority) problems.push('a rule with no authority citation cannot be relied on');
  return problems;
}

// Required fields on an executed agreement.
function validateAgreement(payload) {
  const problems = [];
  if (!payload || typeof payload !== 'object') return ['no agreement supplied'];
  if (!payload.id) problems.push('agreement_id (payload.id) is required');
  if (!payload.claim_id) problems.push('claim_id is required');
  if (AGREEMENT_EVENTS.indexOf(payload.event_type) === -1) problems.push('event_type must be one of: ' + AGREEMENT_EVENTS.join(', '));
  if (payload.event_type === 'executed') {
    if (!String(payload.signer_name || '').trim()) problems.push('signer_name is required on an executed agreement');
    if (!String(payload.signature_data || '').trim()) problems.push('signature_data is required on an executed agreement');
    if (SIGNING_VENUES.indexOf(payload.signing_venue) === -1) problems.push('signing_venue must be one of: ' + SIGNING_VENUES.join(', '));
    if (!parseDate(payload.executed_at)) problems.push('executed_at must be a real date');
    if (!String(payload.state || '').trim()) problems.push('state is required -- the rescission rule is per-state');
  }
  if (payload.event_type === 'rescinded') {
    if (!payload.supersedes) problems.push('a rescission must name the executed agreement_id it supersedes');
    if (!parseDate(payload.rescinded_at)) problems.push('rescinded_at must be a real date');
  }
  return problems;
}

// Evaluate one claim's agreement chain against its state rule.
//
//   rule      : { state, trigger, count, unit, form_required, notice_required,
//                 indefinite_if_noncompliant, applies_only_when_solicited,
//                 authority }
//   events    : the append-only rows for this claim, any order
//   denial_at : the insurer's written-denial date, when the rule triggers on it
//   now       : evaluation instant (injected so tests are deterministic)
//
// Never throws. Collects problems the way the supplement engine does, so the
// worksheet can show them beside the line rather than failing the whole card.
function evaluateAgreement(input) {
  input = input || {};
  const rule = input.rule || null;
  const events = Array.isArray(input.events) ? input.events.slice() : [];
  const now = parseDate(input.now) || new Date();
  const problems = [];

  const executed = events
    .filter(function (e) { return e && e.event_type === 'executed'; })
    .sort(function (a, b) { return (parseDate(a.executed_at) || 0) - (parseDate(b.executed_at) || 0); });
  const latest = executed.length ? executed[executed.length - 1] : null;
  if (executed.length > 1) problems.push(executed.length + ' executed agreements exist for this claim; the latest is shown');

  if (!latest) {
    return {
      ok: true, signed: false, status: 'unsigned', rule_applied: null,
      trigger: null, trigger_at: null, deadline_at: null, hours_remaining: null,
      disclosures: {}, problems: problems
    };
  }

  const rescission = events.filter(function (e) {
    return e && e.event_type === 'rescinded' && e.supersedes === latest.agreement_id;
  })[0] || null;

  // No rule for this state is an HONEST EMPTY STATE, not a zero. It means
  // nobody has entered the requirement yet -- which is a different fact from
  // "this state imposes no right of rescission", and the two must never render
  // the same way.
  if (!rule) {
    return {
      ok: true, signed: true, status: rescission ? 'rescinded' : 'no_rule',
      rule_applied: null, trigger: null, trigger_at: null, deadline_at: null,
      hours_remaining: null,
      disclosures: { note: 'no contingency rule is on file for ' + (latest.state || 'this state') + ' -- the rescission window cannot be computed' },
      problems: problems, executed: latest, rescission: rescission
    };
  }
  const ruleProblems = validateRule(rule);
  if (ruleProblems.length) {
    return {
      ok: true, signed: true, status: 'rule_invalid', rule_applied: rule.rule_id || null,
      trigger: null, trigger_at: null, deadline_at: null, hours_remaining: null,
      disclosures: {}, problems: problems.concat(ruleProblems), executed: latest, rescission: rescission
    };
  }

  const disclosures = {
    holidays_applied: false,
    authority: rule.authority,
    notice_given: latest.notice_given === true,
    cancellation_form_given: latest.cancellation_form_given === true
  };

  // Ohio-shaped conditional: the Act reaches only a sale solicited away from
  // the seller's fixed place of business. Signed at the shop, it does not apply
  // -- and saying so is a real answer, not a gap.
  if (rule.applies_only_when_solicited && latest.signing_venue === 'seller_place_of_business') {
    return {
      ok: true, signed: true, status: rescission ? 'rescinded' : 'rule_not_applicable',
      rule_applied: rule.rule_id || null, trigger: null, trigger_at: null,
      deadline_at: null, hours_remaining: null,
      disclosures: Object.assign(disclosures, { note: 'signed at the seller\'s place of business, so ' + rule.authority + ' does not reach this contract' }),
      problems: problems, executed: latest, rescission: rescission
    };
  }

  // The compliance failure that removes the deadline entirely. Checked BEFORE
  // the arithmetic, because when it fires there is no date to compute.
  const missing = [];
  if (rule.notice_required && !disclosures.notice_given) missing.push('written notice of the right to cancel');
  if (rule.form_required && !disclosures.cancellation_form_given) missing.push('the separate detachable cancellation form');
  if (missing.length && rule.indefinite_if_noncompliant) {
    return {
      ok: true, signed: true, status: rescission ? 'rescinded' : 'indefinite',
      rule_applied: rule.rule_id || null, trigger: rule.trigger, trigger_at: null,
      deadline_at: null, hours_remaining: null,
      disclosures: Object.assign(disclosures, {
        missing: missing,
        note: 'the buyer\'s right to cancel does not expire until ' + missing.join(' and ') + ' is provided (' + rule.authority + ')'
      }),
      problems: problems, executed: latest, rescission: rescission
    };
  }

  // Which instant starts the clock.
  const triggerAt = rule.trigger === 'insurer_denial'
    ? parseDate(input.denial_at)
    : parseDate(latest.executed_at);
  if (!triggerAt) {
    return {
      ok: true, signed: true, status: rescission ? 'rescinded' : 'not_triggered',
      rule_applied: rule.rule_id || null, trigger: rule.trigger, trigger_at: null,
      deadline_at: null, hours_remaining: null,
      disclosures: Object.assign(disclosures, {
        note: rule.trigger === 'insurer_denial'
          ? 'the clock starts on the insurer\'s written denial, which has not been recorded'
          : 'no execution date recorded'
      }),
      problems: problems, executed: latest, rescission: rescission
    };
  }

  let deadline;
  if (rule.unit === 'hours') {
    deadline = new Date(triggerAt.getTime() + rule.count * 3600 * 1000);
  } else if (rule.unit === 'calendar_days') {
    deadline = new Date(triggerAt.getTime());
    deadline.setUTCDate(deadline.getUTCDate() + rule.count);
  } else {
    const basis = BUSINESS_DAY_BASES.indexOf(rule.business_day_basis) !== -1 ? rule.business_day_basis : 'mon_fri';
    deadline = addBusinessDays(triggerAt, rule.count, basis);
    // R.C. 1345.22 runs to MIDNIGHT of the third business day, not to the same
    // clock time -- so the buyer gets the whole final day.
    deadline.setUTCHours(23, 59, 59, 999);
    disclosures.business_day_basis = basis;
    if (basis === 'oh_hssa') {
      disclosures.holidays_applied = true;
      disclosures.note = 'R.C. 1345.21 basis: Saturday IS a business day; Sunday and the eleven named holidays are excluded. No observed-day shifting is applied -- the statute names the days and does not provide for it';
    } else {
      disclosures.note = 'Saturday and Sunday excluded on the ordinary meaning; this state\'s statutory definition of "business day" has NOT been read, and no holiday calendar is applied -- confirm the final day before relying on it';
    }
  }

  const remainingMs = deadline.getTime() - now.getTime();
  return {
    ok: true, signed: true,
    status: rescission ? 'rescinded' : (remainingMs > 0 ? 'open' : 'expired'),
    rule_applied: rule.rule_id || null,
    trigger: rule.trigger,
    trigger_at: triggerAt.toISOString(),
    deadline_at: deadline.toISOString(),
    hours_remaining: rescission ? null : Math.round((remainingMs / 3600000) * 100) / 100,
    disclosures: disclosures,
    problems: problems,
    executed: latest,
    rescission: rescission
  };
}

module.exports = {
  AGREEMENT_EVENTS,
  BUSINESS_DAY_BASES,
  RESCISSION_TRIGGERS,
  RESCISSION_UNITS,
  SIGNING_VENUES,
  validateRule,
  validateAgreement,
  evaluateAgreement
};
