'use strict';
// b36 -- sd_customers: a DELETED employee row is refused like a deactivated one.
// Michael's decision, 2026-10-21: "a deleted employee row denies session access
// the same as deactivation does -- no exception."
//
// CONCEPT (stated before the code): a missing employee row counts as a
// deactivation once the resource's app is known; sd_customers is StoneDesk-only
// and its branch already asserts 'stonedesk', so the pre-gate is told so and a
// deleted row is refused on the same path as active:false.
//
//   D  stonedesk token, row DELETED   -> 403 CREDENTIAL_INACTIVE, every verb, no customer data touched
//   I  stonedesk token, active:false  -> 403 CREDENTIAL_INACTIVE (unchanged)
//   C  stonedesk token, active:true   -> 200 (control)
//   X  sairnbiz token, no sairnbiz row -> NOT CREDENTIAL_INACTIVE: the wrong app is the branch gate's answer
//   T  employee lookup fails (500)     -> not refused here: a transport failure is not a deactivation

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || ['b36', 'deleted', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';
const { signSessionToken } = require('./_lib/auth');

const HASH = 'b36-deleted-hash';

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

// `employee` = what the employee-auth table answers: null (row deleted), a row,
// or { status } for a failed lookup. Every other call is recorded.
async function call(app, role, action, employee) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: { validateLicenseKey: async () => ({
      valid: true, active: true, license_hash: HASH, trial_ends_at: null,
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
  const origErr = console.error, origWarn = console.warn;
  console.error = function () {}; console.warn = function () {};
  try {
    await h({
      method: 'POST',
      headers: { authorization: 'Bearer KEY-FOR-' + HASH,
        'x-sd-auth': signSessionToken({ app: app, employee_id: 'EMP-1', role: role, license_hash: HASH }) },
      body: { action: action, resource: 'sd_customers', payload: { id: 'C-1' } }
    }, res);
  } finally { console.error = origErr; console.warn = origWarn; }
  res.dataCalls = dataCalls;
  return res;
}
const code = (r) => (r.body && r.body.error && r.body.error.code) || '';
const show = (r) => r.statusCode + ' ' + JSON.stringify(r.body).slice(0, 220) + ' calls=' + r.dataCalls.length;

const VERBS = ['read', 'write', 'write_batch', 'soft_delete', 'tombstones'];

(async function main() {
  console.log('\nD. a DELETED stonedesk employee row is refused at the pre-gate');
  for (let i = 0; i < VERBS.length; i++) {
    const r = await call('stonedesk', 'owner', VERBS[i], null);
    is(r.statusCode === 403 && code(r) === 'CREDENTIAL_INACTIVE' && r.dataCalls.length === 0,
       'D' + (i + 1) + '. sd_customers/' + VERBS[i] + ', employee row deleted -> 403 CREDENTIAL_INACTIVE, no customer data touched', show(r));
  }

  console.log('\nI / C. the existing states are unchanged');
  {
    let r = await call('stonedesk', 'owner', 'read', { active: false });
    is(r.statusCode === 403 && code(r) === 'CREDENTIAL_INACTIVE' && r.dataCalls.length === 0,
       'I1. active:false -> 403 CREDENTIAL_INACTIVE (unchanged)', show(r));
    r = await call('stonedesk', 'owner', 'read', { active: true });
    is(r.statusCode === 200 && r.dataCalls.length > 0,
       'C1. CONTROL: an active employee still reads customers', show(r));
  }

  console.log('\nX / T. the gate stays narrow');
  {
    let r = await call('sairnbiz', 'owner', 'read', null);
    is(code(r) !== 'CREDENTIAL_INACTIVE' && r.statusCode >= 400 && r.dataCalls.length === 0,
       'X1. a sairnbiz token with no sairnbiz row is answered by the branch gate, not told it was deactivated', show(r));
    // REVERSED in hank b56 (Michael's b56 decision): an ANSWERED 500 from the
    // employee lookup is refused 502 ACTIVE_CHECK_FAILED -- still never told it
    // was deactivated, and nothing is read.
    r = await call('stonedesk', 'owner', 'read', { status: 500 });
    is(r.statusCode === 502 && code(r) === 'ACTIVE_CHECK_FAILED' && r.dataCalls.length === 0,
       'T1. the employee lookup FAILED (answered 500) -> 502 ACTIVE_CHECK_FAILED, not a deactivation, nothing read', show(r));
  }

  console.log('\n' + (fail ? 'FAILED' : 'PASSED') + ' -- ' + pass + ' passed, '
    + fail + ' failed' + (fail ? '\nFAILING ARMS: ' + failed.join(', ') : ''));
  process.exit(fail ? 1 : 0);
})().catch((e) => {
  console.error('HARNESS ERROR -- no verdict was reached, which is NOT a pass');
  console.error(e);
  process.exit(1);
});
