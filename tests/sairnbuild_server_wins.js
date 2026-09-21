// tests/sairnbuild_server_wins.js
//
// Run:  node tests/sairnbuild_server_wins.js
//
// # REQUIREMENT: SAIRNbuild implements the platform's server-wins hydration
//   rule -- once a record's id exists on both sides the server's copy wins --
//   with its carve-out taken from bld_sync_pending rather than from a
//   synced-id map; and it does not overwrite anything while that list cannot
//   be read, has overflowed, or has not yet been proved to describe reality
//   on this device
//
// ── WHY THIS APP HAS ITS OWN SUITE AND IS NOT IN server_wins_hydration.js ─
// That suite asserts the seven converted apps carry BYTE-IDENTICAL helpers
// modulo their names, which is what stops seven copies of one rule drifting.
// SAIRNbuild is a DECLARED VARIANT: its carve-out comes from a different and
// stronger source, so it cannot be byte-identical and must not be forced to
// be. The rule for a variant is the one the platform already applies to any
// exception -- it carries a written justification and its own arms, rather
// than being admitted by relaxing somebody else's.
//
// ── THE JUSTIFICATION, IN ONE PARAGRAPH ──────────────────────────────────
// The seven apps record ids that HAVE landed (`<app>_synced_ids`), so their
// carve-out protects a record whose FIRST push never landed and cannot protect
// an EDIT to a record that synced months ago. That gap is a recorded finding
// on SAIRNlaw: a locally-issued invoiced:true, on an id long since synced, was
// silently reverted by the next hydrate. SAIRNbuild already had
// `bld_sync_pending` -- ids whose push FAILED, cleared when it succeeds,
// capped, and retried once per sign-in. It answers "does this id have an
// unpushed change right now?", which is the question the rule actually needs.
//
// ── AND THE TRUST GATE, WHICH IS THIS APP'S BOOTSTRAP ────────────────────
// bld_sync_pending only began being written on 2026-09-04, and sairnbuild.html
// records that every push this feature ever attempted had failed before then
// because the schema had never been run. So on an old device "absent from
// pending" means "never pushed", not "safe to overwrite". Nothing is
// overwritten until one sign-in completes with the retry leaving the list
// EMPTY against a provisioned server; that sets bld_pending_trusted.
//
// The negative control is tests/run_sairnbuild_server_wins_sabotage_probe.py.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'sairnbuild.html'), 'utf8').replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
const queue = [];
function test(name, fn) { queue.push({ name, fn }); }
function section(t) { queue.push({ section: t }); }

function braceBody(at) {
  const open = html.indexOf('{', at);
  let depth = 0;
  for (let i = open; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}') { depth--; if (depth === 0) return html.slice(at, i + 1); }
  }
  throw new Error('unbalanced braces');
}
function fn(name) {
  const at = html.indexOf('function ' + name + '(');
  assert.ok(at > 0, 'not found in sairnbuild.html: ' + name);
  return braceBody(at);
}
function oneLineVar(name) {
  const at = html.indexOf('var ' + name + '=');
  const b = at > 0 ? at : html.indexOf('var ' + name + ' =');
  assert.ok(b > 0, name + ' not found');
  return html.slice(b, html.indexOf(';', b) + 1);
}

