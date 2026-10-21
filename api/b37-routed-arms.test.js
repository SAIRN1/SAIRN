'use strict';
// b37 -- the three arms cc's b34 review routed to cody (SAIRN-handoff-cc-b34.md
// s3(a), restated in cc b35 s3(c)). Each states its concept before its code.
//
//   R  bld_draws/release_retainage with a FORGED blob draw_id
//      CONCEPT: the row's key comes from its column, never from its blob -- the
//      released draw, and the summary returned for it, are the column's draw.
//   P  sd_quote_requests/request_photos across TWO tenants
//      CONCEPT: a read returns only the caller's licence's rows -- the same
//      request id under another licence is not the caller's photo.
//      (Pattern: api/sairndental/complaint-respond.test.js -- the mock filters on
//      every eq. clause actually present, so dropping the licence filter fails.)
//   N  dnt_referrals write on a missing table
//      CONCEPT: a "not set up" message names the file that creates THIS table.
//
// R and P guard code that is already right (b33 / b34); they exist because
// cc showed that deleting the guard left every suite green. N fixes a gap.

const fs = require('fs');
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || ['b37', 'routed', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';
const { signSessionToken } = require('./_lib/auth');

const HASH_A = 'b37-tenant-A';
const HASH_B = 'b37-tenant-B';

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
  const f = {};
  (u.split('?')[1] || '').split('&').forEach((kv) => {
    const m = kv.match(/^([a-z_]+)=eq\.(.*)$/);
    if (m) f[m[1]] = decodeURIComponent(m[2]);
  });
  return f;
}
const matches = (row, f) => Object.keys(f).every((k) => String(row[k]) === f[k]);

// store: { table: [rows] }; missing: a table name that answers 404.
async function call(hash, app, resource, action, payload, store, missing) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = { exports: { validateLicenseKey: async () => ({
    valid: true, active: true, license_hash: hash, trial_ends_at: null, stripe_subscription_id: null, app_id: app }) } };
  const rpcCalls = [];
  global.fetch = async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    const reply = (s, b) => ({ ok: s >= 200 && s < 300, status: s, json: async () => b, text: async () => JSON.stringify(b) });
    if (/_employee_auth\?/.test(u)) return reply(200, [{ active: true, role: 'owner' }]);
    if (/\/rpc\/bld_release_retainage_atomic/.test(u)) {
      const b = JSON.parse(init.body);
      rpcCalls.push(b);
      return reply(200, [{ draw_id: b.p_draw_id, data: b.p_next_data }]);
    }
    const t = (u.match(/\/rest\/v1\/([a-z_0-9]+)/) || [])[1];
    if (missing && t === missing) return reply(404, { code: 'PGRST205', message: "Could not find the table 'public." + t + "' in the schema cache" });
    if (method === 'POST' || method === 'PATCH') {
      const b = JSON.parse(init.body);
      return reply(200, Array.isArray(b) ? b : [b]);
    }
    return reply(200, (store[t] || []).filter((r) => matches(r, eqFilters(u))).map((r) => JSON.parse(JSON.stringify(r))));
  };
  delete require.cache[require.resolve('./sd-data.js')];
  const h = require('./sd-data.js');
  const res = { statusCode: null, body: null };
  res.status = function (s) { res.statusCode = s; return res; };
  res.json = function (b) { res.body = b; return res; };
  const ce = console.error, cw = console.warn;
  console.error = function () {}; console.warn = function () {};
  try {
    await h({ method: 'POST', headers: { authorization: 'Bearer KEY-FOR-' + hash,
      'x-sd-auth': signSessionToken({ app: app, employee_id: 'emp-1', role: 'owner', license_hash: hash }) },
      body: { action: action, resource: resource, app_id: app, payload: payload } }, res);
  } finally { console.error = ce; console.warn = cw; }
  res.rpcCalls = rpcCalls;
  return res;
}
const show = (r) => r.statusCode + ' ' + JSON.stringify(r.body).slice(0, 260);

