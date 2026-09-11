// tests/faults/transport_timeout_sweep.js
//
// Run:  node tests/faults/transport_timeout_sweep.js
//
// EVERY SAIRN WRITE TRANSPORT, DRIVEN AGAINST A FETCH THAT NEVER ANSWERS.
//
// ── WHAT WAS TRUE BEFORE 2026-09-11 ────────────────────────────────────────
// Fifteen apps write to a server through exactly one transport function each,
// and each of those makes exactly one `fetch`. TWELVE had no timeout on any
// path. Two more had one only on a READ -- sairnbiz races sbFirstDeviceHydrate(),
// stonedesk puts AbortSignal.timeout(8000) on /api/knowledge -- and neither
// protects a single write. Only sairngrounds was bounded, and only because it
// was fixed hours earlier (7cd70f83).
//
// A HUNG FETCH NEITHER RESOLVES NOR REJECTS. So the transport's own catch never
// runs, and every caller waiting on it waits for the life of the page. On the
// 260-odd call sites that carefully read the result and toast what failed, the
// toast NEVER FIRES: the user clicks Save, the screen says nothing, and that is
// indistinguishable from not having clicked. The refusal path on most of these
// apps is good, which is exactly what made this invisible -- the reporting was
// attached to a promise that never settled.
//
// ── WHY ONE LINE PER TRANSPORT AND NOT A PUSH HELPER PER APP ───────────────
// SAIRNvet and SAIRNdental needed svPushOne()/dntPushOne() because their callers
// had no shared failure vocabulary. Every other app already has one -- `null`, or
// `{status:0}` in SAIRNmechanical -- understood at every call site. So an
// AbortError landing in the catch the transport already has arrives as the
// failure those callers are already written for. Nothing to route through, and no
// call site that can be missed. Fourteen one-line edits, one mechanism, proven
// live on sairngrounds before being applied anywhere else.
//
// ── AND THE TWO TRANSPORTS THAT WOULD HAVE SWALLOWED IT ────────────────────
// A timer is useless if the thing it fires into says nothing. Two transports
// discarded their error entirely:
//   sairnscape   `catch (e) { return null; }`
//   sairnmech    `.catch(function () { return { status: 0, body: null }; })`
// Neither even took the error as an argument. Both now name the failure, and the
// timeout case by name. Found by auditing every transport's catch rather than
// assuming the fourteen were alike -- they were not.
//
// Every arm drives the REAL transport, extracted from the real app file.

'use strict';
const fs = require('fs');
const path = require('path');
const K = require('./faultkit');
const assert = K.assert;

const ROOT = K.ROOT;

// app, transport fn, constant prefix, and what the transport returns on failure.
// The vocabulary differs and that is deliberate per app -- asserted, not assumed.
const APPS = [
  ['sairnbiz.html', 'sbData', 'SB', 'null'],
  ['sairnbuild.html', 'bldData', 'BLD', 'null'],
  ['sairncare.html', 'alfData', 'ALF', 'null'],
  ['sairncode.html', 'scData', 'SC', 'null'],
  ['sairndental.html', 'sdnData', 'DNT', 'null'],
  ['sairndesign.html', 'sdnData', 'SDN', 'null'],
  ['sairnfreedom.html', 'sfData', 'SF', 'null'],
  ['sairngrounds.html', 'grdData', 'GRD', 'null'],
  ['sairnlaw.html', 'sdnData', 'LAW', 'null'],
  ['sairnlegacy.html', 'sdnData', 'LEG', 'null'],
  ['sairnmechanical.html', 'mechData', 'MECH', 'status0'],
  ['sairnscape.html', 'scpData', 'SCP', 'null'],
  ['sairnsenior.html', 'senData', 'SEN', 'null'],
  ['sairnvet.html', 'svData', 'SV', 'null'],
  ['stonedesk.html', 'sdData', 'SD', 'null'],
];

let pass = 0, fail = 0;
const tests = [];
function test(name, fn) { tests.push([name, fn]); }
function section(t) { tests.push([t, null]); }

function read(f) { return fs.readFileSync(path.join(ROOT, f), 'utf8'); }

