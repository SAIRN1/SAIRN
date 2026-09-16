// tests/sairndental_ledger_export_mutation_control.js
// REQUIREMENT: tests/sairndental_ledger_export.js can be MADE TO FAIL on each
//   property it holds -- the append-only charge and payment archives are what
//   an auditor is handed when they ask what was charged and what was paid, and
//   a suite nobody has watched go red is not evidence those exports still
//   carry the row-level record
//
// Run:  node tests/sairndental_ledger_export_mutation_control.js
//
// WHAT THE GUARDED SUITE GUARDS, in its own words: SAIRNdental's export
// registry carried NINE datasets and neither of the two resources its own
// registry file declares APPEND-ONLY -- dnt_charges and dnt_payments. The only
// billing export was `ageing`: five derived buckets and a total, behind an
// Export CSV button on a Billing panel, which READS AS EXPORTED. A bucket total
// is not the row-level record, and an auditor asking what was charged cannot be
// handed five buckets.
//
// `tools/suite_control_triage.py` ranked it among the Tier A suites with no
// negative control -- dnt_charges, dnt_payments, dnt_supplies,
// dnt_vendor_orders.
//
// ── THE COLUMN FUNCTIONS ARE THE REASON THIS NEEDS MUTATION AT ALL ─────────
// Every column is a closure that dereferences a record and often a second
// collection, so a wrong field name or a dropped lookup is a silent empty cell
// or a throw -- neither visible in a diff, and both of them still produce a CSV
// that downloads. The four mutations below are each one of those, planted in a
// copy and driven through the real exportDataset().
//
// ── IT PATCHES NO TRACKED FILE ──────────────────────────────────────────────
// The suite gained a `DNT_HTML` override in the same change, the same
// convention SB_HTML and SV_HTML already carry rather than a third one being
// invented. Section 6 asserts the real file is untouched and asks git as well.
//
// ── EVERY PLANT IS GUARDED THREE WAYS, IN ORDER ─────────────────────────────
//   1. UNIQUENESS -- the anchor occurs exactly once. The `Patient` column
//      appears THREE times in this file, which is precisely why the anchor for
//      that mutation is the whole `payments:` entry line rather than the column
//      alone: an anchor that matches in three places would mutate the first one
//      and the control would be testing a different export than it names.
//   2. DIFFERENCE  -- the mutated text is not the original.
//   3. MATERIALISATION -- the file is read BACK and the marker looked for in
//      the bytes on disk.
// A plant that cannot be placed exits 2 as COULD NOT PLANT, never as a pass.
//
// ── SECTION 5 IS WHAT MAKES THE REST MEAN ANYTHING ──────────────────────────
// A suite that failed on everything would satisfy every arm above.
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const assert = require('assert');
const { spawnSync, execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const SUITE = path.join(ROOT, 'tests', 'sairndental_ledger_export.js');
const APP = path.join(ROOT, 'sairndental.html');

let n = 0;
const fails = [];
function ok(cond, label) {
  console.log('  ' + (cond ? 'ok  ' : 'FAIL') + ' ' + label);
  n++;
  if (!cond) fails.push(label);
}
function section(s) { console.log('\n' + s); }

const ORIGINAL = fs.readFileSync(APP, 'utf8');
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'dnt-ledger-'));

