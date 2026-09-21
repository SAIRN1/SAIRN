// api/sf-auth.test.js
//
// REQUIREMENT: SAIRNfreedom employee credentials behave the way the other
//   sixteen do -- one generic login failure, a lockout that precedes the hash
//   comparison, a bootstrap trapdoor that cannot be reopened by deactivation,
//   and a deactivation lifecycle that cannot lock a post out of its own app.
//
// CROSS-TENANT-ISOLATION: none (this suite is about WHO inside a post may act;
//   the tenant boundary on sf_* is asserted in
//   api/sd-data-cross-tenant-dispatchers.test.js)
//
// Run:  node api/sf-auth.test.js
//
// ── WHY THIS EXISTS ───────────────────────────────────────────────────────
// api/sf-auth.js is new and is the third of five pieces that together close a
// finding: SAIRNfreedom served three Tier A resources -- sf_accounts,
// sf_ledger, sf_vendor_prices -- with NO employee session check of any kind.
// The licence key was the whole authorisation.
//
// EVERY ARM DRIVES THE REAL HANDLER against a PostgREST stand-in. The one
// thing this cannot test is the database: grants and RLS are asserted in the
// schema file's own verification queries, not here.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['sf', 'auth', 'suite', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://fixture.invalid';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY
  || ['fixture', 'service', 'key'].join('-');

const assert = require('assert');
const path = require('path');

const LIC = 'post-A-hash';
const OTHER = 'post-B-hash';

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}

// ── AN IN-MEMORY CREDENTIAL TABLE THAT HONOURS THE QUERY ─────────────────
// Filters on whichever `eq.` clauses the handler actually sends, the way
// PostgREST does -- so `active=eq.true` on loadEmployee is REAL here, and a
// deactivated row genuinely disappears from it rather than being filtered by
// the test's own charity.
function store(rows) {
  const calls = [];
  const db = rows.slice();
  return {
    calls: calls, rows: db,
    fn: async function (url, opts) {
      const u = String(url);
      calls.push({ url: u, method: (opts && opts.method) || 'GET' });
      const q = u.indexOf('?') >= 0 ? u.slice(u.indexOf('?') + 1) : '';
      const eqs = [];
      q.split('&').forEach(function (p) {
        const m = p.match(/^([a-z_]+)=eq\.(.*)$/);
        if (m) eqs.push([m[1], decodeURIComponent(m[2])]);
      });
      const match = function (r) {
        return eqs.every(function (kv) { return String(r[kv[0]]) === kv[1]; });
      };
      const method = (opts && opts.method) || 'GET';
      if (method === 'POST') {
        const sent = JSON.parse(opts.body);
        const i = db.findIndex(function (r) {
          return r.license_hash === sent.license_hash && r.employee_id === sent.employee_id;
        });
        if (i >= 0) db[i] = Object.assign({}, db[i], sent); else db.push(Object.assign({}, sent));
        return { ok: true, status: 200, json: async function () { return [sent]; } };
      }
      if (method === 'PATCH') {
        const patch = JSON.parse(opts.body);
        const touched = [];
        db.forEach(function (r, i) {
          if (match(r)) { db[i] = Object.assign({}, r, patch); touched.push(db[i]); }
        });
        // ── THE ANSWER DEPENDS ON THE Prefer HEADER, THE WAY IT REALLY DOES ─
        // WITHOUT `return=representation` PostgREST answers 204 No Content and
        // parsing the body THROWS -- the defect rf proved live on 2026-08-27,
        // where the outer catch turned a landed mutation into a 502.
        // api/sf-auth.js's own patchEmployee (the lockout counters) takes that
        // path. api/_lib/employee-lifecycle.js DOES set the header and expects
        // a body, so answering 204 to it would be modelling a server that does
        // not exist and would fail a correct handler.
        const prefer = (opts.headers && (opts.headers.Prefer || opts.headers.prefer)) || '';
        if (prefer.indexOf('return=representation') !== -1) {
          return { ok: true, status: 200, json: async function () { return touched; } };
        }
        return { ok: true, status: 204, json: async function () { throw new SyntaxError('Unexpected end of JSON input'); } };
      }
      // HONOURS `select=` THE WAY POSTGREST DOES. Without this the mock hands
      // back whole rows including pin_hash, so an assertion that the roster
      // does not leak credential material would be asserting something about
      // the TEST rather than about the handler -- it would fail on a correct
      // handler and pass on one that asked for everything.
      const sel = (q.split('&').filter(function (p) { return p.indexOf('select=') === 0; })[0] || '')
        .slice('select='.length);
      const hits = db.filter(match);
      if (!sel || sel === '*') {
        return { ok: true, status: 200, json: async function () { return hits; } };
      }
      const cols = sel.split(',').map(function (c) { return c.trim(); }).filter(Boolean);
      const projected = hits.map(function (r) {
        const out = {};
        cols.forEach(function (c) { if (c in r) out[c] = r[c]; });
        return out;
      });
      return { ok: true, status: 200, json: async function () { return projected; } };
    }
  };
}

