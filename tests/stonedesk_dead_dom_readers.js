// tests/stonedesk_dead_dom_readers.js
//
// Run:  node tests/stonedesk_dead_dom_readers.js
//
// GUARDIAN CHECK 0d, MECHANISED FOR THE ONE CASE THAT ACTUALLY BITES.
//
// stonedesk.html contains 27 functions that dereference a property straight off
// `getElementById` for an element that does not exist -- `.value`, `.classList`,
// `.style` on null. Each is a TypeError the instant its function runs, and the
// click that triggered it does nothing further.
//
// EVERY ONE OF THEM IS CURRENTLY UNREACHABLE. Measured, not assumed: zero inline
// handlers, zero string references, and the only textual mentions of six of them
// (commsAIDraft, remakeSave, npsLog, npsSave, setMode, resetEmailTriage) are
// inside comments, or inside markup built by another function that is itself
// dead. So they crash nobody today.
//
// 0d ALLOWS TWO ENDINGS AND FORBIDS A THIRD. Delete them, or quarantine them
// BY NAME -- never leave them sitting unmentioned, "because the moment someone
// adds a nav entry pointing to it later, whatever's inside goes live with zero
// warning." This file is the quarantine, made mechanical: the hazard is not
// that the code exists, it is that the code becomes REACHABLE. So the register
// below is asserted rather than written in a doc nobody re-reads. Wire any one
// of these up and this test names it and names the crash it would cause.
//
// WHY NOT JUST DELETE ALL 27. That is a legitimate reading of 0d(a) and it may
// still be the right end state. It is 27 functions spread across a 2 MB file in
// one pass, and this row's own history warns that "deleting the wrong half
// would take a live panel down". The bounded version -- one well-understood
// orphan module, measured, tombstoned, with the missing-DOM delta as proof --
// was done on 2026-09-09 for the damage-claim twin. This pins the remaining 27
// so they cannot go live while that decision is taken.
//
// A NOTE ON HOW THE LIST WAS BUILT, because the first attempt was wrong. A
// hand-rolled scan for `getElementById('x').prop` where `x` has no `id="x"` in
// the source reported 29 functions and 76 reads -- it included
// `sairn-compare-modal` and `sairn-cam-modal`, which are created at run time by
// `modal.id = '...'` and `document.body.appendChild(modal)`. They are not
// missing; a source grep simply cannot see them. tools/missing_dom_target_check.py
// already resolves that class, so THIS FILE DERIVES ITS MISSING-ID SET FROM THE
// TOOL rather than re-deriving it, and the two entries vanished.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const { execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const FILE = path.join(ROOT, 'stonedesk.html');
const src = fs.readFileSync(FILE, 'utf8').replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   - ' + name); pass++; }
  catch (e) { console.log('  FAIL - ' + name + '\n         ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

// The ids that genuinely do not exist, straight from the tool that already
// knows about runtime-created elements. If the tool cannot be run, this file
// SKIPS rather than passing -- a checker that silently degrades to green is the
// failure this whole suite keeps finding.
function missingIds() {
  let out;
  try {
    out = execFileSync(process.env.PYTHON || 'python',
      [path.join(ROOT, 'tools', 'missing_dom_target_check.py'), FILE],
      { encoding: 'utf8', maxBuffer: 32 * 1024 * 1024 });
  } catch (e) {
    out = (e && e.stdout) || '';
  }
  const ids = (out.match(/^MISSING: id="[^"]+"/gm) || [])
    .map((l) => l.replace(/^MISSING: id="/, '').replace(/"$/, ''));
  return { ids: new Set(ids), ran: /MISSING_TARGETS:\d+/.test(out) };
}

const MISSING = missingIds();

function bodyOf(at) {
  const open = src.indexOf('{', at);
  let d = 0;
  for (let i = open; i < src.length; i++) {
    if (src[i] === '{') d++;
    else if (src[i] === '}') { d--; if (d === 0) return { body: src.slice(at, i + 1), start: at, end: i + 1 }; }
  }
  return null;
}

// Every unguarded read of a missing id, grouped by the function it sits in.
function unguardedReaders() {
  const byFn = {};
  const re = /(?:document\.getElementById|\$)\(\s*'([A-Za-z0-9_-]+)'\s*\)\s*\.\s*([A-Za-z_]\w*)/g;
  let m;
  while ((m = re.exec(src))) {
    if (!MISSING.ids.has(m[1])) continue;
    const at = src.lastIndexOf('function ', m.index);
    if (at < 0) continue;
    const nameEnd = src.indexOf('(', at);
    const name = src.slice(at + 'function '.length, nameEnd).trim();
    if (!/^[A-Za-z_$][\w$]*$/.test(name)) continue;
    (byFn[name] = byFn[name] || []).push({ id: m[1], prop: m[2] });
  }
  return byFn;
}

// Callers OUTSIDE the function's own body: inline handlers, string references
// (dispatch by name), and plain calls.
function callersOf(name) {
  const at = src.indexOf('function ' + name + '(');
  if (at < 0) return null;
  const b = bodyOf(at);
  const inline = (src.match(new RegExp('on\\w+\\s*=\\s*["\'][^"\']*\\b' + name + '\\s*\\(', 'g')) || []).length;
  const strRef = (src.match(new RegExp('[\'"]' + name + '[\'"]', 'g')) || []).length;
  const calls = [];
  const cre = new RegExp('\\b' + name + '\\s*\\(', 'g');
  let m;
  while ((m = cre.exec(src))) {
    if (b && m.index >= b.start && m.index < b.end) continue;
    if (src.slice(Math.max(0, m.index - 10), m.index).trim().endsWith('function')) continue;
    // A mention inside a `//` comment is not a caller. Six of these are named
    // only in comments that explain why they are dead, and counting those made
    // them look reachable on the first pass.
    const lineStart = src.lastIndexOf('\n', m.index) + 1;
    if (src.slice(lineStart, m.index).indexOf('//') !== -1) continue;
    calls.push(m.index);
  }
  return { inline: inline, strRef: strRef, calls: calls.length };
}

const READERS = unguardedReaders();
const NAMES = Object.keys(READERS).sort();

// ═══════════════════════════════════════════════════════════════════════════
section('1. the scan ran, and it still sees what it is for');

test('missing_dom_target_check produced a real answer', () => {
  assert.ok(MISSING.ran,
    'tools/missing_dom_target_check.py did not run or produced no MISSING_TARGETS line -- '
    + 'this file SKIPS rather than passing, because a checker degrading to green is '
    + 'exactly what it exists to prevent');
  assert.ok(MISSING.ids.size >= 100,
    'only ' + MISSING.ids.size + ' missing ids reported; the known baseline is 137. '
    + 'A large drop is either real progress or a blind scan -- read it before trusting it');
});

test('the unguarded-reader set is still populated', () => {
  assert.ok(NAMES.length >= 20,
    'only ' + NAMES.length + ' functions found with unguarded reads of a missing id. '
    + 'Either they were deleted (good -- update this floor) or the scan went blind');
});

// ═══════════════════════════════════════════════════════════════════════════
section('2. THE QUARANTINE: every one of them is still unreachable');

// THREE OF THE 27 HAVE A TEXTUAL CALLER AND ARE STILL UNREACHABLE, and each is
// named with its reason rather than waved through by a looser counter -- the
// standard this repo applies to a push-gate override. The reason is RE-CHECKED
// mechanically below, so an entry cannot outlive the fact it rests on.
const EXPLAINED = {
  // Its only mention is prose. The line is the tail of a wrapped `//` comment,
  // so a same-line `//` test does not see it.
  commsAIDraft: (s) => /could have fed it, commsAIDraft\(\), has zero callers/.test(s),
  // Two `typeof … === 'undefined'` shims install stubs that call it. Both are
  // unconditionally overwritten later by the REAL selectCamPrompt/selectDocPrompt
  // inside IIFEs, and neither real handler calls setMode -- established in the
  // open-work row on 2026-09-08 and re-asserted here.
  setMode: (s) => /if\(typeof selectCamPrompt === 'undefined'\)/.test(s)
    && /if\(typeof selectDocPrompt === 'undefined'\)/.test(s)
    && !/window\.selectCamPrompt\s*=\s*function[^]{0,400}setMode\(/.test(
      s.slice(s.indexOf('window.selectCamPrompt = function', s.indexOf('scam-chip')))),
  // Its only wiring is an inline onclick inside a template string that
  // runEmailTriage builds -- and runEmailTriage is itself in this dead set, so
  // the button is never rendered.
  resetEmailTriage: (s) => /var resetBtn='[^']*onclick="resetEmailTriage\(\)"/.test(s),
};

test('every explained-away caller still has the reason it was explained by', () => {
  Object.keys(EXPLAINED).forEach((name) => {
    assert.ok(NAMES.indexOf(name) !== -1,
      name + ' is no longer an unguarded reader -- remove its entry from EXPLAINED '
      + 'rather than leaving an exemption for a function that no longer needs one');
    assert.ok(EXPLAINED[name](src),
      name + ': the reason it was quarantined rather than treated as reachable no '
      + 'longer holds. Re-read its call sites before trusting the exemption.');
  });
  // resetEmailTriage's exemption depends on runEmailTriage being dead too.
  const rt = callersOf('runEmailTriage');
  assert.ok(rt && rt.inline === 0 && rt.strRef === 0 && rt.calls === 0,
    'runEmailTriage has acquired a caller, so the button it renders -- '
    + 'onclick="resetEmailTriage()" -- is now reachable and will throw on #email-paste-input');
});

test('no unguarded reader has acquired a caller', () => {
  const live = [];
  NAMES.forEach((name) => {
    const c = callersOf(name);
    if (!c) return;
    if (Object.prototype.hasOwnProperty.call(EXPLAINED, name)) return;
    if (c.inline > 0 || c.strRef > 0 || c.calls > 0) {
      const reads = READERS[name].map((r) => '#' + r.id + '.' + r.prop).join(', ');
      live.push(name + ' (inline=' + c.inline + ' strRef=' + c.strRef + ' calls=' + c.calls
        + ') would throw on: ' + reads);
    }
  });
  assert.deepStrictEqual(live, [],
    'a quarantined dead function is now reachable, and it dereferences an element that '
    + 'does not exist -- the click will throw a TypeError and do nothing further. '
    + 'Either build the missing markup or remove the wiring:\n         ' + live.join('\n         '));
});

test('the register is printed, because 0d requires them named', () => {
  // Guardian 0d: "Never let a dormant panel just continue existing unmentioned."
  // Printing is the point of this test, not a side effect.
  const total = NAMES.reduce((n, f) => n + READERS[f].length, 0);
  console.log('         QUARANTINED: ' + NAMES.length + ' function(s), ' + total
    + ' unguarded read(s) of a missing element:');
  NAMES.forEach((f) => {
    const ids = Array.from(new Set(READERS[f].map((r) => r.id))).sort().join(', ');
    console.log('           ' + f.padEnd(22) + ' -> ' + ids);
  });
  assert.ok(total >= 20, 'the register is empty -- see the floor assertion above');
});

// ═══════════════════════════════════════════════════════════════════════════
section('3. the two runtime-created modals are NOT in this set');

test('sairn-compare-modal and sairn-cam-modal are not reported missing', () => {
  // The first version of this analysis flagged both, because they carry no
  // `id="..."` anywhere in the source -- they are created by `modal.id = '...'`
  // and appendChild at run time. openCompare() and openCamera() are LIVE
  // functions, so had that stood it would have read as two live crashes that
  // are not real. The tool already resolves this class; the hand-rolled scan
  // did not.
  ['sairn-compare-modal', 'sairn-cam-modal'].forEach((id) => {
    assert.ok(!MISSING.ids.has(id),
      id + ' is being reported missing again -- it is created at run time by '
      + 'modal.id assignment, and treating it as missing invents a crash in a live path');
  });
  assert.ok(/\.id\s*=\s*'sairn-cam-modal'/.test(src), 'the runtime id assignment was removed');
});

// ═══════════════════════════════════════════════════════════════════════════
console.log('\n' + pass + '/' + (pass + fail) + ' passed');
process.exit(fail ? 1 : 0);
