// api/_lib/money.test.js
// REQUIREMENT: a money value can never be constructed from a non-number, so no amount
//   reaches storage or a ledger having been coerced from a string, null or
//   NaN
//
//
// Run:  node api/_lib/money.test.js
//
// Control for api/_lib/money.js -- item 90's CONSTRUCTIVE half.
//
// THE ARMS THAT MATTER ARE NOT "does it add correctly". They are the three that
// justify a type existing where a validator already could have been written:
//
//   § 2  `Number('')` is 0 and `Number(null)` is 0 -- every one of those must be
//        a REFUSAL here, because that silent zero is the defect.
//   § 3  THE NaN GUARD ASYMMETRY. `x <= 0` cannot see NaN and `!(x > 0)` can.
//        That difference was a live hole on attorney trust money. This type must
//        make the question unreachable, and the arms DEMONSTRATE the raw-number
//        hole beside the typed version so the comparison is on the record.
//   § 5  COERCION THROWS. `money + 1`, `money > 0` and `${money}` are how a
//        checked value becomes unchecked again, and each must fail at the line
//        that did it rather than three functions later.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const M = require('./money.js');

let pass = 0, fail = 0;
const queue = [];
function t(name, fn) { queue.push([name, fn]); }
function section(s) { queue.push([s, null]); }

// ── THE HELPERS MUST NOT STRINGIFY A RESULT THAT CONTAINS MONEY ─────────────
// The first version built its failure message with `JSON.stringify(r)`, and
// JavaScript evaluates an assertion's message argument EAGERLY -- so every
// successful parse hit Money.toJSON(), which throws by design, and 20 of 31
// arms failed with the type's own coercion error. The type was right and the
// harness was wrong, which is a distinction worth writing down: a suite that
// cannot describe its subject without coercing it will report the subject as
// broken.
const describeResult = (r) => (r && r.ok)
  ? 'ok, cents=' + (r.money && r.money.cents)
  : 'refused: ' + (r && r.code) + ' -- ' + (r && r.reason);
const ok = (r) => { assert.ok(r.ok, 'expected ok, got ' + describeResult(r)); return r.money; };
const no = (r) => { assert.ok(!r.ok, 'expected a refusal, got ' + describeResult(r)); return r; };

// ════════════════════════════════════════════════════════════════════════════
section('1. the ordinary case');
t('cents parse and round-trip', () => {
  assert.strictEqual(ok(M.parseCents(1234)).cents, 1234);
  assert.strictEqual(ok(M.parseCents('1234')).cents, 1234);
  assert.strictEqual(ok(M.parseCents(0)).cents, 0);
  assert.strictEqual(ok(M.parseCents(-500)).cents, -500);
});
t('dollars scale to cents WITHOUT a float multiply', () => {
  // 12.34 * 100 is 1233.9999999999998 in IEEE754. Scaling on the string is why
  // this is 1234 and not a rounded 1233.
  assert.strictEqual(ok(M.parseDollars(12.34)).cents, 1234);
  assert.strictEqual(ok(M.parseDollars('12.34')).cents, 1234);
  assert.strictEqual(ok(M.parseDollars('12.3')).cents, 1230);
  assert.strictEqual(ok(M.parseDollars('12')).cents, 1200);
  assert.strictEqual(ok(M.parseDollars('-12.34')).cents, -1234);
});
t('THE 4.5e-13 CASE: the same dollar amount is the same cents', () => {
  // Two figures 4.5e-13 apart refused a CORRECT bill on 2026-09-14, printing
  // "billed $3828.47 against $3828.47 actually received". In cents they are one
  // integer and cannot differ.
  const a = ok(M.parseDollars('3828.47'));
  const b = ok(M.parseDollars(3828.47));
  assert.strictEqual(a.cents, b.cents);
  assert.ok(a.equals(b), 'a correct bill must not be refused');
});
t('format is a STRING and never a number', () => {
  assert.strictEqual(ok(M.parseCents(382847)).format(), '$3,828.47');
  assert.strictEqual(ok(M.parseCents(-5)).format(), '-$0.05');
  assert.strictEqual(ok(M.parseCents(0)).format(), '$0.00');
  assert.strictEqual(typeof ok(M.parseCents(1)).format(), 'string');
});

