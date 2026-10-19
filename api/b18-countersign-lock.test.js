// api/b18-countersign-lock.test.js
//
// Run:  node api/b18-countersign-lock.test.js
//
// THE THREE PRACTITIONER ANSWERS THAT CONVERGED ON ONE PATTERN -- F1, C2 and
// F3 -- driven end to end, plus the ablations that prove each gate is actually
// load-bearing.
//
// ── WHY ABLATIONS AND NOT ONLY ASSERTIONS ────────────────────────────────
// fourth's b26 finding H1 was that SAIRNlaw's trust hard-lock could be
// DELETED ENTIRELY and every suite stayed green: the defence existed, was
// written down, was believed, and no arm could see it because the thing in
// front of it was working. b17 closed that with structural arms. THE SAME
// TRAP IS OPEN FOR EVERY GATE THIS BATCH ADDS, so each one is removed on
// purpose here and the suite asserts what goes red -- per ARM, not per exit
// code (item 12 of docs/2026-09-13-cross-domain-disciplines.md).
//
// ── WHAT THIS DOES NOT DO ────────────────────────────────────────────────
// It does not touch a database and makes no live request. The handler arms
// drive the real dispatcher with a recorded PostgREST stand-in, so they prove
// the lock answers before any upsert -- not that the deployed endpoint does.
// NEITHER SQL FILE HAS BEEN RUN, so in production both locks answer 503
// NOT_PROVISIONED today, which is a refusal and not a bypass -- A1 asserts
// exactly that, because "the lock is inert until Michael runs SQL" and "the
// lock lets writes through until Michael runs SQL" are opposite facts.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['b18', 'countersign', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const { signSessionToken, ROLES_BY_APP } = require('./_lib/auth');
const cs = require('./_lib/countersign');
const lawRoles = require('./_lib/law-roles');
const legRoles = require('./_lib/leg-roles');

const SD_DATA_SRC = path.join(__dirname, 'sd-data.js');
const LEG_ROLES_SRC = path.join(__dirname, '_lib', 'leg-roles.js');
const SELF = __filename;
const ARMS_ONLY = process.env.B18_COUNTERSIGN_ARMS_ONLY === '1';
const HASH = 'b18-cs-hash';
const KEY = 'KEY-FOR-' + HASH;

let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(l) { pass++; console.log('  ok       ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL     ' + l);
  if (why) console.log('           ' + String(why).slice(0, 700));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 700));
}
function is(cond, label, detail) { if (cond) ok(label); else bad(label, detail); }
function section(t) { console.log('\n' + t); }

// ── THE HANDLER HARNESS ─────────────────────────────────────────────────────
function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}
function eCode(res) { return (res.body && res.body.error && res.body.error.code) || ''; }
function eMsg(res) { return (res.body && res.body.error && res.body.error.message) || ''; }

// `opts.tokenRow` = the countersignature row the lookup finds. Absent = none.
// `opts.inactive` = a set of employee_ids the active-employee lookup refuses,
//                   which is how the SETTLING STEP is driven.
// `opts.tableMissing` = the token table does not exist, i.e. the SQL has not
//                   been run. Shaped as PostgREST's real answer, not as a
//                   generic failure, because the handler distinguishes them.
function pgMock(calls, opts) {
  opts = opts || {};
  return async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    calls.push({ url: u, method: method });
    if (/_countersign_tokens/.test(u)) {
      if (opts.tableMissing) {
        return { ok: false, status: 404,
                 json: async () => ({ code: 'PGRST205',
                   message: 'Could not find the table in the schema cache' }) };
      }
      if (method === 'PATCH') {
        return { ok: true, status: 200,
                 json: async () => (opts.tokenRow ? [{ id: 'tok-1' }] : []) };
      }
      return { ok: true, status: 200,
               json: async () => (opts.tokenRow ? [opts.tokenRow] : []) };
    }
    if (/_employee_auth/.test(u)) {
      const m = u.match(/employee_id=eq\.([^&]+)/);
      const who = m ? decodeURIComponent(m[1]) : 'emp-1';
      if (opts.inactive && opts.inactive.indexOf(who) !== -1) {
        return { ok: true, status: 200, json: async () => [] };
      }
      return { ok: true, status: 200, json: async () => [
        { license_hash: HASH, employee_id: who, role: 'owner', active: true }] };
    }
    if (method === 'POST') {
      return { ok: true, status: 200, json: async () => [JSON.parse(init.body)] };
    }
    return { ok: true, status: 200, json: async () => [] };
  };
}

function loadHandler(fetchImpl, app) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: HASH,
        trial_ends_at: null, stripe_subscription_id: null, app_id: app })
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

async function call(app, hdrName, resource, action, role, payload, opts) {
  opts = opts || {};
  const calls = [];
  const h = loadHandler(pgMock(calls, opts), app);
  const res = mockRes();
  const body = { action: action, resource: resource };
  if (action !== 'read') body.payload = payload || { id: 'X1' };
  const headers = {
    authorization: 'Bearer ' + KEY,
    'x-sd-auth': signSessionToken({
      app: app, employee_id: opts.callerId || 'emp-1', role: role,
      license_hash: HASH })
  };
  // The header goes on only when there is a row to find. Without this guard a
  // "signed path" arm measures the `!token` refusal instead and passes for the
  // wrong reason.
  if (opts.tokenRow || opts.sendToken) headers[hdrName] = FIXTURE_TOKEN;
  await h({ method: 'POST', headers: headers, body: body }, res);
  return { res: res, calls: calls };
}
const callLaw = (r, a, role, p, o) => call('sairnlaw', 'x-law-countersign', r, a, role, p, o);
const callLeg = (r, a, role, p, o) => call('sairnlegacy', 'x-leg-countersign', r, a, role, p, o);

