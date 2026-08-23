// api/_lib/payer-routing.js
// SAIRNcare Phase 1 payer/billing-routing engine.
//
// PURE -- no I/O, no database, no network. Every function here takes real
// inputs and returns a decision, so the rules can be tested against the
// worked examples in the source bulletins without any infrastructure.
// Same shape as api/_lib/deadline-engine.js, and for the same reason.
//
// FAILS CLOSED. Every refusal names the missing thing and NO refusal path
// ever returns a billable code/modifier combination. The engine never
// guesses a state's rules, never substitutes one state for another, and
// never infers a value that the state says an external authority assigns.
//
// TWO MECHANISMS, deliberately separate:
//   1. Medicaid HCBS waiver billing (state-specific codes + modifiers)
//   2. Hospice / Medicare Advantage relatedness routing
// They share nothing but this file. A hospice relatedness determination has
// no bearing on an HCBS waiver claim and vice versa.

'use strict';

// ── DATES ────────────────────────────────────────────────────────────────
// All date handling is UTC and string-based (YYYY-MM-DD). Local-time Date
// arithmetic is how off-by-one date bugs happen, and this platform has
// already shipped one.
function daysInMonth(monthStr) {
  const m = /^(\d{4})-(\d{2})$/.exec(monthStr || '');
  if (!m) return null;
  return new Date(Date.UTC(Number(m[1]), Number(m[2]), 0)).getUTCDate();
}

function isValidMonth(monthStr) {
  const m = /^(\d{4})-(\d{2})$/.exec(monthStr || '');
  if (!m) return false;
  const mo = Number(m[2]);
  return mo >= 1 && mo <= 12;
}

// A rule is in force for a service month if the month overlaps its window at
// all. Compared against the LAST day of the service month for effective_from
// and the FIRST day for effective_to, because a rule that takes effect
// mid-month still governs that month's claim.
function ruleInForce(rule, serviceMonth) {
  if (!rule || !rule.effective_from) return false;
  // A rule published and then repealed/paused before it ever governed a claim is
  // retained for legibility but must never be selected. Checked explicitly rather
  // than inferred from an inverted date range, which would be indistinguishable
  // from a data-entry error.
  if (rule.status && rule.status !== 'active') return false;
  const dim = daysInMonth(serviceMonth);
  if (!dim) return false;
  const monthStart = serviceMonth + '-01';
  const monthEnd = serviceMonth + '-' + String(dim).padStart(2, '0');
  if (rule.effective_from > monthEnd) return false;
  if (rule.effective_to && rule.effective_to < monthStart) return false;
  return true;
}

function refuse(code, message, extra) {
  return Object.assign({ ok: false, error: { code: code, message: message } }, extra || {});
}

