// tests/server_wins_hydration.js
//
// Run:  node tests/server_wins_hydration.js
//
// ── ONE RULE, DRIVEN ACROSS EVERY APP THAT IMPLEMENTS IT ───────────────────
// # REQUIREMENT: once a record's id exists on BOTH sides, hydration replaces
//   the local copy with the server's -- except for a record whose own FIRST
//   push has never landed, which keeps its local value; and the rule is the
//   SAME rule in every app that hydrates, not a per-app or per-resource
//   judgement call
//
// Michael's decision, 2026-09-21. What it replaced was additive-only merge:
// "a locally present id is never overwritten by this merge", disclosed in all
// three apps as a limitation about two devices editing the SAME record.
//
// THAT DISCLOSURE UNDERSTATED THE DEFECT, which is why the rule changed. It
// was never only about concurrent edits. ANY field corrected on the server was
// invisible FOREVER to a device that already held that id, whether or not
// anything raced -- workstation A marks a record, workstation B hydrated it
// last week and has done nothing since, and nothing will ever reconcile them.
// No conflict had to occur.
//
// ── WHY THIS SUITE DRIVES EVERY APP FROM ONE TABLE ────────────────────────
// These are single-file apps with no shared module, so the rule necessarily
// exists as one copy per app. Three copies of a rule is three chances to
// drift, and a per-app suite would let them drift while every suite stayed
// green. So the arms below are written ONCE and run against every entry in
// APPS, and section 6 asserts the table is not quietly missing an app.
//
// WHAT IS LIFTED, NOT RETYPED: each app's real ld(), st(), sdnData(), the
// synced-id helpers, the resource list, and sdnHydrateAll() are read out of
// the shipped .html and executed. A retyped fixture is a fixture that drifts
// from the code it exists to check -- the mistake tests/sairnlaw_hydrate.js
// records making with LAW_SYNC_RESOURCES.
//
// The negative control is tests/run_server_wins_hydration_sabotage_probe.py,
// which plants the additive/never-overwrite behaviour back into each app and
// requires this suite to go RED.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const read = (f) => fs.readFileSync(path.join(ROOT, f), 'utf8').replace(/\r\n/g, '\n');

// ── THE TABLE ──────────────────────────────────────────────────────────────
// `sample` is one real resource name out of that app's own list; the arms
// assert it IS in the shipped list rather than trusting this column.
const APPS = [
  {
    app: 'sairnlegacy', file: 'sairnlegacy.html', prefix: 'leg',
    storageKey: 'leg_synced_ids', keyVar: 'LEG_SYNCED_KEY',
    listVar: 'LEG_SYNC_RESOURCES', sample: 'leg_cases',
    licenseFn: 'legLicenseKey', quotaStub: 'lgyIsQuotaError',
    errBag: 'legLastErr', timeoutFn: 'legFetchTimeoutSignal', sessionVar: 'legSession',
  },
  {
    app: 'sairndesign', file: 'sairndesign.html', prefix: 'sdn',
    storageKey: 'sdn_synced_ids', keyVar: 'SDN_SYNCED_KEY',
    listVar: 'SDN_SYNC_RESOURCES', sample: 'sdn_projects',
    licenseFn: 'sdnLicenseKey', quotaStub: 'dsnIsQuotaError',
    errBag: null, timeoutFn: 'sdnFetchTimeoutSignal', sessionVar: 'sdnSession',
  },
];

