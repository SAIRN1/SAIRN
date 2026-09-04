// tests/sairnlaw_hydrate.js
//
// Run:  node tests/sairnlaw_hydrate.js
//
// SAIRNlaw wrote to the server and NEVER read anything back. Measured before
// any code was written: twenty distinct resources written across 31 call
// sites, and exactly ONE read in the whole file -- shared_knowledge. No
// hydrate, merge or sync function of any name existed; the only DATA_API call
// site is inside sdnData(). Hank's work log recorded the same thing from the
// other side while building the deadline engine: "Every deadline in SAIRNlaw
// had been living on exactly one browser, never hydrated back, lost with the
// profile."
//
// So a firm's clients, matters, deadlines and trust ledger were on the server
// and unreachable: a second workstation, or the same one after a browser data
// clear, opened an empty app.
//
// AND ONLY FOUR OF THE TWENTY ARE REGISTERED AT ALL. law_clients, law_matters,
// law_trusttx and law_deadlines reach the server; the other fifteen are
// refused by the resource allowlist and never have. Proven live with a
// control -- on a bogus licence key law_matters answers 401 INVALID_LICENSE
// (past the resource gate) while law_invoices answers 400 "resource must be
// one of", same request shape, only the name different.
//
// These tests hold both halves: the hydrate does the right amount of work, and
// the fifteen that go nowhere now FAIL LOUDLY instead of reporting "server sync
// not yet enabled for this app" -- a sentence that was hiding them.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'sairnlaw.html'), 'utf8').replace(/\r\n/g, '\n');
const registry = require(path.join(ROOT, 'api', '_resources', 'sairnlaw.js'));

let pass = 0, fail = 0;
const queue = [];
function test(name, fn) { queue.push({ name, fn }); }
function section(t) { queue.push({ section: t }); }

function fnBodyAt(at) {
  const open = html.indexOf('{', at);
  let depth = 0;
  for (let i = open; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}') { depth--; if (depth === 0) return html.slice(at, i + 1); }
  }
  throw new Error('unbalanced braces');
}
function fnBody(name) {
  const at = html.indexOf(name);
  assert.ok(at > 0, 'not found in sairnlaw.html: ' + name);
  return fnBodyAt(at);
}
const stripComments = (src) => src.split('\n').filter((l) => !l.trim().startsWith('//')).join('\n');

function harness(opts) {
  opts = opts || {};
  const stored = {};
  const reads = [];
  const ctx = {
    JSON, Object, Array, String, Promise,
    console: { warn: () => {} },
    lawLicenseKey: () => (opts.noLicense ? '' : 'LAW-PINNACLE-2026'),
    ld: (k, d) => (opts.local && opts.local[k] ? JSON.parse(JSON.stringify(opts.local[k])) : d),
    st: (k, v) => { stored[k] = v; return true; },
    sdnData: (action, resource) => {
      reads.push(resource);
      const r = (opts.server || {})[resource];
      return Promise.resolve(r === undefined ? [] : r);
    },
    __stored: stored, __reads: reads,
  };
  vm.createContext(ctx);
  vm.runInContext(fnBody('var LAW_SYNC_RESOURCES=[') .split('\n')[0] + '\n'
    + "var LAW_SYNC_RESOURCES=['law_clients','law_matters','law_deadlines','law_trusttx'];\n"
    + fnBody('async function lawHydrateAll()'), ctx);
  return ctx;
}

// ═══════════════════════════════════════════════════════════════════════════
section('the hydrate reads back what the app has been writing');

test('server records not held locally are merged in', async () => {
  const c = harness({ server: { law_matters: [{ id: 'M-1' }, { id: 'M-2' }] } });
  const r = await c.lawHydrateAll();
  assert.strictEqual(r.merged, 2);
  // join(), not deepStrictEqual: the array is built inside the vm realm, so a
  // structural comparison fails on prototype identity rather than on content.
  assert.strictEqual(c.__stored.law_matters.map((x) => x.id).join(','), 'M-1,M-2');
});

