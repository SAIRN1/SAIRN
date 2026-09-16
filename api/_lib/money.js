// api/_lib/money.js
// ---------------------------------------------------------------------------
// A MONEY VALUE THAT CANNOT BE CONSTRUCTED FROM A NON-NUMBER.
//
// Item 90's constructive half. `tools/shape_antipattern_check.py` already
// DETECTS the shape -- it is live and currently names `Number(payload.amount)`
// at api/sd-data.js:11796 among others. Detection tells you where the bug is.
// This is the thing that makes it unwritable.
//
// ══ THE DEFECT, IN THE FORM IT ACTUALLY TAKES HERE ══════════════════════════
//     const amount = Number(payload.amount);      // '' -> 0
//     if (amount <= 0) return refuse();           // NaN -> false, so NaN PASSES
//     ledger.post(amount);                        // posts NaN, or posts 0
//
// TWO SEPARATE HOLES IN THREE LINES, and the platform has paid for both:
//
//   1. `Number('')` is 0, and `Number(null)` is 0, and `Number([])` is 0. An
//      ABSENT field becomes a real number and every downstream check passes on
//      it. A charge of nothing is recorded as a charge of zero, which is a
//      measurement somebody will act on.
//
//   2. `amount <= 0` CANNOT SEE NaN. Every comparison against NaN is false, so
//      a NaN sails through a guard that reads as a range check. The negated form
//      `!(amount > 0)` catches it. That exact difference was a LIVE HOLE ON
//      ATTORNEY TRUST MONEY, found 2026-09-14, and it is why the detector's own
//      message tells you to check the FORM of any guard you find rather than
//      just its presence.
//
// A validator cannot close this, because a validator is something a caller can
// forget to call and the value looks identical either way. A TYPE can: if the
// only way to get a Money is through a parse that refuses, then a function
// holding a Money is holding a number somebody checked.
//
// ══ WHAT MAKES IT STRUCTURAL RATHER THAN A CONVENTION ═══════════════════════
// JavaScript has no nominal types, so "structural" has to be earned. Four
// mechanisms, and the third is the one that does the real work:
//
//   * CONSTRUCTION IS A PARSE THAT CAN FAIL. `Money.parse()` returns a result
//     object with `ok` and either `money` or `reason`. There is no constructor
//     that takes your word for it.
//   * THE BRAND IS A SYMBOL AND THE OBJECT IS FROZEN, so nothing can forge one
//     with an object literal and nothing can mutate one after the fact.
//   * `valueOf` AND `toString` THROW. This is the mechanism. `money + 1`,
//     `money > 0`, `` `${money}` `` and `JSON.stringify(money)` all THROW
//     LOUDLY instead of silently coercing to a number. Every accidental
//     arithmetic path -- which is how a checked value becomes an unchecked one
//     again -- becomes an exception at the exact line that did it, rather than a
//     wrong figure three functions later.
//   * ARITHMETIC ACCEPTS ONLY MONEY. `plus(5)` throws. You cannot re-enter the
//     unchecked world by adding a raw number to a checked one.
//
// ══ INTEGER CENTS, AND WHY THAT IS NOT NEGOTIABLE HERE ══════════════════════
// Stored and computed as an INTEGER NUMBER OF CENTS. On 2026-09-14 two figures
// 4.5e-13 apart refused a CORRECT bill -- printing "billed $3828.47 against
// $3828.47 actually received", two identical figures and a refusal nobody could
// act on. Found by RUNNING the shipped function rather than reading it. Floats
// are not a money representation and this type will not hold one: `parse` of a
// dollar amount with more than two decimal places is a REFUSAL, not a rounding.
//
// ══ WHAT THIS DELIBERATELY DOES NOT DO ═════════════════════════════════════
// No currency. Every amount on this platform is USD and inventing a currency
// field would be an unused parameter that reads as multi-currency support.
// No locale parsing: `'1,200'` is one thousand two hundred in one locale and
// one-point-two in another, so it is REFUSED rather than guessed. An amount that
// arrives formatted is an upstream defect and must stay visible as one -- the
// same rule api/_lib/safe-number.js states for the same reason.
// No division. Splitting money is a business decision about who gets the
// remainder cent, and a `divide()` that silently dropped it would be the
// quietest possible way to lose money.
// ---------------------------------------------------------------------------

