// tests/failsafe/witness_countersign.js
//
// Run:  node tests/failsafe/witness_countersign.js
//
// THE COUNTERSIGN HALF OF THE WITNESSING LOCK -- the half sixty-six arms never
// entered.
//
// ── WHY THIS FILE EXISTS, AND IT IS NOT "MORE COVERAGE" ─────────────────────
// `python tests/failsafe/countersign_coverage_probe.py` measured it on
// 2026-09-14: every refusal on `api/sv-witness.js`'s `countersign` action could
// be DELETED and all three existing suites stayed green --
// witness_atomicity.js (14), witness_recovery.js (14), api/sv-witness.test.js
// (38). The lock was correct; nothing on this platform would have noticed if it
// stopped being correct.
//
// The sharpest of the six was SAME_PERSON, whose own comment in the lock reads
// *"A COUNTERSIGNATURE BY THE AUTHOR IS NOT A COUNTERSIGNATURE. This is the
// entire content of two person, and without it the setting is a second click by
// the same hand."* On a DEA-relevant, append-only register where a correction is
// a SECOND row and the wrong one stands forever.
//
// ── WHY IT WAS MISSED, WHICH WAS NOT AN OVERSIGHT ───────────────────────────
// Item 83 asked whether the transition is ATOMIC and whether RECOVERY works,
// and answered both well -- about `requireWitness()`, the SPEND path.
// `countersign` is a DIFFERENT ENTRY POINT on the same lock, reached over HTTP
// by a second person. Pass three's own commit disclosed the scope accurately.
// What nobody had done was measure what the undisclosed half cost.
//
// ── EVERY ARM HERE IS KEYED TO A MUTATION THAT SURVIVED ─────────────────────
// Not written to the code and then declared sufficient. Each numbered arm below
// names the probe mutation it is there to kill, so the two files can be checked
// against each other rather than trusted:
//
//   M1  SAME_PERSON              -> if (false)      §3
//   M2  ALREADY_COUNTERSIGNED    -> if (false)      §4
//   M3  ALREADY_SPENT            -> if (false)      §5
//   M4  EXPIRED                  -> if (false)      §6
//   M5  countersign `<=` -> `<`  (the boundary)     §7
//   M6  spend-path `<=` -> `<`   (the boundary)     §8
//
// M5 and M6 are the two the recovery suite could never have caught by adding
// more of what it already had: it proves the window at TTL-1 and TTL+1, both
// SIDES of the boundary and neither ON it, and `<=` and `<` agree everywhere
// except at exactly `expires_at`. A window LENGTH was proven; the COMPARISON
// OPERATOR was not. One millisecond, in the fail-safe direction. The arms below
// freeze `Date.now` and land exactly on it.
//
// ── WHAT THIS CANNOT SEE, STATED RATHER THAN IMPLIED ────────────────────────
// The HTTP session, licence and REST layers are STUBBED. These arms prove the
// DECISION LOGIC -- which refusal for which state, and in which order -- and
// prove nothing about PostgREST, about `_lib/auth`'s real signature
// verification, or about the live database. Two consequences worth naming:
//   * A real countersign never round-trips here, so schema drift on
//     `countersign_employee_id` / `countersign_role` is invisible to this file.
//   * `active=eq.true` doing what it says is a property of the database. The
//     deactivated-caller arm proves the lock refuses when the lookup comes back
//     EMPTY, not that the filter is spelled correctly.
// Both are the same limitation api/sv-witness.test.js already declares for
// requireWitness, in the same words, and for the same reason.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

// ── THE STUBS GO IN BEFORE THE LOCK IS REQUIRED ─────────────────────────────
// `api/sv-witness.js` DESTRUCTURES its dependencies at require time
// (`const { verifySessionToken, tokenFromRequest } = require('./_lib/auth')`),
// so replacing the exports afterwards would change nothing and every arm below
// would be driving the real signature verifier while claiming to drive a stub.
// The real module is loaded first and only the two functions are overridden, so
// nothing else in `_lib/auth` is silently replaced by a weaker version.
const API = path.join(__dirname, '..', '..', 'api');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://db.example';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'svc-key';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || 'x'.repeat(48);

let SESSION = null;                       // what verifySessionToken returns
let LICENSE = { valid: true, active: true, license_hash: 'L1' };

