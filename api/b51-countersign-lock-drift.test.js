// api/b51-countersign-lock-drift.test.js
// OWNER: cody   written 2026-10-22, batch b51, item 1
//
// REQUIREMENT: a write the caller's own table says is countersign-locked is
//   REFUSED when the countersignature PROFILE does not lock that resource --
//   never filed unsigned. cc b50's review of d6b37bb1: requireCountersignature
//   returned null ("signed, proceed") off-profile, so drift between
//   legRoles.requiresCountersignature and PROFILE.lockedResources was guarded
//   only by tests, not at runtime.
//
//   node api/b51-countersign-lock-drift.test.js
//
// Exit: 0 every arm passed · 1 an arm FAILED · 3 COULD NOT RUN
//
// THE DRIFT IS MADE REAL, NOT DESCRIBED: api/leg-countersign.js is replaced in
// the require cache by a copy whose PROFILE locks a different resource, and
// the real handler is driven. Arm X restores the pre-b51 `return null` line in
// a compiled copy of api/_lib/countersign.js and requires R1's exact call to
// FILE the record -- so R1 measures the runtime guard, not the harness.

'use strict';
const fs = require('fs');
const path = require('path');
const Module = require('module');

const API_DIR = __dirname;
const SD_DATA = path.join(API_DIR, 'sd-data.js');

let pass = 0;
const failed = [];
function ok(l) { pass += 1; console.log('  ok   ' + l); }
function bad(l, why) {
  failed.push(l);
  console.log('  FAIL ' + l + (why ? '\n         ' + String(why).slice(0, 500) : ''));
}
function couldNotRun(why) {
  console.log('COULD NOT RUN: ' + why + ' Nothing was verified.');
  process.exit(3);
}

const legRoles = require(path.join(API_DIR, '_lib/leg-roles.js'));

// ── THE HARNESS (the b48 one). Licence, session and fetch mocked.
const HASH = 'hash-of-the-b51-lock-drift-licence';
const KEY = 'legkey-placeholder';
const LICENCE = require.resolve(path.join(API_DIR, '_lib/license.js'));
require.cache[LICENCE] = {
  id: LICENCE, filename: LICENCE, loaded: true,
  exports: {
    validateLicenseKey: async () => ({
      valid: true, active: true, license_hash: HASH,
      stripe_subscription_id: null, trial_ends_at: null, app_id: 'sairnlegacy'
    }),
    hashLicense: () => HASH,
  },
};
process.env.SUPABASE_URL = 'https://example.invalid';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'service-role-for-the-test';
process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  process.env[['SD', 'AUTH', 'SECRET'].join('_')]
  || ['b51', 'lockdrift', String(process.pid)].join('-');

