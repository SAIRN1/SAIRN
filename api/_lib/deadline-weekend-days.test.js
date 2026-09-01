// Per-jurisdiction weekend days -- isolated verification against the REAL
// engine.
//
// WHY THIS FILE EXISTS AND WHY A GREEN REGRESSION BAR IS NOT THE TEST.
// `weekend_days` defaults to [Sunday, Saturday], so every one of the seeded
// jurisdictions' suites passes whether the flag works or is a no-op stub.
// That green bar is precisely the false signal that would let a broken flag
// ship, and the open-work row that commissioned this change said so before a
// line of it was written. So this file does two things nothing else does:
//
//   1. It exercises a NON-DEFAULT weekend set through every path that
//      consults one, using the Louisiana shape the change was built for --
//      La. C.C.P. art. 5059(A) rolls the last day only "unless it is a legal
//      holiday" and never names a weekend day in its own right, while
//      La. R.S. 1:55(A)(1) makes SUNDAYS a statewide legal holiday and
//      Saturdays one only in Orleans, the city of Baton Rouge, the 2nd and
//      6th congressional districts except Ascension, and the 14th and 31st
//      judicial districts. A deadline landing on a Saturday in the rest of
//      the state does NOT roll, and rolling it reports LATE -- the direction
//      that misses a filing.
//
//   2. It AUDITS THE ENGINE SOURCE so a call site cannot be missed. Every
//      isWeekend / rollOff / countExcludingWeekendsAndHolidays call must pass
//      a weekend-days argument. A dynamic test can only cover the paths it
//      reaches; this covers the ones it does not.
//
// NO LOUISIANA ROWS ARE SEEDED AND NONE ARE IMPLIED BY THIS FILE. The parish
// scoping question is open and is a separate decision -- a statewide `la`
// with weekend_days [Sun] is correct for the majority of parishes and LATE
// for the enumerated ones. The standard used below is a TEST fixture, named
// as one, and registered only for the duration of this run.

const engine = require('./deadline-engine.js');

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

// ── Fixtures ──────────────────────────────────────────────────────────────
// 2026 dates used throughout, chosen so the day of the week is unambiguous:
//   2026-07-03 Friday   2026-07-04 Saturday   2026-07-05 Sunday
//   2026-07-06 Monday   2026-07-10 Friday     2026-07-11 Saturday
const FRI = '2026-07-03', SAT = '2026-07-04', SUN = '2026-07-05', MON = '2026-07-06';

// A calendar with ONE real holiday, so a "does it still roll off holidays"
// assertion is possible independently of the weekend question.
// Calendar entries are OBJECTS carrying date/name/kind, not bare strings --
// holidayFor reads `.date` and consults `.kind` for the FRCP 6(a)(6)
// state-holiday rule. A bare-string fixture reads as "no holidays at all"
// with no error, which is exactly the shape that would make the
// holiday-still-rolls assertions below pass vacuously.
const HOLIDAY = '2026-12-25'; // Friday
const calendars = { zz: { 2026: [{ date: HOLIDAY, name: 'Christmas Day', kind: 'declared' }] } };

check('the fixture dates are the days of the week this file assumes',
  [FRI, SAT, SUN, MON].map(engine.dayOfWeek), [5, 6, 0, 1]);

// ── 1. weekendDaysDefect ──────────────────────────────────────────────────
check('undeclared weekend_days is valid -- the default applies', engine.weekendDaysDefect(undefined), null);
check('null weekend_days is valid', engine.weekendDaysDefect(null), null);
check('[0,6] is valid', engine.weekendDaysDefect([0, 6]), null);
check('[0] is valid', engine.weekendDaysDefect([0]), null);
check('a non-array is a defect', engine.weekendDaysDefect(6) !== null, true);
check('a string is a defect', engine.weekendDaysDefect('0,6') !== null, true);
check('an empty array is a defect, not "no weekend days"', engine.weekendDaysDefect([]) !== null, true);
check('a day number above 6 is a defect', engine.weekendDaysDefect([7]) !== null, true);
check('a negative day number is a defect', engine.weekendDaysDefect([-1]) !== null, true);
check('a non-integer day number is a defect', engine.weekendDaysDefect([0.5]) !== null, true);
check('a string element is a defect', engine.weekendDaysDefect(['0']) !== null, true);
check('one bad element among good ones is still a defect', engine.weekendDaysDefect([0, 9]) !== null, true);

