// tests/sairnbuild_backup_pending.js
//
// Run:  node tests/sairnbuild_backup_pending.js
//
// SAIRNbuild's server backup and the records it silently failed to send --
// driven verbatim from sairnbuild.html.
//
// COMPANION TO tests/sairnbuild_server_backup.js, which covers the other half:
// how MUCH the hook pushes (only what changed, never during seed(), never
// after a failed local write) and that hydration is additive. That file is
// synchronous throughout; this one is async because the queue is written from
// the push promise's callback, which is why it is a second file rather than a
// second section.
//
// THE DEFECT, and why it could not be found by reading this repo:
//
// st() hooks every write and hands changed records to bldSyncCollection(),
// which pushes each one with bldData('write', ...). bldData() returns null on
// EVERY failure -- 400, 503, transport -- after a console.warn, and
// bldSyncCollection ignored the result entirely. That alone is the ordinary
// "fails quietly" shape. What made it permanent is the optimisation directly
// above it:
//
//     if (before[String(r.id)] === now) return;   // unchanged -- nothing to push
//
// A record that failed to push is unchanged the next time its collection is
// written, so it is SKIPPED. One failure and that record is on this device and
// nowhere else, for good.
//
// MEASURED AGAINST THE LIVE SERVER ON 2026-09-04, not inferred from the code:
// api/sd-data.js answered
//
//     {"ok":true,"data":[],"provisioned":false}
//
// for bld_jobs, bld_lien_waivers, bld_timesheet and bld_incidents under
// BLD-PINNACLE-2026. sql/sairnbuild_data_schema.sql had never been run, so
// EVERY push this feature has ever attempted failed, for all thirty
// collections, and nothing on any screen said so. The read half returns
// provisioned:false with ok:true, so the client could not tell "the migration
// was never run" from "you have no records yet" -- and the write half's 503
// NOT_PROVISIONED reached a console.warn and stopped.
//
// The consequence that matters most is the one about the FUTURE: without a
// record of what failed, running the migration would not back-fill anything.
// Only records edited afterwards would ever be pushed, and the existing
// business record -- jobs, lien waivers, safety incidents -- would stay
// unbacked while the app looked healthy.
//
// The functions below are EXTRACTED from sairnbuild.html and driven against a
// stubbed bldData that can refuse. The network boundary is the only thing
// stubbed; st(), bldSyncCollection(), the pending queue and the retry are the
// real ones.

const fs = require('fs');
const path = require('path');

const HTML = path.join(__dirname, '..', 'sairnbuild.html');
const src = fs.readFileSync(HTML, 'utf8');

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

function balanced(start) {
  let i = src.indexOf('{', start), depth = 0;
  for (; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') { depth--; if (!depth) return src.slice(start, i + 1); }
  }
  throw new Error('unbalanced from ' + start);
}
function fn(decl) {
  const i = src.indexOf(decl);
  if (i < 0) throw new Error('not found: ' + decl);
  return balanced(i);
}
// Tolerant of both `var x = 1;` and `var x=1;` -- sairnbuild.html uses both.
function decl(name) {
  const m = src.match(new RegExp('var ' + name + '\\s*=\\s*([^;]+);'));
  if (!m) throw new Error('not found: var ' + name);
  return 'var ' + name + ' = ' + m[1] + ';';
}

// A localStorage stub. Deliberately never refuses here: storage failure is
// already covered by st()'s own return value, and the subject of this file is
// what happens after the LOCAL write succeeded.
function makeStore() {
  const data = {};
  return {
    store: {
      getItem: (k) => (k in data ? data[k] : null),
      setItem: (k, v) => { data[k] = v; }
    },
    data
  };
}

// `writes` records every push attempt so a test can assert that something did
// NOT happen -- which is most of the point here.
function makeServer(behaviour) {
  const writes = [];
  const api = function (action, resource, payload) {
    writes.push({ action, resource, id: payload && payload.id, payload });
    return Promise.resolve(behaviour(resource, payload));
  };
  return { api, writes };
}

