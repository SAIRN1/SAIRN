// Isolated test of the alf_billing gate in api/sd-data.js. Runs the REAL
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

let BILLING_ROWS = []; // {entry_id, resident_id, data}

global.fetch = async (url, opts) => {
  opts = opts || {};
  const method = opts.method || 'GET';
  if (method === 'GET' && /alf_billing\?license_hash=eq\.[^&]+&select=entry_id,resident_id,data/.test(url)) {
    return { ok: true, status: 200, json: async () => BILLING_ROWS.map((r) => ({ entry_id: r.entry_id, resident_id: r.resident_id, data: r.data })) };
  }
  if (method === 'POST' && /alf_billing\?on_conflict=/.test(url)) {
    const body = JSON.parse(opts.body);
    const idx = BILLING_ROWS.findIndex((r) => r.entry_id === body.entry_id);
    const row = { entry_id: body.entry_id, resident_id: body.resident_id, data: body.data };
    if (idx === -1) BILLING_ROWS.push(row); else BILLING_ROWS[idx] = row;
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
    body: { action, resource: 'alf_billing', payload }
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
  await check('nursing has zero billing access: read is 403', async () => {
    const res = await call('nursing', 'EMP-NUR', 'read', null);
    assertEq(res.statusCode, 403);
  });
  await check('med_aide has zero billing access: write is 403', async () => {
    const res = await call('med_aide', 'MA-1', 'write', { id: 'INV-RES-1-2026-08', resident_id: 'RES-1' });
    assertEq(res.statusCode, 403);
  });
  await check('caregiver has zero billing access: read is 403', async () => {
    const res = await call('caregiver', 'CG-1', 'read', null);
    assertEq(res.statusCode, 403);
  });
  await check('activities has zero billing access: write is 403', async () => {
    const res = await call('activities', 'EMP-ACT', 'write', { id: 'INV-RES-1-2026-08', resident_id: 'RES-1' });
    assertEq(res.statusCode, 403);
  });

  await check('owner can create an invoice, room_board and care kept as separate fields', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', {
      id: 'INV-RES-1-2026-08', resident_id: 'RES-1', month: '2026-08',
      room_board_amount: 3500, care_amount: 900, private_total: 4400, private_status: 'unpaid',
      hcbs_claim_amount: 0, hcbs_status: 'n/a', generated_by: 'EMP-OWN'
    });
    assertEq(res.statusCode, 200);
    assertEq(res.body.data.room_board_amount, 3500);
    assertEq(res.body.data.care_amount, 900);
  });
  await check('billing role can create a Medicaid HCBS invoice, care-only claim amount, room/board never in it', async () => {
    const res = await call('billing', 'EMP-BILL', 'write', {
      id: 'INV-RES-2-2026-08', resident_id: 'RES-2', month: '2026-08',
      room_board_amount: 3200, care_amount: 750, private_total: 3200, private_status: 'unpaid',
      hcbs_claim_amount: 750, hcbs_status: 'not_submitted', generated_by: 'EMP-BILL'
    });
    assertEq(res.statusCode, 200);
    assertEq(res.body.data.private_total, 3200, 'private_total must be room_board ONLY, never the care amount, for an HCBS resident');
    assertEq(res.body.data.hcbs_claim_amount, 750, 'hcbs_claim_amount must be care ONLY, never room_board');
  });

  await check('regenerating the SAME resident+month invoice upserts in place, not a duplicate row', async () => {
    const before = (await call('owner', 'EMP-OWN', 'read', null)).body.data.length;
    await call('owner', 'EMP-OWN', 'write', {
      id: 'INV-RES-1-2026-08', resident_id: 'RES-1', month: '2026-08',
      room_board_amount: 3500, care_amount: 900, private_total: 4400, private_status: 'paid',
      hcbs_claim_amount: 0, hcbs_status: 'n/a', generated_by: 'EMP-OWN'
    });
    const after = await call('owner', 'EMP-OWN', 'read', null);
    assertEq(after.body.data.length, before, 'row count must not grow on a same-id regeneration');
    const row = after.body.data.find((r) => r.id === 'INV-RES-1-2026-08');
    assertEq(row.private_status, 'paid', 'the update must actually apply');
  });

  await check('missing resident_id is 400', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', { id: 'INV-X' });
    assertEq(res.statusCode, 400);
  });

  await check('owner read sees both invoices across residents', async () => {
    const res = await call('owner', 'EMP-OWN', 'read', null);
    assertEq(res.body.data.length, 2);
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