// opts.local    { key: [records] }
// opts.pending  { key: [ids], __overflow?: true } | 'corrupt' | undefined
// opts.trusted  true to pretend this device has completed a clean retry
function harness(opts) {
  opts = opts || {};
  const raw = {};
  Object.keys(opts.local || {}).forEach((k) => { raw[k] = JSON.stringify(opts.local[k]); });
  if (opts.pending === 'corrupt') raw.bld_sync_pending = '{not json';
  else if (opts.pending !== undefined) raw.bld_sync_pending = JSON.stringify(opts.pending);
  if (opts.trusted) raw.bld_pending_trusted = '1';

  const pushed = [];
  const ctx = {
    JSON, Object, Array, String, Number, Math, Date,
    console: { warn: () => {}, error: () => {} },
    localStorage: {
      getItem: (k) => (Object.prototype.hasOwnProperty.call(raw, k) ? raw[k] : null),
      setItem: (k, v) => { raw[k] = String(v); },
    },
    // The real st() calls bldSyncCollection(); the real bldSyncCollection
    // returns early on `!_bldSyncOn[key] || bldSeeding`. BOTH guards are kept
    // here, because the property under test is that the store seam sets
    // bldSeeding -- a stub that recorded unconditionally would report a push
    // the shipped code never makes, and a stub that recorded never would pass
    // whatever the seam did.
    bldSyncCollection: (k, v) => {
      if (!ctx._bldSyncOn[k] || ctx.bldSeeding) return;
      pushed.push(k);
    },
    bldIsQuotaError: () => false,
    __raw: raw, __pushed: pushed,
  };
  ctx.self = ctx;
  vm.createContext(ctx);
  vm.runInContext([
    fn('st'), fn('ld'),
    oneLineVar('BLD_PENDING_KEY'),
    oneLineVar('BLD_TRUST_KEY'),
    'var bldSeeding=false;',
    'var _bldSyncOn={bld_jobs:true,bld_bids:false};',
    fn('bldPendingRead'), fn('bldPendingAll'),
    fn('bldWhileSeeding'),
    fn('bldPendingTrusted'), fn('bldMarkPendingTrusted'), fn('bldPendingCount'),
    fn('bldHydrateLoad'), fn('bldHydrateStore'),
    fn('bldServerWinsMerge'),
  ].join('\n'), ctx);
  ctx.local = (k) => JSON.parse(raw[k] || 'null');
  // ── THE ATTESTATION, RUN RATHER THAN READ (2026-09-21) ──────────────────
  // The arms below checked the boot line for substrings, which is how a
  // condition can be present and still be wrong: the line did contain
  // `bldPendingCount()===0`, and that is TRUE on a device whose pending list
  // was never written -- so the check passed and the flag was granted with
  // zero pushes. Reading a condition cannot tell you what it answers. The
  // statement itself is lifted out of the file and evaluated here.
  ctx.attest = (provisioned) => {
    ctx._bldBackup = { provisioned: provisioned };
    vm.runInContext(attestLine(), ctx);
  };
  return ctx;
}

// The one statement that grants trust. Found by its call rather than by a line
// number, and it FAILS LOUDLY if that call moves or is duplicated -- a second
// attestation elsewhere is a thing this suite would otherwise never see, and
// it would drive only the first.
function attestLine() {
  const at = html.indexOf('bldMarkPendingTrusted();');
  assert.ok(at > 0, 'no call to bldMarkPendingTrusted() -- nothing attests anything');
  assert.strictEqual(html.indexOf('bldMarkPendingTrusted();', at + 1), -1,
    'bldMarkPendingTrusted() is called in more than one place; this suite drives ONE line '
    + 'and would silently test only that one');
  const NL = String.fromCharCode(10);
  return html.slice(html.lastIndexOf(NL, at) + 1, html.indexOf(NL, at));
}
// ── THE BOOT CHAIN, BOUNDED BY ITS OWN SHAPE (2026-09-21) ────────────────
// Both arms below used to slice a FIXED 2200 CHARACTERS from the start of the
// chain. That is a window, not a boundary, and it did exactly what a window
// does: a 40-line comment was added above the attestation and `.catch(` fell
// off the end, so "the pull/push chain has no catch" failed against a chain
// that still had one. The arm was right about nothing and loud about it.
//
// Bounded now by the enclosing function's own closing brace -- a newline
// followed by `}` in column zero -- and it FAILS rather than returning a short
// slice if it cannot find one.
function bootChain() {
  const NL = String.fromCharCode(10);
  const a = html.indexOf('bldHydrateAll().then(');
  assert.ok(a > 0, 'the boot chain is gone -- nothing hydrates on load');
  const end = html.indexOf(NL + '}', a);
  assert.ok(end > a, 'could not find the end of the function holding the boot chain');
  return html.slice(a, end);
}

const K = 'bld_jobs';

// ═══════════════════════════════════════════════════════════════════════════
section('1. server-wins, once the pending list is trusted');

test('a record held on both sides takes the server copy', () => {
  const c = harness({ local: { [K]: [{ id: 'J-1', status: 'open', note: 'stale' }] },
                      pending: {}, trusted: true });
  c.bldServerWinsMerge(K, [{ id: 'J-1', status: 'closed', note: 'server truth' }]);
  const row = c.local(K)[0];
  assert.strictEqual(row.status, 'closed', 'the local copy survived -- this is the additive behaviour');
  assert.strictEqual(row.note, 'server truth');
});

test('a field the server dropped is gone locally -- replace, not merge', () => {
  const c = harness({ local: { [K]: [{ id: 'J-1', status: 'open', localOnly: 'kept?' }] },
                      pending: {}, trusted: true });
  c.bldServerWinsMerge(K, [{ id: 'J-1', status: 'closed' }]);
  assert.ok(!('localOnly' in c.local(K)[0]), 'a local-only field survived -- that is a field MERGE');
});

