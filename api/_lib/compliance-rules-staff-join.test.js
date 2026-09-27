// api/_lib/compliance-rules-staff-join.test.js
//
//   node api/_lib/compliance-rules-staff-join.test.js
//
// THE PER-STAFF TRAINING BRANCH, WHICH FABRICATED A COMPLIANCE PASS AND HAS
// NEVER FIRED.
//
// `evaluateTraining(rules, opts)` takes an optional `opts.staff` array and
// returns a per-person finding: required hours, recorded hours, shortfall,
// meets. NOTHING IN sairncare.html PASSES IT -- cqShowTraining() sends
// {state, facility_class, requirement_type} and nothing else -- so the branch
// is dormant. That is the only reason what it did has not reached a screen.
//
// WHAT IT DID, DRIVEN 2026-09-26 AGAINST THE REAL SEEDED RULES:
//
//   West Virginia, a staff member with ZERO recorded hours:
//     { required_annual_hours: 0, recorded_annual_hours: 0,
//       shortfall_hours: 0, meets: TRUE, applicable_requirements: [null,null] }
//
// WV mandates 8 hours a year for an administrator and 2 hours a year of
// dementia training for ALL staff. Its rows are `{audience, hours_per_year,
// topic}`; the branch reads `r.who` and `r.annual_hours`, so every requirement
// contributed `Number(undefined) || 0`. A DIFFERENT VOCABULARY READ AS AN
// EMPTY ONE -- and once summed, an empty requirement set is indistinguishable
// from a satisfied one.
//
// THE SECOND ONE IS QUIETER AND WORSE, because it survives a correct
// vocabulary. Pennsylvania PCH requires 12 general annual hours for direct
// care staff PLUS an ADDITIVE 6 for anyone in a secured dementia unit. The
// branch summed both into one target and compared one recorded total against
// it, so 18 hours of general training and no dementia training read as
// compliant. `additive: true` is on the real rule row; nothing was reading it.
//
// BOTH NOW REFUSE RATHER THAN GUESS, which is this module's own standard in
// its own words: "neither is ever silently substituted ... a substitution
// would produce a confident wrong answer rather than an honest gap."
//
// ── WHAT THESE ARMS DO NOT ASSERT ─────────────────────────────────────────
// Not that any staff member IS or IS NOT compliant. The records half of that
// join does not exist yet and cannot be built on the current rule shape --
// docs/2026-09-26-sairncare-compliance-join-scoping.md enumerates why. These
// arms assert that the engine refuses to answer what it cannot answer.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const REPO = path.dirname(path.dirname(__dirname));
const e = require('./compliance-rules');

let pass = 0, fail = 0;
function ok(name, cond, detail) {
  if (cond) { console.log('  ok   ' + name); pass++; }
  else { console.log('  FAIL ' + name + (detail ? '\n        ' + detail : '')); fail++; }
}
function section(t) { console.log('\n' + t); }

// THE REAL SEED, not a fixture. A fixture written from the same reading as the
// fix cannot contradict it, and the shapes that caused both defects are real
// rows a customer's facility is evaluated against.
const seedPath = path.join(REPO, 'sql', 'sairncare_compliance_seed.json');
const raw = JSON.parse(fs.readFileSync(seedPath, 'utf8'));
const rows = Array.isArray(raw) ? raw : (raw.rows || raw.rules || []);
const training = rows.filter(function (r) { return r.requirement_type === 'training'; });

const NOBODY = [{ staff_id: 'S-1', name: 'Nobody Trained', annual_hours_recorded: 0 }];

section('THE SEED ITSELF -- every arm below reads it, so a bad read must be loud');
ok('the compliance seed parses and carries training rules',
   training.length >= 5, 'found ' + training.length);
const wv = training.filter(function (r) { return r.state === 'WV'; });
const paPch = training.filter(function (r) { return r.state === 'PA' && r.facility_class === 'pch'; });
ok('the WV training rule is present -- the unreadable-vocabulary case',
   wv.length === 1, 'found ' + wv.length);
ok('the PA/pch training rule is present -- the additive-pool case',
   paPch.length === 1, 'found ' + paPch.length);
