// tests/stonedesk_server_backup.js
//
// Run:  node tests/stonedesk_server_backup.js
//
// StoneDesk kept its invoices, drawings, remakes, pricing rules, quote history
// and seventeen other collections in ONE browser and nowhere else. The
// open-work row said twelve; that was an undercount taken from
// tools/local_only_collection_check.py before the repair whose own commit
// message reads "the checker could not read half of StoneDesk". Re-run after
// the fix: 26 of 37 collections had no route to a server.
//
// WORSE HERE THAN IN A UNIFORMLY LOCAL APP, which is the reason this was the
// priority: StoneDesk already synced slabs, customers, CRM and approvals, so a
// browser-data clear left the records that LOOK authoritative and took the
// invoices that justify them.
//
// THREE THINGS ARE ASSERTED, and the third is the one that rots quietly:
//   1. the registry, the handler map and the SQL schema agree -- all three,
//      pairwise, because two of three agreeing is how a table name drifts;
//   2. the client pushes only what CHANGED, and never on a failed local write;
//   3. hydration is CALLED. A backup nothing reads back is write-only, and a
//      second device would never see the first device's records.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8');
const api = fs.readFileSync(path.join(ROOT, 'api', 'sd-data.js'), 'utf8');
const sql = fs.readFileSync(path.join(ROOT, 'sql', 'stonedesk_data_schema.sql'), 'utf8');
const reg = require(path.join(ROOT, 'api', '_resources'));

let pass = 0, fail = 0;
const queue = [];
function test(n, f) { queue.push({ n, f }); }
function section(t) { queue.push({ section: t }); }

function handlerMap() {
  const at = api.indexOf('const SD_LOCAL_RESOURCES = {');
  assert.ok(at > 0, 'SD_LOCAL_RESOURCES is gone from api/sd-data.js');
  const body = api.slice(at, api.indexOf('};', at));
  const out = {};
  for (const m of body.matchAll(/(\w+):\s*'(\w+)'/g)) out[m[1]] = m[2];
  return out;
}

function clientList() {
  const at = html.indexOf('var SD_SYNCED=[');
  assert.ok(at > 0, 'SD_SYNCED is gone from stonedesk.html');
  const body = html.slice(at, html.indexOf('];', at));
  return (body.match(/'([a-z_]+)'/g) || []).map((x) => x.slice(1, -1));
}

section('registry, handler and schema agree -- all three, pairwise');

test('the handler map and the client list are the same 21 resources', () => {
  const h = Object.keys(handlerMap()).sort();
  const c = clientList().sort();
  assert.strictEqual(h.length, 21, 'the handler map holds ' + h.length + ', not 21');
  assert.deepStrictEqual(c, h, 'the client syncs a different set from the one the server accepts');
});

test('every one is REGISTERED, and registered to stonedesk', () => {
  // Registering a resource and adding a handler branch are separate edits, and
  // missing the first yields a working branch that still answers 400.
  Object.keys(handlerMap()).forEach((r) => {
    assert.ok(reg.RESOURCES[r], r + ' is not in api/_resources');
    assert.strictEqual(reg.OWNER_BY_RESOURCE[r], 'stonedesk',
      r + ' is owned by ' + reg.OWNER_BY_RESOURCE[r] + ' -- the app boundary would refuse it');
  });
});

test('every one has a TABLE, with the SAME id column the handler writes', () => {
  // The drift that matters: the handler upserts on_conflict=license_hash,<idCol>
  // and a schema whose unique constraint names a different column silently
  // inserts a duplicate row per write instead of updating one.
  const map = handlerMap();
  Object.keys(map).forEach((table) => {
    assert.ok(sql.indexOf('create table if not exists public.' + table + ' (') !== -1,
      'no table for ' + table);
    assert.ok(sql.indexOf('unique (license_hash, ' + map[table] + ')') !== -1,
      table + ': the schema has no unique(license_hash, ' + map[table] + ') for the id column the handler upserts on');
  });
});

