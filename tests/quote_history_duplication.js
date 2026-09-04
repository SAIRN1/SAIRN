// tests/quote_history_duplication.js
//
// Run:  node tests/quote_history_duplication.js
//
// The Quote History panel's quoted value climbed on its own every time anyone
// changed a quote's status.
//
// load() MERGES two stores -- sd_quote_history and sd_aiquotes -- so the panel
// can show both. save() wrote the whole merged array back into
// sd_quote_history alone. There is exactly one mutator,
// sdHistoryUpdateStatus(), and it does `var d=load(); ...; save(d)`:
//
//     history [H], ai [A]
//     change a status -> save([H,A])     -> history is now [H,A]
//     next load       -> [H,A] + [A]     -> [H,A,A]
//     change again    -> history [H,A,A] -> next load [H,A,A,A]
//
// One duplicate per AI quote per status change, permanently. Total Quotes,
// Total Value, Win Rate and Average are all computed from that array, so all
// four inflate together -- a shop watching its own pipeline grow without
// quoting anything.
//
// Found by tools/key_collision_check.py flagging sd_quote_history as written by
// two distinct backing variables. NOTE that the tool still flags it after the
// fix, with the new variable names, and that is CORRECT: two writers is exactly
// what the fix introduces on purpose. The tool is a pointer, not a verdict --
// register entry 16 records the same thing about the sd_referrals collision it
// found in August ("traced by hand"). THIS suite is the verdict.
//
// The fix ROUTES each row back to the store it came from rather than stripping
// AI rows on save: a status change on an AI quote is a real edit, and dropping
// it would trade a duplication bug for a data-loss one.

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

function grab(sig, indent) {
  const s = html.indexOf(sig);
  assert.ok(s > 0, 'not found in stonedesk.html: ' + sig);
  const rest = html.slice(s);
  const m = rest.match(new RegExp('\\r?\\n' + indent + '\\};?(?=\\r?\\n)'));
  assert.ok(m, 'not terminated: ' + sig);
  return rest.slice(0, m.index + m[0].length);
}

const SRC = [
  grab('function load(){\n    var d=[];', '  '),
  grab('function save(d){\n    var hist=[],ai=[];', '  '),
  grab('function updateKPIs(d){', '  '),
  grab('window.sdHistoryUpdateStatus=function(){', '  ')
].join('\n\n');

const KPI_IDS = ['hist-total', 'hist-value', 'hist-won', 'hist-rate', 'hist-avg'];

function build(opts) {
  opts = opts || {};
  const store = {};
  if (opts.history !== undefined) store['sd_quote_history'] = JSON.stringify(opts.history);
  if (opts.ai !== undefined) store['sd_aiquotes'] = JSON.stringify(opts.ai);

  const els = {};
  KPI_IDS.concat(['hist-status-sel', 'hist-new-status', 'hist-breakdown', 'hist-top'])
    .forEach(id => { els[id] = { id, value: '', textContent: '', innerHTML: '' }; });

  const ctx = {
    console,
    localStorage: { getItem: k => (k in store ? store[k] : null) },
    st: (k, v) => { store[k] = JSON.stringify(v); return true; },
    document: { getElementById: id => els[id] || null },
    sdDemoCleared: () => true,          // no seed path in these cases
    sdHistoryRender: () => {},
    showToast: () => {},
    escHtml: s => String(s == null ? '' : s),
    SEED: []
  };
  vm.createContext(ctx);
  const body = opts.mutate ? opts.mutate(SRC) : SRC;
  vm.runInContext('var SEED=[];\nvar window=this;\n' + body +
    '\nthis.api={load:load,save:save,kpis:updateKPIs,' +
    'setStatus:function(id,s){els(\'hist-status-sel\').value=id;' +
    'els(\'hist-new-status\').value=s;window.sdHistoryUpdateStatus();}};',
    Object.assign(ctx, { els: id => els[id] }));
  return { ctx, els, store, api: ctx.api,
           read: k => (k in store ? JSON.parse(store[k]) : null) };
}
const kpi = b => KPI_IDS.reduce((o, id) => (o[id] = b.els[id].textContent, o), {});

const H = [{ id: 1, customer: 'Hartwell', amount: 4000, status: 'Pending' }];
const AI = [{ id: 101, customer: 'Ruiz', amount: 1000, status: 'Pending' },
            { id: 102, customer: 'Chen', amount: 2000, status: 'Approved' }];

console.log('StoneDesk Quote History -- a status change must not clone the AI quotes\n');

section('the KPIs hold still across repeated status changes');

test('three quotes stay three quotes after ten status changes', () => {
  const b = build({ history: H, ai: AI });
  b.api.kpis(b.api.load());
  const before = kpi(b);
  assert.strictEqual(before['hist-total'], 3, 'the fixture is wrong: ' + JSON.stringify(before));
  for (let i = 0; i < 10; i++) {
    b.api.setStatus(1, i % 2 ? 'Pending' : 'Approved');
    b.api.kpis(b.api.load());
    assert.strictEqual(kpi(b)['hist-total'], 3,
      'total climbed to ' + kpi(b)['hist-total'] + ' after ' + (i + 1) + ' status change(s)');
  }
});