// ── MECHANISM 1: MEDICAID HCBS WAIVER BILLING ────────────────────────────
//
// Given a state's rule, how many days the resident was actually present, and
// the resident's state-assigned acuity tier, decide which billing method and
// which exact code+modifier string to use.
//
// THE TIER IS NEVER DERIVED. In Ohio the three-tier unit rate is
// "determined by the ODA's designee through an assessment of the
// individual's service needs" (OAC 5160-33-07(D)) -- it is an external
// authority's determination about a specific person, not something a billing
// system can compute from a care level, a diagnosis, or a facility type.
// A missing tier is refused (MISSING_TIER), never guessed. Same discipline
// as SAIRNcode's PC/TC indicator, which likewise fails closed rather than
// inferring a CMS-assigned value.
function routeHcbsClaim(input) {
  input = input || {};
  const rule = input.rule;
  const serviceMonth = input.service_month;
  const daysPresent = input.days_present;

  if (!rule) return refuse('NO_RULE', 'No HCBS billing rule was supplied for this claim');
  if (!isValidMonth(serviceMonth)) return refuse('BAD_MONTH', 'service_month must be YYYY-MM');
  if (!ruleInForce(rule, serviceMonth)) {
    return refuse('NO_RULE_IN_FORCE',
      'No ' + (rule.state || '?') + ' HCBS rule was in force for ' + serviceMonth +
      ' (this rule covers ' + rule.effective_from + ' to ' + (rule.effective_to || 'present') + ')');
  }
  if (typeof daysPresent !== 'number' || !isFinite(daysPresent) || daysPresent < 0) {
    return refuse('BAD_DAYS_PRESENT', 'days_present must be a non-negative number');
  }
  const dim = daysInMonth(serviceMonth);
  if (daysPresent > dim) {
    return refuse('BAD_DAYS_PRESENT', 'days_present (' + daysPresent + ') exceeds the ' + dim + ' days in ' + serviceMonth);
  }

  const d = rule.data || {};

  // ── IS THIS RULE ROUTABLE AT ALL? ────────────────────────────────────────
  // Added 2026-08-23, when Michigan and Pennsylvania were researched and
  // turned out not to bill assisted living the way Ohio and Indiana do.
  //
  // The original engine assumed every state pays a per-resident amount keyed
  // to days present. That is true of OH and IN and is NOT a general fact:
  //   MI  -- MI Choice pays Community Living Supports in 15-MINUTE units of
  //          service actually delivered, and the provider bills the waiver
  //          agency rather than the state. Days present does not determine the
  //          unit count, so computing one from occupancy would invent it.
  //   PA  -- the only state-published residential code that reaches a licensed
  //          personal care home or assisted living residence sits in the OBRA
  //          waiver, whose unit is a day on which at least 8 HOURS of service
  //          were rendered -- again not the same thing as a day present.
  // A rule that declares billing_model 'reference_only' is real, sourced and
  // worth showing, but this engine refuses to assemble a claim from it. The
  // refusal carries the recorded codes so the information is not lost; it just
  // is not presented as a computed claim line.
  if (d.billing_model === 'reference_only') {
    return refuse('NOT_ROUTABLE',
      (rule.state || '?') + ' does not bill this service on a days-present basis, so this app will not assemble the claim. ' +
      (d.not_routable_reason || 'The recorded codes are provided for reference and the claim must be built from the service log.'),
      {
        state: rule.state, rule_id: rule.rule_id || null,
        reference_only: true,
        codes: d.codes || null,
        constraints: d.constraints || [],
        authority: d.authority || null
      });
  }

  // ── TIER ─────────────────────────────────────────────────────────────────
  // tier_model must be DECLARED. Previously the engine read tier_modifiers and,
  // if absent, fell through to MISSING_TIER with an empty available_tiers list
  // -- which told a tierless state's user to supply one of nothing. A rule that
  // has not said which case it is in is a data defect, and is now named as one
  // rather than reported as a missing input the user could never provide.
  const tiers = d.tier_modifiers || null;
  const tierModel = d.tier_model || (tiers ? 'assigned' : null);
  if (!tierModel) {
    return refuse('MALFORMED_RULE',
      'Rule ' + (rule.rule_id || '?') + ' declares no tier_model and carries no tier_modifiers, so it cannot say whether this state uses acuity tiers. Fix the rule; do not answer from it.');
  }
  const tier = input.tier;
  if (tierModel === 'none') {
    // A tier supplied against a tierless state is refused rather than ignored:
    // silently dropping it would let a caller believe a tier was applied.
    if (tier) {
      return refuse('TIER_NOT_APPLICABLE',
        (rule.state || '?') + ' does not use acuity tiers for this service, so tier "' + tier + '" cannot be applied. Resubmit without a tier.');
    }
  } else if (!tier) {
    // The assigner is returned as its own field rather than spliced into the
    // sentence -- these descriptors are a full clause in some states and read
    // as broken prose when concatenated mid-sentence.
    return refuse('MISSING_TIER',
      'This claim needs the resident’s assigned acuity tier, which is set by an external assessment and cannot be derived from the care level on file.',
      { assigned_by: d.tier_assigned_by || 'the state’s designee', available_tiers: Object.keys(tiers || {}) });
  } else if (!tiers || !tiers[tier]) {
    return refuse('UNKNOWN_TIER',
      'Tier "' + tier + '" is not one of the tiers ' + (rule.state || '?') + ' recognises: ' + Object.keys(tiers || {}).join(', '));
  }

  if (daysPresent === 0) {
    return refuse('NO_BILLABLE_DAYS', 'The resident was not present at all in ' + serviceMonth + ', so there is nothing to bill');
  }

  // Method selection. Each state's thresholds live in the rule data, never
  // in this code -- Indiana's own thresholds changed twice in one month.
  const monthly = d.monthly || null;
  const daily = d.daily || null;
  let method = null;
  let why = '';

  const monthlyMin = monthly && typeof monthly.min_days_present === 'number' ? monthly.min_days_present : null;
  const monthlyRequiredAt = monthly && typeof monthly.required_at_days === 'number' ? monthly.required_at_days : null;
  const dailyMaxDays = daily && typeof daily.max_days === 'number' ? daily.max_days : null;

  const monthlyEligible = !!monthly && (monthlyMin === null || daysPresent >= monthlyMin);
  const dailyEligible = !!daily && (dailyMaxDays === null || daysPresent <= dailyMaxDays);

  if (monthlyRequiredAt !== null && daysPresent >= monthlyRequiredAt) {
    // A hard mandate (Indiana's paused BT2025173 shape). Billing daily here
    // is denied by the payer, so the engine refuses to produce it.
    if (!monthlyEligible) {
      return refuse('RULE_CONFLICT', 'The rule requires monthly billing at ' + daysPresent + ' days but its own monthly minimum is not met');
    }
    method = 'monthly';
    why = (rule.state || '?') + ' requires monthly billing at ' + monthlyRequiredAt + ' or more days present.';
  } else if (monthlyRequiredAt !== null && daysPresent < monthlyRequiredAt) {
    if (!dailyEligible) {
      return refuse('NO_ELIGIBLE_METHOD', 'Neither billing method is available for ' + daysPresent + ' days present');
    }
    method = 'daily';
    why = (rule.state || '?') + ' requires daily billing below ' + monthlyRequiredAt + ' days present.';
  } else if (monthlyEligible && dailyEligible) {
    // Both permitted -- provider discretion (Indiana's CURRENT BT2025190
    // shape). The engine must NOT silently pick one and present it as
    // required; it returns both and says the choice is the provider's.
    method = input.preferred_method === 'daily' ? 'daily' : (input.preferred_method === 'monthly' ? 'monthly' : null);
    if (!method) {
      return {
        ok: true,
        decision: 'provider_choice',
        state: rule.state,
        service_month: serviceMonth,
        days_present: daysPresent,
        options: [
          buildHcbsLine(d, monthly, tier, tiers, 'monthly', serviceMonth, dim, daysPresent),
          buildHcbsLine(d, daily, tier, tiers, 'daily', serviceMonth, dim, daysPresent)
        ],
        note: (rule.state || '?') + ' currently permits either method for ' + daysPresent + ' days present — the provider chooses.',
        authority: d.authority || null,
        rule_id: rule.rule_id || null
      };
    }
    why = 'Provider selected the ' + method + ' method; ' + (rule.state || '?') + ' permits either at ' + daysPresent + ' days present.';
  } else if (monthlyEligible) {
    method = 'monthly';
    why = 'Only monthly billing is available at ' + daysPresent + ' days present.';
  } else if (dailyEligible) {
    method = 'daily';
    why = 'Only daily billing is available at ' + daysPresent + ' days present.';
  } else {
    return refuse('NO_ELIGIBLE_METHOD',
      'Neither billing method is available at ' + daysPresent + ' days present in ' + (rule.state || '?'));
  }

  const spec = method === 'monthly' ? monthly : daily;
  const line = buildHcbsLine(d, spec, tier, tiers, method, serviceMonth, dim, daysPresent);
  return {
    ok: true,
    decision: 'routed',
    state: rule.state,
    service_month: serviceMonth,
    days_present: daysPresent,
    method: method,
    why: why,
    line: line,
    constraints: d.constraints || [],
    authority: d.authority || null,
    rule_id: rule.rule_id || null
  };
}