'use strict';

const { measureNumber } = require('./safe-number');

// A Symbol, not a string key: a string brand can be written by an object
// literal, which would let a forged Money through every check below.
const BRAND = Symbol('sairn.money');

const MAX_CENTS = Number.MAX_SAFE_INTEGER;

class MoneyError extends Error {
  constructor(message, code) {
    super(message);
    this.name = 'MoneyError';
    this.code = code || 'MONEY_INVALID';
  }
}

function freezeMoney(cents) {
  const m = {
    [BRAND]: true,
    cents: cents,
    // NOT a getter for dollars. A `.dollars` float would be the thing this type
    // exists to prevent, one property access away. Formatting is `format()`,
    // which returns a STRING and can never be added to anything.
    plus(other) { return add(m, other); },
    minus(other) { return subtract(m, other); },
    times(n) { return multiply(m, n); },
    isZero() { return cents === 0; },
    isPositive() { return cents > 0; },
    isNegative() { return cents < 0; },
    compare(other) { return compareMoney(m, other); },
    equals(other) { return compareMoney(m, other) === 0; },
    format() { return formatCents(cents); },
    // ── THE MECHANISM ────────────────────────────────────────────────────────
    // Throwing here is what makes the type structural rather than advisory.
    // `money + 1` and `money > 0` both reach valueOf; a template literal and
    // JSON.stringify reach toString/toJSON. Each of those is a path back into
    // unchecked arithmetic, and each now fails AT THE LINE THAT DID IT.
    valueOf() {
      throw new MoneyError(
        'Money has no numeric value -- you are about to do arithmetic on a '
        + 'checked amount as if it were a raw number. Use .plus/.minus/.times, '
        + 'or .cents if you genuinely need the integer.', 'MONEY_COERCION');
    },
    toString() {
      throw new MoneyError(
        'Money has no string form by default -- use .format() for display. '
        + 'Interpolating it would put an unlabelled number in front of a user.',
        'MONEY_COERCION');
    },
    toJSON() {
      throw new MoneyError(
        'Money does not serialise implicitly -- store .cents, so what lands in '
        + 'the database is an integer number of cents and not a float.',
        'MONEY_COERCION');
    }
  };
  return Object.freeze(m);
}

function isMoney(v) {
  return !!(v && typeof v === 'object' && v[BRAND] === true);
}

/**
 * The ONLY way in. Returns {ok:true, money} or {ok:false, reason, code}.
 *
 * A RESULT OBJECT RATHER THAN A THROW, deliberately: parsing external input is
 * the ordinary case, not an exceptional one, and a caller that must write
 * `if (!r.ok)` has the refusal in front of it. Everything AFTER construction
 * throws, because by then a bad value is a programming error rather than bad
 * input.
 */
function parseCents(raw) {
  const n = measureNumber(raw);
  if (n === null) {
    return { ok: false, code: 'MONEY_NOT_A_NUMBER',
             reason: 'not a readable number: ' + describe(raw) };
  }
  if (!Number.isInteger(n)) {
    return { ok: false, code: 'MONEY_FRACTIONAL_CENT',
             reason: 'cents must be a whole number, got ' + n
                     + ' -- a fraction of a cent is not an amount, and rounding '
                     + 'it here would hide where it came from' };
  }
  if (Math.abs(n) > MAX_CENTS) {
    return { ok: false, code: 'MONEY_OUT_OF_RANGE',
             reason: 'beyond safe integer range: ' + n };
  }
  return { ok: true, money: freezeMoney(n) };
}

/**
 * Parse a DOLLAR amount -- `12.34`, `'12.34'`, `'12'`. Refuses anything with
 * more than two decimal places rather than rounding it, because a third decimal
 * place means the caller's number did not come from money and silently
 * rounding it would destroy the evidence.
 */
