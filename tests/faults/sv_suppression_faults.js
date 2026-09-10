// tests/faults/sv_suppression_faults.js
//
// Run:  node tests/faults/sv_suppression_faults.js
//
// FAULT INJECTION on the flag that silences SAIRNvet's server backup.
//
// THE DEFECT THIS GUARDS, and it was live on 2026-09-10. Two places set
// `svSyncSuppressed = true`, do a write, and set it back to false. One of them
// -- svSeedStore() -- used a `finally` from the day it was written, with the
// reason stated at the site: a throw inside a saver must not silence the backup
// for the rest of the session. The other, six lines away in the hydration path,
// did NOT:
//
//     svSyncSuppressed = true;
//     st(key, local);              // st() is the function hardened for quota
//     svSyncSuppressed = false;    // and corrupt-store failures
//
// One throw and every subsequent write on that device stops reaching the
// server, silently, for the rest of the session -- and the surrounding
// `.catch(function(){})` swallows the evidence. Found by reading, handed over,
// and FIXED: the hydration site now carries its own try/finally.
//
// THE POINT OF THIS FILE IS THAT READING IS NOT A GUARD. The next person to
// add a third suppression site gets no warning from a code review that already
// happened. These arms inject the fault -- storage throwing mid-write -- and
// assert the flag comes back down.

'use strict';
const fs = require('fs');
const path = require('path');
const K = require('./faultkit');
const assert = K.assert;

const FILE = 'sairnvet.html';
const SRC = fs.readFileSync(path.join(K.ROOT, FILE), 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

function seedCtx() {
  const ctx = K.makeWorld({});
  K.vm.runInContext('var svSyncSuppressed=false;', ctx);
  K.vm.runInContext(K.grab(SRC, 'function svSeedStore(', ''), ctx);
  return ctx;
}

section('the seed wrapper, under a saver that throws');

test('a normal seed leaves the flag DOWN', () => {
  const ctx = seedCtx();
  ctx.svSeedStore(() => 'ok', [1, 2]);
  assert.strictEqual(ctx.svSyncSuppressed, false);
});

test('and the flag is UP while the saver runs -- or it suppresses nothing', () => {
  // The other direction. A wrapper that never raises the flag would pass every
  // "flag is down afterwards" assertion while doing no work at all, which is
  // the assertion-passing-for-the-wrong-reason shape this platform keeps
  // finding.
  const ctx = seedCtx();
  let seen = null;
  ctx.svSeedStore(() => { seen = ctx.svSyncSuppressed; }, []);
  assert.strictEqual(seen, true, 'the seed ran with the backup NOT suppressed, '
    + 'so demo rows would reach the server');
});

test('A SAVER THAT THROWS still puts the flag back down', () => {
  // The fault: storage full, or a corrupt store, mid-seed. Without the finally
  // the flag stays true and every later write on this device is silently
  // dropped from the backup for the rest of the session.
  const ctx = seedCtx();
  assert.throws(() => ctx.svSeedStore(() => {
    const e = new Error('QuotaExceededError');
    e.name = 'QuotaExceededError';
    throw e;
  }, []), /QuotaExceededError/);
  assert.strictEqual(ctx.svSyncSuppressed, false,
    'the backup is suppressed for the rest of the session after one failed seed');
});

test('...and a SECOND seed after the throw still suppresses correctly', () => {
  // Proves the recovery is real rather than the flag merely reading false: the
  // wrapper has to still work after the fault, not just look clean.
  const ctx = seedCtx();
  try { ctx.svSeedStore(() => { throw new Error('boom'); }, []); } catch (e) { /* */ }
  let seen = null;
  ctx.svSeedStore(() => { seen = ctx.svSyncSuppressed; }, []);
  assert.strictEqual(seen, true);
  assert.strictEqual(ctx.svSyncSuppressed, false);
});

section('EVERY suppression site in the file, not just the one with a test');

test('every `svSyncSuppressed=true` is cleared in a finally', () => {
  // THE STRUCTURAL HALF, and it is what makes this a guard rather than a
  // regression test for one function. A third site added later gets caught
  // here even though nothing drives it, because the shape is the defect.
  //
  // The hydration site is the reason this exists: it set the flag, called
  // st(), and cleared it with no finally, six lines below a wrapper that had
  // one and said why.
  const squashed = SRC.replace(/\s+/g, '');
  const sets = (squashed.match(/svSyncSuppressed=true/g) || []).length;
  assert.ok(sets >= 2, 'expected at least two suppression sites, found ' + sets);
  const guarded = (squashed.match(/svSyncSuppressed=true;try\{/g) || []).length;
  assert.strictEqual(guarded, sets,
    sets - guarded + ' suppression site(s) set the flag without a `try{` '
    + 'immediately after. One throw there silences the backup for the rest of '
    + 'the session and the surrounding .catch swallows the evidence.');
  const cleared = (squashed.match(/finally\{svSyncSuppressed=false/g) || []).length;
  assert.strictEqual(cleared, sets,
    'a suppression site clears the flag outside its finally');
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' SUPPRESSION FAULT ARMS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
