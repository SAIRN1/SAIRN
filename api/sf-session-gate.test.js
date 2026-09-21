// api/sf-session-gate.test.js
//
// REQUIREMENT: sf_accounts, sf_ledger and sf_vendor_prices -- SAIRNfreedom's
//   three Tier A resources -- are reachable only by a signed-in employee of
//   THAT post whose credential is still active.
//
// CROSS-TENANT-ISOLATION: none (the tenant boundary on these three is asserted
//   in api/sd-data-cross-tenant-dispatchers.test.js; this suite is about WHO
//   inside a post may act)
//
// Run:  node api/sf-session-gate.test.js
//
// ── WHAT THIS IS ──────────────────────────────────────────────────────────
// The END-TO-END arm of a five-piece change. The other four are asserted where
// they live -- the schema by its own verification queries, ROLES_BY_APP and
// api/sf-auth.js by api/sf-auth.test.js, the client header by inspection of
// sairnfreedom.html's single transport. This one drives the WHOLE CHAIN:
// api/sf-auth.js mints a real session, and api/sd-data.js's gate is asked to
// accept or refuse it.
//
// ── THE ORDER OF THE FIVE PIECES WAS DRIVEN, NOT CHOSEN ──────────────────
// Arming the gate first answers 403 to every real call, because until today
// SAIRNfreedom had no way to produce a session: no sf_employee_auth table, no
// `sairnfreedom` in ROLES_BY_APP (so signSessionToken THREW), no
// api/sf-auth.js, and no X-SD-Auth header anywhere in the client. The first
// arm below reproduces that state and proves the refusal, so the reason for
// the ordering is in the suite rather than only in a commit message.
//
// ── WHAT IT DOES NOT COVER ───────────────────────────────────────────────
// The database. The RLS policy and the grants at the foot of
// sql/sairnfreedom_employee_auth_schema.sql are not exercised here -- a wrong
// grant surfaces as a 42501 that api/sf-auth.js turns into NOT_GRANTED, which
// IS asserted, but the grant itself is a live-verification item.
//
// And the other 32 sf_ resources stay UNGATED by design. The last arm pins
// that, so widening the gate is a deliberate act rather than a side effect.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['sf', 'gate', 'chain', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://fixture.invalid';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY
  || ['fixture', 'service', 'key'].join('-');

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const LIC = 'post-A-hash';
const GATED = ['sf_accounts', 'sf_ledger', 'sf_vendor_prices'];

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

// One store serving BOTH handlers: the credential table api/sf-auth.js writes
// and api/sd-data.js's active re-check reads, plus the sf_ data rows. Using
// two stores would let the gate pass against a credential the auth endpoint
// never actually created.
function world() {
  const creds = [];
  const data = [
    { license_hash: LIC, account_id: 'A-1', data: { id: 'A-1', name: 'General Fund' } }
  ];
  const calls = [];
  return {
    creds: creds, calls: calls,
    fn: async function (url, opts) {
      const u = String(url);
      const method = (opts && opts.method) || 'GET';
      calls.push({ url: u, method: method });
      const q = u.indexOf('?') >= 0 ? u.slice(u.indexOf('?') + 1) : '';
      const eqs = [];
      q.split('&').forEach(function (p) {
        const m = p.match(/^([a-z_]+)=eq\.(.*)$/);
        if (m) eqs.push([m[1], decodeURIComponent(m[2])]);
      });
      const match = function (r) {
        return eqs.every(function (kv) { return String(r[kv[0]]) === kv[1]; });
      };
      const isCreds = u.indexOf('sairnfreedom_employee_auth') !== -1;
      const table = isCreds ? creds : data;
      if (method === 'POST') {
        const sent = JSON.parse(opts.body);
        const i = table.findIndex(function (r) {
          return r.license_hash === sent.license_hash
            && (isCreds ? r.employee_id === sent.employee_id : true);
        });
        if (i >= 0 && isCreds) table[i] = Object.assign({}, table[i], sent);
        else table.push(Object.assign({}, sent));
        return { ok: true, status: 200, json: async function () { return [sent]; } };
      }
      if (method === 'PATCH') {
        const patch = JSON.parse(opts.body);
        table.forEach(function (r, i) { if (match(r)) table[i] = Object.assign({}, r, patch); });
        return { ok: true, status: 204, json: async function () { throw new SyntaxError('no body'); } };
      }
      return { ok: true, status: 200, json: async function () { return table.filter(match); } };
    }
  };
}

function load(mod, licHash, fetchImpl) {
  const lic = path.join(__dirname, '_lib', 'license');
  delete require.cache[require.resolve(lic)];
  require.cache[require.resolve(lic)] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: licHash, trial_ends_at: null,
                 stripe_subscription_id: null, app_id: 'sairnfreedom' };
      }
    }
  };
  global.fetch = fetchImpl;
  const p = path.join(__dirname, mod);
  delete require.cache[require.resolve(p)];
  return require(p);
}

