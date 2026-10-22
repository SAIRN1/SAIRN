// hank b52 -- UNREADABLE IS NOT EMPTY. The sweep after the leg_settings fix
// (63 row-or-null sites classified) found the same fail-open shape at four more
// Tier A call sites: an OK PostgREST answer whose body is unparsable or not a
// list was read as "no row", and the code went on to the PERMISSIVE answer.
//
//   L. sd-data.js leg_ role gate: no settings row -> no apprentice forbidden
//      list -> a FORBIDDEN record type came back ALLOWED. Also a broken read
//      (HTTP 500) fell back to that same "narrow default", which is wide.
//   F. sd-data.js alf_family_contacts write: no prior row -> "first save" ->
//      consent_granted_at/by re-stamped.
//   W. sairncare-witness.js / sv-witness.js: no policy row -> no two-person
//      rule -> a count saved without its countersign.
//   A. law-auth.js loadEmployee: a non-list answer -> "not enrolled" -> MFA off.
//
// L and F drive the real api/sd-data.js handler. W and A are SOURCE arms on the
// guard line (a driven harness for those endpoints already exists in their own
// suites, which pass; these arms pin the one line). Section M removes each
// driven guard and requires its arm to go red.
//
// Run: node api/b52-unreadable-is-not-empty.test.js    Exit 0 pass, 1 fail

'use strict';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || ['unreadable', 'b52', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const Module = require('module');
const { signSessionToken } = require('./_lib/auth');

const SD_FILE = path.join(__dirname, 'sd-data.js');
const SD_SRC = fs.readFileSync(SD_FILE, 'utf8');
const HASH = 'b52-home-hash';

function load(src, app) {
  const lic = require.resolve('./_lib/license');
  delete require.cache[lic];
  require.cache[lic] = { id: lic, filename: lic, loaded: true, exports: {
    validateLicenseKey: async function () {
      return { valid: true, active: true, license_hash: HASH, trial_ends_at: null,
               stripe_subscription_id: null, app_id: app };
    } } };
  const m = new Module(SD_FILE, module);
  m.filename = SD_FILE;
  m.paths = Module._nodeModulePaths(__dirname);
  m._compile(src || SD_SRC, SD_FILE);
  return m.exports;
}

// route(u, o) -> a response, or undefined for the default (an empty OK list).
async function drive(src, app, role, body, route) {
  const h = load(src, app);
  const writes = [];
  const prev = global.fetch;
  global.fetch = async function (url, o) {
    const u = String(url);
    if (o && o.method && o.method !== 'GET') writes.push({ u: u, body: o.body });
    if (/_employee_auth\?/.test(u)) {
      return { ok: true, status: 200, json: async () => [{ license_hash: HASH, employee_id: 'emp-' + role, role: role, active: true }] };
    }
    const r = route(u, o);
    if (r) return r;
    return { ok: true, status: 201, text: async () => '', json: async () => [] };
  };
  const res = { statusCode: null, body: null, setHeader: function () { return res; },
                status: function (c) { res.statusCode = c; return res; },
                json: function (b) { res.body = b; return res; } };
  try {
    await h({ method: 'POST', headers: { authorization: 'Bearer KEY',
      'x-sd-auth': signSessionToken({ app: app, employee_id: 'emp-' + role, role: role, license_hash: HASH }) },
      body: body }, res);
  } finally { global.fetch = prev; }
  return { res: res, writes: writes };
}
const code = (r) => ((r.body || {}).error || {}).code;
const ok = (rows) => ({ ok: true, status: 200, text: async () => JSON.stringify(rows), json: async () => rows });
const unparsable = () => ({ ok: true, status: 200, text: async () => '<html>', json: async () => { throw new SyntaxError('Unexpected token <'); } });

// ── L. the leg_ role gate ──────────────────────────────────────────────────
const FORBIDS = [{ livery_billing: 'through_the_home', apprentice: { countersign: [], forbidden: ['leg_invoices'], presence_disclosure: true }, livery_grants: {} }];
function legRoute(settings) {
  return function (u) {
    if (/sairnlegacy_settings\?/.test(u)) return settings();
    if (/leg_invoices\?/.test(u)) return ok([]);
    return undefined;
  };
}
const legRead = { action: 'read', resource: 'leg_invoices', payload: {} };
async function armL(src) {
  const control = await drive(src, 'sairnlegacy', 'apprentice', legRead, legRoute(() => ok(FORBIDS)));
  assert.strictEqual(control.res.statusCode, 403, 'control: a home that forbids leg_invoices must refuse the apprentice: ' + JSON.stringify(control.res.body));
  for (const [label, settings] of [['unparsable', unparsable], ['non-list', () => ok({ message: 'x' })],
    ['HTTP 500', () => ({ ok: false, status: 500, text: async () => 'boom', json: async () => ({ message: 'boom' }) })]]) {
    const r = await drive(src, 'sairnlegacy', 'apprentice', legRead, legRoute(settings));
    assert.deepStrictEqual([r.res.statusCode, code(r.res)], [502, 'UNREADABLE_SETTINGS'], label + ': ' + JSON.stringify(r.res.body));
  }
}

// ── F. the alf_family_contacts write's prior-state read ───────────────────
function famRoute(prior) {
  return function (u, o) {
    if (/alf_family_contacts\?/.test(u) && !(o && o.method && o.method !== 'GET')) return prior();
    if (/alf_clients\?/.test(u)) return ok([{ client_id: 'R1' }]);
    return undefined;
  };
}
const famWrite = { action: 'write', resource: 'alf_family_contacts',
  payload: { contact_id: 'C1', resident_id: 'R1', name: 'Dana Reyes', relationship: 'daughter', mar_consent: true } };
async function armF(src) {
  const r = await drive(src, 'sairncare', 'owner', famWrite, famRoute(() => ok({ message: 'not a list' })));
  assert.deepStrictEqual([r.res.statusCode, code(r.res)], [502, 'UNREADABLE_PRIOR'], JSON.stringify(r.res.body));
  assert.strictEqual(r.writes.filter((w) => /alf_family_contacts/.test(w.u)).length, 0, 'a contact row was written');
}
async function armFControl(src) {
  const prior = [{ mar_consent: true, consent_granted_at: '2026-01-01T00:00:00Z', consent_granted_by: 'orig', consent_revoked_at: null, active: true, revoked_at: null }];
  const r = await drive(src, 'sairncare', 'owner', famWrite, famRoute(() => ok(prior)));
  assert.strictEqual(r.res.statusCode, 200, 'control write: ' + JSON.stringify(r.res.body));
  const w = r.writes.filter((x) => /alf_family_contacts/.test(x.u))[0];
  const row = JSON.parse(w.body); const one = Array.isArray(row) ? row[0] : row;
  assert.strictEqual(one.consent_granted_by, 'orig', 'consent provenance not kept on an unchanged consent');
}

// ── W and A: the guard lines, pinned in source ─────────────────────────────
function oneLine(file, line) {
  const s = fs.readFileSync(path.join(__dirname, file), 'utf8');
  assert.strictEqual(s.split(line).length - 1, 1, file + ': expected the guard exactly once: ' + line);
}

function mutate(from, to) {
  const n = SD_SRC.split(from).length - 1;
  if (n !== 1) throw new Error('mutant anchor found ' + n + ' times: ' + from.slice(0, 60));
  return SD_SRC.replace(from, to);
}
async function mustFail(arm, src, name) {
  try { await arm(src); } catch (e) {
    if (e instanceof assert.AssertionError) return;
    throw new Error(name + ': non-assertion error, the mutant proves nothing: ' + e.message);
  }
  throw new Error(name + ' survived');
}

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); pass++; console.log('  ok   ' + name); }
  catch (e) { fail++; console.log('  FAIL ' + name + '\n       ' + String(e.message).slice(0, 300)); }
}

