// Isolated test of api/_lib/payer-routing.js, the Phase 1 payer/billing-routing
// engine. The engine is PURE (no I/O), so every case here runs against the REAL
// module and the REAL seed file -- not a reimplementation, not a fixture copy.
//
// Where a state's own bulletin works an example, that example is the test.
'use strict';
const path = require('path');
const ROOT = path.join(__dirname, '..', '..');
const pr = require(path.join(ROOT, 'api/_lib/payer-routing.js'));
const seed = require(path.join(ROOT, 'sql/sairncare_payer_rules_seed.json'));

function ruleById(id) {
  const r = seed.rules.find((x) => x.rule_id === id);
  if (!r) throw new Error('seed rule not found: ' + id);
  return r;
}
const IN_CURRENT = ruleById('IN-HCBS-AL-2026-PAUSED');
const IN_SUPERSEDED = ruleById('IN-HCBS-AL-2026-MANDATE-SUPERSEDED');
const OH = ruleById('OH-HCBS-AL-2024');
const HOSPICE = ruleById('US-HOSPICE-MA-CARVEOUT-2025');

let pass = 0, fail = 0;
function check(name, fn) {
  try { fn(); pass++; console.log('PASS ' + name); }
  catch (e) { fail++; console.log('FAIL ' + name + ' -- ' + e.message); }
}
function assertEq(actual, expected, msg) {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error((msg || 'mismatch') + ': expected ' + JSON.stringify(expected) + ' got ' + JSON.stringify(actual));
  }
}
function assertTrue(v, msg) { if (!v) throw new Error(msg || 'expected truthy'); }

// ── dates ────────────────────────────────────────────────────────────────
check('daysInMonth is calendar-accurate including leap years', () => {
  assertEq(pr.daysInMonth('2026-01'), 31);
  assertEq(pr.daysInMonth('2026-02'), 28);
  assertEq(pr.daysInMonth('2028-02'), 29);
  assertEq(pr.daysInMonth('2026-04'), 30);
  assertEq(pr.daysInMonth('garbage'), null);
});

check('a rule taking effect mid-month still governs that whole month', () => {
  // IN current rule is effective 2025-12-31 -- it governs December 2025.
  assertEq(pr.ruleInForce(IN_CURRENT, '2025-12'), true);
  assertEq(pr.ruleInForce(IN_CURRENT, '2025-11'), false);
});

check('a never_in_force rule is NEVER selected, for any month in its own window', () => {
  assertEq(pr.ruleInForce(IN_SUPERSEDED, '2026-01'), false);
  assertEq(pr.ruleInForce(IN_SUPERSEDED, '2026-06'), false);
  assertEq(pr.ruleInForce(IN_SUPERSEDED, '2030-01'), false);
});

// ── HCBS: refusals fail closed ───────────────────────────────────────────
check('no rule supplied is refused, with no billable line', () => {
  const r = pr.routeHcbsClaim({ service_month: '2026-05', days_present: 31, tier: 'tier1' });
  assertEq(r.ok, false);
  assertEq(r.error.code, 'NO_RULE');
  assertEq(r.line, undefined);
});

check('a service month before the rule existed is refused by name', () => {
  const r = pr.routeHcbsClaim({ rule: IN_CURRENT, service_month: '2020-05', days_present: 31, tier: 'tier1' });
  assertEq(r.ok, false);
  assertEq(r.error.code, 'NO_RULE_IN_FORCE');
  assertTrue(/2020-05/.test(r.error.message), 'refusal should name the month');
});

check('a MISSING tier is refused and names who actually assigns it -- never guessed', () => {
  const r = pr.routeHcbsClaim({ rule: OH, service_month: '2026-05', days_present: 31 });
  assertEq(r.ok, false);
  assertEq(r.error.code, 'MISSING_TIER');
  assertTrue(/Ohio Department of Aging/i.test(r.assigned_by),
    'Ohio refusal must name the Ohio Department of Aging’s designee as the assigner');
  assertTrue(/cognitive impairments/i.test(r.assigned_by),
    'and must carry the real four-domain assessment basis, so nobody re-derives the tier from care level');
  assertEq(r.available_tiers, ['tier1', 'tier2', 'tier3']);
  assertEq(r.line, undefined);
});