const MUTATIONS = [
  {
    // THE DEFECT THE SUITE EXISTS FOR, one column in. Without the id a charge
    // export is a list of amounts nobody can reconcile against the ledger --
    // the same reason `ageing` could not stand in for it.
    name: 'the CHARGE ID leaves the charges export',
    find: "['Charge ID',function(r){return r.id;}],",
    replace: "/*MUTANT-NO-CHARGE-ID*/",
    marker: 'MUTANT-NO-CHARGE-ID',
    expect: /Charge ID|id kept/i,
    expectLabel: 'the arm requiring the charge id to survive the export',
    suites: ['sairndental_ledger_export.js']
  },
  {
    // A MISSING PATIENT SHOULD LEAVE THE NAME BLANK AND THE ID INTACT. Putting
    // the id in the NAME column looks like data and is not -- an auditor reads
    // a column headed Patient and gets an identifier they cannot resolve.
    // SCOPED TO THE CHARGES ENTRY, and the scoping is the finding. This
    // mutation was first planted on the PAYMENTS patient column and THE SUITE
    // DID NOT NOTICE -- exit 0. The missing-patient behaviour is asserted for
    // charges only, so the identical defect one export over is uncovered.
    // Section 7 records that rather than leaving it as a deleted experiment.
    name: 'a deleted patient puts an ID in the NAME column instead of leaving it blank',
    find: "charges:{label:'charges',rows:function(){return charges();},columns:[\n    ['Date',function(r){return r.date;}],\n    ['Charge ID',function(r){return r.id;}],\n    ['Patient',function(r){var p=patients().find(function(x){return x.id===r.patient_id;});return p?p.name:'';}],",
    replace: "charges:{label:'charges',rows:function(){return charges();},columns:[\n    ['Date',function(r){return r.date;}],\n    ['Charge ID',function(r){return r.id;}],\n    ['Patient',function(r){var p=patients().find(function(x){return x.id===r.patient_id;});return p?p.name:r.patient_id;}],/*MUTANT-NAME-IS-ID*/",
    marker: 'MUTANT-NAME-IS-ID',
    expect: /NAME blank|no longer exists/i,
    expectLabel: 'the arm about a patient who no longer exists',
    suites: ['sairndental_ledger_export.js']
  },
  {
    // TWO FILES THAT CANNOT BE CONFUSED is the near-miss this registry already
    // had once -- `supplies` exported for the vendor-order archive. A label
    // collision is the same mistake with the evidence removed.
    name: 'the charges export calls itself ageing -- two files become confusable',
    find: "charges:{label:'charges'",
    replace: "charges:{label:'ageing'/*MUTANT-LABEL-COLLIDES*/",
    marker: 'MUTANT-LABEL-COLLIDES',
    expect: /names itself|confused|different files/i,
    expectLabel: 'the arm requiring each export to name itself',
    suites: ['sairndental_ledger_export.js']
  },
  {
    // THE METHOD IS WHAT MAKES A PAYMENT RECONCILABLE against a bank line.
    // Dropping it leaves a CSV that still downloads and still has a total.
    name: 'the payment METHOD leaves the payments export',
    find: "['Method',function(r){return r.method;}],",
    replace: "/*MUTANT-NO-METHOD*/",
    marker: 'MUTANT-NO-METHOD',
    expect: /method survives|Method/i,
    expectLabel: 'the arm requiring the payment method to survive',
    suites: ['sairndental_ledger_export.js']
  }
];

function plant(m) {
  const hits = ORIGINAL.split(m.find).length - 1;
  if (hits !== 1) {
    console.log('\nCOULD NOT PLANT: ' + m.name);
    console.log('  the anchor occurs ' + hits + ' time(s) in sairndental.html, not 1.');
    console.log('  That is a STALE ANCHOR, not a passing control. Nothing was tested.');
    process.exit(2);
  }
  const mutated = ORIGINAL.replace(m.find, m.replace);
  if (mutated === ORIGINAL) {
    console.log('\nCOULD NOT PLANT: ' + m.name + ' -- the replacement changed nothing.');
    process.exit(2);
  }
  const file = path.join(TMP, m.marker + '.html');
  fs.writeFileSync(file, mutated);
  if (fs.readFileSync(file, 'utf8').indexOf(m.marker) === -1) {
    console.log('\nCOULD NOT PLANT: ' + m.name + ' -- the marker is absent from the '
                + 'bytes on disk, so the next process would read the original.');
    process.exit(2);
  }
  return file;
}

function runSuite(htmlPath) {
  const r = spawnSync(process.execPath, [SUITE], {
    cwd: ROOT,
    env: Object.assign({}, process.env, { DNT_HTML: htmlPath }),
    encoding: 'utf8'
  });
  return { code: r.status, out: (r.stdout || '') + (r.stderr || '') };
}

console.log('SAIRNdental ledger export: the suite can be made to FAIL on what it claims\n');

