// api/sd-data-scp-licence-only.test.js
//
// Run:  node api/sd-data-scp-licence-only.test.js
//
// THE NINE SAIRNscape RESOURCES NOBODY DRIVES.
//
// api/sd-data-scp-session-gate.test.js gates the two Tier A rows -- `invoices`
// and `scp_quotes` -- and drives exactly ONE of the remaining ten as the
// UNGATED_WITNESS, `scp_vendors`, "so the day somebody widens the scope it is
// visible here". That witness is the right idea and it covers one tenth of the
// surface: the other NINE licence-key-alone resources have no arm at all, so a
// change to any of them is silent in both directions.
//
// ── WHAT LICENCE-KEY-ALONE MEANS, AND WHAT IT MUST NOT MEAN ────────────────
// It means a valid SAIRNscape licence reaches these nine with no employee
// session. That is a deliberate product posture and this file does NOT argue
// with it -- the same disclosure the witness arm makes, nine more times.
//
// It must NOT mean the licence stops being the boundary. So each resource gets
// TWO arms, and the second is what makes the first worth having:
//
//   POSTURE   a valid sairnscape licence, no session -> 200
//   BOUNDARY  a valid licence whose app_id is ANOTHER APP -> refused
//
// Without the boundary arm, "answers 200 without a session" is satisfied by a
// handler that answers 200 to everyone, which is the failure the arm exists to
// rule out. Without the posture arm, the boundary arm is satisfied by a handler
// that refuses everything.
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
async function callAs(appId, body) {
  const h = loadHandler(appId);
  const res = mockRes();
  await h({ method: 'POST', headers: { authorization: 'Bearer KEY' },
            body: body }, res);
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

  test('A3. none of the nine is in SD_SESSION_GATED. If one is gated now, its '
    + 'POSTURE arm below would fail for a correct reason and this arm names it '
    + 'first', function () {
      const gatedNow = UNDRIVEN.filter(function (r) {
        return new RegExp("'" + r + "':\\s*\\[").test(
          SD_DATA.slice(SD_DATA.indexOf('SD_SESSION_GATED'),
                        SD_DATA.indexOf('SD_SESSION_GATED') + 9000));
      });
      assert.deepStrictEqual(gatedNow, [],
        'these are gated now and this file still calls them licence-only: '
        + gatedNow.join(', ') + ' -- a scope change nobody recorded');
    });

  // ── B. THE POSTURE, nine times ──────────────────────────────────────────
  section('B. a valid sairnscape licence with NO session reaches all nine');

  for (const r of UNDRIVEN) {
    await atest('B. ' + r + ' answers without a session -- a DISCLOSURE, not an '
      + 'endorsement, so widening the scope becomes visible here',
      async function () {
        const res = await callAs(APP, { action: 'read', resource: r });
        assert.notStrictEqual(res.statusCode, 401,
          r + ' now answers 401 NO_SESSION. That may well be right -- it is a '
          + 'scope change and this arm is where it gets noticed.');
        assert.notStrictEqual(res.statusCode, 403,
          r + ' now answers 403 FORBIDDEN, same point.');
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
