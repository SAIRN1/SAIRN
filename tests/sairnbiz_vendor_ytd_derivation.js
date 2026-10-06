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


// ── THE UNDATED PRIOR-YEAR RESIDUAL (2026-09-25) ──────────────────────────
// A row marked Paid AT CREATION never gets a paidDate, so sbVendorPaidYTD
// falls back to the BILL date -- and one dated last year is excluded from
// YTD even though the cheque may have been written this year. That
// UNDER-counts toward the $600 1099 threshold, the direction that silently
// files nothing. It is not fixed by counting it (the data does not say which
// year), so it is DISCLOSED, and these arms hold the disclosure to the same
// bar as the figure: it must identify exactly the rows the YTD figure cannot
// see, and no others.
// ── THE FUNCTION WAS SPLIT AND RENAMED (2026-10-06, seq 508) ──────────────
// It was `sbVendorPaidUndatedPriorYear()` returning a flat `{vendor: amount}`.
// The old name was itself a defect: the guard excluded only the CURRENT year,
// so a FUTURE-dated bill marked Paid landed in a bucket called PriorYear and
// fed the 1099 at-risk figure. It is now
// `sbVendorPaidUndatedOtherYear()` -> `{prior, future}`.
//
// THIS SUITE WENT RED ON THE RENAME AND THAT IS THE ANCHOR DOING ITS JOB --
// `assert.notStrictEqual(i2, -1)` is exactly the loud-extraction guard the
// header promises, and it refused to test an empty string. The arms below are
// re-pointed rather than relaxed, and the partition arm is widened from THREE
// buckets to FOUR because the split created a fourth. Relaxing it to
// `{prior}` alone would have left the new bucket untested while the suite went
// green, which is the shape that makes a red suite worth fixing properly.
const START2 = 'function sbVendorPaidUndatedOtherYear(){';
const i2 = src.indexOf(START2);
assert.notStrictEqual(i2, -1,
  'sbVendorPaidUndatedOtherYear not found -- anchor moved');
assert.strictEqual(src.indexOf(START2, i2 + 1), -1, 'defined twice');
const j2 = src.indexOf('\nfunction rVends(){', i2);
assert.notStrictEqual(j2, -1, 'rVends no longer follows it');
const undText = src.slice(i2, j2);

function buckets(bills) {
  const ctx = { Date: Date, Number: Number, String: String, Object: Object,
                ld: function () { return bills; },
                sbNormalizeBills: function (b) { return b; } };
  vm.createContext(ctx);
  vm.runInContext(undText + '\nthis.__o = sbVendorPaidUndatedOtherYear();', ctx);
  const o = JSON.parse(JSON.stringify(ctx.__o));
  // THE SHAPE IS ASSERTED, not assumed. If a later edit returns a flat object
  // again, `o.prior` would be undefined and every arm below would compare
  // undefined to undefined and PASS. That is the vacuous-arm failure this file
  // was written to avoid, one level up from the anchor.
  assert.ok(o && typeof o === 'object' && o.prior && o.future,
    'the function no longer returns {prior, future} -- arms below would be vacuous');
  return o;
}

function undated(bills) { return buckets(bills).prior; }
function future(bills) { return buckets(bills).future; }

t('a Paid row with NO paidDate and a PRIOR-year bill date is the residual', () => {
  assert.deepStrictEqual(
    undated([{ vendor: 'Acme Stone', status: 'Paid', amt: 700, date: LAST + '-11-02' }]),
    { 'acme stone': 700 });
});

t('...and it is EXCLUDED from the YTD figure, which is the whole point', () => {
  const bills = [{ vendor: 'Acme Stone', status: 'Paid', amt: 700, date: LAST + '-11-02' }];
  assert.deepStrictEqual(derive(bills), {}, 'YTD counted an undated prior-year row');
  assert.deepStrictEqual(undated(bills), { 'acme stone': 700 },
    'the residual does not see the row YTD dropped -- the gap is now invisible twice');
});

t('a STAMPED payment is never residual, whatever the bill date says', () => {
  assert.deepStrictEqual(
    undated([{ vendor: 'Acme Stone', status: 'Paid', amt: 700,
               date: LAST + '-11-02', paidDate: YEAR + '-02-01' }]), {},
    'a dated payment was reported as undecidable');
});

t('an undated THIS-year bill is not residual either -- YTD already has it', () => {
  const bills = [{ vendor: 'Acme Stone', status: 'Paid', amt: 50, date: YEAR + '-03-03' }];
  assert.deepStrictEqual(undated(bills), {});
  assert.deepStrictEqual(derive(bills), { 'acme stone': 50 });
});

t('an unpaid prior-year bill is not residual -- nothing was paid', () => {
  assert.deepStrictEqual(
    undated([{ vendor: 'Acme Stone', status: 'Open', amt: 900, date: LAST + '-11-02' }]), {});
});

