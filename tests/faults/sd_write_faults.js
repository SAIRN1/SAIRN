// tests/faults/sd_write_faults.js
//
// Run:  node tests/faults/sd_write_faults.js
//
// FAULT INJECTION on StoneDesk's server write path -- the app the defect
// register calls the LEAST SWEPT, not the cleanest: 2 records across 40,388
// lines by two methods, and fault injection was not one of them.
//
// ── WHAT THE SCAN POINTED AT, AND WHAT READING IT FOUND ────────────────────
// tools/write_path_fault_scan.py flagged six sites. FOUR ARE SAFE and were read
// before anything was touched, which is the rule that tool prints on every run
// and the rule that saved five of SAIRNgrounds' eight:
//
//   :2030  sdSyncCollection     .then(saved===null) -> console.warn. Correct.
//   :29001 sdCRMAdd             .then(saved) -> toast on failure. Correct.
//   :29021 sdCRMReassign        .then(saved) -> toast either way. Correct.
//   :32637 sdSaveEmployeeProfile .then(res) -> inline error. Correct.
//
// They are flagged only because the scan looks for a literal `.catch(`, and
// sdData() cannot reject -- it ends in a try/catch that returns null.
//
// TWO READ NOTHING, and both are deliberate:
//   :22193 recordSharedTopics   best-effort AI topic counter
//   :23269 saveSD3Data          per-customer push from a RENDER path, documented
//                               as fire-and-forget so it cannot block a repaint
//
// ── THE REAL DEFECT IS UNDERNEATH ALL SIX ──────────────────────────────────
// sdData() was the ONLY transport of fifteen with no console call anywhere.
// Measured: fourteen carry one; StoneDesk set `_sdReadFailed[resource] = true`
// and returned null. That flag is consumed by READ-path UI -- sdReadFailedNote(),
// the public-catalog guard -- and does NOTHING for a write. So a write that never
// reached the server left NO TRACE on the two sites that read no result, and the
// one whose own comment notes that an order-tracking link resolves to the SERVER
// copy, so a stage changed locally and nowhere else leaves a customer reading a
// status that is no longer true.
//
// A STATE FLAG IS NOT A REPORT -- the same sentence CLAUDE.md already records for
// st(): "a boolean nobody reads is not a report."
//
// AND IT SLIPPED MY OWN SWEEP THE DAY BEFORE. transport_timeout_sweep.js asserted
// each transport "reports a failure rather than swallowing it" and accepted
// `_sdReadFailed` as evidence. Harmless for fourteen apps that also log; it
// decided everything for the one that did not. That arm is tightened in the same
// commit and carries its own control.

'use strict';
const fs = require('fs');
const path = require('path');
const K = require('./faultkit');
const assert = K.assert;

const FILE = 'stonedesk.html';
const SRC = fs.readFileSync(path.join(K.ROOT, FILE), 'utf8');

let pass = 0, fail = 0;
const tests = [];
function test(name, fn) { tests.push([name, fn]); }
function section(t) { tests.push([t, null]); }

// Brace-balanced from RAW source, then comments stripped only for CONTENT
// assertions. Stripping a 2MB file first cost two apps' arms in the transport
// sweep -- one quote-state slip swallows everything after it.
function grabRaw(sig) {
  const m = new RegExp(sig.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).exec(SRC);
  assert.ok(m, sig + ' not found -- this arm is testing nothing');
  const o = SRC.indexOf('{', m.index);
  let d = 0, k = o;
  for (; k < SRC.length; k++) {
    if (SRC[k] === '{') d++;
    else if (SRC[k] === '}' && --d === 0) break;
  }
  return SRC.slice(m.index, k + 1);
}

