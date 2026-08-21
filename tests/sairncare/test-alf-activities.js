// Isolated test of the alf_activities gate in api/sd-data.js. Runs the
// REAL handler (not a reimplementation) with mocked auth/license/fetch.
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

let ACT_ROWS = [];

global.fetch = async (url, opts) => {
  opts = opts || {};
  const method = opts.method || 'GET';
  if (method === 'GET' && /alf_activities\?license_hash=eq\.[^&]+&select=entry_id,data/.test(url)) {
    return { ok: true, status: 200, json: async () => ACT_ROWS.map((r) => ({ entry_id: r.entry_id, data: r.data })) };
  }
  if (method === 'POST' && /alf_activities\?on_conflict=/.test(url)) {
    const body = JSON.parse(opts.body);
    const idx = ACT_ROWS.findIndex((r) => r.entry_id === body.entry_id);
    const row = { entry_id: body.entry_id, data: body.data };
    if (idx === -1) ACT_ROWS.push(row); else ACT_ROWS[idx] = row;
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
    body: { action, resource: 'alf_activities', payload }
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
  await check('activities role CAN create an activity', async () => {
    const res = await call('activities', 'EMP-ACT', 'write', { id: 'ACT-1', name: 'Bingo', category: 'social', date: '2026-08-21', attendees: ['RES-1'] });
    assertEq(res.statusCode, 200);
  });
  await check('owner CAN create an activity too', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', { id: 'ACT-2', name: 'Morning Stretch', category: 'physical', date: '2026-08-21', attendees: [] });
    assertEq(res.statusCode, 200);
  });
  await check('nursing CANNOT create an activity', async () => {
    const res = await call('nursing', 'EMP-NUR', 'write', { id: 'ACT-3', name: 'x' });
    assertEq(res.statusCode, 403);
  });
  await check('med_aide CANNOT create an activity', async () => {
    const res = await call('med_aide', 'MA-1', 'write', { id: 'ACT-4', name: 'x' });
    assertEq(res.statusCode, 403);
  });
  await check('billing CANNOT create an activity', async () => {
    const res = await call('billing', 'EMP-BILL', 'write', { id: 'ACT-5', name: 'x' });
    assertEq(res.statusCode, 403);
  });
  await check('caregiver CANNOT create an activity', async () => {
    const res = await call('caregiver', 'CG-1', 'write', { id: 'ACT-6', name: 'x' });
    assertEq(res.statusCode, 403);
  });

  await check('EVERY role can READ the activities calendar (broad, non-clinical)', async () => {
    for (const role of ['owner', 'nursing', 'med_aide', 'caregiver', 'billing', 'activities']) {
      const res = await call(role, 'EMP-' + role, 'read', null);
      assertEq(res.statusCode, 200, role + ' should be able to read');
    }
  });
  await check('read returns real attendee data', async () => {
    const res = await call('caregiver', 'CG-1', 'read', null);
    const bingo = res.body.data.find((a) => a.id === 'ACT-1');
    assertEq(bingo.attendees, ['RES-1']);
  });

  await check('missing id is 400', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', { name: 'x' });
    assertEq(res.statusCode, 400);
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
