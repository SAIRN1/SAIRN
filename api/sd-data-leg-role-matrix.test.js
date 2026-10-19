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
    // ── b18: THE F1 COUNTERSIGNATURE TABLE ──────────────────────────────
    // `opts.countersignRow` present = a prepared-and-signed token exists for
    // this exact payload. Absent = the lookup finds nothing, which is what a
    // real unsigned write sees and is the DEFAULT here on purpose: every
    // pre-b18 arm keeps driving the unsigned path without being edited.
    if (/_countersign_tokens\?/.test(u)) {
      if (init && init.method === 'PATCH') {
        // The compare-and-set spend. Non-empty = this request won the token.
        return { ok: true, status: 200,
                 json: async () => (opts.countersignRow ? [{ id: 'tok-1' }] : []) };
      }
      return { ok: true, status: 200,
               json: async () => (opts.countersignRow ? [opts.countersignRow] : []) };
    }
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

// THE FIXTURE TOKEN IS A NAMED CONSTANT CONTAINING THE WORD `placeholder`,
// and that is not cosmetic. tools/redaction_check.py's
// `generic_credential_assignment` pattern matches
// `token: "<16+ chars>"` and the push gate REFUSED this file on it -- which is
// correct behaviour on a literal that looks like a bearer credential, and the
// gate deliberately does not print the match. `placeholder` is one of its
// PLACEHOLDER_MARKERS, so the fixture declares itself as one rather than being
// exempted.
const FIXTURE_TOKEN = 'cs-token-placeholder';

