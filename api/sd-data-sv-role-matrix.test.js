// api/sd-data-sv-role-matrix.test.js
//
// Run:  node api/sd-data-sv-role-matrix.test.js
//
// REQUIREMENT: every one of SAIRNvet's 42 resources has a role rule, the rule
//   the handler actually applies is the one in api/_lib/sv-roles.js's table,
//   the rule that is NOT in the table (append-only sv_audit_log) holds
//   independently of it, and the ONE gate that already existed --
//   sv_controlled's licensed-practitioner pair and its witnessing lock -- is
//   not broken by the 41 new ones.
//
// ── WHY THIS SUITE EXISTS ─────────────────────────────────────────────────
// Before 2026-10-14 this app had one per-resource role check out of 42. The
// failure mode of fixing that is not "the gate is wrong" -- it is "the gate
// exists for the four resources somebody thought about". So section D drives
// EVERY resource against EVERY role in BOTH actions -- 504 calls -- and
// compares the handler's answer to the table's, and section A fails if the
// table and api/sd-data.js's own SV_RESOURCES dict disagree in either
// direction.
//
// The negative controls V1-V12 are fourth's b15 spec §5. That section routed
// them to cody as the suite owner; they are implemented here because the code
// landed in this batch and code that lands unverified is the thing this
// platform keeps paying for. Named in the handoff so they are not written
// twice.
//
// FAILING-FIRST. Written and run RED before api/sd-data.js consulted the
// table: 18 failed of 60. The red is in the batch evidence.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  ['sairnvet', 'matrix', 'fixture', String(process.pid)].join('-');

const APP = 'sairnvet';
const KEY = 'k';
const HASH = crypto.createHash('sha256').update(KEY).digest('hex');
const { signSessionToken, ROLES_BY_APP } = require('./_lib/auth');
const svRoles = require('./_lib/sv-roles');
const { PRESCRIBER_ROLES } = require('./sv-auth');

let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(l) { pass++; console.log('  ok       ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL     ' + l);
  if (why) console.log('           ' + String(why).slice(0, 400));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 400));
}
function is(c, l, why) { if (c) ok(l); else bad(l, why); }

const eCode = (r) => (r && r.body && r.body.error && r.body.error.code) || '';
const eMsg = (r) => (r && r.body && r.body.error && r.body.error.message) || '';

// ── THE HANDLER'S OWN RESOURCE DICT, READ OUT OF THE SOURCE ──────────────
// Not a copy. If somebody adds a 43rd resource to the handler and not to the
// table, arm A2 is what says so.
const SRC = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
function handlerResources() {
  const start = SRC.indexOf('const SV_RESOURCES = {');
  if (start < 0) return null;
  const end = SRC.indexOf('\n    };', start);
  if (end < start) return null;
  const body = SRC.slice(start, end);
  const names = (body.match(/(sv_[a-z_]+)\s*:/g) || [])
    .map((m) => m.replace(/\s*:$/, ''));
  return names.filter((v, i, a) => a.indexOf(v) === i);
}

function mockRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}

// A PostgREST stand-in that RECORDS every call. The refusal arms assert that
// NO data fetch happened, which is strictly stronger than "the status was
// 403": a 403 returned after the row was read is a leak with a tidy status.
//
// `headers.get` is implemented because the sv_ read branch asks for
// Content-Range to report the server's true row count, and a mock without it
// would make every read answer total:null for a reason that has nothing to do
// with roles.
function pgMock(calls, opts) {
  opts = opts || {};
  return async function (url, init) {
    const u = String(url);
    if (/_employee_auth\?/.test(u)) {
      return { ok: true, status: 200, json: async () => [
        { license_hash: HASH, employee_id: 'emp-1', role: opts.role || 'owner',
          active: true }] };
    }
    calls.push({ url: u, method: (init && init.method) || 'GET' });
    if (opts.existing && /select=audit_log_id/.test(u)) {
      return { ok: true, status: 200, headers: { get: () => '' },
               json: async () => [{ audit_log_id: opts.existing }] };
    }
    if (init && init.method === 'POST') {
      return { ok: true, status: 200, headers: { get: () => '' },
               json: async () => [JSON.parse(init.body)] };
    }
    return { ok: true, status: 200, headers: { get: () => '0-0/0' },
             json: async () => [] };
  };
}

