// tests/dnt_vendor_write_confirmation.js
//
// Run:  node tests/dnt_vendor_write_confirmation.js
//
// SAIRNdental's two WHOLESALE vendor objects -- dnt_vendor_pricing_rules and
// dnt_vendor_contacts -- are replaced entire on both sides. That is the right
// call: it is what makes a REMOVAL expressible, which a merge cannot do.
//
// It also made this shape possible, and sql/sairndental_vendor_schema.sql has
// been RUN, so it was live:
//
//     st('dnt_vendor_pricing_rules', rules);
//     dntPushVendorPricing(rules);                      // not awaited
//     toast('... discount set to 12%');                 // unconditional
//
// dntPushOne() reported a failed write with a console.warn and nothing else,
// and dntSyncFromServer() writes the server's copy straight over the local one
// -- server-wins, no guard. So: set a discount, push fails, the toast says it
// worked, and THE NEXT SYNC PUTS THE OLD NUMBER BACK. dnt_settings is the
// precedent for wholesale-write and there this costs a preference. Here it is
// a negotiated vendor discount, so it changes what the practice pays.
//
// TWO HALVES, and this file drives both:
//   1. the toast is DERIVED from the push result;
//   2. hydration does not overwrite an object whose last write was refused.
//
// The persisted flag is the part worth attacking: a reload must not turn "the
// server never took this" back into "the server agrees", which is exactly what
// a console.warn left behind the moment the tab closed.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const FILE = 'sairndental.html';
const SRC = fs.readFileSync(path.join(ROOT, FILE), 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

// Top-level functions here are 0-indented and terminated by a bare `}`.
// The single place this file splits a line out of the source. Repeating a
// regex literal at each call site is how one of them ends up wrong.
function firstLine(sig) {
  return SRC.slice(SRC.indexOf(sig)).split(/\r?\n/)[0];
}

function grab(sig) {
  const i = SRC.indexOf(sig);
  assert.ok(i > 0, sig + ' not found in ' + FILE);
  const rel = SRC.slice(i).search(/\r?\n\}/);
  assert.ok(rel > 0, sig + ' is not terminated');
  return SRC.slice(i, i + rel) + '\n}';
}

// A localStorage that can be made to fail, so the flag's own write path is
// driven rather than assumed.
function makeCtx(writeOk) {
  const store = {};
  const toasts = [];
  const ctx = {
    JSON: JSON, Date: Date, Object: Object, Array: Array, console: { warn() {} },
    localStorage: {
      getItem: (k) => (k in store ? store[k] : null),
      setItem: (k, v) => {
        if (writeOk === false) { const e = new Error('QuotaExceededError'); throw e; }
        store[k] = String(v);
      },
    },
    toast: (m, d) => toasts.push({ m: m, d: d }),
    _store: store,
    _toasts: toasts,
  };
  vm.createContext(ctx);
  ['var DNT_UNCONFIRMED_KEY=', 'function dntUnconfirmed(', 'function dntMarkUnconfirmed(',
   'function dntIsUnconfirmed(', 'function dntVendorSaveToast('].forEach((sig) => {
    if (sig.startsWith('var ')) {
      const line = SRC.slice(SRC.indexOf(sig)).split(/\r?\n/)[0];
      vm.runInContext(line, ctx);
    } else {
      vm.runInContext(grab(sig), ctx);
    }
  });
  // dntPushOne needs sdnData; it is stubbed per test.
  return ctx;
}

section('the flag is real, and it survives a reload');

test('an unconfirmed key is remembered', () => {
  const ctx = makeCtx();
  assert.strictEqual(ctx.dntIsUnconfirmed('dnt_vendor_pricing_rules'), false);
  ctx.dntMarkUnconfirmed('dnt_vendor_pricing_rules', true);
  assert.strictEqual(ctx.dntIsUnconfirmed('dnt_vendor_pricing_rules'), true);
});

test('and it is PERSISTED, not held in a variable', () => {
  // The whole point: a console.warn vanished when the tab closed, turning
  // "the server never took this" back into "the server agrees".
  const ctx = makeCtx();
  ctx.dntMarkUnconfirmed('dnt_vendor_contacts', true);
  const raw = ctx._store['dnt_unconfirmed_writes'];
  assert.ok(raw && raw.indexOf('dnt_vendor_contacts') !== -1,
    'the flag did not reach localStorage: ' + raw);
  // A fresh context reading the SAME store is the reload.
  const after = makeCtx();
  after._store['dnt_unconfirmed_writes'] = raw;
  assert.strictEqual(after.dntIsUnconfirmed('dnt_vendor_contacts'), true,
    'the flag did not survive a reload');
});

test('clearing it removes only that key', () => {
  const ctx = makeCtx();
  ctx.dntMarkUnconfirmed('dnt_vendor_contacts', true);
  ctx.dntMarkUnconfirmed('dnt_vendor_pricing_rules', true);
  ctx.dntMarkUnconfirmed('dnt_vendor_contacts', false);
  assert.strictEqual(ctx.dntIsUnconfirmed('dnt_vendor_contacts'), false);
  assert.strictEqual(ctx.dntIsUnconfirmed('dnt_vendor_pricing_rules'), true,
    'clearing one key cleared the other');
});

