// tests/ai_analysis_logs_delete.js
//
// Run:  node tests/ai_analysis_logs_delete.js
//
// VeinMatch and SeamAI both wrote a row per analysis and then showed the shop
// only a COUNT of them.
//
//   sd_veinmatch  read back by one KPI tile ("Layouts Analyzed") and a CSV
//                 export. Nothing listed the analyses.
//   sd_seamai     read back by four KPI tiles and a CSV export. Same.
//
// A COUNT WITH NO LIST BEHIND IT IS A NUMBER NOBODY CAN CHECK, and there was no
// way to remove a row either -- a mistyped project name sat in the tally for
// good, inflating "Jobs Analyzed" and "Material Savings" for ever.
//
// AND NEITHER HAD EVER BEEN BACKED UP. Both sit in SD_SYNCED, which reads as
// "this is backed up", but their rows carried no `id` and sdSyncCollection()
// skips those. Third and fourth instance of that shape today, after the
// communication log and the SMS log.
//
// The two modules are tested together because they are the same pattern, and
// the arms are parameterised so a divergence between them shows up as one
// failing case rather than as two files drifting apart.

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
// EVERY GRAB IS ANCHORED AFTER THE MODULE'S OWN save(), which is unique in the
// file. `function updateKPIs(){` and `function load(){` each appear in many
// IIFEs, and anchoring on the first match pulls a different panel's copy -- a
// mistake that is loud when the stubbed element ids differ and SILENT when they
// happen to overlap.
function fnAfter(decl, after) {
  const i = html.indexOf(decl, after);
  assert.ok(i > after, 'not found after anchor: ' + decl);
  return balanced(i);
}

const MODULES = {
  VeinMatch: {
    key: 'sd_veinmatch',
    prefix: 'VM',
    fields: ['date', 'proj', 'stone'],
    saveSig: "function save(d){return st('sd_veinmatch',d);}",
    ensure: '  function veinEnsureIds(){',
    renderSaved: '  function veinRenderSaved(d){',
    del: '  window.sdVeinDelete=function(id){',
    analyze: '  window.sdVeinAnalyze=function(){',
    listId: 'vein-saved-list',
    kpiIds: ['vein-jobs', 'vein-match', 'vein-waste', 'vein-saved'],
    delName: 'sdVeinDelete',
    rows: [
      { proj: 'Hartley kitchen', stone: 'Calacatta', style: 'Bookmatch', date: '2026-09-10' },
      { proj: 'Park island', stone: 'Taj Mahal', style: 'Sequential', date: '2026-09-11' }
    ],
    label: 'Hartley kitchen'
  },
  SeamAI: {
    key: 'sd_seamai',
    prefix: 'SA',
    fields: ['date', 'job', 'loc'],
    saveSig: "function save(d){return st('sd_seamai',d);}",
    ensure: '  function seamEnsureIds(){',
    renderSaved: '  function seamRenderSaved(d){',
    del: '  window.sdSeamDelete=function(id){',
    analyze: '  window.sdSeamAnalyze=function(){',
    listId: 'seam-saved-list',
    kpiIds: ['seam-analyzed', 'seam-approved', 'seam-remakes', 'seam-savings'],
    delName: 'sdSeamDelete',
    rows: [
      { job: 'Hartley kitchen', mat: 'Quartz', loc: 'Kitchen Island', date: '2026-09-10', remake: false },
      { job: 'Park vanity', mat: 'Granite', loc: 'Bathroom Vanity', date: '2026-09-11', remake: true }
    ],
    label: 'Hartley kitchen'
  }
};

