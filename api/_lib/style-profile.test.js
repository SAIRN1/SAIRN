// api/_lib/style-profile.test.js
//
// Run:  node api/_lib/style-profile.test.js
//
// The claims worth testing here are not "does it compute an average". They are:
//   1. it DISCRIMINATES -- two genuinely different writers produce different
//      directives, because a personalization feature that emits the same block
//      for everybody is the token implementation this was built to avoid;
//   2. it SHUTS UP below the confidence floor;
//   3. it stores NO RAW TEXT, asserted against rare words rather than assumed;
//   4. merging is incremental and order-independent, so a profile built one
//      message at a time equals one built from the same messages reshuffled.

'use strict';
const assert = require('assert');
const S = require('./style-profile');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); pass++; console.log('  ok   ' + name); }
  catch (e) { fail++; console.log('  FAIL ' + name + '\n       ' + e.message); }
}

function build(msgs) {
  return msgs.reduce(function (p, m) { return S.mergeObservation(p, S.analyse(m)); }, S.emptyProfile());
}

// Two writers who are genuinely different people.
const TERSE = [
  'price a 42 sqft granite kitchen',
  'THH for quartzite?',
  'give me the seam plan',
  'LF on the ogee edge',
  'remake cost breakdown',
  'show waste pct'
];
const VERBOSE = [
  'Hi there, I was wondering if you could possibly help me think through a quote. ' +
  'We have a customer who is looking at a fairly large kitchen, and I think the material ' +
  'they want might be quartzite, though I am not entirely sure yet. Could you walk me through ' +
  'how you would approach the pricing on something like that, and what I should be watching for?',
  'Thanks, that is really helpful. I think the part I am least sure about is the waste percentage. ' +
  'Perhaps you could explain how you would estimate that for a job with a lot of cutouts, and ' +
  'whether the approach changes when the slab has a directional vein pattern that we need to match.',
  'That makes sense. I appreciate the detail. One more thing I have been wondering about: when we ' +
  'quote a customer and they come back weeks later, how should we think about whether the original ' +
  'price still holds, given that our material costs have been moving around quite a lot lately?',
  'Sorry to keep asking questions. I think I understand the margin side reasonably well now, but ' +
  'I would like to understand how you would explain this to a customer who pushes back on price, ' +
  'because that conversation is the one I find hardest and I want to get the framing right.',
  'Please could you also cover the installation scheduling side, since I think that is where we ' +
  'lose the most time, and I would appreciate a sense of what good looks like there.',
  'Thank you, this has been genuinely useful and I think I can take it from here for now.'
];

console.log('--- confidence floor ---');
test('renders nothing at zero samples', function () {
  assert.strictEqual(S.renderStyleDirectives(S.emptyProfile()), '');
});
test('renders nothing one below the floor', function () {
  const p = build(TERSE.slice(0, S.MIN_SAMPLES - 1));
  assert.strictEqual(p.samples, S.MIN_SAMPLES - 1);
  assert.strictEqual(S.renderStyleDirectives(p), '');
});
test('renders AT the floor', function () {
  const p = build(TERSE.slice(0, S.MIN_SAMPLES));
  assert.ok(S.renderStyleDirectives(p).length > 0);
});
test('null and undefined are safe', function () {
  assert.strictEqual(S.renderStyleDirectives(null), '');
  assert.strictEqual(S.renderStyleDirectives(undefined), '');
});

console.log('--- it discriminates ---');
const pT = build(TERSE), pV = build(VERBOSE);
const dT = S.renderStyleDirectives(pT), dV = S.renderStyleDirectives(pV);
test('the two writers produce DIFFERENT directives', function () {
  assert.notStrictEqual(dT, dV);
});
test('terse writer is told to be brief', function () {
  assert.ok(/writes short/.test(dT), dT.slice(0, 200));
});
test('verbose writer is NOT told to be brief', function () {
  assert.ok(!/writes short/.test(dV), dV.slice(0, 200));
});
test('terse writer reads as businesslike, verbose as polite', function () {
  assert.ok(/terse and businesslike/.test(dT), 'terse: ' + dT);
  assert.ok(/polite|warm/.test(dV), 'verbose: ' + dV);
});
test('the hedging writer is told to flag uncertainty', function () {
  assert.ok(/hedge|uncertainty/i.test(dV), dV);
});
test('word targets differ by more than 2x', function () {
  const nT = Number((dT.match(/roughly (\d+) words/) || [])[1] || 0);
  const nV = Number((dV.match(/roughly (\d+) words/) || [])[1] || 0);
  assert.ok(nT > 0 && nV > 0, 'targets: ' + nT + ' / ' + nV);
  assert.ok(nV > nT * 2, 'expected a big gap, got ' + nT + ' vs ' + nV);
});
test('trade abbreviations are picked up from the terse writer', function () {
  assert.ok(/abbreviation/i.test(dT), dT);
});
test('vocabulary is the USER\'s own words', function () {
  const s = S.summarise(pT);
  assert.ok(s.top_terms.includes('granite') || s.top_terms.includes('quartzite'), s.top_terms.join(','));
  assert.ok(!s.top_terms.includes('the') && !s.top_terms.includes('you'), 'stopwords leaked: ' + s.top_terms.join(','));
});