check('an unknown tier is refused and lists the real tiers', () => {
  const r = pr.routeHcbsClaim({ rule: OH, service_month: '2026-05', days_present: 31, tier: 'memory_care' });
  assertEq(r.ok, false);
  assertEq(r.error.code, 'UNKNOWN_TIER');
  assertTrue(/tier1/.test(r.error.message));
});

check('zero days present is refused rather than billing a zero-day claim', () => {
  const r = pr.routeHcbsClaim({ rule: IN_CURRENT, service_month: '2026-05', days_present: 0, tier: 'tier1' });
  assertEq(r.ok, false);
  assertEq(r.error.code, 'NO_BILLABLE_DAYS');
});

check('days_present exceeding the real days in the month is refused', () => {
  const r = pr.routeHcbsClaim({ rule: IN_CURRENT, service_month: '2026-02', days_present: 30, tier: 'tier1' });
  assertEq(r.ok, false);
  assertEq(r.error.code, 'BAD_DAYS_PRESENT');
  assertTrue(/28 days/.test(r.error.message), 'should name the real length of February');
});

// ── INDIANA: the bulletin's own worked example ───────────────────────────
// BT2025190: "Assisted living resident is present from Jan. 1 through Jan. 15
// and then absent ... The provider can submit a claim using the monthly billing
// method since the resident was present in the facility for a minimum of 15
// days. ... the provider may submit their claim on or after Jan. 16"
check('BT2025190 worked example: 15 days present permits MONTHLY billing', () => {
  const r = pr.routeHcbsClaim({ rule: IN_CURRENT, service_month: '2026-01', days_present: 15, tier: 'tier2', preferred_method: 'monthly' });
  assertEq(r.ok, true);
  assertEq(r.method, 'monthly');
  assertEq(r.line.billing_string, 'T2031 U7 UA U2');
});

check('BT2025190 worked example: monthly claim is submittable at 15 days present, NOT month end', () => {
  const r = pr.routeHcbsClaim({ rule: IN_CURRENT, service_month: '2026-01', days_present: 15, tier: 'tier2', preferred_method: 'monthly' });
  assertEq(r.line.earliest_submission.basis, 'days_present');
  assertEq(r.line.earliest_submission.days_present_required, 15);
  // The original brief said "only after the full month is rendered" -- that is the
  // superseded rule. Assert we did NOT encode it.
  assertTrue(!/2026-01-31/.test(JSON.stringify(r.line.earliest_submission)),
    'must not require month-end submission under the current Indiana rule');
});

check('under 15 days present, Indiana monthly is unavailable and daily is chosen', () => {
  const r = pr.routeHcbsClaim({ rule: IN_CURRENT, service_month: '2026-01', days_present: 9, tier: 'tier1' });
  assertEq(r.ok, true);
  assertEq(r.method, 'daily');
  assertEq(r.line.billing_string, 'T2031 U7 U1');
  assertEq(r.line.units, 9, 'daily units must equal real days present');
});

check('when Indiana permits BOTH methods, the engine returns a provider CHOICE, never silently picks', () => {
  const r = pr.routeHcbsClaim({ rule: IN_CURRENT, service_month: '2026-01', days_present: 20, tier: 'tier3' });
  assertEq(r.ok, true);
  assertEq(r.decision, 'provider_choice');
  assertEq(r.options.length, 2);
  assertEq(r.options[0].billing_string, 'T2031 U7 UA U3');
  assertEq(r.options[1].billing_string, 'T2031 U7 U3');
  assertEq(r.method, undefined, 'must not assert a single method when the state permits either');
});

check('Indiana daily is capped at 29 days -- a 31-day stay cannot route to daily', () => {
  const r = pr.routeHcbsClaim({ rule: IN_CURRENT, service_month: '2026-01', days_present: 31, tier: 'tier1' });
  assertEq(r.ok, true);
  assertEq(r.method, 'monthly', 'above the 29-day daily cap only monthly remains');
});

