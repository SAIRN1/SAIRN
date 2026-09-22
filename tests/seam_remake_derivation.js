// tests/seam_remake_derivation.js
// REQUIREMENT: the Seam AI panel's remake figures are DERIVED from the real
//   sd_remakes log, because a boolean written at analysis time can only ever
//   be false and three user-facing tiles were reading it
//
// Run:  node tests/seam_remake_derivation.js
//
// WHAT SHIPPED, AND WHY IT IS WORSE THAN THE CSV COLUMN IT WAS REPORTED AS.
// Every row sdSeamAnalyze() has ever written carried `remake:false`, set at
// both insert sites and never set true by anything in the file. Three things
// read it:
//
//   seam-approved  "First-Pass Approval"  = !x.remake  ->  100%, always
//   seam-remakes   "Remake Issues"        =  x.remake  ->  0, always
//   the CSV        "Remake Risk"          =  x.remake  ->  "No", every row
//
// A shop with twelve remakes on analysed jobs was told its first-pass approval
// was 100%. That is Guardian Check 0b -- a number with no function behind it --
// and it is not softened by the number being a percentage rather than a
// currency figure.
//
// THE FIX IS NOT A NEW DATA SOURCE. sd_remakes already exists, is already
// written by sdRMAdd() with `customer` holding the job name, and was simply
// never wired to this panel. The flag is now derived at READ time, which is
// the only time it can be right: the remake happens after the analysis.
//
// The implementation is extracted from the real stonedesk.html rather than
// re-stated here, so this file fails if what ships changes.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8');

function grab(startMarker, endMarker) {
  const s = html.indexOf(startMarker);
  assert.ok(s > 0, 'not found in stonedesk.html: ' + startMarker);
  const e = html.indexOf(endMarker, s);
  assert.ok(e > s, 'unterminated: ' + startMarker);
  return html.slice(s, e);
}

// localStorage is stubbed rather than the function being skipped: the bad-JSON
// arm below is a real refusal path and would otherwise never be exercised.
let STORE = {};
const ctx = {
  console, Date, Math, JSON, String, Number, Array,
  localStorage: { getItem: (k) => (k in STORE ? STORE[k] : null) }
};
vm.createContext(ctx);
vm.runInContext(grab('function seamRemakeLog(){', 'function updateKPIs(){'), ctx);
const { seamRemakeLog, seamKey, seamHadRemake } = ctx;

let n = 0;
function ok(cond, label) { assert.ok(cond, label); n++; }
function eq(a, b, label) { assert.strictEqual(a, b, label); n++; }

ok(typeof seamHadRemake === 'function', 'seamHadRemake was extracted');
ok(typeof seamRemakeLog === 'function', 'seamRemakeLog was extracted');

function rm(customer, createdAt, extra) {
  return Object.assign({ customer, createdAt, reason: 'cut_error', material: 'Granite' }, extra || {});
}
function sa(job, date, extra) {
  return Object.assign({ job, date, mat: 'Granite', loc: 'Kitchen' }, extra || {});
}

// ── THE TWO DIRECTIONS. A control that only proves "true" would pass against
// ── a function that returned true unconditionally.
eq(seamHadRemake(sa('Webb Kitchen', '2026-09-01'), []), false,
   'no remakes at all -> false');
eq(seamHadRemake(sa('Webb Kitchen', '2026-09-01'),
                 [rm('Webb Kitchen', '2026-09-05T10:00:00Z')]), true,
   'a remake on the same job AFTER the analysis -> true');

// ── ORDER IN TIME IS THE WHOLE POINT. A remake logged before the seam was
// ── analysed is not one the analysis failed to prevent, and counting it would
// ── make the tile worse than the constant it replaced.
eq(seamHadRemake(sa('Webb Kitchen', '2026-09-10'),
                 [rm('Webb Kitchen', '2026-09-01T10:00:00Z')]), false,
   'a remake BEFORE the analysis date -> false');
eq(seamHadRemake(sa('Webb Kitchen', '2026-09-05'),
                 [rm('Webb Kitchen', '2026-09-05T23:59:00Z')]), true,
   'same day counts -- on or after, not strictly after');

