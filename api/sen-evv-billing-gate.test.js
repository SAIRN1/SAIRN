'use strict';
// api/sen-evv-billing-gate.test.js -- fourth b65, Michael's decision: a SAIRNsenior
// claim does not move to submitted or paid while its visit carries an EVV clock
// flag nobody has reviewed. Drives the REAL api/sd-data.js handler against a fake
// PostgREST that holds one claim row and one visit row.
// Run: node api/sen-evv-billing-gate.test.js
const crypto = require('crypto');
process.env[['SD', 'AUTH', 'SECRET'].join('_')] = ['b65', 'fixture', String(process.pid)].join('-');
process.env.SUPABASE_URL = 'https://fake.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'fake-service-key';
const KEY = 'k';
const HASH = crypto.createHash('sha256').update(KEY).digest('hex');

let pass = 0, fail = 0;
function is(c, l, why) {
  if (c) { pass++; console.log('  ok   ' + l); return; }
  fail++; console.log('  FAIL ' + l + (why ? '\n         ' + String(why).slice(0, 300) : ''));
}
require.cache[require.resolve('./_lib/license')] = {
  id: require.resolve('./_lib/license'), filename: require.resolve('./_lib/license'), loaded: true,
  exports: { validateLicenseKey: async () => ({ valid: true, active: true, license_hash: HASH,
    trial_ends_at: null, stripe_subscription_id: null, app_id: 'sairnsenior' }) },
};
const { signSessionToken } = require('./_lib/auth');
delete require.cache[require.resolve('./sd-data.js')];
const handler = require('./sd-data.js');

const DB = { claim: null, visit: null, visitReadFails: false };
const writes = [];
const resp = (status, body) => ({ ok: status < 300, status, headers: { get: () => '' },
  text: async () => JSON.stringify(body), json: async () => body });
global.fetch = async (url, init) => {
  const u = String(url), method = (init && init.method) || 'GET';
  if (/_employee_auth\?/.test(u)) return resp(200, [{ license_hash: HASH, employee_id: 'E1', role: 'owner', active: true }]);
  if (method !== 'GET') {
    const body = JSON.parse(init.body);
    writes.push({ url: u, body });
    if (/^[^?]*sen_visits\?/.test(u)) DB.visit = { assigned_employee_id: body.assigned_employee_id, data: body.data };
    if (/^[^?]*sen_claims\?/.test(u)) DB.claim = { data: body.data };
    return resp(200, [body]);
  }
  if (/sen_visits\?/.test(u)) return DB.visitReadFails ? resp(500, { message: 'boom' }) : resp(200, DB.visit ? [DB.visit] : []);
  if (/sen_claims\?/.test(u)) return resp(200, DB.claim ? [DB.claim] : []);
  return resp(200, []);
};
async function call(resource, action, payload, role) {
  writes.length = 0;
  const res = { statusCode: null, body: null };
  res.status = (c) => { res.statusCode = c; return res; };
  res.json = (b) => { res.body = b; return res; };
  await handler({ method: 'POST', headers: { authorization: 'Bearer ' + KEY,
    'x-sd-auth': signSessionToken({ app: 'sairnsenior', employee_id: 'E1', role: role || 'owner', license_hash: HASH }) },
    body: { action, resource, payload } }, res);
  return { code: res.statusCode, err: (res.body && res.body.error && res.body.error.code) || '', writes: writes.slice(), body: res.body };
}
const FLAG = { field: 'clock_in_at', code: 'LATE_REPLAY', skew_ms: 9 * 864e5 };
const claim = (status) => ({ id: 'CLM-1', visit_id: 'VIS-1', status, amount: 120 });
const claimWrites = (r) => r.writes.filter((w) => /sen_claims\?/.test(w.url)).length;