async function call(h, body, token) {
  const headers = { authorization: 'Bearer KEY' };
  if (token) headers['x-sd-auth'] = token;
  const res = mockRes();
  await h({ method: 'POST', headers: headers, body: body }, res);
  return res;
}

// Mints a REAL session through api/sf-auth.js -- never a hand-signed token.
// A hand-signed one would prove the gate accepts a signature; this proves the
// chain a real user walks actually produces something the gate accepts.
async function provision(w, employee_id, role) {
  let h = load('sf-auth.js', LIC, w.fn);
  if (!w.creds.length) {
    const r = await call(h, { action: 'bootstrap', employee_id: 'gov', pin: '123456' });
    assert.strictEqual(r.statusCode, 200, 'bootstrap failed: ' + JSON.stringify(r.body));
    if (employee_id === 'gov') return r.body.token;
  }
  const govLogin = await call(load('sf-auth.js', LIC, w.fn),
    { action: 'login', employee_id: 'gov', pin: '123456' });
  assert.strictEqual(govLogin.statusCode, 200, JSON.stringify(govLogin.body));
  if (employee_id === 'gov') return govLogin.body.token;
  h = load('sf-auth.js', LIC, w.fn);
  const s = await call(h, { action: 'setup', employee_id: employee_id, pin: '654321',
                            role: role }, govLogin.body.token);
  assert.strictEqual(s.statusCode, 200, 'setup failed: ' + JSON.stringify(s.body));
  const login = await call(load('sf-auth.js', LIC, w.fn),
    { action: 'login', employee_id: employee_id, pin: '654321' });
  assert.strictEqual(login.statusCode, 200, JSON.stringify(login.body));
  return login.body.token;
}

