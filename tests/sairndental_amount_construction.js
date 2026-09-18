// tests/sairndental_amount_construction.js
// REQUIREMENT: an amount that cannot be read as a number is REFUSED at the
//   write, never stored as a measured zero, and the refusal is a shape the
//   caller cannot mistake for "saved on this device only"
//
// Run:  node tests/sairndental_amount_construction.js
//
// ── WHY THIS EXISTS, AND WHY THE SERVER CANNOT COVER IT ────────────────────
// `addChargeEntry` and `addPaymentEntry` built their record with
// `Number(amount)||0`. Both were CORRECT BY CALLER and not by construction: all
// three call sites guard with `if(!amount||amount<=0)`, so nothing unreadable
// ever reached them -- and a fourth caller without that guard stores a silent
// $0. Raised as a finding while reviewing cody's dnt_rollup measureNumber
// change on 2026-09-17 and fixed here.
//
// THE CONSEQUENCE IS WORSE THAN THE SERVER-SIDE VERSION OF THE SAME BUG, which
// is the reason it is worth a suite of its own. api/_lib/dnt-rollup.js reports
// an unreadable AMOUNT as `unread` and drops `disclosure.complete` to false, so
// a reader can see money is missing. A zero stored at the WRITE is not
// unreadable at all -- it is a real, readable, measured $0 charge. The roll-up
// counts it, `unread` stays 0, `complete` stays true, and the practice's
// production total is short by the whole amount with nothing saying so. It is
// precisely the case the server's careful arithmetic structurally cannot see.
//
// DNT_HTML points this at a mutated copy so a negative control can prove the
// arms bite without patching the tracked file.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const html = fs.readFileSync(process.env.DNT_HTML
  || path.join(__dirname, '..', 'sairndental.html'), 'utf8')
  .replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function grab(sig, terminator) {
  const at = html.indexOf(sig);
  assert.ok(at > 0, 'not found in sairndental.html: ' + sig);
  const end = html.indexOf(terminator, at);
  assert.ok(end > at, 'terminator not found after ' + sig);
  return html.slice(at, end + terminator.length);
}

const ctx = { console: console };
vm.createContext(ctx);
vm.runInContext(grab('function dntMoneyIn(v){', '\n}\n'), ctx);
vm.runInContext(grab('function dntBadAmount(what){', '\n}\n'), ctx);

// ---------------------------------------------------------------------------
section('1. THE ONE THAT MATTERS: unreadable is NEVER zero');

test('every unreadable shape returns null, not 0', () => {
  // The whole population Number() silently turns into a number. Each of these
  // would have been stored as a real $0 charge by `Number(amount)||0` -- except
  // the strings, which Number() makes NaN and `||0` then makes 0 anyway. Both
  // routes end at the same wrong place.
  const junk = [undefined, null, '', '   ', '\t', 'abc', '1,200', '$100', '12abc',
                true, false, [], [5], {}, NaN, Infinity, -Infinity, -1, -0.01];
  junk.forEach((v) => {
    assert.strictEqual(ctx.dntMoneyIn(v), null,
      'accepted ' + JSON.stringify(String(v)) + ' as ' + ctx.dntMoneyIn(v));
  });
});

test("'1,200' is refused rather than repaired -- no locale guessing", () => {
  // parseFloat('1,200') is 1. Number('1,200') is NaN. Stripping the comma would
  // be this app deciding it means one thousand two hundred, which is wrong in
  // any locale that uses it as a decimal mark.
  assert.strictEqual(ctx.dntMoneyIn('1,200'), null);
  assert.strictEqual(ctx.dntMoneyIn('1.200'), 1.2, 'a plain decimal must still parse');
});

test('a REAL zero is still accepted -- the distinction cuts both ways', () => {
  assert.strictEqual(ctx.dntMoneyIn(0), 0);
  assert.strictEqual(ctx.dntMoneyIn('0'), 0);
  assert.strictEqual(ctx.dntMoneyIn('0.00'), 0);
});

test('ordinary amounts parse, including strings from a form field', () => {
  assert.strictEqual(ctx.dntMoneyIn(125.5), 125.5);
  assert.strictEqual(ctx.dntMoneyIn('125.50'), 125.5);
  assert.strictEqual(ctx.dntMoneyIn(' 125.50 '), 125.5);
});