const authPath = require.resolve(path.join(API, '_lib', 'auth.js'));
require(authPath);
require.cache[authPath].exports = Object.assign({}, require.cache[authPath].exports, {
  tokenFromRequest: () => (SESSION ? 'stub-session-token' : null),
  verifySessionToken: () => SESSION
});

const licPath = require.resolve(path.join(API, '_lib', 'license.js'));
require(licPath);
require.cache[licPath].exports = Object.assign({}, require.cache[licPath].exports, {
  validateLicenseKey: async () => LICENSE
});

const W = require(path.join(API, 'sv-witness.js'));
const svAuth = require(path.join(API, 'sv-auth.js'));
const EMP = svAuth.EMPLOYEE_TABLE;

let pass = 0, fail = 0;
const queue = [];
function t(name, fn) { queue.push([name, fn]); }
function section(s) { queue.push([s, null]); }

// ── THE FIXTURES ARE RELATIVE TO THE REAL CLOCK, DELIBERATELY ───────────────
// This was a hardcoded wall-clock instant on the first attempt and the EXPIRED
// arm FAILED, reporting 200: the constant sat a few hours in the FUTURE of the
// machine running it, so `PAST` was not past and an expired token was not
// expired. Only the boundary arms freeze the clock; every other arm runs against
// the real one, so the fixtures have to be anchored to the same clock the code
// reads. A fixture that is only sometimes in the past is a fixture that only
// sometimes tests anything.
const REAL_NOW_FN = Date.now;
const NOW = Date.now();
const FUTURE = new Date(NOW + 3600000).toISOString();
const PAST = new Date(NOW - 3600000).toISOString();
const PAYLOAD = { id: 'c1', drug: 'ketamine', qty: 2, vet: 'dr-a' };

// ── A REST STUB THAT ANSWERS FROM A SCRIPT ──────────────────────────────────
// Matched on a URL substring AND the method, because the countersign path hits
// `sairnvet_witness_tokens` twice -- once GET to read the row, once PATCH to
// record the signature -- and a needle that could not tell them apart would
// let the PATCH be served the GET's answer and still look green.
function fakeRest(plan) {
  const calls = [];
  global.fetch = async (url, init) => {
    const method = (init && init.method) || 'GET';
    calls.push({ url: String(url), method: method, body: init && init.body });
    for (const [needle, answer] of plan) {
      if (String(url).indexOf(needle) !== -1 && (answer.method || 'GET') === method) {
        return {
          ok: answer.ok !== false,
          status: answer.status || 200,
          json: answer.throwsOnJson
            ? async () => { throw new Error('204 No Content has no body'); }
            : async () => answer.body
        };
      }
    }
    return { ok: true, status: 200, json: async () => [] };
  };
  return calls;
}

// A caller the employee table confirms is live and active, with a role. The
// ROLE COMES FROM HERE and not from the session, which is the lock's own rule:
// a demotion has to take effect at once rather than waiting out a token.
function caller(id, role) {
  return [EMP + '?license_hash=eq.L1&employee_id=eq.' + id, { body: [{ employee_id: id, role: role || 'dvm' }] }];
}
function tokenRow(extra) {
  return [['sairnvet_witness_tokens?license_hash', {
    method: 'GET',
    body: [Object.assign({
      id: 'r1', witness_employee_id: 'dr-a', countersign_employee_id: null,
      spent_at: null, expires_at: FUTURE
    }, extra || {})]
  }]];
}
const PATCH_OK = ['sairnvet_witness_tokens?id=eq.r1', { method: 'PATCH', status: 204, throwsOnJson: true }];

function mkRes() {
  const r = { code: 0, body: null, sent: 0 };
  r.status = (c) => { r.code = c; return r; };
  r.json = (b) => { r.body = b; r.sent++; return r; };
  return r;
}
function mkReq(body) {
  return { method: 'POST', headers: { authorization: 'Bearer LK-TEST' }, body: body };
}

// Countersign as `who`, against a token row described by `row`.
async function countersign(who, role, row, extraPlan) {
  SESSION = who ? { employee_id: who, role: role || 'dvm', app: 'sairnvet' } : null;
  const plan = tokenRow(row).concat(extraPlan || [caller(who, role), PATCH_OK]);
  const calls = fakeRest(plan);
  const res = mkRes();
  await W(mkReq({ action: 'countersign', token: 'tok-good' }), res);
  return { res: res, calls: calls };
}

