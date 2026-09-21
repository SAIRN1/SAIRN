// tests/collection_delete_reaches_the_server.js
//
// Run:  node tests/collection_delete_reaches_the_server.js
//
// TWENTY-ONE COLLECTIONS HAD A DELETE BUTTON THAT ONLY DELETED LOCALLY, and
// every one of them undid itself.
//
//   sdSyncCollection()  pushed WRITES and nothing else. A row removed from a
//                       panel simply stopped being pushed; its server row was
//                       never touched.
//   sdHydrateAll()      merges the server's rows back in BY ID and never
//                       deletes -- so the record reappeared on the next load.
//
// invDeleteInvoice(), photoDelete(), commsDelete(), finDeleteJob(),
// tmDeleteRecord(), remakeDelete(), schedDelete(), nestingRemove() and the rest
// all had that shape: a deletion the user watched succeed, already scheduled to
// reverse itself. Identical to the sd_customers defect of 2026-09-12, twenty-one
// times over.
//
// The api/sd-data.js soft_delete branch and its `data->>_deleted_at=is.null`
// read filter have existed since 2026-09-08. ONLY THE CALL WAS MISSING -- 21
// verbs declared in api/_resources/stonedesk.js that nothing ever invoked.
//
// WIRED IN ONE PLACE, NOT TWENTY-ONE. sdSyncCollection() is already the seam
// every write goes through, keyed by the same storage key, computing the same
// diff. Section 4's registry arm is what stops the twenty-second from being
// added without a verb.
//
// THE GUARDS ARE MOST OF THIS FILE, because the failure mode of a removal sweep
// is mass deletion, not a missed one. Section 2 proves each guard is
// load-bearing by removing it and demanding the damage.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try {
    const r = fn();
    // A SYNCHRONOUS RUNNER MUST REFUSE A PROMISE rather than print `ok` for a
    // check that has not run. The first version of the reporting arms below
    // returned one and passed on nothing at all.
    assert.ok(!r || typeof r.then !== 'function',
      'this arm returned a promise to the synchronous runner -- use atest()');
    console.log('  ok   ' + name); pass++;
  } catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
// Async arms are queued and awaited in order at the end, so their output stays
// where a reader expects it.
const ASYNC = [];
function atest(name, fn) { ASYNC.push([name, fn]); }
async function runAsync() {
  for (const [name, fn] of ASYNC) {
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
  }
}
function section(t) { console.log('--- ' + t + ' ---'); }

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
function grabBlock(startSig, endSig) {
  const s = html.indexOf(startSig);
  assert.ok(s > 0, 'not found: ' + startSig);
  const e = html.indexOf(endSig, s);
  assert.ok(e > s, 'terminator not found: ' + endSig);
  return html.slice(s, e + endSig.length);
}

// The real seam, end to end: the synced-key list, the suppression flag, st()
// and the sync function itself. st() is included deliberately -- proving
// sdSyncCollection() deletes is not the same as proving anything CALLS it, and
// the hook in st() is where that happens.
const UNIT = [
  grabBlock('var SD_SYNCED=[', 'SD_SYNCED.forEach(function(k){SD_SYNCED_ON[k]=true;});'),
  // Taken from the file, not restated here. sdSyncCollection() reads it on the
  // non-array path, so leaving it out would make every object-shaped arm throw
  // ReferenceError inside the vm -- and the array arms would stay green, which
  // is how a gap like this survives.
  grabLine('var SD_SYNCED_OBJECT={'),
  'var sdSyncSuppressed=false;',
  grabAt('function st(key,data){', ''),
  grabAt('function sdSyncCollection(key,next,prev){', ''),
  grabLine('var _sdCapped={};'),
  grabAt('function sdCapLocal(key,arr,max){', ''),
  grabAt('function sdCapLocalTail(key,arr,max){', '')
].join('\n\n');

