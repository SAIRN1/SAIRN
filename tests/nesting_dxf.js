// tests/nesting_dxf.js
//
// Run:  node tests/nesting_dxf.js
//
// GAP 2 from the 2026-09-02 competitive-gap audit, MACHINE-OUTPUT half.
// Companion to tests/nesting_saw_ticket.js, which covers the paper half.
//
// The DXF block's own comment asserts "there is a test that fails if it is ever
// emitted unflipped." This file is that test -- it did not exist when the claim
// was written, which is precisely the class of unbacked claim this codebase
// refuses elsewhere. It exists now.
//
// What actually makes a DXF dangerous rather than merely wrong: it is a file
// that OPENS. A mirrored layout, a millimetre-assuming reader, a kerf baked
// into the geometry -- none of those produce an error dialog. They produce a
// clean-looking drawing and a slab cut in the wrong places. So the assertions
// below are about the silent-wrongness cases, not about whether the parser is
// happy.

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

// Same block, same extraction as the saw-ticket test -- the DXF functions live
// inside the same IIFE. CRLF-tolerant terminator for the same reason.
const start = html.indexOf('  // ── SAW AND PICK TICKETS (2026-09-02');
assert.ok(start > 0, 'the saw-ticket/DXF block was not found in stonedesk.html');
const rel = html.slice(start).search(/\r?\n\}\)\(\);/);
assert.ok(rel > 0, 'the block is not terminated as expected');
const src = html.slice(start, start + rel);

function harness(opts) {
  opts = opts || {};
  const fields = Object.assign(
    { 'nest-slab-w': '126', 'nest-slab-h': '63', 'nest-slab-mat': 'Calacatta Quartz', 'nest-cost-sqft': '18' },
    opts.fields || {}
  );
  const notices = [];
  const downloads = [];
  const revoked = [];
  const ctx = {
    console,
    sdNestingData: { slabW: 126, slabH: 63, cutouts: opts.cutouts || [], saved: [] },
    sdLocalToday: () => '2026-09-02',
    notify: (m, k) => notices.push({ m, k }),
    escHtml: (v) => String(v == null ? '' : v),
    // Minimal Blob: keeps the bytes so the test can read what was actually
    // handed to the browser, rather than trusting the builder's return value.
    Blob: function (parts, o) { this.parts = parts; this.type = (o || {}).type; },
    document: {
      getElementById: (id) => (id in fields ? { value: fields[id] } : null),
      createElement: () => ({
        set href(v) { this._h = v; }, get href() { return this._h; },
        download: '',
        click() { downloads.push({ href: this._h, name: this.download }); }
      })
    },
    __notices: notices, __downloads: downloads, __revoked: revoked
  };
  ctx.window = {
    URL: {
      createObjectURL: (b) => { ctx.__lastBlob = b; return 'blob:stub'; },
      revokeObjectURL: (u) => revoked.push(u)
    }
  };
  vm.createContext(ctx);
  vm.runInContext(src, ctx);
  ctx.nestBuildDXF = ctx.window.nestBuildDXF;
  ctx.nestingExportDXF = ctx.window.nestingExportDXF;
  return ctx;
}

// Parse a DXF into a flat [code, value] list. Group codes and values alternate,
// one per line -- that IS the format, so a parser this small is the whole spec.
function pairs(dxf) {
  const lines = dxf.split('\n');
  const out = [];
  for (let i = 0; i + 1 < lines.length; i += 2) out.push([lines[i].trim(), lines[i + 1]]);
  return out;
}
// Entities as {type, codes:{code:[values]}} in file order.
function entities(dxf) {
  const p = pairs(dxf);
  const ents = [];
  let cur = null;
  let inEntities = false;
  for (let i = 0; i < p.length; i++) {
    const [c, v] = p[i];
    if (c === '2' && v === 'ENTITIES') { inEntities = true; continue; }
    if (!inEntities) continue;
    if (c === '0') {
      if (v === 'ENDSEC') break;
      cur = { type: v, codes: {} };
      ents.push(cur);
      continue;
    }
    if (cur) (cur.codes[c] = cur.codes[c] || []).push(v);
  }
  return ents;
}
// The PIECES-layer rectangles, as {x,y,w,h} recovered from their vertices.
function pieceRects(dxf) {
  const ents = entities(dxf);
  const rects = [];
  let layer = null, verts = null;
  for (const e of ents) {
    if (e.type === 'POLYLINE') { layer = (e.codes['8'] || [])[0]; verts = []; }
    else if (e.type === 'VERTEX' && verts) verts.push([Number(e.codes['10'][0]), Number(e.codes['20'][0])]);
    else if (e.type === 'SEQEND' && verts) {
      if (layer === 'PIECES') {
        const xs = verts.map(v => v[0]), ys = verts.map(v => v[1]);
        rects.push({
          x: Math.min(...xs), y: Math.min(...ys),
          w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys)
        });
      }
      verts = null; layer = null;
    }
  }
  return rects;
}

