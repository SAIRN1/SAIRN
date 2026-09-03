// tests/sairnbuild_server_backup.js
//
// Run:  node tests/sairnbuild_server_backup.js
//
// SAIRNbuild's server backup, tested where it can actually be wrong.
//
// The feature is one hook inside st() -- the single function every write in
// that file already goes through -- so the risk is not that it fails loudly.
// It is that it does the wrong AMOUNT of work, silently:
//
//   * pushes NOTHING, and the backup that everyone believes exists is empty;
//   * pushes EVERYTHING on every render, turning a page repaint into three
//     hundred network writes;
//   * pushes during seed(), filling a customer's server tables with demo rows;
//   * pushes a record the browser itself failed to store, so the server and
//     the device disagree about what was saved.
//
// None of those throw. Each one is a green app doing the wrong thing, which is
// why the assertions below count calls rather than checking for errors.
//
// The functions are lifted out of the real file rather than reimplemented, so
// a change to sairnbuild.html that breaks them fails here.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

// Line endings normalised so the slice markers below can be written with plain
// \n. The file is CRLF on disk and an assumption about that is not worth a
// brittle test -- this is the same reason tests/nesting_saw_ticket.js matches
// its terminator by regex.
const html = fs.readFileSync(path.join(__dirname, '..', 'sairnbuild.html'), 'utf8')
  .replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

// Pull the real source out of the page. Anchored on comment banners rather
// than line numbers, which move.
function slice(startMark, endMark) {
  const a = html.indexOf(startMark);
  assert.ok(a > 0, 'not found in sairnbuild.html: ' + startMark);
  const b = html.indexOf(endMark, a);
  assert.ok(b > a, 'end marker not found after ' + startMark);
  return html.slice(a, b);
}

const stSrc = slice('function st(k,v){', 'function ld(');
const syncSrc = slice('var BLD_SYNCED = [', '// -- HYDRATION');
const hydrateSrc = slice('function bldHydrateAll()', '\n}\n') + '\n}\n';

function harness(opts) {
  opts = opts || {};
  const store = Object.assign({}, opts.store || {});
  const writes = [];
  const reads = [];
  const ctx = {
    console,
    JSON,
    Array,
    Promise,
    localStorage: {
      setItem: (k, v) => {
        if (opts.storageFull) throw new Error('QuotaExceededError');
        store[k] = v;
      },
      getItem: (k) => (k in store ? store[k] : null)
    },
    ld: (k, d) => { reads.push(k); try { const r = store[k]; return r === undefined ? d : JSON.parse(r); } catch (e) { return d; } },
    bldLicenseKey: () => (opts.noLicense ? '' : 'BLD-PINNACLE-2026'),
    bldData: (action, resource, payload) => {
      writes.push({ action, resource, id: payload && payload.id, payload });
      return Promise.resolve(opts.serverRows ? (opts.serverRows[resource] || []) : []);
    },
    __writes: writes,
    __store: store
  };
  vm.createContext(ctx);
  vm.runInContext(syncSrc + '\n' + stSrc, ctx);
  return ctx;
}

const JOB_A = { id: 'J-1', client: 'Hartley', value: 186500 };
const JOB_B = { id: 'J-2', client: 'Delgado', value: 242000 };

console.log('sairnbuild server backup');

// ── IT PUSHES, AND ONLY WHAT CHANGED ───────────────────────────────────────
section('the backup actually happens');

test('a new record on a synced collection is pushed', () => {
  const c = harness();
  c.st('bld_jobs', [JOB_A]);
  assert.strictEqual(c.__writes.length, 1);
  assert.strictEqual(c.__writes[0].resource, 'bld_jobs');
  assert.strictEqual(c.__writes[0].id, 'J-1');
  assert.strictEqual(c.__writes[0].action, 'write');
});

test('the local write still happens -- the hook never replaces it', () => {
  const c = harness();
  c.st('bld_jobs', [JOB_A]);
  assert.deepStrictEqual(JSON.parse(c.__store['bld_jobs']), [JOB_A]);
});

test('rewriting an UNCHANGED array pushes nothing', () => {
  // The one that stops a page repaint becoming 300 network writes. Every
  // render in this app rewrites its whole collection.
  const c = harness();
  c.st('bld_jobs', [JOB_A, JOB_B]);
  assert.strictEqual(c.__writes.length, 2);
  c.st('bld_jobs', [JOB_A, JOB_B]);
  assert.strictEqual(c.__writes.length, 2, 'an unchanged rewrite pushed again');
});

test('only the CHANGED record is pushed, not the whole array', () => {
  const c = harness();
  c.st('bld_jobs', [JOB_A, JOB_B]);
  c.__writes.length = 0;
  c.st('bld_jobs', [JOB_A, Object.assign({}, JOB_B, { value: 250000 })]);
  assert.strictEqual(c.__writes.length, 1);
  assert.strictEqual(c.__writes[0].id, 'J-2');
});

