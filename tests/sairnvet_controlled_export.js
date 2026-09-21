// tests/sairnvet_controlled_export.js
//
// Run:  node tests/sairnvet_controlled_export.js
//
// `svExportControlled()` is the only way `sv_controlled` -- a Class A,
// DEA-relevant record -- can be produced as a FILE, and nothing ran it. The
// hover auditor flagged the gap (entry #204) as real and lower-severity, and
// it is the ordinary shape: the function was reviewed by reading it, the
// button was clicked once by hand, and no arm has ever asserted what comes out.
//
// ── WHY READING IT IS NOT ENOUGH, ON THIS FUNCTION SPECIFICALLY ────────────
// It builds the file from the RENDERED TABLE, deliberately -- "the file and
// the screen must not be able to disagree", the same call svExportDoseAudit
// makes. That is the right decision and it makes the export depend on DOM
// details no diff shows: which rows `querySelectorAll('tr')` reaches, which
// cells `th,td` reaches, and whether `textContent` preserves the one cell an
// inspector is actually looking for. Every one of those is a silent
// wrong-output failure, not a crash.
//
// ── THE ARM THAT MATTERS IS SECTION 3 ─────────────────────────────────────
// The file carries six preamble lines and every one of them is a REFUSAL to
// overstate: which copy this is, that it is a per-drug balance and not a
// transaction history, that the record is not append-only and not
// tamper-evident, and that the On Hand column must not be summed because the
// units differ between rows. That last one is not decoration -- the KPI
// directly above this table recorded a real defect where millilitres were
// added to milligrams and printed as a controlled-substance balance. A file
// that loses those lines is a file that reads as more than it is, which on a
// DEA record is the whole risk.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

// SV_HTML lets a negative control point this suite at a MUTATED COPY in a temp
// directory rather than patching the tracked file. Same convention four other
// SAIRNvet suites already carry.
const html = fs.readFileSync(process.env.SV_HTML
  || path.join(__dirname, '..', 'sairnvet.html'), 'utf8')
  .replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function grab(sig, terminator) {
  const at = html.indexOf(sig);
  assert.ok(at > 0, 'not found in sairnvet.html: ' + sig);
  const end = html.indexOf(terminator, at);
  assert.ok(end > at, 'terminator not found after ' + sig);
  return html.slice(at, end + terminator.length);
}

// ── THE FAKE TABLE, AND WHY IT IS BUILT AND NOT MOCKED WHOLESALE ──────────
// svExportControlled walks the DOM with querySelectorAll('tbody tr') for the
// COUNT and querySelectorAll('tr') for the CONTENT -- two different selectors,
// which is exactly the pair a stub returning one array would paper over. So
// this models a real thead/tbody split and answers the two selectors
// differently, the way a browser does.
function cell(text) { return { textContent: text }; }
function row(cells) {
  return { cells: cells.map(cell),
           querySelectorAll(sel) { assert.strictEqual(sel, 'th,td'); return this.cells; } };
}
function table(headers, bodyRows) {
  const head = headers ? [row(headers)] : [];
  const body = bodyRows.map(row);
  return {
    querySelectorAll(sel) {
      if (sel === 'tbody tr') return body;
      if (sel === 'tr') return head.concat(body);
      throw new Error('unexpected selector: ' + sel);
    }
  };
}

const HEADERS = ['Drug', 'Schedule', 'On Hand', 'Last Transaction', 'Balance Check'];
const ROWS = [
  ['Fentanyl', 'II', '12mL', 'Dispensed 2026-09-15, "Rex", tech AB', 'Balanced'],
  // The row an inspector is looking for. The screen renders it inside a span
  // with a warning colour; textContent is what reaches the file, and losing it
  // would leave a negative balance looking Balanced.
  ['Ketamine', 'III', '-3mg', 'Adjusted, count short', '⚠ NEGATIVE — investigate'],
  ['Butorphanol', 'IV', '40mg', '', 'Balanced']
];

