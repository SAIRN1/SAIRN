// tests/provisioning_attribution.js
//
// REQUIREMENT: a management-gated action that grants access, revokes access or
//   changes a money field must record WHICH EMPLOYEE did it, and must say so on
//   the response when the record could not be written.
//
// WHY. Measured at HEAD 0f1f845b, 2026-10-07, across every api/*-auth.js:
//
//   17 files have a `setup` action (the act of CREATING a credential)
//   16 of 17 recorded NEITHER an audit row NOR a created_by
//    1 of 17 -- law-auth.js -- already audited it
//
// And REVOKING was audited where GRANTING was not: `set_active` in sc-auth.js
// and sd-auth.js audits every outcome including its refusals. That is the
// loud-in-one-direction-silent-on-its-mirror shape, in the branch where the
// asymmetry matters most.
//
// Same for `api/stonedesk-track.js` `create` and `revoke` -- which issue and
// withdraw a PUBLIC UNAUTHENTICATED URL into a customer's order -- and for
// `api/sd-sub-data.js` `roster`/`write` and `jobs`/`write`, where a pay-status
// change had no author while `progress_photos`/`write` in the SAME FILE already
// stored captured_by_id three branches away.
//
// ── WHAT IS FIXED HERE AND WHAT IS NOT, because 16 of 17 is not what landed ──
// Only 3 of the 17 apps have an audit log at all. `api/_lib/audit.js:40`
// allowlists exactly three tables: sairnlaw, sairncode, stonedesk. The other 14
// apps would need a per-app audit table, which is a MIGRATION this session
// cannot run. So:
//
//   FIXED  sc-auth.js setup        audit row, sairncode_audit_log
//   FIXED  sd-auth.js setup        audit row, stonedesk_audit_log
//   FIXED  stonedesk-track create  audit row
//   FIXED  stonedesk-track revoke  audit row
//   FIXED  sd-sub-data roster      audit row
//   FIXED  sd-sub-data jobs        updatedBy IN THE BLOB -- no migration at all
//   OPEN   the other 14 *-auth.js  no audit table exists; needs a migration
//
// That is stated here rather than left for a reader to infer from a green bar.
//
// REAL: the handlers and the auth module. MOCKED: fetch, validateLicenseKey.
// NOT RUN: the live round trip, so no audit row is ever really stored -- what
// is asserted is the outbound REQUEST the handler issued, which is the only
// mechanical proof that attribution happened (sairn-api-tester section 7).
//
// MUTATION PROOF: against the parent commit every arm in B, C, D and E goes red.
//
// Run:  node tests/provisioning_attribution.js

'use strict';
const path = require('path');
const ROOT = path.join(__dirname, '..');

const LIC_HASH = 'hash-of-the-attribution-licence';
function stubLicence(appId) {
  const p = require.resolve(path.join(ROOT, 'api/_lib/license.js'));
  require.cache[p] = {
    id: p, filename: p, loaded: true,
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: LIC_HASH,
        stripe_subscription_id: 'sub_1', trial_ends_at: null, app_id: appId
      }),
      hashLicense: () => LIC_HASH,
    },
  };
}

process.env.SUPABASE_URL = 'https://example.invalid';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'service-role-for-the-test';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || 'provisioning-attribution-test-secret';
const { signSessionToken } = require(path.join(ROOT, 'api/_lib/auth.js'));

// Every outbound request is recorded with its BODY, because the whole question
// is what the handler ASKED FOR and not what it answered.
let sent = [];
let failAudit = false;
global.fetch = async (url, opts) => {
  const u = String(url);
  let body = null;
  try { body = opts && opts.body ? JSON.parse(opts.body) : null; } catch (e) { body = null; }
  sent.push({ url: u, method: (opts && opts.method) || 'GET', body: body });
  const ok = (rows) => ({ ok: true, status: 200, json: async () => rows,
                          text: async () => '' });
  if (/_audit_log/.test(u)) {
    if (failAudit) {
      return { ok: false, status: 500, json: async () => ({}),
               text: async () => 'audit down' };
    }
    return ok([]);
  }
  if (/_employee_auth\?/.test(u)) {
    return ok([{ employee_id: 'TARGET-1', role: 'admin', active: true,
                 pin_hash: 'x', pin_salt: 'y' }]);
  }
  if (/sd_customers\?/.test(u)) return ok([{ customer_id: 'CUST-1' }]);
  if (/sd_order_links/.test(u)) return ok([{ link_id: 'OL-1', active: false }]);
  if (/sd_subs\?/.test(u) || /sd_subs\b/.test(u)) return ok([{ sub_id: 'SUB-1' }]);
  if (/sd_sub_jobs/.test(u)) return ok([{ id: 'J1', data: {} }]);
  return ok([]);
};

