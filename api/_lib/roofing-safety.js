// api/_lib/roofing-safety.js
// SAIRNroofing gap B4 -- fall-protection equipment and job hazard assessments.
//
// PURE -- no I/O, no LLM.
//
// ── WHY, AND WHAT WAS VERIFIED FIRST ─────────────────────────────────────
// The 2026-08-26 competitive-gap audit's Tier-B item B4: fall-protection
// plans, anchor-point inspection logs, JHA templates, a citation-ready audit
// trail and training verification, against a note that OSHA appears in
// SAIRNroofing "only as a credential type". Re-verified 2026-09-02 rather than
// trusted: sairnroofing.html has 5 hits for "osha", all in the certifications
// panel, and ZERO for fall protection, anchor, JHA, toolbox, incident or near
// miss. api/ and sql/ have none of those at all.
//
// ── TWO APPS ALREADY LOG INCIDENTS AND THIS DOES NOT DUPLICATE THEM ─────
// Checked before writing a line, because the last shared layer I built claimed
// to prevent a duplication that had already happened. SAIRNbuild has a Safety
// & Incidents panel with an osha_reportable flag, corrective actions and
// bld_toolbox_talks. StoneDesk has an incident type list (near_miss, first_aid,
// recordable, lost_time, property, exposure, equipment). Both are client-side
// and both are INCIDENT LOGGING -- what happened after the fact.
//
// This file is the other half and deliberately does not overlap: EQUIPMENT
// THAT EXPIRES and A HAZARD ASSESSMENT THE CREW ON THE ROOF TODAY HAS OR HAS
// NOT SIGNED. Neither app has either. An incident log is a record; this is a
// clock and a cross-check.
//
// ── IT DOES NOT KNOW WHAT OSHA REQUIRES, AND WILL NOT PRETEND TO ─────────
// The single most dangerous thing this file could do is state an inspection
// interval as though it were regulation. Intervals come from the standard, the
// manufacturer's instructions and the competent person's judgement, they
// differ by equipment type and employer programme, and a wrong one printed as
// authoritative is a contractor telling an OSHA inspector a number this app
// invented. So `inspection_interval_days` is entered by the contractor WITH A
// SOURCE, exactly as roofing-programs.js and roofing-warranties.js already do,
// and equipment with no interval reads 'no_interval_stated' -- never a default.
//
// NOTHING HERE PRODUCES A COMPLIANCE VERDICT. It reports what is recorded and
// what is overdue against the contractor's own programme. It never says
// "compliant", and the panel must keep reading that way.
//
// ── IT WILL NOT ASSUME A CLOCK ───────────────────────────────────────────
// Every entry point requires a caller-supplied `today`.

'use strict';

// Removed-from-service is NOT a status of the inspection clock -- it is the
// end of it. Kept separate because "overdue for inspection" and "taken out of
// service" need opposite actions: one is chase it, the other is do not touch
// it.
const EQUIPMENT_STATUSES = ['in_service', 'removed_from_service', 'failed_inspection', 'retired'];
// A due date is "due soon" this many days out. A review window a caller
// overrides -- NOT a regulatory figure, and named so nobody reads it as one.
const DEFAULT_WARN_DAYS = 14;

function isDate(s) { return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s); }
function str(v) { return typeof v === 'string' ? v.trim() : ''; }
function whole(v) {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  return (typeof n === 'number' && isFinite(n) && Math.floor(n) === n) ? n : null;
}
function addDays(iso, n) {
  const t = Date.parse(iso + 'T00:00:00Z');
  if (!isFinite(t)) return null;
  return new Date(t + n * 86400000).toISOString().slice(0, 10);
}
function daysBetween(a, b) {
  const x = Date.parse(a + 'T00:00:00Z'), y = Date.parse(b + 'T00:00:00Z');
  if (!isFinite(x) || !isFinite(y)) return null;
  return Math.round((y - x) / 86400000);
}

// ── One piece of fall-protection equipment ───────────────────────────────
function equipmentState(input) {
  input = input || {};
  const today = isDate(input.today) ? input.today : null;
  if (!today) {
    return { ok: false, error: { code: 'NO_TODAY', message: 'today (YYYY-MM-DD) is required -- this engine will not assume a clock' } };
  }
  const e = input.item || null;
  if (!e) return { ok: false, error: { code: 'NO_ITEM', message: 'no equipment supplied' } };
  const warn = whole(input.warn_days) === null ? DEFAULT_WARN_DAYS : whole(input.warn_days);

  const status = EQUIPMENT_STATUSES.indexOf(e.status) === -1 ? null : e.status;
  const out = {
    ok: true,
    equipment_id: str(e.equipment_id) || null,
    kind: str(e.kind) || null,
    identifier: str(e.identifier) || null,
    job_id: str(e.job_id) || null,
    status: status,
    last_inspected_on: isDate(e.last_inspected_on) ? e.last_inspected_on : null,
    last_inspected_by: str(e.last_inspected_by) || null,
    interval_days: whole(e.inspection_interval_days),
    interval_source: str(e.interval_source) || null,
    due_on: null,
    days_left: null,
    inspection: 'unknown',
    problems: status === null && e.status !== undefined
      ? ['unrecognised equipment status "' + String(e.status) + '"'] : []
  };

  // Out of service short-circuits. Running an inspection clock on kit nobody
  // may use produces a "due soon" nag about a harness in a bin, and buries the
  // real ones.
  if (status === 'removed_from_service' || status === 'failed_inspection' || status === 'retired') {
    out.inspection = 'out_of_service';
    return out;
  }

  if (!out.last_inspected_on) {
    // Never inspected is its own answer. It is NOT "overdue by an unknown
    // amount" and it is certainly not fine.
    out.inspection = 'never_inspected';
    return out;
  }
  if (out.interval_days === null || out.interval_days <= 0) {
    // REFUSES to guess. See the header: an invented interval is a contractor
    // repeating this app's number to an inspector.
    out.inspection = 'no_interval_stated';
    return out;
  }
  if (!out.interval_source) {
    out.inspection = 'no_source_for_interval';
    out.problems.push('an inspection interval is recorded with no source -- name where it comes from (the standard, the manufacturer, your own programme) before relying on it');
    return out;
  }

  out.due_on = addDays(out.last_inspected_on, out.interval_days);
  const left = out.due_on ? daysBetween(today, out.due_on) : null;
  out.days_left = left;
  if (left === null) out.inspection = 'no_interval_stated';
  else if (left < 0) out.inspection = 'overdue';
  else if (left <= warn) out.inspection = 'due_soon';
  else out.inspection = 'current';
  return out;
}