const SLAB_W = 126, SLAB_H = 63;
const PIECES = [
  // Sits hard against the TOP of the slab on screen. In DXF it must sit hard
  // against the TOP too -- i.e. its bottom edge at 63-4 = 59, not at 0.125.
  { label: 'Smith Backsplash', w: 96, h: 4, kerf: 0.125, x: 0.125, y: 0.125 },
  { label: 'Smith Island', w: 80, h: 40, kerf: 0.125, x: 10, y: 20 }
];

// ---------------------------------------------------------------------------
section('THE Y FLIP -- the failure that opens cleanly and cuts wrong');

test('a piece at the TOP of the canvas is at the TOP of the DXF, not the bottom', () => {
  const c = harness({ cutouts: PIECES });
  const rects = pieceRects(c.nestBuildDXF(SLAB_W, SLAB_H, PIECES, 'Quartz'));
  const bs = rects[0];
  // canvasY 0.125 is the TOP edge measured downward; the piece is 4 tall;
  // so its DXF bottom edge is 63 - (0.125 + 4) = 58.875.
  assert.ok(Math.abs(bs.y - 58.875) < 1e-6, 'backsplash bottom edge is ' + bs.y + ', expected 58.875');
});

test('the raw canvas Y is NOT what got written -- an unflipped export fails here', () => {
  const c = harness({ cutouts: PIECES });
  const rects = pieceRects(c.nestBuildDXF(SLAB_W, SLAB_H, PIECES, 'Quartz'));
  assert.notStrictEqual(rects[0].y, 0.125, 'canvas Y was emitted verbatim -- the layout is mirrored');
  assert.notStrictEqual(rects[1].y, 20, 'canvas Y was emitted verbatim -- the layout is mirrored');
});

test('the flip is an inversion, not an offset: order top-to-bottom reverses', () => {
  const c = harness({ cutouts: PIECES });
  const rects = pieceRects(c.nestBuildDXF(SLAB_W, SLAB_H, PIECES, 'Quartz'));
  // Backsplash is ABOVE the island on screen (smaller canvas Y), so in DXF it
  // must have the LARGER Y. A constant offset would preserve the order.
  assert.ok(rects[0].y > rects[1].y, 'vertical order did not invert');
});

test('X is untouched -- only Y is a different convention', () => {
  const c = harness({ cutouts: PIECES });
  const rects = pieceRects(c.nestBuildDXF(SLAB_W, SLAB_H, PIECES, 'Quartz'));
  assert.strictEqual(rects[0].x, 0.125);
  assert.strictEqual(rects[1].x, 10);
});

test('every piece lands inside the slab extents after the flip', () => {
  const c = harness({ cutouts: PIECES });
  pieceRects(c.nestBuildDXF(SLAB_W, SLAB_H, PIECES, 'Quartz')).forEach(r => {
    assert.ok(r.x >= 0 && r.y >= 0, 'piece has a negative coordinate: ' + JSON.stringify(r));
    assert.ok(r.x + r.w <= SLAB_W + 1e-9 && r.y + r.h <= SLAB_H + 1e-9,
      'piece escapes the slab: ' + JSON.stringify(r));
  });
});

// ---------------------------------------------------------------------------
section('KERF stays out of the geometry');

test('the rectangle is the FINISHED size -- kerf is not added or subtracted', () => {
  const c = harness({ cutouts: PIECES });
  const rects = pieceRects(c.nestBuildDXF(SLAB_W, SLAB_H, PIECES, 'Quartz'));
  assert.strictEqual(rects[0].w, 96, 'width moved -- kerf was baked in');
  assert.strictEqual(rects[0].h, 4, 'height moved -- kerf was baked in');
  assert.strictEqual(rects[1].w, 80);
  assert.strictEqual(rects[1].h, 40);
});

test('changing kerf does not change one coordinate in the file', () => {
  const a = harness({ cutouts: PIECES });
  const b = harness({ cutouts: PIECES.map(p => Object.assign({}, p, { kerf: 0.5 })) });
  assert.strictEqual(
    a.nestBuildDXF(SLAB_W, SLAB_H, PIECES, 'Quartz'),
    b.nestBuildDXF(SLAB_W, SLAB_H, PIECES.map(p => Object.assign({}, p, { kerf: 0.5 })), 'Quartz'),
    'kerf leaked into the geometry'
  );
});

// ---------------------------------------------------------------------------
section('it is actually R12, and actually well-formed');

