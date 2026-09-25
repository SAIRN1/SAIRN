// api/_lib/mech-insurance.test.js
//
//   node api/_lib/mech-insurance.test.js
//
// THE TWO ARMS THAT MATTER ARE THE CLEARANCE ONES.
//
// A coverage engine fails in one direction that costs money and one that costs
// nothing. Reporting a contractor as NOT covered when they are is an annoyance;
// reporting them as covered when they are not is how somebody goes on a
// hospital roof with a lapsed policy. So every path that could produce a
// `met: true` from an absence is driven on purpose:
//
//   * a limit nobody typed must be UNKNOWN, not zero and not met
//   * an endorsement nobody recorded must be UNKNOWN, not carried
//   * a policy with no expiry must never read as current
//   * a policy the engine could not evaluate must not silently vanish, leaving
//     its requirement to be reported as merely unmet for an invisible reason
//
// And the money comparison is driven at the boundary, in cents, because
// `2000000.00 >= 2000000.00` in floats is exactly the class of comparison this
// platform already has a finding about (dnt-rollup, money summed as doubles).

'use strict';
const assert = require('assert');
const m = require('./mech-insurance');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n         ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

const TODAY = '2026-09-25';
const GL = {
  policy_id: 'P1', kind: 'general_liability', carrier: 'Acme Mutual',
  policy_no: 'GL-1', effective_on: '2026-01-01', expires_on: '2027-01-01',
  each_occurrence: 1000000, aggregate: 2000000,
  endorsements: { additional_insured: true, waiver_of_subrogation: true }
};

section('ONE POLICY: five states, and no-expiry is never current');

test('a live policy with limits is current', () => {
  const r = m.policyState({ today: TODAY, policy: GL });
  assert.strictEqual(r.state, 'current');
  assert.strictEqual(r.each_occurrence, 1000000);
  assert.deepStrictEqual(r.problems, []);
});

test('a policy expiring inside the warn window is expiring, not current', () => {
  const r = m.policyState({ today: TODAY, policy: Object.assign({}, GL, { expires_on: '2026-10-10' }) });
  assert.strictEqual(r.state, 'expiring');
  assert.strictEqual(r.days_left, 15);
});

test('the warn window is the callers, not this engine\'s', () => {
  const r = m.policyState({ today: TODAY, warn_days: 5,
    policy: Object.assign({}, GL, { expires_on: '2026-10-10' }) });
  assert.strictEqual(r.state, 'current');
});

test('a lapsed policy is expired with a negative day count', () => {
  const r = m.policyState({ today: TODAY, policy: Object.assign({}, GL, { expires_on: '2026-08-01' }) });
  assert.strictEqual(r.state, 'expired');
  assert.ok(r.days_left < 0);
});

test('A POLICY WITH NO EXPIRY IS NEVER current -- it is its own state, and it says why', () => {
  const p = Object.assign({}, GL); delete p.expires_on;
  const r = m.policyState({ today: TODAY, policy: p });
  assert.strictEqual(r.state, 'no_expiry_recorded');
  assert.ok(/cannot answer/.test(r.problems.join(' ')), r.problems.join(' '));
});

test('an expiry before the effective date is reported as a mistype', () => {
  const r = m.policyState({ today: TODAY,
    policy: Object.assign({}, GL, { effective_on: '2027-01-01', expires_on: '2026-01-01' }) });
  assert.ok(/mistyped/.test(r.problems.join(' ')), r.problems.join(' '));
});

test('an unknown coverage kind is REFUSED, not stored through into a silent bucket', () => {
  const r = m.policyState({ today: TODAY, policy: Object.assign({}, GL, { kind: 'cyber' }) });
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.error.code, 'UNKNOWN_KIND');
});

test('the engine will not assume a clock', () => {
  assert.strictEqual(m.policyState({ policy: GL }).error.code, 'NO_TODAY');
  assert.strictEqual(m.evaluateCoverage([GL], 'not-a-date').error.code, 'BAD_TODAY');
});

section('MONEY IS INTEGER CENTS AT THE BOUNDARY');

test('dollars convert to cents once, and back', () => {
  assert.strictEqual(m.cents(1000000), 100000000);
  assert.strictEqual(m.cents('2500.55'), 250055);
  assert.strictEqual(m.dollars(250055), 2500.55);
});

test('an ABSENT limit is null -- not zero, which would fail every requirement '
   + 'for a reason nobody typed', () => {
  assert.strictEqual(m.cents(null), null);
  assert.strictEqual(m.cents(''), null);
  assert.strictEqual(m.cents(undefined), null);
});

test('a negative or nonsense limit is null too, never a number', () => {
  assert.strictEqual(m.cents(-5), null);
  assert.strictEqual(m.cents('abc'), null);
  assert.strictEqual(m.cents(Infinity), null);
});

