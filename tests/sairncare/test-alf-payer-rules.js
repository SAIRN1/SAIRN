// Isolated test of the alf_payer_rules / alf_claim_routes handler branches in
// api/sd-data.js (Phase 1 payer-routing engine). Runs the REAL handler with
// mocked auth/license/fetch -- not a reimplementation.
//
// The routing MATH is covered separately in test-payer-routing.js against the
// pure engine; this file covers the gate, validation, persistence and the
// wiring between them.
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

const seed = require(path.join(ROOT, 'sql/sairncare_payer_rules_seed.json'));
function seedRow(id) {
  const r = seed.rules.find((x) => x.rule_id === id);
  return {
    rule_id: r.rule_id, state: r.state, program: r.program,
    effective_from: r.effective_from, effective_to: r.effective_to,
    status: r.status || 'active', data: r.data, verified_by: 'EMP-OWN'
  };
}
let RULES = [];
let ROUTES = [];

global.fetch = async (url, opts) => {
  opts = opts || {};
  const method = opts.method || 'GET';
  if (method === 'GET' && /alf_payer_rules\?license_hash=eq\.[^&]+&select=rule_id/.test(url)) {
    return { ok: true, status: 200, json: async () => RULES.slice() };
  }
  if (method === 'POST' && /alf_payer_rules\?on_conflict=/.test(url)) {
    const body = JSON.parse(opts.body);
    const i = RULES.findIndex((x) => x.rule_id === body.rule_id);
    if (i === -1) RULES.push(body); else RULES[i] = body;
    return { ok: true, status: 200, json: async () => [body] };
  }
  const dupMatch = url.match(/alf_claim_routes\?license_hash=eq\.[^&]+&entry_id=eq\.([^&]+)&select=id/);
  if (method === 'GET' && dupMatch) {
    const id = decodeURIComponent(dupMatch[1]);
    const found = ROUTES.filter((r) => r.entry_id === id);
    return { ok: true, status: 200, json: async () => (found.length ? [{ id: '1' }] : []) };
  }
  if (method === 'GET' && /alf_claim_routes\?license_hash=eq\.[^&]+&select=entry_id/.test(url)) {
    return { ok: true, status: 200, json: async () => ROUTES.slice() };
  }
  if (method === 'POST' && /\/rest\/v1\/alf_claim_routes$/.test(url)) {
    const body = JSON.parse(opts.body);
    ROUTES.push(body);
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
function assertEq(actual, expected, msg) {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error((msg || 'mismatch') + ': expected ' + JSON.stringify(expected) + ' got ' + JSON.stringify(actual));
  }
}
function assertTrue(v, msg) { if (!v) throw new Error(msg || 'expected truthy'); }

(async () => {
  // ---- write gate ----
  await check('nursing cannot write a billing rule (403)', async () => {
    const res = await call('nursing', 'EMP-NUR', 'write', 'alf_payer_rules', seedRow('OH-HCBS-AL-2024'));
    assertEq(res.statusCode, 403);
    assertEq(RULES.length, 0);
  });

  await check('a rule with no resolvable authority URL is refused (400), not stored', async () => {
    const bad = seedRow('OH-HCBS-AL-2024');
    bad.data = Object.assign({}, bad.data, { authority: { citation: 'trust me' } });
    const res = await call('owner', 'EMP-OWN', 'write', 'alf_payer_rules', bad);
    assertEq(res.statusCode, 400);
    assertEq(res.body.error.code, 'NO_AUTHORITY');
    assertEq(RULES.length, 0);
  });

  await check('an unknown program is refused (400)', async () => {
    const bad = seedRow('OH-HCBS-AL-2024');
    bad.program = 'commercial_ppo';
    const res = await call('owner', 'EMP-OWN', 'write', 'alf_payer_rules', bad);
    assertEq(res.statusCode, 400);
  });

  await check('a bogus state code is refused (400)', async () => {
    const bad = seedRow('OH-HCBS-AL-2024');
    bad.state = 'ZZ';
    const res = await call('owner', 'EMP-OWN', 'write', 'alf_payer_rules', bad);
    assertEq(res.statusCode, 400);
    assertEq(res.body.error.code, 'BAD_STATE');
  });

  await check('state "US" IS accepted, so a federal hospice rule need not pose as a state rule', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', 'alf_payer_rules', seedRow('US-HOSPICE-MA-CARVEOUT-2025'));
    assertEq(res.statusCode, 200);
    assertEq(RULES.length, 1);
  });

  await check('an inverted effective range is refused, pointing at status never_in_force instead', async () => {
    const bad = seedRow('IN-HCBS-AL-2026-PAUSED');
    bad.effective_from = '2026-01-01'; bad.effective_to = '2025-12-30';
    const res = await call('owner', 'EMP-OWN', 'write', 'alf_payer_rules', bad);
    assertEq(res.statusCode, 400);
    assertTrue(/never_in_force/.test(res.body.error.message));
  });

  await check('management CAN load the real seeded rules', async () => {
    for (const id of ['OH-HCBS-AL-2024', 'IN-HCBS-AL-2026-PAUSED', 'IN-HCBS-AL-2026-MANDATE-SUPERSEDED']) {
      const res = await call('owner', 'EMP-OWN', 'write', 'alf_payer_rules', seedRow(id));
      assertEq(res.statusCode, 200, id + ' should have stored');
    }
    assertEq(RULES.length, 4);
  });

  await check('verified_by is server-stamped from the session, not trusted from the client', async () => {
    const forged = seedRow('OH-HCBS-AL-2024');
    forged.verified_by = 'SOMEONE-ELSE';
    await call('billing', 'EMP-BILL', 'write', 'alf_payer_rules', forged);
    const stored = RULES.find((r) => r.rule_id === 'OH-HCBS-AL-2024');
    assertEq(stored.verified_by, 'EMP-BILL');
  });

  // ---- read + coverage ----
  await check('any authenticated employee can READ the rules', async () => {
    const res = await call('med_aide', 'MA-1', 'read', 'alf_payer_rules', null);
    assertEq(res.statusCode, 200);
    assertTrue(res.body.data.length >= 4);
  });

  await check('coverage reports MI/PA as honestly uncovered against a claimed 4-state set', async () => {
    const res = await call('owner', 'EMP-OWN', 'read', 'alf_payer_rules', { claimed_states: ['OH', 'IN', 'MI', 'PA'] });
    assertEq(res.body.coverage.have, 2);
    assertEq(res.body.coverage.need, 4);
    assertEq(res.body.coverage.uncovered_states.sort(), ['MI', 'PA']);
  });

  // ---- route ----
  await check('nursing cannot route a claim (403)', async () => {
    const res = await call('nursing', 'EMP-NUR', 'route', 'alf_payer_rules', { program: 'medicaid_hcbs', state: 'OH', service_month: '2026-05' });
    assertEq(res.statusCode, 403);
  });

  await check('routing an UNCOVERED state fails closed and names the state, never an empty success', async () => {
    const res = await call('owner', 'EMP-OWN', 'route', 'alf_payer_rules', {
      program: 'medicaid_hcbs', state: 'MI', service_month: '2026-05', days_present: 30, tier: 'tier1'
    });
    assertEq(res.body.ok, false);
    assertEq(res.body.error.code, 'NO_RULE_FOR_STATE');
    assertTrue(/MI/.test(res.body.error.message), 'must name the uncovered state');
    assertTrue(/not covered/i.test(res.body.error.message));
  });

  await check('routing a real Ohio claim returns the verified code+modifier line', async () => {
    const res = await call('owner', 'EMP-OWN', 'route', 'alf_payer_rules', {
      program: 'medicaid_hcbs', state: 'OH', service_month: '2026-05', days_present: 31, tier: 'tier2'
    });
    assertEq(res.body.ok, true);
    assertEq(res.body.line.billing_string, 'T2031 U2');
    assertEq(res.body.line.units, 31);
  });

  await check('the superseded Indiana mandate is never selected even though it is loaded', async () => {
    const res = await call('owner', 'EMP-OWN', 'route', 'alf_payer_rules', {
      program: 'medicaid_hcbs', state: 'IN', service_month: '2026-01', days_present: 31, tier: 'tier1'
    });
    assertEq(res.body.ok, true);
    // Would be 'monthly (required)' under the superseded mandate; under the live paused
    // rule 31 days exceeds the 29-day daily cap so monthly is the only option -- but it must
    // come from the PAUSED rule, which is the one that cites BT2025190.
    assertEq(res.body.rule_id, 'IN-HCBS-AL-2026-PAUSED');
  });

  await check('a hospice claim with an exact diagnosis match is refused through the real handler', async () => {
    const res = await call('owner', 'EMP-OWN', 'route', 'alf_payer_rules', {
      program: 'hospice_ma', service_month: '2026-05', hospice_election: true, claim_type: 'professional',
      claim_principal_diagnosis: 'C34.90', hospice_principal_diagnosis: 'C34.90', relatedness: 'unrelated'
    });
    assertEq(res.body.ok, false);
    assertEq(res.body.error.code, 'DX_MATCH_WOULD_DENY');
  });

  await check('routing writes NOTHING -- previewing a route cannot create a billing record', async () => {
    const before = ROUTES.length;
    await call('owner', 'EMP-OWN', 'route', 'alf_payer_rules', {
      program: 'medicaid_hcbs', state: 'OH', service_month: '2026-05', days_present: 31, tier: 'tier1'
    });
    assertEq(ROUTES.length, before, 'route must not persist anything');
  });

  // ---- claim routes ----
  await check('caregiver cannot read claim routes (403)', async () => {
    const res = await call('caregiver', 'CG-1', 'read', 'alf_claim_routes', null);
    assertEq(res.statusCode, 403);
  });

  await check('management can record a routing decision', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', 'alf_claim_routes', {
      id: 'ROUTE-1', resident_id: 'RES-1', service_month: '2026-05',
      method: 'daily', billing_string: 'T2031 U2'
    });
    assertEq(res.statusCode, 200);
    assertEq(ROUTES.length, 1);
    assertEq(ROUTES[0].decided_by, 'EMP-OWN', 'decided_by must be server-stamped');
  });

  await check('a routing decision is append-only -- reusing an id is 409, never an overwrite', async () => {
    const res = await call('owner', 'EMP-OWN', 'write', 'alf_claim_routes', {
      id: 'ROUTE-1', resident_id: 'RES-1', service_month: '2026-05', method: 'monthly', billing_string: 'TAMPERED'
    });
    assertEq(res.statusCode, 409);
    assertEq(ROUTES.length, 1);
    assertEq(ROUTES[0].data.billing_string, 'T2031 U2', 'original decision must be unchanged');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
