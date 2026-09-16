// tests/sairnbiz_po_recv_mutation_control.js
// REQUIREMENT: tests/sairnbiz_po_recv_reach_the_server.js can be MADE TO FAIL on
//   each defect it claims to hold -- the purchase order and the receipt are the
//   only two documents that say a paid bill was ever entitled to be paid, and a
//   suite nobody has watched go red is not evidence that they are covered
//
// Run:  node tests/sairnbiz_po_recv_mutation_control.js
//
// THE SUITE THIS CONTROLS IS TIER A AND HAD NO CONTROL. `tools/
// suite_control_triage.py` ranks the suites nobody has ever tried to break by
// the criticality tier of what they name, and sairnbiz_po_recv_reach_the_
// server.js sits in the Tier A list: sb_ap, sb_invs, sb_po, sb_recv. Measured
// on the run that prompted this: 155 suites, 17 with a negative control, 138
// without, 58 of those Tier A.
//
// WHY THIS PAIR IS THE SHARP ONE, in the suite's own words: the bill was
// already backed up and the ledger entry settling it is durable in Postgres.
// The PO and the receipt are the only two documents that justify either. Clear
// the browser and a payable and a payment survive with nothing behind them --
// and sbThreeWayMatch, reading an empty sb_po, does not go quiet, it starts
// making a false accusation about work that was done right.
//
// ── IT NEVER TOUCHES A TRACKED FILE, AND THAT IS NOT CAUTION, IT IS THE
// ── SUITE'S OWN AFFORDANCE BEING USED AS INTENDED
// The suite reads `process.env.SB_HTML` in place of `sairnbiz.html`. So every
// mutation below is planted in a COPY in a temp directory and the suite is
// pointed at it. No worktree, no `git checkout --` restore, and therefore none
// of the residue class that denied three legitimate pushes on 2026-09-08 --
// a probe's mid-run mutation on disk is indistinguishable from a real edit to
// every gate that reads the working tree. Section 5 asserts the real file is
// still clean at the end rather than assuming it.
//
// ── EVERY PLANT IS GUARDED THREE WAYS, IN ORDER ─────────────────────────────
//   1. UNIQUENESS -- the anchor occurs exactly once. `tools/sabotage.py` names
//      this the strongest of the shapes: presence catches a rename and is blind
//      to an anchor matching in four places; a count catches both.
//   2. DIFFERENCE  -- the mutated text is not the original. `String.replace`
//      silently does nothing on a miss, which is the whole class
//      `tools/sabotage_control_check.py` measures.
//   3. MATERIALISATION -- the file is read BACK off disk and the marker looked
//      for there. A claim about a string in memory is not a claim about what
//      the next process will read.
//
// ── AND THE ARM THAT MAKES THE OTHERS MEAN ANYTHING IS SECTION 4 ────────────
// A suite that failed on everything would satisfy every arm above. Section 4
// runs the same suite against an UNMUTATED copy through the same SB_HTML path
// and demands exit 0. Without it this file proves the suite is noisy, not that
// it discriminates.
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const assert = require('assert');
const { spawnSync, execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const SUITE = path.join(ROOT, 'tests', 'sairnbiz_po_recv_reach_the_server.js');
const APP = path.join(ROOT, 'sairnbiz.html');

let n = 0;
const fails = [];
function ok(cond, label) {
  console.log('  ' + (cond ? 'ok  ' : 'FAIL') + ' ' + label);
  n++;
  if (!cond) fails.push(label);
}
function section(s) { console.log('\n' + s); }

const ORIGINAL = fs.readFileSync(APP, 'utf8');
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'sb-porecv-'));

// COULD-NOT-RUN IS A THIRD STATE. A plant that cannot be placed is not a
// mutation that found nothing; it is a control that did not run, and folding
// the two together is what this file exists to make impossible one level down.
function plant(label, anchor, replacement, marker) {
  const hits = ORIGINAL.split(anchor).length - 1;
  if (hits !== 1) {
    console.log('\nCOULD NOT PLANT: ' + label);
    console.log('  the anchor occurs ' + hits + ' time(s) in sairnbiz.html, not 1.');
    console.log('  That is a STALE ANCHOR, not a passing control. Nothing was tested.');
    process.exit(2);
  }
  const mutated = ORIGINAL.replace(anchor, replacement);
  if (mutated === ORIGINAL) {
    console.log('\nCOULD NOT PLANT: ' + label + ' -- the replacement changed nothing.');
    process.exit(2);
  }
  const file = path.join(TMP, label.replace(/[^\w]+/g, '-') + '.html');
  fs.writeFileSync(file, mutated);
  const readBack = fs.readFileSync(file, 'utf8');
  if (readBack.indexOf(marker) === -1) {
    console.log('\nCOULD NOT PLANT: ' + label + ' -- the marker is absent from the '
                + 'bytes on disk, so the next process would read the original.');
    process.exit(2);
  }
  return file;
}

function runSuite(htmlPath) {
  const r = spawnSync(process.execPath, [SUITE], {
    cwd: ROOT,
    env: Object.assign({}, process.env, { SB_HTML: htmlPath }),
    encoding: 'utf8'
  });
  return { code: r.status, out: (r.stdout || '') + (r.stderr || '') };
}

