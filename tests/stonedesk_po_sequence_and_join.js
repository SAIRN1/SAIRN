// tests/stonedesk_po_sequence_and_join.js
//
// Run:  node tests/stonedesk_po_sequence_and_join.js
//
// THREE DEFECTS ON THE STONEDESK PURCHASING PATH, each asserted against the
// shipped source rather than a reimplementation of it.
//
// 1. THE PO NUMBER WAS A COUNT, NOT A SEQUENCE.
//    `'PO-2024-0' + (50 + d.length)` -- derived from the array's LENGTH, so
//    deleting any PO made the next one REUSE a number already issued. A PO
//    number that is not unique is not a PO number: it is the key a receipt and
//    a vendor bill are matched on, and two POs sharing one makes the match
//    ambiguous in exactly the place it exists to be unambiguous. The year was
//    hardcoded to 2024 as well.
//
// 2. NOTHING JOINED THE THREE DOCUMENTS.
//    StoneDesk shipped all three legs -- purchase orders (sd_pos), receiving
//    (sd_receiving), vendor bills (sd_ap) -- and not one field linked any of
//    them to either of the others. The match was not unenforced; it was
//    UNCONSTRUCTIBLE. `po_num` is now on the receipt and on the bill.
//
// 3. `ap-due` IS THE KPI DIV, NOT THE DATE INPUT.
//    sdAPAdd() read `getElementById('ap-due').value`. That id belongs to the
//    "Due This Week" KPI; the input is `ap-due-date`. Reading `.value` off a
//    div is undefined, so the `||` fired and EVERY BILL SILENTLY TOOK TODAY AS
//    ITS DUE DATE -- and Due This Week and OVERDUE were then computed from a
//    date nobody chose. NOT A CRASH, which is why it survived: the id really
//    exists, so missing_dom_target_check.py has nothing to say. It checks that
//    a target exists, not that it is the right KIND of element.
//
// The functions are extracted from the real stonedesk.html and driven.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const HTML = fs.readFileSync(process.env.SD_HTML || path.join(ROOT, 'stonedesk.html'),
                             'utf8').replace(/\r\n/g, '\n');

let n = 0;
function ok(cond, label) { assert.ok(cond, label); n++; console.log('  ok   ' + label); }

function grab(sig) {
  const start = HTML.indexOf(sig);
  assert.ok(start > 0, 'not found in stonedesk.html: ' + sig);
  let i = HTML.indexOf('{', start + sig.length - 1), depth = 0, q = null;
  for (; i < HTML.length; i++) {
    const c = HTML[i], p = HTML[i - 1];
    if (q) { if (c === q && p !== '\\') q = null; continue; }
    if (c === '"' || c === "'" || c === '`') { q = c; continue; }
    if (c === '/' && HTML[i + 1] === '/') { i = HTML.indexOf('\n', i); continue; }
    if (c === '/' && HTML[i + 1] === '*') { i = HTML.indexOf('*/', i) + 1; continue; }
    if (c === '{') depth++;
    else if (c === '}') { depth--; if (!depth) return HTML.slice(start, i + 1); }
  }
  throw new Error('unterminated: ' + sig);
}

// A stripper that CANNOT remove executable code: it drops only lines whose
// trimmed form STARTS with `//`, which are comments in their entirety. The
// general form of this -- blanking from any `//` to end of line -- is what
// swallowed every https:// in comment_quote_check.py's first version, and a
// stripper that over-reaches makes an ABSENCE assertion pass while the defect
// is present, which is the unsafe direction. Three assertions in this file
// went red on the fix's own explanatory comments before this existed: PR 1.2,
// four times in one session, now in the test rather than the tool.
function codeOnly(src) {
  return src.split(String.fromCharCode(10))
            .filter(l => !l.trim().startsWith('//'))
            .join(String.fromCharCode(10));
}

function ctxWith(store, els) {
  const ctx = {
    console: console,
    localStorage: {
      getItem: k => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); }
    },
    store: store,
    stFails: false,
    showToast: () => {},
    sdLocalToday: () => '2026-09-14',
    document: { getElementById: id => (id in els ? els[id] : null) },
    st: function (k, v) {
      if (ctx.stFails) return false;
      store[k] = JSON.stringify(v);
      return true;
    }
  };
  vm.createContext(ctx);
  vm.runInContext('window = this;', ctx);
  return ctx;
}

console.log('StoneDesk purchasing: a real sequence, and three documents that join\n');

