// tests/sairndental_settings_patch.js
//
// Run:  node tests/sairndental_settings_patch.js
//
// The CLIENT half of the dnt_settings PATCH change. The server half -- that a
// patch merges onto the current row, that two workstations saving different
// keys in one round trip both survive -- is proven end to end against the real
// handler in api/sd-data-dental-settings-patch.test.js. This file proves the
// three panels hold up their end: each sends ONLY ITS OWN KEYS, writes to the
// server before localStorage, and caches the SERVER'S merged record rather than
// the patch it sent.
//
// RENAMED FROM tests/sairndental_settings_merge_base.js. That file tested
// dntSettingsMergeBase(), a client-side fresh-read base added hours earlier the
// same day, which the server-side merge SUPERSEDES -- one round trip instead of
// two, and no window at all between the read and the write. The helper is gone
// and so are its tests; that is a supersession, not an abandonment, and it is
// said here rather than left as a deleted file nobody can account for.
//
// Per sairn-code-scrubber item 16 Shape B, every call-site assertion checks the
// OLD mechanism is ABSENT as well as the new one present: asserting that a
// panel calls dntSettingsWrite() would pass with it still sending the whole
// record, which is the exact thing being removed.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'sairndental.html'), 'utf8').replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
const queue = [];
function test(name, fn) { queue.push({ name, fn }); }
function section(t) { queue.push({ section: t }); }

// Brace-balanced extraction, not a fixed window -- item 16 Shape A: a window of
// a file that also contains commentary is how an assertion ends up matching
// prose about the code instead of the code.
function fnBody(name) {
  const at = html.indexOf(name);
  assert.ok(at > 0, 'not found in sairndental.html: ' + name);
  const open = html.indexOf('{', at);
  let depth = 0;
  for (let i = open; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}') { depth--; if (depth === 0) return html.slice(at, i + 1); }
  }
  throw new Error('unbalanced braces after ' + name);
}
const codeOf = (src) => src.split('\n').filter((l) => !l.trim().startsWith('//')).join('\n');

function harness(opts) {
  opts = opts || {};
  const calls = { writes: [], stored: [] };
  const ctx = {
    JSON, Object, Array, String, Promise,
    console: { warn: () => {} },
    DATA_API: 'https://sairn.test/api/sd-data',
    APP_ID: 'sairndental',
    dntHeaders: () => ({ 'Content-Type': 'application/json' }),
    settings: () => JSON.parse(JSON.stringify(opts.local || { id: 'default' })),
    st: (k, v) => { calls.stored.push({ key: k, value: v }); return true; },
    fetch: (url, init) => {
      calls.writes.push(JSON.parse(init.body));
      const r = opts.writeResponse || { status: 200, body: { ok: true, data: { id: 'default', merged: true } } };
      return Promise.resolve({ ok: r.status >= 200 && r.status < 300, status: r.status, json: () => Promise.resolve(r.body) });
    },
    __calls: calls,
  };
  vm.createContext(ctx);
  vm.runInContext(fnBody('async function dntSettingsWrite(') + '\n' + fnBody('function dntSettingsCache('), ctx);
  return ctx;
}

// ═══════════════════════════════════════════════════════════════════════════
section('the shared writer sends the patch and reports refusals');

test('a 200 returns ok AND the merged record the server sent back', async () => {
  const c = harness({});
  const w = await c.dntSettingsWrite({ id: 'default', gfe_npi: '123' });
  assert.strictEqual(w.ok, true);
  assert.strictEqual(w.data.merged, true, 'the server response was discarded -- the caller has nothing to cache');
  assert.strictEqual(c.__calls.writes[0].resource, 'dnt_settings');
  assert.strictEqual(c.__calls.writes[0].payload.gfe_npi, '123');
});

test('409 SLUG_TAKEN comes back as the server\'s own message', async () => {
  const c = harness({ writeResponse: { status: 409, body: { error: { code: 'SLUG_TAKEN', message: 'already in use by another practice' } } } });
  const w = await c.dntSettingsWrite({ id: 'default' });
  assert.strictEqual(w.ok, false);
  assert.match(w.message, /already in use by another practice/);
});

test('503 SETTINGS_READ_UNAVAILABLE is surfaced, not swallowed', async () => {
  // The server refuses when it could not read the row to merge onto. If that
  // came back as a generic failure the user would retry blind.
  const c = harness({ writeResponse: { status: 503, body: { error: { code: 'SETTINGS_READ_UNAVAILABLE', message: 'The current practice settings could not be read, so nothing was saved' } } } });
  const w = await c.dntSettingsWrite({ id: 'default' });
  assert.strictEqual(w.ok, false);
  assert.match(w.message, /could not be read/);
  assert.match(w.message, /Nothing was saved/);
});

test('a thrown fetch is a refusal, not a success', async () => {
  const c = harness({});
  c.fetch = () => { throw new Error('offline'); };
  const w = await c.dntSettingsWrite({ id: 'default' });
  assert.strictEqual(w.ok, false);
  assert.match(w.message, /could not reach the server/i);
});

test('the stale "sync not yet enabled" wording is gone from the writer', () => {
  assert.strictEqual(codeOf(fnBody('async function dntSettingsWrite(')).indexOf('sync not yet enabled'), -1);
});

// ═══════════════════════════════════════════════════════════════════════════
section('the local copy is the SERVER\'s record, never the patch');

