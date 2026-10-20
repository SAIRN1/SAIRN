// api/b27-leg-settings.test.js
// OWNER: cody   written 2026-10-19, batch b27, item 2(c)
//
// REQUIREMENT: the SAIRNlegacy gate must read the home's own settings row and
//   pass it to legRoles.decide() as the fifth argument -- and an ABSENT row
//   must still mean the NARROW default.
//
//   node api/b27-leg-settings.test.js
//
// Exit: 0 every arm passed · 1 an arm FAILED · 3 COULD NOT RUN
//
// ── WHY THIS FILE EXISTS ───────────────────────────────────────────────────
// api/_lib/leg-roles.js has owned the F2 and F3 policy since b18 and
// sql/sairnlegacy_settings_schema.sql states the gap in its own words:
//
//   "NOTHING READS THIS TABLE YET, AND THAT IS STATED HERE RATHER THAN LEFT TO
//    BE DISCOVERED. api/sd-data.js passes no `home` argument, so every
//    apprentice currently gets the empty default and F3's countersign branch
//    is unreachable in production."
//
// So the policy was correct, the schema was correct, the module's tests were
// green, and the feature did nothing -- because the ONE call site passed three
// arguments to a five-argument function. This suite drives the REAL HANDLER,
// because nothing about testing the module could have shown that.
//
// ── WHAT IS DELIBERATELY NOT ASSERTED ──────────────────────────────────────
// NOT that the F2 livery GRANT works end to end. decide()'s branch 4 needs
// BOTH the home's setting AND a per-employee grant (`grants[resource] === true`
// -- b17's grant table), and api/sd-data.js passes `null` for grants today. So
// S1 asserts the setting makes the resource GRANTABLE, which is the half this
// change landed, and the grant wiring is named as open rather than implied.
// liveryGrantable() is the module's own single source for that question, which
// is why asserting on it is not a reimplementation.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const API_DIR = __dirname;
const SD_DATA = process.env.SAIRN_B27_SD_DATA || path.join(API_DIR, 'sd-data.js');

let pass = 0;
const failed = [];
function ok(l) { pass += 1; console.log('  ok   ' + l); }
function bad(l, why) {
  failed.push(l);
  console.log('  FAIL ' + l + (why ? '\n         ' + String(why).slice(0, 500) : ''));
}
function section(t) { console.log('\n' + t); }
function couldNotRun(why) {
  console.log('COULD NOT RUN: ' + why + ' Nothing was verified.');
  process.exit(3);
}

if (!fs.existsSync(SD_DATA)) couldNotRun(SD_DATA + ' does not exist.');
const legRoles = require(path.join(API_DIR, '_lib/leg-roles.js'));

// ── THE HARNESS. Licence, session and fetch mocked; nothing real is reached.
const HASH = 'hash-of-the-b27-leg-settings-licence';
const KEY = 'legkey-placeholder';
const LICENCE = require.resolve(path.join(API_DIR, '_lib/license.js'));
require.cache[LICENCE] = {
  id: LICENCE, filename: LICENCE, loaded: true,
  exports: {
    validateLicenseKey: async () => ({
      valid: true, active: true, license_hash: HASH,
      stripe_subscription_id: null, trial_ends_at: null, app_id: 'sairnlegacy'
    }),
    hashLicense: () => HASH,
  },
};
process.env.SUPABASE_URL = 'https://example.invalid';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'service-role-for-the-test';
process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  process.env[['SD', 'AUTH', 'SECRET'].join('_')]
  || ['b27', 'legset', String(process.pid)].join('-');

