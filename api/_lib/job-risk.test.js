// api/_lib/job-risk.test.js
//
// Run:  node api/_lib/job-risk.test.js
//
// The claim under test is NOT "does the arithmetic add up". It is:
//   1. a missing lead time produces UNKNOWN, never a default and never "ok";
//   2. thin history produces UNKNOWN, never an invented stage duration;
//   3. quoted and observed are never blended, and the caller is told which won;
//   4. the flag and the slack number agree, and both are reported.
//
// Every fixture below is invented TEST data, which is fine. What must never
// exist is invented PRODUCT data -- a default lead time or a default stage
// duration shipped in the engine. The first test asserts that directly.

'use strict';
const assert = require('assert');
const R = require('./job-risk');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); pass++; console.log('  ok   ' + name); }
  catch (e) { fail++; console.log('  FAIL ' + name + '\n       ' + e.message); }
}

const TODAY = '2026-09-02';
// Three completed jobs, 30 / 40 / 50 days -> median 40.
const HISTORY = [
  { id: 'a', stage: 'installed', templateDate: '2026-06-01', installedAt: '2026-07-01' },
  { id: 'b', stage: 'installed', templateDate: '2026-06-01', installedAt: '2026-07-11' },
  { id: 'c', stage: 'installed', templateDate: '2026-06-01', installedAt: '2026-07-21' }
];
const LEAD = [
  { supplier: 'msi', material: 'quartzite', quoted_days: 21, observed_n: 0, observed_total_days: 0 },
  { supplier: 'msi', material: 'granite', quoted_days: 14, observed_n: 4, observed_total_days: 124,
    observed_min_days: 25, observed_max_days: 38 }
];
const SLABS = [
  { id: 'S1', material: 'granite', status: 'in-stock', usableSqft: 60 },
  { id: 'S2', material: 'marble', status: 'sold', usableSqft: 90 }
];
function ctx(over) {
  return Object.assign({ today: TODAY, jobs: HISTORY, slabs: SLABS, leadTimes: LEAD }, over || {});
}

console.log('--- NO DEFAULTS ARE SHIPPED ---');
test('the engine source contains no default lead time or stage duration', function () {
  const src = require('fs').readFileSync(require('path').join(__dirname, 'job-risk.js'), 'utf8');
  // A default would have to appear as a fallback on a null lead time or an
  // empty history. Assert the two shapes that would betray one.
  assert.ok(!/lead[_A-Za-z]*\s*\|\|\s*\d/.test(src), 'a "lead || <number>" fallback exists');
  assert.ok(!/DEFAULT_(LEAD|STAGE|DAYS)/.test(src), 'a DEFAULT_* constant exists');
});
test('unknown lead time -> risk unknown, NOT ok, and says why', function () {
  const j = { id: 'j1', material: 'soapstone', supplier: 'msi', sqft: 40, stage: 'templated', targetDate: '2026-12-01' };
  const r = R.assessJob(j, ctx());
  assert.strictEqual(r.risk, 'unknown', JSON.stringify(r));
  assert.ok(/no lead time recorded for soapstone from msi/.test(r.reasons.join(' ')), r.reasons.join(' '));
  assert.strictEqual(r.projected_completion, undefined);
});
test('empty lead-time table -> unknown for every procured job', function () {
  const j = { id: 'j2', material: 'granite', supplier: 'msi', sqft: 999, stage: 'templated', targetDate: '2026-12-01' };
  const r = R.assessJob(j, ctx({ leadTimes: [] }));
  assert.strictEqual(r.risk, 'unknown');
});
test('thin history -> unknown, no invented production time', function () {
  const j = { id: 'j3', material: 'granite', sqft: 40, stage: 'templated', targetDate: '2026-12-01' };
  const r = R.assessJob(j, ctx({ jobs: HISTORY.slice(0, 2) }));
  assert.strictEqual(r.risk, 'unknown');
  assert.ok(/completed job\(s\)/.test(r.reasons.join(' ')), r.reasons.join(' '));
});

