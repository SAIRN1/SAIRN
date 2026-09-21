// api/provisioner-health-sole-role.test.js
//
// REQUIREMENT: the trapdoor detector reports a licence that cannot get a
// sole-role holder back, and watches every app that can reach that state.
//
// ── WHY THIS EXISTS ────────────────────────────────────────────────────────
// api/provisioner-health.js counted active rows holding ANY role in that app's
// PROVISIONING_ROLES. For the five apps with two provisioning roles that is the
// wrong set: a StoneDesk licence with an active `admin` and NO `owner` row at
// all reported HEALTHY, while `setup` refuses a non-owner creating an owner and
// `bootstrap` 409s whenever any row exists. Nobody could leave that state and
// nothing said so.
//
// THE SAME BLIND SPOT THE GUARD HAD, IN THE TOOL BUILT TO CATCH IT. The guard
// in api/sd-auth.js was fixed hours earlier the same day; the monitor watching
// for the state that guard prevents was counting the same wrong set.
//
// ── THE DISTINCTION BELOW WAS DRIVEN, AND IT CORRECTED AN OVERSTATEMENT ────
// The finding was first written as "zero active owners plus an active admin is
// unrecoverable". Driving it against the real api/sd-auth.js handler said
// otherwise: `set_active`'s guard only blocks DEACTIVATION, so an active admin
// CAN reactivate an INACTIVE owner (200, write sent). What an admin cannot do
// is CREATE one (403 FORBIDDEN).
//
// So there are two different situations and they need different words:
//   SOLE_ROLE_TRAPDOOR   no sole-role row AT ALL -- nothing to reactivate,
//                        nothing that can be minted. SQL required.
//   SOLE_ROLE_DEGRADED   sole-role rows exist but all inactive -- an active
//                        provisioner can reactivate one. No SQL required.
// Collapsing them would have cried emergency at a state somebody can fix from
// inside the app, which is how a monitor teaches people to ignore it.

const path = require('path');
const assert = require('assert');

const ROOT = path.join(__dirname, '..');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://fake.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'fake-service-key';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || 'test-secret-do-not-use-in-prod';

const licenseMod = require(path.join(ROOT, 'api/_lib/license.js'));
let APP_ID = 'stonedesk';
licenseMod.validateLicenseKey = async () => ({
  valid: true, active: true, license_hash: 'HASH1', app_id: APP_ID
});

const handler = require(path.join(ROOT, 'api/provisioner-health.js'));

// Drive the real endpoint against a roster. `wrote` proves the read-only
// claim in the file's own header -- a health check that writes is not one.
async function health(appId, rows) {
  APP_ID = appId;
  let wrote = false;
  const realFetch = global.fetch;
  global.fetch = async (url, opt) => {
    if (opt && opt.method && opt.method !== 'GET') wrote = true;
    return { ok: true, status: 200, json: async () => rows };
  };
  const res = { statusCode: null, body: null,
    status(c) { this.statusCode = c; return this; },
    json(b) { this.body = b; return this; } };
  try {
    await handler({ method: 'POST', headers: { authorization: 'Bearer KEY' },
                    body: { action: 'provisioner_health' } }, res);
  } finally { global.fetch = realFetch; }
  return { status: res.statusCode, body: res.body, wrote };
}

const OWNER_ON = { role: 'owner', active: true };
const OWNER_OFF = { role: 'owner', active: false };
const ADMIN_ON = { role: 'admin', active: true };
const ADMIN_OFF = { role: 'admin', active: false };

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

