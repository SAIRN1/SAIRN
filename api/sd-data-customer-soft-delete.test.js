// api/sd-data-customer-soft-delete.test.js
// Plain node:assert tests. Run: node api/sd-data-customer-soft-delete.test.js
//
// sd_customers gained a soft_delete verb on 2026-09-12, and unlike the other
// twenty-two soft-deletable StoneDesk resources this one closes a defect that
// was VISIBLE TO THE USER AND UNDID ITSELF.
//
// custDelete() filtered the record out of the local array and stopped there.
// saveSD3Data() writes the SURVIVORS through one row at a time, so the deleted
// customer's server row was never touched -- and sdHydrateCustomers() merges
// the server's rows back in BY ID on the next load. The customer came back.
// The confirm said "Delete this customer?" with no caveat.
//
// AND IT REACHED A CUSTOMER. api/stonedesk-track.js resolves a live order
// tracking link against this table by customer_id, so in the window between
// the local delete and the resurrection a customer could still read their job
// status from a record the shop believed was gone.
//
// THE READ FILTER IS THE HALF THAT MAKES A DELETION STICK, and it is asserted
// first for that reason. The client cannot filter a record it has deleted --
// it no longer knows the record exists to skip it. Only the query can.
//
// The panel half is tests/customer_delete_does_not_resurrect.js.

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || 'test-secret-for-sd-data-harnesses';
const assert = require('assert');
const { signSessionToken } = require('./_lib/auth');

const TEST_LICENSE_HASH = 'test-hash';
const CUST_ID = 'C-1001';

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
  res.status = c => { res.statusCode = c; return res; };
  res.json = p => { res.body = p; return res; };
  return res;
}
function mockReq(body, role) {
  const headers = { authorization: 'Bearer GOOD-KEY' };
  if (role !== null) headers['x-sd-auth'] = sdSession(role || 'owner');
  return { method: 'POST', headers, body };
}
function storedRow(extra) {
  return Object.assign({
    name: 'A. Customer', phone: '555-0100', project: 'Kitchen',
    status: 'fabricating', quote: 8900
  }, extra || {});
}
function loadHandler(fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: TEST_LICENSE_HASH,
        trial_ends_at: null, stripe_subscription_id: null })
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}
function recorder(routes) {
  const calls = [];
  return {
    calls,
    patches: () => calls.filter(c => c.method === 'PATCH'),
    posts: () => calls.filter(c => c.method === 'POST'),
    impl: async (url, init) => {
      const method = (init && init.method) || 'GET';
      const body = init && init.body ? JSON.parse(init.body) : null;
      calls.push({ url: String(url), method, body });
      const r = routes(String(url), method, body);
      return { ok: r.status >= 200 && r.status < 300, status: r.status,
               json: async () => r.json, text: async () => JSON.stringify(r.json) };
    }
  };
}

