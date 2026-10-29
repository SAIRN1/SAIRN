// tests/sairncash_prior_tax_zero.js
//
// REQUIREMENT: a prior-year tax of $0 that the user TYPED is a real answer and
//   must be kept as 0 -- not read as "not provided".
//
// Run:  node tests/sairncash_prior_tax_zero.js
//
// ── THE DEFECT (fourth b64 audit leftover, fixed fourth b68) ────────────────
// saveProfile() stored `Number(value) || null`, so a typed 0 was saved as null,
// and calcQuarterlySetAside() tested `if (priorYearTaxLiability)`, so even a
// stored 0 dropped the prior-year leg. populateProfileForm() showed `|| ''`,
// so a stored 0 came back as an empty box.
//
// WHY $0 MATTERS: 2026 Form 1040-ES Estimated Tax Worksheet, line 12b, is the
// required annual payment based on the prior year's tax (100%, or 110% above
// the AGI threshold), and line 12c is "the smaller of line 12a or 12b". With a
// 2025 tax of $0, line 12b is $0, so line 12c is $0. Reading $0 as "not
// provided" took 90% of the projected 2026 tax instead, and labelled the result
// "90% only -- add last year's tax", which asks for a figure the user had
// already entered.
//
// WRITTEN BEFORE THE FIX and run against the unfixed app: arms 1, 2, 4 and 5
// failed. Arms 3 and 6 are CONTROLS: a blank box must still mean "not
// provided", and a non-zero figure must behave as it did before.

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const FILE = path.resolve(__dirname, '..', 'sairncash.html');
const src = fs.readFileSync(FILE, 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  return Promise.resolve().then(fn).then(
    function () { console.log('  ok   ' + name); pass++; },
    function (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; });
}

// The app's own functions, lifted and RUN -- same method as
// tests/sairncash_safe_harbor.js.
function lift(name, kw) {
  const at = src.indexOf((kw || 'function') + ' ' + name + '(');
  assert.notStrictEqual(at, -1, 'function ' + name + ' not found in sairncash.html');
  const end = src.indexOf('\n}', at);
  assert.notStrictEqual(end, -1, name + ' has no column-0 closing brace');
  return src.slice(at, end + 2);
}
function liftConst(name) {
  const at = src.indexOf('const ' + name + ' = ');
  assert.notStrictEqual(at, -1, 'const ' + name + ' not found in sairncash.html');
  const oneLine = src.slice(at, src.indexOf('\n', at));
  if (/;\s*$/.test(oneLine)) return oneLine;
  return src.slice(at, src.indexOf('\n};', at) + 3);
}

// A DOM of plain objects: enough for the three profile functions, nothing more.
const els = {};
['profFilingStatus', 'profPriorYearTax', 'profPriorYearAgi', 'profAgiOver150k',
 'profRetirementVehicle'].forEach(function (id) { els[id] = { value: '', checked: false }; });
const saved = [];
const ctx = vm.createContext({
  console: console,
  document: { getElementById: function (id) { return els[id] || null; } },
  showToast: function () {},
  window: {
    _fbProfileRef: {},
    _fbSetRaw: function (ref, data) { saved.push(data); return Promise.resolve(); }
  },
  profileCache: {}
});
['TAX_YEAR_2026', 'SAFE_HARBOR_110_AGI_THRESHOLD', 'QBI_CERTAIN_CEILING',
 'QBI_MIN_DEDUCTION', 'QBI_MIN_QBI_FOR_MINIMUM'].forEach(function (c) {
  vm.runInContext(liftConst(c), ctx);
});
['requireFiniteNumber', 'calcSeTax', 'calcAdditionalMedicare', 'bracketTax',
 'calcQbiDeduction', 'calcTotalTax', 'projectAnnualFromYtd',
 'safeHarborAgiThreshold', 'calcQuarterlySetAside', 'populateProfileForm'
].forEach(function (f) { vm.runInContext(lift(f), ctx); });
vm.runInContext(lift('saveProfile', 'async function'), ctx);

