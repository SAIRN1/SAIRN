// tests/sairnmechanical_credential_export.js
//
// Run:  node tests/sairnmechanical_credential_export.js
//
// `mech_credentials` is Class A -- sairnmechanical's own registry declares it
// append-only -- and until 2026-09-16 this contractor could LOOK AT the
// credential board and could not PRODUCE it. There was no `createObjectURL`
// anywhere in the file.
//
// ── THE ARM THAT MATTERS IS SECTION 2 ──────────────────────────────────────
// The table on screen is `board.rows`, which the server builds with
// latestByKey(): ONE ROW per (technician, record type, section-or-jurisdiction),
// newest issue date wins. That is right for a board -- a technician who renewed
// last month should not appear twice under "is this current" -- and WRONG for a
// file. The superseded rows are the renewal history, which is the entire reason
// an append-only register exists, and an export built from the board would drop
// them silently.
//
// That is not a hypothetical shape on this platform. SAIRNdental exported five
// derived ageing buckets in place of the charges that produced them, and the
// Billing panel's Export CSV button made it read as covered. Same defect, one
// app over. So this drives the real mechExportDataset() over a fixture where a
// credential HAS been renewed, and asserts BOTH records are in the file and
// that each says which one the board is showing.
//
// ── AND SECTION 3, THE EPA 608 SECTION ─────────────────────────────────────
// The screen merges section and jurisdiction into one "Section / jurisdiction"
// cell because only one is ever populated. In a file they must not share a
// column. The section is the REGULATED FIELD -- Type I, II, III and Universal
// are different EQUIPMENT under 40 CFR 82.161, not ranks -- and "has an EPA
// card" is not an answer to whether somebody may open a given machine. A
// spreadsheet filtered on a section must not also match a jurisdiction that
// happens to read the same.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

// MECH_HTML lets a negative control point this suite at a MUTATED COPY in a
// temp directory instead of patching the tracked file. Same convention
// DNT_HTML, SB_HTML, SV_HTML and ALF_HTML already carry.
const html = fs.readFileSync(process.env.MECH_HTML
  || path.join(__dirname, '..', 'sairnmechanical.html'), 'utf8')
  .replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function grab(sig, terminator) {
  const at = html.indexOf(sig);
  assert.ok(at > 0, 'not found in sairnmechanical.html: ' + sig);
  const end = html.indexOf(terminator, at);
  assert.ok(end > at, 'terminator not found after ' + sig);
  return html.slice(at, end + terminator.length);
}

// ── THE FIXTURE, AND WHY IT IS SHAPED LIKE THIS ───────────────────────────
// MC-1 and MC-2 are the SAME KEY -- same technician, same type, same section --
// so the server's latestByKey() keeps only MC-2 on the board. MC-1 is the
// superseded original and is the row an export built from the board would lose.
// MC-3 is a jurisdictional licence with no EPA section, and MC-4 is a lifetime
// EPA 608 with no expiry at all, which is the `unknown` status the board is
// careful not to colour green.
const DATA = [
  { credential_id: 'MC-1', technician_id: 'T-4', record_type: 'epa_608',
    epa_section: 'type_ii', jurisdiction: null, credential_no: 'E-111',
    issuer: 'ESCO', issued_on: '2021-03-01', has_expiry: true, expires_on: '2026-03-01' },
  { credential_id: 'MC-2', technician_id: 'T-4', record_type: 'epa_608',
    epa_section: 'type_ii', jurisdiction: null, credential_no: 'E-222',
    issuer: 'ESCO', issued_on: '2026-02-01', has_expiry: true, expires_on: '2031-02-01' },
  { credential_id: 'MC-3', technician_id: 'T-9', record_type: 'state_license',
    epa_section: null, jurisdiction: 'universal', credential_no: 'OH-55',
    issuer: 'state board, Ohio', issued_on: '2025-06-01', has_expiry: true,
    expires_on: '2026-10-01' },
  { credential_id: 'MC-4', technician_id: 'T-9', record_type: 'epa_608',
    epa_section: 'universal', jurisdiction: null, credential_no: 'E-333',
    issuer: 'ESCO', issued_on: '2019-01-01', has_expiry: false, expires_on: null }
];
// The board as the server returns it: latestByKey() over DATA, classified.
// Written out rather than recomputed here, because the whole point of the
// export is that it does not re-derive the server's classification.
const BOARD = {
  today: '2026-09-16', warn_days: 60,
  counts: { current: 2, expiring: 1, expired: 0, unknown: 1 },
  unknown_count: 1,
  rows: [
    { technician_id: 'T-4', record_type: 'epa_608', epa_section: 'type_ii',
      jurisdiction: null, issued_on: '2026-02-01', expires_on: '2031-02-01',
      status: 'current', days: 1600, no_expiry: false },
    { technician_id: 'T-9', record_type: 'state_license', epa_section: null,
      jurisdiction: 'universal', issued_on: '2025-06-01', expires_on: '2026-10-01',
      status: 'expiring', days: 15, no_expiry: false },
    { technician_id: 'T-9', record_type: 'epa_608', epa_section: 'universal',
      jurisdiction: null, issued_on: '2019-01-01', expires_on: null,
      status: 'unknown', days: null, no_expiry: true }
  ]
};