// ── 1. THE SEQUENCE ──────────────────────────────────────────────────────────
console.log('1. the PO number is a sequence, not a count');
{
  const store = {};
  const ctx = ctxWith(store, {});
  vm.runInContext('var PO_SEQ_KEY="sd_po_seq";'
    + 'function poSeqLoad(){try{var s=JSON.parse(localStorage.getItem(PO_SEQ_KEY)||"{}");'
    + 'return (s&&typeof s==="object")?s:{};}catch(e){return {};}}', ctx);
  vm.runInContext(grab('window.sdPONextNum=function(rows,year){'), ctx);

  const rows = [{ num: 'PO-2026-001' }, { num: 'PO-2026-002' }, { num: 'PO-2026-003' }];
  const a = ctx.window.sdPONextNum(rows, '2026');
  ok(a === 'PO-2026-004', 'the next number follows the highest issued (' + a + ')');

  // THE ARM THAT IS THE WHOLE POINT: delete one and the next must NOT reuse it.
  const afterDelete = [rows[0], rows[2]];          // 002 deleted
  const b = ctx.window.sdPONextNum(afterDelete, '2026');
  ok(b === 'PO-2026-005', 'after a DELETE the next number does not reuse one (' + b + ')');
  ok(b !== a, '...and does not repeat the previous issue either');

  const c = ctx.window.sdPONextNum([], '2026');
  ok(c === 'PO-2026-006', 'and an EMPTY store still advances -- the counter is persistent');

  ok(JSON.parse(store.sd_po_seq)['2026'] === 6,
     'the counter really is persisted, not recomputed from the rows');
}
{
  // The year comes from the clock, and a new year starts its own sequence.
  const ctx = ctxWith({}, {});
  vm.runInContext('var PO_SEQ_KEY="sd_po_seq";'
    + 'function poSeqLoad(){try{var s=JSON.parse(localStorage.getItem(PO_SEQ_KEY)||"{}");'
    + 'return (s&&typeof s==="object")?s:{};}catch(e){return {};}}', ctx);
  vm.runInContext(grab('window.sdPONextNum=function(rows,year){'), ctx);
  const v = ctx.window.sdPONextNum([], undefined);
  ok(v === 'PO-2026-001', 'the year is read from the clock, not hardcoded (' + v + ')');
  // ASSERTED AGAINST THE FUNCTION BODY, NOT THE FILE, AND THAT IS THE POINT.
  // The first version of this arm searched the whole file and went red on the
  // COMMENT explaining what the old code was -- PR 1.2, "grep cannot tell code
  // from text that describes code", committed in an assertion. The grabbed body
  // is code by construction, so no stripper is needed and no explanation has to
  // be deleted to make a test pass.
  ok(codeOnly(grab('window.sdPOCreate=function(){')).indexOf('PO-2024') === -1,
     "the hardcoded 'PO-2024' is gone from sdPOCreate's code");
  ok(codeOnly(grab('window.sdPONextNum=function(rows,year){')).indexOf('d.length') === -1,
     "and sdPONextNum's code does not derive a number from the row count");

  // The seed rows are PO-2024-038..041; a 2026 sequence must ignore them.
  const w = ctx.window.sdPONextNum([{ num: 'PO-2024-041' }], '2026');
  ok(w === 'PO-2026-002', "another year's numbers do not raise this year's sequence");
}
{
  // A FAILED RESERVATION REFUSES. Issuing a number the sequence never stored
  // would make the next call collide with it.
  const ctx = ctxWith({}, {});
  vm.runInContext('var PO_SEQ_KEY="sd_po_seq";'
    + 'function poSeqLoad(){try{var s=JSON.parse(localStorage.getItem(PO_SEQ_KEY)||"{}");'
    + 'return (s&&typeof s==="object")?s:{};}catch(e){return {};}}', ctx);
  vm.runInContext(grab('window.sdPONextNum=function(rows,year){'), ctx);
  ctx.stFails = true;
  ok(ctx.window.sdPONextNum([], '2026') === null,
     'a failed write returns null rather than a number nothing recorded');
}

