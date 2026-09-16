// tests/sairnvet_dose_audit_mutation_control.js
// REQUIREMENT: tests/sairnvet_audit_and_controlled.js can be MADE TO FAIL on
//   each defect it holds -- a lost controlled-substance audit row with a
//   success toast printed over it is the exact state the suite was written
//   after, and a suite nobody has watched go red is not evidence it would
//   notice that returning
//
// Run:  node tests/sairnvet_dose_audit_mutation_control.js
//
// WHAT THE GUARDED SUITE GUARDS, in its own words: logDoseAudit() has always
// returned true/false and ALL SEVENTEEN call sites ignored it. st() returns
// false on a full or unavailable store, so a lost audit row was completely
// invisible -- and two of those call sites are CLINICAL SIGN-OFFS whose toast
// asserts the row exists. "Confirmed -- recorded for this patient" could be
// printed over a write that never happened, on the dosing trail of a
// DEA-relevant controlled-substance register.
//
// `tools/suite_control_triage.py` ranked it among the Tier A suites with no
// negative control -- sv_audit_log, sv_boarding, sv_controlled. 58 arms green
// says nothing about whether any of them would notice the defect coming back.
//
// ── IT PATCHES NO TRACKED FILE ──────────────────────────────────────────────
// The suite gained an `SV_HTML` override in the same change, the same
// convention tests/sairnvet_seed_never_syncs.js took from SB_HTML rather than
// a second one being invented. Every mutation is planted in a COPY in a temp
// directory: no worktree, no restore, and none of the residue class that
// denied three legitimate pushes on 2026-09-08. Section 5 asserts the real
// file is untouched and asks git as well.
//
// ── EVERY PLANT IS GUARDED THREE WAYS, IN ORDER ─────────────────────────────
//   1. UNIQUENESS -- the anchor occurs exactly once.
//   2. DIFFERENCE  -- the mutated text is not the original.
//   3. MATERIALISATION -- the file is read BACK and the marker looked for in
//      the bytes on disk.
// A plant that cannot be placed exits 2 as COULD NOT PLANT, never as a pass.
//
// ── THE THREE MUTATIONS ARE THE THREE HALVES OF ONE DEFECT ─────────────────
// A silent failure needs all three to be honest: the write must REPORT
// failure, the failure must be SAID to the operator, and the caller must not
// print a success message over it. Each is disabled separately, because a
// suite that only checked one of them would pass while the other two were
// gone.
//
// ── SECTION 4 IS WHAT MAKES THE REST MEAN ANYTHING ──────────────────────────
// A suite that failed on everything would satisfy every arm above.
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const assert = require('assert');
const { spawnSync, execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const SUITE = path.join(ROOT, 'tests', 'sairnvet_audit_and_controlled.js');
const APP = path.join(ROOT, 'sairnvet.html');

let n = 0;
const fails = [];
function ok(cond, label) {
  console.log('  ' + (cond ? 'ok  ' : 'FAIL') + ' ' + label);
  n++;
  if (!cond) fails.push(label);
}
function section(s) { console.log('\n' + s); }

const ORIGINAL = fs.readFileSync(APP, 'utf8');
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'sv-dose-audit-'));

const MUTATIONS = [
  {
    // THE RETURN VALUE. A store that is full or unavailable makes st() return
    // false; swallowing that into `true` is the original defect, and every one
    // of the seventeen call sites inherits it at once.
    name: 'a FAILED audit write reports success -- the catch swallows it',
    find: '}catch(e){ ok = false; }',
    replace: '}catch(e){ ok = true; }/*MUTANT-CATCH-OK*/',
    marker: 'MUTANT-CATCH-OK',
    expect: /corrupt audit log|returns false/i,
    expectLabel: 'the arms about a refused or corrupt write',
    suites: ['sairnvet_audit_and_controlled.js']
  },
  {
    // THE OPERATOR IS NOT TOLD. The write still reports failure, and nothing
    // says so on screen -- which is the same end state for the person holding
    // the syringe.
    name: 'the failure is no longer SAID to the operator',
    find: "if(!ok && typeof showToast === 'function'){",
    replace: "if(false && !ok && typeof showToast === 'function'){/*MUTANT-SILENT-FAIL*/",
    marker: 'MUTANT-SILENT-FAIL',
    expect: /SAYS SO|naming the audit log|as an error/i,
    expectLabel: 'the arms requiring the refusal to be said, and named',
    suites: ['sairnvet_audit_and_controlled.js']
  },
  {
    // THE CALLER PRINTS OVER IT. The sign-off toast is a claim ABOUT the audit
    // row -- the only thing the handler writes -- so returning early on a
    // failed write is the whole fix. Removing the guard restores the exact
    // 2026-09-04 defect: "Confirmed - recorded for this patient" over nothing.
    name: 'the clinical sign-off confirms even when the audit row was NOT written',
    find: '    if(!audited) return;   // logDoseAudit has already said what happened',
    replace: '    /*MUTANT-SIGNOFF-ALWAYS*/',
    marker: 'MUTANT-SIGNOFF-ALWAYS',
    expect: /failed sign-off|recorded for this patient|opposite/i,
    expectLabel: 'the sign-off arms, which are the ones a person acts on',
    suites: ['sairnvet_audit_and_controlled.js']
  }
];

function plant(m) {
  const hits = ORIGINAL.split(m.find).length - 1;
  if (hits !== 1) {
    console.log('\nCOULD NOT PLANT: ' + m.name);
    console.log('  the anchor occurs ' + hits + ' time(s) in sairnvet.html, not 1.');
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
    env: Object.assign({}, process.env, { SV_HTML: htmlPath }),
    encoding: 'utf8'
  });
  return { code: r.status, out: (r.stdout || '') + (r.stderr || '') };
}

console.log('SAIRNvet dose audit: the suite can be made to FAIL on each half of the defect\n');

let idx = 0;
for (const m of MUTATIONS) {
  idx += 1;
  section(idx + '. ' + m.name);
  const r = runSuite(plant(m));
  ok(r.code !== 0, 'the suite FAILS   exit ' + r.code);
  ok(m.expect.test(r.out), 'and it fails on ' + m.expectLabel);
}

section('4. CONTROL -- an UNMUTATED copy through the same path must PASS');
{
  const clean = path.join(TMP, 'clean.html');
  fs.writeFileSync(clean, ORIGINAL);
  assert.strictEqual(fs.readFileSync(clean, 'utf8'), ORIGINAL,
                     'the clean copy is not byte-identical to the shipped file');
  const r = runSuite(clean);
  ok(r.code === 0, 'the same suite PASSES on an unmutated copy   exit ' + r.code);
  ok(/passed/i.test(r.out), 'and it actually ran its arms');
}

section('5. the shipped file was never touched');
{
  ok(fs.readFileSync(APP, 'utf8') === ORIGINAL,
     'sairnvet.html is byte-identical to how this control found it');
  let porcelain = '';
  try {
    porcelain = execFileSync('git', ['-C', ROOT, 'status', '--porcelain', 'sairnvet.html'],
                             { encoding: 'utf8' });
  } catch (e) {
    porcelain = null;
  }
  ok(porcelain === '' || porcelain === null,
     porcelain === null
       ? 'git could not be consulted -- reported, not folded into a pass'
       : 'and git agrees the working tree is clean for it');
}

fs.rmSync(TMP, { recursive: true, force: true });

console.log('\n' + n + ' assertion(s), ' + fails.length + ' failed');
for (const f of fails) console.log('  FAILED: ' + f);
process.exit(fails.length ? 1 : 0);
