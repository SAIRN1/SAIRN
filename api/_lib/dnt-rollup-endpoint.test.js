// api/_lib/dnt-rollup-endpoint.test.js
//
// Run: node api/_lib/dnt-rollup-endpoint.test.js
//
// The ENDPOINT half of SAIRNdental B2. dnt-rollup.test.js proves the
// arithmetic; this proves the gate, the fan-out and -- the part worth having --
// that a table PostgREST cannot serve arrives at the client as a NULL METRIC
// and not as a zero.
//
// It drives the real api/sd-data.js handler with a mocked auth/license/fetch
// layer, the same shape tests/sairncare/* use. Nothing here reimplements the
// handler; a test that reimplements the thing it tests agrees with itself.
'use strict';
const path = require('path');
const ROOT = path.join(__dirname, '..', '..');

process.env.SUPABASE_URL = 'https://fake.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'fake-service-key';

const licenseMod = require(path.join(ROOT, 'api/_lib/license.js'));
licenseMod.validateLicenseKey = async () => ({
  valid: true, active: true, license_hash: 'HASH1', app_id: 'sairndental',
  stripe_subscription_id: 'sub_1', trial_ends_at: null
});

const authMod = require(path.join(ROOT, 'api/_lib/auth.js'));
authMod.tokenFromRequest = (req) => req.headers['x-test-token'] || null;
authMod.verifySessionToken = (token, licHash, expectedApp) => {
  if (!token) return null;
  if (expectedApp !== 'sairndental') {
    throw new Error('expected app scope not sairndental: ' + expectedApp);
  }
  return JSON.parse(token);
};

// Fixture state, rewritten per arm.
let SETTINGS = [{ data: { locations: [{ id: 'LOC-N', name: 'North' },
                                      { id: 'LOC-S', name: 'South' }] } }];
let PATIENTS = [{ data: { id: 'P1', location_id: 'LOC-N' } },
                { data: { id: 'P2', location_id: 'LOC-S' } }];
let CHARGES = [{ data: { id: 'C1', location_id: 'LOC-N', amount: 200 } }];
let APPTS = [{ data: { id: 'A1', location_id: 'LOC-S' } }];
// Tables the fake PostgREST should answer 404 for, i.e. not migrated.
let MISSING = {};

global.fetch = async (url) => {
  const table = (url.match(/rest\/v1\/([a-z_]+)\?/) || [])[1];
  if (MISSING[table]) return { ok: false, status: 404, json: async () => ({}) };
  const body = { dnt_settings: SETTINGS, dnt_patients: PATIENTS,
                 dnt_charges: CHARGES, dnt_appointments: APPTS }[table];
  if (body === undefined) throw new Error('Unmocked fetch: ' + url);
  return { ok: true, status: 200, json: async () => body };
};

delete require.cache[require.resolve(path.join(ROOT, 'api/sd-data.js'))];
const handler = require(path.join(ROOT, 'api/sd-data.js'));

function fakeRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}
async function call(role) {
  const req = {
    method: 'POST',
    headers: { authorization: 'Bearer testkey',
               'x-test-token': role ? JSON.stringify({ role, employee_id: 'E1' }) : undefined },
    body: { action: 'read', resource: 'dnt_rollup', payload: null }
  };
  const res = fakeRes();
  await handler(req, res);
  return res;
}

let pass = 0, fail = 0;
async function check(name, fn) {
  MISSING = {};
  try { await fn(); pass++; console.log('PASS ' + name); }
  catch (e) { fail++; console.log('FAIL ' + name + ' -- ' + e.message); }
}
function eq(a, b, m) {
  if (JSON.stringify(a) !== JSON.stringify(b)) {
    throw new Error((m || 'mismatch') + ': expected ' + JSON.stringify(b) +
                    ' got ' + JSON.stringify(a));
  }
}
function office(body, id) {
  return body.data.locations.filter((l) => l.location_id === id)[0];
}

