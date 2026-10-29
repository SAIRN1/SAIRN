// tests/mech_fetch_timeout_fallback.js
//
// REQUIREMENT: every sairnmechanical server call SETTLES within the timeout,
//   in every engine -- including one with no AbortSignal.timeout, and one with
//   no AbortController at all.
//
// Run:  node tests/mech_fetch_timeout_fallback.js
//
// ── WHY (cody b64) ──────────────────────────────────────────────────────────
// b63 gave saveDoc a re-entry guard, released when the backup push answers.
// mechFetchTimeoutSignal() fell back to `undefined` where AbortSignal.timeout
// is missing, so mechData()'s fetch had NO timeout there: a request that never
// settles never released the guard, and the Save button stayed refused until
// the browser's own network timeout -- minutes, or never.
//
// FIXTURE FIRST (Michael's b64 ruling, from C5's "fixtures that miss the
// branch"): this file was written and run RED before the fix. It drives the
// real mechData() and mechPushOne() lifted from the page, against a fetch that
// never settles unless aborted, in two degraded engines.
'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'sairnmechanical.html'), 'utf8');

// Lift a function by its declaration line and a brace match -- the anchor
// must be unique, or which copy was tested is unknown.
function lift(marker) {
  const s = html.indexOf(marker);
  assert.ok(s >= 0, 'ANCHOR GONE: ' + marker);
  assert.strictEqual(html.indexOf(marker, s + 1), -1, 'ANCHOR NOT UNIQUE: ' + marker);
  let i = html.indexOf('{', s), depth = 0;
  for (; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}' && --depth === 0) return html.slice(s, i + 1);
  }
  throw new Error('unterminated: ' + marker);
}

const SRC = [
  'var MECH_FETCH_TIMEOUT_MS = 40;',          // the real 15000, shortened for the run
  lift('function mechFetchTimeoutSignal('),
  lift('function mechData('),
  'var MECH_ID_FIELD = {};',
  lift('function mechPushOne('),
].join('\n');

// A fetch that NEVER settles unless its signal aborts it.
function hangingFetch(url, opts) {
  return new Promise(function (resolve, reject) {
    const sig = opts && opts.signal;
    if (sig) sig.addEventListener('abort', function () {
      const e = new Error('aborted'); e.name = 'AbortError'; reject(e);
    });
  });
}

function engine(kind) {
  const ctx = {
    console: { warn() {}, error() {}, log() {} },
    setTimeout, clearTimeout, Promise, Object, String, JSON,
    fetch: hangingFetch,
    mechLic: () => 'MECH-KEY',
    mechHeaders: () => ({}),
    MECH_DATA_API: 'https://example.invalid/api/sd-data',
  };
  if (kind === 'no-timeout') {
    ctx.AbortController = AbortController;            // has a controller...
    ctx.AbortSignal = { };                             // ...but no AbortSignal.timeout
  } else if (kind === 'no-abort') {
    // neither exists: an older engine
  } else {
    ctx.AbortController = AbortController;
    ctx.AbortSignal = AbortSignal;
  }
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  return ctx;
}

// Settles within `ms`, or rejects with HUNG.
function within(p, ms) {
  let t;
  return Promise.race([p, new Promise(function (_, rej) { t = setTimeout(function () { rej(new Error('HUNG')); }, ms); })])
    .finally(function () { clearTimeout(t); });
}

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}

(async function main() {
  console.log('sairnmechanical -- every server call settles, in every engine');
  for (const kind of ['modern', 'no-timeout', 'no-abort']) {
    await test(kind + ': mechData against a fetch that never answers settles as {status:0}', async () => {
      const ctx = engine(kind);
      const r = await within(ctx.mechData('write', 'mech_docs', { id: 'd1' }), 3000);   // timeout + the 1 s backstop margin, with room
      assert.strictEqual(r.status, 0, JSON.stringify(r));
    });
    await test(kind + ': mechPushOne (what saveDoc waits on) settles to null, so the guard is released', async () => {
      const ctx = engine(kind);
      const r = await within(ctx.mechPushOne('mech_docs', { id: 'd1', text: 'x' }), 3000);   // timeout + the 1 s backstop margin, with room
      assert.strictEqual(r, null);
    });
  }
  console.log('\n' + (fail ? 'FAILED' : 'PASSED') + ' -- ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch(function (e) { console.error('COULD NOT RUN: ' + (e && e.stack || e)); process.exit(2); });
