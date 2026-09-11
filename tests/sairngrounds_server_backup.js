// tests/sairngrounds_server_backup.js
//
// Run:  node tests/sairngrounds_server_backup.js
//
// SAIRNGROUNDS' FIRST DEDICATED SUITE -- the last of the three verticals
// docs/MASTER-PLAN.md measured with no file named for them at all.
//
// WHAT IT GUARDS: registry, schema and client must agree, across THREE schema
// files (`sairngrounds_data_schema.sql`, `..._phase2.sql`, `..._caddie_schema
// .sql`). Two of three agreeing is how drift hides, and a third schema file is
// one more place for a table to be added that nothing can reach.
//
// ── THE FOUR ALIASES ARE DECLARED, NOT ABSORBED ─────────────────────────────
// Four resources are registered under BARE names -- `jobs`, `quotes`,
// `properties`, `golf_zones` -- while their tables carry the `grd_` prefix. A
// naive equality check reports four missing tables and four orphaned tables,
// which is eight false findings, and that is the blind-spot class
// `sairn-portfolio-triage` has an entire section about.
//
// It is deliberate: `api/sd-data.js:2288` maps `jobs` to `grd_jobs` explicitly,
// and the RESOURCES comment at :3007 says the bare names exist "specifically to
// avoid the collision noted above". So the aliases are LISTED here. A fifth one
// added later fails this suite rather than being silently absorbed by a looser
// rule -- which is the whole difference between a mapping and an exception.
//
// AND THE TIER A RESOURCES BY NAME, read from docs/CRITICALITY-TIERS.md rather
// than restated, so the two cannot drift.
//
// NOT COVERED: no live write is made from here. Whether any SAIRNgrounds
// migration has actually been run is UNVERIFIED as of 2026-09-10 -- see gate 1
// in docs/MASTER-PLAN.md.

const fs = require('fs');
const path = require('path');
const assert = require('assert');

const ROOT = path.join(__dirname, '..');
const HTML = fs.readFileSync(path.join(ROOT, 'sairngrounds.html'), 'utf8').replace(/\r\n/g, '\n');
const TIERS = fs.readFileSync(path.join(ROOT, 'docs', 'CRITICALITY-TIERS.md'), 'utf8');
const REG = require(path.join(ROOT, 'api', '_resources', 'sairngrounds.js'));

const SCHEMA_FILES = [
  'sairngrounds_data_schema.sql',
  'sairngrounds_data_schema_phase2.sql',
  'sairngrounds_caddie_schema.sql',
];

// Resource name -> table name, where they differ. Every entry is a real mapping
// in api/sd-data.js, not a convenience for this test.
const ALIAS = {
  jobs: 'grd_jobs',
  quotes: 'grd_quotes',
  properties: 'grd_properties',
  golf_zones: 'grd_golf_zones',
};

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
  const out = [];
  SCHEMA_FILES.forEach((f) => {
    const s = fs.readFileSync(path.join(ROOT, 'sql', f), 'utf8');
    (s.match(/create table (?:if not exists )?public\.(\w+)/gi) || [])
      .forEach((m) => out.push(m.split('.').pop().toLowerCase()));
  });
  return out;
}

const tableFor = (r) => ALIAS[r] || r;

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

console.log('sairngrounds -- registry, client and three schema files must agree');

section('1. every schema file is read, not just the first');

test('all three schema files exist', () => {
  SCHEMA_FILES.forEach((f) => {
    assert.ok(fs.existsSync(path.join(ROOT, 'sql', f)), f + ' is gone');
  });
});

section('2. the three sides agree, PAIRWISE, through the declared aliases');

test('registry vs SCHEMA: every registered resource has a table', () => {
  const t = new Set(schemaTables());
  const missing = REG.resources.filter((r) => !t.has(tableFor(r)));
  assert.deepStrictEqual(missing, [],
    'registered with no table -- every write to these answers 503 NOT_PROVISIONED: ' + missing);
});

test('SCHEMA vs registry: every table is reachable', () => {
  const reachable = new Set(REG.resources.map(tableFor));
  const orphan = schemaTables().filter((x) => !reachable.has(x));
  assert.deepStrictEqual(orphan, [],
    'tables nothing can write -- a migration that provisioned dead storage: ' + orphan);
});

test('every declared ALIAS is still needed, and none is stale', () => {
  // An alias for a resource nobody registers any more is a mapping kept alive
  // by nothing -- it would silently accept a table that should have been
  // reported as an orphan.
  const stale = Object.keys(ALIAS).filter((r) => !REG.resources.includes(r));
  assert.deepStrictEqual(stale, [],
    'aliases for resources that are no longer registered: ' + stale);
});

test('no resource is aliased to a table that does not exist', () => {
  const t = new Set(schemaTables());
  const broken = Object.keys(ALIAS).filter((r) => !t.has(ALIAS[r]));
  assert.deepStrictEqual(broken, [], 'aliases pointing at nothing: ' + broken);
});

test('registry vs CLIENT: every registered resource is named in the app', () => {
  const never = REG.resources.filter((r) => HTML.indexOf("'" + r + "'") === -1);
  assert.deepStrictEqual(never, [],
    'registered and never referenced by the app: ' + never);
});

section('3. the TIER A resources are asserted BY NAME');

test('the tier register still names Tier A resources for this app', () => {
  assert.ok(tierA('sairngrounds').length > 0,
    'no Tier A resource found for sairngrounds in docs/CRITICALITY-TIERS.md -- read it '
    + 'before relaxing this');
});

tierA('sairngrounds').forEach((r) => {
  test('`' + r + '` (Tier A) is registered, referenced and has a table', () => {
    assert.ok(REG.resources.includes(r), r + ' is not registered');
    assert.ok(HTML.indexOf("'" + r + "'") !== -1, r + ' is never referenced by the app');
    assert.ok(schemaTables().includes(tableFor(r)), tableFor(r) + ' has no table');
  });
});

console.log('\n' + (fail ? 'FAILED' : 'ok') + '  sairngrounds_server_backup: '
  + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
