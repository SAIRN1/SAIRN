// REQUIREMENT: every direct-care role CAN file an incident report and none of
//   them can READ the log -- mandatory reporting is by the witness, and a
//   witness who can read what others filed is a witness who can align their
//   account with them
//
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
  // ── AN ABSENT expectedApp IS LEGITIMATE; A WRONG ONE IS STILL FATAL ──
  // Threw on ANY expectedApp other than 'sairncare', INCLUDING `undefined`, which
  // is what made this suite red from c8b5e5b1: every arm answered 502 on the
  // stub's own throw. api/_lib/auth.js:604 is `if (expectedApp && payload.app
  // !== expectedApp) return null;` -- the argument is OPTIONAL -- and
  // api/sd-data.js:1387's active-credential pre-gate omits it deliberately,
  // so the refusal modelled here could never happen in production.
  // The guard is KEPT: a branch gate that set the WRONG app is still fatal.
  // Full account: the commit that fixed test-alf-mar.js and the register
  // record against it.
  if (expectedApp === undefined) return JSON.parse(token);
  if (expectedApp !== 'sairncare') throw new Error('expected app scope not sairncare: ' + expectedApp);
  return JSON.parse(token);
};

let INCIDENT_ROWS = []; // {entry_id, resident_id, data}

global.fetch = async (url, opts) => {
  opts = opts || {};
  const method = opts.method || 'GET';
  if (method === 'GET' && /alf_incidents\?license_hash=eq\.[^&]+&select=entry_id,resident_id,data/.test(url)) {
    // ── THE SELF-SCOPE eq-CLAUSE IS APPLIED, AND IT WAS NOT BEFORE ──────────
    // The read gained `&recorded_by=eq.<session.employee_id>` for non-broad
    // roles on 2026-09-27 (api/sd-data.js:10785). This mock ignored it and
    // returned every row to every caller, so the self-scope -- the only thing
    // standing between a caregiver and the whole facility's incident log --
    // had no arm on it at all. Honouring the clause is what lets the two arms
    // below mean something.
    //
    // `recorded_by` IS CARRIED ON THE ROW because the real select asks for it
    // and because it is SERVER-SET from the verified session on insert
    // (:10888) and never re-stamped on update. A fixture that stored it from
    // the payload would be modelling the forgery the write path strips.
    const m = url.match(/recorded_by=eq\.([^&]*)/);
    const only = m ? decodeURIComponent(m[1]) : null;
    const rows = INCIDENT_ROWS
      .filter((r) => only === null || (r.recorded_by || '') === only)
      .map((r) => ({ entry_id: r.entry_id, resident_id: r.resident_id, data: r.data, created_at: r.created_at || '2026-10-05T00:00:00Z', recorded_by: r.recorded_by || '' }));
    return { ok: true, status: 200, json: async () => rows };
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
    // `recorded_by` is taken from the POST BODY, which is where the handler put
    // it from the verified session -- and only on insert, never on update,
    // which is why the existing value is preserved on the update arm.
    const row = { entry_id: body.entry_id, resident_id: body.resident_id, data: body.data,
                  recorded_by: idx === -1 ? (body.recorded_by || '') : (INCIDENT_ROWS[idx].recorded_by || '') };
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

  // ── THESE THREE ARMS ASSERTED A FLAT 403 AND THE GATE DELIBERATELY STOPPED
  // ── ANSWERING ONE ON 2026-09-27 (arms rewritten 2026-10-05) ───────────────
  // api/sd-data.js:10739 records the change and the reason in its own words: a
  // caregiver could file a mandated report and then not see it, and "ending
  // write access is accountability; ending read access is just opacity." So a
  // care role now gets 200 with the log SELF-SCOPED on `recorded_by`.
  //
  // THE ARMS ARE REWRITTEN TO THE REAL CONTRACT RATHER THAN DELETED, and that
  // is strictly stronger than what they asserted. A flat 403 is a single bit;
  // the risk that actually exists now is a self-scope that LEAKS -- a care role
  // reading somebody else's incident report -- and no arm anywhere was testing
  // that, because this suite's own mock ignored the eq-clause until today.
  //
  // `recorded_by` IS SERVER-SET FROM THE VERIFIED SESSION and the write path
  // strips a payload copy, so "mine" cannot be claimed. The gate's comment
  // names the alternative it refused: filtering on the caller-supplied
  // `data.reported_by` "would let any employee read any incident by claiming to
  // have filed it, which is worse than the flat 403 this replaces."
  await check('caregiver CAN read the incident log and sees ONLY their own filings', async () => {
    const res = await call('caregiver', 'CG-1', 'read', null);
    assertEq(res.statusCode, 200);
    const ids = (res.body.data || []).map((x) => x.id !== undefined ? x.id : x.entry_id);
    // Every row returned was filed by this caller. Asserted over the whole
    // result rather than by counting, so a leak of one row fails it.
    assertEq(ids.every((id) => INCIDENT_ROWS.find((r) => r.entry_id === id).recorded_by === 'CG-1'), true);
  });
  await check('a care role does NOT see an incident filed by somebody else -- the self-scope is the control, and it is a NEGATIVE arm', async () => {
    // Seeded directly: a report filed by a DIFFERENT caregiver. If the
    // eq-clause is ever dropped from the query, or this suite's mock stops
    // applying it, this arm is the one that goes red.
    INCIDENT_ROWS.push({ entry_id: 'INC-OTHER', resident_id: 'RES-1',
                         data: { category: 'fall', note: 'filed by CG-2' },
                         recorded_by: 'CG-2' });
    const res = await call('caregiver', 'CG-1', 'read', null);
    assertEq(res.statusCode, 200);
    const ids = (res.body.data || []).map((x) => x.id !== undefined ? x.id : x.entry_id);
    assertEq(ids.indexOf('INC-OTHER') === -1, true);
    // CONTROL: management DOES see it, so the arm above is proving a scope and
    // not merely that the row is unreachable or the fixture is empty.
    const mgmt = await call('owner', 'EMP-OWN', 'read', null);
    const mgmtIds = (mgmt.body.data || []).map((x) => x.id !== undefined ? x.id : x.entry_id);
    assertEq(mgmtIds.indexOf('INC-OTHER') !== -1, true);
    INCIDENT_ROWS = INCIDENT_ROWS.filter((r) => r.entry_id !== 'INC-OTHER');
  });
  await check('med_aide and activities also read self-scoped, not 403', async () => {
    // ASSERTS THE PROPERTY, NOT A COUNT, and the first draft of this arm got
    // that wrong: it expected an empty log for both, and med_aide saw one row
    // because an earlier arm in this file has MA-1 FILE a report. A count is a
    // fact about the fixture's history; "every row I can see is mine" is the
    // contract, and it holds however many rows exist.
    for (const [role, emp] of [['med_aide', 'MA-1'], ['activities', 'EMP-ACT']]) {
      const res = await call(role, emp, 'read', null);
      assertEq(res.statusCode, 200);
      const ids = (res.body.data || []).map((x) => x.id !== undefined ? x.id : x.entry_id);
      assertEq(ids.every((id) => INCIDENT_ROWS.find((r) => r.entry_id === id).recorded_by === emp), true);
    }
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