check('the SUPERSEDED Indiana mandate cannot be used even if handed to the engine directly', () => {
  const r = pr.routeHcbsClaim({ rule: IN_SUPERSEDED, service_month: '2026-01', days_present: 31, tier: 'tier1' });
  assertEq(r.ok, false);
  assertEq(r.error.code, 'NO_RULE_IN_FORCE');
});

// ── OHIO ─────────────────────────────────────────────────────────────────
check('Ohio routes daily with the tier modifier only (no U7/UA -- those are Indiana’s)', () => {
  const r = pr.routeHcbsClaim({ rule: OH, service_month: '2026-05', days_present: 31, tier: 'tier3' });
  assertEq(r.ok, true);
  assertEq(r.method, 'daily');
  assertEq(r.line.billing_string, 'T2031 U3');
  assertEq(r.line.units, 31);
  assertEq(r.line.claim_form, 'CMS-1500');
});

check('Ohio carries its real constraints, including bed-hold and no-balance-billing', () => {
  const r = pr.routeHcbsClaim({ rule: OH, service_month: '2026-05', days_present: 31, tier: 'tier1' });
  const joined = r.constraints.join(' | ');
  assertTrue(/[Bb]ed hold/.test(joined), 'bed hold rule must be surfaced');
  assertTrue(/payment in full/i.test(joined), 'no-balance-billing rule must be surfaced');
  assertTrue(/[Rr]oom and board/.test(joined), 'room and board exclusion must be surfaced');
});

check('Ohio tier is NOT the facility certification track -- the constraint says so explicitly', () => {
  const joined = OH.data.constraints.join(' | ');
  assertTrue(/NOT the facility's certification track/.test(joined),
    'the basic-vs-memory-care / critical-access distinction must be stated, since the original spec had it wrong');
});

check('NO dollar rate appears anywhere in any seeded rule', () => {
  const blob = JSON.stringify(seed.rules);
  // Any bare currency figure would be a fabricated rate -- none were verifiable.
  assertTrue(!/\$\s?\d/.test(blob), 'seed must not contain dollar figures');
  assertEq(OH.data.additional_services[0].cumulative_max, null, 'unverified T2038 cap must stay null, not a guessed 2000');
});

