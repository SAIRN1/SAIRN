// api/sd-data-scp-session-gate.test.js
//
// REQUIREMENT: the two Tier A SAIRNscape resources refuse a call that carries
//   no employee session, AND every correctly signed-in crew still gets through.
//
// CROSS-TENANT-ISOLATION: none (this file is about identity WITHIN a company,
//   not about the tenant boundary; `invoices` and `scp_quotes` already have
//   tenant arms in api/sd-data-cross-tenant-ownbranch.test.js)
//
// Run:  node api/sd-data-scp-session-gate.test.js
//
// ── WHY THIS EXISTS ──────────────────────────────────────────────────────
// All twelve SAIRNscape resources dispatched on the licence hash alone, with
// NO session check of any kind -- and the licence key is shipped to the browser
// and readable by anyone who can open sairnscape.html, so it was the whole
// authorisation. Two of the twelve are Tier A on integrity: `invoices` (money)
// and `scp_quotes` (the priced quote every invoice descends from).
//
// Identical shape to SAIRNfreedom's fifteen and SAIRNdesign's nine, both swept
// earlier in September 2026. SAIRNscape was not swept with either, and
// tests/app_session_isolation.js recorded that gap in prose from 2026-09-24
// rather than leaving it undocumented -- this file is that row being closed.
//
// ── THE HALF THAT BREAKS APPS, AND IT IS THE HALF THIS FILE IS MOSTLY ABOUT
// A gate is two lines. The failure this platform has recorded three times is
// not forgetting the gate, it is arming it before the CLIENT can send a token
// -- which answers 403 "sign in first" to every correctly signed-in employee
// and fails closed AND confusingly, the hardest failure to read.
//
// MEASURED BEFORE ARMING, and SAIRNscape is the easy case: scpData() attaches
// X-SD-Auth from SCP_SESSION_KEY on every call whenever a token exists
// (sairnscape.html:2107) -- there is no per-call `withSession` flag to forget,
// which is exactly what had to be repaired in sairndesign.html. So the client
// half needed no change. THE ARMS BELOW READ THE SHIPPED PAGE RATHER THAN
// TRUSTING THAT SENTENCE, because "no change was needed" is the claim most
// worth checking when no diff exists to review.
//
// ── THE SECOND PRECONDITION, WHICH IS ORDERING ───────────────────────────
// scpData attaching the header is necessary and not sufficient: a token that
// does not EXIST yet cannot be attached. Both login paths must write the
// session to sessionStorage BEFORE the first server read. They do --
// scpDoLogin and scpDoBootstrap each setItem then call scpApplyLoggedIn, which
// calls scpInit, which calls scpSyncFromServer -- and an arm below asserts
// that ordering on the source, because reversing it would make every read on a
// fresh login unauthenticated and now refused.
//
// ── AND THE THIRD LIST, WHICH IS WHERE THIS GOES WRONG QUIETLY ───────────
// A resource in SD_SESSION_GATED and NOT in SD_GATE_APP resolves expectedApp
// to 'stonedesk', so a genuine SAIRNscape token fails verification and the
// caller is refused with "sign in first" no matter what they do. The two lists
// DISAGREEING is the defect, so the arm below asserts they AGREE rather than
// asserting either one's contents -- the same shape
// api/sd-data-sf-session-gate.test.js and api/sd-data-sdn-session-gate.test.js
// use for SAIRNfreedom and SAIRNdesign.
//
// ── THE NAME TRAP, AND IT IS SPECIFIC TO THIS APP ────────────────────────
// SAIRNscape claimed the BARE names `invoices` and `schedule` before the scp_
// convention existed. The storage table is `scp_invoices`; the RESOURCE is
// `invoices`. A gate written against 'scp_invoices' would gate nothing at all
// and every arm asserting a refusal would still be satisfiable by some other
// branch -- so the positive arms below are what make this file decisive, not
// the refusals.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['scp', 'session', 'gate', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { signSessionToken } = require('./_lib/auth');

const HASH = 'scape-company-A-hash';
const APP = 'sairnscape';
const SD_DATA = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
const PAGE = fs.readFileSync(path.join(__dirname, '..', 'sairnscape.html'), 'utf8');

