// tests/sairnlaw_citation_rule.js
// REQUIREMENT: no SAIRNlaw AI call site may emit a case citation in
//   citable-reference format that the MODEL GENERATED, and the only scoped
//   exception is a citation read directly out of SAIRNlaw's own verified
//   citator -- which is retrieved data and not an AI call site at all
//
// Run:  node tests/sairnlaw_citation_rule.js
//
// ── WHY THIS SUITE EXISTS, AND WHAT IT CANNOT DO ──────────────────────────
// Michael converged the platform onto ONE citation rule on 2026-09-17. Until
// then sairnlaw carried three constants that disagreed, and one of them --
// MT_CRITIQUE_CITATION_RULE -- told the model *"If you cite a case, give its
// real reporter citation"*. That is an instruction to GENERATE, licensed by a
// post-hoc check: mtExtractCitations -> mtVerifyCitations -> citatorFetch.
// A check that grades a citation after the fact decides what BADGE it wears;
// it does not stop a fabricated one reaching a lawyer's screen, which is the
// harm LAW_CITATION_RULE names Mata v. Avianca for.
//
// THE HONEST LIMIT, STATED WHERE IT CANNOT BE MISSED: this reads WORDS IN A
// PROMPT. It cannot show the model obeys them -- that needs a model call and
// is deferred by the same recorded decision tools/ai_prompt_refusal_check.py
// carries. A green run here is "the rule is written everywhere it must be",
// never "no citation is ever fabricated".
//
// WHAT IT CAN DO, which is the half that regressed: tell a constant that
// FORBIDS generation from one that PERMITS it. ai_prompt_refusal_check.py
// counts whether a site references A rule constant and cannot read what the
// constant says -- so the divergence it correctly REPORTED as R2 would have
// stayed reportable forever without anything failing.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const HTML = path.join(__dirname, '..', 'sairnlaw.html');
const src = fs.readFileSync(HTML, 'utf8');

let pass = 0, fail = 0;
function t(name, fn) {
  try { fn(); pass++; console.log('  ok   ' + name); }
  catch (e) { fail++; console.log('  FAIL ' + name + '\n       ' + (e && e.message)); }
}
function section(s) { console.log('\n--- ' + s + ' ---'); }

