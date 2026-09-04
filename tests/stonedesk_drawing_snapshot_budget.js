// tests/stonedesk_drawing_snapshot_budget.js
//
// Run:  node tests/stonedesk_drawing_snapshot_budget.js
//
// sdDrawSave() stores a canvas snapshot per saved drawing, and the open-work
// row asked for a MEASUREMENT before any change. Measured in a real browser
// against the deployed app on 2026-09-04:
//
//   flat placeholder, no stone selected   18.4 KB PNG /  25,114 chars
//   U-shape, granite/dark (worst case)    49.9 KB PNG /  68,186 chars   2.7x
//
// localStorage counts UTF-16, so that worst case cost 133 KB of quota per
// entry, and the old 50-entry cap therefore asked for ~6.5 MB of a ~5 MB
// budget. sairn.vercel.app is ONE origin shared by every SAIRN app -- 199
// keys and 1.25 MB already in use before a drawing exists -- so the failure
// mode was never "StoneDesk gets slower", it was "every other SAIRN app on
// the origin stops being able to save, and blames itself".
//
// Michael's call: JPEG q0.70 at full resolution (downscaling was rejected --
// an operator reading a dimension off an old drawing is a functional risk,
// not a cosmetic one), plus a lower cap since that costs no fidelity.
//
// THE PART THAT ARITHMETIC WOULD HAVE MISSED, and the reason the change was
// looked at before it shipped: ct-canvas is TRANSPARENT. The pale field is
// CSS, not pixels. JPEG has no alpha, so a bare toDataURL('image/jpeg')
// flattens transparency to BLACK -- verified in the browser, where the grid
// lines vanished entirely and the drawing came back as something the rep
// never drew. The snapshot is composited onto the canvas's own computed
// background first. These assertions exist so that composite cannot be
// "simplified" away later by someone reading only the compression rationale.

'use strict';
const fs = require('fs');
const path = require('path');

const HTML = path.join(__dirname, '..', 'stonedesk.html');
const src = fs.readFileSync(HTML, 'utf8');

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

function balanced(start) {
  let i = src.indexOf('{', start), depth = 0;
  for (; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') { depth--; if (!depth) return src.slice(start, i + 1); }
  }
  throw new Error('unbalanced from ' + start);
}
function fn(decl) {
  const i = src.indexOf(decl);
  if (i < 0) throw new Error('not found: ' + decl);
  return balanced(i);
}

// Comments carry the old expressions verbatim on purpose, so every assertion
// below reads the CODE only -- the trap this repo has now hit twice.
const save = fn('window.sdDrawSave=function(){')
  .split('\n').filter((l) => !l.trim().startsWith('//')).join('\n');

check('the snapshot is encoded as JPEG at q0.70',
  /toDataURL\('image\/jpeg',\s*0\.70\)/.test(save), true);
check('and no longer as PNG', /toDataURL\('image\/png'\)/.test(save), false);

// The composite. Each of these three is load-bearing: without the fill the
// field is black, without the fill BEFORE drawImage the fill covers the
// drawing, and without the fallback a transparent computed style puts the
// black field straight back.
check('a backing canvas is created at the same size',
  /snap\.width=canvas\.width;\s*snap\.height=canvas\.height;/.test(save), true);
check('it is painted before the drawing is composited onto it',
  save.indexOf('sctx.fillRect(') < save.indexOf('sctx.drawImage(canvas'), true);
check('with the canvas\'s OWN computed background, not a hardcoded colour',
  /getComputedStyle\(canvas\)\.backgroundColor/.test(save), true);
check('and a transparent or unreadable background falls back to white, '
  + 'because falling back to none is the black-field bug',
  /bg='#FFFFFF'/.test(save), true);
check('the fallback recognises the rgba(0,0,0,0) form getComputedStyle returns',
  /rgba\\\(\\s\*0\\s\*,\\s\*0\\s\*,\\s\*0\\s\*,\\s\*0\\s\*\\\)/.test(save), true);

// The cap.
check('the retention cap is 20', /drawings\.length>20/.test(save), true);
check('and the old 50 is gone', /drawings\.length>50/.test(save), false);
check('the slice matches the test, so the cap is not off by a stale number',
  /drawings=drawings\.slice\(0,20\)/.test(save), true);

// What must NOT change: the honest failure path this file already had.
check('the write still goes through st(), whose boolean the caller reads',
  /var drawingSaved = st\('sd_drawings',drawings\);/.test(save), true);
check('and the status line still tells the truth on a failed write',
  /Could not save -- storage may be full or unavailable/.test(save), true);
check('the encode is still guarded, so a canvas that refuses to export '
  + 'costs the image and not the whole save',
  /try\{[\s\S]*entry\.dataUrl=snap\.toDataURL[\s\S]*\}catch\(e\)\{\}/.test(save), true);

// The measured budget, as arithmetic rather than prose. 58 KB is the worst
// case measured AFTER the change (29,123 chars x 2 bytes).
{
  const perEntryKB = 58, cap = 20;
  check('20 entries at the measured worst case stay near 1.2 MB',
    Math.round(perEntryKB * cap / 1024 * 10) / 10, 1.1);
  check('and the old shape -- 50 entries of 133 KB -- was over 6 MB',
    Math.round(133 * 50 / 1024 * 10) / 10, 6.5);
}

console.log((fail ? 'FAILED' : 'ok') + '  stonedesk-drawing-snapshot-budget: ' +
  pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
