// tests/stonedesk_pricing_backtest.js
//
// Run:  node tests/stonedesk_pricing_backtest.js
//
// THE PRICING FORMULA BACKTEST, TESTED WHERE IT CAN ACTUALLY BE WRONG.
//
// parseAndStress() reads a CSV THE USER UPLOADS -- a file input and a drop zone
// both land there -- and reports how close the quote formula came to what those
// jobs actually closed at. It had NO suite at all until this one, which is the
// reason the defect below survived: nothing could go red.
//
// ── WHAT IT DID, AND WHY IT WAS WORSE THAN A CRASH ─────────────────────────
// It split every line on a bare comma and zipped the values to the header BY
// POSITION. A cell containing a comma is quoted by every CSV writer on earth; a
// bare split tears that cell in two, `vals` gains an element, and every later
// column is read ONE PLACE LEFT. The shifted row's `material` and
// `project_type` then miss MATERIALS/PROJECTS, the row returns null, and
// `.filter(Boolean)` DROPS IT SILENTLY -- after which the panel prints
// "Jobs Tested: N" over a number that looks like the whole file, and an average
// computed from whichever rows happened to survive.
//
// Driven before the fix: a three-row file containing one torn row reported
// "Jobs Tested: 2", with no message of any kind. Recorded as a defect against
// stonedesk.html; fixed by refusing a file whose non-empty rows do not carry
// the header's cell count.
//
// ── THE ASSERTIONS READ THE PANEL, NOT A RETURN VALUE ──────────────────────
// parseAndStress() returns nothing. Everything it decides, it decides by
// writing innerHTML into three elements, so those are what the stubs capture
// and what these arms assert on. An arm phrased against an internal would be
// testing a function nobody calls that way.
//
// ── THE FUNCTION IS PULLED FROM THE PAGE, NOT REIMPLEMENTED ────────────────
// escHtml, MATERIALS and PROJECTS come out of stonedesk.html too. The whole
// point of arm 3 is what the REAL formula computes from the REAL material
// table; a fixture copy of either would test this file instead of the app.
//
// SD_HTML lets a negative control point this suite at a MUTATED COPY in a temp
// directory rather than patching the tracked file and restoring it. Same
// convention SB_HTML, SV_HTML, DNT_HTML, LAW_HTML, BLD_HTML and RF_HTML already
// carry. Unset -- every ordinary run, including CI -- this is exactly what it
// was.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const html = fs.readFileSync(process.env.SD_HTML
  || path.join(__dirname, '..', 'stonedesk.html'), 'utf8').replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function grab(sig, terminator) {
  const at = html.indexOf(sig);
  assert.ok(at > 0, 'not found in stonedesk.html: ' + sig);
  const end = html.indexOf(terminator, at);
  assert.ok(end > at, 'terminator not found after ' + sig);
  return html.slice(at, end + terminator.length);
}

// The three elements parseAndStress writes to. Anything else it asks for gets a
// throwaway, so a new getElementById in the function does not crash the suite --
// it shows up as an assertion that stops matching instead.
function harness() {
  const els = {
    'stress-results': { style: {}, innerHTML: '' },
    'stress-metrics': { style: {}, innerHTML: '' },
    'stress-table': { style: {}, innerHTML: '' }
  };
  const src = [
    grab('function escHtml(s){', '\n'),
    grab('var MATERIALS = {', '\n};'),
    grab('var PROJECTS = {', '\n};'),
    grab('function parseAndStress(csvText) {', '\n}')
  ].join('\n\n');
  const ctx = {
    Math, JSON, Object, Array, String, Number, Boolean, parseFloat, isFinite,
    document: { getElementById: (id) => els[id] || { style: {}, innerHTML: '' } }
  };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(src, ctx, { filename: 'stonedesk-backtest-extract.js' });
  return { run: (csv) => { ctx.parseAndStress(csv); return els; } };
}

const HEAD = 'project_type,material,run_a_in,run_b_in,run_c_in,island_in,edge_val,sinks,actual_total';
const ROW_A = 'kitchen_std,gran_mid,96,72,0,0,0,1,4200';
const ROW_B = 'bath_single,gran_mid,42,0,0,0,8,1,1400';
// What any CSV writer emits for a value containing a comma. This is the whole
// subject of the guard, so it is a realistic quoted cell and not a synthetic one.
const ROW_TORN = '"kitchen_std, rush",gran_mid,96,72,0,0,0,1,4200';

