// api/b76-shared-deleted-row-session-app.test.js
//
// Run:  node api/b76-shared-deleted-row-session-app.test.js
//
// cc b76 -- the deleted-row pre-gate on a SHARED / ROUTES resource must decide
// which app's employee table it consults from the SESSION, never from the
// caller-supplied body.app_id.
//
// THE DEFECT (Michael): b38 scoped `shared` and `routes` resources to
// `memApp` = body.app_id || 'stonedesk'. A deleted employee holding a valid
// token for app X could send app_id Y (or omit it, so it defaulted to
// 'stonedesk') and the pre-gate saw "expected app Y, token app X: unscoped",
// logged, and let the request through to a branch that answered 200.
// sairngrounds' grdData() sent no app_id at all, so EVERY grounds request hit
// the default.
//
//   R  row DELETED, body.app_id absent or another app -> 403 CREDENTIAL_INACTIVE,
//      no data call (the four named resources, driven with payloads that DO
//      reach the data when the row is active -- see C)
//   C  CONTROL: the same requests with an active row -> 200 (so R's payloads
//      are not refused for some other reason)
//   P  every shared/routes resource except memory, row DELETED, body.app_id
//      mismatched or absent -> refused, and no data call
//   V  no default app is needed: the verifier refuses a token naming no app or
//      an unknown one (V0 is the control that the forged tokens are valid)
//   K  an ACTIVE employee whose body.app_id names another app is not called
//      deactivated
//
// Exit: 0 all arms passed - 1 an arm FAILED - 2 COULD NOT RUN
'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || ['b76', 'shared', 'session'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';
const { signSessionToken, AUTH_TABLE_BY_APP } = require('./_lib/auth');
const { OWNER_BY_RESOURCE } = require('./_resources');

const HASH = 'b76-shared-hash';
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

// `employee`: null = the row is DELETED, else the row the auth table returns.
// `bodyAppId`: undefined = the key is omitted from the body entirely.
async function call(t) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: { validateLicenseKey: async () => ({
      valid: true, active: true, license_hash: HASH, app_id: t.tokenApp, trial_ends_at: null,
      customer_email: 'b76@example.test', stripe_subscription_id: null }) }
  };
  const dataCalls = [];
  global.fetch = async function (url, init) {
    const u = String(url);
    const reply = (st, b) => ({ ok: st >= 200 && st < 300, status: st,
      json: async () => b, text: async () => JSON.stringify(b) });
    if (/_employee_auth\?/.test(u)) return reply(200, t.employee ? [t.employee] : []);
    dataCalls.push(((init && init.method) || 'GET') + ' ' + u);
    return reply(200, []);
  };
  delete require.cache[require.resolve('./sd-data.js')];
  const h = require('./sd-data.js');
  const res = mockRes();
  const body = { action: t.action, resource: t.resource, payload: t.payload };
  if (t.bodyAppId !== undefined) body.app_id = t.bodyAppId;
  const origErr = console.error, origWarn = console.warn, origLog = console.log;
  console.error = function () {}; console.warn = function () {}; console.log = function () {};
  try {
    await h({
      method: 'POST',
      headers: { authorization: 'Bearer KEY-FOR-' + HASH,
        'x-sd-auth': signSessionToken({ app: t.tokenApp, employee_id: 'EMP-1', role: t.role || 'owner', license_hash: HASH }) },
      body: body
    }, res);
  } catch (e) {
    res.statusCode = 'THREW'; res.body = { error: { code: 'THREW', message: e && e.message } };
  } finally { console.error = origErr; console.warn = origWarn; console.log = origLog; }
  res.dataCalls = dataCalls;
  return res;
}

const ACTIVE = { employee_id: 'EMP-1', active: true };
// The four the defect names, each with a payload its branch accepts.
const NAMED = [
  { label: 'employees/read',    tokenApp: 'stonedesk',    resource: 'employees',    action: 'read',  payload: {},
    wrongApp: 'sairnbiz' },
  { label: 'employees/write',   tokenApp: 'sairnbiz',     resource: 'employees',    action: 'write',
    payload: [{ employee_id: 'E-2', name: 'B76 Test' }], wrongApp: 'stonedesk' },
  { label: 'render_usage/read', tokenApp: 'sairngrounds', resource: 'render_usage', action: 'read',  payload: {},
    wrongApp: 'stonedesk' },
  { label: 'rt_routes/read',    tokenApp: 'sairngrounds', resource: 'rt_routes',    action: 'read',
    payload: { app_id: 'sairngrounds', assignee_id: 'EMP-1', route_date: '2026-10-29' }, wrongApp: 'stonedesk' },
];