(async () => {
  // ── THE GATE ─────────────────────────────────────────────────────────────
  await check('no session is 401, not an empty report', async () => {
    const res = await call(null);
    eq(res.statusCode, 401);
  });
  await check('frontdesk CANNOT read the cross-location roll-up', async () => {
    const res = await call('frontdesk');
    eq(res.statusCode, 403);
    eq(res.body.error.code, 'FORBIDDEN');
  });
  await check('provider CANNOT read it either', async () => {
    const res = await call('provider');
    eq(res.statusCode, 403);
  });
  await check('owner CAN', async () => {
    const res = await call('owner');
    eq(res.statusCode, 200);
  });

  // ── THE NUMBERS ──────────────────────────────────────────────────────────
  await check('per-office figures are what the rows say', async () => {
    const res = await call('owner');
    eq(office(res.body, 'LOC-N').metrics.patients.value, 1);
    eq(office(res.body, 'LOC-N').metrics.production.value, 200);
    eq(office(res.body, 'LOC-S').metrics.appointments.value, 1);
    eq(office(res.body, 'LOC-S').metrics.production.value, 0,
       'South really did produce nothing here -- 0 is a measurement');
  });
  await check('office names come from the registry', async () => {
    const res = await call('owner');
    eq(office(res.body, 'LOC-N').name, 'North');
    eq(office(res.body, 'LOC-N').registered, true);
  });
  await check('a complete read says so', async () => {
    const res = await call('owner');
    eq(res.body.data.disclosure.complete, true);
  });

  // ── THE PART THIS FILE EXISTS FOR ────────────────────────────────────────
  await check('an UNMIGRATED charges table gives NULL production, never 0',
    async () => {
      MISSING = { dnt_charges: true };
      const res = await call('owner');
      eq(res.statusCode, 200);
      eq(office(res.body, 'LOC-N').metrics.production.value, null,
         '0 here would read as "this office produced nothing"');
      eq(res.body.data.totals.production.value, null);
      eq(res.body.data.disclosure.unreadable.dnt_charges, 'NOT_PROVISIONED');
      eq(res.body.data.disclosure.complete, false);
    });
  await check('...and the metrics that COULD be read still report', async () => {
    MISSING = { dnt_charges: true };
    const res = await call('owner');
    eq(office(res.body, 'LOC-N').metrics.patients.value, 1,
       'suppression is per-resource, not all-or-nothing');
  });
  await check('an unmigrated SETTINGS table refuses the whole report (503)',
    async () => {
      // Not a smaller answer: with no registry every office reports as
      // unregistered and unnamed, which is a different report wearing the same
      // shape.
      MISSING = { dnt_settings: true };
      const res = await call('owner');
      eq(res.statusCode, 503);
      eq(res.body.error.code, 'NOT_PROVISIONED');
    });

  // ── PRE-STAMP ROWS ───────────────────────────────────────────────────────
  await check('a row written before location stamping lands in UNASSIGNED',
    async () => {
      PATIENTS = [{ data: { id: 'P1', location_id: 'LOC-N' } },
                  { data: { id: 'P0' } }];
      const res = await call('owner');
      eq(res.body.data.unassigned.metrics.patients.value, 1);
      eq(res.body.data.totals.patients.value, 2,
         'it is still in the total -- unattributed, not lost');
      eq(res.body.data.disclosure.complete, false);
      PATIENTS = [{ data: { id: 'P1', location_id: 'LOC-N' } },
                  { data: { id: 'P2', location_id: 'LOC-S' } }];
    });

  // ── NO PATIENT DATA LEAVES THE BRANCH ────────────────────────────────────
  await check('the response carries NO row-level patient data', async () => {
    const res = await call('owner');
    // ASSERT THE CALL SUCCEEDED FIRST. This arm passed VACUOUSLY on the first
    // run: the whole suite was 400-ing on an unregistered resource, and
    // "the body does not contain P1" is trivially true of an error body. An
    // absence assertion with no positive precondition is the cheapest way to
    // write a test that can never fail.
    eq(res.statusCode, 200, 'a 200 is the precondition for this arm meaning anything');
    const blob = JSON.stringify(res.body);
    eq(blob.indexOf('P1'), -1,
       'a roll-up that ships rows is a patient export wearing a report name');
    eq(blob.indexOf('C1'), -1);
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
