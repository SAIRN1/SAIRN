// tests/vendor_order_delete.js
//
// Run:  node tests/vendor_order_delete.js
//
// The Spend Report showed YTD spend, spend by vendor, spend by category and
// spend by month -- every one of them an AGGREGATE of sd_order_history -- and
// nothing listed the orders those aggregates are made of. A shop could read
// "$41,200 with GMR Stone" and had no way to check which orders that was, or to
// remove one placed twice.
//
// ── THIS ONE IS DIFFERENT FROM THE OTHER LOGS, TWICE OVER ─────────────────
// 1. IT WAS ALREADY BACKED UP. vendorPlaceOrder() has always set
//    `id: 'ORD'+Date.now()`, so these rows pass sdSyncCollection()'s id check.
//    The comms, SMS, VeinMatch, SeamAI, email-threat and snapshot logs all
//    failed it; this one never did, and claiming otherwise in a comment would
//    have been a confident wrong statement of exactly the kind this file keeps
//    correcting. The back-fill here is DEFENSIVE and a no-op on every record
//    the app itself wrote.
// 2. IT IS SUMMED. Deleting an order moves YTD spend, spend-by-vendor,
//    spend-by-category and the figures handed to the AI analysis. So the
//    confirm says so, and an arm pins that it does -- a shop is entitled to
//    remove an order entered twice, and entitled to know the report will read
//    differently afterwards rather than discovering it.

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
  assert.ok(i > 0, 'not found: ' + decl);
  return balanced(i);
}

const ORDERS = [
  { id: 'ORD1', date: '2026-09-10T09:00:00.000Z', vendor: 'GMR Stone', total: 1200,
    items: [{ cat: 'abrasives', price: 600, qty: 2 }] },
  { id: 'ORD2', date: '2026-09-11T09:00:00.000Z', vendor: 'Granquartz', total: 800,
    items: [{ cat: 'blades', price: 800, qty: 1 }] }
];

// `ctx` is a PARAMETER of the generated function, not a closure over this
// scope: without it the `ctx.ensure = ...` lines inside would create a global
// in the sandbox and this harness would hand back nothing to call.
function build(orders, opts) {
  opts = opts || {};
  const out = { toasts: [], confirms: [], writes: [], reports: 0,
                els: { 'vendor-order-list': { innerHTML: '' } } };
  const ctx = {};
  const src =
    balanced(html.indexOf('function sdRowId(prefix,row,fields){')) + '\n' +
    balanced(html.indexOf('function sdEnsureRowIds(rows,prefix,fields){')) + '\n' +
    'var sdOrderHistory=' + JSON.stringify(orders) + ';\n' +
    'function vendorSpendReport(){ out.reports++; vendorRenderOrders(); }\n' +
    fn('function vendorEnsureOrderIds(){') + '\n' +
    fn('function vendorRenderOrders(){') + '\n' +
    fn('function vendorOrderDelete(id){') + '\n' +
    'ctx.ensure=vendorEnsureOrderIds; ctx.render=vendorRenderOrders;'
    + 'ctx.del=vendorOrderDelete; ctx.orders=function(){return sdOrderHistory;};';
  new Function('st', 'document', 'escHtml', 'escAttrJs', 'notify', 'confirm', 'out', 'ctx', src)(
    (k, v) => { out.writes.push(k); if (opts.saveFails) return false; return true; },
    { getElementById: id => out.els[id] || null },
    s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'),
    s => String(s),
    (m, kind) => out.toasts.push({ m: String(m), kind }),
    m => { out.confirms.push(String(m)); return opts.confirm !== false; },
    out, ctx
  );
  return { ctx, out };
}

