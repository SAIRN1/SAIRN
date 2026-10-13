// ─────────────────────────────────────────────────────────────────────────────
// SAIRNbuild bld_draws — THE DRIVEN ROLE ARMS. Routed to cody by hank,
// docs/2026-10-13-hank-b6-routing.md item 4.
//
// api/sd-data.js gates bld_draws on BLD_DRAW_ROLES = ['owner', 'office'], READ
// AND WRITE, after a session gate that 401s a signed-out caller. Michael's
// instruction was "upper management/owner only, not supervisors, access
// assigned by ownership", and `pm` is the role that instruction bites.
//
// THE NEGATIVE CONTROL MATTERS MORE THAN THE POSITIVE ONE HERE, which is hank's
// line and is the whole design of this file: A GATE THAT REFUSES EVERYBODY
// PASSES EVERY SUPERVISOR-DENIED ARM. So the `owner` and `office` arms are not
// a nicety — they are what make the `pm` arms evidence. If this file ever shows
// pm-denied passing while owner/office are also denied, the suite has proved
// nothing about roles and has proved the resource is unreachable.
//
// THE POLICY IS READ OUT OF api/sd-data.js, NOT RETYPED. A literal
// ['owner','office'] here would agree with the handler only until one of them
// is edited, which is the defect class, not the test.
// ─────────────────────────────────────────────────────────────────────────────

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['bld', 'draws', 'role', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const API = path.join(__dirname, '..', 'api');
const { signSessionToken, ROLES_BY_APP } = require(path.join(API, '_lib', 'auth'));

const HASH = 'bld-co-hash';
const APP = 'sairnbuild';
const RESOURCE = 'bld_draws';
const ACTIONS = ['read', 'write'];

let pass = 0, fail = 0;
const FAILED = [];
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; FAILED.push(name); }
}
function section(t) { console.log('\n' + t); }

// ── THE POLICY, PARSED. Refuses rather than guessing. ───────────────────────
function drawRolesFromSource() {
  const src = fs.readFileSync(path.join(API, 'sd-data.js'), 'utf8');
  const m = src.match(/const BLD_DRAW_ROLES = \[([^\]]*)\]/);
  assert.ok(m, 'could not find BLD_DRAW_ROLES in api/sd-data.js. This parse is '
    + 'this file\'s only source for the policy; a silent miss would let every '
    + 'arm below be written against a list that no longer exists.');
  const roles = (m[1].match(/'([a-z.]+)'/g) || []).map((s) => s.replace(/'/g, ''));
  assert.ok(roles.length > 0, 'BLD_DRAW_ROLES parsed to an EMPTY list. An empty '
    + 'allowlist refuses everybody, which would pass every denied arm in this '
    + 'file -- so it is refused here instead.');
  return roles;
}

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}

function pgMock(calls) {
  return async function (url, opts) {
    const u = String(url);
    calls.push({ url: u, method: (opts && opts.method) || 'GET' });
    if (/_employee_auth\?/.test(u)) {
      return { ok: true, status: 200, json: async () => [
        { license_hash: HASH, employee_id: 'emp-1', role: 'owner', active: true }] };
    }
    if (opts && opts.method === 'POST') {
      return { ok: true, status: 200, json: async () => [JSON.parse(opts.body)] };
    }
    return { ok: true, status: 200, json: async () => [] };
  };
}

function loadHandler(fetchImpl) {
  const licPath = require.resolve(path.join(API, '_lib', 'license'));
  delete require.cache[licPath];
  require.cache[licPath] = {
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: HASH,
        trial_ends_at: null, stripe_subscription_id: null, app_id: APP })
    }
  };
  global.fetch = fetchImpl;
  const hPath = require.resolve(path.join(API, 'sd-data.js'));
  delete require.cache[hPath];
  return require(hPath);
}

// role === null means NO SESSION HEADER AT ALL.
async function call(action, role) {
  const calls = [];
  const h = loadHandler(pgMock(calls));
  const res = mockRes();
  const headers = { authorization: 'Bearer KEY-FOR-' + HASH };
  if (role !== null) {
    headers['x-sd-auth'] = signSessionToken(
      { app: APP, employee_id: 'emp-1', role, license_hash: HASH });
  }
  const body = { action, resource: RESOURCE };
  if (action === 'write') body.payload = { id: 'D1', amount: 1000 };
  await h({ method: 'POST', headers, body }, res);
  return { res, calls };
}

const DENY_MESSAGE = 'Draw requests are progress billing and are available to '
  + 'the owner and the office only. Ask the owner if you need access.';

function refusedByRoleGate(res) {
  return res.statusCode === 403
    && !!res.body && !!res.body.error
    && res.body.error.code === 'FORBIDDEN'
    && res.body.error.message === DENY_MESSAGE;
}

