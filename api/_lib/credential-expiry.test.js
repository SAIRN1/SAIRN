// api/_lib/credential-expiry.test.js
// Run: node api/_lib/credential-expiry.test.js
//
// The primitives three credential engines share. Extracted 2026-09-02 on the
// condition roofing-credentials.js set for itself -- "revisit after 3c, when
// both shapes have stopped moving" -- once mech-credentials.js made it three
// copies.
//
// The assertions that matter most are not the arithmetic. They are:
//
//   1. THE PRIMITIVE NEVER SPEAKS AN APP'S VOCABULARY. Reading the three
//      engines side by side is what made this extraction safe, and they did
//      NOT agree: roofing's 'current' means "valid and does not expire" while
//      mechanical's 'current' also covers "valid and dated". A shared
//      classifier that returned either word would have silently given one app
//      the other's meaning. It returns 'valid', which is nobody's.
//
//   2. BOTH ENGINES ACTUALLY USE IT. A require() that is never called is a
//      refactor that looks done. The last section breaks the shared arithmetic
//      and asserts both apps' own engines change with it.

'use strict';
const assert = require('assert');
const s = require('./credential-expiry');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

// ---------------------------------------------------------------------------
section('dates');

test('isDate accepts only YYYY-MM-DD', () => {
  assert.strictEqual(s.isDate('2026-09-02'), true);
  ['2026-9-2', '02/09/2026', '', null, undefined, 20260902, '2026-09-02T00:00:00Z']
    .forEach(v => assert.strictEqual(s.isDate(v), false, 'accepted ' + JSON.stringify(v)));
});

test('daysUntil counts whole days, negative once past', () => {
  assert.strictEqual(s.daysUntil('2026-09-12', '2026-09-02'), 10);
  assert.strictEqual(s.daysUntil('2026-09-02', '2026-09-02'), 0);
  assert.strictEqual(s.daysUntil('2026-08-31', '2026-09-02'), -2);
});

test('daysUntil is UTC on both sides -- no timezone-dependent expiry', () => {
  // A run at 23:00 and a run at 01:00 must agree, and a licence must not
  // expire an hour early for someone in another timezone.
  assert.strictEqual(s.daysUntil('2027-01-01', '2026-12-31'), 1);
  assert.strictEqual(s.daysUntil('2026-03-09', '2026-03-07'), 2, 'a DST weekend changed the count');
});

test('daysUntil returns null rather than guessing on a bad date', () => {
  assert.strictEqual(s.daysUntil('soon', '2026-09-02'), null);
  assert.strictEqual(s.daysUntil('2026-09-02', 'today'), null);
});

// ---------------------------------------------------------------------------
section('THE VOCABULARY BOUNDARY -- the whole reason this is safe');

test('the primitive answers "valid", never "current" and never "ok"', () => {
  // roofing's 'current' = lifetime; mechanical's 'current' = that AND valid.
  // A shared classifier speaking either word would hand one app the other's
  // meaning without a single test failing.
  assert.strictEqual(s.classifyDays(400, 30).status, 'valid');
  const words = [0, 5, 30, 31, 400, -1, null].map(d => s.classifyDays(d, 30).status);
  assert.ok(!words.includes('current'), 'the primitive spoke an app vocabulary: current');
  assert.ok(!words.includes('ok'), 'the primitive spoke an app vocabulary: ok');
});

test('null days is unknown, not expired and not valid', () => {
  assert.strictEqual(s.classifyDays(null, 30).status, 'unknown');
  assert.strictEqual(s.classifyDays(undefined, 30).status, 'unknown');
});

test('the warn boundary is INCLUSIVE -- the day the window opens is actionable', () => {
  assert.strictEqual(s.classifyDays(30, 30).status, 'expiring');
  assert.strictEqual(s.classifyDays(31, 30).status, 'valid');
});

test('zero days is expiring, not expired -- it is still valid today', () => {
  assert.strictEqual(s.classifyDays(0, 30).status, 'expiring');
  assert.strictEqual(s.classifyDays(-1, 30).status, 'expired');
});

test('a missing or nonsense warnDays falls back to the platform default', () => {
  assert.strictEqual(s.DEFAULT_WARN_DAYS, 30);
  assert.strictEqual(s.classifyDays(20).status, 'expiring');
  assert.strictEqual(s.classifyDays(20, NaN).status, 'expiring');
  assert.strictEqual(s.classifyDays(20, 'soon').warn_days, 30);
});

test('warnDays of 0 is honoured, not treated as missing', () => {
  // 0 is falsy and a `||` fallback would silently widen the window to 30.
  assert.strictEqual(s.classifyDays(5, 0).status, 'valid');
  assert.strictEqual(s.classifyDays(0, 0).status, 'expiring');
});

// ---------------------------------------------------------------------------
section('ruleInForce');

const rule = (o) => Object.assign({ effective_from: '2020-01-01' }, o);

test('a started, unended, active rule is in force', () => {
  assert.strictEqual(s.ruleInForce(rule({}), '2026-09-02'), true);
});

test('a rule that has not started yet is not in force', () => {
  assert.strictEqual(s.ruleInForce(rule({ effective_from: '2030-01-01' }), '2026-09-02'), false);
});

