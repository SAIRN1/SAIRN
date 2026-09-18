// tests/sairnlaw_billing_codes_mutation_control.js
// REQUIREMENT: tests/sairnlaw_billing_codes.js can be MADE TO FAIL on each
//   property it holds -- an unreadable store used to empty the UTBMS dropdown
//   and a billable hour then saved with NO code onto the record invoices and
//   the LEDES export are built from, silently, and a suite nobody has watched
//   go red is not evidence that cannot happen again
//
// Run:  node tests/sairnlaw_billing_codes_mutation_control.js
//
// WHAT THE GUARDED SUITE GUARDS, in its own words: the accessor was
// `ld('law_billingcodes',[])`, and ld() returns its default when the key is
// ABSENT, when the stored JSON WILL NOT PARSE, and when localStorage is
// UNAVAILABLE. It logs all three and the UI said nothing about any of them. An
// empty list made fillBillingCodeSelect() write `innerHTML=''` -- an empty
// <select>, whose .value is '' -- and saveTime() validates the matter and the
// hours and NOT the code. A billable hour with no UTBMS code, on the record a
// firm bills from.
//
// Tier A and uncontrolled: law_timeentries, invoices.
//
// ── THE SUITE WAS RED BEFORE THIS CONTROL COULD BE BUILT AT ALL ────────────
// `4eaa3f05` (IOLTA reconciliation) registered a twentieth law_* resource and
// the suite's exact-count pin fired, correctly. A negative control cannot be
// built on a red suite -- section 5 would fail and every mutation would "fail"
// for the wrong reason -- so the pin was updated first, naming the resource and
// the commit, and deliberately NOT loosened to a floor. That is a separate
// commit from this file for a reason: fixing a red suite and proving it can go
// red are different claims.
//
// ── IT PATCHES NO TRACKED FILE ──────────────────────────────────────────────
// The suite gained a `LAW_HTML` override, the convention SB_HTML, SV_HTML and
// DNT_HTML already carry. Section 6 asserts the real file is untouched and asks
// git as well.
//
// ── EVERY PLANT IS GUARDED THREE WAYS: uniqueness, difference, and the bytes
// ── read back off disk. A plant that cannot be placed exits 2, never passes.
// ── `expect` is judged only on a FAILING run: a green suite prints every arm's
// ── own label, so matching it would credit a mutation nobody caught.
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const assert = require('assert');
const { spawnSync, execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const SUITE = path.join(ROOT, 'tests', 'sairnlaw_billing_codes.js');
const APP = path.join(ROOT, 'sairnlaw.html');

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
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'law-codes-'));

const MUTATIONS = [
  {
    // THE ORIGINAL DEFECT, restored exactly. `[]` as the default means an
    // absent, corrupt or unavailable store all produce an EMPTY dropdown, and
    // the only sign is a console line nobody is watching.
    name: 'the accessor falls back to [] again -- an unreadable store empties the dropdown',
    find: "function billingCodes(){return ld('law_billingcodes',LAW_BILLING_CODES);}",
    replace: "function billingCodes(){return ld('law_billingcodes',[]);}/*MUTANT-EMPTY-DEFAULT*/",
    marker: 'MUTANT-EMPTY-DEFAULT',
    expect: /falls back to the constant/i,   // NARROWED 2026-09-18: shared `never ""|real code` with m3, which no anchoring can separate -- Cody named this one specifically
    expectLabel: 'the arms about the constant fallback and a select that is never empty',
    suites: ['sairnlaw_billing_codes.js']
  },
  {
    // A STORED LIST MUST STILL WIN. The constant is a fallback, not an
    // override -- a firm whose codes were customised upstream would otherwise
    // have them silently replaced by the shipped 27 on every read.
    name: 'the constant OVERRIDES a stored list instead of backing it up',
    find: "function billingCodes(){return ld('law_billingcodes',LAW_BILLING_CODES);}",
    replace: "function billingCodes(){return LAW_BILLING_CODES;}/*MUTANT-CONST-WINS*/",
    marker: 'MUTANT-CONST-WINS',
    expect: /STORED list still wins|fallback, not an override|stored EMPTY list/i,
    expectLabel: 'the arms about a stored list winning over the constant',
    suites: ['sairnlaw_billing_codes.js']
  },
  {
    // The select is what makes .value a real code. Filling it from a literal
    // empty list is the same end state as the original defect with the
    // accessor left correct -- which is why the suite asserts the SELECT and
    // not only the accessor.
    name: 'the select is filled from nothing, so .value is "" with a correct accessor',
    find: "el.innerHTML=billingCodes().map(function(c){return '<option value=\"'+c.code+'\">'+H(c.code)+' -- '+H(c.label)+'</option>';}).join('');",
    replace: "el.innerHTML='';/*MUTANT-EMPTY-SELECT*/",
    marker: 'MUTANT-EMPTY-SELECT',
    expect: /select is filled/i,             // NARROWED 2026-09-18: see m1
    expectLabel: 'the arm requiring the filled select to yield a real code',
    suites: ['sairnlaw_billing_codes.js']
  },
  {
    // A missing #ttcode must stay a safe no-op. Removing the guard turns a
    // panel that has not rendered yet into a thrown TypeError mid-save.
    name: 'a missing #ttcode element throws instead of being a safe no-op',
    find: "var el=$('ttcode');if(!el)return;",
    replace: "var el=$('ttcode');/*MUTANT-NO-ELEMENT-GUARD*/",
    marker: 'MUTANT-NO-ELEMENT-GUARD',
    expect: /missing #ttcode|safe no-op/i,
    expectLabel: 'the arm about a missing #ttcode element',
    suites: ['sairnlaw_billing_codes.js']
  }
];

