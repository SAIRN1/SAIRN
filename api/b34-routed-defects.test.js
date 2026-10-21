'use strict';
// b34 -- cc's b29 routed defects 1, 2 and 5 (docs/2026-10-20-cc-b29-notes.md s1).
//
// CONCEPT (stated before the code): an error or an absence must be reported as
// the thing it is -- a "not set up" message names the file that creates THIS
// table, a missing table on a write is a 503 and not a retryable 502, and a
// stored value needs one authorised path that returns it.
//
//   D1  dental generic write: the 503 names the right schema file per resource
//   D2  rf_prequal_documents / rf_bonding write on a missing table -> 503
//   D5  sd_quote_requests/request_photos returns the stored intake photos

const fs = require('fs');
const path = require('path');
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || ['b34', 'routed', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';
const { signSessionToken } = require('./_lib/auth');

const HASH = 'b34-routed-hash';
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
function section(t) { console.log('\n' + t); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}

const MISSING = { code: 'PGRST205', message: "Could not find the table 'public.x' in the schema cache" };
const PHOTO_ROWS = [
  { data: { slot: 1, photo_base64: 'data:image/jpeg;base64,AAA' } },
  { data: { slot: 2, photo_base64: 'data:image/jpeg;base64,BBB' } }
];

// `missingTable` = a substring of the URL for which the data store answers 404.
function pgMock(role, missingTable) {
  return async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    const reply = (st, b) => ({ ok: st >= 200 && st < 300, status: st,
      json: async () => b, text: async () => JSON.stringify(b) });
    if (/_employee_auth/.test(u)) {
      const m = u.match(/employee_id=eq\.([^&]+)/);
      return reply(200, [{ license_hash: HASH, employee_id: m ? decodeURIComponent(m[1]) : 'emp-1', role: role, active: true }]);
    }
    if (missingTable && u.indexOf(missingTable) !== -1) return reply(404, MISSING);
    if (/sd_quote_request_photos/.test(u)) return reply(200, PHOTO_ROWS);
    if (method === 'POST' || method === 'PATCH') {
      let p = {}; try { p = JSON.parse(init.body); } catch (e) { p = {}; }
      return reply(200, Array.isArray(p) ? p : [p]);
    }
    return reply(200, []);
  };
}

async function call(app, role, resource, action, payload, missingTable) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: { validateLicenseKey: async () => ({
      valid: true, active: true, license_hash: HASH, trial_ends_at: null,
      stripe_subscription_id: null, app_id: app }) }
  };
  global.fetch = pgMock(role, missingTable);
  delete require.cache[require.resolve('./sd-data.js')];
  const h = require('./sd-data.js');
  const res = mockRes();
  await h({
    method: 'POST',
    headers: { authorization: 'Bearer ' + KEY,
      'x-sd-auth': signSessionToken({ app: app, employee_id: 'emp-1', role: role, license_hash: HASH }) },
    body: { action: action, resource: resource, payload: payload }
  }, res);
  return res;
}
const msg = (r) => (r.body && r.body.error && r.body.error.message) || '';
const code = (r) => (r.body && r.body.error && r.body.error.code) || '';

