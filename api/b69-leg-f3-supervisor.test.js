// api/b69-leg-f3-supervisor.test.js
//
// REQUIREMENT (Michael, fourth b69 dispatch item 2): an apprentice may prepare
//   a cremation authorisation ONLY when (a) the home's F3 config clears
//   apprentices to prepare it, and (b) a SPECIFIC licensed supervisor is
//   recorded on the record as authorising it. An EMPTY F3 means DENY -- this
//   replaces b18's default-yes, where api/_lib/countersign-endpoint.js checked
//   the preparer by ROLE alone and a director could then file an
//   apprentice-prepared cremation whatever F3 said.
//
// Run:  node api/b69-leg-f3-supervisor.test.js
//
// THE SUPERVISOR IS RECORDED IN THE RECORD, not beside it: the payload field
// `authorized_by_supervisor` is inside the content the countersignature hashes,
// so the name that authorised the preparation is part of what is signed, and
// at filing it must be the director who actually countersigned. A typed name
// that nobody signed is not an authorisation.
//
// WRITTEN BEFORE THE FIX and run against the unfixed code: every refusal arm
// (P1-P7, P10, S2-S4) FAILED. P8, P9, S1, S5 and L1 are CONTROLS -- a cleared
// apprentice with a recorded supervisor, and every director and law path,
// must still work, so the fix cannot pass by refusing everything.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || ['b69', 'f3', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const { signSessionToken } = require('./_lib/auth');
const cs = require('./_lib/countersign');

const HASH = 'b69-f3-hash';
const KEY = 'KEY-FOR-' + HASH;
const CR = { id: 'CR-9', case_id: 'CS-9' };
// The roster the mock serves. emp-9 is the apprentice; emp-2 and emp-3 are
// directors; emp-7 an arranger (not a signer); emp-4 a director who is inactive.
const ROSTER = { 'emp-9': 'apprentice', 'emp-2': 'director', 'emp-3': 'director',
                 'emp-1': 'owner', 'emp-7': 'arranger', 'emp-4': 'director' };
const INACTIVE = ['emp-4'];
const CLEARED = { countersign: ['leg_cremations'] };

let pass = 0, fail = 0;
function is(cond, label, detail) {
  if (cond) { pass++; console.log('  ok   ' + label); }
  else { fail++; console.log('  FAIL ' + label + (detail ? '\n       ' + String(detail).slice(0, 400) : '')); }
}
function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = (c) => { res.statusCode = c; return res; };
  res.json = (b) => { res.body = b; return res; };
  return res;
}
const code = (res) => (res && res.body && res.body.error && res.body.error.code) || '';
const rcode = (r) => (r && r.body && r.body.error && r.body.error.code) || '';

// settings: an object = the stored F3 config; null = no row; 'missing' = the
// table does not exist; 'error' = the read failed.
function pgMock(calls, opts) {
  return async (url, init) => {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    calls.push({ url: u, method: method });
    if (/sairnlegacy_settings/.test(u)) {
      if (opts.settings === 'missing') return { ok: false, status: 404, json: async () => ({ code: 'PGRST205', message: 'Could not find the table' }) };
      if (opts.settings === 'error') return { ok: false, status: 500, json: async () => ({ message: 'boom' }) };
      return { ok: true, status: 200, json: async () => (opts.settings ? [{ apprentice: opts.settings }] : []) };
    }
    if (/countersign_tokens/.test(u)) {
      if (method === 'PATCH') return { ok: true, status: 200, json: async () => [{ id: 'tok-1' }] };
      if (method === 'POST') return { ok: true, status: 200, json: async () => [JSON.parse(init.body)] };
      return { ok: true, status: 200, json: async () => (opts.tokenRow ? [opts.tokenRow] : []) };
    }
    if (/_employee_auth/.test(u)) {
      const m = u.match(/employee_id=eq\.([^&]+)/);
      const who = m ? decodeURIComponent(m[1]) : '';
      if (!ROSTER[who] || INACTIVE.indexOf(who) !== -1) return { ok: true, status: 200, json: async () => [] };
      return { ok: true, status: 200, json: async () => [{ employee_id: who, role: ROSTER[who], active: true }] };
    }
    return { ok: true, status: 200, json: async () => [] };
  };
}

async function prepare(callerId, payload, settings, app, which) {
  app = app || 'sairnlegacy'; which = which || 'leg-countersign';
  const calls = [];
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = { exports: {
    validateLicenseKey: async () => ({ valid: true, active: true, license_hash: HASH,
      trial_ends_at: null, stripe_subscription_id: null, app_id: app }) } };
  global.fetch = pgMock(calls, { settings: settings });
  delete require.cache[require.resolve('./' + which)];
  delete require.cache[require.resolve('./_lib/countersign-endpoint')];
  const h = require('./' + which);
  const res = mockRes();
  const resource = app === 'sairnlegacy' ? 'leg_cremations' : 'law_trusttx';
  await h({ method: 'POST', headers: { authorization: 'Bearer ' + KEY,
    'x-sd-auth': signSessionToken({ app: app, employee_id: callerId,
      role: ROSTER[callerId] || 'paralegal', license_hash: HASH }) },
    body: { action: 'prepare', resource: resource, payload: payload } }, res);
  return { res: res, minted: calls.some((c) => c.method === 'POST' && /countersign_tokens/.test(c.url)) };
}

