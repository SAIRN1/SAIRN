// api/_lib/roofing-warranties.js
// SAIRNroofing gap A1 -- manufacturer warranty registration, and the
// certification gate on which warranty tiers a contractor may offer.
//
// PURE -- no I/O, no LLM.
//
// ── WHY THIS EXISTS ──────────────────────────────────────────────────────
// The 2026-08-26 worldwide competitive-gap audit names this Tier-A item A1 and
// records ZERO occurrences of "warranty" anywhere in sairnroofing.html --
// re-verified 2026-09-02, still zero across the panel, the resource registry
// and the endpoint. The forcing function is real and contractual: enhanced and
// extended manufacturer warranties are gated behind the contractor's own
// certification standing, and they are LOST if the roof is not registered with
// the manufacturer inside a deadline measured from the installation date.
//
// ── THE SAME POSTURE AS roofing-programs.js, AND FOR THE SAME REASON ─────
// That file's 2026-08-25 decision: real programme terms sit behind manufacturer
// contractor portals, what is publicly reachable is marketing copy, and a
// roofer told "you qualify for the Golden Pledge" on a third-hand number could
// act on it. So NOTHING HERE IS SEEDED. No GAF tier list, no CertainTeed
// mapping, no registration windows. Every tier, every programme requirement and
// every registration deadline is entered by the contractor from their own
// programme agreement and carries the `source` they name.
//
// A tier with no source is reported as unusable rather than evaluated, and a
// deadline nobody stated produces 'no_deadline_stated' -- never a guessed 30
// days. Thirty days is the number the marketing pages repeat; it is also wrong
// for some products, and being wrong here costs the homeowner the coverage.
//
// ── THE PART THAT IS ACTUALLY COMPUTABLE ─────────────────────────────────
// The registration clock. Given an installation date and a deadline the
// contractor states, the app can say "this roof loses its enhanced coverage in
// six days" -- a real obligation with a real expiry, the same shape as the
// Phase 3a credential board. That is the half of A1 worth building; the tier
// gate is the half that keeps it honest.
//
// ── IT WILL NOT ASSUME A CLOCK ───────────────────────────────────────────
// Every entry point requires a caller-supplied `today`. Same rule as
// api/_lib/subcontractor-compliance.js, and for the same reason: a UTC server
// clock answers a local-date question wrong for several hours of every day, and
// a deadline computed in the wrong timezone is exactly the failure this feature
// exists to prevent.

'use strict';

// A registration deadline is "due soon" this many days out. A REVIEW WINDOW,
// not a manufacturer term -- callers override it. Named so nobody reads it as
// a warranty condition.
const DEFAULT_WARN_DAYS = 30;

// Where a warranty stands with the manufacturer. 'not_registered' and
// 'registration_rejected' are deliberately different: never sent and sent-and-
// refused need opposite actions, and collapsing them loses the second entirely.
const WARRANTY_STATUSES = ['not_registered', 'submitted', 'registered', 'registration_rejected', 'void'];

function isDate(s) { return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s); }
function str(v) { return typeof v === 'string' ? v.trim() : ''; }
function whole(v) {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  return (typeof n === 'number' && isFinite(n) && Math.floor(n) === n) ? n : null;
}
function addDays(dateISO, n) {
  const t = Date.parse(dateISO + 'T00:00:00Z');
  if (!isFinite(t)) return null;
  return new Date(t + n * 86400000).toISOString().slice(0, 10);
}
function daysBetween(fromISO, toISO) {
  const a = Date.parse(fromISO + 'T00:00:00Z');
  const b = Date.parse(toISO + 'T00:00:00Z');
  if (!isFinite(a) || !isFinite(b)) return null;
  return Math.round((b - a) / 86400000);
}

