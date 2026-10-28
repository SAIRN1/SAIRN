// tests/sd_data_mech_write_unconfirmed.js
//
// REQUIREMENT: every SAIRNmechanical write branch in api/sd-data.js answers ok
//   ONLY when the store returned the row it saved. A save the store did not
//   echo is 502 WRITE_UNCONFIRMED, never a 200.
//
// Run:  node tests/sd_data_mech_write_unconfirmed.js
//
// ── THE DEFECT (cody b58) ──────────────────────────────────────────────────
// All four mech write paths POST with `Prefer: return=representation`, so a
// stored row comes back in the body. When none came back they answered ok
// anyway: the generic MECH_RECORDS branch (mech_quotes, mech_checks, mech_docs,
// mech_takeoffs) returned the request payload as if stored, and the three
// bespoke branches (mech_site_assets, mech_insurance_policies,
// mech_credentials) returned `data: null`. sairnmechanical.html clears the
// form on ok and mechPushOne() reports a backup -- the server-side half of the
// premature "synced" ack fixed on the client in b57.
//
// ABLATION: the last section puts the pre-b58 success lines back into a copy of
// api/sd-data.js and requires the empty-echo arms to go red on it, so a fixture
// that cannot tell the two apart is caught rather than trusted.

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const API = path.join(__dirname, '..', 'api');
process.env.SUPABASE_URL = 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || ['mech', 'unconfirmed', 'fixture'].join('-');

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}

const CASES = [
  ['mech_quotes', { id: 'Q-1', date: '2026-10-28', text: 'Replace RTU-4 compressor' }],
  ['mech_checks', { id: 'C-1', num: '1001', date: '2026-10-28', payee: 'Supply Co', amount: 120 }],
  ['mech_docs', { id: 'D-1', date: '2026-10-28', text: 'Permit 44' }],
  ['mech_takeoffs', { id: 'T-1', date: '2026-10-28', text: '7.5 ton' }],
  ['mech_site_assets', { asset_id: 'AST-1', customer_name: 'Ruiz Foods', site_name: 'Plant 1',
    asset_type: 'chiller', make: 'Trane', model: 'CVHE', serial_no: 'X1',
    refrigerant_type: 'r134a', refrigerant_charge_lb: 900 }],
  ['mech_insurance_policies', { policy_key: 'GL-2026', kind: 'general_liability', carrier: 'Acme Mutual',
    policy_no: 'GL-1', effective_on: '2026-01-01', expires_on: '2027-01-01',
    each_occurrence: 1000000, aggregate_limit: 2000000 }],
  ['mech_credentials', { credential_id: 'CRED-1', technician_id: 'tech-7', record_type: 'epa_608',
    epa_section: 'universal', has_expiry: false, issued_on: '2021-03-01', issuer: 'ESCO' }]
];

// `echo` is what the store does when it saved the row; `[]` is an answer that
// was read and holds no stored row.
function loadHandler(file, echo) {
  delete require.cache[require.resolve(path.join(API, '_lib/license'))];
  require.cache[require.resolve(path.join(API, '_lib/license'))] = {
    exports: { validateLicenseKey: async function () {
      return { valid: true, active: true, license_hash: 'test-hash', trial_ends_at: null,
               stripe_subscription_id: null, app_id: 'sairnmechanical' }; } }
  };
  const authPath = require.resolve(path.join(API, '_lib/auth'));
  delete require.cache[authPath];
  const realAuth = require(authPath);
  require.cache[authPath] = { exports: Object.assign({}, realAuth, {
    tokenFromRequest: function () { return 'tok'; },
    verifySessionToken: function () {
      return { employee_id: 'owner-1', role: 'owner', license_hash: 'test-hash', app: 'sairnmechanical' };
    }
  }) };
  global.fetch = async function (url, init) {
    const method = (init && init.method) || 'GET';
    if (/_employee_auth\?/.test(String(url))) {
      return { ok: true, status: 200, json: async () =>
        [{ license_hash: 'test-hash', employee_id: 'owner-1', role: 'owner', active: true }] };
    }
    if (method === 'GET') return { ok: true, status: 200, json: async () => [] };
    const sent = JSON.parse(init.body);
    return { ok: true, status: 201, text: async () => init.body,
             json: async () => (echo ? [Object.assign({}, sent, { data: sent.data || sent })] : []) };
  };
  delete require.cache[file];
  return require(file);
}

