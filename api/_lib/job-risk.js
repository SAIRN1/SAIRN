// api/_lib/job-risk.js
// ---------------------------------------------------------------------------
// [0072] Material-correlated job risk.
//
// Design: docs/2026-09-02-0072-material-job-risk-design.md
//
// THE ONE RULE. Nothing is assumed. Every input is measured or declared, and if
// it is neither, the job is reported as risk "unknown" with a named reason and
// is NOT scored. There are no default lead times, no default stage durations,
// and no "typical" fallback anywhere in this file.
//
// That is not caution for its own sake. A projected completion date built on an
// invented 14-day lead time is worse than no date, because it is a number a shop
// would schedule a customer against and then miss. The subcontractor compliance
// gate settled the same question the day before this was written: three states,
// never two, and untracked is never a green tick.
//
// Pure functions, no I/O, no clock of its own -- `today` is always passed in, so
// every projection is reproducible and testable.
// ---------------------------------------------------------------------------

'use strict';

// The production pipeline, in order. A job's remaining work is the stages AFTER
// its current one.
const STAGES = ['templated', 'cutting', 'polishing', 'qa', 'ready', 'installed'];

// Below this many completed jobs there is no honest median, so production time
// is unknown and the job is not scored.
const MIN_COMPLETED_JOBS = 3;
// Below this many receipts the observed average is noise; quoted wins.
const MIN_OBSERVATIONS = 3;
// Slack at or under this many days is "tight" rather than "ok".
const TIGHT_DAYS = 3;

const DAY = 86400000;

function norm(s) { return String(s == null ? '' : s).trim().toLowerCase(); }

function toDate(v) {
  if (!v) return null;
  const d = new Date(String(v).slice(0, 10) + 'T00:00:00Z');
  return isNaN(d.getTime()) ? null : d;
}

function addDays(d, n) { return new Date(d.getTime() + n * DAY); }
function daysBetween(a, b) { return Math.round((b.getTime() - a.getTime()) / DAY); }
function iso(d) { return d.toISOString().slice(0, 10); }

