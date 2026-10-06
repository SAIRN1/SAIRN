// tests/lib/fn_span.test.js
//
// Run:  node tests/lib/fn_span.test.js
//
// Fixtures for tests/lib/fn_span.js, IN BOTH DIRECTIONS. Every arm here is a
// shape that produced a wrong span somewhere in this repo, plus the refusals,
// plus an ABLATION proving the regex-literal and string skipping are each
// load-bearing rather than decoration.
'use strict';

const assert = require('assert');
const { fnSpan, fnBody, balancedEnd } = require('./fn_span.js');

let pass = 0;
let fail = 0;
function t(name, fn) {
  try { fn(); pass++; console.log('  ok - ' + name); }
  catch (e) { fail++; console.log('  FAIL - ' + name + '\n        ' + e.message); }
}

// ── A. THE SHAPE THAT WAS THE DEFECT ───────────────────────────────────────
// A NESTED function declaration inside the body. The old spanOf() bounded a
// body at "the next `function` anywhere", so the span stopped here and the
// write after it was invisible. 2026-10-05, tests/sairnlegacy_write_failure_voice.js.
const NESTED = [
  'function confirmReserve(){',
  "  legWriteFailText('leg_merch_units', e);",
  '  function undoLocalReservation(){',
  '    rollback();',
  '  }',
  "  fetch(API, { body: JSON.stringify({ resource:'leg_merch_units' }) });",
  '}',
  'function somethingElse(){ return 1; }',
].join('\n');

t('A1. a nested function declaration does not end the span', () => {
  const b = fnBody(NESTED, 'function confirmReserve(){');
  assert.ok(b.includes("resource:'leg_merch_units'"),
    'the span stopped at the nested declaration -- this is the original defect');
  assert.ok(b.includes('undoLocalReservation'), 'the nested function is part of the body');
});

t('A2. and the span STOPS at its own close, not at the end of the file', () => {
  const b = fnBody(NESTED, 'function confirmReserve(){');
  assert.ok(!b.includes('somethingElse'),
    'the span ran past its own closing brace into the next function -- a span '
    + 'that swallows the rest of the file makes every later write look like '
    + "this function's");
});

// ── B. THE THREE PLACES A BRACE IS NOT A BRACE ─────────────────────────────
t('B1. a brace inside a string literal is not counted', () => {
  const src = 'function f(){\n  const s = "}";\n  const t = 2;\n}\nfunction g(){}';
  const b = fnBody(src, 'function f(){');
  assert.ok(b.includes('const t = 2'), 'the string brace closed the span early');
  assert.ok(!b.includes('function g'), 'the span overran');
});

t('B2. a brace inside a line comment is not counted', () => {
  const src = 'function f(){\n  // }\n  const t = 2;\n}\nfunction g(){}';
  const b = fnBody(src, 'function f(){');
  assert.ok(b.includes('const t = 2'), 'the comment brace closed the span early');
});

t('B3. a brace inside a block comment is not counted', () => {
  const src = 'function f(){\n  /* } */\n  const t = 2;\n}\nfunction g(){}';
  const b = fnBody(src, 'function f(){');
  assert.ok(b.includes('const t = 2'), 'the block-comment brace closed the span early');
});

t('B4. a brace inside a REGEX LITERAL is not counted', () => {
  const src = 'function f(){\n  if (/[}]/.test(x)) y();\n  const t = 2;\n}\nfunction g(){}';
  const b = fnBody(src, 'function f(){');
  assert.ok(b.includes('const t = 2'), 'the regex brace closed the span early');
  assert.ok(!b.includes('function g'), 'the span overran');
});

t('B5. a QUOTE inside a regex literal does not open a string', () => {
  // The failing shape strip_comments.js was fixed for on 2026-09-27: a regex
  // carrying a quote used to open a string literal that never closed, so every
  // brace after it was invisible and the span ran to the end of the input.
  const src = 'function f(){\n  const re = /["\']/;\n  const t = 2;\n}\nfunction g(){}';
  const b = fnBody(src, 'function f(){');
  assert.ok(b.includes('const t = 2'), 'the regex quote swallowed the body');
  assert.ok(!b.includes('function g'), 'the regex quote opened a string and the span ran away');
});

