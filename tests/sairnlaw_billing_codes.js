// tests/sairnlaw_billing_codes.js
//
// Run:  node tests/sairnlaw_billing_codes.js
//
// THE OPEN-WORK ROW THAT SENT ME HERE WAS WRONG ABOUT THE RISK, and the real
// one was next to it. The row read: "law_billingcodes is seeded once and read
// by the billing panel, and reaches no server ... a firm that edits its own
// billing codes on one machine has them nowhere else."
//
// A firm cannot edit them at all. Two sites in the whole file -- the accessor
// and seed() -- and no UI anywhere that writes the key. So nothing is lost,
// and registering it in api/_resources/sairnlaw.js would be syncing a
// constant. That half of the row is retracted rather than built.
//
// WHAT WAS ACTUALLY THERE. The accessor was `ld('law_billingcodes',[])` and
// the 27 rows existed only as a literal inside seed(). ld() returns its
// default when the key is absent, when the stored JSON will not parse, and
// when localStorage is unavailable -- it logs all three, and the UI said
// nothing about any of them. An empty list made fillBillingCodeSelect() write
// `innerHTML=''`: an empty <select>, whose .value is ''. saveTime() validates
// the matter and the hours and NOT the code, so it wrote billing_code:'' into
// law_timeentries and synced it. A billable hour with no UTBMS code, silently,
// on the record invoices and LEDES export are built from.
//
// The fix is that the list is a constant, so it is one: LAW_BILLING_CODES,
// used by both seed() and the accessor's default. An unreadable store now
// shows the real 27 codes instead of an empty box.
//
// These tests hold the fix AND the finding it rests on -- that there is no
// edit path. If one is ever added, section 4 goes red, because at that moment
// the row's original premise becomes true and the sync question really does
// need answering.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'sairnlaw.html'), 'utf8').replace(/\r\n/g, '\n');
const registry = require(path.join(ROOT, 'api', '_resources', 'sairnlaw.js'));

let pass = 0, fail = 0;
const queue = [];
function test(name, fn) { queue.push({ name, fn }); }
function section(t) { queue.push({ section: t }); }

function fnBodyAt(at) {
  const open = html.indexOf('{', at);
  let depth = 0;
  for (let i = open; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}') { depth--; if (depth === 0) return html.slice(at, i + 1); }
  }
  throw new Error('unbalanced braces');
}
function fnBody(name) {
  const at = html.indexOf(name);
  assert.ok(at > 0, 'not found in sairnlaw.html: ' + name);
  return fnBodyAt(at);
}
// The whole `var LAW_BILLING_CODES=[...]` statement, lifted rather than
// retyped -- a fixture holding its own copy of the list is how the test and
// the app drift apart, which tests/sairnlaw_hydrate.js already learned once
// with LAW_SYNC_RESOURCES.
function codesSrc() {
  const at = html.indexOf('var LAW_BILLING_CODES=[');
  assert.ok(at > 0, 'LAW_BILLING_CODES not found -- the constant was removed or renamed');
  const end = html.indexOf('];', at);
  assert.ok(end > at, 'unterminated LAW_BILLING_CODES');
  return html.slice(at, end + 2);
}

// A realm holding the real constant, the real accessor and the real select
// filler. `stored` is what localStorage would hold; `unreadable` is ld()'s
// behaviour on a corrupt or unavailable store, which is to return the default.
function harness(opts) {
  opts = opts || {};
  const el = { innerHTML: '', get value() {
    // What a browser reports for a <select>: the first option's value, or ''
    // when there are none. That '' is the whole defect, so it is modelled
    // rather than asserted around.
    const m = /<option value="([^"]*)"/.exec(this.innerHTML);
    return m ? m[1] : '';
  } };
  const ctx = {
    JSON, Object, Array, String,
    ld: (k, d) => (Object.prototype.hasOwnProperty.call(opts.stored || {}, k)
      ? JSON.parse(JSON.stringify(opts.stored[k])) : d),
    st: (k, v) => { (ctx.__stored || (ctx.__stored = {}))[k] = v; return true; },
    $: () => (opts.noElement ? null : el),
    H: (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;'),
    __el: el,
  };
  vm.createContext(ctx);
  vm.runInContext(codesSrc() + '\n'
    + (opts.accessor || fnBody('function billingCodes()')) + '\n'
    + fnBody('function fillBillingCodeSelect()'), ctx);
  return ctx;
}

// ═══════════════════════════════════════════════════════════════════════════
section('1. the list is a constant, and it is the same one seed() writes');

test('LAW_BILLING_CODES holds the 27 UTBMS rows, each with id/code/label', () => {
  const c = harness({});
  assert.strictEqual(c.LAW_BILLING_CODES.length, 27);
  c.LAW_BILLING_CODES.forEach((r) => {
    assert.ok(r.id && r.code && r.label, 'incomplete row: ' + JSON.stringify(r));
    assert.strictEqual(r.id, r.code, 'id and code diverged on ' + r.code);
    assert.ok(/^L\d{3}$/.test(r.code), 'not a UTBMS litigation code: ' + r.code);
  });
});