test('the schema grants no DELETE anywhere', () => {
  // The platform stripped explicit delete grants from every non-sc_* schema on
  // 2026-08-25, and there is no delete path in the generic block to grant for.
  // COMMENTS STRIPPED FIRST. The first version of this assertion matched the
  // header comment that EXPLAINS there is no delete grant and reported the
  // schema as carrying one -- the same detector-matched-a-comment bug
  // sairn-code-scrubber item 16 Shape A records, and that the pre-auth checker
  // shipped with. Caught by running it, not by reading it.
  const sqlCode = sql.split('\n').filter((l) => l.trim().indexOf('--') !== 0).join('\n');
  assert.ok(!/grant[^;]*\bdelete\b/i.test(sqlCode), 'a delete grant is back in the schema');
  Object.keys(handlerMap()).forEach((t) => {
    assert.ok(sql.indexOf('grant select, insert, update on public.' + t + ' to service_role;') !== -1,
      t + ' does not carry the standard three-verb grant');
  });
});

test('the excluded collections are excluded from ALL THREE, not just one', () => {
  // An exclusion honoured in the registry but not the client would push to a
  // resource the server refuses; the reverse would create a table nothing writes.
  const excluded = ['sd_ai_counts', 'sd_settings', 'sd_alert_settings',
    'sd_stonehead_history', 'sd_stonehub_log', 'sd_market_history', 'sd_intake'];
  const h = handlerMap(), c = clientList();
  excluded.forEach((k) => {
    assert.ok(!h[k], k + ' is in the handler map but was excluded');
    assert.ok(c.indexOf(k) === -1, k + ' is in the client list but was excluded');
    assert.ok(!reg.RESOURCES[k], k + ' was registered but was excluded');
    assert.ok(sql.indexOf('public.' + k + ' (') === -1, k + ' has a table but was excluded');
  });
});

test('...and each exclusion carries a REASON, not just an absence', () => {
  const registry = fs.readFileSync(path.join(ROOT, 'api', '_resources', 'stonedesk.js'), 'utf8');
  ['sd_ai_counts', 'sd_settings', 'sd_alert_settings', 'sd_stonehead_history',
    'sd_stonehub_log', 'sd_market_history', 'sd_intake'].forEach((k) => {
    assert.ok(registry.indexOf(k) !== -1,
      k + ' was dropped silently -- "not in the list" and "decided against" look identical to the next reader');
  });
});

section('the client pushes only what changed, and never on a failed write');

function driveSync(opts) {
  opts = opts || {};
  const at = html.indexOf('function sdSyncCollection(key,next,prev){');
  assert.ok(at > 0, 'sdSyncCollection is gone');
  const src = html.slice(at, html.indexOf('window.sdSyncCollection', at));
  const pushed = [];
  const warned = [];
  const ctx = {
    JSON, Array, String,
    sdSyncSuppressed: !!opts.suppressed,
    SD_SYNCED_ON: { sd_invoices: true },
    sdLicenseKey: () => (opts.noLicence ? '' : 'SD-TEST'),
    sdData: (a, k, r) => { pushed.push([a, k, r.id]); return Promise.resolve(opts.refuse ? null : r); },
    console: { warn: (m) => warned.push(m) },
  };
  vm.createContext(ctx);
  vm.runInContext(src, ctx);
  return { ctx, pushed, warned };
}

test('an unchanged record is not pushed', () => {
  const d = driveSync();
  const rows = [{ id: 'INV-1', total: 10 }, { id: 'INV-2', total: 20 }];
  d.ctx.sdSyncCollection('sd_invoices', rows, JSON.parse(JSON.stringify(rows)));
  assert.deepStrictEqual(d.pushed, [], 'it pushed records nothing had changed');
});

test('only the CHANGED record is pushed', () => {
  const d = driveSync();
  const prev = [{ id: 'INV-1', total: 10 }, { id: 'INV-2', total: 20 }];
  const next = [{ id: 'INV-1', total: 10 }, { id: 'INV-2', total: 99 }];
  d.ctx.sdSyncCollection('sd_invoices', next, prev);
  assert.deepStrictEqual(d.pushed.map((p) => p[2]), ['INV-2']);
});

test('a NEW record is pushed', () => {
  const d = driveSync();
  d.ctx.sdSyncCollection('sd_invoices', [{ id: 'INV-3' }], []);
  assert.deepStrictEqual(d.pushed.map((p) => p[2]), ['INV-3']);
});

test('a record with no id is skipped rather than sent without one', () => {
  const d = driveSync();
  d.ctx.sdSyncCollection('sd_invoices', [{ total: 5 }, { id: '', total: 6 }], []);
  assert.deepStrictEqual(d.pushed, []);
});

