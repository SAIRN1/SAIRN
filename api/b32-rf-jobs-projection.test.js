'use strict';
// b32 -- rf_jobs: THE REAL COLUMNS ARE THE LAST SOURCE IN BOTH PROJECTIONS.
//
// CONCEPT (stated before the code): a projection that tells the client who a
// job is assigned to, and which branch owns it, must apply the authoritative
// columns LAST, so the server's value wins by construction and not only
// because a strip list on the write path happens to keep the competing blob
// copy from ever existing. Source: docs/2026-10-19-fourth-b37-tier-a-review.md
// section 7.1. Both orders were inverted (blob won); rf_claims' read was not.
//
// EVERY ARM HERE IS BEHAVIOURAL EXCEPT S1, and S1 exists because the WRITE
// response cannot be reached behaviourally while the strip is intact: with
// storedBlob removing all four keys there is no blob copy to win. So W1 runs
// the real handler from a COPY of sd-data.js with the strip emptied -- the
// condition the review named ("remove one name from that list") -- and asserts
// the response still carries the server-resolved columns. The copy is deleted
// in a finally.

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || ['b32', 'projection', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const fs = require('fs');
const path = require('path');
const { signSessionToken } = require('./_lib/auth');

const HASH = 'b32-projection-hash';
const KEY = 'KEY-FOR-' + HASH;
const SD_DATA = path.join(__dirname, 'sd-data.js');
const ABLATED = path.join(__dirname, '_b32_strip_ablated_sd_data.tmp.js');

let pass = 0, fail = 0;
const failed = [];
function ok(l) { pass++; console.log('  ok    ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL  ' + l);
  if (why) console.log('        ' + String(why).slice(0, 900));
}
function is(cond, label, detail) { if (cond) ok(label); else bad(label, detail); }
function section(t) { console.log('\n' + t); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}

// What the database holds. `data` carries a TAMPERED copy of all four keys:
// the state a missing strip-list entry would have left behind.
const STORED = {
  job_id: 'JOB-REAL', job_class: 'commercial',
  assigned_employee_id: 'emp-real', location_id: 'LOC-REAL',
  data: { id: 'EVIL-ID', job_class: 'EVIL-CLASS',
          assigned_employee_id: 'EVIL-ASSIGNEE', location_id: 'EVIL-LOC',
          name: 'Roof tear-off', address: '1 Main St' }
};

function pgMock() {
  return async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    if (/_employee_auth/.test(u)) {
      const m = u.match(/employee_id=eq\.([^&]+)/);
      return { ok: true, status: 200, json: async () => [
        { license_hash: HASH, employee_id: m ? decodeURIComponent(m[1]) : 'emp-1',
          role: 'owner', active: true }] };
    }
    if (method === 'POST' || method === 'PATCH') {
      let parsed = null;
      try { parsed = JSON.parse(init.body); } catch (e) { parsed = {}; }
      return { ok: true, status: 200,
               json: async () => (Array.isArray(parsed) ? parsed : [parsed]) };
    }
    if (/rf_jobs/.test(u)) return { ok: true, status: 200, json: async () => [STORED] };
    return { ok: true, status: 200, json: async () => [] };
  };
}

function load(file) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: HASH,
        trial_ends_at: null, stripe_subscription_id: null, app_id: 'sairnroofing' })
    }
  };
  global.fetch = pgMock();
  delete require.cache[require.resolve(file)];
  return require(file);
}

async function call(file, action, payload) {
  const h = load(file);
  const res = mockRes();
  await h({
    method: 'POST',
    headers: {
      authorization: 'Bearer ' + KEY,
      'x-sd-auth': signSessionToken({
        app: 'sairnroofing', employee_id: 'emp-1', role: 'owner', license_hash: HASH })
    },
    body: { action: action, resource: 'rf_jobs', payload: payload }
  }, res);
  return res;
}

(async function main() {
  section('R. THE READ PROJECTION');
  {
    const res = await call(SD_DATA, 'read', {});
    const row = res.body && res.body.data && res.body.data[0];
    is(res.statusCode === 200 && !!row, 'R0. the read answers 200 with a row',
       res.statusCode + ' ' + JSON.stringify(res.body).slice(0, 200));
    is(row && row.id === 'JOB-REAL' && row.job_class === 'commercial'
       && row.assigned_employee_id === 'emp-real' && row.location_id === 'LOC-REAL',
       'R1. a blob copy of id / job_class / assigned_employee_id / location_id '
       + 'does NOT override the stored columns',
       JSON.stringify(row));
    is(row && row.name === 'Roof tear-off' && row.address === '1 Main St',
       'R2. CONTROL: ordinary blob fields still flow through -- the flip did not '
       + 'drop the overlay', JSON.stringify(row));
  }

  section('W. THE WRITE RESPONSE, WITH THE STRIP LIST EMPTIED');
  try {
    const src = fs.readFileSync(SD_DATA, 'utf8');
    const strip = "storedBlob(payload, ['id', 'job_class', 'assigned_employee_id', 'location_id'])";
    is(src.split(strip).length === 2,
       'W0. the strip call is present exactly once in the real file, so the '
       + 'ablated copy removes the right thing', 'count=' + (src.split(strip).length - 1));
    fs.writeFileSync(ABLATED, src.replace(strip, 'Object.assign({}, payload)'));
    const res = await call(ABLATED, 'write', {
      id: 'JOB-W', name: 'n', job_class: 'EVIL-CLASS' });
    const d = res.body && res.body.data;
    is(res.statusCode === 200 && !!d, 'W1a. the ablated handler answers 200',
       res.statusCode + ' ' + JSON.stringify(res.body).slice(0, 300));
    is(d && d.job_class === 'residential' && d.id === 'JOB-W',
       'W1. with the strip emptied the response STILL carries the server-resolved '
       + 'job_class (residential, not the payload\'s EVIL-CLASS) and id',
       JSON.stringify(d));
  } finally {
    try { fs.unlinkSync(ABLATED); } catch (e) { /* nothing to remove */ }
    delete require.cache[ABLATED];
  }

  section('S. STRUCTURE');
  {
    const src = fs.readFileSync(SD_DATA, 'utf8');
    is(/Object\.assign\(\{\}, r\.data \|\| \{\}, \{ id: r\.job_id/.test(src)
       && /Object\.assign\(\{\}, jobData, \{ id: payload\.id, job_class: jobClass/.test(src),
       'S1. both rf_jobs projections put the blob FIRST and the columns LAST',
       'neither expected shape found');
  }

  console.log('\n' + (fail ? 'FAILED' : 'PASSED') + ' -- ' + pass + ' passed, '
    + fail + ' failed' + (fail ? '\nFAILING ARMS: ' + failed.join(', ') : ''));
  process.exit(fail ? 1 : 0);
})().catch((e) => {
  try { fs.unlinkSync(ABLATED); } catch (x) { /* none */ }
  console.error('HARNESS ERROR -- no verdict was reached, which is NOT a pass');
  console.error(e);
  process.exit(1);
});
