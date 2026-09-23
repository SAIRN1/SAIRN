// api/sd-data-exec-context-isolation.test.js
//
// REQUIREMENT: a valid, fully authenticated StoneDesk session for tenant A
//   cannot be presented against tenant B's licence, or a session for another
//   SAIRN app against StoneDesk's, to reach the Executive Suite context.
//
// CROSS-TENANT-ISOLATION: exec_context
//
// Run:  node api/sd-data-exec-context-isolation.test.js
//
// ── FIRST, A CORRECTION TO THE FRAMING THIS FILE WAS ASKED FOR ────────────
// The dispatch said exec_context "reads a different table shape than the
// shared [L] arm can see into". It reads NO TABLE AT ALL. api/_lib/exec-
// context.js IS the store -- there is no query, no license_hash filter, and
// nothing row-shaped to isolate. Said out loud rather than quietly
// reinterpreted, because it changes what the arms below can honestly claim.
//
// SO THE TENANT BOUNDARY HERE IS THE SIGNATURE, NOT A QUERY FILTER. The one
// thing standing between tenant B and this data is
// `verifySessionToken(tokenFromRequest(req), licHash, 'stonedesk')` --
// specifically its licence-hash check and its expected-app check. That is
// the whole of the isolation surface, and it is what these arms drive.
//
// ── WHY THE EXISTING SUITE DOES NOT COVER THIS ────────────────────────────
// api/sd-data-exec-context.test.js is a good file and it asserts the ROLE
// gate thoroughly. It cannot assert the TENANT gate, because it STUBS
// verifySessionToken out entirely:
//
//     verifySessionToken: function () { return role ? {...} : null; }
//
// A stub that returns a session for any token, any licence hash and any app
// is a stub that answers yes to the exact question this file is about. Every
// arm below therefore uses the REAL api/_lib/auth and signs real tokens.
//
// ── THIS FILE GRADES `NONE`, AND THAT IS A LIMIT OF THE MEASURER ──────────
// MEASURED, NOT PREDICTED, and the first version of this paragraph predicted
// WEAK and was wrong -- `python tools/cross_tenant_isolation_scope.py` reports
// exec_context NONE with this suite in place. Two separate limits stack:
//
//   1. GENUINE requires a fetch mock that reads `eq.` clauses out of a query
//      URL and honours them. This resource issues no query, so there is no
//      URL to filter and no mock that could honestly filter one. Writing a
//      query-parsing mock that is never called, purely to move the grade,
//      would be exactly the "string check wearing a behaviour check" the
//      tool's own header exists to refuse.
//   2. Even WEAK needs a tenant-shaped signal, and the one it looks for is
//      `license_hash: SOME_CONSTANT` spelled literally. This file binds the
//      tenant through a helper -- `token(HASH_A, ...)` -> `license_hash:
//      licHash` -- so two genuinely distinct tenants are invisible to the
//      regex. Reshaping the code to spell it the way the regex wants was
//      rejected: this platform's recorded response to "a test that did the
//      more general thing scored worse" is to widen the TOOL, not to bend
//      the test around it.
//
// So the file declares its coverage, grades NONE, and appears in the tool's
// DISCLOSED block as "DECLARES coverage but grades NONE [exec_context]".
// THAT LINE IS THE ONLY PLACE THE HEADLINE TABLE ADMITS THIS SUITE EXISTS --
// read the NONE in the coverage table as "the grader cannot see it", not as
// "nobody has written one". Understating is the safe direction and the
// disclosure names it; widening the grader is a change to the measurer and
// belongs in its own commit with its own control.
//
// THE OPEN-WORK ROW FOR THAT IS OWED AND IS NOT FILED IN THIS COMMIT, and
// saying so is better than an unwritten promise. Do not read this as "it was
// filed" -- check docs/SAIRN-OPEN-WORK-INDEX.md for a row naming
// tools/cross_tenant_isolation_scope.py and a signature-enforced boundary,
// and if there is none, it is still owed. Raised to Michael in the same
// report as this file.
//
// ── WHAT THIS DOES NOT DO ─────────────────────────────────────────────────
// It does not re-test the owner/admin role gate, the unknown-advisor-role
// 400, or the "these strings are gone from stonedesk.html" claims. Those are
// api/sd-data-exec-context.test.js's and duplicating them would put the same
// assertion in two places to drift apart.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['exec', 'context', 'isolation', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const { signSessionToken } = require('./_lib/auth');

const HASH_A = 'tenant-A-hash';
const HASH_B = 'tenant-B-hash';

// The resource this suite drives, in the shape
// tools/cross_tenant_isolation_scope.py cross-checks a declaration against.
// One row, because one resource is what this file is about -- the table is
// here so the declaration above is checkable rather than merely asserted.
const UNITS = [
  ['exec_context', 'read', 'no table -- the store is api/_lib/exec-context.js']
];

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

