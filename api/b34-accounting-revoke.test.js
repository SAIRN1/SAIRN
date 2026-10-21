'use strict';
// b34 -- api/accounting.js: a credential DISCARD is reported only after it is
// confirmed, and a data-store 400 is not automatically "run the migration".
//
// CONCEPT (stated before the code): a response may claim a side effect only
// after the write that performs it came back ok AND matched a row, and a
// PostgREST 400/404 must be classified by its body (missing relation vs missing
// column vs constraint) before it is called NOT_PROVISIONED.
//
// Source: cc's b29 notes section 1 (defects 3 and 4). Every arm drives the real
// handler with a mocked data store; R1-R5 differ ONLY in what the connection
// PATCH answers.

const fs = require('fs');
const path = require('path');
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || ['b34', 'accounting', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';
const { signSessionToken } = require('./_lib/auth');

const HASH = 'b34-accounting-hash';
const SRC = path.join(__dirname, 'accounting.js');

let pass = 0, fail = 0;
const failed = [];
function ok(l) { pass++; console.log('  ok    ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL  ' + l);
  if (why) console.log('        ' + String(why).slice(0, 600));
}
function is(c, l, d) { if (c) ok(l); else bad(l, d); }
function section(t) { console.log('\n' + t); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  res.setHeader = function () {}; res.end = function () {};
  return res;
}

// `conn` = what the accounting_connections PATCH answers; `consentsGet` = what
// the accounting_consents GET answers.
function load(conn, consentsGet) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: { validateLicenseKey: async () => ({
      valid: true, active: true, license_hash: HASH, app_id: 'sairnroofing' }) }
  };
  global.fetch = async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    const reply = (status, bodyObj) => ({
      ok: status >= 200 && status < 300, status: status,
      json: async () => bodyObj, text: async () => JSON.stringify(bodyObj) });
    if (/accounting_consents/.test(u) && method === 'PATCH') {
      return reply(200, [{ consent_id: 'C-1', revoked_on: '2026-10-21' }]);
    }
    if (/accounting_connections/.test(u) && method === 'PATCH') return reply(conn.status, conn.body);
    if (/accounting_consents/.test(u) && method === 'GET') return reply(consentsGet.status, consentsGet.body);
    return reply(200, []);
  };
  delete require.cache[require.resolve('./accounting.js')];
  return require('./accounting.js');
}

async function call(conn, consentsGet, action, payload) {
  const h = load(conn, consentsGet || { status: 200, body: [] });
  const res = mockRes();
  await h({
    method: 'POST',
    headers: {
      authorization: 'Bearer KEY-FOR-' + HASH,
      'x-sd-auth': signSessionToken({ app: 'sairnroofing', employee_id: 'emp-1', role: 'owner', license_hash: HASH })
    },
    body: { action: action, app_id: 'sairnroofing', payload: Object.assign({ today: '2026-10-21' }, payload) }
  }, res);
  return res;
}

const REV = { consent_id: 'C-1' };

(async function main() {
  section('R. REVOKE -- tokens_discarded is claimed only when the discard is confirmed');
  {
    let r = await call({ status: 200, body: [{ provider: 'quickbooks_online', status: 'revoked' }] }, null, 'revoke', REV);
    is(r.statusCode === 200 && r.body.tokens_discarded === true && r.body.connection_found === true,
       'R1. PATCH ok + a row matched -> 200 tokens_discarded:true', r.statusCode + ' ' + JSON.stringify(r.body));
    r = await call({ status: 200, body: [] }, null, 'revoke', REV);
    is(r.statusCode === 200 && r.body.tokens_discarded === false && r.body.connection_found === false,
       'R2. PATCH ok but ZERO rows (nothing was stored) -> 200 tokens_discarded:false, not true', r.statusCode + ' ' + JSON.stringify(r.body));
    r = await call({ status: 500, body: { message: 'boom' } }, null, 'revoke', REV);
    is(r.statusCode === 502 && r.body.error && r.body.error.code === 'TOKEN_DISCARD_UNCONFIRMED'
       && r.body.tokens_discarded === false && r.body.consent_revoked === true,
       'R3. THE DEFECT: PATCH fails (500) -> 502 TOKEN_DISCARD_UNCONFIRMED, never a 200 tokens_discarded:true',
       r.statusCode + ' ' + JSON.stringify(r.body));
    r = await call({ status: 400, body: { code: '23514', message: 'check violation' } }, null, 'revoke', REV);
    is(r.statusCode === 502 && r.body.error.code === 'TOKEN_DISCARD_UNCONFIRMED',
       'R4. a constraint 400 on the discard is UNCONFIRMED too -- not mistaken for a missing table',
       r.statusCode + ' ' + JSON.stringify(r.body));
    r = await call({ status: 404, body: { code: 'PGRST205', message: "Could not find the table 'public.accounting_connections'" } }, null, 'revoke', REV);
    is(r.statusCode === 200 && r.body.tokens_discarded === false && r.body.connection_found === false,
       'R5. connection table genuinely missing -> nothing stored -> 200 tokens_discarded:false', r.statusCode + ' ' + JSON.stringify(r.body));
  }

  section('L. STATUS -- only a MISSING relation is "not provisioned"');
  {
    let r = await call({ status: 200, body: [] }, { status: 404, body: { code: 'PGRST205', message: "Could not find the table 'public.accounting_consents'" } }, 'status', {});
    is(r.statusCode === 200 && r.body.provisioned === false,
       'L1. consents table missing -> provisioned:false (unchanged behaviour)', r.statusCode + ' ' + JSON.stringify(r.body).slice(0, 200));
    r = await call({ status: 200, body: [] }, { status: 400, body: { code: '42703', message: 'column accounting_consents.revoked_by does not exist' } }, 'status', {});
    is(r.statusCode === 502 && r.body.error && r.body.error.code === 'STATE_UNREADABLE',
       'L2. a 400 for a missing COLUMN (table exists) -> STATE_UNREADABLE, not "tables are not set up"',
       r.statusCode + ' ' + JSON.stringify(r.body).slice(0, 200));
    r = await call({ status: 200, body: [] }, { status: 400, body: { code: '22P02', message: 'invalid input syntax' } }, 'status', {});
    is(r.statusCode === 502 && r.body.error.code === 'STATE_UNREADABLE',
       'L3. an unrelated 400 -> STATE_UNREADABLE, not provisioned:false', r.statusCode + ' ' + JSON.stringify(r.body).slice(0, 200));
  }

  section('S. STRUCTURE -- the consent write classifies by body too');
  {
    const src = fs.readFileSync(SRC, 'utf8');
    is(/classifyUpstream\(w\.status, JSON\.stringify\(saved\)\)/.test(src)
       && !/w\.status === 404 \|\| w\.status === 400\) \{ res\.status\(503\)/.test(src),
       'S1. the consent write no longer maps every 404/400 to NOT_PROVISIONED', 'old shape present or new shape missing');
  }

  console.log('\n' + (fail ? 'FAILED' : 'PASSED') + ' -- ' + pass + ' passed, '
    + fail + ' failed' + (fail ? '\nFAILING ARMS: ' + failed.join(', ') : ''));
  process.exit(fail ? 1 : 0);
})().catch((e) => {
  console.error('HARNESS ERROR -- no verdict was reached, which is NOT a pass');
  console.error(e);
  process.exit(1);
});
