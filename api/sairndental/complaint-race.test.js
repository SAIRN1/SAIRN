// api/sairndental/complaint-race.test.js
// Cross-endpoint regression test for design spec §0's race-handling
// decision: both public-complaint-thread.js (patient reply) and
// complaint-respond.js (owner reply) must each do a FRESH read
// immediately before writing, never trust a client-held/stale copy of
// the messages array -- otherwise a sequence of "patient replies,
// then owner replies" would silently lose the patient's message the
// moment the owner's request was built from state that predates it.
// Also covers the one state-transition rule from spec §0/§7.
// Run: node api/sairndental/complaint-race.test.js

const assert = require('assert');

function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (code) { res.statusCode = code; return res; };
  res.json = function (payload) { res.body = payload; return res; };
  res.setHeader = function () { return res; };
  res.end = function () { return res; };
  return res;
}

let passed = 0;
async function test(name, fn) {
  try {
    await fn();
    passed++;
    console.log('  ok - ' + name);
  } catch (err) {
    console.error('  FAIL - ' + name);
    console.error('    ' + err.message);
    process.exitCode = 1;
  }
}

async function main() {
  console.log('api/sairndental/complaint-race.test.js');

  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  // Shared in-memory "table" -- one row, mutated by whichever endpoint
  // writes to it, read fresh by the other. This is the actual thing
  // under test: does each endpoint re-read this shared state right
  // before it writes, or does it trust a value it already had?
  var store = {
    license_hash: 'abc123hash', complaint_id: 'COMP-1', access_token: 'tok-xyz',
    data: { id: 'COMP-1', patient_name: 'Jane', status: 'New', messages: [{ from: 'patient', text: 'Original complaint', at: '2026-08-12T10:00:00.000Z' }] }
  };

  global.fetch = async function (url, opts) {
    var u = String(url);
    if (!opts || !opts.method || opts.method === 'GET') {
      if (u.indexOf('access_token=eq.') !== -1 || u.indexOf('complaint_id=eq.') !== -1) {
        return { ok: true, json: async function () { return [Object.assign({}, store)]; } };
      }
    }
    if (opts && opts.method === 'POST') {
      var body = JSON.parse(opts.body);
      store = { license_hash: body.license_hash, complaint_id: body.complaint_id, access_token: body.access_token, data: body.data };
      return { ok: true, json: async function () { return [store]; } };
    }
    throw new Error('unexpected fetch: ' + u);
  };

  delete require.cache[require.resolve('../_lib/dental-public')];
  require.cache[require.resolve('../_lib/dental-public')] = { exports: { checkAndIncrementRateLimit: async function () { return { allowed: true }; } } };
  delete require.cache[require.resolve('../_lib/license')];
  require.cache[require.resolve('../_lib/license')] = { exports: { validateLicenseKey: async function () { return { valid: true, active: true, license_hash: 'abc123hash' }; } } };

  delete require.cache[require.resolve('./public-complaint-thread.js')];
  delete require.cache[require.resolve('./complaint-respond.js')];
  var threadHandler = require('./public-complaint-thread.js');
  var respondHandler = require('./complaint-respond.js');

  await test('patient reply, then owner reply -- both messages survive, in order', async () => {
    var threadRes = mockRes();
    await threadHandler({ method: 'POST', headers: {}, body: { token: 'tok-xyz', reply: 'Still waiting to hear back' } }, threadRes);
    assert.strictEqual(threadRes.statusCode, 200);
    assert.strictEqual(store.data.messages.length, 2);
    assert.strictEqual(store.data.status, 'New');

    var respondRes = mockRes();
    await respondHandler({ method: 'POST', headers: { authorization: 'Bearer DNT-TEST-KEY' }, body: { complaint_id: 'COMP-1', action: 'reply', text: 'Thanks, looking into it now' } }, respondRes);
    assert.strictEqual(respondRes.statusCode, 200);

    // The real regression: the owner's write must be built from a
    // FRESH read that already includes the patient's reply, not a
    // stale 1-message snapshot.
    assert.strictEqual(store.data.messages.length, 3);
    assert.strictEqual(store.data.messages[0].text, 'Original complaint');
    assert.strictEqual(store.data.messages[1].text, 'Still waiting to hear back');
    assert.strictEqual(store.data.messages[2].text, 'Thanks, looking into it now');
    assert.strictEqual(store.data.status, 'Awaiting Patient');
  });

  await test('patient reply after Resolved reopens to New (state-transition rule)', async () => {
    store.data.status = 'Resolved';
    var threadRes = mockRes();
    await threadHandler({ method: 'POST', headers: {}, body: { token: 'tok-xyz', reply: 'One more thing' } }, threadRes);
    assert.strictEqual(threadRes.statusCode, 200);
    assert.strictEqual(store.data.status, 'New');
  });

  await test("owner resolve with no text appends nothing, sets Resolved", async () => {
    var respondRes = mockRes();
    var before = store.data.messages.length;
    await respondHandler({ method: 'POST', headers: { authorization: 'Bearer DNT-TEST-KEY' }, body: { complaint_id: 'COMP-1', action: 'resolve' } }, respondRes);
    assert.strictEqual(respondRes.statusCode, 200);
    assert.strictEqual(store.data.messages.length, before);
    assert.strictEqual(store.data.status, 'Resolved');
  });

  console.log(passed + ' passed');
}

main();
