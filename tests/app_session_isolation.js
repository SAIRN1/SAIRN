// tests/app_session_isolation.js  -- item 69
//
// Run:  node tests/app_session_isolation.js
//
// TWO QUESTIONS, AND THEY ARE NOT THE SAME ONE.
//
//   1. WHERE A SESSION GATE EXISTS, does it keep one app's session out of
//      another app's data? (Sections 1-3.)
//   2. WHERE DOES A SESSION GATE EXIST AT ALL? (Section 4 -- the posture map.)
//
// `api/_resources/app-boundary.test.js` already answers a third question, the
// LICENCE half: a licence whose `app_id` is `stonedesk` cannot address
// `law_matters`. This suite is the other two, and question 1 is not covered by
// that one, because the licence boundary is DELIBERATELY OPEN for an
// unattributable licence:
//
//     "an unattributable licence is NOT gated -- the documented fallback"
//
// That fallback is correct and was argued for. But it means that for a licence
// with no `app_id` -- the whole pre-2026-09-04 population, which nobody can
// enumerate -- THE ONLY THING BETWEEN ONE APP'S SESSION AND ANOTHER APP'S DATA
// IS THE `expectedApp` ARGUMENT INSIDE EACH BRANCH.
//
// ── A STATIC VERSION WAS TRIED FIRST AND ABANDONED, and the reason generalises
// Attributing a resource map to the `verifySessionToken` call that gates it BY
// TEXT REGION over-reported in both directions: bounded backwards it picked up
// the tail of the previous branch and reported SAIRNlegacy's resources as gated
// by SAIRNdental; bounded by the next declaration it ran past its own branch
// and did it again. That is the same over-reach `removal_path_check.py` records
// about its 2500-character window, arrived at independently on a different
// file. DRIVING THE REAL HANDLER HAS NO REGION PROBLEM -- the handler decides
// and this only reads the answer.

'use strict';
const assert = require('assert');
const path = require('path');

const ROOT = path.join(__dirname, '..');
// Assembled rather than written as a literal assignment, so this file carries
// nothing credential-shaped -- the same convention
// tests/sairncare/test-alf-alerts-endpoint.js uses. Set BEFORE api/_lib/auth.js
// is required, which reads the value at module load.
process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  ['app', 'session', 'isolation', 'fixture', String(process.pid)].join('-');

const auth = require(path.join(ROOT, 'api/_lib/auth.js'));
const reg = require(path.join(ROOT, 'api/_resources'));
const HANDLER = path.join(ROOT, 'api/sd-data.js');

let n = 0;
function ok(cond, label) { assert.ok(cond, label); n++; console.log('  ok   ' + label); }
function section(s) { console.log('\n' + s); }

// THE LICENCE HASH IS DERIVED THE WAY THE HANDLER DERIVES IT, not invented.
// api/_lib/license.js documents license_hash as sha256(license_key) hex and the
// handler binds the session to THAT value. A token minted against a made-up
// hash is refused for the right reason by accident, which would make every
// refusal below meaningless. The control in section 1 caught exactly that on
// the first run of this file.
const LICENSE_KEY = 'k';
const LIC_HASH = require('crypto').createHash('sha256').update(LICENSE_KEY).digest('hex');

function token(app) {
  return auth.signSessionToken({
    app: app, role: auth.ROLES_BY_APP[app][0],
    license_hash: LIC_HASH, employee_id: 'E-ISO'
  });
}

function loadHandler() {
  delete require.cache[require.resolve(HANDLER)];
  return require(HANDLER);
}

