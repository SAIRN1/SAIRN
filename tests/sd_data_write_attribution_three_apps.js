// tests/sd_data_write_attribution_three_apps.js
//
// REQUIREMENT: a write branch that persists a row must record WHICH EMPLOYEE
//   wrote it, taken from the session, and a caller-supplied value must be
//   discarded.
//
// WHY. H1 routed a 10-resource attribution gap across SAIRNcare, SAIRNsenior
// and SAIRNroofing. REPRODUCED WITH MY OWN READ (`scratchpad/attr_scan.py`,
// read-only by construction, git status identical before and after): of 49
// branches in those three apps that POST or PATCH, **15 recorded no acting
// employee at all** — not a column, not a blob key, not an audit row.
//
// MY COUNT IS 15, NOT 10, AND I AM NOT RECLASSIFYING H1's FINDING. Only the
// originating finder closes or reclassifies one. The 15 is what my criteria
// found; the difference is reported and theirs stays open.
//
// EIGHT ARE FIXED HERE — the ones whose row is built through `storedBlob()`,
// where the stamp is two lines and needs no migration. The other seven build
// their row differently and each needs an individual read; they are listed as
// open in the handoff rather than stamped blind.
//
// IN THE BLOB, AFTER storedBlob, AND THAT ORDER IS THE GUARANTEE. storedBlob
// strips only the keys it is told to, so a caller-supplied `updatedBy` would
// survive into the row. The stamp overwrites whatever arrived.
//
// REAL: the handler and the auth module. MOCKED: fetch, validateLicenseKey.
// NOT RUN: the live round trip. ASSERTED ON THE OUTBOUND REQUEST, not the
// response — the response looks identical whether or not the field was stored
// (sairn-api-tester §7).
//
// AND THE REASON THAT MATTERS THIS ROUND: `node --check` exits 0 on a file
// whose every new line is a runtime ReferenceError. A syntax check is not a
// behaviour check. This file is the behaviour check.
//
// MUTATION PROOF: against the parent commit every B arm goes red.
//
// Run:  node tests/sd_data_write_attribution_three_apps.js

'use strict';
const path = require('path');
const ROOT = path.join(__dirname, '..');

const LIC_HASH = 'hash-of-the-attribution-3app-licence';
const LICENCE = require.resolve(path.join(ROOT, 'api/_lib/license.js'));
let APP_ID = 'sairncare';
require.cache[LICENCE] = {
  id: LICENCE, filename: LICENCE, loaded: true,
  exports: {
    validateLicenseKey: async () => ({
      valid: true, active: true, license_hash: LIC_HASH,
      stripe_subscription_id: 'sub_1', trial_ends_at: null, app_id: APP_ID
    }),
    hashLicense: () => LIC_HASH,
  },
};

process.env.SUPABASE_URL = 'https://example.invalid';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'service-role-for-the-test';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || 'three-app-attribution-test-secret';
const { signSessionToken } = require(path.join(ROOT, 'api/_lib/auth.js'));

let sent = [];
global.fetch = async (url, opts) => {
  const u = String(url);
  let body = null;
  try { body = opts && opts.body ? JSON.parse(opts.body) : null; } catch (e) { body = null; }
  sent.push({ url: u, method: (opts && opts.method) || 'GET', body: body });
  const ok = (rows) => ({ ok: true, status: 200, json: async () => rows,
                          text: async () => '' });
  if (/_employee_auth\?/.test(u)) return ok([{ active: true }]);
  // AN APPEND-ONLY EXISTENCE PROBE MUST ANSWER "NOT THERE YET". `alf_signals`
  // and its siblings look the id up by `entry_id=eq.` before writing and 409
  // ALREADY_RECORDED if a row comes back. The permissive one-row mock below
  // made that lookup succeed, so alf_signals refused with 409 -- correctly --
  // and arm A1 caught it as the one case of eight that never reached its
  // write. The refusal was READ rather than guessed at a third time.
  if (/entry_id=eq\./.test(u)) return ok([]);
  // Every read answers one permissive row so a branch's own precondition
  // reads (existing row, roster, rate card) do not short-circuit the write.
  return ok([{ data: {}, id: 'X1', entity_id: 'E1', client_id: 'C1',
               resident_id: 'R1', staff_id: 'S1', claim_id: 'CL1',
               location_id: 'L1', active: true }]);
};

