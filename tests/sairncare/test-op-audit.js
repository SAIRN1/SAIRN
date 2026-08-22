// Isolated test of Phase 3 item 5: the operational-audit layer.
// Covers the PURE engine (api/_lib/op-audit.js) and the alf_op_audits handler
// branches in api/sd-data.js, run against the REAL modules.
'use strict';
const path = require('path');
const ROOT = path.join(__dirname, '..', '..');
const o = require(path.join(ROOT, 'api/_lib/op-audit.js'));

process.env.SUPABASE_URL = 'https://fake.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = ['fake', 'service', 'value'].join('-');

const licenseMod = require(path.join(ROOT, 'api/_lib/license.js'));
licenseMod.validateLicenseKey = async () => ({ valid: true, active: true, license_hash: 'HASH1' });
const authMod = require(path.join(ROOT, 'api/_lib/auth.js'));
authMod.tokenFromRequest = (req) => req.headers['x-test-token'] || null;
authMod.verifySessionToken = (token, licHash, expectedApp) => {
  if (!token) return null;
  if (expectedApp !== 'sairncare') throw new Error('bad app scope: ' + expectedApp);
  return JSON.parse(token);
};

let AUDITS = [];
let FACILITY = [{ data: {} }];

global.fetch = async (url, opts) => {
  opts = opts || {};
  const method = (opts.method || 'GET').toUpperCase();
  const one = url.match(/alf_op_audits\?license_hash=eq\.[^&]+&entry_id=eq\.([^&]+)&select=entry_id/);
  if (method === 'GET' && one) {
    const id = decodeURIComponent(one[1]);
    return { ok: true, status: 200, json: async () => AUDITS.filter((a) => a.entry_id === id) };
  }
  if (method === 'GET' && /alf_op_audits\?license_hash=eq\.[^&]+&select=entry_id/.test(url)) {
    return { ok: true, status: 200, json: async () => AUDITS.slice() };
  }
  if (method === 'GET' && /alf_facility\?license_hash=eq\.[^&]+&select=data/.test(url)) {
    return { ok: true, status: 200, json: async () => FACILITY.slice() };
  }
  if (method === 'POST' && /alf_op_audits\?on_conflict=/.test(url)) {
    const body = JSON.parse(opts.body);
    const i = AUDITS.findIndex((a) => a.entry_id === body.entry_id);
    if (i === -1) AUDITS.push(body); else AUDITS[i] = body;
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
  const res = fakeRes();
  await handler({
    method: 'POST',
    headers: { authorization: 'Bearer k', 'x-test-token': JSON.stringify({ role: role, employee_id: employeeId }) },
    body: { action: action, resource: 'alf_op_audits', payload: payload }
  }, res);
  return res;
}

let pass = 0, fail = 0;
async function check(n, f) { try { await f(); pass++; console.log('PASS ' + n); } catch (e) { fail++; console.log('FAIL ' + n + ' -- ' + e.message); } }
function assertEq(a, b, m) { if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error((m || 'mismatch') + ': expected ' + JSON.stringify(b) + ' got ' + JSON.stringify(a)); }
function assertTrue(v, m) { if (!v) throw new Error(m || 'expected truthy'); }

(async () => {
  // ── engine: food temperature ─────────────────────────────────────────
  await check('cold holding passes at 41F and fails at 42F -- the boundary is exact', () => {
    assertEq(o.evaluateFoodTemp({ holding_kind: 'cold', temperature_f: 41 }).passed, true);
    assertEq(o.evaluateFoodTemp({ holding_kind: 'cold', temperature_f: 42 }).passed, false);
  });

  await check('hot holding passes at 135F and fails at 134F', () => {
    assertEq(o.evaluateFoodTemp({ holding_kind: 'hot', temperature_f: 135 }).passed, true);
    assertEq(o.evaluateFoodTemp({ holding_kind: 'hot', temperature_f: 134 }).passed, false);
  });

  await check('the ROAST exception is a real separate threshold, not the same as hot holding', () => {
    assertEq(o.evaluateFoodTemp({ holding_kind: 'hot', temperature_f: 132 }).passed, false);
    assertEq(o.evaluateFoodTemp({ holding_kind: 'roast_hot', temperature_f: 132 }).passed, true);
  });

  await check('the danger zone is reported for a reading between the two limits', () => {
    assertEq(o.evaluateFoodTemp({ holding_kind: 'cold', temperature_f: 50 }).in_danger_zone, true);
    assertEq(o.evaluateFoodTemp({ holding_kind: 'cold', temperature_f: 38 }).in_danger_zone, false);
    assertEq(o.evaluateFoodTemp({ holding_kind: 'hot', temperature_f: 160 }).in_danger_zone, false);
  });

  await check('every result declares whether it used the MODEL default or a facility override', () => {
    const model = o.evaluateFoodTemp({ holding_kind: 'cold', temperature_f: 40 });
    assertEq(model.threshold_source, 'fda_model_default');
    assertTrue(/model adopted state by state|state by state/i.test(model.source_note + model.authority.citation),
      'a model-default result must say the Food Code is adopted state by state');
    const over = o.evaluateFoodTemp({ holding_kind: 'cold', temperature_f: 40, thresholds: { cold_max_f: 38 } });
    assertEq(over.threshold_source, 'facility_configured');
    assertEq(over.passed, false, '40F fails a stricter 38F facility threshold');
  });

  await check('a non-numeric temperature and a bad holding kind are refused', () => {
    assertEq(o.evaluateFoodTemp({ holding_kind: 'cold', temperature_f: 'chilly' }).error.code, 'BAD_TEMPERATURE');
    assertEq(o.evaluateFoodTemp({ holding_kind: 'lukewarm', temperature_f: 40 }).error.code, 'BAD_HOLDING_KIND');
  });

  // ── engine: cooling ──────────────────────────────────────────────────
  await check('two-stage cooling passes within 2h then 4h and fails outside either', () => {
    assertEq(o.evaluateCooling({ stage1_hours: 2, stage2_hours: 4 }).passed, true);
    assertEq(o.evaluateCooling({ stage1_hours: 2.5, stage2_hours: 4 }).passed, false);
    assertEq(o.evaluateCooling({ stage1_hours: 1, stage2_hours: 5 }).passed, false);
  });

  await check('a one-stage record is not claimed as a complete cooling record', () => {
    const r = o.evaluateCooling({ stage1_hours: 1 });
    assertEq(r.complete, false);
    assertTrue(/not a complete two-stage/.test(r.note));
  });

  // ── engine: drills ───────────────────────────────────────────────────
  await check('drill checking REFUSES without a facility interval rather than inventing one', () => {
    const r = o.evaluateDrillDue({ today: '2026-08-22' });
    assertEq(r.error.code, 'NO_INTERVAL_POLICY');
    assertTrue(/will not assume one/i.test(r.error.message));
  });

  await check('a drill never recorded is due, and says that is absence of evidence not failure', () => {
    const r = o.evaluateDrillDue({ today: '2026-08-22', required_interval_days: 90 });
    assertEq(r.ever_completed, false);
    assertEq(r.due, true);
    assertTrue(/absence of evidence/i.test(r.note));
  });

  await check('drill overdue days are computed from the real last-completed date', () => {
    const r = o.evaluateDrillDue({ today: '2026-08-22', last_completed_on: '2026-05-01', required_interval_days: 90 });
    assertEq(r.days_since, 113);
    assertEq(r.due, true);
    assertEq(r.overdue_days, 23);
  });

  await check('a recent drill is not due and is not overdue', () => {
    const r = o.evaluateDrillDue({ today: '2026-08-22', last_completed_on: '2026-08-01', required_interval_days: 90 });
    assertEq(r.due, false);
    assertEq(r.overdue_days, 0);
  });

  // ── handler: the inverted gate ───────────────────────────────────────
  await check('ANY authenticated employee can record -- housekeeping is not locked out', async () => {
    for (const role of ['caregiver', 'activities', 'med_aide', 'nursing', 'billing', 'owner']) {
      const res = await call(role, 'E-' + role, 'write', {
        id: 'OPA-' + role, record_type: 'sanitation', subject: 'Kitchen deep clean', passed: true
      });
      assertEq(res.statusCode, 200, role + ' should be able to record');
    }
    assertEq(AUDITS.length, 6);
  });

  await check('recorded_by is server-stamped, not trusted from the client', async () => {
    const res = await call('caregiver', 'CG-REAL', 'write', {
      id: 'OPA-STAMP', record_type: 'sanitation', subject: 'Linen room', passed: true, recorded_by: 'FORGED'
    });
    assertEq(res.statusCode, 200);
    assertEq(AUDITS.find((a) => a.entry_id === 'OPA-STAMP').recorded_by, 'CG-REAL');
  });

  await check('THE SERVER evaluates a food temperature -- a client cannot mark a bad reading as passing', async () => {
    const res = await call('caregiver', 'CG-1', 'write', {
      id: 'OPA-TEMP-BAD', record_type: 'food_temp', holding_kind: 'cold', temperature_f: 55,
      location: 'Walk-in 1', passed: true
    });
    assertEq(res.statusCode, 200);
    const stored = AUDITS.find((a) => a.entry_id === 'OPA-TEMP-BAD');
    assertEq(stored.passed, false, 'the real threshold must win over the client-claimed pass');
    assertEq(stored.data.evaluation.in_danger_zone, true);
  });

  await check('a facility-configured threshold is applied by the server', async () => {
    FACILITY = [{ data: { food_thresholds: { cold_max_f: 38 } } }];
    const res = await call('caregiver', 'CG-1', 'write', {
      id: 'OPA-TEMP-OVER', record_type: 'food_temp', holding_kind: 'cold', temperature_f: 40, location: 'Walk-in 2'
    });
    assertEq(res.statusCode, 200);
    const stored = AUDITS.find((a) => a.entry_id === 'OPA-TEMP-OVER');
    assertEq(stored.passed, false, '40F fails the facility 38F threshold even though it passes the model 41F');
    assertEq(stored.data.evaluation.threshold_source, 'facility_configured');
    FACILITY = [{ data: {} }];
  });

  await check('an invalid record_type is refused (400)', async () => {
    const res = await call('owner', 'O1', 'write', { id: 'OPA-BAD', record_type: 'vibes_check' });
    assertEq(res.statusCode, 400);
  });

  await check('observations are APPEND-ONLY -- reusing an id is 409, not an overwrite', async () => {
    const res = await call('caregiver', 'CG-1', 'write', {
      id: 'OPA-TEMP-BAD', record_type: 'food_temp', holding_kind: 'cold', temperature_f: 35
    });
    assertEq(res.statusCode, 409);
    assertEq(AUDITS.find((a) => a.entry_id === 'OPA-TEMP-BAD').passed, false, 'original observation unchanged');
  });

  // ── handler: sign-off is the privileged act ──────────────────────────
  await check('a caregiver CANNOT sign off (403) -- recording and attesting are different acts', async () => {
    const res = await call('caregiver', 'CG-1', 'write', { id: 'OPA-TEMP-BAD', record_type: 'food_temp', reviewed: true });
    assertEq(res.statusCode, 403);
    assertEq(AUDITS.find((a) => a.entry_id === 'OPA-TEMP-BAD').reviewed_by, undefined);
  });

  await check('nursing cannot sign off either -- this is management, not clinical oversight', async () => {
    const res = await call('nursing', 'N1', 'write', { id: 'OPA-TEMP-BAD', record_type: 'food_temp', reviewed: true });
    assertEq(res.statusCode, 403);
  });

  await check('management CAN sign off, and the stamp is from the real session', async () => {
    const res = await call('owner', 'OWN-1', 'write', { id: 'OPA-TEMP-BAD', record_type: 'food_temp', reviewed: true });
    assertEq(res.statusCode, 200);
    const stored = AUDITS.find((a) => a.entry_id === 'OPA-TEMP-BAD');
    assertEq(stored.reviewed_by, 'OWN-1');
    assertTrue(!!stored.reviewed_at);
  });

  await check('A SIGN-OFF CANNOT REWRITE THE OBSERVATION IT SIGNS', async () => {
    await call('owner', 'OWN-1', 'write', {
      id: 'OPA-TEMP-OVER', record_type: 'food_temp', reviewed: true,
      temperature_f: 1, holding_kind: 'cold', passed: true, location: 'TAMPERED'
    });
    const stored = AUDITS.find((a) => a.entry_id === 'OPA-TEMP-OVER');
    assertEq(stored.passed, false, 'the signed observation must keep its original result');
    assertEq(stored.data.location, 'Walk-in 2', 'and its original detail');
    assertEq(stored.reviewed_by, 'OWN-1');
  });

  await check('signing off a record that does not exist is refused (404)', async () => {
    const res = await call('owner', 'OWN-1', 'write', { id: 'OPA-NOPE', record_type: 'sanitation', reviewed: true });
    assertEq(res.statusCode, 404);
  });

  // ── handler: read + summary ──────────────────────────────────────────
  await check('any authenticated employee can read the log, with a real summary', async () => {
    const res = await call('med_aide', 'MA-1', 'read', {});
    assertEq(res.statusCode, 200);
    assertEq(res.body.summary.total, AUDITS.length);
    assertTrue(res.body.summary.failed >= 2, 'the two out-of-tolerance temperatures must be counted');
    assertTrue(res.body.summary.by_type.food_temp.total >= 2);
  });

  await check('a client-claimed pass NEVER leaks back on READ -- the column wins over the blob', async () => {
    // Regression guard. The write path already refused to trust a client `passed`, but the
    // read path originally spread the jsonb blob AFTER the authoritative columns, so the
    // tampered value came straight back out and the summary under-counted the failure.
    // Tamper protection that only holds on the way in is not tamper protection.
    const res = await call('owner', 'O1', 'read', {});
    const rec = res.body.data.find((d) => d.id === 'OPA-TEMP-BAD');
    assertEq(rec.passed, false, '55F cold holding must read back as failed regardless of what was submitted');
    assertEq(rec.recorded_by, 'CG-1', 'server-stamped fields must also survive the round trip');
  });

  await check('the summary counts unreviewed records so sign-off gaps are visible', async () => {
    const res = await call('owner', 'O1', 'read', {});
    const unreviewed = AUDITS.filter((a) => !a.reviewed_by).length;
    assertEq(res.body.summary.unreviewed, unreviewed);
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
