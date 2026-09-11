// tests/faults/grd_write_faults.js
//
// Run:  node tests/faults/grd_write_faults.js
//
// FAULT INJECTION on SAIRNgrounds' server write path.
//
// ── THE FILE HAD NO TIMEOUT AND READ AS IF IT DID ──────────────────────────
// tools/write_path_fault_scan.py reported `timeout? yes` for this app on the
// strength of two USER-FACING SENTENCES -- "Weather Command Engine signal: " at
// lines 3077 and 3414 -- matching its `signal\s*:` probe against raw source.
// There was no timer race, no AbortController and no AbortSignal anywhere in
// 324KB. Forty-three server writes, and the single thing that would make a hang
// survivable was a string in a weather message.
//
// THAT IS THE FAULT THIS FILE EXISTS FOR, and it is worse here than the refusal
// path because the refusal path is already good. Forty of the 43 writes read
// `var syncResult = await grdData('write', ...)` and derive a toast from the
// result, naming exactly what did not sync. But `fetch` against a black-holed
// connection neither resolves nor rejects, so the `await` never returns,
// grdData()'s own catch never runs, and THE TOAST NEVER FIRES AT ALL -- the user
// clicks Save and the screen says nothing, indistinguishable from not having
// clicked. Careful reporting attached to a promise that never settles reports
// nothing.
//
// ── WHAT THE FIX IS, AND WHY IT IS NOT A PUSH HELPER ──────────────────────
// SAIRNvet and SAIRNdental needed svPushOne()/dntPushOne() because their callers
// had no shared failure vocabulary. This file already has one: `null` means "did
// not reach the server" and all 43 sites are written for it. So the timeout went
// INSIDE grdData() as AbortSignal.timeout(), which lands an AbortError in the
// catch that already returns null. A hang now arrives as the refusal every
// caller already handles -- one edit, no site missed, no new shape to learn.
//
// ── THE THREE SITES THAT READ NOTHING, and the 5 that only looked like it ──
// The scan flagged eight fire-and-forget writes. FIVE WERE SAFE: elements of
// `await Promise.all([...])` whose results drive a toast naming each record that
// failed -- the most careful write-reporting on the platform, reported as the
// least, because the classifier looked 40 characters behind the call for an
// `await`. Fixed in the tool, with arms in tests/run_write_path_scan_probe.py.
//
// Of the three real ones:
//   * cmSavePoints()        -- FIXED. Its three callers toast "Point captured"
//                              unconditionally, so a course point that never
//                              reached the server was announced as captured.
//   * gcdSaveRound()        -- NO TOAST, AND THAT STANDS. Already accepted and
//                              recorded in the file: it fires on every shot, so
//                              a per-call toast would run continuously while the
//                              server is down and drown the cart-order messages
//                              somebody is actually waiting on. "Do not tell the
//                              user" was decided; "record nothing" was not, and
//                              grdData() now logs.
//   * recordGrdSharedTopics -- best-effort AI telemetry, console only, same call
//                              and same reasoning as SAIRNvet's.

'use strict';
const fs = require('fs');
const path = require('path');
const K = require('./faultkit');
const assert = K.assert;

const FILE = 'sairngrounds.html';
const SRC = fs.readFileSync(path.join(K.ROOT, FILE), 'utf8');

let pass = 0, fail = 0;
const tests = [];
function test(name, fn) { tests.push([name, fn]); }
function section(t) { tests.push([t, null]); }

