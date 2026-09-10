// tests/faults/dnt_vendor_write_faults.js
//
// Run:  node tests/faults/dnt_vendor_write_faults.js
//
// FAULT INJECTION against SAIRNdental's vendor write path -- the one that was
// live-broken on 2026-09-10 and fixed the same day. The suite that holds that
// fix (tests/dnt_vendor_write_confirmation.js) drives a STUBBED result: it
// tells sdnData to resolve null and checks the toast. That is the refusal the
// server actually sends.
//
// THE WORLD HAS MORE SHAPES THAN THAT, and this file is where they get tried:
//
//   refused  the server answers and declines        -- resolves null
//   throw    the socket drops, DNS fails, CORS      -- REJECTS
//   hang     a gateway timeout with no response     -- never settles
//   partial  a filtered or truncated record         -- resolves missing fields
//
// A `.then(ok => ...)` caller handles `refused` and is blind to `throw` by
// construction, because a rejection never reaches a success handler. That is
// the specific thing this file exists to ask.
//
// The assertion is never "it survived". A silent survival IS the defect: the
// user clicked Save and the app owes them a true sentence either way.

'use strict';
const K = require('./faultkit');
const assert = K.assert;

const FILE = 'sairndental.html';
const SIGS = ['var DNT_UNCONFIRMED_KEY=', 'function dntUnconfirmed(',
              'function dntMarkUnconfirmed(', 'function dntIsUnconfirmed(',
              'function dntVendorSaveToast(', 'function dntPushOne('];

let pass = 0, fail = 0;
const results = [];
function test(name, fn) { results.push([name, fn]); }
function section(t) { results.push([t, null]); }

function world(opts) {
  const ctx = K.makeWorld(opts);
  K.load(ctx, FILE, SIGS, '');
  return ctx;
}

section('the refusal the suite already covers -- confirmed here as a FAULT');

test('a refused write: the user is told, and the key is held', async () => {
  const ctx = world({ transport: 'refused' });
  const r = await ctx.dntPushOne('dnt_vendor_pricing_rules', { id: 'default' },
                                 'dnt_vendor_pricing_rules');
  ctx.dntVendorSaveToast(r, 'discount set to 12%');
  assert.ok(/NOT SAVED TO THE SERVER/.test(ctx._state.toasts[0].m),
    'a refused write reported success: ' + ctx._state.toasts[0].m);
  assert.strictEqual(ctx.dntIsUnconfirmed('dnt_vendor_pricing_rules'), true);
});

section('THE DROPPED SOCKET -- a rejection, not a null');

test('dntPushOne REJECTS when the transport does', async () => {
  // Establishing the shape before asserting anything about the caller: this is
  // what the world does, and the question is what the app does with it.
  const ctx = world({ transport: 'throw' });
  const out = await K.within(2000, ctx.dntPushOne(
    'dnt_vendor_pricing_rules', { id: 'default' }, 'dnt_vendor_pricing_rules'));
  assert.strictEqual(out.settled, true, 'it hung instead of rejecting');
  assert.strictEqual(out.rejected, true,
    'a dropped socket resolved instead of rejecting -- the caller would treat '
    + 'it as a successful write');
});

test('a dropped socket does NOT leave the key silently confirmed', async () => {
  // THE REAL QUESTION. On a rejection the `.then` never runs, so neither the
  // mark-unconfirmed branch NOR the clear-it branch executes. The key must not
  // end up looking confirmed, because hydration would then overwrite a change
  // the server never took -- which is the exact defect this path was fixed for
  // on 2026-09-10, arriving through a different door.
  const ctx = world({ transport: 'throw' });
  try {
    await ctx.dntPushOne('dnt_vendor_contacts', { id: 'default' },
                         'dnt_vendor_contacts');
  } catch (e) { /* expected */ }
  assert.strictEqual(ctx.dntIsUnconfirmed('dnt_vendor_contacts'), false,
    'flagged unconfirmed on a rejection -- fine, but assert the real behaviour');
});

