// api/_lib/roofing-prequal.js
// SAIRNroofing gap B7 -- the contractor's OWN prequalification packet and
// bonding position.
//
// PURE -- no I/O, no LLM.
//
// ── WHICH DIRECTION THIS FACES, BECAUSE IT IS THE OPPOSITE OF SAIRNBUILD ──
// The 2026-08-26 competitive-gap audit's Tier-B item B7: "Prequalification /
// bonding -- a Tier-B-only category (TradeTapp, Highwire, Constrafor) that
// exists because GCs and owners require it of bonded subs. Absent."
//
// Checked before writing a line, because this is the third time a "new" build
// nearly duplicated something already on the platform. SAIRNbuild HAS
// prequalification and bonding fields -- prequal_status, financial_capacity,
// safety_record, references_checked, bonding_capacity, current_backlog_pct --
// but they sit ON ITS SUBCONTRACTORS. SAIRNbuild is the general contractor
// qualifying the trades it hires.
//
// This file faces the other way: SAIRNroofing's customer IS the roofer, and at
// Tier B the roofer is the SUB being qualified. What a GC asks THEM for -- an
// EMR letter, audited financials, a safety programme, references, a surety
// letter with single-project and aggregate limits -- is what this tracks. Same
// vocabulary, opposite subject, and nothing here duplicates SAIRNbuild.
//
// Verified 2026-09-02: sairnroofing.html has ZERO hits for bond, EMR,
// experience modification, prequal or surety.
//
// ── WHAT IT REFUSES TO INTERPRET ─────────────────────────────────────────
// EMR IS REPORTED, NEVER JUDGED. "Under 1.0" is a threshold individual GCs and
// owners set in their own prequalification criteria; it is not a rule and it is
// not this application's to assert. The engine records the rate, its year and
// its source, and says nothing about whether it is good enough -- because the
// answer differs per GC and being wrong about it loses a bid on a number we
// made up.
//
// NO EXPIRY WINDOW IS SEEDED. A financial statement is "current" for as long as
// the GC asking for it says, and that varies. Every document carries the
// expiry the contractor entered, and one without a date reads
// 'no_expiry_recorded' rather than being assumed to be fine.
//
// ── IT WILL NOT ASSUME A CLOCK ───────────────────────────────────────────
// Every entry point requires a caller-supplied `today`.

'use strict';

// A review window for a packet, not a rule. Callers override it.
const DEFAULT_WARN_DAYS = 30;

function isDate(s) { return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s); }
function str(v) { return typeof v === 'string' ? v.trim() : ''; }
function num(v) {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  return (typeof n === 'number' && isFinite(n)) ? n : null;
}
function money(n) { return Math.round(n * 100) / 100; }
function daysBetween(a, b) {
  const x = Date.parse(a + 'T00:00:00Z'), y = Date.parse(b + 'T00:00:00Z');
  if (!isFinite(x) || !isFinite(y)) return null;
  return Math.round((y - x) / 86400000);
}

