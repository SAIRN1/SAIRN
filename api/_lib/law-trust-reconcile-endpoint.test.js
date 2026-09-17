// api/_lib/law-trust-reconcile-endpoint.test.js
// REQUIREMENT: an UNREADABLE transaction table REFUSES rather than reconciling
//   a balance of zero against a real bank statement -- that would report a
//   total loss of client trust money whose actual cause was a failed read, on
//   the one figure a bar association audits
//
//
// Run: node api/_lib/law-trust-reconcile-endpoint.test.js
//
// The ENDPOINT half. law-trust-reconcile.test.js proves the arithmetic; this
// proves the gate, and the one thing that matters most on this resource: an
// UNREADABLE transaction table must REFUSE, not reconcile a balance of zero
// against a real bank statement. That would report a total loss of client trust
// money whose cause was a failed read, on the one figure a bar association
// audits.
'use strict';
const path = require('path');
const ROOT = path.join(__dirname, '..', '..');

process.env.SUPABASE_URL = 'https://fake.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'fake-service-key';

const licenseMod = require(path.join(ROOT, 'api/_lib/license.js'));
licenseMod.validateLicenseKey = async () => ({
  valid: true, active: true, license_hash: 'HASH1', app_id: 'sairnlaw',
  stripe_subscription_id: 'sub_1', trial_ends_at: null
});

const authMod = require(path.join(ROOT, 'api/_lib/auth.js'));
authMod.tokenFromRequest = (req) => req.headers['x-test-token'] || null;
authMod.verifySessionToken = (token, licHash, expectedApp) => {
  if (!token) return null;
  if (expectedApp !== 'sairnlaw') {
    throw new Error('expected app scope not sairnlaw: ' + expectedApp);
  }
  return JSON.parse(token);
};

let TX = [
  { data: { id: 'T1', client_id: 'CL-1', type: 'Deposit', amount: 5000, date: '2026-09-01' } },
  { data: { id: 'T2', client_id: 'CL-2', type: 'Deposit', amount: 1000, date: '2026-09-02' } },
  { data: { id: 'T3', client_id: 'CL-1', type: 'Disbursement', amount: 500, date: '2026-09-03' } }
];
let ST = [{ data: { id: 'BS-1', statement_date: '2026-09-30', bank_balance: 5500 } }];
let MISSING = {};

global.fetch = async (url) => {
  const table = (url.match(/rest\/v1\/([a-z_]+)\?/) || [])[1];
  if (MISSING[table]) return { ok: false, status: 404, json: async () => ({}) };
  const body = { law_trusttx: TX, law_bankstatements: ST }[table];
  if (body === undefined) throw new Error('Unmocked fetch: ' + url);
  return { ok: true, status: 200, json: async () => body };
};

delete require.cache[require.resolve(path.join(ROOT, 'api/sd-data.js'))];
const handler = require(path.join(ROOT, 'api/sd-data.js'));

function fakeRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}
async function call(role, payload) {
  const req = {
    method: 'POST',
    headers: { authorization: 'Bearer testkey',
               'x-test-token': role ? JSON.stringify({ role, employee_id: 'E1' }) : undefined },
    body: { action: 'read', resource: 'law_trust_reconcile', payload: payload || null }
  };
  const res = fakeRes();
  await handler(req, res);
  return res;
}

let pass = 0, fail = 0;
async function t(name, fn) {
  MISSING = {};
  try { await fn(); pass++; console.log('PASS ' + name); }
  catch (e) { fail++; console.log('FAIL ' + name + ' -- ' + e.message); }
}
function eq(a, b, m) {
  if (JSON.stringify(a) !== JSON.stringify(b)) {
    throw new Error((m || 'mismatch') + ': expected ' + JSON.stringify(b)
                    + ' got ' + JSON.stringify(a));
  }
}