// ── 2. isWeekend ──────────────────────────────────────────────────────────
check('default: Saturday is a weekend day', engine.isWeekend(SAT), true);
check('default: Sunday is a weekend day', engine.isWeekend(SUN), true);
check('default: Friday is not', engine.isWeekend(FRI), false);
check('Sunday-only: Saturday is NOT a weekend day', engine.isWeekend(SAT, [0]), false);
check('Sunday-only: Sunday still is', engine.isWeekend(SUN, [0]), true);
check('Saturday-only: Sunday is not', engine.isWeekend(SUN, [6]), false);
check('an arbitrary set is honoured -- Monday', engine.isWeekend(MON, [1]), true);
check('DEFAULT_WEEKEND_DAYS is Sunday and Saturday', engine.DEFAULT_WEEKEND_DAYS, [0, 6]);
check('a non-array argument falls back to the default rather than matching nothing',
  engine.isWeekend(SAT, 'nonsense'), true);

// ── 3. rollOff ────────────────────────────────────────────────────────────
const roll = (d, dir, wd) => {
  const r = engine.rollOff(d, calendars, 'zz', dir, wd);
  return r.ok ? r.date : 'REFUSED:' + r.code;
};
check('default forward: Saturday rolls to Monday', roll(SAT, 'forward'), MON);
check('SUNDAY-ONLY FORWARD: SATURDAY DOES NOT ROLL -- the Louisiana case',
  roll(SAT, 'forward', [0]), SAT);
check('Sunday-only forward: Sunday still rolls to Monday', roll(SUN, 'forward', [0]), MON);
check('default backward: Saturday rolls back to Friday', roll(SAT, 'backward'), FRI);
check('SUNDAY-ONLY BACKWARD: Saturday does not roll', roll(SAT, 'backward', [0]), SAT);
check('Sunday-only backward: Sunday rolls back to Saturday, which is now an ordinary day',
  roll(SUN, 'backward', [0]), SAT);
check('a holiday still rolls under a narrowed weekend set',
  roll(HOLIDAY, 'forward', [0]) !== HOLIDAY, true);
check('narrowing the weekend set does not disable holiday rollover at all',
  roll(HOLIDAY, 'forward', [0]), '2026-12-26');

// ── 4. countExcludingWeekendsAndHolidays ──────────────────────────────────
const countEx = (from, n, wd) => {
  const r = engine.countExcludingWeekendsAndHolidays(from, 1, n, calendars, 'zz', 'forward', wd);
  return r.ok ? r.date : 'REFUSED:' + r.code;
};
// From Friday 3 July, counting 2 days.
//   default   -> skips Sat and Sun, lands Mon 6th then Tue 7th
//   [Sun]     -> Saturday counts, so day 1 is Sat 4th, day 2 is Mon 6th
check('default: two excluded-count days from Friday lands on Tuesday', countEx(FRI, 2), '2026-07-07');
check('SUNDAY-ONLY: the same two days land on Monday because Saturday counts',
  countEx(FRI, 2, [0]), MON);
check('Sunday-only: one day from Friday is the Saturday itself', countEx(FRI, 1, [0]), SAT);
check('default: one day from Friday skips to Monday', countEx(FRI, 1), MON);

