// api/_lib/roofing-asset-registry.js
// SAIRNroofing gap B1 -- the commercial roof asset registry.
//
// PURE -- no I/O, no LLM.
//
// ── WHY THIS IS A DIFFERENT DATA MODEL, NOT A BIGGER rf_jobs ─────────────
// The 2026-08-26 worldwide competitive-gap audit calls this "the single
// largest Tier B structural gap" and says why: an entire product category
// exists for it (Garland RAMP, Tecta TectaTracker, Nations Roof AM,
// RoofManager, Roof Hoss RoofTrack) and it is "completely absent from every
// Tier A product surveyed". The shape is many roofs per customer and one
// contractor servicing hundreds of buildings. rf_jobs is one job at a time.
// Bolting a portfolio onto it would have made every job row pretend to be a
// building.
//
// The audit's B2 is the commercial argument: the asset-registry tools are all
// commercial-owner / large-contractor products, so there is NO starter version
// a growing roofer can adopt when it wins its first maintenance-contract
// commercial customer. That is the whitespace this fills.
//
// ── WHAT IT REFUSES TO INVENT ────────────────────────────────────────────
// EXPECTED SERVICE LIFE IS NOT SEEDED. "TPO lasts 20 years" is real industry
// data and it is also wrong for a specific roof in a specific climate at a
// specific thickness, and a capital plan built on a number nobody entered is a
// budget presented to a building owner on the strength of a blog post. Same
// 2026-08-25 decision as roofing-programs.js and roofing-warranties.js: the
// contractor enters the figure with a source, and a section without one is
// reported as 'no_service_life_recorded' -- never given a default.
//
// CONDITION IS NOT FOLDED INTO REMAINING LIFE, and that is the sharper call.
// Every commercial product in this category quotes a single condition-adjusted
// "remaining service life", and the adjustment is a MODEL -- somebody's curve
// relating a 1-5 walk-over score to years. This engine does not have that model
// and will not invent one. It reports the calendar remaining life, reports the
// condition observation beside it, and FLAGS WHERE THE TWO DISAGREE (a roof
// scored poor with years left; a roof past its life still scoring good). The
// disagreement is the actionable fact, and it is honest in a way a single
// blended number is not.
//
// ── IT WILL NOT ASSUME A CLOCK ───────────────────────────────────────────
// Every entry point requires a caller-supplied `today`, same rule as
// subcontractor-compliance.js, roofing-warranties.js and roofing-crew-
// capacity.js's explicit range.

'use strict';

// A walk-over condition score. 1 is worst. Kept as a small ordinal rather than
// free text so "is this getting worse" is answerable later; kept to five points
// because that is what a roofer writes on a clipboard.
const CONDITION_SCORES = [1, 2, 3, 4, 5];
// Below this, a roof is called out regardless of its age.
const POOR_CONDITION_AT = 2;
// A section is "due soon" this many years out. A REVIEW WINDOW for planning,
// not an engineering figure -- callers override it.
const DEFAULT_HORIZON_YEARS = 5;

function isDate(s) { return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s); }
function str(v) { return typeof v === 'string' ? v.trim() : ''; }
function num(v) {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  return (typeof n === 'number' && isFinite(n)) ? n : null;
}
function yearsBetween(fromISO, toISO) {
  const a = Date.parse(fromISO + 'T00:00:00Z');
  const b = Date.parse(toISO + 'T00:00:00Z');
  if (!isFinite(a) || !isFinite(b)) return null;
  return (b - a) / (365.2425 * 86400000);
}
function round1(n) { return Math.round(n * 10) / 10; }

