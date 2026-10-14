// api/sd-data-leg-role-matrix.test.js
//
// Run:  node api/sd-data-leg-role-matrix.test.js
//
// REQUIREMENT: every one of SAIRNlegacy's 36 resources has a role rule, the
//   rule the handler actually applies is the one in the table, and the two
//   rules that are NOT in the table (append-only custody, the deterministic
//   aftercare key) hold independently of it.
//
// ── WHY THIS SUITE EXISTS ─────────────────────────────────────────────────
// Before 2026-10-14 this app had zero per-resource role checks. The failure
// mode of fixing that is not "the gate is wrong" -- it is "the gate exists for
// the four resources somebody thought about". So the arms below are generated
// FROM the table and FROM api/sd-data.js's own LEG_RESOURCES dict, never from
// a hand-written list, and section A fails if the two disagree in either
// direction.
//
// The negative controls L1-L10 are fourth's b15 spec §5. That section routed
// them to cody as the suite owner; they are implemented here because the code
// landed in this batch and code that lands unverified is the thing this
// platform keeps paying for. Named in the handoff so they are not written
// twice.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  ['sairnlegacy', 'matrix', 'fixture', String(process.pid)].join('-');

const APP = 'sairnlegacy';
const KEY = 'k';
const HASH = crypto.createHash('sha256').update(KEY).digest('hex');
const { signSessionToken, ROLES_BY_APP } = require('./_lib/auth');
const legRoles = require('./_lib/leg-roles');

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
// Not a copy. If somebody adds a 37th resource to the handler and not to the
// table, arm A2 is what says so.
function handlerResources() {
  const src = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
  const start = src.indexOf('const LEG_RESOURCES = {');
  if (start < 0) return null;
  const end = src.indexOf('\n    };', start);
  if (end < start) return null;
  const body = src.slice(start, end);
  const names = (body.match(/(leg_[a-z_]+)\s*:/g) || [])
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
function pgMock(calls, opts) {
  opts = opts || {};
  return async function (url, init) {
    const u = String(url);
    if (/_employee_auth\?/.test(u)) {
      return { ok: true, status: 200, json: async () => [
        { license_hash: HASH, employee_id: 'emp-1', role: 'owner', active: true }] };
    }
    calls.push({ url: u, method: (init && init.method) || 'GET' });
    if (opts.existing && /select=custodylog_id/.test(u)) {
      return { ok: true, status: 200,
               json: async () => [{ custodylog_id: opts.existing }] };
    }
    if (init && init.method === 'POST') {
      return { ok: true, status: 200, json: async () => [JSON.parse(init.body)] };
    }
    return { ok: true, status: 200, json: async () => [] };
  };
}

function loadHandler(fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: HASH,
        trial_ends_at: null, stripe_subscription_id: null, app_id: APP })
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

async function call(resource, action, role, payload, mockOpts) {
  const calls = [];
  const h = loadHandler(pgMock(calls, mockOpts));
  const res = mockRes();
  const body = { action: action, resource: resource };
  if (action === 'write') body.payload = payload || { id: 'X1' };
  await h({ method: 'POST',
            headers: { authorization: 'Bearer ' + KEY,
                       'x-sd-auth': signSessionToken({
                         app: APP, employee_id: 'emp-1', role: role,
                         license_hash: HASH }) },
            body: body }, res);
  return { res: res, calls: calls };
}

console.log('SAIRNlegacy role matrix -- 36 resources, 8 roles, criteria '
          + '2026-10-14.1\n');