test('seed() writes the CONSTANT, not a second copy of the list', () => {
  // The literal used to live inside seed(). Two copies of a 27-row table is
  // exactly the drift this consolidates away, so the literal must be gone.
  assert.ok(/st\('law_billingcodes',\s*LAW_BILLING_CODES\s*\)/.test(html),
    "seed() no longer writes law_billingcodes from LAW_BILLING_CODES");
  const seedAt = html.indexOf('function seed()');
  const seedBody = fnBodyAt(seedAt);
  assert.ok(seedBody.indexOf("code:'L100'") === -1,
    'the 27-row literal is still inside seed() -- there are two copies again');
});

// ═══════════════════════════════════════════════════════════════════════════
section('2. an unreadable store shows the real codes, not an empty dropdown');

test('billingCodes() falls back to the constant when the key is absent', () => {
  const c = harness({});                        // nothing stored: ld returns d
  assert.strictEqual(c.billingCodes().length, 27);
});

test('and the select is filled, so .value is a real code and never ""', () => {
  const c = harness({});
  c.fillBillingCodeSelect();
  assert.strictEqual((c.__el.innerHTML.match(/<option /g) || []).length, 27);
  assert.strictEqual(c.__el.value, 'L100');
});

test('a STORED list still wins -- the constant is a fallback, not an override', () => {
  const c = harness({ stored: { law_billingcodes: [{ id: 'X1', code: 'X1', label: 'Firm code' }] } });
  assert.strictEqual(c.billingCodes().length, 1);
  c.fillBillingCodeSelect();
  assert.strictEqual(c.__el.value, 'X1');
});

test('a stored EMPTY list is honoured, and that is the one case still empty', () => {
  // Deliberate and stated: `[]` in storage is a real stored value, not a
  // missing one, so ld() returns it and the fallback does not fire. Nothing in
  // this app can produce it today -- there is no writer but seed() -- and
  // inventing codes over a value someone stored on purpose is the seed-
  // fallback mistake this fix is careful not to make.
  const c = harness({ stored: { law_billingcodes: [] } });
  assert.strictEqual(c.billingCodes().length, 0);
  c.fillBillingCodeSelect();
  assert.strictEqual(c.__el.value, '');
});

test('NEGATIVE CONTROL: the OLD accessor gives the empty select this fixes', () => {
  // Same harness, same absent key, only the accessor body swapped back. If
  // this ever stops producing '', the test above proves nothing.
  const c = harness({ accessor: "function billingCodes(){return ld('law_billingcodes',[]);}" });
  c.fillBillingCodeSelect();
  assert.strictEqual(c.__el.innerHTML, '');
  assert.strictEqual(c.__el.value, '', 'the old shape must yield the empty-value defect');
});

test('a missing #ttcode element is still a safe no-op', () => {
  const c = harness({ noElement: true });
  c.fillBillingCodeSelect();                    // must not throw
});

// ═══════════════════════════════════════════════════════════════════════════
section('3. it is deliberately NOT a synced resource');

test('law_billingcodes is absent from the registry, and that is the decision', () => {
  assert.ok(registry.resources.indexOf('law_billingcodes') === -1,
    'law_billingcodes was registered -- a constant has nothing to sync. If an '
    + 'edit path now exists, section 4 will also be red and THAT is the '
    + 'question to answer first.');
});

test('the nineteen that ARE registered are untouched by this change', () => {
  const law = registry.resources.filter((r) => r.indexOf('law_') === 0);
  assert.strictEqual(law.length, 19, 'registered law_* count moved: ' + law.length);
});

// ═══════════════════════════════════════════════════════════════════════════
section('4. THE FINDING ITSELF: there is no edit path, and this pins it');

test('exactly one writer of law_billingcodes, and it is seed()', () => {
  const writes = html.match(/st\('law_billingcodes'/g) || [];
  assert.strictEqual(writes.length, 1,
    'law_billingcodes now has ' + writes.length + ' writers. If a firm can '
    + 'edit these codes, they are firm data, they live on one workstation, '
    + 'and the sync question in the open-work row is real after all.');
  const seedBody = fnBodyAt(html.indexOf('function seed()'));
  assert.ok(seedBody.indexOf("st('law_billingcodes'") > -1, 'the writer is not seed()');
});

test('exactly one reader, and it is the accessor', () => {
  const reads = html.match(/ld\('law_billingcodes'/g) || [];
  assert.strictEqual(reads.length, 1);
});

test('the panel tells the user the list is fixed', () => {
  // The old disclosure covered accuracy only. A reader had no way to know
  // whether this was their list or the app's, which is what made the
  // open-work row read the way it did.
  const at = html.indexOf('id="panel-billing"');
  assert.ok(at > 0, 'billing panel not found');
  const panel = html.slice(at, at + 4000);
  assert.ok(/This list is fixed/.test(panel), 'the fixed-list disclosure is gone');
  assert.ok(/UTBMS\/LEDES/.test(panel), 'the accuracy caveat was dropped');
});

// ═══════════════════════════════════════════════════════════════════════════
(async () => {
  for (const item of queue) {
    if (item.section) { console.log('\n' + item.section); continue; }
    try { await item.fn(); console.log('  ok   - ' + item.name); pass++; }
    catch (e) { console.log('  FAIL - ' + item.name + '\n         ' + e.message); fail++; }
  }
  console.log('\n' + pass + '/' + (pass + fail) + ' passed');
  process.exit(fail ? 1 : 0);
})();
