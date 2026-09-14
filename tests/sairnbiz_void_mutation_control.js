// tests/sairnbiz_void_mutation_control.js
//
// Run:  node tests/sairnbiz_void_mutation_control.js
//
// THE NEGATIVE CONTROL FOR THE VOID MECHANISM -- AND IT VERIFIES ITS OWN
// SABOTAGE APPLIED.
//
// Measured on this platform on 2026-09-13 by `tools/sabotage_control_check.py`:
// 23 of 39 negative controls NEVER VERIFY THEIR OWN SABOTAGE APPLIED. A control
// that greps for a string that no longer exists, mutates nothing, and then
// reports "the suite went red" is reporting nothing at all -- it would pass
// identically against a subject with the defect still in it.
//
// So every mutation below is asserted in THREE parts, in order:
//
//   1. the pattern is FOUND in the shipped file           (else: FAIL, stale anchor)
//   2. the mutated copy DIFFERS from the original          (else: FAIL, no-op edit)
//   3. the named suite, run against the mutated copy, EXITS NON-ZERO
//
// Part 1 is the one that goes stale silently. Part 2 is the one the 23 skipped.
//
// The mutations are written to a temp copy; sairnbiz.html is never touched.

'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const assert = require('assert');
const { spawnSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const SRC = path.join(ROOT, 'sairnbiz.html');
const ORIGINAL = fs.readFileSync(SRC, 'utf8');

let n = 0, failures = 0;
function ok(cond, label) {
  n++;
  if (cond) { console.log('  ok   ' + label); return; }
  failures++;
  console.log('  FAIL ' + label);
}
function section(s) { console.log('\n' + s); }

const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'sairnbiz-void-mutation-'));

function runSuite(suite, htmlPath) {
  const r = spawnSync(process.execPath, [path.join(ROOT, 'tests', suite)], {
    cwd: ROOT,
    env: Object.assign({}, process.env, { SB_HTML: htmlPath }),
    encoding: 'utf8'
  });
  return { code: r.status, out: (r.stdout || '') + (r.stderr || '') };
}

// EVERY MUTATION IS A REAL DEFECT SOMEBODY COULD WRITE, not a syntax error.
// A control that sabotages by breaking the parse proves only that the file
// still has to parse.
const MUTATIONS = [
  {
    name: 'the match stops excluding voided POs',
    find: "pos=pos.filter(function(p){return !sbIsVoid(p);});",
    replace: "pos=pos.filter(function(p){return true;});",
    suites: ['functional_core_is_pure.js']
  },
  {
    name: 'the match stops excluding voided RECEIPTS -- the inflated total returns',
    find: "recs=recs.filter(function(r){return !sbIsVoid(r);});",
    replace: "recs=recs.filter(function(r){return true;});",
    suites: ['functional_core_is_pure.js']
  },
  {
    name: 'sbIsVoid matches loosely, so "Cancelled" or a typo silently excludes a real receipt',
    find: "function sbIsVoid(r){ return !!(r&&String(r.status)==='Void'); }",
    replace: "function sbIsVoid(r){ return !!(r&&String(r.status)&&String(r.status)!=='Open'); }",
    suites: ['functional_core_is_pure.js']
  },
  {
    name: 'the role gate is removed from sbPOVoid',
    find: "  if(!sbCanVoid()){toast(sbVoidRefusal('a purchase order'),7000);return;}",
    replace: "  if(false){toast(sbVoidRefusal('a purchase order'),7000);return;}",
    suites: ['sairnbiz_void_not_delete.js']
  },
  {
    name: 'the role gate is removed from sbRecvVoid',
    find: "  if(!sbCanVoid()){toast(sbVoidRefusal('a goods receipt'),7000);return;}",
    replace: "  if(false){toast(sbVoidRefusal('a goods receipt'),7000);return;}",
    suites: ['sairnbiz_void_not_delete.js']
  },
  {
    name: 'a blank reason is accepted',
    find: "  if(!reason){toast('A reason is required to void '+what+' -- nothing was changed',6000);return null;}",
    replace: "  if(!reason){reason='(none given)';}",
    suites: ['sairnbiz_void_not_delete.js']
  },
  {
    name: 'a failed st() reports success anyway -- the silent half-applied void',
    find: "  if(!st('sb_po',rows)){toast(row.po_num+' was NOT voided -- storage may be full or unavailable. Nothing was changed; try again.',9000);return;}",
    replace: "  st('sb_po',rows);",
    suites: ['sairnbiz_void_not_delete.js']
  },
  {
    name: 'the PO void keys on po_num, so both halves of a duplicate pair are voided together',
    find: "function sbPOKey(p){ return String((p&&p.id)||(p&&p.po_num)||''); }",
    replace: "function sbPOKey(p){ return String((p&&p.po_num)||''); }",
    suites: ['sairnbiz_void_not_delete.js']
  },
  {
    name: 'the Received column stops excluding voided receipts -- screen and gate disagree',
    find: "      var rv=recs.filter(function(r){return String(r.po_num)===String(p.po_num)&&!sbIsVoid(r);})",
    replace: "      var rv=recs.filter(function(r){return String(r.po_num)===String(p.po_num);})",
    suites: ['sairnbiz_void_not_delete.js']
  },
  {
    name: 'a receipt may be logged against a voided PO again',
    find: "  if(!poRows.some(function(p){return !sbIsVoid(p);})){",
    replace: "  if(false){",
    suites: ['sairnbiz_void_not_delete.js']
  },
  {
    name: 'the PO sequence skips voided rows, so a voided number is handed out twice',
    find: "    var m=/^PO-(\\d{4})-(\\d+)$/.exec(String((r&&r.po_num)||''));",
    replace: "    if(sbIsVoid(r))return;\n    var m=/^PO-(\\d{4})-(\\d+)$/.exec(String((r&&r.po_num)||''));",
    suites: ['sairnbiz_void_not_delete.js']
  },
  {
    name: 'SB_VOID_ROLES names a role this app does not have',
    find: "var SB_VOID_ROLES=['owner','manager'];",
    replace: "var SB_VOID_ROLES=['admin','manager'];",
    suites: ['sairnbiz_void_not_delete.js']
  }
];