(function main() {
  console.log('StoneDesk vendor orders -- the rows behind the spend figures\n');

  section('the list the aggregates were made of');

  test('every order is listed, with a Delete', () => {
    const b = build(ORDERS);
    b.ctx.render();
    const h = b.out.els['vendor-order-list'].innerHTML;
    assert.ok(h.indexOf('GMR Stone') !== -1 && h.indexOf('Granquartz') !== -1,
      'the orders behind the totals are still invisible: ' + h.slice(0, 160));
    assert.strictEqual((h.match(/onclick="vendorOrderDelete\(/g) || []).length, 2);
  });

  test('an empty history says so', () => {
    const b = build([]);
    b.ctx.render();
    assert.ok(/No orders placed yet/.test(b.out.els['vendor-order-list'].innerHTML));
  });

  test('a vendor name is escaped, not rendered', () => {
    const b = build([Object.assign({}, ORDERS[0], { vendor: '<img src=x onerror=1>' })]);
    b.ctx.render();
    const h = b.out.els['vendor-order-list'].innerHTML;
    assert.ok(h.indexOf('<img src=x') === -1 && h.indexOf('&lt;img') !== -1);
  });

  // THE DIFFERENCE FROM EVERY OTHER LOG IN THIS SET.
  test('these rows ALREADY had ids -- the back-fill writes nothing', () => {
    const b = build(ORDERS);
    b.out.writes.length = 0;
    const d = b.ctx.ensure();
    assert.deepStrictEqual(d.map(x => x.id), ['ORD1', 'ORD2']);
    assert.strictEqual(b.out.writes.length, 0,
      'the defensive back-fill rewrote records that were already fine');
  });

  test('but a row that somehow has none still gets one', () => {
    const b = build([{ date: '2026-09-12T09:00:00.000Z', vendor: 'X', total: 1, items: [] }]);
    const d = b.ctx.ensure();
    assert.ok(String(d[0].id).startsWith('PO-'), String(d[0].id));
    assert.strictEqual(b.out.writes.length, 1, 'the fixed record was not persisted');
  });

  section('deleting an order, and saying what else moves');

  test('deleting removes it and rebuilds the report', () => {
    const b = build(ORDERS);
    b.ctx.del('ORD1');
    assert.deepStrictEqual(b.ctx.orders().map(x => x.id), ['ORD2']);
    assert.ok(b.out.reports >= 1, 'the spend figures were not recomputed');
  });

  // THE ARM THIS FILE EXISTS FOR. Every other confirm in this run says "hidden
  // and kept". This one has to say that AND that the numbers move.
  test('the confirm says the spend figures will drop', () => {
    const b = build(ORDERS, { confirm: false });
    b.ctx.del('ORD1');
    const m = b.out.confirms[0] || '';
    assert.ok(/hidden and kept, not destroyed/.test(m), m);
    assert.ok(/YTD spend/.test(m) && /drop/.test(m),
      'the confirm does not warn that the spend report will read differently: ' + m);
    assert.ok(!/cannot be undone/i.test(m));
  });

  test('declining changes nothing', () => {
    const b = build(ORDERS, { confirm: false });
    b.ctx.del('ORD1');
    assert.strictEqual(b.ctx.orders().length, 2);
  });

  test('an id matching nothing never asks and never writes', () => {
    const b = build(ORDERS);
    b.ctx.ensure();
    b.out.writes.length = 0;
    b.ctx.del('ORD-NO-SUCH');
    assert.strictEqual(b.out.confirms.length, 0);
    assert.strictEqual(b.out.writes.length, 0);
  });

  test('an empty id is refused with a sentence, before the confirm', () => {
    const b = build(ORDERS);
    b.ctx.del('');
    assert.ok(/no id yet/.test((b.out.toasts[0] || {}).m || ''));
    assert.strictEqual(b.out.confirms.length, 0);
  });

  // A FAILED SAVE MUST NOT LEAVE THE IN-MEMORY LIST SHORT while the stored one
  // still holds the order -- the next load would bring it back and the spend
  // figures would jump again.
  test('a storage failure is reported, with no success toast', () => {
    const b = build(ORDERS, { saveFails: true });
    b.ctx.del('ORD1');
    const msgs = b.out.toasts.map(t => t.m).join('|');
    assert.ok(/Could not delete that order/.test(msgs), msgs);
    assert.ok(!/Order deleted/.test(msgs));
  });

  test('the Spend Report renders the list it now has', () => {
    const report = fn('function vendorSpendReport() {');
    assert.ok(/id="vendor-order-list"/.test(report), 'the container is gone');
    assert.ok(/vendorRenderOrders\(\);/.test(report),
      'nothing fills the list, so it would render empty for ever');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  if (fail) process.exit(1);
})();