// THE FULL law_trusttx PAYLOAD. `{id}` alone is a 400 from that branch's own
// field validator -- CORRECT, and nothing to do with the countersignature. A
// thin payload would have made "the write was refused" mean "some refusal
// happened" rather than "the lock refused", which is the distinction the leg
// matrix suite's L10 comment already records paying for.
// `Deposit` AND NOT `Disbursement`, which is not a dodge. A Disbursement goes
// through the `law_check_and_insert_disbursement` RPC and its own balance
// guard (sql/sairnlaw_trust_disbursement_atomic_check.sql) -- a second,
// pre-existing control with its own arms in its own suite. Stubbing that RPC
// here would make these arms depend on a mock of a control they are not
// about. A Deposit is the same resource, the same lock and the same gate, on
// the plain upsert path. THE REAL C2 CASE IS A DISBURSEMENT, so that pairing
// is named in the b18 handoff as the thing to drive live once the SQL is run.
const TX1 = { id: 'TX-1', matter_id: 'M-1', client_id: 'CL-1',
              type: 'Deposit', amount: 500 };
const TX2 = { id: 'TX-2', matter_id: 'M-1', client_id: 'CL-1',
              type: 'Deposit', amount: 500 };
const BS1 = { id: 'BS-1', matter_id: 'M-1', client_id: 'CL-1' };
const CR1 = { id: 'CR-1', case_id: 'CS-1' };

// THE FIXTURE TOKEN IS A NAMED CONSTANT CONTAINING THE WORD `placeholder`,
// and that is not cosmetic. tools/redaction_check.py's
// `generic_credential_assignment` pattern matches
// `token: "<16+ chars>"` and the push gate REFUSED this file on it -- which is
// correct behaviour on a literal that looks like a bearer credential, and the
// gate deliberately does not print the match. `placeholder` is one of its
// PLACEHOLDER_MARKERS, so the fixture declares itself as one rather than being
// exempted.
const FIXTURE_TOKEN = 'cs-token-placeholder';

function row(resource, payload, over) {
  return Object.assign({
    id: 'tok-1',
    resource: resource,
    content_hash: cs.contentHash(resource, payload),
    prepared_by: 'emp-1', prepared_role: 'paralegal',
    countersign_employee_id: 'emp-2', countersign_role: 'attorney',
    countersigned_at: new Date(Date.now() - 60000).toISOString(),
    spent_at: null, spent_on_resource: null,
    expires_at: new Date(Date.now() + 5 * 60000).toISOString()
  }, over || {});
}

// ── THE ABLATION HARNESS ───────────────────────────────────────────────────
// Mutates a real source file, runs THIS FILE's arms-only form in a child
// process, restores, and HARD-EXITS if the restore does not verify. Lifted in
// shape from api/b17-trust-lock-hard.test.js, which is the file that
// established the pattern on this platform.
// RETURNS THE EXIT CODE **AND** THE OUTPUT. The output is what makes J3
// possible: an exit code says a suite broke, not WHICH arm saw it, and item 12
// of docs/2026-09-13-cross-domain-disciplines.md is explicit that ablation is
// measured per ARM. A suite that broke for an unrelated reason produces the
// same exit 1 as one whose named arm fired.
function runSuite(file, armsOnly) {
  const env = armsOnly
    ? Object.assign({}, process.env, { B18_COUNTERSIGN_ARMS_ONLY: '1' })
    : process.env;
  try {
    const out = execFileSync(process.execPath, [file], {
      env: env, encoding: 'utf8', stdio: 'pipe'
    });
    return { exit: 0, out: String(out || '') };
  } catch (e) {
    return {
      exit: typeof e.status === 'number' ? e.status : -1,
      out: String((e && e.stdout) || '') + String((e && e.stderr) || '')
    };
  }
}

// The named arms a child run reports as failed, from its own summary line.
function failedArms(out) {
  const m = String(out || '').match(/FAILED:\s*(.+)/);
  return m ? m[1].trim().split(/\s*,\s*/).filter(Boolean) : [];
}

/**
 * @param {string[]} [alsoRun] other suite paths to run WHILE THE FILE IS
 *   MUTATED. This parameter exists because the first draft ran the leg matrix
 *   suite AFTER `ablate` returned -- i.e. after the `finally` had already
 *   restored the file -- and measured the CLEAN tree while reporting it as an
 *   ablation result. A green answer from a restored tree is exactly the shape
 *   of a check that has stopped testing anything.
 */