test('a locally present id is NEVER overwritten by the server copy', async () => {
  const localEdit = { id: 'M-1', note: 'EDITED HERE' };
  const c = harness({
    local: { law_matters: [localEdit] },
    server: { law_matters: [{ id: 'M-1', note: 'server version' }, { id: 'M-2' }] },
  });
  const r = await c.lawHydrateAll();
  assert.strictEqual(r.merged, 1, 'only the unseen record should merge');
  assert.strictEqual(c.__stored.law_matters.find((x) => x.id === 'M-1').note, 'EDITED HERE');
});

test('all four registered resources are read', async () => {
  const c = harness({});
  await c.lawHydrateAll();
  assert.strictEqual(c.__reads.slice().sort().join(','),
    'law_clients,law_deadlines,law_matters,law_trusttx');
});

test('a FAILED read leaves local data alone and is counted as failed', async () => {
  // sdnData() returns null for a failure, a missing licence and an
  // unprovisioned table alike. None of those may render as "you have none" --
  // that is the defect this whole change exists to end.
  const c = harness({ local: { law_trusttx: [{ id: 'T-1' }] }, server: { law_trusttx: null } });
  const r = await c.lawHydrateAll();
  assert.strictEqual(r.failed, 1);
  assert.strictEqual(r.merged, 0);
  assert.strictEqual(c.__stored.law_trusttx, undefined, 'a failed read wrote to local storage');
});

test('an EMPTY server list is not a failure', async () => {
  const c = harness({ server: { law_clients: [] } });
  const r = await c.lawHydrateAll();
  assert.strictEqual(r.failed, 0);
  assert.strictEqual(r.merged, 0);
});

test('no licence key means no reads at all', async () => {
  const c = harness({ noLicense: true });
  const r = await c.lawHydrateAll();
  assert.strictEqual(c.__reads.length, 0);
  assert.strictEqual(r.merged, 0);
});

test('nothing is written when nothing merged -- a no-op boot costs no storage write', async () => {
  const c = harness({ local: { law_matters: [{ id: 'M-1' }] }, server: { law_matters: [{ id: 'M-1' }] } });
  await c.lawHydrateAll();
  assert.deepStrictEqual(Object.keys(c.__stored), []);
});

// ═══════════════════════════════════════════════════════════════════════════
section('it hydrates only what the server will actually serve');

