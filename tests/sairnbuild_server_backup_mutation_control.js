// tests/sairnbuild_server_backup_mutation_control.js
// REQUIREMENT: tests/sairnbuild_server_backup.js can be MADE TO FAIL on each
//   way the backup hook can do the wrong AMOUNT of work -- pushing nothing,
//   pushing everything, pushing during a seed, or pushing a record the browser
//   itself failed to store -- because none of those throw and every one of them
//   is a green app doing the wrong thing
//
// Run:  node tests/sairnbuild_server_backup_mutation_control.js
//
// WHAT THE GUARDED SUITE GUARDS, in its own words: the feature is ONE hook
// inside st(), the single function every write in the file already goes
// through, "so the risk is not that it fails loudly. It is that it does the
// wrong AMOUNT of work, silently" -- an empty backup everyone believes exists,
// three hundred network writes per repaint, a customer's server filled with
// demo rows, or the server and the device disagreeing about what was saved.
// That is why its assertions COUNT CALLS rather than check for errors.
//
// Tier A and uncontrolled: bld_bids, bld_costs, bld_jobs, bld_tna.
//
// ── THE MUTATIONS ARE THE FOUR FAILURES ITS HEADER NAMES ──────────────────
// Not four defects I invented: the suite's own header lists the ways this hook
// can be wrong, and each mutation below is one of them made real. A control
// built from a different list would be testing a different suite.
//
// ── ONE OF THEM IS ORDER, NOT LOGIC, AND IT IS THE SUBTLE ONE ─────────────
// st() reads the PREVIOUS value before writing and pushes only after the local
// write SUCCEEDS. The file says that order is load-bearing -- "a failed local
// write must not push a value the device does not itself hold" -- so mutation
// 4 changes no condition at all, only when the push is allowed to happen.
//
// ── IT PATCHES NO TRACKED FILE ──────────────────────────────────────────────
// The suite gained a `BLD_HTML` override, the convention SB_HTML, SV_HTML,
// DNT_HTML and LAW_HTML already carry. Section 6 asserts the real file is
// untouched and asks git as well. Every plant is guarded three ways --
// uniqueness, difference, and the bytes read back off disk -- and a plant that
// cannot be placed exits 2 rather than passing. `expect` is judged only on a
// FAILING run, because a green suite prints every arm's own label.
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const assert = require('assert');
const { spawnSync, execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const SUITE = path.join(ROOT, 'tests', 'sairnbuild_server_backup.js');
const APP = path.join(ROOT, 'sairnbuild.html');

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
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'bld-backup-'));

const MUTATIONS = [
  {
    // PUSHES NOTHING. The hook is still called and still returns; the backup
    // everyone believes exists is empty, and no screen says so.
    name: 'the hook returns before doing anything -- the backup is silently empty',
    find: 'function bldSyncCollection(key, next, prev) {\n  if (!_bldSyncOn[key] || bldSeeding) return;',
    replace: 'function bldSyncCollection(key, next, prev) {\n  return;/*MUTANT-PUSHES-NOTHING*/\n  if (!_bldSyncOn[key] || bldSeeding) return;',
    marker: 'MUTANT-PUSHES-NOTHING',
    expect: /is pushed|pushed, not the whole array|appended record/i,
    expectLabel: 'the arms that count a push happening at all',
    suites: ['sairnbuild_server_backup.js']
  },
  {
    // PUSHES EVERYTHING. Losing the previous value means every record looks
    // changed, so a page repaint becomes three hundred network writes.
    name: 'the previous value is never read -- every repaint pushes the whole array',
    find: "if(typeof _bldSyncOn!=='undefined'&&_bldSyncOn[k]){prev=ld(k,null);}",
    replace: "/*MUTANT-NO-PREV*/",
    marker: 'MUTANT-NO-PREV',
    expect: /UNCHANGED array pushes nothing|only the CHANGED record/i,
    expectLabel: 'the arms about an unchanged array and a single changed record',
    suites: ['sairnbuild_server_backup.js']
  },
  {
    // PUSHES DURING seed(). A customer's server tables fill with demo rows,
    // and hydration is additive, so they spread to every other device.
    name: 'the seed guard goes -- demo rows reach a customer\'s server',
    find: 'if (!_bldSyncOn[key] || bldSeeding) return;',
    replace: 'if (!_bldSyncOn[key]) return;/*MUTANT-SEEDS-PUSH*/',
    marker: 'MUTANT-SEEDS-PUSH',
    expect: /seed|not synced|app state/i,
    expectLabel: 'the arms about seeding and about what is not synced',
    suites: ['sairnbuild_server_backup.js']
  },
  {
    // ORDER, NOT LOGIC. Pushing regardless of whether the local write succeeded
    // makes the server hold a record the device does not. The condition is not
    // removed -- only its dependence on okWrite -- so nothing else changes.
    name: 'a FAILED local write still pushes -- the server and the device disagree',
    find: "if(okWrite&&typeof bldSyncCollection==='function'){",
    replace: "if(typeof bldSyncCollection==='function'){/*MUTANT-PUSH-ON-FAILED-WRITE*/",
    marker: 'MUTANT-PUSH-ON-FAILED-WRITE',
    expect: /local write still happens|never replaces it|failed/i,
    expectLabel: 'the arms about the local write and what happens when it fails',
    suites: ['sairnbuild_server_backup.js']
  }
];

function plant(m) {
  const hits = ORIGINAL.split(m.find).length - 1;
  if (hits !== 1) {
    console.log('\nCOULD NOT PLANT: ' + m.name);
    console.log('  the anchor occurs ' + hits + ' time(s) in sairnbuild.html, not 1.');
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
    env: Object.assign({}, process.env, { BLD_HTML: htmlPath }),
    encoding: 'utf8'
  });
  return { code: r.status, out: (r.stdout || '') + (r.stderr || '') };
}

console.log('SAIRNbuild server backup: the suite can be made to FAIL on each wrong AMOUNT of work\n');

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
     'sairnbuild.html is byte-identical to how this control found it');
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