function build(store, bldData, toasts) {
  return new Function(
    'localStorage', 'console', 'bldData', 'bldLicenseKey', 'toast',
    decl('BLD_SYNCED') + '\n' +
    'var _bldSyncOn = {}; BLD_SYNCED.forEach(function (k) { _bldSyncOn[k] = true; });\n' +
    'var bldSeeding = false;\n' +
    decl('_bldBackup') + '\n' +
    decl('BLD_PENDING_KEY') + '\n' +
    decl('BLD_PENDING_MAX') + '\n' +
    fn('function ld(k,d)') + '\n' +
    fn('function st(k,v)') + '\n' +
    fn('function bldSyncCollection(key, next, prev)') + '\n' +
    fn('function bldPendingAll()') + '\n' +
    fn('function bldPendingWrite(o)') + '\n' +
    fn('function bldPendingMark(key,id)') + '\n' +
    fn('function bldPendingClear(key,id)') + '\n' +
    fn('function bldPendingCount()') + '\n' +
    fn('function bldRetryPending()') + '\n' +
    fn('function bldBackupNotice(pushed)') + '\n' +
    'return {\n' +
    '  st: st, ld: ld,\n' +
    '  pendingAll: bldPendingAll, pendingCount: bldPendingCount,\n' +
    '  retry: bldRetryPending, notice: bldBackupNotice,\n' +
    '  mark: bldPendingMark,\n' +
    '  setProvisioned: function (v) { _bldBackup.provisioned = v; },\n' +
    '  provisioned: function () { return _bldBackup.provisioned; },\n' +
    '  setSeeding: function (v) { bldSeeding = v; },\n' +
    '  max: BLD_PENDING_MAX\n' +
    '};'
  )(store, { warn: () => {}, error: () => {} }, bldData, () => 'BLD-TEST-2026',
    (m) => toasts.push(String(m)));
}

const flush = () => new Promise((r) => setImmediate(r));

