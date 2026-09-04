// tests/sairndental_settings_merge_base.js
//
// Run:  node tests/sairndental_settings_merge_base.js
//
// One record, dnt_settings, written by three panels: Booking Settings, the
// Good Faith Estimates practice identity, and the denials panel's appeal
// windows. api/sd-data.js stores `data: payload`, replacing the whole blob, so
// whatever a panel sends IS the row.
//
// Each panel already merged rather than rebuilding, which stopped one panel
// wiping another's fields ON THIS DEVICE. The base was settings() -- this
// device's cached copy -- so it did nothing across devices:
//
//   workstation B saves an appeal window   -> server has windows [X, Y]
//   workstation A, last synced before that, saves the practice identity
//     -> merges onto its stale local copy, sends windows [X]
//     -> Y is erased on the server, and B's next sync loses it
//
// The base is now a fresh SERVER read. These tests drive the two extracted
// helpers rather than reimplementing them, and assert the three call sites
// CONSULT them -- per sairn-code-scrubber item 16 Shape B, asserting a
// mechanism EXISTS is satisfied by a call site that still uses the old one, so
// the old one is asserted ABSENT as well.
//
// WHAT THIS DOES NOT COVER, stated: a true simultaneous race. Two saves inside
// one round trip still end last-write-wins. That residual has its own row in
// docs/SAIRN-OPEN-WORK-INDEX.md; this closes the dominant case, a workstation
// working from an hour-old copy.

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

// Brace-balanced extraction, not a fixed window -- item 16 Shape A: a window
// of a file that also contains commentary is how an assertion ends up matching
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
  const calls = { reads: 0, writes: [] };
  const ctx = {
    JSON, Object, Array, String, Promise,
    console: { warn: () => {} },
    DATA_API: 'https://sairn.test/api/sd-data',
    APP_ID: 'sairndental',
    dntHeaders: () => ({ 'Content-Type': 'application/json' }),
    dntLicenseKey: () => (opts.noLicense ? '' : 'DNT-PINNACLE-2026'),
    settings: () => JSON.parse(JSON.stringify(opts.local || { id: 'default' })),
    sdnData: (action, resource) => {
      calls.reads++;
      if (resource !== 'dnt_settings' || action !== 'read') return Promise.resolve(null);
      return Promise.resolve(opts.serverRead === undefined ? [] : opts.serverRead);
    },
    fetch: (url, init) => {
      calls.writes.push(JSON.parse(init.body));
      const r = opts.writeResponse || { status: 200, body: { ok: true, data: {} } };
      return Promise.resolve({ ok: r.status >= 200 && r.status < 300, status: r.status, json: () => Promise.resolve(r.body) });
    },
    __calls: calls,
  };
  vm.createContext(ctx);
  vm.runInContext(fnBody('async function dntSettingsMergeBase()') + '\n'
                + fnBody('async function dntSettingsWrite('), ctx);
  return ctx;
}

const SERVER_ROW = { id: 'default', booking_slug: 'pinnacle', appeal_windows: ['X', 'Y'], gfe_npi: '' };
const STALE_LOCAL = { id: 'default', booking_slug: 'pinnacle', appeal_windows: ['X'] };

// ═══════════════════════════════════════════════════════════════════════════
section('the merge base is the SERVER row, not this device');

test("the server's row is returned, not the local copy", async () => {
  const c = harness({ serverRead: [SERVER_ROW], local: STALE_LOCAL });
  const b = await c.dntSettingsMergeBase();
  assert.deepStrictEqual(b.base.appeal_windows, ['X', 'Y'],
    'the stale local copy was used as the merge base -- this is the whole defect');
  assert.strictEqual(b.local, false);
});

test("the row with id 'default' is picked, not simply the first", async () => {
  const other = { id: 'other', appeal_windows: ['WRONG'] };
  const c = harness({ serverRead: [other, SERVER_ROW], local: STALE_LOCAL });
  const b = await c.dntSettingsMergeBase();
  assert.deepStrictEqual(b.base.appeal_windows, ['X', 'Y']);
});

test('an empty server table falls back to local -- there is nothing to clobber yet', async () => {
  const c = harness({ serverRead: [], local: STALE_LOCAL });
  const b = await c.dntSettingsMergeBase();
  assert.deepStrictEqual(b.base, STALE_LOCAL);
  assert.strictEqual(b.local, false, 'an empty table is not the same as having no licence');
});

test('a FAILED read returns null, so the caller can refuse', async () => {
  // sdnData() returns null on every failure. Merging onto a base we could not
  // read is exactly the clobber this exists to stop, so it must not be treated
  // as "nothing on the server".
  const c = harness({ serverRead: null, local: STALE_LOCAL });
  assert.strictEqual(await c.dntSettingsMergeBase(), null);
});

test('NO LICENCE is a different case and keeps the local base', async () => {
  // A device with no licence key is not talking to a server, so there is
  // nothing to clobber. Refusing here would break a local-only install.
  const c = harness({ noLicense: true, local: STALE_LOCAL });
  const b = await c.dntSettingsMergeBase();
  assert.strictEqual(b.local, true);
  assert.deepStrictEqual(b.base, STALE_LOCAL);
  assert.strictEqual(c.__calls.reads, 0, 'no read should be attempted without a licence');
});

// ═══════════════════════════════════════════════════════════════════════════
section('the shared writer reports refusals instead of swallowing them');

