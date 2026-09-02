// tests/nesting_saw_ticket.js
//
// Run:  node tests/nesting_saw_ticket.js
//
// GAP 2 from the 2026-09-02 competitive-gap audit, saw/pick-ticket half.
//
// The audit said panel-nesting had "no export function of any kind". That was
// wrong in the specific, and the truth was worse. BOTH functions existed:
//
//   nestingExport() wrote a CSV of exactly two rows -- a header and one row of
//   slab width, height, material and cost. It exported not one cutout.
//   nestingPrint() printed material, slab size, yield, waste cost, an empty AI
//   line and a signature line. No pieces, no positions, not even the canvas.
//
// A fabricator printed it, carried it to the saw, and had nothing to cut from.
// The assertions below are therefore mostly about CONTENT: that the pieces are
// on the ticket, in cut order, with a stated origin, and that the numbers come
// from the data rather than from whatever the KPI elements happen to say.

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

// Pull the real IIFE body out of the page.
const start = html.indexOf('  // ── SAW AND PICK TICKETS (2026-09-02');
assert.ok(start > 0, 'the saw-ticket block was not found in stonedesk.html');
// The file is CRLF here, so the terminator is matched by regex rather than by
// an exact '\n'-joined string -- an assumption about line endings is not worth
// a brittle test.
const endRe = /\r?\n\}\)\(\);/;
const rel = html.slice(start).search(endRe);
assert.ok(rel > 0, 'the saw-ticket block is not terminated as expected');
const src = html.slice(start, start + rel);

