// api/_lib/mech-credentials.js
// SAIRNmechanical -- technician credential registry, expiry, and DISPATCH
// ELIGIBILITY.
//
// PURE -- no I/O. Same shape as api/_lib/roofing-credentials.js and
// api/_lib/dental-credentials.js.
//
// ── WHY THIS IS THE FIRST DATA MODULE THIS APP HAS ──────────────────────────
// docs/superpowers/specs/2026-08-27-sairnmechanical-shared-platform-competitive-research.md
// §9d ranks "Credential registry + expiry + dispatch eligibility (A1 -> A6)"
// FIRST of ten capabilities: "Nothing else can be gated correctly until this
// exists." Verified against the app before building rather than taken on
// faith -- sairnmechanical.html's Technicians page is an honest empty state
// ("Technician certification tracking is not live yet"), its "+ Add Tech"
// button has no handler, there is no api/_resources/sairnmechanical.js, and
// the string `sairnmechanical` appears ZERO times in api/sd-data.js. The app
// has real per-employee auth (api/mech-auth.js, complete with the
// deactivation lifecycle) and no data layer at all. This is the first.
//
// ── THE FOURTH COPY, AND THE EXTRACTION CONDITION IS NOW MET ────────────────
// daysUntil / classifyRecord / latestByKey are near-identical here, in
// roofing-credentials.js and in dental-credentials.js. roofing-credentials.js
// names that cost in its own header and defers the extraction explicitly:
// "Revisit the extraction after 3c, when both shapes have stopped moving."
// Roofing 3c has shipped. So the stated condition has been met and this file
// is the evidence that it is now three engines, not two.
//
// It is STILL not extracted here, deliberately: the request was to build
// SAIRNmechanical's highest-value gap, an extraction touches two live apps
// mid-session, and every changed line should trace to the request. Recorded so
// the next person inherits the trigger rather than rediscovering the
// duplication.
//
// ── WHAT IS GENUINELY DIFFERENT ABOUT MECHANICAL ────────────────────────────
// EPA 608 is SECTIONED, and the sections are not a hierarchy of quality --
// they are a hierarchy of EQUIPMENT. Type I is small appliances, Type II
// high-pressure, Type III low-pressure, Universal all three. A Type I tech is
// not "less certified" than a Type II tech; they are certified for different
// machines. Dispatching on "has EPA 608" is therefore WRONG, and getting that
// wrong is how a technician is sent to a chiller they may not legally open.
// This module matches on the SECTION the job needs.
//
// EPA 608 certification does not expire (40 CFR 82.161 -- certification is for
// life). NATE certifications DO, on a two-year cycle. State HVAC, plumbing and
// electrical licences do, on state-specific cycles. So `has_expiry` is carried
// per record, exactly as roofing does it, and for the same reason: a missing
// expiry date on a record that SHOULD have one is `unknown`, while a record
// that genuinely has none is `current`. Collapsing those two would report a
// lifetime EPA card as incomplete data.
//
// ── ELIGIBILITY REFUSES; IT DOES NOT GUESS ─────────────────────────────────
// The rule this whole module exists to keep: a technician is eligible ONLY on
// evidence. Missing credential -> not eligible. Expired -> not eligible.
// Present but with an unknown expiry -> NOT ELIGIBLE, and the reason says
// "unknown", not "expired" and not "ok". A dispatch board that answers
// "probably fine" is worse than one that answers nothing, because somebody
// acts on it.

'use strict';

// Platform-standard "expiring soon" window -- sairncare.html, sairnbuild.html,
// api/_lib/dental-credentials.js and api/_lib/roofing-credentials.js all use 30.
const DEFAULT_WARN_DAYS = 30;

// What a credential record may be. Unknown types are REFUSED on write rather
// than stored, so the eligibility engine can never be asked about a kind of
// credential nobody has defined the meaning of.
const RECORD_TYPES = {
  epa_608: true,          // federal refrigerant handling, sectioned, no expiry
  nate: true,             // NATE specialty certification, 2-year cycle
  state_license: true,    // state HVAC / plumbing / electrical licence
  manufacturer: true,     // OEM training (Carrier, Trane, Daikin ...)
  safety_training: true,  // OSHA 10/30, confined space, lockout-tagout
  medical_gas: true,      // ASSE 6010/6040 -- medical gas piping
  backflow: true          // backflow prevention tester certification
};

// EPA 608 sections. Explicitly NOT ordered -- see the header. `universal`
// covers the other three; nothing else covers anything else.
const EPA_SECTIONS = { type_i: true, type_ii: true, type_iii: true, universal: true };

