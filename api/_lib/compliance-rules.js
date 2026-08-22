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
      scu_mobility_rule: d.scu_mobility_rule || null
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

  // Optional per-staff evaluation.
  if (Array.isArray(opts.staff)) {
    out.staff_findings = opts.staff.map((s) => {
      const applicable = reqs.filter((r) => !s.applies_to || s.applies_to.indexOf(r.who) !== -1);
      const target = applicable.reduce((sum, r) => sum + (Number(r.annual_hours) || 0), 0);
      const recorded = Number(s.annual_hours_recorded || 0);
      return {
        staff_id: s.staff_id, name: s.name || '',
        required_annual_hours: target,
        recorded_annual_hours: recorded,
        shortfall_hours: Math.max(0, target - recorded),
        meets: recorded >= target,
        applicable_requirements: applicable.map((r) => r.who)
      };
    });
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
