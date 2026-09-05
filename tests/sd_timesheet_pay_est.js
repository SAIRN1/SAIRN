// tests/sd_timesheet_pay_est.js
//
// Run:  node tests/sd_timesheet_pay_est.js
//
// StoneDesk's timesheet module priced every hour with
//
//     (x.hrs || 0) * (x.rate || 28)
//
// at SIX sites: the payroll KPI, the per-employee bars, the on-screen table,
// the CSV export's "Pay Est." column, and both halves of the printed
// timesheet. A record with no usable rate was priced at $28/hour and the
// result was presented as money — in a spreadsheet a shop owner opens and
// sums, and in a document they hand to someone.
//
// THE FINDING MOVED WHEN IT WAS RE-MEASURED, and that is why this file leads
// with the zero case. The index row said an employee with no rate on file
// "silently becomes $28/hour". The entry field is PREFILLED with 28 in the
// markup, so a rate is essentially always stored and those display fallbacks
// rarely fire. The live defect is narrower and worse: `parseFloat(...)||28`
// in sdTSLog turned a DELIBERATE 0 into 28 and stored it, and every display
// did the same to any record carrying 0. An unpaid, volunteer or salaried-zero
// entry was silently repriced at $28/hour.
//
// **0 is a rate.** Every assertion below exists to keep that true, which is
// why the helpers read the TYPE rather than truthiness.
//
// THE REAL HELPERS ARE EXTRACTED FROM THE FILE AND DRIVEN, including the CSV
// cell builder. The render and print sites need a DOM and window.open, so
// those are covered by source assertions instead — stated here rather than
// left for a reader to discover, because a source assertion is weaker: one of
// them was already caught passing a mutation that had removed the behaviour.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const FILE = 'stonedesk.html';
const SRC = fs.readFileSync(path.join(ROOT, FILE), 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

function grab(src, sig) {
  const i = src.indexOf(sig);
  assert.ok(i > 0, sig + ' not found');
  const rel = src.slice(i).search(/\r?\n  \}/);
  assert.ok(rel > 0, sig + ' is not terminated');
  return src.slice(i, i + rel) + '\n  }';
}

const ctx = { Math: Math, Number: Number, String: String, isFinite: isFinite };
vm.createContext(ctx);
['function tsRate(x){', 'function tsPay(x){', 'function tsMoney(v){',
 'function tsCell(x){', 'function tsTotal(rows){', 'function tsNote(unpriced){'].forEach((sig) => {
  vm.runInContext(grab(SRC, sig), ctx);
});

section('0 IS A RATE — the case that was being repriced at $28');

test('a deliberate 0 prices as $0, NOT $28', () => {
  assert.strictEqual(ctx.tsRate({ rate: 0 }), 0, '0 was read as "no rate"');
  assert.strictEqual(ctx.tsPay({ hrs: 8, rate: 0 }), 0);
  assert.strictEqual(ctx.tsMoney(ctx.tsPay({ hrs: 8, rate: 0 })), '$0',
    'an unpaid entry was priced');
});

test('an ordinary rate prices normally', () => {
  assert.strictEqual(ctx.tsPay({ hrs: 8, rate: 22 }), 176);
  assert.strictEqual(ctx.tsMoney(176), '$176');
});

section('a missing rate produces `--`, never a number');

[['absent', {}], ['undefined', { rate: undefined }], ['null', { rate: null }],
 ['a string', { rate: '28' }], ['NaN', { rate: NaN }],
 ['Infinity', { rate: Infinity }], ['negative', { rate: -5 }]].forEach(([label, row]) => {
  test('a ' + label + ' rate is not usable, and is not replaced', () => {
    assert.strictEqual(ctx.tsRate(row), null, label + ' was accepted as a rate');
    assert.strictEqual(ctx.tsPay(Object.assign({ hrs: 8 }, row)), null);
    assert.strictEqual(ctx.tsMoney(ctx.tsPay(Object.assign({ hrs: 8 }, row))), '--');
  });
});

test('a string rate is refused rather than coerced — the CSV is summed by a spreadsheet', () => {
  // Number('28') would "work" and is exactly how a placeholder becomes payroll.
  assert.strictEqual(ctx.tsRate({ rate: '28' }), null);
});

section('totals exclude what they cannot price, and say so');