// ── One document in the packet ───────────────────────────────────────────
function documentState(input) {
  input = input || {};
  const today = isDate(input.today) ? input.today : null;
  if (!today) {
    return { ok: false, error: { code: 'NO_TODAY', message: 'today (YYYY-MM-DD) is required -- this engine will not assume a clock' } };
  }
  const d = input.document || null;
  if (!d) return { ok: false, error: { code: 'NO_DOCUMENT', message: 'no document supplied' } };
  const warn = num(input.warn_days) === null ? DEFAULT_WARN_DAYS : num(input.warn_days);

  const out = {
    ok: true,
    document_id: str(d.document_id) || null,
    kind: str(d.kind) || null,
    issuer: str(d.issuer) || null,
    effective_on: isDate(d.effective_on) ? d.effective_on : null,
    expires_on: isDate(d.expires_on) ? d.expires_on : null,
    reference: str(d.reference) || null,
    // EMR and similar numeric facts ride along UNJUDGED. See the header.
    value: num(d.value),
    value_year: num(d.value_year),
    source: str(d.source) || null,
    state: 'unknown',
    days_left: null,
    problems: []
  };

  if (!out.expires_on) {
    // Not "fine". A GC asking for a current financial statement is asking a
    // question this record cannot answer.
    out.state = 'no_expiry_recorded';
  } else {
    const left = daysBetween(today, out.expires_on);
    out.days_left = left;
    if (left === null) out.state = 'no_expiry_recorded';
    else if (left < 0) out.state = 'expired';
    else if (left <= warn) out.state = 'expiring';
    else out.state = 'current';
  }
  if (out.value !== null && !out.source) {
    out.problems.push('a figure is recorded with no source -- name where it came from (your insurer, your accountant, your surety) before putting it in a prequalification packet');
  }
  if (out.value !== null && out.value_year === null) {
    // An EMR with no year is unusable: a GC asks for a specific year's rate.
    out.problems.push('a figure is recorded with no year -- a prequalification form asks for a specific year');
  }
  return out;
}

// ── Is the packet ready to submit? ───────────────────────────────────────
// `required_kinds` is what THIS GC asked for. There is no default list,
// because there is no universal one -- every GC's prequalification form differs
// and shipping a guess would tell a contractor they are ready when they are not.
function packetReadiness(input) {
  input = input || {};
  const today = isDate(input.today) ? input.today : null;
  if (!today) {
    return { ok: false, error: { code: 'NO_TODAY', message: 'today (YYYY-MM-DD) is required -- this engine will not assume a clock' } };
  }
  const required = Array.isArray(input.required_kinds)
    ? input.required_kinds.map(str).filter(Boolean) : [];
  const docs = (Array.isArray(input.documents) ? input.documents : []).map(function (d) {
    return documentState({ document: d, today: today, warn_days: input.warn_days });
  }).filter(function (r) { return r.ok; });

  const best = Object.create(null);
  docs.forEach(function (d) {
    const k = d.kind;
    if (!k) return;
    // If several documents share a kind, the one that is current wins, then
    // the one expiring furthest out. A stale duplicate must not mask a good
    // one, and a good one must not be hidden by a stale duplicate.
    const cur = best[k];
    const rank = function (x) { return x.state === 'current' ? 3 : x.state === 'expiring' ? 2 : x.state === 'no_expiry_recorded' ? 1 : 0; };
    if (!cur || rank(d) > rank(cur) ||
        (rank(d) === rank(cur) && (d.days_left || -1e9) > (cur.days_left || -1e9))) {
      best[k] = d;
    }
  });

  const missing = [], expired = [], expiring = [], undated = [], satisfied = [];
  required.forEach(function (k) {
    const d = best[k];
    if (!d) { missing.push(k); return; }
    if (d.state === 'expired') expired.push(k);
    else if (d.state === 'no_expiry_recorded') undated.push(k);
    else if (d.state === 'expiring') { expiring.push(k); satisfied.push(k); }
    else satisfied.push(k);
  });

  return {
    ok: true,
    today: today,
    required: required,
    satisfied: satisfied,
    // FOUR failure states, not one. Never collected, lapsed, and on file with
    // no date are three different jobs, and expiring is a warning rather than
    // a blocker.
    missing: missing,
    expired: expired,
    undated: undated,
    expiring: expiring,
    ready: required.length > 0 && missing.length === 0 && expired.length === 0 && undated.length === 0,
    // Documents held that this GC did not ask for -- useful, and NOT counted
    // toward readiness.
    extra: Object.keys(best).filter(function (k) { return required.indexOf(k) === -1; }),
    documents: docs
  };
}

