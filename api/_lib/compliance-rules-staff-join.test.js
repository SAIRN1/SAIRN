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

section('1. AN UNREADABLE REQUIREMENT VOCABULARY IS REFUSED, NEVER SUMMED');
const wvOut = e.evaluateTraining(wv, {
  state: 'WV', facility_class: wv[0].facility_class,
  on_date: '2026-09-26', staff: NOBODY
});
ok('WV refuses instead of producing a staff finding',
   wvOut.ok === false, JSON.stringify(wvOut).slice(0, 220));
ok('...with a code a caller can branch on', wvOut.ok === false
   && wvOut.error && wvOut.error.code === 'REQUIREMENTS_NOT_JOINABLE',
   JSON.stringify(wvOut.error || {}).slice(0, 200));
ok('...naming the state and the rule, so the reader knows WHICH rule is '
   + 'unreadable rather than that something is',
   wvOut.ok === false && wvOut.state === 'WV' && !!wvOut.rule_id,
   JSON.stringify(wvOut).slice(0, 200));
ok('...and it does NOT claim the untrained staff member meets anything',
   !wvOut.staff_findings);

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
ok('...so Ohio also declines to guess a verdict rather than over-requiring',
   ohOut.staff_findings[0].meets === null
   && /OVER-requires/.test(ohOut.staff_findings[0].meets_unknown_reason || ''),
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
ok('the verdict is NULL, not true and not false -- the question is not '
   + 'answerable from one recorded total',
   f && f.meets === null, JSON.stringify(f || {}).slice(0, 220));
ok('...and the reason says WHY rather than leaving a null to be read as false',
   f && typeof f.meets_unknown_reason === 'string'
   && /ADDITIVE/.test(f.meets_unknown_reason)
   && /UNDER-requires/.test(f.meets_unknown_reason), (f || {}).meets_unknown_reason);
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

section('5. THE DORMANCY IS ASSERTED, because it is the reason none of this '
        + 'reached a screen and it will stop being true');
const app = fs.readFileSync(path.join(REPO, 'sairncare.html'), 'utf8');
const callers = (app.match(/requirement_type\s*:\s*'training'/g) || []).length;
ok('sairncare.html still asks for training requirements somewhere',
   callers >= 1, 'callers=' + callers);
ok('...and still passes NO `staff` array, so the branch remains dormant -- '
   + 'when this arm goes red the caller has been built and the scoping doc '
   + 'should be re-read before trusting a verdict',
   !/staff\s*:\s*\[/.test(app.slice(Math.max(0, app.indexOf("requirement_type:'training'") - 600),
                                     app.indexOf("requirement_type:'training'") + 600)));

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
