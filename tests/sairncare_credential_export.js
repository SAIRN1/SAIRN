// tests/sairncare_credential_export.js
//
// Run:  node tests/sairncare_credential_export.js
//
// `alf_staff_credentials` is Class A -- sairncare's own registry declares it
// append-only -- and until 2026-09-16 this facility could LOOK AT the
// credential and training ledger and could not PRODUCE it.
// docs/2026-09-14-class-a-retrievability.md carried "no -- app has no export
// machinery" against it, and that was true: there was no `createObjectURL`
// anywhere in the file.
//
// ── THE COLUMN FUNCTIONS ARE RUN, NOT READ ─────────────────────────────────
// Every column is a closure that dereferences a record and sometimes a second
// lookup (alfStaffName, certDaysUntil). A wrong field name is a silent empty
// cell and a diff cannot see it, which is exactly how SAIRNroofing exported
// eight rows with a blank job identifier and every other column correct --
// found by opening the file, not by the export succeeding. So this drives the
// real alfExportDataset() over seeded records and asserts on the CSV TEXT.
//
// ── AND THE TWO ARMS THAT ARE ABOUT THIS RESOURCE SPECIFICALLY ─────────────
//
//   1. THE SCOPE LINE. The server filters this ledger: a non-management
//      session gets only its own rows, and the panel says so on screen. A file
//      carrying three of forty rows with no note on it is indistinguishable
//      from a facility with three records -- and it is the one somebody hands
//      to a surveyor. Section 3 drives BOTH scope states and asserts the file
//      says which one it is, because a preamble that is right in one direction
//      and silent in the other is the defect, not the fix.
//
//   2. NEVER-LOADED IS NOT EMPTY. `_crRecords === null` means the panel has
//      not been refreshed. Exporting that as a zero-row file would be a
//      positive claim about the ledger that nothing has earned -- the same
//      distinction MECH_NOT_SHOWN and the vet reader already make on screen,
//      carried into the file. Section 4 asserts it REFUSES.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

// ALF_HTML lets a negative control point this suite at a MUTATED COPY in a temp
// directory instead of patching the tracked file and restoring it afterwards.
// Same convention DNT_HTML, SB_HTML and SV_HTML already carry.
const html = fs.readFileSync(process.env.ALF_HTML
  || path.join(__dirname, '..', 'sairncare.html'), 'utf8')
  .replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function grab(sig, terminator) {
  const at = html.indexOf(sig);
  assert.ok(at > 0, 'not found in sairncare.html: ' + sig);
  const end = html.indexOf(terminator, at);
  assert.ok(end > at, 'terminator not found after ' + sig);
  return html.slice(at, end + terminator.length);
}

// Two records of each kind, because the two entry types populate DIFFERENT
// fields -- a training row has hours and a category, a credential row has a
// name and an expiry -- and a registry that only ever saw one shape would pass
// with the other's columns wired to nothing.
const RECORDS = [
  { id: 'CRED-1', staff_id: 'E-7', record_type: 'training_hours', hours: 4.5,
    category: 'dementia', completed_on: '2026-09-01', notes: 'in-service, Q3',
    recorded_by: 'E-1', created_at: '2026-09-01T14:00:00.000Z' },
  { id: 'CRED-2', staff_id: 'E-9', record_type: 'credential',
    credential: 'CPR / BLS', expires_on: '2026-10-05', notes: '',
    recorded_by: 'E-1', created_at: '2026-09-02T09:30:00.000Z' },
  // A staff id the roster cannot resolve. A departed carer still has ledger
  // rows and they must stay attributable.
  { id: 'CRED-3', staff_id: 'E-GONE', record_type: 'credential',
    credential: 'Food handler', expires_on: '', notes: 'card, comma, quote "x"',
    recorded_by: 'E-1', created_at: '2026-08-30T08:00:00.000Z' }
];

function harness(opts) {
  opts = opts || {};
  const files = [];
  const toasts = [];
  const src = [
    grab('function alfCsvField(v){', '\n}'),
    grab('var ALF_EXPORTS={', '\n};'),
    grab('function alfExportDataset(key){', '\n}')
  ].join('\n\n');
  const ctx = {
    JSON, Object, Array, String, Number, Math, Boolean, Date, RegExp,
    _crRecords: opts.records === undefined
      ? JSON.parse(JSON.stringify(RECORDS)) : opts.records,
    _crScopedToSelf: !!opts.scoped,
    alfStaffName: (id) => ({ 'E-7': 'Ada Rowe', 'E-9': 'Kit Nam' })[id] || (id || '--'),
    certDaysUntil: (d) => d ? 19 : null,
    alfLocalToday: () => '2026-09-16',
    toast: (m) => toasts.push(String(m)),
    Blob: function (parts) { this.text = parts.join(''); },
    document: { createElement: () => ({ click() { files.push({ name: this.download, body: this.href.text }); } }) },
    window: { URL: { createObjectURL: (b) => b, revokeObjectURL: () => {} } }
  };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(src, ctx, { filename: 'sairncare-exports-extract.js' });
  return { ctx, files, toasts };
}

