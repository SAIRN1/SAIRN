// tests/stonedesk_hook_dormancy_disclosure.js
//
// Run:  node tests/stonedesk_hook_dormancy_disclosure.js
//
// NINE WAITERS IN stonedesk.html GAVE UP SILENTLY. THIS HOLDS THE DISCLOSURE.
//
// Eight blocks poll for `window.addMsg` every 150-200ms and stop after ten
// seconds; a ninth polls for `window.sendMessage`. Every one of them used to
// call `clearInterval` and nothing else -- so eight chat-enhancement hooks
// declined to install on every page load and said nothing, anywhere. The
// dormancy had to be found by opening a console on the deployed page
// (stonedesk.html ~:22782 records exactly that), which is the cost of the
// silence stated as a fact rather than as a worry.
//
// ── WHAT IS ACTUALLY WORTH ASSERTING HERE, AND WHY ────────────────────────
//
// (1) THE PREMISE, FIRST AND LOUDEST. The disclosure says `window.addMsg` has
//     no definition in this file. If somebody ever adds one, the eight hooks
//     start installing and every warning becomes a lie. Arm 1a fails the moment
//     a real definition appears -- it is the arm that makes this suite about the
//     file rather than about my reading of it on one afternoon.
//
// (2) THE CONDITIONAL. Each give-up timer fires whether or not its interval
//     already succeeded, so an UNCONDITIONAL report would announce a dormancy
//     for a hook that installed at t=3s. That is the same class of false
//     statement as the silence it replaces, in the other direction. Arm 2b
//     asserts every call site is guarded on its own global.
//
// (3) THE WHITE-ON-WHITE CONSTRAINT. installMarkdownHook renders through
//     renderMarkdownRich, which hardcodes light text for a dark surface while
//     the live bubble is white. A warning that says "hook did not install"
//     without saying that invites somebody to just install it. Arm 4b asserts
//     the message carries the constraint.
//
// (4) DEDUPE. One line per hook, not one per tick, and the shared CAUSE exactly
//     once. Arms 3a-3c drive the real helper for that.
//
// Set SD_HTML to point at a mutated copy for a negative control. Arm 0 fails if
// the helper cannot be located, so a rename cannot empty this suite.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const html = fs.readFileSync(process.env.SD_HTML
  || path.join(__dirname, '..', 'stonedesk.html'), 'utf8')
  .replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

// Code lines only. This file is dense with comments that quote the very
// identifiers being counted -- including `window.addMsg =` inside the
// correction at ~:21148 -- so a scan that reads comments finds the thing it was
// written to prove absent. PR 1.2, on the exact shape it keeps recurring in.
const codeLines = html.split('\n').filter(l => {
  const s = l.trim();
  return s && !s.startsWith('//') && !s.startsWith('*') && !s.startsWith('/*')
         && !s.startsWith('<!--');
});
const code = codeLines.join('\n');

const HOOKS = [
  ['installHook', 'addMsg'],
  ['installMemoryHook', 'addMsg'],
  ['installActionHook', 'addMsg'],
  ['installSimplifyHook', 'addMsg'],
  ['installHandoffHook', 'addMsg'],
  ['installMarkdownHook', 'addMsg'],
  ['installConfidenceHook', 'addMsg'],
  ['installLearningHook', 'addMsg'],
  ['installSlowResponseDetector', 'sendMessage'],
];

console.log('StoneDesk -- the dormant chat hooks say so instead of going quiet');

// ── 0. THE SUBJECT EXISTS ────────────────────────────────────────────────
let helperSrc = null;
section('0. the helper is located (a rename must not silently empty this suite)');
test('window.sdHookDormant is defined exactly once, at top level', () => {
  const at = code.indexOf('window.sdHookDormant = function (hookName, globalName) {');
  assert.ok(at > 0, 'the sdHookDormant definition is gone or was renamed');
  assert.strictEqual((code.match(/window\.sdHookDormant = function/g) || []).length, 1,
    'more than one definition of sdHookDormant -- two copies drift');
  // Take the function whole, from its own source, so arms 3-4 test the shipped
  // text rather than a transcription of it.
  const end = code.indexOf('\n};', at);
  assert.ok(end > at, 'could not find the end of the sdHookDormant function');
  helperSrc = code.slice(at, end + 3);
  assert.ok(helperSrc.length > 400,
    'the located helper is only ' + helperSrc.length + ' chars -- boundaries drifted');
});

