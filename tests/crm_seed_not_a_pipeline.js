// tests/crm_seed_not_a_pipeline.js
//
// Run:  node tests/crm_seed_not_a_pipeline.js
//
// This is the Slabs defect (`501d15b`) found in the one other place it exists.
//
// A full audit of all 31 `sdDemoCleared() ? [] : SEED` sites in stonedesk.html
// on 2026-09-04 found exactly ONE with a real server resource behind it:
// sd_crm. That is what makes the fallback dangerous there and merely a demo
// everywhere else -- a seed can only MASK real data if real data exists
// somewhere else to be masked.
//
// THE SHAPE. sd_crm's load() is a local cache of the last real server read.
// With no cache and a FAILED read, it returned six invented leads, and render()
// did real arithmetic on them:
//
//     crm-leads      6
//     crm-pipeline   $35,900      <- somebody else's demo pipeline
//     crm-hot        1
//     crm-conv       0%
//     crm-avg        $5,983
//
// Nothing said the read had failed. A shop with a broken session, an expired
// key or an unreachable database saw a populated CRM and a five-figure pipeline
// presented as its own.
//
// WHAT THE FIX IS NOT. It does not delete the seed. Deleting it outright was
// the Slabs fix and would also delete the demo here, which is a product
// decision. The seed is left for the case it was written for -- a genuine first
// run, before any sync -- and skipped for the case it never covered. Note how
// narrow the first case is: a SUCCESSFUL read of [] is saved as [], which is
// truthy, so the seed never returns after one good sync. It was only ever
// reachable before the first sync, or after a failed one.
//
// The distinction is carried by sdReadFailed(), added the same day for the
// Public Catalog panel. Without it a first-run user with no session is
// indistinguishable from one whose database is unreachable.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8');

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

// The seed's own numbers, read out of the file rather than typed here, so this
// suite still describes the real seed if somebody edits it.
const SEED_SRC = (() => {
  const anchor = html.indexOf("localStorage.getItem('sd_crm')");
  assert.ok(anchor > 0, 'the sd_crm cache read is gone');
  const s = html.lastIndexOf('var SEED=', anchor);
  return html.slice(s, html.indexOf('];', s) + 2);
})();
const SEED_PIPELINE = (SEED_SRC.match(/val:(\d+)/g) || [])
  .reduce((a, m) => a + Number(m.slice(4)), 0);