function ctxFor(opts) {
  opts = opts || {};
  const state = { warns: [], toasts: [], lastOpts: null, written: [] };
  const ctx = {
    JSON, Object, Array, String, Number, Date, Math, Promise, setTimeout, clearTimeout,
    console: { warn: (...a) => state.warns.push(a.map(String).join(' ')),
               error: (...a) => state.warns.push(a.map(String).join(' ')),
               log: () => {} },
    AbortSignal: opts.noAbortSignal ? {} : { timeout: (ms) => ({ __timeoutMs: ms }) },
    sessionStorage: { getItem: () => null },
    sdLicenseKey: () => 'SD-TEST-2026',
    showToast: (m) => state.toasts.push(String(m)),
    // _sdLastStatus added 2026-09-12 with the map itself. sdData() writes it on
    // every path, so without it the transport dies on a ReferenceError before
    // reaching any branch this file asserts on.
    _sdAuthRefused: {}, _sdReadFailed: {}, _sdLastStatus: {},
    fetch: function (url, o) {
      state.lastOpts = o;
      if (opts.mode === 'timeout') {
        const e = new Error('The operation was aborted due to timeout');
        e.name = 'TimeoutError';
        return Promise.reject(e);
      }
      if (opts.mode === 'throw') return Promise.reject(new Error('NetworkError'));
      if (opts.mode === 'refused') return Promise.resolve({ ok: false, status: 503 });
      if (opts.mode === 'oknotok') {
        return Promise.resolve({ ok: true, status: 200,
          json: () => Promise.resolve({ ok: false, error: { code: 'NOPE' } }) });
      }
      try { state.written.push(JSON.parse(o.body)); } catch (e) {}
      return Promise.resolve({ ok: true, status: 200,
        json: () => Promise.resolve({ ok: true, data: { id: 'X1' } }) });
    },
    __state: state,
  };
  K.vm.createContext(ctx);
  K.vm.runInContext(SRC.slice(SRC.indexOf('var SD_FETCH_TIMEOUT_MS')).split(/\r?\n/)[0], ctx);
  K.vm.runInContext(grabRaw('function sdFetchTimeoutSignal()'), ctx);
  // The reporter, loaded from the real file and never stubbed: stubbing it would
  // let its wording and its own try/catch rot while these arms stayed green.
  K.vm.runInContext(grabRaw('function sdDataFailed('), ctx);
  K.vm.runInContext(grabRaw('async function sdData('), ctx);
  return ctx;
}

section('the transport SPEAKS on every failure branch -- it spoke on none');

test('a TIMEOUT is reported, and named as a timeout', async () => {
  const ctx = ctxFor({ mode: 'timeout' });
  const r = await K.within(3000, ctx.sdData('write', 'sd_customers', { id: 'C1' }));
  assert.strictEqual(r.settled, true);
  assert.ok(!r.rejected,
    'the transport REJECTS on a timeout -- every await caller would throw out of '
    + 'its handler and skip the toast. The defect relocated, not fixed.');
  assert.strictEqual(r.value, null, 'null is the vocabulary all six call sites read');
  assert.strictEqual(ctx.__state.warns.length, 1, 'a timed-out write said nothing');
  assert.ok(/no answer in 15s/.test(ctx.__state.warns[0]),
    'a timeout is indistinguishable from a dropped socket: ' + ctx.__state.warns[0]);
  assert.ok(/sd_customers/.test(ctx.__state.warns[0]),
    'the warning does not name what was lost: ' + ctx.__state.warns[0]);
});

test('a DROPPED SOCKET is reported with its own reason', async () => {
  const ctx = ctxFor({ mode: 'throw' });
  assert.strictEqual(await ctx.sdData('write', 'sd_crm', { id: 'L1' }), null);
  assert.strictEqual(ctx.__state.warns.length, 1);
  assert.ok(/NetworkError/.test(ctx.__state.warns[0]),
    'a network failure is being described as a timeout: ' + ctx.__state.warns[0]);
});

test('an HTTP REFUSAL is reported, with the status', async () => {
  // This branch set _sdReadFailed and returned null in silence. A 503 on a write
  // is not a read problem and the read-path flag does nothing for it.
  const ctx = ctxFor({ mode: 'refused' });
  assert.strictEqual(await ctx.sdData('write', 'sd_customers', { id: 'C1' }), null);
  assert.strictEqual(ctx.__state.warns.length, 1, 'a refused write said nothing');
  assert.ok(/503/.test(ctx.__state.warns[0]),
    'the status is not stated: ' + ctx.__state.warns[0]);
});

