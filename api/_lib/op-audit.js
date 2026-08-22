// api/_lib/op-audit.js
// SAIRNcare Phase 3 item 5: operational-audit evaluation.
// PURE -- no I/O, same as every other engine in Phases 1-3.
//
// FOOD TEMPERATURE THRESHOLDS ARE REAL AND SOURCED, verified 2026-08-22
// against the FDA Food Code rather than written from memory:
//   cold holding   <= 41 F   (Food Code 3-501.16)
//   hot holding    >= 135 F  (Food Code 3-501.16)
//   roast hot-hold >= 130 F  (the one stated exception)
//   danger zone    41 F - 135 F
//   cooling        135 -> 70 F within 2 h, then 70 -> 41 F within 4 more (6 h total)
//
// THE CAVEAT THAT MATTERS AND IS ENCODED RATHER THAN GLOSSED: the FDA Food
// Code is a MODEL code. It is not binding law anywhere by itself -- each state
// adopts some edition of it, sometimes amended, sometimes an older edition. The
// current full edition is the 2022 Food Code (10th edition) plus its Supplement.
// So these values are the model default, and a facility whose state has adopted
// a different threshold must be able to override them. evaluateFoodTemp()
// therefore accepts facility-configured thresholds and reports which source it
// used, rather than presenting the model numbers as the law everywhere.

'use strict';

const FDA_MODEL = {
  cold_max_f: 41,
  hot_min_f: 135,
  roast_hot_min_f: 130,
  cooling_stage1: { from_f: 135, to_f: 70, hours: 2 },
  cooling_stage2: { from_f: 70, to_f: 41, hours: 4 },
  source: 'FDA Food Code 2022 (10th edition) 3-501.16 — model code, adopted state by state',
  source_url: 'https://www.fda.gov/food/retail-food-protection/fda-food-code'
};

const HOLDING_KINDS = { cold: true, hot: true, roast_hot: true };

function refuse(code, message, extra) {
  return Object.assign({ ok: false, error: { code: code, message: message } }, extra || {});
}

// Evaluate one temperature reading. thresholds may be a facility override; when
// absent the FDA model values are used AND the response says so, so nobody
// mistakes a model default for their own state's adopted rule.
function evaluateFoodTemp(opts) {
  opts = opts || {};
  const kind = opts.holding_kind;
  if (!HOLDING_KINDS[kind]) {
    return refuse('BAD_HOLDING_KIND', 'holding_kind must be one of: ' + Object.keys(HOLDING_KINDS).join(', '));
  }
  const t = Number(opts.temperature_f);
  if (!isFinite(t)) {
    return refuse('BAD_TEMPERATURE', 'A numeric temperature reading in Fahrenheit is required.');
  }
  const override = opts.thresholds || {};
  const usedOverride = {};
  function pick(key) {
    if (override[key] !== undefined && override[key] !== null && override[key] !== '' && isFinite(Number(override[key]))) {
      usedOverride[key] = true;
      return Number(override[key]);
    }
    return FDA_MODEL[key];
  }

  let limit, passed, requirement;
  if (kind === 'cold') {
    limit = pick('cold_max_f');
    passed = t <= limit;
    requirement = 'at or below ' + limit + ' F';
  } else if (kind === 'hot') {
    limit = pick('hot_min_f');
    passed = t >= limit;
    requirement = 'at or above ' + limit + ' F';
  } else {
    limit = pick('roast_hot_min_f');
    passed = t >= limit;
    requirement = 'at or above ' + limit + ' F (roast exception)';
  }

  const usedAnyOverride = Object.keys(usedOverride).length > 0;
  return {
    ok: true,
    holding_kind: kind,
    temperature_f: t,
    limit_f: limit,
    requirement: requirement,
    passed: passed,
    in_danger_zone: t > FDA_MODEL.cold_max_f && t < FDA_MODEL.hot_min_f,
    threshold_source: usedAnyOverride ? 'facility_configured' : 'fda_model_default',
    // Stated on every response, not buried in docs: the model code is not the law.
    source_note: usedAnyOverride
      ? 'Evaluated against this facility’s configured threshold.'
      : 'Evaluated against the FDA model Food Code default. The Food Code is a model adopted state by state — confirm your state’s adopted edition and any amendment before relying on this as your legal threshold.',
    authority: { citation: FDA_MODEL.source, url: FDA_MODEL.source_url }
  };
}

