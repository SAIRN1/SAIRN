// api/_lib/dnt-location.test.js
// Plain node:assert, matching api/'s zero-npm-dependency convention.
// Run: node api/_lib/dnt-location.test.js

const assert = require('assert');
const loc = require('./dnt-location');

let passed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

console.log('api/_lib/dnt-location.js');

// ── stampLocation ────────────────────────────────────────────────────
test('a payload with no location_id gets the implicit default, not a blank', () => {
  const out = loc.stampLocation({ id: 'P-1', name: 'Jane' });
  assert.strictEqual(out.location_id, loc.DEFAULT_LOCATION_ID);
});

test('an existing single-location payload is otherwise untouched', () => {
  const src = { id: 'P-1', name: 'Jane', email: 'j@example.test' };
  const out = loc.stampLocation(src);
  assert.strictEqual(out.id, 'P-1');
  assert.strictEqual(out.name, 'Jane');
  assert.strictEqual(out.email, 'j@example.test');
});

test('the caller payload is not mutated -- stamping returns a copy', () => {
  const src = { id: 'P-1' };
  loc.stampLocation(src);
  assert.strictEqual(src.location_id, undefined, 'the original object must not gain a field');
});

test('a real location_id is preserved exactly', () => {
  assert.strictEqual(loc.stampLocation({ id: 'A-1', location_id: 'LOC-WESTSIDE' }).location_id, 'LOC-WESTSIDE');
});

test('whitespace around a location_id is trimmed, not stored', () => {
  assert.strictEqual(loc.stampLocation({ id: 'A-1', location_id: '  LOC-EAST  ' }).location_id, 'LOC-EAST');
});

test('blank, non-string and over-length location_ids fall back rather than reject', () => {
  // Falling back matters: rejecting would break every existing client that
  // has never heard of locations, and an unwritten row loses attribution
  // permanently -- the exact failure this module exists to prevent.
  assert.strictEqual(loc.stampLocation({ location_id: '   ' }).location_id, loc.DEFAULT_LOCATION_ID);
  assert.strictEqual(loc.stampLocation({ location_id: 42 }).location_id, loc.DEFAULT_LOCATION_ID);
  assert.strictEqual(loc.stampLocation({ location_id: null }).location_id, loc.DEFAULT_LOCATION_ID);
  assert.strictEqual(loc.stampLocation({ location_id: 'x'.repeat(65) }).location_id, loc.DEFAULT_LOCATION_ID);
});

test('a null or undefined payload still yields an attributable row', () => {
  assert.strictEqual(loc.stampLocation(null).location_id, loc.DEFAULT_LOCATION_ID);
  assert.strictEqual(loc.stampLocation(undefined).location_id, loc.DEFAULT_LOCATION_ID);
});

// ── validateLocations ────────────────────────────────────────────────
test('absent locations is valid -- a single-location practice never sets it', () => {
  assert.strictEqual(loc.validateLocations(undefined).ok, true);
  assert.strictEqual(loc.validateLocations(null).ok, true);
  assert.strictEqual(loc.validateLocations([]).ok, true);
});

test('a well-formed registry passes', () => {
  const r = loc.validateLocations([
    { id: 'LOC-WESTSIDE', name: 'Westside Dental' },
    { id: 'LOC-EAST', name: 'East Office' }
  ]);
  assert.strictEqual(r.ok, true);
});

test('a duplicate location id is REFUSED -- it would split one office history in two', () => {
  const r = loc.validateLocations([
    { id: 'LOC-A', name: 'First' },
    { id: 'LOC-A', name: 'Second' }
  ]);
  assert.strictEqual(r.ok, false);
  assert.ok(/duplicate/i.test(r.message), 'the message must name the real problem');
});

test('a non-array, a non-object entry, and a missing id or name are all refused', () => {
  assert.strictEqual(loc.validateLocations('LOC-A').ok, false);
  assert.strictEqual(loc.validateLocations(['LOC-A']).ok, false);
  assert.strictEqual(loc.validateLocations([{ name: 'No id' }]).ok, false);
  assert.strictEqual(loc.validateLocations([{ id: 'LOC-A' }]).ok, false);
  assert.strictEqual(loc.validateLocations([{ id: '  ', name: 'Blank id' }]).ok, false);
});

test('over-length ids/names and too many entries are refused', () => {
  assert.strictEqual(loc.validateLocations([{ id: 'x'.repeat(65), name: 'Too long id' }]).ok, false);
  assert.strictEqual(loc.validateLocations([{ id: 'LOC-A', name: 'y'.repeat(129) }]).ok, false);
  const many = [];
  for (let i = 0; i <= loc.MAX_LOCATIONS; i++) many.push({ id: 'LOC-' + i, name: 'Office ' + i });
  assert.strictEqual(loc.validateLocations(many).ok, false);
});

console.log(passed + ' passed' + (process.exitCode ? ', with failures above' : ''));
