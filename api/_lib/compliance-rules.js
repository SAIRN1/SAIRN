// api/_lib/compliance-rules.js
// SAIRNcare Phase 2 compliance-rules engine.
//
// PURE -- no I/O. Same shape and same reasoning as api/_lib/payer-routing.js
// (Phase 1) and api/_lib/deadline-engine.js: rules arrive as versioned data,
// this module only evaluates them, so every branch is testable against the
// administrative-code text without a database.
//
// FAILS CLOSED. An unseeded state gets NO_RULE_FOR_STATE naming the state; an
// unseeded facility class within a seeded state gets NO_RULE_FOR_CLASS naming
// the class. Neither is ever silently substituted with another state's or
// another class's numbers -- Pennsylvania's two chapters and Michigan's two
// licence classes carry genuinely different figures, so a substitution would
// produce a confident wrong answer rather than an honest gap.
//
// THERE IS NO DEFAULT STAFFING METHOD, deliberately. The four seeded states use
// four incompatible methods (percentage uplift / census thresholds / fixed
// ratio by shift / service-hours per resident per day). evaluateStaffing()
// dispatches on the rule's declared method and REFUSES an unknown one rather
// than falling through to a "most common" shape -- there is no most-common
// shape, and inventing one is how three of four states get quietly mis-checked.

'use strict';

function refuse(code, message, extra) {
  return Object.assign({ ok: false, error: { code: code, message: message } }, extra || {});
}

function ruleInForce(rule, onDate) {
  if (!rule || !rule.effective_from) return false;
  if (rule.status && rule.status !== 'active') return false;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(onDate || '')) return false;
  if (rule.effective_from > onDate) return false;
  if (rule.effective_to && rule.effective_to < onDate) return false;
  return true;
}

// Select the one rule matching state + requirement type (+ facility class).
// A rule with facility_class null applies to every class in that state.
function selectRule(rules, opts) {
  const state = String(opts.state || '').toUpperCase();
  const type = opts.requirement_type;
  const cls = opts.facility_class || null;
  const onDate = opts.on_date;

  const inState = (rules || []).filter((r) => String(r.state || '').toUpperCase() === state);
  if (!inState.length) {
    return refuse('NO_RULE_FOR_STATE',
      'No compliance rules are loaded for ' + (state || '(no state given)') +
      '. This state is not covered — do not rely on this app for its requirements until real, sourced rules are loaded.');
  }
  const ofType = inState.filter((r) => r.requirement_type === type);
  if (!ofType.length) {
    return refuse('NO_RULE_FOR_TYPE',
      'No ' + type + ' rule is loaded for ' + state + '.');
  }
  const inForce = ofType.filter((r) => ruleInForce(r, onDate));
  if (!inForce.length) {
    return refuse('NO_RULE_IN_FORCE',
      'No ' + state + ' ' + type + ' rule was in force on ' + onDate + '.');
  }
  // Prefer an exact class match; fall back to a class-agnostic rule.
  const exact = inForce.filter((r) => r.facility_class === cls);
  const agnostic = inForce.filter((r) => !r.facility_class);
  const chosen = exact.length ? exact : agnostic;
  if (!chosen.length) {
    return refuse('NO_RULE_FOR_CLASS',
      'No ' + state + ' ' + type + ' rule is loaded for facility class "' + (cls || '(none given)') +
      '". ' + state + ' regulates classes that carry different figures, so another class’s rule is not applied in its place. Covered classes: ' +
      inForce.map((r) => r.facility_class || '(any)').join(', '));
  }
  if (chosen.length > 1) {
    return refuse('AMBIGUOUS_RULE',
      'More than one ' + state + ' ' + type + ' rule is in force for this class on ' + onDate + ': ' +
      chosen.map((r) => r.rule_id).join(', ') + '. Narrow the effective dates so exactly one applies.');
  }
  return { ok: true, rule: chosen[0] };
}

