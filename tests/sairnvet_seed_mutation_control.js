// tests/sairnvet_seed_mutation_control.js
// REQUIREMENT: tests/sairnvet_seed_never_syncs.js can be MADE TO FAIL on each
//   defect it claims to hold -- it guards the moment a demo seed reached a real
//   clinic's DEA-relevant controlled-substance register, and a suite nobody has
//   watched go red is not evidence that it cannot happen again
//
// Run:  node tests/sairnvet_seed_mutation_control.js
//
// THE SUITE THIS CONTROLS GUARDS THE WORST THING THAT HAS ACTUALLY HAPPENED ON
// THIS PLATFORM. From its own header: 39 of SAIRNvet's 41 synced collections
// seeded demo rows LAZILY on first read, through st(), which carries the
// server-backup hook -- so merely OPENING a panel on a fresh or cleared device
// pushed fabricated records into real tables. The controlled-substance panel
// invented Ketamine, Butorphanol and Fentanyl balances with named vets, into a
// register a regulator reads, and hydration is additive-only with NO delete
// path anywhere in the product. Anything that landed spread to every other
// device and could not be removed from the app.
//
// `tools/suite_control_triage.py` ranked it among the Tier A suites with no
// negative control -- sv_controlled, sv_peerconsults, schedule -- and 18/18
// green on the shipped tree says nothing at all about whether it would notice
// the defect coming back.
//
// ── IT PATCHES NO TRACKED FILE ──────────────────────────────────────────────
// The suite gained an `SV_HTML` override in the same change, copying the
// SB_HTML affordance that tests/sairnbiz_po_recv_reach_the_server.js already
// had rather than inventing a second convention. Every mutation below is
// planted in a COPY in a temp directory. No worktree, no `git checkout --`
// restore, and none of the residue that denied three legitimate pushes on
// 2026-09-08. Section 5 asserts the real file is untouched and asks git too.
//
// ── EVERY PLANT IS GUARDED THREE WAYS, IN ORDER ─────────────────────────────
//   1. UNIQUENESS -- the anchor occurs exactly once. The strongest of the
//      shapes `tools/sabotage.py` names: presence catches a rename and is blind
//      to an anchor matching in four places; a count catches both.
//   2. DIFFERENCE  -- the mutated text is not the original, because
//      String.replace silently does nothing on a miss.
//   3. MATERIALISATION -- the file is read BACK and the marker looked for in
//      the bytes, since a claim about a string in memory is not a claim about
//      what the next process reads.
// A plant that cannot be placed exits 2 as COULD NOT PLANT. It is never a pass.
//
// ── SECTION 4 IS WHAT MAKES THE REST MEAN ANYTHING ──────────────────────────
// A suite that failed on everything would satisfy every arm above. Section 4
// runs the same suite on an UNMUTATED copy through the same SV_HTML path and
// demands exit 0.
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const assert = require('assert');
const { spawnSync, execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const SUITE = path.join(ROOT, 'tests', 'sairnvet_seed_never_syncs.js');
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
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'sv-seed-'));

// `expect` names which arm of the suite should notice this particular defect.
// Asserting only on the exit code would let a mutation that breaks the file in
// some unrelated way count as the suite catching the defect.
const MUTATIONS = [
  {
    // THE 2026-09-10 DEFECT ITSELF. svSeedStore's `finally` is the only thing
    // that stops a throw inside a saver leaving the backup suppressed for the
    // rest of the session -- and the surrounding catch swallows the evidence.
    name: 'svSeedStore clears the flag WITHOUT a finally -- one throw silences the backup for the session',
    find: 'try { return saver(rows); }\n  finally { svSyncSuppressed = false; }',
    replace: 'var r = saver(rows); svSyncSuppressed = false; /*MUTANT-NO-FINALLY*/ return r;',
    marker: 'MUTANT-NO-FINALLY',
    expect: /finally|THROWS/i,
    expectLabel: 'the arm about a saver that throws, not somewhere incidental',
    suites: ['sairnvet_seed_never_syncs.js']
  },
  {
    // Seeding stops being suppressed at all: this is the original bug, where
    // opening a panel on a fresh device pushed invented controlled-substance
    // balances into the real register.
    name: 'seeding is no longer suppressed -- opening a panel pushes demo rows to the server',
    find: 'svSyncSuppressed = true;\n  try { return saver(rows); }',
    replace: 'svSyncSuppressed = false;/*MUTANT-SEED-PUSHES*/\n  try { return saver(rows); }',
    marker: 'MUTANT-SEED-PUSHES',
    expect: /ZERO server writes|seeded getter/i,
    expectLabel: 'the arm requiring zero server writes on a fresh store',
    suites: ['sairnvet_seed_never_syncs.js']
  },
  {
    // The HYDRATION site's finally, six lines from the one that always had it.
    // Section 4 of the suite exists because the two sites were not the same,
    // and this proves that section still reads BOTH rather than only the
    // seeder.
    name: 'the HYDRATION site loses its finally -- the other half of the same defect',
    find: 'try{ st(key,local); }\n        finally{ svSyncSuppressed=false; }',
    replace: 'st(key,local); svSyncSuppressed=false;/*MUTANT-HYDRATE-NO-FINALLY*/',
    marker: 'MUTANT-HYDRATE-NO-FINALLY',
    expect: /finally|suppression sites|exactly the two places/i,
    expectLabel: 'the arm that reads BOTH suppression sites, not just the seeder',
    suites: ['sairnvet_seed_never_syncs.js']
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

console.log('SAIRNvet seed suppression: the suite can be made to FAIL on what it claims\n');

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
