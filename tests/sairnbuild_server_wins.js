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

// ── TWO VIEWS OF THE SOURCE, AND THE REASON THERE ARE TWO ─────────────────
// EVERY SUBSTRING ASSERTION IN THIS FILE HAS BEEN SATISFIED AT LEAST ONCE BY
// TEXT THAT DOES NOT EXECUTE. That is not a worry, it is a register, and each
// entry was MEASURED BY ABLATION rather than noticed by reading:
//
//   b17   `key==='bld_bids'` satisfied by a COMMENT inside the very function
//         under test, explaining that the code "used to read" it
//   b27   a fourth argument satisfied by a BLOCK comment, because the repair
//         stripped only `//` lines; and by a FALSY literal, which is the
//         arm's own defect wearing an argument
//   b27r  the verb 'write' invisible once string literals were collapsed, so
//         the retry could be changed to 'read' and the arm stayed green
//   b28   `BLD_PENDING_TRACKED['bld_bids'] = true;` satisfied by a LINE
//         comment carrying it (N1) and the retry guard by a BLOCK comment
//         (N4) -- so bld_bids could lose its pending tracking ENTIRELY with
//         the suite at 25 passed, 0 failed. Routed by fourth b28 check 4 HIGH
//   b23   and two more found while repairing those: a real bldPendingMark
//         call site deleted with a COMMENT carrying the literal (N5), and the
//         retry guard carried by a STRING LITERAL (N6). Both ACCEPTED at 25/0
//
// So the two views are not a style choice, and neither alone is enough:
//
//   code(s)    comments gone. Proves WHICH identifiers and string literals
//              are written -- including which string a call was passed.
//   struct(s)  comments gone AND every string collapsed to ''. Proves the
//              text is EXECUTABLE, because no comment and no string survives
//              to carry it -- but is blind to WHICH string it was.
//
// A mutation hiding code in a string satisfies code() and fails struct(); a
// mutation changing a verb satisfies struct() and fails code(). Every
// assertion below states which view it uses and which mutation that closes.
//
// SCOPE IS ALWAYS A BOUNDED WINDOW, NEVER THE WHOLE FILE, and that is the
// second half of the repair. `html.indexOf(...)` over 400KB answers "does
// this text occur anywhere", which is a question no property of this app
// depends on -- it was the shape of N1, N4 and N5 together. It is also
// unsafe to strip: a naive comment stripper over a whole app blanks URLs
// inside strings and regex literals, which is a measured false-finding source
// on this platform (Guardian check 27, 58 phantom findings). Over a function
// body or a two-statement declaration window there is nothing to get wrong.
function code(s) {
  return s.replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/\/\/[^\n]*/g, ' ');
}
function struct(s) {
  return code(s)
    .replace(/'(?:[^'\\\n]|\\.)*'/g, "''")
    .replace(/"(?:[^"\\\n]|\\.)*"/g, '""');
}

// The session flag as a WHOLE fourth argument: the map read, optionally `!!`,
// then the call's closing `)`. Nothing may precede it (`!`, `false&&`) and
// nothing may follow it inside the argument. fourth b68.
const SESSION_FLAG_ARG = '\\s*(?:!!\\s*)?BLD_SESSION_REQUIRED\\s*\\[\\s*key\\s*\\]\\s*\\)';

