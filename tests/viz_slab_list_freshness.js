// tests/viz_slab_list_freshness.js
// REQUIREMENT: the photo-to-quote visualizer's slab picker must not list a
//   slab another device has already reserved, and when it cannot confirm that,
//   it must SAY SO rather than render a cached list as though it were current.
//
// Run:  node tests/viz_slab_list_freshness.js
//
// This one DRIVES the code rather than reading its shape. The two functions
// involved -- slabSyncFromSupabase() and vizRenderSlabList() -- are extractable
// (unlike the three reservation call sites covered by tests/slab_reserve_client.js,
// which live inside DOM handlers hundreds of lines long); they touch one element
// id and four helpers, all stubbable. So the property under test is the real one:
// given a server that says a slab is reserved, does the picker stop offering it.
//
// WHY A STALE LIST COSTS ANYTHING, given the server already refuses a double
// sale with a 409: the visualizer spends a METERED render. A rep picks a slab
// another device reserved an hour ago, burns a render showing the customer
// their kitchen in that stone, and only learns at "Quote This". The money is
// safe; the render and the conversation are not.
//
// THE THIRD AND FOURTH CASES ARE THE POINT. A refresh that fails and a server
// that returns nothing are BOTH "I could not confirm this list" -- a third
// state, not a pass. Before this fix `catch(e){}` folded them into the same
// silent success as a real sync, which is exactly the shape PR 1.11 names.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'stonedesk.html'), 'utf8');

let pass = 0, fail = 0;
const pending = [];
function test(name, fn) { pending.push([name, fn]); }
function section(t) { pending.push(['__section__', t]); }

// --- extract the two functions verbatim from the page --------------------

function extract(startAnchor, endAnchor, label) {
  const i = html.indexOf(startAnchor);
  assert.notStrictEqual(i, -1, 'could not find ' + label + ' -- anchor moved');
  assert.strictEqual(html.indexOf(startAnchor, i + 1), -1,
    label + ' anchor is not unique; the extraction would be reading the wrong copy');
  const j = html.indexOf(endAnchor, i);
  assert.notStrictEqual(j, -1, 'could not find the end of ' + label);
  return html.slice(i, j + endAnchor.length);
}

const syncSrc = extract(
  'async function slabSyncFromSupabase(){',
  "}catch(e){ return {ok:false, reason:'the server could not be reached'}; }\n}",
  'slabSyncFromSupabase');

const renderSrc = extract(
  '  window.vizRenderSlabList = async function(){',
  "    }).join('');\n  };",
  'vizRenderSlabList');

// --- the harness ---------------------------------------------------------
// Everything the two functions reach for, and nothing else. If either grows a
// new dependency this throws by name instead of silently reading undefined.