test('nothing is pushed with no licence', () => {
  const d = driveSync({ noLicence: true });
  d.ctx.sdSyncCollection('sd_invoices', [{ id: 'INV-9' }], []);
  assert.deepStrictEqual(d.pushed, []);
});

test('nothing is pushed while suppressed -- seeding and hydration', () => {
  const d = driveSync({ suppressed: true });
  d.ctx.sdSyncCollection('sd_invoices', [{ id: 'INV-9' }], []);
  assert.deepStrictEqual(d.pushed, [], 'hydrated rows were echoed straight back to the server');
});

test('A REFUSED PUSH IS SAID OUT LOUD, not swallowed', async () => {
  const d = driveSync({ refuse: true });
  d.ctx.sdSyncCollection('sd_invoices', [{ id: 'INV-4' }], []);
  await new Promise((r) => setTimeout(r, 0));
  assert.strictEqual(d.warned.length, 1, 'a failed backup was silent');
  assert.match(d.warned[0], /did NOT reach the server/);
  assert.match(d.warned[0], /this device only/);
});

test('st() pushes only AFTER a successful local write', () => {
  // A failed localStorage write must not push a value the device does not hold.
  const at = html.indexOf('function st(key,data){');
  const src = html.slice(at, html.indexOf('window.st=st;', at));
  assert.match(src, /sdStorageFailed\(key,e\);\s*return false;/,
    'the catch no longer returns before the push');
  const catchAt = src.indexOf('sdStorageFailed');
  const pushAt = src.indexOf('sdSyncCollection(key,data,prev)');
  assert.ok(pushAt > catchAt, 'the push moved above the failure return');
});

section('hydration is CALLED, not merely defined');

test('sdHydrateAll exists and is wired to sign-in', () => {
  assert.ok(html.indexOf('function sdHydrateAll()') > 0, 'sdHydrateAll is gone');
  const at = html.indexOf('window.sdApplyLoggedInSession = function(role)');
  assert.ok(at > 0, 'the sign-in handler is gone');
  const body = html.slice(at, at + 2000);
  assert.ok(body.indexOf('window.sdHydrateAll()') !== -1,
    'hydration is never called -- the backup is write-only and a second device sees nothing');
});

test('hydration is additive: it never overwrites a local id', () => {
  const at = html.indexOf('function sdHydrateAll(){');
  const src = html.slice(at, html.indexOf('window.sdHydrateAll', at));
  assert.match(src, /!have\[String\(r\.id\)\]/,
    'the merge no longer checks whether the id is already local');
  assert.ok(src.indexOf('sdSyncSuppressed=true') !== -1,
    'hydrated rows would be echoed straight back to the server');
});

section('soft delete: marked and hidden, never destroyed');

test("the verb is 'soft_delete', not 'delete'", () => {
  // 'delete' already exists on this platform and means a real DELETE -- the
  // SAIRNcode branch issues the only method:'DELETE' in api/sd-data.js. Two
  // verbs that destroy different amounts of data must not share a name.
  // ── SCOPE CORRECTED 2026-09-10, and the correction is the interesting part ──
  // This counted `soft_delete` across the PLATFORM-WIDE registry aggregate and
  // asserted 21, which is StoneDesk's number. It read as a StoneDesk assertion
  // and was not one. eb640ae8 gave `dnt_supplies` the verb -- a deliberate,
  // reviewed decision in another app -- and this went red on a CORRECT change,
  // which is the shape that gets an assertion loosened or deleted rather than
  // fixed.
  //
  // So it is split. The StoneDesk family is counted on its own, and the verb's
  // spread beyond it is asserted BY NAME rather than by a number: a new family
  // taking `soft_delete` now has to be written down here, which is the guard the
  // original count was reaching for. "Who may delete" is not the same question
  // as "who may write", and the answer belongs somewhere a reader can find it.
  const granted = Object.keys(reg.EXTRA_ACTIONS)
    .filter((k) => (reg.EXTRA_ACTIONS[k] || []).indexOf('soft_delete') !== -1);
  const sdGranted = granted.filter((k) => k.indexOf('sd_') === 0 || k.indexOf('stonedesk') === 0);
  const elsewhere = granted.filter((k) => sdGranted.indexOf(k) === -1);
  assert.strictEqual(sdGranted.length, 21,
    'soft_delete is granted to ' + sdGranted.length + ' StoneDesk resources, not 21');
  assert.deepStrictEqual(elsewhere.sort(), ['dnt_supplies'],
    'a family outside StoneDesk gained or lost soft_delete: ' + JSON.stringify(elsewhere)
    + '. That is a real decision about who may delete -- record it here rather than '
    + 'widening a count past it.');
  // Same scope correction: handlerMap() is StoneDesk's SD_LOCAL_RESOURCES, so
  // this can only speak for StoneDesk's grants. dnt_supplies is backed by
  // SAIRNdental's own map and is checked by SAIRNdental's own suite.
  sdGranted.forEach((k) => {
    assert.ok(handlerMap()[k], k + ' has soft_delete but is not a backed-up resource');
    assert.ok((reg.EXTRA_ACTIONS[k] || []).indexOf('delete') === -1,
      k + ' grants the HARD delete verb as well -- the two must not both be reachable here');
  });
});

