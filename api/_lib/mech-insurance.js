// api/_lib/mech-insurance.js
// SAIRNmechanical -- the BUSINESS's own insurance position and its COI packet.
//
// PURE -- no I/O, no LLM, no clock.
//
// ── WHY THIS EXISTS AND WHAT IT IS NOT A DUPLICATE OF ─────────────────────
// Measured before a line was written, because this platform has twice nearly
// rebuilt something it already had: `grep -ci "insurance|certificate of
// insurance|general liability|workers comp|umbrella|COI" sairnmechanical.html`
// returns **0**. There is no insurance concept in this app at all.
//
// What DOES exist is api/_lib/mech-credentials.js, and it faces the other way:
// it tracks what an EMPLOYEE holds -- an EPA 608 card, a NATE certificate, a
// state licence -- and answers "who can I dispatch". This file tracks what the
// COMPANY holds, and answers "may this company be on that site at all". A
// technician with a current 608 card working for a business whose general
// liability lapsed last month is dispatchable under one engine and refused at
// the gate by the other, and neither answer is the other's.
//
// ── MODELLED ON WHAT IS ALREADY HERE, NOT DESIGNED FRESH ──────────────────
// api/_lib/roofing-prequal.js is the closest existing shape and this file
// deliberately reuses its structure and its two hardest rules:
//
//   * NO DEFAULT REQUIREMENT LIST. roofing-prequal's packetReadiness takes
//     `required_kinds` from the caller because "every GC's prequalification
//     form differs and shipping a guess would tell a contractor they are ready
//     when they are not". Insurance requirements differ MORE, not less: a
//     hospital, a school district and a homeowner ask for different limits and
//     different endorsements. So `requirements` is always supplied and this
//     file seeds none.
//   * NO EXPIRY IS NOT "FINE". A policy with no expiry recorded is
//     `no_expiry_recorded`, never `current`. A certificate holder asking for
//     proof of current coverage is asking a question that record cannot answer.
//
// api/_lib/roofing-credentials.js contributes the third: FAIL CLOSED on an
// unseeded input rather than borrowing another one's answer.
//
// ── THE LIMITS COMPARISON IS A MONEY COMPARISON, AND IT IS IN CENTS ───────
// This is the part with teeth. `2000000.00 >= 2000000.00` is the kind of
// comparison that has already gone wrong on this platform in IEEE754 -- the
// dnt-rollup finding, money summed as doubles at the cell and re-summed as
// doubles at the rollup. Limits arrive as dollars from a certificate and are
// converted to integer cents ONCE, at the boundary, and every comparison after
// that is integer. A limit is met when `have_cents >= need_cents`, exactly.
//
// ── AND AN UNRECORDED LIMIT IS NOT A ZERO AND NOT A PASS ──────────────────
// The rule this file exists to keep, and it is the same one mech-assets.js
// keeps about an unweighed unit. A policy whose each-occurrence limit nobody
// typed in is `unknown_limit` -- NOT $0 (which would fail every requirement and
// train people to ignore the board) and NOT satisfied (which would tell a
// contractor they meet a limit nobody has evidence of). Unknown is its own
// answer and it is counted separately.
//
// ── WHAT THIS DOES NOT DO, STATED SO NOBODY READS IT AS MORE ──────────────
// It does not gate anything. Nothing here refuses a dispatch or a bid, for the
// same reason sairnmechanical.html's dispatch-eligibility card states: this app
// has no job record that says what a job requires, so the requirement is ASKED
// FOR rather than inferred. Gating on the answer is a product decision and is
// deliberately not taken here.
//
// It also does not read a certificate. ACORD 25 parsing, additional-insured
// wording interpretation and "is this endorsement the one the owner meant" are
// judgements this engine refuses in the same way roofing-prequal refuses to
// judge an EMR: the contractor records what the certificate says, and the
// engine compares it to what was asked for.

'use strict';

const isDate = require('./calendar-date').isCalendarDate;

// A review window, not a rule. Callers override it.
const DEFAULT_WARN_DAYS = 30;

