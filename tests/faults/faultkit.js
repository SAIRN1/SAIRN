// tests/faults/faultkit.js -- the shared harness for FAULT INJECTION.
//
// A DIFFERENT LAYER FROM MUTATION TESTING, and the distinction is the whole
// point. Mutation testing breaks the LOGIC and asks whether a test notices.
// Fault injection breaks the WORLD -- a write refused, a socket dropped between
// two calls, a response that never arrives, storage throwing on the third of
// five writes -- and asks whether the app stays HONEST.
//
// WHY THIS LAYER, AND THE EVIDENCE IS ONE DAY OLD. Every live defect found on
// 2026-09-10 was a world failure, not a logic bug:
//
//   * svSyncSuppressed left true because st() could throw between setting it
//     and clearing it -- no finally.
//   * a refused vendor push showing a success toast, then the next sync
//     silently replacing the edit.
//   * a demo seed reaching the live server on a device with an empty store.
//
// Not one of them is reachable by mutating logic. Every one of them is one
// injected fault away from obvious.
//
// THE ASSERTION IS ALWAYS THE SAME QUESTION: after the fault, does the app SAY
// something true? Not "does it survive" -- a silent survival is the defect.
//
// It drives the REAL functions, extracted from the real app file. Nothing here
// re-implements app behaviour: a harness that re-creates the code it is testing
// proves only that the harness works.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..', '..');

// Extract a top-level `function name(` by brace-balance from the real file.
// Indent-aware: SAIRNdental's are 0-indented, SAIRNvet's are 0-indented too,
// but a nested helper would need its own terminator, so the caller passes the
// indent it expects rather than this guessing.
function grab(src, sig, indent) {
  const i = src.indexOf(sig);
  assert.ok(i > 0, sig + ' not found -- the app file moved and this harness is '
    + 'testing nothing. That is a FAILURE, not a skip.');
  const term = new RegExp('\\r?\\n' + (indent || '') + '\\}');
  const rel = src.slice(i).search(term);
  assert.ok(rel > 0, sig + ' is not terminated at indent ' + JSON.stringify(indent || ''));
  return src.slice(i, i + rel) + '\n' + (indent || '') + '}';
}

// A world that can be told to misbehave. Every fault below is a shape this
// platform has actually seen, not an invented one.
function makeWorld(opts) {
  opts = opts || {};
  const state = {
    store: {},
    toasts: [],
    warns: [],
    calls: 0,
    written: [],          // what reached the "server"
  };

  const storageThrowsOn = opts.storageThrowsOn || 0;   // nth setItem throws
  let setCount = 0;

  const ctx = {
    JSON, Date, Object, Array, Promise, Math, String, Number, isFinite,
    setTimeout, console: { warn: (m) => state.warns.push(String(m)),
                           error: (m) => state.warns.push(String(m)) },
    localStorage: {
      getItem: (k) => (k in state.store ? state.store[k] : null),
      setItem: (k, v) => {
        setCount += 1;
        if (storageThrowsOn && setCount === storageThrowsOn) {
          const e = new Error('QuotaExceededError');
          e.name = 'QuotaExceededError';
          throw e;
        }
        state.store[k] = String(v);
      },
      removeItem: (k) => { delete state.store[k]; },
    },
    toast: (m, d) => state.toasts.push({ m: String(m), d: d }),
    showToast: (m, d) => state.toasts.push({ m: String(m), d: d }),
    _state: state,
  };

  // THE TRANSPORT, and its faults. `mode` is what the world does to a call:
  //   'ok'      -- returns the record, the happy path
  //   'refused' -- resolves NULL, which is how every app here reports a write
  //                the server did not take
  //   'throw'   -- REJECTS. A dropped socket, a DNS failure, a CORS error.
  //                This is the shape a `.then(ok => ...)` caller forgets.
  //   'hang'    -- never settles. A gateway timeout with no response.
  //   'partial' -- resolves a record MISSING fields the caller sent, which is
  //                what a truncated or filtered response looks like.
  const mode = opts.transport || 'ok';
  const failFrom = opts.failFrom || 1;
  ctx.sdnData = ctx.svData = ctx.sdData = function (action, resource, payload) {
    state.calls += 1;
    const failing = state.calls >= failFrom;
    if (action === 'write' && failing) {
      if (mode === 'refused') return Promise.resolve(null);
      if (mode === 'throw') return Promise.reject(new Error('NetworkError'));
      if (mode === 'hang') return new Promise(() => {});
      if (mode === 'partial') return Promise.resolve({ id: payload && payload.id });
    }
    if (action === 'read' && failing && mode !== 'ok') {
      if (mode === 'throw') return Promise.reject(new Error('NetworkError'));
      if (mode === 'hang') return new Promise(() => {});
      return Promise.resolve(null);
    }
    if (action === 'write') state.written.push([resource, payload]);
    return Promise.resolve(payload || { id: 'default' });
  };

  vm.createContext(ctx);
  return ctx;
}

