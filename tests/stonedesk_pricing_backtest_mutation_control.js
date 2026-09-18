// tests/stonedesk_pricing_backtest_mutation_control.js
// REQUIREMENT: tests/stonedesk_pricing_backtest.js can be MADE TO FAIL on each
//   property it holds -- the pricing backtest reads a file a user uploads and
//   reports how accurate the quote formula is, and a suite nobody has watched
//   go red is not evidence that it still refuses a file it cannot read
//
// Run:  node tests/stonedesk_pricing_backtest_mutation_control.js
//
// WHY THIS EXISTS AT ALL. parseAndStress() had NO suite until 2026-09-18, and
// that is precisely why it spent its whole life zipping torn rows to the header
// by position and dropping them silently: nothing could go red. Shipping the
// suite without a control would leave the same hole one level up -- a green
// suite that might be asserting nothing.
//
// ── EVERY PLANT IS GUARDED THREE WAYS, IN ORDER ─────────────────────────────
//   1. UNIQUENESS -- the anchor occurs exactly once in stonedesk.html. In a
//      2.6 MB file that is not a formality: an anchor matching twice would
//      mutate the first hit and the control would be testing another feature.
//   2. DIFFERENCE  -- the mutated text is not the original.
//   3. MATERIALISATION -- the file is read BACK and the marker looked for in
//      the bytes on disk, because the next process reads the file, not the
//      string this one built.
// A plant that cannot be placed exits 2 as COULD NOT PLANT, never as a pass.
//
// ── IT PATCHES NO TRACKED FILE ──────────────────────────────────────────────
// The suite carries an SD_HTML override, the convention SB_HTML, SV_HTML,
// DNT_HTML, LAW_HTML, BLD_HTML and RF_HTML already use. Section 6 asserts the
// real file is untouched and asks git as well.
//
// ── SECTION 5 IS WHAT MAKES THE REST MEAN ANYTHING ──────────────────────────
// A suite that failed on everything would satisfy every arm above it.
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const assert = require('assert');
const { spawnSync, execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const SUITE = path.join(ROOT, 'tests', 'stonedesk_pricing_backtest.js');
const APP = path.join(ROOT, 'stonedesk.html');

let n = 0;
const fails = [];
function ok(cond, label) {
  console.log('  ' + (cond ? 'ok  ' : 'FAIL') + ' ' + label);
  n++;
  if (!cond) fails.push(label);
}
function section(s) { console.log('\n' + s); }

const RAW = fs.readFileSync(APP, 'utf8');
// Anchors below are written with plain \n; the working tree may hold CRLF, and
// an assumption about that is not worth a brittle control. The suite normalises
// the same way, so the mutated copy it reads is the copy this file wrote.
const ORIGINAL = RAW.replace(/\r\n/g, '\n');

function gitPorcelain() {
  try {
    return execFileSync('git', ['-C', ROOT, 'status', '--porcelain', APP],
                        { encoding: 'utf8' });
  } catch (e) {
    return null;
  }
}
const PORCELAIN_BEFORE = gitPorcelain();
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'sd-backtest-'));

