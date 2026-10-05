// tests/sairnlegacy_item_price_lists.js
// REQUIREMENT: the Casket and Outer Burial Container price lists must be built
//   from the real merchandise catalog, must put a VAULT on the OBCPL and an URN
//   on neither, must never print a missing price as $0, and must refuse to
//   render an empty catalog as a finished list asserting nothing is offered
//
// Run:  node tests/sairnlegacy_item_price_lists.js
//       LEG_HTML=<mutated copy> node tests/sairnlegacy_item_price_lists.js
//
// ── THE GAP THIS CLOSES ───────────────────────────────────────────────────
// docs/cloud-research/sairnlegacy-competitive-gap-audit-2026-10-05.md calls F1
// "CONFIRMED AS DISQUALIFYING": the FTC Funeral Rule requires a GPL, ITEMISED
// casket and outer-burial-container price lists, and a statement of goods and
// services -- and every established vendor sells that as a headline feature.
//
// Checked before building rather than assumed: the GPL half WAS already here
// (modal, print path, leg_gplservices). Searching sairnlegacy.html for "CPL"
// and "outer burial container price" returned ZERO. So only the two itemised
// lists were missing, and only those were built.
//
// ── THE THREE ARMS THAT ARE ABOUT DISCLOSURE AND NOT ABOUT CODE ──────────
// B2  a VAULT belongs on the OBCPL -- the Rule's term covers vaults
// B3  an URN belongs on NEITHER -- putting it on one would be a disclosure
//     about an item the Rule does not govern, which is its own kind of wrong
// C1  a missing price must NOT render as $0. fmt(0) gives "$0.00" and a $0
//     casket on a price list reads as an OFFER, not as a gap

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const HTML_PATH = process.env.LEG_HTML
  || path.join(__dirname, '..', 'sairnlegacy.html');
const html = fs.readFileSync(HTML_PATH, 'utf8').replace(/\r\n/g, '\n');
const { stripComments } = require('./lib/strip_comments.js');
const codeOnly = stripComments(html);

const QUEUE = [];
let pass = 0, fail = 0;
function test(name, fn) { QUEUE.push([name, fn]); }
function section(t) { QUEUE.push([t, null]); }
async function runQueue(queue, log) {
  let p = 0, f = 0;
  for (const [name, fn] of queue) {
    if (!fn) { log('\n' + name); continue; }
    try { await fn(); log('  ok   ' + name); p++; }
    catch (e) { log('  FAIL ' + name + '\n       ' + e.message); f++; }
  }
  return { pass: p, fail: f };
}

function grab(sig, terminator) {
  const at = html.indexOf(sig);
  assert.ok(at > 0, 'not found in ' + path.basename(HTML_PATH) + ': ' + sig);
  const end = html.indexOf(terminator, at);
  assert.ok(end > at, 'terminator not found after ' + sig);
  return html.slice(at, end + terminator.length);
}
function grabVar(name) {
  const m = html.match(new RegExp('var ' + name + ' = \\{[\\s\\S]*?\\n\\};'));
  assert.ok(m, 'not found: var ' + name);
  return m[0];
}

// The functions under test are EXTRACTED from the app, never reimplemented --
// a reimplementation tests a copy that agrees with the original exactly until
// the day it does not.
function build(catalog) {
  const shown = [];
  const src = [
    grabVar('IPL_KINDS'),
    grab('function iplRows(kind){', '\n}'),
    grab('function openItemPriceList(kind){', '\n}'),
    grab('function rItemPriceListStatus(){', '\n}')
  ].join('\n\n');
  const el = (id) => ({ _id: id, set innerHTML(v) { shown.push([id, v]); },
                        set textContent(v) { shown.push([id, v]); },
                        classList: { add() {}, remove() {} } });
  const ctx = {
    Object, Array, String, Number, Math, JSON, isFinite,
    merchCatalog: () => catalog,
    H: (s) => String(s == null ? '' : s),
    fmt: (n) => '$' + Number(n || 0).toFixed(2),
    toast: () => {},
    $: (id) => el(id),
    console: { log() {}, warn() {} }
  };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(src, ctx, { filename: 'sairnlegacy-ipl-extract.js' });
  return { ctx, shown, html: (id) => (shown.filter((s) => s[0] === id).pop() || [, ''])[1] };
}

