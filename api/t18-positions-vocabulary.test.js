// api/t18-positions-vocabulary.test.js
//
// Run:  node api/t18-positions-vocabulary.test.js
//
// T18 (cody, routed to hank b13) and the second half of N3, which sit in the
// SAME function and are the same class.
//
//   T18  `mappable` accepted ANY non-empty `applies_to_positions` array
//        without checking its CONTENTS against STAFF_POSITIONS, while the very
//        next leg of the same expression validated `audience` against it. So a
//        requirement declaring ['rn'] was counted MAPPED, left out of
//        `unmapped_requirements_caveat`, and then matchAudience returned a
//        DECIDED `applies: false` for every real position, because
//        `list.indexOf()` can never match a token that is not a position. A
//        training requirement that applies to nobody, reported as a decision
//        rather than as a gap.
//
// THE RULE THIS BATCH IS ARMING: an unmatchable position list is UNDECIDED
// (`applies: null`) and counts as unmapped -- never a silent drop, and never a
// confident `false`. A PARTIALLY valid list keeps its valid tokens, decides
// `true` for a person those tokens name, and REFUSES to decide `false` for
// anybody else while an unrecognised token is still on the row -- a typo
// ('rn' for 'nursing') must not read as "this person is excluded".
//
// Every arm drives the real exported `normalizeRequirements`, `matchAudience`
// and `evaluateTraining`. No reimplementation: a reimplementation passes
// against the unfixed code, which is the failure mode this platform keeps
// paying for.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const rules = require('./_lib/compliance-rules');

let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(l) { pass++; console.log('  ok       ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL     ' + l);
  if (why) console.log('           ' + String(why).slice(0, 400));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 400));
}
function is(c, l, why) { if (c) ok(l); else bad(l, why); }

// A rule row in the shape evaluateTraining really takes -- a LIST of rows,
// each with `data.requirements` -- read off the real call site, not guessed.
function ruleWith(reqs, id) {
  return [{ rule_id: id || 'T18-RULE', state: 'XX', requirement_type: 'training',
            facility_class: 'alf', effective_from: '2020-01-01',
            data: { requirements: reqs } }];
}
function normOne(req) {
  return rules.normalizeRequirements(ruleWith([req])[0])[0];
}

const POSITIONS = rules.STAFF_POSITIONS;

console.log('T18. an unmatchable position list is UNDECIDED, not a decided no');

// ── 1. THE WHOLE LIST IS UNRECOGNISED ───────────────────────────────────────
{
  const r = normOne({ who: 'registered nurses', annual_hours: 8,
                      applies_to_positions: ['rn'] });
  const m = rules.matchAudience(r, { position: 'nursing' });
  is(m.applies === null,
     'T18a. a requirement declaring applies_to_positions:[\'rn\'] is UNDECIDED '
   + 'for a real position, not a decided false. `rn` is not in '
   + 'alf_staff.position (' + POSITIONS.join('|') + '), so indexOf can never '
   + 'match it and the old `false` was the matcher reporting a vocabulary gap '
   + 'as a determination about a person',
     'applies=' + JSON.stringify(m.applies) + ' why=' + JSON.stringify(String(m.why).slice(0, 160)));
  is(/\brn\b/.test(String(m.why)) && /alf_staff\.position/.test(String(m.why)),
     'T18b. ...and the reason NAMES the unrecognised token and the vocabulary '
   + 'it was checked against. An unmatchable list that is merely undecided, '
   + 'without saying WHICH token could not be read, is the silent drop one '
   + 'step later',
     'why=' + JSON.stringify(String(m.why).slice(0, 200)));
  is(Array.isArray(r.positions_unknown) && r.positions_unknown.length === 1
     && r.positions_unknown[0] === 'rn',
     'T18c. ...and the normalised row carries `positions_unknown` so a reader '
   + 'of the row -- not only a reader of one match result -- can see the '
   + 'declared token that does not exist',
     JSON.stringify(r.positions_unknown));
}

