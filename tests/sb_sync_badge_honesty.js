// tests/sb_sync_badge_honesty.js
//
// Run:  node tests/sb_sync_badge_honesty.js
//
// SAIRNbiz's Company panel shows a "Synced / Not Synced" badge that tells the
// user whether StoneDesk can read the current employee roster. Its only input
// was `sb_sync`, the timestamp of the last SUCCESSFUL sync -- so it could only
// ever answer "has this install EVER synced", while reading as "the server has
// the current roster". Two callers, both wrong, in opposite ways:
//
//   * syncSupabase() -- the manual Sync button -- toasted "Sync failed" and
//     LEFT THE BADGE GREEN. The failure branch touched nothing.
//   * saveEmp() -- every employee add or edit -- called syncEmps() and
//     DISCARDED the promise. A failed sync there produced a console.warn and
//     nothing else: no toast, no badge change, and the timestamp still showing
//     the old successful time. The user is told StoneDesk can read the roster
//     while StoneDesk is reading one missing the employee just entered.
//
// `sb_sync_stale` was added rather than clearing `sb_sync`, and the assertion
// that pins that choice is the one about the timestamp SURVIVING a failure:
// clearing it would show "Never" for an install that has synced, which is a
// different false statement.
//
// THE REAL FUNCTIONS ARE DRIVEN against a fake localStorage and a fake DOM.
// `$()` is stubbed -- it is a one-line getElementById wrapper and is not what
// is under test; everything else here comes out of the file.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const FILE = 'sairnbiz.html';

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

function grab(src, sig) {
  const i = src.indexOf(sig);
  assert.ok(i > 0, sig + ' not found');
  const rel = src.slice(i).search(/\r?\n\}/);
  assert.ok(rel > 0, sig + ' is not terminated');
  return src.slice(i, i + rel) + '\n}';
}

function load(opts) {
  opts = opts || {};
  const src = fs.readFileSync(path.join(ROOT, FILE), 'utf8');
  const store = Object.assign({}, opts.store);
  const els = {
    'co-sd-status': { className: '', textContent: '' },
    'co-sync': { textContent: 'Never' },
  };
  if (opts.noBadgeEl) delete els['co-sd-status'];
  if (opts.noSyncEl) delete els['co-sync'];
  const ctx = {
    JSON: JSON, String: String, Number: Number, Date: Date, Object: Object,
    $: (id) => els[id] || null,
    localStorage: {
      getItem: (k) => (Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null),
      setItem: (k, v) => { store[k] = v; },
    },
    console: { error: () => {}, warn: () => {}, log: () => {} },
  };
  vm.createContext(ctx);
  vm.runInContext(grab(src, 'function st(k,v){'), ctx);
  vm.runInContext(grab(src, 'function ld(k,d){'), ctx);
  vm.runInContext(grab(src, 'function sbRecordSyncResult(ok){'), ctx);
  vm.runInContext(grab(src, 'function renderSyncStatus(){'), ctx);
  return { ctx, els, store };
}

const badge = (els) => els['co-sd-status'].textContent;

section('the badge answers "is the server current", not "did this ever work"');

test('a fresh install reads Not Synced', () => {
  const { ctx, els } = load({});
  ctx.renderSyncStatus();
  assert.strictEqual(badge(els), 'Not Synced');
  assert.strictEqual(els['co-sd-status'].className, 'badge bx');
});

test('a successful sync turns it green and stamps the time', () => {
  const { ctx, els, store } = load({});
  assert.strictEqual(ctx.sbRecordSyncResult(true), true, 'the result was not passed through');
  assert.strictEqual(badge(els), 'Synced');
  assert.strictEqual(els['co-sd-status'].className, 'badge bg');
  assert.ok(store['sb_sync'], 'no timestamp was stored');
  assert.notStrictEqual(els['co-sync'].textContent, 'Never', 'the panel still says Never');
});

test('A FAILURE AFTER A SUCCESS TURNS IT RED -- the whole defect', () => {
  const { ctx, els } = load({});
  ctx.sbRecordSyncResult(true);
  assert.strictEqual(badge(els), 'Synced');
  assert.strictEqual(ctx.sbRecordSyncResult(false), false, 'the result was not passed through');
  assert.strictEqual(badge(els), 'Not Synced',
    'the badge stayed green through a failed sync, which is the bug this file exists for');
  assert.strictEqual(els['co-sd-status'].className, 'badge bx');
});

