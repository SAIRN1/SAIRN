// api/b28-role-from-token.test.js
//
// Run:  node api/b28-role-from-token.test.js
//
// ── THE DEFECT, IN ONE SENTENCE ─────────────────────────────────────────────
// `MODE_PREPARED_ONLY` decided whether the caller may move client trust money
// from the ROLE INSIDE THE SIGNED SESSION TOKEN and never asked the database,
// so an attorney demoted to paralegal kept writing `law_trusttx` for as long as
// the token lived -- `SESSION_TTL_MS`, **12 hours** (api/_lib/auth.js:104).
//
// And the half that made it worse rather than merely possible: the SETTLING
// STEP, which exists precisely because "between the signature and the write the
// world has up to TOKEN_TTL_MS to move", re-read `active=eq.true` and **nothing
// about role**. A disbarred attorney who is still on the payroll is active. So
// the one check that did reach the database was asking the wrong column.
//
// ── WHY THE TOKEN IS NOT A WEAKER COPY OF THE DATABASE, IT IS A DIFFERENT
//    FACT ────────────────────────────────────────────────────────────────────
// A signed token is not forgeable and that is exactly what makes this easy to
// miss: every instinct that says "the signature is valid" is correct. The
// signature proves WHO ASKED and WHEN THEY SIGNED IN. It cannot prove what they
// are allowed to do NOW, because it was minted before now. Authentication
// survives in a token; authorisation does not.
//
// ── WHAT IS DRIVEN ──────────────────────────────────────────────────────────
// The REAL dispatcher in api/sd-data.js, with a recorded PostgREST stand-in --
// the same harness shape as api/b18-countersign-lock.test.js, whose comments
// explain why a thin payload would make "some refusal happened" read as "the
// lock refused". No database is touched and no live request is made.
//
// EVERY REFUSAL ARM IS PAIRED WITH A CONTROL THAT MUST BE ALLOWED. A suite
// where everything is refused proves a lockout, not a gate.
//
// Exit: 0 all arms passed · 1 an arm FAILED

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['b28', 'role', 'from', 'token', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const { signSessionToken } = require('./_lib/auth');
const cs = require('./_lib/countersign');

const HASH = 'b28-role-hash';
const KEY = 'KEY-FOR-' + HASH;
// Contains the word `placeholder` on purpose -- tools/redaction_check.py's
// `generic_credential_assignment` pattern matches a 16+ char literal assigned
// to something called `token`, and `placeholder` is one of its
// PLACEHOLDER_MARKERS. Declaring the fixture rather than exempting it; the
// reasoning is recorded at the same constant in api/b18-countersign-lock.test.js.
const FIXTURE_TOKEN = 'b28-cs-token-placeholder';

let pass = 0, fail = 0;
const failed = [];
function ok(l) { pass++; console.log('  ok    ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL  ' + l);
  if (why) console.log('        ' + String(why).slice(0, 700));
}
function is(cond, label, detail) { if (cond) ok(label); else bad(label, detail); }
function section(t) { console.log('\n' + t); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}
function eCode(res) { return (res.body && res.body.error && res.body.error.code) || ''; }
function eMsg(res) { return (res.body && res.body.error && res.body.error.message) || ''; }

// ── THE POSTGREST STAND-IN ──────────────────────────────────────────────────
// `opts.dbRoles` is the whole point of this file: employee_id -> the role the
// DATABASE currently holds, which is allowed to disagree with the token.
// Defaulting it to the token's own role would make every arm pass by agreeing
// with itself, so an absent entry is an explicit `MISSING` and the arms that
// care say which employees they are defining.
function pgMock(calls, opts) {
  opts = opts || {};
  const roles = opts.dbRoles || {};
  return async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    calls.push({ url: u, method: method });
    if (/_countersign_tokens/.test(u)) {
      if (method === 'PATCH') {
        return { ok: true, status: 200,
                 json: async () => (opts.tokenRow ? [{ id: 'tok-1' }] : []) };
      }
      return { ok: true, status: 200,
               json: async () => (opts.tokenRow ? [opts.tokenRow] : []) };
    }
    if (/_employee_auth/.test(u)) {
      if (opts.rosterDown) {
        return { ok: false, status: 503,
                 json: async () => ({ message: 'upstream unavailable' }) };
      }
      const m = u.match(/employee_id=eq\.([^&]+)/);
      const who = m ? decodeURIComponent(m[1]) : 'emp-1';
      if (opts.inactive && opts.inactive.indexOf(who) !== -1) {
        return { ok: true, status: 200, json: async () => [] };
      }
      const role = Object.prototype.hasOwnProperty.call(roles, who)
        ? roles[who] : 'MISSING-FROM-FIXTURE';
      return { ok: true, status: 200, json: async () => [
        { license_hash: HASH, employee_id: who, role: role, active: true }] };
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
  if (opts.tokenRow || opts.sendToken) headers[hdrName] = FIXTURE_TOKEN;
  await h({ method: 'POST', headers: headers, body: body }, res);
  return { res: res, calls: calls };
}
const callLaw = (r, a, role, p, o) => call('sairnlaw', 'x-law-countersign', r, a, role, p, o);
const callLeg = (r, a, role, p, o) => call('sairnlegacy', 'x-leg-countersign', r, a, role, p, o);

// A Deposit and not a Disbursement, and the reason is not brevity: a
// Disbursement goes through the `law_check_and_insert_disbursement` RPC and its
// own balance guard, so stubbing it would make these arms depend on a mock of a
// control they are not about. Same resource, same lock, same gate.
const TX1 = { id: 'TX-1', matter_id: 'M-1', client_id: 'CL-1',
              type: 'Deposit', amount: 500 };
const CR1 = { id: 'CR-1', case_id: 'CS-1' };

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

// ROLE LOOKUPS SPECIFICALLY, and the distinction is load-bearing rather than
// fussy. api/sd-data.js ALREADY re-reads the roster on every request for its
// per-request active-credential check (`select=active`), so counting
// `_employee_auth` requests would count that one too and no arm could tell the
// b28 read from the pre-existing one. The first spelling of R6 and M2 did
// exactly that and reported a leak that was not there.
function roleReads(calls) {
  return calls.filter((c) => /_employee_auth/.test(c.url)
                             && /select=employee_id,role/.test(c.url));
}

(async function main() {
  // ═══════════════════════════════════════════════════════════════════════
  section('R. THE PREPARED-ONLY BYPASS -- the role must come from the DATABASE');
  // ═══════════════════════════════════════════════════════════════════════

  // R1 IS THE REPRODUCTION. Before the fix this arm answered 200 and the
  // demoted attorney's deposit landed in client trust.
  {
    const { res } = await callLaw('law_trusttx', 'write', 'attorney', TX1, {
      dbRoles: { 'emp-1': 'paralegal' }
    });
    is(res.statusCode === 403 && eCode(res) === 'COUNTERSIGN_ROLE_REVOKED',
       'R1. THE REPRODUCTION: token says attorney, the roster says paralegal '
       + '-> 403 COUNTERSIGN_ROLE_REVOKED, not a trust write',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // R2 IS WHAT MAKES R1 A MEASUREMENT AND NOT A LOCKOUT. Same call, same
  // harness, roster agrees with the token.
  {
    const { res } = await callLaw('law_trusttx', 'write', 'attorney', TX1, {
      dbRoles: { 'emp-1': 'attorney' }
    });
    is(res.statusCode === 200,
       'R2. THE CONTROL: an attorney the roster STILL calls an attorney writes '
       + 'with no countersignature, exactly as MODE_PREPARED_ONLY intends',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // R3. THE ARM THAT PROVES THE FIX ONLY EVER REFUSES MORE, which is the
  // decision recorded at the fix. The roster role is required IN ADDITION to
  // the token role, not INSTEAD of it, so a paralegal PROMOTED to attorney who
  // has not signed in again is still refused -- with COUNTERSIGN_REQUIRED and
  // its obvious remedy, exactly as before b28. Reading authority purely from
  // the roster would have been tidier AND would have widened who can write
  // from a path that refuses today; that is not a change to smuggle into a
  // security fix, and this arm goes red if someone does.
  {
    const { res } = await callLaw('law_trusttx', 'write', 'paralegal', TX1, {
      dbRoles: { 'emp-1': 'attorney' }
    });
    is(res.statusCode === 403 && eCode(res) === 'COUNTERSIGN_REQUIRED',
       'R3. ONE-DIRECTIONAL: a PROMOTION in the roster does not grant the '
       + 'bypass to a stale token -> 403 COUNTERSIGN_REQUIRED, unchanged',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // R4. FAIL CLOSED. "Could not tell" is a third state and on an irreversible
  // trust write the only safe answer to it is refusal (PR 1.11).
  {
    const { res } = await callLaw('law_trusttx', 'write', 'attorney', TX1, {
      rosterDown: true
    });
    is(res.statusCode === 503 && eCode(res) === 'COUNTERSIGN_CHECK_FAILED',
       'R4. the roster lookup FAILS -> 503 COUNTERSIGN_CHECK_FAILED and no '
       + 'write, never the token\'s word as a fallback',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // R5. Deactivated, not demoted -- and the refusal is NOT this file's.
  // api/sd-data.js's pre-existing per-request active-credential re-check gets
  // there first and answers CREDENTIAL_INACTIVE. Asserting
  // COUNTERSIGN_NO_LONGER_ACTIVE here was the arm's first spelling and it was
  // wrong about which control fires: it would have reported b28 as the thing
  // refusing a deactivation that was already handled. `currentStanding`'s own
  // no-row refusal IS reachable and IS proved -- by S5, through the settling
  // loop, where no earlier check covers the OTHER attester.
  {
    const { res } = await callLaw('law_trusttx', 'write', 'attorney', TX1, {
      dbRoles: { 'emp-1': 'attorney' }, inactive: ['emp-1']
    });
    is(res.statusCode === 403 && eCode(res) === 'CREDENTIAL_INACTIVE',
       'R5. a DEACTIVATED employee is refused by the PRE-EXISTING active '
       + 're-check (CREDENTIAL_INACTIVE), not by b28 -- attribution asserted',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // R6. THE READ THAT DOES NOT HAPPEN. `requireCountersignature` returns null
  // for every read before the mode switch, so a read must cost ZERO b28 role
  // lookups. It still costs the pre-existing `select=active` one, which is why
  // this arm counts role lookups and not roster requests.
  {
    const { calls } = await callLaw('law_trusttx', 'read', 'attorney', null, {
      dbRoles: { 'emp-1': 'attorney' }
    });
    is(roleReads(calls).length === 0,
       'R6. a READ costs ZERO role lookups -- the new check is on the write '
       + 'path only',
       JSON.stringify(roleReads(calls).map((c) => c.url)).slice(0, 200));
  }

  // ═══════════════════════════════════════════════════════════════════════
  section('S. THE SETTLING STEP -- it re-read ACTIVE and nothing about ROLE');
  // ═══════════════════════════════════════════════════════════════════════

  // The caller here is a PARALEGAL, so the prepared-only short-circuit is not
  // taken and the full countersigned path runs. That is the only way to reach
  // the settling step for law_trusttx.
  const PARA = { callerId: 'emp-1' };

  // S1 IS THE SECOND REPRODUCTION. The row claims emp-2 countersigned as an
  // attorney and the roster now calls emp-2 a paralegal. Before the fix the
  // settling step read `active=eq.true`, found emp-2 active, and filed it.
  {
    const { res } = await callLaw('law_trusttx', 'write', 'paralegal', TX1,
      Object.assign({}, PARA, {
        tokenRow: row('law_trusttx', TX1),
        dbRoles: { 'emp-1': 'paralegal', 'emp-2': 'paralegal' }
      }));
    is(res.statusCode === 403 && eCode(res) === 'COUNTERSIGN_ROLE_REVOKED',
       'S1. THE SECOND REPRODUCTION: the countersigner was an attorney when '
       + 'they signed and is a paralegal at the moment of the write -> 403 '
       + 'COUNTERSIGN_ROLE_REVOKED',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // S2. The control for S1, and it is the arm that proves the settling step
  // still SETTLES rather than merely refusing.
  {
    const { res } = await callLaw('law_trusttx', 'write', 'paralegal', TX1,
      Object.assign({}, PARA, {
        tokenRow: row('law_trusttx', TX1),
        dbRoles: { 'emp-1': 'paralegal', 'emp-2': 'attorney' }
      }));
    is(res.statusCode === 200,
       'S2. THE CONTROL: the countersigner is still an attorney -> the write '
       + 'lands',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // S3. The PREPARER's standing is re-checked too, and it is a different
  // question from the signer's: `isPreparer`, not `isSigner`. A paralegal
  // moved to bookkeeper may no longer prepare a trust transaction -- and
  // bookkeeper is deliberately NOT in LAW_TRUST_PREPARE_ROLES
  // (api/_lib/law-roles.js:121 says why).
  {
    const { res } = await callLaw('law_trusttx', 'write', 'paralegal', TX1,
      Object.assign({}, PARA, {
        tokenRow: row('law_trusttx', TX1),
        dbRoles: { 'emp-1': 'bookkeeper', 'emp-2': 'attorney' }
      }));
    is(res.statusCode === 403 && eCode(res) === 'COUNTERSIGN_ROLE_REVOKED',
       'S3. the PREPARER is now a bookkeeper, who may not prepare trust '
       + '-> 403 COUNTERSIGN_ROLE_REVOKED',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // S4. A SIGNER WHO WAS PROMOTED IS NOT REVOKED. `owner` is in
  // LAW_BAR_ADMITTED_ROLES, so an attorney now listed as owner still qualifies.
  // Asserting a MATCH against the stored role would have refused this, which
  // is why the check asks "is the CURRENT role qualified" and not "is the
  // current role the same string".
  {
    const { res } = await callLaw('law_trusttx', 'write', 'paralegal', TX1,
      Object.assign({}, PARA, {
        tokenRow: row('law_trusttx', TX1),
        dbRoles: { 'emp-1': 'paralegal', 'emp-2': 'owner' }
      }));
    is(res.statusCode === 200,
       'S4. the countersigner was PROMOTED attorney -> owner, still '
       + 'bar-admitted -> the write lands (qualified, not identical)',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // S5. The pre-existing ACTIVE arm still fires. The role check must not have
  // replaced it -- a role row that reads `attorney` for an employee nobody
  // employs is still a refusal, and `active=eq.true` is what asks that.
  {
    const { res } = await callLaw('law_trusttx', 'write', 'paralegal', TX1,
      Object.assign({}, PARA, {
        tokenRow: row('law_trusttx', TX1),
        dbRoles: { 'emp-1': 'paralegal', 'emp-2': 'attorney' },
        inactive: ['emp-2']
      }));
    is(res.statusCode === 403 && eCode(res) === 'COUNTERSIGN_NO_LONGER_ACTIVE',
       'S5. REGRESSION: the ACTIVE half of the settling step still refuses, '
       + 'and with its own code',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // ═══════════════════════════════════════════════════════════════════════
  section('M. MODE_ALWAYS and the non-locked resources are UNCHANGED');
  // ═══════════════════════════════════════════════════════════════════════

  // M1. SAIRNlegacy's lock is MODE_ALWAYS: there is no signer short-circuit to
  // guard, so a director with no countersignature is refused for the reason it
  // always was. If this arm changed code, the fix leaked out of the branch it
  // belongs in.
  {
    const { res } = await callLeg('leg_cremations', 'write', 'director', CR1, {
      dbRoles: { 'emp-1': 'director' }
    });
    is(res.statusCode === 403 && eCode(res) === 'COUNTERSIGN_REQUIRED',
       'M1. MODE_ALWAYS is untouched: a director alone -> 403 '
       + 'COUNTERSIGN_REQUIRED, the same refusal as before',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // M2. THE INERTNESS ARM. `requireCountersignature` returns at its first line
  // for a resource that is not locked, so a non-trust law write must cost ZERO
  // roster lookups from this file. This is the arm that would catch the fix
  // being written above the `if (!mode) return null` guard, where it would add
  // a database round-trip to every write on the platform.
  {
    const { calls } = await callLaw('law_clients', 'write', 'attorney',
      { id: 'CL-9', display_name: 'X' }, { dbRoles: { 'emp-1': 'attorney' } });
    is(roleReads(calls).length === 0,
       'M2. a NON-LOCKED resource costs ZERO role lookups -- the check is '
       + 'inside the mode branch, not above it',
       JSON.stringify(roleReads(calls).map((c) => c.url)).slice(0, 200));
  }

  // ═══════════════════════════════════════════════════════════════════════
  section('A. THE ABLATION -- is the new check load-bearing?');
  // ═══════════════════════════════════════════════════════════════════════

  // A1. Not a source mutation: the same question answered structurally. If the
  // roster read were absent, R1 could not refuse, so the arm that proves the
  // check runs is that the demoted call made a lookup AT ALL. fourth's b26
  // finding was a gate that could be deleted entirely with every suite green;
  // the counter is to assert the mechanism, not only the outcome.
  {
    const { calls } = await callLaw('law_trusttx', 'write', 'attorney', TX1, {
      dbRoles: { 'emp-1': 'paralegal' }
    });
    const reads = roleReads(calls);
    is(reads.length === 1 && /employee_id=eq\.emp-1/.test(reads[0].url)
       && /active=eq\.true/.test(reads[0].url),
       'A1. the prepared-only path issues EXACTLY ONE role lookup, for the '
       + 'CALLER, filtered to active rows',
       JSON.stringify(reads.map((c) => c.url)).slice(0, 300));
  }

  // A2. And the settling step's query carries role as well. Selecting only
  // `employee_id` is precisely the defect S1 reproduces, so the column list is
  // asserted rather than assumed -- an arm that read the outcome alone would
  // stay green if a future edit dropped the column and the role check silently
  // compared `undefined`.
  {
    const { calls } = await callLaw('law_trusttx', 'write', 'paralegal', TX1,
      Object.assign({}, PARA, {
        tokenRow: row('law_trusttx', TX1),
        dbRoles: { 'emp-1': 'paralegal', 'emp-2': 'attorney' }
      }));
    const reads = roleReads(calls);
    is(reads.length === 2
       && reads.some((c) => /employee_id=eq\.emp-1/.test(c.url))
       && reads.some((c) => /employee_id=eq\.emp-2/.test(c.url)),
       'A2. the settling step issues TWO role lookups, one per attester -- '
       + 'the preparer AND the countersigner, neither assumed from the other',
       JSON.stringify(reads.map((c) => c.url)).slice(0, 300));
  }

  console.log('\n' + (fail ? 'FAILED' : 'PASSED') + ' -- ' + pass + ' passed, '
    + fail + ' failed'
    + (fail ? '\nFAILING ARMS: ' + failed.join(', ') : ''));
  process.exit(fail ? 1 : 0);
})().catch((e) => {
  console.error('HARNESS ERROR -- no verdict was reached, which is NOT a pass');
  console.error(e);
  process.exit(1);
});