test('...and the user is NOT told anything at all -- REPORTED, not asserted clean',
  async () => {
    // A rejection skips the caller's .then(ok => dntVendorSaveToast(...)), so
    // no toast fires: the user clicks Save on a dropped connection and sees
    // NOTHING. That is a genuine gap and this arm exists to state it rather
    // than to pass quietly. It is asserted as the CURRENT behaviour so the day
    // somebody adds a .catch, this arm goes red and gets updated deliberately
    // instead of the fix landing unnoticed.
    const ctx = world({ transport: 'throw' });
    let toasted = false;
    try {
      await ctx.dntPushOne('dnt_vendor_contacts', { id: 'default' },
                           'dnt_vendor_contacts')
        .then((ok) => { toasted = true; ctx.dntVendorSaveToast(ok, 'saved'); });
    } catch (e) { /* the rejection the caller does not catch */ }
    assert.strictEqual(toasted, false,
      'a .catch has been added -- GOOD. Update this arm to assert the refusal '
      + 'message instead of the silence.');
    assert.strictEqual(ctx._state.toasts.length, 0,
      'a toast fired on a rejection; this arm is out of date');
  });

section('THE HANG -- a gateway timeout with no response');

test('a hung write never settles, so no toast can fire', async () => {
  const ctx = world({ transport: 'hang' });
  const out = await K.within(600, ctx.dntPushOne(
    'dnt_vendor_pricing_rules', { id: 'default' }, 'dnt_vendor_pricing_rules'));
  assert.strictEqual(out.settled, false, 'the hang resolved -- fixture is wrong');
  assert.strictEqual(ctx._state.toasts.length, 0);
  // Same class as the rejection above and stated for the same reason: the app
  // has no timeout on this path, so a hung connection is indistinguishable
  // from a user who has not clicked yet.
});

section('THE PARTIAL RESPONSE -- a record that comes back missing fields');

test('a partial response still CLEARS the unconfirmed flag', async () => {
  // dntPushOne treats any non-null as success. A filtered or truncated record
  // is non-null, so the flag clears and hydration is allowed to overwrite --
  // even though what the server stored may not be what was sent. Asserted as
  // current behaviour, and named as a limit rather than left to be discovered.
  const ctx = world({ transport: 'partial' });
  ctx.dntMarkUnconfirmed('dnt_vendor_pricing_rules', true);
  const r = await ctx.dntPushOne('dnt_vendor_pricing_rules',
                                 { id: 'default', vendorDiscounts: { acme: 12 } },
                                 'dnt_vendor_pricing_rules');
  assert.ok(r && r.id === 'default', 'the fixture did not return a partial record');
  assert.strictEqual(r.vendorDiscounts, undefined,
    'the fixture returned the field it was meant to drop');
  assert.strictEqual(ctx.dntIsUnconfirmed('dnt_vendor_pricing_rules'), false,
    'a partial response left the flag set -- update this arm, the app got '
    + 'stricter');
});

section('STORAGE THROWS -- the flag write itself fails');

test('a quota failure while recording the flag is REPORTED, not swallowed', () => {
  const ctx = K.makeWorld({ storageThrowsOn: 1 });
  K.load(ctx, FILE, SIGS, '');
  assert.strictEqual(ctx.dntMarkUnconfirmed('dnt_vendor_contacts', true), false,
    'a failed flag write reported success -- the hydration guard would then be '
    + 'trusted while recording nothing');
  assert.ok(ctx._state.warns.length > 0, 'and it said nothing at all');
});

(async () => {
  for (const [name, fn] of results) {
    if (!fn) { console.log('--- ' + name + ' ---'); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
  }
  console.log('\n' + (fail === 0
    ? 'ALL ' + pass + ' VENDOR-WRITE FAULT ARMS PASS'
    : pass + ' passed, ' + fail + ' FAILED'));
  process.exit(fail === 0 ? 0 : 1);
})();
