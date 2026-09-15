// tests/stonedesk_inside_corner_radius.js
//
// Run:  node tests/stonedesk_inside_corner_radius.js
//
// INSIDE-CORNER RADIUS AS A CUT TYPE, AND THE 2" MINIMUM -- driven verbatim
// from stonedesk.html.
//
// ── WHAT THIS IS AND WHERE IT CAME FROM ───────────────────────────────────
// Carolyn's drawing-tool requirements, 2026-09-15. Two of the four were
// already built and the premise is corrected in the commit rather than here:
// CHAMFER has shipped since 2026-08-12, with pricing, canvas rendering and a
// cut-sheet line. What did not exist anywhere was a RADIUS, the distinction
// between the two, or any minimum.
//
// ── WHY A MINIMUM IS A REFUSAL AND NOT A DEFAULT ──────────────────────────
// An inside corner is a stress riser -- it is where a slab cracks, in
// fabrication, in transport, or years later under thermal movement. 2 inches
// is Carolyn's number, taken as a requirement; this app does not derive a safe
// radius from stone type or span and must not appear to. What it does is
// refuse to PRODUCE A DRAWING specifying less, because a cut sheet reading
// "0.5in radius" is an instruction somebody follows.
//
// ── THE ARM THAT MATTERS IS THE SHORT-RUN ONE ─────────────────────────────
// On a corner whose adjacent runs are short, the existing 0.4x clamp lands
// BELOW the 2in floor. Clamping before checking the floor would silently
// produce a 1.2in radius that passes every later check -- exactly the number
// this feature exists to refuse -- so the order of those two tests is the
// whole guard, and section 3 drives it.

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'stonedesk.html'), 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); pass++; console.log('  ok   - ' + name); }
  catch (e) { fail++; console.log('  FAIL - ' + name + '\n         ' + e.message); }
}
function section(t) { console.log('\n--- ' + t + ' ---'); }

function slice(startMark, endMark) {
  const a = html.indexOf(startMark);
  assert.ok(a > 0, 'not found in stonedesk.html: ' + startMark);
  const b = html.indexOf(endMark, a);
  assert.ok(b > a, 'end marker not found after ' + startMark);
  return html.slice(a, b);
}

// The corner model, from the banner that opens it to the start of the edge-
// assignment UI. Anchored on comment text rather than line numbers, the same
// way every other extraction suite in this repo does it.
const SRC = slice('// ── RADIUS IS A SECOND CUT TYPE', '// Build edge assignment selectors');

const NEEDED = ['dcChamferKeyFor', 'dcChamferAdjacentRunsIn', 'dcChamferMaxSetbackIn',
                'dcChamferEffectiveSetbackIn', 'dcSetChamferSetback', 'dcCornerKind'];

// Adjacent runs come from the dimension inputs via gN(); the harness supplies
// them directly so the geometry can be driven without a DOM.
function harness(dims) {
  const toasts = [];
  const ctx = {
    console, Math, Object, String, parseFloat, Number, isNaN,
    gN: (id) => (dims && dims[id] !== undefined ? dims[id] : 0),
    showToast: (m) => toasts.push(String(m)),
    drawCTPreview: () => {},
    calcDrawing: () => {},
    ctShape: 'lshape',
    __toasts: toasts
  };
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  for (const fn of NEEDED) {
    assert.strictEqual(typeof ctx[fn], 'function',
      'extraction failed: ' + fn + ' is not defined -- the slice anchors in '
      + 'stonedesk.html have moved and every arm below would be testing nothing');
  }
  return ctx;
}

// Long runs: the 0.4x clamp is far above the 2in floor, so the floor is the
// only thing that can bind.
const ROOMY = { 'db-len': 60, 'da-len': 120, 'db-dep': 25 };
// Short runs: max setback is 0.4 * 4 = 1.6in, BELOW the 2in minimum. This is
// the fixture that separates "check the floor first" from "clamp first".
const CRAMPED = { 'db-len': 4, 'da-len': 30, 'db-dep': 25 };

const KEY = 'lshape-AB';

console.log('stonedesk inside corners -- radius is a distinct cut, with a floor');

section('0. the page really was read, and the fixtures do what they claim');

test('every corner function was extracted from stonedesk.html', () => {
  const c = harness(ROOMY);
  NEEDED.forEach((f) => assert.strictEqual(typeof c[f], 'function', f));
});

test('the ROOMY fixture allows well over the minimum', () => {
  const c = harness(ROOMY);
  assert.ok(c.dcChamferMaxSetbackIn(KEY) > c.DC_MIN_INSIDE_RADIUS_IN,
    'max is ' + c.dcChamferMaxSetbackIn(KEY) + ' -- section 2 would pass for the wrong reason');
});

test('the CRAMPED fixture allows LESS than the minimum', () => {
  const c = harness(CRAMPED);
  const max = c.dcChamferMaxSetbackIn(KEY);
  assert.ok(max > 0 && max < c.DC_MIN_INSIDE_RADIUS_IN,
    'max is ' + max + ' -- section 3 is not testing the collision it names');
});

section('1. the two cut types are distinct, and absent means chamfer');