test('SECTION and ENDSEC balance, and the file ends with EOF', () => {
  const c = harness({ cutouts: PIECES });
  const dxf = c.nestBuildDXF(SLAB_W, SLAB_H, PIECES, 'Quartz');
  const p = pairs(dxf);
  const secs = p.filter(x => x[0] === '0' && x[1] === 'SECTION').length;
  const ends = p.filter(x => x[0] === '0' && x[1] === 'ENDSEC').length;
  assert.strictEqual(secs, ends, secs + ' SECTION vs ' + ends + ' ENDSEC');
  assert.ok(secs >= 3, 'expected HEADER, TABLES and ENTITIES');
  assert.strictEqual(p[p.length - 1][1], 'EOF', 'file does not end with EOF');
});

test('no LWPOLYLINE -- that entity does not exist in R12', () => {
  const c = harness({ cutouts: PIECES });
  assert.ok(!/LWPOLYLINE/.test(c.nestBuildDXF(SLAB_W, SLAB_H, PIECES, 'Quartz')),
    'emitted LWPOLYLINE while claiming R12');
});

test('every POLYLINE is closed and terminated by a SEQEND', () => {
  const c = harness({ cutouts: PIECES });
  const ents = entities(c.nestBuildDXF(SLAB_W, SLAB_H, PIECES, 'Quartz'));
  const polys = ents.filter(e => e.type === 'POLYLINE');
  const seqs = ents.filter(e => e.type === 'SEQEND');
  assert.strictEqual(polys.length, seqs.length, 'POLYLINE/SEQEND count mismatch');
  polys.forEach(pl => {
    assert.strictEqual((pl.codes['70'] || [])[0], '1', 'polyline is not flagged closed (70=1)');
    assert.strictEqual((pl.codes['66'] || [])[0], '1', 'polyline is missing vertices-follow (66=1)');
  });
});

test('each rectangle carries exactly four vertices', () => {
  const c = harness({ cutouts: PIECES });
  const ents = entities(c.nestBuildDXF(SLAB_W, SLAB_H, PIECES, 'Quartz'));
  let count = null, seen = [];
  ents.forEach(e => {
    if (e.type === 'POLYLINE') count = 0;
    else if (e.type === 'VERTEX' && count !== null) count++;
    else if (e.type === 'SEQEND' && count !== null) { seen.push(count); count = null; }
  });
  assert.ok(seen.length > 0, 'no rectangles emitted');
  seen.forEach(n => assert.strictEqual(n, 4, 'a rectangle has ' + n + ' vertices'));
});

test('every layer an entity uses is declared in the LAYER table', () => {
  const c = harness({ cutouts: PIECES });
  const dxf = c.nestBuildDXF(SLAB_W, SLAB_H, PIECES, 'Quartz');
  const tableEnd = dxf.indexOf('ENDTAB');
  const declared = new Set();
  pairs(dxf.slice(0, tableEnd)).forEach(([c2, v]) => { if (c2 === '2') declared.add(v); });
  entities(dxf).forEach(e => {
    (e.codes['8'] || []).forEach(l => assert.ok(declared.has(l), 'undeclared layer: ' + l));
  });
});

test('the slab outline is emitted, so the file makes sense opened alone', () => {
  const c = harness({ cutouts: PIECES });
  const ents = entities(c.nestBuildDXF(SLAB_W, SLAB_H, PIECES, 'Quartz'));
  assert.ok(ents.some(e => e.type === 'POLYLINE' && (e.codes['8'] || [])[0] === 'SLAB'),
    'no slab outline');
});

// ---------------------------------------------------------------------------
section('units are stated, because a wrong-unit file is silently 25.4x wrong');

test('$INSUNITS is 1 (inches), not left to the reader to assume', () => {
  const c = harness({ cutouts: PIECES });
  const dxf = c.nestBuildDXF(SLAB_W, SLAB_H, PIECES, 'Quartz');
  const p = pairs(dxf);
  const i = p.findIndex(x => x[0] === '9' && x[1] === '$INSUNITS');
  assert.ok(i >= 0, '$INSUNITS is not set');
  assert.strictEqual(p[i + 1][0], '70');
  assert.strictEqual(p[i + 1][1], '1', 'units are not inches');
});

test('$EXTMAX matches the slab, so a fit-to-view shows the whole slab', () => {
  const c = harness({ cutouts: PIECES });
  const p = pairs(c.nestBuildDXF(SLAB_W, SLAB_H, PIECES, 'Quartz'));
  const i = p.findIndex(x => x[0] === '9' && x[1] === '$EXTMAX');
  assert.ok(i >= 0, '$EXTMAX missing');
  assert.strictEqual(Number(p[i + 1][1]), SLAB_W);
  assert.strictEqual(Number(p[i + 2][1]), SLAB_H);
});

// ---------------------------------------------------------------------------
section('numbers and text cannot corrupt the group structure');

