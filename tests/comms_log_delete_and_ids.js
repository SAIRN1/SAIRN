// tests/comms_log_delete_and_ids.js
//
// Run:  node tests/comms_log_delete_and_ids.js
//
// THE COMMUNICATION LOG HAD NEVER BEEN BACKED UP, AND NOT FOR THE REASON
// ANYONE WOULD HAVE GUESSED. `sd_comms` is in SD_SYNCED, which reads as "this
// is backed up". But sdSyncCollection() skips any row without an `id` --
// `if(!r||r.id===undefined||r.id===null||r.id==='') return;` -- and
// sdCommsNew() never set one. Every message a shop logged lived in one browser
// and died with its cache.
//
// Same shape as sd_negotiated_prices and sd_pricing_rules, found the same day:
// a collection listed as synced, skipped by a guard nobody connected to it,
// with nothing anywhere saying so.
//
// THE ID IS DERIVED FROM THE CONTENT, and that is the load-bearing choice
// rather than a stylistic one. A random id assigned at back-fill time would be
// a DIFFERENT id on every device, so the same message would sync as one row per
// browser that ever opened the panel -- and deleting it on one device could not
// delete it on the other. Section 1 is mostly about that.
//
// AND commsDelete() IS NOT THE COMMS DELETE. It belongs to the dormant
// threaded-comms system, has no callers and no markup, and even if called
// would persist nothing because saveSD5() deliberately stopped writing
// sd_comms. Section 4 pins that it stays labelled, because a dormant function
// with a plausible name is exactly what sends the next reader down the wrong
// path.

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
function fn(decl) {
  const i = html.indexOf(decl);
  assert.ok(i > 0, 'not found in stonedesk.html: ' + decl);
  return balanced(i);
}

const SEED_LIKE = [
  { type: 'Email to Customer', to: 'Marcus Webb', subj: 'Thank you', body: 'b1', date: '2024-06-14 10:30', sent: true },
  { type: 'Internal Note', to: 'Shop Team', subj: 'Park job', body: 'b2', date: '2024-06-13 15:00', sent: true }
];

// The real functions, in a realm holding only what they touch.
function build(rows, opts) {
  opts = opts || {};
  const store = { sd_comms: rows === null ? null : JSON.stringify(rows) };
  const out = { saved: [], toasts: [], confirms: [], rendered: 0 };
  const ctx = {};
  // load() and save() come from the file too. There are many `function load()`
  // in a 2.5MB single-file app, so these are taken by their FULL unique text
  // rather than by a bare name -- grabbing the wrong module's loader would give
  // a suite that runs happily against a store these functions never touch.
  const LOAD = "function load(){try{return JSON.parse(localStorage.getItem('sd_comms')"
    + "||'null')||(sdDemoCleared()?[]:SEED);}catch(e){return sdDemoCleared()?[]:SEED;}}";
  const SAVE = "function save(d){return st('sd_comms',d);}";
  assert.strictEqual(html.split(LOAD).length - 1, 1, 'the comms load() moved or changed');
  assert.strictEqual(html.split(SAVE).length - 1, 1, 'the comms save() moved or changed');
  const src =
    LOAD + '\n' + SAVE + '\n' +
    fn('  function commsId(x){') + '\n' +
    fn('  function commsEnsureIds(){') + '\n' +
    fn('  window.sdCommsDelete=function(id){') + '\n' +
    'ctx.commsId=commsId; ctx.commsEnsureIds=commsEnsureIds; ctx.sdCommsDelete=window.sdCommsDelete;';
  new Function('localStorage', 'st', 'sdDemoCleared', 'SEED', 'showToast', 'confirm',
               'window', 'ctx', 'commsUpdateKPIs', src)(
    { getItem: k => (k in store ? store[k] : null) },
    (k, v) => { if (opts.saveFails) return false; out.saved.push(v); store[k] = JSON.stringify(v); return true; },
    () => true,                       // demo cleared: SEED never substitutes
    [],
    m => out.toasts.push(String(m)),
    m => { out.confirms.push(String(m)); return opts.confirm !== false; },
    { sdCommsRender: () => { out.rendered++; } },
    ctx,
    () => {}
  );
  return { ctx, out, store };
}