test('THE EXACT BOUNDARY: a limit equal to the requirement is MET, and one cent '
   + 'under is not -- driven in cents because floats are where this goes wrong', () => {
  const req = [{ kind: 'general_liability', each_occurrence: 2000000 }];
  const exact = m.coverageReadiness({ today: TODAY, requirements: req,
    policies: [Object.assign({}, GL, { each_occurrence: 2000000 })] });
  assert.strictEqual(exact.lines[0].met, true, exact.lines[0].reasons.join('; '));
  const under = m.coverageReadiness({ today: TODAY, requirements: req,
    policies: [Object.assign({}, GL, { each_occurrence: 1999999.99 })] });
  assert.strictEqual(under.lines[0].met, false);
});

section('READINESS: every way an ABSENCE could read as a pass');

test('THE ARM THAT MATTERS: a limit nobody typed is UNKNOWN, not met and not zero', () => {
  const p = Object.assign({}, GL); delete p.each_occurrence;
  const r = m.coverageReadiness({ today: TODAY, policies: [p],
    requirements: [{ kind: 'general_liability', each_occurrence: 1000000 }] });
  assert.strictEqual(r.lines[0].met, false);
  assert.ok(/UNKNOWN, not met and not zero/.test(r.lines[0].reasons.join(' ')),
    r.lines[0].reasons.join(' '));
});

test('AND THE SECOND: an endorsement nobody recorded is UNKNOWN, never carried', () => {
  const p = Object.assign({}, GL, { endorsements: {} });
  const r = m.coverageReadiness({ today: TODAY, policies: [p],
    requirements: [{ kind: 'general_liability', endorsements: ['additional_insured'] }] });
  assert.strictEqual(r.lines[0].met, false);
  assert.ok(/unknown is not carried/.test(r.lines[0].reasons.join(' ')),
    r.lines[0].reasons.join(' '));
});

test('an endorsement recorded as FALSE is a different sentence from unknown', () => {
  const p = Object.assign({}, GL, { endorsements: { additional_insured: false } });
  const r = m.coverageReadiness({ today: TODAY, policies: [p],
    requirements: [{ kind: 'general_liability', endorsements: ['additional_insured'] }] });
  assert.ok(/recorded as NOT carried/.test(r.lines[0].reasons.join(' ')));
});

test('a recorded TRUE endorsement satisfies, and nothing else does', () => {
  const r = m.coverageReadiness({ today: TODAY, policies: [GL],
    requirements: [{ kind: 'general_liability',
      endorsements: ['additional_insured', 'waiver_of_subrogation'] }] });
  assert.strictEqual(r.lines[0].met, true, r.lines[0].reasons.join('; '));
});

test('a policy with NO EXPIRY does not satisfy a requirement, and says it is not '
   + 'a finding that it lapsed', () => {
  const p = Object.assign({}, GL); delete p.expires_on;
  const r = m.coverageReadiness({ today: TODAY, policies: [p],
    requirements: [{ kind: 'general_liability' }] });
  assert.strictEqual(r.lines[0].met, false);
  assert.ok(/not a finding that it lapsed/.test(r.lines[0].reasons.join(' ')));
});

test('an EXPIRED policy does not satisfy, and the expiry date is named', () => {
  const r = m.coverageReadiness({ today: TODAY,
    policies: [Object.assign({}, GL, { expires_on: '2026-08-01' })],
    requirements: [{ kind: 'general_liability' }] });
  assert.strictEqual(r.lines[0].met, false);
  assert.ok(/expired on 2026-08-01/.test(r.lines[0].reasons.join(' ')));
});

test('an EXPIRING policy still satisfies -- it is a warning, not a lapse', () => {
  const r = m.coverageReadiness({ today: TODAY,
    policies: [Object.assign({}, GL, { expires_on: '2026-10-10' })],
    requirements: [{ kind: 'general_liability' }] });
  assert.strictEqual(r.lines[0].met, true, r.lines[0].reasons.join('; '));
  assert.strictEqual(r.counts.expiring, 1);
});

test('a coverage that is not recorded AT ALL is `missing`, named as such', () => {
  const r = m.coverageReadiness({ today: TODAY, policies: [GL],
    requirements: [{ kind: 'workers_comp' }] });
  assert.strictEqual(r.lines[0].state, 'missing');
  assert.ok(/no workers_comp policy is recorded at all/.test(r.lines[0].reasons.join(' ')));
});

test('AND THE FOURTH: a policy the engine could NOT evaluate is reported, not '
   + 'dropped -- and it blocks `ready` even when every line is met', () => {
  const r = m.coverageReadiness({ today: TODAY,
    policies: [GL, { kind: 'cyber', expires_on: '2027-01-01' }],
    requirements: [{ kind: 'general_liability' }] });
  assert.strictEqual(r.lines[0].met, true);
  assert.strictEqual(r.unusable_policies.length, 1);
  assert.strictEqual(r.ready, false, 'a packet with an unevaluable policy reported ready');
});

test('an unknown REQUIREMENT is never reported as met either', () => {
  const r = m.coverageReadiness({ today: TODAY, policies: [GL],
    requirements: [{ kind: 'cyber' }] });
  assert.strictEqual(r.lines[0].met, false);
  assert.strictEqual(r.lines[0].state, 'unknown_requirement');
  assert.ok(/NOT reporting that you meet it/.test(r.lines[0].reasons.join(' ')));
});

