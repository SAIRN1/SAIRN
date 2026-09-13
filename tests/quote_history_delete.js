// tests/quote_history_delete.js
//
// Run:  node tests/quote_history_delete.js
//
// The Quote History panel could View a quote and change its status, and could
// never remove one. A test quote, a duplicate, or one entered against the wrong
// customer stayed in Total Quotes, Total Value, Win Rate and Average for ever --
// and those four KPIs are what a shop reads its own pipeline off.
//
// ── THE TRAP THIS PANEL SETS, AND WHY IT NEEDED ITS OWN SAVE PATH ──────────
// load() MERGES two stores: sd_quote_history and sd_aiquotes, tagging the
// second `_src:'ai'`. save() routes each row back to the store it came from --
// correct, and fixed on 2026-09-04 after every status change had been copying
// every AI quote into the history store.
//
// But save() carries a guard: `ai.length ? st('sd_aiquotes',ai) : true`, so an
// EMPTY ai array leaves that store untouched. That is right for a status change
// and WRONG FOR A DELETION. Removing the only AI quote yields an empty `ai`,
// sd_aiquotes is never written, and load() concatenates the deleted quote
// straight back on the next call -- a deletion that undoes itself, which is the
// exact defect class this app spent 2026-09-12 and 13 removing from
// sd_customers and twenty-one other collections.
//
// So section 2 is mostly that one case, and it is the reason saveAfterDelete()
// exists as its own function rather than the delete calling save().

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

function balanced(start) {
  let i = html.indexOf('{', start), depth = 0;
  for (; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}') { depth--; if (!depth) return html.slice(start, i + 1); }
  }
  throw new Error('unbalanced from ' + start);
}
// Anchored after this module's own two-store save(), which is unique in the
// file. `function load(){` and `function save(d){` each appear in many IIFEs.
const AT = html.indexOf("    var okAi=ai.length?st('sd_aiquotes',ai):true;");
assert.ok(AT > 0, 'the two-store save() moved or changed');
function fnAfter(decl) {
  const i = html.indexOf(decl, AT);
  assert.ok(i > AT, 'not found after the anchor: ' + decl);
  return balanced(i);
}
function fnBefore(decl) {
  const i = html.lastIndexOf(decl, AT);
  assert.ok(i > 0 && i < AT, 'not found before the anchor: ' + decl);
  return balanced(i);
}

const HIST = [
  { id: 1, customer: 'Marcus Webb', project: 'Kitchen', amount: 4850, status: 'Approved', date: '2026-05-12' },
  { id: 2, customer: 'Sarah Johnson', project: 'Vanity', amount: 2100, status: 'Pending', date: '2026-05-10' }
];
const AI = [
  { id: 900, customer: 'AI Quote', project: 'Island', amount: 3000, status: 'Pending', date: '2026-05-09' }
];

function build(hist, ai, opts) {
  opts = opts || {};
  const store = {
    sd_quote_history: JSON.stringify(hist),
    sd_aiquotes: JSON.stringify(ai)
  };
  const out = { toasts: [], confirms: [], rendered: 0, writes: [] };
  const ctx = {};
  const src =
    fnBefore('  function load(){') + '\n' +
    fnBefore('  function save(d){') + '\n' +
    fnAfter('  function saveAfterDelete(d,removedWasAI){') + '\n' +
    fnAfter('  window.sdHistoryDelete=function(id){') + '\n' +
    'ctx.load=load; ctx.save=save; ctx.saveAfterDelete=saveAfterDelete;'
    + 'ctx.del=window.sdHistoryDelete;';
  new Function('localStorage', 'st', 'sdDemoCleared', 'showToast', 'confirm', 'window', 'ctx', src)(
    { getItem: k => (k in store ? store[k] : null) },
    (k, v) => {
      out.writes.push(k);
      if (opts.saveFails) return false;
      store[k] = JSON.stringify(v);
      return true;
    },
    () => true,                        // demo cleared, so SEED never substitutes
    m => out.toasts.push(String(m)),
    m => { out.confirms.push(String(m)); return opts.confirm !== false; },
    { sdHistoryRender: () => { out.rendered++; } },
    ctx
  );
  return { ctx, out, store };
}

