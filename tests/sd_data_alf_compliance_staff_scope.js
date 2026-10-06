// tests/sd_data_alf_compliance_staff_scope.js
//
// REQUIREMENT: `alf_compliance_rules` / `evaluate` with `include_staff:true`
//   must disclose the staff roster on the SAME terms as
//   `alf_staff_credentials` / `read` -- the resource it reads its records from.
//   A role outside ALF_CRED_READ_ROLES sees ITS OWN row and nothing else.
//
// WHY, AND IT IS #894. Until 2026-10-06 this action gated on
// `verifySessionToken` and nothing else (api/sd-data.js:11949). With
// `include_staff:true` it assembled, per staff member, a `name`, a `position`, a
// `hire_date` and the FULL training-hours array, and returned the lot. Any
// authenticated sairncare employee -- a `med_aide`, an `activities` role, a
// `caregiver` with no resident assigned at all -- could ask for it and receive
// the employment and training record of every person on the licence.
//
// THE SIBLING THAT READS THE SAME TABLE ALREADY REFUSED THAT. `:12088`-`:12098`
// filters every role outside ALF_CRED_READ_ROLES to its own `staff_id`, with the
// comment *"enough to know what training they personally owe, without exposing
// the roster's qualifications"*. This branch read the same
// `alf_staff_credentials` rows and did not. The two gates disagreed about one
// table.
//
// ── WHAT IS REAL HERE AND WHAT IS NOT, stated because a suite that does not
//    say so invites "9 passed" to be read as "it works in production".
//
// REAL: the handler (`api/sd-data.js`, required, not reimplemented). The auth
// module is NOT stubbed -- `signSessionToken` mints tokens and the handler's own
// `verifySessionToken` checks the signature, the `typ`, the role-in-app, the
// expiry AND the licence binding. The tokens are signed against the SAME
// `license_hash` the stubbed licence returns, which is the trap sairn-api-tester
// §2 records: a token signed against the wrong hash verifies in isolation and is
// rejected by the handler with an indistinguishable NO_SESSION.
//
// MOCKED: `fetch` (so no Supabase), and `validateLicenseKey` (so no licence
// store). NOT RUN: the live round trip against the deployed URL. This file is a
// SUBSTITUTE for that, not a replacement.
//
// Run:  node tests/sd_data_alf_compliance_staff_scope.js

'use strict';
const assert = require('assert');
const path = require('path');
const ROOT = path.join(__dirname, '..');

// ── The licence, stubbed BEFORE the handler is required, and the hash it
//    returns is the one the tokens are signed with. Not borrowed from a row.
const LICENCE = require.resolve(path.join(ROOT, 'api/_lib/license.js'));
const LIC_HASH = 'hash-of-the-alf-test-licence';
require.cache[LICENCE] = {
  id: LICENCE, filename: LICENCE, loaded: true,
  exports: {
    validateLicenseKey: async () => ({
      valid: true, active: true, license_hash: LIC_HASH,
      stripe_subscription_id: 'sub_1', trial_ends_at: null, app_id: 'sairncare'
    }),
    hashLicense: (k) => LIC_HASH,
  },
};

process.env.SUPABASE_URL = 'https://example.invalid';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'service-role-for-the-test';
// REAL tokens, REAL verification. Set before the handler is required, because
// signer and verifier both read this at call time and an unset secret makes
// every session silently unverifiable.
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || 'alf-compliance-staff-scope-test-secret';
const { signSessionToken } = require(path.join(ROOT, 'api/_lib/auth.js'));

// ── THE FIXTURE. Two staff, each with a distinguishable training record. The
//    whole question is whether a narrow caller identified as S1 can see S2.
const RULES = [{
  rule_id: 'R-1', state: 'OH', requirement_type: 'training',
  facility_class: null, effective_from: '2020-01-01', effective_to: null,
  status: 'active', verified_by: 'test',
  data: { who: 'all_staff', hours: 8, period_months: 12, citation: 'TEST 1' }
}];
const STAFF = [
  { staff_id: 'S1', data: { name: 'Dana Reyes', position: 'med_aide',
                            hire_date: '2024-01-15' } },
  { staff_id: 'S2', data: { name: 'Marcus Webb', position: 'nursing',
                            hire_date: '2023-06-01' } },
];
const CREDS = [
  { staff_id: 'S1', data: { hours: 4, category: 'in-service',
                            completed_on: '2026-03-01' } },
  { staff_id: 'S2', data: { hours: 9, category: 'in-service',
                            completed_on: '2026-04-01' } },
];

