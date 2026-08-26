// api/_lib/roofing-damage-assessment.js
// SAIRNroofing -- per-slope repair-vs-replace evidence assessment.
//
// PURE -- no I/O, same contract as roofing-supplement.js.
//
// ── WHAT THIS IS, AND THE SENTENCE IT MUST NEVER SAY ─────────────────────
// This does NOT decide whether a roof gets replaced. The carrier decides that.
// This states, per slope, whether the evidence the contractor actually
// recorded meets a threshold the contractor actually configured -- and shows
// the threshold and its source next to the answer so the reader can check it.
//
// The distinction is not pedantry, it is the same public-adjuster boundary
// roofing-supplement.js documents at length (Tex. Ins. Code 4102.163, Fla.
// Stat. 626.854, and equivalents): a roofing contractor may not act as a
// public adjuster for property they are servicing. "Your test squares record
// 9 hits against your configured threshold of 8" is a factual statement about
// the contractor's own measurements. "This roof should be replaced" or "the
// carrier owes you a replacement" is an opinion about coverage, and saying it
// is the thing the statute prohibits.
//
// So the outcome vocabulary below is deliberately about EVIDENCE, never about
// entitlement, and every user-facing string in the client repeats that.
//
// ── WHY A THRESHOLD IS CONFIGURED AND NEVER HARDCODED ────────────────────
// The widely-cited convention is 8 or more hail hits in a 10x10 ft test square
// totalling that slope. It is a convention, not a law: it varies by carrier,
// by state, and by policy, and some carriers publish their own. Hardcoding a
// number would be exactly the fabricated-authority pattern Guardian Check 0b
// exists to catch -- a number on screen with nothing real behind it. So the
// threshold is a required, per-company setting carrying its own `source`
// string, and this engine REFUSES to assess rather than assume one.
//
// ── THREE OUTCOMES. THE THIRD IS NOT OPTIONAL ────────────────────────────
//   meets_threshold      -- recorded hits >= threshold, or a hard replace
//                           trigger fired (see below)
//   below_threshold      -- recorded hits < threshold, and no trigger fired
//   insufficient_evidence -- the inputs needed to answer were not recorded
//
// A missing test-square count is NOT a below_threshold. Silently treating
// "nobody measured this slope" as "this slope is fine" is the exact
// silent-failure class sairn-silent-failure-sweep exists for, and it would
// cost a contractor a slope they never inspected. There is no default verdict.
//
// ── HARD REPLACE TRIGGERS, SEPARATE FROM THE COUNT ───────────────────────
// Two conditions total a slope regardless of hit count, and both are facts
// rather than judgements:
//   discontinued_material -- the shingle cannot be bought, so a spot repair is
//                            not physically possible. Recorded by the
//                            contractor, cited like any other evidence.
//   count-based wind damage on creased/missing shingles, against the same
//                            configured threshold, when the peril is wind --
//                            hail hits and wind creases are different physical
//                            evidence and are never summed together.

const OUTCOMES = ['meets_threshold', 'below_threshold', 'insufficient_evidence'];
const PERILS = ['hail', 'wind'];

// A test square is the industry's unit of measure for hail density: a 10x10 ft
// area of a single slope. Recorded per slope, not per roof, because carriers
// total individual slopes and a roof is routinely replace on one and repair on
// the other three.
function isPositiveInt(v) {
  return typeof v === 'number' && isFinite(v) && v >= 0 && Math.floor(v) === v;
}

function validateThreshold(t) {
  const problems = [];
  if (!t || typeof t !== 'object') { return ['no damage threshold is configured for this company']; }
  if (!isPositiveInt(t.hits_per_test_square) || t.hits_per_test_square < 1) {
    problems.push('hits_per_test_square must be a whole number of 1 or more');
  }
  if (!t.source || String(t.source).trim().length < 3) {
    // The source is required for the same reason the supplement engine requires
    // a photo citation on an asserted line: a threshold with no traceable
    // origin is indistinguishable from a guess once whoever configured it has
    // moved on, and this one decides whether a slope is called total.
    problems.push('source is required -- name the carrier bulletin, state guidance or company standard this number comes from');
  }
  return problems;
}

function validateSlope(s, i) {
  const problems = [];
  const where = 'slope ' + (i + 1) + (s && s.slope_label ? ' (' + s.slope_label + ')' : '');
  if (!s || typeof s !== 'object') return [where + ': not an object'];
  if (!s.slope_label || !String(s.slope_label).trim()) problems.push(where + ': slope_label is required');
  if (s.test_squares !== undefined && s.test_squares !== null && !isPositiveInt(s.test_squares)) {
    problems.push(where + ': test_squares must be a whole number');
  }
  if (s.hits !== undefined && s.hits !== null && !isPositiveInt(s.hits)) {
    problems.push(where + ': hits must be a whole number');
  }
  if (s.creased_or_missing !== undefined && s.creased_or_missing !== null && !isPositiveInt(s.creased_or_missing)) {
    problems.push(where + ': creased_or_missing must be a whole number');
  }
  return problems;
}

