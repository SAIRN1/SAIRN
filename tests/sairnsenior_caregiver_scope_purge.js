// tests/sairnsenior_caregiver_scope_purge.js
// Run: node tests/sairnsenior_caregiver_scope_purge.js [path/to/sairnsenior.html]
//
// H1 #1756 (cc b67). The #965 fix narrowed the sen_caregivers READ on the
// server: a caregiver gets its own row, and only owner/billing get the HR
// fields. senServerWinsMerge only adds and replaces, so a device that already
// held the roster kept every colleague's name, phone and CPR expiry in
// localStorage after the next merge. The fix applies the server's own
// envelope declarations (roster_scope, hr_fields_visible) on the device.
//
// The functions are EXTRACTED BY NAME from the shipped file and run in a vm
// against a stubbed fetch that answers in the server's real envelope shape
// (api/sd-data.js sen_caregivers read). An extraction that fails REFUSES
// (exit 2) rather than testing a copy.
//
// Exit: 0 all passed - 1 an arm FAILED - 2 COULD NOT RUN

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const FILE = process.argv[2] || path.join(__dirname, '..', 'sairnsenior.html');
const html = fs.readFileSync(FILE, 'utf8');
function grab(head, oneLine) {
  const i = html.indexOf(head);
  if (i < 0 || html.indexOf(head, i + 1) !== -1) {
    console.log('COULD NOT RUN: "' + head + '" found ' + (i < 0 ? 0 : 'more than one') + ' time(s) in ' + FILE);
    process.exit(2);
  }
  if (oneLine) return html.slice(i, html.indexOf('\n', i));
  return html.slice(i, html.indexOf('\n}\n', i) + 2);
}
const SRC = [
  grab('var senLastScope=', true),
  grab('function senData(action,resource,payload,withSession){'),
  grab('function senServerWinsMerge(key,serverRows){'),
  grab('function senHydrateCaregivers(){'),
  grab('var SEN_CAREGIVER_HR_FIELDS=', true),
  grab('function senPurgeCaregiversOutOfScope(serverRows,scope){'),
].join('\n');

let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  ok   ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail === undefined ? '' : '   got ' + JSON.stringify(detail))); }
}

const ALICE = { id: 'cg-alice', name: 'Alice Own', phone: '555-0101', cpr_expiry: '2027-01-01', employee_id: 'e-alice' };
const BOB = { id: 'cg-bob', name: 'Bob Colleague', phone: '555-0202', cpr_expiry: '2026-12-01', employee_id: 'e-bob' };
const CAROL = { id: 'cg-carol', name: 'Carol Colleague', phone: '555-0303', cpr_expiry: '2026-11-01', employee_id: 'e-carol' };
const HR = { bgcheck_date: '2025-01-01', state_caregiver_id: 'ST-9', notes: 'private note' };

// One run of senHydrateCaregivers against a device store and a server answer.
function run(localRows, synced, envelope, status) {
  const store = { sen_caregivers: JSON.parse(JSON.stringify(localRows)), sen_synced_ids: JSON.parse(JSON.stringify(synced)) };
  const ctx = {
    console: { warn() {}, log() {} },
    JSON, Object, Array, String, Promise,
    DATA_API: '/api/sd-data', APP_ID: 'sairnsenior', SEN_SYNCED_KEY: 'sen_synced_ids', SEN_SYNCED: ['sen_caregivers'],
    senSession: { token: 't' }, senLastErr: {}, senBootstrappedNow: false,
    senLicenseKey: () => 'LIC', senFetchTimeoutSignal: () => undefined, senSyncedBootstrap() {},
    senMarkSynced() {},
    senHydrateLoad: (k) => store[k], senHydrateStore: (k, v) => { store[k] = v; },
    st: (k, v) => { store[k] = v; },
    senSyncedRead: () => ({ map: store.sen_synced_ids, state: 'ok' }),
    fetch: () => Promise.resolve({ ok: status === 200, status, json: () => Promise.resolve(envelope) }),
  };
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  return ctx.senHydrateCaregivers().then((ret) => ({ store, ret, ctx }));
}
const blob = (s) => JSON.stringify(s.sen_caregivers);
const seeded = { sen_caregivers: ['cg-alice', 'cg-bob', 'cg-carol'] };

