// api/b38-deleted-row-platform.test.js
//
// Run:  node api/b38-deleted-row-platform.test.js
//
// b38 -- a DELETED employee row is refused on EVERY registered resource.
// Michael's decision, 2026-10-21: platform-wide, no exception (b36 did
// sd_customers alone; cc b37 drove sd_quote_requests, sd_crm, sen_clients,
// alf_clients and rf_jobs still answering 200 on a deleted row).
//
// CONCEPT (stated before the code): the registry already says which app owns
// each resource, so that app is the pre-gate's expected app, and a missing row
// of that app is a deactivation everywhere it is known.
//
// THE POPULATION IS DERIVED, NOT LISTED: every resource in OWNER_BY_RESOURCE
// whose owner app has an employee-auth table. A resource added to the registry
// tomorrow is driven here tomorrow without anybody editing this file.
//
//   D  owner-app token, row DELETED   -> 403 CREDENTIAL_INACTIVE, no data call   (every derived resource)
//   I  owner-app token, active:false  -> 403 CREDENTIAL_INACTIVE                  (every derived resource)
//   C  owner-app token, active:true   -> NOT CREDENTIAL_INACTIVE                  (control, every derived resource)
//   X  a token from ANOTHER app, no row -> NOT CREDENTIAL_INACTIVE (the branch gate answers the wrong app)
//   S  a SHARED resource follows the caller's app_id, like memory
//   T  the employee lookup FAILS      -> not refused here (a transport failure is not a deactivation)
//
// Exit: 0 all arms passed - 1 an arm FAILED - 2 COULD NOT RUN (empty population)
'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || ['b38', 'deleted', 'platform'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';
const { signSessionToken, AUTH_TABLE_BY_APP, ROLES_BY_APP } = require('./_lib/auth');
const { OWNER_BY_RESOURCE } = require('./_resources');

const HASH = 'b38-deleted-hash';
let pass = 0, fail = 0;
const failed = [];
function is(c, l, d) {
  if (c) { pass++; return; }
  fail++; failed.push(l);
  console.log('  FAIL  ' + l + (d ? '\n        ' + String(d).slice(0, 300) : ''));
}
function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  res.setHeader = function () {};
  return res;
}
const code = (r) => (r.body && r.body.error && r.body.error.code) || '';

// `employee` = what the employee-auth table answers: null (row deleted), a row,
// or { status } for a failed lookup. Every other upstream call is counted.
async function call(tokenApp, resource, employee, appId) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: { validateLicenseKey: async () => ({
      valid: true, active: true, license_hash: HASH, app_id: appId, trial_ends_at: null,
      stripe_subscription_id: null }) }
  };
  const dataCalls = [];
  global.fetch = async function (url, init) {
    const u = String(url);
    const reply = (st, b) => ({ ok: st >= 200 && st < 300, status: st,
      json: async () => b, text: async () => JSON.stringify(b) });
    if (/_employee_auth\?/.test(u)) {
      if (employee && employee.status) return reply(employee.status, { message: 'boom' });
      return reply(200, employee ? [employee] : []);
    }
    dataCalls.push(((init && init.method) || 'GET') + ' ' + u);
    return reply(200, []);
  };
  delete require.cache[require.resolve('./sd-data.js')];
  const h = require('./sd-data.js');
  const res = mockRes();
  const role = (ROLES_BY_APP[tokenApp] || ['owner'])[0];
  const origErr = console.error, origWarn = console.warn, origLog = console.log;
  console.error = function () {}; console.warn = function () {}; console.log = function () {};
  try {
    await h({
      method: 'POST',
      headers: { authorization: 'Bearer KEY-FOR-' + HASH,
        'x-sd-auth': signSessionToken({ app: tokenApp, employee_id: 'EMP-1', role: role, license_hash: HASH }) },
      body: { action: 'read', resource: resource, app_id: appId, payload: { id: 'X-1' } }
    }, res);
  } catch (e) {
    res.statusCode = 'THREW'; res.body = { error: { code: 'THREW', message: e && e.message } };
  } finally { console.error = origErr; console.warn = origWarn; console.log = origLog; }
  res.dataCalls = dataCalls;
  return res;
}

