// api/sd-data-employees-refusal.test.js
//
// Run:  node api/sd-data-employees-refusal.test.js
//
// THE EMPLOYEES READ REFUSED THREE DIFFERENT FACTS WITH ONE SENTENCE.
// `if (!session || EMPLOYEES_READ_DENIED_ROLES[session.role])` answered "Your
// role does not have access to employee records" for all of:
//
//   * no session, or an unverifiable one;
//   * a VALID session for another app -- the read binds to expectedApp
//     'stonedesk' on purpose, because its deny-list names only StoneDesk roles
//     and a SAIRNbiz role would otherwise slip through it;
//   * a StoneDesk session whose role really is denied.
//
// Only the third is about a role. Found 2026-09-10 by holding a valid SAIRNbiz
// owner session against production and being sent to the role model of an app
// that was never the problem. Not a security defect; the same class as "no
// patients" versus "you are not linked yet" elsewhere in api/sd-data.js, where
// a distinct code exists precisely so a client can say WHICH.
//
// WHAT THIS FILE GUARDS, and it is the part that could go wrong later: the
// diagnosis must never become the authorization. The fix verifies a SECOND
// time without expectedApp to name the app in the message, and that unbound
// session must stay message-only -- if it ever reached the allow path, a
// SAIRNbiz role would read a StoneDesk roster. Section 3 asserts exactly that.

const assert = require('assert');

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || 'test-secret-for-employees-refusal';
const { signSessionToken } = require('./_lib/auth');
const { hashLicense } = require('./_lib/license');

// THE HASH IS DERIVED, NOT BORROWED. api/_lib/license.js hashes the BEARER KEY;
// a token signed against a literal license_hash field verifies in isolation and
// is rejected by the handler with an indistinguishable NO_SESSION.
const KEY = 'EMPLOYEES-REFUSAL-TEST-KEY';
const LIC_HASH = hashLicense(KEY);

let pass = 0;
let fail = 0;

// ── await fn(), AND THE FIRST VERSION DID NOT (2026-09-10) ────────────────
// This was a SYNCHRONOUS function calling an async `fn()` inside try/catch. The
// promise was never awaited, so every rejection became an unhandled rejection
// AFTER the counter had already been incremented, and the file printed 7/7 with
// nothing asserted.
//
// It was caught by the negative control, not by reading: run against the
// PRE-FIX handler -- where a SAIRNbiz session must be told "Your role does not
// have access" and the WRONG_APP_SESSION assertion must fail -- it still
// reported 7/7. A suite that is green on the code it was written to reject is
// asserting nothing at all.
async function test(name, fn) {
  try {
    await fn();
    pass += 1;
    console.log('  ok   - ' + name);
  } catch (e) {
    fail += 1;
    console.log('  FAIL - ' + name + '\n         ' + (e && e.message));
  }
}
function section(t) { console.log('\n' + t); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (p) { res.body = p; return res; };
  return res;
}
function mockReq(token) {
  const headers = { authorization: 'Bearer ' + KEY };
  if (token) headers['x-sd-auth'] = token;
  return {
    method: 'POST',
    headers: headers,
    body: { action: 'read', resource: 'employees', app_id: 'stonedesk' }
  };
}
function tokenFor(app, role) {
  return signSessionToken({ app: app, employee_id: 'emp-' + role, role: role, license_hash: LIC_HASH });
}

// A licence WITH a tenant, so the branch reaches its refusals rather than
// short-circuiting on the honest-empty path.
function loadHandler(fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return {
          valid: true, active: true, license_hash: LIC_HASH,
          customer_email: 'tenant@example.test',
          trial_ends_at: null, stripe_subscription_id: null
        };
      },
      hashLicense: hashLicense
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}
const NO_FETCH = async function () {
  throw new Error('fetch must not be called -- the read was refused, so nothing may be read');
};