// ── A job hazard assessment, and who has NOT signed it ───────────────────
// The cross-check that makes this more than a filing cabinet. A JHA sitting in
// a folder tells you nothing; a JHA compared against the crew actually
// scheduled on the roof that day tells you who is up there without one.
//
// `crew` is the list of employee ids scheduled for the job on that date --
// supplied by the caller from rf_schedule, never inferred here.
function jhaState(input) {
  input = input || {};
  const today = isDate(input.today) ? input.today : null;
  if (!today) {
    return { ok: false, error: { code: 'NO_TODAY', message: 'today (YYYY-MM-DD) is required -- this engine will not assume a clock' } };
  }
  const j = input.jha || null;
  if (!j) return { ok: false, error: { code: 'NO_JHA', message: 'no hazard assessment supplied' } };
  const validFor = whole(input.valid_for_days);

  const out = {
    ok: true,
    jha_id: str(j.jha_id) || null,
    job_id: str(j.job_id) || null,
    assessed_on: isDate(j.assessed_on) ? j.assessed_on : null,
    competent_person: str(j.competent_person) || null,
    hazard_count: Array.isArray(j.hazards) ? j.hazards.length : 0,
    acknowledged: [],
    missing_acknowledgement: [],
    currency: 'unknown',
    problems: []
  };

  if (!out.assessed_on) {
    out.problems.push('no assessment date -- it cannot be shown to be current for any day');
  } else if (validFor === null || validFor < 0) {
    // No stated validity is NOT "valid forever". Same refusal as an interval.
    out.currency = 'no_validity_stated';
  } else {
    const age = daysBetween(out.assessed_on, today);
    out.age_days = age;
    out.currency = (age !== null && age <= validFor) ? 'current' : 'stale';
  }
  if (!out.competent_person) {
    out.problems.push('no competent person named on the assessment');
  }
  if (!out.hazard_count) {
    // An empty JHA is worse than none: it looks like the work was done.
    out.problems.push('no hazards recorded -- an empty assessment reads as though one was carried out');
  }

  const ack = Object.create(null);
  (Array.isArray(j.acknowledged_by) ? j.acknowledged_by : []).forEach(function (a) {
    const id = str(a); if (id) ack[id] = true;
  });
  const crew = [];
  (Array.isArray(input.crew) ? input.crew : []).forEach(function (c) {
    const id = str(c);
    if (id && crew.indexOf(id) === -1) crew.push(id);
  });
  out.crew_size = crew.length;
  crew.forEach(function (id) {
    (ack[id] ? out.acknowledged : out.missing_acknowledgement).push(id);
  });
  // Someone who signed but is not on the crew is surfaced too -- usually
  // harmless (they came off the job) but it is the shape of a signature
  // collected for the wrong day, and silently dropping it hides that.
  out.acknowledged_not_on_crew = Object.keys(ack).filter(function (id) { return crew.indexOf(id) === -1; });
  return out;
}

// ── The board ────────────────────────────────────────────────────────────
function safetyBoard(input) {
  input = input || {};
  const today = isDate(input.today) ? input.today : null;
  if (!today) {
    return { ok: false, error: { code: 'NO_TODAY', message: 'today (YYYY-MM-DD) is required -- this engine will not assume a clock' } };
  }
  const items = (Array.isArray(input.equipment) ? input.equipment : []).map(function (e) {
    return equipmentState({ item: e, today: today, warn_days: input.warn_days });
  }).filter(function (r) { return r.ok; });

  const by = function (s) { return items.filter(function (i) { return i.inspection === s; }); };
  return {
    ok: true,
    today: today,
    equipment: items,
    overdue: by('overdue').map(function (i) { return i.equipment_id; }),
    due_soon: by('due_soon').map(function (i) { return i.equipment_id; }),
    never_inspected: by('never_inspected').map(function (i) { return i.equipment_id; }),
    // Kept apart from overdue because it is not a chase -- it is kit whose
    // clock cannot run at all, and the fix is entering a sourced interval.
    unusable_record: by('no_interval_stated').concat(by('no_source_for_interval'))
      .map(function (i) { return i.equipment_id; }),
    out_of_service: by('out_of_service').map(function (i) { return i.equipment_id; }),
    current: by('current').length,
    // Stated on every board, in the response, so a UI cannot present this as a
    // compliance result by omission.
    disclaimer: 'This is a record of what has been entered against your own programme. It is not a compliance determination and no interval here comes from this application.'
  };
}

module.exports = {
  EQUIPMENT_STATUSES,
  DEFAULT_WARN_DAYS,
  equipmentState,
  jhaState,
  safetyBoard
};