// ── One roof section ─────────────────────────────────────────────────────
function sectionState(input) {
  input = input || {};
  const today = isDate(input.today) ? input.today : null;
  if (!today) {
    return { ok: false, error: { code: 'NO_TODAY', message: 'today (YYYY-MM-DD) is required -- this engine will not assume a clock' } };
  }
  const s = input.section || null;
  if (!s) return { ok: false, error: { code: 'NO_SECTION', message: 'no roof section supplied' } };
  const horizon = num(input.horizon_years) === null ? DEFAULT_HORIZON_YEARS : num(input.horizon_years);

  const out = {
    ok: true,
    section_id: str(s.section_id) || null,
    building_id: str(s.building_id) || null,
    name: str(s.name) || null,
    system_type: str(s.system_type) || null,
    area_sqft: num(s.area_sqft),
    installed_on: isDate(s.installed_on) ? s.installed_on : null,
    expected_life_years: num(s.expected_life_years),
    life_source: str(s.life_source) || null,
    age_years: null,
    remaining_life_years: null,
    replacement_year: null,
    life_state: 'unknown',
    condition: null,
    condition_on: isDate(s.condition_on) ? s.condition_on : null,
    condition_state: 'not_inspected',
    flags: []
  };

  // ---- condition, on its own terms ----
  const score = num(s.condition_score);
  if (score !== null) {
    if (CONDITION_SCORES.indexOf(score) === -1) {
      out.flags.push('condition score "' + s.condition_score + '" is not one of ' + CONDITION_SCORES.join('/'));
    } else {
      out.condition = score;
      out.condition_state = score <= POOR_CONDITION_AT ? 'poor' : (score >= 4 ? 'good' : 'fair');
      if (!out.condition_on) {
        // A score with no date is an observation from an unknown time. Reported
        // rather than trusted -- a "good" from four years ago is not news.
        out.flags.push('condition recorded with no inspection date -- its age is unknown');
      }
    }
  }

  // ---- calendar life ----
  if (!out.installed_on) {
    out.life_state = 'no_install_date';
  } else {
    const age = yearsBetween(out.installed_on, today);
    out.age_years = age === null ? null : round1(age);
    if (out.expected_life_years === null || out.expected_life_years <= 0) {
      // REFUSES to guess. See the header: a capital plan built on an unentered
      // service life is a budget presented to an owner on the strength of a
      // blog post.
      out.life_state = 'no_service_life_recorded';
    } else if (!out.life_source) {
      // Same rule as an unsourced warranty tier. A number with no provenance
      // is not usable for a plan somebody will spend against.
      out.life_state = 'no_source_for_service_life';
      out.flags.push('an expected service life is recorded with no source -- name where it comes from before planning against it');
    } else {
      const remaining = out.expected_life_years - age;
      out.remaining_life_years = round1(remaining);
      out.replacement_year = Number(out.installed_on.slice(0, 4)) + out.expected_life_years;
      if (remaining < 0) out.life_state = 'past_expected_life';
      else if (remaining <= horizon) out.life_state = 'due_within_horizon';
      else out.life_state = 'within_life';
    }
  }

  // ---- where calendar and condition DISAGREE ----
  // The actionable fact, and the reason this engine does not blend them into
  // one number. Both directions matter and they mean opposite things.
  if (out.condition_state === 'poor' && out.life_state === 'within_life') {
    out.flags.push('scored poor but not near its expected replacement -- inspect before trusting the plan date');
  }
  if (out.condition_state === 'good' && out.life_state === 'past_expected_life') {
    out.flags.push('past its expected life but still scoring good -- the roof may outlast the figure entered');
  }
  if (out.condition_state === 'not_inspected' && out.life_state === 'past_expected_life') {
    out.flags.push('past its expected life and never inspected');
  }
  return out;
}