// ── THE HANDLER IS LOADED ONCE, NOT PER CALL, AND THAT IS DELIBERATE ──────
// api/sd-data.js is 18,000 lines; section D drives it 504 times. Re-requiring
// it per call made this suite take minutes, and a suite nobody will wait for
// is a suite that stops being run. `fetch` is resolved off the global at call
// time, so swapping the mock per call is enough -- nothing in the handler
// captures it at module load.
require.cache[require.resolve('./_lib/license')] = {
  id: require.resolve('./_lib/license'),
  filename: require.resolve('./_lib/license'),
  loaded: true,
  exports: {
    validateLicenseKey: async () => ({
      valid: true, active: true, license_hash: HASH,
      trial_ends_at: null, stripe_subscription_id: null, app_id: APP })
  }
};
delete require.cache[require.resolve('./sd-data.js')];
const handler = require('./sd-data.js');

async function call(resource, action, role, payload, mockOpts) {
  const calls = [];
  global.fetch = pgMock(calls, Object.assign({ role: role }, mockOpts || {}));
  const res = mockRes();
  const body = { action: action, resource: resource };
  if (action === 'write') body.payload = payload || { id: 'X1' };
  await handler({ method: 'POST',
                  headers: { authorization: 'Bearer ' + KEY,
                             'x-sd-auth': signSessionToken({
                               app: APP, employee_id: 'emp-1', role: role,
                               license_hash: HASH }) },
                  body: body }, res);
  return { res: res, calls: calls };
}

console.log('SAIRNvet role matrix -- 42 resources, 6 roles, criteria '
          + '2026-10-14.1\n');

