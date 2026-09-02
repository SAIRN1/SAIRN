// tests/slab_scan_labels.js
//
// Run:  node tests/slab_scan_labels.js
//
// GAP 3 from the 2026-09-02 competitive-gap audit. `barcode` appeared ZERO
// times in stonedesk.html; the only trace was `externalBarcode:''`, an empty
// placeholder wired to nothing. ActionFlow, Stone Profit Systems, Slabsmith,
// DDL and Sistrom all have this, because it is how the industry stops the
// DOUBLE SALE -- the error iBlocky puts second on its own homepage.
//
// The compare-and-swap shipped earlier the same day stops the double-sale IN
// THE SYSTEM. It cannot stop someone walking into the yard and cutting a slab
// that is already promised, because nothing on the slab says so.
//
// The assertion that matters most here is the AMBIGUITY one. Supplier barcodes
// repeat across bundles, and a resolver that silently returns the first match
// is the same shape of mistake as the blind reservation write it follows: a
// confident answer about the wrong physical stone.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'stonedesk.html'), 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

function grab(startMarker, endRe) {
  const s = html.indexOf(startMarker);
  assert.ok(s > 0, 'not found in stonedesk.html: ' + startMarker);
  const rel = html.slice(s).search(endRe);
  assert.ok(rel > 0, 'unterminated: ' + startMarker);
  return html.slice(s, s + rel);
}

// The two pure resolvers, extracted from the real file.
const src =
  grab('  function sdResolveSlabCode(code, slabs) {', /\r?\n  \}/) + '\n  }\n' +
  grab('  function sdBarcodeBindCheck(code, slabId, slabs) {', /\r?\n  \}/) + '\n  }\n';

const ctx = { console };
vm.createContext(ctx);
vm.runInContext(src, ctx);
const { sdResolveSlabCode, sdBarcodeBindCheck } = ctx;

const SLABS = [
  { id: 'SD-001', colorName: 'Calacatta', status: 'in-stock', externalBarcode: '' },
  { id: 'SD-002', colorName: 'Taj Mahal', status: 'reserved', reservedFor: 'Ruiz kitchen', externalBarcode: 'MSI-99887' },
  { id: 'SD-003', colorName: 'Black Pearl', status: 'consumed', externalBarcode: 'MSI-11111' },
  { id: 'SD-004', colorName: 'Fantasy Brown', status: 'in-stock', externalBarcode: 'MSI-11111' }  // duplicate, on purpose
];

// ---------------------------------------------------------------------------
section('resolving a scan');

test('a bare slab ID resolves', () => {
  const r = sdResolveSlabCode('SD-002', SLABS);
  assert.strictEqual(r.match.id, 'SD-002');
  assert.strictEqual(r.how, 'id');
});

test('our own SDSLAB: prefix resolves, and is reported as prefixed', () => {
  const r = sdResolveSlabCode('SDSLAB:SD-002', SLABS);
  assert.strictEqual(r.match.id, 'SD-002');
  assert.strictEqual(r.how, 'prefixed-id');
});

test('case and surrounding whitespace do not matter -- scanners add both', () => {
  assert.strictEqual(sdResolveSlabCode('  sd-002 ', SLABS).match.id, 'SD-002');
  assert.strictEqual(sdResolveSlabCode('sdslab:sd-002', SLABS).match.id, 'SD-002');
});

test("a supplier's own barcode resolves, and says so", () => {
  const r = sdResolveSlabCode('MSI-99887', SLABS);
  assert.strictEqual(r.match.id, 'SD-002');
  assert.strictEqual(r.how, 'external');
});

test('an unknown code resolves to nothing rather than a nearest guess', () => {
  const r = sdResolveSlabCode('NOT-A-CODE', SLABS);
  assert.strictEqual(r.match, null);
  assert.deepStrictEqual(r.candidates.length, 0);
});

test('empty input is not a lookup', () => {
  ['', '   ', null, undefined, 'SDSLAB:'].forEach((v) => {
    assert.strictEqual(sdResolveSlabCode(v, SLABS).match, null, 'resolved: ' + JSON.stringify(v));
  });
});

test('no slab list at all does not throw', () => {
  assert.strictEqual(sdResolveSlabCode('SD-001', null).match, null);
  assert.strictEqual(sdResolveSlabCode('SD-001', undefined).match, null);
});

// ---------------------------------------------------------------------------
section('THE ONE THAT MATTERS: ambiguity is reported, never resolved');

test('two slabs sharing a supplier barcode -> no match, BOTH named', () => {
  const r = sdResolveSlabCode('MSI-11111', SLABS);
  assert.strictEqual(r.match, null, 'it picked one of two physically different stones');
  assert.deepStrictEqual(r.candidates.map((s) => s.id).sort(), ['SD-003', 'SD-004']);
});

test('the ambiguous case reports HOW it was ambiguous, so the message can say', () => {
  assert.strictEqual(sdResolveSlabCode('MSI-11111', SLABS).how, 'external');
});

