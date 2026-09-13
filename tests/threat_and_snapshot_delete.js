// tests/threat_and_snapshot_delete.js
//
// Run:  node tests/threat_and_snapshot_delete.js
//
// The last two append-only logs that had no way off them.
//
//   sd_email_threats       flagged phishing scans. Listed on screen, never
//                          removable -- a scan flagged while testing the
//                          feature counted against "Scans Flagged" for good.
//   sd_business_snapshots  KPI captures. NOTHING read them back except a "last
//                          snapshot" date, so a shop could take ninety and look
//                          at none -- and could not remove one taken mid-import
//                          while the numbers were wrong, which is exactly when
//                          somebody presses the button twice.
//
// BOTH WERE ALSO NEVER BACKED UP. Both sit in SD_SYNCED, which reads as "this
// is backed up", but their rows carried no `id` and sdSyncCollection() skips
// those. Fifth and sixth instance of that shape.
//
// The snapshot list is the one that did not exist at all: a store with a writer,
// a 90-entry cap, a daily auto-save, and no reader.

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
function fn(decl, after) {
  const i = html.indexOf(decl, after || 0);
  assert.ok(i > 0, 'not found: ' + decl);
  return balanced(i);
}
const HELPERS =
  balanced(html.indexOf('function sdRowId(prefix,row,fields){')) + '\n' +
  balanced(html.indexOf('function sdEnsureRowIds(rows,prefix,fields){')) + '\n';

// ══ EMAIL THREATS ══════════════════════════════════════════════════════════
// Anchored after this module's own loadThreats(), which is unique.
const ET_AT = html.indexOf('function loadThreats(){');
assert.ok(ET_AT > 0, 'loadThreats() moved or changed');
const THREATS_KEY = (html.match(/var THREATS_KEY='([a-z_]+)';/) || [])[1];
assert.strictEqual(THREATS_KEY, 'sd_email_threats', 'the module key moved or changed');

function etBuild(rows, opts) {
  opts = opts || {};
  const store = { sd_email_threats: JSON.stringify(rows), sd_email_checklist: '{}' };
  const out = { toasts: [], confirms: [], writes: [], els: {} };
  ['email-blocked', 'email-phish', 'email-score', 'email-trained', 'email-threats', 'email-checklist']
    .forEach(id => { out.els[id] = { textContent: '', innerHTML: '' }; });
  const ctx = {};
  const src = HELPERS +
    fn('function loadThreats(){', ET_AT) + '\n' +
    fn('function saveThreats(d){', ET_AT) + '\n' +
    fn('  function threatsEnsureIds(){', ET_AT) + '\n' +
    fn('  window.sdEmailThreatDelete=function(id){', ET_AT) + '\n' +
    fn('  function render(){', ET_AT) + '\n' +
    'ctx.ensure=threatsEnsureIds; ctx.del=window.sdEmailThreatDelete; ctx.render=render;';
  // THREATS_KEY is the module's own key constant; without it loadThreats()
  // reads localStorage.getItem(undefined), gets null, and every arm below
  // runs against an empty log while reporting a confident failure about the
  // product. Taken from the file rather than restated.
  new Function('localStorage', 'st', 'document', 'escHtml', 'escAttrJs', 'showToast',
               'confirm', 'window', 'ctx', 'loadChecklist', 'CHECKLIST_ITEMS', 'rColors',
               'THREATS_KEY', src)(
    { getItem: k => (k in store ? store[k] : null) },
    (k, v) => { out.writes.push(k); if (opts.saveFails) return false; store[k] = JSON.stringify(v); return true; },
    { getElementById: id => out.els[id] || null },
    s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'),
    s => String(s),
    m => out.toasts.push(String(m)),
    m => { out.confirms.push(String(m)); return opts.confirm !== false; },
    {}, ctx,
    () => ({}), [], {},
    THREATS_KEY
  );
  return { ctx, out, store };
}
const THREATS = [
  { type: 'Phishing', risk: 'High', summary: 'Wire transfer request', date: '2026-09-10' },
  { type: 'Suspicious', risk: 'Medium', summary: 'Vendor bank change', date: '2026-09-11' }
];