// Drives the REAL handler with a REAL signed token. The licence lookup is
// stubbed so the licence-level boundary can be put in either state
// deliberately; every later fetch answers an honest empty 200, so a branch that
// gets PAST the session gate returns data rather than an error and the
// difference between "refused" and "reached" is unmistakable.
async function call(handler, resource, appId, sessionToken, action) {
  const out = { code: null, body: null };
  const res = { status(c) { out.code = c; return res; }, json(b) { out.body = b; return res; },
                setHeader() {} };
  const names = { url: ['SUPABASE', 'URL'].join('_'),
                  key: ['SUPABASE', 'SERVICE', 'ROLE', 'KEY'].join('_') };
  const envURL = process.env[names.url], envKey = process.env[names.key];
  const realFetch = global.fetch;
  process.env[names.url] = 'https://stub.invalid';
  process.env[names.key] = ['stub', 'fixture', 'value'].join('-');
  let first = true;
  global.fetch = async (url) => {
    if (first) {
      first = false;
      return { ok: true, status: 200, json: async () => [{ status: 'active', app_id: appId }] };
    }
    // ── THE EMPLOYEE-AUTH LOOKUP IS ANSWERED, NOT LEFT EMPTY (2026-09-16) ──
    // credentialStillActive() reads `<app>_employee_auth` and treats an EMPTY
    // result as CREDENTIAL_INACTIVE -- correctly, since a session naming an
    // employee row that does not exist is not a live credential. But this
    // harness answered every query after the licence lookup with [], so a
    // correctly signed-in caller was refused 403 by the re-check before any
    // arm here could observe the thing it was driving.
    //
    // THAT MATTERS BEYOND THE ARMS BELOW: 403 for the right reason and 403 for
    // the wrong one are the same number, so any arm asserting merely "not
    // refused" would have been measuring the stub. The row is modelled as
    // present and ACTIVE, which is the precondition for asking whether the
    // EXPECTED APP is right -- the question this file exists for.
    if (/_employee_auth\?/.test(String(url))) {
      return { ok: true, status: 200, json: async () => [{ active: true }] };
    }
    return { ok: true, status: 200, json: async () => [] };
  };
  try {
    const headers = { authorization: 'Bearer ' + LICENSE_KEY };
    if (sessionToken) headers['x-sd-auth'] = sessionToken;
    await handler({ method: 'POST', headers: headers,
                    body: { action: action || 'read', resource: resource, payload: {} } }, res);
  } finally {
    global.fetch = realFetch;
    if (envURL === undefined) delete process.env[names.url]; else process.env[names.url] = envURL;
    if (envKey === undefined) delete process.env[names.key]; else process.env[names.key] = envKey;
  }
  return out;
}

// One session-gated resource per app that has a gate, chosen for consequence.
const GATED = [
  ['sb_payruns', 'sairnbiz'],
  ['law_invoices', 'sairnlaw'],
  ['sen_claims', 'sairnsenior'],
  ['dnt_charges', 'sairndental'],
];

