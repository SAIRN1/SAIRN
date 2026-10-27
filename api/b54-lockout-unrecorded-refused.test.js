// hank b54 R1 -- a lockout that cannot be recorded is not a lockout. Every PIN
// login wrote the failed attempt with a PATCH whose result nobody checked, so
// a missing UPDATE grant or a 5xx meant failed_attempts never rose and PIN
// guessing was unbounded behind an ordinary 401. Now the attempt answers 503
// LOCKOUT_UNAVAILABLE when its PATCH fails.
//
// D. Driven: api/alf-auth.js (the shared recordFailure helper, 11 files) and
//    api/sd-auth.js (the inline PATCH, 6 files) -- wrong PIN with the PATCH
//    failing -> 503; with the PATCH succeeding -> 401 (control).
// S. Source: all 17 PIN *-auth files carry the refusal and none still says
//    "non-fatal -- the ... is refused either way" on that PATCH.
// M. Mutants: remove the check in each driven file -> its arm goes red.
//
// Run: node api/b54-lockout-unrecorded-refused.test.js    Exit 0 pass, 1 fail

'use strict';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || ['lockout', 'b54', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const Module = require('module');
const { hashPin } = require('./_lib/auth');

const HASH = 'b54-hash';
const PIN = '24681357';
const CRED = hashPin(PIN);

function load(file, src, app) {
  const lic = require.resolve('./_lib/license');
  delete require.cache[lic];
  require.cache[lic] = { id: lic, filename: lic, loaded: true, exports: {
    validateLicenseKey: async function () {
      return { valid: true, active: true, license_hash: HASH, trial_ends_at: null,
               stripe_subscription_id: null, app_id: app };
    } } };
  const full = path.join(__dirname, file);
  const m = new Module(full, module);
  m.filename = full;
  m.paths = Module._nodeModulePaths(__dirname);
  m._compile(src, full);
  return m.exports;
}

async function login(file, src, app, patchStatus) {
  const h = load(file, src, app);
  const patches = [];
  const prev = global.fetch;
  global.fetch = async function (url, o) {
    const u = String(url);
    const method = (o && o.method) || 'GET';
    if (method === 'PATCH') {
      patches.push(u);
      const ok = patchStatus < 300;
      return { ok: ok, status: patchStatus, text: async () => (ok ? '' : '{"code":"42501"}'), json: async () => (ok ? [] : { code: '42501' }) };
    }
    if (/employee_auth\?/.test(u)) {
      return { ok: true, status: 200, json: async () => [{ license_hash: HASH, employee_id: 'E1', role: 'owner',
        pin_hash: CRED.pin_hash, pin_salt: CRED.pin_salt, failed_attempts: 0, locked_until: null, active: true }] };
    }
    if (method !== 'GET') return { ok: true, status: 201, text: async () => '', json: async () => [] };
    return { ok: true, status: 200, json: async () => [] };
  };
  const res = { statusCode: null, body: null, setHeader: function () { return res; },
                status: function (c) { res.statusCode = c; return res; },
                json: function (b) { res.body = b; return res; }, end: function () { return res; } };
  try {
    await h({ method: 'POST', headers: { authorization: 'Bearer KEY' },
      body: { action: 'login', employee_id: 'E1', pin: '99999999' } }, res);
  } finally { global.fetch = prev; }
  return { res: res, patches: patches };
}
const code = (r) => ((r.body || {}).error || {}).code;

const DRIVEN = [
  { tag: 'D1', file: 'alf-auth.js', app: 'sairncare' },
  { tag: 'D2', file: 'sd-auth.js', app: 'stonedesk' },
];
async function arm(t, src) {
  const bad = await login(t.file, src, t.app, 500);
  assert.ok(bad.patches.length >= 1, t.file + ': no failed-attempt PATCH was attempted');
  assert.deepStrictEqual([bad.res.statusCode, code(bad.res)], [503, 'LOCKOUT_UNAVAILABLE'], t.file + ' PATCH 500: ' + JSON.stringify(bad.res.body));
  const good = await login(t.file, src, t.app, 204);
  assert.deepStrictEqual([good.res.statusCode, code(good.res)], [401, 'INVALID_CREDENTIALS'], t.file + ' control: ' + JSON.stringify(good.res.body));
}

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); pass++; console.log('  ok   ' + name); }
  catch (e) { fail++; console.log('  FAIL ' + name + '\n       ' + String(e.message).slice(0, 300)); }
}
async function mustFail(fn, name) {
  try { await fn(); } catch (e) {
    if (e instanceof assert.AssertionError) return;
    throw new Error(name + ': non-assertion error, the mutant proves nothing: ' + e.message);
  }
  throw new Error(name + ' survived');
}

(async function () {
  console.log('b54 -- an unrecordable failed attempt is refused 503, not a quiet 401');
  for (const t of DRIVEN) {
    const src = fs.readFileSync(path.join(__dirname, t.file), 'utf8');
    await test(t.tag + '. ' + t.file + ': wrong PIN + failed-attempt PATCH 500 -> 503 LOCKOUT_UNAVAILABLE (control: PATCH ok -> 401)', () => arm(t, src));
  }
  await test('S1. all 17 PIN *-auth files carry LOCKOUT_UNAVAILABLE and none keeps the unchecked "refused either way" PATCH', () => {
    const files = fs.readdirSync(__dirname).filter((f) => /-auth\.js$/.test(f));
    const withLockout = files.filter((f) => /failed_attempts: attempts/.test(fs.readFileSync(path.join(__dirname, f), 'utf8')));
    assert.strictEqual(withLockout.length, 17, 'PIN auth files with a failed-attempt PATCH: ' + withLockout.length + ' ' + withLockout.join(','));
    const missing = withLockout.filter((f) => fs.readFileSync(path.join(__dirname, f), 'utf8').indexOf("code: 'LOCKOUT_UNAVAILABLE'") === -1);
    assert.deepStrictEqual(missing, [], 'no refusal in: ' + missing.join(','));
    const stale = withLockout.filter((f) => /non-fatal — the (attempt|login) is refused either way/.test(fs.readFileSync(path.join(__dirname, f), 'utf8')));
    assert.deepStrictEqual(stale, [], 'unchecked PATCH still in: ' + stale.join(','));
  });
  // b54 item 2 (the two not-Tier-A OPEN sites left by the b52 sweep): SOURCE pins.
  await test('S2. sd-data.js lead-time and style-profile folds refuse a non-list prior read (source pins)', () => {
    const sd = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
    for (const msg of ['The saved lead times could not be read back, so nothing was changed.',
                       'The saved style profile could not be read back, so nothing was changed.']) {
      assert.strictEqual(sd.split(msg).length - 1, 1, 'missing or duplicated: ' + msg);
    }
  });
  const MUT = [
    { t: DRIVEN[0], from: '    if (!lockRes || !lockRes.ok) {\n      console.error(', to: '    if (false) {\n      console.error(' },
    { t: DRIVEN[1], from: '          if (!lockRes || !lockRes.ok) {\n            console.error(', to: '          if (false) {\n            console.error(' },
  ];
  for (const [i, mu] of MUT.entries()) {
    const src = fs.readFileSync(path.join(__dirname, mu.t.file), 'utf8');
    await test('M' + (i + 1) + '. ' + mu.t.file + ': the PATCH check removed -> ' + mu.t.tag + ' red', () => {
      const n = src.split(mu.from).length - 1;
      if (n !== 1) throw new Error('mutant anchor found ' + n + ' times');
      return mustFail(() => arm(mu.t, src.replace(mu.from, mu.to)), mu.t.file);
    });
  }
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
