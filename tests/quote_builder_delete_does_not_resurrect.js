// tests/quote_builder_delete_does_not_resurrect.js
//
// Run:  node tests/quote_builder_delete_does_not_resurrect.js
//
// DELETING A QUOTE BUILDER SAVE UNDID ITSELF ON THE NEXT SAVED QUOTE, and the
// user watched the delete succeed.
//
//   var quoteHistory = (function(){ ... })();     <- stonedesk.html, ONE read
//                                                    of localStorage at parse
//                                                    time. A module-level array.
//   sdQBDelete(id)      filtered the row out and wrote the SURVIVORS to
//                       localStorage through st(). It never touched
//                       quoteHistory.
//   sdQBRender()        re-reads storage through qbLoad(), so the row really
//                       did vanish from the panel. The delete looked complete.
//   saveQuote()         then does `quoteHistory.unshift(q)` followed by
//                       `st('stonedesk_quote_history', quoteHistory)` -- writing
//                       the STALE array, deleted row and all, back over the
//                       storage AND out to the server through sdSyncCollection.
//
// So every deleted Quote Builder save came back the next time anyone saved a
// quote. The confirm says "It is hidden and kept, not destroyed", which is a
// statement about the SERVER copy; it is not a warning that the local row
// returns.
//
// HOW IT WAS FOUND: tools/key_collision_check.py reported
// `stonedesk_quote_history -> ['d', 'next', 'quoteHistory']` -- three distinct
// backing variables for one key. Two of the three (`d`, `next`) are fresh
// reads and benign; `quoteHistory` is the one that is a CACHE. The same tool
// reported sd_drawings and sd_business_snapshots the same way and BOTH of those
// are benign for exactly the reason this one is not, which is why the
// acknowledgement table records the traced reason rather than the verdict.
//
// SECTION 1 REPRODUCES THE DEFECT before section 2 asserts the fix, because a
// resurrection test that has never seen a resurrection is asserting a property
// of its own fixture -- the same design as
// tests/customer_delete_does_not_resurrect.js, which this follows.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const HTML = fs.readFileSync(process.env.SD_HTML || path.join(ROOT, 'stonedesk.html'),
                             'utf8').replace(/\r\n/g, '\n');

let n = 0;
function ok(cond, label) { assert.ok(cond, label); n++; console.log('  ok   ' + label); }

// Brace-match a function out of the shipped file, skipping strings and comments.
function grab(sig) {
  const start = HTML.indexOf(sig);
  assert.ok(start > 0, 'not found in stonedesk.html: ' + sig);
  let i = HTML.indexOf('{', start + sig.length - 1), depth = 0, q = null;
  for (; i < HTML.length; i++) {
    const c = HTML[i], p = HTML[i - 1];
    if (q) { if (c === q && p !== '\\') q = null; continue; }
    if (c === '"' || c === "'" || c === '`') { q = c; continue; }
    if (c === '/' && HTML[i + 1] === '/') { i = HTML.indexOf('\n', i); continue; }
    if (c === '/' && HTML[i + 1] === '*') { i = HTML.indexOf('*/', i) + 1; continue; }
    if (c === '{') depth++;
    else if (c === '}') { depth--; if (!depth) return HTML.slice(start, i + 1); }
  }
  throw new Error('unterminated: ' + sig);
}

function grabLine(sig) {
  const i = HTML.indexOf(sig);
  assert.ok(i > 0, 'line not found in stonedesk.html: ' + sig);
  return HTML.slice(i, HTML.indexOf('\n', i));
}

const QB_LOAD = grab('function qbLoad(){');
const QB_DELETE = grab('window.sdQBDelete=function(id){');
// The saveQuote write step, taken VERBATIM from the shipped file rather than
// modelled: these two lines are the whole mechanism by which the stale array
// reaches storage, and re-typing them would test this file instead of that one.
const SAVE_UNSHIFT = grabLine('  quoteHistory.unshift(q);');
const SAVE_WRITE = grabLine("  if(!st('stonedesk_quote_history', quoteHistory)){");

// The pre-fix delete body: everything the shipped one does EXCEPT keeping the
// module-level array in step. Derived from the shipped source by removing the
// resync block, so it cannot drift away from what it is contrasting with.
function preFixDelete(shipped) {
  const out = shipped.replace(/\n\s*\/\/ THE MODULE-LEVEL ARRAY[\s\S]*?\n\s*}\n/, '\n');
  assert.ok(out !== shipped, 'the resync block was not found to remove -- has the fix changed shape?');
  return out;
}