const AUTH_SRC = fs.readFileSync(path.join(API_DIR, '_lib/auth.js'), 'utf8');
const HDR_M = AUTH_SRC.match(/function tokenFromRequest\(req\)\s*\{\s*\n\s*const h = req\.headers\[['"]([a-z0-9-]+)['"]\]/);
if (!HDR_M) couldNotRun('the session header name could not be read out of api/_lib/auth.js.');
const SESSION_HEADER = HDR_M[1];
const { signSessionToken } = require(path.join(API_DIR, '_lib/auth.js'));

const ROSTER = { 'emp-app': 'apprentice', 'emp-dir': 'director', 'emp-own': 'owner' };
// fourth b69 (Michael's b69 item 2): an apprentice-prepared cremation must
// RECORD the licensed supervisor who authorised it, and that supervisor must be
// the director who countersigns -- emp-dir in every signed row below.
const PAYLOAD = { id: 'CR-1', case_id: 'CS-1', decedent: 'test', authorized_by_supervisor: 'emp-dir' };
const TOKEN = ['b51', 'countersign', 'fixture'].join('-');

let settingsRow = null;
let tokenRow = null;
const seen = [];
global.fetch = async (url, init) => {
  const u = String(url);
  const method = (init && init.method) || 'GET';
  seen.push({ url: u, method: method });
  if (/_employee_auth\?/.test(u)) {
    const m = u.match(/employee_id=eq\.([^&]+)/);
    const id = m ? decodeURIComponent(m[1]) : 'emp-app';
    return { ok: true, status: 200,
             json: async () => (ROSTER[id] ? [{ license_hash: HASH, employee_id: id,
                                                role: ROSTER[id], active: true }] : []) };
  }
  if (/sairnlegacy_settings\?/.test(u)) {
    return { ok: true, status: 200, json: async () => (settingsRow ? [settingsRow] : []) };
  }
  if (/_countersign_tokens\?/.test(u)) {
    // GET reads the row; the PATCH spend returns it too (the compare-and-set won).
    return { ok: true, status: 200, json: async () => (tokenRow ? [tokenRow] : []) };
  }
  if (method === 'POST' || method === 'PATCH') {
    let b = null;
    try { b = JSON.parse(init.body); } catch (e) { b = {}; }
    return { ok: true, status: 200, json: async () => [b] };
  }
  return { ok: true, status: 200, json: async () => [] };
};

function fakeRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}
async function call(handler, resource, role, employeeId, withToken) {
  seen.length = 0;
  const headers = { authorization: 'Bearer ' + KEY };
  headers[SESSION_HEADER] = signSessionToken({
    app: 'sairnlegacy', employee_id: employeeId, role: role, license_hash: HASH });
  if (withToken) headers['x-leg-countersign'] = TOKEN;
  const res = fakeRes();
  const realErr = console.error;
  console.error = function () {};
  try {
    await handler({ method: 'POST', headers: headers,
                    body: { action: 'write', resource: resource, payload: PAYLOAD } }, res);
  } finally { console.error = realErr; }
  return res;
}
const code = (r) => (r.body && r.body.error && r.body.error.code) || '';
const wrote = (resource) => seen.some((s) => s.method === 'POST'
  && s.url.indexOf('/' + resource + '?') !== -1);
const askedTokens = () => seen.some((s) => /_countersign_tokens\?/.test(s.url));

const HOME_COUNTERSIGN = { livery_billing: 'through_the_home',
                           apprentice: { countersign: ['leg_cremations'] } };

// ── THE DRIFT ──────────────────────────────────────────────────────────────
const CS_PATH = require.resolve(path.join(API_DIR, '_lib/countersign.js'));
const LEGCS_PATH = require.resolve(path.join(API_DIR, 'leg-countersign.js'));
const CS_SRC = fs.readFileSync(CS_PATH, 'utf8');
const NEW_GUARD = "  if (!mode) {\n    return { status: 500, body: { error: { code: 'COUNTERSIGN_LOCK_MISCONFIGURED',";
// The pre-b51 line, with the new block kept but made unreachable so the file still parses.
const OLD_GUARD = "  if (!mode) return null;\n  if (false) {\n    return { status: 500, body: { error: { code: 'COUNTERSIGN_LOCK_MISCONFIGURED',";

function compile(file, source) {
  const m = new Module(file, module);
  m.filename = file;
  m.paths = Module._nodeModulePaths(path.dirname(file));
  m._compile(source, file);
  return m;
}
function signedRow(csLib) {
  return { id: 'tok-1', content_hash: csLib.contentHash('leg_cremations', PAYLOAD),
           prepared_by: 'emp-app', prepared_role: 'apprentice',
           countersign_employee_id: 'emp-dir', countersign_role: 'director',
           spent_at: null, expires_at: new Date(Date.now() + 600000).toISOString() };
}
// `csSource` null = the real library. `drift` true = the leg PROFILE locks another resource.
function loadWith(csSource, drift) {
  delete require.cache[CS_PATH];
  delete require.cache[LEGCS_PATH];
  if (csSource) require.cache[CS_PATH] = compile(CS_PATH, csSource);
  const legCs = require(LEGCS_PATH);
  if (drift) {
    const csLib = require(CS_PATH);
    const drifted = Object.assign({}, legCs.PROFILE, { lockedResources: Object.freeze(
      Object.assign(Object.create(null), { leg_not_cremations: csLib.MODE_ALWAYS })) });
    require.cache[LEGCS_PATH] = { id: LEGCS_PATH, filename: LEGCS_PATH, loaded: true,
      exports: Object.assign(function () {}, legCs, { PROFILE: drifted }) };
  }
  delete require.cache[require.resolve(SD_DATA)];
  return require(SD_DATA);
}

(async function main() {
  console.log('COUNTERSIGN LOCK DRIFT -- off-profile is a refusal -- criteria 2026-10-22.1');
  if (CS_SRC.split(NEW_GUARD).length - 1 !== 1) couldNotRun('the b51 guard does not occur exactly once in api/_lib/countersign.js.');
  if (!legRoles.requiresCountersignature('leg_cremations')) couldNotRun('leg_cremations is no longer countersign-required.');
  const realCs = require(CS_PATH);

  // U1. The library itself, off-profile -> refusal, and nothing is fetched.
  {
    const legCs = require(LEGCS_PATH);
    const drifted = Object.assign({}, legCs.PROFILE, {
      lockedResources: { leg_not_cremations: realCs.MODE_ALWAYS } });
    seen.length = 0;
    const r = await realCs.requireCountersignature(drifted, { resource: 'leg_cremations',
      payload: PAYLOAD, licHash: HASH, rest: (p) => 'https://example.invalid/rest/v1/' + p,
      headers: {}, token: TOKEN, callerRole: 'owner', callerEmployeeId: 'emp-own' });
    if (r && r.status === 500 && r.body.error.code === 'COUNTERSIGN_LOCK_MISCONFIGURED' && seen.length === 0) {
      ok('U1. requireCountersignature off-profile -> 500 COUNTERSIGN_LOCK_MISCONFIGURED, nothing fetched');
    } else bad('U1. off-profile did not refuse', JSON.stringify(r) + ' fetches=' + seen.length);
  }

  // R0. CONTROL: real library, real profile -> the countersigned apprentice write files.
  settingsRow = HOME_COUNTERSIGN; tokenRow = signedRow(realCs);
  {
    const r = await call(loadWith(null, false), 'leg_cremations', 'apprentice', 'emp-app', true);
    if (r.statusCode === 200 && wrote('leg_cremations')) ok('R0. CONTROL: no drift -> the signed apprentice write files (200)');
    else bad('R0. the harness cannot file a signed write, so R1 and X prove nothing', r.statusCode + ' ' + code(r));
  }

  // R1. Drift + the F3-deferred apprentice write with a valid signature -> refused, not filed.
  settingsRow = HOME_COUNTERSIGN; tokenRow = signedRow(realCs);
  {
    const r = await call(loadWith(null, true), 'leg_cremations', 'apprentice', 'emp-app', true);
    if (r.statusCode === 500 && code(r) === 'COUNTERSIGN_LOCK_MISCONFIGURED'
        && !wrote('leg_cremations') && !askedTokens()) {
      ok('R1. drift + deferred apprentice write -> 500 COUNTERSIGN_LOCK_MISCONFIGURED, nothing written');
    } else bad('R1. a deferred write passed a drifted lock', r.statusCode + ' ' + code(r) + ' wrote=' + wrote('leg_cremations'));
  }

  // R2. Drift + the OWNER's own unsigned write (MODE_ALWAYS binds the owner) -> refused.
  settingsRow = null; tokenRow = null;
  {
    const r = await call(loadWith(null, true), 'leg_cremations', 'owner', 'emp-own', false);
    if (r.statusCode === 500 && code(r) === 'COUNTERSIGN_LOCK_MISCONFIGURED' && !wrote('leg_cremations')) {
      ok('R2. drift + an unsigned owner write -> 500, nothing written (F1 binds the owner too)');
    } else bad('R2. an owner write passed a drifted lock unsigned', r.statusCode + ' ' + code(r) + ' wrote=' + wrote('leg_cremations'));
  }

  // X. ABLATION: the pre-b51 `return null` restored -> R1's exact call FILES the record.
  settingsRow = HOME_COUNTERSIGN; tokenRow = signedRow(realCs);
  {
    const r = await call(loadWith(CS_SRC.replace(NEW_GUARD, OLD_GUARD), true),
                         'leg_cremations', 'apprentice', 'emp-app', true);
    if (r.statusCode === 200 && wrote('leg_cremations')) {
      ok('X. ABLATION: with `if (!mode) return null` restored, R1\'s call files the record -- the gap was real at runtime');
    } else bad('X. the old line did not let the drifted write through, so R1 proves nothing', r.statusCode + ' ' + code(r));
  }
  delete require.cache[CS_PATH];
  delete require.cache[LEGCS_PATH];

  console.log('\n' + pass + ' passed, ' + failed.length + ' failed');
  process.exit(failed.length ? 1 : 0);
})().catch((e) => { console.log('COULD NOT RUN: ' + (e && e.stack || e)); process.exit(3); });