// The coverages a mechanical contractor is actually asked for. An unknown kind
// is REFUSED on evaluation rather than stored through, exactly as
// mech-assets.js refuses an unknown asset type: a board that can group by a
// category nobody defined is a board with a silent bucket in it.
const POLICY_KINDS = {
  general_liability: true,
  workers_comp: true,
  commercial_auto: true,
  umbrella: true,          // or excess
  professional: true,      // E&O, design-build exposure
  pollution: true,         // refrigerant release, fuel oil
  installation_floater: true,
  builders_risk: true
};

// Endorsements a certificate holder asks for by name. Tracked as recorded
// booleans, never inferred from the presence of a policy.
const ENDORSEMENTS = {
  additional_insured: true,
  waiver_of_subrogation: true,
  primary_noncontributory: true,
  per_project_aggregate: true
};

function str(v) { return typeof v === 'string' ? v.trim() : ''; }

// Dollars -> integer cents, ONCE, at the boundary. null stays null: see the
// unknown-limit rule in the header. A negative or non-finite figure is null
// too -- it is not a limit, and treating it as 0 would fail a requirement for
// a reason the contractor cannot see.
function cents(v) {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  if (!Number.isFinite(n) || n < 0) return null;
  return Math.round(n * 100);
}
function dollars(c) { return c === null ? null : Math.round(c) / 100; }

function daysBetween(fromISO, toISO) {
  if (!isDate(fromISO) || !isDate(toISO)) return null;
  const a = Date.UTC(+fromISO.slice(0, 4), +fromISO.slice(5, 7) - 1, +fromISO.slice(8, 10));
  const b = Date.UTC(+toISO.slice(0, 4), +toISO.slice(5, 7) - 1, +toISO.slice(8, 10));
  return Math.round((b - a) / 86400000);
}

function refuse(code, message) {
  return { ok: false, error: { code: code, message: message } };
}

// ── ONE POLICY'S STATE ────────────────────────────────────────────────────
// Five states, and the two that are not current/expiring/expired are the ones
// that matter: `no_expiry_recorded` and an unknown kind.
function policyState(input) {
  input = input || {};
  const today = isDate(input.today) ? input.today : null;
  if (!today) {
    return refuse('NO_TODAY', 'today (YYYY-MM-DD) is required -- this engine will not assume a clock');
  }
  const p = input.policy;
  if (!p || typeof p !== 'object') return refuse('NO_POLICY', 'no policy supplied');
  const kind = str(p.kind);
  if (!kind) return refuse('NO_KIND', 'a policy with no kind cannot be matched to a requirement');
  if (!POLICY_KINDS[kind]) {
    return refuse('UNKNOWN_KIND', 'unknown policy kind ' + JSON.stringify(kind)
      + ' -- it is refused rather than stored, because a board that groups by a '
      + 'category nobody defined has a silent bucket in it');
  }
  const warn = Number.isFinite(Number(input.warn_days)) && input.warn_days !== ''
    && input.warn_days !== null ? Number(input.warn_days) : DEFAULT_WARN_DAYS;

  const each = cents(p.each_occurrence);
  const agg = cents(p.aggregate);
  const out = {
    ok: true,
    policy_id: str(p.policy_id) || null,
    kind: kind,
    carrier: str(p.carrier) || null,
    policy_no: str(p.policy_no) || null,
    effective_on: isDate(p.effective_on) ? p.effective_on : null,
    expires_on: isDate(p.expires_on) ? p.expires_on : null,
    certificate_holder: str(p.certificate_holder) || null,
    each_occurrence_cents: each,
    aggregate_cents: agg,
    each_occurrence: dollars(each),
    aggregate: dollars(agg),
    endorsements: {},
    state: 'unknown',
    days_left: null,
    problems: []
  };
  // Endorsements are RECORDED booleans. Absent is absent -- never inferred
  // from the policy existing, which is how a contractor ends up telling an
  // owner they have additional-insured status they were never granted.
  Object.keys(ENDORSEMENTS).forEach(function (e) {
    out.endorsements[e] = (p.endorsements && typeof p.endorsements[e] === 'boolean')
      ? p.endorsements[e] : null;
  });

  if (!out.expires_on) {
    out.state = 'no_expiry_recorded';
    out.problems.push('no expiry recorded -- a certificate holder asking for proof of '
      + 'current coverage is asking a question this record cannot answer');
  } else {
    const left = daysBetween(today, out.expires_on);
    out.days_left = left;
    if (left === null) out.state = 'no_expiry_recorded';
    else if (left < 0) out.state = 'expired';
    else if (left <= warn) out.state = 'expiring';
    else out.state = 'current';
  }
  if (out.effective_on && out.expires_on
      && daysBetween(out.effective_on, out.expires_on) < 0) {
    out.problems.push('the expiry is before the effective date -- one of the two was mistyped');
  }
  if (each === null) {
    out.problems.push('no each-occurrence limit recorded -- this is NOT a limit of zero '
      + 'and it does NOT satisfy a requirement; nobody has typed what the certificate says');
  }
  return out;
}

