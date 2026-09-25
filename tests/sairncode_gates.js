// tests/sairncode_gates.js
//
// Run:  node tests/sairncode_gates.js
//
// SAIRNCODE OWNS 28 REGISTERED RESOURCES AND HAD ZERO TEST FILES.
//
// docs/MASTER-PLAN.md's gate 3 table said `sairncode | 28 | OK | 0 | 0 | 0 |
// **no dedicated suite** - **no fault probe**` -- the largest resource count of
// any app with no suite at all, and the one whose Tier A list is sharpest:
// sc_ar, sc_claims, sc_revenue, sc_denial, sc_compliance and sc_credential_scope
// are medical-billing records.
//
// ── WHAT THIS SUITE IS FOR, AND WHAT IT DELIBERATELY DOES NOT DO ────────────
// SAIRNcode HAS three real server-side controls, every one of them written
// because a client-side check is not a boundary, and NOTHING EXERCISED ANY OF
// THEM:
//
//   1. removal on all 28 resources requires an `admin` session -- and as of
//      2026-09-15 (item 97) the SEVEN Tier A records grant `soft_delete`
//      rather than a destroying `delete`, so the gate now has two halves:
//      who may remove, and whether removal can destroy at all
//   2. `sc_settings` WRITE requires an `admin` session (practice-level settings)
//   3. `sc_auth_requests` SIGN-OFF requires an `admin` session, and the server
//      sets signedOffBy FROM THE SESSION rather than from the payload
//
// plus a value control, the retention floor, which applies to admins too --
// "a role check and a value check are different controls and neither replaces
// the other", in the handler's own words.
//
// IT DOES NOT CHANGE THE POSTURE, AND SECTION 5 IS WHY. Every OTHER read and
// ordinary write on this app is licence-only: no employee session is required. That is
// an open finding in docs/SAIRN-OPEN-WORK-INDEX.md and a decision for Michael,
// not a thing to quietly fix inside a test. So section 5 MEASURES the posture
// resource by resource against a hand-written table, which means a gate that
// silently appears fails this suite just as loudly as one that silently
// disappears. An undocumented posture is not a decided one; an unmeasured one
// is not even visible.
//
// ── DRIVEN, NOT READ ────────────────────────────────────────────────────────
// Same harness and the same reasoning as tests/app_session_isolation.js: a
// static scan that attributes a gate to a resource BY TEXT REGION over-reports
// in both directions, which that file records and `removal_path_check.py`
// records independently about its own 2500-character window. The handler
// decides; this only reads the answer.

'use strict';
const assert = require('assert');
const crypto = require('crypto');
const path = require('path');

const ROOT = path.join(__dirname, '..');
// Assembled rather than written as a literal assignment, so this file carries
// nothing credential-shaped -- the convention tests/app_session_isolation.js
// and tests/sairncare/test-alf-alerts-endpoint.js already use. Set BEFORE
// api/_lib/auth.js is required, which reads the value at module load.
process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  ['sairncode', 'gates', 'fixture', String(process.pid)].join('-');

const auth = require(path.join(ROOT, 'api/_lib/auth.js'));
const reg = require(path.join(ROOT, 'api/_resources'));
const SC = require(path.join(ROOT, 'api/_resources/sairncode.js'));
const HANDLER = path.join(ROOT, 'api/sd-data.js');

let n = 0;
function ok(cond, label) { assert.ok(cond, label); n++; console.log('  ok   ' + label); }
function section(s) { console.log('\n' + s); }

// THE LICENCE HASH IS DERIVED THE WAY THE HANDLER DERIVES IT. A token minted
// against a made-up hash is refused for the right reason BY ACCIDENT, which
// would make every refusal below meaningless. Section 0's control is what keeps
// that honest.
const LICENSE_KEY = 'k';
const LIC_HASH = crypto.createHash('sha256').update(LICENSE_KEY).digest('hex');
const ROLES = auth.ROLES_BY_APP.sairncode;

function token(role, app, licHash) {
  return auth.signSessionToken({
    app: app || 'sairncode', role: role,
    license_hash: licHash || LIC_HASH, employee_id: 'E-' + role.toUpperCase()
  });
}

function loadHandler() {
  delete require.cache[require.resolve(HANDLER)];
  return require(HANDLER);
}

// Drives the REAL handler. The licence lookup answers an active, UNATTRIBUTABLE
// licence -- app_id null -- deliberately: that is the documented pre-2026-09-04
// fallback and the population nobody can enumerate, so it is the state in which
// the per-branch session checks are the ONLY thing left. Every later fetch
// answers an honest empty 200, so a request that gets PAST a gate comes back
// 200 and the difference between "refused" and "reached" is unmistakable.
//
// `sawUpstream` is the arm that makes "reached" a fact rather than an
// inference: it records whether the handler actually issued a request to
// storage. A 200 with no upstream call would be a branch that answered early.
async function call(handler, opts) {
  const out = { code: null, body: null, sawUpstream: false, upstreamMethods: [] };
  const res = { status(c) { out.code = c; return res; }, json(b) { out.body = b; return res; },
                setHeader() {} };
  const names = { url: ['SUPABASE', 'URL'].join('_'),
                  key: ['SUPABASE', 'SERVICE', 'ROLE', 'KEY'].join('_') };
  const envURL = process.env[names.url], envKey = process.env[names.key];
  const realFetch = global.fetch;
  process.env[names.url] = 'https://stub.invalid';
  process.env[names.key] = ['stub', 'fixture', 'value'].join('-');
  let first = true;
  global.fetch = async (url, init) => {
    if (first) {
      first = false;
      // The licence row. app_id null = unattributable, the documented fallback.
      return { ok: true, status: 200, json: async () => [{ status: 'active', app_id: null }] };
    }
    out.sawUpstream = true;
    out.upstreamMethods.push((init && init.method) || 'GET');
    return { ok: true, status: 200, json: async () => [] };
  };
  try {
    const headers = { authorization: 'Bearer ' + LICENSE_KEY };
    if (opts.token) headers['x-sd-auth'] = opts.token;
    await handler({ method: 'POST', headers: headers,
                    body: { action: opts.action, resource: opts.resource,
                            payload: opts.payload === undefined ? {} : opts.payload } }, res);
  } finally {
    global.fetch = realFetch;
    if (envURL === undefined) delete process.env[names.url]; else process.env[names.url] = envURL;
    if (envKey === undefined) delete process.env[names.key]; else process.env[names.key] = envKey;
  }
  return out;
}