function load(ctx, file, sigs, indent) {
  const src = fs.readFileSync(path.join(ROOT, file), 'utf8');
  sigs.forEach((s) => {
    if (s.startsWith('var ') || s.startsWith('let ')) {
      vm.runInContext(src.slice(src.indexOf(s)).split(/\r?\n/)[0], ctx);
    } else {
      vm.runInContext(grab(src, s, indent), ctx);
    }
  });
  return src;
}

// A settled-or-timeout wrapper, so a HANG is observable as a hang instead of
// wedging the whole suite. The timeout being reached IS the observation.
function within(ms, p) {
  return Promise.race([
    Promise.resolve(p).then((v) => ({ settled: true, value: v }),
                            (e) => ({ settled: true, rejected: true, error: e })),
    new Promise((r) => setTimeout(() => r({ settled: false }), ms)),
  ]);
}

module.exports = { ROOT, grab, makeWorld, load, within, assert, vm };

// ── RUN DIRECTLY, THIS SELF-TESTS ───────────────────────────────────────────
// tools/run_all_tests.py walks tests/ and runs every .js it finds, so this
// library gets executed whether or not it is a test. A library that merely
// defines and exits 0 would be counted as a PASSING test file -- a vacuous
// green in the suite, which is the exact shape run_all_tests.py was built to
// stop being invisible.
//
// So running it proves the HARNESS works: if `throw` did not reject or `hang`
// settled, every fault suite built on it would pass while injecting nothing.
if (require.main === module) {
  (async () => {
    let bad = 0;
    const ok = (l, c) => { console.log('  ' + (c ? 'ok  ' : 'FAIL') + ' ' + l); if (!c) bad++; };

    const refused = makeWorld({ transport: 'refused' });
    ok('refused resolves null', (await refused.sdnData('write', 'x', { id: 1 })) === null);

    const thrown = makeWorld({ transport: 'throw' });
    const t = await within(500, thrown.sdnData('write', 'x', { id: 1 }));
    ok('throw REJECTS rather than resolving', t.settled === true && t.rejected === true);

    const hung = makeWorld({ transport: 'hang' });
    const h = await within(300, hung.sdnData('write', 'x', { id: 1 }));
    ok('hang never settles', h.settled === false);

    const part = makeWorld({ transport: 'partial' });
    const p = await part.sdnData('write', 'x', { id: 1, keep: 'me' });
    ok('partial drops fields the caller sent', p && p.id === 1 && p.keep === undefined);

    const happy = makeWorld({});
    ok('the happy path resolves what was sent',
       (await happy.sdnData('write', 'x', { id: 7 })).id === 7);

    const q = makeWorld({ storageThrowsOn: 2 });
    q.localStorage.setItem('a', '1');
    let threw = false;
    try { q.localStorage.setItem('b', '2'); } catch (e) { threw = true; }
    ok('storageThrowsOn fires on the Nth write and not the first', threw);

    console.log('\n' + (bad ? bad + ' FAULTKIT SELF-CHECK(S) FAILED'
                            : 'faultkit self-check: all 6 pass'));
    process.exit(bad ? 1 : 0);
  })();
}