// THE SESSION HEADER IS READ OUT OF auth.js, NEVER TYPED.
const AUTH_SRC = fs.readFileSync(path.join(API_DIR, '_lib/auth.js'), 'utf8');
const HDR_M = AUTH_SRC.match(/function tokenFromRequest\(req\)\s*\{\s*\n\s*const h = req\.headers\[['"]([a-z0-9-]+)['"]\]/);
if (!HDR_M) {
  couldNotRun('the session header name could not be read out of '
            + 'api/_lib/auth.js, so every arm would fail its precondition for '
            + 'a reason that is not about settings.');
}
const SESSION_HEADER = HDR_M[1];
const { signSessionToken } = require(path.join(API_DIR, '_lib/auth.js'));

// `settingsRow` is the ONE knob: null means the home has never saved settings.
let settingsRow = null;
let settingsReads = 0;
const seen = [];
global.fetch = async (url, init) => {
  const u = String(url);
  const method = (init && init.method) || 'GET';
  if (/_employee_auth\?/.test(u)) {
    return { ok: true, status: 200,
             json: async () => [{ license_hash: HASH, employee_id: 'emp-1',
                                  role: 'owner', active: true }] };
  }
  if (/sairnlegacy_settings\?/.test(u)) {
    settingsReads += 1;
    return { ok: true, status: 200,
             json: async () => (settingsRow ? [settingsRow] : []) };
  }
  seen.push({ url: u, method: method });
  if (/_countersign_tokens\?/.test(u)) {
    return { ok: true, status: 200, json: async () => [] };
  }
  if (method === 'POST' || method === 'PATCH') {
    let b = null;
    try { b = JSON.parse(init.body); } catch (e) { b = {}; }
    return { ok: true, status: 200, json: async () => [b] };
  }
  return { ok: true, status: 200, json: async () => [] };
};

delete require.cache[require.resolve(SD_DATA)];
const handler = require(SD_DATA);

function fakeRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}
async function call(resource, action, role, payload) {
  seen.length = 0;
  settingsReads = 0;
  const headers = { authorization: 'Bearer ' + KEY };
  headers[SESSION_HEADER] = signSessionToken({
    app: 'sairnlegacy', employee_id: 'emp-1', role: role, license_hash: HASH });
  const body = { action: action, resource: resource };
  if (action !== 'read') body.payload = payload || { id: 'X1' };
  const res = fakeRes();
  await handler({ method: 'POST', headers: headers, body: body }, res);
  return res;
}
function code(res) {
  return (res.body && res.body.error && res.body.error.code) || '';
}

const HOME_THROUGH = { livery_billing: 'through_the_home', apprentice: {} };
const HOME_DIRECT = { livery_billing: 'direct_to_family', apprentice: {} };
const HOME_COUNTERSIGN = {
  livery_billing: 'through_the_home',
  apprentice: { countersign: ['leg_cremations'] }
};

(async function main() {
  console.log('LEG SETTINGS -- THE FIFTH ARGUMENT -- criteria 2026-10-19.1');
  console.log('handler under test: ' + SD_DATA);

  section('P. PRECONDITIONS -- each a third state, never folded into a pass');

  const SRC = fs.readFileSync(SD_DATA, 'utf8').replace(/\r\n/g, '\n');
  // COMMENT-STRIPPED, because this repo has a recorded case of a precondition
  // satisfied by a comment ABOUT the code it was checking for.
  const CODE = SRC.split('\n').map((l) => l.replace(/\/\/.*$/, '')).join('\n');
  // ── RE-AIMED IN b29, AND THE OLD PATTERN WAS RIGHT TO FIRE ─────────────
  // P1 matched the call site LITERALLY, including `null` as the fourth
  // argument:
  //
  //     legRoles.decide(resource, legSess.role, action, null, legHome)
  //
  // b29 wired the fourth argument -- `legGrants`, read from
  // sairnlegacy_settings.livery_grants -- so the literal stopped matching and
  // P1 went red. That red was CORRECT behaviour from an arm pinned to a
  // spelling, and the fix is to pin it to the REQUIREMENT instead: five
  // arguments reach decide(), and the two optional ones are real values rather
  // than placeholders.
  //
  // THE NEW FORM IS STRICTLY STRONGER. It still goes red on a revert to three
  // arguments, AND it now goes red on a revert of either optional argument to
  // a literal `null` -- which is the state b18 to b27 was in for `home` and
  // b18 to b29 was in for `grants`: the argument present, the value inert, and
  // every module-level policy arm green.
  const P1_CALL = CODE.match(
    /legRoles\.decide\(resource, legSess\.role, action, ([^,]+), ([^)]+)\)/);
  const P1_GRANTS = P1_CALL ? P1_CALL[1].trim() : null;
  const P1_HOME = P1_CALL ? P1_CALL[2].trim() : null;
  if (P1_CALL && P1_GRANTS !== 'null' && P1_HOME !== 'null') {
    ok('P1. the gate calls decide() with FIVE arguments AND neither optional '
       + 'one is a literal null (grants=' + P1_GRANTS + ', home=' + P1_HOME
       + '), measured on comment-stripped source. A revert of either goes red '
       + 'here before the behaviour arms do, and names which');
  } else {
    bad('P1. api/sd-data.js does not pass five REAL arguments to '
        + 'legRoles.decide() -- either the call is back to three, or an '
        + 'optional argument is a literal null, which means the policy it '
        + 'feeds is inert while every module-level arm stays green',
        P1_CALL ? ('grants=' + P1_GRANTS + ' home=' + P1_HOME)
                : (CODE.match(/legRoles\.decide\([^)]*\)/)
                   || ['<no decide call found>'])[0]);
  }
  if (/sairnlegacy_settings\?license_hash=eq\./.test(CODE)) {
    ok('P2. ...and it reads the home\'s row from `sairnlegacy_settings`, which '
       + 'is the table sql/sairnlegacy_settings_schema.sql creates -- NOT '
       + '`leg_settings`, which does not exist');
  } else {
    bad('P2. the settings read is gone from api/sd-data.js', '');
  }

  section('S0. THE DEFAULT -- an ABSENT row still means the NARROW policy');
  // S0 IS THE ABLATION CONTROL. It must be green whether or not the fifth
  // argument is passed, because an absent row and a missing argument produce
  // the SAME narrow default -- which is the compatibility guarantee this
  // change had to keep. An arm that moved here would mean the change altered
  // behaviour for every home that has never saved settings.
  settingsRow = null;
  {
    const r = await call('leg_liverybookings', 'read', 'livery');
    if (r.statusCode === 403 && code(r) === 'FORBIDDEN') {
      ok('S0. with NO settings row, a livery token is still refused '
         + 'leg_liverybookings -- the narrow default, unchanged. THIS ARM IS '
         + 'GREEN IN BOTH LEGS OF THE ABLATION on purpose: an absent row and '
         + 'a missing fifth argument are indistinguishable, which is the '
         + 'compatibility guarantee');
    } else {
      bad('S0. an absent settings row must still produce the narrow default',
          'status=' + r.statusCode + ' code=' + code(r));
    }
  }
  // ── S0b IS A POLICY ARM, NOT A DISPATCHER ARM, AND THE FIRST SPELLING OF
  // ── IT WAS WRONG IN A WAY THAT MATTERS ──────────────────────────────────
  // It drove the dispatcher and asserted 403. The dispatcher answers **400**,
  // and not because of the policy: `prepare` is not a declared extraAction for
  // ANY leg_ resource, so checkEnvelope() refuses the verb before the role
  // gate runs. MEASURED: EXTRA_ACTIONS.leg_cremations is undefined and no
  // leg_ resource declares 'prepare'.
  //
  // The first spelling asserted `statusCode !== 403` for the POSITIVE case
  // (S2 below) and a 400 satisfied that -- so it would have reported F3
  // working while every prepare request was being refused as an unknown verb.
  // A pass built on "not the one status I thought of" is the vacuous shape
  // this platform keeps paying for.
  //
  // So the POLICY half -- which is what the fifth argument changes and what
  // this suite is for -- is asserted on decide() directly, and the DISPATCHER
  // half is recorded separately in section V below as the second gate it is.
  if (legRoles.decide('leg_cremations', 'apprentice',
                      legRoles.LEG_PREPARE_ACTION, null, null) === legRoles.DENY) {
    ok('S0b. ...and with NO settings row the POLICY denies an apprentice the '
       + 'prepare route on leg_cremations, because the default countersign '
       + 'list is empty');
  } else {
    bad('S0b. an apprentice must get no prepare route by default',
        'decide=' + legRoles.decide('leg_cremations', 'apprentice',
                                    legRoles.LEG_PREPARE_ACTION, null, null));
  }

  section('S1. F2 -- direct_to_family makes leg_liverybookings GRANTABLE');
  // THE ASSERTION IS ON GRANTABILITY, not on a completed grant, and the reason
  // is stated above: decide()'s branch 4 needs a per-employee grant too and
  // api/sd-data.js passes `null` for grants today. liveryGrantable() is the
  // module's own single source for "may a grant name this resource", so this is
  // the real question rather than a reimplementation of it.
  if (legRoles.liveryGrantable('leg_liverybookings', 'direct_to_family') === true
      && legRoles.liveryGrantable('leg_liverybookings', 'through_the_home') === false) {
    ok('S1. leg_liverybookings is GRANTABLE under direct_to_family and NOT '
       + 'under through_the_home -- the setting is what moves it, measured in '
       + 'both directions');
  } else {
    bad('S1. the F2 setting does not change grantability',
        'direct=' + legRoles.liveryGrantable('leg_liverybookings', 'direct_to_family')
        + ' through=' + legRoles.liveryGrantable('leg_liverybookings', 'through_the_home'));
  }
  // ...AND THE HANDLER REALLY DELIVERS THE SETTING. This is the arm that
  // distinguishes "the module can do it" from "the call site passes it".
  settingsRow = HOME_DIRECT;
  {
    const r = await call('leg_liverybookings', 'read', 'livery');
    const readIt = settingsReads;
    if (readIt === 1) {
      ok('S1b. the handler READ the settings row on a livery request (' + readIt
         + ' read) -- so the fifth argument is carrying this home\'s real '
         + 'answer and not a default the call site invented');
    } else {
      bad('S1b. the handler did not read the settings row for a '
          + 'settings-sensitive role, so decide() cannot have seen it',
          'settings reads=' + readIt);
    }
    // Still refused, because no per-employee grant exists -- and that is the
    // honest end state of this change rather than a failure.
    if (r.statusCode === 403) {
      ok('S1c. ...and the request is STILL refused, because branch 4 also '
         + 'needs a per-employee grant and api/sd-data.js passes none today. '
         + 'NAMED AS OPEN rather than implied to work: the setting is wired, '
         + 'the grant table is not');
    } else {
      bad('S1c. a livery read of leg_liverybookings must still be refused '
          + 'without a per-employee grant -- if it is allowed, the setting '
          + 'alone widened access and F2\'s "nothing widens by default" is '
          + 'broken', 'status=' + r.statusCode + ' code=' + code(r));
    }
  }
  // NEGATIVE CONTROL: the vendor record is never grantable under EITHER
  // setting. F2's own warning is about exactly this row.
  if (legRoles.liveryGrantable('leg_liveryvendors', 'direct_to_family') === false
      && legRoles.liveryGrantable('leg_liveryvendors', 'through_the_home') === false) {
    ok('S1d. NEGATIVE CONTROL: leg_liveryvendors is grantable under NEITHER '
       + 'setting -- it carries the pricing the invoice is built from, and '
       + 'F2\'s warning names it. So S1 is not "the setting opens things"');
  } else {
    bad('S1d. leg_liveryvendors became grantable -- the setting opened a row '
        + 'it must never open', '');
  }
  // NEGATIVE CONTROL: an unknown stored value falls to the NARROW default,
  // not to the permissive one and not to an error.
  if (legRoles.liveryBilling('not-a-setting') === legRoles.LEG_LIVERY_BILLING_DEFAULT
      && legRoles.liveryGrantable('leg_liverybookings', 'not-a-setting') === false) {
    ok('S1e. NEGATIVE CONTROL: an unknown stored setting falls to the NARROW '
       + 'default, so a typo in the database cannot open a resource');
  } else {
    bad('S1e. an unknown setting value did not fall to the narrow default', '');
  }

  section('S2. F3 -- a countersign list creates a PREPARE route (POLICY)');
  settingsRow = HOME_COUNTERSIGN;
  // THE POLICY HALF. This is what the fifth argument changed and it is the
  // first time decide()'s branch 3 has been reachable with a real home.
  if (legRoles.decide('leg_cremations', 'apprentice',
                      legRoles.LEG_PREPARE_ACTION, null, HOME_COUNTERSIGN)
      === legRoles.ALLOW) {
    ok('S2. with leg_cremations on this home\'s apprentice countersign list, '
       + 'the POLICY ALLOWS the prepare route -- and it DENIES the same call '
       + 'with no home (S0b), so the home is what moves it');
  } else {
    bad('S2. the countersign list did not create a prepare route in the policy',
        'decide=' + legRoles.decide('leg_cremations', 'apprentice',
          legRoles.LEG_PREPARE_ACTION, null, HOME_COUNTERSIGN));
  }
  // NEGATIVE CONTROL: a resource NOT on this home's list gets no prepare.
  if (legRoles.decide('leg_deathrecords', 'apprentice',
                      legRoles.LEG_PREPARE_ACTION, null, HOME_COUNTERSIGN)
      === legRoles.DENY) {
    ok('S2b. NEGATIVE CONTROL: a resource NOT on the list gets no prepare '
       + 'route, so S2 is the LIST working rather than `prepare` being open '
       + 'for apprentices generally');
  } else {
    bad('S2b. an apprentice got a prepare route for a resource this home did '
        + 'not list', '');
  }
  // NEGATIVE CONTROL: the list cannot invent a countersignature route for a
  // resource the platform has no way to countersign.
  {
    const invented = { livery_billing: 'through_the_home',
                       apprentice: { countersign: ['leg_invoices'] } };
    if (legRoles.decide('leg_invoices', 'apprentice',
                        legRoles.LEG_PREPARE_ACTION, null, invented)
        === legRoles.DENY
        && legRoles.LEG_COUNTERSIGN_REQUIRED.leg_invoices !== true) {
      ok('S2d. NEGATIVE CONTROL: a home naming a resource the platform cannot '
         + 'COUNTERSIGN gets no prepare route either -- branch 3 requires '
         + 'LEG_COUNTERSIGN_REQUIRED too, so a home cannot configure a '
         + 'prepare nobody can complete');
    } else {
      bad('S2d. a home invented a prepare route for a resource with no '
          + 'countersignature path', '');
    }
  }
  // NEGATIVE CONTROL: prepare is not a write. The apprentice still cannot file.
  {
    const r = await call('leg_cremations', 'write', 'apprentice');
    if (r.statusCode === 403) {
      ok('S2c. NEGATIVE CONTROL: the same apprentice still cannot WRITE '
         + 'leg_cremations -- preparing is not filing, which is the whole '
         + 'point of F3\'s countersignature lock');
    } else {
      bad('S2c. an apprentice on the countersign list could WRITE the record, '
          + 'so prepare widened into a write grant', 'status=' + r.statusCode);
    }
  }

  section('V. THE SECOND GATE -- `prepare` IS NOT A DECLARED VERB. RECORDED.');
  // ── THE SAME FOUR-GATES SHAPE AS rt_routes, FOUND THE SAME WAY ──────────
  // The fifth argument makes F3's POLICY reachable. It does NOT make the
  // feature usable, and this section says so rather than letting S2's green
  // imply it: `prepare` is not a declared extraAction for ANY leg_ resource,
  // so checkEnvelope() answers 400 before the role gate runs -- and even past
  // that, the LEG_RESOURCES branches dispatch only `read` and `write`, so a
  // prepare would fall through to the handler's unsupported-combination 400.
  //
  // NEITHER HALF IS FIXED HERE AND THE REASON IS A BOUNDARY, NOT AN OVERSIGHT.
  // The declaration is one line in api/_resources/sairnlegacy.js, which is
  // cody's -- but a declared verb with no handler branch asserts a capability
  // that answers 400, which is exactly what fourth's routing document held the
  // rt_routes extraActions line back for. The handler branch is the
  // countersignature flow in api/leg-countersign.js, which is HANK'S and is
  // explicitly out of bounds this batch. So the declaration waits for the
  // branch, as it did for rt_routes, and both are routed together.
  {
    const REG = require(path.join(API_DIR, '_resources/index.js'));
    const withPrepare = Object.keys(REG.EXTRA_ACTIONS).filter(
      (k) => (REG.EXTRA_ACTIONS[k] || []).indexOf(legRoles.LEG_PREPARE_ACTION) !== -1);
    if (withPrepare.length === 0) {
      ok('V1. MEASURED: NO resource anywhere declares the `'
         + legRoles.LEG_PREPARE_ACTION + '` verb, so the dispatcher refuses it '
         + 'before the role gate. The policy is live and the VERB is not -- '
         + 'routed, not claimed working');
    } else {
      bad('V1. some resource now declares `prepare` ('
          + JSON.stringify(withPrepare) + ') -- if that is leg_cremations, '
          + 'this section is stale and the dispatcher arms below should be '
          + 'promoted from "records the 400" to "drives the route"', '');
    }
    settingsRow = HOME_COUNTERSIGN;
    const r = await call('leg_cremations', legRoles.LEG_PREPARE_ACTION,
                         'apprentice');
    if (r.statusCode === 400) {
      ok('V2. ...and the dispatcher really does answer 400 for it (not 403), '
         + 'which is the UNDECLARED-VERB refusal and not a policy refusal. '
         + 'THE FIRST SPELLING OF S2 ASSERTED `!== 403` AND THIS 400 SATISFIED '
         + 'IT -- it would have reported F3 working while every request was '
         + 'refused as an unknown verb');
    } else {
      bad('V2. the dispatcher no longer answers 400 for an undeclared prepare '
          + '-- re-read V1 and re-aim S2 to drive the real route',
          'status=' + r.statusCode + ' code=' + code(r));
    }
  }

  section('H. THE CONDITIONAL READ -- its condition is PROVED, not asserted');
  // api/sd-data.js reads the settings row only for roles the module's policy
  // can actually be affected by, because an unconditional read broke four arms
  // that assert a refused role touches nothing. That list is a COPY of a fact
  // living in the module, so this arm proves the copy is exactly right by
  // driving every role against every resource and both actions with two
  // OPPOSITE homes and requiring the answer to be IDENTICAL for every role
  // NOT on the list. A third settings-sensitive role turns H1 red.
  {
    const SENSITIVE = ['apprentice', 'livery'];
    // `roleSet({...})` AS WELL AS A BARE LITERAL. The first spelling matched
    // only `= {`, and tests/role_maps_have_no_prototype.js then correctly
    // refused the bare literal in api/sd-data.js -- so wrapping it in
    // roleSet() made THIS arm report COULD NOT TELL. Both forms are read now,
    // which is the shape the file can legitimately be in.
    const m = CODE.match(/const LEG_SETTINGS_SENSITIVE_ROLES = (?:roleSet\()?\{([^}]*)\}/);
    const declared = m
      ? m[1].split(',').map((s) => s.split(':')[0].trim()).filter(Boolean)
      : null;
    if (!declared) {
      bad('H0. LEG_SETTINGS_SENSITIVE_ROLES could not be read out of '
          + 'api/sd-data.js, so H1 would be comparing against a list this '
          + 'suite invented. COULD NOT TELL, not a pass', '');
    } else if (declared.slice().sort().join(',') === SENSITIVE.slice().sort().join(',')) {
      ok('H0. the handler\'s LEG_SETTINGS_SENSITIVE_ROLES is exactly '
         + JSON.stringify(declared.slice().sort()) + ', read from its source');
    } else {
      bad('H0. the handler\'s sensitive-role list is '
          + JSON.stringify(declared) + ', not ' + JSON.stringify(SENSITIVE)
          + ' -- update this arm deliberately or the list has drifted', '');
    }
    const roles = ['owner', 'director', 'arranger', 'prep', 'office',
                   'apprentice', 'livery', 'staff'];
    const resources = legRoles.resources();
    const moved = [];
    for (const role of roles) {
      if (SENSITIVE.indexOf(role) !== -1) continue;
      for (const resource of resources) {
        for (const act of ['read', 'write', legRoles.LEG_PREPARE_ACTION]) {
          const a = legRoles.decide(resource, role, act, null, HOME_DIRECT);
          const b = legRoles.decide(resource, role, act, null, HOME_COUNTERSIGN);
          const c = legRoles.decide(resource, role, act, null, null);
          if (a !== b || a !== c) {
            moved.push(role + '/' + resource + '/' + act
                       + ' direct=' + a + ' countersign=' + b + ' none=' + c);
          }
        }
      }
    }
    if (resources.length < 30) {
      bad('H1. only ' + resources.length + ' resources came back from '
          + 'legRoles.resources(), so this sweep would pass vacuously', '');
    } else if (moved.length === 0) {
      ok('H1. NO non-listed role\'s decision changes under two OPPOSITE '
         + 'settings rows, across ' + (roles.length - SENSITIVE.length)
         + ' roles x ' + resources.length + ' resources x 3 actions = '
         + ((roles.length - SENSITIVE.length) * resources.length * 3)
         + ' comparisons. So reading the row only for apprentice and livery '
         + 'cannot change any answer -- the condition is MEASURED, not hoped');
    } else {
      bad('H1. a role NOT on LEG_SETTINGS_SENSITIVE_ROLES has a '
          + 'settings-dependent decision, so the conditional read is skipping '
          + 'a case that matters. ADD THE ROLE TO THE LIST in api/sd-data.js',
          moved.slice(0, 6).join('\n         '));
    }
    // AND THE SWEEP MUST HAVE TEETH: the two LISTED roles must actually move,
    // or H1 is a comparison in which nothing could ever differ.
    const sensitiveMoved = [];
    for (const role of SENSITIVE) {
      for (const resource of resources) {
        for (const act of ['read', 'write', legRoles.LEG_PREPARE_ACTION]) {
          if (legRoles.decide(resource, role, act, null, HOME_DIRECT)
              !== legRoles.decide(resource, role, act, null, HOME_COUNTERSIGN)) {
            sensitiveMoved.push(role + '/' + resource + '/' + act);
          }
        }
      }
    }
    if (sensitiveMoved.length > 0) {
      ok('H2. ...and the two LISTED roles DO move under the same two homes ('
         + sensitiveMoved.length + ' case(s), e.g. ' + sensitiveMoved[0]
         + '), so H1 is a comparison that could have come out the other way');
    } else {
      bad('H2. NEITHER listed role changes decision between the two homes, so '
          + 'H1 proves nothing and the two fixture homes are not actually '
          + 'different', '');
    }
  }

  console.log('\n' + pass + ' passed, ' + failed.length + ' failed');
  if (failed.length) {
    console.log(failed.length + ' ARM(S) FAILED:');
    failed.forEach((f) => console.log('  - ' + f));
    console.log('\nNO ARM HERE IS EXPECTED RED. A P arm means the fifth '
              + 'argument or the settings read was reverted; S0 means the '
              + 'narrow default moved, which would break every home that has '
              + 'never saved settings; an S1/S2 arm is the F2/F3 wiring; and '
              + 'an H arm means the conditional read is skipping a case that '
              + 'matters or is comparing two fixtures that are not different.');
    process.exit(1);
  }
  process.exit(0);
}());
