// api/sd-data-quote-request-soft-delete.test.js
// Plain node:assert tests. Run: node api/sd-data-quote-request-soft-delete.test.js
//
// sd_quote_requests gained a soft_delete verb on 2026-09-12 (Michael's
// decision). It is the ONLY resource on this platform fed by an
// UNAUTHENTICATED PUBLIC FORM, so its volume is bounded by what strangers
// submit rather than by staff effort, and until this landed a shop could not
// remove a request at all.
//
// THE GAP IT CLOSES IS A CONFLATION, not an oversight. api/sd-data.js
// correctly refuses to let staff EDIT the submitted text -- it is the evidence
// of what a customer asked for -- and that argument had been standing in for
// an argument against REMOVAL. Only one of the two was ever decided.
//
// SO THE FIRST THING THIS SUITE PROVES IS THAT THE REFUSAL SURVIVED. Arm 4
// sends a payload stuffed with fields that would overwrite the stored record
// and asserts NONE of them reach the database: a delete must not double as the
// edit path this resource refuses to have. That is why the handler does a
// read-modify-write rather than marking the caller's copy, and it is the arm
// most worth keeping if this file is ever trimmed.
//
// EVERY ASSERTION DRIVES THE REAL HANDLER. api/_lib/license is stubbed because
// there is no licence server here; nothing else is. A stub of the branch under
// test would be a stub of the thing being tested.
//
// SD_AUTH_SECRET is set BEFORE api/_lib/auth is required -- signer and verifier
// both read it at call time, and an unset secret makes every session silently
// unverifiable, which is how api/sd-data-complaints-readonly.test.js spent its
// life asserting 401s it had named as 400s.

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || 'test-secret-for-sd-data-harnesses';
const assert = require('assert');
const { signSessionToken } = require('./_lib/auth');

const TEST_LICENSE_HASH = 'test-hash';
const REQ_ID = 'QR-1788000000-123';

function sdSession(role) {
  return signSessionToken({
    app: 'stonedesk',
    employee_id: 'EMP-' + String(role || 'owner').toUpperCase(),
    role: role || 'owner',
    license_hash: TEST_LICENSE_HASH
  });
}
function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (p) { res.body = p; return res; };
  return res;
}
// `role: null` sends NO session, so the no-session rung stays reachable rather
// than being made untestable by the fix that added the others.
function mockReq(body, role) {
  const headers = { authorization: 'Bearer GOOD-KEY' };
  if (role !== null) headers['x-sd-auth'] = sdSession(role || 'owner');
  return { method: 'POST', headers: headers, body: body };
}

// The stored record, deliberately carrying fields a caller could try to
// overwrite. `message` is the customer's own words -- the thing this resource
// exists to preserve.
function storedRow(extra) {
  return Object.assign({
    name: 'A. Customer',
    phone: '555-0100',
    message: 'Need a quote for a kitchen in Carrara.',
    sqft: 42,
    submitted_at: '2026-09-10T10:00:00.000Z'
  }, extra || {});
}

function loadHandler(fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: TEST_LICENSE_HASH,
                 trial_ends_at: null, stripe_subscription_id: null };
      }
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

// Records every call so an arm can assert what did NOT happen -- a PATCH that
// never fired is the only proof that a refusal refused.
function recorder(routes) {
  const calls = [];
  const impl = async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    const body = init && init.body ? JSON.parse(init.body) : null;
    calls.push({ url: u, method, body });
    const r = routes(u, method, body);
    return {
      ok: r.status >= 200 && r.status < 300,
      status: r.status,
      json: async () => r.json,
      text: async () => JSON.stringify(r.json)
    };
  };
  return { impl, calls, patches: () => calls.filter(c => c.method === 'PATCH') };
}

