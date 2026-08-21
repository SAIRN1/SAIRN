// Isolated test of the alf_facility gate in api/sd-data.js. Runs the REAL
// handler (not a reimplementation) with mocked auth/license/fetch, same
// harness shape as test-alf-gate.js / test-alf-mar.js / test-alf-billing.js.
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

let FAC_ROWS = [];

global.fetch = async (url, opts) => {
  opts = opts || {};
  const method = opts.method || 'GET';
  if (method === 'GET' && /alf_facility\?license_hash=eq\.[^&]+&select=facility_id,data/.test(url)) {
    return { ok: true, status: 200, json: async () => FAC_ROWS.map((r) => ({ facility_id: r.facility_id, data: r.data })) };
  }
  if (method === 'POST' && /alf_facility\?on_conflict=/.test(url)) {
    const body = JSON.parse(opts.body);
    const idx = FAC_ROWS.findIndex((r) => r.facility_id === body.facility_id);
    const row = { facility_id: body.facility_id, data: body.data };
    if (idx === -1) FAC_ROWS.push(row); else FAC_ROWS[idx] = row;
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
    body: { action, resource: 'alf_facility', payload }
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

const FULL_PROFILE = {
  id: 'FAC-DEFAULT', name: 'Pinnacle Senior Living', company: 'Pinnacle Care LLC',
  licensing_state: 'OH', license_number: 'ALF-OH-11923', cs_policy: 'shift_change_count',
  incident_deadline: '24 hours',
  roomboard_rate: 3200, il_rate: 2400, al1_rate: 900, al2_rate: 1400, al3_rate: 2100,
  mc_rate: 2600, snf_rate: 4100, hcbs_enabled: false, hcbs_state: ''
};
const RATE_FIELDS = ['roomboard_rate', 'il_rate', 'al1_rate', 'al2_rate', 'al3_rate', 'mc_rate', 'snf_rate'];

(async () => {
  // ---- WRITE: management only ----
  await check('owner CAN write the facility profile', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', FULL_PROFILE);
    assertEq(res.statusCode, 200);
  });
  await check('billing CAN write the facility profile (management tier)', async () => {
    const res = await call('billing', 'EMP-BILL', 'write', Object.assign({}, FULL_PROFILE, { name: 'Pinnacle Senior Living North' }));
    assertEq(res.statusCode, 200);
  });
  await check('nursing CANNOT write the facility profile (clinical authority is not business authority)', async () => {
    const res = await call('nursing', 'EMP-NUR', 'write', FULL_PROFILE);
    assertEq(res.statusCode, 403);
  });
  await check('activities CANNOT write the facility profile', async () => {
    const res = await call('activities', 'EMP-ACT', 'write', FULL_PROFILE);
    assertEq(res.statusCode, 403);
  });
  await check('med_aide CANNOT write the facility profile', async () => {
    const res = await call('med_aide', 'MA-1', 'write', FULL_PROFILE);
    assertEq(res.statusCode, 403);
  });
  await check('caregiver CANNOT write the facility profile', async () => {
    const res = await call('caregiver', 'CG-1', 'write', FULL_PROFILE);
    assertEq(res.statusCode, 403);
  });
  await check('no session at all is 401, not 403', async () => {
    const req = { method: 'POST', headers: { authorization: 'Bearer testkey' }, body: { action: 'write', resource: 'alf_facility', payload: FULL_PROFILE } };
    const res = fakeRes();
    await handler(req, res);
    assertEq(res.statusCode, 401);
  });

  // ---- READ: everyone, but rates redacted outside management ----
  await check('management read returns the FULL rate card', async () => {
    for (const role of ['owner', 'billing']) {
      const res = await call(role, 'EMP-' + role, 'read', null);
      assertEq(res.statusCode, 200, role + ' read');
      assertEq(res.body.rates_visible, true, role + ' rates_visible');
      const fac = res.body.data.find((f) => f.id === 'FAC-DEFAULT');
      for (const rf of RATE_FIELDS) {
        if (fac[rf] === undefined) throw new Error(role + ' should see rate field ' + rf);
      }
    }
  });
  await check('nursing/med_aide/caregiver/activities read is 200 but EVERY rate field is stripped', async () => {
    for (const role of ['nursing', 'med_aide', 'caregiver', 'activities']) {
      const res = await call(role, 'EMP-' + role, 'read', null);
      assertEq(res.statusCode, 200, role + ' read');
      assertEq(res.body.rates_visible, false, role + ' rates_visible');
      const fac = res.body.data.find((f) => f.id === 'FAC-DEFAULT');
      for (const rf of RATE_FIELDS) {
        if (fac[rf] !== undefined) throw new Error(role + ' must NOT see rate field ' + rf + ' (got ' + fac[rf] + ')');
      }
    }
  });
  await check('the NON-financial half survives redaction -- a Med Aide still gets state + CS policy + deadline', async () => {
    const res = await call('med_aide', 'MA-1', 'read', null);
    const fac = res.body.data.find((f) => f.id === 'FAC-DEFAULT');
    assertEq(fac.licensing_state, 'OH');
    assertEq(fac.cs_policy, 'shift_change_count');
    assertEq(fac.incident_deadline, '24 hours');
    assertEq(fac.license_number, 'ALF-OH-11923');
  });
  await check('redaction does not mutate the stored row -- management still sees rates after a redacted read', async () => {
    await call('caregiver', 'CG-1', 'read', null);
    const res = await call('owner', 'EMP-OWN', 'read', null);
    const fac = res.body.data.find((f) => f.id === 'FAC-DEFAULT');
    assertEq(fac.al2_rate, 1400);
    assertEq(fac.roomboard_rate, 3200);
  });

  // ---- licensing_state validation ----
  await check('licensing_state is normalised to uppercase and trimmed', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', Object.assign({}, FULL_PROFILE, { licensing_state: ' in ' }));
    assertEq(res.statusCode, 200);
    assertEq(res.body.data.licensing_state, 'IN');
  });
  await check('a bogus licensing_state is REFUSED (400), not stored', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', Object.assign({}, FULL_PROFILE, { licensing_state: 'ZZ' }));
    assertEq(res.statusCode, 400);
    assertEq(res.body.error.code, 'BAD_STATE');
    const after = await call('owner', 'EMP-OWN', 'read', null);
    assertEq(after.body.data.find((f) => f.id === 'FAC-DEFAULT').licensing_state, 'IN', 'stored state must be unchanged by the refused write');
  });
  await check('a full state NAME is refused too -- only USPS codes are accepted', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', Object.assign({}, FULL_PROFILE, { licensing_state: 'Ohio' }));
    assertEq(res.statusCode, 400);
  });
  await check('an EMPTY licensing_state is allowed -- not-yet-filled-in is a real state of the world', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', Object.assign({}, FULL_PROFILE, { licensing_state: '' }));
    assertEq(res.statusCode, 200);
    assertEq(res.body.data.licensing_state, '');
  });
  await check('all four SEEDED states are accepted', async () => {
    for (const s of ['OH', 'IN', 'MI', 'PA']) {
      const res = await call('owner', 'EMP-OWN', 'write', Object.assign({}, FULL_PROFILE, { licensing_state: s }));
      assertEq(res.statusCode, 200, s + ' should be accepted');
    }
  });
  await check('states OUTSIDE the seeded four are accepted too -- the field is not hard-limited to the rules engine', async () => {
    for (const s of ['CA', 'TX', 'FL', 'DC', 'AK', 'WY']) {
      const res = await call('owner', 'EMP-OWN', 'write', Object.assign({}, FULL_PROFILE, { licensing_state: s }));
      assertEq(res.statusCode, 200, s + ' should be accepted');
    }
  });

  // ---- multi-facility keying (the CCRC reason this is not keyed by license_hash alone) ----
  await check('a SECOND facility under the same license is a separate row, not an overwrite', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', {
      id: 'FAC-SNF', name: 'Pinnacle Skilled Nursing', licensing_state: 'OH',
      license_number: 'SNF-OH-44821', roomboard_rate: 5200, snf_rate: 4100
    });
    assertEq(res.statusCode, 200);
    const all = await call('owner', 'EMP-OWN', 'read', null);
    assertEq(all.body.data.length, 2, 'both facilities should exist');
    const def = all.body.data.find((f) => f.id === 'FAC-DEFAULT');
    const snf = all.body.data.find((f) => f.id === 'FAC-SNF');
    assertEq(def.license_number, 'ALF-OH-11923', 'FAC-DEFAULT must be untouched by the FAC-SNF write');
    assertEq(snf.license_number, 'SNF-OH-44821');
  });
  await check('re-saving the SAME facility_id upserts in place, not a duplicate row', async () => {
    await call('owner', 'EMP-OWN', 'write', { id: 'FAC-SNF', name: 'Pinnacle Skilled Nursing (renamed)', licensing_state: 'OH' });
    const all = await call('owner', 'EMP-OWN', 'read', null);
    assertEq(all.body.data.length, 2, 'still exactly two facilities');
    assertEq(all.body.data.find((f) => f.id === 'FAC-SNF').name, 'Pinnacle Skilled Nursing (renamed)');
  });

  await check('missing id is 400', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', { name: 'x' });
    assertEq(res.statusCode, 400);
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
