// api/sd-data-sdn-session-gate.test.js
//
// REQUIREMENT: the five Tier A SAIRNdesign resources refuse a call that
//   carries no employee session, AND every correctly signed-in designer still
//   gets through.
//
// CROSS-TENANT-ISOLATION: none (this file is about identity WITHIN a studio,
//   not about the tenant boundary; sdn_pos's tenant arms live in
//   api/sd-data-bespoke-branch-isolation.test.js)
//
// Run:  node api/sd-data-sdn-session-gate.test.js
//
// ── WHY THIS EXISTS ──────────────────────────────────────────────────────
// SDN_RESOURCES' read and write branches carried NO session check of any
// kind, so the licence key -- shipped to the browser and readable by anyone
// who can open sairndesign.html -- was the whole authorisation for all
// eighteen resources, five of them Tier A. Found while writing sdn_pos's
// cross-tenant arms: the [S] arms could not be written, because there was no
// signature to attack.
//
// ── THE HALF THAT BREAKS APPS, AND IT IS THE HALF THIS FILE IS MOSTLY ABOUT
// A gate is one line. The failure this platform has recorded twice is not
// forgetting the gate, it is arming it before the CLIENT can send a token --
// which answers 403 "sign in first" to every correctly signed-in employee and
// fails closed AND confusingly, the hardest failure to read.
//
// MEASURED BEFORE ARMING: 30 sdnData() call sites across 19 resources, and
// exactly ONE passed the `withSession` flag -- sdn_clients. None of the five
// gated here did. So sairndesign.html's header was made unconditional in the
// same commit. THE TWO ARMS THAT CHECK THAT ARE THE POINT OF THIS FILE, and
// they read the shipped page rather than trusting the commit message.
//
// ── AND THE SECOND LIST, WHICH IS WHERE THIS GOES WRONG QUIETLY ──────────
// A resource in SD_SESSION_GATED and NOT in SD_GATE_APP resolves expectedApp
// to 'stonedesk' by default, so a genuine SAIRNdesign token fails
// verification and the caller is refused with "sign in first" no matter what
// they do. The two lists DISAGREEING is the defect, so the arm below asserts
// they AGREE rather than asserting either one's contents -- the same shape
// api/sd-data-sf-session-gate.test.js uses for SAIRNfreedom.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['sdn', 'session', 'gate', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { signSessionToken } = require('./_lib/auth');

const HASH = 'studio-A-hash';
const APP = 'sairndesign';
const SD_DATA = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
const PAGE = fs.readFileSync(path.join(__dirname, '..', 'sairndesign.html'), 'utf8');