// ── NOT YET CONVERTED, NAMED RATHER THAN OMITTED ──────────────────────────
// THE BRIEF SAID THREE APPS AND THE SHAPE IS IN NINE. That was found by this
// suite, not by reading: the first version of the coverage arm below anchored
// on the PROSE those apps carried ("never overwritten by this merge") and
// reported exactly one straggler. Anchoring on prose is PR 1.2 -- grep cannot
// tell code from text describing code -- so it was replaced with the
// STRUCTURAL signature of the merge itself, and the count went from 1 to 7.
// Every site it reports sits inside a function whose name contains "Hydrate";
// that was checked one by one rather than assumed from the regex.
//
// A bare exclusion list is how a real gap goes quiet, so each entry carries
// its site count and its reason, and section 6 asserts the list is EXACTLY
// what the detector finds -- an app converted and left here FAILS, and an app
// that is neither converted nor listed FAILS.
const PENDING = [
  { file: 'sairnlaw.html', sites: 1, fns: ['lawHydrateAll'],
    why: 'IN THE BRIEF and not done in this pass: another session held the '
       + 'app-wide sairnlaw claim (deadline engine) throughout. The file sets '
       + 'are disjoint and the block was NOT overridden. Convert it next.' },
  { file: 'sairncare.html', sites: 6, fns: ['alfHydrateResidents', 'alfHydrateMar', 'alfHydrateStaff', 'alfHydrateBilling', 'alfHydrateIncidents', 'alfHydrateActivities'],
    why: 'NOT IN THE BRIEF. Six separate per-resource hydrates rather than one '
       + 'loop, and one of them is the MAR -- a medication administration '
       + 'record, where "the server copy wins" is a clinical decision and not '
       + 'only a sync one. Needs its own call before any code.' },
  { file: 'sairnsenior.html', sites: 7, fns: ['senHydrateClients', 'senHydrateCaregivers', 'senHydrateVisits', 'senHydrateReferrals', 'senHydrateOrg', 'senHydrateTraining', 'senHydrateClaims'],
    why: 'NOT IN THE BRIEF. Seven per-resource hydrates, the largest single '
       + 'conversion on the platform.' },
  { file: 'stonedesk.html', sites: 2, fns: ['sdHydrateAll', 'sdHydrateCustomers'],
    why: 'NOT IN THE BRIEF. A ~2MB single file with its own storage layer; the '
       + 'blast radius is not the same as a small app carrying the same lines.' },
  { file: 'sairnbuild.html', sites: 2, fns: ['bldHydrateAll', 'bldHydrateBids'],
    why: 'NOT IN THE BRIEF, and architecturally different: st() itself pushes '
       + 'to the server via bldSyncCollection(), suppressed during hydration by '
       + 'a bldSeeding flag that bldHydrateAll sets and bldHydrateBids does '
       + 'NOT. Server-wins writes more often, so that asymmetry has to be '
       + 'settled as part of the conversion rather than inherited.' },
  { file: 'sairnbiz.html', sites: 1, fns: ['sbHydrateAll'],
    why: 'NOT IN THE BRIEF. One loop, the same shape as the two converted here.' },
  { file: 'sairnfreedom.html', sites: 1, fns: ['sfHydrateAll'],
    why: 'NOT IN THE BRIEF. One loop, the same shape as the two converted here.' },
];

let pass = 0, fail = 0;
const queue = [];
function test(name, fn) { queue.push({ name, fn }); }
function section(t) { queue.push({ section: t }); }

function braceBody(src, at) {
  const open = src.indexOf('{', at);
  let depth = 0;
  for (let i = open; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') { depth--; if (depth === 0) return src.slice(at, i + 1); }
  }
  throw new Error('unbalanced braces');
}
function lift(src, needle, label) {
  const at = src.indexOf(needle);
  assert.ok(at > 0, 'not found: ' + (label || needle));
  return braceBody(src, at);
}
function liftList(src, varName) {
  const at = src.indexOf('var ' + varName + '=[');
  assert.ok(at > 0, varName + ' not found');
  const end = src.indexOf('];', at);
  assert.ok(end > at, varName + ' unterminated');
  return src.slice(at, end + 2);
}

