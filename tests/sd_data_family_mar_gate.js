// tests/sd_data_family_mar_gate.js
//
// REQUIREMENT: action 'family_mar' on alf_family_contacts must gate the CALLER
//   the same way action 'read' does -- on a role set AND on the caller's
//   resident assignment -- before it discloses a resident's medication
//   administration record.
//
// WHY, AND IT IS H1 FINDING #877 AT HIGH. Until 2026-10-05 'family_mar' gated
// on NEITHER. `action === 'read'`, eleven lines above it in the same handler,
// resolves ALF_FAMILY_READ_ROLES and then the caller's assigned residents, and
// 403s a resident that is not theirs. 'family_mar' did neither.
//
// THE CONSENT CHECK WAS STANDING IN FOR AN AUTHORISATION CHECK, which is the
// defect in one sentence. familyMarView() answers "may this FAMILY CONTACT see
// anything" -- a question about the contact. Nothing asked "may this EMPLOYEE
// read this resident's MAR". So any authenticated session on the licence,
// including a med_aide or activities employee with NO resident assigned to
// them, could pass any contact_id and receive that resident's full MAR.
//
// IT DRIVES THE REAL HANDLER, not a reimplementation -- same technique as
// tests/sairncare/test-alf-mar.js, with auth, licence and fetch mocked. A
// reimplementation would have passed against the unfixed code.
//
// Run:  node tests/sd_data_family_mar_gate.js

'use strict';
const path = require('path');
const ROOT = path.join(__dirname, '..');

process.env.SUPABASE_URL = 'https://fake.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'fake-service-key';

const licenseMod = require(path.join(ROOT, 'api/_lib/license.js'));
licenseMod.validateLicenseKey = async () => ({
  valid: true, active: true, license_hash: 'HASH1',
  stripe_subscription_id: 'sub_1', trial_ends_at: null, app_id: 'sairncare'
});

const authMod = require(path.join(ROOT, 'api/_lib/auth.js'));
authMod.tokenFromRequest = (req) => req.headers['x-test-token'] || null;
authMod.verifySessionToken = (token) => {
  if (!token) return null;
  const p = JSON.parse(token);
  return { role: p.role, employee_id: p.employee_id, app: 'sairncare',
           subject: p.employee_id };
};

// ── THE FIXTURE. Two residents, each assigned to a DIFFERENT employee, and a
//    family contact on each. The whole question is whether employee E2 can
//    reach resident R1's MAR through R1's contact.
const CLIENTS = [
  { client_id: 'R1', assigned_employee_id: 'E1' },
  { client_id: 'R2', assigned_employee_id: 'E2' },
];
const CONTACTS = [
  { contact_id: 'C1', resident_id: 'R1', name: 'Dana Reyes',
    relationship: 'daughter', email: 'd@example.com', phone: '555-0100',
    // mar_consent, not consent_granted: the library requires an EXPLICIT
    // true and treats null/0/''/'true' as NOT consent. My first fixture
    // invented the field name and every ALLOWED arm came back
    // NO_MAR_CONSENT -- a fixture bug that looked like a code bug.
    active: true, mar_consent: true,
    created_at: '2026-01-01', updated_at: '2026-01-01' },
];
const MAR = [
  { entry_id: 'M1', resident_id: 'R1', entry_type: 'administration',
    data: { med: 'Lisinopril', status: 'given' },
    created_at: '2026-02-01T09:00:00Z' },
];

global.fetch = async (url, opts) => {
  const u = String(url);
  const method = (opts && opts.method) || 'GET';
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
    const rows = CONTACTS.filter((c) => !id || c.contact_id === id);
    return { ok: true, status: 200, json: async () => rows };
  }
  if (/alf_mar\?/.test(u)) {
    return { ok: true, status: 200, json: async () => MAR };
  }
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
async function famMar(role, employeeId, contactId) {
  const req = {
    method: 'POST',
    headers: { authorization: 'Bearer testkey',
               'x-test-token': JSON.stringify({ role, employee_id: employeeId }) },
    body: { action: 'family_mar', resource: 'alf_family_contacts',
            payload: { contact_id: contactId } },
  };
  const res = fakeRes();
  await handler(req, res);
  return res;
}

let pass = 0, fail = 0;
function ok(l) { pass++; console.log('  ok   ' + l); }
function bad(l, why) {
  fail++;
  console.log('  FAIL ' + l);
  if (why) console.log('       ' + String(why).slice(0, 300));
}