function buildHcbsLine(d, spec, tier, tiers, method, serviceMonth, dim, daysPresent) {
  if (!spec) return null;
  const mods = (spec.modifiers || []).slice();
  // The tier modifier is substituted positionally where the rule says it
  // belongs, so a state that orders modifiers differently stays expressible.
  // A <TIER> placeholder that cannot be resolved is DROPPED rather than
  // rendered as "undefined" inside a billing string -- a tierless rule should
  // never have one, but a malformed rule must not emit a claim line that looks
  // real and carries a junk modifier.
  const resolved = mods
    .map((m) => (m === '<TIER>' ? (tiers && tier ? tiers[tier] : null) : m))
    .filter((m) => !!m);
  return {
    method: method,
    code: spec.code || d.code || null,
    modifiers: resolved,
    billing_string: [(spec.code || d.code || '')].concat(resolved).join(' ').trim(),
    unit: spec.unit || null,
    units: method === 'monthly' ? 1 : daysPresent,
    claim_form: d.claim_form || null,
    from_date: serviceMonth + '-01',
    to_date: serviceMonth + '-' + String(dim).padStart(2, '0'),
    earliest_submission: earliestSubmission(spec, serviceMonth, dim)
  };
}

// When the claim may actually be SENT. Indiana's current rule lets a monthly
// claim go out after the 15th day of presence -- NOT after month end -- and
// its own bulletin works that example ("the provider may submit their claim
// on or after Jan. 16"). Encoding "after month end" would block claims the
// state explicitly permits, so this is driven by the rule, not assumed.
function earliestSubmission(spec, serviceMonth, dim) {
  if (!spec) return null;
  if (spec.submit_after_days_present) {
    return {
      basis: 'days_present',
      days_present_required: spec.submit_after_days_present,
      note: 'Submit once the resident has been present for ' + spec.submit_after_days_present +
            ' days in ' + serviceMonth + ' (services must already be rendered).'
    };
  }
  return {
    basis: 'month_end',
    date: serviceMonth + '-' + String(dim).padStart(2, '0'),
    note: 'Submit after ' + serviceMonth + '-' + String(dim).padStart(2, '0') + ', once all services for the month are rendered.'
  };
}

