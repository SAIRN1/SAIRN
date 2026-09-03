// tests/sairnscape_memory.js
//
// Run:  node tests/sairnscape_memory.js
//
// SAIRNscape's memory, which was SOLD and did not work.
//
// The marketing page carried a feature card -- "Claude remembers every
// property, every client, every issue" -- and the pricing table carried a line
// item, "Memory across all properties and clients". What actually shipped:
//
//   * cloudSaveMemory() wrote to localStorage on every reply, and also POSTed
//     to https://sairn.vercel.app/api/memory-cloud;
//   * api/memory-cloud DOES NOT EXIST -- probed live 2026-09-03, 404 -- and the
//     failure was swallowed by a catch whose comment read
//     "Cloud save failed - local backup is enough";
//   * cloudLoadMemory() and loadUserMemory() were DEFINED AND NEVER CALLED,
//     zero call sites, so the local backup was never enough because nothing
//     ever read it;
//   * the system prompt was `SYSTEM + orgContext` and contained no memory at
//     all.
//
// So the assistant had never seen a single remembered fact. Nothing threw,
// nothing logged, and the page kept selling it. These tests exist because that
// is not a bug a screenshot or a green suite would ever show.
//
// The functions are lifted out of the real page rather than reimplemented.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'sairnscape.html'), 'utf8').replace(/\r\n/g, '\n');

// Tests are QUEUED and awaited in order rather than fired off. The first
// version let async tests settle whenever they liked: they passed, but they
// reported out of order and a rejection landing after process exit would have
// been counted as nothing at all. A suite that can silently lose a failure is
// the same shape as the bug this file is about.
let pass = 0, fail = 0;
const QUEUE = [];
function test(name, fn) { QUEUE.push({ name, fn }); }
function section(t) { QUEUE.push({ section: t }); }

async function run() {
  for (const item of QUEUE) {
    if (item.section) { console.log('--- ' + item.section + ' ---'); continue; }
    try { await item.fn(); console.log('  ok   ' + item.name); pass++; }
    catch (e) { console.log('  FAIL ' + item.name + '\n       ' + e.message); fail++; }
  }
}

function slice(start, end) {
  const a = html.indexOf(start);
  assert.ok(a > 0, 'not found in sairnscape.html: ' + start);
  const b = html.indexOf(end, a);
  assert.ok(b > a, 'end marker not found after: ' + start);
  return html.slice(a, b);
}

const memSrc = slice('async function cloudSaveMemory(', '// ── VOICE MODE');

function harness(opts) {
  opts = opts || {};
  const store = Object.assign({}, opts.store || {});
  const posts = [];
  const gets = [];
  const ctx = {
    console, JSON, Date, Promise, Array, String,
    APP_ID: 'sairnscape',
    SAIRN_USER_ID: 'u-123',
    sessionOutcomes: { saved: 0 },
    localStorage: {
      getItem: (k) => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); },
      removeItem: (k) => { delete store[k]; }
    },
    fetch: (url, init) => {
      if (init && init.method === 'POST') { posts.push({ url, body: JSON.parse(init.body) }); }
      else { gets.push({ url }); }
      if (opts.cloudDead !== false) return Promise.reject(new Error('404 — api/memory-cloud does not exist'));
      return Promise.resolve({ json: () => Promise.resolve(opts.cloudBody || { entries: [] }) });
    },
    __store: store, __posts: posts, __gets: gets
  };
  vm.createContext(ctx);
  vm.runInContext(memSrc, ctx);
  return ctx;
}

console.log('sairnscape memory');

// ── THE FIX: IT IS READ ────────────────────────────────────────────────────
section('memory is written AND read -- the half that was missing');

test('a saved reply comes back out of cloudLoadMemory', async () => {
  const c = harness();
  await c.cloudSaveMemory('The Hartley property has a broken irrigation zone on the east bed.');
  const out = await c.cloudLoadMemory();
  assert.match(out, /Hartley property/);
  assert.match(out, /Recent context/, 'it did not fall back to the local store');
});

test('the local store really is what backs it', async () => {
  const c = harness();
  await c.cloudSaveMemory('Delgado wants the hedges cut back before the HOA walkthrough.');
  const raw = c.__store['sairn_local_sairnscape'];
  assert.ok(raw, 'nothing was written locally');
  assert.match(JSON.parse(raw)[0].text, /Delgado/);
});

test('the newest entries come first, and it is capped', async () => {
  const c = harness();
  for (let i = 0; i < 120; i++) await c.cloudSaveMemory('note number ' + i + ' about a property');
  const rows = JSON.parse(c.__store['sairn_local_sairnscape']);
  assert.strictEqual(rows.length, 100, 'the 100-entry cap is not holding');
  assert.match(rows[0].text, /number 119/);
  const out = await c.cloudLoadMemory();
  assert.match(out, /number 119/);
  assert.ok(out.indexOf('number 0 ') === -1, 'it returned more than the recent slice');
});