// ════════════════════════════════════════════════════════════════════════════
section('2. THE SILENT ZERO -- every input Number() turns into 0 is REFUSED');
t("'' is a refusal, not zero", () => {
  const r = no(M.parseCents(''));
  assert.strictEqual(r.code, 'MONEY_NOT_A_NUMBER');
  assert.ok(/empty string/.test(r.reason), r.reason);
  no(M.parseDollars(''));
});
t('null, undefined and a missing field are refusals', () => {
  [null, undefined].forEach((v) => {
    no(M.parseCents(v)); no(M.parseDollars(v));
  });
  const payload = {};
  no(M.parseDollars(payload.amount));
});
t('[] and false are refusals -- Number() makes both 0', () => {
  [[], false, true, {}].forEach((v) => {
    no(M.parseCents(v));
    no(M.parseDollars(v));
  });
});
t('CONTROL: a real zero IS accepted -- it is a measurement', () => {
  // Without this, "reject the falsy" would also reject a genuine $0.00, which
  // is a real amount and a different fact from "no amount".
  assert.strictEqual(ok(M.parseCents(0)).cents, 0);
  assert.strictEqual(ok(M.parseDollars('0.00')).cents, 0);
  assert.ok(ok(M.parseCents(0)).isZero());
});
t('a formatted amount is REFUSED, not guessed', () => {
  // '1,200' is one thousand two hundred in one locale and one-point-two in
  // another. Stripping the separator here would be this file guessing.
  ['$12.34', '1,200', '12.34 USD', '12abc'].forEach((v) => no(M.parseDollars(v)));
});
t('more precision than money has is REFUSED, not rounded', () => {
  const r = no(M.parseDollars('12.345'));
  assert.strictEqual(r.code, 'MONEY_TOO_PRECISE');
  no(M.parseDollars(0.001));
});
t('a fractional CENT is refused', () => {
  assert.strictEqual(no(M.parseCents(12.5)).code, 'MONEY_FRACTIONAL_CENT');
});
t('Infinity and NaN are refusals', () => {
  [Infinity, -Infinity, NaN, 'Infinity', 'NaN'].forEach((v) => {
    no(M.parseCents(v)); no(M.parseDollars(v));
  });
});

// ════════════════════════════════════════════════════════════════════════════
section('3. THE NaN GUARD ASYMMETRY -- the live hole, and why a type ends it');
t('DEMONSTRATION: `<= 0` lets NaN through and `!(x > 0)` does not', () => {
  // On the record in the suite rather than only in a comment, because this is
  // the defect the type exists to make unreachable. Attorney trust money,
  // 2026-09-14.
  const amount = Number('');          // 0 -- the silent zero
  assert.strictEqual(amount, 0);
  const nan = Number('abc');          // NaN
  assert.strictEqual(nan <= 0, false, 'a NaN PASSES a <= 0 guard');
  assert.strictEqual(!(nan > 0), true, 'and is caught by the negated form');
});
t('...and with Money the question cannot arise: there is no NaN to guard', () => {
  no(M.parseCents('abc'));
  no(M.parseCents(NaN));
  // Anything that survives parsing is an integer, so every comparison is total.
  const m = ok(M.parseCents(1));
  assert.strictEqual(m.isPositive(), true);
  assert.strictEqual(ok(M.parseCents(0)).isPositive(), false);
  assert.strictEqual(ok(M.parseCents(-1)).isNegative(), true);
});
t('compare is total across a set including zero and negatives', () => {
  const a = ok(M.parseCents(-1)), b = ok(M.parseCents(0)), c = ok(M.parseCents(1));
  assert.strictEqual(a.compare(b), -1);
  assert.strictEqual(b.compare(c), -1);
  assert.strictEqual(c.compare(c), 0);
  assert.strictEqual(c.compare(a), 1);
});

// ════════════════════════════════════════════════════════════════════════════
section('4. arithmetic accepts ONLY Money');
t('plus, minus and times work', () => {
  const a = ok(M.parseDollars('10.00')), b = ok(M.parseDollars('2.50'));
  assert.strictEqual(a.plus(b).cents, 1250);
  assert.strictEqual(a.minus(b).cents, 750);
  assert.strictEqual(b.times(4).cents, 1000);
});
t('adding a RAW NUMBER throws -- that is how a checked value goes unchecked', () => {
  const a = ok(M.parseDollars('10.00'));
  assert.throws(() => a.plus(5), (e) => e.code === 'MONEY_NOT_MONEY');
  assert.throws(() => a.plus('5'), (e) => e.code === 'MONEY_NOT_MONEY');
  assert.throws(() => a.minus(null), (e) => e.code === 'MONEY_NOT_MONEY');
});
t('a FRACTIONAL multiplier throws rather than reintroducing a float', () => {
  const a = ok(M.parseDollars('10.00'));
  assert.throws(() => a.times(1.5), (e) => e.code === 'MONEY_FRACTIONAL_FACTOR');
});
t('sum() requires every element to be Money and says WHICH failed', () => {
  const a = ok(M.parseCents(100)), b = ok(M.parseCents(200));
  assert.strictEqual(M.sum([a, b]).cents, 300);
  assert.strictEqual(M.sum([]).cents, 0);
  assert.throws(() => M.sum([a, 5]), (e) => /element 1/.test(e.message));
});
t('arithmetic leaving the safe integer range throws', () => {
  const big = ok(M.parseCents(M.MAX_CENTS));
  assert.throws(() => big.plus(big), (e) => e.code === 'MONEY_OUT_OF_RANGE');
});
t('a Money is FROZEN -- cents cannot be rewritten after the check', () => {
  const a = ok(M.parseCents(100));
  try { a.cents = 999999; } catch (e) { /* strict mode throws; either is fine */ }
  assert.strictEqual(a.cents, 100);
  assert.ok(Object.isFrozen(a));
});

