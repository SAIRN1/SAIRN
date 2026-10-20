'use strict';
// b33 -- THE SWEEP FOR INVERTED Object.assign(columns, blob) PROJECTIONS.
//
// CONCEPT (stated before the code): in Object.assign(a, b) the LATER source wins,
// so a projection that lists the authoritative columns FIRST and a stored or
// client-supplied blob LAST lets the blob override the server's value; the
// sweep finds every keyed literal that precedes a non-literal source, then each
// hit is classified by hand -- a hit is LIVE only if the blob can actually carry
// that key, and INERT if the write path allowlists or strips it.
//
// This file pins the four sites that were LIVE. Every arm plants a forged value
// in the blob / client payload and asserts the column or server-stamped value
// is what comes back. Scratch-scanner results and the full classification are
// in docs/2026-10-20-cody-b33-notes.md.

const fs = require('fs');
const path = require('path');
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || ['b33', 'sweep', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';
const { signSessionToken } = require('./_lib/auth');

const HASH = 'b33-sweep-hash';
const KEY = 'KEY-FOR-' + HASH;
const SD_DATA = path.join(__dirname, 'sd-data.js');
const SD_SUB = path.join(__dirname, 'sd-sub-data.js');

let pass = 0, fail = 0;
const failed = [];
function ok(l) { pass++; console.log('  ok    ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL  ' + l);
  if (why) console.log('        ' + String(why).slice(0, 700));
}
function is(c, l, d) { if (c) ok(l); else bad(l, d); }
function section(t) { console.log('\n' + t); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}

// What each table "holds" for the rows these arms read. `data` is the blob and
// carries FORGED copies of keys that are real columns.
const DRAW_ROW = { draw_id: 'DRAW-REAL', data: { draw_id: 'DRAW-FORGED', total: 1000 } };
const PHOTO_ROW = {
  id: 'PH-1', job_id: 'J-1', captured_by_type: 'employee', captured_by_id: 'emp-1',
  is_final: false, qc_status: 'pending', qc_reviewer_id: null, qc_notes: null,
  qc_reviewed_at: null, created_at: '2026-01-02T03:04:05Z',
  data: { created_at: '1999-01-01T00:00:00Z', note: 'ordinary field' }
};

function pgMock(role) {
  return async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    if (/_employee_auth/.test(u)) {
      const m = u.match(/employee_id=eq\.([^&]+)/);
      return { ok: true, status: 200, json: async () => [
        { license_hash: HASH, employee_id: m ? decodeURIComponent(m[1]) : 'emp-1',
          role: role, active: true }] };
    }
    if (method === 'POST' || method === 'PATCH') {
      let parsed = {};
      try { parsed = JSON.parse(init.body); } catch (e) { parsed = {}; }
      return { ok: true, status: 200, json: async () => (Array.isArray(parsed) ? parsed : [parsed]) };
    }
    if (/bld_draws/.test(u)) return { ok: true, status: 200, json: async () => [DRAW_ROW] };
    if (/sd_progress_photos/.test(u)) return { ok: true, status: 200, json: async () => [PHOTO_ROW] };
    return { ok: true, status: 200, json: async () => [] };
  };
}

function load(file, app, role) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: HASH,
        trial_ends_at: null, stripe_subscription_id: null, app_id: app })
    }
  };
  global.fetch = pgMock(role);
  delete require.cache[require.resolve(file)];
  return require(file);
}

async function call(file, app, tokenApp, role, resource, action, payload) {
  const h = load(file, app, role);
  const res = mockRes();
  await h({
    method: 'POST',
    headers: {
      authorization: 'Bearer ' + KEY,
      'x-sd-auth': signSessionToken({
        app: tokenApp, employee_id: 'emp-1', role: role, license_hash: HASH })
    },
    body: { action: action, resource: resource, payload: payload }
  }, res);
  return res;
}

const AUTH = { citation: 'Test Code 1.1', url: 'https://example.org/rule' };

