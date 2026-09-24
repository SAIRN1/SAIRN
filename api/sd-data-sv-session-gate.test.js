// api/sd-data-sv-session-gate.test.js
//
// REQUIREMENT: every SV_RESOURCES table requires an employee SESSION for both
//   READ and WRITE, not the licence key alone -- the key is a bearer
//   credential, and these 36 tables include sv_controlled (the DEA-relevant
//   controlled-substance register) and sv_patients.
//
// CROSS-TENANT-ISOLATION: none (this suite is about AUTHENTICATION, not
//   tenancy; the isolation arms for these resources live in
//   api/sd-data-cross-tenant-dispatchers.test.js, which is already 112/112
//   green and unrelated to this gap).
//
// Run:  node api/sd-data-sv-session-gate.test.js
//
// ── THE DEFECT, REPRODUCED BEFORE IT WAS FIXED (hover2, 2026-09-21) ───────
// `if (SV_RESOURCES[resource] && action === 'read')` and its write twin went
// straight from the licence hash the handler derived to the PostgREST query.
// Neither branch named verifySessionToken, and SD_SESSION_GATED (the shared
// table sf_accounts/sf_ledger/sf_vendor_prices/law_trusttx/slabs/profile/
// memory/locations use) carries zero sv_ entries. Measured on the shipped
// file before the repair, with a valid licence key and NO X-SD-Auth header
// at all:
//
//     sv_controlled read   -> 200 ok:true          (rows returned)
//     sv_patients    write  -> 200 ok:true          (the row was upserted)
//     sv_soapnotes   write  -> 200 ok:true
//
// Anyone holding the licence key -- shipped to the browser, readable by
// anyone who can open the app -- could read a clinic's DEA-relevant
// controlled-substance register and its patient records, and write to
// either, with no employee identity recorded at all.
//
// ── WHY THIS IS DIFFERENT FROM THE "NO AUTH SUBSYSTEM" OPEN-WORK ROWS ─────
// docs/SAIRN-OPEN-WORK-INDEX.md carries rows (2026-09-03, 2026-09-13) saying
// SAIRNvet has "no per-employee authentication at all" -- true when written,
// false since 29b1f1d5 (2026-09-13): api/sv-auth.js, ROLES_BY_APP.sairnvet,
// AUTH_TABLE_BY_APP.sairnvet and sql/sairnvet_employee_auth_schema.sql all
// exist. The auth SUBSYSTEM has existed for 8 days; this gate is the missing
// LAST STEP wiring the data dispatcher to actually require it -- the same
// shape LEG_RESOURCES, SF_RESOURCES and law_trusttx all shipped this same
// week, closed here rather than left as the odd one out.
//
// ── THIS IS THE FOURTH TIME THIS EXACT SHAPE HAS SHIPPED ──────────────────
// dnt_* (2026-08-27, emergency), SF_RESOURCES and law_trusttx (2026-09-16/21),
// LEG_RESOURCES (2026-09-21). The fix here is deliberately the SAME as those
// rather than a new spelling: one gate before the dispatch, scoped to the app
// by verifySessionToken's third argument, which is what stops a valid session
// from a different app passing -- the collision Check 28 exists for.
//
// ── WHAT THIS SUITE ASSERTS, AND WHY THE NETWORK ARM MATTERS ─────────────
// A refused request that still reaches the database is not refused. Every arm
// below counts fetch() calls, because a gate placed after the query would
// answer 401 and have already read the rows.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['sv', 'session', 'gate', 'fixture'].join('-');

const assert = require('assert');

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

// NO x-sd-auth header at all. This is the shape the defect allowed: a bearer
// licence key and nothing else.
function keyOnly(action, resource, payload) {
  return {
    method: 'POST',
    headers: { authorization: 'Bearer SV-TEST-KEY' },
    body: { action: action, resource: resource, payload: payload || {} }
  };
}

const { signSessionToken } = require('./_lib/auth');
function withSession(action, resource, payload, app, role) {
  return {
    method: 'POST',
    headers: {
      authorization: 'Bearer SV-TEST-KEY',
      'x-sd-auth': signSessionToken({
        app: app || 'sairnvet', employee_id: 'emp-1',
        role: role || 'owner', license_hash: 'sv-hash' })
    },
    body: { action: action, resource: resource, payload: payload || {} }
  };
}

function load() {
  const calls = [];
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: 'sv-hash',
                 trial_ends_at: null, stripe_subscription_id: null, app_id: 'sairnvet' };
      }
    }
  };
  global.fetch = async function (url, init) {
    calls.push({ url: String(url), method: (init && init.method) || 'GET' });
    const m = (init && init.method) || 'GET';
    if (m === 'GET') return { ok: true, status: 200, json: async () => [{ data: { id: 'X-1' } }] };
    return { ok: true, status: 200, json: async () => [{ data: { id: 'X-1' } }] };
  };
  delete require.cache[require.resolve('./sd-data.js')];
  return { handler: require('./sd-data.js'), calls: calls };
}