// opts.local        {resource: [records]}          seeded into fake localStorage
// opts.server       {resource: [records] | null}   null = a read that FAILED
// opts.synced       {resource: [ids]} | 'corrupt' | undefined (never written)
function harness(A, opts) {
  opts = opts || {};
  const src = read(A.file);
  const store = {};
  Object.keys(opts.local || {}).forEach((k) => { store[k] = JSON.stringify(opts.local[k]); });
  if (opts.synced === 'corrupt') store[A.storageKey] = '{not json';
  else if (opts.synced !== undefined) store[A.storageKey] = JSON.stringify(opts.synced);

  const reads = [];
  const writes = [];
  const localStorage = {
    getItem: (k) => (Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
  };
  const ctx = {
    JSON, Object, Array, String, Number, Math, Promise, Date, isFinite,
    console: { warn: () => {}, error: () => {} },
    localStorage,
    __store: store, __reads: reads, __writes: writes,
    DATA_API: '/api/sd-data', APP_ID: A.app,
    [A.licenseFn]: () => 'LICENCE-KEY',
    [A.quotaStub]: () => false,
    [A.timeoutFn]: () => undefined,
    [A.sessionVar]: null,
    // The hydrate calls sdnData('read', ...). The sdnData ARMS install the
    // real one over this; everywhere else the read is what is under test, not
    // the transport.
    sdnData: (action, resource) => {
      reads.push(resource);
      const rows = (opts.server || {})[resource];
      return Promise.resolve(rows === undefined ? [] : rows);
    },
  };
  if (A.errBag) ctx[A.errBag] = {};
  vm.createContext(ctx);
  vm.runInContext([
    lift(src, 'function st(k,v){', 'st'),
    lift(src, 'function ld(k,d){', 'ld'),
    src.slice(src.indexOf("var " + A.keyVar + "='"),
              src.indexOf(';', src.indexOf("var " + A.keyVar + "='")) + 1),
    lift(src, 'function ' + A.prefix + 'SyncedRead()', 'SyncedRead'),
    lift(src, 'function ' + A.prefix + 'MarkSynced(', 'MarkSynced'),
    liftList(src, A.listVar),
    lift(src, 'async function sdnHydrateAll()', 'sdnHydrateAll'),
  ].join('\n'), ctx);
  ctx.__local = (k) => JSON.parse(store[k] || 'null');
  ctx.__synced = () => { try { return JSON.parse(store[A.storageKey]); } catch (e) { return store[A.storageKey]; } };
  ctx.__installRealTransport = (responder) => {
    ctx.fetch = (url, o) => {
      const body = JSON.parse(o.body);
      writes.push(body);
      const ok = responder(body);
      return Promise.resolve({
        ok, status: ok ? 200 : 400,
        json: () => Promise.resolve(ok ? { ok: true, data: body.payload }
                                       : { ok: false, error: { code: 'NOPE', message: 'no' } }),
      });
    };
    vm.runInContext(lift(src, 'function sdnData(action,resource,payload,withSession){', 'sdnData'), ctx);
  };
  return ctx;
}

const forEachApp = (name, fn) => APPS.forEach((A) => test('[' + A.app + '] ' + name, () => fn(A)));

// ═══════════════════════════════════════════════════════════════════════════
section('1. server-wins: a record held on BOTH sides takes the server copy');

forEachApp('a synced id is REPLACED by the server copy, field for field', async (A) => {
  const c = harness(A, {
    local:  { [A.sample]: [{ id: 'R-1', status: 'Open', note: 'stale local' }] },
    server: { [A.sample]: [{ id: 'R-1', status: 'Closed', note: 'server truth' }] },
    synced: { [A.sample]: ['R-1'] },
  });
  await c.sdnHydrateAll();
  const row = c.__local(A.sample).find((r) => r.id === 'R-1');
  assert.strictEqual(row.status, 'Closed', 'the local copy survived -- this is the old additive behaviour');
  assert.strictEqual(row.note, 'server truth');
});

forEachApp('a field the server DROPPED is gone locally -- replace, not merge', async (A) => {
  const c = harness(A, {
    local:  { [A.sample]: [{ id: 'R-1', status: 'Open', localOnly: 'kept?' }] },
    server: { [A.sample]: [{ id: 'R-1', status: 'Closed' }] },
    synced: { [A.sample]: ['R-1'] },
  });
  await c.sdnHydrateAll();
  const row = c.__local(A.sample).find((r) => r.id === 'R-1');
  assert.ok(!('localOnly' in row),
    'a local-only field survived -- that is a field MERGE, and the rule is the server copy wins');
});

forEachApp('a server record not held locally is still appended, and marked synced', async (A) => {
  const c = harness(A, {
    local:  { [A.sample]: [{ id: 'R-1' }] },
    server: { [A.sample]: [{ id: 'R-1' }, { id: 'R-2', from: 'other device' }] },
    synced: { [A.sample]: ['R-1'] },
  });
  await c.sdnHydrateAll();
  assert.deepStrictEqual(c.__local(A.sample).map((r) => r.id).sort(), ['R-1', 'R-2']);
  assert.ok(c.__synced()[A.sample].indexOf('R-2') !== -1,
    'a record that came FROM the server was not recorded as being on it');
});

forEachApp('a purely local record the server has never seen is untouched', async (A) => {
  const c = harness(A, {
    local:  { [A.sample]: [{ id: 'R-9', note: 'mine, offline' }] },
    server: { [A.sample]: [] },
    synced: { [A.sample]: [] },
  });
  await c.sdnHydrateAll();
  assert.strictEqual(c.__local(A.sample).find((r) => r.id === 'R-9').note, 'mine, offline');
});

// ═══════════════════════════════════════════════════════════════════════════
section('2. the carve-out: a record whose FIRST push never landed keeps its own value');

forEachApp('an UNSYNCED id is NOT overwritten, even though the server has that id', async (A) => {
  // The collision case, and the only one this branch exists for: newId() is
  // prefix + Date.now() + a 0-999 draw, so two devices in the same millisecond
  // drawing the same number produce the same id. The server's row is then a
  // STRANGER'S record, and overwriting would destroy work that has never been
  // anywhere else.
  const c = harness(A, {
    local:  { [A.sample]: [{ id: 'R-1', note: 'never pushed' }] },
    server: { [A.sample]: [{ id: 'R-1', note: 'somebody else' }] },
    synced: { [A.sample]: [] },                 // seeded, and R-1 is not in it
  });
  await c.sdnHydrateAll();
  assert.strictEqual(c.__local(A.sample).find((r) => r.id === 'R-1').note, 'never pushed',
    'a record whose own push has never landed was overwritten by a stranger');
});

forEachApp('and it is NOT recorded as synced by being kept -- the next hydrate must not overwrite it either', async (A) => {
  const c = harness(A, {
    local:  { [A.sample]: [{ id: 'R-1', note: 'never pushed' }] },
    server: { [A.sample]: [{ id: 'R-1', note: 'somebody else' }] },
    synced: { [A.sample]: [] },
  });
  await c.sdnHydrateAll();
  assert.ok((c.__synced()[A.sample] || []).indexOf('R-1') === -1,
    'keeping the record also marked it synced, which hands the NEXT hydrate permission to overwrite it');
  await c.sdnHydrateAll();
  assert.strictEqual(c.__local(A.sample).find((r) => r.id === 'R-1').note, 'never pushed',
    'it survived one hydrate and not two');
});

forEachApp('once its push DOES land, the same record becomes overwritable', async (A) => {
  const c = harness(A, {
    local:  { [A.sample]: [{ id: 'R-1', note: 'pending' }] },
    server: { [A.sample]: [{ id: 'R-1', note: 'server truth' }] },
    synced: { [A.sample]: [] },
  });
  await c.sdnHydrateAll();
  assert.strictEqual(c.__local(A.sample)[0].note, 'pending');
  vm.runInContext('(' + A.prefix + 'MarkSynced)("' + A.sample + '","R-1")', c);
  await c.sdnHydrateAll();
  assert.strictEqual(c.__local(A.sample)[0].note, 'server truth',
    'the carve-out outlived the push that was supposed to end it');
});

// ═══════════════════════════════════════════════════════════════════════════
section('3. the first hydrate after upgrade seeds what the server already had');

forEachApp('a NEVER-SEEDED resource overwrites on an id match, and records it', async (A) => {
  // Existing installs have no map. Every id present on both sides at that
  // moment was demonstrably pushed by somebody, so server-wins applies -- and
  // if it did not, the rule would be inert for all existing data, which is
  // exactly the situation it was chosen to fix.
  const c = harness(A, {
    local:  { [A.sample]: [{ id: 'R-1', note: 'stale' }] },
    server: { [A.sample]: [{ id: 'R-1', note: 'server truth' }] },
    synced: undefined,
  });
  await c.sdnHydrateAll();
  assert.strictEqual(c.__local(A.sample)[0].note, 'server truth');
  assert.ok(c.__synced()[A.sample].indexOf('R-1') !== -1);
});

forEachApp('seeding is per RESOURCE -- a resource whose read FAILED is not marked seeded', async (A) => {
  // A first hydrate where some reads fail must not permanently exempt those
  // resources: without this the rule would apply to the resources that
  // happened to answer and to no others, forever.
  const other = APPS.find((x) => x.app === A.app).listVar;
  const c = harness(A, { local: {}, server: { [A.sample]: null }, synced: undefined });
  await c.sdnHydrateAll();
  const m = c.__synced();
  assert.ok(!m || !(A.sample in m),
    A.sample + ' was marked seeded on a read that failed (' + other + ')');
});

forEachApp('a resource that read EMPTY is marked seeded, so it is not re-seeded forever', async (A) => {
  const c = harness(A, { local: {}, server: { [A.sample]: [] }, synced: undefined });
  await c.sdnHydrateAll();
  assert.ok(Array.isArray(c.__synced()[A.sample]),
    'an empty but SUCCESSFUL read left the resource un-seeded, so the next hydrate '
    + 'would re-enter the never-seeded branch and overwrite unconditionally');
});

// ═══════════════════════════════════════════════════════════════════════════
section('4. an unreadable map is a THIRD answer, and it fails toward keeping local data');

forEachApp('a CORRUPT synced map overwrites NOTHING', async (A) => {
  // ld() answers the same for "absent" and "corrupt", and absent means
  // never-seeded, which means permission to overwrite. Reading the key raw is
  // what keeps a failed read from being read as that permission.
  const c = harness(A, {
    local:  { [A.sample]: [{ id: 'R-1', note: 'local' }] },
    server: { [A.sample]: [{ id: 'R-1', note: 'server' }] },
    synced: 'corrupt',
  });
  await c.sdnHydrateAll();
  assert.strictEqual(c.__local(A.sample)[0].note, 'local',
    'a map that could not be read was treated as permission to overwrite');
});

forEachApp('a corrupt map is not silently replaced, and nothing is seeded through it', async (A) => {
  const c = harness(A, {
    local:  { [A.sample]: [{ id: 'R-1' }] },
    server: { [A.sample]: [{ id: 'R-1' }, { id: 'R-2' }] },
    synced: 'corrupt',
  });
  await c.sdnHydrateAll();
  assert.strictEqual(c.__store[A.storageKey], '{not json',
    'the unreadable map was overwritten -- whatever it held is now unrecoverable');
  // The merge still degrades to the old additive behaviour rather than doing
  // nothing: a new server record is still worth having.
  assert.deepStrictEqual(c.__local(A.sample).map((r) => r.id).sort(), ['R-1', 'R-2']);
});

// ═══════════════════════════════════════════════════════════════════════════
section('5. the transport is what records a landed push, so no save path can miss it');

forEachApp('a successful WRITE marks the id; a failed one does not', async (A) => {
  const c = harness(A, { local: {}, server: {}, synced: {} });
  c.__installRealTransport((body) => body.payload.id !== 'BAD');
  await c.sdnData('write', A.sample, { id: 'GOOD', v: 1 });
  await c.sdnData('write', A.sample, { id: 'BAD', v: 1 });
  const m = c.__synced()[A.sample] || [];
  assert.ok(m.indexOf('GOOD') !== -1, 'a write the server ACCEPTED was not recorded');
  assert.ok(m.indexOf('BAD') === -1,
    'a write the server REFUSED was recorded as landed -- the carve-out would let '
    + 'the next hydrate overwrite a record that never reached the server');
});

forEachApp('a READ marks nothing, and a write with no id marks nothing', async (A) => {
  const c = harness(A, { local: {}, server: {}, synced: {} });
  c.__installRealTransport(() => true);
  await c.sdnData('read', A.sample);
  await c.sdnData('write', A.sample, { v: 1 });
  assert.deepStrictEqual(c.__synced()[A.sample] || [], []);
});

// ═══════════════════════════════════════════════════════════════════════════
section('6. it is ONE rule, and the table is not quietly missing an app');

test('every app in the table really ships the sample resource it is tested on', () => {
  APPS.forEach((A) => {
    const src = read(A.file);
    const list = liftList(src, A.listVar);
    assert.ok(list.indexOf("'" + A.sample + "'") !== -1,
      A.app + ': ' + A.sample + ' is not in the shipped ' + A.listVar);
  });
});

// THE STRUCTURAL SIGNATURE of the merge this rule replaces: append the server
// row only when its id is NOT already held locally, and never assign into the
// local array. Matched on the CODE rather than on the sentence the authors
// wrote about it -- the prose anchor this arm started with reported 1
// straggler where there are 7 (PR 1.2, and PR 1.3: an anchor that still
// matches is not an anchor that still points at the right thing).
const ADDITIVE = /!\s*(\w+)\[(?:String\()?\w+\.id\)?\][^\n]{0,80}\{[^\n]{0,120}\.push\(/g;
function additiveSites(src) {
  ADDITIVE.lastIndex = 0;
  const out = [];
  let m;
  while ((m = ADDITIVE.exec(src)) !== null) {
    const head = src.slice(0, m.index);
    const fns = head.match(/function\s+(\w+)\s*\(/g) || [];
    const last = fns.length ? fns[fns.length - 1].replace(/function\s+/, '').replace(/\s*\($/, '') : '?';
    out.push(last);
  }
  return out;
}
const APP_FILES = () => fs.readdirSync(ROOT).filter((f) => /^sairn\w*\.html$|^stonedesk\.html$/.test(f));

test('the detector is not vacuous -- it finds the shape it is looking for', () => {
  // An arm whose regex silently stopped matching would report the whole
  // platform converted. So it is proved against a fixture in BOTH directions
  // before its answer about real files is used for anything.
  const additive = "rows.forEach(function(r){ if(r&&r.id&&!have[String(r.id)]){ local.push(r); } });";
  const serverWins = "rows.forEach(function(r){ var at=idx[String(r.id)]; if(at===undefined){local.push(r);return;} local[at]=r; });";
  assert.strictEqual(additiveSites('function xHydrate(){' + additive + '}').length, 1,
    'the detector no longer recognises the additive merge it exists to find');
  assert.strictEqual(additiveSites('function xHydrate(){' + serverWins + '}').length, 0,
    'the detector fires on a server-wins merge, so its count means nothing');
});

test('the converted apps no longer carry the additive shape at all', () => {
  APPS.forEach((A) => {
    assert.deepStrictEqual(additiveSites(read(A.file)), [],
      A.app + ' still contains an additive-only merge');
  });
});

test('every app still hydrating additively is in PENDING, with the right site count', () => {
  const found = {};
  APP_FILES().forEach((f) => {
    const sites = additiveSites(read(f));
    if (sites.length) found[f] = sites;
  });
  const listed = {};
  PENDING.forEach((p) => { listed[p.file] = p.fns; });
  assert.deepStrictEqual(Object.keys(found).sort(), Object.keys(listed).sort(),
    'apps hydrating additively: ' + Object.keys(found).sort().join(', ')
    + '  |  PENDING names: ' + Object.keys(listed).sort().join(', '));
  Object.keys(found).forEach((f) => {
    assert.deepStrictEqual(found[f].sort(), listed[f].slice().sort(),
      f + ': the functions PENDING names are not the ones still doing it');
    const p = PENDING.find((x) => x.file === f);
    assert.strictEqual(p.sites, found[f].length, f + ': PENDING says ' + p.sites + ' sites, found ' + found[f].length);
  });
});

test('every PENDING entry carries a real reason', () => {
  PENDING.forEach((p) => {
    assert.ok(p.why && p.why.length > 40, p.file + ': a bare exclusion is not a reason');
  });
});

test('the converted apps carry the SAME rule, not two readings of it', () => {
  // Compared by behaviour above; compared here by the CODE, with comments
  // stripped -- a per-app note (SAIRNdesign's sdn_clients session caveat) is a
  // legitimate difference in prose, and an arm that failed on it would be
  // retrained to ignore real divergence too.
  const strip = (s) => s.split('\n').filter((l) => !l.trim().startsWith('//')).join('\n');
  const shapes = APPS.map((A) => strip(lift(read(A.file), 'async function sdnHydrateAll()'))
    .replace(new RegExp(A.keyVar, 'g'), 'SYNCED_KEY')
    .replace(new RegExp(A.prefix + 'SyncedRead', 'g'), 'SyncedRead')
    .replace(new RegExp(A.listVar, 'g'), 'SYNC_RESOURCES')
    .replace(new RegExp(A.licenseFn, 'g'), 'LicenseKey')
    .replace(/sdnData\('read',key[^)]*\)/g, "sdnData('read',key)")
    .replace(/\s+/g, ' ').trim());
  assert.strictEqual(shapes[0], shapes[1],
    'the two hydrates differ once names and comments are normalised -- one rule has become two');
});

// ═══════════════════════════════════════════════════════════════════════════
(async () => {
  for (const item of queue) {
    if (item.section) { console.log('--- ' + item.section + ' ---'); continue; }
    try { await item.fn(); console.log('  ok   ' + item.name); pass++; }
    catch (e) { console.log('  FAIL ' + item.name + '\n       ' + e.message); fail++; }
  }
  console.log('\nserver_wins_hydration: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