t('B6. DIVISION is not mistaken for a regex', () => {
  // `a / b` followed by a brace in a string. If the `/` were read as a regex
  // start, the regex would run to the newline and the string brace would be
  // counted -- closing the span early.
  const src = 'function f(){\n  const r = a / b;\n  const s = "}";\n  const t = 2;\n}';
  const b = fnBody(src, 'function f(){');
  assert.ok(b.includes('const t = 2'), 'division was read as a regex');
});

// ── C. ABLATION -- each skip is load-bearing, measured not asserted ────────
// Remove ONE layer from a COPY of balancedEnd and prove the arm above goes
// wrong. Convention 12 (ABLATION over chaos): one named layer off, on already-
// clean input, measured per arm.
function naiveEnd(src, open, skip) {
  let depth = 0; let i = open; let quote = null;
  while (i < src.length) {
    const c = src[i];
    if (skip !== 'strings' && quote) {
      if (c === '\\') { i += 2; continue; }
      if (c === quote) quote = null;
      i++; continue;
    }
    if (skip !== 'strings' && (c === '"' || c === "'" || c === '`')) { quote = c; i++; continue; }
    if (c === '{') depth++;
    else if (c === '}') { depth--; if (depth === 0) return i + 1; }
    i++;
  }
  return -1;
}

t('C1. ABLATION: with string-skipping off, B1 gets the WRONG span', () => {
  const src = 'function f(){\n  const s = "}";\n  const t = 2;\n}\nfunction g(){}';
  const start = src.indexOf('function f(){');
  const open = src.indexOf('{', start);
  const good = balancedEnd(src, open);
  const bad = naiveEnd(src, open, 'strings');
  assert.notStrictEqual(good, bad,
    'the string skip changed nothing on this fixture, so it is not proven here');
  assert.ok(!src.slice(start, bad).includes('const t = 2'),
    'the ablated walk still found the whole body -- the fixture does not bite');
});

t('C2. ABLATION: with regex-skipping off, B4 gets the WRONG span', () => {
  const src = 'function f(){\n  if (/[}]/.test(x)) y();\n  const t = 2;\n}';
  const start = src.indexOf('function f(){');
  const open = src.indexOf('{', start);
  const good = balancedEnd(src, open);
  const bad = naiveEnd(src, open, null);   // strings on, regex still absent
  assert.notStrictEqual(good, bad,
    'the regex skip changed nothing on this fixture, so it is not proven here');
});

// ── D. THE REFUSALS. Each previously produced a span instead of an error. ──
t('D1. an absent signature REFUSES rather than returning a span', () => {
  assert.throws(() => fnBody(NESTED, 'function neverExisted(){'),
    /signature not found/);
});

t('D2. a signature matching TWICE refuses and names the count', () => {
  const src = 'function dup(){ return 1; }\nfunction dup(){ return 2; }';
  assert.throws(() => fnBody(src, 'function dup(){'), /occurs 2 times/);
});

t('D3. unbalanced braces REFUSE rather than falling back to a bound', () => {
  const src = 'function f(){\n  if (x) {\n';
  assert.throws(() => fnBody(src, 'function f(){'), /never balance/);
});

t('D4. a declaration with no opening brace refuses', () => {
  const src = 'function f = 1;';
  assert.throws(() => fnBody(src, 'function f'), /no opening brace/);
});

// ── E. OFFSETS. A caller that reports a position needs them to mean something.
t('E1. start and end bracket the body exactly', () => {
  const sp = fnSpan(NESTED, 'function confirmReserve(){');
  assert.strictEqual(NESTED.slice(sp.start, sp.end), sp.body);
  assert.strictEqual(sp.body[sp.body.length - 1], '}');
  assert.ok(sp.body.startsWith('function confirmReserve(){'));
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