// ── 2. THE JOIN ──────────────────────────────────────────────────────────────
console.log('\n2. the three documents can be joined');
function el(v) { return { value: v }; }
{
  const store = {};
  const els = {
    'recv-mat': el('Calacatta Gold 3cm'), 'recv-qty': el('4'), 'recv-val': el('2800'),
    'recv-vendor': el('Stone World Supply'), 'recv-cond': el('Perfect'),
    'recv-notes': el(''), 'recv-po': el('PO-2026-004')
  };
  const ctx = ctxWith(store, els);
  vm.runInContext('function load(){try{return JSON.parse(localStorage.getItem("sd_receiving")||"[]");}catch(e){return [];}}'
    + 'function save(d){return st("sd_receiving",d);} function render(){}', ctx);
  vm.runInContext(grab('window.sdRecvLog=function(){'), ctx);
  ctx.window.sdRecvLog();
  const row = JSON.parse(store.sd_receiving)[0];
  ok(row.po_num === 'PO-2026-004', 'a receipt carries the PO number it answers');
  ok(row.val === 2800, '...and still carries its OWN value, independently entered');
  ok(els['recv-po'].value === '', '...and the field is cleared afterwards');
}
{
  const store = {};
  const els = {
    'ap-vendor': el('Stone World Supply'), 'ap-desc': el('Calacatta Gold x4'),
    'ap-amt': el('2800'), 'ap-due-date': el('2026-10-15'), 'ap-po': el('PO-2026-004'),
    'ap-due': { textContent: '$0' }        // the KPI div, no .value -- as shipped
  };
  const ctx = ctxWith(store, els);
  vm.runInContext('function load(){try{return JSON.parse(localStorage.getItem("sd_ap")||"[]");}catch(e){return [];}}'
    + 'function save(d){return st("sd_ap",d);} function render(){}', ctx);
  vm.runInContext(grab('window.sdAPAdd=function(){'), ctx);
  ctx.window.sdAPAdd();
  const bill = JSON.parse(store.sd_ap)[0];
  ok(bill.po_num === 'PO-2026-004', 'a vendor bill carries the PO number it answers');

  // ── 3. THE DUE DATE ────────────────────────────────────────────────────────
  ok(bill.due === '2026-10-15',
     'THE DUE DATE THE USER TYPED IS STORED, not silently replaced with today');
  ok(bill.due !== '2026-09-14', '...and it is not today');
  ok(els['ap-due-date'].value === '', 'the real date input is cleared afterwards');
  ok(els['ap-due'].textContent === '$0', '...and the KPI div is left alone');
}
{
  // CONTROL: the old read really did produce today. Without this the arm above
  // is asserting a property of the fixture rather than of the fix.
  const els = { 'ap-due': { textContent: '$0' }, 'ap-due-date': el('2026-10-15') };
  const wrong = els['ap-due'].value || '2026-09-14';
  ok(wrong === '2026-09-14',
     'CONTROL: reading .value off the KPI div yields undefined, so the || fires');
  // Function body again, for the same reason: the fix's own comment quotes the
  // read it replaced, and a file-wide match finds the explanation.
  ok(codeOnly(grab('window.sdAPAdd=function(){')).indexOf("getElementById('ap-due').value") === -1,
     "and that read is gone from sdAPAdd's code");
  ok(codeOnly(grab('window.sdAPAdd=function(){')).indexOf("getElementById('ap-due-date').value") !== -1,
     "...replaced by a read of the real date input");
}
{
  // An optional field must stay optional: a bill or a receipt with no PO is a
  // real thing -- a utility bill, stock arriving unordered -- and refusing it
  // would get the field filled with something untrue.
  const store = {};
  const els = {
    'ap-vendor': el('Shop Utilities'), 'ap-desc': el('Electric'), 'ap-amt': el('820'),
    'ap-due-date': el('2026-10-01'), 'ap-po': el(''), 'ap-due': { textContent: '$0' }
  };
  const ctx = ctxWith(store, els);
  vm.runInContext('function load(){try{return JSON.parse(localStorage.getItem("sd_ap")||"[]");}catch(e){return [];}}'
    + 'function save(d){return st("sd_ap",d);} function render(){}', ctx);
  vm.runInContext(grab('window.sdAPAdd=function(){'), ctx);
  ctx.window.sdAPAdd();
  ok(JSON.parse(store.sd_ap)[0].po_num === '',
     'a bill with no PO is still accepted -- the key is optional by design');
}

// ── 4. THE FORM FIELDS REALLY EXIST ──────────────────────────────────────────
console.log('\n4. the inputs the handlers read are in the markup');
for (const id of ['recv-po', 'ap-po', 'ap-due-date']) {
  ok(HTML.indexOf('id="' + id + '"') !== -1, 'id="' + id + '" is in the markup');
}
ok((HTML.match(/id="ap-due"/g) || []).length === 1,
   'id="ap-due" still appears exactly once -- it is the KPI and nothing else');

console.log('\nALL ' + n + ' ASSERTIONS PASS');
