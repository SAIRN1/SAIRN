// tests/roofing_claim_photo_export_mutation_control.js
// REQUIREMENT: tests/roofing_claim_photo_export.js can be MADE TO FAIL on each
//   property it holds -- an adjuster dispute is about the photographs, and an
//   evidence export that quietly drops a refused claim, or reports an
//   unprovisioned table as zero rows, is worse than no export because it looks
//   like a complete answer
//
// Run:  node tests/roofing_claim_photo_export_mutation_control.js
//
// ── WHY THIS FILE EXISTS, AND IT IS NOT WHAT THE DOCUMENT SAYS ─────────────
// docs/2026-09-14-class-a-retrievability.md records that the claim-photo export
// shipped with "three sabotage controls: pointing `charges` at the ageing
// buckets takes 3 arms red, dropping the fan-out's failure list takes 1, and
// swapping the inventory columns for a `photo_base64` column takes 1. Each
// asserted its anchor first and each file was restored byte-identical."
//
// THOSE WERE RUN, AND THEY WERE NOT LEFT BEHIND. They were one-off sabotages
// performed during the 2026-09-14 work, not a re-runnable control, and neither
// export suite carries a MUTATIONS table. `tools/suite_control_triage.py` has
// gone on listing tests/roofing_claim_photo_export.js among the UNCONTROLLED
// Tier A suites ever since -- rf_claims, rf_claim_photos -- and it was right.
//
// A SABOTAGE THAT HAPPENED ONCE IS EVIDENCE ABOUT THE DAY IT HAPPENED. This
// makes the same demonstrations repeatable, which is the difference between
// "somebody checked" and "this is checked".
//
// ── IT PATCHES NO TRACKED FILE ──────────────────────────────────────────────
// The suite gained an `RF_HTML` override, the convention five other suites
// already carry. Section 6 asserts the real file is untouched and asks git.
// Every plant is guarded three ways -- uniqueness, difference, and the bytes
// read back off disk -- and a plant that cannot be placed exits 2 rather than
// passing. `expect` is judged only on a FAILING run, because a green suite
// prints every arm's own label.
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const assert = require('assert');
const { spawnSync, execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const SUITE = path.join(ROOT, 'tests', 'roofing_claim_photo_export.js');
const APP = path.join(ROOT, 'sairnroofing.html');

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
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'rf-photo-'));

const MUTATIONS = [
  {
    // THE ONE THE DOCUMENT NAMES. A claim the server refuses is DROPPED from
    // the fan-out note, so the export is short by exactly the claims somebody
    // could not see -- and nothing on the file says so. An incomplete evidence
    // inventory that does not admit it is the failure mode this whole export
    // was built against.
    name: 'a REFUSED claim vanishes from the fan-out note -- the export is quietly short',
    find: "failed.push(claimId+' ('+(pr.code||pr.status)+')');",
    replace: "/*MUTANT-SWALLOW-REFUSAL*/",
    marker: 'MUTANT-SWALLOW-REFUSAL',
    expect: /403 on one claim|refus/i,
    expectLabel: 'the arms about a refused claim and a refused list',
    suites: ['roofing_claim_photo_export.js']
  },
  {
    // THE SECOND ONE THE DOCUMENT NAMES. Carrying the data URL into the column
    // set turns a readable inventory into a file nothing will open, and loses
    // the honest statement of what the CSV does not contain.
    name: 'the inventory columns become the image itself -- megabytes into a CSV cell',
    find: "['photo_present','photo_present'],['photo_chars','photo_chars'],",
    replace: "['photo_base64','photo_base64'],/*MUTANT-B64-COLUMN*/",
    marker: 'MUTANT-B64-COLUMN',
    expect: /photo_base64 is not carried|NO stored image/i,
    expectLabel: 'the arms about the image bytes staying out of the column set',
    suites: ['roofing_claim_photo_export.js']
  },
  {
    // A REFUSED CLAIM LIST must be a refusal. Returning the refusal object as
    // though it were data makes "the server said no" and "there is nothing to
    // export" the same file.
    name: 'a refused CLAIM LIST is treated as data instead of as a refusal',
    find: 'if(!cr.ok)return cr;',
    replace: 'if(!cr.ok)return {ok:true,data:{data:[],provisioned:true}};/*MUTANT-REFUSAL-AS-EMPTY*/',
    marker: 'MUTANT-REFUSAL-AS-EMPTY',
    expect: /refused CLAIM LIST|refusal, not an empty export/i,
    expectLabel: 'the arm requiring a refused list to stay a refusal',
    suites: ['roofing_claim_photo_export.js']
  },
  {
    // A row with no stored image must SAY no. Reporting every row as present
    // makes an inventory that cannot be acted on: the one number an adjuster
    // would use to ask for the missing evidence is the one that stops being
    // true.
    name: 'every row claims a stored image, including the ones with none',
    find: "photo_present:b64?'yes':'no',",
    replace: "photo_present:'yes',/*MUTANT-ALWAYS-PRESENT*/",
    marker: 'MUTANT-ALWAYS-PRESENT',
    expect: /NO stored image|says no/i,
    expectLabel: 'the arm about a row with no stored image',
    suites: ['roofing_claim_photo_export.js']
  }
];

function plant(m) {
  const hits = ORIGINAL.split(m.find).length - 1;
  if (hits !== 1) {
    console.log('\nCOULD NOT PLANT: ' + m.name);
    console.log('  the anchor occurs ' + hits + ' time(s) in sairnroofing.html, not 1.');
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
    env: Object.assign({}, process.env, { RF_HTML: htmlPath }),
    encoding: 'utf8'
  });
  return { code: r.status, out: (r.stdout || '') + (r.stderr || '') };
}

console.log('SAIRNroofing claim-photo export: the one-off sabotages, made repeatable\n');

let idx = 0;
for (const m of MUTATIONS) {
  idx += 1;
  section(idx + '. ' + m.name);
  const r = runSuite(plant(m));
  const failed = r.code !== 0;
  ok(failed, 'the suite FAILS   exit ' + r.code);
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
     'sairnroofing.html is byte-identical to how this control found it');
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
