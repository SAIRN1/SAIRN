// tests/sairnfreedom_server_backup.js
//
// Run:  node tests/sairnfreedom_server_backup.js
//
// SAIRNFREEDOM'S FIRST DEDICATED SUITE. Until 2026-09-10 it had none --
// docs/MASTER-PLAN.md measured three verticals with no file named for them at
// all, and this app was the worst of the three: 35 registered resources
// reaching a server, and no fault probe either.
//
// WHAT IT GUARDS, and why these and not a broader sweep of the app: the three
// sides that must agree for a backup to be real, and that drift silently when
// they do not. api/_resources/sairnfreedom.js registers a name, the client
// decides what to push, and sql/sairnfreedom_data_schema.sql has to have a
// table for it. Two of three agreeing is exactly how drift hides -- the
// StoneDesk suite says so in the same words and checks the same way.
//
// AND THE ORC 2915 SIDE IS ASSERTED BY NAME. The registry's own header says
// why this app got a server at all: "membership, the ledger, gaming sessions,
// gaming expenses and CHARITABLE DISBURSEMENTS -- the ORC 2915 reportable side
// of a fraternal post's gaming -- lived in one browser." A registry that
// silently lost sf_disbursements would still pass a pairwise count. It would
// not pass this.
//
// NOT COVERED, said plainly rather than implied: no live write is made from
// here. This is a source-agreement suite. A real round trip needs a
// provisioned SAIRNfreedom licence, and sql/sairnfreedom_license_seed.sql was
// confirmed run on 2026-09-10 -- so the round trip is now possible and is a
// separate piece of work.

const fs = require('fs');
const path = require('path');
const assert = require('assert');

const ROOT = path.join(__dirname, '..');
const HTML = fs.readFileSync(path.join(ROOT, 'sairnfreedom.html'), 'utf8').replace(/\r\n/g, '\n');
const SCHEMA = fs.readFileSync(path.join(ROOT, 'sql', 'sairnfreedom_data_schema.sql'), 'utf8');
const REG = require(path.join(ROOT, 'api', '_resources', 'sairnfreedom.js'));

let pass = 0;
let fail = 0;

function test(name, fn) {
  try {
    fn();
    pass += 1;
    console.log('  ok   - ' + name);
  } catch (e) {
    fail += 1;
    console.log('  FAIL - ' + name + '\n         ' + (e && e.message));
  }
}
function section(t) { console.log('\n' + t); }

