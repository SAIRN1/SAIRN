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
// ── FOUR OUTCOMES. THE LAST TWO ARE NOT OPTIONAL ─────────────────────────
//   meets_threshold      -- recorded density >= threshold, AND a photo that
//                           really exists on this claim backs the slope
//   below_threshold      -- recorded density < threshold
//   material_unavailable -- the shingle cannot be bought (see HARD TRIGGERS).
//                           Its OWN outcome as of 2026-08-26, no longer folded
//                           into meets_threshold: it is a fact about
//                           purchasability, not a measurement against the
//                           damage threshold. Collapsing the two made a supply
//                           fact read as "this slope met your hail threshold"
//                           -- which it did not, and which nobody measured.
//   insufficient_evidence -- the inputs needed to answer were not recorded, OR
//                           a count is not backed by a photo on this claim
//
// A missing test-square count is NOT a below_threshold. Silently treating
// "nobody measured this slope" as "this slope is fine" is the exact
// silent-failure class sairn-silent-failure-sweep exists for, and it would
// cost a contractor a slope they never inspected. There is no default verdict.
//
// ── HARD REPLACE TRIGGERS, SEPARATE FROM THE COUNT ───────────────────────
// Two conditions total a slope regardless of hit count, and both are facts
// rather than judgements:
//   discontinued_material -- the shingle cannot be bought, so a matching spot
//                            repair is not physically possible. Recorded by the
//                            contractor, cited like any other evidence. As of
//                            2026-08-26 this returns its OWN outcome,
//                            material_unavailable, NOT meets_threshold -- see
//                            the outcome list above. It is also EXEMPT from the
//                            strict photo rule, because a discontinued shingle
//                            is normally evidenced by a supplier or
//                            manufacturer letter rather than by a roof photo,
//                            and demanding the wrong artefact would push people
//                            to cite an unrelated one. Its evidence_gap still
//                            says when nothing is cited.
//   count-based wind damage on creased/missing shingles, against the same
//                            configured threshold, when the peril is wind --
//                            hail hits and wind creases are different physical
//                            evidence and are never summed together.