function harness(opts) {
  opts = opts || {};
  const fields = Object.assign(
    { 'nest-slab-w': '126', 'nest-slab-h': '63', 'nest-slab-mat': 'Calacatta Quartz', 'nest-cost-sqft': '18' },
    opts.fields || {}
  );
  const notices = [];
  const downloads = [];
  let printed = null;
  const ctx = {
    console,
    sdNestingData: { slabW: 126, slabH: 63, cutouts: opts.cutouts || [], saved: [] },
    sdLocalToday: () => '2026-09-02',
    notify: (m, k) => notices.push({ m, k }),
    escHtml: (v) => String(v == null ? '' : v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;'),
    document: {
      getElementById: (id) => {
        if (id === 'nest-canvas') {
          return opts.noCanvas ? null : { width: 600, height: 400, toDataURL: () => 'data:image/png;base64,AAAA' };
        }
        if (id in fields) return { value: fields[id] };
        if (opts.kpi && id in opts.kpi) return { textContent: opts.kpi[id] };
        return null;
      },
      createElement: () => ({ set href(v) { this._h = v; }, get href() { return this._h; }, download: '', click() { downloads.push({ href: this._h, name: this.download }); } })
    },
    window: {
      open: () => {
        if (opts.popupBlocked) return null;
        printed = { html: '', closed: false, didPrint: false };
        return {
          document: { write: (s) => { printed.html += s; }, close: () => { printed.closed = true; } },
          print: () => { printed.didPrint = true; }
        };
      }
    },
    __notices: notices, __downloads: downloads,
    get __printed() { return printed; }
  };
  vm.createContext(ctx);
  vm.runInContext(src, ctx);
  // The block assigns to window.*; expose them for calling.
  ctx.nestingExport = ctx.window.nestingExport;
  ctx.nestingPrint = ctx.window.nestingPrint;
  ctx.__getPrinted = () => printed;
  return ctx;
}

const PIECES = [
  // Deliberately NOT in cut order: entered island-first, but it sits lower.
  { label: 'Smith Island', w: 80, h: 40, kerf: 0.125, x: 10, y: 30 },
  { label: 'Smith Backsplash', w: 96, h: 4, kerf: 0.125, x: 0.125, y: 0.125 },
  { label: 'Smith Left Run', w: 60, h: 25, kerf: 0.125, x: 0.125, y: 6 }
];

// ---------------------------------------------------------------------------
section('an empty ticket is refused, because that WAS the bug');

test('export with no pieces downloads nothing and says why', () => {
  const c = harness({ cutouts: [] });
  c.nestingExport();
  assert.strictEqual(c.__downloads.length, 0, 'it exported an empty ticket');
  assert.strictEqual(c.__notices.length, 1);
  assert.match(c.__notices[0].m, /worse than none/);
});

test('print with no pieces opens no window and says why', () => {
  const c = harness({ cutouts: [] });
  c.nestingPrint();
  assert.strictEqual(c.__getPrinted(), null, 'it printed an empty ticket');
  assert.strictEqual(c.__notices.length, 1);
});

// ---------------------------------------------------------------------------
section('THE FIX: the pieces are actually on the ticket');

test('the CSV carries one row per piece, not just the slab header', () => {
  const c = harness({ cutouts: PIECES });
  c.nestingExport();
  assert.strictEqual(c.__downloads.length, 1);
  const csv = decodeURIComponent(c.__downloads[0].href.replace('data:text/csv;charset=utf-8,', ''));
  PIECES.forEach(p => assert.ok(csv.includes(p.label), 'missing from the CSV: ' + p.label));
  const dataRows = csv.split('\n').filter(l => /^"[123]","Smith/.test(l));
  assert.strictEqual(dataRows.length, 3, 'expected 3 numbered cut-list rows, got ' + dataRows.length);
});

test('the CSV names the origin, so X/Y is not a number to guess at', () => {
  const c = harness({ cutouts: PIECES });
  c.nestingExport();
  const csv = decodeURIComponent(c.__downloads[0].href.replace('data:text/csv;charset=utf-8,', ''));
  assert.match(csv, /TOP-LEFT corner of the slab/);
});

test('the printed ticket carries a table row per piece', () => {
  const c = harness({ cutouts: PIECES });
  c.nestingPrint();
  const out = c.__getPrinted();
  assert.ok(out, 'nothing was printed');
  PIECES.forEach(p => assert.ok(out.html.includes(p.label), 'missing from the print: ' + p.label));
  assert.ok(out.closed && out.didPrint, 'the print window was not closed/printed');
});

test('the file is named a saw ticket, not a "layout"', () => {
  const c = harness({ cutouts: PIECES });
  c.nestingExport();
  assert.strictEqual(c.__downloads[0].name, 'saw-ticket-2026-09-02.csv');
});

// ---------------------------------------------------------------------------
section('cut order is the saw\'s order, not the order of entry');

test('pieces are sequenced by Y then X, not by when they were added', () => {
  const c = harness({ cutouts: PIECES });
  c.nestingExport();
  const csv = decodeURIComponent(c.__downloads[0].href.replace('data:text/csv;charset=utf-8,', ''));
  const seq = csv.split('\n').filter(l => /^"[0-9]+","Smith/.test(l)).map(l => l.split('","')[1]);
  assert.deepStrictEqual(seq, ['Smith Backsplash', 'Smith Left Run', 'Smith Island'],
    'cut order was ' + JSON.stringify(seq));
});

test('the order is stable between two runs of the same layout', () => {
  const grab = () => {
    const c = harness({ cutouts: [
      { label: 'B', w: 10, h: 10, x: 5, y: 0 },
      { label: 'A', w: 10, h: 10, x: 5, y: 0 }
    ] });
    c.nestingExport();
    const csv = decodeURIComponent(c.__downloads[0].href.replace('data:text/csv;charset=utf-8,', ''));
    return csv.split('\n').filter(l => /^"[0-9]+","[AB]"/.test(l)).map(l => l.split('","')[1]);
  };
  assert.deepStrictEqual(grab(), grab());
  assert.deepStrictEqual(grab(), ['A', 'B'], 'the tie-break is not by label');
});

// ---------------------------------------------------------------------------
section('the numbers come from the data, not from the screen');

test('a wrong KPI on screen does NOT reach the ticket', () => {
  // The tempting implementation reads document.getElementById('nest-kpi-yield')
  // .textContent. That is one DOM change away from a ticket that is wrong on
  // paper while the screen looks right.
  const c = harness({
    cutouts: [{ label: 'P', w: 144, h: 63, x: 0, y: 0 }],   // exactly 63 sq ft of a 55.125 sq ft slab
    kpi: { 'nest-kpi-yield': '999%', 'nest-kpi-used': '0.0', 'nest-kpi-cost': '$12345.00' }
  });
  c.nestingPrint();
  const out = c.__getPrinted().html;
  assert.ok(!out.includes('999%'), 'the ticket echoed a KPI element');
  assert.ok(!out.includes('12345'), 'the ticket echoed a KPI element');
  assert.ok(out.includes('63.00 sq ft'), 'the used figure was not computed from the pieces');
});

test('no cost entered -> "not entered", never "$0.00"', () => {
  const c = harness({ cutouts: PIECES, fields: { 'nest-cost-sqft': '' } });
  c.nestingPrint();
  const out = c.__getPrinted().html;
  assert.match(out, /Waste cost:<\/strong> not entered/);
  assert.ok(!/Waste cost:<\/strong> \$0\.00/.test(out),
    'an unentered cost was reported as a measured zero');
});

test('a cost of zero IS reported as zero -- it was entered', () => {
  const c = harness({ cutouts: PIECES, fields: { 'nest-cost-sqft': '0' } });
  c.nestingPrint();
  assert.match(c.__getPrinted().html, /Waste cost:<\/strong> \$0\.00/);
});

// ---------------------------------------------------------------------------
section('the honest failure paths');

test('no canvas -> the ticket SAYS the diagram is missing', () => {
  const c = harness({ cutouts: PIECES, noCanvas: true });
  c.nestingPrint();
  const out = c.__getPrinted().html;
  assert.match(out, /No layout diagram available/);
  assert.ok(!out.includes('<img'), 'it emitted an image tag with no image');
  // The cut list must still be there -- a missing picture is not a missing ticket.
  PIECES.forEach(p => assert.ok(out.includes(p.label)));
});

test('a canvas present -> the layout image is embedded', () => {
  const c = harness({ cutouts: PIECES });
  c.nestingPrint();
  assert.match(c.__getPrinted().html, /<img src="data:image\/png/);
});

test('a blocked pop-up is reported, not swallowed', () => {
  const c = harness({ cutouts: PIECES, popupBlocked: true });
  c.nestingPrint();
  assert.strictEqual(c.__getPrinted(), null);
  assert.ok(c.__notices.some(n => /pop-ups/.test(n.m)), 'the block was silent');
});

test('a piece label with markup is escaped in the printed ticket', () => {
  const c = harness({ cutouts: [{ label: '<img src=x onerror=alert(1)>', w: 10, h: 10, x: 0, y: 0 }] });
  c.nestingPrint();
  const out = c.__getPrinted().html;
  assert.ok(!out.includes('<img src=x'), 'a label was written unescaped into the ticket');
  assert.ok(out.includes('&lt;img src=x'), 'the label is missing entirely');
});

test('a label with a quote survives the CSV intact', () => {
  const c = harness({ cutouts: [{ label: 'Smith 24" island', w: 10, h: 10, x: 0, y: 0 }] });
  c.nestingExport();
  const csv = decodeURIComponent(c.__downloads[0].href.replace('data:text/csv;charset=utf-8,', ''));
  assert.ok(csv.includes('"Smith 24"" island"'), 'the quote was not doubled: ' + csv.split('\n').pop());
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' SAW-TICKET ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