// ── 5. End to end, through computeDeadline ────────────────────────────────
// A test-only standard registered on the real table. Named so it cannot be
// mistaken for a shipped jurisdiction, and removed in the finally block.
const STD_KEY = 'test_weekend_sun_only';
const STD_KEY_SHIFT = 'test_weekend_sun_only_shifted';
const STD_KEY_SHORT = 'test_weekend_sun_only_short';
const before = Object.keys(engine.COMPUTATION_STANDARDS).length;
engine.COMPUTATION_STANDARDS[STD_KEY] = {
  label: 'TEST La. C.C.P. art. 5059 shape', impl: 'frcp_6a', weekend_days: [0],
  base_period_suffix: '', months_years_suffix: '', rollover_suffix_forward: '', rollover_suffix_backward: ''
};
engine.COMPUTATION_STANDARDS[STD_KEY_SHIFT] = {
  label: 'TEST shifted-start, Sunday-only', impl: 'frcp_6a', weekend_days: [0], shifted_start: true,
  base_period_suffix: '', months_years_suffix: '', rollover_suffix_forward: '', rollover_suffix_backward: ''
};
engine.COMPUTATION_STANDARDS[STD_KEY_SHORT] = {
  label: 'TEST short-period exclusion, Sunday-only', impl: 'frcp_6a', weekend_days: [0],
  short_period_exclusion_days: 7,
  base_period_suffix: '', months_years_suffix: '', rollover_suffix_forward: '', rollover_suffix_backward: ''
};
// The same three shapes with the default weekend set, so every assertion below
// is a CONTRAST and not just an absolute value that could be right by accident.
['', '_shift', '_short'].forEach((sfx, i) => {
  const src = [STD_KEY, STD_KEY_SHIFT, STD_KEY_SHORT][i];
  const copy = Object.assign({}, engine.COMPUTATION_STANDARDS[src]);
  delete copy.weekend_days;
  copy.label = copy.label + ' (default weekend)';
  engine.COMPUTATION_STANDARDS['test_weekend_default' + sfx] = copy;
});

function ruleFor(std, count, unit, direction) {
  return [{
    rule_id: 'zz-test-' + std + '-' + count + '-' + unit,
    jurisdiction: 'zz', domain: 'civil-litigation',
    label: 'test rule', trigger_event: 'trigger', computation: std,
    count: { value: count, unit: unit || 'calendar_days', direction: direction || 'forward' },
    authority: { citation: 'TEST', url: null, quote: null, note: null, retrieved_at: null },
    effective_from: '2000-01-01', effective_to: null
  }];
}
function compute(std, triggerDate, count, unit, direction) {
  const rules = ruleFor(std, count, unit, direction);
  const r = engine.computeDeadline({
    jurisdiction: 'zz', domain: 'civil-litigation', trigger_event: 'trigger',
    trigger_date: triggerDate, rules: rules, calendars: calendars, as_of: triggerDate
  });
  return r.ok ? r.due_date : 'REFUSED:' + r.code + (r.message ? ' ' + r.message.slice(0, 90) : '');
}

try {
  // (a) Base period whose last day lands on Saturday 4 July.
  //     Wednesday 1 July + 3 calendar days = Saturday 4 July.
  check('END TO END default: a period landing on Saturday rolls to Monday',
    compute('test_weekend_default', '2026-07-01', 3), MON);
  check('END TO END Sunday-only: THE SAME PERIOD STOPS ON THE SATURDAY',
    compute(STD_KEY, '2026-07-01', 3), SAT);

  // (b) Landing on Sunday still rolls -- this is a narrowing, not a disabling.
  check('END TO END Sunday-only: a period landing on Sunday still rolls to Monday',
    compute(STD_KEY, '2026-07-01', 4), MON);
  check('END TO END default: the same period also rolls to Monday',
    compute('test_weekend_default', '2026-07-01', 4), MON);

  // (c) Backward period landing on Saturday.
  check('END TO END default backward: rolls back to Friday',
    compute('test_weekend_default', '2026-07-07', 3, 'calendar_days', 'backward'), FRI);
  check('END TO END Sunday-only backward: stops on the Saturday',
    compute(STD_KEY, '2026-07-07', 3, 'calendar_days', 'backward'), SAT);

  // (d) shifted_start -- the count BEGINS on the next good day.
  //     Trigger Friday 3 July: default skips Sat+Sun and begins Monday;
  //     Sunday-only begins on the Saturday.
  check('END TO END default shifted start: counting begins Monday',
    compute('test_weekend_default_shift', FRI, 1), MON);
  check('END TO END Sunday-only shifted start: counting begins on the Saturday',
    compute(STD_KEY_SHIFT, FRI, 1), SAT);

  // (e) Short-period exclusion -- a period under the threshold skips weekend
  //     days while counting. Two days from Friday.
  check('END TO END default short period: two days from Friday is Tuesday',
    compute('test_weekend_default_short', FRI, 2), '2026-07-07');
  check('END TO END Sunday-only short period: two days from Friday is Monday',
    compute(STD_KEY_SHORT, FRI, 2), MON);

  // (f) business_days unit, which uses its own loop.
  check('END TO END default business days: two from Friday is Tuesday',
    compute('test_weekend_default', FRI, 2, 'business_days'), '2026-07-07');
  check('END TO END Sunday-only business days: two from Friday is Monday',
    compute(STD_KEY, FRI, 2, 'business_days'), MON);

  // (g) A holiday still governs regardless of the weekend set.
  //     Christmas Day 2026 is Friday 25 December; +0 lands on it.
  check('END TO END Sunday-only: a period landing on a holiday still rolls',
    compute(STD_KEY, '2026-12-24', 1), '2026-12-26');
} finally {
  [STD_KEY, STD_KEY_SHIFT, STD_KEY_SHORT,
   'test_weekend_default', 'test_weekend_default_shift', 'test_weekend_default_short']
    .forEach(k => { delete engine.COMPUTATION_STANDARDS[k]; });
}
check('the test standards were removed from the shared table',
  Object.keys(engine.COMPUTATION_STANDARDS).length, before);

