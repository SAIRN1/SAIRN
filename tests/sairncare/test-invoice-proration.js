// Isolated test of the invoice-retroactivity fix's core logic in sairncare.html:
// daysInMonth / careHistoryOf / currentCareLevelOf / careLevelLabel / careRateFor /
// careLevelSegmentsForMonth. Extracted VERBATIM by line range from the real file
// (not retyped) and eval'd with a stubbed facility() rate card, same methodology
// used elsewhere in this project for pure client-side logic with no I/O.
'use strict';
const fs = require('fs');
const path = require('path');
const FILE = path.join(__dirname, '..', '..', 'sairncare.html');

const lines = fs.readFileSync(FILE, 'utf8').split('\n');
// Line numbers are 1-indexed in the editor; array is 0-indexed.
function extract(startLine, endLine) {
  return lines.slice(startLine - 1, endLine).join('\n');
}

// Verify the anchors are still what we expect before trusting the extraction -- if either
// function has moved or been renamed, fail loudly instead of silently testing stale/wrong code.
// CRLF-preserved file (project convention) -- strip a trailing \r before matching.
function noCr(s) { return (s || '').replace(/\r$/, ''); }
if (!/^function daysInMonth\(monthStr\)\{$/.test(noCr(lines[1736]))) {
  throw new Error('daysInMonth anchor moved -- re-check the line range in this test file');
}
if (!/^var ALF_LEVEL_LABEL=/.test(noCr(lines[2199]))) {
  throw new Error('ALF_LEVEL_LABEL anchor moved -- re-check the line range in this test file');
}
if (noCr(lines[2225]).trim() !== '}') {
  throw new Error('careRateFor end-of-block anchor moved -- re-check the line range in this test file');
}

const src = extract(1737, 1780) + '\n' + extract(2200, 2226);

let RATE_CARD = { il_rate: 3000, al1_rate: 3600, al2_rate: 4200, al3_rate: 4800, mc_rate: 6000, snf_rate: 7500 };
function facility() { return RATE_CARD; }

const sandbox = { facility };
const vm = require('vm');
vm.createContext(sandbox);
vm.runInContext(src, sandbox);
const { daysInMonth, careHistoryOf, currentCareLevelOf, careLevelLabel, careRateFor, careLevelSegmentsForMonth } = sandbox;

let pass = 0, fail = 0;
function check(name, fn) {
  try { fn(); pass++; console.log('PASS ' + name); }
  catch (e) { fail++; console.log('FAIL ' + name + ' -- ' + e.message); }
}
function assertEq(actual, expected, msg) {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error((msg || 'mismatch') + ': expected ' + JSON.stringify(expected) + ' got ' + JSON.stringify(actual));
  }
}

check('daysInMonth is calendar-accurate, not hardcoded to 30', () => {
  assertEq(daysInMonth('2026-02'), 28);
  assertEq(daysInMonth('2026-01'), 31);
  assertEq(daysInMonth('2026-04'), 30);
  assertEq(daysInMonth('2028-02'), 29, 'leap year');
});

check('careHistoryOf migrates a legacy flat care_level losslessly, honest null date', () => {
  const h = careHistoryOf({ care_level: 'al2' });
  assertEq(h.length, 1);
  assertEq(h[0].level, 'assisted_living');
  assertEq(h[0].sub_tier, 'al2');
  assertEq(h[0].effective_date, null);
  assertEq(h[0].migrated, true);
});

check('careHistoryOf prefers a real history array over the legacy flat field', () => {
  const real = [{ level: 'memory_care', sub_tier: null, effective_date: '2026-01-01' }];
  const h = careHistoryOf({ care_level: 'al2', care_level_history: real });
  assertEq(h, real);
});

check('currentCareLevelOf returns the LAST entry, not the first', () => {
  const r = { care_level_history: [
    { level: 'assisted_living', sub_tier: 'al1', effective_date: '2026-01-01' },
    { level: 'memory_care', sub_tier: null, effective_date: '2026-06-01' }
  ] };
  assertEq(currentCareLevelOf(r).level, 'memory_care');
});

