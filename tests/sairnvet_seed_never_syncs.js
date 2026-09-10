// tests/sairnvet_seed_never_syncs.js
//
// Run:  node tests/sairnvet_seed_never_syncs.js
//
// A DEMO SEED REACHED A REAL CLINIC'S SERVER, AND IT WAS NOT HYPOTHETICAL:
// sql/sairnvet_data_schema.sql had already been run when this was found.
//
// 39 of SAIRNvet's 41 synced collections seed demo rows LAZILY -- every getX()
// writes its own sample data on FIRST READ when the key is absent, through
// saveX() -> st(). st() carries the server-backup hook, so merely OPENING a
// panel on a fresh or cleared device pushed fabricated records into the real
// tables. Measured against the pre-fix file: 38 of the 39 getters issued
// server writes (the 39th, getSoapNotes, seeds an empty array). The
// controlled-substance panel was the worst of them -- invented Ketamine,
// Butorphanol and Fentanyl balances with named vets, into a DEA-relevant
// register -- and hydration is additive-only with NO delete path anywhere in
// the product, so anything that landed spread to every other device and could
// not be removed from the app.
//
// `svSyncSuppressed` existed and was correct; it was simply only ever set
// while HYDRATING. The comment above it said "Set while seeding or hydrating",
// which described SAIRNbiz's one-pass sbSeedRows() -- a real try/finally
// around a real single seeding pass. This app has no such pass, so there was
// nothing to wrap and the sentence went on reading as if there were.
//
// WHAT THIS FILE HOLDS, and section 3 is the one that matters longest:
//   1. every seeded getter, driven on a fresh store, issues ZERO server writes
//   2. a REAL write still pushes -- the fix is not a mute button
//   3. every getter carrying a seed literal USES svSeedStore, derived from the
//      file rather than from a list here, so a new seeded getter added later
//      without the wrapper fails instead of quietly repeating this.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'sairnvet.html'), 'utf8').replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   - ' + name); pass++; }
  catch (e) { console.log('  FAIL - ' + name + '\n         ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function bodyAt(at) {
  const open = html.indexOf('{', at);
  let d = 0;
  for (let i = open; i < html.length; i++) {
    if (html[i] === '{') d++;
    else if (html[i] === '}') { d--; if (d === 0) return html.slice(at, i + 1); }
  }
  throw new Error('unbalanced braces');
}
function fn(sig) {
  const at = html.indexOf(sig);
  assert.ok(at > 0, 'not found in sairnvet.html: ' + sig);
  return bodyAt(at);
}
function decl(open) { const a = html.indexOf(open); return html.slice(a, html.indexOf('};', a) + 2); }
function arr(open) { const a = html.indexOf(open); return html.slice(a, html.indexOf('];', a) + 2); }

// EVERY getter that writes a seed, and the saver it writes through, DERIVED
// FROM THE FILE. A hardcoded list here would pass forever while the app grew
// a fortieth seeded getter -- the drift tests/sairnlaw_hydrate.js already
// learned once with LAW_SYNC_RESOURCES.
function seededGetters() {
  const savers = {};
  const saveRe = /function (\w+)\(([\w, ]*)\)\{\s*return st\(\s*'(sv_\w+)'/g;
  let m;
  while ((m = saveRe.exec(html))) savers[m[1]] = m[3];
  const out = [];
  const getRe = /function (get\w+)\(/g;
  while ((m = getRe.exec(html))) {
    const name = m[1];
    const body = bodyAt(m.index);
    if (!/var (seed|demo)\w*\s*=/.test(body)) continue;
    const call = /\b(\w+)\(\s*(seed\w*|demo\w*)\s*\)\s*;/.exec(body);
    const wrapped = /svSeedStore\(\s*(\w+)\s*,\s*(seed\w*|demo\w*)\s*\)/.exec(body);
    const saver = wrapped ? wrapped[1] : (call ? call[1] : null);
    if (!saver || !savers[saver]) continue;
    out.push({ getter: name, saver: saver, key: savers[saver], wrapped: !!wrapped });
  }
  return out;
}

const SEEDED = seededGetters();

// A realm holding the REAL st(), svSyncCollection(), svSeedStore() and every
// seeded getter/saver pair. Nothing about the mechanism is stubbed; only the
// browser and the network are.
function harness() {
  const store = {}, writes = [];
  const ctx = {
    JSON, Object, Array, String, Number, Date, Math, parseFloat, parseInt, isNaN,
    console: { warn() {}, error() {}, log() {} },
    localStorage: {
      getItem: (k) => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = v; },
      removeItem: (k) => { delete store[k]; },
      get length() { return Object.keys(store).length; },
      key: (i) => Object.keys(store)[i],
    },
    svLoad: (k, d) => (k === 'license' ? 'SV-PINNACLE-2026' : d),
    svData: (a, r, p) => { writes.push({ action: a, resource: r, id: p && p.id }); return Promise.resolve({}); },
    showToast() {}, document: { getElementById: () => null, addEventListener() {} },
    svBlockForCorruptStore() {}, localToday: () => '2026-09-10',
    __writes: writes, __store: store,
  };
  vm.createContext(ctx);
  let src = arr('var SV_SYNCED=[') + '\n'
    + 'var SV_SYNCED_ON={};SV_SYNCED.forEach(function(k){SV_SYNCED_ON[k]=true;});\n'
    + decl('var SV_ID_FIELD={') + '\n'
    + 'var svSyncSuppressed=false,_svUnreadable={},_svKeyVerified={},_svWriteFailed=null;\n'
    + fn('function svIsQuotaError(') + '\n'
    + fn('function svSyncCollection(') + '\n'
    + fn('function st(key,data){') + '\n';
  if (html.indexOf('function svSeedStore(') > -1) src += fn('function svSeedStore(') + '\n';
  SEEDED.forEach((s) => { src += fn('function ' + s.saver + '(') + '\n' + fn('function ' + s.getter + '(') + '\n'; });
  vm.runInContext(src, ctx);
  return ctx;
}

// ═══════════════════════════════════════════════════════════════════════════
section('1. seeding writes locally and reaches NO server');

test('the file still has the seeded getters this exists for', () => {
  assert.ok(SEEDED.length >= 39,
    'only ' + SEEDED.length + ' seeded getters found -- the scan stopped matching, '
    + 'which would make every assertion below vacuous');
});

test('every seeded getter, on a fresh store, issues ZERO server writes', () => {
  const c = harness();
  const offenders = [];
  SEEDED.forEach((s) => {
    c.__writes.length = 0;
    let rows;
    try { rows = c[s.getter](); } catch (e) { offenders.push(s.getter + ' threw: ' + e.message); return; }
    if (c.__writes.length) {
      offenders.push(s.getter + ' pushed ' + c.__writes.length + ' record(s) to ' + s.key);
    }
    assert.ok(rows !== undefined, s.getter + ' returned nothing');
  });
  assert.deepStrictEqual(offenders, [],
    'demo rows reached the server from: ' + offenders.join('; '));
});

test('and it DID seed locally -- suppressing the push must not skip the write', () => {
  const c = harness();
  SEEDED.forEach((s) => { c[s.getter](); });
  const written = SEEDED.filter((s) => s.key in c.__store).length;
  assert.strictEqual(written, SEEDED.length,
    only(written) + ' of ' + SEEDED.length + ' seeded keys were written locally');
  function only(n) { return String(n); }
});

// ═══════════════════════════════════════════════════════════════════════════
section('2. the fix is not a mute button');

test('a REAL write still reaches the server', () => {
  const c = harness();
  c.__writes.length = 0;
  c.st('sv_controlled', [{ drug: 'REAL ENTRY', schedule: 'IV', onHand: 5, unit: 'mg', lastTransaction: '', witness: '' }]);
  assert.strictEqual(c.__writes.length, 1, 'a genuine write was suppressed too');
  assert.strictEqual(c.__writes[0].resource, 'sv_controlled');
  assert.strictEqual(c.__writes[0].id, 'REAL ENTRY');
});

test('a real write straight after a seed is still pushed', () => {
  // The ordering that would break if the flag were left set: seed, then the
  // clinic's first genuine record in the same session.
  const c = harness();
  c.getControlledLog();
  c.__writes.length = 0;
  c.st('sv_controlled', [{ drug: 'AFTER SEED', schedule: 'IV', onHand: 1, unit: 'mg', lastTransaction: '', witness: '' }]);
  assert.strictEqual(c.__writes.length, 1, 'the suppression outlived the seed');
});

test('a saver that THROWS does not leave the backup suppressed', () => {
  // Why svSeedStore uses try/finally rather than two assignments: one throw
  // would otherwise silence the backup for the rest of the session, which is
  // the same defect with a harder-to-find cause.
  const c = harness();
  const boom = () => { throw new Error('storage exploded'); };
  assert.throws(() => c.svSeedStore(boom, []), /storage exploded/);
  c.__writes.length = 0;
  c.st('sv_controlled', [{ drug: 'AFTER THROW', schedule: 'IV', onHand: 1, unit: 'mg', lastTransaction: '', witness: '' }]);
  assert.strictEqual(c.__writes.length, 1, 'a throwing seed left svSyncSuppressed true');
});

// ═══════════════════════════════════════════════════════════════════════════
section('3. a NEW seeded getter cannot repeat this quietly');

test('every getter that writes a seed goes through svSeedStore', () => {
  const bare = SEEDED.filter((s) => !s.wrapped).map((s) => s.getter + ' -> ' + s.key);
  assert.deepStrictEqual(bare, [],
    'these getters write a seed straight through their saver, so st() will push '
    + 'demo rows to the clinic\'s server: ' + bare.join('; '));
});

test('svSeedStore exists and clears the flag in a finally', () => {
  const body = fn('function svSeedStore(');
  assert.ok(/finally\s*\{\s*svSyncSuppressed\s*=\s*false/.test(body),
    'svSeedStore does not clear svSyncSuppressed in a finally');
  assert.ok(/svSyncSuppressed\s*=\s*true/.test(body), 'svSeedStore never sets the flag');
});

test('svSyncSuppressed is set in exactly the two places that should set it', () => {
  // Hydration and seeding. A third assignment is a new suppression path and
  // wants reading before it is trusted -- this is the mechanism that hid the
  // defect, so it is pinned rather than left to inspection.
  const sets = (html.match(/svSyncSuppressed\s*=\s*true/g) || []).length;
  assert.strictEqual(sets, 2,
    'svSyncSuppressed is set true in ' + sets + ' place(s); expected 2 '
    + '(svHydrateAll and svSeedStore)');
});

// ═══════════════════════════════════════════════════════════════════════════
console.log('\n' + pass + '/' + (pass + fail) + ' passed');
process.exit(fail ? 1 : 0);
