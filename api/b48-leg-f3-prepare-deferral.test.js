// api/b48-leg-f3-prepare-deferral.test.js
// OWNER: cody   written 2026-10-22, batch b48, item 2
//
// REQUIREMENT: an apprentice on a home's F3 countersign list can FILE a
//   leg_cremations record that a director has countersigned -- and nobody
//   else gains anything: no token, no list, a `forbidden` entry, another
//   resource or another role all keep the refusal they had before.
//
//   node api/b48-leg-f3-prepare-deferral.test.js
//
// Exit: 0 every arm passed · 1 an arm FAILED · 3 COULD NOT RUN
//
// ── WHY ────────────────────────────────────────────────────────────────────
// decide(..., 'prepare', grants, home) has allowed it since b18 and the home's
// settings have reached decide() since b27, but the role gate in
// api/sd-data.js answered 403 to the apprentice's WRITE before the
// countersignature check ran, so a signed record could never be filed. Law
// solved the same shape in b18 (C2's two-stage deferral); b48 copies it.
//
// ARM X IS THE ABLATION: the deferral is switched off in a copy of the source
// and arm D2 must go red on it, so D2 is measuring the wiring and not a
// harness that lets everything through.

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
const cs = require(path.join(API_DIR, '_lib/countersign.js'));

// ── THE HARNESS. Licence, session and fetch mocked; nothing real is reached.
const HASH = 'hash-of-the-b48-leg-f3-licence';
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
  || ['b48', 'legf3', String(process.pid)].join('-');