function load(licHash, fetchImpl, active) {
  const lic = path.join(__dirname, '_lib', 'license');
  delete require.cache[require.resolve(lic)];
  require.cache[require.resolve(lic)] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: active !== false, license_hash: licHash,
                 trial_ends_at: null, stripe_subscription_id: null, app_id: 'sairnfreedom' };
      }
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sf-auth.js')];
  return require('./sf-auth.js');
}

function req(body, token) {
  const headers = { authorization: 'Bearer KEY' };
  if (token) headers['x-sd-auth'] = token;
  return { method: 'POST', headers: headers, body: body };
}

async function call(h, body, token) {
  const res = mockRes();
  await h(req(body, token), res);
  return res;
}

(async function () {
  console.log('SAIRNfreedom employee credentials -- api/sf-auth.js');

  // ════════════════════════════════════════════════════════════════════════
  section('THE ROLE VOCABULARY IS THE APP\'S OWN, NOT INVENTED HERE');

  await test('ROLES_BY_APP, the schema check constraint and CAPABILITIES agree', async () => {
    const fs = require('fs');
    const root = path.join(__dirname, '..');
    const auth = fs.readFileSync(path.join(__dirname, '_lib', 'auth.js'), 'utf8');
    const a = auth.slice(auth.indexOf('sairnfreedom: ['));
    const roles = new Set((a.slice(0, a.indexOf(']')).match(/'[a-z.]+'/g) || [])
      .map(function (s) { return s.replace(/'/g, ''); }));
    const sql = fs.readFileSync(path.join(root, 'sql', 'sairnfreedom_employee_auth_schema.sql'), 'utf8');
    const seg = sql.slice(sql.indexOf('role in ('), sql.indexOf('))', sql.indexOf('role in (')));
    const cons = new Set((seg.match(/'[a-z.]+'/g) || []).map(function (s) { return s.replace(/'/g, ''); }));
    const html = fs.readFileSync(path.join(root, 'sairnfreedom.html'), 'utf8');
    const cap = html.slice(html.indexOf('var CAPABILITIES = ['));
    const caps = new Set((cap.slice(0, cap.indexOf('];')).match(/id:'[a-z.]+'/g) || [])
      .map(function (s) { return s.replace(/id:'|'/g, ''); }));
    // THE LIST LIVES IN THREE PLACES and nothing else checks that. A drift
    // here means a capability the UI offers that the server refuses, or a
    // role the server accepts that the database rejects with a check
    // violation -- the second is a 400 nobody can read.
    assert.deepStrictEqual(Array.from(roles).sort(), Array.from(caps).sort(),
      'ROLES_BY_APP.sairnfreedom and sairnfreedom.html CAPABILITIES disagree');
    assert.deepStrictEqual(Array.from(cons).sort(), Array.from(caps).sort(),
      'the schema check constraint and CAPABILITIES disagree');
    assert.strictEqual(caps.size, 10, 'expected ten capabilities, got ' + caps.size);
  });

  // ════════════════════════════════════════════════════════════════════════
  section('BOOTSTRAP AND THE TRAPDOOR');

  await test('bootstrap on an empty licence mints the SOLE capability', async () => {
    const s = store([]);
    const h = load(LIC, s.fn);
    const r = await call(h, { action: 'bootstrap', employee_id: 'gov', pin: '123456' });
    assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
    assert.strictEqual(r.body.role, 'post.govern', JSON.stringify(r.body));
    assert.ok(r.body.token, 'no token returned');
    assert.strictEqual(s.rows.length, 1);
    assert.ok(s.rows[0].pin_hash && s.rows[0].pin_salt, 'the PIN was not hashed');
    assert.ok(!/123456/.test(JSON.stringify(s.rows[0])), 'the raw PIN reached the row');
  });

  await test('a second bootstrap is refused 409 ALREADY_PROVISIONED', async () => {
    const s = store([{ license_hash: LIC, employee_id: 'gov', role: 'post.govern', active: true }]);
    const h = load(LIC, s.fn);
    const r = await call(h, { action: 'bootstrap', employee_id: 'other', pin: '123456' });
    assert.strictEqual(r.statusCode, 409, JSON.stringify(r.body));
    assert.strictEqual(r.body.error.code, 'ALREADY_PROVISIONED');
  });

  await test('THE TRAPDOOR: an all-INACTIVE licence still refuses bootstrap', async () => {
    // The single most important decision in the pattern. If this ever returns
    // 200, anyone holding the licence key can deactivate their way to a fresh
    // governor account and seize the post.
    const s = store([{ license_hash: LIC, employee_id: 'gov', role: 'post.govern', active: false }]);
    const h = load(LIC, s.fn);
    const r = await call(h, { action: 'bootstrap', employee_id: 'attacker', pin: '123456' });
    assert.strictEqual(r.statusCode, 409, 'a deactivated-only licence became re-bootstrappable: '
      + JSON.stringify(r.body));
    assert.strictEqual(r.body.error.code, 'ALREADY_PROVISIONED');
    const probe = s.calls.filter(function (c) { return c.method === 'GET'; })[0];
    assert.ok(probe && probe.url.indexOf('active=eq.') === -1,
      'the existence probe filters on active, which reopens the trapdoor: ' + (probe || {}).url);
  });

  await test('a 4-digit or 9-digit PIN is refused', async () => {
    for (const pin of ['1234', '123456789']) {
      const h = load(LIC, store([]).fn);
      const r = await call(h, { action: 'bootstrap', employee_id: 'gov', pin: pin });
      assert.strictEqual(r.statusCode, 400, 'pin ' + pin + ' was accepted');
    }
  });

  // ════════════════════════════════════════════════════════════════════════
  section('LOGIN, LOCKOUT AND THE GENERIC FAILURE');

  async function seeded() {
    const s = store([]);
    const h = load(LIC, s.fn);
    await call(h, { action: 'bootstrap', employee_id: 'gov', pin: '123456' });
    return s;
  }

  await test('the right PIN logs in and returns a token carrying the role', async () => {
    const s = await seeded();
    const h = load(LIC, s.fn);
    const r = await call(h, { action: 'login', employee_id: 'gov', pin: '123456' });
    assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
    assert.strictEqual(r.body.role, 'post.govern');
  });

  await test('a wrong PIN and an unknown employee give the SAME answer', async () => {
    const s = await seeded();
    let h = load(LIC, s.fn);
    const wrong = await call(h, { action: 'login', employee_id: 'gov', pin: '999999' });
    h = load(LIC, s.fn);
    const unknown = await call(h, { action: 'login', employee_id: 'nobody', pin: '123456' });
    assert.strictEqual(wrong.statusCode, 401);
    assert.strictEqual(unknown.statusCode, 401);
    // Never tell the caller which half was wrong -- that is an employee_id
    // oracle, and the timing equalisation in verifyPin exists for the same
    // reason. Two different messages would give away for free what the
    // constant-time compare is paid for.
    assert.deepStrictEqual(wrong.body, unknown.body,
      'a wrong PIN and an unknown employee are distinguishable: '
      + JSON.stringify(wrong.body) + ' vs ' + JSON.stringify(unknown.body));
  });

  await test('an unknown employee costs the SAME WORK as a known one', async () => {
    // ── A TIMING ARM, AND IT IS THE ONLY WAY TO SEE THIS PROPERTY ─────────
    // The first version of this suite asserted the two RESPONSES are
    // identical, which they are -- and a sabotage replacing the dummy-salt
    // branch with a bare `false` SURVIVED it, because the bodies stay the
    // same and only the TIME changes. That is the whole defect: from a real
    // 2026-08-03 auditor finding, a real employee_id took scrypt-cost
    // milliseconds to reject and an unknown one returned in under one, which
    // enumerates valid ids and then brute-forces PINs against only those.
    //
    // MEDIANS OVER SEVERAL RUNS, and the bar is deliberately loose -- a third
    // of the known-employee cost. scrypt is tens of milliseconds and the
    // short-circuit is sub-millisecond, so the real gap is an order of
    // magnitude; anything tight enough to be flaky would be measuring the
    // machine rather than the code.
    const s = await seeded();
    const median = function (xs) { xs.sort(function (a, b) { return a - b; }); return xs[Math.floor(xs.length / 2)]; };
    const timeOne = async function (employee_id) {
      const h = load(LIC, s.fn);
      const t0 = process.hrtime.bigint();
      await call(h, { action: 'login', employee_id: employee_id, pin: '999999' });
      return Number(process.hrtime.bigint() - t0) / 1e6;
    };
    const known = [], unknown = [];
    for (let i = 0; i < 5; i++) {
      // Reset the counter so the lockout never short-circuits the known path.
      s.rows.forEach(function (r) { r.failed_attempts = 0; r.locked_until = null; });
      known.push(await timeOne('gov'));
      unknown.push(await timeOne('definitely-not-a-real-employee'));
    }
    const k = median(known), u = median(unknown);
    assert.ok(u >= k / 3,
      'an unknown employee_id was rejected in ' + u.toFixed(1) + 'ms against '
      + k.toFixed(1) + 'ms for a real one -- that gap enumerates valid employee '
      + 'ids. verifyPin must run a full scrypt against a dummy salt when no row '
      + 'was found; never optimise that branch away.');
  });

  await test('an attempt at an UNKNOWN employee writes no counter', async () => {
    const s = await seeded();
    const before = s.calls.length;
    const h = load(LIC, s.fn);
    await call(h, { action: 'login', employee_id: 'nobody', pin: '000000' });
    const patches = s.calls.slice(before).filter(function (c) { return c.method === 'PATCH'; });
    assert.strictEqual(patches.length, 0,
      'a failed attempt at a nonexistent employee wrote ' + patches.length + ' PATCH(es)');
  });

  await test('five wrong PINs lock the account; the sixth never reaches the hash', async () => {
    const s = await seeded();
    for (let i = 0; i < 5; i++) {
      const h = load(LIC, s.fn);
      const r = await call(h, { action: 'login', employee_id: 'gov', pin: '999999' });
      assert.strictEqual(r.statusCode, 401, 'attempt ' + (i + 1) + ': ' + JSON.stringify(r.body));
    }
    const row = s.rows.filter(function (x) { return x.employee_id === 'gov'; })[0];
    assert.ok(row.locked_until, 'no lock was set after five failures');
    assert.strictEqual(row.failed_attempts, 0,
      'failed_attempts must reset to 0 when the lock is set, so a expired lock starts a fresh window');
    // And the RIGHT pin is refused too -- the lock precedes verifyPin.
    const h = load(LIC, s.fn);
    const r = await call(h, { action: 'login', employee_id: 'gov', pin: '123456' });
    assert.strictEqual(r.statusCode, 429, JSON.stringify(r.body));
    assert.strictEqual(r.body.error.code, 'LOCKED');
  });

  await test('a success clears BOTH failed_attempts and a stale locked_until', async () => {
    const s = await seeded();
    // An expired lock plus a counter: sc and sd condition only on the counter,
    // so a post-lockout success leaves locked_until in the row forever.
    s.rows.forEach(function (r) {
      if (r.employee_id === 'gov') {
        r.failed_attempts = 0;
        r.locked_until = new Date(Date.now() - 60000).toISOString();
      }
    });
    const h = load(LIC, s.fn);
    const r = await call(h, { action: 'login', employee_id: 'gov', pin: '123456' });
    assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
    const row = s.rows.filter(function (x) { return x.employee_id === 'gov'; })[0];
    assert.strictEqual(row.locked_until, null,
      'a stale locked_until survived a successful login: ' + row.locked_until);
  });

  // ════════════════════════════════════════════════════════════════════════
  section('SESSION SCOPE -- a token is bound to ONE app and ONE licence');

  await test('a token minted for post A is refused against post B', async () => {
    const s = await seeded();
    let h = load(LIC, s.fn);
    const login = await call(h, { action: 'login', employee_id: 'gov', pin: '123456' });
    const token = login.body.token;
    // Same token, a handler resolving the bearer key to a DIFFERENT licence.
    const s2 = store([{ license_hash: OTHER, employee_id: 'gov', role: 'post.govern', active: true }]);
    h = load(OTHER, s2.fn);
    const r = await call(h, { action: 'roster' }, token);
    assert.strictEqual(r.statusCode, 403,
      'a token minted for another licence was accepted: ' + JSON.stringify(r.body));
  });

  await test('a token minted for ANOTHER APP is refused by whoami', async () => {
    // ── DRIVEN THROUGH whoami, NOT roster, AND THE REASON IS THE POINT ─────
    // The first version of this arm used `roster` and SURVIVED a sabotage that
    // dropped `APP` from the verification, because a stonedesk token carries
    // role 'owner', 'owner' is not in sairnfreedom's MANAGEMENT_ROLES, and the
    // ROLE check refused it first. The arm passed for the wrong reason and
    // proved nothing about the app check.
    //
    // whoami has NO role gate -- the app argument is the only thing standing
    // between a valid token from another SAIRN app and this post's identity.
    const { signSessionToken } = require('./_lib/auth');
    const foreign = signSessionToken({ app: 'stonedesk', employee_id: 'gov',
                                       role: 'owner', license_hash: LIC });
    const s = await seeded();
    const h = load(LIC, s.fn);
    const r = await call(h, { action: 'whoami' }, foreign);
    assert.strictEqual(r.statusCode, 401,
      'a valid token from another SAIRN app was accepted as this post identity: '
      + JSON.stringify(r.body));
  });

  // ════════════════════════════════════════════════════════════════════════
  section('SETUP, ROSTER AND WHOAMI');

  async function withGovernor() {
    const s = await seeded();
    const h = load(LIC, s.fn);
    const login = await call(h, { action: 'login', employee_id: 'gov', pin: '123456' });
    return { s: s, token: login.body.token };
  }

  await test('a governor provisions a finance officer', async () => {
    const { s, token } = await withGovernor();
    const h = load(LIC, s.fn);
    const r = await call(h, { action: 'setup', employee_id: 'quartermaster',
                              pin: '654321', role: 'finance.write' }, token);
    assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
    assert.strictEqual(r.body.role, 'finance.write');
    assert.strictEqual(s.rows.length, 2);
  });

  await test('a capability that is not in the list is refused', async () => {
    const { s, token } = await withGovernor();
    const h = load(LIC, s.fn);
    const r = await call(h, { action: 'setup', employee_id: 'x', pin: '654321',
                              role: 'superuser' }, token);
    assert.strictEqual(r.statusCode, 400, JSON.stringify(r.body));
  });

  await test('a NON-provisioning capability cannot provision', async () => {
    const { s, token } = await withGovernor();
    let h = load(LIC, s.fn);
    await call(h, { action: 'setup', employee_id: 'qm', pin: '654321', role: 'finance.write' }, token);
    h = load(LIC, s.fn);
    const login = await call(h, { action: 'login', employee_id: 'qm', pin: '654321' });
    h = load(LIC, s.fn);
    const r = await call(h, { action: 'setup', employee_id: 'sneak', pin: '111111',
                              role: 'post.govern' }, login.body.token);
    assert.strictEqual(r.statusCode, 403, 'finance.write minted a credential: ' + JSON.stringify(r.body));
    assert.strictEqual(r.body.error.code, 'FORBIDDEN');
  });

  await test('a DEACTIVATED governor cannot still provision on an old token', async () => {
    // Only rf re-checks caller-active in setup among the sixteen. Without it a
    // just-deactivated governor mints credentials for up to 12h.
    const { s, token } = await withGovernor();
    s.rows.forEach(function (r) { if (r.employee_id === 'gov') r.active = false; });
    const h = load(LIC, s.fn);
    const r = await call(h, { action: 'setup', employee_id: 'x', pin: '654321',
                              role: 'records.write' }, token);
    assert.strictEqual(r.statusCode, 403, JSON.stringify(r.body));
    assert.strictEqual(r.body.error.code, 'CREDENTIAL_INACTIVE');
  });

  await test('the roster INCLUDES inactive rows and NEVER returns a hash', async () => {
    const { s, token } = await withGovernor();
    let h = load(LIC, s.fn);
    await call(h, { action: 'setup', employee_id: 'gone', pin: '654321', role: 'records.write' }, token);
    s.rows.forEach(function (r) { if (r.employee_id === 'gone') r.active = false; });
    h = load(LIC, s.fn);
    const r = await call(h, { action: 'roster' }, token);
    assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
    const ids = r.body.employees.map(function (e) { return e.employee_id; });
    assert.ok(ids.indexOf('gone') !== -1,
      'a deactivated person is invisible in the roster, so nobody can turn them back on');
    const blob = JSON.stringify(r.body);
    assert.ok(blob.indexOf('pin_hash') === -1 && blob.indexOf('pin_salt') === -1,
      'the roster leaked credential material');
  });

  await test('whoami returns the role from the ROW, not from the token', async () => {
    const { s, token } = await withGovernor();
    // A role change via setup must take effect on the next call rather than
    // waiting out the token's 12h life.
    s.rows.forEach(function (r) { if (r.employee_id === 'gov') r.role = 'records.write'; });
    const h = load(LIC, s.fn);
    const r = await call(h, { action: 'whoami' }, token);
    assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
    assert.strictEqual(r.body.role, 'records.write',
      'whoami echoed the token role instead of reading the row');
  });

  await test('whoami REFUSES a still-valid token whose credential was deactivated', async () => {
    const { s, token } = await withGovernor();
    s.rows.forEach(function (r) { if (r.employee_id === 'gov') r.active = false; });
    const h = load(LIC, s.fn);
    const r = await call(h, { action: 'whoami' }, token);
    assert.strictEqual(r.statusCode, 401,
      'a revoked account renders as logged in: ' + JSON.stringify(r.body));
  });

  // ════════════════════════════════════════════════════════════════════════
  section('THE DEACTIVATION LIFECYCLE');

  await test('a deactivated person can no longer log in', async () => {
    const { s, token } = await withGovernor();
    let h = load(LIC, s.fn);
    await call(h, { action: 'setup', employee_id: 'qm', pin: '654321', role: 'finance.write' }, token);
    h = load(LIC, s.fn);
    const off = await call(h, { action: 'set_active', employee_id: 'qm', active: false,
                                reason: 'left the post' }, token);
    assert.strictEqual(off.statusCode, 200, JSON.stringify(off.body));
    h = load(LIC, s.fn);
    const r = await call(h, { action: 'login', employee_id: 'qm', pin: '654321' });
    assert.strictEqual(r.statusCode, 401, 'a deactivated credential still logs in');
  });

  await test('reactivation restores the login, and the ROW was never deleted', async () => {
    const { s, token } = await withGovernor();
    let h = load(LIC, s.fn);
    await call(h, { action: 'setup', employee_id: 'qm', pin: '654321', role: 'finance.write' }, token);
    h = load(LIC, s.fn);
    await call(h, { action: 'set_active', employee_id: 'qm', active: false, reason: 'suspended' }, token);
    h = load(LIC, s.fn);
    const on = await call(h, { action: 'set_active', employee_id: 'qm', active: true }, token);
    assert.strictEqual(on.statusCode, 200, JSON.stringify(on.body));
    h = load(LIC, s.fn);
    const r = await call(h, { action: 'login', employee_id: 'qm', pin: '654321' });
    assert.strictEqual(r.statusCode, 200, 'reactivation did not restore the login');
    assert.strictEqual(s.rows.length, 2, 'a row was deleted instead of deactivated');
  });

  await test('deactivating needs a REASON; reactivating does not', async () => {
    const { s, token } = await withGovernor();
    let h = load(LIC, s.fn);
    await call(h, { action: 'setup', employee_id: 'qm', pin: '654321', role: 'finance.write' }, token);
    h = load(LIC, s.fn);
    const noReason = await call(h, { action: 'set_active', employee_id: 'qm', active: false }, token);
    assert.strictEqual(noReason.statusCode, 400, JSON.stringify(noReason.body));
    h = load(LIC, s.fn);
    const on = await call(h, { action: 'set_active', employee_id: 'qm', active: true }, token);
    assert.strictEqual(on.statusCode, 200, 'reactivating was refused for want of a reason');
  });

  await test('SELF-DEACTIVATION is refused, and BEFORE the active re-check', async () => {
    const { s, token } = await withGovernor();
    // Deactivate the caller first: an already-deactivated caller deactivating
    // THEMSELVES must still get SELF_DEACTIVATE, not CREDENTIAL_INACTIVE.
    // That ordering is deliberate and is what this arm pins.
    s.rows.forEach(function (r) { if (r.employee_id === 'gov') r.active = false; });
    const h = load(LIC, s.fn);
    const r = await call(h, { action: 'set_active', employee_id: 'gov', active: false,
                              reason: 'oops' }, token);
    assert.strictEqual(r.statusCode, 409, JSON.stringify(r.body));
    assert.strictEqual(r.body.error.code, 'SELF_DEACTIVATE',
      'the guard order changed -- an already-inactive self-deactivation now reports '
      + (r.body.error || {}).code);
  });

  await test('THE OTHER ROUTE TO ZERO GOVERNORS: setup cannot downgrade the last one', async () => {
    // ── FOUND BY CHECKING A PRESS-ON POINT INSTEAD OF FILING IT ───────────
    // set_active guards DEACTIVATING the last sole-capability holder and says
    // nothing about CHANGING their capability. `setup` upserts on
    // (license_hash, employee_id), so the only governor could set their own
    // role to records.write, reach ZERO governors, and find bootstrap still
    // answering 409 -- a licence dead through the API, by a route the
    // deactivation guard was never looking at. Driven before the fix existed:
    // 200, zero active governors, re-bootstrap 409.
    const { s, token } = await withGovernor();
    let h = load(LIC, s.fn);
    const down = await call(h, { action: 'setup', employee_id: 'gov',
                                 pin: '123456', role: 'records.write' }, token);
    assert.strictEqual(down.statusCode, 409,
      'the only governor downgraded themselves and emptied the post: '
      + JSON.stringify(down.body));
    assert.strictEqual(down.body.error.code, 'LAST_ADMIN', JSON.stringify(down.body));
    const govs = s.rows.filter(function (r) {
      return r.active === true && r.role === 'post.govern'; }).length;
    assert.strictEqual(govs, 1, 'the refusal did not prevent the write');
  });

  await test('...but a SECOND governor makes that change ordinary business', async () => {
    // The other side of the same guard. A rule that blocks a legitimate
    // handover is a rule people route around.
    const { s, token } = await withGovernor();
    let h = load(LIC, s.fn);
    await call(h, { action: 'setup', employee_id: 'gov2', pin: '654321',
                    role: 'post.govern' }, token);
    h = load(LIC, s.fn);
    const down = await call(h, { action: 'setup', employee_id: 'gov',
                                 pin: '123456', role: 'records.write' }, token);
    assert.strictEqual(down.statusCode, 200, JSON.stringify(down.body));
  });

  await test('a DEPUTY does not count as a governor for the downgrade guard', async () => {
    // Counting the PROVISIONING list here instead of the sole capability
    // survived the first sabotage run: with a governor and a deputy the count
    // is two, the guard does not fire, and the sole governor downgrades
    // themselves to zero. The deputy provisions; it does not govern.
    const { s, token } = await withGovernor();
    let h = load(LIC, s.fn);
    await call(h, { action: 'setup', employee_id: 'deputy', pin: '654321',
                    role: 'post.govern.deputy' }, token);
    h = load(LIC, s.fn);
    const down = await call(h, { action: 'setup', employee_id: 'gov',
                                 pin: '123456', role: 'records.write' }, token);
    assert.strictEqual(down.statusCode, 409,
      'a deputy was counted as a governor, so the only real governor emptied '
      + 'the post: ' + JSON.stringify(down.body));
  });

  await test('an INACTIVE governor can be re-roled -- it is not holding the post up', async () => {
    // The other direction of the same condition, and it also survived the
    // first run. A guard that refuses more than it must is a guard people
    // route around: a deactivated governor is not what keeps the licence
    // reachable, so changing their capability is ordinary record-keeping.
    const { s, token } = await withGovernor();
    let h = load(LIC, s.fn);
    await call(h, { action: 'setup', employee_id: 'old', pin: '654321',
                    role: 'post.govern' }, token);
    s.rows.forEach(function (r) { if (r.employee_id === 'old') r.active = false; });
    h = load(LIC, s.fn);
    const r = await call(h, { action: 'setup', employee_id: 'old', pin: '654321',
                              role: 'history.write' }, token);
    assert.strictEqual(r.statusCode, 200,
      'a DEACTIVATED governor could not be re-roled, though an active governor '
      + 'remains: ' + JSON.stringify(r.body));
  });

  await test('and a governor can still be PROMOTED without tripping the guard', async () => {
    const { s, token } = await withGovernor();
    let h = load(LIC, s.fn);
    await call(h, { action: 'setup', employee_id: 'qm', pin: '654321',
                    role: 'finance.write' }, token);
    h = load(LIC, s.fn);
    const up = await call(h, { action: 'setup', employee_id: 'qm', pin: '654321',
                               role: 'post.govern' }, token);
    assert.strictEqual(up.statusCode, 200, JSON.stringify(up.body));
  });

  await test('THE LAST-GOVERNOR REFUSAL: a deputy cannot deactivate the sole governor', async () => {
    // LIVE HERE in a way it is not in rf. rf has one provisioning role, so
    // reaching its guard needs two active owners and is unreachable by
    // construction. SAIRNfreedom has TWO provisioning capabilities and only
    // ONE of them is `sole`, so a deputy deactivating the governor satisfies
    // every condition.
    const { s, token } = await withGovernor();
    let h = load(LIC, s.fn);
    await call(h, { action: 'setup', employee_id: 'deputy', pin: '654321',
                    role: 'post.govern.deputy' }, token);
    h = load(LIC, s.fn);
    const dep = await call(h, { action: 'login', employee_id: 'deputy', pin: '654321' });
    assert.strictEqual(dep.statusCode, 200, JSON.stringify(dep.body));
    h = load(LIC, s.fn);
    const r = await call(h, { action: 'set_active', employee_id: 'gov', active: false,
                              reason: 'coup' }, dep.body.token);
    assert.strictEqual(r.statusCode, 409,
      'the deputy deactivated the only governor, which bricks the licence: '
      + JSON.stringify(r.body));
    // THE SHARED HELPER'S SPELLING, not rf's. The platform has two --
    // LAST_OWNER/remaining_owners in rf/sc/sd's hand-written set_active, and
    // LAST_ADMIN/remaining_admins in api/_lib/employee-lifecycle.js -- and a
    // client written against one breaks against the other. This endpoint is
    // wired to the helper, so it emits the helper's.
    assert.strictEqual(r.body.error.code, 'LAST_ADMIN', JSON.stringify(r.body));
    const gov = s.rows.filter(function (x) { return x.employee_id === 'gov'; })[0];
    assert.strictEqual(gov.active, true, 'the refusal did not prevent the write');
  });

  await test('a deputy CAN be deactivated while a governor is in place', async () => {
    // The other side of the same guard: it counts the SOLE capability, not the
    // provisioning list, so ordinary business is not blocked.
    const { s, token } = await withGovernor();
    let h = load(LIC, s.fn);
    await call(h, { action: 'setup', employee_id: 'deputy', pin: '654321',
                    role: 'post.govern.deputy' }, token);
    h = load(LIC, s.fn);
    const r = await call(h, { action: 'set_active', employee_id: 'deputy', active: false,
                              reason: 'stepped down' }, token);
    assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
  });

  await test('a no-op set_active answers unchanged:true and writes nothing', async () => {
    const { s, token } = await withGovernor();
    let h = load(LIC, s.fn);
    await call(h, { action: 'setup', employee_id: 'qm', pin: '654321', role: 'finance.write' }, token);
    const before = s.calls.filter(function (c) { return c.method === 'PATCH'; }).length;
    h = load(LIC, s.fn);
    const r = await call(h, { action: 'set_active', employee_id: 'qm', active: true }, token);
    assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
    assert.strictEqual(r.body.unchanged, true, JSON.stringify(r.body));
    const after = s.calls.filter(function (c) { return c.method === 'PATCH'; }).length;
    assert.strictEqual(after, before, 'a no-op wrote to the table');
  });

  await test('an unknown target is 404, not a silent success', async () => {
    const { s, token } = await withGovernor();
    const h = load(LIC, s.fn);
    const r = await call(h, { action: 'set_active', employee_id: 'ghost', active: false,
                              reason: 'x' }, token);
    assert.strictEqual(r.statusCode, 404, JSON.stringify(r.body));
    assert.strictEqual(r.body.error.code, 'NOT_FOUND');
  });

  await test('a 204 PATCH is NOT read as a failure', async () => {
    // rf proved this live on 2026-08-27: PostgREST answers PATCH with 204 and
    // no body, parsing it threw, the outer catch made it a 502, and the caller
    // saw a failure for a mutation that had already landed. The mock returns a
    // 204 whose .json() throws, so this arm reproduces the real shape.
    const { s, token } = await withGovernor();
    let h = load(LIC, s.fn);
    await call(h, { action: 'setup', employee_id: 'qm', pin: '654321', role: 'finance.write' }, token);
    h = load(LIC, s.fn);
    const r = await call(h, { action: 'set_active', employee_id: 'qm', active: false,
                              reason: 'left' }, token);
    assert.strictEqual(r.statusCode, 200,
      'a successful 204 PATCH was reported as a failure: ' + JSON.stringify(r.body));
    const row = s.rows.filter(function (x) { return x.employee_id === 'qm'; })[0];
    assert.strictEqual(row.active, false, 'the write did not land');
  });

  // ════════════════════════════════════════════════════════════════════════
  section('DIAGNOSTICS -- a missing migration and a missing grant are not one 502');

  await test('a missing table answers 503 NOT_PROVISIONED and names the file', async () => {
    const h = load(LIC, async function () {
      return { ok: false, status: 404, json: async function () {
        return { code: 'PGRST205', message: 'relation "sairnfreedom_employee_auth" does not exist' }; } };
    });
    const r = await call(h, { action: 'bootstrap', employee_id: 'gov', pin: '123456' });
    assert.strictEqual(r.statusCode, 503, JSON.stringify(r.body));
    assert.strictEqual(r.body.error.code, 'NOT_PROVISIONED');
    assert.match(r.body.error.message, /sairnfreedom_employee_auth_schema\.sql/);
  });

  await test('a missing GRANT answers 503 NOT_GRANTED, not the same 502', async () => {
    const h = load(LIC, async function () {
      return { ok: false, status: 403, json: async function () {
        return { code: '42501', message: 'permission denied for table sairnfreedom_employee_auth' }; } };
    });
    const r = await call(h, { action: 'bootstrap', employee_id: 'gov', pin: '123456' });
    assert.strictEqual(r.statusCode, 503, JSON.stringify(r.body));
    assert.strictEqual(r.body.error.code, 'NOT_GRANTED',
      'a 42501 was collapsed into the generic upstream error, which is the '
      + 'difference between a five-second fix and an hour of guessing');
  });

  await test('check_license answers BEFORE any table access', async () => {
    const s = store([]);
    const h = load(LIC, s.fn);
    const r = await call(h, { action: 'check_license' });
    assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
    assert.strictEqual(s.calls.length, 0,
      'check_license touched the data store, so it cannot answer on an unprovisioned licence');
  });

  await test('an unknown action does not name the verb vocabulary to a bad licence', async () => {
    const lic = path.join(__dirname, '_lib', 'license');
    delete require.cache[require.resolve(lic)];
    require.cache[require.resolve(lic)] = {
      exports: { validateLicenseKey: async function () { return { valid: false }; } }
    };
    delete require.cache[require.resolve('./sf-auth.js')];
    const h = require('./sf-auth.js');
    const r = await call(h, { action: 'not_a_real_action' });
    assert.strictEqual(r.statusCode, 401,
      'the envelope gate answered above licence validation: ' + JSON.stringify(r.body));
    assert.strictEqual(r.body.error.code, 'INVALID_LICENSE');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