(async function () {
  console.log('SAIRNfreedom session gate -- the whole chain, end to end');

  // ════════════════════════════════════════════════════════════════════════
  section('THE STATE BEFORE ALL FIVE PIECES -- why the order was what it was');

  await test('no session at all is REFUSED on every gated resource', async () => {
    for (const resource of GATED) {
      const w = world();
      const h = load('sd-data.js', LIC, w.fn);
      const r = await call(h, { action: 'read', resource: resource, app_id: 'sairnfreedom' });
      assert.strictEqual(r.statusCode, 403,
        resource + ' served a caller with no session: ' + JSON.stringify(r.body));
      assert.strictEqual(r.body.error.code, 'FORBIDDEN');
    }
  });

  await test('...and that is exactly what a pre-2026-09-21 client would have got', async () => {
    // The client sent `Authorization: Bearer <licence>` and NOTHING else --
    // reproduced literally here. This is the arm that justifies arming the
    // gate FIFTH rather than first.
    const w = world();
    const h = load('sd-data.js', LIC, w.fn);
    const res = mockRes();
    await h({ method: 'POST', headers: { authorization: 'Bearer KEY' },
              body: { action: 'read', resource: 'sf_ledger', app_id: 'sairnfreedom' } }, res);
    assert.strictEqual(res.statusCode, 403, JSON.stringify(res.body));
  });

  // ════════════════════════════════════════════════════════════════════════
  section('THE CHAIN -- a real session minted by api/sf-auth.js is accepted');

  await test('a governor reads all three gated resources', async () => {
    for (const resource of GATED) {
      const w = world();
      const token = await provision(w, 'gov');
      const h = load('sd-data.js', LIC, w.fn);
      const r = await call(h, { action: 'read', resource: resource, app_id: 'sairnfreedom' }, token);
      assert.strictEqual(r.statusCode, 200,
        resource + ' refused a valid governor session: ' + JSON.stringify(r.body));
    }
  });

  await test('a finance officer reads the ledger -- the gate is about IDENTITY, not rank', async () => {
    // Deliberate: the gate asks "is this a signed-in, still-active employee of
    // this post", not "which capability". Narrowing it to a capability tier is
    // a product decision about who may see a ledger and nobody has made it.
    const w = world();
    const token = await provision(w, 'qm', 'finance.write');
    const h = load('sd-data.js', LIC, w.fn);
    const r = await call(h, { action: 'read', resource: 'sf_ledger', app_id: 'sairnfreedom' }, token);
    assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
  });

  await test('a WRITE is gated too, not only a read', async () => {
    const w = world();
    const token = await provision(w, 'gov');
    let h = load('sd-data.js', LIC, w.fn);
    const noTok = await call(h, { action: 'write', resource: 'sf_ledger',
                                  app_id: 'sairnfreedom', payload: { id: 'L-1' } });
    assert.strictEqual(noTok.statusCode, 403, JSON.stringify(noTok.body));
    h = load('sd-data.js', LIC, w.fn);
    const withTok = await call(h, { action: 'write', resource: 'sf_ledger',
                                    app_id: 'sairnfreedom', payload: { id: 'L-1' } }, token);
    assert.strictEqual(withTok.statusCode, 200, JSON.stringify(withTok.body));
  });

  // ════════════════════════════════════════════════════════════════════════
  section('THE PART THE TOKEN CANNOT PROVE -- still-active NOW');

  await test('a DEACTIVATED employee is refused on a still-valid token', async () => {
    // verifySessionToken proves the token was minted by us and has not
    // expired. It proves nothing about now, and a session outlives its own
    // credential's deactivation by up to 12h. This is what
    // credentialStillActive exists for, and it needs sairnfreedom in
    // AUTH_TABLE_BY_APP -- without that entry it answers NO_ACTIVE_CHECK and
    // the request is allowed on the token alone.
    const w = world();
    const token = await provision(w, 'qm', 'finance.write');
    w.creds.forEach(function (r) { if (r.employee_id === 'qm') r.active = false; });
    const h = load('sd-data.js', LIC, w.fn);
    const r = await call(h, { action: 'read', resource: 'sf_ledger', app_id: 'sairnfreedom' }, token);
    assert.strictEqual(r.statusCode, 403,
      'a deactivated employee kept ledger access on an old token: ' + JSON.stringify(r.body));
    assert.strictEqual(r.body.error.code, 'CREDENTIAL_INACTIVE', JSON.stringify(r.body));
  });

  await test('sairnfreedom IS in AUTH_TABLE_BY_APP, so the check can run at all', async () => {
    const auth = fs.readFileSync(path.join(__dirname, '_lib', 'auth.js'), 'utf8');
    const seg = auth.slice(auth.indexOf('const AUTH_TABLE_BY_APP'));
    const map = seg.slice(0, seg.indexOf('};'));
    assert.match(map, /sairnfreedom:\s*'sairnfreedom_employee_auth'/,
      'without this entry credentialStillActive answers NO_ACTIVE_CHECK, which '
      + 'is NOT a refusal -- the request proceeds on the token alone and only a '
      + 'console warning records it. That fails OPEN.');
  });

  // ════════════════════════════════════════════════════════════════════════
  section('SCOPE -- the gate covers these three and says which app');

  await test('a token from ANOTHER SAIRN app is refused', async () => {
    const { signSessionToken } = require('./_lib/auth');
    const foreign = signSessionToken({ app: 'stonedesk', employee_id: 'gov',
                                       role: 'owner', license_hash: LIC });
    const w = world();
    await provision(w, 'gov');
    const h = load('sd-data.js', LIC, w.fn);
    const r = await call(h, { action: 'read', resource: 'sf_ledger', app_id: 'sairnfreedom' }, foreign);
    assert.strictEqual(r.statusCode, 403,
      'a StoneDesk session opened a veterans post ledger: ' + JSON.stringify(r.body));
  });

  await test('SD_GATE_APP names sairnfreedom for all three', async () => {
    // Without the entry the gate defaults to expectedApp 'stonedesk', a
    // correctly signed-in caller fails verification, and every call answers
    // FORBIDDEN "sign in first" no matter what they do. That is the exact
    // defect `memory` produced on 2026-09-03.
    const src = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
    const seg = src.slice(src.indexOf('const SD_GATE_APP'));
    const map = seg.slice(0, seg.indexOf('};'));
    for (const resource of GATED) {
      assert.ok(map.indexOf("'" + resource + "': 'sairnfreedom'") !== -1,
        resource + ' is gated but has no SD_GATE_APP entry, so it would demand '
        + 'a stonedesk session');
    }
  });

  await test('the other 32 sf_ resources stay UNGATED, deliberately', async () => {
    // The finding was about Tier A. Widening the gate to a duty roster or a
    // bottle count is a product decision nobody has made, and a gate that
    // grows by accident is how an app stops working for its users.
    const w = world();
    const h = load('sd-data.js', LIC, w.fn);
    const r = await call(h, { action: 'read', resource: 'sf_members', app_id: 'sairnfreedom' });
    assert.notStrictEqual(r.statusCode, 403,
      'sf_members answered 403 with no session, so the gate has widened past '
      + 'the three Tier A resources it was scoped to');
  });

  await test('the client actually sends the header the gate reads', async () => {
    // The fourth piece, asserted where the other three cannot see it. A gate
    // nothing feeds is a gate that refuses everybody.
    const html = fs.readFileSync(path.join(__dirname, '..', 'sairnfreedom.html'), 'utf8');
    const i = html.indexOf('function sfData(');
    assert.ok(i > 0, 'sfData is gone -- the transport was renamed or removed');
    const body = html.slice(i, i + 1200);
    assert.ok(body.indexOf("X-SD-Auth") !== -1,
      'sairnfreedom.html\'s only sd-data transport does not send X-SD-Auth, so '
      + 'every gated call from the real app answers 403');
    assert.ok(body.indexOf('Authorization') !== -1,
      'the licence header is gone -- two secrets, two headers');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