// ── DOES THE POSITION MEET WHAT THIS CUSTOMER ASKED FOR? ──────────────────
// `requirements` is ALWAYS the caller's. There is no default list and there
// will not be one: a hospital, a school district and a homeowner ask for
// different limits and different endorsements, and a seeded list would tell a
// contractor they are covered for a job they are not.
//
// Each requirement: { kind, each_occurrence?, aggregate?, endorsements?: [] }
function coverageReadiness(input) {
  input = input || {};
  const today = isDate(input.today) ? input.today : null;
  if (!today) {
    return refuse('NO_TODAY', 'today (YYYY-MM-DD) is required -- this engine will not assume a clock');
  }
  const reqs = Array.isArray(input.requirements) ? input.requirements : null;
  if (!reqs || !reqs.length) {
    return refuse('NO_REQUIREMENTS', 'say what this certificate holder asked for. There '
      + 'is no default insurance requirement in this engine and there will not be one -- '
      + 'a seeded list would tell a contractor they are covered for a job they are not');
  }
  const warn = input.warn_days;
  const states = [];
  for (const p of (Array.isArray(input.policies) ? input.policies : [])) {
    const s = policyState({ today: today, policy: p, warn_days: warn });
    // An unusable policy is REPORTED, never dropped. A silently skipped policy
    // is a requirement that reads as unmet for a reason nobody can see.
    if (!s.ok) {
      states.push({ ok: false, kind: (p && str(p.kind)) || null, error: s.error });
    } else {
      states.push(s);
    }
  }

  const lines = reqs.map(function (r) {
    const kind = str(r && r.kind);
    const line = {
      kind: kind || null,
      met: false,
      state: 'missing',
      reasons: [],
      policy_id: null,
      each_occurrence_required: dollars(cents(r && r.each_occurrence)),
      aggregate_required: dollars(cents(r && r.aggregate))
    };
    if (!kind || !POLICY_KINDS[kind]) {
      line.state = 'unknown_requirement';
      line.reasons.push('this engine does not model a coverage called '
        + JSON.stringify(kind || '') + ', so it is NOT reporting that you meet it');
      return line;
    }
    // Among policies of the right kind, the one that expires LAST is the one a
    // certificate holder would be shown. Not the newest record -- a renewal
    // entered before an endorsement correction would otherwise win.
    const candidates = states.filter(function (s) { return s.ok && s.kind === kind; });
    if (!candidates.length) {
      line.reasons.push('no ' + kind + ' policy is recorded at all');
      return line;
    }
    candidates.sort(function (a, b) {
      if (!a.expires_on) return 1;
      if (!b.expires_on) return -1;
      return a.expires_on < b.expires_on ? 1 : (a.expires_on > b.expires_on ? -1 : 0);
    });
    const best = candidates[0];
    line.policy_id = best.policy_id;
    line.state = best.state;
    line.expires_on = best.expires_on;
    line.days_left = best.days_left;

    if (best.state === 'expired') {
      line.reasons.push('the recorded ' + kind + ' policy expired on ' + best.expires_on);
    } else if (best.state === 'no_expiry_recorded') {
      line.reasons.push('the recorded ' + kind + ' policy has no expiry, so it cannot be '
        + 'shown as current -- this is not a finding that it lapsed');
    }

    // THE MONEY COMPARISON, IN INTEGER CENTS. See the header.
    const needEach = cents(r.each_occurrence);
    if (needEach !== null) {
      if (best.each_occurrence_cents === null) {
        line.reasons.push('an each-occurrence limit of ' + dollars(needEach)
          + ' was asked for and none is recorded -- UNKNOWN, not met and not zero');
      } else if (best.each_occurrence_cents < needEach) {
        line.reasons.push('each occurrence is ' + best.each_occurrence
          + ' and ' + dollars(needEach) + ' was asked for');
      }
    }
    const needAgg = cents(r.aggregate);
    if (needAgg !== null) {
      if (best.aggregate_cents === null) {
        line.reasons.push('an aggregate limit of ' + dollars(needAgg)
          + ' was asked for and none is recorded -- UNKNOWN, not met and not zero');
      } else if (best.aggregate_cents < needAgg) {
        line.reasons.push('the aggregate is ' + best.aggregate
          + ' and ' + dollars(needAgg) + ' was asked for');
      }
    }
    // Endorsements: only a recorded TRUE satisfies. null is unknown and false
    // is a real no, and neither is a pass.
    for (const e of (Array.isArray(r.endorsements) ? r.endorsements : [])) {
      const name = str(e);
      if (!ENDORSEMENTS[name]) {
        line.reasons.push('this engine does not model an endorsement called '
          + JSON.stringify(name) + ', so it is NOT reporting that you carry it');
        continue;
      }
      if (best.endorsements[name] === true) continue;
      line.reasons.push(best.endorsements[name] === false
        ? name + ' is recorded as NOT carried'
        : name + ' has not been recorded either way -- unknown, and unknown is not carried');
    }

    line.met = line.reasons.length === 0
      && (best.state === 'current' || best.state === 'expiring');
    return line;
  });

  const unusable = states.filter(function (s) { return !s.ok; });
  return {
    ok: true,
    today: today,
    ready: lines.every(function (l) { return l.met; }) && unusable.length === 0,
    lines: lines,
    // Surfaced beside the verdict, never under it -- a packet that is "ready"
    // while two recorded policies could not be evaluated is not ready.
    unusable_policies: unusable,
    counts: {
      required: lines.length,
      met: lines.filter(function (l) { return l.met; }).length,
      expired: lines.filter(function (l) { return l.state === 'expired'; }).length,
      expiring: lines.filter(function (l) { return l.state === 'expiring'; }).length,
      missing: lines.filter(function (l) { return l.state === 'missing'; }).length,
      no_expiry_recorded: lines.filter(function (l) { return l.state === 'no_expiry_recorded'; }).length
    },
    // SAID IN THE PAYLOAD. This engine compares what was recorded against what
    // was asked for; it does not gate, and it does not read a certificate.
    not_asserted: 'this engine gates nothing and parses no certificate -- it compares '
      + 'what the contractor recorded against what the certificate holder asked for'
  };
}