async function write(file, resource, payload, echo) {
  const h = loadHandler(file, echo);
  const res = mockRes();
  await h({ method: 'POST',
            headers: { authorization: 'Bearer MECH-TEST-KEY', 'x-sd-auth': 'tok' },
            body: { action: 'write', resource: resource, app_id: 'sairnmechanical', payload: payload } }, res);
  return res;
}

// The pre-b58 success lines, restored into a copy for the ablation.
const OLD = [
  ["if (wroteRow(rows) !== 'WROTE') { refuseUnconfirmedWrite(res, 'this site asset', NO_ROW_BACK); return; }\n      res.status(200).json({ ok: true, provisioned: true, data: rows[0] });",
   "res.status(200).json({ ok: true, provisioned: true, data: (Array.isArray(rows) && rows[0]) || null });"],
  ["if (wroteRow(insRows) !== 'WROTE') { refuseUnconfirmedWrite(res, 'this insurance policy', NO_ROW_BACK); return; }\n      res.status(200).json({ ok: true, provisioned: true, data: insRows[0] });",
   "res.status(200).json({ ok: true, provisioned: true, data: (Array.isArray(insRows) && insRows[0]) || null });"],
  ["if (wroteRow(rows) !== 'WROTE') { refuseUnconfirmedWrite(res, 'this credential', NO_ROW_BACK); return; }\n      res.status(200).json({ ok: true, provisioned: true, data: rows[0] });",
   "res.status(200).json({ ok: true, provisioned: true, data: (Array.isArray(rows) && rows[0]) || null });"],
  ["if (wroteRow(rows) !== 'WROTE') { refuseUnconfirmedWrite(res, resource, NO_ROW_BACK); return; }\n      res.status(200).json({ ok: true, data: rows[0].data });",
   "res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : mPayload });"]
];

async function main() {
  const LIVE = path.join(API, 'sd-data.js');
  console.log('api/sd-data.js -- every sairnmechanical write is ok only when the store returned the row');

  console.log('\n1. a save the store echoed is ok');
  for (const [resource, payload] of CASES) {
    await test(resource + ': echoed row -> 200 ok', async () => {
      const res = await write(LIVE, resource, payload, true);
      assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
      assert.ok(res.body && res.body.ok, JSON.stringify(res.body));
      assert.ok(res.body.data, 'ok must carry the stored row, got ' + JSON.stringify(res.body.data));
    });
  }

  console.log('\n2. a save the store did NOT echo is 502 WRITE_UNCONFIRMED, never ok');
  for (const [resource, payload] of CASES) {
    await test(resource + ': [] back -> 502 WRITE_UNCONFIRMED', async () => {
      const res = await write(LIVE, resource, payload, false);
      assert.strictEqual(res.statusCode, 502, JSON.stringify(res.body));
      assert.ok(!(res.body && res.body.ok), 'answered ok on an unconfirmed save');
      assert.strictEqual(res.body.error.code, 'WRITE_UNCONFIRMED');
    });
  }

  console.log('\n3. ABLATION: the pre-b58 lines must make section 2 go red');
  let src = fs.readFileSync(LIVE, 'utf8');
  const missing = OLD.filter(([now]) => src.split(now).length !== 2);
  await test('every fixed line is present exactly once (else this ablation tests nothing)', async () => {
    assert.strictEqual(missing.length, 0, missing.map(m => m[0].slice(0, 70)).join(' | '));
  });
  if (!missing.length) {
    for (const [now, old] of OLD) src = src.replace(now, old);
    const ABL = path.join(API, '.sd-data-ablate-' + process.pid + '.js');
    fs.writeFileSync(ABL, src);
    try {
      for (const [resource, payload] of CASES) {
        await test(resource + ': the OLD code answers ok on [] (proves section 2 can fail)', async () => {
          const res = await write(ABL, resource, payload, false);
          assert.strictEqual(res.statusCode, 200, 'old code did not answer 200: ' + res.statusCode);
          assert.ok(res.body && res.body.ok);
        });
      }
    } finally {
      try { fs.unlinkSync(ABL); } catch (e) {}
    }
  }

  console.log('\n' + (fail ? 'FAILED' : 'PASSED') + ' -- ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
}

main().catch(function (e) { console.error('COULD NOT RUN: ' + (e && e.stack || e)); process.exit(2); });