// ── FREEZING THE CLOCK ──────────────────────────────────────────────────────
// The boundary arms are the only way `<=` can be told from `<`, and they are
// only meaningful if `expires_at` and `Date.now()` are the SAME MILLISECOND. A
// real clock cannot be asked for that. Restored in a `finally` AFTER the await
// resolves -- restoring before it would leave the arm measuring the real clock
// and reporting a pass for a comparison it never made.
async function atExactly(ms, fn) {
  const real = Date.now;
  Date.now = () => ms;
  try { return await fn(); } finally { Date.now = real; }
}

function ctx(extra) {
  return Object.assign({
    resource: 'sv_controlled', payload: PAYLOAD, licHash: 'L1',
    rest: (p) => 'https://db.example/rest/v1/' + p,
    headers: {}, token: 'tok-good'
  }, extra || {});
}
function spendRow(extra) {
  return [['sairnvet_witness_tokens?license_hash', {
    method: 'GET',
    body: [Object.assign({
      id: 'r1', content_hash: W.contentHash('sv_controlled', PAYLOAD),
      witness_employee_id: 'dr-a', countersign_employee_id: null,
      spent_at: null, expires_at: FUTURE
    }, extra || {})]
  }]];
}

// ════════════════════════════════════════════════════════════════════════════
section('1. the harness reaches the countersign handler at all');
// If this section fails, every refusal arm below is passing for the wrong
// reason -- a stub that never enters the handler refuses everything, and a
// suite of refusals that all fire on the same stub error is indistinguishable
// from a suite that works. This is the negative control on the harness itself.
t('a valid countersign by a DIFFERENT active prescriber SUCCEEDS', async () => {
  const { res } = await countersign('dr-b');
  assert.strictEqual(res.code, 200, 'the lock must OPEN for a real second signature');
  assert.strictEqual(res.body.ok, true);
  assert.strictEqual(res.body.countersigned, true);
  assert.strictEqual(res.body.countersign_employee_id, 'dr-b');
});
t('the PATCH records WHO signed and their role, not merely that someone did', async () => {
  const { calls } = await countersign('dr-b');
  const patch = calls.filter((c) => c.method === 'PATCH')[0];
  assert.ok(patch, 'a signature was recorded');
  const sent = JSON.parse(patch.body);
  assert.strictEqual(sent.countersign_employee_id, 'dr-b');
  assert.strictEqual(sent.countersign_role, 'dvm',
    'an unattributed countersignature is not a two-person control, it is a flag');
});
t('a 204 No Content PATCH is a SUCCESS, not a 502', async () => {
  // PostgREST answers PATCH 204 unless return=representation is set, and
  // parsing unconditionally turns a landed write into an error. The stub throws
  // from .json() so an unconditional parse cannot pass this arm.
  const { res } = await countersign('dr-b');
  assert.strictEqual(res.code, 200);
});

// ════════════════════════════════════════════════════════════════════════════
section('2. who may countersign');
t('NO SESSION refuses with NO_SESSION', async () => {
  SESSION = null;
  fakeRest(tokenRow());
  const res = mkRes();
  await W(mkReq({ action: 'countersign', token: 'tok-good' }), res);
  assert.strictEqual(res.code, 401);
  assert.strictEqual(res.body.error.code, 'NO_SESSION');
});
t('a NON-PRESCRIBER refuses -- a manager is not a clinician', async () => {
  const { res } = await countersign('mgr-1', 'manager');
  assert.strictEqual(res.code, 403);
  assert.strictEqual(res.body.error.code, 'NOT_A_PRESCRIBER');
});
t('the ROLE comes from the DATABASE ROW, not the session token', async () => {
  // The session claims dvm; the employee row says tech. A demotion must take
  // effect at once rather than waiting out the token's life.
  SESSION = { employee_id: 'dr-b', role: 'dvm', app: 'sairnvet' };
  fakeRest(tokenRow().concat([
    [EMP + '?license_hash=eq.L1&employee_id=eq.dr-b', { body: [{ employee_id: 'dr-b', role: 'tech' }] }],
    PATCH_OK
  ]));
  const res = mkRes();
  await W(mkReq({ action: 'countersign', token: 'tok-good' }), res);
  assert.strictEqual(res.body.error.code, 'NOT_A_PRESCRIBER',
    'trusting the role in the token lets a demoted vet keep countersigning');
});
t('a DEACTIVATED caller refuses even with a valid session', async () => {
  const { res } = await countersign('dr-b', 'dvm', null,
    [[EMP + '?license_hash', { body: [] }], PATCH_OK]);
  assert.strictEqual(res.code, 401);
  assert.strictEqual(res.body.error.code, 'NO_SESSION',
    'a signature from a revoked account carries a name that no longer means anything');
});
t('a missing token is a 400, not a 404 -- different fixes', async () => {
  SESSION = { employee_id: 'dr-b', role: 'dvm', app: 'sairnvet' };
  fakeRest([caller('dr-b')]);
  const res = mkRes();
  await W(mkReq({ action: 'countersign' }), res);
  assert.strictEqual(res.code, 400);
});
t('an UNRECOGNISED token is NO_SUCH_TOKEN', async () => {
  SESSION = { employee_id: 'dr-b', role: 'dvm', app: 'sairnvet' };
  fakeRest([['sairnvet_witness_tokens?license_hash', { method: 'GET', body: [] }], caller('dr-b')]);
  const res = mkRes();
  await W(mkReq({ action: 'countersign', token: 'nope' }), res);
  assert.strictEqual(res.code, 404);
  assert.strictEqual(res.body.error.code, 'NO_SUCH_TOKEN');
});

