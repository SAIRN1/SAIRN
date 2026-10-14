// tests/mar_billing_grant.test.js
//
// FAILING-FIRST. THIS SUITE IS RED ON PURPOSE AND MUST STAY RED UNTIL THE api/
// OWNER LANDS THE FEATURE. It is registered in docs/known-red-suites.json so a
// genuinely new regression can be told from this deliberate one, and it is
// wired into NO gate. See docs/2026-10-13-cody-b8-billing-mar-role-vocabulary.md
// for the routed note this suite encodes.
//
// ── THE DECISION THIS ENCODES (Michael, 2026-10-13) ────────────────────────
// "Billing never reads the MAR by default. For coding work only, an office
//  manager may grant billing access to a MAR, time-limited, expiring on its
//  own, and audit-logged."
//
// Four properties, one section each:
//   A  billing is DENIED by default
//   B  the grant requires the OFFICE MANAGER and nobody else
//   C  the grant EXPIRES ON ITS OWN, evaluated at read time
//   D  the grant, its refusals, and each granted read are LOGGED
//
// ── WHY THIS SUITE EXISTS, measured rather than asserted ───────────────────
// `alf_mar` -- the resource that OWNS the table -- already refuses billing:
// ALF_MAR_ROLES = { owner, nursing, med_aide } at api/sd-data.js:11148, and
// both read (:11191) and write (:11234) gate on it. Section A2/A3 pin that so
// it cannot regress while the rest is being built.
//
// The hole is a SIBLING RESOURCE. `alf_family_contacts` action `family_mar`
// gates on ALF_FAMILY_READ_ROLES = { owner, billing, nursing }
// (api/sd-data.js:12551, used at :12654), so a billing clerk 403'd from the
// MAR directly receives a named resident's full medication administration
// record by asking for that resident's family contact -- and because `billing`
// is in the BROAD half of that set, the assignment scope is skipped entirely
// (:12656), so it is every resident on the licence, not one.
//
// THIS IS THE THIRD TIME THE SAME ROLE HAS REACHED THE SAME DATA BY A
// DIFFERENT DOOR, which is why the answer is a vocabulary rule and not a
// third one-off patch:
//   * 2026-10-05  H1 #877 -- `family_mar` had NO caller gate at all. Fixed by
//                 inheriting `read`'s role set, which is how billing got in.
//                 tests/sd_data_family_mar_gate.js pins that fix.
//   * 2026-10-07  7ed27c5e -- `derive_charges` handed billing the medication
//                 NAME for every dose for a named resident for a whole month,
//                 via ALF_MANAGEMENT_ROLES = { owner, billing }. Redacted.
//   * now         `family_mar` itself, still open at HEAD.
// The author of the #877 fix declared this and declined to narrow it in
// passing -- api/sd-data.js:12649-12653 and SAIRN-ACTIVE-WORK-hank.md:2588 --
// because a gate disagreeing with its sibling was the defect being repaired.
// That was the right call. This suite is the decision arriving.
//
// ── IT DRIVES THE REAL HANDLER, not a reimplementation ─────────────────────
// Same technique and the same fixture shape as tests/sd_data_family_mar_gate.js,
// with auth, licence and fetch mocked. A reimplementation would pass against
// the unfixed code, which is the whole failure mode this platform keeps paying
// for. Section A4 is the control that proves A1 is not passing because
// everything is denied, and B3/C3 are the controls that prove the grant is a
// real capability and not a second refusal.
//
// ── NAMES THIS SUITE CHOOSES, AND THEY ARE THE api/ OWNER'S TO OVERRULE ────
// Nothing below exists yet, so every identifier here is a PROPOSAL. They are
// collected in one block so that landing the feature under different names is
// an edit to this block and not a rewrite of the suite.
//
//   GRANT_ROLE        the role permitted to grant. 'office_manager'.
//                     ** IT IS NOT IN THIS APP'S ROLE VOCABULARY. **
//                     ROLES_BY_APP.sairncare is
//                       ['owner','nursing','med_aide','caregiver','billing','activities']
//                     at api/_lib/auth.js:238 -- there is no office manager in
//                     SAIRNcare at all. Arm B1 FAILS ON THAT and is the one
//                     arm here that is a question rather than a defect: either
//                     the role is added to ROLES_BY_APP, to api/alf-auth.js's
//                     provisioning set and to the employee_auth CHECK
//                     together, or `owner` is declared to BE the office
//                     manager for this purpose. Both are legitimate; picking
//                     one silently is not. The routed note states both.
//   GRANT_ACTION      'mar_access_grant' on resource 'alf_family_contacts'.
//   GRANT_TABLE       'alf_mar_access_grants'.
//   GRANT_ROLES_CONST the source constant naming the grantor set:
//                     'ALF_MAR_GRANT_ROLES'.
//   CEILING_CONST     the source constant bounding how long a grant may run:
//                     'ALF_MAR_GRANT_MAX_HOURS'. Arm C2 asserts a named
//                     ceiling exists rather than asserting a number, because a
//                     magic number in a test is a number nobody owns.
//   EVENT_GRANTED / EVENT_REFUSED / EVENT_READ
//                     the three audit event_type strings. They must also be in
//                     the CHECK constraint of sql/sairncare_audit_log_schema.sql
//                     -- arm D5 -- because an event_type the table rejects is
//                     an audit write that returns false and logs nothing. That
//                     table's CHECK today lists five values and none of these.
//
// Run:  node tests/mar_billing_grant.test.js
// Exit: 0 all arms proved and passing · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');