// Every outbound request is recorded, so an arm can assert what the handler
// ASKED FOR and not only what it answered -- sairn-api-tester §7.
let asked = [];
global.fetch = async (url, opts) => {
  const u = String(url);
  asked.push(u);
  const ok = (rows) => ({ ok: true, status: 200, json: async () => rows });
  if (/alf_compliance_rules\?/.test(u)) return ok(RULES);
  if (/alf_staff_credentials\?/.test(u)) return ok(CREDS);
  if (/alf_staff\?/.test(u)) return ok(STAFF);
  if (/_employee_auth\?/.test(u)) return ok([{ active: true }]);
  throw new Error('Unmocked fetch: ' + ((opts && opts.method) || 'GET') + ' ' + u);
};

delete require.cache[require.resolve(path.join(ROOT, 'api/sd-data.js'))];
const handler = require(path.join(ROOT, 'api/sd-data.js'));

function fakeRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}

// ROLE IS A PARAMETER, NOT AN INVISIBLE CONSTANT -- sairn-api-tester §3.
// `role === null` means NO SESSION AT ALL, which is its own arm.
async function evaluate(role, employeeId, extra) {
  asked = [];
  const headers = { authorization: 'Bearer ALF-TEST-KEY' };
  if (role !== null) {
    headers['x-sd-auth'] = signSessionToken({
      app: 'sairncare', employee_id: employeeId, role: role,
      license_hash: LIC_HASH });
  }
  const req = { method: 'POST', headers: headers, body: {
    action: 'evaluate', resource: 'alf_compliance_rules',
    payload: Object.assign({ state: 'OH', requirement_type: 'training',
                             include_staff: true }, extra || {}) } };
  const res = fakeRes();
  await handler(req, res);
  return res;
}

// `staff_findings`, NOT `staff`, AND I ASSERTED THE WRONG KEY FIRST. The first
// run of this file reported every arm's list as empty -- including `owner`'s --
// because `evaluateTraining()` returns the per-person results under
// `staff_findings` and I had assumed `staff`, the name of the INPUT. Seven arms
// failed and three passed, and the three that passed were the ones that only
// checked a flag. Read off the engine rather than guessed: the keys are
// ok, state, rule_id, structure, state_mandated, label, requirements, authority,
// staff_findings -- and `staff_findings` carries `staff_id`, `name` and
// `position`, which is where the disclosure actually is.
//
// A SUITE ASSERTING A KEY NOBODY READ FROM THE CODE would have reported "scoped
// to self" for every role, including the broad ones, and that reads as a PASS
// of the narrow arms. It failed loudly here only because arm D asserts the
// ALLOWED side as well.
function staffIds(res) {
  const s = (res.body && res.body.staff_findings) || [];
  return s.map((x) => String(x.staff_id)).sort();
}
// THE REAL LEAK TEST: not "is S2 missing from .staff" but "does S2 appear
// ANYWHERE in the response". A filtered list with the same data echoed on a
// summary key would pass the narrower assertion and still be the defect.
function bodyMentions(res, needle) {
  return JSON.stringify(res.body || {}).indexOf(needle) !== -1;
}

let pass = 0, fail = 0;
function ok(l) { pass++; console.log('  ok   ' + l); }
function bad(l, why) {
  fail++;
  console.log('  FAIL ' + l);
  if (why) console.log('       ' + String(why).slice(0, 400));
}

