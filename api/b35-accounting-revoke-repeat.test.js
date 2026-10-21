'use strict';
// b35 -- a repeat revoke must not rewrite the original revocation
// (SAIRN-handoff-cody-b34.md s4.4).
//
// CONCEPT (stated before the code): a revocation is a historical fact -- the
// first revoke writes revoked_on/revoked_by, a repeat leaves them exactly as
// they were and still completes the credential discard.
//
// The mock is a STORE, not a canned reply: the consent PATCH honours the
// PostgREST filters in its URL, so a PATCH without the `revoked_on=is.null`
// guard really does overwrite the stored row, the way the live table would.

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || ['b35', 'accounting', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';
const { signSessionToken } = require('./_lib/auth');

const HASH = 'b35-accounting-hash';

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
  res.setHeader = function () {}; res.end = function () {};
  return res;
}

// store.consents: rows keyed by consent_id. store.conn: {status, body} for the
// connection PATCH. store.consentGetStatus: overrides the consent GET status.
function install(store) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: { validateLicenseKey: async () => ({
      valid: true, active: true, license_hash: HASH, app_id: 'sairnroofing' }) }
  };
  global.fetch = async function (url, init) {
    const u = decodeURIComponent(String(url));
    const method = (init && init.method) || 'GET';
    const reply = (status, bodyObj) => ({
      ok: status >= 200 && status < 300, status: status,
      json: async () => bodyObj, text: async () => JSON.stringify(bodyObj) });
    if (/accounting_consents/.test(u)) {
      const m = u.match(/consent_id=eq\.([^&]+)/);
      const row = m ? store.consents[m[1]] : null;
      if (method === 'PATCH') {
        if (!row) return reply(200, []);
        if (/revoked_on=is\.null/.test(u) && row.revoked_on) return reply(200, []);
        if (store.patchMatchesNothing) return reply(200, []);
        Object.assign(row, JSON.parse(init.body));
        return reply(200, [Object.assign({}, row)]);
      }
      if (store.consentGetStatus) return reply(store.consentGetStatus, { message: 'boom' });
      return reply(200, row ? [Object.assign({}, row)] : []);
    }
    if (/accounting_connections/.test(u) && method === 'PATCH') {
      const c = store.conn.shift ? store.conn.shift() : store.conn;
      return reply(c.status, c.body);
    }
    return reply(200, []);
  };
  delete require.cache[require.resolve('./accounting.js')];
  return require('./accounting.js');
}

async function revoke(store, employee, today, consentId) {
  const h = install(store);
  const res = mockRes();
  await h({
    method: 'POST',
    headers: {
      authorization: 'Bearer KEY-FOR-' + HASH,
      'x-sd-auth': signSessionToken({ app: 'sairnroofing', employee_id: employee, role: 'owner', license_hash: HASH })
    },
    body: { action: 'revoke', app_id: 'sairnroofing', payload: { today: today, consent_id: consentId } }
  }, res);
  return res;
}
const show = (r) => r.statusCode + ' ' + JSON.stringify(r.body).slice(0, 300);
const CONN_OK = { status: 200, body: [{ provider: 'quickbooks_online', status: 'revoked' }] };
const fresh = () => ({ 'C-1': { consent_id: 'C-1', revoked_on: null, revoked_by: null } });

(async function main() {
  const origErr = console.error;
  console.error = function () {};
  try {
    console.log('\nV. A REPEAT REVOKE KEEPS THE ORIGINAL REVOCATION');
    {
      let store = { consents: fresh(), conn: CONN_OK };
      let r = await revoke(store, 'emp-1', '2026-10-01', 'C-1');
      is(r.statusCode === 200 && store.consents['C-1'].revoked_on === '2026-10-01' && store.consents['C-1'].revoked_by === 'emp-1'
         && r.body.tokens_discarded === true,
         'V1. first revoke records revoked_on/revoked_by and discards', show(r));

      r = await revoke(store, 'emp-2', '2026-10-21', 'C-1');
      is(store.consents['C-1'].revoked_on === '2026-10-01' && store.consents['C-1'].revoked_by === 'emp-1',
         'V2. THE DEFECT: a repeat revoke leaves revoked_on/revoked_by as the first revoke wrote them',
         JSON.stringify(store.consents['C-1']));
      is(r.statusCode === 200 && r.body.tokens_discarded === true && r.body.already_revoked === true
         && r.body.data && r.body.data.revoked_on === '2026-10-01',
         'V3. a repeat revoke still completes the discard and says the consent was already revoked', show(r));

      store = { consents: fresh(), conn: [{ status: 500, body: { message: 'boom' } }, CONN_OK] };
      r = await revoke(store, 'emp-1', '2026-10-01', 'C-1');
      is(r.statusCode === 502 && r.body.error.code === 'TOKEN_DISCARD_UNCONFIRMED',
         'V4. setup: the discard fails first time -> TOKEN_DISCARD_UNCONFIRMED', show(r));
      r = await revoke(store, 'emp-2', '2026-10-21', 'C-1');
      is(r.statusCode === 200 && r.body.tokens_discarded === true
         && store.consents['C-1'].revoked_on === '2026-10-01' && store.consents['C-1'].revoked_by === 'emp-1',
         'V5. the retry the 502 invites completes the discard without rewriting the revocation', show(r) + ' ' + JSON.stringify(store.consents['C-1']));
    }

    console.log('\nN. ZERO ROWS IS NOT AUTOMATICALLY "NO SUCH CONSENT"');
    {
      let store = { consents: fresh(), conn: CONN_OK };
      let r = await revoke(store, 'emp-1', '2026-10-01', 'C-404');
      is(r.statusCode === 404 && r.body.error.code === 'NO_CONSENT',
         'N1. an id with no consent on this licence -> 404 NO_CONSENT (unchanged)', show(r));
      store = { consents: { 'C-1': { consent_id: 'C-1', revoked_on: '2026-10-01', revoked_by: 'emp-1' } }, conn: CONN_OK, consentGetStatus: 500 };
      r = await revoke(store, 'emp-2', '2026-10-21', 'C-1');
      is(r.statusCode === 502 && r.body.ok !== true && (!r.body.error || r.body.error.code !== 'NO_CONSENT'),
         'N2. the guard matched nothing and the re-read FAILED -> 502, not 404 NO_CONSENT and not success', show(r));
      store = { consents: fresh(), conn: CONN_OK, patchMatchesNothing: true };
      r = await revoke(store, 'emp-2', '2026-10-21', 'C-1');
      is(r.statusCode === 502 && r.body.error.code === 'REVOKE_UNCONFIRMED' && r.body.ok !== true,
         'N3. the guard matched nothing yet the consent reads as ACTIVE -> 502 REVOKE_UNCONFIRMED, not NO_CONSENT and not a discard', show(r));
    }
  } finally { console.error = origErr; }

  console.log('\n' + (fail ? 'FAILED' : 'PASSED') + ' -- ' + pass + ' passed, '
    + fail + ' failed' + (fail ? '\nFAILING ARMS: ' + failed.join(', ') : ''));
  process.exit(fail ? 1 : 0);
})().catch((e) => {
  console.error('HARNESS ERROR -- no verdict was reached, which is NOT a pass');
  console.error(e);
  process.exit(1);
});
