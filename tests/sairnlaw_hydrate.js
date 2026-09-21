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

// The whole `var LAW_SYNC_RESOURCES=[...]` statement, comments and all.
function syncListSrc() {
  const at = html.indexOf('var LAW_SYNC_RESOURCES=[');
  assert.ok(at > 0, 'LAW_SYNC_RESOURCES not found');
  const end = html.indexOf('];', at);
  assert.ok(end > at, 'unterminated LAW_SYNC_RESOURCES');
  return html.slice(at, end + 2);
}
function syncNames() {
  return (stripComments(syncListSrc()).match(/'(law_\w+)'/g) || []).map((x) => x.replace(/'/g, ''));
}

function harness(opts) {
  opts = opts || {};
  const stored = {};
  const raw = Object.assign({}, opts.raw || {});
  const reads = [];
  const ctx = {
    JSON, Object, Array, String, Promise,
    console: { warn: () => {}, error: () => {} },
    lawLicenseKey: () => (opts.noLicense ? '' : 'LAW-PINNACLE-2026'),
    ld: (k, d) => (opts.local && opts.local[k] ? JSON.parse(JSON.stringify(opts.local[k])) : d),
    st: (k, v) => { stored[k] = v; raw[k] = JSON.stringify(v); return true; },
    // The synced-id map is read RAW (localStorage.getItem) rather than through
    // ld(), because "absent" and "corrupt" must be told apart -- see the
    // server-wins comment above lawHydrateAll(). So the harness needs a real
    // enough localStorage for that read to work, and `opts.raw` is how an arm
    // seeds or corrupts it.
    localStorage: {
      getItem: (k) => (Object.prototype.hasOwnProperty.call(raw, k) ? raw[k] : null),
      setItem: (k, v) => { raw[k] = String(v); },
    },
    sdnData: (action, resource) => {
      reads.push(resource);
      const r = (opts.server || {})[resource];
      return Promise.resolve(r === undefined ? [] : r);
    },
    __stored: stored, __reads: reads, __raw: raw,
  };
  vm.createContext(ctx);
  // The REAL declaration is lifted, not retyped. An earlier version of this
  // harness hardcoded the four-name list, so when the list grew to nineteen
  // the suite would have tested a list the app no longer has -- the fixture
  // drifting from the code it exists to check.
  // THE MERGE MOVED OUT OF THE HYDRATE, 2026-09-21. lawHydrateAll() now calls
  // the shared lawServerWinsMerge() -- one copy of a rule seven apps hold,
  // driven across all of them by tests/server_wins_hydration.js -- and runs
  // the one-time lawSyncedBootstrap() first. All of it is lifted out of the
  // shipped file rather than retyped.
  const onelineVar = (name) =>
    html.slice(html.indexOf('var ' + name + "='"), html.indexOf(';', html.indexOf('var ' + name + "='")) + 1);
  vm.runInContext([
    syncListSrc(),
    onelineVar('LAW_SYNCED_KEY'),
    onelineVar('LAW_BOOTSTRAP_KEY'),
    'var lawBootstrappedNow=false;',
    fnBody('function lawSyncedRead()'),
    fnBody('function lawMarkSynced('),
    fnBody('function lawSyncedBootstrap('),
    fnBody('function lawHydrateLoad('),
    fnBody('function lawHydrateStore('),
    fnBody('function lawServerWinsMerge('),
    fnBody('async function lawHydrateAll()'),
  ].join('\n'), ctx);
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

// ── THIS ARM USED TO ASSERT THE OPPOSITE, AND THAT IS THE RECORD ──────────
// It read "a locally present id is NEVER overwritten by the server copy" and
// it pinned the additive merge deliberately -- the behaviour was a DESIGN, and
// the arm was here so nobody could change it by accident.
//
// Michael's decision on 2026-09-21 changed the design: server-wins. The arm is
// INVERTED rather than deleted, because a pin that is quietly dropped when it
// becomes inconvenient is worse than no pin. What it guards now is the new
// rule and its carve-out, with the same intent.
//
// WHY THE OLD DESIGN'S DISCLOSURE UNDERSTATED THE COST: it framed the gap as
// two devices editing the SAME record between hydrations. It was never only
// about concurrent edits -- ANY field corrected on the server was invisible
// FOREVER to a device that already held that id, with nothing racing. The case
// that found it: saveInvoice() marks time entries invoiced:true, the server
// now says so, and a workstation that hydrated them last week still offers the
// same hours as unbilled.
test('a locally present id IS overwritten by the server copy, once it is known to be synced', async () => {
  const c = harness({
    local: { law_matters: [{ id: 'M-1', note: 'EDITED HERE' }] },
    server: { law_matters: [{ id: 'M-1', note: 'server version' }, { id: 'M-2' }] },
    // law_synced_bootstrap set: this is a device whose one-time bootstrap
    // happened on an earlier load. Without it the bootstrap would run HERE and
    // suppress overwriting for the whole call, and the arm would pass while
    // asserting nothing about the merge.
    raw: { law_synced_bootstrap: '1', law_synced_ids: JSON.stringify({ law_matters: ['M-1'] }) },
  });
  const r = await c.lawHydrateAll();
  assert.strictEqual(c.__stored.law_matters.find((x) => x.id === 'M-1').note, 'server version',
    'the local copy survived -- this is the additive behaviour server-wins replaced');
  assert.strictEqual(r.merged, 2, 'an overwrite counts as merged, the same as an append');
});

test('but a record whose FIRST push never landed keeps its local value', async () => {
  // The carve-out. The server's row for an id this device has never
  // successfully pushed belongs to somebody else -- newId() is prefix +
  // Date.now() + a 0-999 draw, so a same-millisecond collision is possible.
  // `law_matters` is SEEDED here (the key exists) and M-1 is not in it, which
  // is what makes this the pending-first-push case rather than a first run.
  const c = harness({
    local: { law_matters: [{ id: 'M-1', note: 'never pushed' }] },
    server: { law_matters: [{ id: 'M-1', note: 'somebody else' }] },
    raw: { law_synced_bootstrap: '1', law_synced_ids: JSON.stringify({ law_matters: [] }) },
  });
  await c.lawHydrateAll();
  assert.strictEqual(c.__stored.law_matters, undefined,
    'a record whose own push never landed was overwritten by a stranger');
});

// ── AND THIS ARM WAS INVERTED TOO, HOURS AFTER IT WAS WRITTEN ────────────
// It read "a FIRST run seeds what the server already had" and asserted the
// first hydrate OVERWRITES on an id match -- which is what the first version
// of server-wins did, and which silently discarded whatever local edit was
// sitting there at the moment of upgrade. Michael's second decision replaced
// that with a read-only bootstrap: it RECORDS what the device holds and
// overwrites nothing, and the server's copy arrives one load later. The arm
// is inverted rather than deleted, and the two halves of the bounded cost are
// asserted separately below.
test('a FIRST run RECORDS what the device holds and overwrites NOTHING', async () => {
  const c = harness({
    local: { law_matters: [{ id: 'M-1', note: 'stale' }] },
    server: { law_matters: [{ id: 'M-1', note: 'server version' }] },
  });
  await c.lawHydrateAll();
  assert.ok(!c.__stored.law_matters || c.__stored.law_matters[0].note === 'stale',
    'the bootstrap load overwrote a local record -- the whole point of it is that it does not');
  assert.ok(JSON.parse(c.__raw.law_synced_ids).law_matters.indexOf('M-1') !== -1,
    'the id was not recorded, so the NEXT load would treat it as never-pushed');
});

test('and the load AFTER the bootstrap takes the server copy -- the cost is ONE hydrate', async () => {
  const first = harness({
    local: { law_matters: [{ id: 'M-1', note: 'stale' }] },
    server: { law_matters: [{ id: 'M-1', note: 'server version' }] },
  });
  await first.lawHydrateAll();
  const second = harness({
    local: { law_matters: [{ id: 'M-1', note: 'stale' }] },
    server: { law_matters: [{ id: 'M-1', note: 'server version' }] },
    raw: { law_synced_bootstrap: '1', law_synced_ids: first.__raw.law_synced_ids },
  });
  await second.lawHydrateAll();
  assert.strictEqual(second.__stored.law_matters[0].note, 'server version');
});

// ── NOT EVERY REGISTERED RESOURCE IS A TABLE (2026-09-18) ────────────────────
// This suite was RED for three days and nobody read it. 4eaa3f05 (2026-09-15)
// registered `law_trust_reconcile`, and these two arms assert
// hydrate-set == registry-set, so both failed the moment it landed. Driven: the
// only difference either arm reports is that one name.
//
// THE ARMS WERE RIGHT TO FAIL AND THE PREMISE IS WHAT CHANGED. Every other
// law_ resource is a stored table whose rows the client keeps a local copy of.
// `law_trust_reconcile` is a COMPUTED READ -- api/sd-data.js runs
// reconcileTrustLedger() over law_trusttx and law_bankstatements and returns
// the verdict. There is no table behind it and nothing to merge; hydrating it
// would cache a point-in-time reconciliation as if it were data, which is the
// worse outcome on the one figure a bar association audits.
//
// SO THE SET IS NARROWED, EXPLICITLY, WITH THE REASON BESIDE EACH NAME, and
// the exclusion is itself asserted below -- a bare exclusion list is how a real
// gap goes quiet. A future derived resource has to be added here deliberately,
// and a future TABLE added here by mistake stops being hydrated silently, which
// is why the list carries a justification a reader can check rather than a
// count somebody can bump.
const NOT_HYDRATED = {
  law_trust_reconcile:
    'a COMPUTED read, not a table -- api/sd-data.js reconciles law_trusttx '
    + 'against law_bankstatements and returns a verdict. Nothing to merge, and '
    + 'caching a point-in-time reconciliation as local data would make a stale '
    + 'verdict look like a record.'
};

function hydratableLaw() {
  return registry.resources
    .filter((r) => r.indexOf('law_') === 0)
    .filter((r) => !Object.prototype.hasOwnProperty.call(NOT_HYDRATED, r))
    .slice().sort();
}

test('every NOT_HYDRATED name is really registered, and really has a reason', () => {
  const names = Object.keys(NOT_HYDRATED);
  assert.ok(names.length > 0, 'the exclusion list is empty -- delete it rather '
    + 'than leaving a mechanism with nothing in it');
  names.forEach((n) => {
    assert.ok(registry.resources.indexOf(n) !== -1,
      n + ' is excluded from hydration but is not in the registry at all -- '
      + 'a stale exclusion silently widens as the registry changes');
    assert.ok(String(NOT_HYDRATED[n]).trim().length >= 60,
      n + ' carries no real reason, and an exclusion with no reason is how a '
      + 'resource nobody reads back stops being a finding');
  });
});

test('EVERY HYDRATABLE registered resource is read -- derived from the registry, not retyped', async () => {
  const c = harness({});
  await c.lawHydrateAll();
  const expected = hydratableLaw();
  assert.strictEqual(c.__reads.slice().sort().join(','), expected.join(','),
    'the hydrate reads a different set than the registry declares');
  assert.ok(expected.length >= 19,
    'expected at least nineteen hydratable law resources, found ' + expected.length);
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

test('no RESOURCE is written when nothing changed -- a no-op boot costs no data write', async () => {
  // NARROWED 2026-09-21 and the narrowing is the point. This used to assert
  // that NOTHING was written at all. Server-wins writes one more thing: the
  // synced-id map, which records that these resources have now been seeded --
  // and it has to be written even on a no-op, because the PRESENCE of a
  // resource's key is what says it was seeded. Without that write every later
  // hydrate re-enters the never-seeded branch and overwrites unconditionally.
  //
  // So the arm still holds the property that matters -- a boot that changed no
  // record does not rewrite the record store -- and stops claiming the one
  // that is no longer true.
  const c = harness({
    local: { law_matters: [{ id: 'M-1' }] },
    server: { law_matters: [{ id: 'M-1' }] },
    raw: { law_synced_ids: JSON.stringify({ law_matters: ['M-1'] }) },
  });
  await c.lawHydrateAll();
  assert.deepStrictEqual(
    Object.keys(c.__stored).filter((k) => k !== 'law_synced_ids' && k !== 'law_synced_bootstrap'), [],
    'a hydrate that changed no record still wrote to a record store');
});

// ═══════════════════════════════════════════════════════════════════════════
section('it hydrates only what the server will actually serve');

test('every hydrated resource is REGISTERED -- otherwise every boot fails four times', () => {
  const names = syncNames();
  assert.ok(names.length > 0, 'no sync list found');
  names.forEach((n) => assert.ok(registry.resources.indexOf(n) !== -1,
    n + ' is hydrated but is NOT in api/_resources/sairnlaw.js -- the read would be refused at the resource gate every boot'));
});

test('and the list is not silently smaller than the registry', () => {
  // If a resource is registered and writable but never hydrated, its records
  // are on the server and still unreachable -- which is the original defect,
  // narrowed rather than fixed.
  const names = syncNames();
  assert.strictEqual(names.slice().sort().join(','), hydratableLaw().join(','),
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