ok('...and PA/pch really does carry an `additive` requirement, so the arm '
   + 'below is not asserting against a field that has gone',
   (paPch[0] || {}).data && (paPch[0].data.requirements || [])
     .some(function (r) { return r.additive === true; }));
ok('...and WV really does carry rows with neither `who` nor `annual_hours`',
   (wv[0] || {}).data && (wv[0].data.requirements || [])
     .every(function (r) { return r.who === undefined && r.annual_hours === undefined; }));

// ── SECTION 1 RE-PINNED 2026-09-26 (Hank): WV IS READ, NOT REFUSED ─────────
// This section asserted that West Virginia is REFUSED, and that was the right
// assertion for as long as nothing could read `{audience, hours_per_year}`.
// normalizeRequirements() reads both vocabularies now, so WV answers -- which
// was the whole point of the refusal: it was a disclosed gap, never coverage,
// and the gap is closed.
//
// THE GUARD ITSELF IS STILL PROVEN LIVE, on a row readable in NEITHER
// vocabulary. Deleting the refusal arm along with the refusal would have removed
// the only evidence that an unreadable requirement is still not summed -- and
// summing one is the false PASS this whole suite exists about.
section('1. THE WV VOCABULARY IS READ NOW -- and the refusal still guards a row '
        + 'readable in NEITHER vocabulary');
const wvOut = e.evaluateTraining(wv, {
  state: 'WV', facility_class: wv[0].facility_class,
  on_date: '2026-09-26', staff: NOBODY
});
ok('WV produces a staff finding instead of refusing -- the disclosed gap is '
   + 'closed, and closing it is what the refusal was holding open',
   wvOut.ok === true && Array.isArray(wvOut.staff_findings),
   JSON.stringify(wvOut).slice(0, 220));
ok('...and an UNTRAINED staff member is FALSE, not true -- the original defect '
   + 'was this exact input returning meets:TRUE on zero recorded hours',
   wvOut.ok === true && wvOut.staff_findings[0].meets === false,
   JSON.stringify((wvOut.staff_findings || [])[0] || {}).slice(0, 220));
ok('...and the required figure is a real number read out of `hours_per_year`, '
   + 'not the 0 that `Number(undefined)||0` produced',
   wvOut.ok === true && wvOut.staff_findings[0].required_annual_hours > 0,
   String((wvOut.staff_findings || [])[0] || {}).slice(0, 80));
ok('...and the administrator requirement is listed as UNMAPPED rather than '
   + 'dropped -- an invisible requirement contributing zero is how the first '
   + 'version turned two real rows into a pass',
   Array.isArray(wvOut.unmapped_requirements)
   && wvOut.unmapped_requirements.length === 1
   && /never "compliant"/.test(wvOut.unmapped_requirements_caveat || ''),
   JSON.stringify(wvOut.unmapped_requirements || []).slice(0, 220));

// THE GUARD, on a synthetic row that no vocabulary reads. This is the arm that
// keeps section 1 meaningful now that WV passes.
const OPAQUE = [{
  rule_id: 'ZZ-TRAINING-OPAQUE', state: 'ZZ', requirement_type: 'training',
  facility_class: null, effective_from: '2020-01-01', effective_to: null,
  status: 'active',
  data: { label: 'a rule whose requirement rows this code cannot read',
          requirements: [{ personnel_group: 'everyone', yearly_clock_hours: 4 }] }
}];
const opaqueOut = e.evaluateTraining(OPAQUE, {
  state: 'ZZ', on_date: '2026-09-26', staff: NOBODY
});
ok('a requirement readable in NEITHER vocabulary is still REFUSED, not summed',
   opaqueOut.ok === false
   && opaqueOut.error.code === 'REQUIREMENTS_NOT_JOINABLE',
   JSON.stringify(opaqueOut).slice(0, 220));
ok('...naming the state and the rule, so a reader knows WHICH rule is '
   + 'unreadable rather than that something is',
   opaqueOut.ok === false && opaqueOut.state === 'ZZ' && !!opaqueOut.rule_id,
   JSON.stringify(opaqueOut).slice(0, 200));
ok('...and it does NOT claim the untrained staff member meets anything',
   !opaqueOut.staff_findings);