test('tsTotal sums only priced rows and counts the rest', () => {
  const r = ctx.tsTotal([
    { hrs: 8, rate: 20 },      // 160
    { hrs: 8, rate: 0 },       //   0, priced
    { hrs: 8 },                //      unpriced
    { hrs: 4, rate: 'x' },     //      unpriced
  ]);
  assert.strictEqual(r.sum, 160);
  assert.strictEqual(r.unpriced, 2);
});

test('a total with nothing unpriced reports zero exclusions and no note', () => {
  const r = ctx.tsTotal([{ hrs: 8, rate: 20 }]);
  assert.strictEqual(r.unpriced, 0);
  assert.strictEqual(ctx.tsNote(0), '', 'a clean total carried a disclosure anyway');
});

test('the note says the rows are NOT included, and gets the plural right', () => {
  assert.match(ctx.tsNote(1), /1 row had no hourly rate/);
  assert.match(ctx.tsNote(1), /is NOT included/);
  assert.match(ctx.tsNote(3), /3 rows had no hourly rate/);
  assert.match(ctx.tsNote(3), /are NOT included/);
});

section('the six sites, asserted on the source');

test('NOT ONE `rate || 28` survives anywhere in the file', () => {
  // Whitespace-normalised, and comments stripped because the new comment
  // quotes the old expression.
  const squashed = SRC.replace(/\/\/[^\n]*/g, '').replace(/\s+/g, '');
  assert.ok(!/x\.rate\|\|28/.test(squashed), 'a $28 fallback is back');
  assert.ok(!/rate\|\|28/.test(squashed), 'a $28 fallback is back in some other spelling');
});

test('sdTSLog REFUSES a blank rate instead of defaulting to 28', () => {
  const body = SRC.slice(SRC.indexOf('window.sdTSLog=function(){'),
                         SRC.indexOf('window.sdTSAI=function(){'));
  assert.ok(body.indexOf('parseFloat(document.getElementById("ts-rate").value)||28') === -1,
    'the storing fallback is back — a cleared field writes a rate the user never gave');
  assert.ok(/showToast\(/.test(body) && /Enter an hourly rate/.test(body),
    'a blank rate is accepted silently again');
  assert.ok(/return;/.test(body), 'nothing stops the record being logged');
});

test('the CSV writes an EMPTY cell for an unpriced row, not a price', () => {
  // DRIVEN, not pattern-matched. The first version of this assertion looked
  // for the literal `p===null?"":` in the export body, and a mutation that
  // reintroduced the defect (`tsPay(x)||0`) left it GREEN -- the text was
  // still there and the behaviour was gone. That is the same class this whole
  // file is about, inside its own test.
  assert.strictEqual(ctx.tsCell({ hrs: 8 }), '', 'an unpriced row got a price in the CSV');
  assert.strictEqual(ctx.tsCell({ hrs: 8, rate: 'x' }), '', 'a junk rate got a price in the CSV');
  assert.strictEqual(ctx.tsCell({ hrs: 8, rate: 0 }), '$0', 'a real zero rate was blanked');
  assert.strictEqual(ctx.tsCell({ hrs: 8, rate: 20 }), '$160');
  // ...and it is a BLANK, not `--`: a spreadsheet sums the column, and `--`
  // is a value someone has to notice and delete.
  assert.notStrictEqual(ctx.tsCell({ hrs: 8 }), '--');
  const body = SRC.slice(SRC.indexOf('window.sdTSExport=function(){'),
                         SRC.indexOf('window.sdTSPrint=function(){'));
  assert.ok(/tsCell\(x\)/.test(body), 'the export builds its own cell again');
  assert.ok(/NOTE: /.test(body), 'the export does not disclose what it left blank');
});

test('the printed timesheet discloses a partial total ON THE PAGE', () => {
  // A tooltip cannot be hovered on paper.
  const body = SRC.slice(SRC.indexOf('window.sdTSPrint=function(){'));
  assert.ok(/Partial total/.test(body.slice(0, 3000)),
    'the printed total can silently omit rows');
});

test('the on-screen payroll KPI marks a partial total', () => {
  const squashed = SRC.replace(/\s+/g, '');
  assert.ok(/payEl\.textContent=tsMoney\(payTot\.sum\)\+\(payTot\.unpriced\?"\*":""\)/.test(squashed),
    'the KPI shows a partial total with no marker');
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' TIMESHEET PAY-EST ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
