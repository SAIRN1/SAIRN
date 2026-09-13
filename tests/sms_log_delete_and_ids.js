// tests/sms_log_delete_and_ids.js
//
// Run:  node tests/sms_log_delete_and_ids.js
//
// The SMS log had the same defect the communication log did, and for the same
// reason: sdSyncCollection() skips any row without an `id`, sdSMSSend() never
// set one, and `sd_sms_log` sits in SD_SYNCED -- a list whose name reads as
// "this is backed up". Every message a shop composed lived in one browser and
// died with its cache.
//
// It also had no way to remove an entry. A mistyped recipient stayed in the log
// for good.
//
// THE ID IS SHARED CODE NOW. sdEnsureRowIds() carries the reasoning for why it
// is derived from the row's content rather than minted -- a random back-fill id
// differs per device, so one message becomes one server row per browser that
// ever opened the panel, and deleting it on one cannot delete it on the other.
// This file pins the SMS-specific half: which FIELDS identify an SMS, and that
// the panel actually offers the button.

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
  assert.ok(i > 0, 'not found in stonedesk.html: ' + decl);
  return balanced(i);
}
// `function render(){` appears in many IIFEs. Anchoring on the FIRST one in the
// file pulled a different module's renderer, which threw on element ids this
// module never touches -- a suite that would have "tested" the wrong panel if
// those ids had happened to exist. Everything ambiguous is taken from AFTER the
// SMS module's own save(), which is unique.
const SMS_AT = html.indexOf("function save(d){return st('sd_sms_log',d);}");
// Full unique text, not a bare name: there are many `function load()` in a
// 2.5MB single-file app and the wrong one gives a suite that runs happily
// against a store these functions never touch.
function exact(text) {
  assert.strictEqual(html.split(text).length - 1, 1, 'moved or changed: ' + text.slice(0, 60));
  return text;
}
const LOAD = exact("function load(){try{return JSON.parse(localStorage.getItem('sd_sms_log')||'[]');}catch(e){return [];}}");
const SAVE = exact("function save(d){return st('sd_sms_log',d);}");

const ROWS = [
  { to: 'Marcus Webb', phone: '555-0100', msg: 'Your slab is ready', date: '2026-09-10 09:15', status: 'Sent' },
  { to: 'Emma Rodriguez', phone: '555-0101', msg: 'Install Tuesday', date: '2026-09-11 14:02', status: 'Sent' }
];

function build(rows, opts) {
  opts = opts || {};
  const store = { sd_sms_log: JSON.stringify(rows) };
  const out = { saved: [], toasts: [], confirms: [], rendered: 0, els: {} };
  ['sms-sent', 'sms-today', 'sms-delivered', 'sms-log'].forEach(id => {
    out.els[id] = { textContent: '', innerHTML: '' };
  });
  const ctx = {};
  const src =
    fn('function sdRowId(prefix,row,fields){') + '\n' +
    fn('function sdEnsureRowIds(rows,prefix,fields){') + '\n' +
    LOAD + '\n' + SAVE + '\n' +
    fn('  function smsEnsureIds(){', SMS_AT) + '\n' +
    fn('  function render(){', SMS_AT) + '\n' +
    fn('  window.sdSMSDelete=function(id){', SMS_AT) + '\n' +
    'ctx.smsEnsureIds=smsEnsureIds; ctx.render=render; ctx.sdSMSDelete=window.sdSMSDelete;';
  new Function('localStorage', 'st', 'document', 'escHtml', 'escAttrJs', 'sdLocalToday',
               'showToast', 'confirm', 'window', 'ctx', src)(
    { getItem: k => (k in store ? store[k] : null) },
    (k, v) => { if (opts.saveFails) return false; out.saved.push(v); store[k] = JSON.stringify(v); return true; },
    { getElementById: id => out.els[id] || null },
    s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'),
    s => String(s),
    () => '2026-09-13',
    m => out.toasts.push(String(m)),
    m => { out.confirms.push(String(m)); return opts.confirm !== false; },
    {}, ctx
  );
  return { ctx, out, store };
}