async function main() {
  console.log('api/sd-data.js -- the employees read says WHICH refusal it is');

  section('1. the three facts are three different answers');

  await test('a SAIRNbiz session is refused for the APP, not blamed on the role', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq(tokenFor('sairnbiz', 'owner')), res);
    assert.strictEqual(res.statusCode, 403, 'got ' + res.statusCode);
    assert.strictEqual(res.body.error.code, 'WRONG_APP_SESSION',
      'got ' + JSON.stringify(res.body));
    assert.match(res.body.error.message, /sairnbiz/,
      'the refusal does not name the app the caller actually holds');
    assert.doesNotMatch(res.body.error.message, /Your role does not have access/,
      'still blaming the role for a cause that is the app');
  });

  await test('NO session is refused as a session, not as a role', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq(null), res);
    assert.strictEqual(res.statusCode, 403);
    assert.strictEqual(res.body.error.code, 'FORBIDDEN');
    assert.match(res.body.error.message, /No valid session/);
  });

  await test('a GARBAGE token is refused as a session too', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq('not.atoken'), res);
    assert.strictEqual(res.statusCode, 403);
    assert.strictEqual(res.body.error.code, 'FORBIDDEN');
    assert.match(res.body.error.message, /No valid session/);
  });

  await test('a DENIED StoneDesk role still gets the role message -- it is the true one', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq(tokenFor('stonedesk', 'sales')), res);
    assert.strictEqual(res.statusCode, 403);
    assert.strictEqual(res.body.error.code, 'FORBIDDEN');
    assert.match(res.body.error.message, /Your role does not have access/);
  });

  section('2. the allow path is unchanged');

  await test('a StoneDesk owner still reads the roster', async () => {
    let asked = null;
    const handler = loadHandler(async function (url) {
      asked = String(url);
      return { ok: true, status: 200, json: async () => [{ data: { first_name: 'A' } }] };
    });
    const res = mockRes();
    await handler(mockReq(tokenFor('stonedesk', 'owner')), res);
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    assert.deepStrictEqual(res.body.data, [{ first_name: 'A' }]);
    assert.match(asked, /source_app=eq\.sairnbiz/, 'the tenant scoping changed');
  });

  // ── AND WHAT THEY SEE, WHICH NO ROLE CHECK CAN PROMISE ───────────────────
  // Added 2026-09-16 after a negative control deleted the manager payroll strip
  // -- `if (session.role !== 'owner') { delete copy.hourly_rate; }` -- and this
  // suite stayed GREEN. `hourly_rate` appeared in NO test anywhere on the
  // platform, so "Manager: full roster visibility, but never payroll" was a
  // promise made in a comment and asserted by nothing.
  //
  // It is a SECOND guarantee living in the same branch as the first. The role
  // deny-list decides WHO reads the roster; this decides WHAT they see, and the
  // arms above cannot reach it because they assert on a fixture row that
  // carries no payroll field at all.
  await test('a MANAGER reads the roster and never sees payroll', async () => {
    const handler = loadHandler(async function () {
      return { ok: true, status: 200, json: async () => [
        { data: { first_name: 'A', hourly_rate: 42, title: 'Fabricator' } }] };
    });
    const res = mockRes();
    await handler(mockReq(tokenFor('stonedesk', 'admin')), res);
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    assert.strictEqual(res.body.data.length, 1, 'the manager lost the roster');
    // ── GENUINELY ABSENT, NOT MERELY UNDEFINED (tightened 2026-09-16) ──────
    // `=== undefined` is satisfied by `copy.hourly_rate = undefined`, which
    // LEAVES THE KEY ON THE OBJECT. Over the wire that serialises away and the
    // two are indistinguishable to a client -- but this arm reads the object
    // BEFORE serialisation, so the weaker form would accept a strip that is not
    // one. hasOwnProperty is the question actually being asked.
    assert.ok(!Object.prototype.hasOwnProperty.call(res.body.data[0], 'hourly_rate'),
      'a manager was served hourly_rate (own property present: '
      + JSON.stringify(res.body.data[0]) + ')');
    assert.strictEqual(res.body.data[0].hourly_rate, undefined,
      'a manager was served hourly_rate');
    // And what the client ACTUALLY receives, which is the contract that
    // matters: the arms above read an in-process object, and res.json() is a
    // mock. A field re-appearing through serialisation would pass both.
    const onTheWire = JSON.parse(JSON.stringify(res.body));
    assert.ok(!Object.prototype.hasOwnProperty.call(onTheWire.data[0], 'hourly_rate'),
      'hourly_rate survives serialisation to the client');
    assert.strictEqual(res.body.data[0].title, 'Fabricator',
      'the strip took more than payroll -- full roster visibility is the other '
      + 'half of the same promise');
  });

  await test('...and an OWNER does -- so the arm above is a STRIP, not an '
    + 'empty response', async () => {
      const handler = loadHandler(async function () {
        return { ok: true, status: 200, json: async () => [
          { data: { first_name: 'A', hourly_rate: 42, title: 'Fabricator' } }] };
      });
      const res = mockRes();
      await handler(mockReq(tokenFor('stonedesk', 'owner')), res);
      assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
      assert.ok(Object.prototype.hasOwnProperty.call(res.body.data[0], 'hourly_rate'),
        'the owner lost the payroll KEY, so the manager arm proves nothing');
      assert.strictEqual(res.body.data[0].hourly_rate, 42,
        'the owner lost payroll too, so the manager arm proves nothing');
    });

  await test('...and the STORED row is not mutated -- the strip is a copy',
    async () => {
      // A delete on the upstream object would remove payroll from whatever the
      // client library cached, so the NEXT read -- by an owner -- would be
      // missing it too. The source says "shallow-copy so we're not mutating
      // whatever the upstream client library cached"; this is that sentence,
      // driven.
      const row = { data: { first_name: 'A', hourly_rate: 42 } };
      const handler = loadHandler(async function () {
        return { ok: true, status: 200, json: async () => [row] };
      });
      await handler(mockReq(tokenFor('stonedesk', 'admin')), mockRes());
      assert.ok(Object.prototype.hasOwnProperty.call(row.data, 'hourly_rate'),
        'the manager read DELETED payroll from the stored row, so an owner '
        + 'reading next would find it gone');
      assert.strictEqual(row.data.hourly_rate, 42,
        'the manager read mutated the stored row, so an owner reading next '
        + 'would find payroll gone');
      // AND THE READ ORDER THAT MAKES IT BITE. A mutation is only observable if
      // somebody reads AFTER it, so the owner read is driven against the SAME
      // row object the manager read already touched. Without this the arm above
      // asserts on an object nothing has consumed.
      const res2 = mockRes();
      await handler(mockReq(tokenFor('stonedesk', 'owner')), res2);
      assert.strictEqual(res2.body.data[0].hourly_rate, 42,
        'an OWNER reading after a MANAGER got no payroll -- the strip leaked '
        + 'into the shared row');
    });

  section('3. THE DIAGNOSIS IS NOT THE AUTHORIZATION');

  // The fix verifies a second time WITHOUT expectedApp so the message can name
  // the caller's app. That unbound session must never reach the allow path --
  // if it did, a SAIRNbiz role would read a StoneDesk-side roster, which is the
  // exact hole the expectedApp binding exists to close.
  await test('no non-StoneDesk app can reach the data, whatever its role', async () => {
    // ROLES ARE PER APP, taken from api/_lib/auth.js rather than invented.
    // signSessionToken REFUSES a role its app does not declare -- the first
    // version of this loop used one list for every app and died on
    // `invalid role "hr" for app "sairnbuild"`, which is the auth layer doing
    // its job and worth recording rather than quietly swapping.
    const ROSTERS = {
      sairnbiz: ['owner', 'hr', 'accounting', 'manager', 'staff'],
      sairnbuild: ['owner', 'pm', 'office'],
      sairnsenior: ['owner', 'scheduler', 'coordinator', 'billing', 'caregiver'],
      sairndental: ['owner', 'frontdesk', 'provider']
    };
    for (const app of Object.keys(ROSTERS)) {
      for (const role of ROSTERS[app]) {
        const handler = loadHandler(NO_FETCH);
        const res = mockRes();
        await handler(mockReq(tokenFor(app, role)), res);
        assert.strictEqual(res.statusCode, 403,
          app + '/' + role + ' reached the roster: ' + JSON.stringify(res.body));
        assert.ok(!res.body.ok, app + '/' + role + ' got data back');
      }
    }
  });

  await test('...and the refusal never leaks a row even when it names the app', async () => {
    const handler = loadHandler(NO_FETCH);
    const res = mockRes();
    await handler(mockReq(tokenFor('sairnbuild', 'owner')), res);
    assert.strictEqual(res.body.data, undefined, 'the refusal carried data');
  });

  console.log('\n' + pass + '/' + (pass + fail) + ' passed');
  process.exit(fail ? 1 : 0);
}

main();
