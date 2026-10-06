// tests/sairndesign_po_procurement.js
//
// Run:  node tests/sairndesign_po_procurement.js
//
// REQUIREMENT (closes findings 2 and 3 of
// docs/cloud-research/sairndesign-competitive-gap-audit-2026-10-05.md):
// a purchase order must carry the middle of the procurement chain -- a
// SIDEMARK and a SHIP-TO so a vendor can route it, a FREIGHT figure so the
// landed cost is real, and a RECEIVING record with a date. And none of those
// may be invented by the software.
//
// The audit's own words: "SAIRNdesign has the two ends -- PO and markup -- and
// NONE of the three middle steps, and the absent one with a name a buyer will
// ask about is FREIGHT... `sidemark` IS THE SHARPEST SINGLE ABSENCE and it is a
// one-word test."
//
// ── THE SPANS ARE BRACE-BOUNDED ───────────────────────────────────────────
// Extraction uses tests/lib/fn_span.js. Five arms across four suites were
// repointed on 2026-10-06 (`d8392f80`) because they bounded a function body
// with a byte window or the next symbol in the file, and a suite written the
// same day with a `+ 2000` window would be the sixth.
'use strict';

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');
const { fnBody } = require('./lib/fn_span.js');

const ROOT = path.join(__dirname, '..');
const APP = fs.readFileSync(path.join(ROOT, 'sairndesign.html'), 'utf8');

let pass = 0;
let fail = 0;
function t(name, fn) {
  try { fn(); pass++; console.log('  ok   ' + name); }
  catch (e) { fail++; console.log('  FAIL ' + name + '\n       ' + e.message); }
}

const ctx = { isFinite: isFinite, Number: Number, String: String, Array: Array,
              Object: Object, JSON: JSON };
vm.createContext(ctx);
['function sdnPoLanded(po){', 'function sdnPoRoutingGaps(po){']
  .forEach(function (s) { vm.runInContext(fnBody(APP, s), ctx); });

// Values crossing out of a vm carry that realm's prototypes, so deepStrictEqual
// fails on structurally identical arrays. JSON round-trip, not loose equality --
// loose would also stop noticing a string where a number belongs.
function plain(v) { return JSON.parse(JSON.stringify(v)); }
const landed = (po) => plain(ctx.sdnPoLanded(po));
const gaps = (po) => plain(ctx.sdnPoRoutingGaps(po));

console.log('\nA. a freight that is not entered is UNKNOWN, never zero');

t('A1. no freight -> landed is null and says which part is missing', function () {
  const L = landed({ total_cost: 12000, freight_cost: null });
  assert.strictEqual(L.landed, null, 'a landed total was computed without a freight figure');
  assert.deepStrictEqual(L.unknowns, ['freight']);
});

['', undefined, null, 'soon'].forEach(function (bad, i) {
  t('A2.' + (i + 1) + ' freight ' + JSON.stringify(bad) + ' -> UNKNOWN, not 0', function () {
    const L = landed({ total_cost: 12000, freight_cost: bad });
    assert.strictEqual(L.freight, null, 'freight ' + JSON.stringify(bad) + ' became ' + L.freight);
    assert.strictEqual(L.landed, null);
  });
});

t('A3. a real 0 freight IS a figure -- free shipping must be sayable', function () {
  const L = landed({ total_cost: 12000, freight_cost: 0 });
  assert.strictEqual(L.freight, 0);
  assert.strictEqual(L.landed, 12000);
  assert.deepStrictEqual(L.unknowns, []);
});

t('A4. goods + freight, and goods is NOT altered', function () {
  const po = { total_cost: 12000, freight_cost: 850 };
  const L = landed(po);
  assert.strictEqual(L.goods, 12000);
  assert.strictEqual(L.landed, 12850);
  assert.strictEqual(po.total_cost, 12000, 'the helper mutated total_cost');
});

t('A5. an unreadable goods total is UNKNOWN too, not 0', function () {
  const L = landed({ total_cost: undefined, freight_cost: 100 });
  assert.strictEqual(L.goods, null);
  assert.strictEqual(L.landed, null);
  assert.deepStrictEqual(L.unknowns, ['goods']);
});

console.log('\nB. routing -- the sidemark one-word test');

t('B1. no sidemark and no ship-to -> both named', function () {
  assert.deepStrictEqual(gaps({}), ['no sidemark', 'no ship-to']);
});

t('B2. whitespace is not a sidemark', function () {
  assert.deepStrictEqual(gaps({ sidemark: '   ', ship_to: 'Warehouse' }), ['no sidemark']);
});

t('B3. both present -> no gaps', function () {
  assert.deepStrictEqual(gaps({ sidemark: 'HALLORAN / LIVING RM', ship_to: 'Receiving' }), []);
});

console.log('\nC. the app USES it -- an engine with no caller is the SAIRNmechanical defect');