test('an unknown ENDORSEMENT is never reported as carried either', () => {
  const r = m.coverageReadiness({ today: TODAY, policies: [GL],
    requirements: [{ kind: 'general_liability', endorsements: ['sole_negligence'] }] });
  assert.strictEqual(r.lines[0].met, false);
  assert.ok(/NOT reporting that you carry it/.test(r.lines[0].reasons.join(' ')));
});

section('NO DEFAULT REQUIREMENT LIST, EVER');

test('with no requirements it REFUSES rather than inventing a standard packet', () => {
  const r = m.coverageReadiness({ today: TODAY, policies: [GL] });
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.error.code, 'NO_REQUIREMENTS');
  assert.ok(/will not be one/.test(r.error.message));
});

test('NEGATIVE CONTROL: the module seeds no limit, no kind list of requirements '
   + 'and no dollar figure anywhere in its source', () => {
  // ASSERTED ON THE CODE, NOT THE PROSE. The first version of this arm read
  // the whole file and went red on the header's own worked example --
  // `2000000.00 >= 2000000.00`, a sentence explaining why the comparison is in
  // cents. That is the grep-cannot-tell-code-from-text-describing-code class
  // (PR 1.2), inside a control written to catch a different mistake.
  const src = require('fs').readFileSync(require.resolve('./mech-insurance.js'), 'utf8');
  const code = src.split('\n')
    .filter(function (l) { return !/^\s*(\/\/|\*|\/\*)/.test(l); }).join('\n');
  // A seeded requirement would look like a limit constant. The only numbers
  // this file may carry are the warn window and cents arithmetic.
  assert.ok(!/\b(1000000|2000000|500000)\b/.test(code),
    'a dollar limit is seeded in the engine -- requirements are the caller\'s');
  assert.ok(!/DEFAULT_REQUIRE|REQUIRED_KINDS|STANDARD_PACKET/.test(code));
  // CONTROL ON THE CONTROL: the stripping really did remove the header, so the
  // arm above is judging code rather than passing on an empty string.
  assert.ok(code.length > 1000 && code.indexOf('function coverageReadiness') !== -1,
    'comment stripping removed the code as well as the prose');
});

section('THE BOARD');

test('the board counts every state and surfaces no-limit beside the totals', () => {
  const noLimit = Object.assign({}, GL, { policy_id: 'P2', kind: 'workers_comp' });
  delete noLimit.each_occurrence;
  const b = m.evaluateCoverage([GL, noLimit,
    Object.assign({}, GL, { policy_id: 'P3', kind: 'umbrella', expires_on: '2026-08-01' })], TODAY);
  assert.strictEqual(b.counts.current, 2);
  assert.strictEqual(b.counts.expired, 1);
  assert.strictEqual(b.no_limit_recorded_count, 1);
  assert.strictEqual(b.by_kind.general_liability, 1);
});

test('the board reports an unevaluable policy rather than shrinking the list', () => {
  const b = m.evaluateCoverage([GL, { kind: 'cyber' }], TODAY);
  assert.strictEqual(b.rows.length, 1);
  assert.strictEqual(b.unusable_policies.length, 1);
});

test('among two policies of one kind, the one expiring LAST is the one compared '
   + '-- a certificate holder is shown current cover, not the newest record', () => {
  const older = Object.assign({}, GL, { policy_id: 'OLD', expires_on: '2026-10-01' });
  const newer = Object.assign({}, GL, { policy_id: 'NEW', expires_on: '2027-06-01' });
  const r = m.coverageReadiness({ today: TODAY, policies: [newer, older],
    requirements: [{ kind: 'general_liability' }] });
  assert.strictEqual(r.lines[0].policy_id, 'NEW');
  const r2 = m.coverageReadiness({ today: TODAY, policies: [older, newer],
    requirements: [{ kind: 'general_liability' }] });
  assert.strictEqual(r2.lines[0].policy_id, 'NEW', 'the answer depended on input order');
});

test('it says in the payload that it gates nothing and parses no certificate', () => {
  const r = m.coverageReadiness({ today: TODAY, policies: [GL],
    requirements: [{ kind: 'general_liability' }] });
  assert.ok(/gates nothing and parses no certificate/.test(r.not_asserted));
});

test('NEGATIVE CONTROL: the engine is PURE -- no clock, no randomness, no I/O', () => {
  const src = require('fs').readFileSync(require.resolve('./mech-insurance.js'), 'utf8');
  const code = src.split('\n').filter(function (l) { return !/^\s*(\/\/|\*)/.test(l); }).join('\n');
  ['Date.now', 'Math.random', 'fetch(', 'require(\'fs\')', 'process.env']
    .forEach(function (n) {
      assert.ok(code.indexOf(n) === -1, 'the engine reaches for ' + n);
    });
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' MECH-INSURANCE ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