// ── MECHANISM 2: HOSPICE / MEDICARE ADVANTAGE RELATEDNESS ────────────────
//
// When a Medicare Advantage enrollee elects hospice, the hospice benefit is
// carved out to FFS Medicare while the MA plan keeps paying for care
// UNRELATED to the terminal diagnosis. That is a per-claim relatedness
// determination, not a one-time enrollment switch.
//
// The VBID hospice carve-in, which briefly changed this, ENDED 2024-12-31
// and was not revived; the entire VBID model terminated beginning CY2026.
// So the carve-out below is the standing model, not a temporary state.
//
// THE PART THAT IS NOT JUST A MODIFIER CHECK: CMS CR 14219 / MLN MM14219,
// effective 2026-04-01 (implementation 2026-04-06), added an edit that
// automatically DENIES a hospital inpatient/outpatient claim when there is a
// hospice claim for the same beneficiary in the same covered period carrying
// condition code 07 or modifier GW AND an EXACT primary-diagnosis match. It
// came out of an OIG audit finding ~$190M in improper payments over 5 years.
// So appending GW to a claim whose principal diagnosis matches the hospice
// principal diagnosis is now an auto-denial, and this engine compares the
// diagnoses rather than trusting the modifier.
const HOSPICE_MODIFIERS = {
  professional_related: 'GV',   // attending physician, related to terminal illness, not hospice-employed
  professional_unrelated: 'GW', // any provider, unrelated to terminal illness
  institutional_unrelated: 'Condition Code 07'
};

function normalizeDx(dx) {
  return String(dx || '').toUpperCase().replace(/[^A-Z0-9]/g, '');
}