// ════════════════════════════════════════════════════════════════════════════
section('3. M1 -- SAME_PERSON. THE ENTIRE CONTENT OF "TWO PERSON"');
// The mutation this kills: `if (row.witness_employee_id === caller.employee_id)`
// replaced with `if (false)`. Survived all three existing suites. With it gone
// the two-person setting is a second click by the same hand, and the record
// says two licensed veterinarians attested to a controlled-substance entry.
t('the AUTHOR cannot countersign their own record', async () => {
  const { res } = await countersign('dr-a');            // dr-a IS the witness
  assert.strictEqual(res.code, 409);
  assert.strictEqual(res.body.error.code, 'SAME_PERSON');
});
t('...and no signature is recorded when it refuses', async () => {
  const { calls } = await countersign('dr-a');
  assert.strictEqual(calls.filter((c) => c.method === 'PATCH').length, 0,
    'a refused countersignature that still writes is the defect wearing a 409');
});
t('CONTROL: a different person on the same row still succeeds', async () => {
  // Without this, "SAME_PERSON refuses" is also satisfied by a lock that
  // refuses every countersignature, which is a broken app rather than a safe one.
  const { res } = await countersign('dr-b');
  assert.strictEqual(res.code, 200);
});

// ════════════════════════════════════════════════════════════════════════════
section('4. M2 -- ALREADY_COUNTERSIGNED');
t('a record already countersigned refuses a second signature', async () => {
  // The caller is a THIRD person: if it were dr-a, SAME_PERSON would fire first
  // and this arm would stay green with the guard deleted.
  const { res } = await countersign('dr-c', 'dvm', { countersign_employee_id: 'dr-b' });
  assert.strictEqual(res.code, 409);
  assert.strictEqual(res.body.error.code, 'ALREADY_COUNTERSIGNED');
});
t('...and it does not overwrite the signature that is already there', async () => {
  const { calls } = await countersign('dr-c', 'dvm', { countersign_employee_id: 'dr-b' });
  assert.strictEqual(calls.filter((c) => c.method === 'PATCH').length, 0,
    'silently replacing dr-b with dr-c would rewrite who attested to a DEA record');
});

// ════════════════════════════════════════════════════════════════════════════
section('5. M3 -- ALREADY_SPENT on the countersign path');
t('a SPENT token cannot be countersigned after the fact', async () => {
  const { res } = await countersign('dr-b', 'dvm', { spent_at: PAST });
  assert.strictEqual(res.code, 409);
  assert.strictEqual(res.body.error.code, 'ALREADY_SPENT');
});
t('...which matters because the write already happened', async () => {
  // The record is on an append-only register with no removal path. A
  // countersignature added afterwards would make an unwitnessed write look
  // two-person in the audit trail, retroactively, and nothing can take it back.
  const { calls } = await countersign('dr-b', 'dvm', { spent_at: PAST });
  assert.strictEqual(calls.filter((c) => c.method === 'PATCH').length, 0);
});
t('PRECEDENCE: spent AND same-person reports ALREADY_SPENT', async () => {
  // Pinned deliberately. Section 3's arm relies on the spent check running
  // first; if the order were reversed, a spent token confirmed by its author
  // would report SAME_PERSON and section 3 would pass for the wrong reason.
  const { res } = await countersign('dr-a', 'dvm', { spent_at: PAST });
  assert.strictEqual(res.body.error.code, 'ALREADY_SPENT');
});