// sv_patients named in the reproduction, plus two ordinary resources so the
// arm is not reading as "only the frightening ones are gated". sv_controlled
// is deliberately NOT in this parameterised list -- its WRITE path already
// carries an independent witness-token requirement (api/sv-witness.js,
// 2026-09-13) that this suite is not exercising, so a generic write payload
// would test that control's shape, not this one's. sv_controlled gets its
// own dedicated arm below instead, scoped to what this suite actually adds:
// the READ path, which the witness lock does not touch at all.
const RESOURCES = ['sv_patients', 'sv_soapnotes', 'sv_billing'];

(async function () {
  console.log('SV_RESOURCES require an employee session -- read AND write');

  section('1. a licence key alone is REFUSED, and never reaches the database');
  for (const resource of RESOURCES) {
    for (const action of ['read', 'write']) {
      await test(resource + ' ' + action + ' -> 401 NO_SESSION, 0 queries', async () => {
        const { handler, calls } = load();
        const res = mockRes();
        await handler(keyOnly(action, resource, { id: 'X-1' }), res);
        assert.strictEqual(res.statusCode, 401,
          'answered ' + res.statusCode + ' ' + JSON.stringify(res.body));
        assert.strictEqual(res.body.error.code, 'NO_SESSION', JSON.stringify(res.body));
        assert.strictEqual(calls.length, 0,
          'a refused request reached the database anyway (' + calls.length + ' fetch calls) '
          + '-- a gate placed after the query answers 401 having already read the rows');
      });
    }
  }

  section('2. a real session still works -- the gate must not refuse everything');
  for (const resource of RESOURCES) {
    await test(resource + ' read with a session -> 200', async () => {
      const { handler } = load();
      const res = mockRes();
      await handler(withSession('read', resource), res);
      assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
      assert.strictEqual(res.body.ok, true, JSON.stringify(res.body));
    });
    await test(resource + ' write with a session -> 200', async () => {
      const { handler } = load();
      const res = mockRes();
      await handler(withSession('write', resource, { id: 'X-1' }), res);
      assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
      assert.strictEqual(res.body.ok, true, JSON.stringify(res.body));
    });
  }

  section('2b. sv_controlled -- the DEA register, READ path only (write has its own witness gate)');
  await test('sv_controlled read -> 401 NO_SESSION, 0 queries with a licence key alone', async () => {
    const { handler, calls } = load();
    const res = mockRes();
    await handler(keyOnly('read', 'sv_controlled'), res);
    assert.strictEqual(res.statusCode, 401,
      'answered ' + res.statusCode + ' ' + JSON.stringify(res.body));
    assert.strictEqual(res.body.error.code, 'NO_SESSION', JSON.stringify(res.body));
    assert.strictEqual(calls.length, 0);
  });
  await test('sv_controlled read with a session -> 200', async () => {
    const { handler } = load();
    const res = mockRes();
    await handler(withSession('read', 'sv_controlled'), res);
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    assert.strictEqual(res.body.ok, true, JSON.stringify(res.body));
  });
  await test('sv_controlled write with NO session is refused BEFORE the witness check runs, 0 queries', async () => {
    // Before this fix: a licence key alone reached the witness check and got
    // 403 WITNESS_REQUIRED -- refused, but for the WRONG reason, and by a
    // control that was never meant to stand in for authentication. After this
    // fix the session gate runs first, so a caller with no session at all
    // gets 401 NO_SESSION and the witness module is never even reached.
    const { handler, calls } = load();
    const res = mockRes();
    await handler(keyOnly('write', 'sv_controlled', { id: 'lidocaine' }), res);
    assert.strictEqual(res.statusCode, 401,
      'answered ' + res.statusCode + ' ' + JSON.stringify(res.body)
      + ' -- if this is 403 WITNESS_REQUIRED, the session gate is not running '
      + 'before the witness check');
    assert.strictEqual(res.body.error.code, 'NO_SESSION', JSON.stringify(res.body));
    assert.strictEqual(calls.length, 0);
  });

  section('3. the session must be a SAIRNvet one -- Check 28, the cross-app collision');
  await test('a valid session for ANOTHER app is refused', async () => {
    // A real, correctly signed token for a different app. Without the third
    // argument to verifySessionToken this passes, which is the collision the
    // LAW/LEG gates' own comments name.
    const { handler, calls } = load();
    const res = mockRes();
    await handler(withSession('read', 'sv_controlled', null, 'sairnlegacy', 'director'), res);
    assert.strictEqual(res.statusCode, 401,
      'a sairnlegacy session read a clinic\'s DEA-relevant register: ' + JSON.stringify(res.body));
    assert.strictEqual(calls.length, 0);
  });

  section('4. the gate covers the WHOLE map, not the four this suite names');
  await test('every SV_RESOURCES member is behind the same gate', async () => {
    // Driven, not read: the gate is one branch before the dispatch, so proving
    // it for the map means proving the branch tests membership of the map
    // rather than a list somebody typed twice.
    const fs = require('fs');
    const path = require('path');
    const src = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8').replace(/\r\n/g, '\n');
    const gateAt = src.indexOf('if (SV_RESOURCES[resource]) {');
    assert.ok(gateAt > 0, 'there is no single SV_RESOURCES gate -- it has been spelled per branch');
    const readAt = src.indexOf("if (SV_RESOURCES[resource] && action === 'read')");
    const writeAt = src.indexOf("if (SV_RESOURCES[resource] && action === 'write')");
    assert.ok(readAt > gateAt && writeAt > gateAt,
      'the gate does not precede both branches, so one of them is reachable without it');
    const gate = src.slice(gateAt, readAt);
    assert.ok(/verifySessionToken\(tokenFromRequest\(req\), licHash, 'sairnvet'\)/.test(gate),
      'the gate does not verify against the handler-derived hash scoped to sairnvet');
  });

  await test('and the map is at least as wide as when the gate landed, '
           + 'including the two that matter most', () => {
    // MEASURED, not assumed: earlier prose (including this role's own first
    // report of this finding) said 36, echoing CRITICALITY-TIERS.md's rollup
    // line for sairnvet; the counted map was 41 when the gate landed.
    //
    // ── THE EXACT COUNT WENT RED AND SAT RED (fixed 2026-09-24) ────────────
    // `=== 41` broke the day sv_scribe_consent became the 42nd resource
    // (68a9d4bc, 2026-09-23) and the suite sat red at origin/main for a day,
    // read as noise -- the third arm THIS WEEK found expired on its own
    // count (the sf_ pair count and the FAI anchor are the others). An exact
    // count on a map that legitimately grows is a fixture with an unannounced
    // expiry date. What this arm actually protects is the GATE covering the
    // whole map -- arm 4 above asserts that directly -- plus two properties a
    // count can hold without expiring: the map never SHRINKS below the size
    // the gate was verified at (a shrink is resources leaving the gate), and
    // the two DEA-relevant names are still in it.
    const fs = require('fs');
    const path = require('path');
    const src = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
    const a = src.indexOf('const SV_RESOURCES = {');
    const body = src.slice(a, src.indexOf('};', a));
    const names = (body.match(/(sv_\w+):/g) || []).map((x) => x.slice(0, -1));
    assert.ok(names.length >= 41,
      'the map SHRANK to ' + names.length + ' -- resources have left the gate');
    assert.ok(names.indexOf('sv_controlled') !== -1);
    assert.ok(names.indexOf('sv_patients') !== -1);
  });

  section('5. the CLIENT half, without which this gate is an outage');

  await test('sairnvet.html attaches the token on EVERY svData call', () => {
    // The gate and the client must ship together or neither works alone.
    // Measured before this landed: svData() sent ONLY Authorization: Bearer
    // <licence> -- no X-SD-Auth anywhere, on any of its 14 call sites, unlike
    // svAuthCall() (a DIFFERENT function, used only for the auth endpoint
    // itself: login/whoami/roster/set_active) which already had the header.
    // The data transport must attach it whenever a session is held, full stop.
    const fs = require('fs');
    const path = require('path');
    const html = fs.readFileSync(path.join(__dirname, '..', 'sairnvet.html'), 'utf8')
      .replace(/\r\n/g, '\n');
    const at = html.indexOf('function svData(action, resource, payload, wantEnvelope) {');
    assert.ok(at > 0, 'svData is gone');
    const body = html.slice(at, html.indexOf('}).then(function(r) {', at));
    // ASSERT THE ACTUAL ASSIGNMENT, not just co-occurring tokens in the
    // function body -- a comment mentioning "X-SD-Auth" in prose, with the
    // real attach line removed, would satisfy a bare substring check on both
    // words while attaching nothing. Caught live: the first version of this
    // arm passed against exactly that mutation.
    assert.ok(/headers\[.X-SD-Auth.\]\s*=\s*svTokNow/.test(body),
      'svData() does not actually ASSIGN X-SD-Auth from svTok() -- landing '
      + 'the server gate alone would 401 every read and write in this app');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
