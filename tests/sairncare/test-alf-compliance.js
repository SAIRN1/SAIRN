// Isolated test of the alf_compliance_rules / alf_staff_credentials handler
// branches in api/sd-data.js (Phase 2). Runs the REAL handler with mocked
// auth/license/fetch. The evaluation MATH is covered separately in
// test-compliance-rules.js against the pure engine; this file covers the gate,
// validation, persistence, and the wiring between them.
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

const seed = require(path.join(ROOT, 'sql/sairncare_compliance_seed.json'));
function seedRow(id) {
  const r = seed.rules.find((x) => x.rule_id === id);
  if (!r) throw new Error('no seed rule ' + id);
  return {
    rule_id: r.rule_id, state: r.state, requirement_type: r.requirement_type,
    facility_class: r.facility_class, effective_from: r.effective_from,
    effective_to: r.effective_to, status: r.status || 'active', data: r.data
  };
}
let RULES = [];
let CREDS = [];

global.fetch = async (url, opts) => {
  opts = opts || {};
  const method = opts.method || 'GET';
  if (method === 'GET' && /alf_compliance_rules\?license_hash=eq\.[^&]+&select=rule_id/.test(url)) {
    return { ok: true, status: 200, json: async () => RULES.slice() };
  }
  if (method === 'POST' && /alf_compliance_rules\?on_conflict=/.test(url)) {
    const body = JSON.parse(opts.body);
    const i = RULES.findIndex((x) => x.rule_id === body.rule_id);
    if (i === -1) RULES.push(body); else RULES[i] = body;
    return { ok: true, status: 200, json: async () => [body] };
  }
  const dup = url.match(/alf_staff_credentials\?license_hash=eq\.[^&]+&entry_id=eq\.([^&]+)&select=id/);
  if (method === 'GET' && dup) {
    const id = decodeURIComponent(dup[1]);
    const f = CREDS.filter((c) => c.entry_id === id);
    return { ok: true, status: 200, json: async () => (f.length ? [{ id: '1' }] : []) };
  }
  if (method === 'GET' && /alf_staff_credentials\?license_hash=eq\.[^&]+&select=entry_id/.test(url)) {
    return { ok: true, status: 200, json: async () => CREDS.slice() };
  }
  if (method === 'POST' && /\/rest\/v1\/alf_staff_credentials$/.test(url)) {
    const body = JSON.parse(opts.body);
    CREDS.push(body);
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
async function check(name, fn) {
  try { await fn(); pass++; console.log('PASS ' + name); }
  catch (e) { fail++; console.log('FAIL ' + name + ' -- ' + e.message); }
}
function assertEq(a, b, m) {
  if (JSON.stringify(a) !== JSON.stringify(b)) {
    throw new Error((m || 'mismatch') + ': expected ' + JSON.stringify(b) + ' got ' + JSON.stringify(a));
  }
}
function assertTrue(v, m) { if (!v) throw new Error(m || 'expected truthy'); }

(async () => {
  // ---- rule write gate ----
  await check('nursing cannot write a compliance rule (403)', async () => {
    const res = await call('nursing', 'EMP-NUR', 'write', 'alf_compliance_rules', seedRow('OH-STAFFING-MEMCARE-2024'));
    assertEq(res.statusCode, 403);
    assertEq(RULES.length, 0);
  });

  await check('a rule with no resolvable authority URL is refused (400), not stored', async () => {
    const bad = seedRow('OH-STAFFING-MEMCARE-2024');
    bad.data = Object.assign({}, bad.data, { authority: { citation: 'someone told me' } });
    const res = await call('owner', 'EMP-OWN', 'write', 'alf_compliance_rules', bad);
    assertEq(res.statusCode, 400);
    assertEq(res.body.error.code, 'NO_AUTHORITY');
    assertEq(RULES.length, 0);
  });

  await check('an unknown requirement_type is refused (400)', async () => {
    const bad = seedRow('OH-STAFFING-MEMCARE-2024');
    bad.requirement_type = 'square_footage';
    const res = await call('owner', 'EMP-OWN', 'write', 'alf_compliance_rules', bad);
    assertEq(res.statusCode, 400);
  });

  await check('a bogus state code is refused (400)', async () => {
    const bad = seedRow('OH-STAFFING-MEMCARE-2024');
    bad.state = 'ZZ';
    const res = await call('owner', 'EMP-OWN', 'write', 'alf_compliance_rules', bad);
    assertEq(res.statusCode, 400);
    assertEq(res.body.error.code, 'BAD_STATE');
  });

  await check('management can load the whole real seed (all 13 rules)', async () => {
    for (const r of seed.rules) {
      const res = await call('owner', 'EMP-OWN', 'write', 'alf_compliance_rules', seedRow(r.rule_id));
      assertEq(res.statusCode, 200, r.rule_id + ' should have stored');
    }
    assertEq(RULES.length, seed.rules.length);
  });

  await check('verified_by is server-stamped, not trusted from the client', async () => {
    const forged = seedRow('IN-TRAINING-2026');
    forged.verified_by = 'SOMEONE-ELSE';
    await call('billing', 'EMP-BILL', 'write', 'alf_compliance_rules', forged);
    assertEq(RULES.find((r) => r.rule_id === 'IN-TRAINING-2026').verified_by, 'EMP-BILL');
  });

  // ---- read + coverage ----
  await check('any authenticated employee can read the rules', async () => {
    const res = await call('caregiver', 'CG-1', 'read', 'alf_compliance_rules', null);
    assertEq(res.statusCode, 200);
    assertEq(res.body.data.length, seed.rules.length);
  });

  await check('coverage reports all four seeded states complete, and an extra state uncovered', async () => {
    const res = await call('owner', 'EMP-OWN', 'read', 'alf_compliance_rules', { claimed_states: ['OH', 'IN', 'MI', 'PA', 'FL'] });
    assertEq(res.body.coverage.have, 4);
    assertEq(res.body.coverage.need, 5);
    assertEq(res.body.coverage.uncovered_states, ['FL']);
  });

  // ---- evaluate ----
  await check('evaluating an uncovered state fails closed and names it', async () => {
    const res = await call('owner', 'EMP-OWN', 'evaluate', 'alf_compliance_rules', {
      state: 'FL', requirement_type: 'staffing', census: 30
    });
    assertEq(res.body.ok, false);
    assertEq(res.body.error.code, 'NO_RULE_FOR_STATE');
    assertTrue(/FL/.test(res.body.error.message));
  });

  await check('evaluating PA for a PCH facility fails closed rather than applying ALR numbers', async () => {
    const res = await call('owner', 'EMP-OWN', 'evaluate', 'alf_compliance_rules', {
      state: 'PA', facility_class: 'pch', requirement_type: 'staffing',
      mobile_residents: 10, mobility_needs_residents: 2
    });
    assertEq(res.body.ok, false);
    assertEq(res.body.error.code, 'NO_RULE_FOR_CLASS');
  });

  await check('a real Michigan large-group evaluation runs through the handler', async () => {
    const res = await call('owner', 'EMP-OWN', 'evaluate', 'alf_compliance_rules', {
      state: 'MI', facility_class: 'afc_large_group', requirement_type: 'staffing',
      shift: 'waking', census: 20, direct_care_staff: 1
    });
    assertEq(res.body.ok, true);
    assertEq(res.body.required_staff, 2);
    assertEq(res.body.meets, false);
  });

  await check('a real Pennsylvania evaluation folds SCU residents into the mobility-needs rate', async () => {
    const res = await call('owner', 'EMP-OWN', 'evaluate', 'alf_compliance_rules', {
      state: 'PA', facility_class: 'alr', requirement_type: 'staffing',
      mobile_residents: 10, mobility_needs_residents: 4, scu_residents: 6
    });
    assertEq(res.body.required_service_hours_per_day, 30);
    assertEq(res.body.effective_mobility_needs_residents, 10);
  });

  await check('a licensure evaluation returns the model, not a pass/fail', async () => {
    const res = await call('nursing', 'EMP-NUR', 'evaluate', 'alf_compliance_rules', {
      state: 'MI', requirement_type: 'licensure'
    });
    assertEq(res.body.ok, true);
    assertEq(res.body.model, 'no_assisted_living_license');
  });

  await check('evaluate WRITES NOTHING -- checking compliance cannot create a record', async () => {
    const before = CREDS.length + RULES.length;
    await call('owner', 'EMP-OWN', 'evaluate', 'alf_compliance_rules', {
      state: 'OH', facility_class: 'rcf_memory_care', requirement_type: 'staffing',
      memory_care_only: true, benchmark_ratio_available: false, census: 20
    });
    assertEq(CREDS.length + RULES.length, before);
  });

  // ---- staff credentials ----
  await check('caregiver cannot write a credential record (403) -- no self-certification', async () => {
    const res = await call('caregiver', 'CG-1', 'write', 'alf_staff_credentials', {
      id: 'CRED-X', staff_id: 'CG-1', record_type: 'training_hours', hours: 99, category: 'dementia'
    });
    assertEq(res.statusCode, 403);
    assertEq(CREDS.length, 0);
  });

  await check('a training_hours record with no positive hours is refused (400)', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', 'alf_staff_credentials', {
      id: 'CRED-BAD', staff_id: 'S1', record_type: 'training_hours', hours: 0
    });
    assertEq(res.statusCode, 400);
    assertEq(CREDS.length, 0);
  });

  await check('an unknown record_type is refused (400)', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', 'alf_staff_credentials', {
      id: 'CRED-BAD2', staff_id: 'S1', record_type: 'vibes'
    });
    assertEq(res.statusCode, 400);
  });

  await check('management can record training hours, recorded_by is server-stamped', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', 'alf_staff_credentials', {
      id: 'CRED-1', staff_id: 'S1', record_type: 'training_hours', hours: 3, category: 'dementia', completed_on: '2026-03-01'
    });
    assertEq(res.statusCode, 200);
    assertEq(CREDS.length, 1);
    assertEq(CREDS[0].recorded_by, 'EMP-OWN');
    assertEq(CREDS[0].data.hours, 3);
  });

  await check('credential records are append-only -- reusing an id is 409, never an overwrite', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', 'alf_staff_credentials', {
      id: 'CRED-1', staff_id: 'S1', record_type: 'training_hours', hours: 99, category: 'TAMPERED'
    });
    assertEq(res.statusCode, 409);
    assertEq(CREDS.length, 1);
    assertEq(CREDS[0].data.hours, 3, 'the original record must be unchanged');
  });

  await check('an expiring credential (CPR) can be recorded alongside training hours in the same store', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', 'alf_staff_credentials', {
      id: 'CRED-2', staff_id: 'S1', record_type: 'credential', credential: 'CPR', expires_on: '2027-01-31'
    });
    assertEq(res.statusCode, 200);
    assertEq(CREDS.length, 2);
  });

  await check('management sees every staff member’s records', async () => {
    await call('owner', 'EMP-OWN', 'write', 'alf_staff_credentials', {
      id: 'CRED-3', staff_id: 'S2', record_type: 'training_hours', hours: 6, category: 'dementia'
    });
    const res = await call('owner', 'EMP-OWN', 'read', 'alf_staff_credentials', null);
    assertEq(res.body.data.length, 3);
    assertEq(res.body.scoped_to_self, false);
  });

  await check('nursing can read the roster’s records (they chase expiring certifications)', async () => {
    const res = await call('nursing', 'EMP-NUR', 'read', 'alf_staff_credentials', null);
    assertEq(res.body.data.length, 3);
    assertEq(res.body.scoped_to_self, false);
  });

  await check('a caregiver sees ONLY their own records, and is told the view is scoped', async () => {
    const res = await call('caregiver', 'S2', 'read', 'alf_staff_credentials', null);
    assertEq(res.statusCode, 200);
    assertEq(res.body.data.length, 1);
    assertEq(res.body.data[0].staff_id, 'S2');
    assertEq(res.body.scoped_to_self, true);
  });

  await check('a caregiver with no records of their own sees an empty list, not someone else’s', async () => {
    const res = await call('caregiver', 'NOBODY', 'read', 'alf_staff_credentials', null);
    assertEq(res.body.data.length, 0);
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
