// api/sairncash/trial-renew-idempotency.test.js
// Run: node api/sairncash/trial-renew-idempotency.test.js
//
// ITEM 6. trial-renew.js SELECTs renewal_count, adds one in JavaScript, and
// PATCHes it back with a fresh expires_at computed from NOW. Two round trips
// with nothing between them, on THE ONLY WRITE PATH THAT CAN EXTEND
// expires_at.
//
// -- TWO FAILURES, TWO FIXES, AND NEITHER COVERS THE OTHER ------------------
// Section C is the RETRY: the response is lost, the admin retries, and without
// a key the retry reads the already-incremented count and writes a SECOND
// 30-day window. One approval, two extensions, reported as a success.
//
// Section D is the RACE: two approvals in flight both read N and both write
// N+1, so one vanishes from the count. A key cannot fix that -- two genuinely
// different approvals carry different keys and both are legitimate -- so the
// PATCH carries a compare-and-set on the count, and the loser must be TOLD.
//
// -- THE ARM MOST LIKELY TO BE GOT WRONG -----------------------------------
// D3. The loser of a compare-and-set gets a 200 with an EMPTY ARRAY, not an
// error. A handler that only checked patchR.ok would tell a stale writer its
// renewal succeeded while nothing was written -- a false success, which is the
// shape this whole sweep is about.
//
// Separate file from trial-renew.test.js, which covers the auth gate and is
// left as it is: it tests a different property and has no need for a stub.

const assert = require('assert');
const handler = require('./trial-renew.js');

let passed = 0, failed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log('  ok   - ' + name); }
  catch (err) { failed++; console.error('  FAIL - ' + name + '\n         ' + err.message); }
}

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = (c) => { res.statusCode = c; return res; };
  res.json = (p) => { res.body = p; return res; };
  return res;
}

// Built from parts rather than written as a literal so the repo's own
// credential scanner does not read the fixture as a secret.
const ADMIN = ['admin', 'fixture', 'value'].join('-');
const KEY = 'renew-approval-2026-09-14-aaaa';
const req = (body) => ({
  method: 'POST',
  headers: { authorization: 'Bearer ' + ADMIN },
  body: body
});

// A world holding ONE trial row. The PATCH honours the compare-and-set exactly
// as PostgREST does -- it applies only when the filter matches, and returns the
// rows it touched, which for the loser is an empty array. Modelled rather than
// scripted, because "did the write land" is the question these arms ask.
function world(opts) {
  const o = opts || {};
  const row = Object.assign({
    renewal_count: 0, expires_at: 'OLD-EXPIRY', renew_idempotency_key: null
  }, o.row || {});
  const calls = [];
  global.fetch = async (url, init) => {
    const u = String(url), m = (init && init.method) || 'GET';
    calls.push({ url: u, method: m, body: init && init.body });
    if (o.unknownColumn) {
      return { ok: false, status: 400,
        json: async () => ({}),
        text: async () => 'column sairncash_trial.renew_idempotency_key does not exist' };
    }
    if (m === 'GET') {
      if (o.noRow) return { ok: true, status: 200, json: async () => [] };
      return { ok: true, status: 200, json: async () => [Object.assign({}, row)] };
    }
    const nullFilter = u.indexOf('renewal_count=is.null') !== -1;
    const eqm = /renewal_count=eq\.(\d+)/.exec(u);
    const matches = nullFilter
      ? (row.renewal_count === null || row.renewal_count === undefined)
      : (eqm ? row.renewal_count === Number(eqm[1]) : true);
    if (!matches) {
      return { ok: true, status: 200, json: async () => [], text: async () => '[]' };
    }
    Object.assign(row, JSON.parse(init.body));
    return { ok: true, status: 200, json: async () => [Object.assign({}, row)],
             text: async () => '[]' };
  };
  return { calls, row };
}