let passed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log('  ok   - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

async function main() {
  console.log('api/sd-data.js -- sd_quote_requests soft delete');
  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  const del = (extra) => Object.assign({ action: 'soft_delete', resource: 'sd_quote_requests',
                                         payload: { id: REQ_ID } }, extra || {});

  // ── the gate, which is SHARED with read and write rather than copied ─────
  await test('no session -> 401, and the database is never touched', async () => {
    const rec = recorder(() => { throw new Error('fetch must not be reached'); });
    const h = loadHandler(rec.impl);
    const res = mockRes();
    await h(mockReq(del(), null), res);
    assert.strictEqual(res.statusCode, 401);
    assert.strictEqual(res.body.error.code, 'NO_SESSION');
    assert.strictEqual(rec.calls.length, 0);
  });

  // 'sales' and 'install' are the app's OWN other roles -- ROLES_BY_APP lists
  // exactly owner/admin/sales/install for stonedesk. A made-up role would be
  // refused by signSessionToken() before the handler ever saw it, so this arm
  // would be asserting the signer's validation rather than the branch's gate.
  for (const role of ['sales', 'install']) {
    await test('role "' + role + '" -> 403, and the database is never touched', async () => {
      const rec = recorder(() => { throw new Error('fetch must not be reached'); });
      const h = loadHandler(rec.impl);
      const res = mockRes();
      await h(mockReq(del(), role), res);
      assert.strictEqual(res.statusCode, 403);
      assert.strictEqual(res.body.error.code, 'FORBIDDEN');
      assert.strictEqual(rec.calls.length, 0);
    });
  }

  await test('an admin CAN delete -- the gate is management, not owner-only', async () => {
    const rec = recorder((u, m) => m === 'PATCH'
      ? { status: 200, json: [{ data: {} }] }
      : { status: 200, json: [{ data: storedRow() }] });
    const h = loadHandler(rec.impl);
    const res = mockRes();
    await h(mockReq(del(), 'admin'), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(rec.patches()[0].body.data._deleted_by, 'EMP-ADMIN');
  });

  await test('no payload.id -> 400', async () => {
    const rec = recorder(() => { throw new Error('fetch must not be reached'); });
    const h = loadHandler(rec.impl);
    const res = mockRes();
    await h(mockReq({ action: 'soft_delete', resource: 'sd_quote_requests', payload: {} }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(rec.calls.length, 0);
  });

  // ── THE ARM THAT MATTERS MOST ────────────────────────────────────────────
  await test('the marker is added to the STORED record -- a caller cannot edit through delete', async () => {
    const rec = recorder((u, m) => m === 'PATCH'
      ? { status: 200, json: [{ data: {} }] }
      : { status: 200, json: [{ data: storedRow() }] });
    const h = loadHandler(rec.impl);
    const res = mockRes();
    // A hostile payload: every field here would be an EDIT if the handler
    // marked the caller's copy instead of what is stored.
    await h(mockReq(del({ payload: { id: REQ_ID, message: 'REWRITTEN', name: 'Someone Else', sqft: 9999 } })), res);
    assert.strictEqual(res.statusCode, 200);
    const patch = rec.patches()[0];
    assert.ok(patch, 'no PATCH was issued');
    assert.strictEqual(patch.body.data.message, 'Need a quote for a kitchen in Carrara.');
    assert.strictEqual(patch.body.data.name, 'A. Customer');
    assert.strictEqual(patch.body.data.sqft, 42);
    assert.ok(patch.body.data._deleted_at, '_deleted_at was not set');
    assert.strictEqual(patch.body.data._deleted_by, 'EMP-OWNER');
    // status is NOT in the PATCH -- a delete is not a status change.
    assert.ok(!('status' in patch.body), 'soft delete wrote a status');
  });

  await test('a request that is not there -> 404, and nothing is written', async () => {
    const rec = recorder((u, m) => m === 'PATCH'
      ? { status: 200, json: [] }
      : { status: 200, json: [] });
    const h = loadHandler(rec.impl);
    const res = mockRes();
    await h(mockReq(del()), res);
    assert.strictEqual(res.statusCode, 404);
    assert.strictEqual(res.body.error.code, 'NOT_FOUND');
    assert.strictEqual(rec.patches().length, 0);
  });

  await test('deleting an already-deleted request says so, and does not write again', async () => {
    const rec = recorder((u, m) => m === 'PATCH'
      ? { status: 200, json: [{ data: {} }] }
      : { status: 200, json: [{ data: storedRow({ _deleted_at: '2026-09-11T09:00:00.000Z' }) }] });
    const h = loadHandler(rec.impl);
    const res = mockRes();
    await h(mockReq(del()), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.already_deleted, true);
    assert.strictEqual(rec.patches().length, 0);
  });

  // ── A FAILED READ IS NOT A MISSING REQUEST ───────────────────────────────
  // The status write had to be taught this on 2026-09-04: telling staff a
  // request is gone is the one answer that stops them looking for it. The
  // delete path is a second chance to make the same mistake.
  await test('an unreadable store -> 502 READ_FAILED saying it is STILL THERE, not 404', async () => {
    const rec = recorder(() => ({ status: 500, json: { message: 'boom' } }));
    const h = loadHandler(rec.impl);
    const res = mockRes();
    await h(mockReq(del()), res);
    assert.strictEqual(res.statusCode, 502);
    assert.strictEqual(res.body.error.code, 'READ_FAILED');
    assert.ok(/still there/i.test(res.body.error.message),
      'the message does not say the request is still there: ' + res.body.error.message);
    assert.strictEqual(rec.patches().length, 0);
  });

  await test('an un-migrated table -> 503 NOT_PROVISIONED naming the SQL file', async () => {
    const rec = recorder(() => ({ status: 404, json: {} }));
    const h = loadHandler(rec.impl);
    const res = mockRes();
    await h(mockReq(del()), res);
    assert.strictEqual(res.statusCode, 503);
    assert.strictEqual(res.body.error.code, 'NOT_PROVISIONED');
    assert.ok(/stonedesk_public_surface_schema\.sql/.test(res.body.error.message));
  });

  // ── the read hides them, and the status write refuses them ───────────────
  await test('read filters soft-deleted rows out in the QUERY, not after', async () => {
    const rec = recorder(() => ({ status: 200, json: [] }));
    const h = loadHandler(rec.impl);
    const res = mockRes();
    await h(mockReq({ action: 'read', resource: 'sd_quote_requests' }), res);
    assert.strictEqual(res.statusCode, 200);
    const read = rec.calls.find(c => /sd_quote_requests/.test(c.url));
    assert.ok(read, 'no read was issued');
    assert.ok(/data->>_deleted_at=is\.null/.test(read.url),
      'the read does not filter deleted rows: ' + read.url);
  });

  // THE API IS THE BOUNDARY, NOT THE PANEL. The read above hides a deleted
  // request so no screen can offer the button -- but "the UI does not show it"
  // has never been an access rule on this platform, and promoting a deleted
  // request would resurrect it in every count computed from status.
  await test('a status change on a deleted request -> 409 DELETED, and nothing is written', async () => {
    const rec = recorder((u, m) => m === 'PATCH'
      ? { status: 200, json: [{ data: {} }] }
      : { status: 200, json: [{ data: storedRow({ _deleted_at: '2026-09-11T09:00:00.000Z' }) }] });
    const h = loadHandler(rec.impl);
    const res = mockRes();
    await h(mockReq({ action: 'write', resource: 'sd_quote_requests',
                      payload: { id: REQ_ID, status: 'promoted' } }), res);
    assert.strictEqual(res.statusCode, 409);
    assert.strictEqual(res.body.error.code, 'DELETED');
    assert.strictEqual(rec.patches().length, 0);
  });

  await test('a status change on a LIVE request still works -- the guard is not a block', async () => {
    const rec = recorder((u, m) => m === 'PATCH'
      ? { status: 200, json: [{ data: storedRow() }] }
      : { status: 200, json: [{ data: storedRow() }] });
    const h = loadHandler(rec.impl);
    const res = mockRes();
    await h(mockReq({ action: 'write', resource: 'sd_quote_requests',
                      payload: { id: REQ_ID, status: 'promoted' } }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(rec.patches().length, 1);
  });

  // ── the verb has to be REGISTERED or the dispatcher 400s before any of the
  //    above is reachable. Asserted against the registry the API itself
  //    merges, not against the app file, because that merge is the thing
  //    sd-data.js validates on.
  await test('soft_delete is registered for sd_quote_requests in the merged registry', async () => {
    delete require.cache[require.resolve('./_resources/index.js')];
    const reg = require('./_resources/index.js');
    assert.ok(reg.RESOURCE_NAMES.includes('sd_quote_requests'));
    assert.deepStrictEqual(reg.EXTRA_ACTIONS['sd_quote_requests'], ['soft_delete']);
  });

  console.log(passed + ' passed');
}

main();