(async function main() {
  console.log('ALF COMPLIANCE EVALUATE -- STAFF SCOPE -- criteria 2026-10-06.1\n');

  console.log('A. NO SESSION');
  let r = await evaluate(null, null);
  if (r.statusCode === 401 && r.body && r.body.error
      && r.body.error.code === 'NO_SESSION') {
    ok('A1. no session is 401 NO_SESSION');
  } else {
    bad('A1. no session must be 401 NO_SESSION',
        'status=' + r.statusCode + ' body=' + JSON.stringify(r.body));
  }
  if (!asked.some((u) => /alf_staff/.test(u))) {
    ok('A2. ...and NOTHING was read -- no alf_staff and no '
       + 'alf_staff_credentials request was issued at all, so the refusal is '
       + 'not a filtered answer to a query that already ran');
  } else {
    bad('A2. an unauthenticated call must not read the roster', asked.join(' | '));
  }

  console.log('\nB. NARROW ROLES: scoped to self, and S2 absent from the WHOLE body');
  const narrow = [['med_aide', 'S1'], ['activities', 'S1'], ['caregiver', 'S1']];
  for (const [role, emp] of narrow) {
    r = await evaluate(role, emp);
    const ids = staffIds(r);
    const leaks = bodyMentions(r, 'Marcus Webb') || bodyMentions(r, 'S2')
      || bodyMentions(r, '2023-06-01');
    if (r.statusCode === 200 && ids.length === 1 && ids[0] === 'S1' && !leaks) {
      ok('B. ' + role + ' sees ONLY S1 -- and "Marcus Webb", "S2" and his hire '
         + 'date appear NOWHERE in the response, which is the leak test rather '
         + 'than the list test');
    } else {
      bad('B. ' + role + ' must be scoped to its own staff_id',
          'status=' + r.statusCode + ' ids=' + JSON.stringify(ids)
          + ' leaks=' + leaks);
    }
    if (r.body && r.body.scoped_to_self === true) {
      ok('B. ...and ' + role + ' is told so -- scoped_to_self:true, so a '
         + 'self-view cannot be read as a facility view');
    } else {
      bad('B. ' + role + ' must be told the view is scoped',
          'scoped_to_self=' + JSON.stringify(r.body && r.body.scoped_to_self));
    }
  }

  console.log('\nC. A NARROW CALLER WITH NO RECORD gets a truthful empty, not a refusal');
  r = await evaluate('med_aide', 'S-NOBODY');
  if (r.statusCode === 200 && staffIds(r).length === 0
      && r.body.scoped_to_self === true) {
    ok('C1. a caller with no roster row gets 200 and an EMPTY staff list. '
       + '"You have no training record" is a true answer to "what do I owe"; '
       + 'a 403 here would be a refusal of a question it is entitled to ask');
  } else {
    bad('C1. an unmatched narrow caller must get an empty 200',
        'status=' + r.statusCode + ' ids=' + JSON.stringify(staffIds(r)));
  }

  console.log('\nD. BROAD ROLES still see everything -- the fix is not "deny everything"');
  for (const role of ['owner', 'billing', 'nursing']) {
    r = await evaluate(role, 'S2');
    const ids = staffIds(r);
    if (r.statusCode === 200 && ids.length === 2
        && r.body.scoped_to_self === false) {
      ok('D. ' + role + ' sees BOTH staff and scoped_to_self:false. WITHOUT '
         + 'THESE THREE ARMS the fix could refuse the roster to everybody and '
         + 'every arm in B would still pass');
    } else {
      bad('D. ' + role + ' is in ALF_CRED_READ_ROLES and must see the roster',
          'status=' + r.statusCode + ' ids=' + JSON.stringify(ids)
          + ' scoped=' + JSON.stringify(r.body && r.body.scoped_to_self));
    }
  }

  console.log('\nE. THE FLAG IS SERVER-STAMPED, not caller-supplied');
  r = await evaluate('med_aide', 'S1', { scoped_to_self: false });
  if (r.body && r.body.scoped_to_self === true && staffIds(r).length === 1) {
    ok('E1. a caller sending scoped_to_self:false is IGNORED -- the server '
       + 'value wins and the scoping still happened. A flag a caller can set '
       + 'is a flag that describes the request rather than the answer');
  } else {
    bad('E1. the caller must not be able to set scoped_to_self',
        'scoped=' + JSON.stringify(r.body && r.body.scoped_to_self)
        + ' ids=' + JSON.stringify(staffIds(r)));
  }

  console.log('\nF. THE FLAG IS ON EVERY RESPONSE, not only the narrow one');
  r = await evaluate('med_aide', 'S1', { include_staff: false });
  if (r.statusCode === 200 && r.body && r.body.scoped_to_self === true) {
    ok('F1. a narrow caller that did NOT ask for staff is still told '
       + 'scoped_to_self:true. A flag present only in the narrow case is one '
       + 'the client has to infer from its absence');
  } else {
    bad('F1. the flag must appear on every response from this action',
        'status=' + r.statusCode + ' body=' + JSON.stringify(r.body).slice(0, 200));
  }

  console.log('\nG. PINNED AT SOURCE -- the same set and the same predicate as the sibling');
  const fs = require('fs');
  const SRC = fs.readFileSync(path.join(ROOT, 'api/sd-data.js'), 'utf8');
  const CODE = SRC.split(/\r?\n/)
    .filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');
  const ANCHOR = "if (resource === 'alf_compliance_rules' && action === 'evaluate')";
  const n = CODE.split(ANCHOR).length - 1;
  if (n !== 1) {
    bad('G0. the source anchor must match EXACTLY ONCE -- it matched ' + n
        + ' time(s), so G1 cannot say which block it measured and is NOT run');
  } else {
    ok('G0. the source anchor matches exactly once');
    const block = CODE.split(ANCHOR)[1].split(/\n {4}if \(/)[0];
    if (/ALF_CRED_READ_ROLES\[session\.role\]/.test(block)
        && /staff_id\) === String\(session\.employee_id\)/.test(block)) {
      ok('G1. the branch consults ALF_CRED_READ_ROLES -- the sibling\'s set, '
         + 'not a new one -- and filters on session.employee_id. A gate that '
         + 'invented its own set would disagree with its sibling about one '
         + 'table, which is the defect being closed');
    } else {
      bad('G1. the filter must reuse the sibling set and predicate', '');
    }
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