console.log('--- quoted vs observed are never blended ---');
test('4 observations outrank the quote, and say so', function () {
  const lt = R.leadTime(LEAD, 'MSI', 'Granite');
  assert.strictEqual(lt.source, 'observed');
  assert.strictEqual(lt.days, 31);              // 124/4
  assert.strictEqual(lt.quoted_days, 14);       // still reported, not merged
  assert.deepStrictEqual(lt.spread, [25, 38]);
});
test('too few observations -> the quote wins and the count is disclosed', function () {
  const rows = [{ supplier: 'msi', material: 'quartz', quoted_days: 10, observed_n: 2, observed_total_days: 60 }];
  const lt = R.leadTime(rows, 'msi', 'quartz');
  assert.strictEqual(lt.source, 'quoted');
  assert.strictEqual(lt.days, 10);
  assert.ok(/2 observation/.test(lt.note), lt.note);
});
test('a row with neither quote nor enough observations is unknown', function () {
  const rows = [{ supplier: 'msi', material: 'onyx', quoted_days: null, observed_n: 1, observed_total_days: 9 }];
  assert.strictEqual(R.leadTime(rows, 'msi', 'onyx').days, null);
});
test('supplier and material are matched case- and space-insensitively', function () {
  assert.strictEqual(R.leadTime(LEAD, '  MSI ', ' GRANITE ').days, 31);
});

console.log('--- slab in hand short-circuits procurement ---');
test('a matching in-stock slab means no lead time is needed at all', function () {
  const j = { id: 'j4', material: 'granite', sqft: 50, stage: 'polishing', targetDate: '2026-12-01' };
  const r = R.assessJob(j, ctx({ leadTimes: [] }));   // empty table on purpose
  assert.strictEqual(r.slab.inHand, true);
  assert.strictEqual(r.slab.via, 'matched');
  assert.strictEqual(r.risk, 'ok', JSON.stringify(r));
});
test('a slab too small does not count', function () {
  const j = { id: 'j5', material: 'granite', sqft: 100, stage: 'templated', targetDate: '2026-12-01' };
  assert.strictEqual(R.assessJob(j, ctx()).slab.inHand, false);
});
test('a sold slab does not count', function () {
  const j = { id: 'j6', material: 'marble', sqft: 10, stage: 'templated', targetDate: '2026-12-01' };
  assert.strictEqual(R.assessJob(j, ctx()).slab.inHand, false);
});
test('a reservation pointing at a missing slab is reported, not silently ignored', function () {
  const j = { id: 'j7', material: 'granite', sqft: 10, reservedSlabId: 'GONE', stage: 'templated', targetDate: '2026-12-01' };
  const r = R.assessJob(j, ctx());
  assert.strictEqual(r.slab.via, 'reserved-but-missing');
  assert.ok(/not in inventory/.test(r.slab.note));
});

console.log('--- the flag and the number agree ---');
test('a comfortable date is ok and carries positive slack', function () {
  const j = { id: 'j8', material: 'granite', sqft: 50, stage: 'templated', targetDate: '2026-12-01' };
  const r = R.assessJob(j, ctx());
  assert.strictEqual(r.risk, 'ok');
  assert.ok(r.slack_days > R.TIGHT_DAYS, JSON.stringify(r));
});
test('a date inside the pipeline is at_risk and slack is negative', function () {
  const j = { id: 'j9', material: 'granite', sqft: 50, stage: 'templated', targetDate: '2026-09-10' };
  const r = R.assessJob(j, ctx());
  assert.strictEqual(r.risk, 'at_risk');
  assert.ok(r.slack_days < 0, JSON.stringify(r));
});
test('at_risk reports HOW LATE, not just that it is late', function () {
  const a = R.assessJob({ id: 'a', material: 'granite', sqft: 50, stage: 'templated', targetDate: '2026-09-10' }, ctx());
  const b = R.assessJob({ id: 'b', material: 'granite', sqft: 50, stage: 'templated', targetDate: '2026-08-01' }, ctx());
  assert.strictEqual(a.risk, 'at_risk');
  assert.strictEqual(b.risk, 'at_risk');
  assert.ok(b.slack_days < a.slack_days, 'both at_risk but the worse one is not distinguishable');
});
test('procurement pushes the projection out by exactly the lead time', function () {
  const inHand = R.assessJob({ id: 'p1', material: 'granite', sqft: 50, stage: 'templated', targetDate: '2026-12-01' }, ctx());
  const needed = R.assessJob({ id: 'p2', material: 'granite', supplier: 'msi', sqft: 999, stage: 'templated', targetDate: '2026-12-01' }, ctx());
  assert.strictEqual(inHand.slack_days - needed.slack_days, 31, 'expected the 31-day observed lead time');
});