// ── Which tiers can this contractor currently offer? ─────────────────────
// A tier names one of the contractor's OWN rf_company_programs rows. The gate
// is the programme's live standing, not its stored status alone: a programme
// recorded as 'held' whose expiry has passed is treated as lapsed, the same
// correction roofing-programs.js already makes with lapsed_by_date. A stored
// status is what someone last typed; the date is what is true.
//
// Four outcomes and they are not collapsible:
//   available   -- the gating programme is held and current
//   unavailable -- the programme exists and does not currently qualify
//   unrestricted-- the tier names no programme at all (a standard warranty
//                  every installer may offer); offerable, and says why
//   unusable    -- the tier names a programme that is not on file, or carries
//                  no source. NEVER 'available': a typo in a programme id must
//                  not read as permission to sell a warranty.
function tierAvailability(input) {
  input = input || {};
  const today = isDate(input.today) ? input.today : null;
  if (!today) {
    return { ok: false, error: { code: 'NO_TODAY', message: 'today (YYYY-MM-DD) is required -- this engine will not assume a clock' } };
  }
  const warnDays = whole(input.warn_days) === null ? DEFAULT_WARN_DAYS : whole(input.warn_days);
  const tiers = Array.isArray(input.tiers) ? input.tiers : [];
  const programs = Array.isArray(input.programs) ? input.programs : [];

  const byId = {};
  programs.forEach(function (p) { if (p && p.program_id) byId[p.program_id] = p; });

  const evaluated = tiers.map(function (t) {
    t = t || {};
    const out = {
      tier_id: str(t.tier_id) || null,
      manufacturer: str(t.manufacturer) || null,
      tier_name: str(t.tier_name) || null,
      requires_program_id: str(t.requires_program_id) || null,
      source: str(t.source) || null,
      // Carried through so the UI can say "the contractor stated this", never
      // "the manufacturer requires this".
      self_reported: true
    };
    if (!out.tier_id || !out.tier_name) {
      out.availability = 'unusable';
      out.reason = 'the tier has no id or no name';
      return out;
    }
    if (!out.source) {
      // Same rule as a requirement with no source in roofing-programs.js. A
      // warranty tier is a term of somebody else's contract; unsourced, this
      // app has no business ruling on it.
      out.availability = 'unusable';
      out.reason = 'no source named -- enter where this tier and its condition come from in your programme agreement';
      return out;
    }
    if (!out.requires_program_id) {
      out.availability = 'unrestricted';
      out.reason = 'no certification condition recorded for this tier';
      return out;
    }
    const p = byId[out.requires_program_id];
    if (!p) {
      out.availability = 'unusable';
      out.reason = 'requires programme "' + out.requires_program_id + '", which is not on file';
      return out;
    }
    out.program_name = str(p.program_name) || null;
    if (p.status !== 'held') {
      out.availability = 'unavailable';
      out.reason = 'programme "' + (out.program_name || out.requires_program_id) + '" is ' + (str(p.status) || 'not recorded');
      return out;
    }
    if (p.has_expiry === false) {
      out.availability = 'available';
      out.reason = 'programme held, no expiry recorded';
      return out;
    }
    const d = isDate(p.expires_on) ? daysBetween(today, p.expires_on) : null;
    if (d === null) {
      // Held, expiry expected, none readable. Not a pass: the whole point of
      // the gate is that standing lapses.
      out.availability = 'unusable';
      out.reason = 'programme "' + (out.program_name || out.requires_program_id) + '" is held but has no readable expiry date';
      return out;
    }
    out.program_expires_on = p.expires_on;
    out.program_days_left = d;
    if (d < 0) {
      out.availability = 'unavailable';
      out.reason = 'programme "' + (out.program_name || out.requires_program_id) + '" lapsed ' + Math.abs(d) + ' days ago';
    } else {
      out.availability = 'available';
      out.reason = d <= warnDays
        ? 'programme held, expires in ' + d + ' days'
        : 'programme held and current';
    }
    return out;
  });

  return {
    ok: true,
    today: today,
    tiers: evaluated,
    available: evaluated.filter(function (t) { return t.availability === 'available' || t.availability === 'unrestricted'; })
      .map(function (t) { return t.tier_id; }),
    // Surfaced separately rather than lumped in with 'unavailable', because
    // one is "you do not qualify" and the other is "your own data is wrong".
    unusable: evaluated.filter(function (t) { return t.availability === 'unusable'; })
      .map(function (t) { return t.tier_id || '(unnamed tier)'; })
  };
}

