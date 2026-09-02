// api/_lib/subcontractor-compliance.js
// ---------------------------------------------------------------------------
// SHARED subcontractor compliance engine. Pure functions, no I/O, no app names.
//
// WHY SHARED AND NOT PER-APP. StoneDesk built this once (sd_subs / sd_sub_auth /
// sd_sub_jobs, api/sd-sub-auth.js, 2026-09-01). The worldwide competitive-gap
// audit then named the SAME gap for SAIRNroofing as Tier-A item A3, and
// SAIRNbuild is the obvious third. Building it a second and third time per app
// is precisely the duplication CLAUDE.md records as SAIRNsenior's root cause,
// and the same reasoning that drove the api/_resources registry split.
//
// WHAT THIS FILE DELIBERATELY DOES NOT DO. It does not touch StoneDesk's live
// implementation. sd_sub_auth is a live CREDENTIAL table -- pin_hash, pin_salt,
// failed_attempts, locked_until, confirmed present in the 2026-09-02 schema
// snapshot -- and renaming or re-keying it is a credential migration in its own
// right, the class push-gate check 2 and the recoverability guard exist for.
// StoneDesk repointing onto this module is a separate, guarded change. Until
// then two implementations coexist and that is a stated, temporary cost rather
// than an accident.
//
// SCOPE: identity + compliance + assignment eligibility + payment state.
// AUTHENTICATION IS NOT HERE. Sub login/PIN handling stays in each app's
// *-sub-auth endpoint against api/_lib/auth.js, because that is where the
// credential lifecycle and lockout rules already live and proving a second copy
// of those correct is not something to do as a side effect of a feature.
// ---------------------------------------------------------------------------

'use strict';

// A document is "expiring" this many days out. Not a compliance standard --
// a review window, and callers can override it. Named rather than inlined so
// nobody reads 30 as a legal figure.
const DEFAULT_WARN_DAYS = 30;

// The compliance documents this engine understands. Each is OPTIONAL at the
// data layer and REQUIRED only when a caller says so, because "insurance
// required before assignment" is a policy an operator sets, not a fact this
// module may assume for every trade in every state.
const DOC_TYPES = ['coi', 'licence', 'w9'];

const ASSIGNMENT_STATUSES = ['scheduled', 'in_progress', 'complete', 'cancelled'];
const PAYMENT_STATUSES = ['unbilled', 'invoiced', 'paid', 'disputed'];

function isDate(s) {
  return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s);
}

function daysBetween(fromISO, toISO) {
  const a = Date.parse(fromISO + 'T00:00:00Z');
  const b = Date.parse(toISO + 'T00:00:00Z');
  if (!isFinite(a) || !isFinite(b)) return null;
  return Math.round((b - a) / 86400000);
}

function num(v) {
  return typeof v === 'number' && isFinite(v) ? v : null;
}

// ── Document state ─────────────────────────────────────────────────────────
// FOUR STATES, AND 'missing' IS NOT 'expired'. A subcontractor with no
// certificate on file and one whose certificate lapsed last week are different
// operational facts: the first needs collecting, the second needs chasing. The
// original StoneDesk columns (coi_expiry, licence_expiry, w9_on_file) can
// express both, so nothing is lost by keeping them apart -- and collapsing them
// into one "not ok" is how a dashboard starts lying about what is wrong.
function documentState(expiry, today, warnDays) {
  const w = num(warnDays) === null ? DEFAULT_WARN_DAYS : num(warnDays);
  if (!expiry) return { state: 'missing', days_left: null };
  if (!isDate(expiry)) return { state: 'unreadable', days_left: null };
  if (!isDate(today)) return { state: 'unknown', days_left: null };
  const d = daysBetween(today, expiry);
  if (d === null) return { state: 'unreadable', days_left: null };
  if (d < 0) return { state: 'expired', days_left: d };
  if (d <= w) return { state: 'expiring', days_left: d };
  return { state: 'valid', days_left: d };
}

// ── Whole-subcontractor compliance ─────────────────────────────────────────
// `required` names which documents this operator insists on. Anything not
// required is still REPORTED -- an expired certificate you do not currently
// mandate is information, not nothing -- but it cannot block an assignment.
function evaluateSubcontractor(input) {
  input = input || {};
  const sub = input.subcontractor || null;
  const today = isDate(input.today) ? input.today : null;
  const warnDays = input.warn_days;
  const required = Array.isArray(input.required) ? input.required : [];

  if (!sub) {
    return { ok: false, error: { code: 'NO_SUBCONTRACTOR', message: 'no subcontractor supplied' } };
  }
  if (!today) {
    // Refuses rather than defaulting to the server clock. A caller that forgot
    // to pass a date would otherwise get answers keyed to UTC "now", and every
    // date bug on this platform this week has come from an implied clock.
    return { ok: false, error: { code: 'NO_TODAY', message: 'today (YYYY-MM-DD) is required -- this engine will not assume a clock' } };
  }

  const docs = {
    coi: documentState(sub.coi_expiry, today, warnDays),
    licence: documentState(sub.licence_expiry, today, warnDays),
    // W-9 has no expiry. It is on file or it is not, so it is modelled as a
    // boolean rather than being given a fake date to make the shapes match.
    w9: { state: sub.w9_on_file === true ? 'valid' : 'missing', days_left: null }
  };

  const unknownRequired = required.filter(function (r) { return DOC_TYPES.indexOf(r) === -1; });
  const blocking = required.filter(function (r) {
    const s = docs[r] && docs[r].state;
    return s === 'missing' || s === 'expired' || s === 'unreadable';
  });
  const warnings = DOC_TYPES.filter(function (r) {
    const s = docs[r] && docs[r].state;
    return s === 'expiring' || (required.indexOf(r) === -1 && (s === 'expired' || s === 'unreadable'));
  });

  return {
    ok: true,
    sub_id: sub.sub_id || null,
    name: sub.name || null,
    trade: sub.trade || null,
    active: sub.active !== false,
    documents: docs,
    required: required,
    // An unrecognised requirement is surfaced, never silently ignored: a typo
    // in a policy list would otherwise read as "requirement satisfied".
    unknown_requirements: unknownRequired,
    blocking: blocking,
    warnings: warnings,
    compliant: blocking.length === 0 && unknownRequired.length === 0
  };
}

// ── Assignment eligibility ─────────────────────────────────────────────────
// Separated from evaluateSubcontractor on purpose: "is this sub compliant" and
// "may this sub be put on this job" are different questions, and an inactive
// sub with perfect paperwork must fail the second while passing the first.
function canAssign(input) {
  input = input || {};
  const ev = evaluateSubcontractor(input);
  if (!ev.ok) return ev;
  const reasons = [];
  if (!ev.active) reasons.push('subcontractor is not active');
  ev.blocking.forEach(function (b) {
    reasons.push(b + ' is ' + ev.documents[b].state);
  });
  ev.unknown_requirements.forEach(function (u) {
    reasons.push('unrecognised requirement "' + u + '" -- cannot be evaluated, so it is treated as unmet');
  });
  return {
    ok: true,
    sub_id: ev.sub_id,
    allowed: reasons.length === 0,
    reasons: reasons,
    // Carried through so a caller can show WHY without a second call.
    evaluation: ev
  };
}

// ── Payment state on an assignment ─────────────────────────────────────────
// Money is derived, never stored twice: `amount` is what was agreed and
// `paid` is the sum of recorded payments. Outstanding is computed here rather
// than persisted, the same rule sql/sairnroofing_billing_schema.sql already
// applies to invoice balances.
function summariseAssignment(assignment) {
  assignment = assignment || {};
  const amount = num(assignment.amount) || 0;
  const payments = Array.isArray(assignment.payments) ? assignment.payments : [];
  const paid = payments.reduce(function (s, p) {
    return s + (num(p && p.amount) || 0);
  }, 0);
  const outstanding = Math.round((amount - paid) * 100) / 100;
  const status = ASSIGNMENT_STATUSES.indexOf(assignment.status) === -1 ? null : assignment.status;
  let payment_status;
  if (amount === 0) payment_status = 'unbilled';
  else if (outstanding <= 0) payment_status = 'paid';
  else if (paid > 0) payment_status = 'part_paid';
  else payment_status = 'invoiced';
  return {
    assignment_id: assignment.assignment_id || null,
    sub_id: assignment.sub_id || null,
    job_id: assignment.job_id || null,
    scheduled_date: isDate(assignment.scheduled_date) ? assignment.scheduled_date : null,
    // An unrecognised status is reported as null WITH a problem rather than
    // being passed through, so a typo cannot travel into a report as if real.
    status: status,
    problems: status === null && assignment.status !== undefined
      ? ['unrecognised status "' + String(assignment.status) + '"']
      : [],
    amount: amount,
    paid: Math.round(paid * 100) / 100,
    outstanding: outstanding < 0 ? 0 : outstanding,
    overpaid: outstanding < 0 ? Math.abs(outstanding) : 0,
    payment_status: payment_status
  };
}

module.exports = {
  DEFAULT_WARN_DAYS,
  DOC_TYPES,
  ASSIGNMENT_STATUSES,
  PAYMENT_STATUSES,
  documentState,
  evaluateSubcontractor,
  canAssign,
  summariseAssignment
};