function makeCtx(deleteBody) {
  const store = { stonedesk_quote_history: JSON.stringify([
    { id: 'QB-1', num: 'Q-1', client: 'A', date: '2026-09-01' },
    { id: 'QB-2', num: 'Q-2', client: 'B', date: '2026-09-02' }
  ]) };
  const ctx = {
    window: {},
    console: console,
    localStorage: {
      getItem: k => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); }
    },
    store: store,
    confirm: () => true,
    showToast: () => {},
    document: { getElementById: () => null },
    stFails: false,
    st: function (k, v) {
      if (ctx.stFails) return false;
      store[k] = JSON.stringify(v);
      return true;
    },
    // The real helper back-fills ids and reports whether it changed anything.
    sdEnsureRowIds: () => false
  };
  vm.createContext(ctx);
  // `window` IS the global object here, exactly as in a browser, and that is
  // not cosmetic. The fix reaches the cache through `window.quoteHistory`, and
  // the first version of this file ASSIGNED that property by hand -- which
  // would have passed whether or not a top-level `var` actually lands on
  // window. It does: stonedesk.html declares it with `var` at the top level of
  // a classic script block that is not IIFE-wrapped. Modelling it this way
  // DEMONSTRATES the scoping the fix depends on instead of assuming it.
  //
  // The two functions also live in DIFFERENT script blocks -- sdQBDelete in
  // block 11, the declaration in block 36 of 131 -- so the global is the only
  // thing connecting them, and the fix's Array.isArray guard is what covers
  // the window before block 36 has parsed.
  vm.runInContext('window = this;', ctx);
  vm.runInContext(QB_LOAD, ctx);
  vm.runInContext('window.sdQBRender=function(){};', ctx);
  vm.runInContext(deleteBody, ctx);
  // The module-level cache, read ONCE, exactly as stonedesk.html declares it --
  // and NOT hand-assigned onto window afterwards.
  vm.runInContext(
    "var quoteHistory = (function(){ try{ return JSON.parse(localStorage.getItem('stonedesk_quote_history')||'[]'); }catch(e){ return []; } })();",
    ctx);
  // saveQuote's write step, shipped text, wrapped so it can be driven.
  vm.runInContext('function driveSaveQuote(q){\n' + SAVE_UNSHIFT + '\n'
                  + SAVE_WRITE + '\n    quoteHistory.shift();\n    return false;\n  }\n'
                  + '  return true;\n}', ctx);
  return ctx;
}

const ids = ctx => JSON.parse(ctx.store.stonedesk_quote_history).map(r => r.id);

console.log('a deleted Quote Builder save does not come back\n');

// ── 1. THE DEFECT, REPRODUCED ────────────────────────────────────────────────
console.log('1. the pre-fix body RESURRECTS the deleted row');
{
  const ctx = makeCtx(preFixDelete(QB_DELETE));
  ctx.window.sdQBDelete('QB-1');
  ok(ids(ctx).join() === 'QB-2', 'the delete really did remove it from storage');
  ok(ctx.window.quoteHistory.map(r => r.id).join() === 'QB-1,QB-2',
     '...and the module-level array still holds it -- nothing updated the cache');
  ctx.driveSaveQuote({ id: 'QB-3', num: 'Q-3', client: 'C', date: '2026-09-03' });
  ok(ids(ctx).indexOf('QB-1') !== -1,
     'SO IT CAME BACK: the next saved quote wrote the stale array over storage');
}

// ── 2. THE SHIPPED BODY ──────────────────────────────────────────────────────
console.log('\n2. the shipped body does not');
{
  const ctx = makeCtx(QB_DELETE);
  ctx.window.sdQBDelete('QB-1');
  ok(ids(ctx).join() === 'QB-2', 'the delete removes it from storage');
  ok(ctx.window.quoteHistory.map(r => r.id).join() === 'QB-2',
     '...and the module-level array is brought into step');
  ctx.driveSaveQuote({ id: 'QB-3', num: 'Q-3', client: 'C', date: '2026-09-03' });
  ok(ids(ctx).indexOf('QB-1') === -1, 'and it STAYS deleted after the next save');
  ok(ids(ctx).sort().join() === 'QB-2,QB-3', 'while the new quote and the survivor are both there');
}

// ── 3. THE CONTROLS ──────────────────────────────────────────────────────────
console.log('\n3. controls -- the fix must not do anything else');
{
  // A FAILED WRITE MUST NOT CLEAR THE CACHE. Resyncing before knowing the write
  // landed would delete the row from memory while storage still holds it --
  // the same defect in the other direction, and a refresh would bring it back
  // while the user was told the delete failed.
  const ctx = makeCtx(QB_DELETE);
  ctx.stFails = true;
  ctx.window.sdQBDelete('QB-1');
  ok(ids(ctx).join() === 'QB-1,QB-2', 'a failed st() leaves storage untouched');
  ok(ctx.window.quoteHistory.map(r => r.id).join() === 'QB-1,QB-2',
     '...and leaves the module-level array untouched too');
}
{
  // Deleting an id that is not there must change nothing at all.
  const ctx = makeCtx(QB_DELETE);
  ctx.window.sdQBDelete('QB-NOPE');
  ok(ids(ctx).join() === 'QB-1,QB-2', 'an unmatched id writes nothing');
  ok(ctx.window.quoteHistory.map(r => r.id).join() === 'QB-1,QB-2',
     '...and touches nothing in memory');
}
{
  // The array must be mutated IN PLACE, not reassigned: saveQuote closes over
  // the original binding, and swapping the reference would leave it writing the
  // old one.
  const ctx = makeCtx(QB_DELETE);
  const before = ctx.window.quoteHistory;
  ctx.window.sdQBDelete('QB-1');
  ok(ctx.window.quoteHistory === before,
     'the same array object survives -- the fix mutates in place, it does not reassign');
}

console.log('\nALL ' + n + ' ASSERTIONS PASS');
