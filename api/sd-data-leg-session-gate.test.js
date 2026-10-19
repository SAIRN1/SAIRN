// api/sd-data-leg-session-gate.test.js
//
// REQUIREMENT: every LEG_RESOURCES table requires an employee SESSION for both
//   READ and WRITE, not the licence key alone -- the key is a bearer
//   credential, and these 36 tables include the death record and the
//   chain-of-custody log for human remains
//
// CROSS-TENANT-ISOLATION: none (this suite is about AUTHENTICATION, not
//   tenancy; the isolation arms for these resources live in
//   api/sd-data-cross-tenant-dispatchers.test.js)
//
// Run:  node api/sd-data-leg-session-gate.test.js
//
// ── THE DEFECT, REPRODUCED BEFORE IT WAS FIXED ────────────────────────────
// `if (LEG_RESOURCES[resource] && action === 'read')` and its write twin went
// straight from the licence hash the handler derived to the PostgREST query.
// Neither branch named verifySessionToken. Measured on the shipped file before
// the repair, with a valid licence key and NO X-SD-Auth header at all:
//
//     leg_deathrecords read   -> 200 ok:true          (rows returned)
//     leg_custodylog   write  -> 200 ok:true          (the row was upserted)
//     leg_cremations   write  -> 403 COUNTERSIGN_REQUIRED since 2026-10-17
//                               (b18 / practitioner answer F1). It was
//                               `200 ok:true` and the lock is why it is not.
//
// Anyone holding the licence key could read a funeral home's death records and
// APPEND TO ITS CHAIN-OF-CUSTODY LOG. That log is the document that says which
// human remains were in whose hands and when.
//
// ── THIS IS THE THIRD TIME THIS EXACT SHAPE HAS SHIPPED ───────────────────
// It was fixed as an emergency for the dnt_* tables on 2026-08-27, and
// SAIRNfreedom's SF_RESOURCES was found carrying it on 2026-09-21 (its own
// open-work row). The fix here is deliberately the SAME as LAW_RESOURCES'
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
  || ['leg', 'session', 'gate', 'fixture'].join('-');

const assert = require('assert');

// ACTIVE-CREDENTIAL PRE-GATE (2026-09-26): api/sd-data.js now re-checks the
// caller's employee row on EVERY request carrying a token. This suite's fetch
// stub answers generic rows with no `active` field -- a state a real deployment
// cannot be in -- so the wrapper answers that ONE read and passes everything
// else through untouched. See tests/lib/active_credential_stub.js.
const { wrapFetch: wrapActiveCred } = require('../tests/lib/active_credential_stub');

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
    headers: { authorization: 'Bearer LEG-TEST-KEY' },
    body: { action: action, resource: resource, payload: payload || {} }
  };
}

const { signSessionToken } = require('./_lib/auth');
function withSession(action, resource, payload, app, role) {
  return {
    method: 'POST',
    headers: {
      authorization: 'Bearer LEG-TEST-KEY',
      'x-sd-auth': signSessionToken({
        app: app || 'sairnlegacy', employee_id: 'emp-1',
        role: role || 'director', license_hash: 'leg-hash' })
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
        return { valid: true, active: true, license_hash: 'leg-hash',
                 trial_ends_at: null, stripe_subscription_id: null, app_id: 'sairnlegacy' };
      }
    }
  };
  global.fetch = wrapActiveCred(async function (url, init) {
    calls.push({ url: String(url), method: (init && init.method) || 'GET' });
    const m = (init && init.method) || 'GET';
    if (m === 'GET') return { ok: true, status: 200, json: async () => [{ data: { id: 'X-1' } }] };
    return { ok: true, status: 200, json: async () => [{ data: { id: 'X-1' } }] };
  });
  delete require.cache[require.resolve('./sd-data.js')];
  return { handler: require('./sd-data.js'), calls: calls };
}

// The three named in the reproduction, plus one ordinary resource so the arm
// is not reading as "only the frightening ones are gated".
const RESOURCES = ['leg_deathrecords', 'leg_custodylog', 'leg_cremations', 'leg_invoices'];