(function main() {
  console.log('StoneDesk SMS log -- ids that make it syncable, and a delete\n');

  section('the id is derived from the message, so two devices agree');

  test('the same log yields the same ids on any device', () => {
    const a = build(ROWS), b = build(ROWS);
    assert.deepStrictEqual(a.ctx.smsEnsureIds().map(x => x.id),
                           b.ctx.smsEnsureIds().map(x => x.id));
  });

  test('and two different messages do not collide', () => {
    const ids = build(ROWS).ctx.smsEnsureIds().map(x => x.id);
    assert.strictEqual(new Set(ids).size, 2);
    assert.ok(ids[0].startsWith('SMS-'), ids[0]);
  });

  // THE FIELD LIST IS THE SMS-SPECIFIC DECISION, and it is asserted rather than
  // assumed: two messages to the same person in the same minute with DIFFERENT
  // text are different entries, so `msg` has to be part of the id.
  test('same recipient, same minute, different text = two ids', () => {
    const b = build([
      { to: 'A', phone: '555', msg: 'first', date: '2026-09-10 09:15', status: 'Sent' },
      { to: 'A', phone: '555', msg: 'second', date: '2026-09-10 09:15', status: 'Sent' }
    ]);
    const ids = b.ctx.smsEnsureIds().map(x => x.id);
    assert.strictEqual(new Set(ids).size, 2, 'two distinct messages collapsed to one id');
    assert.ok(!ids[1].endsWith('-2'), 'they collided and were suffixed rather than distinguished');
  });

  test('truly identical entries are suffixed, not merged away', () => {
    const dup = [ROWS[0], Object.assign({}, ROWS[0])];
    const ids = build(dup).ctx.smsEnsureIds().map(x => x.id);
    assert.strictEqual(new Set(ids).size, 2);
    assert.ok(ids[1].endsWith('-2'), ids[1]);
  });

  test('back-filling writes once and is then idempotent', () => {
    const b = build(ROWS);
    b.ctx.smsEnsureIds();
    assert.strictEqual(b.out.saved.length, 1);
    b.ctx.smsEnsureIds();
    assert.strictEqual(b.out.saved.length, 1);
  });

  test('every row ends up with a non-empty id -- what the sync skips on', () => {
    const b = build(ROWS.concat([{ to: '', phone: '', msg: '', date: '', status: '' }]));
    b.ctx.smsEnsureIds().forEach(x => assert.ok(x.id !== undefined && x.id !== '' && x.id !== null));
  });

  section('an entry can be removed');

  test('deleting writes the survivors back', () => {
    const b = build(ROWS);
    const id = b.ctx.smsEnsureIds()[0].id;
    b.out.saved.length = 0;
    b.ctx.sdSMSDelete(id);
    assert.strictEqual(b.out.saved.length, 1);
    assert.strictEqual(b.out.saved[0].length, 1);
    assert.strictEqual(b.out.saved[0][0].to, 'Emma Rodriguez');
  });

  test('the confirm says kept, not destroyed, and never "cannot be undone"', () => {
    const b = build(ROWS, { confirm: false });
    b.ctx.sdSMSDelete(b.ctx.smsEnsureIds()[0].id);
    const m = b.out.confirms[0] || '';
    assert.ok(/hidden and kept, not destroyed/.test(m), m);
    assert.ok(!/cannot be undone/i.test(m));
  });

  test('declining writes nothing', () => {
    const b = build(ROWS, { confirm: false });
    const id = b.ctx.smsEnsureIds()[0].id;
    b.out.saved.length = 0;
    b.ctx.sdSMSDelete(id);
    assert.strictEqual(b.out.saved.length, 0);
  });

  test('an id matching nothing writes nothing and says nothing', () => {
    const b = build(ROWS);
    b.ctx.smsEnsureIds();
    b.out.saved.length = 0; b.out.toasts.length = 0;
    b.ctx.sdSMSDelete('SMS-NO-SUCH');
    assert.strictEqual(b.out.saved.length, 0);
    assert.strictEqual(b.out.toasts.length, 0);
  });

  test('an empty id is refused before the confirm, with a sentence', () => {
    const b = build(ROWS);
    b.ctx.sdSMSDelete('');
    assert.ok(/no id yet/.test(b.out.toasts[0] || ''));
    assert.strictEqual(b.out.confirms.length, 0);
  });

  test('a storage failure is reported, and no success toast is shown', () => {
    const b = build(ROWS, { saveFails: true });
    const id = b.ctx.smsEnsureIds()[0].id;
    b.out.toasts.length = 0;
    b.ctx.sdSMSDelete(id);
    assert.ok(/Could not delete that entry/.test(b.out.toasts.join('|')), JSON.stringify(b.out.toasts));
    assert.ok(!/entry deleted/.test(b.out.toasts.join('|')));
  });

  section('the panel offers it, on the real renderer');

  test('render draws a Delete per row, wired to the row id', () => {
    const b = build(ROWS);
    b.ctx.render();
    const h = b.out.els['sms-log'].innerHTML;
    assert.strictEqual((h.match(/onclick="sdSMSDelete\(/g) || []).length, 2);
    assert.ok(/sdSMSDelete\('SMS-/.test(h), h.slice(0, 200));
  });

  test('and back-fills before drawing, so no button is wired to an empty id', () => {
    const b = build(ROWS);
    b.ctx.render();
    assert.ok(!/sdSMSDelete\(''\)/.test(b.out.els['sms-log'].innerHTML),
      'a row rendered with no id -- its Delete button would refuse');
  });

  test('an empty log still says so rather than rendering nothing', () => {
    const b = build([]);
    b.ctx.render();
    assert.ok(/No messages yet/.test(b.out.els['sms-log'].innerHTML));
  });

  test('sdSMSSend assigns an id on the way in, not only on a later render', () => {
    const send = fn('  window.sdSMSSend=function(){', SMS_AT);
    assert.ok(/sdEnsureRowIds\(d,'SMS',\['date','phone','msg'\]\);/.test(send),
      'a message sent today would not be syncable until the next render');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  if (fail) process.exit(1);
})();
