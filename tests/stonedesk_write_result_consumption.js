// tests/stonedesk_write_result_consumption.js
//
// Run:  node tests/stonedesk_write_result_consumption.js
//
// THE OTHER HALF OF docs/2026-09-26-fire-and-forget-write-audit.md. That pass
// found five writes whose result nobody reads, decided all five, and changed no
// code. Findings 4 and 5 -- `slabSyncOne()` and `sdLineageSyncOne()` -- were
// recorded as REAL and UNDOCUMENTED and left for their own change. This is that
// change's suite.
//
// AND IT CAUGHT A THIRD THING, which is why this file is not only about those
// two. Finding 2's fix (saveSD3Data batching, 2026-09-26) reads its result
// through `sdData()`, and `sdData()` returns `j.data`. The `write_batch`
// response carries NO `data` key -- it is `{ok, written, refused,
// skipped_without_id}` -- so the client saw `undefined` on every SUCCESSFUL
// batch and:
//
//   * warned "the customer list did not reach the server" on every save that
//     DID reach the server, and
//   * never reached the `refused` branch at all, so a customer deleted on
//     another device was never dropped locally -- the exact resurrection
//     tests/customer_delete_does_not_resurrect.js exists to prevent, arriving
//     by a second route, and
//   * stopped marking written ids in the synced map (`sdMarkSynced` fires only
//     for `action === 'write'`), which is the server-wins carve-out's whole
//     input. Every sd_customers id became "never pushed" and therefore
//     un-overwritable by hydration.
//
// One landed fix, three silent consequences, none of them visible from a green
// suite -- because nothing drove the CLIENT's consumption of a `write_batch`
// response. The endpoint's own suite (api/sd-data-customers-batch.test.js) is
// thorough about what the server sends and says nothing about what the browser
// does with it, which is the seam the defect lived in.
//
// EVERY SECTION HAS A MUTANT. A "the result is read" test that has never seen
// the result NOT read is asserting a property of its own fixture.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8');
const api = fs.readFileSync(path.join(ROOT, 'api', 'sd-data.js'), 'utf8');

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n--- ' + t + ' ---'); }

// Taken from the file, never re-declared here: a hand-copied body goes stale
// silently and this repo has recorded that five times.
function grabAt(sig, indent) {
  const s = html.indexOf(sig);
  assert.ok(s > 0, 'not found in stonedesk.html: ' + sig);
  const m = html.slice(s).match(new RegExp('\\r?\\n' + indent + '\\};?(?=\\r?\\n)'));
  assert.ok(m, 'not terminated: ' + sig);
  return html.slice(s).slice(0, m.index + m[0].length);
}
function grabLine(sig) {
  const s = html.indexOf(sig);
  assert.ok(s > 0, 'not found in stonedesk.html: ' + sig);
  return html.slice(s, html.indexOf('\n', s));
}

const TRANSPORT = [
  grabLine('var _sdAuthRefused = {};'),
  grabLine('var _sdReadFailed  = {};'),
  grabLine('var _sdLastStatus  = {};'),
  grabLine('var SD_FETCH_TIMEOUT_MS = 15000;'),
  grabLine("var SD_SYNCED_KEY='sd_synced_ids';")
].join('\n') + '\n\n' + [
  grabAt('function sdFetchTimeoutSignal(){', ''),
  grabAt('async function sdData(action, resource, payload) {', ''),
  grabAt('function sdDataFailed(action, resource, why) {', ''),
  grabAt('function sdSyncedRead(){', ''),
  grabAt('function sdMarkSynced(resource,id){', '')
].join('\n\n') + '\n';

const SLAB_SYNC_ONE = grabAt('async function slabSyncOne(slab){', '');

const UNITS = [
  grabAt('function saveSD3Data() {', ''),
  SLAB_SYNC_ONE,
  grabAt('async function sdLineageSyncOne(resource, rec){', ''),
  grabLine('function slabLicKey(){ return sdLicenseKey(); }')
].join('\n\n');

