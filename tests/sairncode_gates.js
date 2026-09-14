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
//   1. `delete` on all 28 resources requires an `admin` session
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
};
// Gated only on a specific payload shape. Creating a draft, editing before
// review and logging a payer decision after the fact are all open; making a
// request SUBMISSION-READY is not. Section 4 drives both halves.
const CONDITIONALLY_WRITE_GATED = {
  sc_auth_requests: 'admin, on sign-off writes only (signedOffBy set, or status=submitted)',
};

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
  section('1. delete requires an ADMIN session -- on all 28 resources');
  {
    const nonAdmin = ROLES.filter((r) => r !== 'admin');
    ok(nonAdmin.length > 0, 'CONTROL: there are non-admin roles to refuse -- '
       + nonAdmin.join(', '));

    let refusedNoSession = 0, refusedNonAdmin = 0, reachedAsAdmin = 0;
    const leaks = [];
    for (const resource of SC.resources) {
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
    ok(refusedNoSession === 28,
       'all 28 refuse a delete with NO session, 403, without touching storage -- '
       + refusedNoSession + '/28');
    ok(refusedNonAdmin === 28,
       'all 28 refuse a delete from a signed-in ' + nonAdmin[0]
       + ' the same way -- ' + refusedNonAdmin + '/28');
    // WITHOUT THIS ARM THE TWO ABOVE WOULD PASS ON A HANDLER THAT REFUSED
    // EVERY DELETE FOR ANY REASON, INCLUDING A BROKEN ONE.
    ok(reachedAsAdmin === 28,
       'CONTROL: all 28 DO reach storage with a real admin session, and with an '
       + 'actual DELETE -- ' + reachedAsAdmin + '/28');
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
    const crossAdmin = await call(h, { resource: 'sc_claims', action: 'delete',
                                       payload: { id: 'X1' },
                                       token: token('admin', 'stonedesk') });
    ok(crossAdmin.code === 403 && !crossAdmin.sawUpstream,
       'a StoneDesk ADMIN session cannot delete sc_claims -- the token carries '
       + 'the right role and the wrong app: ' + crossAdmin.code);
    const other = await call(h, { resource: 'sc_claims', action: 'delete',
                                  payload: { id: 'X1' },
                                  token: token(auth.ROLES_BY_APP.sairnbiz[0], 'sairnbiz') });
    ok(other.code === 403 && !other.sawUpstream,
       'and neither can a SAIRNbiz owner session -- wrong app AND wrong role: '
       + other.code);
    const wrongLic = await call(h, { resource: 'sc_claims', action: 'delete',
                                     payload: { id: 'X1' },
                                     token: token('admin', 'sairncode', 'OTHER-HASH') });
    ok(wrongLic.code === 403 && !wrongLic.sawUpstream,
       'nor can a sairncode admin session bound to a different licence -- '
       + wrongLic.code);
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
    const ungated = await call(h, { resource: 'sc_auth_requests', action: 'write',
                                    payload: { id: 'A1', status: 'draft', note: 'x' } });
    ok(ungated.code === 200 && ungated.sawUpstream,
       'CONTROL: an ORDINARY sc_auth_requests write needs no session at all -- '
       + 'the gate below is scoped to sign-off, and this arm proves it is not '
       + 'simply gating the whole resource');

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
    const anon = await call(h, { resource: 'sc_auth_requests', action: 'write',
                                 payload: { id: 'A1', status: 'submitted' } });
    ok(anon.code === 403 && !anon.sawUpstream,
       'and so is a caller with no session at all');

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
    // THE CONDITIONAL GATE IS NOT COUNTED HERE, and that is the honest figure.
    // sc_auth_requests gates only the sign-off write, so a plain write to it is
    // open like the other 26 ordinary writes. Counting it as gated would report 2 of 28 when
    // the true unconditional figure is 1.
    ok(Object.keys(CONDITIONALLY_WRITE_GATED).every((r) => writeOpen.indexOf(r) !== -1),
       'and sc_auth_requests reads as OPEN to a plain write, because its gate is '
       + 'conditional -- section 4 is where that condition is driven');
    // A gate that APPEARS must fail this as loudly as one that disappears. The
    // table is the claim; the handler is the fact; disagreement is a finding
    // either way, and reporting only one direction is how a posture drifts
    // without anybody being told.
    ok(writeOpen.length === 27,
       'CONTROL: 27 resources accept an ordinary write with the licence key '
       + 'alone -- that is the OPEN FINDING this suite records rather than '
       + 'silently changes (measured ' + writeOpen.length + ')');
    const tierA = ['sc_ar', 'sc_claims', 'sc_revenue', 'sc_denial', 'sc_compliance',
                   'sc_credential_scope'];
    const openTierA = tierA.filter((t) => writeOpen.indexOf(t) !== -1);
    ok(openTierA.length === tierA.length,
       'and the six named Tier A resources are all among them, which is why the '
       + 'row is open: ' + openTierA.join(', '));
  }

  console.log('\nALL ' + n + ' ASSERTIONS PASS');
})().catch((e) => { console.error('\nFAILED: ' + (e && e.message)); process.exit(1); });