// ── STAFFING ─────────────────────────────────────────────────────────────
// Returns the REQUIREMENT, and where enough facts were supplied, whether the
// facility meets it. It never guesses a missing input: an absent census or an
// absent baseline ratio produces an explicit "cannot evaluate" naming what is
// missing, not a pass.
function evaluateStaffing(rules, opts) {
  opts = opts || {};
  const sel = selectRule(rules, {
    state: opts.state, requirement_type: 'staffing',
    facility_class: opts.facility_class, on_date: opts.on_date
  });
  if (!sel.ok) return sel;
  const rule = sel.rule;
  const d = rule.data || {};
  const base = {
    ok: true, state: rule.state, rule_id: rule.rule_id,
    facility_class: rule.facility_class, method: d.method,
    label: d.label, authority: d.authority || null
  };

  if (d.method === 'fixed_ratio') {
    const req = Math.ceil((Number(opts.census) || 0) / d.per_residents);
    if (!opts.census) return Object.assign({}, base, { evaluated: false, missing: ['census'], requirement: describeFixed(d) });
    return Object.assign({}, base, {
      evaluated: true, requirement: describeFixed(d),
      required_staff: req, actual_staff: numOrNull(opts.direct_care_staff),
      meets: opts.direct_care_staff == null ? null : Number(opts.direct_care_staff) >= req,
      exclusion: d.exclusion || null
    });
  }

  if (d.method === 'fixed_ratio_by_shift') {
    const shift = opts.shift;
    if (!shift) {
      return Object.assign({}, base, {
        evaluated: false, missing: ['shift'],
        requirement: (d.shifts || []).map(describeFixed).join('; '),
        note: 'This state’s requirement differs by shift, so the shift must be stated — there is no single number that is correct for both.'
      });
    }
    const spec = (d.shifts || []).find((s) => s.shift === shift);
    if (!spec) {
      return refuse('UNKNOWN_SHIFT',
        'Shift "' + shift + '" is not one this rule defines. Defined: ' + (d.shifts || []).map((s) => s.shift).join(', '));
    }
    if (!opts.census) return Object.assign({}, base, { evaluated: false, missing: ['census'], requirement: describeFixed(spec), shift: shift });
    const req = Math.ceil(Number(opts.census) / spec.per_residents);
    return Object.assign({}, base, {
      evaluated: true, shift: shift, requirement: describeFixed(spec),
      required_staff: req, actual_staff: numOrNull(opts.direct_care_staff),
      meets: opts.direct_care_staff == null ? null : Number(opts.direct_care_staff) >= req,
      exclusion: d.exclusion || null
    });
  }

  if (d.method === 'percentage_uplift_with_fallback') {
    // Ohio. Which branch applies is a fact about the provider, not something
    // derivable from a census, so it must be supplied.
    const memoryOnly = opts.memory_care_only;
    const benchmark = opts.benchmark_ratio_available;
    if (memoryOnly == null) {
      return Object.assign({}, base, {
        evaluated: false, missing: ['memory_care_only'],
        branches: d.branches,
        note: 'Ohio’s requirement depends on whether this provider offers memory care alongside the basic service, or memory care only.'
      });
    }
    let branch;
    if (!memoryOnly) branch = d.branches[0];
    else if (benchmark == null) {
      return Object.assign({}, base, {
        evaluated: false, missing: ['benchmark_ratio_available'], branches: d.branches,
        note: 'A memory-care-only provider must use 20% above the Medicaid-program benchmark average WHENEVER that average is readily available. The fixed 1:10 ratio is only the fallback when it is not — so this question has to be answered before the requirement is known.'
      });
    } else branch = benchmark ? d.branches[1] : d.branches[2];

    if (branch.rule === 'fixed_ratio') {
      if (!opts.census) return Object.assign({}, base, { evaluated: false, missing: ['census'], branch: branch, requirement: describeFixed(branch) });
      const req = Math.ceil(Number(opts.census) / branch.per_residents);
      return Object.assign({}, base, {
        evaluated: true, branch: branch, requirement: describeFixed(branch),
        required_staff: req, actual_staff: numOrNull(opts.direct_care_staff),
        meets: opts.direct_care_staff == null ? null : Number(opts.direct_care_staff) >= req,
        additional: branch.additional || null, clinical_coverage: d.clinical_coverage || null
      });
    }
    // Uplift branches need the baseline ratio they uplift FROM.
    const baseline = opts.baseline_ratio_per_staff; // residents per 1 staff
    if (baseline == null) {
      return Object.assign({}, base, {
        evaluated: false, missing: ['baseline_ratio_per_staff'], branch: branch,
        requirement: 'At least ' + branch.uplift_percent + '% higher than ' +
          (branch.rule === 'uplift_over_own_basic_ratio' ? 'this provider’s own basic-service ratio' : 'the benchmark average ratio'),
        note: 'A percentage uplift cannot be computed without the baseline ratio it applies to. This app will not assume one.'
      });
    }
    // "20% higher ratio" means 20% more staff per resident, i.e. the residents
    // covered per staff member falls by the same factor.
    const upliftedPerStaff = Number(baseline) / (1 + (branch.uplift_percent / 100));
    const out = Object.assign({}, base, {
      evaluated: true, branch: branch,
      baseline_residents_per_staff: Number(baseline),
      required_residents_per_staff: Math.round(upliftedPerStaff * 100) / 100,
      requirement: 'At least ' + branch.uplift_percent + '% higher than a ratio of 1 staff per ' + baseline + ' residents',
      clinical_coverage: d.clinical_coverage || null
    });
    if (opts.census) {
      out.required_staff = Math.ceil(Number(opts.census) / upliftedPerStaff);
      out.actual_staff = numOrNull(opts.direct_care_staff);
      out.meets = opts.direct_care_staff == null ? null : Number(opts.direct_care_staff) >= out.required_staff;
    }
    return out;
  }

  if (d.method === 'census_thresholds') {
    // Indiana. Not a ratio -- a set of conditions that switch on at census
    // bands. Every threshold is reported, with which ones are triggered.
    const census = opts.nursing_service_census != null ? Number(opts.nursing_service_census) : null;
    const triggered = (d.thresholds || []).map((t) => {
      let applies = null;
      if (t.census_threshold == null) applies = true; // "at all times"
      else if (census != null) applies = census >= t.census_threshold;
      const row = { requirement: t.requirement, applies: applies };
      if (t.additional_staff_per_residents && census != null && applies) {
        // "one additional for every additional 50 residents" above the threshold.
        row.additional_staff_required = Math.ceil((census - t.census_threshold) / t.additional_staff_per_residents);
      }
      if (t.must_hold) row.must_hold = t.must_hold;
      if (t.must_be_awake) row.must_be_awake = true;
      return row;
    });
    return Object.assign({}, base, {
      evaluated: census != null,
      missing: census == null ? ['nursing_service_census'] : [],
      note: 'Indiana sets no per-resident ratio, but these numeric threshold requirements are real and enforceable.',
      thresholds: triggered
    });
  }

  if (d.method === 'service_hours_per_resident_per_day') {
    // Pennsylvania. Total required service hours, not a headcount.
    const mobile = opts.mobile_residents;
    const mobilityNeeds = opts.mobility_needs_residents;
    const scu = Number(opts.scu_residents || 0);
    if (mobile == null || mobilityNeeds == null) {
      return Object.assign({}, base, {
        evaluated: false, missing: ['mobile_residents', 'mobility_needs_residents'],
        requirement: (d.hours_per_resident_per_day || []).map((h) => h.hours + ' hr/day per ' + h.resident_type.replace('_', ' ') + ' resident').join('; '),
        waking_hours_minimum_percent: d.waking_hours_minimum_percent,
        note: 'Pennsylvania measures service HOURS per resident per day, not a staff-to-resident headcount ratio.'
      });
    }
    const rateFor = (type) => {
      const row = (d.hours_per_resident_per_day || []).find((h) => h.resident_type === type);
      return row ? row.hours : 0;
    };
    // Every SCU resident counts as having mobility needs regardless of actual
    // mobility -- a real rule (§ 2800.238) that is easy to miss and always
    // increases the requirement.
    const effectiveMobilityNeeds = Number(mobilityNeeds) + scu;
    const totalHours = (Number(mobile) * rateFor('mobile')) + (effectiveMobilityNeeds * rateFor('mobility_needs'));
    const wakingHours = Math.ceil(totalHours * (d.waking_hours_minimum_percent / 100) * 100) / 100;
    return Object.assign({}, base, {
      evaluated: true,
      mobile_residents: Number(mobile),
      mobility_needs_residents: Number(mobilityNeeds),
      scu_residents: scu,
      scu_counted_as_mobility_needs: scu > 0 ? scu : 0,
      effective_mobility_needs_residents: effectiveMobilityNeeds,
      required_service_hours_per_day: Math.round(totalHours * 100) / 100,
      minimum_hours_during_waking: wakingHours,
      waking_hours_minimum_percent: d.waking_hours_minimum_percent,
      actual_service_hours_per_day: numOrNull(opts.actual_service_hours),
      meets: opts.actual_service_hours == null ? null : Number(opts.actual_service_hours) >= totalHours,
      always_present: d.always_present || null,
      awake_requirement: d.awake_requirement || null,
      // Added with the PCH rule (2026-08-23). Pennsylvania's two chapters do NOT
      // share an awake rule: the ALR one is unconditional, the PCH one branches
      // on total census (16+) versus mobility-needs count (under 16). This
      // engine reports the PCH branches rather than picking one, because
      // choosing needs both counts as of the moment in question and a wrong
      // branch is a real staffing violation in either direction. The flag says
      // plainly that no evaluation happened, so an unevaluated rule cannot read
      // as a passed one.
      awake_rule_is_conditional: !!d.awake_rule_is_conditional,
      awake_rule_note: d.awake_rule_note || null,
      scu_mobility_rule: d.scu_mobility_rule || null,
      multiple_buildings: d.multiple_buildings || null,
      first_aid_cpr_coverage: d.first_aid_cpr_coverage || null,
      additional_staffing: d.additional_staffing || null
    });
  }

  // ── WEST VIRGINIA: A FIFTH METHOD, AND IT IS NOT A RATIO (2026-09-25) ────
  // 64 CSR 14 § 4.4.1 sets a FLOOR of one direct care staff person 24 hours a
  // day, and 4.4.1.a/b/c then add staff ON TOP of that one, per shift.
  //
  // THE DENOMINATOR IS THE TRAP, and the widely-circulated summary of this
  // rule gets it wrong. Every secondary source renders it "Day 1:10, Evening
  // 1:15, Night 1:18" as if it were a census ratio. The code text is not that:
  // each additional staff member is required "for each 10 residents IDENTIFIED
  // ON THEIR NEEDS ASSESSMENTS TO HAVE TWO OR MORE" of the listed care needs.
  // A 30-bed residence where four residents meet that test needs the baseline
  // one plus one on days -- not three. Driving this off `census` would have
  // over-stated the requirement for almost every real facility, and the
  // over-statement would have looked conservative and therefore safe.
  //
  // SO THE SPECIAL-NEEDS COUNT IS ASKED FOR AND NEVER SUBSTITUTED. A caller
  // who supplies only a census gets `missing`, not an answer computed off the
  // wrong number. That is the same refusal `shift` already gets above.
  if (d.method === 'baseline_plus_special_needs_by_shift') {
    const shift = opts.shift;
    const missing = [];
    if (!shift) missing.push('shift');
    const special = opts.special_care_needs_residents;
    if (special === null || special === undefined || special === '') {
      missing.push('special_care_needs_residents');
    }
    const describe = function () {
      return String(d.baseline_staff) + ' direct care staff on duty at all times, PLUS 1 more '
        + 'per shift for each N residents assessed with two or more special care needs ('
        + (d.shifts || []).map(function (s) {
            return s.shift + ': 1 per ' + s.per_special_needs_residents;
          }).join('; ') + ')';
    };
    if (missing.length) {
      return Object.assign({}, base, {
        evaluated: false, missing: missing, requirement: describe(),
        note: 'This state counts the ADDITIONAL staff against residents assessed with two '
          + 'or more special care needs, not against the census. A census cannot stand in '
          + 'for that count -- it would over-state the requirement for most facilities, and '
          + 'an over-statement is still a wrong number.'
      });
    }
    const spec = (d.shifts || []).find(function (s) { return s.shift === shift; });
    if (!spec) {
      return refuse('UNKNOWN_SHIFT',
        'Shift "' + shift + '" is not one this rule defines. Defined: '
        + (d.shifts || []).map(function (s) { return s.shift; }).join(', '));
    }
    const extra = Math.ceil(Number(special) / spec.per_special_needs_residents);
    const req = Number(d.baseline_staff) + extra;
    return Object.assign({}, base, {
      evaluated: true, shift: shift, requirement: describe(),
      baseline_staff: Number(d.baseline_staff),
      additional_for_special_needs: extra,
      special_care_needs_residents: Number(special),
      required_staff: req, actual_staff: numOrNull(opts.direct_care_staff),
      meets: opts.direct_care_staff == null ? null : Number(opts.direct_care_staff) >= req,
      exclusion: d.exclusion || null,
      // The list is part of the rule: which needs count is not this app's to
      // decide, and a facility applying a different list gets a different
      // answer for reasons nothing here would show.
      special_care_needs: d.special_care_needs || null
    });
  }

  return refuse('UNKNOWN_METHOD',
    'Staffing method "' + d.method + '" is not one this engine implements. It will not fall back to another state’s method.');
}

