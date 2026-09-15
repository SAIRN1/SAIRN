// tests/stonedesk_fixture_catalog.js
//
// Run:  node tests/stonedesk_fixture_catalog.js
//
// THE SINK / COOKTOP FIXTURE CATALOGUE -- driven verbatim from stonedesk.html.
//
// ── WHAT THIS GUARDS, AND IT IS MOSTLY A REFUSAL ──────────────────────────
// Carolyn asked for a real vendor database with autocomplete. The mechanism is
// built; the CONTENTS are not, and must not be. A sink's cutout dimension is
// not its bowl size, is not its overall size, and is not derivable from either
// -- it is published per model, and it is the number a slab is cut to.
//
// So the arms below are largely about what this must never do: invent a cutout,
// derive one, fuzzy-match a near-miss into a real model, or let an entry with
// no spec source pass as verified. Every one of those would be invisible at the
// desk and discovered by the fabricator with the slab already on the saw.
//
// An empty catalogue is a FIRST-CLASS STATE, not a broken control: the app
// falls back to the generic shapes and says so.

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

function slice(a, b) {
  const i = html.indexOf(a);
  assert.ok(i > 0, 'not found in stonedesk.html: ' + a);
  const j = html.indexOf(b, i);
  assert.ok(j > i, 'end marker not found after ' + a);
  return html.slice(i, j);
}

const SRC = slice('// ── THE FIXTURE CATALOGUE (2026-09-15', '// Fills both pickers and says');

const NEEDED = ['sdFixtureCatalog', 'sdFixturesOfKind', 'sdFixtureLabel',
                'sdFindFixture', 'sdFixtureCutoutIn'];

function harness(rows) {
  const ctx = {
    console, Array, Object, String, parseFloat,
    sdLoad: (k, d) => (rows === undefined ? d : rows),
    document: { createElement: () => ({ appendChild() {} }) }
  };
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  for (const fn of NEEDED) {
    assert.strictEqual(typeof ctx[fn], 'function',
      'extraction failed: ' + fn + ' is not defined -- the slice anchors have '
      + 'moved and every arm below would be testing nothing');
  }
  return ctx;
}

const VERIFIED = { id: 'f1', kind: 'sink', vendor: 'Blanco', model: 'X-1',
                   cutoutWIn: 33, cutoutDIn: 19, specSource: 'blanco-x1-spec.pdf' };
const NO_SOURCE = { id: 'f2', kind: 'sink', vendor: 'Elkay', model: 'Y-2',
                    cutoutWIn: 30, cutoutDIn: 18 };
const NO_CUTOUT = { id: 'f3', kind: 'sink', vendor: 'Kraus', model: 'Z-3',
                    bowlWIn: 30, bowlDIn: 18, specSource: 'measured in showroom' };
const A_COOKTOP = { id: 'f4', kind: 'cooktop', vendor: 'Bosch', model: 'C-4',
                    cutoutWIn: 28.5, cutoutDIn: 19.5, specSource: 'bosch-c4.pdf' };

console.log('stonedesk fixture catalogue -- a cutout is published, never derived');

section('0. the page really was read');

test('every catalogue function was extracted', () => {
  const c = harness([]);
  NEEDED.forEach((f) => assert.strictEqual(typeof c[f], 'function', f));
});

section('1. it ships empty, and empty is a state rather than a failure');

test('an empty catalogue yields no fixtures of either kind', () => {
  const c = harness([]);
  assert.deepStrictEqual(c.sdFixturesOfKind('sink'), []);
  assert.deepStrictEqual(c.sdFixturesOfKind('cooktop'), []);
});

test('a corrupt store is an empty catalogue, not a crash', () => {
  const c = harness('not an array');
  const got = c.sdFixtureCatalog();
  // NOT deepStrictEqual AGAINST A LITERAL, and the reason is a real trap rather
  // than a style choice. This `[]` is constructed INSIDE the vm context, so its
  // prototype is that realm's Array -- deepStrictEqual reports "same structure
  // but not reference-equal" and the arm fails against code that is correct.
  // The arms above happen to pass only because they filter the OUTER array this
  // harness passed in. Asserted on the properties that carry the meaning.
  assert.ok(Array.isArray(got), 'got ' + typeof got);
  assert.strictEqual(got.length, 0);
});

section('2. a cooktop never autocompletes into a sink cutout');