const MUTATIONS = [
  {
    // THE DEFECT ITSELF, restored by deleting one line. Without it a quoted
    // cell containing a comma tears, every later column is read one place
    // left, the row misses MATERIALS/PROJECTS and .filter(Boolean) drops it --
    // and the panel prints "Jobs Tested" over a number that is not the file.
    name: 'the length guard goes -- a torn row is dropped silently again',
    find: "    if(vals.length!==headers.length){torn.push({line:n+2,got:vals.length});return null;}\n",
    replace: "    /*MUTANT-NO-LENGTH-GUARD*/\n",
    marker: 'MUTANT-NO-LENGTH-GUARD',
    expect: /refuses the file|EVERY row torn/i,
    expectLabel: 'the arms about a torn row being refused rather than analysed around'
  },
  {
    // A DISAGREEMENT, NOT AN OVERFLOW. `>` catches the row that gained a cell
    // and misses the one that lost one -- and a SHORT row zipped by position
    // leaves later columns undefined, which reads as a zero in the arithmetic.
    // This is the half a reader would most easily write by accident.
    name: 'the guard catches only LONG rows, so a short row zips to undefined',
    find: 'if(vals.length!==headers.length){',
    replace: 'if(vals.length>headers.length){/*MUTANT-LONG-ONLY*/',
    marker: 'MUTANT-LONG-ONLY',
    expect: /FEWER cells/i,
    expectLabel: 'the arm about a row with fewer cells than the header'
  },
  {
    // A refusal notice printed ABOVE the previous run's rows is worse than no
    // refusal: the table still looks like a result and the notice reads as a
    // warning about it rather than as "nothing here was computed".
    name: 'the refusal leaves the previous run\'s table on screen',
    find: "    document.getElementById('stress-table').innerHTML='';\n",
    replace: "    /*MUTANT-KEEPS-STALE-TABLE*/\n",
    marker: 'MUTANT-KEEPS-STALE-TABLE',
    expect: /clears the table/i,
    expectLabel: 'the arm requiring a refused file to clear the table'
  },
  {
    // "Some row is wrong" is not actionable on a 500-row upload. The line
    // number is the difference between a message and a shrug.
    name: 'the refusal stops naming which line is torn',
    find: "+'First at line '+escHtml(String(torn[0].line))+' ('+escHtml(String(torn[0].got))",
    replace: "+'First at line '+escHtml('')+' ('+escHtml(String(torn[0].got))/*MUTANT-NO-LINE-NUMBER*/",
    marker: 'MUTANT-NO-LINE-NUMBER',
    expect: /NAMES the line/i,
    expectLabel: 'the arm requiring the refusal to name the line'
  },
  {
    // The other direction, and the one that would make the guard hated: a
    // stray blank line refusing an otherwise good file is a check people route
    // around, which is worse than not having it.
    name: 'a blank line is treated as a torn row, so one stray line refuses the file',
    find: '    if(!l.trim()) return null;\n',
    replace: '    /*MUTANT-BLANK-IS-TORN*/\n',
    marker: 'MUTANT-BLANK-IS-TORN',
    expect: /BLANK line/i,
    expectLabel: 'the arm about a blank line being skipped rather than refused'
  }
];

function plant(m) {
  const hits = ORIGINAL.split(m.find).length - 1;
  if (hits !== 1) {
    console.log('\nCOULD NOT PLANT: ' + m.name);
    console.log('  the anchor occurs ' + hits + ' time(s) in stonedesk.html, not 1.');
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
    env: Object.assign({}, process.env, { SD_HTML: htmlPath }),
    encoding: 'utf8'
  });
  return { code: r.status, out: (r.stdout || '') + (r.stderr || '') };
}

console.log('StoneDesk pricing backtest: the suite can be made to FAIL on what it claims\n');

let idx = 0;
for (const m of MUTATIONS) {
  idx += 1;
  section(idx + '. ' + m.name);
  const r = runSuite(plant(m));
  const failed = r.code !== 0;
  ok(failed, 'the suite FAILS   exit ' + r.code);
  // ── THE expect ARM IS ANCHORED ON THE FAILURE LINE, NOT ON THE WHOLE RUN ──
  // Two separate holes, and this control would have shipped with the second.
  //
  // ONE: a PASSING run prints every arm's own label, so a naive regex matches
  // the green output of a mutation the suite never noticed and credits it.
  // cc guarded that on the SAIRNdental control with `failed && expect.test(...)`
  // after measuring it -- a missed mutation exited 0 and the arm still said
  // "and it fails on ...".
  //
  // TWO, WHICH THAT GUARD DOES NOT CLOSE: on a run that fails for an UNRELATED
  // reason, every arm that still passed printed its label, so the intended
  // arm's words are in the output anyway. Cody measured exactly this on
  // 2026-09-18 across three controls -- 4 of 4 expect regexes still matched
  // after breaking something none of them was about -- and published the fix:
  // anchor the pattern to the FAIL line. This suite prints `  FAIL <name>`, so
  // that anchoring applies directly.
  //
  // THE (?:) IS LOAD-BEARING and Cody's note says it was got wrong first:
  // without the group, `FAIL[^\n]*a|b|c` is a top-level alternation whose later
  // branches match anywhere, which is the hole again in a new shape.
  const anchored = new RegExp('FAIL[^\\n]*(?:' + m.expect.source + ')', 'i');
  ok(failed && anchored.test(r.out),
     'and it fails ON THAT ARM -- ' + m.expectLabel
     + (failed ? '' : '   [not evaluated -- the suite did not fail]'));
}

section('6. CONTROL -- an UNMUTATED copy through the same path must PASS');
{
  const clean = path.join(TMP, 'clean.html');
  fs.writeFileSync(clean, ORIGINAL);
  const r = runSuite(clean);
  ok(r.code === 0, 'the same suite PASSES on an unmutated copy   exit ' + r.code);
  ok(/passed, 0 failed/.test(r.out), 'and it actually ran its arms');
}

section('7. the shipped file was never touched');
{
  ok(fs.readFileSync(APP, 'utf8') === RAW,
     'stonedesk.html is byte-identical to how this control found it');
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
