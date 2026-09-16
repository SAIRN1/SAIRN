// api/_lib/calendar-date.test.js
// REQUIREMENT: one module owns what a calendar date is and how two compare, so no app
//   reimplements date arithmetic and reaches a different answer about the
//   same two days
//
//
// Run:  node api/_lib/calendar-date.test.js
//
// Item 94's deep module for calendar dates, and the bug all fourteen copies of
// the old helper shared.
//
// THE ARM THAT MATTERS IS THE ROLLOVER. `isDate('2026-02-31')` returned TRUE in
// every one of the fourteen, and JavaScript does not reject an impossible date
// -- it SILENTLY REPAIRS IT into a different, real, plausible one three days
// later. On a credential expiry or a legal deadline that is not an error
// anybody sees; it is a wrong answer produced by a validator that said yes.
//
// AND THE TRAP IS THAT THE OBVIOUS TEST PASSES. '2026-13-99' does become
// Invalid Date, so anybody spot-checking the old guard with garbage would
// conclude it worked. The nearly-right input is the one that fails silently.

'use strict';
const assert = require('assert');
const C = require('./calendar-date.js');

let pass = 0, fail = 0;
const queue = [];
function t(name, fn) { queue.push([name, fn]); }
function section(s) { queue.push([s, null]); }

// The exact body that was copied fourteen times, kept here so the arms below
// compare against the REAL old behaviour rather than a description of it.
function oldIsDate(s) {
  return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s);
}

section('1. the bug all fourteen copies shared');
t('the OLD helper accepts 2026-02-31', () => {
  assert.strictEqual(oldIsDate('2026-02-31'), true);
});
t('...and JavaScript turns it into 2026-03-03 rather than refusing', () => {
  assert.strictEqual(new Date('2026-02-31T00:00:00Z').toISOString().slice(0, 10), '2026-03-03');
});
t('THE NEW ONE REJECTS IT', () => {
  assert.strictEqual(C.isCalendarDate('2026-02-31'), false);
});
t('2026 is not a leap year, so 2026-02-29 is rejected', () => {
  assert.strictEqual(oldIsDate('2026-02-29'), true);
  assert.strictEqual(C.isCalendarDate('2026-02-29'), false);
});
t('...but 2024-02-29 IS a real date and is accepted -- the pair', () => {
  assert.strictEqual(C.isCalendarDate('2024-02-29'), true);
});
t('April has 30 days', () => {
  assert.strictEqual(C.isCalendarDate('2026-04-31'), false);
  assert.strictEqual(C.isCalendarDate('2026-04-30'), true);
});
t('THE TRAP: obvious garbage failed loudly in the old one too', () => {
  // Which is why nobody found the real gap by spot-checking.
  assert.ok(isNaN(new Date('2026-13-99T00:00:00Z').getTime()));
  assert.strictEqual(C.isCalendarDate('2026-13-99'), false);
});
t('a non-string is not a date', () => {
  for (const v of [null, undefined, 20260914, {}, ['2026-09-14']]) {
    assert.strictEqual(C.isCalendarDate(v), false, String(v));
  }
});
t('a datetime is not a CALENDAR date -- the shape is exact', () => {
  assert.strictEqual(C.isCalendarDate('2026-09-14T00:00:00Z'), false);
  assert.strictEqual(C.isCalendarDate('2026-9-14'), false);
});

section('2. comparison returns a THIRD state, never a wrong answer');
t('a real ordering', () => {
  assert.strictEqual(C.compare('2026-01-02', '2026-01-10'), -1);
  assert.strictEqual(C.compare('2026-01-10', '2026-01-02'), 1);
  assert.strictEqual(C.compare('2026-01-02', '2026-01-02'), 0);
});
t('A BAD INPUT IS null, NOT 0 -- 0 would read as "equal"', () => {
  assert.strictEqual(C.compare('2026-02-31', '2026-01-02'), null);
  assert.strictEqual(C.compare('2026-01-02', 'tomorrow'), null);
});
t('it agrees with string comparison on every VALID pair, which is why the '
  + 'old code worked and the gap went unnoticed', () => {
  const days = ['2026-01-01', '2026-01-02', '2026-02-28', '2026-03-01', '2026-12-31'];
  for (const a of days) {
    for (const b of days) {
      assert.strictEqual(C.compare(a, b), a < b ? -1 : (a > b ? 1 : 0), a + ' vs ' + b);
    }
  }
});

section('3. arithmetic anchored at UTC midnight');
t('daysBetween counts whole days', () => {
  assert.strictEqual(C.daysBetween('2026-01-01', '2026-03-01'), 59);
  assert.strictEqual(C.daysBetween('2026-03-01', '2026-01-01'), -59);
});
t('...and crosses a DST boundary without losing a day', () => {
  // US DST 2026-03-08. A local-midnight subtraction here is off by an hour and
  // floors to 13 instead of 14.
  assert.strictEqual(C.daysBetween('2026-03-01', '2026-03-15'), 14);
});
t('an invalid end is null, not a number', () => {
  assert.strictEqual(C.daysBetween('2026-01-01', '2026-02-31'), null);
});
t('addDays rolls the month correctly, both leap and not', () => {
  assert.strictEqual(C.addDays('2026-02-28', 1), '2026-03-01');
  assert.strictEqual(C.addDays('2024-02-28', 1), '2024-02-29');
  assert.strictEqual(C.addDays('2026-01-01', -1), '2025-12-31');
});
t('addDays refuses a non-finite count rather than producing Invalid Date', () => {
  assert.strictEqual(C.addDays('2026-01-01', NaN), null);
  assert.strictEqual(C.addDays('2026-01-01', Infinity), null);
});

section('4. the timezone decision is stated, not hidden');
t('todayUTC takes a clock, so it is testable without waiting', () => {
  assert.strictEqual(C.todayUTC(Date.UTC(2026, 8, 14, 23, 59)), '2026-09-14');
});
t('IT IS NAMED FOR WHAT IT IS -- 23:59 UTC is already TOMORROW in Auckland', () => {
  // The three date bugs on this platform came from reading this value as
  // "today". The name is the fix; there is no server-side answer to the user's
  // local day, and this module does not invent one.
  const ms = Date.UTC(2026, 8, 14, 23, 59);
  assert.strictEqual(C.todayUTC(ms), '2026-09-14');
  assert.notStrictEqual(C.todayUTC(ms), '2026-09-15');
  const src = require('fs').readFileSync(__dirname + '/calendar-date.js', 'utf8');
  assert.ok(/no server-side answer/.test(src), 'the limit is no longer stated in the module');
});

section('5. the information leak is closed at the source');
{
  const CE = require('./credential-expiry.js');
  t('credential-expiry still exports isDate, so its five importers are unbroken', () => {
    assert.strictEqual(typeof CE.isDate, 'function');
  });
  t('...and it is now the DEEP one -- the migration is not bug-compatible', () => {
    assert.strictEqual(CE.isDate('2026-02-31'), false);
    assert.strictEqual(CE.isDate('2026-09-14'), true);
  });
  t('a module that needs a date no longer has to import a CREDENTIALS module', () => {
    const src = require('fs').readFileSync(__dirname + '/credential-expiry.js', 'utf8');
    assert.ok(/require\('\.\/calendar-date'\)/.test(src));
  });
}

(async () => {
  for (const [name, fn] of queue) {
    if (!fn) { console.log('--- ' + name + ' ---'); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + (e && e.message)); fail++; }
  }
  console.log('\ncalendar-date: ' + pass + ' passed, ' + fail + ' failed');
  if (fail) process.exit(1);
})();
