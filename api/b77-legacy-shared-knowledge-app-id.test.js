'use strict';
// cc b77 (N-3 sweep): the sairnlegacy shared_knowledge permission check was
// applied only when the CALLER declared body.app_id === 'sairnlegacy'. A
// legacy staff member without shared_knowledge_access could omit app_id (or
// send another) and read or write sd_shared_knowledge for the licence. The
// check must key on the licence's own app (lic.app_id), the same server truth
// checkEnvelope already uses.

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || ['b77', 'legacy', 'sk'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';
const { signSessionToken } = require('./_lib/auth');

const HASH = 'b77-legacy-sk-hash';
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

async function call(t) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: { validateLicenseKey: async () => ({
      valid: true, active: true, license_hash: HASH, app_id: 'sairnlegacy', trial_ends_at: null,
      customer_email: 'b77@example.test', stripe_subscription_id: null }) }
  };
  const dataCalls = [];
  global.fetch = async function (url, init) {
    const u = String(url);
    const reply = (st, b) => ({ ok: st >= 200 && st < 300, status: st,
      json: async () => b, text: async () => JSON.stringify(b) });
    if (/_employee_auth\?/.test(u)) return reply(200, [{ employee_id: 'EMP-1', active: true,
      shared_knowledge_access: !!t.access }]);
    if (/sd_shared_knowledge/.test(u)) dataCalls.push(((init && init.method) || 'GET') + ' ' + u);
    return reply(200, []);
  };
  delete require.cache[require.resolve('./sd-data.js')];
  const h = require('./sd-data.js');
  const res = mockRes();
  const body = { action: t.action, resource: 'shared_knowledge',
    payload: t.action === 'write' ? { words: ['countertop'] } : {} };
  if (t.bodyAppId !== undefined) body.app_id = t.bodyAppId;
  const origErr = console.error, origWarn = console.warn, origLog = console.log;
  console.error = function () {}; console.warn = function () {}; console.log = function () {};
  try {
    await h({
      method: 'POST',
      headers: { authorization: 'Bearer KEY-FOR-' + HASH,
        'x-sd-auth': signSessionToken({ app: 'sairnlegacy', employee_id: 'EMP-1', role: t.role, license_hash: HASH }) },
      body: body
    }, res);
  } catch (e) {
    res.statusCode = 'THREW'; res.body = { error: { code: 'THREW', message: e && e.message } };
  } finally { console.error = origErr; console.warn = origWarn; console.log = origLog; }
  res.dataCalls = dataCalls;
  return res;
}

(async () => {
  const label = (t) => t.role + (t.access ? '+access' : '') + ' ' + t.action + ', app_id ' + (t.bodyAppId || 'ABSENT');

  console.log('C. CONTROL -- an owner, and staff WITH access, reach the data whatever app_id says');
  for (const action of ['read', 'write']) {
    for (const bodyAppId of ['sairnlegacy', undefined, 'stonedesk']) {
      for (const t of [{ role: 'owner' }, { role: 'staff', access: true }]) {
        const a = Object.assign({ action, bodyAppId }, t);
        const r = await call(a);
        is(r.statusCode === 200 && r.dataCalls.length > 0, 'C[' + label(a) + '] -> 200 with a data call',
          r.statusCode + ' ' + code(r) + ' calls=' + r.dataCalls.length);
      }
    }
  }

  console.log('R. staff WITHOUT access is refused whatever app_id the body declares');
  for (const action of ['read', 'write']) {
    for (const bodyAppId of ['sairnlegacy', undefined, 'stonedesk']) {
      const a = { role: 'staff', access: false, action, bodyAppId };
      const r = await call(a);
      const ok = r.statusCode === 403 && code(r) === 'FORBIDDEN' && r.dataCalls.length === 0;
      console.log('  ' + (ok ? 'ok  ' : 'RED ') + label(a) + ' -> ' + r.statusCode + ' ' + (code(r) || '(ok)')
        + ' dataCalls=' + r.dataCalls.length);
      is(ok, 'R[' + label(a) + '] -> 403 FORBIDDEN, no data call', r.statusCode + ' ' + code(r));
    }
  }

  console.log('\n' + (fail ? 'FAILED' : 'PASSED') + ' -- ' + pass + ' passed, ' + fail + ' failed');
  if (fail) console.log('FAILING ARMS: ' + failed.join(', '));
  process.exit(fail ? 1 : 0);
})();
