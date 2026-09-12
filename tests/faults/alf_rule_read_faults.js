// tests/faults/alf_rule_read_faults.js
//
// Run:  node tests/faults/alf_rule_read_faults.js
//
// FAULT INJECTION on the READ half of the transport -- the first suite on this
// platform pointed there, after two days aimed entirely at writes.
//
// ── HOW THIS WAS FOUND, AND THE HYPOTHESIS WAS WRONG FIRST ─────────────────
// Measured: 8 of 15 apps give a read caller NO named way to tell "the read
// failed" from "there is nothing there" -- their transport returns `null` for
// both. That looked like a portfolio-wide defect and it is NOT. Seven of the
// eight are fine, and reading them is what showed it:
//
//   * the hydrators return false on a null and LEAVE THE LOCAL COPY ALONE
//     (sairncare's six, sairnsenior's thirteen, sairnfreedom, sairnvet,
//     sairndesign, sairngrounds, sairnscape) -- the documented fall-back;
//   * the renderers that need the distinction read the RESPONSE SHAPE instead
//     of a flag, and read it carefully. sairnsenior's rCrew() branches on
//     `rows===null` with its own sentence; sairnmechanical's mechCredRefresh()
//     separates 401/403 from not-ok from provisioned:false with three different
//     messages and cites the StoneDesk lesson by name; sairnscape's
//     scpMemoryRead() returns [] deliberately so the caller falls through to the
//     local store.
//
// So the absence of a flag is not the defect. What IS the defect is narrower and
// was found by sweeping for a coalesce whose variable is tested for null
// elsewhere -- a guard that was written and cannot fire. Exactly two instances
// on the platform, both here.
//
// ── THE DEFECT ─────────────────────────────────────────────────────────────
// prRefresh() and cqRefresh() both did:
//
//     _prRules = Array.isArray(rows) ? rows : [];     // null -> []
//
// and their renderers both still test `_prRules === null` to print
// "Coverage: not loaded". The coalesce runs first, so after ANY click of Refresh
// Rules / Load Rules that branch is unreachable and a FAILED READ renders as an
// authoritative empty rule set:
//
//     HCBS coverage: 0 of 4 states routable
//     No billing rules are loaded yet ... run sql/..._schema.sql and load ..._seed.json
//
//     Coverage: 0 of 4 states fully loaded
//     No compliance rules are loaded yet -- run sql/..._schema.sql and load ..._seed.json
//
// A timeout, a 401 without an employee session, a 503, or a 200 carrying
// ok:false all told an assisted-living operator that their state's staffing,
// training and licensure requirements are absent, and told a biller that no
// Medicaid HCBS rules exist -- then sent both to re-run a seed that is very
// probably already loaded. **The remediation advice is the harmful part**, not
// just the count.
//
// The authors' intent is visible in the dead branch and in its wording. This is
// not a missing guard; it is a guard defeated by the line above it.
//
// THREE STATES, because the two existing messages are each right for their own
// case and neither is right for a failure:
//     null + !failed -> never loaded this session  -> "Click Refresh Rules"
//     null +  failed -> the read did not come back -> say so, advise no SQL
//     []             -> the server really has none -> the run-the-SQL advice

'use strict';
const fs = require('fs');
const path = require('path');
const K = require('./faultkit');
const assert = K.assert;

const FILE = 'sairncare.html';
const SRC = fs.readFileSync(path.join(K.ROOT, FILE), 'utf8');

let pass = 0, fail = 0;
const tests = [];
function test(name, fn) { tests.push([name, fn]); }
function section(t) { tests.push([t, null]); }

function grab(sig) {
  const i = SRC.indexOf(sig);
  assert.ok(i > 0, sig + ' not found -- this arm is testing nothing');
  const o = SRC.indexOf('{', i);
  let d = 0, k = o;
  for (; k < SRC.length; k++) {
    if (SRC[k] === '{') d++;
    else if (SRC[k] === '}' && --d === 0) break;
  }
  return SRC.slice(i, k + 1);
}
function line(decl) {
  const i = SRC.indexOf(decl);
  assert.ok(i > 0, decl + ' not found');
  return SRC.slice(i).split(/\r?\n/)[0];
}

