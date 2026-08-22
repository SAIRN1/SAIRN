// Isolated test of api/_lib/compliance-rules.js (Phase 2). The engine is PURE,
// so every case runs against the REAL module and the REAL seed -- not a
// reimplementation, not a fixture copy.
//
// Where a state's own administrative code gives a figure, that figure is the
// test. Several cases exist specifically to lock in a correction found during
// verification, so the older (wrong) working-summary number cannot come back.
'use strict';
const path = require('path');
const ROOT = path.join(__dirname, '..', '..');
const e = require(path.join(ROOT, 'api/_lib/compliance-rules.js'));
const seed = require(path.join(ROOT, 'sql/sairncare_compliance_seed.json'));
const R = seed.rules;
const D = '2026-08-22';

let pass = 0, fail = 0;
function check(name, fn) {
  try { fn(); pass++; console.log('PASS ' + name); }
  catch (err) { fail++; console.log('FAIL ' + name + ' -- ' + err.message); }
}
function assertEq(a, b, m) {
  if (JSON.stringify(a) !== JSON.stringify(b)) {
    throw new Error((m || 'mismatch') + ': expected ' + JSON.stringify(b) + ' got ' + JSON.stringify(a));
  }
}
function assertTrue(v, m) { if (!v) throw new Error(m || 'expected truthy'); }

// ── fail-closed behaviour ────────────────────────────────────────────────
check('an unseeded state fails closed and names the state', () => {
  const r = e.evaluateStaffing(R, { state: 'FL', on_date: D, census: 20 });
  assertEq(r.ok, false);
  assertEq(r.error.code, 'NO_RULE_FOR_STATE');
  assertTrue(/FL/.test(r.error.message));
  assertTrue(/not covered/i.test(r.error.message));
  assertEq(r.required_staff, undefined, 'a refusal must never carry a requirement figure');
});

check('a seeded state but unseeded facility class fails closed, never borrowing another class', () => {
  // PA seeds ALR only; PCH was deliberately not verified and not seeded.
  const r = e.evaluateStaffing(R, { state: 'PA', facility_class: 'pch', on_date: D, mobile_residents: 10, mobility_needs_residents: 2 });
  assertEq(r.ok, false);
  assertEq(r.error.code, 'NO_RULE_FOR_CLASS');
  assertTrue(/pch/.test(r.error.message));
  assertEq(r.required_service_hours_per_day, undefined, 'must not apply ALR hours to a PCH facility');
});

check('a date before a rule took effect fails closed', () => {
  const r = e.evaluateStaffing(R, { state: 'MI', facility_class: 'afc_small_group', on_date: '1990-01-01', census: 10 });
  assertEq(r.ok, false);
  assertEq(r.error.code, 'NO_RULE_IN_FORCE');
});

// ── MICHIGAN: the correction that matters most ───────────────────────────
check('MI small group home is 1:12, no shift split', () => {
  const r = e.evaluateStaffing(R, { state: 'MI', facility_class: 'afc_small_group', on_date: D, census: 12, direct_care_staff: 1 });
  assertEq(r.method, 'fixed_ratio');
  assertEq(r.required_staff, 1);
  assertEq(r.meets, true);
});

check('MI LARGE group home is NOT 1:12 -- it is 1:15 waking and 1:20 sleeping', () => {
  const waking = e.evaluateStaffing(R, { state: 'MI', facility_class: 'afc_large_group', on_date: D, shift: 'waking', census: 20, direct_care_staff: 1 });
  const sleeping = e.evaluateStaffing(R, { state: 'MI', facility_class: 'afc_large_group', on_date: D, shift: 'sleeping', census: 20, direct_care_staff: 1 });
  assertEq(waking.required_staff, 2, '20 residents / 15 per staff rounds up to 2');
  assertEq(sleeping.required_staff, 1, '20 residents / 20 per staff is exactly 1');
  assertTrue(waking.required_staff !== sleeping.required_staff, 'the shift split must actually change the answer');
  // Lock the correction: applying the old flat 1:12 would have required 2 on BOTH shifts.
  assertTrue(sleeping.required_staff !== Math.ceil(20 / 12), 'sleeping must not use the superseded 1:12 figure');
});

