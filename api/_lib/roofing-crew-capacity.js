// api/_lib/roofing-crew-capacity.js
// SAIRNroofing gap A2 -- crew load and double-booking across the schedule.
//
// PURE -- no I/O, no LLM.
//
// ── WHAT THE AUDIT ACTUALLY SAID, AND WHAT WAS VERIFIED ──────────────────
// The 2026-08-26 worldwide competitive-gap audit calls crew/field-labour
// scheduling "the market's loudest hole" (Roofr named for "zero crew
// management or scheduling"; SubcontractorHub exists specifically to fill it),
// and records SAIRNroofing as PARTIALLY CLOSED -- "rf_schedule exists ...
// depth vs. the complaint NOT ASSESSED HERE".
//
// So it was assessed, 2026-09-02, against the real code rather than the audit's
// summary. rf_schedule genuinely holds a crew day: job, branch, date, one of
// five statuses, a de-duplicated employee list, role-gated visibility, and a
// separate set_status path a crew member may use on their own day without
// being able to move the job, the date or the crew. That is more than the
// complaint describes and it is not nothing.
//
// WHAT IT DOES NOT HOLD -- the depth -- is this file. The same employee can be
// put on two jobs on the same day and NOTHING SAYS SO. That is not a
// hypothetical: normalizeCrew() in roofing-locations.js de-duplicates a crew
// list and its own comment explains why -- "the same person listed twice on one
// day would double-count in ANY FUTURE CAPACITY VIEW". The author of that line
// anticipated this file. It did not exist.
//
// ── IT REPORTS, IT DOES NOT REFUSE ───────────────────────────────────────
// Deliberately different from the subcontractor assignment gate, which refuses
// at the endpoint. Two jobs in one day is a NORMAL roofing day -- a small
// repair in the morning and a second on the same street after lunch -- so a
// hard block would be wrong, and a wrong block is how a gate gets routed
// around. What is wrong is doing it BY ACCIDENT. So every overlap is named,
// loudly, and the operator decides.
//
// ── CANCELLED DAYS DO NOT COUNT. DONE DAYS DO. ───────────────────────────
// A cancelled day is not work; counting it would invent conflicts that stop
// people scheduling real ones. A 'done' day is history and still occupied that
// person's time, so it stays in the load -- a capacity report that quietly
// forgets completed work understates every past week.
//
// ── NO IMPLIED RANGE, FOR THE SAME REASON AS NO IMPLIED CLOCK ────────────
// crewLoad() requires an explicit from/to. Defaulting to "this week" off a
// server clock would compute a contractor's week in UTC, which is the defect
// class fixed across nine SAIRNvet panels on 2026-09-01 and refused again in
// api/_lib/subcontractor-compliance.js and roofing-warranties.js.

'use strict';

// Statuses that occupy a person's day. Mirrors roofing-locations.js's
// SCHEDULE_STATUSES minus 'cancelled'. NOT imported from there on purpose:
// this module is pure and has no business reaching into the locations engine,
// and the two lists answer different questions -- "what may be stored" versus
// "what consumes a day". A status added there should be considered here
// deliberately rather than inherited silently.
const OCCUPYING_STATUSES = ['planned', 'confirmed', 'in_progress', 'done'];

// THE DATE CONCEPT IS OWNED BY ONE MODULE (item 94, 2026-09-14). This was a
// local copy of a line that existed FOURTEEN times across api/, all identical
// and all wrong the same way: they validated the SHAPE and not the DATE, so
// '2026-02-31' passed and `new Date` then SILENTLY REPAIRED it into 2026-03-03.
// The import is not bug-compatible -- rejecting the impossible date is the
// reason to move, and a migration that kept the old behaviour would be a
// rename. See api/_lib/calendar-date.js.
const isDate = require('./calendar-date').isCalendarDate;
function str(v) { return typeof v === 'string' ? v.trim() : ''; }

function occupies(row) {
  return OCCUPYING_STATUSES.indexOf(row && row.status) !== -1;
}