// A fake DOM that records what each element was actually given, plus alfData()
// told to fail in each of the four ways the real transport can.
function ctxFor(mode) {
  const els = {};
  ['pr-rules', 'pr-coverage', 'cq-coverage', 'cq-result', 'cq-state', 'cq-class']
    .forEach((id) => { els[id] = { innerHTML: '', textContent: '', options: { length: 1 }, value: 'OH' }; });
  const state = { reads: 0 };
  const ctx = {
    JSON, Object, Array, String, Number, Date, Math, Promise, setTimeout,
    console: { warn: () => {}, error: () => {}, log: () => {} },
    H: (s) => String(s === undefined || s === null ? '' : s),
    $: (id) => els[id] || null,
    document: { getElementById: (id) => els[id] || null },
    ld: () => null,
    facility: () => ({ licensing_state: 'OH' }),
    alfLicenseKey: () => 'ALF-TEST-2026',
    alfData: function () {
      state.reads += 1;
      // Every one of these is what the real alfData() returns for that fault:
      // it ends in a catch that returns null, and its non-ok branch returns null
      // too, so a failure of ANY kind arrives as null.
      if (mode === 'fail') return Promise.resolve(null);
      if (mode === 'empty') return Promise.resolve([]);
      return Promise.resolve(mode);
    },
    __els: els, __state: state,
  };
  K.vm.createContext(ctx);
  K.vm.runInContext(line('var _prRules=null,_prCoverage=null;'), ctx);
  K.vm.runInContext(line("var ALF_CLAIMED_HCBS_STATES=['OH'"), ctx);
  K.vm.runInContext(line('var _prReadFailed=false;'), ctx);
  K.vm.runInContext(line('var _cqRules=null;'), ctx);
  K.vm.runInContext(line("var ALF_COMPLIANCE_STATES=['OH'"), ctx);
  K.vm.runInContext(line('var _cqReadFailed=false;'), ctx);
  K.vm.runInContext('var ALF_FACILITY_CLASSES={OH:[["rcf","RCF"]]};', ctx);
  K.vm.runInContext('function cqPopulateSelectors(){} function cqPopulateClasses(){}', ctx);
  K.vm.runInContext(grab('function rPayerRouting('), ctx);
  K.vm.runInContext(grab('function prRefresh('), ctx);
  K.vm.runInContext(grab('function rJurisdiction('), ctx);
  K.vm.runInContext(grab('function cqRefresh('), ctx);
  return ctx;
}

const RULE = { rule_id: 'R1', state: 'OH', program: 'medicaid_hcbs', status: 'active',
               requirement_type: 'staffing', data: {} };

section('a FAILED payer-rule read does not render as an empty rule set');

test('the coverage line says it could not be read, not 0 of 4', async () => {
  const ctx = ctxFor('fail');
  await ctx.prRefresh();
  const cov = ctx.__els['pr-coverage'].textContent;
  assert.ok(!/0 of \d+ states routable/.test(cov),
    'a failed read is still reporting a coverage COUNT, which reads as a measured '
    + 'fact about the rules: ' + cov);
  assert.ok(/COULD NOT BE READ/.test(cov), cov);
});

test('...and it does NOT advise re-running the SQL', async () => {
  // The harmful half. That advice is correct for a genuinely empty rule set and
  // actively wrong here -- it sends a biller to re-load a seed that is loaded.
  const ctx = ctxFor('fail');
  await ctx.prRefresh();
  const box = ctx.__els['pr-rules'].innerHTML;
  assert.ok(!/run sql\//.test(box),
    'a failed read still tells the operator to run the seed SQL: ' + box);
  assert.ok(/not an empty rule set/i.test(box), box);
});

test('_prRules stays null on a failure, so the guard can still fire', async () => {
  const ctx = ctxFor('fail');
  await ctx.prRefresh();
  assert.strictEqual(ctx._prRules, null,
    'the coalesce to [] is back, and the === null guard below it is dead again');
  assert.strictEqual(ctx._prReadFailed, true);
});

section('and a GENUINELY empty rule set still says exactly what it said before');

test('an empty array keeps the run-the-SQL advice', async () => {
  const ctx = ctxFor('empty');
  await ctx.prRefresh();
  assert.ok(/run sql\/sairncare_payer_rules_schema\.sql/.test(ctx.__els['pr-rules'].innerHTML),
    'the fix removed the advice from the case where it is CORRECT');
  assert.ok(/0 of 4 states routable/.test(ctx.__els['pr-coverage'].textContent),
    'a real zero-coverage state stopped reporting zero');
});

test('and a real rule still renders and counts', async () => {
  const ctx = ctxFor([RULE]);
  await ctx.prRefresh();
  assert.ok(/1 of 4 states routable/.test(ctx.__els['pr-coverage'].textContent),
    ctx.__els['pr-coverage'].textContent);
  assert.ok(/R1/.test(ctx.__els['pr-rules'].innerHTML));
});