section('email threat log');

test('ids are derived, so two devices agree', () => {
  const a = etBuild(THREATS), b = etBuild(THREATS);
  assert.deepStrictEqual(a.ctx.ensure().map(x => x.id), b.ctx.ensure().map(x => x.id));
  assert.ok(a.ctx.ensure()[0].id.startsWith('ET-'));
});

test('the list draws a Delete per flagged scan', () => {
  const b = etBuild(THREATS);
  b.ctx.render();
  const h = b.out.els['email-threats'].innerHTML;
  assert.strictEqual((h.match(/onclick="sdEmailThreatDelete\(/g) || []).length, 2);
  assert.ok(!/sdEmailThreatDelete\(''\)/.test(h), 'a row rendered with no id');
});

test('the summary is escaped -- it is pasted email content', () => {
  const b = etBuild([Object.assign({}, THREATS[0], { summary: '<img src=x onerror=1>' })]);
  b.ctx.render();
  const h = b.out.els['email-threats'].innerHTML;
  assert.ok(h.indexOf('<img src=x') === -1 && h.indexOf('&lt;img') !== -1);
});

test('deleting writes the survivors back and drops the count', () => {
  const b = etBuild(THREATS);
  const id = b.ctx.ensure()[0].id;
  b.ctx.del(id);
  assert.deepStrictEqual(JSON.parse(b.store.sd_email_threats).map(x => x.type), ['Suspicious']);
  assert.strictEqual(String(b.out.els['email-blocked'].textContent), '1');
});

test('the confirm says kept, never "cannot be undone"', () => {
  const b = etBuild(THREATS, { confirm: false });
  b.ctx.del(b.ctx.ensure()[0].id);
  const m = b.out.confirms[0] || '';
  assert.ok(/hidden and kept, not destroyed/.test(m), m);
  assert.ok(!/cannot be undone/i.test(m));
});

test('an id matching nothing never asks and never writes', () => {
  const b = etBuild(THREATS);
  b.ctx.ensure();
  b.out.writes.length = 0;
  b.ctx.del('ET-NO-SUCH');
  assert.strictEqual(b.out.confirms.length, 0);
  assert.strictEqual(b.out.writes.length, 0);
});

test('a storage failure is reported, with no success toast', () => {
  const b = etBuild(THREATS, { saveFails: true });
  const id = b.ctx.ensure()[0].id;
  b.out.toasts.length = 0;
  b.ctx.del(id);
  assert.ok(/Could not delete that scan/.test(b.out.toasts.join('|')), JSON.stringify(b.out.toasts));
  assert.ok(!/scan deleted/.test(b.out.toasts.join('|')));
});

// ══ BUSINESS SNAPSHOTS ═════════════════════════════════════════════════════
const BS_AT = html.indexOf('  function bizSnaps(){');
assert.ok(BS_AT > 0, 'bizSnaps() moved or changed');

function bsBuild(rows, opts) {
  opts = opts || {};
  const store = { sd_business_snapshots: JSON.stringify(rows) };
  const out = { toasts: [], confirms: [], writes: [], els: { 'biz-snap-list': { innerHTML: '' } } };
  const ctx = {};
  const src = HELPERS +
    fn('  function bizSnaps(){', BS_AT) + '\n' +
    fn('  window.sdBizSnapRender=function(){', BS_AT) + '\n' +
    fn('  window.sdBizSnapDelete=function(id){', BS_AT) + '\n' +
    'ctx.snaps=bizSnaps; ctx.render=window.sdBizSnapRender; ctx.del=window.sdBizSnapDelete;';
  new Function('localStorage', 'st', 'document', 'escHtml', 'escAttrJs', 'showToast',
               'confirm', 'window', 'ctx', src)(
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
const SNAPS = [
  { date: '2026-09-11T09:00:00.000Z', kpis: { revenue: '$120,000', margin: '38%', jobs: '14' } },
  { date: '2026-09-10T09:00:00.000Z', kpis: { revenue: '$118,000', margin: '37%', jobs: '13' } }
];

section('business KPI snapshots -- a store with a writer and no reader');

test('the list exists at all, and shows what each snapshot said', () => {
  const b = bsBuild(SNAPS);
  b.ctx.render();
  const h = b.out.els['biz-snap-list'].innerHTML;
  assert.ok(h.indexOf('revenue') !== -1 && h.indexOf('$120,000') !== -1,
    'the snapshots are still invisible: ' + h.slice(0, 200));
  assert.strictEqual((h.match(/onclick="sdBizSnapDelete\(/g) || []).length, 2);
});

test('an empty store says what the button is for', () => {
  const b = bsBuild([]);
  b.ctx.render();
  assert.ok(/Save KPI Snapshot/.test(b.out.els['biz-snap-list'].innerHTML));
});

test('ids are derived, so two devices agree', () => {
  const a = bsBuild(SNAPS), b = bsBuild(SNAPS);
  assert.deepStrictEqual(a.ctx.snaps().map(x => x.id), b.ctx.snaps().map(x => x.id));
  assert.ok(a.ctx.snaps()[0].id.startsWith('BS-'));
});

// TWO SNAPSHOTS IN ONE DAY IS THE NORMAL CASE -- there is a daily auto-save AND
// a manual button -- so the id has to separate them. `date` is a full ISO
// timestamp here, not a day, which is what makes that work.
test('two snapshots on the same day get different ids', () => {
  const b = bsBuild([
    { date: '2026-09-11T09:00:00.000Z', kpis: { a: '1' } },
    { date: '2026-09-11T14:30:00.000Z', kpis: { a: '2' } }
  ]);
  const ids = b.ctx.snaps().map(x => x.id);
  assert.strictEqual(new Set(ids).size, 2);
  assert.ok(!ids[1].endsWith('-2'), 'they collided and were suffixed rather than distinguished');
});

test('deleting writes the survivors back', () => {
  const b = bsBuild(SNAPS);
  const id = b.ctx.snaps()[0].id;
  b.ctx.del(id);
  assert.strictEqual(JSON.parse(b.store.sd_business_snapshots).length, 1);
});

test('the confirm says kept, never "cannot be undone"', () => {
  const b = bsBuild(SNAPS, { confirm: false });
  b.ctx.del(b.ctx.snaps()[0].id);
  const m = b.out.confirms[0] || '';
  assert.ok(/hidden and kept, not destroyed/.test(m), m);
  assert.ok(!/cannot be undone/i.test(m));
});

test('an id matching nothing never asks and never writes', () => {
  const b = bsBuild(SNAPS);
  b.ctx.snaps();
  b.out.writes.length = 0;
  b.ctx.del('BS-NO-SUCH');
  assert.strictEqual(b.out.confirms.length, 0);
  assert.strictEqual(b.out.writes.length, 0);
});

test('a storage failure is reported, with no success toast', () => {
  const b = bsBuild(SNAPS, { saveFails: true });
  const id = b.ctx.snaps()[0].id;
  b.out.toasts.length = 0;
  b.ctx.del(id);
  assert.ok(/Could not delete that snapshot/.test(b.out.toasts.join('|')), JSON.stringify(b.out.toasts));
});

// THE LIST HAS TO BE REACHED, and a render function nothing calls is the exact
// shape this panel already had -- a store with a writer and no reader.
test('the list is dispatched when the Business panel opens', () => {
  assert.ok(/if\(id==='business'&&typeof window\.sdBizSnapRender==='function'\)window\.sdBizSnapRender\(\);/.test(html),
    'nothing calls sdBizSnapRender, so the list would never appear');
});

test('and re-rendered after a snapshot is saved', () => {
  const save = fn('  window.sdBizSnapshot=function(){', BS_AT);
  assert.ok(/if\(snapSaved\) window\.sdBizSnapRender\(\);/.test(save),
    'a new snapshot would not appear until the panel was reopened');
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