(async () => {
  const population = Object.keys(OWNER_BY_RESOURCE).filter((r) =>
    r !== 'memory' && AUTH_TABLE_BY_APP[OWNER_BY_RESOURCE[r]]).sort();
  const apps = Array.from(new Set(population.map((r) => OWNER_BY_RESOURCE[r]))).sort();
  console.log('POPULATION: ' + population.length + ' registered resources across ' + apps.length + ' apps with an employee table');
  if (population.length < 50 || apps.length < 10) {
    console.log('COULD NOT RUN: the derived population is implausibly small -- the registry or the auth-table map did not load as expected. Nothing was verified.');
    process.exit(2);
  }

  console.log('\nD/I/C. every registered resource, owner-app token');
  for (const r of population) {
    const app = OWNER_BY_RESOURCE[r];
    const d = await call(app, r, null, app);
    is(d.statusCode === 403 && code(d) === 'CREDENTIAL_INACTIVE' && d.dataCalls.length === 0,
      'D[' + app + '/' + r + '] row DELETED -> 403 CREDENTIAL_INACTIVE, no data call',
      d.statusCode + ' ' + code(d) + ' calls=' + d.dataCalls.length);
    const i = await call(app, r, { employee_id: 'EMP-1', active: false }, app);
    is(i.statusCode === 403 && code(i) === 'CREDENTIAL_INACTIVE',
      'I[' + app + '/' + r + '] active:false -> 403 CREDENTIAL_INACTIVE', i.statusCode + ' ' + code(i));
    const c = await call(app, r, { employee_id: 'EMP-1', active: true }, app);
    is(code(c) !== 'CREDENTIAL_INACTIVE',
      'C[' + app + '/' + r + '] CONTROL active:true is not refused as inactive', c.statusCode + ' ' + code(c));
  }
  console.log('  ' + population.length * 3 + ' arms driven');

  console.log('\nX. a token from ANOTHER app with no row is the branch gate\'s answer, not a deactivation');
  for (const r of ['sd_quote_requests', 'sen_clients', 'alf_clients', 'rf_jobs', 'sd_customers']) {
    const owner = OWNER_BY_RESOURCE[r];
    const other = owner === 'sairnbiz' ? 'stonedesk' : 'sairnbiz';
    const x = await call(other, r, null, owner);
    is(x.statusCode !== 200 && code(x) !== 'CREDENTIAL_INACTIVE',
      'X[' + other + ' token at ' + r + '] no row -> refused, but NOT as CREDENTIAL_INACTIVE', x.statusCode + ' ' + code(x));
  }

  console.log('\nS. a SHARED resource follows the caller\'s declared app_id');
  const sd = await call('stonedesk', 'employees', null, 'stonedesk');
  is(sd.statusCode === 403 && code(sd) === 'CREDENTIAL_INACTIVE' && sd.dataCalls.length === 0,
    'S1 stonedesk token at shared employees, app_id stonedesk, row DELETED -> 403', sd.statusCode + ' ' + code(sd));
  const sx = await call('stonedesk', 'employees', null, 'sairnbiz');
  is(code(sx) !== 'CREDENTIAL_INACTIVE',
    'S2 stonedesk token at shared employees but app_id sairnbiz -> not scoped, not called a deactivation', sx.statusCode + ' ' + code(sx));

  console.log('\nT. a failed lookup is not a deactivation');
  const t = await call('stonedesk', 'sd_quote_requests', { status: 500 }, 'stonedesk');
  is(code(t) !== 'CREDENTIAL_INACTIVE', 'T1 the employee lookup FAILED -> not refused as inactive', t.statusCode + ' ' + code(t));

  console.log('\n' + (fail ? 'FAILED' : 'PASSED') + ' -- ' + pass + ' passed, ' + fail + ' failed');
  if (fail) console.log('FAILING ARMS: ' + failed.slice(0, 40).join(', ') + (failed.length > 40 ? ' ... +' + (failed.length - 40) : ''));
  process.exit(fail ? 1 : 0);
})();
