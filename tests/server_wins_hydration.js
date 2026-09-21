// tests/server_wins_hydration.js
//
// Run:  node tests/server_wins_hydration.js
//
// ── ONE RULE, DRIVEN ACROSS EVERY APP THAT IMPLEMENTS IT ───────────────────
// # REQUIREMENT: once a record's id exists on BOTH sides, hydration replaces
//   the local copy with the server's -- except for a record whose own FIRST
//   push has never landed, which keeps its local value; a one-time read-only
//   bootstrap records what a pre-existing install already holds WITHOUT
//   overwriting any of it; and the rule is the SAME rule in every app that
//   hydrates, not a per-app or per-resource judgement call
//
// Michael's decisions, 2026-09-21. Two of them, a few hours apart.
//
// ── WHAT IT REPLACED ──────────────────────────────────────────────────────
// Additive-only merge: "a locally present id is never overwritten by this
// merge", disclosed in every app as a limitation about two devices editing the
// SAME record. THAT UNDERSTATED IT. It was never only about concurrent edits:
// ANY field corrected on the server was invisible FOREVER to a device that
// already held that id, with nothing racing and nothing ever reconciling them.
//
// ── AND THE FIRST VERSION OF THE FIX HAD A COST THAT WAS ALSO DECIDED ─────
// An install predating server-wins has no synced map, so "may this be
// overwritten?" had no recorded answer for anything in it. The first version
// treated an absent map as PERMISSION -- effective immediately, and it
// silently discarded whatever local edit was sitting there at the moment of
// upgrade. THE SHIPPED ANSWER IS THE OTHER ONE: a one-time, local-only pass
// marks every id the device already holds as seeded, overwrites nothing, and
// suppresses overwriting for the rest of that page load. From the next load
// on, the map is the authority and ABSENT means genuinely never pushed.
//
// THE BOUNDED COST, STATED RATHER THAN HIDDEN: a correction made on the server
// BEFORE a given device runs its bootstrap does not reach that device until
// the load AFTER the bootstrap. One extra hydrate of staleness, once per
// device. Section 3 asserts that cost rather than describing it.
//
// ── WHY THIS SUITE DRIVES EVERY APP FROM ONE TABLE ────────────────────────
// These are single-file apps with no shared module, so the rule necessarily
// exists as one copy per app -- SEVEN of them now. Seven copies is seven
// chances to drift, and a per-app suite would let them drift while every suite
// stayed green. The arms below are written ONCE and run against every entry in
// APPS, and section 6 asserts the copies are the same code modulo their names
// and the two declared SEAMS.
//
// WHAT IS LIFTED, NOT RETYPED: each app's real ld()/sdLoad(), st(), the
// synced-id helpers, the bootstrap, the two seams and the merge are read out
// of the shipped .html and executed. A retyped fixture drifts from the code it
// exists to check.
//
// WHAT THIS SUITE DOES NOT DO, said plainly: it does not drive the seven
// HYDRATE functions end to end. They take seven different shapes -- one loop,
// eleven separate functions, a pair-loop, a transport that returns {ok,data}
// rather than rows -- and seven bespoke harnesses would be seven more things
// to keep in step. Instead the merge and the bootstrap are driven directly for
// all seven, and section 5 asserts at SOURCE level that every hydrate really
// calls them. That is a weaker link than execution and it is named here rather
// than left to be assumed.
//
// The negative control is tests/run_server_wins_hydration_sabotage_probe.py.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const read = (f) => fs.readFileSync(path.join(ROOT, f), 'utf8').replace(/\r\n/g, '\n');