(async function main() {
  const ALLOWED = drawRolesFromSource();
  const ALL = ROLES_BY_APP[APP];
  const DENIED = ALL.filter((r) => ALLOWED.indexOf(r) === -1);

  section('0. THE POLICY, READ OUT OF THE HANDLER');
  console.log('  ROLES_BY_APP.sairnbuild  ' + ALL.join(' '));
  console.log('  BLD_DRAW_ROLES (parsed)  ' + ALLOWED.join(' '));
  console.log('  therefore DENIED         ' + (DENIED.join(' ') || '(none)'));
  console.log('  arms                     ' + (ALL.length * 2) + ' role×verb + 2 session + 1 unknown-role');
  assert.ok(DENIED.length > 0, 'every sairnbuild role is allowed, so there is no '
    + 'negative half and this file cannot be evidence of a role gate');
  assert.ok(ALLOWED.length > 0 && ALLOWED.length < ALL.length,
    'the allowlist is all-or-nothing; see this file\'s header on why that passes '
    + 'every denied arm');

  section('1. THE DENIED ROLE(S) -- 403, with the exact message, and NO row read');
  for (const role of DENIED) {
    for (const action of ACTIONS) {
      await test('1. ' + role + ' / ' + action + ' -> 403 FORBIDDEN', async () => {
        const { res, calls } = await call(action, role);
        assert.ok(refusedByRoleGate(res), role + '/' + action + ' was not refused '
          + 'by the role gate: ' + res.statusCode + ' ' + JSON.stringify(res.body));
        const touched = calls.filter((c) => c.url.indexOf(RESOURCE) !== -1);
        assert.strictEqual(touched.length, 0, 'refused 403 but the draw row was '
          + 'ALREADY FETCHED (' + touched.length + ' call(s)) -- a leak with a '
          + 'tidy status code');
      });
    }
  }

  section('2. THE ALLOWED ROLES -- THE ARMS THAT MAKE SECTION 1 EVIDENCE');
  for (const role of ALLOWED) {
    for (const action of ACTIONS) {
      await test('2. ' + role + ' / ' + action + ' reaches the handler', async () => {
        const { res } = await call(action, role);
        assert.strictEqual(refusedByRoleGate(res), false,
          role + '/' + action + ' was refused by the ROLE gate. If every role is '
          + 'refused then section 1 proves nothing about roles -- it proves the '
          + 'resource is unreachable.');
      });
    }
  }

  section('3. THE SESSION GATE UNDERNEATH, so a 403 is not read as the 401');
  for (const action of ACTIONS) {
    await test('3. no session / ' + action + ' -> 401 NO_SESSION', async () => {
      const { res, calls } = await call(action, null);
      assert.strictEqual(res.statusCode, 401, 'expected 401, got ' + res.statusCode
        + ' ' + JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'NO_SESSION',
        JSON.stringify(res.body.error));
      const touched = calls.filter((c) => c.url.indexOf(RESOURCE) !== -1);
      assert.strictEqual(touched.length, 0, 'a signed-out caller reached the row');
    });
  }

  // ── 4. THE FAIL-CLOSED CLAIM, AND WHY IT CANNOT BE DRIVEN END TO END ──────
  // MEASURED, NOT ASSUMED. The first version of arm 4 tried to drive an
  // unlisted role through the handler and FAILED with
  //   signSessionToken: invalid role "superintendent" for app "sairnbuild"
  // That is not a defect and it is not a broken arm — it is a STRONGER
  // guarantee one layer up: the token minter refuses to issue a session for a
  // role that is not in ROLES_BY_APP, so the gate's "an unknown role gets
  // nothing" branch is UNREACHABLE from outside. It becomes reachable only on
  // the day a fourth role is added to ROLES_BY_APP.sairnbuild without a line in
  // BLD_DRAW_ROLES, which is exactly the future this file is for.
  //
  // So the claim is split: 4a drives what can be driven, and 4b proves the rest
  // AT THE POLICY, labelled as not-driven rather than dressed up as an arm.
  section('4. FAILS CLOSED ON AN UNKNOWN ROLE -- split, because one half cannot be driven');
  await test('4a. signSessionToken REFUSES to mint a session for an unlisted role', async () => {
    let threw = null;
    try {
      signSessionToken({ app: APP, employee_id: 'emp-1', role: 'superintendent',
                         license_hash: HASH });
    } catch (e) { threw = e; }
    assert.ok(threw, 'a session was minted for a role that is not in '
      + 'ROLES_BY_APP.sairnbuild -- if this ever passes, the unknown-role path '
      + 'becomes drivable and arm 4b should be promoted to a real driven arm');
    assert.ok(/invalid role/i.test(String(threw.message)),
      'refused, but for some other reason: ' + threw.message);
    console.log('       refused at the minter: ' + threw.message);
  });
  await test('4b. NOT DRIVEN -- every role outside BLD_DRAW_ROLES is outside the '
             + 'allowlist the handler indexes', async () => {
    // Asserted against the PARSED list, so this survives an edit to the policy.
    const hypothetical = ['superintendent', 'foreman', 'estimator'];
    for (const r of hypothetical.concat(DENIED)) {
      assert.strictEqual(ALLOWED.indexOf(r), -1, r + ' is IN BLD_DRAW_ROLES, so '
        + 'this arm\'s premise is wrong and the policy changed');
    }
    console.log('       the handler\'s own test is `BLD_DRAW_ROLES.indexOf(role)'
      + ' === -1` -> 403, so an unlisted role inherits nothing. PROVED AT THE '
      + 'TABLE, not through a session, for the reason above.');
  });

  section('5. WHAT THIS FILE DOES NOT COVER, named rather than implied');
  console.log('  The Draw Requests panel in sairnbuild.html is STILL NOT role-gated');
  console.log('  client-side. A pm can open it and now sees a 403 rather than a');
  console.log('  hidden tab. Refusing is the server\'s job and hiding is the page\'s;');
  console.log('  the panel half is routed and is not tested here because it does');
  console.log('  not exist yet. OWNER: whoever takes the sairnbuild client change.');

  if (FAILED.length) {
    console.log('\n' + FAILED.length + ' ARM(S) FAILED:');
    FAILED.forEach((f) => console.log('  - ' + f));
  }
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