function routeHospiceClaim(input) {
  input = input || {};
  const rule = input.rule;
  const serviceMonth = input.service_month;

  if (!rule) return refuse('NO_RULE', 'No hospice routing rule was supplied for this claim');
  if (!isValidMonth(serviceMonth)) return refuse('BAD_MONTH', 'service_month must be YYYY-MM');
  if (!ruleInForce(rule, serviceMonth)) {
    return refuse('NO_RULE_IN_FORCE',
      'No hospice routing rule was in force for ' + serviceMonth +
      ' (this rule covers ' + rule.effective_from + ' to ' + (rule.effective_to || 'present') + ')');
  }
  if (!input.hospice_election) {
    return refuse('NO_HOSPICE_ELECTION',
      'This routing only applies once the resident has elected the Medicare hospice benefit');
  }
  const claimDx = normalizeDx(input.claim_principal_diagnosis);
  const hospiceDx = normalizeDx(input.hospice_principal_diagnosis);
  if (!claimDx) return refuse('MISSING_CLAIM_DIAGNOSIS', 'The claim’s principal diagnosis is required to determine relatedness');
  if (!hospiceDx) {
    return refuse('MISSING_HOSPICE_DIAGNOSIS',
      'The hospice election’s principal diagnosis is required — relatedness cannot be determined without it, and guessing would risk an auto-denial under CMS CR 14219');
  }

  // Relatedness itself is a CLINICAL determination, never inferred here. The
  // engine requires it to be stated, and then checks that stated answer for
  // consistency against the diagnosis comparison CMS actually runs.
  const stated = input.relatedness; // 'related' | 'unrelated'
  if (stated !== 'related' && stated !== 'unrelated') {
    return refuse('MISSING_RELATEDNESS',
      'A clinician must determine whether this care is related to the terminal diagnosis — this engine will not infer it');
  }

  const d = rule.data || {};
  const claimType = input.claim_type === 'institutional' ? 'institutional' : 'professional';
  const exactDxMatch = claimDx === hospiceDx;

  if (stated === 'related') {
    return {
      ok: true,
      decision: 'routed',
      payer: 'ffs_medicare_hospice',
      service_month: serviceMonth,
      why: 'Care related to the terminal diagnosis is covered under the hospice per-diem paid by FFS Medicare, not the Medicare Advantage plan.',
      modifier: claimType === 'professional' ? HOSPICE_MODIFIERS.professional_related : null,
      modifier_note: claimType === 'professional'
        ? 'GV applies only when the billing provider is the patient’s designated attending physician and is not employed by or under arrangement with the hospice.'
        : 'Institutional claims for related care are the hospice’s responsibility, billed directly or under arrangement — not separately by the facility.',
      diagnosis_match: exactDxMatch,
      authority: d.authority || null,
      rule_id: rule.rule_id || null
    };
  }

  // stated === 'unrelated'
  const modifier = claimType === 'professional'
    ? HOSPICE_MODIFIERS.professional_unrelated
    : HOSPICE_MODIFIERS.institutional_unrelated;

  if (exactDxMatch) {
    // THE MM14219 CASE. The clinician says unrelated, but the principal
    // diagnosis is an exact match for the hospice principal diagnosis --
    // which is the precise condition CMS's edit auto-denies. Refusing here
    // is the whole point: this claim would be denied, and a system that
    // produced it anyway would be generating known-bad claims.
    return refuse('DX_MATCH_WOULD_DENY',
      'This claim states the care is unrelated to the terminal diagnosis, but its principal diagnosis (' +
      String(input.claim_principal_diagnosis).trim() + ') exactly matches the hospice principal diagnosis. ' +
      'Under CMS CR 14219, effective 2026-04-01, a claim billed with ' + modifier +
      ' and an exact principal-diagnosis match against an active hospice claim in the same period is denied automatically. ' +
      'Either the principal diagnosis on this claim is wrong, or the care is in fact related and belongs under the hospice benefit.',
      {
        would_use_modifier: modifier,
        diagnosis_match: true,
        authority: d.authority || null,
        rule_id: rule.rule_id || null
      });
  }

  return {
    ok: true,
    decision: 'routed',
    payer: 'medicare_advantage_plan',
    service_month: serviceMonth,
    why: 'Care unrelated to the terminal diagnosis remains the Medicare Advantage plan’s responsibility — the hospice carve-out moves only the hospice benefit itself to FFS Medicare.',
    modifier: modifier,
    modifier_note: claimType === 'professional'
      ? 'GW on the CMS-1500 professional claim.'
      : 'Condition code 07 on the UB-04 institutional claim.',
    diagnosis_match: false,
    authority: d.authority || null,
    rule_id: rule.rule_id || null
  };
}

// ── COVERAGE ─────────────────────────────────────────────────────────────
// {have, need} over the states this app CLAIMS to support, so an uncovered
// state is visible as a real gap rather than an empty result that reads like
// "nothing to bill." Same contract shape as alf_signals.
// TWO KINDS OF "COVERED", separated 2026-08-23 and this is the whole point of
// the change. Before it, any rule for a state counted as coverage. Seeding MI
// and PA -- whose real, sourced rules this engine deliberately will NOT route
// -- would therefore have flipped the display from an honest "2 of 4" to a
// "4 of 4" that means the opposite of what a biller would read into it.
// `have` stays the number of states this app can actually produce a claim for.
function hcbsCoverage(rules, claimedStates) {
  const states = (claimedStates || []).slice();
  const routable = {};
  const referenceOnly = {};
  (rules || []).forEach((r) => {
    if (!r || r.program !== 'medicaid_hcbs' || !r.state) return;
    if (r.status && r.status !== 'active') return;
    if (r.data && r.data.billing_model === 'reference_only') referenceOnly[r.state] = true;
    else routable[r.state] = true;
  });
  const routableStates = states.filter((s) => routable[s]);
  // A state with both a routable and a reference-only rule counts as routable.
  const referenceOnlyStates = states.filter((s) => referenceOnly[s] && !routable[s]);
  return {
    have: routableStates.length,
    need: states.length,
    covered_states: routableStates,
    reference_only_states: referenceOnlyStates,
    uncovered_states: states.filter((s) => !routable[s] && !referenceOnly[s]),
    note: referenceOnlyStates.length
      ? referenceOnlyStates.join(', ') + ' have real sourced rules on file but are NOT counted as covered: their programs do not bill on a days-present basis, so this app records the codes and refuses to assemble the claim.'
      : null
  };
}

module.exports = {
  daysInMonth,
  isValidMonth,
  ruleInForce,
  routeHcbsClaim,
  routeHospiceClaim,
  hcbsCoverage,
  HOSPICE_MODIFIERS
};