(function main() {
  console.log('StoneDesk comms log -- ids that make it syncable, and a delete\n');

  // ══ 1. the id ════════════════════════════════════════════════════════════
  section('the id is derived from the message, so two devices agree');

  test('the same message yields the same id on any device', () => {
    const a = build(SEED_LIKE), b = build(SEED_LIKE);
    const ida = a.ctx.commsEnsureIds().map(x => x.id);
    const idb = b.ctx.commsEnsureIds().map(x => x.id);
    assert.deepStrictEqual(ida, idb);
    assert.ok(ida[0].startsWith('CM-'), ida[0]);
  });

  // THE ARM THAT MATTERS. A random back-fill id would pass every other arm in
  // this file and still produce one server row per browser.
  test('and a DIFFERENT message does not collide with it', () => {
    const b = build(SEED_LIKE);
    const ids = b.ctx.commsEnsureIds().map(x => x.id);
    assert.strictEqual(new Set(ids).size, 2);
  });

  test('two identical messages in the same minute both survive, suffixed', () => {
    const dupe = [SEED_LIKE[0], Object.assign({}, SEED_LIKE[0])];
    const b = build(dupe);
    const ids = b.ctx.commsEnsureIds().map(x => x.id);
    assert.strictEqual(new Set(ids).size, 2, 'one of two real log entries was merged away');
    assert.ok(ids[1].endsWith('-2'), ids[1]);
  });

  test('back-filling writes once and is then idempotent', () => {
    const b = build(SEED_LIKE);
    b.ctx.commsEnsureIds();
    assert.strictEqual(b.out.saved.length, 1, 'the back-fill did not persist');
    b.ctx.commsEnsureIds();
    assert.strictEqual(b.out.saved.length, 1, 'it rewrote the store on a second pass');
  });

  test('a row that already has an id keeps it', () => {
    const b = build([Object.assign({ id: 'CM-EXISTING' }, SEED_LIKE[0])]);
    assert.strictEqual(b.ctx.commsEnsureIds()[0].id, 'CM-EXISTING');
    assert.strictEqual(b.out.saved.length, 0, 'nothing needed changing, but it wrote anyway');
  });

  test('every row ends up with a non-empty id -- the thing the sync skips on', () => {
    const b = build(SEED_LIKE.concat([{ type: 'x', to: '', subj: '', body: '', date: '' }]));
    b.ctx.commsEnsureIds().forEach(x => {
      assert.ok(x.id !== undefined && x.id !== null && x.id !== '',
        'sdSyncCollection() skips this row, so it is still not backed up');
    });
  });

  // ══ 2. delete ════════════════════════════════════════════════════════════
  section('a log entry can be removed, and the removal leaves the device');

  test('deleting writes the survivors back', () => {
    const b = build(SEED_LIKE);
    const id = b.ctx.commsEnsureIds()[0].id;
    b.out.saved.length = 0;
    b.ctx.sdCommsDelete(id);
    assert.strictEqual(b.out.saved.length, 1);
    assert.strictEqual(b.out.saved[0].length, 1);
    assert.strictEqual(b.out.saved[0][0].subj, 'Park job');
  });

  test('and re-renders, so the row leaves the screen', () => {
    const b = build(SEED_LIKE);
    const id = b.ctx.commsEnsureIds()[0].id;
    b.ctx.sdCommsDelete(id);
    assert.ok(b.out.rendered >= 1);
  });

  test('the confirm says the record is KEPT, and never "cannot be undone"', () => {
    const b = build(SEED_LIKE, { confirm: false });
    b.ctx.sdCommsDelete(b.ctx.commsEnsureIds()[0].id);
    const m = b.out.confirms[0] || '';
    assert.ok(/hidden and kept, not destroyed/.test(m), m);
    assert.ok(!/cannot be undone/i.test(m), 'the confirm claims an irreversible delete');
  });

  test('declining the confirm writes nothing', () => {
    const b = build(SEED_LIKE, { confirm: false });
    const id = b.ctx.commsEnsureIds()[0].id;
    b.out.saved.length = 0;
    b.ctx.sdCommsDelete(id);
    assert.strictEqual(b.out.saved.length, 0);
  });

  test('an id matching nothing writes nothing and says nothing', () => {
    const b = build(SEED_LIKE);
    b.ctx.commsEnsureIds();
    b.out.saved.length = 0; b.out.toasts.length = 0;
    b.ctx.sdCommsDelete('CM-NO-SUCH');
    assert.strictEqual(b.out.saved.length, 0);
    assert.strictEqual(b.out.toasts.length, 0);
  });

  test('an empty id is refused with a sentence, not silently', () => {
    const b = build(SEED_LIKE);
    b.ctx.sdCommsDelete('');
    assert.ok(/no id yet/.test(b.out.toasts[0] || ''), JSON.stringify(b.out.toasts));
    assert.strictEqual(b.out.confirms.length, 0, 'it asked before noticing it could not act');
  });

  // A FAILED LOCAL WRITE MUST NOT LOOK LIKE A DELETION: st() returns false when
  // storage refuses, and reporting success would take the row off the screen
  // while leaving it on disk until the next render put it back.
  test('a storage failure is reported, and no success toast is shown', () => {
    const b = build(SEED_LIKE, { saveFails: true });
    // ensureIds cannot persist either, but the ids are still assigned in memory
    const id = b.ctx.commsEnsureIds()[0].id;
    b.out.toasts.length = 0;
    b.ctx.sdCommsDelete(id);
    assert.ok(/Could not delete that entry/.test(b.out.toasts.join('|')), JSON.stringify(b.out.toasts));
    assert.ok(!/Log entry deleted/.test(b.out.toasts.join('|')));
  });

  // ══ 3. the panel offers it ═══════════════════════════════════════════════
  section('the button exists, on the real renderer');

  test('sdCommsRender draws a Delete per row', () => {
    const render = fn('  window.sdCommsRender=function(){');
    assert.ok(/onclick="sdCommsDelete\(/.test(render), 'no Delete button in the comms log');
  });

  test('and it back-fills ids before drawing, so every row has one to pass', () => {
    const render = fn('  window.sdCommsRender=function(){');
    assert.ok(/var d=commsEnsureIds\(\);/.test(render),
      'the renderer still calls load() directly, so idless rows would render a dead button');
  });

  test('sdCommsNew sets an id on the way in, not only on a later pass', () => {
    const add = fn('  window.sdCommsNew=function(){');
    assert.ok(/rec\.id=commsId\(rec\);/.test(add));
  });

  // ══ 4. the dormant one stays labelled ════════════════════════════════════
  section('commsDelete() is NOT this -- and says so');

  // COUNTED ON COMMENT-STRIPPED SOURCE, and the claim was corrected twice.
  // The first version counted every `commsDelete(` in the raw file and got 3 --
  // its definition plus two COMMENTS naming it, one of them the dormant label
  // added in the same change. That is the comment-quoting trap this repo has a
  // checker for, and here it failed a correct file.
  //
  // THE SECOND VERSION WAS WRONG ABOUT THE PRODUCT, NOT ABOUT COMMENTS. It
  // asserted "no caller and no markup anywhere" and there IS markup -- a
  // Delete button inside renderCommsThreads(). The accurate statement, and the
  // one worth pinning, is that its ONLY caller lives inside that dormant
  // renderer, which has no container and is dispatched by nothing. Asserting a
  // tidier claim than the code supports would have meant weakening the code or
  // lying in the test.
  //
  // (Declared: the label arm below DOES read comments, on purpose.)
  test('commsDelete is called only from the dormant threaded renderer', () => {
    const code = html.split('\n').map(l => l.replace(/^\s*\/\/.*$/, '')).join('\n');
    const uses = (code.match(/commsDelete\s*\(/g) || []).length;
    assert.strictEqual(uses, 2, 'commsDelete gained or lost a caller -- it persists nothing');
    const render = fn('function renderCommsThreads() {');
    assert.ok(/onclick="commsDelete\(/.test(render),
      'the one caller is no longer inside renderCommsThreads -- it may now be reachable');
  });

  test('and that renderer is reached by nothing: no container, no dispatch', () => {
    const code = html.split('\n').map(l => l.replace(/^\s*\/\/.*$/, '')).join('\n');
    // Its own definition is the only mention. A nav dispatch or any other call
    // would be a second.
    assert.strictEqual((code.match(/renderCommsThreads\s*\(/g) || []).length, 1,
      'renderCommsThreads is now called from somewhere -- the dormant label is stale');
  });

  test('and it carries a label saying it is dormant and why', () => {
    const i = html.indexOf('function commsDelete(id) {');
    const before = html.slice(Math.max(0, i - 1400), i);
    assert.ok(/DORMANT/.test(before), 'the dormant label is gone');
    assert.ok(/sdCommsDelete\(\)/.test(before),
      'the label does not point at the reachable one, so a reader still lands here');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  if (fail) process.exit(1);
})();
