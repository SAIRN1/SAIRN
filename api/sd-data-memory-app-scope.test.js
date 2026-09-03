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

test('the accepted app list is DERIVED from the registry, not hand-written', () => {
  // A hand-listed copy beside a real one is how api/_resources/index.js's own
  // header records the resource error string drifting from the resource map.
  assert.match(SRC, /const MEMORY_APPS = \{\};/);
  assert.match(SRC, /REGISTRY_MODULES\.forEach/);
  assert.strictEqual(/MEMORY_APPS = \{\s*stonedesk:/.test(SRC), false,
    'the app list is hand-written');
});

test('every registered app is accepted, and `shared` is not an app', () => {
  const { REGISTRY_MODULES } = require('./_resources');
  const apps = REGISTRY_MODULES.map((m) => m && m.app).filter(Boolean);
  assert.ok(apps.indexOf('stonedesk') !== -1);
  assert.ok(apps.indexOf('sairnscape') !== -1, 'sairnscape is not a registered app');
  assert.ok(apps.indexOf('shared') !== -1, 'the fixture assumption changed');
  // ...and the code drops it.
  assert.match(SRC, /m\.app !== 'shared'/);
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

test('api/_lib/sd-store.js is deliberately NOT changed', () => {
  // It is StoneDesk's own agent SDK. Hardcoding stonedesk there is correct, and
  // this asserts the change was scoped rather than sprayed.
  const store = fs.readFileSync(path.join(__dirname, '_lib', 'sd-store.js'), 'utf8');
  assert.match(store, /app_id: 'stonedesk'/);
});