test('a 200 carrying ok:false is reported too -- the quietest failure of the three',
  async () => {
    const ctx = ctxFor({ mode: 'oknotok' });
    assert.strictEqual(await ctx.sdData('write', 'sd_customers', { id: 'C1' }), null);
    assert.strictEqual(ctx.__state.warns.length, 1);
    assert.ok(/ok:false/.test(ctx.__state.warns[0]), ctx.__state.warns[0]);
  });

test('and a SUCCESSFUL write reports nothing', async () => {
  const ctx = ctxFor({});
  const r = await ctx.sdData('write', 'sd_customers', { id: 'C1' });
  assert.ok(r && r.id === 'X1');
  assert.deepStrictEqual(ctx.__state.warns, [],
    'a working write is reporting a failure');
});

section('the read-path flag still behaves exactly as it did');

test('_sdReadFailed is still set on failure and cleared on success', async () => {
  // Read-path UI depends on it -- sdReadFailedNote(), the public-catalog guard --
  // so the fix ADDS a console call rather than replacing the flag. Asserted
  // because "I only added a log" is a claim.
  const bad = ctxFor({ mode: 'refused' });
  await bad.sdData('read', 'sd_public_shop', {});
  assert.strictEqual(bad._sdReadFailed['sd_public_shop'], true);
  const good = ctxFor({});
  await good.sdData('read', 'sd_public_shop', {});
  assert.strictEqual(good._sdReadFailed['sd_public_shop'], false);
});

test('_sdAuthRefused still distinguishes 401/403 from any other failure', async () => {
  const ctx = ctxFor({ mode: 'refused' });        // 503
  await ctx.sdData('read', 'slabs', {});
  assert.strictEqual(ctx._sdAuthRefused['slabs'], false,
    'a 503 is being reported as an auth refusal');
});

section('the reporter cannot break the transport it reports for');

test('sdData still resolves when sdDataFailed is MISSING', async () => {
  // Found by this suite before it was a suite: a realm without sdDataFailed made
  // the catch throw a ReferenceError, which made the whole async function REJECT.
  // A failure path that can itself fail is the shape two days of this session
  // have been about, so it is not left to the reporter being present.
  const ctx = ctxFor({ mode: 'timeout' });
  delete ctx.sdDataFailed;
  const r = await K.within(3000, ctx.sdData('write', 'sd_customers', { id: 'C1' }));
  assert.strictEqual(r.settled, true);
  assert.ok(!r.rejected, 'a missing reporter makes the transport reject');
  assert.strictEqual(r.value, null);
});

test('...and when console itself throws', async () => {
  const ctx = ctxFor({ mode: 'timeout' });
  ctx.console = { warn: () => { throw new Error('no console here'); },
                  error: () => { throw new Error('no console here'); }, log: () => {} };
  const r = await K.within(3000, ctx.sdData('write', 'sd_customers', { id: 'C1' }));
  assert.ok(r.settled && !r.rejected, 'a throwing console breaks every write');
  assert.strictEqual(r.value, null);
});

section('the timeout is armed, and feature-detected');

test('the request carries a 15s abort signal', async () => {
  const ctx = ctxFor({});
  await ctx.sdData('write', 'sd_customers', { id: 'C1' });
  assert.ok(ctx.__state.lastOpts && ctx.__state.lastOpts.signal, 'no signal on the request');
  assert.strictEqual(ctx.__state.lastOpts.signal.__timeoutMs, 15000);
});

test('an engine without AbortSignal.timeout can still write', async () => {
  const ctx = ctxFor({ noAbortSignal: true });
  assert.ok(await ctx.sdData('write', 'sd_customers', { id: 'C1' }));
  assert.ok(!ctx.__state.lastOpts.signal);
});

section('the four safe sites are safe because they READ the result -- asserted');