(async function () {
  console.log('LEG_RESOURCES require an employee session -- read AND write');

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
    // ── ONE RESOURCE MUST REFUSE A WRITE, AND THIS LOOP DID NOT KNOW IT ──
    // ROOT-CAUSED 2026-10-15. This suite was RED on
    // `leg_custodylog write with a session -> 200` and had been for at least
    // two batches -- it was carried as a known red through b13 with the honest
    // note "not mine", and nobody had asked WHY.
    //
    // THE ANSWER IS THAT THE ARM IS WRONG AND THE CODE IS RIGHT.
    // `leg_custodylog` is APPEND-ONLY: the handler answers 409 APPEND_ONLY in
    // its own words -- "a custody record that can be edited is not a chain of
    // custody" -- and it refuses EVERYONE, including the owner. A generic
    // "every write returns 200" loop over a resource list cannot be right
    // across a list that contains one resource whose whole point is to refuse.
    //
    // A FALSE RED IS NOT THE SAFE DIRECTION. This one sat in the suite long
    // enough to be inherited as a fact about the codebase, and a reader who
    // learns that this file is "always a bit red" reads the next REAL failure
    // the same way.
    //
    // THE REPLACEMENT IS STRICTLY STRONGER, not an exemption: for this one
    // resource the arm asserts the session gate was PASSED and then the
    // append-only rule refused -- 409 with the code, not 401/403. A 401 here
    // would mean the gate rejected a good session, which is what this suite
    // exists to catch, and the old arm could not tell those apart.
    // ── ASK THE MODULE, DO NOT RE-LIST IT (2026-10-15, b17) ──────────────
    // This was a hand-written `{ leg_custodylog: 'APPEND_ONLY' }` -- a SECOND
    // copy of the append-only list, in a suite whose job is to check the
    // first one. api/_lib/leg-roles.js owns LEG_APPEND_ONLY and exports
    // isAppendOnly() for exactly this, and api/_lib/sv-roles.js's header
    // names the cost of the re-listed copy in its own words: "SAIRNsenior
    // paid for the re-listed copy (cross-domain convention 7)."
    //
    // THE FAILURE MODE IT REMOVES IS SPECIFIC: the day a SECOND leg_ resource
    // becomes append-only, the handler answers 409 and this suite still
    // expects 200 -- so a correct lock would be reported as a regression, and
    // the fix would look like relaxing the suite.
    // ── AND A SECOND RESOURCE JOINED THAT CLASS ON 2026-10-17 (b18) ──────
    // THE PARAGRAPH ABOVE PREDICTED THIS IN WRITING: "the day a SECOND leg_
    // resource becomes append-only, the handler answers 409 and this suite
    // still expects 200 -- so a correct lock would be reported as a
    // regression, and the fix would look like relaxing the suite."
    //
    // It was not append-only, it was F1's COUNTERSIGNATURE lock, and the shape
    // was exactly as described: `leg_cremations write with a session -> 200`
    // went red the moment the lock landed. The fix is the same one -- ASK THE
    // MODULE -- and `requiresCountersignature()` is the accessor
    // api/_lib/leg-roles.js exports for it, so there is still no second copy
    // of the list in this file.
    //
    // 403 AND NOT 409, and the difference carries information: 409 means the
    // append-only rule refused an EDIT, 403 COUNTERSIGN_REQUIRED means the
    // record needs a second named person. A 401 for either would mean the
    // session gate rejected a good session, which is what this suite exists
    // to catch, and asserting the exact code is what keeps those apart.
    const legRolesForGate = require('./_lib/leg-roles');
    const expectCode = legRolesForGate.isAppendOnly(resource) ? 'APPEND_ONLY'
                     : legRolesForGate.requiresCountersignature(resource)
                       ? 'COUNTERSIGN_REQUIRED' : null;
    const expectStatus = (expectCode === 'COUNTERSIGN_REQUIRED') ? 403 : 409;
    if (expectCode) {
      await test(resource + ' write with a session -> ' + expectStatus + ' '
               + expectCode + ' (and the SESSION GATE was passed to get there)',
        async () => {
          const { handler } = load();
          const res = mockRes();
          await handler(withSession('write', resource, { id: 'X-1' }), res);
          assert.strictEqual(res.statusCode, expectStatus, JSON.stringify(res.body));
          assert.strictEqual(res.body && res.body.error && res.body.error.code,
                             expectCode, JSON.stringify(res.body));
        });
    } else {
      await test(resource + ' write with a session -> 200', async () => {
        const { handler } = load();
        const res = mockRes();
        await handler(withSession('write', resource, { id: 'X-1' }), res);
        assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
        assert.strictEqual(res.body.ok, true, JSON.stringify(res.body));
      });
    }
  }

  section('3. the session must be a SAIRNlegacy one -- Check 28, the cross-app collision');
  await test('a valid session for ANOTHER app is refused', async () => {
    // A real, correctly signed token for a different app. Without the third
    // argument to verifySessionToken this passes, which is the collision the
    // LAW gate's own comment names.
    const { handler, calls } = load();
    const res = mockRes();
    await handler(withSession('read', 'leg_deathrecords', null, 'sairnvet', 'owner'), res);
    assert.strictEqual(res.statusCode, 401,
      'a sairnvet session read a funeral home\'s death records: ' + JSON.stringify(res.body));
    assert.strictEqual(calls.length, 0);
  });

  section('4. the gate covers the WHOLE map, not the four this suite names');
  await test('every LEG_RESOURCES member is behind the same gate', async () => {
    // Driven, not read: the gate is one branch before the dispatch, so proving
    // it for the map means proving the branch tests membership of the map
    // rather than a list somebody typed twice.
    const fs = require('fs');
    const path = require('path');
    const src = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8').replace(/\r\n/g, '\n');
    const gateAt = src.indexOf('if (LEG_RESOURCES[resource]) {');
    assert.ok(gateAt > 0, 'there is no single LEG_RESOURCES gate -- it has been spelled per branch');
    const readAt = src.indexOf("if (LEG_RESOURCES[resource] && action === 'read')");
    const writeAt = src.indexOf("if (LEG_RESOURCES[resource] && action === 'write')");
    assert.ok(readAt > gateAt && writeAt > gateAt,
      'the gate does not precede both branches, so one of them is reachable without it');
    const gate = src.slice(gateAt, readAt);
    assert.ok(/verifySessionToken\(tokenFromRequest\(req\), licHash, 'sairnlegacy'\)/.test(gate),
      'the gate does not verify against the handler-derived hash scoped to sairnlegacy');
  });

  await test('and the map really is 36 resources, including the two that matter most', () => {
    const fs = require('fs');
    const path = require('path');
    const src = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
    const a = src.indexOf('const LEG_RESOURCES = {');
    const body = src.slice(a, src.indexOf('};', a));
    const names = (body.match(/(leg_\w+):/g) || []).map((x) => x.slice(0, -1));
    assert.strictEqual(names.length, 36, 'the map is ' + names.length + ' resources, not 36');
    assert.ok(names.indexOf('leg_deathrecords') !== -1);
    assert.ok(names.indexOf('leg_custodylog') !== -1);
  });

  section('5. the CLIENT half, without which this gate is an outage');

  await test('sairnlegacy.html attaches the token on EVERY sdnData call', () => {
    // The gate and the client shipped together and neither works alone.
    // Measured when this landed: 56 of 58 call sites passed no `withSession`,
    // so a conditional attach meant no token on every leg_* read and write.
    // The transport must attach it whenever a session is held, full stop.
    const fs = require('fs');
    const path = require('path');
    const html = fs.readFileSync(path.join(__dirname, '..', 'sairnlegacy.html'), 'utf8')
      .replace(/\r\n/g, '\n');
    const at = html.indexOf('function sdnData(action,resource,payload,withSession){');
    assert.ok(at > 0, 'sdnData is gone');
    const body = html.slice(at, html.indexOf('return fetch(DATA_API', at));
    assert.ok(body.indexOf("if(legSession&&legSession.token)h['X-SD-Auth']=legSession.token;") !== -1,
      'the transport attaches the token conditionally again -- with 56 call sites '
      + 'passing no flag, that is an outage on every leg_ read and write');
    assert.ok(body.indexOf('if(withSession&&legSession') === -1,
      'the withSession condition is back on the DATA transport');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