(async function main() {
  console.log('FAMILY_MAR CALLER GATE -- criteria 2026-10-05.1\n');
  console.log('A. DENIED: a narrow role with NO assignment, and with the WRONG one');

  // med_aide, no residents assigned at all.
  let r = await famMar('med_aide', 'E9', 'C1');
  if (r.statusCode === 403) {
    ok('A1. med_aide with NO resident assigned is 403 -- and refused BEFORE ' +
       'the contact is looked up, so it is not told whether C1 exists');
  } else {
    bad('A1. an unassigned med_aide must be refused',
        'status=' + r.statusCode + ' body=' + JSON.stringify(r.body));
  }

  // activities, assigned R2, asking about R1's contact. This is the real
  // attack: a legitimate employee reaching a resident that is not theirs.
  r = await famMar('activities', 'E2', 'C1');
  if (r.statusCode === 403) {
    ok('A2. activities assigned to R2 asking about R1\'s contact is 403. THIS ' +
       'IS THE ONE THAT MATTERS: a legitimate employee with a real assignment ' +
       'reaching a resident who is not theirs');
  } else {
    bad('A2. a wrong-resident request must be refused',
        'status=' + r.statusCode + ' body=' + JSON.stringify(r.body));
  }

  if (r.body && r.body.error && r.body.error.code === 'FORBIDDEN') {
    ok('A3. ...and it is FORBIDDEN, distinct from NO_SUCH_CONTACT -- "you may ' +
       'not see that resident" and "that contact does not exist" are different ' +
       'answers and collapsing them is an oracle');
  } else {
    bad('A3. the refusal must be FORBIDDEN, not a 404',
        JSON.stringify(r.body));
  }

  console.log('\nB. ALLOWED: the authorised paths still work');

  // The assigned narrow employee for R1.
  r = await famMar('activities', 'E1', 'C1');
  if (r.statusCode === 200) {
    ok('B1. activities ASSIGNED to R1 passes. WITHOUT THIS ARM the fix could ' +
       'be "deny everything" and every arm in A would still pass');
  } else {
    bad('B1. the assigned narrow role must pass',
        'status=' + r.statusCode + ' body=' + JSON.stringify(r.body));
  }

  // A broad role needs no assignment at all -- same as `read`.
  r = await famMar('nursing', 'E9', 'C1');
  if (r.statusCode === 200) {
    ok('B2. nursing, with NO assignment, passes -- ALF_FAMILY_READ_ROLES is ' +
       'the same broad set `read` uses, and a broad role is scoped by the ' +
       'licence rather than by assignment');
  } else {
    bad('B2. a broad role must not need an assignment',
        'status=' + r.statusCode + ' body=' + JSON.stringify(r.body));
  }

  r = await famMar('owner', 'E9', 'C1');
  if (r.statusCode === 200) {
    ok('B3. owner passes too, so B2 is not passing on one lucky role');
  } else {
    bad('B3. owner must pass', 'status=' + r.statusCode);
  }

  console.log('\nC. THE GATE IS IN THE HANDLER, pinned at source');

  const fs = require('fs');
  const SRC = fs.readFileSync(path.join(ROOT, 'api/sd-data.js'), 'utf8');
  // Comments stripped: this handler now DOCUMENTS the old ungated shape, so a
  // naive grep matches the documentation. Third instance of that class this
  // week -- see tools/pycomments.py.
  const CODE = SRC.split(/\r?\n/)
    .filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');
  // UNIQUENESS GUARD, and it is here because the first version of this check
  // DID NOT HAVE ONE and was silently measuring the wrong block. The bare
  // string `action === 'family_mar'` occurs TWICE: once in the action
  // allow-list a hundred lines above (`action === 'read' || action ===
  // 'write' || action === 'family_mar'`) and once on the branch itself. So
  // split(...)[1] returned the text BETWEEN them -- `read`'s body -- and the
  // two source checks below were reading a block that is not the subject.
  // C1 failed honestly (no role gate in `read`'s body under that name) and
  // C2 PASSED ON READ'S OWN assigned_employee_id QUERY, which is the worse
  // half: a green arm that never touched the code it names.
  //
  // So the anchor is the branch statement, and the count is asserted rather
  // than assumed. If someone reshapes that line the check SAYS SO instead of
  // quietly grading a different region.
  const ANCHOR = "if (action === 'family_mar')";
  const anchorCount = CODE.split(ANCHOR).length - 1;
  if (anchorCount !== 1) {
    bad('C0. the source anchor ' + JSON.stringify(ANCHOR) + ' must match '
      + 'EXACTLY ONCE -- it matched ' + anchorCount + ' time(s), so C1-C3 '
      + 'below cannot say which block they measured and are NOT run');
    console.log('\n' + pass + ' passed, ' + fail + ' failed');
    process.exit(1);
  }
  ok('C0. the source anchor matches exactly once, so C1-C3 are measuring the '
    + 'family_mar branch and not some other region that happens to contain '
    + 'the same words');
  const famBlock = CODE.split(ANCHOR)[1] || '';
  const upToConsent = famBlock.split('familyMarView(')[0] || '';

  if (/marBroad/.test(upToConsent) && /ALF_FAMILY_READ_ROLES/.test(upToConsent)) {
    ok('C1. the role gate runs BEFORE the consent library is required');
  } else {
    bad('C1. the role gate must precede the consent check', '');
  }
  if (/assigned_employee_id=eq\./.test(upToConsent)) {
    ok('C2. and the assignment scope is resolved from alf_clients, by the same ' +
       'query `read` uses');
  } else {
    bad('C2. the assignment scope must be resolved', '');
  }
  if (/marScope\.indexOf\(String\(contact\.resident_id\)\)/.test(famBlock)) {
    ok('C3. and the resident is checked against that scope using the id off ' +
       'the STORED contact row -- never a caller-supplied resident_id, which ' +
       'is a parameter somebody edits');
  } else {
    bad('C3. the resident must be checked from the stored row', '');
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
