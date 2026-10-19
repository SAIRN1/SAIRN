// api/_lib/location-scope.test.js
// REQUIREMENT: one module owns which location a row happened at, so no app reimplements
//   location scoping and reaches a different answer about the same row
//
// ---------------------------------------------------------------------------
// The shared location stamp, and the arms that stop it being re-forked.
//
// THE DEFECT THIS MODULE CLOSED WAS DUPLICATION, so the arms that matter most
// are not about stampLocation's behaviour -- both copies already behaved
// correctly for two weeks. They are about the copies STAYING gone. Section C
// asserts that exactly one module defines the constant and that both former
// owners now delegate, because the failure mode here is not a wrong answer, it
// is a third copy appearing and nothing noticing until the three disagree.
//
// That is the shape item 94 recorded on `isDate`: fourteen definitions, all
// byte-identical, and ALL WRONG THE SAME WAY -- which is only discoverable once
// somebody counts them.

'use strict';

const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const L = require('./location-scope');
const dnt = require('./dnt-location');
const rf = require('./roofing-locations');

const LIB = __dirname;

test('A. the stamp, every way a caller can get it wrong', () => {
  assert.strictEqual(L.stampLocation({}).location_id, L.DEFAULT_LOCATION_ID);
  assert.strictEqual(L.stampLocation().location_id, L.DEFAULT_LOCATION_ID);
  assert.strictEqual(L.stampLocation(null).location_id, L.DEFAULT_LOCATION_ID);
  assert.strictEqual(L.stampLocation({ location_id: '' }).location_id, L.DEFAULT_LOCATION_ID);
  assert.strictEqual(L.stampLocation({ location_id: '   ' }).location_id, L.DEFAULT_LOCATION_ID);
  assert.strictEqual(L.stampLocation({ location_id: 12345 }).location_id, L.DEFAULT_LOCATION_ID);
  assert.strictEqual(L.stampLocation({ location_id: {} }).location_id, L.DEFAULT_LOCATION_ID);
  assert.strictEqual(
    L.stampLocation({ location_id: 'x'.repeat(L.MAX_LOCATION_ID_LEN + 1) }).location_id,
    L.DEFAULT_LOCATION_ID,
    'over-length falls back rather than truncating -- a truncated id would ' +
    'silently attribute a row to a DIFFERENT location');
  assert.strictEqual(
    L.stampLocation({ location_id: 'x'.repeat(L.MAX_LOCATION_ID_LEN) }).location_id,
    'x'.repeat(L.MAX_LOCATION_ID_LEN), 'the boundary length itself is accepted');
  assert.strictEqual(L.stampLocation({ location_id: '  YARD-2  ' }).location_id, 'YARD-2');
});

test('B. it copies rather than mutating -- a stamper that edited its input ' +
     'would change a caller\'s object under it', () => {
  const src = { id: 'J-1', location_id: 'YARD-2' };
  const out = L.stampLocation(src);
  assert.notStrictEqual(out, src);
  out.location_id = 'CHANGED';
  assert.strictEqual(src.location_id, 'YARD-2');
  assert.strictEqual(L.stampLocation({ a: 1, b: 2 }).a, 1, 'other fields survive');
});

test('C. THE CONSOLIDATION HOLDS -- exactly one module defines the constant', () => {
  const owners = fs.readdirSync(LIB)
    .filter((f) => f.endsWith('.js') && !f.endsWith('.test.js'))
    .filter((f) => /DEFAULT_LOCATION_ID\s*=\s*'LOC-DEFAULT'/
      .test(fs.readFileSync(path.join(LIB, f), 'utf8')));
  assert.deepStrictEqual(owners, ['location-scope.js'],
    'the literal is defined in more than one module again -- that is how this ' +
    'defect came back, and the two former copies were byte-identical for two ' +
    'weeks before anybody counted them');
});