// ════════════════════════════════════════════════════════════════════════════
section('5. COERCION THROWS -- the mechanism that makes this structural');
t('money + 1 THROWS instead of silently becoming a number', () => {
  const a = ok(M.parseCents(100));
  assert.throws(() => a + 1, (e) => e.code === 'MONEY_COERCION');
});
t('money > 0 THROWS -- the comparison that started this whole class', () => {
  const a = ok(M.parseCents(100));
  assert.throws(() => a > 0, (e) => e.code === 'MONEY_COERCION');
});
t('template interpolation THROWS -- no unlabelled number in front of a user', () => {
  const a = ok(M.parseCents(100));
  assert.throws(() => `${a}`, (e) => e.code === 'MONEY_COERCION');
  assert.throws(() => 'total: ' + a, (e) => e.code === 'MONEY_COERCION');
});
t('JSON.stringify THROWS -- store .cents, never a float', () => {
  const a = ok(M.parseCents(100));
  assert.throws(() => JSON.stringify(a), (e) => e.code === 'MONEY_COERCION');
  assert.strictEqual(JSON.stringify({ amount_cents: a.cents }), '{"amount_cents":100}');
});
t('CONTROL: the deliberate paths still work, or the type is unusable', () => {
  // A type that throws on everything is not safe, it is unshippable. Both
  // intended exits must be ergonomic.
  const a = ok(M.parseCents(100));
  assert.strictEqual(a.cents, 100);
  assert.strictEqual(a.format(), '$1.00');
});

// ════════════════════════════════════════════════════════════════════════════
section('6. a Money cannot be FORGED');
t('an object literal claiming to be Money is rejected', () => {
  const fake = { cents: 999, plus() {}, format() { return '$9.99'; } };
  assert.strictEqual(M.isMoney(fake), false);
  assert.throws(() => M.requireMoney(fake), (e) => e.code === 'MONEY_NOT_MONEY');
  assert.throws(() => M.sum([fake]), (e) => e.code === 'MONEY_NOT_MONEY');
});
t('the brand is a Symbol, so a string key cannot forge it', () => {
  const fake = { cents: 1, 'sairn.money': true, 'Symbol(sairn.money)': true };
  assert.strictEqual(M.isMoney(fake), false);
});
t('the real thing passes its own predicate', () => {
  assert.strictEqual(M.isMoney(ok(M.parseCents(1))), true);
  assert.strictEqual(M.isMoney(M.ZERO), true);
  assert.strictEqual(M.ZERO.cents, 0);
});

// ════════════════════════════════════════════════════════════════════════════
section('7. it reuses safe-number rather than re-deciding the parse');
t('the module imports measureNumber instead of its own coercion', () => {
  const src = fs.readFileSync(path.join(__dirname, 'money.js'), 'utf8');
  assert.ok(/require\('\.\/safe-number'\)/.test(src),
    'the parse half is already solved and consolidated; a second copy is the '
    + 'sixth bespoke fix this platform keeps writing');
  assert.ok(src.indexOf('parseFloat(') === -1,
    'parseFloat partially parses -- \'1,200\' becomes 1');
});
t('no currency and no division, and that is deliberate', () => {
  // ── COMMENTS STRIPPED FIRST, AND THIS IS THE THIRD TIME TONIGHT ───────────
  // The first version matched `\bdivide\s*\(` against the whole file and fired
  // on money.js's own comment explaining WHY there is no divide(). Same defect
  // shape as two other arms written today: the QR suite's "no PII" arm firing on
  // the words "no patient or practice data", and the Tier A gate's fail-open arm
  // firing on a docstring quoting the old line.
  //
  // THE CLASS IS NOT "quoting old code in a comment". It is broader: A TEXT
  // MATCH COUNTS A WORD'S APPEARANCE IN PROSE THE SAME AS ITS APPEARANCE IN
  // LOGIC, and the better the prose explains the absence, the more likely the
  // checker is to report the thing as present. Strip comments, or assert on
  // structure.
  const src = fs.readFileSync(path.join(__dirname, 'money.js'), 'utf8');
  const code = src.split('\n').filter((l) => !l.trim().startsWith('//')).join('\n');
  assert.ok(!/\bdivide\s*\(/.test(code),
    'splitting money is a decision about who gets the remainder cent; a silent '
    + 'divide is the quietest way to lose money');
  assert.ok(!/\bcurrency\b/.test(code),
    'every amount here is USD, and an unused currency field reads as '
    + 'multi-currency support');
  // And the CONTROL on the strip itself: the comment really does contain the
  // word, so an arm that passed on the raw source would have been passing for
  // the wrong reason.
  assert.ok(/\bdivide\s*\(/.test(src),
    'the explanatory comment should still mention divide() -- if it does not, '
    + 'this arm has stopped testing the strip');
});

(async () => {
  for (const [name, fn] of queue) {
    if (!fn) { console.log('--- ' + name + ' ---'); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
  }
  console.log('\nmoney: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