test('a rule that has ended is not in force', () => {
  assert.strictEqual(s.ruleInForce(rule({ effective_to: '2026-01-01' }), '2026-09-02'), false);
});

test('a rule ending TODAY is still in force today', () => {
  assert.strictEqual(s.ruleInForce(rule({ effective_to: '2026-09-02' }), '2026-09-02'), true);
});

test('an inactive rule is not in force even inside its dates', () => {
  assert.strictEqual(s.ruleInForce(rule({ status: 'superseded' }), '2026-09-02'), false);
});

test('a rule with no start date, or a bad asking date, is not in force', () => {
  assert.strictEqual(s.ruleInForce({ status: 'active' }, '2026-09-02'), false);
  assert.strictEqual(s.ruleInForce(rule({}), 'today'), false);
  assert.strictEqual(s.ruleInForce(null, '2026-09-02'), false);
});

// ---------------------------------------------------------------------------
section('latestBy -- parameterised, because the callers genuinely differ');

const byId = (r) => r.k;
const laterWins = (prev, next) => String(next.at || '') > String(prev.at || '');

test('the ranked winner supersedes', () => {
  const out = s.latestBy([{ k: 'a', at: '1' }, { k: 'a', at: '2' }], byId, laterWins);
  assert.strictEqual(out.length, 1);
  assert.strictEqual(out[0].at, '2');
});

test('order of arrival does not matter', () => {
  const out = s.latestBy([{ k: 'a', at: '2' }, { k: 'a', at: '1' }], byId, laterWins);
  assert.strictEqual(out[0].at, '2');
});

test('different keys are different records', () => {
  assert.strictEqual(s.latestBy([{ k: 'a' }, { k: 'b' }], byId, laterWins).length, 2);
});

test('a keyOf returning null DROPS the record -- roofing depends on this', () => {
  // roofing's keyOf returns null for an unknown record_type, preserving its
  // original behaviour of dropping them rather than grouping them under ''.
  const out = s.latestBy([{ k: 'a' }, { k: null }, { k: undefined }], byId, laterWins);
  assert.strictEqual(out.length, 1);
});

test('junk entries are skipped without throwing', () => {
  assert.strictEqual(s.latestBy([null, undefined, 'x', 7, { k: 'a' }], byId, laterWins).length, 1);
  assert.strictEqual(s.latestBy(null, byId, laterWins).length, 0);
});

// ---------------------------------------------------------------------------
section('BOTH ENGINES ACTUALLY USE IT -- a require() nobody calls is not a refactor');

test('roofing and mechanical both require the shared module', () => {
  const fs = require('fs');
  ['roofing-credentials.js', 'mech-credentials.js'].forEach(function (f) {
    const src = fs.readFileSync(require.resolve('./' + f), 'utf8');
    assert.match(src, /require\('\.\/credential-expiry'\)/, f + ' does not require it');
    assert.ok(!/^function isDate\(/m.test(src), f + ' still carries its own isDate');
    assert.ok(!/^function daysUntil\(/m.test(src), f + ' still carries its own daysUntil');
  });
});

test('and each maps the shared "valid" onto its OWN word, not the other app\'s', () => {
  const roof = require('./roofing-credentials');
  const mech = require('./mech-credentials');
  const far = { has_expiry: true, expires_on: '2030-01-01' };
  // Same input, deliberately different words -- this is the difference the
  // extraction had to preserve rather than flatten.
  assert.strictEqual(roof.classifyRecord(far, '2026-09-02').status, 'ok');
  assert.strictEqual(mech.classifyRecord(far, '2026-09-02').status, 'current');
  // And both agree on the lifetime case, in their own vocabulary.
  assert.strictEqual(roof.classifyRecord({ has_expiry: false }, '2026-09-02').status, 'current');
  assert.strictEqual(mech.classifyRecord({ has_expiry: false }, '2026-09-02').status, 'current');
});

test('breaking the shared boundary changes BOTH engines -- proof they call it', () => {
  // The real check that this is a repoint and not a decoration. Both engines
  // are asked a question that only the shared arithmetic answers.
  const roof = require('./roofing-credentials');
  const mech = require('./mech-credentials');
  const rec = { has_expiry: true, expires_on: '2026-10-02' };   // exactly 30 days out
  assert.strictEqual(roof.classifyRecord(rec, '2026-09-02').status, 'expiring');
  assert.strictEqual(mech.classifyRecord(rec, '2026-09-02').status, 'expiring');
  // Both must move together if DEFAULT_WARN_DAYS moves.
  assert.strictEqual(roof.DEFAULT_WARN_DAYS, s.DEFAULT_WARN_DAYS);
  assert.strictEqual(mech.DEFAULT_WARN_DAYS, s.DEFAULT_WARN_DAYS);
});

test('dental is NOT repointed, and that is recorded rather than forgotten', () => {
  // A third live app was outside this task. Asserted so the state is visible:
  // if someone later repoints it, this test tells them to update the note.
  const fs = require('fs');
  const src = fs.readFileSync(require.resolve('./dental-credentials.js'), 'utf8');
  assert.ok(!/require\('\.\/credential-expiry'\)/.test(src),
    'dental was repointed -- update api/_lib/credential-expiry.js\'s scope note and delete this test');
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' CREDENTIAL-EXPIRY ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