// The client's own list, read from the file rather than restated here -- a
// hand-copied list in a test is a fourth thing to drift.
function clientSynced() {
  const at = HTML.indexOf('var SF_SYNCED=');
  assert.ok(at > 0, 'SF_SYNCED is gone from sairnfreedom.html');
  const block = HTML.slice(at, HTML.indexOf('];', at));
  return (block.match(/'(sf_[a-z_]+)'/g) || []).map((s) => s.replace(/'/g, ''));
}

function schemaTables() {
  return (SCHEMA.match(/create table (?:if not exists )?public\.(\w+)/gi) || [])
    .map((s) => s.split('.').pop());
}

console.log('sairnfreedom -- registry, client and schema must agree');

section('1. the three sides agree, PAIRWISE');


// ── THE COUNT IS PINNED, NOT JUST CHECKED FOR BEING NON-EMPTY (2026-09-10) ──
// `length > 0` is blind to the defect that matters here: a resource REMOVED
// from the registry takes its own per-resource assertions with it, because
// every loop in this file iterates the registry. That is the self-referential
// hole the fault probe found in the by-name section, and the platform sweep
// that followed showed every other derived-subject suite on the platform
// already pins a count -- these three were the exception because they were the
// newest.
//
// The number is deliberate and must be changed BY HAND when a resource is
// genuinely added or removed. That edit is the point: it makes the change
// visible in a diff instead of silently shrinking the test surface.

test('the registry still holds exactly 35 resources', () => {
  assert.strictEqual(REG.resources.length, 35,
    'the sairnfreedom registry has ' + REG.resources.length + ' resources, not 35 -- if that is deliberate, change this number in the same commit; if it is not, a resource has been removed and every per-resource assertion in this file went with it');
});

test('the registry is non-empty and every name is an sf_ key', () => {
  assert.ok(REG.resources.length > 0, 'the registry has no resources');
  const odd = REG.resources.filter((r) => !/^sf_[a-z_]+$/.test(r));
  assert.deepStrictEqual(odd, [], 'resource names that are not sf_ storage keys: ' + odd);
});

test('registry vs SCHEMA: every registered resource has a table', () => {
  const tables = new Set(schemaTables());
  const missing = REG.resources.filter((r) => !tables.has(r));
  assert.deepStrictEqual(missing, [],
    'registered with no table -- every write to these answers 503 NOT_PROVISIONED: ' + missing);
});

test('SCHEMA vs registry: every table is reachable', () => {
  const reg = new Set(REG.resources);
  const orphan = schemaTables().filter((t) => !reg.has(t));
  assert.deepStrictEqual(orphan, [],
    'tables nothing can write -- a migration that provisioned dead storage: ' + orphan);
});

test('registry vs CLIENT: every registered resource is actually pushed', () => {
  const synced = new Set(clientSynced());
  const never = REG.resources.filter((r) => !synced.has(r));
  assert.deepStrictEqual(never, [],
    'registered and never sent -- the registry claims cover it does not have: ' + never);
});

test('CLIENT vs registry: the client pushes nothing unregistered', () => {
  const reg = new Set(REG.resources);
  const unreg = clientSynced().filter((k) => !reg.has(k));
  assert.deepStrictEqual(unreg, [],
    'pushed but unregistered -- these get a scoped 400 and look like a network fault: ' + unreg);
});

section('2. the ORC 2915 reportable side is registered BY NAME');

// A pairwise count cannot see this: drop sf_disbursements from all three and
// every test above still passes. The registry's own header states these five
// as the reason the app got a server, so they are asserted individually.
[
  ['sf_members', 'membership'],
  ['sf_ledger', 'the ledger'],
  ['sf_sessions', 'gaming sessions'],
  ['sf_gaming_expenses', 'gaming expenses'],
  ['sf_disbursements', 'charitable disbursements'],
].forEach(([key, what]) => {
  test('`' + key + '` (' + what + ') reaches a server', () => {
    assert.ok(REG.resources.includes(key), key + ' is not registered');
    assert.ok(clientSynced().includes(key), key + ' is registered but never pushed');
    assert.ok(schemaTables().includes(key), key + ' has no table');
  });
});

section('3. the backup hook cannot fail silently');

test('st() delegates its backup failure to a NAMED reporter', () => {
  // Fixed 2026-09-10: the hook's console.error sat inline in st() behind its own
  // logger guard, which made a SECOND bare catch in a wrapper the platform-wide
  // suite pins at one. The two failures say different things -- the record was
  // NOT saved versus it WAS saved and only the backup threw -- and collapsing
  // them tells somebody their work was lost when it was not.
  assert.ok(/function sfBackupHookFailed\(/.test(HTML),
    'sfBackupHookFailed() is gone -- the backup failure has no named reporter');
  assert.ok(/catch\(e2\)\{ sfBackupHookFailed\(k, e2\); \}/.test(HTML),
    'st() no longer delegates to it');
});

test('the two failures still say DIFFERENT things', () => {
  const at = HTML.indexOf('function sfBackupHookFailed(');
  const body = HTML.slice(at, at + 400);
  assert.ok(/IS saved on this device/.test(body),
    'the backup-failure message no longer says the record WAS saved');
  assert.ok(/localStorage write FAILED/.test(HTML),
    'the write-failure message is gone');
});

section('4. the sync hook is keyed off the storage key, as the registry says');

test('SF_SYNCED_ON is derived from SF_SYNCED, not hand-listed', () => {
  assert.ok(/SF_SYNCED\.forEach\(function\(k\)\{ SF_SYNCED_ON\[k\]=true; \}\);/.test(HTML),
    'SF_SYNCED_ON is no longer derived -- a hand-kept second list is a fourth thing to drift');
});

test('sfData is the only sd-data caller in the file', () => {
  const calls = (HTML.match(/SF_DATA_API/g) || []).length;
  assert.ok(calls >= 2, 'SF_DATA_API is gone');
  const fetches = (HTML.match(/fetch\(SF_DATA_API/g) || []).length;
  assert.strictEqual(fetches, 1,
    'more than one place calls sd-data directly -- the registry header says there is one');
});

section('5. hydration cannot leave the backup suppressed for the session');

test('every sfSyncSuppressed=true is released in a finally', () => {
  // ── THE THIRD COPY OF ONE BUG, 2026-09-14 (item 34) ────────────────────
  // sairnvet fixed this shape TWICE on 2026-09-10 and wrote the rule into
  // svSeedStore(): "a throw inside a saver must not leave the whole app's
  // backup suppressed for the rest of the session." stonedesk fixed it on
  // 2026-09-14. Nobody looked here either time, and this app carried the leak
  // for four more days. It was found by a checker, not by a reader.
  //
  // WORSE HERE, same as in sairnvet: sfHydrateAll's enclosing
  // `.catch(function(){})` swallows the throw, so the failure is invisible and
  // every later save is silently un-backed-up.
  //
  // ASSERTED AS A COUNT, not on one line, so a FOURTH site added later without
  // a finally fails this rather than sliding past a fixed anchor.
  const ons = (HTML.match(/^\s*sfSyncSuppressed\s*=\s*true\s*;/gm) || []).length;
  const finallys = (HTML.match(/finally\s*\{\s*sfSyncSuppressed\s*=/g) || []).length;
  assert.ok(ons > 0, 'the suppression flag is gone -- this arm now tests nothing');
  assert.strictEqual(finallys, ons,
    'a site sets sfSyncSuppressed and does NOT release it in a finally ('
    + finallys + ' finally of ' + ons + ' set) -- a throw there silences every '
    + 'later save for the rest of the session');
});

test('the release restores the PREVIOUS value, not a bare false', () => {
  // `=false` in a nested call un-suppresses its caller. sairnvet's svSeedStore
  // uses a bare false and is correct there because nothing nests inside it;
  // this site is inside a per-key promise map, so it saves and restores.
  //
  // RE-ANCHORED 2026-09-21. The suppression used to be written INLINE inside
  // sfHydrateAll(), as `var wasSuppressed=...` around a bare st(). Server-wins
  // moved the merge into the shared sfServerWinsMerge(), so the suppression
  // moved with it into the named seam sfHydrateStore() -- which is the whole
  // point of that seam existing. The PROPERTY is unchanged and is still
  // asserted; only the place it lives moved, and the anchor moved with it
  // rather than the arm being deleted for going red.
  assert.ok(/function sfHydrateStore\(key,value\)\{/.test(HTML),
    'the store seam is gone -- the suppression has no home');
  assert.ok(/var was=sfSyncSuppressed;/.test(HTML),
    'the previous value is no longer captured');
  assert.ok(/finally \{ sfSyncSuppressed=was; \}/.test(HTML),
    'the release no longer restores the captured value');
});

console.log('\n' + (fail ? 'FAILED' : 'ok') + '  sairnfreedom_server_backup: '
  + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