t('THE PARTITION, now FOUR buckets: every Paid row lands in exactly one of '
  + 'YTD, prior-residual, future-anomaly or neither -- never two', () => {
  const bills = [
    { vendor: 'A', status: 'Paid', amt: 10, paidDate: YEAR + '-01-01' },   // YTD
    { vendor: 'B', status: 'Paid', amt: 20, date: LAST + '-01-01' },       // prior
    { vendor: 'C', status: 'Paid', amt: 30, paidDate: LAST + '-01-01' },   // neither
    { vendor: 'D', status: 'Open', amt: 40, date: YEAR + '-01-01' },       // neither
    { vendor: 'E', status: 'Paid', amt: 50, date: (YEAR + 1) + '-01-01' }  // future
  ];
  const y = derive(bills), b = buckets(bills);
  assert.deepStrictEqual(y, { a: 10 });
  assert.deepStrictEqual(b.prior, { b: 20 });
  assert.deepStrictEqual(b.future, { e: 50 }, 'the future-dated row is missing');
  // EVERY PAIR, not just YTD-vs-prior. The old arm checked one pair and a
  // third bucket was added underneath it.
  const sets = { ytd: y, prior: b.prior, future: b.future };
  Object.keys(sets).forEach((n1) => Object.keys(sets).forEach((n2) => {
    if (n1 >= n2) return;
    Object.keys(sets[n1]).forEach((k) => assert.ok(!(k in sets[n2]),
      k + ' is in BOTH ' + n1 + ' and ' + n2));
  }));
});

// ── seq 508: THE FUTURE BUCKET, AND THE ABLATION THAT PROVES IT EXISTS ─────
t('a FUTURE-dated bill marked Paid is a separate anomaly, NOT prior-year', () => {
  const bills = [{ vendor: 'Acme Stone', status: 'Paid', amt: 700,
                   date: (YEAR + 1) + '-06-01' }];
  assert.deepStrictEqual(undated(bills), {},
    'a future-dated row was counted into the 1099 at-risk prior-year figure');
  assert.deepStrictEqual(future(bills), { 'acme stone': 700 });
  assert.deepStrictEqual(derive(bills), {}, 'YTD counted a future-dated row');
});

t('CONTROL: the two buckets are reached by DIFFERENT comparisons -- a guard '
  + 'widened to "< year" would have dropped the future rows entirely', () => {
  // Driven, not asserted from the source text: the real function must put a
  // prior row and a future row in DIFFERENT buckets, and neither in both. A
  // single `y !== year` guard would put both in `prior`; a `y < year` guard
  // would lose the future row with no trace, which is the third-state-folded-
  // into-silence shape the split exists to avoid.
  const b = buckets([
    { vendor: 'P', status: 'Paid', amt: 1, date: LAST + '-01-01' },
    { vendor: 'F', status: 'Paid', amt: 2, date: (YEAR + 1) + '-01-01' }
  ]);
  assert.deepStrictEqual(b.prior, { p: 1 }, 'the prior row did not stay prior');
  assert.deepStrictEqual(b.future, { f: 2 }, 'the future row was folded or lost');
});

t('an UNREADABLE year is bucketed PRIOR rather than dropped -- under-counting '
  + 'toward the threshold is the harm, so the ambiguous row is disclosed', () => {
  assert.deepStrictEqual(
    undated([{ vendor: 'Acme Stone', status: 'Paid', amt: 700, date: '' }]),
    { 'acme stone': 700 });
});

t('the disclosure names only vendors the residual could carry OVER $600, and '
  + 'says the count is undecided rather than reporting a number', () => {
  const panel = src.slice(src.indexOf('function rVends()'),
                          src.indexOf("$('vntbody').innerHTML=html;"));
  assert.ok(panel.includes('sbVendorPaidUndatedOtherYear()'),
    'rVends does not consult the residual at all');
  // ── THE ARM PINNED A LITERAL AND THE THRESHOLD BECAME DATA (2026-10-06) ──
  // It required `spendOf(x)<600&&(spendOf(x)+u)>=600`. The code reads
  // `thr.amount`, which is the CORRECT shape -- the 1099 threshold is a
  // per-year figure and hardcoding 600 is the defect, not the contract. So the
  // arm was RED while the code was right, and it was red for that reason
  // BEFORE the seq 508 rename went anywhere near it.
  //
  // Re-pinned to the STRUCTURE and then strengthened in the direction the old
  // arm had backwards: the literal must be ABSENT from this expression.
  const flat = panel.replace(/\s/g, '');
  assert.ok(/u>0&&spendOf\(x\)<thr\.amount&&\(spendOf\(x\)\+u\)>=thr\.amount/
    .test(flat),
    'the at-risk test is not "has undated money, under the threshold now, at '
    + 'or over it with the undated amount"');
  assert.ok(!/spendOf\(x\)<600|>=600/.test(flat),
    'the threshold is hardcoded as 600 in the at-risk test -- it must come '
    + 'from thr.amount, because the 1099 figure is a per-year number');
  assert.ok(panel.includes('COULD NOT BE DECIDED'),
    'the disclosure reports a figure instead of naming it undecidable');
  assert.ok(panel.includes('Counted in NEITHER total'),
    'the disclosure does not say which total the money is in');
});

// CONTROL: the at-risk filter must DISCRIMINATE. A vendor already over the
// threshold needs no warning, and one that stays under it with the undated
// amount included is not at risk either -- a note that fires on everything is
// the furniture this codebase keeps removing.
t('CONTROL: the at-risk band excludes both already-over and still-under', () => {
  const band = (ytd, u) => ytd < 600 && (ytd + u) >= 600;
  assert.strictEqual(band(700, 50), false, 'already over $600 was flagged');
  assert.strictEqual(band(100, 50), false, 'still under $600 with the residual was flagged');
  assert.strictEqual(band(580, 30), true, 'the one case that matters was not flagged');
});

console.log(pass + ' passed');
