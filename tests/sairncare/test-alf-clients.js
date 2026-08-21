// Isolated test of the alf_clients four-tier resident privacy gate in
// api/sd-data.js. Runs the REAL handler (not a reimplementation) with
// mocked auth/license/fetch so no real Supabase/session infra is needed.
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
  return JSON.parse(token); // {role, employee_id}
};

// In-memory fixture roster: RES-1 assigned to MA-1, RES-2 unassigned, RES-3 assigned to MA-2.
let ROSTER = {
  'RES-1': { assigned_employee_id: 'MA-1', data: { name: 'Resident One' } },
  'RES-2': { assigned_employee_id: null, data: { name: 'Resident Two' } },
  'RES-3': { assigned_employee_id: 'MA-2', data: { name: 'Resident Three' } }
};
const WRITES = [];

global.fetch = async (url, opts) => {
  opts = opts || {};
  const method = opts.method || 'GET';
  if (method === 'GET' && /alf_clients\?license_hash=eq\.[^&]+&select=client_id,assigned_employee_id,data/.test(url)) {
    const rows = Object.keys(ROSTER).map((id) => ({
      client_id: id, assigned_employee_id: ROSTER[id].assigned_employee_id, data: ROSTER[id].data
    }));
    return { ok: true, status: 200, json: async () => rows };
  }
  const existingMatch = url.match(/client_id=eq\.([^&]+)&select=assigned_employee_id/);
  if (method === 'GET' && existingMatch) {
    const id = decodeURIComponent(existingMatch[1]);
    const row = ROSTER[id];
    return { ok: true, status: 200, json: async () => (row ? [{ assigned_employee_id: row.assigned_employee_id }] : []) };
  }
  if (method === 'POST' && /alf_clients\?on_conflict=/.test(url)) {
    const body = JSON.parse(opts.body);
    WRITES.push(body);
    ROSTER[body.client_id] = { assigned_employee_id: body.assigned_employee_id, data: body.data };
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
    headers: {
      authorization: 'Bearer testkey',
      'x-test-token': JSON.stringify({ role, employee_id: employeeId })
    },
    body: { action, resource: 'alf_clients', payload }
  };
  const res = fakeRes();
  await handler(req, res);
  return res;
}

let pass = 0, fail = 0;
async function check(name, fn) {
  try {
    await fn();
    pass++;
    console.log('PASS ' + name);
  } catch (e) {
    fail++;
    console.log('FAIL ' + name + ' -- ' + e.message);
  }
}
function assertEq(actual, expected, msg) {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error((msg || 'mismatch') + ': expected ' + JSON.stringify(expected) + ' got ' + JSON.stringify(actual));
  }
}

