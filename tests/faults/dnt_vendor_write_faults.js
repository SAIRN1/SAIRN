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
const SIGS = ['var DNT_UNCONFIRMED_KEY=', 'var DNT_PUSH_TIMEOUT =',
              'var DNT_PUSH_REJECTED =', 'var DNT_PUSH_TIMEOUT_MS =',
              'function dntUnconfirmed(',
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

test('dntPushOne does NOT reject -- it converts the drop into a refusal',
  async () => {
    // INVERTED with the fix. This arm established the raw shape: the transport
    // REJECTS, and a rejection never reaches a `.then(ok => ...)`. That was
    // true of dntPushOne too, so two callers that attach no handler at all
    // (dnt_supplies, dnt_vendor_orders) produced UNHANDLED REJECTIONS as well
    // as silence.
    //
    // It now settles to `null` -- the one shape every caller already
    // understands. Asserting "does not reject" is the load-bearing half: a
    // caller cannot be blind to a value it is handed.
    const ctx = world({ transport: 'throw' });
    const out = await K.within(2000, ctx.dntPushOne(
      'dnt_vendor_pricing_rules', { id: 'default' }, 'dnt_vendor_pricing_rules'));
    assert.strictEqual(out.settled, true, 'it hung instead of settling');
    assert.ok(!out.rejected,
      'a dropped socket still rejects, so a .then-only caller sees nothing');
    assert.strictEqual(out.value, null, 'the drop did not arrive as a refusal');
  });

test('an unkeyed caller survives a drop too -- no unhandled rejection',
  async () => {
    // dnt_supplies and dnt_vendor_orders call dntPushOne and attach NOTHING.
    // Before the fix that was an unhandled rejection on every dropped
    // connection; now it is a resolved null they are free to ignore.
    const ctx = world({ transport: 'throw' });
    const out = await K.within(2000, ctx.dntPushOne('dnt_supplies', { id: 'x' }));
    assert.strictEqual(out.settled, true);
    assert.ok(!out.rejected, 'an unkeyed caller still gets an unhandled rejection');
    assert.strictEqual(out.value, null);
  });

test('a dropped socket leaves the key UNCONFIRMED, so hydration cannot overwrite',
  async () => {
    // Also inverted. Before the fix neither branch ran on a rejection, so the
    // key kept whatever state it had -- which for a first edit is "confirmed",
    // and hydration was then free to replace a change the server never took.
    const ctx = world({ transport: 'throw' });
    await ctx.dntPushOne('dnt_vendor_contacts', { id: 'default' },
                         'dnt_vendor_contacts');
    assert.strictEqual(ctx.dntIsUnconfirmed('dnt_vendor_contacts'), true,
      'a dropped socket left the key confirmed');
  });

section('THE HANG -- a gateway timeout with no response');

test('a hung write TIMES OUT into a refusal instead of never settling',
  async () => {
    // ALSO INVERTED ON PURPOSE. This arm recorded that a hang never settles,
    // so no toast could fire and the user could not tell a dead connection
    // from not having clicked. dntPushOne now races the write against
    // DNT_PUSH_TIMEOUT_MS. The timeout is shortened here rather than waiting
    // fifteen seconds -- the harness overrides the constant it loaded, which
    // is only honest because it loaded the REAL one first.
    const ctx = world({ transport: 'hang' });
    ctx.DNT_PUSH_TIMEOUT_MS = 200;
    const out = await K.within(3000, ctx.dntPushOne(
      'dnt_vendor_pricing_rules', { id: 'default' }, 'dnt_vendor_pricing_rules'));
    assert.strictEqual(out.settled, true, 'it still hangs forever');
    assert.strictEqual(out.value, null, 'the timeout did not arrive as a refusal');
    assert.strictEqual(ctx.dntIsUnconfirmed('dnt_vendor_pricing_rules'), true);
    assert.ok(ctx._state.warns.some((w) => /no answer in/.test(w)),
      'the console does not say it timed out');
  });

test('...and the REAL timeout is a sane wait, not a hidden zero', () => {
  // The override above is only safe while the shipped value is a real one. A
  // constant of 0 would make every write on a slow connection a false refusal.
  const ctx = world({});
  assert.ok(ctx.DNT_PUSH_TIMEOUT_MS >= 5000 && ctx.DNT_PUSH_TIMEOUT_MS <= 60000,
    'the shipped timeout is ' + ctx.DNT_PUSH_TIMEOUT_MS + 'ms');
});

section('THE PARTIAL RESPONSE -- a record that comes back missing fields');

test('a partial response does NOT clear the unconfirmed flag', async () => {
    // THE THIRD INVERSION. dntPushOne treated any non-null as success, so a
    // filtered or truncated record cleared the flag and hydration was free to
    // overwrite the local copy with whatever the server actually kept.
    //
    // DELIBERATELY NOT A USER-FACING REFUSAL. A short response may still have
    // been stored correctly, and turning that into "NOT SAVED" would be a
    // false alarm. It does the one unambiguously right thing instead: it
    // leaves the key unconfirmed so nothing can overwrite it. Conservative on
    // the visible half, strict on the destructive half.
    const ctx = world({ transport: 'partial' });
    const r = await ctx.dntPushOne('dnt_vendor_pricing_rules',
                                   { id: 'default', vendorDiscounts: { acme: 12 } },
                                   'dnt_vendor_pricing_rules');
    assert.ok(r && r.id === 'default', 'the record was refused outright -- too strict');
    assert.strictEqual(r.vendorDiscounts, undefined,
      'the fixture returned the field it was meant to drop');
    assert.strictEqual(ctx.dntIsUnconfirmed('dnt_vendor_pricing_rules'), true,
      'a partial response cleared the flag, so hydration may overwrite');
    assert.ok(ctx._state.warns.some((w) => /came back WITHOUT/.test(w)),
      'it did not say which fields were missing');
  });

test('a COMPLETE response does clear it -- the check is not just always-on',
  async () => {
    // The other direction, and the reason it matters: a missing-key test that
    // never passes would make every write permanently unconfirmed, which reads
    // as caution and behaves as a broken sync.
    const ctx = world({});
    ctx.dntMarkUnconfirmed('dnt_vendor_contacts', true);
    await ctx.dntPushOne('dnt_vendor_contacts', { id: 'default', vendors: {} },
                         'dnt_vendor_contacts');
    assert.strictEqual(ctx.dntIsUnconfirmed('dnt_vendor_contacts'), false);
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
