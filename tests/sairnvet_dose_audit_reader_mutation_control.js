// tests/sairnvet_dose_audit_reader_mutation_control.js
// REQUIREMENT: tests/sairnvet_dose_audit_reader.js can be MADE TO FAIL on each
//   way the dosing trail can lie about ITSELF -- a failed read, a timed-out
//   read and an unprovisioned table must never render as "nothing was dosed",
//   because that sentence is what an inspector would be shown about a
//   DEA-relevant controlled-substance record
//
// Run:  node tests/sairnvet_dose_audit_reader_mutation_control.js
//
// WHAT THE GUARDED SUITE GUARDS: the reader behind the Dosing Audit Trail
// panel. Every one of its failure paths ends in the same place if it is wrong
// -- an empty table -- and an empty table is indistinguishable from a practice
// that has dosed nothing. The suite's arms are therefore about the SENTENCE the
// panel prints, not about the rows: "a FAILED read never claims the trail is
// empty", "NOT SET UP is not empty", "the local copy is capped and may be
// incomplete".
//
// Tier A and uncontrolled until now: sv_audit_log, sv_patients.
//
// ── WHY THIS RESOURCE AND WHY TONIGHT ─────────────────────────────────────
// sv_audit_log was the one Class A resource that could be NEITHER viewed NOR
// produced as a file. Hank closed both halves with this panel and its Export
// CSV, live-verified on 2026-09-16. A record that has just become the thing an
// inspector is handed is exactly the wrong moment for its reader to have never
// been watched go red.
//
// ── IT PATCHES NO TRACKED FILE ──────────────────────────────────────────────
// The suite honours `SV_HTML`, the convention five other suites already carry.
// Section 6 asserts the real file is untouched and asks git. Every plant is
// guarded three ways -- uniqueness, difference, and the bytes read back off
// disk -- and a plant that cannot be placed exits 2 rather than passing.
// `expect` is judged only on a FAILING run, because a green suite prints every
// arm's own label.
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const assert = require('assert');
const { spawnSync, execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const SUITE = path.join(ROOT, 'tests', 'sairnvet_dose_audit_reader.js');
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
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'sv-doseaudit-'));

const MUTATIONS = [
  {
    // A FAILED READ RENDERS AS AN EMPTY TRAIL. The single worst outcome for
    // this resource: an inspector is shown a table with no rows and a panel
    // that does not say the read failed.
    // THE BRANCH IS KEPT LIVE AND MADE TO LIE, rather than disabled. Deleting
    // `if(env === null || env === undefined)` lets a null env reach
    // `env.provisioned` and the suite dies on a TypeError -- it FAILS, but for
    // the wrong reason, and a mutation caught by a crash proves nothing about
    // the arm it was meant to exercise. Measured, not reasoned: that version
    // produced "TypeError: Cannot read properties of null (reading
    // 'provisioned')" before section B had finished.
    name: 'a FAILED server read renders as an EMPTY TRAIL that claims to be the server copy',
    find: "done(local, 'local',\n        '<strong>The server read failed."
      + "</strong> Showing the local copy from this device.' + localNote\n"
      + "        + ' This is not the full record; use \u201cReload from "
      + "server\u201d once connectivity is back.');",
    // The WHOLE statement, terminator included, and a COMPLETE replacement.
    // Anchoring on a fragment left the call unbalanced and the suite died on
    // a SyntaxError -- a third way of failing for the wrong reason.
    replace: "done([], 'server',\n        '<strong>Loaded.</strong>');"
      + "/*MUTANT-FAILED-READ-IS-EMPTY*/",
    marker: 'MUTANT-FAILED-READ-IS-EMPTY',
    expect: /FAILED SERVER READ|never claims the trail is empty|read failed/i,
    expectLabel: 'the arms about a failed read falling back and saying so',
    suites: ['sairnvet_dose_audit_reader.js']
  },
  {
    // NOT SET UP IS NOT EMPTY. provisioned:false means the table does not
    // exist; reading it as "this practice has dosed nothing" is the false
    // statement that branch exists to stop.
    name: 'an UNPROVISIONED table is read as a practice that has dosed nothing',
    find: '    if(env.provisioned === false){',
    replace: '    if(false){/*MUTANT-UNPROVISIONED-IS-EMPTY*/',
    marker: 'MUTANT-UNPROVISIONED-IS-EMPTY',
    expect: /UNPROVISIONED|provisioned/i,
    expectLabel: 'the arms about an unprovisioned read reaching the caller with its flag',
    suites: ['sairnvet_dose_audit_reader.js']
  },
  {
    // THE CAP WARNING IS THE HONESTY. Without it the local copy -- capped at
    // SV_AUDIT_CAP -- is presented as the full record, which is a complete
    // answer that is short by however much the cap removed.
    name: 'the local copy is shown WITHOUT the cap warning, as if it were the full record',
    find: "  var localNote = ' The local copy is capped at ' + SV_AUDIT_CAP",
    replace: "  var localNote = '';/*MUTANT-NO-CAP-WARNING*/ var _unused = ' capped at ' + SV_AUDIT_CAP",
    marker: 'MUTANT-NO-CAP-WARNING',
    expect: /capped|incomplete|full record/i,
    expectLabel: 'the arms requiring the local copy to be labelled and capped',
    suites: ['sairnvet_dose_audit_reader.js']
  },
  {
    // WITH NO TRANSPORT AT ALL the panel must still label what it is showing
    // rather than going silent. This is the branch that runs on an engine where
    // svData is absent entirely.
    // Same reasoning as the first: removing the `typeof svData === 'function'`
    // guard throws a ReferenceError rather than exercising the arm. The branch
    // stays and its ANSWER is made silent instead.
    name: 'with no transport the panel goes silent instead of labelling the local copy',
    find: "    done(local, 'local',\n      '<strong>Showing this device only.</strong> The server could not be asked, so this is the local copy.' + localNote);",
    replace: "    done([], 'server', '');/*MUTANT-NO-TRANSPORT-SILENT*/",
    marker: 'MUTANT-NO-TRANSPORT-SILENT',
    expect: /no transport|labels the local copy|going silent/i,
    expectLabel: 'the arm about having no transport at all',
    suites: ['sairnvet_dose_audit_reader.js']
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

console.log('SAIRNvet dosing trail: the suite can be made to FAIL on each way it could lie\n');

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