// The two this commit gates, written out rather than parsed, because the arm
// below cross-checks the SOURCE against this list in both directions -- a list
// derived from the source could not catch the source being wrong.
//
// THE STOPPING RULE IS "TIER A", NOT "THESE TWO NAMES". If a third SAIRNscape
// row is promoted, it belongs here and in both tables on the same day, which is
// what the sdn set's growth from five to nine on 2026-09-24 established.
const GATED = ['invoices', 'scp_quotes'];

// One of the ten that stay licence-only, driven below. NOT an endorsement -- a
// disclosure, so the day somebody widens the scope it is visible here.
const UNGATED_WITNESS = 'scp_vendors';

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
async function atest(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  res.setHeader = function () { return res; };
  return res;
}
function loadHandler() {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: HASH,
                 trial_ends_at: null, stripe_subscription_id: null, app_id: APP };
      }
    }
  };
  global.fetch = async function (url, opts) {
    const u = String(url);
    // A CREDENTIAL LOOKUP IS NOT THE QUERY UNDER TEST. The gate re-checks that
    // the signed-in employee is still ACTIVE before serving anything, and a
    // stub that answered [] here would make every positive arm below fail 403
    // CREDENTIAL_INACTIVE -- a false negative that reads exactly like the gate
    // refusing a correctly signed-in caller, which is the thing these arms are
    // supposed to be able to detect.
    if (/_employee_auth\?/.test(u)) {
      return { ok: true, status: 200, json: async () =>
        [{ license_hash: HASH, employee_id: 'emp-1', role: 'owner', active: true }] };
    }
    if (opts && opts.method === 'POST') {
      return { ok: true, status: 200, json: async () => [JSON.parse(opts.body)] };
    }
    return { ok: true, status: 200, json: async () => [{ data: { ok: true } }] };
  };
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}
async function callWith(headers, body) {
  const h = loadHandler();
  const res = mockRes();
  await h({ method: 'POST', headers: headers, body: body }, res);
  return res;
}
const BEARER = { authorization: 'Bearer KEY' };
function withToken(app, role) {
  return Object.assign({}, BEARER, {
    'x-sd-auth': signSessionToken({ app: app, employee_id: 'emp-1',
                                    role: role || 'owner', license_hash: HASH })
  });
}

