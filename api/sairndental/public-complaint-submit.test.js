// api/sairndental/public-complaint-submit.test.js
// Plain node:assert tests -- no test framework, matching
// api/sairndental/public-book.test.js's existing convention.
// Run: node api/sairndental/public-complaint-submit.test.js
//
// Covers only the pre-network-call validation paths (required fields,
// message length cap, rate limiting). The full
// resolveSlug -> Supabase insert flow needs a real Supabase
// environment and is covered by Task 10's live verification instead.

const assert = require('assert');

function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (code) { res.statusCode = code; return res; };
  res.json = function (payload) { res.body = payload; return res; };
  res.setHeader = function (key, value) { return res; };
  res.end = function () { return res; };
  return res;
}
function mockReq(body) {
  return { method: 'POST', headers: {}, body: body };
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
  console.log('api/sairndental/public-complaint-submit.js');

  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  delete require.cache[require.resolve('../_lib/dental-public')];
  require.cache[require.resolve('../_lib/dental-public')] = {
    exports: {
      resolveSlug: function () { throw new Error('resolveSlug should not be called in validation tests'); },
      checkAndIncrementRateLimit: async function () { return { allowed: true }; }
    }
  };
  global.fetch = function () { throw new Error('fetch should never be called for a request that fails validation'); };
  delete require.cache[require.resolve('./public-complaint-submit.js')];
  var handler = require('./public-complaint-submit.js');

  await test('missing slug -> 400, never calls fetch', async () => {
    var res = mockRes();
    await handler(mockReq({ message: 'Hello' }), res);
    assert.strictEqual(res.statusCode, 400);
  });

  await test('missing message -> 400, never calls fetch', async () => {
    var res = mockRes();
    await handler(mockReq({ slug: 'test-practice' }), res);
    assert.strictEqual(res.statusCode, 400);
  });

  await test('message over 4000 chars -> 400 MESSAGE_TOO_LONG, never calls fetch', async () => {
    var res = mockRes();
    await handler(mockReq({ slug: 'test-practice', message: 'x'.repeat(4001) }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'MESSAGE_TOO_LONG');
  });

  await test('rate-limited -> 429, never calls fetch', async () => {
    require.cache[require.resolve('../_lib/dental-public')].exports.checkAndIncrementRateLimit = async function () { return { allowed: false }; };
    delete require.cache[require.resolve('./public-complaint-submit.js')];
    var rlHandler = require('./public-complaint-submit.js');
    var res = mockRes();
    await rlHandler(mockReq({ slug: 'test-practice', message: 'Hello' }), res);
    assert.strictEqual(res.statusCode, 429);
    assert.strictEqual(res.body.error.code, 'RATE_LIMITED');
  });

  await test('field-whitelist regression (design spec §1/§7): happy-path insert payload.data has exactly {id, patient_name, status, messages, created_at}, nothing else', async () => {
    var capturedBody = null;
    delete require.cache[require.resolve('../_lib/dental-public')];
    require.cache[require.resolve('../_lib/dental-public')] = {
      exports: {
        resolveSlug: async function () { return 'hash-abc'; },
        checkAndIncrementRateLimit: async function () { return { allowed: true }; }
      }
    };
    global.fetch = async function (url, opts) {
      // The handler now makes a DUPLICATE LOOKUP before the insert (2026-09-13),
      // which is a GET with no body -- this mock previously did
      // JSON.parse(opts.body) on every call and threw on it. Answering the
      // lookup with "no duplicate" keeps this arm asserting exactly what it
      // always asserted: the shape of the insert payload.
      if (String(url).indexOf('submission_key=eq.') >= 0) {
        return { ok: true, status: 200, json: async function () { return []; },
                 text: async function () { return ''; } };
      }
      capturedBody = JSON.parse(opts.body);
      return { ok: true, json: async function () { return [capturedBody]; }, text: async function () { return ''; } };
    };
    delete require.cache[require.resolve('./public-complaint-submit.js')];
    var handler = require('./public-complaint-submit.js');
    var res = mockRes();
    await handler(mockReq({ slug: 'test-practice', message: 'Front desk was rude', patient_name: 'Jane' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.ok(res.body.token, 'expected a token in the response');
    assert.ok(capturedBody, 'expected fetch to have been called with a body');
    var dataKeys = Object.keys(capturedBody.data).sort();
    assert.deepStrictEqual(dataKeys, ['created_at', 'id', 'messages', 'patient_name', 'status']);
    assert.strictEqual(capturedBody.data.status, 'New');
    assert.strictEqual(capturedBody.data.messages.length, 1);
    assert.strictEqual(capturedBody.data.messages[0].from, 'patient');
    assert.strictEqual(capturedBody.data.messages[0].text, 'Front desk was rude');
  });

  // ── IDEMPOTENCE ON A RETRIED SUBMISSION (2026-09-13) ──────────────────
  // A public form is retried by a double-click and by a browser resubmitting
  // on a slow response. Before this, each retry filed a SECOND complaint with
  // the same first message, and the practice replied twice to one grievance.
  //
  // Every arm drives the REAL handler with a fetch that records the calls, so
  // it asserts what the endpoint actually does rather than what it intends.
  // `insert` is the fourth argument and it exists because THIS HARNESS COULD
  // EMIT A RESPONSE PAIR NO DATABASE CAN PRODUCE (found 2026-09-17). It
  // answered the lookup with whatever dupStatus said and then answered the
  // INSERT with 201 unconditionally -- so the "the column is not there yet"
  // test drove a world where PostgREST rejects submission_key in a filter and
  // accepts it in an insert body. A column is present or it is not; it cannot
  // be both, and the arm that rested on it asserted something false.
  function withFetch(calls, dupRows, dupStatus, insert) {
    global.fetch = async function (url, opts) {
      calls.push({ url: String(url), method: (opts && opts.method) || 'GET',
                   body: opts && opts.body ? JSON.parse(opts.body) : null });
      if (String(url).indexOf('submission_key=eq.') >= 0) {
        if (dupStatus && dupStatus !== 200) {
          return { ok: false, status: dupStatus,
                   json: async function () { return null; },
                   text: async function () { return 'boom'; } };
        }
        return { ok: true, status: 200, json: async function () { return dupRows || []; },
                 text: async function () { return ''; } };
      }
      if (insert) {
        return { ok: false, status: insert.status,
                 json: async function () { return null; },
                 text: async function () { return insert.text; } };
      }
      return { ok: true, status: 201,
               json: async function () { return [opts && opts.body ? JSON.parse(opts.body) : {}]; },
               text: async function () { return ''; } };
    };
    delete require.cache[require.resolve('./public-complaint-submit.js')];
    return require('./public-complaint-submit.js');
  }

  // The two real PostgREST bodies, written out rather than paraphrased: the
  // whole point of the split below is that one string CONTAINS the other.
  var PGRST_NO_COLUMN =
    '{"code":"42703","message":"column \\"submission_key\\" of relation ' +
    '\\"dnt_complaints\\" does not exist"}';
  var PGRST_NO_TABLE =
    '{"code":"42P01","message":"relation \\"public.dnt_complaints\\" does not exist"}';

  await test('the duplicate check runs BEFORE the insert, and against the table', async () => {
    var calls = [];
    var h = withFetch(calls, []);
    var res = mockRes();
    await h(mockReq({ slug: 'p', message: 'Front desk was rude', patient_name: 'Jane' }), res);
    assert.ok(calls.length >= 2, 'expected a lookup then an insert, got ' + calls.length);
    assert.ok(calls[0].url.indexOf('submission_key=eq.') >= 0,
      'the FIRST call must be the duplicate lookup: checking after inserting checks nothing');
    assert.strictEqual(calls[0].method, 'GET', 'the check must be a read against the table');
    assert.strictEqual(calls[1].method, 'POST');
  });

  await test('a RETRY inside the window returns the ORIGINAL complaint, and writes nothing',
    async () => {
      var calls = [];
      var h = withFetch(calls, [{ complaint_id: 'COMP-1', access_token: 'tok-1' }]);
      var res = mockRes();
      await h(mockReq({ slug: 'p', message: 'Front desk was rude', patient_name: 'Jane' }), res);
      assert.strictEqual(res.statusCode, 200);
      assert.strictEqual(res.body.complaint_id, 'COMP-1',
        'a patient who clicked twice must see THEIR complaint, not a second one');
      assert.strictEqual(res.body.duplicate_of_recent, true);
      assert.strictEqual(calls.filter(function (c) { return c.method === 'POST'; }).length, 0,
        'THIS IS THE BUG: a retry must not insert');
    });

  await test('CONTROL: with NO duplicate on record it still inserts -- or the arm above '
    + 'would pass on a handler that never writes at all', async () => {
      var calls = [];
      var h = withFetch(calls, []);
      var res = mockRes();
      await h(mockReq({ slug: 'p', message: 'Different message', patient_name: 'Jane' }), res);
      assert.strictEqual(calls.filter(function (c) { return c.method === 'POST'; }).length, 1);
    });

  await test('the key is the BUSINESS EVENT -- a different message is a different key',
    async () => {
      var a = [], b = [];
      var h1 = withFetch(a, []);
      await h1(mockReq({ slug: 'p', message: 'one', patient_name: 'Jane' }), mockRes());
      var h2 = withFetch(b, []);
      await h2(mockReq({ slug: 'p', message: 'two', patient_name: 'Jane' }), mockRes());
      var k1 = a[0].url.split('submission_key=eq.')[1].split('&')[0];
      var k2 = b[0].url.split('submission_key=eq.')[1].split('&')[0];
      assert.notStrictEqual(k1, k2, 'two different complaints must not share a key');
      assert.strictEqual(k1.length, 64, 'expected a sha256 hex digest');
    });

  await test('the same submission produces the SAME key -- or a retry never matches',
    async () => {
      var a = [], b = [];
      var h1 = withFetch(a, []);
      await h1(mockReq({ slug: 'p', message: 'same', patient_name: 'Jane' }), mockRes());
      var h2 = withFetch(b, []);
      await h2(mockReq({ slug: 'p', message: 'same', patient_name: 'Jane' }), mockRes());
      assert.strictEqual(a[0].url.split('submission_key=eq.')[1].split('&')[0],
                         b[0].url.split('submission_key=eq.')[1].split('&')[0]);
    });

  await test('the lookup is BOUNDED IN TIME -- the same sentence a week later is a new complaint',
    async () => {
      var calls = [];
      var h = withFetch(calls, []);
      await h(mockReq({ slug: 'p', message: 'bounded', patient_name: 'Jane' }), mockRes());
      assert.ok(calls[0].url.indexOf('updated_at=gte.') >= 0,
        'without a window, a complaint filed once could never be filed again');
    });

  await test('a FAILED duplicate check REFUSES rather than filing unchecked', async () => {
    var calls = [];
    var h = withFetch(calls, null, 500);
    var res = mockRes();
    await h(mockReq({ slug: 'p', message: 'server down', patient_name: 'Jane' }), res);
    assert.strictEqual(res.statusCode, 503,
      'a failed check is not the same answer as "no duplicate"');
    assert.strictEqual(calls.filter(function (c) { return c.method === 'POST'; }).length, 0);
  });

  await test('a 400 from the lookup FALLS THROUGH to the insert rather than refusing there',
    async () => {
      var calls = [];
      var h = withFetch(calls, null, 400, { status: 400, text: PGRST_NO_COLUMN });
      var res = mockRes();
      await h(mockReq({ slug: 'p', message: 'no column yet', patient_name: 'Jane' }), res);
      assert.strictEqual(calls.filter(function (c) { return c.method === 'POST'; }).length, 1,
        'a 400 on the LOOKUP must not be treated as a failed check -- it reaches the insert');
    });

  // ── WHAT THE ARM ABOVE USED TO CLAIM, AND WHY IT IS SPLIT IN TWO ─────────
  // It was one arm named "...and it proceeds", asserting "before the migration
  // runs, the endpoint must still accept complaints". Reaching the insert is
  // true. Accepting the complaint is NOT, and was never driven: the harness
  // returned 201 for the insert no matter what, so the arm stopped exactly
  // where its own claim became false. The real database answers the insert
  // with 42703 too, because it is the same missing column.
  await test('...and the request then FAILS, because the insert carries the same missing column',
    async () => {
      var calls = [];
      var h = withFetch(calls, null, 400, { status: 400, text: PGRST_NO_COLUMN });
      var res = mockRes();
      await h(mockReq({ slug: 'p', message: 'no column yet', patient_name: 'Jane' }), res);
      assert.strictEqual(res.statusCode, 503,
        'before the migration runs this endpoint refuses every complaint -- the public form is DOWN, ' +
        'and a test that says otherwise is worse than no test');
      assert.strictEqual(res.body.error.code, 'NOT_PROVISIONED');
    });

  await test('the missing-COLUMN message names the column and the migration, not the table',
    async () => {
      var h = withFetch([], null, 400, { status: 400, text: PGRST_NO_COLUMN });
      var res = mockRes();
      await h(mockReq({ slug: 'p', message: 'x', patient_name: 'Jane' }), res);
      var m = res.body.error.message;
      assert.ok(/column is missing/i.test(m) && /sairndental_complaint_idempotency/.test(m),
        'whoever reads the support ticket must be sent at the ALTER TABLE, not at the schema file');
      assert.ok(!/tables are not set up yet/i.test(m),
        'the table has existed for months -- saying it does not is a wrong answer, not a vague one');
    });

  await test('a missing TABLE still says the table is missing -- the two are not merged',
    async () => {
      var h = withFetch([], null, 200, { status: 400, text: PGRST_NO_TABLE });
      var res = mockRes();
      await h(mockReq({ slug: 'p', message: 'x', patient_name: 'Jane' }), res);
      assert.strictEqual(res.statusCode, 503);
      assert.ok(/tables are not set up yet/i.test(res.body.error.message),
        'the column branch must not swallow the table case: its text contains the table case text, ' +
        'so only the ORDER of the two tests keeps this reachable');
    });

  await test('the insert carries the key, so the NEXT retry can find it', async () => {
    var calls = [];
    var h = withFetch(calls, []);
    await h(mockReq({ slug: 'p', message: 'carries', patient_name: 'Jane' }), mockRes());
    var post = calls.filter(function (c) { return c.method === 'POST'; })[0];
    assert.ok(post.body.submission_key, 'a key checked but never stored guards nothing');
    assert.strictEqual(post.body.submission_key,
                       calls[0].url.split('submission_key=eq.')[1].split('&')[0],
                       'the key stored must be the key looked up');
  });

  console.log(passed + ' passed');
}

main();
