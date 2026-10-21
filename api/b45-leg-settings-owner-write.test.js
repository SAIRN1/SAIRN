// api/b45-leg-settings-owner-write.test.js
//
// Run:  node api/b45-leg-settings-owner-write.test.js
//
// The SAIRNlegacy owner's F2/F3 write path (hank b45, routed from cody b40):
// resource `leg_settings`, table `sairnlegacy_settings`, own branch in
// api/sd-data.js. Drives the REAL handler against an in-memory table.
//
// CONCEPT UNDER TEST: only the owner may set it, and only as the values
// decide()'s own normalisers would keep -- so what the owner saved is exactly
// what decide() enforces. Section E closes that loop through decide() itself.
// Section M applies two mutants to the handler source and requires red.
//
// Exit: 0 all arms passed - 1 an arm FAILED

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || ['leg', 'settings', 'b45', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const Module = require('module');
const { signSessionToken } = require('./_lib/auth');
const legRoles = require('./_lib/leg-roles');

const HASH = 'legacy-home-A-hash';
const APP = 'sairnlegacy';
const SD_FILE = path.join(__dirname, 'sd-data.js');
const SD_SRC = fs.readFileSync(SD_FILE, 'utf8');

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

// ── THE TABLE, IN MEMORY ────────────────────────────────────────────────────
// One row per licence. `noGrantsCol` reproduces the state before
// sql/sairnlegacy_settings_livery_grants.sql is run: PostgREST answers 400
// 42703 for a select naming the column.
function makeStore(opts) {
  const s = { row: (opts && opts.row) || null, noGrantsCol: !!(opts && opts.noGrantsCol), writes: [],
              audits: [], auditStatus: (opts && opts.auditStatus) || 201 };
  s.fetch = async function (url, o) {
    const u = String(url);
    if (/sairnlegacy_audit_log/.test(u) && o && o.method === 'POST') {
      s.audits.push(JSON.parse(o.body));
      const ok = s.auditStatus < 300;
      return { ok: ok, status: s.auditStatus, text: async () => (ok ? '' : '{"code":"23514"}'), json: async () => ({}) };
    }
    if (/_employee_auth\?/.test(u)) {
      return { ok: true, status: 200, json: async () => [{ license_hash: HASH, employee_id: s.emp, role: s.role, active: true }] };
    }
    if (/sairnlegacy_settings/.test(u)) {
      if (o && o.method === 'POST') {
        const b = JSON.parse(o.body);
        s.writes.push(b);
        s.row = Object.assign({}, s.row || {}, b);
        return { ok: true, status: 201, json: async () => [s.row] };
      }
      if (s.noGrantsCol && /livery_grants/.test(u)) {
        const t = JSON.stringify({ code: '42703', message: 'column sairnlegacy_settings.livery_grants does not exist' });
        return { ok: false, status: 400, text: async () => t, json: async () => JSON.parse(t) };
      }
      return { ok: true, status: 200, json: async () => (s.row ? [s.row] : []) };
    }
    return { ok: true, status: 200, json: async () => [] };
  };
  return s;
}

function loadHandler(src) {
  const lic = require.resolve('./_lib/license');
  delete require.cache[lic];
  require.cache[lic] = { id: lic, filename: lic, loaded: true, exports: {
    validateLicenseKey: async function () {
      return { valid: true, active: true, license_hash: HASH, trial_ends_at: null,
               stripe_subscription_id: null, app_id: APP };
    } } };
  const m = new Module(SD_FILE, module);
  m.filename = SD_FILE;
  m.paths = Module._nodeModulePaths(__dirname);
  m._compile(src, SD_FILE);
  return m.exports;
}

async function call(store, role, action, payload, src) {
  const h = loadHandler(src || SD_SRC);
  const headers = { authorization: 'Bearer KEY' };
  if (role) {
    store.role = role; store.emp = 'emp-' + role;
    headers['x-sd-auth'] = signSessionToken({ app: APP, employee_id: store.emp, role: role, license_hash: HASH });
  }
  const res = { statusCode: null, body: null, setHeader: function () { return res; },
                status: function (c) { res.statusCode = c; return res; },
                json: function (b) { res.body = b; return res; } };
  const prev = global.fetch;
  global.fetch = store.fetch;
  try { await h({ method: 'POST', headers: headers, body: { action: action, resource: 'leg_settings', payload: payload || {} } }, res); }
  finally { global.fetch = prev; }
  return res;
}
const code = (r) => ((r.body || {}).error || {}).code;

// Arms written as functions of the source, so section M can re-run them on a mutant.
async function armOwnerOnly(src) {
  for (const role of ['director', 'apprentice', 'livery']) {
    const s = makeStore();
    const r = await call(s, role, 'write', { livery_billing: 'direct_to_family' }, src);
    assert.deepStrictEqual([r.statusCode, code(r), s.writes.length], [403, 'FORBIDDEN', 0], role + ' was not refused');
  }
}
// b46: a changing save writes ONE audit row naming the owner and each change.
async function armAuditRow(src) {
  const s = makeStore();
  const r = await call(s, 'owner', 'write', { livery_billing: 'direct_to_family' }, src);
  assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
  assert.strictEqual(s.audits.length, 1, 'audit rows written: ' + s.audits.length);
  const a = s.audits[0];
  assert.deepStrictEqual([a.license_hash, a.employee_id, a.role, a.event_type, a.detail.resource, a.detail.first_save,
    a.detail.changed.livery_billing, Object.keys(a.detail.changed), r.body.audited],
    [HASH, 'emp-owner', 'owner', 'settings_changed', 'leg_settings', true,
     { from: 'through_the_home', to: 'direct_to_family' }, ['livery_billing'], true]);
}
async function armNeverGrantable(src) {
  const s = makeStore();
  const r = await call(s, 'owner', 'write', { livery_billing: 'direct_to_family',
    livery_grants: { 'emp-9': { leg_liveryvendors: true } } }, src);
  assert.deepStrictEqual([r.statusCode, code(r), s.writes.length], [400, 'INVALID_SETTING', 0],
    'leg_liveryvendors was accepted as a livery grant');
}

(async function () {
  console.log('SAIRNlegacy leg_settings -- the owner F2/F3 write path, driven');

  section('S. WHO');
  await test('S1. no session -> 401 NO_SESSION, nothing written', async function () {
    const s = makeStore();
    const r = await call(s, null, 'write', { livery_billing: 'direct_to_family' });
    assert.deepStrictEqual([r.statusCode, code(r), s.writes.length], [401, 'NO_SESSION', 0]);
  });
  await test('S2. director, apprentice and livery are REFUSED (403) for write', function () { return armOwnerOnly(SD_SRC); });
  await test('S3. ...and for read', async function () {
    const r = await call(makeStore(), 'director', 'read');
    assert.deepStrictEqual([r.statusCode, code(r)], [403, 'FORBIDDEN']);
  });
  await test('S4. the registry carries leg_settings, so the envelope accepts it', function () {
    assert.ok(require('./_resources/sairnlegacy.js').resources.indexOf('leg_settings') !== -1);
  });

  section('R. READ');
  await test('R1. no row yet -> 200, saved:false, the NARROW defaults', async function () {
    const r = await call(makeStore(), 'owner', 'read');
    const d = r.body.data;
    assert.deepStrictEqual([r.statusCode, d.saved, d.livery_billing, d.apprentice.countersign, d.apprentice.forbidden,
      d.apprentice.presence_disclosure, d.livery_grants], [200, false, 'through_the_home', [], [], true, {}]);
  });
  await test('R2. a stored typo reads back NORMALISED (narrow), never as stored', async function () {
    const r = await call(makeStore({ row: { livery_billing: 'directtofamily', apprentice: { countersign: ['leg_nope'] }, livery_grants: {} } }), 'owner', 'read');
    assert.deepStrictEqual([r.body.data.livery_billing, r.body.data.apprentice.countersign], ['through_the_home', []]);
  });

  section('W. WRITE -- refused, not narrowed');
  await test('W1. a valid full write is stored as given, with updated_by = the owner', async function () {
    const s = makeStore();
    const r = await call(s, 'owner', 'write', { livery_billing: 'direct_to_family',
      apprentice: { countersign: ['leg_cremations'], forbidden: ['leg_invoices'], presence_disclosure: true },
      livery_grants: { 'emp-9': { leg_liverybookings: true, leg_dispatches: true } } });
    assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
    const w = s.writes[0];
    assert.deepStrictEqual([w.license_hash, w.livery_billing, w.apprentice, w.livery_grants, w.updated_by],
      [HASH, 'direct_to_family', { countersign: ['leg_cremations'], forbidden: ['leg_invoices'], presence_disclosure: true },
       { 'emp-9': { leg_liverybookings: true, leg_dispatches: true } }, 'emp-owner']);
  });
  const bad = [
    ['W2. livery_billing not one of the two values', { livery_billing: 'both' }],
    ['W4. leg_liverybookings granted while billing is through_the_home', { livery_grants: { 'emp-9': { leg_liverybookings: true } } }],
    ['W5a. an unknown record type in countersign', { apprentice: { countersign: ['leg_nope'] } }],
    ['W5b. the same record type in countersign AND forbidden', { apprentice: { countersign: ['leg_cremations'], forbidden: ['leg_cremations'] } }],
    ['W5c. a countersign entry that takes no countersignature (inert)', { apprentice: { countersign: ['leg_invoices'] } }],
    ['W5d. presence_disclosure that is not a boolean', { apprentice: { presence_disclosure: 'no' } }],
    ['W5e. apprentice that is not an object', { apprentice: ['leg_cremations'] }],
    ['W7. a grant value that is not exactly true', { livery_billing: 'direct_to_family', livery_grants: { 'emp-9': { leg_dispatches: 'yes' } } }],
    ['W7b. livery_grants that is an array', { livery_grants: [] }]
  ];
  for (const [name, payload] of bad) {
    await test(name + ' -> 400 INVALID_SETTING, nothing written', async function () {
      const s = makeStore();
      const r = await call(s, 'owner', 'write', payload);
      assert.deepStrictEqual([r.statusCode, code(r), s.writes.length], [400, 'INVALID_SETTING', 0], JSON.stringify(r.body).slice(0, 200));
    });
  }
  await test('W3. leg_liveryvendors is NEVER grantable, even under direct_to_family (b22 B2)', function () { return armNeverGrantable(SD_SRC); });
  await test('W8. switching billing back to through_the_home while a stored grant holds leg_liverybookings is REFUSED', async function () {
    const s = makeStore({ row: { livery_billing: 'direct_to_family', apprentice: {}, livery_grants: { 'emp-9': { leg_liverybookings: true } } } });
    const r = await call(s, 'owner', 'write', { livery_billing: 'through_the_home' });
    assert.deepStrictEqual([r.statusCode, code(r), s.writes.length], [400, 'INVALID_SETTING', 0]);
  });
  await test('W6. an absent field keeps what is stored (partial write)', async function () {
    const s = makeStore({ row: { livery_billing: 'direct_to_family', apprentice: { countersign: ['leg_cremations'], forbidden: [], presence_disclosure: false }, livery_grants: { 'emp-9': { leg_dispatches: true } } } });
    const r = await call(s, 'owner', 'write', { apprentice: { countersign: [], forbidden: ['leg_invoices'] } });
    assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
    assert.deepStrictEqual([s.writes[0].livery_billing, s.writes[0].livery_grants, s.writes[0].apprentice.forbidden],
      ['direct_to_family', { 'emp-9': { leg_dispatches: true } }, ['leg_invoices']]);
  });

  section('N. livery_grants COLUMN NOT YET PROVISIONED');
  await test('N1. a write NAMING livery_grants -> 503 NOT_PROVISIONED naming the SQL file, nothing written', async function () {
    const s = makeStore({ noGrantsCol: true });
    const r = await call(s, 'owner', 'write', { livery_grants: {} });
    assert.deepStrictEqual([r.statusCode, code(r), s.writes.length], [503, 'NOT_PROVISIONED', 0]);
    assert.ok(/sairnlegacy_settings_livery_grants\.sql/.test(r.body.error.message));
  });
  await test('N2. a write NOT naming it still saves F2/F3, without the column', async function () {
    const s = makeStore({ noGrantsCol: true });
    const r = await call(s, 'owner', 'write', { livery_billing: 'direct_to_family' });
    assert.deepStrictEqual([r.statusCode, s.writes.length, 'livery_grants' in s.writes[0]], [200, 1, false]);
  });

  section('E. WHAT THE OWNER SAVED IS WHAT decide() ENFORCES');
  await test('E1. after W1-style save, decide() lets emp-9 (livery) READ leg_liverybookings and not write it; another driver gets nothing', async function () {
    const s = makeStore();
    await call(s, 'owner', 'write', { livery_billing: 'direct_to_family', livery_grants: { 'emp-9': { leg_liverybookings: true } } });
    const home = s.row;
    assert.deepStrictEqual([
      legRoles.decide('leg_liverybookings', 'livery', 'read', home.livery_grants['emp-9'], home),
      legRoles.decide('leg_liverybookings', 'livery', 'write', home.livery_grants['emp-9'], home),
      legRoles.decide('leg_liverybookings', 'livery', 'read', home.livery_grants['emp-8'], home)
    ], [legRoles.ALLOW, legRoles.DENY, legRoles.DENY]);
  });
  await test('E2. a saved apprentice config is enforced: forbidden denies the read, countersign allows prepare', async function () {
    const s = makeStore();
    await call(s, 'owner', 'write', { apprentice: { countersign: ['leg_cremations'], forbidden: ['leg_invoices'] } });
    const home = s.row;
    assert.deepStrictEqual([
      legRoles.decide('leg_invoices', 'apprentice', 'read', null, home),
      legRoles.decide('leg_cremations', 'apprentice', 'prepare', null, home)
    ], [legRoles.DENY, legRoles.ALLOW]);
  });

  section('A. THE AUDIT ROW (b46)');
  await test('A1. a changing save writes ONE settings_changed row: owner, licence, field from -> to; audited:true', function () { return armAuditRow(SD_SRC); });
  await test('A2. a REFUSED write writes no audit row', async function () {
    const s = makeStore();
    await call(s, 'owner', 'write', { livery_billing: 'both' });
    assert.deepStrictEqual([s.writes.length, s.audits.length], [0, 0]);
  });
  await test('A3. a save that changes NOTHING writes no audit row and answers audited:null', async function () {
    const s = makeStore({ row: { livery_billing: 'direct_to_family', apprentice: { countersign: [], forbidden: [], presence_disclosure: true }, livery_grants: {} } });
    const r = await call(s, 'owner', 'write', { livery_billing: 'direct_to_family' });
    assert.deepStrictEqual([r.statusCode, s.writes.length, s.audits.length, r.body.audited], [200, 1, 0, null]);
  });
  await test('A4. a FAILED audit insert (e.g. the CHECK before the b46 SQL runs) does not undo the save; answers audited:false', async function () {
    const s = makeStore({ auditStatus: 400 });
    const r = await call(s, 'owner', 'write', { livery_billing: 'direct_to_family' });
    assert.deepStrictEqual([r.statusCode, s.writes.length, s.audits.length, r.body.audited], [200, 1, 1, false]);
  });
  await test('A5. a refused role writes no audit row', async function () {
    const s = makeStore();
    await call(s, 'director', 'write', { livery_billing: 'direct_to_family' });
    assert.strictEqual(s.audits.length, 0);
  });
  await test('A6. the SQL that admits settings_changed exists and restates the five existing values', function () {
    const sql = fs.readFileSync(path.join(__dirname, '..', 'sql', 'sairnlegacy_audit_log_settings_event.sql'), 'utf8');
    ['pin_bootstrap', 'pin_setup', 'credential_deactivated', 'credential_reactivated',
     'credential_change_refused', 'settings_changed'].forEach(function (v) {
      assert.ok(sql.indexOf("'" + v + "'") !== -1, v + ' missing from the CHECK');
    });
  });

  section('M. MUTANTS on api/sd-data.js -- each must turn its arm red');
  await test('M3. replace the audit write with a stub that claims success -> A1 red', function () {
    return mustFail(armAuditRow, mutate("require('./_lib/audit').writeAuditLog(SUPABASE_URL, SERVICE_KEY, {",
      '(async function () { return true; })({'), 'stubbed audit write');
  });
  function mutate(from, to) {
    const n = SD_SRC.split(from).length - 1;
    if (n !== 1) throw new Error('mutant anchor found ' + n + ' times');
    return SD_SRC.replace(from, to);
  }
  async function mustFail(arm, src, name) {
    let failed = false;
    try { await arm(src); } catch (e) { failed = true; }
    if (!failed) throw new Error(name + ' survived');
  }
  await test('M1. drop the owner-only check -> S2 red', function () {
    return mustFail(armOwnerOnly, mutate("if (setSess.role !== 'owner') {", 'if (false) {'), 'no owner check');
  });
  await test('M2. drop the grantability check -> W3 red', function () {
    return mustFail(armNeverGrantable, mutate('} else if (!legRoles.liveryGrantable(r, billing)) {', '} else if (false) {'), 'no grantability check');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
