// Isolated test of the Phase 3 server paths in api/sd-data.js:
//   - the pharmacy-order review gate on alf_mar (item 1)
//   - derive_charges on alf_billing (item 2)
// Runs the REAL handler with mocked auth/license/fetch.
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

// Fixture state
let MAR = [
  { entry_id: 'RXIN-9001', resident_id: 'RES-1', entry_type: 'medication_order',
    data: { name: 'Metformin', source: 'pharmacy', pharmacy_status: 'pending_review', schedule_times: ['08:00'] } },
  { entry_id: 'ADM-1', resident_id: 'RES-1', entry_type: 'administration',
    data: { medication_id: 'RXIN-9001', administered_at: '2026-08-03T08:05:00Z', status: 'given', medication_name: 'Metformin' } },
  { entry_id: 'ADM-2', resident_id: 'RES-1', entry_type: 'administration',
    data: { medication_id: 'RXIN-9001', administered_at: '2026-08-04T08:05:00Z', status: 'refused', medication_name: 'Metformin' } }
];
let CLIENTS = { 'RES-1': { assigned_employee_id: null, data: { name: 'Eleanor', adl_assessments: [{ id: 'ADL-1', date: '2026-08-10' }] } } };
let ACTIVITIES = [{ entry_id: 'ACT-1', data: { name: 'Music therapy', date: '2026-08-12', attendees: ['RES-1'] } }];
let FACILITY = [{ data: { med_admin_rate: 2.5, activity_rate: 10 } }];
let BILLING = [];

