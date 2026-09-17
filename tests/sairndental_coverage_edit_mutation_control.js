// tests/sairndental_coverage_edit_mutation_control.js
// REQUIREMENT: tests/sairndental_coverage_edit.js can be MADE TO FAIL on each
//   property it holds -- a coverage rule that appends instead of updating is
//   the defect the suite exists for, and it is invisible from the screen
//   because lookupCoverage() is a .find() that silently keeps the FIRST row
//
// Run:  node tests/sairndental_coverage_edit_mutation_control.js
//
// WHAT THE GUARDED SUITE GUARDS, in its own words: a coverage rule could only
// ever be CREATED. Changing Delta/D2740 from 50% to 80% had no path at all, and
// IT LOOKED LIKE IT WORKED -- adding a second rule for the same payer and
// procedure saved fine and `lookupCoverage()` kept using the first. The
// practice believed it had changed a rule it had not, and every patient
// estimate computed from that rule was wrong in the direction nobody checks.
//
// `tools/suite_control_triage.py` ranked it Tier A and uncontrolled --
// dnt_coverage_rules.
//
// ── THE SUITE'S OWN WARNING IS WHAT THESE MUTATIONS ARE BUILT AGAINST ──────
// Its header cites sairn-code-scrubber item 16 Shape B: "asserting that an edit
// path EXISTS is satisfied by one that appends a duplicate, which is the bug."
// So the mutations do not remove the edit path -- they leave it there and make
// it append, stamp, or lose its id, which is exactly the shape that passed for
// working before.
//
// ── IT PATCHES NO TRACKED FILE ──────────────────────────────────────────────
// The suite gained a `DNT_HTML` override in the same change, the convention
// this app's ledger-export suite already carries. Section 6 asserts the real
// file is untouched and asks git as well.
//
// ── EVERY PLANT IS GUARDED THREE WAYS: uniqueness, difference, and the bytes
// ── read back off disk. A plant that cannot be placed exits 2, never passes.
//
// ── SECTION 5 IS THE CONTROL that makes the rest mean anything, and section 4
// ── of this file's sibling explains why `expect` is only judged on a FAILING
// ── run: a green suite prints every arm's label, so matching it proves nothing.
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const assert = require('assert');
const { spawnSync, execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const SUITE = path.join(ROOT, 'tests', 'sairndental_coverage_edit.js');
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
// ── THE BASELINE, TAKEN BEFORE ANYTHING RUNS (2026-09-16) ─────────────
// Section 6's git arm used to assert the working tree was clean for this app
// file FULL STOP, under a heading that says "the shipped file was never
// touched". Those are different claims and they agree only when nobody has
// uncommitted work -- which is exactly when a control is least likely to be
// run. It fired on my own unrelated edit to sairnvet.html minutes after I had
// fixed the identical defect in hover_separation_ci_probe.py's arm 7.
//
// The byte-identity arm above it already proves THIS control changed nothing.
// This captures the state before anything runs so the git arm can report the
// DIFFERENCE, which is what its label claims.
//
// AND THE LIMIT, MEASURED RATHER THAN ASSUMED, BECAUSE IT IS NOT OBVIOUS:
// `git status --porcelain <file>` prints the SAME line (" M file") whether the
// file was modified once or twice. So this comparison detects a
// control-introduced change only when the tree was CLEAN for that file
// beforehand; on an already-dirty tree it cannot see a further one. Verified by
// appending to an already-modified app file and watching the porcelain come
// back byte-identical.
//
// THE BYTE-IDENTITY ARM IS THEREFORE THE ONE THAT CARRIES THE GUARANTEE, in
// both cases, and this arm is corroboration. Said here for the same reason
// sairncode_gates_mutation_control.js says it about its own mtime arm: an arm
// that reads as proof and is only evidence is how a control comes to be
// trusted for something it does not do.
function gitPorcelain() {
  try {
    return execFileSync('git', ['-C', ROOT, 'status', '--porcelain', APP],
                        { encoding: 'utf8' });
  } catch (e) {
    return null;
  }
}
const PORCELAIN_BEFORE = gitPorcelain();
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'dnt-cov-'));