// THE SESSION HEADER IS READ OUT OF auth.js, NEVER TYPED.
const AUTH_SRC = fs.readFileSync(path.join(API_DIR, '_lib/auth.js'), 'utf8');
const HDR_M = AUTH_SRC.match(/function tokenFromRequest\(req\)\s*\{\s*\n\s*const h = req\.headers\[['"]([a-z0-9-]+)['"]\]/);
if (!HDR_M) couldNotRun('the session header name could not be read out of api/_lib/auth.js.');
const SESSION_HEADER = HDR_M[1];
const { signSessionToken } = require(path.join(API_DIR, '_lib/auth.js'));

const ROSTER = { 'emp-app': 'apprentice', 'emp-dir': 'director', 'emp-liv': 'livery' };
const PAYLOAD = { id: 'CR-1', case_id: 'CS-1', decedent: 'test' };
const TOKEN = ['b48', 'countersign', 'fixture'].join('-');

// `settingsRow` and `tokenRow` are the knobs; `seen` records every call.
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

function loadHandler(source) {
  delete require.cache[require.resolve(SD_DATA)];
  if (!source) return require(SD_DATA);
  const m = new Module(SD_DATA, module);
  m.filename = SD_DATA;
  m.paths = Module._nodeModulePaths(API_DIR);
  m._compile(source, SD_DATA);
  return m.exports;
}

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
  await handler({ method: 'POST', headers: headers,
                  body: { action: 'write', resource: resource, payload: PAYLOAD } }, res);
  return res;
}
const code = (r) => (r.body && r.body.error && r.body.error.code) || '';
const wrote = (resource) => seen.some((s) => s.method === 'POST'
  && s.url.indexOf('/' + resource + '?') !== -1);
const askedTokens = () => seen.some((s) => /_countersign_tokens\?/.test(s.url));

const HOME_COUNTERSIGN = { livery_billing: 'through_the_home',
                           apprentice: { countersign: ['leg_cremations'] } };
const HOME_FORBIDDEN = { livery_billing: 'through_the_home',
                         apprentice: { countersign: ['leg_cremations'], forbidden: ['leg_cremations'] } };

function signedRow() {
  return { id: 'tok-1', content_hash: cs.contentHash('leg_cremations', PAYLOAD),
           prepared_by: 'emp-app', prepared_role: 'apprentice',
           countersign_employee_id: 'emp-dir', countersign_role: 'director',
           spent_at: null, expires_at: new Date(Date.now() + 600000).toISOString() };
}

async function arms(handler) {
  const out = {};
  settingsRow = HOME_COUNTERSIGN; tokenRow = signedRow();
  out.d2 = await call(handler, 'leg_cremations', 'apprentice', 'emp-app', true);
  out.d2wrote = wrote('leg_cremations');
  return out;
}

(async function main() {
  console.log('LEG F3 -- an apprentice files a countersigned record -- criteria 2026-10-22.1');

  const SRC = fs.readFileSync(SD_DATA, 'utf8');
  const FLAG = 'const legDeferToCountersign =';
  if (SRC.split(FLAG).length - 1 !== 1) couldNotRun('`' + FLAG + '` does not occur exactly once in api/sd-data.js.');
  if (legRoles.decide('leg_cremations', 'apprentice', 'write', null, HOME_COUNTERSIGN) !== legRoles.DENY) {
    couldNotRun('decide() now ALLOWS an apprentice a plain write on leg_cremations, so nothing here is deferred.');
  }
  const handler = loadHandler();

  // D1. On the list, NO token -> refused by the countersignature, not filed.
  settingsRow = HOME_COUNTERSIGN; tokenRow = null;
  {
    const r = await call(handler, 'leg_cremations', 'apprentice', 'emp-app', false);
    if (r.statusCode === 403 && code(r) === 'COUNTERSIGN_REQUIRED' && !wrote('leg_cremations')) {
      ok('D1. on the list without a signature -> 403 COUNTERSIGN_REQUIRED, nothing written');
    } else bad('D1. an unsigned apprentice write was not refused by the lock', r.statusCode + ' ' + code(r) + ' wrote=' + wrote('leg_cremations'));
  }

  // D2. On the list, a director-countersigned token -> FILED.
  {
    const o = await arms(handler);
    if (o.d2.statusCode === 200 && o.d2wrote) {
      ok('D2. on the list with a director\'s countersignature -> 200 and the record is written');
    } else bad('D2. a countersigned apprentice write did not file', o.d2.statusCode + ' ' + code(o.d2) + ' ' + JSON.stringify(o.d2.body).slice(0, 200));
  }

  // D3. NO settings row (empty F3) + the same valid token -> the role 403, token never consulted.
  settingsRow = null; tokenRow = signedRow();
  {
    const r = await call(handler, 'leg_cremations', 'apprentice', 'emp-app', true);
    if (r.statusCode === 403 && code(r) === 'FORBIDDEN' && !askedTokens() && !wrote('leg_cremations')) {
      ok('D3. NEGATIVE: a home with no F3 list -> 403 FORBIDDEN even with a valid signature; the token is never read');
    } else bad('D3. an apprentice with no F3 list got past the role gate', r.statusCode + ' ' + code(r) + ' tokens=' + askedTokens());
  }

  // D4. `forbidden` beats `countersign` -> the role 403.
  settingsRow = HOME_FORBIDDEN; tokenRow = signedRow();
  {
    const r = await call(handler, 'leg_cremations', 'apprentice', 'emp-app', true);
    if (r.statusCode === 403 && code(r) === 'FORBIDDEN' && !wrote('leg_cremations')) {
      ok('D4. NEGATIVE: leg_cremations both listed and forbidden -> 403 FORBIDDEN (narrowing wins)');
    } else bad('D4. a forbidden resource was deferred', r.statusCode + ' ' + code(r));
  }

  // D5. A resource without the countersignature lock -> the role 403.
  settingsRow = { livery_billing: 'through_the_home', apprentice: { countersign: ['leg_deathrecords'] } };
  tokenRow = signedRow();
  {
    const r = await call(handler, 'leg_deathrecords', 'apprentice', 'emp-app', true);
    if (r.statusCode === 403 && code(r) === 'FORBIDDEN' && !wrote('leg_deathrecords')) {
      ok('D5. NEGATIVE: a listed resource with no countersignature lock -> 403 FORBIDDEN');
    } else bad('D5. an unlocked resource was deferred', r.statusCode + ' ' + code(r));
  }

  // D6. Another role with no prepare route -> the role 403, whatever it carries.
  settingsRow = HOME_COUNTERSIGN; tokenRow = signedRow();
  {
    const r = await call(handler, 'leg_cremations', 'livery', 'emp-liv', true);
    if (r.statusCode === 403 && code(r) === 'FORBIDDEN' && !wrote('leg_cremations')) {
      ok('D6. NEGATIVE: livery with a valid signature -> 403 FORBIDDEN (the list is the apprentice\'s)');
    } else bad('D6. a non-apprentice role was deferred', r.statusCode + ' ' + code(r));
  }

  // D7. Self-signed (preparer === signer) -> refused by the lock.
  settingsRow = HOME_COUNTERSIGN;
  tokenRow = Object.assign(signedRow(), { countersign_employee_id: 'emp-app', countersign_role: 'director' });
  {
    const r = await call(handler, 'leg_cremations', 'apprentice', 'emp-app', true);
    if (r.statusCode === 409 && code(r) === 'COUNTERSIGN_SAME_PERSON' && !wrote('leg_cremations')) {
      ok('D7. NEGATIVE: a signature by the preparer -> 409 COUNTERSIGN_SAME_PERSON, nothing written');
    } else bad('D7. a self-countersigned apprentice record was not refused', r.statusCode + ' ' + code(r));
  }

  // X. ABLATION: the deferral switched off -> D2 must go red.
  {
    const ablated = SRC.replace(FLAG, 'const legDeferToCountersign = false &&');
    const o = await arms(loadHandler(ablated));
    if (o.d2.statusCode === 403 && code(o.d2) === 'FORBIDDEN' && !o.d2wrote) {
      ok('X. ABLATION: with the deferral off, D2\'s exact call is 403 FORBIDDEN -- D2 measures the wiring');
    } else bad('X. D2 passes without the deferral, so it measures nothing', o.d2.statusCode + ' ' + code(o.d2));
  }

  console.log('\n' + pass + ' passed, ' + failed.length + ' failed');
  process.exit(failed.length ? 1 : 0);
})().catch((e) => { console.log('COULD NOT RUN: ' + (e && e.stack || e)); process.exit(3); });