// Two-stage cooling. Each stage is checked independently because failing the
// first does not excuse the second, and a log that only records the end state
// cannot show which stage failed.
function evaluateCooling(opts) {
  opts = opts || {};
  const s1Hours = opts.stage1_hours;
  const s2Hours = opts.stage2_hours;
  const out = { ok: true, stages: [], authority: { citation: FDA_MODEL.source, url: FDA_MODEL.source_url } };
  if (s1Hours === undefined && s2Hours === undefined) {
    return refuse('NO_COOLING_DATA', 'At least one cooling stage duration is required.');
  }
  if (s1Hours !== undefined) {
    const h = Number(s1Hours);
    if (!isFinite(h) || h < 0) return refuse('BAD_STAGE1', 'stage1_hours must be a non-negative number.');
    out.stages.push({
      stage: 1, from_f: FDA_MODEL.cooling_stage1.from_f, to_f: FDA_MODEL.cooling_stage1.to_f,
      limit_hours: FDA_MODEL.cooling_stage1.hours, actual_hours: h, passed: h <= FDA_MODEL.cooling_stage1.hours
    });
  }
  if (s2Hours !== undefined) {
    const h = Number(s2Hours);
    if (!isFinite(h) || h < 0) return refuse('BAD_STAGE2', 'stage2_hours must be a non-negative number.');
    out.stages.push({
      stage: 2, from_f: FDA_MODEL.cooling_stage2.from_f, to_f: FDA_MODEL.cooling_stage2.to_f,
      limit_hours: FDA_MODEL.cooling_stage2.hours, actual_hours: h, passed: h <= FDA_MODEL.cooling_stage2.hours
    });
  }
  out.passed = out.stages.every((s) => s.passed);
  // Only claim a full-process pass when BOTH stages were actually recorded.
  out.complete = out.stages.length === 2;
  if (!out.complete) {
    out.note = 'Only one cooling stage was recorded, so this is not a complete two-stage cooling record.';
  }
  return out;
}

// Emergency-preparedness drills. There is NO universal ALF drill frequency --
// it varies by state and by drill type -- so the required interval is the
// facility's own configured policy and this function refuses to invent one.
function evaluateDrillDue(opts) {
  opts = opts || {};
  const last = opts.last_completed_on;
  const interval = opts.required_interval_days;
  const today = opts.today;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(today || ''))) {
    return refuse('BAD_TODAY', 'today must be YYYY-MM-DD');
  }
  if (interval === undefined || interval === null || interval === '' || !isFinite(Number(interval)) || Number(interval) <= 0) {
    return refuse('NO_INTERVAL_POLICY',
      'No drill interval is configured for this facility. Drill frequency varies by state and by drill type, so this app will not assume one — set the interval your state requires.');
  }
  if (!last) {
    return {
      ok: true, ever_completed: false, due: true, overdue_days: null,
      note: 'No drill of this type has ever been recorded, so it is due now. This is an absence of evidence, not a recorded failure.'
    };
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(last))) {
    return refuse('BAD_LAST_DATE', 'last_completed_on must be YYYY-MM-DD');
  }
  const days = Math.floor((Date.parse(today + 'T00:00:00Z') - Date.parse(last + 'T00:00:00Z')) / 86400000);
  const n = Number(interval);
  return {
    ok: true, ever_completed: true, last_completed_on: last,
    days_since: days, required_interval_days: n,
    due: days >= n, overdue_days: days > n ? days - n : 0
  };
}

// Roll-up for the panel: counts by type, failures, and what is unreviewed.
function summarise(records, opts) {
  opts = opts || {};
  const rows = records || [];
  const byType = {};
  ['food_temp', 'sanitation', 'emergency_drill'].forEach((t) => {
    const of = rows.filter((r) => r.record_type === t);
    byType[t] = {
      total: of.length,
      failed: of.filter((r) => r.passed === false).length,
      unreviewed: of.filter((r) => !r.reviewed_by).length
    };
  });
  return {
    total: rows.length,
    failed: rows.filter((r) => r.passed === false).length,
    unreviewed: rows.filter((r) => !r.reviewed_by).length,
    by_type: byType
  };
}

module.exports = { FDA_MODEL, evaluateFoodTemp, evaluateCooling, evaluateDrillDue, summarise };