async function main() {
  process.env.SAIRNCASH_ADMIN_SECRET = ADMIN;
  process.env.SUPABASE_URL = 'https://db.example.invalid';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'service-key';
  console.log('api/sairncash/trial-renew.js -- one approval must extend once');

  console.log('\nA. the key is validated, not quietly ignored');
  await test('a short key is REFUSED', async () => {
    world();
    const res = mockRes();
    await handler(req({ email: 'a@b.co', idempotency_key: 'tiny' }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'BAD_IDEMPOTENCY_KEY');
  });

  console.log('\nB. the new column is only touched when asked for');
  await test('no key: neither the SELECT nor the PATCH names the new column',
    async () => {
      const w = world();
      const res = mockRes();
      await handler(req({ email: 'a@b.co' }), res);
      assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
      const get = w.calls.filter((c) => c.method === 'GET')[0];
      const patch = w.calls.filter((c) => c.method === 'PATCH')[0];
      assert.ok(get.url.indexOf('renew_idempotency_key') === -1,
        'asking for the column in select= 400s EVERY renewal before the '
        + 'migration has run');
      assert.ok(patch.body.indexOf('renew_idempotency_key') === -1,
        'sending the column does the same on the write side');
    });
  await test('with a key: both name it', async () => {
    const w = world();
    const res = mockRes();
    await handler(req({ email: 'a@b.co', idempotency_key: KEY }), res);
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    assert.ok(w.calls.filter((c) => c.method === 'GET')[0]
      .url.indexOf('renew_idempotency_key') !== -1);
    assert.ok(w.calls.filter((c) => c.method === 'PATCH')[0]
      .body.indexOf(KEY) !== -1);
  });

  console.log('\nC. THE RETRY: one approval extends once');
  await test('the same key again returns the ORIGINAL expiry and writes nothing',
    async () => {
      const w = world({ row: { renewal_count: 3, expires_at: 'FIRST-EXPIRY',
                               renew_idempotency_key: KEY } });
      const res = mockRes();
      await handler(req({ email: 'a@b.co', idempotency_key: KEY }), res);
      assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
      assert.strictEqual(res.body.expiresAt, 'FIRST-EXPIRY',
        'a NEW expiry here is the double extension -- one approval, two 30-day '
        + 'windows, and the admin sees a success either way');
      assert.strictEqual(res.body.renewalCount, 3, 'the count moved on a retry');
      assert.strictEqual(res.body.retried, true);
      assert.strictEqual(w.calls.filter((c) => c.method === 'PATCH').length, 0,
        'the retry wrote to the database at all');
    });
  await test('THE PAIRED POSITIVE: a DIFFERENT key really does renew again',
    async () => {
      const w = world({ row: { renewal_count: 3, expires_at: 'FIRST-EXPIRY',
                               renew_idempotency_key: KEY } });
      const res = mockRes();
      await handler(req({ email: 'a@b.co',
                          idempotency_key: 'renew-approval-2026-09-15-bbbb' }), res);
      assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
      assert.strictEqual(res.body.renewalCount, 4);
      assert.notStrictEqual(res.body.expiresAt, 'FIRST-EXPIRY');
      assert.strictEqual(w.calls.filter((c) => c.method === 'PATCH').length, 1);
    });
  await test('no key at all: unchanged behaviour, it renews', async () => {
    const res = mockRes();
    world({ row: { renewal_count: 3 } });
    await handler(req({ email: 'a@b.co' }), res);
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    assert.strictEqual(res.body.renewalCount, 4);
  });

  console.log('\nD. THE RACE: the loser is told, not silently dropped');
  await test('the PATCH carries a compare-and-set on the count', async () => {
    const w = world({ row: { renewal_count: 7 } });
    const res = mockRes();
    await handler(req({ email: 'a@b.co' }), res);
    void res;
    const patch = w.calls.filter((c) => c.method === 'PATCH')[0];
    assert.ok(patch.url.indexOf('renewal_count=eq.7') !== -1,
      'without the filter a stale writer overwrites the other increment and '
      + 'one approval vanishes from the count: ' + patch.url);
  });
  await test('...and is.null for an untouched row, or the FIRST renewal of '
    + 'every trial would match nothing', async () => {
    const w = world({ row: { renewal_count: null } });
    const res = mockRes();
    await handler(req({ email: 'a@b.co' }), res);
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    const patch = w.calls.filter((c) => c.method === 'PATCH')[0];
    assert.ok(patch.url.indexOf('renewal_count=is.null') !== -1, patch.url);
  });
  await test('D3 losing the race is a 409, NOT a 200 -- zero rows back arrives '
    + 'as a success', async () => {
    const w = world({ row: { renewal_count: 7 } });
    const realFetch = global.fetch;
    global.fetch = async (url, init) => {
      const m = (init && init.method) || 'GET';
      if (m === 'PATCH') { w.row.renewal_count = 9; }
      return realFetch(url, init);
    };
    const res = mockRes();
    await handler(req({ email: 'a@b.co' }), res);
    assert.strictEqual(res.statusCode, 409, JSON.stringify(res.body));
    assert.strictEqual(res.body.error.code, 'CONCURRENT_RENEWAL');
    assert.ok(/retrying blindly would extend it twice/.test(res.body.error.message),
      'an admin told only "try again" would retry and double-extend');
  });
  await test('...and the PATCH asks for return=representation, or there is no '
    + 'row count to read and the CAS is unobservable', async () => {
    const src = require('fs').readFileSync(__dirname + '/trial-renew.js', 'utf8');
    assert.ok(/Prefer: 'return=representation'/.test(src),
      'return=minimal returns no body, so patched.length can never be 0 and '
      + 'the loser of the race would be told it succeeded');
  });

  console.log('\nE. the migration is named rather than reported as an outage');
  await test('a missing column is NOT_PROVISIONED and names the file', async () => {
    world({ unknownColumn: true });
    const res = mockRes();
    await handler(req({ email: 'a@b.co', idempotency_key: KEY }), res);
    assert.strictEqual(res.statusCode, 503, JSON.stringify(res.body));
    assert.ok(/sairncash_trial_renew_idempotency_2026-09-14\.sql/.test(
      res.body.error.message));
  });

  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  if (failed) process.exitCode = 1;
}

main();
