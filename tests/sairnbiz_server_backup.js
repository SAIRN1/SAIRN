// tests/sairnbiz_server_backup.js
//
// Run:  node tests/sairnbiz_server_backup.js
//
// SAIRNbiz's server backup, tested where it can actually be wrong.
//
// The feature is one hook inside st() -- the single function every write in
// that file already goes through -- so the risk is not that it fails loudly.
// It is that it does the wrong AMOUNT of work, silently:
//
//   * pushes NOTHING, and the backup everyone believes exists is empty;
//   * pushes EVERYTHING on every render, turning a repaint into a burst of
//     network writes;
//   * pushes during seed(), filling a real company's tables with Pinnacle
//     Stone & Design demo rows;
//   * pushes a record the browser itself failed to store, so the server and
//     the device disagree about what was saved;
//   * skips the four collections whose records have no id, so four of nine
//     back up nothing while the other five work;
//   * renders a FAILED read as "you have nothing", which is the shape that
//     told a roofing contractor "No jobs yet" earlier the same day.
//
// None of those throw. Each one is a green app doing the wrong thing, which is
// why the assertions below count calls and inspect messages rather than
// checking for errors.
//
// The functions are lifted out of the real file rather than reimplemented, so
// a change to sairnbiz.html that breaks them fails here.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
// Line endings normalised so the slice markers below can be written with plain
// \n -- the file may be CRLF on disk and an assumption about that is not worth
// a brittle test.
const html = fs.readFileSync(path.join(ROOT, 'sairnbiz.html'), 'utf8').replace(/\r\n/g, '\n');
const sdData = fs.readFileSync(path.join(ROOT, 'api', 'sd-data.js'), 'utf8').replace(/\r\n/g, '\n');
const schema = fs.readFileSync(path.join(ROOT, 'sql', 'sairnbiz_data_schema.sql'), 'utf8').replace(/\r\n/g, '\n');
const registry = require(path.join(ROOT, 'api', '_resources', 'sairnbiz.js'));
const merged = require(path.join(ROOT, 'api', '_resources', 'index.js'));

let pass = 0, fail = 0;
const queue = [];
function test(name, fn) { queue.push({ name, fn }); }
function section(t) { queue.push({ section: t }); }

// Pull the real source out of the page. Anchored on markers rather than line
// numbers, which move.
function slice(src, startMark, endMark) {
  const a = src.indexOf(startMark);
  assert.ok(a > 0, 'not found: ' + startMark);
  const b = src.indexOf(endMark, a);
  assert.ok(b > a, 'end marker not found after ' + startMark);
  return src.slice(a, b);
}

const ST_SRC = slice(html, 'var _sbSaveFailed={};', 'function ld(k,d){');
const SYNC_SRC = slice(html, "var SB_SYNCED=['sb_invs'", 'window.sbHydrateAll=sbHydrateAll;');

