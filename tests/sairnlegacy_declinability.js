// tests/sairnlegacy_declinability.js
//
// Run:  node tests/sairnlegacy_declinability.js
//
// REQUIREMENT (closes F2 of
// docs/cloud-research/sairnlegacy-competitive-gap-audit-2026-10-05.md):
// `leg_invoices` must be able to distinguish an item a family DECLINED from
// one that was never offered. The Funeral Rule's substance is the right to
// decline individual items; 16 CFR 453.2(b)(5) requires a written statement
// of the goods and services SELECTED for every arrangement, and a decline
// that leaves no trace makes that statement unverifiable.
//
// ── WHY THE LOGIC IS IN THE APP AND THIS SUITE EXTRACTS IT ────────────────
// A browser single-file app cannot `require()` an api/_lib module, and the
// first draft of this work DID put the composer in `api/_lib/legacy-statement.js`
// -- which would have meant TWO copies of the rules, one tested and one
// shipped, which is item 7 of docs/2026-09-13-cross-domain-disciplines.md
// (byte-identical is not safe-in-context) arriving by the front door. One
// copy, in the app, driven from the app file. That is the shape the platform
// already uses for panel logic and the shape the SAIRNsenior B3 spot-verify
// note describes.
//
// ── THE SPANS ARE BRACE-BOUNDED, DELIBERATELY ─────────────────────────────
// Extraction uses tests/lib/fn_span.js rather than a byte window or a
// next-function bound. Five arms across four suites were repointed on
// 2026-10-06 for exactly that defect (`d8392f80`), and a suite written the
// same day with a `+ 2000` window would be the sixth.
'use strict';

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');
const { fnBody } = require('./lib/fn_span.js');

const ROOT = path.join(__dirname, '..');
const APP = fs.readFileSync(path.join(ROOT, 'sairnlegacy.html'), 'utf8');

let pass = 0;
let fail = 0;
function t(name, fn) {
  try { fn(); pass++; console.log('  ok   ' + name); }
  catch (e) { fail++; console.log('  FAIL ' + name + '\n       ' + e.message); }
}

// ── EXTRACT THE COMPOSER, BY ITS OWN BRACES ───────────────────────────────
const SIGS = [
  'function legPriceOf(v){',
  'function legProblem(code,severity,detail){',
  'function legComposeStatement(input){',
  'function legInvoiceFields(statement){'
];
const ctx = { LEG_SELECTED: 'selected', LEG_DECLINED: 'declined',
              isFinite: isFinite, Number: Number, Object: Object,
              Array: Array, Error: Error, JSON: JSON };
vm.createContext(ctx);
SIGS.forEach(function (s) { vm.runInContext(fnBody(APP, s), ctx); });

// Values crossing back out of the vm carry the VM REALM'S prototypes, so
// `deepStrictEqual` fails on an array that is structurally identical --
// "Values have same structure but are not reference-equal". Round-tripping
// through JSON gives host-realm plain data. Doing this rather than switching
// to loose deepEqual on purpose: loose equality would also stop noticing a
// string where a number belongs, which is half of what these arms check.
function plain(v) { return JSON.parse(JSON.stringify(v)); }
function compose(input) { return plain(ctx.legComposeStatement(input)); }
function fieldsOf(st) { return plain(ctx.legInvoiceFields(st)); }
function codes(st) { return st.problems.map(function (p) { return p.code; }).sort(); }
function refusals(st) {
  return st.problems.filter(function (p) { return p.severity === 'refuse'; })
    .map(function (p) { return p.code; }).sort();
}

// The seeded price list, trimmed. Shapes match sairnlegacy.html's
// leg_gplservices and leg_merch_catalog seeds.
const OFFERED = [
  { id: 'GS-1', label: 'Basic Services of Funeral Director and Staff', price: 2495, kind: 'service' },
  { id: 'GS-2', label: 'Embalming', price: 895, kind: 'service' },
  { id: 'GS-5', label: 'Use of Facilities/Staff for Viewing', price: 595, kind: 'service' },
  { id: 'MU-2', label: 'Cambridge Oak, 18 Gauge (CO18G-0002)', price: 3400, kind: 'merchandise' }
];

console.log('\nA. the distinction F2 names: declined is not never-offered');

t('A1. a declined line lands in `declined`, not in `notOffered`', function () {
  const st = compose({ offered: OFFERED,
    selections: { 'GS-1': 'selected', 'GS-2': 'declined' }, nonDeclinable: ['GS-1'] });
  assert.deepStrictEqual(st.declined.map(function (r) { return r.id; }), ['GS-2']);
  assert.ok(st.notOffered.every(function (r) { return r.id !== 'GS-2'; }),
    'the declined line also appeared in notOffered');
});

