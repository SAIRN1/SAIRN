// api/sd-data-slab-reserve.test.js
// Plain node:assert tests. Run: node api/sd-data-slab-reserve.test.js
//
// THE DOUBLE-SALE. Until 2026-09-02, three places in stonedesk.html did
// `rs.status='reserved'; rs.reservedFor=customer;` with no check of what was
// already there, and the 'write' action is a blind upsert
// (resolution=merge-duplicates). So the second salesperson to save silently
// took a slab already promised to someone else and destroyed `reservedFor` --
// the only record of who had it. Both quotes then displayed the same physical
// slab as theirs, and on the POS path the invoice, with its deposit, was
// written before the slab was touched at all.
//
// Every competing product builds its yard workflow around preventing this;
// iBlocky puts "niente più doppie vendite" second on its own homepage.
//
// A client-side check could not have fixed it: sdSlabs is a localStorage array
// loaded once per session, so one device cannot see another device's
// reservation. These assertions are therefore about the SERVER, which is the
// only place both requests arrive.

const assert = require('assert');

function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}
function mockReq(payload) {
  return {
    method: 'POST',
    headers: { authorization: 'Bearer SD-TEST-KEY' },
    body: { action: 'reserve', resource: 'slabs', payload: payload }
  };
}

let passed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

// A PostgREST stand-in. `row` is what the initial SELECT returns (null = the
// slab has never been synced). `patchReturns` is what the conditional PATCH
// matches -- an empty array is a lost race, which is the case that matters.
function stubBackend(opts) {
  const calls = [];
  global.fetch = async (url, init) => {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    calls.push({ url: u, method: method, headers: (init && init.headers) || {}, body: init && init.body });
    if (method === 'GET') {
      return { ok: true, status: 200, json: async () => (opts.row ? [{ data: opts.row }] : []) };
    }
    if (method === 'POST') {
      if (opts.insertConflict) return { ok: false, status: 409, json: async () => ({ code: '23505' }) };
      return { ok: true, status: 201, json: async () => [{ data: JSON.parse(init.body).data }] };
    }
    if (method === 'PATCH') {
      const returned = opts.patchReturns === undefined
        ? [{ data: JSON.parse(init.body).data }]
        : opts.patchReturns;
      return { ok: true, status: 200, json: async () => returned };
    }
    throw new Error('unexpected method ' + method);
  };
  return calls;
}

function loadHandler() {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: 'test-hash', trial_ends_at: null, stripe_subscription_id: null };
      }
    }
  };
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