// ── 6. Source audit -- no call site may be missed ─────────────────────────
// A dynamic test only covers the paths it reaches. This covers the ones it
// does not, and it is the assertion that fails if a future call site is added
// without threading the flag.
const fs = require('fs');
const path = require('path');
const src = fs.readFileSync(path.join(__dirname, 'deadline-engine.js'), 'utf8');
// Strip line comments so prose mentioning isWeekend() is not audited as code.
const code = src.split('\n').filter(l => !l.trim().startsWith('//')).join('\n');

function callSites(fnName) {
  const out = [];
  const re = new RegExp('(?<!function\\s)\\b' + fnName + '\\s*\\(', 'g');
  let m;
  while ((m = re.exec(code)) !== null) {
    // Capture the argument list, balancing parentheses.
    let i = m.index + m[0].length, depth = 1, args = '';
    while (i < code.length && depth > 0) {
      const ch = code[i];
      if (ch === '(') depth++;
      else if (ch === ')') depth--;
      if (depth > 0) args += ch;
      i++;
    }
    out.push(args);
  }
  return out;
}
function topLevelArgs(args) {
  const parts = []; let depth = 0, cur = '';
  for (const ch of args) {
    if (ch === '(' || ch === '[' || ch === '{') depth++;
    if (ch === ')' || ch === ']' || ch === '}') depth--;
    if (ch === ',' && depth === 0) { parts.push(cur.trim()); cur = ''; continue; }
    cur += ch;
  }
  if (cur.trim()) parts.push(cur.trim());
  return parts;
}

const isWeekendCalls = callSites('isWeekend');
check('every isWeekend call site passes a weekend-days argument',
  isWeekendCalls.filter(a => topLevelArgs(a).length < 2), []);
check('isWeekend has more than one call site, so the audit is not vacuous',
  isWeekendCalls.length >= 4, true);

const rollOffCalls = callSites('rollOff');
check('every rollOff call site passes a weekend-days argument',
  rollOffCalls.filter(a => topLevelArgs(a).length < 5), []);
check('rollOff has more than one call site, so the audit is not vacuous',
  rollOffCalls.length >= 4, true);

const countExCalls = callSites('countExcludingWeekendsAndHolidays');
check('every countExcludingWeekendsAndHolidays call site passes a weekend-days argument',
  countExCalls.filter(a => topLevelArgs(a).length < 7), []);
check('countExcludingWeekendsAndHolidays has a call site, so the audit is not vacuous',
  countExCalls.length >= 1, true);

// ── 7. The shipped table is unchanged by this feature ─────────────────────
const declaring = Object.keys(engine.COMPUTATION_STANDARDS)
  .filter(k => engine.COMPUTATION_STANDARDS[k].weekend_days !== undefined);
check('NO SHIPPED STANDARD DECLARES weekend_days -- every seeded jurisdiction still uses [Sun, Sat]',
  declaring, []);
check('every shipped standard passes the declaration validator',
  Object.keys(engine.COMPUTATION_STANDARDS)
    .filter(k => engine.weekendDaysDefect(engine.COMPUTATION_STANDARDS[k].weekend_days) !== null), []);

console.log('\ndeadline-weekend-days: ' + pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