function median(nums) {
  if (!nums.length) return null;
  const s = nums.slice().sort(function (a, b) { return a - b; });
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

/**
 * Lead time for a (supplier, material) pair.
 *
 * Returns {days, source, spread} or {days:null, reason}. QUOTED AND OBSERVED
 * ARE NEVER BLENDED -- the caller is told which one it got, because "the
 * supplier quotes 14 days but the last four took 31" is the most useful thing
 * this data can say and an average destroys it.
 */
function leadTime(rows, supplier, material) {
  const sup = norm(supplier);
  const mat = norm(material);
  if (!sup) return { days: null, reason: 'no supplier recorded on the slab or job' };
  if (!mat) return { days: null, reason: 'no material recorded on the job' };
  const row = (rows || []).find(function (r) {
    return norm(r.supplier) === sup && norm(r.material) === mat;
  });
  if (!row) return { days: null, reason: 'no lead time recorded for ' + mat + ' from ' + sup };

  const n = row.observed_n || 0;
  if (n >= MIN_OBSERVATIONS) {
    return {
      days: Math.round(row.observed_total_days / n),
      source: 'observed',
      observations: n,
      spread: (row.observed_min_days != null && row.observed_max_days != null)
        ? [row.observed_min_days, row.observed_max_days] : null,
      quoted_days: row.quoted_days == null ? null : row.quoted_days
    };
  }
  if (row.quoted_days != null) {
    return {
      days: row.quoted_days, source: 'quoted', observations: n,
      note: n ? (n + ' observation(s) so far, not yet enough to overrule the quote') : null
    };
  }
  return {
    days: null,
    reason: 'a row exists for ' + mat + ' from ' + sup + ' but it has no quoted lead time and only ' +
            n + ' observation(s)'
  };
}

/**
 * Median duration of each stage, derived from COMPLETED jobs on this licence.
 * No stage durations are shipped as defaults -- if the history is too thin the
 * answer is null and the caller must not score.
 *
 * A completed job gives one total (templateDate -> installedAt). Attributing
 * that total across stages needs per-stage timestamps the app does not record,
 * so this deliberately returns a WHOLE-PIPELINE median and a per-stage share is
 * NOT invented. Remaining time is that median scaled by the fraction of stages
 * left -- stated plainly as an approximation rather than dressed up as a
 * per-stage model.
 */
function productionProfile(jobs, today) {
  const durations = [];
  (jobs || []).forEach(function (j) {
    if (!j || j.stage !== 'installed') return;
    const start = toDate(j.templateDate);
    const end = toDate(j.installedAt);
    if (!start || !end) return;
    const d = daysBetween(start, end);
    if (d >= 0 && d < 3650) durations.push(d);
  });
  if (durations.length < MIN_COMPLETED_JOBS) {
    return {
      full_pipeline_days: null,
      completed_jobs: durations.length,
      reason: 'only ' + durations.length + ' completed job(s) with both a template date and an ' +
              'install date; need ' + MIN_COMPLETED_JOBS + ' before a median means anything'
    };
  }
  return { full_pipeline_days: median(durations), completed_jobs: durations.length };
}

function remainingStageFraction(stage) {
  const i = STAGES.indexOf(String(stage || '').toLowerCase());
  if (i === -1) return null;
  const producing = STAGES.length - 1;          // 'installed' is the end state
  return Math.max(0, (producing - i)) / producing;
}

/**
 * Is there a slab already in hand for this job?
 * Explicit reservation wins. Otherwise a matching in-stock slab of the same
 * material with enough usable sqft counts.
 */
function slabInHand(job, slabs) {
  const mat = norm(job.material);
  const need = Number(job.sqft) || 0;
  if (job.reservedSlabId) {
    const r = (slabs || []).find(function (s) { return s && s.id === job.reservedSlabId; });
    if (r) return { inHand: true, via: 'reserved', slab_id: r.id };
    return { inHand: false, via: 'reserved-but-missing', note: 'job reserves ' + job.reservedSlabId + ' which is not in inventory' };
  }
  if (!mat) return { inHand: false, via: 'no-material' };
  const match = (slabs || []).find(function (s) {
    return s && norm(s.material) === mat && norm(s.status) === 'in-stock' && (Number(s.usableSqft) || 0) >= need;
  });
  return match ? { inHand: true, via: 'matched', slab_id: match.id } : { inHand: false, via: 'none-matching' };
}

/**
 * Score one job. `today` is passed in, never read from the clock.
 */
function assessJob(job, ctx) {
  const today = toDate(ctx && ctx.today);
  const out = { job_id: job && job.id, risk: 'unknown', reasons: [] };
  if (!today) { out.reasons.push('no reference date supplied'); return out; }
  if (!job) { out.reasons.push('no job'); return out; }

  const target = toDate(job.targetDate);
  if (!target) {
    // No commitment means nothing to miss. This is NOT "ok" -- an unscheduled
    // job is a different state from a safe one, and calling it ok would hide it.
    out.risk = 'unscheduled';
    out.reasons.push('no target install date on this job');
    return out;
  }
  out.target_date = iso(target);

  if (String(job.stage).toLowerCase() === 'installed') {
    out.risk = 'done';
    return out;
  }

  const hand = slabInHand(job, ctx.slabs);
  out.slab = hand;
  let slabReady;
  if (hand.inHand) {
    slabReady = today;
    out.slab_ready_on = iso(today);
  } else {
    const supplier = job.supplier || (ctx.defaultSupplierFor ? ctx.defaultSupplierFor(job) : '');
    const lt = leadTime(ctx.leadTimes, supplier, job.material);
    out.lead_time = lt;
    if (lt.days == null) {
      out.reasons.push(lt.reason);
      return out;                          // unknown, and NOT scored
    }
    slabReady = addDays(today, lt.days);
    out.slab_ready_on = iso(slabReady);
  }

  const prof = productionProfile(ctx.jobs, today);
  out.production = prof;
  if (prof.full_pipeline_days == null) {
    out.reasons.push(prof.reason);
    return out;                            // unknown, and NOT scored
  }
  const frac = remainingStageFraction(job.stage);
  if (frac == null) {
    out.reasons.push('unrecognised stage "' + job.stage + '"');
    return out;
  }
  const productionDays = Math.round(prof.full_pipeline_days * frac);
  out.remaining_production_days = productionDays;

  const projected = addDays(slabReady, productionDays);
  out.projected_completion = iso(projected);
  const slack = daysBetween(projected, target);
  out.slack_days = slack;

  // The number is reported alongside the flag on purpose: "at risk by 1 day"
  // and "at risk by 3 weeks" are different problems and a boolean hides that.
  out.risk = slack < 0 ? 'at_risk' : (slack <= TIGHT_DAYS ? 'tight' : 'ok');
  return out;
}

/** Fold one real receipt into a lead-time row. Returns the updated row. */
function observeReceipt(row, orderedAt, receivedAt) {
  const a = toDate(orderedAt), b = toDate(receivedAt);
  if (!a || !b) return { row: row, applied: false, reason: 'need both an order date and a receipt date' };
  const days = daysBetween(a, b);
  if (days < 0) return { row: row, applied: false, reason: 'received before it was ordered' };
  const r = Object.assign({
    observed_total_days: 0, observed_n: 0, observed_min_days: null, observed_max_days: null
  }, row || {});
  r.observed_total_days += days;
  r.observed_n += 1;
  r.observed_min_days = r.observed_min_days == null ? days : Math.min(r.observed_min_days, days);
  r.observed_max_days = r.observed_max_days == null ? days : Math.max(r.observed_max_days, days);
  r.last_observed_at = b.toISOString();
  return { row: r, applied: true, days: days };
}

module.exports = {
  STAGES, MIN_COMPLETED_JOBS, MIN_OBSERVATIONS, TIGHT_DAYS,
  leadTime, productionProfile, remainingStageFraction, slabInHand,
  assessJob, observeReceipt
};