function csv(opts) {
  const h = harness(opts);
  h.ctx.alfExportDataset('credentials');
  assert.strictEqual(h.files.length, 1, 'alfExportDataset wrote no file');
  return { file: h.files[0], lines: h.files[0].body.split('\r\n'), toasts: h.toasts };
}

// The preamble is a variable number of single-cell lines before the header, so
// nothing may assume the header is line N. Found by its own column names.
function headerIndex(lines) {
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].indexOf('Staff,Staff ID,Entry ID,') === 0) return i;
  }
  throw new Error('no header row in the file:\n' + lines.slice(0, 12).join('\n'));
}
// Rows are found by Entry ID, never by position. The registry sorts newest
// first -- the same order rCredentials() renders, deliberately, so the file and
// the screen cannot disagree -- and an assertion keyed on input order would
// have been testing the fixture rather than the export. Section 1's last arm
// pins the order itself.
function rowById(lines, id) {
  const h = headerIndex(lines);
  const head = cells(lines, h);
  const idx = head.indexOf('Entry ID');
  assert.ok(idx !== -1, 'no Entry ID column: ' + lines[h]);
  for (let i = h + 1; i < lines.length; i++) {
    const c = cells(lines, i);
    if (c[idx] === id) return { head, row: c, at: (n) => c[head.indexOf(n)] };
  }
  throw new Error(id + ' is not in the file:\n' + lines.join('\n'));
}
function cells(lines, i) {
  // The fixture's data rows contain a quoted cell with a comma in it, so this
  // is a real split rather than String.split(','). Small, and it is the parser
  // the assertions depend on -- a naive split would let a quoting defect pass.
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

console.log('SAIRNcare -- the credential and training ledger as a FILE');

section('1. the export exists, runs, and its columns are wired to real fields');

test('one row per ledger entry, plus a header, plus the preamble', () => {
  const { lines } = csv();
  const h = headerIndex(lines);
  assert.strictEqual(lines.length - h - 1, RECORDS.length,
    'expected ' + RECORDS.length + ' data rows after the header, got ' +
    (lines.length - h - 1) + '\n' + lines.join('\n'));
  assert.ok(h > 0, 'there is no preamble at all -- the scope line is the point');
});

test('a TRAINING row carries hours, category and the completion date', () => {
  const { lines } = csv();
  const { row, at } = rowById(lines, 'CRED-1');
  assert.strictEqual(at('Type'), 'Training', JSON.stringify(row));
  assert.strictEqual(at('Hours'), '4.5', 'hours cell: ' + JSON.stringify(at('Hours')));
  assert.strictEqual(at('Training category'), 'dementia', JSON.stringify(row));
  assert.strictEqual(at('Completed on'), '2026-09-01', JSON.stringify(row));
  // A training row has no credential name and no expiry. Blank, not the string
  // "undefined" -- which is what a missing field produces when a column
  // concatenates instead of defaulting.
  assert.strictEqual(at('Credential'), '', JSON.stringify(at('Credential')));
  assert.strictEqual(at('Expires on'), '', JSON.stringify(at('Expires on')));
});

test('a CREDENTIAL row carries the name, the expiry and the derived days', () => {
  const { lines } = csv();
  const { row, at } = rowById(lines, 'CRED-2');
  assert.strictEqual(at('Type'), 'Credential', JSON.stringify(row));
  assert.strictEqual(at('Credential'), 'CPR / BLS', JSON.stringify(row));
  assert.strictEqual(at('Expires on'), '2026-10-05', JSON.stringify(row));
  // The SCREEN only shows a day count inside 30 days. The file carries it for
  // every dated row, because a reader sorting by "how close is this to
  // lapsing" cannot recover it from a date without knowing when the file was
  // made -- and the file says when it was made.
  assert.strictEqual(at('Days until expiry'), '19', JSON.stringify(at('Days until expiry')));
  assert.strictEqual(at('Hours'), '', 'a credential row invented an hours figure: ' + JSON.stringify(row));
});

test('a row with NO expiry leaves days blank rather than computing one', () => {
  const { lines } = csv();
  const { row, at } = rowById(lines, 'CRED-3');
  assert.strictEqual(at('Expires on'), '');
  assert.strictEqual(at('Days until expiry'), '',
    'a day count appeared for a row with no expiry date: ' + JSON.stringify(row));
});

test('the file is ordered NEWEST FIRST, the same order the panel renders', () => {
  // Not cosmetic. rCredentials() sorts by created_at descending and the file
  // must not present the same ledger in a different order -- "the file and the
  // screen must not be able to disagree" is the rule both SAIRNvet exports
  // already state in their own comments.
  const { lines } = csv();
  const h = headerIndex(lines);
  const head = cells(lines, h);
  const ids = lines.slice(h + 1).map((_, i) => cells(lines, h + 1 + i)[head.indexOf('Entry ID')]);
  assert.deepStrictEqual(ids, ['CRED-2', 'CRED-1', 'CRED-3'],
    'the export order does not match the panel order: ' + JSON.stringify(ids));
});

section('2. the staff name is resolved, and the id is kept BESIDE it');

test('a known staff id resolves to a name and keeps the id', () => {
  const { lines } = csv();
  const { row, at } = rowById(lines, 'CRED-1');
  assert.strictEqual(at('Staff'), 'Ada Rowe', JSON.stringify(row));
  assert.strictEqual(at('Staff ID'), 'E-7',
    'the raw staff id was dropped, so a departed carer\'s rows become '
    + 'unattributable: ' + JSON.stringify(row));
});

test('an UNRESOLVABLE staff id still exports, and the id is intact', () => {
  const { lines } = csv();
  const { row, at } = rowById(lines, 'CRED-3');
  assert.strictEqual(at('Staff ID'), 'E-GONE', JSON.stringify(row));
});

test('a cell containing a comma and a quote survives the quoting', () => {
  const { lines } = csv();
  const { at } = rowById(lines, 'CRED-3');
  assert.strictEqual(at('Notes'), 'card, comma, quote "x"',
    'the CSV quoting mangled a cell: ' + JSON.stringify(at('Notes')));
});

section('3. THE SCOPE LINE -- a partial file must say it is partial');

test('a SCOPED read says in the FILE that this is not the whole ledger', () => {
  const { lines, toasts } = csv({ scoped: true });
  const pre = lines.slice(0, headerIndex(lines)).join('\n');
  assert.ok(/NOT THE WHOLE LEDGER/.test(pre),
    'a scoped export does not say it is scoped:\n' + pre);
  assert.ok(/not management/i.test(pre), pre);
  assert.ok(toasts.some(t => /YOUR OWN RECORDS ONLY/.test(t)),
    'the toast did not say it either: ' + JSON.stringify(toasts));
});

test('an UNSCOPED read says so too, rather than saying nothing', () => {
  // Silence in one direction is how a reader learns to ignore the line. Both
  // states are stated, and both come from the server's own answer rather than
  // being guessed from the row count.
  const { lines } = csv({ scoped: false });
  const pre = lines.slice(0, headerIndex(lines)).join('\n');
  assert.ok(/SCOPE: the server returned the full ledger/.test(pre),
    'the unscoped case says nothing about scope:\n' + pre);
  assert.ok(!/NOT THE WHOLE LEDGER/.test(pre),
    'the unscoped file claims to be partial:\n' + pre);
});

test('the preamble states the row count and that this is append-only', () => {
  const { lines } = csv();
  const pre = lines.slice(0, headerIndex(lines)).join('\n');
  assert.ok(pre.indexOf('ROWS IN THIS FILE: ' + RECORDS.length) !== -1, pre);
  assert.ok(/append-only/i.test(pre) && /never an edit/i.test(pre),
    'nothing tells the reader a staff member may appear more than once:\n' + pre);
  assert.ok(/not a compliance figure/i.test(pre),
    'nothing warns against summing hours across training categories:\n' + pre);
});

section('4. NEVER LOADED IS NOT EMPTY');

test('_crRecords === null REFUSES rather than writing a zero-row file', () => {
  const h = harness({ records: null });
  h.ctx.alfExportDataset('credentials');
  assert.strictEqual(h.files.length, 0,
    'it wrote a file from a ledger nobody has loaded -- a zero-row file is a '
    + 'claim that the ledger is empty');
  assert.ok(h.toasts.some(t => /not been loaded/i.test(t)),
    'and it did not say why: ' + JSON.stringify(h.toasts));
});

test('a genuinely EMPTY ledger does export, with zero data rows', () => {
  // The other side of the same distinction. A facility that has recorded
  // nothing is entitled to a file saying so.
  const { lines } = csv({ records: [] });
  const h = headerIndex(lines);
  assert.strictEqual(lines.length - h - 1, 0, lines.join('\n'));
  assert.ok(lines.slice(0, h).join('\n').indexOf('ROWS IN THIS FILE: 0') !== -1,
    lines.slice(0, h).join('\n'));
});

test('an unknown dataset key writes nothing and says so', () => {
  const h = harness();
  h.ctx.alfExportDataset('no_such_dataset');
  assert.strictEqual(h.files.length, 0);
  assert.ok(h.toasts.some(t => /No export is declared/.test(t)), JSON.stringify(h.toasts));
});

section('5. the registry DECLARES its resource, which is what the coverage '
      + 'checker reads');

test('the credentials dataset names alf_staff_credentials in the registry', () => {
  // tools/export_coverage_check.py answers "can this Class A record be produced
  // as a file" by finding `resource:'x',action:'read'` in the registry. Without
  // the declaration the answer falls back to an accessor-chain inference that
  // does not exist for a server-backed resource, and the app reports as having
  // no export at all -- which is the state this whole file is closing.
  const reg = grab('var ALF_EXPORTS={', '\n};');
  assert.ok(/resource:\s*'alf_staff_credentials'\s*,\s*action:\s*'read'/.test(reg),
    'the declaration is gone, so the coverage checker cannot see this export');
});

test('the Export CSV button exists and calls the registry, not a one-off', () => {
  assert.ok(html.indexOf('alfExportDataset(\'credentials\')') !== -1,
    'no button calls alfExportDataset -- a registry nothing invokes is a '
    + 'feature nobody has');
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