// ── THE PHOTO RULE IS STRICT, ADDED 2026-08-26 (Michael's call) ──────────
// A count only reaches meets_threshold if a photo THAT REALLY EXISTS ON THIS
// CLAIM backs the slope. Before this, `evidence_gap` was a string annotation
// and nothing more: a slope with 40 hits and zero photos still returned
// meets_threshold with a note beside it. A carrier does not read the note.
//
// The check is not "did the caller type some ids". The cited ids are matched
// against the real rf_claim_photos rows for this claim, read SERVER-SIDE by
// api/sd-data.js and passed in as `claim_photo_ids`. An id resolving to
// nothing comes back BY NAME in `unresolved_photo_ids` rather than being
// silently dropped -- same discipline Phase 3c established for the measured
// scope: a caller cannot supply their own evidence for a server-side finding.
//
// THE RULE BINDS meets_threshold ONLY, deliberately. below_threshold and
// insufficient_evidence do not support a claim, so an unbacked one costs
// nobody anything, and demanding a photo to say "we found little damage here"
// would only suppress honest reporting. material_unavailable is exempt for a
// different reason, stated at the trigger itself.
//
// BACKWARD COMPATIBILITY: when `claim_photo_ids` is not supplied at all, the
// cited ids are taken at face value and `photo_verified` is reported as null
// rather than false. A caller that cannot verify is told it did not, instead
// of every slope silently failing the new rule.
const OUTCOMES = ['meets_threshold', 'below_threshold', 'material_unavailable', 'insufficient_evidence'];
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
function assessSlope(slope, threshold, peril, claimPhotoIds) {
  const raw = Array.isArray(slope.photo_ids)
    ? slope.photo_ids.filter(function (p) { return p && String(p).trim(); }).map(function (p) { return String(p).trim(); })
    : [];
  // claimPhotoIds is the SERVER's list of photos really on this claim. When it
  // is absent the caller could not verify, which is reported rather than
  // treated as a failure -- see BACKWARD COMPATIBILITY above.
  const canVerify = Array.isArray(claimPhotoIds);
  const real = canVerify ? claimPhotoIds.map(function (p) { return String(p).trim(); }) : null;
  const cited = canVerify ? raw.filter(function (p) { return real.indexOf(p) !== -1; }) : raw;
  const unresolved = canVerify ? raw.filter(function (p) { return real.indexOf(p) === -1; }) : [];
  const photoVerified = canVerify ? cited.length > 0 : null;

  // A hard trigger is a physical fact about availability, not a damage count,
  // so it is evaluated first and does not need a test square to be recorded.
  if (slope.discontinued_material === true) {
    return {
      slope_label: slope.slope_label,
      // NOT meets_threshold. Nothing here was measured against the damage
      // threshold, and saying it was would overstate what is known.
      outcome: 'material_unavailable',
      basis: 'discontinued_material',
      reason: 'Recorded as discontinued material -- a matching spot repair is not purchasable. This is a supply fact and was NOT measured against the damage threshold.',
      counted: null,
      threshold: threshold.hits_per_test_square,
      threshold_source: threshold.source,
      photo_ids: cited,
      unresolved_photo_ids: unresolved,
      photo_verified: photoVerified,
      evidence_gap: cited.length ? null : 'No evidence cited for this slope -- a supplier or manufacturer letter is the usual proof that a shingle is discontinued.'
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
      unresolved_photo_ids: unresolved,
      photo_verified: photoVerified,
      evidence_gap: 'This slope has not been assessed. It is not a finding of low damage.'
    };
  }

  // Density, not raw total: 12 hits across 3 test squares is 4 per square, and
  // the convention is per square. Integer counts, real division, no rounding --
  // rounding 7.5 up to 8 would manufacture a total slope out of arithmetic.
  const perSquare = counted / slope.test_squares;
  const meets = perSquare >= threshold.hits_per_test_square;
  const density = Math.round(perSquare * 100) / 100;
  const arithmetic = counted + ' over ' + slope.test_squares + ' test square' +
    (slope.test_squares === 1 ? '' : 's') + ' = ' + density +
    ' per square, against a configured threshold of ' + threshold.hits_per_test_square + '.';

  // THE STRICT RULE. A count that clears the threshold but has no verified
  // photo behind it does NOT reach meets_threshold -- it is reported in full,
  // arithmetic and all, as insufficient_evidence. Suppressing the count would
  // hide real field work; scoring it would assert evidence this app cannot
  // show. Neither, so: state it and withhold the verdict.
  if (meets && photoVerified === false) {
    return {
      slope_label: slope.slope_label,
      outcome: 'insufficient_evidence',
      basis: null,
      reason: arithmetic + ' The threshold is met by the numbers, but no photo on this claim backs this slope, so it is not recorded as met.',
      counted: counted,
      per_test_square: density,
      threshold: threshold.hits_per_test_square,
      threshold_source: threshold.source,
      photo_ids: cited,
      unresolved_photo_ids: unresolved,
      photo_verified: false,
      evidence_gap: unresolved.length
        ? 'The photo ids cited are not on this claim: ' + unresolved.join(', ') + '.'
        : 'No photo cited for this slope -- a count with no evidence behind it is not recorded as meeting the threshold.'
    };
  }

  return {
    slope_label: slope.slope_label,
    outcome: meets ? 'meets_threshold' : 'below_threshold',
    basis: peril === 'wind' ? 'creased_or_missing_per_test_square' : 'hits_per_test_square',
    reason: arithmetic,
    counted: counted,
    per_test_square: density,
    threshold: threshold.hits_per_test_square,
    threshold_source: threshold.source,
    photo_ids: cited,
    unresolved_photo_ids: unresolved,
    photo_verified: photoVerified,
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

  const assessed = slopes.map(function (s) { return assessSlope(s, input.threshold, peril, input.claim_photo_ids); });
  const counts = { meets_threshold: 0, below_threshold: 0, material_unavailable: 0, insufficient_evidence: 0 };
  assessed.forEach(function (a) { counts[a.outcome]++; });

  return {
    ok: true,
    problems: [],
    peril: peril,
    threshold: { hits_per_test_square: input.threshold.hits_per_test_square, source: input.threshold.source },
    threshold_is_override: !!(input && input.threshold_is_override),
    slopes: assessed,
    photo_verification: Array.isArray(input.claim_photo_ids) ? 'server_verified' : 'not_verified',
    summary: {
      slopes_total: assessed.length,
      meets_threshold: counts.meets_threshold,
      below_threshold: counts.below_threshold,
      material_unavailable: counts.material_unavailable,
      insufficient_evidence: counts.insufficient_evidence,
      // Deliberately NOT a roof-level verdict. There is no "this roof is
      // totalled" field and there must not be one -- carriers total slopes,
      // and a roof-level yes/no is the sentence this engine may not say.
      unassessed_slopes_remain: counts.insufficient_evidence > 0
    }
  };
}

module.exports = { OUTCOMES, PERILS, validateThreshold, validateSlope, assessSlope, assess };