test('...and both former owners take the constant from here', () => {
  for (const f of ['dnt-location.js', 'roofing-locations.js']) {
    const src = fs.readFileSync(path.join(LIB, f), 'utf8');
    assert.ok(/require\(['"]\.\/location-scope['"]\)/.test(src),
      f + ' no longer requires the shared module');
    assert.ok(/DEFAULT_LOCATION_ID\s*=\s*locationScope\.DEFAULT_LOCATION_ID/.test(src),
      f + ' has stopped taking the constant from the shared module');
  }
});

// ── THE STAMP IS DUPLICATED ON PURPOSE AND THIS IS WHAT PAYS FOR IT ─────────
// The first version of this migration moved stampLocation() into the shared
// module too. tools/sairn_seam_check.py then reported COULD NOT TELL on
// api/sairndental/public-book.js -> dnt-location.js -- "makes no direct
// `payload.field` reads" -- because its model reads an engine's dependencies
// as payload accesses in the engine's OWN body, and a delegating body has
// none. Measured both ways: 82 clean / 0 could-not-tell before, 81 / 1 after.
//
// TRADING A VERIFIED SEAM FOR FOUR DEDUPLICATED LINES IS THE WRONG DIRECTION,
// so the logic stayed and the constant moved. What makes that safe rather than
// merely accepted is THIS arm: three implementations, one table of cases, and
// any divergence goes red here.
test('...and all three stamps agree on every case, which is what makes the ' +
     'duplication safe rather than merely accepted', () => {
  const cases = [undefined, null, {}, { location_id: '' }, { location_id: '  ' },
                 { location_id: 12345 }, { location_id: {} },
                 { location_id: 'YARD-2' }, { location_id: ' YARD-2 ' },
                 { location_id: 'x'.repeat(65) },
                 { location_id: 'x'.repeat(64) }];
  for (const c of cases) {
    const want = L.stampLocation(c).location_id;
    assert.strictEqual(dnt.stampLocation(c).location_id, want,
      'dnt-location diverged on ' + JSON.stringify(c));
    assert.strictEqual(rf.stampLocation(c).location_id, want,
      'roofing-locations diverged on ' + JSON.stringify(c));
  }
  assert.strictEqual(dnt.DEFAULT_LOCATION_ID, L.DEFAULT_LOCATION_ID);
  assert.strictEqual(rf.DEFAULT_LOCATION_ID, L.DEFAULT_LOCATION_ID);
});

test('D. the boundary is asserted, not just documented -- the roll-ups are ' +
     'NOT unified and must not be', () => {
  // dnt-rollup buckets per LOCATION; roofing-consolidation buckets per legal
  // ENTITY with location->entity as a mapping. Two axes versus one. If a
  // future edit moved either into the shared module this arm goes red before
  // dental acquires an entity concept it does not have.
  const shared = fs.readFileSync(path.join(LIB, 'location-scope.js'), 'utf8');
  for (const word of ['entity', 'bucket', 'rollup', 'roll-up', 'consolidat']) {
    assert.ok(!new RegExp('function\\s+\\w*' + word, 'i').test(shared),
      'location-scope.js has grown a ' + word + ' function; the two roll-ups ' +
      'are different computations and sharing them flattens one of them');
  }
  assert.deepStrictEqual(Object.keys(module.require('./location-scope')).sort(),
    ['DEFAULT_LOCATION_ID', 'MAX_LOCATION_ID_LEN', 'isDefaultLocation',
     'stampLocation'],
    'the shared module grew an export -- adding one is a decision about which ' +
    'app\'s model wins, not a refactor');
});

test('E. isDefaultLocation, because a UI hardcoding the sentinel is where the ' +
     'constant drifts next', () => {
  assert.strictEqual(L.isDefaultLocation('LOC-DEFAULT'), true);
  assert.strictEqual(L.isDefaultLocation('  LOC-DEFAULT  '), true);
  assert.strictEqual(L.isDefaultLocation('YARD-2'), false);
  assert.strictEqual(L.isDefaultLocation(''), false);
  assert.strictEqual(L.isDefaultLocation(null), false);
  assert.strictEqual(L.isDefaultLocation(undefined), false);
  assert.strictEqual(L.isDefaultLocation(12345), false);
});

// ── F. ARM E's STATED REASON IS NOW CHECKED, NOT MERELY WRITTEN
//    (2026-10-19, cody b24, Michael's decision) ─────────────────────────────
// THE CONCEPT: the sentinel is defined in exactly one module and NO app file's
// EXECUTABLE code spells it -- so arm E's own reason, "a UI hardcoding the
// sentinel is where the constant drifts next", is a property this suite
// verifies rather than a sentence it carries.
//
// WHY THIS ARM EXISTS. Arm E passed from the day it was written and proved the
// function WORKS, not that anything USES it. Measured in cody b22:
// sairnroofing.html still asked the question inline TWICE and COULD NOT STOP,
// because this module is CommonJS and that app is a single HTML file with no
// loader and no build step -- there was no path from the UI to the function.
// An arm whose stated purpose names a UI, and which checks no UI, is the shape
// cody b23 repaired six of across three suites.
//
// Michael's decision of the two options cody b23 routed: SERVE THE ANSWER. The
// rf_locations read branch stamps `is_default` per row with isDefaultLocation(),
// and the client reads it off the row. So this arm is the one that would have
// caught the gap, and it is also the one that goes red if a future session
// re-types the literal into a browser file.
//
// COMMENT-STRIPPED, OR IT WOULD FAIL ON THE NOTE EXPLAINING THE FIX. Both app
// files now carry a comment quoting `id==='LOC-DEFAULT'` to record what was
// removed, and an assertion that counted raw occurrences would flag the very
// documentation of its own repair -- a defect this repo has paid for by name.
test('F. no APP file spells the sentinel in executable code -- arm E\'s reason, ' +
     'checked instead of asserted in prose', () => {
  const fs = require('fs');
  const path = require('path');
  const repo = path.join(__dirname, '..', '..');
  // Declared app files rather than a glob: a glob that silently matched
  // nothing would make this arm vacuous, and the two that mattered are named.
  const apps = ['sairnroofing.html', 'sairndental.html'];
  const strip = (s) => s
    .replace(/<!--[\s\S]*?-->/g, ' ')
    .replace(/\/\*[\s\S]*?\*\//g, ' ')
    .replace(/\/\/[^\n]*/g, ' ');
  let checked = 0;
  apps.forEach((rel) => {
    const p = path.join(repo, rel);
    // PRECONDITION, a third state: a missing app file is COULD NOT CHECK and
    // must not read as clean. It is asserted, not skipped.
    assert.ok(fs.existsSync(p), rel + ' is absent, so this arm checked '
      + 'nothing about it. That is a third state and not a pass -- re-point '
      + 'the list rather than letting it shrink silently');
    const code = strip(fs.readFileSync(p, 'utf8'));
    const hits = (code.match(/LOC-DEFAULT/g) || []).length;
    assert.strictEqual(hits, 0, rel + ' spells the default-location sentinel '
      + hits + ' time(s) in EXECUTABLE code. That constant is owned by '
      + 'api/_lib/location-scope.js and a browser file cannot reach it, so the '
      + 'answer has to come from the server: rf_locations read stamps '
      + '`is_default` per row and the response carries `default_location_id` '
      + 'for an id with no row of its own. Read those instead of re-typing the '
      + 'string');
    checked += 1;
  });
  // And the arm cannot pass by having examined nothing.
  assert.strictEqual(checked, apps.length,
    'expected to examine ' + apps.length + ' app file(s), examined ' + checked);
});