t('C1. a generated PO carries the procurement fields, all EMPTY', function () {
  const body = fnBody(APP, 'async function generatePOs(){');
  ['sidemark', 'ship_to', 'freight_cost', 'expected_date', 'received_date', 'received_by']
    .forEach(function (f) {
      assert.ok(body.indexOf(f + ':') !== -1, 'the new PO record has no ' + f);
    });
  assert.ok(/freight_cost\s*:\s*null/.test(body),
    'freight_cost is seeded with something other than null -- a seeded 0 is a '
    + 'freight figure nobody quoted');
  assert.ok(/sidemark\s*:\s*''/.test(body),
    'a sidemark is pre-filled. A sidemark this app invented is a routing string '
    + 'the vendor cannot match');
});

t('C2. total_cost STILL means goods only, and freight is a separate field', function () {
  const body = fnBody(APP, 'async function generatePOs(){');
  const m = body.match(/total_cost:\s*items\.reduce\([^)]*\)/);
  assert.ok(m, 'total_cost is no longer a plain sum of item costs');
  assert.ok(!/freight/.test(m[0]),
    'freight was folded into total_cost -- rPOs() sums that field into the '
    + 'Total Committed KPI, so the meaning of an existing figure would change '
    + 'silently');
});

t('C3. the panel KPI label says goods only', function () {
  assert.ok(/GOODS ONLY/.test(APP),
    'the Total Committed KPI does not say it excludes freight');
});

t('C4. receiving REFUSES without a date', function () {
  const body = fnBody(APP, 'async function receivePO(id){');
  assert.ok(/if\(!when\)\{/.test(body.replace(/\s/g, '')),
    'receivePO does not refuse an empty date');
  assert.ok(/not a receipt/.test(body),
    'the refusal does not say why, so it reads as a validation nag');
  assert.ok(!/sdnLocalToday\(\)/.test(body),
    'the received date defaults to today -- a receipt dated by the software is '
    + 'the fabricated fact this arm exists for');
});

t('C5. Mark Received is NOT reachable without going through receivePO', function () {
  const body = fnBody(APP, 'function openPODetail(id){');
  assert.ok(!/setPOStatus\([^)]*'Received'/.test(body),
    'the old one-click Mark Received is still wired, so the date refusal can be '
    + 'walked around');
});

t('C6. routing gaps are counted on the PANEL, not only inside the modal', function () {
  const body = fnBody(APP, 'function rPOs(){');
  assert.ok(/sdnPoRoutingGaps\(/.test(body), 'rPOs does not count unroutable POs');
  assert.ok(/sdnPoLanded\(/.test(body), 'the list has no landed column');
  assert.ok(APP.indexOf('id="po-routing"') !== -1, 'the panel has no routing status line');
});

t('C7. the landed column renders a DASH, never $0, when freight is unknown', function () {
  const body = fnBody(APP, 'function rPOs(){');
  // MATCHED ON RAW TEXT. The first version stripped whitespace first, which
  // also removed the space inside the string literal `<span style=...>` and
  // could never match -- the same quote-masking mistake convention 13 and 14
  // in docs/2026-09-13-cross-domain-disciplines.md were adopted for, hit again
  // in the hour after writing them.
  // `[^:]*` was the SECOND wrong version of this arm: the text between the `?`
  // and the dash contains a colon, inside `color:var(--muted)`. Two wrong
  // matchers for one three-token assertion, both of them wrong about a STRING
  // LITERAL rather than about the code. Recorded rather than quietly fixed.
  assert.ok(/L\.landed\s*===\s*null\s*\?[\s\S]*?--<\/span>'\s*:\s*fmt\(L\.landed\)/.test(body),
    'an unknown landed cost renders as a currency figure');
});

t('C8. the table head and the colspan agree with the 9 columns', function () {
  const head = APP.slice(APP.indexOf('<tbody id="potbody">') - 900,
                         APP.indexOf('<tbody id="potbody">'));
  const ths = (head.match(/<th>/g) || []).length;
  assert.strictEqual(ths, 9, 'the PO table head has ' + ths + ' columns, not 9');
  const body = fnBody(APP, 'function rPOs(){');
  assert.ok(/colspan="9"/.test(body),
    'the empty-state colspan does not match the 9 columns, so the "no purchase '
    + 'orders yet" row would not span the table');
});

console.log('\nD. sales tax is REFUSED and the refusal is on screen');

t('D1. the app still computes no tax -- the capability is absent, deliberately', function () {
  const code = APP.replace(/<!--[\s\S]*?-->/g, '');     // comments are not code
  assert.ok(!/tax_rate|taxable|calcTax|salesTax/i.test(code),
    'a tax calculation appeared. The audit\'s finding 1 is that this app must '
    + 'NOT pick a rate for a reseller\'s client invoice');
});

t('D2. ...and the absence is DISCLOSED rather than silent', function () {
  assert.ok(/does not calculate sales tax, and will not/.test(APP),
    'nothing on screen tells a designer that tax is out of scope, so they meet '
    + 'the boundary in week one instead of on the panel');
  assert.ok(/resale certificate/i.test(APP),
    'the disclosure does not name the reseller mechanic it rests on');
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
