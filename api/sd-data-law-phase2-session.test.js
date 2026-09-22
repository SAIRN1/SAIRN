// api/sd-data-law-phase2-session.test.js
// REQUIREMENT: law_clients, law_matters and law_deadlines -- the last three
//   SAIRNlaw resources that were authorised by the LICENCE KEY ALONE -- require
//   a signed-in SAIRNlaw employee session, and refuse without one before
//   touching the database.
//
// Run:  node api/sd-data-law-phase2-session.test.js
//
// ── WHY THESE THREE HAVE THEIR OWN SUITE ──────────────────────────────────
// api/sd-data-session-gate.test.js owns the gate TABLE and asserts that every
// pair in it is driven somewhere, naming the file that does the driving. It
// cannot drive these three itself: it mints StoneDesk sessions, and these need
// a SAIRNlaw one. That arm is why this file exists rather than being optional --
// adding the three to the table without a driver fails it, which is exactly
// what happened first and is the reason this file was written.
//
// ── WHAT WAS TRUE BEFORE, MEASURED RATHER THAN ASSUMED ────────────────────
// All SIX pairs (three resources by read and write) answered 200 with no token
// at all, against a control where law_invoices/read answered 401. The licence
// key is shipped to the browser and readable by anyone who can open the app, so
// "authorised" meant "opened the app". law_matters names the client and the
// matter, which made it the most exposed of the three.
//
// ── THE STATUS CODE IS 403, NOT 401, AND THAT IS A DELIBERATE INCONSISTENCY
//    WORTH KNOWING ABOUT ───────────────────────────────────────────────────
// This app now answers TWO different codes for "no session":
//   * the fifteen extended resources -> 401 NO_SESSION, from the inline gate
//     beside the LAW_RESOURCES table
//   * law_trusttx and these three    -> 403 FORBIDDEN, from the shared
//     SD_SESSION_GATED gate near the top of the handler
// The shared gate was chosen here because law_trusttx -- the most sensitive
// resource in the app and the one flipped in phase 2 before these -- uses it,
// and because it carries the per-resource expectedApp machinery that stops a
// valid session from another SAIRN app passing. The split is pre-existing, not
// introduced here; this change widens it from one resource to four. Whether to
// unify is a product decision and is recorded in the open-work index rather
// than settled in this file.

'use strict';
const assert = require('assert');
const { signSessionToken } = require('./_lib/auth');

const LIC_HASH = 'law-phase2-hash';

let passed = 0, total = 0;
async function test(name, fn) {
  total++;
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.log('  FAIL - ' + name + '\n        ' + e.message); }
}

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}
function mockReq(action, resource, payload, token) {
  const headers = { authorization: 'Bearer GOOD-KEY' };
  if (token) headers['x-sd-auth'] = token;
  return { method: 'POST', headers,
           body: { action, resource, app_id: 'sairnlaw', payload: payload || {} } };
}
function tokenFor(role, app) {
  return signSessionToken({
    app: app || 'sairnlaw', employee_id: 'emp-' + (role || 'owner'),
    role: role || 'owner', license_hash: LIC_HASH
  });
}
function loadHandler(fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: LIC_HASH,
        trial_ends_at: null, stripe_subscription_id: null })
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

// Records every URL the handler reaches for, so a refusal can be shown to have
// touched NOTHING -- a 403 issued after the read has already pulled the rows
// passes any status assertion and has still leaked the data.
function restStub(opts) {
  const o = opts || {};
  const calls = [];
  const impl = async function (url) {
    const u = String(url);
    calls.push(u);
    if (u.indexOf('sairnlaw_employee_auth') !== -1) {
      return { ok: true, status: 200,
               json: async () => (o.active === false ? [{ active: false }] : [{ active: true }]) };
    }
    return { ok: true, status: 200, json: async () => [{ data: { id: 'X1' } }] };
  };
  impl.calls = calls;
  return impl;
}

// The three, with a payload each branch will accept so a refusal cannot be
// mistaken for a validation error.
const THREE = [
  ['law_clients', { id: 'C1', name: 'A Client' }],
  ['law_matters', { id: 'M1', client_id: 'C1' }],
  ['law_deadlines', { id: 'D1', matter_id: 'M1' }],
];
const ROLES = ['owner', 'attorney', 'paralegal'];

