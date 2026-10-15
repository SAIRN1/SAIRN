// api/sd-data-law-trusttx-session.test.js
// Plain node:assert tests. Run: node api/sd-data-law-trusttx-session.test.js
//
// ATTORNEY IOLTA TRUST MONEY, AND UNTIL 2026-09-16 IT HAD NO SESSION GATE.
//
// `law_trusttx` read and write both dispatched on the licence hash ALONE. That
// is not a session that had gone stale -- the deactivated-token gap closed the
// same day, one screen up in the same file -- it is NO SESSION CHECK EXISTING.
// The licence key is shipped to the browser and readable by anyone who can open
// the app, so it was the whole authorisation on a client trust ledger that a bar
// association audits.
//
// THE ADJACENT FEATURE SHIPPED AROUND IT. `law_trust_reconcile` reads THE SAME
// TABLE and verifies a session AND a role, forty lines below. A reader
// comparing the two would conclude the gate exists; a reader of either alone
// would not think to ask. That is why this suite asserts BOTH branches
// explicitly rather than trusting the registry entry to stay there.
//
// THE OPEN ROLE QUESTION IS NOW CLOSED, AND IN THE OTHER DIRECTION. This
// header used to say the role question was deliberately not asserted here --
// that "inventing a role restriction would silently lock out a paralegal who
// legitimately records one" -- and arm 3 asserted all three roles could read.
// On 2026-10-12 the role gate landed at api/sd-data.js:15712 and answered it:
//
//     api/_lib/law-roles.js:87   law_trusttx: { owner: 'rw', attorney: 'rw',
//                                  paralegal: '', why: 'TRUST -- IOLTA client
//                                  money, hard-locked, no override may open it' }
//     api/_lib/law-roles.js:52   LAW_TRUST_LOCKED -- law_trusttx and
//                                  law_bankstatements, no override opens either
//
// So the paralegal arm was a STALE EXPECTATION, not a defect: it went red
// because the question it declined to answer got answered. Corrected 2026-10-15
// (hank b16) by asserting the DENY the table states, not by deleting the arm --
// a deleted arm would leave nothing asserting which way the policy went.
//
// AND THE ARM IS PAIRED, because "a paralegal is always refused" would satisfy
// it on its own and that is a broken app rather than a locked ledger. Arm 3b
// drives the SAME paralegal token at law_optx, which the same table grants
// 'r' on the line above, and requires a 200.

'use strict';
const assert = require('assert');
const { signSessionToken } = require('./_lib/auth');

const LIC_HASH = 'law-test-hash';

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
function mockReq(body, token) {
  const headers = { authorization: 'Bearer GOOD-KEY' };
  if (token) headers['x-sd-auth'] = token;
  return { method: 'POST', headers: headers, body: body };
}
function tokenFor(role, app, active) {
  return signSessionToken({
    app: app || 'sairnlaw', employee_id: 'emp-' + (role || 'owner'),
    role: role || 'owner', license_hash: LIC_HASH
  });
}
function loadHandler(fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: LIC_HASH,
                 trial_ends_at: null, stripe_subscription_id: null };
      }
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

// A REST stub that answers the active-credential lookup and the trust read.
// `active` drives what sairnlaw_employee_auth returns, which is how the
// deactivated case is driven without a database.
function restStub(opts) {
  const o = opts || {};
  return async function (url) {
    const u = String(url);
    if (u.indexOf('sairnlaw_employee_auth') !== -1) {
      return { ok: true, status: 200,
               json: async () => (o.active === false ? [{ active: false }] : [{ active: true }]) };
    }
    if (u.indexOf('law_trusttx') !== -1) {
      return { ok: true, status: 200, json: async () => [{ data: { id: 'T1', amount: 100 } }] };
    }
    return { ok: true, status: 200, json: async () => [] };
  };
}

const WRITE_PAYLOAD = {
  id: 'T1', matter_id: 'M1', client_id: 'C1', type: 'Deposit', amount: 100
};