function harness(opts) {
  opts = opts || {};
  const files = [];
  const toasts = [];
  const src = [
    grab('var MECH_TYPE_LABELS = {', '\n  };'),
    grab('var MECH_SECTION_LABELS = {', '\n  };'),
    grab('function mechCsvField(v) {', '\n  }'),
    grab('function mechCredKey(r) {', '\n  }'),
    grab('var MECH_EXPORTS = {', '\n  };'),
    grab('function mechExportDataset(key) {', '\n  }')
  ].join('\n\n');
  const ctx = {
    JSON, Object, Array, String, Number, Math, Boolean, Date, RegExp,
    showToast: (m) => toasts.push(String(m)),
    Blob: function (parts) { this.text = parts.join(''); },
    document: { createElement: () => ({ click() { files.push({ name: this.download, body: this.href.text }); } }) },
    window: { URL: { createObjectURL: (b) => b, revokeObjectURL: () => {} } }
  };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(src, ctx, { filename: 'sairnmechanical-exports-extract.js' });
  // `_mechCredLast` is the module-scoped cache mechCredRefresh() fills. The
  // extract declares it; this is the seam the suite drives through, and it is
  // set AFTER the source runs so `var _mechCredLast = null` cannot clobber it.
  ctx._mechCredLast = ('cache' in opts) ? opts.cache
    : { board: JSON.parse(JSON.stringify(BOARD)), data: JSON.parse(JSON.stringify(DATA)) };
  return { ctx, files, toasts };
}

function csv(opts) {
  const h = harness(opts);
  h.ctx.mechExportDataset('credentials');
  assert.strictEqual(h.files.length, 1, 'mechExportDataset wrote no file');
  return { file: h.files[0], lines: h.files[0].body.split('\r\n'), toasts: h.toasts };
}

function cells(lines, i) {
  const out = [];
  let cur = '', q = false;
  const s = lines[i];
  for (let j = 0; j < s.length; j++) {
    const c = s[j];
    if (q) {
      if (c === '"' && s[j + 1] === '"') { cur += '"'; j++; }
      else if (c === '"') q = false;
      else cur += c;
    } else if (c === '"') q = true;
    else if (c === ',') { out.push(cur); cur = ''; }
    else cur += c;
  }
  out.push(cur);
  return out;
}
function headerIndex(lines) {
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].indexOf('Technician ID,Credential ID,') === 0) return i;
  }
  throw new Error('no header row in the file:\n' + lines.slice(0, 14).join('\n'));
}
// By credential id, never by position: the file's order follows the server's
// `data` array and an assertion keyed on position would be testing the fixture.
function rowById(lines, id) {
  const h = headerIndex(lines);
  const head = cells(lines, h);
  const idx = head.indexOf('Credential ID');
  assert.ok(idx !== -1, 'no Credential ID column: ' + lines[h]);
  for (let i = h + 1; i < lines.length; i++) {
    const c = cells(lines, i);
    if (c[idx] === id) return { head, row: c, at: (n) => c[head.indexOf(n)] };
  }
  throw new Error(id + ' is not in the file:\n' + lines.join('\n'));
}

console.log('SAIRNmechanical -- the technician credential register as a FILE');

section('1. the export exists, runs, and its columns are wired to real fields');

test('one row per RECORD -- four, not the board\'s three', () => {
  const { lines } = csv();
  const h = headerIndex(lines);
  assert.strictEqual(lines.length - h - 1, DATA.length,
    'expected ' + DATA.length + ' data rows, got ' + (lines.length - h - 1) +
    '\n' + lines.join('\n'));
});

test('a record carries its number, issuer and issue date', () => {
  const { at, row } = rowById(csv().lines, 'MC-3');
  assert.strictEqual(at('Technician ID'), 'T-9', JSON.stringify(row));
  assert.strictEqual(at('Credential number'), 'OH-55', JSON.stringify(row));
  assert.strictEqual(at('Issuer'), 'state board, Ohio',
    'the comma in the issuer broke the quoting: ' + JSON.stringify(at('Issuer')));
  assert.strictEqual(at('Issued on'), '2025-06-01', JSON.stringify(row));
});