test('it matches api/_lib/safe-number.js measureNumber, plus non-negative', () => {
  const { measureNumber } = require(path.join(__dirname, '..', 'api', '_lib', 'safe-number.js'));
  // Same answers on everything that is not a negative number -- the two are the
  // same rule, and the ledgers add "an amount is never below zero" on top.
  [undefined, null, '', '   ', 'abc', '1,200', true, [], 0, '0', 125.5, ' 12 ']
    .forEach((v) => {
      assert.strictEqual(ctx.dntMoneyIn(v), measureNumber(v),
        'diverged from the server-side rule on ' + JSON.stringify(String(v)));
    });
  assert.strictEqual(measureNumber(-5), -5, 'the shared rule allows negatives');
  assert.strictEqual(ctx.dntMoneyIn(-5), null, 'a ledger amount must not be negative');
});

// ---------------------------------------------------------------------------
section('2. THE WRITERS REFUSE AT CONSTRUCTION, not at the caller');

test('both writers parse BEFORE building the record', () => {
  const ch = grab('async function addChargeEntry(', '\n}\n');
  const pm = grab('async function addPaymentEntry(', '\n}\n');
  [['addChargeEntry', ch], ['addPaymentEntry', pm]].forEach(([name, src]) => {
    assert.ok(/var amt=dntMoneyIn\(amount\);/.test(src), name + ' does not parse the amount');
    assert.ok(/if\(amt===null\) return dntBadAmount\(/.test(src),
      name + ' does not refuse an unreadable amount');
    assert.ok(!/Number\(amount\)\|\|0/.test(src),
      name + ' still coerces an unreadable amount to a measured zero');
    // The refusal has to come first: anything built before it is a record that
    // existed with a bad amount, however briefly.
    assert.ok(src.indexOf('dntBadAmount') < src.indexOf('newId('),
      name + ' builds the record id before refusing');
  });
});

test('the estimate is computed from the VALIDATED amount', () => {
  const ch = grab('async function addChargeEntry(', '\n}\n');
  assert.ok(/computeEstimatedInsurance\(amt,/.test(ch),
    'the insurance estimate is derived from the raw amount, so a value the '
    + 'function has already refused still produces a stored second figure');
});

// ---------------------------------------------------------------------------
section('3. THE REFUSAL CANNOT BE MISTAKEN FOR A SAVE');

test('badAmount is distinguishable from unreachable and from refused', () => {
  const r = ctx.dntBadAmount('charge');
  assert.strictEqual(r.badAmount, true);
  assert.strictEqual(r.rec, null, 'a refused amount must leave no record behind');
  assert.strictEqual(r.kept, false, 'nothing may be kept locally');
  assert.strictEqual(r.queued, false, 'nothing may be queued for retry');
  // syncResult null + refused false is the UNREACHABLE shape, which is why the
  // flag exists and why every call site must branch on it first.
  assert.strictEqual(r.syncResult, null);
  assert.strictEqual(r.refused, false);
});

test('the message says nothing was stored, and says why not zero', () => {
  const why = ctx.dntBadAmount('payment').why;
  assert.ok(/NOTHING was recorded/.test(why), 'the message does not say nothing was stored');
  assert.ok(/\$0/.test(why), 'the message does not rule out a zero having been saved');
  assert.ok(/payment/.test(why), 'the message does not name which amount');
});

test('EVERY call site branches on badAmount BEFORE reading syncResult', () => {
  // Three today. A fourth added without this line is the defect returning.
  const calls = html.split('\n')
    .map((l, i) => [i, l])
    .filter(([, l]) => /await add(Charge|Payment)Entry\(/.test(l));
  assert.strictEqual(calls.length, 3, 'the number of ledger call sites changed: '
    + calls.length + ' -- read them and extend this arm rather than raising it');
  const lines = html.split('\n');
  calls.forEach(([i]) => {
    const next = lines.slice(i + 1, i + 6).join('\n');
    assert.ok(/if\(result\.badAmount\)\{/.test(next),
      'the call site at line ' + (i + 1) + ' does not branch on badAmount, so a '
      + 'refused amount would be reported to the user as an unreachable server');
  });
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' AMOUNT-CONSTRUCTION ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
