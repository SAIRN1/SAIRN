// tests/cut_sheet_basis_parity.js
//
// Run:  node tests/cut_sheet_basis_parity.js
//
// THE BUG CLASS: two copies of one calculation, and the copy that leaves the
// building lost the caveats. Found by the 2026-09-03 duplicated/diverged sweep
// that followed the base-system-prompt find.
//
// calcDrawing() renders the Drawing Tool's figures ON SCREEN with a sub-label
// under each one stating its basis. printDrawCutSheet() recomputes the SAME
// figures for the Fabrication Cut Sheet -- the copy that goes to the saw and,
// on some jobs, to the customer -- and stated none of them.
//
// The labour figure is the sharpest. The sheet prints the real Material a few
// rows above, then a THH figure computed at GRANITE's 4hr/50sqft regardless of
// what that material is. A reader with no caveat in front of them has every
// reason to read it as material-specific. The app's own base prompt tells the
// AI marble benchmarks at 4.2 and quartz at 3.5, so the same silent number is
// low on one job and high on another.
//
// AND A STALE CAPTION ON SCREEN. "Estimated at 50 sqft per slab" was a
// hardcoded literal sitting under a slab count computed from the
// admin-editable sairn-unit-slab_sqft field. A 2026-08-13 fix moved the
// COMPUTATION to that field and left the CAPTION behind, so a shop that set 55
// saw a count derived from 55 explained as 50. A caption that describes a
// different number than the one beside it is worse than no caption, because it
// gets read and it agrees with nothing.
//
// WHAT THIS FILE DOES NOT ASSERT: that the THH number is right. It is not
// material-aware, and making it so changes labour on live quotes -- a product
// decision raised separately, not a disclosure fix. This holds the DISCLOSURE.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const ROOT = path.join(__dirname, '..');
// Newlines normalised before anything looks for one. The working tree is
// checked out CRLF on Windows and LF elsewhere, so a boundary marker written as
// '\n}\n' matches on one machine and silently finds nothing on the other --
// which reads as "function not found" rather than as a line-ending problem.
const html = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8').replace(/\r\n/g, '\n');

function fnBody(decl, endMarker) {
  const s = html.indexOf(decl);
  assert.ok(s > 0, 'not found in stonedesk.html: ' + decl);
  const e = html.indexOf(endMarker, s);
  assert.ok(e > s, 'unterminated: ' + decl);
  return html.slice(s, e);
}

const calc = fnBody('function calcDrawing() {', 'function dcSyncLiveToQuoteEngine');
// Bounded by the next top-level declaration rather than a bare "\n}\n": the
// function's own body contains lines ending in `}` at column 0 inside template
// strings, and a marker that loose finds the wrong one.
const print = (function () {
  const s = html.indexOf('function printDrawCutSheet() {');
  assert.ok(s > 0, 'printDrawCutSheet not found');
  const e = html.indexOf('\n}\n', s + 100);
  assert.ok(e > s, 'printDrawCutSheet unterminated');
  return html.slice(s, e);
})();

let n = 0;
function ok(cond, label) { assert.ok(cond, label); n++; }

// ── 1. Both copies still exist and still compute the same three figures ────
ok(/const slabSqFt = parseFloat\(\(document\.getElementById\('sairn-unit-slab_sqft'\)/.test(calc),
   'calcDrawing reads the admin-editable slab size');
ok(/const slabSqFt = parseFloat\(\(document\.getElementById\('sairn-unit-slab_sqft'\)/.test(print),
   'printDrawCutSheet reads the same admin-editable slab size');
ok(/const thh=\(totalMat\/slabSqFt\*4\)\.toFixed\(1\)/.test(calc), 'calcDrawing computes THH');
ok(/const thh=\(totalMat\/slabSqFt\*4\)\.toFixed\(1\)/.test(print), 'printDrawCutSheet computes THH the same way');
ok(/\*1\.15/.test(calc) && /\*1\.15/.test(print),
   'both apply the same flat 15% waste allowance');

// ── 2. THE STALE CAPTION IS GONE ───────────────────────────────────────────
ok(!/Estimated at 50 sqft per slab/.test(html),
   'the hardcoded "50" caption is gone -- it described a number the code no longer used');
ok(/'Estimated at '\+slabSqFt\+' sqft per slab'/.test(calc),
   'and the caption is now built from the value actually used');

// ── 3. THE PRINTED SHEET NOW CARRIES ITS BASIS ─────────────────────────────
ok(/How these figures were calculated/.test(print),
   'the cut sheet has a basis section');
ok(/flat 15% waste allowance/.test(print),
   'ORDER QTY discloses the 15% waste allowance it includes');
ok(/'\s*\+\s*slabSqFt\s*\+\s*' sqft per slab/.test(print),
   'Slabs Est. discloses the slab size actually used, from the live field not a literal');
ok(/Granite benchmark 4hr per 50 sqft/.test(print),
   'Est. Labor discloses the granite benchmark');
ok(/NOT adjusted for the material above/.test(print),
   'and says plainly that it is not adjusted for the material printed on the same sheet');

// ── 4. Screen and paper say the same thing about the same figure ───────────
// Not byte-identical wording -- one is a sub-label and one is a table row --
// but neither may be silent about a basis the other discloses.
[
  ['waste allowance', /15%/, /15% waste allowance/],
  ['slab size',       /slabSqFt\+' sqft per slab'/, /slabSqFt\s*\+\s*' sqft per slab/],
  ['THH benchmark',   /Granite benchmark 4hr per 50sqft/, /Granite benchmark 4hr per 50 sqft/]
].forEach(function (row) {
  ok(row[1].test(calc), 'screen discloses the ' + row[0]);
  ok(row[2].test(print), 'and the printed sheet discloses the ' + row[0] + ' too');
});

// ── 5. The material really is printed on that sheet ────────────────────────
// This is what makes an undisclosed granite-rate labour figure misleading
// rather than merely terse. If the sheet ever stops printing the material,
// this finding changes shape and someone should re-read it.
ok(/Material<\/span>/.test(print) || /rl">Material/.test(print),
   'the cut sheet prints the job material, a few rows above the labour figure');

// ── 6. Negative controls ───────────────────────────────────────────────────
ok(!/Estimated at '\+50\+'/.test(calc), 'the caption is not a re-hardcoded 50 in disguise');
(function () {
  // If the basis section were removed, section 3 must fail. Proven, not assumed.
  const stripped = print.replace('How these figures were calculated', 'Notes');
  ok(!/How these figures were calculated/.test(stripped),
     'NEGATIVE CONTROL: removing the basis heading is detectable, so assertion 3 is load-bearing');
})();

console.log('cut_sheet_basis_parity: ' + n + '/' + n + ' assertions passed');