(async function () {
  console.log('b52 -- an unreadable answer is never "no row"');
  await test('L1. leg_ gate: an unparsable, non-list or HTTP-500 settings read -> 502 UNREADABLE_SETTINGS (control: a forbidding home -> 403)', () => armL());
  await test('F1. family contact write: a non-list prior read -> 502 UNREADABLE_PRIOR, nothing written', () => armF());
  await test('F2. control: a readable prior with unchanged consent keeps consent_granted_by', () => armFControl());
  await test('W1. sairncare-witness.js: a non-list policy read is could-not-tell (503), not "no two-person rule"', () =>
    oneLine('sairncare-witness.js', 'if (!Array.isArray(prows)) return null;'));
  await test('W2. sv-witness.js: the same guard', () => oneLine('sv-witness.js', 'if (!Array.isArray(prows)) return null;'));
  await test('A1. law-auth.js loadEmployee: a non-list answer throws; mfa_enroll refuses a token with no active row', () => {
    oneLine('law-auth.js', "if (!Array.isArray(rows)) { const e = new Error('lookup unreadable'); e.detail = rows; throw e; }");
    oneLine('law-auth.js', "res.status(403).json({ error: { code: 'NOT_ACTIVE', message: 'This account is not active, so two-factor cannot be set up for it.' } });");
  });
  console.log('M. mutants -- each removes one driven guard');
  await test('M1. leg_ gate non-list guard removed -> L1 red', () => mustFail(armL,
    mutate('if (!Array.isArray(legSetRows)) {', 'if (false) {'), 'leg non-list'));
  await test('M2. leg_ gate HTTP-500 refusal removed -> L1 red', () => mustFail(armL,
    mutate("+ legSetR.status + ' -- refusing ' + resource + '/' + action);\n          res.status(502)",
      "+ legSetR.status + ' -- refusing ' + resource + '/' + action);\n          if (false) res.status(502)"), 'leg 500'));
  await test('M3. family prior guard removed -> F1 red', () => mustFail(armF,
    mutate('if (!Array.isArray(famPriorRows)) {', 'if (false) {'), 'family prior'));
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