// ── THE BOARD: every policy, with its state, and the unknowns surfaced ────
function evaluateCoverage(policies, today, opts) {
  if (!isDate(today)) return refuse('BAD_TODAY', 'today must be YYYY-MM-DD');
  const o = opts || {};
  const rows = [], unusable = [];
  for (const p of (Array.isArray(policies) ? policies : [])) {
    const s = policyState({ today: today, policy: p, warn_days: o.warn_days });
    if (s.ok) rows.push(s);
    else unusable.push({ kind: (p && str(p.kind)) || null, error: s.error });
  }
  const counts = { current: 0, expiring: 0, expired: 0, no_expiry_recorded: 0, unknown: 0 };
  rows.forEach(function (r) { counts[r.state] = (counts[r.state] || 0) + 1; });
  const byKind = {};
  rows.forEach(function (r) { byKind[r.kind] = (byKind[r.kind] || 0) + 1; });
  return {
    ok: true,
    today: today,
    warn_days: Number.isFinite(Number(o.warn_days)) && o.warn_days !== null
      && o.warn_days !== '' ? Number(o.warn_days) : DEFAULT_WARN_DAYS,
    counts: counts,
    by_kind: byKind,
    // Beside the totals, not inside them -- a board that buries its unknowns
    // reads as a clean bill.
    no_limit_recorded_count: rows.filter(function (r) {
      return r.each_occurrence_cents === null;
    }).length,
    unusable_policies: unusable,
    rows: rows
  };
}

module.exports = {
  DEFAULT_WARN_DAYS,
  POLICY_KINDS,
  ENDORSEMENTS,
  cents,
  dollars,
  policyState,
  coverageReadiness,
  evaluateCoverage
};