const ASOF = new Date('2026-06-30T12:00:00Z');

(async function () {
  console.log('SAIRNCASH -- a typed $0 prior-year tax is an answer, not a blank');

  await test('1. $0 prior-year tax with profit on file: the prior-year leg is $0, so the set-aside is $0 (1040-ES line 12c)', function () {
    const r = ctx.calcQuarterlySetAside(30000, 'single', 0, 50000, ASOF);
    assert.strictEqual(r.priorYearBasis, 0, 'priorYearBasis was ' + r.priorYearBasis
      + ' -- the $0 was read as not provided');
    assert.strictEqual(r.safeHarborBasis, 0, 'safeHarborBasis was ' + r.safeHarborBasis);
    assert.strictEqual(r.quarterlyAmount, 0, 'quarterlyAmount was ' + r.quarterlyAmount);
    assert.strictEqual(r.hasFullBasis, true, 'hasFullBasis was false, so the screen asks '
      + 'for last year\'s tax, which the user already entered');
  });

  await test('2. $0 prior-year tax with NO profit yet: $0, not "nothing to compute"', function () {
    const r = ctx.calcQuarterlySetAside(0, 'single', 0, 50000, ASOF);
    assert.strictEqual(r.quarterlyAmount, 0, 'quarterlyAmount was ' + r.quarterlyAmount
      + ' -- null renders as "Nothing to compute yet -- add last year\'s tax above"');
  });

  await test('3. CONTROL -- null still means not provided', function () {
    const r = ctx.calcQuarterlySetAside(30000, 'single', null, 50000, ASOF);
    assert.strictEqual(r.priorYearBasis, null);
    assert.strictEqual(r.hasFullBasis, false);
    assert.ok(r.quarterlyAmount > 0, 'the 90% leg must still stand alone');
    const r0 = ctx.calcQuarterlySetAside(0, 'single', null, null, ASOF);
    assert.strictEqual(r0.quarterlyAmount, null, 'no profit and no prior year is still unknown');
  });

  await test('4. saveProfile stores a typed 0 as 0, and a blank box as null', async function () {
    els.profFilingStatus.value = 'single';
    els.profRetirementVehicle.value = 'none';
    els.profPriorYearAgi.value = '';
    els.profPriorYearTax.value = '0';
    saved.length = 0;
    await ctx.saveProfile();
    assert.strictEqual(saved.length, 1, 'saveProfile did not write');
    assert.strictEqual(saved[0].prior_year_tax_liability, 0,
      'a typed 0 was stored as ' + JSON.stringify(saved[0].prior_year_tax_liability));
    els.profPriorYearTax.value = '';
    saved.length = 0;
    await ctx.saveProfile();
    assert.strictEqual(saved[0].prior_year_tax_liability, null,
      'a blank box must still store null, got ' + JSON.stringify(saved[0].prior_year_tax_liability));
  });

  await test('5. populateProfileForm shows a stored 0 as "0", not an empty box', function () {
    vm.runInContext('profileCache = { prior_year_tax_liability: 0 };', ctx);
    els.profPriorYearTax.value = 'stale';
    ctx.populateProfileForm();
    assert.strictEqual(String(els.profPriorYearTax.value), '0',
      'a stored 0 was shown as ' + JSON.stringify(els.profPriorYearTax.value));
  });

  await test('6. CONTROL -- a non-zero prior-year tax behaves as before', function () {
    const r = ctx.calcQuarterlySetAside(30000, 'single', 4000, 50000, ASOF);
    assert.strictEqual(r.priorYearBasis, 4000);
    assert.strictEqual(r.hasFullBasis, true);
    assert.ok(r.quarterlyAmount > 0 && r.quarterlyAmount <= 1000);
    els.profPriorYearTax.value = '4000';
    saved.length = 0;
    return ctx.saveProfile().then(function () {
      assert.strictEqual(saved[0].prior_year_tax_liability, 4000);
    });
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