test('a change ANYWHERE in the record counts, not just a watched field', () => {
  const c = harness();
  c.st('bld_jobs', [JOB_A]);
  c.__writes.length = 0;
  c.st('bld_jobs', [Object.assign({}, JOB_A, { notes: 'added a note' })]);
  assert.strictEqual(c.__writes.length, 1);
});

test('appending to a collection pushes only the appended record', () => {
  const c = harness();
  c.st('bld_costs', [{ id: 'C-1', budget: 1 }]);
  c.__writes.length = 0;
  c.st('bld_costs', [{ id: 'C-1', budget: 1 }, { id: 'C-2', budget: 2 }]);
  assert.deepStrictEqual(c.__writes.map((w) => w.id), ['C-2']);
});

// ── AND ONLY WHERE IT SHOULD ───────────────────────────────────────────────
section('what is deliberately NOT backed up');

test('app state is not synced -- role, settings, the seed marker', () => {
  const c = harness();
  ['bld_role', 'bld_settings', 'bld_seeded', 'bld_company_profile', 'bld_ai_chat',
   'bld_integrations'].forEach((k) => c.st(k, [{ id: 'x-1' }]));
  assert.strictEqual(c.__writes.length, 0);
});

test('bld_bids and bld_tna are NOT in the generic list', () => {
  // Both already sync through bespoke branches carrying a privacy gate.
  // Folding them in here would route them past that gate.
  const c = harness();
  c.st('bld_bids', [{ id: 'B-1' }]);
  c.st('bld_tna', [{ id: 'T-1' }]);
  assert.strictEqual(c.__writes.length, 0);
  assert.strictEqual(c.BLD_SYNCED.indexOf('bld_bids'), -1);
  assert.strictEqual(c.BLD_SYNCED.indexOf('bld_tna'), -1);
});

test('the synced list is exactly the 30 declared collections, no duplicates', () => {
  const c = harness();
  assert.strictEqual(c.BLD_SYNCED.length, 30);
  assert.strictEqual(new Set(c.BLD_SYNCED).size, 30);
  c.BLD_SYNCED.forEach((k) => assert.ok(/^bld_[a-z_]+$/.test(k), 'odd key: ' + k));
});

test('every synced collection is registered server-side', () => {
  // A key here that api/_resources/sairnbuild.js does not declare would be
  // pushed to an endpoint that refuses it, forever, silently.
  const c = harness();
  const reg = require(path.join(__dirname, '..', 'api', '_resources', 'sairnbuild.js')).resources;
  c.BLD_SYNCED.forEach((k) => assert.ok(reg.indexOf(k) !== -1, k + ' is not a registered resource'));
});

test('every registered resource except the two bespoke ones is synced', () => {
  // The other direction: a table that exists and that nothing ever writes to.
  const c = harness();
  const reg = require(path.join(__dirname, '..', 'api', '_resources', 'sairnbuild.js')).resources;
  reg.filter((r) => r !== 'bld_bids' && r !== 'bld_tna')
     .forEach((r) => assert.ok(c.BLD_SYNCED.indexOf(r) !== -1, r + ' has a table but nothing syncs it'));
});

test('a record with no id is skipped rather than pushed without one', () => {
  // api/sd-data.js refuses a payload with no id (400). Pushing anyway would
  // produce a console full of 400s and no backup.
  const c = harness();
  c.st('bld_jobs', [{ client: 'no id here' }, { id: '', client: 'empty id' },
                    { id: null }, JOB_A]);
  assert.deepStrictEqual(c.__writes.map((w) => w.id), ['J-1']);
});

test('a non-array value on a synced key pushes nothing', () => {
  const c = harness();
  c.st('bld_jobs', { id: 'J-1' });
  c.st('bld_jobs', null);
  c.st('bld_jobs', 'a string');
  assert.strictEqual(c.__writes.length, 0);
});

// ── THE GUARDS ─────────────────────────────────────────────────────────────
section('the guards, each of which prevents a specific wrong outcome');

test('seeding pushes NOTHING -- demo rows are not the customer\'s records', () => {
  const c = harness();
  c.bldSeeding = true;
  c.st('bld_jobs', [JOB_A, JOB_B]);
  c.st('bld_costs', [{ id: 'C-1' }]);
  assert.strictEqual(c.__writes.length, 0);
  // ...and the local write still happened, so the app seeds normally.
  assert.strictEqual(JSON.parse(c.__store['bld_jobs']).length, 2);
});