// ════════════════════════════════════════════════════════════════════════════
section('6. M4 -- EXPIRED on the countersign path');
t('an EXPIRED token cannot be countersigned', async () => {
  const { res } = await countersign('dr-b', 'dvm', { expires_at: PAST });
  assert.strictEqual(res.code, 409);
  assert.strictEqual(res.body.error.code, 'EXPIRED');
});
t('CONTROL: an unexpired token in the same shape succeeds', async () => {
  const { res } = await countersign('dr-b', 'dvm', { expires_at: FUTURE });
  assert.strictEqual(res.code, 200);
});

// ════════════════════════════════════════════════════════════════════════════
section('7. M5 -- THE COUNTERSIGN BOUNDARY, AT EXACTLY expires_at');
// `<=` and `<` agree everywhere except on this one millisecond. Every existing
// arm sits to one side of it or the other, so loosening the operator changed
// nothing any suite could see.
t('at EXACTLY expires_at, the countersign is EXPIRED -- `<=`, not `<`', async () => {
  const at = NOW;
  const out = await atExactly(at, () =>
    countersign('dr-b', 'dvm', { expires_at: new Date(at).toISOString() }));
  assert.strictEqual(out.res.body.error.code, 'EXPIRED',
    'a token whose expiry is NOW must be closed; `<` would let it through');
  assert.strictEqual(out.res.code, 409);
});
t('one millisecond EARLIER than expiry is still open', async () => {
  const at = NOW;
  const out = await atExactly(at, () =>
    countersign('dr-b', 'dvm', { expires_at: new Date(at + 1).toISOString() }));
  assert.strictEqual(out.res.code, 200,
    'the boundary must close AT expiry and not one millisecond before it');
});
t('the frozen clock is really frozen -- the arm above is not reading the real one', async () => {
  // A stub restored too early, or never installed, makes both boundary arms
  // measure the real clock and pass by luck. This asserts the mechanism.
  const seen = await atExactly(NOW, async () => Date.now());
  assert.strictEqual(seen, NOW, 'the stub was installed and the callback saw it');
  // Identity, not value. Comparing `Date.now()` to NOW would pass by luck the
  // moment the suite takes longer than a millisecond, which says nothing about
  // whether the real function came back.
  assert.strictEqual(Date.now, REAL_NOW_FN, 'and the real function is restored');
});

// ════════════════════════════════════════════════════════════════════════════
section('8. M6 -- THE SPEND-PATH BOUNDARY, AT EXACTLY expires_at');
// Not a countersign defect. Found by the same pass and it belongs with its
// twin: witness_recovery.js proves the window at TTL-1 and TTL+1 -- both SIDES,
// neither ON it -- so the WINDOW LENGTH was proven and the OPERATOR was not.
t('requireWitness at EXACTLY expires_at refuses WITNESS_EXPIRED', async () => {
  const at = NOW;
  const out = await atExactly(at, async () => {
    fakeRest(spendRow({ expires_at: new Date(at).toISOString() }).concat([
      ['sairnvet_witness_policy', { body: [{ require_two_person: false }] }],
      [EMP + '?license_hash', { body: [{ employee_id: 'dr-a' }] }],
      ['spent_at=is.null', { method: 'PATCH', body: [{ id: 'r1' }] }]
    ]));
    return W.requireWitness(ctx());
  });
  assert.ok(out, 'a token expiring exactly now must not be spendable');
  assert.strictEqual(out.status, 409);
  assert.strictEqual(out.body.error.code, 'WITNESS_EXPIRED');
});
t('CONTROL: one millisecond before expiry, the write proceeds', async () => {
  const at = NOW;
  const out = await atExactly(at, async () => {
    fakeRest(spendRow({ expires_at: new Date(at + 1).toISOString() }).concat([
      ['sairnvet_witness_policy', { body: [{ require_two_person: false }] }],
      [EMP + '?license_hash', { body: [{ employee_id: 'dr-a' }] }],
      ['spent_at=is.null', { method: 'PATCH', body: [{ id: 'r1' }] }]
    ]));
    return W.requireWitness(ctx());
  });
  assert.strictEqual(out, null, 'the lock must still open inside its window');
});