test('the handler never issues a real DELETE for these resources', () => {
  const at = api.indexOf("if (SD_LOCAL_RESOURCES[resource] && action === 'soft_delete')");
  assert.ok(at > 0, 'the soft_delete branch is gone');
  const body = api.slice(at, at + 3000);
  assert.ok(body.indexOf("method: 'DELETE'") === -1, 'the soft delete issues a real DELETE');
  assert.ok(body.indexOf("method: 'PATCH'") !== -1, 'it no longer updates the row in place');
  assert.ok(body.indexOf('_deleted_at') !== -1, 'the marker is gone');
});

test('it is READ-MODIFY-WRITE, not a blind upsert of the caller copy', () => {
  // A delete must not double as an opportunity to overwrite the stored record
  // with a stale client copy.
  const at = api.indexOf("if (SD_LOCAL_RESOURCES[resource] && action === 'soft_delete')");
  const body = api.slice(at, at + 2600);
  const readAt = body.indexOf("select=data");
  const writeAt = body.indexOf("method: 'PATCH'");
  assert.ok(readAt > 0 && writeAt > readAt, 'it writes without reading what is stored');
  assert.ok(body.indexOf('Object.assign({}, stored,') !== -1,
    'the stored record is not preserved -- the marker is being applied to the payload instead');
});

test('a missing record is a 404, not a silent success', () => {
  const at = api.indexOf("if (SD_LOCAL_RESOURCES[resource] && action === 'soft_delete')");
  const body = api.slice(at, at + 2600);
  assert.ok(body.indexOf("code: 'NOT_FOUND'") !== -1,
    'deleting a record that is not there reports success -- the false-success shape this repo keeps recording');
  assert.ok(body.indexOf('nothing was deleted') !== -1);
});

test('reads EXCLUDE soft-deleted rows, and the filter is null-safe for old rows', () => {
  const at = api.indexOf("if (SD_LOCAL_RESOURCES[resource] && action === 'read')");
  const body = api.slice(at, at + 900);
  assert.ok(body.indexOf('data->>_deleted_at=is.null') !== -1,
    'a soft-deleted record still comes back on read');
  // A row written before this existed has no _deleted_at key at all, so ->>
  // yields NULL and is.null matches it. The filter must be is.null, never
  // eq.something, or every pre-existing row would vanish.
  assert.ok(body.indexOf('_deleted_at=eq.') === -1, 'the filter would hide every pre-existing row');
});

test('the schema still grants no delete privilege -- soft delete needed none', () => {
  const sqlCode = sql.split(String.fromCharCode(10)).filter((l) => l.trim().indexOf('--') !== 0).join(String.fromCharCode(10));
  assert.ok(!/grant[^;]*delete/i.test(sqlCode));
  assert.ok(/grant select, insert, update/.test(sqlCode));
});

(async () => {
  for (const item of queue) {
    if (item.section) { console.log('--- ' + item.section + ' ---'); continue; }
    try { await item.f(); console.log('  ok   ' + item.n); pass++; }
    catch (e) { console.log('  FAIL ' + item.n + '\n       ' + e.message); fail++; }
  }
  console.log('\nstonedesk_server_backup: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