function build(m, rows, opts) {
  opts = opts || {};
  const at = html.indexOf(m.saveSig);
  assert.ok(at > 0, 'save() moved or changed for ' + m.key);
  const store = {}; store[m.key] = JSON.stringify(rows);
  const out = { saved: [], toasts: [], confirms: [], els: {} };
  m.kpiIds.concat([m.listId]).forEach(id => {
    out.els[id] = { textContent: '', innerHTML: '' };
  });
  const ctx = {};
  const src =
    balanced(html.indexOf('function sdRowId(prefix,row,fields){')) + '\n' +
    balanced(html.indexOf('function sdEnsureRowIds(rows,prefix,fields){')) + '\n' +
    // load() is taken from just before the module's own save(), by span.
    html.slice(html.lastIndexOf('function load()', at), at) + '\n' +
    m.saveSig + '\n' +
    fnAfter(m.ensure, at) + '\n' +
    fnAfter('  function updateKPIs(){', at) + '\n' +
    fnAfter(m.renderSaved, at) + '\n' +
    fnAfter(m.del, at) + '\n' +
    'ctx.ensure=' + m.ensure.trim().replace(/^function\s+/, '').replace(/\(.*$/, '') + ';'
    + 'ctx.updateKPIs=updateKPIs; ctx.del=window.' + m.delName + ';';
  new Function('localStorage', 'st', 'document', 'escHtml', 'escAttrJs',
               'showToast', 'confirm', 'window', 'ctx', src)(
    { getItem: k => (k in store ? store[k] : null) },
    (k, v) => { if (opts.saveFails) return false; out.saved.push(v); store[k] = JSON.stringify(v); return true; },
    { getElementById: id => out.els[id] || null },
    s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'),
    s => String(s),
    msg => out.toasts.push(String(msg)),
    msg => { out.confirms.push(String(msg)); return opts.confirm !== false; },
    {}, ctx
  );
  return { ctx, out, store };
}

(function main() {
  console.log('StoneDesk AI analysis logs -- a list behind the count, and a delete\n');

  Object.keys(MODULES).forEach(name => {
    const m = MODULES[name];
    section(name + ' (' + m.key + ')');

    test(name + ': ids are derived, so two devices agree', () => {
      const a = build(m, m.rows), b = build(m, m.rows);
      assert.deepStrictEqual(a.ctx.ensure().map(x => x.id), b.ctx.ensure().map(x => x.id));
      assert.ok(a.ctx.ensure()[0].id.startsWith(m.prefix + '-'));
    });

    test(name + ': two different analyses do not collide', () => {
      const ids = build(m, m.rows).ctx.ensure().map(x => x.id);
      assert.strictEqual(new Set(ids).size, 2);
    });

    test(name + ': back-filling writes once and is then idempotent', () => {
      const b = build(m, m.rows);
      b.ctx.ensure();
      assert.strictEqual(b.out.saved.length, 1);
      b.ctx.ensure();
      assert.strictEqual(b.out.saved.length, 1);
    });

    test(name + ': every row ends with a non-empty id -- what the sync skips on', () => {
      const b = build(m, m.rows.concat([{}]));
      b.ctx.ensure().forEach(x => assert.ok(x.id !== undefined && x.id !== null && x.id !== ''));
    });

    // THE LIST IS THE FEATURE. The count already existed; what did not was any
    // way to see what it was counting.
    test(name + ': the saved list renders one row per analysis', () => {
      const b = build(m, m.rows);
      b.ctx.updateKPIs();
      const h = b.out.els[m.listId].innerHTML;
      assert.ok(h.indexOf(m.label) !== -1, 'the analyses are still invisible: ' + h.slice(0, 160));
      assert.strictEqual((h.match(new RegExp('onclick="' + m.delName + '\\(', 'g')) || []).length, 2);
    });

    test(name + ': and the count agrees with the list it now shows', () => {
      const b = build(m, m.rows);
      b.ctx.updateKPIs();
      assert.strictEqual(String(b.out.els[m.kpiIds[0]].textContent), '2');
    });

    test(name + ': an empty log says so rather than rendering an empty box', () => {
      const b = build(m, []);
      b.ctx.updateKPIs();
      assert.ok(/No analyses saved yet/.test(b.out.els[m.listId].innerHTML));
    });

    test(name + ': no button is ever wired to an empty id', () => {
      const b = build(m, m.rows.concat([{}]));
      b.ctx.updateKPIs();
      assert.ok(!new RegExp(m.delName + "\\(''\\)").test(b.out.els[m.listId].innerHTML));
    });

    // A project name is user input and reaches the list unescaped if nobody
    // says otherwise -- the same check every other list in this app carries.
    test(name + ': a name containing markup is escaped, not rendered', () => {
      const evil = Object.assign({}, m.rows[0]);
      evil[m.fields[1]] = '<img src=x onerror=1>';
      const b = build(m, [evil]);
      b.ctx.updateKPIs();
      const h = b.out.els[m.listId].innerHTML;
      assert.ok(h.indexOf('<img src=x') === -1, 'markup reached the list unescaped');
      assert.ok(h.indexOf('&lt;img') !== -1);
    });

    test(name + ': deleting writes the survivors back', () => {
      const b = build(m, m.rows);
      const id = b.ctx.ensure()[0].id;
      b.out.saved.length = 0;
      b.ctx.del(id);
      assert.strictEqual(b.out.saved.length, 1);
      assert.strictEqual(b.out.saved[0].length, 1);
    });

    test(name + ': and the count drops with it', () => {
      const b = build(m, m.rows);
      b.ctx.del(b.ctx.ensure()[0].id);
      assert.strictEqual(String(b.out.els[m.kpiIds[0]].textContent), '1');
    });

    test(name + ': the confirm says kept, never "cannot be undone"', () => {
      const b = build(m, m.rows, { confirm: false });
      b.ctx.del(b.ctx.ensure()[0].id);
      const msg = b.out.confirms[0] || '';
      assert.ok(/hidden and kept, not destroyed/.test(msg), msg);
      assert.ok(!/cannot be undone/i.test(msg));
    });

    test(name + ': declining writes nothing', () => {
      const b = build(m, m.rows, { confirm: false });
      const id = b.ctx.ensure()[0].id;
      b.out.saved.length = 0;
      b.ctx.del(id);
      assert.strictEqual(b.out.saved.length, 0);
    });

    test(name + ': an id matching nothing writes nothing and says nothing', () => {
      const b = build(m, m.rows);
      b.ctx.ensure();
      b.out.saved.length = 0; b.out.toasts.length = 0;
      b.ctx.del(m.prefix + '-NO-SUCH');
      assert.strictEqual(b.out.saved.length, 0);
      assert.strictEqual(b.out.toasts.length, 0);
    });

    test(name + ': an empty id is refused before the confirm', () => {
      const b = build(m, m.rows);
      b.ctx.del('');
      assert.ok(/no id yet/.test(b.out.toasts[0] || ''));
      assert.strictEqual(b.out.confirms.length, 0);
    });

    test(name + ': a storage failure is reported, with no success toast', () => {
      const b = build(m, m.rows, { saveFails: true });
      const id = b.ctx.ensure()[0].id;
      b.out.toasts.length = 0;
      b.ctx.del(id);
      assert.ok(/Could not delete that analysis/.test(b.out.toasts.join('|')), JSON.stringify(b.out.toasts));
      assert.ok(!/Analysis deleted/.test(b.out.toasts.join('|')));
    });

    // BOTH SAVE PATHS. Each analyze() writes the row twice -- once on the API
    // reply and once in the .catch() fallback -- and an id set on only one of
    // them would leave every offline analysis unsyncable and undeletable.
    test(name + ': BOTH save paths set an id, not just the happy one', () => {
      const at = html.indexOf(m.saveSig);
      const analyze = fnAfter(m.analyze, at);
      const sets = (analyze.match(new RegExp("sdEnsureRowIds\\(d,'" + m.prefix + "'", 'g')) || []).length;
      assert.strictEqual(sets, 2,
        'the API path and the offline fallback do not both assign an id');
    });
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  if (fail) process.exit(1);
})();
