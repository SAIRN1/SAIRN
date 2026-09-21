// tests/stonedesk_exec_msgs_gate.js
//
// REGRESSION for the sd_exec_msgs session/role gate (2026-09-21, hover
// finding, cold-scan pool). Until this fix, StoneDesk's private CEO/CFO/CTO
// executive chat (sd_exec_msgs) was served through SD_LOCAL_RESOURCES with
// no session or role check at all -- a caller holding only the shared
// fabrication-shop licence key could read, write, and delete every private
// executive message. Confirmed live before the fix: 200 ok:true, a private
// message returned verbatim, no session token sent. This suite pins the
// fix so it cannot silently regress.
//
// The gate enforces the SAME boundary stonedesk.html's own
// sdExecPrivileged() already uses client-side: a real, server-verified
// 'stonedesk' session with role owner or admin. 'ceo'/'cfo'/'cto' are not
// real employee roles in this platform's role model -- they are a label an
// owner/admin wears, chosen through a picker sdExecPrivileged() already
// gates -- so the server enforces owner/admin, not a role literally named
// 'ceo'.
//
// NOT A LIVE-DATABASE TEST. Same mock harness as
// api/sd-data-cross-tenant-dispatchers.test.js: global.fetch and
// api/_lib/license.js are stubbed, no real Supabase call is made.
//
// Run:  node tests/stonedesk_exec_msgs_gate.js

'use strict';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['cross', 'tenant', 'dispatchers', 'fixture'].join('-');

const assert = require('assert');
const path = require('path');

const SD_DATA = path.join(__dirname, '..', 'api', 'sd-data.js');
const LICENSE = path.join(__dirname, '..', 'api', '_lib', 'license.js');
const { signSessionToken } = require(path.join(__dirname, '..', 'api', '_lib', 'auth.js'));

const HASH_A = 'tenant-A-hash';

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}

function loadHandler(licHash, appId, fetchImpl) {
  delete require.cache[require.resolve(LICENSE)];
  require.cache[require.resolve(LICENSE)] = {
    exports: {
      validateLicenseKey: async function () {
        return {
          valid: true, active: true, license_hash: licHash,
          trial_ends_at: null, stripe_subscription_id: null, app_id: appId
        };
      }
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve(SD_DATA)];
  return require(SD_DATA);
}

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}

const MSG = { id: 'EM-1', role: 'ceo', text: 'Private strategy note.', ts: '2026-09-21T10:00:00Z' };

async function fetchImpl(url, opts) {
  const u = String(url);
  if (opts && opts.method === 'POST') {
    const sent = JSON.parse(opts.body);
    return { ok: true, status: 200, json: async () => [sent] };
  }
  if (opts && opts.method === 'PATCH') {
    return { ok: true, status: 200, json: async () => [{ data: MSG }] };
  }
  const q = u.indexOf('?') >= 0 ? u.slice(u.indexOf('?') + 1) : '';
  const eqs = [];
  q.split('&').forEach((part) => {
    const m = part.match(/^([a-z0-9_]+)=eq\.(.*)$/);
    if (m) eqs.push([m[1], decodeURIComponent(m[2])]);
  });
  const rows = [{ license_hash: HASH_A, exec_msg_id: 'EM-1', data: MSG }];
  const matches = rows.filter((r) => eqs.every((kv) => String(r[kv[0]]) === kv[1]));
  return { ok: true, status: 200, json: async () => matches };
}