function parseDollars(raw) {
  const n = measureNumber(raw);
  if (n === null) {
    return { ok: false, code: 'MONEY_NOT_A_NUMBER',
             reason: 'not a readable number: ' + describe(raw) };
  }
  // Scale on the STRING, not by multiplying by 100. `12.34 * 100` is
  // 1233.9999999999998 in IEEE754, and rounding that is how a cent goes
  // missing at scale -- the same class as the 4.5e-13 refusal.
  const s = String(n);
  const m = /^(-?)(\d+)(?:\.(\d{1,2}))?$/.exec(s);
  if (!m) {
    if (/\.\d{3,}$/.test(s) || /e/i.test(s)) {
      return { ok: false, code: 'MONEY_TOO_PRECISE',
               reason: 'more precision than money has: ' + s
                       + ' -- refused rather than rounded, because a third '
                       + 'decimal place means this did not come from an amount' };
    }
    return { ok: false, code: 'MONEY_NOT_A_NUMBER', reason: 'unparseable amount: ' + s };
  }
  const sign = m[1] === '-' ? -1 : 1;
  const whole = parseInt(m[2], 10);
  const frac = (m[3] || '').padEnd(2, '0');
  const cents = sign * (whole * 100 + parseInt(frac, 10));
  if (Math.abs(cents) > MAX_CENTS) {
    return { ok: false, code: 'MONEY_OUT_OF_RANGE', reason: 'beyond safe range: ' + s };
  }
  return { ok: true, money: freezeMoney(cents) };
}

function describe(raw) {
  if (raw === undefined) return 'undefined';
  if (raw === null) return 'null';
  if (typeof raw === 'string') return raw.trim() === '' ? 'an empty string' : JSON.stringify(raw);
  if (Array.isArray(raw)) return 'an array';
  if (typeof raw === 'boolean') return String(raw);
  return typeof raw;
}

function requireMoney(v, who) {
  if (!isMoney(v)) {
    throw new MoneyError(
      (who || 'this operation') + ' takes Money, got ' + describe(v)
      + '. Adding a raw number to a checked amount is how a checked value '
      + 'becomes unchecked again.', 'MONEY_NOT_MONEY');
  }
  return v;
}

function add(a, b) {
  requireMoney(a, 'plus'); requireMoney(b, 'plus');
  return freezeMoney(guardSum(a.cents + b.cents));
}
function subtract(a, b) {
  requireMoney(a, 'minus'); requireMoney(b, 'minus');
  return freezeMoney(guardSum(a.cents - b.cents));
}
function multiply(a, n) {
  requireMoney(a, 'times');
  // A COUNT, not an amount. Multiplying money by money is meaningless and a
  // fractional multiplier would reintroduce the float this type exists to keep
  // out -- a rate calculation belongs where the rate is decided, and must come
  // back through parseCents.
  if (!Number.isInteger(n)) {
    throw new MoneyError('times() takes a whole count, got ' + describe(n)
                         + ' -- a fractional multiplier puts a float back into '
                         + 'an amount', 'MONEY_FRACTIONAL_FACTOR');
  }
  return freezeMoney(guardSum(a.cents * n));
}
function guardSum(c) {
  if (!Number.isSafeInteger(c)) {
    throw new MoneyError('arithmetic left the safe integer range: ' + c,
                         'MONEY_OUT_OF_RANGE');
  }
  return c;
}
function compareMoney(a, b) {
  requireMoney(a, 'compare'); requireMoney(b, 'compare');
  return a.cents < b.cents ? -1 : (a.cents > b.cents ? 1 : 0);
}

function sum(list) {
  if (!Array.isArray(list)) {
    throw new MoneyError('sum() takes an array', 'MONEY_NOT_MONEY');
  }
  let total = 0;
  list.forEach((m, i) => {
    requireMoney(m, 'sum() element ' + i);
    total = guardSum(total + m.cents);
  });
  return freezeMoney(total);
}

function formatCents(cents) {
  const neg = cents < 0;
  const abs = Math.abs(cents);
  const whole = Math.floor(abs / 100);
  const frac = String(abs % 100).padStart(2, '0');
  return (neg ? '-$' : '$')
    + String(whole).replace(/\B(?=(\d{3})+(?!\d))/g, ',') + '.' + frac;
}

const ZERO = freezeMoney(0);

module.exports = {
  parseCents, parseDollars, isMoney, requireMoney, sum, ZERO,
  MoneyError, formatCents, MAX_CENTS
};