// The window between two NAMED, UNIQUE declarations. FAILS CLOSED: if either
// anchor is absent, occurs more than once, or they have swapped order, this
// throws rather than returning a slice that would make the arms vacuous.
function windowBetween(startAnchor, endAnchor) {
  const nS = html.split(startAnchor).length - 1;
  const nE = html.split(endAnchor).length - 1;
  assert.strictEqual(nS, 1, 'window start anchor ' + JSON.stringify(startAnchor)
    + ' occurs ' + nS + ' times, expected exactly 1 -- re-anchor rather than '
    + 'letting this slice some other region');
  assert.strictEqual(nE, 1, 'window end anchor ' + JSON.stringify(endAnchor)
    + ' occurs ' + nE + ' times, expected exactly 1');
  const a = html.indexOf(startAnchor);
  const b = html.indexOf(endAnchor, a);
  assert.ok(b > a, 'the window end anchor ' + JSON.stringify(endAnchor)
    + ' does not follow the start anchor -- the declarations have been '
    + 'reordered and this window would be empty or inverted');
  return html.slice(a, b);
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
  //
  // ── THIS WHOLE ARM WAS A WHOLE-FILE SUBSTRING PROXY. 2026-10-19, b23,
  //    ROUTED BY fourth b28 CHECK 4 AS HIGH AND REPRODUCED BY ABLATION ────
  // THE CONCEPT, which is what the arm is actually checking: bld_bids is
  // ENROLLED IN PENDING TRACKING BY EXECUTABLE CODE, and both of its write
  // sites really call mark and clear -- not merely that those spellings occur
  // somewhere in a 400KB file.
  //
  // What it read before, and what each line let through:
  //
  //   html.indexOf("BLD_PENDING_TRACKED['bld_bids'] = true;")
  //     N1  the real statement replaced by `// BLD_PENDING_TRACKED[...]`
  //         ACCEPTED, 25 passed 0 failed. The comment satisfied it.
  //   html.match(/bldPendingMark\('bld_bids'/g).length === 2
  //     N5  one of the two real call sites deleted and a COMMENT left
  //         carrying both spellings. Count still 2. ACCEPTED, 25/0.
  //
  // Controls, so the above is attributable and not an artefact of a copy that
  // cannot run: N2 the statement DELETED -> REFUSED; N3 flipped to `false`
  // -> REFUSED. Both already bit, which is exactly why the hole was invisible
  // -- the arm caught the careless mutations and missed the plausible ones.
  //
  // THE WINDOW IS THE ENROLMENT BLOCK, bounded by two named unique
  // declarations, and windowBetween() fails closed if either moves.
  const enrol = windowBetween('var BLD_PENDING_TRACKED', 'var BLD_SESSION_REQUIRED');
  // (A) the key: which resource is enrolled, and to what. code() keeps string
  //     literals so 'bld_bids' is still visible. Closes N1 and N3.
  assert.ok(/BLD_PENDING_TRACKED\s*\[\s*'bld_bids'\s*\]\s*=\s*true\s*;/.test(code(enrol)),
    'bld_bids must be enrolled in BLD_PENDING_TRACKED by an EXECUTABLE '
    + 'assignment to true, or its hydrate has no carve-out at all. A comment '
    + 'carrying this statement satisfied the previous form of this assertion '
    + 'at 25 passed, 0 failed. Window was: ' + code(enrol).slice(0, 300));
  // (B) executable: no comment and no string survives struct(), so whatever
  //     matches here is real code. 'bld_bids' collapses to '' -- that is the
  //     blindness (A) exists to cover, and the pair is the point.
  assert.ok(/BLD_PENDING_TRACKED\s*\[\s*''\s*\]\s*=\s*true\s*;/.test(struct(enrol)),
    'the enrolment must survive stripping comments AND collapsing every '
    + 'string literal -- i.e. it must be code rather than text');

  // THE CALL SITES ARE COUNTED INSIDE THEIR OWN FUNCTIONS, not across the
  // file. That is strictly stronger than the count it replaces: it proves the
  // calls are in the two functions that actually write a bid, where a
  // whole-file count of 2 is satisfied by any two occurrences anywhere --
  // including, as N5 measured, one real call and one comment.
  [['saveBid', 'the bid modal'], ['bldReassignBid', 'the table reassignment']]
    .forEach(([name, what]) => {
      const body = code(fn(name));
      const marks = (body.match(/bldPendingMark\(\s*'bld_bids'/g) || []).length;
      const clears = (body.match(/bldPendingClear\(\s*'bld_bids'/g) || []).length;
      assert.strictEqual(marks, 1, 'expected exactly one EXECUTABLE pending '
        + 'mark for bld_bids in ' + name + '() (' + what + '), found ' + marks
        + '. A failed push that is not marked is never retried and hydration '
        + 'does not know to protect it');
      assert.strictEqual(clears, 1, 'expected exactly one EXECUTABLE pending '
        + 'clear for bld_bids in ' + name + '() (' + what + '), found '
        + clears + '. Without it a successful push leaves the id on the list '
        + 'for ever, and the carve-out stops meaning anything');
    });
});

test('the retry covers bld_bids too, with the session its branch demands', () => {
  const body = fn('bldRetryPending');
  // ── N4 AND N6: THIS LINE WAS A RAW indexOf AND BOTH A COMMENT AND A STRING
  //    SATISFIED IT. 2026-10-19, b23 ─────────────────────────────────────
  // THE CONCEPT: the retry's per-key gate actually READS the tracking map in
  // executable code, so a key that is not enrolled is skipped -- not merely
  // that the spelling `BLD_PENDING_TRACKED[key]` appears in the body.
  //
  //   N4  the guard replaced by `/* was: if(!BLD_PENDING_TRACKED[key]||...) */
  //       if(!Array.isArray(o[key]))return;`     ACCEPTED, 25 passed 0 failed
  //   N6  the guard replaced by `var _n='BLD_PENDING_TRACKED[key]';
  //       if(!Array.isArray(o[key]))return;`     ACCEPTED, 25 passed 0 failed
  //
  // Together with N1 and N5 above, that is bld_bids losing its pending
  // tracking END TO END -- enrolment, both write sites and the retry gate --
  // with this suite green. fourth b28 measured the first two and routed it
  // HIGH without fixing it, correctly: tests/ is mine and a reviewer who
  // repairs what he reviews is the self-signed review the ledger prevents.
  //
  // BOTH VIEWS, because N4 needs comments gone and N6 needs strings gone.
  assert.ok(/!\s*BLD_PENDING_TRACKED\s*\[\s*key\s*\]/.test(code(body)),
    'bldRetryPending must GATE on BLD_PENDING_TRACKED[key] in executable '
    + 'code, or a pending bld_bids is never retried. Measured: a block '
    + 'comment carrying this expression satisfied the previous raw indexOf at '
    + '25 passed, 0 failed');
  assert.ok(/!\s*BLD_PENDING_TRACKED\s*\[\s*key\s*\]/.test(struct(body)),
    'the gate must survive collapsing every string literal -- i.e. it must '
    + 'be code and not a string. Measured: assigning the expression to a '
    + 'variable as a STRING satisfied the previous form at 25 passed, 0 failed');
  // ── THIS ASSERTION WAS PASSING ON A COMMENT. 2026-10-15 ───────────────
  // It read `body.indexOf("key==='bld_bids'") !== -1`. That expression is no
  // longer in bldRetryPending: sairnbuild.html:2369 declares
  // `var BLD_SESSION_REQUIRED = { bld_bids: true, bld_draws: true };` and the
  // retry passes `!!BLD_SESSION_REQUIRED[key]` instead -- a generalisation,
  // because bld_draws joined the set. The literal still occurs TWICE in the
  // file and BOTH occurrences are COMMENTS, one of them at :2534 INSIDE this
  // very function, written to explain that the old form "used to read
  // `key==='bld_bids'`, which was right until there were two."
  //
  // So the assertion was satisfied by the comment documenting the removal of
  // the thing it was asserting, and `tests/run_sairnbuild_server_wins_sabotage_probe.py`
  // arm 6 -- which plants exactly that defect by deleting the session flag --
  // reported SILENT once its own anchor was repaired on the same day. Two
  // layers of guard, neither of them guarding.
  //
  // THE PROPERTY, OVER COMMENT-STRIPPED SOURCE, AT THE CALL SITE. A fourth
  // argument must be passed to bldData() by the retry. Which expression
  // computes it is allowed to change; its absence is not, and a comment can
  // no longer satisfy it.
  // ── THE REPAIR ABOVE MOVED THE HOLE INSTEAD OF CLOSING IT. 2026-10-15,
  //    fourth b27, MEASURED BY ABLATION AND NOT BY READING ────────────────
  // The first version of this assertion was satisfied by a LINE comment. The
  // repair stripped line comments and then required SOME fourth argument:
  //
  //     body.replace(/\/\/[^\n]*/g, '')
  //     /bldData\('write',\s*key,\s*rec,\s*[^)\s][^)]*\)/
  //
  // Five mutations were applied to a COPY of sairnbuild.html and the suite was
  // re-run against each. FOUR OF THE FIVE WERE ACCEPTED:
  //
  //   M1 fourth argument DELETED .................. exit 1  REFUSED
  //   M2 fourth argument replaced by `false` ...... exit 0  ACCEPTED  <- same defect
  //   M3 fourth argument replaced by `0` .......... exit 0  ACCEPTED  <- same defect
  //   M4 the DECLARATION deleted, call sites kept . exit 0  ACCEPTED
  //   M5 real call broken, a BLOCK comment carries
  //      a satisfying one ......................... exit 0  ACCEPTED  <- a COMMENT again
  //
  // So cody's own question -- "can the new regex be satisfied by a future
  // comment or string literal the way its predecessor was" -- answers YES: by
  // a BLOCK comment, because the stripper only removed `//` lines. And a
  // FALSY fourth argument is the arm's own defect wearing an argument: the
  // branch in api/sd-data.js refuses a session-required write whose flag is
  // false exactly as it refuses one with no flag at all.
  //
  // THREE CHANGES, AND EACH CLOSES A NAMED MUTATION:
  //   (a) strip BLOCK comments and STRING LITERALS as well as line comments,
  //       so no text that is not executable can satisfy anything here (M5);
  //   (b) require the fourth argument to NAME BLD_SESSION_REQUIRED rather than
  //       merely to exist, which is the real object and is what makes a falsy
  //       literal fail (M2, M3);
  //   (c) assert the DECLARATION carries bld_bids, so the object the whole arm
  //       is about cannot be deleted out from under the call site (M4).
  // Which expression computes the flag is still allowed to change -- `!!`, a
  // helper call, a different coercion -- as long as it reads the map.
  //   ^ NARROWED 2026-10-29, fourth b68, discharging this obligation. "As long
  //   as it reads the map" admitted `!BLD_SESSION_REQUIRED[key]` and
  //   `false&&BLD_SESSION_REQUIRED[key]`: both READ the map and both send a
  //   FALSY flag for bld_bids. Measured, 26 passed 0 failed for each. The
  //   fourth argument must now be the map read and nothing else, optionally
  //   `!!`-coerced, closed by the call's `)` -- SESSION_FLAG_ARG below.
  //
  // ── AND THAT REPAIR OPENED ONE OF ITS OWN. 2026-10-16, fourth b27 resume,
  //    MEASURED BY A SECOND ABLATION OF THE REPAIR ITSELF ─────────────────
  // Ten mutations this time: M1-M5 again, plus five aimed at the shape of the
  // repair rather than its predecessor. Nine were refused. ONE WAS ACCEPTED:
  //
  //   M6 'write' -> 'read' at the retry call site . exit 0  ACCEPTED, 25/0
  //
  // Collapsing every string literal to '' is what closes M5 and M7, and it is
  // also what blinds the assertion to WHICH string the first argument was. So
  // the retry could be changed to READ instead of WRITE and this arm -- the arm
  // whose whole subject is the retry's write -- stayed green. That is the same
  // class of defect as the comment that started this, one layer further in.
  //
  // TWO COPIES, TWO ASSERTIONS, AND NEITHER ALONE IS ENOUGH:
  //   (A) comments stripped AND strings collapsed -- proves the call is real
  //       EXECUTABLE code, because no comment or string survives to carry it
  //       (M5, M7);
  //   (B) comments stripped ONLY -- proves the verb is 'write' and the cell is
  //       [key], which (A) cannot see once the strings are gone (M6, M9).
  // A mutation hiding the call in a string satisfies (B) and fails (A); a
  // mutation changing the verb satisfies (A) and fails (B).
  // The two inline strippers that used to live here are now code() and
  // struct() at the top of the file, unchanged in behaviour and shared with
  // the three assertions b23 repaired. CONSOLIDATED RATHER THAN COPIED, and
  // MEASURED rather than assumed safe: M1-M6 below were re-driven after the
  // move and every one of them is still REFUSED, which is the only thing that
  // makes replacing a working control acceptable.
  const noComments = code(body);
  const retryCode = struct(body);
  // (A) structural: it is executable code, not text.
  assert.ok(new RegExp("bldData\\(\\s*''\\s*,\\s*key\\s*,\\s*rec\\s*," + SESSION_FLAG_ARG)
    .test(retryCode),
    'the retry must pass the session flag READ FROM BLD_SESSION_REQUIRED. A '
    + 'fourth argument that merely exists is not enough: a falsy literal sends '
    + 'bld_bids without a session, which its branch refuses, and that is the '
    + 'defect this arm is named for');
  // (B) the verb: it is the WRITE that is being retried, not a read.
  assert.ok(new RegExp("bldData\\(\\s*'write'\\s*,\\s*key\\s*,\\s*rec\\s*," + SESSION_FLAG_ARG)
    .test(noComments),
    "the retried call must be the 'write' -- assertion (A) collapses every "
    + 'string literal to \'\' and therefore cannot tell \'write\' from '
    + "'read'. Measured: changing this call site to 'read' left the suite at "
    + '25 passed, 0 failed');
  // (c). Asserted on the DECLARATION, comment-stripped for the same reason.
  const sessMap = code(oneLineVar('BLD_SESSION_REQUIRED'));
  assert.ok(/\bbld_bids\s*:\s*true\b/.test(sessMap),
    'BLD_SESSION_REQUIRED must still carry bld_bids: true, or the call site '
    + 'above reads undefined and sends no session while still mentioning the '
    + 'map. Found: ' + sessMap);
});

test('bld_draws carries its session requirement too -- the arm the map gained a second member without', () => {
  // ── THE CONCEPT, stated before this arm was written ───────────────────────
  // bld_draws is a MEMBER of BLD_SESSION_REQUIRED with a TRUTHY value in the
  // real declaration, so the one shared call-site expression
  // `!!BLD_SESSION_REQUIRED[key]` sends an employee session for a draw write
  // -- the identical property bld_bids already had an arm for, asserted over
  // comment-stripped source so no comment can supply it.
  //
  // ── WHY IT DID NOT EXIST, WHICH IS THE PART WORTH KEEPING ────────────────
  // THE GENERALISATION THAT FIXED ONE DEFECT CREATED THIS GAP. bld_bids'
  // session requirement used to be spelled `key==='bld_bids'` inline. When
  // bld_draws joined, that was correctly replaced by a MAP read at three call
  // sites -- and the arm guarding it was updated to follow the map, but only
  // ever for the member it was originally written about. So the suite guarded
  // one of two members of a set whose whole purpose is to be extended.
  //
  // MEASURED, fourth b28 check 2, reproduced here before the fix:
  //   D1  bld_draws: true -> false ............ ACCEPTED, 25 passed 0 failed
  //   D3  bld_draws dropped from the map ...... ACCEPTED, 25 passed 0 failed
  //   D4  real entry removed, a COMMENT carries
  //       `bld_draws: true` ................... ACCEPTED, 25 passed 0 failed
  //   D2  bld_bids: true -> false (CONTROL) ... REFUSED, named arm red
  // D2 refusing is what makes D1 a finding rather than a broken copy: the
  // same mutation on the other member of the same object was caught.
  //
  // fourth called this "the same shape as b26's law_bankstatements finding",
  // and the reusable form is: WHEN A CONDITION BECOMES A SET, THE ARM MUST
  // ITERATE THE SET. An arm naming one member is not a weaker guard, it is a
  // guard that silently stops covering every member added after it.
  //
  // SO THIS ARM ITERATES rather than naming bld_draws a second time. A third
  // resource joining the map gets covered on the day it is added, which is
  // the only form of this arm that cannot recreate the gap it closes.
  const sessMap = code(oneLineVar('BLD_SESSION_REQUIRED'));
  const members = (sessMap.match(/\b(bld_[a-z_]+)\s*:/g) || [])
    .map((m) => m.replace(/\s*:$/, ''));
  // PRECONDITION, a third state and never folded into a pass: if the map
  // cannot be read as a set, nothing below asserted anything.
  assert.ok(members.length >= 2, 'BLD_SESSION_REQUIRED must parse as a set of '
    + 'at least the two resources whose branches demand an employee session. '
    + 'Read ' + members.length + ' member(s) from: ' + sessMap);
  assert.ok(members.indexOf('bld_draws') !== -1, 'bld_draws must be a MEMBER '
    + 'of BLD_SESSION_REQUIRED in executable code. Measured: dropping it, and '
    + 'separately leaving only a comment carrying it, both left this suite at '
    + '25 passed, 0 failed -- a draw write would then be sent with no '
    + 'employee session and refused by its own branch, and the retry would '
    + 'keep re-sending it. Members found: ' + members.join(', '));
  // EVERY member, truthy, in real code. This is the half that closes D1 and
  // D3 for a resource nobody has added yet.
  members.forEach((key) => {
    assert.ok(new RegExp('\\b' + key + '\\s*:\\s*true\\b').test(sessMap),
      key + ' is a member of BLD_SESSION_REQUIRED but is not set to true. '
      + '`!!BLD_SESSION_REQUIRED[key]` then sends false, and api/sd-data.js '
      + 'refuses a session-required write with a false flag exactly as it '
      + 'refuses one with no flag at all. Found: ' + sessMap);
  });
  // And the call sites read the MAP rather than naming a resource, which is
  // what makes iterating it meaningful: an arm over the set is worthless if
  // some site still hardcodes one member. struct() so a comment or string
  // mentioning the map cannot stand in for a read.
  //
  // ── 2026-10-29, fourth b68: THIS LOOP CHECKED ONE FUNCTION OF THREE ─────
  // It named bldRetryPending and bldHydrateOne. bldHydrateOne does not exist
  // in sairnbuild.html (0 occurrences), fn() threw, the catch turned that into
  // `return` -- under a comment saying absence is not a pass -- and a function
  // that stopped mentioning the map at all also returned. The real call sites
  // are bldSyncCollection (the write), bldRetryPending and bldHydrateAll (the
  // read). Measured before this change: dropping or negating the flag at the
  // write or the read left this suite AND sairnbuild_backup_pending.js green.
  // Every name is now REQUIRED to exist, and each must make a bldData call
  // whose fourth argument is SESSION_FLAG_ARG.
  ['bldSyncCollection', 'bldRetryPending', 'bldHydrateAll'].forEach((name) => {
    const s = struct(fn(name));
    assert.ok(new RegExp("bldData\\(\\s*''\\s*,\\s*key\\s*,\\s*\\w+\\s*," + SESSION_FLAG_ARG).test(s),
      name + '() must call bldData with the session flag read from '
      + 'BLD_SESSION_REQUIRED[key] as its whole fourth argument. A dropped, '
      + 'negated or short-circuited flag sends bld_bids and bld_draws without '
      + 'the employee session their api/sd-data.js branches demand');
  });
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