(async () => {
  // ── THE GATE ─────────────────────────────────────────────────────────────
  await t('no session is 401, not an empty reconciliation', async () => {
    eq((await call(null)).statusCode, 401);
  });
  await t('a paralegal CANNOT read the reconciliation', async () => {
    // IOLTA's own rule: whoever can move money out must not be the one who
    // reconciles the account.
    const res = await call('paralegal');
    eq(res.statusCode, 403);
    eq(res.body.error.code, 'FORBIDDEN');
  });
  await t('an attorney CANNOT either', async () => {
    eq((await call('attorney')).statusCode, 403);
  });
  await t('owner CAN', async () => {
    eq((await call('owner')).statusCode, 200);
  });
  // ── `admin` IS NOT A SAIRNlaw ROLE AND NEVER WAS (corrected 2026-09-16) ──
  // This asserted `admin` gets 200, matching LAW_RECONCILE_ROLES when it read
  // `{ owner: true, admin: true }`. ROLES_BY_APP.sairnlaw is owner / attorney /
  // paralegal, so verifySessionToken refuses an `admin` token for this app
  // before the role gate is reached -- the key could never match and
  // reconciliation was owner-only in practice. The literal was corrected in
  // 7884c4a5 and THIS ARM WAS LEFT ASSERTING THE IMPOSSIBLE, which made this
  // suite red from that commit until now. Mine, and I did not run this file.
  await t('admin is REFUSED -- it is not a role SAIRNlaw can issue', async () => {
    const r = await call('admin');
    eq(r.statusCode === 401 || r.statusCode === 403, true,
       'admin answered ' + r.statusCode);
  });

  // ── THE ARITHMETIC, THROUGH THE REAL HANDLER ─────────────────────────────
  await t('the ledger and per-client allocations agree, in cents', async () => {
    const d = (await call('owner')).body.data;
    eq(d.legs.allocation_vs_ledger.ledger_cents, 550000);
    eq(d.legs.allocation_vs_ledger.agrees, true);
    eq(d.clients.length, 2);
  });
  await t('the bank leg agrees as of the statement date', async () => {
    const d = (await call('owner')).body.data;
    eq(d.legs.bank_vs_ledger.statement_date, '2026-09-30');
    eq(d.legs.bank_vs_ledger.agrees, true);
    eq(d.status, 'PARTIAL', 'no device total supplied, so one comparable leg of two');
  });
  await t('supplying the device total makes it BOTH comparable legs and AGREES',
    async () => {
      // TWO, not three, as of 2026-09-16: allocation_vs_ledger is labelled
      // structural and excluded, because driven it cannot disagree -- both
      // traversals skip on identical predicates, so the two sums are the same
      // arithmetic over the same survivors. AGREES still requires every leg
      // that CAN disagree to have been compared.
      const d = (await call('owner', { client_total_cents: 550000 })).body.data;
      eq(d.legs_compared, 2);
      eq(d.status, 'AGREES');
      eq(d.legs.allocation_vs_ledger.structural, true);
      eq(d.row_conservation.holds, true);
    });
  await t('...and a WRONG device total is caught as a sync divergence', async () => {
    const d = (await call('owner', { client_total_cents: 500000 })).body.data;
    eq(d.legs.device_vs_server.agrees, false);
    eq(d.status, 'DISAGREES');
    eq(d.legs_disagreeing, ['device_vs_server']);
  });

  // ── THE PART THIS FILE EXISTS FOR ────────────────────────────────────────
  await t('an UNREADABLE law_trusttx REFUSES with 503 -- it does not reconcile zero',
    async () => {
      MISSING = { law_trusttx: true };
      const res = await call('owner');
      eq(res.statusCode, 503);
      eq(res.body.error.code, 'NOT_PROVISIONED');
      // Reconciling an unreadable table would report a $0 ledger against a
      // $5,500 statement: a total loss of client trust money, caused by a read.
      eq(/Nothing was reconciled/.test(res.body.error.message), true);
    });
  await t('an unreadable law_bankstatements is survivable and NOT silently empty',
    async () => {
      MISSING = { law_bankstatements: true };
      const res = await call('owner');
      eq(res.statusCode, 200);
      eq(res.body.statements_readable, false);
      eq(res.body.data.legs.bank_vs_ledger.agrees, null,
         'NOT COMPARED is not agreement');
      eq(res.body.data.status, 'PARTIAL');
    });

  // ── NO ROW-LEVEL DATA LEAVES THE BRANCH ──────────────────────────────────
  await t('the response carries NO transaction rows', async () => {
    const res = await call('owner');
    eq(res.statusCode, 200, 'the 200 is the precondition for this arm meaning anything');
    const blob = JSON.stringify(res.body);
    eq(blob.indexOf('T1'), -1, 'a reconciliation is not a trust-ledger export');
    eq(blob.indexOf('BS-1'), -1);
    eq(blob.indexOf('CL-1') !== -1, true, 'per-client BALANCES are the point');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