// grdData() is driven for real, against a fetch that can be told to misbehave.
// Nothing about the transport is re-implemented: a harness that re-creates the
// function it is testing proves only that the harness works.
function ctxFor(opts) {
  opts = opts || {};
  const state = { warns: [], toasts: [], fetches: 0 };
  const ctx = {
    JSON, Object, Array, String, Number, Date, Math, Promise,
    setTimeout, clearTimeout,
    console: { warn: (m) => state.warns.push(String(m)),
               error: (m) => state.warns.push(String(m)),
               log: () => {} },
    ld: (k, d) => (k === 'grd_lic' ? 'GRD-TEST-2026' : d),
    st: () => true,
    rGolf: () => {},
    toast: (m, d) => state.toasts.push(String(m)),
    sessionStorage: { getItem: () => null },
    GRD_SESSION_KEY: 'grd_sess',
    AbortSignal: opts.noAbortSignal ? {} : {
      timeout: (ms) => ({ __timeoutMs: ms }),
    },
    fetch: function (url, o) {
      state.fetches += 1;
      state.lastOpts = o;
      if (opts.mode === 'refused') return Promise.resolve({ ok: false, status: 503 });
      if (opts.mode === 'throw') return Promise.reject(new Error('NetworkError'));
      if (opts.mode === 'hang') return new Promise(() => {});
      if (opts.mode === 'timeout') {
        // What the platform really does once a signal is attached: the fetch
        // rejects with a TimeoutError when the signal fires. Modelled as an
        // immediate rejection so the arm does not wait 15 real seconds.
        const e = new Error('The operation was aborted due to timeout');
        e.name = 'TimeoutError';
        return Promise.reject(e);
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true, data: {} }) });
    },
    __state: state,
  };
  K.vm.createContext(ctx);
  K.vm.runInContext(SRC.slice(SRC.indexOf('var GRD_FETCH_TIMEOUT_MS')).split(/\r?\n/)[0], ctx);
  // The signal helper, extracted from the real file. It was inline in grdData()
  // when this suite was written and became a named function on 2026-09-11 so the
  // one app that proved the mechanism stopped being the one a portfolio-wide
  // check has to special-case. Loaded rather than stubbed: a stub would let the
  // feature-detect it contains rot while the arms below stayed green.
  K.vm.runInContext(K.grab(SRC, 'function grdFetchTimeoutSignal(', ''), ctx);
  K.vm.runInContext(K.grab(SRC, 'async function grdData(', ''), ctx);
  K.vm.runInContext(K.grab(SRC, 'async function cmSavePoints(', ''), ctx);
  return ctx;
}

section('the timeout is ARMED -- the whole point, and it was absent entirely');

test('grdData attaches an abort signal to the request', async () => {
  const ctx = ctxFor({});
  await ctx.grdData('write', 'golf_zones', { id: 'Z1' });
  assert.ok(ctx.__state.lastOpts && ctx.__state.lastOpts.signal,
    'no signal on the request -- a hung connection is unbounded again, which is '
    + 'the state this file was in until 2026-09-10');
  assert.strictEqual(ctx.__state.lastOpts.signal.__timeoutMs, 15000,
    'the timeout is not the platform-wide 15s used by svPushOne and dntPushOne');
});

test('...and an engine WITHOUT AbortSignal.timeout can still write', async () => {
  // The property exists on the global but the method does not -- the real shape
  // of an older engine. Must degrade to the previous unbounded behaviour rather
  // than throwing a TypeError that would break every write in the app.
  const ctx = ctxFor({ noAbortSignal: true });
  const r = await ctx.grdData('write', 'golf_zones', { id: 'Z1' });
  assert.ok(r, 'a browser without AbortSignal.timeout can no longer write at all');
  assert.ok(!ctx.__state.lastOpts.signal);
});

test('...and so can one with NO AbortSignal global at all', async () => {
  // Stronger than the arm above, and the reason both exist: a bare
  // `AbortSignal.timeout` on an absent global throws ReferenceError, not
  // TypeError, and only the `typeof` half of the guard sees that coming.
  //
  // HONEST NOTE ON WHAT THIS DOES *NOT* PROVE. Deleting the `typeof` guard does
  // not fail this suite, because the inner try/catch around the assignment
  // catches both throws. That was checked by mutation, not assumed: M7 in the
  // probe run removed the guard and all 18 arms stayed green. The guard is kept
  // for readability -- a normal, expected condition should not be signalled by
  // an exception -- and this arm exists to prove the BEHAVIOUR, which is what
  // matters, rather than the particular line that delivers it.
  const ctx = ctxFor({});
  delete ctx.AbortSignal;
  const r = await ctx.grdData('write', 'golf_zones', { id: 'Z1' });
  assert.ok(r, 'an engine with no AbortSignal global can no longer write');
  assert.ok(!ctx.__state.lastOpts.signal);
});

