// tests/faults/sv_backup_write_faults.js
//
// Run:  node tests/faults/sv_backup_write_faults.js
//
// FAULT INJECTION on SAIRNvet's server-backup WRITE path -- svSyncCollection()
// at the st() hook, and recordSvSharedTopics() on the AI context path.
//
// ── WHAT THE HAZARD SCAN SAID, AND WHERE IT WAS WRONG ──────────────────────
// tools/write_path_fault_scan.py flagged two sites in this file and the
// hand-verification note written with it (SAIRN-ACTIVE-WORK-cody.md,
// 2026-09-10) explained them like this:
//
//   sairnvet.html:2135 -- "...has no `.catch`. A DROPPED SOCKET SKIPS THAT
//                          HANDLER ENTIRELY."
//   sairnvet.html:8721 -- "a try/catch whose catch is synchronous and cannot
//                          catch a promise rejection."
//
// BOTH MECHANISMS ARE WRONG, and the correction is the reason this file exists
// rather than a straight port of SAIRNdental's fix. svData() -- sairnvet.html
// :8698 -- ends in `.catch(function(e){ console.warn(...); return null; })`.
// So a dropped socket, a DNS failure, a CORS rejection and a non-JSON body
// (Vercel's bot-mitigation challenge page, which this platform really does get)
// are ALL converted to a resolved `null` before any caller sees them. The
// `.then(saved => ...)` handler at 2135 therefore DOES run, and it DOES warn.
// There is no unhandled rejection to find on either line in the app as it
// stands. A checker that reads a call site cannot see that its callee already
// catches -- the flag was correct about the SHAPE and the conclusion drawn from
// it was not, which is why a flag is a lead and not a finding.
//
// ── THE FAULT THAT IS REAL, AND IS NOT THE ONE THAT WAS WRITTEN DOWN ──────
// `grep -c setTimeout sairnvet.html` returned **1** for an 8,866-line file, and
// that one occurrence is not on this path. There is NO TIMEOUT ANYWHERE. So:
//
//   A HANG NEVER SETTLES. fetch() against a black-holed connection or a
//   gateway that accepts and never answers resolves nothing and rejects
//   nothing. svData()'s `.catch` is never reached either -- it only fires on a
//   rejection. The `.then` at 2135 never runs, the careful `saved===null`
//   warning never prints, the record is never backed up, and NOTHING SAYS SO.
//
// That is the defect class the whole backup feature was built to close, arriving
// through the one door the feature's own reporting cannot see. It is also the
// portfolio finding: 11 of 15 apps that write to a server have no timeout
// anywhere on a write path.
//
// ── WHY A REJECTION ARM IS STILL HERE ─────────────────────────────────────
// Not to assert the app currently rejects -- it does not. The helper is a
// boundary, and a boundary that is only correct while its callee keeps its
// `.catch` is one edit away from the original claim becoming true. The arm
// costs one line in the fix and removes the dependency.
//
// Every arm drives the REAL functions grabbed out of the real file.

'use strict';
const fs = require('fs');
const path = require('path');
const K = require('./faultkit');
const assert = K.assert;

const FILE = 'sairnvet.html';
const SRC = fs.readFileSync(path.join(K.ROOT, FILE), 'utf8');

let pass = 0, fail = 0;
const tests = [];
function test(name, fn) { tests.push([name, fn]); }
function section(t) { tests.push([t, null]); }

// The push helper's timeout has to be shortened or every hang arm would wait
// the real 15s. Patched in the SOURCE TEXT, not re-implemented: the arm still
// runs the file's own code, it just runs it on a stopwatch it can afford.
function ctxFor(opts) {
  const ctx = K.makeWorld(opts || {});
  K.vm.runInContext('var svSyncSuppressed=false;', ctx);
  K.vm.runInContext('var SV_SYNCED_ON={};', ctx);
  K.vm.runInContext('var SV_ID_FIELD={ sv_controlled:"drug" };', ctx);
  K.vm.runInContext('function svLoad(k,d){ return k==="license" ? "SV-TEST-2026" : d; }', ctx);
  const localOnly = SRC.slice(SRC.indexOf('var SV_LOCAL_ONLY_FIELDS=')).split(/\r?\n/)[0];
  K.vm.runInContext(localOnly, ctx);
  K.vm.runInContext(K.grab(SRC, 'function svOutbound(', ''), ctx);
  if (SRC.indexOf('function svPushOne(') > 0) {
    const consts = SRC.slice(SRC.indexOf('var SV_PUSH_TIMEOUT ')).split(/\r?\n/).slice(0, 3).join('\n');
    K.vm.runInContext(consts.replace(/SV_PUSH_TIMEOUT_MS\s*=\s*\d+/, 'SV_PUSH_TIMEOUT_MS = 120'), ctx);
    K.vm.runInContext(K.grab(SRC, 'function svPushOne(', ''), ctx);
  }
  K.vm.runInContext(K.grab(SRC, 'function svSyncCollection(', ''), ctx);
  return ctx;
}

