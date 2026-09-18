// tests/sairndental_ledger_export.js
//
// Run:  node tests/sairndental_ledger_export.js
//
// SAIRNdental's export registry carried NINE datasets and neither of the two
// resources its own registry file declares APPEND-ONLY: dnt_charges and
// dnt_payments. The only billing export was `ageing` -- five derived buckets
// and a total -- and a Billing panel with an Export CSV button on it reads as
// exported. A bucket total is not the row-level record, and an auditor asking
// what was charged and what was paid cannot be handed five buckets.
//
// dnt_vendor_orders was the same near-miss one resource over: the registry
// exported `supplies`, which is dnt_supplies -- the mutable stock list, not the
// append-only purchase archive.
//
// THE COLUMN FUNCTIONS ARE RUN, NOT READ. Every column is a closure that
// dereferences a record and often a second collection (patients,
// procedureTypes), so a wrong field name or a missing lookup is a silent empty
// cell or a throw, and neither is visible in a diff. This drives the real
// exportDataset() over seeded data and asserts on the CSV TEXT it produces.
//
// AND IT ASSERTS THE THING THAT WAS ACTUALLY WRONG: that the charges export is
// not the ageing export. An export named for a dataset that emits a DIFFERENT,
// aggregated dataset is exactly the defect this registry's own header says it
// was written to remove.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

// DNT_HTML lets a negative control point this suite at a MUTATED COPY in a temp
// directory instead of patching the tracked file and restoring it afterwards.
// Same convention SB_HTML and SV_HTML already carry, rather than a third one
// being invented. Unset -- every ordinary run, including CI -- this is exactly
// what it was.
const html = fs.readFileSync(process.env.DNT_HTML
  || path.join(__dirname, '..', 'sairndental.html'), 'utf8')
  .replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function grab(sig, terminator) {
  const at = html.indexOf(sig);
  assert.ok(at > 0, 'not found in sairndental.html: ' + sig);
  const end = html.indexOf(terminator, at);
  assert.ok(end > at, 'terminator not found after ' + sig);
  return html.slice(at, end + terminator.length);
}

const CHARGES = [
  { id: 'CH-1', patient_id: 'P-1', appointment_id: 'A-9', procedure_type_id: 'PR-1',
    amount: 180, estimated_insurance_portion: 90, date: '2026-09-01' },
  { id: 'CH-2', patient_id: 'P-2', appointment_id: '', procedure_type_id: 'PR-2',
    amount: 42.5, estimated_insurance_portion: 0, date: '2026-09-02' }
];
const PAYMENTS = [
  { id: 'PM-1', patient_id: 'P-1', amount: 90, method: 'card', date: '2026-09-03' }
];
const ORDERS = [
  { id: 'VORD-1', date: '2026-09-04T10:00:00.000Z', vendor: 'Benco', vendorKey: 'benco',
    total: 61.5,
    items: [{ qty: 2, name: 'Nitrile gloves, M', sku: 'GL-M', effectivePrice: 12.75 },
            { qty: 1, name: 'Composite, A2', sku: 'CO-A2', effectivePrice: 36 }] }
];

function harness() {
  const files = [];
  const src = [
    // dntCsvField delegates to the formula-injection guard since 2026-09-17, so
    // the guard has to come with it. PULLED FROM THE REAL FILE rather than
    // stubbed: a stub would let the guard rot while these arms stayed green,
    // and the guard is the only thing standing between a patient-typed field
    // and a formula executing in whoever opens the export.
    grab('function dntCsvCell(v)', '\n'),
    grab('function dntCsvField(v){', '\n}'),
    grab('function dntYesNo(v){', '\n'),
    grab('var DNT_CRED_COMMON={', '\n'),
    grab('function dntCredDetails(rec){', '\n}'),
    grab('var DNT_EXPORTS={', '\n};'),
    grab('function exportDataset(key){', '\n}')
  ].join('\n\n');
  const ctx = {
    JSON, Object, Array, String, Number, Math, Boolean,
    charges: () => JSON.parse(JSON.stringify(CHARGES)),
    payments: () => JSON.parse(JSON.stringify(PAYMENTS)),
    vendorOrderHistory: () => JSON.parse(JSON.stringify(ORDERS)),
    patients: () => [{ id: 'P-1', name: 'Ada Rowe' }, { id: 'P-2', name: 'Kit Nam' }],
    providers: () => [],
    procedureTypes: () => [{ id: 'PR-1', cdt_code: 'D2740', description: 'Crown' },
                           { id: 'PR-2', cdt_code: 'D1110', description: 'Prophy' }],
    supplies: () => [],
    referrals: () => [],
    credentials: () => [],
    gfeRecords: () => [],
    txPlans: () => [],
    denials: () => [],
    rcRows: () => [],
    dnAging: () => ({ buckets: [{ label: '0-30', count: 1, amount: 180 }], undated: 0 }),
    dntLocalToday: () => '2026-09-14',
    toast: () => {},
    Blob: function (parts) { this.text = parts.join(''); },
    document: { createElement: () => ({ click() { files.push({ name: this.download, body: this.href.text }); } }) },
    window: { URL: { createObjectURL: (b) => b, revokeObjectURL: () => {} } }
  };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(src, ctx, { filename: 'sairndental-exports-extract.js' });
  return { ctx, files };
}

