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
// ALL FIFTEEN ARE FIXED HERE, in three passes and the order is the record:
//   8  the rows built on a `const x = storedBlob(` line of its own.
//   5  the SAIRNsenior rows built as `const xBody = Object.assign(storedBlob(
//      ...), {...})` -- missed by the first scan because of MY pattern, not a
//      property of the code.
//   2  the SAIRNroofing pair recorded as BLOCKED on a data-loss hazard. The
//      hazard was real for ONE of them. `rf_claims/write` does send `data` and
//      took the same one-line stamp; `rf_schedule/set_status` does not and
//      took a read-then-merge onto the row it already reads.
// `scratchpad/attr_scan.py` re-run at this state: UNATTRIBUTED 0 of 49.
// NONE of the fifteen needed the audit-table migration -- that migration is
// about AUDIT tables, and all fifteen of these are DATA tables.
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
  // ── THE FIVE ADDED 2026-10-07 ────────────────────────────────────────
  // These build their row as `const xBody = Object.assign(storedBlob(...),
  // {...})` rather than on a `const x = storedBlob(...)` line of its own,
  // which is why the first scan did not see them as stampable. The stamp
  // goes in as the LAST argument to Object.assign: sources apply left to
  // right, so a later one wins, and a caller-supplied updatedBy that
  // survived storedBlob is overwritten there.
  { res: 'sen_branches', app: 'sairnsenior', role: 'owner', table: 'sen_branches' },
  { res: 'sen_payer_contracts', app: 'sairnsenior', role: 'owner', table: 'sen_payer_contracts' },
  { res: 'sen_authorizations', app: 'sairnsenior', role: 'owner', table: 'sen_authorizations' },
  { res: 'sen_pay_rates', app: 'sairnsenior', role: 'owner', table: 'sen_pay_rates' },
  { res: 'sen_franchise_agreements', app: 'sairnsenior', role: 'owner', table: 'sen_franchise_agreements' },
  // ── THE LAST TWO OF THE SEVEN, ADDED 2026-10-07 ──────────────────────
  // These were recorded as BLOCKED on a data-loss hazard: "neither sends
  // `data`, so stamping would REPLACE the stored blob". Re-read at HEAD,
  // that is true of ONE of them and FALSE of the other.
  //
  //   rf_claims/write        DOES send `data: dataBlob` (sd-data.js:7772),
  //                          built from the whole payload via storedBlob.
  //                          It takes the SAME one-line stamp as the five
  //                          above. The refusal belonged to the other path.
  //   rf_schedule/set_status genuinely does not -- it PATCHes two scalar
  //                          columns. It takes a READ-THEN-MERGE onto the
  //                          row the branch ALREADY reads for its gate, so
  //                          the window/notes blob survives. `created_by`
  //                          is not usable (it is `not null` and means who
  //                          CREATED the day); a `status_changed_by` column
  //                          would be cleaner and is a MIGRATION.
  { res: 'rf_claims', app: 'sairnroofing', role: 'owner', table: 'rf_claims' },
  { res: 'rf_schedule', app: 'sairnroofing', role: 'owner', table: 'rf_schedule',
    action: 'set_status' },
];