test('no exponential notation reaches the file', () => {
  const c = harness({ cutouts: [{ label: 'Tiny', w: 0.00001, h: 0.00001, x: 0.0000001, y: 0 }] });
  const dxf = c.nestBuildDXF(SLAB_W, SLAB_H, c.sdNestingData.cutouts, 'Quartz');
  assert.ok(!/\d[eE][-+]?\d/.test(dxf), 'exponential notation in a DXF real');
});

test('a NaN or missing dimension becomes 0, never the string "NaN"', () => {
  const c = harness({ cutouts: [{ label: 'Broken', w: undefined, h: NaN, x: 'abc', y: null }] });
  const dxf = c.nestBuildDXF(SLAB_W, SLAB_H, c.sdNestingData.cutouts, 'Quartz');
  assert.ok(!/NaN|undefined/.test(dxf), 'NaN or undefined written into the file');
});

test('a label with a newline cannot split into a bogus group code', () => {
  const c = harness({ cutouts: [{ label: 'Bad\n0\nEOF\n', w: 10, h: 10, x: 0, y: 0 }] });
  const dxf = c.nestBuildDXF(SLAB_W, SLAB_H, c.sdNestingData.cutouts, 'Quartz');
  // The only EOF is the real one, at the very end.
  const p = pairs(dxf);
  assert.strictEqual(p.filter(x => x[1] === 'EOF').length, 1, 'a label forged an EOF');
  assert.strictEqual(p[p.length - 1][1], 'EOF');
});

test('an every-line-is-a-pair file: nothing is emitted odd-length', () => {
  const c = harness({ cutouts: PIECES });
  const dxf = c.nestBuildDXF(SLAB_W, SLAB_H, PIECES, 'Quartz');
  const lines = dxf.split('\n');
  // Trailing newline after the final value gives one empty last element.
  assert.strictEqual(lines[lines.length - 1], '');
  assert.strictEqual((lines.length - 1) % 2, 0, 'group codes and values do not pair up');
});

// ---------------------------------------------------------------------------
section('the export path itself, and what it tells the operator');

test('no pieces -> no file, same refusal as the paper ticket', () => {
  const c = harness({ cutouts: [] });
  c.nestingExportDXF();
  assert.strictEqual(c.__downloads.length, 0, 'exported an empty DXF');
  assert.match(c.__notices[0].m, /worse than none/);
});

test('the download is named .dxf and dated', () => {
  const c = harness({ cutouts: PIECES });
  c.nestingExportDXF();
  assert.strictEqual(c.__downloads.length, 1);
  assert.strictEqual(c.__downloads[0].name, 'slab-layout-2026-09-02.dxf');
});

test('the object URL is revoked -- no leaked blob per export', () => {
  const c = harness({ cutouts: PIECES });
  c.nestingExportDXF();
  assert.deepStrictEqual(c.__revoked, ['blob:stub']);
});

test('the notice says what it is NOT -- "DXF" alone reads as a machine program', () => {
  const c = harness({ cutouts: PIECES });
  c.nestingExportDXF();
  const m = c.__notices[0].m;
  assert.match(m, /not a machine program/i, 'the notice does not disclaim being a program');
  assert.match(m, /inch/i, 'the notice does not state units');
  assert.match(m, /bottom-left/i, 'the notice does not state the origin');
  assert.match(m, /kerf/i, 'the notice does not say where kerf lives');
});

test('the slab size comes from the form, not from the stale data object', () => {
  const c = harness({ cutouts: PIECES, fields: { 'nest-slab-h': '80' } });
  c.nestingExportDXF();
  const dxf = c.__lastBlob.parts.join('');
  const rects = pieceRects(dxf);
  // Flip must use 80, not the sdNestingData.slabH of 63.
  assert.ok(Math.abs(rects[0].y - (80 - 0.125 - 4)) < 1e-6,
    'the flip used a stale slab height -- got ' + rects[0].y);
});

test('the material typed on screen is carried into the file', () => {
  const c = harness({ cutouts: PIECES });
  c.nestingExportDXF();
  assert.match(c.__lastBlob.parts.join(''), /Calacatta Quartz/);
});

test('same layout in, byte-identical file out -- no clock, no randomness', () => {
  const a = harness({ cutouts: PIECES }).nestBuildDXF(SLAB_W, SLAB_H, PIECES, 'Quartz');
  const b = harness({ cutouts: PIECES }).nestBuildDXF(SLAB_W, SLAB_H, PIECES, 'Quartz');
  assert.strictEqual(a, b);
});

// ---------------------------------------------------------------------------
console.log('');
if (fail) { console.log(fail + ' FAILED, ' + pass + ' passed'); process.exit(1); }
console.log('ALL ' + pass + ' DXF ASSERTIONS PASS');
