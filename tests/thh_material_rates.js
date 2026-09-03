// tests/thh_material_rates.js
//
// Run:  node tests/thh_material_rates.js
//
// THH labour hours, DRIVEN rather than pattern-matched. tests/cut_sheet_basis_parity.js
// asserts the wiring; this file runs the real extracted functions against real
// material strings and checks the hours that come out.
//
// WHAT WAS WRONG BEFORE 2026-09-03. Both calculators did
// `totalMat/slabSqFt*4` -- granite's rate on every job -- while the AI's base
// prompt stated four different rates. Same shop, same question, two answers:
// the assistant said marble benchmarks at 4.2 and the cut sheet quietly billed
// it at 4.0. The rates lived only inside a prompt string, so no shop could
// change them and nothing in the app read them.
//
// The three properties worth driving rather than reading:
//
//   1. QUARTZITE BEFORE QUARTZ. "quartzite" contains "quartz". Get the order
//      wrong and every quartzite job bills at 3.5 instead of 4.6 -- a 24%
//      understatement on the most expensive natural stone the app handles.
//   2. AN UNRECOGNISED MATERIAL IS DISCLOSED, NOT GUESSED. Free text field; a
//      shop can type anything. Falling back silently is what the old code did
//      for EVERY job.
//   3. A BLANK RATE DOES NOT MAKE LABOUR FREE. Number('') is 0 and finite.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8').replace(/\r\n/g, '\n');

function slice(a, b) {
  const s = html.indexOf(a);
  assert.ok(s > 0, 'not found: ' + a);
  const e = html.indexOf(b, s);
  assert.ok(e > s, 'unterminated: ' + a);
  return html.slice(s, e);
}

// A stand-in for the four rate inputs. The functions under test read the DOM,
// so the DOM is what gets faked -- not the functions.
function makeCtx(fieldValues) {
  const ctx = {
    console, Math, String, Number, isFinite, parseFloat,
    document: {
      getElementById: function (id) {
        if (Object.prototype.hasOwnProperty.call(fieldValues, id)) return { value: fieldValues[id] };
        return null;   // an absent field is absent, not an empty string
      }
    }
  };
  vm.createContext(ctx);
  vm.runInContext(
    slice('var SD_THH_BENCH_SQFT = 50;', 'function calcDrawing() {'),
    ctx
  );
  return ctx;
}

const DEFAULTS = {
  'sairn-unit-thh_granite': '4',
  'sairn-unit-thh_quartz': '3.5',
  'sairn-unit-thh_quartzite': '4.6',
  'sairn-unit-thh_marble': '4.2'
};

let n = 0;
function ok(cond, label) { assert.ok(cond, label); n++; }
function near(a, b, label) { assert.ok(Math.abs(a - b) < 1e-9, label + ' (got ' + a + ', wanted ' + b + ')'); n++; }
function eq(a, b, label) { assert.strictEqual(a, b, label); n++; }

const base = makeCtx(DEFAULTS);

// ── 1. Classification ──────────────────────────────────────────────────────
const C = base.sdThhClassify;
eq(C('Calacatta Gold Quartz 3cm'), 'quartz', 'a quartz product name classifies as quartz');
eq(C('Taj Mahal Quartzite 3cm'), 'quartzite', 'THE ONE THAT MATTERS: quartzite is not quartz');
eq(C('quartzite'), 'quartzite', 'bare quartzite');
eq(C('Carrara'), 'marble', 'a marble varietal with no "marble" in the string');
eq(C('Calacatta Borghini'), 'marble', 'a bare marble varietal with no explicit material word is marble');
eq(C('Cambria Calacatta'), 'quartz', 'but a BRAND beats a varietal -- Cambria Calacatta is quartz');
eq(C('Statuario'), 'marble', 'Statuario');
eq(C('Arabescato'), 'marble', 'Arabescato');
eq(C('Cambria Brittanicca'), 'quartz', 'Cambria is engineered quartz');
eq(C('Silestone Ethereal'), 'quartz', 'Silestone');
eq(C('Caesarstone 5131'), 'quartz', 'Caesarstone');
eq(C('Absolute Black Granite'), 'granite', 'granite');
eq(C('DEKTON VENTUS'), null, 'a porcelain slab is not one of the four and is not guessed at');
eq(C(''), null, 'an empty material is not classified');
eq(C('   '), null, 'whitespace is not classified');
eq(C(null), null, 'null does not throw');
eq(C(undefined), null, 'undefined does not throw');

// ── 2. The hours that actually come out ────────────────────────────────────
// 100 sqft is two benchmark units, so hours == rate * 2 and the arithmetic is
// checkable by eye.
const F = base.sdThhFor;
near(F('Absolute Black Granite', 100).hours, 8.0, 'granite 100sqft = 8.0hr');
near(F('Cambria Brittanicca', 100).hours, 7.0, 'quartz 100sqft = 7.0hr');
near(F('Taj Mahal Quartzite', 100).hours, 9.2, 'quartzite 100sqft = 9.2hr');
near(F('Carrara Marble', 100).hours, 8.4, 'marble 100sqft = 8.4hr');