section('2. THE READABLE STATES STILL WORK -- refusing everything is not a fix');
const oh = training.filter(function (r) { return r.state === 'OH'; });
const ohOut = e.evaluateTraining(oh, {
  state: 'OH', facility_class: oh[0].facility_class, on_date: '2026-09-26', staff: NOBODY
});
ok('Ohio still evaluates', ohOut.ok === true, JSON.stringify(ohOut.error || {}));
ok('OHIO IS THE ARM THAT PROVES THE REFUSAL IS SELECTIVE -- its vocabulary '
   + 'IS readable, so it is not refused the way WV is',
   ohOut.ok === true && !!ohOut.staff_findings);
// AND OHIO IS THE OTHER HALF OF THE STACKING DEFECT, found while writing this
// arm. Its first two requirements carry `counts_toward_general_annual: true`
// -- 4 and 8 hours that count TOWARD the general 8 rather than adding to it --
// so summing all four rows gives 29 where the code requires less. That
// OVER-requires and produces a false FAIL: the merciful direction, and still a
// wrong number on a compliance board, which is how a screen teaches people to
// ignore it. Same refusal, opposite error.
ok('Ohio carries counts_toward_general_annual rows, so summation is wrong '
   + 'HERE TOO -- in the opposite direction to Pennsylvania',
   oh[0].data.requirements.some(function (r) {
     return r.counts_toward_general_annual === true;
   }));
// ── RE-PINNED 2026-09-26 (Hank) WHEN THE RECORDS JOIN LANDED ──────────────
// The verdict is still NULL and still for Ohio's reason, and the REASON TEXT is
// sharper because the diagnosis got sharper. `counts_toward_general_annual: true`
// says a row counts toward THE GENERAL ANNUAL requirement, and nothing on the
// rule says WHICH row that is -- so the pool it counts toward cannot be
// identified at all. That is a stronger statement than "summing OVER-requires":
// it names the one edit that would close it (declare the target row's key).
ok('...so Ohio also declines to guess a verdict rather than over-requiring',
   ohOut.staff_findings[0].meets === null
   && /COUNTS_TOWARD_GENERAL_ANNUAL/.test(ohOut.staff_findings[0].meets_unknown_reason || '')
   && /which row is the general annual one/i.test(ohOut.staff_findings[0].meets_unknown_reason || ''),
   JSON.stringify(ohOut.staff_findings[0]).slice(0, 220));
ok('...while still reporting the figures, so the screen is not left blank',
   ohOut.staff_findings[0].required_annual_hours > 0,
   String(ohOut.staff_findings[0].required_annual_hours));

section('3. SEPARATE POOLS ARE NOT APPORTIONED FROM ONE NUMBER');
const reqs = paPch[0].data.requirements;
const general = reqs.filter(function (r) { return /general annual/i.test(r.who || ''); });
const dementia = reqs.filter(function (r) { return r.additive === true; });
const applies = general.concat(dementia).map(function (r) { return r.who; });
// 18 hours of GENERAL training, none of the additive dementia hours. The old
// code summed 12 + 6 = 18 and answered `meets: true`.
const paOut = e.evaluateTraining(paPch, {
  state: 'PA', facility_class: 'pch', on_date: '2026-09-26',
  staff: [{ staff_id: 'S-9', name: 'General hours only',
            applies_to: applies, annual_hours_recorded: 18 }]
});
ok('PA/pch still evaluates -- an additive rule is readable, just not collapsible',
   paOut.ok === true, JSON.stringify(paOut.error || {}));
