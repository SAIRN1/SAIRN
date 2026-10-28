// api/b60-readiness-caregiver-projection.test.js
//
// Run:  node api/b60-readiness-caregiver-projection.test.js
//
// REQUIREMENT (H1 #1274, hank b60): sen_visits/readiness is open to coordinators and
// schedulers, who may NOT see a caregiver's HR fields on sen_caregivers/read. So the
// readiness engine must never be handed those VALUES for such a role, and must still
// give a TRUE verdict on whether a state caregiver ID is on file.
//
//   P1  the engine receives exactly {id, name, state_caregiver_id}: no bgcheck_date, notes,
//       phone, cpr, etc. Checked on the engine's own input, captured by wrapping
//       summarize(), because the response alone cannot show what was consumed.
//   P2  a coordinator or scheduler's engine input carries a presence marker, never the
//       state ID value; owner and billing get the value.
//   P3  the VERDICT is unchanged for every role: a caregiver WITH an ID gets no
//       "No state caregiver ID" miss, and one WITHOUT an ID gets it.
//   P4  the response carries no HR value for any role.
//   M   mutation controls: with the projection or the role split reverted in a copy of
//       sd-data.js, P1 and P2 go red.
'use strict';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || 'b60-readiness-projection';
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { signSessionToken } = require('./_lib/auth');

const HASH = 'b60-sen-hash', APP = 'sairnsenior', CG = 'emp-7';
const SID = 'OH-STNA-ZZSTATEIDZZ', BG = '2026-02-14-ZZBGCHECKZZ', NOTE = 'ZZHRNOTESZZ';
const HR = ['owner', 'billing'], NON_HR = ['coordinator', 'scheduler'];
const MISS = 'No state caregiver ID';

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function mockRes() { const r = { statusCode: null, body: null }; r.status = (c) => { r.statusCode = c; return r; }; r.json = (b) => { r.body = b; return r; }; return r; }
function tables(withSid) {
  const data = { name: 'Dana Okonkwo', phone: '330-555-0147', cpr_expiry: '2027-03-01', employee_id: CG, bgcheck_date: BG, notes: NOTE };
  if (withSid) data.state_caregiver_id = SID;
  return {
    sen_visits: [{ visit_id: 'V-1', assigned_employee_id: CG, data: { client_id: 'CL-1', assigned_employee_id: CG,
      scheduled_date: '2026-10-01', status: 'completed', clock_in_at: '2026-10-01T13:00:00Z', clock_out_at: '2026-10-01T15:00:00Z' } }],
    sen_clients: [{ client_id: 'CL-1', data: { name: 'A Client', member_id: 'M-1' } }],
    sen_caregivers: [{ caregiver_id: CG, data }],
    sen_settings: [{ setting_key: 'evv_config', data: { state: 'OH' } }],
  };
}
function fetchFor(t) {
  return async (url) => {
    const u = String(url);
    if (/_employee_auth\?/.test(u)) return { ok: true, status: 200, json: async () => [{ employee_id: 'emp-1', active: true }] };
    const tbl = (u.split('/rest/v1/')[1] || '').split('?')[0];
    const rows = (t[tbl] || []).filter((r) => !/setting_key=eq\./.test(u) || r.setting_key === 'evv_config');
    return { ok: true, status: 200, json: async () => rows.map((r) => JSON.parse(JSON.stringify(r))) };
  };
}
async function call(file, role, withSid) {
  const LIC = require.resolve('./_lib/license');
  require.cache[LIC] = { id: LIC, filename: LIC, loaded: true, exports: { validateLicenseKey: async () => ({
    valid: true, active: true, license_hash: HASH, app_id: APP, trial_ends_at: null, stripe_subscription_id: null }) } };
  const ENG = require.resolve('./_lib/sen-evv-readiness');
  delete require.cache[ENG];
  const eng = require('./_lib/sen-evv-readiness');
  const real = eng.summarize; let seen = null;
  eng.summarize = function (v, c, g, o) { seen = JSON.parse(JSON.stringify(g)); return real.apply(this, arguments); };
  global.fetch = fetchFor(tables(withSid));
  delete require.cache[require.resolve(file)];
  const h = require(file); const res = mockRes();
  const q = [console.error, console.warn, console.log]; console.error = console.warn = () => {};
  try {
    await h({ method: 'POST', headers: { authorization: 'Bearer KEY-' + HASH,
      'x-sd-auth': signSessionToken({ app: APP, employee_id: 'emp-1', role, license_hash: HASH }) },
      body: { action: 'readiness', resource: 'sen_visits' } }, res);
  } finally { [console.error, console.warn, console.log] = q; eng.summarize = real; }
  return { res, seen: seen && seen[CG], body: JSON.stringify(res.body) };
}