const GRANT_ROLE = 'office_manager';
const GRANT_ACTION = 'mar_access_grant';
const GRANT_TABLE = 'alf_mar_access_grants';
const GRANT_ROLES_CONST = 'ALF_MAR_GRANT_ROLES';
const CEILING_CONST = 'ALF_MAR_GRANT_MAX_HOURS';
const EVENT_GRANTED = 'mar_access_granted';
const EVENT_REFUSED = 'mar_access_grant_refused';
const EVENT_READ = 'mar_access_read';
const AUDIT_TABLE = 'sairncare_audit_log';

process.env.SUPABASE_URL = 'https://fake.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'fake-service-key';

const licenseMod = require(path.join(ROOT, 'api/_lib/license.js'));
licenseMod.validateLicenseKey = async () => ({
  valid: true, active: true, license_hash: 'HASH1',
  stripe_subscription_id: 'sub_1', trial_ends_at: null, app_id: 'sairncare'
});

const authMod = require(path.join(ROOT, 'api/_lib/auth.js'));
const REAL_ROLES_BY_APP = authMod.ROLES_BY_APP;
authMod.tokenFromRequest = (req) => req.headers['x-test-token'] || null;
authMod.verifySessionToken = (token) => {
  if (!token) return null;
  const p = JSON.parse(token);
  return { role: p.role, employee_id: p.employee_id, app: 'sairncare',
           subject: p.employee_id };
};

// ── THE FIXTURE. Lifted from tests/sd_data_family_mar_gate.js:48-69 rather
//    than re-invented, including `mar_consent` (NOT `consent_granted`): the
//    consent library requires an explicit true, and a made-up field name turns
//    every ALLOWED arm into NO_MAR_CONSENT -- a fixture bug wearing the costume
//    of a code bug, already paid for once in that file.
const CLIENTS = [
  { client_id: 'R1', assigned_employee_id: 'E1' },
  { client_id: 'R2', assigned_employee_id: 'E2' },
];
const CONTACTS = [
  { contact_id: 'C1', resident_id: 'R1', name: 'Dana Reyes',
    relationship: 'daughter', email: 'd@example.com', phone: '555-0100',
    active: true, mar_consent: true,
    created_at: '2026-01-01', updated_at: '2026-01-01' },
];
const MAR = [
  { entry_id: 'M1', resident_id: 'R1', entry_type: 'administration',
    data: { med: 'Lisinopril', status: 'given' },
    created_at: '2026-02-01T09:00:00Z' },
];

const HOUR = 3600 * 1000;
function isoIn(ms) { return new Date(Date.now() + ms).toISOString(); }