const CASKET_A = { id: 'M1', category: 'Casket', model_name: 'Cambridge Oak', sku: 'CO-18G', retail: 3400 };
const CASKET_B = { id: 'M2', category: 'Casket', model_name: 'Heritage Cherry', sku: 'HC-SW', retail: 4800 };
const URN      = { id: 'M3', category: 'Urn', model_name: 'Serenity Bronze', sku: 'SB-URN', retail: 495 };
const VAULT    = { id: 'M4', category: 'Vault', model_name: 'Standard Concrete', sku: 'VC-1', retail: 1200 };
const OBC      = { id: 'M5', category: 'Outer Burial Container', model_name: 'Graveliner', sku: 'GL-1', retail: 900 };
const NOPRICE  = { id: 'M6', category: 'Casket', model_name: 'Unpriced Pine', sku: 'UP-1' };
const ALL = [CASKET_A, CASKET_B, URN, VAULT, OBC];

console.log('SAIRNlegacy -- the Funeral Rule itemised price lists\n');

section('A. the lists draw from the real catalog');
test('A1. the casket list holds exactly the caskets', () => {
  const { ctx } = build(ALL);
  const ids = ctx.iplRows('casket').rows.map((r) => r.id);
  assert.deepStrictEqual(ids.sort(), ['M1', 'M2']);
});
test('A2. the OBC list holds the outer burial containers', () => {
  const { ctx } = build(ALL);
  const ids = ctx.iplRows('obc').rows.map((r) => r.id);
  assert.ok(ids.indexOf('M5') >= 0, 'the graveliner is missing');
});
test('A3. an unknown list kind returns nothing and does not throw', () => {
  const { ctx } = build(ALL);
  const r = ctx.iplRows('nonsense');
  assert.strictEqual(r.spec, null);
  // LENGTH, NOT deepStrictEqual. The array is built inside the vm realm, so
  // its prototype is that realm's Array and deepStrictEqual compares
  // prototypes -- it fails on two empty arrays that are both empty. Same trap
  // recorded in tests/sairnsenior_referral_hours.js.
  assert.strictEqual(r.rows.length, 0);
  assert.strictEqual(r.missingPrice.length, 0);
});

section('B. the category mapping, which is a DISCLOSURE decision');
test('B1. CONTROL: the two lists are not the same list', () => {
  const { ctx } = build(ALL);
  const c = ctx.iplRows('casket').rows.map((r) => r.id).sort().join(',');
  const o = ctx.iplRows('obc').rows.map((r) => r.id).sort().join(',');
  assert.notStrictEqual(c, o, 'both lists returned ' + c);
});
test('B2. a VAULT is on the OBCPL -- the Rule\'s term covers vaults', () => {
  const { ctx } = build(ALL);
  assert.ok(ctx.iplRows('obc').rows.some((r) => r.id === 'M4'),
    'the vault is missing from the outer burial container list');
});
test('B3. an URN is on NEITHER list -- cremation urns are not governed by '
  + 'either itemised list, and listing one is a disclosure about an item the '
  + 'Rule does not reach', () => {
  const { ctx } = build(ALL);
  assert.ok(!ctx.iplRows('casket').rows.some((r) => r.id === 'M3'), 'urn on the CPL');
  assert.ok(!ctx.iplRows('obc').rows.some((r) => r.id === 'M3'), 'urn on the OBCPL');
});
test('B4. a vault is NOT on the casket list', () => {
  const { ctx } = build(ALL);
  assert.ok(!ctx.iplRows('casket').rows.some((r) => r.id === 'M4'));
});

section('C. a missing price is never rendered as money');
test('C1. an item with no retail is flagged, not priced at $0', () => {
  const b = build([CASKET_A, NOPRICE]);
  b.ctx.openItemPriceList('casket');
  const out = b.html('ipl-preview');
  assert.ok(/PRICE NOT ON FILE/.test(out), 'the missing price was not flagged');
  assert.ok(!/\$0\.00/.test(out),
    'a missing price rendered as $0.00, which on a price list reads as an offer');
});
test('C2. ...and the real price still prints', () => {
  const b = build([CASKET_A, NOPRICE]);
  b.ctx.openItemPriceList('casket');
  assert.ok(/\$3400\.00/.test(b.html('ipl-preview')));
});
test('C3. iplRows reports WHICH items lack a price, not just how many', () => {
  const { ctx } = build([CASKET_A, NOPRICE]);
  const r = ctx.iplRows('casket');
  assert.strictEqual(r.missingPrice.length, 1);
  assert.strictEqual(r.missingPrice[0].id, 'M6');
});
test('C4. a retail of 0 entered ON PURPOSE is treated as a real price, not '
  + 'as missing -- a no-charge item is a legitimate line', () => {
  const { ctx } = build([{ id: 'Z', category: 'Casket', model_name: 'Donated', retail: 0 }]);
  assert.strictEqual(ctx.iplRows('casket').missingPrice.length, 0);
});

