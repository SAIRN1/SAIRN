// tests/strip_consolidation_pinning.test.js
//
// Run:  node tests/strip_consolidation_pinning.test.js
//
// A PINNING TEST FOR THE COMMENT-STRIPPER CONSOLIDATION (b8 item 2).
//
// Over batches b5-b8, 29 private comment-strippers across 20 files were
// replaced with calls into tests/lib/strip_comments.js. Every one of those
// suites was driven before and after and none changed verdict -- which is good
// evidence and not the same thing as a pin. "All the suites still pass" cannot
// distinguish a correct swap from a swap whose difference the suites happen not
// to assert on, and the next person to touch a call site has nothing to run.
//
// SO THIS FILE PINS THE DIFFERENCE ITSELF, in two directions:
//
//   A. THE NAIVE STRIPPER DESTROYS CODE AND THE SHARED ONE DOES NOT. Each arm
//      states an input where `/\/\/[^\n]*/g` removes something that is not a
//      comment, and asserts BOTH that the naive version loses it and that
//      stripJs keeps it. The first half is what makes the arm able to fail: if
//      somebody reverts a call site to the private regex, the behaviour this
//      file pins goes with it.
//
//   B. THE ANCHORS THE REAL SUITES MATCH ON SURVIVE. The consolidation is only
//      safe if the text each suite asserts about is still present after the
//      shared strip. Those anchors are read from the real subjects on disk, so
//      an app or endpoint that moves takes this file red rather than leaving a
//      stale claim behind.
//
// WHAT THIS DOES NOT CLAIM. Not that stripJs is correct in general -- its own
// suite does that, 27 arms in tests/lib/strip_comments.test.js. Not that the
// swap is behaviour-identical: IT IS NOT, deliberately, and direction A is the
// difference. It pins that the difference only ever goes the safe way: the
// shared stripper under-strips rather than over-strips, so it can leave a
// comment in and never remove code.

'use strict';
const fs = require('fs');
const path = require('path');
const { stripJs, stripComments } = require('./lib/strip_comments.js');

const ROOT = path.join(__dirname, '..');
let pass = 0, fail = 0;
function ok(name, cond, detail) {
  if (cond) { pass++; console.log('  ok   ' + name); return; }
  fail++;
  console.log('  FAIL ' + name + (detail ? '\n       ' + detail : ''));
}
function section(t) { console.log('--- ' + t + ' ---'); }

// The exact private implementations that were replaced, kept here as the thing
// being pinned AGAINST. Three shapes appeared across the 20 files.
const naiveLine = (s) => s.replace(/\/\/[^\n]*/g, '');
const naiveBlockLine = (s) => s.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
const naivePerLine = (s) => s.split('\n').map((l) => l.replace(/\/\/.*$/, '')).join('\n');

// ---------------------------------------------------------------------------
section('A. the naive strippers destroy code; the shared one does not');

const URL_CASE = "const ep = 'https://example.invalid/v1';\nauditPinSetup(ctx);\n";
ok('a URL on its own line: naive eats the rest of the line',
   naiveLine(URL_CASE).indexOf('example.invalid') === -1);
ok('...and stripJs keeps the whole string literal',
   stripJs(URL_CASE).indexOf("'https://example.invalid/v1'") !== -1,
   JSON.stringify(stripJs(URL_CASE)));

const SAME_LINE = "fetch('https://api.invalid/x'); auditPinSetup(ctx);\n";
ok('A CALL AFTER A URL ON ONE LINE: naive deletes the call',
   naiveLine(SAME_LINE).indexOf('auditPinSetup') === -1);
ok('...and stripJs keeps it -- this is the case that makes a deleted call '
   + 'look present, or an existing call look deleted',
   stripJs(SAME_LINE).indexOf('auditPinSetup(ctx)') !== -1);

const IN_STRING = "const re = '// not a comment';\nkeep(1);\n";
ok('`//` inside a string: naive eats the rest of the line',
   naiveLine(IN_STRING).indexOf('not a comment') === -1);
ok('...and stripJs leaves the string alone',
   stripJs(IN_STRING).indexOf('// not a comment') !== -1);

const REGEX_SLASHES = 'const r = /a\\/\\/b/;\nkeep(2);\n';
ok('`//` inside a regex literal: stripJs keeps the literal',
   stripJs(REGEX_SLASHES).indexOf('keep(2)') !== -1);

const PER_LINE_CASE = "sql += 'SELECT 1'; // trailing\nsql += 'https://x/y';\n";
ok('the PER-LINE variant eats a URL on a later line of a concatenation',
   naivePerLine(PER_LINE_CASE).indexOf('https://x/y') === -1);
ok('...and stripJs keeps it while still removing the real trailing comment',
   stripJs(PER_LINE_CASE).indexOf('https://x/y') !== -1
   && stripJs(PER_LINE_CASE).indexOf('trailing') === -1);

const BLOCK_RUNAWAY = 'const a = 1; /* open\nconst b = 2;\n*/ const c = 3;\n';
ok('the BLOCK variant and stripJs agree when the comment really closes',
   naiveBlockLine(BLOCK_RUNAWAY).indexOf('const b') === -1
   && stripJs(BLOCK_RUNAWAY).indexOf('const b') === -1);

