// hank b51 -- D1 / D1b: a billing employee ASSIGNED to a resident read that
// resident's MAR through the assignment tier with no grant, no expiry and no
// audit row (hank b50 review of cody's tests/mar_billing_grant.test.js). And a
// granted read was served even when its mar_access_read row failed to write.
//
// Concept: a grantee role is admitted by its grant or not at all, and the log
// row is the grant's condition, so a read that cannot be logged is not served.
//
// Drives the real api/sd-data.js handler with auth, licence and fetch mocked.
// Every GET is recorded, so "refused BEFORE the MAR was read" is asserted, not
// inferred from a status code. Section M recompiles the handler from source
// with one barrier removed and requires the named arm to go red.
//
// Run:  node api/b51-mar-billing-assigned.test.js     Exit: 0 pass, 1 fail

'use strict';
const fs = require('fs');
const path = require('path');
const Module = require('module');
const ROOT = path.join(__dirname, '..');
const SD = path.join(ROOT, 'api/sd-data.js');

process.env.SUPABASE_URL = 'https://fake.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'fake-service-key';

const licenseMod = require(path.join(ROOT, 'api/_lib/license.js'));
licenseMod.validateLicenseKey = async () => ({
  valid: true, active: true, license_hash: 'HASH1',
  stripe_subscription_id: 'sub_1', trial_ends_at: null, app_id: 'sairncare' });
const authMod = require(path.join(ROOT, 'api/_lib/auth.js'));
authMod.tokenFromRequest = (req) => req.headers['x-test-token'] || null;
authMod.verifySessionToken = (token) => {
  if (!token) return null;
  const p = JSON.parse(token);
  return { role: p.role, employee_id: p.employee_id, app: 'sairncare', subject: p.employee_id };
};

// E1 (billing) and E3 (caregiver) are both assigned to R1 -- the shape the
// defect needed. R2 belongs to E2.
const CLIENTS = [{ client_id: 'R1', assigned_employee_id: 'E1' },
                 { client_id: 'R1', assigned_employee_id: 'E3' },
                 { client_id: 'R2', assigned_employee_id: 'E2' }];
const CONTACTS = [{ contact_id: 'C1', resident_id: 'R1', name: 'Dana Reyes',
  relationship: 'daughter', email: 'd@example.com', phone: '555-0100', active: true,
  mar_consent: true, created_at: '2026-01-01', updated_at: '2026-01-01' }];
const MAR = [{ entry_id: 'M1', resident_id: 'R1', entry_type: 'administration',
  data: { med: 'Lisinopril', status: 'given' }, created_at: '2026-02-01T09:00:00Z' }];
const HOUR = 3600 * 1000;
const isoIn = (ms) => new Date(Date.now() + ms).toISOString();
const liveGrant = () => ({ grant_id: 'G1', contact_id: 'C1', resident_id: 'R1',
  grantee_employee_id: 'E1', granted_by: 'OM1', expires_at: isoIn(24 * HOUR),
  revoked_at: null, created_at: isoIn(-HOUR) });

let GRANTS = [], WRITES = [], GETS = [], AUDIT_FAILS = false;
function reset() { GRANTS = []; WRITES = []; GETS = []; AUDIT_FAILS = false; }

global.fetch = async (url, opts) => {
  const u = String(url);
  const method = (opts && opts.method) || 'GET';
  let body = null;
  if (opts && opts.body) { try { body = JSON.parse(opts.body); } catch (e) { body = opts.body; } }
  if (method !== 'GET') {
    WRITES.push({ url: u, method, body });
    if (AUDIT_FAILS && /sairncare_audit_log/.test(u)) {
      return { ok: false, status: 500, text: async () => 'down', json: async () => ({ message: 'down' }) };
    }
    return { ok: true, status: 201, text: async () => '', json: async () => (Array.isArray(body) ? body : [body]) };
  }
  GETS.push(u);
  if (/alf_mar_access_grants\?/.test(u)) return { ok: true, status: 200, json: async () => GRANTS };
  if (/alf_clients\?/.test(u)) {
    const m = u.match(/assigned_employee_id=eq\.([^&]+)/);
    const who = m ? decodeURIComponent(m[1]) : null;
    return { ok: true, status: 200, json: async () =>
      CLIENTS.filter((c) => !who || c.assigned_employee_id === who).map((c) => ({ client_id: c.client_id })) };
  }
  if (/alf_family_contacts\?/.test(u)) {
    const m = u.match(/contact_id=eq\.([^&]+)/);
    const id = m ? decodeURIComponent(m[1]) : null;
    return { ok: true, status: 200, json: async () => CONTACTS.filter((c) => !id || c.contact_id === id) };
  }
  if (/alf_mar\?/.test(u)) return { ok: true, status: 200, json: async () => MAR };
  throw new Error('Unmocked fetch: ' + method + ' ' + u);
};

const SRC = fs.readFileSync(SD, 'utf8');
function compile(src) {
  // Same filename and paths as the real module, so its relative requires
  // resolve exactly as in production.
  const m = new Module(SD, module);
  m.filename = SD;
  m.paths = Module._nodeModulePaths(path.dirname(SD));
  m._compile(src, SD);
  return m.exports;
}
let handler = compile(SRC);

function fakeRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}
async function famMar(role, emp) {
  const req = { method: 'POST', headers: { authorization: 'Bearer testkey',
    'x-test-token': JSON.stringify({ role, employee_id: emp }) },
    body: { action: 'family_mar', resource: 'alf_family_contacts', payload: { contact_id: 'C1' } } };
  const res = fakeRes();
  try { await handler(req, res); } catch (e) { res.threw = e; }
  return res;
}
const marRead = () => GETS.some((u) => /alf_mar\?/.test(u));
const audits = (ev) => WRITES.filter((w) => /sairncare_audit_log/.test(w.url)
  && w.body && (Array.isArray(w.body) ? w.body[0] : w.body).event_type === ev)
  .map((w) => (Array.isArray(w.body) ? w.body[0] : w.body));