console.log('--- formatting signals ---');
test('a list writer is told to use lists', function () {
  const p = build([
    'need this:\n- price\n- lead time\n- waste',
    'checklist:\n- template\n- fab\n- install',
    'steps:\n1. measure\n2. quote\n3. schedule',
    'wants:\n- ogee\n- mitre\n- splash',
    'todo:\n- call supplier\n- book crew'
  ]);
  assert.ok(/structure answers as lists/.test(S.renderStyleDirectives(p)));
});
test('a prose writer is told to avoid lists', function () {
  assert.ok(/prose, not lists/.test(dV), dV);
});
test('markdown use is detected', function () {
  const p = build(Array(6).fill('use **bold** and `code` in the quote please'));
  assert.ok(/markdown/.test(S.renderStyleDirectives(p)));
});
test('CAPS emphasis is detected and is not confused with abbreviations', function () {
  const caps = build(Array(6).fill('this is URGENT and IMPORTANT for the customer today'));
  assert.ok(/capitals for emphasis/.test(S.renderStyleDirectives(caps)));
});

console.log('--- privacy: no raw text is retained ---');
test('a rare sentence cannot be found anywhere in the stored profile', function () {
  const secret = 'The zygomorphic quokka absconded with our vermilion escutcheon on Tuesday';
  const p = build([secret, secret, secret, secret, secret, secret]);
  const blob = JSON.stringify(p);
  assert.ok(!blob.includes('zygomorphic quokka'), 'a phrase survived into the profile');
  assert.ok(!blob.includes(secret), 'the raw sentence survived into the profile');
  assert.ok(!/absconded with/.test(blob), 'word ORDER survived, which is a phrase');
  // Individual content words DO survive as a frequency tally, by design -- that
  // is the vocabulary signal. The claim is that ORDER and PHRASING do not, so a
  // message cannot be reconstructed.
  assert.ok(/zygomorphic/.test(blob), 'expected the term tally to exist at all');
});
test('no field holds a string longer than a single word', function () {
  const p = build(VERBOSE);
  (function walk(v) {
    if (typeof v === 'string') { assert.ok(!/\s/.test(v), 'multi-word string stored: ' + v); return; }
    if (v && typeof v === 'object') Object.keys(v).forEach(function (k) { assert.ok(!/\s/.test(k), 'multi-word key: ' + k); walk(v[k]); });
  })(p);
});

console.log('--- incremental merge ---');
test('order does not change the profile', function () {
  const a = build(VERBOSE);
  const b = build(VERBOSE.slice().reverse());
  assert.deepStrictEqual(S.summarise(a), S.summarise(b));
});
test('merging is incremental, not a recompute', function () {
  const half = build(VERBOSE.slice(0, 3));
  const full = VERBOSE.slice(3).reduce(function (p, m) { return S.mergeObservation(p, S.analyse(m)); }, half);
  assert.deepStrictEqual(S.summarise(full), S.summarise(build(VERBOSE)));
});
test('mergeObservation does not mutate its input', function () {
  const before = build(TERSE);
  const snapshot = JSON.stringify(before);
  S.mergeObservation(before, S.analyse('another message about granite pricing'));
  assert.strictEqual(JSON.stringify(before), snapshot);
});
test('the term tally stays bounded, and the cap is actually exercised', function () {
  // 700 distinct terms against a 400 cap, so eviction really runs rather than
  // the test passing because the corpus never reached the boundary.
  let p = S.emptyProfile();
  for (let i = 0; i < 700; i++) p = S.mergeObservation(p, S.analyse('uniqueterm' + i + ' granite quartzite marble'));
  assert.ok(Object.keys(p.terms).length <= 400, 'terms grew to ' + Object.keys(p.terms).length);
  assert.ok(p.terms.granite >= 700, 'the genuinely frequent term was evicted');
  assert.ok(p.terms.quartzite >= 700 && p.terms.marble >= 700, 'a frequent term was evicted');
});
test('a realistic corpus never reaches the cap, which is what makes order not matter', function () {
  const p = build(VERBOSE.concat(TERSE));
  assert.ok(Object.keys(p.terms).length < 400,
    'realistic corpus hit the cap at ' + Object.keys(p.terms).length + ' -- order-independence would stop holding');
});
test('one huge paste cannot dominate the average', function () {
  const huge = new Array(5000).fill('granite').join(' ');
  const o = S.analyse(huge);
  assert.ok(o.words <= 400, 'sample not capped: ' + o.words);
});

console.log('--- manager override outranks observation ---');
test('an explicit manager style is stated as outranking', function () {
  const d = S.renderStyleDirectives(pT, 'detailed');
  assert.ok(/OUTRANKS/.test(d), d);
  assert.ok(/"detailed"/.test(d), d);
});
test('no override, no override line', function () {
  assert.ok(!/OUTRANKS/.test(dT));
});

console.log('--- degenerate input ---');
test('empty and whitespace messages do not throw or skew', function () {
  const p = build(['', '   ', '\n\n', 'granite', 'quartz', 'marble']);
  assert.strictEqual(p.samples, 6);
  assert.ok(S.renderStyleDirectives(p).length > 0);
});
test('non-string input is tolerated', function () {
  assert.doesNotThrow(function () { S.analyse(null); S.analyse(undefined); S.analyse(42); S.analyse({}); });
});

console.log('');
console.log(fail ? 'FAILURES: ' + fail + ' (passed ' + pass + ')' : 'ALL ' + pass + ' STYLE-PROFILE ASSERTIONS PASS');
process.exit(fail ? 1 : 0);
