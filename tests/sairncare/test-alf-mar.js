// Isolated test of the alf_mar MAR gate in api/sd-data.js. Runs the REAL
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

// Fixture: RES-1 assigned to MA-1, RES-2 assigned to MA-2.
const RESIDENTS = { 'RES-1': 'MA-1', 'RES-2': 'MA-2' };
let MAR_ROWS = []; // {entry_id, resident_id, assigned_employee_id, entry_type, data}

global.fetch = async (url, opts) => {
  opts = opts || {};
  const method = opts.method || 'GET';

  // alf_clients assignment lookup (for the write path's live look-up)
  const clientLookup = url.match(/alf_clients\?license_hash=eq\.[^&]+&client_id=eq\.([^&]+)&select=assigned_employee_id/);
  if (method === 'GET' && clientLookup) {
    const id = decodeURIComponent(clientLookup[1]);
    const assignee = RESIDENTS[id];
    return { ok: true, status: 200, json: async () => (assignee !== undefined ? [{ assigned_employee_id: assignee }] : []) };
  }

  // alf_mar facility-wide read
  if (method === 'GET' && /alf_mar\?license_hash=eq\.[^&]+&select=entry_id,resident_id,assigned_employee_id,entry_type,data/.test(url)) {
    return { ok: true, status: 200, json: async () => MAR_ROWS.map((r) => ({ entry_id: r.entry_id, resident_id: r.resident_id, assigned_employee_id: r.assigned_employee_id, entry_type: r.entry_type, data: r.data })) };
  }

  // alf_mar existing-entry-id check (append-only integrity)
  const existingMatch = url.match(/alf_mar\?license_hash=eq\.[^&]+&entry_id=eq\.([^&]+)&select=id/);
  if (method === 'GET' && existingMatch) {
    const id = decodeURIComponent(existingMatch[1]);
    const found = MAR_ROWS.find((r) => r.entry_id === id);
    return { ok: true, status: 200, json: async () => (found ? [{ id: 'x' }] : []) };
  }

  // alf_mar write
  if (method === 'POST' && /alf_mar\?on_conflict=/.test(url)) {
    const body = JSON.parse(opts.body);
    const idx = MAR_ROWS.findIndex((r) => r.entry_id === body.entry_id);
    const row = { entry_id: body.entry_id, resident_id: body.resident_id, assigned_employee_id: body.assigned_employee_id, entry_type: body.entry_type, data: body.data };
    if (idx === -1) MAR_ROWS.push(row); else MAR_ROWS[idx] = row;
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
    body: { action, resource: 'alf_mar', payload }
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
  await check('billing has zero MAR access: read is 403', async () => {
    const res = await call('billing', 'EMP-BILL', 'read', null);
    assertEq(res.statusCode, 403);
  });
  await check('caregiver has zero MAR access: write is 403', async () => {
    const res = await call('caregiver', 'CG-1', 'write', { id: 'X1', resident_id: 'RES-1', entry_type: 'administration' });
    assertEq(res.statusCode, 403);
  });
  await check('activities has zero MAR access: read is 403', async () => {
    const res = await call('activities', 'EMP-ACT', 'read', null);
    assertEq(res.statusCode, 403);
  });

  await check('owner can create a medication_order for any resident', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', { id: 'MED-1', resident_id: 'RES-1', entry_type: 'medication_order', name: 'Metformin', dose: '500mg' });
    assertEq(res.statusCode, 200);
  });
  await check('nursing can create a reconciliation entry', async () => {
    const res = await call('nursing', 'EMP-NUR', 'write', { id: 'REC-1', resident_id: 'RES-1', entry_type: 'reconciliation', type: 'admission', summary: 'no discrepancies' });
    assertEq(res.statusCode, 200);
  });
  await check('nursing can create an assessment_refusal entry', async () => {
    const res = await call('nursing', 'EMP-NUR', 'write', { id: 'REF-1', resident_id: 'RES-1', entry_type: 'assessment_refusal', legal_rep_notified: true });
    assertEq(res.statusCode, 200);
  });

  await check('med_aide CANNOT create a medication_order (clinical-decision type)', async () => {
    const res = await call('med_aide', 'MA-1', 'write', { id: 'MED-2', resident_id: 'RES-1', entry_type: 'medication_order', name: 'Lisinopril' });
    assertEq(res.statusCode, 403);
  });
  await check('med_aide CANNOT create a reconciliation entry', async () => {
    const res = await call('med_aide', 'MA-1', 'write', { id: 'REC-2', resident_id: 'RES-1', entry_type: 'reconciliation' });
    assertEq(res.statusCode, 403);
  });
  await check('med_aide CANNOT create an assessment_refusal entry', async () => {
    const res = await call('med_aide', 'MA-1', 'write', { id: 'REF-2', resident_id: 'RES-1', entry_type: 'assessment_refusal' });
    assertEq(res.statusCode, 403);
  });

  await check('med_aide CAN log administration for their own-assigned resident (RES-1)', async () => {
    const res = await call('med_aide', 'MA-1', 'write', { id: 'ADM-1', resident_id: 'RES-1', entry_type: 'administration', medication_id: 'MED-1', status: 'given' });
    assertEq(res.statusCode, 200);
  });
  await check('med_aide CANNOT log administration for a resident assigned to someone else (RES-2)', async () => {
    const res = await call('med_aide', 'MA-1', 'write', { id: 'ADM-2', resident_id: 'RES-2', entry_type: 'administration', medication_id: 'MED-1', status: 'given' });
    assertEq(res.statusCode, 403);
  });
  await check('med_aide CAN log a controlled-substance count for their own-assigned resident', async () => {
    const res = await call('med_aide', 'MA-1', 'write', { id: 'CNT-1', resident_id: 'RES-1', entry_type: 'count', medication_id: 'MED-1', witness_id: 'EMP-NUR', count_value: 30 });
    assertEq(res.statusCode, 200);
  });

  await check('append-only integrity: reusing an administration id is 409, not silently overwritten', async () => {
    const res = await call('med_aide', 'MA-1', 'write', { id: 'ADM-1', resident_id: 'RES-1', entry_type: 'administration', status: 'refused' });
    assertEq(res.statusCode, 409);
    assertEq(res.body.error.code, 'ALREADY_RECORDED');
  });
  await check('medication_order IS editable in place (same id, no 409)', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', { id: 'MED-1', resident_id: 'RES-1', entry_type: 'medication_order', name: 'Metformin', dose: '1000mg', discontinued: false });
    assertEq(res.statusCode, 200);
  });

  await check('unknown resident_id is 400', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', { id: 'ADM-99', resident_id: 'RES-NOPE', entry_type: 'administration' });
    assertEq(res.statusCode, 400);
  });

  await check('owner read sees ALL entry types across all residents (facility-wide)', async () => {
    const res = await call('owner', 'EMP-OWN', 'read', null);
    assertEq(res.statusCode, 200);
    const types = res.body.data.map((d) => d.entry_type).sort();
    assertEq(types.indexOf('medication_order') !== -1, true);
    assertEq(types.indexOf('reconciliation') !== -1, true);
    assertEq(types.indexOf('assessment_refusal') !== -1, true);
    assertEq(types.indexOf('administration') !== -1, true);
    assertEq(types.indexOf('count') !== -1, true);
  });
  await check('med_aide read is scoped to their own-assigned resident only', async () => {
    const res = await call('med_aide', 'MA-1', 'read', null);
    const residentIds = res.body.data.map((d) => d.resident_id);
    assertEq(residentIds.every((id) => id === 'RES-1'), true, 'every entry must belong to RES-1');
  });
  await check('a different med_aide (MA-2, RES-2 assignee, zero entries yet) sees nothing', async () => {
    const res = await call('med_aide', 'MA-2', 'read', null);
    assertEq(res.body.data.length, 0);
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
