// api/sd-data-scp-licence-only.test.js
//
// Run:  node api/sd-data-scp-licence-only.test.js
//
// THE NINE SAIRNscape RESOURCES THAT WERE LICENCE-KEY-ALONE, NOW SESSION-GATED.
//
// api/sd-data-scp-session-gate.test.js drives the two Tier A rows -- `invoices`
// and `scp_quotes` -- and the witness `scp_vendors`. This file drives the other
// NINE. It was written (2026-09-29) when they answered a valid licence with no
// employee session. That posture was RETIRED on purpose: `customers` was
// session-gated on 2026-10-05 (5e33157e) and the other eight on 2026-10-11 and
// 2026-10-14 (0442646c, d99b47f9, 5776ef19). The B arms kept asserting the old
// posture and went red for a correct reason (cc b35 bisect); inverted 2026-10-21
// (hank b42) to assert the posture that is actually shipped.
//
// ── EACH RESOURCE NOW GETS THREE ARMS ─────────────────────────────────────
//   B1  GATE      a valid sairnscape licence, NO session -> 403 FORBIDDEN
//   B2  PASSES    a valid sairnscape licence WITH a session -> not refused
//   C   BOUNDARY  a valid licence whose app_id is ANOTHER APP -> refused
//
// B1 alone is satisfied by a handler that refuses everything; B2 rules that
// out. C keeps the licence as the boundary underneath the session.
//
// ── THE TWO NAMES THAT ARE NOT THE TABLE NAMES ────────────────────────────
// `customers` and `schedule` are registered under their BARE names and reach
// `scp_customers` and `scp_schedule`. Written out here rather than derived,
// because a list derived from the registry could not catch the registry being
// wrong -- the same reasoning the gate file gives for its GATED list.
//
// NOTHING IS FIXED HERE. api/sd-data.js is inside another session's claim; if
// an arm below finds a hole it is reported, not patched.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['scp', 'licence', 'only', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const HASH = 'scape-company-A-hash';
const APP = 'sairnscape';
const OTHER_APP = 'stonedesk';
const SD_DATA = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
const REG = require('./_resources/index.js');

// The two the gate file already covers. Named so the arm below can assert this
// file and that one PARTITION the twelve rather than overlapping or leaving a
// gap -- a resource in neither is one nothing drives at all, which is the state
// this file exists to end.
const GATED = ['invoices', 'scp_quotes'];
// The witness the gate file already drives.
const WITNESS = 'scp_vendors';
// The nine with no arm anywhere before this file.
const UNDRIVEN = [
  'customers',            // -> scp_customers
  'schedule',             // -> scp_schedule
  'scp_jobs',
  'scp_progress_photos',
  'scp_designs',
  'scp_irr_controllers',
  'scp_irr_zones',
  'scp_irr_schedules',
  'scp_water_features'
];

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

// The licence mock carries the app_id, which is the whole boundary under test:
// pass sairnscape and the read should land, pass stonedesk and it must not.
function loadHandler(appId) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: HASH,
                 trial_ends_at: null, stripe_subscription_id: null,
                 app_id: appId };
      }
    }
  };
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}
// A signed-in sairnscape owner, plus the one database answer the gate needs:
// it re-checks that the employee is still ACTIVE. Same stub as
// api/sd-data-scp-session-gate.test.js; without it B2 would fail 403
// CREDENTIAL_INACTIVE and read exactly like the gate refusing a real session.
const { signSessionToken } = require('./_lib/auth');
function withSession() {
  return {
    'x-sd-auth': signSessionToken({ app: APP, employee_id: 'emp-1',
                                    role: 'owner', license_hash: HASH }),
    fetch: async function (url, opts) {
      if (/_employee_auth\?/.test(String(url))) {
        return { ok: true, status: 200, json: async () =>
          [{ license_hash: HASH, employee_id: 'emp-1', role: 'owner', active: true }] };
      }
      return { ok: true, status: 200, json: async () => [] };
    }
  };
}
async function callAs(appId, body, session) {
  const h = loadHandler(appId);
  const res = mockRes();
  const headers = { authorization: 'Bearer KEY' };
  const prevFetch = global.fetch;
  if (session) { headers['x-sd-auth'] = session['x-sd-auth']; global.fetch = session.fetch; }
  try {
    await h({ method: 'POST', headers: headers, body: body }, res);
  } finally {
    global.fetch = prevFetch;
  }
  return res;
}