// ── 2. THE RULE-LEVEL CAVEAT, which is what T18 was actually about ──────────
{
  // `opts.staff` IS REQUIRED TO REACH THIS BLOCK -- `unmapped_requirements` is
  // computed inside `if (Array.isArray(opts.staff))` at :825. The first draft of
  // this arm omitted it and failed against the FIXED code, reporting the fix
  // as absent; the arm was measuring the fixture. Found by reading the output
  // and then the branch, not by trusting the exit code.
  const out = rules.evaluateTraining(
    ruleWith([{ who: 'registered nurses', annual_hours: 8,
                applies_to_positions: ['rn'] }], 'T18-UNMAPPED'),
    { state: 'XX', facility_class: 'alf', on_date: '2026-06-01',
      staff: [{ staff_id: 'S1', position: 'caregiver', annual_hours_recorded: 0,
                applies_to: [] }] });
  const un = (out && out.unmapped_requirements) || [];
  is(un.length === 1 && un[0].key === 'T18-UNMAPPED#0' && un[0].annual_hours === 8,
     'T18d. the row appears in `unmapped_requirements`. This is the finding '
   + 'T18 names: `mappable` accepted the array for being non-empty, so the '
   + 'row was counted MAPPED and the caveat told the reader every requirement '
   + 'in the rule had been attributed',
     JSON.stringify(un).slice(0, 220));
  is(typeof out.unmapped_requirements_caveat === 'string'
     && /1 of 1/.test(out.unmapped_requirements_caveat),
     'T18e. ...and the caveat counts it, so `meets: true` elsewhere cannot be '
   + 'read as compliant',
     String(out.unmapped_requirements_caveat).slice(0, 140));
}

// ── 3. THE PER-STAFF VERDICT STOPS BEING A CONFIDENT "NOTHING APPLIES" ──────
//
// `applicable` inside evaluateStaffing/evaluateTraining filters on `s.applies_to`
// and NOT on matchAudience -- the audience decision is made by the CALLER and
// handed in. The real caller is api/sd-data.js, which builds it as
//
//     normReqs.filter((r) => matchAudience(r, person).applies === true).map(r => r.who)
//
// so an arm that omits `applies_to` is measuring a path production never takes
// (every row applicable, hours summed for requirements the response says do not
// apply). MIRRORED HERE, and T18q below FAILS if that line in api/sd-data.js
// stops looking like this -- a mirror nothing re-checks is the stale-anchor
// shape this repo keeps paying for.
function appliesToAsEndpointBuildsIt(reqs, position) {
  return rules.normalizeRequirements(ruleWith(reqs)[0])
    .filter(function (r) { return rules.matchAudience(r, { position: position }).applies === true; })
    .map(function (r) { return r.who; });
}
{
  const reqs = [{ who: 'registered nurses', annual_hours: 8,
                  applies_to_positions: ['rn'] }];
  const out = rules.evaluateTraining(ruleWith(reqs, 'T18-STAFF'),
    { state: 'XX', facility_class: 'alf', on_date: '2026-06-01',
      staff: [{ staff_id: 'S1', position: 'caregiver', annual_hours_recorded: 0,
                applies_to: appliesToAsEndpointBuildsIt(reqs, 'caregiver') }] });
  const f = (out && out.staff_findings && out.staff_findings[0]) || null;
  if (!f) {
    cannot('T18f. evaluateTraining returned no staff finding, so the verdict '
         + 'could not be measured', JSON.stringify(out).slice(0, 200));
    cannot('T18g. depends on T18f', 'no finding');
  } else {
    is(f.meets === null
       && !/^No requirement in this rule applies to this position/
            .test(String(f.meets_unknown_reason)),
       'T18f. the per-staff reason is no longer the CONFIDENT "no requirement '
     + 'in this rule applies to this position". That sentence is a claim about '
     + 'the rule a surveyor reads; what actually happened is that the rule '
     + 'named an audience this code cannot read. Both ways round the '
     + 'applicable set is empty, so the VERDICT does not move -- the sentence '
     + 'beside it does, and the sentence is the finding',
       'meets=' + JSON.stringify(f.meets) + ' reason='
     + JSON.stringify(String(f.meets_unknown_reason).slice(0, 180)));
    is(f.excluded_by_position === undefined,
       'T18g. ...and the row is NOT listed as an exclusion. `excluded_by_'
     + 'position` means "considered and did not apply to this position", which '
     + 'is a determination -- an unreadable audience has not been determined',
       JSON.stringify(f.excluded_by_position));
  }
}