(async () => {
  console.log('STONEDESK sd_exec_msgs SESSION/ROLE GATE -- regression for the 2026-09-21 fix\n');

  await test('no session at all -> 401 NO_SESSION (read)', async () => {
    const h = loadHandler(HASH_A, 'stonedesk', fetchImpl);
    const res = mockRes();
    await h({ method: 'POST', headers: { authorization: 'Bearer KEY-FOR-' + HASH_A },
      body: { action: 'read', resource: 'sd_exec_msgs', payload: {} } }, res);
    assert.strictEqual(res.statusCode, 401);
    assert.strictEqual(res.body.error.code, 'NO_SESSION');
  });

  await test('no session at all -> 401 NO_SESSION (write)', async () => {
    const h = loadHandler(HASH_A, 'stonedesk', fetchImpl);
    const res = mockRes();
    await h({ method: 'POST', headers: { authorization: 'Bearer KEY-FOR-' + HASH_A },
      body: { action: 'write', resource: 'sd_exec_msgs', payload: { id: 'EM-2', role: 'cfo', text: 'x' } } }, res);
    assert.strictEqual(res.statusCode, 401);
    assert.strictEqual(res.body.error.code, 'NO_SESSION');
  });

  await test('no session at all -> 401 NO_SESSION (soft_delete)', async () => {
    const h = loadHandler(HASH_A, 'stonedesk', fetchImpl);
    const res = mockRes();
    await h({ method: 'POST', headers: { authorization: 'Bearer KEY-FOR-' + HASH_A },
      body: { action: 'soft_delete', resource: 'sd_exec_msgs', payload: { id: 'EM-1' } } }, res);
    assert.strictEqual(res.statusCode, 401);
    assert.strictEqual(res.body.error.code, 'NO_SESSION');
  });

  await test('a valid session with a non-privileged role (sales) -> 403 FORBIDDEN', async () => {
    const h = loadHandler(HASH_A, 'stonedesk', fetchImpl);
    const res = mockRes();
    const token = signSessionToken({ app: 'stonedesk', employee_id: 'emp-1', role: 'sales', license_hash: HASH_A });
    await h({ method: 'POST',
      headers: { authorization: 'Bearer KEY-FOR-' + HASH_A, 'x-sd-auth': token },
      body: { action: 'read', resource: 'sd_exec_msgs', payload: {} } }, res);
    assert.strictEqual(res.statusCode, 403);
    assert.strictEqual(res.body.error.code, 'FORBIDDEN');
  });

  await test('a valid session with a non-privileged role (install) is refused on write too', async () => {
    const h = loadHandler(HASH_A, 'stonedesk', fetchImpl);
    const res = mockRes();
    const token = signSessionToken({ app: 'stonedesk', employee_id: 'emp-2', role: 'install', license_hash: HASH_A });
    await h({ method: 'POST',
      headers: { authorization: 'Bearer KEY-FOR-' + HASH_A, 'x-sd-auth': token },
      body: { action: 'write', resource: 'sd_exec_msgs', payload: { id: 'EM-3', role: 'cto', text: 'x' } } }, res);
    assert.strictEqual(res.statusCode, 403);
  });

  await test('a session valid for a DIFFERENT app is refused (Guardian Check 28)', async () => {
    const h = loadHandler(HASH_A, 'stonedesk', fetchImpl);
    const res = mockRes();
    const foreignToken = signSessionToken({ app: 'sairndental', employee_id: 'emp-1', role: 'owner', license_hash: HASH_A });
    await h({ method: 'POST',
      headers: { authorization: 'Bearer KEY-FOR-' + HASH_A, 'x-sd-auth': foreignToken },
      body: { action: 'read', resource: 'sd_exec_msgs', payload: {} } }, res);
    assert.strictEqual(res.statusCode, 401,
      'a sairndental session must not satisfy the stonedesk exec gate');
  });

  await test('owner CAN read sd_exec_msgs, and the fix does not break the resource', async () => {
    const h = loadHandler(HASH_A, 'stonedesk', fetchImpl);
    const res = mockRes();
    const token = signSessionToken({ app: 'stonedesk', employee_id: 'emp-owner', role: 'owner', license_hash: HASH_A });
    await h({ method: 'POST',
      headers: { authorization: 'Bearer KEY-FOR-' + HASH_A, 'x-sd-auth': token },
      body: { action: 'read', resource: 'sd_exec_msgs', payload: {} } }, res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.ok, true);
    assert.strictEqual(res.body.data[0].text, MSG.text);
  });

  await test('admin CAN write sd_exec_msgs, and the write round-trips real data', async () => {
    const h = loadHandler(HASH_A, 'stonedesk', fetchImpl);
    const res = mockRes();
    const token = signSessionToken({ app: 'stonedesk', employee_id: 'emp-admin', role: 'admin', license_hash: HASH_A });
    await h({ method: 'POST',
      headers: { authorization: 'Bearer KEY-FOR-' + HASH_A, 'x-sd-auth': token },
      body: { action: 'write', resource: 'sd_exec_msgs', payload: { id: 'EM-4', role: 'cfo', text: 'Board update.' } } }, res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.ok, true);
    assert.strictEqual(res.body.data.text, 'Board update.');
  });

  await test('admin CAN soft_delete sd_exec_msgs', async () => {
    const h = loadHandler(HASH_A, 'stonedesk', fetchImpl);
    const res = mockRes();
    const token = signSessionToken({ app: 'stonedesk', employee_id: 'emp-admin', role: 'admin', license_hash: HASH_A });
    await h({ method: 'POST',
      headers: { authorization: 'Bearer KEY-FOR-' + HASH_A, 'x-sd-auth': token },
      body: { action: 'soft_delete', resource: 'sd_exec_msgs', payload: { id: 'EM-1' } } }, res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.ok, true);
  });

  await test('NO REGRESSION: the other 20 SD_LOCAL_RESOURCES members are still ungated (sd_inventory)', async () => {
    const h = loadHandler(HASH_A, 'stonedesk', fetchImpl);
    const res = mockRes();
    await h({ method: 'POST', headers: { authorization: 'Bearer KEY-FOR-' + HASH_A },
      body: { action: 'read', resource: 'sd_inventory', payload: {} } }, res);
    assert.strictEqual(res.statusCode, 200,
      'sd_inventory (a genuinely shared shop record) must remain ungated -- this gate is scoped to sd_exec_msgs only');
  });

  await test('NO REGRESSION: sd_drawings write with no session still succeeds (scope check)', async () => {
    const h = loadHandler(HASH_A, 'stonedesk', fetchImpl);
    const res = mockRes();
    await h({ method: 'POST', headers: { authorization: 'Bearer KEY-FOR-' + HASH_A },
      body: { action: 'write', resource: 'sd_drawings', payload: { id: 'DR-1' } } }, res);
    assert.strictEqual(res.statusCode, 200);
  });

  // ── WHERE the gate sits, not just that it answers 401 ────────────────────
  // Added 2026-09-21 by tests/run_exec_msgs_gate_sabotage_probe.py, which
  // planted the gate BEHIND the PostgREST query and watched every arm above
  // stay GREEN. A gate that reads the private executive messages out of the
  // database and THEN answers 401 has already done the thing it exists to
  // prevent -- the rows are in the process, in the logs on any upstream error,
  // and one careless edit away from the response body. Same arm cc's
  // api/sd-data-leg-session-gate.test.js carries for the same reason.
  await test('the refusal happens BEFORE any query -- zero fetch calls on all three verbs', async () => {
    for (const action of ['read', 'write', 'soft_delete']) {
      let calls = 0;
      const counting = async function (url, opts) { calls++; return fetchImpl(url, opts); };
      const h = loadHandler(HASH_A, 'stonedesk', counting);
      const res = mockRes();
      await h({ method: 'POST', headers: { authorization: 'Bearer KEY-FOR-' + HASH_A },
        body: { action: action, resource: 'sd_exec_msgs', payload: { id: 'EM-1' } } }, res);
      assert.strictEqual(res.statusCode, 401, action + ' did not refuse');
      assert.strictEqual(calls, 0,
        action + ' refused only AFTER touching the table -- ' + calls + ' query(ies) ran');
    }
  });

  // ── THE REGISTER ENTRY THAT LET THIS SHIP, PINNED ────────────────────────
  // sd_exec_msgs sat at Tier B on "an internal message lost" for eleven days.
  // That sentence is TRUE and describes the wrong axis: a lost message is a
  // nuisance, so nothing about the row invited anyone to ask who could READ
  // the thing, and the missing gate looked acceptable the whole time. It moved
  // to A on 2026-09-21 on the third A criterion (its failure has already caused
  // a documented one), which is also what makes every later change to this
  // resource require a recorded independent review --
  // tools/tier_a_review_gate.py takes its Tier A set from this file and nowhere
  // else, so the letter in that cell is a live gate input, not a label.
  //
  // ASSERTED HERE because nothing else would notice it moving back: the
  // register's own checker verifies that every resource HAS a tier and that A
  // rows cite evidence -- never that a particular resource is rated correctly.
  // Reverting this cell to B is a silent, one-character un-gating of every
  // future change, and this arm is the only thing on the platform that fails
  // when it happens.
  await test('docs/CRITICALITY-TIERS.md still rates sd_exec_msgs Tier A, with evidence', () => {
    const fs = require('fs');
    const reg = fs.readFileSync(path.join(__dirname, '..', 'docs', 'CRITICALITY-TIERS.md'), 'utf8');
    const rows = reg.split('\n').filter((l) => l.indexOf('| `sd_exec_msgs` |') === 0);
    assert.strictEqual(rows.length, 1, 'expected exactly one sd_exec_msgs row, found ' + rows.length);
    const cells = rows[0].split('|').map((c) => c.trim());
    assert.strictEqual(cells[2], '**A**',
      'sd_exec_msgs is rated ' + cells[2] + '. It is the private executive channel and it has a '
      + 'documented exposure behind it; Tier A is what makes tools/tier_a_review_gate.py demand a '
      + 'review on the next change to it.');
    assert.ok(cells[4] && cells[4].length > 40,
      'the A row carries no real evidence cell -- a tier asserted with nothing to check it against is a label');
    // CONTROL: a genuinely-B sibling, so this arm cannot pass by matching any
    // row anywhere or by the file having been replaced with all-A rows.
    const cust = reg.split('\n').filter((l) => l.indexOf('| `sd_customers` |') === 0);
    assert.strictEqual(cust.length, 1);
    assert.strictEqual(cust[0].split('|').map((c) => c.trim())[2], '**B**',
      'the control row moved too -- this arm is matching the file, not the decision');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  if (fail) process.exit(1);
})();