(async function main() {
  console.log('\nR. bld_draws/release_retainage -- a forged blob draw_id');
  {
    const store = { bld_draws: [{ license_hash: HASH_A, draw_id: 'DR-1', data: {
      draw_id: 'DR-FORGED', job_id: 'J-1', draw_no: 1, period_end: '2026-08-31', pct_complete: 100,
      amount: 100000, retainage_pct: 10, retainage_held: 10000,
      status: 'received', requested_at: '2026-08-01', amount_received: 100000 } }] };
    const r = await call(HASH_A, 'sairnbuild', 'bld_draws', 'release_retainage',
      { draw_id: 'DR-1', amount: 5000, released_at: '2026-10-21', today: '2026-10-21' }, store);
    is(r.statusCode === 200 && r.body.summary && r.body.summary.draw_id === 'DR-1',
       'R1. the summary returned for the release names the COLUMN draw (DR-1), not the blob\'s DR-FORGED', show(r));
    is(r.rpcCalls.length === 1 && r.rpcCalls[0].p_draw_id === 'DR-1',
       'R2. the atomic release is applied to the column draw', JSON.stringify(r.rpcCalls).slice(0, 200));
  }

  console.log('\nP. sd_quote_requests/request_photos -- two tenants, one request id');
  {
    const store = { sd_quote_request_photos: [
      { license_hash: HASH_A, request_id: 'QR-1', created_at: '2026-10-01', data: { slot: 1, photo_base64: 'data:image/jpeg;base64,AAA' } },
      { license_hash: HASH_B, request_id: 'QR-1', created_at: '2026-10-01', data: { slot: 1, photo_base64: 'data:image/jpeg;base64,BBB-OTHER-SHOP' } },
      { license_hash: HASH_B, request_id: 'QR-1', created_at: '2026-10-02', data: { slot: 2, photo_base64: 'data:image/jpeg;base64,CCC-OTHER-SHOP' } }
    ] };
    let r = await call(HASH_A, 'stonedesk', 'sd_quote_requests', 'request_photos', { id: 'QR-1' }, store);
    const blob = JSON.stringify(r.body);
    is(r.statusCode === 200 && r.body.data.length === 1 && blob.indexOf('AAA') !== -1 && blob.indexOf('OTHER-SHOP') === -1,
       'P1. licence A gets only its own photo, never licence B\'s under the same request id', show(r));
    r = await call(HASH_B, 'stonedesk', 'sd_quote_requests', 'request_photos', { id: 'QR-1' }, store);
    is(r.statusCode === 200 && r.body.data.length === 2 && JSON.stringify(r.body).indexOf('AAA') === -1,
       'P2. ...and the other way round', show(r));
  }

  console.log('\nN. dnt_referrals -- the not-set-up message names the file that creates it');
  {
    const r = await call(HASH_A, 'sairndental', 'dnt_referrals', 'write',
      { id: 'RF-1', patient_name: 'A. Patient', external_party: 'Dr Specialist', reason: 'endo consult', direction: 'outgoing', status: 'Pending', date: '2026-10-21' }, {}, 'dnt_referrals');
    const m = (r.body && r.body.error && r.body.error.message) || '';
    is(r.statusCode === 503 && m.indexOf('sql/sairndental_referrals_schema.sql') !== -1 && m.indexOf('sairndental_data_schema.sql') === -1,
       'N1. a missing dnt_referrals table names sql/sairndental_referrals_schema.sql, not the data schema (which does not create it)', show(r));
    const created = fs.readFileSync(__dirname + '/../sql/sairndental_referrals_schema.sql', 'utf8');
    is(/create table (if not exists )?(public\.)?dnt_referrals\b/i.test(created),
       'N2. and that file really does create dnt_referrals', 'no create table dnt_referrals in the named file');
  }

  console.log('\n' + (fail ? 'FAILED' : 'PASSED') + ' -- ' + pass + ' passed, '
    + fail + ' failed' + (fail ? '\nFAILING ARMS: ' + failed.join(', ') : ''));
  process.exit(fail ? 1 : 0);
})().catch((e) => {
  console.error('HARNESS ERROR -- no verdict was reached, which is NOT a pass');
  console.error(e);
  process.exit(1);
});