(async function () {
  console.log('api/provisioner-health.js -- the sole-role blind spot');

  section('THE STATE THAT READ AS HEALTHY');

  await test('an active ADMIN and NO owner row at all -> SOLE_ROLE_TRAPDOOR',
    async () => {
      const r = await health('stonedesk', [ADMIN_ON]);
      assert.strictEqual(r.status, 200);
      assert.strictEqual(r.body.state, 'SOLE_ROLE_TRAPDOOR',
        'this is the state that reported HEALTHY until 2026-09-21');
      assert.strictEqual(r.body.active_provisioners, 1,
        'the old count is still reported -- it was not wrong, it was answering '
        + 'a different question');
      assert.strictEqual(r.body.sole_role_rows, 0);
      assert.match(r.body.message, /UNRECOVERABLE/);
      assert.strictEqual(r.wrote, false, 'a health check must not write');
    });

  await test('...and the message does not make the FALSE claim that there is '
    + 'no provisioner row', async () => {
      const r = await health('stonedesk', [ADMIN_ON]);
      // ── THIS ARM WAS WEAKER AND A MUTATION WALKED THROUGH IT ────────────
      // It asserted only that the message mentions "owner" somewhere. The
      // message names the role TWICE, so rewriting one clause to "this licence
      // holds NO provisioner row at all" left the other mention in place and
      // the arm passed -- while the sentence had become FALSE, because an
      // active admin provisioner demonstrably exists in this state. Caught by
      // tests/run_provisioner_health_sole_role_sabotage_probe.py mutation 7,
      // which is what the probe is for.
      //
      // The claim that matters is not "the role is mentioned" but "the message
      // is true", so that is what is asserted.
      assert.ok(r.body.active_provisioners > 0,
        'the fixture no longer has an active provisioner, so this arm is not '
        + 'testing the case it describes');
      assert.ok(!/NO provisioner row/i.test(r.body.message),
        'the message says there is no provisioner row while an active '
        + 'provisioner exists -- the operator is told something they can see '
        + 'is wrong, which is how a monitor loses its reader');
      assert.match(r.body.message, /"owner"/,
        'the operator has to know WHICH role to insert; "a provisioner" does '
        + 'not tell them, and on this app it is the wrong word besides');
    });

  section('THE STATE THAT IS RECOVERABLE -- and must NOT cry emergency');

  await test('an active ADMIN and an INACTIVE owner -> SOLE_ROLE_DEGRADED',
    async () => {
      const r = await health('stonedesk', [ADMIN_ON, OWNER_OFF]);
      assert.strictEqual(r.body.state, 'SOLE_ROLE_DEGRADED');
      assert.strictEqual(r.body.sole_role_rows, 1);
      assert.strictEqual(r.body.active_sole_role, 0);
      // DRIVEN against the real api/sd-auth.js: an active admin CAN reactivate
      // an inactive owner. Calling this unrecoverable would be false.
      assert.ok(!/UNRECOVERABLE/.test(r.body.message),
        'this state is recoverable from inside the app -- an active provisioner '
        + 'can reactivate the inactive holder, which was DRIVEN, and saying '
        + 'UNRECOVERABLE here would be the monitor crying wolf');
      assert.match(r.body.message, /RECOVERABLE/);
    });

  section('THE CONTROLS -- the new states must not fire where they should not');

  await test('an active OWNER and an active ADMIN -> HEALTHY', async () => {
    const r = await health('stonedesk', [OWNER_ON, ADMIN_ON]);
    assert.strictEqual(r.body.state, 'HEALTHY');
  });

  await test('an active OWNER alone -> HEALTHY', async () => {
    const r = await health('stonedesk', [OWNER_ON]);
    assert.strictEqual(r.body.state, 'HEALTHY');
  });

  await test('zero rows -> NO_CREDENTIALS, not a trapdoor of any kind',
    async () => {
      const r = await health('stonedesk', []);
      assert.strictEqual(r.body.state, 'NO_CREDENTIALS');
    });

  await test('no ACTIVE provisioner at all -> the classic TRAPDOOR wins, '
    + 'because it is strictly worse', async () => {
      const r = await health('stonedesk', [OWNER_OFF, ADMIN_OFF]);
      assert.strictEqual(r.body.state, 'TRAPDOOR',
        'a licence with no active provisioner is also missing an active owner; '
        + 'reporting the narrower finding would understate it');
    });

  section('A SINGLE-PROVISIONING-ROLE APP CANNOT REACH THE NEW STATES');

  await test('SAIRNcode (roles: admin) reports sole_role null and stays HEALTHY',
    async () => {
      const r = await health('sairncode', [{ role: 'admin', active: true }]);
      assert.strictEqual(r.body.sole_role, null,
        'null, not absent -- an absent key reads as "not checked" when it means '
        + '"the two questions coincide here"');
      assert.strictEqual(r.body.state, 'HEALTHY');
      assert.strictEqual(r.body.sole_role_rows, null);
    });

  section('COVERAGE -- every app that can reach the trapdoor is watched');

  await test('every auth endpoint with a set_active AND PROVISIONING_ROLES is '
    + 'in the map', () => {
      const fs = require('fs');
      const API = path.join(ROOT, 'api');
      const src = fs.readFileSync(path.join(API, 'provisioner-health.js'), 'utf8');
      const mapBlock = src.match(/const APPS = \{[\s\S]*?\n\};/)[0];
      const watched = new Set(
        [...mapBlock.matchAll(/^ {2}([a-z]+):/gm)].map((m) => m[1]));
      // DERIVED FROM THE ENDPOINTS, not listed here. A list would go stale the
      // same way the sentence this replaced did -- it said the other files
      // "cannot reach this state", which was true when written and wrong by
      // the time ten more apps existed.
      const shouldWatch = fs.readdirSync(API)
        .filter((f) => /^[a-z-]+-auth\.js$/.test(f))
        .map((f) => {
          const s = fs.readFileSync(path.join(API, f), 'utf8');
          if (!/action === 'set_active'/.test(s)) return null;
          if (!/const PROVISIONING_ROLES = /.test(s)) return null;
          const app = /const APP = '([a-z]+)'/.exec(s);
          return app ? app[1] : null;
        })
        .filter(Boolean);
      const missing = shouldWatch.filter((a) => !watched.has(a));
      assert.deepStrictEqual(missing, [],
        'these apps implement set_active and declare PROVISIONING_ROLES, so '
        + 'they can reach the trapdoor, and nothing watches them: '
        + missing.join(', '));
    });

  await test('the map imports each rule rather than restating it', () => {
    const fs = require('fs');
    const src = fs.readFileSync(path.join(ROOT, 'api/provisioner-health.js'), 'utf8');
    const mapBlock = src.match(/const APPS = \{[\s\S]*?\n\};/)[0];
    // A literal role name in the map would be this file re-deriving the rule
    // it checks -- the exact drift its own header warns about.
    assert.ok(!/roles: \[/.test(mapBlock),
      'a role list is written out in the map instead of imported; the header '
      + 'says importing is what stops this file drifting from the rule');
    assert.ok(!/sole: '/.test(mapBlock),
      'a sole role is written out in the map instead of imported');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  if (fail) { console.log('FAILURES ABOVE'); process.exit(1); }
})();