test('nothing saved -> empty string, not the word "undefined"', async () => {
  const c = harness();
  assert.strictEqual(await c.cloudLoadMemory(), '');
});

test('a dead cloud endpoint does NOT suppress the local answer', async () => {
  // The whole failure mode: the cloud leg 404s, and before this the catch
  // simply returned nothing at all.
  const c = harness({ cloudDead: true });
  await c.cloudSaveMemory('The Whitfield addition failed rough electrical inspection.');
  const out = await c.cloudLoadMemory();
  assert.match(out, /Whitfield/, 'a 404 on the cloud leg swallowed the local memory');
});

test('a live cloud endpoint would be preferred over local', async () => {
  // Proves the fallback is a fallback and not the only path -- which is what
  // step 2 of this work depends on.
  const c = harness({ cloudDead: false, cloudBody: { entries: [{ content: 'from the server' }] } });
  await c.cloudSaveMemory('a local note about a property that is long enough');
  const out = await c.cloudLoadMemory();
  assert.match(out, /from the server/);
  assert.match(out, /previous sessions/);
});

test('short scraps are not saved as memory', async () => {
  const c = harness();
  await c.cloudSaveMemory('ok');
  await c.cloudSaveMemory('');
  assert.strictEqual(c.__store['sairn_local_sairnscape'], undefined);
});

// ── THE WIRING ─────────────────────────────────────────────────────────────
section('and it actually reaches the model');

test('cloudLoadMemory is CALLED, not merely defined', () => {
  // It was defined and never called for the entire life of the feature. That
  // is the assertion this file exists for.
  const defs = html.split('async function cloudLoadMemory(').length - 1;
  const uses = html.split('cloudLoadMemory(').length - 1;
  assert.strictEqual(defs, 1);
  assert.ok(uses > defs, 'cloudLoadMemory is defined but never called');
});

test('its result is prepended to the system prompt', () => {
  const at = html.indexOf('const memoryContext = await cloudLoadMemory();');
  assert.ok(at > 0, 'the memory is not loaded where the prompt is built');
  const window = html.slice(at, at + 500);
  assert.match(window, /system:\s*SYSTEM \+ orgContext \+ \(memoryContext/,
    'memory is loaded and then not put in the prompt');
});

test('an empty memory adds nothing to the prompt, not a stray blank block', () => {
  const at = html.indexOf('system: SYSTEM + orgContext + (memoryContext');
  const line = html.slice(at, html.indexOf('\n', at));
  assert.match(line, /memoryContext \? /, 'it concatenates unconditionally');
});

// ── THE CLAIM MATCHES WHAT SHIPS ───────────────────────────────────────────
section('the copy says what the code does');

test('the pricing line no longer promises cross-device memory', () => {
  assert.strictEqual(html.indexOf('Memory across all properties and clients'), -1,
    'the pricing table still claims memory across all properties and clients, ' +
    'which is cross-device and is not what ships');
  assert.ok(html.indexOf('on this device') > 0, 'the corrected pricing line is missing');
});

test('the feature card no longer claims it remembers EVERYTHING', () => {
  assert.strictEqual(html.indexOf('Claude remembers every property, every client, every issue'), -1,
    'the feature card still makes the original claim');
});

test('the feature card states the per-device limit out loud', () => {
  const at = html.indexOf('Memory — gets smarter as you use it');
  assert.ok(at > 0, 'the corrected feature card is missing');
  const card = html.slice(at, at + 600);
  assert.match(card, /stored on the device/i);
  assert.match(card, /does not yet follow you between devices/i,
    'the limitation is implied rather than stated');
});

// ── THE DEAD ENDPOINTS ARE STILL DEAD, AND SAID TO BE ──────────────────────
section('what is still missing is labelled, not hidden');

test('the dead cloud endpoint is named as dead in the code', () => {
  const at = html.indexOf('async function cloudLoadMemory()');
  const head = html.slice(at, at + 900);
  assert.match(head, /DOES NOT EXIST/, 'the dead cloud leg reads as working code');
});

test('the reassuring catch comment is gone', () => {
  assert.strictEqual(html.indexOf('// Cloud save failed — local backup is enough'), -1,
    '"local backup is enough" is still there, and it was only true because ' +
    'nothing read either copy');
});

test('api/memory-cloud, api/memory and api/greeting are still absent', () => {
  // Recorded so that when one of them is built, this fails and the comments
  // above get revisited rather than going stale.
  ['memory-cloud.js', 'memory.js', 'greeting.js'].forEach((f) => {
    assert.ok(!fs.existsSync(path.join(ROOT, 'api', f)),
      'api/' + f + ' now exists -- update the "dead endpoint" comments in ' +
      'sairnscape.html and this test');
  });
});

run().then(() => {
  console.log('');
  if (fail) { console.log(fail + ' FAILED, ' + pass + ' passed'); process.exit(1); }
  console.log('ALL ' + pass + ' MEMORY ASSERTIONS PASS');
});