// One permissive payload. Branch preconditions differ; the fields they ask for
// are supplied together so a 400 on a missing id does not masquerade as a
// missing stamp. THE HOSTILE VALUES ARE THE POINT of arm C.
function payloadFor(res) {
  const p = {
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
    // ── THE SAIRNsenior VALIDATORS, READ OFF THEIR OWN REFUSALS ─────────
    // Five fields added because five branches 400ed on the first run and
    // arm A1 caught every one. The messages were READ, not guessed at:
    //   sen_payer_contracts      payer, rate_per_hour > 0, effective_on
    //   sen_authorizations       auth_number, units_authorized > 0,
    //                            minutes_per_unit in 15/30/60, start_on, end_on
    //   sen_pay_rates            rate_per_hour > 0, effective_on
    //   sen_franchise_agreements branch_id, royalty_base in billed/collected,
    //                            effective_on
    // `royalty_base` has NO DEFAULT on purpose -- the handler says so:
    // "there is no default, because guessing picks a side of the agreement".
    payer: 'A Payer', rate_per_hour: 42, effective_on: '2026-01-01',
    auth_number: 'AUTH-1', units_authorized: 10, minutes_per_unit: 30,
    start_on: '2026-01-01', end_on: '2026-12-31',
    branch_id: 'BR-1', royalty_base: 'billed',
    // `state` for sen_branches -- its validator says why: "It is what a
    // per-state EVV or training rule is matched on."
    state: 'OH',
    // `employee_id` for sen_pay_rates is the SUBJECT of the rate -- WHOSE
    // pay it is -- and NOT the actor. The actor is the session, which is
    // the whole distinction this suite exists to pin: arm C1 proves the
    // caller cannot supply the actor, while this field is a legitimate
    // caller-supplied subject and must keep working.
    employee_id: 'SUBJECT-EMP-1',
    updatedBy: 'SOMEONE-ELSE', updatedByRole: 'owner'
  };
  // ── PER-RESOURCE EXTRAS, NOT ADDED TO THE SHARED PAYLOAD ─────────────
  // `status` is the reason this is per-resource rather than global.
  // rf_schedule/set_status requires one from SCHEDULE_STATUSES
  // (roofing-locations.js:56) and rf_claims validates its own against
  // CLAIM_STATUSES (roofing-claims.js:41). The two lists are DISJOINT, so
  // one shared `status` would 400 the other branch -- and a branch that
  // 400s before it builds a row is exactly the vacuous pass arm A1 exists
  // to catch.
  if (res === 'rf_claims') {
    // validateClaim (roofing-claims.js:133) requires id, job_id, carrier,
    // claim_number. `status` deliberately OMITTED so the handler's own
    // default ('loss_reported') applies.
    p.job_id = 'JOB-1';
    p.carrier = 'A Carrier';
    p.claim_number = 'CLM-0001';
  }
  if (res === 'rf_schedule') {
    p.schedule_id = 'RFSCH-1';
    p.status = 'confirmed';
  }
  return p;
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
  // `c.action` defaults to 'write'. rf_schedule's attribution gap is on
  // 'set_status', a PATCH -- a suite that can only drive 'write' cannot see it.
  const req = { method: 'POST', headers: headers, body: {
    action: c.action || 'write', resource: c.res, payload: payloadFor(c.res) } };
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

  console.log('A. EVERY ONE OF THE ' + CASES.length + ' REACHES ITS WRITE');
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

  // ── D2: THE SEVEN Object.assign STAMPS, PINNED THE SAME WAY ──────────
  // D1 pins the `x.updatedBy = session.employee_id` spelling the first eight
  // use. The seven added since are stamped as the LAST ARGUMENT to an
  // Object.assign, which D1's string cannot see at all -- so without this arm
  // seven of fifteen stamps are behaviour-tested and NOT source-pinned, and a
  // future edit that moves one to the FIRST argument would keep every B and C
  // arm green while the payload silently won again.
  //
  // The assertion is ORDER WITHIN THE STATEMENT: the stamp text must appear
  // AFTER the `storedBlob(` call that builds the row it lands on.
  const ASSIGN_STAMPED = [
    { v: 'brBody', res: 'sen_branches' },
    { v: 'pcBody', res: 'sen_payer_contracts' },
    { v: 'azBody', res: 'sen_authorizations' },
    { v: 'prBody', res: 'sen_pay_rates' },
    { v: 'frBody', res: 'sen_franchise_agreements' },
    { v: 'dataBlob', res: 'rf_claims' },
  ];
  const STAMP = '{ updatedBy: session.employee_id, updatedByRole: session.role }';
  let assignOk = 0;
  const assignBad = [];
  for (const a of ASSIGN_STAMPED) {
    const decl = CODE.indexOf('const ' + a.v + ' = Object.assign(');
    if (decl === -1) { assignBad.push(a.v + ' decl not found'); continue; }
    // The next `const ` declaration bounds the statement, so a stamp belonging
    // to a LATER branch cannot be miscounted as this one's.
    let end = CODE.indexOf('\n      const ', decl + 1);
    if (end === -1) end = CODE.length;
    const stmt = CODE.slice(decl, end);
    const sb = stmt.indexOf('storedBlob(');
    const st = stmt.indexOf(STAMP);
    if (sb !== -1 && st !== -1 && st > sb) assignOk++;
    else assignBad.push(a.v + ' storedBlob=' + sb + ' stamp=' + st);
  }
  if (assignOk === ASSIGN_STAMPED.length) {
    ok('D2. all ' + ASSIGN_STAMPED.length + ' Object.assign stamps are the LAST '
       + 'source, after their storedBlob. Object.assign applies sources left to '
       + 'right, so this ordering -- not the presence of the field -- is what '
       + 'makes a caller-supplied updatedBy lose');
  } else {
    bad('D2. every Object.assign stamp must follow its storedBlob -- '
        + assignOk + ' of ' + ASSIGN_STAMPED.length, assignBad.join(' | '));
  }

  // ── D3: rf_schedule/set_status PRESERVES THE BLOB IT MERGES INTO ─────
  // The ONE path that could not take the one-line stamp. The hazard being
  // guarded is not a missing field -- it is `data: { updatedBy }` REPLACING a
  // blob that holds the window and notes. So the arm asserts the existing blob
  // is spread FIRST and the stamp lands after it.
  const merge = CODE.indexOf('const schedBlob = Object.assign({}, entry.data || {}');
  const mergeStamp = CODE.indexOf(STAMP, merge === -1 ? 0 : merge);
  if (merge !== -1 && mergeStamp > merge && CODE.indexOf('data: schedBlob') !== -1) {
    ok('D3. rf_schedule/set_status spreads the STORED blob first, stamps after '
       + 'it, and PATCHes the merged value. A bare `data: { updatedBy }` here '
       + 'would pass every B and C arm above while destroying the window and '
       + 'notes on every status change');
  } else {
    bad('D3. rf_schedule/set_status must merge onto the stored blob',
        'merge=' + merge + ' stamp=' + mergeStamp
        + ' patches=' + (CODE.indexOf('data: schedBlob') !== -1));
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
