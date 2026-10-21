'use strict';
// b37 -- the revoke discard is scoped to the consent being revoked
// (cc b35 handoff s1 / s3(c): "the discard it reaches is not scoped to the
// consent ... a repeat revoke of a stale consent cleared the connection
// belonging to an active consent").
//
// CONCEPT (stated before the code): a revoke may discard only the credentials
// its own consent authorised -- the connection PATCH is filtered by consent_id,
// not by provider.
//
// TWO CONSENTS, ONE PROVIDER: C-OLD was granted and revoked; C-NEW was granted
// after it and its connection holds live tokens. Revoking C-OLD again (the
// repeat b35 made reachable) must leave C-NEW's connection exactly as it was.
//
// The mock is a STORE that honours every eq. filter in the PATCH URL, so a PATCH
// filtered by provider alone really does match C-NEW's row.

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || ['b37', 'scope', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';
const { signSessionToken } = require('./_lib/auth');

const HASH = 'b37-scope-hash';

let pass = 0, fail = 0;
const failed = [];
function ok(l) { pass++; console.log('  ok    ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL  ' + l);
  if (why) console.log('        ' + String(why).slice(0, 600));
}
function is(c, l, d) { if (c) ok(l); else bad(l, d); }

function eqFilters(u) {
  const q = u.split('?')[1] || '';
  const f = {};
  q.split('&').forEach((kv) => {
    const m = kv.match(/^([a-z_]+)=eq\.(.*)$/);
    if (m) f[m[1]] = decodeURIComponent(m[2]);
  });
  return f;
}
const matches = (row, f) => Object.keys(f).every((k) => String(row[k]) === f[k]);

function install(store) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: { validateLicenseKey: async () => ({ valid: true, active: true, license_hash: HASH, app_id: 'sairnroofing' }) }
  };
  global.fetch = async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    const reply = (s, b) => ({ ok: s >= 200 && s < 300, status: s, json: async () => b, text: async () => JSON.stringify(b) });
    if (/_employee_auth\?/.test(u)) return reply(200, [{ active: true }]);
    const table = /accounting_consents/.test(u) ? 'consents' : (/accounting_connections/.test(u) ? 'connections' : null);
    if (!table) return reply(200, []);
    const f = eqFilters(u);
    let rows = store[table].filter((r) => matches(r, f));
    if (/revoked_on=is\.null/.test(u)) rows = rows.filter((r) => !r.revoked_on);
    if (method === 'PATCH') {
      const patch = JSON.parse(init.body);
      rows.forEach((r) => Object.assign(r, patch));
      return reply(200, rows.map((r) => Object.assign({}, r)));
    }
    return reply(200, rows.map((r) => Object.assign({}, r)));
  };
  delete require.cache[require.resolve('./accounting.js')];
  return require('./accounting.js');
}

async function revoke(store, consentId, payloadExtra) {
  const h = install(store);
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  res.setHeader = function () {}; res.end = function () {};
  const ce = console.error; console.error = function () {};
  try {
    await h({ method: 'POST', headers: { authorization: 'Bearer KEY-FOR-' + HASH,
      'x-sd-auth': signSessionToken({ app: 'sairnroofing', employee_id: 'emp-2', role: 'owner', license_hash: HASH }) },
      body: { action: 'revoke', app_id: 'sairnroofing', payload: Object.assign({ today: '2026-10-21', consent_id: consentId }, payloadExtra || {}) } }, res);
  } finally { console.error = ce; }
  return res;
}

function twoConsents() {
  return {
    consents: [
      { license_hash: HASH, consent_id: 'C-OLD', provider: 'quickbooks_online', granted_on: '2026-09-01', revoked_on: '2026-09-15', revoked_by: 'emp-1' },
      { license_hash: HASH, consent_id: 'C-NEW', provider: 'quickbooks_online', granted_on: '2026-10-01', revoked_on: null, revoked_by: null }
    ],
    connections: [
      { license_hash: HASH, provider: 'quickbooks_online', consent_id: 'C-NEW', status: 'connected', access_token_enc: 'ENC-A', refresh_token_enc: 'ENC-R' }
    ]
  };
}
const show = (r, s) => r.statusCode + ' ' + JSON.stringify(r.body).slice(0, 200) + ' conn=' + JSON.stringify(s.connections);

(async function main() {
  console.log('\nS. the discard belongs to the consent being revoked');
  {
    let s = twoConsents();
    let r = await revoke(s, 'C-OLD');
    const live = s.connections[0];
    is(live.status === 'connected' && live.access_token_enc === 'ENC-A' && live.refresh_token_enc === 'ENC-R',
       'S1. THE DEFECT: a repeat revoke of the stale C-OLD leaves C-NEW\'s live connection untouched', show(r, s));
    is(r.statusCode === 200 && r.body.already_revoked === true && r.body.tokens_discarded === false && r.body.connection_found === false,
       'S2. ...and reports that C-OLD had no connection to discard, not that one was discarded', show(r, s));

    s = twoConsents();
    r = await revoke(s, 'C-NEW');
    is(r.statusCode === 200 && r.body.tokens_discarded === true && s.connections[0].status === 'revoked'
       && s.connections[0].access_token_enc === null && s.connections[0].refresh_token_enc === null,
       'S3. CONTROL: revoking C-NEW discards C-NEW\'s own connection', show(r, s));
    is(s.consents[0].revoked_on === '2026-09-15' && s.consents[0].revoked_by === 'emp-1',
       'S4. ...and does not touch C-OLD\'s recorded revocation', JSON.stringify(s.consents[0]));

    s = twoConsents();
    s.connections.push({ license_hash: 'OTHER-LICENCE', provider: 'quickbooks_online', consent_id: 'C-NEW', status: 'connected', access_token_enc: 'X', refresh_token_enc: 'Y' });
    r = await revoke(s, 'C-NEW');
    is(s.connections[1].status === 'connected' && s.connections[1].access_token_enc === 'X',
       'S5. the licence filter still holds: another licence\'s row with the same consent_id is untouched', show(r, s));
  }

  console.log('\n' + (fail ? 'FAILED' : 'PASSED') + ' -- ' + pass + ' passed, '
    + fail + ' failed' + (fail ? '\nFAILING ARMS: ' + failed.join(', ') : ''));
  process.exit(fail ? 1 : 0);
})().catch((e) => {
  console.error('HARNESS ERROR -- no verdict was reached, which is NOT a pass');
  console.error(e);
  process.exit(1);
});