// The regression in one assertion: these four used to be identical.
const spread = new Set([
  F('granite', 100).hours, F('quartz', 100).hours,
  F('quartzite', 100).hours, F('marble', 100).hours
]);
eq(spread.size, 4, 'four materials now produce four different labour figures, not one');

// And the specific pair the classifier ordering protects.
ok(F('Taj Mahal Quartzite', 100).hours > F('Cambria Quartz', 100).hours,
   'a quartzite job bills MORE than a quartz job, which is the whole point of the ordering');
near(F('Taj Mahal Quartzite', 100).hours - F('Cambria Quartz', 100).hours, 2.2,
     'and the gap is the real one: (4.6 - 3.5) x 2');

// ── 3. Unrecognised material: fallback IS the old behaviour, but disclosed ─
const unknown = F('Dekton Ventus 20mm', 100);
near(unknown.hours, 8.0, 'an unrecognised material falls back to the granite rate');
eq(unknown.matched, false, 'and is flagged as unmatched');
eq(unknown.kind, 'granite', 'with the fallback named');
ok(/Material not recognised/.test(unknown.basis),
   'and the basis SAYS SO -- the old code did this for every job and mentioned it never');
const known = F('Carrara Marble', 100);
eq(known.matched, true, 'a recognised material is flagged matched');
ok(/Marble benchmark 4\.2hr per 50 sqft/.test(known.basis), 'and names its own benchmark');
ok(!/not recognised/.test(known.basis), 'without the fallback warning');

// ── 4. Shop-configured rates are actually used ─────────────────────────────
const custom = makeCtx(Object.assign({}, DEFAULTS, { 'sairn-unit-thh_marble': '5.5' }));
near(custom.sdThhFor('Carrara Marble', 100).hours, 11.0,
     'a shop that sets marble to 5.5 gets 11.0hr on a 100sqft job');
ok(/5\.5hr per 50 sqft/.test(custom.sdThhFor('Carrara Marble', 100).basis),
   'and the basis quotes the shop rate, not the published default');
near(custom.sdThhFor('Absolute Black Granite', 100).hours, 8.0,
     'while the untouched materials are unaffected');

// ── 5. A blank, zero or junk rate never makes labour free ──────────────────
[['', 'blank'], ['0', 'zero'], ['abc', 'junk'], ['-3', 'negative']].forEach(function (row) {
  const c = makeCtx(Object.assign({}, DEFAULTS, { 'sairn-unit-thh_marble': row[0] }));
  const r = c.sdThhFor('Carrara Marble', 100);
  near(r.hours, 8.4, 'a ' + row[1] + ' marble rate falls back to the published 4.2, not to 0');
  ok(r.hours > 0, 'and never reports a job as taking no labour');
});
// The precondition that makes that guard necessary rather than decorative.
ok(Number('') === 0 && isFinite(Number('')), 'precondition: Number("") is a finite 0');

// A missing field entirely -- the pricing panel not yet rendered.
const noFields = makeCtx({});
near(noFields.sdThhFor('Carrara Marble', 100).hours, 8.4,
     'with no pricing panel in the DOM at all, the published benchmark is used');

// ── 6. Labour does not depend on slab size ─────────────────────────────────
// The old formula divided by the admin-editable slab size, so buying bigger
// slabs made jobs take fewer hours. The helper cannot see that field now, and
// this proves it rather than asserting it from the source text.
const bigSlab = makeCtx(Object.assign({}, DEFAULTS, { 'sairn-unit-slab_sqft': '120' }));
near(bigSlab.sdThhFor('Absolute Black Granite', 100).hours, 8.0,
     'setting slab size to 120 does not change labour hours');

// ── 7. Zero-size job ───────────────────────────────────────────────────────
near(F('granite', 0).hours, 0, 'a zero-sqft job is zero hours, which is a real answer');

// ── 8. Mutation probe ──────────────────────────────────────────────────────
(function () {
  const mutated = vm.createContext({
    console, Math, String, Number, isFinite, parseFloat,
    document: { getElementById: function (id) { return DEFAULTS[id] ? { value: DEFAULTS[id] } : null; } }
  });
  vm.runInContext(
    slice('var SD_THH_BENCH_SQFT = 50;', 'function calcDrawing() {')
      .replace("if (m.indexOf('quartzite') !== -1) return 'quartzite';", ''),
    mutated
  );
  eq(mutated.sdThhClassify('Taj Mahal Quartzite'), 'quartz',
     'MUTATION PROBE: drop the quartzite branch and quartzite falls through to quartz, so assertion 1 is load-bearing');
})();

console.log('thh_material_rates: ' + n + '/' + n + ' assertions passed');
