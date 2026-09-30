// tests/stonedesk_sync_null_blob.js
//
// Run:  node tests/stonedesk_sync_null_blob.js
//
// REQUIREMENT: a StoneDesk sync function that reports whether a write reached
//   the server must decide that from the response ENVELOPE, never from the
//   shape of the unwrapped payload -- the endpoint answers a stored row with a
//   null jsonb blob as 200/ok:true/data:null, which is a LANDED write that the
//   payload cannot be told apart from a failure.
//
// A LANDED WRITE REPORTED AS LOST, because the guard tests the wrong thing.
//
// hank's 2026-09-26 obligation said slabSyncOne's boolean "is only sound
// because the slabs write branch answers data: rows[0].data || payload". IT DOES
// NOT. api/sd-data.js answers
//
//     data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload
//
// on 69 write branches, slabs among them. The guard is on rows[0] EXISTING, not
// on rows[0].data being NON-NULL. `data` is a nullable jsonb column, so a stored
// row whose blob is null takes the TRUE branch, the endpoint answers 200 ok with
// data:null, sdData unwraps it to null, and slabSyncOne's
// `if (saved !== null && saved !== undefined) return true` falls through to
// `return false` and logs the slab as unsynced. The write landed. The app says
// it did not, and the failure log names a record that is on the server.
//
// ── WHAT THIS FILE FIXES AND WHAT IT CANNOT ────────────────────────────────
// api/sd-data.js is inside another session's claim, so the ENDPOINT half is
// supplied as change text in the review verdict and is NOT edited here. What is
// fixable in stonedesk.html is the CLIENT half, and it is the more general one:
// a caller that needs to know whether a write LANDED must not infer it from the
// shape of the returned payload. sdData already knows -- it tested `j.ok` on the
// envelope -- and threw that away.
//
// ── THE ARMS ──────────────────────────────────────────────────────────────
// A. THE KNOWN-BAD, on a stubbed transport answering 200/ok:true/data:null.
//    Before the fix this arm fails: the sync reports false on a landed write.
//    A0 exists because the FIRST version of this file failed A1 for the wrong
//    reason -- the sandbox was missing sdLicenseKey and sdData threw a
//    ReferenceError, which slabSyncOne's catch turned into the same `false` the
//    defect produces. A red that a broken harness can forge is not a control,
//    so A0 asserts the transport was actually reached and the envelope actually
//    read before any other arm is allowed to mean anything.
// B. THE SILENT HALF. A genuine failure -- ok:false, a non-200, no licence --
//    must still report false, or the fix is "always return true" and the whole
//    sync verdict becomes worthless.
// C. THE SWEEP, over the source: every other place that decides a write landed
//    from the unwrapped payload rather than from the envelope, plus the
//    cross-file anchor that keeps the two EXEMPT resources exempt.

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const PAGE = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8');
const ENDPOINT = fs.readFileSync(path.join(ROOT, 'api', 'sd-data.js'), 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
async function atest(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

// Lift one balanced function body out of the page by its opening line.
function grab(startsWith) {
  const at = PAGE.indexOf(startsWith);
  assert.ok(at > -1, 'anchor not found in stonedesk.html: ' + startsWith);
  let i = PAGE.indexOf('{', at), depth = 0;
  for (; i < PAGE.length; i++) {
    if (PAGE[i] === '{') depth++;
    else if (PAGE[i] === '}') { depth--; if (!depth) return PAGE.slice(at, i + 1); }
  }
  throw new Error('unbalanced body for ' + startsWith);
}

// The same, for the piece the FIX introduces. Absent before the fix, and the
// code under test does not reference it before the fix either, so returning
// null is the honest answer rather than an error that would take every arm
// down with it and hide which ones are red for the real reason.
function grabIfPresent(startsWith) {
  return PAGE.indexOf(startsWith) > -1 ? grab(startsWith) : null;
}

// A sandbox carrying everything the lifted functions touch. Everything the real
// page supplies is stubbed HERE rather than inside the functions, so the code
// under test is the shipped code. A missing stub does not produce a softer
// failure on this platform -- it produces the SAME `false` the defect produces,
// which is why A0 counts fetches.
function sandbox(reply) {
  const logged = [];
  const warned = [];
  const seen = { fetches: 0, envelopeRead: 0 };
  const ctx = {
    // console.warn IS THE CHANNEL THE DEFECT SPEAKS ON. The first version of
    // this file stubbed it to a no-op and asserted on sdDataFailed instead, so
    // the "no spurious log entry" arm passed while the shipped code was warning
    // that a landed slab had not reached the server.
    console: { warn: function (m) { warned.push(String(m)); },
               error: function () {} },
    JSON: JSON,
    Array: Array,
    Object: Object,
    String: String,
    Promise: Promise,
    fetch: async function () {
      seen.fetches++;
      return {
        ok: reply.httpOk !== false,
        status: reply.status || 200,
        json: async function () { seen.envelopeRead++; return reply.body; }
      };
    },
    // sdData's real name for the licence, not slabSyncOne's. Getting this wrong
    // is what forged the first red.
    sdLicenseKey: function () { return reply.noLicence ? '' : 'KEY'; },
    slabLicKey: function () { return reply.noLicence ? '' : 'KEY'; },
    sdFetchTimeoutSignal: function () { return undefined; },
    sdDataFailed: function (a, r, why) { logged.push(r + ': ' + why); },
    sdSyncLog: function (m) { logged.push(m); },
    sdMarkSynced: function () {},
    _sdAuthRefused: {},
    _sdReadFailed: {},
    _sdLastStatus: {},
    localStorage: { getItem: function () { return null; },
                    setItem: function () {} },
    sessionStorage: { getItem: function () { return null; } }
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  const writeOkDecl = grabIfPresent('var _sdWriteOk');
  if (writeOkDecl !== null) vm.runInContext('var _sdWriteOk = {};', ctx, { filename: '_sdWriteOk' });
  const landed = grabIfPresent('function sdWriteLanded(resource)');
  if (landed !== null) vm.runInContext(landed, ctx, { filename: 'sdWriteLanded' });
  vm.runInContext(grab('async function sdData(action, resource, payload)'), ctx,
                  { filename: 'sdData' });
  vm.runInContext(grab('async function slabSyncOne('), ctx,
                  { filename: 'slabSyncOne' });
  vm.runInContext(grab('async function sdLineageSyncOne(resource, rec)'), ctx,
                  { filename: 'sdLineageSyncOne' });
  ctx.__logged = logged;
  ctx.__warned = warned;
  ctx.__seen = seen;
  ctx.__hasAccessor = landed !== null;
  return ctx;
}

(async function () {
  console.log('StoneDesk sync -- a landed write must not report as lost');

  section('A. THE KNOWN-BAD: 200 ok:true data:null is a LANDED write');

  await atest('A0. THE HARNESS ARM, and it comes first: driving slabSyncOne '
    + 'really does reach the transport and really does read the envelope. '
    + 'Without this, one missing stub makes sdData throw, slabSyncOne\'s catch '
    + 'returns false, and A1 goes red for a reason that has nothing to do with '
    + 'the defect -- which is exactly what the first version of this file did',
    async function () {
      const ctx = sandbox({ body: { ok: true, data: null } });
      await ctx.slabSyncOne({ id: 'SLAB-0', name: 'x' });
      assert.strictEqual(ctx.__seen.fetches, 1,
        'the transport was never reached (' + ctx.__seen.fetches + ' fetches) -- '
        + 'sdData threw before it got there, so every arm below is measuring '
        + 'the sandbox, not the code');
      assert.strictEqual(ctx.__seen.envelopeRead, 1,
        'the 200 body was never parsed, so nothing under test saw ok:true');
      assert.deepStrictEqual(ctx.__logged, [],
        'sdData reported a transport failure on a clean 200: '
        + JSON.stringify(ctx.__logged));
      assert.ok(Array.isArray(ctx.__warned),
        'console.warn is not being captured, so A1b cannot see the spurious '
        + 'log line the defect emits');
    });

  await atest('A1. slabSyncOne returns TRUE when the server answers ok:true with '
    + 'data:null. That is a stored row whose jsonb blob is null -- the slabs '
    + 'write branch guards rows[0] EXISTING, not rows[0].data being non-null, '
    + 'so it answers data:null and the write DID land',
    async function () {
      const ctx = sandbox({ body: { ok: true, data: null } });
      const got = await ctx.slabSyncOne({ id: 'SLAB-1', name: 'x' });
      assert.strictEqual(got, true,
        'a landed write reported as LOST. The failure log now names a record '
        + 'that is on the server, which is the worst kind of sync report: it '
        + 'sends somebody to re-save data that is already saved.');
    });

  await atest('A1b. ...and NOTHING IS WARNED ABOUT IT. A correct return with a '
    + 'spurious "the yard copy and the server copy now disagree" line in the '
    + 'console is half the defect still shipping -- and console.warn is the '
    + 'channel slabSyncOne actually uses, not sdDataFailed',
    async function () {
      const ctx = sandbox({ body: { ok: true, data: null } });
      await ctx.slabSyncOne({ id: 'SLAB-1', name: 'x' });
      assert.deepStrictEqual(ctx.__warned, [],
        'warned: ' + JSON.stringify(ctx.__warned));
      assert.deepStrictEqual(ctx.__logged, [],
        'logged: ' + JSON.stringify(ctx.__logged));
    });

  await atest('A2. sdLineageSyncOne has the SAME defect and its comment says it '
    + 'does not: "All three lineage writes answer data: wrows[0].data || '
    + 'payload". api/sd-data.js:3303 and :3362 answer the row-exists ternary, '
    + 'the same one slabs uses. A landed lineage row must report TRUE',
    async function () {
      const ctx = sandbox({ body: { ok: true, data: null } });
      const got = await ctx.sdLineageSyncOne('sd_slab_lineage', { id: 'LIN-1' });
      assert.strictEqual(got, true,
        'a landed lineage write reported as lost -- and this is the function '
        + 'whose own header argues it cannot happen');
    });

  section('B. THE SILENT HALF: a real failure still reports false');

  await atest('B1. ok:false is still FALSE. Without this arm the fix is "always '
    + 'return true" and every sync verdict in the app becomes worthless',
    async function () {
      const ctx = sandbox({ body: { ok: false, error: { message: 'nope' } } });
      const got = await ctx.slabSyncOne({ id: 'SLAB-2', name: 'x' });
      assert.strictEqual(got, false, 'a refused write reported as landed');
    });

  await atest('B2. a NON-200 is still FALSE',
    async function () {
      const ctx = sandbox({ httpOk: false, status: 500,
                            body: { error: { message: 'boom' } } });
      const got = await ctx.slabSyncOne({ id: 'SLAB-3', name: 'x' });
      assert.strictEqual(got, false, 'a 500 reported as landed');
    });

  await atest('B3. and a normal success -- ok:true with a real blob -- is TRUE, '
    + 'so A1 is not passing because the function stopped looking at anything',
    async function () {
      const ctx = sandbox({ body: { ok: true, data: { id: 'SLAB-4' } } });
      const got = await ctx.slabSyncOne({ id: 'SLAB-4', name: 'x' });
      assert.strictEqual(got, true, 'an ordinary success reported as lost');
    });

  await atest('B4. NO LICENCE IS FALSE, AND THIS IS THE ARM THAT DECIDES '
    + 'WHETHER THE FIX FAILS OPEN. An envelope-level signal read out of a map '
    + 'is `undefined` for a call that never happened, and `!undefined` is '
    + 'true -- so a write that never left the browser would report as landed. '
    + 'The signal has to be a positive record, not the absence of a failure',
    async function () {
      const ctx = sandbox({ noLicence: true, body: { ok: true, data: null } });
      const got = await ctx.slabSyncOne({ id: 'SLAB-5', name: 'x' });
      assert.strictEqual(ctx.__seen.fetches, 0,
        'no licence should not reach the transport at all');
      assert.strictEqual(got, false, 'a write that never happened reported as '
        + 'landed -- the accessor fails OPEN');
    });

  await atest('B5. ...and the same for a lineage write with no licence',
    async function () {
      const ctx = sandbox({ noLicence: true, body: { ok: true, data: null } });
      const got = await ctx.sdLineageSyncOne('sd_slab_lineage', { id: 'LIN-2' });
      assert.strictEqual(got, false, 'the accessor fails OPEN for lineage');
    });

  section('C. THE SWEEP: who else decides a write landed from the payload?');

  // Every `X = await sdData('write'|'write_batch'|'soft_delete', <resource>)`
  // whose next few lines test X for null/undefined or truthiness. Read off the
  // source, so a new caller written the old way is caught here rather than in a
  // sync log. Keyed on the RESOURCE argument, not the line number: line numbers
  // in a 2MB single-file app move every session and would make this arm stale
  // without anything announcing it.
  const LINES = PAGE.split('\n');
  const suspects = [];
  for (let i = 0; i < LINES.length; i++) {
    const m = /(?:var|const|let)\s+(\w+)\s*=\s*await\s+sdData\(\s*'(write|write_batch|soft_delete)'\s*,\s*('?[\w.]+'?)/
      .exec(LINES[i]);
    if (!m) continue;
    const name = m[1];
    const after = LINES.slice(i + 1, i + 6).join('\n');
    const infers = new RegExp('\\b' + name + '\\s*!==\\s*null'
                             + '|\\b' + name + '\\s*===\\s*null'
                             + '|if\\s*\\(\\s*!?' + name + '\\s*\\)').test(after);
    if (infers) {
      suspects.push({ line: i + 1, name: name, action: m[2],
                      resource: m[3].replace(/'/g, '') });
    }
  }

  // The two that may stay. Not "these are fine" -- these are the two whose
  // endpoint branch cannot answer a falsy `data` at all, because it wraps the
  // stored blob in flat(), which is Object.assign({}, data || {}, extra) and
  // therefore always an object. C4 re-checks that claim against the endpoint on
  // every run rather than trusting this comment.
  const EXEMPT = {
    memory: 'api/sd-data.js answers flat(row.data, {created_at}) -- always an '
          + 'object, so a null blob cannot reach the caller as a falsy value',
    profile: 'api/sd-data.js answers flat(row.data, {shop_id}) -- same'
  };

  test('C1. the sweep found the call sites it was built to find -- a zero here '
    + 'would mean the pattern stopped matching and every arm below is vacuous',
    function () {
      assert.ok(LINES.length > 1000, 'the page did not load');
      assert.ok(/await sdData\('write'/.test(PAGE),
        'no write call site matches the pattern at all');
      assert.ok(suspects.length >= 2,
        'the pattern matched fewer than the two EXEMPT sites it must always '
        + 'find (' + suspects.length + '). The regex has stopped matching and '
        + 'C2 would pass against nothing');
    });

  test('C2. NO caller outside the two EXEMPT resources decides a write landed '
    + 'by testing the unwrapped payload. Every other one must read the '
    + 'envelope, because a 200 ok:true with a null blob is a LANDED write and '
    + 'the payload cannot tell you that',
    function () {
      const bad = suspects.filter(function (s) {
        return !Object.prototype.hasOwnProperty.call(EXEMPT, s.resource);
      });
      assert.deepStrictEqual(bad.map(function (s) {
        return s.resource + ' (' + s.name + ')';
      }), [], 'these infer success from the payload shape:\n       '
        + bad.map(function (s) {
            return 'stonedesk.html:' + s.line + '  ' + s.name + ' = await '
                   + 'sdData(\'' + s.action + '\', ' + s.resource + ')';
          }).join('\n       '));
    });

  test('C3. ANCHOR, on code that ships TODAY: sdData still decides success from '
    + 'the ENVELOPE -- `if (!(j && j.ok))` -- and still records the outcome per '
    + 'resource. That envelope test is the fact the fix reads. If it is removed '
    + 'or renamed there is no envelope-level truth left to read and C2 would '
    + 'pass because every caller is back to guessing from the payload',
    function () {
      assert.ok(/if \(!\(j && j\.ok\)\) \{/.test(PAGE),
        'sdData no longer tests the envelope ok flag');
      assert.ok(/_sdReadFailed\[resource\] = false;/.test(PAGE),
        'sdData no longer records a per-resource success');
    });

  test('C4. CROSS-FILE ANCHOR, read-only on fourth\'s file: the two EXEMPT '
    + 'resources are exempt ONLY because their write branch wraps the blob in '
    + 'flat(). If either is changed to the bare row-exists ternary the 69 other '
    + 'branches use, the exemption is false and this arm says so',
    function () {
      assert.ok(/function flat\(data, extra\) \{\s*\n\s*return Object\.assign\(\{\}, data \|\| \{\}, extra \|\| \{\}\);/
        .test(ENDPOINT), 'flat() no longer coerces a null blob to an object, so '
        + 'the memory and profile exemptions are no longer sound');
      assert.ok(/data: row \? flat\(row\.data, \{ created_at: row\.created_at \}\) : payload/
        .test(ENDPOINT), 'the memory write branch no longer answers through '
        + 'flat() -- remove it from EXEMPT and fix the caller');
      assert.ok(/data: row \? flat\(row\.data, \{ shop_id: row\.shop_id \}\) : payload/
        .test(ENDPOINT), 'the profile write branch no longer answers through '
        + 'flat() -- remove it from EXEMPT and fix the caller');
    });

  test('C5. and the endpoint-side defect is still THERE, so nothing here is '
    + 'claiming it was fixed: the row-exists ternary that answers a null blob '
    + 'as data:null is still on the slabs and lineage write branches. When '
    + 'fourth lands the endpoint change this arm goes red and is the prompt to '
    + 'retire the client-side workaround, not to delete the arm',
    function () {
      const n = (ENDPOINT.match(/\? [a-zA-Z]+\[0\]\.data : /g) || []).length;
      assert.ok(n > 0, 'the endpoint no longer answers the row-exists ternary '
        + 'anywhere -- re-read api/sd-data.js and re-derive whether the client '
        + 'workaround is still needed');
      console.log('       (endpoint still answers a bare row-exists ternary on '
        + n + ' branches -- the change text for fourth is in the verdict)');
    });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