// ── THE POSTURE MAP: THE HAND-WRITTEN HALF ────────────────────────────────
// Whether an app SHOULD gate on a session is a judgement, and four of these
// judgements are already argued in api/sd-data.js. The rest are not written
// down anywhere, and saying so is the point of this table -- an undocumented
// posture is not the same as a decided one.
//
// `auth` is whether the app has a per-employee auth endpoint at all. An app
// with no api/<prefix>-auth.js CANNOT have a session gate; one that has it and
// gates nothing has made a choice nobody recorded.
const POSTURE = {
  sairnbiz:        { gate: 'ALL',  auth: true,  why: 'payroll history, performance scores and PIP flags; argued at SB_RESOURCES' },
  sairncare:       { gate: 'ALL',  auth: true,  why: 'eMAR and resident records' },
  sairndental:     { gate: 'ALL',  auth: true,  why: 'PHI and the financial tier' },
  sairnroofing:    { gate: 'ALL',  auth: true,  why: 'claims and claim photos' },
  sairnsenior:     { gate: 'ALL',  auth: true,  why: 'claims, pay rates and payer contracts' },
  sairnlaw:        { gate: 'SOME', auth: true,  why: 'PHASE 1 of a deliberate, sequenced rollout (2026-09-05): the fifteen generic resources are gated, four bespoke ones are not YET. See section 5' },
  sairnbuild:      { gate: 'SOME', auth: true,  why: 'DOCUMENTED at BLD_RESOURCES: the shared job record is read by every role; bld_bids and bld_tna gate because each has a real per-person visibility rule' },
  stonedesk:       { gate: 'SOME', auth: true,  why: 'DOCUMENTED at SD_LOCAL_RESOURCES: the shared shop record; personnel and financial data gate elsewhere' },
  sairnmechanical: { gate: 'SOME', auth: true,  why: 'NOT DOCUMENTED -- 2 of 6 gate and nothing records why the other four do not' },
  sairndesign:     { gate: 'SOME', auth: true,  why: 'NOT DOCUMENTED -- 1 of 18 gates (the assignment rule); nothing records the posture for the rest' },
  sairnvet:        { gate: 'NONE', auth: true,  why: 'DOCUMENTED at SV_RESOURCES: SAIRNvet has NO per-employee authentication -- role is a self-selected dropdown, never server-verified. A gate here would gate on a session that does not exist' },
  sairnfreedom:    { gate: 'NONE', auth: false, why: 'DOCUMENTED at SF_RESOURCES: no per-employee authentication either' },
  // READS are still licence-only on all 28 and that is what this column
  // measures. The WRITE posture is no longer NONE: on 2026-09-14 Michael
  // decided the six Tier A billing resources -- sc_ar, sc_claims, sc_revenue,
  // sc_denial, sc_compliance, sc_credential_scope -- require an admin or
  // biller session to WRITE, and tests/sairncode_gates.js drives that. So this
  // row is no longer NOT DOCUMENTED: the read posture is a decision now, not
  // an omission, and the open question is narrower than it was.
  sairncode:       { gate: 'NONE', auth: true,  why: 'DECIDED 2026-09-14: READS stay licence-only on all 28, deliberately; WRITES on the six Tier A billing resources require admin or biller (SC_TIER_A_WRITE_ROLES in api/sd-data.js, driven by tests/sairncode_gates.js). This column measures READS only, which is why it still says NONE' },
  sairngrounds:    { gate: 'NONE', auth: true,  why: 'NOT DOCUMENTED -- api/grd-auth.js exists; grd_invoices and msb_licenses are Tier A' },
  sairnscape:      { gate: 'NONE', auth: true,  why: 'NOT DOCUMENTED -- api/scp-auth.js exists; scp_quotes and invoices are Tier A' },
  // MEASURED MOVED, SO THIS ROW MOVED WITH IT (2026-09-21). CC's gate landed in
  // 760a34a9 and was live-verified in 30a9f179, taking sairnlegacy from measured
  // NONE to measured ALL -- and this suite FAILED until this row was updated,
  // which is the table working rather than the table being wrong.
  //
  // WHAT THE OLD VALUE ACTUALLY RECORDED, worth keeping rather than overwriting
  // silently: it said NOT DOCUMENTED for as long as the gap existed, and it was
  // right to -- 36 leg_* resources were authorised by the licence key alone,
  // including leg_custodylog, the chain-of-custody record for human remains. This
  // table never claimed the posture was SAFE, only that nobody had decided it.
  // THE GAP WAS FOUND BY THE HOVER AUDITOR, NOT BY THIS TABLE, and that is the
  // honest division: the column says whether a decision was written down, and an
  // undocumented posture is the signal to go and look, not the finding itself.
  sairnlegacy:     { gate: 'ALL',  auth: true,  why: 'DECIDED AND FIXED 2026-09-21 (CC): every leg_* resource requires a SAIRNlegacy session. Found by the hover auditor as a CRITICAL gap -- 36 resources including leg_custodylog (chain of custody for human remains) and leg_preneed (Tier A) were licence-only. Gate 760a34a9, obligation b9f1779a, live-verified 30a9f179' },
  shared:          { gate: 'NONE', auth: false, why: 'the cross-app resources. NONE of the seven answers 401 to a no-session read -- five answer something else entirely (they are not plain read/write resources), and render_usage and shared_knowledge are licence-only. Recorded rather than gated: `shared` is not an app and has no session to bind to' },
  sairncash:       { gate: 'NONE', auth: false, why: 'registers no resources on this endpoint at all' },
};

// The four SAIRNlaw resources phase 2 will move. Named rather than left out,
// because a suite that tested only the gated ones would read as "every SAIRNlaw
// resource is gated" -- the opposite of true for the most consequential one.
const PHASE_1_UNGATED = ['law_clients', 'law_matters', 'law_trusttx', 'law_deadlines'];

console.log('SAIRN: one app\'s session cannot reach another app\'s gated data\n');

section('0. the fixture really is a token, and really is app-bound');
{
  const t = token('sairnbiz');
  ok(typeof t === 'string' && t.length > 20, 'a SAIRNbiz session token is minted');
  ok(!!auth.verifySessionToken(t, LIC_HASH, 'sairnbiz'),
     'it verifies for SAIRNbiz -- so a refusal below is about the APP, not a broken fixture');
  ok(!auth.verifySessionToken(t, LIC_HASH, 'sairnlaw'),
     'and does NOT verify for SAIRNlaw at the library level');
  ok(!auth.verifySessionToken(t, 'OTHER-HASH', 'sairnbiz'),
     'nor for the same app under a different licence');
}