const MUTATIONS = [
  {
    // THE ORIGINAL DEFECT, restored in one character. A fresh id every save
    // means the server INSERTS instead of upserting, so the old rule stays and
    // lookupCoverage()'s .find() goes on returning it.
    name: 'an edit mints a NEW id, so the save appends instead of updating',
    find: "var rec={id:cvEditId||newId('CV'),payer:payer,procedure_type_id:procedureTypeId,coverage_percent:pct,",
    replace: "var rec={id:newId('CV'),/*MUTANT-NEW-ID*/payer:payer,procedure_type_id:procedureTypeId,coverage_percent:pct,",
    marker: 'MUTANT-NEW-ID',
    expect: /SAME id|REPLACED in place|appends/i,
    expectLabel: 'the arms about the id being kept and the list replaced in place',
    suites: ['sairndental_coverage_edit.js']
  },
  {
    // created_at is the date the rule was FIRST written. Stamping today onto an
    // edit rewrites history on a record a payer dispute is argued from.
    name: 'an edit stamps created_at with today, rewriting when the rule began',
    find: "created_at:(existing&&existing.created_at)||dntLocalToday()};",
    replace: "created_at:dntLocalToday()};/*MUTANT-RESTAMP*/",
    marker: 'MUTANT-RESTAMP',
    expect: /created_at/i,
    expectLabel: 'the arm requiring created_at to be preserved',
    suites: ['sairndental_coverage_edit.js']
  },
  {
    // Editing a rule another device deleted mid-edit must REFUSE. Without the
    // guard the save re-creates it under its old id, silently resurrecting a
    // rule somebody removed on purpose.
    name: 'a rule deleted mid-edit is silently re-created instead of refused',
    find: "if(cvEditId&&!existing){toast('That coverage rule is no longer on file -- refresh and try again',4000);cancelCoverageEdit();rCoverage();return;}",
    replace: "/*MUTANT-NO-VANISH-GUARD*/",
    marker: 'MUTANT-NO-VANISH-GUARD',
    expect: /no longer on file|vanished|refuses/i,
    expectLabel: 'the arms about a rule that is no longer on file',
    suites: ['sairndental_coverage_edit.js']
  },
  {
    // SERVER FIRST, LOCAL SECOND. Writing locally before knowing the server
    // accepted leaves this device applying a rule the server rejected, and
    // every estimate computed here differs from one computed anywhere else.
    name: 'a REFUSED save still writes locally -- the device diverges silently',
    find: "if(!syncResult){toast(dntLastErrText('dnt_coverage_rules')||'Could not save the coverage rule -- nothing was changed',7000);return;}",
    replace: "if(!syncResult){toast('Could not save');}/*MUTANT-REFUSAL-IGNORED*/",
    marker: 'MUTANT-REFUSAL-IGNORED',
    expect: /REFUSED save|changes nothing locally|edit mode/i,
    expectLabel: 'the arm requiring a refused save to change nothing locally',
    suites: ['sairndental_coverage_edit.js']
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

console.log('SAIRNdental coverage edit: the suite can be made to FAIL on what it claims\n');

let idx = 0;
for (const m of MUTATIONS) {
  idx += 1;
  section(idx + '. ' + m.name);
  const r = runSuite(plant(m));
  const failed = r.code !== 0;
  ok(failed, 'the suite FAILS   exit ' + r.code);
  // Only meaningful on a failing run: a green suite prints every arm's own
  // label, so `expect` would match its own success output and credit a miss.
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
  const porcelain = gitPorcelain();
  ok(porcelain === PORCELAIN_BEFORE,
     porcelain === null || PORCELAIN_BEFORE === null
       ? 'git could not be consulted -- reported, not folded into a pass'
       : 'and git sees no change this control did not make'
         + (PORCELAIN_BEFORE ? '   [the tree was already dirty for this file '
            + 'before the control started; the DIFFERENCE is what was measured]' : ''));
}

fs.rmSync(TMP, { recursive: true, force: true });

console.log('\n' + n + ' assertion(s), ' + fails.length + ' failed');
for (const f of fails) console.log('  FAILED: ' + f);
process.exit(fails.length ? 1 : 0);
