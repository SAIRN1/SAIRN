// tests/slab_reserve_client.js
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

const ctx = { console };
vm.createContext(ctx);
const s = html.indexOf('async function sdReserveSlab(slab, forWho){');
const e = html.indexOf('\n}', s) + 2;
assert.ok(s > 0 && e > s, 'sdReserveSlab not found in stonedesk.html');
vm.runInContext('var sdLicenseKey = function(){ return ctxLic; };\nvar ctxLic = "LIC";\n' + html.slice(s, e), ctx);

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
  const src = html.slice(s, e);
  assert.match(src, /code:'OFFLINE'/);
  assert.ok(!/catch\s*\(e\)\s*\{[^}]*status\s*=\s*['"]reserved['"]/.test(src),
    'the catch path reserves locally');
});

test('a 409 is surfaced with the server\'s own message, not a generic one', () => {
  const src = html.slice(s, e);
  assert.match(src, /message:err\.message\|\|/);
});

test('success adopts the SERVER\'s row rather than a locally-guessed one', () => {
  const src = html.slice(s, e);
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

Promise.resolve().then(() => {
  console.log('\n' + (fail === 0
    ? 'ALL ' + pass + ' SLAB-RESERVE-CLIENT ASSERTIONS PASS'
    : pass + ' passed, ' + fail + ' FAILED'));
  process.exit(fail === 0 ? 0 : 1);
});