// `setHeader` and `end` are here because api/stonedesk-track.js sets CORS
// headers and 204s a preflight -- the first run of this file died on
// `res.setHeader is not a function` at :78. A fake response that is narrower
// than the real one does not weaken an assertion, it stops the run, which is
// the loud direction and is why it was found immediately.
function fakeRes() {
  const r = { statusCode: null, body: null, headers: {}, ended: false };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  r.setHeader = (k, v) => { r.headers[k] = v; return r; };
  r.end = () => { r.ended = true; return r; };
  return r;
}
function fresh(rel) {
  const p = require.resolve(path.join(ROOT, rel));
  delete require.cache[p];
  return require(p);
}
const auditRows = () => sent.filter((q) => /_audit_log/.test(q.url)
  && q.method === 'POST');

let pass = 0, fail = 0;
function ok(l) { pass++; console.log('  ok   ' + l); }
function bad(l, why) {
  fail++;
  console.log('  FAIL ' + l);
  if (why) console.log('       ' + String(why).slice(0, 400));
}

async function post(rel, appId, bodyObj, sessApp, role, employeeId) {
  stubLicence(appId);
  const handler = fresh(rel);
  sent = [];
  const headers = { authorization: 'Bearer ATTR-TEST-KEY' };
  if (sessApp) {
    headers['x-sd-auth'] = signSessionToken({
      app: sessApp, employee_id: employeeId || 'ACTOR-7', role: role,
      license_hash: LIC_HASH });
  }
  const req = { method: 'POST', headers: headers, body: bodyObj };
  const res = fakeRes();
  await handler(req, res);
  return res;
}