console.log('SAIRNbiz void: every arm is shown to FAIL on a sabotaged subject\n');

// ── 0. THE BASELINE ─────────────────────────────────────────────────────────
// Both suites must be GREEN against the untouched file first. Without this,
// every "went red" below could be a suite that is red for an unrelated reason.
section('0. baseline -- the suites are green against the shipped file');
{
  const clean = path.join(tmpDir, 'clean.html');
  fs.writeFileSync(clean, ORIGINAL);
  for (const suite of ['functional_core_is_pure.js', 'sairnbiz_void_not_delete.js']) {
    const r = runSuite(suite, clean);
    ok(r.code === 0, suite + ' passes against an unmutated copy (exit ' + r.code + ')');
  }
}

section('1. each mutation: found, applied, and caught');
let idx = 0;
for (const m of MUTATIONS) {
  idx += 1;
  console.log('\n  [' + idx + '] ' + m.name);

  // PART 1 -- THE ANCHOR IS REAL. This is the arm that rots: a string that
  // stopped matching months ago looks identical to one that matches, because
  // nothing downstream can tell a no-op edit from a real one.
  const hits = ORIGINAL.split(m.find).length - 1;
  ok(hits === 1,
     'the anchor is present in sairnbiz.html EXACTLY once (found ' + hits + ')');
  if (hits !== 1) continue;

  // PART 2 -- THE SABOTAGE ACTUALLY CHANGED THE BYTES. The half the platform
  // measured 23 controls skipping.
  const mutated = ORIGINAL.replace(m.find, m.replace);
  ok(mutated !== ORIGINAL, 'the mutated copy differs from the original');
  const file = path.join(tmpDir, 'mutant-' + idx + '.html');
  fs.writeFileSync(file, mutated);
  ok(fs.readFileSync(file, 'utf8').indexOf(m.replace.split('\n')[0]) !== -1,
     '...and the mutation is present in the file on disk that the suite will read');

  // PART 3 -- THE SUITE GOES RED.
  for (const suite of m.suites) {
    const r = runSuite(suite, file);
    ok(r.code !== 0, suite + ' FAILS on it (exit ' + r.code + ')');
    if (r.code === 0) {
      console.log('       -- the defect survived the suite. Last lines:');
      console.log(r.out.split('\n').slice(-6).map((l) => '       ' + l).join('\n'));
    }
  }
}

// ── 2. THE SHIPPED FILE IS UNTOUCHED ────────────────────────────────────────
section('2. sairnbiz.html was never written to');
{
  ok(fs.readFileSync(SRC, 'utf8') === ORIGINAL,
     'the shipped file is byte-identical to how this run found it');
}

try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (e) { /* temp dir */ }

console.log('\n' + (failures
  ? failures + ' OF ' + n + ' ASSERTIONS FAILED'
  : 'ALL ' + n + ' ASSERTIONS PASS'));
process.exit(failures ? 1 : 0);