check('MI large group home REFUSES to answer without a shift, rather than picking one', () => {
  const r = e.evaluateStaffing(R, { state: 'MI', facility_class: 'afc_large_group', on_date: D, census: 20 });
  assertEq(r.evaluated, false);
  assertEq(r.missing, ['shift']);
  assertEq(r.required_staff, undefined);
});

check('MI declares NO state-mandated dementia hours -- distinct from "zero hours required"', () => {
  const r = e.evaluateTraining(R, { state: 'MI', on_date: D });
  assertEq(r.ok, true);
  assertEq(r.state_mandated, false);
  assertEq(r.requirements, []);
  assertTrue(/facility/i.test(r.note), 'must say the target would be the facility’s own policy');
});

check('a facility-defined MI target is echoed back but never presented as a state mandate', () => {
  const r = e.evaluateTraining(R, { state: 'MI', on_date: D, facility_defined_target_hours: 6 });
  assertEq(r.facility_defined_target_hours, 6);
  assertEq(r.state_mandated, false);
});

// ── OHIO: three branches, not two ────────────────────────────────────────
check('OH memory-care-alongside-basic uses a 20% uplift over the provider’s OWN ratio', () => {
  const r = e.evaluateStaffing(R, { state: 'OH', facility_class: 'rcf_memory_care', on_date: D, memory_care_only: false, baseline_ratio_per_staff: 12, census: 24 });
  assertEq(r.branch.rule, 'uplift_over_own_basic_ratio');
  assertEq(r.required_residents_per_staff, 10, '12 residents per staff, 20% richer, is 10');
  assertEq(r.required_staff, 3, '24 residents at 1 per 10 rounds up to 3');
});

check('OH memory-care-ONLY with a benchmark available uses the benchmark uplift, NOT the 1:10 fallback', () => {
  const r = e.evaluateStaffing(R, { state: 'OH', facility_class: 'rcf_memory_care', on_date: D, memory_care_only: true, benchmark_ratio_available: true, baseline_ratio_per_staff: 15, census: 30 });
  assertEq(r.branch.rule, 'uplift_over_benchmark_average');
  assertEq(r.required_residents_per_staff, 12.5);
  assertEq(r.required_staff, 3);
  // The old two-branch reading would have applied 1:10 here, requiring 3 as well
  // at this census -- so assert the BRANCH, which is what actually differs.
  assertTrue(r.branch.rule !== 'fixed_ratio', 'must not fall back to 1:10 when the benchmark is available');
});

check('OH memory-care-ONLY without a benchmark falls back to 1:10 plus a per-floor rule', () => {
  const r = e.evaluateStaffing(R, { state: 'OH', facility_class: 'rcf_memory_care', on_date: D, memory_care_only: true, benchmark_ratio_available: false, census: 25 });
  assertEq(r.branch.rule, 'fixed_ratio');
  assertEq(r.required_staff, 3);
  assertTrue(/each floor/i.test(r.additional || ''), 'the multi-floor requirement must be surfaced');
});

check('OH refuses to compute an uplift without the baseline it upflifts from', () => {
  const r = e.evaluateStaffing(R, { state: 'OH', facility_class: 'rcf_memory_care', on_date: D, memory_care_only: false, census: 24 });
  assertEq(r.evaluated, false);
  assertEq(r.missing, ['baseline_ratio_per_staff']);
  assertEq(r.required_staff, undefined);
});

check('OH refuses when the benchmark-availability question is unanswered for a memory-care-only provider', () => {
  const r = e.evaluateStaffing(R, { state: 'OH', facility_class: 'rcf_memory_care', on_date: D, memory_care_only: true, census: 25 });
  assertEq(r.evaluated, false);
  assertEq(r.missing, ['benchmark_ratio_available']);
});

check('OH surfaces the RN/LPN on-call-or-on-site coverage requirement', () => {
  const r = e.evaluateStaffing(R, { state: 'OH', facility_class: 'rcf_memory_care', on_date: D, memory_care_only: true, benchmark_ratio_available: false, census: 20 });
  assertTrue(/RNs or LPNs/.test(r.clinical_coverage || ''));
});