const SEED_ROWS = (SEED_SRC.match(/\{name:/g) || []).length;

function grab(sig, indent) {
  const s = html.indexOf(sig);
  assert.ok(s > 0, 'not found in stonedesk.html: ' + sig);
  const rest = html.slice(s);
  const m = rest.match(new RegExp('\\r?\\n' + indent + '\\};?(?=\\r?\\n)'));
  assert.ok(m, 'not terminated: ' + sig);
  return rest.slice(0, m.index + m[0].length);
}
function grabLine(sig) {
  const s = html.indexOf(sig);
  assert.ok(s > 0, 'not found: ' + sig);
  return html.slice(s, html.indexOf('\n', s));
}

const PARTS = [
  grabLine('var _crmReadFailed=false;'),
  grab('function crmSeed(){', '  '),
  grabLine("function load(){try{return JSON.parse(localStorage.getItem('sd_crm')||'null')||crmSeed();}"),
  grabLine("function save(d){return st('sd_crm',d);}"),
  grab('function refresh(){', '  '),
  grab('function render(){\n    var d=load();\n    var isMgmt=crmIsManagement();', '  ')
].join('\n\n');

const KPI_IDS = ['crm-leads', 'crm-pipeline', 'crm-hot', 'crm-conv', 'crm-avg'];

// One sandbox per case.
function build(opts) {
  const els = {};
  ['crm-assignee', 'crm-kanban', 'crm-tbody'].concat(KPI_IDS)
    .forEach(id => { els[id] = { id, textContent: '', innerHTML: '', style: {} }; });
  const store = {};
  if (opts.cache !== undefined) store['sd_crm'] = JSON.stringify(opts.cache);

  const ctx = {
    console,
    document: { getElementById: id => els[id] || null },
    localStorage: { getItem: k => (k in store ? store[k] : null) },
    st: (k, v) => { store[k] = JSON.stringify(v); return v; },
    escHtml: s => String(s == null ? '' : s),
    escAttrJs: s => String(s),
    sdDemoCleared: () => !!opts.demoCleared,
    crmIsManagement: () => false,
    refreshRoster: () => {},
    employeeName: () => '',
    sdReadFailedNote: what => '<div>Could not load ' + what + '</div>',
    // The two the fix turns on.
    sdReadFailed: () => !!opts.readFailed,
    sdData: opts.noSdData ? undefined
      : () => Promise.resolve(opts.readFailed ? null : opts.serverRows),
    STAGES: ['New Lead', 'Contacted', 'Quote Sent', 'Hot'],
    _roster: null
  };
  vm.createContext(ctx);
  const body = opts.mutate ? opts.mutate(PARTS) : PARTS;
  vm.runInContext(
    SEED_SRC + '\n' +
    'var _roster=null;\n' +
    'var STAGES=["New Lead","Contacted","Quote Sent","Hot"];\n' +
    body + '\n' +
    'this.api={render:render,refresh:refresh,load:load,' +
    'failed:function(){return _crmReadFailed;}};', ctx);
  return { ctx, els, store, api: ctx.api };
}
const kpi = b => KPI_IDS.reduce((o, id) => (o[id] = b.els[id].textContent, o), {});

async function main() {
  console.log('StoneDesk CRM -- a failed read must not print somebody else\'s pipeline\n');
  console.log('  (seed as it stands in the file: ' + SEED_ROWS + ' leads, $' +
              SEED_PIPELINE.toLocaleString() + ' pipeline)\n');

  section('the demo the seed was written for is still there');

  await test('first run, before any sync: the seed still renders', async () => {
    const b = build({});
    b.api.render();
    assert.strictEqual(kpi(b)['crm-leads'], SEED_ROWS,
      'the demo was deleted -- that is a product decision, not this fix');
    assert.strictEqual(kpi(b)['crm-pipeline'], '$' + SEED_PIPELINE.toLocaleString());
  });

  await test('demo explicitly cleared: empty, and that has not changed', async () => {
    const b = build({ demoCleared: true });
    b.api.render();
    assert.strictEqual(kpi(b)['crm-leads'], 0);
    assert.strictEqual(kpi(b)['crm-pipeline'], '$0');
  });

  section('a FAILED read must not be answered by the seed');

  await test('no cache + failed read: no invented leads and no invented pipeline', async () => {
    const b = build({ readFailed: true });
    await b.api.refresh();
    const k = kpi(b);
    assert.strictEqual(b.api.failed(), true);
    assert.notStrictEqual(k['crm-pipeline'], '$' + SEED_PIPELINE.toLocaleString(),
      'the demo pipeline was shown to a shop whose read failed');
    KPI_IDS.forEach(id => assert.strictEqual(k[id], '--',
      id + ' printed a number computed from nothing'));
  });

  await test('...and it says so rather than showing an empty table', async () => {
    const b = build({ readFailed: true });
    await b.api.refresh();
    assert.match(b.els['crm-tbody'].innerHTML, /Could not load your leads/);
    assert.strictEqual(b.els['crm-kanban'].innerHTML, '');
  });

  await test('a failed read must not print a confident $0 either', async () => {
    // $0 pipeline and 0% conversion are as wrong as $35,900 when the truth is
    // "we could not ask" -- they just look more innocent.
    const b = build({ readFailed: true });
    await b.api.refresh();
    assert.notStrictEqual(kpi(b)['crm-pipeline'], '$0');
    assert.notStrictEqual(kpi(b)['crm-conv'], '0%');
  });

  section('the real states still work');

  await test('a real empty CRM reads as empty, is cached, and shows real zeroes', async () => {
    const b = build({ serverRows: [] });
    await b.api.refresh();
    assert.strictEqual(b.store['sd_crm'], '[]');
    assert.strictEqual(b.api.failed(), false);
    assert.strictEqual(kpi(b)['crm-leads'], 0);
    assert.strictEqual(kpi(b)['crm-pipeline'], '$0', 'a genuine zero must still be a zero');
  });

  await test('and the seed can never return after one good sync', async () => {
    // [] is truthy, so the cached empty array wins over the seed forever after.
    const b = build({ serverRows: [] });
    await b.api.refresh();
    const back = b.api.load();
    // Length rather than deepStrictEqual: the array crosses a vm realm
    // boundary, so it is not reference-equal to this file's Array.prototype.
    assert.strictEqual(back.length, 0);
  });

  await test('real leads render and are counted', async () => {
    const b = build({ serverRows: [
      { name: 'A', proj: 'Kitchen', val: 1000, stage: 'Hot', source: 'Web' },
      { name: 'B', proj: 'Bath', val: 500, stage: 'Contacted', source: 'Web' }] });
    await b.api.refresh();
    assert.strictEqual(kpi(b)['crm-leads'], 2);
    assert.strictEqual(kpi(b)['crm-pipeline'], '$1,500');
  });

  await test('a failed read leaves an existing cache alone -- unchanged behaviour', async () => {
    const b = build({ readFailed: true, cache: [
      { name: 'Real Lead', proj: 'Kitchen', val: 9000, stage: 'Hot', source: 'Referral' }] });
    await b.api.refresh();
    assert.strictEqual(kpi(b)['crm-pipeline'], '$9,000',
      'a transient failure wiped or hid the local cache');
    assert.strictEqual(JSON.parse(b.store['sd_crm']).length, 1);
  });

  await test('a later success clears the failure state', async () => {
    const b = build({ readFailed: true });
    await b.api.refresh();
    assert.strictEqual(b.api.failed(), true);
    b.ctx.sdData = () => Promise.resolve([]);
    await b.api.refresh();
    assert.strictEqual(b.api.failed(), false, 'one blip disabled the panel permanently');
  });

  section('MUTATION: put the old fallback back and the pipeline reappears');

  await test('MUTANT: without the guard, a failed read really does print $' +
             SEED_PIPELINE.toLocaleString(), async () => {
    const UNGUARD = src => {
      const out = src.replace('return (_crmReadFailed||sdDemoCleared())?[]:SEED;',
                              'return sdDemoCleared()?[]:SEED;')
                     .replace('var unread=_crmReadFailed&&!d.length;',
                              'var unread=false;');
      assert.notStrictEqual(out, src, 'the mutation is a no-op -- this asserts nothing');
      return out;
    };
    const b = build({ readFailed: true, mutate: UNGUARD });
    await b.api.refresh();
    assert.strictEqual(kpi(b)['crm-pipeline'], '$' + SEED_PIPELINE.toLocaleString(),
      'the mutant did not reproduce the defect -- the guard is not what fixes it');
    assert.strictEqual(kpi(b)['crm-leads'], SEED_ROWS);
  });

  section('the audit that found this, recorded so it is not repeated blind');

  await test('sd_crm is still the only one of the 31 seed sites with a server read', async () => {
    // If a second resource gains a server read while keeping its seed fallback,
    // it inherits this defect and this assertion is how anyone finds out.
    const sites = html.split('\n').filter(l => l.indexOf('sdDemoCleared()') !== -1 && l.indexOf('?[]:') !== -1);
    assert.strictEqual(sites.length, 31, 'the seed-site count moved: ' + sites.length);
    // Keys come from the cache READS that fall back to a seed -- directly, or
    // through crmSeed(), which is how sd_crm reads since the fix. Taking them
    // off the seed lines alone silently drops sd_crm and makes this assertion
    // pass by finding nothing, which is exactly what it did on first run.
    const keys = html.split('\n')
      .filter(l => /localStorage\.getItem\('sd_[a-z_]+'\)/.test(l) &&
                   (l.indexOf('sdDemoCleared()') !== -1 || l.indexOf('crmSeed()') !== -1))
      .map(l => l.match(/localStorage\.getItem\('(sd_[a-z_]+)'\)/)[1]);
    assert.ok(keys.indexOf('sd_crm') !== -1,
      'sd_crm dropped out of the seed-site list -- this assertion would pass while checking nothing');
    const backed = keys.filter(k => html.indexOf("sdData('read','" + k + "'") !== -1);
    assert.deepStrictEqual(backed, ['sd_crm'],
      'a seed-backed resource gained a server read: ' + backed.join(', ') +
      ' -- it now has the sd_crm defect and needs the same guard');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  if (fail) process.exitCode = 1;
}

main();