test('the STATUS is the server\'s word, not one recomputed here', () => {
  const { at } = rowById(csv().lines, 'MC-3');
  assert.strictEqual(at('Status (server, board rows only)'), 'expiring');
  assert.strictEqual(at('Days until expiry'), '15');
});

test('a lifetime credential says so from the STATED field, not from a blank date', () => {
  // has_expiry is stated at entry and the form refuses a record that leaves it
  // blank, precisely so nobody infers "lifetime" from a missing date. The file
  // carries the stated answer.
  const { at } = rowById(csv().lines, 'MC-4');
  assert.strictEqual(at('Expires?'), 'no — lifetime', JSON.stringify(at('Expires?')));
  assert.strictEqual(at('Expires on'), '');
  assert.strictEqual(at('Days until expiry'), '',
    'a day count was invented for a credential with no expiry');
  assert.strictEqual(at('Status (server, board rows only)'), 'unknown');
});

section('2. IT EXPORTS THE RECORDS, NOT THE BOARD');

test('a SUPERSEDED renewal is in the file, which the board does not show', () => {
  const { lines } = csv();
  const old = rowById(lines, 'MC-1');
  assert.strictEqual(old.at('Credential number'), 'E-111',
    'the superseded record is missing its own fields');
  assert.ok(/^no —/.test(old.at('On the board?')),
    'the superseded record is not marked as superseded: '
    + JSON.stringify(old.at('On the board?')));
});

test('...and the CURRENT record for the same key is marked as current', () => {
  const cur = rowById(csv().lines, 'MC-2');
  assert.ok(/^yes —/.test(cur.at('On the board?')), JSON.stringify(cur.row));
  assert.strictEqual(cur.at('Status (server, board rows only)'), 'current');
});

test('the superseded record carries NO status, because the board gave it none', () => {
  // The alternative -- copying the current record's status onto the superseded
  // one -- would state that a 2021 card expiring in 2026 is "current". A blank
  // is the honest answer: the server classified the key, not this row.
  const old = rowById(csv().lines, 'MC-1');
  assert.strictEqual(old.at('Status (server, board rows only)'), '',
    'a superseded record was given the current record\'s status: '
    + JSON.stringify(old.row));
});

test('TWO records sharing a key AND a date -- only ONE is marked current', () => {
  // The board shows one row per key. Matching a record to it on the issue date
  // alone marks both of a same-day pair as current, and the file then shows
  // two current rows where the screen shows one. The server's latestBy() keeps
  // the FIRST record seen when the ranking does not prefer the next; the export
  // walks `data` in the same order and consumes the board row on first match,
  // so the two agree without a second place computing the winner.
  const dup = JSON.parse(JSON.stringify(DATA));
  dup.push({ credential_id: 'MC-5', technician_id: 'T-4', record_type: 'epa_608',
             epa_section: 'type_ii', jurisdiction: null, credential_no: 'E-DUP',
             issuer: 'ESCO', issued_on: '2026-02-01', has_expiry: true,
             expires_on: '2031-02-01' });
  const h = harness({ cache: { board: JSON.parse(JSON.stringify(BOARD)), data: dup } });
  h.ctx.mechExportDataset('credentials');
  const lines = h.files[0].body.split('\r\n');
  const hi = headerIndex(lines);
  const head = cells(lines, hi);
  const onBoard = lines.slice(hi + 1)
    .map((_, i) => cells(lines, hi + 1 + i))
    .filter(c => /^yes —/.test(c[head.indexOf('On the board?')]));
  const key = onBoard.filter(c => c[head.indexOf('Technician ID')] === 'T-4');
  assert.strictEqual(key.length, 1,
    'both same-day records were marked current, so the file shows ' + key.length +
    ' current rows for a key the board shows once: ' +
    JSON.stringify(key.map(c => c[head.indexOf('Credential ID')])));
  assert.strictEqual(key[0][head.indexOf('Credential ID')], 'MC-2',
    'the tie went to the wrong record -- the server keeps the first seen');
});

