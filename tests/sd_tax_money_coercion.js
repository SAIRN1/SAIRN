// tests/sd_tax_money_coercion.js
//
// REQUIREMENT: every money fold behind StoneDesk's two tax surfaces must
//   coerce before it adds. Both surfaces state a dollar figure as fact -- one
//   to an LLM that answers tax questions from it, one on a printed report a
//   shop hands a CPA -- so a wrong number here is asserted, not merely shown.
//
// Run:  node tests/sd_tax_money_coercion.js
//
// ── THE DEFECT, MEASURED BEFORE IT WAS FIXED ──────────────────────────────
// `de7b4838` coerced eleven folds, two of them the INVOICES half of
//   profit = invoices.reduce(...Number(i.amount)||0...)
//          - bills.reduce(...(b.amt||0)...)
// and left the BILLS half uncoerced on the same line. A string sum inside a
// subtraction is worse than a string sum alone: it does not merely append, it
// produces an arbitrary large negative.
//
//   bills "100" and "200"  ->  "0100200"  ->  profit -99450, where 450 is right
//
// And `Math.max(0, profit * 0.28)` on the printed report turns that negative
// into **$0**, not a NaN -- so the failure is a silently understated tax
// figure rather than a visible error.
//
// The same function's third fold was uncoerced too:
//
//   salesTaxYTD = entries.reduce(s + (e.tax || 0))
//   entries "50" and "25"  ->  "05025"  ->  prints "$5,025" for $75
//
// Math.round("05025") is 5025. Not NaN, not an error -- a plausible wrong
// number, two orders of magnitude out, on a tax report.
//
// ── WHY THE CHECKER SAID CLEAN THE WHOLE TIME ─────────────────────────────
// `stonedesk.html::b.amt` and `stonedesk.html::e.tax` were both in
// tools/truthy_sum_baseline.json's `grandfathered` list, so truthy_sum_check.py
// exited 0 and reported CLEAN. The tool that found the eleven could not see
// these three by CONFIGURATION, not by capability. Both entries are removed in
// the same change as this fix -- a fix that leaves its own detector blind is
// half a fix.
//
// ── WHY Number(x) || 0 AND NOT Number(x || 0) ─────────────────────────────
// Following the convention `de7b4838` set and this repo already uses:
// `Number("abc") || 0` is 0, so one bad row costs that row; `Number("abc" || 0)`
// is NaN and would blank the whole figure. The counter-argument was raised in
// review and is real -- on THESE two surfaces a visible NaN would beat a
// silently under-counted total. It is not the fix taken, because the actual
// defect was never the choice between those two: it was that one operand was
// coerced and the other was not, which no choice of fallback repairs.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'stonedesk.html'), 'utf8');

let pass = 0, fail = 0;
const run = [];
function t(name, fn) { run.push([name, fn]); }
function section(s) { run.push([s, null]); }

// --- the three folds, lifted out of the file rather than modelled ---------

function foldSource(label, re) {
  const hits = HTML.match(re) || [];
  return { label, hits };
}

// ANCHORED ON `,0)` RATHER THAN THE FIRST `)`. A non-greedy `[^\n]*?\)` stops
// at the `)` inside `(e.tax||0)` and lifts half an expression, which then fails
// to parse -- an extraction bug that reads exactly like a defect in the file.
// The reducer's `, 0` seed is the only unambiguous end of these folds.
const PROFIT_RE = /var profit=invoices\.reduce\(.*?,0\)-bills\.reduce\(.*?,0\);/g;
const SALESTAX_RE = /var salesTaxYTD=entries\.reduce\(.*?,0\);/g;

// Evaluate a lifted fold against real inputs. The expression is the FILE's,
// not a copy -- a model of it could drift from what ships.
function evalFold(src, bindings) {
  const names = Object.keys(bindings);
  const vals = names.map(n => bindings[n]);
  // strip the leading `var <name>=` so what is left is the expression
  const expr = src.replace(/^var\s+[A-Za-z_$][\w$]*\s*=\s*/, '').replace(/;$/, '');
  // eslint-disable-next-line no-new-func
  return new Function(...names, 'return (' + expr + ');')(...vals);
}

// ---------------------------------------------------------------------------
section('the two profit folds -- BOTH operands coerce');

t('both profit sites are present and there are exactly two', () => {
  const f = foldSource('profit', PROFIT_RE);
  assert.strictEqual(f.hits.length, 2,
    'expected 2 profit folds (sdTaxCalc and sdTaxPrint), found ' + f.hits.length);
});