function describeFixed(spec) {
  return '1 direct care staff per ' + spec.per_residents + ' residents' + (spec.shift ? ' (' + spec.shift + ' hours)' : '');
}
function numOrNull(v) { return v == null ? null : Number(v); }

// ── TRAINING ─────────────────────────────────────────────────────────────
// Returns the requirements that apply, and if credential records are supplied,
// which staff fall short. Hours are compared against real recorded rows only --
// a staff member with no records is reported as having none, never assumed
// compliant.
function evaluateTraining(rules, opts) {
  opts = opts || {};
  const sel = selectRule(rules, {
    state: opts.state, requirement_type: 'training',
    facility_class: opts.facility_class, on_date: opts.on_date
  });
  if (!sel.ok) return sel;
  const rule = sel.rule;
  const d = rule.data || {};

  if (d.structure === 'no_state_mandated_hours') {
    // Michigan. Reporting a zero here would read as "0 hours required, you're
    // compliant"; reporting a number would invent a mandate. Neither. The
    // distinction between "no state floor" and "no requirement" is the point.
    return {
      ok: true, state: rule.state, rule_id: rule.rule_id,
      structure: d.structure,
      state_mandated: false,
      requirements: [],
      label: d.label,
      notes: d.notes || [],
      facility_defined_target_hours: opts.facility_defined_target_hours != null ? Number(opts.facility_defined_target_hours) : null,
      note: 'This state sets no dementia-training hour floor. Any target tracked here is the facility’s own policy and is labelled as such — it is not a state mandate.',
      authority: d.authority || null
    };
  }

  const reqs = d.requirements || [];
  const out = {
    ok: true, state: rule.state, rule_id: rule.rule_id,
    structure: d.structure, state_mandated: true,
    label: d.label, requirements: reqs, authority: d.authority || null
  };

  // ── OPTIONAL PER-STAFF EVALUATION, AND IT USED TO FABRICATE A PASS ────────
  // DRIVEN 2026-09-26, not reasoned about. Asking this branch for a West
  // Virginia finding on a staff member with ZERO recorded hours returned:
  //
  //   { required_annual_hours: 0, recorded_annual_hours: 0, shortfall_hours: 0,
  //     meets: TRUE, applicable_requirements: [null, null] }
  //
  // In a state that mandates 8 hours a year for an administrator and 2 hours a
  // year of dementia training for ALL staff. The `[null, null]` is the tell:
  // WV's rows are `{audience, hours_per_year, topic}` and this code reads
  // `r.who` and `r.annual_hours`, so every requirement contributed
  // `Number(undefined) || 0`. A DIFFERENT VOCABULARY READ AS AN EMPTY ONE, and
  // an empty requirement set is indistinguishable from a satisfied one once it
  // has been summed.
  //
  // It has never fired: nothing in sairncare.html passes `opts.staff` --
  // cqShowTraining() sends {state, facility_class, requirement_type} and
  // nothing else -- so this whole branch is dormant. That is the only reason
  // the fabricated pass has not reached a screen, and it is not a reason to
  // leave it: the open request that surfaced this is to BUILD the caller.
  //
  // TWO REFUSALS NOW, BOTH FAIL-CLOSED, matching this module's own standard --
  // "neither is ever silently substituted ... a substitution would produce a
  // confident wrong answer rather than an honest gap".
  if (Array.isArray(opts.staff)) {
    // (1) AN UNRECOGNISED REQUIREMENT VOCABULARY IS REFUSED, NEVER SUMMED.
    // A row is recognised if it carries EITHER key this branch reads. An
    // initial-only row (`who` + `initial_hours`, no `annual_hours`) is
    // recognised and correctly contributes zero to an ANNUAL total -- that is
    // a real Ohio row and must keep working. What is refused is a row carrying
    // NEITHER, which means this code cannot see it at all.
    const unreadable = reqs.filter(function (r) {
      return !r || (r.who === undefined && r.annual_hours === undefined);
    });
    if (unreadable.length) {
      return refuse('REQUIREMENTS_NOT_JOINABLE',
        'This state\'s training requirements are not in a shape the per-staff '
        + 'check can read, so no staff finding is produced. ' + unreadable.length
        + ' of ' + reqs.length + ' requirement(s) in rule ' + rule.rule_id
        + ' (' + rule.state + ') carry neither `who` nor `annual_hours`. '
        + 'Summing them would report every staff member as meeting a '
        + 'requirement this code never read.',
        { state: rule.state, rule_id: rule.rule_id,
          unreadable_requirement_keys: unreadable.map(function (r) {
            return Object.keys(r || {}).sort();
          }) });
    }
    // (2) A REQUIREMENT SET WITH STACKING SEMANTICS CANNOT BE SUMMED, AND IT
    //     IS WRONG IN BOTH DIRECTIONS.
    // Two machine-readable fields on the real seeded rows say that plain
    // addition is not the arithmetic:
    //
    //   additive: true                  Pennsylvania. A secured-dementia-unit
    //                                   requirement ON TOP OF the general
    //                                   annual hours. Summing both into one
    //                                   target and comparing one recorded
    //                                   total says a staff member with 18
    //                                   general hours and no dementia hours
    //                                   meets a 12-plus-6 rule. They do not.
    //                                   UNDER-requires -> a false PASS.
    //
    //   counts_toward_general_annual:   Ohio. Two cognitive-impairment
    //     true                          requirements whose 4 and 8 hours COUNT
    //                                   TOWARD the general 8 rather than
    //                                   adding to it. Summing all four rows
    //                                   gives 29 where the code requires less.
    //                                   OVER-requires -> a false FAIL.
    //
    // The second is the merciful direction and is still a wrong number on a
    // compliance board, which is how a screen teaches people to ignore it.
    // Neither can be fixed by better addition: both need each RECORDED hour to
    // carry which requirement it was for, and an alf_staff_credentials row
    // carries `category` (dementia/general/orientation) rather than a
    // requirement id. Until that exists the honest answer is a null verdict
    // with the reason, not a boolean in either direction.
    const stacked = function (r) {
      return !!r && (r.additive === true || r.counts_toward_general_annual === true
                     || typeof r.stacking === 'string');
    };
    const additive = reqs.filter(stacked);
    out.staff_findings = opts.staff.map(function (s) {
      const applicable = reqs.filter(function (r) {
        return !s.applies_to || s.applies_to.indexOf(r.who) !== -1;
      });
      const target = applicable.reduce(function (sum, r) {
        return sum + (Number(r.annual_hours) || 0);
      }, 0);
      const recorded = Number(s.annual_hours_recorded || 0);
      const pooled = applicable.some(stacked);
      return {
        staff_id: s.staff_id, name: s.name || '',
        required_annual_hours: target,
        recorded_annual_hours: recorded,
        shortfall_hours: Math.max(0, target - recorded),
        // NULL, NOT FALSE, and not true. A separate pool means this comparison
        // cannot answer the question either way.
        meets: pooled ? null : (recorded >= target),
        meets_unknown_reason: pooled
          ? ('At least one applicable requirement carries STACKING SEMANTICS '
             + '-- either ADDITIVE (a separate pool on top of the general '
             + 'annual total, so summing UNDER-requires) or '
             + 'COUNTS_TOWARD_GENERAL_ANNUAL (already inside it, so summing '
             + 'OVER-requires). One recorded hours figure cannot be '
             + 'apportioned across requirements, so whether this person '
             + 'complies is not answerable from it in either direction. Read '
             + 'the requirements below directly, or record hours per '
             + 'requirement.')
          : null,
        applicable_requirements: applicable.map(function (r) { return r.who; })
      };
    });
    if (additive.length) {
      out.staff_findings_caveat =
        'This rule carries ' + additive.length + ' requirement(s) with stacking '
        + 'semantics (additive, or counting toward the general annual), so '
        + 'per-staff verdicts are reported as unknown rather than guessed. '
        + 'Summing would be wrong in a different direction for each.';
    }
  }
  return out;
}