(async () => {
  const h = loadHandler();

  section('1. an unattributable licence -- expectedApp is the only gate left');
  for (const [resource, owner] of GATED) {
    ok(reg.OWNER_BY_RESOURCE[resource] === owner,
       resource + ' is owned by ' + owner + ' in the registry -- the fixture is not stale');
  }
  // THE CONTROL COMES FIRST, deliberately. Without it every refusal below could
  // be a resource that is simply unreachable in this harness, and the suite
  // would be asserting that nothing works.
  for (const [resource, owner] of GATED) {
    const own = await call(h, resource, null, token(owner));
    // POSITIVELY, not as `!== 401` (corrected 2026-09-16). This is the arm that
    // licenses every refusal below to mean something, and as a negation it was
    // satisfied by a 403, a 500 or a harness fault -- each of which is the
    // owner NOT reaching their own resource, i.e. exactly the state that makes
    // the refusals underneath it meaningless.
    ok(own.code === 200,
       'CONTROL: ' + owner + '\'s OWN session reaches ' + resource + ' (' + own.code
       + ') -- so a 401 below is about the app, not the harness');
  }
  for (const [resource, owner] of GATED) {
    for (const [other] of GATED) {
      if (other === resource) continue;
      const otherOwner = reg.OWNER_BY_RESOURCE[other];
      const out = await call(h, resource, null, token(otherOwner));
      ok(out.code === 401,
         otherOwner + '\'s session is REFUSED ' + resource + ' (owned by ' + owner
         + ') -- got ' + out.code);
    }
  }

  section('2. no session is not a weak session');
  for (const [resource, owner] of GATED) {
    const out = await call(h, resource, null, null);
    ok(out.code === 401,
       resource + ' with no token at all is 401, not an empty 200 that reads as "'
       + owner + ' has no records"');
  }

  section('3. with an ATTRIBUTABLE licence the boundary refuses first, and differently');
  {
    // 400, not 401: a foreign resource must stay indistinguishable from one
    // that does not exist -- the enumeration oracle app-boundary.test.js
    // closed. Pinned here so a change to the session gate cannot reopen it by
    // turning a 400 into a 401.
    const out = await call(h, 'law_invoices', 'sairnbiz', token('sairnbiz'));
    const invented = await call(h, '__no_such_resource__', 'sairnbiz', token('sairnbiz'));
    ok(out.code === invented.code,
       'a SAIRNbiz licence asking for law_invoices answers exactly as an invented name '
       + 'does (' + out.code + ') -- the oracle stays closed even with a valid session');
    // 400 BY NAME, not "anything except 401" (corrected 2026-09-16). The
    // negation was satisfied by a 500, or by a 403 from the session gate -- and
    // a 403 here would mean the session gate answered FIRST, which is the exact
    // thing this arm claims did not happen.
    ok(out.code === 400,
       '...and it is the LICENCE boundary answering with ' + out.code + ', not the '
       + 'session gate -- two locks, not one counted twice');
  }

  section('4. THE POSTURE MAP -- where a session gate exists at all');
  // MEASURED BY DRIVING, then compared with the hand-written table above. A gate
  // that silently disappears fails here; a gate that appears must be recorded.
  // The `why` column is the part a tool cannot produce, and the rows that say
  // NOT DOCUMENTED are a finding rather than a gap in this file.
  //
  // THIS COLUMN MEASURES READS, AND SINCE 2026-09-14 THAT IS A REAL LIMITATION
  // RATHER THAN A DETAIL. SAIRNcode now gates six WRITES and no reads, so its
  // verdict here is NONE while its write posture is SOME -- one app where the
  // two halves genuinely differ. Stated rather than left for a reader to infer
  // from a row that looks unchanged; the write side is driven by
  // tests/sairncode_gates.js, which is where that assertion belongs.
  const measured = {};
  for (const app of reg.APP_NAMES) {
    const names = reg.RESOURCE_NAMES_BY_APP[app] || [];
    if (!names.length) { measured[app] = 'NONE'; continue; }
    let gated = 0;
    for (const r of names) {
      // `call` returns {code, body} -- comparing the OBJECT to 401 made every
      // app measure as ungated, including ones section 2 had just proven were
      // gated. Caught because the recorded table disagreed with the
      // measurement, which is the table doing its job.
      const out = await call(h, r, null, null);
      if (out.code === 401) gated++;
    }
    measured[app] = gated === 0 ? 'NONE' : (gated === names.length ? 'ALL' : 'SOME');
  }
  for (const app of Object.keys(measured)) {
    ok(POSTURE[app] && POSTURE[app].gate === measured[app],
       app + ': measured ' + measured[app] + ', recorded '
       + ((POSTURE[app] && POSTURE[app].gate) || 'NOTHING')
       + (POSTURE[app] ? ' -- ' + POSTURE[app].why.slice(0, 90) : ' -- ADD A ROW WITH A REASON'));
  }
  const undocumented = Object.keys(POSTURE).filter((a) => /NOT DOCUMENTED/.test(POSTURE[a].why));
  ok(undocumented.length > 0,
     'CONTROL: the table really does distinguish documented from undocumented postures '
     + '(' + undocumented.length + ' undocumented: ' + undocumented.join(', ') + ') -- if this '
     + 'ever reads zero, check that the postures were WRITTEN DOWN rather than that the '
     + 'column stopped working');

  section('5. the SAIRNlaw phase-1 split -- a KNOWN state, asserted so it cannot drift');
  // NOT A FINDING. api/sd-data.js records this as PHASE 1 OF THE SESSION GATE
  // (2026-09-05): flipping these four in the same commit would have broken a
  // staff member mid-session ON TRUST-MONEY WRITES, because Vercel deploys the
  // page and the endpoint together and a cached page sends no token.
  //
  // THE TRIGGER, from the open-work row: once the fifteen have been writing
  // cleanly for a full working day with no session complaints, these four move
  // behind the same check -- AND THIS SECTION MUST THEN BE INVERTED, NOT
  // DELETED. Deleting it removes the only mechanical record the split existed.
  //
  // AND THE PART WORTH SAYING OUT LOUD: THE CANARY IS SILENCE, and a silent
  // canary and a healthy canary look identical. "No session complaints" is
  // evidence the fifteen are not FAILING; it is not evidence they are being
  // USED. The trigger cannot be confirmed from an error table alone.
  // ── THE ARM BELOW PASSED WHILE PRINTING ITS OWN REFUTATION ───────────────
  // Until 2026-09-16 this loop asserted `out.code !== 401` and ran over all
  // four resources. law_trusttx was gated on 2026-09-16 and SD_SESSION_GATED
  // refuses with 403 FORBIDDEN, not 401 -- so the arm stayed GREEN and printed:
  //
  //   ok  PHASE 1 (2026-09-05, still open): law_trusttx is reachable with the
  //       LICENCE ALONE -- no session -- and answers 403
  //
  // The message interpolates the status code that disproves the sentence it is
  // asserting. REACHABILITY WAS ENCODED AS THE NEGATION OF ONE REFUSAL CODE,
  // and the refusal that arrived was the other one. This file's own comment,
  // six lines up, says a silent canary and a healthy canary look identical --
  // and this is a canary that sang the wrong note and was counted as singing.
  //
  // Two changes, both of them the point: reachability is asserted POSITIVELY as
  // 200, and the gated resource is in its own list with the inversion the
  // section asked for. Never `!== <one code>` for "it got through".
  // PHASE 2 COMPLETED 2026-09-22. The remaining three moved into the shared
  // SD_SESSION_GATED table with sairnlaw expectedApp entries, so STILL_UNGATED
  // derives to EMPTY and the loop below runs zero times -- which is the arm
  // being INVERTED by the mechanism it was written with, exactly as its own
  // instruction asked, rather than by deleting anything. The emptiness is
  // asserted immediately after, so a resource re-opened later cannot vanish
  // from this boundary by leaving both lists.
  const PHASE_2_GATED = ['law_trusttx', 'law_clients', 'law_matters', 'law_deadlines'];
  const STILL_UNGATED = PHASE_1_UNGATED.filter((r) => PHASE_2_GATED.indexOf(r) === -1);

  ok(STILL_UNGATED.length === 0,
     'PHASE 1 IS CLOSED (2026-09-22): no SAIRNlaw resource on the original four is '
     + 'reachable with the LICENCE ALONE. STILL_UNGATED derives to '
     + (STILL_UNGATED.join(', ') || 'nothing') + ' -- if that is ever non-empty '
     + 'again, a resource went back to being authorised by a key shipped to the '
     + 'browser');
  for (const resource of STILL_UNGATED) {
    const out = await call(h, resource, null, null);
    ok(out.code === 200,
       'PHASE 1: ' + resource + ' is reachable with the LICENCE ALONE -- no session '
       + '-- and answers ' + out.code);
  }
  for (const resource of PHASE_2_GATED) {
    const out = await call(h, resource, null, null);
    ok(out.code === 403 && out.body && out.body.error
       && out.body.error.code === 'FORBIDDEN',
       'PHASE 2 (law_trusttx 2026-09-16, the other three 2026-09-22 -- ALL DONE): '
       + resource + ' is REFUSED without a session and answers ' + out.code + ' '
       + ((out.body && out.body.error && out.body.error.code) || '?')
       + ' -- law_trusttx is attorney CLIENT TRUST MONEY, the one balance a bar '
       + 'association audits, and law_matters names the client and the matter');
  }
  // ── AND THE EXPECTED APP, WHICH IS THIS WHOLE FILE'S SUBJECT ─────────────
  // Added 2026-09-16 after a negative control emptied SD_GATE_APP -- reverting
  // law_trusttx's expected app to the hardcoded 'stonedesk' -- and this suite
  // stayed SILENT. Every arm above drives the newest gated resource with NO
  // session, and a refusal with no session is the same 403 whichever app the
  // gate was expecting. The mutation is only visible to a caller who IS signed
  // in, correctly, to the right app.
  //
  // That is not a small omission here: the header of this file says that for an
  // unattributable licence, the expectedApp argument is THE ONLY THING between
  // one app's session and another's data. A suite about expectedApp that cannot
  // see expectedApp being emptied is measuring the other half.
  //
  // The failure it prevents is the one with the misleading symptom: with the
  // expected app wrong, every correctly signed-in attorney is refused, and the
  // obvious repair for THAT is to take the gate off.
  for (const resource of PHASE_2_GATED) {
    const right = await call(h, resource, null, token('sairnlaw'));
    // ── AND THIS ARM WAS `!== 403` WHEN IT WAS WRITTEN, 38 LINES BELOW A
    //    COMMENT SAYING "Never `!== <one code>` for it got through" ─────────
    // Corrected 2026-09-16 in the same round that found the original. The class
    // does not announce itself at the moment of writing: `!== 403` reads as
    // "not refused by the gate", which is the question -- and it is satisfied
    // by a 401, a 500, and by the harness throwing. Every one of those is a
    // SAIRNlaw session failing to reach its own resource, which is precisely
    // what this arm exists to detect.
    ok(right.code === 200,
       'a correctly signed-in SAIRNlaw session REACHES ' + resource + ' (' + right.code
       + ') -- anything but 200 means a legitimate attorney is being turned away, '
       + 'and if it is 403 the gate is verifying against the wrong app');
    const wrong = await call(h, resource, null, token('sairnbiz'));
    ok(wrong.code === 403,
       '...and a SAIRNbiz session is REFUSED ' + resource + ' (' + wrong.code
       + ') -- so the arm above is about the APP, not about any session working');
  }
  ok(STILL_UNGATED.length + PHASE_2_GATED.length === PHASE_1_UNGATED.length
     && PHASE_2_GATED.every((r) => PHASE_1_UNGATED.indexOf(r) !== -1),
     'the two phase lists PARTITION the original four, so a resource cannot '
     + 'leave the boundary by being dropped from one without joining the other');
  ok(PHASE_1_UNGATED.indexOf('law_trusttx') !== -1,
     '...and the original list still names law_trusttx: attorney CLIENT TRUST MONEY, '
     + 'Tier A, the one balance a bar association audits, with no removal path. If it '
     + 'leaves this list because it was gated, move it to PHASE_2_GATED; if it leaves '
     + 'because somebody trimmed the list, that is a defect');

  console.log('\nALL ' + n + ' ASSERTIONS PASS');
})().catch((e) => { console.error('\nFAILED: ' + (e && e.message)); process.exit(1); });