(async () => {
  // ---- READ tier tests ----
  await check('owner (management) read sees all 3 residents', async () => {
    const res = await call('owner', 'EMP-OWN', 'read', null);
    assertEq(res.statusCode, 200);
    assertEq(res.body.data.length, 3);
  });
  await check('billing (management) read sees all 3 residents', async () => {
    const res = await call('billing', 'EMP-BILL', 'read', null);
    assertEq(res.body.data.length, 3);
  });
  await check('nursing (broad edit) read sees all 3 residents', async () => {
    const res = await call('nursing', 'EMP-NUR', 'read', null);
    assertEq(res.body.data.length, 3);
  });
  await check('activities (broad read-only) read sees all 3 residents', async () => {
    const res = await call('activities', 'EMP-ACT', 'read', null);
    assertEq(res.body.data.length, 3);
  });
  await check('med_aide (narrow) read sees ONLY own-assigned (RES-1)', async () => {
    const res = await call('med_aide', 'MA-1', 'read', null);
    assertEq(res.body.data.length, 1);
    assertEq(res.body.data[0].id, 'RES-1');
  });
  await check('caregiver (narrow) read sees ONLY own-assigned, none assigned = empty', async () => {
    const res = await call('caregiver', 'CG-X', 'read', null);
    assertEq(res.body.data.length, 0);
  });
  await check('med_aide read never sees unassigned RES-2 or other-assigned RES-3', async () => {
    const res = await call('med_aide', 'MA-2', 'read', null);
    const ids = res.body.data.map((r) => r.id);
    assertEq(ids, ['RES-3']);
  });

  // ---- WRITE tier tests ----
  await check('activities write is refused outright with 403 (never silently downgraded)', async () => {
    const res = await call('activities', 'EMP-ACT', 'write', { id: 'RES-2', name: 'x' });
    assertEq(res.statusCode, 403);
    assertEq(res.body.error.code, 'FORBIDDEN');
  });
  await check('nursing may edit any resident detail without changing assignment', async () => {
    const res = await call('nursing', 'EMP-NUR', 'write', { id: 'RES-1', name: 'Updated by nursing' });
    assertEq(res.statusCode, 200);
    assertEq(ROSTER['RES-1'].assigned_employee_id, 'MA-1');
    assertEq(ROSTER['RES-1'].data.name, 'Updated by nursing');
  });
  await check('nursing reassigning a resident is 403 forbidden', async () => {
    const res = await call('nursing', 'EMP-NUR', 'write', { id: 'RES-1', assigned_employee_id: 'MA-2' });
    assertEq(res.statusCode, 403);
    assertEq(ROSTER['RES-1'].assigned_employee_id, 'MA-1', 'assignment must not have changed');
  });
  await check('nursing creating a NEW resident with an explicit assignee is 403 (cannot assign)', async () => {
    const res = await call('nursing', 'EMP-NUR', 'write', { id: 'RES-NEW-N', assigned_employee_id: 'MA-1' });
    assertEq(res.statusCode, 403);
  });
  await check('nursing creating a NEW unassigned resident is allowed', async () => {
    const res = await call('nursing', 'EMP-NUR', 'write', { id: 'RES-NEW-N2', name: 'brand new' });
    assertEq(res.statusCode, 200);
    assertEq(ROSTER['RES-NEW-N2'].assigned_employee_id, null);
  });
  await check('management (owner) CAN reassign a resident', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', { id: 'RES-1', assigned_employee_id: 'MA-2' });
    assertEq(res.statusCode, 200);
    assertEq(ROSTER['RES-1'].assigned_employee_id, 'MA-2');
  });
  await check('med_aide (narrow) self-assign-on-create with explicit own id succeeds', async () => {
    const res = await call('med_aide', 'MA-9', 'write', { id: 'RES-NEW-1', name: 'new one', assigned_employee_id: 'MA-9' });
    assertEq(res.statusCode, 200);
    assertEq(ROSTER['RES-NEW-1'].assigned_employee_id, 'MA-9');
  });
  await check('med_aide creating without explicit own-id assignment is 403 (no implicit self-assign)', async () => {
    const res = await call('med_aide', 'MA-9', 'write', { id: 'RES-NEW-3', name: 'no assignee field' });
    assertEq(res.statusCode, 403);
  });
  await check('med_aide can edit a resident already assigned to them', async () => {
    const res = await call('med_aide', 'MA-9', 'write', { id: 'RES-NEW-1', name: 'edited', assigned_employee_id: 'MA-9' });
    assertEq(res.statusCode, 200);
    assertEq(ROSTER['RES-NEW-1'].data.name, 'edited');
  });
  await check('med_aide CANNOT edit a resident assigned to someone else (RES-3 -> MA-2)', async () => {
    const res = await call('med_aide', 'MA-9', 'write', { id: 'RES-3', name: 'hijack attempt' });
    assertEq(res.statusCode, 403);
    assertEq(ROSTER['RES-3'].data.name !== 'hijack attempt', true);
  });
  await check('med_aide cannot reassign their own resident away to someone else', async () => {
    const res = await call('med_aide', 'MA-9', 'write', { id: 'RES-NEW-1', assigned_employee_id: 'MA-2' });
    assertEq(res.statusCode, 403);
    assertEq(ROSTER['RES-NEW-1'].assigned_employee_id, 'MA-9');
  });
  await check('caregiver tier follows the same narrow rules as med_aide (self-assign-on-create)', async () => {
    const res = await call('caregiver', 'CG-1', 'write', { id: 'RES-NEW-CG', name: 'cg new', assigned_employee_id: 'CG-1' });
    assertEq(res.statusCode, 200);
    assertEq(ROSTER['RES-NEW-CG'].assigned_employee_id, 'CG-1');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