let passed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log('  ok   - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

async function main() {
  console.log('api/sd-data.js -- sd_customers soft delete');
  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';
  const del = { action: 'soft_delete', resource: 'sd_customers', payload: { id: CUST_ID } };

  // ── the half that makes a deletion stick ─────────────────────────────────
  await test('read filters deleted rows IN THE QUERY -- the client cannot do this', async () => {
    const rec = recorder(() => ({ status: 200, json: [] }));
    const h = loadHandler(rec.impl);
    const res = mockRes();
    await h(mockReq({ action: 'read', resource: 'sd_customers' }), res);
    assert.strictEqual(res.statusCode, 200);
    const read = rec.calls.find(c => /sd_customers/.test(c.url));
    assert.ok(read, 'no read was issued');
    assert.ok(/data->>_deleted_at=is\.null/.test(read.url),
      'a deleted customer would still be merged back in by sdHydrateCustomers: ' + read.url);
  });

  // ── the gate ─────────────────────────────────────────────────────────────
  await test('no session -> 401, nothing touched', async () => {
    const rec = recorder(() => { throw new Error('must not be reached'); });
    const h = loadHandler(rec.impl);
    const res = mockRes();
    await h(mockReq(del, null), res);
    assert.strictEqual(res.statusCode, 401);
    assert.strictEqual(rec.calls.length, 0);
  });

  for (const role of ['sales', 'install']) {
    await test('role "' + role + '" cannot delete a customer -> 403', async () => {
      const rec = recorder(() => { throw new Error('must not be reached'); });
      const h = loadHandler(rec.impl);
      const res = mockRes();
      await h(mockReq(del, role), res);
      assert.strictEqual(res.statusCode, 403);
      assert.strictEqual(rec.calls.length, 0);
    });
  }

  // ── a delete is not an edit ──────────────────────────────────────────────
  await test('the marker goes on the STORED record, not on the caller\'s copy', async () => {
    const rec = recorder((u, m) => m === 'PATCH'
      ? { status: 200, json: [{ data: {} }] }
      : { status: 200, json: [{ data: storedRow() }] });
    const h = loadHandler(rec.impl);
    const res = mockRes();
    await h(mockReq({ action: 'soft_delete', resource: 'sd_customers',
                      payload: { id: CUST_ID, status: 'complete', quote: 1, name: 'Someone Else' } }), res);
    assert.strictEqual(res.statusCode, 200);
    const p = rec.patches()[0];
    assert.ok(p, 'no PATCH issued');
    assert.strictEqual(p.body.data.name, 'A. Customer');
    assert.strictEqual(p.body.data.status, 'fabricating');
    assert.strictEqual(p.body.data.quote, 8900);
    assert.ok(p.body.data._deleted_at);
    assert.strictEqual(p.body.data._deleted_by, 'EMP-OWNER');
    // No upsert -- a delete must not also re-create the row it is deleting.
    assert.strictEqual(rec.posts().length, 0);
  });

  // ── NOT A SILENT SUCCESS ─────────────────────────────────────────────────
  // A customer that exists only in this browser has no server row. Answering
  // "deleted" would report work that did not happen, and the caller needs to
  // know the local removal was the whole of it -- nothing else will say so.
  await test('no server row -> 404, said plainly rather than reported as deleted', async () => {
    const rec = recorder(() => ({ status: 200, json: [] }));
    const h = loadHandler(rec.impl);
    const res = mockRes();
    await h(mockReq(del), res);
    assert.strictEqual(res.statusCode, 404);
    assert.strictEqual(res.body.error.code, 'NOT_FOUND');
    assert.strictEqual(rec.patches().length, 0);
  });

  await test('an un-migrated table -> 503 NOT_PROVISIONED, which is the state it is in TODAY', async () => {
    const rec = recorder(() => ({ status: 404, json: {} }));
    const h = loadHandler(rec.impl);
    const res = mockRes();
    await h(mockReq(del), res);
    assert.strictEqual(res.statusCode, 503);
    assert.strictEqual(res.body.error.code, 'NOT_PROVISIONED');
  });

  await test('an unreadable store -> 502 saying the record is STILL THERE, not 404', async () => {
    const rec = recorder(() => ({ status: 500, json: { message: 'boom' } }));
    const h = loadHandler(rec.impl);
    const res = mockRes();
    await h(mockReq(del), res);
    assert.strictEqual(res.statusCode, 502);
    assert.strictEqual(res.body.error.code, 'READ_FAILED');
    assert.ok(/still there/i.test(res.body.error.message), res.body.error.message);
    assert.strictEqual(rec.patches().length, 0);
  });

  await test('deleting twice reports already_deleted and writes nothing', async () => {
    const rec = recorder((u, m) => m === 'PATCH'
      ? { status: 200, json: [{ data: {} }] }
      : { status: 200, json: [{ data: storedRow({ _deleted_at: '2026-09-11T00:00:00.000Z' }) }] });
    const h = loadHandler(rec.impl);
    const res = mockRes();
    await h(mockReq(del), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.already_deleted, true);
    assert.strictEqual(rec.patches().length, 0);
  });

  await test('soft_delete is registered for sd_customers in the merged registry', async () => {
    delete require.cache[require.resolve('./_resources/index.js')];
    const reg = require('./_resources/index.js');
    assert.deepStrictEqual(reg.EXTRA_ACTIONS['sd_customers'], ['soft_delete']);
  });

  console.log(passed + ' passed');
}

main();
