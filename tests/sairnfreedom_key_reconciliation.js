// tests/sairnfreedom_key_reconciliation.js
//
// Run:  node tests/sairnfreedom_key_reconciliation.js
//
// EVERY SAIRNfreedom STORAGE KEY IS EITHER BACKED UP OR DELIBERATELY EXCLUDED,
// AND `sf_trustee_audits` WAS NEITHER.
//
// api/_resources/sairnfreedom.js ends with a reconciliation the registry states
// about itself:
//
//     42 keys written, 35 backed up, 7 excluded above -- the count reconciles.
//
// That sentence is the only thing in the repo that ever checked it, and a
// sentence does not re-run. A 43rd key -- `sf_trustee_audits`, the quarterly
// trustee audit with the auditor's name, the bond and its expiry -- was added
// to sairnfreedom.html and reached NONE of the three lists. It was not in
// SF_SYNCED, not in the registry, not in the schema, and not in the exclusion
// list either, so nothing anywhere recorded a decision about it.
//
// `tools/local_only_collection_check.py` measured it as 1 of 36 collections
// with no route to a server. That tool reports; this file FAILS, which is the
// difference between a number somebody reads and a gate somebody trips.
//
// ── WHY THE RECONCILIATION ARM IS THE ONE THAT MATTERS ────────────────────
// A test that only asserts `sf_trustee_audits` is wired goes green the moment
// this one resource is fixed and says nothing about the 44th key. The
// reconciliation arm is the general property: EVERY key is on exactly one of
// the two lists, so a new collection has to be a DECISION -- backed up, or
// excluded with a stated reason -- rather than a default of silence. The
// deliberate exclusions are real and must stay excluded: a signing keypair and
// a trust-on-first-use fingerprint map must not leave the device, and the
// licence key is the credential the backup authenticates WITH.
//
// C1 is the control for that arm: an invented key that is on neither list must
// be REPORTED, so a green run is evidence the reconciliation is being computed
// rather than that both lists happened to agree.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const ROOT = path.join(__dirname, '..');
const HTML = fs.readFileSync(path.join(ROOT, 'sairnfreedom.html'), 'utf8');
const SQL = fs.readFileSync(
  path.join(ROOT, 'sql', 'sairnfreedom_data_schema.sql'), 'utf8');
const SDDATA = fs.readFileSync(path.join(ROOT, 'api', 'sd-data.js'), 'utf8');
const REG = require(path.join(ROOT, 'api', '_resources', 'sairnfreedom.js'));

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

// Every `K_SOMETHING = 'sf_...'` binding in the app. Read off the ASSIGNMENT
// rather than off a list, because a list is the thing under test.
function storageKeys(src) {
  const out = new Set();
  const re = /K_[A-Z_0-9]+\s*=\s*'(sf_[a-z_0-9]+)'/g;
  let m;
  while ((m = re.exec(src)) !== null) out.add(m[1]);
  return [...out].sort();
}

function syncedList(src) {
  const m = src.match(/var SF_SYNCED\s*=\s*\[([^\]]*)\]/);
  assert.ok(m, 'sairnfreedom.html has no SF_SYNCED -- the backup is not wired');
  return (m[1].match(/'([a-z0-9_]+)'/g) || []).map((s) => s.slice(1, -1));
}

// ── THE SEVEN DELIBERATE EXCLUSIONS, RESTATED HERE ON PURPOSE ─────────────
// Duplicated from the registry comment rather than parsed out of it. Parsing
// the comment would make this file agree with that comment BY CONSTRUCTION,
// and then a key quietly added to the comment would pass here without anybody
// deciding anything -- the reconciliation checking itself.
const EXCLUDED = [
  'sf_license_key',          // the credential the backup authenticates WITH
  'sf_post',                 // the post's own identity/config object
  'sf_fees',                 // a fee schedule -- configuration
  'sf_hall_rates',           // a rate card -- configuration
  'sf_phase4_config',        // configuration
  'sf_district_keypair',     // SIGNING KEY MATERIAL. A backup is the opposite
  'sf_district_known_keys',  // device-local trust-on-first-use fingerprints
];

section('A. the reconciliation, which is the general property');

test('A1. EVERY sf_ storage key is either in SF_SYNCED or in the stated '
   + 'exclusion list -- a key that is on neither is a collection nobody '
   + 'decided about, which is how sf_trustee_audits lived in one browser',
  () => {
    const keys = storageKeys(HTML);
    const synced = syncedList(HTML);
    const orphan = keys.filter(
      (k) => !synced.includes(k) && !EXCLUDED.includes(k));
    assert.deepStrictEqual(orphan, [],
      'storage key(s) on NEITHER list: ' + orphan.join(', ')
      + ' -- add to SF_SYNCED (and the registry, the schema and, if it carries '
      + 'identity or money, SD_SESSION_GATED), or to the exclusion list with '
      + 'the reason');
  });

test('A1b. CONTROL: an invented key on neither list IS reported, so A1 is '
   + 'computing a reconciliation rather than comparing two lists that happen '
   + 'to agree',
  () => {
    const synced = syncedList(HTML);
    const keys = storageKeys(HTML).concat(['sf_zz_not_a_real_key']);
    const orphan = keys.filter(
      (k) => !synced.includes(k) && !EXCLUDED.includes(k));
    assert.deepStrictEqual(orphan, ['sf_zz_not_a_real_key'],
      'the reconciliation did not catch a planted orphan -- A1 proves nothing');
  });

