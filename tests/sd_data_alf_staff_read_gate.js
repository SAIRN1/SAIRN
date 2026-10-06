// tests/sd_data_alf_staff_read_gate.js
//
// REQUIREMENT: `alf_staff` / `read` must not hand a care worker's PERSONAL
//   PHONE NUMBER, BACKGROUND-CHECK DATE or free-text `notes` to a role with no
//   management function. Roles in ALF_CRED_READ_ROLES get the roster unchanged;
//   every other role gets id, name, position and status, and nothing else.
//
// WHY. Until 2026-10-06 the branch (`api/sd-data.js`) verified the session and
// gated on NOTHING ELSE, then returned `Object.assign({ id: r.staff_id },
// r.data)` -- the entire jsonb blob, spread. `sairncare.html` `saveStaff()`
// writes name, phone, position, cert_expiry, bgcheck_date, status and notes;
// `alf_compliance_rules`/`evaluate` adds hire_date. The sairncare role
// vocabulary (`api/_lib/auth.js:238`) is owner, nursing, med_aide, caregiver,
// billing, activities -- so a `caregiver`, a `med_aide` and an `activities`
// role all reached every colleague's phone and screening date.
// `docs/CRITICALITY-TIERS.md` rates this resource A / A.
//
// THE FIX IS A PROJECTION, NOT A REFUSAL, and arm D is what keeps it honest:
// scheduling and coverage genuinely need the roster, so a blanket 403 would
// break the thing the old comment was protecting. Broad roles must still see
// everything.
//
// ── WHAT IS REAL AND WHAT IS NOT, stated because a suite that does not say so
//    invites "N passed" to be read as "it works in production".
//
// REAL: the handler (`api/sd-data.js`, required, not reimplemented), and the
// auth module -- `signSessionToken` mints and the handler's own
// `verifySessionToken` checks signature, typ, role-in-app, expiry AND the
// licence binding. Tokens are signed against the SAME `license_hash` the
// stubbed licence returns, which is the trap sairn-api-tester section 2 records.
//
// MOCKED: `fetch` and `validateLicenseKey`. NOT RUN: the live round trip. This
// file is a SUBSTITUTE for that, not a replacement.
//
// MUTATION PROOF: run this file against the parent of the fix commit. Expected
// RED on every B and C arm, and on D's scoped_projection half.
//
// Run:  node tests/sd_data_alf_staff_read_gate.js

'use strict';
const path = require('path');
const ROOT = path.join(__dirname, '..');

const LICENCE = require.resolve(path.join(ROOT, 'api/_lib/license.js'));
const LIC_HASH = 'hash-of-the-alf-staff-test-licence';
require.cache[LICENCE] = {
  id: LICENCE, filename: LICENCE, loaded: true,
  exports: {
    validateLicenseKey: async () => ({
      valid: true, active: true, license_hash: LIC_HASH,
      stripe_subscription_id: 'sub_1', trial_ends_at: null, app_id: 'sairncare'
    }),
    hashLicense: () => LIC_HASH,
  },
};

process.env.SUPABASE_URL = 'https://example.invalid';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'service-role-for-the-test';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || 'alf-staff-read-gate-test-secret';
const { signSessionToken } = require(path.join(ROOT, 'api/_lib/auth.js'));

// ── THE FIXTURE. Two staff. Every sensitive field carries a DISTINCTIVE value
//    so the leak test can look for it anywhere in the response rather than
//    only in the list -- a filtered list with the same data echoed on a
//    summary key would pass the narrower assertion and still be the defect.
const STAFF = [
  { staff_id: 'S1', data: { name: 'Dana Reyes', position: 'med_aide',
                            phone: '555-0101-DANA', cert_expiry: '2027-03-01',
                            bgcheck_date: '2024-02-02', status: 'active',
                            notes: 'NOTE-ABOUT-DANA' } },
  { staff_id: 'S2', data: { name: 'Marcus Webb', position: 'nursing',
                            phone: '555-0202-MARCUS', cert_expiry: '2027-09-09',
                            bgcheck_date: '2023-06-01', status: 'active',
                            notes: 'NOTE-ABOUT-MARCUS', hire_date: '2023-06-01' } },
];
const SENSITIVE = ['555-0101-DANA', '555-0202-MARCUS', '2024-02-02',
                   '2023-06-01', 'NOTE-ABOUT-DANA', 'NOTE-ABOUT-MARCUS',
                   '2027-03-01', '2027-09-09'];

let asked = [];
global.fetch = async (url) => {
  const u = String(url);
  asked.push(u);
  const ok = (rows) => ({ ok: true, status: 200, json: async () => rows });
  if (/alf_staff\?/.test(u)) return ok(STAFF);
  if (/_employee_auth\?/.test(u)) return ok([{ active: true }]);
  throw new Error('Unmocked fetch: ' + u);
};

