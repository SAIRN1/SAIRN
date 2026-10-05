// REQUIREMENT: an undated payment that cannot be attributed to a tax year must
//   be NAMED, whoever the payee is and whichever direction the bill date
//   points -- and a future-dated bill marked Paid must never be folded into a
//   1099 at-risk figure.
//
// Drives sbVendorPaidUndatedOtherYear() out of sairnbiz.html against hand-built
// sb_ap data. H2 seq 507 and 508.
//
// ── WHY THE FUNCTION IS EXTRACTED RATHER THAN THE PANEL RENDERED ────────────
// The two findings are both about WHICH ROWS REACH THE NOTE, and that is
// decided entirely inside this function plus one set-difference in rVends. A
// DOM harness would add a renderer, a store and a template to the blast radius
// of an arithmetic question. The set-difference half is asserted here directly
// against the same keys rVends uses, and that is stated as the limit rather
// than implied: THIS FILE DOES NOT PROVE THE ROW IS PAINTED.
'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const SRC = fs.readFileSync(
  path.join(__dirname, '..', 'sairnbiz.html'), 'utf8').replace(/\r\n/g, '\n');

// Pull the function out by name and evaluate it with the two helpers it needs.
// Anchored on the DECLARATION, and it must appear exactly once -- an anchor
// that matches twice picks a function nobody chose.
const NAME = 'sbVendorPaidUndatedOtherYear';
const occurrences = SRC.split('function ' + NAME + '(').length - 1;
assert.strictEqual(occurrences, 1,
  'expected exactly one declaration of ' + NAME + ', found ' + occurrences +
  ' -- the anchor is ambiguous and this suite would be testing a guess');

const start = SRC.indexOf('function ' + NAME + '(');
// Walk braces so the slice is the whole function and not a fixed window.
let depth = 0, end = -1;
for (let i = SRC.indexOf('{', start); i < SRC.length; i++) {
  if (SRC[i] === '{') depth++;
  else if (SRC[i] === '}') { depth--; if (depth === 0) { end = i + 1; break; } }
}
assert.ok(end > start, 'could not find the end of ' + NAME);
const FN_SRC = SRC.slice(start, end);

let BILLS = [];
// sbNormalizeBills is the app's own shaping step; the parts this function uses
// are status, paidDate, date, vendor and amt, so the stand-in passes them
// through unchanged. Named as a stand-in so nobody reads this as proof the
// real normaliser agrees.
const sbNormalizeBills = (rows) => rows;
const ld = () => BILLS;
// eslint-disable-next-line no-new-func
const fn = new Function('sbNormalizeBills', 'ld',
  FN_SRC + '\nreturn ' + NAME + ';')(sbNormalizeBills, ld);

const YEAR = String(new Date().getFullYear());
const PRIOR = String(new Date().getFullYear() - 1);
const FUTURE = String(new Date().getFullYear() + 1);

let pass = 0, fail = 0;
function t(name, run) {
  try { run(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}

function bill(o) {
  return Object.assign({ status: 'Paid', vendor: 'Acme', amt: 100 }, o);
}

console.log('sb_ap undated-payee notes -- H2 seq 507 and 508');

t('a PRIOR-year bill marked Paid with no paidDate lands in prior', () => {
  BILLS = [bill({ date: PRIOR + '-03-01', amt: 700 })];
  const r = fn();
  assert.strictEqual(r.prior.acme, 700);
  assert.strictEqual(r.future.acme, undefined);
});

t('seq 508: a FUTURE-dated bill marked Paid is NOT prior-year', () => {
  BILLS = [bill({ date: FUTURE + '-03-01', amt: 900 })];
  const r = fn();
  assert.strictEqual(r.prior.acme, undefined,
    'a future-dated bill was counted as a prior-year ambiguity -- that is the '
    + 'defect the old name hid');
  assert.strictEqual(r.future.acme, 900, 'it must still be REPORTED, not dropped');
});

t('seq 508 control: widening the guard would have DROPPED it, so both buckets exist', () => {
  BILLS = [bill({ date: PRIOR + '-01-01', amt: 10 }),
           bill({ date: FUTURE + '-01-01', amt: 20 })];
  const r = fn();
  assert.strictEqual(r.prior.acme, 10);
  assert.strictEqual(r.future.acme, 20);
});

t('a THIS-year bill is in neither bucket -- it already counts toward YTD', () => {
  BILLS = [bill({ date: YEAR + '-05-05', amt: 500 })];
  const r = fn();
  assert.deepStrictEqual(r.prior, {});
  assert.deepStrictEqual(r.future, {});
});

t('a stamped paidDate is dated and never enters either bucket', () => {
  BILLS = [bill({ date: PRIOR + '-01-01', paidDate: YEAR + '-02-02', amt: 400 })];
  const r = fn();
  assert.deepStrictEqual(r.prior, {});
  assert.deepStrictEqual(r.future, {});
});

t('an UNREADABLE year is treated as prior, not dropped -- under-counting is the harm', () => {
  BILLS = [bill({ date: '', amt: 300 })];
  const r = fn();
  assert.strictEqual(r.prior.acme, 300);
});

t('an unpaid bill is not a payment', () => {
  BILLS = [bill({ status: 'Open', date: PRIOR + '-01-01', amt: 800 })];
  const r = fn();
  assert.deepStrictEqual(r.prior, {});
});

t('names are folded the way sbVendorPaidYTD folds them -- trimmed, case-folded', () => {
  BILLS = [bill({ vendor: ' ACME ', date: PRIOR + '-01-01', amt: 50 }),
           bill({ vendor: 'acme', date: PRIOR + '-02-01', amt: 70 })];
  const r = fn();
  assert.strictEqual(r.prior.acme, 120,
    'two spellings of one payee must be one key, or the threshold is computed '
    + 'per spelling');
});

t('seq 507: an UNLISTED payee is still a key, so the set difference can find it', () => {
  BILLS = [bill({ vendor: 'One Off Contractor', date: PRIOR + '-01-01', amt: 2500 })];
  const r = fn();
  const listed = { acme: 1 };                    // the sb_vends side of rVends
  const orphans = Object.keys(r.prior).filter((k) => !listed[k]);
  assert.deepStrictEqual(orphans, ['one off contractor'],
    'the unlisted payee is invisible to the vendor-list loop, so the note can '
    + 'only exist if the key survives here');
  assert.strictEqual(r.prior['one off contractor'], 2500);
});

t('seq 507 control: a LISTED payee is not reported as an orphan', () => {
  BILLS = [bill({ vendor: 'Acme', date: PRIOR + '-01-01', amt: 2500 })];
  const r = fn();
  const listed = { acme: 1 };
  assert.deepStrictEqual(Object.keys(r.prior).filter((k) => !listed[k]), [],
    'a listed vendor must go through the threshold loop, not the orphan note');
});

t('rVends still unions the orphan keys rather than only walking sb_vends', () => {
  // The set-difference half, asserted against the SOURCE because this suite
  // does not render the panel. If this anchor stops matching, the note has
  // been removed or rewritten and these arms no longer describe the screen.
  assert.ok(/Object\.keys\(und\)\.forEach/.test(SRC),
    'rVends no longer iterates the undated keys, so an unlisted payee is '
    + 'unreachable again');
  assert.ok(/NOT ON THE VENDOR LIST/.test(SRC),
    'the unlisted-payee note is gone from the panel');
  assert.ok(/FUTURE year already marked Paid/.test(SRC),
    'the future-dated note is gone from the panel');
});

console.log('');
console.log(pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