console.log('--- states that are not risk ---');
test('no target date is "unscheduled", not "ok"', function () {
  const r = R.assessJob({ id: 'u', material: 'granite', sqft: 10, stage: 'templated' }, ctx());
  assert.strictEqual(r.risk, 'unscheduled');
});
test('an installed job is "done"', function () {
  const r = R.assessJob({ id: 'd', material: 'granite', stage: 'installed', targetDate: '2026-09-01' }, ctx());
  assert.strictEqual(r.risk, 'done');
});
test('an unrecognised stage is unknown, not assumed to be the first one', function () {
  const r = R.assessJob({ id: 'x', material: 'granite', sqft: 10, stage: 'sandblasting', targetDate: '2026-12-01' }, ctx());
  assert.strictEqual(r.risk, 'unknown');
  assert.ok(/unrecognised stage/.test(r.reasons.join(' ')));
});
test('later stages have less remaining work than earlier ones', function () {
  const early = R.assessJob({ id: 'e', material: 'granite', sqft: 50, stage: 'templated', targetDate: '2026-12-01' }, ctx());
  const late = R.assessJob({ id: 'l', material: 'granite', sqft: 50, stage: 'ready', targetDate: '2026-12-01' }, ctx());
  assert.ok(late.remaining_production_days < early.remaining_production_days,
    early.remaining_production_days + ' vs ' + late.remaining_production_days);
});

console.log('--- observing a real receipt ---');
test('a receipt folds in and moves the average', function () {
  let row = { supplier: 'msi', material: 'quartz', quoted_days: 10, observed_total_days: 0, observed_n: 0 };
  const r1 = R.observeReceipt(row, '2026-08-01', '2026-08-21');
  assert.strictEqual(r1.applied, true);
  assert.strictEqual(r1.days, 20);
  assert.strictEqual(r1.row.observed_n, 1);
  assert.strictEqual(r1.row.observed_min_days, 20);
});
test('a receipt before its order is refused, not recorded as negative', function () {
  const r = R.observeReceipt({ observed_total_days: 0, observed_n: 0 }, '2026-08-21', '2026-08-01');
  assert.strictEqual(r.applied, false);
  assert.ok(/before it was ordered/.test(r.reason));
});
test('a missing order date is refused -- this is why orderedAt had to be added', function () {
  const r = R.observeReceipt({ observed_total_days: 0, observed_n: 0 }, null, '2026-08-01');
  assert.strictEqual(r.applied, false);
});
test('three receipts flip the source from quoted to observed', function () {
  let row = { supplier: 'msi', material: 'quartz', quoted_days: 10, observed_total_days: 0, observed_n: 0 };
  ['2026-08-21', '2026-08-22', '2026-08-23'].forEach(function (d) {
    row = R.observeReceipt(row, '2026-08-01', d).row;
  });
  row.supplier = 'msi'; row.material = 'quartz';
  const lt = R.leadTime([row], 'msi', 'quartz');
  assert.strictEqual(lt.source, 'observed');
  assert.strictEqual(lt.quoted_days, 10);
});

console.log('');
console.log(fail ? 'FAILURES: ' + fail + ' (passed ' + pass + ')' : 'ALL ' + pass + ' JOB-RISK ASSERTIONS PASS');
process.exit(fail ? 1 : 0);