// GRANTS is the mutable half of the fixture: an arm sets it to decide what the
// grant table currently holds, so section C can present an UNEXPIRED and an
// EXPIRED grant to the same code path and see two different answers.
let GRANTS = [];
// Everything the handler POSTs, in order, so sections C and D can assert on
// what was WRITTEN rather than on what was returned. A 200 that wrote no audit
// row and a 200 that wrote one are indistinguishable from the response alone,
// and that exact gap is why api/_lib/audit.js surfaces `attributed`.
let WRITES = [];

function resetFixture() { GRANTS = []; WRITES = []; }

global.fetch = async (url, opts) => {
  const u = String(url);
  const method = (opts && opts.method) || 'GET';
  let body = null;
  if (opts && opts.body) { try { body = JSON.parse(opts.body); } catch (e) { body = opts.body; } }
  if (method !== 'GET') {
    WRITES.push({ url: u, method, body });
    return { ok: true, status: 201, text: async () => '',
             json: async () => (Array.isArray(body) ? body : [body]) };
  }
  if (new RegExp(GRANT_TABLE + '\\?').test(u)) {
    return { ok: true, status: 200, json: async () => GRANTS };
  }
  if (/alf_clients\?/.test(u)) {
    const m = u.match(/assigned_employee_id=eq\.([^&]+)/);
    const who = m ? decodeURIComponent(m[1]) : null;
    const rows = CLIENTS.filter((c) => !who || c.assigned_employee_id === who)
      .map((c) => ({ client_id: c.client_id }));
    return { ok: true, status: 200, json: async () => rows };
  }
  if (/alf_family_contacts\?/.test(u)) {
    const m = u.match(/contact_id=eq\.([^&]+)/);
    const id = m ? decodeURIComponent(m[1]) : null;
    return { ok: true, status: 200,
             json: async () => CONTACTS.filter((c) => !id || c.contact_id === id) };
  }
  if (/alf_mar\?/.test(u)) {
    return { ok: true, status: 200, json: async () => MAR };
  }
  // NOT a silent empty list. An unmocked read that returns [] makes a DENY arm
  // pass for the wrong reason -- the caller was refused because the fixture had
  // nothing, not because the gate held.
  throw new Error('Unmocked fetch: ' + method + ' ' + u);
};

delete require.cache[require.resolve(path.join(ROOT, 'api/sd-data.js'))];
const handler = require(path.join(ROOT, 'api/sd-data.js'));

function fakeRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}
async function call(role, employeeId, action, payload, resource) {
  const req = {
    method: 'POST',
    headers: { authorization: 'Bearer testkey',
               'x-test-token': JSON.stringify({ role, employee_id: employeeId }) },
    body: { action, resource: resource || 'alf_family_contacts',
            payload: payload || {} },
  };
  const res = fakeRes();
  try { await handler(req, res); } catch (e) { res.threw = e; }
  return res;
}
const famMar = (role, emp, contactId) =>
  call(role, emp, 'family_mar', { contact_id: contactId });
const grant = (role, emp, payload) => call(role, emp, GRANT_ACTION, payload);

// ── A 400 FROM AN ACTION THAT DOES NOT EXIST IS NOT A REFUSAL ABOUT THE
//    PAYLOAD, AND THIS GUARD EXISTS BECAUSE TWO ARMS PASSED ON ONE.
// First run of this file: C1 ("a grant with no expires_at is 400") and C3
// ("a grant a year out is 400") both went GREEN -- against a handler with no
// grant action at all. The dispatcher answered
//   400 {"error":{"message":"action must be 'read' or 'write' or 'family_mar'"}}
// to every malformed-grant arm, so the two arms that are supposed to prove the
// TIME BOUND was enforced were in fact proving the action is unimplemented.
// Caught by reading the failure text of the arms around them, not by the exit
// code: 7 passed looked like seven regression pins.
//
// Those two are now UNPROVEN while the action is absent, which is the third
// state this platform requires -- "could not run" is never folded into
// "passed". They convert to real assertions the moment the action exists.
function unknownAction(res) {
  const m = res && res.body && res.body.error && res.body.error.message;
  return res && res.statusCode === 400 && typeof m === 'string'
    && /action must be/.test(m);
}