// The transport's own body, comments stripped, so an assertion about its CODE
// cannot be satisfied by its prose -- the standing rule added to CLAUDE.md on
// 2026-09-11 after this exact mistake was made twice in two different probes.
function stripComments(src) {
  const BS = String.fromCharCode(92);
  let out = '', i = 0, q = null;
  const n = src.length;
  while (i < n) {
    const c = src[i], d = src[i + 1];
    if (q) {
      if (c === BS) { out += c + (d || ''); i += 2; continue; }
      if (c === q) q = null;
      out += c; i++; continue;
    }
    if (c === '"' || c === "'" || c === '`') { q = c; out += c; i++; continue; }
    if (c === '/' && d === '/') { while (i < n && src[i] !== '\n') { out += src[i] === '\n' ? '\n' : ' '; i++; } continue; }
    if (c === '/' && d === '*') {
      i += 2;
      while (i < n && !(src[i] === '*' && src[i + 1] === '/')) { out += src[i] === '\n' ? '\n' : ' '; i++; }
      i += 2; continue;
    }
    out += c; i++;
  }
  return out;
}

// THE DECLARATION IS FOUND IN RAW SOURCE AND ONLY THE BODY IS STRIPPED.
// Stripping a whole 2MB app file first cost two apps' arms outright: a single
// quote-state slip -- an apostrophe inside a regex literal is the usual culprit
// -- swallows everything after it, and `mechData` and `scpData` both disappeared
// from a stripped copy while being plainly present in the file. A whole-file
// quote walk that goes wrong goes wrong for the REST OF THE FILE, which is the
// worst failure mode a detector can have; the same lesson the timeout column in
// write_path_fault_scan.py learned the same day. A declaration inside a comment
// is not a thing this codebase contains, so finding it raw is safe; the CONTENT
// assertions still run on a stripped body, which is what the rule requires.
function transportBody(src, fn) {
  const m = new RegExp('(?:async\\s+)?function\\s+' + fn + '\\s*\\(').exec(src);
  assert.ok(m, fn + ' not found -- the transport was renamed and this arm tests nothing');
  const o = src.indexOf('{', m.index);
  let d = 0, k = o;
  for (; k < src.length; k++) {
    if (src[k] === '{') d++;
    else if (src[k] === '}' && --d === 0) break;
  }
  return stripComments(src.slice(m.index, k + 1));
}

section('every transport arms a timeout -- the structural half, all 15');

APPS.forEach(([app, fn, CONST]) => {
  test(app + ': ' + fn + '() arms AbortSignal.timeout', () => {
    const src = read(app);
    const body = transportBody(src, fn);
    assert.ok(/signal\s*:/.test(body),
      fn + ' passes no signal to fetch, so a hung connection is unbounded again');
    const hm = /signal\s*:\s*(\w+FetchTimeoutSignal)\s*\(\s*\)/.exec(body);
    assert.ok(hm, fn + ' does not get its signal from a FetchTimeoutSignal helper, '
      + 'so the feature-detect arm below cannot check it');
    // And the helper this transport names really exists and really reads the
    // constant -- a helper returning undefined unconditionally would satisfy
    // every other arm here while arming nothing.
    const hb = new RegExp('function\\s+' + hm[1]
      + '\\s*\\(\\s*\\)\\s*\\{([\\s\\S]{0,500}?)\\n\\}').exec(src);
    assert.ok(hb, hm[1] + '() is not defined in ' + app);
    assert.ok(new RegExp(CONST + '_FETCH_TIMEOUT_MS').test(hb[1]),
      hm[1] + '() does not reference ' + CONST + '_FETCH_TIMEOUT_MS');
    assert.ok(/AbortSignal\.timeout/.test(hb[1]),
      hm[1] + '() never calls AbortSignal.timeout');
  });
});

test('all 15 use the SAME 15s, or the platform has no single number', () => {
  const odd = [];
  APPS.forEach(([app, , CONST]) => {
    const m = new RegExp('var\\s+' + CONST + '_FETCH_TIMEOUT_MS\\s*=\\s*(\\d+)')
      .exec(read(app));
    if (!m) odd.push(app + ': not declared');
    else if (Number(m[1]) !== 15000) odd.push(app + ': ' + m[1] + 'ms');
  });
  assert.deepStrictEqual(odd, []);
});