check('careLevelLabel shows the sub-tier label for assisted_living, the plain level otherwise', () => {
  assertEq(careLevelLabel({ level: 'assisted_living', sub_tier: 'al2' }), 'AL2 - Moderate Assistance');
  assertEq(careLevelLabel({ level: 'memory_care' }), 'Memory Care');
  assertEq(careLevelLabel(null), '--');
});

check('careRateFor reads the correct facility rate field per level/sub_tier', () => {
  assertEq(careRateFor('independent_living'), 3000);
  assertEq(careRateFor('assisted_living', 'al1'), 3600);
  assertEq(careRateFor('assisted_living', 'al3'), 4800);
  assertEq(careRateFor('memory_care'), 6000);
  assertEq(careRateFor('skilled_nursing'), 7500);
});

check('a resident with no history at all gets zero segments (nothing to bill)', () => {
  assertEq(careLevelSegmentsForMonth({}, '2026-08'), []);
});

check('a single migrated legacy entry (no effective_date) covers the WHOLE month as one segment', () => {
  const segs = careLevelSegmentsForMonth({ care_level: 'al2' }, '2026-04'); // 30 days
  assertEq(segs.length, 1);
  assertEq(segs[0].level, 'assisted_living');
  assertEq(segs[0].sub_tier, 'al2');
  assertEq(segs[0].days, 30);
  assertEq(segs[0].amount, 4200);
});

// THE CORE FIX: a mid-month level change must prorate, not silently re-bill the whole month at
// whichever level happens to be current. April has 30 days: AL1 the first 14 days (1st-14th),
// AL2 the remaining 16 days (15th-30th).
check('a mid-month level change prorates by real days-in-effect, not the whole month', () => {
  const r = { care_level_history: [
    { level: 'assisted_living', sub_tier: 'al1', effective_date: '2026-03-01' },
    { level: 'assisted_living', sub_tier: 'al2', effective_date: '2026-04-15' }
  ] };
  const segs = careLevelSegmentsForMonth(r, '2026-04');
  assertEq(segs.length, 2);
  assertEq(segs[0].sub_tier, 'al1'); assertEq(segs[0].days, 14);
  assertEq(segs[1].sub_tier, 'al2'); assertEq(segs[1].days, 16);
  const al1Expected = Math.round((3600 / 30) * 14 * 100) / 100;
  const al2Expected = Math.round((4200 / 30) * 16 * 100) / 100;
  assertEq(segs[0].amount, al1Expected);
  assertEq(segs[1].amount, al2Expected);
  const total = Math.round((segs[0].amount + segs[1].amount) * 100) / 100;
  // Sanity: the prorated total must land strictly between one full month at either rate --
  // proof this is real proration, not silently defaulting to either the old or new level.
  if (!(total > 3600 && total < 4200)) throw new Error('prorated total ' + total + ' is not between the two monthly rates');
});

check('a level that starts LATER in the month is not billed for days before it began', () => {
  const r = { care_level_history: [
    { level: 'skilled_nursing', sub_tier: null, effective_date: '2026-08-20' }
  ] };
  const segs = careLevelSegmentsForMonth(r, '2026-08'); // 31 days, level starts on the 20th
  assertEq(segs.length, 1);
  assertEq(segs[0].days, 12); // 20th through 31st inclusive
});

check('three levels in one month produce three correctly-ordered, correctly-sized segments', () => {
  const r = { care_level_history: [
    { level: 'independent_living', sub_tier: null, effective_date: '2026-06-01' },
    { level: 'assisted_living', sub_tier: 'al2', effective_date: '2026-06-11' },
    { level: 'memory_care', sub_tier: null, effective_date: '2026-06-21' }
  ] };
  const segs = careLevelSegmentsForMonth(r, '2026-06'); // 30 days
  assertEq(segs.map((s) => s.level), ['independent_living', 'assisted_living', 'memory_care']);
  assertEq(segs.map((s) => s.days), [10, 10, 10]);
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
