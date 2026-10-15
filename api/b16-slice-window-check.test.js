// api/b16-slice-window-check.test.js
//
// Run:  node api/b16-slice-window-check.test.js
//
// REQUIREMENT: no NEW fixed-width source window may be added to an `api/`
//   test suite. A window of the shape `.slice(V, V + N)` over source text
//   stops containing what it was written to contain the first time anybody
//   adds a comment above the line, and it reports that as a FAILING ARM.
//
// ── THE FALSE RED THIS COMES FROM ─────────────────────────────────────────
// b14 found two false reds by running the suites and READING THE OUTPUT, which
// is not a control. One was an arm asserting a source line inside
// `slice(at, at + 900)` that went red when comments pushed the line past the
// window -- the code was fine, the test was measuring a 900-character box. The
// b15 handoff carried it as open item 1: "a check that flags `slice(x, x + N)`
// over source text in any `*.test.js`, failing-first. It is the mechanical
// half of a two-part finding and the other half is already closed."
//
// ── WHAT IS AND IS NOT FLAGGED, AND WHY THE NARROWING IS NOT A LOOPHOLE ───
// FLAGGED:     `.slice(V, V + N)` where the SAME expression V appears on both
//              sides and N is an integer literal >= 2. That is a fixed-width
//              box anchored at V, and nothing about it tracks the structure it
//              was meant to cover.
// NOT FLAGGED: `.slice(open, i + 1)`, `.slice(m.index, k + 1)`,
//              `.slice(start, end + 1)` -- two DIFFERENT expressions, which is
//              the shape of a window bounded by a scanned structure (a matched
//              brace, a located terminator). That is the CORRECT form and
//              flagging it would push authors away from it.
// NOT FLAGGED: N < 2. `slice(i, i + 1)` is a single character, not a window.
//
// Measured on the real tree rather than assumed: the broad pattern matches 55
// sites and the narrowed one 31, so the narrowing is doing real work and is
// not a rounding error. Both figures are RE-DERIVED by arm S5 on every run
// rather than trusted from this comment -- the first draft of this paragraph
// said 45 from memory and S5 printed 55.
//
// FAILING-FIRST, and driven: a file containing one planted
// `src.slice(anchor, anchor + 750)` was added to api/ and this suite went
// exit 1 on S1 with "32 found, 31 in the baseline". The plant was then
// deleted and the suite returned to exit 0.
// docs/hank-evidence/b16/red_slice_window.log carries the red run.
//
// ── WHAT THIS CHECK DOES NOT DO, SAID PLAINLY ────────────────────────────
// IT DOES NOT FIX THE 31 WINDOWS THAT ALREADY EXIST. They are recorded in
// BASELINE below, by file and by `V+N` token rather than by line number, and
// every one of them is still capable of the exact false red b14 found. A
// reader must not take a green run here as "the fragile windows are gone" --
// it means NO NEW ONE WAS ADDED. Converting the 31 to structure-bounded
// windows is real work across 12 files, it is named in the handoff, and
// pretending this gate covers it would be the more expensive lie.
//
// THE BASELINE IS EXACT IN BOTH DIRECTIONS. A new window fails (exit 1) and a
// baseline entry that has DISAPPEARED also fails -- otherwise the list would
// quietly accumulate entries for windows nobody has written for months, and a
// stale allowlist is how a gate stops testing anything (cross-domain
// discipline 8).
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const fs = require('fs');
const path = require('path');

const API = __dirname;
const ROOT = path.join(__dirname, '..');

let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(l) { pass++; console.log('  ok       ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL     ' + l);
  if (why) console.log('           ' + String(why).slice(0, 2000));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 800));
}
function is(c, l, why) { if (c) ok(l); else bad(l, why); }

// ── THE DETECTOR ─────────────────────────────────────────────────────────
const NARROW = /\.slice\(\s*([A-Za-z_$][A-Za-z0-9_$.]*)\s*,\s*([A-Za-z_$][A-Za-z0-9_$.]*)\s*\+\s*(\d+)\s*\)/g;
const BROAD = /\.slice\([A-Za-z_$][A-Za-z0-9_$.]*\s*,\s*[A-Za-z_$][A-Za-z0-9_$.]*\s*\+\s*\d+\s*\)/g;