test('the READ path is bounded too, which is deliberate', async () => {
  const ctx = ctxFor({});
  await ctx.grdData('read', 'shared_knowledge', {});
  assert.ok(ctx.__state.lastOpts.signal,
    'a hung read leaves a panel waiting forever with no message');
});

section('a TIMEOUT arrives as the refusal every caller is already written for');

test('a timed-out write resolves NULL, not a rejection', async () => {
  // The one shape all 43 sites understand. If this returned a rejection instead,
  // forty `await` sites would throw out of their handlers and the toast would be
  // skipped -- the defect, relocated.
  const ctx = ctxFor({ mode: 'timeout' });
  const r = await ctx.grdData('write', 'grd_invoices', { id: 'I1' });
  assert.strictEqual(r, null);
});

test('...and it is REPORTED, naming the timeout rather than a generic failure', async () => {
  const ctx = ctxFor({ mode: 'timeout' });
  await ctx.grdData('write', 'grd_invoices', { id: 'I1' });
  const w = ctx.__state.warns;
  assert.strictEqual(w.length, 1, 'a timed-out write said nothing at all');
  assert.ok(/no answer in 15s/.test(w[0]),
    'the reader cannot tell a timeout from a refusal: ' + w[0]);
  assert.ok(/grd_invoices/.test(w[0]),
    'the warning does not name what was lost: ' + w[0]);
});

test('a dropped socket is reported with its own reason', async () => {
  const ctx = ctxFor({ mode: 'throw' });
  const r = await ctx.grdData('write', 'grd_rounds', { id: 'R1' });
  assert.strictEqual(r, null);
  assert.strictEqual(ctx.__state.warns.length, 1);
  assert.ok(/NetworkError/.test(ctx.__state.warns[0]),
    'a network failure is being described as a timeout: ' + ctx.__state.warns[0]);
});

test('a server REFUSAL still resolves null -- unchanged behaviour', async () => {
  const ctx = ctxFor({ mode: 'refused' });
  assert.strictEqual(await ctx.grdData('write', 'grd_rounds', { id: 'R1' }), null);
});

test('the happy path is untouched', async () => {
  const ctx = ctxFor({});
  const r = await ctx.grdData('write', 'golf_zones', { id: 'Z1' });
  assert.ok(r && r.ok, 'the fix broke the working path');
  assert.deepStrictEqual(ctx.__state.warns, [],
    'a successful write reported a failure');
});

section('cmSavePoints -- the point that was announced as captured');

test('a refused course-point push now TELLS the user', async () => {
  const ctx = ctxFor({ mode: 'refused' });
  await ctx.cmSavePoints({ id: 'Z1', points: [{ id: 'P1' }] });
  assert.strictEqual(ctx.__state.toasts.length, 1,
    'the point is still announced as captured with nothing said about the server');
  assert.ok(/did not\s+sync to the server/.test(ctx.__state.toasts[0]),
    'the message does not say the sync failed: ' + ctx.__state.toasts[0]);
});

test('...and a HANG does too, which is the case that said nothing', async () => {
  const ctx = ctxFor({ mode: 'timeout' });
  await ctx.cmSavePoints({ id: 'Z1', points: [{ id: 'P1' }] });
  assert.strictEqual(ctx.__state.toasts.length, 1,
    'a timed-out course-point push is silent');
});

