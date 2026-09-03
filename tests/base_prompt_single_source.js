// tests/base_prompt_single_source.js
//
// Run:  node tests/base_prompt_single_source.js
//
// THE DEFECT THIS HOLDS CLOSED.
//
// stonedesk.html carried TWO full copies of the ~2KB StoneDesk base system
// prompt, and they had already diverged. Proven by comparing the literals
// rather than by reading them: the copy at the old `const SYSTEM` was a
// BYTE-IDENTICAL PREFIX of the one inside buildSDSystemPrompt() -- 1,793
// characters against 2,086 -- missing exactly the 293-character SAIRNBIZ
// ROUTING paragraph. One copy was corrected and the other was not, which is
// the only way two copies of anything ever end.
//
// IT MATTERED BECAUSE THE STALE COPY WAS LIVE. getAIDrawingAdvice() -- the
// "AI - Review This Job" button on the Drawing Tool, wired to a real control
// -- posted it as `system` on every click. A shop asking that button about
// payroll or bookkeeping got an assistant that had never been told those are
// handled by SAIRNbiz, while the same question in the chat panel got one that
// had. Same product, same shop, two different answers, depending which button
// they pressed.
//
// This file does not check that the prompt is GOOD. It checks that there is
// exactly ONE of it, which is the property that failed.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const ROOT = path.join(__dirname, '..');
const FILE = path.join(ROOT, 'stonedesk.html');
const html = fs.readFileSync(FILE, 'utf8');

let n = 0;
function ok(cond, label) { assert.ok(cond, label); n++; }
function eq(a, b, label) { assert.deepStrictEqual(a, b, label); n++; }

// The opening clause is distinctive enough to find every copy and short enough
// that a reformat of the later text cannot hide one.
const OPENER = 'You are StoneDesk™ AI, the world’s most advanced AI platform';
const opener = html.includes(OPENER)
  ? OPENER
  : 'You are StoneDesk™ AI, the world\'s most advanced AI platform';

// ── 1. Exactly one copy ─────────────────────────────────────────────────────
const copies = html.split(opener).length - 1;
eq(copies, 1,
  'the base system prompt appears ' + copies + ' times in stonedesk.html -- ' +
  'two copies is how the SAIRNBIZ ROUTING paragraph came to exist in one and ' +
  'not the other');

// ── 2. It is a named constant, exported, and read by name ──────────────────
ok(/const SD_BASE_PROMPT = "You are StoneDesk/.test(html),
   'the single copy is the named SD_BASE_PROMPT constant');
ok(/window\.SD_BASE_PROMPT = SD_BASE_PROMPT;/.test(html),
   'and it is published on window so a later block cannot justify its own copy');
ok(/const base = SD_BASE_PROMPT;/.test(html),
   'buildSDSystemPrompt() reads the shared constant instead of holding a literal');
ok(/const SYSTEM = SD_BASE_PROMPT;/.test(html),
   'the legacy SYSTEM name is an alias, so it can no longer hold a DIFFERENT prompt');

// ── 3. The paragraph whose absence was the live bug ────────────────────────
const a = html.indexOf('const SD_BASE_PROMPT = "');
const q = html.indexOf('"', a);
const e = html.indexOf('";', q) + 1;
const literal = JSON.parse(html.slice(q, e));
// Pinned to a length rather than a hash so a real edit shows up as a number a
// reader can reason about. It moved 2086 -> 2194 on 2026-09-03 when the four
// hardcoded THH benchmark figures came OUT (no shop could reach them and no
// calculator agreed with them) and a pointer to the shop's own configured
// rates went in. Update this deliberately, with the reason, never to make a
// red test green.
eq(literal.length, 2168, 'the surviving copy is the current one');
ok(!/Michael L\. Dibert/.test(literal),
   'the personal name is OUT of the prompt -- the model states the ENTITY that built it, not a natural person');
ok(/built by SAIRN Tech LLC/.test(literal),
   'and names the real legal entity: SAIRN Tech LLC, not "SAIRN Technologies LLC"');
ok(!/Granite 4hr per 50sqft/.test(literal),
   'the hardcoded THH benchmark figures are OUT of the prompt -- they belonged in a setting, not a string');
ok(/SHOP THH BENCHMARKS/.test(literal),
   'and the prompt points at the rates the shop actually configured');
ok(/say you do not have the rates for this shop rather than quoting a general figure/.test(literal),
   'with an instruction to refuse rather than invent a benchmark when they are absent');
ok(/SAIRNBIZ ROUTING:/.test(literal),
   'and it carries the SAIRNbiz routing paragraph the stale copy lacked');
ok(/not QuickBooks\/Gusto\/ADP/.test(literal),
   'including the line that keeps an accounting question out of QuickBooks');

// ── 4. Declared before every consumer ──────────────────────────────────────
// SD_BASE_PROMPT is a top-level `const`, so it lives in the shared global
// lexical scope rather than on window at declaration time. A consumer in an
// EARLIER script block would hit the temporal dead zone and throw, and it
// would throw at click time in one feature rather than at load, which is the
// slowest possible way to find out.
const decl = html.indexOf('const SD_BASE_PROMPT = "');
ok(decl > 0, 'the declaration exists');
['const base = SD_BASE_PROMPT;', 'const SYSTEM = SD_BASE_PROMPT;'].forEach(function (c) {
  ok(html.indexOf(c) > decl, c + ' comes after the declaration, not before it');
});

// ── 5. The live consumer is still wired to a real control ──────────────────
// If this ever stops being true the finding above stops being a live bug and
// becomes a dead-code cleanup, which is a different conversation.
ok(/onclick="getAIDrawingAdvice\(\)"/.test(html),
   'getAIDrawingAdvice() is still reachable from a real button');
ok(/async function getAIDrawingAdvice\(\)/.test(html),
   'and still defined');
const adviceStart = html.indexOf('async function getAIDrawingAdvice()');
const adviceEnd = html.indexOf('\n}', adviceStart);
const advice = html.slice(adviceStart, adviceEnd);
ok(/system:\s*SYSTEM/.test(advice),
   'it posts the shared prompt -- via the alias, which now resolves to the one copy');
ok(!/system:\s*"You are StoneDesk/.test(advice),
   'and does not carry an inline literal of its own');

// ── 6. Negative control ────────────────────────────────────────────────────
// A test that counts to one is worthless if it would also pass at two.
(function negativeControl() {
  const reintroduced = html.replace(
    'const SYSTEM = SD_BASE_PROMPT;',
    'const SYSTEM = "' + opener + ' ...";'
  );
  const c = reintroduced.split(opener).length - 1;
  ok(c === 2,
     'NEGATIVE CONTROL: putting a second copy back is seen as two, so the count above is real');
})();

console.log('base_prompt_single_source: ' + n + '/' + n + ' assertions passed');