(async function main() {
  section('A. alf_payer_rules WRITE RESPONSE -- client payload.data must not override the server-stamped fields');
  {
    const res = await call(SD_DATA, 'sairncare', 'sairncare', 'owner', 'alf_payer_rules', 'write', {
      rule_id: 'R-1', state: 'tx', program: 'medicaid_hcbs', effective_from: '2026-01-01',
      data: { authority: AUTH, verified_by: 'FORGED-VERIFIER', state: 'ZZ', rule_id: 'FORGED-RULE', note: 'keep me' } });
    const d = res.body && res.body.data;
    is(res.statusCode === 200 && !!d, 'A0. the write answers 200', res.statusCode + ' ' + JSON.stringify(res.body).slice(0, 300));
    is(d && d.verified_by === 'emp-1' && d.state === 'TX' && d.rule_id === 'R-1',
       'A1. verified_by / state / rule_id in the response are the server\'s (emp-1 / TX / R-1), not the forged copies',
       JSON.stringify(d));
    is(d && d.note === 'keep me' && d.authority && d.authority.citation === 'Test Code 1.1',
       'A2. CONTROL: ordinary blob fields still flow through', JSON.stringify(d));
  }

  section('B. alf_compliance_rules WRITE RESPONSE');
  {
    const res = await call(SD_DATA, 'sairncare', 'sairncare', 'owner', 'alf_compliance_rules', 'write', {
      rule_id: 'C-1', state: 'tx', requirement_type: 'staffing', effective_from: '2026-01-01',
      data: { authority: AUTH, verified_by: 'FORGED-VERIFIER', state: 'ZZ', rule_id: 'FORGED-RULE', note: 'keep me' } });
    const d = res.body && res.body.data;
    is(res.statusCode === 200 && !!d, 'B0. the write answers 200', res.statusCode + ' ' + JSON.stringify(res.body).slice(0, 300));
    is(d && d.verified_by === 'emp-1' && d.state === 'TX' && d.rule_id === 'C-1',
       'B1. verified_by / state / rule_id in the response are the server\'s, not the forged copies', JSON.stringify(d));
    is(d && d.note === 'keep me', 'B2. CONTROL: ordinary blob fields still flow through', JSON.stringify(d));
  }

  section('C. bld_draws wip -- a blob draw_id must not replace the row key');
  {
    const res = await call(SD_DATA, 'sairnbuild', 'sairnbuild', 'owner', 'bld_draws', 'wip', { today: '2026-10-20' });
    const txt = JSON.stringify(res.body);
    is(res.statusCode === 200, 'C0. wip answers 200', res.statusCode + ' ' + txt.slice(0, 300));
    is(txt.indexOf('DRAW-REAL') !== -1 && txt.indexOf('DRAW-FORGED') === -1,
       'C1. the response names the row\'s real draw_id (DRAW-REAL) and never the blob\'s DRAW-FORGED', txt.slice(0, 400));
  }

  section('D. sd-sub-data progress_photos read -- a blob created_at must not replace the column');
  {
    const res = await call(SD_SUB, 'stonedesk', 'stonedesk', 'owner', 'progress_photos', 'read', {});
    const row = res.body && res.body.data && res.body.data[0];
    is(res.statusCode === 200 && !!row, 'D0. the read answers 200 with a row', res.statusCode + ' ' + JSON.stringify(res.body).slice(0, 300));
    is(row && row.created_at === '2026-01-02T03:04:05Z' && row.qc_status === 'pending',
       'D1. created_at is the COLUMN\'s (2026-01-02...), not the blob\'s forged 1999 value', JSON.stringify(row));
    is(row && row.note === 'ordinary field', 'D2. CONTROL: ordinary blob fields still flow through', JSON.stringify(row));
  }

  section('S. STRUCTURE -- the four sites put the blob first');
  {
    const a = fs.readFileSync(SD_DATA, 'utf8'), b = fs.readFileSync(SD_SUB, 'utf8');
    is(/Object\.assign\(\{\}, ruleData, \{ rule_id: payload\.rule_id/.test(a)
       && /Object\.assign\(\{\}, cData, \{ rule_id: payload\.rule_id/.test(a)
       && /Object\.assign\(\{\}, x\.data \|\| \{\}, \{ draw_id: x\.draw_id \}\)/.test(a)
       && /return Object\.assign\(\{\}, row\.data, \{/.test(b),
       'S1. all four sites have the blob as an EARLIER source than the columns', 'a shape was not found');
  }

  console.log('\n' + (fail ? 'FAILED' : 'PASSED') + ' -- ' + pass + ' passed, '
    + fail + ' failed' + (fail ? '\nFAILING ARMS: ' + failed.join(', ') : ''));
  process.exit(fail ? 1 : 0);
})().catch((e) => {
  console.error('HARNESS ERROR -- no verdict was reached, which is NOT a pass');
  console.error(e);
  process.exit(1);
});