test('a corrupt flag value does not throw and does not falsely hold', () => {
  const ctx = makeCtx();
  ctx._store['dnt_unconfirmed_writes'] = '{not json';
  assert.strictEqual(ctx.dntIsUnconfirmed('dnt_vendor_contacts'), false);
});

test('a storage failure is REPORTED, not swallowed', () => {
  // If the flag itself cannot be written, the hydration guard cannot protect
  // anything, and saying so is the only honest option.
  const ctx = makeCtx(false);
  assert.strictEqual(ctx.dntMarkUnconfirmed('dnt_vendor_contacts', true), false);
});

section('the toast is DERIVED from the push result');

test('a refused push says NOT SAVED and names the consequence', () => {
  const ctx = makeCtx();
  ctx.dntVendorSaveToast(null, 'Acme vendor discount set to 12%');
  assert.strictEqual(ctx._toasts.length, 1);
  const m = ctx._toasts[0].m;
  assert.ok(/NOT SAVED TO THE SERVER/.test(m), m);
  assert.ok(/THIS DEVICE only/.test(m), 'it does not say where the record is: ' + m);
  assert.ok(ctx._toasts[0].d >= 6000, 'a failure toast must outlast a success one');
});

test('a successful push says the ordinary thing', () => {
  const ctx = makeCtx();
  ctx.dntVendorSaveToast({ id: 'default' }, 'Acme vendor discount set to 12%');
  assert.strictEqual(ctx._toasts[0].m, 'Acme vendor discount set to 12%');
});

section('dntPushOne marks and clears the key it was given');

function pushCtx(result) {
  const ctx = makeCtx();
  ctx.sdnData = () => Promise.resolve(result);
  ctx.Promise = Promise;
  // dntPushOne gained a TIMEOUT and two sentinels on 2026-09-10, when fault
  // injection found that a dropped socket and a hang both produced silence.
  // The harness has to supply what the real function now needs: omitting
  // setTimeout made every arm below CRASH rather than fail, which reads as a
  // broken suite instead of a missing dependency -- and a crash after the last
  // printed `ok` is easy to mistake for a pass.
  ctx.setTimeout = setTimeout;
  ['var DNT_PUSH_TIMEOUT =', 'var DNT_PUSH_REJECTED =',
   'var DNT_PUSH_TIMEOUT_MS ='].forEach((sig) => {
    vm.runInContext(firstLine(sig), ctx);
  });
  vm.runInContext(grab('function dntPushOne('), ctx);
  return ctx;
}

test('a refused write marks the store key unconfirmed', async () => {
  const ctx = pushCtx(null);
  await ctx.dntPushOne('dnt_vendor_pricing_rules', { id: 'default' },
                       'dnt_vendor_pricing_rules');
  assert.strictEqual(ctx.dntIsUnconfirmed('dnt_vendor_pricing_rules'), true);
});

test('a later SUCCESS clears it -- the guard must not be permanent', async () => {
  const ctx = pushCtx(null);
  await ctx.dntPushOne('dnt_vendor_contacts', { id: 'default' }, 'dnt_vendor_contacts');
  assert.strictEqual(ctx.dntIsUnconfirmed('dnt_vendor_contacts'), true);
  ctx.sdnData = () => Promise.resolve({ id: 'default' });
  await ctx.dntPushOne('dnt_vendor_contacts', { id: 'default' }, 'dnt_vendor_contacts');
  assert.strictEqual(ctx.dntIsUnconfirmed('dnt_vendor_contacts'), false,
    'a successful write did not clear the flag, so hydration would be blocked forever');
});

// ADDED 2026-09-11, and it was found by a PROBE ANCHOR THAT HAD DRIFTED. The
// probe's arm 3 was aimed at the refused branch and its anchor had moved onto
// THIS branch instead -- the response-came-back-incomplete one. The anchor still
// matched exactly once, so the harness saw no error; it silently probed a branch
// this suite never asserted. Re-anchoring arm 3 back where it belonged left this
// branch uncovered and the probe immediately said SILENT, which is how the gap
// surfaced at all.
//
// THE BRANCH MATTERS AS MUCH AS THE OTHER TWO. dntPushOne() compares the keys of
// the record it SENT against the object that came back, and a reply that is
// missing any of them is not a confirmation. Without this the flag would be
// cleared on a 200 that silently dropped a field, and the next hydration would
// overwrite the local copy with a server row that never received it.
test('a reply MISSING a field that was sent does not count as confirmation', async () => {
  // 200, well-formed, and short one key. This is the shape a partial write or a
  // schema drift produces -- not an error, just an answer that agrees with less
  // than it was asked to store.
  const ctx = pushCtx(null);
  ctx.sdnData = () => Promise.resolve({ id: 'default' });
  await ctx.dntPushOne('dnt_vendor_pricing_rules',
                       { id: 'default', discount: 12 }, 'dnt_vendor_pricing_rules');
  assert.strictEqual(ctx.dntIsUnconfirmed('dnt_vendor_pricing_rules'), true,
    'a reply without `discount` was treated as a confirmation, so the next sync would overwrite it');
});