// ── Per-employee, per-day load ───────────────────────────────────────────
// Returns one entry per (employee, date) that has any occupying day, plus the
// two problem classes kept APART because they need opposite fixes:
//
//   conflict  -- the same person on TWO DIFFERENT JOBS that day. Might be
//                deliberate; the operator decides.
//   duplicate -- the same person on the SAME JOB twice that day, i.e. two
//                schedule rows that should be one. Always a data error, and
//                invisible today because normalizeCrew only de-duplicates
//                WITHIN one row's crew array, never across rows.
function crewLoad(input) {
  input = input || {};
  const from = isDate(input.from) ? input.from : null;
  const to = isDate(input.to) ? input.to : null;
  if (!from || !to) {
    return { ok: false, error: { code: 'NO_RANGE', message: 'from and to (YYYY-MM-DD) are both required -- this engine will not assume a date range' } };
  }
  if (from > to) {
    return { ok: false, error: { code: 'BAD_RANGE', message: 'from is after to' } };
  }
  const schedule = Array.isArray(input.schedule) ? input.schedule : [];

  // key: employee \x00 date  ->  { employee_id, date, jobs: {job_id: n}, days: [...] }
  const cells = Object.create(null);
  let skipped_no_date = 0, skipped_cancelled = 0;

  schedule.forEach(function (row) {
    if (!row) return;
    const d = str(row.scheduled_date).slice(0, 10);
    if (!isDate(d)) { skipped_no_date++; return; }
    if (d < from || d > to) return;
    if (!occupies(row)) { skipped_cancelled++; return; }
    const jobId = str(row.job_id) || '(no job)';
    const crew = Array.isArray(row.crew) ? row.crew : [];
    // De-duplicate WITHIN the row as well. normalizeCrew does this on write,
    // but this engine is handed whatever is in the table -- including rows
    // written before that helper existed -- and a report that trusts its input
    // to have been cleaned is a report that is wrong on old data.
    const seen = Object.create(null);
    crew.forEach(function (c) {
      const id = str(c);
      if (!id || seen[id]) return;
      seen[id] = true;
      const key = id + '\x00' + d;
      const cell = cells[key] || (cells[key] = { employee_id: id, date: d, jobs: Object.create(null), rows: [] });
      cell.jobs[jobId] = (cell.jobs[jobId] || 0) + 1;
      cell.rows.push({ schedule_id: str(row.schedule_id) || null, job_id: jobId, status: row.status });
    });
  });

  const load = Object.keys(cells).map(function (k) {
    const c = cells[k];
    const jobIds = Object.keys(c.jobs);
    return {
      employee_id: c.employee_id,
      date: c.date,
      job_count: jobIds.length,
      jobs: jobIds,
      rows: c.rows,
      conflict: jobIds.length > 1,
      duplicate: jobIds.filter(function (j) { return c.jobs[j] > 1; })
    };
  }).sort(function (a, b) {
    return a.date < b.date ? -1 : a.date > b.date ? 1 :
      (a.employee_id < b.employee_id ? -1 : a.employee_id > b.employee_id ? 1 : 0);
  });

  const conflicts = load.filter(function (x) { return x.conflict; });
  const duplicates = load.filter(function (x) { return x.duplicate.length > 0; });

  // Per-day head-count, which is the other half of the question a foreman
  // actually asks: not "is anyone double-booked" but "how many people do I
  // have out on Thursday".
  const perDay = Object.create(null);
  load.forEach(function (x) {
    const p = perDay[x.date] || (perDay[x.date] = { date: x.date, people: 0, jobs: Object.create(null) });
    p.people++;
    x.jobs.forEach(function (j) { p.jobs[j] = true; });
  });
  const days = Object.keys(perDay).sort().map(function (d) {
    return { date: d, people: perDay[d].people, job_count: Object.keys(perDay[d].jobs).length };
  });

  return {
    ok: true,
    from: from,
    to: to,
    load: load,
    conflicts: conflicts,
    duplicates: duplicates,
    days: days,
    // Stated rather than silently dropped: a row with an unreadable date is
    // invisible to this report, and a reader is entitled to know how many.
    skipped: { unreadable_date: skipped_no_date, not_occupying: skipped_cancelled }
  };
}

// ── What would this one day do? ──────────────────────────────────────────
// For the write path: given the schedule as it stands and a day about to be
// saved, name who would end up on two jobs. The candidate's OWN existing row
// is excluded by schedule_id, so editing a day never reports it as colliding
// with itself -- the mistake that makes this kind of check useless.
function conflictsFor(input) {
  input = input || {};
  const cand = input.candidate || null;
  if (!cand) return { ok: false, error: { code: 'NO_CANDIDATE', message: 'no candidate day supplied' } };
  const d = str(cand.scheduled_date).slice(0, 10);
  if (!isDate(d)) {
    return { ok: false, error: { code: 'NO_DATE', message: 'the candidate day has no readable scheduled_date' } };
  }
  const candId = str(cand.schedule_id) || null;
  const candJob = str(cand.job_id) || '(no job)';
  if (!occupies(cand)) {
    // A cancelled day cannot conflict with anything. Saying so explicitly
    // beats returning an empty list that reads like "we checked and it is
    // clear".
    return { ok: true, date: d, applicable: false, reason: 'a ' + str(cand.status) + ' day does not occupy anyone', conflicts: [] };
  }

  const crew = Object.create(null);
  (Array.isArray(cand.crew) ? cand.crew : []).forEach(function (c) {
    const id = str(c); if (id) crew[id] = true;
  });

  const found = Object.create(null);
  (Array.isArray(input.schedule) ? input.schedule : []).forEach(function (row) {
    if (!row) return;
    if (candId && str(row.schedule_id) === candId) return;     // itself
    if (str(row.scheduled_date).slice(0, 10) !== d) return;
    if (!occupies(row)) return;
    const rowJob = str(row.job_id) || '(no job)';
    (Array.isArray(row.crew) ? row.crew : []).forEach(function (c) {
      const id = str(c);
      if (!id || !crew[id]) return;
      const e = found[id] || (found[id] = { employee_id: id, date: d, with_jobs: [], same_job: false });
      if (rowJob === candJob) {
        // Same person, same job, same day, different row. Not a scheduling
        // conflict -- a duplicated row. Named separately so it is not
        // presented to the user as "he is on two jobs".
        e.same_job = true;
      } else if (e.with_jobs.indexOf(rowJob) === -1) {
        e.with_jobs.push(rowJob);
      }
    });
  });

  const list = Object.keys(found).map(function (k) { return found[k]; });
  return {
    ok: true,
    date: d,
    applicable: true,
    conflicts: list.filter(function (x) { return x.with_jobs.length > 0; }),
    duplicates: list.filter(function (x) { return x.same_job; })
  };
}

module.exports = {
  OCCUPYING_STATUSES,
  crewLoad,
  conflictsFor
};
