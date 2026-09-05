// tests/sairnlegacy_write_failure_voice.js
//
// Run:  node tests/sairnlegacy_write_failure_voice.js
//
// Every save path in sairnlegacy.html that failed to reach the server said
//
//     "Saved on this device only -- server sync not yet enabled for this app"
//
// on 57 sites. THAT SENTENCE WAS FALSE IN EVERY CASE. Sync is enabled for this
// app: all 37 resources it calls are registered — 36 in
// api/_resources/sairnlegacy.js plus shared_knowledge in shared.js, checked
// rather than assumed. So a funeral home reading it went looking for a feature
// flag instead of the real refusal, which the app had thrown away: sdnData()
// returned null on every failure and kept no memory of the reason.
//
// DELIBERATELY DIFFERENT FROM SAIRNlaw's version of this finding. There the
// same sentence was hiding FIFTEEN unregistered resources that never reached
// the server at all. Here the registry is complete, so the defect is only the
// voice — a negative result, recorded so nobody goes looking for a second
// registry gap that is not there.
//
// THE PAIRING ASSERTION IS THE POINT OF THIS FILE. A helper that reads a
// shared per-resource map will happily return ANOTHER resource's message if a
// call site passes the wrong name — a wrong reason stated confidently, which
// is the defect being replaced wearing a new disguise. Every call site is
// paired here against the resource its own function actually writes.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const FILE = 'sairnlegacy.html';
const SRC = fs.readFileSync(path.join(ROOT, FILE), 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

function grab(src, sig) {
  const i = src.indexOf(sig);
  assert.ok(i > 0, sig + ' not found');
  const rel = src.slice(i).search(/\r?\n\}/);
  assert.ok(rel > 0, sig + ' is not terminated');
  return src.slice(i, i + rel) + '\n}';
}

function load(recorded) {
  const ctx = { legLastErr: Object.assign({}, recorded), String: String, RegExp: RegExp };
  vm.createContext(ctx);
  ['function legLastErrText(resource){', 'function legLastErrCode(resource){',
   'function legWriteFailText(resource,fallback){'].forEach((sig) => {
    vm.runInContext(grab(SRC, sig), ctx);
  });
  return ctx;
}

const FALLBACK = 'Saved on this device only -- it did not reach the server';

section("the server's own words come first");

test("a recorded server message is returned verbatim", () => {
  const ctx = load({ leg_cases: { code: 'HTTP_409', message: 'A case with that number already exists.' } });
  assert.strictEqual(ctx.legWriteFailText('leg_cases', FALLBACK),
    'A case with that number already exists.');
});

test('a MISSING LICENCE KEY says so, and says what to do about it', () => {
  // This used to arrive as the same silent null as a server refusal, so both
  // read as "sync not yet enabled". Only one of them has an action attached.
  const ctx = load({ leg_cases: { code: 'NO_LICENSE', message: '' } });
  const t = ctx.legWriteFailText('leg_cases', FALLBACK);
  assert.match(t, /no licence key/);
  assert.match(t, /Settings/);
});

test('an UNREGISTERED resource gets a sentence a funeral home can act on', () => {
  // The raw server reply here is "resource must be one of: ..." with the whole
  // allowlist — a developer message, in a toast, to a funeral director.
  const ctx = load({ leg_x: { code: 'HTTP_400', message: 'resource must be one of: leg_cases, leg_plots, ...' } });
  const t = ctx.legWriteFailText('leg_x', FALLBACK);
  assert.match(t, /not set up on the server yet/);
  assert.ok(!/must be one of/.test(t), 'the developer message reached the user');
});

test('nothing recorded falls back to the CALLER\'s sentence, not a generic one', () => {
  const ctx = load({});
  assert.strictEqual(ctx.legWriteFailText('leg_cases', FALLBACK), FALLBACK);
});

test('and with no fallback either, it still never returns empty', () => {
  const ctx = load({});
  const t = ctx.legWriteFailText('leg_cases', '');
  assert.ok(t.length > 20, 'a failed write produced an empty toast');
  assert.match(t, /on this computer only/);
});