// fetch is made to THROW. This endpoint reads no table, so any network call
// at all is itself the finding: the day exec_context starts querying
// something, this stops being a signature-only boundary and needs a row
// filter and the arms that go with one. A thrown error inside the handler
// would surface as a rejected promise here rather than as a quiet 200.
const NO_NETWORK = async function (url) {
  throw new Error('exec_context reached the network (' + String(url)
    + ') -- it reads no table, so this is a new tenant surface with no filter '
    + 'asserted anywhere');
};

// Fresh per call, with the REAL api/_lib/auth. Only the licence layer is
// stubbed, and it is stubbed per tenant so the hash the handler derives from
// the bearer key is the thing the token is checked against.
function loadHandler(licHash) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: licHash,
                 trial_ends_at: null, stripe_subscription_id: null, app_id: 'stonedesk' };
      }
    }
  };
  global.fetch = NO_NETWORK;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

function req(token, advisorRole) {
  return {
    method: 'POST',
    headers: Object.assign({ authorization: 'Bearer KEY' },
                           token ? { 'x-sd-auth': token } : {}),
    body: { action: 'read', resource: 'exec_context', payload: { role: advisorRole } }
  };
}

function token(licHash, app, role, employeeId) {
  return signSessionToken({ app: app, employee_id: employeeId || 'emp-1',
                            role: role, license_hash: licHash });
}

async function call(licHash, tok, advisorRole) {
  const h = loadHandler(licHash);
  const res = mockRes();
  await h(req(tok, advisorRole || 'cfo'), res);
  return res;
}

// The string the whole endpoint exists to keep off a customer's screen. Used
// as the leak probe rather than "is there a body", because a refusal that
// echoes the thing it refused is the failure worth naming.
const SECRET = 'Chart of Accounts: Assets 1000s';