test('A2. ...and nothing in SF_SYNCED is ALSO in the exclusion list. The two '
   + 'lists are a partition; an overlap means one of them is wrong and the '
   + 'total in the registry comment reconciles by accident',
  () => {
    const both = syncedList(HTML).filter((k) => EXCLUDED.includes(k));
    assert.deepStrictEqual(both, [], 'on both lists: ' + both.join(', '));
  });

test('A3. the three counts reconcile: keys = backed up + excluded, with no '
   + 'remainder. This is the registry\'s own closing sentence, executed',
  () => {
    const keys = storageKeys(HTML);
    const synced = syncedList(HTML);
    assert.strictEqual(keys.length, synced.length + EXCLUDED.length,
      keys.length + ' keys, ' + synced.length + ' backed up, '
      + EXCLUDED.length + ' excluded -- the count does NOT reconcile');
  });

section('B. sf_trustee_audits specifically, on all four surfaces');

test('B1. SF_SYNCED pushes it, or the app never sends it at all', () => {
  assert.ok(syncedList(HTML).includes('sf_trustee_audits'),
    'sf_trustee_audits is not in SF_SYNCED');
});

test('B2. the resource registry allows it, or every write answers 400 at the '
   + 'gate', () => {
  assert.ok(REG.resources.includes('sf_trustee_audits'),
    'sf_trustee_audits is not in api/_resources/sairnfreedom.js');
});

test('B3. the schema creates the table, or every write answers 503 '
   + 'NOT_PROVISIONED -- a different failure from 400 and both are honest, '
   + 'but neither is a backup', () => {
  assert.ok(/create table if not exists public\.sf_trustee_audits/.test(SQL),
    'no sf_trustee_audits table in sql/sairnfreedom_data_schema.sql');
});

test('B3b. ...with RLS enabled and the NARROWED grant -- select/insert/update '
   + 'and no delete, matching every other sf_ table', () => {
  assert.ok(
    /alter table public\.sf_trustee_audits enable row level security/.test(SQL),
    'RLS is not enabled on sf_trustee_audits');
  assert.ok(
    /revoke all on public\.sf_trustee_audits from service_role/.test(SQL),
    'the blanket grant is not revoked on sf_trustee_audits');
  assert.ok(
    /grant select, insert, update on public\.sf_trustee_audits to service_role/
      .test(SQL),
    'sf_trustee_audits does not carry the narrowed grant');
  assert.ok(!/delete on public\.sf_trustee_audits/.test(SQL),
    'sf_trustee_audits grants DELETE -- no other sf_ table does');
});

test('B4. SD_SESSION_GATED covers read AND write. A trustee audit names the '
   + 'auditor and carries the fidelity bond and its expiry -- it is the '
   + 'financial-controls attestation for an ORC 2915 gaming post, and the '
   + 'licence key alone is shipped to the browser',
  () => {
    const m = SDDATA.match(/'sf_trustee_audits':\s*\[([^\]]*)\]/);
    assert.ok(m, 'sf_trustee_audits is not in SD_SESSION_GATED in api/sd-data.js');
    assert.ok(/'read'/.test(m[1]) && /'write'/.test(m[1]),
      'sf_trustee_audits is gated on only one of read/write: ' + m[1]);
  });

test('B5. ...and the HANDLER can dispatch it. Registering a name decides what '
   + 'the allowlist admits; SF_RESOURCES in api/sd-data.js decides what the '
   + 'handler can actually reach. A name in the first and not the second '
   + 'passes the gate and falls through to "Unsupported action/resource '
   + 'combination" -- worse than not registering it',
  () => {
    assert.ok(/sf_trustee_audits:\s*'trustee_audit_id'/.test(SDDATA),
      'sf_trustee_audits has no SF_RESOURCES key-column mapping in api/sd-data.js');
  });

test('B5b. ...and the mapped key column is the one the table actually has, or '
   + 'every write is a 400 from PostgREST about an unknown column',
  () => {
    const m = SDDATA.match(/sf_trustee_audits:\s*'([a-z_]+)'/);
    assert.ok(m, 'no mapping to read the column name out of');
    assert.ok(new RegExp('\\b' + m[1] + ' text not null').test(SQL),
      'api/sd-data.js maps sf_trustee_audits to `' + m[1] + '` and the schema '
      + 'does not declare that column');
  });

section('C. anchors -- what tells us the day this file stops testing');

test('C1. the key-extraction regex still finds a realistic number of keys. If '
   + 'the app changes how it declares them, every arm above would go green '
   + 'against an empty set',
  () => {
    const keys = storageKeys(HTML);
    assert.ok(keys.length >= 40,
      'only ' + keys.length + ' storage keys extracted -- the K_ assignment '
      + 'pattern stopped matching and A1 is now vacuous');
  });

test('C2. SF_SYNCED is non-empty for the same reason', () => {
  assert.ok(syncedList(HTML).length >= 30,
    'SF_SYNCED extracted as ' + syncedList(HTML).length + ' entries');
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