function build(transport, opts) {
  opts = opts || {};
  const calls = { fetch: [], warns: [], stored: {}, rendered: 0 };
  const store = Object.assign({}, opts.localStorage || {});
  const ctx = {
    console: {
      log: console.log,
      warn: function () { calls.warns.push(Array.prototype.slice.call(arguments).join(' ')); },
      error: function () { calls.warns.push(Array.prototype.slice.call(arguments).join(' ')); }
    },
    Promise: Promise, JSON: JSON, Array: Array, Object: Object, String: String,
    Date: Date, Math: Math, setTimeout: setTimeout, clearTimeout: clearTimeout,
    sdCustomers: (opts.customers || []).map(function (c) { return Object.assign({}, c); }),
    sdPhotos: [],
    st: function (k, v) { calls.stored[k] = v; store[k] = JSON.stringify(v); return true; },
    localStorage: {
      getItem: function (k) { return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null; },
      setItem: function (k, v) { store[k] = v; }
    },
    sessionStorage: { getItem: function () { return 'tok'; }, setItem: function () {} },
    renderCustomers: function () { calls.rendered++; },
    sdLicenseKey: function () { return opts.noLicence ? '' : 'SD-TEST-2026'; },
    fetch: async function (url, init) {
      const body = init && init.body ? JSON.parse(init.body) : {};
      calls.fetch.push({ url: String(url), body: body });
      const r = opts.route(body);
      if (r && r.thrown) throw new Error(r.thrown);
      return {
        ok: r.status >= 200 && r.status < 300,
        status: r.status,
        json: async function () { return r.json; }
      };
    }
  };
  ctx.globalThis = ctx;
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(transport + '\n\n' + (opts.units || UNITS), ctx,
    { filename: 'stonedesk-write-result-extract.js' });
  return { ctx: ctx, calls: calls, store: store };
}

// A settle that does not depend on a timer: saveSD3Data is deliberately NOT
// awaited, so the assertions need the microtask queue drained rather than a
// sleep whose length is a guess.
async function settle() { for (let i = 0; i < 12; i++) await Promise.resolve(); }

function batchRoute(answer) {
  return function (body) {
    if (body.action === 'write_batch') return answer;
    return { status: 200, json: { ok: true, data: null } };
  };
}
function envelope(written, refused, skipped) {
  return { status: 200, json: { ok: true, written: written,
                                refused: refused || [], skipped_without_id: skipped || 0 } };
}

const CUSTS = [{ id: 'C-1', name: 'One' }, { id: 'C-2', name: 'Two' }];