check('OH dementia hours are 2 initial + 4 annual and may COUNT TOWARD the general 8', () => {
  const r = e.evaluateTraining(R, { state: 'OH', facility_class: 'rcf', on_date: D });
  const cog = r.requirements.find((x) => /late-stage cognitive/.test(x.who));
  assertEq(cog.initial_hours, 2);
  assertEq(cog.annual_hours, 4);
  assertEq(cog.counts_toward_general_annual, true, 'Ohio stacks INTO the general hours -- the opposite of Pennsylvania');
  const gen = r.requirements.find((x) => /general continuing education/.test(x.who));
  assertEq(gen.annual_hours, 8);
});

// ── INDIANA: real numeric thresholds ─────────────────────────────────────
check('IN has REAL numeric staffing requirements -- not "no requirement"', () => {
  const r = e.evaluateStaffing(R, { state: 'IN', facility_class: 'rcf', on_date: D, nursing_service_census: 120 });
  assertEq(r.method, 'census_thresholds');
  assertTrue(r.thresholds.length >= 3, 'all three thresholds must be reported');
  assertTrue(r.thresholds.every((t) => t.applies === true), 'at a census of 120 every threshold is triggered');
});

check('IN computes the additional nursing staff for every further 50 residents above 100', () => {
  const at120 = e.evaluateStaffing(R, { state: 'IN', facility_class: 'rcf', on_date: D, nursing_service_census: 120 });
  const at210 = e.evaluateStaffing(R, { state: 'IN', facility_class: 'rcf', on_date: D, nursing_service_census: 210 });
  const add120 = at120.thresholds.find((t) => t.additional_staff_required != null);
  const add210 = at210.thresholds.find((t) => t.additional_staff_required != null);
  assertEq(add120.additional_staff_required, 1);
  assertEq(add210.additional_staff_required, 3, '110 residents above the threshold, one per 50, rounds up to 3');
});

check('IN below the 50-resident threshold triggers only the always-on awake-staff rule', () => {
  const r = e.evaluateStaffing(R, { state: 'IN', facility_class: 'rcf', on_date: D, nursing_service_census: 20 });
  assertEq(r.thresholds[0].applies, true, 'the awake-staff rule applies at all times');
  assertEq(r.thresholds[1].applies, false);
  assertEq(r.thresholds[2].applies, false);
});

check('IN awake staff must hold current CPR and first aid', () => {
  const r = e.evaluateStaffing(R, { state: 'IN', facility_class: 'rcf', on_date: D, nursing_service_census: 10 });
  assertEq(r.thresholds[0].must_hold, ['current CPR certificate', 'current first aid certificate']);
  assertEq(r.thresholds[0].must_be_awake, true);
});

check('IN training is 6 initial / 3 annual for contact staff, 12 / 6 for the SCU director', () => {
  const r = e.evaluateTraining(R, { state: 'IN', facility_class: 'rcf', on_date: D });
  const staff = r.requirements.find((x) => /contact with residents/.test(x.who));
  const dir = r.requirements.find((x) => /director/.test(x.who));
  assertEq([staff.initial_hours, staff.annual_hours], [6, 3]);
  assertEq([dir.initial_hours, dir.annual_hours], [12, 6]);
});

check('IN records the SCU director grandfather clause so an existing director is not falsely flagged', () => {
  const r = e.describeLicensure(R, { state: 'IN', facility_class: 'rcf', on_date: D });
  assertTrue(/exempt from the degree and experience requirements/i.test(r.director_requirements.grandfathered));
  assertEq(r.director_requirements.experience_years, 1);
  assertEq(r.director_requirements.experience_window_years, 5);
});

// ── PENNSYLVANIA: hours, not headcount ───────────────────────────────────
check('PA computes service HOURS per day, not a staff headcount', () => {
  const r = e.evaluateStaffing(R, { state: 'PA', facility_class: 'alr', on_date: D, mobile_residents: 10, mobility_needs_residents: 5 });
  assertEq(r.method, 'service_hours_per_resident_per_day');
  assertEq(r.required_service_hours_per_day, 20, '10 mobile x 1hr + 5 mobility x 2hr');
  assertEq(r.required_staff, undefined, 'PA does not express this as a headcount');
});