test('the preamble COUNTS the superseded rows rather than leaving them implicit', () => {
  const { lines } = csv();
  const pre = lines.slice(0, headerIndex(lines)).join('\n');
  assert.ok(/ROWS IN THIS FILE: 4 \(3 currently shown on the board, 1 superseded/.test(pre),
    'the preamble does not say how much of this file the board is not showing:\n' + pre);
  assert.ok(/renewal\s+history/i.test(pre), pre);
});

test('the board counts and the UNKNOWN warning are in the file', () => {
  const { lines } = csv();
  const pre = lines.slice(0, headerIndex(lines)).join('\n');
  assert.ok(/2 current, 1 expiring, 0 expired, 1 unknown/.test(pre), pre);
  assert.ok(/UNKNOWN IS NOT A PASS/.test(pre),
    'the file lets an unknown read as a pass, which the board is careful not '
    + 'to do:\n' + pre);
  assert.ok(pre.indexOf('2026-09-16') !== -1 && /warning window of 60/.test(pre),
    'the classification date and warning window are not stated, so the status '
    + 'column has no as-of:\n' + pre);
});

section('3. EPA 608 SECTION IS ITS OWN COLUMN, and it is the regulated field');

test('the section is exported separately from the jurisdiction', () => {
  const { lines } = csv();
  const epa = rowById(lines, 'MC-2');
  const lic = rowById(lines, 'MC-3');
  assert.strictEqual(epa.at('EPA 608 section code'), 'type_ii');
  assert.strictEqual(epa.at('Jurisdiction'), '',
    'an EPA record picked up a jurisdiction it does not have');
  // THE COLLISION THE SCREEN CANNOT AVOID AND THE FILE MUST. MC-3's
  // jurisdiction is the literal string "universal", which is also an EPA
  // section code. Merged into one cell the way the panel does, filtering a
  // spreadsheet for Universal-section technicians would return a state licence.
  assert.strictEqual(lic.at('Jurisdiction'), 'universal');
  assert.strictEqual(lic.at('EPA 608 section code'), '',
    'a jurisdiction leaked into the EPA section column -- the exact collision '
    + 'the separate columns exist for: ' + JSON.stringify(lic.row));
});

test('the section code is carried BESIDE its full label, not instead of it', () => {
  const { at } = rowById(csv().lines, 'MC-2');
  assert.strictEqual(at('EPA 608 section'), 'Type II (high pressure)',
    'the file is unreadable to somebody who does not know the codes: '
    + JSON.stringify(at('EPA 608 section')));
  assert.strictEqual(at('EPA 608 section code'), 'type_ii',
    'the stored code was dropped, so the file cannot be matched back to the '
    + 'record');
});

test('the preamble states that sections are EQUIPMENT, not ranks', () => {
  const { lines } = csv();
  const pre = lines.slice(0, headerIndex(lines)).join('\n');
  assert.ok(/EQUIPMENT, NOT RANKS/.test(pre) && /82\.161/.test(pre), pre);
  assert.ok(/not an answer to whether somebody may open/.test(pre),
    'nothing warns against dispatching on "has an EPA card":\n' + pre);
});

section('4. NEVER LOADED IS NOT EMPTY');

test('an unread register REFUSES rather than writing a zero-row file', () => {
  const h = harness({ cache: null });
  h.ctx.mechExportDataset('credentials');
  assert.strictEqual(h.files.length, 0,
    'it wrote a file from a register nobody has read -- a zero-row file is a '
    + 'claim that the register is empty, which is the same claim '
    + 'MECH_NOT_SHOWN exists to refuse on screen');
  assert.ok(h.toasts.some(t => /has not been loaded/i.test(t)), JSON.stringify(h.toasts));
});

test('a failed refresh CLEARS the cache, so a stale board cannot be exported', () => {
  // The file and the screen must not be able to disagree. Every failure path in
  // mechCredRefresh() replaces the table with MECH_NOT_SHOWN; if the cache
  // survived, the Export button would still produce a file from the board that
  // is no longer on screen.
  const fn = grab('function mechCredRefresh() {', '\n  }');
  const at = fn.indexOf("mechData('read', 'mech_credentials'");
  assert.ok(at > 0, 'mechCredRefresh no longer reads mech_credentials');
  assert.ok(fn.slice(0, at).indexOf('_mechCredLast = null') !== -1,
    'the cache is not cleared BEFORE the read, so a refusal leaves the '
    + 'previous board exportable');
});

test('an unknown dataset key writes nothing and says so', () => {
  const h = harness();
  h.ctx.mechExportDataset('no_such_dataset');
  assert.strictEqual(h.files.length, 0);
  assert.ok(h.toasts.some(t => /No export is declared/.test(t)), JSON.stringify(h.toasts));
});

section('5. the registry DECLARES its resource, and something invokes it');

test('the credentials dataset names mech_credentials in the registry', () => {
  const reg = grab('var MECH_EXPORTS = {', '\n  };');
  assert.ok(/resource:\s*'mech_credentials'\s*,\s*action:\s*'read'/.test(reg),
    'the declaration is gone, so tools/export_coverage_check.py cannot see '
    + 'this export and the app reports as having none');
});

test('the Export CSV button exists and calls the registry', () => {
  assert.ok(html.indexOf("mechExportDataset('credentials')") !== -1,
    'no button calls mechExportDataset -- a registry nothing invokes is a '
    + 'feature nobody has, which is this app\'s own svNav() lesson');
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
