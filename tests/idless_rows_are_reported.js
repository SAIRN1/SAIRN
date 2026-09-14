// tests/idless_rows_are_reported.js
//
// Run:  node tests/idless_rows_are_reported.js
//
// A ROW WITH NO `id` IS NOT BACKED UP, AND FOR MONTHS NOTHING SAID SO.
//
// Every app with a generic collection-sync seam skips rows whose `id` is
// missing or empty -- there is nothing to key an upsert on. That is correct.
// What was not correct is that two of the five apps did it SILENTLY, so a
// collection that had never once reached the server looked exactly like one
// that was being backed up on every save.
//
// It cost StoneDesk six collections. sd_comms, sd_sms_log, sd_veinmatch,
// sd_seamai, sd_email_threats and sd_business_snapshots were all built before
// their sync seam existed and never set an id. Every one of them sat in
// SD_SYNCED -- a list whose name reads as "this is backed up" -- while living
// entirely in one browser's cache. They were found on 2026-09-13 by reading
// writers one at a time, which is not a method that scales to the next one.
//
// ── WHAT THIS FILE PINS, AND WHY IT IS ABOUT FIVE APPS ────────────────────
// SAIRNfreedom and SAIRNvet have counted and warned here for weeks, and
// SAIRNbiz back-fills ids instead so nothing is ever skipped. StoneDesk and
// SAIRNbuild were the two doing NEITHER. This asserts all five are covered --
// by whichever of the two mechanisms each uses -- so the next app to grow a
// sync seam has to choose one rather than defaulting to silence.
//
// ONE LINE PER COLLECTION PER SAVE, not one per row: a 400-row array with no
// ids would otherwise produce 400 identical warnings and get muted, which is
// its own way of saying nothing.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const ROOT = path.join(__dirname, '..');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

function read(app) { return fs.readFileSync(path.join(ROOT, app), 'utf8'); }
function balanced(h, start) {
  let i = h.indexOf('{', start), d = 0;
  for (; i < h.length; i++) {
    if (h[i] === '{') d++;
    else if (h[i] === '}') { d--; if (!d) return h.slice(start, i + 1); }
  }
  throw new Error('unbalanced');
}
// COMMENT-STRIPPED. Every one of these functions now carries a paragraph
// EXPLAINING the skipped-row warning, and several name `skipped` in prose. A
// check that counted those would pass on a file whose code had lost the
// counter entirely -- the comment-quoting trap this repo has a checker for.
function syncBody(app, fnName) {
  const h = read(app);
  const i = h.indexOf('function ' + fnName + '(');
  assert.ok(i > 0, fnName + ' not found in ' + app);
  return balanced(h, i).split('\n')
    .filter(l => !l.trim().startsWith('//') && !l.trim().startsWith('/*') && !l.trim().startsWith('*'))
    .join('\n');
}

// app -> [sync function, mechanism]
//   'report'   counts skipped rows and warns once per collection
//   'backfill' assigns ids before the loop, so nothing is ever skipped
const APPS = [
  ['stonedesk.html', 'sdSyncCollection', 'report'],
  ['sairnbuild.html', 'bldSyncCollection', 'report'],
  ['sairnfreedom.html', 'sfSyncCollection', 'report'],
  ['sairnvet.html', 'svSyncCollection', 'report'],
  ['sairnbiz.html', 'sbSyncCollection', 'backfill']
];

section('every app with a sync seam covers the idless case, one way or the other');

APPS.forEach(([app, fnName, how]) => {
  test(app + ': ' + fnName + ' still skips rows with no id', () => {
    const b = syncBody(app, fnName);
    assert.ok(/===\s*undefined/.test(b) && /===\s*null/.test(b) && /===\s*''/.test(b),
      'the id guard is gone -- an idless row would now be pushed with no key to upsert on');
  });

  if (how === 'report') {
    test(app + ': and COUNTS what it skipped', () => {
      const b = syncBody(app, fnName);
      assert.ok(/skipped\s*\+\+/.test(b) || /skipped\s*=\s*skipped\s*\+\s*1/.test(b),
        'rows are dropped without being counted -- the silence that cost StoneDesk six collections');
    });

    test(app + ': and SAYS so, naming the collection', () => {
      const b = syncBody(app, fnName);
      assert.ok(/console\.warn/.test(b), 'nothing is reported');
      assert.ok(/have no id and were NOT backed up|no "\'\+idField\+\'" and were NOT backed up|were NOT backed up/.test(b),
        'the warning does not say the records were not backed up: ' + (b.match(/console\.warn[^;]{0,160}/) || [''])[0]);
      assert.ok(/\+\s*key\s*\+|"\s*\+\s*key|'\+key\+'/.test(b),
        'the warning does not name which collection, so it cannot be acted on');
    });

    // ONE LINE PER COLLECTION, NOT PER ROW.
    test(app + ': the warning is outside the per-row loop', () => {
      const b = syncBody(app, fnName);
      const warnAt = b.search(/if\s*\(\s*skipped\s*\)/);
      const loopAt = b.indexOf('next.forEach');
      assert.ok(warnAt > loopAt,
        'the skipped-row warning fires inside the loop -- 400 idless rows would '
        + 'produce 400 identical lines and get muted');
    });
  } else {
    test(app + ': back-fills ids instead, so nothing is ever skipped', () => {
      const b = syncBody(app, fnName);
      assert.ok(/EnsureIds\s*\(/.test(b),
        'the back-fill call is gone, and this app has no skipped-row warning to fall back on');
      const ensureAt = b.search(/EnsureIds\s*\(/);
      const loopAt = b.indexOf('next.forEach');
      assert.ok(ensureAt < loopAt, 'the back-fill runs after the loop it exists to feed');
    });
  }
});

// ── THE REGRESSION THIS FILE REALLY GUARDS ────────────────────────────────
// A sixth app growing a *SyncCollection seam must not default to silence. The
// list above is hand-written; this arm derives the real one from the files and
// fails if they disagree, so a new app cannot be added to the platform without
// being added here.
section('a new sync seam cannot appear without a decision');

test('the apps declaring a *SyncCollection seam are exactly the five listed', () => {
  // Tracked files, not whatever is on disk -- see tests/rootpages.js. An
  // untracked .html in a clone turned a sibling suite red on 2026-09-14;
  // this one survived by luck and a differently-named stray would not have.
  const found = require('./rootpages.js').rootPages(ROOT)
    .map(f => [f, (read(f).match(/function\s+(\w*SyncCollection)\s*\(/) || [])[1]])
    .filter(([, fnName]) => fnName);
  const declared = APPS.map(a => a[0] + ':' + a[1]).sort();
  const actual = found.map(([f, n]) => f + ':' + n).sort();
  assert.deepStrictEqual(actual, declared,
    'an app grew or lost a collection-sync seam. If it grew one, decide whether it '
    + 'REPORTS skipped rows or BACK-FILLS their ids, and add it above -- silence is '
    + 'the option that cost StoneDesk six collections');
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