const f = (paOut.staff_findings || [])[0];
// ── RE-PINNED 2026-09-26 (Hank), AND THIS ONE CHANGED DIRECTION ───────────
// It asserted NULL for 18 recorded hours against a 42-hour set of pools, on the
// grounds that "the question is not answerable from one recorded total". That is
// true of the QUESTION and false of THIS NUMBER: the largest single applicable
// pool is 24 hours, and 18 cannot reach 24 under ANY apportionment. So FALSE is
// exact, and NULL was declining an answer the data already had.
//
// THE DETERMINABILITY RULE QUANTIFIES OVER ALL APPORTIONMENTS rather than
// picking one, which is why it is strictly more answerable and no less honest:
//   recorded >= SUM of every pool  -> TRUE  (no assignment fails)
//   recorded <  the LARGEST pool   -> FALSE (no assignment succeeds)
//   between                        -> NULL  (genuinely unapportionable)
// A TRUE now has to clear the SUM of every applicable requirement, which is the
// strictest available reading -- the summation defect was reporting a pass in the
// MIDDLE band while presenting the sum as one target.
ok('18 hours against a largest single pool of 24 is FALSE, not null -- no '
   + 'apportionment of 18 reaches 24, so declining to answer was declining '
   + 'an answer the data already had',
   f && f.meets === false, JSON.stringify(f || {}).slice(0, 220));
ok('...and it reports how many separate pools the person is subject to, so a '
   + 'false is readable as "at least one pool is unreachable"',
   f && f.applicable_pool_count >= 2, JSON.stringify(f || {}).slice(0, 220));
// AND THE MIDDLE BAND IS STILL NULL, which is the arm that keeps the change
// honest: without it "more answerable" could mean "always answers".
const paMid = e.evaluateTraining(paPch, {
  state: 'PA', facility_class: 'pch', on_date: '2026-09-26',
  staff: [{ staff_id: 'S-10', name: 'In the middle band',
            applies_to: applies, annual_hours_recorded: 30 }]
});
const fm = (paMid.staff_findings || [])[0];
ok('30 hours -- above the largest pool (24), below the sum (42) -- is NULL, '
   + 'because THAT is the band where attribution is the missing fact',
   fm && fm.meets === null, JSON.stringify(fm || {}).slice(0, 220));
ok('...and the reason names separate pools and what would close it',
   fm && typeof fm.meets_unknown_reason === 'string'
   && /SEPARATE/.test(fm.meets_unknown_reason)
   && /not attributed/.test(fm.meets_unknown_reason), (fm || {}).meets_unknown_reason);
ok('...and the rule-level caveat says how many additive requirements caused it',
   typeof paOut.staff_findings_caveat === 'string'
   && /stacking semantics/.test(paOut.staff_findings_caveat),
   paOut.staff_findings_caveat);
ok('THE RECORDED AND REQUIRED NUMBERS ARE STILL REPORTED, because a null '
   + 'verdict with no figures would be less useful than the wrong answer it '
   + 'replaces',
   f && f.recorded_annual_hours === 18 && f.required_annual_hours > 0,
   JSON.stringify(f || {}).slice(0, 160));

section('4. A NON-ADDITIVE STATE STILL GETS A BOOLEAN');
const inRule = training.filter(function (r) { return r.state === 'IN'; });
const inOut = e.evaluateTraining(inRule, {
  state: 'IN', facility_class: inRule[0].facility_class, on_date: '2026-09-26',
  staff: [{ staff_id: 'S-2', name: 'Fully trained', annual_hours_recorded: 999 }]
});
ok('Indiana answers TRUE for an over-trained staff member',
   inOut.ok === true && inOut.staff_findings[0].meets === true,
   JSON.stringify((inOut.staff_findings || [])[0] || {}).slice(0, 180));
ok('...and null is reserved for the pooled case, not used everywhere',
   inOut.staff_findings[0].meets_unknown_reason === null);