(async () => {
  // ── A. THE TABLE IS COMPLETE AND AGREES WITH THE HANDLER ────────────────
  console.log('A. completeness -- no resource without a rule, in either '
            + 'direction');

  const inHandler = handlerResources();
  const inTable = legRoles.resources();
  if (inHandler === null) {
    cannot('A1. LEG_RESOURCES could not be located in api/sd-data.js, so '
         + 'completeness was not measured', 'anchor absent');
    cannot('A2. depends on A1', 'see A1');
  } else {
    is(inHandler.length === 36 && inTable.length === 36,
       'A1. the handler dispatches 36 leg_ resources and the table carries 36 '
     + 'rows',
       'handler=' + inHandler.length + ' table=' + inTable.length);
    const missing = inHandler.filter((r) => inTable.indexOf(r) === -1);
    const extra = inTable.filter((r) => inHandler.indexOf(r) === -1);
    is(missing.length === 0 && extra.length === 0,
       'A2. every resource the handler dispatches has a row, and every row is '
     + 'a resource the handler dispatches -- READ from the source, not a '
     + 'hand-written list',
       'no row: ' + JSON.stringify(missing) + ' no resource: ' + JSON.stringify(extra));
  }

  const VOCAB = ROLES_BY_APP[APP];
  is(Array.isArray(VOCAB) && VOCAB.length === 8 && VOCAB.indexOf('staff') !== -1,
     'A3. ROLES_BY_APP.sairnlegacy carries 8 roles and `staff` is STILL among '
   + 'them -- removing it would invalidate every existing credential row',
     JSON.stringify(VOCAB));

  const uncovered = inTable.filter(function (r) {
    const row = legRoles.LEG_ROLE_MATRIX[r];
    return VOCAB.some((role) => !Object.prototype.hasOwnProperty.call(row, role));
  });
  is(uncovered.length === 0,
     'A4. every row names every role in the vocabulary. A role with no column '
   + 'is denied by decide(), which is right, but silently -- this arm is what '
   + 'makes an omission visible',
     JSON.stringify(uncovered));

  const bands = {};
  inTable.forEach((r) => {
    const b = legRoles.LEG_ROLE_MATRIX[r].band;
    bands[b] = (bands[b] || 0) + 1;
  });
  is(bands.REGULATED === 9 && bands.MONEY === 15 && bands.OPERATIONS === 12,
     'A5. the bands are 9 REGULATED / 15 MONEY / 12 OPERATIONS, as specified. '
   + 'A band count that drifts is a resource that moved band without anyone '
   + 'deciding to move it',
     JSON.stringify(bands));

  // ── B. THE MIGRATION ARM, WHICH IS THE EXPENSIVE ONE TO GET WRONG ───────
  console.log('\nB. `staff` is deprecated to the NARROWEST band, not promoted');

  const moneyRows = inTable.filter((r) => legRoles.LEG_ROLE_MATRIX[r].band === 'MONEY');
  const staffMoney = moneyRows.filter((r) => legRoles.decide(r, 'staff', 'read') === legRoles.ALLOW);
  is(staffMoney.length === 0,
     'B1. THE ARM THAT PROTECTS A LIVE PRACTICE -- `staff` gets NOTHING on any '
   + 'of the 15 MONEY resources, not even read. Mapping the deprecated role to '
   + '`arranger` would have granted all 15 to everyone who had a login '
   + 'yesterday',
     JSON.stringify(staffMoney));

  const regRows = inTable.filter((r) => legRoles.LEG_ROLE_MATRIX[r].band === 'REGULATED');
  const staffRegWrite = regRows.filter((r) => legRoles.decide(r, 'staff', 'write') === legRoles.ALLOW);
  is(staffRegWrite.length === 0,
     'B2. `staff` cannot WRITE any REGULATED resource',
     JSON.stringify(staffRegWrite));

  const opsRows = inTable.filter((r) => legRoles.LEG_ROLE_MATRIX[r].band === 'OPERATIONS');
  const staffOps = opsRows.filter((r) => legRoles.decide(r, 'staff', 'write') === legRoles.ALLOW);
  is(staffOps.length === opsRows.length,
     'B3. CONTROL -- `staff` keeps read+write on all 12 OPERATIONS resources. '
   + 'Without this arm, "staff is narrowed" is satisfied by a migration that '
   + 'locks every existing employee out of the app entirely',
     staffOps.length + ' of ' + opsRows.length);

  // ── C. FAIL-CLOSED, IN EVERY DIRECTION ──────────────────────────────────
  console.log('\nC. decide() fails closed');

  is(legRoles.decide('leg_notatable', 'owner', 'read') === legRoles.DENY,
     'C1. a NEW leg_ resource with no row is DENIED, not allowed by default -- '
   + 'the exact state this table exists to end',
     legRoles.decide('leg_notatable', 'owner', 'read'));
  is(legRoles.decide('sd_jobs', 'owner', 'read') === legRoles.NOT_LEG,
     'C2. a non-leg resource answers NOT_LEG, a third state never folded into '
   + 'ALLOW -- a silent ALLOW here would read as "this table approved it"',
     legRoles.decide('sd_jobs', 'owner', 'read'));
  is(legRoles.decide('leg_bookings', 'embalmer', 'read') === legRoles.DENY
     && legRoles.decide('leg_bookings', '', 'read') === legRoles.DENY
     && legRoles.decide('leg_bookings', null, 'read') === legRoles.DENY,
     'C3. a role outside the row, an empty role and a null role are all DENY',
     'embalmer=' + legRoles.decide('leg_bookings', 'embalmer', 'read'));
  is(legRoles.decide('leg_deathrecords', 'arranger', 'soft_delete') === legRoles.DENY,
     'C4. an unknown VERB is treated as write-class, so a future action cannot '
   + 'slip through on a read grant (arranger has read on leg_deathrecords)',
     legRoles.decide('leg_deathrecords', 'arranger', 'soft_delete'));
  is(legRoles.decide('leg_bookings', 'constructor', 'read') === legRoles.DENY
     && legRoles.decide('constructor', 'owner', 'read') === legRoles.NOT_LEG,
     'C5. prototype keys are not roles and not resources -- the table is built '
   + 'on a null prototype, so `constructor` is not a truthy row',
     'role=' + legRoles.decide('leg_bookings', 'constructor', 'read')
     + ' resource=' + legRoles.decide('constructor', 'owner', 'read'));

  // ── D. THE SPEC'S NEGATIVE CONTROLS, AGAINST THE REAL HANDLER ───────────
  console.log('\nD. spec §5 negative controls L1-L10, driven end to end');

  const L = [
    ['L1', 'leg_invoices', 'write', 'staff', 403, 'a deprecated staff token writes an invoice'],
    ['L2', 'leg_deathrecords', 'read', 'livery', 403, 'a livery token reads death records'],
    ['L3', 'leg_cremations', 'write', 'apprentice', 403, 'an apprentice writes a cremation authorisation'],
    ['L4', 'leg_custodylog', 'write', 'office', 403, 'an office token writes the custody log'],
    ['L6', 'leg_cremations', 'write', 'director', 200, 'CONTROL -- a director writes a cremation authorisation'],
    ['L7', 'leg_invoices', 'write', 'arranger', 200, 'CONTROL -- an arranger writes an invoice'],
    ['L7b', 'leg_documents', 'read', 'arranger', 200, 'CONTROL -- an arranger reads documents']
  ];
  for (const t of L) {
    const r = await call(t[1], t[2], t[3]);
    const got = r.res.statusCode;
    if (t[4] === 403) {
      is(got === 403 && eCode(r.res) === 'FORBIDDEN'
         && eMsg(r.res).indexOf(t[3]) !== -1 && r.calls.length === 0,
         t[0] + '. ' + t[5] + ' -> 403, the body NAMES THE ROLE, and NO data '
       + 'fetch happened',
         got + ' ' + eCode(r.res) + ' / ' + eMsg(r.res)
         + ' / calls=' + r.calls.length);
    } else {
      is(got === 200,
         t[0] + '. ' + t[5] + ' -> 200',
         got + ' ' + eCode(r.res) + ' ' + eMsg(r.res));
    }
  }

  // L5 -- append-only, and it binds the OWNER. Two arms: a NEW entry from the
  // owner is accepted, an EDIT of an existing one is refused.
  const newEntry = await call('leg_custodylog', 'write', 'owner', { id: 'CL-NEW' });
  is(newEntry.res.statusCode === 200,
     'L5a. CONTROL -- an owner APPENDS a new custody entry and it is accepted. '
   + 'Append-only must not mean read-only, or the log stops being written',
     newEntry.res.statusCode + ' ' + eMsg(newEntry.res));

  const edit = await call('leg_custodylog', 'write', 'owner', { id: 'CL-1' },
                          { existing: 'CL-1' });
  is(edit.res.statusCode === 409 && eCode(edit.res) === 'APPEND_ONLY'
     && !edit.calls.some((c) => c.method === 'POST'),
     'L5. THE OWNER EDITING AN EXISTING CUSTODY ROW IS REFUSED 409 APPEND_ONLY '
   + 'and no upsert is sent. A chain-of-custody log that can be edited is not '
   + 'a chain of custody, and no role grant reaches past this',
     edit.res.statusCode + ' ' + eCode(edit.res)
     + ' methods=' + JSON.stringify(edit.calls.map((c) => c.method)));

  const editDirector = await call('leg_custodylog', 'write', 'director',
                                  { id: 'CL-1' }, { existing: 'CL-1' });
  is(editDirector.res.statusCode === 409 && eCode(editDirector.res) === 'APPEND_ONLY',
     'L5b. ...and a director too -- the rule is not owner-specific',
     editDirector.res.statusCode + ' ' + eCode(editDirector.res));

  // L8 -- a role string outside the vocabulary. MEASURED STRONGER THAN THE
  // SPEC EXPECTED: the spec said "refused at the token, by
  // verifySessionToken". It is refused one step EARLIER than that -- a token
  // for such a role CANNOT BE MINTED AT ALL, so there is nothing to present.
  // Recorded as what actually happens rather than reworded to match the
  // prediction.
  let l8err = null;
  try {
    signSessionToken({ app: APP, employee_id: 'emp-1', role: 'embalmer',
                       license_hash: HASH });
  } catch (e) { l8err = e; }
  is(l8err && /invalid role/i.test(l8err.message),
     'L8. a role string not in the vocabulary (`embalmer`) cannot even be '
   + 'SIGNED into a token -- refused one step earlier than the spec predicted, '
   + 'so no request carrying it can exist',
     l8err ? l8err.message : 'signSessionToken ACCEPTED an unknown role');

  // L9 -- a role valid in ANOTHER app, presented against sairnlegacy. The
  // token is real and correctly signed; what refuses it is the app scope.
  const l9calls = [];
  const l9h = loadHandler(pgMock(l9calls));
  const l9res = mockRes();
  await l9h({ method: 'POST',
              headers: { authorization: 'Bearer ' + KEY,
                         'x-sd-auth': signSessionToken({
                           app: 'sairncare', employee_id: 'emp-1',
                           role: 'nursing', license_hash: HASH }) },
              body: { action: 'read', resource: 'leg_bookings' } }, l9res);
  is(l9res.statusCode === 401 && l9calls.length === 0,
     'L9. a VALID, correctly signed session for another app (`nursing`, '
   + 'SAIRNcare) is refused 401 on a leg_ resource and no data is fetched -- '
   + 'the cross-app vocabulary leak is closed by the app scope, not by this '
   + 'table',
     l9res.statusCode + ' ' + eCode(l9res) + ' calls=' + l9calls.length);

  // L10 -- THE OVER-REFUSAL CONTROL. Every one of the 36, owner token.
  // A matrix that locks an owner out of their own app is a matrix somebody
  // switches off by Friday.
  console.log('\nL10. CONTROL -- all 36 resources, owner token, read AND write');
  // THE TWO BOOKING RESOURCES NEED A VALID WINDOW, and that is not a
  // concession -- it is the distinction this arm has to keep. `{id:'X1'}` on
  // leg_bookings is a 400 from the overlap gate's own field validation, which
  // is CORRECT and has nothing to do with the role matrix. Feeding them a
  // real payload is what makes "the owner is not refused" mean the role
  // matrix did not refuse them, rather than "no refusal of any kind occurs".
  const OWNER_PAYLOAD = {
    leg_bookings: { id: 'X1', facility_id: 'FC-1',
                    start_time: '2026-12-01T10:00:00.000Z',
                    end_time: '2026-12-01T11:00:00.000Z' },
    leg_clergybookings: { id: 'X1', clergy_id: 'CG-1',
                          start_time: '2026-12-01T10:00:00.000Z',
                          end_time: '2026-12-01T11:00:00.000Z' }
  };
  const ownerFails = [];
  for (const r of inTable) {
    const rd = await call(r, 'read', 'owner');
    if (rd.res.statusCode !== 200) ownerFails.push(r + '/read:' + rd.res.statusCode);
    const wr = await call(r, 'write', 'owner', OWNER_PAYLOAD[r] || { id: 'X1' });
    if (wr.res.statusCode !== 200) ownerFails.push(r + '/write:' + wr.res.statusCode);
  }
  is(ownerFails.length === 0,
     'L10. an owner gets 200 on all 36 resources, read and write (72 calls). '
   + 'An owner locked out of their own app is the failure mode that gets a '
   + 'gate deleted',
     JSON.stringify(ownerFails).slice(0, 380));

  // ── E. THE DETERMINISTIC AFTERCARE KEY, BOTH HALVES ─────────────────────
  console.log('\nE. leg_aftercare -- the key is the fix, and both halves agree');

  const a1 = await call('leg_aftercare', 'write', 'owner',
    { id: 'AC-1760000000000-abc', case_id: 'CS-7', checkin_type: '1 Week',
      status: 'Pending' });
  const a2 = await call('leg_aftercare', 'write', 'owner',
    { id: 'AC-1760000009999-xyz', case_id: 'CS-7', checkin_type: '1 Week',
      status: 'Pending' });
  const idOf = (r) => (r.res.body && r.res.body.data && r.res.body.data.id) || '';
  is(idOf(a1) === 'AC-CS-7-1-WEEK' && idOf(a1) === idOf(a2),
     'E1. two devices sending DIFFERENT random ids for the same (case, '
   + 'check-in type) both land on ONE deterministic key, so the upsert '
   + 'de-duplicates by construction rather than by a check',
     'a=' + idOf(a1) + ' b=' + idOf(a2));

  const a3 = await call('leg_aftercare', 'write', 'owner',
    { id: 'AC-KEEP-ME', status: 'Pending' });
  is(idOf(a3) === 'AC-KEEP-ME',
     'E2. CONTROL -- a payload MISSING case_id or checkin_type keeps its own '
   + 'id. A key built from a missing field would collide with every other row '
   + 'missing the same field, which is worse than the bug being fixed',
     idOf(a3));

  const a4 = await call('leg_aftercare', 'write', 'owner',
    { id: 'X', case_id: 'CS-7', checkin_type: '1 Month' });
  is(idOf(a4) === 'AC-CS-7-1-MONTH' && idOf(a4) !== idOf(a1),
     'E3. CONTROL -- a DIFFERENT check-in type on the same case gets a '
   + 'DIFFERENT key. Without this arm, "they all collapse to one row" would '
   + 'pass E1',
     idOf(a4));

  // ** THE TWO COPIES OF THE DERIVATION MUST AGREE. ** There is no way to
  // share one function between a static page and a serverless handler, so the
  // client's is extracted and run against the server's answer.
  let html = null;
  try {
    html = fs.readFileSync(path.join(__dirname, '..', 'sairnlegacy.html'), 'utf8');
  } catch (e) { html = null; }
  if (html === null) {
    cannot('E4. sairnlegacy.html is not readable, so the client half of the '
         + 'key derivation was not compared', 'ENOENT');
  } else {
    const m = html.match(/function legAftercareId\(caseId,type\)\{([\s\S]*?)\n\}/);
    if (!m) {
      cannot('E4. legAftercareId() was not found in sairnlegacy.html, so the '
           + 'two derivations could not be compared', 'anchor absent');
    } else {
      let clientFn = null;
      try {
        /* eslint-disable no-new-func */
        clientFn = new Function('caseId', 'type', m[1]);
      } catch (e) { clientFn = null; }
      if (!clientFn) {
        cannot('E4. the extracted client function would not compile', 'syntax');
      } else {
        const cases = [['CS-7', '1 Week'], ['CS-7', '1 Month'],
                       ['CS-7', '1 Year'], ['CS 9', 'ad hoc  check-in']];
        const disagree = [];
        for (const c of cases) {
          const serverR = await call('leg_aftercare', 'write', 'owner',
            { id: 'RANDOM', case_id: c[0], checkin_type: c[1] });
          const serverId = idOf(serverR);
          const clientId = clientFn(c[0], c[1]);
          if (serverId !== clientId) {
            disagree.push(JSON.stringify(c) + ' server=' + serverId
                        + ' client=' + clientId);
          }
        }
        is(disagree.length === 0,
           'E4. the CLIENT\'s legAftercareId() and the SERVER\'s derivation '
         + 'produce the same key for every case tried, including one with '
         + 'spaces and doubled separators -- extracted from the HTML and RUN, '
         + 'not compared by eye',
           JSON.stringify(disagree));
      }
    }
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed, '
            + unproven + ' unproven');
  if (failed.length) console.log(failed.length + ' ARM(S) FAILED: ' + failed.join(', '));
  if (notProved.length) console.log(notProved.length + ' ARM(S) UNPROVEN: ' + notProved.join(', '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
})().catch((e) => { console.error(e); process.exit(1); });