delete require.cache[require.resolve(path.join(ROOT, 'api/sd-data.js'))];
const handler = require(path.join(ROOT, 'api/sd-data.js'));

function fakeRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}

// ROLE IS A PARAMETER, NOT AN INVISIBLE CONSTANT. `role === null` means no
// session at all, which is its own arm.
async function read(role, employeeId) {
  asked = [];
  const headers = { authorization: 'Bearer ALF-STAFF-TEST-KEY' };
  if (role !== null) {
    headers['x-sd-auth'] = signSessionToken({
      app: 'sairncare', employee_id: employeeId || 'EMP-X', role: role,
      license_hash: LIC_HASH });
  }
  const req = { method: 'POST', headers: headers, body: {
    action: 'read', resource: 'alf_staff', payload: {} } };
  const res = fakeRes();
  await handler(req, res);
  return res;
}

function leaks(res) {
  const s = JSON.stringify(res.body || {});
  return SENSITIVE.filter((v) => s.indexOf(v) !== -1);
}
function keysOf(res) {
  const rows = (res.body && res.body.data) || [];
  const k = {};
  rows.forEach((r) => Object.keys(r).forEach((x) => { k[x] = true; }));
  return Object.keys(k).sort();
}

let pass = 0, fail = 0;
function ok(l) { pass++; console.log('  ok   ' + l); }
function bad(l, why) {
  fail++;
  console.log('  FAIL ' + l);
  if (why) console.log('       ' + String(why).slice(0, 400));
}

