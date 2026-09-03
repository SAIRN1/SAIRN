// tests/cut_sheet_basis_parity.js
//
// Run:  node tests/cut_sheet_basis_parity.js
//
// THE BUG CLASS: two copies of one calculation, and the copy that leaves the
// building diverges from the one on screen.
//
// 2026-09-03, first pass. calcDrawing() rendered three figures each with a
// sub-label stating its basis. printDrawCutSheet() recomputed the same three
// for the Fabrication Cut Sheet -- the copy that goes to the saw and, on some
// jobs, to the customer -- and stated none of them. ORDER QTY silently
// included a 15% waste allowance, Slabs Est. silently assumed the configured
// slab size, and Est. Labor was computed at GRANITE's rate regardless of the
// material printed a few rows above it.
//
// 2026-09-03, second pass, on Michael's decision. THH is now material-aware
// and the rates are shop-configurable (sairn-unit-thh_*) instead of stranded
// inside a prompt string where nothing in the app could read them. Two copies
// of the arithmetic became one shared helper, which is the property this file
// now holds: not "both compute the same expression" but "there is only one
// expression".
//
// A THIRD THING WAS WRONG AND IS FIXED: the old formula divided by
// `slabSqFt`, the admin-editable SLAB SIZE. The benchmark is defined per 50
// SF, so a shop that set slab size to 55 silently rescaled every labour
// estimate -- buying bigger slabs made jobs take fewer hours. The benchmark
// denominator is now its own constant.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const ROOT = path.join(__dirname, '..');
// Newlines normalised before anything looks for one. This tree is checked out
// CRLF on Windows and LF elsewhere, so a boundary marker written as '\n}\n'
// matches on one machine and silently finds nothing on the other -- which
// reads as "function not found" rather than as a line-ending problem.
const html = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8').replace(/\r\n/g, '\n');

function slice(startMarker, endMarker, from) {
  const s = html.indexOf(startMarker, from || 0);
  assert.ok(s > 0, 'not found in stonedesk.html: ' + startMarker);
  const e = html.indexOf(endMarker, s + 100);
  assert.ok(e > s, 'unterminated: ' + startMarker);
  return html.slice(s, e);
}

const helper = slice('function sdThhFor(materialText, totalMatSqFt){', '\n}');
const classify = slice('function sdThhClassify(materialText){', '\n}');
const calc = slice('function calcDrawing() {', 'function dcSyncLiveToQuoteEngine');
const print = slice('function printDrawCutSheet() {', '\n}\n');

let n = 0;
function ok(cond, label) { assert.ok(cond, label); n++; }

// ── 1. ONE expression, not two ─────────────────────────────────────────────
// Checked against the CODE, not the whole file: the helper's header quotes the
// old expression verbatim to explain what it replaced, and a file-wide match
// would hit that explanation. Comment lines are stripped first. (Scrubber item
// 16 shape A -- the same trap tests/stonedesk_locations.js already records.)
const codeOnly = html.split('\n').filter(function (l) { return !/^\s*(\/\/|\*|\/\*)/.test(l); }).join('\n');
ok(!/totalMat\/slabSqFt\*4/.test(codeOnly),
   'the hardcoded granite-rate formula is gone from the code, not just from one copy of it');
ok(/sdThhFor\(\(document\.getElementById\('draw-material'\)\|\|\{\}\)\.value, totalMat\)/.test(calc),
   'calcDrawing computes THH through the shared helper');
ok(/sdThhFor\(\(document\.getElementById\('draw-material'\)\|\|\{\}\)\.value, totalMat\)/.test(print),
   'printDrawCutSheet computes THH through the SAME shared helper');
ok(/thhInfo\.basis/.test(calc) && /thhInfo\.basis/.test(print),
   'and both render the basis the helper returns, so they cannot state different ones');

// ── 2. The benchmark denominator is not the slab size ──────────────────────
ok(/var SD_THH_BENCH_SQFT = 50;/.test(html),
   'the per-50-sqft benchmark denominator is its own named constant');
ok(/totalMatSqFt \/ SD_THH_BENCH_SQFT\) \* rate/.test(helper),
   'labour divides by the benchmark, not by the admin-editable slab size');
ok(!/slabSqFt/.test(helper),
   'the helper does not see the slab size at all -- buying bigger slabs cannot change labour hours');