test('kinds are kept apart', () => {
  const c = harness([VERIFIED, A_COOKTOP]);
  assert.deepStrictEqual(c.sdFixturesOfKind('sink').map((r) => r.id), ['f1']);
  assert.deepStrictEqual(c.sdFixturesOfKind('cooktop').map((r) => r.id), ['f4']);
  assert.strictEqual(c.sdFindFixture('sink', 'Bosch C-4'), null,
    'a cooktop resolved through the sink picker');
});

section('3. matching is exact -- a near miss is NOT resolved');

test('the exact "Vendor Model" string matches', () => {
  const c = harness([VERIFIED]);
  assert.strictEqual(c.sdFindFixture('sink', 'Blanco X-1').id, 'f1');
});

test('case and surrounding space do not matter', () => {
  const c = harness([VERIFIED]);
  assert.strictEqual(c.sdFindFixture('sink', '  blanco x-1 ').id, 'f1');
});

test('A PREFIX DOES NOT MATCH -- half a model name resolves to nothing', () => {
  // The arm that matters. A picker that helpfully completes "Blanco X" into
  // "Blanco X-1" is a picker that silently cuts the wrong hole, and the two
  // models differ by one character on real spec sheets.
  const c = harness([VERIFIED]);
  assert.strictEqual(c.sdFindFixture('sink', 'Blanco X'), null);
  assert.strictEqual(c.sdFindFixture('sink', 'Blanco'), null);
});

test('an AMBIGUOUS name resolves to nothing rather than to the first row', () => {
  const dup = Object.assign({}, VERIFIED, { id: 'f1b', cutoutWIn: 36 });
  const c = harness([VERIFIED, dup]);
  assert.strictEqual(c.sdFindFixture('sink', 'Blanco X-1'), null,
    'two entries with one name resolved to one of them -- a 33" and a 36" '
    + 'cutout cannot both be right and the app must not choose');
});

test('an empty string matches nothing', () => {
  const c = harness([VERIFIED]);
  assert.strictEqual(c.sdFindFixture('sink', ''), null);
  assert.strictEqual(c.sdFindFixture('sink', '   '), null);
});

section('4. a cutout is published or it is absent -- never derived');

test('a verified entry returns its cutout and says it is sourced', () => {
  const c = harness([VERIFIED]);
  const cut = c.sdFixtureCutoutIn(VERIFIED);
  assert.deepStrictEqual({ w: cut.wIn, d: cut.dIn, v: cut.verified },
                         { w: 33, d: 19, v: true });
});

test('AN ENTRY WITH NO SPEC SOURCE IS USABLE BUT NOT VERIFIED', () => {
  const c = harness([NO_SOURCE]);
  const cut = c.sdFixtureCutoutIn(NO_SOURCE);
  assert.strictEqual(cut.wIn, 30);
  assert.strictEqual(cut.verified, false,
    'an unsourced dimension passed as verified, which is the whole distinction');
});

test('AN ENTRY WITH BOWL DIMENSIONS BUT NO CUTOUT RETURNS NULL', () => {
  // The sharpest arm in the file. There is no arithmetic from bowl to cutout;
  // a function that produced one would be inventing the single number this
  // feature exists to protect.
  const c = harness([NO_CUTOUT]);
  assert.strictEqual(c.sdFixtureCutoutIn(NO_CUTOUT), null,
    'a cutout was derived from a bowl size');
});

test('a zero or negative cutout is absent, not a measurement', () => {
  const c = harness([]);
  assert.strictEqual(c.sdFixtureCutoutIn({ cutoutWIn: 0, cutoutDIn: 19 }), null);
  assert.strictEqual(c.sdFixtureCutoutIn({ cutoutWIn: -3, cutoutDIn: 19 }), null);
  assert.strictEqual(c.sdFixtureCutoutIn({ cutoutWIn: '', cutoutDIn: '' }), null);
});

test('null in, null out', () => {
  const c = harness([]);
  assert.strictEqual(c.sdFixtureCutoutIn(null), null);
});

section('5. the label is what a rep types and what a spec sheet is titled');

test('label joins vendor and model, and tolerates a missing half', () => {
  const c = harness([]);
  assert.strictEqual(c.sdFixtureLabel({ vendor: 'Blanco', model: 'X-1' }), 'Blanco X-1');
  assert.strictEqual(c.sdFixtureLabel({ model: 'X-1' }), 'X-1');
  assert.strictEqual(c.sdFixtureLabel({}), '');
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail === 0 ? 0 : 1);
