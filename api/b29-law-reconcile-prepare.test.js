// api/b29-law-reconcile-prepare.test.js
//
// Run:  node api/b29-law-reconcile-prepare.test.js
//
// ── MICHAEL'S DECISION, 2026-10-20, DRIVEN ──────────────────────────────────
// "Paralegal: goes back on the IOLTA reconcile list as PREPARE-ONLY. The
// attorney or owner attests (same two-stage rule as trust disbursement; a solo
// firm self-attests per the per-firm setting)."
//
// api/b19-iolta-reconcile-carveout.test.js asserts the POLICY TABLES. This
// asserts the ENDPOINT, because a grant on a frozen object is inert until a
// gate reads it -- and this exact resource is the one whose gate spent from b19
// to b27 refusing an attorney with a hand-written copy of a list the policy
// module had already superseded. A table and a gate agreeing is the thing that
// has to be measured here, not assumed.
//
// ── THE ARM THAT MATTERS MOST IS NOT THE PERMISSION ONE ─────────────────────
// A paralegal being admitted is one line. The reason b20 WITHDREW this grant is
// that a non-lawyer could produce a finished reconciliation that nothing
// records a lawyer as having reviewed, on the one figure a bar association
// audits. So P3 and P4 are the arms this suite exists for: EVERY reply is
// stamped `attested: false` and names who must attest -- including an owner's
// own run, because running the comparison and attesting to it are two acts
// even when one person does both.
//
// No database is touched. The real dispatcher runs against a recorded
// PostgREST stand-in.
//
// Exit: 0 all arms passed · 1 an arm FAILED

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['b29', 'law', 'reconcile', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const { signSessionToken } = require('./_lib/auth');
const lawRoles = require('./_lib/law-roles');

const HASH = 'b29-rec-hash';
const KEY = 'KEY-FOR-' + HASH;

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

function pgMock() {
  return async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    if (/_employee_auth/.test(u)) {
      const m = u.match(/employee_id=eq\.([^&]+)/);
      return { ok: true, status: 200, json: async () => [
        { license_hash: HASH, employee_id: m ? decodeURIComponent(m[1]) : 'emp-1',
          role: 'owner', active: true }] };
    }
    // Both legs readable with one row each, so the comparison runs rather than
    // short-circuiting on an unreadable table -- which would answer 503 and
    // make every arm below measure a provisioning state.
    if (/law_trusttx/.test(u) && method === 'GET') {
      return { ok: true, status: 200, json: async () => [
        { data: { id: 'TX-1', matter_id: 'M-1', client_id: 'CL-1',
                  type: 'Deposit', amount: 500 } }] };
    }
    if (/law_bankstatements/.test(u) && method === 'GET') {
      return { ok: true, status: 200, json: async () => [
        { data: { id: 'BS-1', closing_balance_cents: 50000 } }] };
    }
    if (method === 'POST' || method === 'PATCH') {
      return { ok: true, status: 200, json: async () => [{ id: 'x' }] };
    }
    return { ok: true, status: 200, json: async () => [] };
  };
}

function loadHandler() {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: HASH,
        trial_ends_at: null, stripe_subscription_id: null, app_id: 'sairnlaw' })
    }
  };
  global.fetch = pgMock();
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

async function reconcile(role) {
  const h = loadHandler();
  const res = mockRes();
  await h({
    method: 'POST',
    headers: {
      authorization: 'Bearer ' + KEY,
      'x-sd-auth': signSessionToken({
        app: 'sairnlaw', employee_id: 'emp-1', role: role, license_hash: HASH })
    },
    // THE VERB IS 'read', NOT lawRoles.LAW_RECONCILE_ACTION. That constant is
    // 'reconcile' and names the ACT for the role matrix and the deny message;
    // api/sd-data.js dispatches this resource on action === 'read' (:19049),
    // because the reconciliation is COMPUTED from two tables rather than
    // stored. The first spelling of this harness sent 'reconcile' and measured
    // the dispatcher's top-level action whitelist instead -- 400 "action must
    // be 'read' or 'write'" on all seven arms, including the ones that assert
    // a 403. A refusal for the wrong reason is the trap this suite's own
    // header warns about, and it arrived in the harness rather than the code.
    body: { action: 'read', resource: 'law_trust_reconcile',
            payload: {} }
  }, res);
  return res;
}