(async function () {
  console.log('CROSS-TENANT ISOLATION -- ' + UNITS[0][0] + ' (' + UNITS[0][2] + ')');

  // ── THE POSITIVE CONTROL FIRST, DELIBERATELY ────────────────────────────
  // Every refusal below is only evidence if a correctly signed request
  // SUCCEEDS. A handler that refused everybody would pass every negative arm
  // in this file and serve nobody.
  section('THE POSITIVE CONTROL -- a correctly signed owner of each tenant');

  await test('tenant A\'s own owner gets the context', async () => {
    const res = await call(HASH_A, token(HASH_A, 'stonedesk', 'owner'));
    assert.strictEqual(res.statusCode, 200,
      'the positive control was refused (' + res.statusCode + ' '
      + JSON.stringify(res.body) + '). Every refusal arm below is meaningless '
      + 'until this passes -- a handler that refuses everybody looks isolated.');
    assert.ok(String(res.body.data.system).indexOf(SECRET) !== -1,
      'the 200 did not actually carry the context');
  });

  await test('tenant B\'s own owner gets the context', async () => {
    const res = await call(HASH_B, token(HASH_B, 'stonedesk', 'owner'));
    assert.strictEqual(res.statusCode, 200,
      'tenant B is refused its own context: ' + res.statusCode + ' '
      + JSON.stringify(res.body));
  });

  section('THE TENANT BOUNDARY -- a real, unexpired, correctly signed token '
    + 'minted for the OTHER tenant');

  await test('[X] tenant B\'s owner token against tenant A\'s licence -> 403', async () => {
    // The token is genuine: signed by the same secret, same app, a role that
    // WOULD pass the role gate, not expired. The only thing wrong with it is
    // whose licence it was minted for -- which is the entire boundary.
    const res = await call(HASH_A, token(HASH_B, 'stonedesk', 'owner', 'emp-B1'));
    assert.strictEqual(res.statusCode, 403,
      'a session minted for ' + HASH_B + ' was accepted against ' + HASH_A
      + ': ' + res.statusCode + ' ' + JSON.stringify(res.body));
    assert.strictEqual(res.body.error.code, 'FORBIDDEN');
    assert.ok(JSON.stringify(res.body).indexOf(SECRET) === -1,
      'the refusal leaked the very thing it refused');
  });

  await test('[X-rev] tenant A\'s owner token against tenant B\'s licence -> 403',
    async () => {
      // Both directions, because a check comparing the token's hash against
      // itself rather than against the request's would pass the arm above.
      const res = await call(HASH_B, token(HASH_A, 'stonedesk', 'owner'));
      assert.strictEqual(res.statusCode, 403,
        'a session minted for ' + HASH_A + ' was accepted against ' + HASH_B
        + ': ' + res.statusCode + ' ' + JSON.stringify(res.body));
      assert.ok(JSON.stringify(res.body).indexOf(SECRET) === -1,
        'the refusal leaked the very thing it refused');
    });

  await test('[X-app] a SAIRNbiz owner token for the SAME tenant -> 403', async () => {
    // Guardian Check 28's collision. Same licence, same secret, a real owner
    // of a real app -- and not this one. Without the third argument to
    // verifySessionToken this reaches the chart of accounts.
    const res = await call(HASH_A, token(HASH_A, 'sairnbiz', 'owner'));
    assert.strictEqual(res.statusCode, 403,
      'a SAIRNbiz session reached StoneDesk\'s Executive Suite: ' + res.statusCode
      + ' ' + JSON.stringify(res.body));
    assert.ok(JSON.stringify(res.body).indexOf(SECRET) === -1,
      'the refusal leaked the very thing it refused');
  });

  await test('[X-sub] a stonedesk_sub token -> 403', async () => {
    // stonedesk_sub is a SEPARATE app id precisely so a subcontractor token
    // cannot pass a `'stonedesk'` check. A sub is not an employee of the shop
    // at all, which makes this the widest of the three collisions.
    //
    // AND THIS ARM IS DEFENCE-IN-DEPTH, NOT AN INDEPENDENT PROOF OF THE APP
    // CHECK. Measured, not assumed: with the expected-app check removed from
    // verifySessionToken, [X-app] above fails and THIS ARM STILL PASSES --
    // because ROLES_BY_APP.stonedesk_sub is ['sub'] and no sub token can
    // carry 'owner', so the role gate catches it anyway. The arm asserts the
    // composite outcome (a sub never sees this) and [X-app] is the one that
    // proves the app check itself. Said here rather than left to look like
    // two independent proofs of the same control.
    const res = await call(HASH_A, token(HASH_A, 'stonedesk_sub', 'sub'));
    assert.strictEqual(res.statusCode, 403,
      'a subcontractor session reached the Executive Suite: ' + res.statusCode
      + ' ' + JSON.stringify(res.body));
    assert.ok(JSON.stringify(res.body).indexOf(SECRET) === -1,
      'the refusal leaked the very thing it refused');
  });

  await test('[X-none] no token at all -> 403', async () => {
    const res = await call(HASH_A, null);
    assert.strictEqual(res.statusCode, 403);
    assert.ok(JSON.stringify(res.body).indexOf(SECRET) === -1);
  });

  section('WHAT THERE IS TO ISOLATE -- and the tripwire for the day that changes');

  await test('[N] the branch touches the network ZERO times', async () => {
    // Asserted by the fetch stand-in throwing rather than by counting: there
    // is no table, so there is no tenant-filtered query, and that is WHY the
    // arms above are the whole boundary. If this ever fails, the arms above
    // have stopped being sufficient.
    const res = await call(HASH_A, token(HASH_A, 'stonedesk', 'owner'));
    assert.strictEqual(res.statusCode, 200);
  });

  await test('[T] TRIPWIRE: both tenants receive byte-identical context, BY DESIGN',
    async () => {
      // exec_context carries SAIRN'S OWN chart of accounts, price book and
      // patent dates -- the vendor's data, not the customer's. Two tenants
      // getting the same bytes is therefore correct, and pinning it is what
      // makes the sentence above checkable instead of remembered.
      //
      // THIS IS A TRIPWIRE, NOT A LOCK. If this assertion ever fails, the
      // resource has started carrying something that differs per tenant --
      // at which point it IS tenant data, the signature is no longer the
      // whole boundary, and it needs a row filter plus the [L]/[W] arms that
      // go with one. Failing here is the notice to write them.
      const a = await call(HASH_A, token(HASH_A, 'stonedesk', 'owner'));
      const b = await call(HASH_B, token(HASH_B, 'stonedesk', 'owner', 'emp-B1'));
      assert.strictEqual(a.statusCode, 200);
      assert.strictEqual(b.statusCode, 200);
      assert.strictEqual(a.body.data.system, b.body.data.system,
        'the two tenants received DIFFERENT Executive Suite context. That is not '
        + 'a failure of this test -- it means exec_context now carries per-tenant '
        + 'data and needs a license_hash-filtered store with real [L] and [W] '
        + 'isolation arms. See this file\'s header.');
    });

  // ── THE NEGATIVE CONTROL ON THE HARNESS ITSELF ──────────────────────────
  section('THE NEGATIVE CONTROL -- the tokens this file signs are real');
  await test('the refusals above are not a broken signer', async () => {
    // Every negative arm would pass if signSessionToken produced garbage, or
    // if the shared secret differed between signing and verifying. The
    // positive controls at the top are that check; this one states the
    // property the grader looks for and the two hashes are genuinely distinct.
    assert.notStrictEqual(HASH_A, HASH_B, 'the two tenants are the same tenant');
    const tA = token(HASH_A, 'stonedesk', 'owner');
    const tB = token(HASH_B, 'stonedesk', 'owner');
    assert.notStrictEqual(tA, tB, 'the signer produced the same token for two tenants');
    const { verifySessionToken } = require('./_lib/auth');
    assert.ok(verifySessionToken(tA, HASH_A, 'stonedesk'),
      'the signer and the verifier disagree -- every refusal above is a false pass');
    assert.strictEqual(verifySessionToken(tA, HASH_B, 'stonedesk'), null);
    assert.strictEqual(verifySessionToken(tA, HASH_A, 'sairnbiz'), null);
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