test('duplicate slab IDs are treated the same way, not first-wins', () => {
  const dupes = [{ id: 'X1', colorName: 'A' }, { id: 'x1', colorName: 'B' }];
  const r = sdResolveSlabCode('X1', dupes);
  assert.strictEqual(r.match, null);
  assert.strictEqual(r.candidates.length, 2);
});

test('a PREFIXED code never falls through to a supplier barcode', () => {
  // SDSLAB: means "this is our label and the payload is a slab id". Falling
  // through to a barcode match would answer a question nobody asked.
  const r = sdResolveSlabCode('SDSLAB:MSI-99887', SLABS);
  assert.strictEqual(r.match, null, 'a StoneDesk label matched a supplier barcode');
});

test('an empty externalBarcode never matches an empty-ish scan', () => {
  // SD-001 has externalBarcode:'' -- a normaliser that treats '' as a value
  // would match it on any blank-ish input.
  assert.strictEqual(sdResolveSlabCode('   ', SLABS).match, null);
  assert.strictEqual(sdResolveSlabCode('""', SLABS).match, null);
});

// ---------------------------------------------------------------------------
section('binding a supplier label refuses what would make a code mean two things');

test('a clean code binds', () => {
  const r = sdBarcodeBindCheck('CAMBRIA-4521', 'SD-001', SLABS);
  assert.strictEqual(r.ok, true);
  assert.strictEqual(r.code, 'CAMBRIA-4521');
});

test('a code already bound to ANOTHER slab is refused, and names it', () => {
  const r = sdBarcodeBindCheck('MSI-99887', 'SD-001', SLABS);
  assert.strictEqual(r.ok, false);
  assert.match(r.message, /SD-002/);
});

test('re-binding the same code to the SAME slab is not a clash', () => {
  assert.strictEqual(sdBarcodeBindCheck('MSI-99887', 'SD-002', SLABS).ok, true);
});

test('a code that is already a slab ID is refused', () => {
  const r = sdBarcodeBindCheck('SD-003', 'SD-001', SLABS);
  assert.strictEqual(r.ok, false);
  assert.match(r.message, /two different slabs/);
});

test('one of our own labels is refused -- there is nothing to bind', () => {
  const r = sdBarcodeBindCheck('SDSLAB:SD-001', 'SD-001', SLABS);
  assert.strictEqual(r.ok, false);
  assert.match(r.message, /already identifies a slab/);
});

test('an empty code is refused', () => {
  assert.strictEqual(sdBarcodeBindCheck('  ', 'SD-001', SLABS).ok, false);
});

// ---------------------------------------------------------------------------
section('what the UI promises, checked against the source');

test('the scan field is wired to both a scanner and a human', () => {
  // A USB scanner types then sends Enter; a person types and tabs away.
  assert.match(html, /id="sd-slab-scan"[\s\S]{0,400}onchange="sdSlabScanLookup\(\)"/);
  assert.match(html, /onkeydown="if\(event\.key==='Enter'\)/);
});

test('a reserved slab shouts the holder -- that is the yard-facing answer', () => {
  assert.match(html, /RESERVED FOR/);
  assert.match(html, /do not cut this for another job/);
});

test('a consumed slab says so instead of just "not available"', () => {
  assert.match(html, /ALREADY CONSUMED/);
});

test('the label sheet does NOT print status or reservation', () => {
  // A printed "Available" outlives the fact. Status is what the scan is for,
  // and the sheet says so on the page rather than only in a code comment.
  assert.match(html, /Status and reservations are deliberately NOT printed on a label/);
});

test('a missing QR library is announced ON THE PRINTED SHEET, not just in a toast', () => {
  assert.match(html, /No QR codes on this sheet/);
  assert.match(html, /typeof QRCode !== 'undefined'/);
});

test('the previously-unused QR library is now actually used', () => {
  // qrcodejs was loaded on every page load and `new QRCode(` appeared zero
  // times -- a download every user paid for and nothing consumed.
  assert.match(html, /qrcodejs\/1\.0\.0\/qrcode\.min\.js/);
  assert.ok(/new QRCode\(/.test(html), 'the library is still loaded and never used');
});

test('cut slabs are excluded from the label run', () => {
  assert.match(html, /eng\(\)\.filter\(function \(s\) \{ return dispStatus\(s\) !== 'Cut'; \}\)/);
});

test('a blocked pop-up is reported, not swallowed', () => {
  const i = html.indexOf('window.sdSlabsPrintLabels');
  assert.match(html.slice(i, i + 3000), /pop-ups for this site/);
});

test('the bind path states its own concurrency limit rather than implying safety', () => {
  const i = html.indexOf('window.sdSlabBindBarcode');
  const src2 = html.slice(i - 1200, i + 200);
  assert.match(src2, /blind upsert/);
  assert.match(src2, /REPORTS ambiguity rather than guessing/);
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' SLAB-SCAN ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