function build(opts) {
  opts = opts || {};
  const calls = [];
  const warns = [];
  const notes = [];
  const store = Object.assign({}, opts.store || {});
  const ctx = {
    console: { warn: m => warns.push(String(m)), error: () => {}, log: () => {} },
    localStorage: {
      // readFails EXISTS BECAUSE A MUTATION WENT UNNOTICED. The object-hydration
      // path's fail-closed branch is `try{ ... }catch(e){ return; }` around a
      // getItem, and nothing here could drive it -- storageFails only throws on
      // setItem -- so turning that `return` into a no-op was invisible.
      getItem: k => {
        if (opts.readFails) throw new Error('unreadable');
        return (k in store ? store[k] : null);
      },
      setItem: (k, v) => { if (opts.storageFails) throw new Error('quota'); store[k] = v; },
      // The bootstrap's undo path calls removeItem when a flag write fails.
      removeItem: k => { delete store[k]; }
    },
    sdStorageFailed: () => {},
    sdBackupHookFailed: (k, e) => warns.push('HOOK THREW ' + k + ' ' + (e && e.message)),
    notify: (m, kind) => notes.push({ m: String(m), kind }),
    sdLicenseKey: () => (opts.noLicence ? '' : 'SD-TEST-2026'),
    sdData: (action, key, payload) => {
      calls.push({ action, key, payload });
      const answer = opts.answer ? opts.answer(action, key, payload) : {};
      return Promise.resolve(answer);
    },
    __store: store
  };
  ctx.window = ctx;
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(opts.mutate ? opts.mutate(UNIT) : UNIT, ctx,
    { filename: 'stonedesk-sync-extract.js' });
  return { ctx, calls, warns, notes, store };
}

const ROWS = [{ id: 'A', v: 1 }, { id: 'B', v: 2 }, { id: 'C', v: 3 }];
const dels = b => b.calls.filter(c => c.action === 'soft_delete');
const writes = b => b.calls.filter(c => c.action === 'write');

// Seeds localStorage with `prev` the way a real device would hold it, then
// saves `next` through the REAL st(), so the hook is exercised rather than
// sdSyncCollection() being called by hand.
function save(b, key, next) { b.ctx.st(key, next); }
function seeded(key, prev, opts) {
  const store = {}; store[key] = JSON.stringify(prev);
  return build(Object.assign({ store }, opts || {}));
}