global.fetch = async (url, opts) => {
  opts = opts || {};
  const method = opts.method || 'GET';
  if (method === 'GET' && /alf_mar\?license_hash=eq\.[^&]+&resident_id=eq\.([^&]+)&select=entry_id,entry_type,data/.test(url)) {
    const rid = decodeURIComponent(url.match(/resident_id=eq\.([^&]+)/)[1]);
    return { ok: true, status: 200, json: async () => MAR.filter((m) => m.resident_id === rid) };
  }
  const marDup = url.match(/alf_mar\?license_hash=eq\.[^&]+&entry_id=eq\.([^&]+)&select=id/);
  if (method === 'GET' && marDup) {
    const id = decodeURIComponent(marDup[1]);
    return { ok: true, status: 200, json: async () => (MAR.some((m) => m.entry_id === id) ? [{ id: '1' }] : []) };
  }
  const cliOne = url.match(/alf_clients\?license_hash=eq\.[^&]+&client_id=eq\.([^&]+)&select=assigned_employee_id/);
  if (method === 'GET' && cliOne) {
    const id = decodeURIComponent(cliOne[1]);
    return { ok: true, status: 200, json: async () => (CLIENTS[id] ? [{ assigned_employee_id: CLIENTS[id].assigned_employee_id }] : []) };
  }
  const cliData = url.match(/alf_clients\?license_hash=eq\.[^&]+&client_id=eq\.([^&]+)&select=data/);
  if (method === 'GET' && cliData) {
    const id = decodeURIComponent(cliData[1]);
    return { ok: true, status: 200, json: async () => (CLIENTS[id] ? [{ data: CLIENTS[id].data }] : []) };
  }
  if (method === 'GET' && /alf_activities\?license_hash=eq\.[^&]+&select=entry_id,data/.test(url)) {
    return { ok: true, status: 200, json: async () => ACTIVITIES.slice() };
  }
  if (method === 'GET' && /alf_facility\?license_hash=eq\.[^&]+&select=data/.test(url)) {
    return { ok: true, status: 200, json: async () => FACILITY.slice() };
  }
  const billOne = url.match(/alf_billing\?license_hash=eq\.[^&]+&entry_id=eq\.([^&]+)&select=data/);
  if (method === 'GET' && billOne) {
    const id = decodeURIComponent(billOne[1]);
    return { ok: true, status: 200, json: async () => BILLING.filter((b) => b.entry_id === id) };
  }
  if (method === 'POST' && /alf_mar\?on_conflict=/.test(url)) {
    const body = JSON.parse(opts.body);
    const i = MAR.findIndex((m) => m.entry_id === body.entry_id);
    if (i === -1) MAR.push(body); else MAR[i] = Object.assign({}, MAR[i], body);
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
async function call(role, employeeId, action, resource, payload) {
  const req = {
    method: 'POST',
    headers: { authorization: 'Bearer testkey', 'x-test-token': JSON.stringify({ role, employee_id: employeeId }) },
    body: { action, resource, payload }
  };
  const res = fakeRes();
  await handler(req, res);
  return res;
}

let pass = 0, fail = 0;
async function check(n, f) { try { await f(); pass++; console.log('PASS ' + n); } catch (e) { fail++; console.log('FAIL ' + n + ' -- ' + e.message); } }
function assertEq(a, b, m) {
  if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error((m || 'mismatch') + ': expected ' + JSON.stringify(b) + ' got ' + JSON.stringify(a));
}
function assertTrue(v, m) { if (!v) throw new Error(m || 'expected truthy'); }

function pharmOrder(extra) {
  return Object.assign({
    id: 'RXIN-9001', resident_id: 'RES-1', entry_type: 'medication_order',
    name: 'Metformin', source: 'pharmacy'
  }, extra || {});
}

(async () => {
  // ── item 1: pharmacy review gate ─────────────────────────────────────
  await check('med_aide CANNOT accept a pharmacy order -- clearing an order into use is clinical', async () => {
    const res = await call('med_aide', 'MA-1', 'write', 'alf_mar', pharmOrder({ pharmacy_status: 'accepted' }));
    assertEq(res.statusCode, 403);
    assertEq(MAR.find((m) => m.entry_id === 'RXIN-9001').data.pharmacy_status, 'pending_review', 'must be unchanged');
  });

  await check('caregiver cannot touch the MAR at all (403 before the review gate)', async () => {
    const res = await call('caregiver', 'CG-1', 'write', 'alf_mar', pharmOrder({ pharmacy_status: 'accepted' }));
    assertEq(res.statusCode, 403);
  });

  await check('an invalid pharmacy_status is refused (400), not stored', async () => {
    const res = await call('nursing', 'EMP-NUR', 'write', 'alf_mar', pharmOrder({ pharmacy_status: 'looks_fine' }));
    assertEq(res.statusCode, 400);
  });

  await check('nursing CAN accept, and reviewed_by is server-stamped not client-supplied', async () => {
    const res = await call('nursing', 'EMP-NUR', 'write', 'alf_mar',
      pharmOrder({ pharmacy_status: 'accepted', reviewed_by: 'FORGED', reviewed_at: '2001-01-01T00:00:00Z' }));
    assertEq(res.statusCode, 200);
    const stored = MAR.find((m) => m.entry_id === 'RXIN-9001').data;
    assertEq(stored.pharmacy_status, 'accepted');
    assertEq(stored.reviewed_by, 'EMP-NUR', 'must be the real session, not the forged value');
    assertTrue(stored.reviewed_at !== '2001-01-01T00:00:00Z', 'reviewed_at must be server-stamped');
  });

  await check('nursing can reject, and that is also stamped', async () => {
    MAR.push({ entry_id: 'RXIN-9002', resident_id: 'RES-1', entry_type: 'medication_order',
      data: { name: 'Warfarin', source: 'pharmacy', pharmacy_status: 'pending_review' } });
    const res = await call('nursing', 'EMP-NUR', 'write', 'alf_mar',
      { id: 'RXIN-9002', resident_id: 'RES-1', entry_type: 'medication_order', name: 'Warfarin', pharmacy_status: 'rejected' });
    assertEq(res.statusCode, 200);
    assertEq(MAR.find((m) => m.entry_id === 'RXIN-9002').data.reviewed_by, 'EMP-NUR');
  });

  await check('an ordinary hand-entered order is unaffected by the review gate', async () => {
    const res = await call('nursing', 'EMP-NUR', 'write', 'alf_mar',
      { id: 'MED-HAND', resident_id: 'RES-1', entry_type: 'medication_order', name: 'Vitamin D' });
    assertEq(res.statusCode, 200);
    assertEq(MAR.find((m) => m.entry_id === 'MED-HAND').data.reviewed_by, undefined, 'no review stamp on a non-pharmacy order');
  });

  // ── item 2: derive_charges ───────────────────────────────────────────
  await check('nursing cannot derive charges (403) -- billing is management only', async () => {
    const res = await call('nursing', 'EMP-NUR', 'derive_charges', 'alf_billing', { resident_id: 'RES-1', month: '2026-08' });
    assertEq(res.statusCode, 403);
  });

  await check('derive_charges bills a GIVEN administration but not a REFUSED one', async () => {
    const res = await call('owner', 'EMP-OWN', 'derive_charges', 'alf_billing', { resident_id: 'RES-1', month: '2026-08' });
    assertEq(res.statusCode, 200);
    assertEq(res.body.ok, true);
    const medLines = res.body.lines.filter((l) => l.type === 'medication_administration');
    assertEq(medLines.length, 1, 'only ADM-1 (given) is billable; ADM-2 was refused');
    assertEq(medLines[0].event_id, 'ADM-1');
  });

  await check('every charge line carries the id of the document behind it', async () => {
    const res = await call('owner', 'EMP-OWN', 'derive_charges', 'alf_billing', { resident_id: 'RES-1', month: '2026-08' });
    res.body.lines.forEach((l) => assertTrue(!!l.event_id, 'line without a source document id'));
  });

  await check('an activity the resident attended becomes a charge', async () => {
    const res = await call('owner', 'EMP-OWN', 'derive_charges', 'alf_billing', { resident_id: 'RES-1', month: '2026-08' });
    const act = res.body.lines.find((l) => l.type === 'activity_attendance');
    assertEq(act.amount, 10);
    assertEq(act.event_id, 'ACT-1');
  });

  await check('a documented ADL assessment with NO configured rate is surfaced, not billed at zero', async () => {
    const res = await call('owner', 'EMP-OWN', 'derive_charges', 'alf_billing', { resident_id: 'RES-1', month: '2026-08' });
    const unp = res.body.unpriced.find((u) => u.type === 'adl_assessment');
    assertTrue(!!unp, 'the assessment must appear as unpriced');
    assertEq(res.body.lines.filter((l) => l.type === 'adl_assessment').length, 0, 'and must not appear as a zero-dollar line');
    assertEq(res.body.reconciliation.fully_reconciled, false, 'the gap must be reported');
  });

  await check('the reconciliation counts documented-vs-billed as real numbers', async () => {
    const res = await call('owner', 'EMP-OWN', 'derive_charges', 'alf_billing', { resident_id: 'RES-1', month: '2026-08' });
    const rc = res.body.reconciliation;
    assertEq(rc.documented_chargeable_events, 3, '1 given admin + 1 activity + 1 assessment');
    assertEq(rc.billed_events, 2);
    assertEq(rc.unbilled_events, 1);
  });

  await check('configuring the missing rate closes the gap without touching anything else', async () => {
    FACILITY = [{ data: { med_admin_rate: 2.5, activity_rate: 10, adl_assessment_rate: 40 } }];
    const res = await call('owner', 'EMP-OWN', 'derive_charges', 'alf_billing', { resident_id: 'RES-1', month: '2026-08' });
    assertEq(res.body.reconciliation.fully_reconciled, true);
    assertEq(res.body.total, 52.5, '2.50 + 10 + 40');
  });

  await check('another month returns nothing rather than leaking this month’s documentation', async () => {
    const res = await call('owner', 'EMP-OWN', 'derive_charges', 'alf_billing', { resident_id: 'RES-1', month: '2026-09' });
    assertEq(res.body.lines.length, 0);
    assertEq(res.body.total, 0);
  });

  await check('derive_charges WRITES NOTHING', async () => {
    const before = JSON.stringify(BILLING) + '|' + MAR.length;
    await call('owner', 'EMP-OWN', 'derive_charges', 'alf_billing', { resident_id: 'RES-1', month: '2026-08' });
    assertEq(JSON.stringify(BILLING) + '|' + MAR.length, before);
  });

  await check('missing resident_id or month is refused (400)', async () => {
    assertEq((await call('owner', 'EMP-OWN', 'derive_charges', 'alf_billing', { month: '2026-08' })).statusCode, 400);
    assertEq((await call('owner', 'EMP-OWN', 'derive_charges', 'alf_billing', { resident_id: 'RES-1' })).statusCode, 400);
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