// ---------------------------------------------------------------------------
// Harness. The stub is at fetch(), not at sbBackupFetch(), so the response
// handling -- NOT_PROVISIONED, provisioned:false, a 500, a missing session --
// is exercised as written rather than assumed.
// ---------------------------------------------------------------------------
function harness(opts, syncOverride, stOverride) {
  opts = opts || {};
  const store = Object.assign({}, opts.store || {});
  if (!opts.noLicense && !('sb_lic' in store)) store.sb_lic = JSON.stringify('SD-PINNACLE-2026');
  const calls = [], toasts = [], warns = [];
  let initCount = 0;

  function respond(body) {
    const rows = (opts.serverRows && opts.serverRows[body.resource]) || [];
    if (body.action === 'read') {
      if (opts.readFails) return { status: 500, body: { error: { code: 'BOOM' } } };
      if (opts.notProvisioned) return { status: 200, body: { ok: true, data: [], provisioned: false } };
      return { status: 200, body: { ok: true, data: rows, provisioned: true } };
    }
    if (opts.notProvisioned) return { status: 503, body: { error: { code: 'NOT_PROVISIONED' } } };
    if (opts.writeFails) return { status: 500, body: { error: { code: 'BOOM' } } };
    return { status: 200, body: { ok: true, data: body.payload } };
  }

  const ctx = {
    JSON, Array, Object, String, Date, Promise, setTimeout,
    console: { warn: (...a) => warns.push(a.join(' ')), log: () => {}, error: () => {} },
    localStorage: {
      setItem: (k, v) => { if (opts.storageFull) throw new Error('QuotaExceededError'); store[k] = v; },
      getItem: (k) => (k in store ? store[k] : null)
    },
    sessionStorage: { getItem: () => (opts.noSession ? null : 'session-token-abc') },
    ld: (k, d) => { try { const r = store[k]; return r === undefined ? d : JSON.parse(r); } catch (e) { return d; } },
    DATA_API: 'https://sairn.test/api/sd-data',
    APP_ID: 'sairnbiz',
    SB_SESSION_KEY: 'sb_session_token',
    toast: (m) => toasts.push(String(m)),
    init: () => { initCount++; },
    document: { getElementById: () => ({}) },
    fetch: (url, init) => {
      const body = JSON.parse(init.body);
      calls.push({ resource: body.resource, action: body.action, payload: body.payload, headers: init.headers });
      const r = respond(body);
      return Promise.resolve({ ok: r.status >= 200 && r.status < 300, status: r.status, json: () => Promise.resolve(r.body) });
    },
    window: {},
    __store: store, __calls: calls, __toasts: toasts, __warns: warns,
    __initCount: () => initCount
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext((syncOverride || SYNC_SRC) + '\n' + (stOverride || ST_SRC), ctx);
  return ctx;
}

// Pushes are fire-and-forget promise chains. Drain the microtask queue.
const flush = () => new Promise((r) => setTimeout(r, 0));

const writesOf = (c) => c.__calls.filter((x) => x.action === 'write');

const INV_A = { id: 'INV-2601', cust: 'Hartley', amt: 8420, status: 'Paid' };
const INV_B = { id: 'INV-2602', cust: 'Lakewood', amt: 3890, status: 'Sent' };
const RUN_A = { id: 'PR1a2b3c', run_on: '2026-09-04', employees: 8, gross: 12000 };

// ═══════════════════════════════════════════════════════════════════════════
section('the nine collections agree across all four files');

test('registry, server handler, client list and SQL declare the same nine', () => {
  const declared = registry.resources.slice().sort();
  assert.strictEqual(declared.length, 9, 'registry should declare 9 resources');

  const handlerBlock = slice(sdData, 'const SB_RESOURCES = {', '};');
  const handled = (handlerBlock.match(/\bsb_[a-z_]+(?=:)/g) || []).sort();
  assert.deepStrictEqual(handled, declared, 'sd-data.js SB_RESOURCES disagrees with the registry');

  const clientList = slice(html, "var SB_SYNCED=['sb_invs'", '];');
  const client = (clientList.match(/'(sb_[a-z_]+)'/g) || []).map((s) => s.replace(/'/g, '')).sort();
  assert.deepStrictEqual(client, declared, 'sairnbiz.html SB_SYNCED disagrees with the registry');

  declared.forEach((r) => {
    assert.ok(schema.includes('create table if not exists public.' + r + ' ('), 'no table in the SQL for ' + r);
    assert.ok(schema.includes('grant select, insert, update on public.' + r + ' to service_role;'), 'no grant for ' + r);
  });
});

test('every id column in the handler exists in the SQL table it names', () => {
  const handlerBlock = slice(sdData, 'const SB_RESOURCES = {', '};');
  const pairs = handlerBlock.match(/sb_[a-z_]+:\s*'[a-z_]+'/g) || [];
  assert.strictEqual(pairs.length, 9);
  pairs.forEach((p) => {
    const [res, col] = p.split(':').map((s) => s.trim().replace(/'/g, ''));
    const table = slice(schema, 'create table if not exists public.' + res + ' (', ');');
    assert.ok(table.includes('\n  ' + col + ' text not null,'), res + ' has no ' + col + ' column');
    assert.ok(table.includes('unique (license_hash, ' + col + ')'), res + ' is not unique on (license_hash, ' + col + ')');
  });
});

test('the SQL grants no delete anywhere', () => {
  assert.ok(!/\bdelete\b/i.test(schema.replace(/^--.*$/gm, '')), 'a delete grant appeared in the schema');
});

test('no sb_ resource collides with another app', () => {
  registry.resources.forEach((r) => {
    assert.strictEqual(merged.OWNER_BY_RESOURCE[r], 'sairnbiz', r + ' is not owned by sairnbiz');
  });
  assert.strictEqual(new Set(merged.RESOURCE_NAMES).size, merged.RESOURCE_NAMES.length, 'duplicate resource names');
});

test('the eight excluded collections carry a written reason, not silence', () => {
  const src = fs.readFileSync(path.join(ROOT, 'api', '_resources', 'sairnbiz.js'), 'utf8');
  ['sb_emps', 'sb_co', 'sb_cfg', 'sb_incidents', 'sb_lic', 'sb_role', 'sb_seeded', 'sb_sync']
    .forEach((k) => assert.ok(new RegExp('//\\s*' + k + ' --').test(src), 'no recorded reason for excluding ' + k));
});

// ═══════════════════════════════════════════════════════════════════════════
section('the backup actually happens, and only for what changed');

test('a new record on a synced collection is pushed', async () => {
  const c = harness();
  c.st('sb_invs', [INV_A]);
  await flush();
  const w = writesOf(c);
  assert.strictEqual(w.length, 1);
  assert.strictEqual(w[0].resource, 'sb_invs');
  assert.strictEqual(w[0].payload.id, 'INV-2601');
});

test('the local write still happens -- the hook never replaces it', async () => {
  const c = harness();
  assert.strictEqual(c.st('sb_invs', [INV_A]), true, 'st() should report a successful write');
  await flush();
  assert.deepStrictEqual(JSON.parse(c.__store.sb_invs), [INV_A]);
});

test('rewriting an UNCHANGED array pushes nothing', async () => {
  // The one that stops a repaint becoming a burst of writes. rAP() and rTrain()
  // both persist their whole collection from inside a render.
  const c = harness();
  c.st('sb_invs', [INV_A, INV_B]);
  await flush();
  assert.strictEqual(writesOf(c).length, 2);
  c.st('sb_invs', [INV_A, INV_B]);
  await flush();
  assert.strictEqual(writesOf(c).length, 2, 'an unchanged rewrite pushed again');
});

test('only the CHANGED record is pushed, not the whole array', async () => {
  const c = harness();
  c.st('sb_invs', [INV_A, INV_B]);
  await flush();
  c.__calls.length = 0;
  c.st('sb_invs', [INV_A, Object.assign({}, INV_B, { paid: 3890, status: 'Paid' })]);
  await flush();
  assert.deepStrictEqual(writesOf(c).map((w) => w.payload.id), ['INV-2602']);
});

test('a payroll run is pushed the moment it is recorded', async () => {
  const c = harness();
  c.st('sb_payruns', [RUN_A]);
  await flush();
  assert.deepStrictEqual(writesOf(c).map((w) => w.resource), ['sb_payruns']);
});

// ═══════════════════════════════════════════════════════════════════════════
section('the four id-less collections, which would otherwise sync nothing');

test('sb_exps records get an id minted and are pushed', async () => {
  // Expenses were stored with no identifier of any kind. Without minting, the
  // push below skips every one of them and the collection silently backs up
  // nothing while sb_invs works -- four of nine dead, no error anywhere.
  const c = harness();
  c.st('sb_exps', [{ date: '2026-06-02', desc: 'Granite slab', amt: 4200 }]);
  await flush();
  const w = writesOf(c);
  assert.strictEqual(w.length, 1, 'an id-less expense was not backed up');
  assert.ok(/^EX/.test(w[0].payload.id), 'minted id has the wrong prefix: ' + w[0].payload.id);
});

test('the minted id is PERSISTED, so the next save does not mint a second one', async () => {
  const c = harness();
  const rows = [{ date: '2026-06-02', desc: 'Granite slab', amt: 4200 }];
  c.st('sb_exps', rows);
  await flush();
  const firstId = writesOf(c)[0].payload.id;
  assert.strictEqual(JSON.parse(c.__store.sb_exps)[0].id, firstId, 'the id was not written back to storage');
  c.__calls.length = 0;
  // A later render re-persists the same collection, read fresh from storage.
  c.st('sb_exps', JSON.parse(c.__store.sb_exps));
  await flush();
  assert.strictEqual(writesOf(c).length, 0, 'a re-save minted a new id and pushed a duplicate record');
});

test('all four minting collections mint, with distinct prefixes', async () => {
  const c = harness();
  c.st('sb_exps', [{ desc: 'a' }]);
  c.st('sb_perf', [{ emp: 'Marcus Thompson', type: 'Annual Review' }]);
  c.st('sb_hire', [{ pos: 'Senior Fabricator' }]);
  c.st('sb_bud', [{ cat: 'Labor & Payroll', annual: 520000 }]);
  await flush();
  const byRes = {};
  writesOf(c).forEach((w) => { byRes[w.resource] = w.payload.id; });
  assert.deepStrictEqual(Object.keys(byRes).sort(), ['sb_bud', 'sb_exps', 'sb_hire', 'sb_perf']);
  assert.ok(/^EX/.test(byRes.sb_exps) && /^PF/.test(byRes.sb_perf) && /^HR/.test(byRes.sb_hire) && /^BD/.test(byRes.sb_bud));
});

test('minting does not overwrite an id a record already has', async () => {
  const c = harness();
  c.st('sb_exps', [{ id: 'EX-KEEP-ME', desc: 'a' }]);
  await flush();
  assert.strictEqual(writesOf(c)[0].payload.id, 'EX-KEEP-ME');
});

test('a USER-VISIBLE id is never invented -- it is reported instead', async () => {
  // sb_invs ids are invoice numbers and sb_vends ids are vendor codes; both are
  // printed in front of a customer. A generated string there would be worse
  // than the gap. It must not be silent either.
  const c = harness();
  c.st('sb_invs', [{ cust: 'Hartley', amt: 100 }]);
  await flush();
  assert.strictEqual(writesOf(c).length, 0, 'an id was invented for an invoice');
  assert.ok(c.__warns.some((w) => /sb_invs record has no id/.test(w)), 'the skipped record was not reported');
  // Latched: a standing condition, not an event. Without this it repeats on
  // every repaint and buries the failures that ARE events.
  c.st('sb_invs', [{ cust: 'Hartley', amt: 100 }]);
  c.st('sb_invs', [{ cust: 'Hartley', amt: 100 }]);
  await flush();
  assert.strictEqual(c.__warns.filter((w) => /sb_invs record has no id/.test(w)).length, 1,
    'the no-id notice repeated on every write');
});

// ═══════════════════════════════════════════════════════════════════════════
section('what is deliberately NOT backed up');

test('app state is not synced -- licence, role, seed marker, sync stamp', async () => {
  const c = harness();
  ['sb_role', 'sb_seeded', 'sb_sync', 'sb_cfg', 'sb_co', 'sb_incidents'].forEach((k) => c.st(k, [{ id: 'x-1' }]));
  await flush();
  assert.strictEqual(writesOf(c).length, 0);
});

test('sb_emps is NOT in the generic list -- it syncs through the gated employees branch', () => {
  assert.ok(!registry.resources.includes('sb_emps'));
  assert.ok(!SYNC_SRC.includes("'sb_emps'"));
});

test('nothing is pushed while seeding', async () => {
  const c = harness();
  c.sbSyncPaused = true;
  c.st('sb_invs', [INV_A, INV_B]);
  c.st('sb_exps', [{ desc: 'demo' }]);
  await flush();
  assert.strictEqual(writesOf(c).length, 0, 'demo rows were pushed to a customer table');
});

test('seed() pauses the sync around the whole seed, and restores it after', () => {
  const seedFn = slice(html, 'function seed(){', 'function sbSeedRows(){');
  assert.ok(/sbSyncPaused=true;/.test(seedFn), 'seed() does not pause the sync');
  assert.ok(/finally\s*\{\s*sbSyncPaused=false;\s*\}/.test(seedFn), 'seed() does not restore it in a finally');
});

test('nothing is pushed without a licence key', async () => {
  const c = harness({ noLicense: true });
  c.st('sb_invs', [INV_A]);
  await flush();
  assert.strictEqual(writesOf(c).length, 0);
});

test('nothing is pushed without a signed-in session', async () => {
  // These resources require a session server-side. A request certain to 401 is
  // noise, and sending it would also mean the failure path is exercised on
  // every save for every logged-out tab.
  const c = harness({ noSession: true });
  c.st('sb_invs', [INV_A]);
  await flush();
  assert.strictEqual(c.__calls.length, 0);
});

// ═══════════════════════════════════════════════════════════════════════════
section('a failed local write is never reported as saved');

test('st() returns false when localStorage refuses', () => {
  const c = harness({ storageFull: true });
  assert.strictEqual(c.st('sb_invs', [INV_A]), false);
});

test('a failed local write pushes NOTHING', async () => {
  // The server must not hold a record the device does not, or hydration
  // reintroduces it later as though it had always been there.
  const c = harness({ storageFull: true });
  c.st('sb_invs', [INV_A]);
  await flush();
  assert.strictEqual(c.__calls.length, 0);
});

test('a failed local write TELLS THE USER, in the words that matter', () => {
  const c = harness({ storageFull: true });
  c.st('sb_payruns', [RUN_A]);
  assert.strictEqual(c.__toasts.length, 1, 'the save failed silently');
  assert.ok(/DID NOT SAVE/i.test(c.__toasts[0]), 'the message does not say the record was not saved: ' + c.__toasts[0]);
});

test('the alarm fires once per key, not once per repaint', () => {
  const c = harness({ storageFull: true });
  c.st('sb_ap', [{ id: 'AP-1' }]);
  c.st('sb_ap', [{ id: 'AP-1' }]);
  c.st('sb_ap', [{ id: 'AP-1' }]);
  assert.strictEqual(c.__toasts.length, 1, 'a render-path failure toasted on every repaint');
  assert.strictEqual(c.__warns.filter((w) => /localStorage write failed/.test(w)).length, 3,
    'the console record should still be complete');
});

// ═══════════════════════════════════════════════════════════════════════════
section('an unprovisioned backup goes quiet after one failure, not 300');

test('NOT_PROVISIONED latches, so a nine-collection save is one warning', async () => {
  const c = harness({ notProvisioned: true });
  c.st('sb_invs', [INV_A, INV_B]);
  await flush();
  c.st('sb_payruns', [RUN_A]);
  c.st('sb_vends', [{ id: 'V001', name: 'Midwest Stone' }]);
  await flush();
  assert.strictEqual(c.sbBackupUnavailable, true, 'the unavailable flag did not latch');
  assert.strictEqual(c.__warns.filter((w) => /not exist|not available|unavailable/i.test(w)).length, 1,
    'more than one alarm for a single cause');
  // The first save's two records were both in flight before the latch, which is
  // expected; nothing after the latch should reach the network.
  const after = c.__calls.filter((x) => x.resource === 'sb_payruns' || x.resource === 'sb_vends');
  assert.strictEqual(after.length, 0, 'writes continued after the backup was known unavailable');
});

test('a real write failure is reported per record, not swallowed', async () => {
  const c = harness({ writeFails: true });
  c.st('sb_invs', [INV_A]);
  await flush();
  assert.ok(c.__warns.some((w) => /backup write failed for sb_invs INV-2601/.test(w)), 'a failed push said nothing');
});

// ═══════════════════════════════════════════════════════════════════════════
section('hydration merges, and never mistakes a failure for an empty backup');

test('server records not held locally are appended', async () => {
  const c = harness({ serverRows: { sb_invs: [INV_A, INV_B] } });
  const r = await c.sbHydrateAll();
  assert.strictEqual(r.merged, 2);
  assert.deepStrictEqual(JSON.parse(c.__store.sb_invs).map((x) => x.id), ['INV-2601', 'INV-2602']);
});

test('a locally present id is never overwritten by the server copy', async () => {
  const localEdit = Object.assign({}, INV_A, { cust: 'EDITED LOCALLY' });
  const c = harness({ store: { sb_invs: JSON.stringify([localEdit]) }, serverRows: { sb_invs: [INV_A, INV_B] } });
  const r = await c.sbHydrateAll();
  assert.strictEqual(r.merged, 1, 'only the unseen record should merge');
  const rows = JSON.parse(c.__store.sb_invs);
  assert.strictEqual(rows.find((x) => x.id === 'INV-2601').cust, 'EDITED LOCALLY');
});

test('hydrated rows are NOT echoed straight back to the server', async () => {
  const c = harness({ serverRows: { sb_invs: [INV_A] } });
  await c.sbHydrateAll();
  await flush();
  assert.strictEqual(writesOf(c).length, 0, 'records that came from the server were pushed back to it');
});

test('a FAILED read leaves local data untouched and is counted as failed', async () => {
  const c = harness({ store: { sb_invs: JSON.stringify([INV_A]) }, readFails: true });
  const r = await c.sbHydrateAll();
  assert.strictEqual(r.merged, 0);
  assert.strictEqual(r.failed, 9, 'a failed read was not counted');
  assert.strictEqual(r.notProvisioned, 0, 'a failure was miscounted as an unprovisioned backup');
  assert.deepStrictEqual(JSON.parse(c.__store.sb_invs), [INV_A], 'a failed read modified local data');
});

test('a failed read TELLS THE USER, and does not say the backup is empty', () => {
  const c = harness({ readFails: true });
  c.sbReportHydrate({ merged: 0, failed: 9, notProvisioned: 0 }, true);
  assert.strictEqual(c.__toasts.length, 1, 'a failed read was silent -- this is the "No jobs yet" shape');
  assert.ok(/Could not read/i.test(c.__toasts[0]));
  assert.ok(!/no records|nothing|empty/i.test(c.__toasts[0]), 'the message implies an empty backup: ' + c.__toasts[0]);
});

test('provisioned:false is counted as not-provisioned, not as an empty backup', async () => {
  const c = harness({ notProvisioned: true });
  const r = await c.sbHydrateAll();
  assert.strictEqual(r.notProvisioned, 9);
  assert.strictEqual(r.failed, 0);
});

test('an unprovisioned backup warns the operator and does NOT alarm the user', () => {
  // A shop owner cannot run a SQL file. An alarm with no available action is
  // noise; the console line is for whoever deploys.
  const c = harness();
  c.sbReportHydrate({ merged: 0, failed: 0, notProvisioned: 9 }, true);
  assert.strictEqual(c.__toasts.length, 0);
  assert.ok(c.__warns.some((w) => /sairnbiz_data_schema\.sql/.test(w)), 'the operator was not told which file to run');
  assert.strictEqual(c.sbBackupUnavailable, true, 'reads did not latch the flag, so writes will keep retrying');
});

test('a restore repaints the app so the records are actually visible', () => {
  const c = harness();
  const before = c.__initCount();
  c.sbReportHydrate({ merged: 3, failed: 0, notProvisioned: 0 }, true);
  assert.strictEqual(c.__initCount(), before + 1, 'records were merged but nothing re-rendered');
  assert.ok(/3 records restored/.test(c.__toasts[0]));
});

// ═══════════════════════════════════════════════════════════════════════════
section('login ordering: a fresh device must not seed on top of a live licence');

test('a device that already holds data paints FIRST, then merges', () => {
  const fn = slice(html, 'function sbApplyLoggedIn(role){', '\n}\n');
  assert.ok(/if\(ld\('sb_seeded',false\)\)\{\s*\n\s*init\(\);/.test(fn),
    'a seeded device should call init() before hydrating -- first paint must not wait on the network');
});

test('a fresh device hydrates BEFORE init(), and marks itself seeded if records came back', () => {
  const fn = slice(html, 'function sbFirstDeviceHydrate(){', '\n}\n');
  const seedIdx = fn.indexOf("st('sb_seeded',true)");
  const initIdx = fn.indexOf('init();');
  assert.ok(seedIdx > 0 && initIdx > seedIdx,
    'the seed marker must be set before init(), or seed() writes demo rows over a real licence');
  assert.ok(/if\(r\.merged\)st\('sb_seeded',true\)/.test(fn), 'the marker is set unconditionally');
});

test('the blocking path is bounded, so an unreachable server cannot hang the app', () => {
  const fn = slice(html, 'function sbFirstDeviceHydrate(){', '\n}\n');
  assert.ok(/Promise\.race/.test(fn) && /timedOut:true/.test(fn), 'no timeout on the one path that blocks first paint');
});

// ═══════════════════════════════════════════════════════════════════════════
section('the server branch refuses before it reads');

test('SB_RESOURCES checks the session before any fetch', () => {
  const block = slice(sdData, 'const SB_RESOURCES = {', "const LEG_RESOURCES = {");
  const guardIdx = block.indexOf("verifySessionToken(tokenFromRequest(req), licHash, 'sairnbiz')");
  const fetchIdx = block.indexOf('await fetch(');
  assert.ok(guardIdx > 0, 'no session check on the SAIRNbiz branch');
  assert.ok(fetchIdx > guardIdx, 'a fetch runs before the session is verified');
  assert.ok(/NO_SESSION/.test(block.slice(guardIdx, fetchIdx)), 'the refusal does not name NO_SESSION');
});

test('the read branch reports provisioned:false rather than pretending to be empty', () => {
  const block = slice(sdData, 'const SB_RESOURCES = {', "const LEG_RESOURCES = {");
  assert.ok(/provisioned: false/.test(block));
  assert.ok(/NOT_PROVISIONED/.test(block) && /sairnbiz_data_schema\.sql/.test(block),
    'the write refusal does not name the file to run');
});

test('the write branch refuses a payload with no id', () => {
  const block = slice(sdData, 'const SB_RESOURCES = {', "const LEG_RESOURCES = {");
  assert.ok(/payload\.id === undefined \|\| payload\.id === null \|\| payload\.id === ''/.test(block));
});

// ═══════════════════════════════════════════════════════════════════════════
// MUTATION PROBES. Each one reverts a specific fix in the lifted source and
// asserts the suite would have caught it. A probe that passes means the
// assertion above it is decorative.
// ═══════════════════════════════════════════════════════════════════════════
const probes = [
  ['id minting removed -> the four id-less collections silently sync nothing',
    (s) => s.replace(/var SB_ID_PREFIX=\{[^}]*\}/, 'var SB_ID_PREFIX={}'),
    async () => {
      const c = harness({}, probeSrc);
      c.st('sb_exps', [{ desc: 'Granite slab' }]);
      await flush();
      assert.strictEqual(writesOf(c).length, 1);
    }],
  ['diff removed -> every repaint pushes the whole collection',
    (s) => s.replace('if(before[String(r.id)]===now)return;', ''),
    async () => {
      const c = harness({}, probeSrc);
      c.st('sb_invs', [INV_A, INV_B]);
      await flush();
      c.st('sb_invs', [INV_A, INV_B]);
      await flush();
      assert.strictEqual(writesOf(c).length, 2);
    }],
  ['pause ignored -> seeding pushes demo rows to a customer table',
    (s) => s.replace('if(sbSyncPaused||sbBackupUnavailable)return;', 'if(sbBackupUnavailable)return;'),
    async () => {
      const c = harness({}, probeSrc);
      c.sbSyncPaused = true;
      c.st('sb_invs', [INV_A]);
      await flush();
      assert.strictEqual(writesOf(c).length, 0);
    }],
  ['NOT_PROVISIONED no longer latches -> one cause, many alarms',
    (s) => s.replace('sbBackupUnavailable=true;\n          console.warn(\'SAIRNbiz server backup is unavailable', 'console.warn(\'SAIRNbiz server backup is unavailable'),
    async () => {
      const c = harness({ notProvisioned: true }, probeSrc);
      c.st('sb_invs', [INV_A, INV_B]);
      await flush();
      c.st('sb_payruns', [RUN_A]);
      await flush();
      assert.strictEqual(c.__calls.filter((x) => x.resource === 'sb_payruns').length, 0);
    }],
  ['failed read counted as not-provisioned -> "you have nothing" returns',
    (s) => s.replace("if(res.reason==='not_provisioned')notProvisioned++;else failed++;", 'notProvisioned++;'),
    async () => {
      const c = harness({ readFails: true }, probeSrc);
      const r = await c.sbHydrateAll();
      assert.strictEqual(r.failed, 9);
    }],
  ['hydration overwrites local edits instead of merging additively',
    (s) => s.replace('if(r&&r.id!=null&&!have[String(r.id)]){local.push(r);added++;}', 'if(r&&r.id!=null){local.push(r);added++;}'),
    async () => {
      const localEdit = Object.assign({}, INV_A, { cust: 'EDITED LOCALLY' });
      const c = harness({ store: { sb_invs: JSON.stringify([localEdit]) }, serverRows: { sb_invs: [INV_A, INV_B] } }, probeSrc);
      const r = await c.sbHydrateAll();
      assert.strictEqual(r.merged, 1);
    }],
  ['hydrated rows echoed back to the server',
    (s) => s.replace('sbSyncPaused=true;\n        st(key,local);\n        sbSyncPaused=false;', 'st(key,local);'),
    async () => {
      const c = harness({ serverRows: { sb_invs: [INV_A] } }, probeSrc);
      await c.sbHydrateAll();
      await flush();
      assert.strictEqual(writesOf(c).length, 0);
    }],
  // The mutation that puts the ORIGINAL `catch(e){}` back into st(): the state
  // this file was in before 2026-09-04, where a quota failure showed the
  // caller's success toast and nothing else.
  ['st() swallows a failed write again -> a lost payroll run reports as saved',
    null,
    async () => {
      const brokenSt = ST_SRC.replace(/catch\(e\)\{[\s\S]*?\n  \}\n/, 'catch(e){okWrite=false;}\n');
      assert.ok(brokenSt !== ST_SRC, 'the st() probe did not change the source');
      const c = harness({ storageFull: true }, SYNC_SRC, brokenSt);
      c.st('sb_payruns', [RUN_A]);
      assert.strictEqual(c.__toasts.length, 1, 'nothing told the user the payroll run was not stored');
    }],
];

let probeSrc = SYNC_SRC;

// ═══════════════════════════════════════════════════════════════════════════
(async () => {
  for (const item of queue) {
    if (item.section) { console.log('--- ' + item.section + ' ---'); continue; }
    try { await item.fn(); console.log('  ok   ' + item.name); pass++; }
    catch (e) { console.log('  FAIL ' + item.name + '\n       ' + e.message); fail++; }
  }

  console.log('--- mutation probes (each MUST fail) ---');
  let bit = 0;
  for (const [name, mutate, check] of probes) {
    let threw = false;
    if (mutate) {
      probeSrc = mutate(SYNC_SRC);
      assert.ok(probeSrc !== SYNC_SRC, 'probe did not change the source: ' + name);
    }
    try { await check(); } catch (e) { threw = true; }
    probeSrc = SYNC_SRC;
    if (threw) { console.log('  ok   bites: ' + name); bit++; }
    else { console.log('  FAIL survives: ' + name); fail++; }
  }

  console.log('\n' + pass + ' passed, ' + bit + ' probes bit, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