// ── LICENSURE ────────────────────────────────────────────────────────────
function describeLicensure(rules, opts) {
  opts = opts || {};
  const sel = selectRule(rules, {
    state: opts.state, requirement_type: 'licensure',
    facility_class: opts.facility_class, on_date: opts.on_date
  });
  if (!sel.ok) return sel;
  const d = sel.rule.data || {};
  return {
    ok: true, state: sel.rule.state, rule_id: sel.rule.rule_id,
    model: d.model, label: d.label,
    base_license: d.base_license || null,
    license_classes: d.license_classes || null,
    memory_care_license: d.memory_care_license !== undefined ? d.memory_care_license : null,
    certification_types: d.certification_types || null,
    special_care_unit: d.special_care_unit || null,
    director_requirements: d.director_requirements || null,
    disclosure_required: d.disclosure_required || false,
    notes: d.notes || [],
    authority: d.authority || null
  };
}

// ── COVERAGE ─────────────────────────────────────────────────────────────
function complianceCoverage(rules, claimedStates) {
  const states = (claimedStates || []).slice();
  const seen = {};
  (rules || []).forEach((r) => {
    if (!r || !r.state) return;
    seen[r.state] = seen[r.state] || {};
    seen[r.state][r.requirement_type] = true;
  });
  const TYPES = ['staffing', 'training', 'licensure'];
  const detail = states.map((s) => ({
    state: s,
    types_covered: TYPES.filter((t) => seen[s] && seen[s][t]),
    complete: TYPES.every((t) => seen[s] && seen[s][t])
  }));
  return {
    have: detail.filter((x) => x.complete).length,
    need: states.length,
    detail: detail,
    uncovered_states: detail.filter((x) => !x.types_covered.length).map((x) => x.state)
  };
}

module.exports = {
  ruleInForce,
  selectRule,
  evaluateStaffing,
  evaluateTraining,
  describeLicensure,
  complianceCoverage
};