test('the server\'s merged record is what gets cached', async () => {
  const c = harness({ local: { id: 'default', timezone: 'America/New_York' } });
  const rec = c.dntSettingsCache({ id: 'default', gfe_npi: '1' }, { id: 'default', merged: true, timezone: 'America/New_York' });
  assert.strictEqual(rec.merged, true);
  assert.strictEqual(c.__calls.stored[0].key, 'dnt_settings_obj');
  assert.strictEqual(c.__calls.stored[0].value.merged, true);
});

test('WITHOUT a server record it merges locally -- it never caches the bare patch', async () => {
  // Caching the patch would leave the device holding a settings object missing
  // every key that panel does not own: the same wipe, from the other direction.
  const c = harness({ local: { id: 'default', timezone: 'America/New_York', appeal_windows: ['X'] } });
  const rec = c.dntSettingsCache({ id: 'default', gfe_npi: '1' }, null);
  assert.strictEqual(rec.timezone, 'America/New_York', 'the local keys were dropped');
  assert.deepStrictEqual(rec.appeal_windows, ['X']);
  assert.strictEqual(rec.gfe_npi, '1');
});

// ═══════════════════════════════════════════════════════════════════════════
section('each panel sends ONLY its own keys');

const PANELS = [
  ['async function saveBookingSettings()', ['booking_slug', 'timezone', 'publicly_bookable_procedure_type_ids', 'practice_name', 'practice_phone', 'practice_address'],
    ['appeal_windows', 'gfe_npi', 'gfe_legal_name', 'gfe_tin', 'gfe_state', 'locations']],
  ['async function dnPersistWindows(', ['appeal_windows'],
    ['booking_slug', 'timezone', 'gfe_npi', 'gfe_legal_name', 'practice_name', 'locations']],
  ['async function saveGfeIdentity()', ['gfe_legal_name', 'gfe_npi', 'gfe_tin', 'gfe_state'],
    ['appeal_windows', 'booking_slug', 'timezone', 'practice_name', 'locations']],
];

for (const [fn, own, foreign] of PANELS) {
  const label = fn.replace('async function ', '').replace(/\(.*/, '');
  test(label + ' builds a patch of its own keys and NOT the whole record', () => {
    const code = codeOf(fnBody(fn));
    assert.ok(/var patch=\{id:'default'/.test(code), 'does not build a patch keyed on id');
    own.forEach((k) => assert.ok(code.indexOf(k) > 0, 'own key missing from the patch: ' + k));
    // THE ONE THAT MATTERS: a foreign key appearing anywhere in this function
    // means it is still carrying a value it does not own, which is what erases
    // another panel's work.
    foreign.forEach((k) => assert.strictEqual(code.indexOf(k), -1,
      label + ' still mentions ' + k + ', a key it does not own -- the whole-record send is back'));
    assert.strictEqual(code.indexOf('Object.assign({},settings()'), -1,
      'still merges onto the local cached copy before sending');
    assert.strictEqual(code.indexOf('dntSettingsMergeBase'), -1,
      'the superseded client-side base read is back -- the server merges now');
  });

  test(label + ' writes to the SERVER before it touches localStorage', () => {
    const code = codeOf(fnBody(fn));
    const write = code.indexOf('dntSettingsWrite(patch)');
    const cache = code.indexOf('dntSettingsCache(patch,w.data)');
    assert.ok(write > 0, 'does not use the shared writer');
    assert.ok(cache > write, 'the local cache is written before the server has taken it');
    const firstCache = code.indexOf('dntSettingsCache(');
    if (firstCache < write) {
      // The only cache allowed before the writer is the no-licence branch,
      // which never reaches the server at all.
      assert.ok(/if\(!dntLicenseKey\(\)\)\{/.test(code.slice(0, firstCache).slice(-40)),
        'an unguarded local write happens before the server call again');
    }
  });
}

test('saveBookingSettings no longer keeps a slug the server REFUSED', () => {
  // It wrote to localStorage before the request and the 409 branch only toasted
  // and returned, so the form and the patient-feedback link preview advertised
  // a booking slug belonging to another practice.
  const code = codeOf(fnBody('async function saveBookingSettings()'));
  const guard = code.indexOf('if(!w.ok)');
  const cache = code.indexOf('dntSettingsCache(patch,w.data)', guard);
  assert.ok(guard > 0 && cache > guard, 'the refusal no longer precedes the local write');
});

test('the collision the tool reports is ACKNOWLEDGED, and for the writers that exist NOW', () => {
  const tool = fs.readFileSync(path.join(__dirname, '..', 'tools', 'key_collision_check.py'), 'utf8');
  assert.match(tool, /'dnt_settings_obj':\s*\(/, 'no acknowledgement entry');
  assert.match(tool, /\{'rec', 'serverSettings'\}/, 'the acknowledged variable pair is not the one reported');
  // The entry's REASON has to describe the code as it is. It named three `rec`
  // writers; there is one now, inside dntSettingsCache().
  assert.ok(tool.indexOf('dntSettingsCache()') > 0,
    'the acknowledgement still describes the three-writer shape that the patch change removed');
});

// ═══════════════════════════════════════════════════════════════════════════
(async () => {
  for (const item of queue) {
    if (item.section) { console.log('--- ' + item.section + ' ---'); continue; }
    try { await item.fn(); console.log('  ok   ' + item.name); pass++; }
    catch (e) { console.log('  FAIL ' + item.name + '\n       ' + e.message); fail++; }
  }
  console.log('\nsairndental_settings_patch: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