// ════════════════════════════════════════════════════════════════════════════
section('9. could-not-tell on the countersign path refuses too');
t('an upstream failure reading the token does not become a signature', async () => {
  SESSION = { employee_id: 'dr-b', role: 'dvm', app: 'sairnvet' };
  const calls = fakeRest([
    ['sairnvet_witness_tokens?license_hash', { method: 'GET', ok: false, status: 500, body: { message: 'boom' } }],
    caller('dr-b'), PATCH_OK
  ]);
  const res = mkRes();
  await W(mkReq({ action: 'countersign', token: 'tok-good' }), res);
  assert.strictEqual(res.code, 502);
  assert.strictEqual(calls.filter((c) => c.method === 'PATCH').length, 0);
});
t('a MISSING TABLE is NOT_PROVISIONED, not a generic failure', async () => {
  SESSION = { employee_id: 'dr-b', role: 'dvm', app: 'sairnvet' };
  fakeRest([
    ['sairnvet_witness_tokens?license_hash', { method: 'GET', ok: false, status: 404, body: { code: 'PGRST205' } }],
    caller('dr-b')
  ]);
  const res = mkRes();
  await W(mkReq({ action: 'countersign', token: 'tok-good' }), res);
  assert.strictEqual(res.code, 503);
  assert.strictEqual(res.body.error.code, 'NOT_PROVISIONED');
});
t('a failed PATCH is reported, never reported as countersigned', async () => {
  const { res } = await countersign('dr-b', 'dvm', null, [
    caller('dr-b'),
    ['sairnvet_witness_tokens?id=eq.r1', { method: 'PATCH', ok: false, status: 500, body: {} }]
  ]);
  assert.notStrictEqual(res.code, 200,
    'answering ok:true on a write that did not land is the silent-failure shape');
  assert.strictEqual(res.code, 502);
});
t('an INACTIVE LICENCE refuses before any of this is reached', async () => {
  const saved = LICENSE;
  LICENSE = { valid: true, active: false, license_hash: 'L1' };
  try {
    SESSION = { employee_id: 'dr-b', role: 'dvm', app: 'sairnvet' };
    fakeRest(tokenRow().concat([caller('dr-b'), PATCH_OK]));
    const res = mkRes();
    await W(mkReq({ action: 'countersign', token: 'tok-good' }), res);
    assert.strictEqual(res.code, 403);
    assert.strictEqual(res.body.error.code, 'LICENSE_INACTIVE');
  } finally { LICENSE = saved; }
});

// ════════════════════════════════════════════════════════════════════════════
section('10. the mutations this file claims to kill are the ones the probe lists');
// The two files have to agree or one of them is lying about coverage. This
// reads the probe's own mutation list rather than restating it, so adding a
// mutation there without an arm here is VISIBLE instead of silently uncovered.
t('every mutation in countersign_coverage_probe.py has a section here', () => {
  const probe = fs.readFileSync(
    path.join(__dirname, 'countersign_coverage_probe.py'), 'utf8');
  const listed = (probe.match(/^\s{4}\('([^']+)/gm) || []).length;
  assert.ok(listed >= 6,
    'the probe lists at least the six mutations this suite was built for; '
    + 'found ' + listed + ' -- if the probe grew, this suite has to grow with it');
  const self = fs.readFileSync(__filename, 'utf8');
  ['M1', 'M2', 'M3', 'M4', 'M5', 'M6'].forEach((m) => {
    assert.ok(new RegExp('section\\(\'\\d+\\. ' + m + ' ').test(self),
      m + ' must have its own section, keyed to the mutation it kills');
  });
});
t('the lock still refuses a self-countersignature in SOURCE, not only in behaviour', () => {
  // A belt-and-braces anchor on the one guard whose deletion is invisible
  // everywhere else. If the line moves, this arm says so rather than rotting
  // quietly -- the failure mode named in the eighth cross-domain discipline.
  const src = fs.readFileSync(path.join(API, 'sv-witness.js'), 'utf8');
  assert.ok(/row\.witness_employee_id === caller\.employee_id/.test(src),
    'SAME_PERSON is the entire content of the two-person control');
  assert.ok(/code: 'SAME_PERSON'/.test(src));
});

(async () => {
  const realFetch = global.fetch;
  for (const [name, fn] of queue) {
    if (!fn) { console.log('--- ' + name + ' ---'); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
  }
  global.fetch = realFetch;
  console.log('\nwitness_countersign: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