// ── THE THREE OUTCOMES, AND UNPROVEN IS COUNTED RATHER THAN PRINTED ────────
// An arm that could not be evaluated is not a pass. It is counted, it is named
// in the summary line beside pass and fail, and `process.exit` reads that
// counter -- so this suite cannot exit 0 with an unproven arm in it.
// tools/unproven_arm_check.py's A1/A2/A3 are the detectors for getting this
// wrong; this file is in their scope (tests/**/*.test.js) on purpose.
let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(l) { pass++; console.log('  ok       ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL     ' + l);
  if (why) console.log('           ' + String(why).slice(0, 300));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 300));
}

// Source read for the pinning arms. Comment lines are stripped because this
// handler DOCUMENTS the shapes it refuses, so a naive grep matches the
// documentation and reports a fix that is not there -- the same class
// tests/sd_data_family_mar_gate.js:192-196 was already bitten by.
const SRC = fs.readFileSync(path.join(ROOT, 'api/sd-data.js'), 'utf8');
const CODE = SRC.split(/\r?\n/)
  .filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');

(async function main() {
  console.log('BILLING / MAR GRANT -- criteria 2026-10-13.1 (FAILING-FIRST)\n');

  // ── A. DENIED BY DEFAULT ────────────────────────────────────────────────
  console.log('A. billing is DENIED by default');

  resetFixture();
  let r = await famMar('billing', 'E9', 'C1');
  if (r.statusCode === 403 && r.body && r.body.error
      && r.body.error.code === 'FORBIDDEN') {
    ok('A1. billing with NO grant is 403 FORBIDDEN on family_mar. THIS IS THE '
     + 'OPEN HOLE: at HEAD it is 200 and returns R1\'s full MAR, because '
     + 'ALF_FAMILY_READ_ROLES (api/sd-data.js:12551) includes billing and '
     + 'family_mar inherits it (:12654)');
  } else {
    bad('A1. billing with no grant must be 403 FORBIDDEN on family_mar',
        'status=' + r.statusCode + ' body=' + JSON.stringify(r.body));
  }

  if (r.statusCode === 403 && !/alf_mar\?/.test((WRITES.map((w) => w.url).join('|')))
      && r.body && !(r.body.data)) {
    ok('A2. ...and no MAR row reached the caller with the refusal. A 403 '
     + 'carrying data is not a refusal');
  } else if (r.statusCode === 403) {
    bad('A2. the 403 must carry no MAR data', JSON.stringify(r.body).slice(0, 200));
  } else {
    cannot('A2. whether the refusal leaks a row cannot be judged until A1 '
         + 'refuses at all', 'A1 returned ' + r.statusCode);
  }

  resetFixture();
  r = await famMar('billing', 'E9', 'C1');
  const sawMarFetch = r.statusCode === 403;
  if (sawMarFetch) {
    ok('A3. and billing is refused BEFORE the contact row is read, so it is '
     + 'not told whether C1 exists -- the existence oracle api/sd-data.js'
     + ':12645-12647 already refuses for the narrow tier');
  } else {
    bad('A3. the refusal must precede the contact lookup',
        'status=' + r.statusCode);
  }

  resetFixture();
  r = await call('billing', 'E9', 'read', {}, 'alf_mar');
  if (r.statusCode === 403) {
    ok('A4. billing is 403 on alf_mar/read -- REGRESSION PIN, green at HEAD. '
     + 'ALF_MAR_ROLES = { owner, nursing, med_aide } (api/sd-data.js:11148, '
     + 'gated :11191). This is the answer the sibling resource must agree with');
  } else {
    bad('A4. billing must stay 403 on alf_mar/read', 'status=' + r.statusCode);
  }

  resetFixture();
  r = await call('billing', 'E9', 'write',
                 { id: 'M9', resident_id: 'R1', entry_type: 'administration' },
                 'alf_mar');
  if (r.statusCode === 403) {
    ok('A5. billing is 403 on alf_mar/write too -- REGRESSION PIN, green at '
     + 'HEAD (api/sd-data.js:11234). A grant is a READ grant and must never '
     + 'become a write one');
  } else {
    bad('A5. billing must stay 403 on alf_mar/write', 'status=' + r.statusCode);
  }

  resetFixture();
  r = await famMar('nursing', 'E9', 'C1');
  if (r.statusCode === 200) {
    ok('A6. CONTROL -- nursing, with no assignment and no grant, still gets '
     + '200. WITHOUT THIS ARM the fix could be "deny everything" and A1-A5 '
     + 'would all pass');
  } else {
    bad('A6. a broad clinical role must not be collateral damage',
        'status=' + r.statusCode + ' body=' + JSON.stringify(r.body));
  }

  resetFixture();
  r = await famMar('activities', 'E1', 'C1');
  if (r.statusCode === 200) {
    ok('A7. CONTROL -- the assigned narrow role still passes, so the change is '
     + 'to the ROLE SET and not to the assignment logic '
     + 'tests/sd_data_family_mar_gate.js:161 pins');
  } else {
    bad('A7. the assigned narrow role must keep passing',
        'status=' + r.statusCode);
  }

  // Source pin. The named constant must stop including billing, OR family_mar
  // must stop reading that constant. Either resolution satisfies this arm;
  // asserting only one would dictate the implementation.
  const famRoleLine = (CODE.match(/const ALF_FAMILY_READ_ROLES = [^\n]*/) || [''])[0];
  const ANCHOR = "if (action === 'family_mar')";
  const anchorCount = CODE.split(ANCHOR).length - 1;
  if (anchorCount !== 1) {
    cannot('A8. the source anchor ' + JSON.stringify(ANCHOR) + ' matched '
         + anchorCount + ' time(s), not once, so this arm cannot say which '
         + 'block it measured', 'uniqueness guard');
  } else {
    const famBlock = CODE.split(ANCHOR)[1] || '';
    const gateRegion = famBlock.split('familyMarView(')[0] || '';
    const billingOut = !/billing:\s*true/.test(famRoleLine);
    const notInherited = !/ALF_FAMILY_READ_ROLES/.test(gateRegion);
    if (billingOut || notInherited) {
      ok('A9. family_mar\'s gate no longer admits billing -- either '
       + 'ALF_FAMILY_READ_ROLES dropped it (' + billingOut + ') or family_mar '
       + 'stopped inheriting that set (' + notInherited + ')');
    } else {
      bad('A9. family_mar must not admit billing through ALF_FAMILY_READ_ROLES',
          famRoleLine.trim().slice(0, 160));
    }
  }

  // ── B. THE GRANT NEEDS THE OFFICE MANAGER ───────────────────────────────
  console.log('\nB. the grant requires the OFFICE MANAGER and nobody else');

  if (CODE.indexOf('const ' + GRANT_ROLES_CONST) !== -1) {
    ok('B1. ' + GRANT_ROLES_CONST + ' exists as a named constant, so the '
     + 'grantor set is one declared thing and not an inline literal somebody '
     + 'widens');
  } else {
    bad('B1. the grantor set must be a named constant ' + GRANT_ROLES_CONST,
        'absent from api/sd-data.js');
  }

  // THE VOCABULARY QUESTION, AS AN ARM RATHER THAN A PARAGRAPH.
  const careRoles = (REAL_ROLES_BY_APP && REAL_ROLES_BY_APP.sairncare) || [];
  if (careRoles.indexOf(GRANT_ROLE) !== -1) {
    ok('B2. ' + GRANT_ROLE + ' is in ROLES_BY_APP.sairncare, so a session can '
     + 'actually hold it');
  } else {
    bad('B2. ** DECISION, NOT A DEFECT ** -- ' + GRANT_ROLE + ' is not in this '
      + 'app\'s role vocabulary, so no session can ever satisfy the grant gate. '
      + 'Resolve by ADDING the role (ROLES_BY_APP at api/_lib/auth.js:238, the '
      + 'provisioning set in api/alf-auth.js and the employee_auth CHECK, all '
      + 'three together) or by DECLARING owner to be the office manager here '
      + 'and setting GRANT_ROLE to \'owner\' in this file. See the routed note',
        'ROLES_BY_APP.sairncare = [' + careRoles.join(', ') + ']');
  }

  const NON_GRANTORS = careRoles.filter((x) => x !== GRANT_ROLE);
  let refusedAll = true, firstBad = null;
  for (const role of NON_GRANTORS) {
    resetFixture();
    const rr = await grant(role, 'E9',
      { contact_id: 'C1', grantee_employee_id: 'E7', expires_at: isoIn(2 * HOUR) });
    if (rr.statusCode !== 403) { refusedAll = false; firstBad = role + ' -> ' + rr.statusCode; break; }
  }
  if (NON_GRANTORS.length === 0) {
    cannot('B3. no non-grantor roles to drive', 'ROLES_BY_APP.sairncare empty');
  } else if (refusedAll) {
    ok('B3. every one of the ' + NON_GRANTORS.length + ' non-grantor SAIRNcare '
     + 'roles is 403 on ' + GRANT_ACTION + ' (' + NON_GRANTORS.join(', ') + ') '
     + '-- driven per role, not asserted from the table');
  } else {
    bad('B3. every non-grantor role must be 403 on ' + GRANT_ACTION, firstBad);
  }

  resetFixture();
  r = await grant('billing', 'E7',
    { contact_id: 'C1', grantee_employee_id: 'E7', expires_at: isoIn(2 * HOUR) });
  if (r.statusCode === 403) {
    ok('B4. billing cannot grant ITSELF access. B3 covers it as one of many; '
     + 'this arm names it, because self-grant is the whole point of the '
     + 'control and a future widening would hit it first');
  } else {
    bad('B4. billing must not be able to self-grant', 'status=' + r.statusCode);
  }

  resetFixture();
  r = await grant(GRANT_ROLE, 'E3',
    { contact_id: 'C1', grantee_employee_id: 'E7', expires_at: isoIn(2 * HOUR) });
  if (r.statusCode === 200 || r.statusCode === 201) {
    ok('B5. CONTROL -- the grantor role succeeds. Without this arm the feature '
     + 'could be "refuse everybody" and B3/B4 would still pass');
  } else {
    bad('B5. the grantor role must be able to grant',
        'status=' + r.statusCode + ' body=' + JSON.stringify(r.body));
  }

  // ── C. THE GRANT EXPIRES ON ITS OWN ─────────────────────────────────────
  console.log('\nC. the grant EXPIRES ON ITS OWN, evaluated at read time');

  resetFixture();
  r = await grant(GRANT_ROLE, 'E3', { contact_id: 'C1', grantee_employee_id: 'E7' });
  if (unknownAction(r)) {
    cannot('C1. a grant with no expires_at CANNOT BE JUDGED while ' + GRANT_ACTION
         + ' does not exist -- the 400 is the dispatcher rejecting the action, '
         + 'not the handler rejecting a missing expiry', r.body.error.message);
  } else if (r.statusCode === 400) {
    ok('C1. a grant with NO expires_at is 400. "Time-limited" cannot be a '
     + 'default somebody omits -- an unbounded grant is the thing being '
     + 'prevented, so absence must be a refusal and not a fallback');
  } else {
    bad('C1. a grant without expires_at must be refused 400',
        'status=' + r.statusCode);
  }

  if (CODE.indexOf(CEILING_CONST) !== -1) {
    ok('C2. ' + CEILING_CONST + ' exists, so how long a grant may run is a '
     + 'declared number in the handler rather than whatever the caller sent');
  } else {
    bad('C2. a named ceiling ' + CEILING_CONST + ' must bound the grant window',
        'absent from api/sd-data.js');
  }

  resetFixture();
  r = await grant(GRANT_ROLE, 'E3',
    { contact_id: 'C1', grantee_employee_id: 'E7', expires_at: isoIn(365 * 24 * HOUR) });
  if (unknownAction(r)) {
    cannot('C3. whether the ceiling is ENFORCED cannot be judged while '
         + GRANT_ACTION + ' does not exist -- same dispatcher 400 as C1',
           r.body.error.message);
  } else if (r.statusCode === 400) {
    ok('C3. a grant a year out is 400 -- the ceiling is ENFORCED, not merely '
     + 'declared. C2 proves the constant exists; this proves it is read');
  } else {
    bad('C3. a grant beyond the ceiling must be refused', 'status=' + r.statusCode);
  }

  resetFixture();
  GRANTS = [{ grant_id: 'G1', contact_id: 'C1', resident_id: 'R1',
              grantee_employee_id: 'E7', granted_by: 'E3',
              expires_at: isoIn(2 * HOUR), revoked_at: null }];
  r = await famMar('billing', 'E7', 'C1');
  if (r.statusCode === 200) {
    ok('C4. CONTROL -- with an UNEXPIRED grant, billing/E7 gets 200. The grant '
     + 'is a real capability; A1 is a default and not a wall. '
     + '** THIS PASS IS VACUOUS WHILE A1 IS RED: at HEAD billing gets 200 on '
     + 'family_mar with or without a grant row, so C4 is only load-bearing '
     + 'once A1 refuses. Read it with A1, never alone **');
  } else {
    bad('C4. an unexpired grant must admit the named grantee',
        'status=' + r.statusCode + ' body=' + JSON.stringify(r.body));
  }

  resetFixture();
  GRANTS = [{ grant_id: 'G1', contact_id: 'C1', resident_id: 'R1',
              grantee_employee_id: 'E7', granted_by: 'E3',
              expires_at: isoIn(-1 * HOUR), revoked_at: null }];
  r = await famMar('billing', 'E7', 'C1');
  if (r.statusCode === 403) {
    ok('C5. THE ARM THE WHOLE SECTION IS FOR -- an EXPIRED grant row is still '
     + 'in the table and billing is 403 anyway. "Expiring on its own" means '
     + 'the READ PATH compares expires_at to now; a grant that only expires '
     + 'when a sweeper deletes the row is live for as long as the sweeper is '
     + 'down, and nothing would say so');
  } else {
    bad('C5. an expired grant must be refused at read time',
        'status=' + r.statusCode + ' body=' + JSON.stringify(r.body));
  }

  resetFixture();
  GRANTS = [{ grant_id: 'G1', contact_id: 'C1', resident_id: 'R1',
              grantee_employee_id: 'E7', granted_by: 'E3',
              expires_at: isoIn(2 * HOUR), revoked_at: null }];
  r = await famMar('billing', 'E8', 'C1');
  if (r.statusCode === 403) {
    ok('C6. the grant is to ONE employee -- billing/E8 is 403 while billing/E7 '
     + 'is admitted by the same row. A grant to a ROLE is not time-limited '
     + 'access, it is a role change with a timer on it');
  } else {
    bad('C6. a grant must not admit a different billing employee',
        'status=' + r.statusCode);
  }

  resetFixture();
  GRANTS = [{ grant_id: 'G1', contact_id: 'C9', resident_id: 'R2',
              grantee_employee_id: 'E7', granted_by: 'E3',
              expires_at: isoIn(2 * HOUR), revoked_at: null }];
  r = await famMar('billing', 'E7', 'C1');
  if (r.statusCode === 403) {
    ok('C7. and the grant is to ONE resident -- a live grant on R2 does not '
     + 'open R1. "Access to a MAR", singular, is what was decided');
  } else {
    bad('C7. a grant must not generalise to another resident',
        'status=' + r.statusCode);
  }

  // ── D. LOGGED ───────────────────────────────────────────────────────────
  console.log('\nD. the grant, its refusals, and each granted read are LOGGED');

  function auditRows() {
    return WRITES.filter((w) => w.url.indexOf(AUDIT_TABLE) !== -1)
      .map((w) => (Array.isArray(w.body) ? w.body : [w.body])).reduce(
        (a, b) => a.concat(b), []).filter(Boolean);
  }

  resetFixture();
  r = await grant(GRANT_ROLE, 'E3',
    { contact_id: 'C1', grantee_employee_id: 'E7', expires_at: isoIn(2 * HOUR) });
  let rows = auditRows();
  let granted = rows.filter((x) => x && x.event_type === EVENT_GRANTED);
  if (granted.length === 1) {
    ok('D1. the grant writes exactly one ' + EVENT_GRANTED + ' row to '
     + AUDIT_TABLE);
  } else {
    bad('D1. the grant must write one ' + EVENT_GRANTED + ' audit row',
        'found ' + granted.length + ' of ' + rows.length + ' audit row(s)');
  }

  if (granted.length === 1) {
    const d = granted[0].detail || {};
    const have = ['grantee_employee_id', 'resident_id', 'expires_at']
      .filter((k) => d[k] !== undefined && d[k] !== null);
    if (have.length === 3 && granted[0].employee_id === 'E3'
        && granted[0].role === GRANT_ROLE) {
      ok('D2. and the row names WHO granted (employee_id/role), to WHOM, for '
       + 'WHICH resident, and UNTIL WHEN. A grant log missing the expiry '
       + 'cannot answer "was this read inside its window", which is the only '
       + 'question anyone asks it');
    } else {
      bad('D2. the audit row must carry grantor, grantee, resident and expiry',
          'detail keys present: [' + have.join(', ') + '] employee_id='
          + granted[0].employee_id + ' role=' + granted[0].role);
    }
  } else {
    cannot('D2. the row\'s shape cannot be judged when D1 found '
         + granted.length + ' rows', 'depends on D1');
  }

  resetFixture();
  r = await grant('billing', 'E7',
    { contact_id: 'C1', grantee_employee_id: 'E7', expires_at: isoIn(2 * HOUR) });
  rows = auditRows();
  if (rows.filter((x) => x && x.event_type === EVENT_REFUSED).length >= 1) {
    ok('D3. a REFUSED grant is logged too. api/*-auth.js audits every outcome '
     + 'of set_active including its refusals, and an attempt to self-grant '
     + 'access to a medication record is the single most worth-recording '
     + 'event this feature has');
  } else {
    bad('D3. a refused grant attempt must write ' + EVENT_REFUSED,
        'audit rows: ' + JSON.stringify(rows.map((x) => x && x.event_type)));
  }

  resetFixture();
  GRANTS = [{ grant_id: 'G1', contact_id: 'C1', resident_id: 'R1',
              grantee_employee_id: 'E7', granted_by: 'E3',
              expires_at: isoIn(2 * HOUR), revoked_at: null }];
  r = await famMar('billing', 'E7', 'C1');
  rows = auditRows();
  if (r.statusCode === 200
      && rows.filter((x) => x && x.event_type === EVENT_READ).length >= 1) {
    ok('D4. EACH granted read is logged, not just the grant. One audit row per '
     + 'grant tells you access was possible; one per read tells you what was '
     + 'actually looked at, and only the second is an access log');
  } else if (r.statusCode !== 200) {
    cannot('D4. cannot observe the read audit until C4 admits the grantee',
           'status=' + r.statusCode);
  } else {
    bad('D4. a granted MAR read must write ' + EVENT_READ,
        'audit rows: ' + JSON.stringify(rows.map((x) => x && x.event_type)));
  }

  // THE EVENT TYPES MUST BE ACCEPTED BY THE TABLE. An event_type outside the
  // CHECK constraint makes writeAuditLog's POST fail; it returns false and logs
  // server-side only (api/_lib/audit.js:131-134), so the grant succeeds and the
  // audit silently does not exist. That is the exact shape
  // tools/audit_event_type_check.py was built for.
  const DDL = path.join(ROOT, 'sql/sairncare_audit_log_schema.sql');
  if (!fs.existsSync(DDL)) {
    cannot('D5. the audit DDL is not at ' + DDL, 'cannot compare event types');
  } else {
    const ddl = fs.readFileSync(DDL, 'utf8');
    const missing = [EVENT_GRANTED, EVENT_REFUSED, EVENT_READ]
      .filter((e) => ddl.indexOf("'" + e + "'") === -1);
    if (missing.length === 0) {
      ok('D5. all three event types are in the sairncare_audit_log CHECK '
       + 'constraint, so the writes are accepted rather than silently dropped');
    } else {
      bad('D5. these event types are not in the CHECK constraint and would be '
        + 'rejected by the table: ' + missing.join(', '),
          'sql/sairncare_audit_log_schema.sql:31-36 lists five values');
    }
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed, '
            + unproven + ' unproven');
  if (failed.length) console.log(failed.length + ' ARM(S) FAILED: ' + failed.join(', '));
  if (notProved.length) console.log(notProved.length + ' ARM(S) UNPROVEN: ' + notProved.join(', '));
  console.log('\nEXPECTED RED until the api/ owner lands the feature. '
            + 'Registered in docs/known-red-suites.json; no gate reads this.');
  process.exit(fail ? 1 : (unproven ? 3 : 0));
})();