async function suite(file, label) {
  for (const role of HR.concat(NON_HR)) {
    await test(label + ' P1 [' + role + '] the engine is handed exactly {id, name, state_caregiver_id}', async () => {
      const r = await call(file, role, true);
      assert.strictEqual(r.res.statusCode, 200, 'readiness answered ' + r.res.statusCode + ' ' + r.body.slice(0, 200));
      assert.ok(r.seen, 'the engine was never called with this caregiver');
      assert.deepStrictEqual(Object.keys(r.seen).sort(), ['id', 'name', 'state_caregiver_id'],
        'the engine received ' + JSON.stringify(Object.keys(r.seen)));
    });
    await test(label + ' P2 [' + role + '] state ID ' + (HR.includes(role) ? 'VALUE reaches the engine' : 'is a presence marker only'), async () => {
      const r = await call(file, role, true);
      if (HR.includes(role)) assert.strictEqual(r.seen.state_caregiver_id, SID);
      else assert.strictEqual(r.seen.state_caregiver_id, 'present', 'a non-HR role\'s engine input held ' + JSON.stringify(r.seen.state_caregiver_id));
    });
    await test(label + ' P3 [' + role + '] verdict is true both ways: ID on file -> no miss; ID absent -> miss', async () => {
      const w = await call(file, role, true), wo = await call(file, role, false);
      assert.ok(w.body.indexOf(MISS) === -1, 'reported a missing state ID that is on file');
      assert.ok(wo.body.indexOf(MISS) !== -1, 'did not report a state ID that is missing');
    });
    await test(label + ' P4 [' + role + '] no HR value in the response', async () => {
      const r = await call(file, role, true);
      [SID, BG, NOTE].forEach((s) => assert.ok(r.body.indexOf(s) === -1, 'the response carries ' + s));
    });
  }
}

function mutant(from, to) {
  const src = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
  if (src.split(from).length !== 2) throw new Error('mutation anchor not unique: ' + from.slice(0, 60));
  const f = path.join(__dirname, '.b60-mutant-sd-data.js');
  fs.writeFileSync(f, src.split(from).join(to));
  return f;
}
async function mustFail(name, file, re) {
  const before = fail, p = pass;
  const log = console.log; console.log = () => {};
  try { await suite(file, 'M'); } finally { console.log = log; }
  const failed = fail - before; fail = before; pass = p;
  if (failed > 0) { console.log('  ok   ' + name + ' (' + failed + ' arm(s) went red)'); pass++; }
  else { console.log('  FAIL ' + name + ' -- the suite stayed green against the mutant'); fail++; }
}

(async () => {
  console.log('sen_visits/readiness -- caregiver projection (H1 #1274)');
  await suite('./sd-data.js', 'live');
  const m1 = mutant("caregiversById[x.caregiver_id] = {\n            id: x.caregiver_id,\n            name: d.name,\n            state_caregiver_id: readinessSeesHr ? sid : (hasSid ? 'present' : '')\n          };",
    'caregiversById[x.caregiver_id] = Object.assign({ id: x.caregiver_id }, x.data);');
  const m2 = mutant("state_caregiver_id: readinessSeesHr ? sid : (hasSid ? 'present' : '')", 'state_caregiver_id: sid');
  try {
    await mustFail('M1. projection reverted to the whole blob -> P1 red', m1);
    await mustFail('M2. role split removed (value for everyone) -> P2 red', m2);
  } finally { [m1, m2].forEach((f) => { try { fs.unlinkSync(f); } catch (e) { /* gone */ } }); }
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exitCode = fail ? 1 : 0;
})();