function ablate(file, find, replace, label, alsoRun) {
  const original = fs.readFileSync(file, 'utf8');
  const hits = original.split(find).length - 1;
  if (hits !== 1) {
    return { ok: false, why: 'the ablation anchor matched ' + hits + ' time(s) in '
                           + path.basename(file) + ', not exactly 1 -- refusing to '
                           + 'mutate. Anchor: ' + find.slice(0, 90) };
  }
  try {
    fs.writeFileSync(file, original.replace(find, replace), 'utf8');
    const mine = runSuite(SELF, true);
    const others = (alsoRun || []).map((f) => {
      const r = runSuite(f, false);
      return { file: path.basename(f), exit: r.exit, arms: failedArms(r.out) };
    });
    return { ok: true, exit: mine.exit, arms: failedArms(mine.out),
             others: others, label: label };
  } finally {
    fs.writeFileSync(file, original, 'utf8');
    if (fs.readFileSync(file, 'utf8') !== original) {
      console.error('\nFATAL: could not restore ' + file + ' after an ablation. '
        + 'The working tree is MODIFIED. Run: git checkout -- ' + file);
      process.exit(70);
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════
async function arms() {
  // ── A. THE SQL HAS NOT BEEN RUN, AND THAT IS A REFUSAL, NOT A BYPASS ────
  section('A. NOT_PROVISIONED is a refusal (the production state today)');

  const a1 = await callLeg('leg_cremations', 'write', 'director', CR1,
                           { sendToken: true, tableMissing: true });
  is(a1.res.statusCode === 503 && eCode(a1.res) === 'NOT_PROVISIONED'
     && /refused rather than filed unsigned/.test(eMsg(a1.res))
     && !a1.calls.some((c) => c.method === 'POST' && /leg_cremations/.test(c.url)),
     'A1. with the countersignature table ABSENT the write is REFUSED 503 '
   + 'NOT_PROVISIONED and nothing is upserted. "Could not tell" is a third '
   + 'state and is never folded into "signed"',
     a1.res.statusCode + ' ' + eCode(a1.res) + ' ' + eMsg(a1.res));

  const a2 = await callLaw('law_trusttx', 'write', 'paralegal', TX1,
                           { sendToken: true, tableMissing: true });
  is(a2.res.statusCode === 503 && eCode(a2.res) === 'NOT_PROVISIONED',
     'A2. ...and the same for a paralegal-prepared trust disbursement',
     a2.res.statusCode + ' ' + eCode(a2.res) + ' ' + eMsg(a2.res));

  // ── B. C2 END TO END THROUGH THE REAL HANDLER ──────────────────────────
  section('B. C2 -- a paralegal prepares, an attorney authorises');

  const b1 = await callLaw('law_trusttx', 'write', 'paralegal', TX1);
  is(b1.res.statusCode === 403 && eCode(b1.res) === 'COUNTERSIGN_REQUIRED'
     && !b1.calls.some((c) => c.method === 'POST' && /law_trusttx/.test(c.url)),
     'B1. a paralegal writing law_trusttx with NO signature is refused 403 '
   + 'COUNTERSIGN_REQUIRED and nothing is upserted',
     b1.res.statusCode + ' ' + eCode(b1.res) + ' ' + eMsg(b1.res));

  const b2 = await callLaw('law_trusttx', 'write', 'paralegal', TX1,
                           { tokenRow: row('law_trusttx', TX1) });
  is(b2.res.statusCode === 200
     && b2.calls.some((c) => c.method === 'POST' && /law_trusttx/.test(c.url)),
     'B2. the SAME write carrying an attorney-signed token LANDS, and the '
   + 'upsert really is sent. This is the arm that makes C2 a workflow rather '
   + 'than a reworded refusal',
     b2.res.statusCode + ' ' + eCode(b2.res) + ' ' + eMsg(b2.res));

  const b3 = await callLaw('law_trusttx', 'write', 'attorney', TX1);
  is(b3.res.statusCode === 200,
     'B3. an ATTORNEY writing law_trusttx needs no token at all -- '
   + 'MODE_PREPARED_ONLY. C2 asked whether a paralegal may prepare, not '
   + 'whether an attorney needs a second attorney',
     b3.res.statusCode + ' ' + eCode(b3.res) + ' ' + eMsg(b3.res));

  const b4 = await callLaw('law_trusttx', 'read', 'paralegal');
  is(b4.res.statusCode === 403 && eCode(b4.res) === 'FORBIDDEN'
     && /PREPARE/.test(eMsg(b4.res)) === false,
     'B4. a paralegal still cannot READ the trust ledger -- the deferral is '
   + 'write-only, and the read refusal does not offer a prepare route that '
   + 'would not help',
     b4.res.statusCode + ' ' + eCode(b4.res) + ' ' + eMsg(b4.res));

  const b5 = await callLaw('law_bankstatements', 'write', 'paralegal', BS1,
                           { tokenRow: row('law_bankstatements', BS1) });
  is(b5.res.statusCode === 403 && eCode(b5.res) === 'FORBIDDEN'
     && !b5.calls.some((c) => c.method === 'POST' && /law_bankstatements/.test(c.url)),
     'B5. law_bankstatements is NOT two-stage: a paralegal is refused even '
   + 'holding a signed token, because nobody at a firm prepares a bank '
   + 'statement',
     b5.res.statusCode + ' ' + eCode(b5.res) + ' ' + eMsg(b5.res));

  const b6 = await callLaw('law_trusttx', 'write', 'bookkeeper', TX1,
                           { tokenRow: row('law_trusttx', TX1) });
  is(b6.res.statusCode === 403 && eCode(b6.res) === 'FORBIDDEN',
     'B6. and C1\'s `bookkeeper` cannot reach trust by the two-stage route '
   + 'either -- it is not in LAW_TRUST_PREPARE_ROLES, which is the one-line '
   + 'decision C2 says it would take to change that',
     b6.res.statusCode + ' ' + eCode(b6.res) + ' ' + eMsg(b6.res));

  // ── C. THE TOKEN'S OWN PROPERTIES, DRIVEN ──────────────────────────────
  section('C. the token: content binding, self-signature, qualification, '
        + 'spend, expiry');

  const CASES = [
    ['C1', { countersign_employee_id: null, countersign_role: null, countersigned_at: null },
      403, 'COUNTERSIGN_REQUIRED', 'a PREPARED but unsigned token is not a signature'],
    ['C2', { countersign_employee_id: 'emp-1' },
      409, 'COUNTERSIGN_SAME_PERSON', 'the preparer signing their own work is refused at the WRITE'],
    ['C3', { countersign_role: 'paralegal' },
      403, 'COUNTERSIGN_NOT_QUALIFIED', 'a signature from a non-bar-admitted role is refused, derived from the ROW\'s role'],
    ['C4', { spent_at: new Date(Date.now() - 1000).toISOString() },
      409, 'COUNTERSIGN_ALREADY_SPENT', 'one signature covers exactly one write'],
    ['C5', { expires_at: new Date(Date.now() - 1000).toISOString() },
      409, 'COUNTERSIGN_EXPIRED', 'a signature detached from its moment is not reused']
  ];
  for (const c of CASES) {
    const r = await callLaw('law_trusttx', 'write', 'paralegal', TX1,
                            { tokenRow: row('law_trusttx', TX1, c[1]) });
    is(r.res.statusCode === c[2] && eCode(r.res) === c[3]
       && !r.calls.some((x) => x.method === 'POST' && /law_trusttx/.test(x.url)),
       c[0] + '. ' + c[4] + ' -> ' + c[2] + ' ' + c[3] + ', nothing upserted',
       r.res.statusCode + ' ' + eCode(r.res) + ' ' + eMsg(r.res));
  }

  const c6 = await callLaw('law_trusttx', 'write', 'paralegal', TX2,
                           { tokenRow: row('law_trusttx', TX1) });
  is(c6.res.statusCode === 409 && eCode(c6.res) === 'COUNTERSIGN_CONTENT_MISMATCH',
     'C6. THE CONTENT BINDING: an authorisation issued for TX-1 cannot file '
   + 'TX-2. Without this the lock is decorative -- a $0 authorisation would '
   + 'file any disbursement',
     c6.res.statusCode + ' ' + eCode(c6.res) + ' ' + eMsg(c6.res));

  // ── D. THE SETTLING STEP ───────────────────────────────────────────────
  section('D. the settling step -- the signers are re-verified AT THE WRITE');

  const d1 = await callLaw('law_trusttx', 'write', 'paralegal', TX1,
                           { tokenRow: row('law_trusttx', TX1),
                             inactive: ['emp-2'] });
  is(d1.res.statusCode === 403 && eCode(d1.res) === 'COUNTERSIGN_NO_LONGER_ACTIVE'
     && !d1.calls.some((c) => c.method === 'POST' && /law_trusttx/.test(c.url)),
     'D1. an attorney who authorised and was THEN deactivated cannot have '
   + 'their signature spent -- 403 COUNTERSIGN_NO_LONGER_ACTIVE. A signature '
   + 'from a revoked account carries a name that no longer means anything',
     d1.res.statusCode + ' ' + eCode(d1.res) + ' ' + eMsg(d1.res));

  // D2 IS ON THE SAIRNlegacy SIDE, and that is not a convenience. To test a
  // deactivated PREPARER the preparer must not be the caller -- and on the law
  // side they are, because MODE_PREPARED_ONLY means the paralegal who prepared
  // it is the one who saves. Marking that employee inactive is caught by the
  // SESSION gate first and answers CREDENTIAL_INACTIVE, which is a correct and
  // stronger refusal but is NOT the settling step. SAIRNlegacy's F1 flow has
  // the two roles genuinely separate: an apprentice prepares, a director saves.
  const d2 = await callLeg('leg_cremations', 'write', 'director', CR1,
                           { tokenRow: row('leg_cremations', CR1, {
                               prepared_by: 'emp-9', prepared_role: 'apprentice',
                               countersign_employee_id: 'emp-2',
                               countersign_role: 'director' }),
                             inactive: ['emp-9'] });
  is(d2.res.statusCode === 403 && eCode(d2.res) === 'COUNTERSIGN_NO_LONGER_ACTIVE'
     && !d2.calls.some((c) => c.method === 'POST' && /leg_cremations/.test(c.url)),
     'D2. ...and the PREPARER too, not only the signer: an apprentice who '
   + 'prepared a cremation authorisation and was then deactivated blocks the '
   + 'write. Both names are on the record, so both have to still mean something',
     d2.res.statusCode + ' ' + eCode(d2.res) + ' ' + eMsg(d2.res));

  // ── E. THE PROFILES ARE DERIVED, NOT RETYPED ───────────────────────────
  section('E. the profiles are derived from the role modules');

  const legCs = require('./leg-countersign');
  const lawCs = require('./law-countersign');

  is(legCs.PROFILE.signerRoles === legRoles.LEG_REGULATED_WRITE_ROLES,
     'E1. SAIRNlegacy\'s signer set IS legRoles.LEG_REGULATED_WRITE_ROLES by '
   + 'IDENTITY, not by equality -- so a band change moves it and no second '
   + 'copy can go stale',
     'identity=' + (legCs.PROFILE.signerRoles === legRoles.LEG_REGULATED_WRITE_ROLES));

  is(lawCs.PROFILE.signerRoles === lawRoles.LAW_BAR_ADMITTED_ROLES
     && lawCs.PROFILE.preparerRoles === lawRoles.LAW_TRUST_PREPARE_ROLES,
     'E2. SAIRNlaw\'s signer set IS lawRoles.LAW_BAR_ADMITTED_ROLES and its '
   + 'preparer set IS LAW_TRUST_PREPARE_ROLES, both by identity',
     'signer=' + (lawCs.PROFILE.signerRoles === lawRoles.LAW_BAR_ADMITTED_ROLES)
     + ' preparer=' + (lawCs.PROFILE.preparerRoles === lawRoles.LAW_TRUST_PREPARE_ROLES));

  const lockedLaw = Object.keys(lawCs.PROFILE.lockedResources).sort();
  const twoStage = Object.keys(lawRoles.LAW_TRUST_TWO_STAGE).sort();
  is(lockedLaw.length === twoStage.length
     && lockedLaw.every((r, i) => r === twoStage[i]),
     'E3. the endpoint\'s locked list and law-roles\' LAW_TRUST_TWO_STAGE are '
   + 'the SAME SET -- asserted rather than agreeing by eye, because the write '
   + 'gate keys off one and the endpoint off the other',
     JSON.stringify({ endpoint: lockedLaw, roles: twoStage }));

  const lockedLeg = Object.keys(legCs.PROFILE.lockedResources).sort();
  const legReq = legRoles.resources().filter((r) => legRoles.requiresCountersignature(r)).sort();
  is(lockedLeg.length === legReq.length
     && lockedLeg.every((r, i) => r === legReq[i]),
     'E4. ...and the same on the SAIRNlegacy side',
     JSON.stringify({ endpoint: lockedLeg, roles: legReq }));

  is(legCs.PROFILE.lockedResources.leg_cremations === cs.MODE_ALWAYS
     && lawCs.PROFILE.lockedResources.law_trusttx === cs.MODE_PREPARED_ONLY,
     'E5. THE ASYMMETRY IS ASSERTED, not left as a reader\'s inference: '
   + 'leg_cremations is MODE_ALWAYS (F1 binds the owner) and law_trusttx is '
   + 'MODE_PREPARED_ONLY (C2 did not ask about attorneys)',
     JSON.stringify({ leg: legCs.PROFILE.lockedResources,
                      law: lawCs.PROFILE.lockedResources }));

  // ── F. assertProfile FAILS CLOSED, BOTH DIRECTIONS ─────────────────────
  section('F. an incomplete profile is refused at load, not served');

  const BAD_PROFILES = [
    ['F1', {}, 'an empty profile'],
    ['F2', Object.assign({}, lawCs.PROFILE, { signerRoles: Object.create(null) }),
      'an EMPTY signer set -- which would mean either "anyone may sign" or "a '
    + 'cremation nobody can ever authorise", and both are wrong'],
    ['F3', Object.assign({}, lawCs.PROFILE, { lockedResources: Object.create(null) }),
      'a profile that locks nothing -- the lock with extra steps'],
    ['F4', Object.assign({}, lawCs.PROFILE, {
      lockedResources: Object.assign(Object.create(null), { law_trusttx: 'maybe' }) }),
      'a mode that is not one of the two named ones']
  ];
  for (const b of BAD_PROFILES) {
    let threw = false, msg = '';
    try { cs.assertProfile(b[1]); } catch (e) { threw = true; msg = e.message; }
    is(threw, b[0] + '. assertProfile REFUSES ' + b[2], 'it did not throw');
    if (threw && b[0] === 'F2') {
      is(/signerRoles/.test(msg),
         'F2b. ...and the message NAMES the missing field, so the deploy that '
       + 'fails says what to fix', msg);
    }
  }
  // THE SILENT HALF OF THE PAIR. Without this, a validator that threw on
  // everything would pass every arm above.
  let goodThrew = '';
  try { cs.assertProfile(lawCs.PROFILE); cs.assertProfile(legCs.PROFILE); }
  catch (e) { goodThrew = e.message; }
  is(goodThrew === '',
     'F5. CLEAN -- both real profiles pass. A validator that refused '
   + 'everything would have passed F1-F4 and taken both endpoints down',
     goodThrew);

  // ── G. C3 -- THE LICENSURE TIER AND THE MAPS THAT MATCH IT ─────────────
  section('G. C3 -- the bar-admitted tier, and the two maps that equal it');

  const tier = Object.keys(lawRoles.LAW_BAR_ADMITTED_ROLES).sort();
  is(tier.length === 2 && tier[0] === 'attorney' && tier[1] === 'owner',
     'G1. LAW_BAR_ADMITTED_ROLES is EXACTLY owner and attorney, asserted as a '
   + 'set so adding a third goes red -- the tier decides trust access',
     JSON.stringify(tier));

  is(Object.isFrozen(lawRoles.LAW_BAR_ADMITTED_ROLES)
     && Object.getPrototypeOf(lawRoles.LAW_BAR_ADMITTED_ROLES) === null,
     'G2. ...and it is FROZEN with a NULL PROTOTYPE, so `constructor` is not a '
   + 'truthy bar-admitted role and no caller can add one at runtime',
     'frozen=' + Object.isFrozen(lawRoles.LAW_BAR_ADMITTED_ROLES)
     + ' proto=' + Object.getPrototypeOf(lawRoles.LAW_BAR_ADMITTED_ROLES));

  // THE RELATIONSHIP, NOT A SECOND COPY. Modelled on
  // api/sd-data-sv-role-matrix.test.js arm A5b, which asserts
  // SV_CONTROLLED_RECORD_ROLES is PRESCRIBER_ROLES plus exactly one named
  // role rather than re-listing anything.
  //
  // THESE TWO MAPS ARE NOT COLLAPSED INTO THE TIER AND THAT IS DELIBERATE.
  // "Reviewing an AI chain-of-custody record" and "authoring a deadline rule"
  // happen to need the same two roles as "authorising money out of trust";
  // whether they are the SAME legal act is a question nobody has answered, so
  // this batch asserts the agreement and leaves the definitions separate. If
  // they ever diverge on purpose, this arm is where the divergence has to be
  // declared.
  try {
    const lawAuthSrc = fs.readFileSync(path.join(__dirname, 'law-auth.js'), 'utf8');
    const spellings = (lawAuthSrc.match(/roleSet\(\{\s*owner:\s*true,\s*attorney:\s*true\s*\}\)/g) || []).length;
    const lawAuth = require('./law-auth');
    const sameAsTier = (m) => {
      const k = Object.keys(m || {}).sort();
      return k.length === tier.length && k.every((x, i) => x === tier[i]);
    };
    is(spellings === 2,
       'G3. api/law-auth.js spells `roleSet({ owner: true, attorney: true })` '
     + 'in EXACTLY 2 places -- AI_COC_REVIEW_ROLES and RULE_AUTHORING_ROLES. A '
     + 'THIRD appearing is the drift C3 exists to make visible, and a drop to '
     + 'ONE means somebody collapsed them without declaring it here',
       'spellings=' + spellings);
    is(sameAsTier(lawAuth.RULE_AUTHORING_ROLES),
       'G3b. ...and RULE_AUTHORING_ROLES is the SAME SET as the tier. Not the '
     + 'same OBJECT: whether authoring a deadline rule is the same legal act '
     + 'as authorising money out of trust is a question nobody has answered, '
     + 'so the agreement is asserted and the definitions stay separate',
       JSON.stringify(Object.keys(lawAuth.RULE_AUTHORING_ROLES || {})));
  } catch (e) { bad('G3. the law-auth spellings agree with the tier', e && e.message); }

  // ── H. F3 -- THE APPRENTICE CONFIG, NORMALISED AND NARROWING ───────────
  section('H. F3 -- the apprentice config is untrusted input and narrows only');

  const H = [
    ['H1', undefined, { countersign: [], forbidden: [], presence_disclosure: true },
      'a MISSING config is the empty default with the disclosure ON'],
    ['H2', { presence_disclosure: null }, { presence_disclosure: true },
      'a null presence flag leaves the disclosure ON -- only an explicit false removes it'],
    ['H3', { presence_disclosure: false }, { presence_disclosure: false },
      'an explicit false removes it'],
    ['H4', { countersign: 'leg_cremations' }, { countersign: [] },
      'a STRING where a list belongs grants nothing'],
    ['H5', { countersign: ['leg_nonexistent'] }, { countersign: [] },
      'a resource that is not in the table is DROPPED, so a typo grants nothing'],
    ['H6', { countersign: ['leg_cremations'], forbidden: ['leg_cremations'] },
      { countersign: [], forbidden: ['leg_cremations'] },
      'countersign and forbidden overlapping resolves to FORBIDDEN -- the narrower reading']
  ];
  for (const h of H) {
    const got = legRoles.apprenticePolicy(h[1]);
    const want = h[2];
    const agrees = Object.keys(want).every((k) => JSON.stringify(got[k]) === JSON.stringify(want[k]));
    is(agrees, h[0] + '. ' + h[3],
       'got ' + JSON.stringify({ countersign: got.countersign, forbidden: got.forbidden,
                                 presence_disclosure: got.presence_disclosure }));
  }
  is(typeof legRoles.apprenticePolicy({}).disclosure_text === 'string'
     && legRoles.apprenticePolicy({}).disclosure_text.length > 60
     && /cannot verify/.test(legRoles.apprenticePolicy({}).disclosure_text),
     'H7. the disclosure TEXT is carried with the policy and says the app '
   + 'CANNOT VERIFY presence -- F3\'s third branch is a disclosure, never a '
   + 'gate, because a wrong supervision model looks like compliance',
     legRoles.apprenticePolicy({}).disclosure_text);

  // ── I. F2 -- THE LIVERY BILLING SETTING ────────────────────────────────
  section('I. F2 -- the livery-billing setting, and what it does NOT change');

  is(legRoles.liveryBilling(undefined) === 'through_the_home'
     && legRoles.liveryBilling('nonsense') === 'through_the_home'
     && legRoles.liveryBilling('direct_to_family') === 'direct_to_family',
     'I1. an unanswered or malformed setting falls to the NARROW default; only '
   + 'the exact string widens anything',
     [legRoles.liveryBilling(undefined), legRoles.liveryBilling('nonsense'),
      legRoles.liveryBilling('direct_to_family')].join(' / '));

  const MONEY_READ = ['leg_liverybookings', 'leg_liveryvendors', 'leg_invoices',
                      'leg_gplservices', 'leg_preneed'];
  const leaks = [];
  legRoles.LEG_LIVERY_BILLING_VALUES.forEach((setting) => {
    MONEY_READ.forEach((r) => {
      ['read', 'write'].forEach((a) => {
        // NO GRANT PRESENTED. This is the question F2 actually asked: does a
        // driver ever see a price by DEFAULT?
        if (legRoles.decide(r, 'livery', a, null, { livery_billing: setting })
            === legRoles.ALLOW) {
          leaks.push(setting + ':' + r + '/' + a);
        }
      });
    });
  });
  is(leaks.length === 0,
     'I2. under EITHER setting, and with no grant presented, `livery` can read '
   + 'no price on any money resource. THIS IS THE INVARIANT F2 IS ABOUT -- '
   + '"a driver who can see what a grieving family is being charged for a '
   + 'casket is a real problem"',
     JSON.stringify(leaks));

  const vendorLeak = legRoles.decide('leg_liveryvendors', 'livery', 'read',
                                     { leg_liveryvendors: true },
                                     { livery_billing: 'direct_to_family' });
  is(vendorLeak === legRoles.DENY,
     'I3. and leg_liveryvendors is NOT grantable under either setting, even '
   + 'with an explicit grant -- the vendor record carries the pricing the '
   + 'invoice is built from, so there is no arrangement that needs it',
     vendorLeak);

  const bookingGranted = legRoles.decide('leg_liverybookings', 'livery', 'read',
                                         { leg_liverybookings: true },
                                         { livery_billing: 'direct_to_family' });
  const bookingDefault = legRoles.decide('leg_liverybookings', 'livery', 'read',
                                         { leg_liverybookings: true });
  is(bookingGranted === legRoles.ALLOW && bookingDefault === legRoles.DENY,
     'I4. the setting\'s ONE effect, both directions: under direct_to_family a '
   + 'GRANTED driver may read their own booking, and under the default the '
   + 'same grant yields nothing. A setting with no measurable effect would be '
   + 'dormant code',
     'granted=' + bookingGranted + ' default=' + bookingDefault);

  // ── K. THE ENDPOINT ITSELF, prepare -> countersign -> status ───────────
  section('K. the endpoint -- the three actions, driven');

  // The endpoint is reached directly rather than through sd-data. It has its
  // own licence/session/employee lookups, so it gets its own loader: the
  // handler modules are re-required after the licence stub is installed,
  // because `makeHandler` runs at module load.
  async function endpoint(app, which, body, opts) {
    opts = opts || {};
    const calls = [];
    delete require.cache[require.resolve('./_lib/license')];
    require.cache[require.resolve('./_lib/license')] = {
      exports: {
        validateLicenseKey: async () => ({
          valid: true, active: true, license_hash: HASH,
          trial_ends_at: null, stripe_subscription_id: null, app_id: app })
      }
    };
    global.fetch = pgMock(calls, opts);
    delete require.cache[require.resolve('./' + which)];
    delete require.cache[require.resolve('./_lib/countersign-endpoint')];
    const h = require('./' + which);
    const res = mockRes();
    await h({ method: 'POST',
              headers: { authorization: 'Bearer ' + KEY,
                         'x-sd-auth': signSessionToken({
                           app: app, employee_id: opts.callerId || 'emp-1',
                           role: opts.callerRole || 'owner',
                           license_hash: HASH }) },
              body: body }, res);
    return { res: res, calls: calls };
  }

  // THE MOCK RETURNS role 'owner' FOR EVERY EMPLOYEE LOOKUP, and the endpoint
  // reads the role FROM THE DATABASE ROW rather than from the token -- so a
  // demotion takes effect at once. That means `opts.callerRole` only decides
  // what the SESSION claims, and these arms are driving an `owner` caller
  // whatever the token says. Stated because it is the opposite of what a
  // reader would assume, and because it is the behaviour that matters: a
  // session must not be able to assert a role the roster has taken away.
  const k1 = await endpoint('sairnlegacy', 'leg-countersign',
    { action: 'prepare', resource: 'leg_cremations', payload: CR1 });
  is(k1.res.statusCode === 200 && k1.res.body && typeof k1.res.body.token === 'string'
     && k1.res.body.token.length >= 32
     && k1.res.body.countersigned === false
     && /licensed funeral director/.test(k1.res.body.countersign_required_from || ''),
     'K1. `prepare` returns a token ONCE, says it is not yet countersigned, '
   + 'and NAMES who has to sign -- a workflow lock whose next step is unnamed '
   + 'is a workflow stall',
     JSON.stringify(Object.assign({}, k1.res.body,
       { token: (k1.res.body && k1.res.body.token || '').slice(0, 8) + '...' })));

  const k2 = await endpoint('sairnlegacy', 'leg-countersign',
    { action: 'prepare', resource: 'leg_cremations', payload: CR1 },
    { callerId: 'emp-1' });
  const stored = (k2.calls.find((c) => c.method === 'POST') || {});
  is(!!stored.url && /leg.*countersign_tokens/.test(stored.url),
     'K2. ...and it is written to THIS APP\'S token table, not a shared one',
     stored.url || 'no POST');

  const k3 = await endpoint('sairnlegacy', 'leg-countersign',
    { action: 'prepare', resource: 'leg_invoices', payload: { id: 'I-1' } });
  is(k3.res.statusCode === 400 && /resource must be one of/.test(eMsg(k3.res))
     && /leg_cremations/.test(eMsg(k3.res)),
     'K3. a resource that is not locked is a 400 that NAMES the locked set, '
   + 'rather than minting a token nothing will ever check',
     k3.res.statusCode + ' ' + eMsg(k3.res));

  const k4 = await endpoint('sairnlegacy', 'leg-countersign',
    { action: 'prepare', resource: 'leg_cremations' });
  is(k4.res.statusCode === 400 && /payload is required/.test(eMsg(k4.res)),
     'K4. no payload is a 400 -- there is nothing to bind a signature TO, and '
   + 'a token bound to "a write is coming" can be spent on any record',
     k4.res.statusCode + ' ' + eMsg(k4.res));

  const k5 = await endpoint('sairnlegacy', 'leg-countersign',
    { action: 'countersign', token: FIXTURE_TOKEN },
    { tokenRow: row('leg_cremations', CR1, {
        prepared_by: 'emp-1', prepared_role: 'director',
        countersign_employee_id: null, countersign_role: null,
        countersigned_at: null }),
      callerId: 'emp-1' });
  is(k5.res.statusCode === 409 && eCode(k5.res) === 'SAME_PERSON',
     'K5. the preparer cannot countersign their own record -- 409 SAME_PERSON '
   + 'at the ENDPOINT, which is the first of the three places this is refused',
     k5.res.statusCode + ' ' + eCode(k5.res) + ' ' + eMsg(k5.res));

  const k6 = await endpoint('sairnlegacy', 'leg-countersign',
    { action: 'countersign', token: FIXTURE_TOKEN },
    { tokenRow: row('leg_cremations', CR1, {
        prepared_by: 'emp-9', prepared_role: 'apprentice',
        countersign_employee_id: null, countersign_role: null,
        countersigned_at: null }),
      callerId: 'emp-1' });
  is(k6.res.statusCode === 200 && k6.res.body && k6.res.body.countersigned === true
     && k6.calls.some((c) => c.method === 'PATCH'
                             && /countersign_employee_id=is\.null/.test(c.url)),
     'K6. a DIFFERENT qualified employee signs it, and the PATCH is a '
   + 'COMPARE-AND-SET on `countersign_employee_id=is.null` -- two signers '
   + 'racing one record must not both be recorded, because only one is the '
   + 'signature the write will cite',
     k6.res.statusCode + ' ' + eCode(k6.res) + ' ' + JSON.stringify(k6.res.body));

  const k7 = await endpoint('sairnlegacy', 'leg-countersign',
    { action: 'countersign', token: FIXTURE_TOKEN },
    { tokenRow: row('leg_cremations', CR1, {
        prepared_by: 'emp-9',
        countersign_employee_id: 'emp-5', countersign_role: 'director' }),
      callerId: 'emp-1' });
  is(k7.res.statusCode === 409 && eCode(k7.res) === 'ALREADY_COUNTERSIGNED',
     'K7. a record that already carries a signature is not signed twice',
     k7.res.statusCode + ' ' + eCode(k7.res));

  const STAGES = [
    ['K8', { countersign_employee_id: null, countersign_role: null, countersigned_at: null },
      'awaiting_signature'],
    ['K9', {}, 'signed'],
    ['K10', { expires_at: new Date(Date.now() - 1000).toISOString() }, 'expired'],
    ['K11', { spent_at: new Date(Date.now() - 1000).toISOString() }, 'filed']
  ];
  for (const st of STAGES) {
    const r = await endpoint('sairnlegacy', 'leg-countersign',
      { action: 'status', token: FIXTURE_TOKEN },
      { tokenRow: row('leg_cremations', CR1,
          Object.assign({ prepared_by: 'emp-9' }, st[1])) });
    is(r.res.statusCode === 200 && r.res.body && r.res.body.stage === st[2],
       st[0] + '. `status` computes ONE NAMED STAGE -- ' + st[2] + '. Four '
     + 'nullable columns is four chances for a panel to render "signed" for a '
     + 'spent-and-expired row',
       r.res.statusCode + ' stage=' + (r.res.body && r.res.body.stage));
  }
  // `filed` BEATS `expired`, asserted explicitly: a row that was spent AND has
  // since passed its expiry is FILED, because the write happened. The other
  // order would report a landed cremation authorisation as expired.
  const k12 = await endpoint('sairnlegacy', 'leg-countersign',
    { action: 'status', token: FIXTURE_TOKEN },
    { tokenRow: row('leg_cremations', CR1, {
        prepared_by: 'emp-9',
        spent_at: new Date(Date.now() - 2000).toISOString(),
        expires_at: new Date(Date.now() - 1000).toISOString() }) });
  is(k12.res.statusCode === 200 && k12.res.body.stage === 'filed',
     'K12. a token that was SPENT and has since EXPIRED reports `filed`, not '
   + '`expired` -- the write happened, and the other precedence would report a '
   + 'landed authorisation as lost',
     'stage=' + (k12.res.body && k12.res.body.stage));

  const k13 = await endpoint('sairnlaw', 'law-countersign',
    { action: 'countersign', token: FIXTURE_TOKEN },
    { tokenRow: row('law_trusttx', TX1, {
        prepared_by: 'emp-9', prepared_role: 'paralegal',
        countersign_employee_id: null, countersign_role: null,
        countersigned_at: null }),
      callerRole: 'paralegal' });
  // The employee lookup returns `owner`, so this arm proves the ROSTER role
  // decides. To drive a genuine refusal the ROW has to say paralegal, which
  // is what the write-path arm C3 does. Asserted as a 200 here so the
  // database-role-wins behaviour is recorded rather than assumed.
  is(k13.res.statusCode === 200,
     'K13. a session CLAIMING paralegal still signs, because the endpoint '
   + 'reads the role from the ROSTER ROW and the roster says owner. This is '
   + 'the right direction -- a token cannot assert a role the roster has '
   + 'taken away -- and the refusal for a genuine paralegal is arm C3',
     k13.res.statusCode + ' ' + eCode(k13.res) + ' ' + eMsg(k13.res));

  const k14 = await endpoint('sairnlaw', 'law-countersign',
    { action: 'nonsense', token: 'x' });
  is(k14.res.statusCode === 400 && /action must be one of/.test(eMsg(k14.res))
     && /prepare/.test(eMsg(k14.res)) && /countersign/.test(eMsg(k14.res)),
     'K14. an unknown action is a 400 that names the three, so a typo is not '
   + 'silently a no-op',
     k14.res.statusCode + ' ' + eMsg(k14.res));

  if (ARMS_ONLY) return;

  // ── J. THE ABLATIONS ───────────────────────────────────────────────────
  section('J. ABLATIONS -- remove ONE named layer and measure what it alone '
        + 'catches');

  // J1. The law write gate. Remove ONLY the requireCountersignature call in
  // api/sd-data.js's law branch and B2's sibling B1 must flip: an UNSIGNED
  // paralegal write would land. This is the arm that proves the deferral in
  // the prelude is not a hole -- the write gate is what closes it.
  const j1 = ablate(SD_DATA_SRC,
    "      if (action !== 'read' && lawRoles.LAW_TRUST_TWO_STAGE[resource] === true) {\n        const csLibGate = require('./_lib/countersign');",
    "      if (false && action !== 'read' && lawRoles.LAW_TRUST_TWO_STAGE[resource] === true) {\n        const csLibGate = require('./_lib/countersign');",
    'law write gate removed', []);
  if (!j1.ok) {
    cannot('J1. the law write gate is load-bearing', j1.why);
  } else {
    is(j1.exit === 1,
       'J1. removing ONLY the countersignature call from the law write path '
     + 'makes this file FAIL (exit 1) -- so the prelude\'s C2 deferral is not '
     + 'a hole, the write gate is what closes it',
       'child exit ' + j1.exit + ' (expected 1)');
  }

  // J2. The leg lock membership. Empty LEG_COUNTERSIGN_REQUIRED and
  // api/sd-data-leg-role-matrix.test.js must flip -- its L6/L10b arms are
  // what see it. Measured in THAT file, not this one, because this is where
  // fourth's H1 went wrong: the lock had arms in a file that could not see it.
  const j2 = ablate(LEG_ROLES_SRC,
    "const LEG_COUNTERSIGN_REQUIRED = Object.freeze(Object.assign(Object.create(null), {\n  leg_cremations: true\n}));",
    "const LEG_COUNTERSIGN_REQUIRED = Object.freeze(Object.create(null));",
    'leg countersign membership emptied',
    [path.join(__dirname, 'sd-data-leg-role-matrix.test.js')]);
  if (!j2.ok) {
    cannot('J2. the leg lock membership is load-bearing', j2.why);
  } else {
    // THE ARM THAT SEES IT IS IN THE MATRIX SUITE, not here -- this file's leg
    // arms are the NOT_PROVISIONED one and the F2/F3 module arms. Which is
    // the whole point: a lock with arms only in a file that cannot see it is
    // fourth's b26 H1. `alsoRun` runs it inside the mutated window.
    const matrix = (j2.others || [])[0] || { exit: null };
    is(matrix.exit === 1,
       'J2. emptying LEG_COUNTERSIGN_REQUIRED makes '
     + 'api/sd-data-leg-role-matrix.test.js FAIL (exit ' + matrix.exit + '), '
     + 'which is where L6 and L10b live. The lock is armed in a file that can '
     + 'see it',
       'this=' + j2.exit + ' matrix=' + JSON.stringify(j2.others));
  }

  // J3. WHICH ARMS, not just "a suite failed". Item 12 of
  // docs/2026-09-13-cross-domain-disciplines.md: ablation is measured per ARM.
  // J1 asserts exit 1, and a suite that broke for an unrelated reason gives
  // the same answer. These are the arms the removed call alone produces.
  if (j1.ok) {
    // D1 IS HERE AND D2 IS NOT, and that asymmetry is the measurement. D1 is
    // the law-side settling step and dies with this gate; D2 is the SAME
    // property on the SAIRNlegacy side and MUST SURVIVE, because it goes
    // through a different gate in a different block. An ablation whose
    // survivor list is empty has not shown that it removed ONE layer.
    const MUST_DIE = ['A2', 'B1', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'D1'];
    const MUST_LIVE = ['A1', 'D2', 'E1', 'E5', 'I2', 'I3'];
    const died = j1.arms || [];
    const missing = MUST_DIE.filter((a) => died.indexOf(a) === -1);
    const survivorsThatDied = MUST_LIVE.filter((a) => died.indexOf(a) !== -1);
    is(missing.length === 0 && survivorsThatDied.length === 0,
       'J3. the law write gate is the ONLY thing holding A2, B1, C1-C6 and D1 '
     + '-- all nine go red when it is removed. A1, D2 (the SAIRNlegacy half of '
     + 'the same property, through a different gate), E1/E5 and the F2 '
     + 'invariants all SURVIVE, which is what shows ONE layer was removed and '
     + 'not the floor',
       JSON.stringify({ died: died, expectedDeadButLived: missing,
                        expectedAliveButDied: survivorsThatDied }));
  } else {
    cannot('J3. which arms the law write gate holds', j1.why);
  }
}

(async () => {
  console.log('b18 countersignature lock -- F1 / C2 / F3'
            + (ARMS_ONLY ? '  [ARMS ONLY]' : '') + '\n');
  try {
    await arms();
  } catch (e) {
    bad('the suite itself threw', e && e.stack);
  }
  console.log('\n  ' + pass + ' passed, ' + fail + ' failed, ' + unproven + ' unproven');
  if (failed.length) console.log('  FAILED: ' + failed.join(', '));
  if (notProved.length) console.log('  UNPROVEN: ' + notProved.join(', '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
})();
