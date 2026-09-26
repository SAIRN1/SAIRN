// api/sd-data-customers-batch.test.js
// REQUIREMENT: pushing the customer list must cost a FIXED number of PostgREST
//   round trips, not two per customer -- and it must hand the caller a result,
//   because the loop it replaces was scored DISCARDED by
//   tools/sync_write_result_check.py
//
// Run: node api/sd-data-customers-batch.test.js
//
// ── WHY THIS SUITE EXISTS ──────────────────────────────────────────────────
// stonedesk.html's saveSD3Data() looped the customer array and called `write`
// once per record, from SIXTEEN call sites, several of them render paths whose
// own comment said they must not wait on a round trip. The sd_customers
// resurrection guard (2026-09-24) then added a pre-read to every `write`, so
// each record became TWO trips: 200 customers, 400 trips, on one render.
//
// THE ARM THAT MATTERS IS THE TRIP COUNT. A `write_batch` that quietly looped
// internally would pass every other assertion here -- same responses, same
// refusals, same stored shape -- and fix nothing. So the calls are counted.
//
// THE SECOND IS THE REFUSAL. The batch must not silently drop the records it
// declines to write: a batch that reported `ok` while omitting deleted ids
// would be the same silence as the discarded loop, one level up.

const assert = require('assert');

function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}
function mockReq(action, payload) {
  return {
    method: 'POST',
    headers: { authorization: 'Bearer SD-TEST-KEY', 'x-sd-auth': 'tok' },
    body: { action: action, resource: 'sd_customers', payload: payload || {} }
  };
}

let passed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

function loadHandler(opts) {
  opts = opts || {};
  const calls = [];
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: 'test-hash',
                 trial_ends_at: null, stripe_subscription_id: null };
      }
    }
  };
  const realAuth = require('./_lib/auth');
  delete require.cache[require.resolve('./_lib/auth')];
  require.cache[require.resolve('./_lib/auth')] = {
    exports: Object.assign({}, realAuth, {
      tokenFromRequest: function () { return 'tok'; },
      verifySessionToken: function () {
        return opts.noSession ? null : { employee_id: 'emp-1', role: opts.role || 'owner' };
      }
    })
  };
  global.fetch = async function (url, init) {
    const method = (init && init.method) || 'GET';
    calls.push({ url: String(url), method: method, body: init && init.body });
    if (opts.throwOn && String(url).indexOf(opts.throwOn) !== -1) {
      throw new Error('simulated transport failure');
    }
    if (method === 'GET') {
      const st = opts.readStatus || 200;
      return { ok: st === 200, status: st, json: async () => (opts.rows || []) };
    }
    const st = opts.writeStatus || 201;
    return { ok: st < 300, status: st, json: async () => (st < 300 ? [] : { message: 'upstream' }) };
  };
  delete require.cache[require.resolve('./sd-data.js')];
  return { handler: require('./sd-data.js'), calls: calls };
}

function customers(n) {
  const out = [];
  for (let i = 1; i <= n; i++) out.push({ id: 'C' + i, name: 'Customer ' + i });
  return out;
}

