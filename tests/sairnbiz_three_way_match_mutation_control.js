// tests/sairnbiz_three_way_match_mutation_control.js
// REQUIREMENT: tests/sairnbiz_bill_cannot_settle_unmatched.js can be MADE TO
//   FAIL on each reason the three-way match refuses for -- the gate is what
//   stops a bill being paid with no purchase order, no receipt, the wrong
//   vendor or the wrong amount, and a gate nobody has watched refuse is
//   indistinguishable from one that always says yes
//
// Run:  node tests/sairnbiz_three_way_match_mutation_control.js
//
// WHAT THE GUARDED SUITE GUARDS. SAIRNbiz had a ZERO-way match: saveBill()
// created a payable from one form and sbPayBill() settled it from that same
// internally-created row -- no second document, no second person, no amount
// re-entered. `grep -ciE "purchase order|receiving|packing slip|bill of lading"`
// returned 0 against the file. The match was not skipped; there was nothing to
// match against.
//
// `tools/suite_control_triage.py` ranked the suite that now holds that gate
// among the Tier A ones with no negative control -- sb_ap, sb_po, sb_recv. It
// is green, and green says nothing about whether it would notice the gate
// going soft.
//
// ── FIVE REFUSALS, FOUR DRIVEN, AND THE FIFTH SAID OUT LOUD ────────────────
// sbMatchPure refuses for: no PO number, no such PO, nothing received, wrong
// vendor, and a money mismatch against either the PO or the receipts. Four are
// mutated below. THE "NO SUCH PO" BRANCH IS DELIBERATELY NOT ONE OF THEM: the
// only surgical way to disable it leaves `pos[0]` undefined and the function
// throws, so the suite would go red on a CRASH rather than on the gate being
// soft -- a mutation the suite "catches" for the wrong reason proves nothing
// about the arm it is supposed to exercise. Named here rather than quietly
// skipped, because an untested branch inside a tested function is exactly what
// a control is meant to surface.
//
// ── IT PATCHES NO TRACKED FILE ──────────────────────────────────────────────
// The suite already reads `process.env.SB_HTML` -- the convention this app's
// suites adopted before either of them was controlled -- so every mutation is
// planted in a COPY in a temp directory. No worktree, no restore, and none of
// the residue class that denied three legitimate pushes on 2026-09-08. Section
// 6 asserts the real file is untouched and asks git as well.
//
// ── EVERY PLANT IS GUARDED THREE WAYS, IN ORDER ─────────────────────────────
//   1. UNIQUENESS -- the anchor occurs exactly once.
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
const SUITE = path.join(ROOT, 'tests', 'sairnbiz_bill_cannot_settle_unmatched.js');
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
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'sb-3way-'));

// `expect` names the arm that should notice. Asserting only on the exit code
// would credit the suite for failing on something unrelated to the defect.
const MUTATIONS = [
  {
    name: 'a bill with NO PO NUMBER matches -- the zero-way match returns',
    find: "if(!po_num) return {ok:false,reasons:['no purchase order number on this bill']};",
    replace: "if(!po_num) return {ok:true,reasons:[]};/*MUTANT-NO-PO-OK*/",
    marker: 'MUTANT-NO-PO-OK',
    expect: /NO PO NUMBER/i,
    expectLabel: 'the no-PO-number arm',
    suites: ['sairnbiz_bill_cannot_settle_unmatched.js']
  },
  {
    // The bill exceeds the purchase order. Without this the second person's
    // authorisation -- the PO -- stops bounding what the first person can pay.
    name: 'BILLED MORE THAN THE PO no longer refuses',
    find: 'if(Math.abs(billC-poC)>tolC)',
    replace: 'if(false&&Math.abs(billC-poC)>tolC)/*MUTANT-OVERBILL-OK*/',
    marker: 'MUTANT-OVERBILL-OK',
    expect: /BILLED MORE THAN THE PO/i,
    expectLabel: 'the over-billing arm',
    suites: ['sairnbiz_bill_cannot_settle_unmatched.js']
  },
  {
    // Billed in full for a partial delivery: the goods-received note stops
    // bounding the payment, which is the third document's entire job.
    name: 'BILLED IN FULL FOR A PARTIAL DELIVERY no longer refuses',
    find: 'if(recs.length&&Math.abs(billC-recvC)>tolC)',
    replace: 'if(false&&recs.length&&Math.abs(billC-recvC)>tolC)/*MUTANT-PARTIAL-OK*/',
    marker: 'MUTANT-PARTIAL-OK',
    expect: /PARTIAL DELIVERY/i,
    expectLabel: 'the partial-delivery arm',
    suites: ['sairnbiz_bill_cannot_settle_unmatched.js']
  },
  {
    // A bill from a different vendor than the PO authorised. This is the arm
    // that separates a clerical error from a redirected payment.
    name: 'A DIFFERENT VENDOR ON THE BILL no longer refuses',
    find: 'if(sbVendorKey(po.vendor)!==sbVendorKey(vendor))',
    replace: 'if(false&&sbVendorKey(po.vendor)!==sbVendorKey(vendor))/*MUTANT-VENDOR-OK*/',
    marker: 'MUTANT-VENDOR-OK',
    expect: /DIFFERENT VENDOR/i,
    expectLabel: 'the vendor-mismatch arm',
    suites: ['sairnbiz_bill_cannot_settle_unmatched.js']
  }
];

function plant(m) {
  const hits = ORIGINAL.split(m.find).length - 1;
  if (hits !== 1) {
    console.log('\nCOULD NOT PLANT: ' + m.name);
    console.log('  the anchor occurs ' + hits + ' time(s) in sairnbiz.html, not 1.');
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
    env: Object.assign({}, process.env, { SB_HTML: htmlPath }),
    encoding: 'utf8'
  });
  return { code: r.status, out: (r.stdout || '') + (r.stderr || '') };
}

console.log('SAIRNbiz three-way match: the suite can be made to FAIL on each refusal\n');

let idx = 0;
for (const m of MUTATIONS) {
  idx += 1;
  section(idx + '. ' + m.name);
  const r = runSuite(plant(m));
  ok(r.code !== 0, 'the suite FAILS   exit ' + r.code);
  ok(m.expect.test(r.out), 'and it fails on ' + m.expectLabel);
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
     'sairnbiz.html is byte-identical to how this control found it');
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