(async function main() {
  console.log('StoneDesk -- a write whose result nobody reads, and the three '
    + 'consequences of reading the WRONG result');

  // ══ 0. the fixture is checked against the endpoint, not invented ═════════
  section('0. the write_batch envelope asserted against below is the REAL one');

  await test('api/sd-data.js write_batch answers ok/written and carries NO data key', () => {
    const i = api.indexOf("if (action === 'write_batch') {");
    assert.ok(i > 0, 'write_batch branch not found in api/sd-data.js');
    const branch = api.slice(i, i + 6000);
    const oks = branch.match(/res\.status\(200\)\.json\(\{[^}]*\}/g) || [];
    assert.ok(oks.length >= 2, 'expected at least two 200 responses, found ' + oks.length);
    oks.forEach(function (o) {
      assert.ok(/ok:\s*true/.test(o), 'a 200 response without ok:true: ' + o);
      assert.ok(/written:/.test(o), 'a 200 response without written: ' + o);
      assert.ok(!/\bdata:/.test(o),
        'the endpoint GAINED a data key -- this suite asserts the opposite and '
        + 'both halves must move together: ' + o);
    });
  });

  // ══ 1. the defect, reproduced ════════════════════════════════════════════
  section('1. MUTATION: reading j.data on a write_batch calls every success a failure');

  await test('MUTANT: sdData returning j.data makes a SUCCESSFUL batch warn', async () => {
    const mutant = TRANSPORT.replace(
      /return \(action === 'write_batch'\) \? j : j\.data;/,
      'return j.data;');
    assert.notStrictEqual(mutant, TRANSPORT,
      'the mutation did not apply -- sdData no longer carries the write_batch '
      + 'carve-out this control mutates, so this arm is proving nothing');
    const b = build(mutant, { customers: CUSTS, route: batchRoute(envelope(2)) });
    b.ctx.saveSD3Data();
    await settle();
    assert.ok(b.calls.warns.some(function (w) { return /did not reach the server/.test(w); }),
      'the MUTANT did not warn on a successful batch -- this control is proving '
      + 'nothing');
  });

  // ══ 2. the fix: a success is a success, a failure is still a failure ═════
  section('2. a successful batch is not reported as a failure');

  await test('a 200 ok:true write_batch produces NO failure warning', async () => {
    const b = build(TRANSPORT, { customers: CUSTS, route: batchRoute(envelope(2)) });
    b.ctx.saveSD3Data();
    await settle();
    const bad = b.calls.warns.filter(function (w) { return /did not reach the server/.test(w); });
    assert.strictEqual(bad.length, 0, 'warned on a success: ' + JSON.stringify(bad));
  });

  await test('a 503 batch still warns -- the fix did not silence the branch', async () => {
    const b = build(TRANSPORT, {
      customers: CUSTS,
      route: batchRoute({ status: 503, json: { error: { code: 'NOT_PROVISIONED' } } })
    });
    b.ctx.saveSD3Data();
    await settle();
    assert.ok(b.calls.warns.some(function (w) { return /did not reach the server/.test(w); }),
      'a 503 batch was not reported');
  });

  await test('a 200 carrying ok:false still warns', async () => {
    const b = build(TRANSPORT, {
      customers: CUSTS,
      route: batchRoute({ status: 200, json: { ok: false, error: { code: 'NOPE' } } })
    });
    b.ctx.saveSD3Data();
    await settle();
    assert.ok(b.calls.warns.some(function (w) { return /did not reach the server/.test(w); }),
      'an ok:false batch was treated as a success');
  });

  // ══ 3. refused ids are dropped locally ═══════════════════════════════════
  section('3. the refused branch is REACHABLE, which is what stops a resurrection');

  await test('a refused id is dropped from sdCustomers and the panel re-rendered', async () => {
    const b = build(TRANSPORT, {
      customers: CUSTS,
      route: batchRoute(envelope(1,
        [{ id: 'C-2', code: 'DELETED', reason: 'deleted on another device' }], 0))
    });
    b.ctx.saveSD3Data();
    await settle();
    const ids = b.ctx.sdCustomers.map(function (c) { return c.id; });
    assert.deepStrictEqual(ids, ['C-1'],
      'the refused customer was not dropped locally -- it will be written again '
      + 'on the next save and read back by hydration. ids=' + JSON.stringify(ids));
    assert.ok(b.calls.rendered > 0, 'the panel was not re-rendered after the drop');
  });

  // ══ 4. the synced map ════════════════════════════════════════════════════
  section('4. a batch that LANDED marks its ids synced -- the server-wins input');

  await test('every written id enters sd_synced_ids', async () => {
    const b = build(TRANSPORT, {
      customers: CUSTS,
      localStorage: { sd_synced_ids: JSON.stringify({}) },
      route: batchRoute(envelope(2))
    });
    b.ctx.saveSD3Data();
    await settle();
    const map = JSON.parse(b.store.sd_synced_ids || '{}');
    assert.deepStrictEqual((map.sd_customers || []).slice().sort(), ['C-1', 'C-2'],
      'a batched write did not mark its ids synced, so hydration will never '
      + 'overwrite a customer this device pushed. map=' + JSON.stringify(map));
  });

  await test('a REFUSED id is NOT marked synced', async () => {
    const b = build(TRANSPORT, {
      customers: CUSTS,
      localStorage: { sd_synced_ids: JSON.stringify({}) },
      route: batchRoute(envelope(1, [{ id: 'C-2', code: 'DELETED', reason: 'gone' }], 0))
    });
    b.ctx.saveSD3Data();
    await settle();
    const map = JSON.parse(b.store.sd_synced_ids || '{}');
    assert.deepStrictEqual(map.sd_customers || [], ['C-1'],
      'a refused id was marked synced -- it was never written. map='
      + JSON.stringify(map));
  });

  await test('a FAILED batch marks nothing synced', async () => {
    const b = build(TRANSPORT, {
      customers: CUSTS,
      localStorage: { sd_synced_ids: JSON.stringify({}) },
      route: batchRoute({ status: 500, json: { error: {} } })
    });
    b.ctx.saveSD3Data();
    await settle();
    const map = JSON.parse(b.store.sd_synced_ids || '{}');
    assert.deepStrictEqual(map.sd_customers || [], [],
      'a failed batch marked ids synced -- hydration would then overwrite local '
      + 'edits the server never received. map=' + JSON.stringify(map));
  });

  // ══ 5. finding 4: slabSyncOne ════════════════════════════════════════════
  section('5. finding 4 -- slabSyncOne answers whether the slab reached the server');

  await test('a 403 (slabs is session-gated) answers false, not undefined', async () => {
    const b = build(TRANSPORT, {
      route: function (body) {
        if (body.resource === 'slabs') return { status: 403, json: { error: { code: 'NO_SESSION' } } };
        return { status: 200, json: { ok: true, data: null } };
      }
    });
    const r = await b.ctx.slabSyncOne({ id: 'S-1', status: 'Reserved' });
    assert.strictEqual(r, false,
      'slabSyncOne returned ' + JSON.stringify(r) + ' on a 403. pcToggleSlab '
      + 'tests `ok === false` to show its "the catalog on the web has NOT '
      + 'changed" warning, so anything else leaves that warning unreachable.');
  });

  await test('a landed write answers true', async () => {
    const b = build(TRANSPORT, {
      route: function (body) {
        if (body.resource === 'slabs') return { status: 200, json: { ok: true, data: { id: 'S-1' } } };
        return { status: 200, json: { ok: true, data: null } };
      }
    });
    assert.strictEqual(await b.ctx.slabSyncOne({ id: 'S-1' }), true);
  });

  await test('no licence answers false rather than a silent nothing', async () => {
    const b = build(TRANSPORT, {
      noLicence: true,
      route: function () { return { status: 200, json: { ok: true, data: null } }; }
    });
    assert.strictEqual(await b.ctx.slabSyncOne({ id: 'S-1' }), false);
    assert.strictEqual(b.calls.fetch.length, 0, 'it called the server with no licence');
  });

  await test('a network throw answers false and does not reject', async () => {
    const b = build(TRANSPORT, { route: function () { return { thrown: 'ECONNREFUSED' }; } });
    assert.strictEqual(await b.ctx.slabSyncOne({ id: 'S-1' }), false);
  });

  await test('a failure is REPORTED, not only returned -- six of seven callers '
    + 'ignore the value', async () => {
    const b = build(TRANSPORT, {
      route: function (body) {
        if (body.resource === 'slabs') return { status: 403, json: { error: {} } };
        return { status: 200, json: { ok: true, data: null } };
      }
    });
    await b.ctx.slabSyncOne({ id: 'S-1', status: 'Reserved' });
    // NAMES THE SLAB, not the resource. sdData() already warns `write "slabs"
    // did NOT reach the server`, so an arm that accepted any warning would pass
    // for the pre-fix body too -- it did, before this was tightened. The id is
    // the part only this site can supply, and six of the seven callers discard
    // the return value, so the log is the only place the WHICH is recorded.
    const named = b.calls.warns.filter(function (w) { return /S-1/.test(w); });
    assert.ok(named.length > 0,
      'a slab hold, release or status change that never reached the server left '
      + 'no trace NAMING THE SLAB. That is the reserve/release path a '
      + 'salesperson acts on. warns=' + JSON.stringify(b.calls.warns));
  });

  await test('MUTANT: the pre-fix body returns undefined on a 403', async () => {
    const mutant = UNITS.replace(SLAB_SYNC_ONE,
      ['async function slabSyncOne(slab){',
       "  if(typeof sdData!=='function') return;",
       '  var lic=slabLicKey(); if(!lic) return;',
       "  try{ await sdData('write','slabs',slab); }catch(e){}",
       '}'].join('\n'));
    assert.notStrictEqual(mutant, UNITS, 'the slabSyncOne mutation did not apply');
    const b = build(TRANSPORT, {
      units: mutant,
      route: function (body) {
        if (body.resource === 'slabs') return { status: 403, json: { error: {} } };
        return { status: 200, json: { ok: true, data: null } };
      }
    });
    assert.strictEqual(await b.ctx.slabSyncOne({ id: 'S-1' }), undefined,
      'the MUTANT did not swallow the 403 -- this control is proving nothing');
  });

  // ══ 6. finding 5: sdLineageSyncOne ═══════════════════════════════════════
  section('6. finding 5 -- sdLineageSyncOne answers whether the history row landed');

  await test('a failed lineage write answers false', async () => {
    const b = build(TRANSPORT, {
      route: function (body) {
        if (body.action === 'write') return { status: 500, json: { error: {} } };
        return { status: 200, json: { ok: true, data: null } };
      }
    });
    assert.strictEqual(await b.ctx.sdLineageSyncOne('sd_slab_history', { id: 'EVT1' }), false);
  });

  await test('a landed lineage write answers true', async () => {
    const b = build(TRANSPORT, {
      route: function () { return { status: 200, json: { ok: true, data: { id: 'EVT1' } } }; }
    });
    assert.strictEqual(await b.ctx.sdLineageSyncOne('sd_slab_history', { id: 'EVT1' }), true);
  });

  await test('a dropped history row is REPORTED', async () => {
    const b = build(TRANSPORT, {
      route: function (body) {
        if (body.action === 'write') return { status: 500, json: { error: {} } };
        return { status: 200, json: { ok: true, data: null } };
      }
    });
    await b.ctx.sdLineageSyncOne('sd_blocks', { id: 'BLK1' });
    // Same tightening as the slab arm: the id, which only this site knows.
    const named = b.calls.warns.filter(function (w) { return /BLK1/.test(w); });
    assert.ok(named.length > 0,
      'a dropped lineage row left no trace NAMING THE ROW. The slab\'s current '
      + 'state still looks right and the history that would contradict it is '
      + 'absent. warns=' + JSON.stringify(b.calls.warns));
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