// ── SECTION 5 REWRITTEN 2026-09-26 (Hank), AND THE OLD ONE WAS A GHOST ────
// It asserted "the branch remains dormant" by checking that sairncare.html sends
// no `staff` array. That is a fact about the UI, and it was being read as a fact
// about REACHABILITY -- which stopped being true the moment the endpoint gained
// `include_staff`. The arm would have stayed green while the branch was
// reachable by any session holder: a check that reads as proving dormancy while
// the thing it describes has changed, which is the class
// docs/2026-09-26-ghost-failure-path-sweep.md is about.
//
// What it asserts now is the three separate facts, each on its own arm, so no
// one of them can be mistaken for another.
// ── 4b. AN EMPTY APPLICABLE SET IS NEVER A PASS ────────────────────────────
// RE-PINNED 2026-09-27 (Hank) when the position lists landed, and NOT reverted:
// this section used to drive OH/IN/PA on the grounds that EVERY audience there
// was prose so nothing matched. That is precisely what item 3 fixed, so those
// four rules now answer — the old assertion was made false ON PURPOSE.
//
// THE PROPERTY IS UNCHANGED AND STILL NEEDS AN ARM, so it is driven where the
// applicable set is genuinely empty rather than where it used to be: a `billing`
// position against a rule whose requirements are direct-care only.
//
// THE DEFECT IT GUARDS, kept because the first version of the records join
// shipped it: nothing matched, `applicable` was empty, the target summed to 0,
// and a caregiver with ZERO recorded hours came back `meets: true` — with the
// `unmapped_requirements` caveat sitting on the same response. This module's own
// sentence about the WV vocabulary bug, arriving through a third door: "an empty
// requirement set is indistinguishable from a satisfied one once it has been
// summed."
section('4b. AN EMPTY APPLICABLE SET IS NEVER A PASS');

// One driver for 4b/4c/4d. It builds `applies_to` the way api/sd-data.js does —
// through matchAudience() — rather than hand-listing `who` strings, so these arms
// exercise the same mapping the endpoint uses and cannot pass against a shape the
// product does not have.
function drive(rule, position, records, hire, extra) {
  const norm = e.normalizeRequirements(rule);
  const applies = norm
    .filter(function (r) { return e.matchAudience(r, { position: position }).applies === true; })
    .map(function (r) { return r.who; });
  return e.evaluateTraining([rule], Object.assign({
    state: rule.state, facility_class: rule.facility_class, on_date: '2026-09-27',
    staff: [{ staff_id: 'S', position: position, applies_to: applies,
              hire_date: hire, records: records }]
  }, extra || {}));
}
const LOTS = [{ hours: 500, category: 'general', completed_on: '2026-06-01' }];
const PCH = training.filter(function (r) {
  return r.state === 'PA' && r.facility_class === 'pch';
})[0];

const billingOut = drive(PCH, 'billing', LOTS, '2024-11-03');
const bf = (billingOut.staff_findings || [])[0];
ok('a position NO requirement maps to is meets:null even with 500 recorded '
   + 'hours -- the empty SET is the reason, not the hours',
   !!bf && bf.meets === null && bf.no_applicable_requirement === true,
   JSON.stringify(bf || billingOut).slice(0, 240));
ok('...and the reason says "we could not read who it applies to" rather than '
   + '"no obligation" -- only the rule author can make the second claim',
   !!bf && /could not read who it/.test(bf.meets_unknown_reason || ''),
   (bf || {}).meets_unknown_reason);
ok('...and it reports 0 required over 0 applicable pools, which is exactly the '
   + 'state that used to be summed into a pass',
   !!bf && bf.required_annual_hours === 0 && bf.applicable_pool_count === 0,
   JSON.stringify(bf || {}).slice(0, 200));

// ── 4c. THE POSITION LISTS, AND WHAT THEY DELIBERATELY REFUSE TO MAP ───────
// Item 3. Authored into sql/sairncare_compliance_seed.json from the code each row
// already cites, onto the real `alf_staff.position` vocabulary. The arms are
// about the DISTINCTION rather than the count: a row naming a ROLE CLASS is
// mapped, and a row naming an ASSIGNMENT ("staff serving residents with
// late-stage cognitive impairment") or a LICENSED OFFICE ("administrator") is
// not — neither is a fact about position, and mapping `owner` to `administrator`
// would be a licensure claim invented by a lookup table. Refused on 2026-09-26 in
// docs/CRITICALITY-TIERS.md for the same reason, and refused again here.
section('4c. the position lists map role classes and refuse assignments');
['OH', 'IN', 'PA'].forEach(function (st) {
  training.filter(function (r) { return r.state === st; }).forEach(function (rule) {
    const f = (drive(rule, 'caregiver', [], '2024-11-03').staff_findings || [])[0];
    ok(rule.rule_id + ': a caregiver with ZERO hours is FALSE now -- a real '
       + 'verdict where this rule used to answer null for want of an audience',
       !!f && f.meets === false && f.required_annual_hours > 0,
       JSON.stringify(f || {}).slice(0, 220));
    const over = (drive(rule, 'caregiver', LOTS, '2024-11-03').staff_findings || [])[0];
    ok(rule.rule_id + ': ...and TRUE when over-trained, so the verdict tracks the '
       + 'hours rather than being pinned one way by the mapping',
       !!over && over.meets === true, JSON.stringify(over || {}).slice(0, 220));
  });
});

