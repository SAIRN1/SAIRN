// Isolated test of alf_signals (Phase 0 item 3, passive-monitoring signal
// log) in api/sd-data.js. Runs the REAL handler with mocked auth/license/
// fetch, not a reimplementation.
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

let ROWS = [];

global.fetch = async (url, opts) => {
  opts = opts || {};
  const method = opts.method || 'GET';
  if (method === 'GET' && /alf_signals\?license_hash=eq\.[^&]+&select=entry_id,resident_id,signal_type,data,recorded_at/.test(url)) {
    return { ok: true, status: 200, json: async () => ROWS.slice() };
  }
  const existingMatch = url.match(/alf_signals\?license_hash=eq\.[^&]+&entry_id=eq\.([^&]+)&select=id/);
  if (method === 'GET' && existingMatch) {
    const id = decodeURIComponent(existingMatch[1]);
    const found = ROWS.filter((r) => r.entry_id === id);
    return { ok: true, status: 200, json: async () => (found.length ? [{ id: '1' }] : []) };
  }
  if (method === 'POST' && /\/rest\/v1\/alf_signals$/.test(url)) {
    const body = JSON.parse(opts.body);
    ROWS.push(body);
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
    body: { action, resource: 'alf_signals', payload }
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
  await check('nursing (non-management) write is refused (403)', async () => {
    const res = await call('nursing', 'EMP-NUR', 'write', { id: 'SIG-1', resident_id: 'RES-1', signal_type: 'bed_exit' });
    assertEq(res.statusCode, 403);
    assertEq(ROWS.length, 0);
  });

  await check('an unauthenticated read is refused (401)', async () => {
    const req = { method: 'POST', headers: { authorization: 'Bearer testkey' }, body: { action: 'read', resource: 'alf_signals', payload: null } };
    const res = fakeRes();
    await handler(req, res);
    assertEq(res.statusCode, 401);
  });

  await check('a read with zero rows reports coverage {have:0, need:4}', async () => {
    const res = await call('nursing', 'EMP-NUR', 'read', null);
    assertEq(res.statusCode, 200);
    assertEq(res.body.data.length, 0);
    assertEq(res.body.coverage, { have: 0, need: 4 });
  });

  await check('management CAN record a valid signal', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', { id: 'SIG-1', resident_id: 'RES-1', signal_type: 'bed_exit', value: 'exited at 02:14' });
    assertEq(res.statusCode, 200);
    assertEq(ROWS.length, 1);
    assertEq(ROWS[0].signal_type, 'bed_exit');
  });

  await check('an invalid signal_type is refused (400), not silently stored', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', { id: 'SIG-2', resident_id: 'RES-1', signal_type: 'not_a_real_type' });
    assertEq(res.statusCode, 400);
    assertEq(ROWS.length, 1, 'must not have been added');
  });

  await check('reusing an entry id is refused (409), append-only, never a silent overwrite', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', { id: 'SIG-1', resident_id: 'RES-1', signal_type: 'fall_detection' });
    assertEq(res.statusCode, 409);
    assertEq(ROWS.length, 1);
    assertEq(ROWS[0].signal_type, 'bed_exit', 'original entry must be unchanged');
  });

  await check('coverage reflects real distinct signal_type rows only, never a fabricated count', async () => {
    await call('owner', 'EMP-OWN', 'write', { id: 'SIG-3', resident_id: 'RES-1', signal_type: 'fall_detection' });
    const res = await call('nursing', 'EMP-NUR', 'read', null);
    assertEq(res.body.coverage, { have: 2, need: 4 });
  });

  await check('no risk_score or any derived-score field appears anywhere in a read response', async () => {
    const res = await call('nursing', 'EMP-NUR', 'read', null);
    const flat = JSON.stringify(res.body);
    assertEq(/risk_?score/i.test(flat), false);
  });

  await check('read is available facility-wide to any authenticated role, not just management', async () => {
    const res = await call('activities', 'EMP-ACT', 'read', null);
    assertEq(res.statusCode, 200);
    assertEq(res.body.data.length, 2);
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