// THE PATTERN PER SITE IS THE RESULT-DERIVED REPORT, NOT "showToast appears".
// The first version of these arms matched /showToast\(/ anywhere in the window,
// and a mutation that changed `if(!saved){showToast(...)}` to `if(false){...}`
// SURVIVED all 18 arms -- the exact "a mention is not a report" weakness this
// same commit tightens in transport_timeout_sweep.js, reproduced in the suite
// written to replace it. So each pattern now pins the report to the RESULT.
[['sdSyncCollection', /if\(saved===null\)/, 'logs only when the push returned null'],
 ['sdCRMAdd', /if\(!saved\)\{showToast\(/, 'toasts only when the lead push failed'],
 ['sdCRMReassign', /showToast\(saved\?/, 'derives both messages from the result'],
 ['sdSaveEmployeeProfile', /if\(!res\)\{errEl\.textContent/,
  'shows the inline error only when the save failed']].forEach(
  ([name, re, what]) => {
    test(name + '() still ' + what, () => {
      // EVERY occurrence is considered, not the first. These names appear in
      // PROSE before they appear as code -- this repo's comments quote the
      // scan's own findings -- so anchoring on indexOf(name) measured a
      // paragraph.
      const windows = [];
      for (let i = SRC.indexOf(name); i >= 0; i = SRC.indexOf(name, i + 1)) {
        windows.push(SRC.slice(i, i + 2600));
      }
      assert.ok(windows.length, name + ' is gone -- the scan flagged it, so say why');
      const writing = windows.filter((w) => /sdData\(\s*'write'/.test(w));
      assert.ok(writing.length,
        name + ' no longer performs the write this arm is about');
      assert.ok(writing.some((w) => re.test(w)),
        name + ' no longer derives its report FROM THE RESULT. The scan already '
        + 'lists it as then-without-catch, so nothing else would notice.');
    });
  });

section('the two fire-and-forget sites stay that way, deliberately');

test('recordSharedTopics reads no result and raises no toast', () => {
  const body = grabRaw('function recordSharedTopics(');
  assert.ok(/sdData\(\s*'write'\s*,\s*'shared_knowledge'/.test(body));
  assert.ok(!/showToast|\.then\(/.test(body.replace(/\/\/[^\n]*/g, '')),
    'a best-effort topic counter gained a handler or a toast -- if that was '
    + 'deliberate, say why at the site');
});

test('saveSD3Data stays fire-and-forget AND still says why at the site', () => {
  // The reason is load-bearing: it is called from render paths that must not
  // wait on a network round trip. An arm that only checked the shape would let
  // the reason be deleted and the next reader would "fix" it.
  const body = grabRaw('function saveSD3Data(');
  assert.ok(/sdData\(\s*'write'\s*,\s*'sd_customers'/.test(body));
  // The SPECIFIC reason, not an alternation another phrase can satisfy. Deleting
  // the render-path sentence survived the first version because the words
  // "Fire-and-forget" appear elsewhere in the same body.
  assert.ok(/must not wait on a network round trip/.test(body),
    'the reason for not awaiting is no longer stated at the site -- the next '
    + 'reader will file this as a defect and "fix" a render path into a blocking '
    + 'one');
  assert.ok(!/showToast/.test(body.replace(/\/\/[^\n]*/g, '')),
    'a per-record toast was added to a function called from a render path');
});

test('and BOTH are covered by the transport now speaking', () => {
  // Which is the only reason leaving them unhandled is honest rather than
  // silent. If sdData stopped logging, these two would go dark again -- which is
  // exactly the state this file was written to close.
  const body = grabRaw('async function sdData(');
  assert.ok(/sdDataFailed\(/.test(body),
    'sdData no longer reports, so the two fire-and-forget sites are silent again');
  const rep = grabRaw('function sdDataFailed(');
  assert.ok(/console\.warn/.test(rep) && /did NOT reach/.test(rep),
    'the reporter lost the wording the rest of the platform uses');
});

(async () => {
  for (const [name, fn] of tests) {
    if (fn === null) { console.log('--- ' + name + ' ---'); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
  }
  console.log('\n' + (fail === 0
    ? 'ALL ' + pass + ' STONEDESK WRITE FAULT ARMS PASS'
    : pass + ' passed, ' + fail + ' FAILED'));
  process.exit(fail === 0 ? 0 : 1);
})();