(async function main() {
  section('D1. the dental "not set up" message names the file that creates THIS table');
  for (const [resource, file] of [
    ['dnt_gfe', 'sairndental_gfe_schema.sql'],
    ['dnt_recall_outreach', 'sairndental_recall_schema.sql'],
    ['dnt_txplans', 'sairndental_treatment_plans_schema.sql'],
    ['dnt_patients', 'sairndental_data_schema.sql']
  ]) {
    const r = await call('sairndental', 'owner', resource, 'write', { id: 'X-1', patient_id: 'P-1', procedure_type_id: 'PT-1', title: 'Plan', items: [{ procedure_type_id: 'PT-1', description: 'x', fee: 100, qty: 1 }], on: '2026-10-21', channel: 'phone', outcome: 'booked', status: 'proposed', dob: '1980-01-01' }, resource + '?on_conflict');
    is(r.statusCode === 503 && code(r) === 'NOT_PROVISIONED' && msg(r).indexOf(file) !== -1,
       'D1[' + resource + ']. 503 NOT_PROVISIONED naming ' + file, r.statusCode + ' ' + code(r) + ' ' + msg(r));
  }
  {
    const r = await call('sairndental', 'owner', 'dnt_gfe', 'write', { id: 'X-1', patient_id: 'P-1' }, 'dnt_gfe?on_conflict');
    is(msg(r).indexOf('sairndental_data_schema.sql') === -1,
       'D1x. CONTROL: the dnt_gfe message no longer sends the user to the data schema, which does not create it', msg(r));
  }

  section('D2. rf_prequal_documents / rf_bonding write on a missing table');
  {
    let r = await call('sairnroofing', 'owner', 'rf_prequal_documents', 'write',
      { document_id: 'D-1', kind: 'w9' }, 'rf_prequal_documents?on_conflict');
    is(r.statusCode === 503 && code(r) === 'NOT_PROVISIONED' && msg(r).indexOf('sairnroofing_prequal_schema.sql') !== -1,
       'D2a. prequal write, table missing -> 503 NOT_PROVISIONED naming the schema file (was a generic 502)',
       r.statusCode + ' ' + code(r) + ' ' + msg(r));
    r = await call('sairnroofing', 'owner', 'rf_bonding', 'write', { bonding_id: 'B-1' }, 'rf_bonding?on_conflict');
    is(r.statusCode === 503 && code(r) === 'NOT_PROVISIONED' && msg(r).indexOf('sairnroofing_prequal_schema.sql') !== -1,
       'D2b. bonding write, table missing -> 503 NOT_PROVISIONED naming the schema file (was a generic 502)',
       r.statusCode + ' ' + code(r) + ' ' + msg(r));
    r = await call('sairnroofing', 'owner', 'rf_bonding', 'write', { bonding_id: 'B-1' }, null);
    is(r.statusCode === 200 && r.body.ok === true, 'D2c. CONTROL: a bonding write on a present table still succeeds',
       r.statusCode + ' ' + JSON.stringify(r.body).slice(0, 200));
  }

  section('D5. sd_quote_requests / request_photos');
  {
    let r = await call('stonedesk', 'owner', 'sd_quote_requests', 'request_photos', { id: 'QR-1' }, null);
    is(r.statusCode === 200 && r.body.data && r.body.data.length === 2
       && r.body.data[0].slot === 1 && r.body.data[1].photo_base64.indexOf('BBB') !== -1,
       'D5a. owner gets the stored photos, in slot order', r.statusCode + ' ' + JSON.stringify(r.body).slice(0, 200));
    r = await call('stonedesk', 'owner', 'sd_quote_requests', 'request_photos', {}, null);
    is(r.statusCode === 400 && code(r) === 'ID_REQUIRED', 'D5b. no request id -> 400 ID_REQUIRED', r.statusCode + ' ' + code(r));
    r = await call('stonedesk', 'sales', 'sd_quote_requests', 'request_photos', { id: 'QR-1' }, null);
    is(r.statusCode === 403, 'D5c. a role that cannot work the requests is refused (403), same gate as read', r.statusCode + ' ' + code(r));
    r = await call('stonedesk', 'owner', 'sd_quote_requests', 'request_photos', { id: 'QR-1' }, 'sd_quote_request_photos');
    is(r.statusCode === 200 && r.body.provisioned === false && Array.isArray(r.body.data) && r.body.data.length === 0,
       'D5d. photos table not provisioned -> 200 provisioned:false with no photos', r.statusCode + ' ' + JSON.stringify(r.body).slice(0, 200));
  }

  console.log('\n' + (fail ? 'FAILED' : 'PASSED') + ' -- ' + pass + ' passed, '
    + fail + ' failed' + (fail ? '\nFAILING ARMS: ' + failed.join(', ') : ''));
  process.exit(fail ? 1 : 0);
})().catch((e) => {
  console.error('HARNESS ERROR -- no verdict was reached, which is NOT a pass');
  console.error(e);
  process.exit(1);
});