(async () => {
  console.log('api/sd-data.js -- law_trusttx session gate (attorney trust money)');

  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';
  process.env.SD_AUTH_SECRET = ['law', 'trusttx', 'session', 'fixture'].join('-');

  // ── 1. NO SESSION IS REFUSED ON BOTH BRANCHES ─────────────────────────────
  // A valid licence and NO token is exactly the pre-fix caller.
  for (const action of ['read', 'write']) {
    await test('a valid licence with NO session is REFUSED on ' + action, async () => {
      const handler = loadHandler(async function () {
        throw new Error('the gate must refuse BEFORE any query reaches the trust table');
      });
      const res = mockRes();
      await handler(mockReq({ action, resource: 'law_trusttx', payload: WRITE_PAYLOAD }), res);
      assert.strictEqual(res.statusCode, 403, 'expected 403, got ' + res.statusCode);
      assert.strictEqual(res.body.error.code, 'FORBIDDEN');
      assert.ok(!res.body.ok, 'a refusal must not carry ok:true');
      assert.ok(!('data' in res.body),
        'a refusal must not carry a data array -- an empty trust ledger is a real answer and this is not it');
    });
  }

  // ── 2. A SESSION FOR ANOTHER APP IS NOT A SESSION FOR THIS ONE ────────────
  await test('a valid session for a DIFFERENT app is refused', async () => {
    const handler = loadHandler(async function () {
      throw new Error('must refuse before the query');
    });
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'law_trusttx' },
      tokenFor('owner', 'sairndental')), res);
    assert.strictEqual(res.statusCode, 403, 'expected 403, got ' + res.statusCode);
    assert.strictEqual(res.body.error.code, 'FORBIDDEN');
  });

  // ── 2b. THE LOG THAT ARM 2 EMITS MUST NOT CLAIM AN ADMISSION ─────────────
  // Arm 2 passes and always did; what it also did was print
  //   "active-credential re-check DID NOT RUN ... The request was allowed on
  //    the token alone."
  // on a request it then refused 403. cody's b15 full-tree triage read that
  // line as this suite's failure and routed it to hank as one; the real
  // failing arm was the stale paralegal expectation at 3a. A log that
  // misdescribes the outcome of the very request it is attached to is a
  // silent-failure shape -- it reports a state the code did not reach -- so it
  // is asserted here rather than left to the next reader.
  //
  // FAILING-FIRST, and the red was driven rather than asserted: this arm was
  // run against the PRE-CHANGE tree in a detached worktree at dd66872a and
  // this suite was 12/13 there, with this arm the one failure and the 'was
  // allowed' substring the reason. docs/hank-evidence/b16/red_law_trusttx.log.
  // It is not a snapshot of the new text either -- it forbids the CLAIM and
  // requires the REFUSAL to still have happened, so rewording the sentence
  // again cannot quietly satisfy it.
  await test('the NO_ACTIVE_CHECK log does not claim an admission for a request that is refused', async () => {
    const handler = loadHandler(async function () {
      throw new Error('must refuse before the query');
    });
    const res = mockRes();
    const lines = [];
    const realWarn = console.warn;
    console.warn = function () { lines.push(Array.prototype.join.call(arguments, ' ')); };
    try {
      await handler(mockReq({ action: 'read', resource: 'law_trusttx' },
        tokenFor('owner', 'sairndental')), res);
    } finally { console.warn = realWarn; }

    assert.strictEqual(res.statusCode, 403,
      'the premise of this arm is that the request IS refused; got ' + res.statusCode);
    const hit = lines.filter((l) => l.indexOf('DID NOT RUN') !== -1);
    assert.strictEqual(hit.length, 1,
      'expected exactly one NO_ACTIVE_CHECK log for this request, got ' + hit.length
      + ' -- ' + JSON.stringify(lines));
    assert.ok(/NO_ACTIVE_CHECK/.test(hit[0]),
      'the log must name the code it is reporting: ' + hit[0]);
    assert.ok(!/allowed/i.test(hit[0]),
      'the log claims the request was ALLOWED while the handler refused it 403: ' + hit[0]);
    assert.ok(/continues|NOT an admission/i.test(hit[0]),
      'the log must say what actually happened -- the request continues to the '
      + 'per-resource gate, which may refuse it: ' + hit[0]);
  });

  // ── 3. A REAL SAIRNLAW SESSION GETS THROUGH -- both directions ────────────
  // Without this the gate could refuse everybody and every arm above would
  // still pass, which is a broken app rather than a protected one.
  for (const role of ['owner', 'attorney']) {
    await test('a signed-in ' + role + ' can READ the trust ledger', async () => {
      const handler = loadHandler(restStub({}));
      const res = mockRes();
      await handler(mockReq({ action: 'read', resource: 'law_trusttx' }, tokenFor(role)), res);
      assert.strictEqual(res.statusCode, 200, 'expected 200, got ' + res.statusCode
        + ' ' + JSON.stringify(res.body));
      assert.strictEqual(res.body.ok, true);
    });
  }

  // ── 3a. A PARALEGAL IS REFUSED, and that is the POLICY, not the gate ──────
  // api/_lib/law-roles.js:87 gives paralegal '' on law_trusttx and :52
  // hard-locks it. The refusal is 403 and NOT 404 on purpose -- the handler's
  // own note at api/sd-data.js:15707 says a paralegal refused law_trusttx
  // learns the resource exists, because the app's navigation shows them the
  // tab and pretending it is absent is a lie they can disprove by clicking.
  await test('a signed-in paralegal is REFUSED the trust ledger (law-roles.js:87, hard-locked)', async () => {
    const handler = loadHandler(restStub({}));
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'law_trusttx' }, tokenFor('paralegal')), res);
    assert.strictEqual(res.statusCode, 403, 'expected 403, got ' + res.statusCode
      + ' ' + JSON.stringify(res.body));
    assert.strictEqual(res.body.error.code, 'FORBIDDEN');
    assert.ok(!('data' in res.body),
      'a refusal must not carry a data array -- an empty trust ledger is a real answer and this is not it');
  });

  // ── 3b. THE CONTROL FOR 3a. Without it, "paralegal always refused" passes ─
  // Same token, same handler, a resource the SAME table grants paralegal 'r'
  // on (api/_lib/law-roles.js:83, law_optx -- operating-account transactions,
  // "deliberately not trust transactions"). If this goes red the refusal in 3a
  // is the role gate having swallowed the role, not the trust lock.
  await test('CONTROL -- the same paralegal token CAN read law_optx (law-roles.js:83)', async () => {
    const handler = loadHandler(restStub({}));
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'law_optx' }, tokenFor('paralegal')), res);
    assert.strictEqual(res.statusCode, 200, 'expected 200, got ' + res.statusCode
      + ' ' + JSON.stringify(res.body));
    assert.strictEqual(res.body.ok, true);
  });

  // ── 3c. AND THE TABLE ITSELF SAYS SO, read rather than inferred ───────────
  // The behavioural arms above go through the handler; this one asks the
  // module that decides. Both must agree -- a policy table that said one thing
  // while the endpoint did another is the shape of defect this platform keeps
  // paying for, and only one of the two is visible in a status code.
  await test('api/_lib/law-roles.js and the endpoint agree on paralegal/law_trusttx', async () => {
    const lawRoles = require('./_lib/law-roles');
    assert.strictEqual(lawRoles.decide('law_trusttx', 'paralegal', 'read'), lawRoles.DENY,
      'law-roles.js must DENY paralegal read on law_trusttx');
    assert.notStrictEqual(lawRoles.decide('law_optx', 'paralegal', 'read'), lawRoles.DENY,
      'law-roles.js must NOT deny paralegal read on law_optx, or 3b proves nothing');
  });

  // ── 4. A DEACTIVATED CREDENTIAL IS REFUSED ────────────────────────────────
  // The token is validly signed and unexpired; the employee row says active
  // false. This is the layer CC added on 2026-09-16, exercised here on the
  // resource that had no gate at all to layer it onto.
  await test('a DEACTIVATED credential with a valid token is refused', async () => {
    const handler = loadHandler(restStub({ active: false }));
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'law_trusttx' }, tokenFor('owner')), res);
    assert.strictEqual(res.statusCode, 403, 'expected 403, got ' + res.statusCode);
    assert.strictEqual(res.body.error.code, 'CREDENTIAL_INACTIVE');
  });

  // ── 5. THE REGISTRY ENTRY IS REAL, not a comment ──────────────────────────
  // Asserted against the source because the registry is what makes the gate
  // run at all, and a resource silently leaving it is the whole failure mode.
  await test('law_trusttx is in SD_SESSION_GATED for BOTH actions', async () => {
    const fs = require('fs');
    const path = require('path');
    const src = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
    const block = src.slice(src.indexOf('const SD_SESSION_GATED = {'),
      src.indexOf('};', src.indexOf('const SD_SESSION_GATED = {')));
    assert.match(block, /'law_trusttx':\s*\['read',\s*'write'\]/,
      'law_trusttx must be gated for read AND write -- one without the other '
      + 'leaves the ledger readable or writable on a licence key alone');
  });
  await test('...and its expected app is sairnlaw, not stonedesk', async () => {
    const fs = require('fs');
    const path = require('path');
    const src = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
    assert.match(src, /SD_GATE_APP\s*=\s*\{\s*'law_trusttx':\s*'sairnlaw'/,
      'verifying a SAIRNlaw session against expectedApp stonedesk refuses '
      + 'every correctly signed-in attorney');
  });

  // ── 6. THE ADJACENT READER STILL GATES, so the fix did not move the hole ──
  await test('law_trust_reconcile still verifies a session and a role', async () => {
    const handler = loadHandler(async function () {
      throw new Error('must refuse before the query');
    });
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'law_trust_reconcile' }), res);
    assert.strictEqual(res.statusCode, 401, 'expected 401, got ' + res.statusCode);
    assert.strictEqual(res.body.error.code, 'NO_SESSION');
  });

  console.log('\n' + passed + '/' + total + ' passed');
  process.exit(passed === total ? 0 : 1);
})();