t('A2. a line nobody touched lands in `notOffered`, not in `declined`', function () {
  const st = compose({ offered: OFFERED, selections: { 'GS-1': 'selected' },
    nonDeclinable: ['GS-1'] });
  assert.deepStrictEqual(st.notOffered.map(function (r) { return r.id; }).sort(),
    ['GS-2', 'GS-5', 'MU-2']);
  assert.deepStrictEqual(st.declined, []);
});

t('A3. CONTROL: the two cases genuinely differ, so A1/A2 are not both satisfied '
  + 'by putting everything in both lists', function () {
  const declinedCase = compose({ offered: OFFERED,
    selections: { 'GS-1': 'selected', 'GS-2': 'declined' }, nonDeclinable: ['GS-1'] });
  const untouchedCase = compose({ offered: OFFERED,
    selections: { 'GS-1': 'selected' }, nonDeclinable: ['GS-1'] });
  assert.notDeepStrictEqual(
    declinedCase.declined.map(function (r) { return r.id; }),
    untouchedCase.declined.map(function (r) { return r.id; }),
    'the composed shape is the SAME whether a line was declined or never '
    + 'offered -- which is the defect, not the fix');
});

t('A4. and the STORED fields differ too, which is where F2 actually bit', function () {
  const a = fieldsOf(compose({ offered: OFFERED,
    selections: { 'GS-1': 'selected', 'GS-2': 'declined' }, nonDeclinable: ['GS-1'] }));
  const b = fieldsOf(compose({ offered: OFFERED,
    selections: { 'GS-1': 'selected' }, nonDeclinable: ['GS-1'] }));
  assert.deepStrictEqual(a.line_items, b.line_items,
    'the two cases should agree on what was SELECTED');
  assert.notDeepStrictEqual(a.declined_items, b.declined_items,
    'the two cases produce the same stored record -- a decline still leaves '
    + 'no trace, which is F2 unfixed');
});

console.log('\nB. 16 CFR 453.2(b)(4)(iii)(C) permits exactly one non-declinable charge');

t('B1. none marked -> DISCLOSE, and the document still prints', function () {
  const st = compose({ offered: OFFERED, selections: { 'GS-1': 'selected' }, nonDeclinable: [] });
  assert.ok(codes(st).indexOf('NO_NON_DECLINABLE_MARKED') >= 0);
  assert.strictEqual(st.printable, true,
    'an unmarked basic-services fee is incomplete, not false -- blocking the '
    + 'document would make the honest state unusable');
});

t('B2. two marked -> REFUSE', function () {
  const st = compose({ offered: OFFERED, selections: { 'GS-1': 'selected' },
    nonDeclinable: ['GS-1', 'GS-2'] });
  assert.deepStrictEqual(refusals(st), ['MULTIPLE_NON_DECLINABLE']);
  assert.strictEqual(st.printable, false);
});

t('B3. one marked -> no problem about it at all', function () {
  const st = compose({ offered: OFFERED, selections: { 'GS-1': 'selected' },
    nonDeclinable: ['GS-1'] });
  assert.strictEqual(codes(st).length, 0, 'unexpected problems: ' + codes(st));
});

t('B4. a mark pointing at a line not on the list -> REFUSE', function () {
  const st = compose({ offered: OFFERED, selections: { 'GS-1': 'selected' },
    nonDeclinable: ['GS-99'] });
  assert.ok(refusals(st).indexOf('NON_DECLINABLE_NOT_ON_LIST') >= 0);
});

t('B5. declining the non-declinable line -> REFUSE, and it NAMES the line', function () {
  const st = compose({ offered: OFFERED, selections: { 'GS-1': 'declined' },
    nonDeclinable: ['GS-1'] });
  assert.ok(refusals(st).indexOf('DECLINED_NON_DECLINABLE') >= 0);
  const p = st.problems.filter(function (x) { return x.code === 'DECLINED_NON_DECLINABLE'; })[0];
  assert.ok(/Basic Services/.test(p.detail),
    'the refusal does not say which line, so a director cannot act on it');
});

t('B6. NOTHING infers the non-declinable line from its NAME', function () {
  // The seed list opens with "Basic Services of Funeral Director and Staff".
  // If the composer matched that string, B1 would not fire on an unmarked
  // list -- and a legal determination would be being made by a substring.
  const st = compose({ offered: OFFERED, selections: { 'GS-1': 'selected' }, nonDeclinable: [] });
  assert.ok(codes(st).indexOf('NO_NON_DECLINABLE_MARKED') >= 0,
    'the composer treated a line as non-declinable without being told');
  assert.strictEqual(st.selected[0].nonDeclinable, false);
});