(function main() {
  console.log('StoneDesk quote history -- a quote can finally be removed\n');

  section('an ordinary history row');

  test('deleting removes it from the history store', () => {
    const b = build(HIST, AI);
    b.ctx.del(1);
    assert.deepStrictEqual(JSON.parse(b.store.sd_quote_history).map(x => x.id), [2]);
  });

  test('and the merged view no longer carries it', () => {
    const b = build(HIST, AI);
    b.ctx.del(1);
    assert.deepStrictEqual(b.ctx.load().map(x => x.id).sort(), [2, 900]);
  });

  test('the AI store is untouched when no AI row was removed', () => {
    const b = build(HIST, AI);
    b.ctx.del(1);
    assert.deepStrictEqual(JSON.parse(b.store.sd_aiquotes).map(x => x.id), [900]);
  });

  test('and it re-renders, so the KPIs above stop counting it', () => {
    const b = build(HIST, AI);
    b.ctx.del(1);
    assert.ok(b.out.rendered >= 1);
  });

  // ══ THE ARM THIS FILE EXISTS FOR ════════════════════════════════════════
  section('the last AI quote -- the case save() gets right for edits and wrong for deletes');

  test('deleting the ONLY AI quote really removes it', () => {
    const b = build(HIST, AI);
    b.ctx.del(900);
    assert.deepStrictEqual(JSON.parse(b.store.sd_aiquotes), [],
      'sd_aiquotes was never written, so the quote is still on disk');
  });

  test('and it does not come back on the next load', () => {
    const b = build(HIST, AI);
    b.ctx.del(900);
    assert.deepStrictEqual(b.ctx.load().map(x => x.id).sort(), [1, 2],
      'the deleted AI quote reappeared -- a deletion that undoes itself');
  });

  // THE CONTROL. Without it the arm above could pass because sd_aiquotes is
  // written on EVERY save, which would reintroduce the 2026-09-04 bug where a
  // status change erased that store from a state holding nothing.
  test('but an ordinary save with no AI rows still leaves the store alone', () => {
    const b = build(HIST, AI);
    b.out.writes.length = 0;
    b.ctx.save(HIST);                   // no _src:'ai' rows in this array
    assert.ok(b.out.writes.indexOf('sd_aiquotes') === -1,
      'save() now writes sd_aiquotes unconditionally -- that is the older bug, back');
  });

  test('saveAfterDelete writes sd_aiquotes only when told the removed row was AI', () => {
    const b = build(HIST, AI);
    b.out.writes.length = 0;
    b.ctx.saveAfterDelete(HIST, false);
    assert.ok(b.out.writes.indexOf('sd_aiquotes') === -1);
    b.out.writes.length = 0;
    b.ctx.saveAfterDelete(HIST, true);
    assert.ok(b.out.writes.indexOf('sd_aiquotes') !== -1);
  });

  test('the _src tag never persists into either store', () => {
    const b = build(HIST, AI);
    b.ctx.del(1);
    JSON.parse(b.store.sd_quote_history).concat(JSON.parse(b.store.sd_aiquotes))
      .forEach(x => assert.ok(!('_src' in x), 'the merge tag was written to disk'));
  });

  section('the ordinary refusals');

  test('the confirm says kept, and never "cannot be undone"', () => {
    const b = build(HIST, AI, { confirm: false });
    b.ctx.del(1);
    const m = b.out.confirms[0] || '';
    assert.ok(/hidden and kept, not destroyed/.test(m), m);
    assert.ok(!/cannot be undone/i.test(m));
  });

  test('declining writes nothing', () => {
    const b = build(HIST, AI, { confirm: false });
    b.out.writes.length = 0;
    b.ctx.del(1);
    assert.strictEqual(b.out.writes.length, 0);
  });

  test('an id matching nothing writes nothing and never asks', () => {
    const b = build(HIST, AI);
    b.out.writes.length = 0;
    b.ctx.del(12345);
    assert.strictEqual(b.out.writes.length, 0);
    assert.strictEqual(b.out.confirms.length, 0,
      'it asked the user before checking the row exists');
  });

  test('an empty id is refused outright', () => {
    const b = build(HIST, AI);
    b.ctx.del('');
    assert.strictEqual(b.out.confirms.length, 0);
    assert.strictEqual(b.out.writes.length, 0);
  });

  test('a storage failure is reported, with no success toast', () => {
    const b = build(HIST, AI, { saveFails: true });
    b.ctx.del(1);
    assert.ok(/Could not delete that quote/.test(b.out.toasts.join('|')), JSON.stringify(b.out.toasts));
    assert.ok(!/Quote deleted/.test(b.out.toasts.join('|')));
  });

  section('the panel offers it');

  test('every row gets a Delete beside its View', () => {
    const render = fnAfter('  window.sdHistoryRender=function(){');
    assert.ok(/onclick="sdHistoryView\(/.test(render), 'View is gone');
    assert.ok(/onclick="sdHistoryDelete\(/.test(render), 'no Delete button in the history table');
  });

  // ══ THE OTHER QUOTE STORE ════════════════════════════════════════════════
  // THIS APP HAS TWO "SAVE A QUOTE" BUTTONS WRITING TWO DIFFERENT STORES.
  // "Save to History" (sdQuoteSaveHistory) writes sd_quote_history and shows in
  // the table above. "Save Quote" (saveQuote) writes stonedesk_quote_history
  // and was rendered ONLY by renderHistory(), which targets #history-list -- an
  // element this file's own comment records as never built. A shop pressing
  // Save Quote got a confirmation and the quote appeared nowhere.
  //
  // LISTED, NOT MERGED, and that is the decision the arms below pin. Folding
  // these into the table above would put them into Total Quotes, Total Value
  // and Win Rate -- silently changing four money figures every existing shop
  // already reads. Which store should be canonical is a product decision.
  section('the Quote Builder store is visible, and stays out of the KPIs');

  function qb(rows, opts) {
    opts = opts || {};
    const store = { stonedesk_quote_history: JSON.stringify(rows) };
    const out = { toasts: [], confirms: [], writes: [], els: { 'sd-qb-saves': { innerHTML: '' } } };
    const ctx = {};
    const src =
      balanced(html.indexOf('function sdRowId(prefix,row,fields){')) + '\n' +
      balanced(html.indexOf('function sdEnsureRowIds(rows,prefix,fields){')) + '\n' +
      fnAfter('  function qbLoad(){') + '\n' +
      fnAfter('  window.sdQBRender=function(){') + '\n' +
      fnAfter('  window.sdQBDelete=function(id){') + '\n' +
      'ctx.qbLoad=qbLoad; ctx.render=window.sdQBRender; ctx.del=window.sdQBDelete;';
    new Function('localStorage', 'st', 'document', 'escHtml', 'escAttrJs',
                 'showToast', 'confirm', 'window', 'ctx', src)(
      { getItem: k => (k in store ? store[k] : null) },
      (k, v) => { out.writes.push(k); if (opts.saveFails) return false; store[k] = JSON.stringify(v); return true; },
      { getElementById: id => out.els[id] || null },
      s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'),
      s => String(s),
      m => out.toasts.push(String(m)),
      m => { out.confirms.push(String(m)); return opts.confirm !== false; },
      {}, ctx
    );
    return { ctx, out, store };
  }
  const QB = [
    { num: 'Q-101', client: 'Marcus Webb', project: 'Kitchen', total: 4850, date: '2026-09-10' },
    { num: 'Q-102', client: 'Sarah Johnson', project: 'Vanity', total: 2100, date: '2026-09-11' }
  ];

  test('the Quote Builder saves are listed at all -- they never were', () => {
    const b = qb(QB);
    b.ctx.render();
    const h = b.out.els['sd-qb-saves'].innerHTML;
    assert.ok(h.indexOf('Marcus Webb') !== -1, 'still invisible: ' + h.slice(0, 160));
    assert.strictEqual((h.match(/onclick="sdQBDelete\(/g) || []).length, 2);
  });

  test('their rows get ids, so they are syncable as well as deletable', () => {
    const b = qb(QB);
    b.ctx.qbLoad().forEach(x => assert.ok(String(x.id || '').startsWith('QB-'), String(x.id)));
  });

  test('an empty store says so rather than rendering nothing', () => {
    const b = qb([]);
    b.ctx.render();
    assert.ok(/No Quote Builder saves yet/.test(b.out.els['sd-qb-saves'].innerHTML));
  });

  test('a client name containing markup is escaped', () => {
    const b = qb([Object.assign({}, QB[0], { client: '<img src=x onerror=1>' })]);
    b.ctx.render();
    const h = b.out.els['sd-qb-saves'].innerHTML;
    assert.ok(h.indexOf('<img src=x') === -1 && h.indexOf('&lt;img') !== -1);
  });

  test('deleting one writes the survivors back to ITS OWN store', () => {
    const b = qb(QB);
    const id = b.ctx.qbLoad()[0].id;
    b.ctx.del(id);
    assert.deepStrictEqual(JSON.parse(b.store.stonedesk_quote_history).map(x => x.num), ['Q-102']);
  });

  test('and never touches sd_quote_history', () => {
    const b = qb(QB);
    b.ctx.del(b.ctx.qbLoad()[0].id);
    assert.ok(b.out.writes.indexOf('sd_quote_history') === -1,
      'the Quote Builder delete reached into the other store');
  });

  test('an id matching nothing never asks and never writes', () => {
    const b = qb(QB);
    b.ctx.qbLoad();
    b.out.writes.length = 0;
    b.ctx.del('QB-NO-SUCH');
    assert.strictEqual(b.out.confirms.length, 0);
    assert.strictEqual(b.out.writes.length, 0);
  });

  test('a storage failure is reported, with no success toast', () => {
    const b = qb(QB, { saveFails: true });
    const id = b.ctx.qbLoad()[0].id;
    b.out.toasts.length = 0;
    b.ctx.del(id);
    assert.ok(/Could not delete that quote/.test(b.out.toasts.join('|')), JSON.stringify(b.out.toasts));
    assert.ok(!/save deleted/.test(b.out.toasts.join('|')));
  });

  // THE SEPARATION IS THE POINT. If these ever reach load(), the four KPIs
  // above change for every existing shop without anyone deciding that.
  test('the merged history loader still reads TWO stores, not three', () => {
    const loader = fnBefore('  function load(){');
    assert.ok(/sd_quote_history/.test(loader) && /sd_aiquotes/.test(loader));
    assert.ok(!/stonedesk_quote_history/.test(loader),
      'the Quote Builder store was folded into the KPI table -- that moves Total '
      + 'Value and Win Rate for every existing shop and is a product decision');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  if (fail) process.exit(1);
})();