check('PA counts EVERY special-care-unit resident as having mobility needs', () => {
  const r = e.evaluateStaffing(R, { state: 'PA', facility_class: 'alr', on_date: D, mobile_residents: 10, mobility_needs_residents: 4, scu_residents: 6 });
  assertEq(r.effective_mobility_needs_residents, 10, '4 stated + 6 SCU residents');
  assertEq(r.required_service_hours_per_day, 30, '10x1 + 10x2');
});

check('PA 75% applies to WAKING HOURS, not to staffing mix', () => {
  const r = e.evaluateStaffing(R, { state: 'PA', facility_class: 'alr', on_date: D, mobile_residents: 10, mobility_needs_residents: 5 });
  assertEq(r.waking_hours_minimum_percent, 75);
  assertEq(r.minimum_hours_during_waking, 15, '75% of 20 hours');
  // Lock the correction: there must be no direct-care-mix field implying the old reading.
  assertEq(r.direct_care_staff_percent, undefined, 'the 75% must not be modelled as a staffing-mix rule');
});

check('PA surfaces the always-present-21-or-older and awake requirements', () => {
  const r = e.evaluateStaffing(R, { state: 'PA', facility_class: 'alr', on_date: D, mobile_residents: 1, mobility_needs_residents: 0 });
  assertTrue(/21 years of age or older/.test(r.always_present || ''));
  assertTrue(/awake at all times/.test(r.awake_requirement || ''));
});

check('PA SCU dementia training is 8 + 8, materially higher than the 4 + 2 baseline', () => {
  const r = e.evaluateTraining(R, { state: 'PA', facility_class: 'alr', on_date: D });
  const baseline = r.requirements.find((x) => /dementia baseline/.test(x.who));
  const scu = r.requirements.find((x) => /special care unit/.test(x.who));
  assertEq([baseline.initial_hours, baseline.annual_hours], [4, 2]);
  assertEq([scu.initial_hours, scu.annual_hours], [8, 8]);
  assertTrue(scu.annual_hours > baseline.annual_hours, 'the SCU tier must be higher than the baseline tier');
});

check('PA dementia hours are ADDITIVE to the general 16 -- the opposite of Ohio’s stacking', () => {
  const pa = e.evaluateTraining(R, { state: 'PA', facility_class: 'alr', on_date: D });
  const scu = pa.requirements.find((x) => /special care unit/.test(x.who));
  const oh = e.evaluateTraining(R, { state: 'OH', facility_class: 'rcf', on_date: D });
  const cog = oh.requirements.find((x) => /late-stage cognitive/.test(x.who));
  // Compared on a SINGLE shared field with opposite values. An earlier version of
  // this data expressed the same fact with two differently-named booleans that were
  // both true, which reads as agreement when the two states in fact do the
  // opposite -- exactly the confusion that would let a shared model be written.
  assertEq(scu.stacking, 'additive');
  assertEq(cog.stacking, 'counts_toward_general');
  assertTrue(scu.stacking !== cog.stacking,
    'these two states stack in opposite directions -- a shared model would get one of them wrong');
  // 8 SCU dementia hours land ON TOP of PA's 16, so a PA SCU worker owes 24.
  const paGeneral = pa.requirements.find((x) => /general annual/.test(x.who) && x.annual_hours === 16);
  assertEq(paGeneral.annual_hours + scu.annual_hours, 24);
  // Ohio's 4 dementia hours sit INSIDE the general 8, so an Ohio worker owes 8, not 12.
  const ohGeneral = oh.requirements.find((x) => /general continuing education/.test(x.who));
  assertEq(ohGeneral.annual_hours, 8);
  assertTrue(cog.annual_hours < ohGeneral.annual_hours, 'Ohio’s dementia hours fit within the general requirement');
});

check('PA 18 hours gates UNSUPERVISED work specifically', () => {
  const r = e.evaluateTraining(R, { state: 'PA', facility_class: 'alr', on_date: D });
  const gate = r.requirements.find((x) => x.initial_hours === 18);
  assertTrue(/unsupervised/i.test(gate.gate));
});