(async function () {
  console.log('SAIRNscape licence-key-alone -- the nine nobody drove');

  // ── A. THE PARTITION, so this file cannot silently stop covering them ────
  section('A. the twelve are partitioned, and this file owns nine of them');

  test('A1. the registry still lists exactly the twelve these three sets '
    + 'partition. If SAIRNscape grows a thirteenth resource it belongs in one '
    + 'of them on the same day, and this arm is where that gets noticed',
    function () {
      const registered = REG.RESOURCE_NAMES_BY_APP[APP];
      assert.ok(Array.isArray(registered) && registered.length > 0,
        'the sairnscape registry read empty -- every arm below would be vacuous');
      const covered = GATED.concat([WITNESS], UNDRIVEN).sort();
      assert.deepStrictEqual(
        registered.slice().sort(), covered,
        'the registry and the three sets in this file disagree. A name in the '
        + 'registry and in none of the sets is a resource NOTHING drives, which '
        + 'is the state this file exists to end.');
    });

  test('A2. ...and the three sets do not OVERLAP. A resource driven here and in '
    + 'the gate file would make one of the two arms pass for the other\'s '
    + 'reason', function () {
      const all = GATED.concat([WITNESS], UNDRIVEN);
      assert.strictEqual(new Set(all).size, all.length,
        'a resource appears in more than one set: ' + all.join(', '));
    });

  // THE TABLE, NOT THE FIRST MENTION. This arm used to search 9,000 characters
  // after the first 'SD_SESSION_GATED' in the file -- a COMMENT at line 99 --
  // while the entries sit ~1,800 lines later, so it could never see one and
  // passed while all nine were gated (cc b35). Same declaration anchor as
  // api/sd-data-scp-session-gate.test.js, plus a control on each side so a
  // wrong window fails here instead of passing.
  const GATE_TABLE = (SD_DATA.match(/const SD_SESSION_GATED = \{[\s\S]*?\n    \};/) || [''])[0];
  function inGateTable(r) {
    return new RegExp("\\n\\s*'" + r + "':\\s*\\[[^\\]]*'read'").test(GATE_TABLE);
  }

  test('A3. all nine are in the SD_SESSION_GATED table for read. If one leaves '
    + 'it, its B1 arm below fails for a correct reason and this arm names it '
    + 'first', function () {
      assert.ok(GATE_TABLE.length > 0, 'const SD_SESSION_GATED = { ... } not found');
      assert.ok(inGateTable('invoices'),
        'CONTROL: the parsed table does not contain invoices -- the window is wrong');
      assert.ok(!inGateTable('sd_customers'),
        'CONTROL: the parsed table contains sd_customers, which is not gated -- the window is wrong');
      const notGated = UNDRIVEN.filter(function (r) { return !inGateTable(r); });
      assert.deepStrictEqual(notGated, [],
        'these are no longer session-gated for read: ' + notGated.join(', ')
        + ' -- a scope change nobody recorded');
    });

  // ── B. THE POSTURE, nine times ──────────────────────────────────────────
  section('B. a valid sairnscape licence needs an employee session for all nine');

  for (const r of UNDRIVEN) {
    await atest('B1. ' + r + ' is REFUSED without a session: 403 FORBIDDEN, '
      + '"A valid employee session is required"',
      async function () {
        const res = await callAs(APP, { action: 'read', resource: r });
        const err = (res.body && res.body.error) || {};
        assert.ok(res.statusCode === 403 && err.code === 'FORBIDDEN'
                  && /valid employee session is required/.test(err.message || ''),
          r + ' answered ' + res.statusCode + ' ' + JSON.stringify(err).slice(0, 120)
          + ' with NO session. It is in SD_SESSION_GATED, so a licence alone '
          + 'must not reach it.');
      });
  }

  for (const r of UNDRIVEN) {
    await atest('B2. ' + r + ' is NOT refused WITH a sairnscape session, so B1 '
      + 'is a gate and not a handler that refuses everything',
      async function () {
        const res = await callAs(APP, { action: 'read', resource: r }, withSession());
        assert.ok(res.statusCode !== 401 && res.statusCode !== 403,
          r + ' answered ' + res.statusCode + ' '
          + JSON.stringify((res.body && res.body.error) || {}).slice(0, 120)
          + ' to a signed-in owner of its own app');
      });
  }

  // ── C. THE BOUNDARY, and this is what makes section B worth having ──────
  section('C. THE LICENCE IS STILL THE BOUNDARY -- another app\'s licence is '
    + 'refused for all nine');

  for (const r of UNDRIVEN) {
    await atest('C. ' + r + ' is REFUSED to a valid ' + OTHER_APP + ' licence. '
      + 'Without this arm, "answers without a session" is satisfied by a '
      + 'handler that answers everyone',
      async function () {
        const res = await callAs(OTHER_APP, { action: 'read', resource: r });
        // The BOUNDARY refusal specifically, not any 4xx: a 400 for a missing
        // payload key would otherwise satisfy this arm while the boundary did
        // nothing at all.
        // THE BOUNDARY REFUSAL SPECIFICALLY, and it has no error CODE -- it is
        // a 400 whose message is the allow-list this licence may reach, with
        // the resource absent from it. Asserting any 4xx would be satisfied by
        // a 400 about a missing payload key, which names the resource and means
        // the boundary did nothing.
        const msg = (res.body && res.body.error && res.body.error.message) || '';
        const boundary = res.statusCode === 400
          && /^resource must be one of/.test(msg)
          // WHOLE LIST ITEM, NOT A SUBSTRING. `customers` is a substring of
          // stonedesk's own `sd_customers`, so an indexOf test reported the
          // boundary as NOT having fired on the one resource whose name
          // collides -- a false finding on a correctly refused read.
          && msg.replace(/^resource must be one of:\s*/, '')
                .split(/\s*,\s*/).indexOf(r) === -1;
        assert.ok(boundary,
          r + ' ANSWERED ' + res.statusCode + ' (' + msg.slice(0, 60) + ') TO A '
          + OTHER_APP.toUpperCase()
          + ' LICENCE. Licence-key-alone means the licence IS the boundary; if '
          + 'another app\'s key reaches this resource there is no boundary at '
          + 'all. THIS IS A FINDING, NOT A TEST BUG -- report it, do not patch '
          + 'api/sd-data.js from here.');
      });
  }

  // ── D. THE KNOWN-BAD CONTROL for section C ──────────────────────────────
  section('D. the boundary arm can fail -- driven, not assumed');

  await atest('D1. a resource SAIRNscape does not own is refused to a '
    + 'sairnscape licence, so section C is reading a real boundary rather than '
    + 'a handler that refuses every unknown name the same way',
    async function () {
      const res = await callAs(APP, { action: 'read', resource: 'law_matters' });
      assert.ok(res.statusCode >= 400,
        'a sairnscape licence reached law_matters -- the app boundary is not '
        + 'enforced at all and every arm in section C is vacuous');
    });

  await atest('D2. ...and the SILENT HALF: the witness the gate file already '
    + 'drives still answers to a sairnscape licence, so D1 is not satisfied by '
    + 'a handler refusing everything',
    async function () {
      const res = await callAs(APP, { action: 'read', resource: WITNESS });
      // NOT `statusCode < 400`. This harness has no network and no Supabase
      // mock, so a resource that PASSES the boundary then fails its upstream
      // fetch and answers 500. Asserting 2xx would make every arm in this file
      // depend on a database, which is the opposite of what a boundary test
      // should need. What must be true is that it is not refused BY THE
      // BOUNDARY: that refusal is 400 UNKNOWN_RESOURCE, and a 500 from an
      // unreachable host is a different fact.
      const msg = (res.body && res.body.error && res.body.error.message) || '';
      assert.ok(!(res.statusCode === 400 && /^resource must be one of/.test(msg)
                  && msg.indexOf(WITNESS) === -1),
        WITNESS + ' is refused BY THE APP BOUNDARY to its own app\'s licence -- '
        + 'if that is right, the gate file\'s witness arm is wrong too and both '
        + 'need re-reading');
    });

  test('D3. ANCHOR: isVisibleTo is still the name the boundary is built on. If '
    + 'it is renamed or removed, sections C and D go green against nothing',
    function () {
      assert.strictEqual(typeof REG.isVisibleTo, 'function',
        'api/_resources/index.js no longer exports isVisibleTo');
      assert.ok(REG.isVisibleTo('scp_vendors', APP),
        'the registry says sairnscape cannot see its own resource');
      assert.ok(!REG.isVisibleTo('law_matters', APP),
        'the registry says sairnscape CAN see law_matters -- the boundary this '
        + 'file drives does not exist');
    });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