check('every seeded rule carries a real citation with a resolvable URL and a quote', () => {
  seed.rules.forEach((r) => {
    const a = r.data.authority;
    assertTrue(a && a.citation, r.rule_id + ' missing citation');
    assertTrue(a && /^https?:\/\//.test(a.url || ''), r.rule_id + ' missing resolvable URL');
    assertTrue(a && a.quote && a.quote.length > 40, r.rule_id + ' missing a real source quote');
  });
});

// ── HOSPICE / MEDICARE ADVANTAGE ─────────────────────────────────────────
check('routing does not apply until hospice is actually elected', () => {
  const r = pr.routeHospiceClaim({ rule: HOSPICE, service_month: '2026-05', hospice_election: false });
  assertEq(r.ok, false);
  assertEq(r.error.code, 'NO_HOSPICE_ELECTION');
});

check('relatedness is never inferred -- an unstated determination is refused', () => {
  const r = pr.routeHospiceClaim({
    rule: HOSPICE, service_month: '2026-05', hospice_election: true,
    claim_principal_diagnosis: 'J18.9', hospice_principal_diagnosis: 'C34.90'
  });
  assertEq(r.ok, false);
  assertEq(r.error.code, 'MISSING_RELATEDNESS');
});

check('a missing hospice principal diagnosis is refused rather than assumed', () => {
  const r = pr.routeHospiceClaim({
    rule: HOSPICE, service_month: '2026-05', hospice_election: true,
    claim_principal_diagnosis: 'J18.9', relatedness: 'unrelated'
  });
  assertEq(r.ok, false);
  assertEq(r.error.code, 'MISSING_HOSPICE_DIAGNOSIS');
});

check('care RELATED to the terminal diagnosis routes to FFS Medicare, not the MA plan', () => {
  const r = pr.routeHospiceClaim({
    rule: HOSPICE, service_month: '2026-05', hospice_election: true, claim_type: 'professional',
    claim_principal_diagnosis: 'C34.90', hospice_principal_diagnosis: 'C34.90', relatedness: 'related'
  });
  assertEq(r.ok, true);
  assertEq(r.payer, 'ffs_medicare_hospice');
  assertEq(r.modifier, 'GV');
});

check('care UNRELATED with a different diagnosis routes to the MA plan with GW', () => {
  const r = pr.routeHospiceClaim({
    rule: HOSPICE, service_month: '2026-05', hospice_election: true, claim_type: 'professional',
    claim_principal_diagnosis: 'S72.001A', hospice_principal_diagnosis: 'C34.90', relatedness: 'unrelated'
  });
  assertEq(r.ok, true);
  assertEq(r.payer, 'medicare_advantage_plan');
  assertEq(r.modifier, 'GW');
  assertEq(r.diagnosis_match, false);
});

check('institutional unrelated claims use condition code 07, not GW', () => {
  const r = pr.routeHospiceClaim({
    rule: HOSPICE, service_month: '2026-05', hospice_election: true, claim_type: 'institutional',
    claim_principal_diagnosis: 'S72.001A', hospice_principal_diagnosis: 'C34.90', relatedness: 'unrelated'
  });
  assertEq(r.modifier, 'Condition Code 07');
});

// THE MM14219 CASE -- the whole reason this is a diagnosis comparison and not
// just a modifier check.
check('CR 14219: "unrelated" + EXACT diagnosis match is REFUSED, not billed with GW', () => {
  const r = pr.routeHospiceClaim({
    rule: HOSPICE, service_month: '2026-05', hospice_election: true, claim_type: 'professional',
    claim_principal_diagnosis: 'C34.90', hospice_principal_diagnosis: 'C34.90', relatedness: 'unrelated'
  });
  assertEq(r.ok, false);
  assertEq(r.error.code, 'DX_MATCH_WOULD_DENY');
  assertTrue(/CR 14219/.test(r.error.message), 'refusal must cite the controlling edit');
  assertTrue(/2026-04-01/.test(r.error.message), 'refusal must name the effective date');
  assertEq(r.modifier, undefined, 'a refusal must never hand back a billable modifier');
});

check('the diagnosis match is normalized -- formatting differences still count as a match', () => {
  const r = pr.routeHospiceClaim({
    rule: HOSPICE, service_month: '2026-05', hospice_election: true, claim_type: 'institutional',
    claim_principal_diagnosis: 'c34.90 ', hospice_principal_diagnosis: 'C3490', relatedness: 'unrelated'
  });
  assertEq(r.ok, false);
  assertEq(r.error.code, 'DX_MATCH_WOULD_DENY');
});

// ── COVERAGE ─────────────────────────────────────────────────────────────
// ── COVERAGE, AFTER MI AND PA WERE RESEARCHED (2026-08-23) ───────────────
// MI and PA now HAVE rules. `have` deliberately did not move, and this pair of
// checks is the guard on that: seeding a state must not be able to raise the
// coverage number unless the app can actually produce a claim for it.
check('coverage still reports 2 of 4 -- seeding MI and PA did NOT create a fake 4-of-4', () => {
  const c = pr.hcbsCoverage(seed.rules, ['OH', 'IN', 'MI', 'PA']);
  assertEq(c.have, 2, 'only OH and IN can actually be routed');
  assertEq(c.need, 4);
  assertEq(c.covered_states.sort(), ['IN', 'OH']);
  assertEq(c.reference_only_states.sort(), ['MI', 'PA']);
  assertEq(c.uncovered_states, [], 'no claimed state is now without any rule at all');
  assertTrue(/NOT counted as covered/.test(c.note || ''), 'the distinction has to be stated, not just structural');
});

check('a reference-only state REFUSES to route and returns its real codes instead of a claim', () => {
  ['MI', 'PA'].forEach((st) => {
    const rule = seed.rules.find((r) => r.state === st && r.program === 'medicaid_hcbs');
    assertTrue(!!rule, st + ' must now be seeded');
    assertEq(rule.data.billing_model, 'reference_only');
    const r = pr.routeHcbsClaim({ rule: rule, service_month: '2026-05', days_present: 30 });
    assertEq(r.ok, false, st + ' must not produce a claim');
    assertEq(r.error.code, 'NOT_ROUTABLE');
    assertEq(r.line, undefined, 'a refusal must never carry a billable line');
    assertEq(r.options, undefined);
    assertTrue(Array.isArray(r.codes) && r.codes.length > 0, st + ' must still hand back the real codes for reference');
    assertTrue(r.codes.every((c) => !!c.code && !!c.unit), 'every reference code needs its unit — a code without a unit invites the wrong unit count');
    assertTrue(!!r.authority && /^https?:\/\//.test(r.authority.url || ''), st + ' needs a resolvable source');
  });
});

check('supplying a tier to a tierless state is REFUSED, not silently ignored', () => {
  const mi = seed.rules.find((r) => r.state === 'MI');
  assertEq(mi.data.tier_model, 'none');
  // Reference-only is checked first, so use a synthetic routable tierless rule
  // to exercise the tier branch itself.
  const tierless = { rule_id: 'X', state: 'XX', effective_from: '2020-01-01', data: { tier_model: 'none', daily: { code: 'X0001', unit: '1 day' } } };
  const withTier = pr.routeHcbsClaim({ rule: tierless, service_month: '2026-05', days_present: 10, tier: 'tier1' });
  assertEq(withTier.ok, false);
  assertEq(withTier.error.code, 'TIER_NOT_APPLICABLE');
  const withoutTier = pr.routeHcbsClaim({ rule: tierless, service_month: '2026-05', days_present: 10 });
  assertEq(withoutTier.ok, true, 'a tierless state must route without a tier');
  assertEq(withoutTier.line.billing_string, 'X0001', 'no stray modifier from an unresolved <TIER>');
});

check('a rule that declares neither tier_model nor tier_modifiers is a DATA DEFECT, named as one', () => {
  // Before this, such a rule returned MISSING_TIER with an empty tier list --
  // asking the user to supply one of nothing, and blaming them for the gap.
  const broken = { rule_id: 'BROKEN-1', state: 'XX', effective_from: '2020-01-01', data: { daily: { code: 'X0001', unit: '1 day' } } };
  const r = pr.routeHcbsClaim({ rule: broken, service_month: '2026-05', days_present: 10 });
  assertEq(r.ok, false);
  assertEq(r.error.code, 'MALFORMED_RULE');
  assertTrue(/BROKEN-1/.test(r.error.message), 'the message must name the offending rule');
});

check('a state with no rule at all still fails closed', () => {
  const r = pr.routeHcbsClaim({ rule: undefined, service_month: '2026-05', days_present: 30, tier: 'tier1' });
  assertEq(r.ok, false);
  assertEq(r.error.code, 'NO_RULE');
});

check('every reference-only rule states WHY it is not routable, in its own data', () => {
  seed.rules.filter((r) => r.data && r.data.billing_model === 'reference_only').forEach((r) => {
    assertTrue((r.data.not_routable_reason || '').length > 60,
      r.rule_id + ' must explain why it cannot be routed — "not supported" is not a reason');
    assertTrue(Array.isArray(r.data.unverified) && r.data.unverified.length > 0,
      r.rule_id + ' must state what is still unverified rather than implying the research is complete');
  });
});

check('every seeded HCBS rule carries a citation, a resolvable URL and a real quote', () => {
  seed.rules.forEach((r) => {
    const a = (r.data || {}).authority;
    assertTrue(a && a.citation, r.rule_id + ' missing citation');
    assertTrue(a && /^https?:\/\//.test(a.url || ''), r.rule_id + ' missing resolvable URL');
    assertTrue(a && (a.quote || '').length > 40, r.rule_id + ' missing a real source quote');
    assertTrue(a && /^\d{4}-\d{2}-\d{2}$/.test(a.read_on || ''), r.rule_id + ' missing the verification date');
  });
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