delete require.cache[require.resolve(path.join(ROOT, 'api/sd-data.js'))];
const handler = require(path.join(ROOT, 'api/sd-data.js'));

function fakeRes() {
  const r = { statusCode: null, body: null, headers: {} };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  r.setHeader = (k, v) => { r.headers[k] = v; return r; };
  r.end = () => r;
  return r;
}

// THE EIGHT, with the app each belongs to, a role its own gate admits, and the
// table its POST lands on. Written down rather than derived from the handler:
// a test that reads its expected set out of its subject cannot see the subject
// lose a member.
const CASES = [
  { res: 'alf_activities', app: 'sairncare', role: 'owner', table: 'alf_activities' },
  { res: 'alf_billing', app: 'sairncare', role: 'owner', table: 'alf_billing' },
  { res: 'alf_facility', app: 'sairncare', role: 'owner', table: 'alf_facility' },
  { res: 'alf_signals', app: 'sairncare', role: 'owner', table: 'alf_signals' },
  { res: 'alf_staff', app: 'sairncare', role: 'owner', table: 'alf_staff' },
  { res: 'sen_caregivers', app: 'sairnsenior', role: 'owner', table: 'sen_caregivers' },
  { res: 'sen_claims', app: 'sairnsenior', role: 'owner', table: 'sen_claims' },
  { res: 'rf_locations', app: 'sairnroofing', role: 'owner', table: 'rf_locations' },
];

// One permissive payload. Branch preconditions differ; the fields they ask for
// are supplied together so a 400 on a missing id does not masquerade as a
// missing stamp. THE HOSTILE VALUES ARE THE POINT of arm C.
function payloadFor(res) {
  return {
    id: 'X1', resident_id: 'R1', client_id: 'C1', staff_id: 'S1',
    claim_id: 'CL1', entity_id: 'E1', location_id: 'L1',
    name: 'A Name',
    // `fall` was REFUSED: ALF_SIGNAL_TYPES (api/sd-data.js:11352) is
    // ['fall_detection','bed_exit','wandering_alert','activity_baseline'] and
    // the branch 400s on anything else. Read off the constant rather than
    // guessed -- the first run of this file had `fall` and alf_signals was
    // the one case of eight that never reached its write, which arm A1 is
    // there to catch and did.
    signal_type: 'fall_detection', recorded_at: '2026-09-01T10:00:00Z',
    hours: 1, amount: 10, active: true, date: '2026-09-01',
    updatedBy: 'SOMEONE-ELSE', updatedByRole: 'owner'
  };
}

async function write(c) {
  APP_ID = c.app;
  sent = [];
  const headers = {
    authorization: 'Bearer ATTR3-TEST-KEY',
    'x-sd-auth': signSessionToken({
      app: c.app, employee_id: 'ACTOR-42', role: c.role,
      license_hash: LIC_HASH })
  };
  const req = { method: 'POST', headers: headers, body: {
    action: 'write', resource: c.res, payload: payloadFor(c.res) } };
  const res = fakeRes();
  await handler(req, res);
  const w = sent.filter((q) => (q.method === 'POST' || q.method === 'PATCH')
    && q.url.indexOf(c.table) !== -1);
  return { res: res, posts: w, blob: w[0] && w[0].body && w[0].body.data };
}

let pass = 0, fail = 0;
function ok(l) { pass++; console.log('  ok   ' + l); }
function bad(l, why) {
  fail++;
  console.log('  FAIL ' + l);
  if (why) console.log('       ' + String(why).slice(0, 300));
}

