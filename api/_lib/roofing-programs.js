// api/_lib/roofing-programs.js
// SAIRNroofing Phase 4d -- manufacturer certification programmes, at COMPANY
// level. GAF Master Elite, Owens Corning Platinum Preferred, CertainTeed
// SELECT ShingleMaster and anything like them.
//
// PURE -- no I/O, no LLM.
//
// ── THESE ARE NOT REGULATIONS, AND THE APP MUST NEVER IMPLY THEY ARE ─────
// The v1 scope doc is explicit: "These are voluntary manufacturer programmes,
// not state mandates -- the app must not present them as regulatory." That is
// the opposite posture from Phase 3a (state licensing, where the law decides)
// and Phase 5 (statutory rescission). Nothing here produces a compliance
// verdict. It produces "against the requirements YOU entered, here is where
// you stand", which is a different sentence and has to keep reading like one.
//
// ── WHY NOTHING IS SEEDED (decision, 2026-08-25) ─────────────────────────
// The real programme terms sit behind manufacturer contractor portals. What is
// publicly reachable is contractor marketing pages -- consistent with each
// other and with the scope doc, and still SECONDARY. Michael's call, matching
// the Phase 5 notice-text decision: ship the mechanism, and let the contractor
// enter their own thresholds citing their own programme agreement. Nothing
// blog-sourced renders as a verdict. A roofer told "you qualify for Master
// Elite" on a third-hand number could act on it.
//
// So every requirement carries a `source` the contractor names, and a
// requirement with no source is reported as unusable rather than evaluated.
//
// ── TWO CLASSES OF REQUIREMENT, ONLY ONE COMPUTED ────────────────────────
// Deliberately the same split as the Phase 3c supplement engine, because it is
// the same honesty problem.
//
//   COMPUTED  -- derived from data this app actually holds. Exactly one family
//                today: what share of the roster holds a named credential. It
//                is real arithmetic over the Phase 3a rf_certifications store,
//                and it is the thing this app can answer that a spreadsheet
//                cannot. CertainTeed SELECT's "50% of employees hold Master
//                Craftsman" is this shape.
//   ATTESTED  -- a fact the contractor states: years in business, insurance
//                limits, customer-satisfaction score, product share, annual
//                volume. The app CANNOT verify any of these and does not
//                pretend to. Each needs a value, a date and a source, and one
//                missing any of those is 'unknown' -- never quietly 'met'.
//
// An attested requirement that is present and meets its threshold still counts
// toward the verdict, because refusing to use the contractor's own figures
// would make the feature useless. What the engine will not do is let the
// verdict READ as verified: every result reports how many of its requirements
// were self-reported.
//
// ── THE AMBIGUITY THE APP MUST NOT RESOLVE SILENTLY ──────────────────────
// "50% of employees" does not say WHICH employees -- everyone on the payroll,
// or the field crews. That materially changes the answer for a shop with an
// office staff, and picking one silently would be the app inventing a term of
// somebody else's contract. So the denominator is part of the requirement the
// contractor enters, and every computed result names the denominator it used.

'use strict';

// The company's standing in a programme. 'lapsed' is distinct from
// 'not_enrolled': having held it and lost it is a different fact, and it is
// the one that matters for the annual-renewal programmes.
const PROGRAM_STATUSES = ['not_enrolled', 'in_progress', 'held', 'lapsed'];

// The only requirement kinds this engine COMPUTES. Everything else is
// attested, and its `kind` is a free-text label the contractor chooses --
// inventing a closed taxonomy of business facts would be guessing at other
// companies' programme terms.
const COMPUTED_KINDS = ['employee_credential_share', 'employee_credential_count'];

// Which roster the share is measured against. Named, never assumed.
const DENOMINATORS = ['all_active', 'listed_roles'];

const DEFAULT_WARN_DAYS = 30;

