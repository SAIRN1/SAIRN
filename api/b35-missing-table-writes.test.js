'use strict';
// b35 -- the eight sibling writes b34 left open (SAIRN-handoff-cody-b34.md s4.3).
//
// CONCEPT (stated before the code): a missing table on a write is a 503
// NOT_PROVISIONED that names the file which creates THAT table -- not a
// retryable generic 502 -- and the classification is made from the body, so a
// row the database refused is still reported as a refused row.
//
//   M  each write, table missing   -> 503 NOT_PROVISIONED naming its schema file
//   R  each write, 23xxx 400       -> 400 ROW_REFUSED (the table exists)
//   C  each write, table present   -> 200 ok (control)

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || ['b35', 'missing', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';
const { signSessionToken } = require('./_lib/auth');

const HASH = 'b35-missing-hash';
const KEY = 'KEY-FOR-' + HASH;

let pass = 0, fail = 0;
const failed = [];
function ok(l) { pass++; console.log('  ok    ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL  ' + l);
  if (why) console.log('        ' + String(why).slice(0, 600));
}
function is(c, l, d) { if (c) ok(l); else bad(l, d); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}

const MISSING = { code: 'PGRST205', message: "Could not find the table 'public.x' in the schema cache" };
const REFUSED = { code: '23514', message: 'new row violates check constraint' };

// `failOn` = a URL substring the data store answers with `failWith` for.
function pgMock(failOn, failWith) {
  return async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    const reply = (st, b) => ({ ok: st >= 200 && st < 300, status: st,
      json: async () => b, text: async () => JSON.stringify(b) });
    if (/_employee_auth/.test(u)) {
      return reply(200, [{ license_hash: HASH, employee_id: 'emp-1', role: 'owner', active: true }]);
    }
    if (failOn && u.indexOf(failOn) !== -1) return reply(failWith.status, failWith.body);
    if (method === 'POST' || method === 'PATCH') {
      let p = {}; try { p = JSON.parse(init.body); } catch (e) { p = {}; }
      return reply(200, Array.isArray(p) ? p : [p]);
    }
    // rf_roof_sections checks its building exists before writing.
    if (/rf_buildings\?/.test(u)) return reply(200, [{ building_id: 'B-1' }]);
    return reply(200, []);
  };
}

async function call(resource, payload, failOn, failWith) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: { validateLicenseKey: async () => ({
      valid: true, active: true, license_hash: HASH, trial_ends_at: null,
      stripe_subscription_id: null, app_id: 'sairnroofing' }) }
  };
  global.fetch = pgMock(failOn, failWith);
  delete require.cache[require.resolve('./sd-data.js')];
  const h = require('./sd-data.js');
  const res = mockRes();
  const origErr = console.error;
  console.error = function () {};
  try {
    await h({
      method: 'POST',
      headers: { authorization: 'Bearer ' + KEY,
        'x-sd-auth': signSessionToken({ app: 'sairnroofing', employee_id: 'emp-1', role: 'owner', license_hash: HASH }) },
      body: { action: 'write', resource: resource, payload: payload }
    }, res);
  } finally { console.error = origErr; }
  return res;
}
const msg = (r) => (r.body && r.body.error && r.body.error.message) || '';
const code = (r) => (r.body && r.body.error && r.body.error.code) || '';
const show = (r) => r.statusCode + ' ' + JSON.stringify(r.body).slice(0, 240);

const SITES = [
  ['subcontractors', { sub_id: 'S-1', name: 'Acme' }, 'subcontractor_compliance_schema.sql'],
  ['sub_assignments', { assignment_id: 'A-1', sub_id: 'S-1' }, 'subcontractor_compliance_schema.sql'],
  ['rf_safety_equipment', { equipment_id: 'E-1', kind: 'harness' }, 'sairnroofing_safety_schema.sql'],
  ['rf_job_hazard_assessments', { jha_id: 'J-1', job_id: 'JOB-1' }, 'sairnroofing_safety_schema.sql'],
  ['rf_buildings', { building_id: 'B-1', name: 'Main' }, 'sairnroofing_asset_registry_schema.sql'],
  ['rf_roof_sections', { section_id: 'R-1', building_id: 'B-1', name: 'North' }, 'sairnroofing_asset_registry_schema.sql'],
  ['rf_warranty_tiers', { tier_id: 'T-1', manufacturer: 'GAF', tier_name: 'Gold' }, 'sairnroofing_warranties_schema.sql'],
  ['rf_job_warranties', { warranty_id: 'W-1' }, 'sairnroofing_warranties_schema.sql']
];

(async function main() {
  for (let i = 0; i < SITES.length; i++) {
    const [resource, payload, schema] = SITES[i];
    const n = i + 1;
    console.log('\n' + resource);
    const onConflict = resource + '?on_conflict';
    let r = await call(resource, payload, onConflict, { status: 404, body: MISSING });
    is(r.statusCode === 503 && code(r) === 'NOT_PROVISIONED' && msg(r).indexOf('sql/' + schema) !== -1,
       'M' + n + '. ' + resource + ' write, table missing -> 503 NOT_PROVISIONED naming ' + schema + ' (was a generic 502)', show(r));
    r = await call(resource, payload, onConflict, { status: 400, body: REFUSED });
    is(r.statusCode === 400 && code(r) === 'ROW_REFUSED',
       'R' + n + '. ' + resource + ' write, 23514 -> 400 ROW_REFUSED, not "run the migration"', show(r));
    r = await call(resource, payload, null, null);
    is(r.statusCode === 200 && r.body && r.body.ok === true,
       'C' + n + '. CONTROL: ' + resource + ' write on a present table still succeeds', show(r));
  }

  console.log('\n' + (fail ? 'FAILED' : 'PASSED') + ' -- ' + pass + ' passed, '
    + fail + ' failed' + (fail ? '\nFAILING ARMS: ' + failed.join(', ') : ''));
  process.exit(fail ? 1 : 0);
})().catch((e) => {
  console.error('HARNESS ERROR -- no verdict was reached, which is NOT a pass');
  console.error(e);
  process.exit(1);
});