const REC = { id: 'p1', name: 'Rex' };
function backupWarns(ctx) {
  return ctx._state.warns.filter((w) => /did NOT reach the server/.test(w));
}

section('the happy path still works -- or every arm below is vacuous');

test('a changed record REACHES the server and nothing is reported', async () => {
  const ctx = ctxFor({});
  ctx.svSyncCollection('sv_patients', [REC], []);
  await new Promise((r) => setTimeout(r, 250));
  assert.strictEqual(ctx._state.written.length, 1, 'the record never reached the server');
  assert.deepStrictEqual(backupWarns(ctx), [], 'a successful push reported a failure');
});

test('an UNCHANGED record is not pushed at all', async () => {
  const ctx = ctxFor({});
  ctx.svSyncCollection('sv_patients', [REC], [REC]);
  await new Promise((r) => setTimeout(r, 250));
  assert.strictEqual(ctx._state.written.length, 0);
});

section('REFUSED -- the one fault the original code already handled');

test('a refusal names the collection and the record', async () => {
  const ctx = ctxFor({ transport: 'refused' });
  ctx.svSyncCollection('sv_patients', [REC], []);
  await new Promise((r) => setTimeout(r, 250));
  const w = backupWarns(ctx);
  assert.strictEqual(w.length, 1, 'a refused push said nothing');
  assert.ok(/sv_patients/.test(w[0]) && /p1/.test(w[0]),
    'the warning does not identify what was lost: ' + w[0]);
});

section('HANG -- the real defect, and the one nothing could see');

test('A HANG IS REPORTED rather than being waited on forever', async () => {
  // AGAINST THE PRE-FIX FILE THIS ARM FAILS WITH ZERO WARNINGS. That is the
  // defect reproduced: the clinic's record is on one device, the backup did
  // not happen, and the app's own failure reporting never runs because it is
  // attached to a promise that never settles.
  const ctx = ctxFor({ transport: 'hang' });
  ctx.svSyncCollection('sv_patients', [REC], []);
  await new Promise((r) => setTimeout(r, 400));
  const w = backupWarns(ctx);
  assert.strictEqual(w.length, 1, 'a hung push said NOTHING -- ' + w.length + ' warnings');
  assert.ok(/no answer/i.test(w[0]),
    'the warning does not say it was a timeout, so the reader cannot tell a '
    + 'refusal from a dead connection: ' + w[0]);
});

test('a hang does NOT claim the record reached the server', async () => {
  const ctx = ctxFor({ transport: 'hang' });
  ctx.svSyncCollection('sv_patients', [REC], []);
  await new Promise((r) => setTimeout(r, 400));
  assert.strictEqual(ctx._state.written.length, 0);
});

test('one hung record does not stop the OTHERS in the same collection', async () => {
  // A loop that awaited each push would turn one dead record into a dead
  // collection. The pushes are independent and must stay that way.
  const ctx = ctxFor({ transport: 'hang', failFrom: 2 });
  ctx.svSyncCollection('sv_patients', [REC, { id: 'p2', name: 'Mia' }], []);
  await new Promise((r) => setTimeout(r, 400));
  assert.strictEqual(ctx._state.written.length, 1, 'the first record was lost too');
  assert.strictEqual(backupWarns(ctx).length, 1, 'the hung record was not reported');
});

section('REJECTION -- not reachable through svData() today, and not relied on');