function isDate(s) { return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s); }
// null/''/undefined are ABSENT, not zero. Number(null) is 0, so the naive
// version turned a requirement stored with `threshold: null` into a threshold
// of ZERO -- which every holding satisfies, so an unusable requirement would
// have reported 'met'. Not reachable through the panel (it omits an empty
// threshold rather than sending null) but reachable by a direct API write,
// which is exactly the caller that would do it. Same root cause as the
// billing bug found the same day.
function num(v) { if (v === null || v === undefined || v === '') return null; const n = Number(v); return (typeof n === 'number' && isFinite(n)) ? n : null; }
function str(v) { return typeof v === 'string' ? v.trim() : ''; }

function daysUntil(dateStr, today) {
  if (!isDate(dateStr) || !isDate(today)) return null;
  const a = Date.UTC(+dateStr.slice(0, 4), +dateStr.slice(5, 7) - 1, +dateStr.slice(8, 10));
  const b = Date.UTC(+today.slice(0, 4), +today.slice(5, 7) - 1, +today.slice(8, 10));
  return Math.round((a - b) / 86400000);
}

function validateProgram(payload) {
  const problems = [];
  if (!payload || typeof payload !== 'object') return ['no programme supplied'];
  if (!str(payload.id)) problems.push('program_id (payload.id) is required');
  if (!str(payload.manufacturer)) problems.push('manufacturer is required');
  if (!str(payload.program_name)) problems.push('program_name is required');
  if (payload.status !== undefined && PROGRAM_STATUSES.indexOf(payload.status) === -1) {
    problems.push('status must be one of: ' + PROGRAM_STATUSES.join(', '));
  }
  if (payload.requirements !== undefined && !Array.isArray(payload.requirements)) {
    problems.push('requirements must be an array');
  }
  return problems;
}

// Is a named credential current for this employee, as of `today`?
// A LAPSED credential does not count toward a share -- a programme that
// requires half the crew to hold a card means half the crew to hold a VALID
// one, and counting expired cards would inflate the number in the direction
// that makes a contractor think they qualify when they do not.
function holdsCurrentCredential(records, employeeId, credential, today) {
  const want = credential.toLowerCase();
  let held = false;
  (records || []).forEach(function (rec) {
    if (!rec || rec.employee_id !== employeeId) return;
    if (rec.record_type !== 'installer_cert') return;
    if (str(rec.credential).toLowerCase() !== want) return;
    if (rec.has_expiry === false) { held = true; return; }
    const d = daysUntil(rec.expires_on, today);
    if (d !== null && d >= 0) held = true;
  });
  return held;
}

