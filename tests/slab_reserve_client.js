// tests/slab_reserve_client.js
// REQUIREMENT: the blind `status = reserved` assignment and its paired
//   reservedFor are gone from the WHOLE file, all three reservation sites go
//   through sdReserveSlab, and the quote is not saved when the reservation is
//   refused
//
//
// Run:  node tests/slab_reserve_client.js
//
// The server-side compare-and-swap is covered by
// api/sd-data-slab-reserve.test.js. This covers the other half: that
// stonedesk.html actually GOES THROUGH it, everywhere, and that the blind
// `status='reserved'` pattern is gone rather than merely bypassed in the one
// place that was noticed.
//
// It is a source-shape test on purpose. The three call sites live inside DOM
// handlers hundreds of lines long that read dozens of element ids; extracting
// them to drive would mean rebuilding half the page, and the property worth
// protecting is not "does this function work once" but "is there any remaining
// path that writes a reservation without asking".

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'stonedesk.html'), 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

// ---------------------------------------------------------------------------
section('no path writes a reservation without asking the server');

test('the blind `status = reserved` assignment is gone from the whole file', () => {
  // The exact shape of the bug: assigning the reserved status to a slab object
  // in page code. Any occurrence is a path that skips the conflict check.
  const blind = html.split(/\r?\n/)
    .filter(l => !/^\s*(\/\/|\*)/.test(l))
    .filter(l => /\.status\s*=\s*['"]reserved['"]/.test(l));
  assert.strictEqual(blind.length, 0,
    'still assigns reserved directly: ' + JSON.stringify(blind));
});

test('and so is the paired reservedFor assignment', () => {
  // Comment lines are excluded: several of them QUOTE the old code to explain
  // what was removed, and a guard that fires on its own documentation would
  // have to be deleted -- taking the guard with it.
  const blind = html.split(/\r?\n/)
    .filter(l => !/^\s*(\/\/|\*)/.test(l))
    .filter(l => /\.reservedFor\s*=\s*[^=]/.test(l));
  assert.strictEqual(blind.length, 0,
    'still assigns reservedFor directly: ' + JSON.stringify(blind));
});

test('all three reservation sites call sdReserveSlab', () => {
  const calls = html.match(/await sdReserveSlab\(/g) || [];
  assert.strictEqual(calls.length, 3,
    'expected the quote, POS and remake paths -- found ' + calls.length);
});

// ---------------------------------------------------------------------------
section('a refusal stops the thing it was refusing');

test('the quote is NOT saved when the reservation is refused', () => {
  const i = html.indexOf('var qbRes = await sdReserveSlab(');
  assert.ok(i > 0, 'the quote path does not reserve');
  const after = html.slice(i, i + 500);
  assert.match(after, /if \(!qbRes\.ok\) \{/);
  assert.match(after, /return;/);
  // The save itself must come after the guard, not before it.
  const save = html.indexOf('quoteHistory.unshift(q);');
  assert.ok(save > i, 'the quote is stored before the reservation is decided');
});

test('THE MONEY ONE: the POS reserves BEFORE the invoice is written', () => {
  const reserve = html.indexOf('var posRes=await sdReserveSlab(');
  const invoice = html.indexOf('sd_invoices.unshift(inv);');
  assert.ok(reserve > 0 && invoice > 0, 'could not find both POS steps');
  assert.ok(reserve < invoice,
    'the sale is recorded before the slab is secured -- a refusal then becomes a refund');
});

test('the POS shows the refusal in its own error line and stops', () => {
  const i = html.indexOf('var posRes=await sdReserveSlab(');
  const after = html.slice(i, i + 300);
  assert.match(after, /if\(!posRes\.ok\)\{/);
  assert.match(after, /errEl\.textContent=posRes\.message;/);
  assert.match(after, /return;/);
});

test('the three callers are async, or the await is a syntax error waiting', () => {
  assert.match(html, /window\.posCompleteSale=async function\(\)\{/);
  assert.match(html, /async function saveQuote\(\) \{/);
  assert.match(html, /async function remakeSave\(\)\{/);
});

// ---------------------------------------------------------------------------
section('the helper refuses rather than guessing');

// EXTRACTS sdSlabHoldCall, NOT sdReserveSlab (2026-09-24). The transport moved
// there when 'release' was added, and sdReserveSlab is now a two-line wrapper
// around it. Slicing the wrapper would have left every assertion below reading
// a function body that no longer contains the thing being asserted.
//
// AND THE EXTRACTION FAILURE IS A REPORTED TEST, NOT A THROW. When the
// signature changed, the bare `assert.ok(s > 0)` at module scope threw out of
// the whole file: node printed a stack, the two sections after this one never
// ran at all, and the process still exited 0 because the throw escaped the
// runner. A test file that cannot find its subject must fail LOUDLY and keep
// going -- the same "could not run is not a pass" rule the gates use.
const ctx = { console };
vm.createContext(ctx);
const HOLD_SIG = 'async function sdSlabHoldCall(action, slab, forWho, holdMinutes){';
const s = html.indexOf(HOLD_SIG);
const e = s < 0 ? -1 : html.indexOf('\n}', s) + 2;
let src = '';
test('the reservation transport is findable in stonedesk.html', () => {
  assert.ok(s > 0 && e > s,
    'could not find `' + HOLD_SIG + '`. It was renamed or its signature '
    + 'changed, and every assertion in this section reads its body -- they '
    + 'would all be reading an empty string. Update HOLD_SIG here.');
});
if (s > 0 && e > s) {
  src = html.slice(s, e);
  vm.runInContext('var sdLicenseKey = function(){ return ctxLic; };\nvar ctxLic = "LIC";\n'
    + src
    + '\nasync function sdReserveSlab(a,b,c){ return sdSlabHoldCall("reserve",a,b,c); }'
    + '\nasync function sdReleaseSlab(a,b){ return sdSlabHoldCall("release",a,b); }', ctx);
}

test('no slab -> refused, and never calls the network', async () => {
  ctx.fetch = () => { throw new Error('must not be called'); };
  return ctx.sdReserveSlab(null, 'Chen').then(r => {
    assert.strictEqual(r.ok, false);
    assert.strictEqual(r.code, 'NO_SLAB');
  });
});

test('no customer name -> refused before any request', async () => {
  ctx.fetch = () => { throw new Error('must not be called'); };
  return ctx.sdReserveSlab({ id: 'S1' }, '  ').then(r => {
    assert.strictEqual(r.ok, false);
    assert.strictEqual(r.code, 'NO_HOLDER');
  });
});

test('OFFLINE IS A REFUSAL, NOT A LOCAL RESERVATION', () => {
  // The tempting failure: "the server is unreachable, reserve it locally and
  // sync later". An unreachable server cannot tell you the slab is free, and
  // reserving on that basis is the double-sale with extra steps.
  assert.match(src, /code:'OFFLINE'/);
  assert.ok(!/catch\s*\(e\)\s*\{[^}]*status\s*=\s*['"]reserved['"]/.test(src),
    'the catch path reserves locally');
});

test('a 409 is surfaced with the server\'s own message, not a generic one', () => {
  assert.match(src, /message:err\.message\|\|/);
});

test('success adopts the SERVER\'s row rather than a locally-guessed one', () => {
  assert.match(src, /sdSlabs\[i\]=j\.data/);
});

// ---------------------------------------------------------------------------
section('the picker no longer claims a slab is held when it is not');

test('the chip says Selected, not Reserved', () => {
  assert.ok(!html.includes('📦 Reserved:'),
    'the picker still tells the user a slab is Reserved at pick time');
  assert.strictEqual((html.match(/📦 Selected: <b>/g) || []).length, 2,
    'expected the quote and POS chips to both say Selected');
});

// ---------------------------------------------------------------------------
section('the hold expires, and this file does not get a vote on when');

// A fetch stand-in that records the request and answers with a slab row.
function captureFetch(reply) {
  const seen = [];
  ctx.fetch = async (url, init) => {
    seen.push(JSON.parse(init.body));
    return { ok: true, status: 200, json: async () => reply };
  };
  ctx.sdSlabs = [];
  ctx.saveSlabs = function () {};
  return seen;
}

test('a quote reservation asks for a WINDOW, not an open-ended hold', () => {
  // The whole defect being fixed is a hold nobody ever clears. If the quote
  // path stops sending holdMinutes it silently reverts to the server default,
  // which is not wrong but is no longer a decision anyone made here.
  const i = html.indexOf('var qbRes = await sdReserveSlab(');
  assert.ok(i > 0, 'the quote path does not reserve');
  assert.match(html.slice(i, i + 260), /SD_HOLD_MINUTES_QUOTE/,
    'the quote path no longer asks for a hold window');
  assert.match(html, /var SD_HOLD_MINUTES_QUOTE\s*=\s*\d+;/,
    'SD_HOLD_MINUTES_QUOTE is referenced but never defined');
});

test('holdMinutes reaches the wire on a reserve', async () => {
  const seen = captureFetch({ ok: true, data: { id: 'S1', status: 'reserved' } });
  return ctx.sdReserveSlab({ id: 'S1' }, 'Chen', 45).then(() => {
    assert.strictEqual(seen.length, 1);
    assert.strictEqual(seen[0].action, 'reserve');
    assert.strictEqual(seen[0].payload.holdMinutes, 45);
  });
});

test('...and is NEVER sent on a release, even if the slab object carries one', async () => {
  const seen = captureFetch({ ok: true, data: { id: 'S1', status: 'in-stock' }, released: true });
  return ctx.sdReleaseSlab({ id: 'S1', holdMinutes: 999 }, 'Chen').then(() => {
    assert.strictEqual(seen[0].action, 'release');
    assert.strictEqual(seen[0].payload.holdMinutes, undefined,
      'a stale holdMinutes rode along on a release');
  });
});

test('THE ONE THAT MATTERS: this file never decides a hold has expired', () => {
  // sdHoldMinutesLeft/sdHoldLabel exist for DISPLAY. If either one ever gated a
  // write -- "it looks expired, so reserve it" -- a device with a fast clock
  // could take a live hold, which is the double-sale with a clock-skew step.
  // The server recomputes on every reserve and is the only opinion that counts.
  const callers = html.split(/\r?\n/)
    .filter(l => !/^\s*(\/\/|\*)/.test(l))
    .filter(l => /sdHoldMinutesLeft\s*\(/.test(l) || /sdHoldLabel\s*\(/.test(l));
  assert.ok(callers.length > 0, 'the display helpers are defined and never used');
  const writers = callers.filter(l =>
    /sdReserveSlab|sdReleaseSlab|sdSlabHoldCall|sdData\s*\(/.test(l));
  assert.deepStrictEqual(writers, [],
    'a hold-expiry judgement is feeding a write: ' + JSON.stringify(writers));
});

test('an expiring hold is DISPLAYED, or the feature is invisible to the yard', () => {
  // A hold that lapses silently is the same as no hold at all: the row still
  // reads "Allocated" and nobody goes near the slab.
  assert.match(html, /Hold lapsed/, 'no lapsed state is ever shown');
  assert.match(html, /HOLD LAPSED/, 'the slab detail card never says the hold ran out');
  assert.match(html, /function sdHoldLabel\(/, 'there is no way to render time remaining');
});

test('a takeover is surfaced to the salesperson, not swallowed', () => {
  const i = html.indexOf('var qbRes = await sdReserveSlab(');
  assert.match(html.slice(i, i + 1400), /qbRes\.tookOverFrom/,
    'the quote path takes a lapsed slab from another customer and says nothing');
});

test('a release that the server refused does NOT clear the local row', () => {
  // Clearing locally on a refusal shows the slab free on this device while
  // another device still sees the hold -- the split-brain the whole
  // reservation system exists to avoid.
  const i = html.indexOf('async function qbReleaseQuoteHold(');
  assert.ok(i > 0, 'the release path is gone');
  const body = html.slice(i, i + 1200);
  const guard = body.indexOf('if (!r.ok)');
  const clear = body.indexOf('q.reservedSlabId = null;');
  assert.ok(guard > 0 && clear > guard,
    'the local row is cleared before the server answer is checked');
  assert.match(body.slice(guard, clear), /return;/,
    'the refusal path falls through into clearing the row anyway');
});

Promise.resolve().then(() => {
  console.log('\n' + (fail === 0
    ? 'ALL ' + pass + ' SLAB-RESERVE-CLIENT ASSERTIONS PASS'
    : pass + ' passed, ' + fail + ' FAILED'));
  process.exit(fail === 0 ? 0 : 1);
});