// ── per-staff training evaluation ────────────────────────────────────────
check('a staff member with NO records is reported short, never assumed compliant', () => {
  const r = e.evaluateTraining(R, {
    state: 'IN', facility_class: 'rcf', on_date: D,
    staff: [{ staff_id: 'S1', name: 'No Records', applies_to: ['staff who have contact with residents'], annual_hours_recorded: 0 }]
  });
  const f = r.staff_findings[0];
  assertEq(f.required_annual_hours, 3);
  assertEq(f.recorded_annual_hours, 0);
  assertEq(f.shortfall_hours, 3);
  assertEq(f.meets, false);
});

check('a staff member meeting the hours is reported as meeting them', () => {
  const r = e.evaluateTraining(R, {
    state: 'IN', facility_class: 'rcf', on_date: D,
    staff: [{ staff_id: 'S2', applies_to: ['staff who have contact with residents'], annual_hours_recorded: 3 }]
  });
  assertEq(r.staff_findings[0].meets, true);
  assertEq(r.staff_findings[0].shortfall_hours, 0);
});

// ── licensure + coverage ─────────────────────────────────────────────────
check('OH licensure is a certification layered on the RCF licence, not a separate licence', () => {
  const r = e.describeLicensure(R, { state: 'OH', facility_class: 'rcf_memory_care', on_date: D });
  assertEq(r.model, 'certification_layered_on_license');
  assertEq(r.memory_care_license, null);
  assertTrue(/basic service and memory care/.test((r.certification_types || []).join('|')));
});

check('MI licensure records that no assisted-living licence exists at all', () => {
  const r = e.describeLicensure(R, { state: 'MI', on_date: D });
  assertEq(r.model, 'no_assisted_living_license');
  assertEq(r.memory_care_license, null);
  assertEq(r.license_classes.length, 3);
});

check('PA licensure records two parallel licences and the 60-day SCU application lead time', () => {
  const r = e.describeLicensure(R, { state: 'PA', on_date: D });
  assertEq(r.model, 'two_parallel_licenses');
  assertEq(r.special_care_unit.application_lead_days, 60);
});

check('no two seeded states share a staffing METHOD -- the reason there is no core model', () => {
  const methods = {};
  R.filter((r) => r.requirement_type === 'staffing').forEach((r) => {
    methods[r.state] = methods[r.state] || new Set();
    methods[r.state].add(r.data.method);
  });
  const perState = Object.keys(methods).map((s) => Array.from(methods[s]).sort().join('+'));
  assertEq(new Set(perState).size, perState.length, 'each state must use a distinct staffing method signature');
});

check('coverage reports all four states complete across all three requirement types', () => {
  const c = e.complianceCoverage(R, seed.claimed_states);
  assertEq(c.have, 4);
  assertEq(c.need, 4);
  assertEq(c.uncovered_states, []);
});

check('coverage reports an unseeded state as uncovered rather than silently omitting it', () => {
  const c = e.complianceCoverage(R, ['OH', 'IN', 'MI', 'PA', 'FL']);
  assertEq(c.have, 4);
  assertEq(c.need, 5);
  assertEq(c.uncovered_states, ['FL']);
});

check('every seeded rule carries a citation, a resolvable URL and a real quote', () => {
  R.forEach((r) => {
    const a = r.data.authority;
    assertTrue(a && a.citation, r.rule_id + ' missing citation');
    assertTrue(a && /^https?:\/\//.test(a.url || ''), r.rule_id + ' missing resolvable URL');
    assertTrue(a && (a.quote || '').length > 40, r.rule_id + ' missing a real source quote');
    assertTrue(a && a.read_on === '2026-08-22', r.rule_id + ' missing the verification date');
  });
});

check('every correction found during verification is recorded in the rule itself', () => {
  const corrected = R.filter((r) => r.data._corrected);
  assertTrue(corrected.length >= 5, 'expected the verification corrections to be recorded, found ' + corrected.length);
  const states = new Set(corrected.map((r) => r.state));
  assertEq(states.size, 4, 'all four states had at least one correction');
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