test('every hydrated resource is REGISTERED -- otherwise every boot fails four times', () => {
  const listSrc = html.slice(html.indexOf('var LAW_SYNC_RESOURCES=['));
  const names = (listSrc.slice(0, listSrc.indexOf(']')).match(/'(law_\w+)'/g) || [])
    .map((s) => s.replace(/'/g, ''));
  assert.ok(names.length > 0, 'no sync list found');
  names.forEach((n) => assert.ok(registry.resources.indexOf(n) !== -1,
    n + ' is hydrated but is NOT in api/_resources/sairnlaw.js -- the read would be refused at the resource gate every boot'));
});

test('and the list is not silently smaller than the registry', () => {
  // If a resource is registered and writable but never hydrated, its records
  // are on the server and still unreachable -- which is the original defect,
  // narrowed rather than fixed.
  const listSrc = html.slice(html.indexOf('var LAW_SYNC_RESOURCES=['));
  const names = (listSrc.slice(0, listSrc.indexOf(']')).match(/'(law_\w+)'/g) || [])
    .map((s) => s.replace(/'/g, ''));
  const registeredLaw = registry.resources.filter((r) => r.indexOf('law_') === 0);
  assert.deepStrictEqual(names.slice().sort(), registeredLaw.slice().sort(),
    'the hydrate list and the registry disagree -- a registered resource that is never read back is still unreachable');
});

// ═══════════════════════════════════════════════════════════════════════════
section('the fifteen that go nowhere now fail loudly');

test('no CODE line still claims server sync is not enabled', () => {
  const code = stripComments(html);
  const hits = code.split('\n').filter((l) => l.indexOf('sync not yet enabled') !== -1);
  assert.deepStrictEqual(hits, [], 'still claimed on ' + hits.length + ' code line(s)');
});

test('an UNREGISTERED refusal gets a sentence a firm can act on, not the allowlist dump', () => {
  // The server answers "resource must be one of: profile, memory, employees,
  // ..." with 250+ names. That is a developer message. A firm needs to know
  // the record is on this computer only and that it is the app's gap.
  const ctx = { lawLastErr: { law_invoices: { code: 'HTTP_400', message: 'resource must be one of: profile, memory, employees' } } };
  vm.createContext(ctx);
  vm.runInContext(fnBody('function lawLastErrText(') + '\n' + fnBody('function lawLastErrCode(') + '\n'
    + fnBody('function lawWriteFailText('), ctx);
  const msg = ctx.lawWriteFailText('law_invoices', 'fallback');
  assert.match(msg, /NOT SAVED TO THE SERVER/);
  assert.match(msg, /only on this computer/i);
  assert.strictEqual(msg.indexOf('must be one of'), -1, 'the raw allowlist is shown to the user');
});

test("a real server refusal shows the SERVER's own words", () => {
  const ctx = { lawLastErr: { law_trusttx: { code: 'INSUFFICIENT_TRUST_BALANCE', message: 'That would overdraw the client ledger' } } };
  vm.createContext(ctx);
  vm.runInContext(fnBody('function lawLastErrText(') + '\n' + fnBody('function lawLastErrCode(') + '\n'
    + fnBody('function lawWriteFailText('), ctx);
  assert.match(ctx.lawWriteFailText('law_trusttx', 'fallback'), /overdraw the client ledger/);
});

test('with no recorded reason it falls back rather than showing an empty toast', () => {
  const ctx = { lawLastErr: {} };
  vm.createContext(ctx);
  vm.runInContext(fnBody('function lawLastErrText(') + '\n' + fnBody('function lawLastErrCode(') + '\n'
    + fnBody('function lawWriteFailText('), ctx);
  assert.strictEqual(ctx.lawWriteFailText('law_matters', 'my fallback'), 'my fallback');
  assert.ok(ctx.lawWriteFailText('law_matters', '').length > 0, 'an empty fallback must not produce an empty toast');
});

test('each write path asks for the error of the resource IT writes', () => {
  // A helper called with the wrong resource returns another resource's stale
  // message, which reads as a real explanation and is worse than the generic
  // one it replaced. Same load-bearing assertion as the SAIRNdental suite.
  const re = /(?:async\s+)?function\s+(\w+)\s*\(/g;
  let m, checked = 0;
  const problems = [];
  while ((m = re.exec(html)) !== null) {
    let body;
    try { body = fnBodyAt(m.index); } catch (e) { continue; }
    const code = stripComments(body);
    const writes = [...code.matchAll(/sdnData\('write','(\w+)'/g)].map((x) => x[1]);
    if (!writes.length) continue;
    const asked = [...code.matchAll(/lawWriteFailText\('(\w+)'/g)].map((x) => x[1]);
    if (!asked.length) continue;
    checked++;
    asked.forEach((a) => {
      if (writes.indexOf(a) === -1) problems.push(m[1] + " asks for '" + a + "' but writes '" + writes.join('/') + "'");
    });
  }
  assert.ok(checked >= 20, 'expected 20+ paired write paths, checked ' + checked);
  assert.deepStrictEqual(problems, [], problems.join('; '));
});

// ═══════════════════════════════════════════════════════════════════════════
section('it runs at boot without delaying first paint');

test('hydrate is called AFTER init(), and a failed read is reported', () => {
  const at = html.indexOf('lawHydrateAll().then(');
  assert.ok(at > 0, 'the hydrate is never called');
  const before = html.slice(Math.max(0, at - 400), at);
  assert.ok(before.indexOf('init();') !== -1,
    'the hydrate runs before init() -- first paint would wait on the network');
  const after = html.slice(at, at + 700);
  assert.match(after, /if\(r\.failed\)/, 'a failed read is not reported');
  assert.match(after, /records saved on another computer are not being shown/,
    'the failure message does not distinguish "could not read" from "you have none"');
  assert.match(after, /if\(r\.merged\)/);
});

// ═══════════════════════════════════════════════════════════════════════════
(async () => {
  for (const item of queue) {
    if (item.section) { console.log('--- ' + item.section + ' ---'); continue; }
    try { await item.fn(); console.log('  ok   ' + item.name); pass++; }
    catch (e) { console.log('  FAIL ' + item.name + '\n       ' + e.message); fail++; }
  }
  console.log('\nsairnlaw_hydrate: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