// Evaluate one requirement. Never throws; an unusable requirement comes back
// as 'unusable' with a reason rather than silently not counting.
function evaluateRequirement(req, ctx) {
  const out = {
    req_id: str(req && req.req_id) || null,
    label: str(req && req.label) || str(req && req.req_id) || 'unnamed requirement',
    kind: str(req && req.kind) || null,
    basis: null, status: 'unknown', detail: '', source: str(req && req.source) || null
  };
  if (!req || typeof req !== 'object') { out.status = 'unusable'; out.detail = 'not a requirement'; return out; }
  if (!out.source) {
    // The whole point of the no-seed decision: a threshold with no stated
    // origin is somebody's guess, and the engine will not turn a guess into a
    // verdict.
    out.status = 'unusable';
    out.detail = 'no source named -- enter where this requirement comes from (your programme agreement) before it can be used';
    return out;
  }

  const isComputed = COMPUTED_KINDS.indexOf(out.kind) !== -1;
  out.basis = isComputed ? 'computed' : 'attested';

  if (isComputed) {
    const credential = str(req.credential);
    if (!credential) { out.status = 'unusable'; out.detail = 'a computed requirement must name the credential to count'; return out; }
    const denominator = DENOMINATORS.indexOf(req.denominator) !== -1 ? req.denominator : 'all_active';
    const roles = Array.isArray(req.roles) ? req.roles.map(str).filter(Boolean) : [];
    if (denominator === 'listed_roles' && !roles.length) {
      out.status = 'unusable'; out.detail = 'denominator is listed_roles but no roles were listed'; return out;
    }
    const pool = (ctx.roster || []).filter(function (e) {
      if (!e || e.active === false) return false;
      if (denominator === 'listed_roles') return roles.indexOf(e.role) !== -1;
      return true;
    });
    const holders = pool.filter(function (e) {
      return holdsCurrentCredential(ctx.certifications, e.employee_id, credential, ctx.today);
    });
    out.credential = credential;
    out.denominator = denominator;
    out.roles = denominator === 'listed_roles' ? roles : null;
    out.pool_size = pool.length;
    out.holders = holders.length;
    out.holder_ids = holders.map(function (e) { return e.employee_id; });

    const threshold = num(req.threshold);
    if (threshold === null) { out.status = 'unusable'; out.detail = 'threshold is not a number'; return out; }
    out.threshold = threshold;

    if (out.kind === 'employee_credential_count') {
      out.actual = holders.length;
      out.unit = 'people';
      out.status = holders.length >= threshold ? 'met' : 'not_met';
      out.detail = holders.length + ' of ' + pool.length + ' hold a current ' + credential + ' (need ' + threshold + ')';
      return out;
    }
    // share
    if (pool.length === 0) {
      // Zero over zero is not 100%. An empty pool cannot satisfy a share
      // requirement and must not read as if it did.
      out.status = 'unknown';
      out.actual = null;
      out.unit = '%';
      out.detail = 'no employees in the ' + (denominator === 'listed_roles' ? roles.join('/') : 'active') + ' pool -- a share cannot be computed';
      return out;
    }
    const pct = Math.round((holders.length / pool.length) * 1000) / 10;
    out.actual = pct;
    out.unit = '%';
    out.status = pct >= threshold ? 'met' : 'not_met';
    out.detail = holders.length + ' of ' + pool.length + ' (' + pct + '%) hold a current ' + credential + ' (need ' + threshold + '%)';
    return out;
  }

  // ── attested ──
  out.attested_on = str(req.attested_on) || null;
  out.attested_by = str(req.attested_by) || null;
  const value = req.attested_value;
  // NOTE: the emptiness test must not go through str(), which returns '' for
  // ANY non-string -- an attested value of 2000000 read as blank and every
  // numeric attestation came back 'unknown'. Caught by the suite below.
  if (value === undefined || value === null || (typeof value === 'string' && value.trim() === '')) {
    out.status = 'unknown';
    out.detail = 'nothing recorded yet -- this is a figure only you can supply';
    return out;
  }
  if (!out.attested_on) {
    out.status = 'unknown';
    out.detail = 'recorded without a date -- an insurance limit or a satisfaction score is only meaningful as of a date';
    return out;
  }
  out.attested_value = value;
  const threshold = num(req.threshold);
  const actual = num(value);
  if (threshold === null) {
    // A non-numeric requirement (a code of ethics, an exam passed). Present
    // and dated is all the engine can check, and it says exactly that.
    out.status = 'met';
    out.detail = 'recorded as "' + String(value) + '" on ' + out.attested_on + ' -- self-reported, not verified';
    return out;
  }
  if (actual === null) {
    out.status = 'unknown';
    out.detail = 'threshold is numeric but the recorded value "' + String(value) + '" is not';
    return out;
  }
  out.threshold = threshold;
  out.actual = actual;
  out.unit = str(req.unit) || null;
  out.status = actual >= threshold ? 'met' : 'not_met';
  out.detail = actual + (out.unit ? ' ' + out.unit : '') + ' recorded on ' + out.attested_on +
    ' against a threshold of ' + threshold + (out.unit ? ' ' + out.unit : '') + ' -- self-reported, not verified';
  return out;
}