(async function main() {
  console.log('WRITE ATTRIBUTION -- SAIRNcare / SAIRNsenior / SAIRNroofing '
    + '-- criteria 2026-10-07.1\n');

  console.log('A. EVERY ONE OF THE EIGHT REACHES ITS POST');
  const reached = [];
  const missed = [];
  for (const c of CASES) {
    const r = await write(c);
    if (r.posts.length) reached.push(c.res);
    else missed.push(c.res + '=' + r.res.statusCode);
  }
  if (reached.length === CASES.length) {
    ok('A1. all ' + CASES.length + ' branches issued a POST or PATCH to their '
       + 'own table. WITHOUT THIS ARM every assertion below could be passing on '
       + 'a branch that 400ed before it ever built a row -- which is the vacuous '
       + 'shape an attribution test fails into');
  } else {
    bad('A1. every case must reach its write -- ' + reached.length + ' of '
        + CASES.length, 'did not reach: ' + missed.join(', '));
  }

  console.log('\nB. THE BLOB CARRIES THE ACTING EMPLOYEE, FROM THE SESSION');
  for (const c of CASES) {
    const r = await write(c);
    if (!r.posts.length) { bad('B. ' + c.res + ' did not reach its write', 'status=' + r.res.statusCode); continue; }
    if (r.blob && r.blob.updatedBy === 'ACTOR-42'
        && r.blob.updatedByRole === c.role) {
      ok('B. ' + c.res + ' stores updatedBy=ACTOR-42 and updatedByRole='
         + c.role);
    } else {
      bad('B. ' + c.res + ' must store the session employee in its blob',
          'blob=' + JSON.stringify(r.blob));
    }
  }

  console.log('\nC. A CALLER-SUPPLIED updatedBy IS DISCARDED -- storedBlob cannot stop it');
  let discarded = 0;
  const kept = [];
  for (const c of CASES) {
    const r = await write(c);
    if (r.blob && r.blob.updatedBy === 'ACTOR-42') discarded++;
    else kept.push(c.res + '=' + (r.blob && r.blob.updatedBy));
  }
  if (discarded === CASES.length) {
    ok('C1. all ' + CASES.length + ' discarded the payload\'s '
       + '`updatedBy: SOMEONE-ELSE`. storedBlob strips only the keys it is told '
       + 'to, so the hostile value DOES reach the blob -- the stamp is written '
       + 'AFTER it, and that order is the only thing making this field evidence '
       + 'rather than a request');
  } else {
    bad('C1. every case must discard a caller-supplied actor -- '
        + discarded + ' of ' + CASES.length, kept.join(', '));
  }

  console.log('\nD. PINNED AT SOURCE -- stamped AFTER storedBlob, never before');
  const fs = require('fs');
  const SRC = fs.readFileSync(path.join(ROOT, 'api/sd-data.js'), 'utf8');
  const CODE = SRC.split(/\r?\n/)
    .filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');
  let after = 0;
  const before = [];
  for (const v of ['activityData', 'billingData', 'facilityData', 'signalData',
                   'staffData', 'caregiverData', 'claimData', 'blob']) {
    const decl = CODE.indexOf('const ' + v + ' = storedBlob(');
    const stamp = CODE.indexOf(v + '.updatedBy = session.employee_id');
    if (decl !== -1 && stamp !== -1 && stamp > decl) after++;
    else before.push(v + ' decl=' + decl + ' stamp=' + stamp);
  }
  if (after === 8) {
    ok('D1. all 8 stamps appear AFTER their storedBlob declaration in the '
       + 'source. A stamp written before it would be stripped or overwritten by '
       + 'the payload, and the behaviour arms above would still pass on seven '
       + 'of eight');
  } else {
    bad('D1. every stamp must follow its storedBlob -- ' + after + ' of 8',
        before.join(' | '));
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