(async function main() {
  console.log('PROVISIONING / MANAGEMENT-WRITE ATTRIBUTION -- criteria 2026-10-07.1\n');

  console.log('A. THE MEASUREMENT THIS BATCH ACTED ON, re-derived from the tree');
  {
    const fs = require('fs');
    const dir = path.join(ROOT, 'api');
    const files = fs.readdirSync(dir).filter((f) => /^[a-z-]+-auth\.js$/.test(f));
    let withSetup = 0, attributed = 0;
    const unattributed = [];
    files.forEach((f) => {
      const src = fs.readFileSync(path.join(dir, f), 'utf8');
      const key = "action === 'setup'";
      if (src.indexOf(key) === -1) return;
      withSetup++;
      const i = src.indexOf(key);
      const j = src.indexOf('if (action ===', i + 10);
      const blk = src.slice(i, j === -1 ? src.length : j);
      if (/writeAuditLog\(/.test(blk) || /\baudit\(/.test(blk)
          || /created_by/.test(blk)) attributed++;
      else unattributed.push(f);
    });
    if (withSetup === 17) {
      ok('A1. 17 api/*-auth.js files carry a `setup` action. Pinned as a FLOOR '
         + 'in A2 rather than as an equality, because a new vertical adding one '
         + 'is legitimate growth and must not turn this arm red');
    } else {
      bad('A1. expected 17 files with a setup action, found ' + withSetup, '');
    }
    if (attributed >= 3) {
      ok('A2. at least 3 of them now attribute the grant (law-auth.js already '
         + 'did; sc-auth.js and sd-auth.js are this batch). ' + unattributed.length
         + ' still do not, and that is NOT a failure of this arm -- they are the '
         + 'apps with no audit table, listed in this file\'s header as OPEN');
    } else {
      bad('A2. at least three setup branches must attribute -- found '
          + attributed, 'unattributed: ' + unattributed.join(', '));
    }
  }

  console.log('\nB. sc-auth.js `setup` -- SAIRNcode, the act of granting access');
  {
    const r = await post('api/sc-auth.js', 'sairncode',
      { action: 'setup', license_key: 'K', employee_id: 'TARGET-1',
        pin: '246810', role: 'coder', display_name: 'T' },
      'sairncode', 'admin', 'ACTOR-7');
    const a = auditRows();
    const row = a[0] && a[0].body;
    if (r.statusCode === 200 && a.length === 1
        && row.employee_id === 'ACTOR-7' && row.role === 'admin'
        && row.event_type === 'pin_setup'
        && row.detail && row.detail.target === 'TARGET-1') {
      ok('B1. exactly ONE audit row, naming the ACTOR (ACTOR-7/admin) and the '
         + 'TARGET separately. Asserted on the OUTBOUND REQUEST, not the '
         + 'response -- the response would look identical if nothing were '
         + 'written');
    } else {
      bad('B1. setup must write one audit row naming the actor',
          'status=' + r.statusCode + ' rows=' + a.length + ' body='
          + JSON.stringify(row));
    }
    if (r.body && r.body.attributed === true) {
      ok('B2. ...and the response says attributed:true');
    } else {
      bad('B2. the response must declare the attribution',
          'attributed=' + JSON.stringify(r.body && r.body.attributed));
    }
  }

  console.log('\nC. AN AUDIT THAT FAILS SAYS SO -- the silent-failure half');
  {
    failAudit = true;
    const r = await post('api/sc-auth.js', 'sairncode',
      { action: 'setup', license_key: 'K', employee_id: 'TARGET-1',
        pin: '246810', role: 'coder', display_name: 'T' },
      'sairncode', 'admin', 'ACTOR-7');
    failAudit = false;
    if (r.statusCode === 200 && r.body && r.body.attributed === false) {
      ok('C1. the credential is STILL created (200) and the response says '
         + 'attributed:FALSE. writeAuditLog is deliberately non-fatal and '
         + 'returns false, so without this flag an unrecorded attribution and a '
         + 'recorded one are indistinguishable -- which is the defect being '
         + 'fixed, one level down. An unavailable audit log must not block a '
         + 'legitimate grant, and must not be able to pretend it worked');
    } else {
      bad('C1. a failed audit must surface as attributed:false, not block',
          'status=' + r.statusCode + ' attributed='
          + JSON.stringify(r.body && r.body.attributed));
    }
  }

  console.log('\nD. stonedesk-track -- a PUBLIC unauthenticated URL, issued and withdrawn');
  {
    let r = await post('api/stonedesk-track.js', 'stonedesk',
      { action: 'create', license_key: 'K', customer_id: 'CUST-1', label: 'L' },
      'stonedesk', 'owner', 'ACTOR-9');
    let a = auditRows();
    let row = a[0] && a[0].body;
    if (r.statusCode === 200 && a.length === 1
        && row.employee_id === 'ACTOR-9'
        && row.event_type === 'order_link_created'
        && row.detail && row.detail.customer_id === 'CUST-1') {
      ok('D1. `create` audits the issuing employee and the customer');
    } else {
      bad('D1. create must audit the acting employee',
          'status=' + r.statusCode + ' rows=' + a.length + ' body='
          + JSON.stringify(row));
    }
    const tok = r.body && r.body.token;
    if (tok && JSON.stringify(a).indexOf(tok) === -1) {
      ok('D2. ...and the BEARER TOKEN is NOT in the audit detail. It is the '
         + 'secret for an unauthenticated URL and an audit log is read by more '
         + 'people than the one who issued it; link_id identifies the row '
         + 'without reproducing the credential');
    } else {
      bad('D2. the token must not be written into the audit trail',
          'token present in audit detail');
    }
    r = await post('api/stonedesk-track.js', 'stonedesk',
      { action: 'revoke', license_key: 'K', link_id: 'OL-1' },
      'stonedesk', 'owner', 'ACTOR-9');
    a = auditRows();
    row = a[0] && a[0].body;
    if (r.statusCode === 200 && a.length === 1
        && row.event_type === 'order_link_revoked'
        && row.employee_id === 'ACTOR-9') {
      ok('D3. `revoke` audits too, and AFTER the 404 check -- a revoke that '
         + 'matched no row did not happen, and logging it would put an event in '
         + 'the trail for an action that never occurred');
    } else {
      bad('D3. revoke must audit the acting employee',
          'status=' + r.statusCode + ' rows=' + a.length + ' body='
          + JSON.stringify(row));
    }
  }

  console.log('\nE. sd-sub-data -- the blob route, and it is SERVER-STAMPED');
  {
    const r = await post('api/sd-sub-data.js', 'stonedesk',
      { action: 'write', resource: 'jobs',
        payload: { sub_id: 'SUB-1', amount: 1200,
                   updatedBy: 'SOMEONE-ELSE', updatedByRole: 'owner' } },
      'stonedesk', 'admin', 'ACTOR-3');
    const w = sent.filter((q) => /sd_sub_jobs/.test(q.url)
      && (q.method === 'POST' || q.method === 'PATCH'));
    const d = w[0] && w[0].body && w[0].body.data;
    if (r.statusCode === 200 && d && d.updatedBy === 'ACTOR-3'
        && d.updatedByRole === 'admin') {
      ok('E1. the stored blob carries updatedBy=ACTOR-3 from the SESSION, and '
         + 'the caller-supplied updatedBy:SOMEONE-ELSE was DISCARDED. storedBlob '
         + 'only strips the keys it is told to, so a hostile value would have '
         + 'survived -- these two lines are written after it, which is the only '
         + 'thing that makes the field evidence rather than a request');
    } else {
      bad('E1. jobs/write must server-stamp the acting employee',
          'status=' + r.statusCode + ' data=' + JSON.stringify(d));
    }
    if (d && d.updatedAt) {
      ok('E2. ...beside the updatedAt that was already there. WHEN had an '
         + 'answer and WHO did not, in the same object');
    } else {
      bad('E2. updatedAt must still be stamped', JSON.stringify(d));
    }
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