test('a server record not held locally is appended', () => {
  const c = harness({ local: { [K]: [{ id: 'J-1' }] }, pending: {}, trusted: true });
  const n = c.bldServerWinsMerge(K, [{ id: 'J-1' }, { id: 'J-2', from: 'another device' }]);
  assert.strictEqual(n, 1);
  assert.deepStrictEqual(c.local(K).map((r) => r.id).sort(), ['J-1', 'J-2']);
});

test('a failed read changes nothing and returns null', () => {
  const c = harness({ local: { [K]: [{ id: 'J-9', note: 'mine' }] }, pending: {}, trusted: true });
  assert.strictEqual(c.bldServerWinsMerge(K, null), null);
  assert.strictEqual(c.local(K)[0].note, 'mine');
});

test('hydrated rows are NOT echoed back to the server -- the store seam suppresses', () => {
  const c = harness({ local: { [K]: [{ id: 'J-1' }] }, pending: {}, trusted: true });
  c.bldServerWinsMerge(K, [{ id: 'J-2' }]);
  assert.deepStrictEqual(c.__pushed, [],
    'records that came FROM the server were pushed back to it');
});

// ═══════════════════════════════════════════════════════════════════════════
section('2. the carve-out: an id with an UNPUSHED CHANGE keeps its local value');

test('an id in bld_sync_pending is NOT overwritten', () => {
  const c = harness({ local: { [K]: [{ id: 'J-1', note: 'edited here, never pushed' }] },
                      pending: { [K]: ['J-1'] }, trusted: true });
  c.bldServerWinsMerge(K, [{ id: 'J-1', note: 'server copy' }]);
  assert.strictEqual(c.local(K)[0].note, 'edited here, never pushed',
    'a record with an unpushed change was overwritten -- the only copy of it is gone');
});

test('AND THIS IS THE CASE A SYNCED-ID MAP CANNOT COVER -- an EDIT to a long-synced record', () => {
  // The SAIRNlaw finding, in this app's terms: the record synced months ago,
  // so a "has it ever landed" map says yes and permits the overwrite. What
  // matters is that THIS CHANGE has not landed, which is what pending knows.
  const c = harness({ local: { [K]: [{ id: 'J-1', status: 'invoiced' }] },
                      pending: { [K]: ['J-1'] }, trusted: true });
  c.bldServerWinsMerge(K, [{ id: 'J-1', status: 'open' }]);
  assert.strictEqual(c.local(K)[0].status, 'invoiced');
});

test('a DIFFERENT id in the same resource is still overwritten', () => {
  const c = harness({ local: { [K]: [{ id: 'J-1', v: 'local' }, { id: 'J-2', v: 'local' }] },
                      pending: { [K]: ['J-1'] }, trusted: true });
  c.bldServerWinsMerge(K, [{ id: 'J-1', v: 'server' }, { id: 'J-2', v: 'server' }]);
  const by = {}; c.local(K).forEach((r) => { by[r.id] = r.v; });
  assert.strictEqual(by['J-1'], 'local', 'the pending one was overwritten');
  assert.strictEqual(by['J-2'], 'server', 'a non-pending one was protected for no reason');
});

// ═══════════════════════════════════════════════════════════════════════════
section('3. three reasons not to overwrite, and each is a THIRD STATE');

test('an UNREADABLE pending file overwrites nothing', () => {
  const c = harness({ local: { [K]: [{ id: 'J-1', note: 'local' }] },
                      pending: 'corrupt', trusted: true });
  c.bldServerWinsMerge(K, [{ id: 'J-1', note: 'server' }]);
  assert.strictEqual(c.local(K)[0].note, 'local',
    'a file that could not be read was treated as "nothing is pending", which is permission');
  assert.strictEqual(c.__raw.bld_sync_pending, '{not json',
    'the unreadable file was overwritten -- whatever it held is now unrecoverable');
});

test('an OVERFLOWED list overwrites nothing in any resource', () => {
  // Past BLD_PENDING_MAX the list stops recording, so every id beyond the cap
  // looks un-pending -- during exactly the long outage that filled it.
  const c = harness({ local: { [K]: [{ id: 'J-1', note: 'local' }] },
                      pending: { __overflow: true, [K]: [] }, trusted: true });
  c.bldServerWinsMerge(K, [{ id: 'J-1', note: 'server' }]);
  assert.strictEqual(c.local(K)[0].note, 'local');
});

test('an UNTRUSTED device overwrites nothing -- the list has not been proved yet', () => {
  // bld_sync_pending began 2026-09-04 and every push before then had failed,
  // so on an old device "absent from pending" means "never pushed".
  const c = harness({ local: { [K]: [{ id: 'J-1', note: 'local' }] }, pending: {} });
  c.bldServerWinsMerge(K, [{ id: 'J-1', note: 'server' }]);
  assert.strictEqual(c.local(K)[0].note, 'local',
    'a device that has never completed a clean retry overwrote a record anyway');
});