function harness(opts) {
  opts = opts || {};
  const files = [];
  const toasts = [];
  // ── THE GUARD IS PART OF THE FUNCTION UNDER TEST NOW (2026-09-18) ────────
  // This extracted svExportControlled() ALONE, which was complete until the
  // CSV formula-injection sweep (885fd0b9, 2026-09-17 18:07) made it call
  // svCsvCell(). From that commit this suite was 3 passed / 19 FAILED with
  // `svCsvCell is not defined` on a Class A DEA-relevant record, and it stayed
  // that way unnoticed -- 22/22 green against sairnvet.html at 885fd0b9^,
  // driven both ways to establish that rather than infer it.
  //
  // PULLED FROM THE APP, NOT RE-IMPLEMENTED IN THE SANDBOX. A hand-written
  // stand-in would let the app's real guard rot while every arm below kept
  // passing, which is the exact shape section 3 of this file exists to refuse.
  // The sweep is entitled to add a dependency; a suite that extracts one
  // function by signature is what has to notice.
  const src = grab('function svCsvCell(', '\n')
            + grab('function svExportControlled(){', '\n}');
  const el = ('table' in opts) ? opts.table : table(HEADERS, ROWS);
  const ctx = {
    JSON, Object, Array, String, Number, Math, Boolean, Date, RegExp,
    showToast: (m, kind) => toasts.push({ msg: String(m), kind: kind }),
    Blob: function (parts, o) { this.text = parts.join(''); this.type = o && o.type; },
    document: {
      getElementById: (id) => (id === 'panel-controlled-table' ? el : null),
      createElement: () => ({
        click() { files.push({ name: this.download, body: this.href.text, type: this.href.type }); }
      })
    },
    URL: { createObjectURL: (b) => b, revokeObjectURL: () => {} }
  };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(src, ctx, { filename: 'sairnvet-controlled-export-extract.js' });
  return { ctx, files, toasts };
}

function csv(opts) {
  const h = harness(opts);
  h.ctx.svExportControlled();
  assert.strictEqual(h.files.length, 1, 'svExportControlled wrote no file');
  return { file: h.files[0], lines: h.files[0].body.split('\n'), toasts: h.toasts };
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
    if (cells(lines, i)[0] === 'Drug') return i;
  }
  throw new Error('the column header row is not in the file:\n' + lines.join('\n'));
}

console.log('SAIRNvet -- what svExportControlled() actually writes');

section('1. it produces a CSV, and every rendered row reaches it');

test('one line per rendered row, plus the table header, plus the preamble', () => {
  const { lines } = csv();
  const h = headerIndex(lines);
  assert.ok(h > 0, 'there is no preamble -- the six refusals are the point');
  // A trailing newline produces a final empty element; the rows are what sits
  // between the header and it.
  const data = lines.slice(h + 1).filter(l => l !== '');
  assert.strictEqual(data.length, ROWS.length,
    'expected ' + ROWS.length + ' data rows, got ' + data.length + '\n' + lines.join('\n'));
});

test('the SCREEN\'s column headers are in the file, not a second set', () => {
  // The export takes `tr`, not `tbody tr`, so the thead row comes through. That
  // is the reason the file's columns cannot drift from the panel's.
  const { lines } = csv();
  assert.deepStrictEqual(cells(lines, headerIndex(lines)), HEADERS);
});

test('every cell of a row survives, in order', () => {
  const { lines } = csv();
  const h = headerIndex(lines);
  assert.deepStrictEqual(cells(lines, h + 1), ROWS[0],
    'a cell was dropped or reordered: ' + lines[h + 1]);
});

test('a cell containing a comma and quotes survives the quoting', () => {
  const { lines } = csv();
  const h = headerIndex(lines);
  assert.strictEqual(cells(lines, h + 1)[3], ROWS[0][3],
    'the CSV quoting mangled the transaction note: ' + JSON.stringify(cells(lines, h + 1)[3]));
});