function plant(m) {
  const hits = ORIGINAL.split(m.find).length - 1;
  if (hits !== 1) {
    console.log('\nCOULD NOT PLANT: ' + m.name);
    console.log('  the anchor occurs ' + hits + ' time(s) in sairnlaw.html, not 1.');
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
    env: Object.assign({}, process.env, { LAW_HTML: htmlPath }),
    encoding: 'utf8'
  });
  return { code: r.status, out: (r.stdout || '') + (r.stderr || '') };
}

console.log('SAIRNlaw billing codes: the suite can be made to FAIL on what it claims\n');

// -- THE expect ARM IS ANCHORED ON THE FAILURE LINE, NOT ON THE WHOLE RUN ---
// Two holes, and this file had the second one.
//
// ONE: a PASSING run prints every arm's own label, so a bare regex over stdout
// matches the green output of a mutation the suite never noticed and credits
// it. cc guarded that on the SAIRNdental control after measuring it.
//
// TWO, WHICH THAT GUARD DOES NOT CLOSE: on a run that fails for an UNRELATED
// reason, every arm that still PASSED printed its label, so the intended arm's
// words are in the output anyway. Cody measured it across three controls on
// 2026-09-18 -- 4 of 4 expect regexes still matched after breaking something
// none of them was about -- and published this fix, open-work row 63.
//
// MEASURED ACROSS EVERY CONTROL ON THE PLATFORM BEFORE CHANGING ANY OF THEM,
// by planting each mutation and testing EVERY expect against every other
// mutation's output: 104 cross matches unanchored, 15 anchored. The 89 that
// disappear were matches against lines an arm printed while PASSING.
//
// THE NON-CAPTURING GROUP AROUND THE PATTERN IS LOAD-BEARING, per Cody's note
// that they got it wrong first: without it the pattern degenerates into a
// top-level alternation whose later branches match anywhere, which is the same
// hole wearing a fix.
//
// The leading alternation covers all three shapes a suite here fails in: a
// printed FAIL, a TAP-style "not ok", and a thrown AssertionError.
function anchoredExpect(expect) {
  return new RegExp('(FAIL|not ok|AssertionError)[^\\n]*(?:' + expect.source + ')', 'i');
}

let idx = 0;
for (const m of MUTATIONS) {
  idx += 1;
  section(idx + '. ' + m.name);
  const r = runSuite(plant(m));
  const failed = r.code !== 0;
  ok(failed, 'the suite FAILS   exit ' + r.code);
  ok(failed && anchoredExpect(m.expect).test(r.out),
     'and it fails ON THAT ARM -- ' + m.expectLabel
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
  ok(/passed/i.test(r.out), 'and it actually ran its arms');
}

section('6. the shipped file was never touched');
{
  ok(fs.readFileSync(APP, 'utf8') === ORIGINAL,
     'sairnlaw.html is byte-identical to how this control found it');
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