// ── THE POSTURE, HAND-WRITTEN ───────────────────────────────────────────────
// Read from api/sd-data.js's SAIRNcode branch on 2026-09-14 and written out
// here so a CHANGE fails rather than passes. ONE resource carries an
// unconditional write gate and one more carries a conditional one; no resource
// carries a read gate; all 28 carry a delete gate.
//
// TWO KINDS OF WRITE GATE, AND CONFLATING THEM OVERSTATES THE POSTURE. The
// first version of this table listed sc_auth_requests as write-gated and the
// suite failed against the handler, correctly: sc_auth_requests gates only the
// SIGN-OFF write, so an ordinary write to it is open, exactly like the other
// 26. Recording it as "gated" would have said 2 of 28 resources require a
// session to write when the true figure is 1 -- a posture map that flatters the
// app is worse than none, because it is the document somebody would cite.
//
// So the unconditional gate is measured here, and the conditional one is
// measured in section 4 where the condition can actually be expressed.
const WRITE_GATED = {
  // Practice-level settings: the practice name printed on output, the payer
  // payment-cycle reference, the records-retention policy. Not one coder's
  // preferences, so one coder must not change what the whole practice sees.
  // EVERY write to this resource is gated, which is what makes it measurable
  // by a plain write.
  sc_settings: 'admin',
  // ── THE SIX TIER A BILLING RESOURCES (2026-09-14, Michael's decision) ─────
  // These six were the FINDING this suite recorded on 2026-09-14: all 28
  // resources accepted an ordinary write with the licence key alone, and six of
  // them are Tier A medical-billing records. The decision was to narrow the
  // WRITE to a real role gate and leave the READ licence-only, so the table
  // moves from 1 write-gated to 7 -- and this suite failed on the change until
  // the table was updated, which is the direction that failure should run. The
  // handler is the fact; this is the claim; a disagreement is a finding.
  sc_ar: 'admin|biller',
  sc_claims: 'admin|biller',
  sc_revenue: 'admin|biller',
  sc_denial: 'admin|biller',
  sc_compliance: 'admin|biller|auditor',   // a per-resource override; there are two
  sc_credential_scope: 'admin|biller',
  // ── THE SEVENTH, ADDED 2026-09-15 AFTER A LIVE PROBE FOUND IT OPEN ────────
  // The 2026-09-14 gate was a hand-written list of SIX and the register says
  // SEVEN sc_* resources are Tier A. Measured against the deployed function on
  // 2026-09-15: the other six answered 401 NO_SESSION to a write carrying the
  // LICENCE KEY ALONE, and sc_denial_events answered 200. "The event history an
  // appeal is argued from" took a write from anybody holding the licence
  // string this app documents as not being auth.
  //
  // Nothing compared the two lists, which is why nothing noticed. The handler
  // derives the gate from the pinned Tier A list now, so this table is the
  // third opinion rather than a second copy -- and it failed the moment the
  // posture changed, which is the direction that failure should run.
  sc_denial_events: 'admin|biller',
  // ── SEVEN BECAME TWENTY-THREE, 2026-09-23 ─────────────────────────────────
  // THE TABLE ABOVE IS THE CLAIM AND THE HANDLER IS THE FACT, which is why it
  // is spelled out one resource at a time rather than generated from the same
  // list the handler uses -- a table derived from its own subject agrees with
  // itself by construction and checks nothing.
  //
  // Sixteen sc_* resources were re-tiered A between 2026-09-15 and 2026-09-23,
  // and because SC_TIER_A_WRITE_GATED derives from the pinned Tier A list, all
  // sixteen SHOULD have become write-gated automatically. They did not, because
  // the pinned list itself had not been updated -- so for eight days every one
  // of them accepted a write carrying the LICENCE KEY ALONE and could be
  // hard-deleted. This suite's arm 1 was RED for those eight days and nothing
  // required anybody to look.
  //
  // THREE OF THE SIXTEEN ARE WHY THIS IS NOT BOOKKEEPING: sc_hcc is a named
  // patient joined to a diagnosis grouping and its dollar value; sc_eligibility
  // is a named patient joined to payer and plan; sc_providers carries the QP
  // status that selects between two CMS conversion factors, so a write from
  // anybody holding the licence string changes what every unit billed under
  // that provider is worth.
  sc_anesthesia: 'admin|biller',
  sc_anesthesia_base_units: 'admin|biller',
  sc_auth: 'admin|biller',
  // AND IT MOVES OUT OF CONDITIONALLY_WRITE_GATED BELOW. Its sign-off gate is
  // still admin-only and still narrower than this; what changed is that an
  // ORDINARY write now needs a session too, so it is unconditionally gated and
  // the conditional table no longer describes it.
  sc_auth_requests: 'admin|biller',
  // ── THE SECOND OVERRIDE, AND THIS CELL WAS WRONG FOR TWO DAYS (2026-09-25) ─
  // It read 'admin|biller'. The handler grants ['admin','biller','coder'] --
  // sc_coded_items is the coder's own resource and the override admits them,
  // which is the half that makes the sc_claims coder-exclusion a split rather
  // than a lockout. Nothing caught the disagreement because until today only
  // Object.keys() of this table was ever read: the RESOURCE half was checked
  // against the handler and the ROLE half was decoration, in a table whose own
  // header says in capitals that it is the claim and a disagreement is a
  // finding. Arm 5b below now reads the values, so this cell is load-bearing.
  sc_coded_items: 'admin|biller|coder',
  sc_dme: 'admin|biller',
  sc_drg: 'admin|biller',
  sc_eligibility: 'admin|biller',
  sc_fraud: 'admin|biller',
  sc_hcc: 'admin|biller',
  // sc_pctc joined 2026-09-25 with its Tier A promotion (integrity: a wrong
  // PC/TC indicator is a wrong billing instruction on every future check of
  // that code). The seam test below is what demanded this row move with the
  // register -- the same route the sixteen of 2026-09-23 took.
  sc_pctc: 'admin|biller',
  sc_prebill: 'admin|biller',
  sc_providers: 'admin|biller',
  sc_query: 'admin|biller',
  sc_rac: 'admin|biller',
  sc_telehealth: 'admin|biller',
};
// Read from api/sd-data.js rather than retyped, for the same reason
// SB_VOID_ROLES is read out of sairnbiz.html in tests/sairnbiz_void_not_delete.js:
// a hardcoded ['admin','biller'] here would keep passing after somebody widened
// the constant, which is the one change this suite most needs to notice.
const TIER_A_ROLES = (() => {
  const src = require('fs').readFileSync(path.join(ROOT, 'api/sd-data.js'), 'utf8');
  const m = /const SC_TIER_A_WRITE_ROLES = (\[[^\]]*\]);/.exec(src);
  assert.ok(m, 'SC_TIER_A_WRITE_ROLES not found in api/sd-data.js');
  return JSON.parse(m[1].replace(/'/g, '"'));
})();
// ── IT IS DERIVED NOW, NOT A LITERAL (2026-09-15) ──────────────────────────
// This used to parse an array literal out of api/sd-data.js. That literal was a
// HAND-WRITTEN list of six while the register says seven are Tier A, and
// sc_denial_events -- the one missing -- accepted a write from the LICENCE KEY
// ALONE on the deployed function while the other six answered 401. Measured
// live on 2026-09-15, not inferred.
//
// The handler now derives the gate from the same pinned list the removal verbs
// use, so this reads the DERIVATION rather than a copy: if somebody puts a
// literal back, the regex below stops matching and this suite fails loudly
// instead of silently checking a list nobody maintains.
const TIER_A_GATED = (() => {
  const src = require('fs').readFileSync(path.join(ROOT, 'api/sd-data.js'), 'utf8');
  const derived = /const SC_TIER_A_WRITE_GATED = SC_TIER_A_SOFT_DELETE_ONLY;/.test(src);
  assert.ok(derived,
    'SC_TIER_A_WRITE_GATED is no longer derived from SC_TIER_A_SOFT_DELETE_ONLY. '
    + 'It was a hand-written list of six once and the register said seven; '
    + 'sc_denial_events took a write with no session for a day because of it.');
  return SC.tierASoftDeleteOnly.slice();
})();
// ── THE PER-RESOURCE OVERRIDE (2026-09-14) ─────────────────────────────────
// Michael added `auditor` to sc_compliance and left `coder` off sc_claims. Both
// are read out of api/sd-data.js rather than retyped, so a widened list fails
// here instead of being ratified by a test that agreed with itself. Section 6
// drives allowed and denied PER RESOURCE as a result: its first version asked
// "every disallowed role on every one of the six" and went red the moment one
// resource departed from the shared list -- which is the arm doing its job, but
// a blanket claim is the wrong shape once an exception exists.
const TIER_A_OVERRIDES = (() => {
  const src = require('fs').readFileSync(path.join(ROOT, 'api/sd-data.js'), 'utf8');
  const m = /const SC_TIER_A_WRITE_ROLES_BY_RESOURCE = \{([\s\S]*?)\};/.exec(src);
  assert.ok(m, 'SC_TIER_A_WRITE_ROLES_BY_RESOURCE not found in api/sd-data.js');
  const out = {};
  const re = /(\w+)\s*:\s*\[([^\]]*)\]/g;
  let e;
  while ((e = re.exec(m[1])) !== null) {
    out[e[1]] = JSON.parse('[' + e[2].replace(/'/g, '"').replace(/,\s*$/, '') + ']');
  }
  return out;
})();
// ── AND ONE RESOURCE IS NARROWED BY A SECOND GATE IN A DIFFERENT BRANCH ────
// sc_settings passes the Tier A gate as `admin|biller` and is then refused by
// its OWN admin-only branch a few lines below it, which has been there since
// 2026-08-20 and is not in SC_TIER_A_WRITE_ROLES_BY_RESOURCE. So the EFFECTIVE
// allowed set is the intersection, and nothing expressed that until sc_settings
// joined the Tier A list on 2026-09-23 -- at which point the "every ALLOWED
// role reaches storage" control failed 46/47, correctly, on a biller that the
// handler was right to refuse.
//
// DERIVED FROM THE BRANCH, NOT TYPED, and it FAILS CLOSED: if that check is
// reworded or removed, the regex stops matching and this suite refuses rather
// than quietly widening sc_settings back to admin|biller. Same discipline as
// TIER_A_ROLES and TIER_A_OVERRIDES above -- read the handler, never a copy.
const SECOND_GATE_NARROWING = (() => {
  const src = require('fs').readFileSync(path.join(ROOT, 'api/sd-data.js'), 'utf8');
  const m = /if \(resource === 'sc_settings'\) \{[\s\S]{0,400}?scSetCaller\.role !== '(\w+)'/
    .exec(src);
  assert.ok(m,
    "sc_settings' own role check was not found in api/sd-data.js. It narrowed "
    + 'the Tier A gate to a single role; if it is gone, sc_settings is now '
    + 'writable by every Tier A role and that is a posture change nobody '
    + 'declared. Refusing rather than assuming either way.');
  return { sc_settings: [m[1]] };
})();
const rolesFor = (resource) =>
  SECOND_GATE_NARROWING[resource] || TIER_A_OVERRIDES[resource] || TIER_A_ROLES;
// Gated only on a specific payload shape. Creating a draft, editing before
// review and logging a payer decision after the fact are all open; making a
// request SUBMISSION-READY is not. Section 4 drives both halves.
//
// ── EMPTY SINCE 2026-09-23, AND KEPT RATHER THAN DELETED ───────────────────
// sc_auth_requests was the only entry. It is now UNCONDITIONALLY write-gated
// as a Tier A resource, so a plain write no longer reads as open and the
// conditional description stopped being true. The sign-off gate itself is
// unchanged and is still narrower than the resource gate -- section 4 drives
// both halves and asserts a biller can do an ordinary write while being
// refused sign-off, which is the property this table existed to keep visible.
//
// The table stays because the SHAPE is real and the next resource to grow a
// payload-conditional gate belongs here; an empty table with a reason reads
// differently from a deleted one.
const CONDITIONALLY_WRITE_GATED = {};

console.log('SAIRNcode: the three server-side gates, and the posture of the '
            + 'other 27\n');

// ── 0. THE FIXTURE ──────────────────────────────────────────────────────────
section('0. the fixture is a real token, really app-bound and really licence-bound');
{
  ok(Array.isArray(ROLES) && ROLES.indexOf('admin') === 0,
     'SAIRNcode\'s role vocabulary is read from ROLES_BY_APP and admin is the '
     + 'bootstrap role: ' + ROLES.join('|'));
  const t = token('admin');
  ok(!!auth.verifySessionToken(t, LIC_HASH, 'sairncode'),
     'an admin token verifies for sairncode -- so a refusal below is about the '
     + 'GATE, not a broken fixture');
  ok(!auth.verifySessionToken(t, LIC_HASH, 'sairnbiz'),
     'CONTROL: it does NOT verify for sairnbiz, so the app claim is load-bearing');
  ok(!auth.verifySessionToken(t, 'OTHER-HASH', 'sairncode'),
     'CONTROL: nor for the same app under a different licence hash');
  ok(SC.resources.length === 28,
     'the registry still owns 28 SAIRNcode resources -- ' + SC.resources.length);
  const missing = SC.resources.filter((r) => reg.OWNER_BY_RESOURCE[r] !== 'sairncode');
  ok(missing.length === 0,
     'and every one is owned by sairncode in the shared registry'
     + (missing.length ? ' -- NOT: ' + missing.join(', ') : ''));
}

(async () => {
  const h = loadHandler();

  // ── 1. THE DELETE GATE ────────────────────────────────────────────────────
  // The strongest control this app has, on every resource it owns, and nothing
  // exercised it. SAIRNcode is also the ONLY app on the platform where every
  // registered resource declares a removal verb (removal_path_check.py:
  // "SAIRNcode 28/28"), so this gate is the whole of what stands between a
  // licence key and a deleted claims record.
  section('1. removal requires an ADMIN session -- and 7 may never be destroyed');
  {
    const nonAdmin = ROLES.filter((r) => r !== 'admin');
    ok(nonAdmin.length > 0, 'CONTROL: there are non-admin roles to refuse -- '
       + nonAdmin.join(', '));

    // ── THE SEVEN, AND THE PIN THAT KEEPS THE LIST HONEST (2026-09-15) ──────
    // Item 97: a Tier A record may be HIDDEN and never destroyed. The list is
    // read from the registry, and then pinned against docs/CRITICALITY-TIERS.md
    // IN BOTH DIRECTIONS -- a resource tiered A there without a verb change
    // here fails, and a name added here that is not Tier A fails too. Without
    // the pin this is one more hand-kept copy of a list, which is the exact
    // shape item 97 is about.
    const SOFT_ONLY = SC.tierASoftDeleteOnly;
    ok(Array.isArray(SOFT_ONLY) && SOFT_ONLY.length > 0,
       'api/_resources/sairncode.js exports tierASoftDeleteOnly -- '
       + (SOFT_ONLY || []).length + ' name(s)');
    {
      const md = require('fs').readFileSync(
        path.join(ROOT, 'docs/CRITICALITY-TIERS.md'), 'utf8');
      const tierA = [];
      for (const line of md.split('\n')) {
        const m = /^\|\s*`(sc_[a-z_]+)`\s*\|\s*\*\*A\*\*\s*\|/.exec(line);
        if (m) tierA.push(m[1]);
      }
      ok(tierA.length > 0,
         'CONTROL: the register really does mark sc_* rows Tier A -- '
         + tierA.length + ' found, so the comparison below is not vacuous');
      ok(tierA.slice().sort().join(',') === SOFT_ONLY.slice().sort().join(','),
         'the soft-delete-only list EQUALS the Tier A sc_* rows in '
         + 'docs/CRITICALITY-TIERS.md, both directions -- register ['
         + tierA.slice().sort().join(', ') + ']');
    }
    const hardDeletable = SC.resources.filter((r) => SOFT_ONLY.indexOf(r) === -1);
    ok(hardDeletable.length === SC.resources.length - SOFT_ONLY.length,
       'CONTROL: the two sets partition the 28 -- ' + hardDeletable.length
       + ' hard-deletable + ' + SOFT_ONLY.length + ' soft-only');

    let refusedNoSession = 0, refusedNonAdmin = 0, reachedAsAdmin = 0;
    const leaks = [];
    for (const resource of hardDeletable) {
      const anon = await call(h, { resource, action: 'delete', payload: { id: 'X1' } });
      if (anon.code === 403 && !anon.sawUpstream) refusedNoSession += 1;
      else leaks.push(resource + ' (no session -> ' + anon.code
                      + (anon.sawUpstream ? ', REACHED STORAGE' : '') + ')');

      const coder = await call(h, { resource, action: 'delete', payload: { id: 'X1' },
                                    token: token(nonAdmin[0]) });
      if (coder.code === 403 && !coder.sawUpstream) refusedNonAdmin += 1;
      else leaks.push(resource + ' (' + nonAdmin[0] + ' -> ' + coder.code
                      + (coder.sawUpstream ? ', REACHED STORAGE' : '') + ')');

      const admin = await call(h, { resource, action: 'delete', payload: { id: 'X1' },
                                    token: token('admin') });
      if (admin.code === 200 && admin.upstreamMethods.indexOf('DELETE') !== -1) reachedAsAdmin += 1;
      else leaks.push(resource + ' (admin -> ' + admin.code + ', methods '
                      + JSON.stringify(admin.upstreamMethods) + ')');
    }
    const HD = hardDeletable.length;
    ok(refusedNoSession === HD,
       'all ' + HD + ' hard-deletable refuse a delete with NO session, 403, '
       + 'without touching storage -- ' + refusedNoSession + '/' + HD);
    ok(refusedNonAdmin === HD,
       'all ' + HD + ' refuse a delete from a signed-in ' + nonAdmin[0]
       + ' the same way -- ' + refusedNonAdmin + '/' + HD);
    // WITHOUT THIS ARM THE TWO ABOVE WOULD PASS ON A HANDLER THAT REFUSED
    // EVERY DELETE FOR ANY REASON, INCLUDING A BROKEN ONE.
    ok(reachedAsAdmin === HD,
       'CONTROL: all ' + HD + ' DO reach storage with a real admin session, and '
       + 'with an actual DELETE -- ' + reachedAsAdmin + '/' + HD);

    // ── THE SEVEN: DESTROY IS REFUSED FOR EVERYONE, INCLUDING ADMIN ─────────
    // The arm that would have been green before this change and is the whole
    // point of it. `admin` is the role that COULD destroy every one of these
    // until today, so asserting a non-admin refusal would prove nothing.
    //
    // ANY REFUSAL COUNTS AND ONLY A DELETE REACHING STORAGE IS A FAILURE. Two
    // guards can answer -- checkEnvelope rejects the verb the registry no
    // longer grants, and the handler's own SOFT_DELETE_ONLY branch answers if
    // the lists ever disagree -- and pinning one status would make this fail
    // when the other correct guard fires first.
    let destroyRefused = 0;
    for (const resource of SOFT_ONLY) {
      const admin = await call(h, { resource, action: 'delete', payload: { id: 'X1' },
                                    token: token('admin') });
      if (admin.code !== 200 && admin.upstreamMethods.indexOf('DELETE') === -1) destroyRefused += 1;
      else leaks.push(resource + ' (admin DESTROYED it -> ' + admin.code
                      + ', methods ' + JSON.stringify(admin.upstreamMethods) + ')');
    }
    ok(destroyRefused === SOFT_ONLY.length,
       'all ' + SOFT_ONLY.length + ' Tier A records refuse a destroying delete '
       + 'even from an ADMIN, and none issues a DELETE to storage -- '
       + destroyRefused + '/' + SOFT_ONLY.length);

    // ── THE SECOND GUARD, DRIVEN IN THE ONLY STATE IT EXISTS FOR ────────────
    // The arm above is answered by checkEnvelope, which refuses a verb the
    // registry does not grant. The handler carries its OWN refusal underneath
    // it, for the case the two ever disagree -- and while they agree, that
    // branch is unreachable and therefore untested.
    //
    // THE MUTATION CONTROL PROVED THAT RATHER THAN MY READING IT: deleting the
    // handler's guard left this suite entirely GREEN. An untested guard on a
    // destroy path is worth very little, and "it can never be reached" is the
    // sentence that precedes finding out otherwise.
    //
    // So the disagreement is CREATED here, in process, by granting `delete`
    // back to sc_claims in the shared registry object the handler reads -- the
    // exact shape of a registry edit that forgot the handler -- and the
    // handler's own refusal is then the only thing standing. Restored in a
    // finally, and the restore is asserted rather than assumed.
    {
      const before = reg.EXTRA_ACTIONS.sc_claims;
      let widened;
      try {
        reg.EXTRA_ACTIONS.sc_claims = ['delete', 'soft_delete'];
        widened = await call(h, { resource: 'sc_claims', action: 'delete',
                                  payload: { id: 'X1' }, token: token('admin') });
      } finally {
        reg.EXTRA_ACTIONS.sc_claims = before;
      }
      ok(widened.code === 403 && widened.body
         && widened.body.error && widened.body.error.code === 'SOFT_DELETE_ONLY',
         'DEFENCE IN DEPTH: with the registry wrongly granting `delete` on '
         + 'sc_claims, the handler still refuses with SOFT_DELETE_ONLY -- '
         + widened.code + ' ' + ((widened.body || {}).error || {}).code);
      ok(widened.upstreamMethods.indexOf('DELETE') === -1,
         '...and it never issued a DELETE to storage: '
         + JSON.stringify(widened.upstreamMethods));
      ok(reg.EXTRA_ACTIONS.sc_claims === before
         && reg.EXTRA_ACTIONS.sc_claims.indexOf('delete') === -1,
         'CONTROL: the registry object was restored, so no later arm inherits '
         + 'the widened grant');
    }

    // ── ...AND soft_delete IS GATED THE SAME WAY THE HARD DELETE WAS ────────
    // This narrows what the verb DOES, not who may call it. If the role gate
    // had been dropped in the same change, every arm above would still pass.
    let softAnon = 0, softNonAdmin = 0, softReached = 0;
    for (const resource of SOFT_ONLY) {
      const anon = await call(h, { resource, action: 'soft_delete', payload: { id: 'X1' } });
      if (anon.code === 403 && !anon.sawUpstream) softAnon += 1;
      else leaks.push(resource + ' (soft, no session -> ' + anon.code + ')');

      const coder = await call(h, { resource, action: 'soft_delete', payload: { id: 'X1' },
                                    token: token(nonAdmin[0]) });
      if (coder.code === 403 && !coder.sawUpstream) softNonAdmin += 1;
      else leaks.push(resource + ' (soft, ' + nonAdmin[0] + ' -> ' + coder.code + ')');

      // The stub answers every storage read with [], so a reached soft_delete
      // ends at the honest 404 -- "no record with that id, nothing was removed"
      // -- having issued a GET and never a DELETE. That is the shape being
      // asserted: it got past the gate, it looked, and it destroyed nothing.
      const admin = await call(h, { resource, action: 'soft_delete', payload: { id: 'X1' },
                                    token: token('admin') });
      if (admin.sawUpstream && admin.upstreamMethods.indexOf('DELETE') === -1
          && admin.code === 404) softReached += 1;
      else leaks.push(resource + ' (soft, admin -> ' + admin.code + ', methods '
                      + JSON.stringify(admin.upstreamMethods) + ')');
    }
    ok(softAnon === SOFT_ONLY.length,
       'all ' + SOFT_ONLY.length + ' refuse soft_delete with NO session -- '
       + softAnon + '/' + SOFT_ONLY.length);
    ok(softNonAdmin === SOFT_ONLY.length,
       'all ' + SOFT_ONLY.length + ' refuse soft_delete from a signed-in '
       + nonAdmin[0] + ' -- ' + softNonAdmin + '/' + SOFT_ONLY.length);
    ok(softReached === SOFT_ONLY.length,
       'CONTROL: all ' + SOFT_ONLY.length + ' DO reach storage as admin, with a '
       + 'GET and never a DELETE, answering 404 on a row that is not there -- '
       + softReached + '/' + SOFT_ONLY.length);

    // ── AND THE READ EXCLUDES THEM, without which the hiding is cosmetic ────
    // A soft delete that the next read returns anyway is not a delete at all.
    // Asserted from the REQUEST THE HANDLER ISSUES, not from the response,
    // because the stub has no rows to filter.
    {
      const urls = [];
      const realFetch = global.fetch;
      let seen = 0;
      const names = { url: ['SUPABASE', 'URL'].join('_'),
                      key: ['SUPABASE', 'SERVICE', 'ROLE', 'KEY'].join('_') };
      const envURL = process.env[names.url], envKey = process.env[names.key];
      process.env[names.url] = 'https://stub.invalid';
      process.env[names.key] = ['stub', 'fixture', 'value'].join('-');
      global.fetch = async (url) => {
        seen += 1;
        if (seen > 1) urls.push(String(url));
        return { ok: true, status: 200,
                 json: async () => (seen === 1 ? [{ status: 'active', app_id: null }] : []) };
      };
      try {
        for (const resource of SOFT_ONLY.concat(hardDeletable.slice(0, 3))) {
          seen = 0;
          const res2 = { status() { return res2; }, json() { return res2; }, setHeader() {} };
          await h({ method: 'POST', headers: { authorization: 'Bearer ' + LICENSE_KEY },
                    body: { action: 'read', resource: resource, payload: {} } }, res2);
        }
      } finally {
        global.fetch = realFetch;
        if (envURL === undefined) delete process.env[names.url]; else process.env[names.url] = envURL;
        if (envKey === undefined) delete process.env[names.key]; else process.env[names.key] = envKey;
      }
      const filtered = urls.filter((u) => u.indexOf('_deleted_at=is.null') !== -1);
      ok(filtered.length === SOFT_ONLY.length,
         'every read of the ' + SOFT_ONLY.length + ' Tier A resources filters '
         + 'out soft-deleted rows -- ' + filtered.length + '/' + SOFT_ONLY.length);
      // WITHOUT THIS THE ARM ABOVE WOULD PASS ON A HANDLER THAT ADDED THE
      // FILTER TO EVERY RESOURCE, which would be a predicate that can only
      // ever be true on the 21 and reads to a later maintainer as meaning
      // something.
      ok(urls.length === SOFT_ONLY.length + 3 && filtered.length === SOFT_ONLY.length,
         'CONTROL: three hard-deletable resources were read too and NONE of '
         + 'them carries the filter');
    }
    ok(leaks.length === 0, 'no resource behaved differently: '
       + (leaks.slice(0, 6).join('; ') || 'none'));

    // Cross-app and cross-licence, on the gate that matters most. An admin
    // token for a DIFFERENT app, and a real sairncode admin token bound to a
    // DIFFERENT licence, must both be refused -- the licence row here is
    // unattributable, so this branch's own check is the only thing left.
    //
    // THE CROSS-APP TOKEN MUST CARRY THE ROLE THE GATE ASKS FOR, or the arm
    // passes for the wrong reason. The first version of this used a SAIRNbiz
    // OWNER token -- and `owner` is not `admin`, so the ROLE check refuses it
    // whether or not the app check exists. The mutation control caught that
    // immediately: dropping `expectedApp` from verifySessionToken left this
    // suite green. StoneDesk's vocabulary contains a real `admin`
    // (ROLES_BY_APP.stonedesk), so a StoneDesk admin token satisfies the role
    // half and the APP CLAIM is then the only thing left standing -- which is
    // the property Check 28 and the 2026-08-03 cross-app collision are about.
    ok(auth.ROLES_BY_APP.stonedesk.indexOf('admin') !== -1,
       'CONTROL: StoneDesk really does have an `admin` role, so the next arm '
       + 'tests the APP claim and not the role check');
    // THE VERB MOVED WITH THE SUBJECT (2026-09-15, item 97). sc_claims is Tier
    // A and no longer grants a destroying `delete`, so these three arms send
    // `soft_delete` -- the verb that now reaches the session check on this
    // resource. Keeping `delete` here would have passed for the WRONG REASON:
    // checkEnvelope rejects the ungranted verb with a 400 before the app claim
    // is ever examined, so the arm would have stopped testing the thing it is
    // named for while still going green on a handler with no app check at all.
    // That is exactly the stale-anchor shape PR 1.3 is about, and it appeared
    // the moment the verb changed.
    const crossAdmin = await call(h, { resource: 'sc_claims', action: 'soft_delete',
                                       payload: { id: 'X1' },
                                       token: token('admin', 'stonedesk') });
    ok(crossAdmin.code === 403 && !crossAdmin.sawUpstream,
       'a StoneDesk ADMIN session cannot remove sc_claims -- the token carries '
       + 'the right role and the wrong app: ' + crossAdmin.code);
    const other = await call(h, { resource: 'sc_claims', action: 'soft_delete',
                                  payload: { id: 'X1' },
                                  token: token(auth.ROLES_BY_APP.sairnbiz[0], 'sairnbiz') });
    ok(other.code === 403 && !other.sawUpstream,
       'and neither can a SAIRNbiz owner session -- wrong app AND wrong role: '
       + other.code);
    const wrongLic = await call(h, { resource: 'sc_claims', action: 'soft_delete',
                                     payload: { id: 'X1' },
                                     token: token('admin', 'sairncode', 'OTHER-HASH') });
    ok(wrongLic.code === 403 && !wrongLic.sawUpstream,
       'nor can a sairncode admin session bound to a different licence -- '
       + wrongLic.code);
    // AND THE SAME THREE ON A RESOURCE THAT STILL HARD-DELETES, so the cross-app
    // property is proved on BOTH verbs rather than only on the one that changed.
    //
    // ── THE FIXTURE IS DERIVED NOW, AND IT WAS PINNED (2026-09-23) ──────────
    // This read `resource: 'sc_dme'`, hardcoded, in a file whose whole job is
    // that the soft-delete list is DERIVED rather than typed. sc_dme was
    // re-tiered A, moved into SOFT_ONLY, and this arm started failing with 400
    // -- the envelope gate correctly refusing a verb the registry no longer
    // grants -- under a message claiming the app check had let a StoneDesk
    // admin through. A pinned fixture inside a derived suite is the same drift
    // one layer down, and it reported the right behaviour as a wrong one.
    const stillHard = SC.resources.filter((r) => SOFT_ONLY.indexOf(r) === -1);
    if (!stillHard.length) {
      ok(false, 'COULD NOT DRIVE the hard-delete cross-app arm: every SAIRNcode '
         + 'resource is now soft-delete-only, so there is nothing left that '
         + 'hard-deletes. That is a real state and this arm must be RETIRED '
         + 'deliberately rather than left passing vacuously.');
    } else {
      const hardFixture = stillHard[0];
      const crossHard = await call(h, { resource: hardFixture, action: 'delete',
                                        payload: { id: 'X1' },
                                        token: token('admin', 'stonedesk') });
      ok(crossHard.code === 403 && !crossHard.sawUpstream,
         'a StoneDesk ADMIN session cannot delete ' + hardFixture + ' either -- '
         + 'the hard-delete branch checks the app claim the same way: '
         + crossHard.code);
    }
  }

  // ── 2. sc_settings WRITE ──────────────────────────────────────────────────
  section('2. sc_settings write requires an ADMIN session');
  {
    const anon = await call(h, { resource: 'sc_settings', action: 'write',
                                 payload: { id: 'S1', practiceName: 'X' } });
    ok(anon.code === 401 && !anon.sawUpstream,
       'no session is 401 NO_SESSION, not 403 -- the two mean different things '
       + 'and the message says which: ' + (anon.body && anon.body.error
       && anon.body.error.code));
    for (const role of ROLES.filter((r) => r !== 'admin')) {
      const r = await call(h, { resource: 'sc_settings', action: 'write',
                                payload: { id: 'S1', practiceName: 'X' },
                                token: token(role) });
      ok(r.code === 403 && !r.sawUpstream,
         'a signed-in ' + role + ' is refused 403 and never reaches storage');
    }
    const admin = await call(h, { resource: 'sc_settings', action: 'write',
                                  payload: { id: 'S1', practiceName: 'X' },
                                  token: token('admin') });
    ok(admin.code === 200 && admin.sawUpstream,
       'CONTROL: an admin DOES write -- otherwise every arm above would pass on '
       + 'a branch that refused everyone');
  }

  // ── 3. THE RETENTION FLOOR -- A VALUE CONTROL, NOT A ROLE CONTROL ─────────
  // "a role check and a value check are different controls and neither replaces
  // the other" (api/sd-data.js). This value is meant to drive a purge that does
  // not exist yet, so by the time anything acts on it nobody will remember who
  // typed it -- which is why a below-floor value must never reach storage at
  // all, admin or not.
  section('3. the retention floor applies to an ADMIN too');
  {
    const FLOOR = 10;
    for (const bad of [1, 9, 9.99, 0, -5, 'forever', '', null]) {
      const r = await call(h, { resource: 'sc_settings', action: 'write',
                                payload: { id: 'S1', retention_years: bad },
                                token: token('admin') });
      ok(r.code === 400 && r.body && r.body.error
         && r.body.error.code === 'RETENTION_BELOW_FLOOR' && !r.sawUpstream,
         'retention_years=' + JSON.stringify(bad)
         + ' is refused RETENTION_BELOW_FLOOR and never reaches storage');
    }
    for (const good of [FLOOR, FLOOR + 1, 99, 'indefinite', String(FLOOR)]) {
      const r = await call(h, { resource: 'sc_settings', action: 'write',
                                payload: { id: 'S1', retention_years: good },
                                token: token('admin') });
      ok(r.code === 200 && r.sawUpstream,
         'CONTROL: retention_years=' + JSON.stringify(good) + ' is accepted');
    }
    // The floor is a FLOOR, not an equality check, and the boundary is the
    // half that silently inverts. 10 passes, 9.99 does not -- both asserted
    // above; this names why the pair is there.
    const at = await call(h, { resource: 'sc_settings', action: 'write',
                               payload: { id: 'S1', retention_years: FLOOR },
                               token: token('admin') });
    const under = await call(h, { resource: 'sc_settings', action: 'write',
                                  payload: { id: 'S1', retention_years: FLOOR - 0.01 },
                                  token: token('admin') });
    ok(at.code === 200 && under.code === 400,
       'the boundary is inclusive at exactly ' + FLOOR + ' and exclusive just '
       + 'below it');
  }

  // ── 4. THE SIGN-OFF GATE, AND THE FORGED NAME ────────────────────────────
  // The role half is one control; "the server sets signedOffBy from the
  // verified session, not from whatever the client sent" is a SECOND one, and
  // it is the one that decides whose name ends up on a submitted prior-auth
  // request. Nothing tested either.
  section('4. sc_auth_requests sign-off: the role, and whose name is recorded');
  {
    // ── THIS CONTROL ASSERTED THE OPPOSITE UNTIL 2026-09-23, AND IT WAS RIGHT
    // ── TO. It read "an ORDINARY sc_auth_requests write needs no session at
    // all", expecting 200 from an unauthenticated caller, and its job was to
    // prove the sign-off gate below is SCOPED rather than gating the whole
    // resource. sc_auth_requests was re-tiered A on 2026-09-22 and the Tier A
    // write gate now covers it, so an unsigned write is refused 401 -- the old
    // expectation is now a statement that the security fix did not happen.
    //
    // THE CONTROL'S REAL PURPOSE SURVIVES AND IS RESTATED RATHER THAN DELETED:
    // the sign-off gate must still be NARROWER than the resource gate. So the
    // pair below is (a) no session at all is refused 401 by the Tier A gate,
    // and (b) a signed-in BILLER -- a role the Tier A gate allows and the
    // sign-off gate does not -- can still do an ordinary write. If (b) ever
    // fails, the sign-off gate has swallowed the whole resource, which is the
    // thing this arm has always existed to catch.
    const unsigned = await call(h, { resource: 'sc_auth_requests', action: 'write',
                                     payload: { id: 'A1', status: 'draft', note: 'x' } });
    ok(unsigned.code === 401 && !unsigned.sawUpstream,
       'an ORDINARY sc_auth_requests write with NO session is refused 401 by the '
       + 'Tier A write gate -- it was 200 until 2026-09-23, on a resource holding '
       + "a named beneficiary's authorisation request: " + unsigned.code);
    const ordinary = await call(h, { resource: 'sc_auth_requests', action: 'write',
                                     payload: { id: 'A1', status: 'draft', note: 'x' },
                                     token: token('biller') });
    ok(ordinary.code === 200 && ordinary.sawUpstream,
       'CONTROL: a signed-in biller CAN still do an ordinary write -- the sign-off '
       + 'gate below is scoped to sign-off and has not swallowed the resource: '
       + ordinary.code);

    for (const role of ROLES.filter((r) => r !== 'admin')) {
      const byName = await call(h, { resource: 'sc_auth_requests', action: 'write',
                                     payload: { id: 'A1', signedOffBy: 'Dr Someone' },
                                     token: token(role) });
      ok(byName.code === 403 && !byName.sawUpstream,
         'a ' + role + ' setting signedOffBy at all is refused 403');
      const byStatus = await call(h, { resource: 'sc_auth_requests', action: 'write',
                                       payload: { id: 'A1', status: 'submitted' },
                                       token: token(role) });
      ok(byStatus.code === 403 && !byStatus.sawUpstream,
         '...and so is a ' + role + ' moving status to submitted');
    }
    // AND A CALLER WITH NO SESSION -- REFUSED 401 NOW, NOT 403, AND THE CHANGE
    // IS THE RIGHT DIRECTION. Until 2026-09-23 the sign-off gate was the only
    // thing refusing this, so an unauthenticated caller got FORBIDDEN. The Tier
    // A write gate now fires first and answers NO_SESSION, which is the more
    // accurate of the two: "you are not signed in" and "your role may not do
    // this" are different problems, and api/sd-data.js keeps them distinct on
    // purpose. Asserted as "refused, and by the resource gate" rather than
    // loosened to "refused somehow" -- which gate answered is the fact that
    // would change if either were removed.
    const anon = await call(h, { resource: 'sc_auth_requests', action: 'write',
                                 payload: { id: 'A1', status: 'submitted' } });
    ok(anon.code === 401 && !anon.sawUpstream,
       'and so is a caller with no session at all -- 401 from the Tier A write '
       + 'gate, which now fires before the sign-off gate: ' + anon.code);

    // THE FORGED NAME. An admin may sign off -- and the name recorded must be
    // the SESSION's employee_id, never the string the client sent.
    const forged = await call(h, { resource: 'sc_auth_requests', action: 'write',
                                   payload: { id: 'A1', status: 'submitted',
                                              signedOffBy: 'Somebody Else Entirely' },
                                   token: token('admin') });
    ok(forged.code === 200 && forged.sawUpstream,
       'an admin CAN sign off');
    ok(forged.body && forged.body.data
       && forged.body.data.signedOffBy === 'E-ADMIN',
       '...and signedOffBy is taken from the VERIFIED SESSION, overwriting the '
       + 'name the client sent -- got '
       + JSON.stringify(forged.body && forged.body.data && forged.body.data.signedOffBy));
    ok(forged.body && forged.body.data && forged.body.data.signedOffAt,
       '...and signedOffAt is stamped by the server, not supplied');
  }

  // ── 5. THE POSTURE OF THE OTHER 27 -- MEASURED, NOT CHANGED ──────────────
  // This is the arm that makes the open finding visible instead of merely
  // written down. Every read and every non-gated write on this app is
  // LICENCE-ONLY: no employee session required, on an app whose Tier A list is
  // sc_ar, sc_claims, sc_revenue, sc_denial, sc_compliance and
  // sc_credential_scope. api/sc-auth.js EXISTS, so a session is available to
  // bind to; nothing records why it is not bound.
  //
  // NOT FIXED HERE, DELIBERATELY. Which resources should gate is a product
  // decision with a real cost -- SAIRNlaw's own phase 1 comment records why
  // flipping several at once would break a staff member mid-session -- and it
  // is Michael's call. What a test CAN do is make a silent change in either
  // direction fail, which is what the hand-written table below buys.
  section('5. the posture of every resource, measured against a written table');
  {
    const readOpen = [], readGated = [], writeOpen = [], writeGated = [];
    for (const resource of SC.resources) {
      const r = await call(h, { resource, action: 'read' });
      (r.code === 200 ? readOpen : readGated).push(resource);
      const w = await call(h, { resource, action: 'write', payload: { id: 'W1' } });
      (w.code === 200 ? writeOpen : writeGated).push(resource);
    }
    ok(readOpen.length === 28,
       'READ is licence-only on all 28 -- no employee session is required '
       + 'anywhere on this app. ' + readOpen.length + '/28 open'
       + (readGated.length ? '; GATED: ' + readGated.join(', ') : ''));
    const expectGated = Object.keys(WRITE_GATED).sort();
    ok(JSON.stringify(writeGated.sort()) === JSON.stringify(expectGated),
       'an ORDINARY write is gated on exactly the one the handler argues for ('
       + expectGated.join(', ') + ') -- measured: [' + writeGated.join(', ') + ']');
    // ── THE ROLE HALF OF THE TABLE WAS DECORATION (2026-09-25) ──────────────
    // The arm above compares Object.keys(WRITE_GATED) against the handler, and
    // that was the ONLY read of this table anywhere in the suite. So half of it
    // -- the 'admin|biller' strings -- was never checked against anything, in a
    // table whose own header says in capitals that it is THE CLAIM, the handler
    // is THE FACT, and "a disagreement is a finding". It had already drifted:
    // sc_coded_items read 'admin|biller' while the handler granted
    // ['admin','biller','coder'], from 2026-09-23 until this arm was written.
    //
    // WHY THIS IS NOT SELF-AGREEING. rolesFor() parses SC_TIER_A_WRITE_ROLES,
    // SC_TIER_A_WRITE_ROLES_BY_RESOURCE and sc_settings' own narrowing out of
    // api/sd-data.js -- the FACT -- and the table above is hand-written from a
    // reading of the posture. A widened constant, a new override, or a deleted
    // one now fails here instead of being ratified silently.
    const roleClaims = Object.keys(WRITE_GATED).sort()
      .map((r) => r + '=' + WRITE_GATED[r]).join('  ');
    const roleFacts = Object.keys(WRITE_GATED).sort()
      .map((r) => r + '=' + rolesFor(r).join('|')).join('  ');
    ok(roleClaims === roleFacts,
       'and the WRITE_GATED table\'s ROLE half agrees with the handler on every '
       + 'one of the ' + Object.keys(WRITE_GATED).length + ' rows -- claim: ['
       + roleClaims + '] fact: [' + roleFacts + ']');
    // THE CONDITIONAL GATE IS NOT COUNTED HERE, and that is the honest figure.
    // sc_auth_requests gates only the sign-off write, so a plain write to it is
    // open like the other 26 ordinary writes. Counting it as gated would report 2 of 28 when
    // the true unconditional figure is 1.
    // Vacuously true while CONDITIONALLY_WRITE_GATED is empty, and that is the
    // correct reading rather than a hole: sc_auth_requests left this table on
    // 2026-09-23 because its ordinary write is now gated too. The arm stays so
    // the next payload-conditional gate is measured the same way, and the table
    // above says why it is empty.
    ok(Object.keys(CONDITIONALLY_WRITE_GATED).every((r) => writeOpen.indexOf(r) !== -1),
       'every CONDITIONALLY write-gated resource reads as OPEN to a plain write -- '
       + Object.keys(CONDITIONALLY_WRITE_GATED).length + ' such resource(s) today');
    // A gate that APPEARS must fail this as loudly as one that disappears. The
    // table is the claim; the handler is the fact; disagreement is a finding
    // either way, and reporting only one direction is how a posture drifts
    // without anybody being told.
    // 21 -> 20 on 2026-09-15. sc_denial_events moved out of this population
    // into the gated one, after a live probe found it accepting a write with
    // the LICENCE KEY ALONE while the other six Tier A resources answered 401
    // NO_SESSION. The number is moved by hand deliberately rather than made
    // self-adjusting: a count derived from the handler agrees with the handler
    // by construction and could never report a gate appearing or disappearing,
    // which is the only thing this arm is for.
    //
    // 20 -> 5 on 2026-09-23, AND THIS IS THE BIGGEST MOVE THIS NUMBER WILL EVER
    // MAKE. Sixteen resources were re-tiered A over the preceding eight days and
    // the pinned list had not followed, so all sixteen sat in THIS population --
    // accepting a write on the licence key alone -- including a named patient
    // joined to a diagnosis and its dollar value (sc_hcc), a named patient
    // joined to payer and plan (sc_eligibility), and the QP status that picks
    // between two CMS conversion factors (sc_providers).
    //
    // THE FOUR THAT REMAIN ARE THE FOUR THAT ARE NOT TIER A, and they are the
    // same four that still hard-delete: sc_scrubrules, sc_encoder,
    // sc_specialty_checks, sc_specialty_checklists. FIVE became FOUR on
    // 2026-09-25 when sc_pctc was promoted Tier A on integrity (a wrong PC/TC
    // indicator is a wrong billing instruction on every future check) and its
    // gate, soft-delete conversion and client call site all moved together --
    // the seam test above is what refused the register moving alone. So this
    // number and the partition in arm 1 have to agree, which is a second way
    // to notice a drift in either.
    ok(writeOpen.length === 4,
       '4 resources still accept an ordinary write with the licence key alone -- '
       + 'the 28 minus the 24 Tier A ones. They are the same four that still '
       + 'hard-delete, so this figure and the partition in arm 1 must agree '
       + '(got ' + writeOpen.length + ': ' + writeOpen.join(', ') + ')');
    // THE ARM THAT WAS INVERTED BY THE DECISION, and it is left visibly
    // inverted rather than deleted. It used to read "the six named Tier A
    // resources are ALL among the open ones, which is why the row is open".
    // They are now all gated. Deleting it would lose the record that this is
    // the same six, measured the same way, with the answer changed on purpose.
    const openTierA = TIER_A_GATED.filter((t) => writeOpen.indexOf(t) !== -1);
    ok(openTierA.length === 0,
       'and NONE of the six Tier A billing resources is open to an ordinary '
       + 'write any more -- this arm was inverted on 2026-09-14 when the '
       + 'decision landed, not deleted'
       + (openTierA.length ? ' -- STILL OPEN: ' + openTierA.join(', ') : ''));
    // ...and the reads are untouched, which is the other half of the decision
    // and the half a role gate most easily breaks by accident.
    let readsOpen = 0;
    for (const resource of TIER_A_GATED) {
      const r = await call(h, { resource, action: 'read' });
      if (r.code === 200) readsOpen += 1;
    }
    ok(readsOpen === TIER_A_GATED.length,
       'CONTROL: all six are still READABLE with the licence key alone -- reads '
       + 'were deliberately not narrowed, and a gate applied to the wrong branch '
       + 'is the obvious way that goes wrong. ' + readsOpen + '/'
       + TIER_A_GATED.length);
  }

  // ── 6. THE TIER A BILLING WRITE GATE ─────────────────────────────────────
  // Michael's decision of 2026-09-14, after section 5 measured the posture.
  // Written as its own section because it is a BEHAVIOUR CHANGE ON LIVE DATA,
  // not a discovery: these accepted a write from the licence key alone until
  // the gate landed -- six of them on 2026-09-14 and the seventh, which the
  // hand-written list had missed, on 2026-09-15.
  section('6. the Tier A billing resources require a role to WRITE');
  {
    // SIX -> SEVEN on 2026-09-15. The gate was a hand-written list of six and
    // the register says seven; sc_denial_events was the one missing, and a live
    // probe found it answering 200 to a write with the licence key alone while
    // the other six answered 401 NO_SESSION. The handler derives the list from
    // the pinned Tier A set now, so this arm is checking the DERIVATION rather
    // than a copy -- and section 1 is what pins that set to the register.
    //
    // SEVEN -> TWENTY-THREE on 2026-09-23, and the COUNT IS NOT WRITTEN HERE
    // ANY MORE. A literal number in this arm is the fourth copy of a list that
    // already exists in three places, and it is the copy that would go stale
    // silently -- which is exactly what happened: sixteen resources were
    // re-tiered A over eight days, the pinned list did not follow, and section
    // 1 went red while this arm kept agreeing with a seven that was no longer
    // anybody's claim. The count is derived from the pin; section 1 is what
    // makes the pin equal the register, in both directions.
    ok(TIER_A_GATED.length === SC.tierASoftDeleteOnly.length
       && TIER_A_GATED.length > 0,
       'the handler gates exactly the pinned Tier A set -- '
       + TIER_A_GATED.length + ': ' + TIER_A_GATED.join(', '));
    ok(TIER_A_GATED.indexOf('sc_denial_events') !== -1,
       'sc_denial_events is gated -- it was the seventh Tier A resource and the '
       + 'hand-written list of six left it open to the licence key alone');
    ok(TIER_A_GATED.every((r) => SC.resources.indexOf(r) !== -1),
       'and every one is a real registered SAIRNcode resource');
    // THE ROLE LIST NAMES ROLES THIS APP ACTUALLY HAS. The same PR 3.4 trap as
    // SAIRNbiz's void gate: the decision said "Admin/Manager" and SAIRNcode has
    // no `manager`, so a literal implementation would have shipped a gate no
    // account could pass. `biller` is the translation and it is asserted, not
    // assumed.
    const unknown = TIER_A_ROLES.filter((r) => ROLES.indexOf(r) === -1);
    ok(unknown.length === 0,
       'every role in SC_TIER_A_WRITE_ROLES exists in ROLES_BY_APP.sairncode ('
       + ROLES.join('|') + ')' + (unknown.length ? ' -- UNKNOWN: ' + unknown.join(', ') : ''));
    ok(ROLES.indexOf('manager') === -1,
       'CONTROL: SAIRNcode genuinely has no `manager` role, so mapping the '
       + 'decision\'s "Manager" onto `biller` was a translation and not a rename');

    // ── ALLOWED AND DENIED ARE MEASURED PER RESOURCE ──────────────────────
    // Not as one blanket claim over all six. The first version of this section
    // asserted "every disallowed role on every one of the six" and went red the
    // moment Michael added `auditor` to sc_compliance -- the arm doing its job,
    // and the wrong shape once an exception exists. Every expectation below
    // comes from the handler's own per-resource list.
    let anon401 = 0, deniedCount = 0, allowedCount = 0, deniedExpected = 0;
    const leaks = [];
    for (const resource of TIER_A_GATED) {
      const allowed = rolesFor(resource);
      const denied = ROLES.filter((r) => allowed.indexOf(r) === -1);
      ok(denied.length > 0,
         'CONTROL: ' + resource + ' still has roles to deny -- ' + denied.join(', ')
         + ' (allowed: ' + allowed.join(', ') + ')');
      deniedExpected += denied.length;

      const anon = await call(h, { resource, action: 'write', payload: { id: 'W1', amt: 1 } });
      if (anon.code === 401 && anon.body && anon.body.error
          && anon.body.error.code === 'NO_SESSION' && !anon.sawUpstream) anon401 += 1;
      else leaks.push(resource + ' (no session -> ' + anon.code + ')');

      for (const role of denied) {
        const r = await call(h, { resource, action: 'write', payload: { id: 'W1' },
                                  token: token(role) });
        if (r.code === 403 && r.body && r.body.error
            && r.body.error.code === 'FORBIDDEN' && !r.sawUpstream) deniedCount += 1;
        else leaks.push(resource + '/' + role + ' -> ' + r.code
                        + (r.sawUpstream ? ' REACHED STORAGE' : ''));
      }
      for (const role of allowed) {
        const r = await call(h, { resource, action: 'write', payload: { id: 'W1' },
                                  token: token(role) });
        if (r.code === 200 && r.sawUpstream) allowedCount += 1;
        else leaks.push(resource + '/' + role + ' -> ' + r.code + ' (expected 200)');
      }
    }
    ok(anon401 === TIER_A_GATED.length,
       'all ' + TIER_A_GATED.length + ' answer 401 NO_SESSION to an unsigned '
       + 'write, without touching storage -- ' + anon401 + '/' + TIER_A_GATED.length);
    ok(deniedCount === deniedExpected,
       'every role NOT on a resource\'s own list is refused 403 FORBIDDEN, '
       + 'resource by resource -- ' + deniedCount + '/' + deniedExpected);
    // WITHOUT THIS THE TWO ARMS ABOVE WOULD PASS ON A BRANCH THAT REFUSED
    // EVERYONE, which would be a worse outage than the gap it closed.
    const allowedExpected = TIER_A_GATED.reduce((a, r) => a + rolesFor(r).length, 0);
    ok(allowedCount === allowedExpected,
       'CONTROL: every ALLOWED role does reach storage on its own resources -- '
       + allowedCount + '/' + allowedExpected);
    ok(leaks.length === 0, 'nothing behaved differently: '
       + (leaks.slice(0, 6).join('; ') || 'none'));

    // ── THE TWO DECISIONS, NAMED SO THEY CANNOT DRIFT BACK SILENTLY ───────
    // Both were open questions when the gate shipped and both were answered on
    // 2026-09-14. Asserting them by name means a later widening or narrowing is
    // a test failure with a reason attached, not a quiet change to a constant.
    ok(rolesFor('sc_compliance').indexOf('auditor') !== -1,
       'DECIDED: an `auditor` CAN write sc_compliance -- recording a compliance '
       + 'finding is that role\'s stated job, and excluding it from the resource '
       + 'named for that job was the wrong-shaped gate');
    const auditorCompliance = await call(h, { resource: 'sc_compliance', action: 'write',
                                              payload: { id: 'W1' },
                                              token: token('auditor') });
    ok(auditorCompliance.code === 200 && auditorCompliance.sawUpstream,
       '...driven, not just declared -- an auditor session reaches storage on '
       + 'sc_compliance');
    // AND THE OVERRIDE IS AN OVERRIDE. Widening the shared constant instead
    // would have granted an auditor five more resources nobody decided about.
    let auditorElsewhere = 0;
    for (const resource of TIER_A_GATED.filter((r) => r !== 'sc_compliance')) {
      const r = await call(h, { resource, action: 'write', payload: { id: 'W1' },
                                token: token('auditor') });
      if (r.code === 403 && !r.sawUpstream) auditorElsewhere += 1;
      else leaks.push('auditor reached ' + resource + ' -> ' + r.code);
    }
    // Derived from the gated set rather than written as 5, because the set grew
    // on 2026-09-15 and a literal here would have made a CORRECT widening of
    // the population look like a broken exception. The exception itself is
    // still pinned by name above; this arm is about everything that is not it.
    ok(auditorElsewhere === TIER_A_GATED.length - 1,
       'CONTROL: and an auditor is still refused on the other '
       + (TIER_A_GATED.length - 1) + ' -- the exception is an EXCEPTION, not a '
       + 'widened shared list. ' + auditorElsewhere + '/' + (TIER_A_GATED.length - 1));
    ok(rolesFor('sc_claims').indexOf('coder') === -1,
       'DECIDED: a `coder` CANNOT write sc_claims. Coherent with the split this '
       + 'app already has -- sc_coded_items is the coder\'s own resource and is '
       + 'ungated -- and claims submission is billing-side by design');
    const coderClaims = await call(h, { resource: 'sc_claims', action: 'write',
                                        payload: { id: 'W1' }, token: token('coder') });
    ok(coderClaims.code === 403 && !coderClaims.sawUpstream,
       '...driven: a coder session is refused 403 on sc_claims');
    // ── THE SPLIT SURVIVED THE TIER CHANGE, AND IT NEARLY DID NOT ──────────
    // This read "sc_coded_items is still UNGATED" and drove a write with no
    // token at all. sc_coded_items was re-tiered A -- the row carries a
    // verbatim quote from a clinical note -- so on 2026-09-23 it joined the
    // Tier A write gate and that write became a 401. Left alone, the tier
    // change would have locked a coder out of the resource named for their own
    // job, which is the wrong-shaped gate the sc_compliance/auditor exception
    // already exists to avoid, and it would have pulled the floor out from
    // under the sc_claims decision asserted immediately above.
    //
    // SO THE CONTROL IS RESTATED, NOT RELAXED: a session is now required (the
    // security half of the tier change), and a CODER is still one of the roles
    // that may write it (the split the sc_claims exclusion is argued on). Both
    // halves are driven, because asserting only the second would pass on a
    // branch that had stopped gating at all.
    const coderCodedAnon = await call(h, { resource: 'sc_coded_items', action: 'write',
                                           payload: { id: 'W1' } });
    ok(coderCodedAnon.code === 401 && !coderCodedAnon.sawUpstream,
       'sc_coded_items needs a session now -- it holds a verbatim quote from a '
       + 'clinical note and took a write on the licence key alone until '
       + '2026-09-23: ' + coderCodedAnon.code);
    const coderCoded = await call(h, { resource: 'sc_coded_items', action: 'write',
                                       payload: { id: 'W1' }, token: token('coder') });
    ok(coderCoded.code === 200 && coderCoded.sawUpstream,
       'CONTROL: and a signed-in CODER still reaches storage on sc_coded_items -- '
       + 'their own resource. That is what makes the sc_claims exclusion above a '
       + 'split rather than a lockout, and it is why the tier change carries a '
       + 'per-resource role override rather than the shared admin|biller list');

    // 401 AND 403 ARE DIFFERENT PROBLEMS WITH DIFFERENT FIXES and collapsing
    // them sends a support call to the wrong place. Asserted rather than assumed
    // because the shortest way to write this gate collapses them.
    const anon = await call(h, { resource: 'sc_claims', action: 'write',
                                 payload: { id: 'W1' } });
    const wrongRole = await call(h, { resource: 'sc_claims', action: 'write',
                                      payload: { id: 'W1' }, token: token('coder') });
    ok(anon.code === 401 && wrongRole.code === 403,
       'not signed in is 401 and wrong role is 403 -- ' + anon.code + ' vs '
       + wrongRole.code);
    ok(/requires a signed-in employee session/.test(
         (anon.body && anon.body.error && anon.body.error.message) || ''),
       '...and the 401 says what to do');
    // THE MESSAGE MUST NAME THE LIST THE CHECK ACTUALLY USED. With a
    // per-resource override those can diverge, and a refusal that tells somebody
    // the wrong set of roles sends them to the wrong colleague.
    const wrMsg = (wrongRole.body && wrongRole.body.error
                   && wrongRole.body.error.message) || '';
    ok(rolesFor('sc_claims').every((r) => wrMsg.indexOf(r) !== -1),
       '...and the 403 names every role that CAN, rather than only the one that '
       + 'cannot: ' + wrMsg.slice(0, 90));
    const compDenied = await call(h, { resource: 'sc_compliance', action: 'write',
                                       payload: { id: 'W1' }, token: token('coder') });
    const compMsg = (compDenied.body && compDenied.body.error
                     && compDenied.body.error.message) || '';
    ok(compMsg.indexOf('auditor') !== -1,
       'CONTROL: and on sc_compliance it names `auditor` too, so the message '
       + 'tracks the OVERRIDE and not the shared constant: ' + compMsg.slice(0, 90));

    // CROSS-APP: a StoneDesk ADMIN token carries the right role string and the
    // wrong app. The app claim must be the thing that refuses it -- the same
    // property the delete gate's arm in section 1 exists for, and the 2026-08-03
    // collision this whole convention comes from.
    const crossAdmin = await call(h, { resource: 'sc_claims', action: 'write',
                                       payload: { id: 'W1' },
                                       token: token('admin', 'stonedesk') });
    ok(crossAdmin.code === 401 && !crossAdmin.sawUpstream,
       'a StoneDesk admin session cannot write sc_claims -- the token does not '
       + 'verify for this app at all, so it is 401 rather than 403: '
       + crossAdmin.code);
    const wrongLic = await call(h, { resource: 'sc_claims', action: 'write',
                                     payload: { id: 'W1' },
                                     token: token('biller', 'sairncode', 'OTHER-HASH') });
    ok(wrongLic.code === 401 && !wrongLic.sawUpstream,
       'nor can a real sairncode biller session bound to a different licence -- '
       + wrongLic.code);

    // AND THE 22 THAT WERE DELIBERATELY LEFT ALONE. "The other 22 stay as-is"
    // is a decision, and a gate that crept onto one of them would be a silent
    // outage for every role that writes it.
    const untouched = SC.resources.filter((r) => TIER_A_GATED.indexOf(r) === -1
                                           && r !== 'sc_settings'
                                           && r !== 'sc_auth_requests');
    let stillOpen = 0;
    for (const resource of untouched) {
      const r = await call(h, { resource, action: 'write', payload: { id: 'W1' } });
      if (r.code === 200 && r.sawUpstream) stillOpen += 1;
      else leaks.push(resource + ' (should still be open -> ' + r.code + ')');
    }
    ok(stillOpen === untouched.length,
       'all ' + untouched.length + ' non-billing resources still accept a write '
       + 'with the licence key alone -- the gate did not creep');
  }

  // ── 7. THE CLIENT HALF: A REFUSAL MUST NOT READ AS A SYNC FAILURE ────────
  // Every add-function on this page already tested its scData() result and said
  // "added on this device only -- server sync failed, will not appear on other
  // devices until resolved". That was TRUE of every failure this client could
  // previously get on these six: a network drop, a 503, an unprovisioned table.
  // IT IS NOT TRUE OF A 403. "Until resolved" tells a coder to wait for
  // something that will never happen, and the row sits on that one device for
  // ever -- so shipping the gate without this half would have reintroduced the
  // silent-failure class on purpose.
  section('7. the client tells a refusal apart from a transient failure');
  {
    const html = require('fs').readFileSync(path.join(ROOT, 'sairncode.html'), 'utf8')
      .replace(/\r\n/g, '\n');
    function grab(sig) {
      const start = html.indexOf(sig);
      assert.ok(start > 0, 'not found in sairncode.html: ' + sig);
      let i = html.indexOf('{', start + sig.length - 1), depth = 0, q = null;
      for (; i < html.length; i++) {
        const c = html[i], p = html[i - 1];
        if (q) { if (c === q && p !== '\\') q = null; continue; }
        if (c === '"' || c === "'" || c === '`') { q = c; continue; }
        if (c === '/' && html[i + 1] === '/') { i = html.indexOf('\n', i); continue; }
        if (c === '/' && html[i + 1] === '*') { i = html.indexOf('*/', i) + 1; continue; }
        if (c === '{') depth++;
        else if (c === '}') { depth--; if (!depth) return html.slice(start, i + 1); }
      }
      throw new Error('unterminated: ' + sig);
    }
    const ctx = { err: null, scLastDataError: () => ctx.err };
    require('vm').createContext(ctx);
    require('vm').runInContext(grab('function scWriteRefusalText(fallback) {'), ctx);
    const FALLBACK = 'added on this device only -- server sync failed, will not '
      + 'appear on other devices until resolved';

    for (const code of ['FORBIDDEN', 'NO_SESSION']) {
      ctx.err = { code: code, message: 'Only admin or biller can change sc_claims.' };
      const t = ctx.scWriteRefusalText(FALLBACK);
      ok(/NOT SAVED TO THE SERVER/.test(t) && !/until resolved/.test(t),
         code + ' does NOT get the "until resolved" sentence -- ' + t.slice(0, 70));
      ok(/re-trying will not change that/.test(t),
         '...and says re-trying will not help, which is the part that stops '
         + 'somebody waiting');
      ok(t.indexOf('Only admin or biller can change sc_claims.') !== -1,
         '...and carries the SERVER\'s own words, not a local paraphrase');
    }
    // CONTROL: every OTHER failure keeps the original sentence. Without this the
    // arms above would pass on a helper that had simply replaced the message for
    // everybody, which would make a real transient failure look permanent.
    for (const code of ['NETWORK', 'NOT_PROVISIONED', 'HTTP_500', '']) {
      ctx.err = { code: code, message: 'x' };
      ok(ctx.scWriteRefusalText(FALLBACK) === FALLBACK,
         'CONTROL: ' + (code || '(empty)') + ' keeps the original transient '
         + 'sentence unchanged');
    }
    ctx.err = null;
    ok(ctx.scWriteRefusalText(FALLBACK) === FALLBACK,
       'CONTROL: and so does no recorded error at all');

    // THE PAIRING ASSERTION. A helper nothing calls is worse than no helper:
    // it reads as covered. Every write-gated resource must route its failure
    // branch through a refusal-aware path, and no OTHER resource may -- on
    // those, the original "until resolved" sentence is still accurate.
    //
    // ── TWO HELPERS, NOT ONE, AND THE SECOND IS THE STRONGER (2026-09-23) ───
    // sc_settings does not call scWriteRefusalText and must not be made to.
    // scSaveSettings() checks FORBIDDEN/NO_SESSION itself, ROLLS BACK the local
    // write it had already made, and answers through scSettingsSaveMessage(),
    // which separates saved / refused / stored-but-unsynced into three
    // outcomes. That is strictly more than the helper does, and demanding one
    // spelling would have meant replacing a better mechanism with a worse one
    // to satisfy a test. Enumerated rather than matched loosely, so a resource
    // still cannot opt out silently: a new helper has to be named here.
    // The third spelling is an INLINE refusal check rather than a helper, and
    // it is sc_settings again: scSaveSettings() tests the code itself right
    // under the await, because it has to DECIDE WHETHER TO ROLL BACK before
    // it can phrase anything. Its scSettingsSaveMessage() call is real but
    // sits 2,245 characters further on, outside the window every other
    // resource is measured in -- and widening the window for one resource
    // would weaken the pairing for all twenty-two. The inline test is the
    // honest in-window evidence, and the dedicated arm below drives the
    // three-outcome message directly rather than matching text for it.
    const REFUSAL_AWARE = ['scWriteRefusalText(', 'scSettingsSaveMessage(',
                           "err.code === 'FORBIDDEN'"];
    let viaHelper = 0;
    for (const resource of TIER_A_GATED) {
      const at = html.indexOf("scData('write', '" + resource + "'");
      ok(at > 0, resource + ' has a write call site in sairncode.html');
      const window_ = html.slice(at, at + 1800);
      const used = REFUSAL_AWARE.filter((h) => window_.indexOf(h) !== -1);
      ok(used.length > 0,
         '...and its failure branch is refusal-aware, via ' + used.join(' / '));
      if (window_.indexOf('scWriteRefusalText(') !== -1) viaHelper += 1;
    }
    // THE OTHER DIRECTION, AND IT IS THE HALF THE OLD MAGIC NUMBER WAS FOR.
    // The count used to be `TIER_A_GATED.length + 1`, which stopped being true
    // the moment one gated resource used the other helper. Derived from what
    // was actually measured above, so it still fails if the helper creeps onto
    // a resource where the transient sentence remains accurate -- that call
    // site would be outside every window counted here.
    // ── sc_settings' THREE OUTCOMES, DRIVEN RATHER THAN GREPPED ───────────
    // The window above proves it TESTS for a refusal. This proves it SAYS
    // something different for each outcome, which is the property that matters:
    // saved / refused / stored-here-only must never collapse into two, and a
    // refusal must carry the server's own words rather than a local paraphrase.
    {
      const sctx = { scSettingsSaveMessage: null };
      require('vm').createContext(sctx);
      require('vm').runInContext(
        grab('function scSettingsSaveMessage(res, whatSaved) {'), sctx);
      const savedMsg = sctx.scSettingsSaveMessage({ synced: true }, 'Practice name');
      const refusedMsg = sctx.scSettingsSaveMessage(
        { synced: false, refused: true,
          error: { code: 'FORBIDDEN', message: 'Only a Compliance Admin can change practice-level settings.' } },
        'Practice name');
      const localMsg = sctx.scSettingsSaveMessage({ synced: false, refused: false }, 'Practice name');
      ok(savedMsg !== refusedMsg && refusedMsg !== localMsg && savedMsg !== localMsg,
         'sc_settings tells its three outcomes apart -- saved / refused / stored '
         + 'on this device only are three different sentences, never two');
      ok(refusedMsg.indexOf('Only a Compliance Admin') !== -1,
         '...and the refusal carries the SERVER\'s own words: ' + refusedMsg.slice(0, 60));
      ok(!/until resolved|will not see it/.test(refusedMsg),
         '...and does NOT promise the refusal resolves itself, which is the whole '
         + 'reason this pairing exists');
    }
    const uses = (html.match(/scWriteRefusalText\(/g) || []).length;
    ok(uses === viaHelper + 1,
       'scWriteRefusalText is called exactly once per gated write site that uses '
       + 'it, plus its own definition -- ' + viaHelper + ' + 1 = ' + uses + '. A '
       + 'caller outside those sites would mean it crept onto a resource where '
       + '"until resolved" is still true');
  }

  console.log('\nALL ' + n + ' ASSERTIONS PASS');
})().catch((e) => { console.error('\nFAILED: ' + (e && e.message)); process.exit(1); });