section('D. an empty catalog must not print as a finished list');
test('D1. an empty casket list REFUSES to render a table', () => {
  const b = build([URN]);
  b.ctx.openItemPriceList('casket');
  const out = b.html('ipl-preview');
  assert.ok(/Nothing on file/i.test(out), 'no refusal text: ' + out.slice(0, 160));
  assert.ok(!/<table>/.test(out),
    'an empty table rendered, which reads as "we offer none of these"');
});
test('D2. ...and says so in words a reader cannot mistake for a result', () => {
  const b = build([URN]);
  b.ctx.openItemPriceList('casket');
  assert.ok(/empty catalog/i.test(b.html('ipl-preview')));
});

section('E. the panel status line agrees with the documents');
test('E1. it names both lists and their counts', () => {
  const b = build(ALL);
  b.ctx.rItemPriceListStatus();
  const s = b.html('mc-pricelist-status');
  assert.ok(/Casket list: 2 item/.test(s), s.slice(0, 200));
  assert.ok(/Outer burial container list: 2 item/.test(s), s.slice(0, 200));
});
test('E2. it reports unpriced items rather than calling the list ready', () => {
  const b = build([CASKET_A, NOPRICE]);
  b.ctx.rItemPriceListStatus();
  assert.ok(/1 with no price/.test(b.html('mc-pricelist-status')));
});
test('E3. it never claims COMPLIANCE -- whether a list was OFFERED to a '
  + 'family is an act this system cannot observe', () => {
  const b = build(ALL);
  b.ctx.rItemPriceListStatus();
  const s = b.html('mc-pricelist-status');
  assert.ok(!/compliant/i.test(s), 'the status line claims compliance: ' + s);
  assert.ok(/cannot record that a list was offered/i.test(s),
    'the limit is not stated');
});

section('F. source properties a later edit would quietly undo');
test('F1. both buttons are on the MERCHANDISE panel, where caskets are shown',
  () => {
    const at = codeOnly.indexOf('id="panel-merch"');
    assert.ok(at > 0, 'the merch panel is gone');
    const panel = codeOnly.slice(at, at + 3000);
    assert.ok(/openItemPriceList\('casket'\)/.test(panel), 'no CPL button on the panel');
    assert.ok(/openItemPriceList\('obc'\)/.test(panel), 'no OBCPL button on the panel');
  });
test('F2. the OBC kind still names BOTH source categories', () => {
  const v = grabVar('IPL_KINDS');
  assert.ok(/'Outer Burial Container', 'Vault'/.test(v),
    'the vault mapping was changed: ' + v.replace(/\s+/g, ' ').slice(0, 220));
});
test('F3. CONTROL: the stripped source is real code, so F1 is not vacuous',
  () => {
    assert.ok(codeOnly.length > 100000, 'got ' + codeOnly.length + ' chars');
  });

let unhandled = 0;
process.on('unhandledRejection', (e) => {
  unhandled++; console.log('  FAIL unhandled rejection: ' + (e && e.message));
});
runQueue(QUEUE, (s) => console.log(s)).then(async (r) => {
  pass = r.pass; fail = r.fail;
  await new Promise((res) => setImmediate(res));
  const queued = QUEUE.filter(([, fn]) => fn).length;
  const problems = [];
  if (unhandled) problems.push(unhandled + ' unhandled rejection(s)');
  if (pass + fail !== queued) problems.push(queued + ' queued but ' + (pass + fail) + ' tallied');
  if (problems.length) {
    console.log('\nRESULT WITHHELD -- ' + problems.join('; '));
    console.log(pass + ' passed, ' + (fail + unhandled) + ' failed');
    process.exit(1);
  }
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  if (fail) process.exit(1);
});