function scan(src) {
  const hits = [];
  let m;
  NARROW.lastIndex = 0;
  while ((m = NARROW.exec(src)) !== null) {
    const a = m[1], b = m[2], n = Number(m[3]);
    if (a === b && n >= 2) {
      hits.push({ token: a + '+' + n, line: src.slice(0, m.index).split('\n').length });
    }
  }
  return hits;
}

function walk(dir, out) {
  fs.readdirSync(dir, { withFileTypes: true }).forEach((e) => {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) { if (e.name !== 'node_modules') walk(p, out); return; }
    if (/\.test\.js$/.test(e.name)) out.push(p);
  });
  return out;
}

function inventory() {
  const files = walk(API, []).sort();
  const inv = {};
  files.forEach((f) => {
    const rel = path.relative(ROOT, f).split(path.sep).join('/');
    // THE CHECK DOES NOT FLAG ITSELF. Its own regexes and its BASELINE
    // contain the shape as DATA. Excluded by exact filename rather than by a
    // "looks like a checker" heuristic, so nothing else can slip in behind it.
    if (rel === 'api/b16-slice-window-check.test.js') return;
    const hits = scan(fs.readFileSync(f, 'utf8'));
    if (hits.length) inv[rel] = hits.map((h) => h.token).sort();
  });
  return inv;
}

// ── THE BASELINE. 31 windows in 12 files, measured 2026-10-15. ───────────
// Keyed by `V+N` token and NOT by line number, deliberately: a line-keyed
// allowlist is itself a fixed-width window and would go red every time
// anything above it moved, which is the defect wearing the gate's clothes.
const BASELINE = {
  'api/_lib/dental-gfe.test.js': ['i+1600', 'i+1600', 'i+1600'],
  'api/_lib/employee-lifecycle-wiring.test.js':
    ['at+1400', 'at+1400', 'at+400', 'at+600', 'at+900', 'at+900', 'at+900'],
  'api/alf-mar-every-path-tenant-scoped.test.js': ['at+900', 'i+600'],
  'api/hydrate-gate-coupling.test.js': ['def.index+6000', 'def.index+6000'],
  'api/lifecycle-audit-event-coverage.test.js': ['m.index+8000'],
  'api/role-vocabulary-agreement.test.js': ['m.index+8000'],
  'api/sairndental/public-book-guardian.test.js':
    ['i+1400', 'i+4000', 'i+700', 'i+900'],
  'api/sd-data-memory-app-scope.test.js': ['at+1400', 'at+200', 'at+300', 'at+900'],
  'api/sd-data-numeric-guards.test.js': ['trustIdx+2600'],
  'api/sd-data-scp-session-gate.test.js': ['at+400'],
  'api/sd-data-unconfirmed-write-sweep.test.js': ['idx+30'],
  'api/sf-session-gate.test.js': ['at+1600', 'at+2600', 'i+1200'],
  'api/sv-witness.test.js': ['at+2600']
};
const BASELINE_COUNT = Object.keys(BASELINE)
  .reduce((s, k) => s + BASELINE[k].length, 0);