function refuse(code, message, extra) {
  return Object.assign({ ok: false, error: { code: code, message: message } }, extra || {});
}

function isDate(s) {
  return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s);
}

// Whole days from `today` to `dateStr`, negative once past. Compared as UTC
// midnights so a technician's licence does not expire an hour early for a
// dispatcher in a different timezone.
function daysUntil(dateStr, today) {
  if (!isDate(dateStr) || !isDate(today)) return null;
  const a = Date.UTC(+dateStr.slice(0, 4), +dateStr.slice(5, 7) - 1, +dateStr.slice(8, 10));
  const b = Date.UTC(+today.slice(0, 4), +today.slice(5, 7) - 1, +today.slice(8, 10));
  return Math.round((a - b) / 86400000);
}

// Four states, and 'unknown' is one of them on purpose.
//   current  -- valid, or genuinely has no expiry
//   expiring -- inside the warning window
//   expired  -- past
//   unknown  -- should have an expiry and none is recorded
function classifyRecord(rec, today, warnDays) {
  const w = Number.isFinite(warnDays) ? warnDays : DEFAULT_WARN_DAYS;
  if (!rec || typeof rec !== 'object') return { status: 'unknown', days: null, warn_days: w, no_expiry: false };
  // has_expiry === false is a POSITIVE answer about a lifetime credential, not
  // an absence of data. EPA 608 is the case this exists for.
  if (rec.has_expiry === false) return { status: 'current', days: null, warn_days: w, no_expiry: true };
  const days = daysUntil(rec.expires_on, today);
  if (days === null) return { status: 'unknown', days: null, warn_days: w, no_expiry: false };
  if (days < 0) return { status: 'expired', days: days, warn_days: w, no_expiry: false };
  if (days <= w) return { status: 'expiring', days: days, warn_days: w, no_expiry: false };
  return { status: 'current', days: days, warn_days: w, no_expiry: false };
}

// One record per (technician, type, section-or-jurisdiction) -- the newest by
// issue date wins. A technician who renews a licence has two rows; the board
// must show the renewal, not whichever arrived first.
function recordKey(r) {
  return [
    String(r.technician_id || ''),
    String(r.record_type || ''),
    String(r.epa_section || r.jurisdiction || '')
  ].join('|').toLowerCase();
}

function latestByKey(records) {
  const best = Object.create(null);
  (Array.isArray(records) ? records : []).forEach(function (r) {
    if (!r || typeof r !== 'object') return;
    const k = recordKey(r);
    const cur = best[k];
    if (!cur) { best[k] = r; return; }
    const a = isDate(r.issued_on) ? r.issued_on : '';
    const b = isDate(cur.issued_on) ? cur.issued_on : '';
    // A dated record beats an undated one; between two dated ones the later
    // wins. Two undated records keep the first seen, and that is reported as
    // unknown downstream anyway.
    if (a > b) best[k] = r;
  });
  return Object.keys(best).map(function (k) { return best[k]; });
}

// The board: every technician's credentials, classified. No aggregate verdict
// per technician here -- "is this person compliant" is not a question with an
// answer independent of what they are being sent to do. That is eligibility's
// job, below, and it needs the job's requirements.
function evaluateBoard(records, today, warnDays) {
  if (!isDate(today)) return refuse('BAD_TODAY', 'today must be YYYY-MM-DD');
  const rows = latestByKey(records).map(function (r) {
    const c = classifyRecord(r, today, warnDays);
    return {
      technician_id: r.technician_id || null,
      record_type: r.record_type || null,
      epa_section: r.epa_section || null,
      jurisdiction: r.jurisdiction || null,
      issued_on: isDate(r.issued_on) ? r.issued_on : null,
      expires_on: isDate(r.expires_on) ? r.expires_on : null,
      status: c.status,
      days: c.days,
      no_expiry: c.no_expiry
    };
  });
  const counts = { current: 0, expiring: 0, expired: 0, unknown: 0 };
  rows.forEach(function (r) { counts[r.status] = (counts[r.status] || 0) + 1; });
  return {
    ok: true,
    today: today,
    warn_days: Number.isFinite(warnDays) ? warnDays : DEFAULT_WARN_DAYS,
    counts: counts,
    // Surfaced beside the totals rather than under them: a board that buries
    // its unknowns reads as a compliance verdict it has not earned.
    unknown_count: counts.unknown,
    rows: rows
  };
}

