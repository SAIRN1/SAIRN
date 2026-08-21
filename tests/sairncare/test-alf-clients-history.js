// Isolated test of alf_clients' care_level_history (Phase 0 item 1) and
// ccrc_contract_type (Phase 0 item 2) additions in api/sd-data.js. Runs the
// REAL handler with mocked auth/license/fetch, not a reimplementation.
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

// In-memory fixture roster, this time WITH a real data blob on the existing-row
// lookup (the four-tier gate test's mock deliberately omits it -- this file
// exercises the path that mock can't).
let ROSTER = {
  'RES-1': { assigned_employee_id: 'MA-1', data: { name: 'Resident One', care_level: 'al1' } }
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
  const existingMatch = url.match(/client_id=eq\.([^&]+)&select=assigned_employee_id,data/);
  if (method === 'GET' && existingMatch) {
    const id = decodeURIComponent(existingMatch[1]);
    const row = ROSTER[id];
    return { ok: true, status: 200, json: async () => (row ? [{ assigned_employee_id: row.assigned_employee_id, data: row.data }] : []) };
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
    headers: { authorization: 'Bearer testkey', 'x-test-token': JSON.stringify({ role, employee_id: employeeId }) },
    body: { action, resource: 'alf_clients', payload }
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
  await check('nursing attempting to include care_level_history is 403, resident untouched', async () => {
    const res = await call('nursing', 'EMP-NUR', 'write', {
      id: 'RES-1', name: 'Resident One',
      care_level_history: [{ level: 'assisted_living', sub_tier: 'al2', effective_date: '2026-08-21' }]
    });
    assertEq(res.statusCode, 403);
    assertEq(ROSTER['RES-1'].data.care_level_history, undefined, 'must not have been written');
  });

  await check('management CAN start a care_level_history with a valid first entry', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', {
      id: 'RES-1', name: 'Resident One',
      care_level_history: [{ level: 'assisted_living', sub_tier: 'al2', effective_date: '2026-08-21' }]
    });
    assertEq(res.statusCode, 200);
    assertEq(ROSTER['RES-1'].data.care_level_history.length, 1);
    assertEq(ROSTER['RES-1'].data.care_level_history[0].level, 'assisted_living');
    assertEq(ROSTER['RES-1'].data.care_level_history[0].sub_tier, 'al2');
  });

  await check('care_level is derived from the last history entry (assisted_living+sub_tier -> flat sub_tier)', async () => {
    assertEq(ROSTER['RES-1'].data.care_level, 'al2');
  });

  await check('changed_by/changed_at are server-stamped, client-supplied values are ignored', async () => {
    // Realistic client behavior: start from the exact array the server already returned
    // (server-stamped fields and all), then append the new entry -- never re-author the
    // existing prefix by hand, since the append-only check requires an exact match.
    const res = await call('owner', 'EMP-OWN', 'write', {
      id: 'RES-1', name: 'Resident One',
      care_level_history: ROSTER['RES-1'].data.care_level_history.concat([
        { level: 'memory_care', effective_date: '2026-09-01', changed_by: 'FORGED', changed_at: '2020-01-01T00:00:00.000Z' }
      ])
    });
    assertEq(res.statusCode, 200);
    const last = ROSTER['RES-1'].data.care_level_history[1];
    assertEq(last.changed_by, 'EMP-OWN');
    assertEq(last.changed_at !== '2020-01-01T00:00:00.000Z', true);
    assertEq(last.sub_tier, null, 'sub_tier must be null for a non-assisted_living level');
  });

  await check('care_level derives to the bare level name when not assisted_living', async () => {
    assertEq(ROSTER['RES-1'].data.care_level, 'memory_care');
  });

  await check('rewriting an existing history entry is refused (400), not silently accepted', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', {
      id: 'RES-1', name: 'Resident One',
      care_level_history: [
        { level: 'independent_living', effective_date: '2026-08-21' }, // tampered first entry
        { level: 'memory_care', effective_date: '2026-09-01' }
      ]
    });
    assertEq(res.statusCode, 400);
    assertEq(ROSTER['RES-1'].data.care_level_history[0].level, 'assisted_living', 'original entry must be untouched');
  });

  await check('shortening the history array is refused (400)', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', {
      id: 'RES-1', name: 'Resident One',
      care_level_history: [{ level: 'assisted_living', sub_tier: 'al2', effective_date: '2026-08-21' }]
    });
    assertEq(res.statusCode, 400);
    assertEq(ROSTER['RES-1'].data.care_level_history.length, 2, 'must still have both entries');
  });

  await check('an invalid level value is refused (400)', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', {
      id: 'RES-1', name: 'Resident One',
      care_level_history: ROSTER['RES-1'].data.care_level_history.concat([{ level: 'skilled_nursing_bogus', effective_date: '2026-10-01' }])
    });
    assertEq(res.statusCode, 400);
  });

  await check('assisted_living without a valid sub_tier is refused (400)', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', {
      id: 'RES-1', name: 'Resident One',
      care_level_history: ROSTER['RES-1'].data.care_level_history.concat([{ level: 'assisted_living', effective_date: '2026-10-01' }])
    });
    assertEq(res.statusCode, 400);
  });

  await check('a non-assisted_living entry carrying a sub_tier is refused (400)', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', {
      id: 'RES-1', name: 'Resident One',
      care_level_history: ROSTER['RES-1'].data.care_level_history.concat([{ level: 'skilled_nursing', sub_tier: 'al1', effective_date: '2026-10-01' }])
    });
    assertEq(res.statusCode, 400);
  });

  await check('a missing/malformed effective_date is refused (400)', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', {
      id: 'RES-1', name: 'Resident One',
      care_level_history: ROSTER['RES-1'].data.care_level_history.concat([{ level: 'skilled_nursing', effective_date: 'not-a-date' }])
    });
    assertEq(res.statusCode, 400);
  });

  await check('nursing editing an unrelated field never disturbs the existing care_level_history', async () => {
    const before = JSON.stringify(ROSTER['RES-1'].data.care_level_history);
    const res = await call('nursing', 'EMP-NUR', 'write', { id: 'RES-1', name: 'Renamed by nursing' });
    assertEq(res.statusCode, 200);
    assertEq(JSON.stringify(ROSTER['RES-1'].data.care_level_history), before, 'history must be carried forward unchanged');
    assertEq(ROSTER['RES-1'].data.name, 'Renamed by nursing');
  });

  // ---- ccrc_contract_type ----
  await check('a brand-new resident with no ccrc_contract_type defaults to not_ccrc', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', { id: 'RES-NEW-CCRC', name: 'New Resident' });
    assertEq(res.statusCode, 200);
    assertEq(ROSTER['RES-NEW-CCRC'].data.ccrc_contract_type, 'not_ccrc');
  });

  await check('a valid ccrc_contract_type is accepted', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', { id: 'RES-NEW-CCRC', name: 'New Resident', ccrc_contract_type: 'lifecare' });
    assertEq(res.statusCode, 200);
    assertEq(ROSTER['RES-NEW-CCRC'].data.ccrc_contract_type, 'lifecare');
  });

  await check('an invalid ccrc_contract_type is refused (400), not silently stored', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', { id: 'RES-NEW-CCRC', name: 'New Resident', ccrc_contract_type: 'bogus_type' });
    assertEq(res.statusCode, 400);
    assertEq(ROSTER['RES-NEW-CCRC'].data.ccrc_contract_type, 'lifecare', 'must not have changed');
  });

  await check('ccrc_contract_type is carried forward unchanged when omitted, even by narrow tier', async () => {
    const res = await call('med_aide', 'MA-1', 'write', { id: 'RES-NEW-CCRC', name: 'still lifecare', assigned_employee_id: 'MA-1' });
    // MA-1 is not assigned to RES-NEW-CCRC yet in this fixture, so self-assign-on-create rules
    // apply on an existing (unassigned) record -- this exercises the ccrc carry-forward path
    // regardless of gate outcome, so only check the ccrc value when the write actually succeeds.
    if (res.statusCode === 200) {
      assertEq(ROSTER['RES-NEW-CCRC'].data.ccrc_contract_type, 'lifecare');
    } else {
      assertEq(ROSTER['RES-NEW-CCRC'].data.ccrc_contract_type, 'lifecare', 'unaffected by a rejected write either way');
    }
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