// ── The registration clock ───────────────────────────────────────────────
// The computable half of A1. `register_within_days` is the contractor's own
// figure from their own programme agreement; absent, this returns
// 'no_deadline_stated' and NOT a guessed window.
function registrationState(input) {
  input = input || {};
  const today = isDate(input.today) ? input.today : null;
  if (!today) {
    return { ok: false, error: { code: 'NO_TODAY', message: 'today (YYYY-MM-DD) is required -- this engine will not assume a clock' } };
  }
  const w = input.warranty || {};
  const warnDays = whole(input.warn_days) === null ? DEFAULT_WARN_DAYS : whole(input.warn_days);
  const status = WARRANTY_STATUSES.indexOf(w.status) === -1 ? null : w.status;
  const out = {
    ok: true,
    status: status,
    problems: status === null && w.status !== undefined
      ? ['unrecognised warranty status "' + String(w.status) + '"']
      : [],
    installed_on: isDate(w.installed_on) ? w.installed_on : null,
    registered_on: isDate(w.registered_on) ? w.registered_on : null,
    deadline_on: null,
    days_left: null,
    registration: 'unknown'
  };

  if (status === 'registered') {
    // Already done. Whether it was done LATE is still worth saying -- it is
    // the difference between a clean file and a claim the manufacturer may
    // refuse later -- so the deadline is still computed below where possible.
    out.registration = 'registered';
  } else if (status === 'void') {
    out.registration = 'void';
    return out;
  }

  const days = whole(w.register_within_days);
  if (!out.installed_on) {
    if (out.registration !== 'registered') out.registration = 'no_install_date';
    return out;
  }
  if (days === null || days < 0) {
    if (out.registration !== 'registered') out.registration = 'no_deadline_stated';
    return out;
  }
  out.deadline_on = addDays(out.installed_on, days);
  if (!out.deadline_on) {
    if (out.registration !== 'registered') out.registration = 'no_deadline_stated';
    return out;
  }

  if (out.registration === 'registered') {
    // Late registration is reported, not hidden. It does not un-register the
    // warranty and this function does not pretend it does.
    if (out.registered_on) {
      const late = daysBetween(out.deadline_on, out.registered_on);
      if (late !== null && late > 0) {
        out.registered_late_by = late;
        out.problems.push('registered ' + late + ' days after the stated deadline');
      }
    }
    return out;
  }

  const left = daysBetween(today, out.deadline_on);
  out.days_left = left;
  if (left === null) out.registration = 'no_deadline_stated';
  else if (left < 0) out.registration = 'overdue';
  else if (left <= warnDays) out.registration = 'due_soon';
  else out.registration = 'open';
  return out;
}

// ── Coverage ─────────────────────────────────────────────────────────────
// Either an explicit end date or a term in years from installation. If both
// are present the EXPLICIT DATE WINS and the disagreement is reported, because
// a manufacturer's certificate is the authority and a term is our arithmetic.
function coverageState(input) {
  input = input || {};
  const today = isDate(input.today) ? input.today : null;
  if (!today) {
    return { ok: false, error: { code: 'NO_TODAY', message: 'today (YYYY-MM-DD) is required -- this engine will not assume a clock' } };
  }
  const w = input.warranty || {};
  const out = { ok: true, expires_on: null, basis: 'none', years: whole(w.coverage_years), problems: [] };
  const stated = isDate(w.coverage_expires_on) ? w.coverage_expires_on : null;
  let derived = null;
  if (out.years !== null && out.years > 0 && isDate(w.installed_on)) {
    const d = new Date(Date.parse(w.installed_on + 'T00:00:00Z'));
    d.setUTCFullYear(d.getUTCFullYear() + out.years);
    derived = d.toISOString().slice(0, 10);
  }
  if (stated) {
    out.expires_on = stated;
    out.basis = 'stated';
    if (derived && derived !== stated) {
      out.problems.push('the certificate date (' + stated + ') and the ' + out.years + '-year term from installation (' + derived + ') disagree');
    }
  } else if (derived) {
    out.expires_on = derived;
    out.basis = 'derived_from_term';
  } else {
    return out;
  }
  const left = daysBetween(today, out.expires_on);
  out.days_left = left;
  out.state = left === null ? 'unknown' : (left < 0 ? 'expired' : 'active');
  return out;
}

// ── One warranty, whole ──────────────────────────────────────────────────
function evaluateWarranty(input) {
  input = input || {};
  const today = isDate(input.today) ? input.today : null;
  if (!today) {
    return { ok: false, error: { code: 'NO_TODAY', message: 'today (YYYY-MM-DD) is required -- this engine will not assume a clock' } };
  }
  const w = input.warranty || null;
  if (!w) return { ok: false, error: { code: 'NO_WARRANTY', message: 'no warranty supplied' } };

  const reg = registrationState({ warranty: w, today: today, warn_days: input.warn_days });
  const cov = coverageState({ warranty: w, today: today });

  return {
    ok: true,
    warranty_id: str(w.warranty_id) || null,
    job_id: str(w.job_id) || null,
    manufacturer: str(w.manufacturer) || null,
    tier_id: str(w.tier_id) || null,
    tier_name: str(w.tier_name) || null,
    registration_number: str(w.registration_number) || null,
    registration: reg,
    coverage: cov,
    // Everything that needs a human. Deliberately one list: a screen that has
    // to check four fields to find out whether anything is wrong grows a bug
    // the first time a fifth is added.
    problems: reg.problems.concat(cov.problems)
  };
}

module.exports = {
  DEFAULT_WARN_DAYS,
  WARRANTY_STATUSES,
  tierAvailability,
  registrationState,
  coverageState,
  evaluateWarranty
};
