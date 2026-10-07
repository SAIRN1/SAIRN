// tests/sd_data_grd_session_gate.js
//
// REQUIREMENT: every SAIRNgrounds resource in `api/sd-data.js` requires a real
//   employee session. The licence key alone must reach NONE of them, on read or
//   on write, and the refusal must happen BEFORE any table is touched.
//
// WHY. SAIRNgrounds has had a per-employee auth system the whole time --
// `api/grd-auth.js`, the `grd_employee_auth` table (`api/_lib/auth.js:1048`)
// and a five-role vocabulary (`:128`: owner, superintendent, manager, crew,
// office). None of these branches used it. Anybody holding the licence key
// could list a course's properties, jobs, invoices, vendor list and
// bill-of-quantity rates and WRITE to all of them, with no employee identity
// involved at all.
//
// MEASURED BY THE AUDITOR, NOT BY ME:
// `.claude/skills/sairn-hover-auditor/tools-hover2/grd_session_gate_repro.py
// --all` reported REPRODUCES on 16 of the 17 `grd_*` resources, read and write.
// The seventeenth, grd_progress_photos, was PARTIAL. That tree is the
// auditor's and is READ ONLY to this session -- it was RUN, not edited, and
// the finding stays OPEN for its finder to close.
//
// ── WHY THIS FILE EXISTS WHEN THE AUDITOR ALREADY HAS A PROBE ─────────────
// The probe asks whether `verifySessionToken` appears INSIDE each resource's
// dispatch block. The fix is ONE SHARED PRELUDE covering all 21 resources --
// which `tools/gate_parity_check.py` calls "the single most common correct
// shape on this platform". A lexical inside-the-block test cannot see it, so
// the probe still reports REPRODUCES at the fixed tree. That blind spot is
// ROUTED BACK to hover2 with this file as the reproducing artifact; this suite
// DRIVES the handler instead of reading it, which is the only way to tell a
// prelude gate from no gate.
//
// REAL: the handler and the auth module. MOCKED: fetch, validateLicenseKey.
// NOT RUN: the live round trip.
//
// MUTATION PROOF: against the parent commit every arm in A and C goes red.
//
// Run:  node tests/sd_data_grd_session_gate.js

'use strict';
const path = require('path');
const ROOT = path.join(__dirname, '..');

const LICENCE = require.resolve(path.join(ROOT, 'api/_lib/license.js'));
const LIC_HASH = 'hash-of-the-grd-session-gate-licence';
require.cache[LICENCE] = {
  id: LICENCE, filename: LICENCE, loaded: true,
  exports: {
    validateLicenseKey: async () => ({
      valid: true, active: true, license_hash: LIC_HASH,
      stripe_subscription_id: 'sub_1', trial_ends_at: null, app_id: 'sairngrounds'
    }),
    hashLicense: () => LIC_HASH,
  },
};

process.env.SUPABASE_URL = 'https://example.invalid';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'service-role-for-the-test';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || 'grd-session-gate-test-secret';
const { signSessionToken } = require(path.join(ROOT, 'api/_lib/auth.js'));

// The 21 resources the prelude covers: 17 grd_* plus the four bare names that
// map to grd_* tables. LISTED HERE rather than derived from the handler, on
// purpose: a test that reads its own expected set out of the subject cannot see
// the subject lose a member. Arm E reconciles this list against the source.
const GRD = [
  'properties', 'jobs', 'quotes', 'golf_zones',
  'grd_schedule', 'grd_progress_photos', 'grd_invoices', 'grd_dreamclose',
  'grd_invasive_sightings', 'grd_ecosystem_reports', 'grd_rounds',
  'grd_cart_orders', 'grd_designs', 'grd_irr_controllers', 'grd_irr_zones',
  'grd_irr_schedules', 'grd_water_features', 'grd_training_courses',
  'grd_training_completions', 'grd_boq_rates', 'grd_vendors',
];

let asked = [];
global.fetch = async (url, opts) => {
  const u = String(url);
  asked.push(((opts && opts.method) || 'GET') + ' ' + u);
  const ok = (rows) => ({ ok: true, status: 200, json: async () => rows });
  if (/_employee_auth\?/.test(u)) return ok([{ active: true }]);
  // Every grd_/msb_ table answers with one harmless row so a 200 means the
  // branch RAN rather than that the table was missing.
  return ok([{ data: { id: 'X1' }, property_id: 'P1', schedule_id: 'S1' }]);
};

delete require.cache[require.resolve(path.join(ROOT, 'api/sd-data.js'))];
const handler = require(path.join(ROOT, 'api/sd-data.js'));

function fakeRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}

// `app` is a PARAMETER, not a constant: a session signed for a different app
// must not satisfy this gate, and that is its own arm.
async function call(resource, action, opts) {
  const o = opts || {};
  asked = [];
  const headers = { authorization: 'Bearer GRD-TEST-KEY' };
  if (o.app) {
    headers['x-sd-auth'] = signSessionToken({
      app: o.app, employee_id: 'EMP-1', role: o.role || 'owner',
      license_hash: LIC_HASH });
  }
  const payload = { id: 'X1', property_id: 'P1', schedule_id: 'S1' };
  const req = { method: 'POST', headers: headers, body: {
    action: action, resource: resource, payload: payload } };
  const res = fakeRes();
  await handler(req, res);
  return res;
}

const touchedTable = () =>
  asked.some((q) => /\b(grd_|msb_)/.test(q));

let pass = 0, fail = 0;
function ok(l) { pass++; console.log('  ok   ' + l); }
function bad(l, why) {
  fail++;
  console.log('  FAIL ' + l);
  if (why) console.log('       ' + String(why).slice(0, 300));
}