(async () => {
  console.log('SAIRNsenior EVV billing gate (fourth b65)\n');
  DB.claim = { data: claim('draft') };
  DB.visit = { assigned_employee_id: 'CG1', data: { status: 'completed', clock_flags: [FLAG] } };

  let r = await call('sen_claims', 'write', claim('paid'));
  is(r.code === 409 && r.err === 'EVV_UNREVIEWED' && claimWrites(r) === 0,
     'draft -> paid over an UNREVIEWED flag is refused, and nothing is written', r.code + ' ' + r.err);
  is(/LATE_REPLAY on clock_in_at/.test(r.body.error.message), '...and the refusal names the flag');
  r = await call('sen_claims', 'write', claim('submitted'));
  is(r.code === 409 && r.err === 'EVV_UNREVIEWED', 'draft -> submitted is refused the same way');
  r = await call('sen_claims', 'write', Object.assign(claim('draft'), { notes: 'x' }));
  is(r.code === 200 && claimWrites(r) === 1, 'CONTROL: editing the DRAFT is not gated');

  r = await call('sen_visits', 'review_clock_flags', { id: 'VIS-1', note: 'checked' }, 'caregiver');
  is(r.code === 403, 'a caregiver cannot review clock flags', r.code + ' ' + JSON.stringify(r.body));
  r = await call('sen_visits', 'review_clock_flags', { id: 'VIS-1', note: '  ' });
  is(r.code === 400 && r.err === 'NOTE_REQUIRED', 'a review with no note is refused');
  r = await call('sen_visits', 'review_clock_flags', { id: 'VIS-1', note: 'Tablet was offline; matched to the caregiver call log' }, 'billing');
  const rev = DB.visit.data.clock_flags_review;
  is(r.code === 200 && rev && JSON.stringify(rev.flags) === JSON.stringify([FLAG]) && rev.reviewed_by === 'E1' && rev.reviewed_role === 'billing',
     'billing reviews it: the review stores the exact flags, who and as what role', JSON.stringify(rev));

  r = await call('sen_claims', 'write', claim('paid'));
  is(r.code === 200 && claimWrites(r) === 1 && DB.claim.data.status === 'paid', 'after review, the claim pays');
  r = await call('sen_claims', 'write', Object.assign(claim('paid'), { appeal: null }));
  is(r.code === 200, 'CONTROL: an already-paid claim is not re-gated on edit');

  DB.claim = { data: claim('draft') };
  DB.visit.data.clock_flags = [FLAG, { field: 'clock_out_at', code: 'FUTURE', skew_ms: 3e5 }];
  r = await call('sen_claims', 'write', claim('paid'));
  is(r.code === 409 && r.err === 'EVV_UNREVIEWED', 'a flag that arrives AFTER the review makes the visit unreviewed again');

  DB.visit = { assigned_employee_id: 'CG1', data: { status: 'completed' } };
  r = await call('sen_claims', 'write', claim('paid'));
  is(r.code === 200, 'CONTROL: a visit with no flags pays normally');

  DB.claim = { data: claim('draft') };
  DB.visitReadFails = true;
  r = await call('sen_claims', 'write', claim('paid'));
  is(r.code === 503 && r.err === 'EVV_CHECK_FAILED' && claimWrites(r) === 0, 'a visit that cannot be READ refuses -- could-not-tell is not a pass');
  DB.visitReadFails = false;
  DB.visit = null;
  r = await call('sen_claims', 'write', claim('paid'));
  is(r.code === 409 && r.err === 'EVV_VISIT_MISSING', 'a claim whose visit is not on the server is refused');
  DB.claim = null;   // a brand-new claim with no stored row and no visit_id
  r = await call('sen_claims', 'write', { id: 'CLM-2', status: 'paid' });
  is(r.code === 409 && r.err === 'EVV_UNVERIFIABLE', 'a claim naming no visit is refused');

  const src = require('fs').readFileSync(require('path').join(__dirname, 'sd-data.js'), 'utf8');
  const lists = src.match(/SEN_VISIT_(SCHEDULE|EVV)_FIELDS = \[[^\]]*\]/g) || [];
  is(lists.length === 2 && lists.every((l) => !/clock_flags_review/.test(l)),
     'the ordinary visit write cannot set or clear a review (not in either field list)', JSON.stringify(lists));

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('COULD NOT RUN: ' + (e && e.stack || e)); process.exit(2); });