test('CONTROL: a reply carrying every field sent DOES confirm', async () => {
  // The control that makes the test above mean something: if the flag were set
  // on every write regardless, the assertion would pass while checking nothing.
  const ctx = pushCtx(null);
  ctx.sdnData = () => Promise.resolve({ id: 'default', discount: 12 });
  await ctx.dntPushOne('dnt_vendor_pricing_rules',
                       { id: 'default', discount: 12 }, 'dnt_vendor_pricing_rules');
  assert.strictEqual(ctx.dntIsUnconfirmed('dnt_vendor_pricing_rules'), false,
    'a complete reply left the key unconfirmed, which would block hydration forever');
});

test('a caller that passes no store key is unaffected', async () => {
  // Every other dntPushOne caller in the file has no wholesale object to
  // protect and must behave exactly as before.
  const ctx = pushCtx(null);
  await ctx.dntPushOne('dnt_supplies', { id: 'x' });
  assert.deepStrictEqual(ctx.dntUnconfirmed(), {});
});

section('the four writers, and hydration, asserted on the source');

test('no vendor writer toasts before the push result is known', () => {
  // The exact defect: st(...); push(...); toast('set') with nothing awaited.
  const squashed = SRC.replace(/\s+/g, '');
  assert.ok(!/dntPushVendorPricing\(rules\);rVendorCat\(\);toast\(/.test(squashed),
    'a pricing writer still toasts unconditionally after an unawaited push');
  assert.ok(!/dntPushVendorContacts\(contacts\);vRenderContactBox\(\);toast\(/.test(squashed),
    'the contacts writer still toasts unconditionally after an unawaited push');
});

test('all four writers route their toast through dntVendorSaveToast', () => {
  // CALL SITES ONLY. The first version counted `dntVendorSaveToast(ok,` and
  // got 5, because the helper's own DEFINITION has that exact signature -- an
  // assertion counting the thing plus itself. Excluding `function ` is the
  // difference between "four writers use it" and "it exists".
  const n = (SRC.match(/(?<!function\s)dntVendorSaveToast\(ok,/g) || []).length;
  assert.strictEqual(n, 4, 'expected 4 result-derived toasts, found ' + n);
});

test('both wholesale hydrations check the flag BEFORE overwriting', () => {
  // ANCHORED ON `if(` -- the guard's POSITION, not merely its presence. The
  // first version matched what came after the call, so a mutation to
  // `if(false&&dntIsUnconfirmed(...))` left it GREEN while the behaviour was
  // gone. Asserting a mechanism exists where the requirement is that it is
  // CONSULTED is scrubber item 16, and the mutation probe is what found it.
  const squashed = SRC.replace(/\s+/g, '');
  assert.ok(/if\(dntIsUnconfirmed\('dnt_vendor_contacts'\)\)\{unconfirmedHeld/.test(squashed),
    'contacts hydration does not consult the flag as its first condition');
  assert.ok(/if\(dntIsUnconfirmed\('dnt_vendor_pricing_rules'\)\)\{unconfirmedHeld/.test(squashed),
    'pricing hydration does not consult the flag as its first condition');
});

test('a held key is REPORTED by the refresh, not silently skipped', () => {
  assert.ok(/unconfirmed_held:unconfirmedHeld/.test(SRC),
    'the sync result does not carry the held keys');
  // Same lesson: anchored on the whole condition INCLUDING `if(result&&`, so
  // `if(false&&result.unconfirmed_held...)` cannot satisfy it.
  assert.ok(/\}elseif\(result&&result\.unconfirmed_held&&result\.unconfirmed_held\.length\)\{/.test(
    SRC.replace(/\s+/g, '')), 'no caller reads unconfirmed_held as a live branch');
  assert.ok(/NOT reached the server, so the server copy was not/.test(
    SRC.replace(/\s+/g, ' ')), 'the refresh does not say what it did');
});

test('the flag key is NOT a synced resource', () => {
  // It is a fact about THIS device's relationship to the server. A merged copy
  // of it would be meaningless, and syncing it would let one workstation
  // silence another's guard.
  const i = SRC.indexOf('DNT_SYNC_RESOURCES');
  assert.ok(i > 0);
  const block = SRC.slice(i, i + 4000);
  assert.ok(block.indexOf('dnt_unconfirmed_writes') === -1,
    'the guard flag is in the sync registry');
});

(async () => {
  // The async tests above register synchronously; give them a tick to settle.
  await new Promise((r) => setTimeout(r, 50));
  console.log('\n' + (fail === 0
    ? 'ALL ' + pass + ' VENDOR WRITE-CONFIRMATION ASSERTIONS PASS'
    : pass + ' passed, ' + fail + ' FAILED'));
  process.exit(fail === 0 ? 0 : 1);
})();