test('THE NEGATIVE BALANCE REACHES THE FILE', () => {
  // The one cell a DEA inspection is looking for. It is rendered inside a
  // styled span; if the export ever moved to reading innerHTML, or to the
  // underlying record instead of the screen, this is the cell that would go
  // quiet -- and a short count would export as Balanced.
  const { lines } = csv();
  const h = headerIndex(lines);
  const r = cells(lines, h + 2);
  assert.strictEqual(r[0], 'Ketamine', JSON.stringify(r));
  assert.ok(/NEGATIVE/.test(r[4]),
    'a negative balance did not survive into the file: ' + JSON.stringify(r));
  // ── THE APOSTROPHE IS THE CSV GUARD AND IT IS EXPECTED, NOT TOLERATED ────
  // From 885fd0b9 this cell is `'-3mg`, not `-3mg`. svCsvCell() forces text on
  // any cell whose first character is =/+/-/@ UNLESS the whole cell parses as
  // a number -- so `-50.00` passes through untouched and `-3mg`, which has a
  // unit suffix, does not. That is the guard's stated rule working as designed:
  // `-1+1` is a formula and nothing can tell it from `-3mg` by looking at the
  // first character.
  //
  // THIS ASSERTION WAS CHANGED TO MATCH NEW BEHAVIOUR, WHICH IS NORMALLY THE
  // WRONG MOVE, SO THE REASONING IS HERE RATHER THAN IN A COMMIT MESSAGE
  // NOBODY WILL FIND. The alternative was to relax the guard for
  // unit-suffixed quantities, and weakening a formula-injection control on a
  // DEA record to make a test pass is not a trade this suite gets to make.
  // What it CAN do is assert the two things that actually matter and keep the
  // quantity itself under assertion: the sign and the magnitude must both be
  // intact, and only the leading apostrophe may differ.
  //
  // STILL OPEN, AND FLAGGED RATHER THAN DECIDED HERE: a downstream reader of
  // this file -- a DEA reporting tool, a script, an auditor's import -- sees
  // the literal `'-3mg`. Excel and Calc strip the apostrophe on display; a
  // parser does not. Whether that is acceptable on a Class A record is a
  // question for whoever owns that reporting path, not for this arm.
  assert.strictEqual(r[2].replace(/^'/, ''), '-3mg',
    'the negative quantity was lost: ' + JSON.stringify(r));
  assert.ok(/^'?-3mg$/.test(r[2]),
    'the quantity cell is neither -3mg nor the guarded \'-3mg: ' + JSON.stringify(r[2]));
});

test('an empty cell stays empty rather than becoming "undefined" or "null"', () => {
  const { lines } = csv();
  const h = headerIndex(lines);
  assert.strictEqual(cells(lines, h + 3)[3], '', JSON.stringify(cells(lines, h + 3)));
});

section('2. the row COUNT in the file is the body rows, not the rendered lines');

test('ROWS IN THIS FILE counts tbody rows and excludes the header', () => {
  const { lines } = csv();
  const pre = lines.slice(0, headerIndex(lines)).join('\n');
  assert.ok(pre.indexOf('ROWS IN THIS FILE: ' + ROWS.length) !== -1,
    'the stated count does not match the rows: \n' + pre);
});

test('an EMPTY register exports a file that says zero, not a file that lies', () => {
  // renderControlled() leaves the tbody genuinely empty rather than writing a
  // placeholder row, so zero here is a fact about the register. A placeholder
  // would be counted as a row and exported as one, which is why this is pinned.
  const { lines, file } = csv({ table: table(HEADERS, []) });
  const pre = lines.slice(0, headerIndex(lines)).join('\n');
  assert.ok(pre.indexOf('ROWS IN THIS FILE: 0') !== -1, pre);
  const data = lines.slice(headerIndex(lines) + 1).filter(l => l !== '');
  assert.strictEqual(data.length, 0, 'an empty register produced rows: ' + file.body);
});

section('3. THE SIX REFUSALS -- a file that does not overstate what it is');

const PREAMBLE = [
  ['names the resource and stamps the export', /SAIRNvet controlled-substance register — exported \d{4}-\d{2}-\d{2}T/],
  ['says WHICH COPY, because this is the local one', /WHICH COPY: the LOCAL record on this device/],
  ['...and that this is not a statement about the server', /not a statement about what the server holds/],
  ['says it is a per-DRUG balance and NOT a transaction history',
   /one row per DRUG with its CURRENT balance[\s\S]*NOT a transaction history/],
  ['...and points at sv_audit_log, which is the per-event trail', /Dosing Audit Trail \(sv_audit_log\)/],
  ['says the record is NOT append-only and NOT tamper-evident',
   /NOT APPEND-ONLY AND IS NOT TAMPER-EVIDENT/],
  ['...and that a corrected balance leaves no trace of what it replaced',
   /leaves no trace of the value[\s\S]*it replaced/],
  ['REFUSES THE SUM: the units differ between rows', /Do not sum the column/],
  // ── ADDED 2026-09-21: the one thing DONE to the file, not just what it IS ──
  // The arm above this section's own note used to say "six refusals"; there
  // were already eight regexes and now there are ten, which is why the count
  // lives in the anchors and not in a number. This pair is a different KIND of
  // line from the seven above it: those say what the file is and is not, this
  // says what was done to its cells.
  //
  // WHY IT BELONGS ON A DEA RECORD. svCsvCell() prefixes an apostrophe to any
  // cell starting = + - @ tab or CR that is not a plain number, so `-3mg`
  // becomes `'-3mg` while `-50.00` is untouched. Excel and Calc strip it on
  // display; a parser does not, and a numeric parse of the quantity then
  // fails. Nothing in this repo imports this file, so the owner of any
  // downstream reporting path is outside it and had no way to learn the quirk
  // except by hitting it.
  ['DECLARES the apostrophe guard, because a parser sees it and a human does not',
   /apostrophe[\s\S]*cannot[\s\S]*formula/i],
  ['...and says what to DO about it rather than only that it happens',
   /strip a[\s\S]*leading apostrophe before parsing/i]
];
PREAMBLE.forEach(([name, re]) => {
  test(name, () => {
    const { lines } = csv();
    const pre = lines.slice(0, headerIndex(lines)).join('\n');
    assert.ok(re.test(pre), 'missing from the preamble:\n' + pre);
  });
});

test('each preamble line is ONE quoted cell, so a comma in it cannot split it', () => {
  // The preamble sentences are full of commas. If any of them were written
  // unquoted the file would still open, and the sentence would arrive split
  // across columns -- present, unreadable, and passing any arm that only greps
  // the raw text. So this asserts the PARSED shape.
  const { lines } = csv();
  for (let i = 0; i < headerIndex(lines); i++) {
    if (lines[i] === '') continue;
    const c = cells(lines, i);
    assert.strictEqual(c.length, 1,
      'preamble line ' + i + ' parses as ' + c.length + ' cells: ' + lines[i]);
  }
});

section('4. failure and shape');

test('NO TABLE means no file and a stated refusal', () => {
  const h = harness({ table: null });
  h.ctx.svExportControlled();
  assert.strictEqual(h.files.length, 0,
    'it wrote a file with no table to read -- a zero-row file is a claim that '
    + 'the register is empty');
  assert.ok(h.toasts.length === 1 && h.toasts[0].kind === 'error',
    'the refusal was silent or not marked an error: ' + JSON.stringify(h.toasts));
});

test('the blob is text/csv and the filename names the record', () => {
  const { file } = csv();
  assert.strictEqual(file.type, 'text/csv');
  assert.strictEqual(file.name, 'controlled-substance-register.csv');
});

test('the success toast names the file rather than saying "done"', () => {
  const { toasts } = csv();
  assert.ok(toasts.some(t => /controlled-substance-register\.csv/.test(t.msg)),
    JSON.stringify(toasts));
});

section('5. it is WIRED -- a writer nothing invokes is a feature nobody has');

test('the Controlled Substances panel has a button calling it', () => {
  assert.ok(/onclick="svExportControlled\(\)"/.test(html),
    'nothing in the markup calls svExportControlled -- this app\'s own svNav() '
    + 'comment records a renderer nothing called leaving a panel permanently '
    + 'empty while the gap looked closed');
});

test('...and it reads the table the panel actually renders into', () => {
  // The button and the function must name the same table. Two ids that drifted
  // apart would fail at run time with "Nothing to export" -- the same message
  // an empty register gets, which is how it would be mistaken for one.
  assert.ok(html.indexOf('id="panel-controlled-table"') !== -1,
    'panel-controlled-table is not in the markup');
  assert.ok(grab('function svExportControlled(){', '\n}')
    .indexOf("getElementById('panel-controlled-table')") !== -1,
    'the export reads a different table from the one the panel renders');
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