t('string money on BOTH sides still subtracts as numbers', () => {
  const { hits } = foldSource('profit', PROFIT_RE);
  const invoices = [{ amount: '500' }, { amount: '250' }];
  const bills = [{ amt: '100' }, { amt: '200' }];
  hits.forEach((src, i) => {
    const got = evalFold(src, { invoices, bills });
    assert.strictEqual(got, 450,
      'profit fold ' + i + ' returned ' + JSON.stringify(got) + ', expected 450. '
      + 'Pre-fix this was -99450, because the bills half folded to the string "0100200".');
  });
});

t('a non-numeric row costs THAT ROW and not the figure', () => {
  const { hits } = foldSource('profit', PROFIT_RE);
  const got = evalFold(hits[0], {
    invoices: [{ amount: '500' }, { amount: 'abc' }],
    bills: [{ amt: 'oops' }, { amt: 50 }]
  });
  assert.strictEqual(got, 450, 'expected 500 - 50 with the junk rows dropped, got ' + got);
});

t('THE CONTROL: ordinary numbers are unchanged', () => {
  // Without this, a fix that returned a constant would score full marks above.
  const { hits } = foldSource('profit', PROFIT_RE);
  hits.forEach((src, i) => {
    assert.strictEqual(evalFold(src, { invoices: [{ amount: 900 }], bills: [{ amt: 300 }] }), 600,
      'fold ' + i + ' broke the ordinary numeric case');
    assert.strictEqual(evalFold(src, { invoices: [], bills: [] }), 0,
      'fold ' + i + ' broke the empty case');
  });
});

t('a negative profit is no longer produced by string data, so the $0 clamp cannot hide one', () => {
  // Math.max(0, profit*0.28) on the printed report turns a negative into $0
  // rather than NaN. The clamp is not the defect and is left alone -- what is
  // fixed is that string data can no longer manufacture the negative.
  const { hits } = foldSource('profit', PROFIT_RE);
  const got = evalFold(hits[1], { invoices: [{ amount: '750' }], bills: [{ amt: '100' }, { amt: '200' }] });
  assert.ok(got > 0, 'string bills still drove profit negative: ' + got);
  assert.strictEqual(Math.round(Math.max(0, got * 0.28)), Math.round(450 * 0.28));
});

// ---------------------------------------------------------------------------
section('the sales-tax fold on the same printed report');

t('string tax entries sum as numbers', () => {
  const { hits } = foldSource('salesTaxYTD', SALESTAX_RE);
  assert.strictEqual(hits.length, 1, 'expected 1 salesTaxYTD fold, found ' + hits.length);
  const got = evalFold(hits[0], { entries: [{ tax: '50' }, { tax: '25' }] });
  assert.strictEqual(got, 75,
    'salesTaxYTD returned ' + JSON.stringify(got) + '. Pre-fix this was "05025", '
    + 'which Math.round turns into 5025 -- $75 printed as "$5,025".');
  assert.strictEqual(Math.round(got), 75);
});

t('THE CONTROL: ordinary numbers and the empty case are unchanged', () => {
  const { hits } = foldSource('salesTaxYTD', SALESTAX_RE);
  assert.strictEqual(evalFold(hits[0], { entries: [{ tax: 40 }, { tax: 60 }] }), 100);
  assert.strictEqual(evalFold(hits[0], { entries: [] }), 0);
});

// ---------------------------------------------------------------------------
section('the THIRD tax surface, found only because the baseline was cleared');

// taxRender() draws panel-tax's KPI tiles -- tax-kpi-revenue, -expenses,
// -profit, -tax-est, plus tax-ytd and tax-est -- from four folds with the same
// defect. It was invisible while b.amt and e.tax were grandfathered, and the
// FIRST of its folds is worse than the rest: `s + i.amount` carries no `|| 0`
// at all, so the checker's own `+ (x || 0)` pattern cannot match it and never
// could. Removing a baseline entry is what surfaced a fold the detector is
// structurally unable to find.
// BOUND TO taxRender's OWN SOURCE COLLECTIONS, not just the target names. A
// looser pattern also matched sdTaxPrint's `salesTaxYTD=entries.reduce(...)`
// -- four hits for three folds -- and then failed with "entries is not
// defined", which reads like a defect in the file and is a defect in the
// extraction. taxRender folds `taxEntries`; sdTaxPrint folds `entries`.
const TAXRENDER_RE =
  /var (?:invTotal=sd_invoices\?sd_invoices|expTotal=apBillsReal|salesTaxYTD=taxEntries)\.reduce\(.*?,0\)(?::0)?;/g;