(async function main() {
  console.log('ALF_STAFF / READ -- ROLE GATE -- criteria 2026-10-06.1\n');

  console.log('A. NO SESSION');
  let r = await read(null, null);
  if (r.statusCode === 401 && r.body && r.body.error
      && r.body.error.code === 'NO_SESSION') {
    ok('A1. no session is 401 NO_SESSION');
  } else {
    bad('A1. no session must be 401 NO_SESSION',
        'status=' + r.statusCode + ' body=' + JSON.stringify(r.body));
  }
  if (!asked.some((u) => /alf_staff\?/.test(u))) {
    ok('A2. ...and the roster was NEVER READ -- no alf_staff request was '
       + 'issued at all, so the refusal is not a projection of a query that '
       + 'already ran');
  } else {
    bad('A2. an unauthenticated call must not read the roster', asked.join(' | '));
  }

  console.log('\nB. NARROW ROLES: the projection, and NO sensitive value anywhere in the body');
  for (const role of ['med_aide', 'caregiver', 'activities']) {
    r = await read(role, 'S1');
    const got = keysOf(r);
    const lk = leaks(r);
    const want = ['id', 'name', 'position', 'status'].join(',');
    if (r.statusCode === 200 && got.join(',') === want && lk.length === 0) {
      ok('B. ' + role + ' gets EXACTLY id,name,position,status -- and not one '
         + 'of the eight sensitive fixture values appears ANYWHERE in the '
         + 'response, which is the leak test rather than the list test');
    } else {
      bad('B. ' + role + ' must get the projection and leak nothing',
          'status=' + r.statusCode + ' keys=' + got.join(',')
          + ' leaked=' + JSON.stringify(lk));
    }
    if (r.body && r.body.scoped_projection === true) {
      ok('B. ...and ' + role + ' is TOLD -- scoped_projection:true, so a '
         + 'reduced roster cannot be read as the full one');
    } else {
      bad('B. ' + role + ' must be told the view is projected',
          'scoped_projection=' + JSON.stringify(r.body && r.body.scoped_projection));
    }
  }

  console.log('\nC. THE WHOLE ROSTER IS STILL RETURNED -- the fix is a projection, not a filter');
  r = await read('caregiver', 'S1');
  const ids = (((r.body || {}).data) || []).map((x) => x.id).sort();
  if (ids.length === 2 && ids[0] === 'S1' && ids[1] === 'S2') {
    ok('C1. a narrow role still sees BOTH staff by id, name and position. '
       + 'Coverage planning is what the old open comment was protecting and it '
       + 'still works -- the fields went, the roster did not');
  } else {
    bad('C1. the narrow projection must still list every staff member',
        'ids=' + JSON.stringify(ids));
  }

  console.log('\nD. BROAD ROLES see everything -- without this the fix could project for ALL');
  for (const role of ['owner', 'billing', 'nursing']) {
    r = await read(role, 'S2');
    const got = keysOf(r);
    const hasPhone = got.indexOf('phone') !== -1;
    const hasBg = got.indexOf('bgcheck_date') !== -1;
    if (r.statusCode === 200 && hasPhone && hasBg
        && r.body.scoped_projection === false) {
      ok('D. ' + role + ' still gets phone and bgcheck_date, and '
         + 'scoped_projection:false. WITHOUT THESE THREE ARMS the fix could '
         + 'project for every role and every arm in B would still pass');
    } else {
      bad('D. ' + role + ' is in ALF_CRED_READ_ROLES and must see the blob',
          'status=' + r.statusCode + ' keys=' + got.join(',')
          + ' scoped=' + JSON.stringify(r.body && r.body.scoped_projection));
    }
  }

  console.log('\nE. THE FLAG IS SERVER-STAMPED, not caller-supplied');
  asked = [];
  {
    const headers = { authorization: 'Bearer ALF-STAFF-TEST-KEY',
      'x-sd-auth': signSessionToken({ app: 'sairncare', employee_id: 'S1',
        role: 'caregiver', license_hash: LIC_HASH }) };
    const req = { method: 'POST', headers: headers, body: {
      action: 'read', resource: 'alf_staff',
      payload: { scoped_projection: false } } };
    const res = fakeRes();
    await handler(req, res);
    if (res.body && res.body.scoped_projection === true
        && keysOf(res).indexOf('phone') === -1) {
      ok('E1. a caller sending scoped_projection:false is IGNORED -- the '
         + 'server value wins and the projection still happened');
    } else {
      bad('E1. the caller must not be able to set scoped_projection',
          'scoped=' + JSON.stringify(res.body && res.body.scoped_projection)
          + ' keys=' + keysOf(res).join(','));
    }
  }

  console.log('\nF. THE UNPROVISIONED ANSWER CARRIES THE FLAG TOO');
  {
    const saved = global.fetch;
    global.fetch = async (url) => {
      const u = String(url);
      if (/alf_staff\?/.test(u)) return { ok: false, status: 404, json: async () => ({}) };
      if (/_employee_auth\?/.test(u)) return { ok: true, status: 200, json: async () => [{ active: true }] };
      throw new Error('Unmocked fetch: ' + u);
    };
    r = await read('caregiver', 'S1');
    global.fetch = saved;
    if (r.statusCode === 200 && r.body && r.body.provisioned === false
        && r.body.scoped_projection === true) {
      ok('F1. the not-provisioned 200 says provisioned:false AND '
         + 'scoped_projection:true. A flag missing from one branch is a flag '
         + 'the client has to infer from its absence, which is how the three '
         + 'honest empty states collapse into one');
    } else {
      bad('F1. the unprovisioned response must carry scoped_projection',
          'status=' + r.statusCode + ' body=' + JSON.stringify(r.body));
    }
  }

  console.log('\nG. PINNED AT SOURCE -- the SIBLING\'S set, not a new one');
  const fs = require('fs');
  const SRC = fs.readFileSync(path.join(ROOT, 'api/sd-data.js'), 'utf8');
  const CODE = SRC.split(/\r?\n/)
    .filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');
  const DECL = 'const ALF_CRED_READ_ROLES = roleSet(';
  const n = CODE.split(DECL).length - 1;
  if (n === 1) {
    ok('G1. ALF_CRED_READ_ROLES is declared EXACTLY ONCE in the handler. Two '
       + 'declarations with the same contents would be two things to drift, '
       + 'and a gate that disagrees with its sibling about one table is the '
       + '#894 defect this reuses the set to avoid');
  } else {
    bad('G1. the role set must be declared exactly once -- found ' + n, '');
  }
  const ANCHOR = "if (resource === 'alf_staff' && action === 'read')";
  const m = CODE.split(ANCHOR).length - 1;
  if (m !== 1) {
    bad('G2. the source anchor must match EXACTLY ONCE -- it matched ' + m
        + ' time(s), so G3 cannot say which block it measured and is NOT run', '');
  } else {
    ok('G2. the read anchor matches exactly once');
    const block = CODE.split(ANCHOR)[1].split(/\n {4}if \(/)[0];
    if (/ALF_CRED_READ_ROLES\[session\.role\]/.test(block)) {
      ok('G3. the branch consults ALF_CRED_READ_ROLES -- the set '
         + 'alf_staff_credentials/read and alf_compliance_rules/evaluate '
         + 'already use for the same people');
    } else {
      bad('G3. the branch must consult the sibling set', '');
    }
    if (!/Object\.assign\(\{ id: r\.staff_id \}, d\)[\s\S]*?Object\.assign\(\{ id: r\.staff_id \}, d\)/.test(block)) {
      ok('G4. the narrow shape is CONSTRUCTED from named fields rather than '
         + 'deleted from the blob, so a field added to alf_staff later is '
         + 'excluded by default instead of disclosed until somebody notices');
    } else {
      bad('G4. the narrow shape must not be built by spreading the blob', '');
    }
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