// ── 1. THE PREMISE THE WHOLE DISCLOSURE RESTS ON ─────────────────────────
section('1. the premise: addMsg has no definition, so the chain has no head');
test('1a. every `window.addMsg =` is INSIDE an install*Hook that guards on it first', () => {
  // Not "addMsg is absent" -- it appears constantly. The claim is narrower and
  // is the one that matters: no assignment is reachable without a prior
  // definition, so nothing can be first.
  const assigns = (code.match(/window\.addMsg\s*=/g) || []).length;
  assert.ok(assigns >= 8, 'expected at least 8 wrapper assignments, found ' + assigns);
  // ── THE ANCHOR NEEDS A BODY, AND THAT IS NOT PEDANTRY ───────────────────
  // `/function\s+addMsg\s*\(/` is the obvious pattern and it went RED against a
  // correct file on the first run of this suite -- because sdHookDormant's own
  // warning text contains the string "a real `function addMsg(...)` survives
  // only in archive/...", which is a CODE line (it is inside a string literal),
  // so the comment filter above cannot remove it. My own disclosure tripped my
  // own premise check. Requiring an identifier parameter list AND an opening
  // brace distinguishes a declaration from prose about one: the message says
  // `(...)`, which is not an identifier and carries no `{`.
  const DECL = /function\s+addMsg\s*\(\s*(?:[A-Za-z_$][\w$]*\s*(?:,\s*[A-Za-z_$][\w$]*\s*)*)?\)\s*\{/g;
  assert.strictEqual((code.match(DECL) || []).length, 0,
    'a real `function addMsg(params) {` now exists in this file. The eight hooks will '
    + 'install, and every sdHookDormant warning is now FALSE. Remove the '
    + 'disclosure, or explain why it still holds.');
  // An unguarded top-level assignment would also give the chain a head.
  const bad = codeLines.filter(l => /^\s*window\.addMsg\s*=/.test(l)
                                    && !/^\s{2,}/.test(l));
  assert.deepStrictEqual(bad, [],
    'a top-level (unindented) window.addMsg assignment exists: ' + JSON.stringify(bad));
});
test('1b. sendMessage IS defined, which is why one waiter differs', () => {
  assert.ok(/^async function sendMessage\(\)/m.test(code),
    'the top-level `async function sendMessage()` is gone -- installSlowResponseDetector '
    + 'now genuinely waits, and its branch comment needs revisiting');
});

// ── 2. EVERY GIVE-UP REPORTS, AND EVERY REPORT IS GUARDED ────────────────
section('2. all nine give-up branches report, conditionally');
test('2a. each of the nine hooks has exactly one sdHookDormant call, naming itself', () => {
  HOOKS.forEach(([hook]) => {
    const n = (code.match(new RegExp("sdHookDormant\\('" + hook + "'", 'g')) || []).length;
    assert.strictEqual(n, 1, hook + ' has ' + n + ' disclosure call(s), expected 1');
  });
  const total = (code.match(/window\.sdHookDormant\(/g) || []).length;
  assert.strictEqual(total, HOOKS.length,
    'found ' + total + ' disclosure calls for ' + HOOKS.length + ' hooks -- a hook '
    + 'gained a second call or an unlisted hook gained one');
});
test('2b. THE CONDITIONAL: every call is gated on its OWN global still missing', () => {
  HOOKS.forEach(([hook, глоб]) => {
    const g = глоб;
    const at = code.indexOf("sdHookDormant('" + hook + "'");
    assert.ok(at > 0, 'no disclosure call for ' + hook);
    // The guard sits on the line above the call in every site.
    const before = code.slice(Math.max(0, at - 260), at);
    assert.ok(before.indexOf('typeof window.' + g + " !== 'function'") !== -1,
      hook + "'s disclosure is not guarded on `typeof window." + g + " !== 'function'`. "
      + 'Unguarded, this timer reports a dormancy for a hook that installed before '
      + 'the deadline.\n...' + before.slice(-200));
    assert.ok(before.indexOf("typeof window.sdHookDormant === 'function'") !== -1,
      hook + "'s call is not guarded on the helper existing -- if the first block "
      + 'throws, this becomes a TypeError instead of degrading to silence');
  });
});
test('2c. no bare give-up remains', () => {
  const bare = codeLines.filter(l =>
    /setTimeout\(function\s*\(\)\s*\{\s*clearInterval\([A-Za-z]+\);?\s*\}\s*,\s*10000\)/.test(l));
  assert.deepStrictEqual(bare, [],
    'a give-up still clears its interval and says nothing: ' + JSON.stringify(bare));
});

// ── 3. THE HELPER'S BEHAVIOUR, DRIVEN ───────────────────────────────────
function runHelper(calls) {
  const warns = [];
  const ctx = { window: {}, console: { warn: m => warns.push(String(m)) },
                Object, Array, String };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(helperSrc, ctx, { filename: 'sdHookDormant' });
  calls.forEach(([h, g]) => ctx.window.sdHookDormant(h, g));
  return { warns, ctx };
}

section('3. the helper: one line per hook, the cause exactly once');
test('3a. first call emits the CAUSE and the NAME -- two lines', () => {
  const { warns } = runHelper([['installHook', 'addMsg']]);
  assert.strictEqual(warns.length, 2, 'expected 2 warnings, got ' + warns.length
    + ':\n' + warns.join('\n---\n'));
  assert.ok(/window\.addMsg` has no definition|has no definition in/.test(warns[0]),
    'the first line does not explain the cause:\n' + warns[0].slice(0, 200));
  assert.ok(/installHook\(\)/.test(warns[1]), 'the second line does not name the hook');
});
test('3b. a second, different hook adds ONE line -- the cause is not repeated', () => {
  const { warns } = runHelper([['installHook', 'addMsg'], ['installMemoryHook', 'addMsg']]);
  assert.strictEqual(warns.length, 3, 'expected 3 warnings, got ' + warns.length);
  assert.ok(/installMemoryHook/.test(warns[2]));
  assert.strictEqual(warns.filter(w => /has no definition in/.test(w)).length, 1,
    'the shared cause was printed more than once');
});
test('3c. the SAME hook twice adds nothing -- one line per hook, not per tick', () => {
  const { warns, ctx } = runHelper([
    ['installHook', 'addMsg'], ['installHook', 'addMsg'], ['installHook', 'addMsg']]);
  assert.strictEqual(warns.length, 2, 'expected 2 warnings, got ' + warns.length);
  // Array.from, not deepStrictEqual on the object: the helper builds its list
  // with a `[]` literal INSIDE the vm, so it is a different realm's Array and
  // deepStrictEqual fails on the prototype while reporting "same structure".
  assert.deepStrictEqual(Array.from(ctx.window.__sdDormantHooks), ['installHook']);
});
test('3d. all nine reported gives 1 cause + 9 names', () => {
  const { warns } = runHelper(HOOKS);
  assert.strictEqual(warns.length, 10, 'expected 10 warnings, got ' + warns.length);
  HOOKS.forEach(([h]) => assert.ok(warns.some(w => w.indexOf(h + '()') !== -1),
    h + ' is not named in the output'));
});

// ── 4. THE MESSAGE SAYS THE THINGS A READER NEEDS ───────────────────────
section('4. the message is honest about what it is and what not to do');
test('4a. it says this is a KNOWN state, not a new fault', () => {
  const { warns } = runHelper([['installHook', 'addMsg']]);
  assert.ok(/KNOWN state/i.test(warns[0]),
    'the cause line does not say this is a known state, so it reads as an incident');
  assert.ok(/not running|are simply not/i.test(warns[0]),
    'it does not say plainly that the features are not running');
});
test('4b. THE WHITE-ON-WHITE CONSTRAINT is in the message, with both colours', () => {
  const { warns } = runHelper([['installMarkdownHook', 'addMsg']]);
  const all = warns.join('\n');
  assert.ok(/installMarkdownHook/.test(all) && /renderMarkdownRich/.test(all),
    'the message does not name the hook and renderer with the visual defect');
  assert.ok(/#F0F0FF/.test(all) && /#FFFFFF/.test(all),
    'the message does not carry BOTH colours -- the light text and the white bubble '
    + 'are the whole point, and one without the other is not actionable');
  assert.ok(/near-white/i.test(all) || /white on white|on white/i.test(all),
    'the message does not state the consequence in words');
});
test('4c. it points at the retired chat as the missing head, not at nothing', () => {
  const { warns } = runHelper([['installHook', 'addMsg']]);
  assert.ok(/archive\/branch-lucid-ptolemy/.test(warns[0]),
    'the cause line does not say where a real addMsg does still exist, which is what '
    + 'stops the next reader re-deriving it');
});

console.log('\n' + (fail ? 'FAIL' : 'ALL') + ' -- ' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
