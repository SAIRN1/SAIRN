// api/sairncash/trial-start.test.js
// Run: node api/sairncash/trial-start.test.js
//
// ITEM 6. The ROW could never duplicate -- `email` is UNIQUE and the 409 was
// handled -- but the REQUEST was not idempotent: trial_token is minted here and
// returned only on the 200 path, so a lost response left the trial existing on
// the server and unreachable by the person it belonged to.
//
// ── THE ARM THAT MATTERS MOST IS THE SECURITY ONE ──────────────────────────
// The obvious fix is "return the existing token on 409", which is what
// api/sairndental/public-complaint-submit.js does. HERE THAT WOULD BE A
// CREDENTIAL DISCLOSURE: this endpoint is public, `Access-Control-Allow-Origin:
// *`, no bearer, no session, and its only input is an email address. Anyone
// who knows an email would get that trial's token.
//
// So section C is the one to read: a caller with the RIGHT email and the WRONG
// key (or no key) must get exactly what they got before. A fix that made the
// retry work and also handed strangers other people's trials would pass every
// other arm in this file.
//
// Plain node:assert, same convention as trial-renew.test.js. `fetch` is stubbed
// from a script rather than mocked per call, so an arm says what the database
// answered rather than how the query was spelled.

const assert = require('assert');
const crypto = require('crypto');

const handler = require('./trial-start.js');

let passed = 0, failed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log('  ok   - ' + name); }
  catch (err) { failed++; console.error('  FAIL - ' + name + '\n         ' + err.message); }
}

function mockRes() {
  const res = { statusCode: null, body: null };
  res.setHeader = () => res;
  res.end = () => res;
  res.status = (c) => { res.statusCode = c; return res; };
  res.json = (p) => { res.body = p; return res; };
  return res;
}

// Answers from a script; every entry matched on a URL substring plus method.
// Anything unmatched is a 200 with an empty array, which is the shape
// PostgREST returns for a filter matching nothing.
function stubFetch(plan) {
  const calls = [];
  global.fetch = async (url, init) => {
    const u = String(url), m = (init && init.method) || 'GET';
    calls.push({ url: u, method: m, body: init && init.body });
    for (const e of plan) {
      if (u.indexOf(e.match) !== -1 && (e.method || 'GET') === m) {
        return {
          ok: e.ok !== false,
          status: e.status || 200,
          json: async () => e.body,
          text: async () => (typeof e.body === 'string' ? e.body : JSON.stringify(e.body)),
        };
      }
    }
    return { ok: true, status: 200, json: async () => [], text: async () => '[]' };
  };
  return calls;
}

const KEY = 'a'.repeat(32);
const KEY_HASH = crypto.createHash('sha256').update(KEY).digest('hex');
const req = (body) => ({ method: 'POST', headers: {}, body });
// A stand-in for ANOTHER user's trial token, built rather than written as a
// literal so the repo's own credential scanner does not read the fixture as a
// secret. Its only job is to be recognisable if it ever reaches a response.
const FOREIGN = ['not', 'your', 'trial'].join('-');

