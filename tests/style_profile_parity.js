// tests/style_profile_parity.js
//
// Run:  node tests/style_profile_parity.js
//
// The style profile is implemented TWICE on purpose: api/_lib/style-profile.js
// runs the merge server-side, and stonedesk.html carries analyse() and
// renderStyleDirectives() so the browser can observe locally and post counts
// instead of the user's text.
//
// A deliberate duplication is only defensible if divergence is LOUD. This
// extracts the client copy out of the real HTML, runs it against the real
// server module, and asserts they agree on the same corpus. Change one and not
// the other and this fails -- rather than the two silently personalising
// differently on each side, which is exactly the class of bug this codebase has
// been finding all week.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const ROOT = path.join(__dirname, '..');
const server = require(path.join(ROOT, 'api', '_lib', 'style-profile'));

// Pull the IIFE out of the page and evaluate it in a bare context.
const html = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8');
const start = html.indexOf('window.SAIRNStyle = (function () {');
assert.ok(start > 0, 'client SAIRNStyle block not found in stonedesk.html');
const endMarker = '})();';
const end = html.indexOf(endMarker, start);
assert.ok(end > start, 'client SAIRNStyle block is not terminated');
const src = html.slice(start, end + endMarker.length);

const window = {};
// eslint-disable-next-line no-eval
eval(src);
const client = window.SAIRNStyle;

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); pass++; console.log('  ok   ' + name); }
  catch (e) { fail++; console.log('  FAIL ' + name + '\n       ' + e.message); }
}

const CORPUS = [
  'price a 42 sqft granite kitchen',
  'THH for quartzite?',
  'give me the seam plan',
  'LF on the ogee edge',
  'remake cost breakdown',
  'show waste pct',
  'need this:\n- price\n- lead time\n- waste',
  'use **bold** and `code` please',
  'this is URGENT and IMPORTANT',
  'Hi there, I was wondering if you could possibly walk me through how you would approach ' +
  'the pricing on a large quartzite kitchen, because I am not entirely sure and would ' +
  'appreciate the detail. Thanks very much for your help with this.',
  '',
  '   ',
  'Could you please explain, perhaps in a bit more depth, what the waste percentage should ' +
  'be for a job with many cutouts and a directional vein that we have to match?'
];

console.log('--- analyse() parity, message by message ---');
CORPUS.forEach(function (m, i) {
  test('message ' + i + ' produces an identical observation', function () {
    assert.deepStrictEqual(client.analyse(m), server.analyse(m));
  });
});

console.log('--- constants must not drift ---');
test('MIN_SAMPLES matches', function () {
  assert.strictEqual(client.MIN_SAMPLES, server.MIN_SAMPLES);
});

console.log('--- renderStyleDirectives() parity on a real merged profile ---');
function build(msgs) {
  return msgs.reduce(function (p, m) { return server.mergeObservation(p, server.analyse(m)); }, server.emptyProfile());
}
const profile = build(CORPUS);
test('the merged profile renders identically on both sides', function () {
  assert.strictEqual(client.renderStyleDirectives(profile), server.renderStyleDirectives(profile));
});
test('with a manager override, identically too', function () {
  assert.strictEqual(
    client.renderStyleDirectives(profile, 'detailed'),
    server.renderStyleDirectives(profile, 'detailed'));
});
test('below the floor BOTH return empty', function () {
  const thin = build(CORPUS.slice(0, 2));
  assert.strictEqual(client.renderStyleDirectives(thin), '');
  assert.strictEqual(server.renderStyleDirectives(thin), '');
});
test('the rendered block is non-trivial, so parity is not parity-on-empty', function () {
  const d = server.renderStyleDirectives(profile);
  assert.ok(d.length > 120, 'expected a real directive block, got ' + d.length + ' chars');
  assert.ok(/HOW THIS PERSON WRITES/.test(d));
});

console.log('--- summarise() parity on the fields the client actually uses ---');
test('shared summary fields agree', function () {
  const c = client.summarise(profile), s = server.summarise(profile);
  ['samples', 'avg_words', 'question_ratio', 'imperative_ratio', 'bullet_ratio',
    'numbered_ratio', 'markdown_ratio', 'caps_ratio', 'hedge_per_msg',
    'courtesy_per_msg', 'abbrev_per_msg', 'dominant_length'].forEach(function (k) {
    assert.deepStrictEqual(c[k], s[k], k + ' differs: ' + c[k] + ' vs ' + s[k]);
  });
  assert.deepStrictEqual(c.top_terms, s.top_terms);
});

console.log('');
console.log(fail ? 'PARITY FAILURES: ' + fail + ' (passed ' + pass + ')'
  : 'ALL ' + pass + ' PARITY ASSERTIONS PASS — client and server agree');
process.exit(fail ? 1 : 0);