(async function main() {
  section('P. THE PREPARE-ONLY GRANT, AT THE ENDPOINT');

  // P1. THE REPRODUCTION. Before b29 the gate read LAW_RECONCILE_ROLES alone,
  // so a paralegal was refused 403 FORBIDDEN.
  {
    const res = await reconcile('paralegal');
    is(res.statusCode === 200 && res.body && res.body.ok === true,
       'P1. THE REPRODUCTION: a paralegal may now RUN the three-way '
       + 'reconciliation -- 200, not 403',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // P2. CONTROL: the bar-admitted roles still run it. Without this, P1 proves
  // the gate was opened, not that it was opened correctly.
  for (const role of ['owner', 'attorney']) {
    const res = await reconcile(role);
    is(res.statusCode === 200 && res.body && res.body.ok === true,
       'P2[' + role + ']. CONTROL: the finished-work set still runs it',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // P3. THE ARM THIS SUITE EXISTS FOR. A paralegal's run is marked, with the
  // role that produced it and who still owes the attestation.
  {
    const res = await reconcile('paralegal');
    const b = res.body || {};
    is(b.attested === false && b.prepare_only === true
       && b.prepared_by_role === 'paralegal'
       && Array.isArray(b.attestation_required_from)
       && b.attestation_required_from.indexOf('attorney') !== -1
       && b.attestation_required_from.indexOf('owner') !== -1
       && b.attestation_required_from.indexOf('paralegal') === -1,
       'P3. a paralegal\'s run is stamped attested:false, prepare_only:true, '
       + 'and names owner+attorney (never paralegal) as who must attest',
       JSON.stringify({ attested: b.attested, prepare_only: b.prepare_only,
                        by: b.prepared_by_role,
                        from: b.attestation_required_from }));
  }

  // P4. AND AN OWNER'S RUN IS STAMPED TOO. `attested: recMayRun` would have
  // been the natural-looking one-liner and would be the lie this stamp exists
  // to prevent: an owner running the comparison is somebody who MAY attest and
  // has not yet. `prepare_only` is what differs between the two, not
  // `attested`.
  for (const role of ['owner', 'attorney']) {
    const res = await reconcile(role);
    const b = res.body || {};
    is(b.attested === false && b.prepare_only === false
       && b.prepared_by_role === role,
       'P4[' + role + ']. a bar-admitted run is ALSO attested:false, with '
       + 'prepare_only:false -- running it is not attesting to it',
       JSON.stringify({ attested: b.attested, prepare_only: b.prepare_only,
                        by: b.prepared_by_role }));
  }

  // P5. AND A ROLE IN NEITHER SET IS STILL REFUSED. `bookkeeper` is the one
  // that matters: it is a money role, it is in LAW_TRUST_LOCKED's deliberate
  // exclusion, and the b18 note records that a bookkeeper cannot run this
  // reconciliation. Widening the gate must not have widened it to them.
  {
    const res = await reconcile('bookkeeper');
    is(res.statusCode === 403 && eCode(res) === 'FORBIDDEN',
       'P5. a bookkeeper is STILL refused 403 -- the gate was widened by '
       + 'exactly one role, not opened',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // P6. THE GATE READS THE MODULE, NOT A COPY. This is the defect b27 fixed on
  // this exact gate -- a hand-written roleSet({owner:true}) that said
  // owner-only while the module had said {owner, attorney} since b19, so an
  // attorney was refused in production by a superseded copy. The arm asserts
  // the SOURCE, because behaviour arms agree with a copy as happily as with
  // the module right up until the two diverge.
  {
    const fs = require('fs');
    const path = require('path');
    const { stripJs } = require('../tests/lib/strip_comments.js');
    const src = stripJs(
      fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8'));
    is(/lawRoles\.LAW_RECONCILE_ROLES\[recSess\.role\] === true/.test(src)
       && /lawRoles\.LAW_RECONCILE_PREPARE_ROLES\[recSess\.role\] === true/.test(src),
       'P6. both sets are read FROM api/_lib/law-roles.js at the gate, with '
       + '=== true, and neither is re-listed here',
       'finished=' + /LAW_RECONCILE_ROLES\[recSess\.role\] === true/.test(src)
         + ' prepare=' + /LAW_RECONCILE_PREPARE_ROLES\[recSess\.role\] === true/.test(src));
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
