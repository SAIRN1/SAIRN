// tests/template_migration_orphaning.js
//
// Run:  node tests/template_migration_orphaning.js
//
// StoneDesk had two template modules on two storage keys. That was resolved on
// 2026-07-30 -- the tm* module on `sd_templates` is canonical, and
// tmMigrateLegacyRecords() moves anything left in `sd_template_records` across
// on load. The open-work row describing the duplication was stale by five
// weeks; what was NOT resolved was inside the migration itself.
//
// ── THE DEFECT ────────────────────────────────────────────────────────────
//     if(added)tmSave();
//     stRaw(FLAG,'1');
//
// The save's return value was ignored and the done-flag was set regardless.
// st() returns false on a localStorage quota failure, which is not theoretical
// here: the mapping embeds each legacy PHOTO as a data URL into the migrated
// record, making this the largest write the module ever performs.
//
// The consequence was permanent. A failed save set the flag anyway, so the
// migration never ran again -- and the legacy rows sat in sd_template_records,
// which this function deliberately never deletes, with nothing left in the app
// that would ever move them. The panel showed an empty template list and said
// nothing.
//
// That is the exact "silently orphans real user data" outcome the open-work row
// warned about, reached from a direction the row did not consider: it told
// whoever merged the modules to check which key the panel renders from. The
// answer to that was right. The failure was one line further down.
//
// The surrounding `catch(e){}` was also bare -- a migration of real customer
// records that fails should not do so without a trace.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

function grab(sig) {
  const s = html.indexOf(sig);
  assert.ok(s > 0, 'not found in stonedesk.html: ' + sig);
  const rest = html.slice(s);
  const m = rest.match(/\r?\n\}(?=\r?\n)/);
  assert.ok(m, 'not terminated: ' + sig);
  return rest.slice(0, m.index + m[0].length);
}

const SRC = grab('function tmMigrateLegacyRecords(){');
const FLAG = 'sd_templates_migrated_from_tmpl';

const LEGACY = [
  { id: 7, customer: 'Hartwell Kitchen', job: 'J-2026-014', method: 'laser',
    tech: 'Dana', date: '2026-08-30', cncStatus: 'programmed',
    dxfName: 'hartwell.dxf', photo: 'data:image/png;base64,AAAA', notes: 'two seams' },
  { id: 8, customer: 'Ruiz Bath', job: 'J-2026-021', method: 'digitizer',
    tech: 'Sam', date: '2026-09-01', cncStatus: 'complete' }
];

// opts.saveOk false simulates a localStorage quota failure on the migration
// write, which is the whole point of this suite.
function build(opts) {
  opts = opts || {};
  const store = Object.assign({}, opts.store);
  const notes = [], errs = [];
  const ctx = {
    console: { error: (...a) => errs.push(a.join(' ')), log: () => {} },
    localStorage: { getItem: k => (k in store ? store[k] : null) },
    tmRecords: (opts.existing || []).slice(),
    tmSave: () => { if (opts.saveOk === false) return false; store['sd_templates'] = 'saved'; return true; },
    stRaw: (k, v) => { if (opts.rawOk === false) return false; store[k] = v; return true; },
    notify: (m, kind) => notes.push((kind || '') + ':' + m),
    JSON, Math, Date
  };
  vm.createContext(ctx);
  vm.runInContext(SRC + '\nthis.run=tmMigrateLegacyRecords;', ctx);
  return { ctx, store, notes, errs, run: ctx.run };
}

console.log('StoneDesk template migration -- a failed move must not mark itself done\n');

section('the happy path, so the fix cannot pass by breaking migration');

test('legacy records are migrated and the flag is set', () => {
  const b = build({ store: { sd_template_records: JSON.stringify(LEGACY) } });
  b.run();
  assert.strictEqual(b.ctx.tmRecords.length, 2, 'nothing was migrated');
  assert.strictEqual(b.store[FLAG], '1', 'the flag was not set after a good save');
  assert.match(b.notes.join(' | '), /2 template records migrated/);
});

test('the status mapping is the documented one, including running -> reviewed', () => {
  const b = build({ store: { sd_template_records: JSON.stringify(
    LEGACY.concat([{ id: 9, cncStatus: 'running' }])) } });
  b.run();
  const byStatus = b.ctx.tmRecords.map(r => r.status);
  assert.deepStrictEqual(byStatus, ['reviewed', 'sent_cnc', 'reviewed']);
});

test('the photo and the DXF name both survive the move', () => {
  const b = build({ store: { sd_template_records: JSON.stringify(LEGACY) } });
  b.run();
  const files = b.ctx.tmRecords[0].files;
  // join() rather than deepStrictEqual: the array crosses a vm realm boundary,
  // so it is structurally equal but not reference-equal to this file's Array.
  assert.strictEqual(files.map(f => f.type).sort().join(','), 'dxf,photo');
  assert.strictEqual(files.find(f => f.type === 'photo').data, 'data:image/png;base64,AAAA');
});

