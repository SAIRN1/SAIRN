// tests/sairndesign_server_backup.js
//
// Run:  node tests/sairndesign_server_backup.js
//
// SAIRNDESIGN'S FIRST DEDICATED SUITE. docs/MASTER-PLAN.md measured three
// verticals with no file named for them at all; this is the second of the three
// to be closed.
//
// WHAT IT GUARDS: the three sides that must agree for a backup to be real and
// that drift silently when they do not -- api/_resources/sairndesign.js
// registers a name, sairndesign.html decides what to push, and
// sql/sairndesign_data_schema.sql has to have a table. Two of three agreeing is
// exactly how drift hides.
//
// AND THE TIER A RESOURCES BY NAME. docs/CRITICALITY-TIERS.md tiers this app's
// `sdn_invoices` and `sdn_discounts` as A -- money. A pairwise count cannot see
// one of those vanishing from all three lists at once, because the three would
// then agree perfectly with each other. The by-name section is the only thing
// that can, and it is tied to the tier register rather than to a list invented
// here, so the two cannot drift apart.
//
// NOT COVERED, said plainly: no live write is made from here. This is a
// source-agreement suite. A real round trip needs a provisioned SAIRNdesign
// licence, and whether sql/sairndesign_data_schema.sql has actually been run is
// UNVERIFIED as of 2026-09-10 -- see the gate 1 section of docs/MASTER-PLAN.md.

const fs = require('fs');
const path = require('path');
const assert = require('assert');

const ROOT = path.join(__dirname, '..');
const HTML = fs.readFileSync(path.join(ROOT, 'sairndesign.html'), 'utf8').replace(/\r\n/g, '\n');
const SCHEMA = fs.readFileSync(path.join(ROOT, 'sql', 'sairndesign_data_schema.sql'), 'utf8');
const TIERS = fs.readFileSync(path.join(ROOT, 'docs', 'CRITICALITY-TIERS.md'), 'utf8');
const REG = require(path.join(ROOT, 'api', '_resources', 'sairndesign.js'));

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

function schemaTables() {
  return (SCHEMA.match(/create table (?:if not exists )?public\.(\w+)/gi) || [])
    .map((s) => s.split('.').pop().toLowerCase());
}

// ── TIER A IS READ FROM THE REGISTER'S OWN SECTION, NOT FROM THE REGISTRY ──
// The first version filtered REG.resources by their tier, which meant the
// by-name guard could be switched off by the very change it exists to catch:
// remove a resource from the registry and its own assertion stops running.
// The fault probe found that on its first real run -- the arm that drops a
// Tier A money resource from all three sides reported NO failure, because the
// test for it had quietly stopped existing.
//
// docs/CRITICALITY-TIERS.md is now the independent source. Its rows are grouped
// under `### \`<app>\` — N resources`, so the section is sliced by heading and
// every Tier A row in it is asserted to be registered, referenced and backed by
// a table. Removing the resource from the registry now FAILS rather than
// vanishing.
function tierA(app) {
  const at = TIERS.indexOf('### `' + app + '`');
  assert.ok(at > 0, 'docs/CRITICALITY-TIERS.md has no section for ' + app
    + ' -- read the register before relaxing this');
  const next = TIERS.indexOf('\n### ', at + 1);
  const block = TIERS.slice(at, next === -1 ? TIERS.length : next);
  return block.split('\n')
    .filter((l) => /^\| `[\w.-]+` \| \*\*A\*\* \|/.test(l))
    .map((l) => l.split('`')[1]);
}

console.log('sairndesign -- registry, client and schema must agree');

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

test('the registry still holds exactly 18 resources', () => {
  assert.strictEqual(REG.resources.length, 18,
    'the sairndesign registry has ' + REG.resources.length + ' resources, not 18 -- if that is deliberate, change this number in the same commit; if it is not, a resource has been removed and every per-resource assertion in this file went with it');
});

test('the registry is non-empty and every name carries the sdn_ prefix', () => {
  assert.ok(REG.resources.length > 0, 'the registry has no resources');
  // The registry's own comment says why: a bare `schedule`/`invoices` would
  // collide with names already claimed by other apps in the shared handler.
  const bare = REG.resources.filter((r) => !/^sdn_[a-z_]+$/.test(r));
  assert.deepStrictEqual(bare, [],
    'names without the sdn_ prefix -- the registry says these would collide: ' + bare);
});

test('registry vs SCHEMA: every registered resource has a table', () => {
  const t = new Set(schemaTables());
  const missing = REG.resources.filter((r) => !t.has(r));
  assert.deepStrictEqual(missing, [],
    'registered with no table -- every write to these answers 503 NOT_PROVISIONED: ' + missing);
});

test('SCHEMA vs registry: every table is reachable', () => {
  const reg = new Set(REG.resources);
  const orphan = schemaTables().filter((x) => !reg.has(x));
  assert.deepStrictEqual(orphan, [],
    'tables nothing can write -- a migration that provisioned dead storage: ' + orphan);
});

test('registry vs CLIENT: every registered resource is named in the app', () => {
  const never = REG.resources.filter((r) => HTML.indexOf("'" + r + "'") === -1);
  assert.deepStrictEqual(never, [],
    'registered and never referenced by the app -- cover the registry claims and does '
    + 'not have: ' + never);
});

section('2. the TIER A resources are asserted BY NAME');

// Tied to docs/CRITICALITY-TIERS.md so the two cannot drift: if a resource is
// promoted to A there, it is asserted here without anyone remembering to.
test('the tier register still names Tier A resources for this app', () => {
  assert.ok(tierA('sairndesign').length > 0,
    'no Tier A resource found for sairndesign in docs/CRITICALITY-TIERS.md -- either '
    + 'the register changed shape or this app was re-tiered; read it before relaxing this');
});

tierA('sairndesign').forEach((r) => {
  test('`' + r + '` (Tier A) is registered, referenced and has a table', () => {
    assert.ok(REG.resources.includes(r), r + ' is not registered');
    assert.ok(HTML.indexOf("'" + r + "'") !== -1, r + ' is never referenced by the app');
    assert.ok(schemaTables().includes(r), r + ' has no table');
  });
});

section('3. the storage wrapper still reports failure');

test('st() exists and its failure path says the write FAILED', () => {
  // The platform-wide guard is tests/st_reports_failure.js; this asserts the
  // app-local half so a SAIRNdesign-only regression is named here rather than
  // surfacing as a platform count.
  assert.ok(/function st\(/.test(HTML), 'st() is gone from sairndesign.html');
  assert.ok(/FAILED/.test(HTML),
    'nothing in the file reports a failed write -- a refused write would be silent');
});

console.log('\n' + (fail ? 'FAILED' : 'ok') + '  sairndesign_server_backup: '
  + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