test('Total Value, Win Rate and Average are stable too, not just the count', () => {
  const b = build({ history: H, ai: AI });
  b.api.setStatus(1, 'Approved');
  b.api.kpis(b.api.load());
  const first = kpi(b);
  for (let i = 0; i < 5; i++) b.api.setStatus(1, 'Approved');
  b.api.kpis(b.api.load());
  assert.deepStrictEqual(kpi(b), first, 'a KPI moved without anything being quoted');
  assert.strictEqual(first['hist-value'], '$7,000');
});

test('the two stores keep their own rows -- 1 and 2, not 1 and 3', () => {
  const b = build({ history: H, ai: AI });
  for (let i = 0; i < 4; i++) b.api.setStatus(1, 'Declined');
  assert.strictEqual(b.read('sd_quote_history').length, 1,
    'AI quotes were copied into the history store');
  assert.strictEqual(b.read('sd_aiquotes').length, 2);
});

section('routing, not stripping: an edit to an AI quote survives');

test('changing an AI quote status writes it back to sd_aiquotes', () => {
  const b = build({ history: H, ai: AI });
  b.api.setStatus(101, 'Approved');
  const ai = b.read('sd_aiquotes');
  assert.strictEqual(ai.length, 2);
  assert.strictEqual(ai.find(x => x.id === 101).status, 'Approved',
    'the edit was dropped -- that would be data loss, not a fix');
  assert.strictEqual(b.read('sd_quote_history').length, 1,
    'the AI row leaked into the history store');
});

test('...and the routing tag never reaches storage', () => {
  const b = build({ history: H, ai: AI });
  b.api.setStatus(101, 'Approved');
  const all = b.read('sd_aiquotes').concat(b.read('sd_quote_history'));
  all.forEach(r => assert.ok(!('_src' in r), '_src persisted into ' + JSON.stringify(r)));
});

test('a history-quote edit still lands in the history store', () => {
  const b = build({ history: H, ai: AI });
  b.api.setStatus(1, 'Declined');
  assert.strictEqual(b.read('sd_quote_history')[0].status, 'Declined');
});

section('the empty and absent cases');

test('an empty sd_aiquotes is not erased by a save', () => {
  // Writing [] unconditionally would destroy that store on any save made from a
  // state where it happened to hold nothing.
  const b = build({ history: H, ai: [] });
  b.api.setStatus(1, 'Approved');
  assert.deepStrictEqual(b.read('sd_aiquotes'), []);
});

test('no sd_aiquotes key at all: nothing is created, history still saves', () => {
  const b = build({ history: H });
  b.api.setStatus(1, 'Approved');
  assert.strictEqual(b.read('sd_aiquotes'), null, 'an empty store was invented');
  assert.strictEqual(b.read('sd_quote_history')[0].status, 'Approved');
});

test('corrupt sd_aiquotes JSON does not take the panel down', () => {
  const b = build({ history: H });
  b.store['sd_aiquotes'] = '{not json';
  const d = b.api.load();
  assert.strictEqual(d.length, 1, 'the history rows were lost with the bad store');
});

section('MUTATION: the pre-fix save, restored, inflates the panel');

test('MUTANT: writing the merged array back to one store duplicates on every change', () => {
  const UNFIX = src => {
    const out = src.replace(/function save\(d\)\{[\s\S]*?\n  \}/,
                            "function save(d){return st('sd_quote_history',d);}");
    assert.notStrictEqual(out, src, 'save() was not found -- this mutation asserts nothing');
    return out;
  };
  const b = build({ history: H, ai: AI, mutate: UNFIX });
  b.api.kpis(b.api.load());
  assert.strictEqual(kpi(b)['hist-total'], 3);
  b.api.setStatus(1, 'Approved');
  b.api.kpis(b.api.load());
  assert.strictEqual(kpi(b)['hist-total'], 5,
    'the mutant did not duplicate -- it no longer reproduces the defect');
  b.api.setStatus(1, 'Pending');
  b.api.kpis(b.api.load());
  assert.strictEqual(kpi(b)['hist-total'], 7);
  // And the money, which is the part a shop would actually notice. Derived by
  // hand rather than copied from the run -- 4000 + (1000+2000)x3 = 13,000:
  //   load 1: [H,A1,A2]                    $7,000
  //   save   -> history [H,A1,A2]
  //   load 2: history + ai = 5 rows       $10,000
  //   save   -> history 5 rows
  //   load 3: 5 + 2 = 7 rows              $13,000
  assert.strictEqual(kpi(b)['hist-value'], '$13,000',
    'from a real $7,000 of quotes, after two status changes');
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
if (fail) process.exitCode = 1;