function csv(key) {
  const h = harness();
  h.ctx.exportDataset(key);
  assert.strictEqual(h.files.length, 1, 'exportDataset("' + key + '") wrote no file');
  return h.files[0];
}

console.log('SAIRNdental -- the two append-only money records, and the order archive');

section('1. every new export actually produces a file, and its columns RUN');

test('charges exports one row per charge, with the id kept', () => {
  const f = csv('charges');
  const lines = f.body.split('\r\n');
  assert.strictEqual(lines.length, 1 + CHARGES.length,
    'expected a header and ' + CHARGES.length + ' rows, got ' + lines.length);
  assert.ok(/^Date,Charge ID,Patient,Patient ID,/.test(lines[0]), lines[0]);
  assert.ok(lines[1].indexOf('CH-1') !== -1, 'the charge id is not in the row: ' + lines[1]);
});

test('payments the same, and the method survives', () => {
  const f = csv('payments');
  const lines = f.body.split('\r\n');
  assert.strictEqual(lines.length, 1 + PAYMENTS.length, lines.join('|'));
  assert.ok(lines[1].indexOf('PM-1') !== -1, lines[1]);
  assert.ok(lines[1].indexOf('card') !== -1, lines[1]);
});

test('vendor orders export one row per ORDER with the lines flattened', () => {
  const f = csv('vendororders');
  const lines = f.body.split('\r\n');
  assert.strictEqual(lines.length, 1 + ORDERS.length, lines.join('|'));
  // Both line items are present in the one cell. Dropping the second is the
  // quietly-partial defect this registry's header exists to describe.
  assert.ok(lines[1].indexOf('GL-M') !== -1 && lines[1].indexOf('CO-A2') !== -1,
    'a line item is missing from the flattened cell: ' + lines[1]);
  assert.ok(lines[1].indexOf('VORD-1') !== -1, lines[1]);
});

section('2. ids are RESOLVED to names, and the raw id is kept beside them');

test('a charge names its patient and its procedure, and still carries both ids', () => {
  const row = csv('charges').body.split('\r\n')[1];
  assert.ok(row.indexOf('Ada Rowe') !== -1, 'patient not resolved: ' + row);
  assert.ok(row.indexOf('D2740') !== -1, 'procedure not resolved: ' + row);
  assert.ok(row.indexOf('P-1') !== -1, 'the raw patient id was dropped: ' + row);
  assert.ok(row.indexOf('PR-1') !== -1, 'the raw procedure id was dropped: ' + row);
});