(async function () {
  console.log('SAIRNscape -- the two Tier A resources demand an employee session\n');

  section('THE TWO LISTS MUST AGREE -- the way this goes wrong quietly');

  test('both gated SAIRNscape resources have an SD_GATE_APP entry', function () {
    // Anchored on the VALUE 'sairnscape' for the second list and on membership
    // in GATED for the first, because these two resource names share no prefix
    // -- `invoices` is bare. A prefix parser of the kind the sdn and sf suites
    // use would find `scp_quotes` and silently miss `invoices`, which is the
    // half that carries the money.
    const gateTable = SD_DATA.match(/const SD_SESSION_GATED = \{[\s\S]*?\n    \};/);
    const appTable = SD_DATA.match(/const SD_GATE_APP = \{[\s\S]*?\n    \};/);
    assert.ok(gateTable, 'SD_SESSION_GATED is gone');
    assert.ok(appTable, 'SD_GATE_APP is gone');
    const gatedIn = GATED.filter((r) =>
      new RegExp("'" + r + "':\\s*\\['read', 'write'\\]").test(gateTable[0])).sort();
    const appIn = (appTable[0].match(/'([a-z_]+)':\s*'sairnscape'/g) || [])
      .map((s) => s.match(/'([a-z_]+)'/)[1]).sort();
    assert.deepStrictEqual(gatedIn, GATED.slice().sort(),
      'SD_SESSION_GATED does not gate both Tier A SAIRNscape resources for read '
      + 'AND write -- found: ' + gatedIn.join(', '));
    assert.deepStrictEqual(appIn, GATED.slice().sort(),
      'SD_SESSION_GATED and SD_GATE_APP disagree. A resource in the first and '
      + 'not the second resolves expectedApp to "stonedesk" and refuses every '
      + 'correctly signed-in crew lead -- it fails CLOSED and confusingly.');
  });

  test('the RESOURCE name is the bare one the dispatch actually uses', function () {
    // The trap this app carries and no other does. If somebody "tidies" the
    // gate entry to 'scp_invoices' it gates a resource that does not exist,
    // every refusal arm below still passes for the wrong reason, and the money
    // row goes back to licence-only in silence.
    assert.ok(/if \(resource === 'invoices' && action === 'read'\)/.test(SD_DATA),
      "the `invoices` read branch is gone or renamed -- if the resource really "
      + "is called something else now, this whole file's anchor moved");
    assert.ok(!/'scp_invoices':\s*\['read', 'write'\]/.test(SD_DATA),
      "SD_SESSION_GATED carries 'scp_invoices', which is the STORAGE TABLE and "
      + 'not a resource the dispatch ever sees. That entry gates nothing.');
  });

  section('THE CLIENT CAN ACTUALLY SEND A TOKEN -- the precondition, read out '
    + 'of the shipped page');

  test('scpData attaches X-SD-Auth with no per-call flag to forget', function () {
    const at = PAGE.indexOf('var headers = { \'Content-Type\': \'application/json\', Authorization: \'Bearer \' + licKey };');
    assert.ok(at > -1, "scpData's header block not found -- anchor moved");
    const fn = PAGE.slice(at, at + 400);
    assert.ok(/sessionStorage\.getItem\(SCP_SESSION_KEY\); if \(tok\) headers\['X-SD-Auth'\] = tok;/.test(fn),
      'scpData no longer sets X-SD-Auth from the stored session. The gate above '
      + 'then refuses every correctly signed-in employee, which is the failure '
      + 'arming a gate before the client can send a token produces.');
    assert.ok(!/withSession/.test(fn),
      'a withSession-style flag has appeared on scpData\'s header. SAIRNdesign '
      + 'had exactly that and 18 of 19 call sites never passed it.');
  });

  test('every scpData call for these two goes through that one helper', function () {
    // The header being unconditional only covers the call sites that USE the
    // helper. A bespoke fetch for either resource would bypass it entirely.
    for (const r of GATED) {
      const direct = PAGE.split('\n').filter((l) =>
        l.indexOf("'" + r + "'") > -1 && /fetch\s*\(/.test(l) && l.indexOf('scpData') === -1);
      assert.deepStrictEqual(direct, [],
        r + ' has a call site that calls fetch() directly instead of scpData(), '
        + 'so it carries no session header and is now refused: ' + direct.join(' | '));
    }
  });

  test('a session exists BEFORE the first server read, on BOTH login paths', function () {
    // scpDoLogin and scpDoBootstrap each write the token to sessionStorage and
    // then call scpApplyLoggedIn -> scpInit -> scpSyncFromServer. Reversed,
    // every read on a fresh login would carry no token and now be refused.
    for (const fname of ['scpDoLogin', 'scpDoBootstrap']) {
      const start = PAGE.indexOf('function ' + fname + '(){');
      assert.ok(start > -1, fname + ' not found -- anchor moved');
      const body = PAGE.slice(start, PAGE.indexOf('window.' + fname + '=' + fname + ';', start));
      const setsToken = body.indexOf('sessionStorage.setItem(SCP_SESSION_KEY');
      const enters = body.indexOf('scpApplyLoggedIn(');
      assert.ok(setsToken > -1, fname + ' no longer stores a session token');
      assert.ok(enters > -1, fname + ' no longer calls scpApplyLoggedIn');
      assert.ok(setsToken < enters,
        fname + ' enters the app BEFORE storing the session token, so the first '
        + 'read after a sign-in carries no header and is now refused');
    }
    // And the third link: scpApplyLoggedIn is the only route into scpInit, and
    // scpInit is what triggers the first server read.
    const apply = PAGE.slice(PAGE.indexOf('function scpApplyLoggedIn(role){'),
                             PAGE.indexOf('function scpDoLogin(){'));
    assert.ok(/scpInit\(\);/.test(apply),
      'scpApplyLoggedIn no longer calls scpInit -- the ordering asserted above '
      + 'no longer says anything about when the first read happens');
    const init = PAGE.slice(PAGE.indexOf('function scpInit(){'),
                            PAGE.indexOf('function scpInit(){') + 900);
    assert.ok(/scpSyncFromServer\(\);/.test(init),
      'scpInit no longer calls scpSyncFromServer -- re-derive where the first '
      + 'server read now happens and re-anchor this arm on that');
  });

  section('THE GATE ITSELF -- driven, both directions');

  for (const resource of GATED) {
    await atest(resource + ' read with NO session is refused', async function () {
      const res = await callWith(BEARER, { action: 'read', resource: resource });
      assert.strictEqual(res.statusCode, 403,
        'answered ' + res.statusCode + ' ' + JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'FORBIDDEN');
    });

    await atest(resource + ' write with NO session is refused', async function () {
      const res = await callWith(BEARER,
        { action: 'write', resource: resource, payload: { id: 'X-1', customer_id: 'C-1' } });
      assert.strictEqual(res.statusCode, 403,
        'answered ' + res.statusCode + ' ' + JSON.stringify(res.body));
    });

    await atest(resource + ' read WITH a valid SAIRNscape session is allowed',
      async function () {
        // THE PAIRED POSITIVE, and the half that matters most: a gate that
        // refused everybody would pass every arm above and lock a landscaping
        // company out of its own quotes and invoices.
        const res = await callWith(withToken(APP), { action: 'read', resource: resource });
        assert.strictEqual(res.statusCode, 200,
          'a correctly signed-in crew lead was refused: ' + res.statusCode + ' '
          + JSON.stringify(res.body) + ' -- if this is FORBIDDEN, check that '
          + resource + ' is in SD_GATE_APP as well as SD_SESSION_GATED');
      });

    await atest(resource + ' write WITH a valid SAIRNscape session is allowed',
      async function () {
        // The write half of the same point. A gate is a SPLIT, not a lockout,
        // and a read-only positive would not have noticed a write that refused
        // everybody.
        const res = await callWith(withToken(APP),
          { action: 'write', resource: resource, payload: { id: 'X-1', customer_id: 'C-1' } });
        assert.strictEqual(res.statusCode, 200,
          'a correctly signed-in write was refused: ' + res.statusCode + ' '
          + JSON.stringify(res.body));
      });

    await atest(resource + ' refuses a token minted for ANOTHER SAIRN app',
      async function () {
        // Guardian Check 28's collision, and the reason SD_GATE_APP exists.
        // sairndesign chosen deliberately: it is the app whose registry scan
        // claimed `invoices` before the handler settled the question.
        const res = await callWith(withToken('sairndesign'),
          { action: 'read', resource: resource });
        assert.strictEqual(res.statusCode, 403,
          'a sairndesign session reached ' + resource);
      });

    await atest(resource + ' refuses a DEACTIVATED credential on a token that '
      + 'still verifies', async function () {
        // verifySessionToken proves the token was minted by us and has not
        // expired. It proves nothing about NOW, and deactivation is the one
        // control an owner has for somebody who has just left.
        const h = (function () {
          const handler = loadHandler();
          const prev = global.fetch;
          global.fetch = async function (url, opts) {
            if (/_employee_auth\?/.test(String(url))) {
              return { ok: true, status: 200, json: async () =>
                [{ license_hash: HASH, employee_id: 'emp-1', role: 'owner', active: false }] };
            }
            return prev(url, opts);
          };
          return handler;
        })();
        const res = mockRes();
        await h({ method: 'POST', headers: withToken(APP),
                  body: { action: 'read', resource: resource } }, res);
        assert.strictEqual(res.statusCode, 403,
          'a deactivated credential still reached ' + resource + ': '
          + res.statusCode + ' ' + JSON.stringify(res.body));
        assert.strictEqual(res.body.error.code, 'CREDENTIAL_INACTIVE');
      });
  }

  section('AND THE TEN THAT ARE NOT GATED ARE STILL NOT GATED');

  await atest(UNGATED_WITNESS + ' still answers without a session', async function () {
    // NOT AN ENDORSEMENT -- a disclosure. Stopping at Tier A is the scope
    // SAIRNfreedom's entry set and SAIRNdesign followed, and widening it to the
    // other ten is a product decision about who on a crew may see a vendor list
    // that nobody has made. This arm exists so the day somebody makes it, the
    // change is visible here rather than silent.
    const res = await callWith(BEARER, { action: 'read', resource: UNGATED_WITNESS });
    assert.strictEqual(res.statusCode, 200,
      UNGATED_WITNESS + ' is now gated too. That may well be right -- but it is '
      + 'a scope change and this arm is where it gets noticed.');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