t('all three taxRender folds coerce', () => {
  const hits = HTML.match(TAXRENDER_RE) || [];
  assert.strictEqual(hits.length, 3, 'expected 3 taxRender folds, found ' + hits.length);
  const bind = {
    sd_invoices: [{ amount: '500' }, { amount: '250' }],
    apBillsReal: [{ amt: '100' }, { amt: '200' }],
    taxEntries: [{ tax: '50' }, { tax: '25' }]
  };
  const want = { invTotal: 750, expTotal: 300, salesTaxYTD: 75 };
  hits.forEach(src => {
    const name = src.match(/^var (\w+)=/)[1];
    assert.strictEqual(evalFold(src, bind), want[name],
      name + ' returned ' + JSON.stringify(evalFold(src, bind)) + ', expected ' + want[name]);
  });
});

t('...so the panel-tax profit tile and its $0 clamp cannot be driven negative by strings', () => {
  const hits = HTML.match(TAXRENDER_RE) || [];
  const bind = { sd_invoices: [{ amount: '500' }, { amount: '250' }],
                 apBillsReal: [{ amt: '100' }, { amt: '200' }], taxEntries: [] };
  const by = {};
  hits.forEach(src => { by[src.match(/^var (\w+)=/)[1]] = evalFold(src, bind); });
  const profit = by.invTotal - by.expTotal;
  assert.strictEqual(profit, 450, 'panel-tax profit is ' + profit);
  assert.ok(Math.max(0, profit * 0.28) > 0, 'the clamp still swallows a string-driven negative');
});

t('THE CONTROL: taxRender is unchanged on ordinary numbers and empties', () => {
  const hits = HTML.match(TAXRENDER_RE) || [];
  const bind = { sd_invoices: [{ amount: 900 }], apBillsReal: [{ amt: 300 }], taxEntries: [{ tax: 10 }] };
  const by = {};
  hits.forEach(src => { by[src.match(/^var (\w+)=/)[1]] = evalFold(src, bind); });
  assert.deepStrictEqual(by, { invTotal: 900, expTotal: 300, salesTaxYTD: 10 });
  const empty = { sd_invoices: [], apBillsReal: [], taxEntries: [] };
  hits.forEach(src => assert.strictEqual(evalFold(src, empty), 0, src.slice(0, 40) + ' broke on empty'));
});

// ---------------------------------------------------------------------------
section('the detector can see this class again');

t('b.amt and e.tax are NO LONGER grandfathered', () => {
  // A fix that leaves its own detector blind is half a fix: the checker
  // reported CLEAN throughout, by configuration rather than capability.
  const baseline = JSON.parse(
    fs.readFileSync(path.join(__dirname, '..', 'tools', 'truthy_sum_baseline.json'), 'utf8'));
  const g = Object.keys(baseline.grandfathered || {});
  ['stonedesk.html::b.amt', 'stonedesk.html::e.tax'].forEach(k => {
    assert.ok(!g.includes(k), k + ' is still grandfathered, so the checker still cannot fail on it');
  });
});

t('...and no OTHER grandfathered entry was removed in passing', () => {
  // The diff should subtract exactly two. Anything else is scope the change
  // did not ask for, and a silently shortened baseline is how a real
  // grandfathered hazard stops being tracked.
  const baseline = JSON.parse(
    fs.readFileSync(path.join(__dirname, '..', 'tools', 'truthy_sum_baseline.json'), 'utf8'));
  const n = Object.keys(baseline.grandfathered || {}).length;
  assert.strictEqual(n, 46, 'grandfathered count is ' + n + ', expected 46 (48 - 2)');
});

// ---------------------------------------------------------------------------
section('the control: this suite can fail');

t('the PRE-FIX expressions are refused by the arms above', () => {
  // Proves the arms test coercion and not some other property of the line.
  const preProfit = 'var profit=invoices.reduce(function(s,i){return s+(Number(i.amount)||0);},0)'
    + '-bills.reduce(function(s,b){return s+(b.amt||0);},0);';
  const preTax = 'var salesTaxYTD=entries.reduce(function(s,e){return s+(e.tax||0);},0);';
  assert.strictEqual(
    evalFold(preProfit, { invoices: [{ amount: '500' }, { amount: '250' }], bills: [{ amt: '100' }, { amt: '200' }] }),
    -99450, 'the pre-fix profit expression no longer reproduces -99450 -- the arms may pass for the wrong reason');
  assert.strictEqual(
    evalFold(preTax, { entries: [{ tax: '50' }, { tax: '25' }] }),
    '05025', 'the pre-fix sales-tax expression no longer reproduces "05025"');
});

// ---------------------------------------------------------------------------
(async () => {
  for (const [name, fn] of run) {
    if (fn === null) { console.log('--- ' + name + ' ---'); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
  }
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