// ── THE TABLE ──────────────────────────────────────────────────────────────
// `sample` is one real resource out of that app's own list.
const APPS = [
  { app: 'sairnlegacy',  file: 'sairnlegacy.html',  prefix: 'leg', up: 'LEG',
    listVar: 'LEG_SYNC_RESOURCES', sample: 'leg_cases',
    hydrates: ['sdnHydrateAll'], transport: 'legMarkSynced' },
  { app: 'sairndesign',  file: 'sairndesign.html',  prefix: 'sdn', up: 'SDN',
    listVar: 'SDN_SYNC_RESOURCES', sample: 'sdn_projects',
    hydrates: ['sdnHydrateAll'], transport: 'sdnMarkSynced' },
  { app: 'sairnlaw',     file: 'sairnlaw.html',     prefix: 'law', up: 'LAW',
    listVar: 'LAW_SYNC_RESOURCES', sample: 'law_timeentries',
    hydrates: ['lawHydrateAll'], transport: 'lawMarkSynced' },
  { app: 'sairnsenior',  file: 'sairnsenior.html',  prefix: 'sen', up: 'SEN',
    listVar: 'SEN_SYNCED', sample: 'sen_clients',
    hydrates: ['senHydrateClients', 'senHydrateCaregivers', 'senHydrateVisits',
               'senHydrateReferrals', 'senHydrateOrg', 'senHydrateTraining',
               'senHydrateClaims', 'senHydratePayerContracts', 'senHydrateFranchise',
               'senHydratePayRates', 'senHydrateAuthorizations'],
    transport: 'senMarkSynced' },
  { app: 'stonedesk',    file: 'stonedesk.html',    prefix: 'sd',  up: 'SD',
    listVar: 'SD_SYNCED', sample: 'sd_invoices',
    hydrates: ['sdHydrateAll', 'sdHydrateCustomers'], transport: 'sdMarkSynced',
    // StoneDesk reads through sdLoad(), not ld(), and its st() calls a backup
    // hook. Both are lifted or stubbed rather than reimplemented.
    ldFn: 'sdLoad',
    stubs: [
      'var sdSyncSuppressed=false;',
      'function sdWhileSuppressed(fn){var w=sdSyncSuppressed;sdSyncSuppressed=true;try{return fn();}finally{sdSyncSuppressed=w;}}',
      'function sdBackupHookFailed(){}',
      'var SD_SYNCED_ON={};',
      'function ld(k,d){return sdLoad(k,d);}',
    ].join('\n') },
  { app: 'sairnbiz',     file: 'sairnbiz.html',     prefix: 'sb',  up: 'SB',
    listVar: 'SB_SYNCED', sample: 'sb_invs',
    hydrates: ['sbHydrateAll'], transport: 'sbMarkSynced',
    stubs: 'var sbSyncPaused=false;' },
  { app: 'sairnfreedom', file: 'sairnfreedom.html', prefix: 'sf',  up: 'SF',
    listVar: 'SF_SYNCED', sample: 'sf_members',
    hydrates: ['sfHydrateAll'], transport: 'sfMarkSynced',
    stubs: 'var sfSyncSuppressed=false;' },
];