async function main() {
  console.log('sd_customers write_batch -- one call for the whole list\n');

  await test('THE ARM THAT MATTERS: 50 customers cost TWO PostgREST trips, not 100',
    async () => {
      const { handler, calls } = loadHandler({});
      const res = mockRes();
      await handler(mockReq('write_batch', { records: customers(50) }), res);
      assert.strictEqual(res.body.ok, true, JSON.stringify(res.body));
      const rest = calls.filter(c => c.url.indexOf('sd_customers') !== -1);
      assert.strictEqual(rest.length, 2,
        'expected 1 pre-read + 1 upsert, got ' + rest.length
        + ' -- a write_batch that loops internally fixes nothing');
      assert.strictEqual(rest.filter(c => c.method === 'GET').length, 1);
      assert.strictEqual(rest.filter(c => c.method === 'POST').length, 1);
    });

  await test('...and the count does NOT grow with the list -- 5 and 200 cost the same',
    async () => {
      const counts = [];
      for (const n of [5, 200]) {
        const { handler, calls } = loadHandler({});
        await handler(mockReq('write_batch', { records: customers(n) }), mockRes());
        counts.push(calls.filter(c => c.url.indexOf('sd_customers') !== -1).length);
      }
      assert.deepStrictEqual(counts, [2, 2], 'trip count scaled with the list: ' + counts);
    });

  await test('the upsert body is an ARRAY of rows, each with its own customer_id',
    async () => {
      const { handler, calls } = loadHandler({});
      await handler(mockReq('write_batch', { records: customers(3) }), mockRes());
      const post = calls.find(c => c.method === 'POST' && c.url.indexOf('sd_customers') !== -1);
      const body = JSON.parse(post.body);
      assert.ok(Array.isArray(body) && body.length === 3, JSON.stringify(body).slice(0, 200));
      assert.deepStrictEqual(body.map(r => r.customer_id), ['C1', 'C2', 'C3']);
      assert.ok(body.every(r => r.license_hash === 'test-hash' && r.app_id === 'stonedesk'));
    });

  await test('the stored blob strips `id` and keeps everything else -- same rule '
    + 'as the single write, because the read spreads {id: customer_id} + data',
    async () => {
      const { handler, calls } = loadHandler({});
      await handler(mockReq('write_batch',
        { records: [{ id: 'C1', name: 'A', _deleted_at: null, stage: 'quoted' }] }), mockRes());
      const body = JSON.parse(calls.find(c => c.method === 'POST').body);
      assert.strictEqual(body[0].data.id, undefined, 'id was stored inside data');
      assert.strictEqual(body[0].data.name, 'A');
      assert.ok('_deleted_at' in body[0].data,
        '_deleted_at was stripped -- it lives inside data by design and the guard reads it there');
    });

  await test('the pre-read asks for every id at once with in.(...), not one at a time',
    async () => {
      const { handler, calls } = loadHandler({});
      await handler(mockReq('write_batch', { records: customers(3) }), mockRes());
      const get = calls.find(c => c.method === 'GET' && c.url.indexOf('sd_customers') !== -1);
      assert.ok(/customer_id=in\.\(/.test(get.url), get.url);
      ['C1', 'C2', 'C3'].forEach(id => assert.ok(get.url.indexOf(id) !== -1, id + ' missing'));
    });

  await test('THE SECOND ARM THAT MATTERS: a deleted id is REFUSED BY NAME and '
    + 'is not written -- a batch that dropped it silently would be the '
    + 'discarded loop one level up',
    async () => {
      const { handler, calls } = loadHandler({
        rows: [{ customer_id: 'C2', data: { _deleted_at: '2026-09-01T00:00:00Z' } }] });
      const res = mockRes();
      await handler(mockReq('write_batch', { records: customers(3) }), res);
      assert.strictEqual(res.body.written, 2);
      assert.deepStrictEqual(res.body.refused.map(r => r.id), ['C2']);
      assert.strictEqual(res.body.refused[0].code, 'DELETED');
      const body = JSON.parse(calls.find(c => c.method === 'POST').body);
      assert.deepStrictEqual(body.map(r => r.customer_id), ['C1', 'C3'],
        'a deleted customer was resurrected by the batch');
    });

  await test('a batch that is ENTIRELY deleted writes nothing and still reports '
    + 'every refusal -- no POST is made at all',
    async () => {
      const { handler, calls } = loadHandler({
        rows: [{ customer_id: 'C1', data: { _deleted_at: 'x' } }] });
      const res = mockRes();
      await handler(mockReq('write_batch', { records: customers(1) }), res);
      assert.strictEqual(res.body.written, 0);
      assert.strictEqual(res.body.refused.length, 1);
      assert.strictEqual(calls.filter(c => c.method === 'POST'
        && c.url.indexOf('sd_customers') !== -1).length, 0);
    });

  await test('A TRANSPORT FAILURE ON THE PRE-READ WRITES NOTHING -- same '
    + 'fails-closed property the single write has, and for the same reason',
    async () => {
      const { handler, calls } = loadHandler({ throwOn: 'customer_id=in.' });
      const res = mockRes();
      await handler(mockReq('write_batch', { records: customers(3) }), res);
      assert.strictEqual(res.statusCode, 502, JSON.stringify(res.body));
      assert.strictEqual(calls.filter(c => c.method === 'POST'
        && c.url.indexOf('sd_customers') !== -1).length, 0,
        'the batch was written after a pre-read that never answered');
    });

  await test('...but a pre-read that ANSWERED with a refusal falls through and '
    + 'writes, because the store said nothing about a deletion',
    async () => {
      const { handler, calls } = loadHandler({ readStatus: 500 });
      const res = mockRes();
      await handler(mockReq('write_batch', { records: customers(2) }), res);
      assert.strictEqual(res.body.ok, true, JSON.stringify(res.body));
      assert.strictEqual(res.body.written, 2);
      assert.strictEqual(calls.filter(c => c.method === 'POST'
        && c.url.indexOf('sd_customers') !== -1).length, 1);
    });

  await test('an oversized batch is REFUSED, never truncated -- a truncated '
    + 'batch reports success for records that were never sent',
    async () => {
      const res = mockRes();
      await loadHandler({}).handler(mockReq('write_batch', { records: customers(501) }), res);
      assert.strictEqual(res.statusCode, 413);
      assert.strictEqual(res.body.error.code, 'BATCH_TOO_LARGE');
    });

  await test('records with no id are counted and reported, not silently dropped',
    async () => {
      const { handler } = loadHandler({});
      const res = mockRes();
      await handler(mockReq('write_batch',
        { records: [{ id: 'C1' }, { name: 'no id' }, null] }), res);
      assert.strictEqual(res.body.written, 1);
      assert.strictEqual(res.body.skipped_without_id, 2);
    });

  await test('a non-array payload is refused rather than coerced', async () => {
    for (const p of [{}, { records: 'C1' }, { records: null }]) {
      const res = mockRes();
      await loadHandler({}).handler(mockReq('write_batch', p), res);
      assert.strictEqual(res.statusCode, 400, JSON.stringify(p));
      assert.strictEqual(res.body.error.code, 'NO_RECORDS');
    }
  });

  await test('an empty batch is a 200 that wrote nothing, not an error',
    async () => {
      const { handler, calls } = loadHandler({});
      const res = mockRes();
      await handler(mockReq('write_batch', { records: [] }), res);
      assert.strictEqual(res.body.ok, true);
      assert.strictEqual(res.body.written, 0);
      assert.strictEqual(calls.filter(c => c.url.indexOf('sd_customers') !== -1).length, 0);
    });

  await test('write_batch needs a session, exactly like write', async () => {
    const res = mockRes();
    await loadHandler({ noSession: true })
      .handler(mockReq('write_batch', { records: customers(1) }), res);
    assert.strictEqual(res.statusCode, 401);
  });

  await test('IS IT REACHABLE: write_batch is declared in the resource registry, '
    + 'or the dispatcher answers 400 before the branch is ever entered',
    async () => {
      const reg = require('./_resources/stonedesk');
      assert.ok((reg.extraActions.sd_customers || []).indexOf('write_batch') !== -1,
        'write_batch is implemented and undeclared -- that is how tombstones '
        + 'shipped dead and a live probe caught it');
    });

  console.log('\n' + (process.exitCode
    ? 'FAILURES ABOVE'
    : 'ALL ' + passed + ' CUSTOMERS-BATCH ASSERTIONS PASS'));
}

main();