test('no licence key -> no push, and no crash', () => {
  const c = harness({ noLicense: true });
  c.st('bld_jobs', [JOB_A]);
  assert.strictEqual(c.__writes.length, 0);
  assert.strictEqual(JSON.parse(c.__store['bld_jobs']).length, 1);
});

test('a FAILED local write pushes nothing', () => {
  // The server must never hold a record the device itself could not store.
  const c = harness({ storageFull: true });
  const ok = c.st('bld_jobs', [JOB_A]);
  assert.strictEqual(ok, false, 'st() reported success on a failed write');
  assert.strictEqual(c.__writes.length, 0);
});

test('st() still returns its boolean, which existing callers depend on', () => {
  const good = harness();
  assert.strictEqual(good.st('bld_jobs', [JOB_A]), true);
  assert.strictEqual(good.st('bld_role', 'owner'), true);
  const bad = harness({ storageFull: true });
  assert.strictEqual(bad.st('bld_role', 'owner'), false);
});

test('a throwing sync never breaks the local write', () => {
  const c = harness();
  c.bldData = () => { throw new Error('network exploded'); };
  let ok;
  assert.doesNotThrow(() => { ok = c.st('bld_jobs', [JOB_A]); });
  assert.strictEqual(ok, true);
  assert.strictEqual(JSON.parse(c.__store['bld_jobs']).length, 1);
});

test('an unserialisable record is skipped, not thrown', () => {
  const c = harness();
  const circular = { id: 'J-9' };
  circular.self = circular;
  // st() itself cannot store this either; the point is that the hook does not
  // turn a storage failure into an exception the caller never expected.
  assert.doesNotThrow(() => c.st('bld_jobs', [circular]));
});

// ── HYDRATION ──────────────────────────────────────────────────────────────
section('hydration is additive and never clobbers local work');

test('server records absent locally are appended', async () => {
  const c = harness({ serverRows: { bld_jobs: [JOB_A, JOB_B] } });
  vm.runInContext(hydrateSrc, c);
  const n = await c.bldHydrateAll();
  assert.ok(n >= 2, 'nothing was merged');
  assert.deepStrictEqual(JSON.parse(c.__store['bld_jobs']).map((j) => j.id), ['J-1', 'J-2']);
});

test('a locally present id is NEVER overwritten by the server copy', async () => {
  const local = { id: 'J-1', client: 'EDITED LOCALLY' };
  const c = harness({
    store: { bld_jobs: JSON.stringify([local]) },
    serverRows: { bld_jobs: [JOB_A] }
  });
  vm.runInContext(hydrateSrc, c);
  await c.bldHydrateAll();
  const rows = JSON.parse(c.__store['bld_jobs']);
  assert.strictEqual(rows.length, 1);
  assert.strictEqual(rows[0].client, 'EDITED LOCALLY', 'the server clobbered a local edit');
});

test('hydration does NOT echo the merged rows straight back to the server', async () => {
  // They came FROM the server. Pushing them back is pure noise, and it is
  // exactly what st()'s hook would do without the suppression.
  const c = harness({ serverRows: { bld_jobs: [JOB_A] } });
  vm.runInContext(hydrateSrc, c);
  c.__writes.length = 0;
  await c.bldHydrateAll();
  assert.strictEqual(c.__writes.filter((w) => w.action === 'write').length, 0,
    'hydrated rows were pushed back');
});

test('the suppression flag is left OFF afterwards', async () => {
  // If it stayed on, every later save would silently stop backing up.
  const c = harness({ serverRows: { bld_jobs: [JOB_A] } });
  vm.runInContext(hydrateSrc, c);
  await c.bldHydrateAll();
  assert.strictEqual(c.bldSeeding, false);
  c.__writes.length = 0;
  c.st('bld_costs', [{ id: 'C-9' }]);
  assert.strictEqual(c.__writes.length, 1, 'syncing stayed suppressed after hydration');
});

test('a failed or unprovisioned read leaves local data untouched', async () => {
  const c = harness({ store: { bld_jobs: JSON.stringify([JOB_A]) } });
  vm.runInContext(hydrateSrc, c);
  c.bldData = () => Promise.resolve(null);   // what bldData returns on 503/failure
  const n = await c.bldHydrateAll();
  assert.strictEqual(n, 0);
  assert.deepStrictEqual(JSON.parse(c.__store['bld_jobs']), [JOB_A]);
});

test('no licence -> hydration is a no-op, not an error', async () => {
  const c = harness({ noLicense: true });
  vm.runInContext(hydrateSrc, c);
  assert.strictEqual(await c.bldHydrateAll(), 0);
});

console.log('');
if (fail) { console.log(fail + ' FAILED, ' + pass + ' passed'); process.exit(1); }
console.log('ALL ' + pass + ' SERVER-BACKUP ASSERTIONS PASS');