// ── 3. The rates are shop-configurable ─────────────────────────────────────
['granite', 'quartz', 'quartzite', 'marble'].forEach(function (k) {
  ok(new RegExp('id="sairn-unit-thh_' + k + '"').test(html),
     k + ' has a rate field on the pricing panel');
});
ok(/document\.getElementById\('sairn-unit-thh_' \+ k\)/.test(html),
   'and the helper reads those fields rather than a constant');

// ── 4. A blank or zero rate does not make labour free ──────────────────────
// Number('') is 0 and finite. A zero here would print "0.0 hours" as though
// the job took no work, which is the fabricated-zero shape this platform has
// been bitten by repeatedly.
ok(/isFinite\(v\) && v > 0\) \? v : SD_THH_DEFAULTS\[k\]/.test(html),
   'a blank, zero or unparseable rate falls back to the published benchmark, never to 0');

// ── 5. Quartzite is tested before quartz ───────────────────────────────────
// "quartzite" contains "quartz". Get the order wrong and every quartzite job
// silently bills at the quartz rate -- 3.5 against 4.6, a 24% understatement.
const qzi = classify.indexOf("indexOf('quartzite')");
const qz = classify.indexOf("indexOf('quartz')");
ok(qzi > 0 && qz > 0 && qzi < qz,
   'quartzite is matched before quartz, or every quartzite job bills at the quartz rate');

// ── 6. An unrecognised material is disclosed, not guessed ──────────────────
ok(/return null;/.test(classify),
   'an unrecognised material returns null rather than being assigned a guess');
ok(/Material not recognised/.test(helper),
   'and the basis line says so, instead of naming a benchmark as if it had been chosen');

// ── 7. The printed sheet still carries all three bases ─────────────────────
ok(/How these figures were calculated/.test(print), 'the cut sheet has a basis section');
ok(/flat 15% waste allowance/.test(print), 'ORDER QTY discloses the 15% waste allowance');
ok(/' sqft per slab \(set in pricing settings\)/.test(print),
   'Slabs Est. discloses the slab size actually used, from the live field not a literal');
ok(/Material<\/span>/.test(print) || /rl">Material/.test(print),
   'and the sheet still prints the job material, which is what makes the labour basis matter');

// ── 8. The stale caption stays gone ────────────────────────────────────────
ok(!/Estimated at 50 sqft per slab/.test(html),
   'the hardcoded "50" caption is still gone');
ok(/'Estimated at '\+slabSqFt\+' sqft per slab'/.test(calc),
   'and the caption is still built from the value actually used');

// ── 9. The prompt no longer carries its own copy of the rates ──────────────
ok(!/Granite 4hr per 50sqft, Quartz 3\.5hr per 50sqft/.test(html),
   'the base prompt no longer hardcodes benchmarks nothing in the app agreed with');
ok(!/Granite: 4hr\/50sqft\./.test(html),
   'and neither does MODE_PROMPTS.thh');
ok(/SHOP THH BENCHMARKS \(hours per ' \+ SD_THH_BENCH_SQFT/.test(html),
   'the assembled prompt supplies the shop-configured rates at send time');

// ── 10. The pricing fields actually persist ────────────────────────────────
// They never did. sairnSavePricing() carried unitPricing forward from storage
// and never read the form, and nothing loaded them back -- so a shop could
// edit a rate, press "Save Pricing", get a success toast and lose it on
// reload, while seven live consumers used the edited value until then.
ok(/unitPricing:Object\.assign\(\{\}, sairnGetPricing\(\)\.unitPricing, sdUnitFieldsRead\(\)\)/.test(html),
   'save reads the form instead of re-storing what was already there');
ok(/sdUnitFieldsApply\(p\.unitPricing\)/.test(html),
   'opening the pricing panel restores the saved rates');
ok(/DOMContentLoaded[\s\S]{0,200}sdUnitFieldsApply\(sairnGetPricing\(\)\.unitPricing\)/.test(html),
   'and so does page load -- the consumers read these inputs whether the modal was opened or not');
ok(/if \(isFinite\(v\)\) out\[id\.replace\('sairn-unit-',''\)\] = v;/.test(html),
   'a blank box is left out of the saved set rather than stored as a real 0');

console.log('cut_sheet_basis_parity: ' + n + '/' + n + ' assertions passed');