async function call(resource, action, role, payload, mockOpts) {
  const calls = [];
  const h = loadHandler(pgMock(calls, mockOpts));
  const res = mockRes();
  const body = { action: action, resource: resource };
  if (action === 'write') body.payload = payload || { id: 'X1' };
  const headers = { authorization: 'Bearer ' + KEY,
                    'x-sd-auth': signSessionToken({
                      app: APP, employee_id: 'emp-1', role: role,
                      license_hash: HASH }) };
  // b18: the F1 countersignature header is sent ONLY when the mock has a token
  // row to find. Without this the lock refuses on `!token` before any lookup,
  // and every "signed path" arm would be measuring the no-token refusal
  // instead -- which is a green arm testing the wrong thing.
  if (mockOpts && mockOpts.countersignRow) {
    headers['x-leg-countersign'] = FIXTURE_TOKEN;
  }
  await h({ method: 'POST', headers: headers, body: body }, res);
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

  // EVERY ROW CARRIES ITS REASON, AND SOMETHING READS IT. The `why` field is
  // the only record of why a resource is in the band it is in, and a field
  // nothing consumes is a field that can go empty without anyone noticing --
  // 36 of them. This arm is the consumer.
  const noWhy = inTable.filter(function (r) {
    const w = legRoles.LEG_ROLE_MATRIX[r].why;
    return typeof w !== 'string' || w.trim().length < 30;
  });
  is(noWhy.length === 0,
     'A6. all 36 rows carry a `why` of at least 30 characters. The band is a judgement and the '
   + 'reason is the only thing a reviewer can check it against; nothing else '
   + 'reads this field, so without this arm it can empty out silently',
     JSON.stringify(noWhy));

  // THE APPEND-ONLY SET IS ASSERTED AS A SET, not inferred from the one arm
  // that happens to exercise it. If a second resource is added to it, the
  // handler's existence lookup costs that resource an extra round trip per
  // write, which is a decision rather than a detail.
  const ao = Object.keys(legRoles.LEG_APPEND_ONLY);
  is(ao.length === 1 && ao[0] === 'leg_custodylog'
     && legRoles.isAppendOnly('leg_custodylog')
     && !legRoles.isAppendOnly('leg_cases'),
     'A7. LEG_APPEND_ONLY is exactly { leg_custodylog }, and isAppendOnly '
   + 'agrees with it in both directions',
     JSON.stringify(ao));

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
    // L6 RE-AIMED 2026-10-17 (b18, practitioner answer F1). It expected 200
    // and that was the right expectation until F1 was answered: Michael's
    // answer is that a cremation authorisation takes a SECOND NAMED, SIGNING
    // PERSON, so an UNSIGNED director write is now a 403 COUNTERSIGN_REQUIRED
    // and the 200 moved to L6b, which drives the signed path.
    // NOT LOOSENED -- the expectation moved and a second arm was added, so
    // both halves of the pair are still measured. A control that was changed
    // from "must succeed" to "may fail" would be the bad version of this.
    ['L6', 'leg_cremations', 'write', 'director', 403, 'F1 -- a director writes a cremation authorisation with NO countersignature', 'COUNTERSIGN_REQUIRED'],
    ['L7', 'leg_invoices', 'write', 'arranger', 200, 'CONTROL -- an arranger writes an invoice'],
    ['L7b', 'leg_documents', 'read', 'arranger', 200, 'CONTROL -- an arranger reads documents']
  ];
  for (const t of L) {
    const r = await call(t[1], t[2], t[3]);
    const got = r.res.statusCode;
    if (t[6]) {
      // A NAMED NON-ROLE REFUSAL. b18's F1 lock is not a role problem and its
      // message must NOT name the role -- a director told "your role does not
      // have access" to a cremation they ARE allowed to authorise would go and
      // ask for a permission they already hold. So the assertions invert:
      // the expected code, NOT the generic role sentence, and above all NO
      // upsert.
      //
      // THE ANCHOR IS `Your role (`, NOT the role NAME. First draft asserted
      // the role name was absent and FAILED ON CORRECT CODE: the F1 refusal
      // says "Ask another licensed DIRECTOR to review and countersign it",
      // which contains the word `director` for a good reason -- it names who
      // to go to. The property that matters is that this is not
      // `legRoles.denyMessage`, and the generic sentence's own opening is the
      // only thing that identifies it.
      //
      // The token lookup itself IS a fetch, so `calls.length === 0` cannot be
      // asserted here -- `no POST` is the property that matters.
      is(got === t[4] && eCode(r.res) === t[6]
         && eMsg(r.res).indexOf('Your role (') === -1
         && !r.calls.some((c) => c.method === 'POST'),
         t[0] + '. ' + t[5] + ' -> ' + t[4] + ' ' + t[6] + ', the body is NOT '
       + 'the generic role refusal (it is not a role problem), and NO upsert '
       + 'was sent',
         got + ' ' + eCode(r.res) + ' / ' + eMsg(r.res)
         + ' / posts=' + r.calls.filter((c) => c.method === 'POST').length);
    } else if (t[4] === 403) {
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

  // ── L6b (b18): THE OTHER HALF OF THE PAIR -- THE SIGNED PATH LANDS ─────
  // L6 proves the lock refuses. WITHOUT THIS ARM THAT IS HALF A MEASUREMENT:
  // a lock that refuses everything passes L6 and makes the app unusable, and
  // "refuses an unsigned write" would be indistinguishable from "refuses a
  // cremation authorisation".
  //
  // The token row is built with the REAL contentHash over the REAL payload, so
  // the content binding is exercised rather than stubbed past -- a row with a
  // made-up hash would be refused by COUNTERSIGN_CONTENT_MISMATCH and this arm
  // would be measuring the wrong refusal.
  const csLib = require('./_lib/countersign');
  const CREM_PAYLOAD = { id: 'CR-1' };
  function signedRow(over) {
    return Object.assign({
      id: 'tok-1',
      content_hash: csLib.contentHash('leg_cremations', CREM_PAYLOAD),
      prepared_by: 'emp-1', prepared_role: 'director',
      countersign_employee_id: 'emp-2', countersign_role: 'director',
      countersigned_at: new Date(Date.now() - 60000).toISOString(),
      spent_at: null, spent_on_resource: null,
      expires_at: new Date(Date.now() + 5 * 60000).toISOString()
    }, over || {});
  }
  const l6b = await call('leg_cremations', 'write', 'director', CREM_PAYLOAD,
                         { countersignRow: signedRow() });
  is(l6b.res.statusCode === 200
     && l6b.calls.some((c) => c.method === 'POST'
                              && /leg_cremations/.test(c.url)),
     'L6b. CONTROL -- the SAME director write WITH a valid countersignature '
   + 'from a different employee is accepted, and the upsert really is sent. '
   + 'The lock is a workflow, not a wall',
     l6b.res.statusCode + ' ' + eCode(l6b.res) + ' ' + eMsg(l6b.res)
     + ' / posts=' + l6b.calls.filter((c) => c.method === 'POST').length);

  // AND THE SELF-SIGNATURE, re-checked at the WRITE and not only at
  // `countersign`. The endpoint refuses it, the database CHECK refuses it,
  // and this is the third place -- because the first two are in a different
  // process and a future write path that skipped them would leave no trace.
  const l6c = await call('leg_cremations', 'write', 'director', CREM_PAYLOAD,
                         { countersignRow: signedRow({ countersign_employee_id: 'emp-1' }) });
  is(l6c.res.statusCode === 409 && eCode(l6c.res) === 'COUNTERSIGN_SAME_PERSON'
     && !l6c.calls.some((c) => c.method === 'POST' && /leg_cremations/.test(c.url)),
     'L6c. a token whose signer IS its preparer is refused AT THE WRITE with '
   + 'COUNTERSIGN_SAME_PERSON, and nothing is upserted -- a second click by '
   + 'one hand is not a second named person',
     l6c.res.statusCode + ' ' + eCode(l6c.res) + ' ' + eMsg(l6c.res));

  // AND AN UNQUALIFIED SIGNER. The role on the ROW is what is re-derived, not
  // the caller's -- it is the signer's standing the record claims.
  const l6d = await call('leg_cremations', 'write', 'director', CREM_PAYLOAD,
                         { countersignRow: signedRow({ countersign_role: 'arranger' }) });
  is(l6d.res.statusCode === 403 && eCode(l6d.res) === 'COUNTERSIGN_NOT_QUALIFIED'
     && !l6d.calls.some((c) => c.method === 'POST' && /leg_cremations/.test(c.url)),
     'L6d. a signature from a role with no `rw` on the REGULATED band is '
   + 'refused COUNTERSIGN_NOT_QUALIFIED at the write, derived from the row\'s '
   + 'stored role and not from the caller',
     l6d.res.statusCode + ' ' + eCode(l6d.res) + ' ' + eMsg(l6d.res));

  // AND A TOKEN FOR A DIFFERENT RECORD. The content binding, driven rather
  // than asserted structurally: without it a signature for a $0 authorisation
  // could file any other.
  const l6e = await call('leg_cremations', 'write', 'director', { id: 'CR-2' },
                         { countersignRow: signedRow() });
  is(l6e.res.statusCode === 409 && eCode(l6e.res) === 'COUNTERSIGN_CONTENT_MISMATCH'
     && !l6e.calls.some((c) => c.method === 'POST' && /leg_cremations/.test(c.url)),
     'L6e. a signature issued for CR-1 cannot file CR-2 -- '
   + 'COUNTERSIGN_CONTENT_MISMATCH, nothing upserted',
     l6e.res.statusCode + ' ' + eCode(l6e.res) + ' ' + eMsg(l6e.res));

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
  // ── b18: THE COUNTERSIGNED RESOURCES GET A SIGNED TOKEN, NOT AN EXEMPTION
  // F1 is MODE_ALWAYS and BINDS THE OWNER -- a rule the owner is exempt from
  // is not "the paperwork takes a second named person". So an unsigned owner
  // write of leg_cremations is a 403 BY DESIGN and this arm must not simply
  // skip the resource: skipping it would stop measuring whether the owner can
  // file a cremation authorisation AT ALL, which is exactly what L10 exists to
  // catch. It is given a VALID SIGNATURE instead, so the arm still asserts 200
  // on all 36 and the thing being proved is "an owner who follows the workflow
  // is not locked out".
  const ownerFails = [];
  for (const r of inTable) {
    const rd = await call(r, 'read', 'owner');
    if (rd.res.statusCode !== 200) ownerFails.push(r + '/read:' + rd.res.statusCode);
    const wPayload = OWNER_PAYLOAD[r] || { id: 'X1' };
    const wOpts = legRoles.requiresCountersignature(r)
      ? { countersignRow: {
            id: 'tok-L10',
            content_hash: csLib.contentHash(r, wPayload),
            prepared_by: 'emp-1', prepared_role: 'owner',
            countersign_employee_id: 'emp-2', countersign_role: 'director',
            countersigned_at: new Date(Date.now() - 60000).toISOString(),
            spent_at: null, spent_on_resource: null,
            expires_at: new Date(Date.now() + 5 * 60000).toISOString() } }
      : undefined;
    const wr = await call(r, 'write', 'owner', wPayload, wOpts);
    if (wr.res.statusCode !== 200) ownerFails.push(r + '/write:' + wr.res.statusCode);
  }
  is(ownerFails.length === 0,
     'L10. an owner gets 200 on all 36 resources, read and write (72 calls), '
   + 'the countersigned ones WITH a valid second signature. An owner locked '
   + 'out of their own app is the failure mode that gets a gate deleted',
     JSON.stringify(ownerFails).slice(0, 380));

  // AND THE COUNT OF COUNTERSIGNED RESOURCES IS ASSERTED, so the arm above
  // cannot quietly become "36 resources, none of them locked" if
  // LEG_COUNTERSIGN_REQUIRED is ever emptied -- which would make L10 pass by
  // measuring nothing, the same unreachable-lock shape as fourth's b26 H1.
  const counterSigned = inTable.filter((r) => legRoles.requiresCountersignature(r));
  is(counterSigned.length === 1 && counterSigned[0] === 'leg_cremations',
     'L10b. EXACTLY ONE of the 36 requires a countersignature and it is '
   + 'leg_cremations -- so L10 really did drive the signed path, and a third '
   + 'locked resource cannot appear unannounced',
     JSON.stringify(counterSigned));

  // ── E. THE DETERMINISTIC AFTERCARE KEY, BOTH HALVES ─────────────────────
  console.log('\nE. leg_aftercare -- the key is the fix, and both halves agree');

  // ── THE CASE ID HERE IS NOW A REAL ONE (2026-10-15, fourth's F4) ────────
  // These arms used case_id 'CS-7' and pinned 'AC-CS-7-1-WEEK'. F4 made the key
  // delimiter-safe: the HISTORIC form is kept for the only pairs the shipped
  // app can produce -- a newId('CS') case id (^CS-[0-9]+-[0-9]+$) with one of
  // the three fixed types -- and anything else gets the escaped form. 'CS-7'
  // is not a shape the generator can emit, so it correctly takes the escaped
  // form now, and pinning it here was pinning a key no production row has.
  // Switched to a real generated id, which is also what makes these arms
  // evidence that live ids did not move. Full account and the collision arms:
  // api/leg-aftercare-key-unambiguous.test.js
  const AC_CASE = 'CS-1760000000000-123';
  const a1 = await call('leg_aftercare', 'write', 'owner',
    { id: 'AC-1760000000000-abc', case_id: AC_CASE, checkin_type: '1 Week',
      status: 'Pending' });
  const a2 = await call('leg_aftercare', 'write', 'owner',
    { id: 'AC-1760000009999-xyz', case_id: AC_CASE, checkin_type: '1 Week',
      status: 'Pending' });
  const idOf = (r) => (r.res.body && r.res.body.data && r.res.body.data.id) || '';
  is(idOf(a1) === 'AC-' + AC_CASE + '-1-WEEK' && idOf(a1) === idOf(a2),
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
    { id: 'X', case_id: AC_CASE, checkin_type: '1 Month' });
  is(idOf(a4) === 'AC-' + AC_CASE + '-1-MONTH' && idOf(a4) !== idOf(a1),
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
    // legAcEsc() IS LIFTED WITH IT (2026-10-15). legAftercareId() now calls the
    // escape helper, so extracting it alone threw ReferenceError -- which this
    // block would have reported as "would not compile", i.e. as an unproven
    // arm about the fixture rather than about the thing being measured.
    const esc = html.match(/function legAcEsc\(s\)\{[\s\S]*?\n\}/);
    const m = html.match(/function legAftercareId\(caseId,type\)\{([\s\S]*?)\n\}/);
    if (!m || !esc) {
      cannot('E4. legAftercareId() was not found in sairnlegacy.html, so the '
           + 'two derivations could not be compared', 'anchor absent');
    } else {
      let clientFn = null;
      try {
        /* eslint-disable no-new-func */
        clientFn = new Function('caseId', 'type', esc[0] + ';\n' + m[1]);
      } catch (e) { clientFn = null; }
      if (!clientFn) {
        cannot('E4. the extracted client function would not compile', 'syntax');
      } else {
        const cases = [[AC_CASE, '1 Week'], [AC_CASE, '1 Month'],
                       [AC_CASE, '1 Year'], ['CS 9', 'ad hoc  check-in'],
                       ['CS-7', '1 Week'], ['CS-7-1', 'Week']];
        const disagree = [];
        for (const c of cases) {
          const serverR = await call('leg_aftercare', 'write', 'owner',
            { id: 'RANDOM', case_id: c[0], checkin_type: c[1] });
          const serverId = idOf(serverR);
          const clientId = clientFn(c[0], c[1]);
          // The client returns null where the server leaves the caller's id
          // alone -- both declining is agreement, not disagreement.
          if (serverId !== (clientId === null ? 'RANDOM' : clientId)) {
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