(function main() {
  console.log('StoneDesk synced collections -- a delete that now leaves the device\n');

  // ══ 1. the wiring ════════════════════════════════════════════════════════
  section('a removal reaches the server, through the real st() hook');

  test('removing one row issues soft_delete for exactly that id', () => {
    const b = seeded('sd_invoices', ROWS);
    save(b, 'sd_invoices', [ROWS[0], ROWS[2]]);
    assert.deepStrictEqual(dels(b).map(c => c.payload.id), ['B']);
    assert.strictEqual(dels(b)[0].key, 'sd_invoices');
  });

  // NOT deepStrictEqual. The payload object is created INSIDE the vm, so it
  // carries the vm realm's Object.prototype and deepStrictEqual reports "same
  // structure but not reference-equal" against a host literal -- the same
  // cross-realm trap already recorded for empty arrays in the active-work log.
  // Compared field by field, which is what the assertion actually means.
  test('the payload is the id ALONE -- a delete is not a write', () => {
    const b = seeded('sd_photos', ROWS);
    save(b, 'sd_photos', [ROWS[0], ROWS[1]]);
    const p = dels(b)[0].payload;
    assert.deepStrictEqual(Object.keys(p).sort(), ['id']);
    assert.strictEqual(p.id, 'C');
  });

  test('removing several issues one call each, and no writes', () => {
    const b = seeded('sd_comms', ROWS);
    save(b, 'sd_comms', [ROWS[1]]);
    assert.deepStrictEqual(dels(b).map(c => c.payload.id).sort(), ['A', 'C']);
    assert.strictEqual(writes(b).length, 0);
  });

  test('an unchanged save issues nothing at all', () => {
    const b = seeded('sd_fin_jobs', ROWS);
    save(b, 'sd_fin_jobs', ROWS.map(r => Object.assign({}, r)));
    assert.strictEqual(b.calls.length, 0);
  });

  test('a changed row still WRITES -- the removal sweep did not displace it', () => {
    const b = seeded('sd_remakes', ROWS);
    save(b, 'sd_remakes', [ROWS[0], { id: 'B', v: 99 }, ROWS[2]]);
    assert.deepStrictEqual(writes(b).map(c => c.payload.id), ['B']);
    assert.strictEqual(dels(b).length, 0);
  });

  test('an edit AND a delete in one save produce both', () => {
    const b = seeded('sd_inventory', ROWS);
    save(b, 'sd_inventory', [{ id: 'A', v: 42 }, ROWS[1]]);
    assert.deepStrictEqual(writes(b).map(c => c.payload.id), ['A']);
    assert.deepStrictEqual(dels(b).map(c => c.payload.id), ['C']);
  });

  test('a row with no id cannot be deleted, and does not throw', () => {
    const b = seeded('sd_sms_log', [{ v: 1 }, ROWS[0]]);
    save(b, 'sd_sms_log', []);
    assert.deepStrictEqual(dels(b).map(c => c.payload.id), ['A']);
  });

  // ══ 2. the guards, each proven load-bearing by removing it ═══════════════
  section('the guards -- a removal sweep fails by deleting too much');

  test('prev === null issues NO deletes: a cleared cache is not a deletion', () => {
    const b = build({});                       // localStorage empty
    save(b, 'sd_invoices', []);
    assert.strictEqual(dels(b).length, 0);
  });

  // ── AN HONEST NOTE ABOUT THAT GUARD, because a probe that cannot bite must
  // not pretend it did. `if(!Array.isArray(prev)) return;` is DEFENSIVE, NOT
  // load-bearing: `before` is built from `(Array.isArray(prev)?prev:[])`, so a
  // null or malformed prev already yields an empty `before` and an empty
  // removal loop. Removing the early return changes no behaviour, and a mutant
  // asserting otherwise would be a green arm proving nothing. The arm below
  // asserts the PROPERTY -- a cleared cache deletes nothing -- by BOTH routes,
  // which is the thing that actually has to stay true.
  test('a malformed prev also deletes nothing, with or without the early return', () => {
    const mk = mutate => {
      const b = build({ store: { sd_invoices: '"not-an-array"' }, mutate });
      save(b, 'sd_invoices', []);
      return dels(b).length;
    };
    assert.strictEqual(mk(undefined), 0);
    assert.strictEqual(mk(src => {
      const out = src.replace('  if(!Array.isArray(prev)) return;\n', '');
      assert.notStrictEqual(out, src, 'the prev guard anchor no longer matches the source');
      return out;
    }), 0, '`before` is supposed to be the real protection here, and it is not');
  });

  test('sdSyncSuppressed blocks deletes -- hydration must not delete', () => {
    const b = seeded('sd_drawings', ROWS);
    b.ctx.sdSyncSuppressed = true;
    save(b, 'sd_drawings', []);
    assert.strictEqual(b.calls.length, 0);
  });

  test('MUTANT: without suppression, a hydrate-shaped save deletes everything', () => {
    const b = seeded('sd_drawings', ROWS, {
      mutate: src => {
        const out = src.replace('  if(sdSyncSuppressed) return;\n', '');
        assert.notStrictEqual(out, src, 'the suppression anchor no longer matches');
        return out;
      }
    });
    b.ctx.sdSyncSuppressed = true;
    save(b, 'sd_drawings', []);
    assert.strictEqual(dels(b).length, 3, 'the mutant did not reproduce the damage');
  });

  test('no licence: nothing is sent, so an unlicensed install deletes nothing', () => {
    const b = seeded('sd_invoices', ROWS, { noLicence: true });
    save(b, 'sd_invoices', []);
    assert.strictEqual(b.calls.length, 0);
  });

  test('a key that is NOT synced never reaches the hook at all', () => {
    const b = seeded('sd_not_a_synced_key', ROWS);
    save(b, 'sd_not_a_synced_key', []);
    assert.strictEqual(b.calls.length, 0);
  });

  test('a FAILED local write does not delete anything on the server', () => {
    const b = seeded('sd_invoices', ROWS, { storageFails: true });
    save(b, 'sd_invoices', []);
    assert.strictEqual(b.calls.length, 0,
      'the server was told to delete rows this device did not manage to remove');
  });

  // ══ 3. a failed delete is the dangerous direction ════════════════════════
  section('a delete that did not land is SAID, not logged and forgotten');

  // THE REPORTING RUNS IN A .then(), so these two have to wait for the
  // microtask queue. The first version of this arm returned a promise to a
  // SYNCHRONOUS runner and asserted nothing at all -- it printed `ok` for a
  // check that had not happened yet, which is the shape this whole file exists
  // to catch. `await flush()` is what makes it real.
  const flush = () => new Promise(r => setImmediate(r));

  atest('a null answer warns on the console AND on screen', async () => {
    const b = seeded('sd_invoices', ROWS, { answer: () => null });
    save(b, 'sd_invoices', [ROWS[0], ROWS[1]]);
    await flush();
    assert.ok(b.warns.some(w => /record C was deleted on this device but NOT on the server/.test(w)),
      'no console warning: ' + JSON.stringify(b.warns));
    assert.ok(b.notes.some(n => /may come back/i.test(n.m)),
      'the user was told nothing: ' + JSON.stringify(b.notes));
  });

  atest('a successful delete says nothing, on either channel', async () => {
    const b = seeded('sd_invoices', ROWS, { answer: () => ({ ok: true }) });
    save(b, 'sd_invoices', [ROWS[0], ROWS[1]]);
    await flush();
    assert.strictEqual(b.notes.length, 0, JSON.stringify(b.notes));
    assert.strictEqual(b.warns.length, 0, JSON.stringify(b.warns));
  });

  atest('a failed WRITE is logged but NOT toasted -- the two are not symmetric', async () => {
    const b = seeded('sd_invoices', ROWS, { answer: () => null });
    save(b, 'sd_invoices', [ROWS[0], { id: 'B', v: 99 }, ROWS[2]]);
    await flush();
    assert.ok(b.warns.some(w => /saved on this device only/.test(w)), 'the write failure was silent');
    assert.strictEqual(b.notes.length, 0,
      'a failed write toasted the user -- it leaves the record on screen and re-saving retries, '
      + 'so it is a console matter; only a failed DELETE makes a record vanish while it survives');
  });

  // ══ 3b. a local cap is not a deletion ════════════════════════════════════
  section('a length cap trims the DEVICE, not the archive');

  test('rows dropped by sdCapLocal are not deleted on the server', () => {
    const b = seeded('sd_drawings', ROWS);
    const kept = b.ctx.sdCapLocal('sd_drawings', ROWS.slice(), 2);
    save(b, 'sd_drawings', kept);
    assert.strictEqual(dels(b).length, 0,
      'the cap told the server the dropped row had been deleted: ' + JSON.stringify(dels(b)));
  });

  test('and the cap really did shorten the local list', () => {
    const b = build({});
    assert.deepStrictEqual(b.ctx.sdCapLocal('sd_drawings', ROWS.slice(), 2).length, 2);
    // The argument is not mutated -- the call sites assign the result.
    const src = ROWS.slice();
    b.ctx.sdCapLocal('sd_drawings', src, 1);
    assert.strictEqual(src.length, 3);
  });

  // ── THE TAIL VARIANT HAD ONLY A SOURCE-LEVEL ARM ────────────────────────
  // sdCapLocalTail() was added for sd_exec_msgs, which trims with slice(-500)
  // -- keeping the NEWEST. Until now the only thing asserted about it was that
  // execSend() calls it; nothing had ever watched it exempt a row. A helper
  // with a source-level arm and no behavioural one is the same shape as a
  // checker nobody has seen fail: it looks covered and is not.
  test('sdCapLocalTail keeps the NEWEST and exempts what it dropped', () => {
    const b = seeded('sd_exec_msgs', ROWS);
    const kept = b.ctx.sdCapLocalTail('sd_exec_msgs', ROWS.slice(), 2);
    assert.deepStrictEqual(kept.map(r => r.id), ['B', 'C'],
      'the tail cap kept the wrong end -- that is sdCapLocal, not sdCapLocalTail');
    save(b, 'sd_exec_msgs', kept);
    assert.strictEqual(dels(b).length, 0,
      'the tail cap told the server the dropped row had been deleted: ' + JSON.stringify(dels(b)));
  });

  test('and a real deletion alongside a tail cap is still sent', () => {
    const b = seeded('sd_exec_msgs', ROWS);
    const kept = b.ctx.sdCapLocalTail('sd_exec_msgs', ROWS.slice(), 2);   // drops A
    save(b, 'sd_exec_msgs', [kept[1]]);                                   // user deletes B
    assert.deepStrictEqual(dels(b).map(c => c.payload.id), ['B'],
      'the tail exemption swallowed a real deletion, or failed to exempt the capped row');
  });

  test('its exemption is consumed after one sweep too', () => {
    const b = seeded('sd_exec_msgs', ROWS);
    const kept = b.ctx.sdCapLocalTail('sd_exec_msgs', ROWS.slice(), 2);
    save(b, 'sd_exec_msgs', kept);                 // sweep 1: A exempt
    assert.strictEqual(dels(b).length, 0);
    save(b, 'sd_exec_msgs', [kept[1], ROWS[0]]);   // A comes back
    save(b, 'sd_exec_msgs', [kept[1]]);            // and is genuinely deleted
    assert.ok(dels(b).map(c => c.payload.id).indexOf('A') !== -1,
      'a stale tail-cap registration is still silencing a real deletion of that id');
  });

  test('it does not mutate its argument either', () => {
    const b = build({});
    const src = ROWS.slice();
    b.ctx.sdCapLocalTail('sd_exec_msgs', src, 1);
    assert.strictEqual(src.length, 3);
  });

  test('a REAL deletion in the same save is still sent', () => {
    const b = seeded('sd_drawings', ROWS);
    const kept = b.ctx.sdCapLocal('sd_drawings', ROWS.slice(), 2);   // drops C
    save(b, 'sd_drawings', [kept[0]]);                               // and the user deletes B
    assert.deepStrictEqual(dels(b).map(c => c.payload.id), ['B'],
      'the cap exemption swallowed a real deletion, or failed to exempt the capped row');
  });

  // THE EXEMPTION IS CONSUMED, NOT STANDING. A registration that outlived its
  // sweep would go on silencing real deletions of that id for ever -- an
  // exemption nobody can see is worse than a missing one.
  test('the exemption lasts exactly one sweep', () => {
    const b = seeded('sd_drawings', ROWS);
    const kept = b.ctx.sdCapLocal('sd_drawings', ROWS.slice(), 2);
    save(b, 'sd_drawings', kept);              // sweep 1: C exempt
    assert.strictEqual(dels(b).length, 0);
    save(b, 'sd_drawings', [kept[0]]);         // sweep 2: user deletes B
    assert.deepStrictEqual(dels(b).map(c => c.payload.id), ['B']);
    // And C, re-added and then genuinely deleted, is no longer exempt.
    save(b, 'sd_drawings', [kept[0], ROWS[2]]);
    save(b, 'sd_drawings', [kept[0]]);
    assert.ok(dels(b).map(c => c.payload.id).indexOf('C') !== -1,
      'a stale cap registration is still silencing a real deletion of that id');
  });

  // A SIXTH CAP ADDED LATER MUST FAIL HERE rather than quietly deleting server
  // history. Derived from the file, never from a list in this test.
  //
  // ATTRIBUTED BY THE CAP'S OWN SAVE, not by proximity. A +/-60-line window was
  // tried first and produced three false positives on `today.slice(0,7)` --
  // date strings, not array caps -- plus two real caps on keys that are NOT
  // synced (sd_quote_history, sd_stonehub_log). A cap only matters if the array
  // it trims is the one being saved under a SYNCED key, so the check follows
  // the self-assignment to the next st() call and reads THAT key.
  // BOTH SLICE FORMS. The first version of this arm only recognised
  // `x = x.slice(0,N)` -- keep the oldest -- and walked straight past
  // sd_exec_msgs' `x = x.slice(-500)`, which keeps the NEWEST. That was a sixth
  // cap on a synced collection, and it would have deleted the executive
  // channel's server history one message at a time while this arm stayed green.
  // A guard that recognises one spelling of the thing it guards is a guard with
  // a hole the exact width of the other spelling.
  test('every cap on a SYNCED collection routes its trim through sdCapLocal', () => {
    const lines = html.split('\n');
    const synced = new Set(build({}).ctx.SD_SYNCED);
    // BACKING VARIABLE -> KEY, derived once from every st(key, var) site in the
    // file. The previous version looked for that save within 12 lines of the
    // trim, and sd_exec_msgs' cap is saved by saveSD5() -- an AGGREGATE saver
    // several hundred lines away -- so the arm could not attribute it and
    // reported clean on a mutation that removed the guard. Proven by reverting
    // the exec cap and watching this stay green, which is why it was rewritten.
    const varToKey = {};
    html.replace(/st\(\s*'([a-z_]+)'\s*,\s*([A-Za-z_$][\w$]*)\s*\)/g, (all, key, v) => {
      if (synced.has(key)) varToKey[v] = key;
      return all;
    });
    const offenders = [];
    lines.forEach((l, i) => {
      const m = l.match(/\b(\w+)\s*=\s*\1\.slice\(\s*(?:0\s*,\s*\d+|-\d+)\s*\)/);
      if (!m || /sdCapLocal/.test(l)) return;
      const key = varToKey[m[1]];
      if (key) offenders.push((i + 1) + ': ' + l.trim() + '  -> ' + key);
    });
    assert.deepStrictEqual(offenders, [],
      'these trim a SYNCED collection without registering the drop, so the cap '
      + 'would delete server history: ');
  });

  // ══ 3c. the two single-object collections ════════════════════════════════
  // They sat in SD_SYNCED and NEVER SYNCED AT ALL -- `if(!Array.isArray(next))
  // return;` sent both straight out of the function. A shop's negotiated
  // supplier prices and its whole discount rule set lived in one browser and
  // died with its cache, on a list that reads as "these are backed up".
  section('an object-shaped collection is backed up too, as one row');

  test('a changed object is written as {id:"all", blob}', () => {
    const b = build({ store: { sd_negotiated_prices: JSON.stringify({ 'SKU-1': 10 }) } });
    save(b, 'sd_negotiated_prices', { 'SKU-1': 10, 'SKU-2': 22 });
    const w = writes(b);
    assert.strictEqual(w.length, 1);
    assert.strictEqual(w[0].key, 'sd_negotiated_prices');
    assert.strictEqual(w[0].payload.id, 'all');
    assert.strictEqual(w[0].payload.blob['SKU-2'], 22);
  });

  // WRAPPED, NOT SPREAD. These objects are keyed by SKU; spreading one would
  // collide with `id` the first time a vendor used that string.
  test('a SKU literally called "id" cannot collide with the row id', () => {
    const b = build({ store: { sd_negotiated_prices: JSON.stringify({}) } });
    save(b, 'sd_negotiated_prices', { id: 99 });
    assert.strictEqual(writes(b)[0].payload.id, 'all');
    assert.strictEqual(writes(b)[0].payload.blob.id, 99);
  });

  test('an unchanged object writes nothing', () => {
    const o = { 'SKU-1': 10 };
    const b = build({ store: { sd_negotiated_prices: JSON.stringify(o) } });
    save(b, 'sd_negotiated_prices', { 'SKU-1': 10 });
    assert.strictEqual(b.calls.length, 0);
  });

  test('and no soft_delete is ever issued for an object collection', () => {
    const b = build({ store: { sd_negotiated_prices: JSON.stringify({ 'SKU-1': 10, 'SKU-2': 1 }) } });
    save(b, 'sd_negotiated_prices', {});          // every SKU removed
    assert.strictEqual(dels(b).length, 0,
      'the removal sweep ran on an object -- its ids are SKUs, not rows');
  });

  test('an object key NOT declared object-shaped is still skipped entirely', () => {
    const b = build({ store: { sd_invoices: JSON.stringify([]) } });
    save(b, 'sd_invoices', { notAnArray: true });
    assert.strictEqual(b.calls.length, 0);
  });

  test('both object-shaped keys are declared, and both are in SD_SYNCED', () => {
    const b = build({});
    const declared = Object.keys(b.ctx.SD_SYNCED_OBJECT);
    assert.deepStrictEqual(declared.sort(), ['sd_negotiated_prices', 'sd_pricing_rules']);
    declared.forEach(k => assert.ok(Array.from(b.ctx.SD_SYNCED).indexOf(k) !== -1,
      k + ' is declared object-shaped but is not in SD_SYNCED, so nothing reads it'));
  });

  // ── HYDRATION IS THE RISKIER HALF, so it gets its own arms ──────────────
  // The array path's rule is "a locally present id is NEVER overwritten". The
  // object equivalent has no id to merge on, so the choice is adopt-or-leave --
  // and adopting over a shop's live discount rules from a second browser is
  // exactly the clobber that rule exists to prevent.
  // sdWhileSuppressed is pulled in DELIBERATELY, not incidentally. Hydration's
  // two writes went through it on 2026-09-14 (item 34) so a throw inside st()
  // cannot leave sdSyncSuppressed stuck on for the session. Omitting it here
  // does not fail loudly -- sdHydrateAll's own `.catch(function(){})` swallows
  // the ReferenceError and the arm below fails with "undefined is not valid
  // JSON", which is the extract being incomplete, not the app being wrong.
  const HYDRATE = [
    grabAt('function sdLoad(k,def){', ''),
    grabAt('function sdWhileSuppressed(fn){', ''),
    // ADDED 2026-09-21, AND THE WHOLE DEPENDENCY CLOSURE RATHER THAN THE ONE
    // NAME IN THE ERROR. sdHydrateAll() gained `sdSyncedBootstrap(SD_SYNCED);`
    // as its first line when the one-time bootstrap landed, and this extract
    // did not, so the four object-hydration arms threw ReferenceError inside
    // the vm. sdSyncedBootstrap() needs SD_SYNCED_KEY, sdSyncedRead(),
    // SD_BOOTSTRAP_KEY, sdBootstrappedNow and sdHydrateLoad() -- taken from
    // the file, not restated here, for the same reason the comment above gives
    // about SD_SYNCED_OBJECT.
    //
    // IT FAILED LOUDLY ONLY BECAUSE THE NEW CALL IS SYNCHRONOUS. sdHydrateAll's
    // own `.catch(function(){})` swallows a ReferenceError raised inside the
    // promise chain -- the comment below already warns about that -- so the
    // quiet version of this break is still possible for anything added after
    // the first await.
    grabLine("var SD_SYNCED_KEY='sd_synced_ids';"),
    grabAt('function sdSyncedRead(){', ''),
    grabLine("var SD_BOOTSTRAP_KEY='sd_synced_bootstrap';"),
    grabLine('var sdBootstrappedNow=false;'),
    grabAt('function sdSyncedBootstrap(resources){', ''),
    grabLine('function sdHydrateLoad(key){'),
    grabAt('function sdHydrateAll(){', '')
  ].join('\n\n');

  function hydrateWith(store, rowsByKey, extra) {
    const b = build(Object.assign({ store, answer: () => null }, extra || {}));
    b.ctx.sdData = (action, key) => {
      b.calls.push({ action, key });
      return Promise.resolve(action === 'read' ? (rowsByKey[key] || null) : {});
    };
    vm.runInContext(HYDRATE, b.ctx, { filename: 'stonedesk-hydrate-extract.js' });
    return b;
  }

  atest('an object collection this device already holds is NOT overwritten', async () => {
    const b = hydrateWith({ sd_negotiated_prices: JSON.stringify({ 'SKU-1': 1 }) },
      { sd_negotiated_prices: [{ id: 'all', blob: { 'SKU-1': 999, 'SKU-9': 5 } }] });
    await b.ctx.sdHydrateAll();
    assert.deepStrictEqual(JSON.parse(b.store.sd_negotiated_prices), { 'SKU-1': 1 },
      'a second browser overwrote this shop\'s live negotiated prices');
  });

  atest('a device that has never written one adopts the server copy', async () => {
    const b = hydrateWith({}, { sd_negotiated_prices: [{ id: 'all', blob: { 'SKU-9': 5 } }] });
    await b.ctx.sdHydrateAll();
    assert.deepStrictEqual(JSON.parse(b.store.sd_negotiated_prices), { 'SKU-9': 5 });
  });

  atest('and adopting does not echo straight back to the server', async () => {
    const b = hydrateWith({}, { sd_negotiated_prices: [{ id: 'all', blob: { 'SKU-9': 5 } }] });
    await b.ctx.sdHydrateAll();
    assert.strictEqual(b.calls.filter(c => c.action === 'write').length, 0,
      'the hydrate wrote the row it had just read -- sdSyncSuppressed was not held');
  });

  atest('a malformed server row is left alone rather than adopted', async () => {
    const b = hydrateWith({}, { sd_negotiated_prices: [{ id: 'all' }] });
    await b.ctx.sdHydrateAll();
    // NOT `=== undefined`, WHICH IS WHAT THIS ASSERTED AND WHY IT WAS VACUOUS.
    // Dropping the blob guard makes the path call st(key, undefined), whose
    // JSON.stringify IS undefined, so the key gets written and reads back
    // undefined -- satisfying the old assertion exactly while the row was in
    // fact adopted. The question is whether the key was TOUCHED, so ask that.
    assert.ok(!('sd_negotiated_prices' in b.store),
      'a server row with no blob was adopted -- the key was written as '
      + JSON.stringify(b.store.sd_negotiated_prices));
  });

  atest('and an UNREADABLE local store refuses to adopt, rather than adopting blind',
    async () => {
      // The fail-closed half of the same guard, which nothing drove before. The
      // adopt-only-if-absent test is a getItem inside a try, and on a throw the
      // only safe answer is to leave the key alone: a device whose storage is
      // unreadable must not take a second browser's blob over its own.
      const b = hydrateWith({}, { sd_negotiated_prices: [{ id: 'all', blob: { 'SKU-9': 5 } }] },
        { readFails: true });
      const before = JSON.stringify(b.store);
      await b.ctx.sdHydrateAll();
      assert.strictEqual(JSON.stringify(b.store), before,
        'an unreadable local store adopted the server copy instead of leaving it alone');
    });

  // ══ 4. coverage: the twenty-second cannot be added without a verb ════════
  section('every synced collection can actually be deleted from');

  test('every SD_SYNCED key declares soft_delete in the registry', () => {
    delete require.cache[require.resolve(path.join(ROOT, 'api/_resources/index.js'))];
    const reg = require(path.join(ROOT, 'api/_resources/index.js'));
    const b = build({});
    const keys = b.ctx.SD_SYNCED;
    assert.ok(Array.isArray(keys) && keys.length >= 21, 'SD_SYNCED did not load: ' + keys);
    // Array.from, because `keys` comes from the vm realm and `.filter` returns
    // a vm-realm array whose prototype is not this realm's -- deepStrictEqual
    // fails on two EMPTY arrays across that boundary, which is a green-looking
    // failure with nothing wrong.
    const missing = Array.from(keys)
      .filter(k => (reg.EXTRA_ACTIONS[k] || []).indexOf('soft_delete') === -1);
    assert.deepStrictEqual(missing, [],
      'these synced collections have no soft_delete verb, so their delete buttons '
      + 'would silently do nothing on the server: ' + JSON.stringify(missing));
  });

  test('and every one of them is registered to stonedesk', () => {
    const reg = require(path.join(ROOT, 'api/_resources/index.js'));
    const b = build({});
    b.ctx.SD_SYNCED.forEach(k => {
      assert.strictEqual(reg.OWNER_BY_RESOURCE[k], 'stonedesk',
        k + ' is owned by ' + reg.OWNER_BY_RESOURCE[k] + ' -- the app boundary would refuse it');
    });
  });

  // ══ 5. clearing demo data must not reach the server ══════════════════════
  section('a bulk demo wipe is not a user deleting a record');

  test('sdClearSafeDemoData suppresses the sweep, and restores the flag', () => {
    const b = build({ store: { sd_comms: JSON.stringify(ROWS) } });
    const demo = [
      grabBlock('var SAFE_DEMO_KEYS=[', "'sd_it_tickets','sd_it_licenses'];"),
      grabAt('  function sdClearSafeDemoData(){', '  ')
    ].join('\n').replace(/^ {2}/gm, '');
    vm.runInContext('var stRaw=function(){};\n' + demo, b.ctx,
      { filename: 'stonedesk-demo-clear-extract.js' });
    b.ctx.sdClearSafeDemoData();
    assert.strictEqual(dels(b).length, 0,
      'clearing demo data soft-deleted server rows: ' + JSON.stringify(dels(b)));
    assert.strictEqual(b.ctx.sdSyncSuppressed, false,
      'the suppression flag was left ON -- every later save would be silently un-backed-up');
  });

  test('and a later ordinary delete still works after that clear', () => {
    const b = build({ store: { sd_comms: JSON.stringify(ROWS) } });
    const demo = [
      grabBlock('var SAFE_DEMO_KEYS=[', "'sd_it_tickets','sd_it_licenses'];"),
      grabAt('  function sdClearSafeDemoData(){', '  ')
    ].join('\n').replace(/^ {2}/gm, '');
    vm.runInContext('var stRaw=function(){};\n' + demo, b.ctx, { filename: 'x.js' });
    b.ctx.sdClearSafeDemoData();
    b.ctx.st('sd_invoices', ROWS);          // establish a prev through the real path
    save(b, 'sd_invoices', [ROWS[0]]);
    assert.deepStrictEqual(dels(b).map(c => c.payload.id).sort(), ['B', 'C']);
  });

  runAsync().then(() => {
    console.log('\n' + pass + ' passed, ' + fail + ' failed');
    if (fail) process.exit(1);
  });
})();