function tokenRow(payload, over) {
  return Object.assign({
    id: 'tok-1', resource: 'leg_cremations',
    content_hash: cs.contentHash('leg_cremations', payload),
    prepared_by: 'emp-9', prepared_role: 'apprentice',
    countersign_employee_id: 'emp-2', countersign_role: 'director',
    countersigned_at: new Date(Date.now() - 60000).toISOString(),
    spent_at: null, expires_at: new Date(Date.now() + 5 * 60000).toISOString()
  }, over || {});
}
async function settle(payload, settings, over) {
  const calls = [];
  global.fetch = pgMock(calls, { settings: settings, tokenRow: tokenRow(payload, over) });
  delete require.cache[require.resolve('./leg-countersign')];
  const legCs = require('./leg-countersign');
  const r = await cs.requireCountersignature(legCs.PROFILE, {
    resource: 'leg_cremations', payload: payload, licHash: HASH,
    rest: (p) => process.env.SUPABASE_URL + '/rest/v1/' + p,
    headers: {}, token: 'tok', callerRole: 'director', callerEmployeeId: 'emp-2' });
  return { r: r, spent: calls.some((c) => c.method === 'PATCH' && /spent_at=is\.null/.test(c.url)) };
}

const withSup = (id) => Object.assign({}, CR, { authorized_by_supervisor: id });

(async () => {
  console.log('B69 -- an apprentice prepares a cremation only when F3 clears it AND a named licensed supervisor authorises it\n');

  let k = await prepare('emp-9', withSup('emp-2'), {});
  is(k.res.statusCode === 403 && !k.minted, 'P1. EMPTY F3 -> 403, no token minted (was b18 default-yes)', k.res.statusCode + ' ' + code(k.res));
  k = await prepare('emp-9', withSup('emp-2'), null);
  is(k.res.statusCode === 403 && !k.minted, 'P2. NO settings row -> the narrow default -> 403', k.res.statusCode + ' ' + code(k.res));
  k = await prepare('emp-9', withSup('emp-2'), 'missing');
  is(k.res.statusCode === 403 && !k.minted, 'P2b. settings table not provisioned -> the narrow default -> 403', k.res.statusCode + ' ' + code(k.res));
  k = await prepare('emp-9', withSup('emp-2'), 'error');
  is(k.res.statusCode === 502 && !k.minted, 'P3. settings UNREADABLE -> 502, never read as permission', k.res.statusCode + ' ' + code(k.res));
  k = await prepare('emp-9', CR, CLEARED);
  is(k.res.statusCode === 403 && code(k.res) === 'SUPERVISOR_REQUIRED' && !k.minted, 'P4. F3 clears it but NO supervisor is recorded -> 403 SUPERVISOR_REQUIRED', k.res.statusCode + ' ' + code(k.res));
  k = await prepare('emp-9', withSup('emp-7'), CLEARED);
  is(k.res.statusCode === 403 && code(k.res) === 'SUPERVISOR_NOT_QUALIFIED' && !k.minted, 'P5. the named supervisor is not a licensed director -> 403', k.res.statusCode + ' ' + code(k.res));
  k = await prepare('emp-9', withSup('emp-4'), CLEARED);
  is(k.res.statusCode === 403 && !k.minted, 'P6. the named supervisor is INACTIVE -> 403', k.res.statusCode + ' ' + code(k.res));
  k = await prepare('emp-9', withSup('emp-9'), CLEARED);
  is(k.res.statusCode >= 400 && !k.minted, 'P7. the apprentice names themself as supervisor -> refused', k.res.statusCode + ' ' + code(k.res));
  k = await prepare('emp-9', withSup('emp-2'), CLEARED);
  is(k.res.statusCode === 200 && k.minted, 'P8. CONTROL: F3 clears it and a licensed director is recorded -> 200, token minted', k.res.statusCode + ' ' + code(k.res));
  k = await prepare('emp-2', CR, {});
  is(k.res.statusCode === 200 && k.minted, 'P9. CONTROL: a DIRECTOR prepares with no supervisor field and empty F3 -> 200 (signers are not apprentices)', k.res.statusCode + ' ' + code(k.res));
  k = await prepare('emp-9', withSup('emp-2'), { countersign: ['leg_cremations'], forbidden: ['leg_cremations'] });
  is(k.res.statusCode === 403 && !k.minted, 'P10. F3 FORBIDDEN wins over countersign -> 403', k.res.statusCode + ' ' + code(k.res));

  let s = await settle(withSup('emp-2'), CLEARED);
  is(s.r === null && s.spent, 'S1. CONTROL: apprentice-prepared, recorded supervisor emp-2 is the director who countersigned, F3 clears it -> filed', JSON.stringify(s.r));
  s = await settle(withSup('emp-3'), CLEARED);
  is(s.r && s.r.status === 403 && rcode(s.r) === 'SUPERVISOR_DID_NOT_SIGN' && !s.spent, 'S2. the recorded supervisor (emp-3) is NOT who countersigned (emp-2) -> 403, signature not spent', JSON.stringify(s.r));
  s = await settle(CR, CLEARED);
  is(s.r && s.r.status === 403 && rcode(s.r) === 'SUPERVISOR_REQUIRED' && !s.spent, 'S3. an apprentice-prepared record with NO supervisor recorded -> 403 at filing', JSON.stringify(s.r));
  s = await settle(withSup('emp-2'), {});
  is(s.r && s.r.status === 403 && !s.spent, 'S4. F3 emptied AFTER the prepare -> refused at filing; the config at FILE time governs', JSON.stringify(s.r));
  s = await settle(CR, {}, { prepared_by: 'emp-3', prepared_role: 'director' });
  is(s.r === null && s.spent, 'S5. CONTROL: a DIRECTOR-prepared record needs no supervisor field and ignores F3 -> filed', JSON.stringify(s.r));

  const lawCs = require('./law-countersign');
  is(!lawCs.PROFILE.supervisorField && typeof lawCs.PROFILE.preparePolicy !== 'function',
     'L1. CONTROL: SAIRNlaw\'s profile carries neither hook, so the shared module behaves exactly as before for law');

  console.log('\nb69 leg F3 supervisor: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });
