// api/_lib/calendar-date.js
// ---------------------------------------------------------------------------
// ONE MODULE OWNS "WHAT IS A CALENDAR DATE, AND HOW DO TWO OF THEM COMPARE".
// Item 94 -- deep vs shallow modules, applied to the concept this platform has
// reimplemented most.
//
// ── THE MEASUREMENT THAT MADE THIS WORTH DOING ─────────────────────────────
// `isDate` is defined FOURTEEN TIMES across api/, and all fourteen are
// BYTE-IDENTICAL:
//
//     function isDate(s) { return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s); }
//
// So the interesting finding is not that they disagree. It is that they agree,
// and are all wrong in the same way -- WHICH IS THE FAILURE MODE OF COPYING
// RATHER THAN IMPORTING. One fix would have been fourteen.
//
// ── WHAT ALL FOURTEEN GET WRONG, MEASURED IN NODE ──────────────────────────
// They validate the SHAPE of a date, not the DATE. And JavaScript does not
// reject an impossible one -- it silently repairs it into a different, real,
// plausible one:
//
//     isDate('2026-02-31')  -> true
//     new Date('2026-02-31T00:00:00Z')  ->  2026-03-03      THREE DAYS LATER
//     isDate('2026-02-29')  -> true      (2026 is not a leap year)
//     new Date('2026-02-29T00:00:00Z')  ->  2026-03-01
//     isDate('2026-04-31')  -> true
//     new Date('2026-04-31T00:00:00Z')  ->  2026-05-01
//
// On a legal deadline, a credential expiry or a draw period end that is not an
// error anybody sees. It is a WRONG ANSWER THAT LOOKS RIGHT, produced days
// after the value was accepted, by a validator that said yes.
//
// `2026-13-99` DOES become Invalid Date, which is the trap: the obviously
// broken input fails loudly and the nearly-right one fails silently. Anybody
// spot-checking with garbage would conclude the guard works.
//
// ── THE INFORMATION LEAK THIS ALSO CLOSES ──────────────────────────────────
// Five modules already share a date helper -- by importing it from
// `credential-expiry.js`. A module that needs to know what a date is should not
// have to depend on a module about CREDENTIALS. That is the shallow-module
// symptom exactly: the concern leaked into whichever file happened to need it
// first, and everything downstream now carries that file's name in its imports.
//
// ── THE ONE DECISION THIS MODULE MAKES, AND STATES ─────────────────────────
// A CALENDAR DATE HAS NO TIMEZONE. '2026-09-14' is the same string in Auckland
// and in Los Angeles, and the moment you turn it into a Date you have chosen
// one. So every function here works on the STRING where it can, and where it
// cannot -- daysBetween, addDays -- it anchors at UTC midnight and says so.
//
// `todayUTC()` is deliberately named for what it is. The three date bugs on this
// platform all came from `new Date().toISOString().slice(0, 10)` being read as
// "today" when it is "today in UTC", which is yesterday for a Los Angeles user
// until 5pm. A caller who wants the user's local day must pass it in from the
// browser; there is no server-side answer to that question and this module does
// not pretend to have one.
// ---------------------------------------------------------------------------

'use strict';

const SHAPE = /^(\d{4})-(\d{2})-(\d{2})$/;
const DAY_MS = 24 * 60 * 60 * 1000;

/**
 * A real calendar date in YYYY-MM-DD, not merely something shaped like one.
 *
 * THE ROUND TRIP IS THE CHECK. Building the date and reading the parts back is
 * the only way to reject 2026-02-31 -- a regex cannot know how many days
 * February has, and `new Date` will not tell you, because it rolls over instead
 * of refusing.
 */
function isCalendarDate(s) {
  const m = typeof s === 'string' && SHAPE.exec(s);
  if (!m) return false;
  const y = Number(m[1]), mo = Number(m[2]), d = Number(m[3]);
  if (mo < 1 || mo > 12 || d < 1 || d > 31) return false;
  const t = Date.UTC(y, mo - 1, d);
  if (!isFinite(t)) return false;
  const back = new Date(t);
  return back.getUTCFullYear() === y &&
         back.getUTCMonth() === mo - 1 &&
         back.getUTCDate() === d;
}

/** Milliseconds at UTC midnight, or null. NULL, NEVER NaN: NaN compares false
 *  against everything, so a caller who forgot to check gets a silent "no"
 *  rather than a loud one -- the shape that let a NaN reach the trust ledger. */
function toMs(s) {
  if (!isCalendarDate(s)) return null;
  const m = SHAPE.exec(s);
  return Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
}

/**
 * -1, 0, 1 -- or null when either side is not a calendar date.
 *
 * NULL RATHER THAN A NUMBER for a bad input, deliberately. Returning 0 would
 * read as "equal" and returning -1 as "earlier", and both are answers to a
 * question that was not asked. A caller must handle the third state; that is
 * the point of it existing.
 *
 * For two VALID dates this is the same answer `a < b` gives on the strings --
 * ISO-8601 sorts lexicographically, which is why string comparison has worked
 * here and why nobody noticed the validation gap.
 */
function compare(a, b) {
  if (!isCalendarDate(a) || !isCalendarDate(b)) return null;
  return a < b ? -1 : (a > b ? 1 : 0);
}

/** Whole days from `a` to `b`, or null. Anchored at UTC midnight on both sides,
 *  so it is unaffected by daylight saving -- a local-midnight subtraction across
 *  a DST boundary is off by an hour and floors to the wrong day. */
function daysBetween(a, b) {
  const x = toMs(a), y = toMs(b);
  if (x === null || y === null) return null;
  return Math.round((y - x) / DAY_MS);
}

/** `s` plus n days as YYYY-MM-DD, or null. Rounds through UTC for the same
 *  reason daysBetween does. */
function addDays(s, n) {
  const t = toMs(s);
  if (t === null || typeof n !== 'number' || !isFinite(n)) return null;
  return format(new Date(t + Math.trunc(n) * DAY_MS));
}

/** A Date to YYYY-MM-DD, read in UTC. */
function format(d) {
  if (!(d instanceof Date) || isNaN(d.getTime())) return null;
  const p = (n) => (n < 10 ? '0' : '') + n;
  return d.getUTCFullYear() + '-' + p(d.getUTCMonth() + 1) + '-' + p(d.getUTCDate());
}

/**
 * Today's calendar date IN UTC.
 *
 * NAMED FOR WHAT IT IS. `new Date().toISOString().slice(0, 10)` is the same
 * value and reads as "today", and that misreading is where this platform's date
 * bugs came from -- for a Los Angeles user it is YESTERDAY until 5pm. A caller
 * who needs the user's local day has to send it from the browser. There is no
 * server-side answer to that and this module will not invent one.
 */
function todayUTC(nowMs) {
  return format(new Date(typeof nowMs === 'number' ? nowMs : Date.now()));
}

module.exports = {
  isCalendarDate,
  toMs,
  compare,
  daysBetween,
  addDays,
  format,
  todayUTC,
  DAY_MS,
  // THE OLD NAME, KEPT AS AN ALIAS SO THE FOURTEEN COPIES CAN BE RETIRED ONE
  // AT A TIME rather than in a bulk replace across api/. It is NOT the old
  // behaviour: this one rejects 2026-02-31. That is the whole reason to move,
  // and a migration that preserved the bug would be a rename.
  isDate: isCalendarDate
};