(async function main() {
  console.log('SAIRNGROUNDS SESSION GATE -- criteria 2026-10-07.1\n');

  console.log('A. NO SESSION -- 401 on all ' + GRD.length
    + ' resources, read AND write, and NOTHING touched');
  let refused = 0, leakedRead = [];
  for (const resource of GRD) {
    for (const action of ['read', 'write']) {
      const r = await call(resource, action, {});
      const is401 = r.statusCode === 401 && r.body && r.body.error
        && r.body.error.code === 'NO_SESSION';
      if (!is401) { leakedRead.push(resource + '/' + action + '=' + r.statusCode); continue; }
      if (touchedTable()) {
        leakedRead.push(resource + '/' + action + '=401-but-read: ' + asked.join('|'));
        continue;
      }
      refused++;
    }
  }
  if (refused === GRD.length * 2) {
    ok('A1. all ' + (GRD.length * 2) + ' resource/action pairs refuse 401 '
       + 'NO_SESSION -- and NONE of them issued a single grd_ or msb_ request, '
       + 'so the refusal is not a filtered answer to a query that already ran');
  } else {
    bad('A1. every pair must refuse 401 and touch nothing -- '
        + refused + ' of ' + (GRD.length * 2) + ' did',
        leakedRead.slice(0, 6).join('  |  '));
  }

  console.log('\nB. WITH A REAL SAIRNGROUNDS SESSION the resources still work');
  let worked = 0, broke = [];
  for (const resource of GRD) {
    const r = await call(resource, 'read', { app: 'sairngrounds', role: 'owner' });
    if (r.statusCode === 200) worked++;
    else broke.push(resource + '=' + r.statusCode);
  }
  if (worked === GRD.length) {
    ok('B1. all ' + GRD.length + ' reads return 200 with a real session. '
       + 'WITHOUT THIS ARM the gate could refuse everybody and every arm in A '
       + 'would still pass -- which is the same reason #894 needed its D arms');
  } else {
    bad('B1. every resource must still work for a signed-in employee -- '
        + worked + ' of ' + GRD.length, broke.slice(0, 6).join(', '));
  }

  console.log('\nC. A SESSION FOR ANOTHER APP DOES NOT COUNT');
  let crossRefused = 0, crossLeak = [];
  for (const resource of GRD) {
    const r = await call(resource, 'read', { app: 'sairncare', role: 'owner' });
    if (r.statusCode === 401) crossRefused++;
    else crossLeak.push(resource + '=' + r.statusCode);
  }
  if (crossRefused === GRD.length) {
    ok('C1. a token signed for `sairncare` on the SAME licence is refused on '
       + 'all ' + GRD.length + '. The app binding is checked, so a session '
       + 'from one vertical cannot read another\'s course data');
  } else {
    bad('C1. a cross-app session must not satisfy this gate -- '
        + crossRefused + ' of ' + GRD.length, crossLeak.slice(0, 6).join(', '));
  }

  console.log('\nD. THE EXCLUSION IS PROVEN, NOT ASSUMED -- msb_* is untouched');
  {
    const r = await call('msb_products', 'read', {});
    if (r.statusCode === 200) {
      ok('D1. `msb_products` still answers WITHOUT a session, exactly as before '
         + 'this change. That is NOT an endorsement -- it is a different app, '
         + 'not in this finding and not in this claim, and it is logged as open. '
         + 'The arm exists so the prelude is proven not to have silently '
         + 'widened or narrowed a neighbouring app sharing this region');
    } else {
      bad('D1. msb_products must be unchanged by this prelude',
          'status=' + r.statusCode + ' -- the prelude has caught a resource '
          + 'outside its named set');
    }
  }

  console.log('\nE. PINNED AT SOURCE -- the set, and the prototype trap');
  const fs = require('fs');
  const SRC = fs.readFileSync(path.join(ROOT, 'api/sd-data.js'), 'utf8');
  const CODE = SRC.split(/\r?\n/)
    .filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');
  const DECL = 'const GRD_SESSION_RESOURCES = {';
  if (CODE.split(DECL).length - 1 !== 1) {
    bad('E0. GRD_SESSION_RESOURCES must be declared exactly once -- found '
        + (CODE.split(DECL).length - 1) + ', so E1 cannot say which it '
        + 'measured and is NOT run', '');
  } else {
    ok('E0. the set is declared exactly once');
    const lit = CODE.split(DECL)[1].split('}')[0];
    const names = (lit.match(/([A-Za-z_][A-Za-z0-9_]*)\s*:\s*true/g) || [])
      .map((s) => s.split(':')[0].trim()).sort();
    const want = GRD.slice().sort();
    if (names.join(',') === want.join(',')) {
      ok('E1. the source set is EXACTLY the ' + GRD.length + ' resources this '
         + 'file names -- set EQUALITY, not a count, so it fails on an '
         + 'unapproved addition AND on a silent removal');
    } else {
      bad('E1. the source set must equal this file\'s list',
          'only in source: ' + names.filter((x) => want.indexOf(x) === -1).join(',')
          + ' | only here: ' + want.filter((x) => names.indexOf(x) === -1).join(','));
    }
    if (/hasOwnProperty\.call\(GRD_SESSION_RESOURCES, resource\)/.test(CODE)) {
      ok('E2. membership is tested with hasOwnProperty, not `SET[resource]`. '
         + 'A bare object literal inherits from Object.prototype, so '
         + '`[\'constructor\']` is truthy on it -- api/rf-auth.js:96 records '
         + 'that exact trap for a role set');
    } else {
      bad('E2. membership must not be a bare property read', '');
    }
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
