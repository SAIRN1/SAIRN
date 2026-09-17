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

section('8. EVERY AI call site carries a citation rule -- the sweep, not a list');
// DISCOVERED, NOT ENUMERATED. A hand-written list of call sites is a second
// copy of the page and would miss the one somebody adds next -- which is how
// the critique step's divergence survived. Both call shapes this app uses are
// matched: lawAuth('ai_generate', ...) and fetch(PROXY, ...).
const CALL_LINES = src.split('\n').map(function (l, i) { return [i + 1, l]; })
  .filter(function (p) {
    return /lawAuth\(\s*'ai_generate'/.test(p[1]) || /fetch\(\s*PROXY\b/.test(p[1]);
  });
t('the sweep finds every AI call site in the file (at least 7)', function () {
  assert.ok(CALL_LINES.length >= 7, 'found ' + CALL_LINES.length + ' AI call sites');
});
// ── COMMENTS ARE STRIPPED BEFORE THE SEARCH, AND THAT IS NOT TIDINESS ────
// The first version of the arm below searched the raw segment, and the
// sabotage control came back SILENT: a new AI call site planted with NO rule
// still "passed", because the long comment block above lawCiteGuard MENTIONS
// LAW_CITATION_RULE and sat inside the 70-line window. A marker search that
// cannot tell code from prose about code is PR 1.2 exactly -- the `esign`
// matching 47 occurrences of `design` case -- and this suite committed it
// while testing a rule about prompts.
//
// String-aware, because `'https://sairn.vercel.app/api/claude'` contains `//`
// and a naive stripper would eat the rest of that line.
function stripJsComments(code) {
  let out = '', i = 0, q = null;
  while (i < code.length) {
    const c = code[i], n = code[i + 1];
    if (q) {
      if (c === '\\') { out += '  '; i += 2; continue; }
      if (c === q) q = null;
      out += c; i++; continue;
    }
    if (c === '"' || c === "'" || c === '`') { q = c; out += c; i++; continue; }
    if (c === '/' && n === '/') { while (i < code.length && code[i] !== '\n') i++; continue; }
    if (c === '/' && n === '*') {
      i += 2;
      while (i < code.length && !(code[i] === '*' && code[i + 1] === '/')) {
        if (code[i] === '\n') out += '\n';
        i++;
      }
      i += 2; continue;
    }
    out += c; i++;
  }
  return out;
}

t('CONTROL: the comment stripper keeps code and drops prose about code', function () {
  assert.ok(stripJsComments("var a='x';// LAW_CITATION_RULE\n").indexOf('LAW_CITATION_RULE') === -1,
    'a line comment survived stripping');
  assert.ok(stripJsComments("/* LAW_CITATION_RULE */ var b=1;").indexOf('LAW_CITATION_RULE') === -1,
    'a block comment survived stripping');
  assert.ok(stripJsComments("var u='https://x/y';var s=LAW_CITATION_RULE;")
    .indexOf('LAW_CITATION_RULE') !== -1,
    'the stripper ate real code after a // inside a string literal');
});

// THE WINDOW IS THE CALL EXPRESSION, NOT A LINE COUNT. A fixed "+5 lines
// forward" hid a real miss: the trust-reconciliation call spans twenty lines
// and puts `system:'...'+LAW_CITATION_RULE` well past the opening paren, so
// with comments stripped the arm failed against a site that is correctly
// guarded. Balanced parens from the call site cover the whole argument object
// however long it is, and 70 lines back cover a prompt assembled into a
// variable beforehand (`var sys = ...`).
function callExpression(line0) {
  const lines = src.split('\n');
  const start = lines.slice(0, line0 - 1).join('\n').length + 1;
  let i = src.indexOf('(', start), depth = 0;
  if (i < 0) return '';
  for (let j = i; j < src.length && j < i + 20000; j++) {
    if (src[j] === '(') depth++;
    else if (src[j] === ')') { depth--; if (!depth) return src.slice(start, j + 1); }
  }
  return src.slice(start, start + 4000);
}

CALL_LINES.forEach(function (p) {
  t('the AI call at line ' + p[0] + ' is under a citation rule', function () {
    const before = src.split('\n').slice(Math.max(0, p[0] - 71), p[0] - 1).join('\n');
    const seg = stripJsComments(before + '\n' + callExpression(p[0]));
    assert.ok(RULE_NAMES.some(function (n) { return seg.indexOf(n) !== -1; }),
      'no citation-rule constant reaches the call at line ' + p[0]);
  });
});

section('9. the work-product surfaces have a CHECK, not only a rule');
// THE SWEEP'S REAL FINDING. Until 2026-09-17 the checking was inverted: the two
// mock-trial surfaces -- practice and training -- extracted and verified every
// citation, while the assistant, the AI draft and the document review did not.
// The draft one is the sharpest because saveDraft() PERSISTS that text as a
// matter document, so a fabricated citation reaches the client's own file.
t('lawCiteGuard exists and is ONE implementation, not a fourth copy', function () {
  assert.ok(/function lawCiteGuard\s*\(/.test(src), 'lawCiteGuard is gone');
  assert.strictEqual((src.match(/function lawCiteGuard\s*\(/g) || []).length, 1,
    'more than one definition of the guard');
});
t('it degrades SILENT rather than claiming a check it did not run', function () {
  const i = src.indexOf('function lawCiteGuard');
  const body = src.slice(i, i + 3000);
  assert.ok(/typeof mtExtractCitations !== 'function'/.test(body),
    'the guard does not check the extractor is loaded before using it');
  // ── TWO SEPARATE COULD-NOT-CHECK STATES, ASSERTED SEPARATELY ───────────
  // This was one loose alternation -- /could not be resolved either way|could
  // not be checked/ -- and the sabotage control came back SILENT: deleting the
  // first phrase left the SECOND one, which lives in the per-citation state
  // map for a verifier that answered `unavailable`. Two different facts about
  // two different failures, and an `|` between them meant either could stand
  // in for both.
  assert.ok(body.indexOf('citation checking is unavailable here') !== -1,
    'the VERIFIER-MISSING branch has no could-not-check wording, so it would read as clean');
  assert.ok(body.indexOf("'could not be checked'") !== -1,
    'the per-citation `unavailable` state has no wording of its own');
});
[
  ["$('draftresult').value=text+'\\n\\n--- '+grounded.note;", 'the AI draft'],
  ["$('draftresult').value='--- REVIEW OF: '", 'the document review'],
  ['thinking.textContent=rep;', 'the assistant first reply'],
  ['thinking.textContent=rep2;', 'the assistant tool-use reply']
].forEach(function (pair) {
  t(pair[1] + ' runs lawCiteGuard on the model text', function () {
    const i = src.indexOf(pair[0]);
    assert.ok(i > 0, 'render site not found: ' + pair[0]);
    const seg = src.slice(i, i + 700);
    assert.ok(seg.indexOf('lawCiteGuard(') !== -1,
      pair[1] + ' renders model prose with no citation guard');
  });
});
t('and the draft guard fires BEFORE the text can be saved as a matter document',
  function () {
    const g = src.indexOf("lawCiteGuard(text,$('draftresult').parentNode,'draft')");
    const s = src.indexOf("content_text:text,ocr_text:''");
    assert.ok(g > 0 && s > 0, 'one of the two sites moved');
    assert.ok(g < s, 'the guard now runs after the save path, which is no guard at all');
  });

section('7. the user-facing promise matches the rule');
t('the AI Assistant panel still promises never to output an unverified citation',
  function () {
    assert.ok(/never presents an unverified case citation/i.test(src),
      'the panel subtitle no longer makes the promise the rule enforces');
  });

console.log('\nsairnlaw citation rule: ' + pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