test('every one is FEATURE-DETECTED, not assumed', () => {
  // An engine without AbortSignal.timeout must keep the previous unbounded
  // behaviour rather than throwing and breaking every server call in the app.
  // Both halves are required: `typeof` for an absent GLOBAL (ReferenceError) and
  // the try for an absent METHOD on a present global (TypeError).
  const bare = [];
  APPS.forEach(([app]) => {
    const hm = /function\s+\w+FetchTimeoutSignal\s*\(\s*\)\s*\{([\s\S]{0,500}?)\n\}/
      .exec(read(app));
    if (!hm) { bare.push(app + ': no FetchTimeoutSignal helper'); return; }
    const h = stripComments(hm[1]);
    if (!/typeof\s+AbortSignal\s*!==\s*'undefined'/.test(h)) {
      bare.push(app + ': no typeof guard on the global');
    }
    if (!/try\s*\{/.test(h)) bare.push(app + ': no try around the call');
    if (!/return\s+undefined\s*;/.test(h)) {
      bare.push(app + ': no explicit undefined fallback -- fetch must see no signal');
    }
  });
  assert.deepStrictEqual(bare, []);
});

section('and every transport SAYS something when the world fails');

// ── TIGHTENED 2026-09-11, BECAUSE THIS ARM LET ONE THROUGH THE DAY BEFORE ──
// It accepted `_sdReadFailed|LastErr|provisioned =` as evidence that a transport
// reports its failure. For fourteen apps that was harmless -- they all carry a
// console.warn as well, so the alternation never decided anything. For StoneDesk
// it decided everything: sdData() had ZERO console calls and passed on
// `_sdReadFailed[resource] = true` alone, which is a READ-path flag consumed by
// sdReadFailedNote() and the public-catalog guard and does NOTHING for a write.
//
// So the one app the arm actually had to catch was the one it cleared, and a
// write that never reached the server left no trace at all on the two call sites
// that read no result. Measured after tightening: all 15 pass, 14 directly and
// StoneDesk through sdDataFailed().
//
// A STATE FLAG IS NOT A REPORT. That is the whole lesson, and it is the same one
// CLAUDE.md already records for st(): "a boolean nobody reads is not a report."
// This arm now requires a console call, or ONE hop to a named function in the
// same file whose body makes one -- the same delegation rule
// sairn_storage_wrapper_honesty.js uses, and narrowed the same way, because
// StoneDesk's two wrappers legitimately share a reporter.
function reportsFailure(src, fn) {
  const body = transportBody(src, fn);
  if (/console\.(warn|error)/.test(body)) return true;
  const called = body.match(/(?<![\w.$])([A-Za-z_$][\w$]*)\s*\(/g) || [];
  return called.some((c) => {
    const nm = c.replace(/\s*\($/, '');
    const dm = new RegExp('(?:async\\s+)?function\\s+' + nm + '\\s*\\(').exec(src);
    if (!dm) return false;
    const o = src.indexOf('{', dm.index);
    let d = 0, k = o;
    for (; k < src.length && k - o < 4000; k++) {
      if (src[k] === '{') d++;
      else if (src[k] === '}' && --d === 0) break;
    }
    return /console\.(warn|error)/.test(stripComments(src.slice(dm.index, k + 1)));
  });
}

APPS.forEach(([app, fn]) => {
  test(app + ': ' + fn + '() reports a failure rather than swallowing it', () => {
    // A timer is useless if the thing it fires into is silent. Three transports
    // were: sairnscape's `catch (e) { return null; }`, sairnmechanical's
    // `.catch(function () { ... })` -- neither of which even took the error --
    // and StoneDesk's, which looked like it reported and was setting a flag.
    assert.ok(reportsFailure(read(app), fn),
      fn + ' discards its error -- the timeout is then worse than no timer, '
      + 'because it reads as protection. A state flag does not count: it is not '
      + 'read on the write path.');
  });
});

test('a STATE FLAG alone does not satisfy the arm above', () => {
  // The control that makes the tightening real rather than asserted. Without it
  // the rule could silently loosen again and every app would still pass.
  assert.strictEqual(
    reportsFailure('function xData(a,r){ try{} catch(e){ _xReadFailed[r]=true; '
                   + 'return null; } }', 'xData'), false);
  assert.strictEqual(
    reportsFailure('function xData(a,r){ try{} catch(e){ oops(r); return null; } }\n'
                   + 'function oops(r){ return false; }', 'xData'), false,
    'a hop to a helper that says nothing counts as speaking');
  assert.strictEqual(
    reportsFailure('function xData(a,r){ try{} catch(e){ oops(r); return null; } }\n'
                   + 'function oops(r){ console.warn(r); }', 'xData'), true,
    'the one hop StoneDesk actually uses stopped counting');
});

test('the two transports that DID swallow it now name the timeout', () => {
  ['sairnscape.html', 'sairnmechanical.html'].forEach((app) => {
    const fn = app === 'sairnscape.html' ? 'scpData' : 'mechData';
    const body = transportBody(read(app), fn);
    assert.ok(/TimeoutError/.test(body),
      app + ': the reader cannot tell a timeout from a dropped socket');
    assert.ok(/no answer in/.test(body),
      app + ': the message does not state the timeout');
  });
});

section('driven for real: a hang becomes the refusal each caller expects');

// The transports differ in what they need in scope, so each is given only what
// its own body reads. Nothing is stubbed that the assertion is about.
function driveCtx(app, fn, mode) {
  const state = { warns: [], fetches: 0, lastOpts: null };
  const ctx = {
    JSON, Object, Array, String, Number, Date, Math, Promise, setTimeout, clearTimeout,
    console: { warn: (...a) => state.warns.push(a.map(String).join(' ')),
               error: (...a) => state.warns.push(a.map(String).join(' ')),
               log: () => {} },
    AbortSignal: { timeout: (ms) => ({ __timeoutMs: ms }) },
    localStorage: { getItem: () => 'LIC-TEST', setItem: () => {}, removeItem: () => {} },
    sessionStorage: { getItem: () => null },
    DATA_API: 'https://sairn.vercel.app/api/sd-data',
    APP_ID: 'test',
    toast: () => {}, showToast: () => {}, scpToast: () => {},
    ld: () => 'LIC-TEST', scpLd: () => 'LIC-TEST',
    svLoad: () => 'LIC-TEST',
    K_LIC: 'lic', SF_DATA_API: 'u', SV_DATA_API: 'u', MECH_DATA_API: 'u',
    SCP_SESSION_KEY: 's', GRD_SESSION_KEY: 's',
    mechLic: () => 'LIC-TEST', mechHeaders: () => ({}),
    sbLicenseKey: () => 'LIC-TEST', bldLicenseKey: () => 'LIC-TEST',
    alfLicenseKey: () => 'LIC-TEST', sdnLicenseKey: () => 'LIC-TEST',
    senLicenseKey: () => 'LIC-TEST', sdLicenseKey: () => 'LIC-TEST',
    lawLicenseKey: () => 'LIC-TEST', legLicenseKey: () => 'LIC-TEST',
    fetch: function (url, o) {
      state.fetches += 1;
      state.lastOpts = o;
      if (mode === 'timeout') {
        const e = new Error('The operation was aborted due to timeout');
        e.name = 'TimeoutError';
        return Promise.reject(e);
      }
      if (mode === 'throw') return Promise.reject(new Error('NetworkError'));
      return Promise.resolve({ ok: true, status: 200,
        json: () => Promise.resolve({ ok: true, data: {}, provisioned: true }) });
    },
    __state: state,
  };
  // per-app scaffolding the transport reads
  ['_bldBackup', '_scLastDataError', '_scLastProvisioned', 'dntLastErr', 'lawLastErr',
   'legLastErr', '_sdAuthRefused', '_sdReadFailed', 'sbSession', 'bldSession',
   'alfSession', 'sdnSession', 'senSession'].forEach((n) => { ctx[n] = {}; });
  K.vm.createContext(ctx);
  const src = read(app);
  const prefix = APPS.find((a) => a[0] === app)[2];
  const cm = new RegExp('var\\s+' + prefix + '_FETCH_TIMEOUT_MS\\s*=\\s*\\d+\\s*;').exec(src);
  K.vm.runInContext(cm[0], ctx);
  const hm = new RegExp('function\\s+\\w+FetchTimeoutSignal\\s*\\(\\s*\\)\\s*\\{[\\s\\S]*?\\n\\}')
    .exec(src);
  assert.ok(hm, app + ': no FetchTimeoutSignal helper to load');
  K.vm.runInContext(hm[0], ctx);
  // BRACE-BALANCED FROM RAW, not K.grab's indent terminator. scData() and
  // mechData() are declared inside IIFEs and indented, so a terminator of
  // `\n}` at indent "" never matches them -- K.grab threw "not terminated"
  // rather than returning the wrong thing, which is the right failure but still
  // a failure. Two of fifteen, so the harness has to handle indentation.
  const dm = new RegExp('(?:async\\s+)?function\\s+' + fn + '\\s*\\(').exec(src);
  const o = src.indexOf('{', dm.index);
  let d = 0, k = o;
  for (; k < src.length; k++) {
    if (src[k] === '{') d++;
    else if (src[k] === '}' && --d === 0) break;
  }
  K.vm.runInContext(src.slice(dm.index, k + 1), ctx);

  // A TRANSPORT READS WHATEVER ITS APP HAPPENS TO HAVE IN SCOPE -- dntLicenseKey,
  // lawSessionToken, bldSession -- and the list is per-app and not worth
  // hardcoding fifteen times. Missing names are resolved by running once,
  // reading the ReferenceError, and defining a benign stub. Bounded at 20 so a
  // genuine bug cannot loop; and the names that get stubbed are PRINTED by the
  // arm that needs them, so this never silently substitutes something the
  // assertion was about.
  // WHAT SHAPE TO STUB IS DECIDED BY HOW THE TRANSPORT USES THE NAME, not by the
  // name itself. `dntLicenseKey` is called; `lawSessionToken` is read. Guessing
  // from the suffix got both wrong in the same run -- "is not a function" on one
  // and the reverse on the other -- so the source is consulted instead.
  const tbody = transportBody(src, fn);
  ctx.__stub = function (name) {
    const called = new RegExp('(?<![\\w.$])' + name + '\\s*\\(').test(tbody);
    if (called) {
      ctx[name] = function () { return 'LIC-TEST'; };
    } else if (/^_|Err$|Backup$|Refused$|Failed$/.test(name)) {
      ctx[name] = {};
    } else {
      ctx[name] = 'LIC-TEST';
    }
  };
  return ctx;
}

// Run a transport, stubbing any global it turns out to read. Returns the settled
// result via faultkit's within(), so a HANG is observable as a hang.
async function drive(ctx, fn, args) {
  for (let attempt = 0; attempt < 20; attempt++) {
    try {
      return await K.within(3000, ctx[fn].apply(null, args));
    } catch (e) {
      const m = /^(\w+) is not defined$/.exec(String(e && e.message));
      if (!m) throw e;
      ctx.__stub(m[1]);
    }
  }
  throw new Error('still undefined after 20 stubs -- the transport reads more '
    + 'globals than this harness can reasonably guess; name them explicitly');
}

APPS.forEach(([app, fn, , vocab]) => {
  test(app + ': a TIMEOUT resolves to the failure value, never a rejection', async () => {
    const ctx = driveCtx(app, fn, 'timeout');
    const r = await drive(ctx, fn, ['write', 'probe_resource', { id: 'X1' }]);
    assert.strictEqual(r.settled, true, 'the transport never settled on a timeout');
    assert.ok(!r.rejected,
      'the transport REJECTS on a timeout; every `await` caller would throw out '
      + 'of its handler and skip the toast -- the defect, relocated');
    if (vocab === 'status0') {
      assert.ok(r.value && r.value.status === 0,
        'expected {status:0}; this app\'s callers read r.status');
    } else {
      assert.strictEqual(r.value, null, 'expected null, this app\'s failure value');
    }
  });

  test(app + ': ...and the timeout is REPORTED', async () => {
    const ctx = driveCtx(app, fn, 'timeout');
    await drive(ctx, fn, ['write', 'probe_resource', { id: 'X1' }]);
    assert.ok(ctx.__state.warns.length > 0
              || /LastErr|_sdReadFailed/.test(transportBody(read(app), fn)),
      'a timed-out write said nothing and recorded nothing');
  });

  test(app + ': the signal really reached fetch, at 15s', async () => {
    const ctx = driveCtx(app, fn, 'ok');
    await drive(ctx, fn, ['read', 'probe_resource', {}]);
    const o = ctx.__state.lastOpts;
    assert.ok(o && o.signal, 'fetch was called with no signal');
    assert.strictEqual(o.signal.__timeoutMs, 15000);
  });
});

(async () => {
  for (const [name, fn] of tests) {
    if (fn === null) { console.log('--- ' + name + ' ---'); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
  }
  console.log('\n' + (fail === 0
    ? 'ALL ' + pass + ' TRANSPORT TIMEOUT ARMS PASS (15 apps)'
    : pass + ' passed, ' + fail + ' FAILED'));
  process.exit(fail === 0 ? 0 : 1);
})();