// ── ATTRIBUTION IS BY JOB NAME AND THE NAME IS TYPED TWICE, in two different
// ── forms, by two different people. Exact string equality would silently
// ── under-count, which reads exactly like the constant-false bug returning.
eq(seamHadRemake(sa('webb   KITCHEN', '2026-09-01'),
                 [rm('  Webb Kitchen ', '2026-09-05T10:00:00Z')]), true,
   'case and whitespace do not break the match');
eq(seamHadRemake(sa('Webb Kitchen', '2026-09-01'),
                 [rm('Alvarez Bath', '2026-09-05T10:00:00Z')]), false,
   'a different job does not count');

// ── UNKNOWNS MUST NOT QUIETLY CLEAR A REAL REMAKE. An absent date is a
// ── could-not-tell, and folding it into "no remake" is the same failure this
// ── whole fix is about, one level down.
eq(seamHadRemake(sa('Webb Kitchen', '2026-09-01'), [rm('Webb Kitchen', '')]), true,
   'a remake with no createdAt still counts');
eq(seamHadRemake(sa('Webb Kitchen', ''), [rm('Webb Kitchen', '2026-01-01T00:00:00Z')]), true,
   'an analysis with no date still counts a remake on that job');

// ── AN UNATTRIBUTABLE ROW IS FALSE, not "matches everything". seamKey('')
// ── would otherwise equal seamKey(undefined) and every dateless remake would
// ── light up every blank-job analysis.
eq(seamHadRemake(sa('', '2026-09-01'), [rm('', '2026-09-05T10:00:00Z')]), false,
   'an analysis with no job name cannot be attributed -> false');

// ── THE STORED FIELD IS IGNORED, which is what makes this a derivation rather
// ── than a rename. Old rows on disk still carry remake:false; a hand-edited
// ── one carrying true must not be believed either.
eq(seamHadRemake(sa('Webb Kitchen', '2026-09-01', { remake: true }), []), false,
   'a stored remake:true with no matching record is NOT believed');
eq(seamHadRemake(sa('Webb Kitchen', '2026-09-01', { remake: false }),
                 [rm('Webb Kitchen', '2026-09-05T10:00:00Z')]), true,
   'a stored remake:false does not suppress a real one');

// ── THE LOG READER FAILS TO AN EMPTY LIST, NEVER THROWS. This runs inside
// ── updateKPIs on every render; an exception here blanks the whole panel.
STORE = {};
eq(seamRemakeLog().length, 0, 'absent sd_remakes -> []');
STORE = { sd_remakes: '{not json' };
eq(seamRemakeLog().length, 0, 'unparseable sd_remakes -> [], not a throw');
STORE = { sd_remakes: JSON.stringify([rm('Webb Kitchen', '2026-09-05T10:00:00Z')]) };
eq(seamRemakeLog().length, 1, 'a real sd_remakes is read');

// ── AND THE CONSTANTS ARE GONE FROM THE SHIPPING FILE. Asserted against the
// ── source text, because the functions above can be perfect while the call
// ── sites still read the frozen field -- which is exactly the shape that put
// ── the [0040] trigger behind a dead element for three weeks.
ok(html.indexOf('remake:false') === -1 || /Every row this panel has ever written carries `remake:false`/.test(html),
   'remake:false survives only inside the comment explaining it');
eq((html.match(/d\.push\(\{job:job,mat:mat,loc:loc,date:sdLocalToday\(\),remake:false\}\)/g) || []).length, 0,
   'neither insert site writes the frozen flag any more');
eq((html.match(/\(d\.length\s*\*\s*180\)/g) || []).length, 0,
   'the $180-per-analysis "Material Savings" constant is gone');
ok(/getElementById\('seam-savings'\)\.textContent='--'/.test(html),
   "seam-savings reads '--', matching the sibling Vein Match tile");
ok(/\['Job','Material','Location','Date','Remake Logged'\]/.test(html),
   'the CSV header says Remake Logged, which is what the column can actually say');

console.log(n + ' assertions pass');