function main() {
  console.log('api/b16-slice-window-check.test.js');
  console.log('  no NEW fixed-width source window in an api/ test suite');

  const inv = inventory();
  const found = Object.keys(inv).reduce((s, k) => s + inv[k].length, 0);

  // ── S1: NOTHING NEW ────────────────────────────────────────────────────
  {
    const added = [];
    Object.keys(inv).sort().forEach((f) => {
      const base = (BASELINE[f] || []).slice();
      inv[f].forEach((t) => {
        const at = base.indexOf(t);
        if (at === -1) added.push(f + ' :: ' + t); else base.splice(at, 1);
      });
    });
    is(added.length === 0,
       'S1. NO NEW fixed-width source window. ' + found + ' found, '
     + BASELINE_COUNT + ' in the baseline',
       'NEW fixed-width windows -- rewrite each as a window bounded by the '
     + 'structure it is meant to cover (scan to the matching brace or the '
     + 'terminator) rather than a character count:\n           '
     + added.join('\n           '));
  }

  // ── S2: AND NOTHING STALE. The allowlist cannot outlive its entries. ──
  {
    const gone = [];
    Object.keys(BASELINE).sort().forEach((f) => {
      const live = (inv[f] || []).slice();
      BASELINE[f].forEach((t) => {
        const at = live.indexOf(t);
        if (at === -1) gone.push(f + ' :: ' + t); else live.splice(at, 1);
      });
    });
    is(gone.length === 0,
       'S2. NO STALE baseline entry -- every one of the ' + BASELINE_COUNT
     + ' recorded windows is still really there. A tolerated-list that '
     + 'outlives its entries is how a gate stops testing anything',
       'baseline entries that no longer exist (delete them from BASELINE, '
     + 'which is the good news):\n           ' + gone.join('\n           '));
  }

  // ── S3: THE DETECTOR FINDS A PLANTED ONE ──────────────────────────────
  // Without this arm an empty or broken regex passes S1 and S2 forever. The
  // plant is in a STRING, not on disk: nothing is written, so there is no
  // mutant to leave behind.
  {
    const planted = 'const s = src.slice(anchor, anchor + 750);';
    const hits = scan(planted);
    is(hits.length === 1 && hits[0].token === 'anchor+750',
       'S3. the detector flags a PLANTED window (`slice(anchor, anchor + '
     + '750)`). Without this arm a broken regex passes S1 and S2 forever',
       'hits=' + JSON.stringify(hits));
  }

  // ── S4: AND IT DOES NOT FLAG THE CORRECT SHAPE ────────────────────────
  // The structure-bounded forms really in the tree. If this arm went red the
  // check would be pushing authors AWAY from the right answer, which is worse
  // than not having it.
  {
    const good = [
      'const body = src.slice(open, i + 1);',
      'const block = src.slice(m.index, k + 1);',
      'const seg = src.slice(start, end + 1);',
      'const ch = src.slice(i, i + 1);'
    ].join('\n');
    const hits = scan(good);
    is(hits.length === 0,
       'S4. the detector does NOT flag a structure-bounded window '
     + '(slice(open, i+1), slice(m.index, k+1), slice(start, end+1)) or a '
     + 'single-character read. Flagging those would push authors off the '
     + 'correct form',
       'false positives=' + JSON.stringify(hits));
  }

  // ── S5: THE NARROWING IS DOING REAL WORK, measured ────────────────────
  {
    let broad = 0;
    walk(API, []).forEach((f) => {
      const rel = path.relative(ROOT, f).split(path.sep).join('/');
      if (rel === 'api/b16-slice-window-check.test.js') return;
      const src = fs.readFileSync(f, 'utf8');
      BROAD.lastIndex = 0;
      broad += (src.match(BROAD) || []).length;
    });
    is(broad > found,
       'S5. the narrowed pattern matches ' + found + ' sites where the broad '
     + 'one matches ' + broad + ', so excluding two-different-expressions '
     + 'windows is a real distinction and not a rounding error',
       'broad=' + broad + ' narrow=' + found);
  }

  // ── S6: THE THING THIS DOES NOT DO, ASSERTED SO IT CANNOT BE FORGOTTEN
  // A green run above means "nothing new". It does NOT mean the 31 recorded
  // windows are safe -- every one can still produce b14's false red. This arm
  // fails if the baseline ever reaches zero WITHOUT this note being revisited,
  // which is the only state in which the claim would change.
  is(BASELINE_COUNT > 0,
     'S6. ' + BASELINE_COUNT + ' fixed-width windows are TOLERATED, not '
   + 'fixed. A green run here means NO NEW ONE WAS ADDED and nothing more; '
   + 'all ' + BASELINE_COUNT + ' can still report a false red when a comment '
   + 'pushes a line past the box. Converting them is named in the handoff',
     'the baseline is empty -- if the 31 really are gone, delete this arm and '
   + 'say so out loud rather than leaving a note that no longer describes '
   + 'anything');

  console.log('');
  console.log('  passed ' + pass + '  failed ' + fail + '  unproven ' + unproven);
  if (fail) console.log('  FAILING ARMS: ' + failed.join(' '));
  if (unproven) console.log('  UNPROVEN ARMS: ' + notProved.join(' '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
}

main();