// ── The portfolio, by year ───────────────────────────────────────────────
// The capital/lifecycle forecast the audit names, and the thing no Tier A
// product surveyed does at all.
function portfolioForecast(input) {
  input = input || {};
  const today = isDate(input.today) ? input.today : null;
  if (!today) {
    return { ok: false, error: { code: 'NO_TODAY', message: 'today (YYYY-MM-DD) is required -- this engine will not assume a clock' } };
  }
  const horizon = num(input.horizon_years) === null ? DEFAULT_HORIZON_YEARS : num(input.horizon_years);
  const sections = Array.isArray(input.sections) ? input.sections : [];

  const evaluated = sections.map(function (s) {
    return sectionState({ section: s, today: today, horizon_years: horizon });
  }).filter(function (e) { return e.ok; });

  const byYear = Object.create(null);
  const unplannable = [];
  let plannedArea = 0, unplannableArea = 0;

  evaluated.forEach(function (e) {
    if (e.replacement_year === null) {
      unplannable.push({ section_id: e.section_id, building_id: e.building_id, reason: e.life_state });
      unplannableArea += (e.area_sqft || 0);
      return;
    }
    const y = byYear[e.replacement_year] || (byYear[e.replacement_year] = { year: e.replacement_year, sections: 0, area_sqft: 0, section_ids: [] });
    y.sections++;
    y.area_sqft += (e.area_sqft || 0);
    y.section_ids.push(e.section_id);
    plannedArea += (e.area_sqft || 0);
  });

  const years = Object.keys(byYear).map(function (k) { return byYear[k]; })
    .sort(function (a, b) { return a.year - b.year; });

  return {
    ok: true,
    today: today,
    horizon_years: horizon,
    sections_evaluated: evaluated.length,
    years: years,
    // NOT a footnote. A forecast that silently omits every section with no
    // service life recorded understates the capital plan by exactly the roofs
    // nobody has assessed -- which are the ones most likely to fail. The count
    // and the area are surfaced beside the totals, not below them.
    unplannable: unplannable,
    planned_area_sqft: Math.round(plannedArea),
    unplannable_area_sqft: Math.round(unplannableArea),
    overdue: evaluated.filter(function (e) { return e.life_state === 'past_expected_life'; })
      .map(function (e) { return e.section_id; }),
    due_within_horizon: evaluated.filter(function (e) { return e.life_state === 'due_within_horizon'; })
      .map(function (e) { return e.section_id; }),
    poor_condition: evaluated.filter(function (e) { return e.condition_state === 'poor'; })
      .map(function (e) { return e.section_id; })
  };
}

// ── Is this roof still under a manufacturer warranty? ────────────────────
// Cross-checks the registry against rf_job_warranties, which gap A1 built the
// same day. Matching is by an EXPLICIT warranty_id recorded on the section --
// never inferred from a shared address or a nearby date, because a wrong match
// here tells an owner a roof is covered when it is not.
function warrantyCoverage(input) {
  input = input || {};
  const today = isDate(input.today) ? input.today : null;
  if (!today) {
    return { ok: false, error: { code: 'NO_TODAY', message: 'today (YYYY-MM-DD) is required -- this engine will not assume a clock' } };
  }
  const sections = Array.isArray(input.sections) ? input.sections : [];
  const byId = Object.create(null);
  (Array.isArray(input.warranties) ? input.warranties : []).forEach(function (w) {
    const id = str(w && w.warranty_id);
    if (id) byId[id] = w;
  });

  const rows = sections.map(function (s) {
    const sid = str(s.section_id) || null;
    const wid = str(s.warranty_id) || null;
    if (!wid) return { section_id: sid, warranty_id: null, coverage: 'none_recorded' };
    const w = byId[wid];
    if (!w) {
      // Named a warranty that is not on file. Never 'covered' -- a typo must
      // not read as coverage.
      return { section_id: sid, warranty_id: wid, coverage: 'warranty_not_found' };
    }
    if (w.status === 'void') return { section_id: sid, warranty_id: wid, coverage: 'void' };
    const ends = isDate(w.coverage_expires_on) ? w.coverage_expires_on : null;
    if (!ends) return { section_id: sid, warranty_id: wid, coverage: 'no_end_date_recorded', status: w.status || null };
    return {
      section_id: sid, warranty_id: wid, expires_on: ends, status: w.status || null,
      coverage: ends < today ? 'expired' : 'active'
    };
  });

  return {
    ok: true,
    today: today,
    sections: rows,
    covered: rows.filter(function (r) { return r.coverage === 'active'; }).length,
    // Everything that is NOT a confident 'active', kept as one list because a
    // screen that has to check five states to find out what needs attention
    // grows a bug the first time a sixth is added.
    needs_attention: rows.filter(function (r) { return r.coverage !== 'active'; })
  };
}

module.exports = {
  CONDITION_SCORES,
  POOR_CONDITION_AT,
  DEFAULT_HORIZON_YEARS,
  sectionState,
  portfolioForecast,
  warrantyCoverage
};