test('a record with no kind reads as a chamfer', () => {
  const c = harness(ROOMY);
  c.dcChamferedCorners[KEY] = { setbackIn: 1.5 };
  assert.strictEqual(c.dcCornerKind(KEY), 'chamfer',
    'a pre-existing record without the new field changed meaning');
});

test('kind radius reads as a radius', () => {
  const c = harness(ROOMY);
  c.dcChamferedCorners[KEY] = { setbackIn: 3, kind: 'radius' };
  assert.strictEqual(c.dcCornerKind(KEY), 'radius');
});

test('an unset corner is neither -- it is square', () => {
  const c = harness(ROOMY);
  assert.strictEqual(c.dcChamferEffectiveSetbackIn(KEY), 0);
});

section('2. the 2" minimum refuses rather than silently raising');

test('a 0.5in RADIUS is refused and nothing is stored', () => {
  const c = harness(ROOMY);
  c.dcChamferedCorners[KEY] = { setbackIn: 4, kind: 'radius' };
  c.dcSetChamferSetback(KEY, '0.5', null, null);
  assert.strictEqual(c.dcChamferedCorners[KEY].setbackIn, 4,
    'the refused value was written anyway');
  assert.ok(c.__toasts.some((t) => /at least 2/.test(t)),
    'nothing told the rep why: ' + JSON.stringify(c.__toasts));
});

test('...and it is NOT quietly raised to 2', () => {
  const c = harness(ROOMY);
  c.dcChamferedCorners[KEY] = { setbackIn: 4, kind: 'radius' };
  c.dcSetChamferSetback(KEY, '0.5', null, null);
  assert.notStrictEqual(c.dcChamferedCorners[KEY].setbackIn, 2,
    'a silent correction changes the drawn geometry and the price under a rep '
    + 'who never saw it happen');
});

test('exactly 2in is ACCEPTED -- the floor is inclusive', () => {
  const c = harness(ROOMY);
  c.dcChamferedCorners[KEY] = { setbackIn: 0, kind: 'radius' };
  c.dcSetChamferSetback(KEY, '2', null, null);
  assert.strictEqual(c.dcChamferedCorners[KEY].setbackIn, 2);
});

test('the SAME 0.5in as a CHAMFER is allowed -- the floor is radius-only', () => {
  // The whole point of two cut types. A shallow chamfer is an ordinary eased
  // corner; a shallow radius is the stress riser. An arm that refused both
  // would mean the distinction had not been implemented at all.
  const c = harness(ROOMY);
  c.dcChamferedCorners[KEY] = { setbackIn: 0, kind: 'chamfer' };
  c.dcSetChamferSetback(KEY, '0.5', null, null);
  assert.strictEqual(c.dcChamferedCorners[KEY].setbackIn, 0.5);
});

section('3. short runs: the floor is checked BEFORE the clamp');

test('a radius on runs too short to hold 2in is REFUSED, not clamped to 1.6', () => {
  const c = harness(CRAMPED);
  c.dcChamferedCorners[KEY] = { setbackIn: 0, kind: 'radius' };
  c.dcSetChamferSetback(KEY, '2', null, null);
  assert.strictEqual(c.dcChamferedCorners[KEY].setbackIn, 0,
    'it stored ' + c.dcChamferedCorners[KEY].setbackIn + ' -- clamping ran first '
    + 'and produced an illegal radius that passes every later check');
  assert.ok(c.__toasts.some((t) => /too short/.test(t)),
    'the refusal did not name the real obstruction: ' + JSON.stringify(c.__toasts));
});

test('...and a CHAMFER on the same short runs is clamped, not refused', () => {
  const c = harness(CRAMPED);
  c.dcChamferedCorners[KEY] = { setbackIn: 0, kind: 'chamfer' };
  c.dcSetChamferSetback(KEY, '5', null, null);
  const v = c.dcChamferedCorners[KEY].setbackIn;
  assert.ok(v > 0 && v <= 1.6 + 1e-9,
    'expected a clamp to the 0.4x bound, got ' + v);
});

section('4. the geometry clamp still applies to a radius');

test('an over-long radius is clamped to the 0.4x bound, not accepted', () => {
  const c = harness(ROOMY);
  c.dcChamferedCorners[KEY] = { setbackIn: 0, kind: 'radius' };
  const max = c.dcChamferMaxSetbackIn(KEY);
  c.dcSetChamferSetback(KEY, String(max + 50), null, null);
  assert.ok(c.dcChamferedCorners[KEY].setbackIn <= max + 1e-9,
    'a radius bigger than the corner can hold was stored, which self-intersects '
    + 'the fill -- the bound chamfer already had was not extended to radius');
});

test('the effective value is re-derived, so shrinking the runs cannot leave a stale radius', () => {
  const c = harness(ROOMY);
  c.dcChamferedCorners[KEY] = { setbackIn: 20, kind: 'radius' };
  const roomy = c.dcChamferEffectiveSetbackIn(KEY);
  const c2 = harness(CRAMPED);
  c2.dcChamferedCorners[KEY] = { setbackIn: 20, kind: 'radius' };
  assert.ok(c2.dcChamferEffectiveSetbackIn(KEY) < roomy,
    'the same stored value survived a run shrink unchanged -- the cut sheet '
    + 'would specify geometry the canvas is not drawing');
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail === 0 ? 0 : 1);
