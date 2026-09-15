// api/_lib/safe-number.js
// ---------------------------------------------------------------------------
// TWO functions, not one, and the split is the whole point.
//
// ══ WHY THIS IS A RECOMBINATION AND NOT A NEW HELPER ════════════════════════
// 190 non-test `Number(` / `parseFloat(` / `parseInt(` call sites exist in
// api/. Five of them already solve this problem CORRECTLY and independently,
// and they had already converged on two DIFFERENT answers -- because there are
// two different jobs:
//
//   CONFIG   `ai-rate-limit.js:117,135,139`, `anon-rate-limit.js:126,131`,
//            `cron-jitter.js:68`     -> fall back to a DEFAULT
//   MEASURE  `ai-rate-limit.js:164`, `dental-bi.js:89`
//                                    -> return NULL
//
// A single "safe number" function would have to pick one, and would then be
// wrong in the other job -- which is precisely how the SIXTH bespoke fix gets
// written. So: two functions, named for the job, and this header says why.
//
// ── WHAT EACH EXISTING FIX GOT RIGHT, AND WHICH ONE IS THE MODEL ───────────
// `cron-jitter.js` IS THE MODEL FOR CONFIG, AND IT IS THE ONLY ONE THAT
// ACTUALLY HANDLES THE TRAP. It checks `raw !== undefined && raw !== ''`
// BEFORE converting. The rate limiters do not -- they rely on a later `> 0`
// test, and `Number('') === 0` fails that test, so they are correct BY
// ACCIDENT OF AN UNRELATED POSITIVITY CONSTRAINT.
//
// THAT MATTERS BECAUSE IT IS THE COPYABLE ONE. The rate-limiter shape reads as
// the platform idiom (five of six sites) and it is the shape that breaks the
// moment somebody uses it for a config value where ZERO IS LEGAL -- a jitter,
// a retry count, a grace period. `SAIRN_X=''` then means "0", silently, which
// is a switched-off feature that looks configured. `cron-jitter.js` allows
// `>= 0` and therefore HAD to get the empty-string check right; the others
// never had to.
//
// `dental-bi.js:coerce` IS THE MODEL FOR MEASUREMENT: `undefined`, `null` and
// `''` are null BEFORE any conversion, then `Number` (not `parseFloat`), then
// `Number.isFinite(n) ? n : null`.
//
// ── Number() NOT parseFloat(), AND THIS IS NOT STYLE ───────────────────────
//     Number('12abc')     -> NaN      parseFloat('12abc')     -> 12
//     Number('1,200')     -> NaN      parseFloat('1,200')     -> 1
//     Number('$1,200')    -> NaN      parseFloat('$1,200')    -> NaN
//     Number('')          -> 0        parseFloat('')          -> NaN
//     Number(' 12 ')      -> 12       parseFloat(' 12 ')      -> 12
//     Number(null)        -> 0        parseFloat(null)        -> NaN
//     Number([])          -> 0        parseFloat([])          -> NaN
//     Number(true)        -> 1        parseFloat(true)        -> NaN
//
// parseFloat's PARTIAL PARSE is the dangerous half: a thousands-separated
// amount `'1,200'` becomes 1, and `'12abc'` becomes 12. Both are plausible
// numbers that are wrong, which is worse than NaN -- NaN is loud. Number()'s
// dangerous half is the opposite: `''`, `null`, `[]` and `false` all become 0.
// Each function below closes the half that matters for its own job, and
// NEITHER is a drop-in for a bare `Number()` -- that is the point.
//
// ── WHAT THIS DELIBERATELY DOES NOT DO ────────────────────────────────────
// No currency parsing. Stripping `$` and `,` would be this module guessing at a
// locale, and `1,200` is one thousand two hundred in one and one-point-two in
// another. An amount that arrives formatted is an UPSTREAM defect and must be
// visible as unreadable, not silently repaired here.
//
// No integer-cents conversion either. That is a real standing rule on this
// platform -- two figures 4.5e-13 apart once refused a correct bill -- but it
// is a decision about a FIELD'S representation, made where the field is
// defined. A parser that silently multiplied by 100 would be worse than the
// float.
// ---------------------------------------------------------------------------

'use strict';

/**
 * A CONFIG value: a number somebody set, or the default when they did not.
 *
 * Absent, blank and unparseable all mean THE SAME THING here -- "nobody chose"
 * -- so they all return `fallback`. That is correct for config and WRONG for a
 * measurement, where "nobody recorded it" and "it is zero" are different facts.
 *
 * @param {*} raw          typically process.env.X
 * @param {number} fallback used whenever raw does not name a usable number
 * @param {object} [opts]  {min, max, integer} -- a value outside the range is
 *                         NOT clamped, it falls back, because a clamp hides a
 *                         misconfiguration behind a working system
 * @returns {number} always a finite number: `fallback` must itself be finite
 */
function configNumber(raw, fallback, opts) {
  const o = opts || {};
  if (!Number.isFinite(fallback)) {
    // The one thing this cannot paper over. A non-finite fallback would make
    // the function return NaN from the "safe" branch, which is the failure it
    // exists to prevent, arriving through the front door.
    throw new TypeError('configNumber: fallback must be a finite number, got '
                        + String(fallback));
  }
  // EXPLICIT, BEFORE ANY CONVERSION -- cron-jitter.js's discipline. Without
  // this line `Number('')` is 0, and for any config where zero is legal that
  // is a switched-off feature wearing the appearance of a configured one.
  if (raw === undefined || raw === null) return fallback;
  if (typeof raw === 'string' && raw.trim() === '') return fallback;
  // Booleans and arrays convert to numbers in JavaScript and never mean one.
  if (typeof raw === 'boolean' || Array.isArray(raw)) return fallback;

  const n = Number(raw);
  if (!Number.isFinite(n)) return fallback;
  if (o.integer && !Number.isInteger(n)) return fallback;
  if (typeof o.min === 'number' && n < o.min) return fallback;
  if (typeof o.max === 'number' && n > o.max) return fallback;
  return n;
}

/**
 * A MEASUREMENT: a number that was recorded, or `null` when it was not.
 *
 * NEVER 0 FOR AN ABSENT VALUE. Zero is itself a measurement -- "we billed
 * nothing" is a different claim from "we could not read what we billed" -- and
 * collapsing them produces an authoritative total that is short by an unknown
 * amount. That sentence is api/_lib/dnt-rollup.js's own rule 3, which that file
 * applied to RESOURCES and not to FIELDS.
 *
 * A caller that genuinely wants 0 writes `?? 0` and is visibly choosing it.
 *
 * @param {*} raw
 * @returns {number|null}
 */
function measureNumber(raw) {
  if (raw === undefined || raw === null) return null;
  if (typeof raw === 'string' && raw.trim() === '') return null;
  if (typeof raw === 'boolean' || Array.isArray(raw)) return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

/**
 * Sum a column of measurements and SAY HOW MANY COULD NOT BE READ.
 *
 * The second half is the part that is usually missing, and it is what makes a
 * total checkable: `{value: 112, rows: 5}` looks well-founded, and
 * `{value: 112, rows: 5, unread: 3}` cannot be mistaken for it.
 *
 * @param {Array} values
 * @returns {{value:number, counted:number, unread:number}}
 */
function sumMeasurements(values) {
  const list = Array.isArray(values) ? values : [];
  let value = 0, counted = 0, unread = 0;
  list.forEach((v) => {
    const n = measureNumber(v);
    if (n === null) { unread += 1; return; }
    value += n; counted += 1;
  });
  return { value: value, counted: counted, unread: unread };
}

module.exports = { configNumber, measureNumber, sumMeasurements };