// Does one record satisfy one requirement?
function satisfies(rec, req) {
  if (rec.record_type !== req.record_type) return false;
  if (req.record_type === 'epa_608') {
    // THE SECTION RULE. Universal covers everything; otherwise the section must
    // match exactly. "Has an EPA card" is not an answer to "may open this
    // chiller" -- see the header.
    if (!req.epa_section) return true;
    return rec.epa_section === 'universal' || rec.epa_section === req.epa_section;
  }
  if (req.jurisdiction) {
    return String(rec.jurisdiction || '').toLowerCase() === String(req.jurisdiction).toLowerCase();
  }
  return true;
}

// DISPATCH ELIGIBILITY. `requirements` is what the JOB needs, supplied by the
// caller -- there is no default list, because what a job requires depends on
// the equipment and the jurisdiction and nobody can infer it from a trade name.
// A job with no stated requirements yields ok:false, not "everyone is
// eligible".
function evaluateEligibility(records, requirements, today, warnDays) {
  if (!isDate(today)) return refuse('BAD_TODAY', 'today must be YYYY-MM-DD');
  if (!Array.isArray(requirements) || !requirements.length) {
    return refuse('NO_REQUIREMENTS',
      'This job lists no required credentials, so eligibility cannot be computed. ' +
      'State what the job requires rather than treating an empty list as "anyone may go".');
  }
  for (const req of requirements) {
    if (!req || !RECORD_TYPES[req.record_type]) {
      return refuse('UNKNOWN_REQUIREMENT',
        'Requirement names an unknown credential type: ' + JSON.stringify(req && req.record_type));
    }
    if (req.record_type === 'epa_608' && req.epa_section && !EPA_SECTIONS[req.epa_section]) {
      return refuse('UNKNOWN_EPA_SECTION',
        'EPA 608 section must be one of: ' + Object.keys(EPA_SECTIONS).join(', '));
    }
  }

  const held = latestByKey(records);
  const byTech = Object.create(null);
  held.forEach(function (r) {
    const t = String(r.technician_id || '');
    if (!t) return;
    (byTech[t] = byTech[t] || []).push(r);
  });

  const techs = Object.keys(byTech).sort().map(function (t) {
    const mine = byTech[t];
    const checks = requirements.map(function (req) {
      const match = mine.filter(function (r) { return satisfies(r, req); })[0];
      if (!match) {
        return { requirement: req, met: false, reason: 'missing', status: null };
      }
      const c = classifyRecord(match, today, warnDays);
      // EXPIRING still dispatches -- it is valid today, which is the question
      // being asked -- but it is reported so a dispatcher can see the cliff.
      const met = c.status === 'current' || c.status === 'expiring';
      return {
        requirement: req,
        met: met,
        // 'unknown' is its own reason and never collapses into 'expired'. One
        // means the paperwork is missing; the other means the person may not
        // legally do the work. They lead to different phone calls.
        reason: met ? (c.status === 'expiring' ? 'expiring' : 'ok') : c.status,
        status: c.status,
        days: c.days,
        expires_on: isDate(match.expires_on) ? match.expires_on : null
      };
    });
    const eligible = checks.every(function (c) { return c.met; });
    return {
      technician_id: t,
      eligible: eligible,
      // Named so a dispatcher can act: which requirement, and why not.
      blocking: checks.filter(function (c) { return !c.met; })
        .map(function (c) { return { record_type: c.requirement.record_type, epa_section: c.requirement.epa_section || null, jurisdiction: c.requirement.jurisdiction || null, reason: c.reason }; }),
      warnings: checks.filter(function (c) { return c.met && c.reason === 'expiring'; })
        .map(function (c) { return { record_type: c.requirement.record_type, days: c.days, expires_on: c.expires_on }; }),
      checks: checks
    };
  });

  return {
    ok: true,
    today: today,
    warn_days: Number.isFinite(warnDays) ? warnDays : DEFAULT_WARN_DAYS,
    requirements: requirements,
    eligible: techs.filter(function (t) { return t.eligible; }).map(function (t) { return t.technician_id; }),
    // Technicians with NO records at all never appear here, and that is stated
    // rather than silently true: this evaluates the people who have credentials
    // on file. Somebody with an empty file is not "ineligible", they are
    // unrecorded, and the roster is where that shows.
    evaluated: techs.length,
    technicians: techs
  };
}

module.exports = {
  DEFAULT_WARN_DAYS,
  RECORD_TYPES,
  EPA_SECTIONS,
  daysUntil,
  classifyRecord,
  latestByKey,
  evaluateBoard,
  satisfies,
  evaluateEligibility
};