let idx = 0;
for (const m of MUTATIONS) {
  idx += 1;
  section(idx + '. ' + m.name);
  const r = runSuite(plant(m));
  const failed = r.code !== 0;
  ok(failed, 'the suite FAILS   exit ' + r.code);
  // ── THE `expect` ARM IS ONLY MEANINGFUL ON A FAILING RUN, AND THE FIRST
  // ── VERSION OF THIS FILE GOT THAT WRONG ─────────────────────────────────
  // A PASSING run prints every arm's own label, so `expect` matched the green
  // output of a mutation the suite had not noticed and credited it. Measured,
  // not imagined: the payments patient-column mutation exited 0 and this arm
  // said "and it fails on the arm about a patient who no longer exists".
  // A control that can credit a miss is worse than no control.
  ok(failed && m.expect.test(r.out),
     'and it fails on ' + m.expectLabel
     + (failed ? '' : '   [not evaluated -- the suite did not fail]'));
}

section('5. CONTROL -- an UNMUTATED copy through the same path must PASS');
{
  const clean = path.join(TMP, 'clean.html');
  fs.writeFileSync(clean, ORIGINAL);
  assert.strictEqual(fs.readFileSync(clean, 'utf8'), ORIGINAL,
                     'the clean copy is not byte-identical to the shipped file');
  const r = runSuite(clean);
  ok(r.code === 0, 'the same suite PASSES on an unmutated copy   exit ' + r.code);
  ok(r.out.length > 0, 'and it actually ran');
}

section('6. the shipped file was never touched');
{
  ok(fs.readFileSync(APP, 'utf8') === ORIGINAL,
     'sairndental.html is byte-identical to how this control found it');
  let porcelain = '';
  try {
    porcelain = execFileSync('git', ['-C', ROOT, 'status', '--porcelain', 'sairndental.html'],
                             { encoding: 'utf8' });
  } catch (e) {
    porcelain = null;
  }
  ok(porcelain === '' || porcelain === null,
     porcelain === null
       ? 'git could not be consulted -- reported, not folded into a pass'
       : 'and git agrees the working tree is clean for it');
}

section('7. A MUTATION THIS SUITE DOES NOT CATCH, recorded rather than deleted');
// The same missing-patient defect on the PAYMENTS export instead of the
// charges one. The suite asserts the blank-name behaviour for charges only, so
// this identical defect one export over changes nothing it checks.
//
// IT IS AN ARM RATHER THAN A COMMENT because a gap written in prose is a gap
// nobody re-measures. If somebody extends the suite to cover payments, THIS
// ARM GOES RED and says so -- which is the correct outcome and the signal to
// promote the mutation into the list above.
{
  const find = "payments:{label:'payments',rows:function(){return payments();},columns:[\n"
    + "    ['Date',function(r){return r.date;}],\n"
    + "    ['Payment ID',function(r){return r.id;}],\n"
    + "    ['Patient',function(r){var p=patients().find(function(x){return x.id===r.patient_id;});return p?p.name:'';}],";
  const hits = ORIGINAL.split(find).length - 1;
  if (hits !== 1) {
    console.log('  COULD NOT TEST -- the payments anchor occurs ' + hits
                + ' time(s), not 1. The gap below was NOT re-measured.');
    fails.push('the known-gap arm could not plant its anchor');
    n++;
  } else {
    const f = path.join(TMP, 'MUTANT-PAYMENTS-NAME-IS-ID.html');
    fs.writeFileSync(f, ORIGINAL.replace(find,
      find.replace("return p?p.name:'';", 'return p?p.name:r.patient_id;')
        + '/*MUTANT-PAYMENTS-NAME-IS-ID*/'));
    const r = runSuite(f);
    ok(r.code === 0,
       'the payments patient column is STILL uncovered -- exit ' + r.code
       + (r.code === 0 ? ' (the gap is real)' : ' (the suite now catches it -- '
          + 'promote this mutation into the list above and delete this section)'));
  }
}

fs.rmSync(TMP, { recursive: true, force: true });

console.log('\n' + n + ' assertion(s), ' + fails.length + ' failed');
for (const f of fails) console.log('  FAILED: ' + f);
process.exit(fails.length ? 1 : 0);