const ohRule = training.filter(function (r) { return r.state === 'OH'; })[0];
const ohMapped = drive(ohRule, 'caregiver', LOTS, '2024-11-03');
ok('Ohio STILL DISCLOSES its unmapped requirements rather than dropping them -- '
   + 'two assignment rows and an administrator row are not facts about position, '
   + 'and a meets:true beside them means "meets what could be attributed", never '
   + '"compliant"',
   Array.isArray(ohMapped.unmapped_requirements)
   && ohMapped.unmapped_requirements.length === 3,
   JSON.stringify((ohMapped.unmapped_requirements || []).map(function (u) { return u.key; })));

ok('every mapped position token is in the REAL alf_staff.position vocabulary -- '
   + 'a token this app cannot store would match nobody and read as an exemption',
   (function () {
     const bad = [];
     training.forEach(function (rule) {
       ((rule.data || {}).requirements || []).forEach(function (q) {
         (q.applies_to_positions || []).forEach(function (t) {
           if (e.STAFF_POSITIONS.indexOf(t) === -1) bad.push(rule.rule_id + ':' + t);
         });
       });
     });
     return !bad.length;
   })(), 'unknown position tokens in the seed');

ok('...and every mapped row records the BASIS for its mapping, so a reader can '
   + 'disagree with the READING rather than with a bare list',
   (function () {
     const missing = [];
     training.forEach(function (rule) {
       ((rule.data || {}).requirements || []).forEach(function (q, i) {
         if (q.applies_to_positions && !q.applies_to_positions_basis) {
           missing.push(rule.rule_id + '#' + i);
         }
       });
     });
     return !missing.length;
   })(), 'a position list with no recorded basis');

ok('...and every row deliberately LEFT unmapped records why, so an absent list '
   + 'reads as a decision rather than as an omission somebody forgot',
   (function () {
     const bare = [];
     ['OH', 'IN', 'PA'].forEach(function (st) {
       training.filter(function (r) { return r.state === st; }).forEach(function (rule) {
         ((rule.data || {}).requirements || []).forEach(function (q, i) {
           if (!q.applies_to_positions && !q.positions_not_mappable) {
             bare.push(rule.rule_id + '#' + i);
           }
         });
       });
     });
     return !bare.length;
   })(), 'a requirement with neither a position list nor a recorded reason');

// ── 4d. THE ANNUAL WINDOW: DECIDED, ANCHORED, AND STILL REFUSING TO GUESS ──
// Item 4, Michael's decision. The three-way 400 is replaced by a COMPUTED
// DEFAULT: rolling twelve months ending on each staff member's most recent hire
// anniversary. Anchoring is not a detail — one facility-wide window makes
// somebody hired in November non-compliant for eleven months against a figure
// they have not had a year to earn, and the underlying requirements are already
// hire-relative ("within 6 months", "within the first 30 days of the date of
// hire", "in the first year of employment").
section('4d. the annual window is computed, anchored to hire, and names its own '
        + 'could-not-tell');
const WV1 = training.filter(function (r) { return r.state === 'WV'; })[0];

const anchored = (drive(WV1, 'caregiver', LOTS, '2024-11-03').staff_findings || [])[0];
ok('THE ANCHOR: hired 2024-11-03, evaluated 2026-09-27 -- the window opens '
   + '2025-11-03. Not a calendar year, and not 365 days counted back from today',
   !!anchored && anchored.hours_window_from === '2025-11-03',
   JSON.stringify(anchored || {}).slice(0, 260));
ok('...and the finding names the window AND what it means, because a verdict '
   + 'computed over a period the reader cannot see is one they cannot check -- '
   + 'and with a per-person anchor the period differs per row',
   !!anchored && anchored.hours_window === 'rolling_12_months_from_hire'
   && /hire anniversary/.test(anchored.hours_window_meaning || ''),
   JSON.stringify(anchored || {}).slice(0, 260));