console.log('\nC. an absent price is never rendered or stored as 0');

[undefined, null, '', 'abc'].forEach(function (bad, i) {
  t('C1.' + (i + 1) + ' selected with price ' + JSON.stringify(bad)
    + ' -> REFUSE, total null', function () {
    const st = compose({
      offered: [{ id: 'GS-2', label: 'Embalming', price: bad, kind: 'service' },
                { id: 'GS-1', label: 'Basic Services', price: 2495, kind: 'service' }],
      selections: { 'GS-2': 'selected', 'GS-1': 'selected' }, nonDeclinable: ['GS-1'] });
    assert.ok(refusals(st).indexOf('PRICE_NOT_ON_FILE') >= 0);
    assert.strictEqual(st.total, null,
      'the total was a number while a selected line had no price');
  });
});

t('C2. a real 0 is a PRICE, not a missing one', function () {
  const st = compose({
    offered: [{ id: 'GS-1', label: 'Basic Services', price: 2495, kind: 'service' },
              { id: 'GS-3', label: 'Other Preparation', price: 0, kind: 'service' }],
    selections: { 'GS-1': 'selected', 'GS-3': 'selected' }, nonDeclinable: ['GS-1'] });
  assert.strictEqual(refusals(st).length, 0, 'refused on a genuine zero: ' + refusals(st));
  assert.strictEqual(st.total, 2495);
});

t('C3. an unpriced line that was DECLINED does not refuse', function () {
  const st = compose({
    offered: [{ id: 'GS-1', label: 'Basic Services', price: 2495, kind: 'service' },
              { id: 'GS-2', label: 'Embalming', price: null, kind: 'service' }],
    selections: { 'GS-1': 'selected', 'GS-2': 'declined' }, nonDeclinable: ['GS-1'] });
  assert.strictEqual(refusals(st).length, 0, 'refused on a declined unpriced line');
  assert.strictEqual(st.total, 2495);
});

t('C4. the total sums SELECTED only', function () {
  const st = compose({ offered: OFFERED,
    selections: { 'GS-1': 'selected', 'MU-2': 'selected', 'GS-2': 'declined' },
    nonDeclinable: ['GS-1'] });
  assert.strictEqual(st.total, 2495 + 3400);
});

console.log('\nD. a decision about a line that has left the price list');

t('D1. REFUSE rather than silently omit it', function () {
  const st = compose({ offered: OFFERED,
    selections: { 'GS-1': 'selected', 'GS-77': 'declined' }, nonDeclinable: ['GS-1'] });
  assert.ok(refusals(st).indexOf('SELECTION_FOR_UNKNOWN_LINE') >= 0);
  assert.strictEqual(st.printable, false);
});

console.log('\nE. the WRITER must not undo the composer refusal');

t('E1. legInvoiceFields REFUSES on a non-printable statement', function () {
  const st = compose({ offered: [{ id: 'GS-2', label: 'Embalming', price: null, kind: 'service' }],
    selections: { 'GS-2': 'selected' }, nonDeclinable: [] });
  assert.strictEqual(st.printable, false);
  assert.throws(function () { fieldsOf(st); }, /not printable/);
});

t('E2. ABLATION: the pre-fix writer produced exactly the row the composer refuses', function () {
  const st = compose({ offered: [{ id: 'GS-2', label: 'Embalming', price: null, kind: 'service' }],
    selections: { 'GS-2': 'selected' }, nonDeclinable: [] });
  const old = st.selected.map(function (r) {
    return { label: r.label, amount: r.price === null ? 0 : r.price };
  });
  assert.deepStrictEqual(old, [{ label: 'Embalming', amount: 0 }],
    'the ablation does not reproduce the old behaviour, so E1 proves nothing');
  assert.throws(function () { fieldsOf(st); },
    'the current writer accepts what the old one produced -- the fix is a no-op');
});

console.log('\nF. purity, so these arms are about the rules and not the browser');

t('F1. same input twice, same answer -- no clock, no randomness', function () {
  const input = { offered: OFFERED, selections: { 'GS-1': 'selected' }, nonDeclinable: ['GS-1'] };
  assert.deepStrictEqual(compose(input), compose(input));
});

t('F2. it does not mutate its inputs', function () {
  const sel = { 'GS-1': 'selected' };
  const nd = ['GS-1'];
  compose({ offered: OFFERED.slice(), selections: sel, nonDeclinable: nd });
  assert.deepStrictEqual(sel, { 'GS-1': 'selected' });
  assert.deepStrictEqual(nd, ['GS-1']);
});