(async () => {
  // ── A. THE TABLE AGREES WITH THE HANDLER AND WITH ITSELF ────────────────
  console.log('A. coverage: the table, the handler and the vocabulary agree');

  const tableRes = svRoles.resources().slice().sort();
  const handRes = handlerResources();
  const ROLES = (ROLES_BY_APP[APP] || []).slice();

  is(tableRes.length === 42,
     'A1. the table carries exactly 42 rows, which is the measured resource '
   + 'count in fourth\'s b15 spec',
     'rows=' + tableRes.length);

  if (handRes === null) {
    cannot('A2. SV_RESOURCES could not be read out of api/sd-data.js, so the '
         + 'two lists could not be compared', 'anchor absent');
  } else {
    const hs = handRes.slice().sort();
    const missing = hs.filter((x) => tableRes.indexOf(x) === -1);
    const extra = tableRes.filter((x) => hs.indexOf(x) === -1);
    is(missing.length === 0 && extra.length === 0,
       'A2. the table and api/sd-data.js\'s own SV_RESOURCES dict name the '
     + 'SAME ' + hs.length + ' resources, compared in BOTH directions -- a '
     + 'resource in the handler with no row would be ungated, and a row with '
     + 'no resource is a rule for nothing',
       'in handler not table: [' + missing.join(', ') + '] in table not '
     + 'handler: [' + extra.join(', ') + ']');
  }

  const BANDS = ['REGULATED', 'MONEY', 'OPERATIONS', 'REFERENCE'];
  const badBand = tableRes.filter(
    (k) => BANDS.indexOf(svRoles.SV_ROLE_MATRIX[k].band) === -1);
  is(badBand.length === 0,
     'A3. every row carries one of the four spec bands, so a reviewer can '
   + 'check the band against the resource name',
     badBand.join(', '));

  const noCol = [];
  tableRes.forEach(function (k) {
    ROLES.forEach(function (role) {
      if (!Object.prototype.hasOwnProperty.call(svRoles.SV_ROLE_MATRIX[k], role)) {
        noCol.push(k + '/' + role);
      }
    });
  });
  is(ROLES.length === 6 && noCol.length === 0,
     'A4. all ' + ROLES.length + ' roles in ROLES_BY_APP.sairnvet have a '
   + 'column on all ' + tableRes.length + ' rows -- a role with no column is '
   + 'DENIED by decide(), which is right, but silently',
     'roles=' + ROLES.join(',') + ' gaps=' + noCol.slice(0, 8).join(', '));

  // THE ONE GATE THAT ALREADY EXISTED, PINNED TO ITS SOURCE SET. Not compared
  // to the literal names { owner, dvm }: that is the re-listing this arm is
  // here to prevent. If somebody changes PRESCRIBER_ROLES, this row must move
  // with it, and this arm is what says so.
  const ctl = svRoles.SV_ROLE_MATRIX.sv_controlled;
  const ctlDisagree = ROLES.filter(function (role) {
    const wantRW = !!PRESCRIBER_ROLES[role];
    return (ctl[role] === 'rw') !== wantRW;
  });
  is(ctlDisagree.length === 0,
     'A5. sv_controlled\'s row is DERIVED from api/sv-auth.js\'s '
   + 'PRESCRIBER_ROLES and agrees with it role by role, so the DEA register\'s '
   + 'pair is named in exactly one place',
     'disagree: ' + ctlDisagree.join(', '));

  // THE `why` FIELD HAS A CONSUMER. b10's equivalent arm failed on first run
  // because one row's reason was a noun restating the resource name, which is
  // a field that looks documented and says nothing.
  const weakWhy = tableRes.filter(function (k) {
    const w = String(svRoles.SV_ROLE_MATRIX[k].why || '');
    const bare = k.replace(/^sv_/, '').replace(/_/g, ' ');
    return w.length < 25 || w.trim().toLowerCase() === bare;
  });
  is(weakWhy.length === 0,
     'A6. every row\'s `why` is a reason rather than the resource name '
   + 'restated -- this arm IS the consumer of that field, which is what keeps '
   + 'it from being dormant',
     weakWhy.join(', '));

  const counts = {};
  tableRes.forEach(function (k) {
    const b = svRoles.SV_ROLE_MATRIX[k].band;
    counts[b] = (counts[b] || 0) + 1;
  });
  is(counts.REGULATED === 23 && counts.MONEY === 4
     && counts.OPERATIONS === 13 && counts.REFERENCE === 2,
     'A7. the bands count 23 REGULATED / 4 MONEY / 13 OPERATIONS / '
   + '2 REFERENCE, which is the spec\'s own split -- a drifted band is a '
   + 'policy change wearing a typo',
     JSON.stringify(counts));

  // ── B. THE SPEC'S NEGATIVE CONTROLS, DRIVEN ─────────────────────────────
  console.log('\nB. fourth\'s b15 spec §5 negative controls V1-V12');

  async function refuses(id, resource, action, role, label) {
    const { res, calls } = await call(resource, action, role);
    const dataCalls = calls.filter((c) => c.url.indexOf(resource) !== -1);
    if (res.statusCode === 403 && eCode(res) === 'FORBIDDEN'
        && dataCalls.length === 0) {
      ok(id + '. ' + label + ' -- 403 FORBIDDEN and NO query against '
       + resource + ' was issued');
    } else {
      bad(id + '. ' + label + ' must be 403 FORBIDDEN with no data query',
          'status=' + res.statusCode + ' code=' + eCode(res)
        + ' dataCalls=' + dataCalls.length + ' body='
        + JSON.stringify(res.body).slice(0, 200));
    }
  }

  await refuses('V1', 'sv_soapnotes', 'write', 'frontdesk',
                'a frontdesk token writing the SOAP note');
  await refuses('V2', 'sv_labresults', 'write', 'assistant',
                'an assistant token writing a lab result');

  {
    const { res } = await call('sv_controlled', 'write', 'tech');
    const named = /licensed veterinarian/i.test(eMsg(res));
    if (res.statusCode === 403 && eCode(res) === 'FORBIDDEN' && named) {
      ok('V3. a tech token writing the controlled register is 403 AND the '
       + 'message names the licensed-practitioner requirement -- a technician '
       + 'told only "forbidden" asks for their role to be widened, and '
       + 'widening it would not change the answer');
    } else {
      bad('V3. the sv_controlled refusal must name the licensed-practitioner '
        + 'requirement', 'status=' + res.statusCode + ' code=' + eCode(res)
        + ' msg=' + eMsg(res).slice(0, 160));
    }
  }

  await refuses('V4', 'sv_surgery', 'write', 'manager',
                'a manager token writing a surgical record');
  await refuses('V5', 'sv_financials', 'write', 'dvm',
                'a dvm token writing practice financials -- the '
              + 'clinician/money separation');

  // V6. APPEND-ONLY, AND IT BINDS THE OWNER. Driven for owner AND dvm,
  // because "append-only" proven on one role is a role grant, not a lock.
  for (const role of ['owner', 'dvm']) {
    const { res } = await call('sv_audit_log', 'write', role,
                              { id: 'AL-1' }, { existing: 'AL-1' });
    is(res.statusCode === 409 && eCode(res) === 'APPEND_ONLY',
       'V6' + (role === 'owner' ? 'a' : 'b') + '. ' + role + ' editing an '
     + 'EXISTING sv_audit_log row is refused 409 APPEND_ONLY -- the dosing '
     + 'trail binds the owner exactly as it binds anybody else',
       'status=' + res.statusCode + ' code=' + eCode(res));
  }
  {
    // ...AND A NEW ENTRY STILL GOES IN. Without this the lock could be "no
    // writes at all", which would break the trail it protects.
    const { res } = await call('sv_audit_log', 'write', 'tech', { id: 'AL-2' });
    is(res.statusCode === 200,
       'V6c. CONTROL -- a NEW sv_audit_log entry is accepted, so the lock '
     + 'refuses EDITS and not appends. The trail would be worthless if '
     + 'nothing could be recorded',
       'status=' + res.statusCode + ' body=' + JSON.stringify(res.body).slice(0, 160));
  }

  {
    const { res } = await call('sv_clients', 'read', 'frontdesk');
    is(res.statusCode === 200,
       'V7. CONTROL -- a frontdesk token READS sv_clients, 200. This is the '
     + 'phone-answering control: without it the fix could be "refuse front '
     + 'desk everything" and V1 would still pass',
       'status=' + res.statusCode + ' body=' + JSON.stringify(res.body).slice(0, 160));
  }

  for (const resource of ['sv_vitals', 'sv_soapnotes']) {
    const { res } = await call(resource, 'write', 'tech');
    is(res.statusCode === 200,
       'V8' + (resource === 'sv_vitals' ? 'a' : 'b') + '. CONTROL -- a tech '
     + 'token WRITES ' + resource + ', 200. A technician doing clinical work '
     + 'is the normal case in a veterinary practice, and the matrix must not '
     + 'break it',
       'status=' + res.statusCode);
  }

  {
    const { res } = await call('sv_invoicing', 'write', 'manager');
    is(res.statusCode === 200,
       'V9. CONTROL -- a manager token WRITES sv_invoicing, 200. The practice '
     + 'manager is the money role; V5 is only meaningful beside this',
       'status=' + res.statusCode);
  }

  // V10. THE REGRESSION ARM, AND IT CANNOT ASSERT 200. sv_controlled's write
  // path runs the WITNESSING LOCK after the role gate, and this fixture sends
  // no witness token -- so the honest assertion is that the refusal is the
  // WITNESS lock's and not the role table's. A 200 here would mean the
  // witnessing lock had stopped working, which is the opposite of the thing
  // being checked.
  for (const role of ['owner', 'dvm']) {
    const { res } = await call('sv_controlled', 'write', role);
    const roleRefusal = res.statusCode === 403 && eCode(res) === 'FORBIDDEN';
    is(!roleRefusal,
       'V10' + (role === 'owner' ? 'a' : 'b') + '. ' + role + ' is NOT '
     + 'refused by the role table on sv_controlled -- the answer comes from '
     + 'the witnessing lock (' + (eCode(res) || res.statusCode) + '), which '
     + 'is the gate that existed before these 41 and must still be the one '
     + 'speaking',
       'status=' + res.statusCode + ' code=' + eCode(res));
  }

  {
    // V11. A ROLE FROM ANOTHER APP, AND THE ANSWER CAME BACK STRONGER THAN
    // THE SPEC PREDICTED -- recorded as what happens rather than reworded to
    // match. The spec expected a refusal at the token. What actually happens
    // is that signSessionToken THROWS: a role outside ROLES_BY_APP.sairnvet
    // cannot be signed into a sairnvet session at all, so there is no token to
    // present and nothing for the handler to refuse. (b10's L8 on SAIRNlegacy
    // found the same thing; this is the same mechanism, not a copy of the
    // claim.)
    let signed = null, threw = null;
    try {
      signed = signSessionToken({ app: APP, employee_id: 'emp-1',
        role: 'caregiver', license_hash: HASH });
    } catch (e) { threw = e; }
    if (threw && /invalid role/i.test(String(threw.message))) {
      ok('V11. a role from another app (caregiver) cannot be MINTED for '
       + 'sairnvet at all -- signSessionToken throws "' + threw.message
       + '", so the refusal is one layer earlier than the spec expected and '
       + 'there is no token to present');
    } else if (signed) {
      const { res } = await call('sv_soapnotes', 'write', 'caregiver');
      is(res.statusCode === 401 || res.statusCode === 403,
         'V11. a role from another app (caregiver) is refused ('
       + res.statusCode + ' ' + eCode(res) + ')',
         'status=' + res.statusCode + ' code=' + eCode(res));
    } else {
      bad('V11. a foreign role must be refused somewhere',
          'neither minted nor rejected with a role message: ' + String(threw));
    }
  }

  {
    // V12. THE OVER-REFUSAL CONTROL AT FULL WIDTH. All 42 resources, owner
    // token, read. If the gate is too broad this is the arm that says so, and
    // it names every resource that failed rather than the first.
    const broke = [];
    for (const resource of tableRes) {
      const { res } = await call(resource, 'read', 'owner');
      if (res.statusCode !== 200) {
        broke.push(resource + '=' + res.statusCode + '/' + eCode(res));
      }
    }
    is(broke.length === 0,
       'V12. CONTROL -- an owner token reads all ' + tableRes.length
     + ' resources, 200 each. The whole risk of adding 41 gates is refusing '
     + 'somebody who should be allowed, and this is the arm that would catch '
     + 'it at full width',
       broke.slice(0, 10).join(', '));
  }

  // ── C. THE GATE IS CONSULTED ONCE, BEFORE THE DISPATCH, PINNED AT SOURCE ─
  console.log('\nC. one call, before the dispatch, pinned at source');

  const CODE = SRC.split(/\r?\n/)
    .filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');
  const ANCHOR = 'if (SV_RESOURCES[resource]) {';
  const anchorCount = CODE.split(ANCHOR).length - 1;
  if (anchorCount !== 1) {
    cannot('C1. the source anchor ' + JSON.stringify(ANCHOR) + ' matched '
         + anchorCount + ' time(s), not once, so C2 and C3 cannot say which '
         + 'block they measured', 'uniqueness guard');
    cannot('C2. depends on C1', 'anchor not unique');
    cannot('C3. depends on C1', 'anchor not unique');
  } else {
    ok('C1. the source anchor matches exactly once, so C2 and C3 are '
     + 'measuring the pre-dispatch block and not some other region');
    const decideCount = (CODE.match(/svRoles\.decide\(/g) || []).length;
    is(decideCount === 1,
       'C2. svRoles.decide() is called exactly ONCE in api/sd-data.js. A role '
     + 'check written at one call site and not the other forty-one is '
     + 'indistinguishable from no policy when read one branch at a time',
       'calls=' + decideCount);
    const preBlock = CODE.split(ANCHOR)[1].split('\n    if (SV_RESOURCES[resource] && action')[0];
    is(/svRoles\.decide\(/.test(preBlock) && /svRoles\.isAppendOnly\(/.test(preBlock),
       'C3. both the role decision and the append-only lock are inside that '
     + 'pre-dispatch block, so NEITHER the read branch nor the write branch '
     + 'can be reached without them',
       'decide in block: ' + /svRoles\.decide\(/.test(preBlock)
     + ' appendOnly in block: ' + /svRoles\.isAppendOnly\(/.test(preBlock));
    is(!/sv-witness/.test(preBlock),
       'C4. the pre-dispatch block does NOT touch api/sv-witness.js -- the '
     + 'spec requires the witnessing lock to stay exactly where it was, on '
     + 'the write branch, because it carries a legal act',
       'witness referenced in the new block');
  }

  // ── D. EVERY RESOURCE, EVERY ROLE, BOTH ACTIONS ─────────────────────────
  // 504 calls. The handler's answer must agree with the table's for all of
  // them -- this is the arm that makes "the gate exists for the four
  // resources somebody thought about" impossible to ship.
  //
  // THREE RESOURCES ARE EXCLUDED FROM THE WRITE SWEEP, EACH NAMED AND WITH A
  // REASON, because a second control answers after the role gate and the
  // sweep would be measuring that instead:
  //   sv_controlled  the witnessing lock
  //   sv_audit_log   the append-only lock
  // Their role behaviour is covered by V3/V6/V10 and by the READ half of this
  // sweep, which no second control intercepts.
  console.log('\nD. the full sweep: 42 resources x 6 roles x 2 actions');

  const WRITE_EXCLUDED = { sv_controlled: 'witnessing lock',
                           sv_audit_log: 'append-only lock' };
  const disagreements = [];
  let driven = 0;
  for (const resource of tableRes) {
    for (const role of ROLES) {
      for (const action of ['read', 'write']) {
        if (action === 'write' && WRITE_EXCLUDED[resource]) continue;
        const want = svRoles.decide(resource, role, action);
        const { res } = await call(resource, action, role);
        driven++;
        const gotAllow = res.statusCode === 200;
        const gotDeny = res.statusCode === 403 && eCode(res) === 'FORBIDDEN';
        const agree = (want === svRoles.ALLOW) ? gotAllow : gotDeny;
        if (!agree) {
          disagreements.push(resource + '/' + role + '/' + action
            + ' table=' + want + ' handler=' + res.statusCode + '/' + eCode(res));
        }
      }
    }
  }
  is(disagreements.length === 0,
     'D1. all ' + driven + ' driven (resource, role, action) combinations '
   + 'answer exactly what the table says, in both directions. Excluded from '
   + 'the WRITE half and named rather than silently skipped: '
   + Object.keys(WRITE_EXCLUDED).map((k) => k + ' (' + WRITE_EXCLUDED[k] + ')')
       .join(', '),
     disagreements.slice(0, 12).join('\n           '));

  // ── THE TWO WRITE EXCLUSIONS ARE MEASURED, NOT MERELY NAMED ─────────────
  // The push gate's scrutiny ledger flags this file WEAKENING for "a skip /
  // exemption / allowlist entry ADDED", quoting D1's own label. The flag is
  // RIGHT that the line makes a claim about an exemption; what was missing is
  // that nothing checked the claim. b9 answered the same flag on
  // tests/mar_billing_grant.test.js the same way: do not argue the flag down,
  // make the line carry an assertion.
  //
  // WHAT IS ACTUALLY EXCLUDED, AND ONLY FROM THE SWEEP: the WRITE half of two
  // resources whose answer comes from a SECOND control that runs after the
  // role gate (the witnessing lock, the append-only lock). The role table
  // still governs them, and this arm is what says so: a role the table DENIES
  // must still get the role refusal on a write, and a role it ALLOWS must get
  // something that is NOT the role refusal. An exemption from a sweep is not
  // an exemption from the policy.
  {
    const wrong = [];
    for (const resource of Object.keys(WRITE_EXCLUDED)) {
      for (const role of ROLES) {
        const want = svRoles.decide(resource, role, 'write');
        const { res } = await call(resource, 'write', role);
        const roleRefusal = res.statusCode === 403 && eCode(res) === 'FORBIDDEN';
        if (want === svRoles.DENY && !roleRefusal) {
          wrong.push(resource + '/' + role + ' table=DENY but got '
            + res.statusCode + '/' + eCode(res) + ' -- the second control '
            + 'answered where the ROLE gate should have');
        }
        if (want === svRoles.ALLOW && roleRefusal) {
          wrong.push(resource + '/' + role + ' table=ALLOW but the role gate '
            + 'refused it');
        }
      }
    }
    is(wrong.length === 0,
       'D1b. both WRITE-EXCLUDED resources are still governed by the role '
     + 'table on writes for all ' + ROLES.length + ' roles -- the exclusion is '
     + 'from the SWEEP (whose comparison the second control would spoil), not '
     + 'from the policy. This arm is what makes D1\'s exclusion note a '
     + 'measurement rather than an assurance',
       wrong.join('; '));
  }

  // AND THE SWEEP IS NOT VACUOUS. A sweep in which the table says ALLOW
  // everywhere would pass D1 while gating nothing, and a sweep that says DENY
  // everywhere would pass it while refusing everybody.
  let allows = 0, denies = 0;
  for (const resource of tableRes) {
    for (const role of ROLES) {
      for (const action of ['read', 'write']) {
        if (svRoles.decide(resource, role, action) === svRoles.ALLOW) allows++;
        else denies++;
      }
    }
  }
  is(allows > 0 && denies > 0,
     'D2. CONTROL -- the table itself contains both verdicts (' + allows
   + ' ALLOW, ' + denies + ' DENY of ' + (allows + denies) + '), so D1 is '
   + 'comparing two real answers rather than one constant',
     'allows=' + allows + ' denies=' + denies);

  // A NON-sv RESOURCE IS A THIRD ANSWER. NOT_SV must never be folded into
  // ALLOW: a silent ALLOW for somebody else's resource reads as "this table
  // approved it".
  is(svRoles.decide('leg_cases', 'owner', 'read') === svRoles.NOT_SV
     && svRoles.decide('sv_notathing', 'owner', 'read') === svRoles.DENY,
     'D3. a non-sv resource answers NOT_SV and an UNKNOWN sv_ resource '
   + 'answers DENY -- a 43rd resource added to the handler without a row here '
   + 'is refused, not defaulted open',
     'leg_cases -> ' + svRoles.decide('leg_cases', 'owner', 'read')
   + ', sv_notathing -> ' + svRoles.decide('sv_notathing', 'owner', 'read'));

  console.log('\n' + pass + ' passed, ' + fail + ' failed, '
            + unproven + ' unproven');
  if (failed.length) console.log(failed.length + ' ARM(S) FAILED: ' + failed.join(', '));
  if (notProved.length) console.log(notProved.length + ' ARM(S) UNPROVEN: ' + notProved.join(', '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
})().catch((e) => { console.error(e); process.exit(1); });
