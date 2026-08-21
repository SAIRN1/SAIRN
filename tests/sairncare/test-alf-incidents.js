// Isolated test of the alf_incidents gate in api/sd-data.js. Runs the REAL
// handler (not a reimplementation) with mocked auth/license/fetch.
'use strict';
const path = require('path');
const ROOT = path.join(__dirname, '..', '..');

process.env.SUPABASE_URL = 'https://fake.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'fake-service-key';

const licenseMod = require(path.join(ROOT, 'api/_lib/license.js'));
licenseMod.validateLicenseKey = async () => ({
  valid: true, active: true, license_hash: 'HASH1', stripe_subscription_id: 'sub_1', trial_ends_at: null
});

const authMod = require(path.join(ROOT, 'api/_lib/auth.js'));
authMod.tokenFromRequest = (req) => req.headers['x-test-token'] || null;
authMod.verifySessionToken = (token, licHash, expectedApp) => {
  if (!token) return null;
  if (expectedApp !== 'sairncare') throw new Error('expected app scope not sairncare: ' + expectedApp);
  return JSON.parse(token);
};

let INCIDENT_ROWS = []; // {entry_id, resident_id, data}

global.fetch = async (url, opts) => {
  opts = opts || {};
  const method = opts.method || 'GET';
  if (method === 'GET' && /alf_incidents\?license_hash=eq\.[^&]+&select=entry_id,resident_id,data/.test(url)) {
    return { ok: true, status: 200, json: async () => INCIDENT_ROWS.map((r) => ({ entry_id: r.entry_id, resident_id: r.resident_id, data: r.data })) };
  }
  const existingMatch = url.match(/alf_incidents\?license_hash=eq\.[^&]+&entry_id=eq\.([^&]+)&select=id/);
  if (method === 'GET' && existingMatch) {
    const id = decodeURIComponent(existingMatch[1]);
    const found = INCIDENT_ROWS.find((r) => r.entry_id === id);
    return { ok: true, status: 200, json: async () => (found ? [{ id: 'x' }] : []) };
  }
  if (method === 'POST' && /alf_incidents\?on_conflict=/.test(url)) {
    const body = JSON.parse(opts.body);
    const idx = INCIDENT_ROWS.findIndex((r) => r.entry_id === body.entry_id);
    const row = { entry_id: body.entry_id, resident_id: body.resident_id, data: body.data };
    if (idx === -1) INCIDENT_ROWS.push(row); else INCIDENT_ROWS[idx] = row;
    return { ok: true, status: 200, json: async () => [body] };
  }
  throw new Error('Unmocked fetch: ' + method + ' ' + url);
};

delete require.cache[require.resolve(path.join(ROOT, 'api/sd-data.js'))];
const handler = require(path.join(ROOT, 'api/sd-data.js'));

function fakeRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}
async function call(role, employeeId, action, payload) {
  const req = {
    method: 'POST',
    headers: { authorization: 'Bearer testkey', 'x-test-token': JSON.stringify({ role, employee_id: employeeId }) },
    body: { action, resource: 'alf_incidents', payload }
  };
  const res = fakeRes();
  await handler(req, res);
  return res;
}

let pass = 0, fail = 0;
async function check(name, fn) {
  try { await fn(); pass++; console.log('PASS ' + name); }
  catch (e) { fail++; console.log('FAIL ' + name + ' -- ' + e.message); }
}
function assertEq(actual, expected, msg) {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error((msg || 'mismatch') + ': expected ' + JSON.stringify(expected) + ' got ' + JSON.stringify(actual));
  }
}

(async () => {
  await check('caregiver CAN file a new incident report (mandatory-reporting-by-witness)', async () => {
    const res = await call('caregiver', 'CG-1', 'write', { id: 'INC-1', resident_id: 'RES-1', category: 'fall', description: 'resident fell in hallway' });
    assertEq(res.statusCode, 200);
  });
  await check('med_aide CAN file a new incident report', async () => {
    const res = await call('med_aide', 'MA-1', 'write', { id: 'INC-2', resident_id: 'RES-1', category: 'medication_error', description: 'wrong dose given' });
    assertEq(res.statusCode, 200);
  });
  await check('activities CAN file a new incident report', async () => {
    const res = await call('activities', 'EMP-ACT', 'write', { id: 'INC-3', category: 'behavioral', description: 'agitation during group activity' });
    assertEq(res.statusCode, 200);
  });

  await check('caregiver CANNOT read the incident log', async () => {
    const res = await call('caregiver', 'CG-1', 'read', null);
    assertEq(res.statusCode, 403);
  });
  await check('med_aide CANNOT read the incident log', async () => {
    const res = await call('med_aide', 'MA-1', 'read', null);
    assertEq(res.statusCode, 403);
  });
  await check('activities CANNOT read the incident log', async () => {
    const res = await call('activities', 'EMP-ACT', 'read', null);
    assertEq(res.statusCode, 403);
  });

  await check('owner CAN read the incident log', async () => {
    const res = await call('owner', 'EMP-OWN', 'read', null);
    assertEq(res.statusCode, 200);
    assertEq(res.body.data.length, 3);
  });
  await check('nursing CAN read the incident log', async () => {
    const res = await call('nursing', 'EMP-NUR', 'read', null);
    assertEq(res.statusCode, 200);
  });
  await check('billing CAN read the incident log', async () => {
    const res = await call('billing', 'EMP-BILL', 'read', null);
    assertEq(res.statusCode, 200);
  });

  await check('the ORIGINAL FILER (caregiver) CANNOT go back and edit their own filed report', async () => {
    const res = await call('caregiver', 'CG-1', 'write', { id: 'INC-1', resident_id: 'RES-1', category: 'fall', description: 'EDITED -- trying to alter my own report' });
    assertEq(res.statusCode, 403);
  });
  await check('nursing CAN update an existing report (add follow-up/status)', async () => {
    const res = await call('nursing', 'EMP-NUR', 'write', { id: 'INC-1', resident_id: 'RES-1', category: 'fall', description: 'resident fell in hallway', status: 'closed', follow_up_notes: 'x-ray negative, no injury found', state_reported: true, state_reported_date: '2026-08-20' });
    assertEq(res.statusCode, 200);
    assertEq(res.body.data.status, 'closed');
  });
  await check('owner CAN update an existing report too', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', { id: 'INC-2', resident_id: 'RES-1', category: 'medication_error', status: 'under_review' });
    assertEq(res.statusCode, 200);
  });
  await check('billing CANNOT create a new report about... wait, billing CAN file too (any role can create)', async () => {
    const res = await call('billing', 'EMP-BILL', 'write', { id: 'INC-4', category: 'other', description: 'billing witnessed something' });
    assertEq(res.statusCode, 200);
  });

  await check('missing id is 400', async () => {
    const res = await call('caregiver', 'CG-1', 'write', { category: 'fall' });
    assertEq(res.statusCode, 400);
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