test('...and it still APPENDS while untrusted -- the old additive behaviour, not a freeze', () => {
  const c = harness({ local: { [K]: [{ id: 'J-1' }] }, pending: {} });
  const n = c.bldServerWinsMerge(K, [{ id: 'J-1' }, { id: 'J-2' }]);
  assert.strictEqual(n, 1);
  assert.deepStrictEqual(c.local(K).map((r) => r.id).sort(), ['J-1', 'J-2']);
});

test('once trusted, the SAME device overwrites', () => {
  const c = harness({ local: { [K]: [{ id: 'J-1', note: 'local' }] }, pending: {} });
  c.bldServerWinsMerge(K, [{ id: 'J-1', note: 'server' }]);
  assert.strictEqual(c.local(K)[0].note, 'local');
  c.bldMarkPendingTrusted();
  c.bldServerWinsMerge(K, [{ id: 'J-1', note: 'server' }]);
  assert.strictEqual(c.local(K)[0].note, 'server');
});

// ═══════════════════════════════════════════════════════════════════════════
section('4. the source-level facts the merge rests on');

test('both hydrates go through the ONE merge, and neither keeps a private copy', () => {
  ['bldHydrateAll', 'bldHydrateBids'].forEach((name) => {
    const body = fn(name);
    assert.ok(body.indexOf('bldServerWinsMerge(') !== -1, name + ' does not call the shared merge');
    assert.ok(!/!\w+\[String\(\w+\.id\)\]/.test(body), name + ' still carries an additive merge');
  });
});

test('the seeding suppression has a finally, and the boot chain has a catch', () => {
  assert.match(fn('bldWhileSeeding'), /finally/,
    'a throw inside st() would leave the whole app un-backed-up for the session');
  const boot = bootChain();
  assert.ok(boot.indexOf('.catch(function(e)') !== -1,
    'the pull/push chain has no catch -- a throw strands the pending retry silently');
  assert.ok(boot.indexOf('bldMarkPendingTrusted()') !== -1,
    'nothing ever attests that the pending list describes reality, so the merge can never trust it');
});