test('it is idempotent -- a second run adds nothing', () => {
  const b = build({ store: { sd_template_records: JSON.stringify(LEGACY) } });
  b.run();
  const first = b.ctx.tmRecords.length;
  delete b.store[FLAG];            // force the guard open
  b.run();
  assert.strictEqual(b.ctx.tmRecords.length, first, 'a re-run duplicated rows');
});

test('the legacy key is never deleted, so the move stays reversible', () => {
  const b = build({ store: { sd_template_records: JSON.stringify(LEGACY) } });
  b.run();
  assert.ok(b.store['sd_template_records'], 'the legacy data was destroyed');
});

section('a save that fails must NOT mark the migration done');

test('quota failure leaves the flag UNSET, so the next load retries', () => {
  const b = build({ store: { sd_template_records: JSON.stringify(LEGACY) }, saveOk: false });
  b.run();
  assert.strictEqual(b.store[FLAG], undefined,
    'the flag was set after a failed save -- the records are orphaned forever');
});

test('...and the user is told, in words that say nothing was lost', () => {
  const b = build({ store: { sd_template_records: JSON.stringify(LEGACY) }, saveOk: false });
  b.run();
  assert.match(b.notes.join(' | '), /err:/, 'the failure was not surfaced as an error');
  assert.match(b.notes.join(' | '), /Nothing was lost/);
  assert.ok(!/2 template records migrated/.test(b.notes.join(' | ')),
    'it reported a successful migration that did not happen');
});

test('...and it is logged, so the failure leaves a trace either way', () => {
  const b = build({ store: { sd_template_records: JSON.stringify(LEGACY) }, saveOk: false });
  b.run();
  assert.match(b.errs.join(' | '), /flag deliberately NOT set/);
});

test('the retry after a failure actually migrates once storage frees up', () => {
  const b = build({ store: { sd_template_records: JSON.stringify(LEGACY) }, saveOk: false });
  b.run();
  assert.strictEqual(b.store[FLAG], undefined);
  const b2 = build({ store: { sd_template_records: JSON.stringify(LEGACY) } });
  b2.run();
  assert.strictEqual(b2.ctx.tmRecords.length, 2);
  assert.strictEqual(b2.store[FLAG], '1');
});

section('nothing to migrate is not a failure');

test('no legacy key: flag set, nothing said', () => {
  const b = build({});
  b.run();
  assert.strictEqual(b.store[FLAG], '1');
  assert.deepStrictEqual(b.notes, []);
});

test('an empty legacy array: flag set, nothing said', () => {
  const b = build({ store: { sd_template_records: '[]' } });
  b.run();
  assert.strictEqual(b.store[FLAG], '1');
});

test('corrupt legacy JSON is logged rather than swallowed by a bare catch', () => {
  const b = build({ store: { sd_template_records: '{not json' } });
  b.run();   // must not throw
  assert.match(b.errs.join(' | '), /tmMigrateLegacyRecords failed/);
  assert.strictEqual(b.store[FLAG], undefined,
    'corrupt data marked the migration done');
});

section('MUTATION: the pre-fix lines, restored, orphan the records');

test('MUTANT: ignoring the save result sets the flag on a failed migration', () => {
  const UNFIX = src => {
    const out = src.replace(/if\(added&&!tmSave\(\)\)\{[\s\S]*?\n    \}\n/, 'if(added)tmSave();\n');
    assert.notStrictEqual(out, src, 'the guard was not found -- this mutation asserts nothing');
    return out;
  };
  const store = { sd_template_records: JSON.stringify(LEGACY) };
  const ctx = {
    console: { error: () => {}, log: () => {} },
    localStorage: { getItem: k => (k in store ? store[k] : null) },
    tmRecords: [],
    tmSave: () => false,                       // quota failure
    stRaw: (k, v) => { store[k] = v; return true; },
    notify: () => {},
    JSON, Math, Date
  };
  vm.createContext(ctx);
  vm.runInContext(UNFIX(SRC) + '\nthis.run=tmMigrateLegacyRecords;', ctx);
  ctx.run();
  assert.strictEqual(store[FLAG], '1',
    'the mutant did not set the flag -- it no longer reproduces the defect');
  // And that is the orphaning: flag set, nothing saved, legacy data still
  // sitting there with nothing that will ever move it.
  assert.ok(store['sd_template_records'], 'legacy rows gone too, which would be worse');
  assert.strictEqual(store['sd_templates'], undefined, 'the mutant saved after all');
});

section('the duplication itself really is resolved');

test('the canonical key is sd_templates and the legacy one is only ever read', () => {
  // The open-work row said to check which key the panel renders from before
  // merging. Asserting the answer so the question is not re-opened.
  assert.match(html, /var TM_KEY='sd_templates';/);
  const writes = html.split('\n').filter(l =>
    /(st|stRaw)\(\s*'sd_template_records'/.test(l) ||
    /setItem\(\s*'sd_template_records'/.test(l));
  assert.deepStrictEqual(writes, [],
    'something writes the legacy key: ' + writes.join(' | '));
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
if (fail) process.exitCode = 1;