t('F3. missing arguments are handled as data, not as an exception', function () {
  const st = compose();
  assert.deepStrictEqual(st.selected, []);
  assert.ok(codes(st).indexOf('NO_NON_DECLINABLE_MARKED') >= 0);
});

console.log('\nG. the panel actually USES it -- an engine with no caller is the SAIRNmechanical defect');

t('G1. the picker renders THREE states per line, with Not offered as the default', function () {
  const body = fnBody(APP, 'function legLineRadios(id,label,price){');
  assert.ok(/Not offered/.test(body) && /Selected/.test(body) && /Declined/.test(body),
    'the picker does not offer all three states');
  // MATCHED ON RAW TEXT, not on a whitespace-stripped copy. The first version
  // of this arm stripped whitespace before matching, which also removed the
  // space INSIDE the string literal `' checked'` -- so the pattern could
  // never match and the arm failed against correct code. That is the same
  // quote-masking mistake cc recorded in strip_comments on 2026-10-05.
  assert.ok(/val\s*===\s*''\s*\?\s*' checked'\s*:\s*''/.test(body),
    'Not offered is not the pre-checked default -- a director who has not '
    + 'reached a line would have it read as the family declining it');
});

t('G2. the SAVE path refuses, not only the preview', function () {
  const body = fnBody(APP, 'async function saveInvoice(){');
  assert.ok(/legComposeStatement\(/.test(body), 'saveInvoice does not use the composer');
  assert.ok(/statement\.printable/.test(body),
    'saveInvoice does not check printable -- a preview that warns beside a '
    + 'save that proceeds is the defect this suite exists for');
  assert.ok(/declined_items:fields\.declined_items/.test(body.replace(/\s/g, '')),
    'the invoice record does not store declined_items');
});

t('G3. the preview total reads the SAME composer, so the three cannot disagree', function () {
  const body = fnBody(APP, 'function ivTotalPreview(){');
  assert.ok(/legComposeStatement\(/.test(body),
    'the total preview computes its own sum instead of using the composer');
  assert.ok(/not computable/.test(body),
    'a null total renders as a number -- "$0" is a figure a family can read '
    + 'as a total');
});

t('G4. the Statement document distinguishes UNRECORDED from none-declined', function () {
  const body = fnBody(APP, 'function openStatement(invoiceId){');
  assert.ok(/Not recorded/.test(body),
    'an invoice saved before declines were kept would render as "none '
    + 'declined", which is the same fold F2 names');
  assert.ok(/NOT a statement that nothing was declined/.test(body),
    'the unrecorded case does not say what it is not');
  assert.ok(/453\.2\(b\)\(5\)/.test(body), 'the document does not cite its own rule');
  assert.ok(/does not assert/.test(body),
    'the document does not disclaim compliance -- this system cannot observe '
    + 'whether a list was offered in a room');
});

t('G5. the Statement button is reachable from the invoice table', function () {
  assert.ok(/onclick="openStatement\(/.test(APP),
    'openStatement has no caller -- an engine with no caller is the '
    + 'SAIRNmechanical G3 defect');
  assert.ok(APP.indexOf('id="stmtmodal"') !== -1, 'the statement modal is absent');
  assert.ok(/body:has\(#stmtmodal\.on\)/.test(APP),
    'the statement has no print rule, so printing it would print every panel '
    + 'underneath plus the backdrop');
});

t('G6. the non-declinable mark is editable and nothing is pre-ticked', function () {
  assert.ok(/onchange="saveGplNonDeclinable\(/.test(APP),
    'the non-declinable column has no handler');
  const seed = APP.slice(APP.indexOf("st('leg_gplservices',["),
                         APP.indexOf(']);', APP.indexOf("st('leg_gplservices',[")));
  assert.ok(!/non_declinable/.test(seed),
    'the SEED pre-marks a non-declinable line -- which charge that is, is the '
    + "home's statement about its own price list, not ours");
});

t('G7. the status line says when nothing is marked, and when too many are', function () {
  const body = fnBody(APP, 'function rGplNonDeclinableStatus(){');
  assert.ok(/No line is marked non-declinable/.test(body));
  assert.ok(/The Rule \n?permits one|permits one/.test(body.replace(/\s+/g, ' ')),
    'the too-many case does not state the rule');
  assert.ok(!/compliant/.test(body) || /does not/.test(body),
    'the status line claims compliance');
});

console.log('\nH. the vocabulary F2 measured at zero');

t('H1. declinability now has a representation in the app', function () {
  const n = (APP.match(/non_declinable|nonDeclinable/g) || []).length;
  assert.ok(n >= 10, 'only ' + n + ' declinability references -- F2 measured 0 '
    + 'for `declinable` and this arm exists so that number is not re-measured '
    + 'as 0 after a refactor quietly removes the feature');
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
