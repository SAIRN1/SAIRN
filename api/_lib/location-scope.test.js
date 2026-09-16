// api/_lib/location-scope.test.js
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
