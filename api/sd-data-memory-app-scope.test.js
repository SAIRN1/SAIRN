// api/sd-data-memory-app-scope.test.js
//
// Run:  node --test api/sd-data-memory-app-scope.test.js
//
// `ai_memories` is one table shared by every app on the platform, and until
// 2026-09-03 the `memory` resource in api/sd-data.js:
//
//   * HARDCODED app_id 'stonedesk' on write, and
//   * filtered on license_hash ALONE on read.
//
// That was harmless while StoneDesk was the only caller. It stops being
// harmless the moment a second app writes: two apps under one licence read each
// other's memories, and every SAIRNscape memory lands stamped 'stonedesk'.
// SAIRNscape became that second caller in this same commit.
//
// The change has to be backward compatible by construction, because StoneDesk
// is live and its client sends NO app_id at all -- stonedesk.html's sdData()
// posts only action/resource/payload. The tests that matter most here are
// therefore the ones proving StoneDesk's behaviour did not move.

'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');

const SRC = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');

function memoryBlock(kind) {
  const at = SRC.indexOf("resource === 'memory' && action === '" + kind + "'");
  assert.ok(at > 0, 'no memory ' + kind + ' handler');
  return SRC.slice(at, at + 1400);
}

test('the accepted app list is DERIVED, not hand-written', () => {
  // A hand-listed copy beside a real one is how api/_resources/index.js's own
  // header records the resource error string drifting from the resource map.
  assert.match(SRC, /const MEMORY_APPS = \{\};/);
  assert.strictEqual(/MEMORY_APPS = \{\s*stonedesk:/.test(SRC), false,
    'the app list is hand-written');
});

test('it is derived from ROLES_BY_APP, which is the set that can pass the gate', () => {
  // THE FIRST VERSION DERIVED IT FROM THE RESOURCE REGISTRY AND WAS WRONG.
  // REGISTRY_MODULES lists apps that own a *_resources file; SAIRNbiz has none,
  // so a legitimate SAIRNbiz memory call was refused with
  // `app_id "sairnbiz" is not a known app`. Caught by the two-device live
  // check, not by these tests.
  //
  // ROLES_BY_APP is the set of apps that have employee SESSIONS, and a session
  // is exactly what this resource requires -- so the set the gate accepts and
  // the set that can pass it are the same set by construction.
  assert.match(SRC, /Object\.keys\(ROLES_BY_APP\)\.forEach/);
  assert.match(SRC, /ROLES_BY_APP \} = require\('\.\/_lib\/auth'\)/);
});

test('every app with a session is accepted -- including the one that was refused', () => {
  const { ROLES_BY_APP } = require('./_lib/auth');
  const apps = Object.keys(ROLES_BY_APP);
  ['stonedesk', 'sairnbiz', 'sairnscape'].forEach((a) => {
    assert.ok(apps.indexOf(a) !== -1, a + ' is not in ROLES_BY_APP');
  });
});

test('stonedesk_sub is EXCLUDED -- subs are not employees', () => {
  // A separate actor class with its own app namespace precisely so a sub token
  // is never mistaken for an employee one. Subs do not get the shop's memory.
  assert.match(SRC, /a !== 'stonedesk_sub'/);
  const { ROLES_BY_APP } = require('./_lib/auth');
  assert.ok(Object.keys(ROLES_BY_APP).indexOf('stonedesk_sub') !== -1,
    'the fixture assumption changed -- stonedesk_sub is no longer a role app');
});

test('the resource registry is NOT the source, and here is why', () => {
  // Kept as a live demonstration rather than a comment: the registry genuinely
  // does not know about SAIRNbiz, so anything derived from it would refuse a
  // real app again.
  const { REGISTRY_MODULES } = require('./_resources');
  const apps = REGISTRY_MODULES.map((m) => m && m.app).filter(Boolean);
  assert.strictEqual(apps.indexOf('sairnbiz'), -1,
    'the resource registry now knows sairnbiz -- the reasoning above needs revisiting');
});

test('an unknown app_id is REFUSED, not silently accepted', () => {
  // Otherwise a typo creates an orphan namespace that writes succeed into and
  // no read ever returns -- a memory feature that looks like it works.
  assert.match(SRC, /UNKNOWN_APP/);
  const at = SRC.indexOf('UNKNOWN_APP');
  const around = SRC.slice(at - 300, at + 200);
  assert.match(around, /res\.status\(400\)/);
});