// THE ONE-DIRECTION PROPERTY, which is the whole safety argument.
section('A2. the shared stripper only ever UNDER-strips');
[URL_CASE, SAME_LINE, IN_STRING, REGEX_SLASHES, PER_LINE_CASE].forEach((s, i) => {
  ok('case ' + (i + 1) + ': stripJs output is at least as long as the naive one',
     stripJs(s).replace(/\s/g, '').length >= naiveLine(s).replace(/\s/g, '').length);
});

// HTML must NOT be handed to stripJs, and the reason is measurable.
section('A3. the HTML/JS distinction is real, not stylistic');
const HTML_CASE = '<input accept="image/*">\n<script>keep(3);</script>\n';
ok('stripComments keeps code after an accept="image/*" attribute',
   stripComments(HTML_CASE).indexOf('keep(3)') !== -1);
ok('...and the naive BLOCK regex would open a comment on that `/*`',
   naiveBlockLine(HTML_CASE + '/* later */').indexOf('keep(3)') === -1);

// ---------------------------------------------------------------------------
section('B. the anchors the real suites assert on survive the shared strip');

// Each entry: the real subject, the entry point its suite now uses, and an
// anchor that suite matches on. Read from disk so a moved subject fails here.
const SUBJECTS = [
  ['api/sd-data.js', stripJs, 'DNT_RESOURCES'],
  ['api/_lib/mech-assets.js', stripJs, 'module.exports'],
  ['api/_lib/deadline-engine.js', stripJs, 'input.'],
  ['api/legal-deadlines.js', stripJs, 'JURISDICTION_LABELS'],
  ['api/greeting.js', stripJs, 'module.exports'],
  ['api/sairndental/public-book.js', stripJs, 'GUARDIAN_REQUIRED'],
  ['sairndental.html', stripComments, 'DNT_SCOPED_CACHES'],
  ['sairncare.html', stripComments, 'ALF_SCOPED_CACHES'],
  ['sairndesign.html', stripComments, 'function '],
  ['stonedesk.html', stripComments, 'function '],
];

SUBJECTS.forEach(([rel, fn, anchor]) => {
  const p = path.join(ROOT, rel);
  if (!fs.existsSync(p)) {
    // FAIL CLOSED: a subject that is gone is not a pass. PR 1.11.
    ok('SUBJECT MISSING: ' + rel + ' -- this arm could not run', false,
       'the file does not exist at this HEAD');
    return;
  }
  const src = fs.readFileSync(p, 'utf8');
  const before = (src.match(new RegExp(anchor.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) || []).length;
  const after = (fn(src).match(new RegExp(anchor.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) || []).length;
  ok(rel + ': `' + anchor + '` present before the strip', before > 0,
     'the anchor is gone from the subject itself -- the arm, not the stripper');
  ok(rel + ': ...and still present after it (' + before + ' -> ' + after + ')',
     after > 0);
});

// ---------------------------------------------------------------------------
section('C. the consolidation is actually in place');
const CALLERS = [
  'api/_lib/courtlistener-rate-limit.test.js',
  'api/_lib/deadline-endpoint-inputs.test.js',
  'api/_lib/deadline-jurisdiction-labels.test.js',
  'api/_lib/dental-gfe.test.js',
  'api/_lib/mech-assets.test.js',
  'api/greeting.test.js',
  'api/sairndental/public-book-guardian.test.js',
  'api/auth-setup-attribution.test.js',
  'api/alf-append-only-read-order.test.js',
  'tests/faults/grd_write_faults.js',
  'tests/faults/alf_rule_read_faults.js',
  'tests/faults/sd_write_faults.js',
  'tests/intake_form_public_surface.js',
  'tests/intake_link_no_credential.js',
  'tests/intake_no_false_success.js',
  'tests/ld_reports_unreadable.js',
  'tests/roofing_claim_gate_single_source.js',
  'tests/sairndesign_po_procurement.js',
  'tests/sb_sync_badge_honesty.js',
  'tests/sd_timesheet_pay_est.js',
  'tests/st_reports_failure.js',
  'tests/stonedesk_admin_storage_kpi.js',
  'tests/sv_storage_guard.js',
];
let wired = 0, privateLeft = [];
CALLERS.forEach((rel) => {
  const p = path.join(ROOT, rel);
  if (!fs.existsSync(p)) { privateLeft.push(rel + ' (MISSING)'); return; }
  const src = fs.readFileSync(p, 'utf8');
  if (src.indexOf('strip_comments.js') !== -1) wired += 1;
  // Its own require line mentions the regex nowhere; a surviving private strip
  // is what this looks for.
  if (/\.replace\(\s*\/\\\/\\\/\[\^\\n\]\*\/g/.test(src)) privateLeft.push(rel);
});
ok('all ' + CALLERS.length + ' consolidated files require the shared library ('
   + wired + ')', wired === CALLERS.length,
   'not wired: ' + CALLERS.filter((r) => {
     const p = path.join(ROOT, r);
     return !fs.existsSync(p) || fs.readFileSync(p, 'utf8').indexOf('strip_comments.js') === -1;
   }).join(', '));
ok('and none of them has a private `//` stripper left',
   privateLeft.length === 0, privateLeft.join(', '));

console.log('\n%d passed, %d failed', pass, fail);
process.exit(fail ? 1 : 0);