// ── 4. A PARTIALLY VALID LIST: the valid tokens still work ──────────────────
{
  const r = normOne({ who: 'caregivers and RNs', annual_hours: 6,
                      applies_to_positions: ['caregiver', 'rn'] });
  const yes = rules.matchAudience(r, { position: 'caregiver' });
  is(yes.applies === true,
     'T18h. a list with one real token and one unrecognised token still '
   + 'DECIDES true for the person the real token names. An unrecognised token '
   + 'can only widen an audience, never narrow it, so `true` stays true',
     'applies=' + JSON.stringify(yes.applies));
  is(/\brn\b/.test(String(yes.why)),
     'T18i. ...and the unrecognised token is still disclosed on that true, '
   + 'because the row is wrong whether or not this particular person matched',
     'why=' + JSON.stringify(String(yes.why).slice(0, 200)));
  const no = rules.matchAudience(r, { position: 'nursing' });
  is(no.applies === null,
     'T18j. ...and it REFUSES to decide false for anybody else while `rn` is '
   + 'unread. `rn` is most plausibly a typo for `nursing`, and a confident '
   + 'false here would exclude exactly the person the author meant to include '
   + '-- under-inclusion arriving through a spelling mistake',
     'applies=' + JSON.stringify(no.applies) + ' why='
   + JSON.stringify(String(no.why).slice(0, 160)));
}

// ── 5. CONTROLS. These must be GREEN before the fix as well as after; an arm
//    that only ever goes one way is not measuring a boundary.
console.log('\nT18 controls -- a fully valid list is unchanged in both directions');
{
  const r = normOne({ who: 'caregivers', annual_hours: 6,
                      applies_to_positions: ['caregiver'] });
  is(rules.matchAudience(r, { position: 'caregiver' }).applies === true,
     'T18k. CONTROL -- an all-valid list still decides TRUE for a named position');
  is(rules.matchAudience(r, { position: 'nursing' }).applies === false,
     'T18l. CONTROL -- an all-valid list still decides FALSE for a position it '
   + 'does not name. This is the arm that stops the fix from turning every '
   + 'exclusion into an undecided, which would be the opposite fabrication',
     JSON.stringify(rules.matchAudience(r, { position: 'nursing' })));
  is(r.positions_unknown === null || r.positions_unknown === undefined,
     'T18m. CONTROL -- `positions_unknown` is absent when every token is real, '
   + 'not an empty array on every row',
     JSON.stringify(r.positions_unknown));
  const out = rules.evaluateTraining(
    ruleWith([{ who: 'caregivers', annual_hours: 6,
                applies_to_positions: ['caregiver'] }], 'T18-CTRL'),
    { state: 'XX', facility_class: 'alf', on_date: '2026-06-01',
      staff: [{ staff_id: 'S1', position: 'caregiver', annual_hours_recorded: 6,
                applies_to: ['caregivers'] }] });
  is(out.unmapped_requirements === undefined,
     'T18n. CONTROL -- an all-valid list is still MAPPED and raises no caveat',
     JSON.stringify(out.unmapped_requirements));
}
{
  // N3's malformed-SHAPE path is a different fact from an unreadable TOKEN and
  // must keep its own reason. Two wrong things, two sentences.
  const r = normOne({ who: 'caregivers', annual_hours: 6,
                      applies_to_positions: 'caregiver' });
  const m = rules.matchAudience(r, { position: 'caregiver' });
  is(m.applies === null && /wrong shape/.test(String(m.why)),
     'T18o. CONTROL -- a present-but-wrong-SHAPED list (a string) still gets '
   + 'N3\'s shape reason, not the new token reason',
     'applies=' + JSON.stringify(m.applies) + ' why='
   + JSON.stringify(String(m.why).slice(0, 120)));
  is(rules.matchAudience(normOne({ who: 'all', annual_hours: 4,
                                   audience: 'all_staff' }),
                         { position: 'caregiver' }).applies === true,
     'T18p. CONTROL -- all_staff still answers before anything else');
}
{
  // THE MIRROR IS RE-REFERENCED AGAINST THE SOURCE, not trusted. If the
  // endpoint stops building `applies_to` from `applies === true`, the arms
  // above are measuring a path nothing takes and would keep passing.
  const fs = require('fs');
  const path = require('path');
  const src = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
  is(/matchAudience\(r,\s*person\)\.applies\s*===\s*true/.test(src),
     'T18q. api/sd-data.js still builds `applies_to` from '
   + '`matchAudience(r, person).applies === true`, so the fixture in section 3 '
   + 'is still the production path. An undecided row is excluded from '
   + '`applies_to` by that `=== true`, which is why the fix needs no change '
   + 'there',
     'the filter expression was not found in api/sd-data.js');
}

console.log('\n' + pass + ' passed, ' + fail + ' failed, ' + unproven + ' unproven');
if (failed.length) console.log(failed.length + ' ARM(S) FAILED: ' + failed.join(', '));
if (notProved.length) console.log(notProved.length + ' ARM(S) UNPROVEN: ' + notProved.join(', '));
process.exit(fail ? 1 : (unproven ? 3 : 0));