test('a 200 is ok, and the record really reaches the network', async () => {
  // Field-by-field, not deepStrictEqual: the helper runs in a vm realm, so its
  // object literals have a different prototype and a structural comparison
  // fails on identity rather than on content.
  const c = harness({});
  const w = await c.dntSettingsWrite({ id: 'default', gfe_npi: '123' });
  assert.strictEqual(w.ok, true);
  assert.strictEqual(w.message, undefined);
  assert.strictEqual(c.__calls.writes.length, 1);
  assert.strictEqual(c.__calls.writes[0].resource, 'dnt_settings');
  assert.strictEqual(c.__calls.writes[0].payload.gfe_npi, '123');
});

test('409 SLUG_TAKEN comes back as the SERVER\'s own message', async () => {
  const c = harness({ writeResponse: { status: 409, body: { error: { code: 'SLUG_TAKEN', message: 'This booking link is already in use by another practice' } } } });
  const w = await c.dntSettingsWrite({ id: 'default' });
  assert.strictEqual(w.ok, false);
  assert.match(w.message, /already in use by another practice/);
});

test('any other refusal carries the reason and says nothing was saved', async () => {
  const c = harness({ writeResponse: { status: 400, body: { error: { code: 'BAD_LOCATIONS', message: 'locations must be an array' } } } });
  const w = await c.dntSettingsWrite({ id: 'default' });
  assert.strictEqual(w.ok, false);
  assert.match(w.message, /Nothing was saved/);
  assert.match(w.message, /locations must be an array/);
});

test('a thrown fetch is a refusal, not a success', async () => {
  const c = harness({});
  c.fetch = () => { throw new Error('offline'); };
  const w = await c.dntSettingsWrite({ id: 'default' });
  assert.strictEqual(w.ok, false);
  assert.match(w.message, /could not reach the server/i);
});

test('the stale "sync not yet enabled" wording is gone from the writer', () => {
  // It was on every failure path of all three panels. Sync IS enabled; the
  // string hid the real reason behind a reassuring one.
  assert.strictEqual(codeOf(fnBody('async function dntSettingsWrite(')).indexOf('sync not yet enabled'), -1);
});

// ═══════════════════════════════════════════════════════════════════════════
section('all three panels CONSULT the base, and the old one is gone');

for (const fn of ['async function saveBookingSettings()',
                  'async function dnPersistWindows(',
                  'async function saveGfeIdentity()']) {
  const label = fn.replace('async function ', '').replace(/\(.*/, '');
  test(label + ' merges onto dntSettingsMergeBase(), and NOT onto settings()', () => {
    const code = codeOf(fnBody(fn));
    assert.ok(code.indexOf('dntSettingsMergeBase()') > 0, 'does not consult the shared base');
    assert.strictEqual(code.indexOf('Object.assign({},settings()'), -1,
      'still merges onto the local cached copy -- asserting the new mechanism EXISTS is not enough, '
      + 'the old one has to be absent at the call site');
  });

  test(label + ' refuses when the base could not be read', () => {
    const code = codeOf(fnBody(fn));
    assert.match(code, /if\(!b\)\{toast\(/, 'a null base is not refused');
    assert.match(code, /could not be read from the server/, 'the refusal does not say why');
  });

  test(label + ' writes to the SERVER before localStorage', () => {
    const code = codeOf(fnBody(fn));
    const write = code.indexOf('dntSettingsWrite(rec)');
    const local = code.indexOf("st('dnt_settings_obj',rec)", code.indexOf('dntSettingsWrite(rec)'));
    const firstLocal = code.indexOf("st('dnt_settings_obj',rec)");
    assert.ok(write > 0, 'does not use the shared writer');
    assert.ok(local > write, 'no local write after the server call');
    // The only st() allowed BEFORE the writer is the no-licence branch, which
    // is guarded by b.local and never reaches the server at all.
    if (firstLocal < write) {
      const before = code.slice(0, firstLocal);
      assert.ok(/if\(b\.local\)\{/.test(before.slice(-40)),
        'an unguarded local write happens before the server call again');
    }
  });
}

test('saveBookingSettings no longer keeps a slug the server REFUSED', () => {
  // It wrote to localStorage before the request and the 409 branch only
  // toasted and returned, so the form and the patient-feedback link preview
  // advertised a booking slug belonging to another practice.
  const code = codeOf(fnBody('async function saveBookingSettings()'));
  const guard = code.indexOf('if(!w.ok)');
  const local = code.indexOf("st('dnt_settings_obj',rec)", guard);
  assert.ok(guard > 0 && local > guard, 'the refusal no longer precedes the local write');
});

test('the collision the tool reports is ACKNOWLEDGED with a traced reason', () => {
  const tool = fs.readFileSync(path.join(__dirname, '..', 'tools', 'key_collision_check.py'), 'utf8');
  assert.match(tool, /'dnt_settings_obj':\s*\(/, 'no acknowledgement entry');
  assert.match(tool, /\{'rec', 'serverSettings'\}/, 'the acknowledged variable pair is not the one reported');
});

// ═══════════════════════════════════════════════════════════════════════════
(async () => {
  for (const item of queue) {
    if (item.section) { console.log('--- ' + item.section + ' ---'); continue; }
    try { await item.fn(); console.log('  ok   ' + item.name); pass++; }
    catch (e) { console.log('  FAIL ' + item.name + '\n       ' + e.message); fail++; }
  }
  console.log('\nsairndental_settings_merge_base: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