function harness(opts) {
  const written = { html: null };
  const saved = [];
  const ctx = {
    console,
    sdSlabs: JSON.parse(JSON.stringify(opts.localSlabs)),
    sdData: opts.sdData,
    slabLicKey: function () { return opts.licence === undefined ? 'LIC-1' : opts.licence; },
    saveSlabs: function () { saved.push(1); },
    escHtml: function (s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); },
    escAttrJs: function (s) { return String(s == null ? '' : s).replace(/'/g, "\\'"); },
    slabMaterialLabel: function (m) { return String(m || ''); },
    document: {
      getElementById: function (id) {
        assert.strictEqual(id, 'viz-slab-list', 'the picker reached for an unexpected element: ' + id);
        return { set innerHTML(v) { written.html = v; }, get innerHTML() { return written.html; } };
      }
    }
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  // sdData must exist as a *function* for the transport guard; when a case
  // wants "no transport" it passes undefined and the guard is what we're testing.
  vm.runInContext(syncSrc + '\n' + renderSrc + '\n', ctx);
  return { ctx, written, saved };
}

const STALE_MARK = 'Reservations may be out of date';

function slab(id, status) {
  return { id: id, status: status, colorName: 'Slab ' + id, material: 'granite', usableSqft: 40 };
}

// -------------------------------------------------------------------------
section('the list reflects the SERVER, not the session cache');

test('a slab the server says is reserved is no longer offered', async () => {
  const h = harness({
    localSlabs: [slab('s1', 'in-stock'), slab('s2', 'in-stock')],
    sdData: async function () { return [slab('s1', 'reserved'), slab('s2', 'in-stock')]; }
  });
  await h.ctx.vizRenderSlabList();
  assert.ok(!/data-id="s1"/.test(h.written.html),
    's1 was reserved server-side and the picker still listed it');
  assert.ok(/data-id="s2"/.test(h.written.html), 's2 is free and should still be listed');
  assert.ok(h.written.html.indexOf(STALE_MARK) === -1,
    'the refresh succeeded, so there must be no stale warning');
  assert.strictEqual(h.saved.length, 1, 'a successful merge must persist to localStorage');
});

test('and the reverse: a slab the server has RELEASED comes back', async () => {
  // Guards against a fix that only ever subtracts. The server is the authority
  // in both directions or it is not the authority.
  const h = harness({
    localSlabs: [slab('s1', 'reserved')],
    sdData: async function () { return [slab('s1', 'in-stock')]; }
  });
  await h.ctx.vizRenderSlabList();
  assert.ok(/data-id="s1"/.test(h.written.html),
    's1 was released server-side and the picker still hid it');
});

// -------------------------------------------------------------------------
section('an unconfirmed list is labelled, not passed off as current');

test('when the server cannot be reached the list still renders AND warns', async () => {
  const h = harness({
    localSlabs: [slab('s1', 'in-stock')],
    sdData: async function () { throw new Error('offline'); }
  });
  await h.ctx.vizRenderSlabList();
  assert.ok(/data-id="s1"/.test(h.written.html),
    'a rep offline in a yard must still get a list');
  assert.ok(h.written.html.indexOf(STALE_MARK) !== -1,
    'the refresh failed and nothing said so -- this is the silent-success shape');
  assert.strictEqual(h.saved.length, 0, 'a failed sync must not write to localStorage');
});

test('an empty server response is reported, not treated as a confirmed sync', async () => {
  // The distinction that `catch(e){}` destroyed: "the server has no slabs" is a
  // real answer but it is NOT a merge, so the cache it left alone is still
  // unconfirmed and must not be presented as current.
  const h = harness({
    localSlabs: [slab('s1', 'in-stock')],
    sdData: async function () { return []; }
  });
  await h.ctx.vizRenderSlabList();
  assert.ok(h.written.html.indexOf(STALE_MARK) !== -1,
    'an empty response left the cache unconfirmed and the list did not say so');
  assert.ok(/data-id="s1"/.test(h.written.html), 'the cached list is still shown');
});

test('signed out is reported too -- there is no licence to sync against', async () => {
  const h = harness({
    localSlabs: [slab('s1', 'in-stock')],
    licence: '',
    sdData: async function () { throw new Error('should not be called'); }
  });
  await h.ctx.vizRenderSlabList();
  assert.ok(h.written.html.indexOf(STALE_MARK) !== -1,
    'no licence means the list was never confirmed and must say so');
});

test('the warning survives the empty-inventory branch', async () => {
  // Both render paths carry it or only one of them is honest.
  const h = harness({
    localSlabs: [],
    sdData: async function () { throw new Error('offline'); }
  });
  await h.ctx.vizRenderSlabList();
  assert.ok(h.written.html.indexOf(STALE_MARK) !== -1,
    'the no-slabs branch dropped the stale warning');
  assert.ok(/No in-stock slabs found/.test(h.written.html),
    'the no-slabs message itself is missing');
});

// -------------------------------------------------------------------------
section('the control: this test can actually fail');

test('the old sync body -- catch(e){} returning undefined -- is refused', async () => {
  // A criteria lock. If slabSyncFromSupabase ever regresses to swallowing the
  // error and returning nothing, `fresh.ok` is undefined, the note renders, and
  // the first two cases above go red. This asserts the harness would notice by
  // running the PRE-FIX body against the SAME picker.
  const ctxSrc = renderSrc.replace(
    'window.vizRenderSlabList',
    'var _unused; window.vizRenderSlabList');
  const oldSync = "async function slabSyncFromSupabase(){ try { await sdData(); } catch(e){} }";
  const ctx = {
    console, sdSlabs: [slab('s1', 'in-stock')],
    sdData: async function () { return [slab('s1', 'reserved')]; },
    escHtml: function (s) { return String(s == null ? '' : s); },
    escAttrJs: function (s) { return String(s == null ? '' : s); },
    slabMaterialLabel: function (m) { return String(m || ''); },
    document: { getElementById: function () { return { innerHTML: null }; } }
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(oldSync + '\n' + ctxSrc + '\n', ctx);
  let out = null;
  ctx.document.getElementById = function () { return { set innerHTML(v) { out = v; } }; };
  await ctx.vizRenderSlabList();
  assert.ok(out.indexOf(STALE_MARK) !== -1,
    'the pre-fix sync returns undefined, so the picker MUST fall through to the '
    + 'warning -- if it did not, the freshness cases above would pass on a broken sync');
});

// -------------------------------------------------------------------------
(async function run() {
  for (const [name, fn] of pending) {
    if (name === '__section__') { console.log('--- ' + fn + ' ---'); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
  }
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