(async function () {

  // ── a push that succeeds queues nothing ────────────────────────────────
  {
    const s = makeStore();
    const srv = makeServer(() => ({ id: 'J-1' }));
    const w = build(s.store, srv.api, []);
    w.st('bld_jobs', [{ id: 'J-1', name: 'Riverside' }]);
    await flush();
    check('a successful push is attempted once', srv.writes.length, 1);
    check('and nothing is left pending', w.pendingCount(), 0);
    check('and the pending key is not even written', s.data.bld_sync_pending, undefined);
  }

  // ── a push that fails is recorded, not swallowed ───────────────────────
  {
    const s = makeStore();
    const srv = makeServer(() => null);            // every push fails
    const w = build(s.store, srv.api, []);
    w.st('bld_jobs', [{ id: 'J-1', name: 'Riverside' }]);
    await flush();
    check('the failed push was attempted', srv.writes.length, 1);
    check('and its id is on the pending list', w.pendingAll(), { bld_jobs: ['J-1'] });
    check('the local write still happened -- the app is never worse off',
      w.ld('bld_jobs', []), [{ id: 'J-1', name: 'Riverside' }]);
  }

  // ── THE MECHANISM: an unchanged record is never re-pushed ──────────────
  // This is the assertion that describes the defect rather than the fix. If
  // bldSyncCollection ever starts re-pushing unchanged records this fails,
  // and that is worth knowing -- it would make the retry queue redundant.
  {
    const s = makeStore();
    const srv = makeServer(() => null);
    const w = build(s.store, srv.api, []);
    w.st('bld_jobs', [{ id: 'J-1', name: 'Riverside' }]);
    await flush();
    // A second, unrelated record added to the same collection. J-1 is
    // untouched, so the diff skips it -- for ever, which is why it had to be
    // written down at the moment it failed.
    w.st('bld_jobs', [{ id: 'J-1', name: 'Riverside' }, { id: 'J-2', name: 'Oak St' }]);
    await flush();
    check('only the CHANGED record is pushed on the second write',
      srv.writes.map((x) => x.id), ['J-1', 'J-2']);
    check('both failures are queued', w.pendingAll(), { bld_jobs: ['J-1', 'J-2'] });
  }

  // ── retry sends what was stranded, and clears it ───────────────────────
  {
    const s = makeStore();
    let refuse = true;
    const srv = makeServer(() => (refuse ? null : { ok: true }));
    const w = build(s.store, srv.api, []);
    w.st('bld_lien_waivers', [{ id: 'LW-1', amount: 4000 }]);
    await flush();
    check('stranded after the failure', w.pendingCount(), 1);
    refuse = false;
    const pushed = await w.retry();
    check('retry reports what it actually recovered', pushed, 1);
    check('and the queue is empty afterwards', w.pendingAll(), {});
  }

  // ── retry pushes the CURRENT record, not the one that failed ───────────
  {
    const s = makeStore();
    let refuse = true;
    const srv = makeServer(() => (refuse ? null : { ok: true }));
    const w = build(s.store, srv.api, []);
    w.st('bld_lien_waivers', [{ id: 'LW-1', amount: 4000 }]);
    await flush();
    // Edited while stranded. The edit also fails, and does not duplicate the
    // queue entry.
    w.st('bld_lien_waivers', [{ id: 'LW-1', amount: 4500 }]);
    await flush();
    check('one id, not two', w.pendingAll(), { bld_lien_waivers: ['LW-1'] });
    refuse = false;
    await w.retry();
    const last = srv.writes[srv.writes.length - 1];
    check('the retry sends the amount as it stands NOW', last.payload.amount, 4500);
  }

  // ── a record deleted locally is dropped, not retried for ever ──────────
  {
    const s = makeStore();
    const srv = makeServer(() => null);
    const w = build(s.store, srv.api, []);
    w.st('bld_rfis', [{ id: 'RFI-1' }]);
    await flush();
    w.st('bld_rfis', []);                       // deleted on this device
    await flush();
    const before = srv.writes.length;
    const pushed = await w.retry();
    check('nothing was pushed for the deleted record', srv.writes.length, before);
    check('and it reports zero recovered', pushed, 0);
    check('and the queue no longer holds it', w.pendingAll(), {});
  }

  // ── provisioned:false skips the retry entirely ─────────────────────────
  // Firing hundreds of writes that are all certain to 503 is a burst with no
  // possible benefit. The records stay queued for the sign-in after the
  // migration is run -- asserted, because dropping them would be the very
  // data loss this exists to prevent.
  {
    const s = makeStore();
    const srv = makeServer(() => null);
    const w = build(s.store, srv.api, []);
    w.st('bld_incidents', [{ id: 'INC-1' }]);
    await flush();
    w.setProvisioned(false);
    const before = srv.writes.length;
    const pushed = await w.retry();
    check('no push is attempted while the tables do not exist',
      srv.writes.length, before);
    check('and it says it recovered nothing', pushed, 0);
    check('the stranded record is KEPT, not discarded', w.pendingAll(),
      { bld_incidents: ['INC-1'] });
  }

  // ── seeding still pushes nothing, and queues nothing ───────────────────
  // Demo rows are not the customer's business record. If seeding queued, the
  // first retry after provisioning would upload several hundred fake rows.
  {
    const s = makeStore();
    const srv = makeServer(() => null);
    const w = build(s.store, srv.api, []);
    w.setSeeding(true);
    w.st('bld_jobs', [{ id: 'SEED-1' }, { id: 'SEED-2' }]);
    await flush();
    check('seeding attempts no push', srv.writes.length, 0);
    check('and queues nothing for later', w.pendingCount(), 0);
  }

  // ── the cap records that it capped ─────────────────────────────────────
  {
    const s = makeStore();
    const srv = makeServer(() => null);
    const w = build(s.store, srv.api, []);
    for (let i = 0; i < w.max + 5; i++) w.mark('bld_costs', 'C-' + i);
    check('the list stops at the cap', w.pendingCount(), w.max);
    check('and says so rather than truncating quietly',
      w.pendingAll().__overflow, true);
  }

  // ── what the operator is actually told ─────────────────────────────────
  {
    const s = makeStore();
    const toasts = [];
    const w = build(s.store, makeServer(() => null).api, toasts);
    w.setProvisioned(false);
    w.notice(0);
    check('unprovisioned is stated plainly, once', toasts.length, 1);
    check('and says the records are on this device only',
      /NOT active/.test(toasts[0]) && /this device only/.test(toasts[0]), true);
  }
  {
    const s = makeStore();
    const toasts = [];
    const srv = makeServer(() => null);
    const w = build(s.store, srv.api, toasts);
    w.st('bld_daily_logs', [{ id: 'DL-1' }]);
    await flush();
    w.setProvisioned(true);
    w.notice(0);
    check('a stranded record is reported even when the server is up',
      toasts.length, 1);
    check('and the count is real', /^1 record still could not be backed up/.test(toasts[0]), true);
  }
  {
    const s = makeStore();
    const toasts = [];
    const w = build(s.store, makeServer(() => ({ ok: true })).api, toasts);
    w.setProvisioned(true);
    w.notice(0);
    check('a healthy backup with nothing stranded says NOTHING', toasts.length, 0);
  }

  console.log((fail ? 'FAILED' : 'ok') + '  sairnbuild-backup-pending: ' +
    pass + ' passed, ' + fail + ' failed');
  if (fail) process.exit(1);
})();
