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
  sc_compliance: 'admin|biller|auditor',   // the one per-resource override
  sc_credential_scope: 'admin|biller',
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
const TIER_A_GATED = (() => {
  const src = require('fs').readFileSync(path.join(ROOT, 'api/sd-data.js'), 'utf8');
  const m = /const SC_TIER_A_WRITE_GATED = \[([^\]]*)\];/.exec(src);
  assert.ok(m, 'SC_TIER_A_WRITE_GATED not found in api/sd-data.js');
  return JSON.parse('[' + m[1].replace(/'/g, '"').replace(/,\s*\]/, ']') + ']');
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
const rolesFor = (resource) => TIER_A_OVERRIDES[resource] || TIER_A_ROLES;
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
    ok(writeOpen.length === 21,
       '21 resources still accept an ordinary write with the licence key alone '
       + '-- the 22 non-billing ones minus sc_auth_requests\' conditional gate, '
       + 'which is what "the other 22 stay as-is" means measured rather than '
       + 'asserted (got ' + writeOpen.length + ')');
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
  // not a discovery: these six accepted a write from the licence key alone
  // until now.
  section('6. the six Tier A billing resources require a role to WRITE');
  {
    ok(TIER_A_GATED.length === 6,
       'the handler gates exactly six resources -- ' + TIER_A_GATED.join(', '));
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
    ok(anon401 === 6,
       'all six answer 401 NO_SESSION to an unsigned write, without touching '
       + 'storage -- ' + anon401 + '/6');
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
    ok(auditorElsewhere === 5,
       'CONTROL: and an auditor is still refused on the other five -- the '
       + 'exception is an EXCEPTION, not a widened shared list. '
       + auditorElsewhere + '/5');
    ok(rolesFor('sc_claims').indexOf('coder') === -1,
       'DECIDED: a `coder` CANNOT write sc_claims. Coherent with the split this '
       + 'app already has -- sc_coded_items is the coder\'s own resource and is '
       + 'ungated -- and claims submission is billing-side by design');
    const coderClaims = await call(h, { resource: 'sc_claims', action: 'write',
                                        payload: { id: 'W1' }, token: token('coder') });
    ok(coderClaims.code === 403 && !coderClaims.sawUpstream,
       '...driven: a coder session is refused 403 on sc_claims');
    const coderCoded = await call(h, { resource: 'sc_coded_items', action: 'write',
                                       payload: { id: 'W1' } });
    ok(coderCoded.code === 200 && coderCoded.sawUpstream,
       'CONTROL: sc_coded_items -- the coder\'s own resource -- is still ungated, '
       + 'which is what makes the exclusion above a split rather than a lockout');

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
    // it reads as covered. Every one of the six write sites must route its
    // failure branch through it, and the other twenty must NOT -- on those, the
    // original sentence is still accurate.
    for (const resource of TIER_A_GATED) {
      const at = html.indexOf("scData('write', '" + resource + "'");
      ok(at > 0, resource + ' has a write call site in sairncode.html');
      const window_ = html.slice(at, at + 1400);
      ok(/scWriteRefusalText\(/.test(window_),
         '...and its failure branch routes through scWriteRefusalText');
    }
    const uses = (html.match(/scWriteRefusalText\(/g) || []).length;
    ok(uses === TIER_A_GATED.length + 1,
       'the helper is called exactly ' + TIER_A_GATED.length + ' times plus its '
       + 'own definition -- ' + uses + '. A 7th caller would mean it crept onto '
       + 'a resource where the original sentence is still true');
  }

  console.log('\nALL ' + n + ' ASSERTIONS PASS');
})().catch((e) => { console.error('\nFAILED: ' + (e && e.message)); process.exit(1); });