test('...and the LAST SUCCESSFUL TIME SURVIVES the failure', () => {
  // This is the assertion that pins sb_sync_stale over clearing sb_sync.
  // "Never" on an install that has synced is a different false statement.
  const { ctx, els, store } = load({});
  ctx.sbRecordSyncResult(true);
  const stamped = store['sb_sync'];
  const shown = els['co-sync'].textContent;
  ctx.sbRecordSyncResult(false);
  assert.strictEqual(store['sb_sync'], stamped, 'the last successful time was erased');
  assert.strictEqual(els['co-sync'].textContent, shown, 'the panel stopped showing when it last worked');
});

test('a failure on a NEVER-synced install leaves it red and stores nothing false', () => {
  const { ctx, els, store } = load({});
  assert.strictEqual(ctx.sbRecordSyncResult(false), false);
  assert.strictEqual(badge(els), 'Not Synced');
  assert.strictEqual(store['sb_sync'], undefined, 'a timestamp was invented for a sync that never happened');
});

test('a later success clears the stale mark and goes green again', () => {
  const { ctx, els } = load({});
  ctx.sbRecordSyncResult(true);
  ctx.sbRecordSyncResult(false);
  assert.strictEqual(badge(els), 'Not Synced');
  ctx.sbRecordSyncResult(true);
  assert.strictEqual(badge(els), 'Synced', 'a recovered sync never cleared the stale mark');
});

test('an EXISTING install that synced before this change still reads Synced', () => {
  // sb_sync_stale is absent on every install that predates it. Defaulting it
  // to true would flip every working customer to red on first load.
  const { ctx, els } = load({ store: { 'sb_sync': '"1/2/2026, 9:00:00 AM"' } });
  ctx.renderSyncStatus();
  assert.strictEqual(badge(els), 'Synced');
});

test('neither function throws when the Company panel elements are absent', () => {
  ['noBadgeEl', 'noSyncEl'].forEach((k) => {
    const opts = {}; opts[k] = true;
    const { ctx } = load(opts);
    assert.doesNotThrow(() => ctx.sbRecordSyncResult(true), k + ' threw on success');
    assert.doesNotThrow(() => ctx.sbRecordSyncResult(false), k + ' threw on failure');
    assert.doesNotThrow(() => ctx.renderSyncStatus(), k + ' threw on render');
  });
});

section('both call sites go through the one helper');

test('saveEmp no longer DISCARDS the sync promise', () => {
  const squashed = fs.readFileSync(path.join(ROOT, FILE), 'utf8')
    .replace(/\/\/[^\n]*/g, '')      // the new comment quotes the old line
    .replace(/\s+/g, '');
  assert.ok(!/rEmps\(\);syncEmps\(emps\);/.test(squashed),
    'saveEmp is back to firing syncEmps() and throwing the result away');
  assert.ok(/syncEmps\(emps\)\.then\(/.test(squashed),
    'saveEmp does not read the sync result at all');
});

test('and it reports the failure to the USER, not only to the console', () => {
  const src = fs.readFileSync(path.join(ROOT, FILE), 'utf8');
  const i = src.indexOf('function saveEmp(){');
  assert.ok(i > 0);
  const body = src.slice(i, i + 2600);
  assert.ok(/sbRecordSyncResult\(ok\)/.test(body), 'saveEmp does not use the shared helper');
  assert.ok(/toast\(/.test(body) && /sync to the server FAILED/.test(body),
    'a failed sync from the employee modal is still silent to the user');
});

test('syncSupabase routes through the helper too, so the two cannot diverge', () => {
  const src = fs.readFileSync(path.join(ROOT, FILE), 'utf8');
  const body = grab(src, 'function syncSupabase(){');
  assert.ok(/sbRecordSyncResult\(ok\)/.test(body),
    'the manual Sync button keeps its own bookkeeping, which is how these two drifted');
  assert.ok(!/st\('sb_sync',now\)/.test(body),
    'syncSupabase still stamps the timestamp itself');
});

test('renderSyncStatus reads BOTH facts, not just the timestamp', () => {
  const body = grab(fs.readFileSync(path.join(ROOT, FILE), 'utf8'), 'function renderSyncStatus(){');
  assert.ok(/sb_sync_stale/.test(body),
    'the badge is back to answering "has this ever synced"');
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' SYNC-BADGE ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