function panel(csv) {
  const els = harness().run(csv);
  const metrics = els['stress-metrics'].innerHTML;
  const table = els['stress-table'].innerHTML;
  const shown = els['stress-results'].style.display === 'block';
  const refused = /no backtest was run/.test(metrics);
  const jobsMatch = metrics.match(/class="sv">(\d+)<\/div><div class="sl">Jobs Tested/);
  return {
    shown, refused, metrics, table,
    jobs: jobsMatch ? Number(jobsMatch[1]) : null,
    text: metrics.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
  };
}

console.log('StoneDesk -- the pricing backtest reads an uploaded file, so it can be fed a bad one');

section('1. THE FOUR CASES THE GUARD EXISTS FOR');

test('a clean file is analysed, and Jobs Tested is the number of data rows', () => {
  const p = panel([HEAD, ROW_A, ROW_B].join('\n'));
  assert.strictEqual(p.refused, false, 'a clean file was refused: ' + p.text);
  assert.strictEqual(p.jobs, 2, 'Jobs Tested was ' + p.jobs + ', expected 2');
  assert.ok(p.shown, 'the results panel was not shown');
});

test('ONE torn row among good ones refuses the file -- it is not analysed around', () => {
  // The defect: before the guard this reported "Jobs Tested: 2" over a
  // three-row file, having dropped the torn row with no message at all.
  const p = panel([HEAD, ROW_A, ROW_TORN, ROW_B].join('\n'));
  assert.ok(p.refused, 'a torn row was analysed around rather than refused: ' + p.text);
  assert.strictEqual(p.jobs, null, 'a Jobs Tested figure was printed for a file that was not read');
});

test('and the refusal NAMES the line and the count, so it can be acted on', () => {
  const p = panel([HEAD, ROW_A, ROW_TORN, ROW_B].join('\n'));
  assert.match(p.text, /line 3/, 'the offending line is not named: ' + p.text);
  assert.match(p.text, /1 row\(s\)/, 'the count is not stated: ' + p.text);
  assert.match(p.text, /9 comma-separated values/,
    'the expected cell count is not stated: ' + p.text);
});

test('EVERY row torn refuses, and says so rather than showing nothing', () => {
  // This case is why the arm exists rather than being folded into the one
  // above: before the guard it fell through to a bare `return` and the panel
  // rendered NOTHING -- no error, no message, no indication a file was read.
  const p = panel([HEAD, ROW_TORN, ROW_TORN].join('\n'));
  assert.ok(p.refused, 'an entirely unreadable file produced no refusal: '
    + JSON.stringify(p.text));
  assert.match(p.text, /2 row\(s\)/, p.text);
});

test('a BLANK line mid-file is skipped, not treated as a torn row', () => {
  // A guard that refused a file for a stray blank line is a guard people route
  // around, so the distinction is asserted rather than left to the reader.
  const p = panel([HEAD, ROW_A, '', ROW_B].join('\n'));
  assert.strictEqual(p.refused, false, 'a blank line was refused as torn: ' + p.text);
  assert.strictEqual(p.jobs, 2, 'Jobs Tested was ' + p.jobs + ', expected 2');
});

section('2. THE REFUSAL LEAVES NOTHING BEHIND THAT LOOKS LIKE A RESULT');

test('a refused file clears the table -- no rows from a previous run survive', () => {
  const h = harness();
  h.run([HEAD, ROW_A, ROW_B].join('\n'));
  const before = h.run([HEAD, ROW_A, ROW_B].join('\n'))['stress-table'].innerHTML;
  assert.ok(before.length > 0, 'the clean run rendered no table to begin with');
  const after = harness();
  after.run([HEAD, ROW_A, ROW_B].join('\n'));
  const els = after.run([HEAD, ROW_TORN].join('\n'));
  assert.strictEqual(els['stress-table'].innerHTML, '',
    'a refused file left the previous run\'s rows on screen under a refusal notice');
});

section('3. THE ZIP IS BY HEADER NAME, WHICH IS THE PROPERTY THE GUARD PROTECTS');