const stale = (drive(WV1, 'caregiver',
  [{ hours: 500, category: 'general', completed_on: '2025-06-01' }],
  '2024-11-03').staff_findings || [])[0];
ok('hours BEFORE the window do not count: 500 hours dated 2025-06-01 fall in the '
   + 'PREVIOUS training year for a 2024-11-03 hire, so the verdict is FALSE',
   !!stale && stale.recorded_annual_hours === 0 && stale.meets === false,
   JSON.stringify(stale || {}).slice(0, 260));

const noHire = (drive(WV1, 'caregiver', LOTS, null).staff_findings || [])[0];
ok('THE ARM THAT MATTERS FOR THE WINDOW: no recorded hire date is meets:NULL, '
   + 'not false -- a total of zero derived from a MISSING FIELD would report a '
   + 'fully trained person as non-compliant, which is the empty-set defect one '
   + 'direction over',
   !!noHire && noHire.meets === null
   && noHire.hours_window_error === 'NO_HIRE_DATE',
   JSON.stringify(noHire || {}).slice(0, 260));
ok('...and the reason names the missing field and BOTH ways out, rather than '
   + 'leaving a null for a reader to interpret',
   !!noHire && /no recorded hire date/.test(noHire.meets_unknown_reason || '')
   && /facility-wide windows/.test(noHire.meets_unknown_reason || ''),
   (noHire || {}).meets_unknown_reason);

const future = (drive(WV1, 'caregiver', LOTS, '2027-01-01').staff_findings || [])[0];
ok('a hire date AFTER the evaluation date is named, not guessed past',
   !!future && future.meets === null
   && future.hours_window_error === 'HIRE_DATE_AFTER_EVALUATION',
   JSON.stringify(future || {}).slice(0, 220));

ok('THE DECISION IS A DEFAULT, NOT THE REMOVAL OF A CHOICE: the three '
   + 'facility-wide windows are all still available to a caller that states one',
   Object.keys(e.ANNUAL_WINDOWS).length === 4
   && !!e.ANNUAL_WINDOWS.rolling_12_months
   && !!e.ANNUAL_WINDOWS.calendar_year
   && !!e.ANNUAL_WINDOWS.facility_training_year,
   Object.keys(e.ANNUAL_WINDOWS).join(','));
ok('...and a caller-stated window is honoured over the default -- the same '
   + 'caregiver evaluated on the facility-wide rolling year sees a DIFFERENT '
   + 'window start, which is what proves the anchor is doing work',
   (function () {
     const f = (drive(WV1, 'caregiver', LOTS, '2024-11-03',
                      { annual_window: 'rolling_12_months' }).staff_findings || [])[0];
     return !!f && f.hours_window === 'rolling_12_months'
       && f.hours_window_from !== '2025-11-03';
   })());

section('5. WHAT REACHES THIS BRANCH, stated as three facts rather than one');
const app = fs.readFileSync(path.join(REPO, 'sairncare.html'), 'utf8');
const api = fs.readFileSync(path.join(REPO, 'api', 'sd-data.js'), 'utf8');
const callers = (app.match(/requirement_type\s*:\s*'training'/g) || []).length;
ok('sairncare.html still asks for training requirements somewhere',
   callers >= 1, 'callers=' + callers);
ok('FACT 1: the PANEL still does not ask for per-staff findings, so nothing in '
   + 'the UI shows one yet -- the window selector it would need is a product '
   + 'decision, not a wiring gap',
   !/include_staff/.test(app));
ok('FACT 2: the ENDPOINT can now reach the branch, which is what the old '
   + '"dormant" arm would have gone on denying -- api/sd-data.js builds '
   + '`opts.staff` from alf_staff_credentials behind include_staff',
   /include_staff/.test(api) && /alf_staff_credentials\?license_hash/.test(api));
ok('FACT 3: and a CALLER-SUPPLIED staff array is refused, which is the thing '
   + 'that made the old reachability dangerous rather than merely unused',
   /STAFF_NOT_CALLER_SUPPLIED/.test(api));

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