async function main() {
  console.log('api/sd-data.js -- slabs/reserve: compare-and-swap, refuses the double-sale');
  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  // ---- inputs -----------------------------------------------------------
  await test('no slab id -> 400, never touches the network', async () => {
    const calls = stubBackend({ row: null });
    const res = mockRes();
    await loadHandler()(mockReq({ reservedFor: 'Ruiz' }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'NO_SLAB_ID');
    assert.strictEqual(calls.length, 0);
  });

  await test('a reservation with nobody to hold it -> 400', async () => {
    const calls = stubBackend({ row: null });
    const res = mockRes();
    await loadHandler()(mockReq({ id: 'S1', reservedFor: '   ' }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'NO_HOLDER');
    assert.strictEqual(calls.length, 0);
  });

  // ---- the refusals that ARE the feature --------------------------------
  await test('THE DOUBLE-SALE: a slab held by another customer -> 409, no write', async () => {
    const calls = stubBackend({ row: { id: 'S1', status: 'reserved', reservedFor: 'Ruiz kitchen' } });
    const res = mockRes();
    await loadHandler()(mockReq({ id: 'S1', reservedFor: 'Chen bath' }), res);
    assert.strictEqual(res.statusCode, 409);
    assert.strictEqual(res.body.error.code, 'ALREADY_RESERVED');
    assert.ok(!calls.some(c => c.method === 'PATCH' || c.method === 'POST'),
      'it refused and wrote anyway');
  });

  await test('...and it NAMES the holder, so nobody has to go hunting', async () => {
    stubBackend({ row: { id: 'S1', status: 'reserved', reservedFor: 'Ruiz kitchen' } });
    const res = mockRes();
    await loadHandler()(mockReq({ id: 'S1', reservedFor: 'Chen bath' }), res);
    assert.match(res.body.error.message, /Ruiz kitchen/);
    assert.strictEqual(res.body.error.reservedFor, 'Ruiz kitchen');
  });

  await test('a consumed slab -> 409 SLAB_CONSUMED, a different answer from "taken"', async () => {
    stubBackend({ row: { id: 'S1', status: 'consumed', reservedFor: 'Ruiz' } });
    const res = mockRes();
    await loadHandler()(mockReq({ id: 'S1', reservedFor: 'Chen' }), res);
    assert.strictEqual(res.statusCode, 409);
    assert.strictEqual(res.body.error.code, 'SLAB_CONSUMED');
  });

  await test('LOST RACE: the row moved between read and write -> 409, not an overwrite', async () => {
    stubBackend({ row: { id: 'S1', status: 'in-stock' }, patchReturns: [] });
    const res = mockRes();
    await loadHandler()(mockReq({ id: 'S1', reservedFor: 'Chen' }), res);
    assert.strictEqual(res.statusCode, 409);
    assert.strictEqual(res.body.error.code, 'RESERVATION_RACE');
  });

  // ---- the happy paths --------------------------------------------------
  await test('an in-stock slab is reserved, and the write CARRIES THE COMPARE', async () => {
    const calls = stubBackend({ row: { id: 'S1', status: 'in-stock' } });
    const res = mockRes();
    await loadHandler()(mockReq({ id: 'S1', reservedFor: 'Chen bath' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.data.status, 'reserved');
    assert.strictEqual(res.body.data.reservedFor, 'Chen bath');
    const patch = calls.find(c => c.method === 'PATCH');
    assert.ok(patch, 'no conditional write was issued');
    // Without these two filters the update is just the blind write again.
    assert.ok(/data-%3E%3Estatus=eq\.|data->>status=eq\./.test(decodeURI(patch.url)) ||
              patch.url.includes('data->>status=eq.'),
      'the write did not assert the status it read: ' + patch.url);
    assert.ok(patch.url.includes('data->>reservedFor=is.null'),
      'the write did not assert reservedFor was still empty: ' + patch.url);
  });

  await test('re-reserving for the SAME customer is allowed, not a self-conflict', async () => {
    stubBackend({ row: { id: 'S1', status: 'reserved', reservedFor: 'Chen bath' } });
    const res = mockRes();
    await loadHandler()(mockReq({ id: 'S1', reservedFor: 'Chen bath' }), res);
    assert.strictEqual(res.statusCode, 200);
  });

  await test('a customer name with a comma and quotes is QUOTED in the filter', async () => {
    // PostgREST filter values are comma and parenthesis delimited. Real shop
    // names contain both, and an unquoted one would silently change the
    // predicate -- i.e. compare against the wrong thing and pass.
    const calls = stubBackend({ row: { id: 'S1', status: 'reserved', reservedFor: 'Smith, Jones & Co (Ohio)' } });
    const res = mockRes();
    await loadHandler()(mockReq({ id: 'S1', reservedFor: 'Smith, Jones & Co (Ohio)' }), res);
    assert.strictEqual(res.statusCode, 200);
    const patch = calls.find(c => c.method === 'PATCH');
    const decoded = decodeURIComponent(patch.url);
    assert.ok(decoded.includes('data->>reservedFor=eq."Smith, Jones & Co (Ohio)"'),
      'the holder name was not quoted in the filter: ' + decoded);
  });

  // ---- the never-synced slab --------------------------------------------
  await test('a slab absent server-side is INSERTED, and reports created:true', async () => {
    const calls = stubBackend({ row: null });
    const res = mockRes();
    await loadHandler()(mockReq({ id: 'S9', reservedFor: 'Chen' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.created, true);
    assert.strictEqual(res.body.data.status, 'reserved');
  });

  await test('...and that insert is PLAIN, never merge-duplicates', async () => {
    // An upsert here would silently clobber a row inserted a millisecond
    // earlier by another device -- the same bug, moved.
    const calls = stubBackend({ row: null });
    const res = mockRes();
    await loadHandler()(mockReq({ id: 'S9', reservedFor: 'Chen' }), res);
    const post = calls.find(c => c.method === 'POST');
    assert.ok(post, 'no insert issued');
    assert.ok(!/merge-duplicates/.test(String(post.headers.Prefer || '')),
      'the insert was an upsert: ' + post.headers.Prefer);
    assert.ok(!/on_conflict/.test(post.url), 'the insert declared on_conflict: ' + post.url);
  });

  await test('two devices racing on a never-synced slab: the loser gets 409', async () => {
    stubBackend({ row: null, insertConflict: true });
    const res = mockRes();
    await loadHandler()(mockReq({ id: 'S9', reservedFor: 'Chen' }), res);
    assert.strictEqual(res.statusCode, 409);
    assert.strictEqual(res.body.error.code, 'ALREADY_RESERVED');
  });

  console.log('\n' + (process.exitCode ? 'FAILURES ABOVE' : 'ALL ' + passed + ' SLAB-RESERVE ASSERTIONS PASS'));
}

main();