// Per-slope assessment. `peril` selects WHICH recorded count is compared --
// never both, never their sum.
function assessSlope(slope, threshold, peril) {
  const cited = Array.isArray(slope.photo_ids)
    ? slope.photo_ids.filter(function (p) { return p && String(p).trim(); })
    : [];

  // A hard trigger is a physical fact about availability, not a damage count,
  // so it is evaluated first and does not need a test square to be recorded.
  if (slope.discontinued_material === true) {
    return {
      slope_label: slope.slope_label,
      outcome: 'meets_threshold',
      basis: 'discontinued_material',
      reason: 'Recorded as discontinued material -- a matching spot repair is not purchasable.',
      counted: null,
      threshold: threshold.hits_per_test_square,
      threshold_source: threshold.source,
      photo_ids: cited,
      evidence_gap: cited.length ? null : 'No photo cited for this slope.'
    };
  }

  const countKey = peril === 'wind' ? 'creased_or_missing' : 'hits';
  const counted = slope[countKey];
  const haveCount = isPositiveInt(counted);
  const haveSquares = isPositiveInt(slope.test_squares) && slope.test_squares > 0;

  if (!haveCount || !haveSquares) {
    const missing = [];
    if (!haveSquares) missing.push('test squares inspected');
    if (!haveCount) missing.push(peril === 'wind' ? 'creased or missing shingle count' : 'hail hit count');
    return {
      slope_label: slope.slope_label,
      outcome: 'insufficient_evidence',
      basis: null,
      reason: 'Not enough recorded to answer: ' + missing.join(' and ') + ' missing.',
      counted: haveCount ? counted : null,
      threshold: threshold.hits_per_test_square,
      threshold_source: threshold.source,
      photo_ids: cited,
      evidence_gap: 'This slope has not been assessed. It is not a finding of low damage.'
    };
  }

  // Density, not raw total: 12 hits across 3 test squares is 4 per square, and
  // the convention is per square. Integer counts, real division, no rounding --
  // rounding 7.5 up to 8 would manufacture a total slope out of arithmetic.
  const perSquare = counted / slope.test_squares;
  const meets = perSquare >= threshold.hits_per_test_square;
  return {
    slope_label: slope.slope_label,
    outcome: meets ? 'meets_threshold' : 'below_threshold',
    basis: peril === 'wind' ? 'creased_or_missing_per_test_square' : 'hits_per_test_square',
    reason: counted + ' over ' + slope.test_squares + ' test square' + (slope.test_squares === 1 ? '' : 's') +
      ' = ' + (Math.round(perSquare * 100) / 100) + ' per square, against a configured threshold of ' +
      threshold.hits_per_test_square + '.',
    counted: counted,
    per_test_square: Math.round(perSquare * 100) / 100,
    threshold: threshold.hits_per_test_square,
    threshold_source: threshold.source,
    photo_ids: cited,
    evidence_gap: cited.length ? null : 'No photo cited for this slope -- the count is unsupported by evidence in this app.'
  };
}

// assess({ slopes, threshold, peril, threshold_is_override })
// Returns { ok, problems, peril, threshold, slopes, summary } -- and REFUSES
// (ok:false) rather than returning a partial answer, matching how
// deadline-engine.js's resolvePeriods refuses instead of guessing.
function assess(input) {
  const problems = [];
  const peril = input && input.peril;
  if (PERILS.indexOf(peril) === -1) {
    problems.push('peril must be one of: ' + PERILS.join(', ') + ' -- hail hits and wind creases are different evidence and are never combined');
  }
  problems.push.apply(problems, validateThreshold(input && input.threshold));
  const slopes = (input && Array.isArray(input.slopes)) ? input.slopes : [];
  if (!slopes.length) problems.push('at least one slope row is required');
  slopes.forEach(function (s, i) { problems.push.apply(problems, validateSlope(s, i)); });

  if (problems.length) {
    return { ok: false, problems: problems, slopes: [], summary: null };
  }

  const assessed = slopes.map(function (s) { return assessSlope(s, input.threshold, peril); });
  const counts = { meets_threshold: 0, below_threshold: 0, insufficient_evidence: 0 };
  assessed.forEach(function (a) { counts[a.outcome]++; });

  return {
    ok: true,
    problems: [],
    peril: peril,
    threshold: { hits_per_test_square: input.threshold.hits_per_test_square, source: input.threshold.source },
    threshold_is_override: !!(input && input.threshold_is_override),
    slopes: assessed,
    summary: {
      slopes_total: assessed.length,
      meets_threshold: counts.meets_threshold,
      below_threshold: counts.below_threshold,
      insufficient_evidence: counts.insufficient_evidence,
      // Deliberately NOT a roof-level verdict. There is no "this roof is
      // totalled" field and there must not be one -- carriers total slopes,
      // and a roof-level yes/no is the sentence this engine may not say.
      unassessed_slopes_remain: counts.insufficient_evidence > 0
    }
  };
}

module.exports = { OUTCOMES, PERILS, validateThreshold, validateSlope, assessSlope, assess };