let pass = 0, fail = 0; const failed = [];
function check(label, cond, why) {
  if (cond) { pass++; console.log('  ok   ' + label); }
  else { fail++; failed.push(label.split('.')[0]); console.log('  FAIL ' + label + (why ? '\n       ' + String(why).slice(0, 300) : '')); }
}
const brief = (r) => JSON.stringify({ s: r.statusCode, b: r.body, t: r.threw && String(r.threw) });

const ARMS = {
  async N1() {
    reset();
    const r = await famMar('billing', 'E1');
    const ref = audits('mar_access_grant_refused');
    return [r.statusCode === 403 && r.body && r.body.error && r.body.error.code === 'FORBIDDEN'
      && !(r.body && r.body.family_mar) && !marRead()
      && ref.length === 1 && ref[0].detail && ref[0].detail.reason === 'NO_LIVE_GRANT', brief(r) + ' audits=' + JSON.stringify(ref)];
  },
  async N2() {
    reset(); GRANTS = [Object.assign(liveGrant(), { expires_at: isoIn(-HOUR) })];
    const r = await famMar('billing', 'E1');
    return [r.statusCode === 403 && !marRead(), brief(r)];
  },
  async N3() {
    reset(); GRANTS = [Object.assign(liveGrant(), { revoked_at: isoIn(-HOUR) })];
    const r = await famMar('billing', 'E1');
    return [r.statusCode === 403 && !marRead(), brief(r)];
  },
  async N4() {
    reset(); GRANTS = [liveGrant()];
    const r = await famMar('billing', 'E1');
    const rd = audits('mar_access_read');
    return [r.statusCode === 200 && r.body.via_grant === 'G1' && rd.length === 1
      && rd[0].detail.grant_id === 'G1', brief(r).slice(0, 200)];
  },
  async N5() {
    reset();
    const r = await famMar('nursing', 'E9');
    return [r.statusCode === 200 && !!r.body.family_mar && audits('mar_access_read').length === 0, brief(r).slice(0, 200)];
  },
  async N6() {
    reset();
    const r = await famMar('caregiver', 'E3');
    return [r.statusCode !== 403 || !(r.body && r.body.error && /grant/i.test(r.body.error.message || '')),
      brief(r).slice(0, 200)];
  },
  async A1() {
    reset(); GRANTS = [liveGrant()]; AUDIT_FAILS = true;
    const r = await famMar('billing', 'E1');
    return [r.statusCode === 503 && r.body.error.code === 'AUDIT_UNAVAILABLE' && !r.body.family_mar, brief(r)];
  },
  async A2() {
    reset(); AUDIT_FAILS = true;
    const r = await famMar('billing', 'E1');
    return [r.statusCode === 403 && !marRead(), brief(r)];
  },
};
const LABELS = {
  N1: 'N1. billing ASSIGNED to the resident, no grant -> 403 FORBIDDEN, MAR never fetched, refusal audited NO_LIVE_GRANT',
  N2: 'N2. billing assigned, EXPIRED grant -> 403, MAR never fetched',
  N3: 'N3. billing assigned, REVOKED grant -> 403, MAR never fetched',
  N4: 'N4. billing with a LIVE grant -> 200 via_grant G1, one mar_access_read row naming G1',
  N5: 'N5. control: nursing (broad) -> 200 with the MAR, no granted-read row',
  N6: 'N6. control: a non-grantee narrow role (caregiver, assigned) is not caught by the grant gate',
  A1: 'A1. live grant but the mar_access_read write FAILS -> 503 AUDIT_UNAVAILABLE, no MAR in the body',
  A2: 'A2. billing refusal whose audit write fails is STILL refused (refusals stay best-effort)',
};

// One barrier removed per mutant; the named arm must go red.
const GATE_ANCHOR = "if (!marBroad && !marGrant && ALF_MAR_GRANT_GRANTEE_ROLES[session.role]) {";
const LOG_ANCHOR = "if (marReadLogged !== true) {";
const MUTANTS = [
  { id: 'M1', arm: 'N1', why: 'grant gate removed', from: GATE_ANCHOR, to: 'if (false) {' },
  { id: 'M2', arm: 'A1', why: 'read-log condition removed', from: LOG_ANCHOR, to: 'if (false) {' },
  { id: 'M3', arm: 'N1', why: 'refusal not audited',
    from: "reason: 'NO_LIVE_GRANT', action: 'family_mar',", to: "reason: 'X', action: 'family_mar'," },
];

(async () => {
  console.log('b51 MAR billing assignment-tier gate + granted-read log condition');
  for (const k of Object.keys(ARMS)) { const [c, why] = await ARMS[k](); check(LABELS[k], c, why); }
  console.log('M. mutants');
  for (const mu of MUTANTS) {
    const n = SRC.split(mu.from).length - 1;
    if (n !== 1) { check(mu.id + '. anchor for "' + mu.why + '" occurs exactly once', false, 'occurs ' + n); continue; }
    handler = compile(SRC.replace(mu.from, mu.to));
    const [c] = await ARMS[mu.arm]();
    check(mu.id + '. ' + mu.why + ' -> ' + mu.arm + ' goes RED', !c);
  }
  handler = compile(SRC);
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  if (fail) console.log('FAILED: ' + failed.join(', '));
  process.exit(fail ? 1 : 0);
})();