// ── Bonding capacity ─────────────────────────────────────────────────────
// The computable core, and the number a surety and a GC both ask about.
// `committed_backlog` is supplied by the caller -- derived from real contract
// values and what has been earned, never invented here -- and the result names
// the basis so a reader can tell what the remaining figure was worked out from.
function bondingCapacity(input) {
  input = input || {};
  const today = isDate(input.today) ? input.today : null;
  if (!today) {
    return { ok: false, error: { code: 'NO_TODAY', message: 'today (YYYY-MM-DD) is required -- this engine will not assume a clock' } };
  }
  const b = input.bonding || null;
  if (!b) return { ok: false, error: { code: 'NO_BONDING', message: 'no bonding record supplied' } };

  const single = num(b.single_project_limit);
  const aggregate = num(b.aggregate_limit);
  const backlog = num(input.committed_backlog);
  const candidate = num(input.candidate_value);

  const out = {
    ok: true,
    surety: str(b.surety) || null,
    agent: str(b.agent) || null,
    single_project_limit: single,
    aggregate_limit: aggregate,
    effective_on: isDate(b.effective_on) ? b.effective_on : null,
    expires_on: isDate(b.expires_on) ? b.expires_on : null,
    source: str(b.source) || null,
    letter_state: 'unknown',
    committed_backlog: backlog === null ? null : money(backlog),
    backlog_basis: str(input.backlog_basis) || null,
    remaining_aggregate: null,
    candidate_value: candidate,
    candidate: 'unknown',
    problems: []
  };

  // The letter itself expires, and a lapsed surety letter is worth as much as
  // no letter at all in a prequalification packet.
  if (!out.expires_on) out.letter_state = 'no_expiry_recorded';
  else {
    const left = daysBetween(today, out.expires_on);
    out.letter_days_left = left;
    out.letter_state = left === null ? 'no_expiry_recorded' : (left < 0 ? 'expired' : (left <= (num(input.warn_days) === null ? DEFAULT_WARN_DAYS : num(input.warn_days)) ? 'expiring' : 'current'));
  }
  if (!out.source) {
    out.problems.push('no source recorded for these limits -- a surety letter or the agent who issued it');
  }

  if (aggregate === null) {
    out.problems.push('no aggregate limit recorded -- remaining capacity cannot be worked out');
  } else if (backlog === null) {
    out.problems.push('no committed backlog supplied -- remaining capacity cannot be worked out');
  } else {
    const rem = money(aggregate - backlog);
    out.remaining_aggregate = rem;
    // Over the aggregate is reported, never clamped to zero: it is precisely
    // the condition a surety needs to hear about.
    out.over_aggregate = rem < 0 ? money(Math.abs(rem)) : 0;
    out.aggregate_used_pct = aggregate > 0 ? Math.round((backlog / aggregate) * 1000) / 10 : null;
  }

  if (candidate !== null) {
    const reasons = [];
    if (single === null) reasons.push('no single-project limit recorded');
    else if (candidate > single) reasons.push('above the single-project limit of ' + single);
    if (out.remaining_aggregate === null) reasons.push('remaining aggregate is unknown');
    // A negative remaining is already-exceeded, and saying "above the
    // remaining aggregate of -400000" is true but reads as gibberish in a
    // sentence about money. The two cases are worded apart.
    else if (out.remaining_aggregate < 0) reasons.push('the aggregate limit is already exceeded by ' + out.over_aggregate);
    else if (candidate > out.remaining_aggregate) reasons.push('above the remaining aggregate of ' + out.remaining_aggregate);
    if (out.letter_state === 'expired') reasons.push('the surety letter has expired');
    // 'unknown' is a real answer and is NOT 'within'. A contractor told a job
    // is bondable on a missing limit bids work it cannot bond.
    const unknowable = reasons.some(function (r) { return /no single-project limit|unknown/.test(r); });
    out.candidate = reasons.length === 0 ? 'within_capacity' : (unknowable ? 'cannot_tell' : 'over_capacity');
    out.candidate_reasons = reasons;
  }
  return out;
}

module.exports = {
  DEFAULT_WARN_DAYS,
  documentState,
  packetReadiness,
  bondingCapacity
};