test('a rejection is reported, not left unhandled', async () => {
  const ctx = ctxFor({ transport: 'throw' });
  ctx.svSyncCollection('sv_patients', [REC], []);
  await new Promise((r) => setTimeout(r, 250));
  const w = backupWarns(ctx);
  assert.strictEqual(w.length, 1, 'a rejected push said nothing');
  assert.ok(/connection/i.test(w[0]), 'the reason is not stated: ' + w[0]);
});

section('the AI-context write -- fire-and-forget, with nothing reading it');

test('recordSvSharedTopics routes through the same helper', () => {
  // It was `svData(...)` bare inside a synchronous try/catch. A refusal was
  // logged by svData itself, so that half was never silent -- but a HANG was,
  // exactly as above, and the call site had no way to know either way.
  const body = K.grab(SRC, 'function recordSvSharedTopics(', '');
  assert.ok(/svPushOne\(/.test(body),
    'recordSvSharedTopics still calls svData directly, so a hang on the '
    + 'shared-knowledge write is unobservable');
});

test('...and it still guards the case where the helper is not defined yet', () => {
  const body = K.grab(SRC, 'function recordSvSharedTopics(', '');
  assert.ok(/try\s*\{/.test(body),
    'the synchronous guard was removed; svLoad() and JSON.stringify() can '
    + 'still throw before any promise exists');
});

section('the structural half -- a THIRD write site added later is caught here');

test('no server-backup write call site bypasses svPushOne', () => {
  // The shape is the defect, so the shape is what is asserted. Every
  // `svData('write'` in the file must be inside svPushOne itself.
  const sites = [];
  const re = /svData\(\s*['"]write['"]/g;
  let m;
  while ((m = re.exec(SRC)) !== null) {
    sites.push(SRC.slice(0, m.index).split(/\r?\n/).length);
  }
  assert.strictEqual(sites.length, 1,
    'expected exactly one `svData("write"` -- the one inside svPushOne -- '
    + 'found ' + sites.length + ' at line(s) ' + sites.join(', ')
    + '. A write that does not go through the helper has no timeout.');
  const helper = K.grab(SRC, 'function svPushOne(', '');
  assert.ok(/svData\(\s*['"]write['"]/.test(helper),
    'the single write call site is not the one inside svPushOne');
});

test('the timeout is a real number of milliseconds, not a disabled 0', () => {
  const m = SRC.match(/var SV_PUSH_TIMEOUT_MS\s*=\s*(\d+)/);
  assert.ok(m, 'SV_PUSH_TIMEOUT_MS is not declared');
  const ms = Number(m[1]);
  assert.ok(ms >= 5000 && ms <= 60000,
    'SV_PUSH_TIMEOUT_MS is ' + ms + 'ms -- too short is a false alarm on a slow '
    + 'connection, too long is the hang again');
});

test('svPushOne does not mark anything "unconfirmed" -- SAIRNvet has no such flag', () => {
  // DELIBERATELY NARROWER THAN SAIRNdental's dntPushOne, and this arm records
  // why so the next reader does not "complete" the port. dntPushOne treats a
  // partial response as unconfirmed because dntHydrate OVERWRITES local rows,
  // so an unconfirmed local copy can be clobbered. svHydrateAll() is
  // additive-only and NEVER overwrites a locally present id -- stated at its
  // own definition -- so there is no destructive path for a flag to protect.
  assert.ok(/NEVER overwritten/.test(SRC) || /is NEVER overwritten/.test(SRC),
    'svHydrateAll no longer documents additive-only merging; if hydration now '
    + 'overwrites local rows, the partial-response case DOES need a flag and '
    + 'this narrowing is no longer justified');
  const helper = K.grab(SRC, 'function svPushOne(', '');
  assert.ok(!/Unconfirmed/i.test(helper), 'an unconfirmed flag appeared without '
    + 'the hydration behaviour that would make it necessary');
});

(async () => {
  for (const [name, fn] of tests) {
    if (fn === null) { console.log('--- ' + name + ' ---'); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
  }
  console.log('\n' + (fail === 0
    ? 'ALL ' + pass + ' BACKUP WRITE FAULT ARMS PASS'
    : pass + ' passed, ' + fail + ' FAILED'));
  process.exit(fail === 0 ? 0 : 1);
})();
