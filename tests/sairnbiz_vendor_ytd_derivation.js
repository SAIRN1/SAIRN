// tests/sairnbiz_vendor_ytd_derivation.js
//
// Run:  node tests/sairnbiz_vendor_ytd_derivation.js
//
// REQUIREMENT: vendor YTD spend is DERIVED from paid sb_ap bills -- current
// calendar year, paidDate falling back to bill date, vendors joined by
// trimmed case-folded name -- and the stored, formerly-fabricated `ytd`
// field is read by nothing.
//
// The function under test is extracted from sairnbiz.html by anchor and run
// with stubbed stores, so this suite goes red if the derivation changes shape
// -- and the extraction itself fails loudly (anchor count) rather than
// testing an empty string, which is the vacuous-arm shape this repo records.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const src = fs.readFileSync(path.join(__dirname, '..', 'sairnbiz.html'), 'utf8');

const START = 'function sbVendorPaidYTD(){';
const END = '\nfunction rVends(){';
const i = src.indexOf(START);
assert.notStrictEqual(i, -1, 'sbVendorPaidYTD not found -- the anchor moved');
assert.strictEqual(src.indexOf(START, i + 1), -1, 'sbVendorPaidYTD defined twice');
const j = src.indexOf(END, i);
assert.notStrictEqual(j, -1, 'rVends no longer follows sbVendorPaidYTD');
const fnText = src.slice(i, j);

const YEAR = new Date().getFullYear();
const LAST = YEAR - 1;

function derive(bills) {
  const ctx = {
    Date: Date, Number: Number, String: String, Object: Object,
    ld: function () { return bills; },
    sbNormalizeBills: function (b) { return b; }
  };
  vm.createContext(ctx);
  vm.runInContext(fnText + '\nthis.__out = sbVendorPaidYTD();', ctx);
  // JSON round-trip: the object was built inside the vm context, so its
  // prototype differs and deepStrictEqual would refuse structurally equal
  // values for a reason that is not this test's subject.
  return JSON.parse(JSON.stringify(ctx.__out));
}

let pass = 0;
function t(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); process.exitCode = 1; }
}

console.log('sairnbiz vendor YTD derivation');

t('paid bills accumulate per vendor; Open/Overdue/Held count nothing', () => {
  const out = derive([
    { vendor: 'Acme Stone', status: 'Paid', amt: 100, paidDate: YEAR + '-03-01' },
    { vendor: 'Acme Stone', status: 'Paid', amt: 250, paidDate: YEAR + '-06-01' },
    { vendor: 'Acme Stone', status: 'Open', amt: 999, date: YEAR + '-06-01' },
    { vendor: 'Other Co', status: 'Held', amt: 500, date: YEAR + '-06-01' }
  ]);
  assert.deepStrictEqual(out, { 'acme stone': 350 });
});

t('YTD means THIS year -- last year\'s paid bill counts nothing', () => {
  const out = derive([
    { vendor: 'Acme Stone', status: 'Paid', amt: 700, paidDate: LAST + '-12-31' },
    { vendor: 'Acme Stone', status: 'Paid', amt: 40, paidDate: YEAR + '-01-02' }
  ]);
  assert.deepStrictEqual(out, { 'acme stone': 40 });
});

t('a bill created-as-Paid has no paidDate and falls back to the bill date', () => {
  const out = derive([
    { vendor: 'Erie Ins', status: 'Paid', amt: 1140, date: YEAR + '-06-01' }
  ]);
  assert.deepStrictEqual(out, { 'erie ins': 1140 });
});

t('vendor names join trimmed and case-folded', () => {
  const out = derive([
    { vendor: '  Acme Stone ', status: 'Paid', amt: 10, paidDate: YEAR + '-02-01' },
    { vendor: 'ACME STONE', status: 'Paid', amt: 5, paidDate: YEAR + '-02-02' }
  ]);
  assert.deepStrictEqual(out, { 'acme stone': 15 });
});

t('a string amount is COERCED, not concatenated -- the quiet wrong number', () => {
  const out = derive([
    { vendor: 'Acme Stone', status: 'Paid', amt: '100', paidDate: YEAR + '-02-01' },
    { vendor: 'Acme Stone', status: 'Paid', amt: 50, paidDate: YEAR + '-02-02' }
  ]);
  assert.deepStrictEqual(out, { 'acme stone': 150 });
});

t('the fabricated stored field is read by NOTHING in the vendors panel: no '
  + 'display site reads x.ytd any more', () => {
  const panel = src.slice(src.indexOf('function rVends()'),
                          src.indexOf('}', src.indexOf('$(\'vntbody\').innerHTML')));
  assert.ok(!/\.ytd\b/.test(panel),
    'rVends still reads the stored ytd field: ' + (panel.match(/.{0,40}\.ytd.{0,40}/) || [])[0]);
  const csvLine = src.split('\n').filter((l) => l.includes("type==='vendors'"))[0] || '';
  assert.ok(!/v\.ytd/.test(csvLine), 'the CSV export still reads v.ytd');
});

// MUTATION CONTROL, in memory: strip the year filter out of the extracted
// function and prove the last-year arm above would have caught it -- so these
// arms are known to bite, not merely to agree.
t('CONTROL: removing the year filter is caught by the last-year fixture', () => {
  const anchor = "if(when.slice(0,4)!==year)return;";
  assert.strictEqual(fnText.split(anchor).length - 1, 1, 'year-filter anchor not unique');
  const mutated = fnText.replace(anchor, '');
  const ctx = {
    Date: Date, Number: Number, String: String, Object: Object,
    ld: function () {
      return [{ vendor: 'Acme Stone', status: 'Paid', amt: 700, paidDate: LAST + '-12-31' }];
    },
    sbNormalizeBills: function (b) { return b; }
  };
  vm.createContext(ctx);
  vm.runInContext(mutated + '\nthis.__out = sbVendorPaidYTD();', ctx);
  assert.deepStrictEqual(JSON.parse(JSON.stringify(ctx.__out)), { 'acme stone': 700 },
    'the mutant did not behave as expected, so the control proves nothing');
});

console.log(pass + ' passed');