// Read a `var NAME='...';` single-quoted JS string out of the page, with its
// \' escapes resolved. Driven from the real file so the suite cannot drift
// from the prompt that actually ships.
function constant(name) {
  const m = new RegExp("var\\s+" + name + "\\s*=\\s*'((?:[^'\\\\]|\\\\.)*)'\\s*;").exec(src);
  assert.ok(m, name + ' is not defined as a single-quoted var in sairnlaw.html');
  return m[1].replace(/\\'/g, "'");
}

// EVERY citation-rule constant on the page, DISCOVERED rather than listed. A
// hand-kept list is a second copy of the page and would silently miss the
// fourth constant somebody adds -- which is exactly how the divergence this
// suite exists for came to be.
const RULE_NAMES = Array.from(
  new Set((src.match(/var\s+([A-Z][A-Z0-9_]*CITATION_RULE)\s*=/g) || [])
    .map(function (s) { return /var\s+([A-Z0-9_]+)\s*=/.exec(s)[1]; })));

section('1. the population this suite speaks about');
t('at least three citation-rule constants are defined, and they are DISCOVERED',
  function () { assert.ok(RULE_NAMES.length >= 3, 'found: ' + RULE_NAMES.join(', ')); });
t('the three known ones are among them', function () {
  ['LAW_CITATION_RULE', 'MT_CITATION_RULE', 'MT_CRITIQUE_CITATION_RULE']
    .forEach(function (n) { assert.ok(RULE_NAMES.indexOf(n) !== -1, n + ' is missing'); });
});

section('2. every citation rule FORBIDS generating a citable-format string');
RULE_NAMES.forEach(function (name) {
  const rule = constant(name);
  t(name + ' contains an explicit prohibition on producing one', function () {
    assert.ok(/never output a specific case citation|do not generate a case citation/i.test(rule),
      name + ' does not forbid generating a citation: ' + rule.slice(0, 120));
  });
  // THE ARM THAT WOULD HAVE CAUGHT THE DIVERGENCE. The old critique rule said
  // "If you cite a case, give its real reporter citation and do not invent
  // one" -- a prohibition on INVENTING, which reads as a guard and is a
  // PERMISSION to emit. Matched on the instruction, not on the word "invent".
  t(name + ' does NOT instruct the model to supply a real reporter citation', function () {
    assert.ok(!/give its real reporter citation/i.test(rule),
      name + ' tells the model to produce a citation, which is generation with a caveat');
  });
  t(name + ' does not claim to be a permitted exception', function () {
    assert.ok(!/permitted to emit a citation/i.test(rule),
      name + ' still carries the withdrawn permission');
  });
});

section('3. the two mock-trial rules permit only a VERBATIM repeat');
['MT_CITATION_RULE', 'MT_CRITIQUE_CITATION_RULE'].forEach(function (name) {
  t(name + ' allows repeating a string the user supplied, and says verbatim',
    function () {
      const rule = constant(name);
      assert.ok(/verbatim/i.test(rule), name + ' has no verbatim carve-out');
      assert.ok(/narrativ|holding|principle/i.test(rule),
        name + ' does not offer the narrative alternative, so it only forbids');
    });
});

section('4. the scoped exception is the citator, and it is not an AI call site');
t('citatorFetch exists and is how a real citation is retrieved', function () {
  assert.ok(/function citatorFetch\s*\(/.test(src), 'citatorFetch is gone');
});
t('no ai_generate/system prompt is built from a citatorFetch result', function () {
  // A prompt assembled out of citator output would be the one shape that could
  // legitimately carry a citation -- and there is none today. Asserted so that
  // adding one is a deliberate act rather than a quiet widening.
  assert.ok(!/system\s*:\s*[^,]*citator/i.test(src),
    'a system prompt is being built from citator output -- re-read the scoped exception');
});

section('5. the post-hoc verification is a BACKSTOP and was not removed with the permission');
t('mtExtractCitations still exists', function () {
  assert.ok(/function mtExtractCitations\s*\(/.test(src), 'mtExtractCitations is gone');
});
t('mtVerifyCitations still exists and still reaches the real citator', function () {
  assert.ok(/function mtVerifyCitations\s*\(/.test(src), 'mtVerifyCitations is gone');
  assert.ok(/citatorFetch\(\s*'verify'/.test(src), "the 'verify' call is gone");
});
t('...and the critique path still runs it', function () {
  // ANCHORED ON THE CALL SITE, NOT THE CONSTANT. Searching forward from the
  // constant's DEFINITION finds `function mtVerifyCitations` three thousand
  // lines later and passes whether or not the critique path calls it -- an arm
  // satisfied by the function existing rather than by it being used. The
  // sabotage control caught that on the first run.
  const i = src.indexOf("'3. ' + MT_CRITIQUE_CITATION_RULE");
  assert.ok(i > 0, 'the critique HARD RULES block no longer names the constant');
  assert.ok(src.indexOf('mtVerifyCitations(', i) > 0,
    'nothing verifies the critique output any more -- the backstop went with the licence');
});

section('6. the work-product surfaces still carry the strict rule');
[
  'You explain trust-accounting reconciliation discrepancies',
  'You are a legal document drafting and review assistant',
  'You are reviewing a legal document for a law firm',
  'You are a legal practice operations assistant'
].forEach(function (marker) {
  t('the site beginning "' + marker.slice(0, 42) + '" carries LAW_CITATION_RULE', function () {
    const i = src.indexOf(marker);
    assert.ok(i > 0, 'call site not found: ' + marker);
    const seg = src.slice(i, i + 1800);
    assert.ok(seg.indexOf('LAW_CITATION_RULE') !== -1,
      'this work-product site no longer references LAW_CITATION_RULE');
  });
});

section('7. the user-facing promise matches the rule');
t('the AI Assistant panel still promises never to output an unverified citation',
  function () {
    assert.ok(/never presents an unverified case citation/i.test(src),
      'the panel subtitle no longer makes the promise the rule enforces');
  });

console.log('\nsairnlaw citation rule: ' + pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