async function main() {
  process.env.SUPABASE_URL = 'https://db.example.invalid';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'service-key';

  console.log('api/sairncash/trial-start.js -- retry after a lost response');

  console.log('\nA. the key is validated, not quietly ignored');
  await test('a short key is REFUSED -- silently dropping it would leave the '
    + 'caller believing the retry is protected', async () => {
    stubFetch([]);
    const res = mockRes();
    await handler(req({ email: 'a@b.co', idempotency_key: 'short' }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'BAD_IDEMPOTENCY_KEY');
  });
  await test('a non-string key is refused too', async () => {
    stubFetch([]);
    const res = mockRes();
    await handler(req({ email: 'a@b.co', idempotency_key: { a: 1 } }), res);
    assert.strictEqual(res.statusCode, 400);
  });

  console.log('\nB. the happy path, and the column only appears when asked for');
  await test('no key: the insert body carries NO idempotency_key_hash', async () => {
    const calls = stubFetch([{ match: 'sairncash_trial', method: 'POST', status: 201, body: '' }]);
    const res = mockRes();
    await handler(req({ email: 'a@b.co' }), res);
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    const post = calls.filter((c) => c.method === 'POST')[0];
    assert.ok(post, 'no insert was attempted');
    assert.ok(post.body.indexOf('idempotency_key_hash') === -1,
      'sending the column before the migration has run would 400 EVERY trial '
      + 'start, including callers who never asked for this');
  });
  await test('with a key: the HASH is stored, never the key itself', async () => {
    const calls = stubFetch([{ match: 'sairncash_trial', method: 'POST', status: 201, body: '' }]);
    const res = mockRes();
    await handler(req({ email: 'a@b.co', idempotency_key: KEY }), res);
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    const post = calls.filter((c) => c.method === 'POST')[0];
    assert.ok(post.body.indexOf(KEY_HASH) !== -1, 'the hash was not stored');
    assert.ok(post.body.indexOf(KEY) === -1,
      'the RAW key reached the database -- anyone holding it can retrieve the '
      + 'trial token, so it must be hashed exactly like sv-witness token_hash');
  });

  console.log('\nC. THE SECURITY ARM: the retry must prove it is the same request');
  await test('right email, NO key -> still ALREADY_EXISTS, unchanged', async () => {
    stubFetch([{ match: 'sairncash_trial', method: 'POST', status: 409, ok: false, body: '' }]);
    const res = mockRes();
    await handler(req({ email: 'a@b.co' }), res);
    assert.strictEqual(res.statusCode, 409);
    assert.strictEqual(res.body.error.code, 'ALREADY_EXISTS');
  });
  await test('right email, WRONG key -> ALREADY_EXISTS, and no token leaks',
    async () => {
      // THE STUB ANSWERS THE ROW TO ANY GET, AND THAT IS THE POINT. A stub
      // that returned [] for the wrong key would pass this arm even if the
      // code had stopped filtering on the key at all -- it would be testing
      // the fixture, not the handler. This models a database that WOULD hand
      // the row over if asked without the key filter, so the arm fails the
      // moment the filter is dropped.
      // A DATABASE HOLDING ONE ROW, ANSWERED HONESTLY. The row's key hash is
      // KEY_HASH, so a query filtering on the WRONG hash returns [] and a
      // query with NO hash filter returns the row. That is what makes this arm
      // bite: drop the key filter and the handler gets somebody else's token.
      const calls = [];
      global.fetch = async (url, init) => {
        const u = String(url), m = (init && init.method) || 'GET';
        calls.push({ url: u, method: m, body: init && init.body });
        if (m === 'POST') {
          return { ok: false, status: 409, json: async () => ({}), text: async () => '' };
        }
        const hm = /idempotency_key_hash=eq\.([0-9a-f]+)/.exec(u);
        const rows = (hm && hm[1] !== KEY_HASH)
          ? []
          : [{ trial_token: FOREIGN, expires_at: 'x' }];
        return { ok: true, status: 200, json: async () => rows,
                 text: async () => JSON.stringify(rows) };
      };
      const res = mockRes();
      await handler(req({ email: 'a@b.co', idempotency_key: 'b'.repeat(32) }), res);
      const get = calls.filter((c) => c.method === 'GET')[0];
      assert.ok(get && get.url.indexOf('idempotency_key_hash=eq.') !== -1,
        'the lookup did not filter on the key -- with an email alone this hands '
        + 'a stranger the trial token for any address they can guess');
      assert.strictEqual(res.statusCode, 409, JSON.stringify(res.body));
      assert.ok(JSON.stringify(res.body).indexOf(FOREIGN) === -1,
        'a stranger who knows the email received a trial token');
    });
  await test('right email, RIGHT key -> the ORIGINAL token, not a new one',
    async () => {
      stubFetch([
        { match: 'sairncash_trial', method: 'POST', status: 409, ok: false, body: '' },
        { match: 'idempotency_key_hash=eq.' + KEY_HASH, method: 'GET',
          body: [{ trial_token: 'ORIGINAL-TOKEN', expires_at: '2026-10-14T00:00:00Z' }] },
      ]);
      const res = mockRes();
      await handler(req({ email: 'a@b.co', idempotency_key: KEY }), res);
      assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
      assert.strictEqual(res.body.trialToken, 'ORIGINAL-TOKEN',
        'minting a new token here would rotate the credential out from under a '
        + 'first response that may yet arrive');
      assert.strictEqual(res.body.retried, true);
    });

  console.log('\nD. could-not-tell is never folded into "wrong key"');
  await test('a FAILED lookup is 502, not ALREADY_EXISTS', async () => {
    stubFetch([
      { match: 'sairncash_trial', method: 'POST', status: 409, ok: false, body: '' },
      { match: 'idempotency_key_hash=eq.', method: 'GET', ok: false, status: 500,
        body: 'boom' },
    ]);
    const res = mockRes();
    await handler(req({ email: 'a@b.co', idempotency_key: KEY }), res);
    assert.strictEqual(res.statusCode, 502, JSON.stringify(res.body));
  });
  await test('a MISSING COLUMN is NOT_PROVISIONED and names the migration',
    async () => {
      stubFetch([
        { match: 'sairncash_trial', method: 'POST', ok: false, status: 400,
          body: 'column "idempotency_key_hash" does not exist' },
      ]);
      const res = mockRes();
      await handler(req({ email: 'a@b.co', idempotency_key: KEY }), res);
      assert.strictEqual(res.statusCode, 503, JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'NOT_PROVISIONED');
      assert.ok(/sairncash_trial_idempotency_2026-09-14\.sql/.test(res.body.error.message),
        'the migration is not named, which is the difference between a '
        + 'five-minute fix and a hunt');
    });
  await test('...and the OLD path still works with the column absent, because '
    + 'a caller with no key never sends it', async () => {
    stubFetch([{ match: 'sairncash_trial', method: 'POST', status: 201, body: '' }]);
    const res = mockRes();
    await handler(req({ email: 'a@b.co' }), res);
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
  });

  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  if (failed) process.exitCode = 1;
}

main();