// ── NOT CONVERTED, NAMED RATHER THAN OMITTED ──────────────────────────────
// Michael's call, and each is held for a reason that is not "we ran out of
// time". Section 6 asserts this list is EXACTLY what the detector finds: an
// app converted and left here FAILS, and one that is neither converted nor
// listed FAILS.
const PENDING = [
  { file: 'sairncare.html', sites: 6,
    fns: ['alfHydrateResidents', 'alfHydrateMar', 'alfHydrateStaff',
          'alfHydrateBilling', 'alfHydrateIncidents', 'alfHydrateActivities'],
    why: 'HELD DELIBERATELY. One of the six is the MAR -- a medication '
       + 'administration record. "The server copy wins" there is a '
       + 'clinical-documentation decision about whose entry survives a '
       + 'disagreement, not a mechanical sync one, and it is not this session\'s to make.' },
  { file: 'sairnbuild.html', sites: 2, fns: ['bldHydrateAll', 'bldHydrateBids'],
    why: 'HELD DELIBERATELY. st() pushes to the server itself via '
       + 'bldSyncCollection(), suppressed during hydration by a bldSeeding flag '
       + 'that bldHydrateAll sets and bldHydrateBids does NOT. Server-wins '
       + 'writes more often, so that asymmetry has to be READ and settled as '
       + 'part of the conversion rather than inherited.' },
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
function liftFn(src, name) {
  const a = src.indexOf('async function ' + name + '(');
  const b = src.indexOf('function ' + name + '(');
  const at = (a >= 0 && (b < 0 || a < b)) ? a : b;
  assert.ok(at >= 0, 'function not found: ' + name);
  return braceBody(src, at);
}
function liftVar(src, name) {
  const at = src.indexOf('var ' + name + '=');
  assert.ok(at > 0, name + ' not found');
  const semi = src.indexOf(';', at);
  const open = src.indexOf('[', at);
  if (open > 0 && open < semi) {
    const close = src.indexOf('];', at);
    assert.ok(close > at, name + ' unterminated');
    return src.slice(at, close + 2);
  }
  return src.slice(at, semi + 1);
}

// opts.local   {resource: [records]}
// opts.synced  {resource:[ids]} | 'corrupt' | undefined
// opts.booted  true to pretend the bootstrap already ran on an earlier load
function harness(A, opts) {
  opts = opts || {};
  const src = read(A.file);
  const store = {};
  const syncedKey = A.prefix + '_synced_ids';
  const bootKey = A.prefix + '_synced_bootstrap';
  Object.keys(opts.local || {}).forEach((k) => { store[k] = JSON.stringify(opts.local[k]); });
  if (opts.synced === 'corrupt') store[syncedKey] = '{not json';
  else if (opts.synced !== undefined) store[syncedKey] = JSON.stringify(opts.synced);
  if (opts.booted) store[bootKey] = '1';

  const localStorage = {
    getItem: (k) => (Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
  };
  const ctx = {
    JSON, Object, Array, String, Number, Math, Promise, Date,
    console: { warn: () => {}, error: () => {} },
    localStorage, __store: store,
  };
  vm.createContext(ctx);
  const quota = (src.match(/(\w*IsQuotaError)\(e\)/) || [])[1];
  const parts = [
    quota ? 'function ' + quota + '(e){return false;}' : '',
    liftFn(src, 'st'),
    liftFn(src, A.ldFn || 'ld'),
    A.stubs || '',
    liftVar(src, A.up + '_SYNCED_KEY'),
    liftVar(src, A.up + '_BOOTSTRAP_KEY'),
    'var ' + A.prefix + 'BootstrappedNow=false;',
    liftFn(src, A.prefix + 'SyncedRead'),
    liftFn(src, A.prefix + 'MarkSynced'),
    liftFn(src, A.prefix + 'SyncedBootstrap'),
    liftFn(src, A.prefix + 'HydrateLoad'),
    liftFn(src, A.prefix + 'HydrateStore'),
    liftFn(src, A.prefix + 'ServerWinsMerge'),
    'function __merge(k,r){return ' + A.prefix + 'ServerWinsMerge(k,r);}',
    'function __bootstrap(l){return ' + A.prefix + 'SyncedBootstrap(l);}',
    'function __mark(r,i){return ' + A.prefix + 'MarkSynced(r,i);}',
    'function __bootedNow(){return ' + A.prefix + 'BootstrappedNow;}',
  ];
  vm.runInContext(parts.join('\n'), ctx);

  ctx.merge = ctx.__merge;
  ctx.bootstrap = (list) => ctx.__bootstrap(list || [A.sample]);
  ctx.mark = ctx.__mark;
  ctx.bootedNow = ctx.__bootedNow;
  ctx.local = (k) => JSON.parse(store[k] || 'null');
  ctx.synced = () => { try { return JSON.parse(store[syncedKey]); } catch (e) { return store[syncedKey]; } };
  ctx.__bootKey = bootKey;
  ctx.__syncedKey = syncedKey;
  return ctx;
}

const each = (name, fn) => APPS.forEach((A) => test('[' + A.app + '] ' + name, () => fn(A)));

// ═══════════════════════════════════════════════════════════════════════════
section('1. server-wins: a record held on BOTH sides takes the server copy');

each('a synced id is REPLACED by the server copy', (A) => {
  const c = harness(A, {
    local: { [A.sample]: [{ id: 'R-1', status: 'Open', note: 'stale local' }] },
    synced: { [A.sample]: ['R-1'] }, booted: true,
  });
  c.merge(A.sample, [{ id: 'R-1', status: 'Closed', note: 'server truth' }]);
  const row = c.local(A.sample).find((r) => r.id === 'R-1');
  assert.strictEqual(row.status, 'Closed', 'the local copy survived -- this is the additive behaviour');
  assert.strictEqual(row.note, 'server truth');
});

each('a field the server DROPPED is gone locally -- replace, not merge', (A) => {
  const c = harness(A, {
    local: { [A.sample]: [{ id: 'R-1', status: 'Open', localOnly: 'kept?' }] },
    synced: { [A.sample]: ['R-1'] }, booted: true,
  });
  c.merge(A.sample, [{ id: 'R-1', status: 'Closed' }]);
  assert.ok(!('localOnly' in c.local(A.sample).find((r) => r.id === 'R-1')),
    'a local-only field survived -- that is a field MERGE, not server-wins');
});

each('a server record not held locally is appended and marked synced', (A) => {
  const c = harness(A, {
    local: { [A.sample]: [{ id: 'R-1' }] }, synced: { [A.sample]: ['R-1'] }, booted: true,
  });
  c.merge(A.sample, [{ id: 'R-1' }, { id: 'R-2', from: 'other device' }]);
  assert.deepStrictEqual(c.local(A.sample).map((r) => r.id).sort(), ['R-1', 'R-2']);
  assert.ok(c.synced()[A.sample].indexOf('R-2') !== -1,
    'a record that came FROM the server was not recorded as being on it');
});

each('a failed read changes nothing and returns null', (A) => {
  const c = harness(A, { local: { [A.sample]: [{ id: 'R-9', note: 'mine' }] }, synced: {}, booted: true });
  assert.strictEqual(c.merge(A.sample, null), null);
  assert.strictEqual(c.local(A.sample)[0].note, 'mine');
});

// ═══════════════════════════════════════════════════════════════════════════
section('2. the carve-out: a record whose FIRST push never landed keeps its value');

each('an UNSYNCED id is NOT overwritten, even though the server has that id', (A) => {
  const c = harness(A, {
    local: { [A.sample]: [{ id: 'R-1', note: 'never pushed' }] },
    synced: { [A.sample]: [] }, booted: true,
  });
  c.merge(A.sample, [{ id: 'R-1', note: 'somebody else' }]);
  assert.strictEqual(c.local(A.sample).find((r) => r.id === 'R-1').note, 'never pushed',
    'a record whose own push never landed was overwritten by a stranger');
});

each('and being kept does NOT record it as synced -- two merges, not one', (A) => {
  const c = harness(A, {
    local: { [A.sample]: [{ id: 'R-1', note: 'never pushed' }] },
    synced: { [A.sample]: [] }, booted: true,
  });
  c.merge(A.sample, [{ id: 'R-1', note: 'somebody else' }]);
  assert.ok((c.synced()[A.sample] || []).indexOf('R-1') === -1,
    'keeping it also marked it synced, which hands the NEXT merge permission to overwrite it');
  c.merge(A.sample, [{ id: 'R-1', note: 'somebody else' }]);
  assert.strictEqual(c.local(A.sample).find((r) => r.id === 'R-1').note, 'never pushed',
    'it survived one merge and not two');
});

each('once its push DOES land, the same record becomes overwritable', (A) => {
  const c = harness(A, {
    local: { [A.sample]: [{ id: 'R-1', note: 'pending' }] },
    synced: { [A.sample]: [] }, booted: true,
  });
  c.merge(A.sample, [{ id: 'R-1', note: 'server truth' }]);
  assert.strictEqual(c.local(A.sample)[0].note, 'pending');
  c.mark(A.sample, 'R-1');
  c.merge(A.sample, [{ id: 'R-1', note: 'server truth' }]);
  assert.strictEqual(c.local(A.sample)[0].note, 'server truth',
    'the carve-out outlived the push that was supposed to end it');
});

// ═══════════════════════════════════════════════════════════════════════════
section('3. the one-time bootstrap: it records, and it does not overwrite');

each('it marks every id the device already holds', (A) => {
  const c = harness(A, { local: { [A.sample]: [{ id: 'A-1' }, { id: 'A-2' }] } });
  assert.strictEqual(c.bootstrap([A.sample]), 'ran');
  assert.deepStrictEqual((c.synced()[A.sample] || []).sort(), ['A-1', 'A-2']);
});

each('it OVERWRITES NOTHING while it runs -- no network, no record touched', (A) => {
  const c = harness(A, { local: { [A.sample]: [{ id: 'A-1', note: 'local' }] } });
  c.bootstrap([A.sample]);
  assert.strictEqual(c.local(A.sample)[0].note, 'local');
  assert.deepStrictEqual(c.local(A.sample).map((r) => r.id), ['A-1']);
});

each('AND NOTHING IS OVERWRITTEN FOR THE REST OF THAT LOAD -- the bounded cost', (A) => {
  // The cost the decision accepted, asserted rather than described: a
  // correction the server already holds does not reach this device until the
  // load AFTER its bootstrap.
  const c = harness(A, { local: { [A.sample]: [{ id: 'A-1', note: 'stale' }] } });
  c.bootstrap([A.sample]);
  assert.strictEqual(c.bootedNow(), true);
  c.merge(A.sample, [{ id: 'A-1', note: 'server truth' }]);
  assert.strictEqual(c.local(A.sample)[0].note, 'stale',
    'the bootstrap load overwrote a record -- the whole point of it is that it does not');
  assert.ok((c.synced()[A.sample] || []).indexOf('A-1') !== -1,
    'the id was not recorded, so the NEXT load would treat it as never-pushed');
});

each('and on the NEXT load the same record IS taken from the server', (A) => {
  // The other half of the same cost: one hydrate of staleness, not forever.
  const c = harness(A, { local: { [A.sample]: [{ id: 'A-1', note: 'stale' }] } });
  c.bootstrap([A.sample]);
  const carried = c.synced();
  const next = harness(A, {
    local: { [A.sample]: [{ id: 'A-1', note: 'stale' }] }, synced: carried, booted: true,
  });
  next.merge(A.sample, [{ id: 'A-1', note: 'server truth' }]);
  assert.strictEqual(next.local(A.sample)[0].note, 'server truth');
});

each('it runs ONCE -- a second call is a no-op', (A) => {
  const c = harness(A, { local: { [A.sample]: [{ id: 'A-1' }] } });
  assert.strictEqual(c.bootstrap([A.sample]), 'ran');
  assert.strictEqual(c.bootstrap([A.sample]), 'already');
  const c2 = harness(A, { local: { [A.sample]: [{ id: 'A-1' }] }, booted: true });
  assert.strictEqual(c2.bootstrap([A.sample]), 'already');
  assert.strictEqual(c2.bootedNow(), false, 'an already-bootstrapped load suppressed overwriting anyway');
});

each('AFTER the bootstrap, absent-from-map means PROTECTED, not overwritable', (A) => {
  // The meaning that changed. Before the bootstrap existed, a resource absent
  // from the map meant "never seeded" and therefore "overwrite freely". A
  // record created AFTER the bootstrap and never pushed is absent for the
  // opposite reason, and must be kept.
  const c = harness(A, { local: { [A.sample]: [{ id: 'A-1' }] } });
  c.bootstrap([A.sample]);
  const carried = c.synced();
  const next = harness(A, {
    local: { [A.sample]: [{ id: 'A-1' }, { id: 'NEW-1', note: 'created after the bootstrap' }] },
    synced: carried, booted: true,
  });
  next.merge(A.sample, [{ id: 'NEW-1', note: 'a stranger with the same id' }]);
  assert.strictEqual(next.local(A.sample).find((r) => r.id === 'NEW-1').note,
    'created after the bootstrap',
    'a record created after the bootstrap and never pushed was overwritten');
});

each('a record with NO id is not marked -- the map must not fill with junk', (A) => {
  // Dropping the id guard marks the string 'undefined' as a seeded id. Nothing
  // would ever notice: the map is bigger, no record is wrong, and the first
  // real record that happens to arrive with no id becomes overwritable.
  const c = harness(A, { local: { [A.sample]: [{ id: 'A-1' }, { note: 'no id at all' }] } });
  c.bootstrap([A.sample]);
  assert.deepStrictEqual((c.synced()[A.sample] || []).sort(), ['A-1'],
    'the bootstrap marked an id that is not in the store');
});

each('it refuses to run on an UNREADABLE map, and does not claim it did', (A) => {
  const c = harness(A, { local: { [A.sample]: [{ id: 'A-1' }] }, synced: 'corrupt' });
  assert.strictEqual(c.bootstrap([A.sample]), 'unreadable');
  assert.strictEqual(c.__store[c.__bootKey], undefined,
    'the done-flag was set over a map that could not be read, so the bootstrap can never run');
  assert.strictEqual(c.__store[c.__syncedKey], '{not json');
});

// ═══════════════════════════════════════════════════════════════════════════
section('4. an unreadable map is a THIRD answer, failing toward keeping local data');

each('a CORRUPT synced map overwrites NOTHING', (A) => {
  const c = harness(A, {
    local: { [A.sample]: [{ id: 'R-1', note: 'local' }] }, synced: 'corrupt', booted: true,
  });
  c.merge(A.sample, [{ id: 'R-1', note: 'server' }]);
  assert.strictEqual(c.local(A.sample)[0].note, 'local',
    'a map that could not be read was treated as permission to overwrite');
});

each('a corrupt map is not silently replaced, and the merge still appends', (A) => {
  const c = harness(A, {
    local: { [A.sample]: [{ id: 'R-1' }] }, synced: 'corrupt', booted: true,
  });
  c.merge(A.sample, [{ id: 'R-1' }, { id: 'R-2' }]);
  assert.strictEqual(c.__store[c.__syncedKey], '{not json',
    'the unreadable map was overwritten -- whatever it held is now unrecoverable');
  assert.deepStrictEqual(c.local(A.sample).map((r) => r.id).sort(), ['R-1', 'R-2']);
});

// ═══════════════════════════════════════════════════════════════════════════
section('5. what the transport and the hydrates must say -- checked at SOURCE');

each('the transport records an id when a WRITE really lands', (A) => {
  // SOURCE level, and the reason is worth stating: the seven transports have
  // seven shapes (one returns d.data, one returns {ok,data,provisioned}, one
  // is async/await with a status bag). Driving all seven would be seven more
  // fixtures to keep in step. What must be true of all of them is one line, so
  // that is what is asserted -- weaker than execution, and named as weaker.
  const src = read(A.file);
  // [\s\S]{0,200} rather than [^\n]*: StoneDesk's transport puts the guard and
  // the call on separate lines inside a try. A one-line anchor would have
  // reported the one app that wrote it most carefully as the one missing it.
  const re = new RegExp("action\\s*===\\s*'write'[\\s\\S]{0,200}?" + A.transport + "\\(resource,\\s*payload\\.id\\)");
  assert.ok(re.test(src),
    A.app + ': no guarded ' + A.transport + '(resource, payload.id) in the transport');
});

each('every hydrate calls the shared merge AND the bootstrap', (A) => {
  const src = read(A.file);
  A.hydrates.forEach((fn) => {
    const body = liftFn(src, fn);
    assert.ok(body.indexOf(A.prefix + 'ServerWinsMerge(') !== -1,
      A.app + '.' + fn + ' does not call ' + A.prefix + 'ServerWinsMerge');
    assert.ok(body.indexOf(A.prefix + 'SyncedBootstrap(') !== -1,
      A.app + '.' + fn + ' does not run the bootstrap before merging');
  });
});

test('[sairnsenior] SEN_SYNCED is exactly the resources its hydrates read', () => {
  // The list was assembled from eleven functions. A list assembled by hand is
  // a list that goes stale, so it is checked against the functions themselves.
  const src = read('sairnsenior.html');
  const declared = (liftVar(src, 'SEN_SYNCED').match(/'(sen_\w+)'/g) || []).map((x) => x.replace(/'/g, ''));
  const used = new Set();
  APPS.find((A) => A.app === 'sairnsenior').hydrates.forEach((fn) => {
    (liftFn(src, fn).match(/senData\('read','(sen_\w+)'/g) || [])
      .forEach((m) => used.add(m.replace(/.*'(sen_\w+)'$/, '$1')));
  });
  assert.deepStrictEqual(declared.slice().sort(), Array.from(used).sort());
});

test('[stonedesk] the single-OBJECT resources are left out of server-wins, deliberately', () => {
  // They are one blob with no ids, so there is nothing to match on and no
  // first-push carve-out to apply. The existing adopt-or-leave rule stands and
  // this arm exists so a later sweep cannot quietly fold them in.
  const body = liftFn(read('stonedesk.html'), 'sdHydrateAll');
  assert.ok(body.indexOf('SD_SYNCED_OBJECT[key]') !== -1, 'the object branch is gone');
  assert.ok(body.indexOf('localStorage.getItem(key)!==null') !== -1,
    'the adopt-only-on-a-device-that-has-none rule is gone');
});

// ═══════════════════════════════════════════════════════════════════════════
section('6. it is ONE rule, and the table is not quietly missing an app');

const ADDITIVE = /!\s*(\w+)\[(?:String\()?\w+\.id\)?\][^\n]{0,80}\{[^\n]{0,120}\.push\(/;
function hydrateBodies(src) {
  const out = [];
  const re = /function\s+(\w*[Hh]ydrate\w*)\s*\(/g;
  let m;
  while ((m = re.exec(src)) !== null) {
    const chunk = src.slice(m.index, m.index + 3000);
    const e = chunk.indexOf('\n}');
    out.push([m[1], e > 0 ? chunk.slice(0, e + 2) : chunk]);
  }
  return out;
}
const additiveSites = (src) =>
  hydrateBodies(src).filter(([, b]) => ADDITIVE.test(b)).map(([n]) => n);
const APP_FILES = () => fs.readdirSync(ROOT).filter((f) => /^sairn\w*\.html$|^stonedesk\.html$/.test(f));

test('the detector is not vacuous -- it finds the shape, and only that shape', () => {
  const additive = 'function xHydrate(){ rows.forEach(function(r){ if(r&&r.id&&!have[String(r.id)]){ local.push(r); } });\n}';
  const wins = 'function xHydrate(){ var c=xServerWinsMerge(key,rows);\n}';
  assert.deepStrictEqual(additiveSites(additive), ['xHydrate'],
    'the detector no longer recognises the additive merge it exists to find');
  assert.deepStrictEqual(additiveSites(wins), [],
    'the detector fires on a server-wins hydrate, so its count means nothing');
});

test('no converted app carries the additive shape any more', () => {
  APPS.forEach((A) => {
    assert.deepStrictEqual(additiveSites(read(A.file)), [], A.app + ' still merges additively');
  });
});

test('every app still hydrating additively is in PENDING, with the right functions', () => {
  const found = {};
  APP_FILES().forEach((f) => { const s = additiveSites(read(f)); if (s.length) found[f] = s; });
  const listed = {};
  PENDING.forEach((p) => { listed[p.file] = p.fns; });
  assert.deepStrictEqual(Object.keys(found).sort(), Object.keys(listed).sort(),
    'additive: ' + Object.keys(found).sort().join(', ') + '  |  PENDING: ' + Object.keys(listed).sort().join(', '));
  Object.keys(found).forEach((f) => {
    assert.deepStrictEqual(found[f].sort(), listed[f].slice().sort(), f + ': wrong functions');
    assert.strictEqual(PENDING.find((x) => x.file === f).sites, found[f].length, f + ': wrong site count');
  });
});

test('NOBODY hydrates with an UNGUARDED overwrite -- the other wrong rule', () => {
  // sairnsenior shipped FOUR hydrates that already overwrote any local record
  // whose id the server held, with no carve-out at all, while SEVEN others in
  // the same file were additive-only. One file, two opposite conflict rules,
  // neither disclosed -- and invisible to the additive detector, which is why
  // this second one exists. An overwrite is only allowed through the shared
  // merge.
  const bad = [];
  APP_FILES().forEach((f) => {
    hydrateBodies(read(f)).forEach(([name, body]) => {
      // The RHS must be the SAME variable whose .id is the key -- `byId[c.id]=c`.
      // Without that it also matches `have[String(r.id)]=true`, which is a
      // seen-set and not an overwrite at all, and the arm fires on every
      // additive hydrate instead of the shape it exists to find.
      const overwrites = /\[\s*(?:String\()?(\w+)\.id\)?\s*\]\s*=\s*\s*;/.test(body);
      if (overwrites && !/ServerWinsMerge\(/.test(body)) bad.push(f + ':' + name);
    });
  });
  assert.deepStrictEqual(bad, [],
    'hydrates overwriting local records outside the shared merge: ' + bad.join(', '));
});

test('every PENDING entry carries a real reason', () => {
  PENDING.forEach((p) => assert.ok(p.why && p.why.length > 60, p.file + ': a bare exclusion is not a reason'));
});

test('all seven copies are the SAME rule, modulo names and the two declared seams', () => {
  // Compared as CODE with comments stripped and prefixes normalised. The two
  // SEAMS are excluded because they are the DECLARED per-app difference --
  // four of these apps push to the server from inside st() and one reads
  // through sdLoad() -- and this section's whole claim is that this is the
  // ONLY difference.
  const strip = (s) => s.split('\n').filter((l) => !l.trim().startsWith('//')).join('\n');
  const norm = (A, body) => strip(body)
    .replace(new RegExp(A.up + '_SYNCED_KEY', 'g'), 'SYNCED_KEY')
    .replace(new RegExp(A.up + '_BOOTSTRAP_KEY', 'g'), 'BOOTSTRAP_KEY')
    .replace(new RegExp(A.prefix + 'SyncedRead', 'g'), 'SyncedRead')
    .replace(new RegExp(A.prefix + 'BootstrappedNow', 'g'), 'BootstrappedNow')
    .replace(new RegExp(A.prefix + 'HydrateLoad', 'g'), 'HydrateLoad')
    .replace(new RegExp(A.prefix + 'HydrateStore', 'g'), 'HydrateStore')
    .replace(new RegExp(A.prefix + 'SyncedBootstrap', 'g'), 'SyncedBootstrap')
    .replace(new RegExp(A.prefix + 'ServerWinsMerge', 'g'), 'ServerWinsMerge')
    .replace(new RegExp(A.prefix + 'MarkSynced', 'g'), 'MarkSynced')
    .replace(/SAIRN\w+|StoneDesk/g, 'APP')
    .replace(/\s+/g, ' ').trim();
  ['SyncedRead', 'MarkSynced', 'SyncedBootstrap', 'ServerWinsMerge'].forEach((fn) => {
    const shapes = APPS.map((A) => norm(A, liftFn(read(A.file), A.prefix + fn)));
    shapes.forEach((s, i) => {
      assert.strictEqual(s, shapes[0],
        APPS[i].app + "'s " + fn + ' differs from ' + APPS[0].app + "'s once names are normalised");
    });
  });
});

test('the seams are one line of intent each, and the auto-push apps really suppress', () => {
  // A store seam that forgot to suppress would echo the server's own rows back
  // to the server on every hydrate -- quietly, and only under load.
  const SUPPRESSORS = { sairnfreedom: 'sfSyncSuppressed', sairnbiz: 'sbSyncPaused', stonedesk: 'sdWhileSuppressed' };
  APPS.forEach((A) => {
    const store = liftFn(read(A.file), A.prefix + 'HydrateStore');
    const need = SUPPRESSORS[A.app];
    if (need) {
      assert.ok(store.indexOf(need) !== -1, A.app + ': the store seam does not suppress the server push');
      assert.ok(/finally/.test(store) || A.app === 'stonedesk',
        A.app + ': the suppression has no finally -- a throw leaves the app un-backed-up for the session');
    } else {
      assert.ok(/return st\(key,value\);/.test(store), A.app + ': the store seam is not a plain st()');
    }
  });
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
