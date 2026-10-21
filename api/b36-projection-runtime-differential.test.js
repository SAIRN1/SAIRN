'use strict';
// b36 -- the RUNTIME half of b34's per-resource proof (SAIRN-handoff-cody-b34.md
// s4.5; b35 NEXT item 2).
//
// CONCEPT (stated before the code): a projection key is safe only if it is
// EXECUTED to be so -- a real write with every projection key planted must
// persist none of them in the blob, and the read of that stored row must
// return each key with a value a COLUMN holds.
//
// b34 proved this STATICALLY for the 44 PAIRED sites
// (docs/b33-sweep/pair_by_resource.py): every key is in the strip list of every
// storedBlob() call for the resource. Static is not executed. This drives each
// of those 22 resources through api/sd-data.js against a STORE mock (a write
// stores the exact row the handler sent; a read returns those rows) and checks:
//
//   A  the stored row's `data` blob carries NONE of the projection keys
//   B  the READ returns each key, and its value is one some COLUMN of the stored
//      row holds -- so it came from a column, not from a blob
//   W  the WRITE response passes the same test (it is a projection site too)
//
// The criteria are locked FIRST against synthetic fixtures (section F), in both
// directions, so a harness that could only ever say "pass" fails here.
//
// L (INFO, does not fail the run): a LEGACY blob that DOES carry the keys -- a
// row written before its strip list existed -- is planted and re-read. A key
// that comes back with the blob's value means that read is still the inverted
// Object.assign(columns, blob) shape and is inert only while no stored blob
// holds the key. This is measured and printed, not asserted: the write side
// cannot produce such a row any more, and whether any LIVE row does is a
// data question this mock cannot answer.

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || ['b36', 'projection', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';
const { signSessionToken } = require('./_lib/auth');

const HASH = 'b36-projection-hash';
const DB_NOW = '2026-01-01T00:00:00.000Z';
const EMP = 'EMP-1';

let pass = 0, fail = 0;
const failed = [];
const info = [];
function ok(l) { pass++; console.log('  ok    ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL  ' + l);
  if (why) console.log('        ' + String(why).slice(0, 600));
}
function is(c, l, d) { if (c) ok(l); else bad(l, d); }

// ── THE CRITERIA (pure; locked by section F before any real run) ───────────
function columnValues(row) {
  return Object.keys(row).filter((k) => k !== 'data').map((k) => row[k]);
}
// -> null when clean, else a string naming what failed. "Could not tell" fails.
function blobVerdict(rows, keys) {
  if (!Array.isArray(rows) || !rows.length) return 'COULD NOT RUN: the write stored no row';
  for (const row of rows) {
    const d = row && row.data;
    if (!d || typeof d !== 'object') return 'COULD NOT TELL: stored row has no data blob';
    const leaked = keys.filter((k) => Object.prototype.hasOwnProperty.call(d, k));
    if (leaked.length) return 'blob carries ' + leaked.join(',');
  }
  return null;
}
function readVerdict(row, rec, keys) {
  if (!row) return 'COULD NOT RUN: no stored row';
  if (!rec || typeof rec !== 'object') return 'COULD NOT TELL: no record in the response';
  const cols = columnValues(row);
  const bad = [];
  for (const k of keys) {
    if (rec[k] === undefined) { bad.push(k + ' absent'); continue; }
    if (!cols.some((v) => v === rec[k])) bad.push(k + '=' + JSON.stringify(rec[k]) + ' held by no column');
  }
  return bad.length ? bad.join('; ') : null;
}

// ── THE 22 PAIRED RESOURCES (pair_by_resource.py at b36), with the union of
// each resource's projection keys and the smallest payload its write accepts.
const PLANT = (k) => 'PLANT-' + k;
const CFG = [
  { r: 'sd_customers', app: 'stonedesk', keys: ['id'], p: { name: 'A' } },
  { r: 'sd_crm', app: 'stonedesk', keys: ['id', 'assigned_employee_id'], p: {} },
  { r: 'sdn_clients', app: 'sairndesign', keys: ['id', 'assigned_employee_id'], p: {} },
  { r: 'bld_bids', app: 'sairnbuild', keys: ['id', 'assigned_employee_id'], p: {} },
  { r: 'sen_clients', app: 'sairnsenior', keys: ['id', 'assigned_employee_id'], p: {} },
  { r: 'sen_caregivers', app: 'sairnsenior', keys: ['id'], p: {} },
  { r: 'sen_claims', app: 'sairnsenior', keys: ['id'], p: {} },
  { r: 'sen_branches', app: 'sairnsenior', keys: ['id'], p: { state: 'OH' } },
  { r: 'sen_payer_contracts', app: 'sairnsenior', keys: ['id'], p: { payer: 'medicaid', rate_per_hour: 20, effective_on: '2026-01-01' } },
  { r: 'sen_authorizations', app: 'sairnsenior', keys: ['id'], p: { client_id: 'C-1', auth_number: 'A1', units_authorized: 10, minutes_per_unit: 15, start_on: '2026-01-01', end_on: '2026-12-31' } },
  { r: 'sen_pay_rates', app: 'sairnsenior', keys: ['id'], p: { employee_id: 'E-1', rate_per_hour: 20, effective_on: '2026-01-01' } },
  { r: 'sen_franchise_agreements', app: 'sairnsenior', keys: ['id'], p: { branch_id: 'B-1', royalty_base: 'billed', effective_on: '2026-01-01' } },
  { r: 'alf_clients', app: 'sairncare', keys: ['id', 'assigned_employee_id'], p: {} },
  { r: 'alf_staff', app: 'sairncare', keys: ['id'], p: {} },
  { r: 'alf_mar', app: 'sairncare', keys: ['id', 'resident_id', 'entry_type', 'assigned_employee_id', 'created_at'], p: { resident_id: 'RES-1', entry_type: 'administration' },
    seed: { alf_clients: [{ client_id: 'RES-1', assigned_employee_id: EMP, data: {} }] } },
  { r: 'alf_billing', app: 'sairncare', keys: ['id', 'resident_id'], p: { resident_id: 'RES-1' } },
  { r: 'alf_incidents', app: 'sairncare', keys: ['id', 'resident_id'], p: { resident_id: 'RES-1' } },
  { r: 'alf_activities', app: 'sairncare', keys: ['id'], p: {} },
  { r: 'alf_facility', app: 'sairncare', keys: ['id'], p: {} },
  { r: 'alf_signals', app: 'sairncare', keys: ['id', 'resident_id', 'signal_type', 'recorded_at'], p: { resident_id: 'RES-1', signal_type: 'bed_exit' } },
  { r: 'alf_claim_routes', app: 'sairncare', keys: ['id', 'resident_id', 'service_month', 'decided_by', 'created_at'], p: { resident_id: 'RES-1', service_month: '2026-10' } },
  { r: 'alf_staff_credentials', app: 'sairncare', keys: ['id', 'staff_id', 'record_type', 'recorded_by', 'created_at'], p: { staff_id: 'S-1', record_type: 'credential' } }
];

// The write response may legitimately omit a server-set key it did not echo;
// only keys it DOES return are held to the column test.
function writeVerdict(row, rec, keys) {
  if (!rec) return 'COULD NOT TELL: no record in the write response';
  return readVerdict(row, rec, keys.filter((k) => rec[k] !== undefined));
}

function harness(c) {
  const store = JSON.parse(JSON.stringify(c.seed || {}));
  const tbl = (u) => (u.match(/\/rest\/v1\/([a-z_0-9]+)/) || [])[1];
  global.fetch = async function (url, init) {
    const u = decodeURIComponent(String(url));
    const m = (init && init.method) || 'GET';
    const rep = (s, b) => ({ ok: s >= 200 && s < 300, status: s, json: async () => b, text: async () => JSON.stringify(b) });
    if (/_employee_auth\?/.test(u)) return rep(200, [{ active: true, role: 'owner', employee_id: EMP, license_hash: HASH }]);
    const t = tbl(u);
    if (m === 'POST' || m === 'PATCH') {
      const b = JSON.parse(init.body);
      // alf_mar writes through an RPC; emulate the function's INSERT so the row
      // stored is exactly what the handler handed it (p_data is the blob).
      if (/\/rpc\/alf_check_and_insert_mar_entry/.test(u)) {
        const mr = { license_hash: b.p_license_hash, entry_id: b.p_entry_id, resident_id: b.p_resident_id,
          assigned_employee_id: b.p_assigned_employee_id, entry_type: b.p_entry_type, data: b.p_data, created_at: DB_NOW };
        store.alf_mar = (store.alf_mar || []).concat([mr]);
        return rep(200, [JSON.parse(JSON.stringify(mr))]);
      }
      // created_at is a COLUMN DEFAULT in every schema that carries it; a real
      // insert fills it, so the store does too rather than reporting it absent.
      const rows = (Array.isArray(b) ? b : [b]).map((x) => Object.assign({ created_at: DB_NOW }, x));
      store[t] = (store[t] || []).concat(JSON.parse(JSON.stringify(rows)));
      return rep(200, rows);
    }
    return rep(200, JSON.parse(JSON.stringify(store[t] || [])));
  };
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = { exports: { validateLicenseKey: async () => ({
    valid: true, active: true, license_hash: HASH, trial_ends_at: null, stripe_subscription_id: null, app_id: c.app }) } };
  delete require.cache[require.resolve('./sd-data.js')];
  const h = require('./sd-data.js');
  async function run(action, payload) {
    const res = { statusCode: null, body: null };
    res.status = function (s) { res.statusCode = s; return res; };
    res.json = function (b) { res.body = b; return res; };
    const ce = console.error, cw = console.warn;
    console.error = function () {}; console.warn = function () {};
    try {
      await h({ method: 'POST', headers: { authorization: 'Bearer KEY-FOR-' + HASH,
        'x-sd-auth': signSessionToken({ app: c.app, employee_id: EMP, role: 'owner', license_hash: HASH }) },
        body: { action: action, resource: c.r, app_id: c.app, payload: payload } }, res);
    } finally { console.error = ce; console.warn = cw; }
    return res;
  }
  return { store, run };
}
const firstRec = (b) => (b && Array.isArray(b.data) ? b.data.find((x) => x && x.id === 'R-1') : null);

(async function main() {
  console.log('\nF. CRITERIA LOCK -- synthetic fixtures, both directions');
  {
    const good = { client_id: 'R-1', data: { name: 'A' } };
    is(blobVerdict([good], ['id']) === null && readVerdict(good, { id: 'R-1', name: 'A' }, ['id']) === null,
       'F1. a stripped blob read from its column -> clean');
    is(/blob carries id/.test(blobVerdict([{ client_id: 'R-1', data: { id: 'X' } }], ['id']) || ''),
       'F2. a blob that carries the key -> fails A');
    is(/held by no column/.test(readVerdict(good, { id: 'Z' }, ['id']) || ''),
       'F3. a read value no column holds (it came from the blob) -> fails B');
    is(/absent/.test(readVerdict(good, {}, ['id']) || ''),
       'F4. a key missing from the read -> fails B, not skipped');
    is(/COULD NOT RUN/.test(blobVerdict([], ['id']) || '') && /COULD NOT/.test(readVerdict(null, null, ['id']) || ''),
       'F5. no stored row / no record -> COULD NOT RUN, which fails, never a pass');
  }

  for (let i = 0; i < CFG.length; i++) {
    const c = CFG[i];
    const n = i + 1;
    console.log('\n' + c.r + '  keys=' + c.keys.join(','));
    const H = harness(c);
    const payload = Object.assign({ id: 'R-1' }, c.p);
    c.keys.forEach((k) => { if (payload[k] === undefined) payload[k] = PLANT(k); });
    const w = await H.run('write', payload);
    const rows = H.store[c.r] || [];
    const row = rows[rows.length - 1];
    is(w.statusCode === 200 && blobVerdict(rows, c.keys) === null,
       'A' + n + '. ' + c.r + ': a write with every projection key planted stores NONE of them in the blob',
       w.statusCode + ' ' + (blobVerdict(rows, c.keys) || JSON.stringify(w.body).slice(0, 200)));
    const wrec = w.body && w.body.data && !Array.isArray(w.body.data) ? w.body.data : null;
    const wv = writeVerdict(row, wrec, c.keys);
    is(wv === null, 'W' + n + '. ' + c.r + ': the write response takes each key it returns from a column', wv);
    const r = await H.run('read', {});
    const rec = firstRec(r.body);
    const rv = readVerdict(row, rec, c.keys);
    is(r.statusCode === 200 && rv === null,
       'B' + n + '. ' + c.r + ': the read returns every key from a COLUMN of the stored row', r.statusCode + ' ' + rv);

    // L: a legacy blob that carries every key, planted under the same row.
    if (row && row.data) {
      c.keys.forEach((k) => { row.data[k] = 'BLOB-' + k; });
      const lr = await H.run('read', {});
      const lrec = (lr.body && Array.isArray(lr.body.data)) ? lr.body.data[0] : null;
      const won = lrec ? c.keys.filter((k) => lrec[k] === 'BLOB-' + k) : null;
      if (won && won.length) info.push(c.r + ': a legacy blob OVERRIDES the column on read for ' + won.join(','));
    }
  }

  console.log('\nL. INFO -- legacy-blob exposure (measured, not asserted)');
  if (!info.length) console.log('  none: on every resource the column wins even when the blob carries the key');
  info.forEach((s) => console.log('  INFO  ' + s));

  console.log('\n' + (fail ? 'FAILED' : 'PASSED') + ' -- ' + pass + ' passed, '
    + fail + ' failed' + (fail ? '\nFAILING ARMS: ' + failed.join(', ') : ''));
  process.exit(fail ? 1 : 0);
})().catch((e) => {
  console.error('HARNESS ERROR -- no verdict was reached, which is NOT a pass');
  console.error(e);
  process.exit(1);
});