(async () => {
  const sharedPop = Object.keys(OWNER_BY_RESOURCE).filter((r) =>
    (OWNER_BY_RESOURCE[r] === 'shared' || OWNER_BY_RESOURCE[r] === 'routes') && r !== 'memory').sort();
  console.log('SHARED/ROUTES POPULATION (memory excluded): ' + sharedPop.join(', '));
  if (sharedPop.length < 6 || !AUTH_TABLE_BY_APP.sairngrounds || !AUTH_TABLE_BY_APP.stonedesk) {
    console.log('COULD NOT RUN: the registry or the auth-table map did not load as expected. Nothing was verified.');
    process.exit(2);
  }

  console.log('\nC. CONTROL -- an active row reaches the data (so R tests the pre-gate, not a bad payload)');
  for (const n of NAMED) {
    for (const appId of [undefined, n.wrongApp]) {
      const c = await call(Object.assign({}, n, { employee: ACTIVE, bodyAppId: appId }));
      is(c.statusCode === 200, 'C[' + n.label + ' ' + n.tokenApp + ' token, app_id ' + (appId || 'ABSENT') + '] active -> 200',
        c.statusCode + ' ' + code(c));
    }
  }

  console.log('\nR. a DELETED row is refused whatever app_id the body declares');
  for (const n of NAMED) {
    for (const appId of [undefined, n.wrongApp, n.tokenApp]) {
      const r = await call(Object.assign({}, n, { employee: null, bodyAppId: appId }));
      const ok = r.statusCode === 403 && code(r) === 'CREDENTIAL_INACTIVE' && r.dataCalls.length === 0;
      console.log('  ' + (ok ? 'ok  ' : 'RED ') + n.label + ' ' + n.tokenApp + ' token, app_id ' + (appId || 'ABSENT')
        + ' -> ' + r.statusCode + ' ' + (code(r) || '(ok)') + ' dataCalls=' + r.dataCalls.length);
      is(ok, 'R[' + n.label + ' ' + n.tokenApp + ' token, app_id ' + (appId || 'ABSENT') + '] DELETED -> 403 CREDENTIAL_INACTIVE, no data call',
        r.statusCode + ' ' + code(r) + ' calls=' + r.dataCalls.length);
    }
  }

  console.log('\nP. every shared/routes resource: a deleted row is served nothing');
  for (const r of sharedPop) {
    for (const t of [{ tokenApp: 'stonedesk', bodyAppId: 'sairnbiz' }, { tokenApp: 'sairngrounds', bodyAppId: undefined }]) {
      const p = await call({ tokenApp: t.tokenApp, resource: r, action: 'read', payload: { id: 'X-1' }, employee: null, bodyAppId: t.bodyAppId });
      is(p.statusCode !== 200 && p.dataCalls.length === 0,
        'P[' + r + ' ' + t.tokenApp + ' token, app_id ' + (t.bodyAppId || 'ABSENT') + '] DELETED -> refused, no data call',
        p.statusCode + ' ' + code(p) + ' calls=' + p.dataCalls.length);
    }
  }

  console.log('\nV. the fix has NO default app because the verifier refuses an app-less token');
  {
    // signSessionToken() refuses to mint an app-less token, so these are
    // signed directly with the platform key -- and V0 proves the forger makes
    // a token the verifier ACCEPTS, so V1/V2 cannot pass on a bad signature.
    const crypto = require('crypto');
    const { verifySessionToken } = require('./_lib/auth');
    const b64u = (b) => Buffer.from(b).toString('base64').replace(/=+$/, '').replace(/\+/g, '-').replace(/\//g, '_');
    const forge = (claims) => {
      const p = b64u(JSON.stringify(Object.assign({ typ: 'session', employee_id: 'EMP-1', role: 'owner',
        license_hash: HASH, iat: Date.now(), exp: Date.now() + 60000 }, claims)));
      return p + '.' + b64u(crypto.createHmac('sha256', process.env.SD_AUTH_SECRET).update(p).digest());
    };
    const v0 = verifySessionToken(forge({ app: 'sairngrounds' }), HASH);
    is(!!v0 && v0.app === 'sairngrounds', 'V0 CONTROL the forger mints a token the verifier accepts');
    is(verifySessionToken(forge({}), HASH) === null, 'V1 a token naming NO app is not a session (so the pre-gate never sees an app-less session)');
    is(verifySessionToken(forge({ app: 'not-an-app' }), HASH) === null, 'V2 a token naming an UNKNOWN app is not a session');
  }

  console.log('\nK. an ACTIVE employee declaring another app is not called deactivated');
  for (const n of NAMED) {
    const k = await call(Object.assign({}, n, { employee: ACTIVE, bodyAppId: n.wrongApp }));
    is(code(k) !== 'CREDENTIAL_INACTIVE', 'K[' + n.label + '] active, app_id ' + n.wrongApp + ' -> not CREDENTIAL_INACTIVE',
      k.statusCode + ' ' + code(k));
  }

  console.log('\n' + (fail ? 'FAILED' : 'PASSED') + ' -- ' + pass + ' passed, ' + fail + ' failed');
  if (fail) console.log('FAILING ARMS: ' + failed.slice(0, 40).join(', ') + (failed.length > 40 ? ' ... +' + (failed.length - 40) : ''));
  process.exit(fail ? 1 : 0);
})();