test('NEVER LOADED is still its own third state', async () => {
  // Not the same as a failure and not the same as empty. Rendering before any
  // refresh must still invite the click rather than claim anything.
  const ctx = ctxFor('fail');
  ctx.rPayerRouting();                       // no refresh has run
  assert.ok(/not loaded/.test(ctx.__els['pr-coverage'].textContent));
  assert.ok(/Click Refresh Rules/.test(ctx.__els['pr-rules'].innerHTML));
});

section('the compliance panel -- the same defect where the stakes are higher');

test('a failed compliance read does not say 0 of 4 states fully loaded', async () => {
  const ctx = ctxFor('fail');
  await ctx.cqRefresh();
  const cov = ctx.__els['cq-coverage'].textContent;
  assert.ok(!/0 of \d+ states fully loaded/.test(cov),
    'an operator is being told their state requirements are absent: ' + cov);
  assert.ok(/COULD NOT BE READ/.test(cov), cov);
});

test('...and does not tell them to load the compliance seed', async () => {
  const ctx = ctxFor('fail');
  await ctx.cqRefresh();
  const box = ctx.__els['cq-result'].innerHTML;
  assert.ok(!/run sql\//.test(box), box);
  assert.ok(/not an empty rule set/i.test(box), box);
});

test('a genuinely empty compliance set keeps its original wording', async () => {
  const ctx = ctxFor('empty');
  await ctx.cqRefresh();
  assert.ok(/No compliance rules are loaded yet/.test(ctx.__els['cq-result'].innerHTML));
  assert.ok(/run sql\/sairncare_compliance_schema\.sql/.test(ctx.__els['cq-result'].innerHTML));
  assert.ok(/0 of 4 states fully loaded/.test(ctx.__els['cq-coverage'].textContent));
});

test('and a complete state still counts as complete', async () => {
  const full = ['staffing', 'training', 'licensure'].map((t) =>
    ({ rule_id: 'C-' + t, state: 'OH', requirement_type: t, data: {} }));
  const ctx = ctxFor(full);
  await ctx.cqRefresh();
  assert.ok(/1 of 4 states fully loaded/.test(ctx.__els['cq-coverage'].textContent),
    ctx.__els['cq-coverage'].textContent);
});

section('the structural half -- this shape must not come back anywhere');

test('neither cache coalesces a failed read to an empty array', () => {
  const src = SRC.replace(/\/\/[^\n]*/g, '');
  ['_prRules', '_cqRules'].forEach((v) => {
    assert.ok(!new RegExp(v + '\\s*=\\s*Array\\.isArray\\(\\s*rows\\s*\\)\\s*\\?\\s*rows\\s*:\\s*\\[\\s*\\]').test(src),
      v + ' coalesces a failed read to [] again, which makes the `=== null` '
      + 'guard below it dead and renders a failure as an empty rule set');
  });
});

test('and both still HAVE the null guard the coalesce used to defeat', () => {
  const src = SRC.replace(/\/\/[^\n]*/g, '');
  ['_prRules', '_cqRules'].forEach((v) => {
    assert.ok(new RegExp(v + '\\s*===\\s*null').test(src),
      v + ' lost its null guard -- the fix has to keep BOTH halves, or a '
      + 'never-loaded panel starts claiming something');
  });
});

test('the failure flag is set from the SAME test that decides the value', () => {
  // Two separate tests of `rows` could drift apart and produce the fourth,
  // incoherent state: a null cache with failed=false, which renders the
  // click-refresh message after a real failure.
  ['prRefresh', 'cqRefresh'].forEach((fn) => {
    const body = grab('function ' + fn + '(').replace(/\/\/[^\n]*/g, '');
    assert.ok(/ReadFailed\s*=\s*!Array\.isArray\(\s*rows\s*\)/.test(body),
      fn + ' no longer derives its failure flag from Array.isArray(rows)');
    assert.ok(/Rules\s*=\s*Array\.isArray\(\s*rows\s*\)\s*\?\s*rows\s*:\s*null/.test(body),
      fn + ' no longer stores null for a failed read');
  });
});

(async () => {
  for (const [name, fn] of tests) {
    if (fn === null) { console.log('--- ' + name + ' ---'); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
  }
  console.log('\n' + (fail === 0
    ? 'ALL ' + pass + ' SAIRNCARE RULE-READ FAULT ARMS PASS'
    : pass + ' passed, ' + fail + ' FAILED'));
  process.exit(fail === 0 ? 0 : 1);
})();