test('NOT ONE reply claims sync is unavailable for this app', () => {
  const cases = [
    {}, { leg_cases: { code: 'NO_LICENSE', message: '' } },
    { leg_cases: { code: 'NETWORK', message: 'Failed to fetch' } },
    { leg_cases: { code: 'HTTP_500', message: 'boom' } },
  ];
  cases.forEach((rec) => {
    const t = load(rec).legWriteFailText('leg_cases', FALLBACK);
    assert.ok(!/not yet enabled/.test(t), 'the false claim came back: ' + t);
  });
});

section('THE PAIRING — every call site names the resource its own function writes');

// Enclosing-function spans, computed once.
const funcs = [];
const fre = /\n\s*(?:async\s+)?function\s+(\w+)\s*\(/g;
let fm;
while ((fm = fre.exec(SRC)) !== null) funcs.push([fm.index, fm[1]]);
function spanOf(pos) {
  const starts = funcs.filter(([s]) => s <= pos);
  if (!starts.length) return null;
  const [fs2, name] = starts[starts.length - 1];
  const later = funcs.filter(([s]) => s > pos);
  return { name, from: fs2, to: later.length ? later[0][0] : SRC.length };
}

// A function "writes" a resource through sdnData('write', ...) or, for the one
// path that needs the raw response, a direct fetch carrying resource:'...'.
function resourcesWritten(body) {
  const a = [...body.matchAll(/sdnData\(\s*'write'\s*,\s*'(\w+)'/g)].map((m) => m[1]);
  const b = [...body.matchAll(/resource\s*:\s*'(\w+)'/g)].map((m) => m[1]);
  return new Set(a.concat(b));
}

const sites = [...SRC.matchAll(/legWriteFailText\(\s*([^,]+?)\s*,/g)]
  .filter((m) => SRC.slice(0, m.index).lastIndexOf('function legWriteFailText') !==
                 SRC.slice(0, m.index).length - 0 || true)
  .filter((m) => !/^\s*resource\s*$/.test(m[1]));   // the definition itself

test('every call site passes a resource literal (or a conditional between two)', () => {
  sites.forEach((m) => {
    const arg = m[1];
    assert.ok(/^'(\w+)'$/.test(arg) || /\?\s*'(\w+)'\s*:\s*'(\w+)'$/.test(arg),
      'unreadable resource argument at line ' +
      (SRC.slice(0, m.index).split('\n').length) + ': ' + arg);
  });
});

test('and that resource is one the ENCLOSING function actually writes', () => {
  const bad = [];
  sites.forEach((m) => {
    const names = [...m[1].matchAll(/'(\w+)'/g)].map((x) => x[1]);
    const sp = spanOf(m.index);
    const written = resourcesWritten(SRC.slice(sp.from, sp.to));
    names.forEach((n) => {
      if (!written.has(n)) {
        bad.push(sp.name + ' -> ' + n + ' (writes: ' + [...written].join(',') + ')');
      }
    });
  });
  assert.deepStrictEqual(bad, [],
    'a call site names a resource its own function never writes, so the helper ' +
    'can return another write\'s message:\n       ' + bad.join('\n       '));
});

test('the pairing covers every site — 57 of them, counted not assumed', () => {
  assert.strictEqual(sites.length, 57,
    'expected 57 call sites, found ' + sites.length +
    '. If a save path was added, pair it; if one was removed, update this number.');
});

section('the false sentence is gone from the source');

test('it survives only in the historical comment that records it was wrong', () => {
  const hits = [...SRC.matchAll(/server sync not yet enabled/g)];
  assert.strictEqual(hits.length, 1, 'expected exactly one occurrence, found ' + hits.length);
  const lineStart = SRC.lastIndexOf('\n', hits[0].index) + 1;
  assert.ok(SRC.slice(lineStart, hits[0].index).trimStart().startsWith('//'),
    'the surviving occurrence is live code, not a comment');
});

test('sdnData records a reason on EVERY failure path, including no licence', () => {
  const body = grab(SRC, 'function sdnData(action,resource,payload,withSession){');
  assert.match(body, /NO_LICENSE/, 'a missing licence key is still an unexplained null');
  assert.match(body, /legLastErr\[resource\]=\{code:/, 'a server refusal is not recorded');
  assert.match(body, /code:'NETWORK'/, 'a network failure is not recorded');
  assert.match(body, /delete legLastErr\[resource\]/,
    'a later SUCCESS never clears the stale reason, so the next failure lies');
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' WRITE-FAILURE-VOICE ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