test('the default is stonedesk, which is what makes this backward compatible', () => {
  assert.match(SRC, /const memApp = String\(\(body && body\.app_id\) \|\| 'stonedesk'\)/);
});

test('stonedesk.html still sends no app_id -- the default is load-bearing', () => {
  // If this ever changes, the default stops being the thing that protects
  // StoneDesk and the compatibility argument has to be re-made.
  const sd = fs.readFileSync(path.join(__dirname, '..', 'stonedesk.html'), 'utf8');
  const at = sd.indexOf('async function sdData(');
  assert.ok(at > 0);
  const body = sd.slice(at, at + 900);
  assert.match(body, /body: JSON\.stringify\(\{ action: action, resource: resource, payload: payload \}\)/,
    'sdData() now sends something else -- re-check the app_id default');
});

test('the READ is filtered by app, not by licence alone', () => {
  const body = memoryBlock('read');
  assert.match(body, /app_id=eq\.' \+ enc\(memApp\)/,
    'the read still returns every app\'s memories for the licence');
  assert.match(body, /license_hash=eq\.' \+ enc\(licHash\)/, 'the licence filter was lost');
});

test('the WRITE stamps the calling app, not a constant', () => {
  const body = memoryBlock('write');
  assert.match(body, /app_id: memApp/);
  assert.strictEqual(/app_id: 'stonedesk'/.test(body), false,
    'the write still hardcodes stonedesk');
});

test('the shop_id lookup follows the same app', () => {
  // It used to look up a stonedesk business_profile no matter who was calling,
  // so a SAIRNscape memory would have been stamped with a StoneDesk shop.
  const body = memoryBlock('write');
  assert.match(body, /business_profiles\?license_hash=eq\.' \+ enc\(licHash\) \+\s*\n?\s*'&app_id=eq\.' \+ enc\(memApp\)/,
    'the profile lookup is still pinned to stonedesk');
});

test('memory stays session-gated for every app', () => {
  // The 2026-09-02 licence-key-exposure audit closed this. A second caller must
  // not be the reason it reopens.
  const at = SRC.indexOf('const SD_SESSION_GATED');
  assert.ok(at > 0);
  const table = SRC.slice(at, at + 700);
  assert.match(table, /'memory':\s*\['read', 'write'\]/);
});

test('the session gate verifies against the CALLING app, not always stonedesk', () => {
  // THE BUG THE UNIT TESTS COULD NOT SEE, and the reason the two-device live
  // check exists. The gate hardcoded expectedApp 'stonedesk', so a SAIRNscape
  // session -- correctly issued, correctly presented -- failed verification and
  // every memory call from a second app returned 403 "sign in first". Ten green
  // assertions above and the feature was dead in production.
  const at = SRC.indexOf('const gateApp =');
  assert.ok(at > 0, 'the gate is back to a hardcoded expected app');
  const line = SRC.slice(at, at + 200);
  assert.match(line, /resource === 'memory'/, 'memory does not follow the caller');
  assert.match(SRC.slice(at, at + 300), /verifySessionToken\(tokenFromRequest\(req\), licHash, gateApp\)/);
});

test('slabs, profile and locations stay pinned to stonedesk', () => {
  // They ARE StoneDesk's resources. Letting them follow a caller-supplied app
  // would turn a fix into a hole.
  const at = SRC.indexOf('const gateApp =');
  const line = SRC.slice(at, SRC.indexOf(';', at));
  assert.match(line, /: 'stonedesk'/, 'the non-memory default is no longer stonedesk');
});

test('the app is validated BEFORE it is used as the expected session app', () => {
  // Order matters: an unvalidated app string reaching verifySessionToken is
  // harmless today but is the kind of ordering that stops being harmless.
  const validate = SRC.indexOf('UNKNOWN_APP');
  const gate = SRC.indexOf('const gateApp =');
  assert.ok(validate > 0 && gate > 0);
  assert.ok(validate < gate, 'the unknown-app refusal runs after the session gate');
});

test('api/_lib/sd-store.js is deliberately NOT changed', () => {
  // It is StoneDesk's own agent SDK. Hardcoding stonedesk there is correct, and
  // this asserts the change was scoped rather than sprayed.
  const store = fs.readFileSync(path.join(__dirname, '_lib', 'sd-store.js'), 'utf8');
  assert.match(store, /app_id: 'stonedesk'/);
});