(async () => {
  // 1. CAREGIVER, own scope: the device held the whole roster before the fix.
  let r = await run([ALICE, BOB, CAROL], seeded,
    { ok: true, data: [ALICE], provisioned: true, hr_fields_visible: false, roster_scope: 'own' }, 200);
  check('caregiver: only its own row is left on the device', r.store.sen_caregivers.length === 1 && r.store.sen_caregivers[0].id === 'cg-alice', r.store.sen_caregivers);
  check("caregiver: no colleague's phone or name survives in localStorage", !/555-0202|555-0303|Bob|Carol/.test(blob(r.store)), blob(r.store));
  check('caregiver: the purged ids leave the synced map too', JSON.stringify(r.store.sen_synced_ids.sen_caregivers) === '["cg-alice"]', r.store.sen_synced_ids);
  check('caregiver: hydrate reports a change', r.ret === true, r.ret);

  // 2. HR fields on a row the merge KEEPS (pending first push, not seeded).
  r = await run([Object.assign({}, ALICE, HR)], { sen_caregivers: [] },
    { ok: true, data: [ALICE], provisioned: true, hr_fields_visible: false, roster_scope: 'own' }, 200);
  check('a kept local row loses bgcheck_date, state_caregiver_id and notes', !/bgcheck_date|state_caregiver_id|notes/.test(blob(r.store)), r.store.sen_caregivers);
  check('...and keeps everything else', r.store.sen_caregivers[0].phone === '555-0101', r.store.sen_caregivers);

  // 3. COORDINATOR: agency roster, no HR.
  r = await run([Object.assign({}, ALICE, HR), Object.assign({}, BOB, HR)], seeded,
    { ok: true, data: [ALICE, BOB], provisioned: true, hr_fields_visible: false, roster_scope: 'agency' }, 200);
  check('coordinator (agency scope): no row is dropped', r.store.sen_caregivers.length === 2, r.store.sen_caregivers);
  check('coordinator: HR fields are gone from every row', !/bgcheck_date|state_caregiver_id|notes/.test(blob(r.store)), blob(r.store));

  // 4. OWNER: agency + HR visible -- the purge must touch nothing.
  const localOnly = { id: 'cg-new', name: 'Unpushed Hire', phone: '555-0404' };
  r = await run([Object.assign({}, ALICE, HR), localOnly], { sen_caregivers: ['cg-alice'] },
    { ok: true, data: [Object.assign({}, ALICE, HR)], provisioned: true, hr_fields_visible: true, roster_scope: 'agency' }, 200);
  check("owner: a manager's unpushed local row is kept", r.store.sen_caregivers.some((x) => x.id === 'cg-new'), r.store.sen_caregivers);
  check('owner: HR fields are kept', /bgcheck_date/.test(blob(r.store)), blob(r.store));

  // 5. A FAILED read never deletes anything.
  r = await run([ALICE, BOB, CAROL], seeded, { ok: false, error: { code: 'ACTIVE_CHECK_FAILED' } }, 502);
  check('a refused/failed read deletes nothing', r.store.sen_caregivers.length === 3 && r.ret === false, r.store.sen_caregivers.length);

  // 6. UNPROVISIONED (the real shape: ok, empty, no scope flags) deletes nothing.
  r = await run([ALICE, BOB], seeded, { ok: true, data: [], provisioned: false }, 200);
  check('an unprovisioned store (no declaration) deletes nothing', r.store.sen_caregivers.length === 2, r.store.sen_caregivers.length);

  // 7. The flags are taken from the READ envelope only.
  r = await run([ALICE, BOB], seeded,
    { ok: true, data: [ALICE], provisioned: true, hr_fields_visible: false, roster_scope: 'own' }, 200);
  check('senData kept the read envelope declarations', r.ctx.senLastScope.sen_caregivers && r.ctx.senLastScope.sen_caregivers.roster_scope === 'own', r.ctx.senLastScope);

  console.log('\nsairnsenior caregiver scope purge (#1756): ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('COULD NOT RUN: ' + (e && e.stack || e)); process.exit(2); });