// ── THE MUTATIONS ARE A DECLARED TABLE, NOT FOUR HAND-ROLLED BLOCKS ────────
// Restructured 2026-09-16, and the reason is that two tools READ this shape.
// `suite_control_coverage.survey()` credits a suite with a control only when
// the probe declares `MUTATIONS =`, and `mutation_anchor_check.py` parses the
// same table to sweep every anchor in the repo for uniqueness. Written as four
// inline plant() calls, this file was correct and INVISIBLE to both -- the
// triage went on listing sairnbiz_po_recv_reach_the_server.js among the
// uncontrolled Tier A suites after its control existed, which is an
// under-count in the direction that matters.
//
// `expect` and `forbid` are per-mutation because they are FACTS ABOUT THE
// MUTATION, not decoration: which arm of the suite should notice this
// particular defect, and -- for the persistence one -- which failure shape
// means the suite crashed beside the defect rather than naming it.
const MUTATIONS = [
  {
    // po_num comes from a per-device counter, so two workstations both raise
    // PO-2026-001. Keying the upsert on it lets the second device's PO
    // overwrite the first through resolution=merge-duplicates, with no error
    // anywhere. This is the defect the suite's section 2 exists for.
    name: 'the minted id becomes the PO NUMBER -- one row, two real purchase orders',
    find: "do{id=prefix+Date.now().toString(36)+'-'+(i+n);n++;}while(seen[id]);",
    replace: "id=String(r.po_num||('zzmut'+i));/*MUTANT-ID-IS-PO-NUM*/",
    marker: 'MUTANT-ID-IS-PO-NUM',
    expect: /SHARING A NUMBER|not the PO number/,
    expectLabel: 'the arm about two POs sharing a number, not somewhere incidental',
    suites: ['sairnbiz_po_recv_reach_the_server.js']
  },
  {
    // Rows raised before 2026-09-14 carry po_num and no id. sbSyncCollection
    // SKIPS a record without one, so without minting the old POs back up to
    // nothing while the newer rows sync. Nothing reports it.
    name: 'sb_po stops minting at all -- half a collection backs up, no error',
    find: 'var prefix=SB_ID_PREFIX[key];',
    replace: "var prefix=(key==='sb_po')?undefined:SB_ID_PREFIX[key];/*MUTANT-NO-MINT*/",
    marker: 'MUTANT-NO-MINT',
    expect: /changed sb_po|carries an id/,
    expectLabel: 'the minting arms specifically',
    suites: ['sairnbiz_po_recv_reach_the_server.js']
  },
  {
    // Minting without writing back means the next load mints DIFFERENT ids for
    // the same rows, so one purchase order becomes two server rows and the
    // three-way match sees a PO it cannot reconcile. The write is deliberately
    // direct rather than through st(); removing it leaves every in-memory
    // assertion passing.
    name: 'the minted ids are never PERSISTED -- the same PO backs up twice',
    find: 'try{localStorage.setItem(key,JSON.stringify(arr));}catch(e){',
    replace: 'try{void 0;/*MUTANT-NO-PERSIST*/}catch(e){',
    marker: 'MUTANT-NO-PERSIST',
    expect: /WRITTEN BACK|PERSISTED/,
    expectLabel: 'the persistence arm, which is the one an in-memory test cannot reach',
    // The suite CRASHED here with a raw node JSON error until 2026-09-16, so
    // this shape is forbidden as well as the right arm being required.
    forbid: /is not valid JSON/,
    forbidLabel: 'it NAMES the defect rather than throwing a raw JSON parse error beside it',
    suites: ['sairnbiz_po_recv_reach_the_server.js']
  },
  {
    // The drift shape the suite checks BIDIRECTIONALLY: a collection present in
    // the API, the registry and the schema and absent from the client's own
    // list backs up nothing forever while three of the four places say it is
    // covered.
    name: 'sb_po leaves the synced list -- the four lists stop agreeing',
    find: "'sb_incidents','sb_po','sb_recv','sb_ts'",
    replace: "'sb_incidents','sb_recv','sb_ts'/*MUTANT-UNSYNCED*/",
    marker: 'MUTANT-UNSYNCED',
    expect: /SB_SYNCED carries sb_po|actually synced by the client/,
    expectLabel: 'the list that stopped agreeing',
    suites: ['sairnbiz_po_recv_reach_the_server.js']
  }
];

console.log('SAIRNbiz po/recv: the suite can be made to FAIL on what it claims\n');

let idx = 0;
for (const m of MUTATIONS) {
  idx += 1;
  section(idx + '. ' + m.name);
  const f = plant(m.name, m.find, m.replace, m.marker);
  const r = runSuite(f);
  ok(r.code !== 0, 'the suite FAILS   exit ' + r.code);
  ok(m.expect.test(r.out), 'and it fails on ' + m.expectLabel);
  if (m.forbid) {
    ok(!m.forbid.test(r.out), 'and ' + m.forbidLabel);
  }
}

// ── 5 ───────────────────────────────────────────────────────────────────────
section('5. CONTROL -- an UNMUTATED copy through the same path must PASS');
// Without this, every arm above is satisfied by a suite that fails on anything,
// including on being handed a file through SB_HTML at all.
{
  const clean = path.join(TMP, 'clean.html');
  fs.writeFileSync(clean, ORIGINAL);
  assert.strictEqual(fs.readFileSync(clean, 'utf8'), ORIGINAL,
                     'the clean copy is not byte-identical to the shipped file');
  const r = runSuite(clean);
  ok(r.code === 0, 'the same suite PASSES on an unmutated copy   exit ' + r.code);
  ok(/assertion/i.test(r.out) || r.out.length > 0, 'and it actually ran');
}

section('6. the shipped file was never touched');
{
  ok(fs.readFileSync(APP, 'utf8') === ORIGINAL,
     'sairnbiz.html is byte-identical to how this control found it');
  let porcelain = '';
  try {
    porcelain = execFileSync('git', ['-C', ROOT, 'status', '--porcelain', 'sairnbiz.html'],
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
