// api/_lib/roofing-locations.js
// SAIRNroofing Phase 4a -- multi-location attribution and crew scheduling.
//
// PURE -- no I/O.
//
// ── WHY ATTRIBUTION SHIPS NOW AND FILTERING DOES NOT ─────────────────────
// The same asymmetry api/_lib/dnt-location.js argued for SAIRNdental, and it
// is the whole reason this is in 4a rather than later: CAPTURING which
// location a job belongs to has a deadline. A job written without a location
// can never be assigned one afterwards, because the information was never
// collected. Consolidated reporting, per-location dashboards and a location
// filter can all be built later at the same cost.
//
// So location_id is stamped on every job write and reported on, and the
// PRIVACY GATE IS UNCHANGED -- still the three-tier assignment model from
// Phase 1. A Columbus foreman sees the jobs assigned to them, wherever those
// jobs are; they do not lose sight of a job because it belongs to another
// branch, and a Cleveland estimator does not gain or lose anything either.
//
// Decision recorded 2026-08-25 (Michael): location-as-access-boundary is NOT
// built yet. It is real work, harder to reverse, and it interacts with the
// existing tiers in exactly the shape of the SAIRNsenior bug where one branch
// checked management-only where it should have checked broad-read. It deserves
// a real multi-location customer to design against rather than a guess now.
// Logged as ready-to-build-later.
//
// ── INVISIBLE TO A SINGLE-LOCATION SHOP ──────────────────────────────────
// Every write with no location_id is stamped DEFAULT_LOCATION_ID, so the jobs
// that already exist and every shop that never opens a second branch behave
// exactly as they do today. Nothing in the UI has to know about locations for
// the data to stay correct.

'use strict';

// The implicit location every pre-existing and single-branch job belongs to.
// A real registry row may later be created with this id; nothing here assumes
// the string is absent from rf_locations.
const DEFAULT_LOCATION_ID = 'LOC-DEFAULT';

const MAX_ID_LEN = 64;
const MAX_NAME_LEN = 128;

// A scheduled day is one of these. Deliberately small -- this is a crew day,
// not a project-management state machine, and inventing statuses nobody asked
// for is how a schedule stops matching what the crew actually does.
const SCHEDULE_STATUSES = ['planned', 'confirmed', 'in_progress', 'done', 'cancelled'];

function str(v) { return typeof v === 'string' ? v.trim() : ''; }

// Returns a shallow copy of payload with location_id guaranteed present and
// bounded. A caller-supplied value is trusted but length-capped; anything
// absent, blank, non-string or over-length falls back to the default rather
// than being rejected -- a job must never fail to save because of an optional
// attribution field.
function stampLocation(payload) {
  const out = Object.assign({}, payload || {});
  const given = str(out.location_id);
  out.location_id = (given && given.length <= MAX_ID_LEN) ? given : DEFAULT_LOCATION_ID;
  return out;
}

function validateLocation(payload) {
  const problems = [];
  if (!payload || typeof payload !== 'object') return ['no location supplied'];
  const id = str(payload.id);
  if (!id) problems.push('location_id (payload.id) is required');
  else if (id.length > MAX_ID_LEN) problems.push('location_id is too long');
  const name = str(payload.name);
  if (!name) problems.push('a location needs a name');
  else if (name.length > MAX_NAME_LEN) problems.push('name is too long');
  return problems;
}

function validateSchedule(payload) {
  const problems = [];
  if (!payload || typeof payload !== 'object') return ['no schedule entry supplied'];
  if (!str(payload.id)) problems.push('schedule_id (payload.id) is required');
  if (!str(payload.job_id)) problems.push('job_id is required -- a scheduled day always belongs to a job');
  const d = str(payload.scheduled_date);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(d)) problems.push('scheduled_date must be YYYY-MM-DD');
  else if (isNaN(new Date(d + 'T12:00:00Z').getTime())) problems.push('scheduled_date is not a real date');
  if (payload.status !== undefined && SCHEDULE_STATUSES.indexOf(payload.status) === -1) {
    problems.push('status must be one of: ' + SCHEDULE_STATUSES.join(', '));
  }
  if (payload.crew !== undefined && !Array.isArray(payload.crew)) {
    problems.push('crew must be an array of employee_ids');
  }
  return problems;
}

// Normalise the crew list: strings only, trimmed, de-duplicated, order kept.
// De-duplication matters -- the same person listed twice on one day would
// double-count in any future capacity view, and silently.
function normalizeCrew(crew) {
  const seen = Object.create(null);
  const out = [];
  (Array.isArray(crew) ? crew : []).forEach(function (c) {
    const id = str(c);
    if (!id || seen[id]) return;
    seen[id] = true;
    out.push(id);
  });
  return out;
}

// Can this session see this schedule entry?
//
// Management and broad-read see the whole board, matching their job access.
// A NARROW-TIER employee sees a day if they are ON THE CREW for it, or if the
// job itself is assigned to them. The crew clause is the part that is easy to
// miss and the reason this is a named function rather than an inline check: a
// crew member who is not the job's assignee would otherwise be scheduled to
// work a day they cannot see, which is worse than not being scheduled at all.
function canSeeSchedule(session, entry, jobAssignee, managementRoles, broadReadRoles) {
  if (!session) return false;
  if (managementRoles && managementRoles[session.role]) return true;
  if (broadReadRoles && broadReadRoles[session.role]) return true;
  const crew = normalizeCrew(entry && entry.crew);
  if (crew.indexOf(session.employee_id) !== -1) return true;
  return !!jobAssignee && jobAssignee === session.employee_id;
}

module.exports = {
  DEFAULT_LOCATION_ID,
  SCHEDULE_STATUSES,
  stampLocation,
  validateLocation,
  validateSchedule,
  normalizeCrew,
  canSeeSchedule
};