// Evaluate one programme against the roster and the Phase 3a certification
// records.
//
//   program        : the stored programme row (contractor-entered)
//   roster         : [{ employee_id, role, active }]
//   certifications : rf_certifications records (latest-per-key already applied)
//   today          : 'YYYY-MM-DD'
function evaluateProgram(input) {
  input = input || {};
  const program = input.program || null;
  const today = isDate(input.today) ? input.today : null;
  const warnDays = typeof input.warn_days === 'number' ? input.warn_days : DEFAULT_WARN_DAYS;
  if (!program) return { ok: false, error: { code: 'NO_PROGRAM', message: 'no programme supplied' } };

  const ctx = {
    roster: input.roster || [],
    certifications: input.certifications || [],
    today: today
  };

  const requirements = (Array.isArray(program.requirements) ? program.requirements : [])
    .map(function (r) { return evaluateRequirement(r, ctx); });

  const notMet = requirements.filter(function (r) { return r.status === 'not_met'; });
  const unknown = requirements.filter(function (r) { return r.status === 'unknown'; });
  const unusable = requirements.filter(function (r) { return r.status === 'unusable'; });
  const attested = requirements.filter(function (r) { return r.basis === 'attested'; });
  const computed = requirements.filter(function (r) { return r.basis === 'computed'; });

  // The verdict vocabulary is deliberately not the word "eligible".
  //   no requirements       -> nothing to say
  //   any not met           -> requirements_not_met
  //   any unknown/unusable  -> incomplete   (NEVER "met" on missing data)
  //   otherwise             -> appears_met  (against what YOU entered)
  let verdict;
  if (!requirements.length) verdict = 'no_requirements_entered';
  else if (notMet.length) verdict = 'requirements_not_met';
  else if (unknown.length || unusable.length) verdict = 'incomplete';
  else verdict = 'appears_met';

  // Standing: the company's own record of holding the programme, and its
  // renewal clock. These programmes are recurring, not one-time badges -- an
  // annual continuing-education or re-inspection condition is the norm -- so a
  // held credential with a past expiry is surfaced as lapsed_by_date even when
  // the stored status still says 'held'.
  const standing = program.standing || {};
  const statusStored = PROGRAM_STATUSES.indexOf(standing.status) !== -1 ? standing.status : 'not_enrolled';
  let renewal = { status: 'not_applicable', days: null, expires_on: null };
  if (statusStored === 'held') {
    if (standing.has_expiry === false) {
      renewal = { status: 'no_expiry', days: null, expires_on: null };
    } else {
      const d = daysUntil(standing.expires_on, today);
      if (d === null) renewal = { status: 'unknown', days: null, expires_on: standing.expires_on || null };
      else if (d < 0) renewal = { status: 'lapsed_by_date', days: d, expires_on: standing.expires_on };
      else if (d <= warnDays) renewal = { status: 'expiring', days: d, expires_on: standing.expires_on };
      else renewal = { status: 'current', days: d, expires_on: standing.expires_on };
    }
  }

  return {
    ok: true,
    program_id: program.program_id || null,
    manufacturer: program.manufacturer || null,
    program_name: program.program_name || null,
    standing: { status: statusStored, obtained_on: standing.obtained_on || null },
    renewal: renewal,
    requirements: requirements,
    verdict: verdict,
    totals: {
      total: requirements.length,
      met: requirements.filter(function (r) { return r.status === 'met'; }).length,
      not_met: notMet.length,
      unknown: unknown.length,
      unusable: unusable.length,
      computed: computed.length,
      attested: attested.length
    },
    // Carried on EVERY result, not only the good ones. This is a voluntary
    // programme evaluated against numbers the contractor typed in; the moment
    // that stops being said out loud, the verdict starts reading like a
    // certification the app is issuing.
    disclosures: {
      not_regulatory: 'A manufacturer programme is voluntary and commercial. This is not a licensing or compliance status.',
      thresholds_are_yours: 'Requirements and thresholds here were entered by you from your own programme agreement. They are not verified against ' + (program.manufacturer || 'the manufacturer') + '.',
      self_reported_count: attested.length,
      computed_count: computed.length,
      verified_by_app: computed.length > 0
        ? computed.length + ' requirement(s) computed from your own certification records; ' + attested.length + ' self-reported'
        : 'every requirement here is self-reported -- the app verified none of them'
    }
  };
}

module.exports = {
  PROGRAM_STATUSES,
  COMPUTED_KINDS,
  DENOMINATORS,
  DEFAULT_WARN_DAYS,
  validateProgram,
  holdsCurrentCredential,
  evaluateRequirement,
  evaluateProgram
};