// The five this commit gates. Written out rather than parsed, because the
// arms below cross-check the SOURCE against this list in both directions --
// a list derived from the source could not catch the source being wrong.
// GREW BY FOUR ON 2026-09-24 and the two-lists arm caught the growth the day
// it happened -- which is the arm doing its job, not a defect in it.
// sdn_projects, sdn_proposals, sdn_specitems and sdn_timeentries were
// individually read and promoted B->A hours AFTER the first five were gated,
// and the gate's stopping rule was "Tier A", not "these five names".
const GATED = ['sdn_contracts', 'sdn_discounts', 'sdn_invoices', 'sdn_pos',
               'sdn_projects', 'sdn_proposals', 'sdn_referrals',
               'sdn_specitems', 'sdn_timeentries'];

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
  console.log('SAIRNdesign -- the five Tier A resources demand an employee session\n');

  section('THE TWO LISTS MUST AGREE -- the way this goes wrong quietly');

  test('every gated sdn_ resource has an SD_GATE_APP entry', function () {
    const gatedIn = (SD_DATA.match(/'(sdn_[a-z_]+)':\s*\['read', 'write'\]/g) || [])
      .map(s => s.match(/'(sdn_[a-z_]+)'/)[1]).sort();
    const appIn = (SD_DATA.match(/'(sdn_[a-z_]+)':\s*'sairndesign'/g) || [])
      .map(s => s.match(/'(sdn_[a-z_]+)'/)[1]).sort();
    assert.ok(gatedIn.length >= 5,
      'the parser found ' + gatedIn.length + ' gated sdn_ entries -- a broken '
      + 'parser reported as a clean platform is the one failure this must not have');
    assert.deepStrictEqual(gatedIn, appIn,
      'SD_SESSION_GATED and SD_GATE_APP disagree. A resource in the first and '
      + 'not the second resolves expectedApp to "stonedesk" and refuses every '
      + 'correctly signed-in designer -- it fails CLOSED and confusingly.');
    assert.deepStrictEqual(gatedIn, GATED.slice().sort(),
      'the gated set is not the NINE Tier A resources this file is about');
  });

  section('THE CLIENT CAN ACTUALLY SEND A TOKEN -- the precondition, read out '
    + 'of the shipped page');

  test('sdnData sends X-SD-Auth UNCONDITIONALLY', function () {
    const fn = PAGE.slice(PAGE.indexOf('function sdnData(action,resource,payload,withSession){'),
                          PAGE.indexOf('// ── AUTH CLIENT'));
    assert.ok(fn.length > 0, 'sdnData() not found -- anchor moved');
    assert.ok(/if\(sdnSession&&sdnSession\.token\)h\['X-SD-Auth'\]=sdnSession\.token;/.test(fn),
      'sdnData does not set X-SD-Auth on the token alone. If this is still '
      + 'conditional on `withSession`, the gate above refuses every resource '
      + 'whose call sites do not pass it -- which was 18 of 19 when this was '
      + 'measured.');
    assert.ok(!/if\(withSession&&sdnSession/.test(fn),
      'the withSession condition is back on the header');
  });

  test('a session exists BEFORE the first server read', function () {
    // sdnEnterApp sets sdnSession, then calls sdnHydrateAll. Reversed, every
    // hydrate on a fresh login would be unauthenticated and now refused.
    const enter = PAGE.slice(PAGE.indexOf('function sdnEnterApp(d){'),
                             PAGE.indexOf('// Restores a still-valid session'));
    const setsSession = enter.indexOf('sdnSession={token:d.token');
    const hydrates = enter.indexOf('sdnHydrateAll()');
    assert.ok(setsSession > -1 && hydrates > -1,
      'could not find both the session assignment and the hydrate in sdnEnterApp');
    assert.ok(setsSession < hydrates,
      'sdnEnterApp hydrates BEFORE it sets the session, so the first read after '
      + 'a login carries no token and is now refused');
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
        { action: 'write', resource: resource, payload: { id: 'X-1' } });
      assert.strictEqual(res.statusCode, 403,
        'answered ' + res.statusCode + ' ' + JSON.stringify(res.body));
    });

    await atest(resource + ' read WITH a valid designer session is allowed',
      async function () {
        // THE PAIRED POSITIVE, and the half that matters most here: a gate
        // that refused everybody would pass every arm above and lock the
        // studio out of its own data.
        const res = await callWith(withToken(APP), { action: 'read', resource: resource });
        assert.strictEqual(res.statusCode, 200,
          'a correctly signed-in designer was refused: ' + res.statusCode + ' '
          + JSON.stringify(res.body) + ' -- this is the failure arming a gate '
          + 'before the client can send a token produces, and it is why the '
          + 'header change landed in the same commit');
      });

    await atest(resource + ' refuses a token minted for ANOTHER SAIRN app',
      async function () {
        // Guardian Check 28's collision, and the reason SD_GATE_APP exists.
        const res = await callWith(withToken('sairnbuild'),
          { action: 'read', resource: resource });
        assert.strictEqual(res.statusCode, 403,
          'a sairnbuild session reached ' + resource);
      });
  }

  section('AND THE NINE THAT ARE NOT GATED ARE STILL NOT GATED');

  await atest('sdn_moodboards still answers without a session', async function () {
    // NOT AN ENDORSEMENT -- a disclosure. Stopping at Tier A is the scope
    // SAIRNfreedom's entry set, and widening it is a product decision about
    // who may see a mood board that nobody has made. This arm exists so the
    // day somebody makes it, the change is visible here rather than silent.
    const res = await callWith(BEARER, { action: 'read', resource: 'sdn_moodboards' });
    assert.strictEqual(res.statusCode, 200,
      'sdn_moodboards is now gated too. That may well be right -- but it is a '
      + 'scope change and this arm is where it gets noticed.');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
