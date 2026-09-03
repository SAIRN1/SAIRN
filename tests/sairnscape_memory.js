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
  const serverRows = (opts.serverRows || []).slice();
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
    // The real cloud leg, as of step 2. cloudSaveMemory/cloudLoadMemory probe
    // for these with `typeof ... === 'function'`, so leaving them undefined is
    // exactly the not-signed-in case and defining them is the signed-in one.
    scpMemoryWrite: opts.signedIn ? async (t) => { serverRows.unshift(String(t).slice(0, 400)); return true; } : undefined,
    scpMemoryRead: opts.signedIn ? async () => serverRows.slice() : undefined,
    __store: store, __posts: posts, __gets: gets, __serverRows: serverRows
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

// ── STEP 2: THE REAL CLOUD LEG ─────────────────────────────────────────────
section('signed in, memory belongs to the licence and follows the customer');

test('a signed-in save goes to the SERVER, not just localStorage', async () => {
  const c = harness({ signedIn: true });
  await c.cloudSaveMemory('The Ferreira job needs the retaining wall re-graded before seeding.');
  assert.strictEqual(c.__serverRows.length, 1, 'nothing reached the server');
  assert.match(c.__serverRows[0], /Ferreira/);
  // ...and the local copy is still written, so a later offline session still has it.
  assert.match(c.__store['sairn_local_sairnscape'], /Ferreira/);
});

test('a signed-in read PREFERS the server -- this is the cross-device path', async () => {
  // The device that did not write it still sees it: empty local store, populated
  // server. That is the whole feature.
  const c = harness({ signedIn: true, serverRows: ['Okafor wants the beds mulched in April, not March.'] });
  assert.strictEqual(c.__store['sairn_local_sairnscape'], undefined, 'the fixture has local data');
  const out = await c.cloudLoadMemory();
  assert.match(out, /Okafor/);
  assert.match(out, /previous sessions/);
});

test('NOT signed in, nothing is sent to the server at all', async () => {
  // The marketing-page demo chat. An anonymous visitor has no account to attach
  // memory to and must not be given a server row.
  const c = harness({ signedIn: false });
  await c.cloudSaveMemory('A demo question about pricing a mulch job for a 22-acre HOA.');
  assert.strictEqual(c.__serverRows.length, 0, 'the demo chat wrote to the server');
  assert.match(c.__store['sairn_local_sairnscape'], /mulch job/, 'the demo chat lost its local memory');
});

test('not signed in, the read still answers from local', async () => {
  const c = harness({ signedIn: false });
  await c.cloudSaveMemory('A demo answer long enough to be stored as a memory entry.');
  const out = await c.cloudLoadMemory();
  assert.match(out, /Recent context/);
  assert.match(out, /demo answer/);
});

test('a signed-in customer with no history yet falls through to local', async () => {
  const c = harness({ signedIn: true, serverRows: [] });
  await c.cloudSaveMemory('First note of the day about the Hartley irrigation zone.');
  const c2 = harness({ signedIn: true, serverRows: [] });
  c2.__store['sairn_local_sairnscape'] = c.__store['sairn_local_sairnscape'];
  const out = await c2.cloudLoadMemory();
  assert.match(out, /Recent context/, 'an empty server response suppressed the local answer');
  assert.match(out, /Hartley/);
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

test('the original unqualified pricing claim is gone', () => {
  // Written at step 1, when the honest line was "on this device". Step 2 made
  // cross-device true for signed-in users, so the SECOND half of this test was
  // retired rather than left asserting the previous state -- a test that pins
  // an interim answer becomes the thing blocking the real one. The current
  // pricing line is asserted below, in the step-2 section.
  assert.strictEqual(html.indexOf('Memory across all properties and clients'), -1,
    'the original unqualified claim is back');
});

test('the feature card no longer claims it remembers EVERYTHING', () => {
  assert.strictEqual(html.indexOf('Claude remembers every property, every client, every issue'), -1,
    'the feature card still makes the original claim');
});

// The step-1 version of this test asserted "stored on the device you use it on"
// and "does not yet follow you between devices". Both were true then and are
// false now; the replacement lives in the step-2 section and checks the
// distinction that actually ships -- signed-in memory follows the licence, the
// demo chat's does not.


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

test('the IN-APP assistant reads memory into its prompt', () => {
  // Before step 2 the in-app assistant was the only chat that never touched
  // memory at all, so a paying signed-in customer's real conversations
  // contributed nothing and recalled nothing.
  const at = html.indexOf('async function scpCallAI(');
  assert.ok(at > 0, 'scpCallAI is not async -- it cannot await the memory read');
  const body = html.slice(at, at + 2500);
  assert.match(body, /await scpMemoryRead\(\)/, 'the in-app assistant does not read memory');
  assert.match(body, /What this company has told you before/, 'memory is read and not put in the prompt');
});

test('the IN-APP assistant writes memory when a reply lands', () => {
  const at = html.indexOf('async function scpCallAI(');
  const body = html.slice(at, at + 2500);
  assert.match(body, /scpMemoryWrite\(replyText\)/, 'replies are never saved as memory');
});

test('the server leg requires BOTH a licence and a session', () => {
  const at = html.indexOf('function scpMemoryReady()');
  assert.ok(at > 0, 'no scpMemoryReady gate');
  const body = html.slice(at, at + 300);
  assert.match(body, /scpLd\('scp_lic'/, 'it does not check the licence');
  assert.match(body, /SCP_SESSION_KEY/, 'it does not check the employee session');
});

test('scpData only sends app_id when a caller asks for it', () => {
  // Every other scpData caller relies on the field being absent so
  // api/sd-data.js applies its stonedesk default. Sending it always would
  // change behaviour for resources that never asked.
  const at = html.indexOf('async function scpData(');
  const body = html.slice(at, at + 1200);
  assert.match(body, /if \(appId\) reqBody\.app_id = appId;/);
});

test('the pricing copy now claims cross-device, which is now true', () => {
  assert.ok(html.indexOf('on every device you sign in from') > 0,
    'the pricing line was not updated for step 2');
  assert.strictEqual(html.indexOf('Memory of your properties and clients, on this device'), -1,
    'the device-only pricing line is still there');
});

test('the feature card distinguishes signed-in memory from the demo chat', () => {
  const at = html.indexOf('Memory — gets smarter as you use it');
  assert.ok(at > 0);
  const card = html.slice(at, at + 700);
  assert.match(card, /follows your licence to/i);
  assert.match(card, /demo assistant on this page keeps its memory on this/i,
    'the demo chat limitation is no longer stated');
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