(async () => {
  console.log('api/sd-data.js -- phase 2 final three: law_clients, law_matters, law_deadlines');

  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';
  process.env.SD_AUTH_SECRET = ['law', 'phase2', 'session', 'fixture'].join('-');

  console.log('\n1. a valid licence and NO session is refused -- and reads nothing');
  for (const [resource, payload] of THREE) {
    for (const action of ['read', 'write']) {
      await test(resource + '/' + action + ' -> 403 FORBIDDEN with no token', async () => {
        const stub = restStub();
        const handler = loadHandler(stub);
        const res = mockRes();
        await handler(mockReq(action, resource, payload), res);
        assert.strictEqual(res.statusCode, 403, 'status was ' + res.statusCode
          + ' body ' + JSON.stringify(res.body));
        assert.strictEqual(res.body.error.code, 'FORBIDDEN');
        assert.match(res.body.error.message, /sign in first/i);
        // The part a status-only assertion would miss.
        assert.deepStrictEqual(stub.calls, [],
          'a refused request still reached the database: ' + JSON.stringify(stub.calls));
      });
    }
  }

  console.log('\n2. the refusal is a SPLIT, not a lockout -- every real role still works');
  for (const [resource, payload] of THREE) {
    for (const role of ROLES) {
      await test('a signed-in ' + role + ' can read ' + resource, async () => {
        const handler = loadHandler(restStub());
        const res = mockRes();
        await handler(mockReq('read', resource, null, tokenFor(role)), res);
        assert.strictEqual(res.statusCode, 200, 'status was ' + res.statusCode
          + ' body ' + JSON.stringify(res.body));
        assert.strictEqual(res.body.ok, true);
      });
    }
  }
  // Without this arm the suite above could pass on a handler that refuses
  // everybody, which is the shape that makes a gate look correct while the app
  // is unusable. All three roles legitimately work clients, matters and
  // deadlines -- this is a session gate, not a role gate, and that is recorded
  // beside the table in api/sd-data.js.
  await test('a signed-in owner can WRITE law_matters too -- writes are gated, not blocked',
    async () => {
      const handler = loadHandler(restStub());
      const res = mockRes();
      await handler(mockReq('write', 'law_matters', { id: 'M1', client_id: 'C1' },
        tokenFor('owner')), res);
      assert.strictEqual(res.statusCode, 200, 'status was ' + res.statusCode
        + ' body ' + JSON.stringify(res.body));
    });

  console.log('\n3. a session from ANOTHER SAIRN app is refused -- the expectedApp entry');
  for (const [resource] of THREE) {
    await test('a valid SAIRNdental owner session cannot read ' + resource, async () => {
      const handler = loadHandler(restStub());
      const res = mockRes();
      await handler(mockReq('read', resource, null, tokenFor('owner', 'sairndental')), res);
      assert.strictEqual(res.statusCode, 403, 'status was ' + res.statusCode);
      assert.strictEqual(res.body.error.code, 'FORBIDDEN');
    });
  }

  console.log('\n4. the table and its expectedApp entries, asserted on the source');
  await test('all three are in SD_SESSION_GATED for BOTH actions', () => {
    const fs = require('fs');
    const src = fs.readFileSync(require.resolve('./sd-data.js'), 'utf8');
    const m = src.match(/const SD_SESSION_GATED = \{[\s\S]*?\n    \};/);
    assert.ok(m, 'the gate table is gone');
    for (const r of ['law_clients', 'law_matters', 'law_deadlines']) {
      assert.match(m[0], new RegExp("'" + r + "':\\s*\\['read', 'write'\\]"),
        r + ' is not gated for both actions');
    }
  });
  // SEPARATE ARM, DELIBERATELY. A resource in SD_SESSION_GATED with no
  // SD_GATE_APP entry defaults to expectedApp 'stonedesk' and refuses every
  // correctly signed-in attorney -- it fails CLOSED and confusingly, and the
  // table's own comment records that exact defect happening twice before.
  await test('...and each one names sairnlaw as its expected app', () => {
    const fs = require('fs');
    const src = fs.readFileSync(require.resolve('./sd-data.js'), 'utf8');
    const m = src.match(/const SD_GATE_APP = \{[\s\S]*?\n    \};/);
    assert.ok(m, 'the expected-app table is gone');
    for (const r of ['law_clients', 'law_matters', 'law_deadlines']) {
      assert.match(m[0], new RegExp("'" + r + "':\\s*'sairnlaw'"),
        r + ' has no expectedApp entry, so it would resolve to stonedesk');
    }
  });

  console.log('\n5. a DEACTIVATED credential is refused on a token that still verifies');
  for (const [resource] of THREE) {
    await test('a deactivated employee cannot read ' + resource, async () => {
      const handler = loadHandler(restStub({ active: false }));
      const res = mockRes();
      await handler(mockReq('read', resource, null, tokenFor('owner')), res);
      assert.notStrictEqual(res.statusCode, 200,
        'a deactivated credential read the data (status ' + res.statusCode + ')');
    });
  }

  console.log('\n' + passed + '/' + total + (passed === total ? ' PASS' : ' FAILED'));
  process.exit(passed === total ? 0 : 1);
})();