test('a patient who no longer exists leaves the NAME blank and the ID intact', () => {
  // A deleted patient still has charges. Resolving to a name INSTEAD of the id
  // would make those rows unattributable, which is worse than a blank cell.
  const h = harness();
  h.ctx.patients = () => [];
  h.ctx.exportDataset('charges');
  const lines = h.files[0].body.split('\r\n');
  const row = lines[1];
  assert.ok(row.indexOf('P-1') !== -1, 'the id went with the name: ' + row);
  // ── THE LABEL PROMISED BOTH HALVES AND THE ASSERTION TESTED ONE ──────────
  // Added 2026-09-16 by tests/sairndental_ledger_export_mutation_control.js,
  // which changed the Patient column to fall back to `r.patient_id` and WATCHED
  // THIS ARM PASS. The id was still in the row -- twice -- so the only
  // assertion here was satisfied by exactly the defect the arm is named after.
  // A cell headed Patient holding an identifier nobody can resolve looks like
  // data and is not, which is the whole reason blank is the right answer.
  //
  // Split naively on commas. Sound HERE -- the two cells before Patient are a
  // date and an id, neither of which can contain a comma in this fixture -- and
  // GUARDED below rather than left resting on that sentence.
  //
  // ── THE COMMENT ABOVE USED TO NAME THE WRONG FRAGILITY, AND THE RIGHT ONE
  //    PASSED ON THE DEFECT (2026-09-18, independent review) ────────────────
  // It said the reasoning could rot "if a column is reordered". It cannot:
  // `head.indexOf('Patient')` tracks a reorder. The real fragility is a comma
  // inside any cell BEFORE Patient, because dntCsvCell() QUOTES such a cell and
  // a naive split then tears it into pieces.
  //
  // MOSTLY THAT FAILS SAFE -- a charge id 'CH,1' quotes to "CH,1" and cells[2]
  // becomes '1"', so the arm goes red on correct code. BUT NOT ALWAYS. Any
  // preceding cell carrying two adjacent commas at the right offset yields
  // cells[2] === '' and THIS ARM PASSED WITH THE NAME-IS-ID DEFECT PRESENT --
  // driven with date values 'a,,,b', 'a,,,,b', 'x,,,y,,,z' and ',,,,', all four
  // green on the mutated app. That is precisely the defect this arm was fixed
  // for in the first place, reappearing one layer down.
  //
  // THE GUARD IS A COUNT, NOT A PARSER. If the split disagrees with the header
  // the row contains a quoted comma and the naive index is meaningless -- so
  // the arm REFUSES rather than indexing into the pieces. "Could not tell" is a
  // third state and is never folded into "passed" (PR 1.11). A real parser
  // would be the wrong trade here: it would make this arm keep answering on
  // input shapes nobody has decided are legal, where a refusal makes somebody
  // look.
  //
  // IT IS DORMANT TODAY BY CONSTRUCTION -- Date and Charge ID are both app
  // generated -- and it arms itself the moment a free-text column is INSERTED
  // before Patient, which is the change the old comment should have warned
  // about.
  const head = lines[0].split(',');
  const cells = row.split(',');
  const nameIdx = head.indexOf('Patient');
  assert.ok(nameIdx !== -1, 'no Patient column in the header: ' + lines[0]);
  assert.strictEqual(cells.length, head.length,
    'a cell in this row contains a quoted comma, so splitting on commas does '
    + 'NOT line up with the header and the Patient cell cannot be located. '
    + 'This arm is REFUSING rather than indexing into the pieces -- it is not a '
    + 'pass and it is not a failure of the export. header=' + head.length
    + ' cells=' + cells.length + '  row=' + JSON.stringify(row));
  assert.strictEqual(cells[nameIdx], '',
    'the NAME cell must be BLANK, not an unresolvable identifier: ' + JSON.stringify(cells[nameIdx]));
});

section('3. the derived ageing export is NOT a substitute, and never was');

test('ageing and charges are different files with different shapes', () => {
  const a = csv('ageing'), c = csv('charges');
  assert.notStrictEqual(a.body, c.body);
  assert.ok(a.body.split('\r\n')[0].indexOf('Bucket') === 0,
    'ageing no longer exports buckets: ' + a.body.split('\r\n')[0]);
  assert.ok(c.body.split('\r\n')[0].indexOf('Bucket') === -1,
    'the charges export is emitting the ageing summary');
});

test('ageing carries NO charge id, which is why it could not stand in', () => {
  const a = csv('ageing');
  assert.ok(a.body.indexOf('CH-1') === -1,
    'ageing suddenly carries row ids -- if that is deliberate this arm needs '
    + 'rewriting, but it was the whole reason a separate export was needed');
});

section('4. the file is named for the dataset it holds');

test('each export names itself, so two files cannot be confused', () => {
  const names = ['charges', 'payments', 'vendororders'].map((k) => csv(k).name);
  assert.deepStrictEqual(names, [
    'sairndental-charges-2026-09-14.csv',
    'sairndental-payments-2026-09-14.csv',
    'sairndental-vendor-orders-2026-09-14.csv'
  ], names.join(' | '));
});

console.log('\n' + (fail ? 'FAILED' : 'ok') + '  sairndental_ledger_export: '
  + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