test('reordering the columns does not change the answer', () => {
  // If the mapping were positional-by-luck this would move the numbers. It is
  // the strongest available evidence that headers.forEach((h,i)=>obj[h]=vals[i])
  // is keyed on the NAME, and it is the reason a torn row is dangerous at all:
  // tearing shifts the values out from under correct names.
  const straight = panel([HEAD, ROW_A].join('\n'));
  const swapped = panel([
    'material,project_type,run_a_in,run_b_in,run_c_in,island_in,edge_val,sinks,actual_total',
    'gran_mid,kitchen_std,96,72,0,0,0,1,4200'
  ].join('\n'));
  assert.strictEqual(swapped.refused, false, swapped.text);
  assert.strictEqual(swapped.jobs, straight.jobs);
  assert.strictEqual(swapped.metrics, straight.metrics,
    'reordering the header changed the computed metrics');
});

test('the formula is computed from the REAL material and project tables', () => {
  // gran_mid base 58, kitchen_std depthIn 25.5 / comp 1.00 / min 1800, both
  // read out of stonedesk.html rather than restated here. 168 in of run is
  // 14 LF; 58 * (25.5/25.5) * 14 * 1.15 * 1.00 = 933.8, + 1 sink at 200 =
  // 1133.8, which is under the 1800 minimum -- so the answer is the MINIMUM,
  // and that is the interesting case: it proves the floor is applied.
  const p = panel([HEAD, ROW_A].join('\n'));
  assert.strictEqual(p.refused, false, p.text);
  assert.match(p.table, /\$1,800/, 'the project minimum was not applied: ' + p.table.slice(0, 300));
  assert.match(p.table, /\$4,200/, 'the actual total is not in the row: ' + p.table.slice(0, 300));
});

section('4. WHAT IS STILL SILENT, ASSERTED SO IT CANNOT CHANGE UNNOTICED');

test('an UNKNOWN material is still dropped with no message -- recorded, not endorsed', () => {
  // NOT a guard. This arm pins CURRENT behaviour so that closing the gap is a
  // deliberate change with a red test in front of it, rather than something a
  // later edit does by accident. The defect record carries this as a declined
  // factor: the torn-row cause refuses outright, the others do not.
  const p = panel([HEAD, ROW_A, 'kitchen_std,NOT_A_MATERIAL,96,72,0,0,0,1,4200'].join('\n'));
  assert.strictEqual(p.refused, false, 'an unknown material now refuses -- if that is '
    + 'deliberate this arm should be rewritten, but it was silent when written');
  assert.strictEqual(p.jobs, 1,
    'the unknown-material row was counted; it used to be dropped silently');
});

test('a file whose rows are ALL excluded for a non-torn reason still shows NOTHING', () => {
  // The bare `if(!results.length) return;`. Found by driving the guard and
  // deliberately left in place; this arm is the record that it is still there.
  const p = panel([HEAD, 'kitchen_std,NOT_A_MATERIAL,96,72,0,0,0,1,4200'].join('\n'));
  assert.strictEqual(p.refused, false, p.text);
  assert.strictEqual(p.jobs, null, 'a metrics figure appeared: ' + p.text);
  assert.strictEqual(p.shown, false,
    'the panel is now shown for an all-excluded file -- that silence was the '
    + 'known gap, so if it has been closed this arm should say so instead');
});

section('5. SHAPES A REAL UPLOAD ARRIVES IN');

test('Windows line endings do not tear every row', () => {
  const p = panel([HEAD, ROW_A, ROW_B].join('\r\n'));
  assert.strictEqual(p.refused, false, 'a CRLF file was refused: ' + p.text);
  assert.strictEqual(p.jobs, 2);
});

test('a trailing newline is not a torn final row', () => {
  const p = panel([HEAD, ROW_A, ROW_B].join('\n') + '\n');
  assert.strictEqual(p.refused, false, 'a trailing newline was refused: ' + p.text);
  assert.strictEqual(p.jobs, 2);
});

test('a row with FEWER cells than the header is torn too, not just more', () => {
  // The guard is a disagreement, not an overflow. A short row zipped by
  // position leaves later columns undefined, which reads as a zero.
  const p = panel([HEAD, ROW_A, 'kitchen_std,gran_mid,96'].join('\n'));
  assert.ok(p.refused, 'a SHORT row was analysed rather than refused: ' + p.text);
  assert.match(p.text, /3 values/, p.text);
});

console.log('\n' + (fail ? 'FAILED' : 'ok') + '  stonedesk_pricing_backtest: '
  + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