test('a SUCCESSFUL push says nothing extra -- the caller owns the good news', async () => {
  // Or every captured point would draw two toasts, and the honest message would
  // stop meaning anything.
  const ctx = ctxFor({});
  await ctx.cmSavePoints({ id: 'Z1', points: [{ id: 'P1' }] });
  assert.deepStrictEqual(ctx.__state.toasts, []);
});

test('the local write happens BEFORE the push, not after it', async () => {
  // A point must survive on the device even when the server is unreachable --
  // and it must not be written only if the push succeeds.
  const body = K.grab(SRC, 'async function cmSavePoints(', '');
  const stAt = body.indexOf("st('grd_golf_zones'");
  const pushAt = body.indexOf("grdData('write'");
  assert.ok(stAt > 0 && pushAt > stAt,
    'the local write no longer precedes the server push, so a failed push could '
    + 'lose the point entirely');
});

section('the two deliberate no-toast sites, asserted as decisions not oversights');

test('gcdSaveRound still raises NO toast, and says why at the site', () => {
  const body = K.grab(SRC, 'function gcdSaveRound(', '');
  assert.ok(!/toast\(/.test(body.replace(/\/\/[^\n]*/g, '')),
    'a per-shot failure toast was added; it fires on every shot and hole arrival '
    + 'and will drown the cart-order messages -- see the accepted note above '
    + 'rCaddie() before changing this');
  assert.ok(/every shot/.test(body) || /telemetry/.test(body),
    'the reason for the silence is no longer stated at the site, so the next '
    + 'reader will file it as a defect and "fix" it');
});

test('recordGrdSharedTopics stays fire-and-forget and says why', () => {
  const body = K.grab(SRC, 'function recordGrdSharedTopics(', '');
  assert.ok(/grdData\(\s*'write'/.test(body));
  assert.ok(!/toast\(/.test(body.replace(/\/\/[^\n]*/g, '')));
});

test('BOTH of them are covered by grdData\'s own reporting', () => {
  // Which is the only reason leaving them unhandled is honest rather than
  // silent. If grdData stopped logging, these two would go dark again.
  const body = K.grab(SRC, 'async function grdData(', '');
  assert.ok(/console\.warn/.test(body),
    'grdData no longer logs a failure, so the two no-toast sites are silent '
    + 'again -- they were only acceptable because the transport speaks');
  assert.ok(/did NOT reach/.test(body),
    'the transport message lost the wording the rest of the platform uses');
});

section('the structural half -- a 44th write site added later');

test('every grdData write call site is inside a function, not top-level', () => {
  // Cheap, and it catches a write added to module scope where no handler and no
  // toast could exist at all.
  const code = SRC.replace(/\/\/[^\n]*/g, '');
  const re = /grdData\(\s*'write'/g;
  let m, bad = 0;
  while ((m = re.exec(code)) !== null) {
    const before = code.slice(0, m.index);
    if (before.lastIndexOf('function ') < before.lastIndexOf('\n</script>')) bad++;
  }
  assert.strictEqual(bad, 0);
});

test('the count of write sites is what this file was measured against', () => {
  // Not a freeze -- a tripwire. If it moves, somebody added or removed a write
  // and should say which, and whether the new one reads its result.
  const code = SRC.replace(/\/\/[^\n]*/g, '');
  const n = (code.match(/grdData\(\s*'write'/g) || []).length;
  assert.strictEqual(n, 43,
    'SAIRNgrounds now has ' + n + ' write call sites, measured at 43 on '
    + '2026-09-10. Re-run tools/write_path_fault_scan.py and update this number '
    + 'deliberately, saying whether the new site reads its result.');
});

(async () => {
  for (const [name, fn] of tests) {
    if (fn === null) { console.log('--- ' + name + ' ---'); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
  }
  console.log('\n' + (fail === 0
    ? 'ALL ' + pass + ' SAIRNGROUNDS WRITE FAULT ARMS PASS'
    : pass + ' passed, ' + fail + ' FAILED'));
  process.exit(fail === 0 ? 0 : 1);
})();