test('the attestation is EARNED, not merely made', () => {
  // Found by the sabotage probe: making bldMarkPendingTrusted() unconditional
  // passed every other arm. The flag is never cleared, so ONE wrong
  // attestation makes the carve-out permanently unearned on that device while
  // everything keeps looking correct -- which is worse than bypassing the gate,
  // because it is silent and it is durable.
  const boot = bootChain();
  const at = boot.indexOf('bldMarkPendingTrusted()');
  const NL = String.fromCharCode(10);
  const line = boot.slice(boot.lastIndexOf(NL, at) + 1, at);
  assert.match(line, /if\s*\(/, 'the attestation is unconditional: ' + JSON.stringify(line));
  assert.ok(line.indexOf('provisioned!==false') !== -1,
    'the attestation does not require a provisioned server -- an unprovisioned one '
    + 'leaves the pending list empty because nothing was even attempted');
  assert.ok(line.indexOf('bldPendingCount()===0') !== -1,
    'the attestation does not require the retry to have left the list EMPTY, which '
    + 'is the whole thing it is attesting');
});

// ═══════════════════════════════════════════════════════════════════════════
section('5. the attestation, DRIVEN -- what it grants and what it refuses');
// Every arm above reads the attestation as TEXT. These run it. The finding
// that made them necessary: the line contained `bldPendingCount()===0`, every
// source-text arm passed, and the flag was still granted on a device that had
// pushed nothing -- because an EMPTY pending list and a list that was NEVER
// WRITTEN are the same count.

test('THE FINDING: a NEVER-WRITTEN pending list does not earn trust', () => {
  // The pre-2026-09-04 device this whole design is reasoned about. Its
  // bld_sync_pending key does not exist, so the retry pushes nothing and the
  // count is zero -- and zero here means "no record of anything", not
  // "everything landed".
  const c = harness({ local: { [K]: [{ id: 'J-1', note: 'EDITED HERE, never pushed' }] } });
  assert.strictEqual(c.bldPendingRead().state, 'absent', 'the fixture is not the case being tested');
  c.attest(true);
  assert.strictEqual(c.bldPendingTrusted(), false,
    'trust was granted on a device that has pushed NOTHING -- and the flag is never '
    + 'cleared, so from the first later failed write onward the merge overwrites edits '
    + 'the pending list has no record of because the mechanism postdates them');
});

test('...and the merge still refuses, which is why this was invisible', () => {
  // The delay that made it look fine. mayOverwrite also requires state==='ok',
  // a term that is there for an UNREADABLE map -- so on the first load nothing
  // is overwritten whether or not the flag was granted. That is the arm that
  // explains why a source-text check was not enough.
  const c = harness({ local: { [K]: [{ id: 'J-1', note: 'never pushed' }] } });
  c.attest(true);
  c.bldServerWinsMerge(K, [{ id: 'J-1', note: 'the server copy' }]);
  assert.strictEqual(c.local(K)[0].note, 'never pushed');
});

test('THE SEQUENCE: trust granted wrongly + the key appearing later = the edit is gone', () => {
  // Three steps, nothing unusual, and it is what this fix prevents. Driven
  // with the flag PRE-SET, which is the state the old code reached on load 1.
  const c = harness({
    local: { [K]: [{ id: 'J-1', note: 'EDITED HERE, never pushed' }] },
    pending: {},            // the key now exists -- any later failed write does this
    trusted: true,          // ...and the flag was already granted on load 1
  });
  c.bldServerWinsMerge(K, [{ id: 'J-1', note: 'the server copy' }]);
  assert.strictEqual(c.local(K)[0].note, 'the server copy',
    'this arm is meant to SHOW the loss, so if it stops it is the fixture that changed');
});

test('a list the retry really emptied DOES earn trust', () => {
  // The fix must not make the gate unearnable. An existing, empty list is the
  // honest attestation and it still works.
  const c = harness({ local: { [K]: [{ id: 'J-1' }] }, pending: {} });
  assert.strictEqual(c.bldPendingRead().state, 'ok');
  c.attest(true);
  assert.strictEqual(c.bldPendingTrusted(), true,
    'the gate is now unearnable -- a device that has pushed everything can never overwrite');
});

test('a list with something still stranded does NOT earn trust', () => {
  const c = harness({ local: { [K]: [{ id: 'J-1' }] }, pending: { [K]: ['J-1'] } });
  c.attest(true);
  assert.strictEqual(c.bldPendingTrusted(), false);
});

test('an UNPROVISIONED server does not earn trust, however empty the list', () => {
  const c = harness({ local: { [K]: [{ id: 'J-1' }] }, pending: {} });
  c.attest(false);
  assert.strictEqual(c.bldPendingTrusted(), false,
    'nothing was even attempted, so an empty list attests nothing');
});

test('a CORRUPT pending list does not earn trust either', () => {
  // state is 'unreadable', not 'ok'. Its count is zero for the same reason the
  // absent case's is, and it must fail closed for the same reason.
  const c = harness({ local: { [K]: [{ id: 'J-1' }] }, pending: 'corrupt' });
  assert.strictEqual(c.bldPendingRead().state, 'unreadable');
  c.attest(true);
  assert.strictEqual(c.bldPendingTrusted(), false);
});

test('bld_bids is tracked for pending at BOTH of its explicit write sites', () => {
  // It is not in BLD_SYNCED and so gets nothing from st()'s hook. Converting
  // its hydrate without this would give it a carve-out that is always empty.
  assert.ok(html.indexOf("BLD_PENDING_TRACKED['bld_bids'] = true;") !== -1,
    'bld_bids is not tracked, so its hydrate has no carve-out at all');
  const marks = (html.match(/bldPendingMark\('bld_bids'/g) || []).length;
  const clears = (html.match(/bldPendingClear\('bld_bids'/g) || []).length;
  assert.strictEqual(marks, 2, 'expected a pending mark at both bld_bids write sites, found ' + marks);
  assert.strictEqual(clears, 2, 'expected a pending clear at both bld_bids write sites, found ' + clears);
});

test('the retry covers bld_bids too, with the session its branch demands', () => {
  const body = fn('bldRetryPending');
  assert.ok(body.indexOf('BLD_PENDING_TRACKED[key]') !== -1,
    'the retry still filters on _bldSyncOn, so a pending bld_bids is never retried');
  assert.ok(body.indexOf("key==='bld_bids'") !== -1,
    'the retry sends bld_bids without a session, which its branch refuses');
});

// ═══════════════════════════════════════════════════════════════════════════
(async () => {
  for (const item of queue) {
    if (item.section) { console.log('--- ' + item.section + ' ---'); continue; }
    try { await item.fn(); console.log('  ok   ' + item.name); pass++; }
    catch (e) { console.log('  FAIL ' + item.name + '\n       ' + e.message); fail++; }
  }
  console.log('\nsairnbuild_server_wins: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
